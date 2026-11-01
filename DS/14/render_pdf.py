from pathlib import Path
import json
import pymupdf
from PIL import Image,ImageDraw
r=Path('D:/LNU/DS/14'); out=r/'work/render';out.mkdir(exist_ok=True)
d=pymupdf.open(r/'ЛР14_Шевчук_ФЕІм-13с.pdf')
info=[]
for i,p in enumerate(d):
    p.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(out/f'page-{i+1}.png')
    bad=[list(b[:4]) for b in p.get_text('blocks') if b[0]<30 or b[2]>584 or b[3]>805]
    info.append(dict(page=i+1,chars=len(p.get_text()),outside=bad))
for start in range(0,len(d),6):
    sheet=Image.new('RGB',(1200,1710),'#cccccc'); draw=ImageDraw.Draw(sheet)
    for j in range(start,min(start+6,len(d))):
        im=Image.open(out/f'page-{j+1}.png');im.thumbnail((580,805))
        x=(j-start)%2*600;y=(j-start)//2*570
        im.thumbnail((580,540));sheet.paste(im,(x,y+25));draw.text((x+8,y+6),f'Page {j+1}',fill='black')
    sheet.save(out/f'contact-{start//6+1}.png')
(r/'results/report_validation.json').write_text(json.dumps(info,indent=2),'utf-8')
print('Pages',len(d),'bad bounds',[(x['page'],len(x['outside'])) for x in info if x['outside']])
print('Short pages',[(x['page'],x['chars']) for x in info if x['chars']<120])
