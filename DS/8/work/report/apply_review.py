from pathlib import Path
import shutil
root=Path(r'D:\LNU\DS\8');work=root/'work/report'
backup=work/'before_review';backup.mkdir(exist_ok=True)
for f in [root/'Звіт_Лабораторна_8_Neo4j_Енергетика.docx',root/'Звіт_Лабораторна_8_Neo4j_Енергетика.pdf',work/'build_report.py']:
    if not (backup/f.name).exists():shutil.copy2(f,backup/f.name)
p=work/'build_report.py';s=p.read_text(encoding='utf-8')
s=s.replace('Варіант із лабораторної №1: енергетика, програмне забезпечення, візуалізація.', 'Тематичний напрям роботи — енергетика, програмне забезпечення та візуалізація.')
s=s.replace("170,(0,100,650,235)","100,(30,135,465,238)")
s=s.replace("170,(0,90,650,228)","100,(25,139,460,242)")
s=s.replace("180,(510,105,1818,864)","180,(530,200,1798,824)")
s=s.replace("120,(10,120,800,750)","95,(170,235,625,650)")
s=s.replace("180,(300,190,1317,465)","180,(330,197,1298,420)")
s=s.replace("130,(10,140,800,730)","110,(155,175,655,650)")
start=s.index(",\n h('Використані джерела')")
end=s.index('\n\n# Keep the complete',start)
s=s[:start]+')'+s[end:]
old="""    return ('screen',str(ROOT/'results/screenshots'/name),caption,width,box)"""
new="""    path=ROOT/'results/screenshots'/name
    if box:
        # Materialize the document viewport so Word and previews show the same crop.
        # The original evidence image remains unchanged in results/screenshots.
        target=WORK/'cropped_figures'/name
        target.parent.mkdir(exist_ok=True)
        with Image.open(path) as original:
            original.crop(box).save(target)
        path=target
    return ('screen',str(path),caption,width,None)"""
assert old in s
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('Updated topic, removed sources, corrected figure viewports.')
