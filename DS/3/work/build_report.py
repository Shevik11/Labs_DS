from pathlib import Path
import json
from html import escape
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START,WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_JUSTIFY,TA_CENTER,TA_LEFT

R=Path(r'D:\LNU\DS\3'); M=json.loads((R/'model.json').read_text(encoding='utf-8'))
BASENAME='Звіт_Лабораторна_3_Моделювання_Енергетика'
fonts=Path(r'C:\Windows\Fonts')
for name,file in [('TNR','times.ttf'),('TNRB','timesbd.ttf'),('TNRI','timesi.ttf')]:pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNRB',italic='TNRI',boldItalic='TNRB')
cm=28.3464567
D=Document();sec=D.sections[0]
sec.page_width,sec.page_height=Cm(21),Cm(29.7)
sec.left_margin,sec.right_margin=Cm(2),Cm(1); sec.top_margin=sec.bottom_margin=Cm(2)
sec.header_distance=Cm(1);sec.different_first_page_header_footer=True
for name in ['Normal','Title','Heading 1','Heading 2']:
    s=D.styles[name];s.font.name='Times New Roman';s.font.size=Pt(14);s.font.color.rgb=RGBColor(0,0,0)
    s.paragraph_format.space_before=Pt(0);s.paragraph_format.space_after=Pt(0)
    s.paragraph_format.line_spacing=1.5;s.paragraph_format.first_line_indent=Cm(1.25)
    if name!='Normal':s.font.bold=True;s.paragraph_format.first_line_indent=Cm(0);s.paragraph_format.keep_with_next=True
D.styles['Normal'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
D.styles['Heading 1'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
h=sec.header.paragraphs[0];h.alignment=WD_ALIGN_PARAGRAPH.RIGHT
f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');h._p.append(f)
D.core_properties.author='Шевчук Максим Вікторович';D.core_properties.title=M['title']
C=canvas.Canvas(str(R/(BASENAME+'.pdf')),pagesize=(21*cm,29.7*cm));C.setTitle(M['title']);C.setAuthor('Шевчук Максим Вікторович')
page=1;y=27.7*cm;pw=21*cm;ph=29.7*cm
style=ParagraphStyle('body',fontName='TNR',fontSize=14,leading=21,alignment=TA_JUSTIFY,firstLineIndent=1.25*cm)
def pdfp(text,bold=False,center=False,size=14,after=6):
    global y
    st=ParagraphStyle('p',parent=style,fontSize=size,leading=size*1.5,alignment=TA_CENTER if center else TA_JUSTIFY,firstLineIndent=0 if center or bold else 1.25*cm)
    p=Paragraph(('<b>'+escape(text)+'</b>') if bold else escape(text),st)
    w,hh=p.wrap(pw-3*cm,1000)
    if y-hh<2*cm:raise ValueError(f'PDF page {page} overflow: {text[:50]}')
    p.drawOn(C,2*cm,y-hh);y-=hh+after

def para(text,bold=False,center=False,size=14,after=6):
    p=D.add_paragraph(style='Heading 1' if bold else 'Normal');r=p.add_run(text);r.font.size=Pt(size)
    if center:p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0)
    p.paragraph_format.space_after=Pt(after)
    pdfp(text,bold,center,size,after)

def nextpage(land=False):
    global page,y,pw,ph
    C.showPage();page+=1;pw,ph=((29.7*cm,21*cm) if land else (21*cm,29.7*cm));C.setPageSize((pw,ph))
    C.setFont('TNR',12);C.drawRightString(pw-cm,ph-cm,str(page));y=ph-2*cm
    if land or D.sections[-1].orientation==WD_ORIENT.LANDSCAPE:
        s=D.add_section(WD_SECTION_START.NEW_PAGE);s.orientation=WD_ORIENT.LANDSCAPE if land else WD_ORIENT.PORTRAIT;s.page_width=Cm(29.7 if land else 21);s.page_height=Cm(21 if land else 29.7);s.different_first_page_header_footer=False
    else:D.add_page_break()

def table(headers,rows,widths):
    global y
    t=D.add_table(rows=1,cols=len(headers));t.autofit=False
    for col,w in zip(t.columns,widths):col.width=Cm(w)
    for cells,vals in [(t.rows[0].cells,headers)]+[(t.add_row().cells,row) for row in rows]:
        for cell,text in zip(cells,vals):
            cell.text=str(text)
            for p in cell.paragraphs:p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.line_spacing=1;p.paragraph_format.space_after=Pt(4);p.paragraph_format.space_before=Pt(4)
            pr=cell._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
            for edge in ['top','bottom','left','right']:
                v=OxmlElement('w:'+edge);v.set(qn('w:val'),'single');v.set(qn('w:sz'),'4');v.set(qn('w:color'),'D9D9D9');b.append(v)
            pr.append(b)
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    for row in t.rows:
        trpr=row._tr.get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
    for cell in t.rows[0].cells:
        sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'EEEEEE');cell._tc.get_or_add_tcPr().append(sh)
        for run in cell.paragraphs[0].runs:run.bold=True
    st=ParagraphStyle('cell',fontName='TNR',fontSize=14,leading=16,alignment=TA_LEFT)
    data=[[Paragraph(('<b>'+escape(str(v))+'</b>') if i==0 else escape(str(v)),st) for v in row] for i,row in enumerate([headers]+rows)]
    tb=Table(data,colWidths=[w*cm for w in widths]);tb.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D9D9D9')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EEEEEE')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    w,hh=tb.wrap(pw-3*cm,1000)
    if y-hh<2*cm:raise ValueError(f'Table overflow page {page}, height {hh}, available {y-2*cm}')
    tb.drawOn(C,2*cm,y-hh);y-=hh+8

