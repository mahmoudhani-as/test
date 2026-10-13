"""Build reread3 outputs for TikTok account 7338074303931449345 from the saved read-only API responses in ../raw.

TASK 1: one output line per input row (same order, ad_id and slot copied exactly).
TASK 2: ads not in the input (created after the 11-Oct pull), deleted/removed ones skipped.
"""
import collections
import datetime
import json
import os
import sys
from urllib.parse import parse_qsl, quote, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import load  # noqa: E402

W = os.path.dirname(HERE)
BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
ACC = '7338074303931449345'
ACC_NAME = 'H&S - DGCL - Diriyah Gate'
IN_FILE = f'{BASE}/reread/in/tiktok_{ACC}.json'
OUT_FILE = f'{BASE}/reread3/out/tiktok_{ACC}.jsonl'
NEW_FILE = f'{BASE}/reread3/out/new_tiktok_{ACC}.jsonl'
SLOT_MANUAL = 'ad.landing_page_url'
SLOT_SP0 = 'smart_plus_ad.landing_page_url_list[0].landing_page_url'
DELETED = {'AD_STATUS_DELETE', 'AD_STATUS_CAMPAIGN_DELETE', 'AD_STATUS_ADGROUP_DELETE'}

inp = json.load(open(IN_FILE, encoding='utf-8'))


def req_utc(rid):
    """TikTok request_id starts with YYYYMMDDHHMMSS in UTC+8."""
    t = datetime.datetime.strptime(rid[:14], '%Y%m%d%H%M%S') - datetime.timedelta(hours=8)
    return t.strftime('%Y-%m-%d %H:%M:%S')


# ---------------- load current state ----------------
manual, children, msrc = {}, {}, {}
for k in range(3):
    j = load.load(f'{W}/raw/manual_b{k}.json')
    d = j['data']['data']
    assert d['code'] == 0 and not j.get('meta', {}).get('mcp_output_budget'), (k, d.get('message'))
    lst = d['data']['list']
    assert all(isinstance(x, dict) for x in lst) and d['data']['page_info']['total_number'] == len(lst)
    for it in lst:
        a = it['ad_id']
        tgt = manual if it.get('campaign_automation_type') == 'MANUAL' else children
        assert a not in tgt
        tgt[a] = it
        msrc[a] = d['request_id']
smart, ssrc = {}, {}
for k in range(3):
    j = load.load(f'{W}/raw/smart_b{k}.json')
    d = j['data']['data']
    assert d['code'] == 0 and not j.get('meta', {}).get('mcp_output_budget'), (k, d.get('message'))
    lst = d['data']['list']
    assert all(isinstance(x, dict) for x in lst) and d['data']['page_info']['total_number'] == len(lst)
    for it in lst:
        a = it['smart_plus_ad_id']
        assert a not in smart
        smart[a] = it
        ssrc[a] = d['request_id']

inv = [l.rstrip('\n').split('\t') for l in open(f'{W}/raw/inventory_ad_get_STATUS_ALL.tsv', encoding='utf-8')
       if not l.startswith('#')]
spinv = [l.rstrip('\n').split('\t') for l in open(f'{W}/raw/inventory_smart_plus_ad_get_STATUS_ALL.tsv', encoding='utf-8')
         if not l.startswith('#')]
inv_manual = {r[0] for r in inv if r[1] == 'M'}
assert len(inv) == 265 and len(spinv) == 111
assert set(manual) == inv_manual, 'manual detail reads must cover the full STATUS_ALL inventory'
assert set(smart) == {r[0] for r in spinv}, 'Smart+ detail reads must cover the full STATUS_ALL listing'
assert {r[2] for r in inv if r[1] == 'C'} == set(smart), 'every Smart+ creative child maps to a listed Smart+ ad'

# ---------------- URL helpers ----------------
SAFE = "-._~!$'()*,;:@/{}"


def utm_pairs(utm):
    out, seen = [], set()
    for p in utm or []:
        k, v = p.get('key'), p.get('value')
        if not k or k in seen:
            continue
        seen.add(k)
        out.append((k, '' if v is None else str(v)))
    return out


def render(url, utm):
    """Append utm_params keys that are missing from the URL query (before any #fragment).
    Keys already in the URL keep the URL's value (TikTok's click-time behaviour as recorded on 11-Oct)."""
    info = {'added': [], 'conflicts': [], 'same': [], 'url_only': []}
    if not url:
        return None, info
    pairs = utm_pairs(utm)
    parts = urlsplit(url)
    qd = {}
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
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


def tags_str(utm):
    pairs = utm_pairs(utm)
    return '&'.join(f'{k}={v}' for k, v in pairs) if pairs else None


