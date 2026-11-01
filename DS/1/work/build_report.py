from pathlib import Path
import json
from docx import Document
from docx.shared import Inches, Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(r"D:\LNU\DS\1")
OUT = ROOT / "Звіт_Лабораторна_1_Енергетика_Візуалізація.docx"
RESULTS = ROOT / "results"
M = json.loads((RESULTS / "metrics.json").read_text(encoding="utf-8"))
CODE = (ROOT / "main.py").read_text(encoding="utf-8")
if CODE.startswith('"""'):
    CODE = CODE.split('"""', 2)[2].lstrip("\r\n")

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin, sec.right_margin = Cm(2), Cm(1)
sec.top_margin = sec.bottom_margin = Cm(2)
sec.header_distance, sec.footer_distance = Cm(1), Cm(1)
sec.different_first_page_header_footer = True
normal = doc.styles["Normal"]
normal.font.name = "Times New Roman"
normal.font.size = Pt(14)
normal.font.color.rgb = RGBColor(0, 0, 0)
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
normal.paragraph_format.line_spacing = 1.5
normal.paragraph_format.first_line_indent = Cm(1.25)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.space_after = Pt(0)
for sn in ("Title", "Heading 1", "Heading 2", "Heading 3"):
    st = doc.styles[sn]
    st.font.name = "Times New Roman"
    st.font.color.rgb = RGBColor(0, 0, 0)
    st._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    st.font.size = Pt(14)
    st.font.bold = True
    st.paragraph_format.keep_with_next = True
    st.paragraph_format.space_before = Pt(8 if sn != "Title" else 0)
    st.paragraph_format.space_after = Pt(4)
