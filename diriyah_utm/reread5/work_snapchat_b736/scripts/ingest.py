# usage: python3 -I ingest.py <saved_tool_result_path> <dest_path> <collection: ads|creatives|adsquads|campaigns>
# Copies a saved MCP tool result into the work dir and checks it is complete (no truncation, no leftover next_link).
import json, sys, shutil
src, dst, coll = sys.argv[1:4]
if src != dst:
    shutil.copyfile(src, dst)
d = json.load(open(dst))
if isinstance(d, list):  # [{"type":"text","text":"..."}] wrapper
    d = json.loads("".join(x.get("text", "") for x in d))
assert d.get("success") is True, "gateway not success: %s" % json.dumps(d)[:500]
print("outer meta", json.dumps(d.get("meta"))[:600])
print("data.meta", json.dumps(d["data"].get("meta"))[:1200])
inner = d["data"]["data"]
assert inner.get("request_status") == "SUCCESS", inner.get("request_status")
print("inner keys", list(inner.keys()), "paging", json.dumps(inner.get("paging"))[:300])
items = inner[coll]
bad = [x for x in items if not isinstance(x, dict)]
key = coll[:-1]
subs = sorted({x.get("sub_request_status") for x in items if isinstance(x, dict)}, key=str)
recs = [x[key] for x in items if isinstance(x, dict) and key in x]
ids = [r["id"] for r in recs]
print("items", len(items), "records", len(recs), "unique ids", len(set(ids)), "non-dict markers", bad[:3], "sub_status", subs)
print("sorted_by_id", ids == sorted(ids))
