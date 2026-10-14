"""Final verification workbook (12-Oct): before vs after %, every URL with its ad name, changes applied, what still needs the
user (not applied / manual), what was left out per URL, month check, questions, 7-Oct sheet audit, rules.
Usage: python3 scripts/build_final2.py <dir> <out.xlsx> [reread folder] [plan folder]
Reads: work/scored.json (11-Oct inventory = before), work/targets.json (final rules), work/live_now.json (keyed re-read = after),
       reread/out/new_*.jsonl (ads created since 11-Oct), apply*/out_*.jsonl (every write), round4/diff.json (pending plan), omit / legacy items."""
import sys, os, json, re, glob, collections
from urllib.parse import urlsplit, parse_qsl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.formatting.rule import FormulaRule
from derive import Deriver
from omit import check_omit

W, OUT = sys.argv[1], sys.argv[2]
REREAD = sys.argv[3] if len(sys.argv) > 3 else 'reread'   # folder of the latest keyed re-read (its out/new_*.jsonl = ads created since 11-Oct)
PLAN = sys.argv[4] if len(sys.argv) > 4 else 'round4'      # folder of the latest pending plan (diff.json)
APPLY = os.environ.get('APPLY') or PLAN                      # folder(s) of the final apply run, comma-separated (e.g. apply6,apply7 = run + resume)
APPLY_LIST = [x.strip() for x in APPLY.split(',') if x.strip()]
in_apply = lambda f: any(f.startswith(a + '/') for a in APPLY_LIST)
FPLAN = {}   # the final run's plan: slot -> plan row (url_now at the pause); used for writes whose result line could not be recorded
if os.path.exists(f'{W}/{APPLY_LIST[0]}/diff.json'):
    for d_ in json.load(open(f'{W}/{APPLY_LIST[0]}/diff.json')): FPLAN[(d_['platform'], str(d_['ad_id']), d_['slot'])] = d_
SPARK_PUSH = set(json.load(open(f'{W}/work/spark_check/spark_push_plan_ids.json'))['ad_ids']) if os.path.exists(f'{W}/work/spark_check/spark_push_plan_ids.json') else set()
LANE = {}   # slot -> stop reason of the final-run batch that held it (from <apply>/lane_reports.json), for units the agent never wrote a result line for
for ap in APPLY_LIST:
    rp = f'{W}/{ap}/lane_reports.json'
    if not os.path.exists(rp): continue
    reps = json.load(open(rp))
    for f_ in glob.glob(f'{W}/{ap}/in_*.json'):
        se = (reps.get(os.path.basename(f_)) or {}).get('systemic_error') or ''
        for u_ in json.load(open(f_)):
            for ch_ in u_['changes']:
                for a_ in u_['ad_ids']: LANE[(u_['platform'], str(a_), ch_['slot'])] = (ap + '/' + os.path.basename(f_), se)
def lane_status(k):
    b_, se = LANE.get(k, ('', ''))
    if re.search(r'safety check|SAFETY|BLOCKED|classifier', se):
        return BL, ('not written: the final-run batch ' + b_ + ' stopped after the session safety check denied a step. ' + se)[:400]
    if re.search(r'PERMISSION|Page permission', se):
        return RF, ('not written: the platform refused the batch ' + b_ + '. ' + se)[:400]
    if re.search(r'OUTAGE|timed out|51002|Service Unavailable', se):
        return PENDING, ('not written: a TikTok API outage stopped the batch ' + b_ + ' (re-run later). ' + se)[:400]
    if re.search(r'^AUTH:|sign in again', se):
        return PENDING, ('not written: Whathead asked to sign in again (batch ' + b_ + '). ' + se)[:400]
    return None
DAY_OF = lambda f: '11-Oct' if re.search(r'(^|/)apply2?/', f) else '13-Oct' if re.search(r'(^|/)apply(8|9|1[0-9])/', f) else '12-Oct'
APN = lambda f: (int(re.match(r'apply(\d*)', os.path.relpath(f, W)).group(1) or 1), f)   # apply folders in run order (apply10-12 after apply9)
A13 = ('apply8', 'apply9', 'apply10', 'apply11', 'apply12', 'apply13')   # the 13-Oct runs
A8 = set()   # slots of the 13-Oct runs (apply8 = approved writes the 12-Oct run never reached, apply9 = after the permission rules, apply10-12 = retries and your approvals)
A9NOW = {}  # apply9 plan 'now' per (platform, unit, slot): the before of writes made by the stopped first apply9 runs
for ap_ in [a for a in A13 if a in APPLY_LIST]:
    for f_ in glob.glob(f'{W}/{ap_}/in_*.json'):
        for u_ in json.load(open(f_)):
            for ch_ in u_['changes']:
                for a_ in u_['ad_ids']: A8.add((u_['platform'], str(a_), ch_['slot']))
                if ap_ == 'apply9': A9NOW[(u_['platform'], str(u_['unit']), ch_['slot'])] = ch_['now']
WADI = {}   # Wadi Safar Meta slots: Meta refuses that Page / Instagram for this connection (re-tested 13-Oct)
WADI_FILE = os.environ.get('WADI_FILE') or 'work/wadi_safar_meta_needs_page.json'
if os.path.exists(f'{W}/{WADI_FILE}'):
    for e in json.load(open(f'{W}/{WADI_FILE}')): WADI[(e['platform'], str(e['ad_id']), e['slot'])] = e['why']
SNAPSPLIT = set()   # Snapchat shared sub-creatives the 13-Oct run tried to split (Snapchat refuses to move an ad to another creative: E1008)
for f_ in glob.glob(f'{W}/apply11/in_snapchat_snap_split_*.json') if 'apply11' in APPLY_LIST else []:
    for u_ in json.load(open(f_)):
        for ch_ in u_['changes']:
            for a_ in u_['ad_ids']: SNAPSPLIT.add((u_['platform'], str(a_), ch_['slot']))
STORY13 = set()   # Snapchat Story ads whose own composite was tried on 13-Oct (apply13): E2003
for f_ in glob.glob(f'{W}/apply13/in_snapchat_*.json') if 'apply13' in APPLY_LIST else []:
    for u_ in json.load(open(f_)):
        for ch_ in u_['changes']:
            for a_ in u_['ad_ids']: STORY13.add((u_['platform'], str(a_), ch_['slot']))
E2003 = (' The 6 Story ads were also tried inside their own Story creative (copies of the shared sub-creatives): Snapchat refused that too '
         '(E2003 "Property could not be updated after the Ad is in flight: creative_ids"), and you chose not to create new ads.')
E1008 = (' On 13-Oct, after your approval to split them: Snapchat refuses to move an existing ad to a copied creative (E1008 "This field cannot be updated. Field creativeId"), '
         'so the split cannot be done through the API without creating new ads (not approved). Copies made before the stop are unattached and were not deleted.')
UNREC8 = 'written on 13-Oct; the agent returned no verified result for it - confirmed by the final re-read'
UNREC = 'written on 12-Oct by the final run; its result line could not be recorded (the session safety check denied the local logging step) - confirmed by the final re-read'
PENDING = os.environ.get('PENDING_LABEL') or 'Being applied now'   # e.g. 'Paused - not yet written'
G = glob.glob(f'{W}/in/e2e*.xlsx')[0]
N = Deriver(G, {}).N
S = json.load(open(f'{W}/work/scored.json'))
T = {(r['platform'], r['ad_id'], r['slot']): r for r in json.load(open(f'{W}/work/targets.json'))}
LIVE_FILE = os.environ.get('LIVE_FILE') or f'{W}/work/live_now.json'   # e.g. work/live_interim.json = re-read + later apply read-backs
LIVE = json.load(open(LIVE_FILE)) if os.path.exists(LIVE_FILE) else {}
DIFF = {(d['platform'], d['ad_id'], d['slot']): d for d in json.load(open(f'{W}/{PLAN}/diff.json'))}
PMAN = {}   # the plan's manual list: tweet-text links, shared sub-creatives needing different URLs
for m in json.load(open(f'{W}/{PLAN}/manual.json')):
    for aid in ([m['ad_id']] if m.get('ad_id') else m.get('ad_ids') or []):
        for sl_ in ([m['slot']] if m.get('slot') else [c_['slot'] for c_ in m.get('changes') or []]):
            PMAN[(m['platform'], str(aid), sl_)] = m.get('manual') if isinstance(m.get('manual'), str) else 'shared creative used by ads that need different URLs - split it by hand'
FS = json.load(open(f'{W}/work/first_serving_all.json'))
key = lambda s: (s['platform'], str(s.get('ad_id')), s.get('slot'))
OMIT = {key(o): o for o in json.load(open(f'{W}/work/omit_items.json'))}
LEG = {key(i): i for i in json.load(open(f'{W}/work/legacy_clash_items.json'))}
MONTHFIX = {(f['platform'], f['ad_id'], f['slot']): f for f in json.load(open(f'{W}/work/month_fixes.json'))}
norm = lambda u: (lambda p: (p.scheme, p.netloc.lower(), p.path, p.fragment, tuple(sorted(parse_qsl(p.query, keep_blank_values=True)))))(urlsplit((u or '').strip()))
same = lambda a, b: a is not None and b is not None and norm(a) == norm(b)
MAIN_SESSION = {('google', '812832821725'), ('google', '812832821731')}   # written from the main session on 12-Oct (see notes)
FINAL = bool(os.environ.get('FINAL'))       # final build: every approved write has been run (no pause / no queue)
RF, BL, HELD = 'Refused by the platform', 'Blocked by safety check', 'Held - your decision'
REFUSED = {}   # slots a platform refuses through its API (never retried): REFUSED_FILE=comma-separated json lists [{platform, ad_id, slot, why}]
for rf_ in (os.environ.get('REFUSED_FILE') or 'work/excl_platform_refused_v2.json').split(','):
    if os.path.exists(f'{W}/{rf_}'):
        for e in json.load(open(f'{W}/{rf_}')): REFUSED[(e['platform'], str(e['ad_id']), e['slot'])] = e.get('why') or ''
