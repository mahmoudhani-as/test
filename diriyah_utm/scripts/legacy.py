"""Legacy rebuild (user rule 11-Oct: 'drop the code if it doesn't exist in the generator sheet').
Tokens come only from: generator codes; codes already used by sibling ads in the same live campaign / ad set;
the URL's own name tokens; the legacy entity names (objective, language, format words); first-serving month (filled later)."""
import re, json, sys, os, collections
from urllib.parse import urlsplit, urlunsplit, parse_qsl, quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from derive import PLATFORM_SOURCES, CLICK_IDS

OBJ = {'AWR': 'awr', 'CONV': 'conv', 'LEAD': 'conv', 'TRF': 'cond'}   # generator rows: lf+leads->conv (32/32), mf/lf+traffic->cond (11/11)
CHANNEL = {'meta': 'meta', 'x': 'x', 'tiktok': 'tiktok', 'snapchat': 'snapchat', 'linkedin': 'linkedin', 'googlesearch': 'google', 'google': 'google'}
CODE_PREFIX = re.compile(r'^(?:(?:ad|adset|adgroup|cam|creative)-id-(?:\{[a-z_]+\}|[0-9a-z]+)|[0-9a-f]{8})[_-]', re.I)
PLACEHOLDER = re.compile(r'(^|[-_])(test|x{3,}|\{[a-z_]+\})([-_]|$)|test-?ad(set)?-?name|^ad(set|group)?-?name$', re.I)

def slug(s):
    s = re.sub(r'[^a-z0-9_-]+', '-', s.strip().lower())
    return re.sub(r'-{2,}', '-', re.sub(r'[\s_]+', '-', s)).strip('-')

# v6 (12-Oct second review)
def repair_query(url):
    """Old URLs: an unencoded '&' inside a value (utm_campaign=H&S_DGCL_...) and mangled keys (http://utm_source=) are repaired so the
    old tokens parse; the FIRST occurrence of each utm_ key wins (a template pasted after the ad's own block does not override it)."""
    p = urlsplit((url or '').strip())
    if not p.query: return (url or '').strip()
    out = []
    for sg in p.query.split('&'):
        if '=' not in sg and out and out[-1].split('=', 1)[0].lower().lstrip('htps:/').startswith('utm_') and '_' in sg: out[-1] += '-' + sg
        else: out.append(sg)
    fixed, seen = [], set()
    for sg in out:
        k, eq, v = sg.partition('=')
        kk = re.sub(r'^.*/', '', k)
        if kk.lower().startswith('utm_'):
            if kk.lower() in seen: continue
            seen.add(kk.lower()); k = kk
        fixed.append(f'{k}{eq}{v}')
    return urlunsplit((p.scheme, p.netloc, p.path, '&'.join(fixed), p.fragment))
AGENCY = {'mindshare', 'tact', 'wavemaker', 'mediacom', 'essence', 'essencemediacom', 'hs', 'h-s'}
CTYPE = {'tactical', 'tac', 'ao', 'alwayson', 'always-on'}
MONTHWORD = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)(uary|ruary|ch|il|e|y|ust|tember|ober|ember)?'
def layout_name(raw):
    """generator-layout old token agency_BU_asset_type_NAME_year_month_funnel_objective_...: only the NAME position is the campaign name"""
    segs = [x for x in raw.split('_') if x]
    if len(segs) >= 6 and segs[0] in AGENCY and segs[3] in CTYPE:
        nm = re.sub(MONTHWORD + r'(19|20)\d\d$', '', segs[4]).strip('-')
        return nm or None, segs[2]
    return None, None
GENERIC_ONLY = {'brand', 'generic', 'competitors', 'competitor', 'competitive', 'restaurants', 'restaurant', 'tickets', 'ticket', 'others', 'other',
                'general', 'search', 'keywords', 'keyword', 'exact', 'phrase', 'broad', 'campaign', 'creative', 'adgroup', 'ad', 'name'}
COUNTRY = {'saudi', 'saudiarabia', 'kuwait', 'qatar', 'emirates', 'bahrain', 'oman', 'egypt', 'jordan', 'france', 'paris', 'london', 'gbr', 'uk', 'ksa', 'uae'}
NONNAME = {'riyadh', 'jeddah', 'easternprovince', 'dammam', 'khobar', 'makkah', 'madinah',
           'clicks', 'click', 'impressions', 'views', 'conversions', 'engagement', 'exact', 'phrase', 'broad', 'bmm', 'dgcl',
           'fr', 'de', 'es', 'it', 'ru', 'zh'}
