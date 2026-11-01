from pathlib import Path
import json, math
from xml.etree.ElementTree import Element, SubElement, ElementTree
from html import escape

ROOT = Path(r'D:\LNU\DS\3')
N = [
('object','Об’єкт споживання','Домогосподарство','Енергетика',60,150,'Фізичний об’єкт, для якого аналізують споживання електроенергії.','ідентифікатор, назва, тип'),
('meter','Засіб обліку','Лічильник / підлічильник','Енергетика',440,150,'Засіб отримання вимірювань енергоспоживання об’єкта.','ідентифікатор, канал обліку'),
('measurement','Вимірювання','Значення у певний час','Дані',820,150,'Спостереження показника з часовою міткою, значенням, одиницею та ознакою якості.','час, значення, одиниця, якість'),
('indicator','Енергетичний показник','Потужність, енергія, напруга','Дані',1200,150,'Величина, яку спостерігають або обчислюють; енергію за годину отримують агрегуванням.','назва, одиниця, спосіб обчислення'),
('module','Програмний модуль','Обробка та подання даних','Програмне забезпечення',60,410,'Компонент програми, який перевіряє й перетворює дані та формує їх візуальне подання.','назва, версія, функції'),
('dataset','Набір даних','Годинні дані споживання','Дані',440,410,'Сукупність спостережень, підготовлених для аналізу.','схема, період, якість'),
('series','Часовий ряд','Послідовність спостережень','Дані',820,410,'Упорядковані за часом вимірювання одного показника одного об’єкта.','показник, крок часу, пропуски'),
('period','Часовий інтервал','Година, доба, тиждень','Дані',1200,410,'Проміжок часу, до якого належать спостереження або результати.','початок, кінець, часовий контекст'),
('user','Користувач','Аналітик / споживач','Взаємодія',60,670,'Особа, яка переглядає графіки, налаштовує відбір і використовує результати.','роль, інформаційна потреба'),
('view','Візуалізація','Графік, теплова карта','Візуалізація',440,670,'Графічне подання спостережень або аналітичного результату з підписами та одиницями.','тип, осі, легенда, джерело'),
('result','Результат аналізу','Прогноз, клас, кластер','Аналітика',820,670,'Результат застосування моделі до даних: значення прогнозу, мітка класу чи кластер.','тип, значення, час, модель'),
('model','Аналітична модель','Прогнозування / класифікація / групування','Аналітика',1200,670,'Метод із визначеними параметрами, який виконує аналітичне завдання.','алгоритм, параметри, версія'),
('decision','Рішення користувача','Перевірити режим споживання','Взаємодія',60,930,'Висновок або дія, яку користувач обирає після інтерпретації візуалізації.','опис, підстава, автор'),
('filter','Фільтр подання','Період, показник, клас','Візуалізація',440,930,'Умова відбору або групування інформації, яка показана на візуалізації.','поле, умова, значення'),
('metric','Метрика якості','Точність і похибка прогнозу','Аналітика',820,930,'Числова оцінка результату із зазначенням задачі й вибірки оцінювання.','назва, значення, одиниця, вибірка'),
('task','Аналітичне завдання','Класифікація, регресія, кластери','Аналітика',1200,930,'Постановка аналізу з визначеними входами, очікуваним результатом і критеріями оцінювання.','тип, ціль, горизонт, критерії'),
]
# Endpoint anchors: relative to the 280 x 96 concept rectangle.
E = [
('object','meter','обладнаний',(1,.5),(0,.5),0,-13),
('meter','measurement','реєструє',(1,.5),(0,.5),0,-13),
('measurement','indicator','описує',(1,.5),(0,.5),0,-13),
('module','dataset','опрацьовує',(1,.5),(0,.5),0,-13),
('dataset','series','містить',(1,.5),(0,.5),0,-13),
('series','period','охоплює',(1,.5),(0,.5),0,-13),
('series','measurement','складається з',(.5,0),(.5,1),0,0),
('user','module','використовує',(.5,0),(.5,1),0,0),
('module','view','формує',(1,1),(0,0),0,-8),
('user','view','переглядає',(1,.5),(0,.5),0,-13),
('result','view','подано у',(0,.5),(1,.5),0,-13),
('model','result','створює',(0,.5),(1,.5),0,-13),
('view','series','відображає',(1,0),(0,1),0,-8),
('model','series','аналізує',(0,0),(1,1),0,-8),
('result','series','отримано з',(.5,0),(.5,1),0,0),
('task','model','виконується моделлю',(.5,0),(.5,1),0,0),
('result','metric','оцінюється',(.5,1),(.5,0),0,0),
('filter','view','налаштовує',(.5,0),(.5,1),0,0),
('user','decision','ухвалює',(.5,1),(.5,0),0,0),
('view','decision','підтримує',(0,1),(1,0),0,-8),
]
colors={'Енергетика':'#f6edcf','Дані':'#e7eff7','Програмне забезпечення':'#e4eee7','Взаємодія':'#f2e8ee','Візуалізація':'#e4eee7','Аналітика':'#eee9f7'}
nodes=[dict(zip(['id','label','example','category','x','y','definition','attributes'],n)) for n in N]
lookup={n['id']:n for n in nodes}
relations=[{'id':f'R{i:02}','source':e[0],'predicate':e[2],'target':e[1]} for i,e in enumerate(E,1)]
model={'title':'Візуалізація енергетичних даних засобами програмного забезпечення','variant':{'industry':'Енергетика','domain':'Програмне забезпечення','problem':'Візуалізація'},'nodes':nodes,'relations':relations,'notes':['Вузли є концептами. Другий рядок у вузлі містить приклади, а не підкласи.','Стрілка читається: джерело — назва відношення — ціль.','Кратності та формальні аксіоми OWL не визначено: це концептуальна граф-модель.']}
(ROOT/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8')
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1540" height="1170" viewBox="0 0 1540 1170">','<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9" fill="#46505c"/></marker></defs>','<rect width="1540" height="1170" fill="white"/>']
def txt(x,y,s,size=20,bold=False):
    svg.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Arial" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="#000000">{escape(s)}</text>')
txt(770,45,'Візуалізація енергетичних даних засобами програмного забезпечення',29,True)
txt(770,84,'Енергетика / Програмне забезпечення / Візуалізація • Лабораторна робота №3',20)
mx=Element('mxfile',host='app.diagrams.net',version='24.7.17',type='device')
diag=SubElement(mx,'diagram',id='energy-concepts',name='Граф-модель')
gm=SubElement(diag,'mxGraphModel',dx='1540',dy='1170',grid='1',gridSize='10',page='1',pageWidth='1540',pageHeight='1170')
r=SubElement(gm,'root'); SubElement(r,'mxCell',id='0'); SubElement(r,'mxCell',id='1',parent='0')
for id_,value,y,size in [('title',model['title'],20,28),('subtitle','Енергетика / Програмне забезпечення / Візуалізація',60,20)]:
    c=SubElement(r,'mxCell',id=id_,value=value,style=f'text;html=0;align=center;fontSize={size};fontColor=#000000;',vertex='1',parent='1'); SubElement(c,'mxGeometry',x='20',y=str(y),width='1500',height='40',attrib={'as':'geometry'})
for i,e in enumerate(E,1):
    a,b,label,aa,bb,dx,dy=e; na,nb=lookup[a],lookup[b]
    x1,y1=na['x']+280*aa[0],na['y']+96*aa[1];x2,y2=nb['x']+280*bb[0],nb['y']+96*bb[1]
    svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#46505c" stroke-width="2" marker-end="url(#arrow)"/>')
    angle=math.atan2(y2-y1,x2-x1)
    bx,by=x2-14*math.cos(angle),y2-14*math.sin(angle)
    points=f'{x2},{y2} {bx+6*math.sin(angle)},{by-6*math.cos(angle)} {bx-6*math.sin(angle)},{by+6*math.cos(angle)}'
    svg.append(f'<polygon points="{points}" fill="#46505c"/>')
    lx,ly=(x1+x2)/2+dx,(y1+y2)/2+dy
    width=len(label)*8.2+12
    svg.append(f'<rect x="{lx-width/2}" y="{ly-17}" width="{width}" height="26" rx="3" fill="white"/>'); txt(lx,ly+2,label,15)
    style=f'endArrow=block;html=0;rounded=0;strokeColor=#46505c;fontColor=#000000;fontSize=18;labelBackgroundColor=#ffffff;exitX={aa[0]};exitY={aa[1]};entryX={bb[0]};entryY={bb[1]};'
    c=SubElement(r,'mxCell',id=f'R{i:02}',value=label,style=style,edge='1',parent='1',source=a,target=b); geo=SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'}); SubElement(geo,'mxPoint',x=str(dx),y=str(dy),attrib={'as':'offset'})
for n in nodes:
    x,y=n['x'],n['y'];fill=colors[n['category']]
    svg.append(f'<rect x="{x}" y="{y}" width="280" height="96" rx="12" fill="{fill}" stroke="#55616d" stroke-width="1.5"/>')
    txt(x+140,y+36,n['label'],23,True);txt(x+140,y+67,n['example'],16)
    c=SubElement(r,'mxCell',id=n['id'],value=n['label']+'\n'+n['example'],style=f'rounded=1;whiteSpace=wrap;html=0;fillColor={fill};strokeColor=#55616d;fontColor=#000000;fontSize=20;fontFamily=Arial;',vertex='1',parent='1'); SubElement(c,'mxGeometry',x=str(x),y=str(y),width='280',height='96',attrib={'as':'geometry'})
txt(770,1085,'Стрілка: поняття → відношення → поняття. Другий рядок вузла містить приклади.',19)
txt(770,1119,'16 концептів • 20 напрямлених зв’язків • Концептуальна модель для подальшої бази знань',19)
c=SubElement(r,'mxCell',id='legend',value='Стрілка: поняття → відношення → поняття. Другий рядок вузла містить приклади.\n16 концептів · 20 зв’язків · Концептуальна модель',style='text;html=0;align=center;fontSize=19;fontColor=#000000;',vertex='1',parent='1');SubElement(c,'mxGeometry',x='20',y='1060',width='1500',height='80',attrib={'as':'geometry'})
svg.append('</svg>'); (ROOT/'Граф_модель_Енергетика.svg').write_text('\n'.join(svg),encoding='utf-8')
ElementTree(mx).write(ROOT/'Граф_модель_Енергетика.drawio',encoding='utf-8',xml_declaration=True)
assert len(lookup)==16 and len(relations)==20
assert all(e['source'] in lookup and e['target'] in lookup for e in relations)
print('Created: 16 concepts, 20 relations, SVG, draw.io, JSON')


