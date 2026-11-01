from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

path = Path(r"D:\LNU\DS\1\Звіт_Лабораторна_1_Енергетика_Візуалізація.docx")
doc = Document(path)
course = "з курсу «Вибрані розділи науки про дані»"
changed_course = changed_teacher = False
for i, para in enumerate(doc.paragraphs):
    if para.text == "з курсу «Методи видобування даних»":
        para.runs[0].text = course
        changed_course = True
    if para.text == "Перевірив:" and i + 1 < len(doc.paragraphs):
        teacher = doc.paragraphs[i + 1]
        teacher.clear()
        run = teacher.add_run("Парубочий В. О.")
        run.font.name = "Times New Roman"
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0, 0, 0)
        teacher.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        teacher.paragraph_format.first_line_indent = Pt(0)
        changed_teacher = True
if not changed_course or not changed_teacher:
    raise RuntimeError(f"Fields not updated: course={changed_course}, teacher={changed_teacher}")
doc.core_properties.subject = "Вибрані розділи науки про дані: електроспоживання, класифікація, регресія, кластеризація"
doc.save(path)
print(path)
