import json
import re
import sys
from urllib.parse import urlsplit, parse_qsl

W = sys.argv[1]
IN = sys.argv[2]
OUT = sys.argv[3]
NEW = sys.argv[4]

ACC = "623ccdb3-d546-42e8-9082-89ff8b59cfd1"

inp = json.load(open(IN))
ads = json.load(open(W + "ads_transcribed.json"))
cr = {c["creative"]["id"]: c["creative"]
      for c in json.load(open(W + "creatives_raw.txt"))["data"]["data"]["creatives"]}
amap = {a["id"]: a for a in ads}

# delivery_status is an unordered set; order it with the convention seen in the 11-Oct pull
ORDER = ["INVALID_NOT_EFFECTIVE_ACTIVE", "INVALID_NO_CREATIVE_EFFECTIVE_ACTIVE", "INVALID_NOT_ACTIVE",
         "INVALID_NOT_APPROVED_REVIEW_STATUS", "INVALID_EFFECTIVE_INVALID"]


def canon_status(ds):
    known = [s for s in ORDER if s in ds]
    extra = [s for s in ds if s not in ORDER]
    return ",".join(known + extra)


REASONS = {
    "SOCIAL": "Your ad contains a link to a social platform (X/Twitter etc. prohibited)",
    "NOT_FOUND": "Web View destination page not found / has an error / not publicly displaying intended content",
}


def url_diff(old, new):
    if old == new:
        return "URL unchanged vs 11-Oct"
    if old is None:
        return "URL now present (was null on 11-Oct)"
    if new is None:
        return "URL now missing (was %s on 11-Oct)" % old
    if new.startswith(old):
        added = new[len(old):]
        return "URL changed vs 11-Oct: base unchanged, appended '%s'" % added
    o, n = urlsplit(old), urlsplit(new)
    if (o.scheme, o.netloc, o.path) == (n.scheme, n.netloc, n.path):
        oq, nq = dict(parse_qsl(o.query, keep_blank_values=True)), dict(parse_qsl(n.query, keep_blank_values=True))
        added = {k: v for k, v in nq.items() if k not in oq}
        changed = {k: (oq[k], nq[k]) for k in nq if k in oq and oq[k] != nq[k]}
        removed = [k for k in oq if k not in nq]
        return "URL changed vs 11-Oct (same base): added=%s changed=%s removed=%s" % (added, changed, removed)
    return "URL changed vs 11-Oct: base URL differs (was %s)" % old


def utm_check(u):
    if not u:
        return None
    q = parse_qsl(urlsplit(u).query, keep_blank_values=True)
    keys = [k for k, _ in q]
    utm = [k for k in keys if k.lower().startswith("utm_")]
    if not utm:
        return "no UTM params on current URL"
    missing = [k for k in ("utm_source", "utm_medium", "utm_campaign") if k not in keys]
    dup = sorted({k for k in utm if keys.count(k) > 1})
    msg = "UTM keys present: %s" % ",".join(utm)
    if missing:
        msg += "; WARNING missing %s" % ",".join(missing)
    if dup:
        msg += "; WARNING duplicated %s" % ",".join(dup)
    return msg


def has_any_url(c):
    """Return list of URL-bearing values on a creative (non-composite)."""
    found = []
    wv = c.get("web_view_properties") or {}
    if wv.get("url"):
        found.append(("web_view_properties.url", wv["url"]))
    for dl in wv.get("deep_link_urls") or []:
        found.append(("web_view_properties.deep_link_urls", dl))
    for k, v in c.items():
        if k.endswith("_properties") and k not in ("web_view_properties", "profile_properties",
                                                    "composite_properties", "preview_properties"):
            if v:
                found.append((k, json.dumps(v)))
    return found


COMP_RE = re.compile(r"^composite_properties\.creative_ids\[(\d+)\]\(([0-9a-f-]{36})\)\.web_view_properties\.url$")

