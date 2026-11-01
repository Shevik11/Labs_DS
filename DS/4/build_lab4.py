from __future__ import annotations

import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
import fitz

OUT = Path(__file__).resolve().parent
SOURCE = Path(r"D:\LNU\DS\3\model.json")
source = json.loads(SOURCE.read_text(encoding="utf-8"))
labels = {n["id"]: n["label"] for n in source["nodes"]}
ROOT = "root"
groups = [
    ("energy", "Енергетичний контекст", ["object", "meter", "indicator"]),
    ("data", "Дані споживання", ["measurement", "dataset", "series", "period"]),
    ("analysis", "Аналітика", ["task", "model", "result", "metric"]),
    ("software", "Програмне подання", ["module", "view", "filter"]),
    ("interaction", "Використання", ["user", "decision"]),
]
extensions = [
    ("submeter", "Підлічильник", "meter"),
    ("heatmap", "Теплова карта", "view"),
    ("forecast", "Прогноз наступної години", "result"),
]
dependencies = [
    ("meter", "measurement", "реєструє"),
    ("measurement", "series", "формує часовий ряд"),
    ("series", "model", "слугує входом"),
    ("model", "result", "обчислює"),
    ("result", "view", "відображається у"),
    ("view", "decision", "підтримує"),
]

assert len(labels) == 16 and len(set(labels)) == 16
assigned = [nid for _, _, ids in groups for nid in ids]
assert set(assigned) == set(labels) and len(assigned) == len(labels)

nodes = [{"id": ROOT, "label": source["title"], "level": 0, "kind": "root"}]
edges = []
for gid, glabel, ids in groups:
    nodes.append({"id": gid, "label": glabel, "level": 1, "kind": "category"})
    edges.append({"source": ROOT, "target": gid, "relation": "охоплює"})
    for nid in ids:
        old = next(n for n in source["nodes"] if n["id"] == nid)
        nodes.append({"id": nid, "label": old["label"], "level": 2,
                      "kind": "concept", "definition": old["definition"],
                      "source_lab": 3})
        edges.append({"source": gid, "target": nid, "relation": "включає поняття"})
extension_nodes = [{"id": n, "label": label, "parent": parent,
                    "level": 3, "kind": "extension_example", "relation": "підтип або спеціалізація"}
                   for n, label, parent in extensions]
model = {
    "title": "Таксономія понять візуалізації енергетичних даних",
    "variant": source["variant"],
    "semantics": "Рівні 0–2: тематичне групування понять. Рівень 3: приклади спеціалізації; не є частиною базових 16 концептів. Операційні залежності подано окремо і вони не є таксономічними ребрами.",
    "nodes": nodes,
    "edges": edges,
    "extension_tests": extension_nodes,
    "operational_dependencies": [
        {"source": a, "target": b, "relation": rel} for a, b, rel in dependencies
    ],
    "source": "Лабораторна робота №3, model.json",
}
(OUT / "taxonomy.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

# Rooted tree invariants and extension placement.
ids = {n["id"] for n in nodes}
assert len(ids) == len(nodes) == 22
assert len(edges) == len(nodes) - 1
assert all(e["source"] in ids and e["target"] in ids for e in edges)
assert len({e["target"] for e in edges}) == len(edges)
assert all(e["parent"] in labels for e in extension_nodes)
assert all(a in labels and b in labels for a, b, _ in dependencies)

W, H = 1800, 1120
font_dir = Path(r"C:\Windows\Fonts")
font = ImageFont.truetype(str(font_dir / "arial.ttf"), 25)
font_bold = ImageFont.truetype(str(font_dir / "arialbd.ttf"), 27)
font_small = ImageFont.truetype(str(font_dir / "arial.ttf"), 22)
font_title = ImageFont.truetype(str(font_dir / "arialbd.ttf"), 34)
im = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(im)

def centered(text, box, ft, fill="#000000"):
    x0, y0, x1, y1 = box
    bb = d.textbbox((0, 0), text, font=ft)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x0 + (x1-x0-tw)/2, y0 + (y1-y0-th)/2 - bb[1]), text, font=ft, fill=fill)

