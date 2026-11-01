doc=Document(); sec=doc.sections[0]
sec.page_width=Cm(21); sec.page_height=Cm(29.7)
sec.top_margin=sec.bottom_margin=sec.left_margin=Cm(2); sec.right_margin=Cm(1)
sec.different_first_page_header_footer=True
for style in doc.styles:
    if style.type in [1,2]:
        style.font.name='Times New Roman'; style.font.size=Pt(14); style.font.color.rgb=RGBColor(0,0,0)
normal=doc.styles['Normal']; normal.paragraph_format.line_spacing=1.5
normal.paragraph_format.first_line_indent=Cm(1.25); normal.paragraph_format.space_after=Pt(0)
normal.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
header=sec.header.paragraphs[0]; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
field=OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE'); header._p.append(field)
def dpara(text,size=14,bold=False,align=None,space_before=0):
    para=doc.add_paragraph(); para.paragraph_format.space_before=Pt(space_before)
    if align is not None: para.alignment=align; para.paragraph_format.first_line_indent=Pt(0)
    rr=para.add_run(text); rr.font.size=Pt(size); rr.bold=bold
    return para

center=WD_ALIGN_PARAGRAPH.CENTER; right=WD_ALIGN_PARAGRAPH.RIGHT
dpara('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ',12,align=center)
dpara('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА',12,align=center)
dpara('Факультет електроніки і комп’ютерних технологій',align=center)
title=dpara('Звіт',bold=True,align=center,space_before=85); title.style=doc.styles['Title']
dpara('про виконання лабораторної роботи №12',align=center,space_before=8)
dpara('з курсу «Вибрані розділи науки про дані»',align=center,space_before=8)
dpara('«Інтегрована система: RAG + граф знань + API»',align=center,space_before=15)
dpara('Виконав:',bold=True,align=right,space_before=65)
dpara('студент групи ФЕІм-13с',align=right)
dpara('Шевчук Максим Вікторович',align=right)
dpara('Перевірив:',bold=True,align=right,space_before=12)
dpara('Парубочий В. О.',align=right)
dpara('Львів 2026',align=center,space_before=60)

