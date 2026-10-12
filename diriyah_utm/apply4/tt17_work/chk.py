import json, sys
# usage: chk.py ad_id  -> compares the LAST dry-run preview body for that ad in this agent's transcript with payloads.json
T='/root/.claude/projects/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/subagents/workflows/wf_ffa6c8c2-c0c/agent-a391a4040f69bd6da.jsonl'
ad=sys.argv[1]; mode=sys.argv[2] if len(sys.argv)>2 else 'dry'
P=json.load(open('/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/tt17_work/payloads.json'))[ad]
def texts(o):
    if isinstance(o,dict):
        if o.get('type')=='tool_result':
            c=o.get('content')
            if isinstance(c,str): yield c
            elif isinstance(c,list):
                for x in c:
                    if isinstance(x,dict) and x.get('type')=='text': yield x['text']
        for v in o.values(): yield from texts(v)
    elif isinstance(o,list):
        for v in o: yield from texts(v)
found=None
for line in open(T):
    try: o=json.loads(line)
    except: continue
    for t in texts(o):
        if f'"ad_id": "{ad}"' in t and ('"dryRun": true' in t if mode=='dry' else '"dryRun": false' in t and 'ad/update' in t):
            found=t
assert found, 'no result found'
j=json.loads(found)
if mode=='dry':
    body=j['data']['data']['request']['body']
    exp=P
    def cmp(x,y,path=''):
        if isinstance(x,dict) and isinstance(y,dict):
            for k in set(x)|set(y): cmp(x.get(k),y.get(k),path+'.'+k)
        elif isinstance(x,list) and isinstance(y,list) and len(x)==len(y):
            for i,(a,b) in enumerate(zip(x,y)): cmp(a,b,path+f'[{i}]')
        elif x!=y: print('DIFF',path, ascii(x), '!=', ascii(y))
    cmp(exp,body)
    print('compared dry-run body vs built payload for',ad)
else:
    cr=j['data']['data']['data']['creatives'][0]
    print('live code',j['data']['data']['code'],'req',j['data']['data']['request_id'],'need_audit',j['data']['data']['data']['need_audit'],'lpu==payload',cr['landing_page_url']==P['creatives'][0]['landing_page_url'],'text==',cr['ad_text']==P['creatives'][0]['ad_text'], 'rstrip==', cr['ad_text']==P['creatives'][0]['ad_text'].rstrip(), 'mtime',cr['modify_time'],'vid',cr['video_id'])
