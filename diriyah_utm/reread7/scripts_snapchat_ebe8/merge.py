# usage: python3 -I merge.py <work_dir> <collection> <out_name> <page files...>
import json, sys
W, coll, outname = sys.argv[1:4]
pages = sys.argv[4:]
key = coll[:-1]


def load(p):
    d = json.load(open(p))
    if isinstance(d, list):
        d = json.loads(d[0]["text"])
    assert d["success"] is True and d["data"]["data"]["request_status"] == "SUCCESS"
    assert not ((d.get("meta") or {}).get("mcp_output_budget") or {}).get("truncated"), "truncated page " + p
    assert not ((d["data"].get("meta") or {}).get("mcp_result_projection") or {}).get("truncated"), "truncated page " + p
    return d["data"]["data"][coll], (d["data"]["data"].get("paging") or {}).get("next_link")


recs, order = {}, []
for i, p in enumerate(pages):
    items, nl = load(p)
    if i < len(pages) - 1:
        assert nl, "page %s has no next_link but is not the last page" % p
    else:
        assert not nl, "last page %s still has a next_link: %s" % (p, nl)
    for x in items:
        assert isinstance(x, dict), "truncation marker in " + p
        r = x[key]
        assert r["id"] not in recs, "duplicate id across pages " + r["id"]
        order.append(r["id"])
        recs[r["id"]] = r
print(coll, "unique", len(recs), "sorted", order == sorted(order))
json.dump([recs[i] for i in order], open(W + "/" + outname, "w"), indent=1, ensure_ascii=False)
