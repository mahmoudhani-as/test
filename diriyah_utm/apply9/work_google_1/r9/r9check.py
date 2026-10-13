"""usage: python3 r9check.py <pre|post> <out.json> <raw1.json> [raw2.json ...]
Reads saved GAQL ad_group_ad outputs (MCP text wrapper or plain JSON) and classifies every change of in_google_1.json."""
import json, sys
from collections import Counter
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


def load(paths):
    rows = {}
    for src in paths:
        raw = json.load(open(src))
        txt = raw[0]['text'] if isinstance(raw, list) else raw
        outer = json.loads(txt) if isinstance(txt, str) else txt
        meta = outer.get('meta', {})
        d = outer['data']['data']
        inner = d.get('data', d)
        res = inner.get('results', [])
        print(src.split('/')[-1], 'success', outer.get('success'), 'rows', len(res), 'nondict', [r for r in res if not isinstance(r, dict)],
              'requestId', meta.get('requestId'), 'budget', meta.get('mcp_output_budget'))
        for r in res:
            if not isinstance(r, dict):
                continue
            aga = r['adGroupAd']; ad = aga['ad']
            rec = dict(final_urls=ad.get('finalUrls'), suffix=ad.get('finalUrlSuffix'), tracking=ad.get('trackingUrlTemplate'),
                       type=ad.get('type'), aga=aga.get('resourceName'), aga_status=aga.get('status'),
                       ag_suffix=r.get('adGroup', {}).get('finalUrlSuffix'), ag_tracking=r.get('adGroup', {}).get('trackingUrlTemplate'),
                       c_suffix=r.get('campaign', {}).get('finalUrlSuffix'), c_tracking=r.get('campaign', {}).get('trackingUrlTemplate'),
                       c_status=r.get('campaign', {}).get('status'), request_id=meta.get('requestId'))
            lst = rows.setdefault(ad['id'], [])
            if not any(x['aga'] == rec['aga'] for x in lst):
                lst.append(rec)
    return rows


def main():
    mode, out = sys.argv[1], sys.argv[2]
    rows = load(sys.argv[3:])
    inp = json.load(open(BASE + '/in_google_1.json'))
    res = []
    for u in inp:
        for c in u['changes']:
            rr = rows.get(u['unit']) or []
            rec = {'unit': u['unit'], 'slot': c['slot'], 'n_rows': len(rr)}
            if not rr:
                rec['class'] = 'NOT_FOUND'; res.append(rec); continue
            r = rr[0]
            fu = r['final_urls'] or []
            cur = fu[0] if fu else None
            rec.update(cur=cur, n_final_urls=len(fu), suffix=r['suffix'], tracking=r['tracking'], ag_suffix=r['ag_suffix'],
                       c_suffix=r['c_suffix'], ag_tracking=r['ag_tracking'], c_tracking=r['c_tracking'], type=r['type'],
                       aga_status=r['aga_status'], c_status=r['c_status'], request_id=r['request_id'],
                       all_rows_same=all(x['final_urls'] == r['final_urls'] and x['suffix'] == r['suffix'] for x in rr))
            parent_suffix = bool(r['ag_suffix'] or r['c_suffix'])
            if mode == 'pre':
                if parent_suffix:
                    rec['class'] = 'PARENT_SUFFIX'
                elif same(cur, c['new']) and len(fu) == 1 and not r['suffix'] and rec['all_rows_same']:
                    rec['class'] = 'AlreadyFixed'
                elif (cur == c['now'] or cur in (c.get('alt_now') or [])) and rec['all_rows_same']:
                    rec['class'] = 'WRITE'
                else:
                    rec['class'] = 'CHANGED'
            else:
                ok = fu == [c['new']] and not r['suffix'] and not parent_suffix and rec['all_rows_same']
                rec['class'] = 'VERIFIED' if ok else 'MISMATCH'
            res.append(rec)
    json.dump(res, open(out, 'w'), indent=1, ensure_ascii=False)
    print(mode, 'changes', len(res), Counter(x['class'] for x in res))
    print('statuses', Counter((x.get('aga_status'), x.get('c_status')) for x in res))
    print('types', Counter(x.get('type') for x in res))
    print('suffix/tracking present', [x['unit'] for x in res if x.get('suffix') or x.get('ag_suffix') or x.get('c_suffix') or x.get('tracking') or x.get('ag_tracking') or x.get('c_tracking')])
    print('multi final_urls', [x['unit'] for x in res if x.get('n_final_urls', 1) != 1], 'multi rows', [x['unit'] for x in res if x.get('n_rows', 1) > 1])
    for x in res:
        print(x['unit'], x['class'])


if __name__ == '__main__':
    main()
