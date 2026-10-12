# Helper for in_x_3 card updates. Reads my own MCP results from my transcript (via tr.py logic).
import json, sys, copy, re
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x3_work'
IN='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_x_3.json'
OUT='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_x_3.jsonl'
EXCL='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_ab8422cb-21a/agent-a6497fc413eadd5b3.jsonl'

def load_tr():
    calls={}; results={}; order=[]
    for line in open(T):
        try: e=json.loads(line)
        except Exception: continue
        msg=e.get('message') or {}
        content=msg.get('content')
        if not isinstance(content, list): continue
        for c in content:
            if not isinstance(c, dict): continue
            if c.get('type')=='tool_use':
                calls[c['id']]=(c.get('name'), c.get('input')); order.append(c['id'])
            elif c.get('type')=='tool_result':
                rc=c.get('content')
                txt=''.join(x.get('text','') for x in rc if isinstance(x, dict) and x.get('type')=='text') if isinstance(rc, list) else (rc if isinstance(rc,str) else json.dumps(rc))
                results[c['tool_use_id']]=txt
    return calls, results, order

def card_from(tid):
    calls, results, _ = load_tr()
    name, inp = calls[tid]
    d=json.loads(results[tid])
    assert d.get('success') is True, results[tid][:500]
    card=d['data']['data']['data']
    return inp, card

def eq(a,b):
    A=urlsplit(a); B=urlsplit(b)
    return (A.scheme,A.netloc,A.path,A.fragment)==(B.scheme,B.netloc,B.path,B.fragment) and sorted(parse_qsl(A.query,keep_blank_values=True))==sorted(parse_qsl(B.query,keep_blank_values=True))