REFUSE_RX = re.compile(r'Spark Pull|editable only in Ads Manager|(?<!not )archived|POLICY_FINDING|PROHIBITED|disapproved|requires? an Instagram|Instagram account|https?://t\.co/|t\.co link|Page/profile permission|Page permission|required_permission|interactive components|interactive_components_spec|2446581|Media Not Wide Enough|2875006', re.I)
RUN_LABEL = lambda f: {'apply': '11-Oct', 'apply2': '11-Oct', 'apply3': '11-Oct', 'apply4': '12-Oct', 'apply5': '12-Oct (before the pause)',
                       'apply6': '12-Oct (final run)', 'apply7': '12-Oct (final run, resumed 22:00 UTC)', 'apply8': '13-Oct (approved writes not reached on 12-Oct)',
                       'apply9': '13-Oct (after your permission rules: writes the safety check had blocked)',
                       'apply10': '13-Oct (retries of transient failures)',
                       'apply11': '13-Oct (your approvals: Spark Push, carousels, fix everything you can)',
                       'apply12': '13-Oct (fix everything you can: ad held over a text trim)',
                       'apply13': '13-Oct (your Snapchat split, done inside each ad\'s own Story creative)'}.get(f.split('/')[0], '12-Oct (final run)')
NONAME = lambda p: '(Google ads have no name)' if p == 'google' else '(no ad name)'

# ---------- every write ----------
runs = collections.defaultdict(list)
for f in sorted(glob.glob(f'{W}/apply*/out_*.jsonl'), key=APN):
    day = DAY_OF(f)
    for line in open(f):
        if not line.strip(): continue
        try: a = json.loads(line)
        except Exception: continue
        a['_day'] = day; a['_file'] = os.path.relpath(f, W)
        for aid in a.get('ad_ids') or []:
            runs[(a['platform'], str(aid), a.get('slot'))].append(a)
        if a.get('unit_type') == 'sitelink_asset':      # one asset = every placement
            for k in T:
                if k[0] == 'google' and k[2].split(' final')[0] == 'sitelink asset ' + str(a['unit']): runs[k].append(a)

OFF = re.compile(r'PAUSED|DISABLE|INVALID|NOT_SERVING|REJECTED|DONE|ARCHIVED|REMOVED|ENDED|COMPLETED|DRAFT|HOLD', re.I)
def is_on(s, status=None):
    st = status if status is not None else (s.get('effective_status') or s.get('ad_status'))
    for k in ('campaign_status', 'adset_status'):
        v = s.get(k)
        if v is not None and not re.match(r'\s*(ACTIVE|ENABLE|ENABLED|SERVING)', str(v), re.I): return False
    return bool(st) and not OFF.search(str(st))

def wrong_before(s):
    return '\n'.join(m for _, m in (s.get('violations') or [])) or ('; '.join(s.get('derive_reasons') or []))

def status_of(s, t, live):
    """-> status, detail, changed_on"""
    k = key(s); tgt = (t or {}).get('target')
    rs = runs.get(k, [])
    last12 = [a for a in rs if a['_day'] == '12-Oct']
    if live is None: return 'Not re-read', 'the final re-read did not return this slot', ''
    if live.get('found') is False: return 'Gone', live.get('note') or 'ad / slot no longer exists', ''
    url = live.get('url')
    if tgt and same(url, tgt):
        if FINAL and (k in A8 or any(a['_day'] == '13-Oct' for a in rs)):    # 13-Oct runs (sitelink placements are keyed per placement, not in A8)
            l8 = [a for a in rs if a['_day'] == '13-Oct']
            if any(a['result'] == 'Fixed' for a in l8): return 'Fixed 13-Oct', next(a.get('detail') or '' for a in l8 if a['result'] == 'Fixed')[:300], '13-Oct'
            if any(a['result'] == 'AlreadyFixed' and '/apply9/' in '/' + a['_file'] for a in l8):
                return 'Fixed 13-Oct', ('written on 13-Oct by the first apply9 run (stopped and restarted after the switch to Accept edits); the restarted run found it correct. ' + next(a.get('detail') or '' for a in l8 if a['result'] == 'AlreadyFixed'))[:300], '13-Oct'
            if l8 and l8[-1]['result'] == 'AlreadyFixed': return 'Correct', 'already correct when re-read on 13-Oct before the write (no write needed)', ''
            return 'Fixed 13-Oct', (UNREC8 + ('. Agent result: ' + (l8[-1].get('detail') or '') if l8 else ''))[:400], '13-Oct'
        if (s['platform'], str(s.get('ad_id'))) in MAIN_SESSION: return 'Fixed 12-Oct', 'written from the main session (agent stopped by the safety check)', '12-Oct'
        if any(a['result'] in ('Fixed',) for a in last12): return 'Fixed 12-Oct', next(a.get('detail') for a in last12 if a['result'] == 'Fixed')[:300], '12-Oct'
        if FINAL and any(a['result'] == 'AlreadyFixed' and in_apply(a['_file']) for a in rs):
            return 'Fixed 12-Oct', 'already correct when the final run re-read it (no write needed): written earlier on 12-Oct by the run that was paused before it recorded the result', '12-Oct'
        if FINAL and k in FPLAN: return 'Fixed 12-Oct', UNREC, '12-Oct'
        if any(a['result'] == 'Fixed' for a in rs): return 'Fixed 11-Oct', 'written 11-Oct and still matches the final rules', '11-Oct'
        if any(a['result'] == 'AlreadyFixed' for a in last12): return 'Fixed 11-Oct', 'already correct when re-read before the 12-Oct write', '11-Oct'
        return 'Correct', 'live URL already matches the final rules', ''
    if t and t.get('manual'): return 'Manual - you', ((t['manual'].rstrip('. ') + '.' + E1008 + (E2003 if k in STORY13 else '')) if k in SNAPSPLIT else t['manual'])[:800], ''
    if k in PMAN: return 'Manual - you', ((PMAN[k].rstrip('. ') + '.' + E1008 + (E2003 if k in STORY13 else '')) if k in SNAPSPLIT else PMAN[k])[:800], ''
    if not tgt:
        o = OMIT.get(k) or {}
        return 'Manual - you', (o.get('manual') or 'no single correct URL for this slot'), ''
    if FINAL and k in WADI: return RF, WADI[k][:800], ''
    if k in REFUSED: return RF, ('the platform refused this edit through its API (never retried): ' + REFUSED[k])[:400], ''
    a5 = [a for a in rs if in_apply(a['_file'])]
    if FINAL and rs and rs[-1]['result'] == 'Fixed' and rs[-1]['_day'] == '13-Oct':   # written and read back on 13-Oct, yet the final re-read differs
        return 'Failed', ('written and read back on 13-Oct, but the final re-read shows another URL (changed afterwards, e.g. by the platform): ' + (rs[-1].get('detail') or ''))[:400], ''
    if FINAL and s['platform'] == 'tiktok' and str(s.get('ad_id')) in SPARK_PUSH and not any(a['_day'] == '13-Oct' for a in rs):
        return HELD, 'TikTok Spark Push ad (brand-account post), held for your decision: an API URL edit makes TikTok re-publish the post 30-60 min later and detach the ad from the original post (55 ads were affected by the 11/12-Oct writes)', ''
    last_b = LANE.get(k, ('', ''))[0]
    no_line_in_last = bool(last_b) and not any(a['_file'] == last_b.replace('/in_', '/out_').replace('.json', '.jsonl') for a in rs)
    if FINAL and k in DIFF and (not a5 or no_line_in_last) and lane_status(k): return lane_status(k) + ('',)
    if k in DIFF and not a5: return PENDING, ('reviewed URL ready; not written: the final run has no write result for it' if FINAL else 'reviewed URL ready; the writes were paused before this one was reached' if PENDING != 'Being applied now' else 'reviewed URL is in the write queue that was still running when this workbook was built'), ''
    bad = [a for a in (a5 or last12) if a['result'] in ('Failed', 'Skipped', 'NotAttempted')]
    if bad:
        b = bad[-1]; d = (b.get('detail') or '')
        if FINAL and re.search(r'Spark Push', d) and b['result'] == 'NotAttempted':
            return HELD, ('TikTok Spark Push ad, held for your decision: an API URL edit makes TikTok re-publish the post and detach the ad from the original post. ' + d)[:400], ''
        if FINAL and re.search(r'safety check', d, re.I):
            return BL, ('approved and reviewed, but this session\'s safety check stopped the live write: ' + d)[:400], ''
        if FINAL and REFUSE_RX.search(d) and not re.search(r'sign-?in|re-?authent', d, re.I):
            return RF, 'the platform does not allow this edit through its API: ' + d[:300], ''
        if FINAL and (b['result'] == 'NotAttempted' or re.search(r'sign-?in|re-?authent', d, re.I)):
            return PENDING, ('not written yet: ' + ('Whathead asked to sign in again before this write. ' if re.search(r'sign-?in|re-?authent', d, re.I) else '') + d)[:400], ''
        if b['result'] == 'NotAttempted' or re.search(r'safety check|sign-?in', d, re.I):
            return 'Not applied - needs your OK', ('not written: ' + d)[:400] if FINAL else 'planned and reviewed, not written: the session safety check stopped this live write', ''
        if REFUSE_RX.search(d):
            return (RF if FINAL else 'Manual - you'), 'the platform does not allow this edit through its API: ' + d[:300], ''
        if FINAL and re.search(r'existing (Facebook )?Page post|stored on the post itself', d):
            return 'Manual - you', ('the link is stored on an existing Facebook Page post that this ad boosts: edit the post\'s link in Meta, or decide to replace the post. ' + d)[:400], ''
        return {'Failed': 'Failed', 'Skipped': 'Skipped'}[b['result']], d[:400], ''
    if any(a['result'] == 'Fixed' and same(url, a.get('after_live')) for a in rs):
        if FINAL: return PENDING, 'written earlier with a previous version of the rules; the final rules change it once more and the final run has no write result for it', ''
        return 'Not applied - needs your OK', 'written earlier with a previous version of the rules; the final rules change it once more (second edit ready, not written: the session safety check stopped further live writes)', ''
    if k in DIFF or any(same(url, x) for x in [s.get('url')] + [a.get('after_live') for a in rs]):
        if FINAL: return PENDING, 'reviewed URL ready; not written: the final run has no write result for it', ''
        return 'Not applied - needs your OK', 'planned and reviewed, not written: the session safety check stopped further live writes - see "Not applied - needs your OK"', ''
    return 'Changed by someone else', 'live URL differs from both the 11-Oct URL and the planned one', ''

def left_out(k, t):
    o = OMIT.get(k)
    if t and (t.get('source') or '').startswith('omit') and o: return ', '.join(o.get('omitted') or [])
    return ''

def how(k, t):
    b = []
    i = LEG.get(k) or OMIT.get(k)
    if i: b += i.get('basis') or []
    if t: b += (t.get('consistency') or []) + ([t['month_fix']] if t.get('month_fix') else [])
    return '\n'.join(dict.fromkeys(str(x) for x in b if x))[:1500]

