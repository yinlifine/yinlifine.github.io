"""Offline sanity test for conservative change-monitor behavior."""
import importlib.util
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('check_sources',root/'scripts/check_sources.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Response:
    def __init__(self,html):
        self.text=html;self.headers={'content-type':'text/html'};self.url='https://demo.edu.cn/notice/';self.encoding='utf-8';self.apparent_encoding='utf-8'
    def raise_for_status(self):return None
    def __bool__(self):return True

def html(variant):
    extra=('<a href="/2027-new-phd">2027年教育学博士新公告</a>' if variant else '')
    return f'<html><head><title>博士招生</title></head><body><main><h1>2027博士招生信息</h1><p>{"年度招生日期调整" if variant else "招生工作日程请关注学校官方网站"}</p>{"最新公告须按照学校章程和学院招生实施细则核对报名时间、申请材料、导师安排和资格要求。"*2}{extra}</main></body></html>'

with tempfile.TemporaryDirectory() as tmp:
    t=Path(tmp);(t/'data').mkdir();(t/'docs/data').mkdir(parents=True)
    (t/'data/schools.json').write_text(json.dumps({'schools':[{'id':'demo','name':'测试大学','monitorUrls':['https://demo.edu.cn/notice/']}]}),encoding='utf8')
    mod.DATA_FILE=t/'data/schools.json';mod.STATE_FILE=t/'data/source_state.json';mod.OUT_FILE=t/'docs/data/monitor.json'
    with patch.object(mod.requests,'get',lambda *a,**k:Response(html(False))):
        assert mod.main()==0
    assert not json.loads(mod.OUT_FILE.read_text())['changes']
    with patch.object(mod.requests,'get',lambda *a,**k:Response(html(True))):
        assert mod.main()==0
    result=json.loads(mod.OUT_FILE.read_text())
    assert len(result['changes'])==1, result
    assert len(result['discovered'])==1,result
    assert result['summary']['ok']==1
print('Passed: initial check creates baseline; changed official page and new relevant link are flagged as unverified.')
