import json,sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/work_meta_2')
import lib2
# usage: verify.py <tool-result-file> <ad_id> [<ad_id>...]
f=sys.argv[1]; ids=sys.argv[2:]
inner=lib2.load_tool(f)
ads={a['id']:a for a in inner['data']['data']}
json.dump(list(ads.values()), open(lib2.WORK+'/readback_'+f.rsplit('/',1)[-1], 'w'), ensure_ascii=False, indent=1)
pr=lib2.preread()
IGNORE_TOP={'id','name','status','effective_object_story_id','effective_instagram_media_id','thumbnail_url','video_id','object_story_id'}
for aid in ids:
    a=ads.get(aid)
    u=lib2.unit(aid)
    old=pr[aid]['creative']; new=a['creative']
    print('==== ad', aid, 'configured', a['configured_status'], 'effective', a['effective_status'], 'creative', old['id'], '->', new['id'])
    for c in u['changes']:
        cur=lib2.get_slot(new, c['slot'])
        print('   slot', c['slot'], 'readback==new:', cur==c['new'], '| url_tags:', new.get('url_tags'))
    # expected = old with the URL set, and name prefix
    exp=json.loads(json.dumps(old))
    for c in u['changes']: lib2.set_slot(exp, c['slot'], c['new'])
    print('   name old->new:', old['name'], '=>', new['name'], '| prefix kept:', new['name'].startswith(old['name']))
    d=lib2.diff({k:v for k,v in exp.items() if k not in IGNORE_TOP}, {k:v for k,v in new.items() if k not in IGNORE_TOP})
    # summarize dof additions separately
    dof_add=[x for x in d if x.startswith('+ .degrees_of_freedom_spec.creative_features_spec.')]
    other=[x for x in d if x not in dof_add]
    if dof_add:
        vals=set(x.split('= ',1)[1] for x in dof_add)
        print('   dof features added by Meta default:', len(dof_add), 'values', vals)
    for x in other: print('  ', x)
