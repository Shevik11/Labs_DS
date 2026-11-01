from pathlib import Path
import json, textwrap, ast, copy, hashlib
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
STEM='Звіт_Лабораторна_5_Онтологія_Енергетика'
S=json.loads((ROOT/'ontology_structure.json').read_text(encoding='utf-8'))
V=json.loads((ROOT/'results/validation.json').read_text(encoding='utf-8'))
Q=json.loads((ROOT/'results/query_results.json').read_text(encoding='utf-8'))
assert V['status']=='passed' and V['check_count']==88 and len(Q)==8
REF=next(Path('D:/LNU/DS/4').glob('Звіт*.docx'))
F=Path('C:/Windows/Fonts')
for name,file in [('TNR','times.ttf'),('TNRB','timesbd.ttf'),('CONS','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(F/file)))
pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNRB',italic='TNR',boldItalic='TNRB')

def diagram(name,rows):
    width=1200; height=90+len(rows)*110
    im=Image.new('RGB',(width,height),'white'); d=ImageDraw.Draw(im)
    font=ImageFont.truetype(str(F/'times.ttf'),31)
    small=ImageFont.truetype(str(F/'times.ttf'),28)
    for i,(left,right) in enumerate(rows):
        y=40+i*110
        for x,w,t,col in [(15,410,left,'#EDF1F5'),(590,590,right,'#F2F2F2')]:
            d.rounded_rectangle((x,y,x+w,y+90),radius=8,fill=col,outline='#606060',width=2)
            lines=t.split('\n'); step=35
            for j,line in enumerate(lines):
                ft=font if len(line)<37 else small
                d.text((x+w/2,y+45+(j-(len(lines)-1)/2)*step),line,font=ft,fill='black',anchor='mm')
        d.line((585,y+45,430,y+45),fill='black',width=3)
        d.polygon([(430,y+45),(447,y+37),(447,y+53)],fill='black')
    im.save(WORK/name)

diagram('hierarchy.png',[
 ('Об’єкт споживання','Домогосподарство'),('Засіб обліку','Підлічильник'),
 ('Вимірювання','Вимірювання енергії'),('Користувач','Аналітик'),
 ('Візуалізація','Лінійний графік; теплова карта;\nвізуалізація прогнозу'),
 ('Результат аналізу','Прогноз; результат класифікації;\nрезультат кластеризації'),
 ('Аналітична модель','Регресійна; класифікаційна;\nкластеризаційна модель')])

def inference_diagram():
    im=Image.new('RGB',(1200,520),'white'); d=ImageDraw.Draw(im)
    ft=ImageFont.truetype(str(F/'times.ttf'),32)
    for x,y,w,h,t in [(30,25,480,110,'forecast\nекземпляр ForecastResult'),(690,25,480,110,'forecastChart\nекземпляр LineChart'),(690,345,480,110,'forecastChart\nекземпляр ForecastVisualization')]:
        d.rounded_rectangle((x,y,x+w,y+h),8,fill='#F2F2F2',outline='black',width=2)
        d.multiline_text((x+w/2,y+h/2),t,font=ft,fill='black',anchor='mm',align='center',spacing=7)
    d.line((515,80,682,80),fill='black',width=3); d.polygon([(682,80),(665,72),(665,88)],fill='black')
    d.text((600,160),'presentedIn',font=ft,fill='black',anchor='mm')
    d.line((930,190,930,330),fill='black',width=3); d.polygon([(930,330),(922,313),(938,313)],fill='black')
    d.text((705,260),'HermiT',font=ft,fill='black',anchor='mm')
    d.multiline_text((35,300),'Обернений зв’язок:\npresentsResult\n\nВиведений тип →',font=ft,fill='black',spacing=10)
    im.save(WORK/'inference.png')
inference_diagram()

pages=[]
def page(*items): pages.append(items)
def h(t): return ('h',t)
def p(t): return ('p',t)
def table(title,headers,rows,widths): return ('table',title,headers,rows,widths)
def fig(name,caption,width=180): return ('fig',name,caption,width)
def screen(name,caption,width=180,box=None):
    path=ROOT/'results/webprotege_screenshots'/name
    if box:
        cropped=WORK/('panel_'+name)
        with Image.open(path) as original:
            original.crop(box).save(cropped)
        path=cropped
    return ('screen',str(path),caption,width,None)
def code(t): return ('code',t)

page(h('Тема та мета роботи'),
 p('Тема — побудова онтології для бази знань візуалізації енергетичних даних засобами програмного забезпечення. Мета — формалізувати поняття предметної області, їхні атрибути й відношення та перевірити придатність онтології до пошуку й логічного виведення.'),
 h('Завдання'),
 p('1. Розглянути інструменти створення онтологій.\n2. Визначити класи та їхні спеціалізації.\n3. Додати типізовані атрибути, зв’язки й обмеження.\n4. Створити екземпляри та перевірити онтологію.\n5. Зберегти графічну структуру й експорт у форматі OWL.'),
 h('1 Предметна область та інструменти'),
 p('Тематичний напрям роботи — енергетика, програмне забезпечення та візуалізація. Онтологія описує об’єкти споживання, вимірювання, аналітичні результати, графічні подання та дії користувача.'),
 p('За основу взято 16 понять і 20 напрямлених зв’язків лабораторної №3 та приклади спеціалізацій із таксономії №4. Тарифоутворення, будова електромереж і автоматичне керування обладнанням до меж моделі не входять.'),
 p('Protégé підтримує редагування OWL 2 і підключення HermiT; OWLGrEd подає онтології графічними діаграмами. Файл сформовано через RDFLib, імпортовано у WebProtégé, переглянуто в редакторі й повторно експортовано. Логічну перевірку HermiT виконано локально через Owlready2.'))

labels={c['id']:c['label'] for c in S['classes']}
base=list(S['lab3_mapping'].values())
page(h('2 Класи та ієрархія онтології'),
 p('Збережено всі 16 базових понять попередньої граф-моделі. Українські назви задано через rdfs:label, а сталі латинські ідентифікатори використано в OWL-аксіомах і запитах (табл. 1).'),
 table('Таблиця 1 — Базові класи предметної області',['Клас','Ідентифікатор OWL'],[[labels[n],n] for n in base],[88,92]),
 p('Загалом онтологія містить 31 клас: DomainEntity, 16 базових класів, 12 спеціалізацій, Unit та визначений клас ForecastVisualization. Базові класи є підкласами DomainEntity. Клас Unit задає одиницю вимірювання.'))

page(h('3 Спеціалізація понять'),
 p('На рис. 1 показано спеціалізації семи базових класів. Стрілка спрямована від підкласу до батьківського класу; кожна назва праворуч позначає окремий підклас.'),
 fig('hierarchy.png','Рис. 1 — Спеціалізації базових класів онтології'),
 p('Підлічильник, теплова карта та прогноз наступної години продовжують приклади розширення з лабораторної №4. Тепер це формальні відношення rdfs:subClassOf, які успадковують властивості й обмеження батьківських класів.'),
 p('Тематичні групи четвертої роботи збережено анотацією topicGroup. Наприклад, належність вимірювання до групи «Дані споживання» не перетворено на твердження, що вимірювання є різновидом набору даних.'))

attrs=S['data_properties']
rows=[]
for domain in ['DomainEntity']+base+['Unit','ForecastResult']:
    aa=[a for a in attrs if a['domain']==domain]
    if aa: rows.append([labels[domain], '\n'.join(a['id'] for a in aa), '\n'.join(a['datatype'] for a in aa)])
page(h('4 Атрибути та типи значень'),
 p('Визначено 34 властивості даних. Усі вони функціональні: один екземпляр має не більше одного значення кожного такого атрибута. identifier і name успадковуються всіма класами. Типи наведено з простору імен xsd.'),
 table('Таблиця 2 — Атрибути енергетичних об’єктів і даних',['Клас','Атрибут','Тип'],rows[:9],[51,85,44]),
 p('numericValue зберігає енергію десятковим числом, а timestamp — початок годинного інтервалу. Вимірювання прив’язане до окремого екземпляра одиниці через об’єктну властивість hasUnit. Так одиниця доступна для запиту як сутність онтології.'))
page(h('4 Атрибути та типи значень — продовження'),
 table('Таблиця 2 — Атрибути аналітики та взаємодії (продовження)',['Клас','Атрибут','Тип'],rows[9:],[51,85,44]),
 p('Часові мітки збережено без UTC-зсуву, оскільки його не задано в обраних вихідних рядках. recordCount, missingCount та stepMinutes описують підготовлений фрагмент даних, а не весь набір UCI.'),
 p('Загальний resultValue має рядковий тип, щоб подавати прогноз, клас або кластер. Для числового прогнозу додано спеціалізований forecastKwh типу decimal: його можна використовувати в числових умовах SPARQL.'))

relations=json.loads((ROOT/'inputs/model_lab3.json').read_text(encoding='utf-8'))['relations']
model_labels={k:labels[v] for k,v in S['lab3_mapping'].items()}
relrows=[[model_labels[r['source']],r['predicate'],model_labels[r['target']]] for r in relations]
page(h('5 Відношення між класами'),
 p('Онтологія має 28 об’єктних властивостей: 20 відношень із лабораторної №3, три додаткові предметні зв’язки та п’ять обернених. Для кожної задано domain і range. Основні відношення наведено в табл. 3.'),
 table('Таблиця 3 — Відношення енергетичних даних та подань',['Джерело','Відношення','Ціль'],relrows[:10],[61,58,61]),
 p('Для часового ряду додано seriesOf — об’єкт споживання та seriesIndicator — його показник. Властивість hasUnit пов’язує вимірювання з одиницею. Ці три зв’язки функціональні.'),
 p('Domain і range визначають типи учасників відношення та дають логічні наслідки типізації. Самі по собі вони не перевіряють, чи всі обов’язкові дані явно заповнені.'))
page(h('5 Відношення між класами — продовження'),
 table('Таблиця 3 — Відношення аналітики та взаємодії (продовження)',['Джерело','Відношення','Ціль'],relrows[10:],[61,58,61]),
 p('Задано п’ять пар обернених властивостей: hasMeter / installedAt, records / recordedBy, containsSeries / belongsToDataset, producesResult / generatedBy, presentedIn / presentsResult.'),
 p('Наприклад, із факту «meter records measurement1» reasoner виводить «measurement1 recordedBy meter». Зв’язок користувача з поданнями допускає кілька значень, а observesIndicator для вимірювання — не більше одного.'))

page(h('6 Формальні обмеження'),
 table('Таблиця 4 — Основні OWL-аксіоми та їх зміст',['Об’єкт обмеження','Зміст'],[
 ['DomainEntity','Рівно один identifier та name.'],
 ['Measurement','Рівно один timestamp, numericValue, qualityFlag, observesIndicator, recordedBy та hasUnit.'],
 ['TimeSeries','Рівно один seriesOf, seriesIndicator і coversInterval; існує щонайменше одне hasMeasurement.'],
 ['Dataset','Існує containsSeries із класу TimeSeries.'],
 ['Visualization','Існує displaysSeries із класу TimeSeries.'],
 ['ForecastResult','Існує generatedBy із класу RegressionModel; рівно один forecastKwh і targetTime.'],
 ['ForecastVisualization','Visualization і presentsResult some ForecastResult — необхідна й достатня умова належності класу.'],
 ['Несумісність класів','16 базових класів попарно несумісні; ForecastResult, ClassificationResult і ClusterResult також несумісні.']],[57,123]),
 p('Окремо задано AllDifferent для іменованих екземплярів. Це потрібно тому, що різні імена в OWL автоматично не означають різні сутності.'),
 p('За припущенням відкритого світу відсутнє явне значення може залишатися невідомим, навіть коли задано «рівно один». Тому логічну узгодженість і повноту записаних даних перевірено окремо.'))

page(h('7 Екземпляри та походження даних'),
 p('Створено 26 екземплярів. Числові приклади взято зі збережених результатів лабораторної №1. Назви користувача, подань, рішення та локальні ідентифікатори приладів є демонстраційними й позначені відповідними коментарями.'),
 table('Таблиця 5 — Три повні години з hourly_clean.csv',['Початок години','Енергія, кВт·год'],[['16.12.2006 18:00','3,632200'],['16.12.2006 19:00','3,400233'],['16.12.2006 20:00','3,268567']],[105,75]),
 p('Для прогнозу на 09.09.2009 20:00 використано перший рядок test_predictions.csv: фактичне значення — 2,12 кВт·год, прогноз Random Forest — 1,951941 кВт·год. Цей приклад має окремий часовий ряд і не змішується з фрагментом 2006 року.'),
 p('MAE = 0,335966 кВт·год узято з metrics.json і стосується 9530 тестових прогнозів ЛР1. Це не похибка одного наведеного спостереження. Числа в таблиці округлено для читання; повні значення збережено в OWL.'),
 p('На рис. 2 показано виведення типу для подання forecastChart. У початковому файлі воно має тип LineChart; HermiT додатково відносить його до ForecastVisualization.'),
 fig('inference.png','Рис. 2 — Виведення класу візуалізації прогнозу',165))

page(h('8 Запити до бази знань'),
 p('Виконано вісім SPARQL-сценаріїв на графі з виведеними фактами. Таблиця 6 містить фактичну кількість відповідей та їх зміст; тексти запитів і повні відповіді збережено окремими файлами.'),
 table('Таблиця 6 — Перевірені сценарії використання',['Сценарій','Відповіді та результат'],[
 ['Засоби обліку об’єкта','2: meter і submeter.'],
 ['Годинні значення енергії','3: значення та час із таблиці 5.'],
 ['Походження прогнозу','1: forecast, regressor, значення прогнозу, MAE і вибірка оцінювання.'],
 ['Візуалізація прогнозу','1: forecastChart за виведеним типом ForecastVisualization.'],
 ['Користувач та рішення','1: analyst, decision і lineChart, що підтримує рішення.'],
 ['Фільтри подань','1: відбір timestamp для lineChart.'],
 ['Енергія понад 3,4 кВт·год','2: measurement1 і measurement2.'],
 ['Горизонт завдання','1: регресія; прогноз на одну годину.']],[65,115]),
 p('Числовий поріг 3,4 кВт·год використано лише як демонстраційну умову запиту. Він не є порогом високого навантаження класифікатора ЛР1.'),
 p('Сталі ідентифікатори, типізовані значення та обернені властивості дозволяють знаходити походження результату й пов’язані подання без аналізу текстових описів. Перевірка показує придатність моделі для цих сценаріїв, але не є дослідженням зручності інтерфейсу за участю користувачів.'))

page(h('9 Перевірка коректності'),
 p('У перевіреному запуску успішно виконано 88 перевірок. Використано Python 3.11.6, RDFLib 7.6.0, Owlready2 0.51 і HermiT із Java 8. Підсумок записано у validation.json, а повідомлення reasoner — у журнали.'),
 table('Таблиця 7 — Результати перевірки',['Перевірка','Результат'],[
 ['Експорт RDF/XML і Turtle','Графи ізоморфні: обидва формати описують ту саму онтологію.'],
 ['Повнота структури','Збережено 16 понять; усі властивості мають domain і range.'],
 ['Основна онтологія','Узгоджена; нездійсненних іменованих класів не виявлено.'],
 ['Логічне виведення','Підтверджено recordedBy та тип ForecastVisualization для forecastChart.'],
 ['Запити','8 сценаріїв пройшли перевірку; вимірювання й прогноз звірено з джерелом.'],
 ['Несумісні класи','Копію, де household також має тип Meter, відхилено.'],
 ['Два числові значення','Додавання 999 як другого numericValue створило суперечність.'],
 ['Два різні показники','Друге, явно відмінне значення observesIndicator створило суперечність.'],
 ['Відсутнє явне значення','Вилучення numericValue не порушило OWL-узгодженість, але виявляється перевіркою повноти.']],[65,115]),
 p('Негативні сценарії виконано на окремих копіях. Основний файл онтології не містить навмисних суперечностей. Контроль повноти охоплює основні поля прикладу, порядок дат і кількість записів; це не універсальна перевірка всіх можливих даних.'))

page(h('10 Робота у WebProtégé'),
 p('Підготовлений OWL-файл імпортовано у вебпроєкт «5». На вкладці Classes розгорнуто дерево підкласів DomainEntity (рис. 3). Ієрархія містить спеціалізації вимірювань, моделей, результатів і візуалізацій, описані в розділах 2–3.'),
 screen('02_expanded_class_hierarchy.png','Рис. 3 — Ієрархія класів у WebProtégé',90),
 p('У картці Measurement перевірено батьківський клас DomainEntity, український підпис «Вимірювання» та тематичну анотацію «Дані споживання». Редактор відображає імпортовану структуру; перевірку повних OWL-аксіом виконано також за експортованим файлом.'))

page(h('10.1 Об’єктна властивість records'),
 p('Для records задано domain Meter і range Measurement (рис. 4). Отже, це відношення пов’язує лічильник із зареєстрованим вимірюванням.'),
 screen('04_records_domain_range.png','Рис. 4 — Налаштування властивості records',160,(581,62,1526,525)),
 p('Зв’язок читається як «лічильник реєструє вимірювання». Domain задає клас джерела — Meter, а range — клас цілі Measurement. За цим зв’язком reasoner може визначити типи його учасників.'))

page(h('10.2 Числовий атрибут numericValue'),
 p('Для numericValue визначено тип xsd:decimal і характеристику Functional (рис. 5).'),
 screen('05_numeric_value_datatype.png','Рис. 5 — Налаштування атрибута numericValue',160,(581,65,1527,600)),
 p('Функціональність означає, що одному вимірюванню відповідає не більше одного числового значення. Вимогу мати таке значення для кожного Measurement задає окрема OWL-кардинальність у класі; явну заповненість додатково перевірено програмно.'))

page(h('10.3 Екземпляр вимірювання'),
 p('На вкладці Individuals відкрито measurement1 (рис. 6). Екземпляр має тип EnergyMeasurement, одиницю kWh, показник energy та ознаку complete_hour. Час і числове значення збігаються зі збереженим прикладом лабораторної №1.'),
 screen('06_measurement1_values.png','Рис. 6 — Значення екземпляра measurement1',160,(581,62,1527,738)),
 p('За годину, що починається 16.12.2006 о 18:00, спожито 3,632200 кВт·год енергії. Значення округлено до шести знаків, як у табл. 5; повний десятковий запис збережено в онтології.'))

page(h('10.4 Екземпляр прогнозу'),
 p('Для екземпляра forecast перевірено тип ForecastResult, зв’язки з predictionSeries, mae та forecastChart (рис. 7). Числовий прогноз становить 1,9519405504171758 кВт·год для 09.09.2009 о 20:00.'),
 screen('07_forecast_values.png','Рис. 7 — Екземпляр forecast і його зв’язки у WebProtégé',180,(581,81,1527,851)),
 p('Після перегляду проєкт завантажено у форматі RDF/XML. Експорт зберіг 31 клас, 28 об’єктних властивостей, 34 атрибути, 26 екземплярів і всі обмеження. Локальна повторна перевірка HermiT підтвердила узгодженість; усі вісім запитів повернули ті самі відповіді.'))

page(h('11 Експорт та відтворення'),
 p('Основний результат — energy_ontology.owl у RDF/XML. Додатково збережено еквівалентний Turtle, структурований опис ontology_structure.json та редаговані схеми draw.io. Папки queries і results містять запити, відповіді та докази перевірки. Джерела прикладу й SHA-256 початкових файлів зафіксовано в inputs/lab1_sample.json.'),
 h('Висновок'),
 p('Побудовано формалізовану онтологію для варіанта «Енергетика / Програмне забезпечення / Візуалізація». Вона містить 31 клас, 28 об’єктних властивостей, 34 атрибути та 26 екземплярів і зберігає поняття попередніх лабораторних робіт.'),
 p('Перевірка HermiT підтвердила узгодженість моделі та виведення нових фактів. Вісім SPARQL-сценаріїв дали очікувані відповіді, а три суперечливі копії було відхилено. У WebProtégé переглянуто класи, властивості й екземпляри; повторний експорт зберіг модель. База знань придатна для перевірених сценаріїв пошуку вимірювань, прогнозу та подань.'))

source=(ROOT/'build_lab5.py').read_text(encoding='utf-8')
tree=ast.parse(source)
def function_code(name):
    n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return '\n'.join(source.splitlines()[n.lineno-1:n.end_lineno])
# Format exact function excerpts with Python's AST unparser, preserving semantics.
def formatted_fn(name):
    fn=ast.parse(function_code(name))
    if name=='restriction':
        result="""def restriction(class_, property_, kind, target):
    b = BNode()
    G.add((b, RDF.type, OWL.Restriction))
    G.add((b, OWL.onProperty, E[property_]))
    value = (
        Literal(target, datatype=XSD.nonNegativeInteger)
        if isinstance(target, int) else E[target]
    )
    G.add((b, OWL[kind], value))
    G.add((E[class_], RDFS.subClassOf, b))
    RESTRICTIONS.append(dict(
        class_id=class_, property=property_,
        kind=kind, value=target
    ))"""
        assert ast.dump(ast.parse(result),include_attributes=False)==ast.dump(fn,include_attributes=False)
        return result
    text=ast.unparse(fn)
    # wrap only long comma-separated calls via ast-compatible parenthesized continuation.
    out=[]
    for line in text.splitlines():
        if len(line)<=72: out.append(line); continue
        indent=len(line)-len(line.lstrip())
        # tokenize with Black unavailable: textwrap preserves tokens and line indentation,
        # and all long statements in these helpers are inside parentheses or a ternary.
        if ' if ' in line and ' else ' in line:
            lhs,rhs=line.split(' = ',1); out.append(lhs+' = (')
            out.extend(textwrap.wrap(rhs,68-indent,initial_indent=' '*(indent+4),subsequent_indent=' '*(indent+4),break_long_words=False,break_on_hyphens=False));out.append(' '*indent+')')
        else:
            # put the entire RHS or expression in an extra pair of parentheses
            if ' = ' in line:
                lhs,rhs=line.split(' = ',1); out.append(lhs+' = ('); val=rhs
            else: out.append(' '*indent+'('); val=line.strip()
            out.extend(textwrap.wrap(val,68-indent,initial_indent=' '*(indent+4),subsequent_indent=' '*(indent+4),break_long_words=False,break_on_hyphens=False));out.append(' '*indent+')')
    result='\n'.join(out)
    assert ast.dump(ast.parse(result),include_attributes=False)==ast.dump(fn,include_attributes=False)
    return result
page(h('Додаток А'),h('Фрагменти основної програми'),
 p('Наведено функцію створення OWL-обмежень із build_lab5.py. Повний код побудови онтології збережено в електронному пакеті лабораторної. Перенесення рядків у лістингу не змінює логіку програми.'),
 h('build_lab5.py — функція restriction'),code(formatted_fn('restriction')),
 p('Функція створює вузол owl:Restriction, задає властивість та вид обмеження й додає його як умову належності класу. Числові кратності зберігаються як xsd:nonNegativeInteger.'),
 h('Приклади застосування'),
 code("restriction(\n    'Measurement', 'numericValue', 'cardinality', 1\n)\nrestriction(\n    'TimeSeries', 'hasMeasurement',\n    'someValuesFrom', 'Measurement'\n)"))
page(h('Додаток Б'),h('Приклад запиту до онтології'),
 p('Запит 03_forecast_provenance.rq знаходить прогноз, модель, числове значення та метрику з описом вибірки. Властивість generatedBy доступна завдяки виведенню оберненого зв’язку producesResult.'),
 code('PREFIX energy:\n  <https://example.org/lnu/energy-visualization#>\n\nSELECT ?forecast ?model ?value ?mae ?scope\nWHERE {\n  ?forecast a energy:ForecastResult;\n    energy:generatedBy ?model;\n    energy:forecastKwh ?value;\n    energy:evaluatedBy ?metric .\n  ?metric energy:metricValue ?mae;\n    energy:evaluationScope ?scope\n}'),
 p('Фактична відповідь: forecast — forecast; model — regressor; value — 1,9519405504171758; mae — 0,3359660136113589; scope — 9530 тестових прогнозів ЛР1 за період 09.09.2009–26.11.2010.'),
 p('Усього запит повернув один рядок. Інші сім запитів та їхні результати доступні в електронному пакеті; службові перевірки до лістингу звіту не включено.'))

# DOCX: preserve the reference style package, replace its content and section geometry.
doc=Document(REF)
body=doc._element.body
sect=copy.deepcopy(doc.sections[0]._sectPr)
for el in list(body): body.remove(el)
body.append(sect)
sec=doc.sections[0]; sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.left_margin=Cm(2);sec.right_margin=Cm(1);sec.top_margin=Cm(2);sec.bottom_margin=Cm(2)
sec.different_first_page_header_footer=True
for name in ['Normal','Title','Heading 1','Heading 2','Caption']:
    st=doc.styles[name];st.font.name='Times New Roman';st.font.size=Pt(12 if name=='Caption' else 14);st.font.color.rgb=RGBColor(0,0,0)
    st.paragraph_format.space_before=Pt(0);st.paragraph_format.space_after=Pt(0)
normal=doc.styles['Normal'].paragraph_format;normal.line_spacing=1.5;normal.first_line_indent=Cm(1.25)
for header in [sec.header,sec.first_page_header]:
    for el in list(header._element): header._element.remove(el)
hp=sec.header.add_paragraph();hp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=hp.add_run();r.font.name='Times New Roman';r.font.size=Pt(12)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');r._r.addnext(fld)
sec.first_page_header.add_paragraph()
for footer in [sec.footer,sec.first_page_footer]:
    for el in list(footer._element):footer._element.remove(el)
    footer.add_paragraph()

def dp(text,style=None,align=None,size=14,bold=False):
    par=doc.add_paragraph(style=style)
    par.paragraph_format.widow_control=True
    if align is not None:par.alignment=align;par.paragraph_format.first_line_indent=Pt(0)
    else:par.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    run=par.add_run(text);run.font.name='Times New Roman';run.font.size=Pt(size);run.font.color.rgb=RGBColor(0,0,0);run.bold=bold
    return par

title_lines=[('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ',12,0,False),('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА',12,0,False),('Факультет електроніки і комп’ютерних технологій',14,0,False),('Звіт',14,85,True),('про виконання лабораторної роботи №5',14,12,False),('з курсу «Вибрані розділи науки про дані»',14,12,False),('«Побудова онтології для бази знань\nвізуалізації енергетичних даних»',14,20,False)]
for text,size,before,bold in title_lines:
    par=dp(text,'Title' if text=='Звіт' else None,WD_ALIGN_PARAGRAPH.CENTER,size,bold);par.paragraph_format.space_before=Pt(before);par.paragraph_format.line_spacing=1.2
for i,text in enumerate(['Виконав:','студент групи ФЕІм-13с','Шевчук Максим Вікторович','Перевірив:','Парубочий В. О.']):
    par=dp(text,align=WD_ALIGN_PARAGRAPH.RIGHT,bold=text.endswith(':'));par.paragraph_format.line_spacing=1.2;par.paragraph_format.space_before=Pt(72 if i==0 else 0)
par=dp('Львів 2026',align=WD_ALIGN_PARAGRAPH.CENTER);par.paragraph_format.space_before=Pt(115)

styles={
 'p':ParagraphStyle('p',fontName='TNR',fontSize=14,leading=21,alignment=TA_JUSTIFY,firstLineIndent=12.5*mm,spaceAfter=0),
 'h':ParagraphStyle('h',fontName='TNRB',fontSize=14,leading=18,alignment=TA_CENTER,spaceBefore=8,spaceAfter=8,keepWithNext=True),
 'cell':ParagraphStyle('cell',fontName='TNR',fontSize=14,leading=16,alignment=TA_LEFT),
 'cellhead':ParagraphStyle('cellhead',fontName='TNRB',fontSize=14,leading=16,alignment=TA_LEFT),
 'list':ParagraphStyle('list',fontName='TNR',fontSize=14,leading=21,alignment=TA_LEFT,firstLineIndent=0),
 'cap':ParagraphStyle('cap',fontName='TNR',fontSize=12,leading=14,alignment=TA_CENTER,spaceAfter=6),
 'tablecap':ParagraphStyle('tablecap',fontName='TNR',fontSize=14,leading=17,alignment=TA_CENTER,spaceAfter=6,keepWithNext=True),
 'code':ParagraphStyle('code',fontName='CONS',fontSize=12,leading=14,alignment=TA_LEFT),
}
def rp(t,sty):return Paragraph(escape(t).replace('\n','<br/>'),styles[sty])
story=[Spacer(1,10)]
story.append(PageBreak())

class ScreenshotViewport(Flowable):
    """Native PDF clipping; the original screenshot is embedded unchanged."""
    def __init__(self,path,width,box):
        super().__init__()
        self.path=path
        self.iw,self.ih=Image.open(path).size
        self.box=box or (0,0,self.iw,self.ih)
        left,top,right,bottom=self.box
        self.scale=width/(right-left)
        self.width=width;self.height=(bottom-top)*self.scale
        self.hAlign='CENTER'
    def draw(self):
        c=self.canv;left,top,right,bottom=self.box;s=self.scale
        c.saveState()
        clip=c.beginPath();clip.rect(0,0,self.width,self.height)
        c.clipPath(clip,stroke=0,fill=0)
        c.drawImage(self.path,-left*s,-(self.ih-bottom)*s,self.iw*s,self.ih*s)
        c.restoreState()

page_heights=[]
for pn,items in enumerate(pages,2):
    doc.add_page_break()
    current=[]
    for item in items:
        kind=item[0]
        if kind=='p':
            par=dp(item[1])
            is_list=item[1].startswith('1. ')
            if is_list:
                par.alignment=WD_ALIGN_PARAGRAPH.LEFT
                par.paragraph_format.first_line_indent=Pt(0)
            current.append(rp(item[1],'list' if is_list else 'p'))
        elif kind=='h':
            par=dp(item[1],'Heading 1',WD_ALIGN_PARAGRAPH.CENTER,bold=True)
            par.paragraph_format.space_before=Pt(8);par.paragraph_format.space_after=Pt(8);par.paragraph_format.line_spacing=1.0;par.paragraph_format.keep_with_next=True
            current.append(rp(item[1],'h'))
        elif kind=='table':
            _,title,headers,rows,widths=item
            par=dp(title,align=WD_ALIGN_PARAGRAPH.CENTER);par.paragraph_format.line_spacing=1;par.paragraph_format.space_after=Pt(6);par.paragraph_format.keep_with_next=True
            dt=doc.add_table(rows=1,cols=len(headers));dt.autofit=False
            for col,w in zip(dt.columns,widths):col.width=Cm(w/10)
            for vals in [headers]+rows:
                cells=dt.rows[0].cells if vals is headers else dt.add_row().cells
                for c,t,w in zip(cells,vals,widths):
                    c.width=Cm(w/10);c.text=t
                    tcpr=c._tc.get_or_add_tcPr()
                    borders=OxmlElement('w:tcBorders')
                    for side in ['top','left','bottom','right']:
                        b=OxmlElement('w:'+side);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'D9D9D9');borders.append(b)
                    tcpr.append(borders)
                    marg=OxmlElement('w:tcMar')
                    for side in ['top','left','bottom','right']:
                        m=OxmlElement('w:'+side);m.set(qn('w:w'),'50');m.set(qn('w:type'),'dxa');marg.append(m)
                    tcpr.append(marg)
                    if vals is headers:
                        sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'EDEDED');tcpr.append(sh)
                    for par in c.paragraphs:
                        par.paragraph_format.first_line_indent=Pt(0);par.paragraph_format.line_spacing=1;par.paragraph_format.space_after=Pt(0)
                        for r in par.runs:r.font.name='Times New Roman';r.font.size=Pt(14);r.font.color.rgb=RGBColor(0,0,0);r.bold=vals is headers
                trpr=cells[0]._tc.getparent().get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
            dt.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
            rlt=Table([[rp(t,'cellhead' if vals is headers else 'cell') for t in vals] for vals in [headers]+rows],colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
            rlt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.35,colors.HexColor('#D9D9D9')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EDEDED')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
            current.extend([rp(title,'tablecap'),rlt,Spacer(1,6)])
        elif kind=='fig':
            _,name,caption,width=item
            par=doc.add_paragraph();par.paragraph_format.first_line_indent=Pt(0);par.paragraph_format.line_spacing=1;par.alignment=WD_ALIGN_PARAGRAPH.CENTER;par.paragraph_format.keep_with_next=True;par.add_run().add_picture(str(WORK/name),width=Cm(width/10))
            par=dp(caption,'Caption',WD_ALIGN_PARAGRAPH.CENTER,12);par.paragraph_format.line_spacing=1;par.paragraph_format.space_after=Pt(6)
            im=Image.open(WORK/name);rw=width*mm;rh=rw*im.height/im.width
            current.append(KeepTogether([RLImage(str(WORK/name),rw,rh),rp(caption,'cap')]))
        elif kind=='screen':
            _,path,caption,width,box=item
            iw,ih=Image.open(path).size
            left,top,right,bottom=box or (0,0,iw,ih)
            height=width*(bottom-top)/(right-left)
            par=doc.add_paragraph();par.paragraph_format.first_line_indent=Pt(0);par.paragraph_format.line_spacing=1;par.alignment=WD_ALIGN_PARAGRAPH.CENTER;par.paragraph_format.keep_with_next=True
            par.paragraph_format.space_before=Pt(12);par.paragraph_format.space_after=Pt(6)
            pic=par.add_run().add_picture(path,width=Cm(width/10),height=Cm(height/10))
            if box:
                fill=pic._inline.graphic.graphicData.pic.blipFill
                rect=OxmlElement('a:srcRect')
                for key,value in [('l',left/iw),('t',top/ih),('r',(iw-right)/iw),('b',(ih-bottom)/ih)]:
                    rect.set(key,str(round(value*100000)))
                fill.insert(1,rect)
            pic._inline.docPr.set('descr',caption+'; оригінальний скриншот WebProtégé')
            par=dp(caption,'Caption',WD_ALIGN_PARAGRAPH.CENTER,12);par.paragraph_format.line_spacing=1;par.paragraph_format.space_after=Pt(6)
            current.append(KeepTogether([Spacer(1,12),ScreenshotViewport(path,width*mm,box),Spacer(1,6),rp(caption,'cap'),Spacer(1,6)]))
        elif kind=='code':
            text=item[1]
            par=doc.add_paragraph();par.paragraph_format.first_line_indent=Pt(0);par.paragraph_format.line_spacing=1;par.paragraph_format.space_after=Pt(6);par.alignment=WD_ALIGN_PARAGRAPH.LEFT
            r=par.add_run(text);r.font.name='Consolas';r.font.size=Pt(12);r.font.color.rgb=RGBColor(0,0,0)
            pr=par._p.get_or_add_pPr();sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'F2F2F2');pr.append(sh)
            bd=OxmlElement('w:pBdr')
            for side in ['top','left','bottom','right']:
                el=OxmlElement('w:'+side);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');el.set(qn('w:space'),'7');bd.append(el)
            pr.append(bd)
            block=Table([[Preformatted(text,styles['code'])]],colWidths=[180*mm]);block.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F2F2F2')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#D9D9D9')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));current.extend([block,Spacer(1,6)])
    story.extend(current)
    if pn<len(pages)+1:story.append(PageBreak())