# Title page uses explicit spacing rather than empty paragraphs.
for txt,size,before,after in [
('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ',12,0,3),('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА',12,0,3),('Факультет електроніки і комп’ютерних технологій',14,0,0),('Звіт',14,70,10),('про виконання лабораторної роботи №3',14,0,10),('з курсу «Вибрані розділи науки про дані»',14,0,20),('«Моделювання тематичної області візуалізації енергетичних даних засобами програмного забезпечення»',14,0,60)]:
    p=D.add_paragraph(style='Title' if txt=='Звіт' else 'Normal');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.line_spacing=1.2;p.paragraph_format.space_before=Pt(before);p.paragraph_format.space_after=Pt(after);r=p.add_run(txt);r.font.size=Pt(size)
    y-=before;pdfp(txt,txt=='Звіт',True,size,after)
for txt in ['Виконав:','студент групи ФЕІм-13с','Шевчук Максим Вікторович','Перевірив:','Парубочий В. О.']:
    p=D.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.line_spacing=1.2;r=p.add_run(txt);r.bold=txt.endswith(':')
    C.setFont('TNRB' if txt.endswith(':') else 'TNR',14);C.drawRightString(20*cm,y-16,txt);y-=21
p=D.add_paragraph('Львів 2026');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.space_before=Pt(65)
C.setFont('TNR',14);C.drawCentredString(pw/2,2.2*cm,'Львів 2026')
nextpage()
para('Тема та мета роботи',True,True)
para('Тема — моделювання візуалізації енергетичних даних засобами програмного забезпечення. Мета — визначити ключові поняття, їх категорії та напрямлені взаємозв’язки й побудувати граф-модель як основу для подальшої бази знань та онтології.')
para('Завдання',True,True)
for item in [
    '1. Визначити предметну область.',
    '2. Проаналізувати наявні дані та поняття предметної області.',
    '3. Виділити основні концепти.',
    '4. Побудувати й пояснити карту взаємозв’язків.',
]:
    para(item,after=2)
