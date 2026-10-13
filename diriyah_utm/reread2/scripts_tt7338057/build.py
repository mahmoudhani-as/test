# usage: python3 -I build.py
# Builds reread2/out/tiktok_7338057963233443842.jsonl (one line per input row) and
# reread2/out/new_tiktok_7338057963233443842.jsonl from the read-only snapshot in work_tt7338057/snapshot.json.
import json, re
from urllib.parse import unquote, unquote_plus

BASE = "/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm"
ACC = "7338057963233443842"
ACC_NAME = "H&S - DGCL - Visit Diriyah"
inp = json.load(open(f"{BASE}/reread/in/tiktok_{ACC}.json", encoding="utf-8"))
snap = json.load(open(f"{BASE}/reread2/work_tt7338057/snapshot.json", encoding="utf-8"))
man, sp = snap["manual"], snap["smart_plus"]
REF_M, REF_S = set(snap.get("refreshed_manual_ids") or []), set(snap.get("refreshed_smart_ids") or [])
RECHK = "re-checked ~23:09 UTC by id (ads modified since 20:00 UTC): URL, utm_params and status identical to the sweep"
DEL = {"AD_STATUS_DELETE", "AD_STATUS_CAMPAIGN_DELETE", "AD_STATUS_ADGROUP_DELETE"}
READ_MAN = ("read via /v1.3/ad/get/ (filtering primary_status STATUS_ALL + campaign_automation_type MANUAL, "
            "page_size 34, 19 pages, 643 ads incl. deleted) 12-Oct ~23:01-23:04 UTC")
READ_SP = ("read via /v1.3/smart_plus/ad/get/ (filtering primary_status STATUS_ALL, page_size 40, 3 pages, "
           "85 Smart+ ads incl. deleted) 12-Oct ~23:05 UTC")


def query_pairs(url):
    """Raw (undecoded) key/value pairs of the URL query (fragment excluded)."""
    u = url.split('#', 1)[0]
    if '?' not in u:
        return []
    q = u.split('?', 1)[1]
    out = []
    for part in q.split('&'):
        if part == '':
            continue
        k, _, v = part.partition('=')
        out.append((k, v))
    return out


def same(a, b):
    if a == b:
        return True
    for f in (unquote, unquote_plus):
        try:
            if f(a) == f(b):
                return True
        except Exception:
            pass
    return False


def render(base, pairs):
    """Render utm_params into the stored URL: append keys missing from the URL query (before any #fragment),
    keep the URL's value when a key is already there. Returns (url, note)."""
    if not base:
        return None, ("utm_params set but no landing page URL to attach them to" if pairs else None)
    if not pairs:
        return base, "no utm_params stored on the ad (UTMs, if any, are inline in the URL)"
    existing = {}
    for k, v in query_pairs(base):
        existing.setdefault(unquote_plus(k), []).append(v)
    add, conf = [], []
    for p in pairs:
        k, v = p.get('key'), p.get('value')
        if k is None:
            continue
        if k in existing:
            if v is not None and not any(same(v, ev) for ev in existing[k]):
                conf.append(f"{k}: URL has {existing[k][0]!r}, utm_params has {v!r} (URL value kept)")
            continue
        add.append(f"{k}={v}" if v is not None else k)
    if not add:
        url = base
        note = "all utm_params already present in landing page URL"
    else:
        b, frag = (base.split('#', 1) + [None])[:2]
        url = b + ('&' if '?' in b else '?') + '&'.join(add) + (('#' + frag) if frag is not None else '')
        note = "utm_params keys missing from the URL appended: " + ", ".join(add)
    if conf:
        note += "; CONFLICT " + "; ".join(conf)
    return url, note