def box(text, rect, fill, outline="#45515D", ft=font):
    d.rounded_rectangle(rect, radius=12, fill=fill, outline=outline, width=2)
    centered(text, rect, ft)

def line(a, b, color="#56616B", width=3):
    d.line((a, b), fill=color, width=width)

centered("Таксономія понять візуалізації енергетичних даних", (0, 20, W, 76), font_title)
centered("Енергетика / Програмне забезпечення / Візуалізація", (0, 75, W, 112), font_small)
root_box = (445, 125, 1355, 196)
box("Візуалізація енергетичних даних", root_box, "#E8EDF2", ft=font_bold)
col_x = [40, 392, 744, 1096, 1448]
col_w = 312
cat_y = (315, 382)
leaf_top, leaf_gap, leaf_h = 490, 108, 68
colors = ["#F7F0DC", "#E6EFF8", "#EEEAF8", "#E8F2EB", "#F5EAF0"]
for i, (gid, glabel, concepts) in enumerate(groups):
    x = col_x[i]
    cx = x + col_w/2
    line((W/2, root_box[3]), (W/2, 260))
    line((W/2, 260), (cx, 260))
    line((cx, 260), (cx, cat_y[0]))
    box(glabel, (x, cat_y[0], x+col_w, cat_y[1]), colors[i], ft=font)
    spine_x = x + 15
    last_mid_y = leaf_top + (len(concepts)-1)*leaf_gap + leaf_h/2
    line((cx, cat_y[1]), (cx, 420))
    line((cx, 420), (spine_x, 420))
    line((spine_x, 420), (spine_x, last_mid_y))
    for j, nid in enumerate(concepts):
        y = leaf_top + j*leaf_gap
        line((spine_x, y+leaf_h/2), (x+35, y+leaf_h/2))
        box(labels[nid], (x+35, y, x+col_w, y+leaf_h), colors[i], ft=font_small)

d.line((40, 936, 1760, 936), fill="#B6BDC3", width=2)
centered("Операційна залежність між поняттями — окремо від дерева категорій", (0, 946, W, 990), font_bold)
flow = ["Засіб обліку", "Вимірювання", "Часовий ряд", "Аналітична модель", "Результат аналізу", "Візуалізація"]
flow_x = [38, 338, 638, 938, 1238, 1538]
for i, (x, label) in enumerate(zip(flow_x, flow)):
    box(label, (x, 1000, x+224, 1063), "#F3F3F3", ft=font_small)
    if i < len(flow)-1:
        d.line((x+226, 1032, flow_x[i+1]-10, 1032), fill="#56616B", width=3)
        d.polygon([(flow_x[i+1]-10, 1032), (flow_x[i+1]-22, 1025), (flow_x[i+1]-22, 1039)], fill="#56616B")
centered("16 понять із лабораторної №3 · 5 категорій · 1 корінь · 21 ребро", (0, 1070, W, 1110), font_small)
im.save(OUT / "Таксономія_Енергетика.png", dpi=(180, 180))

mx = Element("mxfile", host="app.diagrams.net", version="24.7.17", type="device")
diagram = SubElement(mx, "diagram", id="taxonomy-energy", name="Таксономія")
gm = SubElement(diagram, "mxGraphModel", dx=str(W), dy=str(H), grid="1", gridSize="10", page="1", pageWidth=str(W), pageHeight=str(H))
rt = SubElement(gm, "root")
SubElement(rt, "mxCell", id="0")
SubElement(rt, "mxCell", id="1", parent="0")

def cell(nid, value, rect, fill, size=25):
    x0, y0, x1, y1 = rect
    style = f"rounded=1;whiteSpace=wrap;html=0;fillColor={fill};strokeColor=#45515D;fontColor=#000000;fontSize={size};fontFamily=Arial;"
    c = SubElement(rt, "mxCell", id=nid, value=value, style=style, vertex="1", parent="1")
    SubElement(c, "mxGeometry", x=str(x0), y=str(y0), width=str(x1-x0), height=str(y1-y0), attrib={"as": "geometry"})

