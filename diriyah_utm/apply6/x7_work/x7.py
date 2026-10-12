# Helper for in_x_7 card updates. Reads my own MCP results from my transcript.
import json, sys, copy, re
from urllib.parse import urlsplit, parse_qsl
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x7_work')
from tr import load_tr
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x7_work'
IN='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_x_7.json'
OUT='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_x_7.jsonl'
EXCL='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
ACCT='18ce55o46ul'

def units(): return json.load(open(IN, encoding='utf-8'))

def resp(tid):
    calls, results, _ = load_tr()
    name, inp = calls[tid]
    return name, inp, results[tid]

def card_from(tid):
    name, inp, txt = resp(tid)
    assert name.endswith('x_ads_native_action') and inp.get('action') in ('GET_CARD','x_accounts_account_id_cards_card_id_get'), (name, inp)
    d=json.loads(txt)
    assert d.get('success') is True, txt[:500]
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
def strip(comp):
    return {k:v for k,v in comp.items() if k not in READONLY_COMP}

def build_payload(card, changes):
    p={'name': card['name']}
    if card.get('components') is not None:
        p['components']=[strip(copy.deepcopy(c)) for c in card['components']]
    if card.get('slides') is not None:
        p['slides']=[[strip(copy.deepcopy(c)) for c in s] for s in card['slides']]
    if 'experiment_signals' in card:
        p['experiment_signals']=copy.deepcopy(card['experiment_signals'])
    for ch in changes:
        slot_set(p, ch['slot'], ch['new'])
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
    ex=json.load(open(EXCL))
    for e in ex:
        if str(e.get('platform','')).lower() in ('x','twitter'):
            ids={e.get('ad_id'), e.get('unit'), e.get('card_id'), e.get('creative_id')}
            if (set(u['ad_ids'])|{u['unit'], u.get('creative_id')}) & ids and e.get('slot') in (None, ch['slot']):
                return True
    return False

def write_line(rec):
    keys=["platform","account_id","unit_type","unit","ad_ids","ad_names","slot","before","after_expected","after_live","result","new_entity_ids","detail"]
    assert set(rec)==set(keys), set(rec)^set(keys)
    with open(OUT,'a',encoding='utf-8') as f:
        f.write(json.dumps({k:rec[k] for k in keys}, ensure_ascii=False)+'\n')

