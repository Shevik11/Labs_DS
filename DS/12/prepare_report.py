from pathlib import Path
import shutil,json
from PIL import Image
r=Path.cwd();(r/'sources/lab8').mkdir(parents=True,exist_ok=True)
for n in ['report.pdf','MODEL_MAPPING.md']:shutil.copy2(Path('D:/LNU/DS/11/sources/lab8')/n,r/'sources/lab8'/n)
shutil.copytree('D:/LNU/DS/11/corpus',r/'corpus',dirs_exist_ok=True)
for n in ['simple','multihop','unanswerable']:
 im=Image.open(r/'figures'/f'{n}.png');im.crop((130,610,1190,im.height-55)).save(r/'figures'/f'{n}_result.png')
(r/'results/clean_install.json').write_text(json.dumps({'status':'failed','phase':'isolated_python_dependency_install','error':'OSError [Errno 28] No space left on device','graph_import':'passed: empty local Neo4j database imported','runtime':'passed: existing Python dependencies and inherited model files','next_step':'Free at least 5 GB; install requirements in new venv; run pytest and demo.py'},ensure_ascii=False,indent=2),'utf-8')
print([(x['id'],round(x['seconds'],3),x['prompt_tokens'],x['output_tokens']) for x in json.loads((r/'results/demo.json').read_text('utf-8'))])
