"""Group FIX slots into edit units per platform; flag shared-unit conflicts. Writes apply_plan.json."""
import json, sys, collections
S = json.load(open(sys.argv[1])); out = sys.argv[2]
UNIT = {'meta': 'ad_id', 'snapchat': 'creative_id', 'tiktok': 'ad_id', 'google': 'ad_id', 'linkedin': 'creative_id', 'x': 'creative_id'}
# every slot of every unit (to detect units where only some slots are fixable)
by_unit = collections.defaultdict(list)
for s in S:
    if not s.get('url'): continue
    if 'sitelink' in str(s.get('slot')).lower():
        key = (s['platform'], s.get('account_id'), 'asset:' + str(s.get('ad_id')))
    else:
        key = (s['platform'], s.get('account_id'), str(s.get(UNIT[s['platform']]) or s.get('ad_id')))
    by_unit[key].append(s)
plan, skipped = [], []
for key, slots in by_unit.items():
    fix = [s for s in slots if s['derive_status'] == 'FIX']
    if not fix: continue
    # one URL slot can appear on several rows (shared creative / sitelink links): expected must agree
    per_slot = collections.defaultdict(set)
    for s in slots:
        per_slot[(s.get('slot'), s.get('url'))].add(s.get('expected_url') if s['derive_status'] in ('FIX', 'OK') else 'BLOCKED')
    conflict = [k for k, v in per_slot.items() if len(v) > 1]
    blocked_sibling = [s for s in slots if s['derive_status'] == 'BLOCKED']
    item = {'platform': key[0], 'account_id': key[1], 'unit': key[2],
            'account_name': fix[0].get('account_name'), 'campaign_name': fix[0].get('campaign_name'), 'adset_name': fix[0].get('adset_name'),
            'ad_ids': sorted({str(s.get('ad_id')) for s in slots}), 'ad_names': sorted({str(s.get('ad_name')) for s in slots}),
            'creative_id': fix[0].get('creative_id'), 'adset_id': fix[0].get('adset_id'), 'campaign_id': fix[0].get('campaign_id'),
            'status': fix[0].get('effective_status') or fix[0].get('ad_status'), 'edit_method': fix[0].get('edit_method'),
            'changes': sorted({(s.get('slot'), s.get('base_url'), s.get('url_tags'), s['url'], s['expected_url']) for s in fix}),
            'notes': sorted({str(s.get('notes')) for s in slots if s.get('notes')})[:5]}
    if conflict:
        item['skip_reason'] = 'same URL slot shared by ads whose names give different generator URLs: ' + json.dumps([list(k) for k in conflict])[:400]
        skipped.append(item); continue
    if blocked_sibling:
        item['skip_reason'] = 'same edit unit also has a blocked slot (' + blocked_sibling[0]['derive_reasons'][0][:150] + ')'
        skipped.append(item); continue
    plan.append(item)
json.dump({'plan': plan, 'skipped': skipped}, open(out, 'w'), indent=1, default=str)
c = collections.Counter((p['platform'], p['account_name']) for p in plan)
print('edit units to apply:', len(plan), 'slots:', sum(len(p['changes']) for p in plan))
for k, v in sorted(c.items(), key=str): print('  ', v, k)
print('skipped units:', len(skipped))
for s in skipped[:10]: print('  ', s['platform'], s['unit'], s['skip_reason'][:160])
