from pathlib import Path
import hashlib, json, math, statistics, zipfile
from pypdf import PdfReader

R=Path(__file__).resolve().parent
if not (R/'evidence').exists(): R=R/'ЛР16'
def load(path):return json.loads((R/path).read_text('utf-8-sig'))
def quantile(values,q):
    values=sorted(values); x=(len(values)-1)*q; i=int(x)
    return values[i]+(values[min(i+1,len(values)-1)]-values[i])*(x-i)
rows=load('evidence/lab15/results/benchmark.json')
summary=load('evidence/lab15/results/summary.json')
assert len(rows)==160
checks={}
for stage in range(4):
    group=[r for r in rows if r['stage']==stage]
    assert len(group)==40 and len({r['id'] for r in group})==40
    s=summary[stage]
    assert math.isclose(s['accuracy'],sum(r['correct'] for r in group)/40)
    assert math.isclose(s['mean_seconds'],statistics.mean(r['seconds'] for r in group))
    assert math.isclose(s['p95_seconds'],quantile([r['seconds'] for r in group],.95))
    for field,key in [('input_tokens','prompt_tokens'),('output_tokens','output_tokens')]:
        assert s[field]==sum(r['result'][key] for r in group)
    checks[f'stage_{stage}']='40 IDs, success, timing, tokens verified'
assert sum(r['correct'] for r in rows if r['stage']==0)==23
assert sum(r['correct'] for r in rows if r['stage']==3)==40
for kind,n in [('simple',20),('multihop',10),('unanswerable',5),('adversarial',5)]:
    assert len([r for r in rows if r['stage']==3 and r['type']==kind])==n
assert all(x['passed'] for x in load('evidence/lab15/results/safety.json'))
assert load('evidence/lab13/results/calibration.json')['judge_validated_for_use'] is False
for item in load('SOURCE_MANIFEST.json'):
    assert hashlib.sha256((R/item['file']).read_bytes()).hexdigest()==item['sha256']
calc=load('calculations.json')
assert calc['monthly_net_uah']==1000*5/60*300-9000==16000
assert calc['payback_months']==40000/16000
pdf=R/'ЛР16_Шевчук_ФЕІм-13с.pdf'
reader=PdfReader(pdf)
assert len(reader.pages)==12
assert len(load('report_content.json'))==12
for i,page in enumerate(reader.pages):
    assert len(page.extract_text())>200, f'Empty page {i+1}'
text='\n'.join(p.extract_text() for p in reader.pages)
for phrase in ['Резюме для керівника','Метрики успіху','Архітектура','Реєстр ризиків','Декларація використання ШІ','Додаток А']:
    assert phrase in text,phrase
with zipfile.ZipFile(R/'ЛР16_Шевчук_ФЕІм-13с.docx') as z:
    xml=z.read('word/document.xml').decode()
    assert xml.count('<w:drawing>')==2
    assert 'Шевчук Максим Вікторович' in xml
for p in R.rglob('*'):
    if p.is_file():
        assert p.name not in ['.env','id_rsa','credentials.json']
        assert p.suffix.lower() not in ['.gguf','.safetensors','.pem','.key']
checks.update(pdf_pages=12,source_hashes='PASS',calculations='PASS',docx_images=2,
              pdf_visual_review='All 12 pages inspected',docx_visual_review='Unavailable: LibreOffice missing',
              repository='pending' if 'очікує підтвердження' in text else 'included',
              new_model_inference=False)
(R/'VALIDATION.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
