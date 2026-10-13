import json, sys
# usage: parse_read.py out.json in1.json [in2.json ...]  (merges GAQL ad_group_ad reads, exact strings)
dst, srcs = sys.argv[1], sys.argv[2:]
rows = {}
for src in srcs:
    raw = json.load(open(src))
    txt = raw[0]['text'] if isinstance(raw, list) else raw
    outer = json.loads(txt) if isinstance(txt, str) else txt
    d = outer['data']['data']
    inner = d.get('data', d)
    results = inner.get('results', [])
    trunc = [r for r in results if not isinstance(r, dict)]
    print(src.split('/')[-1], 'success', outer.get('success'), 'rows', len(results), 'non-dict', trunc, 'requestId', outer.get('meta', {}).get('requestId'), 'budget', outer.get('meta', {}).get('mcp_output_budget', {}).get('truncated'))
    for r in results:
        if not isinstance(r, dict):
            continue
        aga = r['adGroupAd']; ad = aga['ad']
        rec = {
            'ad_id': ad['id'], 'type': ad.get('type'), 'final_urls': ad.get('finalUrls'),
            'final_url_suffix': ad.get('finalUrlSuffix'), 'tracking_url_template': ad.get('trackingUrlTemplate'),
            'aga_resource': aga.get('resourceName'), 'aga_status': aga.get('status'), 'ad_group_id': r.get('adGroup', {}).get('id'),
            'ag_suffix': r.get('adGroup', {}).get('finalUrlSuffix'), 'ag_tracking': r.get('adGroup', {}).get('trackingUrlTemplate'),
            'campaign_id': r.get('campaign', {}).get('id'), 'campaign_status': r.get('campaign', {}).get('status'),
            'c_suffix': r.get('campaign', {}).get('finalUrlSuffix'), 'c_tracking': r.get('campaign', {}).get('trackingUrlTemplate'),
            'request_id': outer.get('meta', {}).get('requestId'),
        }
        lst = rows.setdefault(ad['id'], [])
        if not any(x['aga_resource'] == rec['aga_resource'] for x in lst):
            lst.append(rec)
        else:
            for x in lst:
                if x['aga_resource'] == rec['aga_resource'] and x['final_urls'] != rec['final_urls']:
                    print('INCONSISTENT between reads', ad['id'], x['final_urls'], rec['final_urls'])
json.dump(rows, open(dst, 'w'), indent=1, ensure_ascii=False)
print('distinct ads', len(rows), 'multi-row ads', [k for k, v in rows.items() if len(v) > 1])
