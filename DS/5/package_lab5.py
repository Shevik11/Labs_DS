"""Archive deliverables and report evidence, excluding the local environment."""
from pathlib import Path
import hashlib, json, zipfile

ROOT=Path(__file__).resolve().parent
EXCLUDE={'.venv','__pycache__','.git','work'}
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and not EXCLUDE.intersection(p.relative_to(ROOT).parts)
             and p.name not in {'lab5_energy_ontology.zip','manifest.json','Запустити_Protege.cmd'})
manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(ROOT/'lab5_energy_ontology.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in files+[ROOT/'manifest.json']: z.write(p,Path('5')/p.relative_to(ROOT))
with zipfile.ZipFile(ROOT/'lab5_energy_ontology.zip') as z:
    assert z.testzip() is None
    for name,digest in manifest.items():
        assert hashlib.sha256(z.read('5/'+name)).hexdigest()==digest
print(f'Archive verified: {len(files)+1} files')