def slot_get(card, slot):
    m=re.fullmatch(r'card\.components\[(\d+)\]\.destination\.url', slot)
    if m: return card['components'][int(m.group(1))]['destination']['url']
    m=re.fullmatch(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url', slot)
    if m: return card['slides'][int(m.group(1))][int(m.group(2))]['destination']['url']
    raise ValueError(slot)

def slot_set(obj, slot, val):
    m=re.fullmatch(r'card\.components\[(\d+)\]\.destination\.url', slot)
    if m: obj['components'][int(m.group(1))]['destination']['url']=val; return
    m=re.fullmatch(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url', slot)
    if m: obj['slides'][int(m.group(1))][int(m.group(2))]['destination']['url']=val; return
    raise ValueError(slot)

READONLY_COMP={'media_metadata'}
def strip(comp):
    return {k:v for k,v in comp.items() if k not in READONLY_COMP}

def build_payload(card, changes):
    p={'name': card['name']}
    if 'components' in card and card['components'] is not None:
        p['components']=[strip(copy.deepcopy(c)) for c in card['components']]
    if 'slides' in card and card['slides'] is not None:
        p['slides']=[[strip(copy.deepcopy(c)) for c in s] for s in card['slides']]
    if 'experiment_signals' in card:
        p['experiment_signals']=copy.deepcopy(card['experiment_signals'])
    for ch in changes:
        slot_set(p, ch['slot'], ch['new'])
    return p

def comparable(card):
    # everything except destination urls and volatile fields
    c=copy.deepcopy(card)
    for k in ['updated_at']:
        c.pop(k, None)
    def blank(comp):
        if isinstance(comp, dict) and isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
            comp['destination']['url']='<URL>'
    for comp in c.get('components') or []: blank(comp)
    for s in c.get('slides') or []:
        for comp in s: blank(comp)
    return c

def units(): return json.load(open(IN))

def excluded(u, ch):
    ex=json.load(open(EXCL))
    for e in ex:
        if str(e.get('platform','')).lower() in ('x','twitter'):
            ids=set([e.get('ad_id'), e.get('unit'), e.get('card_id')])
            if (set(u['ad_ids'])|{u['unit']}) & ids and e.get('slot') in (None, ch['slot']):
                return True
    return False

cmd=sys.argv[1]
if cmd=='prep':
    idx=int(sys.argv[2]); tid=sys.argv[3]
    u=units()[idx]
    inp, card=card_from(tid)
    print('card', card['id'], card['card_type'], 'name=', card['name'], 'deleted=', card.get('deleted'), 'top keys=', sorted(card.keys()))
    status={}
    towrite=[]
    for ch in u['changes']:
        cur=slot_get(card, ch['slot'])
        if excluded(u, ch): st='EXCLUDED'
        elif cur==ch['new'] or eq(cur, ch['new']): st='AlreadyFixed'
        elif cur==ch['now'] or cur in ch['alt_now'] or eq(cur, ch['now']) or any(eq(cur,a) for a in ch['alt_now']): st='WRITE'; towrite.append(ch)
        else: st='Skipped'
        status[ch['slot']]={'cur':cur,'st':st}
        print(ch['slot'], st, 'cur==now exact:', cur==ch['now'])
    json.dump({'card_before':card,'status':status,'get_tool':tid}, open(f'{W}/pre_{idx}.json','w'), ensure_ascii=False)
    if towrite:
        p=build_payload(card, towrite)
        json.dump(p, open(f'{W}/payload_{idx}.json','w'), ensure_ascii=False)
        print('PAYLOAD', json.dumps(p, ensure_ascii=False))
elif cmd=='checkdry':
    idx=int(sys.argv[2]); tid=sys.argv[3]
    calls, results, _=load_tr()
    name, inp=calls[tid]
    exp=json.load(open(f'{W}/payload_{idx}.json'))
    sent=inp['payload'] if isinstance(inp['payload'], dict) else json.loads(inp['payload'])
    print('sent==expected:', sent==exp)
    d=json.loads(results[tid])
    echo=d['data']['request']['payload']
    print('dry_run flag:', inp.get('dry_run'), '| echo dry_run:', d['data'].get('dry_run'))
    print('echoed payload==expected:', echo==exp)
    print('path card_id:', d['data']['request'].get('card_id'), 'account:', d['data']['request'].get('account_id'))
    pre=json.load(open(f'{W}/pre_{idx}.json'))
    print('card id matches:', d['data']['request'].get('card_id')==pre['card_before']['id'])
elif cmd=='checklive':
    idx=int(sys.argv[2]); tid=sys.argv[3]
    calls, results, _=load_tr()
    name, inp=calls[tid]
    exp=json.load(open(f'{W}/payload_{idx}.json'))
    sent=inp['payload'] if isinstance(inp['payload'], dict) else json.loads(inp['payload'])
    print('sent==expected:', sent==exp, '| dry_run:', inp.get('dry_run'))
    print(results[tid][:300].replace('\n',' '))
elif cmd=='verify':
    # verify <idx> <get_after_tool_id> <write_tool_id|-> [extra detail]
    idx=int(sys.argv[2]); tid=sys.argv[3]; wtid=sys.argv[4]; extra=sys.argv[5] if len(sys.argv)>5 else ''
    u=units()[idx]
    pre=json.load(open(f'{W}/pre_{idx}.json'))
    before_card=pre['card_before']
    inp, after=card_from(tid)
    same_rest = comparable(before_card)==comparable(after)
    print('non-URL fields unchanged:', same_rest)
    if not same_rest:
        a=comparable(before_card); b=comparable(after)
        for k in set(a)|set(b):
            if a.get(k)!=b.get(k): print('  DIFF', k, json.dumps(a.get(k), ensure_ascii=False)[:300], '=>', json.dumps(b.get(k), ensure_ascii=False)[:300])
    # also check other slots (not in changes) unchanged
    ok_all=True
    lines=[]
    for ch in u['changes']:
        st=pre['status'][ch['slot']]['st']; cur=pre['status'][ch['slot']]['cur']
        al=slot_get(after, ch['slot'])
        if st=='WRITE':
            res='Fixed' if (al==ch['new'] and same_rest) else 'Failed'
        else:
            res=st
        print(ch['slot'], st, '->', res, '| after==new:', al==ch['new'])
        lines.append((ch, cur, al, res))
    json.dump({'after':after,'lines':[(c['slot'],cur,al,res) for c,cur,al,res in lines],'extra':extra,'wtid':wtid}, open(f'{W}/post_{idx}.json','w'), ensure_ascii=False)

if cmd=='record':
    # record <idx> <detail_prefix_for_written> [detail_for_not_written]
    idx=int(sys.argv[2]); dw=sys.argv[3]; dn=sys.argv[4] if len(sys.argv)>4 else ''
    u=units()[idx]
    post=json.load(open(f'{W}/post_{idx}.json'))
    # avoid duplicate lines
    done=set()
    try:
        for l in open(OUT):
            r=json.loads(l); done.add((r['unit'], r['slot']))
    except FileNotFoundError: pass
    n=0
    with open(OUT,'a') as f:
        for slot,cur,al,res in post['lines']:
            if (u['unit'], slot) in done: print('dup skip', slot); continue
            ch=[c for c in u['changes'] if c['slot']==slot][0]
            if res=='Fixed':
                assert al==ch['new']
                detail=dw.replace('{SLOT}', slot)
            elif res=='AlreadyFixed':
                detail=(dn or 'slot already equals new; no write').replace('{SLOT}', slot)
            elif res=='Skipped':
                detail=('changed since plan: '+cur) + ((' ; '+dn) if dn else '')
            else:
                detail=dw.replace('{SLOT}', slot) + ' ; READ-BACK MISMATCH'
            rec={"platform":"x","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],
                 "ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":slot,"before":cur,"after_expected":ch['new'],
                 "after_live":al,"result":res,"new_entity_ids":"","detail":detail}
            f.write(json.dumps(rec, ensure_ascii=False)+'\n'); n+=1
    print('recorded', n)

def latest(action, card_id, dry=None, after_id=None):
    calls, results, order = load_tr()
    found=None
    start = order.index(after_id)+1 if after_id else 0
    for i in order[start:]:
        nm, inp = calls[i]
        if not isinstance(inp, dict) or 'x_ads' not in (nm or ''): continue
        if inp.get('action')!=action: continue
        pp=inp.get('path_params') or {}
        if str(pp.get('card_id'))!=str(card_id): continue
        if dry is not None and bool(inp.get('dry_run'))!=dry: continue
        if i not in results: continue
        found=i
    return found

if cmd=='auto':
    # auto <stage> <idx> <card_id>   stage in prep|dry|live|verify
    stage=sys.argv[2]; idx=int(sys.argv[3]); cid=sys.argv[4]
    if stage=='prep':
        tid=latest('GET_CARD', cid); print('using', tid)
        sys.argv=['card.py','prep',str(idx),tid]
    elif stage=='dry':
        tid=latest('UPDATE_CARD', cid, dry=True); print('using', tid)
        sys.argv=['card.py','checkdry',str(idx),tid]
    elif stage=='live':
        tid=latest('UPDATE_CARD', cid, dry=False); print('using', tid)
        sys.argv=['card.py','checklive',str(idx),tid]
    elif stage=='verify':
        wt=latest('UPDATE_CARD', cid, dry=False)
        tid=latest('GET_CARD', cid, after_id=wt); print('using write', wt, 'read-back', tid)
        assert tid, 'no read-back after write'
        sys.argv=['card.py','verify',str(idx),tid,wt]
    import subprocess
    r=subprocess.run(['python3', __file__]+sys.argv[1:], capture_output=True, text=True)
    print(r.stdout, r.stderr)
