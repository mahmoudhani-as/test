# usage: python3 -I build.py
# reread5 (13-Oct-2026 ~14:25-14:37 UTC), TikTok advertiser 7338057963233443842 "H&S - DGCL - Visit Diriyah". READ-ONLY.
# Inputs (all produced from this agent's own read-only MCP calls, parsed out of the transcript by collect.py):
#   data/census.json     ad/get filtering {primary_status: STATUS_ALL} page_size 100, 8/8 pages, 792 rows
#                        (fields ad_id, campaign_automation_type, operation/secondary status, modify/create time,
#                        tiktok_item_id, identity_type/id/authorized_bc_id, ad_format)
#   data/urls.json       ad/get filtering {STATUS_NOT_DELETE, MANUAL} - landing_page_url(s), utm_params, deeplink, page_id
#   data/smartplus.json  smart_plus/ad/get filtering {STATUS_ALL} - union of all pages (85 ads)
#   data/collected.json  every MCP call (spark re-check by ad_ids, identity/video/info lookups)
# Outputs:
#   reread5/out/tiktok_<acc>.jsonl          one line per input row (same order; ad_id and slot copied exactly)
#   reread5/out/new_tiktok_<acc>.jsonl      ads not in the input and not deleted (none expected)
#   work/spark_check/apply11_spark_check_<acc>.json
#   data/spark_item_id_times.json           side file: creation second encoded in the TikTok item IDs (NOT a lookup)
# URL rendering rule (same as the 11-Oct values and reread4): a utm_params key=value is appended (before any #fragment)
# only when that key is absent from the URL query; if the key is present with another value the stored URL value is kept
# and the conflict is noted.
import json, re, collections, datetime
from urllib.parse import urlsplit, parse_qsl

BASE = "/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm"
ACC = "7338057963233443842"
ACC_NAME = "H&S - DGCL - Visit Diriyah"
W = f"{BASE}/reread5/work_tiktok_{ACC}"
inp = json.load(open(f"{BASE}/reread/in/tiktok_{ACC}.json", encoding="utf-8"))
cen = json.load(open(f"{W}/data/census.json", encoding="utf-8"))
census = cen["rows"]
urls_d = json.load(open(f"{W}/data/urls.json", encoding="utf-8"))
urls, url_src = urls_d["rows"], urls_d["src"]
sp_d = json.load(open(f"{W}/data/smartplus.json", encoding="utf-8"))
sp, sp_src = sp_d["rows"], sp_d["src"]
C = json.load(open(f"{W}/data/collected.json", encoding="utf-8"))
spark_in = json.load(open(f"{BASE}/work/spark_check/apply11_spark_{ACC}.json", encoding="utf-8"))
DEL = {"AD_STATUS_DELETE", "AD_STATUS_CAMPAIGN_DELETE", "AD_STATUS_ADGROUP_DELETE"}


def bj_to_utc(rid):
    """TikTok request_id starts with the Beijing (UTC+8) timestamp YYYYMMDDHHMMSS; return 'HH:MM:SS' UTC."""
    t = datetime.datetime.strptime(rid[:14], "%Y%m%d%H%M%S") - datetime.timedelta(hours=8)
    return t.strftime("%H:%M:%S")


