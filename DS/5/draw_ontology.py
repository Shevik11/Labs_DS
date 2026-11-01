"""Readable class hierarchy and relation diagrams; editable draw.io pages."""
from pathlib import Path
import json, textwrap, xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).resolve().parent
S=json.loads((ROOT/'ontology_structure.json').read_text(encoding='utf-8'))
CL={c['id']:c for c in S['classes']}
DOC=ET.Element('mxfile',host='app.diagrams.net')
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})

def page(name,w,h):
    d=ET.SubElement(DOC,'diagram',name=name,id=name)
    m=ET.SubElement(d,'mxGraphModel',page='1',pageWidth=str(w),pageHeight=str(h))
    root=ET.SubElement(m,'root'); ET.SubElement(root,'mxCell',id='0'); ET.SubElement(root,'mxCell',id='1',parent='0')
    fig,ax=plt.subplots(figsize=(w/90,h/90)); ax.set_xlim(0,w); ax.set_ylim(h,0); ax.axis('off'); fig.subplots_adjust(0,0,1,1)
    return fig,ax,root

def box(ax,root,id_,title,x,y,w=255,h=60,color='#e8f0fb'):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.01,rounding_size=7',facecolor=color,edgecolor='#667991',linewidth=1))
    ax.text(x+w/2,y+h/2,title,ha='center',va='center',fontsize=10)
    cell=ET.SubElement(root,'mxCell',id=id_,value=title,style=f'rounded=1;whiteSpace=wrap;html=0;fillColor={color};fontSize=13;',vertex='1',parent='1')
    ET.SubElement(cell,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})

def arrow(ax,root,id_,src,dst,start,end,title='',hierarchy=False):
    ax.annotate('',xy=end,xytext=start,arrowprops=dict(arrowstyle='-|>',color='#43546c',lw=1.2))
    if title: ax.text((start[0]+end[0])/2,(start[1]+end[1])/2-9,title,ha='center',va='bottom',fontsize=8,color='#25354a')
    cell=ET.SubElement(root,'mxCell',id=id_,value=title,style='edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;'+('endFill=0;' if hierarchy else ''),edge='1',parent='1',source=src,target=dst)
    ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})

def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=160,facecolor='white')
    fig.savefig(ROOT/'figures'/f'{name}.svg',facecolor='white'); plt.close(fig)

def hierarchy():
    parents=[c for c in S['classes'] if c['parent']=='DomainEntity']
    # Each base class and its descendants are in one row; arrows point subtype -> parent.
    fig,ax,root=page('Ієрархія класів',1680,1360)
    ax.text(45,40,'Ієрархія OWL-класів · Енергетика / ПЗ / Візуалізація',fontsize=20,weight='bold')
    ax.text(45,72,'Кожен базовий клас є підкласом DomainEntity. Стрілка: підклас → батьківський клас.',fontsize=12)
    for i,c in enumerate(parents):
        col=i//9; row=i%9; x=45+col*830; y=110+row*130
        box(ax,root,c['id'],c['label']+'\n'+c['id'],x,y,260,62)
        children=[z for z in S['classes'] if z['parent']==c['id']]
        if children:
            # Three-child groups use compact text on separate lines in one visual box.
            title='\n'.join(z['label']+'  ['+z['id']+']' for z in children)
            title='\n'.join(textwrap.fill(line,47) for line in title.splitlines())
            box(ax,root,c['id']+'_children',title,x+325,y-9,450,86,color='#e8f5ec')
            arrow(ax,root,'h_'+c['id'],c['id']+'_children',c['id'],(x+325,y+31),(x+260,y+31),hierarchy=True)
    ax.text(45,1320,'Зелені блоки перелічують окремі підкласи. ForecastVisualization має також еквівалентне визначення через presentsResult some ForecastResult.',fontsize=11)
    save(fig,'01_class_hierarchy')

def relations():
    original=[p for p in S['object_properties'] if not p['label'].startswith('Обернене:')]
    for part in range(3):
        subset=original[part*8:(part+1)*8]
        fig,ax,root=page(f'Зв’язки {part+1}',1300,1050)
        ax.text(40,42,f'Об’єктні властивості · частина {part+1}/3',fontsize=20,weight='bold')
        ax.text(40,75,'Domain → властивість → Range. Класи повторюються для читабельності; це не додаткові класи.',fontsize=11)
        for i,p in enumerate(subset):
            y=115+i*105; a=f'{part}_{i}_a'; b=f'{part}_{i}_b'
            box(ax,root,a,CL[p['domain']]['label']+'\n'+p['domain'],40,y,295,64)
            box(ax,root,b,CL[p['range']]['label']+'\n'+p['range'],965,y,295,64)
            title=p['label']+'\n'+p['id']
            arrow(ax,root,f'{part}_{i}_edge',a,b,(335,y+39),(965,y+39),title)
            detail=('обернена: '+p['inverse'] if p['inverse'] else 'односпрямована')+(' · функціональна (≤1)' if p['functional'] else ' · допускає кілька значень')
            ax.text(650,y+65,detail,fontsize=9,ha='center',color='#596777')
        ax.text(40,1010,'Точні обмеження існування й кратності: ontology_structure.json → restrictions; повна семантика: energy_ontology.owl.',fontsize=11)
        save(fig,f'0{part+2}_object_properties')

if __name__=='__main__':
    (ROOT/'figures').mkdir(exist_ok=True)
    hierarchy(); relations()
    ET.indent(DOC)
    ET.ElementTree(DOC).write(ROOT/'energy_ontology.drawio',encoding='utf-8',xml_declaration=True)
    print('Saved 4 PNG + 4 SVG diagrams and a 4-page draw.io file')
