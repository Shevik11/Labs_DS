from pathlib import Path
from xml.sax.saxutils import escape
import ast,json,textwrap
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER,TA_JUSTIFY,TA_LEFT,TA_RIGHT
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate,Paragraph,Table,TableStyle,Image,
                                PageBreak,Spacer,Preformatted,KeepTogether)
R=Path(__file__).resolve().parent
STEM='ЛР14_Шевчук_ФЕІм-13с'
for name,font in [('TNR','times.ttf'),('TNRB','timesbd.ttf'),('CONS','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/font)))
pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNRB',italic='TNR',boldItalic='TNRB')
body=ParagraphStyle('body',fontName='TNR',fontSize=14,leading=21,alignment=TA_JUSTIFY,
                    firstLineIndent=12.5*mm,spaceAfter=6)
heading=ParagraphStyle('heading',fontName='TNRB',fontSize=14,leading=18,
                       alignment=TA_CENTER,spaceBefore=5,spaceAfter=12,keepWithNext=True)
cell=ParagraphStyle('cell',fontName='TNR',fontSize=14,leading=16)
caption=ParagraphStyle('caption',fontName='TNR',fontSize=12,leading=14,
                       alignment=TA_CENTER,spaceAfter=8)
code_style=ParagraphStyle('code',fontName='CONS',fontSize=12,leading=14.2,
                          backColor=colors.HexColor('#F2F2F2'),borderPadding=5,
                          borderWidth=.5,borderColor=colors.HexColor('#D9D9D9'))
styles=dict(body=body,heading=heading,cell=cell,caption=caption,code=code_style)
story=[]

def read(name): return json.loads((R/name).read_text('utf-8'))
def para(text,style=body): return Paragraph(escape(str(text)).replace('\n','<br/>'),style)
def p(text): story.append(para(text))
def h(text): story.append(para(text,heading))
def page(title):
    story.append(PageBreak()); h(title)
def table(title,headers,rows,widths):
    story.append(para(title,caption))
    cells=[[para(v,cell) for v in headers]]+[[para(v,cell) for v in row] for row in rows]
    t=Table(cells,colWidths=[w*mm*176/180 for w in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.HexColor('#D9D9D9')),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F2F2F2')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),5),
        ('RIGHTPADDING',(0,0),(-1,-1),5)]))
    story.extend([t,Spacer(1,8)])
def figure(name,number,text):
    from PIL import Image as PILImage
    path=R/'figures'/name
    with PILImage.open(path) as im: width,height=im.size
    w=176*mm
    story.append(KeepTogether([Image(str(path),width=w,height=w*height/width),
        para(f'Рис. {number} - {text}',caption)]))
def listing(text):
    lines=[]
    # The appendix is a readable listing, the runnable originals are in ZIP.
    for line in text.expandtabs(4).splitlines():
        lines.extend(textwrap.wrap(line,width=74,replace_whitespace=False,
            drop_whitespace=False,break_long_words=True,break_on_hyphens=False) or [''])
    block=Table([[Preformatted('\n'.join(lines),code_style)]],
                colWidths=[176*mm],splitByRow=1,splitInRow=1,hAlign='LEFT')
    block.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F2F2F2')),
        ('BOX',(0,0),(-1,-1),.5,colors.HexColor('#D9D9D9')),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.extend([block,Spacer(1,8)])

load=read('results/load_summary.json'); drift=read('results/drift.json')
false=read('results/false_alarms.json'); runtime=read('results/runtime.json')
manifest=read('data/reference_manifest.json'); verified=read('results/metrics_verification.json')
containers=read('results/container_evidence.json'); fault=read('results/fault_injection.json')

