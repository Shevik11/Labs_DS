import csv
import json
import argparse
from pathlib import Path

from lab10 import ROOT, Knowledge, validate, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--first', type=Path, help='First independent human CSV; omit to use provisional Codex labels')
    parser.add_argument('--second', type=Path, default=ROOT/'data/annotation_blind.csv')
    args = parser.parse_args()
    path = args.second
    records = list(csv.DictReader(path.open(encoding='utf-8-sig', newline='')))
    if len(records) < 10 or any(not r['status'].strip() for r in records):
        raise SystemExit('Need at least 10 completed independent annotations. Kappa was not calculated.')
    gold = {}
    if args.first:
        for row in csv.DictReader(args.first.open(encoding='utf-8-sig', newline='')):
            if not row['status'].strip():
                raise SystemExit('First independent annotation is incomplete.')
            gold[row['id']] = dict(status=row['status'].strip(), classes=[c.strip() for c in row['classes'].split(';') if c.strip()])
    else:
        for split in ('dev', 'test'):
            for line in (ROOT/f'data/{split}.jsonl').read_text(encoding='utf-8').splitlines():
                row = json.loads(line)
                gold[row['id']] = row
    knowledge = Knowledge()
    first, second = [], []
    def signature(obj):
        return obj['status'] + ':' + ','.join(sorted(obj['classes']))
    for row in records:
        if row['id'] not in gold:
            raise SystemExit('ID missing from first annotation: ' + row['id'])
        validate(json.dumps(gold[row['id']]), knowledge, strict=True) if args.first else None
        obj = dict(status=row['status'].strip(), classes=[x.strip() for x in row['classes'].split(';') if x.strip()])
        validate(json.dumps(obj), knowledge, strict=True)
        first.append(signature(gold[row['id']]))
        second.append(signature(obj))
    n = len(records)
    labels = set(first+second)
    po = sum(a == b for a,b in zip(first, second))/n
    pe = sum(first.count(label)*second.count(label) for label in labels)/(n*n)
    kappa = (po-pe)/(1-pe) if pe < 1 else None
    save('results/annotation_agreement.json', dict(n=n, observed=po, expected=pe, kappa=kappa,
         comparison=('Two supplied independent annotation files; human provenance must be confirmed by author.' if args.first else
                     'Provisional Codex-authored labels vs independent human; not two verified human annotators.'),
         disagreements=[r['id'] for r,a,b in zip(records, first,second) if a!=b]))
    print('Cohen kappa:', kappa)


if __name__ == '__main__':
    main()
