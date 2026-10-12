import json,sys,copy
src,newurl,out=sys.argv[1],sys.argv[2],sys.argv[3]
o=json.load(open(src))
p={}
p['name']=o['name']
p['object_story_spec']=o['object_story_spec']
afs=copy.deepcopy(o['asset_feed_spec'])
assert len(afs['link_urls'])==1
afs['link_urls'][0]['website_url']=newurl
p['asset_feed_spec']=afs
cfs={}
for k in o['dof_optout_keys']:
    cfs[k]={"enroll_status":"OPT_OUT"}
    if k=='product_extensions':
        cfs[k]["customizations"]={"pe_carousel":{"enroll_status":"OPT_OUT"}}
p['degrees_of_freedom_spec']={"creative_features_spec":cfs}
for k in ('creative_sourcing_spec','format_transformation_spec','threads_user_id'):
    if k in o: p[k]=o[k]
json.dump(p,open(out,'w'),ensure_ascii=False,indent=1)
print(len(cfs),'dof keys')
print(json.dumps(p,ensure_ascii=False))
