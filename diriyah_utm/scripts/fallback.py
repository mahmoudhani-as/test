"""Optional 'live-name fallback' (NOT yet approved by the user): where the old UTM has no usable token,
take the missing part from the live entity names / facts instead of flagging the slot.
  - campaign / ad set / ad name: the live campaign / ad set (ad group) / ad name, with every token that belongs to
    another generator field removed (Mappings lists, years, months, dates, BO numbers, platform names, legacy codes)
  - Google search ads have no ad name: the ad group name is used
  - objective: sub-objective word in the campaign name, mapped as the generator rows do (reach->awr, traffic->cond, leads/sales->conv)
  - format: from the ad type (responsive search ad -> search) or the creative type words
  - month for ads that never served: the month the ad was created"""
import re, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from legacy import Legacy, slug, CODE_PREFIX, PLACEHOLDER
from derive import PLATFORM_SOURCES

MONTHS = 'jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december'
NOISE = {'meta', 'x', 'tiktok', 'snapchat', 'snap', 'sc', 'google', 'googlesearch', 'search', 'linkedin', 'instagram', 'facebook', 'fb', 'ig', 'twitter',
         'tactical', 'tac', 'ao', 'alwayson', 'campaign', 'up', 'uf', 'mf', 'lf', 'awr', 'trf', 'conv', 'lead', 'leads', 'cond', 'awareness', 'consideration',
         'conversion', 'conversions', 'traffic', 'reach', 'sales', 'engagement', 'views', 'videoviews', 'prospecting', 'prospect', 'retargeting', 'remarketing',
         'aud', 'ret', 'en', 'ar', 'enar', 'en-ar', 'na', 'cpc', 'cpm', 'cpv', 'cpl', 'cpa', 'paidsocial', 'paid', 'social', 'sa', 'copy', 'boosted', 'dark',
         'ksa', 'gcc', 'uae', 'kwt', 'qat', 'omn', 'bah', 'uk', 'fra', 'kuwait', 'qatar', 'oman', 'bahrain', 'feed', 'stories', 'story', 'reels'}
SUBOBJ = [('traffic-leads', 'conv'), ('leads', 'conv'), ('lead', 'conv'), ('sales', 'conv'), ('traffic', 'cond'), ('engagement', 'cond'),
          ('reach', 'awr'), ('video views', 'awr'), ('videoviews', 'awr')]
CHANNEL_SRC = {'meta': 'meta', 'google': 'google', 'tiktok': 'tiktok', 'snapchat': 'snapchat', 'x': 'x', 'linkedin': 'linkedin'}

