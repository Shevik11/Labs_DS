from pathlib import Path
import shutil,json,hashlib
root=Path(r'D:\LNU\DS\8');work=root/'work/report';stem='Звіт_Лабораторна_8_Neo4j_Енергетика'
review=work/'docx-render-review';final=work/'docx-render-final'
for f in review.iterdir():
    if f.suffix.lower() in {'.png','.pdf'}:shutil.copy2(f,final/f.name)
shutil.copy2(review/(stem+'.pdf'),root/(stem+'.pdf'))
p=work/'check_report.py';s=p.read_text(encoding='utf-8')
anchor="'pdf_pages_20':len(reader.pages)==20,"
addition="""'pdf_pages_20':len(reader.pages)==20,
'no_sources_section':'Використані джерела' not in text,
'independent_topic':'Варіант із лабораторної №1' not in text and 'Тематичний напрям роботи — енергетика, програмне забезпечення та візуалізація.' in text,
'preview_safe_image_crops':not doc._element.xpath('.//a:srcRect'),"""
assert anchor in s
s=s.replace(anchor,addition)
p.write_text(s,encoding='utf-8')
print('Final PDF is the actual export of the updated DOCX.')
