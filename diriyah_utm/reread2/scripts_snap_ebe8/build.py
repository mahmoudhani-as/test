# usage: python3 -I build.py <work_dir> <input_json> <out_jsonl> <new_jsonl>
import json, re, sys
from collections import defaultdict

W, IN, OUT, NEW = sys.argv[1:5]
ACC = "ebe8d66e-0e3e-4b71-9d37-5c53118d6481"
ACC_NAME = "Diriyah Company"
READ_NOTE = ("read 2026-10-12 22:44-22:48Z via GET /v1/adaccounts/{id}/ads, /creatives (all pages), /adsquads, /campaigns; "
             "after both Snapchat apply7 runs had completed")

ads = {a["id"]: a for a in json.load(open(W + "/ads.json"))}
crs = {c["id"]: c for c in json.load(open(W + "/creatives.json"))}
par = json.load(open(W + "/parents.json"))
sqs, cps = par["adsquads"], par["campaigns"]
rows = json.load(open(IN))

# Fresher read (POST get_ads_by_ids / get_creatives_by_ids, read-only) of the entities that were in review during the list read.
# URLs and composite lists were checked equal to the list read; only review/delivery status moved on.
refreshed_ads, refreshed_crs = {}, set()
try:
    ref = json.load(open(W + "/refresh.json"))
except FileNotFoundError:
    ref = {"ads": {}, "creatives": {}}
for aid, v in ref["ads"].items():
    a = ads[aid]
    assert a["creative_id"] == v["creative_id"]
    refreshed_ads[aid] = "|".join(a["delivery_status"])
    a.update({k: v[k] for k in ("status", "review_status", "delivery_status", "updated_at")})
for cid, v in ref["creatives"].items():
    c = crs[cid]
    if "url" in v:
        assert c["web_view_properties"]["url"] == v["url"]
    if "creative_ids" in v:
        assert c["composite_properties"]["creative_ids"] == v["creative_ids"]
    if (c["review_status"], c["updated_at"]) != (v["review_status"], v["updated_at"]):
        refreshed_crs.add(cid)
    c["review_status"], c["updated_at"] = v["review_status"], v["updated_at"]
REFRESH_NOTE = "status re-read %s via POST get_ads_by_ids/get_creatives_by_ids (read-only) after Snapchat review completed" % ref.get("read_at", "")

# which ads use each creative (directly, or as a sub-creative of their composite)
users = defaultdict(set)
for a in ads.values():
    users[a["creative_id"]].add(a["id"])
    c = crs.get(a["creative_id"]) or {}
    for s in (c.get("composite_properties") or {}).get("creative_ids") or []:
        users[s].add(a["id"])

SLOT_RE = re.compile(r"^creative\.composite_properties\.creative_ids\[(\d+)\] \(([0-9a-f-]{36})\)\.web_view_properties\.url$")


def norm_status(now_list, old_str):
    """Join delivery_status with '|'. Snapchat returns the list in arbitrary order, so keep the 11-Oct order
    for values present then, and append new ones in API order."""
    old = old_str.split("|") if old_str else []
    def key(s):
        return (0, old.index(s)) if s in old else (1, now_list.index(s))
    return "|".join(sorted(now_list, key=key))


def cr_desc(c):
    parts = ["type=%s" % c["type"], "review_status=%s" % c.get("review_status"), "updated_at=%s" % c.get("updated_at")]
    if c.get("utm_autofix_permission"):
        parts.append("utm_autofix_permission=%s" % c["utm_autofix_permission"])
    return ", ".join(parts)


