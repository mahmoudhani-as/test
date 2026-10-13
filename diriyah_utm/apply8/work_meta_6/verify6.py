"""usage: python3 -I verify6.py <nodof_read.json> <dof_read.json or -> <ad_id> <expected_new_creative_id>
Compares the ad's live creative with the original (pre_merged.json): slot must equal "new" byte for byte,
everything else identical except derived ids and the name suffix Meta appends."""
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_6')
import lib6 as L

nod_path, dof_path, ad_id, new_cid = sys.argv[1:5]
pre = json.load(open(L.W + 'pre_merged.json'))
u = L.unit(ad_id)
orig_cid = pre['ads'][ad_id]['creative_id']
orig = pre['creatives'][orig_cid]

N = L.ads_from(nod_path)
a = N[ad_id]
cr = a['creative']
print('ad', ad_id, 'status', a['status'], 'configured', a['configured_status'], 'effective', a['effective_status'], 'updated', a['updated_time'])
print('creative id live', cr['id'], 'expected', new_cid, 'match', cr['id'] == new_cid)
live = dict(cr)
if dof_path != '-':
    D = L.ads_from(dof_path)
    dc = D[ad_id]['creative']
    assert dc['id'] == cr['id'], ('dof read creative differs', dc['id'], cr['id'])
    live['degrees_of_freedom_spec'] = dc['degrees_of_freedom_spec']
    print('dof features', len(dc['degrees_of_freedom_spec'].get('creative_features_spec', {})),
          'statuses', sorted({v.get('enroll_status') for v in dc['degrees_of_freedom_spec'].get('creative_features_spec', {}).values()}))
for c in u['changes']:
    after = L.full_url(live, c['slot'])
    print('slot', c['slot'])
    print('  after_live :', after)
    print('  new        :', c['new'])
    print('  byte-equal :', after == c['new'], '| url_tags:', repr(live.get('url_tags')))
# full comparison (name handled separately)
o = dict(orig)
n = dict(live)
if dof_path == '-':
    o.pop('degrees_of_freedom_spec', None)
oname, nname = o.pop('name'), n.pop('name')
diffs = L.compare_creatives(o, n, u['changes'])
print('name orig:', oname)
print('name new :', nname)
print('name keeps original prefix:', nname.startswith(oname[:60]))
print('unexpected diffs vs original (besides slot):', diffs if diffs else 'NONE')