center=ParagraphStyle('center',parent=body,alignment=TA_CENTER,firstLineIndent=0)
small=ParagraphStyle('small',parent=center,fontSize=12,leading=16)
right=ParagraphStyle('right',parent=body,alignment=TA_RIGHT,firstLineIndent=0)
story.extend([para('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ',small),
              para('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ\nІМЕНІ ІВАНА ФРАНКА',small),
              Spacer(1,8),para('Факультет електроніки і комп’ютерних технологій',center),
              Spacer(1,85),para('Звіт',heading),
              para('про виконання лабораторної роботи №14',center),
              Spacer(1,8),para('з курсу «Вибрані розділи науки про дані»',center),
              Spacer(1,12),para('«Розгортання та моніторинг дрейфу»',center),
              Spacer(1,75),para('Виконав:',ParagraphStyle('rb',parent=right,fontName='TNRB')),
              para('студент групи ФЕІм-13с',right),para('Шевчук Максим Вікторович',right),
              Spacer(1,12),para('Перевірив:',ParagraphStyle('rb2',parent=right,fontName='TNRB')),
              para('Парубочий В. О.',right),Spacer(1,75),para('Львів 2026',center)])

page('Мета та початкові матеріали')
p('Мета роботи - підготувати систему ЛР12 до контейнерного запуску, додати експлуатаційні метрики, перевірити виявлення дрейфу та описати реагування й безпечне розгортання.')
p('Використано наявну Energy GraphRAG: FastAPI, Neo4j, FAISS, multilingual MiniLM і локальну FLAN-T5-small. Новий запуск виконано в Docker на диску D. Система доступна через локальний порт 8144; зовнішній LLM API не потрібен.')
table('Таблиця 1 - Походження матеріалів',['Джерело','Повторно використано','Нове в ЛР14'],[
 ['ЛР12','API, Engine, імпортер, індекс, вебформа','Docker API, метрики, розширені журнали'],
 ['ЛР11','Ваги моделей і тестові питання','50 HTTP-запитів до контейнера'],
 ['ЛР8–9, ЛР1','Граф, вимірювання, прогнози','Reference та модельовані зсуви']], [28,76,76])
p('П’ять результатів: контейнеризація; журнали й метрики; PSI/KS та графіки; тривоги й контрольні сценарії; runbook, план розгортання та контракт даних. Успадковані матеріали не подано як нові вимірювання.')
p(f"Середовище: Docker Engine {containers['engine']}, Linux/WSL2, Python {runtime['python']}, CPU, seed=42. Основні версії: NumPy 1.26.4, SciPy 1.15.3, FastAPI 0.115.6, PyTorch 2.6.0+cpu. Повний pip freeze збережено в requirements-lock.txt.")

page('1 Контейнеризація системи')
p('Compose містить три сервіси: neo4j, одноразовий init та api. Neo4j зберігає граф у власному іменованому томі. Init чекає healthy-бази й виконує MERGE; API запускається після успішного завершення init. Це усуває ручний імпорт після docker compose up.')
p('Базовий образ API - python:3.11-slim. Застосунок працює від UID/GID 10001, EXPOSE 8144, CMD запускає один uvicorn worker. Для LLM використано CPU-версію PyTorch. Dockerfile не копіює .env, моделі, журнали чи звіти.')
p('Пароль випадково створює setup_env.py; він зберігається у локальному .env, виключеному з образу та ZIP. Neo4j не публікує порти на хості. Ваги монтуються read-only з D:/LNU/DS/11/models; дані та результати роботи знаходяться в D:/LNU/DS/14.')
listing('python setup_env.py --models-dir D:/LNU/DS/11/models\ndocker compose -p lnu-ds14 up -d --build\ndocker compose -p lnu-ds14 ps\ncurl.exe http://127.0.0.1:8144/health')
p('Підготовка .env і ваг виконується один раз. Після цього система стартує однією командою Compose. Healthcheck API виконує /health, який також перевіряє Neo4j; health не є повним тестом якості генерації.')
p('Фактичний запуск підтвердив healthy для API та Neo4j. Імпортовано 43 746 вузлів і 199 287 зв’язків; FAISS містить 38 фрагментів. Image IDs, версія Engine та контрольні суми джерел збережені в results/container_evidence.json.')

