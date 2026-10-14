import json
import sys
from urllib.parse import urlsplit, parse_qsl

IN = sys.argv[1]
OUT = sys.argv[2]

ACCOUNT = "623ccdb3-d546-42e8-9082-89ff8b59cfd1"
READ_AT = "2026-10-14 ~14:47-14:50Z"

# Values exactly as returned by the live reads on 14-Oct-2026:
# GET /v1/adaccounts/{id}/ads (39 ads), /creatives (47 creatives),
# /adsquads (17), /campaigns (14); each returned one complete page.
ADS = {
    "02da1fcb-58e4-4742-a1ee-b3fc3e0387e9": {
        "creative_id": "6751c922-c15a-4dd8-bba2-580579842381",
        "status": "ACTIVE", "review_status": "APPROVED", "type": "REMOTE_WEBPAGE",
        "delivery_status": ["INVALID_EFFECTIVE_INVALID"],
        "ad_squad_id": "19b1349d-6f1f-4ab0-865f-f4707ce02816",
        "updated_at": "2025-09-21T08:56:34.218Z",
    },
    "1d81af98-7db5-463c-84ea-7f31f83ef679": {
        "creative_id": "6751c922-c15a-4dd8-bba2-580579842381",
        "status": "ACTIVE", "review_status": "APPROVED", "type": "REMOTE_WEBPAGE",
        "delivery_status": ["INVALID_EFFECTIVE_INVALID", "INVALID_NOT_EFFECTIVE_ACTIVE"],
        "ad_squad_id": "9021ca57-7586-49f7-82ee-e8c827f27f1a",
        "updated_at": "2025-09-21T08:41:18.182Z",
    },
    "4a098bdd-6db5-4fdb-8523-a7aa9eb94029": {
        "creative_id": "6751c922-c15a-4dd8-bba2-580579842381",
        "status": "ACTIVE", "review_status": "APPROVED", "type": "REMOTE_WEBPAGE",
        "delivery_status": ["INVALID_EFFECTIVE_INVALID"],
        "ad_squad_id": "38ef2d3d-c1b2-4bd8-a73b-802eb2237f84",
        "updated_at": "2025-09-21T08:41:23.165Z",
    },
}

CREATIVES = {
    "6751c922-c15a-4dd8-bba2-580579842381": {
        "type": "WEB_VIEW", "review_status": "APPROVED", "cta": "MORE",
        "url": "https://www.dgda.gov.sa/ar",
        "updated_at": "2025-09-21T08:41:18.078Z",
    },
}

ADSQUADS = {
    "19b1349d-6f1f-4ab0-865f-f4707ce02816": ("DGDA_CPC_Saudi National Day_21Sep_29Sep", "ACTIVE", "2025-09-29T20:59:00.000Z", "f41e443b-c042-47e7-9a09-6564c372544d"),
    "9021ca57-7586-49f7-82ee-e8c827f27f1a": ("DGDA_CPV_Saudi National Day_21Sep_29Sep", "PAUSED", "2025-09-29T20:59:00.000Z", "f41e443b-c042-47e7-9a09-6564c372544d"),
    "38ef2d3d-c1b2-4bd8-a73b-802eb2237f84": ("DGDA_CPM_Saudi National Day_21Sep_29Sep", "ACTIVE", "2025-09-29T20:59:00.000Z", "4a0c3ece-3ac9-4b97-90ab-e7c2f5e0ef27"),
}

CAMPAIGNS = {
    "f41e443b-c042-47e7-9a09-6564c372544d": ("DGDA_CPC_Saudi National Day_21Sep_29Sep_BO13398", "ACTIVE", "INVALID_END_TIME,INVALID_NOT_ACTIVE,INVALID_CAMPAIGN_HAS_NO_ACTIVE_AD_SQUAD"),
    "4a0c3ece-3ac9-4b97-90ab-e7c2f5e0ef27": ("DGDA_CPM_Saudi National Day_21Sep_29Sep_BO13398", "ACTIVE", "INVALID_END_TIME,INVALID_NOT_ACTIVE,INVALID_CAMPAIGN_HAS_NO_ACTIVE_AD_SQUAD"),
}


