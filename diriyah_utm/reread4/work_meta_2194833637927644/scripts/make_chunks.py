"""Plan id chunks for the detail reads, sized from the previous (reread3) detail records so each MCP result stays well under ~65KB.
Usage: make_chunks.py IN_FILE PREV_DETAILS OUT_JSON BUDGET_BYTES"""
import json, sys
IN_FILE, PREV, OUT, BUDGET = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
rows = json.load(open(IN_FILE, encoding='utf-8'))
inv = json.load(open('data/inventory.json', encoding='utf-8'))
prev = json.load(open(PREV, encoding='utf-8'))
in_ids = []
for r in rows:
    if r['ad_id'] not in in_ids:
        in_ids.append(r['ad_id'])
new_ids = [a for a in inv if a not in set(in_ids) and inv[a]['effective_status'] != 'DELETED']

def est(aid):
    p = prev.get(aid)
    if not p:
        return 2600
    s = json.dumps(p, indent=2, ensure_ascii=False)
    # pretty-printed inside the MCP envelope at depth ~5 (10 extra spaces per line) + some growth margin
    return int((len(s.encode('utf-8')) + 10 * s.count('\n')) * 1.25) + 300

chunks = []
cur, size = [], 0
for aid in in_ids:
    e = est(aid)
    if cur and (size + e > BUDGET or len(cur) >= 40):
        chunks.append(cur); cur, size = [], 0
    cur.append(aid); size += e
if cur:
    chunks.append(cur)
STAT = ["ACTIVE", "PAUSED", "PENDING_REVIEW", "DISAPPROVED", "PREAPPROVED", "PENDING_BILLING_INFO", "CAMPAIGN_PAUSED", "ARCHIVED", "ADSET_PAUSED", "IN_PROCESS", "WITH_ISSUES", "DELETED"]
plan = {'input_chunks': chunks, 'new_ids': new_ids, 'status_filter': STAT}
json.dump(plan, open(OUT, 'w'), indent=1)
for i, c in enumerate(chunks):
    print(i, len(c), sum(est(a) for a in c))
print('new', len(new_ids))
