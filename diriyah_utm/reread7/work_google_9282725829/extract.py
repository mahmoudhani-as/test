"""Extract google_ads search results for account 9282725829 from this subagent's transcript.
Writes one JSON file per successful GAQL call into <work>/res/<n>_<tool_use_id>.json:
  {"query": ..., "page_token": ..., "results": [...], "nextPageToken": ...}
Usage: python3 -I extract.py <transcript.jsonl> <work dir>
"""
import json, os, re, sys

TR, W = sys.argv[1], sys.argv[2]
OUT = os.path.join(W, 'res')
os.makedirs(OUT, exist_ok=True)

uses = {}
results = []
for line in open(TR):
    try:
        o = json.loads(line)
    except Exception:
        continue
    m = o.get('message')
    if not isinstance(m, dict):
        continue
    c = m.get('content')
    if not isinstance(c, list):
        continue
    for b in c:
        if b.get('type') == 'tool_use' and b.get('name', '').endswith('google_ads_native_action'):
            uses[b['id']] = b['input']
        elif b.get('type') == 'tool_result' and b.get('tool_use_id') in uses:
            results.append((b['tool_use_id'], b.get('content')))


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(x.get('text', '') for x in content if isinstance(x, dict))
    return ''


n = 0
summary = []
for i, (tid, content) in enumerate(results):
    inp = uses[tid]
    if inp.get('action') != 'google_ads_v23_google_ads_search':
        continue
    if inp.get('account_id') != '9282725829':
        continue
    txt = text_of(content)
    # persisted large output: harness message pointing to a file
    mm = re.search(r'(/root/\.claude/[^\s"\']+\.(?:txt|json))', txt)
    if not txt.lstrip().startswith('{') and mm:
        txt = open(mm.group(1)).read()
        # tool-results json files may be a list of content blocks
        try:
            j = json.loads(txt)
            if isinstance(j, list):
                txt = text_of(j)
        except Exception:
            pass
    try:
        j = json.loads(txt)
    except Exception as e:
        summary.append((i, tid, 'UNPARSEABLE', str(e)[:80]))
        continue
    if not j.get('success'):
        summary.append((i, tid, 'ERROR', json.dumps(j.get('error'))[:120]))
        continue
    d = j['data']['data']
    if not d.get('success', True):
        summary.append((i, tid, 'ERROR2', json.dumps(d)[:120]))
        continue
    dd = d.get('data', d)
    params = inp.get('params') or {}
    budget = (j.get('meta') or {}).get('mcp_output_budget') or {}
    truncated = bool(budget.get('truncated'))
    # the gateway also caps long arrays and appends a string marker like "[8 more items truncated]"
    markers = [x for x in dd.get('results', []) if not isinstance(x, dict)]
    if markers:
        truncated = True
        budget = dict(budget, item_markers=markers)
        dd['results'] = [x for x in dd['results'] if isinstance(x, dict)]
    rec = {'query': params.get('query'), 'page_token': params.get('page_token'),
           'results': dd.get('results', []), 'nextPageToken': dd.get('nextPageToken'),
           'totalResultsCount': dd.get('totalResultsCount'), 'truncated': truncated,
           'budget': budget}
    fn = os.path.join(OUT, f'{i:03d}_{tid}.json')
    json.dump(rec, open(fn, 'w'), ensure_ascii=False)
    n += 1
    summary.append((i, tid, 'TRUNCATED' if truncated else 'OK', len(rec['results']), bool(rec['nextPageToken']),
                    budget.get('serialized_bytes_before_budget'), (rec['query'] or '')[:300]))

for s in summary:
    print(*s)
print('saved', n)
