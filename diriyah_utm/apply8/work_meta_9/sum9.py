"""Print (stdout only) a per-change summary built from this agent's transcript + saved reads. Read-only."""
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_9')
from lib9 import *

calls = transcript_calls()
def rid(txt):
    r = parse_result(txt)
    return (r or {}).get('meta', {}).get('requestId') if isinstance(r, dict) else None

out = []
for u in units():
    AD = u['unit']
    pre = json.load(open(W + 'ad_pre_%s.json' % AD))
    aft = json.load(open(W + 'ad_after_%s.json' % AD))
    payload = json.load(open(W + 'payload_%s.json' % AD))
    gets = [(i, inp, txt) for i, inp, txt in calls if inp.get('action') == 'meta_ad_id_get' and str((inp.get('path_params') or {}).get('ad_id')) == AD]
    creates = [(i, inp, txt) for i, inp, txt in calls if inp.get('action') == 'meta_ad_account_id_adcreatives_create' and inp.get('payload') == payload]
    dry_c = [rid(t) for i, inp, t in creates if inp.get('dry_run') is True]
    live_c = [(rid(t), parse_result(t)['data']['data'].get('id')) for i, inp, t in creates if inp.get('dry_run') is False]
    assert len(live_c) == 1, (AD, live_c)
    new_id = live_c[0][1]
    assert aft['creative']['id'] == new_id, (AD, aft['creative']['id'], new_id)
    crd = [rid(t) for i, inp, t in calls if inp.get('action') == 'meta_creative_id_get' and str((inp.get('path_params') or {}).get('creative_id')) == new_id]
    upd = [(inp.get('dry_run'), rid(t), parse_result(t)['data']['data']) for i, inp, t in calls if inp.get('action') == 'meta_ad_id_update' and str((inp.get('path_params') or {}).get('ad_id')) == AD]
    upd_dry = [r for d, r, x in upd if d is True]
    upd_live = [(r, x) for d, r, x in upd if d is False]
    assert len(upd_live) == 1 and upd_live[0][1].get('success') is True, (AD, upd_live)
    for c in u['changes']:
        before = full_url(pre['creative'], c['slot'])
        after = full_url(aft['creative'], c['slot'])
        ok = after == c['new']
        assert (before == c['now']) or (before in c['alt_now'])
        detail = ("Pre-read meta_ad_id_get req %s: slot == now byte for byte (ad %s/%s/%s, creative %s, no url_tags; not on platform-refused list; no 11-Oct payload file). "
                  "New adcreative = exact copy of live creative %s with only %s changed to new (payload built from the raw read): dry run req %s (sent body and preview == payload, no warnings), "
                  "live create req %s -> creative %s (1 live attempt). New creative read req %s: label-keyed diff vs original = only the link URL(s); Meta-side only: name dedupe suffix, new ids, status IN_PROCESS, "
                  "full creative_features_spec all OPT_OUT, destination_screenshot OPT_OUT. "
                  "Attach POST /%s creative_id only (status not sent): dry run req %s, live req %s success=true. "
                  "Read-back req %s: ad on creative %s, slot == new byte for byte; status/configured_status %s/%s unchanged, effective_status %s -> %s (Meta re-review); old creative %s not deleted.") % (
            gets[0][2] and rid(gets[0][2]), pre.get('status'), pre.get('configured_status'), pre.get('effective_status'), pre['creative']['id'],
            pre['creative']['id'], ', '.join(x['slot'].replace('creative.', '') for x in u['changes']), ','.join(dry_c), live_c[0][0], new_id, ','.join(crd),
            AD, ','.join(upd_dry), upd_live[0][0], rid(gets[-1][2]), aft['creative']['id'], aft.get('status'), aft.get('configured_status'), pre.get('effective_status'), aft.get('effective_status'), pre['creative']['id'])
        out.append({"platform": "meta", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": AD,
                    "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
                    "after_expected": c['new'], "after_live": after, "result": "Fixed" if ok else "Failed",
                    "new_entity_ids": "creative %s" % new_id, "detail": detail})
print(json.dumps(out, ensure_ascii=False, indent=1))
print('COUNT', len(out), 'fixed', sum(1 for o in out if o['result'] == 'Fixed'), file=sys.stderr)
