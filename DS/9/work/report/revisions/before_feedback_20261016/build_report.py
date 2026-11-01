import ast
import hashlib
import json
import re
import textwrap
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path('D:/LNU/DS/9')
WORK = Path(__file__).resolve().parent
STEM = 'ЛР09_Шевчук_ФЕІм-13с'


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8-sig'))


RUN = load('results/latest_local.json')['folder']
VALID = load(RUN + '/validation.json')
ANS = load(RUN + '/query_results.json')
COMP = load(RUN + '/language_comparison.json')
PROFILES = load(RUN + '/profiles.json')
CAT = {q['id']: q for q in load('queries/catalog.json')}
PAIRS = {q['id']: q for q in load('comparison/catalog.json')}
REVIEW = load('results/sandbox_screenshot_review.json')
assert VALID['status'] == 'passed' and all(VALID['checks'].values())
assert REVIEW['status'] == 'verified' and len(REVIEW['screenshots']) == 4
for screenshot in REVIEW['screenshots']:
    assert hashlib.sha256((ROOT / screenshot['file']).read_bytes()).hexdigest() == screenshot['sha256']

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(2), Cm(2)
sec.left_margin, sec.right_margin = Cm(2), Cm(1)
sec.header_distance = Cm(0.7)
sec.different_first_page_header_footer = True
for style_name in ['Normal', 'Title', 'Heading 1', 'Heading 2', 'Caption']:
    style = doc.styles[style_name]
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12 if style_name == 'Caption' else 14)
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.font.italic = False
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.5
    fonts = style.element.get_or_add_rPr().rFonts
    for key in list(fonts.attrib):
        if key.endswith('Theme'):
            del fonts.attrib[key]
    for key in ['ascii', 'hAnsi', 'eastAsia', 'cs']:
        fonts.set(qn('w:' + key), 'Times New Roman')
doc.styles['Normal'].paragraph_format.first_line_indent = Cm(1.25)
for name in ['Heading 1', 'Heading 2']:
    doc.styles[name].font.bold = True
    doc.styles[name].paragraph_format.first_line_indent = Cm(0)
    doc.styles[name].paragraph_format.keep_with_next = True
doc.styles['Heading 1'].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.styles['Heading 1'].paragraph_format.space_after = Pt(6)
doc.styles['Heading 2'].paragraph_format.space_before = Pt(6)
doc.styles['Heading 2'].paragraph_format.space_after = Pt(3)
doc.styles['Caption'].paragraph_format.first_line_indent = Cm(0)
doc.styles['Caption'].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.styles['Caption'].paragraph_format.line_spacing = 1
doc.styles['Caption'].paragraph_format.space_after = Pt(6)
doc.styles['Caption'].font.bold = False
header = sec.header.paragraphs[0]
header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
header.paragraph_format.first_line_indent = Cm(0)
field = OxmlElement('w:fldSimple')
field.set(qn('w:instr'), 'PAGE')
header._p.append(field)
doc.core_properties.author = 'Шевчук Максим Вікторович'
doc.core_properties.title = 'Лабораторна робота 9 Збереження знань у графовій базі даних'
doc.core_properties.subject = 'Вибрані розділи науки про дані'


def font(run, size=14, bold=False, family='Times New Roman'):
    run.font.name, run.font.size = family, Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    run.font.bold = bold
    pr = run._element.get_or_add_rPr()
    for key in ['ascii', 'hAnsi', 'eastAsia', 'cs']:
        pr.rFonts.set(qn('w:' + key), family)


def p(text='', indent=True, before=0, after=0, align=None):
    para = doc.add_paragraph()
    para.alignment = align or WD_ALIGN_PARAGRAPH.JUSTIFY
    para.paragraph_format.first_line_indent = Cm(1.25 if indent else 0)
    para.paragraph_format.space_before = Pt(before)
    para.paragraph_format.space_after = Pt(after)
    font(para.add_run(text))
    return para


def h(text, level=1):
    para = doc.add_paragraph(text, style='Heading ' + str(level))
    return para


def page(title=None):
    if title:
        h(title).paragraph_format.page_break_before = True