def cmp_note(url, r, status_now):
    parts = []
    if url == r['url_11oct']:
        parts.append("URL unchanged vs 11-Oct" if url is not None else "still no URL (as on 11-Oct)")
    else:
        parts.append(f"URL CHANGED vs 11-Oct (11-Oct: {r['url_11oct']})")
    if r.get('status_11oct') and status_now and r['status_11oct'] != status_now:
        parts.append(f"status changed since 11-Oct ({r['status_11oct']} -> {status_now})")
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
            rec['note'] = "Ad not returned by /v1.3/ad/get/ with primary_status STATUS_ALL (ad no longer exists / deleted)."
            out.append(rec)
            continue
        st = a['secondary_status']
        rec['status_now'] = st
        base = a.get('landing_page_url') or None
        url, rn = render(base, a.get('utm_params'))
        rec['url'] = url
        deleted = st in DEL
        rec['found'] = not deleted
        notes.append(f"Manual ad (ad_format {a.get('ad_format')}); {READ_MAN}; operation_status {a.get('operation_status')}; "
                     f"delivery status {st}")
        if deleted:
            notes.append(f"ad is DELETED ({st}); url is the last stored value")
        if base is None:
            notes.append("no landing page URL on this ad (landing_page_url empty; landing_page_urls, deeplink and page_id also empty)")
            if a.get('utm_params'):
                notes.append("utm_params set but there is no URL")
        elif rn:
            notes.append(rn)
        notes += cmp_note(url, r, st)
        if aid in REF_M:
            notes.append(RECHK)
        notes.append(f"ad last modified {a.get('modify_time')} UTC; TikTok ads have no separate creative ID")
    elif slot.startswith("smart_plus_ad.landing_page_url_list"):
        a = sp.get(aid)
        if a is None:
            rec['status_now'] = "NOT_FOUND"
            rec['note'] = "Smart+ ad not returned by /v1.3/smart_plus/ad/get/ with primary_status STATUS_ALL (ad no longer exists / deleted)."
            out.append(rec)
            continue
        st = a['secondary_status']
        rec['status_now'] = st
        m = re.match(r"smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url$", slot)
        idx = int(m.group(1)) if m else 0
        lpl = a.get('landing_page_url_list') or []
        pairs = (a.get('ad_configuration') or {}).get('utm_params')
        deleted = st in DEL
        rec['found'] = not deleted
        notes.append(f"Upgraded Smart+ ad (smart_plus_ad_id); {READ_SP}; operation_status {a.get('operation_status')}; "
                     f"delivery status {st}; landing_page_url_list has {len(lpl)} entr{'y' if len(lpl) == 1 else 'ies'}")
        if deleted:
            notes.append(f"ad is DELETED ({st}); url is the last stored value")
        if idx < len(lpl) and (lpl[idx].get('landing_page_url') or None):
            url, rn = render(lpl[idx].get('landing_page_url'), pairs)
            rec['url'] = url
            if not m:
                notes.append("slot recorded without index on 11-Oct; entry [0] reported")
            if pairs:
                notes.append(rn + " (ad_configuration.utm_params)")
            else:
                notes.append("no ad_configuration.utm_params stored (UTMs, if any, are inline in the URL)")
        else:
            notes.append("landing_page_url_list absent/empty in smart_plus/ad/get response (no website destination on this ad)"
                         if not lpl else f"landing_page_url_list[{idx}] not present")
            if pairs:
                notes.append("ad_configuration.utm_params set but no URL")
        notes += cmp_note(rec['url'], r, st)
        if aid in REF_S:
            notes.append(RECHK)
        notes.append(f"ad last modified {a.get('modify_time')} UTC; TikTok ads have no separate creative ID")
    else:
        errs.append(f"unknown slot {slot!r} for {aid}")
        rec['note'] = f"unknown slot {slot!r}"
        out.append(rec)
        continue
    rec['note'] = "; ".join(notes)
    out.append(rec)

out_path = f"{BASE}/reread2/out/tiktok_{ACC}.jsonl"
with open(out_path, "w", encoding="utf-8") as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# Task 2: ads not in the input, not deleted (manual ads + Upgraded Smart+ ads; creative-level
# UPGRADED_SMART_PLUS_CREATIVE rows of ad/get belong to Smart+ ads and are not separate ads).
in_ids = {r['ad_id'] for r in inp}
new = []
for aid, a in sorted(man.items(), key=lambda kv: (kv[1].get('create_time') or '', kv[0])):
    if aid in in_ids or a['secondary_status'] in DEL:
        continue
    url, _ = render(a.get('landing_page_url') or None, a.get('utm_params'))
    new.append({"platform": "tiktok", "account_id": ACC, "account_name": ACC_NAME,
                "campaign_name": a.get('campaign_name'), "adset_name": a.get('adgroup_name'),
                "ad_id": aid, "ad_name": a.get('ad_name'), "effective_status": a['secondary_status'],
                "slot": "ad.landing_page_url", "url": url})
for aid, a in sorted(sp.items(), key=lambda kv: (kv[1].get('create_time') or '', kv[0])):
    if aid in in_ids or a['secondary_status'] in DEL:
        continue
    pairs = (a.get('ad_configuration') or {}).get('utm_params')
    lpl = a.get('landing_page_url_list') or []
    for i, e in enumerate(lpl or [None]):
        url = render((e or {}).get('landing_page_url') or None, pairs)[0] if e else None
        new.append({"platform": "tiktok", "account_id": ACC, "account_name": ACC_NAME,
                    "campaign_name": None, "adset_name": None,  # filled below if any
                    "ad_id": aid, "ad_name": a.get('ad_name'), "effective_status": a['secondary_status'],
                    "slot": f"smart_plus_ad.landing_page_url_list[{i}].landing_page_url" if e else "smart_plus_ad.landing_page_url_list",
                    "url": url, "_campaign_id": a.get('campaign_id'), "_adgroup_id": a.get('adgroup_id')})
new_path = f"{BASE}/reread2/out/new_tiktok_{ACC}.jsonl"
with open(new_path, "w", encoding="utf-8") as f:
    for rec in new:
        f.write(json.dumps({k: v for k, v in rec.items() if not k.startswith('_')}, ensure_ascii=False) + "\n")

print("rows", len(out), "found", sum(1 for x in out if x['found']), "not_found", sum(1 for x in out if not x['found']),
      "new", len(new), "errs", errs)
