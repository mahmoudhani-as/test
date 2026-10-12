# usage: python3 -I extract.py <marker> <out_file>
# Copies the exact text of the LATEST tool_result in this agent's transcript that contains <marker>.
import json, sys
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_cb294060-2b1/agent-a056558e821784e36.jsonl'
marker, out = sys.argv[1], sys.argv[2]
found=None
for line in open(T, encoding='utf-8'):
    try: e=json.loads(line)
    except Exception: continue
    content=(e.get('message') or {}).get('content')
    if not isinstance(content, list): continue
    for c in content:
        if not isinstance(c, dict) or c.get('type')!='tool_result': continue
        cc=c.get('content')
        texts=[x.get('text','') for x in cc if isinstance(x,dict) and x.get('type')=='text'] if isinstance(cc,list) else [cc if isinstance(cc,str) else '']
        for t in texts:
            if marker in t: found=t
if found is None:
    sys.exit('marker not found')
open(out,'w',encoding='utf-8').write(found)
j=json.loads(found)
print('saved', out, len(found))
