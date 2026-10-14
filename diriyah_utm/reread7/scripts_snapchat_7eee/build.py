import json
import sys

# usage: build.py <input_partial.json> <snapshot.json> <out.jsonl> [<prev_snapshot.json>]
inp_path, snap_path, out_path = sys.argv[1:4]
prev_path = sys.argv[4] if len(sys.argv) > 4 else None

ACCOUNT_ID = "7eee5995-3ea6-4419-9d2d-726f927578b2"
SLOT = "creative.web_view_properties.url"
UNATTACHED = "fbf7fafd-e334-4f16-9be8-41f5803d2166"
READ_NOTE = ("read 2026-10-14 ~14:50Z via GET adaccounts/{id}/ads + /creatives + /adsquads + /campaigns "
             "(paging verified: ads limit=5 -> 3 pages / 12 ads, creatives limit=5 -> 2 pages / 7 creatives)")

rows = json.load(open(inp_path))
snap = json.load(open(snap_path))
ads = {a["id"]: a for a in snap["ads"]}
sqs = {s["id"]: s for s in snap["adsquads"]}
cps = {c["id"]: c for c in snap["campaigns"]}
crs = {c["id"]: c for c in snap["creatives"]}

prev_ads = prev_crs = None
if prev_path:
    prev = json.load(open(prev_path))
    prev_ads = {a["id"]: a for a in prev["ads"]}
    prev_crs = {c["id"]: c for c in prev["creatives"]}

users = {}
for a in snap["ads"]:
    users.setdefault(a["creative_id"], []).append(a["id"])
attached = set(users)


def effective(ad, sq, cp):
    # Snapchat has no effective_status field: derive it from the ad and its parents.
    if ad["status"] != "ACTIVE":
        return ad["status"]
    if sq and sq["status"] != "ACTIVE":
        return "ADSET_PAUSED"
    if cp and cp["status"] != "ACTIVE":
        return "CAMPAIGN_PAUSED"
    if ad.get("review_status") == "REJECTED":
        return "REJECTED"
    return "ACTIVE"


out = []
for r in rows:
    ad = ads.get(r["ad_id"])
    rec = {
        "platform": "snapchat",
        "account_id": ACCOUNT_ID,
        "ad_id": r["ad_id"],
        "slot": r["slot"],
        "url": None,
        "status_now": None,
        "creative_id_now": None,
        "found": False,
        "note": "",
    }
    if ad is None:
        rec["status_now"] = "DELETED"
        rec["note"] = ("ad not returned by GET /v1/adaccounts/{id}/ads (all pages read) - "
                       "deleted / no longer exists; " + READ_NOTE)
        out.append(rec)
        continue
    sq = sqs.get(ad["ad_squad_id"])
    cp = cps.get(sq["campaign_id"]) if sq else None
    cr = crs.get(ad["creative_id"])
    status_now = effective(ad, sq, cp)
    rec["status_now"] = status_now
    rec["creative_id_now"] = ad["creative_id"]
    notes = []
    if r["slot"] != SLOT:
        notes.append("UNEXPECTED slot for a WEB_VIEW creative - check")
    if cr is None:
        rec["found"] = False
        notes.append("creative %s not returned by GET creatives - creative missing" % ad["creative_id"])
    else:
        rec["found"] = True
        rec["url"] = cr["url"]
        if r.get("url_11oct") is None:
            notes.append("11-Oct URL was null; current URL read from creative")
        elif cr["url"] == r["url_11oct"]:
            notes.append("URL unchanged vs 11-Oct")
        else:
            notes.append("URL CHANGED vs 11-Oct (was %s)" % r["url_11oct"])
    if ad["creative_id"] != r.get("creative_id"):
        notes.append("creative_id CHANGED vs 11-Oct (was %s)" % r.get("creative_id"))
    else:
        notes.append("creative_id unchanged vs 11-Oct")
    if status_now == r.get("status_11oct"):
        notes.append("effective status unchanged vs 11-Oct (%s)" % status_now)
    else:
        notes.append("effective status CHANGED vs 11-Oct (was %s)" % r.get("status_11oct"))
    notes.append("ad.status=%s; ad.review_status=%s; ad.type=%s; delivery_status=%s; ad.updated_at=%s" % (
        ad["status"], ad["review_status"], ad["type"], "|".join(ad["delivery_status"]), ad["updated_at"]))
    if sq:
        notes.append("adsquad.status=%s (%s)" % (sq["status"], sq["name"]))
    if cp:
        notes.append("campaign.status=%s (%s)" % (cp["status"], cp["name"]))
    if cr:
        notes.append("creative type=%s (%s) review_status=%s updated_at=%s" % (
            cr["type"], cr["ad_product"], cr["review_status"], cr["updated_at"]))
        others = [x for x in users.get(ad["creative_id"], []) if x != ad["id"]]
        if others:
            notes.append("creative shared with ad(s) %s" % ", ".join(others))
    notes.append("UTMs embedded in web_view_properties.url, no separate url_tags field")
    if prev_ads is not None:
        pa = prev_ads.get(ad["id"])
        pc = prev_crs.get(ad["creative_id"]) if prev_crs else None
        same = (pa is not None and pa["creative_id"] == ad["creative_id"] and pa["status"] == ad["status"]
                and pa["updated_at"] == ad["updated_at"] and pc is not None and cr is not None
                and pc["url"] == cr["url"] and pc["updated_at"] == cr["updated_at"])
        notes.append("no change since the 13-Oct ~14:08Z re-read (ad and creative updated_at identical)"
                     if same else "DIFFERS from the 13-Oct ~14:08Z re-read - check")
    if ad["id"] == "220baf2e-85d5-4b9a-be8a-26e239875a4d":
        u = crs.get(UNATTACHED)
        if u and UNATTACHED not in attached:
            notes.append(("apply11 snap_split copy creative %s (utm_campaign=1788ef28_thechediresidences_conv, "
                          "review_status=%s, created %s) still exists in the account but is NOT attached to any ad - "
                          "this ad still serves creative 5131682d with the sep26 URL") % (
                              UNATTACHED, u["review_status"], u["updated_at"]))
    notes.append(READ_NOTE)
    rec["note"] = "; ".join(notes)
    out.append(rec)

with open(out_path, "w") as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print("rows", len(out), "found", sum(1 for r in out if r["found"]), "not_found",
      sum(1 for r in out if not r["found"]))
print("url changed vs 11-Oct:", sum(1 for r in out if "URL CHANGED" in r["note"]))
print("creative changed vs 11-Oct:", sum(1 for r in out if "creative_id CHANGED" in r["note"]))
print("status changed vs 11-Oct:", sum(1 for r in out if "effective status CHANGED" in r["note"]))
print("differs from 13-Oct:", sum(1 for r in out if "DIFFERS from the 13-Oct" in r["note"]))
print("account ads not in input:", sorted(set(ads) - {r["ad_id"] for r in rows}))
print("creatives not attached to any ad:", sorted(set(crs) - attached))
