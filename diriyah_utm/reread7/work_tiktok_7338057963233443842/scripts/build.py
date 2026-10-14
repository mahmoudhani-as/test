# usage: python3 -I build.py
# reread7 (14-Oct-2026 ~14:50-14:54 UTC), TikTok advertiser 7338057963233443842 "H&S - DGCL - Visit Diriyah". READ-ONLY.
# Inputs (all produced from this agent's own read-only MCP calls, parsed out of the transcript by collect.py):
#   data/census.json     ad/get filtering {primary_status: STATUS_ALL} page_size 180, 5/5 pages, 792 rows
#                        (fields ad_id, campaign_automation_type, operation_status, secondary_status, create_time, modify_time)
#   data/urls.json       ad/get filtering {STATUS_NOT_DELETE, MANUAL} page_size 56, 10/10 pages, 556 rows
#                        (landing_page_url, landing_page_urls, utm_params, deeplink, page_id, modify_time)
#   data/smartplus.json  smart_plus/ad/get filtering {STATUS_ALL} page_size 40, 3/3 pages, 85 ads
#                        (landing_page_url_list, ad_configuration.utm_params, operation/secondary status, times, ad_name)
#   data/collected.json  every MCP call (also the TopView check: buying_types RESERVATION_TOP_VIEW -> 0 ads)
# Outputs:
#   reread7/out/tiktok_<acc>.jsonl          one line per input row (same order; ad_id and slot copied exactly)
#   reread7/out/new_tiktok_<acc>.jsonl      ads not in the input and not deleted (none expected)
# URL rendering rule (same as the 11-Oct values and reread4/5): a utm_params key=value is appended (before any #fragment)
# only when that key is absent from the URL query; if the key is present with another value the stored URL value is kept
# and the conflict is noted.
import json, re, collections, datetime
from urllib.parse import urlsplit, parse_qsl

BASE = "/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm"
ACC = "7338057963233443842"
ACC_NAME = "H&S - DGCL - Visit Diriyah"
W = f"{BASE}/reread7/work_tiktok_{ACC}"
inp = json.load(open(f"{BASE}/reread/in/tiktok_{ACC}.json", encoding="utf-8"))
cen = json.load(open(f"{W}/data/census.json", encoding="utf-8"))
census = cen["rows"]
urls_d = json.load(open(f"{W}/data/urls.json", encoding="utf-8"))
urls, url_src = urls_d["rows"], urls_d["src"]
sp_d = json.load(open(f"{W}/data/smartplus.json", encoding="utf-8"))
sp, sp_src = sp_d["rows"], sp_d["src"]
C = json.load(open(f"{W}/data/collected.json", encoding="utf-8"))
prev = [json.loads(l) for l in open(f"{BASE}/reread5/out/tiktok_{ACC}.jsonl", encoding="utf-8")]
prev_by = {(p['ad_id'], p['slot']): p for p in prev}
DEL = {"AD_STATUS_DELETE", "AD_STATUS_CAMPAIGN_DELETE", "AD_STATUS_ADGROUP_DELETE"}


def bj_to_utc(rid):
    """TikTok request_id starts with the Beijing (UTC+8) timestamp YYYYMMDDHHMMSS; return 'HH:MM:SS' UTC."""
    t = datetime.datetime.strptime(rid[:14], "%Y%m%d%H%M%S") - datetime.timedelta(hours=8)
    return t.strftime("%H:%M:%S")


# sanity checks on the reads
assert cen["total_number"] == [792] and len(census) == 792 and not cen["problems"], "census incomplete"
assert urls_d["total_number"] == [556] and len(urls) == 556 and not urls_d["problems"], "URL pass incomplete"
assert sp_d["total_number"] == [85] and len(sp) == 85 and not sp_d["problems"], "Smart+ read incomplete"
topview = [r for r in C if (r['input'] or {}).get('action') == 'tiktok_ad_get'
           and ((r['input'].get('params') or {}).get('filtering') or {}).get('buying_types') == ["RESERVATION_TOP_VIEW"]]
assert topview and topview[-1]['result']['data']['data']['data']['page_info']['total_number'] == 0