# ---------- one row per ad URL slot, one per sitelink asset ----------
recs, seen = [], set()
for s in S:
    if not s.get('url'): continue
    k = key(s); t = T.get(k)
    kind = 'Sitelink' if 'sitelink' in str(s.get('slot')).lower() else 'Ad'
    if kind == 'Sitelink':
        a = (s['account_id'], str(s.get('ad_id')))
        if a in seen: continue
        seen.add(a)
    live = LIVE.get('|'.join(k))
    st, why, day = status_of(s, t, live)
    if FINAL and st == BL and s['platform'] == 'meta' and re.search(r'wadi', str(s.get('campaign_name') or ''), re.I):   # Wadi Safar Page: Meta refused every Wadi Safar ad it was asked to write
        why = ('Wadi Safar Meta ad: Meta also needs Page / Instagram access before it accepts this edit (it refused the Wadi Safar ads it was asked to write, missing Page permission). ' + (why or ''))[:400]
    url_now = (live or {}).get('url')
    vnow = 'GONE' if st == 'Gone' else ('CORRECT' if t and t.get('target') and same(url_now, t['target']) else 'WRONG')
    if st == 'Not re-read': vnow = 'NOT RE-READ'
    status_now = (live or {}).get('status_now') or s.get('effective_status') or s.get('ad_status')
    recs.append(dict(s=s, t=t, kind=kind, st=st, why=why, day=day, url_now=url_now, vnow=vnow, status_now=status_now,
                     on=is_on(s, (live or {}).get('status_now')), before='WRONG' if s['verdict'] != 'CORRECT' else 'CORRECT',
                     placements=sum(1 for x in S if x.get('url') and kind == 'Sitelink' and x['account_id'] == s['account_id'] and str(x['ad_id']) == str(s['ad_id']))))
recs.sort(key=lambda r: (r['s']['platform'], str(r['s'].get('account_name')), r['kind'], str(r['s'].get('campaign_name')), str(r['s'].get('adset_name')), str(r['s'].get('ad_name')), str(r['s'].get('ad_id')), str(r['s'].get('slot'))))
ad_b, ad_n = collections.defaultdict(list), collections.defaultdict(list)
for r in recs:
    if r['kind'] == 'Ad':
        ka = (r['s']['platform'], r['s'].get('account_id'), str(r['s'].get('ad_id')))
        ad_b[ka].append(r['before']); ad_n[ka].append(r['vnow'])
agg = lambda v: 'WRONG' if 'WRONG' in v else ('CORRECT' if all(x == 'CORRECT' for x in v) else v[0])

# ---------- styling helpers ----------
F = 'Arial'
HDR = Font(name=F, bold=True, color='FFFFFF'); HFILL = PatternFill('solid', fgColor='1F3864')
BODY = Font(name=F, size=10); BOLD = Font(name=F, size=10, bold=True)
TITLE = Font(name=F, size=14, bold=True); H2 = Font(name=F, size=12, bold=True); NOTE = Font(name=F, size=9, italic=True, color='595959')
WRAP = Alignment(wrap_text=True, vertical='top'); TOP = Alignment(vertical='top')
RED = PatternFill('solid', fgColor='F8CBAD'); GREEN = PatternFill('solid', fgColor='C6EFCE'); AMBER = PatternFill('solid', fgColor='FFE699'); BLUE = PatternFill('solid', fgColor='DDEBF7')
def table(ws, headers, rows, name, widths, wrap_cols=()):
    ws.append(headers); hr = ws.max_row
    for c in ws[hr]: c.font = HDR; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical='center')
    for r in rows:
        ws.append([('' if v is None else v) for v in r])
        for i, c in enumerate(ws[ws.max_row], 1): c.font = BODY; c.alignment = WRAP if i in wrap_cols else TOP
    last = max(ws.max_row, hr + 1)
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    t = Table(displayName=name, ref=f'A{hr}:{get_column_letter(len(headers))}{last}')
    t.tableStyleInfo = TableStyleInfo(name='TableStyleLight1', showRowStripes=True)
    ws.add_table(t); ws.freeze_panes = ws.cell(hr + 1, 1)
    return hr, last
def colour(ws, col, first, last, pairs):
    for val, fill in pairs:
        ws.conditional_formatting.add(f'{col}{first}:{col}{last}', FormulaRule(formula=[f'${col}{first}="{val}"'], fill=fill))

wb = Workbook()
# ---------------- Every URL ----------------
ws = wb.active; ws.title = 'Every URL'
H = ['Platform', 'Account', 'Campaign', 'Ad set / ad group', 'Ad name', 'Ad ID', 'Kind', 'Delivery status now', 'Switched on', 'URL slot',
     'URL before fix (11-Oct)', 'Verdict before', 'What was wrong before', 'Correct URL (final rules)', 'Built by', 'Parts left out (12-Oct rule)',
     'Live URL now (re-read)', 'Verdict now', 'Status', 'Detail / next step', 'Fixed on', 'Sitelink placements', 'First row of ad', 'Ad verdict before', 'Ad verdict now']
C = {h: get_column_letter(i) for i, h in enumerate(H, 1)}
rows, firsts = [], set()
for r in recs:
    s, t = r['s'], r['t']
    ka = (s['platform'], s.get('account_id'), str(s.get('ad_id')))
    first = 1 if (r['kind'] == 'Ad' and ka not in firsts) else 0
    if r['kind'] == 'Ad': firsts.add(ka)
    r['first'] = first
    rows.append([s['platform'], s.get('account_name'), s.get('campaign_name'), s.get('adset_name'), s.get('ad_name') or NONAME(s['platform']), str(s.get('ad_id')),
                 r['kind'], r['status_now'], 'Yes' if r['on'] else 'No', s.get('slot'), s.get('url'), r['before'], wrong_before(s),
                 (t or {}).get('target') or '', (t or {}).get('source') or '', left_out(key(s), t), r['url_now'], r['vnow'], r['st'], r['why'], r['day'],
                 r['placements'] if r['kind'] == 'Sitelink' else '', first,
                 agg(ad_b[ka]) if r['kind'] == 'Ad' else r['before'], agg(ad_n[ka]) if r['kind'] == 'Ad' else r['vnow']])
f1, l1 = table(ws, H, rows, 'EveryURL', [9, 22, 40, 38, 44, 22, 8, 16, 8, 26, 70, 10, 40, 70, 10, 34, 70, 11, 20, 50, 9, 9, 7, 10, 10],
               wrap_cols=(3, 4, 5, 11, 13, 14, 16, 17, 20))
for col in ('Verdict before', 'Verdict now', 'Ad verdict before', 'Ad verdict now'):
    colour(ws, C[col], f1 + 1, l1, (('WRONG', RED), ('CORRECT', GREEN)))
colour(ws, C['Status'], f1 + 1, l1, (('Fixed 12-Oct', GREEN), ('Fixed 13-Oct', GREEN), ('Fixed 11-Oct', GREEN), ('Correct', GREEN), ('Manual - you', AMBER),
                                      ('Not applied - needs your OK', BLUE), (PENDING, BLUE), ('Failed', RED), ('Skipped', AMBER), ('Changed by someone else', AMBER),
                                      (RF, AMBER), (BL, BLUE), (HELD, BLUE)))
EU = "'Every URL'"
rng = lambda h: f"{EU}!${C[h]}${f1+1}:${C[h]}${l1}"

# ---------------- Changes applied ----------------
wa = wb.create_sheet('Changes applied')
ca = []
for f in sorted(glob.glob(f'{W}/apply*/out_*.jsonl'), key=APN):
    day = DAY_OF(f)
    for line in open(f):
        if not line.strip(): continue
        try: a = json.loads(line)
        except Exception: continue
        if a['result'] not in ('Fixed', 'AlreadyFixed'): continue
        ok = same(a.get('after_live'), a.get('after_expected'))
        tg = None
        for aid in a.get('ad_ids') or []:
            tt = T.get((a['platform'], str(aid), a.get('slot')))
            if tt: tg = tt.get('target'); break
        a9 = a['result'] == 'AlreadyFixed' and '/apply9/' in f
        ca.append([day, RUN_LABEL(os.path.relpath(f, W)) + (' - first run, stopped and restarted' if a9 else ''), a['platform'], a.get('account_id'), '; '.join(str(x) for x in (a.get('ad_names') or []) if x) or NONAME(a['platform']),
                   ', '.join(str(x) for x in a.get('ad_ids') or []), str(a.get('unit')), a.get('slot'), (A9NOW.get((a['platform'], str(a.get('unit')), a.get('slot'))) or a.get('before')) if a9 else a.get('before'), a.get('after_live'),
                   'Yes' if ok else 'No', ('Yes' if same(a.get('after_live'), tg) else 'No - superseded, see Every URL') if tg else '',
                   a['result'], a.get('new_entity_ids') or '', (a.get('detail') or '')[:400]])
for (p, aid) in sorted(MAIN_SESSION):
    s_ = next((x for x in S if x['platform'] == p and str(x.get('ad_id')) == aid), None)
    lv = LIVE.get(f"{p}|{aid}|{s_['slot']}") if s_ else None
    tg = (T.get((p, aid, s_['slot'])) or {}).get('target') if s_ else None
    ca.append(['12-Oct', '12-Oct', p, s_['account_id'] if s_ else '', NONAME(p), aid, aid, s_['slot'] if s_ else '', s_['url'] if s_ else '', (lv or {}).get('url') or '',
               'Yes' if lv and same(lv.get('url'), tg) else '', 'Yes' if lv and same(lv.get('url'), tg) else '', 'Fixed',
               '', 'written from the main session after the agent was stopped by the safety check (dry-run, MutateAds final_urls, GAQL read-back byte-equal, status ENABLED unchanged)'])
for r in recs:
    if (r['why'] or '').startswith(UNREC8):
        s_ = r['s']; pl = FPLAN.get(key(s_)) or {}
        ca.append(['13-Oct', '13-Oct (no verified result line)', s_['platform'], s_.get('account_id'), s_.get('ad_name') or NONAME(s_['platform']), str(s_.get('ad_id')),
                   str(s_.get('ad_id')), s_.get('slot'), pl.get('url_now') or '', r['url_now'], 'Yes', 'Yes', 'Fixed (confirmed by re-read)', '', r['why'][:400]])
    if r['why'] == UNREC:
        s_ = r['s']; pl = FPLAN.get(key(s_)) or {}
        ca.append(['12-Oct', '12-Oct (final run; no result line)', s_['platform'], s_.get('account_id'), s_.get('ad_name') or NONAME(s_['platform']), str(s_.get('ad_id')),
                   str(s_.get('ad_id')), s_.get('slot'), pl.get('url_now') or '', r['url_now'], 'Yes', 'Yes', 'Fixed (confirmed by re-read)', '',
                   'the agent wrote and verified this change but the session safety check denied the step that logs it; before = the live URL in the plan at the pause, after = the final re-read'])
