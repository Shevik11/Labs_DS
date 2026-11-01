from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

path = Path(r"D:\LNU\DS\1\Звіт_Лабораторна_1_Енергетика_Візуалізація.docx")
doc = Document(path)
target_text = "Індустрію задано як енергетику, домен — програмний аналітичний модуль, а задачу — візуалізацію. Щоб виконати вимоги методички, окрім графіків проведено три види аналізу: класифікацію, регресію та кластеризацію."
target = next((x for x in doc.paragraphs if x.text == target_text), None)
if target is None:
    raise RuntimeError("Target paragraph not found")

def format_run(run, bold=False):
    run.font.name = "Times New Roman"
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0, 0, 0)
    run.bold = bold

def set_text(paragraph, text, bold=False):
    paragraph.clear()
    format_run(paragraph.add_run(text), bold)
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.5
    return paragraph

set_text(target, "Персональний варіант:", bold=True)
items = [
    "• Індустрія: енергетика.",
    "• Домен: програмне забезпечення.",
    "• Задача: візуалізація.",
    "Відповідно до методички, результати візуалізовано для класифікації, регресії та кластеризації.",
]
anchor = target
for value in items:
    element = OxmlElement("w:p")
    anchor._p.addnext(element)
    paragraph = Paragraph(element, anchor._parent)
    set_text(paragraph, value, bold=False)
    if value.startswith("•"):
        paragraph.paragraph_format.left_indent = Cm(0.6)
        paragraph.paragraph_format.first_line_indent = Cm(-0.35)
    anchor = paragraph

doc.save(path)
print(path)
