"""v5 (12-Oct review): one live campaign = one utm_campaign name, one live ad set = one utm_term name.
Legacy / omit targets (never generator-derived ones) take the name that their sibling ads in the same live campaign / ad set
already get, when that name is clearly dominant (>= 2 rows and >= 60% of the named rows; generator rows win when present):
  - a missing name is filled from the siblings
  - a different name (an old token copied from another campaign, e.g. a Ramadan token inside a Summer campaign) is replaced
Ads with the same name (language / copy / date marks removed) in the same live campaign share the ad-name part when theirs is missing.
Month, objective, languages and format stay per row. Rewrites work/targets.json; lists every change in work/consistency_fixes.json."""
import sys, os, json, re, collections, glob
from urllib.parse import urlsplit, urlunsplit, parse_qsl, quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from derive import Deriver, MONTHS
from omit import check_omit
from legacy import Legacy
W = sys.argv[1]
N = Deriver(glob.glob(f'{W}/in/e2e*.xlsx')[0], {}).N
T = json.load(open(f'{W}/work/targets.json'))
MON = re.compile(r'(' + '|'.join(MONTHS) + r')\d\d')
HEX = re.compile(r'[0-9a-f]{8}')

def parts(url):
    p = urlsplit(url.strip()); return p, parse_qsl(p.query, keep_blank_values=True)

def split_camp(v):
    t = [x for x in (v or '').split('_') if x]; obj = t.pop() if t and t[-1] in N.objectives else None
    mon = t.pop() if t and MON.fullmatch(t[-1]) else None; uid = t.pop(0) if t and HEX.fullmatch(t[0]) else None
    return uid, '_'.join(t) or None, mon, obj

def split_term(v):
    t = [x for x in (v or '').split('_') if x]; lang = t.pop() if t and t[-1] in N.langs else None
    uid = t.pop(0) if t and HEX.fullmatch(t[0]) else None
    return uid, '_'.join(t) or None, lang

def split_content(v):
    t = [x for x in (v or '').split('_') if x]; lang = t.pop() if t and t[-1] in N.langs else None
    fmt = t.pop() if t and t[-1] in N.formats else None; uid = t.pop(0) if t and HEX.fullmatch(t[0]) else None
    return uid, '_'.join(t) or None, fmt, lang