doc.core_properties.author='Шевчук Максим Вікторович'
doc.core_properties.title='Лабораторна робота №5 — Побудова онтології для бази знань'
doc.save(ROOT/(STEM+'.docx'))

def page_canvas(canvas,document):
    canvas.setFillColor(colors.black)
    if document.page>1:
        canvas.setFont('TNR',12);canvas.drawRightString(A4[0]-10*mm,A4[1]-10*mm,str(document.page));return
    def center(text,y,size=14,bold=False):
        canvas.setFont('TNRB' if bold else 'TNR',size);canvas.drawCentredString(A4[0]/2,y,text)
    center('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ',A4[1]-84,12)
    center('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА',A4[1]-101,12)
    center('Факультет електроніки і комп’ютерних технологій',A4[1]-121)
    center('Звіт',A4[1]-242,14,True)
    center('про виконання лабораторної роботи №5',A4[1]-274)
    center('з курсу «Вибрані розділи науки про дані»',A4[1]-304)
    center('«Побудова онтології для бази знань',A4[1]-350)
    center('візуалізації енергетичних даних»',A4[1]-372)
    for i,t in enumerate(['Виконав:','студент групи ФЕІм-13с','Шевчук Максим Вікторович','Перевірив:','Парубочий В. О.']):
        canvas.setFont('TNRB' if t.endswith(':') else 'TNR',14);canvas.drawRightString(A4[0]-25*mm,A4[1]-485-i*22,t)
    center('Львів 2026',70)

pdf=SimpleDocTemplate(str(ROOT/(STEM+'.pdf')),pagesize=A4,leftMargin=20*mm,rightMargin=10*mm,topMargin=20*mm,bottomMargin=20*mm,title=doc.core_properties.title,author=doc.core_properties.author)
pdf.build(story,onFirstPage=page_canvas,onLaterPages=page_canvas)
(WORK/'content.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
print('Created',STEM, 'planned pages:',len(pages)+1)
