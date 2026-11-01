from contextlib import asynccontextmanager
from pathlib import Path
import asyncio,json,logging,time,uuid,os
from typing import Literal
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel,Field,ConfigDict,field_validator
from starlette.concurrency import run_in_threadpool
R=Path(__file__).parent
log=logging.getLogger('lab12');log.setLevel(logging.INFO)
if not log.handlers:log.addHandler(logging.StreamHandler())
class Ask(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 question:str=Field(min_length=3,max_length=500)
 top_k:int=Field(default=3,ge=1,le=5)
 use_graph:bool=True
 @field_validator('question')
 @classmethod
 def clean(cls,v):
  if len(v.strip())<3:raise ValueError('Питання має містити щонайменше 3 символи')
  return v.strip()
class Source(BaseModel):
 id:str;doc_id:str;title:str;quote:str;source:str;source_page:int
class Node(BaseModel):
 id:str;name:str|None=None
class GraphPath(BaseModel):
 id:str;nodes:list[Node];relations:list[str]
class Answer(BaseModel):
 answer:str;status:Literal['answered','insufficient_data'];sources:list[Source];graph:list[GraphPath]
 raw_model_answer:str;prompt_tokens:int;output_tokens:int;request_id:str

def create_app(engine=None,timeout=30):
 @asynccontextmanager
 async def life(app):
  if app.state.engine is None:
   from engine import Engine
   app.state.engine=await run_in_threadpool(Engine)
  yield
  if engine is None:app.state.engine.close()
 app=FastAPI(title='ЛР12 — Energy GraphRAG',version='1.0',lifespan=life)
 app.state.engine=engine;app.state.busy=False
 @app.middleware('http')
 async def audit(request:Request,call_next):
  rid=uuid.uuid4().hex;request.state.rid=rid;t=time.perf_counter()
  response=await call_next(request)
  response.headers['X-Request-ID']=rid
  log.info(json.dumps({'request_id':rid,'duration_ms':round((time.perf_counter()-t)*1000,2),'status':response.status_code,'tokens':getattr(request.state,'tokens',0)}))
  return response
 @app.exception_handler(RequestValidationError)
 async def validation(request,exc):
  # Do not echo input values, question text, credentials, or paths in errors/logs.
  return JSONResponse(status_code=422,content={'detail':'Некоректні дані: question 3–500 символів, top_k 1–5; зайві поля заборонені','request_id':request.state.rid})
 @app.get('/')
 def index():return FileResponse(R/'static/index.html')
 @app.get('/health')
 async def health():
  try:return {'status':'ok',**await run_in_threadpool(app.state.engine.health)}
  except Exception:raise HTTPException(503,'Neo4j недоступна або система не готова')
 @app.get('/sources/{id}',response_model=Source)
 def source(id:str):
  c=next((c for c in app.state.engine.chunks if c['id']==id),None)
  if not c:raise HTTPException(404,'Джерело не знайдено')
  return dict(c,quote=c['text'])
 @app.post('/ask',response_model=Answer)
 async def ask(body:Ask,request:Request):
  if app.state.busy:raise HTTPException(429,'Система зайнята; повторіть запит пізніше')
  app.state.busy=True
  async def work():
   try:return await run_in_threadpool(app.state.engine.ask,body.question,body.top_k,body.use_graph)
   finally:app.state.busy=False
  task=asyncio.create_task(work())
  try:
   # Keep a timed-out worker busy until it really finishes; prevent runaway queues.
   result=await asyncio.wait_for(asyncio.shield(task),timeout)
   result.pop('prompt',None);request.state.tokens=result['prompt_tokens']+result['output_tokens']
   return dict(result,request_id=request.state.rid)
  except asyncio.TimeoutError:raise HTTPException(504,'Перевищено час відповіді LLM')
  except Exception:raise HTTPException(503,'Недоступна база або сервіс генерації')
 return app
app=create_app()
