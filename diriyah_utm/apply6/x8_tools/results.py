# Append result lines for one unit of in_x_8 to out_x_8.jsonl.
# Usage: results.py <unit_idx> <kind> [dry_rid] [live_rid] [extra detail]
#   kind = written   -> uses pre_<i>.json + post_<i>.json (Fixed/Failed per slot; Already/Skipped slots as such)
#   kind = nowrite   -> uses pre_<i>.json only (AlreadyFixed / Skipped)
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x8_tools')
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x8_work'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_x_8.json'
OUT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_x_8.jsonl'

SHARE = ('card used only by this unit: live LIST_PROMOTED_TWEETS with_deleted (sorted created_at-desc, paged back past the '
         'earliest card in this batch, 2025-12-16T14:46Z) shows no other promoted tweet on this tweet, and live LIST_TWEETS card_uri '
         'of all 146 other tweets behind promoted tweets created since then shows none carries this card; tweet text has no URLs.')


def main():
    i = int(sys.argv[1]); kind = sys.argv[2]
    dry = sys.argv[3] if len(sys.argv) > 3 else ''
    live = sys.argv[4] if len(sys.argv) > 4 else ''
    extra = sys.argv[5] if len(sys.argv) > 5 else ''
    u = json.load(open(IN))[i]
    m = json.load(open(W + '/map.json'))
    pt = u['ad_ids'][0]
    pre = json.load(open(W + '/pre_%d.json' % i))
    card = pre['card_before']
    post = json.load(open(W + '/post_%d.json' % i)) if kind == 'written' else None
    nslots_written = sum(1 for s in pre['status'].values() if s['st'].startswith('WRITE'))
    head = ('X card %s (%s, deleted=%s) behind promoted tweet %s -> tweet %s, line item %s; pre-read GET_CARD req %s. '
            % (pre['card_id'], card['card_type'], card['deleted'], pt, u['unit'], m[pt]['line_item_id'], pre['get_rid']))
    es = card.get('experiment_signals')
    es_txt = ('experiment_signals carried as read: %s. ' % json.dumps(es)) if es else 'no experiment_signals on the card as read (nothing to carry). '
    lines = []
    for c in u['changes']:
        slot = c['slot']
        s = pre['status'][slot]
        cur = s['cur']
        row = {'platform': 'x', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'],
               'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': slot, 'before': cur,
               'after_expected': c['new'], 'after_live': cur, 'result': '', 'new_entity_ids': '', 'detail': ''}
        if s['st'] == 'ALREADY':
            row['result'] = 'AlreadyFixed'
            row['detail'] = 'No write made for this slot: live value already equals new%s. ' % ('' if cur == c['new'] else ' (same params, different order)') + head + SHARE
        elif s['st'] == 'CHANGED':
            row['result'] = 'Skipped'
            row['detail'] = 'changed since plan: ' + cur + ' | ' + head
        elif s['st'] == 'EXCLUDED':
            row['result'] = 'Skipped'
            row['detail'] = 'slot listed in excl_platform_refused_v2.json; not written. ' + head
        elif s['st'].startswith('WRITE'):
            assert kind == 'written'
            live_v = post['slots'][slot]['after_live']
            row['after_live'] = live_v
            ok = post['slots'][slot]['eq_new_bytes']
            row['result'] = 'Fixed' if ok else 'Failed'
            row['detail'] = ('UPDATE_CARD PUT /12/accounts/%s/cards/%s %s: before equalled %s byte for byte; dry-run req %s preview body = '
                             'name + %s as read (read-only media_metadata not sent) with only the %d listed destination url(s) set to new; '
                             'live req %s (idempotency key) OK; independent GET_CARD re-read req %s: this slot %s new byte for byte; '
                             'card otherwise identical to the pre-read (name, card_type, media keys, titles, destination types, deleted=false, '
                             'created_at%s). %s%s%s'
                             % (u['account_id'], pre['card_id'], 'OK' if ok else 'returned but read-back differs',
                                "'now'" if s['match'] == 'now' else ("an 'alt_now' value" if s['match'] == 'alt_now' else 'now/alt_now (param order differs)'),
                                dry, 'slides' if 'slides' in card else 'components', nslots_written, live, post['post_rid'],
                                'equals' if ok else 'DOES NOT equal',
                                '' if post['rest_unchanged'] else ' -- NOTE: other differences seen, see work file post_%d.json' % i,
                                es_txt, head, SHARE))
            if extra:
                row['detail'] += ' ' + extra
        else:
            raise SystemExit('unknown status ' + s['st'])
        lines.append(row)
    with open(OUT, 'a', encoding='utf-8') as f:
        for r in lines:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    for r in lines:
        print(r['slot'], r['result'])


if __name__ == '__main__':
    main()
