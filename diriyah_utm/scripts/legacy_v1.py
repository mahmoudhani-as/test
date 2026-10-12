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
        vocab |= {'conversions', 'awareness', 'consideration', 'conversion'}
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

    def clean(self, name):
        name = CODE_PREFIX.sub('', name)
        if PLACEHOLDER.search(name): return ''          # template / macro leftovers are not names
        toks = [t for t in re.split(r'[-_/]+', name) if t]
        kept = [t for t in toks if t not in self.vocab]
        return '-'.join(kept)                           # nothing left = no real name

    def lang_from(self, name):
        n = str(name or '')
        if re.search(r'arabic', n, re.I) and not re.search(r'english', n, re.I): return 'ar'
        if re.search(r'english', n, re.I) and not re.search(r'arabic', n, re.I): return 'en'
        if re.search(r'(^|[_\s-])(ENAR|EN-AR)([_\s-]|$)', n, re.I): return 'en-ar'
        if re.search(r'(^|[_\s-])EN([_\s-]|$)', n, re.I): return 'en'
        if re.search(r'(^|[_\s-])AR([_\s-]|$)', n, re.I): return 'ar'
        return None

    def fmt_from(self, *names):
        n = ' '.join(str(x or '') for x in names)
        if re.search(r'video|reel|\d+s\b|_\d+s_', n, re.I): return 'video'
        if re.search(r'(^|[_\s-])(kv\d*|static|image|carousel|cr\d*|display|banner)([_\s-]|$)', n, re.I): return 'display'
        if re.search(r'rsa|search', n, re.I): return 'search'
        return None

    def rebuild(self, s, month=None):
        """Return (expected_url|None, missing[list], basis[list])."""
        url = s['url']; p = s['platform']
        parts = urlsplit(url.strip()); q = parse_qsl(parts.query, keep_blank_values=True)
        cur = {k.lower(): v for k, v in q}
        missing, basis = [], []
        # source / medium
        src = cur.get('utm_source', '').lower()
        if src not in self.N.sources or src not in PLATFORM_SOURCES.get(p, {src}):
            m = re.search(r'_(Meta|X|TikTok|Snapchat|LinkedIn|GoogleSearch|Google)(?:_|$)', str(s.get('campaign_name')), re.I)
            if m: src = CHANNEL[m.group(1).lower()]; basis.append(f'utm_source from campaign-name channel "{m.group(1)}"')
            else: missing.append('source')
        med = cur.get('utm_medium', '').lower()
        if med not in self.N.mediums:
            meds = {r['medium'] for r in self.D.input_rows if r['source'] == src and r['medium']}
            if len(meds) == 1: med = meds.pop(); basis.append(f'utm_medium = every generator row for {src}')
            else: missing.append('medium')
        # campaign
        ck = self.camp_codes.get((p, s.get('account_id'), s.get('campaign_id')))
        if ck and len(ck) == 1:
            (cuid, cname), = ck.keys(); basis.append(f'campaign code {cuid.upper()} {cname}: already used by other ads in this live campaign')
        else:
            cuid = None
            raw = CODE_PREFIX.sub('', cur.get('utm_campaign', ''))
            raw = re.sub(r'[_-]?(19|20)\d\d', '', raw, flags=re.I)
            raw = re.sub(r'[_-]?(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*', '', raw, flags=re.I)
            cname = self.clean(slug(raw))
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
        om = re.search(r'_(UF|MF|LF)_([A-Z]+)_', str(s.get('campaign_name')))
        obj = OBJ.get(om.group(2)) if om else None
        if not obj:
            wm = re.search(r'(awareness|consideration|conversion)', str(s.get('campaign_name')), re.I)
            if wm:
                obj = {'awareness': 'awr', 'consideration': 'cond', 'conversion': 'conv'}[wm.group(1).lower()]
                basis.append(f'objective from campaign-name word "{wm.group(1)}" (Mappings col K definition)')
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
            t = CODE_PREFIX.sub('', cur.get('utm_term', '').lower())
            mt = (re.match(r'(.+?)[-_](en-ar|ar|en|all)[-_](?:all|mob|desk|android|ios)(?:[-_]|$)', t)
                  or re.match(r'(.+?)_(en-ar|ar|en|all)(?:_|$)', t) or re.match(r'(.+?)-(en-ar|ar|en)$', t))
            tname = self.clean(slug(mt.group(1)) if mt else slug(t))
            if mt: tlang = mt.group(2)
            if tname in self.N.adset: tuid = self.N.adset[tname]
            if not tname: missing.append('ad set name')
        tlang = tlang or self.lang_from(s.get('adset_name'))
        # content
        pd, _ = self.D.parse_ad(s.get('ad_name'))
        lp = re.search(r'/(en|ar)(/|$)', parts.path.lower())
        if pd and not pd.get('kv_only'):
            aname, afmt, alang, auid = pd['adname'], pd['fmt'], pd['lang'], pd['gen_uid']
            basis.append('utm_content from the generator-format ad name')
            return self._finish(q, parts, src, med, cuid, cname, month, obj, tuid, tname, tlang, auid, aname, afmt, alang, missing, basis, lp)
        c = CODE_PREFIX.sub('', cur.get('utm_content', '').lower())
        mc = re.match(r'(.+?)(?:_(display|video|search|audio|banner|partner-listing))?(?:_(en-ar|ar|en|all))?(?:_.*)?$', c)
        aname = self.clean(slug(mc.group(1))) if mc and mc.group(1) else ''
        afmt = (mc.group(2) if mc else None) or self.fmt_from(s.get('ad_name'), c)
        ml = re.search(r'(?:^|[-_])(en|ar)(?:[-_]|$)', c)
        alang = (mc.group(3) if mc else None) or self.lang_from(s.get('ad_name')) or (ml.group(1) if ml else None)
        auid = self.N.ad.get(aname)
        return self._finish(q, parts, src, med, cuid, cname, month, obj, tuid, tname, tlang, auid, aname, afmt, alang, missing, basis, lp)

    def _finish(self, q, parts, src, med, cuid, cname, month, obj, tuid, tname, tlang, auid, aname, afmt, alang, missing, basis, lp):
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
