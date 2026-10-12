import json, sys
inp_path, snap_path, out_path, new_path = sys.argv[1:5]
ACC = "7eee5995-3ea6-4419-9d2d-726f927578b2"
ACC_NAME = "Wadi Safar"
rows = json.load(open(inp_path))
snap = json.load(open(snap_path))
ads = {a["id"]: a for a in snap["ads"]}
crs = {c["id"]: c for c in snap["creatives"]}
sqs = {s["id"]: s for s in snap["adsquads"]}
cps = {c["id"]: c for c in snap["campaigns"]}
cr_users = {}
for a in snap["ads"]:
    cr_users.setdefault(a["creative_id"], []).append(a["id"])

out = []
for r in rows:
    ad = ads.get(r["ad_id"])
    rec = {"platform": "snapchat", "account_id": ACC, "ad_id": r["ad_id"], "slot": r["slot"]}
    if ad is None:
        rec.update({"url": None, "status_now": "DELETED", "creative_id_now": None, "found": False,
                    "note": "ad not returned by GET /adaccounts/{id}/ads (deleted)"})
        out.append(rec); continue
    cr = crs.get(ad["creative_id"])
    sq = sqs.get(ad["ad_squad_id"], {})
    cp = cps.get(sq.get("campaign_id"), {})
    if cr is None:
        rec.update({"url": None, "status_now": ad["status"], "creative_id_now": ad["creative_id"], "found": False,
                    "note": "creative %s not returned by GET /adaccounts/{id}/creatives (deleted)" % ad["creative_id"]})
        out.append(rec); continue
    url = cr["url"]
    parts = []
    parts.append("URL unchanged vs 11-Oct" if url == r["url_11oct"] else "URL CHANGED vs 11-Oct (was %s)" % r["url_11oct"])
    if ad["creative_id"] != r["creative_id"]:
        parts.append("creative_id CHANGED vs 11-Oct (was %s)" % r["creative_id"])
    parts.append("ad.status=%s; review_status=%s; delivery_status=%s; ad updated_at=%s" % (
        ad["status"], ad["review_status"], "|".join(ad["delivery_status"]), ad["updated_at"]))
    parts.append("adsquad.status=%s (%s); campaign.status=%s (%s)" % (sq.get("status"), sq.get("name"), cp.get("status"), cp.get("name")))
    others = [x for x in cr_users.get(ad["creative_id"], []) if x != ad["id"]]
    parts.append("creative type=%s (%s) review_status=%s updated_at=%s; UTMs embedded in web_view_properties.url, no separate url_tags field; creative shared with ad(s) %s" % (
        cr["type"], cr["ad_product"], cr["review_status"], cr["updated_at"], ", ".join(others) if others else "none"))
    parts.append("read 2026-10-12 ~14:05Z via GET adaccounts/{id}/ads + /creatives")
    rec.update({"url": url, "status_now": ad["status"], "creative_id_now": ad["creative_id"], "found": True,
                "note": "; ".join(parts)})
    out.append(rec)

with open(out_path, "w") as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

input_ids = {r["ad_id"] for r in rows}
new = []
for a in snap["ads"]:
    if a["id"] in input_ids:
        continue
    cr = crs.get(a["creative_id"], {})
    sq = sqs.get(a["ad_squad_id"], {})
    cp = cps.get(sq.get("campaign_id"), {})
    new.append({"platform": "snapchat", "account_id": ACC, "account_name": ACC_NAME,
                "campaign_name": cp.get("name"), "adset_name": sq.get("name"), "ad_id": a["id"],
                "ad_name": a["name"], "effective_status": a["status"],
                "slot": "creative.web_view_properties.url", "url": cr.get("url")})
with open(new_path, "w") as f:
    for rec in new:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print("rows_out", len(out), "found", sum(1 for x in out if x["found"]), "not_found", sum(1 for x in out if not x["found"]),
      "url_changed", sum(1 for x, r in zip(out, rows) if x["url"] != r["url_11oct"]), "new_ads", len(new))
