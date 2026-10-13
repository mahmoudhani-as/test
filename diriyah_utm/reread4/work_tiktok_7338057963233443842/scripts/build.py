# usage: python3 -I build.py
# Builds reread4/out/tiktok_7338057963233443842.jsonl (one line per input row, same order, ad_id/slot copied exactly)
# and reread4/out/new_tiktok_7338057963233443842.jsonl (ads not in the input, not deleted) from the read-only
# snapshot in reread4/work_tiktok_7338057963233443842/data/snapshot.json.
# utm_params are rendered into the stored URL with the same rule used for the 11-Oct values (live/tt_7338/build_final.py):
# a utm_params key=value is appended (before any #fragment) only when that key is absent from the URL query; when the key
# is present with a different value the URL value is kept and the conflict is noted.
import json, re, collections
from urllib.parse import urlsplit, parse_qsl

BASE = "/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm"
ACC = "7338057963233443842"
ACC_NAME = "H&S - DGCL - Visit Diriyah"
W = f"{BASE}/reread4/work_tiktok_{ACC}"
inp = json.load(open(f"{BASE}/reread/in/tiktok_{ACC}.json", encoding="utf-8"))
snap = json.load(open(f"{W}/data/snapshot.json", encoding="utf-8"))
man, sp = snap["manual"], snap["smart_plus"]
refreshed_m = snap.get("refreshed_manual", {})
DEL = {"AD_STATUS_DELETE", "AD_STATUS_CAMPAIGN_DELETE", "AD_STATUS_ADGROUP_DELETE"}
NM, NS = len(man), len(sp)
READ_MAN = (f"read 13-Oct 12:09-12:11 UTC via /v1.3/ad/get/ (filtering primary_status STATUS_ALL + campaign_automation_type MANUAL, "
            f"page_size 40 because 100 full rows exceed the ~65KB MCP cap, 17 of 17 pages, {NM} manual ads incl. deleted; "
            "account census ad/get STATUS_ALL page_size 100 = 792 rows = 643 MANUAL + 149 UPGRADED_SMART_PLUS creative rows, 0 SMART_PLUS; "
            "re-checked 12:15 UTC with ad/get STATUS_ALL page_size 100, 8 of 8 pages: modify_time and delivery status unchanged for every ad)")
READ_SP = (f"read 13-Oct 12:10-12:11 UTC via /v1.3/smart_plus/ad/get/ (filtering primary_status STATUS_ALL, page_size 40, 3 of 3 pages, "
           f"{NS} Upgraded Smart+ ads incl. deleted; re-checked 12:15 UTC with smart_plus/ad/get page_size 100: modify_time and "
           "delivery status unchanged for every ad)")


def merge(base, pairs):
    """Return (url, note) merging utm (key, value) pairs into base without duplicating params already in the URL."""
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
    notes = []
    url = base
    if add:
        url = b0 + ('&' if '?' in b0 else '?') + '&'.join(add) + (sep0 + frag0)
        notes.append("utm_params not present in stored landing page URL were appended: " + ", ".join(add))
    if conflicts:
        notes.append("utm_params value differs from value already in stored URL (stored URL value kept): " + "; ".join(conflicts))
    if not add and not conflicts:
        notes.append("all utm_params already present in stored landing page URL (no change on merge)")
    return url, "; ".join(notes)


def qdiff(old, new):
    """Short description of what differs between two URLs (base and query params)."""
    if old is None or new is None:
        return ""
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


