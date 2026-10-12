# Helper for in_x_6 card URL updates. Reads my own MCP calls/results from my transcript.
import json, sys, copy, re
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x6_work'
IN='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_x_6.json'
OUT='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_x_6.jsonl'
EXCL='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
exec(open(W+'/tr.py').read().split("if __name__")[0])
ACCT='18ce55o46ul'

def units(): return json.load(open(IN))
def share(): return json.load(open(W+'/share_summary.json'))

def card_from(tid):
    calls, order, results = load()
    name, inp = calls[tid]
    assert name.endswith('x_ads_native_action') and inp['action']=='GET_CARD', (name, inp)
    d=json.loads(results[tid])
    assert d.get('success') is True and d['data'].get('success') is True, results[tid][:800]
    card=d['data']['data']['data']
    return inp, card, d.get('meta',{}).get('requestId')

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
def strip(comp): return {k:v for k,v in comp.items() if k not in READONLY_COMP}

def build_payload(card, changes):
    p={'name': card['name']}
    if card.get('components') is not None:
        p['components']=[strip(copy.deepcopy(c)) for c in card['components']]
    if card.get('slides') is not None:
        p['slides']=[[strip(copy.deepcopy(c)) for c in s] for s in card['slides']]
    if 'experiment_signals' in card:
        p['experiment_signals']=copy.deepcopy(card['experiment_signals'])
    for ch in changes: slot_set(p, ch['slot'], ch['new'])
    return p

def comparable(card):
    c=copy.deepcopy(card)
    c.pop('updated_at', None)
    def blank(comp):
        if isinstance(comp, dict) and isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
            comp['destination']['url']='<URL>'
    for comp in c.get('components') or []: blank(comp)
    for s in c.get('slides') or []:
        for comp in s: blank(comp)
    return c

def excluded(u, ch):
    for e in json.load(open(EXCL)):
        if str(e.get('platform','')).lower() in ('x','twitter'):
            ids={e.get('ad_id'), e.get('unit'), e.get('card_id')}
            if (set(u['ad_ids'])|{u['unit'], u.get('creative_id')}) & ids and e.get('slot') in (None, ch['slot']):
                return True
    return False

cmd=sys.argv[1]
if cmd=='prep':
    idx=int(sys.argv[2]); tid=sys.argv[3]
    u=units()[idx]; sh=share()[u['unit']]
    inp, card, rid=card_from(tid)
    assert inp['path_params']['card_id']==sh['card_id']==card['id'], (inp, sh, card['id'])
    assert inp['path_params']['account_id']==ACCT==u['account_id']
    assert sh['tweets_with_card']==[u['unit']]
    print('card', card['id'], card['card_type'], '| deleted=', card.get('deleted'), '| exp_signals=', card.get('experiment_signals'), '| keys=', sorted(card.keys()), '| reqid', rid)
    status={}; towrite=[]
    for ch in u['changes']:
        cur=slot_get(card, ch['slot'])
        if excluded(u, ch): st='EXCLUDED'
        elif cur==ch['new'] or eq(cur, ch['new']): st='AlreadyFixed'
        elif cur==ch['now'] or cur in ch.get('alt_now',[]): st='WRITE'; towrite.append(ch)
        else: st='Skipped'
        status[ch['slot']]={'cur':cur,'st':st, 'cur_is':('now' if cur==ch['now'] else ('alt_now' if cur in ch.get('alt_now',[]) else ('new' if cur==ch['new'] else 'other')))}
        print(ch['slot'], st, '| cur is', status[ch['slot']]['cur_is'])
    json.dump({'card_before':card,'status':status,'get_tool':tid,'get_reqid':rid}, open(f'{W}/pre_{idx}.json','w'), ensure_ascii=False)
    if towrite:
        p=build_payload(card, towrite)
        json.dump(p, open(f'{W}/payload_{idx}.json','w'), ensure_ascii=False)
        print('PAYLOAD_ASCII', json.dumps(p, ensure_ascii=True, separators=(',',':')))
