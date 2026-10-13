import json, re, sys
raw_path, in_path, out_path, new_path = sys.argv[1:5]
ACCOUNT = "1033388761412991"
j = json.load(open(raw_path, encoding="utf-8"))
payload = j["data"]["data"]
ads = payload["data"]
assert not payload.get("paging", {}).get("next"), "unexpected further page"
by_id = {a["id"]: a for a in ads}
inp = json.load(open(in_path, encoding="utf-8"))

def join_tags(link, tags):
    if not tags:
        return link
    return link + ("&" if "?" in link else "?") + tags.lstrip("?&")

out = []
for r in inp:
    ad_id, slot = r["ad_id"], r["slot"]
    a = by_id.get(ad_id)
    if a is None:
        out.append({"platform": "meta", "account_id": ACCOUNT, "ad_id": ad_id, "slot": slot, "url": None,
                    "status_now": "NOT_FOUND", "creative_id_now": None, "found": False,
                    "note": "ad not returned by act_%s/ads across all non-deleted effective statuses (incl. ARCHIVED): deleted" % ACCOUNT})
        continue
    c = a.get("creative") or {}
    cid = c.get("id")
    status = a.get("effective_status")
    oss = c.get("object_story_spec") or {}
    tags = c.get("url_tags")
    parts = []
    if cid == r["creative_id"]:
        parts.append("creative unchanged since 11-Oct")
    else:
        parts.append("creative CHANGED since 11-Oct: %s -> %s (ad updated_time %s)" % (r["creative_id"], cid, a.get("updated_time")))
    url = None
    if slot == "creative.object_story_spec.link_data.link":
        ld = oss.get("link_data") or {}
        link = ld.get("link")
        url = join_tags(link, tags) if link else None
        parts.append("object_story_spec.link_data.link = %s" % link)
        parts.append("creative.url_tags = %s" % tags if tags else "creative.url_tags not set (UTMs carried in the link itself)" if link and "utm_" in link else "creative.url_tags not set (no UTM)")
        cta = ld.get("call_to_action") or c.get("call_to_action") or {}
        if cta.get("type"):
            parts.append("CTA %s" % cta["type"])
        if ld.get("name"):
            parts.append("headline link_data.name '%s'" % ld["name"])
        if ld.get("image_hash"):
            parts.append("image_hash %s" % ld["image_hash"])
        parts.append("effective_object_story_id %s, IG %s" % (c.get("effective_object_story_id"), c.get("instagram_permalink_url")))
        if r["url_11oct"] is not None and url != r["url_11oct"]:
            parts.append("URL changed since 11-Oct (was %s)" % r["url_11oct"])
        if cid != r["creative_id"] and ad_id == "120203161740580598":
            parts.append("matches apply11 meta_tco_headline fix (after_expected == live); caution: UTMs sit on a t.co short link - whether t.co passes them through to the final destination was not checked")
    else:
        m = re.match(r"boosted post call_to_action\.value\.link \(effective_object_story_id (\S+)\)$", slot)
        assert m, slot
        eosid_in = m.group(1)
        eosid_now = c.get("effective_object_story_id")
        if eosid_now == eosid_in:
            parts.append("still a boosted existing post (effective_object_story_id %s, object_type %s, IG %s)" % (eosid_now, c.get("object_type"), c.get("instagram_permalink_url")))
        else:
            parts.append("effective_object_story_id CHANGED: %s -> %s" % (eosid_in, eosid_now))
        parts.append("no object_story_spec/asset_feed_spec on creative" if not oss and not c.get("asset_feed_spec") else "creative now has object_story_spec/asset_feed_spec")
        parts.append("creative.url_tags = %s" % tags if tags else "creative.url_tags not set")
        cta = c.get("call_to_action")
        link = None
        if not cta:
            parts.append("no call_to_action on creative (no destination link)")
        else:
            val = cta.get("value") or {}
            link = val.get("link")
            if not link:
                parts.append("creative.call_to_action %s with no link (no destination link)" % cta.get("type"))
            elif val.get("app_destination") == "MESSENGER":
                parts.append("creative.call_to_action %s -> %s (app_destination MESSENGER; messaging CTA, not a website URL)" % (cta.get("type"), link))
            else:
                parts.append("creative.call_to_action %s -> %s (%s)" % (cta.get("type"), link, "has UTM" if "utm_" in link else "no UTM"))
        if r["url_11oct"] is None:
            url = None
            s = "url kept null as on 11-Oct (11-Oct had no readable URL for this slot)"
            if link:
                s += "; the CTA link above is now readable on the creative itself"
            parts.append(s)
        else:
            url = join_tags(link, tags) if link else None
    if status == r["status_11oct"]:
        parts.append("status unchanged (%s)" % status)
    else:
        parts.append("status changed %s -> %s" % (r["status_11oct"], status))
    out.append({"platform": "meta", "account_id": ACCOUNT, "ad_id": ad_id, "slot": slot, "url": url,
                "status_now": status, "creative_id_now": cid, "found": True, "note": "; ".join(parts)})

with open(out_path, "w", encoding="utf-8") as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")

in_ids = {r["ad_id"] for r in inp}
new_rows = []
for a in ads:
    if a["id"] in in_ids:
        continue
    # (none expected) emit each URL slot of a new ad
    c = a.get("creative") or {}
    base = {"platform": "meta", "account_id": ACCOUNT, "account_name": "Diriyah Gate - Billed to MS KSA",
            "campaign_name": (a.get("campaign") or {}).get("name"), "adset_name": (a.get("adset") or {}).get("name"),
            "ad_id": a["id"], "ad_name": a.get("name"), "effective_status": a.get("effective_status")}
    new_rows.append(dict(base, slot="NEEDS_MANUAL_SLOT_EXPANSION", url=None))
with open(new_path, "w", encoding="utf-8") as f:
    for o in new_rows:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")
print("wrote", len(out), "rows;", len(new_rows), "new-ad rows")
