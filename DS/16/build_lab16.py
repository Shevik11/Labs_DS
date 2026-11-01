from pathlib import Path
import json, shutil, hashlib, statistics, math, zipfile
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderPM
from docx import Document
from docx.shared import Pt, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parent
OUT=ROOT if (ROOT/'evidence').exists() else ROOT/'ЛР16'
OUT.mkdir(exist_ok=True)
for folder in ['evidence/lab13','evidence/lab14','evidence/lab15','figures','sources']:
    (OUT/folder).mkdir(parents=True,exist_ok=True)
SOURCE=Path('D:/LNU/DS')
selected={13:['results/metrics.json','results/calibration.json','results/metric_audit.json','results/environment.json','README.md'],
          14:['results/load_summary.json','results/false_alarms.json','results/fault_injection.json','RUNBOOK.md','DATA_CONTRACT.md','README.md'],
          15:['results/summary.json','results/benchmark.json','results/effects.json','results/safety.json','results/api.json','results/repeated.json','results/environment.json','results/regression.json','README.md','BUDGET.json','data/gold_v1.jsonl']}
manifest=[]
for lab,files in selected.items():
    for rel in files:
        src=SOURCE/str(lab)/rel
        dst=OUT/'evidence'/f'lab{lab}'/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        if src.exists() and not dst.exists(): shutil.copy2(src,dst)
        manifest.append({'source':str(src),'file':dst.relative_to(OUT).as_posix(),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
if not (OUT/'sources/ЛР16_завдання.pdf').exists():
    shutil.copy2('D:/downloads/ЛР16_завдання.pdf',OUT/'sources/ЛР16_завдання.pdf')
for name,src in [('lab1_README.md',SOURCE/'1/README.md'),('lab5_README.md',SOURCE/'5/README.md'),('lab8_MODEL_MAPPING.md',SOURCE/'8/MODEL_MAPPING.md'),('lab12_README.md',SOURCE/'12/README.md')]:
    if not (OUT/'sources'/name).exists(): shutil.copy2(src,OUT/'sources'/name)
def read(rel): return json.loads((OUT/rel).read_text('utf-8-sig'))
summary=read('evidence/lab15/results/summary.json')
bench=read('evidence/lab15/results/benchmark.json')
metrics13=read('evidence/lab13/results/metrics.json')
cal=read('evidence/lab13/results/calibration.json')
repo_file=ROOT/'repository_url.txt'
REPO=repo_file.read_text('utf-8').strip() if repo_file.exists() else 'Посилання очікує підтвердження автора'

for name,file in [('TNR','times.ttf'),('TNRB','timesbd.ttf'),('TNRI','timesi.ttf'),('Mono','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNRB',italic='TNRI',boldItalic='TNRB')
styles={
 'body':ParagraphStyle('body',fontName='TNR',fontSize=14,leading=21,alignment=TA_JUSTIFY,firstLineIndent=12.5*mm,spaceAfter=0),
 'tight':ParagraphStyle('tight',fontName='TNR',fontSize=14,leading=16,alignment=TA_LEFT,spaceAfter=4),
 'heading':ParagraphStyle('heading',fontName='TNRB',fontSize=14,leading=19,alignment=TA_CENTER,spaceAfter=10,keepWithNext=True),
 'caption':ParagraphStyle('caption',fontName='TNR',fontSize=12,leading=14,alignment=TA_CENTER,spaceAfter=6),
 'small':ParagraphStyle('small',fontName='TNR',fontSize=12,leading=15,alignment=TA_LEFT,spaceAfter=5),
 'code':ParagraphStyle('code',fontName='Mono',fontSize=12,leading=14,backColor=colors.HexColor('#F2F2F2'),borderColor=colors.HexColor('#D9D9D9'),borderWidth=.5,borderPadding=6),
}
PAGES=[]
def page(title):
    items=[]; PAGES.append({'title':title,'items':items}); return items
def p(items,text,kind='body'): items.append(('p',text,kind))
def table(items,title,headers,rows,widths): items.append(('table',title,headers,rows,widths))
def fig(items,name,caption,height): items.append(('fig',name,caption,height))

# Vector figures use only recorded values. All lettering is black.
d=Drawing(500,230)
d.add(String(250,213,'Частка проходження proxy перевірок',fontName='TNRB',fontSize=14,textAnchor='middle'))
labels=['Прості  n=20','Багатокрокові  n=10','Без відповіді  n=5','Провокативні  n=5']
types=['simple','multihop','unanswerable','adversarial']
for i,(typ,label) in enumerate(zip(types,labels)):
    y=165-i*43
    d.add(String(0,y+5,label,fontName='TNR',fontSize=12))
    before=[r['seconds'] for r in bench if r['stage']==0 and r['type']==typ]
    after=[r['seconds'] for r in bench if r['stage']==3 and r['type']==typ]
    timing=f'{statistics.mean(before):.3f} → {statistics.mean(after):.3f} с'.replace('.',',')
    d.add(String(0,y-10,timing,fontName='TNR',fontSize=11))
    for j,stage in enumerate([0,3]):
        group=[r for r in bench if r['stage']==stage and r['type']==typ]
        val=sum(r['correct'] for r in group)/len(group)
        d.add(Rect(172,y+11-j*16,270*val,12,fillColor=colors.HexColor('#7A9EB1' if j==0 else '#87B095'),strokeColor=None))
        d.add(String(448,y+12-j*16,f'{sum(r["correct"] for r in group)}/{len(group)}',fontName='TNR',fontSize=12))
d.add(Rect(172,2,12,12,fillColor=colors.HexColor('#7A9EB1'),strokeColor=None));d.add(String(190,3,'ЛР15 до',fontName='TNR',fontSize=12))
d.add(Rect(300,2,12,12,fillColor=colors.HexColor('#87B095'),strokeColor=None));d.add(String(318,3,'ЛР15 після',fontName='TNR',fontSize=12))
from reportlab.graphics import renderSVG
renderSVG.drawToFile(d,str(OUT/'figures/quality.svg'))
FIGURES={'quality':d}

a=Drawing(500,280)
a.add(Rect(6,185,488,87,fillColor=None,strokeColor=colors.black,strokeDashArray=[4,3]))
a.add(String(15,258,'Межа 1  Клієнт і недовірений ввід',fontName='TNRB',fontSize=12))
a.add(Rect(30,205,175,35,fillColor=colors.white,strokeColor=colors.black));a.add(String(117,219,'Аналітик  →  FastAPI',fontName='TNR',fontSize=13,textAnchor='middle'))
a.add(Rect(265,205,205,35,fillColor=colors.white,strokeColor=colors.black));a.add(String(367,219,'Валідація та guardrails',fontName='TNR',fontSize=13,textAnchor='middle'))
a.add(Line(205,222,265,222));a.add(Polygon([265,222,258,226,258,218],fillColor=colors.black))
a.add(Rect(6,55,488,120,fillColor=None,strokeColor=colors.black,strokeDashArray=[4,3]));a.add(String(15,157,'Межа 2  Локальний сервіс і версійовані дані',fontName='TNRB',fontSize=12))
for x,w,t1,t2 in [(20,140,'MiniLM → FAISS','38 фрагментів'),(180,140,'Neo4j read only','Дозволені шляхи'),(340,140,'FLAN та витяги','Цитати  LRU TTL')]:
    a.add(Rect(x,84,w,52,fillColor=colors.white,strokeColor=colors.black));a.add(String(x+w/2,115,t1,fontName='TNR',fontSize=12,textAnchor='middle'));a.add(String(x+w/2,96,t2,fontName='TNR',fontSize=12,textAnchor='middle'))
a.add(Line(367,205,489,205));a.add(Line(489,205,489,145));a.add(Line(90,145,489,145));a.add(Line(90,145,90,136));a.add(Line(250,145,250,136));a.add(Line(410,145,410,136))
a.add(Line(160,110,180,110));a.add(Line(320,110,340,110))
a.add(String(250,65,'Корпус і граф є доказами  Інструкції з них не виконуються',fontName='TNR',fontSize=11,textAnchor='middle'))
a.add(String(250,31,'ЛР1–9 → перевірка даних → граф і корпус → індекс',fontName='TNR',fontSize=13,textAnchor='middle'))
a.add(String(250,11,'Відповідь і джерела → аналітик   Метрики → монітор ЛР14',fontName='TNR',fontSize=12,textAnchor='middle'))
renderSVG.drawToFile(a,str(OUT/'figures/architecture.svg'));FIGURES['architecture']=a
try:
    import pymupdf
    for key in FIGURES:
        with pymupdf.open(OUT/'figures'/f'{key}.svg') as svgdoc:
            svgdoc[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(str(OUT/'figures'/f'{key}.png'))
except ImportError:
    if not all((OUT/'figures'/f'{key}.png').exists() for key in FIGURES):
        raise RuntimeError('Install PyMuPDF to render DOCX figures')

x=page('Титул')
p(x,'МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ','caption')
p(x,'ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА','caption')
p(x,'Факультет електроніки і комп’ютерних технологій','center')
x.append(('space',45))
p(x,'Звіт','title')
p(x,'про виконання лабораторної роботи №16','center')
p(x,'з курсу «Вибрані розділи науки про дані»','center')
p(x,'«Подання бізнес-рішення Whitepaper»','center')
p(x,'Асистент аналітика енергоспоживання на основі графа знань і RAG','center')
x.append(('space',30))
p(x,'<b>Виконав:</b><br/>студент групи ФЕІм-13с<br/>Шевчук Максим Вікторович<br/><br/><b>Перевірив:</b>','right')
x.append(('space',25));p(x,'Львів 2026','center')

x=page('Резюме для керівника')
p(x,'Резюме для керівника','heading')
p(x,'Пропонується контрольований пілот локального асистента для пошуку підтверджених відомостей про дані електроспоживання, онтологію та результати аналізу. Цільова аудиторія — технічний директор і керівник аналітичної команди. Рішення, яке пропонується ухвалити: перевірити корисність асистента на робочих запитаннях аналітиків до будь-якого виробничого впровадження.')
p(x,'Проблема — витрати часу на пошук одиниць вимірювання, походження прогнозів і зв’язків між даними в різних лабораторних артефактах. Система об’єднує перевірені нотатки, векторний пошук, граф Neo4j та локальну мовну модель. Відповідь супроводжується цитатами; невідомі або небезпечні запити передаються на ручний розгляд через сигнал handoff.')
p(x,'На одному наборі із 40 запитань у ЛР15 частка проходження перевірок термінів і політик зросла з 23/40 до 40/40; p95 зменшився з 0,984 до 0,657 с, вхідні токени — з 12 414 до 6 211. Це результати послідовного локального експерименту з живою Neo4j, після прогріву, без часу завантаження моделей [3].')
p(x,'40/40 не означає безпомилковості: фінальна відповідь містить довші цитовані витяги, які полегшують проходження перевірки ключових слів. Нової незалежної людської оцінки цих відповідей немає. У ЛР13 LLM-суддя не пройшов калібрування: κ=0 за всіма трьома критеріями [2].')
p(x,'За сценарних 1 000 запитів на місяць, зменшення часу пошуку з 8 до 3 хв і вартості праці 300 грн/год потенційна економія становить 25 000 грн/місяць. Після умовних 9 000 грн щомісячних витрат чистий ефект — 16 000 грн/місяць. Це модель, а не виміряний дохід чи економія електроенергії.')
p(x,'Наступний крок — незалежне оцінювання якості, вимірювання часу виконання завдань і повних витрат у пілоті. Система має працювати як довідковий інструмент із перевіркою людиною; керування енергетичним обладнанням виходить за її поточне призначення.')

x=page('Зміст і проблема')
p(x,'Зміст','heading')
for title,num in [('Резюме для керівника',2),('1 Проблема користувачі та сценарії',3),('2 Метрики успіху та економічна цінність',4),('3 Архітектура та вибір технологій',5),('4 Дані та шар знань',6),('5 Результати та методика оцінювання',7),('6 Приклади відповідей та межі результатів',8),('7 Реєстр ризиків',9),('8 Регуляторні вимоги та експлуатація',10),('9 Наступні кроки та висновок',11),('10 Джерела і відтворюваність',12)]:
    p(x,f'{title} ................................................................ {num}','toc')
p(x,'1 Проблема користувачі та сценарії','heading')
p(x,'Основне повідомлення: асистент скорочує шлях до перевіреного джерела, але корисність і безпеку треба підтвердити на незалежному пілоті. Його користувач — аналітик, який звіряє одиниці, структуру графа, методику прогнозування або пояснює результат колезі.')
p(x,'Сценарії: знайти кількість вузлів і зв’язків; пояснити відношення між поняттями; відрізнити потужність у кВт від енергії у кВт·год; виявити, що запитаного серійного номера чи майбутнього факту немає. Керівник використовує цитовану відповідь для перевірки звіту. Зовнішніх клієнтів і фактичний попит поки не досліджено.')

x=page('2 Метрики успіху та економічна цінність')
p(x,'2 Метрики успіху та економічна цінність','heading')
table(x,'Таблиця 1 — Запропоновані критерії пілоту',['Показник','Ціль пілоту','Стан доказів'],[
 ['Людська якість','≥90% відповідей прийняті двома оцінювачами','Для фінальної ЛР15 не виміряно'],
 ['Час роботи аналітика','Медіана ≤3 хв проти базових 8 хв','Обидва значення — гіпотези'],
 ['Затримка сервісу','p95 ≤1 с на заявленому CPU','ЛР15 0,657 с; без HTTP і холодного старту'],
 ['Приватні та атакувальні запити','0 витоків у розширеному наборі','15/15 навчальних перевірок пройдено'],
 ['Повні витрати','≤9 000 грн/місяць','Умовний бюджет; потрібен облік'],
], [48,65,67])
p(x,'Розрахунок моделі: E = N × (t₀ − t₁) / 60 × w − C. Тут N — кількість запитів за місяць; t₀ і t₁ — хвилини на завдання без та з асистентом, включно з перевіркою відповіді; w — повна вартість години праці; C — експлуатаційні витрати. Одноразові витрати I не включаються в C.')
p(x,'Базові припущення: N=1 000; t₀=8; t₁=3; w=300 грн/год; C=9 000 грн/місяць (6 000 підтримка, 3 000 інфраструктура); I=40 000 грн. Вивільняється 83,3 год/місяць, валова цінність — 25 000 грн, E=16 000 грн; проста окупність I/E=2,5 місяця. Дисконт, податки, навчання користувачів і вартість помилок не оцінені.')
table(x,'Таблиця 2 — Чутливість за незмінних N w C',['Економія на запит','Чистий ефект за місяць','Проста окупність'],[
 ['2 хв','1 000 грн','40 місяців'],['5 хв','16 000 грн','2,5 місяця'],['7 хв','26 000 грн','1,54 місяця']],[60,65,55])
p(x,'Поріг беззбитковості: 9000 × 60 / (1000 × 300) = 1,8 хв економії на запит. Вивільнений час стає грошовою економією лише за реального перерозподілу роботи; зменшення енергоспоживання ця модель не доводить.','tight')

x=page('3 Архітектура та вибір технологій')
p(x,'3 Архітектура та вибір технологій','heading')
p(x,'На рис. 1 показано логічний потік. Ввід користувача, корпус і граф мають різні рівні довіри. Guardrails обмежує вхід і перевіряє схему виходу; контекст передається моделі лише як дані. Телеметрія ЛР14 і оптимізований Engine ЛР15 перевірені окремо: їх спільне виробниче розгортання ще потребує інтеграційного тесту.','tight')
fig(x,'architecture','Рис. 1 — Компоненти потоки та межі довіри',100)
table(x,'Таблиця 3 — Технології та альтернативи',['Компонент і вибір','Альтернатива','Причина та обмеження'],[
 ['FastAPI і Pydantic','Flask','Типізований контракт і валідація; автентифікацію ще додати'],
 ['MiniLM і FAISS dense','BM25 або RRF','Локальний пошук; RRF знизив Recall@3 і відхилений'],
 ['Neo4j і дозволені шляхи','SQL або лише текст','Явні спрямовані зв’язки; складніший супровід'],
 ['FLAN T5 small і цитати','Більша модель або API','CPU і локальна обробка; слабкий синтез та оцінювання'],
 ['LRU 64  TTL 300 с','Без кешу або Redis','Простий локальний кеш; інвалідація при релізі потрібна'],
],[62,48,70])

x=page('4 Дані та шар знань')
p(x,'4 Дані та шар знань','heading')
p(x,'Джерело ЛР1 — UCI Individual Household Electric Power Consumption: 2 075 259 хвилинних вимірювань одного домогосподарства у Франції за 2006–2010 роки [5]. Це історичний навчальний набір; його не можна подавати як актуальні дані всієї енергосистеми України.')
p(x,'Конвеєр даних: перевірка архіву та схеми → дата і час → пропуски й дублікати → фізичні одиниці → повні години → ознаки → часовий поділ → моделі → граф і джерельні нотатки. Для години потрібні 60 хвилинних записів. Енергія за годину — сума хвилинних потужностей у кВт, поділена на 60; пропуски не підміняються нулями. Масштабування навчається лише на навчальній частині [1].')
p(x,'ЛР4–5 задають таксономію та онтологічні обмеження. Збережена схема, використана в ЛР8–15, містить 37 класів, 31 об’єктну властивість, 34 властивості даних та 26 індивідів. Повний граф має 43 746 вузлів і 199 287 зв’язків; локальний знімок дозволених запитів — 63 вузли та 38 ребер. Окремого первинного звіту ЛР6 немає; її відомості простежуються через наступні роботи [1–3].')
p(x,'Фіксований індекс містить 38 фрагментів із 20 англомовних нотаток. MiniLM формує вектори, FAISS повертає top 3. Базова система додає дозволені графові шляхи до контексту. На фінальному шляху ЛР15 повертаються переважно цитовані текстові докази, а не новий логічний висновок із графа. Промпт вимагає відповідати лише з доказів і відмовляти за їх відсутності.')
p(x,'Контроль якості: непорожній унікальний id; скінченні значення; узгоджені часові поля й одиниці; карантин дефектного пакета; hash, версія та походження кожного артефакту. Межі 0–20 кВт і 180–270 В у ЛР14 є локальним контрактом цього набору, а не правовою нормою. Історичні localdatetime не перетворюються на UTC без додаткових відомостей [4].')
p(x,'У цьому Whitepaper попередні експерименти не перезапускаються. Копії вибраних первинних JSON, методика та SHA256 включені в ZIP; нові обчислення обмежені агрегуванням збережених журналів і сценарною економікою.','tight')

x=page('5 Результати та методика оцінювання')
p(x,'5 Результати та методика оцінювання','heading')
table(x,'Таблиця 4 — Збережені результати до та після [2 3]',['Показник','ЛР13 dense','ЛР15 до','ЛР15 після'],[
 ['Backend','Знімок','Жива Neo4j','Жива Neo4j'],
 ['Proxy успіху','23/40 сирі; 24/40 аудит','23/40','40/40'],
 ['Recall@3  n=33','0,9899','0,9899','0,9899'],
 ['p95 запиту  с','0,785','0,984','0,657'],
 ['Вхідні токени за 40','12 414','12 414','6 211'],
 ['API плата  USD','0','0','0'],
],[61,43,38,38])
p(x,'Порівнювані етапи ЛР15 виконані в Linux на CPU з 4 потоками: 40 запитів на етап, один спільний прогрів, фіксований порядок етапів. Середня затримка 0,308 → 0,224 с (−27,1%); p95 −33,2%; вхідні токени −50,0%. На рис. 2 розподілено успіх за типами.','tight')
fig(x,'quality','Рис. 2 — Proxy успіху і середня затримка до та після за типами',76)
p(x,'Еталон: 20 простих, 10 багатокрокових, 5 без відповіді, 5 провокативних запитань. Recall@3 — макросереднє лише за 33 запитами з непорожніми еталонними ID. Proxy перевіряє required_terms і політику відмови, а не семантичну правильність. ЛР13 додатково вручну прийняла q32; ЛР15 застосовує суворішу перевірку статусу, тому 24/40 не є її базою.','tight')
p(x,'RRF у проміжному етапі: 22/40 і Recall@3=0,9848; його відхилено. Повернення dense, стиснення та цитовані витяги дали 40/40 ще до фінального guardrails. Bootstrap інтервал [1;1] на цьому наборі не гарантує якості на нових питаннях. Порядок етапів і одиничні вимірювання обмежують висновки про швидкодію.','tight')

x=page('6 Приклади відповідей та межі результатів')
p(x,'6 Приклади відповідей та межі результатів','heading')
p(x,'Успішний простий приклад q01: «How many nodes and relationships are in the complete Lab8 graph?» Збережена відповідь: «The complete Lab8 graph contains 43746 nodes and 199287 relationships. [fixed-0001]». Це коректний пошук факту зі збереженого джерела, а не новий підрахунок усіх вузлів [3].')
p(x,'Невдалий приклад q21 до оптимізації: на прохання одночасно навести розмір графа й кількість класів відповідь — «Недостатньо даних», proxy=0. Після оптимізації повернуто цитовані фрагменти fixed-0002, fixed-0011 і fixed-0001 з числами 37, 43746 та 199287, proxy=1. Витяги довгі; поліпшення стислості й зрозумілості людиною не перевірене [3].')
p(x,'Приклад межі q32: запит фізичного серійного номера лічильника. База пояснювала, що номер невідомий, але повертала status=answered і не проходила сувору політику ЛР15. Фінальна відповідь «Недостатньо даних» з handoff пройшла перевірку. Це виправлення політики відмови, а не поява нового факту.')
p(x,'Людська перевірка ЛР13: 76/76 збігів релевантності, κ=1; розмітка A була чернеткою ШІ, відредагованою людиною, незалежність двох учасників підтверджена в збереженому provenance. Для 12 відповідей отримано 36 людських оцінок. Суддя давав сталі одиниці: κ=0; Spearman не визначений. Його бали не можна використовувати як валідовану якість [2].')
p(x,'У ЛР13 додавання BM25 ранжування змінило аудований proxy з 24/40 до 23/40, Recall@3 з 0,9899 до 0,9848, p95 з 0,785 до 1,468 с. Цей варіант не забезпечив поліпшення; час Windows зі знімком не порівнюється напряму з Linux і живою БД ЛР15.','tight')
p(x,'Затримка й вартість: ЛР14 має окремий HTTP-тест із 45 генераціями та 5 очікуваними 422; p95 усіх 50 запитів 1,290 с, перший запит 28,591 с. Це інший протокол, тому його не слід об’єднувати з прогрітим Engine ЛР15. У серії 40 повторів ЛР15 кеш спрацював 32 рази; середній час серії 0,031 с не є затримкою довільного нового запиту [3–4].')
p(x,'Фактична API-плата локальних моделей — 0 USD. Повна вартість запиту невідома без обліку енергії, CPU, пам’яті, підтримки та перевірки людиною. Умовні 9 000 грн/місяць за 1 000 запитів дають 9 грн/запит лише в економічному сценарії. Даних про реальних клієнтів, багатокористувацьке навантаження чи незалежну якість українською немає.')

x=page('7 Реєстр ризиків')
p(x,'7 Реєстр ризиків','heading')
p(x,'Таблиця 5 містить експертні оцінки ймовірності, а не частоти інцидентів. Низька/середня/висока описують очікування для пілоту. У кожному рядку визначено вплив, захід і перевірку. Виконавцем навчальної версії є автор; виробничі ролі ще потрібно призначити.','tight')
table(x,'Таблиця 5 — Ризики заходи та перевірки',['Ризик і ймовірність','Вплив','Захід','Метрика перевірки'],[
 ['Хибний висновок або неповна відповідь\nВисока','Неправильний звіт','Цитати й перевірка аналітиком; незалежний еталон','Ціль ≥90% людського прийняття; фінальне значення відсутнє'],
 ['Prompt injection\nСередня','Підміна відповіді','Контекст як дані; allowlist інструментів; відмова','15/15 сукупних safety кейсів пройдено; новий набір перед релізом'],
 ['Розкриття даних\nСередня','Шкода приватності','Мінімізація вводу, технічні журнали; рольовий доступ у пілоті','0 секретів у ZIP; ціль 0 витоків у тестах доступу'],
 ['Дефект одиниць або дрейф\nСередня','Хибна інтерпретація','Контракт, карантин, PSI/KS','0 прийнятих пакетів із ×100; PSI пороги 0,1/0,25'],
 ['Недоступність LLM або БД\nСередня','Затримка роботи','Health, явний 503, відкат, ручний шлях','Час реакції 5 хв — ціль runbook; перевірка відновлення'],
 ['Застарілий кеш чи індекс\nСередня','Застарілі факти','TTL 300 с; очистити кеш при зміні версії','0 відповідей старої версії після релізного тесту'],
 ['Використання для керування мережею\nНизька','Висока небезпека','Обмежити призначення; read only; повторна правова оцінка','0 команд обладнанню; перевірка дозволених операцій'],
],[42,36,53,49])
p(x,'15/15 safety кейсів — обмежена навчальна перевірка ін’єкцій, вводу, відмов і контракту; це не оцінка ймовірності успішної атаки. Поки немає пілоту, залишковий ризик помилкових відповідей і витрат лишається невиміряним.','tight')

x=page('8 Регуляторні вимоги та експлуатація')
p(x,'8 Регуляторні вимоги та експлуатація','heading')
p(x,'AI Act. Для описаного довідкового асистента віднесення до високого ризику не випливає лише з енергетичної теми. Це попередня оцінка призначення, а не сертифікація. Для застосування як компонента безпеки постачання електроенергії Annex III(2) вимагає окремого аналізу високого ризику. Для пілоту слід повідомляти про взаємодію із ШІ, забезпечити підготовку оператора і перегляд результатів людиною [6].')
p(x,'GDPR. Відкритість набору не гарантує анонімності. Якщо запити чи вимірювання пов’язані з ідентифікованими людьми, до запуску треба визначити контролера, правову підставу, мету і строк зберігання; застосувати мінімізацію та захист даних і перевірити потребу DPIA. План пілоту: не приймати ідентифікатори домогосподарств, не журналювати тексти запитів, технічні журнали видаляти через запропоновані 30 днів; перевіряти доступ і видалення. Ці організаційні правила ще не підтверджені виробничим аудитом [7].')
p(x,'Експлуатація спирається на ЛР14: /health, /metrics, журнали без текстів запитів, latency, помилки, токени. Автор у навчальному середовищі виконує ролі оператора, розробника і відповідального за дані. Для пілоту керівник має призначити ці ролі окремо. Цілі реакції runbook: 5 хв на недоступність або дефект одиниць, 15 хв на critical drift, 1 год на warning [4].')
p(x,'Дрейф: PSI≥0,1 для warning та ≥0,25 для critical, KS p&lt;0,01/3 і підтвердження у двох ознаках; мінімум 1 000 значень на ознаку. Це навчальні пороги activePowerKw, voltageV, forecastKwh, а не моніторинг якості відповідей LLM. Після сигналу перевіряють контракт, сезонність і джерело; дефектний пакет ізолюють. Cooldown 900 с не пригнічує підвищення критичності.')
p(x,'Реліз: зафіксувати hash даних, версії моделей, індексу й конфігурації; виконати regression і safety; перевірити HTTP та права доступу; очистити кеш. У разі відмови повернути попередній образ та сумісний індекс. Перевірка резервного відновлення й спільний запуск ЛР14/15 залишаються завданнями пілоту; автоматичне перенавчання не передбачене.','tight')

x=page('9 Наступні кроки та висновок')
p(x,'9 Наступні кроки та висновок','heading')
for text in [
 '<b>P0 — Незалежна якість.</b> Зібрати щонайменше 100 нових запитань, окремо українською та англійською. Два оцінювачі незалежно перевіряють правильність, повноту і джерела; приклади з поточного еталона виключаються. Критерій переходу — ≥90% прийняття й розбір усіх критичних помилок.',
 '<b>P0 — Межі доступу.</b> До пілоту додати автентифікацію, ролі, rate limit, процедуру видалення та інвалідацію кешу за версією корпусу. Провести тести несанкціонованого доступу й розширені ін’єкції.',
 '<b>P1 — Інтеграція й навантаження.</b> Поєднати оптимізований Engine із телеметрією ЛР14; окремо виміряти холодний старт, HTTP p95, конкурентні запити і відновлення. За зростання навантаження оцінити чергу, окремі процеси inference та спільний кеш.',
 '<b>P1 — Економіка пілоту.</b> Виміряти час одного й того самого завдання без та з асистентом, включаючи перевірку; вести облік підтримки, CPU й електроенергії. Приймати рішення за фактичною економією понад 1,8 хв/запит при сценарному бюджеті.',
 '<b>P2 — Якість відповіді.</b> Порівняти короткі витяги та сильнішу модель на незалежному наборі; зберегти цитати, політику відмови й контроль витрат. Лише після цього розширювати корпус і предметну область.'
]:p(x,text,'tight')
p(x,'Висновок','heading')
p(x,'Артефакти курсу підтверджують працездатність локального пошуку з цитатами, контрольовані відмови та поліпшення proxy показників у ЛР15. Вони достатні для обґрунтування пілоту, але не доводять виробничої надійності чи окупності. Головна умова наступного рішення — незалежна людська оцінка разом із вимірюванням часу і повних витрат.','tight')
p(x,'Декларація використання ШІ','heading')
p(x,'Інструмент — OpenAI Codex. Призначення: пошук локальних артефактів, звірка метрик, структурування Whitepaper, сценарні розрахунки, код формування документа. Запит автора: «Використовуй попередні лабораторні роботи, якщо треба щось від мене напишеш список + інструкцію як це зробити». Перевірка: перерахунок із JSON, контроль хешів, перевірка джерел і сторінок PDF. Нові експерименти з моделями не заявляються. Особисте розуміння й усний захист забезпечує автор.','small')

x=page('10 Джерела і відтворюваність')
p(x,'10 Джерела і відтворюваність','heading')
refs=[
 '[1] Артефакти автора ЛР1, ЛР4–5, ЛР8 і ЛР12. README та MODEL_MAPPING; копії у sources/. Походження даних, варіант і структура знань.',
 '[2] ЛР13. results/metrics.json, calibration.json, metric_audit.json та README. Копії: evidence/lab13/.',
 '[3] ЛР15. results/benchmark.json, summary.json, safety.json, repeated.json; evaluate.py та optimized_engine.py перевірено у первинному проєкті. Докази: evidence/lab15/.',
 '[4] ЛР14. load_summary.json, RUNBOOK.md, DATA_CONTRACT.md та README. Копії: evidence/lab14/.',
 '[5] Hebrail G., Berard A. Individual Household Electric Power Consumption. UCI, 2006. DOI 10.24432/C58K54. CC BY 4.0. https://doi.org/10.24432/C58K54',
 '[6] Regulation (EU) 2024/1689. AI Act, ст. 4, 6, 50; Annex III(2). Офіційний текст EUR Lex. https://eur-lex.europa.eu/eli/reg/2024/1689',
 '[7] Regulation (EU) 2016/679. GDPR, ст. 5, 6, 25, 32, 35. Офіційний текст EUR Lex. https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng/',
 '[8] ЛР16 «Подання бізнес-рішення Whitepaper», 2026–2027 н. р. Завдання автора, 3 с.; sources/ЛР16_завдання.pdf. Нормативні джерела звірено 01.11.2026.'
]
for ref in refs:p(x,ref,'small')
p(x,'Репозиторій: '+REPO,'tight')
p(x,'ZIP містить перевірений PDF, редагований DOCX, build_lab16.py, verify_lab16.py, README, декларацію ШІ, первинні JSON, рисунки та маніфест SHA256. Паролі, API ключі, ваги моделей і дані інших користувачів не включаються. Перебудова Whitepaper не потребує повторного inference.','tight')
p(x,'Додаток А Розрахунок сценарної цінності','heading')
p(x,'Основний обчислювальний фрагмент з build_lab16.py. N — запити/місяць, minutes — економія хвилин на запит, wage — грн/год, cost — грн/місяць.','small')
CODE='def net_value(n, minutes, wage, cost):\n    return n * minutes / 60 * wage - cost\n\nassert net_value(1000, 5, 300, 9000) == 16000'
p(x,escape(CODE).replace(' ','&nbsp;').replace('\n','<br/>'),'code')

def net_value(n,minutes,wage,cost):return n*minutes/60*wage-cost
assert net_value(1000,5,300,9000)==16000

# PDF has explicit page boundaries so the table of contents is deterministic.
pdf_path=OUT/'ЛР16_Шевчук_ФЕІм-13с.pdf'
story=[]
center=ParagraphStyle('center',parent=styles['body'],alignment=TA_CENTER,firstLineIndent=0)
right=ParagraphStyle('right',parent=styles['body'],alignment=2,firstLineIndent=0)
title=ParagraphStyle('title',parent=center,fontName='TNRB',fontSize=20,leading=27)
toc=ParagraphStyle('toc',parent=styles['tight'],fontSize=12,leading=15,spaceAfter=3)
styles.update(center=center,right=right,title=title,toc=toc)
def para(t,k='body'):return Paragraph(t,styles[k])
for idx,pg in enumerate(PAGES):
    if idx:story.append(PageBreak())
    for item in pg['items']:
        if item[0]=='p':story.append(para(item[1],item[2]))
        elif item[0]=='space':story.append(Spacer(1,item[1]*mm))
        elif item[0]=='table':
            _,caption,headers,rows,widths=item
            data=[[para(escape(v).replace('\n','<br/>'),'tight') for v in row] for row in [headers]+rows]
            tbl=Table(data,colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
            tbl.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#777777')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EEEEEE')),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
            story.append(KeepTogether([para(caption,'small'),tbl]));story.append(Spacer(1,5*mm))
        elif item[0]=='fig':
            _,key,cap,height=item
            drawing=FIGURES[key]
            story.append(KeepTogether([drawing,para(cap,'caption')]))
def header(canvas,doc):
    if doc.page>1:
        canvas.setFont('TNR',12);canvas.drawRightString(200*mm,285*mm,str(doc.page))
doc=SimpleDocTemplate(str(pdf_path),pagesize=(210*mm,297*mm),leftMargin=20*mm,rightMargin=10*mm,topMargin=20*mm,bottomMargin=20*mm,title='Асистент аналітика енергоспоживання Whitepaper',author='Шевчук Максим Вікторович')
doc.build(story,onFirstPage=header,onLaterPages=header)

# Editable counterpart from the same page content. PDF remains the submission master.
wd=Document();sec=wd.sections[0]
sec.page_width=Mm(210);sec.page_height=Mm(297)
sec.top_margin=Mm(20);sec.bottom_margin=Mm(20);sec.left_margin=Mm(20);sec.right_margin=Mm(10)
sec.different_first_page_header_footer=True
for s in ['Normal','Title','Heading 1','Heading 2','Caption']:
    st=wd.styles[s];st.font.name='Times New Roman';st.font.size=Pt(14);st.font.color.rgb=RGBColor(0,0,0)
    st.paragraph_format.space_before=Pt(0);st.paragraph_format.space_after=Pt(0)
wd.styles['Normal'].paragraph_format.line_spacing=1.5
wd.styles['Normal'].paragraph_format.first_line_indent=Mm(12.5)
h=sec.header.paragraphs[0];h.alignment=WD_ALIGN_PARAGRAPH.RIGHT
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');h._p.append(fld)
import re
def clean(t):return re.sub('<[^>]+>','',t.replace('<br/>','\n')).replace('&nbsp;',' ').replace('&lt;','<').replace('&gt;','>').replace('&amp;','&')
for idx,pg in enumerate(PAGES):
    if idx:wd.add_page_break()
    for item in pg['items']:
        if item[0]=='space':
            pp=wd.add_paragraph();pp.paragraph_format.space_after=Mm(item[1]);continue
        if item[0]=='p':
            _,t,k=item
            pp=wd.add_paragraph(style='Title' if k=='title' else 'Heading 1' if k=='heading' else 'Normal')
            pp.add_run(clean(t));pp.paragraph_format.keep_with_next=k in ['heading','title']
            if k in ['tight','small','caption','toc','code']:pp.paragraph_format.line_spacing=1.0
            if k!='body':pp.paragraph_format.first_line_indent=Mm(0)
            if k in ['center','heading','title','caption']:pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
            elif k=='right':pp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
            elif k=='body':pp.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
            for r in pp.runs:
                r.font.size=Pt(12 if k in ['small','caption','toc','code'] else 20 if k=='title' else 14)
                r.bold=k in ['heading','title']
                if k=='code':r.font.name='Consolas'
            if k=='code':
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'F2F2F2');pp._p.get_or_add_pPr().append(sh)
        elif item[0]=='table':
            _,cap,heads,rows,widths=item
            pp=wd.add_paragraph(cap);pp.paragraph_format.first_line_indent=Mm(0)
            tb=wd.add_table(rows=1,cols=len(heads));tb.style='Table Grid'
            for i,v in enumerate(heads):tb.rows[0].cells[i].text=v
            for row in rows:
                cells=tb.add_row().cells
                for i,v in enumerate(row):cells[i].text=v
            for row in tb.rows:
                for i,c in enumerate(row.cells):
                    c.width=Mm(widths[i])
                    for pp in c.paragraphs:
                        pp.paragraph_format.first_line_indent=Mm(0);pp.paragraph_format.line_spacing=1
                        for r in pp.runs:r.font.size=Pt(14)
        elif item[0]=='fig':
            _,key,cap,height=item
            # PNG is generated separately from reviewed vectors for portable Word support.
            png=OUT/'figures'/f'{key}.png'
            if png.exists():wd.add_picture(str(png),width=Mm(176))
            pp=wd.add_paragraph(cap);pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
            pp.paragraph_format.first_line_indent=Mm(0)
            for r in pp.runs:r.font.size=Pt(12)
wd.save(OUT/'ЛР16_Шевчук_ФЕІм-13с.docx')
# The bundled local helper removes title borders and normalizes black text.
helper=OUT/'tools/normalize_report_docx.py'
if helper.exists():
    import importlib.util, io
    spec=importlib.util.spec_from_file_location('normalizer',helper)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    docx_path=OUT/'ЛР16_Шевчук_ФЕІм-13с.docx'
    buff=io.BytesIO()
    with zipfile.ZipFile(docx_path) as srczip, zipfile.ZipFile(buff,'w',zipfile.ZIP_DEFLATED) as dstzip:
        for item in srczip.infolist():
            data=srczip.read(item.filename)
            if item.filename.startswith('word/') and item.filename.endswith('.xml'):
                data=module.normalize(data,item.filename)
            dstzip.writestr(item,data)
    docx_path.write_bytes(buff.getvalue())
(OUT/'report_content.json').write_text(json.dumps(PAGES,ensure_ascii=False,indent=2),'utf-8')
(OUT/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
(OUT/'calculations.json').write_text(json.dumps({'monthly_gross_uah':25000,'monthly_net_uah':16000,'hours_saved':1000*5/60,'payback_months':2.5,'break_even_minutes':1.8,'latency_mean_reduction_percent':100*(1-summary[3]['mean_seconds']/summary[0]['mean_seconds']),'latency_p95_reduction_percent':100*(1-summary[3]['p95_seconds']/summary[0]['p95_seconds']),'input_token_reduction_percent':100*(1-summary[3]['input_tokens']/summary[0]['input_tokens'])},ensure_ascii=False,indent=2),'utf-8')
print(pdf_path)
