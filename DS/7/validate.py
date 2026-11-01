"""Artifact integrity and independent checks of the saved RAG experiment."""
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import faiss
from rag import ROOT, read_json, save_json
from evaluate import retrieval_metrics, check_answer

def validate():
    checks = []
    def check(name, condition):
        checks.append({'name':name, 'passed':bool(condition)})
    chunks = read_json(ROOT / 'knowledge' / 'chunks.json')
    by_id = {c['id']:c for c in chunks}
    for source in read_json(ROOT / 'knowledge' / 'sources.json'):
        file = ROOT / source['file']
        check('source hash: ' + source['file'], hashlib.sha256(file.read_bytes()).hexdigest()==source['sha256'])
    check('unique chunk ids',len(chunks)==len(by_id))
    check('passages contain no evaluation expected answers',all('expected_patterns' not in c['text'] for c in chunks))
    for c in chunks:
        check('provenance: '+c['id'],(ROOT / c['source']).is_file() and bool(c['locator']))
    original = read_json(ROOT / 'inputs' / 'lab1_metrics.json')
    for value, cid in [(original['split']['train_rows'],'lab1.split'),(original['split']['test_rows'],'lab1.split'),(original['split']['high_threshold_kwh'],'lab1.threshold'),(original['data_quality']['complete_hours'],'lab1.quality')]:
        check('numeric provenance: '+str(value),str(value) in by_id[cid]['text'])
    vectors = np.load(ROOT / 'knowledge' / 'embeddings.npy')
    index = faiss.read_index(str(ROOT / 'knowledge' / 'index.faiss'))
    check('FAISS dimensions and count',index.ntotal==len(chunks)==len(vectors) and index.d==vectors.shape[1])
    check('unit norm embeddings',np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5))
    query = np.ascontiguousarray(vectors[[0,12,35]],dtype='float32')
    scores,ids = index.search(query,5)
    independent = query @ vectors.T
    check('FAISS scores equal independent cosine',all(np.allclose(scores[i],independent[i,ids[i]],atol=1e-5) for i in range(len(query))))
    qs = read_json(ROOT / 'evaluation' / 'queries.json')
    qmap = {q['id']:q for q in qs}
    dev = [q for q in qs if q['split']=='dev']; test = [q for q in qs if q['split']=='test']
    check('separate dev and test question text',not ({q['question'] for q in dev} & {q['question'] for q in test}))
    check('dev/test counts',len(dev)==12 and len(test)==15)
    check('test relevant ids exist',all(set(q['relevant_ids'])<=set(by_id) for q in qs))
    tuning = read_json(ROOT / 'results' / 'tuning.json')
    check('99 distinct tuning configurations',len(tuning['configurations'])==99 and len({(c['top_k'],c['lexical_weight'],c['min_score']) for c in tuning['configurations']})==99)
    check('selection has maximum dev objective',tuning['selected']['retrieval_success_rate']==max(c['retrieval_success_rate'] for c in tuning['configurations']))
    config = read_json(ROOT / 'results' / 'selected_config.json')
    retrieval = read_json(ROOT / 'results' / 'retrieval_test.json')
    check('all test retrieval records present',{r['id'] for r in retrieval}=={q['id'] for q in test})
    for row in retrieval:
        for cond in ['baseline','optimized']:
            for p in row[cond]:
                check('retrieved content unchanged: '+row['id']+':'+cond+':'+p['id'],p['text']==by_id[p['id']]['text'])
        check('optimized threshold: '+row['id'],all(p['score']>=config['min_score'] for p in row['optimized']))
        check('optimized top k: '+row['id'],len(row['optimized'])<=config['top_k'])
    answers = read_json(ROOT / 'results' / 'answers.json')
    lines = [json.loads(line) for line in (ROOT / 'results' / 'answers.jsonl').read_text(encoding='utf-8').splitlines()]
    check('raw JSONL equals full answer export',lines==answers)
    check('45 unique test/condition runs',len(answers)==45 and len({(r['id'],r['condition']) for r in answers})==45)
    for r in answers:
        check('recomputed answer checks '+r['id']+':'+r['condition'],check_answer(qmap[r['id']],r)==r['checks'])
        check('answers have nonnegative measured duration '+r['id']+':'+r['condition'],r['generation_ms']>=0)
        if r['generator_called']:
            check('real generated tokens '+r['id']+':'+r['condition'],r['output_tokens']>0 and bool(r['prompt']))
        if r['condition']=='optimized' and not r['passages']:
            check('gate avoids generator '+r['id'],not r['generator_called'] and r['refused'])
    metrics = read_json(ROOT / 'results' / 'metrics.json')
    for cond in ['baseline','optimized']:
        m = retrieval_metrics(test,{r['id']:r[cond] for r in retrieval})
        check('recomputed retrieval metrics '+cond,m==metrics['conditions'][cond]['retrieval'])
    save_json(ROOT / 'results' / 'validation.json',dict(passed=sum(c['passed'] for c in checks),failed=sum(not c['passed'] for c in checks),checks=checks))
    print(f"Passed {sum(c['passed'] for c in checks)}; failed {sum(not c['passed'] for c in checks)}")
    if not all(c['passed'] for c in checks):
        raise SystemExit(1)

if __name__=='__main__':
    validate()
