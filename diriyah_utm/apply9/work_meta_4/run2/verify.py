import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_meta_4/run2')
import lib10 as L
AD, NEW = sys.argv[1], sys.argv[2]
u = L.unit(AD)
ad, rid = L.read_ad(AD)
cr = ad['creative']
print('ad', ad['id'], 'configured', ad['configured_status'], 'effective', ad['effective_status'], 'status', ad['status'], 'updated', ad['updated_time'], 'creative', cr['id'], 'is new', cr['id'] == NEW, 'url_tags', repr(cr.get('url_tags')), 'read req', rid)
for c in u['changes']:
    got = L.full_landing(cr, c['slot'])
    print('slot', c['slot'])
    print(' after_live', got)
    print(' == new byte for byte:', got == c['new'])
n, rid_n = L.read_creative(NEW)
print('creative read req', rid_n, '| creative slot == new:', all(L.get_slot(n, c['slot']) == c['new'] for c in u['changes']), '| url_tags', repr(n.get('url_tags')), '| status', n.get('status'), '| eff story', n.get('effective_object_story_id'), '| eff IG', n.get('effective_instagram_media_id'))
if len(sys.argv) > 3:
    o = json.load(open(L.W + 'orig_%s.json' % sys.argv[3]))
    d = L.compare_new(o, n, u['changes'])
    dof, other = L.split_dof(d)
    print('new creative vs (orig with new URL), non-derived diffs other than Meta-default dof spec:', other)
    print('dof spec added by Meta:', L.dof_summary(n), '| orig dof:', L.dof_summary(o))
    print('name', n['name'])
