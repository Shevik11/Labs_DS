from pathlib import Path
import hashlib
import json
import zipfile

R=Path(__file__).resolve().parent
STEM='ЛР15_Шевчук_ФЕІм-13с'
EXCLUDED={'.git','work','__pycache__','.venv','models','pilot_results'}


def members():
    return sorted(p for p in R.rglob('*') if p.is_file() and
        not any(part in EXCLUDED for part in p.relative_to(R).parts) and
        p.suffix!='.zip' and p.name not in {'.env','MANIFEST.sha256.json'})


def main():
    paths=members()
    assert (R/(STEM+'.pdf')).is_file()
    assert (R/'lab15.bundle').is_file()
    manifest={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (R/'MANIFEST.sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
    archive=R/(STEM+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in paths+[R/'MANIFEST.sha256.json']:
            z.write(path,path.relative_to(R).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in manifest.items():
            assert hashlib.sha256(z.read(name)).hexdigest()==digest
        assert not any('.env'==Path(n).name or n.endswith('.pyc') for n in z.namelist())
    print(f'ZIP verified: {len(paths)+1} files; {archive.stat().st_size} bytes')


if __name__=='__main__':main()