table(wa, ['Day', 'Run', 'Platform', 'Account ID', 'Ad name(s)', 'Ad ID(s)', 'Edited entity', 'URL slot', 'Before', 'After (read back live)', 'Read-back = planned',
           'Matches final rules', 'Result', 'New entity (e.g. creative)', 'Detail'], ca, 'ChangesApplied',
      [8, 16, 9, 14, 44, 22, 22, 26, 70, 70, 10, 14, 11, 16, 60], wrap_cols=(5, 9, 10, 15))

WHERE = {'meta': 'Ads Manager > ad > Edit > Website URL', 'snapchat': 'Snap Ads Manager > ad > Attachment > Website URL', 'tiktok': 'TikTok Ads Manager > ad > Destination URL',
         'x': 'X Ads > creative (card) > Website URL', 'google': 'Google Ads > Assets > Sitelinks (split the asset per campaign type)', 'linkedin': 'Campaign Manager > ad > Landing page'}
if FINAL:
    # ---------------- Still needs you (final): manual, refused by the platform, blocked by the safety check, anything else not fixed ----------------
    ORDER = [HELD, BL, RF, 'Manual - you', 'Failed', 'Skipped', 'Changed by someone else', PENDING, 'Not applied - needs your OK', 'Check landing page']
    def where_(p, kind):
        if p == 'google' and kind == 'Ad': return 'Google Ads > Ads > edit the ad > Final URL'
        return WHERE.get(p)
    def next_step(st, p, why):
        w = why or ''
        if st == HELD: return 'Your decision: write it through the API anyway (TikTok then re-publishes the post and the ad loses the original post\'s likes and comments), or change the URL in TikTok Ads Manager and check the ad keeps its post'
        if st == BL and w.startswith('Wadi Safar Meta ad'): return 'First grant the connected Meta user the Advertiser role on Wadi Safar Page 1245023868693595 and ad-account access to Instagram 17841441699550567 (wadisafarsa), then allow the blocked tools (see "Questions for you") and re-run - or set the correct URL in Ads Manager'
        if st == BL: return 'Approved and ready: allow the blocked Whathead write tool (see "Questions for you") and re-run, or set the correct URL by hand'
        if st == RF:
            if p == 'meta' and 'Wadi Safar Page' in w: return ('Grant the connected Meta user the Advertiser role on Wadi Safar Page 1245023868693595 and ad-account access to Instagram 17841441699550567 (wadisafarsa) in Business Settings, then ask for a re-run'
                                                             + (' (this carousel needs the copy without the parent image)' if 'parent image' in w else '') + ' - or set the correct URL in Ads Manager')
            if p == 'meta' and re.search(r'archived', w, re.I): return 'Meta does not allow edits to archived ads and they do not serve; nothing to do unless you restore or duplicate the ad - then use the correct URL'
            if p == 'meta' and re.search(r'permission', w, re.I) and re.search(r'Instagram account', w): return 'Meta refuses: the connected Meta user has no permission on the Instagram account this creative uses (e.g. wadisafarsa). Grant it in Business Settings and re-run, or edit the URL in Ads Manager'
            if p == 'meta' and re.search(r'Missing Page permission|Page permission reason|required_permission|subcode 3858749', w): return 'Meta refuses: the connected Meta user has no Advertiser role on this Page (e.g. Wadi Safar Page 1245023868693595). Grant the role in Business Settings and re-run, or edit the URL in Ads Manager'
            if p == 'meta' and re.search(r'Instagram', w, re.I): return 'Instagram-only ad set with a page-only creative: Meta needs an Instagram account on the creative; edit the URL in Ads Manager'
            if p == 'meta' and re.search(r'(?<![A-Za-z0-9])t\.co(?![A-Za-z0-9])', w): return 'The ad links to a t.co short link (Meta would show "t.co" as the headline): replace it with the correct URL in Ads Manager'
            if p == 'meta' and re.search(r'interactive components|interactive_components_spec|2446581', w): return 'Meta refuses an exact copy of this carousel (its cards and its interactive components no longer match, because of the parent image): set the URL in Ads Manager, or allow a copy without the parent image (that changes the creative beyond the URL)'
            if p == 'meta' and re.search(r'Media Not Wide Enough|2875006', w): return 'Meta refuses to attach a copy: the ad image is only 326 px wide. Upload an image at least 500 px wide, or set the URL in Ads Manager'
            if p == 'tiktok' and re.search(r'Spark Pull', w, re.I): return 'Spark Pull ad with expired creator authorisation: renew the authorisation or edit the destination URL in TikTok Ads Manager'
            if p == 'google' and re.search(r'POLICY|PROHIBITED|disapproved|policy', w): return 'Google refuses edits while the ad has a policy finding: fix the ad text (or recreate the ad), then set the correct final URL'
            return 'The platform refused the API edit: set the correct URL in the platform UI'
        if st == 'Manual - you':
            if re.search(r'tweet', w, re.I): return 'X does not allow editing links in a published tweet: post a new tweet with the correct URL if needed'
            if p == 'snapchat' and 'E1008' in w: return ('Snapchat cannot switch an ad to another creative (E1008' + (', nor change a Story creative\'s sub-creatives, E2003' if 'E2003' in w else '') + '). '
                                                       'In Snap Ads Manager duplicate the ad with its own creative carrying the correct URL, then pause the old ad'
                                                       + ('' if 'apply13' in APPLY_LIST else ' - or approve doing exactly that through the API (new ads + pausing the old ones)'))
            if re.search(r'shared|split', w, re.I): return 'Split the shared creative / card / sitelink so each ad gets its own URL, then set the correct URLs'
            return 'No single correct URL: decide the URL for this slot'
        if st == 'Check landing page': return 'Check the landing page language; the UTM follows the ad'
        return 'See the detail; set the correct URL by hand or ask for a re-run'
    wm = wb.create_sheet('Still needs you')
    ma = [[r['st'], r['s']['platform'], r['s'].get('account_name'), r['s'].get('campaign_name'), r['s'].get('adset_name'), r['s'].get('ad_name') or NONAME(r['s']['platform']), str(r['s'].get('ad_id')),
           r['kind'], r['status_now'], 'Yes' if r['on'] else 'No', r['why'], next_step(r['st'], r['s']['platform'], r['why']), r['s'].get('slot'), where_(r['s']['platform'], r['kind']), r['url_now'], (r['t'] or {}).get('target') or '']
          for r in recs if r['st'] in ORDER]
    for r in recs:      # landing pages whose language contradicts the ad (target keeps the ad's language; the page itself is the user's call)
        s = r['s']; tg = (r['t'] or {}).get('target')
        if not tg or r['kind'] != 'Ad': continue
        lp = re.search(r'/(en|ar)(/|$)', urlsplit(tg).path.lower()); q = dict(parse_qsl(urlsplit(tg).query))
        cl = (q.get('utm_content', '').split('_') or [''])[-1]; tl = (q.get('utm_term', '').split('_') or [''])[-1]
        cl = cl if cl in ('en', 'ar') else (tl if tl in ('en', 'ar') else None)   # Google ads have no ad name: fall back to the ad group language
        if lp and cl and cl != lp.group(1):
            ma.append(['Check landing page', s['platform'], s.get('account_name'), s.get('campaign_name'), s.get('adset_name'), s.get('ad_name') or NONAME(s['platform']), str(s.get('ad_id')), r['kind'], r['status_now'],
                       'Yes' if r['on'] else 'No', f'the ad / ad group is {cl.upper()} but its landing page is /{lp.group(1)}/ - the UTM follows the ad; change the page if it is wrong',
                       next_step('Check landing page', s['platform'], ''), s.get('slot'), where_(s['platform'], r['kind']), r['url_now'], tg])
    ma.sort(key=lambda x: (ORDER.index(x[0]), x[1], str(x[2]), str(x[3]), str(x[5]), x[6]))
    table(wm, ['What it is', 'Platform', 'Account', 'Campaign', 'Ad set / ad group', 'Ad name', 'Ad ID', 'Kind', 'Delivery status now', 'Switched on', 'Why it is yours', 'Next step',
               'URL slot', 'Where to edit', 'URL now', 'Correct URL (when one exists)'], ma or [['(nothing left)'] + [''] * 15], 'StillNeedsYou',
          [22, 9, 22, 40, 36, 44, 22, 8, 16, 8, 55, 50, 26, 34, 70, 70], wrap_cols=(4, 5, 6, 11, 12, 15, 16))
    colour(wm, 'A', 2, max(2, len(ma) + 1), ((HELD, BLUE), (BL, BLUE), (RF, AMBER), ('Manual - you', AMBER), ('Failed', RED), ('Skipped', AMBER), ('Check landing page', GREEN)))
else:
    # ---------------- Not applied - needs your OK ----------------
    wn = wb.create_sheet('Not applied - needs your OK')
    na = [[r['s']['platform'], r['s'].get('account_name'), r['s'].get('campaign_name'), r['s'].get('adset_name'), r['s'].get('ad_name') or NONAME(r['s']['platform']),
           str(r['s'].get('ad_id')), r['kind'], r['status_now'], 'Yes' if r['on'] else 'No', r['s'].get('slot'), r['url_now'], (r['t'] or {}).get('target'), r['why']]
          for r in recs if r['st'] in ('Not applied - needs your OK', PENDING)]
    table(wn, ['Platform', 'Account', 'Campaign', 'Ad set', 'Ad name', 'Ad ID', 'Kind', 'Delivery status', 'Switched on', 'URL slot', 'URL now', 'Correct URL (ready, reviewed)', 'Why not applied'],
          na, 'NotApplied', [9, 22, 40, 36, 44, 22, 8, 16, 8, 26, 70, 70, 50], wrap_cols=(3, 4, 5, 11, 12, 13))

    # ---------------- Manual - do yourself ----------------
    wm = wb.create_sheet('Manual - do yourself')
    ma = [[r['s']['platform'], r['s'].get('account_name'), r['s'].get('campaign_name'), r['s'].get('adset_name'), r['s'].get('ad_name') or NONAME(r['s']['platform']), str(r['s'].get('ad_id')),
           r['kind'], r['status_now'], 'Yes' if r['on'] else 'No', r['st'], r['why'], r['s'].get('slot'), WHERE.get(r['s']['platform']), r['url_now'], (r['t'] or {}).get('target') or '']
          for r in recs if r['st'] in ('Manual - you', 'Failed', 'Skipped', 'Changed by someone else')]
    # landing pages whose language contradicts the ad (target keeps the ad's language; the page itself is the user's call)
    for r in recs:
        s = r['s']; tg = (r['t'] or {}).get('target')
        if not tg or r['kind'] != 'Ad': continue
        lp = re.search(r'/(en|ar)(/|$)', urlsplit(tg).path.lower()); q = dict(parse_qsl(urlsplit(tg).query))
        cl = (q.get('utm_content', '').split('_') or [''])[-1]; tl = (q.get('utm_term', '').split('_') or [''])[-1]
        cl = cl if cl in ('en', 'ar') else (tl if tl in ('en', 'ar') else None)   # Google ads have no ad name: fall back to the ad group language
        if lp and cl and cl != lp.group(1):
            ma.append([s['platform'], s.get('account_name'), s.get('campaign_name'), s.get('adset_name'), s.get('ad_name') or NONAME(s['platform']), str(s.get('ad_id')), r['kind'], r['status_now'],
                       'Yes' if r['on'] else 'No', 'Check landing page', f'the ad / ad group is {cl.upper()} but its landing page is /{lp.group(1)}/ - the UTM follows the ad; change the page if it is wrong',
                       s.get('slot'), WHERE.get(s['platform']), r['url_now'], tg])
    table(wm, ['Platform', 'Account', 'Campaign', 'Ad set', 'Ad name', 'Ad ID', 'Kind', 'Delivery status', 'Switched on', 'Status', 'Why it is yours', 'URL slot', 'Where to edit',
               'URL now', 'Correct URL (when one exists)'], ma, 'Manual', [9, 22, 40, 36, 44, 22, 8, 16, 8, 16, 55, 26, 34, 70, 70], wrap_cols=(3, 4, 5, 11, 14, 15))

