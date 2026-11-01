import asyncio,time
from fastapi.testclient import TestClient
from app import create_app
class Fake:
 chunks=[{'id':'fixed-0001','doc_id':'D01','title':'Size','source':'lab8','source_page':3,'text':'43746 nodes'}]
 def health(self):return {'neo4j':'ok','faiss':1,'llm':'loaded'}
 def ask(self,*args):return {'answer':'43746 nodes [fixed-0001]','status':'answered','sources':[dict(self.chunks[0],quote='43746 nodes')],'graph':[],'raw_model_answer':'43746','prompt_tokens':20,'output_tokens':2}

def test_success():
 with TestClient(create_app(Fake())) as c:
  r=c.post('/ask',json={'question':'How many nodes?'})
  assert r.status_code==200 and r.json()['sources'][0]['id']=='fixed-0001'
def test_invalid_data():
 with TestClient(create_app(Fake())) as c:
  for value in [None,4,'  ']:assert c.post('/ask',json={'question':value}).status_code==422
  assert c.post('/ask',json={'question':'abc','top_k':6}).status_code==422
def test_long_input():
 with TestClient(create_app(Fake())) as c:assert c.post('/ask',json={'question':'x'*501}).status_code==422
def test_database_failure():
 class Broken(Fake):
  def ask(self,*args):raise ConnectionError('sensitive password')
 with TestClient(create_app(Broken())) as c:
  r=c.post('/ask',json={'question':'abc'});assert r.status_code==503 and 'password' not in r.text
def test_timeout():
 class Slow(Fake):
  def ask(self,*args):time.sleep(.08);return super().ask(*args)
 with TestClient(create_app(Slow(),timeout=.01)) as c:
  assert c.post('/ask',json={'question':'abc'}).status_code==504
  assert c.post('/ask',json={'question':'abc'}).status_code==429
def test_response_format():
 with TestClient(create_app(Fake())) as c:
  r=c.post('/ask',json={'question':'abc'});d=r.json()
  assert set(d)=={'answer','status','sources','graph','raw_model_answer','prompt_tokens','output_tokens','request_id'}
  assert d['request_id']==r.headers['x-request-id'] and len(d['request_id'])==32
def test_sources_and_docs():
 with TestClient(create_app(Fake())) as c:
  assert c.get('/sources/fixed-0001').json()['quote']=='43746 nodes'
  assert c.get('/sources/unknown').status_code==404
  assert c.get('/docs').status_code==200
  assert {'/ask','/health','/sources/{id}'}<=set(c.get('/openapi.json').json()['paths'])
def test_health_unavailable():
 class Broken(Fake):
  def health(self):raise ConnectionError()
 with TestClient(create_app(Broken())) as c:assert c.get('/health').status_code==503
def test_validation_redaction(caplog):
 with TestClient(create_app(Fake())) as c:
  r=c.post('/ask',json={'question':'SECRET_PERSON','password':'SECRET_TOKEN'})
  assert r.status_code==422 and 'SECRET' not in r.text
 assert 'SECRET' not in caplog.text
