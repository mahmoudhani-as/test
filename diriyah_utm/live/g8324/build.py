import json,glob,collections,os
D=os.path.dirname(os.path.abspath(__file__))
OUT='/tmp/claude-0/-home-user-test/c5fcace8-62b1-55a4-9129-dbfe4d94e847/scratchpad/live/google_8324286739.jsonl'
ACC='8324286739'; ACCNAME='H&S - DGCL - Visit Diriyah'
CUST_SUFFIX=None; CUST_TMPL=None  # customer.final_url_suffix / tracking_url_template read live: both unset

def load(pattern,key):
    out={}
    for f in sorted(glob.glob(os.path.join(D,pattern))):
        d=json.load(open(f)); j=json.loads(d[0]['text'])
        for r in j['data']['data']['data'].get('results',[]):
            if not isinstance(r,dict): continue
            out[key(r)]=r
    return out

ads=load('ads_p*.json',lambda r:r['adGroupAd']['resourceName'])
assets=load('sl_assets_p*.json',lambda r:r['asset']['id'])
cas=load('ca_p*.json',lambda r:r['campaignAsset']['resourceName'])
agas=load('aga_p*.json',lambda r:r['adGroupAsset']['resourceName'])

camp={}; ag={}
for r in ads.values():
    c=r['campaign']; camp.setdefault(c['id'],{}).update({k:c.get(k) for k in ('name','status','advertisingChannelType','finalUrlSuffix','trackingUrlTemplate') if k in c or k in ('finalUrlSuffix','trackingUrlTemplate')})
    g=r['adGroup']; ag[g['id']]={'name':g.get('name'),'status':g.get('status'),'finalUrlSuffix':g.get('finalUrlSuffix'),'trackingUrlTemplate':g.get('trackingUrlTemplate'),'campaign':c['id']}
for r in cas.values():
    c=r['campaign']; e=camp.setdefault(c['id'],{})
    e.setdefault('name',c.get('name')); e.setdefault('status',c.get('status'))
print('ads',len(ads),'assets',len(assets),'campaign links',len(cas),'adgroup links',len(agas))

def join(base,suffix):
    if not base: return None
    if not suffix: return base
    frag=''
    if '#' in base:
        base,frag=base.split('#',1); frag='#'+frag
    if base.endswith('?') or base.endswith('&'): sep=''
    elif '?' in base: sep='&'
    else: sep='?'
    return base+sep+suffix.lstrip('?&')+frag

def eff(*levels):
    for name,val in levels:
        if val: return val,name
    return None,None

rows=[]
# ---- ads
for rn,r in sorted(ads.items(), key=lambda kv:(kv[1]['campaign']['id'],kv[1]['adGroup']['id'],int(kv[1]['adGroupAd']['ad']['id']))):
    c=r['campaign']; g=r['adGroup']; aga=r['adGroupAd']; ad=aga['ad']
    suf,suflvl=eff(('ad',ad.get('finalUrlSuffix')),('ad_group',g.get('finalUrlSuffix')),('campaign',c.get('finalUrlSuffix')),('account',CUST_SUFFIX))
    tmpl,tmpllvl=eff(('ad',ad.get('trackingUrlTemplate')),('ad_group',g.get('trackingUrlTemplate')),('campaign',c.get('trackingUrlTemplate')),('account',CUST_TMPL))
    appr=aga.get('policySummary',{}).get('approvalStatus')
    if c.get('status')!='ENABLED': es='CAMPAIGN_'+str(c.get('status'))
    elif g.get('status')!='ENABLED': es='AD_GROUP_'+str(g.get('status'))
    elif aga.get('status')!='ENABLED': es='AD_'+str(aga.get('status'))
    elif appr=='DISAPPROVED': es='DISAPPROVED'
    else: es='ELIGIBLE'
    base_notes=f"ad_type={ad.get('type')}; channel={c.get('advertisingChannelType')}; approval_status={appr}; ad_status={aga.get('status')}; adgroup_status={g.get('status')}; campaign_status={c.get('status')}"
    base_notes+=f"; effective suffix level={suflvl or 'none (no suffix set at ad/ad group/campaign/account)'}"
    if tmpllvl: base_notes+=f"; tracking template level={tmpllvl}"
    common={"platform":"google","account_id":ACC,"account_name":ACCNAME,
        "campaign_id":c['id'],"campaign_name":c.get('name'),"campaign_status":c.get('status'),
        "adset_id":g['id'],"adset_name":g.get('name'),"adset_status":g.get('status'),
        "ad_id":ad['id'],"ad_name":ad.get('name'),"ad_status":aga.get('status'),"effective_status":es,
        "creative_id":None,"creative_name":None}
    slots=[(f'ad.final_urls[{i}]',u) for i,u in enumerate(ad.get('finalUrls',[]))]+[(f'ad.final_mobile_urls[{i}]',u) for i,u in enumerate(ad.get('finalMobileUrls',[]))]
    edit=f"AdService.MutateAds update (resource customers/{ACC}/ads/{ad['id']}, update_mask ad.final_urls / ad.final_mobile_urls / ad.final_url_suffix); ad keeps its id, goes back to policy review"
    if not slots:
        rows.append({**common,"slot":None,"base_url":None,"url_tags":suf,"url":None,"tracking_template":tmpl,"editable":"yes","edit_method":edit,"notes":base_notes+"; ad has no final URL"})
    for slot,u in slots:
        rows.append({**common,"slot":slot,"base_url":u,"url_tags":suf,"url":join(u,suf),"tracking_template":tmpl,"editable":"yes","edit_method":edit,"notes":base_notes})

