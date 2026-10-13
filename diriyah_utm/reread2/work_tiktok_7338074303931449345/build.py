import json, sys, collections
from urllib.parse import urlsplit, parse_qsl, quote
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread2/work_tiktok_7338074303931449345'
sys.path.insert(0, W)
import parse
BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
ACC = '7338074303931449345'
ACC_NAME = 'H&S - DGCL - Diriyah Gate'
inp = json.load(open(f'{BASE}/reread/in/tiktok_{ACC}.json', encoding='utf-8'))

# ---- load current state (merge batches; later reads only fill/confirm) ----
def req_utc(rid):
    # TikTok request_id prefix is YYYYMMDDHHMMSS in UTC+8
    import datetime
    t = datetime.datetime.strptime(rid[:14], '%Y%m%d%H%M%S') - datetime.timedelta(hours=8)
    return t.strftime('%Y-%m-%d %H:%M:%S')
manual, manual_src = {}, {}
for f in ['manual_p1.txt', 'manual_bA.txt', 'manual_bB.json']:
    j = parse.load(f'{W}/raw/{f}')
    rid = j['data']['data']['request_id']
    for it in j['data']['data']['data']['list']:
        a = it['ad_id']
        if a in manual:
            for k in set(it) & set(manual[a]):
                assert it[k] == manual[a][k], (a, k)
            manual[a].update(it)
        else:
            manual[a] = dict(it); manual_src[a] = (f, rid)
smart, smart_src = {}, {}
for f in ['smart_S1.json', 'smart_S2.json', 'smart_S3.json']:
    j = parse.load(f'{W}/raw/{f}')
    rid = j['data']['data']['request_id']
    for it in j['data']['data']['data']['list']:
        a = it['smart_plus_ad_id']
        if a in smart:
            assert it == smart[a], a
        else:
            smart[a] = it; smart_src[a] = (f, rid)
assert len(manual) == 106 and len(smart) == 97, (len(manual), len(smart))

SAFE = "-._~!$'()*,;:@/{}"
def utm_pairs(utm):
    out, seen = [], set()
    for p in utm or []:
        k, v = p.get('key'), p.get('value')
        if not k or k in seen:
            continue
        seen.add(k); out.append((k, '' if v is None else str(v)))
    return out

def render(url, utm):
    """Return (rendered_url, info) - append utm_params keys missing from the URL query (before any #fragment);
    keys already in the URL keep the URL's value."""
    info = {'added': [], 'conflicts': [], 'same': [], 'url_only': []}
    if not url:
        return None, info
    pairs = utm_pairs(utm)
    if not pairs:
        return url, info
    parts = urlsplit(url)
    q = parse_qsl(parts.query, keep_blank_values=True)
    qd = {}
    for k, v in q:
        qd.setdefault(k, v)
    for k, v in pairs:
        if k in qd:
            (info['same'] if qd[k] == v else info['conflicts']).append((k, qd[k], v))
        else:
            info['added'].append((k, v))
    pk = {k for k, _ in pairs}
    info['url_only'] = [k for k in qd if k.startswith('utm_') and k not in pk]
    if not info['added']:
        return url, info
    i = url.find('#')
    base, frag = (url, '') if i < 0 else (url[:i], url[i:])
    if parts.query:
        sep = '' if base.endswith('&') else '&'
    else:
        sep = '' if base.endswith('?') else '?'
    add = '&'.join(f"{quote(k, safe=SAFE)}={quote(v, safe=SAFE)}" for k, v in info['added'])
    return base + sep + add + frag, info

def qdiff(old, new):
    """Describe differences between two URLs at host/path/query/fragment level."""
    if old == new:
        return []
    if old is None or new is None:
        return [f"url {old!r} -> {new!r}"]
    o, n = urlsplit(old), urlsplit(new)
    out = []
    if (o.scheme, o.netloc, o.path) != (n.scheme, n.netloc, n.path):
        out.append(f"base {o.scheme}://{o.netloc}{o.path} -> {n.scheme}://{n.netloc}{n.path}")
    oq = collections.OrderedDict(parse_qsl(o.query, keep_blank_values=True))
    nq = collections.OrderedDict(parse_qsl(n.query, keep_blank_values=True))
    for k in list(oq) + [k for k in nq if k not in oq]:
        if oq.get(k) != nq.get(k):
            if k not in nq:
                out.append(f"{k} removed (was '{oq[k]}')")
            elif k not in oq:
                out.append(f"{k} added '{nq[k]}'")
            else:
                out.append(f"{k} '{oq[k]}' -> '{nq[k]}'")
    if o.fragment != n.fragment:
        out.append(f"fragment '#{o.fragment}' -> '#{n.fragment}'")
    if not out:
        out.append('query encoding/order differs')
    return out

