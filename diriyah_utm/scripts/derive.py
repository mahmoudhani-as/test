"""Derive the nomenclature-correct URL for a live ad strictly from the generator workbook.

Every token is sourced from (a) the generator-format entity names (which are themselves
generator outputs) mapped through Campaign_Code_Generator, (b) explicit Input/Output rows,
or (c) a decision the user gave in this session. Anything else -> BLOCKED with the reason.
"""
import re, os, sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nomen import Nomen, MONTHS, SOCIAL

PLATFORM_SOURCES = {
    'meta': {'meta', 'fb-ig', 'instagram'}, 'snapchat': {'snapchat'}, 'tiktok': {'tiktok'},
    'x': {'x', 'twitter'}, 'linkedin': {'linkedin'}, 'google': {'google', 'gadg', 'youtube', 'gadv360'},
}
CLICK_IDS = {'fbclid', 'gclid', 'ttclid', 'sccid', 'twclid', 'li_fat_id', 'utm_id'}
# User decisions in this session (11 Oct 2026)
USER_DECISIONS = {
    'no_utm_id': 'User: do not add utm_id (remove where present).',
    'objective': 'User: add the Campaign Objective to utm_campaign, per Schema.',
    'kva': 'User: kva/kvb/kvd creatives are programmatic-only; flag social/search use until a social/search code exists in Campaign_Code_Generator.',
    'ritz_search': 'User: Google search ads for Ritz use the Campaign_Code_Generator search code rcsr-search (78F964BB).',
}
# Google search creative per campaign name: only where the generator / user names one explicitly
GOOGLE_SEARCH_CREATIVE = {
    'ritz-carlton-signature': ('rcsr-search', 'ritz_search'),
    'thechediresidences': ('thechedi-rsa', 'Input_Campaign_Generator rows 162-163'),
}
KV_LETTER = re.compile(r'(^|-)kv[a-d]($|-)')


