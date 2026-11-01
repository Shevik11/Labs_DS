from pathlib import Path
import json
r=Path.cwd();run=json.loads((r/'results/run.json').read_text('utf-8'))
versions=run['versions'];versions['numpy']='1.26.4'
(r/'requirements.txt').write_text('\n'.join(k+'=='+v for k,v in versions.items())+'\nsentencepiece==0.2.0\nprotobuf==5.29.3\n','utf-8')
