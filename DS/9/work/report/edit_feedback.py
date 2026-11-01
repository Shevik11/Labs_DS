from pathlib import Path
from docx import Document

WORK = Path(__file__).resolve().parent
ROOT = Path('D:/LNU/DS/9')
STEM = 'ЛР09_Шевчук_ФЕІм-13с'
OLD = 'Модель, імпортер та повний граф уже створено в лабораторній роботі №8. Надалі позначення «ЛР08» стосується звіту Шевчука М. В. «Збереження знань у графовій базі даних для візуалізації енергетичних даних», 2026, 20 с. Повторний опис цих частин замінено посиланнями на його розділи та сторінки.'
NEW = 'Модель, імпортер та повний граф я створив у своїй лабораторній роботі №8. Надалі «ЛР08» означає мій звіт «Збереження знань у графовій базі даних для візуалізації енергетичних даних», 2026, 20 с. Замість повторного опису цих частин посилаюся на відповідні розділи та сторінки мого звіту.'

doc = Document(ROOT / (STEM + '.docx'))
matches = [p for p in doc.paragraphs if p.text == OLD]
assert len(matches) == 1
para = matches[0]
para.runs[0].text = NEW
for run in para.runs[1:]:
    run.text = ''
doc.save(WORK / 'feedback_raw.docx')

builder = (ROOT / 'work/report/build_report.py').read_text(encoding='utf-8')
assert builder.count(OLD) == 1
(WORK / 'build_report.py').write_text(builder.replace(OLD, NEW), encoding='utf-8')
print('Own-work reference corrected; title author retained.')