def table(title, headers, rows, widths):
    para = p(title, indent=False, before=4, after=3)
    para.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment, t.autofit = WD_TABLE_ALIGNMENT.CENTER, False
    for col, width in zip(t.columns, widths):
        col.width = Cm(width)
    props = t._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        item = OxmlElement('w:' + edge)
        item.set(qn('w:val'), 'single')
        item.set(qn('w:sz'), '4')
        item.set(qn('w:color'), 'B7B7B7')
        borders.append(item)
    props.append(borders)
    for index, values in enumerate([headers] + rows):
        row = t.rows[0] if index == 0 else t.add_row()
        trpr = row._tr.get_or_add_trPr()
        cant = OxmlElement('w:cantSplit')
        trpr.append(cant)
        if index == 0:
            repeat = OxmlElement('w:tblHeader')
            trpr.append(repeat)
        for cell, value, width in zip(row.cells, values, widths):
            cell.width = Cm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            para = cell.paragraphs[0]
            para.paragraph_format.first_line_indent = Cm(0)
            para.paragraph_format.line_spacing = 1
            para.paragraph_format.space_after = Pt(3)
            para.paragraph_format.space_before = Pt(3)
            font(para.add_run(str(value)), bold=index == 0)
    return t


figures = []


def fig(filename, caption):
    number = len(figures) + 1
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.first_line_indent = Cm(0)
    para.paragraph_format.line_spacing = 1
    para.paragraph_format.space_before = Pt(4)
    para.paragraph_format.keep_with_next = True
    picture = para.add_run().add_picture(str(ROOT / 'results/screenshots' / filename), width=Cm(18))
    picture._inline.docPr.set('descr', caption)
    doc.add_paragraph('Рис. ' + str(number) + ' — ' + caption, style='Caption')
    figures.append(filename)


def code(text):
    t = doc.add_table(rows=1, cols=1)
    t.autofit = False
    t.columns[0].width = Cm(18)
    t.cell(0, 0).width = Cm(18)
    props = t._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ['top', 'left', 'bottom', 'right']:
        border = OxmlElement('w:' + edge)
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:color'), 'D9D9D9')
        borders.append(border)
    props.append(borders)
    cell = t.cell(0, 0)
    tcpr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), 'F2F2F2')
    tcpr.append(shading)
    margins = OxmlElement('w:tcMar')
    for edge in ['top', 'left', 'bottom', 'right']:
        margin = OxmlElement('w:' + edge)
        margin.set(qn('w:w'), '144')
        margin.set(qn('w:type'), 'dxa')
        margins.append(margin)
    tcpr.append(margins)
    cell._tc.getparent().get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    para = cell.paragraphs[0]
    para.paragraph_format.first_line_indent = Cm(0)
    para.paragraph_format.line_spacing = Pt(13.2)
    font(para.add_run(text.rstrip()), 12, family='Consolas')
    return t


def format_query(query):
    # Whitespace-only formatting; identifiers and string literal contents are preserved.
    if '[:ANALYZES_SERIES|' in query:
        query = re.sub(r'\[:(ANALYZES_SERIES\|[^\]]+)\]',
                       lambda m: '[:' + m[1].replace('|', '|\n  ') + ']', query)
    lines = []
    for line in query.splitlines():
        lead = re.match(r'\s*', line)[0]
        lines += textwrap.wrap(line, width=68, break_long_words=False,
                               break_on_hyphens=False, subsequent_indent=lead + '  ') or ['']
    return '\n'.join(lines)


def query(identifier, label):
    spec = CAT[identifier]
    h(label + ' ' + spec['question'], 2)
    code(format_query(spec['query']) + ';')


def n(value, places=4):
    return f'{value:.{places}f}'.replace('.', ',')


def cover_line(text, before=0, after=0, size=14, bold=False, right=False):
    para = doc.add_paragraph(style='Title' if text == 'Звіт' else 'Normal')
    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT if right else WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.first_line_indent = Cm(0)
    para.paragraph_format.line_spacing = 1
    para.paragraph_format.space_before, para.paragraph_format.space_after = Pt(before), Pt(after)
    font(para.add_run(text), size, bold)


cover_line('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ', before=14, after=3, size=12)
cover_line('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА', after=3, size=12)
cover_line('Факультет електроніки і комп’ютерних технологій')
cover_line('Звіт', before=84, after=12, bold=True)
cover_line('про виконання лабораторної роботи №9', after=12)
cover_line('з курсу «Вибрані розділи науки про дані»', after=18)
cover_line('«Збереження знань у графовій базі даних»')
cover_line('Виконав:', before=148, after=4, bold=True, right=True)
cover_line('студент групи ФЕІм-13с', after=4, right=True)
cover_line('Шевчук Максим Вікторович', after=18, right=True)
cover_line('Перевірив:', after=7, bold=True, right=True)
cover_line('Парубочий В. О.', right=True)
cover_line('Львів 2026', before=140)

