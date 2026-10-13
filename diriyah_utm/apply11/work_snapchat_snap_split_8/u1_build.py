import json,sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_snapchat_snap_split_8/')
from lib import *
u=units()[0]; r=json.load(open(W+'u1_reads.json'))
assert u['unit']==r['ad']['id'] and r['ad']['creative_id']==u['creative_id']
ids=r['composite']['composite_properties']['creative_ids']
subs={s['id']:s for s in r['subs']}
out=[]
for i,ch in enumerate(u['changes']):
    sid=ch['slot'].split('(')[1].split(')')[0]
    assert ch['slot'].startswith('creative.composite_properties.creative_ids[%d] ('%i) and ids[i]==sid
    cur=subs[sid]['web_view_properties']['url']
    print(i,sid,classify(cur,ch), cur==ch['now'])
    out.append(copy_creative(subs[sid], url=ch['new']))
p={"creatives":out}
json.dump(p,open(W+'u1_payload_subs.json','w'),ensure_ascii=False,indent=1)
print(json.dumps(p,ensure_ascii=False))
