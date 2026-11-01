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
