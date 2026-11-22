import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
tmpl=(root/'site'/'template.html').read_text(encoding='utf-8')
data=json.loads((root/'data'/'schools.json').read_text(encoding='utf-8'))
json_value=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
assert '__SCHOOLS_JSON__' in tmpl
(root/'docs'/'index.html').write_text(tmpl.replace('__SCHOOLS_JSON__',json_value),encoding='utf-8')
print('built',root/'docs'/'index.html')
