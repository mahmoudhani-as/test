# usage: python3 -I build.py
# Builds reread5 outputs for TikTok account 7338074303931449345 (H&S - DGCL - Diriyah Gate) from the read-only API responses
# collected byte-for-byte from this agent's own transcript into ../data/collected.json (scripts/collect.py):
#   TASK 1: reread5/out/tiktok_<acc>.jsonl       one line per input row, same order, ad_id and slot copied exactly
#   TASK 2: reread5/out/new_tiktok_<acc>.jsonl   ads not in the input (created after the 11-Oct pull), deleted/removed skipped
#   EXTRA : work/spark_check/apply11_spark_check_<acc>.json  Spark Push post check of the 4 apply11 ads
# URL rule (same as the 11-Oct pull; self-check printed at the end): the stored landing page URL with every utm_params key that
# is missing from its query appended (before any #fragment); a key already in the URL with a different value keeps the URL
# value and the conflict is noted.
import collections
import datetime
import json
import os
from urllib.parse import parse_qsl, quote, urlsplit

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
ACC = '7338074303931449345'
ACC_NAME = 'H&S - DGCL - Diriyah Gate'
W = f'{BASE}/reread5/work_tiktok_{ACC}'
IN_FILE = f'{BASE}/reread/in/tiktok_{ACC}.json'
OUT_FILE = f'{BASE}/reread5/out/tiktok_{ACC}.jsonl'
NEW_FILE = f'{BASE}/reread5/out/new_tiktok_{ACC}.jsonl'
SPARK_IN = f'{BASE}/work/spark_check/apply11_spark_{ACC}.json'
SPARK_OUT = f'{BASE}/work/spark_check/apply11_spark_check_{ACC}.json'
PREV_FILE = f'{BASE}/reread4/out/tiktok_{ACC}.jsonl'  # 13-Oct ~12:20 UTC re-read (before apply11), only used for change notes
SLOT_MANUAL = 'ad.landing_page_url'
SLOT_SP0 = 'smart_plus_ad.landing_page_url_list[0].landing_page_url'
DELETED = {'AD_STATUS_DELETE', 'AD_STATUS_CAMPAIGN_DELETE', 'AD_STATUS_ADGROUP_DELETE'}

inp = json.load(open(IN_FILE, encoding='utf-8'))
spark_in = json.load(open(SPARK_IN, encoding='utf-8'))
C = json.load(open(f'{W}/data/collected.json', encoding='utf-8'))
prev = {}
if os.path.exists(PREV_FILE):
    for l in open(PREV_FILE, encoding='utf-8'):
        o = json.loads(l)
        prev[(o['ad_id'], o['slot'])] = o


def req_utc(rid):
    """Marketing API request_id starts with YYYYMMDDHHMMSS in UTC+8."""
    t = datetime.datetime.strptime(rid[:14], '%Y%m%d%H%M%S') - datetime.timedelta(hours=8)
    return t.strftime('%H:%M:%S')


