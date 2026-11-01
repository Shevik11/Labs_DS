from pathlib import Path
import json
import os
os.environ['GRAPH_BACKEND'] = 'snapshot'
from optimized_engine import Engine
from guardrails import Guarded

R = Path(__file__).resolve().parent


def main():
    reference = json.loads((R/'results/benchmark.json').read_text('utf-8'))
    reference = {r['id']: r for r in reference if r['stage']==3}
    questions = [json.loads(x) for x in (R/'data/gold_v1.jsonl').read_text('utf-8').splitlines()]
    engine = Engine()
    guard = Guarded(engine)
    checks = []
    for q in questions:
        result = guard.ask(q['question'])
        prior = reference[q['id']]['result']
        checks.append(dict(id=q['id'], same_answer=result['answer']==prior['answer'],
                           same_status=result['status']==prior['status']))
    # Expire a real cached result and verify inference is used again.
    question=questions[0]['question']
    cached=guard.ask(question)
    key=(question,3,True)
    engine.cache_times[key] -= 301
    expired=guard.ask(question)
    checks.append(dict(id='ttl',same_answer=cached['answer']==expired['answer'],
                       same_status=cached['cache_hit'] and not expired['cache_hit']))
    result=dict(backend='63-node/38-edge Lab13 snapshot; no network latency',
                checks=checks,passed=all(x['same_answer'] and x['same_status'] for x in checks))
    (R/'results/snapshot_verification.json').write_text(
        json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    engine.close()
    assert result['passed'], result
    print('Snapshot parity and TTL: PASS')


if __name__=='__main__': main()
