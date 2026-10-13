#!/usr/bin/env python3
"""rec.py <row_json_file>  -> append one result line (fields filled from the input unit) to apply7/out_tiktok_5.jsonl
row file: {"unit":..., "before":..., "after_live":..., "result":..., "detail":..., "new_entity_ids": ""}"""
import json, sys
ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = ROOT + '/apply7/in_tiktok_5.json'
OUT = ROOT + '/apply7/out_tiktok_5.jsonl'
r = json.load(open(sys.argv[1]))
u = {x['unit']: x for x in json.load(open(INP))}[r['unit']]
ch = u['changes'][0]
assert r['result'] in ('Fixed', 'AlreadyFixed', 'Failed', 'Skipped', 'NotAttempted')
if r['result'] == 'Fixed': assert r['after_live'] == ch['new']
row = {'platform': 'tiktok', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'], 'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'],
       'slot': ch['slot'], 'before': r['before'], 'after_expected': ch['new'], 'after_live': r['after_live'], 'result': r['result'],
       'new_entity_ids': r.get('new_entity_ids', ''), 'detail': r['detail']}
with open(OUT, 'a', encoding='utf-8') as f:
    f.write(json.dumps(row, ensure_ascii=False) + '\n')
print('appended', row['unit'], row['result'])
