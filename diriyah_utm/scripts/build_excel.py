"""Verification workbook: every live ad + URL slot (with ad name), formulas for %, 7-Oct sheet audit, change list, blocked list."""
import sys, os, json, re, collections
from urllib.parse import urlsplit, parse_qsl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.formatting.rule import FormulaRule

scored_path, sheet_ads_path, plan_path, out_path = sys.argv[1:5]
applied_path = sys.argv[5] if len(sys.argv) > 5 else None
S = json.load(open(scored_path)); sheet_ads = json.load(open(sheet_ads_path)); PLAN = json.load(open(plan_path))
applied = {}
if applied_path and os.path.exists(applied_path):
    for line in open(applied_path):
        if line.strip():
            a = json.loads(line)
            for aid in a.get('ad_ids') or []:
                applied[(a['platform'], str(aid), a.get('slot'))] = a

OFF = re.compile(r'PAUSED|DISABLE|INVALID|NOT_SERVING|REJECTED|DONE|ARCHIVED|REMOVED|ENDED|COMPLETED|DRAFT|HOLD', re.I)
def is_on(s):
    for k in ('campaign_status', 'adset_status', 'ad_status'):
        v = s.get(k)
        if v is not None and not re.match(r'\s*(ACTIVE|ENABLE|ENABLED|SERVING)', str(v), re.I): return False
    return not OFF.search(str(s.get('effective_status') or ''))

F = 'Arial'
HDR = Font(name=F, bold=True, color='FFFFFF'); HFILL = PatternFill('solid', fgColor='1F3864')
BODY = Font(name=F, size=10); BOLD = Font(name=F, size=10, bold=True)
TITLE = Font(name=F, size=14, bold=True); H2 = Font(name=F, size=12, bold=True); NOTE = Font(name=F, size=9, italic=True, color='595959')
WRAP = Alignment(wrap_text=True, vertical='top'); TOP = Alignment(vertical='top')
RED = PatternFill('solid', fgColor='F8CBAD'); GREEN = PatternFill('solid', fgColor='C6EFCE'); AMBER = PatternFill('solid', fgColor='FFE699')

def table(ws, headers, rows, name, widths, wrap_cols=(), start_row=None):
    if start_row: 
        while ws.max_row < start_row - 1: ws.append([])
    ws.append(headers)
    hr = ws.max_row
    for c in ws[hr]:
        c.font = HDR; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical='center')
    for r in rows:
        ws.append(r)
        for i, c in enumerate(ws[ws.max_row], 1):
            c.font = BODY; c.alignment = WRAP if i in wrap_cols else TOP
    last = max(ws.max_row, hr + 1)
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    t = Table(displayName=name, ref=f'A{hr}:{get_column_letter(len(headers))}{last}')
    t.tableStyleInfo = TableStyleInfo(name='TableStyleLight1', showRowStripes=True)
    ws.add_table(t); ws.freeze_panes = ws.cell(hr + 1, 1)
    return hr, last

viol = lambda v: '\n'.join(m for _, m in v)
wb = Workbook()

# ---------------- Every URL (live) ----------------
ws = wb.active; ws.title = 'Every URL (live)'
H = ['Platform', 'Account', 'Campaign', 'Ad set / ad group', 'Ad name', 'Ad ID', 'Kind', 'Status', 'Switched on',
     'URL slot', 'Live URL (11-Oct, before fix)', 'Verdict', 'What is wrong', 'Correct URL (from generator)', 'Action',
     'Why / generator basis', 'First row of ad', 'Ad verdict', 'Fix result', 'Live URL after fix']
# dedupe sitelink link-rows to one row per asset URL; keep all ad slots
rows_src, seen = [], set()
for s in S:
    kind = 'Sitelink' if 'sitelink' in str(s.get('slot') or '').lower() else 'Ad'
    if kind == 'Sitelink':
        k = (s['platform'], s.get('account_id'), s.get('ad_id'), s.get('url'))
        if k in seen: continue
        seen.add(k)
    s['_kind'] = kind; s['_on'] = is_on(s); rows_src.append(s)
