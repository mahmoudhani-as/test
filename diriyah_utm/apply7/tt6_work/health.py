# Scans every apply7 TikTok agent transcript (incl. mine) for the latest TikTok API outcomes (local only, no API calls).
import json, glob, re, sys
B='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
evs=[]
for d in ['wf_96598b86-20e','wf_a77bf62d-a6a','wf_e62cae8e-5aa']:
    for f in glob.glob(B+d+'/agent-*.jsonl'):
        uses={}
        for line in open(f,encoding='utf-8'):
            try: e=json.loads(line)
            except Exception: continue
            c=(e.get('message') or {}).get('content')
            if not isinstance(c,list): continue
            for x in c:
                if not isinstance(x,dict): continue
                if x.get('type')=='tool_use' and x.get('name','').endswith('tiktok_native_action'):
                    i=x.get('input') or {}; uses[x['id']]=(i.get('action'), i.get('dry_run'))
                if x.get('type')=='tool_result' and x.get('tool_use_id') in uses:
                    cc=x.get('content')
                    t=''.join(y.get('text','') for y in cc if isinstance(y,dict)) if isinstance(cc,list) else str(cc)
                    m=re.search(r'"request_id": "(\d{14})',t) or re.search(r'"tiktokRequestId": "(\d{14})',t)
                    code=re.search(r'"code": (\d+)',t)
                    ok=t.lstrip().startswith('{') and '"success": true' in t[:80]
                    a,dr=uses[x['tool_use_id']]
                    if a in ('LIST_ACTIONS','DESCRIBE_ACTION') or (a and dr is True and a.endswith('update')): continue
                    evs.append((m.group(1) if m else '?', f.split('/')[-1][6:14], a, ok, code.group(1) if code else ('timeout40s' if 'timed out after' in t else None)))
evs=[e for e in evs if e[0]!='?']
evs.sort()
for e in evs[-int(sys.argv[1]) if len(sys.argv)>1 else -15:]: print(e)
