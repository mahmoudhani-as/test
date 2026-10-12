import json,sys,unicodedata
from urllib.parse import urlsplit, parse_qsl
IN='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_snapchat_3.json'
OUT='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_snapchat_3.jsonl'
EXCL='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
units=json.load(open(IN))
def unit(uid): return [u for u in units if u['unit']==uid][0]
def same_url(a,b):
    A=urlsplit(a); B=urlsplit(b)
    return (A.scheme,A.netloc,A.path,A.fragment)==(B.scheme,B.netloc,B.path,B.fragment) and sorted(parse_qsl(A.query,keep_blank_values=True))==sorted(parse_qsl(B.query,keep_blank_values=True))
def classify(uid,cur):
    ch=unit(uid)['changes'][0]
    if cur==ch['new']: return 'NEW_EXACT'
    if same_url(cur,ch['new']): return 'NEW_SAMEPARAMS'
    if cur==ch['now']: return 'NOW'
    if cur in ch['alt_now']: return 'ALT'
    return 'OTHER'
def show_invisible(s):
    return ''.join(c if (c.isprintable() and unicodedata.category(c) not in ('Cf','Zs') ) or c==' ' else '\\u%04x'%ord(c) for c in s)
def excluded(u):
    e=json.load(open(EXCL))
    for x in e:
        if x['platform']=='snapchat' and (x['ad_id'] in u['ad_ids'] or x['ad_id']==u['unit']): return True
    return False
cmd=sys.argv[1]
if cmd=='classify':
    uid=sys.argv[2]; obj=json.load(open(sys.argv[3]))
    cur=obj['web_view_properties']['url']
    print('state',classify(uid,cur),'excluded',excluded(unit(uid)))
    for k in ('name','headline','brand_name'):
        if k in obj: print(k, repr(obj[k]), show_invisible(obj[k]))
elif cmd=='payload':
    uid=sys.argv[2]; obj=json.load(open(sys.argv[3]))
    ch=unit(uid)['changes'][0]
    obj['web_view_properties']['url']=ch['new']
    p={"creatives":[obj]}
    json.dump(p,open(sys.argv[4],'w'),ensure_ascii=False)
    print(json.dumps(p,ensure_ascii=False))
elif cmd=='record':
    uid,before,after_live,result,detail=sys.argv[2:7]
    newids=sys.argv[7] if len(sys.argv)>7 else ''
    u=unit(uid); ch=u['changes'][0]
    if result=='Fixed': assert after_live==ch['new'], 'readback mismatch'
    if result=='AlreadyFixed': assert same_url(before,ch['new'])
    rec={"platform":"snapchat","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":uid,"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":newids,"detail":detail}
    with open(OUT,'a') as f: f.write(json.dumps(rec,ensure_ascii=False)+'\n')
    print('recorded',uid,result,'before==now' if before==ch['now'] else ('before in alt' if before in ch['alt_now'] else ('before==new' if before==ch['new'] else 'before OTHER')))
if cmd=='compare':
    b=json.load(open(sys.argv[2])); a=json.load(open(sys.argv[3]))
    ign={'updated_at','review_status','review_status_details','semantic_id','packaging_status'}
    diffs=[]
    for k in sorted(set(b)|set(a)):
        if k in ign: continue
        if k=='web_view_properties':
            for kk in sorted(set(b[k])|set(a[k])):
                if kk=='url': continue
                if b[k].get(kk,'<absent>')!=a[k].get(kk,'<absent>'): diffs.append(('wvp.'+kk,b[k].get(kk,'<absent>'),a[k].get(kk,'<absent>')))
        elif b.get(k,'<absent>')!=a.get(k,'<absent>'): diffs.append((k,b.get(k,'<absent>'),a.get(k,'<absent>')))
    print('other-field diffs:',diffs if diffs else 'NONE')
    print('review_status', b.get('review_status'),'->',a.get('review_status'),'| semantic_id',b.get('semantic_id'),'->',a.get('semantic_id'),'| packaging',b.get('packaging_status'),'->',a.get('packaging_status'))
