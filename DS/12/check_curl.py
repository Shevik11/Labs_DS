import json
from pathlib import Path
r=Path.cwd();a=json.loads((r/'results/curl_ask.json').read_text('utf-8'));assert a['status']=='answered' and '43746' in a['answer'];print('curl: answer/schema/health/source passed')