def id_time(item_id):
    """UTC time embedded in a TikTok post id (upper 32 bits = Unix seconds). Informational only."""
    return datetime.datetime.fromtimestamp(int(item_id) >> 32, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


# ---------------- classify the collected calls ----------------
def body(x):
    r = x['result']
    assert isinstance(r, dict) and r.get('success') is True, (x['seq'], str(r)[:300])
    d = r['data']['data']
    assert d['code'] == 0, (x['seq'], d.get('message'))
    assert not (r.get('meta') or {}).get('mcp_output_budget'), ('MCP output budget hit', x['seq'])
    assert not ((r.get('data') or {}).get('meta') or {}).get('mcp_output_budget'), ('MCP output budget hit', x['seq'])
    return d


groups = collections.defaultdict(dict)  # kind -> page -> (seq, rid, list, page_info)
video_info, video_get, other_calls = [], [], []
for x in C:
    i = x['input'] or {}
    act = i.get('action')
    p = i.get('params') or {}
    f = p.get('filtering') or {}
    flds = p.get('fields') or []
    if act == 'tiktok_identity_video_info_get':
        video_info.append((x, body(x)))
        continue
    if act == 'tiktok_identity_video_get':
        video_get.append((x, body(x)))
        continue
    if act == 'tiktok_ad_get' and f == {'primary_status': 'STATUS_ALL'} and 'campaign_automation_type' in flds:
        kind = 'census'
    elif act == 'tiktok_ad_get' and f == {'primary_status': 'STATUS_ALL'}:
        kind = 'final_census'
    elif act == 'tiktok_ad_get' and f.get('campaign_automation_type') == 'MANUAL':
        kind = 'manual'
    elif act == 'tiktok_ad_get' and f.get('ad_ids'):
        kind = 'by_ids'
    elif act == 'tiktok_smart_plus_ad_get' and 'landing_page_url_list' in flds:
        kind = 'smart'
    elif act == 'tiktok_smart_plus_ad_get':
        kind = 'final_smart_census'
    else:
        other_calls.append((x['seq'], act))
        continue
    d = body(x)
    lst = d['data']['list']
    assert all(isinstance(it, dict) for it in lst), ('truncated list item', x['seq'])
    page = p.get('page', 1) if kind != 'by_ids' else x['seq']
    assert page not in groups[kind], ('page read twice', kind, page)
    groups[kind][page] = (x['seq'], d['request_id'], lst, d['data']['page_info'])


def merged(kind, key):
    pages = groups[kind]
    tp = {v[3]['total_page'] for v in pages.values()}
    tn = {v[3]['total_number'] for v in pages.values()}
    assert len(tp) == 1 and len(tn) == 1, (kind, tp, tn)
    assert sorted(pages) == list(range(1, tp.pop() + 1)), (kind, sorted(pages))
    out, src = {}, {}
    for pg in sorted(pages):
        seq, rid, lst, _ = pages[pg]
        for it in lst:
            assert it[key] not in out, (kind, 'duplicate', it[key])
            out[it[key]] = it
            src[it[key]] = (rid, pg, len(pages))
    assert len(out) == tn.pop(), (kind, len(out))
    return out, src


census, _ = merged('census', 'ad_id')
manual, msrc = merged('manual', 'ad_id')
smart, ssrc = merged('smart', 'smart_plus_ad_id')
final_ad, _ = merged('final_census', 'ad_id')
final_sp, _ = merged('final_smart_census', 'smart_plus_ad_id')
by_ids = {}
for seq, rid, lst, pi in groups['by_ids'].values():
    for it in lst:
        by_ids[it['ad_id']] = it

c_manual = {a for a, v in census.items() if v['campaign_automation_type'] == 'MANUAL'}
c_children = {a: v for a, v in census.items() if v['campaign_automation_type'] == 'UPGRADED_SMART_PLUS_CREATIVE'}
assert set(census) == c_manual | set(c_children), 'unexpected campaign_automation_type in census'
assert set(manual) == c_manual, 'manual full read must cover the account census'
assert {v['smart_plus_ad_id'] for v in c_children.values()} == set(smart), 'Smart+ creative rows <-> Smart+ ads'
assert set(final_ad) == set(census), 'final census returned a different ad set'
assert set(final_sp) == set(smart), 'final Smart+ census returned a different ad set'
t_census = sorted(req_utc(v[1]) for v in groups['census'].values())
t_manual = sorted(req_utc(v[1]) for v in groups['manual'].values())
t_smart = sorted(req_utc(v[1]) for v in groups['smart'].values())
t_final = sorted(req_utc(v[1]) for k in ('final_census', 'final_smart_census') for v in groups[k].values())
NM, NS, NC = len(manual), len(smart), len(census)
RECHECK_F = ('modify_time', 'secondary_status', 'operation_status')


def recheck_note(kind, a, cur):
    ref = (final_ad if kind == 'manual' else final_sp).get(a)
    if ref is None:
        return f'NOT returned by the {t_final[0]}-{t_final[-1]} UTC re-check census'
    flds = RECHECK_F + (('tiktok_item_id',) if kind == 'manual' else ())
    d = [f"{f} {cur.get(f)} -> {ref.get(f)}" for f in flds if cur.get(f) != ref.get(f)]
    if d:
        return f'CHANGED at the {t_final[0]}-{t_final[-1]} UTC re-check: ' + '; '.join(d)
    return f're-checked {t_final[0]}-{t_final[-1]} UTC: modify_time and status unchanged'


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
        return [f'{field} not set (UTMs only inline in the URL)']
    if info['added']:
        parts.append(f"{field} keys missing from the stored URL appended: " + ', '.join(f'{k}={v}' for k, v in info['added']))
    for k, uv, pv in info['conflicts']:
        parts.append(f"CONFLICT {k}: stored URL has '{uv}' but {field} has '{pv}' (url keeps the stored URL value)")
    if info['same'] and not info['added'] and not info['conflicts']:
        parts.append(f"{field} identical to the query already in the stored URL")
    if info['url_only']:
        parts.append(f"stored URL has {', '.join(info['url_only'])} not present in {field}")
    return parts


# ---------------- Spark Push check (post lookups) ----------------
spark = {s['ad_id']: s['orig_item'] for s in spark_in}
looked_up = {}  # item_id -> (status, request_id, endpoint)
for x, d in video_info:
    for vd in (d['data'].get('video_details') or []) + [d['data'].get('video_detail') or {}]:
        if vd.get('item_id'):
            looked_up[vd['item_id']] = (vd.get('status'), d['request_id'], 'identity/video/info')
for x, d in video_get:
    for vd in d['data'].get('video_list') or []:
        looked_up.setdefault(vd['item_id'], (vd.get('status'), d['request_id'], 'identity/video/get'))
create_time_keys = {k for x, d in video_info + video_get for vd in
                    ((d['data'].get('video_details') or []) + (d['data'].get('video_list') or []))
                    for k in vd if 'time' in k.lower() or 'date' in k.lower()}
assert not create_time_keys, ('a post lookup returned a time field - use it', create_time_keys)
import glob
import re
apply11_log = {}  # ad_id -> (modify_time right after the apply11 write, tiktok_item_id right after the write)
for fp in sorted(glob.glob(f'{BASE}/apply11/out_tiktok_spark_push_*.jsonl')):
    for l in open(fp, encoding='utf-8'):
        o = json.loads(l)
        if o.get('account_id') == ACC and o.get('unit') in spark:
            mt = re.search(r'modify_time -> (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) UTC', o.get('detail') or '')
            it = re.search(r'tiktok_item_id right after the write: (\d+)', o.get('detail') or '')
            apply11_log[o['unit']] = (mt.group(1) if mt else None, it.group(1) if it else None, o.get('result'))
spark_rows, spark_note = [], {}
for a, orig in spark.items():
    cur = manual[a]
    ci = cur.get('tiktok_item_id')
    chg = ci != orig
    spark_rows.append({'ad_id': a, 'orig_item': orig, 'current_item': ci, 'changed': chg,
                       'orig_created': None, 'cur_created': None})
    lk = []
    for lab, it in (('orig', orig), ('current', ci)):
        if it in looked_up:
            st, rid, ep = looked_up[it]
            lk.append(f"{lab} post {it} exists ({ep} {req_utc(rid)} UTC: status {st}; no create-time field returned)")
        elif not chg:
            lk.append(f"post {it} not looked up (item unchanged; create times are only read for changed posts)")
            break
        else:
            lk.append(f"{lab} post {it} not looked up")
    ref = final_ad[a].get('tiktok_item_id')
    lg = apply11_log.get(a)
    lgt = (f"apply11 log ({lg[2]}): right after its write modify_time {lg[0]} UTC and tiktok_item_id {lg[1]}"
           f"{' (unchanged then)' if lg[1] == orig else ''}; now modify_time {cur.get('modify_time')} UTC"
           if lg else 'apply11 log entry not found')
    spark_note[a] = (f"Spark Push check (apply11 write 13-Oct): identity {cur.get('identity_type')} {cur.get('identity_id')} / "
                     f"BC {cur.get('identity_authorized_bc_id')}; tiktok_item_id now {ci} vs orig_item {orig} before the write -> "
                     + (f"CHANGED (new post; time embedded in the post ids {id_time(ci)} UTC vs orig {id_time(orig)} UTC, "
                        f"informational only, not from a lookup); " if chg else "UNCHANGED; ")
                     + lgt + '; ' + '; '.join(lk)
                     + f"; re-check census {t_final[0]}-{t_final[-1]} UTC tiktok_item_id {ref}")

# ---------------- rendering rule self-check on the 11-Oct pull itself ----------------
# re-render every 11-Oct row from its own base_url_11oct + url_tags_11oct and compare with url_11oct
rule_check = collections.Counter()
for r in inp:
    if r.get('base_url_11oct') is None:
        rule_check['no_base_11oct'] += 1
        continue
    pairs = [{'key': k, 'value': v} for k, v in parse_qsl(r.get('url_tags_11oct') or '', keep_blank_values=True)]
    u, _ = render(r['base_url_11oct'], pairs)
    rule_check['rule_matches_11oct' if u == r.get('url_11oct') else 'rule_differs_11oct'] += 1
    if u != r.get('url_11oct'):
        print('RULE DIFF', r['ad_id'], u, r.get('url_11oct'))

# ---------------- TASK 1 ----------------
assert all(r.get('creative_id') is None for r in inp), 'input has creative ids'
out_rows, selfcheck, stats = [], collections.Counter(), collections.Counter()
for r in inp:
    a, slot = r['ad_id'], r['slot']
    notes = []
    if slot == SLOT_MANUAL:
        cur = manual.get(a)
        if cur is None:
            out_rows.append({'platform': 'tiktok', 'account_id': ACC, 'ad_id': a, 'slot': slot, 'url': None,
                             'status_now': 'NOT_FOUND', 'creative_id_now': None, 'found': False,
                             'note': f'Ad not returned by /v1.3/ad/get/ with primary_status STATUS_ALL (all {NM} manual ads of the '
                                     f'account read 13-Oct): the ad no longer exists (deleted).'})
            stats['not_found'] += 1
            continue
        rid, pg, npg = msrc[a]
        raw = cur.get('landing_page_url') or None
        utm = cur.get('utm_params')
        field = 'utm_params'
        url, info = render(raw, utm)
        notes.append(f"Manual ad (ad_format {cur.get('ad_format')}); read-only /v1.3/ad/get/ 13-Oct {req_utc(rid)} UTC "
                     f"(filtering primary_status STATUS_ALL + campaign_automation_type MANUAL, page {pg} of {npg}, request {rid})")
        if raw is None:
            extra = [f'{k}={cur.get(k)!r}' for k in ('landing_page_urls', 'deeplink', 'page_id') if cur.get(k)]
            notes.append('landing_page_url still empty: no destination URL on this ad' +
                         (' (' + ', '.join(extra) + ')' if extra else ' (landing_page_urls null, deeplink empty, page_id null)'))
            if utm_pairs(utm):
                notes.append(f'{field} set ({tags_str(utm)}) but there is no URL to carry them')
        else:
            notes += info_text(info, field, bool(utm_pairs(utm)))
    else:
        assert slot == SLOT_SP0, slot
        cur = smart.get(a)
        if cur is None:
            out_rows.append({'platform': 'tiktok', 'account_id': ACC, 'ad_id': a, 'slot': slot, 'url': None,
                             'status_now': 'NOT_FOUND', 'creative_id_now': None, 'found': False,
                             'note': f'Smart+ ad not returned by /v1.3/smart_plus/ad/get/ with primary_status STATUS_ALL (all {NS} '
                                     f'Upgraded Smart+ ads of the account read 13-Oct): the ad no longer exists (deleted).'})
            stats['not_found'] += 1
            continue
        rid, pg, npg = ssrc[a]
        lst = cur.get('landing_page_url_list') or []
        raw = (lst[0].get('landing_page_url') if lst else None) or None
        utm = (cur.get('ad_configuration') or {}).get('utm_params')
        field = 'ad_configuration.utm_params'
        url, info = render(raw, utm)
        notes.append(f"Upgraded Smart+ ad; read-only /v1.3/smart_plus/ad/get/ 13-Oct {req_utc(rid)} UTC "
                     f"(filtering primary_status STATUS_ALL, page {pg} of {npg}, request {rid})")
        if len(lst) != 1:
            notes.append(f'landing_page_url_list has {len(lst)} entries: ' + json.dumps(lst, ensure_ascii=False))
        if cur.get('deeplink_list'):
            notes.append('deeplink_list=' + json.dumps(cur['deeplink_list'], ensure_ascii=False))
        if raw is None:
            notes.append('landing_page_url_list[0] empty: no destination URL')
        else:
            notes += info_text(info, field, bool(utm_pairs(utm)))
    # self-check of the rendering rule against the 11-Oct pull
    if raw == r.get('base_url_11oct') and (tags_str(utm) or None) == (r.get('url_tags_11oct') or None):
        selfcheck['same_inputs'] += 1
        selfcheck['render_matches_11oct' if url == r.get('url_11oct') else 'render_differs_11oct'] += 1
    d = qdiff(r.get('url_11oct'), url)
    if url is None and r.get('url_11oct') is None:
        notes.insert(1, 'still no URL (none on 11-Oct either)')
        stats['null_both'] += 1
    elif not d:
        notes.insert(1, 'URL unchanged since 11-Oct')
        stats['url_same_11oct'] += 1
    else:
        notes.insert(1, 'URL changed since 11-Oct: ' + '; '.join(d))
        stats['url_changed_11oct'] += 1
    ch = utm_change(r.get('url_tags_11oct'), utm, field)
    if ch:
        notes.append(ch)
    st = cur.get('secondary_status')
    if st != r.get('status_11oct'):
        notes.append(f"delivery status 11-Oct {r.get('status_11oct')} -> now {st}")
        stats['status_changed_11oct'] += 1
    notes.append(f"operation_status {cur.get('operation_status')}, secondary_status {st}; last modified {cur.get('modify_time')} UTC")
    rc = recheck_note('manual' if slot == SLOT_MANUAL else 'smart', a, cur)
    notes.append(rc)
    stats['recheck_' + rc.split(' ')[0]] += 1
    p = prev.get((a, slot))
    if p is not None:
        pd = []
        if p.get('url') != url:
            pd.append('URL ' + '; '.join(qdiff(p.get('url'), url)))
        if p.get('status_now') != st:
            pd.append(f"status {p.get('status_now')} -> {st}")
        if pd:
            notes.append('changed since the 13-Oct ~12:20 UTC re-read: ' + ' | '.join(pd))
            stats['changed_since_reread4'] += 1
        else:
            notes.append('same URL and status as the 13-Oct ~12:20 UTC re-read')
    if slot == SLOT_MANUAL:
        notes.append('TikTok has no separate creative ID for a manual ad (creative_id_now null, as on 11-Oct)')
    else:
        notes.append('the Smart+ URL is owned by the Smart+ ad, no separate creative ID (creative_id_now null, as on 11-Oct)')
    if a in spark and slot == SLOT_MANUAL:
        notes.append(spark_note[a])
    deleted = st in DELETED
    note = '; '.join(notes)
    if deleted:
        note = f'Ad now has secondary_status {st}: deleted (the API still returns it under STATUS_ALL); ' + note
        stats['deleted'] += 1
    row = {'platform': 'tiktok', 'account_id': ACC, 'ad_id': a, 'slot': slot, 'url': url,
           'status_now': st, 'creative_id_now': None, 'found': not deleted, 'note': note}
    if a in spark and slot == SLOT_MANUAL:
        row['tiktok_item_id_now'] = cur.get('tiktok_item_id')
        row['identity_type_now'] = cur.get('identity_type')
        stats['spark_rows'] += 1
    out_rows.append(row)

os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
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
    kids = [c for c in by_ids.values() if c.get('smart_plus_ad_id') == a]
    assert kids, f'no creative row read for new Smart+ ad {a}'
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

# ---------------- EXTRA: Spark Push check file ----------------
with open(SPARK_OUT, 'w', encoding='utf-8') as f:
    json.dump(spark_rows, f, ensure_ascii=False, indent=1)

json.dump({'manual': manual, 'smart_plus': smart, 'census': census, 'final_census': final_ad, 'final_smart_census': final_sp,
           'smart_plus_creative_rows_by_ids': by_ids, 'manual_src': msrc, 'smart_src': ssrc,
           'skipped_deleted_not_in_input': skipped, 'post_lookups': looked_up, 'spark_check': spark_rows,
           'other_calls': other_calls,
           'read_times_utc': {'census': t_census, 'manual': t_manual, 'smart': t_smart, 'final_recheck': t_final},
           'render_selfcheck': selfcheck, 'stats': stats},
          open(f'{W}/data/snapshot.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('census', NC, 'rows (', len(c_manual), 'MANUAL +', len(c_children), 'Smart+ creative rows ) read', t_census)
print('manual full read', NM, t_manual, '| smart+ full read', NS, t_smart, '| final re-check', t_final)
print('TASK1 rows', len(out_rows), '->', OUT_FILE)
print('TASK2 rows', len(new_rows), 'ads', len({x['ad_id'] for x in new_rows}), '->', NEW_FILE)
print('skipped deleted not in input', len(skipped), collections.Counter(s[0] + ':' + s[2] for s in skipped))
print('render self-check vs 11-Oct', dict(selfcheck), '| rule re-applied to every 11-Oct row', dict(rule_check))
print('apply11 log', apply11_log)
print('stats', dict(stats))
print('spark', json.dumps(spark_rows))
print('other calls (not used for data):', other_calls)
