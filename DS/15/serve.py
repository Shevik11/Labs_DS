import os
os.environ.setdefault('GRAPH_BACKEND', 'snapshot')
from optimized_engine import Engine
from guardrails import Guarded
from api import create_app

app = create_app(Guarded(Engine()))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8155)