# ---------------- What was left out ----------------
wl = wb.create_sheet('What was left out')
lo = []
for r in recs:
    k = key(r['s']); t = r['t']
    if not t: continue
    lo.append([r['s']['platform'], r['s'].get('ad_name') or NONAME(r['s']['platform']), str(r['s'].get('ad_id')), r['kind'], t.get('source'), t.get('target'), left_out(k, t) or '(nothing - every part sourced)', how(k, t)])
table(wl, ['Platform', 'Ad name', 'Ad ID', 'Kind', 'Built by', 'Correct URL (final rules)', 'Parts left out', 'How each part was sourced'], lo, 'LeftOut',
      [9, 44, 22, 8, 10, 70, 40, 90], wrap_cols=(2, 6, 7, 8))

# ---------------- Month check ----------------
wmo = wb.create_sheet('Month check')
mo = []
for r in recs:
    s = r['s']
    if r['kind'] != 'Ad': continue
    fs = FS.get(f"{s['platform']}|{s.get('ad_id')}")
    tg = (r['t'] or {}).get('target') or ''
    m = re.search(r'(?:^|_)((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\d\d)(?:_|$)', dict(parse_qsl(urlsplit(tg).query)).get('utm_campaign', '')) if tg else None
    mf = MONTHFIX.get(key(s))
    mo.append([s['platform'], s.get('ad_name') or NONAME(s['platform']), str(s.get('ad_id')), fs or '', m.group(1) if m else '(left out)', (mf or {}).get('why') or ''])
table(wmo, ['Platform', 'Ad name', 'Ad ID', 'First day with impressions (account time zone)', 'Month in utm_campaign', 'Correction made on 12-Oct'], mo, 'MonthCheck',
      [9, 50, 22, 18, 14, 70], wrap_cols=(2, 6))

# ---------------- TikTok posts re-published (Spark Push side effect) ----------------
SPK = f'{W}/work/spark_check/spark_item_check.json'
if FINAL and os.path.exists(SPK):
    wsp = wb.create_sheet('TikTok posts re-published')
    sp = []
    for x in json.load(open(SPK)):
        if not x.get('changed'): continue
        sp.append([x['ad_id'], '; '.join(n for n in (x.get('ad_names') or []) if n) or NONAME('tiktok'), x.get('account_id'), RUN_LABEL(x['run'] + '/'),
                   x['orig_item'], x.get('orig_created'), x.get('current_item'), x.get('cur_created'),
                   'TikTok re-published the post after the URL edit; the ad now runs on the new post and no longer shows the original post\'s likes and comments. '
                   'The API refuses to point the ad back at the original post (error 40002). Check in TikTok Ads Manager whether the original post can be re-selected; otherwise the ad keeps the new post.'])
    sp.sort(key=lambda r: (r[3], r[0]))
    table(wsp, ['Ad ID', 'Ad name', 'Account ID', 'Written in run', 'Original post (tiktok_item_id)', 'Original post created (UTC)', 'Post now', 'New post created (UTC)', 'What happened / what you can do'],
          sp or [['(none)'] + [''] * 8], 'SparkRepublished', [20, 50, 20, 18, 22, 18, 22, 18, 90], wrap_cols=(2, 9))

# ---------------- Unattached copies (created by the runs, not in use, nothing deleted) ----------------
UNA = f'{W}/work/unattached_copies.json'
if FINAL and os.path.exists(UNA):
    wu = wb.create_sheet('Unattached copies')
    ua = [[x['platform'], x.get('account_id'), x['creative_id'], x.get('name') or '', x.get('run') or '', x.get('for') or '', x.get('why') or ''] for x in json.load(open(UNA))]
    table(wu, ['Platform', 'Account ID', 'Creative ID', 'Creative name', 'Created in run', 'Made for (ad / creative)', 'Why it is not attached (none of these serves; nothing was deleted)'],
          ua or [['(none)'] + [''] * 6], 'Unattached', [9, 22, 40, 44, 16, 40, 90], wrap_cols=(4, 6, 7))

# ---------------- TikTok ad texts trimmed by the gateway (side effect of a URL write) ----------------
TRM = f'{W}/work/tiktok_text_trimmed.json'
if FINAL and os.path.exists(TRM):
    wt = wb.create_sheet('TikTok text trimmed')
    tr = [[x['ad_id'], x.get('ad_name') or NONAME('tiktok'), x.get('account_id'), RUN_LABEL(x['run'] + '/'), x['kind'] + ' space',
           ('TikTok kept the post caption unchanged (only the request was trimmed). ' if x['ad_id'] == '1825848526683217' else '') + (x.get('detail') or '')] for x in json.load(open(TRM))]
    table(wt, ['Ad ID', 'Ad name', 'Account ID', 'Written in run', 'Whitespace removed', 'What the agent recorded (the Whathead gateway strips a leading / trailing space or no-break space from ad_text; nothing else in the text changed)'],
          tr or [['(none)'] + [''] * 5], 'TextTrimmed', [20, 50, 20, 30, 16, 100], wrap_cols=(2, 6))

# ---------------- New since 11-Oct ----------------
wnw = wb.create_sheet('New ads since 11-Oct')
nw = []
for f in sorted(glob.glob(f'{W}/{REREAD}/out/new_*.jsonl')):
    for line in open(f):
        if not line.strip(): continue
        try: x = json.loads(line)
        except Exception: continue
        e = check_omit(N, x['url']) if x.get('url') else ['no URL']
        nw.append([x.get('platform'), x.get('account_name'), x.get('campaign_name'), x.get('adset_name'), x.get('ad_name'), str(x.get('ad_id')), x.get('effective_status') or x.get('ad_status'),
                   x.get('slot'), x.get('url'), 'passes the format checks' if not e else '; '.join(e)])
table(wnw, ['Platform', 'Account', 'Campaign', 'Ad set', 'Ad name', 'Ad ID', 'Delivery status', 'URL slot', 'URL now', 'Format check (not counted in the %)'], nw or [['(none found)'] + [''] * 9],
      'NewAds', [9, 22, 40, 36, 44, 22, 16, 26, 70, 50], wrap_cols=(3, 4, 5, 9, 10))

# ---------------- 7-Oct sheet audit (carried over) ----------------
old = glob.glob(f'{W}/out/Diriyah_UTM_Verification_2026-10-11_final.xlsx')
if old:
    ow = openpyxl.load_workbook(old[0])['7-Oct sheet audit']
    w7 = wb.create_sheet('7-Oct sheet audit')
    vals = [list(r) for r in ow.iter_rows(values_only=True)]
    table(w7, [str(x) for x in vals[0]], vals[1:], 'Audit7Oct', [9, 40, 36, 44, 22, 70, 22, 9, 40, 12, 12, 60], wrap_cols=(2, 3, 4, 6, 9, 12))

