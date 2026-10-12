# Helper for in_x_9 card updates. Reads my own MCP results from my transcript.
import json, sys, copy, re
from urllib.parse import urlsplit, parse_qsl
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x9_work')
from tr import load_tr
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x9_work'
IN='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_x_9.json'
OUT='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_x_9.jsonl'
EXCL='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
ACCT='18ce55o46ul'
GET_ACTIONS=('GET_CARD','x_accounts_account_id_cards_card_id_get')
UPD_ACTIONS=('UPDATE_CARD','x_accounts_account_id_cards_card_id_put')

def units(): return json.load(open(IN, encoding='utf-8'))
def share(u): return json.load(open(f'{W}/share_summary.json'))['share'][u['unit']]

def x_calls(actions, card_id, dry=None):
    calls, results, order = load_tr()
    out=[]
    for t in order:
        name, inp = calls[t]
        if not (name or '').endswith('x_ads_native_action') or t not in results: continue
        inp=inp or {}
        if inp.get('action') not in actions: continue
        if (inp.get('path_params') or {}).get('card_id')!=card_id: continue
        if dry is not None and inp.get('dry_run') is not dry: continue
        out.append(t)
    return out, calls, results

def card_from_get(tid):
    calls, results, _ = load_tr()
    name, inp = calls[tid]
    assert inp.get('action') in GET_ACTIONS, inp
    d=json.loads(results[tid])
    assert d.get('success') is True and d['data'].get('success') is True, results[tid][:800]
    card=d['data']['data']['data']
    return inp, card, d

def eq(a,b):
    A=urlsplit(a); B=urlsplit(b)
    return (A.scheme,A.netloc,A.path,A.fragment)==(B.scheme,B.netloc,B.path,B.fragment) and sorted(parse_qsl(A.query,keep_blank_values=True))==sorted(parse_qsl(B.query,keep_blank_values=True))

