from pathlib import Path
parts=[Path(n).read_text('utf-8-sig') for n in ['report_head.py','report_body.py','report_tail.py']]
Path('build_report.py').write_text('\n'.join(parts),'utf-8')