page('1 Визначення образу API')
listing((R/'Dockerfile').read_text('utf-8'))
p('Прямі залежності зафіксовані у requirements.txt; фактичні транзитивні версії - у requirements-lock.txt. У маніфесті зафіксовано revisions моделей та версію промпту. Тег образу придатний для локальної демонстрації; для виробничого розгортання план вимагає незмінний digest.')

page('2 Журнали та експлуатаційні метрики')
p('Для кожного прикладного HTTP-запиту створюється JSON-запис: UTC-час, UUID запиту, шаблон маршруту, статус, версії моделі та промпту, затримка, токени й API-вартість. Тексти запитань, відповідей та секрети до журналу не потрапляють.')
p('Ендпоінт /metrics повертає Prometheus-лічильники запитів, помилок, input/output токенів і зовнішньої API-вартості, а також гістограму часу. /health і /metrics виключені з бізнес-лічильників, тому опитування стану не змінює статистику навантаження.')
table('Таблиця 2 - Фактичний прогін 50 запитів',['Показник','Значення'],[
 ['HTTP 200 / навмисні HTTP 422',f"{load['successful']} / {load['intentional_validation_errors']}"],
 ['Неочікувані відповіді',str(load['unexpected'])],
 ['Токени input / output',f"{load['input_tokens']} / {load['output_tokens']}"],
 ['Середній час усіх запитів',f"{load['mean_seconds']:.3f} с"],
 ['p95 усіх / успішних',f"{load['p95_seconds']:.3f} / {load['success_p95_seconds']:.3f} с"],
 ['Перший запит і максимум',f"{load['max_seconds']:.3f} с"],
 ['Зовнішня API-вартість','$0']], [100,80])
p(f"Запити виконувалися послідовно всередині API-контейнера. Ваги вже завантажені, але перша генерація окремо не прогрівалася; її {load['first_request_seconds']:.3f} с включено в результати. p95 та максимум наведено окремо. Це не тест паралельного навантаження.")
p('Усі 50 відповідей зіставлено за request_id з JSON-журналом; прирости лічильників, гістограми та токенів збігаються. Часткові токени невдалої генерації невідомі. $0 означає лише відсутність платного LLM API, без оцінки електроенергії та обладнання.')

page('3 Еталон і методика виявлення дрейфу')
p('Моніторинг охоплює activePowerKw та voltageV вузлів Lab8Observation і forecastKwh вузлів Lab8Forecast. Це поля наявного графа ЛР12, що походять з енергетичних даних ЛР1. Розподіл RAG-запитів або концептуальний дрейф LLM цим експериментом не перевіряється.')
p('Для кожної популяції взято перші 6000 історичних записів, відсортованих за часом. Фіксована випадкова перестановка seed=42 ділить їх на 3000 reference та 3000 current pool без спільних рядків усередині ознаки. Дати й SHA-256 джерела записано в reference_manifest.json.')
periods=[]
for feature,info in manifest['features'].items():
    periods.append([feature,info['historical_start'][:10]+'\n'+info['historical_end'][:10],'3000 / 3000'])
table('Таблиця 3 - Популяції для моніторингу',['Поле','Історичні межі','Reference / pool'],periods,[65,65,50])
p('Ознаки мають різні історичні періоди й не видаються за одну спільну таблицю спостережень. Потужність і прогноз пов’язані, тому підтвердження двома ознаками не є двома незалежними статистичними доказами.')
p('PSI обчислюється як сума (a - e)·ln(a/e) за частками поточного та еталонного розподілів. Десять квантильних інтервалів визначає лише reference; хвости відкриті до ±∞. Псевдолічильник 0,5 усуває log(0), після чого частки знову нормуються.')
p('KS-тест scipy.stats.ks_2samp порівнює емпіричні розподіли. Для трьох ознак використано поріг p<0,01/3. Часова залежність і повтори значень обмежують буквальну інтерпретацію p-value як частоти помилки.')

page('3 Результати PSI та KS')
rows=[]
for key,label in [('calm','Без зсуву'),('mean_plus_1sigma','Зсув +1σ'),('units_times_100','Одиниці ×100')]:
    for feature,m in drift[key]['metrics'].items():
        pv='0*' if m['pvalue']==0 else f"{m['pvalue']:.2g}"
        rows.append([label,feature,f"{m['psi']:.3f}",f"{m['ks']:.3f}",pv])