def tags_str(utm):
    pairs = utm_pairs(utm)
    return '&'.join(f'{k}={v}' for k, v in pairs) if pairs else None

def utm_change(old_tags, new_utm):
    new_tags = tags_str(new_utm)
    if (old_tags or None) == (new_tags or None):
        return None
    od = collections.OrderedDict(parse_qsl(old_tags or '', keep_blank_values=True))
    nd = collections.OrderedDict(utm_pairs(new_utm))
    ch = []
    for k in list(od) + [k for k in nd if k not in od]:
        if od.get(k) != nd.get(k):
            if k not in nd: ch.append(f"{k} removed")
            elif k not in od: ch.append(f"{k}='{nd[k]}' added")
            else: ch.append(f"{k} '{od[k]}' -> '{nd[k]}'")
    if not od: return 'utm_params now set (were not set on 11-Oct): ' + (new_tags or '')
    if not nd: return 'utm_params now empty (were set on 11-Oct)'
    return 'utm_params changed since 11-Oct: ' + '; '.join(ch) if ch else 'utm_params order changed'

def info_text(info, field):
    parts = []
    if info['added']:
        parts.append(f"{field} keys not in landing_page_url appended to url: " + ', '.join(f'{k}={v}' for k, v in info['added']))
    for k, uv, pv in info['conflicts']:
        parts.append(f"CONFLICT {k}: landing_page_url has '{uv}' but {field} has '{pv}' (url keeps landing_page_url value)")
    if info['same'] and not info['added'] and not info['conflicts']:
        parts.append(f"{field} identical to query already in landing_page_url")
    elif info['same'] and (info['added'] or info['conflicts']):
        parts.append(f"other {field} keys identical to URL query")
    if info.get('url_only'):
        parts.append(f"landing_page_url has {', '.join(info['url_only'])} not present in {field}")
    return parts

out_rows = []
for r in inp:
    a, slot = r['ad_id'], r['slot']
    notes = []
    if slot == 'ad.landing_page_url':
        cur = manual.get(a)
        if cur is None:
            out_rows.append({'platform': 'tiktok', 'account_id': ACC, 'ad_id': a, 'slot': slot, 'url': None,
                             'status_now': 'NOT_FOUND', 'creative_id_now': None, 'found': False,
                             'note': 'Ad not returned by /v1.3/ad/get/ with primary_status STATUS_ALL (deleted/no longer exists).'})
            continue
        deleted = 'DELETE' in (cur.get('secondary_status') or '')
        lpu = cur.get('landing_page_url') or None
        url, info = render(lpu, cur.get('utm_params'))
        notes.append(f"Manual ad ({cur.get('ad_format')}); read via /v1.3/ad/get/ (filtering primary_status STATUS_ALL; request {manual_src[a][1]}, {req_utc(manual_src[a][1])} UTC)")
        if lpu is None:
            extra = []
            if cur.get('landing_page_urls'): extra.append(f"landing_page_urls={cur.get('landing_page_urls')}")
            if cur.get('deeplink'): extra.append(f"deeplink={cur.get('deeplink')}")
            if cur.get('page_id'): extra.append(f"page_id={cur.get('page_id')}")
            notes.append('landing_page_url still empty; no destination URL on this ad' + (' (' + ', '.join(extra) + ')' if extra else ' (landing_page_urls null, no deeplink/page_id)'))
        notes += info_text(info, 'utm_params')
        if not cur.get('utm_params') and lpu:
            notes.append('utm_params not set')
        ch = utm_change(r.get('url_tags_11oct'), cur.get('utm_params'))
        if ch: notes.append(ch)
    else:
        cur = smart.get(a)
        if cur is None:
            out_rows.append({'platform': 'tiktok', 'account_id': ACC, 'ad_id': a, 'slot': slot, 'url': None,
                             'status_now': 'NOT_FOUND', 'creative_id_now': None, 'found': False,
                             'note': 'Smart+ ad not returned by /v1.3/smart_plus/ad/get/ with primary_status STATUS_ALL (deleted/no longer exists).'})
            continue
        deleted = 'DELETE' in (cur.get('secondary_status') or '')
        lst = cur.get('landing_page_url_list') or []
        assert slot == 'smart_plus_ad.landing_page_url_list[0].landing_page_url'
        lpu = (lst[0].get('landing_page_url') if lst else None) or None
        utm = (cur.get('ad_configuration') or {}).get('utm_params')
        url, info = render(lpu, utm)
        notes.append(f"Upgraded Smart+ ad; read via /v1.3/smart_plus/ad/get/ (filtering primary_status STATUS_ALL, smart_plus_ad_ids; request {smart_src[a][1]}, {req_utc(smart_src[a][1])} UTC)")
        if len(lst) != 1:
            notes.append(f"landing_page_url_list has {len(lst)} entries: " + json.dumps(lst))
        if cur.get('deeplink_list'):
            notes.append('deeplink_list=' + json.dumps(cur['deeplink_list']))
        notes += info_text(info, 'ad_configuration.utm_params')
        if not utm and lpu:
            notes.append('ad_configuration.utm_params not set')
        ch = utm_change(r.get('url_tags_11oct'), utm)
        if ch: notes.append(ch)
    # comparison with 11-Oct
    d = qdiff(r.get('url_11oct'), url)
    if not d:
        notes.insert(1, 'URL unchanged since 11-Oct')
    else:
        notes.insert(1, 'URL changed since 11-Oct: ' + '; '.join(d))
    st = cur.get('secondary_status')
    if st != r.get('status_11oct'):
        notes.append(f"status 11-Oct {r.get('status_11oct')} -> now {st}")
    notes.append(f"operation_status {cur.get('operation_status')}, secondary_status {st}; last modified {cur.get('modify_time')} UTC")
    if a == '1871315166237921' or (r.get('url_11oct') != r.get('base_url_11oct')):
        pass
    notes.append('TikTok has no separate creative ID for this slot (creative_id_now null)')
    row = {'platform': 'tiktok', 'account_id': ACC, 'ad_id': a, 'slot': slot, 'url': url,
           'status_now': st, 'creative_id_now': None, 'found': not deleted,
           'note': '; '.join(notes) if not deleted else 'Ad now has secondary_status ' + st + ' (deleted); ' + '; '.join(notes)}
    out_rows.append(row)

