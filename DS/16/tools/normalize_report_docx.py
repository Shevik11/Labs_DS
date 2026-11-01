"""LNU DOCX normalization, requires lxml; --out creates a separate file.

Remove title rules, use black text and 12 pt figure captions.
--check returns 1 when normalization is needed. Does not validate page layout.
"""
import argparse
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as ET

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W = '{' + NS['w'] + '}'

def child(parent, tag):
    found = parent.find('w:' + tag, NS)
    return found if found is not None else ET.SubElement(parent, W + tag)

def assign(el, tag, value):
    node = child(el, tag)
    node.attrib.clear()
    node.set(W + 'val', value)

def normalize(data, name):
    tree = ET.fromstring(data)
    baseline = ET.tostring(tree)
    if name in ('word/styles.xml', 'word/stylesWithEffects.xml'):
        for style in tree.findall('w:style', NS):
            sid = style.get(W + 'styleId', '').lower()
            if sid == 'title':
                for border in style.findall('w:pPr/w:pBdr', NS):
                    border.getparent().remove(border)
            if sid == 'caption':
                pr = child(style, 'rPr')
                for tag, val in [('sz', '24'), ('szCs', '24'), ('b', '0'), ('i', '0')]:
                    assign(pr, tag, val)
    if name == 'word/document.xml':
        cover = True
        for p in tree.findall('w:body/w:p', NS):
            node = p.find('w:pPr/w:pStyle', NS)
            sid = node.get(W + 'val', '') if node is not None else ''
            if sid.lower().startswith('heading') or p.xpath('.//w:br[@w:type="page"]', namespaces=NS):
                cover = False
            if cover or sid.lower() == 'title':
                for border in p.findall('w:pPr/w:pBdr', NS):
                    border.getparent().remove(border)
            text = ''.join(p.itertext()).strip()
            if sid.lower() == 'caption' or re.match(r'^Рис\.\s*\d+\s*[—–-]', text):
                for run in p.findall('w:r', NS):
                    pr = child(run, 'rPr')
                    for tag, val in [('sz', '24'), ('szCs', '24'), ('b', '0'), ('i', '0')]:
                        assign(pr, tag, val)
    # Text colors only; retain code borders and colored chart images.
    for color in tree.findall('.//w:color', NS):
        color.attrib.clear()
        color.set(W + 'val', '000000')
    if name == 'word/document.xml' or name.startswith(('word/header', 'word/footer')):
        for run in tree.xpath('.//w:r | .//m:r', namespaces=NS):
            pr = run.find('w:rPr', NS)
            if pr is None:
                pr = ET.Element(W + 'rPr')
                run.insert(1 if len(run) and run[0].tag == '{'+NS['m']+'}rPr' else 0, pr)
            assign(pr, 'color', '000000')
    if baseline == ET.tostring(tree):
        return data
    return ET.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out', type=Path)
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.out and args.out.resolve() == args.input.resolve():
        parser.error('Use a separate output path; do not overwrite the source.')
    entries, changed = [], []
    with ZipFile(args.input) as z:
        for item in z.infolist():
            data = z.read(item.filename)
            fresh = normalize(data, item.filename) if item.filename.startswith('word/') and item.filename.endswith('.xml') else data
            if fresh != data: changed.append(item.filename)
            entries.append((item, fresh))
    if args.check:
        print('PASS' if not changed else 'NEEDS NORMALIZATION: ' + ', '.join(changed))
        return int(bool(changed))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.out, 'w', ZIP_DEFLATED) as z:
        for item, data in entries: z.writestr(item, data)
    print('Updated: ' + (', '.join(changed) or 'no changes needed'))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
