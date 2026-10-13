#!/usr/bin/env python3
"""Verification helpers (reads raw API results from calls.json, the transcript extract).

python3 -I verify.py crcmp <calls.json> <old_cid> <new_cid> <new_url>
    old creative (first raw read) vs new creative (latest raw read): every field equal except
    id/timestamps/review/semantic and web_view_properties.url; url must equal new_url byte for byte.
python3 -I verify.py adcmp <calls.json> <ad_id> <expected_creative_id>
    ad first raw read vs latest raw read: only creative_id (and updated_at/review/delivery) may differ;
    latest creative_id must equal expected.
"""
import json
import sys

VOLATILE_CR = {"id", "updated_at", "created_at", "packaging_status", "review_status",
               "review_status_details", "semantic_id", "created_by_app_id", "created_by_user",
               "last_updated_by_app_id", "last_updated_by_user"}
VOLATILE_AD = {"updated_at", "review_status", "review_status_details", "delivery_status",
               "last_updated_by_app_id", "last_updated_by_user"}


def reads(calls, actions, key, value, entity):
    out = []
    for r in calls:
        inp = r.get("input") or {}
        if inp.get("action") not in actions:
            continue
        if (inp.get("path_params") or {}).get(key) != value:
            continue
        j = r.get("result_json")
        if not j:
            continue
        for it in j.get("data", {}).get("data", {}).get(entity + "s") or []:
            obj = it.get(entity)
            if obj and obj.get("id") == value:
                out.append((r["tool_use_id"], obj))
    return out


def main():
    mode = sys.argv[1]
    calls = json.load(open(sys.argv[2], encoding="utf-8"))
    ok = True
    if mode == "crcmp":
        old_id, new_id, new_url = sys.argv[3], sys.argv[4], sys.argv[5]
        cr_actions = {"snapchat_creative_get", "snapchat_creatives_creative_id_get"}
        old = reads(calls, cr_actions, "creative_id", old_id, "creative")
        new = reads(calls, cr_actions, "creative_id", new_id, "creative")
        if not old or not new:
            raise SystemExit("missing reads old=%d new=%d" % (len(old), len(new)))
        (ot, o), (nt, n) = old[0], new[-1]
        print("old read", ot, "| new read", nt)
        keys = sorted((set(o) | set(n)) - VOLATILE_CR)
        for k in keys:
            ov, nv = o.get(k, "<absent>"), n.get(k, "<absent>")
            if k == "web_view_properties":
                ov = dict(ov); nv = dict(nv)
                ou, nu = ov.pop("url", None), nv.pop("url", None)
                if nu != new_url:
                    ok = False
                    print("URL MISMATCH new creative:", nu)
                else:
                    print("url == new (byte for byte):", nu)
            if ov != nv:
                ok = False
                print("DIFF", k, "old=", json.dumps(ov, ensure_ascii=False), "new=", json.dumps(nv, ensure_ascii=False))
        print("new review_status:", n.get("review_status"), "| old review_status:", o.get("review_status"))
        print("old url:", o.get("web_view_properties", {}).get("url"))
    elif mode == "adcmp":
        ad_id, exp_cid = sys.argv[3], sys.argv[4]
        ad_actions = {"snapchat_ad_get", "snapchat_ads_ad_id_get"}
        rs = reads(calls, ad_actions, "ad_id", ad_id, "ad")
        if len(rs) < 2:
            raise SystemExit("need >=2 reads of the ad, have %d" % len(rs))
        (ft, f), (lt, l) = rs[0], rs[-1]
        print("first read", ft, "| latest read", lt)
        for k in sorted((set(f) | set(l)) - VOLATILE_AD - {"creative_id"}):
            if f.get(k, "<absent>") != l.get(k, "<absent>"):
                ok = False
                print("DIFF", k, json.dumps(f.get(k), ensure_ascii=False), "->", json.dumps(l.get(k), ensure_ascii=False))
        print("creative_id:", f.get("creative_id"), "->", l.get("creative_id"), "(expected %s)" % exp_cid)
        if l.get("creative_id") != exp_cid:
            ok = False
        print("status:", f.get("status"), "->", l.get("status"), "| review_status:", f.get("review_status"), "->", l.get("review_status"),
              "| delivery_status:", f.get("delivery_status"), "->", l.get("delivery_status"))
    print("VERIFY_OK" if ok else "VERIFY_FAIL")


if __name__ == "__main__":
    main()
