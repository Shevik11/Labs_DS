from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
r=Path.cwd();im=Image.new('RGB',(1500,900),'white');d=ImageDraw.Draw(im)
f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',27);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23);bold=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',29)
def box(xy,title,lines):
 d.rounded_rectangle(xy,12,fill='#f1f4f6',outline='black',width=2);x,y,x2,y2=xy;d.text((x+20,y+18),title,font=bold,fill='black')
 for i,line in enumerate(lines):d.text((x+20,y+62+i*33),line,font=small,fill='black')
def arrow(a,b):
 d.line([a,b],fill='black',width=4);x,y=b;dx=x-a[0];dy=y-a[1]
 if abs(dx)>abs(dy):d.polygon([(x,y),(x-14,y-8),(x-14,y+8)],fill='black')
 else:d.polygon([(x,y),(x-8,y-14),(x+8,y-14)],fill='black')
d.text((40,25),'ЛР12: архітектура та межі довіри',font=bold,fill='black')
d.rectangle((430,100,1465,800),outline='black',width=3);d.text((450,115),'Довірений локальний сервер (127.0.0.1)',font=bold,fill='black')
box((40,260,365,470),'Браузер / клієнт',['HTML-форма','Недовірений ввід','POST /ask (JSON)'])
box((465,240,885,520),'FastAPI / оркестратор',['Pydantic: 3–500 символів','request_id, коди помилок','Дедуплікація, бюджет токенів','Без тексту запиту в логах'])
box((1010,180,1435,320),'FAISS / ЛР11',['38 фрагментів + метадані','Корпус = недовірені дані'])
box((1010,355,1435,495),'Neo4j / ЛР8–9',['43 746 вузлів, 199 287 ребер','READ, параметри, глибина ≤ 2'])
box((1010,535,1435,675),'Локальний LLM',['FLAN-T5-small / CPU','Промпт → текст + токени'])
arrow((365,345),(465,345));arrow((885,285),(1010,250));arrow((885,400),(1010,420));arrow((885,480),(1010,590))
d.text((450,710),'Секрети: лише змінні середовища сервера.',font=f,fill='black')
d.text((450,750),'Локальна БД без пароля доступна лише через loopback.',font=small,fill='black')
d.text((40,835),'Відповідь JSON: answer, sources[], graph[], status, request_id, tokens',font=f,fill='black')
im.save(r/'figures/architecture.png')