cen_rids = sorted(cen["request_ids"].values())
url_rids = sorted(p[3] for p in urls_d["pages"])
sp_rids = sorted(c[7] for c in sp_d["calls"])
READ_CEN = (f"census ad/get STATUS_ALL 5/5 pages 792 rows read 14-Oct {bj_to_utc(cen_rids[0])}-{bj_to_utc(cen_rids[-1])} UTC")
READ_URL = (f"URL pass ad/get STATUS_NOT_DELETE+MANUAL 10/10 pages 556 ads read 14-Oct {bj_to_utc(url_rids[0])}-{bj_to_utc(url_rids[-1])} UTC")
READ_SP = (f"smart_plus/ad/get STATUS_ALL 3/3 pages 85 ads read 14-Oct {bj_to_utc(sp_rids[0])}-{bj_to_utc(sp_rids[-1])} UTC")


def merge(base, pairs):
    if base is None:
        return None, None
    if not pairs:
        return base, "no utm_params stored on the ad (UTMs, if any, are inline in the URL)"
    b0, sep0, frag0 = base.partition('#')
    q = urlsplit(b0).query
    existing = parse_qsl(q, keep_blank_values=True)
    raw_tokens = q.split('&') if q else []
    exd = collections.defaultdict(list)
    for k, v in existing:
        exd[k].append(v)
    add, conflicts = [], []
    for k, v in pairs:
        tok = k if v is None else f"{k}={v}"
        if tok in raw_tokens:
            continue
        if v is not None and k in exd and v in exd[k]:
            continue
        if k in exd:
            conflicts.append(f"{k}: url={exd[k][0]!r} vs utm_params={v!r}")
            continue
        add.append(tok)
    notes, url = [], base
    if add:
        url = b0 + ('&' if '?' in b0 else '?') + '&'.join(add) + (sep0 + frag0)
        notes.append("utm_params not present in the stored landing page URL were appended: " + ", ".join(add))
    if conflicts:
        notes.append("utm_params value differs from the value already in the stored URL (stored URL value kept): " + "; ".join(conflicts))
    if not add and not conflicts:
        notes.append("all utm_params already present in the stored landing page URL (no change on merge)")
    return url, "; ".join(notes)


def qdiff(old, new):
    o, n = urlsplit(old), urlsplit(new)
    parts = []
    if (o.scheme, o.netloc, o.path) != (n.scheme, n.netloc, n.path):
        parts.append(f"base {o.scheme}://{o.netloc}{o.path} -> {n.scheme}://{n.netloc}{n.path}")
    oq, nq = dict(parse_qsl(o.query, keep_blank_values=True)), dict(parse_qsl(n.query, keep_blank_values=True))
    for k in list(oq) + [k for k in nq if k not in oq]:
        if oq.get(k) != nq.get(k):
            if k not in nq:
                parts.append(f"{k} removed (was {oq[k]!r})")
            elif k not in oq:
                parts.append(f"{k} added {nq[k]!r}")
            else:
                parts.append(f"{k} {oq[k]!r} -> {nq[k]!r}")
    if o.fragment != n.fragment:
        parts.append(f"fragment {o.fragment!r} -> {n.fragment!r}")
    if not parts and old != new:
        parts.append("same params, different encoding/order")
    return "; ".join(parts)


def cmp_notes(url, r, status_now):
    parts = []
    if url == r['url_11oct']:
        parts.append("URL unchanged vs 11-Oct" if url is not None else "still no URL (as on 11-Oct)")
    elif r['url_11oct'] is None:
        parts.append("URL now set; on 11-Oct there was none")
    elif url is None:
        parts.append(f"URL now empty; on 11-Oct it was {r['url_11oct']}")
    else:
        parts.append(f"URL changed vs 11-Oct ({qdiff(r['url_11oct'], url)})")
    p = prev_by.get((r['ad_id'], r['slot']))
    if p is not None:
        if p['url'] == url:
            parts.append("URL same as the 13-Oct 14:30 UTC re-read")
        elif p['url'] is None:
            parts.append("URL CHANGED SINCE 13-Oct re-read (then no URL)")
        elif url is None:
            parts.append(f"URL CHANGED SINCE 13-Oct re-read (now empty; then {p['url']})")
        else:
            parts.append(f"URL CHANGED SINCE 13-Oct re-read ({qdiff(p['url'], url)}; 13-Oct URL: {p['url']})")
        if p.get('status_now') and status_now and p['status_now'] != status_now:
            parts.append(f"delivery status changed since 13-Oct ({p['status_now']} -> {status_now})")
    if r.get('status_11oct') and status_now and r['status_11oct'] != status_now:
        parts.append(f"delivery status changed since 11-Oct ({r['status_11oct']} -> {status_now})")
    elif r.get('status_11oct'):
        parts.append("delivery status same as 11-Oct")
    return parts