def id_time(item_id):
    """Creation second encoded in a TikTok item ID (top 32 bits = Unix seconds)."""
    return datetime.datetime.fromtimestamp(int(item_id) >> 32, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


cen_rids = sorted(cen["request_ids"].values())
url_rids = sorted(p[3] for p in urls_d["pages"])
sp_rids = sorted(c[7] for c in sp_d["calls"])
READ_CEN = (f"census /v1.3/ad/get/ filtering primary_status STATUS_ALL page_size 100, 8/8 pages, 792 rows "
            f"(643 MANUAL + 149 UPGRADED_SMART_PLUS_CREATIVE), read 13-Oct {bj_to_utc(cen_rids[0])}-{bj_to_utc(cen_rids[-1])} UTC")
READ_URL = (f"URL fields from /v1.3/ad/get/ filtering primary_status STATUS_NOT_DELETE + campaign_automation_type MANUAL "
            f"(total_number 556), page_size 45 (pages 1-7) and 50 (pages 7-12) because 100 rows with URL+utm_params exceed the "
            f"65,536-byte MCP cap; read {bj_to_utc(url_rids[0])}-{bj_to_utc(url_rids[-1])} UTC; modify_time and delivery status "
            f"identical to the census for all 556 ads")
READ_SP = (f"/v1.3/smart_plus/ad/get/ filtering primary_status STATUS_ALL (total_number 85 incl. deleted), page_size 40 pages 1+3 "
           f"and page_size 20 pages 3+4 (page 2 at 40 hit the MCP cap); union of reads covers all 85; read "
           f"{bj_to_utc(sp_rids[0])}-{bj_to_utc(sp_rids[-1])} UTC")


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
        parts.append(f"URL CHANGED vs 11-Oct ({qdiff(r['url_11oct'], url)}; 11-Oct URL: {r['url_11oct']})")
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


# ---- Spark Push: re-check read by ad_ids (after the census) and identity/video/info lookups ----
recheck, recheck_rid = {}, None
lookup_ok, lookup_fail, lookup_rids = {}, [], []
for r in C:
    inpc = r['input'] or {}
    p = inpc.get('params') or {}
    res = r['result'] if isinstance(r['result'], dict) else {}
    if inpc.get('action') == 'tiktok_ad_get' and isinstance((p.get('filtering') or {}).get('ad_ids'), list) and res.get('success'):
        inner = res['data']['data']
        for x in inner['data']['list']:
            recheck[x['ad_id']] = x
        recheck_rid = inner.get('request_id')
    if inpc.get('action') == 'tiktok_identity_video_info_get':
        ids = p.get('item_ids') or ([p['item_id']] if p.get('item_id') else [])
        if res.get('success'):
            inner = res['data']['data']
            lookup_rids.append(inner.get('request_id'))
            for x in (inner.get('data') or {}).get('video_details') or []:
                lookup_ok[x['item_id']] = x
        else:
            lookup_fail.append((tuple(ids), p.get('identity_id'), p.get('identity_authorized_bc_id')))
# items that failed in every lookup that included them and never succeeded
not_fetchable = set()
for ids, _, _ in lookup_fail:
    if len(ids) == 1 and ids[0] not in lookup_ok:
        not_fetchable.add(ids[0])
create_field_seen = any('create_time' in x for x in lookup_ok.values())

spark_ids = {x['ad_id']: x['orig_item'] for x in spark_in}
spark_rows, id_times, recheck_diffs = [], [], []
for x in spark_in:
    aid, orig = x['ad_id'], x['orig_item']
    c = census[aid]
    cur = c.get('tiktok_item_id')
    rc = recheck.get(aid) or {}
    if rc.get('tiktok_item_id') != cur or rc.get('modify_time') != c.get('modify_time'):
        recheck_diffs.append((aid, cur, rc.get('tiktok_item_id'), c.get('modify_time'), rc.get('modify_time')))
    changed = cur != orig
    spark_rows.append({"ad_id": aid, "orig_item": orig, "current_item": cur, "changed": changed,
                       "orig_created": None, "cur_created": None})
    id_times.append({"ad_id": aid, "orig_item": orig, "current_item": cur, "changed": changed,
                     "orig_item_id_time_utc": id_time(orig), "current_item_id_time_utc": id_time(cur) if cur else None,
                     "ad_modify_time_utc": c.get('modify_time'),
                     "orig_lookup": ("found " + lookup_ok[orig]['status']) if orig in lookup_ok else ("not retrievable" if orig in not_fetchable else "not looked up"),
                     "current_lookup": ("found " + lookup_ok[cur]['status']) if cur in lookup_ok else ("not retrievable" if cur in not_fetchable else "not looked up")})
n_changed = sum(1 for s in spark_rows if s['changed'])

# ---- Task 1 ----
out, errs = [], []
for r in inp:
    aid, slot = r['ad_id'], r['slot']
    rec = {"platform": "tiktok", "account_id": ACC, "ad_id": aid, "slot": slot, "url": None,
           "status_now": None, "creative_id_now": None, "found": False, "note": ""}
    notes = []
    if slot == "ad.landing_page_url":
        c = census.get(aid)
        u = urls.get(aid)
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
        if u is None and not deleted:
            errs.append(f"{aid} not in URL pass")
        u = u or {}
        base = u.get('landing_page_url') or None
        pairs = [(p.get('key'), p.get('value')) for p in (u.get('utm_params') or []) if p.get('key') is not None]
        url, mnote = merge(base, pairs)
        rec['url'] = url
        notes.append(f"Manual campaign ad (ad_format {c.get('ad_format')}, identity {c.get('identity_type')}); "
                     f"operation_status {c.get('operation_status')}; delivery status (secondary_status) {st}")
        if deleted:
            notes.append(f"ad is DELETED ({st}); url shown is the last stored value")
        if base is None:
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
        notes.append(f"{READ_CEN}; {READ_URL} (this ad: page {s.get('page')} @ page_size {s.get('page_size')}, request_id {s.get('request_id')})")
        if aid in spark_ids:
            orig = spark_ids[aid]
            cur = c.get('tiktok_item_id')
            rec['tiktok_item_id_now'] = cur
            rec['identity_type_now'] = c.get('identity_type')
            if cur != orig:
                look = ("current post " + (("found via identity/video/info (" + lookup_ok[cur]['status'] + ")") if cur in lookup_ok else "NOT retrievable via identity/video/info"))
                notes.append(f"Spark Push ad written 13-Oct 12:51-13:19 UTC (apply11): tiktok_item_id CHANGED {orig} -> {cur} "
                             f"(new item ID encodes creation {id_time(cur)} UTC; ad modify_time {c.get('modify_time')}); {look}")
            else:
                notes.append(f"Spark Push ad written 13-Oct 12:51-13:19 UTC (apply11): tiktok_item_id unchanged ({cur})")
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
        notes.append(f"{READ_SP} (this ad: page {s.get('page')} @ page_size {s.get('page_size')}, request_id {s.get('request_id')})")
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

out_path = f"{BASE}/reread5/out/tiktok_{ACC}.jsonl"
with open(out_path, "w", encoding="utf-8") as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---- Task 2: ads not in the input, not deleted ----
in_ids = {r['ad_id'] for r in inp}
new = []
for aid, c in sorted(census.items(), key=lambda kv: (kv[1].get('create_time') or '', kv[0])):
    if c.get('campaign_automation_type') != 'MANUAL' or aid in in_ids or c['secondary_status'] in DEL:
        continue
    errs.append(f"new manual ad {aid} needs names/URL (not expected)")
for sid, a in sorted(sp.items(), key=lambda kv: (kv[1].get('create_time') or '', kv[0])):
    if sid in in_ids or a['secondary_status'] in DEL:
        continue
    errs.append(f"new Smart+ ad {sid} needs names/URL (not expected)")
new_path = f"{BASE}/reread5/out/new_tiktok_{ACC}.jsonl"
with open(new_path, "w", encoding="utf-8") as f:
    for rec in new:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---- Spark check outputs ----
spark_path = f"{BASE}/work/spark_check/apply11_spark_check_{ACC}.json"
json.dump(spark_rows, open(spark_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"note": "creation second decoded from the TikTok item IDs (item_id >> 32 = Unix seconds). This is NOT a post lookup; "
                   "identity/video/info and identity/video/get return no create time field, so orig_created/cur_created are null "
                   "in apply11_spark_check.",
           "lookup_request_ids": lookup_rids, "recheck_request_id": recheck_rid, "rows": id_times},
          open(f"{W}/data/spark_item_id_times.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

c1 = collections.Counter()
for rec, r in zip(out, inp):
    c1['url_same' if rec['url'] == r['url_11oct'] else 'url_changed'] += 1
    c1['status_same' if rec['status_now'] == r['status_11oct'] else 'status_changed'] += 1
print("rows", len(out), "found", sum(1 for x in out if x['found']), "not_found", sum(1 for x in out if not x['found']),
      "url_null", sum(1 for x in out if x['url'] is None), dict(c1), "new", len(new))
print("spark: listed", len(spark_rows), "changed", n_changed, "unchanged", len(spark_rows) - n_changed,
      "recheck diffs", recheck_diffs, "lookup items found", len(lookup_ok), "not fetchable", sorted(not_fetchable),
      "create_time field seen in lookups", create_field_seen)
print("errs", errs)
