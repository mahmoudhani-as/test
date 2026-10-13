"""Merge GAQL ad_group_ad reads (saved MCP outputs) and check them against in_google_1.json.

usage: python3 check.py <mode pre|post> <unit ids comma-separated> <out.json> <read1.json> [read2.json ...]
Only the listed unit ids are reported; rows for other ads are ignored.
pre : classify each change as AlreadyFixed / WRITE / CHANGED from the live final_urls[0]
post: compare the live final_urls with ["new"] byte for byte (and suffix empty)
"""
import json
import sys
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9'


def same(a, b):
    if a == b:
        return True
    if a is None or b is None:
        return False
    A, B = urlsplit(a), urlsplit(b)
    return ((A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment)
            and sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True)))


def load_reads(paths):
    rows = {}
    for src in paths:
        raw = json.load(open(src))
        txt = raw[0]['text'] if isinstance(raw, list) else raw
        outer = json.loads(txt) if isinstance(txt, str) else txt
        meta = outer.get('meta', {})
        d = outer['data']['data']
        inner = d.get('data', d)
        results = inner.get('results', [])
        bad = [r for r in results if not isinstance(r, dict)]
        print(src.split('/')[-1], 'success', outer.get('success'), 'rows', len(results), 'truncated-items', bad,
              'requestId', meta.get('requestId'), 'budget-truncated', meta.get('mcp_output_budget', {}).get('truncated'))
        for r in results:
            if not isinstance(r, dict):
                continue
            aga = r['adGroupAd']
            ad = aga['ad']
            rec = {
                'final_urls': ad.get('finalUrls'), 'final_url_suffix': ad.get('finalUrlSuffix'),
                'tracking_url_template': ad.get('trackingUrlTemplate'), 'type': ad.get('type'),
                'aga_resource': aga.get('resourceName'), 'aga_status': aga.get('status'),
                'ag_suffix': r.get('adGroup', {}).get('finalUrlSuffix'), 'c_suffix': r.get('campaign', {}).get('finalUrlSuffix'),
                'campaign_status': r.get('campaign', {}).get('status'), 'request_id': meta.get('requestId'),
            }
            lst = rows.setdefault(ad['id'], [])
            if not any(x['aga_resource'] == rec['aga_resource'] for x in lst):
                lst.append(rec)
    return rows


def main():
    mode, ids, out = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
    rows = load_reads(sys.argv[4:])
    inp = {u['unit']: u for u in json.load(open(BASE + '/in_google_1.json'))}
    res = []
    for uid in ids:
        u = inp[uid]
        for c in u['changes']:
            rr = rows.get(uid) or []
            rec = {'unit': uid, 'slot': c['slot'], 'n_rows': len(rr)}
            if not rr:
                rec['class'] = 'NOT_FOUND'
                res.append(rec)
                continue
            r = rr[0]
            fu = r['final_urls'] or []
            cur = fu[0] if fu else None
            rec.update(cur=cur, n_final_urls=len(fu), suffix=r['final_url_suffix'], ag_suffix=r['ag_suffix'],
                       c_suffix=r['c_suffix'], tracking=r['tracking_url_template'], aga_status=r['aga_status'],
                       campaign_status=r['campaign_status'], request_id=r['request_id'],
                       all_rows_same=all(x['final_urls'] == r['final_urls'] for x in rr))
            if mode == 'pre':
                if same(cur, c['new']) and len(fu) == 1 and not r['final_url_suffix']:
                    rec['class'] = 'AlreadyFixed'
                elif cur == c['now'] or cur in (c.get('alt_now') or []):
                    rec['class'] = 'WRITE'
                else:
                    rec['class'] = 'CHANGED'
            else:
                ok = fu == [c['new']] and not r['final_url_suffix'] and not r['ag_suffix'] and not r['c_suffix'] and rec['all_rows_same']
                rec['class'] = 'VERIFIED' if ok else 'MISMATCH'
            res.append(rec)
    json.dump(res, open(out, 'w'), indent=1, ensure_ascii=False)
    from collections import Counter
    print(mode, 'units', len(ids), Counter(x['class'] for x in res))
    print('statuses', Counter((x.get('aga_status'), x.get('campaign_status')) for x in res))
    print('suffix/tracking present', [x['unit'] for x in res if x.get('suffix') or x.get('ag_suffix') or x.get('c_suffix') or x.get('tracking')])
    for x in res:
        if x['class'] not in ('WRITE', 'VERIFIED'):
            print('NOTE', json.dumps(x, ensure_ascii=False))


if __name__ == '__main__':
    main()
