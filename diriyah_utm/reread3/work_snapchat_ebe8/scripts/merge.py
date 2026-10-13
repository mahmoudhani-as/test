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
    assert not (d.get("meta") or {}).get("mcp_output_budget", {}).get("truncated"), "truncated page " + p
    return d["data"]["data"][coll]
def norm(o):
    o = dict(o)
    if isinstance(o.get("delivery_status"), list):
        o["delivery_status"] = sorted(o["delivery_status"])
    return o
recs, order, diffs = {}, [], 0
for p in pages:
    for x in load(p):
        assert isinstance(x, dict), "truncation marker in " + p
        r = x[key]
        if r["id"] in recs:
            if norm(recs[r["id"]]) != norm(r):
                b = recs[r["id"]]
                diffs += 1
                print("overlap diff", r["id"], {k: (b.get(k), r.get(k)) for k in set(b) | set(r) if norm(b).get(k) != norm(r).get(k)})
        else:
            order.append(r["id"])
        recs[r["id"]] = r
print(coll, "unique", len(recs), "sorted", order == sorted(order), "overlap diffs", diffs)
json.dump([recs[i] for i in order], open(W + "/" + outname, "w"), indent=1, ensure_ascii=False)