out_rows = []
for r in inp:
    ad_id = r["ad_id"]
    slot = r["slot"]
    a = amap.get(ad_id)
    row = {"platform": "snapchat", "account_id": ACC, "ad_id": ad_id, "slot": slot}
    if a is None:
        row.update({"url": None, "status_now": None, "creative_id_now": None, "found": False,
                    "note": "ad no longer returned by GET /adaccounts/{id}/ads - deleted"})
        out_rows.append(row)
        continue
    cid = a["creative_id"]
    c = cr.get(cid)
    status_now = canon_status(a["delivery_status"])
    notes = ["ad.status=%s" % a["status"], "ad.review_status=%s" % a["review_status"]]
    if a.get("reason"):
        notes.append("ad rejection: %s" % REASONS[a["reason"]])
    if c is not None:
        notes.append("creative.type=%s" % c["type"])
        notes.append("creative.review_status=%s" % c.get("review_status"))
    if cid != r["creative_id"]:
        notes.append("AD CREATIVE CHANGED since 11-Oct (was %s)" % r["creative_id"])
    old_set = set((r["status_11oct"] or "").split(",")) - {""}
    if old_set == set(a["delivery_status"]):
        notes.append("delivery_status unchanged vs 11-Oct")
    else:
        notes.append("delivery_status changed vs 11-Oct (was %s)" % r["status_11oct"])
    url = None
    found = True
    if c is None:
        found = False
        notes.append("creative %s not found in account creatives list" % cid)
    elif slot == "web_view_properties.url":
        wv = c.get("web_view_properties")
        if wv is None:
            notes.append("current creative has no web_view_properties")
        else:
            url = wv.get("url")
            if c.get("updated_at"):
                notes.append("creative.updated_at=%s" % c["updated_at"])
            shared = sorted(x["id"] for x in ads if x["creative_id"] == cid)
            if len(shared) > 1:
                notes.append("creative shared by %d ads in this account" % len(shared))
            if c.get("utm_autofix_permission"):
                notes.append("utm_autofix_permission=%s" % c["utm_autofix_permission"])
        notes.append(url_diff(r["url_11oct"], url))
    elif slot and COMP_RE.match(slot):
        idx, sub_old = COMP_RE.match(slot).groups()
        idx = int(idx)
        subs = (c.get("composite_properties") or {}).get("creative_ids") or []
        if idx >= len(subs):
            notes.append("composite no longer has a sub-creative at index %d" % idx)
        else:
            sub_now = subs[idx]
            if sub_now != sub_old:
                notes.append("SUB-CREATIVE AT INDEX %d CHANGED: was %s now %s" % (idx, sub_old, sub_now))
            sc = cr.get(sub_now)
            if sc is None:
                found = False
                notes.append("sub-creative %s not found in account creatives list" % sub_now)
            else:
                url = (sc.get("web_view_properties") or {}).get("url")
                notes.append("URL read from sub-creative %s (type=%s, review_status=%s, updated_at=%s)" % (
                    sub_now, sc["type"], sc.get("review_status"), sc.get("updated_at")))
        notes.append(url_diff(r["url_11oct"], url))
    elif slot is None:
        # no URL slot on 11-Oct; confirm still none
        extra = []
        if c["type"] == "COMPOSITE":
            subs = (c.get("composite_properties") or {}).get("creative_ids") or []
            for s in subs:
                sc = cr.get(s)
                if sc is None:
                    extra.append(("sub %s missing" % s, None))
                else:
                    extra += [("sub %s %s" % (s, k), v) for k, v in has_any_url(sc)]
            notes.append("composite sub-creative(s) %s" % ",".join(subs))
        else:
            extra = has_any_url(c)
        if extra:
            notes.append("NOTE: creative now carries URL(s) %s although slot was null on 11-Oct" % extra)
        else:
            notes.append("still no attachment URL (no web_view/deep_link/collection) - url null as on 11-Oct")
    else:
        notes.append("unrecognised slot format")
    uc = utm_check(url)
    if uc:
        notes.append(uc)
    row.update({"url": url, "status_now": status_now, "creative_id_now": cid, "found": found,
                "note": "; ".join(notes)})
    out_rows.append(row)

with open(OUT, "w") as f:
    for row in out_rows:
        f.write(json.dumps({k: row[k] for k in ["platform", "account_id", "ad_id", "slot", "url", "status_now",
                                                "creative_id_now", "found", "note"]}, ensure_ascii=False) + "\n")

# Task 2: ads not in input
in_ids = {r["ad_id"] for r in inp}
new_ads = [a for a in ads if a["id"] not in in_ids]
with open(NEW, "w") as f:
    for a in new_ads:
        f.write(json.dumps({"ad_id": a["id"], "TODO": True}) + "\n")
print("rows", len(out_rows), "new_ads", len(new_ads))
