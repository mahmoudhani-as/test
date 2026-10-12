import json, collections
from urllib.parse import urlsplit, parse_qsl
ACC="7338057963233443842"; ACCN="H&S - DGCL - Visit Diriyah"
OUT="/tmp/claude-0/-home-user-test/c5fcace8-62b1-55a4-9129-dbfe4d94e847/scratchpad/live/tiktok_7338057963233443842.jsonl"
camps={}
for l in open('campaigns.tsv'):
    i,n,op,sec,typ=l.rstrip('\n').split('\t'); camps[i]=dict(name=n,op=op,sec=sec,type=typ)
OPM={'E':'ENABLE','D':'DISABLE'}; SECM={'TD':'ADGROUP_STATUS_TIME_DONE','CD':'ADGROUP_STATUS_CAMPAIGN_DISABLE','D':'ADGROUP_STATUS_DISABLE'}
ags={}
for f in ['adgroups_p1.tsv','adgroups_p2.tsv']:
    for l in open(f):
        i,op,sec,n=l.rstrip('\n').split('\t'); ags[i]=dict(name=n,op=OPM[op],sec=SECM[sec])
print('campaigns',len(camps),'adgroups',len(ags))
errors=[]
def render(pairs):
    if not pairs: return None
    parts=[]
    for k,v in pairs:
        parts.append(k if v is None else f"{k}={v}")
    return "&".join(parts)
def merge(base, pairs):
    """Return (url, note) merging utm pairs into base without duplicating identical params."""
    if base is None: return None, None
    if not pairs: return base, None
    q=urlsplit(base).query
    existing=parse_qsl(q, keep_blank_values=True)
    raw_tokens=q.split('&') if q else []
    exd=collections.defaultdict(list)
    for k,v in existing: exd[k].append(v)
    add=[]; conflicts=[]; same=0
    for k,v in pairs:
        tok = k if v is None else f"{k}={v}"
        if tok in raw_tokens: same+=1; continue
        if v is not None and k in exd and v in exd[k]: same+=1; continue
        if k in exd: conflicts.append(f"{k}: url={exd[k][0]!r} vs utm_params={v!r}"); continue
        add.append(tok)
    notes=[]
    url=base
    if add:
        url = base + ('&' if '?' in base else '?') + '&'.join(add)
        notes.append("utm_params not present in stored landing page URL were appended: "+", ".join(add))
    if conflicts:
        notes.append("utm_params value differs from value already in stored URL (stored URL value kept): "+"; ".join(conflicts))
    if not add and not conflicts:
        notes.append("all utm_params already present in stored landing_page_url (no change on merge)")
    url_keys=[k for k,_ in existing]
    utm_keys={k for k,_ in pairs}
    extra=[k for k in url_keys if k not in utm_keys]
    if extra: notes.append("URL has params not in utm_params: "+",".join(extra))
    return url, "; ".join(notes)
def cstatus(cid):
    c=camps.get(cid)
    if not c: errors.append(f"campaign {cid} not in campaign/get STATUS_NOT_DELETE list"); return None,None
    return c['name'], f"{c['op']} / {c['sec']}"
def astatus(aid):
    a=ags.get(aid)
    if not a: errors.append(f"adgroup {aid} not in adgroup/get STATUS_NOT_DELETE list"); return None,None
    return a['name'], f"{a['op']} / {a['sec']}"
