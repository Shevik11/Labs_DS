import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from lxml import etree as ET
from pypdf import PdfReader

WORK = Path(__file__).resolve().parent
ROOT = Path('D:/LNU/DS/9')
STEM = 'ЛР09_Шевчук_ФЕІм-13с'
DOCX = WORK / (STEM + '.docx')
RENDER = WORK / 'render_final'
reader = PdfReader(RENDER / (STEM + '.pdf'))
document = Document(DOCX)
texts = [page.extract_text() for page in reader.pages]
full = '\n'.join(texts)
load = lambda path: json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
catalog = load('queries/catalog.json')
pairs = load('comparison/catalog.json')
cell_texts = [table.cell(0, 0).text for table in document.tables if len(table.columns) == 1]
compact = lambda text: re.sub(r'\s+', '', text).rstrip(';')
code_blocks = {compact(text) for text in cell_texts}
with ZipFile(DOCX) as archive:
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    roots = {name: ET.fromstring(archive.read(name)) for name in ['word/document.xml', 'word/styles.xml', 'word/stylesWithEffects.xml']}
    colors_black = all(node.get('{'+ns['w']+'}val') == '000000'
                       for root in roots.values() for node in root.findall('.//w:color', ns))
    no_title_border = all(not root.xpath('//w:style[@w:styleId="Title"]//w:pBdr', namespaces=ns)
                          for name, root in roots.items() if 'styles' in name)
    media_hashes = {hashlib.sha256(archive.read(name)).hexdigest()
                    for name in archive.namelist() if name.startswith('word/media/')}
review = load('results/sandbox_screenshot_review.json')
checks = {
    'all_ten_new_cypher_queries_present_exactly': all(compact(q['query']) in code_blocks for q in catalog if q['origin'] == 'new_lab9'),
    'all_six_paired_query_texts_present': all(compact(pair[k]) in code_blocks for pair in pairs for k in ['sparql', 'cypher']),
    'inherited_importer_not_reprinted': not any('def import_graph' in text or 'def node_statement' in text for text in cell_texts),
    'four_original_screenshots_embedded_without_edits': len(document.inline_shapes) == 4 and all(item['sha256'] in media_hashes for item in review['screenshots']),
    'four_figure_captions_in_sequence': [p.text.split(' — ')[0] for p in document.paragraphs if p.style.name == 'Caption'] == ['Рис. 1', 'Рис. 2', 'Рис. 3', 'Рис. 4'],
    'all_font_colors_black': colors_black,
    'no_title_border_in_both_style_parts': no_title_border,
    'heading_fonts_explicit_times_new_roman_without_theme': all(
        all(value == 'Times New Roman' for key, value in document.styles[name].element.get_or_add_rPr().rFonts.attrib.items()
            if key.endswith('}ascii') or key.endswith('}hAnsi'))
        and not any(key.endswith('Theme') for key in document.styles[name].element.get_or_add_rPr().rFonts.attrib)
        for name in ['Heading 1', 'Heading 2']),
    'all_caption_runs_12pt': all(r.font.size and r.font.size.pt == 12 for p in document.paragraphs if p.style.name == 'Caption' for r in p.runs),
    'code_runs_consolas_12pt': all(r.font.name == 'Consolas' and r.font.size.pt == 12 for t in document.tables if len(t.columns) == 1 for p in t.cell(0, 0).paragraphs for r in p.runs if r.text),
    'page_size_a4': abs(document.sections[0].page_width.cm - 21) < 0.01 and abs(document.sections[0].page_height.cm - 29.7) < 0.01,
    'page_margins_20_20_20_10mm': all(abs(value - expected) < 0.01 for value, expected in [(document.sections[0].left_margin.cm, 2), (document.sections[0].right_margin.cm, 1), (document.sections[0].top_margin.cm, 2), (document.sections[0].bottom_margin.cm, 2)]),
    'author_group_teacher_year_confirmed': all(s in texts[0] for s in ['Шевчук Максим Вікторович', 'ФЕІм-13с', 'Парубочий В. О.', 'Львів 2026']),
    'no_empty_pages': all(len(t.strip()) > 50 for t in texts),
    'all_pages_rendered': all((RENDER / ('page-' + str(i + 1) + '.png')).is_file() for i in range(len(texts))),
    'lab8_references_present': full.count('ЛР08') >= 10 and 'с. 15–16' in full and 'с. 19–20' in full,
    'ai_declaration_present': 'Декларація використання ШІ' in full and 'OpenAI Codex' in full,
    'new_timings_from_verified_local_run': all(s in full for s in ['0,1854', '1,5707', '0,2815', '1,5368', '0,1958', '1,6754']),
    'shortest_path_scopes_distinguished': '26 початкових' in full and '2 ребра TYPE_OF' in full,
    'new_profile_db_hits_present': 'Q3 13' in full and 'Q9 63' in full,
    'no_replacement_glyphs': '\ufffd' not in full,
    'all_five_required_results_present': all(s in full for s in ['1 Модель графа', '2 Ідемпотентний імпорт', '3 Запити Cypher', '4 Шляхи та аналіз графа', '5 Порівняння SPARQL']),
}
result = {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
          'pages': len(texts), 'source': 'DOCX and its actual LibreOffice PDF export',
          'visual_review': 'pending', 'pdf': str(RENDER / (STEM + '.pdf')),
          'docx_sha256': hashlib.sha256(DOCX.read_bytes()).hexdigest(),
          'pdf_sha256': hashlib.sha256((RENDER / (STEM + '.pdf')).read_bytes()).hexdigest()}
(WORK / 'report_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
for i, text in enumerate(texts):
    print(i + 1, len(text), repr(text[:75]), repr(text[-65:]))
print(result['status'], {k: v for k, v in checks.items() if not v})
if not all(checks.values()):
    raise SystemExit(1)