page('Тема та мета роботи')
p('Тема — збереження знань у графовій базі даних на прикладі аналізу та візуалізації електроспоживання. Мета — доповнити наявну графову базу знань запитами Cypher, дослідити її структуру та зіставити відповіді й час виконання трьох однакових питань у SPARQL і Cypher.')
h('Завдання')
for text in [
    '1. Перевірити модель графа, обмеження та індекси.',
    '2. Підтвердити ідемпотентність імпорту й відповідність джерелу.',
    '3. Виконати різні типи запитів Cypher та перевірити PROFILE.',
    '4. Дослідити ієрархію, найкоротші шляхи та ступені вузлів.',
    '5. Порівняти SPARQL і Cypher та обґрунтувати вибір сховища.',
]:
    p(text, indent=False)
h('Використання результатів лабораторної роботи №8')
p('Модель, імпортер та повний граф уже створено в лабораторній роботі №8. Надалі позначення «ЛР08» стосується звіту Шевчука М. В. «Збереження знань у графовій базі даних для візуалізації енергетичних даних», 2026, 20 с. Повторний опис цих частин замінено посиланнями на його розділи та сторінки.')
p('Нові обчислення виконано локально: Neo4j Community 5.26.32, Python 3.11.6, драйвер neo4j 5.28.2, RDFLib 7.1.4. Чотири нові результати додатково підтверджено скриншотами Neo4j Sandbox. Часові вимірювання нижче належать локальному запуску ЛР09, а не попередньому Sandbox-запуску ЛР08.')

page('1 Модель графа та обмеження')
p('Правила відображення OWL у граф наведено в ЛР08, розд. 2, с. 3; структуру класів та індивідів — у розд. 4–7, с. 5–8. Модель використано повторно. Її зв’язок TYPE_OF відповідає INSTANCE_OF із прикладу поточного завдання.')
p('Обмеження Lab8Entity.id та індекси описано в ЛР08, розд. 10, с. 11. Додатковий SHOW CONSTRAINTS підтвердив унікальність id у Sandbox (рис. 1). Назва її типу тут — NODE_PROPERTY_UNIQUENESS; локально Neo4j повертає UNIQUENESS.')
fig('01_constraints.png', 'Обмеження унікальності id у Neo4j Sandbox')
h('2 Ідемпотентний імпорт')
p('Пакетний MERGE повторно використано з ЛР08, розд. 3, с. 4, додаток А, с. 15–16. Новий локальний повтор підтвердив сталість лічильників: створено 0 нових вузлів і 0 ребер (табл. 1).')
table('Таблиця 1 — Контроль джерела та проєкції', ['Показник', 'Результат'], [
    ['Початкові RDF-трійки', '993; Turtle ізоморфний OWL'],
    ['Класи / початкові індивіди', '37 / 26; ID збігаються'],
    ['Повний граф після двох імпортів', '43 746 вузлів / 199 287 ребер'],
], [10.4, 7.6])
p('Групи міток і типів ребер збігаються з джерелом. Число RDF-трійок не дорівнює числу ребер: частина значень стає властивостями; часові дані ЛР01 розширюють граф.')

page('3 Запити Cypher')
p('Базові 11 сценаріїв ЛР08 наведено в її розд. 8, с. 9, та додатку В, с. 19–20. Нові запити доповнюють їх OPTIONAL MATCH, collect, обмеженням кількості рядків та аналізом шляхів. Тексти нових запитів подано в додатку А цього звіту; Q9 повторює Q8 ЛР08.')
table('Таблиця 2 — Питання та фактичні відповіді', ['Код', 'Питання', 'Результат'], [
    ['Q1', 'Які індивіди мають метрику?', '26 рядків; для 25 — null'],
    ['Q2', 'Які засоби обліку має об’єкт?', 'count = 2; meter, submeter'],
    ['Q3', 'Які найбільші прогнози понад поріг за добу?', '2,206241 та 1,951941 kWh'],
    ['Q4', 'Які всі предки класу прогнозу?', '3 предки; відстані 1, 2, 3'],
    ['Q5', 'Які нащадки DomainEntity?', '36 нащадків'],
    ['Q8', 'Які поняття мають найбільші ступені?', '5 класів; максимум 45'],
    ['Q9', 'Яка добова MAE прогнозів?', '4 прогнози; 0,429294 kWh'],
], [1.3, 9.5, 7.2])
p('Параметри: $householdId = "owl:household"; $start = "2009-09-09T00:00:00"; $end = "2009-09-10T00:00:00"; $threshold = 1,5613 kWh. Інтервал [start, end) не включає праву межу; час джерела не має UTC-зсуву.')
p('У Q1 збережено індивідів без метрики. Q2 повертає count і впорядкований collect. Q3 використовує WHERE, ORDER BY та LIMIT 5; оскільки умовам відповідають лише два прогнози, отримано два рядки. Q9 з avg використано з ЛР08 без повторного опису алгоритму.')
table('Таблиця 3 — Нові локальні плани PROFILE', ['Запит', 'DB Hits', 'Початковий доступ'], [
    ['Q3', str(PROFILES['03_top_high_forecasts']['db_hits_sum']), 'NodeIndexSeekByRange'],
    ['Q9', str(PROFILES['09_forecast_mae']['db_hits_sum']), 'NodeIndexSeekByRange'],
], [2.3, 3, 12.7])

