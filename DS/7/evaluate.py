"""Development-only retrieval tuning and frozen test comparison, with raw evidence."""
from pathlib import Path
import csv
import html
import json
import platform
import re
import statistics
import time
from importlib.metadata import version
from rag import ROOT, Retriever, Generator, REFUSAL, read_json, save_json

def questions():
    def q(cid, split, question, relevant, patterns):
        return dict(id=cid, split=split, question=question, relevant_ids=relevant, expected_patterns=patterns, answerable=bool(relevant))
    dev = [
        q('d01','dev','Які індустрія, домен і задача обрані у першій лабораторній?', ['lab1.variant'], ['енергет','програмн','візуаліза']),
        q('d02','dev','З якої країни і якого об’єкта взято вимірювання електроспоживання?', ['lab1.dataset'], ['Франц','домогосподар']),
        q('d03','dev','Який числовий поріг високого споживання і як його обчислено?', ['lab1.threshold'], ['1[.,]5613','75']),
        q('d04','dev','Яка accuracy класифікатора Logistic Regression?', ['lab1.classification'], ['0[.,]824|82[.,]4']),
        q('d05','dev','Які MAE Random Forest та MAE наївного прогнозу?', ['lab1.regression'], ['0[.,]3359|0[.,]336','0[.,]4235|0[.,]424']),
        q('d06','dev','Скільки кластерів K-means обрано і яке значення silhouette?', ['lab1.clustering'], ['2','0[.,]1858|0[.,]186']),
        q('d07','dev','Що означає клас Measurement в онтології?', ['class.Measurement'], ['час','значенн','одиниц']),
        q('d08','dev','Яка властивість є оберненою до records?', ['property.records'], ['recordedBy']),
        q('d09','dev','Яка ліцензія набору даних UCI?', ['lab1.dataset'], ['CC BY 4[.,]0']),
        q('d10','dev','Чи означає високий клас підтверджену аварію?', ['lab1.threshold'], ['не','авар']),
        q('d11','dev','Дай рецепт шоколадного торта.', [], []),
        q('d12','dev','Хто переміг у футбольному чемпіонаті світу 2022 року?', [], []),
    ]
    test = [
        q('t01','test','Скільки спостережень використано для навчання і для тесту?', ['lab1.split'], ['22\s?233','9\s?530']),
        q('t02','test','Скільки повних годин залишилося після очищення?', ['lab1.quality'], ['34\s?085']),
        q('t03','test','Як обчислити енергію за годину з хвилинної потужності та що робити з неповними годинами?', ['lab1.aggregation'], ['60','неповн','виключ|пропуск']),
        q('t04','test','Які часові лаги входять до ознак прогнозу?', ['lab1.features'], ['1','2','24','168']),
        q('t05','test','Якими були прогноз і факт на 2009-09-09 20:00?', ['lab5.forecast'], ['1[.,]9519|1[.,]952','2[.,]12']),
        q('t06','test','Чи є відсутність явного атрибута суперечністю в OWL і чому?', ['lab5.openworld'], ['не','відкрит']),
        q('t07','test','Який тип HermiT вивів для forecastChart?', ['lab5.inference'], ['ForecastVisualization']),
        q('t08','test','Які шість полів або зв’язків Measurement повинні мати рівно одне значення?', ['lab5.restrictions'], ['timestamp','numericValue','qualityFlag','observesIndicator','recordedBy','hasUnit']),
        q('t09','test','Скільки перевірок і SPARQL-сценаріїв пройшла онтологія ЛР5?', ['lab5.validation'], ['88','8']),
        q('t10','test','Скільки концептів та напрямлених відношень у граф-моделі третьої лабораторної?', ['lab3.graph'], ['16','20']),
        q('t11','test','Що таке TimeSeries у цій предметній області?', ['class.TimeSeries'], ['час','вимірюван','показник','об’єкт|об.єкт']),
        q('t12','test','Яка одиниця потужності, а яка — енергії?', ['lab1.aggregation'], ['кВт','кВт[·⋅* ]год']),
        q('t13','test','Яка столиця Японії?', [], []),
        q('t14','test','Скільки коштує електроенергія в Україні сьогодні?', [], []),
        q('t15','test','Який пароль Wi-Fi у досліджуваному домогосподарстві?', [], []),
    ]
    return dev + test

def retrieval_metrics(queries, hits_by_id):
    positive = [q for q in queries if q['answerable']]
    negative = [q for q in queries if not q['answerable']]
    def matched(q):
        return set(q['relevant_ids']) & {x['id'] for x in hits_by_id[q['id']]}
    recalls = [len(matched(q))/len(q['relevant_ids']) for q in positive]
    precisions = [len(matched(q))/max(1,len(hits_by_id[q['id']])) for q in positive]
    rr = []
    for q in positive:
        ranks = [i+1 for i,h in enumerate(hits_by_id[q['id']]) if h['id'] in q['relevant_ids']]
        rr.append(1/min(ranks) if ranks else 0)
    successes = [bool(matched(q)) if q['answerable'] else not hits_by_id[q['id']] for q in queries]
    return dict(recall=statistics.mean(recalls), precision=statistics.mean(precisions), mrr=statistics.mean(rr), unknown_rejection_rate=statistics.mean([not hits_by_id[q['id']] for q in negative]), retrieval_success_rate=statistics.mean(successes))

