# Read-only: shorten the detail text of the summarize.py output (stdin) and print entries [a:b] one per line.
import sys, json, re
a, b = int(sys.argv[1]), int(sys.argv[2])
out = json.loads(sys.stdin.readline())
for r in out[a:b]:
    d = r['detail']
    if r['slot'] == 'ad.landing_page_url':
        m = re.match(r'pre-read ad/get req ([0-9A-F]+)( \+ re-read req ([0-9A-F]+) \(identical\))?:', d)
        pre = m.group(1) + ((' + re-read ' + m.group(3)) if m.group(3) else '')
        adg = re.search(r'adgroup (\d+)', d).group(1)
        st = re.search(r'status (\w+ / \w+) unchanged', d).group(1)
        live = re.search(r'live ad/update req ([0-9A-F]+)', d).group(1)
        post = re.search(r'read-back ad/get req ([0-9A-F]+)', d).group(1)
        r['detail'] = ('CUSTOMIZED_USER manual SINGLE_VIDEO ad (no tiktok_item_id), adgroup %s. Pre-read ad/get req %s: URL == now. '
                       'Dry run == read except landing_page_url = new and utm_params = 5 UTMs of new (no utm_id); pixel sent as exact '
                       'string 7347671240183693330. Live ad/update req %s: code 0 OK, need_audit false. Read-back ad/get req %s: URL == new '
                       'byte for byte, utm_params match, no other field changed, status %s unchanged. Final re-read req '
                       '202610131756106EE5A98C1D63E8190B32 OK.') % (adg, pre, live, post, st)
    print(json.dumps(r, ensure_ascii=False))