rows_src.sort(key=lambda s: (s['platform'], str(s.get('account_name')), s['_kind'], str(s.get('campaign_name')), str(s.get('adset_name')), str(s.get('ad_name')), str(s.get('ad_id')), str(s.get('slot'))))
adv = collections.defaultdict(list)
for s in rows_src: adv[(s['platform'], s.get('account_id'), str(s.get('ad_id')))].append(s['verdict'])
def ad_verdict(k):
    v = adv[k]
    if 'WRONG' in v: return 'WRONG'
    if all(x == 'NO URL' for x in v): return 'NO URL'
    if all(x in ('CORRECT', 'NO URL') for x in v): return 'CORRECT'
    return 'UNTRACEABLE'
UNIT = {'meta': 'ad_id', 'snapchat': 'creative_id', 'tiktok': 'ad_id', 'google': 'ad_id', 'linkedin': 'creative_id', 'x': 'creative_id'}
SKIP = {(k['platform'], k['account_id'], k['unit']): k['skip_reason'] for k in PLAN['skipped']}
def unit_of(s):
    return (s['platform'], s.get('account_id'), str(s.get(UNIT[s['platform']]) or s.get('ad_id')))
rows, firsts = [], set()
for s in rows_src:
    k = (s['platform'], s.get('account_id'), str(s.get('ad_id')))
    first = 0 if k in firsts else 1; firsts.add(k)
    if s['verdict'] == 'NO URL': action = 'No URL to tag'
    elif s['verdict'] == 'CORRECT': action = 'None - already correct'
    elif s['derive_status'] == 'FIX' and unit_of(s) in SKIP: action = 'Decision needed'
    elif s['derive_status'] == 'FIX': action = 'Fix to generator URL'
    elif any(r.startswith('CONFLICT') for r in s['derive_reasons']): action = 'Decision needed'
    else: action = 'Blocked - needs generator entry'
    why = '\n'.join(s['derive_reasons']) if s['derive_status'] in ('BLOCKED', 'NO_URL') else '\n'.join(s.get('basis') or [])
    if action == 'Decision needed' and s['derive_status'] == 'FIX': why = 'Shared creative/card: ' + SKIP[unit_of(s)] + '\n' + why
    ap = applied.get((s['platform'], str(s.get('ad_id')), s.get('slot')), {})
    rows.append([s['platform'], s.get('account_name'), s.get('campaign_name'), s.get('adset_name'), s.get('ad_name'), str(s.get('ad_id')),
                 s['_kind'], s.get('effective_status') or s.get('ad_status'), 'Yes' if s['_on'] else 'No', s.get('slot'), s.get('url'),
                 s['verdict'], viol(s['violations']) or (s.get('notes') if s['verdict'] == 'NO URL' else ''), s.get('expected_url'), action, why,
                 first, ad_verdict(k), ap.get('result', ''), ap.get('after_live', '')])
f1, l1 = table(ws, H, rows, 'EveryURL', [10, 24, 42, 42, 44, 22, 9, 16, 9, 28, 70, 12, 50, 70, 24, 60, 8, 11, 12, 70],
               wrap_cols=(3, 4, 5, 11, 13, 14, 16, 20))
for col, val, fill in (('L', 'WRONG', RED), ('L', 'CORRECT', GREEN), ('L', 'UNTRACEABLE', AMBER), ('S', 'Fixed', GREEN), ('S', 'Failed', RED)):
    ws.conditional_formatting.add(f'{col}{f1+1}:{col}{l1}', FormulaRule(formula=[f'${col}{f1+1}="{val}"'], fill=fill))
LV = "'Every URL (live)'"
rng = lambda c: f"{LV}!${c}${f1+1}:${c}${l1}"

# ---------------- 7-Oct sheet audit ----------------
ws3 = wb.create_sheet('7-Oct sheet audit')
H3 = ['Platform', 'Campaign', 'Ad set', 'Ad name', 'Ad ID', 'Final URL in the 7-Oct sheet', 'Tab it came from', 'Written by Claude',
      'What the sheet claimed', 'Compliant with nomenclature', 'Breaks format rules (beyond objective)', 'What is wrong']