class Deriver:
    def __init__(self, gen_path, first_serving=None):
        self.N = Nomen(gen_path)
        self.first_serving = first_serving or {}
        import openpyxl
        wb = openpyxl.load_workbook(gen_path, data_only=True)
        m = wb['Mappings']
        col = lambda c: {str(x.value).strip().lower() for x in m[c][1:] if x.value not in (None, '')}
        self.bus, self.assets, self.types = col('D'), col('E'), col('Q')
        self.funnels, self.devices, self.genders, self.strategies = col('H'), col('N'), col('O'), col('S')
        self.out_rows = []
        for r in self.N.rows:
            qq = {k.lower(): v.lower() for k, v in parse_qsl(urlsplit(r['url']).query, keep_blank_values=True)}
            self.out_rows.append({'row': r['row'], 'q': qq})
        ws = wb['Input_Campaign_Generator']
        self.input_rows = []
        for r in range(3, ws.max_row + 1):
            v = [ws.cell(r, c).value for c in range(1, 26)]
            if v[1] and v[7]:
                self.input_rows.append({'row': r, 'source': str(v[1]).strip().lower(),
                                        'medium': (str(v[2]).strip().lower() if v[2] else None),
                                        'campaign': str(v[7]).strip().lower()})

    # ---------- name parsers (generator formats from Output_Campaign_Generator B/C/D) ----------
    def parse_campaign(self, name):
        if not name: return None, 'no campaign name'
        n = name.strip().lower()
        m = re.fullmatch(r'(?P<src>[^_]+)_(?P<bu>[^_]+)_(?P<asset>[^_]+)_(?P<type>[^_]+)_(?P<year>\d{4})_(?P<mon>[a-z]+)_'
                         r'(?P<cname>[^_]+)_cam-id-(?P<uid>[0-9a-f]{8})_(?P<funnel>uf|mf|lf|mf/lf)_(?P<obj>[a-z]+)(?:_(?P<rest>.*))?', n)
        if not m: return None, f'campaign name "{name}" is not in generator format'
        d = m.groupdict(); probs = []
        if d['src'] not in self.N.sources: probs.append(f'source "{d["src"]}" not in Mappings')
        if d['bu'] not in self.bus: probs.append(f'business unit "{d["bu"]}" not in Mappings')
        if d['mon'] not in MONTHS: probs.append(f'month "{d["mon"]}" not in Mappings')
        if d['obj'] not in self.N.objectives: probs.append(f'objective "{d["obj"]}" not in Mappings')
        if d['cname'] not in self.N.camp: probs.append(f'campaign "{d["cname"]}" not in Campaign_Code_Generator')
        if probs: return None, 'campaign name: ' + '; '.join(probs)
        d['gen_uid'] = self.N.camp[d['cname']]
        d['uid_ok'] = d['uid'] == d['gen_uid']
        return d, None

    def parse_adset(self, name):
        if not name: return None, 'no ad set name'
        n = name.strip().lower()
        m = re.fullmatch(r'(?P<bu>[^_]+)_(?P<asset>[^_]+)_(?P<year>\d{4})_(?P<mon>[a-z]+)_(?P<aname>[^_]+)_adset-id-(?P<uid>[0-9a-f]{8})_'
                         r'(?P<lang>en-ar|ar|en|all)_(?P<device>[^_]+)_(?P<gender>[^_]+)_(?P<strategy>[^_]+)(?:_(?P<rest>.*))?', n)
        if not m: return None, f'ad set name "{name}" is not in generator format'
        d = m.groupdict()
        if d['aname'] not in self.N.adset:
            return None, f'ad set "{d["aname"]}" not in Campaign_Code_Generator'
        d['gen_uid'] = self.N.adset[d['aname']]; d['uid_ok'] = d['uid'] == d['gen_uid']
        return d, None

    def parse_ad(self, name):
        if not name: return None, 'no ad name'
        n = name.strip().lower()
        fm = '|'.join(sorted(self.N.formats, key=len, reverse=True))
        m = re.fullmatch(r'(?P<bu>[^_]+)_(?P<asset>[^_]+)_(?P<year>\d{4})_(?P<mon>[a-z]+)_(?P<adname>[^_]+)_(?:adset|ad)-id-(?P<uid>[0-9a-f]{8})_'
                         rf'(?P<fmt>{fm})_(?P<lang>en-ar|ar|en|all)(?:_(?P<rest>.*))?', n)
        if not m:
            m2 = re.search(r'_(?P<adname>[^_]+)_(?:adset|ad)-id-', n)
            if m2 and KV_LETTER.search(m2.group('adname')):
                return {'adname': m2.group('adname'), 'kv_only': True}, None
            return None, f'ad name "{name}" is not in generator format'
        d = m.groupdict()
        if d['adname'] not in self.N.ad:
            return None, f'ad "{d["adname"]}" not in Campaign_Code_Generator'
        d['gen_uid'] = self.N.ad[d['adname']]; d['uid_ok'] = d['uid'] == d['gen_uid']
        return d, None

    # ---------- medium ----------
    def medium_for(self, source, cname, current):
        rows = [r for r in self.input_rows if r['source'] == source and r['campaign'] == cname and r['medium']]
        meds = {r['medium'] for r in rows}
        if len(meds) == 1:
            return meds.pop(), f'Input_Campaign_Generator rows {",".join(str(r["row"]) for r in rows)} ({source} / {cname})'
        if current and current in self.N.mediums:
            return current, 'current value kept (valid Mappings medium; no single generator row for this source+campaign)'
        allm = {r['medium'] for r in self.input_rows if r['source'] == source and r['medium']}
        if len(allm) == 1:
            return allm.pop(), f'every Input_Campaign_Generator row for source {source}'
        return None, f'medium "{current}" not in Mappings and generator rows for {source} disagree ({sorted(allm)})'

    # ---------- main ----------
    def derive(self, rec):
        """rec: live inventory row. Returns dict(status, expected_url, reasons, basis)."""
        url = rec.get('url')
        platform = (rec.get('platform') or '').lower()
        out = {'status': None, 'expected_url': None, 'reasons': [], 'basis': []}
        if not url:
            out['status'] = 'NO_URL'; out['reasons'].append(rec.get('notes') or 'no destination URL on this ad')
            return out
        parts = urlsplit(url.strip())
        q = parse_qsl(parts.query, keep_blank_values=True)
        cur = {k.lower(): v for k, v in q}
        if 'sitelink' in str(rec.get('slot') or '').lower():
            out['status'] = 'BLOCKED'; out['reasons'] = ['sitelink: Campaign_Code_Generator has no creative code for sitelinks (and one sitelink can serve several ad groups)']
            return out
        camp, ce = self.parse_campaign(rec.get('campaign_name'))
        adset, ae = self.parse_adset(rec.get('adset_name'))
        ad, de = (None, None)
        blocked = []
        if platform == 'google':
            # RSAs carry no ad name: creative comes only from an explicit generator / user mapping
            if camp:
                gs = GOOGLE_SEARCH_CREATIVE.get(camp['cname'])
                if gs:
                    adn, why = gs
                    ad = {'adname': adn, 'gen_uid': self.N.ad[adn], 'fmt': 'search', 'lang': None}
                    out['basis'].append(USER_DECISIONS.get(why, why))
                else:
                    blocked.append(f'no search creative code in Campaign_Code_Generator for Google campaign "{camp["cname"]}"')
            if rec.get('ad_name'):
                pa, pe = self.parse_ad(rec.get('ad_name'))
                if pa and not pa.get('kv_only'): ad = pa
        else:
            ad, de = self.parse_ad(rec.get('ad_name'))
        if ce: blocked.append(ce)
        if ae and platform != 'google': blocked.append(ae)
        if de: blocked.append(de)
        src_cur = cur.get('utm_source', '').lower()
        # kva rule (user) -- check the ad name and the current content token
        content_name = (ad or {}).get('adname') or ''
        cur_content = cur.get('utm_content', '').lower()
        if (platform in PLATFORM_SOURCES and platform != 'google' and (KV_LETTER.search(content_name) or KV_LETTER.search(cur_content.split('_')[1] if '_' in cur_content else ''))) \
           or (platform == 'google' and KV_LETTER.search(cur_content)):
            blocked.append('kva/kvb/kvd creative is programmatic-only (user decision); no social/search code for it in Campaign_Code_Generator')
        if ad and ad.get('kv_only'):
            ad = None
        if ad and platform in ('meta', 'snapchat', 'tiktok', 'x', 'linkedin') and (ad.get('fmt') == 'search' or re.search(r'(^|-)(search|rsa)($|-)', ad.get('adname', ''))):
            blocked.append('search creative/format on a social platform')
        if blocked:
            out['status'] = 'BLOCKED'; out['reasons'] = blocked
            return out
        # Google ad group language: RSA content language comes from the ad group (generator utm_term lang)
        if platform == 'google':
            if not adset:
                out['status'] = 'BLOCKED'; out['reasons'] = [ae or 'ad group not in generator format']; return out
            if ad.get('lang') is None:
                if adset['lang'] in ('en', 'ar'):
                    ad['lang'] = adset['lang']
                    out['basis'].append('Google RSA has no ad name: content language = ad group language token')
                else:
                    out['status'] = 'BLOCKED'; out['reasons'] = [f'ad group language "{adset["lang"]}" cannot give one content language']; return out
        source = camp['src']
        if platform in PLATFORM_SOURCES and source not in PLATFORM_SOURCES[platform]:
            out['status'] = 'BLOCKED'; out['reasons'] = [f'campaign name source "{source}" does not belong to platform {platform}']; return out
        medium, mbasis = self.medium_for(source, camp['cname'], cur.get('utm_medium', '').lower())
        if not medium:
            out['status'] = 'BLOCKED'; out['reasons'] = [mbasis]; return out
        yy = camp['year'][2:]
        mon = camp['mon']
        fs = self.first_serving.get(str(rec.get('ad_id')))
        if fs and rec.get('_use_serving_month'):
            mon, yy = MONTHS[int(fs[5:7]) - 1], fs[2:4]
            out['basis'].append(f'MonthYear from the date the ad started serving ({fs}, account timezone) - user decision 11-Oct')
        exp = [
            ('utm_source', source),
            ('utm_medium', medium),
            ('utm_campaign', f"{camp['gen_uid']}_{camp['cname']}_{mon}{yy}_{camp['obj']}"),
            ('utm_term', f"{adset['gen_uid']}_{adset['aname']}_{adset['lang']}"),
            ('utm_content', f"{ad['gen_uid']}_{ad['adname']}_{ad['fmt']}_{ad['lang']}"),
        ]
        expd = dict(exp)
        cand = [r for r in self.out_rows if r['q'].get('utm_source') == expd['utm_source'] and r['q'].get('utm_term') == expd['utm_term']
                and r['q'].get('utm_content') == expd['utm_content']
                and r['q'].get('utm_campaign', '').split('_')[:2] == expd['utm_campaign'].split('_')[:2]]
        if cand:
            obj = expd['utm_campaign'].rsplit('_', 1)[-1]
            same = [r for r in cand if r['q'].get('utm_campaign') == expd['utm_campaign']]
            month_conflict = [r for r in cand if r['q'].get('utm_campaign') != expd['utm_campaign']
                              and r['q'].get('utm_campaign', '').rsplit('_', 1)[-1] == obj]
            if same:
                meds = {r['q'].get('utm_medium') for r in same}
                out['basis'].append(f'Matches explicit generator Output row(s) {[r["row"] for r in same]}')
                if len(meds) == 1 and meds != {expd['utm_medium']}:
                    gmed = meds.pop()
                    out['basis'].append(f'utm_medium {gmed} taken from those rows')
                    exp = [(k, gmed if k == 'utm_medium' else v) for k, v in exp]; medium, mbasis = gmed, f'generator Output row(s) {[r["row"] for r in same]}'
            elif month_conflict:
                out['status'] = 'BLOCKED'
                out['reasons'] = [f'CONFLICT: live campaign name gives {expd["utm_campaign"]} but generator Output row(s) '
                                  f'{[r["row"] for r in month_conflict]} for this exact ad give {sorted({r["q"].get("utm_campaign") for r in month_conflict})} (month differs) - needs your decision']
                return out
            # rows with a different objective belong to another campaign of the same creative: ignored
        out['basis'] += [
            f'utm_source = campaign name channel "{source}"',
            f'utm_medium = {medium} ({mbasis})',
            f'utm_campaign = Campaign_Code_Generator {camp["cname"]}={camp["gen_uid"].upper()} + month/year {mon}{yy} + objective {camp["obj"]} (Schema row 8)',
            f'utm_term = Campaign_Code_Generator {adset["aname"]}={adset["gen_uid"].upper()} + ad set language {adset["lang"]} (Schema row 9)',
            f'utm_content = Campaign_Code_Generator {ad["adname"]}={ad["gen_uid"].upper()} + format {ad["fmt"]} + language {ad["lang"]} (Schema row 10)',
            USER_DECISIONS['no_utm_id'],
        ]
        if not camp['uid_ok']: out['basis'].append(f'NOTE campaign name carries cam-id-{camp["uid"]} but generator uid is {camp["gen_uid"]}')
        if not adset['uid_ok']: out['basis'].append(f'NOTE ad set name carries adset-id-{adset["uid"]} but generator uid is {adset["gen_uid"]}')
        if ad.get('uid') and not ad.get('uid_ok', True): out['basis'].append(f'NOTE ad name carries id {ad["uid"]} but generator uid is {ad["gen_uid"]}')
        keep = [(k, v) for k, v in q if not k.lower().startswith('utm_') and k.lower() not in CLICK_IDS]
        query = '&'.join(f'{k}={quote(v, safe="-_.~{}/:")}' for k, v in keep + exp)
        new = urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
        out['expected_url'] = new
        out['status'] = 'OK' if self._same(url, new) else 'FIX'
        return out

    @staticmethod
    def _same(a, b):
        pa, pb = urlsplit(a.strip()), urlsplit(b.strip())
        return (pa.scheme, pa.netloc.lower(), pa.path, pa.fragment) == (pb.scheme, pb.netloc.lower(), pb.path, pb.fragment) and \
            sorted(parse_qsl(pa.query, keep_blank_values=True)) == sorted(parse_qsl(pb.query, keep_blank_values=True))
