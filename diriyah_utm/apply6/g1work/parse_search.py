import json, sys
def load(path):
    raw = open(path).read()
    obj = json.loads(raw)
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and 'text' in obj[0]:
        obj = json.loads(''.join(x.get('text','') for x in obj))
    return obj
def rows(obj):
    d = obj
    while isinstance(d, dict) and 'results' not in d and 'data' in d:
        d = d['data']
    return d.get('results', []) if isinstance(d, dict) else []
def truncated(obj):
    m = obj.get('meta', {}).get('mcp_output_budget', {}) if isinstance(obj, dict) else {}
    return bool(m.get('truncated'))
def summarize(rs):
    out = {}
    bad = []
    for r in rs:
        if not isinstance(r, dict):
            bad.append(r); continue
        aga = r.get('adGroupAd', {})
        ad = aga.get('ad', {})
        out[ad.get('id')] = {
            'type': ad.get('type'),
            'final_urls': ad.get('finalUrls'),
            'final_url_suffix': ad.get('finalUrlSuffix'),
            'tracking_url_template': ad.get('trackingUrlTemplate'),
            'aga_status': aga.get('status'),
            'aga_rn': aga.get('resourceName'),
            'ad_group_id': r.get('adGroup', {}).get('id'),
            'ad_group_suffix': r.get('adGroup', {}).get('finalUrlSuffix'),
            'campaign_id': r.get('campaign', {}).get('id'),
            'campaign_status': r.get('campaign', {}).get('status'),
            'campaign_suffix': r.get('campaign', {}).get('finalUrlSuffix'),
        }
    return out, bad
if __name__ == '__main__':
    # usage: parse_search.py out.json in1.json [in2.json ...]
    allout = {}
    for p in sys.argv[2:]:
        obj = load(p)
        rs = rows(obj)
        out, bad = summarize(rs)
        print(p, 'rows', len(rs), 'parsed', len(out), 'non-dict', bad, 'truncated', truncated(obj))
        allout.update(out)
    json.dump(allout, open(sys.argv[1], 'w'), indent=1, ensure_ascii=False)
    print('total unique ads', len(allout))