GEN_LIVE_STOP = {'family', 'residential', 'visit-diriyah', 'rcsr'}
def gen_from_live(live, table):
    """a generator name that is exactly a run of segments of the live ad / ad set name (IntroVideo1_45s -> intro-video1-45s)"""
    nz = lambda x: re.sub(r'[^a-z0-9]', '', str(x).lower())
    segs = [x for x in re.split(r'[_|]+|\s+-\s+', str(live or '')) if x.strip()]
    runs = {nz(''.join(segs[i:j])) for i in range(len(segs)) for j in range(i + 1, min(len(segs), i + 4) + 1)}
    hits = [g for g in table if g not in GEN_LIVE_STOP and len(nz(g)) >= 7 and nz(g) in runs]
    return hits[0] if len(hits) == 1 else None

# v5 (12-Oct review): one objective rule for ads and sitelinks. Sources, in order: funnel+objective token (_MF_TRF_), a bare
# objective token (_Conv_, _lf_conv_), the Mappings col K definition words (awareness/consideration/conversion), and the
# sub-objective words whose generator Input rows all use one objective (reach->awr, traffic->cond, leads/sales->conv).
# Several sources that disagree -> unknown (left out).
SUBWORD = {'reach': 'awr', 'traffic': 'cond', 'leads': 'conv', 'lead': 'conv', 'sales': 'conv'}
DEFWORD = {'awareness': 'awr', 'consideration': 'cond', 'conversion': 'conv', 'conversions': 'conv'}
def objective_of(campaign_name):
    n = str(campaign_name or '')
    m = re.search(r'(?:^|[_\s-])(UF|MF|LF|UP)[_\s-](AWR|CONV|LEAD|TRF)(?=[_\s-]|$)', n, re.I)
    if m: return OBJ[m.group(2).upper()], f'objective from campaign-name token {m.group(1)}_{m.group(2)}'
    got = set(); why = []
    for t in re.findall(r'(?:^|[_\s-])(awr|cond|conv|trf|lead)(?=[_\s-]|$)', n, re.I):
        o = {'awr': 'awr', 'cond': 'cond', 'conv': 'conv', 'trf': 'cond', 'lead': 'conv'}[t.lower()]; got.add(o); why.append(f'token "{t}"')
    words = re.findall(r'[a-z]+', n.lower())
    for w in words:
        if w in DEFWORD: got.add(DEFWORD[w]); why.append(f'word "{w}" (Mappings definition)')
        elif w in SUBWORD: got.add(SUBWORD[w]); why.append(f'sub-objective "{w}" (every generator Input row with it uses {SUBWORD[w]})')
    if len(got) == 1: return got.pop(), 'objective from campaign name: ' + ', '.join(why)
    return None, None