# ---------------- Questions for you ----------------
wq = wb.create_sheet('Questions for you')
LIVE_ROW = None
if FINAL:   # results of the final run (last result line per change, as check_apply.py)
    n_ch = sum(len(u['changes']) for f in glob.glob(f'{W}/{APPLY_LIST[0]}/in_*.json') for u in json.load(open(f)))   # the approved plan (first folder)
    last = {}
    for ap in APPLY_LIST:                                   # later folders (the resume) override earlier ones, per change
        for f in sorted(glob.glob(f'{W}/{ap}/out_*.jsonl')):
            for line in open(f):
                try: a = json.loads(line)
                except Exception: continue
                a['_ap'] = ap; last[(a.get('platform'), str(a.get('unit')), a.get('slot'))] = a
    fr = collections.Counter()
    U8K = {key(r['s']) for r in recs if (r['why'] or '').startswith(UNREC8)}
    for a in last.values():
        d = a.get('detail') or ''; r_ = a['result']
        if r_ == 'AlreadyFixed' and a.get('_ap') == 'apply9': fr['Fixed'] += 1     # written by the stopped first apply9 run, confirmed by the restarted one
        elif r_ in ('Fixed', 'AlreadyFixed'): fr[r_] += 1
        elif any((a.get('platform'), str(x), a.get('slot')) in WADI for x in a.get('ad_ids') or []): fr['wadi'] += 1
        elif any((a.get('platform'), str(x), a.get('slot')) in U8K for x in a.get('ad_ids') or []): fr['written_unverified'] += 1
        elif re.search(r'existing (Facebook )?Page post|stored on the post itself', d): fr['manual'] += 1
        elif r_ == 'NotAttempted' and re.search(r'Spark Push', d): fr['held'] += 1
        elif re.search(r'safety check', d, re.I): fr['blocked'] += 1
        elif REFUSE_RX.search(d): fr['refused'] += 1
        elif re.search(r'sign-?in|re-?authent', d, re.I): fr['signin'] += 1
        else: fr[r_] += 1
    no_line = max(0, n_ch - len(last))
    unrec = sum(1 for r in recs if r['why'] == UNREC)
    txt = (f'Final run on 12-Oct' + (' (and on 13-Oct: the approved writes it had not reached and, after you added the permission rules, the ones the safety check had blocked)' if 'apply9' in APPLY_LIST else ' (and on 13-Oct for the approved writes it had not reached)' if A8 else '') + f', after you approved every remaining write ({n_ch} changes): {fr["Fixed"]} written and read back byte for byte, '
           f'{fr["AlreadyFixed"]} already correct when re-read (no write needed), {fr["held"]} TikTok Spark Push changes held for your decision, '
           f'{fr["refused"]} refused by the platform, {fr["blocked"]} blocked by this session\'s safety check, {fr["Failed"]} failed, '
           + (f'{fr["manual"]} left to you (the link lives on an existing Page post), ' if fr['manual'] else '')
           + (f'{fr["wadi"]} Wadi Safar Meta changes waiting for Page / Instagram access, ' if fr['wadi'] else '')
           + (f'{fr["written_unverified"]} written on 13-Oct whose verification step the safety check denied (the final re-read confirms them), ' if fr['written_unverified'] else '') +
           f'{fr["Skipped"]} skipped because the live URL had changed since the plan, {fr["NotAttempted"] + fr["signin"]} not attempted (TikTok API outage, sign-in prompt or a stopped batch), '
           f'{no_line} with no result line because their batch stopped first. A further {unrec} URL slots were written and verified by agents that could not log them '
           f'(the safety check denied the logging step); the final re-read confirms them. The status of every URL comes from the final re-read; everything still not right is in "Still needs you".')
    if fr['blocked']: txt += ' ' + (os.environ.get('PERMISSION_RULE') or 'To let the blocked writes through, add an allow rule for the blocked Whathead write tool to the Claude Code permission settings.')
    if any(a in APPLY_LIST for a in ('apply10', 'apply11', 'apply12', 'apply13')):   # 13-Oct afternoon: writes per day and per run, then where the URLs stand (final re-read)
        wd, wr, w11 = collections.Counter(), collections.Counter(), collections.Counter()
        R11 = [('spark_push', 'TikTok Spark Push'), ('carousel_no_parent_image', 'Meta carousels copied without the parent image'), ('ig_identity', 'Meta Instagram-only ads given their Instagram account'),
               ('page_post', 'Meta ads boosting a Page post'), ('tco_headline', 'Meta ad linking to a t.co short link')]
        for f in sorted(glob.glob(f'{W}/apply*/out_*.jsonl'), key=APN):
            ap = os.path.relpath(f, W).split('/')[0]
            for line in open(f):
                try: a = json.loads(line)
                except Exception: continue
                if a['result'] == 'Fixed' or (a['result'] == 'AlreadyFixed' and ap == 'apply9'):
                    wd[DAY_OF(f)] += 1; wr[ap] += 1
                    if ap == 'apply11': w11[next((lbl for k_, lbl in R11 if k_ in f), 'other')] += 1
        n8 = sum(1 for r in recs if (r['why'] or '').startswith(UNREC8))
        wd['12-Oct'] += unrec + len(MAIN_SESSION); wd['13-Oct'] += n8; wr['apply8'] += n8
        sa = collections.Counter(r['st'] for r in recs if r['kind'] == 'Ad' and r['vnow'] == 'WRONG')
        txt = (f'Writes made and read back byte for byte (one per changed URL slot; a shared creative counts once): {sum(wd.values())} - 11-Oct {wd["11-Oct"]}, 12-Oct {wd["12-Oct"]}, 13-Oct {wd["13-Oct"]}. '
               f'13-Oct: {wr["apply8"]} approved writes the 12-Oct run had not reached; {wr["apply9"]} after you added the permission rules (writes the safety check had blocked); '
               f'{wr["apply10"]} retries of transient failures; {wr["apply11"]} after your approvals ("run until its 0%", "fix everything you can", Spark Push, Snapchat split, Meta carousels): '
               + ', '.join(f'{lbl} {w11[lbl]}' for _, lbl in R11 if w11[lbl]) + f'; {wr["apply12"]} TikTok ad held over a text trim'
               + (f'; {wr["apply13"]} Snapchat Story-ad URLs after "continue until everything is fixed" (the approved split, done inside each ad\'s own Story creative)' if wr['apply13'] else '') + '. '
               + 'Tried on 13-Oct and refused by the platforms: the Snapchat split (Snapchat will not switch an ad to another creative, E1008'
               + ('; for the 6 Story ads with their own Story creative it also refused changing that creative\'s sub-creatives, E2003' if STORY13 else '') +
               '; the copies made before each stop are unattached, nothing deleted) and the Wadi Safar Meta ads (Meta: Missing Page permission). '
               + ('You then said not to create new ads and to leave Wadi Safar to you. ' if STORY13 else '')
               + f'Still not right after the final re-read: {sum(sa.values())} ad URL slots - ' + ', '.join(f'{k_} {v_}' for k_, v_ in sa.most_common()) +
               '. Each is listed with its reason and next step in "Still needs you"; the status of every URL comes from the final re-read.')
        fr['blocked'] = sum(1 for r in recs if r['st'] == BL)
    LIVE_ROW = ('Live writes', txt, 'Done' if not fr['blocked'] else 'Done - some writes need a permission rule')
    if os.environ.get('INTERIM'):
        txt = (f'INTERIM - {os.environ["INTERIM"]}. So far in the final run: ' + txt.split('): ', 1)[1].replace(' Everything that is still not right', ' The rest of the changes have no result yet ("' + PENDING + '"). Everything that is still not right')
               + f' (approved total: {n_ch} changes)')
    LIVE_ROW = ('Live writes', txt, ('Stopped - ' + os.environ['INTERIM']) if os.environ.get('INTERIM') else 'Done' if not fr['blocked'] else 'Done - some writes need a permission rule')
QS = [
    ('Live writes still to do', ('Writes were PAUSED at your request on 12-Oct. The remaining reviewed changes are listed as "' + PENDING + '" in "Not applied - needs your OK"; they resume once the Whathead connector is signed in again (claude.ai > Customize > Connectors). ' if PENDING != 'Being applied now' else 'You confirmed the remaining writes on 12-Oct. They were running when this workbook was built ("Being applied now"). ') + 'The session safety check stopped some Google and TikTok writes even after your OK; those are "Not applied - needs your OK". To let them through, add a permission rule allowing the Whathead Google Ads / TikTok write actions; each write uses the same re-read / dry-run / read-back routine.', 'Paused' if PENDING != 'Being applied now' else 'In progress'),
    ('utm_medium', 'Old URLs mixed cpc / cpm / paid-social / paid-search, even inside one campaign and on Google Search. The planned URLs use the generator\'s own medium for each source: google -> paid-search; meta / tiktok / snapchat / x / linkedin -> paid-social. Keep, or keep the old medium where it is a valid Mappings value?', 'Default applied: generator medium'),
    ('Demand Gen (source gadg)', 'The generator has no row for gadg, so no medium can be sourced; the planned URLs leave utm_medium out (12-Oct omit rule). Pick paid-display or paid-video if you want one.', 'Left out'),
    ('Template campaign name "visitor-diriyah-coe"', 'The agency template token (cam-id_mindshare_diriyah-company_<asset>_tactical_visitor-diriyah-coe_...) was pasted on Bujairi, Zallal, Bab Samhan and Shopping 2026 campaigns. Only its Campaign Name field is used (visitor-diriyah-coe), as the schema says; that merges those campaigns under one name in reports. Alternatives: leave the campaign name out, or keep the unit + asset (diriyah-company-bujairi-visitor-diriyah-coe).', 'Default applied: name field only'),
    ('Agency prefix "hs-"', 'Legacy H&S campaign tokens keep their hs- prefix (hs-cityscape, hs-wintercampaign-zallal). Strip it?', 'Kept'),
    ('utm_source', 'Where the campaign name carries its channel, the source follows it (instagram -> meta on _Meta_ campaigns, twitter -> x on _X_ campaigns), as the generator does.', 'Default applied'),
    ('Ritz rule', 'The 78f964bb_rcsr-search_search_{lang} content is applied to the Ritz-Carlton Signature (2026) search ads only, not to RitzCarlton_Residences 2024. Correct?', 'Signature only'),
    ('Landing pages', 'Some Arabic ads land on /en/ pages (and the reverse). The UTM language follows the ad; the page itself is listed in "Manual - do yourself" for you to check.', 'Your call'),
]
if LIVE_ROW: QS[0] = LIVE_ROW
if FINAL and 'apply13' in APPLY_LIST:
    QS.insert(1, ('Your decisions on 13-Oct', 'Approved: TikTok Spark Push, Snapchat split, Meta carousels, "fix everything you can", "run until its 0%", "continue until everything is fixed". '
                  'Declined: "do not create new ads" (so no new Snapchat ads, X tweets or Google sitelink splits); Wadi Safar Meta: "Leave Wadi Safar to me".', 'Applied'))
    QS.insert(2, ('Snapchat Diriyah Gate (observed 13-Oct)', '2 ended "Founding day" ads (db6eaca4, ffc624dc) were rejected by Snap review after the 12-Oct URL edit: '
                  '"page not found" for https://www.dgda.gov.sa/ar. Their campaigns ended in 2025, so nothing delivers either way; check that page before reusing them.', 'FYI'))
if FINAL: QS = [(a, b.replace('listed in "Manual - do yourself"', 'listed in "Still needs you"'), c) for a, b, c in QS]
table(wq, ['Topic', 'Question / what was done', 'Status'], QS, 'Questions', [30, 120, 26], wrap_cols=(2,))