body_style=ParagraphStyle('body',fontName='TNR',fontSize=14,leading=21,alignment=TA_JUSTIFY,firstLineIndent=12.5*mm,spaceAfter=5)
heading_style=ParagraphStyle('heading',fontName='TNRB',fontSize=14,leading=18,alignment=TA_CENTER,spaceAfter=10,keepWithNext=True)
cell_style=ParagraphStyle('cell',fontName='TNR',fontSize=14,leading=16)
caption_style=ParagraphStyle('caption',fontName='TNR',fontSize=12,leading=14,alignment=TA_CENTER,spaceAfter=6)
code_style=ParagraphStyle('code',fontName='CONS',fontSize=12,leading=14.2,backColor=colors.HexColor('#F2F2F2'),borderColor=colors.HexColor('#D9D9D9'),borderWidth=.5,borderPadding=4)
story=[Spacer(1,1)]
def para(s,style): return Paragraph(escape(s).replace('\n','<br/>'),style)
for items in pages:
    story.append(PageBreak()); doc.add_page_break()
    for item in items:
        kind=item[0]
        if kind=='h':
            pp=dpara(item[1],bold=True,align=center); pp.paragraph_format.keep_with_next=True; pp.paragraph_format.space_after=Pt(8)
            story.append(para(item[1],heading_style))
        elif kind=='p':
            dpara(item[1]); story.append(para(item[1],body_style))
        elif kind=='table':
            _,title,heads,rows,widths=item
            pp=dpara(title,align=WD_ALIGN_PARAGRAPH.LEFT); pp.paragraph_format.keep_with_next=True
            tab=doc.add_table(rows=1,cols=len(heads)); tab.style='Table Grid'; tab.autofit=False
            for i,(head,width) in enumerate(zip(heads,widths)):
                tab.columns[i].width=Cm(width/10); tab.rows[0].cells[i].text=head
            for row in rows:
                cells=tab.add_row().cells
                for i,value in enumerate(row): cells[i].text=str(value)
            for ri,row in enumerate(tab.rows):
                for ci,cell in enumerate(row.cells):
                    cell.width=Cm(widths[ci]/10)
                    for pp in cell.paragraphs:
                        pp.paragraph_format.first_line_indent=Pt(0); pp.paragraph_format.line_spacing=1
                        pp.paragraph_format.space_after=Pt(4); pp.paragraph_format.space_before=Pt(4)
                        for rr in pp.runs: rr.bold=ri==0
            cells=[[para(str(x),cell_style) for x in row] for row in [heads]+rows]
            rt=Table(cells,colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
            rt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.black),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([para(title,ParagraphStyle('tc',parent=body_style,firstLineIndent=0,keepWithNext=True)),rt,Spacer(1,8)])
        elif kind=='image':
            _,path,caption,width=item
            pp=doc.add_paragraph(); pp.alignment=center; pp.paragraph_format.first_line_indent=Pt(0); pp.paragraph_format.keep_with_next=True
            pp.add_run().add_picture(path,width=Cm(width/10))
            pp=dpara(caption,12,align=center); pp.paragraph_format.line_spacing=1
            from PIL import Image as PILImage
            with PILImage.open(path) as im: iw,ih=im.size
            story.append(KeepTogether([Image(path,width=width*mm,height=width*mm*ih/iw),para(caption,caption_style)]))
        else:
            pp=doc.add_paragraph(); pp.paragraph_format.first_line_indent=Pt(0); pp.paragraph_format.line_spacing=1
            rr=pp.add_run(item[1]); rr.font.name='Consolas'; rr.font.size=Pt(12)
            pr=pp._p.get_or_add_pPr(); shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'F2F2F2'); pr.append(shade)
            borders=OxmlElement('w:pBdr')
            for side in ['top','left','bottom','right']:
                b=OxmlElement('w:'+side); b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'4'); b.set(qn('w:color'),'D9D9D9'); b.set(qn('w:space'),'3'); borders.append(b)
            pr.append(borders)
            listing=Table([[Preformatted(item[1],code_style)]],colWidths=[180*mm])
            listing.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F2F2F2')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#D9D9D9')),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
            story.append(listing)

doc.core_properties.author='Шевчук Максим Вікторович'; doc.core_properties.title='ЛР12 Інтегрована система RAG + граф знань + API'
doc.save(ROOT/(STEM+'.docx'))
def first(canvas,document):
    def text(t,y,size=14,bold=False,alignment='center'):
        canvas.setFont('TNRB' if bold else 'TNR',size); canvas.setFillColor(colors.black)
        if alignment=='right': canvas.drawRightString(A4[0]-20*mm,A4[1]-y,t)
        else: canvas.drawCentredString(A4[0]/2,A4[1]-y,t)
    text('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ',80,12)
    text('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА',98,12)
    text('Факультет електроніки і комп’ютерних технологій',120)
    text('Звіт',232,bold=True)
    text('про виконання лабораторної роботи №12',260)
    text('з курсу «Вибрані розділи науки про дані»',288)
    text('«Інтегрована система:',330)
    text('RAG + граф знань + API»',352)
    text('Виконав:',480,bold=True,alignment='right')
    text('студент групи ФЕІм-13с',502,alignment='right')
    text('Шевчук Максим Вікторович',524,alignment='right')
    text('Перевірив:',562,bold=True,alignment='right')
    text('Парубочий В. О.',584,alignment='right')
    text('Львів 2026',755)
def later(canvas,document):
    canvas.setFont('TNR',14); canvas.drawRightString(A4[0]-10*mm,A4[1]-13*mm,str(document.page))
pdf=SimpleDocTemplate(str(ROOT/(STEM+'.pdf')),pagesize=A4,leftMargin=20*mm,rightMargin=10*mm,topMargin=20*mm,bottomMargin=20*mm,title=doc.core_properties.title,author=doc.core_properties.author)
pdf.build(story,onFirstPage=first,onLaterPages=later)
(ROOT/'work/report_content.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
print('Created',STEM,'logical pages',len(pages)+1)
