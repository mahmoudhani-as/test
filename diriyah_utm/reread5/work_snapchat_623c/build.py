import json, re, sys
from urllib.parse import urlsplit, parse_qsl

WORK = sys.argv[1]
INP = sys.argv[2]
OUT = sys.argv[3]
NEW = sys.argv[4]

ACCOUNT_ID = "623ccdb3-d546-42e8-9082-89ff8b59cfd1"
ACCOUNT_NAME = "Diriyah Gate - Billed to MS KSA"
READ_NOTE = ("read 2026-10-13 ~14:15-14:30Z via GET /v1/adaccounts/{id}/ads + /creatives + /adsquads + /campaigns "
             "(aggregate_pages; each returned one complete page, no paging.next_link; re-checked with limit=50: 39 ads, 47 creatives)")

inp = json.load(open(INP))
raw = json.load(open(WORK + "/creatives_raw.txt"))
cr = {x["creative"]["id"]: x["creative"] for x in raw["data"]["data"]["creatives"]}
T = json.load(open(WORK + "/ads_transcribed.json"))
ads = {a["id"]: a for a in T["ads"]}
sq = {s["id"]: s for s in T["adsquads"]}
cp = {c["id"]: c for c in T["campaigns"]}

ORDER = ["INVALID_NOT_EFFECTIVE_ACTIVE", "INVALID_NO_CREATIVE_EFFECTIVE_ACTIVE", "INVALID_NOT_ACTIVE",
         "INVALID_NOT_APPROVED_REVIEW_STATUS", "INVALID_EFFECTIVE_INVALID"]


def fmt_status(ds):
    known = [s for s in ORDER if s in ds]
    other = sorted(s for s in ds if s not in ORDER)
    # keep INVALID_EFFECTIVE_INVALID last, unknown codes before it
    if "INVALID_EFFECTIVE_INVALID" in known:
        known.remove("INVALID_EFFECTIVE_INVALID")
        return ",".join(known + other + ["INVALID_EFFECTIVE_INVALID"])
    return ",".join(known + other)


# ads sharing a creative (direct or as composite sub-creative)
users = {}
for a in T["ads"]:
    users.setdefault(a["creative_id"], []).append(a["id"])
    c = cr.get(a["creative_id"]) or {}
    for sub in (c.get("composite_properties") or {}).get("creative_ids") or []:
        users.setdefault(sub, []).append(a["id"])


def utm_summary(url):
    if not url:
        return "no URL"
    q = parse_qsl(urlsplit(url).query, keep_blank_values=True)
    utm = [(k, v) for k, v in q if k.lower().startswith("utm_")]
    if not utm:
        return "no UTM params in URL"
    s = "UTMs in URL: " + ", ".join(f"{k}={v}" for k, v in utm)
    keys = {k.lower() for k, _ in utm}
    missing = [k for k in ("utm_source", "utm_medium", "utm_campaign") if k not in keys]
    if missing:
        s += " (missing " + ", ".join(missing) + ")"
    return s


SLOT_COMPOSITE = re.compile(r"^composite_properties\.creative_ids\[(\d+)\]\(([0-9a-f-]{36})\)\.web_view_properties\.url$")