out, errs = [], []
for r in inp:
    aid, slot = r['ad_id'], r['slot']
    rec = {"platform": "tiktok", "account_id": ACC, "ad_id": aid, "slot": slot, "url": None,
           "status_now": None, "creative_id_now": None, "found": False, "note": ""}
    notes = []
    if slot == "ad.landing_page_url":
        a = man.get(aid)
        if a is None:
            rec['status_now'] = "NOT_FOUND"
            rec['note'] = (f"Ad not returned by /v1.3/ad/get/ with primary_status STATUS_ALL (all {NM} manual ads read 13-Oct 12:09-12:11 UTC): "
                           "the ad no longer exists (deleted).")
            out.append(rec)
            continue
        st = a['secondary_status']
        rec['status_now'] = st
        base = a.get('landing_page_url') or None
        pairs = [(p.get('key'), p.get('value')) for p in (a.get('utm_params') or []) if p.get('key') is not None]
        url, mnote = merge(base, pairs)
        rec['url'] = url
        deleted = st in DEL
        rec['found'] = not deleted
        notes.append(f"Manual ad (ad_format {a.get('ad_format')}); operation_status {a.get('operation_status')}; delivery status {st}")
        if deleted:
            notes.append(f"ad is DELETED ({st}); url shown is the last stored value")
        if base is None:
            extra = []
            if a.get('landing_page_urls'):
                extra.append(f"landing_page_urls {a.get('landing_page_urls')}")
            if a.get('deeplink'):
                extra.append(f"deeplink {a.get('deeplink')}")
            if a.get('page_id'):
                extra.append(f"page_id {a.get('page_id')}")
            notes.append("no landing page URL on this ad (landing_page_url empty" +
                         ("; " + "; ".join(extra) if extra else "; landing_page_urls, deeplink and page_id also empty") + ")")
            if pairs:
                notes.append("utm_params set but landing_page_url empty, so no final URL")
        elif mnote:
            notes.append(mnote)
        notes += cmp_notes(url, r, st)
        notes.append(f"ad last modified {a.get('modify_time')} UTC")
        if aid in refreshed_m:
            notes.append("re-read 12:11 UTC by ad_ids (modified 12:01:53 UTC, just before this read): same values")
        notes.append(READ_MAN)
        notes.append("TikTok ads have no separate creative ID (creative_id_now null, as on 11-Oct)")
    elif slot.startswith("smart_plus_ad.landing_page_url_list"):
        a = sp.get(aid)
        if a is None:
            rec['status_now'] = "NOT_FOUND"
            rec['note'] = (f"Upgraded Smart+ ad not returned by /v1.3/smart_plus/ad/get/ with primary_status STATUS_ALL "
                           f"(all {NS} Smart+ ads read 13-Oct 12:10-12:11 UTC): the ad no longer exists (deleted).")
            out.append(rec)
            continue
        st = a['secondary_status']
        rec['status_now'] = st
        m = re.match(r"smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url$", slot)
        idx = int(m.group(1)) if m else 0
        lpl = a.get('landing_page_url_list') or []
        pairs = [(p.get('key'), p.get('value')) for p in ((a.get('ad_configuration') or {}).get('utm_params') or []) if p.get('key') is not None]
        deleted = st in DEL
        rec['found'] = not deleted
        notes.append(f"Upgraded Smart+ ad (smart_plus_ad_id); operation_status {a.get('operation_status')}; delivery status {st}; "
                     f"landing_page_url_list has {len(lpl)} entr{'y' if len(lpl) == 1 else 'ies'}")
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
        notes += cmp_notes(rec['url'], r, st)
        notes.append(f"ad last modified {a.get('modify_time')} UTC")
        notes.append(READ_SP)
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

out_path = f"{BASE}/reread4/out/tiktok_{ACC}.jsonl"
with open(out_path, "w", encoding="utf-8") as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# Task 2: ads not in the input and not deleted (manual ads from ad/get + Upgraded Smart+ ads from smart_plus/ad/get;
# the 149 UPGRADED_SMART_PLUS_CREATIVE rows of ad/get are creative-level rows of Smart+ ads, not separate ads).
in_ids = {r['ad_id'] for r in inp}
new = []
for aid, a in sorted(man.items(), key=lambda kv: (kv[1].get('create_time') or '', kv[0])):
    if aid in in_ids or a['secondary_status'] in DEL:
        continue
    pairs = [(p.get('key'), p.get('value')) for p in (a.get('utm_params') or []) if p.get('key') is not None]
    url, _ = merge(a.get('landing_page_url') or None, pairs)
    new.append({"platform": "tiktok", "account_id": ACC, "account_name": ACC_NAME,
                "campaign_name": a.get('campaign_name'), "adset_name": a.get('adgroup_name'),
                "ad_id": aid, "ad_name": a.get('ad_name'), "effective_status": a['secondary_status'],
                "slot": "ad.landing_page_url", "url": url})
new_sp = []
for aid, a in sorted(sp.items(), key=lambda kv: (kv[1].get('create_time') or '', kv[0])):
    if aid in in_ids or a['secondary_status'] in DEL:
        continue
    new_sp.append(aid)
    pairs = [(p.get('key'), p.get('value')) for p in ((a.get('ad_configuration') or {}).get('utm_params') or []) if p.get('key') is not None]
    lpl = a.get('landing_page_url_list') or []
    for i, e in enumerate(lpl or [None]):
        url = merge((e or {}).get('landing_page_url') or None, pairs)[0] if e else None
        new.append({"platform": "tiktok", "account_id": ACC, "account_name": ACC_NAME,
                    "campaign_name": None, "adset_name": None,
                    "ad_id": aid, "ad_name": a.get('ad_name'), "effective_status": a['secondary_status'],
                    "slot": f"smart_plus_ad.landing_page_url_list[{i}].landing_page_url" if e else "smart_plus_ad.landing_page_url_list",
                    "url": url})
if new_sp:
    errs.append(f"new Smart+ ads need campaign/adgroup names filled: {new_sp}")
new_path = f"{BASE}/reread4/out/new_tiktok_{ACC}.jsonl"
with open(new_path, "w", encoding="utf-8") as f:
    for rec in new:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

c = collections.Counter()
for rec, r in zip(out, inp):
    c['url_same' if rec['url'] == r['url_11oct'] else 'url_changed'] += 1
    c['status_same' if rec['status_now'] == r['status_11oct'] else 'status_changed'] += 1
print("rows", len(out), "found", sum(1 for x in out if x['found']), "not_found", sum(1 for x in out if not x['found']),
      "url_null", sum(1 for x in out if x['url'] is None), dict(c), "new", len(new), "errs", errs)
