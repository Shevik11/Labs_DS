from pathlib import Path
import json, ast, re, textwrap
from xml.sax.saxutils import escape
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, PageBreak, Spacer, Preformatted, KeepTogether
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

ROOT=Path(__file__).resolve().parent
(ROOT/'work').mkdir(exist_ok=True)
STEM='ЛР11_Шевчук_ФЕІм-13с'
def load(n): return json.loads((ROOT/n).read_text(encoding='utf-8'))
retrieval=load('results/retrieval.json'); rag=load('results/rag.json'); chunks=load('results/chunking.json'); run=load('results/run.json')
for name,file in [('TNR','times.ttf'),('TNRB','timesbd.ttf'),('CONS','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNRB',italic='TNR',boldItalic='TNRB')

pages=[]
def page(*items): pages.append(items)
def h(s): return ('h',s)
def p(s): return ('p',s)
def table(title,headers,rows,widths): return ('table',title,headers,rows,widths)
def code(s): return ('code',s)
def image(path,caption,width): return ('image',str(path),caption,width)
def fmt(v): return f'{v:.2f}'.replace('.',',')

page(h('Мета та зв’язок із лабораторною роботою №8'),
 p('Мета роботи — доповнити матеріали енергетичної бази знань із ЛР8 векторним пошуком і RAG: розбити документи на фрагменти, побудувати індекс, сформувати відповіді з джерелами та порівняти якість пошуку.'),
 p('У ЛР8 вже створено граф Neo4j, виконано імпорт онтології й фактичних даних, підготовлено Cypher-запити та досліджено індексацію [1, розд. 2–12]. Тут ці результати є джерелами корпусу. Хід повторного імпорту та налаштування Neo4j не входить до поточного дослідження.'),
 table('Таблиця 1 — Що додано до ЛР8',['Основа з ЛР8','Нове в ЛР11'],[
 ['Граф та онтологія','Текстовий корпус із метаданими'],
 ['Пошук за властивостями і зв’язками','BM25, embeddings, FAISS та RRF'],
 ['Відповідь Cypher','RAG-відповідь із цитатою або відмовою'],
 ['Час і DB Hits','Recall@1, @3, @5 і перевірка цитат'],
 ],[83,97]),
 p('Виконано п’ять нових результатів: chunking; векторний індекс; RAG; порівняння пошуку; аналіз помилок і перевірка покращення. Експерименти проведено локально на CPU, seed=42. Замість зовнішнього LLM API використано локальну FLAN-T5-small; це відмінність від переліку інструментів у завданні [3].'))

page(h('1 Корпус і дві стратегії chunking'),
 p('Корпус містить 22 логічні документи: D01–D20 — нові англомовні тематичні технічні нотатки за фактами ЛР8; D21 — основний текст звіту [1]; D22 — правила відображення онтології [2]. Нотатки є похідними власними матеріалами, а не незалежними зовнішніми статтями. Кожна має посилання на джерело; оригінали збережено з SHA-256.'),
 p('Із PDF прибрано номери сторінок і зайві пробіли. Токени визначає tokenizer MiniLM. Фіксоване вікно містить до 400 токенів, перекриття — 60 токенів (15%). Вікна не перетинають меж PDF-сторінок. Структурний варіант зберігає розділи й абзаци; довгі блоки також обмежені 400 токенами.'),
 table('Таблиця 2 — Результати розбиття',['Стратегія','Фрагменти','Середня довжина'],[
 ['Фіксована','38','207,00 токена'],['Структурна','72','104,43 токена']], [67,45,68]),
 p('Метадані фрагмента: id, doc_id, section, page, language, source та source_page. Для MD page=1 означає умовну сторінку; source_page посилається на вихідний звіт. D21 зберігає справжні номери PDF-сторінок.'),
 p('Приклад невдалого розрізу: fixed-0034 завершується всередині ідентифікатора «OntologyPro», а fixed-0035 починається з «язок UPPER_SNAKE_CASE». Інший фрагмент закінчується після «numericValue і». Перекриття повертає сусідній контекст, але саме по собі не забезпечує завершені речення. Структурний поділ розділяє факт та його пояснення; це може погіршити їх спільне знаходження.'))

samples=load('results/top3_examples.json')
page(h('2 Векторний індекс та фільтрація'),
 p('Для embeddings використано paraphrase-multilingual-MiniLM-L12-v2: 384 виміри, максимальна довжина входу встановлена 512 токенів. Фрагменти до 400 токенів уміщуються зі спеціальними токенами. Вектори L2-нормалізовано; IndexFlatIP ранжує за внутрішнім добутком, який для таких векторів дорівнює косинусній схожості.'),
 p('Для обох стратегій збережено vectors.faiss, embeddings.npy та metadata.json. Повторне читання індексу відтворило результати контрольного пошуку. Норми векторів перевірено з похибкою менше 10⁻⁵. Фільтри language/doc_id застосовано перед top-k: для дозволених кандидатів створюється точний підіндекс.'),
 table('Таблиця 3 — П’ять перевірок dense для структури',['Питання','Очікується','Документи top-3'],[
 [s['id'],s['expected'][0],', '.join(x['doc_id'] for x in s['top3'])] for s in samples], [43,47,90]),
 p('У цих п’яти запитах цільова нотатка потрапила до top-3. Перевірено language=en, language=uk, document=D15 та порожню вибірку language=de; усі результати відповідають фільтрам. Відсутня мова повертає порожній список.'),
 p('На відміну від range-індексів ЛР8 [1, розд. 10], цей індекс порівнює текстові подання. Навіть близький за змістом фрагмент може містити інший аспект питання, тому якість оцінюється окремо від працездатності індексу.'))

page(h('3 RAG і автоматична перевірка цитат'),
 p('Конвеєр: запит → embedding → гібридний пошук → контекст → FLAN-T5-small → перевірка підтвердження → відповідь із [id] або «Недостатньо даних». Фінальна конфігурація використовує fixed, language=en і top-1. Одне джерело скорочує контекст для малої локальної моделі; перевірки top-3 для пошуку виконано окремо.'),
 p('Промпт вимагає відповідати лише з контексту, копіювати короткий точний фрагмент і відмовляти за відсутності даних. Інструкції всередині джерела трактуються як дані. Еталонна відповідь не передається ні моделі, ні пошуку. Застосовано greedy decoding, max_new_tokens=70.'),
 p('FLAN-T5 часто повертає тільки число. Тому підтверджений фрагмент розгортається до повного речення того самого джерела. Це екстрактивне постопрацювання, а не додаткова генерація. Ідентифікатор цитати додає програма лише після збігу з реально отриманим фрагментом. Якщо запитаний рік відсутній у контексті, відповідь відхиляється.'),
 p('Приклад Q01: сирий вихід моделі — «43746». Підтверджена відповідь — «The complete Lab8 graph contains 43746 nodes and 199287 relationships. [fixed-0001]». Числа походять із ЛР8 [1, розд. 3], а новим результатом є їх знаходження та повернення з перевіреним посиланням.'),
 p('Рядковий збіг доводить наявність цитованого тексту, але не гарантує логічної відповідності будь-якому питанню. Повноту перевірено додатково на заданих восьми відповідних питаннях; механізм відмови — на двох питаннях без відповіді.'))

page(h('3 Результати десяти RAG-запитів'),
 table('Таблиця 4 — Фінальні відповіді та джерела',['ID','Зміст відповіді','Цитата'],[
 ['Q01','43 746 вузлів; 199 287 зв’язків','fixed-0001'],
 ['Q03','34 085 повних годин','fixed-0003'],
 ['Q04','9 530 тестових прогнозів','fixed-0004'],
 ['Q07','502 пропущені години','fixed-0007'],
 ['Q09','Обмеження lab8_entity_id','fixed-0009'],
 ['Q11','36 зв’язків SUBCLASS_OF','fixed-0011'],
 ['Q15','MAE: 0,335966 та 0,423517 kWh','fixed-0015'],
 ['Q20','forecastKwh > 1,5613','fixed-0020'],
 ['U01','Номер фізичного лічильника: недостатньо даних','Відмова'],
 ['U02','Споживання в січні 2025: недостатньо даних','Відмова'],
 ],[20,115,45]),
 p('У таблиці наведено стислий український переказ; точні англійські відповіді, промпти та сирі виходи є в results/rag.json. Усі 8 прийнятих цитат підтверджено текстом отриманих джерел. Повні відповіді містять потрібні числа або назви. Обидва питання без відповіді завершилися відмовою.'),
 p('У початковій конфігурації structure/top-3 без розгортання речення повними були 4 із 8 відповідей. Фінальна дала 8 із 8. Одночасно змінено контекст, chunking і постопрацювання, тому цей результат не ізолює внесок кожної зміни. Початкові відповіді збережено в rag_initial.json.'))

metric_rows=[]
for strategy in ['fixed','structure']:
    for method in ['bm25','dense','hybrid']:
        m=retrieval[strategy]['metrics'][method]
        metric_rows.append([strategy,method,*[fmt(m[str(k)]) for k in [1,3,5]]])
page(h('4 Порівняння BM25 dense та RRF'),
 p('BM25 і dense працюють з однаковими фрагментами кожної стратегії. Гібрид використовує RRF: score(d)=Σ 1/(60+rank(d)), де ранг починається з 1. Для 20 заздалегідь підготовлених питань визначено одну цільову тематичну нотатку. Recall@k тут дорівнює частці питань, для яких її знайдено серед перших k фрагментів.'),
 table('Таблиця 5 — Фактичний recall@k',['Chunking','Метод','@1','@3','@5'],metric_rows,[48,42,30,30,30]),
 image(ROOT/'figures/recall.png','Рис. 1 — Recall для структурного розбиття на 20 питаннях',155),
 p('Рис. 1 показує результати структурного варіанта. Фіксований гібрид має recall@1=1,00; це результат на даному малому наборі, а не гарантія на нових питаннях.'))

page(h('4 Інтерпретація та межі порівняння'),
 p('На структурному розбитті BM25 помиляється на першій позиції для Q04 та Q08. В обох випадках запит використовує слово population, яке зустрічається і в описі тестових прогнозів, і в описі географічної вибірки. Dense знаходить потрібні нотатки першими; це конкретний приклад виграшу семантичного пошуку на синонімічному формулюванні.'),
 p('Для Q14 dense віддає перевагу українському першоджерелу D21 та опису одиниць D05. Гібрид повертає цільову D14 другою. Після об’єднання факту з поясненням у fixed D14 стає першою. Отже, надмірне дроблення короткої нотатки іноді погіршує пошук.'),
 p('Для питань із назвами constraint, SUBCLASS_OF, Q7 та forecastKwh пошукові методи використовують точні технічні терміни. У цьому наборі немає підстав стверджувати загальну перевагу BM25 для всіх кодів або dense для всіх довгих запитів: висновок обмежено реально перевіреними прикладами.'),
 p('Важлива межа метрики: D21 або D22 іноді містять правильний факт, але не є призначеною тематичною нотаткою D01–D20. Тому така знахідка не зарахована. Оцінюється навігація до конкретного документа, а не всі можливі релевантні відповіді. У results/retrieval.json збережено повні top-5 і тип кожного питання.'),
 p('Нотатки та питання мають спільне походження з ЛР8. Порівняння конфігурацій проведено на тих самих 20 питаннях, без окремої незалежної тестової вибірки після налаштування. Підсумкові значення слід вважати дослідницькою перевіркою реалізації.'))

page(h('5 Помилки та перевірене покращення'),
 table('Таблиця 6 — Причини й перевірки',['Категорія','Спостереження'],[
 ['Немає в корпусі','U01: серійний номер невідомий; U02: немає даних за 2025 рік. Отримано відмови.'],
 ['Chunking','Q14: факт та пояснення розділено. Fixed підняв цільову нотатку на 1-ше місце.'],
 ['Embeddings / ранг','Q14 dense: знайдено близькі першоджерела, але не призначену D14.'],
 ['Фільтр','language=de закономірно повертає порожній список; це не збій embeddings.'],
 ['Промпт / модель','Початковий RAG повертав короткі неповні фрагменти; підтримане речення відновлює контекст.'],
 ],[50,130]),
 p('Основне перевірене покращення — використати fixed замість structure у гібридному пошуку. На тих самих 20 питаннях recall@1 зріс із 0,95 до 1,00: +0,05, тобто +5 відсоткових пунктів або одне додаткове питання. Recall@3 та @5 залишилися 1,00. Це окреме порівняння змінює лише стратегію chunking.'),
 p('Додатковий дослід: залишення найкращого фрагмента кожного документа прибрало повтори джерел. Для structure/dense recall@5 зріс із 0,95 до 1,00; для hybrid виграшу не виявлено. Результати містяться в improvement.json. Фінальний RAG: fixed, RRF, англійські джерела, top-1, локальна FLAN-T5-small та перевірка цитованого речення.'))

page(h('Висновок'),
 p('До бази знань із ЛР8 додано текстовий пошук і RAG. Побудовано два набори фрагментів та збережені FAISS-індекси, реалізовано фільтрацію, BM25, dense і RRF. На 20 питаннях фіксований гібрид знаходить цільову нотатку першим у 20 випадках; структурний — у 19. Для десяти RAG-запитів отримано вісім підтверджених відповідей і дві відмови.'),
 p('Нові результати показують вплив chunking і способу подання контексту. Факти про Neo4j, енергоспоживання та похибки прогнозу запозичено з ЛР8 із посиланнями; вони не видаються за нові вимірювання. Обмеження: малий похідний корпус, відсутність незалежного тесту після налаштування, локальна мала мовна модель та обмежена сила рядкової перевірки цитат.'),
 h('Джерела'),
 p('[1] Шевчук М. В. Лабораторна робота №8 «Збереження знань у графовій базі даних для візуалізації енергетичних даних». 2026. Вихідний звіт: D:/LNU/DS/8; копія в пакеті: sources/lab8/report.pdf. Посилання в тексті ведуть на розділи цього звіту.'),
 p('[2] Матеріали ЛР8: MODEL_MAPPING.md, validation.json і benchmark_comparison.json від запуску sandbox_20261016T054342525797Z. Копії: sources/lab8/.'),
 p('[3] ЛР11_завдання.pdf. «Векторна база даних та RAG», 2026–2027 н. р. Копія: sources/assignment11.pdf.'),
 h('Декларація використання ШІ'),
 p('OpenAI Codex використано для підготовки коду, нотаток, питань і звіту; FLAN-T5-small — як компонент RAG. Код фактично запущено, результати та цитати перевірено. Промпти й сирі відповіді збережено. Повна декларація, початковий запит користувача та спосіб перевірки наведені в AI_DECLARATION.md.'))

# Formatting-only excerpts of the executed source, kept with the report.
import math
extracts=load('report_assets/formatted_extracts.json')
for letter,(name,block) in zip(['А','Б','В'],extracts):
    wrapped=[]
    for line in block:
        wrapped.extend(textwrap.wrap(line,width=71,replace_whitespace=False,drop_whitespace=False,break_long_words=True,break_on_hyphens=False,subsequent_indent='    ') or [''])
    count=math.ceil(len(wrapped)/42)
    size=math.ceil(len(wrapped)/count)
    title={'make_chunks':'Розбиття тексту','rank':'Пошук і RRF','citation':'Перевірка та прив’язка цитат'}[name]
    for n in range(0,len(wrapped),size):
        page(h(f'Додаток {letter} {title}'+(' — продовження' if n else '')),
             p(f'run_lab11.py — {name}; форматування для читання'),
             code('\n'.join(wrapped[n:n+size])))

doc=Document(); sec=doc.sections[0]
sec.page_width=Cm(21); sec.page_height=Cm(29.7)
sec.top_margin=sec.bottom_margin=sec.left_margin=Cm(2); sec.right_margin=Cm(1)
sec.different_first_page_header_footer=True
for style in doc.styles:
    if style.type in [1,2]:
        style.font.name='Times New Roman'; style.font.size=Pt(14); style.font.color.rgb=RGBColor(0,0,0)
normal=doc.styles['Normal']; normal.paragraph_format.line_spacing=1.5
normal.paragraph_format.first_line_indent=Cm(1.25); normal.paragraph_format.space_after=Pt(0)
normal.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
header=sec.header.paragraphs[0]; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
field=OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE'); header._p.append(field)
def dpara(text,size=14,bold=False,align=None,space_before=0):
    para=doc.add_paragraph(); para.paragraph_format.space_before=Pt(space_before)
    if align is not None: para.alignment=align; para.paragraph_format.first_line_indent=Pt(0)
    rr=para.add_run(text); rr.font.size=Pt(size); rr.bold=bold
    return para

center=WD_ALIGN_PARAGRAPH.CENTER; right=WD_ALIGN_PARAGRAPH.RIGHT
dpara('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ',12,align=center)
dpara('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА',12,align=center)
dpara('Факультет електроніки і комп’ютерних технологій',align=center)
title=dpara('Звіт',bold=True,align=center,space_before=85); title.style=doc.styles['Title']
dpara('про виконання лабораторної роботи №11',align=center,space_before=8)
dpara('з курсу «Вибрані розділи науки про дані»',align=center,space_before=8)
dpara('«Векторна база даних та RAG\nна матеріалах лабораторної роботи №8»',align=center,space_before=15)
dpara('Виконав:',bold=True,align=right,space_before=65)
dpara('студент групи ФЕІм-13с',align=right)
dpara('Шевчук Максим Вікторович',align=right)
dpara('Перевірив:',bold=True,align=right,space_before=12)
dpara('Парубочий В. О.',align=right)
dpara('Львів 2026',align=center,space_before=60)

body_style=ParagraphStyle('body',fontName='TNR',fontSize=14,leading=21,alignment=TA_JUSTIFY,firstLineIndent=12.5*mm,spaceAfter=5)
heading_style=ParagraphStyle('heading',fontName='TNRB',fontSize=14,leading=18,alignment=TA_CENTER,spaceAfter=10,keepWithNext=True)
cell_style=ParagraphStyle('cell',fontName='TNR',fontSize=14,leading=16)
caption_style=ParagraphStyle('caption',fontName='TNR',fontSize=12,leading=14,alignment=TA_CENTER,spaceAfter=6)
code_style=ParagraphStyle('code',fontName='CONS',fontSize=12,leading=14.2,backColor=colors.HexColor('#F2F2F2'),borderColor=colors.HexColor('#D9D9D9'),borderWidth=.5,borderPadding=4)
story=[Spacer(1,1)]
def para(s,style): return Paragraph(escape(s).replace('\n','<br/>'),style)
for items in pages:
    story.append(PageBreak()); doc.add_page_break()
    for item in items:
        kind=item[0]
        if kind=='h':
            pp=dpara(item[1],bold=True,align=center); pp.paragraph_format.keep_with_next=True; pp.paragraph_format.space_after=Pt(8)
            story.append(para(item[1],heading_style))
        elif kind=='p':
            dpara(item[1]); story.append(para(item[1],body_style))
        elif kind=='table':
            _,title,heads,rows,widths=item
            pp=dpara(title,align=WD_ALIGN_PARAGRAPH.LEFT); pp.paragraph_format.keep_with_next=True
            tab=doc.add_table(rows=1,cols=len(heads)); tab.style='Table Grid'; tab.autofit=False
            for i,(head,width) in enumerate(zip(heads,widths)):
                tab.columns[i].width=Cm(width/10); tab.rows[0].cells[i].text=head
            for row in rows:
                cells=tab.add_row().cells
                for i,value in enumerate(row): cells[i].text=str(value)
            for ri,row in enumerate(tab.rows):
                for ci,cell in enumerate(row.cells):
                    cell.width=Cm(widths[ci]/10)
                    for pp in cell.paragraphs:
                        pp.paragraph_format.first_line_indent=Pt(0); pp.paragraph_format.line_spacing=1
                        pp.paragraph_format.space_after=Pt(4); pp.paragraph_format.space_before=Pt(4)
                        for rr in pp.runs: rr.bold=ri==0
            cells=[[para(str(x),cell_style) for x in row] for row in [heads]+rows]
            rt=Table(cells,colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
            rt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.black),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([para(title,ParagraphStyle('tc',parent=body_style,firstLineIndent=0,keepWithNext=True)),rt,Spacer(1,8)])
        elif kind=='image':
            _,path,caption,width=item
            pp=doc.add_paragraph(); pp.alignment=center; pp.paragraph_format.first_line_indent=Pt(0); pp.paragraph_format.keep_with_next=True
            pp.add_run().add_picture(path,width=Cm(width/10))
            pp=dpara(caption,12,align=center); pp.paragraph_format.line_spacing=1
            from PIL import Image as PILImage
            with PILImage.open(path) as im: iw,ih=im.size
            story.append(KeepTogether([Image(path,width=width*mm,height=width*mm*ih/iw),para(caption,caption_style)]))
        else:
            pp=doc.add_paragraph(); pp.paragraph_format.first_line_indent=Pt(0); pp.paragraph_format.line_spacing=1
            rr=pp.add_run(item[1]); rr.font.name='Consolas'; rr.font.size=Pt(12)
            pr=pp._p.get_or_add_pPr(); shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'F2F2F2'); pr.append(shade)
            borders=OxmlElement('w:pBdr')
            for side in ['top','left','bottom','right']:
                b=OxmlElement('w:'+side); b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'4'); b.set(qn('w:color'),'D9D9D9'); b.set(qn('w:space'),'3'); borders.append(b)
            pr.append(borders)
            listing=Table([[Preformatted(item[1],code_style)]],colWidths=[180*mm])
            listing.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F2F2F2')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#D9D9D9')),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
            story.append(listing)