# ---------------- Rules used ----------------
wr = wb.create_sheet('Rules used')
RULES = [
    ('utm_campaign', 'uid_campaign-name_monYY_objective (all lower case)', 'Generator Schema / Output formula'),
    ('utm_term', 'uid_adset-name_adset-language', 'Generator Schema / Output formula'),
    ('utm_content', 'uid_ad-name_format_ad-language', 'Generator Schema / Output formula'),
    ('utm_source / utm_medium', 'From the Mappings lists; source follows the campaign name channel when it has one (_Meta_ -> meta, _X_ -> x)', 'Mappings; v5 review'),
    ('No utm_id', 'Removed wherever it appeared; click ids (fbclid, gclid) dropped', 'User 11-Oct'),
    ('Objective', 'Always added when known: _MF_TRF_ -> cond, AWR -> awr, CONV/LEAD -> conv, or the definition / sub-objective words (traffic -> cond, reach -> awr, leads/sales -> conv)', 'User 11-Oct; generator Input rows'),
    ('Uids', 'Only Campaign_Code_Generator 8-hex codes, only for exactly that name; otherwise no code. Manazel: generator code if it has one', 'User 11-Oct'),
    ('Month', 'Month the ad FIRST served (first day with impressions, account time zone), confirmed with daily data. Never served -> left out. Sitelinks -> left out', 'User 11-Oct ("be extremely accurate")'),
    ('kva / kvb / kvd', 'Programmatic-only: on social / search the ad token is unknown and left out', 'User 11-Oct'),
    ('Ritz Google search', '78f964bb_rcsr-search_search_{lang}', 'User 11-Oct'),
    ('12-Oct omit rule', '"for unknown figures like ad tokens write the utm without them" - a part that cannot be sourced is left out, never invented; a parameter with no known part is dropped', 'User 12-Oct'),
    ('Names (legacy ads)', 'From the generator, from names sibling ads in the same live campaign / ad set already use, or from the ad\'s own old UTM token; one name per live campaign / ad set; tokens that name another campaign or another cut are not used', 'v5 review (12-Oct)'),
    ('Format', 'Video slot -> video; carousel has no Mappings format and is written as display', 'Mappings col T; v5 review'),
    ('Shared creatives', 'A creative / card / sitelink used by ads that need different URLs is on the manual list (split it by hand)', 'User 11-Oct'),
    ('utm_medium (v6)', "Legacy / rebuilt URLs use the generator's medium for the source (google -> paid-search, social -> paid-social); Demand Gen (no generator row) left out", 'Generator Input rows; see Questions'),
    ('Old generator-layout tokens', 'agency_unit_asset_type_NAME_... : only the NAME field is a campaign name', 'Generator Schema; review 12-Oct'),
    ('Every write', 're-read live -> skip if it changed -> dry-run -> write -> read back and compare byte for byte; nothing deleted', 'Handoff'),
]
table(wr, ['Rule', 'What is required', 'Source'], RULES, 'Rules', [24, 110, 34], wrap_cols=(2,))

# ---------------- Summary ----------------
sm = wb.create_sheet('Summary', 0)
sm['A1'] = 'Diriyah / Wadi Safar UTM fix - before vs after' + ((' (INTERIM - ' + os.environ['INTERIM'] + ')') if os.environ.get('INTERIM') else ''); sm['A1'].font = TITLE
sm['A2'] = ('Every ad and every final-URL slot in every ad account whose name contains "Diriyah" or "Wadi" (Meta, TikTok, Snapchat, X, Google Ads, LinkedIn). '
            'Before = live pull 11-Oct-2026. After = keyed live re-read of the same slots on 12-Oct-2026, compared with the URL the final rules give. Ad name is on every row of "Every URL".')
sm['A2'].font = NOTE; sm['A2'].alignment = WRAP; sm.merge_cells('A2:N2'); sm.row_dimensions[2].height = 42
EXP = {}   # python-side value of every Summary formula cell (checked against the LibreOffice recalculation)
if FINAL:
    sm['A2'] = ('Every ad and every final-URL slot in every ad account whose name contains "Diriyah" or "Wadi" (Meta, TikTok, Snapchat, X, Google Ads, LinkedIn). '
                'Before = live pull 11-Oct-2026. After = keyed live re-read of the same slots on ' + (os.environ.get('REREAD_DATE') or '12-Oct-2026') + ', after the final write run, compared with the URL the final rules give. Ad name is on every row of "Every URL".')
    plats = ['meta', 'tiktok', 'snapchat', 'x', 'google', 'linkedin']
    P, K, VB, VN, ST, FR = rng('Platform'), rng('Kind'), rng('Verdict before'), rng('Verdict now'), rng('Status'), rng('First row of ad')
    AB, AN, ON, PL = rng('Ad verdict before'), rng('Ad verdict now'), rng('Switched on'), rng('Slot placements') if 'Slot placements' in C else rng('Sitelink placements')
    def put(r_, c_, formula, val, pct=False, bold=False):
        cell = sm.cell(r_, c_, formula); cell.font = BOLD if bold else BODY
        if pct: cell.number_format = '0.0%'
        EXP[f'{get_column_letter(c_)}{r_}'] = val
    def hdr_row(r_, names):
        for i, h in enumerate(names, 1):
            c = sm.cell(r_, i, h); c.font = HDR; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical='center')
    pick = lambda p, kind: [r for r in recs if r['kind'] == kind and (p == 'ALL' or r['s']['platform'] == p)]
    ratio = lambda a_, b_: (a_ / b_) if b_ else 0
    sm['A4'] = 'Before vs after, per platform'; sm['A4'].font = H2
    for col, title in ((2, 'Ad URL slots'), (7, 'Ads with a URL (an ad is wrong when any of its URLs is wrong)'), (12, 'Switched-on ads (ad, ad set and campaign on now)')):
        c = sm.cell(4, col, title); c.font = BOLD; c.alignment = Alignment(wrap_text=True, vertical='bottom'); sm.merge_cells(start_row=4, start_column=col, end_row=4, end_column=col + 4)
    sm.row_dimensions[4].height = 30
    hdr_row(5, ['Platform', 'URL slots', 'Wrong before', '% wrong before', 'Wrong now', '% wrong now', 'Ads', 'Wrong before', '% wrong before', 'Wrong now', '% wrong now',
                'Switched-on ads', 'Wrong before', '% wrong before', 'Wrong now', '% wrong now'])
    row = 6
    for p in plats + ['ALL']:
        pc = f'"{p}"' if p != 'ALL' else '"*"'; bold = p == 'ALL'
        sm.cell(row, 1, p if p != 'ALL' else 'All platforms').font = BOLD if bold else BODY
        rr = pick(p, 'Ad'); fa = [r for r in rr if r['first'] == 1]; fo = [r for r in fa if r['on']]
        ka_ = lambda r: (r['s']['platform'], r['s'].get('account_id'), str(r['s'].get('ad_id')))
        f = lambda extra: f'=COUNTIFS({P},{pc},{K},"Ad"{extra})'
        n1, b1, w1 = len(rr), sum(r['before'] == 'WRONG' for r in rr), sum(r['vnow'] == 'WRONG' for r in rr)
        n2, b2, w2 = len(fa), sum(agg(ad_b[ka_(r)]) == 'WRONG' for r in fa), sum(agg(ad_n[ka_(r)]) == 'WRONG' for r in fa)
        n3, b3, w3 = len(fo), sum(agg(ad_b[ka_(r)]) == 'WRONG' for r in fo), sum(agg(ad_n[ka_(r)]) == 'WRONG' for r in fo)
        put(row, 2, f(''), n1, bold=bold); put(row, 3, f(f',{VB},"WRONG"'), b1, bold=bold); put(row, 4, f'=IF(B{row}=0,0,C{row}/B{row})', ratio(b1, n1), True, bold)
        put(row, 5, f(f',{VN},"WRONG"'), w1, bold=bold); put(row, 6, f'=IF(B{row}=0,0,E{row}/B{row})', ratio(w1, n1), True, bold)
        put(row, 7, f(f',{FR},1'), n2, bold=bold); put(row, 8, f(f',{FR},1,{AB},"WRONG"'), b2, bold=bold); put(row, 9, f'=IF(G{row}=0,0,H{row}/G{row})', ratio(b2, n2), True, bold)
        put(row, 10, f(f',{FR},1,{AN},"WRONG"'), w2, bold=bold); put(row, 11, f'=IF(G{row}=0,0,J{row}/G{row})', ratio(w2, n2), True, bold)
        put(row, 12, f(f',{FR},1,{ON},"Yes"'), n3, bold=bold); put(row, 13, f(f',{FR},1,{ON},"Yes",{AB},"WRONG"'), b3, bold=bold); put(row, 14, f'=IF(L{row}=0,0,M{row}/L{row})', ratio(b3, n3), True, bold)
        put(row, 15, f(f',{FR},1,{ON},"Yes",{AN},"WRONG"'), w3, bold=bold); put(row, 16, f'=IF(L{row}=0,0,O{row}/L{row})', ratio(w3, n3), True, bold)
        row += 1
    row += 1
    sm.cell(row, 1, 'Google sitelink assets (one row per asset; sitelinks exist on Google only)').font = H2; row += 1
    hdr_row(row, ['Platform', 'Sitelink assets', 'Wrong before', '% wrong before', 'Wrong now', '% wrong now', 'Placements']); row += 1
    rr = pick('google', 'Sitelink'); n1, b1, w1 = len(rr), sum(r['before'] == 'WRONG' for r in rr), sum(r['vnow'] == 'WRONG' for r in rr)
    sm.cell(row, 1, 'google').font = BODY
    put(row, 2, f'=COUNTIFS({K},"Sitelink")', n1); put(row, 3, f'=COUNTIFS({K},"Sitelink",{VB},"WRONG")', b1); put(row, 4, f'=IF(B{row}=0,0,C{row}/B{row})', ratio(b1, n1), True)
    put(row, 5, f'=COUNTIFS({K},"Sitelink",{VN},"WRONG")', w1); put(row, 6, f'=IF(B{row}=0,0,E{row}/B{row})', ratio(w1, n1), True); put(row, 7, f'=SUMIFS({PL},{K},"Sitelink")', sum(r['placements'] for r in rr))
    row += 2
    sm.cell(row, 1, 'Where every URL stands now (number of URL slots; sitelinks: number of assets)').font = H2; row += 1
    OTHER = ['Failed', 'Skipped', 'Changed by someone else', PENDING, 'Not applied - needs your OK']
    cols = [('Fixed 12-Oct', ['Fixed 12-Oct'])] + ([('Fixed 13-Oct', ['Fixed 13-Oct'])] if A8 else []) + [('Fixed 11-Oct', ['Fixed 11-Oct']), ('Already correct', ['Correct']), ('Manual - you', ['Manual - you']),
            (RF, [RF]), (BL, [BL]), (HELD, [HELD]), ('Failed / skipped / other not fixed', OTHER), ('Gone / not re-read', ['Gone', 'Not re-read'])]
    hdr_row(row, ['Platform'] + [c_[0] for c_ in cols] + ['Total']); row += 1
    for p in plats + ['ALL', 'google sitelinks']:
        kind = 'Sitelink' if p == 'google sitelinks' else 'Ad'; pp = 'google' if kind == 'Sitelink' else p
        pc = f'"{pp}"' if pp != 'ALL' else '"*"'; bold = p == 'ALL'
        sm.cell(row, 1, p if p != 'ALL' else 'All platforms (ad URL slots)').font = BOLD if bold else BODY
        rr = pick(pp, kind)
        for i, (_, sts) in enumerate(cols, 2):
            put(row, i, '=' + '+'.join(f'COUNTIFS({P},{pc},{K},"{kind}",{ST},"{x}")' for x in sts), sum(r['st'] in sts for r in rr), bold=bold)
        put(row, len(cols) + 2, f'=COUNTIFS({P},{pc},{K},"{kind}")', len(rr), bold=bold)
        row += 1
    row += 1
    sm.cell(row, 1, 'How to read it').font = H2; row += 1
    notes = [
        'A URL is right only when the live URL equals the URL the final rules give (parameter order ignored). Before (11-Oct) every URL was wrong.',
        '"Wrong now" includes every URL listed in "Still needs you": manual, refused by the platform, blocked by the safety check, and anything else not fixed.',
        '"Refused by the platform": the platform API will not take this edit (Meta: archived ads, Wadi Safar Page / Instagram permission, page-only creatives in Instagram-only ad sets, the t.co link, 2 Bab Samhan carousels whose exact copy Meta rejects, 1 image too narrow; TikTok Spark Pull ads with expired authorisation; Google ads with policy findings). These are never retried.',
        '"Blocked by safety check": you approved it and the URL is ready, but this session\'s safety check stopped the live write (the Wadi Safar Meta ads among them also need Page / Instagram access first).',
        '"Held - your decision": TikTok Spark Push ads. An API URL edit makes TikTok re-publish the post 30-60 minutes later and detach the ad from its original post, so they were not written. See "TikTok posts re-published" for the ads already affected by the earlier runs.',
        '"Manual - you": shared creatives / cards / sitelinks that would need two different URLs, links inside tweet text, and sitelinks with no single correct URL.',
        'Every write was re-read before and after; "Changes applied" has the before / after read-back of each one (column Run shows which run).',
        'Ads created after the 11-Oct pull are listed in "New ads since 11-Oct" and are not counted in the percentages.',
    ]
    if 'apply11' in APPLY_LIST:   # after the 13-Oct approvals (Spark Push, carousels, fix everything you can)
        notes[2] = ('"Refused by the platform": the platform API will not take this edit (Meta: archived ads, the Wadi Safar Page / Instagram permission - re-tested on 13-Oct, '
                    '1 image too narrow; TikTok Spark Pull ads whose creator authorisation expired or whose post no longer resolves; Google ads with policy findings). '
                    'The 13-Oct approvals fixed the Bab Samhan carousels, the Instagram-only ads, the t.co ad and the Page-post ads that were listed here before.')
        notes[4] = ('TikTok Spark Push ads were written on 13-Oct after your approval. TikTok re-publishes a post 30-60 minutes after such an edit and the ad then runs on the new post, '
                    'without the original post\'s likes and comments - see "TikTok posts re-published".')
        notes[5] += (' Snapchat: the split was tried on 13-Oct after your approval, but Snapchat refuses to switch an existing ad to another creative (E1008)'
                     + (' and to change the sub-creatives of an ad\'s own Story creative (E2003)' if STORY13 else '') +
                     ', so these stay manual (only new ads could split them, and you chose not to create new ads).')
        if not any(r['st'] == BL for r in recs): notes.pop(3)
    for n in notes:
        sm.cell(row, 1, '- ' + n).font = BODY; sm.merge_cells(start_row=row, start_column=1, end_row=row, end_column=16); sm.cell(row, 1).alignment = WRAP; sm.row_dimensions[row].height = 28; row += 1
    for i, w in enumerate([26, 11, 11, 10, 11, 10, 11, 11, 10, 11, 10, 11, 11, 10, 11, 10], 1): sm.column_dimensions[get_column_letter(i)].width = w
