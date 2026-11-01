import json,os,time,platform,importlib.metadata
from pathlib import Path
from engine import Engine
r=Path(__file__).parent;e=Engine();rows=[]
questions=[('simple','How many nodes and relationships are in the complete Lab8 graph?',True),('multihop_vector','Which series is analyzed by the model on which forecastChart is based?',False),('multihop_graph','Which series is analyzed by the model on which forecastChart is based?',True),('unanswerable','What was the household consumption in January 2025?',True)]
for id,q,g in questions:
 t=time.perf_counter();a=e.ask(q,3,g);rows.append(dict(a,id=id,question=q,use_graph=g,seconds=time.perf_counter()-t));print(id,a['answer'],flush=True)
(r/'results/demo.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf-8')
(r/'results/run.json').write_text(json.dumps({'python':platform.python_version(),'platform':platform.platform(),'seed':42,'health':e.health(),'versions':{m:importlib.metadata.version(m) for m in ['fastapi','uvicorn','pydantic','httpx','pytest','neo4j','torch','transformers','sentence-transformers','faiss-cpu','numpy'] }},indent=2),'utf-8')
e.close()