rows=[]
# Manual ads
man=json.load(open('manual_ads.json'))
for aid,a in man.items():
    cn,cs=cstatus(a['campaign_id']); gn,gs=astatus(a['adgroup_id'])
    base=a.get('landing_page_url') or None
    pairs=a.get('utm_params')
    tags=render(pairs)
    url,mnote=merge(base,pairs)
    if base is None and tags:
        mnote="utm_params set but landing_page_url empty, so no final URL"
    notes=[f"Manual campaign ad; ad_format={a.get('ad_format')}"]
    if base is None:
        notes.append("no landing page URL on this ad (landing_page_url empty; landing_page_urls, deeplink and page_id also empty in ad/get response)")
    if mnote: notes.append(mnote)
    if a['secondary_status']!='AD_STATUS_DELIVERY_OK': notes.append(f"delivery status {a['secondary_status']}")
    rows.append(dict(platform="tiktok",account_id=ACC,account_name=ACCN,campaign_id=a['campaign_id'],campaign_name=cn,campaign_status=cs,
        adset_id=a['adgroup_id'],adset_name=gn,adset_status=gs,ad_id=aid,ad_name=a['ad_name'],ad_status=a['operation_status'],effective_status=a['secondary_status'],
        creative_id=None,creative_name=None,slot="ad.landing_page_url",base_url=base,url_tags=tags,url=url,tracking_template=None,
        editable="yes" if base else "unknown",
        edit_method=("TikTok Marketing API ad/update (advertiser_id, adgroup_id, creatives[] with ad_id + landing_page_url; utm_params stored on the same creative) or Ads Manager > Ad > Destination URL" if base else
                     "No URL slot populated; would require ad/update setting landing_page_url, only possible if the ad group objective/placement supports a website destination"),
        notes="; ".join(notes)))
# Smart+ ads
cmap=collections.defaultdict(list)
for l in open('creative_map.txt'):
    c,s=l.split(); cmap[s].append(c)
spc=[json.loads(l) for f in ['spc_a.jsonl','spc_b.jsonl','spc_c.jsonl','spc_d.jsonl'] for l in open(f)]
for s in spc:
    cn,cs=cstatus(s['c']); gn,gs=astatus(s['ag'])
    pairs=None
    if s['utm']:
        pairs=[]
        for tok in s['utm'].split('&'):
            if '=' in tok: k,v=tok.split('=',1); pairs.append([k,v])
            else: pairs.append([tok,None])
    tags=s['utm']
    base_notes=[f"Upgraded Smart+ ad (smart_plus_ad_id; campaign_automation_type UPGRADED_SMART_PLUS); read via smart_plus/ad/get; creative-level ad/get ad_ids under this ad: {','.join(sorted(cmap[s['id']]))}"]
    if s.get('x'): base_notes.append(s['x'])
    if s['sec']!='AD_STATUS_DELIVERY_OK': base_notes.append(f"delivery status {s['sec']}")
    em="TikTok Marketing API smart_plus/ad/update (smart_plus_ad_id, landing_page_url_list[%d].landing_page_url; utm params in ad_configuration.utm_params) or Ads Manager > Smart+ ad > Destination URL"
    lps=s['lp'] or []
    if not lps:
        rows.append(dict(platform="tiktok",account_id=ACC,account_name=ACCN,campaign_id=s['c'],campaign_name=cn,campaign_status=cs,
            adset_id=s['ag'],adset_name=gn,adset_status=gs,ad_id=s['id'],ad_name=s['name'],ad_status=s['op'],effective_status=s['sec'],
            creative_id=None,creative_name=None,slot="smart_plus_ad.landing_page_url_list",base_url=None,url_tags=tags,url=None,tracking_template=None,
            editable="unknown",edit_method="No URL slot populated; smart_plus/ad/update landing_page_url_list only if the objective supports a website destination",
            notes="; ".join(base_notes+["no landing page URL (landing_page_url_list absent/empty; deeplink_list empty)"])))
    for i,lp in enumerate(lps):
        url,mnote=merge(lp,pairs)
        rows.append(dict(platform="tiktok",account_id=ACC,account_name=ACCN,campaign_id=s['c'],campaign_name=cn,campaign_status=cs,
            adset_id=s['ag'],adset_name=gn,adset_status=gs,ad_id=s['id'],ad_name=s['name'],ad_status=s['op'],effective_status=s['sec'],
            creative_id=None,creative_name=None,slot=f"smart_plus_ad.landing_page_url_list[{i}].landing_page_url",base_url=lp,url_tags=tags,url=url,tracking_template=None,
            editable="yes",edit_method=em%i,notes="; ".join(base_notes+([mnote] if mnote else []))))
with open(OUT,'w') as f:
    for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
print('rows',len(rows)); print('errors',sorted(set(errors)))
