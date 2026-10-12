"""Append one result line per change to out_tiktok_2.jsonl.

Usage: python3 -I rec.py <unit> <result> <before_file_or_->  <after_live_file_or_-> <detail_file> [new_entity_ids]
 - before / after_live: path to a text file holding the exact URL, or "-" to use the pre-read URL
   from preread.json (before) / the same value as before (after_live).
"""
import json
import sys

BASE = "/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/"
OUT = BASE + "out_tiktok_2.jsonl"

unit, result, before_src, after_src, detail_src = sys.argv[1:6]
new_ids = sys.argv[6] if len(sys.argv) > 6 else ""
assert result in ("Fixed", "AlreadyFixed", "Failed", "Skipped", "NotAttempted"), result

units = {u["unit"]: u for u in json.load(open(BASE + "in_tiktok_2.json"))}
pre = {a["ad_id"]: a for a in json.load(open(BASE + "tt2_work/preread.json"))["ads"]}
u = units[unit]
assert len(u["changes"]) == 1
c = u["changes"][0]

before = pre[unit]["landing_page_url"] if before_src == "-" else open(before_src).read().rstrip("\n")
after_live = before if after_src == "-" else open(after_src).read().rstrip("\n")
detail = open(detail_src).read().strip()

if result == "Fixed":
    assert after_live == c["new"], "Fixed requires byte-exact read-back"

# no duplicate lines for the same unit/slot
try:
    for line in open(OUT):
        r = json.loads(line)
        assert not (r["unit"] == unit and r["slot"] == c["slot"]), "already recorded"
except FileNotFoundError:
    pass

row = {
    "platform": "tiktok",
    "account_id": u["account_id"],
    "unit_type": u["unit_type"],
    "unit": unit,
    "ad_ids": u["ad_ids"],
    "ad_names": u["ad_names"],
    "slot": c["slot"],
    "before": before,
    "after_expected": c["new"],
    "after_live": after_live,
    "result": result,
    "new_entity_ids": new_ids,
    "detail": detail,
}
with open(OUT, "a") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
print("recorded", unit, result, "after_live==new:", after_live == c["new"])
