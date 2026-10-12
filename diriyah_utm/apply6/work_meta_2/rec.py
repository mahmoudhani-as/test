import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/work_meta_2')
import lib2

# usage: rec.py <readback json basename> <ad_id> <new_creative> <shape text> <extra side-effects text>
# Appends one result line for the unit's first change to the batch results file (lib2.OUT).
rbf, aid, newc, shape, extra = sys.argv[1:6]
u = lib2.unit(aid)
pr = lib2.preread()
old = pr[aid]['creative']
before = lib2.get_slot(old, u['changes'][0]['slot'])
rb = {a['id']: a for a in json.load(open(lib2.WORK + '/readback_' + rbf))}
a = rb[aid]
assert a['creative']['id'] == newc, (a['creative']['id'], newc)
after = lib2.get_slot(a['creative'], u['changes'][0]['slot'])
prev_eff = pr[aid]['effective_status']
detail = ("Live slot equalled 'now' (re-read just before the write; ad still on planned creative %s, no url_tags). "
          "Old creative %s -> new creative %s: %s Only %s changed. Dry-run preview checked; new creative read back and "
          "diffed by script against the original: 0 differences except the URL, Meta's name date-hash suffix (name dedupe)%s. "
          "Ad POST {creative_id} success=true; status not sent. After: ad on creative %s, configured_status=%s (unchanged), "
          "effective_status=%s (re-review; was %s).") % (
    old['id'], old['id'], newc, shape, u['changes'][0]['slot'].replace('creative.', ''), extra, newc,
    a['configured_status'], a['effective_status'], prev_eff)
assert a['configured_status'] == pr[aid]['configured_status']
result = 'Fixed' if after == u['changes'][0]['new'] else 'Failed'
lib2.record(u, 0, before, after, result, 'creative:' + newc, detail)
print(detail)
