import json, sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

BASE = "/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm"
ACC = "7280828159585468418"
ACC_NAME = "Diriyah Gate - Billed to MS KSA"
inp = json.load(open(f"{BASE}/reread/in/tiktok_{ACC}.json"))
snap = json.load(open(f"{BASE}/reread2/work/tiktok_{ACC}_snapshot.json"))
cur = {a["ad_id"]: a for a in snap["ads"]}

def render(url, utm):
    """Append utm_params (list of {key,value}) to url unless already present."""
    if not url:
        return None
    if not utm:
        return url
    parts = urlsplit(url)
    q = parse_qsl(parts.query, keep_blank_values=True)
    have = {k for k, _ in q}
    add = [(p.get("key"), p.get("value")) for p in utm if p.get("key") and p.get("key") not in have]
    if not add:
        return url
    return urlunsplit(parts._replace(query=urlencode(q + add, safe="{}_:/")))

out_rows = []
for r in inp:
    a = cur.get(r["ad_id"])
    if a is None:
        out_rows.append({"platform": "tiktok", "account_id": ACC, "ad_id": r["ad_id"], "slot": r["slot"],
                         "url": None, "status_now": "DELETED", "creative_id_now": None, "found": False,
                         "note": "Ad not returned by ad/get with primary_status STATUS_ALL (deleted)."})
        continue
    if r["slot"] == "ad.landing_page_url":
        url = render(a.get("landing_page_url") or None, a.get("utm_params"))
    else:
        url = None
    note = (f"Unchanged since 11-Oct: landing_page_url empty, landing_page_urls null, utm_params not set, "
            f"no deeplink/page_id/card; operation_status {a['operation_status']}, secondary_status {a['secondary_status']} "
            f"(finished delivery); last modified {a['modify_time']} UTC. TikTok has no separate creative ID "
            f"(video_id {a['video_id']}). Read via ad/get STATUS_ALL page_size 100 (13 ads, 1 page).")
    out_rows.append({"platform": "tiktok", "account_id": ACC, "ad_id": r["ad_id"], "slot": r["slot"],
                     "url": url, "status_now": a["secondary_status"], "creative_id_now": None,
                     "found": True, "note": note})

out_path = f"{BASE}/reread2/out/tiktok_{ACC}.jsonl"
with open(out_path, "w", encoding="utf-8") as f:
    for row in out_rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

# Task 2: ads in account not in input (skip deleted)
in_ids = {r["ad_id"] for r in inp}
new_rows = []
for a in snap["ads"]:
    if a["ad_id"] in in_ids:
        continue
    new_rows.append({"platform": "tiktok", "account_id": ACC, "account_name": ACC_NAME,
                     "campaign_name": a["campaign_name"], "adset_name": a["adgroup_name"],
                     "ad_id": a["ad_id"], "ad_name": a["ad_name"], "effective_status": a["secondary_status"],
                     "slot": "ad.landing_page_url", "url": render(a.get("landing_page_url") or None, a.get("utm_params"))})
new_path = f"{BASE}/reread2/out/new_tiktok_{ACC}.jsonl"
with open(new_path, "w", encoding="utf-8") as f:
    for row in new_rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
print("wrote", len(out_rows), "rows;", len(new_rows), "new ads")
