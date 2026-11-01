from pathlib import Path
import json
from fastapi.testclient import TestClient
from app import create_app
from engine import Engine
from drift import AlertManager

# Load real models and real graph; replace only generation to model LLM outage.
engine = Engine()
original = engine.llm.generate
def unavailable(*args, **kwargs):
    raise RuntimeError('Injected LLM failure')
engine.llm.generate = unavailable
with TestClient(create_app(engine)) as client:
    response = client.post('/ask', json={'question': 'How many nodes does the graph contain?'})
    assert response.status_code == 503
    alert = AlertManager().check({}, 0, llm_failed=response.status_code == 503)
    evidence = dict(method='in-process fault injection into loaded real LLM.generate',
                    http_status=response.status_code, response=response.json(), alert=alert,
                    distinction='simulated LLM outage; not an observed spontaneous failure')
    Path('results/fault_injection.json').write_text(json.dumps(evidence, indent=2), 'utf-8')
engine.llm.generate = original
engine.close()
print(json.dumps(evidence))
