# Read-only: build one result object per change from THIS agent's own transcript (byte-exact). Prints JSON; writes no results file.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply10/work_tiktok_1')
from common import *
from build import build

R = ad_reads()
out = []
for u in INP:
    ad = u['unit']
    b = build(ad)
    ch, a = b['ch'], b['a']
    ups = [(i, tid, inp, txt, err) for i, tid, inp, txt, err in calls('tiktok_ad_update')
           if ((inp.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
    dry = [x for x in ups if x[2].get('dry_run', True) is not False]
    live = [x for x in ups if x[2].get('dry_run') is False]
    rec = {"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": ad, "ad_ids": u['ad_ids'],
           "ad_names": u['ad_names'], "slot": ch['slot'], "before": b['cur'], "after_expected": ch['new'], "new_entity_ids": ""}
    if live:
        lj = result_json(live[-1][3]) or {}
        ld = (lj.get('data') or {}).get('data') or {}
        post = [r for r in (R.get(ad) or []) if r[0] > live[-1][0]]
        prid, pa = post[-1][1], post[-1][2]
        eff, extra, conflict = eff_url(pa.get('landing_page_url'), pa.get('utm_params'))
        other = {k for k in set(a) | set(pa) if k not in ('landing_page_url', 'utm_params', 'modify_time') and a.get(k) != pa.get(k)}
        ok = eff == ch['new'] and pa.get('landing_page_url') == ch['new'] and not other
        rec['after_live'] = eff
        rec['result'] = 'Fixed' if ok else 'Failed'
        rec['_info'] = dict(pre_rid=b['rid'], live_n=len(live), dry_n=len(dry), live_rid=ld.get('request_id'), code=ld.get('code'),
                            gw=(lj.get('meta') or {}).get('requestId'), need_audit=(ld.get('data') or {}).get('need_audit'),
                            post_rid=prid, other=sorted(other), mt=(a.get('modify_time'), pa.get('modify_time')),
                            utm=[(x['key'], x['value']) for x in pa.get('utm_params') or []], status=(pa.get('operation_status'), pa.get('secondary_status')))
    else:
        rec['after_live'] = b['cur']
        rec['result'] = 'NotAttempted'
        rec['_info'] = dict(pre_rid=b['rid'], live_n=0, dry_n=len(dry))
    out.append(rec)
print(json.dumps(out, ensure_ascii=False, indent=1))
