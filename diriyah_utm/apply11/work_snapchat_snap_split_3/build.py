#!/usr/bin/env python3
"""Helpers for snap_split units (batch 3).

python3 -I build.py creative <calls.json> <creative_id> <new_url> <out_payload.json>
    -> builds the create payload from the latest raw GET of <creative_id>
python3 -I build.py ad <calls.json> <ad_id> <new_creative_id> <out_payload.json>
    -> builds the ad squad PUT payload from the latest raw GET of <ad_id>
python3 -I build.py cmp <calls.json> <tool_use_id> <payload.json>
    -> compares the payload I typed in that call with the built payload (byte for byte after JSON canonicalisation)
"""
import json
import sys

DROP_CREATIVE = {
    "id", "updated_at", "created_at", "packaging_status", "review_status",
    "review_status_details", "semantic_id", "created_by_app_id", "created_by_user",
    "last_updated_by_app_id", "last_updated_by_user",
}


def latest(calls, action_names, key, value, entity):
    found = None
    for r in calls:
        inp = r.get("input") or {}
        if inp.get("action") not in action_names:
            continue
        pp = inp.get("path_params") or {}
        if pp.get(key) != value:
            continue
        j = r.get("result_json")
        if not j:
            continue
        data = j.get("data", {}).get("data", {})
        items = data.get(entity + "s") or []
        for it in items:
            obj = it.get(entity)
            if obj and obj.get("id") == value:
                found = (r["tool_use_id"], obj)
    if not found:
        raise SystemExit("no raw read found for %s %s" % (entity, value))
    return found


def canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main():
    mode = sys.argv[1]
    calls = json.load(open(sys.argv[2], encoding="utf-8"))
    if mode == "creative":
        cid, new_url, out = sys.argv[3], sys.argv[4], sys.argv[5]
        tid, cr = latest(calls, {"snapchat_creative_get", "snapchat_creatives_creative_id_get"}, "creative_id", cid, "creative")
        if cr.get("type") != "WEB_VIEW":
            raise SystemExit("not WEB_VIEW: %s" % cr.get("type"))
        body = {k: v for k, v in cr.items() if k not in DROP_CREATIVE}
        wvp = dict(body["web_view_properties"])
        wvp["url"] = new_url
        body["web_view_properties"] = wvp
        payload = {"creatives": [body]}
        json.dump(payload, open(out, "w", encoding="utf-8"), ensure_ascii=False)
        print("source read:", tid)
        print("dropped:", sorted(k for k in cr if k in DROP_CREATIVE))
        print(json.dumps(payload, ensure_ascii=False))
    elif mode == "ad":
        aid, new_cid, out = sys.argv[3], sys.argv[4], sys.argv[5]
        tid, ad = latest(calls, {"snapchat_ad_get", "snapchat_ads_ad_id_get"}, "ad_id", aid, "ad")
        body = dict(ad)
        body["creative_id"] = new_cid
        payload = {"ads": [body]}
        json.dump(payload, open(out, "w", encoding="utf-8"), ensure_ascii=False)
        print("source read:", tid, "ad_squad_id:", ad["ad_squad_id"], "old creative:", ad["creative_id"])
        print(json.dumps(payload, ensure_ascii=False))
    elif mode == "cmp":
        tid, pfile = sys.argv[3], sys.argv[4]
        want = json.load(open(pfile, encoding="utf-8"))
        row = [r for r in calls if r["tool_use_id"] == tid]
        if not row:
            raise SystemExit("call not found")
        got = row[0]["input"].get("payload")
        if isinstance(got, str):
            got = json.loads(got)
        same = canon(got) == canon(want)
        print("payload identical:", same)
        if not same:
            print("typed :", canon(got))
            print("wanted:", canon(want))
        print("input flags:", {k: v for k, v in row[0]["input"].items() if k != "payload"})
        res = row[0].get("result_text") or ""
        print("result:", res[:6000])
    else:
        raise SystemExit("bad mode")


if __name__ == "__main__":
    main()