def odd_chars(u):
    if u is None:
        return None
    bad = sorted({f"U+{ord(ch):04X}" for ch in u if ord(ch) > 126 or ch.isspace()})
    return bad or None


# ---- Task 1 ----
out, errs = [], []
mt_diff = []
for r in inp:
    aid, slot = r['ad_id'], r['slot']
    rec = {"platform": "tiktok", "account_id": ACC, "ad_id": aid, "slot": slot, "url": None,
           "status_now": None, "creative_id_now": None, "found": False, "note": ""}
    notes = []
    if slot == "ad.landing_page_url":
        c = census.get(aid)
        if c is None:
            rec['status_now'] = "NOT_FOUND"
            rec['note'] = ("Ad not returned by /v1.3/ad/get/ with primary_status STATUS_ALL (complete 792-row census): "
                           "the ad no longer exists (deleted).")
            out.append(rec)
            errs.append(f"{aid} missing from census")
            continue
        st = c['secondary_status']
        rec['status_now'] = st
        deleted = st in DEL
        rec['found'] = not deleted
        u = urls.get(aid)
        if u is None and not deleted:
            errs.append(f"{aid} not in URL pass")
        u = u or {}
        if u and u.get('modify_time') != c.get('modify_time'):
            mt_diff.append((aid, c.get('modify_time'), u.get('modify_time')))
        base = u.get('landing_page_url') or None
        pairs = [(p.get('key'), p.get('value')) for p in (u.get('utm_params') or []) if p.get('key') is not None]
        url, mnote = merge(base, pairs)
        rec['url'] = url
        notes.append(f"Manual campaign ad; operation_status {c.get('operation_status')}; delivery status (secondary_status) {st}")
        if deleted:
            notes.append(f"ad is DELETED ({st}); no URL read for deleted ads")
        if base is None and not deleted:
            extra = [f"{k} {u.get(k)}" for k in ('landing_page_urls', 'deeplink', 'page_id') if u.get(k)]
            notes.append("no landing page URL on this ad (landing_page_url empty" +
                         ("; " + "; ".join(extra) if extra else "; landing_page_urls, deeplink and page_id also empty") + ")")
            if pairs:
                notes.append("utm_params set but landing_page_url empty, so no final URL")
        elif mnote:
            notes.append(mnote)
        oc = odd_chars(url)
        if oc:
            notes.append(f"stored URL contains non-ASCII/invisible characters {oc} (kept exactly as stored)")
        notes += cmp_notes(url, r, st)
        notes.append(f"ad last modified {c.get('modify_time')} UTC")
        s = url_src.get(aid) or {}
        notes.append(f"{READ_CEN}; {READ_URL} (this ad: page {s.get('page')}, request_id {s.get('request_id')})")
        notes.append("TikTok ads have no separate creative ID (creative_id_now null, as on 11-Oct)")
    elif slot.startswith("smart_plus_ad.landing_page_url_list"):
        a = sp.get(aid)
        if a is None:
            rec['status_now'] = "NOT_FOUND"
            rec['note'] = ("Upgraded Smart+ ad not returned by /v1.3/smart_plus/ad/get/ with primary_status STATUS_ALL "
                           "(all 85 Smart+ ads read): the ad no longer exists (deleted).")
            out.append(rec)
            errs.append(f"{aid} missing from smart+ reads")
            continue
        st = a['secondary_status']
        rec['status_now'] = st
        m = re.match(r"smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url$", slot)
        idx = int(m.group(1)) if m else 0
        lpl = a.get('landing_page_url_list') or []
        pairs = [(p.get('key'), p.get('value')) for p in ((a.get('ad_configuration') or {}).get('utm_params') or []) if p.get('key') is not None]
        deleted = st in DEL
        rec['found'] = not deleted
        notes.append(f"Upgraded Smart+ ad (smart_plus_ad_id); operation_status {a.get('operation_status')}; delivery status "
                     f"(secondary_status) {st}; landing_page_url_list has {len(lpl)} entr{'y' if len(lpl) == 1 else 'ies'}")
        if deleted:
            notes.append(f"ad is DELETED ({st}); url shown is the last stored value")
        if idx < len(lpl) and (lpl[idx].get('landing_page_url') or None):
            url, mnote = merge(lpl[idx]['landing_page_url'], pairs)
            rec['url'] = url
            if not m:
                notes.append("slot recorded without an index on 11-Oct (no URL then); entry [0] reported")
            notes.append(mnote + (" (ad_configuration.utm_params)" if pairs else ""))
        else:
            notes.append("landing_page_url_list absent/empty in smart_plus/ad/get response (no website URL on this ad)"
                         if not lpl else f"landing_page_url_list[{idx}] not present")
            if pairs:
                notes.append("ad_configuration.utm_params set but there is no URL to attach them to")
        oc = odd_chars(rec['url'])
        if oc:
            notes.append(f"stored URL contains non-ASCII/invisible characters {oc} (kept exactly as stored)")
        notes += cmp_notes(rec['url'], r, st)
        notes.append(f"ad last modified {a.get('modify_time')} UTC")
        s = sp_src.get(aid) or {}
        notes.append(f"{READ_SP} (this ad: page {s.get('page')}, request_id {s.get('request_id')})")
        notes.append("TikTok ads have no separate creative ID (creative_id_now null, as on 11-Oct)")
    else:
        errs.append(f"unknown slot {slot!r} for {aid}")
        rec['status_now'] = "UNKNOWN_SLOT"
        rec['found'] = True
        rec['note'] = f"slot {slot!r} not recognised by this reader; not re-read"
        out.append(rec)
        continue
    rec['note'] = "; ".join(n for n in notes if n)
    out.append(rec)

