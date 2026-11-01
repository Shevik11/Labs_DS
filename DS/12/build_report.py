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
STEM='ЛР12_Шевчук_ФЕІм-13с'
def load(n): return json.loads((ROOT/n).read_text(encoding='utf-8'))
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
run=load('results/run.json'); demo=load('results/demo.json')

page(h('Мета, завдання та початкові дані'),
 p('Мета роботи — інтегрувати векторний пошук, граф знань Neo4j та локальну мовну модель в одну систему з REST API і вебінтерфейсом. Реалізовано нові модулі engine.py, app.py, HTML-форму та автоматичні перевірки.'),
 p('Використано власні матеріали попередніх лабораторних: повний енергетичний граф ЛР8–9 та fixed-індекс ЛР11. Граф повторно імпортовано в окрему порожню локальну базу. Вихідні лабораторні не змінено; нових прогнозів електроспоживання не створювали.'),
 table('Таблиця 1 — Повторне використання результатів',['Матеріал','Обсяг / призначення'],[
 ['Граф ЛР8–9','43 746 вузлів; 199 287 зв’язків'],
 ['FAISS ЛР11','38 фрагментів; вектори 384 вимірів'],
 ['Embeddings','multilingual MiniLM; cosine / IndexFlatIP'],
 ['Локальна LLM','FLAN-T5-small; CPU; seed 42'],
 ['Нове в ЛР12','GraphRAG, API, HTML, тести, демонстрація']], [54,126]),
 p('Завдання складається з п’яти результатів: архітектура; поєднання контекстів; REST API; вебінтерфейс; відтворюваний запуск і перевірки. Відомості про корпус та граф успадковано з власних звітів, а інтеграційні результати отримано під час поточних запусків.'))

page(h('1 Архітектура системи та межі довіри'),
 p('Браузер надсилає JSON у FastAPI. Сервер отримує фрагменти FAISS і шляхи Neo4j, формує обмежений контекст, запускає LLM та повертає відповідь з доказами. На рис. 1 показано межу між клієнтом і сервером та місця зберігання секретів.'),
 image(ROOT/'figures/architecture.png','Рис. 1 — Архітектура GraphRAG та межі довіри',180),
 p('Запит і документи є недовіреними даними. API перевіряє типи, довжину та параметри; текст користувача не стає кодом Cypher. LLM не має інструментів, доступу до файлової системи або права змінювати граф. Корпус не задає інструкцій виконання.'),
 p('У демонстрації всі компоненти локальні; зовнішній ключ LLM не потрібен. Пароль зовнішньої Neo4j задається лише змінною NEO4J_PASSWORD у серверному середовищі. Локальний режим без пароля прив’язано до 127.0.0.1.'))

page(h('1 Потоки даних, ризики та вимоги'),
 table('Таблиця 2 — Формати обміну',['Потік','Формат'],[
 ['Клієнт → API','question, top_k, use_graph: JSON'],
 ['API → FAISS','Нормалізований float32-вектор запиту'],
 ['API → Neo4j','Фіксований Cypher + параметр ids'],
 ['API → LLM','Інструкція, «Фрагменти», «Зв’язки графа», питання'],
 ['API → клієнт','answer, sources[], graph[], tokens, request_id']], [51,129]),
 table('Таблиця 3 — Ризики та реалізовані заходи',['Ризик','Захід'],[
 ['Cypher-ін’єкція','Параметри; статичні типи ребер; жодної генерації запиту'],
 ['Prompt injection','Докази позначені як дані; LLM без інструментів'],
 ['Витік','Логи без запитань і цитат; секрети поза ZIP; textContent у HTML'],
 ['Збій / перевантаження','503/504; таймаути; 429 для паралельної генерації']], [51,129]),
 p('Вимоги для локальної демонстрації: питання 3–500 символів, top_k 1–5, графові шляхи до 2 ребер, не більше 12 шляхів, контекст до 260 токенів T5 плюс інструкція і питання. Цільова затримка теплого запиту — до 5 с; це ціль, а не доведена гарантія p95. Таймаут API — 30 с, транзакції Neo4j — 3 с. Обсяг корпусу — 38 фрагментів; права API — читання.'))

