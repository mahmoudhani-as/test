# usage: python3 -I merge.py <work_dir> <collection> <out_name> <page files...>
import json, sys
W, coll, outname = sys.argv[1:4]
pages = sys.argv[4:]
key = coll[:-1]


def load(p):
    d = json.load(open(p))
    if isinstance(d, list):
        d = json.loads("".join(x.get("text", "") for x in d))
    assert d["success"] is True and d["data"]["data"]["request_status"] == "SUCCESS"
    assert not ((d.get("meta") or {}).get("mcp_output_budget") or {}).get("truncated"), "truncated page " + p
    assert not ((d["data"].get("meta") or {}).get("mcp_result_projection") or {}).get("truncated"), "truncated page " + p
    return d["data"]["data"][coll]


recs, order = {}, []
for p in pages:
    for x in load(p):
        assert isinstance(x, dict), "truncation marker in " + p
        assert x.get("sub_request_status") in (None, "SUCCESS"), x
        r = x[key]
        assert r["id"] not in recs, "duplicate id across pages " + r["id"]
        order.append(r["id"])
        recs[r["id"]] = r
print(coll, "unique", len(recs), "sorted", order == sorted(order))
json.dump({i: recs[i] for i in order}, open(W + "/" + outname, "w"), indent=1, ensure_ascii=False)
