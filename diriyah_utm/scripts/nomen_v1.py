"""Nomenclature rules loaded strictly from the Diriyah Campaign Nomenclature Generator."""
import re, openpyxl
from urllib.parse import urlsplit, parse_qsl

MONTHS = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
SOCIAL = {'meta','fb-ig','instagram','snapchat','tiktok','twitter','x','linkedin'}

class Nomen:
    def __init__(self, path):
        wb = openpyxl.load_workbook(path, data_only=True)
        m = wb['Mappings']
        col = lambda c: [str(v).strip() for v in (x.value for x in m[c][1:]) if v not in (None, '')]
        self.sources = {s.lower() for s in col('A')}
        self.mediums = {s.lower() for s in col('B')}
        self.objectives = {s.lower() for s in col('J')}
        self.langs = {s.lower() for s in col('M')}
        self.formats = {s.lower() for s in col('T')}
        g = wb['Campaign_Code_Generator']
        self.camp, self.adset, self.ad = {}, {}, {}
        for r in g.iter_rows(min_row=2, values_only=True):
            for d, n, u in ((self.camp, r[0], r[1]), (self.adset, r[3], r[4]), (self.ad, r[6], r[7])):
                if n and u: d[str(n).strip().lower()] = str(u).strip().lower()
        self.uid2camp = {v: k for k, v in self.camp.items()}
        self.uid2adset = {v: k for k, v in self.adset.items()}
        self.uid2ad = {v: k for k, v in self.ad.items()}
        # explicit generator rows: input + output URL
        ws, wo = wb['Input_Campaign_Generator'], wb['Output_Campaign_Generator']
        self.rows = []
        for r in range(3, ws.max_row + 1):
            url = wo.cell(r, 1).value
            if url and 'utm_' in str(url):
                v = [ws.cell(r, c).value for c in range(1, 26)]
                self.rows.append({'row': r, 'lp': v[0], 'source': v[1], 'medium': v[2], 'url': str(url)})

    def check(self, url):
        """Return list of (code, message) violations for a URL."""
        errs = []
        if not url or 'utm_' not in url:
            return [('NO_UTM', 'URL carries no UTM parameters')]
        parts = urlsplit(url.strip())
        params = parse_qsl(parts.query, keep_blank_values=True)
        q = {}
        for k, v in params:
            q.setdefault(k, v)
        if re.search(r'x{4,}', url, re.I):
            errs.append(('PLACEHOLDER', 'XXXX placeholder left in URL'))
        for k in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'):
            if k not in q or q[k] == '':
                errs.append(('MISSING_' + k.upper(), f'{k} missing'))
        if 'utm_id' in q:
            errs.append(('UTM_ID_PRESENT', 'utm_id present (agreed rule: no utm_id)'))
        extra = [k for k, _ in params if k.startswith('utm_') and k not in
                 ('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'utm_id')]
        extra += [k for k, _ in params if k in ('fbclid', 'gclid', 'ttclid', 'sccid', 'twclid')]
        if extra:
            errs.append(('EXTRA_PARAM', 'non-nomenclature parameter(s): ' + ', '.join(sorted(set(extra)))))
        for k in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'):
            v = q.get(k, '')
            if v != v.lower():
                errs.append(('UPPERCASE', f'{k} has uppercase (generator lower-cases every value)'))
            if ' ' in v:
                errs.append(('SPACE', f'{k} has spaces'))
            if re.search(r'(^|_)(ad-id|adset-id|cam-id)-', v, re.I):
                errs.append(('LEGACY_PREFIX', f'{k} uses legacy "ad-id-/adset-id-" code, not a generator uid'))
        src, med = q.get('utm_source', '').lower(), q.get('utm_medium', '').lower()
        if src and src not in self.sources:
            errs.append(('BAD_SOURCE', f'utm_source "{src}" not in Mappings source list'))
        if med and med not in self.mediums:
            errs.append(('BAD_MEDIUM', f'utm_medium "{med}" not in Mappings medium list'))
        social = src in SOCIAL
        # utm_campaign = uid_name_monYY_objective
        c = q.get('utm_campaign', '').lower()
        if c:
            mm = re.fullmatch(r'([0-9a-f]{8})_(.+?)_(' + '|'.join(MONTHS) + r')(\d{2})(?:_(.+))?', c)
            if not mm:
                errs.append(('CAMPAIGN_FORMAT', f'utm_campaign "{q["utm_campaign"]}" is not uid_name_monYY_objective (legacy / free text)'))
            else:
                uid, name, _, _, obj = mm.groups()
                if obj is None:
                    errs.append(('CAMPAIGN_NO_OBJECTIVE', 'utm_campaign missing the Campaign Objective (awr/cond/conv) per Schema'))
                elif obj not in self.objectives:
                    errs.append(('CAMPAIGN_BAD_OBJECTIVE', f'utm_campaign objective "{obj}" not in awr/cond/conv'))
                if name not in self.camp:
                    errs.append(('CAMPAIGN_NAME_NOT_IN_GEN', f'campaign name "{name}" not in Campaign_Code_Generator'))
                elif self.camp[name] != uid:
                    errs.append(('CAMPAIGN_UID_MISMATCH', f'campaign uid {uid} != generator {self.camp[name]} for "{name}"'))
        t = q.get('utm_term', '').lower()
        if t:
            mm = re.fullmatch(r'([0-9a-f]{8})_(.+)_(' + '|'.join(sorted(self.langs, key=len, reverse=True)) + r')', t)
            if not mm:
                errs.append(('TERM_FORMAT', f'utm_term "{q["utm_term"]}" is not uid_adset_language'))
            else:
                uid, name, _ = mm.groups()
                if name not in self.adset:
                    errs.append(('TERM_NAME_NOT_IN_GEN', f'adset name "{name}" not in Campaign_Code_Generator'))
                elif self.adset[name] != uid:
                    errs.append(('TERM_UID_MISMATCH', f'adset uid {uid} != generator {self.adset[name]} for "{name}"'))
        co = q.get('utm_content', '').lower()
        if co:
            mm = re.fullmatch(r'([0-9a-f]{8})_(.+)_(' + '|'.join(self.formats) + r')_(' +
                              '|'.join(sorted(self.langs, key=len, reverse=True)) + r')', co)
            if not mm:
                errs.append(('CONTENT_FORMAT', f'utm_content "{q["utm_content"]}" is not uid_ad_format_language'))
                adname, fmt = co, ''
            else:
                uid, adname, fmt, _ = mm.groups()
                if adname not in self.ad:
                    errs.append(('CONTENT_NAME_NOT_IN_GEN', f'ad name "{adname}" not in Campaign_Code_Generator'))
                elif self.ad[adname] != uid:
                    errs.append(('CONTENT_UID_MISMATCH', f'ad uid {uid} != generator {self.ad[adname]} for "{adname}"'))
            if social and (fmt == 'search' or re.search(r'(^|[-_])(search|rsa)([-_]|$)', adname)):
                errs.append(('SEARCH_ON_SOCIAL', 'search creative/format used on a social platform'))
            if (social or med == 'paid-search' or src == 'google') and re.search(r'kv[a-d]\b|kv[a-d]_|kv[a-d]$', adname):
                errs.append(('KV_LETTER_OFF_PROGRAMMATIC', 'kva/kvb/kvd creative is programmatic-only, used on social/search'))
        # landing page language vs content language (informational)
        path = parts.path.lower()
        lp_lang = 'en' if '/en' in path else ('ar' if '/ar' in path else None)
        ml = re.search(r'_(en|ar)$', co)
        if lp_lang and ml and ml.group(1) != lp_lang:
            errs.append(('LP_LANG_MISMATCH', f'landing page /{lp_lang}/ but utm_content language _{ml.group(1)}'))
        return errs