class Legacy:
    def __init__(self, deriver, scored, deriver_path):
        self.D = deriver; self.N = deriver.N
        # words that belong to OTHER generator positions (Mappings lists) are not part of a name
        vocab = set()
        for lst in (self.N.sources, self.N.mediums, self.N.objectives, self.N.langs, self.N.formats, deriver.funnels, deriver.devices,
                    deriver.genders, deriver.strategies, deriver.types):
            for w in lst: vocab |= set(re.split(r'[-_/]', w))
        import openpyxl
        m = openpyxl.load_workbook(deriver_path, data_only=True)['Mappings']
        for col in ('C', 'I', 'K', 'L', 'R'):
            for x in m[col][1:]:
                if x.value: vocab |= set(re.split(r'[-_/\s]+', str(x.value).strip().lower()))
        vocab |= {'conversions', 'awareness', 'consideration', 'conversion', 'carousel', 'image', 'sponsoredpost', 'static', 'gif',
                  'googlesearch', 'tactical', 'diriyahcompany'}
        self.vocab = {w for w in vocab if w and len(w) >= 2}
        # codes already used by generator-format URLs in the same live campaign / ad set (sibling evidence)
        self.camp_codes = collections.defaultdict(collections.Counter)
        self.set_codes = collections.defaultdict(collections.Counter)
        for s in scored:
            if not s.get('url'): continue
            q = {k.lower(): v.lower() for k, v in parse_qsl(urlsplit(s['url']).query)}
            m = re.fullmatch(r'([0-9a-f]{8})_([^_]+)_[a-z]{3}\d{2}(?:_[a-z]+)?', q.get('utm_campaign', ''))
            if m and self.N.camp.get(m.group(2)) == m.group(1):
                self.camp_codes[(s['platform'], s.get('account_id'), s.get('campaign_id'))][(m.group(1), m.group(2))] += 1
            m = re.fullmatch(r'([0-9a-f]{8})_([^_]+)_(en-ar|ar|en|all)', q.get('utm_term', ''))
            if m and self.N.adset.get(m.group(2)) == m.group(1):
                self.set_codes[(s['platform'], s.get('account_id'), s.get('adset_id'))][(m.group(1), m.group(2))] += 1
        # v5: language of every ad in each live ad set (ad name, else landing page) - an ad set name that contradicts all of them
        # (duplicated ad set never renamed) does not set the ad set language
        self.set_ad_langs = collections.defaultdict(set)
        for s in scored:
            if not s.get('url') or 'sitelink' in str(s.get('slot')).lower(): continue
            al = self.lang_from(s.get('ad_name'))
            if al not in ('en', 'ar'):
                lp = re.search(r'/(en|ar)(/|$)', urlsplit(s['url'].strip()).path.lower()); al = lp.group(1) if lp else None
            self.set_ad_langs[(s['platform'], s.get('account_id'), s.get('adset_id'))].add(al)

    def clean(self, name):
        name = CODE_PREFIX.sub('', (name or '').lower())     # the old code prefix first (it may itself hold a {macro} id)
        name = re.sub(r'\{[^}]*\}|__[a-z_]+__', '', name)        # v6: ValueTrack / platform macros are never names ({creative} -> nothing)
        if PLACEHOLDER.search(name): return ''          # template / macro leftovers are not names
        toks = [t for t in re.split(r'[-_/]+', name) if t]
        toks = [t for t in toks if t not in NONNAME]       # v6: cities, KPI / match-type words
        while toks and len(toks[0]) == 1: toks.pop(0)     # v6: leading / trailing single letters (h-s_...), not inner ones (bab-samhan-x-qiddiya)
        while toks and len(toks[-1]) == 1: toks.pop()
        if toks and all(t in GENERIC_ONLY or t in COUNTRY for t in toks): return ''    # v6: 'restaurants' / 'brand' / 'saudi' alone is not a name
        kept = [t for t in toks if t not in self.vocab and not re.fullmatch(r'rsa\d*', t)]
        # v5: a vocabulary word that leads a name made only of numbers / durations is part of the name ('video-2-15s', not '2-15s')
        if kept and len(kept) < len(toks) and all(re.fullmatch(r'\d+[a-z]?|\d+s|v\d+', t) for t in kept):
            lead = [t for t in toks if not re.fullmatch(r'rsa\d*', t)]
            while lead and lead[-1] in self.vocab: lead.pop()
            return '-'.join(lead)
        out = '-'.join(kept)
        return out if len(re.sub(r'[^a-z]', '', out)) >= 3 or re.search(r'[a-z]{2,}\d', out) else ''   # v5: 'h' / 's' leftovers are not names

    def belongs(self, name, *live):
        hay = re.sub(r'[^a-z0-9]', '', ' '.join(str(x or '') for x in live).lower())
        words = [w for w in re.findall(r'[a-z]+', name) if w not in self.vocab and w != 'hs' and len(w) >= 4]
        if not words: return True
        for w in words:
            n = 5 if len(w) >= 5 else 4
            if any(w[i:i + n] in hay for i in range(len(w) - n + 1)): return True
        return False

    def unmatched(self, aname, s):
        # every part of the old creative token must be found in the ad's own names (ad, creative, ad set, campaign); creative ids / durations excepted
        hay = re.sub(r'[^a-z0-9]', '', ' '.join(str(s.get(k) or '') for k in ('ad_name', 'creative_name', 'adset_name', 'campaign_name')).lower())
        tok = re.sub(r'[^a-z0-9]', '', aname)
        cov = [False] * len(tok)
        for i in range(len(tok) - 3):
            if tok[i:i + 4] in hay: cov[i:i + 4] = [True] * 4
        runs = [m.group(0) for m in re.finditer(r'0+', ''.join('1' if c else '0' for c in cov))]
        gaps = [tok[m.start():m.end()] for m in re.finditer(r'0+', ''.join('1' if c else '0' for c in cov))]
        return [g for g in gaps if len(g) > 2 and not re.fullmatch(r'(kv|cr|ad|v|video|s)?\d+s?|\d+[a-z]?', g)]

    def fix_number(self, aname, ad_name):
        # creative id in the ad name wins over a stale id in the old token (ad1 -> ad2, ad1 -> video1, cutdowns3 -> cutdowns2)
        n = re.sub(r'(?<=[a-z])(kv|cr)(?=\d)', r' \1', str(ad_name or '').lower())
        ids_name = {(w, d) for w, d in re.findall(r'(?<![a-z])(ad|cr|kv|video)[\s_-]*(\d+)(?![\ds])', n)}
        ids_tok = list(re.finditer(r'(?<![a-z])(ad|cr|kv|video)(\d+)(?!\d)', aname))
        if len(ids_name) == 1 and len(ids_tok) == 1:
            (w, d), = ids_name; m = ids_tok[0]
            if (w, d) != (m.group(1), m.group(2)):
                return aname[:m.start()] + w + d + aname[m.end():], f'creative id {w}{d} taken from the ad name (old token said {m.group(0)})'
        for w in ('ad', 'cr', 'kv', 'video', 'cutdowns', 'cutdown'):
            nums = set(re.findall(r'(?<![a-z])' + w + r'[\s_-]*(\d+)(?![\ds])', n))
            m = re.search(w + r'(\d+)(?!\d)', aname)
            if m and len(nums) == 1:
                good = nums.pop()
                if good != m.group(1):
                    return aname[:m.start(1)] + good + aname[m.end(1):], f'creative number {w}{good} taken from the ad name (old token said {w}{m.group(1)})'
        return aname, None

    def num_conflict(self, aname, ad_name):
        """v5: the old token's creative number (video1, kv2, cr3, ad1, 45s) must not contradict the ad's own name (Video6s, KV3...)."""
        n = re.sub(r'[^a-z0-9]+', ' ', re.sub(r'(?<=[a-z])(kv|cr)(?=\d)', r' \1', str(ad_name or '').lower()))
        n = re.sub(r'(\d+)\s*(sec|secs|second|seconds)\b', r'\1s', n)
        name_ids = {x for x in re.findall(r'(?<![a-z])(video|kv|cr|ad)(\s?)(\d+)(s?)(?![0-9a-z])', n) if not (x[1] and x[3])}   # 'video 10s' = duration
        name_ids = {(w, d, s_) for w, _sp, d, s_ in name_ids}
        for w, d, s in set(re.findall(r'(?<![a-z])(video|kv|cr|ad)-?(\d+)(s?)(?![0-9])', aname)):
            same = {(d2, s2) for w2, d2, s2 in name_ids if w2 == w}
            if same and (d, s) not in same:
                return f'old token says {w}{d}{s}, the ad name says ' + '/'.join(sorted(w + a + b for a, b in same))
        # durations (10s vs 45s)
        nd = set(re.findall(r'(?<![0-9])(\d{1,3})\s?(?:s|sec|secs|second|seconds)(?![a-z])', n))
        td = set(re.findall(r'(?<![0-9])(\d{1,3})s(?![a-z0-9])', aname))
        if nd and td and not (td & nd): return f'old token says {"/".join(sorted(x + "s" for x in td))}, the ad name says {"/".join(sorted(x + "s" for x in nd))}'
        return None

    def lang_from(self, name):
        n = str(name or '')
        if re.search(r'arabic', n, re.I) and not re.search(r'english', n, re.I): return 'ar'
        if re.search(r'english', n, re.I) and not re.search(r'arabic', n, re.I): return 'en'
        if re.search(r'(^|[_\s-])(ENAR|EN-AR|EN/AR|AR/EN|EN\+AR)([_\s-]|$)', n, re.I): return 'en-ar'
        if re.search(r'(^|[_\s-])EN([_\s-]|$)', n, re.I): return 'en'
        if re.search(r'(^|[_\s-])AR([_\s-]|$)', n, re.I): return 'ar'
        return None

    def fmt_from(self, *names):
        n = ' '.join(str(x or '') for x in names)
        if re.search(r'static', n, re.I) and not re.search(r'video|reel|film', n, re.I): return 'display'
        if re.search(r'video|reel|cutdown|film|\d+s\b|_\d+s_', n, re.I): return 'video'
        if re.search(r'(^|[_\s-])(kv\d*|static|image|carousel|cr\d*|display|banner)([_\s-]|$)|(?<=[a-z])kv\d', n, re.I): return 'display'
        if re.search(r'rsa|search', n, re.I): return 'search'
        return None

    def rebuild(self, s, month=None):
        """Return (expected_url|None, missing[list], basis[list])."""
        url = repair_query(s['url']); p = s['platform']
        parts = urlsplit(url.strip()); q = parse_qsl(parts.query, keep_blank_values=True)
        cur = {}
        for k, v in q: cur.setdefault(k.lower(), v)     # v6: first occurrence wins
        missing, basis = [], []
        self._cur_s = s; self._tok_lang = None
        placeholder_camp = bool(re.fullmatch(r'\s*(dnu|do not use)\b.*|reach & frequency', str(s.get('campaign_name') or ''), re.I))
        # source / medium
        src = cur.get('utm_source', '').lower()
        m = re.search(r'_(Meta|X|TikTok|Snapchat|LinkedIn|GoogleSearch|Google)(?:_|$)', str(s.get('campaign_name')), re.I)
        if m and CHANNEL[m.group(1).lower()] in PLATFORM_SOURCES.get(p, set()) and CHANNEL[m.group(1).lower()] != src:
            # v5: the campaign name's own channel wins (as the generator derives it), e.g. instagram on a _Meta_ campaign -> meta
            basis.append(f'utm_source "{CHANNEL[m.group(1).lower()]}" from campaign-name channel "{m.group(1)}" (old URL said "{src}")')
            src = CHANNEL[m.group(1).lower()]
        elif src not in self.N.sources or src not in PLATFORM_SOURCES.get(p, {src}):
            if m: src = CHANNEL[m.group(1).lower()]; basis.append(f'utm_source from campaign-name channel "{m.group(1)}"')
            else: missing.append('source')
        med = cur.get('utm_medium', '').lower()
        gm = collections.Counter(r['medium'] for r in self.D.input_rows if r['source'] == src and r['medium'])
        if gm:
            top = gm.most_common(1)[0][0]
            if med != top: basis.append(f'utm_medium {top}: the generator\'s medium for {src} ({gm[top]} of {sum(gm.values())} rows)' + (f'; old URL said {med}' if med else ''))
            med = top
        else:
            missing.append(f'medium (the generator has no row for source {src})'); med = None
        # campaign
        ck = self.camp_codes.get((p, s.get('account_id'), s.get('campaign_id')))
        if ck and len(ck) == 1:
            (cuid, cname), = ck.keys(); basis.append(f'campaign code {cuid.upper()} {cname}: already used by other ads in this live campaign')
        else:
            cuid = None
            raw = re.sub(r'\{[^}]*\}', '', CODE_PREFIX.sub('', cur.get('utm_campaign', '').lower()))
            ln, l_asset = layout_name(raw)
            if ln:
                basis.append(f'campaign name "{ln}" = the Campaign Name field of the old generator-layout token (agency / unit / asset / type fields are not part of it)'); raw = ln
                # the layout token names its asset: it belongs to this live campaign when the asset matches (not by the name's words)
                if placeholder_camp or self.belongs(re.sub(r'\d+$', '', l_asset), s.get('campaign_name'), s.get('adset_name'), s.get('ad_name')): placeholder_camp = True
            MON = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)(uary|ruary|ch|il|e|y|ust|tember|ober|ember)?'
            toks = [t for t in re.split(r'[-_/]+', raw) if t and not re.fullmatch(r'(19|20)\d\d|' + MON + r'|' + MON + r'(19|20)?\d\d|(19|20)\d\d' + MON, t)]
            toks = [t for t in toks if t not in ('brand', 'generic', 'competitors', 'competitor', 'competitive')]
            cname = self.clean(slug('-'.join(toks)))
            if cname in self.N.camp: cuid = self.N.camp[cname]
            else:
                # user 11-Oct: 'if the campaign generator sheet has it do it, if it doesn't drop it'
                norm = lambda x: re.sub(r'[^a-z0-9]', '', x.lower())
                lead = re.match(r'([A-Za-z]+)', str(s.get('campaign_name') or ''))
                keys = {norm(cname)} | ({norm(lead.group(1))} if lead else set())
                cy = re.findall(r'(20\d\d)', str(s.get('campaign_name') or ''))
                def yr_ok(g):
                    gy = re.findall(r'(20\d\d)', g)
                    return not gy or (cy and cy[0] == gy[0])
                hits = {g for g in self.N.camp if yr_ok(g) and any(k and (norm(g) == k or re.fullmatch(re.escape(k) + r'(19|20)\d\d', norm(g))) for k in keys)}
                if len(hits) == 1:
                    g = hits.pop(); cuid, cname = self.N.camp[g], g
                    basis.append(f'campaign "{g}" ({cuid.upper()}) exists in Campaign_Code_Generator for this legacy campaign (user rule: use it if the generator has it)')
            if not cname: missing.append('campaign name')
            elif not cuid and not placeholder_camp and not self.belongs(cname, s.get('campaign_name'), s.get('adset_name'), s.get('ad_name')):
                missing.append('campaign name (old token belongs to another campaign)')
        obj, ow = objective_of(s.get('campaign_name'))
        if ow and not re.match(r'objective from campaign-name token', ow): basis.append(ow)
        if not obj:
            fc = re.search(r'(?:^|[_\s-])(uf|mf|lf)(?:[_\s-]|$)', str(s.get('campaign_name') or '').lower())
            ft = re.search(r'(?:^|[_-])(uf|mf|lf)(?:[_-]|$)', cur.get('utm_campaign', '').lower())
            obj, ow = (None, None) if (fc and ft and fc.group(1) != ft.group(1)) else objective_of(re.sub(r'[-_]+', '_', cur.get('utm_campaign', '')))
            if obj: basis.append(f'objective {obj} from the ad\'s own old utm_campaign (the live campaign name gives none)')
        if not obj: missing.append('objective')
        if not month: missing.append('first-serving month')
        # term
        sk = self.set_codes.get((p, s.get('account_id'), s.get('adset_id')))
        tlang = None
        pa, _ = self.D.parse_adset(s.get('adset_name'))
        if pa:
            tuid, tname, tlang = pa['gen_uid'], pa['aname'], pa['lang']; basis.append('utm_term from the generator-format ad set name')
        elif sk and len(sk) == 1:
            (tuid, tname), = sk.keys(); basis.append(f'ad set code {tuid.upper()} {tname}: already used by other ads in this live ad set')
        else:
            tuid = None
            t = re.sub(r'\{[^}]*\}', '', CODE_PREFIX.sub('', cur.get('utm_term', '').lower()))
            mt = (re.match(r'(.+?)[-_](en-ar|ar|en|all)[-_](?:all|mob|desk|android|ios)(?:[-_]|$)', t)
                  or re.match(r'(.+?)_(en-ar|ar|en|all)(?:_|$)', t) or re.match(r'(.+?)-(en-ar|ar|en)$', t))
            tname = self.clean(slug(mt.group(1)) if mt else slug(t))
            if mt and not PLACEHOLDER.search(t): self._tok_lang = mt.group(2)      # v6: used only when the ad set name, campaign and landing page give none
            gl = gen_from_live(s.get('adset_name'), self.N.adset)
            if gl and gl != tname: tname = gl; basis.append(f'ad set name {gl} = Campaign_Code_Generator {self.N.adset[gl].upper()}, exactly in the live ad set name')
            if tname in self.N.adset: tuid = self.N.adset[tname]
            if not tname: missing.append('ad set name')
            elif not tuid and not placeholder_camp and not self.belongs(tname, s.get('campaign_name'), s.get('adset_name'), s.get('ad_name')):
                missing.append('ad set name (old token belongs to another ad set)')
        nl = self.lang_from(s.get('adset_name'))
        ads_l = self.set_ad_langs.get((p, s.get('account_id'), s.get('adset_id')), set())
        if nl in ('en', 'ar') and len(ads_l) == 1 and None not in ads_l and nl not in ads_l and not pa:
            al, = ads_l
            basis.append(f'ad set language {al}: the ad set name says {nl.upper()} but every ad in this live ad set is {al.upper()} (ad names / landing pages)')
            nl = al
        if nl and not pa:
            if tlang and tlang != nl: basis.append(f'ad set language {nl} from the ad set name (old token said {tlang})')
            tlang = nl
        # content
        pd, _ = self.D.parse_ad(s.get('ad_name'))
        lp = re.search(r'/(en|ar)(/|$)', parts.path.lower())
        if pd and not pd.get('kv_only'):
            aname, afmt, alang, auid = pd['adname'], pd['fmt'], pd['lang'], pd['gen_uid']
            basis.append('utm_content from the generator-format ad name')
            return self._finish(q, parts, src, med, cuid, cname, month, obj, tuid, tname, tlang, auid, aname, afmt, alang, missing, basis, lp)
        mz = re.search(r'manazel[\s_-]*al[\s_-]*hadawi[\s_-]*(?:static[\s_-]*)?kv[\s_-]*(\d+)', str(s.get('ad_name') or ''), re.I)
        if mz and f'manazel-alhadawi-kv{mz.group(1)}' in self.N.ad:
            g = f'manazel-alhadawi-kv{mz.group(1)}'
            basis.append(f'ad name part {g} = Campaign_Code_Generator {self.N.ad[g].upper()} (Manazel: the generator has it, so it is used)')
            fmt_m = 'video' if 'video_data' in str(s.get('slot')) else 'display'
            return self._finish(q, parts, src, med, cuid, cname, month, obj, tuid, tname, tlang, self.N.ad[g], g, fmt_m, self.lang_from(s.get('ad_name')), missing, basis,
                                re.search(r'/(en|ar)(/|$)', parts.path.lower()))
        c0 = re.sub(r'\{[^}]*\}', '', CODE_PREFIX.sub('', cur.get('utm_content', '').lower()))
        c0 = re.split(r'\+|\s+\d', c0)[0]
        c = c0
        # legacy H&S tokens are {creative}-{format}-{aud|ret}-{country}: what follows the format word is targeting / geography, not the creative name
        lm = re.match(r'(.+?)-(?:video|image|carousel|static|gif|display|banner)(-.*)?$', c)
        if lm and '_' not in c:
            # v5: a creative-variant tail (option2, v2, set1) after the format word is part of the creative, targeting / country is not
            var = re.findall(r'(?<=-)(option\d+|v\d+|set\d+|version\d+|var\d+)(?=-|$)', lm.group(2) or '')
            c = lm.group(1) + ''.join('-' + v for v in var)
            basis.append(f'ad name = creative part of the old token "{c0}" (text after the format word is targeting / country'
                         + (f'; variant {"-".join(var)} kept' if var else '') + ')')
        # v5: schema-shaped parse - every name segment before the format / language word is the name (zallal_restaurants_search ->
        # zallal-restaurants); targeting / test / placeholder segments are not part of it; anything after format / language is a tail
        FMTS = ('display', 'video', 'search', 'audio', 'banner', 'partner-listing'); LNGS = ('en-ar', 'ar', 'en', 'all')
        name_segs, tfmt, tlng, after = [], None, None, False
        is_ph = bool(PLACEHOLDER.search(c0) or re.search(r'(^|_)test(_|$)', c0))
        for sg in [x for x in c.split('_') if x]:
            if sg in FMTS: tfmt = tfmt or (None if is_ph else sg); after = True; continue
            if sg in LNGS: tlng = tlng or (None if is_ph else sg); after = True; continue
            if after: continue
            if re.fullmatch(r'test|\d*(fe)?male|ad|adset|adgroup|name|na|none|null', sg) or sg in self.vocab: continue
            name_segs.append(sg)
        name_segs = [re.sub(r'^((?:kv|cr|video|ad)\d+)(ar|en)$', r'\1', x) for x in name_segs]
        aname = self.clean(slug('-'.join(name_segs))) if name_segs else ''
        # a targeting-strategy word glued to the creative name (retargetingvideo7s) is not part of the name
        aname = re.sub(r'^(retargeting|remarketing|prospecting)(?=[a-z0-9])', '', aname)
        if aname:
            aname, why = self.fix_number(aname, s.get('ad_name'))
            if why: basis.append(why)
        vtag = None
        if aname:
            # v5: the ad name's single version tag (..._CR2_V2) is added (after the checks below) when the old token has none
            vn = set(re.findall(r'(?:^|[_\s-])(v\d+|option\s?\d+)(?=[_\s-]|$)', str(s.get('ad_name') or '').lower()))
            if len(vn) == 1 and int(re.search(r'\d+', next(iter(vn))).group(0)) >= 2 and not re.search(r'(?:^|-)(v\d+|option\d+)(?=-|$)', aname):
                vtag = re.sub(r'\s', '', vn.pop())
        slot_fmt = 'video' if 'video_data' in str(s.get('slot')) else ('display' if p == 'meta' and 'link_data' in str(s.get('slot')) else None)
        nt = str(s.get('notes') or '')
        type_fmt = ('video' if re.search(r'ad_format[=\s]+SINGLE_VIDEO|card_type=VIDEO_|creative_type=VIDEO|ad_type=VIDEO', nt) else
                    'display' if re.search(r'card_type=IMAGE_|ad_format[=\s]+(SINGLE_IMAGE|CAROUSEL)', nt) else None)
        # v6: the ad / creative name decide before any old-token format; the old token's own words only when the ad names give nothing
        afmt = slot_fmt or type_fmt or self.fmt_from(s.get('ad_name')) or self.fmt_from(s.get('creative_name')) or tfmt or (None if is_ph else self.fmt_from(c0))
        if type_fmt and tfmt and type_fmt != tfmt: basis.append(f'format {type_fmt} from the creative type (old token said {tfmt})')
        if slot_fmt and tfmt and tfmt != slot_fmt: basis.append(f'format video: the URL sits in the video slot (old token said {tfmt})')
        ml = re.search(r'(?:^|[-_])(en|ar)(?:[-_]|$)', c0) if not is_ph else None
        alang = self.lang_from(s.get('ad_name')) or tlng or (ml.group(1) if ml else None)
        auid = self.N.ad.get(aname)
        ga = gen_from_live(s.get('ad_name'), self.N.ad)
        if ga and ga != aname:
            basis.append(f'ad name part {ga} = Campaign_Code_Generator {self.N.ad[ga].upper()}, exactly in the live ad name'); aname, auid = ga, self.N.ad[ga]
        id_only = re.fullmatch(r'(kv|cr|ad|video)(\d+)', aname or '')
        if aname and not auid and re.fullmatch(r'\d+s?|\d+-\d+s?|v\d+', aname):
            missing.append('ad name (old token is only a duration / number, not a creative name)')
        elif aname and not auid and id_only and not re.search(rf'(?<![a-z]){id_only.group(1)}[\s_-]?{id_only.group(2)}(?![0-9])', re.sub(r'(?<=[a-z])(kv|cr)(?=\d)', r' \1', str(s.get('ad_name') or '').lower())):
            missing.append('ad name (old token is only a creative number that this ad name does not carry)')
        elif aname and not auid and s.get('ad_name') and self.num_conflict(aname, s.get('ad_name')):
            missing.append('ad name (old token names another cut: ' + self.num_conflict(aname, s.get('ad_name')) + ')')
        elif aname and not auid and s.get('ad_name') and (not self.belongs(aname, s.get('ad_name')) or self.unmatched(aname, s)):
            # v5: keep the old token when it contains the ad's own creative label (launchbuilding on '..._Building', coeadoptation on '..._COE')
            lab = slug(re.split(r'[_|]', str(s.get('ad_name')).strip())[-1]).replace('-', '')
            if len(lab) >= 3 and not re.fullmatch(r'(en|ar|enar|na|\d+)', lab) and lab in aname.replace('-', ''):
                basis.append(f'ad name "{aname}": the old token contains this ad\'s own creative label "{lab}"')
            else:
                missing.append('ad name (old token does not match this ad)')
        if any(m.startswith('ad name (old token') for m in missing) and not (slot_fmt or type_fmt or self.fmt_from(s.get('ad_name')) or self.fmt_from(s.get('creative_name'))):
            afmt = None      # the rejected token names another creative: its format word is no evidence either
        if vtag and aname and not auid and not any(m.startswith('ad name') for m in missing):
            aname = f'{aname}-{vtag}'; basis.append(f'version "{vtag}" taken from the ad name (the old token has none)')
        return self._finish(q, parts, src, med, cuid, cname, month, obj, tuid, tname, tlang, auid, aname, afmt, alang, missing, basis, lp)

    def _finish(self, q, parts, src, med, cuid, cname, month, obj, tuid, tname, tlang, auid, aname, afmt, alang, missing, basis, lp):
        s_ = getattr(self, '_cur_s', None) or {}
        al_set = self.lang_from(s_.get('adset_name'))
        if not alang and al_set in ('en', 'ar') and s_.get('platform') != 'google':
            alang = al_set; basis.append(f'ad language {al_set} from the ad set name (the ad name has none)')
        cl = self.lang_from(s_.get('campaign_name'))
        if cl in ('en', 'ar'):     # v6: the campaign's own EN / AR token comes before the landing page
            if not tlang: tlang = cl; basis.append(f'ad set language {cl} from the campaign name')
            if not alang and (s_.get('platform') == 'google' or not s_.get('ad_name')): alang = tlang if tlang in ('en', 'ar') else cl; basis.append(f'ad language {alang} from the ad group / campaign language')
        if not tlang and lp: tlang = lp.group(1); basis.append(f'ad set language from landing page /{tlang}/ (names have none)')
        if not tlang and getattr(self, '_tok_lang', None): tlang = self._tok_lang; basis.append(f'ad set language {tlang} from the old utm_term (no name / page gives one)')
        if not tlang and lp: tlang = lp.group(1); basis.append(f'ad set language from landing page /{tlang}/ (name has none)')
        if not alang and lp: alang = lp.group(1); basis.append(f'ad language from landing page /{alang}/ (name has none)')
        if not tlang: missing.append('ad set language')
        if not aname: missing.append('ad name')
        if not afmt: missing.append('ad format')
        if not alang: missing.append('ad language')
        if missing: return None, missing, basis
        pre = lambda u: f'{u}_' if u else ''
        exp = [('utm_source', src), ('utm_medium', med),
               ('utm_campaign', f'{pre(cuid)}{cname}_{month}_{obj}'),
               ('utm_term', f'{pre(tuid)}{tname}_{tlang}'),
               ('utm_content', f'{pre(auid)}{aname}_{afmt}_{alang}')]
        keep = [(k, v) for k, v in q if not k.lower().startswith('utm_') and k.lower() not in CLICK_IDS]
        query = '&'.join(f'{k}={quote(v, safe="-_.~{}/:")}' for k, v in keep + exp)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment)), [], basis