cell(ROOT, "Візуалізація енергетичних даних", root_box, "#E8EDF2", 27)
for i, (gid, glabel, concepts) in enumerate(groups):
    x = col_x[i]
    cell(gid, glabel, (x, cat_y[0], x+col_w, cat_y[1]), colors[i], 25)
    for j, nid in enumerate(concepts):
        y = leaf_top+j*leaf_gap
        cell(nid, labels[nid], (x+35, y, x+col_w, y+leaf_h), colors[i], 22)
for i, e in enumerate(edges, 1):
    c = SubElement(rt, "mxCell", id=f"T{i:02}", value="", style="endArrow=block;html=0;rounded=0;strokeColor=#56616B;strokeWidth=2;", edge="1", parent="1", source=e["source"], target=e["target"])
    SubElement(c, "mxGeometry", relative="1", attrib={"as": "geometry"})
for nid, value, y, size in [
    ("diagram_title", "Таксономія понять візуалізації енергетичних даних", 20, 34),
    ("diagram_subtitle", "Енергетика / Програмне забезпечення / Візуалізація", 75, 23),
    ("flow_title", "Операційна залежність між поняттями — окремо від дерева категорій", 946, 27),
    ("diagram_note", "16 понять із лабораторної №3 · 5 категорій · 1 корінь · 21 ребро", 1070, 22),
]:
    c = SubElement(rt, "mxCell", id=nid, value=value,
                   style=f"text;html=0;align=center;verticalAlign=middle;fontColor=#000000;fontSize={size};fontFamily=Arial;",
                   vertex="1", parent="1")
    SubElement(c, "mxGeometry", x="0", y=str(y), width=str(W), height="45", attrib={"as": "geometry"})
for i, label in enumerate(flow):
    x = flow_x[i]
    cell(f"flow_{i}", label, (x, 1000, x+224, 1063), "#F3F3F3", 22)
    if i:
        c = SubElement(rt, "mxCell", id=f"flow_edge_{i}", value="",
                       style="endArrow=block;html=0;strokeColor=#56616B;strokeWidth=2;",
                       edge="1", parent="1", source=f"flow_{i-1}", target=f"flow_{i}")
        SubElement(c, "mxGeometry", relative="1", attrib={"as": "geometry"})
ElementTree(mx).write(OUT / "Таксономія_Енергетика.drawio", encoding="utf-8", xml_declaration=True)

# Standalone, print-ready diagram PDF.
diagram_pdf = fitz.open()
p = diagram_pdf.new_page(width=1190.55, height=841.89)
p.insert_image(fitz.Rect(0, 0, p.rect.width, p.rect.height), filename=str(OUT / "Таксономія_Енергетика.png"))
diagram_pdf.save(OUT / "Таксономія_Енергетика.pdf", deflate=True)
diagram_pdf.close()

print("Created taxonomy JSON, draw.io, PNG, and A3 diagram PDF")

# Report in the same style as the previous laboratory work.
REPORT = "Звіт_Лабораторна_4_Таксономія_Енергетика"
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin, sec.right_margin = Cm(2), Cm(1)
sec.top_margin = sec.bottom_margin = Cm(2)
sec.header_distance = Cm(1)
sec.different_first_page_header_footer = True
for name in ["Normal", "Title", "Heading 1", "Heading 2"]:
    st = doc.styles[name]
    st.font.name = "Times New Roman"
    st.font.size = Pt(14)
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.paragraph_format.space_before = Pt(0)
    st.paragraph_format.space_after = Pt(0)
    st.paragraph_format.line_spacing = 1.5
    st.paragraph_format.first_line_indent = Cm(1.25 if name == "Normal" else 0)
    if name != "Normal":
        st.font.bold = True
        st.paragraph_format.keep_with_next = True
