import sys, re, json, collections, openpyxl
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nomen import Nomen

audit_path, gen_path, out_json = sys.argv[1:4]
N = Nomen(gen_path)
wb = openpyxl.load_workbook(audit_path)

def url_of(v):
    if not isinstance(v, str): return None
    m = re.search(r'(https?://|www\.)\S+', v)
    return m.group(0) if m else None

def hdr(ws, row=1):
    return {c.value: c.column for c in ws[row] if c.value}

ads = collections.OrderedDict()   # ad_id -> record
def rec(ad_id):
    ad_id = str(ad_id).strip()
    if ad_id not in ads:
        ads[ad_id] = {'ad_id': ad_id, 'history': []}
    return ads[ad_id]

ws = wb['URL Audit']; H = hdr(ws)
for r in range(2, ws.max_row + 1):
    g = lambda k: ws.cell(r, H[k]).value
    if not g('Ad ID'): continue
    a = rec(g('Ad ID'))
    a.update(platform=g('Platform'), account=g('Account'), campaign=g('Campaign name'),
             adset=g('Ad set name'), adset_id=g('Ad set / Squad / Ad group / Line item ID'), ad_name=g('Ad name'), status=g('Status'),
             outcome=g('Outcome'), audit_row=r, campaign_id=g('Campaign ID'))
    b = url_of(g('Final URL - BEFORE')); af = url_of(g('Final URL - AFTER (applied) / expected'))
    if b: a['history'].append(('URL Audit BEFORE', r, b, False))
    if af: a['history'].append(('URL Audit AFTER', r, af, True))
    act = g('6-Oct rollout - action') or ''
    m = re.search(r'URL now:\s*(\S+)', act)
    if m: a['history'].append(('URL Audit 6-Oct URL now', r, m.group(1), True))

ws = wb['ID Mapping Fix']; H = hdr(ws)
for r in range(2, ws.max_row + 1):
    g = lambda k: ws.cell(r, H[k]).value
    if not g('Ad ID'): continue
    a = rec(g('Ad ID')); a.setdefault('platform', g('Platform'))
    af = url_of(g('Final URL - AFTER (blank = unchanged)'))
    if af: a['history'].append(('ID Mapping Fix AFTER', r, af, True))

ws = wb['Rollout 6-Oct']; H = hdr(ws)
for r in range(2, ws.max_row + 1):
    g = lambda k: ws.cell(r, H[k]).value
    if not g('Ad ID'): continue
    a = rec(g('Ad ID'))
    for k, v in (('platform', 'Platform'), ('campaign', 'Campaign name'), ('adset', 'Ad set / Squad / Ad group / Line item'), ('ad_name', 'Ad name - BEFORE')):
        a.setdefault(k, g(v))
    if g('Ad name - AFTER (blank = unchanged)'): a['ad_name_after'] = g('Ad name - AFTER (blank = unchanged)')
    a['rollout_result'] = g('Result (re-checked live)')
    b = url_of(g('Final URL - BEFORE')); af = url_of(g('Final URL - AFTER'))
    if b and not a['history']: a['history'].append(('Rollout BEFORE', r, b, False))
    if af: a['history'].append(('Rollout 6-Oct AFTER', r, af, True))

ws = wb['Decisions 6-Oct']; H = hdr(ws)
for r in range(2, ws.max_row + 1):
    g = lambda k: ws.cell(r, H[k]).value
    cid = str(g('Ad / campaign ID') or '')
    if not cid or 'campaign' in cid: continue
    a = rec(cid); a.setdefault('platform', g('Platform'))
    if g('Name - AFTER (blank = unchanged)'): a['ad_name_after'] = g('Name - AFTER (blank = unchanged)')
    af = url_of(g('Final URL - AFTER'))
    if af: a['history'].append(('Decisions 6-Oct AFTER', r, af, True))

ws = wb['Google 7-Oct']; H = hdr(ws)
for r in range(2, ws.max_row + 1):
    g = lambda k: ws.cell(r, H[k]).value
    if not g('Ad ID'): continue
    a = rec(g('Ad ID')); a.setdefault('platform', 'Google Ads'); a.setdefault('campaign', g('Campaign')); a.setdefault('adset', g('Ad group'))
    b = url_of(g('Final URL - BEFORE')); af = url_of(g('Final URL - AFTER'))
    if b and not a['history']: a['history'].append(('Google BEFORE', r, b, False))
    if af: a['history'].append(('Google 7-Oct AFTER', r, af, True))

RANK = {'URL Audit BEFORE': 0, 'Rollout BEFORE': 0, 'Google BEFORE': 0, 'URL Audit AFTER': 1, 'ID Mapping Fix AFTER': 1,
        'URL Audit 6-Oct URL now': 2, 'Rollout 6-Oct AFTER': 2, 'Decisions 6-Oct AFTER': 2, 'Google 7-Oct AFTER': 3}
for a in ads.values():
    a['history'].sort(key=lambda x: RANK[x[0]])
    h = a['history']
    a['final_url'] = h[-1][2] if h else None
    a['final_src'] = h[-1][0] if h else None
    a['claude_wrote_final'] = bool(h and h[-1][3])
    a['claude_touched'] = any(x[3] for x in h)
    a['errors'] = N.check(a['final_url']) if a['final_url'] else []
    # every URL Claude wrote at any point
    a['claude_urls'] = [(s, r, u, N.check(u)) for s, r, u, w in h if w]

json.dump(list(ads.values()), open(out_json, 'w'), indent=1, default=str)
print('ads', len(ads))
