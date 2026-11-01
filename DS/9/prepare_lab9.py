import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lab8', type=Path, default=Path('D:/LNU/DS/8'))
    parser.add_argument('--assignment', type=Path, default=Path('D:/downloads/ЛР09_завдання.pdf'))
    args = parser.parse_args()
    source = args.lab8.resolve()
    target = ROOT / 'inherited/lab8'
    selected_dirs = ['data', 'inputs', 'queries', 'cypher', 'browser', 'figures',
                     'results/screenshots', 'results/local_20261016T053315908454Z',
                     'results/sandbox_20261016T054342525797Z']
    selected_files = ['build_lab8.py', 'run_neo4j.py', 'requirements.txt', 'README.md',
                      'MODEL_MAPPING.md', 'SANDBOX_REVIEW.md', 'SANDBOX_STEPS.md',
                      'REPORT_MATERIALS.md', 'results/build_validation.json',
                      'results/sandbox_review.json',
                      'Звіт_Лабораторна_8_Neo4j_Енергетика.pdf']
    for folder in selected_dirs:
        selected_files.extend(p.relative_to(source).as_posix()
                              for p in (source / folder).rglob('*') if p.is_file())
    inventory = []
    # Preserve user evidence byte for byte. No server files, credentials or environments.
    for relative in sorted(set(selected_files)):
        src, dest = source / relative, target / relative
        if not src.is_file():
            raise FileNotFoundError(src)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(src, dest)
        src_hash, dest_hash = digest(src), digest(dest)
        if src_hash != dest_hash:
            raise RuntimeError('Snapshot mismatch: ' + relative)
        inventory.append({'relative_path': relative, 'bytes': src.stat().st_size,
                          'sha256': src_hash, 'copied_without_changes': True})
    audit = ROOT / 'results/audit'
    audit.mkdir(parents=True, exist_ok=True)
    manifest = {'source_lab8': str(source), 'snapshot': 'inherited/lab8',
                'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'excluded': ['.tools', '.venv', '__pycache__', 'work (rendering intermediates)'],
                'files': inventory}
    (audit / 'lab8_snapshot_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    inputs = ROOT / 'inputs'
    inputs.mkdir(exist_ok=True)
    assignment = inputs / 'ЛР09_завдання.pdf'
    if not assignment.exists():
        shutil.copy2(args.assignment, assignment)
    if digest(assignment) != digest(args.assignment):
        raise RuntimeError('Assignment snapshot mismatch')
    for pdf, stem in [(assignment, 'lab9_assignment'),
                      (target / 'inputs/ds_lab_8.pdf', 'lab8_assignment'),
                      (target / 'Звіт_Лабораторна_8_Neo4j_Енергетика.pdf', 'lab8_report')]:
        reader = PdfReader(pdf)
        text = '\n\n'.join('PAGE ' + str(i + 1) + '\n' + (page.extract_text() or '')
                             for i, page in enumerate(reader.pages))
        (audit / (stem + '.txt')).write_text(text, encoding='utf-8')
    print('Saved', len(inventory), 'unchanged lab8 files to', target)
    print('PDF source texts saved under', audit)


if __name__ == '__main__':
    main()
