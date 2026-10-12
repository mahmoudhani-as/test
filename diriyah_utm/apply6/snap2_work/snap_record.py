"""Compare before/after objects and append one result line.

usage: python3 -I snap_record.py <unit_id> <change_idx> <before.json> <after.json> <result> <detail> [new_entity_ids]
For results without a write (AlreadyFixed / Skipped / NotAttempted / blocked Failed) pass the before file as <after.json>.
"""
import json, sys

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = BASE + '/apply6/in_snapchat_2.json'
OUT = BASE + '/apply6/out_snapchat_2.jsonl'
VOLATILE = {'updated_at', 'review_status', 'review_status_details', 'semantic_id'}


def main():
    uid, idx, bf, af, result, detail = sys.argv[1:7]
    new_ids = sys.argv[7] if len(sys.argv) > 7 else ''
    idx = int(idx)
    u = [x for x in json.load(open(INP)) if x['unit'] == uid][0]
    ch = u['changes'][idx]
    b = json.load(open(bf))
    a = json.load(open(af))
    before = b['web_view_properties']['url']
    after = a['web_view_properties']['url']
    diffs = []
    for k in sorted(set(a) | set(b)):
        if k in VOLATILE:
            continue
        if k == 'web_view_properties':
            wa = dict(a.get(k) or {}); wb = dict(b.get(k) or {})
            wa.pop('url', None); wb.pop('url', None)
            if wa != wb:
                diffs.append('web_view_properties(other than url)')
            continue
        if a.get(k, '<missing>') != b.get(k, '<missing>'):
            diffs.append(k)
    print('before == now:', before == ch['now'], '| before in alt_now:', before in ch['alt_now'], '| before == new:', before == ch['new'])
    print('after == new (byte for byte):', after == ch['new'])
    print('non-volatile field diffs:', diffs or 'none')
    print('review_status before -> after:', b.get('review_status'), '->', a.get('review_status'))
    if result == 'Fixed' and after != ch['new']:
        print('REFUSED: result Fixed but read-back != new')
        sys.exit(1)
    if result == 'Fixed' and diffs:
        print('REFUSED: unexpected field changes; record manually')
        sys.exit(1)
    rec = {"platform": "snapchat", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": uid,
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'], "before": before,
           "after_expected": ch['new'], "after_live": after, "result": result, "new_entity_ids": new_ids,
           "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('recorded', uid, idx, result)


main()
