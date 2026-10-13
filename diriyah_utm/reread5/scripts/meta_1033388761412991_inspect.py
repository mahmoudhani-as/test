import json, sys
raw_path, in_path = sys.argv[1], sys.argv[2]
j = json.load(open(raw_path, encoding='utf-8'))
ads = j['data']['data']['data']
paging = j['data']['data'].get('paging')
print('ads returned:', len(ads), 'paging:', paging, 'meta:', j['data']['data'].get('meta'))
inp = json.load(open(in_path, encoding='utf-8'))
in_ids = [r['ad_id'] for r in inp]
print('input rows:', len(inp), 'unique input ad ids:', len(set(in_ids)))
cur_ids = [a['id'] for a in ads]
print('missing from current (non-deleted) list:', sorted(set(in_ids) - set(cur_ids)))
print('current ads not in input:', sorted(set(cur_ids) - set(in_ids)))
for a in ads:
    c = a.get('creative', {})
    oss = c.get('object_story_spec') or {}
    ld = oss.get('link_data') or {}
    vd = oss.get('video_data') or {}
    print('---', a['id'], a['effective_status'], '| cfg', a.get('configured_status'), '| upd', a.get('updated_time'))
    print('   creative', c.get('id'), '| eosid', c.get('effective_object_story_id'), '| osid', c.get('object_story_id'), '| type', c.get('object_type'))
    print('   url_tags', repr(c.get('url_tags')), '| afs', bool(c.get('asset_feed_spec')), '| link_url', c.get('link_url'), '| template_url', c.get('template_url'))
    print('   oss keys', list(oss.keys()), '| ld.link', ld.get('link'), '| ld.cta', ld.get('call_to_action'), '| vd.cta', vd.get('call_to_action'))
    print('   creative.cta', c.get('call_to_action'), '| cta_type', c.get('call_to_action_type'))