table('Таблиця 4 - Порівняння за 3000 значень у кожній вибірці',
      ['Сценарій','Поле','PSI','KS D','p-value'],rows,[37,55,23,23,42])
p('У сценарії +1σ до current додається стандартне відхилення reference відповідної ознаки. В експерименті без зсуву PSI нижче 0,1 для всіх трьох полів. Навмисний зсув переводить усі поля вище 0,25; множення на 100 дає значно сильнішу відмінність.')
p('Позначка 0* означає числовий нуль, повернутий SciPy для надзвичайно малого p-value; це не твердження про математично нульову ймовірність. Сирі значення збережено у results/drift.json.')
p('Пороги PSI 0,1/0,25 обрано як початкові рівні warning/critical із завдання. Вони перевірені на спокійних вікнах, але не є універсальним стандартом. Тривога дрейфу вимагає одночасно достатнього PSI, малого p-value та щонайменше двох ознак.')

page('3 Розподіли після навмисних змін')
p('На рис. 1 порівняно reference і current після додавання 1σ. Для потужності й прогнозу зсув прибирає масу біля початкового мінімуму, що пояснює великі значення PSI.')
figure('mean_plus_1sigma.png',1,'Змодельований зсув середнього на 1σ')
p('На рис. 2 усі поточні значення помножено на 100. Розподіли майже не перекриваються; контракт фізичних одиниць також порушено. Такий випадок слід виправляти в джерелі, а не компенсувати перенавчанням.')
figure('units_times_100.png',2,'Змодельований дефект одиниць ×100')

page('3 Контрольний розподіл і динаміка PSI')
p('На рис. 3 показано початкові незалежні за рядками вибірки без навмисної зміни. Подібність розподілів узгоджується з малим PSI та відсутністю тривоги.')
figure('calm.png',3,'Історичний контрольний сценарій без зсуву')
p('На рис. 4 наведено 10 змодельованих тижневих вікон по 1000 значень на ознаку. Послідовність зсувів у σ: 0; 0; 0,1; 0,2; 0,35; 0,5; 0,75; 1; 1; 0. Це демонстрація розвитку й зникнення зсуву, а не 10 тижнів реальної експлуатації.')
figure('psi_weeks.png',4,'PSI у десяти змодельованих тижнях')

page('4 Тривоги та контрольні інциденти')
p('AlertManager створює warning або critical і зберігає час останньої тривоги кожного типу. Повтор протягом 900 с пригнічується; warning→critical проходить негайно. Дефект контракту й відмова LLM не чекають підтвердження двома PSI.')
table('Таблиця 5 - Три змодельовані інциденти',['Сценарій','Реакція','Підтвердження'],[
 ['Дрейф +1σ','data_drift, critical','PSI/KS у трьох полях'],
 ['Дефект ×100','data_defect, critical','Порушення діапазонів контракту'],
 ['Відмова LLM','llm_failure, critical','HTTP 503 при ін’єкції відмови']], [43,61,76])
p('Відмова LLM перевірена в окремому процесі: справжні модель і граф завантажено, але метод llm.generate навмисно замінено функцією, що піднімає виняток. API повернуло HTTP 503, а AlertManager - critical. Це контрольована ін’єкція, не спонтанний збій; робочий API не перемикався в режим відмови.')
p('Для дрейфу тривога в момент 0 пройшла, повтор через 60 с пригнічено, після 901 с тривогу дозволено. Тести окремо перевірили warning, ескалацію до critical та незалежні типи інцидентів. У модельованій динаміці третій тиждень має warning, четвертий - critical.')
p(f"На {false['n_windows']} спокійних bootstrap-вікнах по 1000 значень на поле отримано {false['alerts']} тривог, тобто {100*false['rate']:.1f}%. Вікна повторно використовують held-out pool і не є незалежними календарними тижнями. Нуль у цій перевірці не доводить нульову частоту хибних тривог у майбутньому.")
p('Зменшення хибних тривог: сезонні еталони, достатній розмір пакета, перевірка двох послідовних вікон, поріг ефекту разом із p-value та окрема валідація одиниць. Вісім автоматичних тестів пройшли; залежності перевірено pip check.')

