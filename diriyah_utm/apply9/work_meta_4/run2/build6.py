import json, sys, unicodedata, copy
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_meta_4/run2')
import lib10 as L
AD = '120252572195190058'
u = L.unit(AD)
print('excluded:', [L.excluded(AD, c['slot']) for c in u['changes']])
ad, rid_ad = L.read_ad(AD)
print('ad', ad['id'], ad['configured_status'], ad['effective_status'], ad['status'], ad['updated_time'], 'creative', ad['creative']['id'], 'plan', u['creative_id'], 'req', rid_ad)
o, rid_o = L.read_creative(ad['creative']['id'])
json.dump(o, open(L.W + 'orig_%s.json' % o['id'], 'w'), ensure_ascii=False, indent=1)
print('creative read req', rid_o, 'url_tags', repr(o.get('url_tags')), 'unknown fields', L.unknown_fields(o), 'dof', L.dof_summary(o)[0])
for c, cur, v in L.classify(u, o):
    print(v, c['slot']); print('  cur ', cur); print('  ==now', cur == c['now'], '| in alt', cur in c['alt_now'])
print('ad-level slot == creative slot:', ad['creative']['asset_feed_spec']['link_urls'][0]['website_url'] == L.get_slot(o, u['changes'][0]['slot']))
# unchanged since apply8 pre-read?
pre = json.load(open(L.ROOT + '/apply8/work_meta_8/pre_120252572195190058.json'))
pc = pre['creative'] if 'creative' in pre else pre
strip = lambda d: {k: v for k, v in d.items() if k not in L.DERIVED}
def drop_img(d):
    d = copy.deepcopy(d)
    for sl in (d.get('creative_sourcing_spec') or {}).get('site_links_spec', []) or []:
        sl.pop('site_link_image_url', None)
    return d
print('live creative vs apply8 pre-read (non-derived, site_link_image_url ignored):', L.diff(drop_img(strip(pc)), drop_img(strip(o)))[:10])
p, notes = L.build_payload(o, u['changes'])
for sl in (p.get('creative_sourcing_spec') or {}).get('site_links_spec', []) or []:
    assert sl.get('site_link_image_hash'), sl
    sl.pop('site_link_image_url', None)
notes.append('site_links_spec[*].site_link_image_url (derived from site_link_image_hash) not sent; hash sent')
json.dump(p, open(L.W + 'payload_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
print('notes', notes)
for x in L.diff({k: v for k, v in o.items() if k in p}, p):
    print('diff orig->payload', x)
print('payload keys', list(p.keys()))
print('all urls in payload:', [(a, b) for a, b in L.all_urls(p)])
s = json.dumps(p, ensure_ascii=False)
seen = {}
for ch in s:
    if ord(ch) > 127 and not (0x0621 <= ord(ch) <= 0x064A):
        seen[ch] = seen.get(ch, 0) + 1
print('non-ASCII chars outside U+0621..U+064A:', sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items()))
print('PAYLOAD_ASCII', json.dumps(p, ensure_ascii=True, separators=(', ', ': ')))
