from pathlib import Path
from datetime import datetime, timezone
import json
import time
import urllib.request
import urllib.error

import numpy as np

R = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:8144'


def fetch(route, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + route, data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def main():
    start = datetime.now(timezone.utc).isoformat()
    before = fetch('/metrics')[1]
    (R / 'results/metrics_before.prom').write_text(before, 'utf-8')
    questions = json.loads((R / 'data/questions.json').read_text('utf-8'))
    rows = []
    for i in range(50):
        # 45 real generations, five intentional invalid requests, serial CPU load.
        if i % 10 == 9:
            payload = dict(question='x', top_k=8)
            expected = 422
        else:
            payload = dict(question=questions[i % len(questions)]['question'],
                           top_k=3, use_graph=True)
            expected = 200
        t = time.perf_counter()
        status, text = fetch('/ask', payload)
        row = dict(sequence=i + 1, status=status, expected_status=expected,
                   seconds=time.perf_counter() - t, response=json.loads(text))
        rows.append(row)
        (R / 'results/load_requests.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), 'utf-8')
        print(f'{i + 1}/50 HTTP {status}', flush=True)
    after = fetch('/metrics')[1]
    (R / 'results/metrics_after.prom').write_text(after, 'utf-8')
    times = np.array([r['seconds'] for r in rows])
    summary = dict(started_utc=start, finished_utc=datetime.now(timezone.utc).isoformat(),
                   total=50, successful=sum(r['status'] == 200 for r in rows),
                   intentional_validation_errors=sum(r['status'] == 422 for r in rows),
                   unexpected=sum(r['status'] != r['expected_status'] for r in rows),
                   mean_seconds=float(times.mean()), p50_seconds=float(np.quantile(times, .5)),
                   p95_seconds=float(np.quantile(times, .95)), max_seconds=float(times.max()),
                   input_tokens=sum(r['response'].get('prompt_tokens', 0) for r in rows),
                   output_tokens=sum(r['response'].get('output_tokens', 0) for r in rows),
                   api_cost_usd=0.0,
                   cost_scope='local model; excludes electricity, hardware and infrastructure',
                   success_p95_seconds=float(np.quantile([r['seconds'] for r in rows if r['status']==200], .95)),
                   first_request_seconds=rows[0]['seconds'],
                   design='45 real inference calls, five intentional HTTP422; models loaded, first inference not warmed separately')
    (R / 'results/load_summary.json').write_text(json.dumps(summary, indent=2), 'utf-8')
    print(json.dumps(summary, indent=2))
    if summary['unexpected']:
        raise SystemExit('Unexpected responses: inspect results before accepting benchmark')


if __name__ == '__main__':
    main()
