from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn

path = Path(r"D:\LNU\DS\1\Звіт_Лабораторна_1_Енергетика_Візуалізація.docx")
doc = Document(path)
prefix = "На рис. 1 показано суму споживання за кожну повну добу."
replacement = (
    "На рис. 1 видно, що влітку добове споживання загалом нижче, а взимку — вище. "
    "Імовірне пояснення: улітку мешканці можуть більше часу проводити надворі, а взимку — "
    "довше залишатися вдома; додаткове споживання може бути пов’язане з опаленням. "
    "Це можливе тлумачення сезонного малюнка, а не встановлена причина, адже набір не містить "
    "відомостей про присутність мешканців чи систему опалення. На початку періоду також є "
    "окремі піки близько 80 кВт·год/добу. Розриви лінії відповідають дням без 24 повних годин вимірювань."
)
matches = [p for p in doc.paragraphs if p.text.startswith(prefix)]
if len(matches) != 1:
    raise RuntimeError(f"Expected exactly one graph-1 explanation; found {len(matches)}")
para = matches[0]
para.clear()
run = para.add_run(replacement)
run.font.name = "Times New Roman"
run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0, 0, 0)
doc.save(path)
print(path)
