# usage: python3 extract.py <marker> <out_file>
# Copies the exact text of the latest tool_result in THIS agent's transcript that contains <marker>.
# If the result says the output was saved to a file path, copies that file instead.
import json, sys, re, shutil
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_cb294060-2b1/agent-ab049e1e8215f3395.jsonl'
marker, out = sys.argv[1], sys.argv[2]
found=None
for line in open(T, encoding='utf-8'):
    try: e=json.loads(line)
    except Exception: continue
    content=(e.get('message') or {}).get('content')
    if not isinstance(content, list): continue
    for c in content:
        if c.get('type')!='tool_result': continue
        cc=c.get('content')
        texts=[x.get('text','') for x in cc if isinstance(x,dict) and x.get('type')=='text'] if isinstance(cc,list) else [cc if isinstance(cc,str) else '']
        for t in texts:
            if marker in t: found=t
if found is None:
    sys.exit('marker not found')
try:
    j=json.loads(found)
    open(out,'w',encoding='utf-8').write(found)
    print('saved', out, len(found))
except Exception:
    m=re.search(r'(/[^\s"\']+\.(?:json|txt))', found)
    if m:
        shutil.copy(m.group(1), out); json.load(open(out)); print('copied saved file', m.group(1), '->', out)
    else:
        open(out,'w',encoding='utf-8').write(found); print('saved non-JSON text', out, len(found))