def slot_path(slot):
    m=re.fullmatch(r'card\.components\[(\d+)\]\.destination\.url', slot)
    if m: return ('components', int(m.group(1)))
    m=re.fullmatch(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url', slot)
    if m: return ('slides', int(m.group(1)), int(m.group(2)))
    raise ValueError(slot)

def slot_get(card, slot):
    p=slot_path(slot)
    if p[0]=='components': return card['components'][p[1]]['destination']['url']
    return card['slides'][p[1]][p[2]]['destination']['url']

def slot_set(obj, slot, val):
    p=slot_path(slot)
    if p[0]=='components': obj['components'][p[1]]['destination']['url']=val
    else: obj['slides'][p[1]][p[2]]['destination']['url']=val

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
    c=copy.deepcopy(card); c.pop('updated_at', None)
    def blank(comp):
        if isinstance(comp, dict) and isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
            comp['destination']['url']='<URL>'
    for comp in c.get('components') or []: blank(comp)
    for s in c.get('slides') or []:
        for comp in s: blank(comp)
    return c

def all_urls(card):
    out={}
    for i,comp in enumerate(card.get('components') or []):
        if isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
            out[f'card.components[{i}].destination.url']=comp['destination']['url']
    for i,s in enumerate(card.get('slides') or []):
        for j,comp in enumerate(s):
            if isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
                out[f'card.slides[{i}][{j}].destination.url']=comp['destination']['url']
    return out

def excluded(u, ch):
    for e in json.load(open(EXCL)):
        if str(e.get('platform','')).lower() in ('x','twitter'):
            ids={e.get('ad_id'), e.get('unit'), e.get('card_id'), e.get('creative_id')}
            if (set(u['ad_ids'])|{u['unit'], u.get('creative_id'), share(u)['card_id']}) & ids and e.get('slot') in (None, ch['slot']):
                return True
    return False

KEYS=["platform","account_id","unit_type","unit","ad_ids","ad_names","slot","before","after_expected","after_live","result","new_entity_ids","detail"]
def write_line(rec):
    assert set(rec)==set(KEYS), set(rec)^set(KEYS)
    with open(OUT,'a',encoding='utf-8') as f:
        f.write(json.dumps({k:rec[k] for k in KEYS}, ensure_ascii=False)+'\n')

def base(u, ch):
    return {"platform":"x","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"after_expected":ch['new'],"new_entity_ids":""}

if __name__=='__main__':
    cmd=sys.argv[1]; idx=int(sys.argv[2]); u=units()[idx]; sh=share(u); cid=sh['card_id']
    if cmd=='prep':
        gets, calls, results = x_calls(GET_ACTIONS, cid)
        tid=gets[-1]
        inp, card, d = card_from_get(tid)
        assert card['id']==cid and card['card_uri']==sh['card_uri'], (card['id'], sh)
        assert (inp.get('path_params') or {}).get('account_id')==ACCT==u['account_id']
        print('unit', idx, u['unit'], 'card', card['id'], card['card_type'], 'created', card.get('created_at'), 'updated', card.get('updated_at'), '| deleted=', card.get('deleted'), '| keys=', sorted(card.keys()))
        print('  name=', repr(card['name']), '| share ok:', sh['ok'], sh['tweets_with_card'], '| GET tool', tid, 'req', d['meta']['requestId'])
        status={}; towrite=[]
        for ch in u['changes']:
            cur=slot_get(card, ch['slot'])
            if excluded(u, ch): st='EXCLUDED'
            elif not sh['ok']: st='SHARED'
            elif cur==ch['new'] or eq(cur, ch['new']): st='AlreadyFixed'
            elif cur==ch['now'] or cur in ch['alt_now'] or eq(cur, ch['now']) or any(eq(cur,a) for a in ch['alt_now']): st='WRITE'; towrite.append(ch)
            else: st='Skipped'
            status[ch['slot']]={'cur':cur,'st':st,'cur_eq_now_exact':cur==ch['now'],'cur_in_alt_exact':cur in ch['alt_now']}
            print(' ', ch['slot'], st, '| cur==now exact:', cur==ch['now'], '| cur in alt_now exact:', cur in ch['alt_now'])
            print('    cur:', cur)
        others={k:v for k,v in all_urls(card).items() if k not in [c['slot'] for c in u['changes']]}
        print('  other URL slots on card (left untouched):', others)
        json.dump({'card_before':card,'status':status,'get_tool':tid,'get_req':d['meta']['requestId']}, open(f'{W}/pre_{idx}.json','w'), ensure_ascii=False)
        if towrite:
            p=build_payload(card, towrite)
            json.dump(p, open(f'{W}/payload_{idx}.json','w'), ensure_ascii=False)
            print('PAYLOAD', json.dumps(p, ensure_ascii=False))
    elif cmd in ('checkdry','checklive'):
        dry = (cmd=='checkdry')
        ups, calls, results = x_calls(UPD_ACTIONS, cid, dry=dry)
        print('update calls (dry=%s) for card:'%dry, ups)
        tid=ups[-1]; name, inp = calls[tid]; txt=results[tid]
        exp=json.load(open(f'{W}/payload_{idx}.json'))
        pl=inp.get('payload'); sent=pl if isinstance(pl,(dict,list)) else json.loads(pl)
        print('tool', tid, 'action:', inp.get('action'), '| path_params:', inp.get('path_params'), '| dry_run:', inp.get('dry_run'), '| idem:', inp.get('idempotency_key'))
        print('sent==expected:', sent==exp, '| account ok:', (inp.get('path_params') or {}).get('account_id')==ACCT)
        try: d=json.loads(txt)
        except Exception: print('RAW RESULT', txt[:3000]); sys.exit(0)
        print('success:', d.get('success'), d.get('data',{}).get('success'), '| req', d.get('meta',{}).get('requestId'))
        if dry:
            req=d['data']['request']
            print('preview endpoint', d['data'].get('method'), d['data'].get('endpoint'), '| card_id', req.get('card_id'), '| account', req.get('account_id'))
            print('preview payload==expected:', req.get('payload')==exp)
            pre=json.load(open(f'{W}/pre_{idx}.json'))['card_before']
            prev=req.get('payload')
            # diff preview vs card as read (minus read-only)
            asread=build_payload(pre, [])
            diffs=[k for k in set(all_urls(prev))|set(all_urls(asread)) if all_urls(prev).get(k)!=all_urls(asread).get(k)]
            print('URL slots changed by preview:', diffs)
            print('non-URL parts identical to card as read:', comparable(prev)==comparable(asread))
        else:
            print('RESULT', txt[:4000])
    elif cmd=='verify':
        gets, calls, results = x_calls(GET_ACTIONS, cid)
        pre=json.load(open(f'{W}/pre_{idx}.json'))
        tid=gets[-1]
        assert tid!=pre['get_tool'], 'need a fresh GET after the write'
        inp, card, d = card_from_get(tid)
        print('re-read GET tool', tid, 'req', d['meta']['requestId'], 'updated_at', card.get('updated_at'))
        for ch in u['changes']:
            v=slot_get(card, ch['slot'])
            print(' ', ch['slot'], 'equals new byte for byte:', v==ch['new'])
            print('    live:', v)
        before=pre['card_before']
        others_before={k:v for k,v in all_urls(before).items() if k not in [c['slot'] for c in u['changes']]}
        others_after={k:v for k,v in all_urls(card).items() if k not in [c['slot'] for c in u['changes']]}
        print('  other URL slots unchanged:', others_before==others_after)
        print('  card otherwise identical (excl updated_at, URLs):', comparable(card)==comparable(before))
        if comparable(card)!=comparable(before):
            print('BEFORE', json.dumps(comparable(before), ensure_ascii=False)); print('AFTER ', json.dumps(comparable(card), ensure_ascii=False))
        json.dump({'card_after':card,'get_tool':tid,'get_req':d['meta']['requestId']}, open(f'{W}/post_{idx}.json','w'), ensure_ascii=False)
