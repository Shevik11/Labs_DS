from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from docx import Document
import json, hashlib, re

ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'Звіт_Лабораторна_5_Онтологія_Енергетика.docx'
doc=Document(path)
text='\n'.join(p.text for p in doc.paragraphs)+'\n'+'\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
checks={}
def test(name,result):
    checks[name]=bool(result)
    assert result,name
test('author', 'Шевчук Максим Вікторович' in text)
test('group', 'ФЕІм-13с' in text)
test('teacher_from_same_course', 'Парубочий В. О.' in text)
test('year_from_previous_labs', 'Львів 2026' in text)
test('lab5', 'про виконання лабораторної роботи №5' in text)
test('honest_protege_status','імпортовано у WebProtégé' in text and 'HermiT виконано локально через Owlready2' in text and 'не проведено' not in text)
test('theme_without_lab1_reference','Тематичний напрям роботи — енергетика, програмне забезпечення та візуалізація.' in text and 'Персональний варіант із лабораторної №1' not in text)
test('removed_export_paragraph','Експорт редактора збережено як energy_ontology_webprotege.owl' not in text)
test('removed_user_marked_source_block','Використані джерела' not in text and 'https://protege.stanford.edu/software/' not in text and '[1–3]' not in text)
test('results',all(s in text for s in ['31 клас','28 об’єктних властивостей','34 атрибути','26 екземплярів','88 перевірок']))
s=json.loads((ROOT/'ontology_structure.json').read_text(encoding='utf-8'))
test('all_34_attribute_names', all(a['id'] in text for a in s['data_properties']))
test('all_16_class_ids',all(x in text for x in s['lab3_mapping'].values()))
caps=[p for p in doc.paragraphs if p.text.startswith('Рис. ')]
test('captions_1_through_7',[p.text[:6] for p in caps]==[f'Рис. {i}' for i in range(1,8)])
test('caption_12pt',all(all(r.font.size.pt==12 for r in p.runs if r.text) for p in caps))
test('image_count',len(doc.inline_shapes)==7)
test('portrait_A4',len(doc.sections)==1 and abs(doc.sections[0].page_width.cm-21)<.01 and abs(doc.sections[0].page_height.cm-29.7)<.01)
test('margins',all(abs(x.cm-y)<.01 for x,y in [(doc.sections[0].left_margin,2),(doc.sections[0].right_margin,1),(doc.sections[0].top_margin,2),(doc.sections[0].bottom_margin,2)]))
test('appendices_after_conclusion', text.index('Додаток А')>text.index('Висновок') and text.index('Додаток Б')>text.index('Додаток А'))
code=[r for p in doc.paragraphs for r in p.runs if r.font.name=='Consolas']
test('code_12pt_black',len(code)==3 and all(r.font.size.pt==12 and str(r.font.color.rgb)=='000000' for r in code))
with ZipFile(path) as z:
    for part in ['word/document.xml','word/styles.xml','word/stylesWithEffects.xml']:
        if part not in z.namelist():continue
        x=etree.fromstring(z.read(part))
        bad=x.xpath('//w:rPr/w:color[@w:val!="000000"]',namespaces=ns)
        test(part+'_black_text',not bad)
        if 'styles' in part:
            test(part+'_title_no_border',not x.xpath('//w:style[@w:styleId="Title"]//w:pBdr',namespaces=ns))
    x=etree.fromstring(z.read('word/document.xml'))
    titles=x.xpath('//w:p[w:pPr/w:pStyle[@w:val="Title"]]',namespaces=ns)
    test('title_direct_no_border',all(not p.xpath('./w:pPr/w:pBdr',namespaces=ns) for p in titles))
    test('shaded_code_blocks',len(x.xpath('//w:pPr/w:shd[@w:fill="F2F2F2"]',namespaces=ns))==3)
old=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
test('original_ontology_unchanged',all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==old[f] for f in ['energy_ontology.owl','energy_ontology.ttl','ontology_structure.json']))
export=json.loads((ROOT/'results/webprotege_validation.json').read_text(encoding='utf-8'))
test('webprotege_export_verified',export['status']=='passed' and all(export['checks'].values()))
with ZipFile(path) as z:
    embedded={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
    evidence=ROOT/'results/webprotege_screenshots'
    from PIL import Image
    import io
    crops={'04_records_domain_range.png':(581,62,1526,525),'05_numeric_value_datatype.png':(581,65,1527,600),'06_measurement1_values.png':(581,62,1527,738),'07_forecast_values.png':(581,81,1527,851)}
    expected={hashlib.sha256((evidence/'02_expanded_class_hierarchy.png').read_bytes()).hexdigest()}
    for name,box in crops.items():
        output=io.BytesIO()
        Image.open(evidence/name).crop(box).save(output,format='PNG')
        expected.add(hashlib.sha256(output.getvalue()).hexdigest())
    test('authentic_screenshot_panels_embedded',expected.issubset(embedded))
result={'status':'passed','checks':checks,'count':len(checks),'docx_visual_render':'unavailable: bundled LibreOffice absent; no registered Word COM','pdf_visual_review':'performed separately on every rendered page','reference_pdf_pages':{'lab3':7,'lab4':5}}
(ROOT/'work/report/report_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS:',len(checks),'report checks')