out = []
for r in rows:
    ad_id, slot = r["ad_id"], r["slot"]
    rec = {"platform": "snapchat", "account_id": ACC, "ad_id": ad_id, "slot": slot,
           "url": None, "status_now": None, "creative_id_now": None, "found": False, "note": ""}
    a = ads.get(ad_id)
    if a is None:
        rec["status_now"] = "DELETED"
        rec["note"] = "ad not returned by GET /v1/adaccounts/{id}/ads (deleted); " + READ_NOTE
        out.append(rec)
        continue
    notes = []
    rec["status_now"] = norm_status(a["delivery_status"], r["status_11oct"])
    rec["creative_id_now"] = a["creative_id"]
    rec["found"] = True
    sq = sqs.get(a["ad_squad_id"], {})
    cp = cps.get(sq.get("campaign_id"), {})
    notes.append("ad.status=%s; ad.review_status=%s; ad.type=%s; adsquad.status=%s; campaign.status=%s" % (
        a["status"], a.get("review_status"), a.get("type"), sq.get("status"), cp.get("status")))
    if a.get("review_status_reasons"):
        notes.append("ad.review_status_reasons: " + " / ".join(a["review_status_reasons"]))
    if set(a["delivery_status"]) == set((r["status_11oct"] or "").split("|")):
        notes.append("delivery_status unchanged vs 11-Oct")
    else:
        notes.append("delivery_status CHANGED vs 11-Oct (was %s)" % r["status_11oct"])
    if ad_id in refreshed_ads:
        notes.append("ad %s (list read at 22:44Z showed delivery_status=%s)" % (REFRESH_NOTE, refreshed_ads[ad_id]))
    if a["creative_id"] != r["creative_id"]:
        notes.append("ad creative CHANGED vs 11-Oct (was %s)" % r["creative_id"])
    c = crs.get(a["creative_id"])
    if c is None:
        rec["found"] = False
        notes.append("ad creative %s not returned by GET /v1/adaccounts/{id}/creatives (deleted)" % a["creative_id"])
        notes.append(READ_NOTE)
        rec["note"] = "; ".join(notes)
        out.append(rec)
        continue
    url_holder = None
    if slot == "creative.web_view_properties.url":
        if c["type"] != "WEB_VIEW" or "web_view_properties" not in c:
            notes.append("creative %s is now type %s with no web_view_properties; slot not present" % (c["id"], c["type"]))
        else:
            rec["url"] = c["web_view_properties"].get("url")
            url_holder = c["id"]
            notes.append("creative " + cr_desc(c))
    else:
        m = SLOT_RE.match(slot)
        if not m:
            notes.append("UNPARSED SLOT")
        else:
            idx, sub_old = int(m.group(1)), m.group(2)
            kids = (c.get("composite_properties") or {}).get("creative_ids") or []
            if c["type"] != "COMPOSITE" or idx >= len(kids):
                rec["found"] = False
                notes.append("creative %s is type %s with %d sub-creatives; slot position creative_ids[%d] no longer exists" % (
                    c["id"], c["type"], len(kids), idx))
            else:
                sub = kids[idx]
                if sub != sub_old:
                    notes.append("sub-creative at creative_ids[%d] CHANGED vs 11-Oct (was %s, now %s)" % (idx, sub_old, sub))
                sc = crs.get(sub)
                if sc is None:
                    rec["found"] = False
                    notes.append("sub-creative %s not returned by GET /v1/adaccounts/{id}/creatives (deleted)" % sub)
                else:
                    rec["url"] = (sc.get("web_view_properties") or {}).get("url")
                    url_holder = sub
                    notes.append("composite creative %s (review_status=%s, updated_at=%s, %d sub-creatives); URL read from sub-creative %s at creative_ids[%d] (%s)" % (
                        c["id"], c.get("review_status"), c.get("updated_at"), len(kids), sub, idx, cr_desc(sc)))
                    if rec["url"] is None:
                        notes.append("sub-creative has no web_view_properties.url")
    touched = sorted({x for x in (c["id"], url_holder) if x and x in refreshed_crs})
    if touched:
        notes.append("creative review status for %s from the %s (URL unchanged vs list read)" % (", ".join(touched), REFRESH_NOTE.replace("status re-read ", "re-read ")))
    if url_holder:
        n_users = len(users[url_holder])
        if n_users > 1:
            notes.append("URL-holding creative %s is used by %d ads in this account" % (url_holder, n_users))
    if rec["found"]:
        if rec["url"] == r["url_11oct"]:
            notes.append("URL unchanged vs 11-Oct")
        else:
            notes.append("URL CHANGED vs 11-Oct")
    notes.append("UTMs embedded in web_view_properties.url (Snapchat has no separate URL-tags field)")
    notes.append(READ_NOTE)
    rec["note"] = "; ".join(notes)
    out.append(rec)

with open(OUT, "w") as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# TASK 2: ads in the account that are not in the input (list endpoints exclude deleted entities)
input_ids = {r["ad_id"] for r in rows}
new = []
for aid in sorted(ads):
    if aid in input_ids:
        continue
    a = ads[aid]
    c = crs.get(a["creative_id"]) or {}
    sq = sqs.get(a["ad_squad_id"], {})
    base = {"platform": "snapchat", "account_id": ACC, "account_name": ACC_NAME,
            "campaign_name": None, "adset_name": None, "ad_id": aid, "ad_name": a["name"],
            "effective_status": "|".join(a["delivery_status"])}
    if c.get("type") == "COMPOSITE":
        for i, s in enumerate((c.get("composite_properties") or {}).get("creative_ids") or []):
            new.append(dict(base, slot="creative.composite_properties.creative_ids[%d] (%s).web_view_properties.url" % (i, s),
                            url=((crs.get(s) or {}).get("web_view_properties") or {}).get("url")))
    else:
        new.append(dict(base, slot="creative.web_view_properties.url", url=(c.get("web_view_properties") or {}).get("url")))
with open(NEW, "w") as f:
    for rec in new:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print("rows_out", len(out), "found", sum(1 for x in out if x["found"]), "not_found", sum(1 for x in out if not x["found"]),
      "url_changed", sum(1 for x, r in zip(out, rows) if x["url"] != r["url_11oct"]),
      "status_changed", sum(1 for x, r in zip(out, rows) if set((x["status_now"] or "").split("|")) != set((r["status_11oct"] or "").split("|"))),
      "new_ad_rows", len(new))
