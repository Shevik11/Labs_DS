from pathlib import Path
import hashlib
import json
import shutil

R = Path(__file__).resolve().parent
SOURCE = Path('D:/LNU/DS')
for name in ('data', 'index', 'static', 'results', 'figures', 'sources', 'tests', 'work'):
    (R / name).mkdir(exist_ok=True)
files = ['engine.py', 'app.py', 'import_graph.py', 'download_models.py',
         'requirements.txt', 'data/nodes.json', 'data/relationships.json',
         'index/metadata.json', 'index/vectors.faiss', 'static/index.html']
provenance = []
for name in files:
    src, dest = SOURCE / '12' / name, R / name
    shutil.copy2(src, dest)
    provenance.append(dict(source=str(src), destination=name,
                           source_sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
src = SOURCE / '11/questions.json'
shutil.copy2(src, R / 'data/questions.json')
shutil.copy2('D:/downloads/ЛР14_завдання.pdf', R / 'sources/assignment14.pdf')
# Preserve citations exposed by /sources from the inherited index.
shutil.copytree(SOURCE / '12/sources', R / 'sources', dirs_exist_ok=True)
app = (R / 'app.py').read_text('utf-8')
start = app.index(" @app.middleware('http')")
end = app.index(' @app.exception_handler', start)
app = app[:start] + ' from telemetry import install\n install(app)\n' + app[end:]
app = app.replace("title='ЛР12 — Energy GraphRAG'", "title='ЛР14 — Energy GraphRAG monitoring'")
app = app.replace("result.pop('prompt',None);request.state.tokens=result['prompt_tokens']+result['output_tokens']",
                  "result.pop('prompt',None)\n   request.state.prompt_tokens=result['prompt_tokens']\n   request.state.output_tokens=result['output_tokens']")
(R / 'app.py').write_text(app, 'utf-8')
engine = (R / 'engine.py').read_text('utf-8')
engine = engine.replace("os.environ['HF_HOME']=str(Path(__file__).parent/'work/hf')",
                        "os.environ.setdefault('HF_HOME', '/tmp/huggingface')")
engine = engine.replace("os.environ['TRANSFORMERS_CACHE']=str(Path(__file__).parent/'work/hf/hub')",
                        "os.environ.setdefault('TRANSFORMERS_CACHE', '/tmp/huggingface/hub')")
(R / 'engine.py').write_text(engine, 'utf-8')
requirements = (R / 'requirements.txt').read_text('utf-8')
requirements += '\nscipy==1.15.3\nmatplotlib==3.10.1\nprometheus-client==0.21.1\n'
(R / 'requirements.txt').write_text(requirements, 'utf-8')
(R / 'data/provenance.json').write_text(json.dumps(provenance, indent=2), 'utf-8')
print('Prepared Lab12 reuse; model weights remain outside build context')