def base(u, ch):
    return {"platform":"x","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"after_expected":ch['new'],"new_entity_ids":""}

cmd=sys.argv[1]
if cmd=='prep':
    idx=int(sys.argv[2]); tid=sys.argv[3]
    u=units()[idx]
    share=json.load(open(f'{W}/share_summary.json'))[u['unit']]
    if tid=='auto':
        calls, results, order = load_tr()
        cands=[t for t in order if (calls[t][0] or '').endswith('x_ads_native_action') and calls[t][1].get('action')=='GET_CARD' and (calls[t][1].get('path_params') or {}).get('card_id')==share['card_id'] and t in results]
        tid=cands[-1]; print('using GET', tid, 'of', len(cands))
    inp, card, d = card_from(tid)
    assert inp['path_params']['card_id']==share['card_id']==card['id'], (inp, share, card['id'])
    assert (inp.get('path_params') or {}).get('account_id')==ACCT==u['account_id']
    print('unit', idx, u['unit'], 'card', card['id'], card['card_type'], '| name=', repr(card['name']), '| deleted=', card.get('deleted'), '| keys=', sorted(card.keys()))
    print('  share ok:', share['ok'], share['tweets_with_card'])
    status={}; towrite=[]
    for ch in u['changes']:
        cur=slot_get(card, ch['slot'])
        if excluded(u, ch): st='EXCLUDED'
        elif not share['ok']: st='SHARED'
        elif cur==ch['new'] or eq(cur, ch['new']): st='AlreadyFixed'
        elif cur==ch['now'] or cur in ch['alt_now'] or eq(cur, ch['now']) or any(eq(cur,a) for a in ch['alt_now']): st='WRITE'; towrite.append(ch)
        else: st='Skipped'
        status[ch['slot']]={'cur':cur,'st':st,'cur_eq_now_exact':cur==ch['now'],'cur_in_alt_exact':cur in ch['alt_now']}
        print(' ', ch['slot'], st, '| cur==now exact:', cur==ch['now'], '| cur in alt_now exact:', cur in ch['alt_now'])
        print('    cur:', cur)
    other_urls={k:v for k,v in all_urls(card).items() if k not in [c['slot'] for c in u['changes']]}
    print('  other URL slots on card (left untouched):', other_urls)
    json.dump({'card_before':card,'status':status,'get_tool':tid,'get_req':d.get('meta',{}).get('requestId')}, open(f'{W}/pre_{idx}.json','w'), ensure_ascii=False)
    if towrite:
        p=build_payload(card, towrite)
        json.dump(p, open(f'{W}/payload_{idx}.json','w'), ensure_ascii=False)
        print('PAYLOAD', json.dumps(p, ensure_ascii=False))
        print('PAYLOAD_ASCII', json.dumps(p, ensure_ascii=True))
        nonascii=[ch for ch in json.dumps(p, ensure_ascii=False) if ord(ch)>127 and not ('؀'<=ch<='ۿ')]
        print('  non-ascii non-arabic chars in payload:', [hex(ord(c)) for c in nonascii])
elif cmd=='checkdry' or cmd=='checklive':
    idx=int(sys.argv[2]); tid=sys.argv[3]
    name, inp, txt = resp(tid)
    exp=json.load(open(f'{W}/payload_{idx}.json'))
    pre=json.load(open(f'{W}/pre_{idx}.json'))
    pl=inp.get('payload')
    sent=pl if isinstance(pl,(dict,list)) else json.loads(pl)
    print('action:', inp.get('action'), '| path_params:', inp.get('path_params'), '| dry_run:', inp.get('dry_run'))
    print('sent==expected:', sent==exp)
    if sent!=exp:
        print('SENT', json.dumps(sent, ensure_ascii=False)); print('EXP ', json.dumps(exp, ensure_ascii=False))
    print('path card_id ok:', (inp.get('path_params') or {}).get('card_id')==pre['card_before']['id'], '| account ok:', (inp.get('path_params') or {}).get('account_id')==ACCT)
    print('RESPONSE:', txt[:3000])
elif cmd=='verify':
    # verify <idx> <get_after_tool_id> <live_write_tool_id> <dry_tool_id>
    idx=int(sys.argv[2]); tid=sys.argv[3]; wtid=sys.argv[4]; dtid=sys.argv[5]
    u=units()[idx]
    pre=json.load(open(f'{W}/pre_{idx}.json'))
    before=pre['card_before']
    inp, after, d = card_from(tid)
    assert after['id']==before['id']
    same_rest = comparable(before)==comparable(after)
    print('non-URL fields unchanged:', same_rest)
    if not same_rest:
        a=comparable(before); b=comparable(after)
        for k in sorted(set(a)|set(b)):
            if a.get(k)!=b.get(k): print('  DIFF', k, json.dumps(a.get(k), ensure_ascii=False)[:400], '=>', json.dumps(b.get(k), ensure_ascii=False)[:400])
    changed_slots=[c['slot'] for c in u['changes']]
    bu=all_urls(before); au=all_urls(after)
    others_same=all(bu[k]==au.get(k) for k in bu if k not in changed_slots) and set(bu)==set(au)
    print('other URL slots unchanged:', others_same)
    _,winp,wtxt=resp(wtid); _,dinp,dtxt=resp(dtid)
    wd=json.loads(wtxt); dd=json.loads(dtxt)
    wreq=wd.get('meta',{}).get('requestId'); dreq=dd.get('meta',{}).get('requestId')
    lines=[]
    for ch in u['changes']:
        st=pre['status'][ch['slot']]
        if st['st']!='WRITE':
            print('not a write slot', ch['slot'], st['st']); continue
        live=slot_get(after, ch['slot'])
        ok = live==ch['new']
        res='Fixed' if (ok and same_rest and others_same) else ('Fixed' if ok else 'Failed')
        print(ch['slot'], 'read-back==new byte for byte:', ok, '->', res)
        lines.append((ch, st['cur'], live, res))
    json.dump({'after':after,'lines':[(c['slot'],b,l,r) for c,b,l,r in lines],'wtid':wtid,'dtid':dtid,'wreq':wreq,'dreq':dreq,'get_after_req':d.get('meta',{}).get('requestId'),'same_rest':same_rest,'others_same':others_same}, open(f'{W}/post_{idx}.json','w'), ensure_ascii=False)
elif cmd=='record':
    # record <idx> <detail-json-file-or-string>
    idx=int(sys.argv[2]); extra=sys.argv[3] if len(sys.argv)>3 else ''
    u=units()[idx]
    post=json.load(open(f'{W}/post_{idx}.json'))
    for (slot,b,l,r) in post['lines']:
        ch=[c for c in u['changes'] if c['slot']==slot][0]
        rec=base(u,ch); rec.update({'before':b,'after_live':l,'result':r,'detail':extra})
        write_line(rec); print('WROTE', slot, r)
elif cmd=='record_nowrite':
    # record_nowrite <idx> <result> <detail>  (for AlreadyFixed / Skipped / NotAttempted / Failed without write)
    idx=int(sys.argv[2]); result=sys.argv[3]; detail=sys.argv[4]
    u=units()[idx]
    pre=None
    try: pre=json.load(open(f'{W}/pre_{idx}.json'))
    except Exception: pass
    for ch in u['changes']:
        cur = pre['status'][ch['slot']]['cur'] if pre else ''
        rec=base(u,ch); rec.update({'before':cur,'after_live':cur,'result':result,'detail':detail})
        write_line(rec); print('WROTE', ch['slot'], result)