rows = []
problems = []
for r in inp:
    ad_id = r["ad_id"]
    slot = r["slot"]
    a = ads.get(ad_id)
    rec = {"platform": "snapchat", "account_id": ACCOUNT_ID, "ad_id": ad_id, "slot": slot}
    if a is None:
        rec.update({"url": None, "status_now": "DELETED/NOT_FOUND", "creative_id_now": None, "found": False,
                    "note": "ad no longer returned by GET /v1/adaccounts/{id}/ads (deleted); " + READ_NOTE})
        rows.append(rec)
        continue
    c = cr.get(a["creative_id"])
    s = sq.get(a["ad_squad_id"])
    k = cp.get(s["campaign_id"]) if s else None
    notes = []
    url = None
    found = True
    if slot is None:
        url = None
        # confirm there is still no URL anywhere in the creative chain
        chain = [a["creative_id"]] + list(((c or {}).get("composite_properties") or {}).get("creative_ids") or [])
        urls_now = [(cid, (cr.get(cid) or {}).get("web_view_properties", {}).get("url")) for cid in chain]
        urls_now = [(cid, u) for cid, u in urls_now if u]
        if urls_now:
            notes.append("NOTE: 11-Oct had no URL slot but a URL now exists: " +
                         "; ".join(f"{cid}: {u}" for cid, u in urls_now))
            problems.append((ad_id, "url appeared"))
        else:
            if c and c.get("type") == "COMPOSITE":
                subs = (c.get("composite_properties") or {}).get("creative_ids") or []
                desc = ", ".join(f"{sid} ({(cr.get(sid) or {}).get('type')}, review_status={(cr.get(sid) or {}).get('review_status')})" for sid in subs)
                notes.append(f"no landing-URL slot (as on 11-Oct): composite creative {a['creative_id']} -> sub-creative(s) {desc} with no web_view/deep_link/collection attachment")
            else:
                notes.append(f"no landing-URL slot (as on 11-Oct): creative {a['creative_id']} type={(c or {}).get('type')} has no web_view/deep_link/collection attachment")
    elif slot == "web_view_properties.url":
        if c is None:
            found = False
            notes.append(f"creative {a['creative_id']} not returned by /creatives")
        else:
            url = (c.get("web_view_properties") or {}).get("url")
            if url is None:
                notes.append(f"creative {a['creative_id']} (type={c.get('type')}) has no web_view_properties.url now")
                problems.append((ad_id, "no url now"))
    else:
        m = SLOT_COMPOSITE.match(slot)
        if not m:
            problems.append((ad_id, "unparsed slot " + slot))
            notes.append("unparsed slot")
        else:
            idx, sub_old = int(m.group(1)), m.group(2)
            subs = ((c or {}).get("composite_properties") or {}).get("creative_ids") or []
            sub_now = subs[idx] if idx < len(subs) else None
            if sub_now is None:
                notes.append(f"composite creative {a['creative_id']} has no creative_ids[{idx}] now")
                problems.append((ad_id, "composite position missing"))
            else:
                if sub_now != sub_old:
                    notes.append(f"composite creative_ids[{idx}] changed: 11-Oct {sub_old} -> now {sub_now}; URL read from current sub-creative")
                    problems.append((ad_id, "sub-creative changed"))
                else:
                    notes.append(f"URL read from composite sub-creative {sub_now} (composite {a['creative_id']} creative_ids[{idx}] unchanged)")
                sc = cr.get(sub_now)
                if sc is None:
                    notes.append(f"sub-creative {sub_now} not returned by /creatives")
                    problems.append((ad_id, "sub missing"))
                else:
                    url = (sc.get("web_view_properties") or {}).get("url")
                    notes.append(f"sub-creative type={sc.get('type')} review_status={sc.get('review_status')} cta={sc.get('call_to_action')} updated_at={sc.get('updated_at')}")

    # URL comparison
    old = r["url_11oct"]
    if slot is not None:
        if url == old:
            notes.insert(0, "URL unchanged vs 11-Oct")
        elif old and url and url.startswith(old) and url[len(old):len(old) + 1] in ("?", "&"):
            notes.insert(0, f"URL changed vs 11-Oct: UTM params appended to the 11-Oct URL (11-Oct: {old})")
        else:
            notes.insert(0, f"URL changed vs 11-Oct (11-Oct: {old})")
        notes.insert(1, utm_summary(url) + "; UTMs live inside web_view_properties.url (Snapchat has no separate url_tags field)")

    # creative id
    if a["creative_id"] == r["creative_id"]:
        notes.append("creative_id unchanged vs 11-Oct")
    else:
        notes.append(f"creative_id changed vs 11-Oct (11-Oct: {r['creative_id']})")

    # status
    status_now = fmt_status(a["delivery_status"])
    old_set = set((r["status_11oct"] or "").split(",")) - {""}
    if old_set == set(a["delivery_status"]):
        notes.append("delivery_status unchanged vs 11-Oct")
    else:
        notes.append(f"delivery_status changed vs 11-Oct (11-Oct: {r['status_11oct']})")
    ad_bits = f"ad.status={a['status']}; ad.review_status={a['review_status']}"
    if a.get("review_status_reasons"):
        reason = " | ".join(a["review_status_reasons"])
        ad_bits += "; rejection: " + (reason[:160] + ("..." if len(reason) > 160 else ""))
    ad_bits += f"; ad.type={a['type']}; ad.updated_at={a['updated_at']}"
    notes.append(ad_bits)
    if c:
        cb = f"creative {a['creative_id']} type={c.get('type')} review_status={c.get('review_status')} updated_at={c.get('updated_at')}"
        if c.get("call_to_action"):
            cb += f" cta={c.get('call_to_action')}"
        if c.get("utm_autofix_permission"):
            cb += f" utm_autofix_permission={c.get('utm_autofix_permission')}"
        notes.append(cb)
    sharers = [x for x in users.get(a["creative_id"], []) if x != ad_id]
    if sharers:
        notes.append(f"creative shared with ad(s) {', '.join(sharers)} - editing it changes all of them")
    if s:
        notes.append(f"adsquad '{s['name']}' status={s['status']} end_time={s['end_time']}")
    if k:
        notes.append(f"campaign '{k['name']}' status={k['status']} (campaign delivery: {','.join(k['delivery_status'])})")
    notes.append(READ_NOTE)
    rec.update({"url": url, "status_now": status_now, "creative_id_now": a["creative_id"], "found": found,
                "note": "; ".join(notes)})
    rows.append(rec)

with open(OUT, "w") as f:
    for rec in rows:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# Task 2: ads not in input
in_ids = {r["ad_id"] for r in inp}
new_rows = []
for a in T["ads"]:
    if a["id"] in in_ids:
        continue
    c = cr.get(a["creative_id"]) or {}
    s = sq.get(a["ad_squad_id"]) or {}
    k = cp.get(s.get("campaign_id")) or {}
    slots = []
    if (c.get("web_view_properties") or {}).get("url"):
        slots.append(("web_view_properties.url", c["web_view_properties"]["url"]))
    for i, sid in enumerate((c.get("composite_properties") or {}).get("creative_ids") or []):
        u = ((cr.get(sid) or {}).get("web_view_properties") or {}).get("url")
        if u:
            slots.append((f"composite_properties.creative_ids[{i}]({sid}).web_view_properties.url", u))
    if not slots:
        slots.append((None, None))
    for sl, u in slots:
        new_rows.append({"platform": "snapchat", "account_id": ACCOUNT_ID, "account_name": ACCOUNT_NAME,
                         "campaign_name": k.get("name"), "adset_name": s.get("name"), "ad_id": a["id"],
                         "ad_name": a["name"], "effective_status": fmt_status(a["delivery_status"]),
                         "slot": sl, "url": u})
with open(NEW, "w") as f:
    for rec in new_rows:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print("rows", len(rows), "new_rows", len(new_rows), "problems", problems)
