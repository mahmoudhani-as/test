import json, sys, unicodedata
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_meta_4/run2')
import lib10 as L
AD = sys.argv[1]
u = L.unit(AD)
print('excluded:', [L.excluded(AD, c['slot']) for c in u['changes']])
ad, rid_ad = L.read_ad(AD)
print('ad', ad['id'], ad['configured_status'], ad['effective_status'], ad['status'], ad['updated_time'], 'creative', ad['creative']['id'], 'plan', u['creative_id'], 'req', rid_ad)
o, rid_o = L.read_creative(ad['creative']['id'])
json.dump(o, open(L.W + 'orig_%s.json' % o['id'], 'w'), ensure_ascii=False, indent=1)
print('creative read req', rid_o, 'url_tags', repr(o.get('url_tags')), 'unknown fields', L.unknown_fields(o), 'dof', L.dof_summary(o))
verdicts = L.classify(u, o)
for c, cur, v in verdicts:
    print(v, c['slot']); print('  cur ', cur); print('  ==now', cur == c['now'], '| in alt', cur in c['alt_now'])
print('ad-level slot == creative slot:', ad['creative']['asset_feed_spec']['link_urls'][0]['website_url'] == L.get_slot(o, u['changes'][0]['slot']))
if all(v == 'Write' for _, _, v in verdicts):
    p, notes = L.build_payload(o, u['changes'])
    json.dump(p, open(L.W + 'payload_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
    print('notes', notes)
    for x in L.diff({k: v for k, v in o.items() if k in p}, p):
        print('diff orig->payload', x)
    try:
        prevp = json.load(open(L.ROOT + '/apply9/work_meta_4/payload_%s.json' % AD))
        print('rebuilt payload == earlier payload file:', p == prevp, L.diff(prevp, p)[:5])
    except FileNotFoundError:
        print('no earlier payload file')
    try:
        p11 = json.load(open(L.ROOT + '/payloads/payload_%s.json' % AD))
        print('11-Oct payload exists; equal:', p11 == p)
    except FileNotFoundError:
        print('no 11-Oct payload')
    s = json.dumps(p, ensure_ascii=False)
    seen = {}
    for ch in s:
        if ord(ch) > 127 and not (0x0621 <= ord(ch) <= 0x064A):
            seen[ch] = seen.get(ch, 0) + 1
    print('non-ASCII chars outside U+0621..U+064A:', sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items()))
    print('PAYLOAD_JSON', json.dumps(p, ensure_ascii=False, separators=(',', ':')))