def qdiff(old, new):
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
        out.append('query parameter order/encoding differs')
    return out


def utm_change(old_tags, new_utm, field):
    new_tags = tags_str(new_utm)
    if (old_tags or None) == (new_tags or None):
        return None
    od = collections.OrderedDict(parse_qsl(old_tags or '', keep_blank_values=True))
    nd = collections.OrderedDict(utm_pairs(new_utm))
    if not od:
        return f'{field} now set (not set on 11-Oct): {new_tags}'
    if not nd:
        return f'{field} now empty (11-Oct: {old_tags})'
    ch = []
    for k in list(od) + [k for k in nd if k not in od]:
        if od.get(k) != nd.get(k):
            if k not in nd:
                ch.append(f"{k} removed")
            elif k not in od:
                ch.append(f"{k}='{nd[k]}' added")
            else:
                ch.append(f"{k} '{od[k]}' -> '{nd[k]}'")
    return f'{field} changed since 11-Oct: ' + '; '.join(ch) if ch else f'{field} key order changed since 11-Oct'


def info_text(info, field, has_utm):
    parts = []
    if not has_utm:
        parts.append(f'{field} not set')
        return parts
    if info['added']:
        parts.append(f"{field} keys not in landing_page_url appended to url: " +
                     ', '.join(f'{k}={v}' for k, v in info['added']))
    for k, uv, pv in info['conflicts']:
        parts.append(f"CONFLICT {k}: landing_page_url has '{uv}' but {field} has '{pv}' (url keeps landing_page_url value)")
    if info['same'] and not info['added'] and not info['conflicts']:
        parts.append(f"{field} identical to query already in landing_page_url")
    if info['url_only']:
        parts.append(f"landing_page_url has {', '.join(info['url_only'])} not present in {field}")
    return parts


# ---------------- TASK 1 ----------------
out_rows, selfcheck = [], collections.Counter()
for r in inp:
    a, slot = r['ad_id'], r['slot']
    notes = []
    if slot == SLOT_MANUAL:
        cur = manual.get(a)
        if cur is None:
            out_rows.append({'platform': 'tiktok', 'account_id': ACC, 'ad_id': a, 'slot': slot, 'url': None,
                             'status_now': 'NOT_FOUND', 'creative_id_now': None, 'found': False,
                             'note': 'Ad not returned by /v1.3/ad/get/ with primary_status STATUS_ALL (deleted / no longer exists).'})
            continue
        rid = msrc[a]
        raw = cur.get('landing_page_url') or None
        utm = cur.get('utm_params')
        url, info = render(raw, utm)
        notes.append(f"Manual ad ({cur.get('ad_format')}); read-only /v1.3/ad/get/ (filtering primary_status STATUS_ALL + ad_ids, "
                     f"request {rid}, {req_utc(rid)} UTC)")
        tag_field = 'utm_params'
        if raw is None:
            extra = [f'{k}={cur.get(k)!r}' for k in ('landing_page_urls', 'deeplink', 'page_id') if cur.get(k)]
            notes.append('landing_page_url still empty; no destination URL on this ad' +
                         (' (' + ', '.join(extra) + ')' if extra else ' (landing_page_urls null, deeplink empty, page_id null)'))
        else:
            notes += info_text(info, tag_field, bool(utm_pairs(utm)))
    else:
        assert slot == SLOT_SP0, slot
        cur = smart.get(a)
        if cur is None:
            out_rows.append({'platform': 'tiktok', 'account_id': ACC, 'ad_id': a, 'slot': slot, 'url': None,
                             'status_now': 'NOT_FOUND', 'creative_id_now': None, 'found': False,
                             'note': 'Smart+ ad not returned by /v1.3/smart_plus/ad/get/ with primary_status STATUS_ALL (deleted / no longer exists).'})
            continue
        rid = ssrc[a]
        lst = cur.get('landing_page_url_list') or []
        raw = (lst[0].get('landing_page_url') if lst else None) or None
        utm = (cur.get('ad_configuration') or {}).get('utm_params')
        url, info = render(raw, utm)
        notes.append(f"Upgraded Smart+ ad; read-only /v1.3/smart_plus/ad/get/ (filtering primary_status STATUS_ALL + smart_plus_ad_ids, "
                     f"request {rid}, {req_utc(rid)} UTC)")
        tag_field = 'ad_configuration.utm_params'
        if len(lst) != 1:
            notes.append(f'landing_page_url_list has {len(lst)} entries: ' + json.dumps(lst, ensure_ascii=False))
        if cur.get('deeplink_list'):
            notes.append('deeplink_list=' + json.dumps(cur['deeplink_list'], ensure_ascii=False))
        if raw is None:
            notes.append('landing_page_url_list[0] empty; no destination URL')
        else:
            notes += info_text(info, tag_field, bool(utm_pairs(utm)))
    # self-check of the rendering rule against the 11-Oct pull
    if raw == r.get('base_url_11oct') and (tags_str(utm) or None) == (r.get('url_tags_11oct') or None):
        selfcheck['same_inputs'] += 1
        selfcheck['render_matches_11oct' if url == r.get('url_11oct') else 'render_differs_11oct'] += 1
    d = qdiff(r.get('url_11oct'), url)
    notes.insert(1, 'URL unchanged since 11-Oct' if not d else 'URL changed since 11-Oct: ' + '; '.join(d))
    ch = utm_change(r.get('url_tags_11oct'), utm, tag_field)
    if ch:
        notes.append(ch)
    st = cur.get('secondary_status')
    if st != r.get('status_11oct'):
        notes.append(f"status 11-Oct {r.get('status_11oct')} -> now {st}")
    notes.append(f"operation_status {cur.get('operation_status')}, secondary_status {st}; last modified {cur.get('modify_time')} UTC")
    if slot == SLOT_MANUAL:
        notes.append('TikTok has no separate creative ID for a manual ad (creative_id_now null)')
    else:
        notes.append('Smart+ URL is owned by the Smart+ ad, no separate creative ID (creative_id_now null)')
    deleted = st in DELETED
    note = '; '.join(notes)
    if deleted:
        note = f'Ad now has secondary_status {st} (deleted); ' + note
    out_rows.append({'platform': 'tiktok', 'account_id': ACC, 'ad_id': a, 'slot': slot, 'url': url,
                     'status_now': st, 'creative_id_now': None, 'found': not deleted, 'note': note})

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    for row in out_rows:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

