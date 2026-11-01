from pathlib import Path
import json, textwrap, ast, copy, hashlib, re
from xml.sax.saxutils import escape
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image as RLImage, PageBreak, Spacer, Preformatted, KeepTogether, Flowable
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

WORK=Path(__file__).resolve().parent
ROOT=WORK.parent.parent
STEM='Звіт_Лабораторна_8_Neo4j_Енергетика'
REF=Path('D:/LNU/DS/5/Звіт_Лабораторна_5_Онтологія_Енергетика.docx')
REFERENCE_HASH=hashlib.sha256(REF.read_bytes()).hexdigest()
RUN=ROOT/'results/sandbox_20261016T054342525797Z'
V=json.loads((RUN/'validation.json').read_text(encoding='utf-8'))
Q=json.loads((RUN/'query_results.json').read_text(encoding='utf-8'))
B=json.loads((RUN/'benchmark_comparison.json').read_text(encoding='utf-8'))
BUILD=json.loads((ROOT/'results/build_validation.json').read_text(encoding='utf-8'))
assert V['status']=='passed' and all(V['checks'].values())
F=Path('C:/Windows/Fonts')
for name,file in [('TNR','times.ttf'),('TNRB','timesbd.ttf'),('CONS','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(F/file)))
pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNRB',italic='TNR',boldItalic='TNRB')
pages=[]
figures=[]
def page(*items): pages.append(items)
def h(t): return ('h',t)
def p(t): return ('p',t)
def table(title,headers,rows,widths): return ('table',title,headers,rows,widths)
def code(t): return ('code',t)
def screen(name,caption,width=180,box=None):
    figures.append((name,caption))
    path=ROOT/'results/screenshots'/name
    if box:
        # Materialize the document viewport so Word and previews show the same crop.
        # The original evidence image remains unchanged in results/screenshots.
        target=WORK/'cropped_figures'/name
        target.parent.mkdir(exist_ok=True)
        with Image.open(path) as original:
            original.crop(box).save(target)
        path=target
    return ('screen',str(path),caption,width,None)
def num(x,n=3): return f'{x:.{n}f}'.replace('.',',')

page(h('Тема та мета роботи'),
 p('Тема — збереження знань візуалізації енергетичних даних у графовій базі Neo4j. Мета — перетворити онтологію попередніх робіт на графову структуру, імпортувати поняття й фактичні дані, розробити запити та перевірити ефект індексації.'),
 h('Завдання'),
 p('1. Ознайомитися з графовими базами даних і підключитися до Neo4j.\n2. Визначити вузли, властивості та зв’язки для онтології.\n3. Підготувати JSON/CSV і виконати імпорт через Cypher.\n4. Перевірити повноту даних і візуалізувати графові запити.\n5. Створити індекси та виміряти продуктивність складних запитів.'),
 h('1 Предметна область та середовище'),
 p('Тематичний напрям роботи — енергетика, програмне забезпечення та візуалізація. Предметна область охоплює вимірювання електроспоживання, їх часову організацію, аналітичні результати й графічні подання. Основою є семантична онтологія лабораторної №6.'),
 p('Роботу виконано у Neo4j Sandbox через Neo4j Browser та офіційний Python-драйвер. Віддалений сервер — Neo4j Enterprise 2026.04.0, клієнт — Python 3.11.6 і neo4j 5.28.2. Перетворення OWL виконано RDFLib 7.1.4. Усі наведені основні вимірювання отримано у Sandbox.'))

page(h('2 Перетворення онтології на граф'),
 p('У property graph вузли та зв’язки мають властивості, а мітки визначають прикладний тип вузла. Створено вузли класів, визначення властивостей, індивіди й записи фактичних даних. Правила відображення наведено в табл. 1.'),
 table('Таблиця 1 — Відображення знань у Neo4j',['Джерело','Подання у графі'],[
 ['Клас OWL','Вузол OntologyClass з IRI та name'],
 ['Ієрархія класів','Зв’язок SUBCLASS_OF'],
 ['Індивід OWL','Вузол OntologyIndividual з предметними мітками'],
 ['Тип індивіда','Мітка класу та зв’язок TYPE_OF'],
 ['Об’єктна властивість','Спрямований зв’язок із provenance та IRI'],
 ['Властивість даних','Число, bool, рядок або localdatetime'],
 ['Визначення властивості','Вузол OntologyProperty; DOMAIN і RANGE'],
 ['Година / прогноз ЛР1','Вузол Lab8Observation / Lab8Forecast'],
 ],[62,118]),
 p('Вихідна онтологія містить 37 класів, 31 об’єктну властивість, 34 властивості даних і 26 індивідів. Їх доповнено 34 085 повними годинами та 9 530 прогнозами з першої роботи. Нове навчання моделей не виконувалося.'),
 p('Висновки HermiT із №6 перенесено як матеріалізовані факти. Neo4j не виконує OWL-виведення автоматично: кардинальності та несумісність класів не стали обмеженнями Cypher. Повний OWL і 993 вихідні RDF-трійки збережено окремо; відновлений RDF-граф ізоморфний джерелу.'))

page(h('3 Підготовка даних та імпорт'),
 p('Підготовлено nodes.json і relationships.json, а також CSV-подання. Кожен вузол має спільну мітку Lab8Entity та унікальний id. Префікси class:, property:, owl:, data:, measurement: і forecast: розрізняють схему, приклади й повний масив. Час джерела без UTC-зсуву перетворено на localdatetime.'),
 p('Імпортер передає параметризовані списки пакетами до 1000 записів, створює вузли через MERGE, а потім зв’язує їх за id. Використано обмеження унікальності:'),
 code('CREATE CONSTRAINT lab8_entity_id IF NOT EXISTS\nFOR (n:Lab8Entity) REQUIRE n.id IS UNIQUE;'),
 p('Після імпорту отримано 43 746 вузлів і 199 287 зв’язків. Результати контрольних запитів у браузері показано на рис. 1 і 2; вони збігаються з перевіркою імпортера.'),
 screen('11_node_count.png','Рис. 1 — Кількість вузлів повного графа',100,(30,135,465,238)),
 screen('12_relationship_count.png','Рис. 2 — Кількість зв’язків повного графа',100,(25,125,460,238)),
 p('Окремий локальний повтор імпорту підтвердив ідемпотентність: 0 нових вузлів і 0 нових зв’язків. Цей контроль не підміняє віддалений запуск; перевірка Sandbox має власні відповіді та журнали.'))

page(h('4 Класи та успадкування'),
 p('Ієрархію подано 37 вузлами OntologyClass та 36 зв’язками SUBCLASS_OF. Запит повертає шляхи від підкласів до батьківських класів; стрілки позначають напрям спеціалізації. Приклад відображення та властивості кореневого DomainEntity наведено на рис. 3.'),
 code('MATCH p=(c:Lab8Entity:OntologyClass)\n  -[:SUBCLASS_OF]->\n  (parent:Lab8Entity:OntologyClass)\nRETURN p;'),
 screen('03_class_hierarchy.png','Рис. 3 — Ієрархія класів і властивості DomainEntity',180,(530,200,1798,824)),
 p('Наприклад, Household спеціалізує ConsumptionObject, EnergyMeasurement — Measurement, а RegressionModel — AnalyticalModel. Мітки й зв’язки TYPE_OF зберігають типи початкових індивідів, включно з відомими висновками та успадкуванням.'))

page(h('5 Граф онтологічних індивідів'),
 p('Візуалізовано 26 початкових індивідів із предметними відношеннями (рис. 4). До них належать домогосподарство, канали обліку, часові ряди, аналітична модель, прогноз, подання й користувач. Перегляд цього фрагмента дозволяє дослідити структуру без одночасного малювання всіх вимірювань.'),
 screen('04_ontology_individuals.png','Рис. 4 — Онтологічні індивіди та їхні зв’язки',180),
 p('Зв’язок ANALYZES_SERIES поєднує модель Random Forest із цільовим тестовим рядом (рис. 5). Цей ряд задає походження аналітичного результату; він не перелічує всі лагові ознаки, на яких модель навчалася у №1.'),
 screen('08_model_series.png','Рис. 5 — Модель і цільовий часовий ряд',110,(120,135,780,610)))

page(h('6 Походження прогнозу та семантика'),
 p('Запит від графіка прогнозу через PRESENTS_RESULT і GENERATED_BY відновлює ланцюжок «подання → результат → модель» (рис. 6). Подання має тип AttentionVisualization, а прогноз — HighConsumptionForecast; ці висновки отримано у №6 й збережено під час імпорту.'),
 screen('05_forecast_provenance_graph.png','Рис. 6 — Походження прогнозу Random Forest',95,(170,235,625,650)),
 p('Значення 1,9519405504171758 kWh перевищує навчальний поріг 1,5613 kWh. Табличний результат із типами показано на рис. 7. Це окреме правило числового прогнозу: мітка Logistic Regression для цього прикладу залишилася 0. Поріг не є технічною нормою безпеки.'),
 screen('06_forecast_semantic_table.png','Рис. 7 — Числовий прогноз і матеріалізовані типи',180,(330,197,1298,420)))

page(h('7 Контекст реального вимірювання'),
 p('Для вимірювання за 09.09.2009 о 20:00 відновлено чотири контекстні зв’язки: MEASUREMENT_OF, RECORDED_BY, OBSERVES_INDICATOR та HAS_UNIT. На рис. 8 показано вимірювання, домогосподарство, канал загального споживання, показник енергії та одиницю kWh.'),
 screen('07_measurement_context.png','Рис. 8 — Контекст одного годинного вимірювання',110,(155,175,655,650)),
 code("MATCH (m:Lab8Entity {\n  id:'measurement:2009-09-09T20:00:00'})\n  -[r:MEASUREMENT_OF|RECORDED_BY|HAS_UNIT|\n       OBSERVES_INDICATOR]->(n:Lab8Entity)\nRETURN m,r,n;"),
 p('Енергія цього інтервалу становить 2,12 kWh. numericValue зберігає енергію, а activePowerKw — середню активну потужність. Одиниці цих величин розрізняються. Початкові чотири приклади OWL мають окремі id; запити повної вибірки використовують Lab8Observation, тому приклади не подвоюють суму енергії.'))

page(h('8 Запити для отримання знань'),
 p('Підготовлено й виконано 11 сценаріїв. Часові запити використовують інтервал [start, end); основний приклад — 09.09.2009. Каталог і фактичні відповіді подано у табл. 2. Повні результати збережено в query_results.json.'),
 table('Таблиця 2 — Запити та результати',['№','Призначення','Результат'],[
 ['Q1','Кількість вузлів','43 746'],
 ['Q2','Ієрархія класів','36 шляхів успадкування'],
 ['Q3','Домогосподарство → засоби обліку','2 шляхи'],
 ['Q4','Подання → прогноз → модель','1 шлях, 1,951941 kWh'],
 ['Q5','Годинні виміри за добу','24 записи'],
 ['Q6','Прогнози вище 1,5613 kWh','2 записи'],
 ['Q7','Добова енергія та об’єкт','24 год; 25,355733 kWh'],
 ['Q8','Похибки добових прогнозів','4 прогнози; MAE 0,429294'],
 ['Q9','Прогноз → факт → об’єкт','2 високі прогнози'],
 ['Q10','Контекст одного вимірювання','5 вузлів; 4 зв’язки'],
 ['Q11','MAE повної тестової вибірки','9 530 прогнозів'],
 ],[14,95,71]),
 p('Чотири прогнози в добовому прикладі відповідають початку тестового періоду ввечері 09.09.2009. Їх MAE не є оцінкою всієї тестової вибірки. У Q9 максимальна абсолютна похибка серед двох відібраних прогнозів становить 0,430059 kWh.'))

page(h('9 Контроль значень і повноти'),
 p('Похибку регресії повторно обчислено безпосередньо в Neo4j через зв’язок прогнозу з фактичним вимірюванням. Використано всі 9 530 збережених прогнозів. Відповідний запит і результат показано на рис. 9.'),
 screen('13_full_test_mae_repeat.png','Рис. 9 — MAE на повній тестовій вибірці',180),
 p('Середня абсолютна похибка визначається як MAE = (1/n) Σ |ŷᵢ − yᵢ|, де n — кількість прогнозів, ŷᵢ — прогноз, yᵢ — фактична енергія. Для Random Forest отримано 0,335966 kWh; для базового прогнозу незмінного навантаження — 0,423517 kWh. Результати збігаються з №1 в межах похибки обчислень.'),
 p('Ця перевірка підтверджує збереження значень та правильність зв’язування прогнозів із фактами, а не нове навчання моделі. Усі цільові мітки часу та actual_kwh перевірено за hourly_clean.csv.'),
 p('Повний часовий ряд має 502 відсутні години всередині його меж. Наявні 34 085 записів відповідають повним годинам; пропущені інтервали не заповнювалися. Дослідження стосується одного домогосподарства Франції з UCI, а не всієї енергосистеми.'))

index_rows=[['Lab8Entity.id','Унікальність і зв’язування MERGE'],['Lab8Entity.name','Пошук за назвою'],['Lab8Observation:\nobjectId, timestamp','Відбір об’єкта й інтервалу часу'],['Lab8Forecast.targetTime','Відбір прогнозів за часом']]
page(h('10 Індекси та доступ до даних'),
 p('Створено унікальне обмеження id та три додаткові range-індекси. Для перевірки стану виконано SHOW INDEXES і db.awaitIndexes(300). Усі чотири індекси lab8_* мають стан ONLINE; їхні призначення наведено в табл. 3.'),
 table('Таблиця 3 — Індексовані властивості',['Мітка та властивості','Призначення'],index_rows,[83,97]),
 screen('10_indexes_partial.png','Рис. 10 — Перегляд стану індексів у Neo4j Browser',180),
 p('На рис. 10 видно верхню частину таблиці. Повний стан часових індексів підтверджено indexes.json із того самого запуску. Композитний індекс прискорює початковий пошук за objectId і timestamp; індекс targetTime — пошук потрібного діапазону прогнозів.'))

perf_rows=[]
volume_rows=[]
for key,label in [('07_daily_energy','Q7'),('08_forecast_errors','Q8'),('09_forecast_paths','Q9')]:
    a,b=B[key]['before'],B[key]['after']
    perf_rows.append([label,num(a['median_wall_ms']),num(b['median_wall_ms']),str(a['db_hits_sum']),str(b['db_hits_sum'])])
    volume_rows.append([label,str(a['returned_rows']),str(a['json_utf8_bytes']),num(a['p95_wall_ms']),num(b['p95_wall_ms'])])
page(h('11 Тестування продуктивності'),
 p('На одному повному графі порівняно Q7, Q8 та Q9 до й після додавання пошукових індексів. Обмеження id існувало в обох умовах. Кожен сценарій прогрівався тричі; далі виконано по 10 повторів із чергуванням порядку запитів. PROFILE запускався окремо. Відповіді до й після індексації еквівалентні.'),
 table('Таблиця 4 — Результати вимірювань у Sandbox',['Запит','Медіана до, ms','Медіана після, ms','DB Hits до','DB Hits після'],perf_rows,[19,40,41,40,40]),
 p('Для Q7 медіана зменшилася на 38,4%, для Q8 — на 5,9%. Для Q9 зміна з 123,897 до 124,034 ms означає практично однаковий час; прискорення не виявлено. DB Hits скоротилися в усіх трьох сценаріях.'),
 table('Таблиця 5 — Повернені дані та варіація часу',['Запит','Рядків','JSON, байт','P95 до, ms','P95 після, ms'],volume_rows,[19,25,42,47,47]),
 p('wall_ms охоплює виконання, мережевий обмін, отримання й серіалізацію результату. Значна варіація повторів обмежує висновки про невеликий виграш. JSON-байти — обсяг серіалізованої відповіді, а DB Hits — звернення рушія; це не точні мережеві байти або дисковий I/O.'))

profile_rows=[]
for stage,label in [('before','До'),('after','Після')]:
    raw=json.loads((RUN/(stage+'_profiles.json')).read_text(encoding='utf-8'))['07_daily_energy']['plan']
    pending=[raw]
    while pending:
        item=pending.pop()
        profile_rows.append([label,item['operatorType'].split('@')[0],str(item.get('rows',0)),str(item.get('dbHits',0))])
        pending.extend(reversed(item.get('children',[])))
page(h('12 Аналіз планів виконання'),
 p('Збережені PROFILE-плани показують зміну початкового доступу з NodeByLabelScan на NodeIndexSeek або NodeIndexSeekByRange. У табл. 6 наведено фактичні оператори Q7 з before_profiles.json та after_profiles.json. Це подання виміряного плану, а не скриншот інтерфейсу.'),
 table('Таблиця 6 — Оператори плану Q7',['Умова','Оператор','Rows','DB Hits'],profile_rows,[24,96,25,35]),
 p('До індексації скануються 34 085 вузлів вимірювань. Після індексації початковий пошук повертає 24 потрібні години. Сума DB Hits плану зменшилася зі 102 400 до 217. Для Q8 і Q9 використано NodeIndexSeekByRange за targetTime.'),
 p('Ранні часові фільтри зменшують подальшу роботу переходів графом. Повернення одного агрегованого рядка в усіх умовах дозволяє порівнювати однакові результати; менша кількість DB Hits не гарантує пропорційного зменшення загального клієнтського часу.'))

page(h('13 Перевірка реалізації'),
 p('Віддалений запуск завершився статусом passed. Перевірено кількість вузлів і кожного типу зв’язків, збіг усіх прогнозів із фактами, добову суму енергії, MAE, семантичні типи та рівність відповідей до/після індексів. JSON/CSV і джерела мають контрольні суми; збережено всі повтори та сирі плани.'),
 p('Повні результати містяться в results/sandbox_20261016T054342525797Z. Оригінали 13 зображень Neo4j Browser збережено без редагування. Для звіту використано репрезентативні фрагменти; непоказані в кадрі деталі підтверджуються структурованими файлами.'),
 h('Висновок'),
 p('Перетворено семантичну онтологію енергетичних даних на граф Neo4j і виконано повний імпорт 43 746 вузлів та 199 287 зв’язків. Запити відновлюють ієрархію класів, контекст вимірювання, походження прогнозу й відомі семантичні типи. Повторний розрахунок MAE на 9 530 прогнозах підтвердив збереження результатів першої роботи.'),
 p('Індекси істотно зменшили обсяг роботи рушія. Для добової агрегації медіана часу зменшилася на 38,4%; для пошуку шляхів прогнозів прискорення за часом не виявлено. Отже, ефект оптимізації слід оцінювати за планами, DB Hits і повторними вимірюваннями, враховуючи мережеві витрати. Повна OWL-семантика залишається у вихідній онтології; у Neo4j зберігається її прикладна проєкція.'))

# Keep the complete individual graph on one page; its provenance is shown in the next section.
pages[4]=pages[4][:3]+(p('Зв’язок ANALYZES_SERIES поєднує Random Forest із цільовим тестовим рядом. Він задає походження результату, а не повний перелік лагових ознак моделі першої роботи.'),)
def renumber_figures(text):
    return re.sub(r'([Рр]ис\. )(\d+)',lambda m:m.group(1)+str(int(m.group(2))-1 if int(m.group(2))>5 else int(m.group(2))),text)
new_pages=[]
for items in pages:
    rewritten=[]
    for item in items:
        if item[0] in {'p','h'}:item=(item[0],renumber_figures(item[1]))
        elif item[0]=='screen':item=(item[0],item[1],renumber_figures(item[2]),*item[3:])
        rewritten.append(item)
    new_pages.append(tuple(rewritten))
pages=new_pages
figures=[(Path(item[1]).name,item[2]) for items in pages for item in items if item[0]=='screen']

# Relevant implementation excerpts; tests, setup and report helpers are omitted.
def function_source(file,name):
    source=(ROOT/file).read_text(encoding='utf-8-sig')
    tree=ast.parse(source)
    match=next(node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name)
    return '\n'.join(source.splitlines()[match.lineno-1:match.end_lineno])

def visual_length(line):
    return max(1,len(textwrap.wrap(line,width=68,break_long_words=True,break_on_hyphens=False)))

def appendix(title,filename,blocks):
    # Small blocks preserve original line boundaries; automatic visual wraps do not change source text.
    chunk=[]; lines=0; first=True
    def flush():
        nonlocal chunk,lines,first
        if not chunk:return
        page(h(title if first else title+' — продовження'),
             (h(filename) if first else p('Продовження лістингу')),code('\n'.join(chunk)))
        first=False;chunk=[];lines=0
    for block in blocks:
        raw=block.splitlines()
        for line in raw:
            size=visual_length(line)
            if lines+size>38:flush()
            chunk.append(line);lines+=size
        if lines+1>38:flush()
        chunk.append('');lines+=1
    flush()

appendix('Додаток А Основні функції імпорту','build_lab8.py та run_neo4j.py — фрагменти реалізації',[
    function_source('build_lab8.py','node_statement'),
    function_source('build_lab8.py','edge_statement'),
    function_source('run_neo4j.py','import_graph')])
appendix('Додаток Б Вимірювання продуктивності','run_neo4j.py — отримання відповідей, PROFILE та повторні вимірювання',[
    function_source('run_neo4j.py','run'),function_source('run_neo4j.py','plan_totals'),function_source('run_neo4j.py','measure')])
cypher_blocks=[(ROOT/'cypher/00_constraint.cypher').read_text(encoding='utf-8').strip(),
               (ROOT/'cypher/10_indexes.cypher').read_text(encoding='utf-8').strip()]
for filename in ['02_ontology_graph.cypher','04_semantic_forecast.cypher','07_daily_energy.cypher','08_forecast_errors.cypher','09_forecast_paths.cypher','11_all_test_mae.cypher']:
    query=(ROOT/'queries'/filename).read_text(encoding='utf-8').strip()
    # Insert legal Cypher whitespace between complete pattern and clause tokens.
    for keyword in [' MATCH ', ' WHERE ', ' RETURN ', ' ORDER BY ', ' AND ']:
        query=query.replace(keyword,'\n'+keyword.strip()+' ')
    query=query.replace(')-[',')\n  -[').replace(']->(',']->\n  (')
    cypher_blocks.append('// '+filename+'\n'+query)
appendix('Додаток В Запити Cypher','Обмеження, індекси й основні запити; параметри start, end, objectId та threshold задає клієнт',cypher_blocks)

# Reuse the approved report's style package and document components.
engine=Path('D:/LNU/DS/5/work/report/build_report.py').read_text(encoding='utf-8')
engine=engine[engine.index('# DOCX:'):]
engine=engine.replace('лабораторної роботи №5','лабораторної роботи №8')
engine=engine.replace('«Побудова онтології для бази знань\\nвізуалізації енергетичних даних»','«Збереження знань у графовій базі даних\\nдля візуалізації енергетичних даних»')
engine=engine.replace("center('«Побудова онтології для бази знань',", "center('«Збереження знань у графовій базі даних',")
engine=engine.replace("center('візуалізації енергетичних даних»',", "center('для візуалізації енергетичних даних»',")
engine=engine.replace("'Лабораторна робота №5 — Побудова онтології для бази знань'", "'Лабораторна робота №8 — Збереження знань у графовій базі даних'")
engine=engine.replace('оригінальний скриншот WebProtégé','оригінальний скриншот Neo4j Browser')
# Visually wrap listings without changing original source strings.
engine=engine.replace("text=item[1]\n            par=", "text=item[1]\n            par=")
engine=engine.replace("block=Table([[Preformatted(text,styles['code'])]]", "display='\\n'.join(textwrap.wrap(line,width=68,break_long_words=True,break_on_hyphens=False,subsequent_indent='    ') if line else [''] for line in []) if False else '\\n'.join('\\n'.join(textwrap.wrap(line,width=68,break_long_words=True,break_on_hyphens=False,subsequent_indent='    ')) if line else '' for line in text.splitlines())\n            block=Table([[Preformatted(display,styles['code'])]]")
engine=engine.replace('\\\\n','\\n')
exec(compile(engine,'approved_report_engine','exec'))
for par in doc.paragraphs[:14]:
    for run in par.runs:
        if '\\n' in run.text:run.text=run.text.replace('\\n','\n')
doc.save(ROOT/(STEM+'.docx'))
assert hashlib.sha256(REF.read_bytes()).hexdigest()==REFERENCE_HASH
(WORK/'reference_hash.json').write_text(json.dumps({'path':str(REF),'sha256':REFERENCE_HASH,'unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'figures.json').write_text(json.dumps(figures,ensure_ascii=False,indent=2),encoding='utf-8')
print('Body and appendices:',len(pages),'pages; figures:',len(figures))