elif cmd in ('checkdry','checklive'):
    idx=int(sys.argv[2]); tid=sys.argv[3]
    calls, order, results=load()
    name, inp=calls[tid]
    exp=json.load(open(f'{W}/payload_{idx}.json'))
    pre=json.load(open(f'{W}/pre_{idx}.json'))
    sent=inp['payload'] if isinstance(inp['payload'], dict) else json.loads(inp['payload'])
    print('action:', inp['action'], '| path_params:', inp.get('path_params'), '| dry_run:', inp.get('dry_run'))
    assert inp['action']=='UPDATE_CARD'
    assert inp['path_params']=={'account_id':ACCT,'card_id':pre['card_before']['id']}, inp['path_params']
    print('sent==expected (exact, incl. title codepoints):', sent==exp)
    if sent!=exp:
        print('SENT', json.dumps(sent, ensure_ascii=True)); print('EXP ', json.dumps(exp, ensure_ascii=True))
    d=json.loads(results[tid])
    print('result success:', d.get('success'), '| reqid', d.get('meta',{}).get('requestId'))
    if cmd=='checkdry':
        assert inp.get('dry_run') is True
        echo=d['data']['request']['payload']
        print('echo dry_run:', d['data'].get('dry_run'), '| echoed payload==expected:', echo==exp, '| echoed card_id:', d['data']['request'].get('card_id'), '| acct:', d['data']['request'].get('account_id'))
        # diff vs card as read: only the URL(s) should differ
        before=build_payload(pre['card_before'], [])
        diffs=[]
        def walk(a,b,path=''):
            if isinstance(a,dict) and isinstance(b,dict):
                for k in set(a)|set(b): walk(a.get(k,'<MISSING>'), b.get(k,'<MISSING>'), path+'.'+k)
            elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
                for i,(x,y) in enumerate(zip(a,b)): walk(x,y,path+f'[{i}]')
            elif a!=b: diffs.append((path,a,b))
        walk(before, echo)
        print('preview diff vs card as read:', json.dumps(diffs, ensure_ascii=True))
    else:
        assert inp.get('dry_run') is False
        print(results[tid][:600].replace('\n',' '))
elif cmd=='verify':
    idx=int(sys.argv[2]); tid=sys.argv[3]
    u=units()[idx]
    pre=json.load(open(f'{W}/pre_{idx}.json'))
    before_card=pre['card_before']
    inp, after, rid=card_from(tid)
    assert after['id']==before_card['id']
    same_rest = comparable(before_card)==comparable(after)
    print('reqid', rid, '| non-URL fields unchanged (excl updated_at):', same_rest, '| updated_at before/after:', before_card.get('updated_at'), after.get('updated_at'))
    if not same_rest:
        a=comparable(before_card); b=comparable(after)
        for k in set(a)|set(b):
            if a.get(k)!=b.get(k): print('  DIFF', k, json.dumps(a.get(k), ensure_ascii=True)[:400], '=>', json.dumps(b.get(k), ensure_ascii=True)[:400])
    lines=[]
    for ch in u['changes']:
        st=pre['status'][ch['slot']]['st']; cur=pre['status'][ch['slot']]['cur']
        al=slot_get(after, ch['slot'])
        if st=='WRITE': res='Fixed' if (al==ch['new']) else 'Failed'
        else: res=st
        print(ch['slot'], st, '->', res, '| after==new byte-for-byte:', al==ch['new'])
        lines.append((ch['slot'],cur,al,res))
    json.dump({'after':after,'lines':lines,'reqid':rid,'same_rest':same_rest}, open(f'{W}/post_{idx}.json','w'), ensure_ascii=False)
elif cmd=='record':
    # record <idx> <detail>   (uses post_<idx>.json; detail may contain {SLOT})
    idx=int(sys.argv[2]); detail_t=sys.argv[3]
    u=units()[idx]
    post=json.load(open(f'{W}/post_{idx}.json'))
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
            if res=='Fixed': assert al==ch['new']
            detail=detail_t.replace('{SLOT}', slot)
            if res=='Skipped': detail='changed since plan: '+cur+' ; '+detail
            rec={"platform":"x","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],
                 "ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":slot,"before":cur,"after_expected":ch['new'],
                 "after_live":al,"result":res,"new_entity_ids":"","detail":detail}
            f.write(json.dumps(rec, ensure_ascii=False)+'\n'); n+=1
    print('recorded', n)