page('5 Runbook та відповідальність')
p('У навчальній системі ролі оператора, розробника й відповідального за дані виконує Шевчук Максим. Запропонований runbook задає час початку реакції, а не обіцяний час повного відновлення.')
table('Таблиця 6 - Перші дії при інциденті',['Тривога','Дія та відповідальний','Реакція'],[
 ['Warning дрейфу','Оператор: перевірити період, сезонність, походження; оцінити наступне вікно','1 година'],
 ['Critical дрейфу','Дані / розробник: зупинити просування релізу; перевірити джерело; за зв’язку з релізом - відкат','15 хв'],
 ['Дефект контракту','Дані: карантин пакета, останній перевірений граф; виправити одиниці в джерелі','5 хв'],
 ['LLM недоступна','Розробник: перевірити журнал, ресурси, завантаження ваг; відновити попередній образ','5 хв']], [42,108,30])
p('Спочатку слід класифікувати інцидент: дефект схеми чи одиниць, справжня зміна розподілу або недоступність сервісу. Великий PSI сам по собі не доводить погіршення точності моделі.')
p('Перенавчання можливе лише після перевірки коректності джерела, наявності істинних міток та нового offline-оцінювання. Оновлення reference має окрему версію, період і hash; воно не повинно приховувати інцидент. Закриття інциденту, причина й час відновлення фіксуються оператором.')

page('5 План розгортання та контракт даних')
p('Обрано blue-green: green завчасно прогрівається з окремим томом графа; blue зберігається для швидкого повернення. Для невеликої CPU-системи canary має мало запитів для статистики, а shadow подвоює обчислення. У лабораторній запущено одну версію; blue-green тут описаний план, без реалізованого reverse proxy.')
p('Перед перемиканням перевіряються health, API-контракт, точність цитат, тести, 50 запитів і контракт даних. Критерії успіху: відсутність неочікуваних 5xx і дефектів цитат; p95 успішних відповідей не більше 1,2×baseline; відсутність нової critical-тривоги.')
p(f"Baseline p95 успішних відповідей становить {load['success_p95_seconds']:.3f} с. Порівняння допустиме лише за того самого набору запитів, CPU та рівня прогріву. Перший холодний виклик включено до поточного baseline.")
p('Відкат: три невдалі healthcheck поспіль, дефект цитування або контракту, 5xx>5% за 5 хв при ≥20 запитах чи p95>1,5×baseline у двох вікнах. Оператор повертає трафік на blue та зберігає журнал green. Це запропоновані початкові SLO, не production-гарантії.')
p('Data contract 1.0 задає унікальний id, ISO localdatetime без вигаданого UTC offset, скінченні числові значення та одиниці: activePowerKw у kW, voltageV у V, forecastKwh у kWh. Навчальні діапазони - 0..20, 180..270 і 0..20 відповідно; вони не є універсальними нормами електромережі.')
p('Для дрейфу потрібні ≥1000 значень на поле; пропуски не замінюються нулями. Новий пакет має version, period_start/end, units, record_count і SHA-256. Порушений пакет відхиляється, останній перевірений граф зберігається. Докладні дії й запропонований SLA записано в RUNBOOK.md, DEPLOYMENT.md та DATA_CONTRACT.md.')