# ---------------- TASK 2 ----------------
in_ids = {r['ad_id'] for r in inp}
new_rows, skipped = [], []
for a, cur in manual.items():
    if a in in_ids:
        continue
    st = cur.get('secondary_status') or ''
    if st in DELETED:
        skipped.append(('manual', a, st, cur.get('ad_name'), cur.get('create_time')))
        continue
    url, _ = render(cur.get('landing_page_url') or None, cur.get('utm_params'))
    new_rows.append({'platform': 'tiktok', 'account_id': ACC, 'account_name': ACC_NAME,
                     'campaign_name': cur.get('campaign_name'), 'adset_name': cur.get('adgroup_name'),
                     'ad_id': a, 'ad_name': cur.get('ad_name'), 'effective_status': st,
                     'slot': SLOT_MANUAL, 'url': url})
for a, cur in smart.items():
    if a in in_ids:
        continue
    st = cur.get('secondary_status') or ''
    if st in DELETED:
        skipped.append(('smart_plus', a, st, cur.get('ad_name'), cur.get('create_time')))
        continue
    kids = [c for c in children.values() if c.get('smart_plus_ad_id') == a]
    assert kids, f'no creative child read for new Smart+ ad {a}'
    for c in kids:
        assert c['campaign_id'] == cur['campaign_id'] and c['adgroup_id'] == cur['adgroup_id'], a
    cname, gname = kids[0].get('campaign_name'), kids[0].get('adgroup_name')
    utm = (cur.get('ad_configuration') or {}).get('utm_params')
    for i, e in enumerate(cur.get('landing_page_url_list') or [{}]):
        url, _ = render(e.get('landing_page_url') or None, utm)
        new_rows.append({'platform': 'tiktok', 'account_id': ACC, 'account_name': ACC_NAME,
                         'campaign_name': cname, 'adset_name': gname,
                         'ad_id': a, 'ad_name': cur.get('ad_name'), 'effective_status': st,
                         'slot': f'smart_plus_ad.landing_page_url_list[{i}].landing_page_url', 'url': url})
new_rows.sort(key=lambda x: (x['campaign_name'] or '', x['adset_name'] or '', x['ad_name'] or '', x['ad_id']))
with open(NEW_FILE, 'w', encoding='utf-8') as f:
    for row in new_rows:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

json.dump({'manual': manual, 'smart_plus_creative_children_read': children, 'smart_plus': smart,
           'manual_request': msrc, 'smart_request': ssrc, 'skipped_deleted_not_in_input': skipped,
           'render_selfcheck': selfcheck},
          open(f'{W}/snapshot_current.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('TASK1 rows', len(out_rows), '->', OUT_FILE)
print('TASK2 rows', len(new_rows), '->', NEW_FILE)
print('skipped deleted not in input', len(skipped))
print('render self-check vs 11-Oct', dict(selfcheck))