out_path = f'{BASE}/reread2/out/tiktok_{ACC}.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for row in out_rows:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

# ---- Task 2: ads not in input (skip deleted) ----
in_ids = {r['ad_id'] for r in inp}
new_rows, skipped = [], []
for a, cur in manual.items():
    if a in in_ids:
        continue
    st = cur.get('secondary_status') or ''
    if 'DELETE' in st:
        skipped.append(('manual', a, st, cur.get('ad_name'))); continue
    url, info = render(cur.get('landing_page_url') or None, cur.get('utm_params'))
    new_rows.append({'platform': 'tiktok', 'account_id': ACC, 'account_name': ACC_NAME,
                     'campaign_name': cur.get('campaign_name'), 'adset_name': cur.get('adgroup_name'),
                     'ad_id': a, 'ad_name': cur.get('ad_name'), 'effective_status': st,
                     'slot': 'ad.landing_page_url', 'url': url})
for a, cur in smart.items():
    if a in in_ids:
        continue
    st = cur.get('secondary_status') or ''
    if 'DELETE' in st:
        skipped.append(('smart', a, st, cur.get('ad_name'))); continue
    lst = cur.get('landing_page_url_list') or []
    for i, e in enumerate(lst or [{}]):
        url, info = render(e.get('landing_page_url') or None, (cur.get('ad_configuration') or {}).get('utm_params'))
        new_rows.append({'platform': 'tiktok', 'account_id': ACC, 'account_name': ACC_NAME,
                         'campaign_name': cur.get('campaign_name'), 'adset_name': cur.get('adgroup_name'),
                         'ad_id': a, 'ad_name': cur.get('ad_name'), 'effective_status': st,
                         'slot': f'smart_plus_ad.landing_page_url_list[{i}].landing_page_url', 'url': url})
new_rows.sort(key=lambda x: (x['campaign_name'] or '', x['adset_name'] or '', x['ad_name'] or '', x['ad_id']))
new_path = f'{BASE}/reread2/out/new_tiktok_{ACC}.jsonl'
with open(new_path, 'w', encoding='utf-8') as f:
    for row in new_rows:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

# snapshot for audit
json.dump({'manual': manual, 'smart_plus': smart, 'manual_src': manual_src, 'smart_src': smart_src, 'skipped_deleted_not_in_input': skipped},
          open(f'{W}/snapshot_current.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote', len(out_rows), 'rows ->', out_path)
print('wrote', len(new_rows), 'new-ad rows ->', new_path)
print('skipped deleted not-in-input:', len(skipped))
