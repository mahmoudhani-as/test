import json
import sys

inp_path, snap_path, out_path, new_path = sys.argv[1:5]
ACCOUNT_ID = "7eee5995-3ea6-4419-9d2d-726f927578b2"
ACCOUNT_NAME = "Wadi Safar"
SLOT = "creative.web_view_properties.url"
UNATTACHED = "fbf7fafd-e334-4f16-9be8-41f5803d2166"

rows = json.load(open(inp_path))
snap = json.load(open(snap_path))
ads = {a["id"]: a for a in snap["ads"]}
sqs = {s["id"]: s for s in snap["adsquads"]}
cps = {c["id"]: c for c in snap["campaigns"]}
crs = {c["id"]: c for c in snap["creatives"]}

users = {}
for a in snap["ads"]:
    users.setdefault(a["creative_id"], []).append(a["id"])


def effective(ad, sq, cp):
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
        rec["note"] = ("ad not returned by GET /v1/adaccounts/{id}/ads (paged, all pages read) - "
                       "deleted / no longer exists; read 2026-10-13 ~14:08Z")
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
    if ad["creative_id"] == "5131682d-a402-4319-b1e5-6e656d0b0dfb" and ad["id"] == "220baf2e-85d5-4b9a-be8a-26e239875a4d":
        u = crs.get(UNATTACHED)
        if u:
            notes.append(("apply11 snap_split copy creative %s (utm_campaign=1788ef28_thechediresidences_conv, "
                          "review_status=%s, created %s) exists in the account but is NOT attached to this ad - "
                          "the ad still serves creative 5131682d with the sep26 URL") % (
                              UNATTACHED, u["review_status"], u["updated_at"]))
    notes.append("read 2026-10-13 ~14:08Z via GET adaccounts/{id}/ads + /creatives + /adsquads + /campaigns (paging verified)")
    rec["note"] = "; ".join(notes)
    out.append(rec)

with open(out_path, "w") as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# TASK 2: ads in the account not in the input
input_ids = {r["ad_id"] for r in rows}
new_lines = []
for a in snap["ads"]:
    if a["id"] in input_ids:
        continue
    sq = sqs.get(a["ad_squad_id"])
    cp = cps.get(sq["campaign_id"]) if sq else None
    cr = crs.get(a["creative_id"])
    new_lines.append({
        "platform": "snapchat", "account_id": ACCOUNT_ID, "account_name": ACCOUNT_NAME,
        "campaign_name": cp["name"] if cp else None, "adset_name": sq["name"] if sq else None,
        "ad_id": a["id"], "ad_name": a["name"], "effective_status": effective(a, sq, cp),
        "slot": SLOT, "url": cr["url"] if cr else None,
    })
with open(new_path, "w") as f:
    for rec in new_lines:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print("rows", len(out), "found", sum(1 for r in out if r["found"]), "not_found",
      sum(1 for r in out if not r["found"]), "new_ads", len(new_lines))
