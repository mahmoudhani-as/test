# usage: python3 -I ingest.py <saved_tool_result_path> <dest_path> <collection: ads|creatives|adsquads|campaigns>
import json, sys, base64, re, shutil
src, dst, coll = sys.argv[1:4]
shutil.copyfile(src, dst)
t = open(dst).read()
d = json.loads(t)
if isinstance(d, list):  # [{"type":"text","text":"..."}] wrapper
    d = json.loads(d[0]["text"])
assert d.get("success") is True, "gateway not success"
inner = d["data"]["data"]
assert inner.get("request_status") == "SUCCESS", inner.get("request_status")
items = inner[coll]
bad = [x for x in items if not isinstance(x, dict)]
budget = (d.get("meta") or {}).get("mcp_output_budget")
key = coll[:-1]
subs = sorted({x.get("sub_request_status") for x in items if isinstance(x, dict)}, key=str)
recs = [x[key] for x in items if isinstance(x, dict)]
print("path", d["data"].get("path"), "items", len(items), "records", len(recs), "non-dict(truncation markers)", bad[:2], "budget", budget, "sub_status", subs)
print("first", recs[0]["id"] if recs else None, "last", recs[-1]["id"] if recs else None)
print("sorted_by_id", [r["id"] for r in recs] == sorted(r["id"] for r in recs))
nl = (inner.get("paging") or {}).get("next_link", "")
m = re.search(r"cursor=([^&]+)", nl)
if m:
    c = m.group(1)
    print("next_cursor", c, base64.b64decode(c + "=" * (-len(c) % 4)).decode())
else:
    print("no next_link")
