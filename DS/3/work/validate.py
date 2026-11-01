from pathlib import Path
from docx import Document
from docx.shared import Cm
from xml.etree import ElementTree as ET
import json, hashlib
r=Path(r'D:\LNU\DS\3')
p=r/'work'/'report-clean.docx'
d=Document(p)
for table,widths in zip(d.tables,[[4,9.1,4.9],[4,9.1,4.9],[6.1,5.8,6.1]]):
    for row in table.rows:
        for cell,width in zip(row.cells,widths):cell.width=Cm(width)
d.save(r/'Звіт_Лабораторна_3_Моделювання_Енергетика.docx')
m=json.loads((r/'model.json').read_text(encoding='utf-8'))
nodes={n['id'] for n in m['nodes']};degree={n:0 for n in nodes};adj={n:set() for n in nodes}
for e in m['relations']:
    a,b=e['source'],e['target'];assert a in nodes and b in nodes;degree[a]+=1;degree[b]+=1;adj[a].add(b);adj[b].add(a)
seen=set();queue=[next(iter(nodes))]
while queue:
    n=queue.pop()
    if n not in seen:seen.add(n);queue.extend(adj[n]-seen)
assert seen==nodes and all(degree.values())
xml=ET.parse(r/'Граф_модель_Енергетика.drawio')
verts={x.attrib['id']:x for x in xml.findall('.//mxCell') if x.attrib.get('vertex')=='1'}
edges={x.attrib['id']:x for x in xml.findall('.//mxCell') if x.attrib.get('edge')=='1'}
assert nodes <= verts.keys() and len(edges)==20
for e in m['relations']:
    v=edges[e['id']].attrib
    assert (v['source'],v['target'],v['value'])==(e['source'],e['target'],e['predicate'])
texts='\n'.join(p.text for p in d.paragraphs)+'\n'+'\n'.join(c.text for t in d.tables for row in t.rows for c in row.cells)
assert all(n['label'] in texts for n in m['nodes'])
assert len(d.tables)==3 and len(d.tables[-1].rows)==21
results={'concepts':len(nodes),'relations':len(edges),'connected':True,'isolated':0,'drawio_json_agree':True,'docx_concepts_present':True,'pdf_pages':8,'pdf_visual_review':'all 8 pages and full-size diagram inspected','docx_visual_review':'unavailable: bundled LibreOffice is absent on Windows','source_pdf_sha256':hashlib.sha256((r/'ds_lab_3.pdf').read_bytes()).hexdigest()}
(r/'work'/'validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
