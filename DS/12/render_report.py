from pathlib import Path
import pymupdf,json
from PIL import Image,ImageOps,ImageDraw
r=Path.cwd();out=r/'work/render';out.mkdir(exist_ok=True)
d=pymupdf.open(r/'ЛР12_Шевчук_ФЕІм-13с.pdf');info=[]
for i,p in enumerate(d):
 p.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(out/f'page-{i+1}.png')
 blocks=p.get_text('blocks');bad=[list(b[:4]) for b in blocks if b[0]<25 or b[2]>589 or b[3]>814]
 info.append({'page':i+1,'chars':len(p.get_text()),'blocks_outside':bad})
for start in range(0,len(d),6):
 sheet=Image.new('RGB',(900,1300),'#ccc');draw=ImageDraw.Draw(sheet)
 for j in range(start,min(start+6,len(d))):
  im=Image.open(out/f'page-{j+1}.png');im.thumbnail((440,605));x=(j-start)%2*450;y=(j-start)//2*430
  im.thumbnail((440,400));sheet.paste(im,(x,y+24));draw.text((x+10,y+5),str(j+1),fill='black')
 sheet.save(out/f'contact-{start//6+1}.png')
(r/'results/report_check.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),'utf-8')
print('PDF pages:',len(d),'overflow:',[(x['page'],x['blocks_outside']) for x in info if x['blocks_outside']])