para('1 Визначення предметної області',True,True)
para('Індустрія: енергетика.',after=2)
para('Домен: програмне забезпечення.',after=2)
para('Проблема: візуалізація.',after=2)
para('Об’єкт моделювання — поняття та відношення, потрібні програмі для подання даних електроспоживання і результатів їх аналізу користувачеві.')
para('Межі моделі охоплюють вимірювання, їх часову організацію, програмну обробку, аналітичні результати, графічне подання та інтерпретацію. Проєктування електромереж, тарифоутворення й автоматичне керування обладнанням до цієї моделі не входять.')
para('2 Аналіз та дослідження',True,True)
para('Для побудови граф-моделі використано раніше отримані дані про погодинне споживання електроенергії. Часові вимірювання дають змогу виділити енергетичні показники, часові ряди, програмні засоби їх обробки, способи візуалізації та потреби користувача.')
nextpage()
para('3 Ключові концепти та категорії',True,True)
para('Виділено 16 концептів. Таблиці 1–2 задають їх значення й типові атрибути. Приклади алгоритмів, файлів і графіків ілюструють концепти та не є окремими класами моделі.')
para('Таблиця 1 — Енергетичні об’єкти та дані',center=True,after=8)
sel=[M['nodes'][i] for i in [0,1,2,3,5,6,7]]
table(['Концепт','Зміст','Атрибути'],[[n['label'],n['definition'],n['attributes']] for n in sel],[4.0,9.1,4.9])
nextpage()
para('Таблиця 2 — Програмні засоби та взаємодія',center=True,after=8)
sel=[M['nodes'][i] for i in [4,8,9,10,11,12,13,14,15]]
table(['Концепт','Зміст','Атрибути'],[[n['label'],n['definition'],n['attributes']] for n in sel],[4.0,9.1,4.9])
nextpage(True)
para('4 Граф-модель тематичної області',True,True,after=2)
# Main editable deliverable is the full-size diagram; this is its report overview.
p=D.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.line_spacing=1;p.paragraph_format.keep_with_next=True
p.add_run().add_picture(str(R/'Граф_модель_Енергетика.png'),width=Cm(20.0))
iw=20*cm;ih=iw*1170/1540
C.drawImage(str(R/'Граф_модель_Енергетика.png'),(pw-iw)/2,y-ih,width=iw,height=ih);y-=ih+3
para('Рис. 1 — Граф-модель предметної області',center=True,size=12,after=0)
nextpage()
para('5 Опис взаємозв’язків',True,True)
para('Кожний зв’язок читається як «джерело — відношення — ціль». Вузли позначають поняття, стрілки — семантичні відношення; це не схема порядку виконання програми. Повнорозмірна схема збережена окремо у форматах draw.io, SVG, PNG і PDF.')
para('Таблиця 3 — Відношення між концептами',center=True,after=8)
lookup={n['id']:n['label'] for n in M['nodes']}
relation_rows=[[lookup[e['source']],e['predicate'],lookup[e['target']]] for e in M['relations']]
table(['Джерело','Відношення','Ціль'],relation_rows[:10],[6.1,5.8,6.1])
nextpage()
para('Таблиця 3 — Відношення між концептами (продовження)',center=True,after=8)
table(['Джерело','Відношення','Ціль'],relation_rows[10:],[6.1,5.8,6.1])
para('Висновок',True,True)
para('Побудовано концептуальну граф-модель візуалізації енергетичних даних у програмному забезпеченні. Вона охоплює 16 понять із категорій енергетики, даних, програмного забезпечення, аналітики, візуалізації та взаємодії й визначає 20 напрямлених зв’язків між ними. Модель описує шлях від вимірювання енергоспоживання до його опрацювання, графічного подання та рішення користувача і може слугувати основою для подальшої бази знань.')
D.save(R/(BASENAME+'.docx'));C.save();print(f'Saved DOCX and PDF; PDF pages: {page}')



