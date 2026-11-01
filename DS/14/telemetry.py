from datetime import datetime, timezone
import json
import logging
import os
import time
import uuid

from fastapi.responses import Response
from prometheus_client import (CollectorRegistry, Counter, Histogram,
                               generate_latest, CONTENT_TYPE_LATEST)

MODEL_VERSION = 'flan-t5-small@0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab'
PROMPT_VERSION = 'lab12-extractive-v1'


def install(app):
    registry = CollectorRegistry()
    requests = Counter('lab14_requests', 'Completed HTTP requests',
                       ['route', 'status'], registry=registry)
    errors = Counter('lab14_errors', 'HTTP errors including validation',
                     ['route', 'status'], registry=registry)
    latency = Histogram('lab14_latency_seconds', 'HTTP processing time',
                        ['route'], buckets=(.01, .05, .1, .5, 1, 2, 5, 10, 30, 60),
                        registry=registry)
    tokens = Counter('lab14_tokens', 'Successful generation tokens',
                     ['kind'], registry=registry)
    cost = Counter('lab14_api_cost_usd', 'External API charge only', registry=registry)
    cost.inc(0)
    logger = logging.getLogger('lab14.requests')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)

    @app.middleware('http')
    async def audit(request, call_next):
        request.state.rid = uuid.uuid4().hex
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers['X-Request-ID'] = request.state.rid
            return response
        finally:
            # Template route labels prevent unbounded cardinality from source ids.
            route = getattr(request.scope.get('route'), 'path', 'unmatched')
            elapsed = time.perf_counter() - start
            if route not in ('/metrics', '/health'):
                requests.labels(route, str(status)).inc()
                latency.labels(route).observe(elapsed)
                if status >= 400:
                    errors.labels(route, str(status)).inc()
                inp = getattr(request.state, 'prompt_tokens', 0)
                out = getattr(request.state, 'output_tokens', 0)
                tokens.labels('input').inc(inp)
                tokens.labels('output').inc(out)
                row = dict(timestamp=datetime.now(timezone.utc).isoformat(),
                           request_id=request.state.rid, route=route, status=status,
                           model_version=MODEL_VERSION, prompt_version=PROMPT_VERSION,
                           duration_ms=round(elapsed * 1000, 3),
                           prompt_tokens=inp, output_tokens=out, tokens=inp + out,
                           token_accounting='successful_generations_only',
                           api_cost_usd=0.0)
                logger.info(json.dumps(row, ensure_ascii=False))
                path = os.getenv('REQUEST_LOG')
                if path:
                    with open(path, 'a', encoding='utf-8') as stream:
                        stream.write(json.dumps(row, ensure_ascii=False) + '\n')

    @app.get('/metrics', include_in_schema=True)
    def metrics():
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    app.state.metrics_registry = registry
