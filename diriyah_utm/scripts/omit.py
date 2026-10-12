"""User rule 12-Oct: "for unknown figures like ad tokens write the utm without them".
Where a part of the generator schema cannot be sourced (no generator code / no usable name / never served / kva on social or search),
the part is LEFT OUT instead of being invented or the URL being flagged:
  utm_campaign = [uid_][campaign name_][monYY_][objective]
  utm_term     = [uid_][ad set name_][ad set language]
  utm_content  = [uid_][ad name_][format_][ad language]
A parameter with no known part at all is left out. Source and medium are always known (platform / generator rows)."""
import re, sys, os, json, collections
from urllib.parse import urlsplit, urlunsplit, parse_qsl, quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from derive import PLATFORM_SOURCES, CLICK_IDS, KV_LETTER, MONTHS
from fallback import Fallback
from legacy import objective_of, repair_query

CHANNEL_SRC = {'meta': 'meta', 'google': 'google', 'tiktok': 'tiktok', 'snapchat': 'snapchat', 'x': 'x', 'linkedin': 'linkedin'}
# objective from funnel + sub-objective words in a legacy campaign name: only combinations the generator's own
# Input_Campaign_Generator rows use for >= 90% of their rows (and at least 2 rows)
COMBO_OBJ = {('uf', 'reach'): 'awr', ('mf', 'reach'): 'awr', ('lf', 'reach'): 'awr', ('lf', 'leads'): 'conv', ('lf', 'sales'): 'conv',
             ('mf', 'traffic'): 'cond', ('lf', 'traffic'): 'cond'}
SUB = {'reach': 'reach', 'awareness': 'reach', 'leads': 'leads', 'lead': 'leads', 'sales': 'sales', 'conversion': 'sales', 'conversions': 'sales',
       'traffic': 'traffic'}

def generator_combos(gen_path):
    import openpyxl
    ws = openpyxl.load_workbook(gen_path, data_only=True)['Input_Campaign_Generator']
    H = [ws.cell(1, c).value for c in range(1, 26)]
    c = collections.defaultdict(collections.Counter)
    for r in range(3, ws.max_row + 1):
        d = dict(zip(H, [ws.cell(r, k).value for k in range(1, 26)]))
        if d.get('Campaign Funnel') and d.get('Campaign Objective') and d.get('Campaign Sub-Objective'):
            c[(d['Campaign Funnel'], d['Campaign Sub-Objective'])][d['Campaign Objective']] += 1
    out = {}
    for k, v in c.items():
        (o, n), = v.most_common(1); tot = sum(v.values())
        if tot >= 2 and n / tot >= 0.9: out[k] = o
    return out