doc.styles["Heading 1"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.styles["Heading 1"].paragraph_format.first_line_indent = Cm(0)
doc.styles["Heading 2"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
doc.styles["Heading 2"].paragraph_format.first_line_indent = Cm(0)

def set_run(run, size=14, bold=None, font="Times New Roman"):
    run.font.name = font
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        run.bold = bold
    return run

def p(text="", bold=False, align=None, size=14, font="Times New Roman", first=None, before=0, after=0, line=1.5):
    para = doc.add_paragraph()
    if text:
        set_run(para.add_run(text), size=size, bold=bold, font=font)
    if align is not None: para.alignment = align
    if first is not None: para.paragraph_format.first_line_indent = Cm(first)
    para.paragraph_format.space_before = Pt(before)
    para.paragraph_format.space_after = Pt(after)
    para.paragraph_format.line_spacing = line
    return para

def heading(text, level=1):
    para = doc.add_paragraph(style=f"Heading {level}")
    para.paragraph_format.keep_with_next = True
    set_run(para.add_run(text), size=14, bold=True)
    return para

def set_cell_border(cell, **kwargs):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders"); tcPr.append(borders)
    for edge, attrs in kwargs.items():
        element = borders.find(qn("w:" + edge))
        if element is None:
            element = OxmlElement("w:" + edge); borders.append(element)
        for key, value in attrs.items(): element.set(qn("w:" + key), str(value))

def table(headers, rows, widths=None, font_size=12):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    if widths:
        for col, width in zip(t.columns, widths): col.width = Cm(width)
    for i, val in enumerate(headers):
        cell=t.rows[0].cells[i]; cell.text=""
        shd=OxmlElement("w:shd"); shd.set(qn("w:fill"),"D9E2F3"); cell._tc.get_or_add_tcPr().append(shd)
        set_run(cell.paragraphs[0].add_run(val), size=font_size, bold=True)
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for row in rows:
        cells=t.add_row().cells
        for i,val in enumerate(row):
            cells[i].text=""; cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_run(cells[i].paragraphs[0].add_run(str(val)), size=font_size)
    borders={edge:{"val":"single","sz":"4","color":"D9D9D9"} for edge in ("top","left","bottom","right","insideH","insideV")}
    for row in t.rows:
        for cell in row.cells:
            set_cell_border(cell,**borders)
            for para in cell.paragraphs:
                para.paragraph_format.first_line_indent=Cm(0); para.paragraph_format.line_spacing=1.1
                para.paragraph_format.space_after=Pt(2); para.paragraph_format.space_before=Pt(2)
    spacer=doc.add_paragraph(); spacer.paragraph_format.space_after=Pt(3)
    return t

def figure(filename, caption, width=6.4):
    para=doc.add_paragraph(); para.alignment=WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.first_line_indent=Cm(0); para.paragraph_format.space_before=Pt(4)
    para.paragraph_format.space_after=Pt(0); para.paragraph_format.keep_with_next=True
    para.add_run().add_picture(str(RESULTS/"plots"/filename), width=Inches(width))
    cap=p(caption,align=WD_ALIGN_PARAGRAPH.CENTER,size=12,first=0,after=6,line=1.0)

def add_page_field(para):
    para.alignment=WD_ALIGN_PARAGRAPH.RIGHT; para.paragraph_format.first_line_indent=Cm(0)
    run=para.add_run(); set_run(run,size=12)
    begin=OxmlElement("w:fldChar"); begin.set(qn("w:fldCharType"),"begin")
    instr=OxmlElement("w:instrText"); instr.set(qn("xml:space"),"preserve"); instr.text=" PAGE "
    separate=OxmlElement("w:fldChar"); separate.set(qn("w:fldCharType"),"separate")
    txt=OxmlElement("w:t"); txt.text="2"
    end=OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"),"end")
    run._r.extend([begin,instr,separate,txt,end])

add_page_field(sec.header.paragraphs[0])
p("МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ",align=WD_ALIGN_PARAGRAPH.CENTER,size=12,first=0,line=1.0,after=3)
p("ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА",align=WD_ALIGN_PARAGRAPH.CENTER,size=12,first=0,line=1.0,after=3)
p("Факультет електроніки та комп’ютерних технологій",align=WD_ALIGN_PARAGRAPH.CENTER,first=0)
for _ in range(5):
    s=doc.add_paragraph(); s.paragraph_format.space_after=Pt(0); s.paragraph_format.line_spacing=1.0
p("Звіт",bold=True,align=WD_ALIGN_PARAGRAPH.CENTER,first=0,before=32,after=4)
p("про виконання лабораторної роботи №1",align=WD_ALIGN_PARAGRAPH.CENTER,first=0,after=3)
p("з курсу «Методи видобування даних»",align=WD_ALIGN_PARAGRAPH.CENTER,first=0,after=4)
p("«Візуалізація електроспоживання засобами класифікації, регресії та кластеризації»",align=WD_ALIGN_PARAGRAPH.CENTER,first=0)
for _ in range(5):
    s=doc.add_paragraph(); s.paragraph_format.space_after=Pt(0); s.paragraph_format.line_spacing=1.0
p("Виконав:",bold=True,align=WD_ALIGN_PARAGRAPH.RIGHT,first=0,before=15)
p("студент групи ФЕІм-13с",align=WD_ALIGN_PARAGRAPH.RIGHT,first=0)
p("Шевчук Максим Вікторович",align=WD_ALIGN_PARAGRAPH.RIGHT,first=0)
p("Перевірив:",bold=True,align=WD_ALIGN_PARAGRAPH.RIGHT,first=0,before=8)
p("",align=WD_ALIGN_PARAGRAPH.RIGHT,first=0)
for _ in range(4):
    s=doc.add_paragraph(); s.paragraph_format.space_after=Pt(0); s.paragraph_format.line_spacing=1.0
p("Львів 2026",align=WD_ALIGN_PARAGRAPH.CENTER,first=0,before=20)
doc.add_page_break()

heading("Тема та мета роботи",1)
p("Тема роботи — аналіз і візуалізація електроспоживання на реальних часових даних із застосуванням класифікації, регресії та кластеризації. Мета — пройти основні етапи KDD: отримати відкриті дані, підготувати їх, побудувати моделі, оцінити якість і пояснити результат за допомогою графіків.")
heading("Завдання",1)
for text in ["Завантажити відкритий набір електроспоживання та підготувати часові ознаки.","Навчити класифікатор для виявлення годин із високим споживанням та оцінити його метриками.","Побудувати регресійну модель прогнозу енергії наступної години й порівняти з простим прогнозом.","Згрупувати добові профілі методом K-means, обрати кількість кластерів і візуалізувати результат.","Пояснити графіки, обмеження аналізу та сформулювати висновки."]:
    q=p("• "+text,first=0.65); q.paragraph_format.left_indent=Cm(0.5)

heading("Хід роботи та результати",1)
heading("1. Набір даних і постановка задачі",2)
p("Для аналізу використано відкритий набір Individual Household Electric Power Consumption з репозитарію UCI [1]. Він містить 2 075 259 хвилинних записів одного домогосподарства у Франції за період від грудня 2006 до листопада 2010 року. Набір охоплює активну й реактивну потужність, напругу, силу струму та три показники підлічильників. Це приклад побутового енергоспоживання, а не дані всієї електромережі чи України.")
p("Індустрію задано як енергетику, домен — програмний аналітичний модуль, а задачу — візуалізацію. Щоб виконати вимоги методички, окрім графіків проведено три види аналізу: класифікацію, регресію та кластеризацію.")
table(["Задача","Реалізація"],[("Класифікація","Logistic Regression: чи перевищить споживання наступної години навчальний 75-й процентиль."),("Регресія","Random Forest: прогноз енергії наступної години, кВт·год."),("Кластеризація","K-means групує повні доби за 24-годинними профілями."),("Візуалізація","Часовий ряд, теплова карта, матриця помилок, порівняння прогнозів і профілі кластерів.")],[3.4,13.6])

heading("2. Отримання та попередня обробка даних",2)
p("Архів завантажено з UCI та перевірено як ZIP. Дату й час об’єднано в часову мітку; рядки з пропусками у вимірюваннях вилучено. У початкових даних було 25 979 рядків із принаймні одним пропуском. Точних повторів вимірювання не виявлено. Від’ємних показників і нульової або від’ємної напруги також не знайдено.")
p("Хвилинні дані агреговано до годинних. Використано лише години з усіма 60 вимірюваннями; 504 неповні години не включалися в агрегований файл. Після очищення залишилося 2 049 280 хвилинних вимірювань і 34 085 повних годин. Годинну енергію обчислено як суму хвилинних середніх значень активної потужності, поділену на 60: для потужності в кВт результат має одиницю кВт·год.")
p("Для навчання сформовано попередні значення потужності за 1, 2, 24 і 168 годин, середнє за 24 години та календарні ознаки. Ціль регресії — енергія наступної години. Дані поділено в часовому порядку: 22 233 навчальні та 9 530 тестових рядків. Параметри стандартизації й поріг високого навантаження визначено лише за навчальною частиною.")
figure("01_daily_consumption.png","Рис. 1 — Добове електроспоживання у повні дні")
p("На рис. 1 показано суму споживання за кожну повну добу. Значення змінюються протягом усього періоду; на початку є окремі піки близько 80 кВт·год/добу, а більшість пізніших значень лежить приблизно в межах 15–40 кВт·год/добу. Видно періоди зростання й спаду, однак графік сам по собі не встановлює їхню причину. Розриви лінії відповідають дням без 24 повних годин вимірювань.")
figure("02_weekly_heatmap.png","Рис. 2 — Середня погодинна енергія за днями тижня")
p("Рис. 2 агрегує значення за днем тижня та годиною доби. Темніші ділянки відповідають більшому середньому споживанню. Помітне нічне зниження та ранкове й вечірнє зростання; профілі вихідних дещо відрізняються від будніх. Це середні значення майже за чотири роки, а не прогноз для окремого дня.")

heading("3. Класифікація високого навантаження",2)
p("Мітку «високе споживання» визначено як енергію наступної години, що перевищує 75-й процентиль навчальних цілей: 1,5613 кВт·год. Logistic Regression прогнозує клас 0 (звичайне) або 1 (високе). Оцінювання виконано на пізнішому часовому відрізку, який не використовувався для навчання.")
table(["Метрика","Значення","Пояснення"],[("Accuracy","0,8241","Частка правильних прогнозів серед усіх годин."),("Precision, високий клас","0,7366","Серед годин, позначених високими, 73,7% справді високі."),("Recall, високий клас","0,4777","Знайдено близько 47,8% усіх фактично високих годин."),("F1, високий клас","0,5795","Спільна оцінка precision та recall."),("Accuracy базової моделі","0,7463","Модель завжди передбачає найчастіший навчальний клас.")],[4.2,2.5,10.3])
p("Accuracy класифікатора перевищує базову на 7,8 відсоткового пункта. Водночас recall високого навантаження — 47,8%: понад половину годин цього класу модель пропускає. Класифікатор помірно знаходить піки, але його не варто використовувати як самостійну систему попередження без налаштування порогу й перевірки на нових даних.")
figure("03_confusion_matrix.png","Рис. 3 — Матриця помилок класифікатора")
p("Матриця на рис. 3 деталізує помилки на 9 530 тестових годинах: 6 699 звичайних годин правильно віднесено до звичайних, 1 155 високих знайдено, 1 263 високих пропущено, а 413 звичайних помилково оголошено високими. Такий розподіл пояснює невисокий recall високого класу.")

heading("4. Регресія споживання наступної години",2)
p("Random Forest Regressor прогнозує числову енергію наступної години в кВт·год. Результат порівнюється з базовим прогнозом збереження навантаження: наступна година матиме таку саму енергію, як середня активна потужність поточної години, помножена на одну годину.")
table(["Метрика","Random Forest","Базовий прогноз"],[("MAE, кВт·год","0,3360","0,4235"),("MSE, (кВт·год)²","0,2361","0,4061"),("R²","0,6427","0,3854")],[5,5.6,6.4])
p("Random Forest має меншу середню абсолютну похибку: 0,336 кВт·год проти 0,424 кВт·год. Квадратична помилка також нижча, а R² вищий. Отже, лаги, середнє попередніх вимірювань і календарні ознаки додають інформацію для однокрокового прогнозу. Оцінки стосуються тестового інтервалу цього набору й не гарантують такої самої якості для іншого будинку чи сучасної мережі.")
figure("04_forecast.png","Рис. 4 — Фактичне та прогнозоване споживання за перший тиждень тесту")
p("На рис. 4 синя лінія показує виміряне споживання, помаранчева — прогноз Random Forest. За звичайних рівнів лінії часто близькі; різкі піки модель згладжує й нерідко недооцінює. Розриви позначають відсутні години: вони не з’єднані штучною інтерполяцією.")
figure("05_regression_scatter.png","Рис. 5 — Фактичні та прогнозовані значення регресії",width=5.6)
p("Кожна точка на рис. 5 відповідає тестовій годині. Червона пунктирна діагональ — ідеальний прогноз, де прогноз дорівнює фактичному значенню. Точки вище лінії означають завищення, нижче — заниження. Для великих значень розкид зростає, а частина точок лежить нижче діагоналі, що вказує на недооцінювання деяких піків.")

heading("5. Кластеризація добових профілів",2)
p("Для кожної повної доби сформовано вектор із 24 погодинних значень кВт·год. Після стандартизації K-means перевірено для k від 2 до 8. Кількість кластерів обрано за найбільшим silhouette score серед перевірених значень; метод ліктя використано як додатковий графічний огляд.")
table(["Показник","Результат","Пояснення"],[("Повних діб","1 358","Враховано доби з усіма 24 годинами."),("Вибране k","2","Найвищий перевірений silhouette для двох груп."),("Silhouette","0,1858","Розділення слабке, профілі помітно перекриваються."),("Кластер 0","548 діб","У середньому вищий рівень і виразніший вечірній пік."),("Кластер 1","810 діб","У середньому нижчий рівень споживання.")],[4,3.2,9.8])
p("Метод ліктя показує поступове зниження інерції без однозначного різкого зламу. Максимум silhouette обирає k=2, однак значення 0,1858 указує на слабке розділення. Це радше два середні типи добового навантаження, ніж чітко ізольовані режими. Мітки 0 та 1 умовні й можуть помінятися місцями при повторному запуску.")
figure("06_cluster_selection.png","Рис. 6 — Інерція та silhouette для вибору числа кластерів")
p("Ліва панель рис. 6 показує спад інерції при збільшенні k, права — silhouette для кожного значення. Вертикальна риска позначає два автоматично вибрані кластери. Відсутність чіткого ліктя й невисокий silhouette радять обережно тлумачити результат.")
figure("07_daily_clusters.png","Рис. 7 — Середні добові профілі двох кластерів")
p("На рис. 7 синя крива (кластер 0) лежить вище більшу частину дня та має сильніший вечірній підйом. Помаранчева (кластер 1) показує нижчий середній рівень. Це опис середніх профілів повних діб, а не групування за сезоном чи днем тижня.")

heading("6. Обмеження та можливі покращення",2)
p("Набір описує одне домогосподарство у Франції в 2006–2010 роках, тому висновки не можна переносити на інших споживачів без нових даних. Клас високого споживання утворено статистичним порогом 75-го процентиля; він не означає аварію чи порушення нормативу. Recall високого класу низький, а кластерне розділення слабке. Регресійний тест моделює послідовні однокрокові прогнози з доступними минулими вимірюваннями, а не прогноз усього майбутнього періоду з однієї початкової точки.")
p("Подальше дослідження може перевірити інші пороги та ваги класів, порівняти моделі на кількох часових вікнах, випробувати інші регресійні алгоритми, а для кластеризації зіставити стандартизацію погодинних профілів із нормалізацією форми доби. Налаштування слід обирати на навчальних або окремих валідаційних даних.")

heading("Висновки",1)
p("У лабораторній роботі підготовлено відкриті дані електроспоживання UCI. Після очищення та відбору повних годин отримано 34 085 погодинних спостережень. Реалізовано часовий поділ, стандартизацію ознак, класифікацію, регресію й кластеризацію добових профілів.")
p("Класифікатор досяг accuracy 0,824 проти 0,746 для базового правила, але recall високого навантаження становив 0,478 — багато пікових годин пропущено. Random Forest зменшив MAE до 0,336 кВт·год проти 0,424 кВт·год у простого прогнозу незмінного навантаження; R² становив 0,643. K-means обрав дві групи з 1 358 повних діб, але silhouette 0,186 указує на слабке розмежування.")
p("Графіки показали добову й тижневу мінливість, структуру класифікаційних помилок, недооцінювання частини регресійних піків і різницю середніх профілів кластерів. Отже, програмний модуль дає змогу візуально дослідити закономірності набору, а метрики виявляють сильні й слабкі сторони моделей. Висновки мають навчальний характер і обмежені історичними даними одного домогосподарства.")
heading("Список використаних джерел",1)
p("1. Hebrail G., Berard A. Individual Household Electric Power Consumption. UCI Machine Learning Repository, 2006. DOI: 10.24432/C58K54. URL: https://archive.ics.uci.edu/dataset/235/individualhouseholdelectricpowerconsumption (дата звернення: 30.09.2026).",first=0)

doc.add_page_break()
heading("Додаток А",1)
heading("Основна програма",2)
p("Нижче подано код реалізації. Початковий модульний docstring з інструкціями запуску пропущено; алгоритми й потрібні коментарі збережено.",first=0)
p("Лістинг програми main.py",bold=True,first=0,before=4,after=2)
listing=CODE.splitlines()
for idx,line in enumerate(listing):
    para=doc.add_paragraph(); para.paragraph_format.first_line_indent=Cm(0)
    para.paragraph_format.left_indent=Cm(0.25); para.paragraph_format.right_indent=Cm(0.15)
    para.paragraph_format.space_before=Pt(0); para.paragraph_format.space_after=Pt(0)
    para.paragraph_format.line_spacing=1.0; para.paragraph_format.keep_together=True
    set_run(para.add_run(line if line else " "),size=12,font="Consolas")
    shd=OxmlElement("w:shd"); shd.set(qn("w:fill"),"F2F2F2"); para._p.get_or_add_pPr().append(shd)
    borders=OxmlElement("w:pBdr")
    for edge in ("left","right"):
        el=OxmlElement("w:"+edge); el.set(qn("w:val"),"single"); el.set(qn("w:sz"),"4"); el.set(qn("w:space"),"3"); el.set(qn("w:color"),"D9D9D9"); borders.append(el)
    if idx==0 or idx==len(listing)-1:
        edge="top" if idx==0 else "bottom"
        el=OxmlElement("w:"+edge); el.set(qn("w:val"),"single"); el.set(qn("w:sz"),"4"); el.set(qn("w:space"),"3"); el.set(qn("w:color"),"D9D9D9"); borders.append(el)
    para._p.get_or_add_pPr().append(borders)

doc.core_properties.title="Звіт про виконання лабораторної роботи №1 з методів видобування даних"
doc.core_properties.subject="Електроспоживання: класифікація, регресія, кластеризація та візуалізація"
doc.core_properties.author="Шевчук Максим Вікторович"
doc.save(OUT)
print(OUT)
print("code lines",len(listing),"figures",len(list((RESULTS/"plots").glob("*.png"))))
