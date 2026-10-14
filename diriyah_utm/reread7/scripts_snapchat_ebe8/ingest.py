# usage: python3 -I ingest.py <saved_tool_result_path> <dest_path> <collection: ads|creatives|adsquads|campaigns>
# Copies a saved MCP tool result into the work dir and checks it is complete (no budget truncation).
import json, sys, base64, re, shutil
src, dst, coll = sys.argv[1:4]
shutil.copyfile(src, dst)
d = json.load(open(dst))
if isinstance(d, list):  # [{"type":"text","text":"..."}] wrapper
    d = json.loads(d[0]["text"])
assert d.get("success") is True, "gateway not success"
budget = (d.get("meta") or {}).get("mcp_output_budget") or {}
proj = (d["data"].get("meta") or {}).get("mcp_result_projection") or {}
inner = d["data"]["data"]
assert inner.get("request_status") == "SUCCESS", inner.get("request_status")
items = inner[coll]
bad = [x for x in items if not isinstance(x, dict)]
key = coll[:-1]
subs = sorted({x.get("sub_request_status") for x in items if isinstance(x, dict)}, key=str)
recs = [x[key] for x in items if isinstance(x, dict)]
print("path", d["data"].get("path"), "items", len(items), "records", len(recs),
      "TRUNCATED" if (budget.get("truncated") or proj.get("truncated") or bad) else "complete",
      "markers", bad[:2], "budget_bytes", budget.get("serialized_bytes_before_budget"), "sub_status", subs)
print("first", recs[0]["id"] if recs else None, "last", recs[-1]["id"] if recs else None)
print("sorted_by_id", [r["id"] for r in recs] == sorted(r["id"] for r in recs))
nl = (inner.get("paging") or {}).get("next_link", "")
m = re.search(r"cursor=([^&]+)", nl)
if m:
    c = m.group(1)
    print("next_cursor", c, base64.b64decode(c + "=" * (-len(c) % 4)).decode())
else:
    print("no next_link")