class Omit:
    def __init__(self, deriver, scored, gen_path):
        self.D = deriver; self.N = deriver.N
        self.L = Fallback(deriver, scored, gen_path)
        self.combos = generator_combos(gen_path)

    # ---------- helpers ----------
    def objective(self, campaign_name):
        # v5: the same rule as the legacy rebuild (legacy.objective_of) for ads and sitelinks alike
        return objective_of(campaign_name)

    def compose(self, url, src, med, camp, term, content):
        parts = urlsplit(repair_query(url).strip()); q = parse_qsl(parts.query, keep_blank_values=True)
        j = lambda xs: '_'.join(x for x in xs if x)
        exp = [('utm_source', src), ('utm_medium', med), ('utm_campaign', j(camp)), ('utm_term', j(term)), ('utm_content', j(content))]
        exp = [(k, v) for k, v in exp if v]
        keep = [(k, v) for k, v in q if not k.lower().startswith('utm_') and k.lower() not in CLICK_IDS]
        query = '&'.join(f'{k}={quote(v, safe="-_.~{}/:")}' for k, v in keep + exp)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))

    # ---------- legacy ads (old names) ----------
    def legacy(self, s, month):
        """month: 'mmmYY' (first serving) or None (never served -> left out)."""
        p = s['platform']
        g = self.L._pieces(s, month or 'x')
        omitted, basis = [], []
        src = g.get('src') or CHANNEL_SRC.get(p)
        med = g.get('med')
        if not med:
            gm = collections.Counter(r['medium'] for r in self.D.input_rows if r['source'] == src and r['medium'])
            med = gm.most_common(1)[0][0] if gm else None      # v6: no generator row for the source (Demand Gen gadg) -> left out, not invented
            if med: basis.append(f'utm_medium {med} (the generator\'s medium for {src})')
        obj = g.get('obj')
        if not obj:
            obj, why = self.objective(s.get('campaign_name'))
            if why: basis.append(why)
        cname = g.get('cname'); cuid = g.get('cuid') if cname else None
        tname = g.get('tname'); tuid = g.get('tuid') if tname else None
        aname = g.get('aname'); auid = g.get('auid') if aname else None
        tlang, afmt, alang = g.get('tlang'), g.get('afmt'), g.get('alang')
        cl = self.L.lang_from(s.get('campaign_name'))
        if cl in ('en', 'ar'):     # v6: the campaign's own EN / AR token comes before the landing page
            if not tlang: tlang = cl; basis.append(f'ad set language {cl} from the campaign name')
            if not alang and (p == 'google' or not s.get('ad_name')): alang = tlang if tlang in ('en', 'ar') else cl; basis.append(f'ad language {alang} from the ad group / campaign language')
        lp = re.search(r'/(en|ar)(/|$)', urlsplit((s.get('url') or '').strip()).path.lower())
        if not tlang and lp: tlang = lp.group(1); basis.append(f'ad set language from landing page /{tlang}/')
        if not alang and lp: alang = lp.group(1); basis.append(f'ad language from landing page /{alang}/')
        if not afmt and p == 'google' and re.search(r'RESPONSIVE_SEARCH|channel=SEARCH|EXPANDED_TEXT', str(s.get('notes'))): afmt = 'search'
        for nm, v in (('medium (no generator row for this source)', med), ('campaign name', cname), ('month (ad never served)', month), ('objective', obj), ('ad set name', tname),
                      ('ad set language', tlang), ('ad name', aname), ('ad format', afmt), ('ad language', alang)):
            if not v: omitted.append(nm)
        url = self.compose(s['url'], src, med, [cuid, cname, month, obj], [tuid, tname, tlang], [auid, aname, afmt, alang])
        return url, omitted, basis

    # ---------- generator-format ads whose ad token is unknown (kva on social/search, Google search without a creative code) ----------
    def unknown_ad_token(self, s):
        p = s['platform']
        camp, ce = self.D.parse_campaign(s.get('campaign_name'))
        adset, ae = self.D.parse_adset(s.get('adset_name'))
        if not camp: return None, ['campaign not in generator format: ' + str(ce)], []
        cur = {}
        for k, v in parse_qsl(urlsplit(repair_query(s['url'])).query): cur.setdefault(k.lower(), v.lower())
        src = camp['src']
        if p in PLATFORM_SOURCES and src not in PLATFORM_SOURCES[p]: return None, [f'campaign source {src} not for {p}'], []
        med, mb = self.D.medium_for(src, camp['cname'], cur.get('utm_medium', ''))
        basis = ['ad token left out: ' + ('kva/kvb/kvd is programmatic-only' if p != 'google' or KV_LETTER.search(cur.get('utm_content', '')) else 'no search creative code in the generator')]
        # v5: month = first day the ad served (pulled), never the campaign-name month; never served -> left out
        k = f"{p}|{s.get('ad_id')}"
        fs = getattr(self, 'fs', {}).get(k)
        if fs: mon, yy = MONTHS[int(fs[5:7]) - 1], fs[2:4]; basis.append(f'MonthYear {mon}{yy} = first day the ad served ({fs})')
        else: mon, yy = None, ''
        month_missing = None if fs else ('month (ad never served)' if k in getattr(self, 'never', set()) else 'month (first-serving date not pulled)')
        term = [adset['gen_uid'], adset['aname'], adset['lang']] if adset else [None, None, None]
        omitted = []
        if not adset:
            # keep the live utm_term when it already is a valid generator pair + language (nothing invented)
            mt = re.fullmatch(r'([0-9a-f]{8})_([a-z0-9-]+)_(en-ar|ar|en|all)', cur.get('utm_term', ''))
            if mt and self.N.adset.get(mt.group(2)) == mt.group(1):
                term = [mt.group(1), mt.group(2), mt.group(3)]; basis.append('utm_term kept: already a valid generator ad set code + name + language')
            else:
                omitted.append('ad set (' + str(ae) + ')')
        # format + language of the ad: from the ad name tail, else the current content tail, else (Google) search + ad group language
        fm = '|'.join(sorted(self.N.formats, key=len, reverse=True))
        an = str(s.get('ad_name') or '').lower()
        m = re.search(rf'_({fm})_(en-ar|ar|en|all)(?:_|$)', an)
        if m: afmt, alang = m.group(1), m.group(2)
        else:
            # v5: generator-style ad names such as ..._adset-id-ef48098a_video_video1_en carry format and language too (ahead of the old token)
            m2f = re.search(rf'adset-id-[0-9a-z]+_({fm})(?:_|$)', an); m2l = re.search(r'_(en-ar|ar|en|all)$', an)
            mc = re.search(rf'_({fm})_(en-ar|ar|en|all)$', cur.get('utm_content', ''))
            afmt = (m2f.group(1) if m2f else None) or (mc.group(1) if mc else None) or ('search' if p == 'google' else None)
            alang = (m2l.group(1) if m2l else None) or (mc.group(2) if mc else None) or (adset['lang'] if adset and p == 'google' else None)
        if not afmt: omitted.append('ad format')
        if not alang: omitted.append('ad language')
        nt = str(s.get('notes') or '')
        tf = 'video' if re.search(r'ad_format[=\s]+SINGLE_VIDEO|card_type=VIDEO_', nt) else ('display' if re.search(r'card_type=IMAGE_|ad_format[=\s]+(SINGLE_IMAGE|CAROUSEL)', nt) else None)
        if tf and afmt != tf and 'video_data' not in str(s.get('slot')):
            basis.append(f'format {tf} from the creative type (old token said {afmt})'); afmt = tf
            if 'ad format' in omitted: omitted.remove('ad format')
        if 'video_data' in str(s.get('slot')) and afmt != 'video':
            basis.append(f'format video: the URL sits in the video slot (old token said {afmt})'); afmt = 'video'
            if 'ad format' in omitted: omitted.remove('ad format')
        if month_missing: omitted.append(month_missing)
        url = self.compose(s['url'], src, med, [camp['gen_uid'], camp['cname'], f'{mon}{yy}' if mon else None, camp['obj']], term, [None, None, afmt, alang])
        return url, ['ad token (uid + ad name)'] + omitted, basis