def utm_keys(url):
    if not url:
        return []
    return [k for k, _ in parse_qsl(urlsplit(url).query, keep_blank_values=True) if k.lower().startswith("utm_")]


rows = json.load(open(IN, encoding="utf-8"))
ads_by_creative = {}
for aid, a in ADS.items():
    ads_by_creative.setdefault(a["creative_id"], []).append(aid)

out_lines = []
for r in rows:
    ad_id = r["ad_id"]
    slot = r["slot"]
    ad = ADS.get(ad_id)
    if ad is None:
        out_lines.append({
            "platform": "snapchat", "account_id": ACCOUNT, "ad_id": ad_id, "slot": slot,
            "url": None, "status_now": None, "creative_id_now": None, "found": False,
            "note": "ad not returned by GET /v1/adaccounts/{id}/ads on 14-Oct (deleted or moved)",
        })
        continue
    cid = ad["creative_id"]
    cr = CREATIVES[cid]
    assert slot == "web_view_properties.url", slot
    url = cr["url"]

    ds_now = ad["delivery_status"]
    old = r.get("status_11oct") or ""
    old_set = set(s for s in old.split(",") if s)
    if set(ds_now) == old_set:
        # same set as 11-Oct: keep the 11-Oct ordering so the comparison does not show a false change
        status_now = old
        ds_note = "delivery_status unchanged vs 11-Oct (same set; API now lists it as %s)" % ",".join(ds_now) if ",".join(ds_now) != old else "delivery_status unchanged vs 11-Oct"
    else:
        status_now = ",".join(ds_now)
        ds_note = "delivery_status CHANGED vs 11-Oct (was %s)" % old

    notes = []
    notes.append("URL unchanged vs 11-Oct" if url == r.get("url_11oct") else "URL CHANGED vs 11-Oct (was %s)" % r.get("url_11oct"))
    keys = utm_keys(url)
    notes.append("UTM params on current URL: " + ",".join(keys) if keys else "no UTM params on current URL")
    notes.append("Snapchat has no separate url_tags field; UTMs live inside web_view_properties.url")
    notes.append("creative_id unchanged vs 11-Oct" if cid == r.get("creative_id") else "creative_id CHANGED vs 11-Oct (was %s)" % r.get("creative_id"))
    notes.append(ds_note)
    notes.append("ad.status=%s; ad.review_status=%s; ad.type=%s; ad.updated_at=%s" % (ad["status"], ad["review_status"], ad["type"], ad["updated_at"]))
    notes.append("creative %s type=%s review_status=%s updated_at=%s cta=%s (not edited since 2025-09-21)" % (cid, cr["type"], cr["review_status"], cr["updated_at"], cr["cta"]))
    others = [x for x in ads_by_creative[cid] if x != ad_id]
    if others:
        notes.append("creative shared with ad(s) %s - editing it changes all of them" % ", ".join(others))
    sq = ADSQUADS.get(ad["ad_squad_id"])
    if sq:
        camp = CAMPAIGNS.get(sq[3])
        notes.append("adsquad '%s' status=%s end_time=%s" % (sq[0], sq[1], sq[2]))
        if camp:
            notes.append("campaign '%s' status=%s (campaign delivery: %s)" % camp)
    notes.append("read %s via GET /v1/adaccounts/{id}/ads + /creatives + /adsquads + /campaigns (aggregate_pages; one complete page each: 39 ads, 47 creatives, 17 ad squads, 14 campaigns)" % READ_AT)

    out_lines.append({
        "platform": "snapchat", "account_id": ACCOUNT, "ad_id": ad_id, "slot": slot,
        "url": url, "status_now": status_now, "creative_id_now": cid, "found": True,
        "note": "; ".join(notes),
    })

with open(OUT, "w", encoding="utf-8") as f:
    for o in out_lines:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")
print("wrote", len(out_lines), "lines")