class Fallback(Legacy):
    def __init__(self, deriver, scored, deriver_path, created=None):
        super().__init__(deriver, scored, deriver_path)
        self.created = created or {}

    def live_name(self, name, drop_extra=()):
        n = str(name or '').lower()
        if not n or n == 'none': return ''
        n = re.sub(r'\[copy\]|\bcopy\b', ' ', n)
        n = re.sub(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}', ' ', n)
        n = re.sub(r'\b20\d{6}(-20\d{6})?\b', ' ', n)
        n = re.sub(r'\bbo#?\s?\d+\b', ' ', n)
        n = re.sub(r'\b\d+x\d+\b', ' ', n)
        toks = [t for t in re.split(r'[^a-z0-9]+', n) if t]
        keep = []
        for t in toks:
            if t in self.vocab or t in NOISE or t in drop_extra: continue
            if re.fullmatch(r'(19|20)\d\d|(' + MONTHS + r')(19|20)?\d{0,2}|(19|20)\d\d(' + MONTHS + r')', t): continue
            if keep and keep[-1] == t: continue
            keep.append(t)
        out = '-'.join(keep)
        return '' if PLACEHOLDER.search(out) else out

    def ad_label(self, name):
        # legacy taxonomy names (Brand_Type_Campaign_Funnel_Country_Strategy_Lang_Objective_Platform_Creative): the creative is the last real segment
        segs = [x for x in re.split(r'_', str(name or '')) if x.strip()]
        if len(segs) >= 5:
            for seg in reversed(segs):
                lab = self.live_name(seg)
                if lab: return lab
            return ''
        return self.live_name(name)

    def adset_label(self, s):
        camp = re.sub(r'[^a-z0-9]', '', str(s.get('campaign_name') or '').lower())
        full = self.live_name(s.get('adset_name'))
        own = [t for t in full.split('-') if t and t not in camp]
        return '-'.join(own) or full

    def rebuild_fb(self, s, month=None):
        e, missing, basis = self.rebuild(s, month=month or 'x')
        if e and month: return self.rebuild(s, month=month)[0], [], basis, False
        # re-run with live-name fallbacks filled in
        url = s['url'] or ''; p = s['platform']
        from urllib.parse import urlsplit, urlunsplit, parse_qsl, quote
        from derive import CLICK_IDS
        parts = urlsplit(url.strip()); q = parse_qsl(parts.query, keep_blank_values=True)
        cur = {k.lower(): v for k, v in q}
        fb = []
        # parse the URL the same way the base rebuild does by asking it for each piece through a synthetic record
        base = self._pieces(s, month)
        src, med, cuid, cname, obj, tuid, tname, tlang, auid, aname, afmt, alang = [base.get(k) for k in
            ('src', 'med', 'cuid', 'cname', 'obj', 'tuid', 'tname', 'tlang', 'auid', 'aname', 'afmt', 'alang')]
        if not src: src = CHANNEL_SRC.get(p); fb.append(f'utm_source = platform {p}')
        if not med:
            med = 'paid-search' if p == 'google' else 'paid-social'; fb.append(f'utm_medium = {med} (generator rows for {src})')
        if not cname:
            cname = self.live_name(s.get('campaign_name')); fb.append(f'campaign name from live campaign name "{s.get("campaign_name")}"')
        if not obj:
            cn = re.sub(r'[_\-]+', ' ', str(s.get('campaign_name') or '')).lower()
            for w, o in SUBOBJ:
                if re.search(r'\b' + w + r'\b', cn): obj = o; fb.append(f'objective {o} from sub-objective "{w}" in the campaign name (generator rows: {w} -> {o})'); break
        if not tname:
            tname = self.adset_label(s); fb.append(f'ad set name from live ad set "{s.get("adset_name")}" (words already in the campaign name removed)')
        if not aname:
            has_ad = s.get('ad_name') not in (None, 'None', '')
            aname = self.ad_label(s.get('ad_name')) if has_ad else self.adset_label(s)
            fb.append(f'ad name from live {"ad" if has_ad else "ad group (search ads have no ad name)"} "{s.get("ad_name") if has_ad else s.get("adset_name")}"')
        if not afmt:
            notes = str(s.get('notes') or '') + ' ' + str(s.get('ad_name') or '') + ' ' + str(s.get('creative_name') or '')
            if re.search(r'RESPONSIVE_SEARCH|EXPANDED_TEXT|channel=SEARCH', notes): afmt = 'search'
            elif re.search(r'video|reel|\b\d+s\b', notes, re.I): afmt = 'video'
            elif re.search(r'image|static|carousel|\bkv\d*|display|banner|IMAGE', notes, re.I): afmt = 'display'
            if afmt: fb.append(f'format {afmt} from the ad type / creative')
        lp = re.search(r'/(en|ar)(/|$)', parts.path.lower())
        if not tlang: tlang = self.lang_from(s.get('adset_name')) or (lp.group(1) if lp else None)
        if not alang: alang = self.lang_from(s.get('ad_name')) or tlang or (lp.group(1) if lp else None)
        if not month:
            c = self.created.get((p, str(s.get('ad_id'))))
            if c: month = c; fb.append(f'month {c} = month the ad was created (it never served)')
        miss = [k for k, v in (('source', src), ('medium', med), ('campaign name', cname), ('objective', obj), ('ad set name', tname),
                               ('ad set language', tlang), ('ad name', aname), ('ad format', afmt), ('ad language', alang), ('month', month)) if not v]
        if miss: return None, miss, basis + fb, True
        pre = lambda u: f'{u}_' if u else ''
        exp = [('utm_source', src), ('utm_medium', med), ('utm_campaign', f'{pre(cuid)}{cname}_{month}_{obj}'),
               ('utm_term', f'{pre(tuid)}{tname}_{tlang}'), ('utm_content', f'{pre(auid)}{aname}_{afmt}_{alang}')]
        keep = [(k, v) for k, v in q if not k.lower().startswith('utm_') and k.lower() not in CLICK_IDS]
        query = '&'.join(f'{k}={quote(v, safe="-_.~{}/:")}' for k, v in keep + exp)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment)), [], basis + fb, True

    def _pieces(self, s, month):
        """Run the base rebuild with month and capture every piece it resolved (None where it found nothing)."""
        got = {}
        orig = self._finish
        def cap(q, parts, src, med, cuid, cname, month_, obj, tuid, tname, tlang, auid, aname, afmt, alang, missing, basis, lp):
            got.update(src=src if 'source' not in missing else None, med=med if 'medium' not in missing else None, cuid=cuid,
                       cname=cname if not any(m.startswith('campaign name') for m in missing) else None,
                       obj=obj, tuid=tuid, tname=tname if not any(m.startswith('ad set name') for m in missing) else None,
                       tlang=tlang, auid=auid, aname=aname if not any(m.startswith('ad name') for m in missing) else None, afmt=afmt, alang=alang)
            return orig(q, parts, src, med, cuid, cname, month_, obj, tuid, tname, tlang, auid, aname, afmt, alang, missing, basis, lp)
        self._finish = cap
        try:
            if s.get('url'): self.rebuild(s, month=month or 'x')
        finally:
            self._finish = orig
        return got