def check_omit(N, url):
    """Validate a URL built under the omit rule: every part that IS present must be valid; missing parts are allowed."""
    errs = []
    parts = urlsplit(url.strip()); params = parse_qsl(parts.query, keep_blank_values=True)
    q = {}
    for k, v in params: q.setdefault(k, v)
    # v5: only the UTM values are checked for macros / placeholders (non-UTM params such as Google ValueTrack {device} stay as they are)
    utm_vals = '&'.join(v for k, v in parse_qsl(urlsplit(url.strip()).query, keep_blank_values=True) if k.lower().startswith('utm_'))
    if re.search(r'x{4,}|\{[a-z_]+\}|(^|[_-])test([_-]|$)|adset_name|ad_name', utm_vals, re.I): errs.append('placeholder / macro left')
    if 'utm_id' in q: errs.append('utm_id present')
    extra = [k for k, _ in params if (k.startswith('utm_') and k not in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content')) or k in CLICK_IDS]
    if extra: errs.append('extra params ' + ','.join(extra))
    for k in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'):
        v = q.get(k)
        if v is None: continue
        if v != v.lower(): errs.append(f'{k} upper-case')
        if not re.fullmatch(r'[a-z0-9_-]+', v): errs.append(f'{k} has characters outside a-z0-9_-')
    if 'utm_source' in q and q['utm_source'] not in N.sources: errs.append('source not in Mappings')
    if 'utm_medium' in q and q['utm_medium'] not in N.mediums: errs.append('medium not in Mappings')
    def split(v, tails):
        toks = v.split('_'); got = {}
        for name, allowed in reversed(tails):
            if toks and allowed(toks[-1]): got[name] = toks.pop()
        if toks and re.fullmatch(r'[0-9a-f]{8}', toks[0]): got['uid'] = toks.pop(0)
        if toks: got['name'] = '_'.join(toks)
        return got
    mon = lambda t: re.fullmatch(r'(' + '|'.join(MONTHS) + r')\d\d', t) is not None
    for k, tails, lookup in (('utm_campaign', [('month', mon), ('objective', lambda t: t in N.objectives)], N.camp),
                             ('utm_term', [('lang', lambda t: t in N.langs)], N.adset),
                             ('utm_content', [('format', lambda t: t in N.formats), ('lang', lambda t: t in N.langs)], N.ad)):
        v = q.get(k)
        if not v: continue
        g = split(v, tails)
        if 'name' in g and '_' in g['name']: errs.append(f'{k}: unexpected "_" inside name "{g["name"]}"')
        if 'uid' in g and lookup.get(g.get('name', '')) != g['uid']: errs.append(f'{k}: uid {g["uid"]} does not belong to "{g.get("name")}" in Campaign_Code_Generator')
        if 'uid' not in g and g.get('name') in lookup: errs.append(f'{k}: generator has a code for "{g["name"]}" ({lookup[g["name"]]}) but it is missing')
        if k == 'utm_content' and g.get('name') and KV_LETTER.search(g['name']) and q.get('utm_medium') != 'programmatic': errs.append('kva token on social/search')
    return errs
