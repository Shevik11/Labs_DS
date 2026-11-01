from pathlib import Path
p=Path('report_body.py');s=p.read_text('utf-8-sig');s=s.replace('for offset in range(0,len(lines),39):',"chunk_size=(len(lines)+(len(lines)+38)//39-1)//((len(lines)+38)//39)\n for offset in range(0,len(lines),chunk_size):").replace("lines[offset:offset+39]","lines[offset:offset+chunk_size]");p.write_text(s,'utf-8')