r3 = []
for a in sheet_ads:
    if not a.get('final_url'): continue
    codes = {e[0] for e in a['errors']}
    claim = a.get('outcome') or ''
    if a.get('rollout_result'): claim = (claim + ' | ' if claim else '') + 'Rollout: ' + str(a['rollout_result'])
    r3.append([a.get('platform'), a.get('campaign'), a.get('adset'), a.get('ad_name_after') or a.get('ad_name'), a['ad_id'], a['final_url'],
               a['final_src'], 'Yes' if a['claude_wrote_final'] else 'No', claim, 'No' if a['errors'] else 'Yes',
               'Yes' if codes - {'CAMPAIGN_NO_OBJECTIVE'} else 'No', viol(a['errors'])])
f3, l3 = table(ws3, H3, r3, 'SheetAudit', [12, 40, 40, 44, 22, 70, 22, 10, 34, 12, 14, 60], wrap_cols=(2, 3, 4, 6, 9, 12))
AU = "'7-Oct sheet audit'"
ar = lambda c: f"{AU}!${c}${f3+1}:${c}${l3}"

# ---------------- Changes ready (awaiting approval / applied) ----------------
ws6 = wb.create_sheet('Changes ready')
r6 = []
for p in PLAN['plan']:
    for c in p['changes']:
        qa = dict(parse_qsl(urlsplit(c[3]).query)); qb = dict(parse_qsl(urlsplit(c[4]).query))
        what = '; '.join(f'{k}: {qa.get(k)} -> {qb.get(k)}' for k in sorted(set(qa) | set(qb)) if qa.get(k) != qb.get(k))
        ap = applied.get((p['platform'], p['ad_ids'][0], c[0]), {})
        r6.append([p['platform'], p['account_name'], p['campaign_name'], p['adset_name'], '\n'.join(p['ad_names']), '\n'.join(p['ad_ids']),
                   p['status'], c[0], c[3], c[4], what, ap.get('result', 'Awaiting approval'), ap.get('detail', '')])
table(ws6, ['Platform', 'Account', 'Campaign', 'Ad set', 'Ad name', 'Ad ID', 'Status', 'URL slot', 'Live URL now', 'Generator URL', 'What changes', 'Result', 'Detail'],
      r6, 'Changes', [10, 24, 40, 40, 44, 22, 14, 26, 70, 70, 50, 16, 40], wrap_cols=(3, 4, 5, 6, 9, 10, 11, 13))

# ---------------- Blocked / decisions ----------------
ws4 = wb.create_sheet('Blocked & decisions')
grp = collections.defaultdict(list)
for s in rows_src:
    if s['verdict'] != 'NO URL' and s['derive_status'] == 'BLOCKED':
        reason = s['derive_reasons'][0]
        key = re.sub(r'"[^"]*"', '"…"', reason) if 'not in generator format' in reason else reason
        grp[(s['platform'], s.get('account_name'), key)].append(s)
for sk in PLAN['skipped']:
    grp[(sk['platform'], sk['account_name'], 'Shared creative/card: ' + sk['skip_reason'][:120])].append({'ad_name': ', '.join(sk['ad_names']), 'ad_id': sk['unit'], 'campaign_name': sk['campaign_name'], '_on': False})