doc.styles["Normal"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
doc.styles["Heading 1"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
header = sec.header.paragraphs[0]
header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
field = OxmlElement("w:fldSimple")
field.set(qn("w:instr"), "PAGE")
header._p.append(field)
doc.core_properties.author = "Шевчук Максим Вікторович"
doc.core_properties.title = "Побудова таксономії понять для візуалізації енергетичних даних"

def paragraph(text, *, bold=False, align=None, first=True, size=14, after=0, style="Normal"):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.first_line_indent = Cm(1.25 if first else 0)
    p.paragraph_format.space_after = Pt(after)
    if align is not None:
        p.alignment = align
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.color.rgb = RGBColor(0, 0, 0)
    return p

def heading(text):
    return paragraph(text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
                     first=False, style="Heading 1", after=6)

def table(title, heads, rows, widths):
    paragraph(title, bold=True, first=False, after=3)
    t = doc.add_table(rows=1, cols=len(heads))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for c, w in zip(t.columns, widths):
        c.width = Cm(w)
    for j, value in enumerate(heads):
        t.rows[0].cells[j].text = value
    for row in rows:
        cells = t.add_row().cells
        for j, value in enumerate(row):
            cells[j].text = str(value)
    for ri, row in enumerate(t.rows):
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr = cell._tc.get_or_add_tcPr()
            borders = OxmlElement("w:tcBorders")
            for side in ["top", "left", "bottom", "right"]:
                edge = OxmlElement(f"w:{side}")
                edge.set(qn("w:val"), "single")
                edge.set(qn("w:sz"), "4")
                edge.set(qn("w:color"), "D9D9D9")
                borders.append(edge)
            tcpr.append(borders)
            if ri == 0:
                shd = OxmlElement("w:shd")
                shd.set(qn("w:fill"), "EEEEEE")
                tcpr.append(shd)
            for p in cell.paragraphs:
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(3)
                for r in p.runs:
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(12)
                    r.font.color.rgb = RGBColor(0, 0, 0)
                    if ri == 0:
                        r.bold = True
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

cover = [
    ("МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ", 12, 0, 3),
    ("ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА", 12, 0, 3),
    ("Факультет електроніки і комп’ютерних технологій", 14, 0, 0),
    ("Звіт", 14, 80, 12),
    ("про виконання лабораторної роботи №4", 14, 0, 12),
    ("з курсу «Вибрані розділи науки про дані»", 14, 0, 20),
    ("«Побудова таксономії понять для візуалізації енергетичних даних»", 14, 0, 55),
]
for value, size, before, after in cover:
    p = paragraph(value, bold=value == "Звіт", align=WD_ALIGN_PARAGRAPH.CENTER,
                  first=False, size=size, after=after, style="Title" if value == "Звіт" else "Normal")
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.2
for value in ["Виконав:", "студент групи ФЕІм-13с", "Шевчук Максим Вікторович",
              "Перевірив:", "Парубочий В. О."]:
    paragraph(value, bold=value.endswith(":"), align=WD_ALIGN_PARAGRAPH.RIGHT,
              first=False).paragraph_format.line_spacing = 1.2
p = paragraph("Львів 2026", align=WD_ALIGN_PARAGRAPH.CENTER, first=False)
p.paragraph_format.space_before = Pt(75)
doc.add_page_break()

heading("Тема та мета роботи")
paragraph("Тема — побудова таксономії понять для візуалізації енергетичних даних засобами програмного забезпечення. Мета — упорядкувати поняття моделі з лабораторної №3 за рівнями, описати ієрархічні та операційні зв’язки і перевірити можливість розширення.")
heading("Завдання")
for item in [
    "1. Визначити рівні таксономії від загальної теми до окремих понять.",
    "2. Розподілити всі 16 ключових концептів лабораторної №3 за рівнями.",
    "3. Побудувати дерево понять у draw.io та пояснити зв’язки між рівнями.",
    "4. Перевірити узгодженість дерева й додати приклади його розширення.",
]:
    paragraph(item, first=False)

heading("1 Вихідна предметна область")
paragraph("Персональний варіант із лабораторної №1:")
for item in [
    "Індустрія — енергетика.",
    "Домен — програмне забезпечення.",
    "Проблема — візуалізація.",
]:
    paragraph(item, first=False)
paragraph("Модель лабораторної №3 містить 16 понять про споживання, дані, аналітику, програмне подання та використання результату. Саме вони є базовим словником цієї таксономії.")
heading("2 Рівні таксономії")
table("Таблиця 1 — Рівні таксономії",
      ["Рівень", "Зміст", "Кількість"], [
          ["0", "Тема: візуалізація енергетичних даних", "1"],
          ["1", "Тематичні категорії", "5"],
          ["2", "Ключові поняття з лабораторної №3", "16"],
          ["3", "Приклади майбутніх спеціалізацій", "3"],
      ], [2.0, 14.5, 2.5])
paragraph("Рівні 0–2 утворюють базове дерево. Рівень 3 використано тільки для тесту розширюваності. Зв’язок між категорією та поняттям означає тематичне включення, а не твердження, що, наприклад, вимірювання є підтипом набору даних.")
heading("3 Розподіл понять")
table("Таблиця 2 — Ключові поняття за категоріями",
      ["Категорія", "Поняття з лабораторної №3"], [
          [glabel, ", ".join(labels[nid] for nid in ids)] for _, glabel, ids in groups
      ], [5.0, 14.0])
paragraph("У кожного базового поняття один батьківський вузол категорії. Таке групування дає змогу знайти поняття за функцією у предметній області й не створює штучного ланцюга «показник → засіб обліку» або «метрика → результат».")

heading("4 Типи зв’язків")
paragraph("У дереві використано два типи ребер: тема «охоплює» категорію; категорія «включає поняття». Ці ребра класифікують словник, але самі по собі не доводять причинності. Причинні й операційні залежності з попередньої граф-моделі наведено окремо в таблиці 3 та нижній частині схеми.")
table("Таблиця 3 — Операційні залежності між поняттями",
      ["Джерело", "Зв’язок", "Ціль"], [
          [labels[a], rel, labels[b]] for a, b, rel in dependencies
      ], [6.0, 6.5, 6.5])
paragraph("Засіб обліку реєструє вимірювання, з яких формують часовий ряд. Аналітична модель використовує цей ряд і обчислює результат; результат показують на візуалізації. Остання підтримує рішення користувача, проте не визначає його автоматично. Послідовність описує процес роботи системи, а не додаткові батьківські зв’язки дерева.")

land = doc.add_section(WD_SECTION_START.NEW_PAGE)
land.orientation = WD_ORIENT.LANDSCAPE
land.page_width, land.page_height = Cm(29.7), Cm(21)
land.left_margin = land.right_margin = Cm(1.5)
land.top_margin = land.bottom_margin = Cm(1.5)
land.header_distance = Cm(0.8)
land.header.is_linked_to_previous = True
heading("5 Графічна модель таксономії")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.first_line_indent = Cm(0)
p.add_run().add_picture(str(OUT / "Таксономія_Енергетика.png"), width=Cm(24.3))
paragraph("Рис. 1 — Дерево категорій і окрема схема операційних залежностей",
          align=WD_ALIGN_PARAGRAPH.CENTER, first=False, size=12, after=6)
paragraph("Для збільшення та редагування схему збережено окремо у форматах PDF, PNG і draw.io.",
          align=WD_ALIGN_PARAGRAPH.CENTER, first=False, size=12)

port = doc.add_section(WD_SECTION_START.NEW_PAGE)
port.orientation = WD_ORIENT.PORTRAIT
port.page_width, port.page_height = Cm(21), Cm(29.7)
port.left_margin, port.right_margin = Cm(2), Cm(1)
port.top_margin = port.bottom_margin = Cm(2)
port.header_distance = Cm(1)
port.header.is_linked_to_previous = True
heading("6 Перевірка коректності")
paragraph("Структурна перевірка підтвердила 22 вузли базової таксономії: один корінь, п’ять категорій і 16 понять. Дерево має 21 ребро, кожне поняття з лабораторної №3 зустрічається рівно один раз, кожний некореневий вузол має одного батька. Всі ребра ведуть від рівня 0 до 1 або від 1 до 2; отже, циклів немає.")
table("Таблиця 4 — Перевірка розширення",
      ["Нове поняття", "Батьківське поняття", "Підстава"], [
          ["Підлічильник", "Засіб обліку", "Спеціалізація приладу обліку"],
          ["Теплова карта", "Візуалізація", "Окремий вид графічного подання"],
          ["Прогноз наступної години", "Результат аналізу", "Частковий тип результату"],
      ], [5.0, 5.0, 9.0])
paragraph("Три нові вузли можна додати на рівень 3 без зміни вже класифікованих понять. Вони наведені як перевірочні приклади й не входять до базових 16 концептів. Редагована схема містить лише базове дерево; розширення задокументовано у таблиці та taxonomy.json.")
heading("Висновок")
paragraph("Побудовано таксономію для персонального варіанта «Енергетика / Програмне забезпечення / Візуалізація». Вона охоплює всі 16 понять попередньої граф-моделі, розміщених у п’яти тематичних категоріях. Окремо описано операційні залежності, що дає змогу читати дерево як класифікацію, не плутаючи його з процесом обробки даних. Перевірка структури та трьох прикладів розширення підтвердила узгодженість базової моделі.")
doc.save(OUT / f"{REPORT}.docx")

# PDF report with the same content. The full-size diagram is a separate A3 page.
pdf = fitz.open()
font_regular = fitz.Font(fontfile=str(font_dir / "times.ttf"))
font_b = fitz.Font(fontfile=str(font_dir / "timesbd.ttf"))

def add_text(page, x, y, text, size=14, bold=False):
    page.insert_text((x, y), text, fontname="TNRB" if bold else "TNR",
                     fontfile=str(font_dir / ("timesbd.ttf" if bold else "times.ttf")),
                     fontsize=size, color=(0, 0, 0))

def wrap(text, max_width, size=14, bold=False):
    f = font_b if bold else font_regular
    lines = []
    for token in text.split():
        if not lines or f.text_length(lines[-1]+" "+token, fontsize=size) > max_width:
            lines.append(token)
        else:
            lines[-1] += " " + token
    return lines

def center(page, y, text, size=14, bold=False):
    f = font_b if bold else font_regular
    width = f.text_length(text, fontsize=size)
    add_text(page, (page.rect.width-width)/2, y, text, size, bold)

cover_pdf = pdf.new_page(width=595.28, height=841.89)
for y, text, size, bold in [
    (66, "МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ", 12, False),
    (86, "ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА", 12, False),
    (110, "Факультет електроніки і комп’ютерних технологій", 14, False),
    (300, "Звіт", 18, True),
    (332, "про виконання лабораторної роботи №4", 14, False),
    (358, "з курсу «Вибрані розділи науки про дані»", 14, False),
    (727, "Львів 2026", 14, False),
]:
    center(cover_pdf, y, text, size, bold)
for i, line_text in enumerate(wrap("«Побудова таксономії понять для візуалізації енергетичних даних»", 460, 14)):
    center(cover_pdf, 395+i*21, line_text)
for i, text in enumerate(["Виконав:", "студент групи ФЕІм-13с", "Шевчук Максим Вікторович",
                           "Перевірив:", "Парубочий В. О."]):
    f = font_b if text.endswith(":") else font_regular
    add_text(cover_pdf, 525-f.text_length(text, fontsize=14), 510+i*24, text, bold=text.endswith(":"))

page = None
y = 0
def new_body_page():
    global page, y
    page = pdf.new_page(width=595.28, height=841.89)
    y = 68
    add_text(page, 515, 36, str(pdf.page_count), 12)

def body(text, *, heading_level=False, after=7, size=14):
    global y
    lines = wrap(text, 480 if not heading_level else 500, size, heading_level)
    needed = len(lines)*(size*1.45)+after
    if page is None or y+needed > 778:
        new_body_page()
    if heading_level:
        for line_text in lines:
            center(page, y, line_text, size, True)
            y += size*1.45
    else:
        for line_text in lines:
            add_text(page, 57, y, line_text, size)
            y += size*1.45
    y += after

body("Тема та мета роботи", heading_level=True)
body("Тема — побудова таксономії понять для візуалізації енергетичних даних засобами програмного забезпечення. Мета — упорядкувати поняття моделі з лабораторної №3 за рівнями, описати ієрархічні та операційні зв’язки і перевірити можливість розширення.")
body("Завдання", heading_level=True)
for item in ["1. Визначити рівні таксономії від загальної теми до окремих понять.",
             "2. Розподілити всі 16 ключових концептів лабораторної №3 за рівнями.",
             "3. Побудувати дерево понять у draw.io та пояснити зв’язки між рівнями.",
             "4. Перевірити узгодженість дерева й додати приклади розширення."]:
    body(item, after=2)
body("1 Вихідна предметна область", heading_level=True)
body("Персональний варіант із лабораторної №1:")
for item in ["Індустрія — енергетика.", "Домен — програмне забезпечення.", "Проблема — візуалізація."]:
    body(item, after=2)
body("Модель лабораторної №3 містить 16 понять про споживання, дані, аналітику, програмне подання та використання результату. Саме вони є базовим словником цієї таксономії.")
body("2 Рівні таксономії", heading_level=True)
for item in ["Рівень 0: тема — візуалізація енергетичних даних (1 вузол).",
             "Рівень 1: тематичні категорії (5 вузлів).",
             "Рівень 2: ключові поняття з лабораторної №3 (16 вузлів).",
             "Рівень 3: приклади майбутніх спеціалізацій (3 перевірочні вузли)."]:
    body(item, after=2)
body("Рівні 0–2 утворюють базове дерево. Рівень 3 використано тільки для перевірки розширення. Категорія включає поняття за темою; це не обов’язково зв’язок типу «є різновидом».")
body("3 Розподіл понять", heading_level=True)
for _, glabel, ids in groups:
    body(glabel + ": " + ", ".join(labels[nid] for nid in ids) + ".", after=4)
body("У кожного базового поняття один батьківський вузол категорії. Це усуває штучні зв’язки між поняттями одного рівня.")
body("4 Типи зв’язків", heading_level=True)
body("Тема охоплює категорії; кожна категорія включає поняття. Операційні залежності подано окремо, бо вони не є ребрами таксономічного дерева.")
for a, b, rel in dependencies:
    body(labels[a] + " — " + rel + " — " + labels[b] + ".", after=2)
body("Послідовність описує процес роботи системи. Візуалізація підтримує рішення користувача, але не визначає його автоматично.")

diagram_page = pdf.new_page(width=1190.55, height=841.89)
diagram_page.insert_image(diagram_page.rect, filename=str(OUT / "Таксономія_Енергетика.png"))
add_text(diagram_page, 1150, 30, str(pdf.page_count), 12)

page = None
body("5 Перевірка коректності", heading_level=True)
body("Структурна перевірка підтвердила 22 вузли базової таксономії: один корінь, п’ять категорій і 16 понять. Дерево має 21 ребро; кожне поняття з лабораторної №3 зустрічається рівно один раз; кожний некореневий вузол має одного батька. Всі ребра йдуть від рівня 0 до 1 або від 1 до 2, тому циклів немає.")
body("Перевірка розширення", heading_level=True)
for nid, label, parent in extensions:
    body(label + " — спеціалізація поняття «" + labels[parent] + "» на рівні 3.")
body("Три нові вузли можна додати без зміни базових категорій. Вони є перевірочними прикладами й не входять до 16 концептів моделі лабораторної №3.")
body("Висновок", heading_level=True)
body("Побудовано таксономію для варіанта «Енергетика / Програмне забезпечення / Візуалізація». Вона охоплює всі 16 понять попередньої граф-моделі у п’яти тематичних категоріях. Операційні залежності подано окремо. Структурна перевірка й три приклади розширення підтвердили узгодженість базової моделі.")
pdf.save(OUT / f"{REPORT}.pdf", deflate=True)
pdf.close()
print("Created DOCX and PDF report")