page(h('2 Поєднання векторного і графового контекстів'),
 p('vector_context(q) кодує питання multilingual MiniLM, виконує FAISS-пошук cosine та вибирає top-k серед англомовних нотаток. Повертаються id, doc_id, текст, назва, сторінка джерела та score. Індекс і метадані завантажуються з ЛР11 без повторного навчання.'),
 p('graph_context(q) розпізнає точні ідентифікатори або назви сутностей онтології. Наприклад, forecastChart зіставляється з owl:forecastChart. Neo4j розширює їх за BASED_ON_MODEL, ANALYZES_SERIES та SUBCLASS_OF на глибину 1–2. Це словникове розпізнавання, а не універсальний NER.'),
 p('merge_context видаляє однакові тексти та резервує бюджет спочатку для графа, потім для документів. Токени рахує tokenizer LLM; довгі фрагменти скорочуються за символьними offsets оригіналу. Заголовки «Фрагменти» та «Зв’язки графа» зберігаються. Повний промпт не обрізається приховано.'),
 p('FLAN-T5 генерує короткий вихід. Програма приймає лише рядково підтверджену цитату, розгортає її до речення й окремо виводить перевірені шляхи графа та текстовий контекст. Це явне екстрактивне постопрацювання; шляхи не видаються за самостійну генерацію LLM.'),
 p('Відмова «Недостатньо даних» спрацьовує за непідтвердженим виходом без графа або за запитаним роком, якого немає у контексті. Рядковий збіг не гарантує відповідності питанню, тому наступне порівняння містить також помилку звичайного RAG.'))

page(h('2 Багатокрокове питання та порівняння'),
 p('Питання: Which series is analyzed by the model on which forecastChart is based? Потрібно знайти модель, на якій ґрунтується графік, а потім часовий ряд, який аналізує ця модель.'),
 table('Таблиця 4 — Той самий запит у двох режимах',['Режим','Фактичний результат'],[
 ['Лише векторний RAG','Цитата про AttentionVisualization і HighConsumptionForecast; цільового ряду немає'],
 ['RAG + Neo4j','forecastChart → BASED_ON_MODEL → regressor → ANALYZES_SERIES → predictionSeries']], [46,134]),
 p('Граф змінив відповідь: додано owl:predictionSeries із підтвердженим шляхом у два ребра. Текстовий контекст окремо повернув відомості про 9 530 збережених прогнозів. Цей текст описує дані прогнозів, але сам по собі не доводить потрібний ланцюжок; доказом зв’язку є Neo4j.'),
 p('В одному теплому запуску vector-only зайняв '+f"{demo[1]['seconds']:.3f}"+' с, а з графом — '+f"{demo[2]['seconds']:.3f}"+' с. Вимірювання охоплює пошук, Neo4j, генерацію й постопрацювання, але не початкове завантаження моделей. Одного повтору недостатньо для оцінки стабільної продуктивності.'),
 p('Повні запити, обидва промпти, raw_model_answer, токени й цитати збережено у results/demo.json. Очікувана відповідь не передається моделі як прихований еталон.'))

page(h('3 REST API та обробка помилок'),
 table('Таблиця 5 — Ендпоінти API',['Маршрут','Результат'],[
 ['POST /ask','Answer: текст, статус, джерела, шляхи, токени, request_id'],
 ['GET /health','Реальний запит Neo4j; стан індексу та LLM'],
 ['GET /sources/{id}','Повний фрагмент і локатори; 404, якщо id немає'],
 ['GET /docs','Інтерактивна OpenAPI-документація']], [58,122]),
 p('Pydantic-модель Ask використовує strict=True та extra=forbid. Рядок question після обрізання пробілів має 3–500 символів, top_k — ціле число 1–5, use_graph — bool. Модель Answer перевіряє структуру джерел і графових шляхів перед відправленням.'),
 p('Некоректні дані повертають 422 без віддзеркалення введеного тексту. Для недоступного компонента використано 503, таймауту LLM — 504, зайнятої генерації — 429. Після таймауту worker залишається зайнятим до завершення, що запобігає накопиченню нових генерацій.'),
 p('Кожен HTTP-запит отримує серверний UUID у X-Request-ID та JSON. Структурований журнал містить request_id, duration_ms, status і tokens; питання, відповіді, паролі та персональні дані не журналюються. При запуску uvicorn access-log вимкнено.'),
 p('API перевірено через OpenAPI, TestClient та справжні curl-запити до /ask, /health і /sources/fixed-0001. Для /ask отримано HTTP 200 та відповідь із 43 746 вузлами і 199 287 зв’язками.'))

page(h('4 Вебінтерфейс — просте питання'),
 p('HTML-форма містить поле питання, перемикач графового контексту та три готові приклади. Під час виконання кнопка блокується й показується «Обробка питання…»; помилка відображається окремим повідомленням. На рис. 2 — фактична відповідь на питання про розмір графа.'),
 image(ROOT/'figures/simple_result.png','Рис. 2 — Відповідь, джерела та цитати для простого питання',180),
 p('Програма повернула речення про 43 746 вузлів і 199 287 зв’язків із посиланням fixed-0001. Для цього питання словникові сутності не знайдено; використаних графових шляхів немає. На рисунку показано фрагмент реального інтерфейсу, повний скриншот збережено у figures/simple.png.'))