page('Висновки та підготовка до захисту')
p('Систему ЛР12 запущено в Docker із власним томом Neo4j, автоматичним імпортом та непривілейованим API. За 50 HTTP-запитів отримано 45 успішних відповідей і 5 очікуваних помилок валідації; неочікуваних відповідей не було. Метрики й токени звірено з журналами.')
p('PSI та KS виявили обидва навмисні зсуви трьох полів. Контракт відокремив ×100 як дефект одиниць; контрольована відмова генерації дала HTTP 503 і critical-тривогу. На 100 спокійних bootstrap-вікнах тривог не було. Межі експерименту - історичні дані, корельовані поля й модельовані тижні.')
p('1. Дрейф даних - зміна P(X); дрейф концепції - зміна залежності P(Y|X). Поточний дослід перевіряє перше, без доведення зміни якості за істинними мітками.')
p('2. PSI=0,3 перевищує початковий critical-поріг 0,25, але потрібні перевірка вибірки, одиниць та умов; це не відсоток втрати точності.')
p('3. Shadow обробляє копію трафіку без впливу на відповідь; canary отримує малу частину живого трафіку; blue-green перемикає між двома готовими середовищами.')
p('4. Реєстр моделей зберігає версії, походження, метрики й статуси просування та допомагає відкату. У цій роботі використано файловий маніфест; сервер MLflow не розгортався.')
p('5. Дефект одиниць змінює числовий розподіл і тому виглядає як дрейф. Data contract допомагає визначити причину до рішення про перенавчання.')

page('Джерела та використання ШІ')
p('1. Завдання ЛР14 «Розгортання та моніторинг дрейфу», курс «Вибрані розділи науки про дані», 2026–2027 н. р. Копія: sources/assignment14.pdf.')
p('2. Власні матеріали ЛР1, ЛР8–9, ЛР11 та ЛР12: енергетичні дані, граф знань, корпус, ваги й код API. SHA-256 повторно використаних файлів: data/provenance.json.')
p('3. Docker. Control startup and shutdown order in Compose. https://docs.docker.com/compose/how-tos/startup-order/ .')
p('4. SciPy. scipy.stats.ks_2samp. https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ks_2samp.html .')
p('5. Prometheus Python client. Histogram. https://prometheus.github.io/client_python/instrumenting/histogram/ .')
p('6. Hebrail G., Berard A. Individual Household Electric Power Consumption. UCI Machine Learning Repository. DOI: 10.24432/C58K54. CC BY 4.0. Початковий набір описує одне домогосподарство у Франції, не енергосистему України.')
p('Для аналізу завдання, написання коду, документації та оформлення використано OpenAI Codex. Користувач доручив переглянути попередні роботи, підготував Docker та попросив зберігати матеріали на D у папці з номером лабораторної. Повні фактичні формулювання й призначення ШІ наведені в AI_DECLARATION.md.')
p('Перевірка допомоги ШІ: реальні Docker-запуски, 50 HTTP-запитів, 8 тестів, pip check, зіставлення метрик із журналами, PSI/KS на збережених даних, ін’єкція відмови та візуальна перевірка графіків і PDF. Контрольовані сценарії не видаються за виробничі інциденти. Автор має самостійно розуміти код перед захистом.')

for letter,name,title in [('А','drift.py','PSI та правила тривог'),
                          ('Б','telemetry.py','Журнали та метрики API'),
                          ('В','monitor.py','Відтворюваний експеримент дрейфу'),
                          ('Г','load_test.py','Прогін HTTP-запитів')]:
    page(f'Додаток {letter} {title}')
    p('Лістинг програми '+name+'. Оригінальний виконуваний файл включено до ZIP. Успадкований Engine ЛР12 повторно не друкується; тести та службові скрипти не включено до лістингу звіту.')
    listing((R/name).read_text('utf-8'))

def page_number(canvas,doc):
    if doc.page>1:
        canvas.setFont('TNR',14);canvas.setFillColor(colors.black)
        canvas.drawRightString(200*mm,286*mm,str(doc.page))

doc=SimpleDocTemplate(str(R/(STEM+'.pdf')),pagesize=A4,
    leftMargin=20*mm,rightMargin=10*mm,topMargin=20*mm,bottomMargin=20*mm,
    title='ЛР14 Розгортання та моніторинг дрейфу',author='Шевчук Максим Вікторович')
doc.build(story,onFirstPage=page_number,onLaterPages=page_number)
print('Built',STEM+'.pdf')
