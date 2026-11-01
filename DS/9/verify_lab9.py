import hashlib
import json
import math
import sys
from pathlib import Path

from neo4j import GraphDatabase

from build_lab9 import LAB8, ROOT, dump

sys.path.insert(0, str(LAB8))
from run_neo4j import run


def main():
    # Verify the exact copy/paste commands, not only the parameterized equivalents.
    driver = GraphDatabase.driver('bolt://127.0.0.1:17689', auth=None)
    browser = []
    with driver.session(database='neo4j') as session:
        for file in sorted((ROOT / 'browser').glob('*.cypher')):
            text = '\n'.join(line for line in file.read_text(encoding='utf-8').splitlines()
                             if not line.lstrip().startswith('//'))
            for index, statement in enumerate(text.split(';')):
                if statement.strip():
                    rows, _, _ = run(session, statement)
                    browser.append({'file': file.relative_to(ROOT).as_posix(),
                                    'statement': index + 1, 'query': statement.strip(), 'rows': rows})
    driver.close()
    checks = {'all_11_browser_statements_return_results': len(browser) == 11 and all(b['rows'] for b in browser)}
    manifest = json.loads((ROOT / 'results/audit/lab8_snapshot_manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        relative = item['relative_path']
        for base in [LAB8, Path(manifest['source_lab8'])]:
            actual = hashlib.sha256((base / relative).read_bytes()).hexdigest()
            if actual != item['sha256']:
                raise RuntimeError('Source/snapshot changed: ' + relative)
    checks['all_89_snapshot_and_source_hashes_unchanged'] = len(manifest['files']) == 89
    latest = json.loads((ROOT / 'results/latest_local.json').read_text(encoding='utf-8'))
    folder = ROOT / latest['folder']
    validation = json.loads((folder / 'validation.json').read_text(encoding='utf-8'))
    samples = json.loads((folder / 'language_samples.json').read_text(encoding='utf-8'))
    checks['latest_run_passed'] = validation['status'] == 'passed' and all(validation['checks'].values())
    checks['all_60_timing_samples_finite_positive'] = len(samples) == 60 and all(math.isfinite(s['wall_ms']) and s['wall_ms'] > 0 for s in samples)
    report_path = ROOT / 'results/report_creation.json'
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
    checks['report_state_matches_user_request'] = (all((ROOT / report.get(k, '')).is_file() for k in ['docx', 'pdf']) if report.get('status') == 'ready' else not list(ROOT.glob('*.docx')) and not list(ROOT.glob('*.pdf')))
    dump(ROOT / 'results/audit/browser_commands_verified.json', browser)
    dump(ROOT / 'results/audit/final_verification.json', {'status': 'passed' if all(checks.values()) else 'failed',
                                                         'checks': checks, 'source_files_modified': False,
                                                         'new_sandbox_screenshots': ('verified user evidence' if (ROOT / 'results/sandbox_screenshot_review.json').exists() and json.loads((ROOT / 'results/sandbox_screenshot_review.json').read_text(encoding='utf-8')).get('status') == 'verified' else 'pending user')})
    if not all(checks.values()):
        raise RuntimeError('Final verification failed')
    print('PASS: 11 literal Browser commands, 89 unchanged source/snapshot files, 60 timing samples; report state checked.')


if __name__ == '__main__':
    main()