page(h('4 Вебінтерфейс — питання у два кроки'),
 p('На рис. 3 показано відповідь для питання про часовий ряд моделі forecastChart. Інтерфейс виводить цитати з переходом до /sources/{id}, а нижче — вузли й назви використаних ребер Neo4j.'),
 image(ROOT/'figures/multihop_result.png','Рис. 3 — Текстовий контекст і підтверджений шлях у два ребра',180),
 p('Відповідь пов’язує owl:forecastChart, owl:regressor та owl:predictionSeries. Шляхи мають окремі ідентифікатори graph-1 і graph-2. Увесь динамічний вміст додається через textContent; отриманий текст не виконується як HTML.'))

page(h('4 Вебінтерфейс — відсутня відповідь'),
 p('Питання: What was the household consumption in January 2025? Джерела попередніх лабораторних не містять потрібного періоду. На рис. 4 система утримується від вигадування значення.'),
 image(ROOT/'figures/unanswerable_result.png','Рис. 4 — Відмова для непідтвердженого періоду 2025 року',180),
 p('Повернуто status=insufficient_data, текст «Недостатньо даних», порожні sources і graph. Правило відсутнього року перевірено саме на цьому прикладі; універсальна здатність відмовляти на будь-яке нерелевантне питання не доведена.'),
 p('Усі три сценарії виконано у headless Edge з реальною HTML-формою та API. Браузерний журнал не зафіксував JavaScript-помилок. Скриншоти є доказом роботи, GIF або відео додатково не створювалися.'))

page(h('5 Тести, запуск та відтворюваність'),
 table('Таблиця 6 — Дев’ять тестів pytest + TestClient',['Перевірка','Результат'],[
 ['Успішна відповідь і цитата','Пройдено'],['Некоректні дані / top_k','Пройдено'],['Питання довше 500 символів','Пройдено'],['Недоступний сервіс → 503','Пройдено'],['Таймаут → 504; зайнятість → 429','Пройдено'],['Схема відповіді / request_id','Пройдено'],['Джерела, 404, /docs, OpenAPI','Пройдено'],['Неготова БД /health → 503','Пройдено'],['Відсутність даних вводу в помилках і логах','Пройдено']], [140,40]),
 p('Тести обробників використовують контрольовані підміни Engine. Справжню інтеграцію окремо перевірено через demo.py, браузер і curl; результати збережено у results/. Порожню базу Neo4j створено, повний граф імпортовано та перевірено за лічильниками.'),
 p('29.10.2026 виконано повне встановлення залежностей у нове ізольоване Python-середовище на D: без системних пакетів. Перевірка pip check успішна. У порожню Neo4j-базу імпортовано 43 746 вузлів і 199 287 зв’язків. У новому середовищі пройшли 9 тестів API, чотири реальні запуски та інтеграційна перевірка шляхів і точності цитат. Ваги моделей повторно використано з ЛР11.'))

page(h('5 Інструкція запуску та декларація ШІ'),
 p('Пакет містить requirements.txt, README, імпортер, compose.yaml, альтернативний start_neo4j.ps1, завантажувач моделей з фіксованими revisions, тести, індекс, корпус, дані й докази. Ваги моделей, Python-середовище, двійкові файли Neo4j і паролі до ZIP не включено.'),
 code('python -m venv .clean\n.clean\\Scripts\\python -m pip install -r requirements.txt\ndocker compose up -d\n.clean\\Scripts\\python import_graph.py\n.clean\\Scripts\\python download_models.py\n.clean\\Scripts\\python -m pytest -q\n.clean\\Scripts\\python -m uvicorn app:app --port 8122\n  --host 127.0.0.1 --no-access-log'),
 p('Останню команду слід вводити одним рядком. Замість завантаження моделей можна задати MODELS_DIR на каталог ЛР11. У демонстрації використано локальний дистрибутив Neo4j 5.26.32 і Java 26; Docker-конфіг підготовлено, але Docker daemon на машині не працював.'),
 p('Декларація ШІ. Використано OpenAI Codex для аналізу завдання, розроблення інтеграції, тестів, документації та звіту. Основний запит: виконати лабораторну, використовуючи попередні роботи. Код перевірено фактичними запусками, тестами API, Neo4j, браузером і curl. Сама програма використовує multilingual MiniLM та FLAN-T5-small локально. Повна декларація — AI_DECLARATION.md.'),
 p('Результати потребують розуміння автором для усного захисту. Після перенесення на диск D: чисте встановлення та запуск повторно перевірено 29.10.2026. Докладні докази й повний список версій збережено у results/.'))