out_path = f"{BASE}/reread7/out/tiktok_{ACC}.jsonl"
with open(out_path, "w", encoding="utf-8") as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---- Task 2: ads not in the input, not deleted ----
in_ids = {r['ad_id'] for r in inp}
new = []
for aid, c in sorted(census.items(), key=lambda kv: (kv[1].get('create_time') or '', kv[0])):
    if c.get('campaign_automation_type') == 'UPGRADED_SMART_PLUS_CREATIVE':
        continue  # creatives of Upgraded Smart+ ads; the ads themselves are checked via smart_plus/ad/get below
    if aid in in_ids or c['secondary_status'] in DEL:
        continue
    errs.append(f"new {c.get('campaign_automation_type')} ad {aid} needs names/URL (not expected)")
for sid, a in sorted(sp.items(), key=lambda kv: (kv[1].get('create_time') or '', kv[0])):
    if sid in in_ids or a['secondary_status'] in DEL:
        continue
    errs.append(f"new Smart+ ad {sid} needs names/URL (not expected)")
new_path = f"{BASE}/reread7/out/new_tiktok_{ACC}.jsonl"
with open(new_path, "w", encoding="utf-8") as f:
    for rec in new:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

c1 = collections.Counter()
chg13 = []
for rec, r in zip(out, inp):
    c1['url_same_11oct' if rec['url'] == r['url_11oct'] else 'url_changed_11oct'] += 1
    c1['status_same_11oct' if rec['status_now'] == r['status_11oct'] else 'status_changed_11oct'] += 1
    p = prev_by.get((r['ad_id'], r['slot']))
    if p is not None and p['url'] != rec['url']:
        chg13.append((r['ad_id'], r['slot'], p['url'], rec['url']))
    if p is not None and p['status_now'] != rec['status_now']:
        c1['status_changed_since_13oct'] += 1
print("rows", len(out), "found", sum(1 for x in out if x['found']), "not_found", sum(1 for x in out if not x['found']),
      "url_null", sum(1 for x in out if x['url'] is None), dict(c1), "new", len(new))
print("URL changed since 13-Oct re-read:", len(chg13))
for x in chg13:
    print("  ", x[0], x[1], "\n     13-Oct:", x[2], "\n     now:   ", x[3])
print("modify_time differences census vs URL pass:", mt_diff)
print("errs", errs)
