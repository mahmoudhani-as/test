# usage: python3 -I from_transcript.py <transcript.jsonl> <action> <cursor or "-" for none> <dest_path> [limit]
# Saves the tool_result of the LAST snapchat_native_action call matching (action, query.cursor[, query.limit]) from this
# agent's own transcript (for results that were returned inline instead of being persisted to tool-results/).
import json, sys
tr, action, cursor, dst = sys.argv[1:5]
limit = int(sys.argv[5]) if len(sys.argv) > 5 else None
uses, results = [], {}
for line in open(tr):
    try:
        d = json.loads(line)
    except Exception:
        continue
    c = (d.get("message") or {}).get("content")
    if not isinstance(c, list):
        continue
    for b in c:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "tool_use" and b.get("name", "").endswith("snapchat_native_action"):
            uses.append(b)
        elif b.get("type") == "tool_result":
            results[b.get("tool_use_id")] = b.get("content")
match = []
for u in uses:
    i = u.get("input") or {}
    q = i.get("query") or {}
    if isinstance(q, str):
        q = json.loads(q)
    if i.get("action") != action:
        continue
    if (q.get("cursor") or "-") != cursor:
        continue
    if limit is not None and q.get("limit") != limit:
        continue
    match.append(u)
assert match, "no matching tool_use"
u = match[-1]
res = results.get(u["id"])
assert res is not None, "no tool_result yet for " + u["id"]
if isinstance(res, str):
    res = [{"type": "text", "text": res}]
json.dump(res, open(dst, "w"), ensure_ascii=False)
print("saved", u["id"], "->", dst, "chars", sum(len(x.get("text", "")) for x in res if isinstance(x, dict)))
