import json, os
OUT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_google_4.jsonl'
def record(u, c, before, after_live, result, detail, new_entity_ids=""):
    line = {"platform": u["platform"], "account_id": u["account_id"], "unit_type": u["unit_type"],
            "unit": u["unit"], "ad_ids": u["ad_ids"], "ad_names": u["ad_names"], "slot": c["slot"],
            "before": before, "after_expected": c["new"], "after_live": after_live, "result": result,
            "new_entity_ids": new_entity_ids, "detail": detail}
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
def recorded_keys():
    ks = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            l = l.strip()
            if l:
                o = json.loads(l); ks.add((o["unit"], o["slot"]))
    return ks
