import json, sys

# usage: python3 -I verify.py <readback.json> -> byte-for-byte verdict vs "new" for each asset in the read-back
BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
units = {u['unit']: u for u in json.load(open(BASE + '/apply9/in_google_sl_1.json'))}
rb = json.load(open(sys.argv[1]))
for aid, urls in rb['assets'].items():
    new = units[aid]['changes'][0]['new']
    ok = urls == [new]
    print(aid, 'BYTE_EQUAL_NEW' if ok else 'MISMATCH', rb['request_id'])
    if not ok:
        print('  live:', urls)
        print('  new :', new)
