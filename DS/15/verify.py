from pathlib import Path
import ast
import hashlib
import json

R=Path(__file__).resolve().parent


def load(name): return json.loads((R/name).read_text('utf-8-sig'))


def main():
    rows=load('results/benchmark.json')
    chunks={c['id']:c for c in load('index/metadata.json')}
    assert len(rows)==160
    for stage in range(4):
        group=[r for r in rows if r['stage']==stage]
        assert len(group)==40 and len({r['id'] for r in group})==40
    summary=load('results/summary.json')
    for stage in range(4):
        group=[r for r in rows if r['stage']==stage]
        assert abs(summary[stage]['accuracy']-sum(r['correct'] for r in group)/40)<1e-10
        assert summary[stage]['input_tokens']==sum(r['result']['prompt_tokens'] for r in group)
    for row in rows:
        for source in row['result']['sources']:
            assert source['id'] in chunks
            assert source['quote'] in chunks[source['id']]['text']
    assert all(x['passed'] for x in load('results/safety.json'))
    assert all(x['passed'] for x in load('results/api.json'))
    regression=load('results/regression.json')
    assert regression['lost_correct_ids']==[], regression
    assert regression['final_accuracy_ge_baseline']
    assert summary[3]['recall_at3']>=summary[0]['recall_at3']
    assert load('results/snapshot_verification.json')['passed']
    assert hashlib.sha256((R/'data/gold_v1.jsonl').read_bytes()).hexdigest()==load('results/environment.json')['question_sha256']
    for path in R.glob('*.py'):
        ast.parse(path.read_text('utf-8-sig'))
    result={'passed':True,'benchmark_rows':160,'checks':'metrics, citations, safety, API, regression, snapshot, source hash, Python syntax'}
    (R/'results/verification.json').write_text(json.dumps(result,indent=2),'utf-8')
    print('Artifact verification: PASS')


if __name__=='__main__':main()