page('4 Шляхи та аналіз графа')
h('4.1 Предки та нащадки класів', 2)
p('У ЛР08, розд. 4, с. 5, показано прямі зв’язки ієрархії. Новий Q4 обходить SUBCLASS_OF*1.. і повертає всіх предків HighConsumptionForecast, а не лише безпосереднього батька. Отримано ForecastResult на відстані 1, AnalysisResult — 2, DomainEntity — 3.')
p('Об’єднання повернених шляхів містить чотири вузли та три ребра, що підтверджує рис. 2. Q5 аналогічно знаходить 36 нащадків DomainEntity. Обидві відповіді звірено з незалежним обходом ієрархії з файлу relationships.json.')
fig('02_ancestors_graph.png', 'Усі предки HighConsumptionForecast у Sandbox')
p('Відсутність верхньої межі довжини тут не створює невизначеності: збережена ієрархія містить 37 класів і 36 ребер. Запит відновлює явно задані шляхи цієї моделі; нове OWL-виведення він не запускає.')

page('4.2 Найкоротші шляхи')
p('Q6 шукає shortestPath між owl:analyst та owl:kWh у підграфі 26 початкових індивідів за предметними відношеннями. Напрямок ребер під час обходу не обмежується. Мінімальна довжина — 4 ребра.')
fig('03_shortest_path.png', 'Найкоротший шлях у підграфі початкових індивідів')
p('На рис. 3 аналітик переглядає графік, графік відображає ряд, ряд містить вимірювання, а вимірювання має одиницю kWh: VIEWS → DISPLAYS_SERIES → HAS_MEASUREMENT → HAS_UNIT. ID вимірювання в кадрі не видно, тому конкретну годину не встановлювали.')
p('Локально отримано інший рівнозначний маршрут: analyst → lineChart → household ← targetMeasurement → kWh. Незалежний пошук у ширину також дав довжину 4.')
p('У повному графі Q11 знаходить 2 ребра TYPE_OF: analyst → DomainEntity ← kWh. Цей шлях відображає спільний клас. Довжина 4 стосується лише визначеного предметного підграфа.')
p('03N90 Cartesian product — інформаційна нотифікація: два кінці вибрано за унікальними id, тобто поєднується одна пара вузлів. Запит повернув один запис.')

page('4.3 Ступені вузлів та найбільш зв’язані поняття')
p('Ступінь визначено як число інцидентних ребер усіх типів, без обмеження напрямку. Це не кількість різних сусідів. Q8 обмежує початкову множину вузлами OntologyClass; результати на рис. 4 збігаються з незалежним підрахунком за файлом ребер.')
fig('04_top5_concepts.png', 'Топ-5 онтологічних понять за ступенем у Sandbox')
p('Найбільш зв’язаний клас — DomainEntity, ступінь 45; далі Visualization — 19, TimeSeries — 16, Measurement — 15, AnalysisResult — 13. Показник включає не лише SUBCLASS_OF, а й зв’язки типізації, domain/range, що інцидентні класу.')
table('Таблиця 4 — Топ-5 вузлів у повному графі за Q7', ['Вузол', 'Ступінь'], [
    [r['id'], str(r['degree'])] for r in ANS['07_top5_graph_degree']['rows']
], [13, 5])
p('На рівні всього графа переважають часовий ряд і спільні контекстні сутності вимірювань. Тому топ вузлів повної вибірки та топ онтологічних класів відповідають різним питанням.')

