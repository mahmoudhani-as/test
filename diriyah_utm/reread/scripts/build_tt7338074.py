import json, collections
from urllib.parse import urlsplit, parse_qsl
W="/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/reread/"
ACC="7338074303931449345"; ACCN="H&S - DGCL - Diriyah Gate"
inp=json.load(open(W+"in/tiktok_7338074303931449345.json"))
man=json.load(open(W+"work_tt7338074/manual_ads.json"))
sp=json.load(open(W+"work_tt7338074/smartplus_ads.json"))

def merge(base, pairs):
    """Render utm_params into base URL: append keys not already in the URL query (before any #fragment); keep URL value on conflicts."""
    notes=[]
    if not base: return None, notes
    if not pairs: return base, notes
    frag=''
    b=base
    if '#' in b: b,frag=b.split('#',1); frag='#'+frag
    q=urlsplit(b).query
    ex=collections.defaultdict(list)
    for k,v in parse_qsl(q, keep_blank_values=True): ex[k].append(v)
    add=[]; conf=[]
    for p in pairs:
        k=p.get('key'); v=p.get('value')
        if k is None: continue
        if k in ex:
            if v not in ex[k]: conf.append(f"{k}: landing_page_url has {ex[k][0]!r} but utm_params has {v!r} (url keeps landing_page_url value)")
            continue
        add.append(f"{k}={v}" if v is not None else k)
    url=b
    if add:
        url=b+('&' if '?' in b else '?')+'&'.join(add)
        notes.append("utm_params keys not in landing_page_url appended: "+", ".join(add))
    url+=frag
    if conf: notes.append("CONFLICT "+"; ".join(conf))
    if not add and not conf: notes.append("utm_params identical to query already in landing_page_url")
    return url, notes

out=[]; errs=[]
for r in inp:
    aid=r['ad_id']; slot=r['slot']
    rec=dict(platform="tiktok",account_id=ACC,ad_id=aid,slot=slot,url=None,status_now=None,creative_id_now=None,found=False,note="")
    notes=[]
    if slot=="ad.landing_page_url":
        a=man.get(aid)
        if not a:
            rec['note']="ad not returned by /v1.3/ad/get/ with primary_status STATUS_ALL (ad no longer exists)"; out.append(rec); continue
        sec=a.get('secondary_status'); op=a.get('operation_status')
        rec['status_now']=sec
        base=a.get('landing_page_url') or None
        url,mn=merge(base,a.get('utm_params'))
        rec['url']=url
        deleted = sec=='AD_STATUS_DELETE'
        rec['found']=not deleted
        notes.append(f"Manual ad read via /v1.3/ad/get/ (ad_format {a.get('ad_format')}); operation_status {op}")
        if deleted: notes.append("ad DELETED (secondary_status AD_STATUS_DELETE); url is the last stored value")
        if base is None:
            notes.append("landing_page_url empty; no landing_page_urls/deeplink/page_id set (no destination URL on this ad)")
            if a.get('utm_params'): notes.append("utm_params set but no landing_page_url")
        else:
            notes+=mn
    elif slot.startswith("smart_plus_ad.landing_page_url_list["):
        idx=int(slot.split('[',1)[1].split(']',1)[0])
        a=sp.get(aid)
        if not a:
            rec['note']="Smart+ ad not returned by /v1.3/smart_plus/ad/get/ with primary_status STATUS_ALL (ad no longer exists)"; out.append(rec); continue
        sec=a.get('secondary_status'); op=a.get('operation_status')
        rec['status_now']=sec
        deleted = sec=='AD_STATUS_DELETE'
        rec['found']=not deleted
        lpl=a.get('landing_page_url_list') or []
        pairs=(a.get('ad_configuration') or {}).get('utm_params')
        notes.append(f"Upgraded Smart+ ad read via /v1.3/smart_plus/ad/get/; operation_status {op}; landing_page_url_list has {len(lpl)} entr{'y' if len(lpl)==1 else 'ies'}")
        if deleted: notes.append("ad DELETED (secondary_status AD_STATUS_DELETE); url is the last stored value")
        if idx < len(lpl):
            base=lpl[idx].get('landing_page_url') or None
            url,mn=merge(base,pairs)
            rec['url']=url; notes+=mn
            if not pairs: notes.append("no ad_configuration.utm_params set")
        else:
            notes.append(f"landing_page_url_list[{idx}] no longer present")
    else:
        errs.append(f"unknown slot {slot} for {aid}")
    if r['status_11oct'] and rec['status_now'] and r['status_11oct']!=rec['status_now']:
        notes.append(f"status changed since 11-Oct ({r['status_11oct']} -> {rec['status_now']})")
    if rec['url']!=r['url_11oct']:
        notes.append("URL differs from 11-Oct value")
    rec['note']="; ".join(notes)
    out.append(rec)

with open(W+"out/tiktok_7338074303931449345.jsonl","w") as f:
    for rec in out: f.write(json.dumps(rec,ensure_ascii=False)+"\n")

# Task 2: new ads (not in input, not deleted)
inids={r['ad_id'] for r in inp}
new=[]
for aid,a in sorted(man.items(), key=lambda kv:(kv[1]['create_time'],kv[0])):
    if aid in inids or a.get('secondary_status')=='AD_STATUS_DELETE': continue
    url,_=merge(a.get('landing_page_url') or None, a.get('utm_params'))
    new.append(dict(platform="tiktok",account_id=ACC,account_name=ACCN,campaign_name=a.get('campaign_name'),adset_name=a.get('adgroup_name'),
        ad_id=aid,ad_name=a.get('ad_name'),effective_status=a.get('secondary_status'),slot="ad.landing_page_url",url=url))
for aid,a in sp.items():
    if aid in inids or a.get('secondary_status')=='AD_STATUS_DELETE': continue
    pairs=(a.get('ad_configuration') or {}).get('utm_params')
    for i,lp in enumerate(a.get('landing_page_url_list') or []):
        url,_=merge(lp.get('landing_page_url') or None, pairs)
        new.append(dict(platform="tiktok",account_id=ACC,account_name=ACCN,campaign_name=a.get('campaign_name'),adset_name=a.get('adgroup_name'),
            ad_id=aid,ad_name=a.get('ad_name'),effective_status=a.get('secondary_status'),slot=f"smart_plus_ad.landing_page_url_list[{i}].landing_page_url",url=url))
with open(W+"out/new_tiktok_7338074303931449345.jsonl","w") as f:
    for rec in new: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
print("rows",len(out),"found",sum(r['found'] for r in out),"not_found",sum(not r['found'] for r in out),"new",len(new),"errs",errs)