r4 = []
for (p, acct, reason), items in sorted(grp.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
    camps = sorted({str(i.get('campaign_name')) for i in items})
    names = sorted({str(i.get('ad_name')) for i in items})
    r4.append([p, acct, reason, len(items), sum(1 for i in items if i.get('_on')),
               '\n'.join(camps[:8]) + (f'\n… +{len(camps)-8} more' if len(camps) > 8 else ''),
               '\n'.join(names[:8]) + (f'\n… +{len(names)-8} more' if len(names) > 8 else '')])
table(ws4, ['Platform', 'Account', 'Why it is not fixed from the generator', 'URL slots', 'of which switched on', 'Campaigns', 'Ad names (sample)'],
      r4, 'Blocked', [10, 24, 70, 10, 12, 55, 55], wrap_cols=(3, 6, 7))

# ---------------- Rules ----------------
ws5 = wb.create_sheet('Rules used')
rules = [
    ('utm_source', 'Mappings col A list; = the campaign-name channel; must belong to the platform', 'Schema row 6'),
    ('utm_medium', 'Mappings col B list; from the Input_Campaign_Generator row(s) for the same source + campaign when they agree, else the current value if valid', 'Schema row 7'),
    ('utm_campaign', '{Campaign Unique ID}_{campaign name}_{mon}{yy}_{objective}, lower-case; tokens from the generator-format campaign name', 'Schema row 8 / Output formula'),
    ('utm_term', '{Adset Unique ID}_{ad set name}_{ad set language} - language from the AD SET name, not the ad', 'Schema row 9 / Output formula'),
    ('utm_content', '{Ad Unique ID}_{ad name}_{ad format}_{ad language}', 'Schema row 10 / Output formula'),
    ('Unique IDs', 'Only the 8-character IDs in Campaign_Code_Generator; nothing invented (no ad-id-AD1001, adset-id-XXXXXX, RSA1...)', 'Campaign_Code_Generator'),
    ('Explicit generator rows', 'If an Output row exists for the exact source/ad set/ad and agrees with the campaign: confirmed. Same objective but different month: flagged as a decision. Different objective: belongs to another campaign, ignored.', 'Input/Output_Campaign_Generator'),
    ('utm_id', 'Not added; removed where present', 'User decision 11-Oct'),
    ('Objective', 'Added to every utm_campaign', 'User decision 11-Oct'),
    ('kva / kvb / kvd', 'Programmatic only; on social or search the ad is flagged until a social/search code exists', 'User decision 11-Oct'),
    ('Ritz Google search', 'utm_content = 78f964bb_rcsr-search_search_{lang}', 'User decision 11-Oct (Campaign_Code_Generator)'),
    ('Sitelinks', 'No generator creative code exists for sitelinks: counted and flagged, not changed', 'No assumption'),
    ('Landing page', 'Kept as is; only the UTM query is rebuilt; click ids (fbclid etc.) removed', 'No change to user journey'),
    ('Scope', 'Every ad in every Meta, TikTok, Snapchat, LinkedIn, X and Google Ads account whose name contains "Diriyah" or "Wadi", pulled live 11-Oct-2026 via Whathead', 'User instruction 11-Oct'),
]
table(ws5, ['Rule', 'What is required', 'Source'], rules, 'Rules', [22, 100, 40], wrap_cols=(2,))

# ---------------- Summary (formulas only) ----------------
w0 = wb.create_sheet('Summary', 0)
w0['A1'] = 'Diriyah / Wadi Safar UTM verification vs Campaign Nomenclature Generator'; w0['A1'].font = TITLE
w0['A2'] = ('Live pull 11-Oct-2026 of every ad in every ad account whose name contains "Diriyah" or "Wadi" (Meta, TikTok, Snapchat, LinkedIn, X, Google Ads). '
            'All figures are formulas over the "Every URL (live)" and "7-Oct sheet audit" tabs.')
w0['A2'].font = NOTE; w0['A2'].alignment = WRAP; w0.merge_cells('A2:K2'); w0.row_dimensions[2].height = 28
w0['A4'] = 'Live ads (Google sitelinks shown separately)'; w0['A4'].font = H2
hdr = ['Platform', 'Ads', 'Ads with a URL', 'Ads wrong', '% ads wrong', 'URL slots', 'Slots wrong', '% slots wrong', 'Fixable from generator', 'Blocked / decision', 'Fixed live']
w0.append(hdr)
for c in w0[w0.max_row]: c.font = HDR; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical='center')
plats = sorted({s['platform'] for s in rows_src})
def frow(label, extra):
    r = w0.max_row + 1
    base = f'{rng("G")},"Ad"' + extra
    w0.append([label,
               f'=COUNTIFS({base},{rng("Q")},1)',
               f'=COUNTIFS({base},{rng("Q")},1,{rng("R")},"<>NO URL")',
               f'=COUNTIFS({base},{rng("Q")},1,{rng("R")},"WRONG")',
               f'=IF(C{r}=0,0,D{r}/C{r})',
               f'=COUNTIFS({base},{rng("L")},"<>NO URL")',
               f'=COUNTIFS({base},{rng("L")},"WRONG")',
               f'=IF(F{r}=0,0,G{r}/F{r})',
               f'=COUNTIFS({base},{rng("O")},"Fix to generator URL")',
               f'=COUNTIFS({base},{rng("O")},"Blocked*")+COUNTIFS({base},{rng("O")},"Decision needed")',
               f'=COUNTIFS({base},{rng("S")},"Fixed")'])
    for c in w0[r]: c.font = BOLD if label.startswith(('ALL', 'Switched')) else BODY
    w0[f'E{r}'].number_format = '0.0%'; w0[f'H{r}'].number_format = '0.0%'
