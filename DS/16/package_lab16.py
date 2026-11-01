from pathlib import Path
import hashlib, json, zipfile

R=Path(__file__).resolve().parent
name='ЛР16_Шевчук_ФЕІм-13с.zip'
files=[p for p in R.rglob('*') if p.is_file()
       and p.suffix!='.zip' and p.name!='MANIFEST.sha256.json'
       and not any(x in p.parts for x in ['__pycache__','.venv','work','.git'])]
assert not any(p.name=='.env' or p.suffix in ['.key','.pem','.gguf','.safetensors'] for p in files)
manifest={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(R/'MANIFEST.sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
files.append(R/'MANIFEST.sha256.json')
with zipfile.ZipFile(R/name,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):z.write(p,p.relative_to(R).as_posix())
with zipfile.ZipFile(R/name) as z:
    assert z.testzip() is None
    for rel,sha in manifest.items():assert hashlib.sha256(z.read(rel)).hexdigest()==sha
print(f'ZIP verified: {len(files)} files, {(R/name).stat().st_size} bytes')