def rebuild(url, new):
    p, q = parts(url)
    keep = [(k, v) for k, v in q if not k.lower().startswith('utm_')]
    cur = dict((k, v) for k, v in q if k.lower().startswith('utm_'))
    cur.update(new)
    utm = [(k, cur[k]) for k in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content') if cur.get(k)]
    query = '&'.join(f'{k}={quote(v, safe="-_.~{}/:")}' for k, v in keep + utm)
    return urlunsplit((p.scheme, p.netloc, p.path, query, p.fragment))

j = lambda xs: '_'.join(x for x in xs if x)
GENERIC = ('campaigns', 'campaign', 'tactical', 'company', 'alwayson', 'generic', 'brand')
def belongs(name, *live):
    """strict: every 4+ letter word of the name (generic words aside) must be covered by 4-letter runs of the live names"""
    hay = re.sub(r'[^a-z0-9]', '', ' '.join(str(x or '') for x in live).lower())
    for w in re.findall(r'[a-z]+', name or ''):
        for g in GENERIC: w = w.replace(g, ' ')
        for piece in w.split():
            if piece == 'hs' or len(piece) < 4: continue
            cov = [False] * len(piece)
            for i in range(len(piece) - 3):
                if piece[i:i + 4] in hay: cov[i:i + 4] = [True] * 4
            if re.search(r'0{3,}', ''.join('1' if x else '0' for x in cov)): return False
    return True
rows = [r for r in T if r.get('target') and 'sitelink' not in str(r['slot']).lower()]
def dominant(group, getter, ok=lambda r, name: True):
    gen = collections.Counter(getter(r) for r in group if r['source'] in ('generator', 'clash') and getter(r)[1])
    if len(gen) == 1: return next(iter(gen)), 'generator-derived siblings'
    c = collections.Counter(getter(r) for r in group if getter(r)[1] and (getter(r)[0] or ok(r, getter(r)[1])))
    if not c: return None, None
    (val, n), tot = c.most_common(1)[0], sum(c.values())
    if n >= 2 and n / tot >= 0.6 and (len(c) == 1 or c.most_common(2)[1][1] < n): return val, f'{n} of {tot} sibling ads'
    return None, None

fixes = []
q_of = lambda r: dict(parse_qsl(urlsplit(r['target']).query))
# campaign name / ad set name. Rule: a missing name is filled from the dominant sibling name; a present name is replaced only
# when it does NOT match the live campaign / ad set (strict check) while the dominant sibling name does. Nothing is dropped here.
def harmonise(g, part, get, strict, compose):
    dom_s, why_s = dominant(g, get, strict)          # only names that match the live entity (or carry a generator code) vote
    dom_l, why_l = dominant(g, get)
    for r in g:
        if r['source'] in ('generator', 'clash'): continue
        uid, name = get(r)
        if not name:
            d, why = (dom_s, why_s) if dom_s else (dom_l, why_l)
            if not d: continue
            msg = f'{part} "{d[1]}" filled from {why} in the same live {"campaign" if part == "campaign name" else "ad set"}'
        elif dom_s and (uid, name) != dom_s and not uid and not strict(r, name):
            d = dom_s
            msg = f'{part} "{d[1]}" used by {why_s} in the same live {"campaign" if part == "campaign name" else "ad set"} (this ad\'s old token "{name}" names another one)'
        else: continue
        new = compose(r, d)
        if not new: continue
        fixes.append({'platform': r['platform'], 'ad_id': r['ad_id'], 'slot': r['slot'], 'part': 'utm_campaign name' if part == 'campaign name' else 'utm_term name',
                      'old': name, 'new': d[1], 'why': msg, 'old_target': r['target'], 'target': new})
        r['target'] = new; r.setdefault('consistency', []).append(msg)
by = collections.defaultdict(list)
for r in rows: by[(r['platform'], r['account_id'], r.get('campaign_id') or r.get('campaign_name'))].append(r)
def comp_c(r, d):
    uid, name, mon, obj = split_camp(q_of(r).get('utm_campaign')); return rebuild(r['target'], {'utm_campaign': j([d[0], d[1], mon, obj])})
for g in by.values():
    harmonise(g, 'campaign name', lambda r: split_camp(q_of(r).get('utm_campaign'))[:2], lambda r, n: belongs(n, r.get('campaign_name')), comp_c)
by = collections.defaultdict(list)
for r in rows:
    if r.get('adset_id'): by[(r['platform'], r['account_id'], r['adset_id'])].append(r)
def comp_t(r, d):
    uid, name, lang = split_term(q_of(r).get('utm_term'))
    return rebuild(r['target'], {'utm_term': j([d[0], d[1], lang])}) if lang else None
for g in by.values():
    harmonise(g, 'ad set name', lambda r: split_term(q_of(r).get('utm_term'))[:2], lambda r, n: belongs(n, r.get('adset_name'), r.get('campaign_name')), comp_t)
# ad name: same live campaign + same ad name apart from language / copy / dates -> share a missing ad-name part
def norm_ad(n):
    n = str(n or '').lower()
    n = re.sub(r'\[copy\]|-?\s*copy(\s*\d+)?|\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{4}-\d{2}-\d{2}[ \d:]*', ' ', n)
    n = re.sub(r'(^|[_\s-])(en|ar|english|arabic|enar|en-ar)(?=[_\s-]|$)', ' ', n)
    return re.sub(r'[^a-z0-9]+', '', n)
by = collections.defaultdict(list)
for r in rows:
    if r.get('ad_name') and len(norm_ad(r['ad_name'])) >= 6: by[(r['platform'], r['account_id'], r.get('campaign_id'), norm_ad(r['ad_name']))].append(r)
for k, g in by.items():
    get = lambda r: split_content(q_of(r).get('utm_content'))[:2]
    dom, why = dominant(g, get)
    if not dom: continue
    for r in g:
        if r['source'] in ('generator', 'clash'): continue
        uid, name, fmt, lang = split_content(q_of(r).get('utm_content'))
        if name or not (fmt or lang): continue
        if Legacy.num_conflict(None, dom[1], r.get('ad_name')): continue   # sibling name names another cut than this ad
        new = rebuild(r['target'], {'utm_content': j([dom[0], dom[1], fmt, lang])})
        fixes.append({'platform': r['platform'], 'ad_id': r['ad_id'], 'slot': r['slot'], 'part': 'utm_content name', 'old': None, 'new': dom[1],
                      'why': f'ad name part "{dom[1]}" used by {why} with the same ad name in this live campaign', 'old_target': r['target'], 'target': new})
        r['target'] = new; r.setdefault('consistency', []).append(fixes[-1]['why'])
bad = [(r['ad_id'], e) for r in rows for e in check_omit(N, r['target'])]
json.dump(T, open(f'{W}/work/targets.json', 'w'), indent=1, default=str)
json.dump(fixes, open(f'{W}/work/consistency_fixes.json', 'w'), indent=1, default=str)
print('consistency fixes', collections.Counter((f['platform'], f['part'], 'filled' if not f['old'] else 'replaced') for f in fixes), 'check errors', bad[:5], len(bad))
