import json
B='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W=B+'/reread4/work_meta_1198625455580757'
prev=json.load(open(B+'/reread3/work_meta_1198625455580757/data/ads_store.json'))
ids=json.load(open(W+'/data/list_ids_call1.json'))
def est(it):
    t=json.dumps(it,indent=2,ensure_ascii=False)
    return len(t)+10*(t.count('\n')+1)
E={a:est(prev[a]) for a in ids}
NG=4
tot=sum(E.values()); per=tot/NG
groups=[[] for _ in range(NG)]; sz=[0]*NG
gi=0
for a in ids:
    if groups[gi] and sz[gi]+E[a] > per*1.02 and gi<NG-1:
        gi+=1
    groups[gi].append(a); sz[gi]+=E[a]
TARGET=55500
small=sorted(ids,key=lambda a:E[a])
out=[]
for g,s in zip(groups,sz):
    pad=[]
    for a in small:
        if s>=TARGET: break
        if a in g or a in pad: continue
        pad.append(a); s+=E[a]
    out.append({'ids':g,'pad':pad,'est':s})
STAT=['ACTIVE','PAUSED','DELETED','PENDING_REVIEW','DISAPPROVED','PREAPPROVED','PENDING_BILLING_INFO','CAMPAIGN_PAUSED','ARCHIVED','ADSET_PAUSED','IN_PROCESS','WITH_ISSUES']
json.dump(out,open(W+'/data/groups.json','w'))
for i,g in enumerate(out):
    print('GROUP',i,len(g['ids']),'+',len(g['pad']),'pad est',g['est'])
    print(json.dumps([{'field':'effective_status','operator':'IN','value':STAT},{'field':'id','operator':'IN','value':g['ids']+g['pad']}],separators=(',',':')))
