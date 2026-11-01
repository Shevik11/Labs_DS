import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEM = 'ЛР10_Шевчук_ФЕІм-13с'


def main():
    files = []
    for pattern in ['*.py', '*.md', '*.txt', '*.ttl', '*.log', 'schema.json', '*.docx', '*.pdf',
                    'data/*', 'prompts/*', 'results/*.json', 'work/architecture.png']:
        files.extend(path for path in ROOT.glob(pattern) if path.is_file())
    files = sorted(set(files))
    manifest = {str(p.relative_to(ROOT)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    output = ROOT/(STEM+'.zip')
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, 'lab10/'+str(path.relative_to(ROOT)).replace('\\','/'))
        archive.writestr('lab10/submission_manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert all('/model/' not in n and '/vendor/' not in n and '/.cache/' not in n for n in archive.namelist())
    print(output, output.stat().st_size)


if __name__ == '__main__':
    main()