page(h('Висновок'),
 p('Створено навчальну інтегровану систему на власних матеріалах ЛР8–9 і ЛР11. Вона поєднує FAISS, граф Neo4j та FLAN-T5-small, надає три REST-ендпоінти, OpenAPI й HTML-інтерфейс. Контекст має токенний бюджет, джерела — локатори, графові шляхи — межу у два ребра.'),
 p('На багатокроковому прикладі граф додає зв’язок до owl:predictionSeries, відсутній у відповіді векторного RAG. Це конкретний доказ користі графового контексту, але не статистична оцінка якості GraphRAG. Для простого питання знайдено правильні лічильники; для 2025 року отримано відмову.'),
 p('Дев’ять тестів API та три браузерні сценарії пройшли. 29.10.2026 додатково підтверджено повне встановлення Python-залежностей у чисте ізольоване середовище на D: і відновлення графа в порожній Neo4j-базі. Повторні реальні запуски підтвердили працездатність інтеграції; відтворюваність задокументовано у README та results/clean_install.json.'),
 h('Відповіді до захисту'),
 p('1. Граф знаходить зв’язки та ланцюжки, які векторний пошук може не повернути одним фрагментом. 2. API використовує Pydantic, strict-типи, межі довжини та allowlist параметрів. 3. Журналюються лише технічні метадані, щоб не зберігати питання чи приватний вміст. 4. Межі довіри проходять між клієнтом і API, а також між інструкціями та отриманими доказами. 5. Для 100 запитів/с потрібні автентифікація, rate limiting, черга генерації, кеш, масштабовані workers і окремий сервіс LLM; одного CPU-процесу недостатньо.'))

page(h('Використані джерела'),
 p('1. Власні матеріали ЛР8–9: енергетичний граф, онтологія, MODEL_MAPPING, дані nodes.json і relationships.json. Звіт ЛР8 та опис відображення включено в sources/lab8/.'),
 p('2. Власні матеріали ЛР11: fixed FAISS-індекс, метадані, похідні нотатки та фіксовані revisions multilingual MiniLM і FLAN-T5-small. Нотатки не є незалежними зовнішніми статтями.'),
 p('3. FastAPI. Testing. Офіційна документація: https://fastapi.tiangolo.com/tutorial/testing/ (переглянуто 28.10.2026). Використано схему pytest + TestClient.'),
 p('4. Neo4j Python Driver Manual. Query the database; Further query mechanisms: https://neo4j.com/docs/python-manual/current/query-simple/ ; https://neo4j.com/docs/python-manual/current/query-advanced/ (переглянуто 28.10.2026). Використано параметри Cypher і Query(timeout=3).'),
 p('5. UCI Individual Household Electric Power Consumption. DOI: 10.24432/C58K54; CC BY 4.0. Джерело даних успадковано з попередніх лабораторних. Поточна робота не виконує повторного прогнозного експерименту.'))

# Relevant main implementation, extracted from the actual saved source.
modules=[('А','Векторний, графовий пошук і злиття контексту','engine.py',['vector_context','graph_context','graph_text','merge_context']),('Б','Генерація й перевірка відповіді','engine.py',['ask']),('В','Валідація та REST API','app.py',['Ask','Answer','create_app'])]
for letter,title,filename,names in modules:
 source=(ROOT/filename).read_text('utf-8-sig');tree=ast.parse(source);blocks=[]
 for node in ast.walk(tree):
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and node.name in names:
   blocks.append('\n'.join(source.splitlines()[node.lineno-1:node.end_lineno]))
 # 66 characters fit Consolas 12 within the A4 text area; visual wrapping only.
 lines=[]
 for block in blocks:
  for line in block.splitlines():
   lines.extend(textwrap.wrap(line,width=66,subsequent_indent='    ',replace_whitespace=False,drop_whitespace=False) or [''])
  lines.append('')
 chunk_size=(len(lines)+(len(lines)+38)//39-1)//((len(lines)+38)//39)
 for offset in range(0,len(lines),chunk_size):
  label=f'Додаток {letter} — {title}' if offset==0 else f'Додаток {letter} — продовження'
  page(h(label),p(filename+' — лістинг програми; переноси довгих рядків лише для відображення.'),code('\n'.join(lines[offset:offset+chunk_size])))

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
dpara('про виконання лабораторної роботи №12',align=center,space_before=8)
dpara('з курсу «Вибрані розділи науки про дані»',align=center,space_before=8)
dpara('«Інтегрована система: RAG + граф знань + API»',align=center,space_before=15)
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

doc.core_properties.author='Шевчук Максим Вікторович'; doc.core_properties.title='ЛР12 Інтегрована система RAG + граф знань + API'
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
    text('про виконання лабораторної роботи №12',260)
    text('з курсу «Вибрані розділи науки про дані»',288)
    text('«Інтегрована система:',330)
    text('RAG + граф знань + API»',352)
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
