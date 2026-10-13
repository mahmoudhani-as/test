import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_meta_4/run2')
import lib10 as L
AD = '120249174447430058'; ORIG = '1701601021126452'; ORPHAN = '967332096432226'
u = L.unit(AD)
print('excluded:', [L.excluded(AD, c['slot']) for c in u['changes']])
ad, rid_ad = L.read_ad(AD)
print('ad', ad['id'], ad['configured_status'], ad['effective_status'], ad['status'], ad['updated_time'], 'creative', ad['creative']['id'], 'plan', u['creative_id'], 'req', rid_ad)
o, rid_o = L.read_creative(ORIG)
n, rid_n = L.read_creative(ORPHAN)
json.dump(o, open(L.W + 'orig_%s.json' % ORIG, 'w'), ensure_ascii=False, indent=1)
json.dump(n, open(L.W + 'orphan_%s.json' % ORPHAN, 'w'), ensure_ascii=False, indent=1)
print('url_tags orig', repr(o.get('url_tags')), 'orphan', repr(n.get('url_tags')), 'unknown fields', L.unknown_fields(o))
for c, cur, v in L.classify(u, o):
    print(v, c['slot']); print('  cur ', cur); print('  ==now', cur == c['now'], '| in alt', cur in c['alt_now'])
print('ad-level slot == creative slot:', ad['creative']['asset_feed_spec']['link_urls'][0]['website_url'] == L.get_slot(o, u['changes'][0]['slot']))
d = L.compare_new(o, n, u['changes'])
dof, other = L.split_dof(d)
print('orphan vs (orig with new URL), non-derived diffs other than Meta-default dof spec:', other)
print('orphan dof spec:', L.dof_summary(n), '| orig dof spec:', L.dof_summary(o))
print('orphan slot == new byte for byte:', L.get_slot(n, u['changes'][0]['slot']) == u['changes'][0]['new'])
print('derived: orphan name', n['name'], '| status', n['status'], '| eff story', n.get('effective_object_story_id'), '| eff IG', n.get('effective_instagram_media_id'))
print('derived: orig   name', o['name'], '| status', o['status'], '| eff story', o.get('effective_object_story_id'), '| eff IG', o.get('effective_instagram_media_id'))
p, notes = L.build_payload(o, u['changes'])
json.dump(p, open(L.W + 'payload_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
prevp = json.load(open(L.ROOT + '/apply9/work_meta_4/payload_%s.json' % AD))
print('rebuilt payload == earlier payload file:', p == prevp, L.diff(prevp, p)[:5], 'notes', notes)
hits = L.find_calls('meta_ad_account_id_adcreatives_create', lambda i: i.get('dry_run') is False, L.PREV_TRANSCRIPT)
for cid, inp, res, err in hits:
    dd = L.parse_result(res)
    if dd['data']['data'].get('id') == ORPHAN:
        print('earlier live create input == rebuilt payload:', inp['payload'] == p, '| req', dd['meta']['requestId'])
prev_o = json.load(open(L.ROOT + '/apply9/work_meta_4/orig_%s.json' % ORIG))
print('orig now vs earlier read (non-derived):', L.diff({k: v for k, v in prev_o.items() if k not in L.DERIVED}, {k: v for k, v in o.items() if k not in L.DERIVED}))
nn = {k: v for k, v in n.items() if k in p or k == 'degrees_of_freedom_spec'}
print('orphan creatable fields vs payload:', [x for x in L.diff(p, nn) if not x.startswith('+ .degrees_of_freedom_spec')])
