from pathlib import Path
import json,logging,asyncio
from fastapi.testclient import TestClient
from app import create_app,log
from engine import Engine
r=Path.cwd();handler=logging.FileHandler(r/'results/requests.jsonl',mode='w',encoding='utf-8');log.addHandler(handler)
e=Engine();checks={}
with TestClient(create_app(e)) as c:
 for key,url in [('health','/health'),('source','/sources/fixed-0001'),('openapi','/openapi.json')]:
  resp=c.get(url);assert resp.status_code==200;checks[key]=resp.json()
 resp=c.post('/ask',json={'question':'Which series is analyzed by the model on which forecastChart is based?'})
 assert resp.status_code==200;d=resp.json();assert any(p['nodes'][-1]['id']=='owl:predictionSeries' and len(p['relations'])==2 for p in d['graph'])
 assert all(c['quote'] in next(x['text'] for x in e.chunks if x['id']==c['id']) for c in d['sources'])
 checks['ask']=d
 for bad in ['', 'x'*501]:assert c.post('/ask',json={'question':bad}).status_code==422
(r/'results/integration.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),'utf-8')
log.removeHandler(handler);handler.close();e.close()
print('Real Neo4j + FAISS + LLM API, graph path, exact source quotes: PASS')