page('5 Порівняння SPARQL та Cypher')
h('5.1 Однакові питання та збіг відповідей', 2)
p('Питання SPARQL із ЛР05 доповнено еквівалентами Cypher у ЛР09 (додаток Б). Онтологію ЛР06 і її графову проєкцію взято з матеріалів ЛР08.')
p('Порівнюються ті самі 26 початкових індивідів. RDF має 993 початкові трійки, а зі збереженими фактами HermiT і належністю до надкласів — 1335. Це узгоджено з матеріалізованими типами й відношеннями Neo4j; нового запуску reasoner не було.')
table('Таблиця 5 — Парні питання та узгоджені відповіді', ['Пара', 'Питання', 'Результат обох мов'], [
    ['C1', 'Які засоби обліку належать домогосподарству?', 'meter, submeter; 2 рядки'],
    ['C2', 'Які модель, прогноз і метрика пов’язані між собою?', 'forecast → regressor; 1 рядок'],
    ['C3', 'Які подання мають тип ForecastVisualization?', 'forecastChart; 1 рядок'],
], [2, 9, 7])
p('У C2 прогноз дорівнює 1,9519405504171758 kWh; MAE — 0,3359660136113589 kWh для всіх 9530 тестових прогнозів ЛР01 за 09.09.2009–26.11.2010. Ця MAE має інше охоплення, ніж добові чотири прогнози Q9.')
p('Відповіді збігаються за IRI, значеннями й кількістю рядків; допуск для чисел — 10⁻⁹. Без збережених висновків C2 і C3 у RDF повертають 0 рядків. SPARQL сам не запускає OWL reasoner.')
h('5.2 Методика вимірювання', 2)
p('Для кожної пари й рушія виконано 3 прогріви та 10 повторів із чергуванням порядку. Вимірювали виконання й повне отримання відповіді в Python. Читання графа, prepareQuery, перші виконання та PROFILE виключено.')

page('5.3 Час виконання та вибір подання знань')
table('Таблиця 6 — Медіани локального часу за 10 повторами', ['Пара', 'SPARQL, ms', 'Cypher, ms', 'Рядків'], [
    [key[:2], n(value['sparql']['median_wall_ms']), n(value['cypher']['median_wall_ms']), str(len(value['sparql_rows']))]
    for key, value in COMP.items()
], [2, 5.5, 5.5, 5])
p('SPARQL виконується в RDFLib у процесі Python, Cypher — у Neo4j через Bolt. RDF містить аксіоми та збережені висновки; Neo4j — також повні часові дані. Через різні накладні витрати й фізичні обсяги ці часи характеризують лише наведені реалізації.')
p('Сирі 60 повторів збережено в language_samples.csv, відповіді й статистики — у language_comparison.json запуску local_20261016T190455229366Z. В усіх повторах відповіді залишалися еквівалентними.')
h('Читабельність та виразність', 2)
p('У C1 обидва записи короткі: hasMeter відповідає HAS_METER. У C2 SPARQL описує дані трійками, Cypher — шаблонами ребер і властивостями. Перший зручний для IRI та RDF-термів, другий наочно показує переходи. SPARQL 1.1 також підтримує property paths.')
h('Семантика та рекомендація', 2)
p('Обмеження проєкції OWL описано в ЛР08, розд. 2, с. 3. У C3 тип ForecastVisualization доступний завдяки збереженому висновку; для нових даних його слід актуалізувати окремо. Автоматичного виконання всіх OWL-аксіом у цій проєкції немає.')
p('Для контексту вимірювань, походження прогнозів та обходів доцільна Neo4j. OWL/RDF варто залишити джерелом семантичної моделі й обміну; перевірку узгодженості та нове виведення виконувати reasoner окремо. Це відповідає структурі застосунку.')