def check_answer(query, response):
    answer = response['answer']
    norm = answer.replace('\u00a0',' ').replace('\u202f',' ')
    matched = [bool(re.search(p, norm, flags=re.I)) for p in query['expected_patterns']]
    citations = re.findall(r'\[([a-zA-Z0-9_.]+)\]', answer)
    given = {p['id'] for p in response['passages']}
    refusal = response['refused'] or bool(re.search(r'не (?:маю|знаю|можу)|немає (?:даних|інформації)|недостатньо',answer,re.I))
    # These are reproducible surface checks, not a semantic correctness judge.
    return dict(fact_pattern_match=all(matched) if query['answerable'] else refusal,
                patterns_matched=matched, citations=citations,
                citation_ids_valid=bool(citations) and all(c in given for c in citations),
                expected_source_cited=bool(set(citations) & set(query['relevant_ids'])),
                refused_detected=refusal)

def run():
    import torch
    from build_knowledge import build
    build()
    queries = questions()
    save_json(ROOT / 'evaluation' / 'queries.json', queries)
    retriever = Retriever(rebuild=True)
    valid_ids = {x['id'] for x in retriever.chunks}
    assert all(set(q['relevant_ids']) <= valid_ids for q in queries)
    # Freeze test definitions before tuning. Only dev questions enter the tuning loop.
    dev = [q for q in queries if q['split']=='dev']
    test = [q for q in queries if q['split']=='test']
    retriever.score(dev[0]['question'])  # warmup excluded
    dev_scores = {q['id']:retriever.score(q['question'])[:2] for q in dev}
    configs = []
    for k in [1,3,5]:
        for weight in [0.0,0.25,0.5]:
            for threshold in [0.0,0.45,0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90]:
                config = dict(top_k=k, lexical_weight=weight, min_score=threshold)
                hits = {q['id']:retriever.select(*dev_scores[q['id']], config) for q in dev}
                configs.append({**config, **retrieval_metrics(dev,hits)})
    selected = max(configs,key=lambda c:(c['retrieval_success_rate'],c['recall'],c['precision'],c['mrr'],-c['top_k'],-c['lexical_weight']))
    optimized = {k:selected[k] for k in ['top_k','lexical_weight','min_score']}
    save_json(ROOT / 'results' / 'selected_config.json', optimized)
    save_json(ROOT / 'results' / 'tuning.json', dict(split='dev only; 12 questions, not included in final test metrics', objective='maximize retrieval_success_rate, recall, precision, MRR; ties favor smaller k then less lexical weight', selected=selected, configurations=configs))
    with (ROOT / 'results' / 'tuning.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(configs[0])); writer.writeheader(); writer.writerows(configs)
    baseline = dict(top_k=3,lexical_weight=0.0,min_score=0.0)
    retrieval_records = []
    for q in test:
        dense, lexical, ms = retriever.score(q['question'])
        retrieval_records.append(dict(id=q['id'],question=q['question'], relevant_ids=q['relevant_ids'], retrieval_ms=ms, baseline=retriever.select(dense,lexical,baseline), optimized=retriever.select(dense,lexical,optimized)))
    save_json(ROOT / 'results' / 'retrieval_test.json', retrieval_records)
    benchmarks = {}
    for name, config in [('baseline',baseline),('optimized',optimized)]:
        times = []
        for repeat in range(5):
            for q in test:
                start = time.perf_counter()
                retriever.retrieve(q['question'],config)
                times.append((time.perf_counter()-start)*1000)
        times.sort()
        benchmarks[name] = dict(repetitions=5,queries_per_repetition=len(test),warmup_excluded=True,scope='query encoding + FAISS search over all passages + lexical scoring + filtering; no model loading or generation',p50_ms=statistics.median(times),p95_ms=times[int(.95*(len(times)-1))],mean_ms=statistics.mean(times))
    save_json(ROOT / 'results' / 'retrieval_benchmark.json', benchmarks)
    print('Selected config',optimized,'dev',selected,flush=True)
    generator = Generator()
    generator.generate('Відповідай одним словом: привіт.',None)  # generation warmup excluded
    raw_path = ROOT / 'results' / 'answers.jsonl'
    raw_path.write_text('',encoding='utf-8')
    records = []
    # Re-use a single model and deterministic decoding for all three conditions.
    for i,q in enumerate(test):
        ret = retrieval_records[i]
        for name,hits in [('no_context',None),('baseline',ret['baseline']),('optimized',ret['optimized'])]:
            response = generator.generate(q['question'],hits)
            response.update(id=q['id'],condition=name,question=q['question'],passages=hits or [],retrieval_ms=0.0 if hits is None else ret['retrieval_ms'])
            response['checks'] = check_answer(q,response)
            with raw_path.open('a',encoding='utf-8') as f:
                f.write(json.dumps(response,ensure_ascii=False)+'\n')
            records.append(response)
            print(q['id'],name,response['checks']['fact_pattern_match'],f"{response['generation_ms']/1000:.1f}s",response['answer'][:150],flush=True)
    save_json(ROOT / 'results' / 'answers.json', records)
    summary = {}
    for condition in ['no_context','baseline','optimized']:
        rows = [r for r in records if r['condition']==condition]
        positives = [r for r in rows if next(q for q in test if q['id']==r['id'])['answerable']]
        negatives = [r for r in rows if r not in positives]
        summary[condition] = dict(questions=len(rows),answer_fact_pattern_accuracy=statistics.mean([r['checks']['fact_pattern_match'] for r in rows]),answerable_fact_pattern_accuracy=statistics.mean([r['checks']['fact_pattern_match'] for r in positives]),unknown_refusal_rate=statistics.mean([r['checks']['refused_detected'] for r in negatives]),valid_citation_rate_answerable=statistics.mean([r['checks']['citation_ids_valid'] for r in positives]),expected_source_citation_rate=statistics.mean([r['checks']['expected_source_cited'] for r in positives]),mean_generation_ms=statistics.mean([r['generation_ms'] for r in rows]),mean_generation_ms_when_called=statistics.mean([r['generation_ms'] for r in rows if r['generator_called']]))
        if condition!='no_context':
            summary[condition]['retrieval'] = retrieval_metrics(test,{r['id']:r[condition] for r in retrieval_records})
    save_json(ROOT / 'results' / 'metrics.json',dict(test_questions=len(test),positive_questions=sum(q['answerable'] for q in test),negative_questions=sum(not q['answerable'] for q in test),chunk_count=len(retriever.chunks),selected_config=optimized,conditions=summary,limitations=['Small authored evaluation; not an external benchmark.', 'Exact source IDs are conservative: alternative README passages can also contain the answer.', 'Fact-pattern checks verify selected strings, not complete semantic correctness or entailment.', 'Citation validity verifies identifiers, not that all claims are supported.', 'Some optimized refusals come from the retrieval gate and do not call the LLM.', 'CPU warm timings exclude model loading; no speedup should be inferred from small differences.']))
    save_json(ROOT / 'results' / 'environment.json',dict(python=platform.python_version(),platform=platform.platform(),torch_threads=torch.get_num_threads(),cuda=torch.cuda.is_available(),device='cpu',packages={p:version(p) for p in ['torch','transformers','numpy','faiss-cpu','scikit-learn','huggingface-hub']},models=read_json(ROOT / 'models' / 'metadata.json'),generation=dict(do_sample=False,max_new_tokens=160,repetition_penalty=1.05,enable_thinking=False,seed=42)))
    blocks = []
    for q in test:
        cells = []
        for r in [r for r in records if r['id']==q['id']]:
            sources = '\n\n'.join('['+p['id']+'] '+p['source']+' / '+p['locator']+'\n'+p['text'] for p in r['passages'])
            cells.append('<article><b>'+html.escape(r['condition'])+'</b><p>'+html.escape(r['answer'])+'</p><small>Генерація: '+f"{r['generation_ms']/1000:.2f}"+' с</small><details><summary>Знайдені джерела</summary><pre>'+html.escape(sources or 'Без контексту / відмова пошуку')+'</pre></details></article>')
        blocks.append('<section><h2>'+html.escape(q['id']+' · '+q['question'])+'</h2><div class="grid">'+''.join(cells)+'</div></section>')
    page = '<!doctype html><html lang="uk"><meta charset="utf-8"><title>ЛР7 · Енергетичний RAG</title><style>body{font:16px system-ui;background:#eef2f5;color:#172333;max-width:1400px;margin:40px auto;padding:0 22px}h1{font-size:32px}h2{font-size:19px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}article{background:white;border-radius:12px;padding:18px;line-height:1.6}section{margin:34px 0}pre{white-space:pre-wrap;font-size:12px;overflow-wrap:anywhere}small{color:#546578}summary{cursor:pointer;margin-top:14px}@media(max-width:850px){.grid{grid-template-columns:1fr}}</style><h1>ЛР7 · RAG для енергетичних даних</h1><p>Збережені реальні відповіді Qwen3-0.6B. Порівняння без контексту, базового та налаштованого RAG. Це перегляд результатів, не інтерактивна генерація.</p>'+''.join(blocks)+'</html>'
    (ROOT / 'results' / 'demo.html').write_text(page,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    run()
