import json, copy
from urllib.parse import parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread2/work_tiktok_7338074303931449345'
INP='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread/in/tiktok_7338074303931449345.json'
TEMPLATE=json.loads(open(W+'/raw/manual_p1.txt',encoding='utf-8').read())
def resp_size(items, page_size=100, total=None):
    j=copy.deepcopy(TEMPLATE)
    j['data']['data']['data']['list']=items
    j['data']['data']['data']['page_info']={'page':1,'page_size':page_size,'total_page':1,'total_number':total if total is not None else len(items)}
    return len(json.dumps(j, indent=2, ensure_ascii=False))
def utm_list(tags):
    if not tags: return None
    return [{'key':k,'value':v} for k,v in parse_qsl(tags, keep_blank_values=True)]
