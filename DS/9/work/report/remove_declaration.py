from pathlib import Path
from docx import Document

WORK = Path(__file__).resolve().parent
ROOT = Path('D:/LNU/DS/9')
STEM = 'ЛР09_Шевчук_ФЕІм-13с'
doc = Document(ROOT / (STEM + '.docx'))
paras = doc.paragraphs
start = next(i for i,p in enumerate(paras) if p.text == 'Декларація використання ШІ')
end = next(i for i in range(start+1,len(paras)) if paras[i].text == 'Висновок')
assert end-start == 3
for para in paras[start:end]:
    para._p.getparent().remove(para._p)
head = next(p for p in doc.paragraphs if p.text == 'Відтворення та використання ШІ')
head.runs[0].text = 'Відтворення результатів'
for run in head.runs[1:]:
    run.text = ''
assert not any('OpenAI Codex' in p.text or 'використання ШІ' in p.text for p in doc.paragraphs)
assert any('мій звіт' in p.text for p in doc.paragraphs)
doc.save(WORK / 'without_declaration_raw.docx')

builder = (ROOT / 'work/report/build_report.py').read_text(encoding='utf-8')
a = builder.index("h('Декларація використання ШІ', 2)")
b = builder.index("h('Висновок')",a)
builder = builder[:a] + builder[b:]
builder = builder.replace("page('Відтворення та використання ШІ')", "page('Відтворення результатів')")
compile(builder, 'build_report.py', 'exec')
(WORK / 'build_report.py').write_text(builder, encoding='utf-8')

verify = (ROOT / 'work/report/verify_report.py').read_text(encoding='utf-8')
old = "'ai_declaration_present': 'Декларація використання ШІ' in full and 'OpenAI Codex' in full,"
assert verify.count(old) == 1
verify = verify.replace(old, "'ai_declaration_removed_as_requested': 'Декларація використання ШІ' not in full and 'OpenAI Codex' not in full,")
(WORK / 'verify_report.py').write_text(verify, encoding='utf-8')
(WORK / 'verify_no_declaration.py').write_text(verify.replace("WORK / 'render_final'", "WORK / 'render_no_declaration'"), encoding='utf-8')
print('Removed declaration heading and two paragraphs; renamed reproduction heading.')