# ---- sitelinks
linkcount=collections.Counter()
for r in cas.values(): linkcount[r['asset']['id']]+=1
for r in agas.values(): linkcount[r['asset']['id']]+=1
missing_assets=set()
def sl_rows(level, link, lnk):
    a=assets.get(link['asset']['id'])
    if a is None:
        missing_assets.add(link['asset']['id']); return
    a=a['asset']; c=link['campaign']; cinfo=camp.get(c['id'],{})
    cname=c.get('name') or cinfo.get('name')
    if level=='ad_group':
        g=link['adGroup']; ginfo=ag.get(g['id'],{})
        gsuf=ginfo.get('finalUrlSuffix'); gtmpl=ginfo.get('trackingUrlTemplate')
    else:
        g=None; gsuf=gtmpl=None
    suf,suflvl=eff(('asset',a.get('finalUrlSuffix')),('ad_group',gsuf),('campaign',cinfo.get('finalUrlSuffix')),('account',CUST_SUFFIX))
    tmpl,tmpllvl=eff(('asset',a.get('trackingUrlTemplate')),('ad_group',gtmpl),('campaign',cinfo.get('trackingUrlTemplate')),('account',CUST_TMPL))
    appr=a.get('policySummary',{}).get('approvalStatus')
    cst=c.get('status'); gst=g.get('status') if g else None; lst=lnk.get('status')
    if cst!='ENABLED': es='CAMPAIGN_'+str(cst)
    elif g and gst!='ENABLED': es='AD_GROUP_'+str(gst)
    elif lst!='ENABLED': es='LINK_'+str(lst)
    elif appr=='DISAPPROVED': es='DISAPPROVED'
    else: es='ELIGIBLE'
    linkres=lnk['resourceName']
    notes=(f"SITELINK asset (not an ad); linked at {level} level via {linkres}; link_status={lst}; asset approval_status={appr or 'not returned'}; "
           f"same asset linked in {linkcount[a['id']]} campaign/ad group placement(s) in this account; effective suffix level={suflvl or 'none (no suffix set at asset/ad group/campaign/account)'}")
    if tmpllvl: notes+=f"; tracking template level={tmpllvl}"
    common={"platform":"google","account_id":ACC,"account_name":ACCNAME,
        "campaign_id":c['id'],"campaign_name":cname,"campaign_status":cst,
        "adset_id":g['id'] if g else None,"adset_name":g.get('name') if g else None,"adset_status":gst,
        "ad_id":a['id'],"ad_name":a.get('sitelinkAsset',{}).get('linkText'),"ad_status":lst,"effective_status":es,
        "creative_id":a['id'],"creative_name":a.get('name') or a.get('sitelinkAsset',{}).get('linkText')}
    edit=(f"AssetService.MutateAssets update customers/{ACC}/assets/{a['id']} (update_mask final_urls / final_url_suffix) - shared asset, change hits all {linkcount[a['id']]} placement(s); "
          f"or create a new sitelink asset and swap the {level}_asset link")
    slots=[(f"sitelink asset {a['id']} final_urls[{i}] ({level}_asset)",u) for i,u in enumerate(a.get('finalUrls',[]))]+[(f"sitelink asset {a['id']} final_mobile_urls[{i}] ({level}_asset)",u) for i,u in enumerate(a.get('finalMobileUrls',[]))]
    if not slots:
        rows.append({**common,"slot":f"sitelink asset {a['id']} ({level}_asset)","base_url":None,"url_tags":suf,"url":None,"tracking_template":tmpl,"editable":"yes","edit_method":edit,"notes":notes+"; sitelink has no final URL"})
    for slot,u in slots:
        rows.append({**common,"slot":slot,"base_url":u,"url_tags":suf,"url":join(u,suf),"tracking_template":tmpl,"editable":"yes","edit_method":edit,"notes":notes})

for rn,r in sorted(cas.items(), key=lambda kv:(kv[1]['campaign']['id'],kv[1]['asset']['id'])):
    sl_rows('campaign', r, r['campaignAsset'])
for rn,r in sorted(agas.items(), key=lambda kv:(kv[1]['campaign']['id'],kv[1]['adGroup']['id'],kv[1]['asset']['id'])):
    sl_rows('ad_group', r, r['adGroupAsset'])

print('missing assets',missing_assets)
print('campaigns without name', [k for k,v in camp.items() if not v.get('name')])
print('sitelink rows w/o campaign name', sum(1 for x in rows if not x['campaign_name']))
with open(OUT,'w') as f:
    for x in rows: f.write(json.dumps(x,ensure_ascii=False)+'\n')
print('rows',len(rows))
linked=set(linkcount); print('sitelink assets linked',len(linked),'unlinked',len(set(assets)-linked))