for p in plats: frow(p, f',{rng("A")},"{p}"')
frow('ALL ADS', '')
frow('Switched on now', f',{rng("I")},"Yes"')
r = w0.max_row + 1
w0.append(['Google sitelinks', f'=COUNTIFS({rng("G")},"Sitelink")', f'=COUNTIFS({rng("G")},"Sitelink",{rng("L")},"<>NO URL")',
           f'=COUNTIFS({rng("G")},"Sitelink",{rng("L")},"WRONG")', f'=IF(C{r}=0,0,D{r}/C{r})'])
for c in w0[r]: c.font = BODY
w0[f'E{r}'].number_format = '0.0%'
w0.append([]); w0.append(['Ads with no readable URL (LinkedIn posts 403, Meta boosted posts, media-only tweets, TikTok ads without landing page) are counted in "Ads" but not in "Ads with a URL".'])
w0.cell(w0.max_row, 1).font = NOTE
w0.append([])
w0.append(['The 7-Oct "open_items_resolved" sheet']); w0.cell(w0.max_row, 1).font = H2
w0.append(['Measure', 'Count', '% of sheet URLs'])
for c in w0[w0.max_row]: c.font = HDR; c.fill = HFILL
b = w0.max_row
for i, (lbl, fml) in enumerate([
        ('URLs in the sheet (latest per ad)', f'=COUNTA({ar("F")})'),
        ('Not compliant with the nomenclature', f'=COUNTIFS({ar("J")},"No")'),
        ('Break format rules beyond the missing objective', f'=COUNTIFS({ar("K")},"Yes")'),
        ('Written or changed by Claude and not compliant', f'=COUNTIFS({ar("H")},"Yes",{ar("J")},"No")'),
        ('Marked "Correct"/"no change needed"/"Verified live" and not compliant', f'=COUNTIFS({ar("I")},"*Correct*",{ar("J")},"No")+COUNTIFS({ar("I")},"*Verified*",{ar("J")},"No")-COUNTIFS({ar("I")},"*Correct*",{ar("I")},"*Verified*",{ar("J")},"No")'),
        ('Contain an XXXX placeholder', f'=COUNTIFS({ar("L")},"*placeholder*")'),
        ('Use codes not in the generator (ad-id-/adset-id-)', f'=COUNTIFS({ar("L")},"*legacy*ad-id*")')]):
    rr = b + 1 + i
    w0.append([lbl, fml, f'=IF($B${b+1}=0,0,B{rr}/$B${b+1})'])
    for c in w0[rr]: c.font = BODY
    w0[f'C{rr}'].number_format = '0.0%'
w0.column_dimensions['A'].width = 62
for i, w in enumerate([62, 9, 12, 10, 10, 10, 11, 11, 12, 12, 10], 1): w0.column_dimensions[get_column_letter(i)].width = w
wb.save(out_path)
print('saved', out_path, 'live rows', len(rows), 'sheet rows', len(r3), 'changes', len(r6), 'blocked groups', len(r4))
