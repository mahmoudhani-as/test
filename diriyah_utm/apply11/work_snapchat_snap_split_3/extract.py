#!/usr/bin/env python3
"""Extract tool_use inputs and tool_result outputs from this agent's transcript.

Usage: python3 -I extract.py <transcript.jsonl> <out.json>
Writes a list of {tool_use_id, name, input, result_text, result_json} in call order.
"""
import json
import sys

src, out = sys.argv[1], sys.argv[2]
uses = {}
order = []
results = {}
with open(src, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        msg = ev.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use":
                uses[part["id"]] = {"tool_use_id": part["id"], "name": part.get("name"), "input": part.get("input")}
                order.append(part["id"])
            elif part.get("type") == "tool_result":
                c = part.get("content")
                if isinstance(c, list):
                    txt = "".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
                else:
                    txt = c if isinstance(c, str) else json.dumps(c)
                results[part.get("tool_use_id")] = txt

rows = []
for tid in order:
    r = dict(uses[tid])
    txt = results.get(tid)
    r["result_text"] = txt
    try:
        r["result_json"] = json.loads(txt) if txt else None
    except Exception:
        r["result_json"] = None
    rows.append(r)

with open(out, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False, indent=1)
print(len(rows), "tool calls extracted ->", out)
