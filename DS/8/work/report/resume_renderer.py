from pathlib import Path
import ctypes as C,json,subprocess,collections
ROOT=Path(r'D:\LNU\DS\8\.tools\report-render')
target=ROOT/'LibreOffice-readonly'
original=json.loads((ROOT/'selected_files.json').read_text(encoding='utf-8'))
files={}
for key,dest in original.items():
    rel=Path(dest).relative_to(target).as_posix().lower()
    if '/program/resource/' in rel and '/resource/en_us/' not in rel and '/resource/en-us/' not in rel:continue
    if '/share/config/images_' in rel and not rel.endswith('/images_colibre.zip'):continue
    files[key]=dest
# Remove only dispensable components from this temporary renderer directory.
for dest in original.values():
    p=Path(dest)
    if p.exists() and dest not in files.values():
        assert p.resolve().is_relative_to(target.resolve())
        p.unlink()
listing=subprocess.check_output(['C:/Windows/System32/tar.exe','-tvf',str(ROOT/'libreoffice1.cab')],text=True)
sizes={line.split()[-1]:int(line.split()[4]) for line in listing.splitlines()}
print('Minimal renderer bytes:',sum(sizes.get(k,0) for k in files),flush=True)
source=Path(r'D:\LNU\DS\8\work\report\extract_renderer_minimal.py').read_text(encoding='utf-8-sig')
source=source[source.index('class CabinetFile'):]
source=source.replace('extracted=0','extracted=0').replace("cabinets:","cabinets:")
cabinets=[ROOT/'libreoffice1.cab']
exec(compile(source,'selective_cabinet_extract','exec'))
