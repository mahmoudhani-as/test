import sys, json, copy
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_5')
from lib5 import *
AD = sys.argv[1]
ad, inp = last_ad_read(AD)
json.dump(ad, open(W + 'ad_pre_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
u = unit(AD)
cr = ad['creative']
print('ad', AD, 'status', ad.get('status'), ad.get('configured_status'), ad.get('effective_status'), 'creative', cr['id'], 'plan creative', u['creative_id'], 'updated', ad.get('updated_time'))
cl = classify(u, cr)
for x in cl: print(x)
known = {'id', 'name', 'account_id', 'actor_id', 'object_type', 'status', 'contextual_multi_ads', 'threads_user_id',
         'authorization_category', 'source_instagram_media_id', 'effective_object_story_id', 'effective_instagram_media_id',
         'use_page_actor_override', 'body', 'title', 'call_to_action', 'instagram_user_id', 'call_to_action_type',
         'effective_authorization_category', 'instagram_permalink_url', 'video_id', 'image_hash', 'link_url', 'object_id'}
unknown = [k for k in cr if k not in known]
print('unknown fields:', unknown)
assert not unknown
assert cr.get('use_page_actor_override') in (None, False)
assert not cr.get('url_tags')
if all(v == 'Write' for _, v, _ in cl):
    p = {'name': cr['name'], 'object_id': cr['actor_id'], 'instagram_user_id': cr['instagram_user_id'],
         'source_instagram_media_id': cr['source_instagram_media_id'],
         'call_to_action': copy.deepcopy(cr['call_to_action'])}
    for k in ('contextual_multi_ads', 'threads_user_id', 'authorization_category'):
        if k in cr:
            p[k] = copy.deepcopy(cr[k])
    for c in u['changes']:
        assert c['slot'] == 'creative.call_to_action.value.link'
        p['call_to_action']['value']['link'] = c['new']
    assert set(p['call_to_action'].keys()) == {'type', 'value'} and set(p['call_to_action']['value'].keys()) == {'link'}
    json.dump(p, open(W + 'payload_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(p, ensure_ascii=False))
