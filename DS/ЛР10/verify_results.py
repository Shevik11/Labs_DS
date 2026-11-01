import hashlib
import json
from pathlib import Path

from lab10 import ROOT, load_rows, metrics, save, Knowledge, validate


def load(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def main():
    dev, test = load_rows('dev'), load_rows('test')
    assert not {r['id'] for r in dev} & {r['id'] for r in test}
    assert len(dev)+len(test) >= 30
    assert sum(r['category']=='malicious' for r in dev+test) >= 5
    assert hashlib.sha256((ROOT/'data/test.jsonl').read_bytes()).hexdigest() == load('data/manifest.json')['test_sha256']
    selection = load('results/selection.json')
    assert selection['test_seen'] is False
    assert selection['prompt_sha256'] == hashlib.sha256((ROOT/'lab10.py').read_bytes()).hexdigest()
    knowledge = Knowledge()
    for style in ['instruction','role','context','fewshot']:
        assert len(load('results/templates_'+style+'.json')) == 5
    assert len(load('results/dynamic_demo.json')) == 5
    for version, expected in load('results/dev_metrics.json').items():
        results = load('results/dev_'+version+'.json')
        assert len(results) == len(dev)
        assert metrics(results, dev) == expected
    test_results = load('results/test.json')
    assert len(test_results) == len(test)
    assert all(r['version']==selection['version'] for r in test_results)
    assert metrics(test_results, test) == load('results/test_metrics.json')
    for path in (ROOT/'results').glob('*.json'):
        value = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(value, list):
            for row in value:
                if not isinstance(row,dict) or 'attempts' not in row:
                    continue
                assert len(row['attempts']) <= (1 if row['version']=='v1' else 3)
                if row['schema_valid']:
                    assert validate(row['attempts'][-1]['raw'], knowledge) == row['prediction']
    attack = load('results/attack_metrics.json')
    assert attack['v1']['n'] == attack['v3']['n'] >= 5
    save('results/requirement_matrix.json', {
        'result_1': {'status':'complete','evidence':'4 prompt types x 5 queries; schema and saved responses'},
        'result_2': {'status':'complete','evidence':'dynamic SPARQL, ontology validation, up to 2 retries, 5 queries'},
        'result_3': {'status':'partial','evidence':'38 synthetic cases, rules, dev/test, version; blind form for 10 cases',
                     'missing':'Two independent human annotations and Cohen kappa'},
        'result_4': {'status':'complete','evidence':'3 dev versions, tokens/cost, errors, frozen one-time held-out evaluation'},
        'result_5': {'status':'complete','evidence':'7 attacks before/after; multiple guards; README and AI declaration'},
    })
    save('results/verification.json', {'status':'passed','checks':'counts, split disjointness, test hash, source freeze, metrics recomputation, saved accepted responses, retry limits',
         'remaining':'Independent human annotations; no kappa fabricated'})
    print('Saved results verified. Independent human annotation remains incomplete.')


if __name__ == '__main__':
    main()