else:
    sm['A4'] = 'Ad URL slots and ads'; sm['A4'].font = H2
    hdr = ['Platform', 'URL slots', 'Slots wrong before', '% wrong before', 'Slots wrong now', '% wrong now', 'Fixed 12-Oct', 'Fixed 11-Oct', 'Not applied - needs your OK',
           'Manual - you', 'Failed / skipped', 'Ads with a URL', 'Ads wrong before', '% ads wrong before', 'Ads wrong now', '% ads wrong now', PENDING]
    for i, h in enumerate(hdr, 1):
        c = sm.cell(5, i, h); c.font = HDR; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical='center')
    plats = ['meta', 'tiktok', 'snapchat', 'x', 'google', 'linkedin']
    row = 6
    P, K, VB, VN, ST, FR = rng('Platform'), rng('Kind'), rng('Verdict before'), rng('Verdict now'), rng('Status'), rng('First row of ad')
    AB, AN = rng('Ad verdict before'), rng('Ad verdict now')
    for p in plats + ['ALL']:
        pc = f'"{p}"' if p != 'ALL' else '"*"'
        sm.cell(row, 1, p if p != 'ALL' else 'All platforms').font = BOLD if p == 'ALL' else BODY
        f = lambda extra: f'=COUNTIFS({P},{pc},{K},"Ad"{extra})'
        sm.cell(row, 2, f('')); sm.cell(row, 3, f(f',{VB},"WRONG"')); sm.cell(row, 4, f'=IF(B{row}=0,0,C{row}/B{row})')
        sm.cell(row, 5, f(f',{VN},"WRONG"')); sm.cell(row, 6, f'=IF(B{row}=0,0,E{row}/B{row})')
        sm.cell(row, 7, f(f',{ST},"Fixed 12-Oct"')); sm.cell(row, 8, f(f',{ST},"Fixed 11-Oct"')); sm.cell(row, 9, f(f',{ST},"Not applied - needs your OK"'))
        sm.cell(row, 10, f(f',{ST},"Manual - you"')); sm.cell(row, 11, f'=' + f(f',{ST},"Failed"')[1:] + '+' + f(f',{ST},"Skipped"')[1:])
        sm.cell(row, 12, f(f',{FR},1')); sm.cell(row, 13, f(f',{FR},1,{AB},"WRONG"')); sm.cell(row, 14, f'=IF(L{row}=0,0,M{row}/L{row})')
        sm.cell(row, 15, f(f',{FR},1,{AN},"WRONG"')); sm.cell(row, 16, f'=IF(L{row}=0,0,O{row}/L{row})'); sm.cell(row, 17, f(f',{ST},"{PENDING}"'))
        for c in (4, 6, 14, 16): sm.cell(row, c).number_format = '0.0%'
        for c in range(2, 18): sm.cell(row, c).font = BOLD if p == 'ALL' else BODY
        row += 1
    row += 1
    sm.cell(row, 1, 'Switched-on ads (delivering now)').font = H2; row += 1
    for i, h in enumerate(['Scope', 'Ads', 'Wrong before', '% before', 'Wrong now', '% now'], 1):
        c = sm.cell(row, i, h); c.font = HDR; c.fill = HFILL
    row += 1
    ON = rng('Switched on')
    sm.cell(row, 1, 'Switched-on ads'); sm.cell(row, 2, f'=COUNTIFS({K},"Ad",{FR},1,{ON},"Yes")'); sm.cell(row, 3, f'=COUNTIFS({K},"Ad",{FR},1,{ON},"Yes",{AB},"WRONG")')
    sm.cell(row, 4, f'=IF(B{row}=0,0,C{row}/B{row})'); sm.cell(row, 5, f'=COUNTIFS({K},"Ad",{FR},1,{ON},"Yes",{AN},"WRONG")'); sm.cell(row, 6, f'=IF(B{row}=0,0,E{row}/B{row})')
    for c in (4, 6): sm.cell(row, c).number_format = '0.0%'
    row += 2
    sm.cell(row, 1, 'Google sitelinks (one row per asset)').font = H2; row += 1
    for i, h in enumerate(['Scope', 'Assets', 'Wrong before', '% before', 'Wrong now', '% now', 'Placements'], 1):
        c = sm.cell(row, i, h); c.font = HDR; c.fill = HFILL
    row += 1
    PL = rng('Sitelink placements')
    sm.cell(row, 1, 'Sitelink assets'); sm.cell(row, 2, f'=COUNTIFS({K},"Sitelink")'); sm.cell(row, 3, f'=COUNTIFS({K},"Sitelink",{VB},"WRONG")'); sm.cell(row, 4, f'=IF(B{row}=0,0,C{row}/B{row})')
    sm.cell(row, 5, f'=COUNTIFS({K},"Sitelink",{VN},"WRONG")'); sm.cell(row, 6, f'=IF(B{row}=0,0,E{row}/B{row})'); sm.cell(row, 7, f'=SUMIFS({PL},{K},"Sitelink")')
    for c in (4, 6): sm.cell(row, c).number_format = '0.0%'
    row += 2
    sm.cell(row, 1, 'How to read it').font = H2; row += 1
    notes = [
        '"Wrong now" counts every slot whose live URL is not the URL the final rules give - that includes the ones still waiting for your OK and the manual ones.',
        '"Not applied - needs your OK": planned and reviewed, but the session safety check stopped the live write. "' + PENDING + '": reviewed and ready, not yet written when this workbook was built. The ready URL is in "Not applied - needs your OK".',
        '"Manual - you": shared creatives / cards / sitelinks that would need two different URLs (split them by hand), plus anything a platform refused.',
        'Every write was re-read before and after; "Changes applied" has the before / after read back for each one.',
        'Ads created after the 11-Oct pull are listed in "New ads since 11-Oct" and are not counted in the percentages.',
    ]
    for n in notes:
        sm.cell(row, 1, '- ' + n).font = BODY; sm.merge_cells(start_row=row, start_column=1, end_row=row, end_column=14); sm.cell(row, 1).alignment = WRAP; sm.row_dimensions[row].height = 28; row += 1
    for i, w in enumerate([22, 10, 12, 10, 12, 10, 11, 11, 14, 11, 11, 11, 12, 10, 12, 10, 12], 1): sm.column_dimensions[get_column_letter(i)].width = w
sm.freeze_panes = 'A6'
wb.save(OUT)
if EXP: json.dump(EXP, open(os.environ.get('EXPECTED_FILE') or f'{W}/work/summary_expected.json', 'w'), indent=0)
# python-side numbers (for the summary check)
ad = [r for r in recs if r['kind'] == 'Ad']; sl = [r for r in recs if r['kind'] == 'Sitelink']
c = collections.Counter(r['st'] for r in ad)
print('ad slots', len(ad), 'wrong before', sum(r['before'] == 'WRONG' for r in ad), 'wrong now', sum(r['vnow'] == 'WRONG' for r in ad), dict(c))
ads = {(r['s']['platform'], r['s'].get('account_id'), str(r['s'].get('ad_id'))) for r in ad}
print('ads', len(ads), 'wrong before', sum(agg(ad_b[a]) == 'WRONG' for a in ads), 'wrong now', sum(agg(ad_n[a]) == 'WRONG' for a in ads))
print('sitelinks', len(sl), 'wrong now', sum(r['vnow'] == 'WRONG' for r in sl))
