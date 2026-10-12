# usage: python3 -I extract.py <marker> <out_file>
# Copies the exact text of the latest tool_result in THIS agent's transcript that contains <marker>.
# If that result says the output was saved to a file, copies that saved file instead.
import json, sys, re, shutil
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_24c2ba83-4c4/agent-a919e0588b2b5257b.jsonl'
marker, out = sys.argv[1], sys.argv[2]
found = None
for line in open(T, encoding='utf-8'):
    try:
        e = json.loads(line)
    except Exception:
        continue
    content = (e.get('message') or {}).get('content')
    if not isinstance(content, list):
        continue
    for c in content:
        if not isinstance(c, dict) or c.get('type') != 'tool_result':
            continue
        cc = c.get('content')
        texts = [x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text'] if isinstance(cc, list) else [cc if isinstance(cc, str) else '']
        for t in texts:
            if marker in t:
                found = t
if found is None:
    sys.exit('marker not found')
try:
    json.loads(found)
    open(out, 'w', encoding='utf-8').write(found)
    print('saved', out, len(found))
except Exception:
    m = re.search(r'(/[^\s"\']+\.(?:json|txt))', found)
    if m:
        src = open(m.group(1), encoding='utf-8').read()
        try:
            j = json.loads(src)
            if isinstance(j, list) and j and isinstance(j[0], dict) and 'text' in j[0]:
                src = j[0]['text']
                json.loads(src)
        except Exception as ex:
            print('warn: saved file not plain JSON:', ex)
        open(out, 'w', encoding='utf-8').write(src)
        print('copied saved file', m.group(1), '->', out, len(src))
    else:
        open(out, 'w', encoding='utf-8').write(found)
        print('saved non-JSON text', out, len(found))