page('Відтворення та використання ШІ')
p('README містить версії, порядок запуску й поділ середовищ. Джерела ЛР08 збережено без змін із SHA-256. Онтологія представлена в ontology_asserted.ttl та ontology_semantic.ttl. Випадкова генерація не використовується; seed не потрібен.')
p('Запуск run_lab9.py без --import-data читає наявний граф. Для нової бази --import-data виконує імпорт через MERGE двічі та перевіряє сталість лічильників. Облікові дані вводяться інтерактивно й у файли результатів не записуються. Основні алгоритми порівняння наведено в додатку В; імпортер повторно використано з ЛР08, додаток А, с. 15–16.')
h('Декларація використання ШІ', 2)
p('Використано OpenAI Codex для звірки завдань і результатів ЛР08, підготовки нових запитів, скриптів порівняння та оформлення звіту. Основні запити: доповнити ЛР08 до вимог ЛР09 із збереженням результатів; створити звіт і посилатися на ЛР08 для вже описаних частин.')
p('Результати перевірено запусками Neo4j та RDFLib, звіркою ID, незалежним розрахунком шляхів і ступенів, повторним імпортом та порівнянням відповідей. Локально пройдено 21 перевірку. Чотири оригінальні кадри отримано з Sandbox користувача; вони підтверджують показані результати, а не новий повний віддалений бенчмарк.')
h('Висновок')
p('Доповнено граф ЛР08 новими запитами Cypher. Знайдено 3 предки HighConsumptionForecast, 36 нащадків DomainEntity та найкоротші шляхи з урахуванням обраного підграфа; топ-5 класів підтверджено в Sandbox. Три пари SPARQL/Cypher дали однакові відповіді. Модель, імпорт та індекси використано з ЛР08 за наведеними посиланнями; нові вимірювання характеризують локальні реалізації.')

page('Додаток А Нові запити Cypher')
p('queries/*.cypher', indent=False).runs[0].bold = True
p('Нумерація Q1–Q11 відповідає номерам файлів у queries/. Повторно використаний Q9 наведено в ЛР08, додаток В, с. 20, тому його лістинг тут не дублюється.')
query('01_optional_metric', 'Q1')
query('02_collect_meters', 'Q2')

page('Додаток А Нові запити Cypher продовження')
query('03_top_high_forecasts', 'Q3')
query('04_ancestors', 'Q4')
query('05_descendants', 'Q5')

page('Додаток А Найкоротші шляхи')
query('06_shortest_path', 'Q6')
query('11_shortest_full_graph', 'Q11')

page('Додаток А Ступені вузлів та підграф')
query('07_top5_graph_degree', 'Q7')
query('08_top5_class_degree', 'Q8')
query('10_ancestor_graph', 'Q10')

page('Додаток Б Парні запити SPARQL та Cypher')
for key in ['C1_household_meters', 'C3_inferred_visualization']:
    pair = PAIRS[key]
    h(key[:2] + ' ' + pair['question'], 2)
    p('comparison/' + key + '.rq', indent=False).runs[0].bold = True
    code(format_query(pair['sparql']))
    p('comparison/' + key + '.cypher', indent=False, before=4).runs[0].bold = True
    code(format_query(pair['cypher']) + ';')

page('Додаток Б Походження прогнозу та метрика')
pair = PAIRS['C2_forecast_provenance']
h('C2 ' + pair['question'], 2)
p('comparison/C2_forecast_provenance.rq', indent=False).runs[0].bold = True
code(format_query(pair['sparql']))
p('comparison/C2_forecast_provenance.cypher', indent=False, before=6).runs[0].bold = True
code(format_query(pair['cypher']) + ';')
p('IRI в обох відповідях порівнюються повністю. Префікс energy позначає https://example.org/lnu/energy-visualization#. Числові RDF-літерали value і mae перед зіставленням перетворюються на числа; їхні початкові RDF-терми збережені окремо.')

page('Додаток В Виконання та вимірювання SPARQL')
p('run_lab9.py — основні фрагменти нового порівняння', indent=False).runs[0].bold = True
source = (ROOT / 'run_lab9.py').read_text(encoding='utf-8')
tree = ast.parse(source)
function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'sparql_run')
lines = source.splitlines()
code('\n'.join(lines[function.lineno - 1:function.end_lineno]))
h('Чергування порядку та контроль незмінності відповіді', 2)
compare = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'compare_languages')
loop = next(x for x in ast.walk(compare) if isinstance(x, ast.For)
            and isinstance(x.target, ast.Name) and x.target.id == 'iteration')
code(textwrap.dedent('\n'.join(lines[loop.lineno - 1:loop.end_lineno])))

WORK.mkdir(parents=True, exist_ok=True)
doc.save(WORK / 'report_raw.docx')
(WORK / 'build_manifest.json').write_text(json.dumps({
    'source_run': RUN, 'figures': figures, 'planned_pages': 17,
    'source_report8': 'D:/LNU/DS/9/inherited/lab8/Звіт_Лабораторна_8_Neo4j_Енергетика.pdf',
    'previous_work_referenced_instead_of_repeated': True,
    'raw_docx': str(WORK / 'report_raw.docx'), 'final_stem': STEM,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('Built', WORK / 'report_raw.docx')
