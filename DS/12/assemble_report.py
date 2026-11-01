from pathlib import Path
src=Path('D:/LNU/DS/11/build_report.py').read_text('utf-8')
head=src[:src.index("ROOT=Path")]
setup='''ROOT=Path(__file__).resolve().parent
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
'''
tail=src[src.index('doc=Document()'):]
tail=tail.replace('№11','№12').replace('ЛР11 Векторна база даних та RAG на матеріалах ЛР8','ЛР12 Інтегрована система RAG + граф знань + API')
tail=tail.replace('«Векторна база даних та RAG\\nна матеріалах лабораторної роботи №8»','«Інтегрована система: RAG + граф знань + API»')
tail=tail.replace("text('«Векторна база даних та RAG',330)","text('«Інтегрована система:',330)").replace("text('на матеріалах лабораторної роботи №8»',352)","text('RAG + граф знань + API»',352)")
Path('report_tail.py').write_text(tail,'utf-8')
Path('report_head.py').write_text(head+setup,'utf-8')
