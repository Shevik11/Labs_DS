from pathlib import Path
import json,hashlib,zipfile,ast
from lxml import etree
r=Path.cwd();stem='ЛР12_Шевчук_ФЕІм-13с'
files=[]
for folder in ['data','index','corpus','sources','static','tests','results','figures']:
 files.extend(p for p in (r/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for name in ['app.py','engine.py','import_graph.py','download_models.py','demo.py','verify_integration.py','start_neo4j.ps1','neo4j-local.conf','compose.yaml','requirements.txt','requirements-report.txt','README.md','AI_DECLARATION.md','ЩО_ПОТРІБНО_ВІД_ТЕБЕ.txt','build_report.py','.gitignore',stem+'.pdf',stem+'.docx']:
 files.append(r/name)
for p in files:
 if p.suffix=='.py':ast.parse(p.read_text('utf-8-sig'))
manifest={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
(r/'MANIFEST.sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8');files.append(r/'MANIFEST.sha256.json')
with zipfile.ZipFile(r/(stem+'.docx')) as z:
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 for name in ['word/styles.xml','word/stylesWithEffects.xml']:
  if name in z.namelist():
   root=etree.fromstring(z.read(name));assert not root.xpath('//w:style[@w:styleId="Title"]/w:pPr/w:pBdr',namespaces=ns)
with zipfile.ZipFile(r/(stem+'.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(r).as_posix())
with zipfile.ZipFile(r/(stem+'.zip')) as z:
 assert z.testzip() is None
 assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest.items())
 assert not any(n.endswith(('.safetensors','.exe','.dll','.env')) for n in z.namelist())
 print('ZIP:',len(z.namelist()),'files;',round((r/(stem+'.zip')).stat().st_size/1024**2,2),'MiB; checksums OK')
print('Code syntax, DOCX title borders, ZIP CRC + SHA256: PASS')