doc.core_properties.author='Шевчук Максим Вікторович'; doc.core_properties.title='ЛР11 Векторна база даних та RAG на матеріалах ЛР8'
doc.save(ROOT/(STEM+'.docx'))
def first(canvas,document):
    def text(t,y,size=14,bold=False,alignment='center'):
        canvas.setFont('TNRB' if bold else 'TNR',size); canvas.setFillColor(colors.black)
        if alignment=='right': canvas.drawRightString(A4[0]-20*mm,A4[1]-y,t)
        else: canvas.drawCentredString(A4[0]/2,A4[1]-y,t)
    text('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ',80,12)
    text('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА',98,12)
    text('Факультет електроніки і комп’ютерних технологій',120)
    text('Звіт',232,bold=True)
    text('про виконання лабораторної роботи №11',260)
    text('з курсу «Вибрані розділи науки про дані»',288)
    text('«Векторна база даних та RAG',330)
    text('на матеріалах лабораторної роботи №8»',352)
    text('Виконав:',480,bold=True,alignment='right')
    text('студент групи ФЕІм-13с',502,alignment='right')
    text('Шевчук Максим Вікторович',524,alignment='right')
    text('Перевірив:',562,bold=True,alignment='right')
    text('Парубочий В. О.',584,alignment='right')
    text('Львів 2026',755)
def later(canvas,document):
    canvas.setFont('TNR',14); canvas.drawRightString(A4[0]-10*mm,A4[1]-13*mm,str(document.page))
pdf=SimpleDocTemplate(str(ROOT/(STEM+'.pdf')),pagesize=A4,leftMargin=20*mm,rightMargin=10*mm,topMargin=20*mm,bottomMargin=20*mm,title=doc.core_properties.title,author=doc.core_properties.author)
pdf.build(story,onFirstPage=first,onLaterPages=later)
(ROOT/'work/report_content.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
print('Created',STEM,'logical pages',len(pages)+1)
