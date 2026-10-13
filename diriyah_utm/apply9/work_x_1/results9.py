# apply9 in_x_1: prints the final results array (stdout only; writes no file).
import json

W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_x_1'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/in_x_1.json'
units = json.load(open(IN, encoding='utf-8'))
post0 = json.load(open(f'{W}/post_0.json', encoding='utf-8'))
pre0 = json.load(open(f'{W}/pre_0.json', encoding='utf-8'))
share = json.load(open(f'{W}/share_check.json', encoding='utf-8'))

nf = {
    '2095131822749524008': ('f5e797ea-6394-4a0f-a731-26079e5384b2', 'd1def1a3-c642-4b3c-aa0d-0e7b5a9a2833'),
    '2095139956872167629': ('f8e0d165-d4eb-4721-98c5-3661de36e81b', '07542f75-ea08-4e7c-994f-fb797da40e94'),
    '2095139958206177684': ('086df080-f651-47ba-84c5-8409fa2ffbda', '01062cb8-e53f-4e61-a3ad-a3adf4a8c18a'),
}

out = []
for i, u in enumerate(units):
    for ch in u['changes']:
        r = {'platform': u['platform'], 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'],
             'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': ch['slot'], 'after_expected': ch['new'], 'new_entity_ids': ''}
        if i == 0:
            line = [l for l in post0['lines'] if l['slot'] == ch['slot']][0]
            assert line['before'] == pre0['status'][ch['slot']]['cur']
            assert line['after_expected'] == ch['new']
            r['before'] = line['before']
            r['after_live'] = line['after_live']
            r['result'] = line['result']
            sc = share['18ce55o46uh']
            c = sc['cards'][u['unit']]
            r['detail'] = (
                f"Card {u['unit']} ({pre0['card_before']['card_type']}, no experiment_signals as read) on tweet {c['tweets'][0]}, "
                f"promoted only by {u['ad_ids'][0]} (line item {c['promoted'][0][3]}); live share check LIST_PROMOTED_TWEETS req {sc['promoted_req']} "
                f"(200 newest by created_at, back to 2025-12-11, before the card's 2026-08-11 creation) + LIST_TWEETS req {sc['tweets_req']} "
                f"(all 11 tweets newer than the card read; only this tweet carries card://{u['unit']}); no link in the tweet text. "
                f"Pre-read GET_CARD req {pre0['get_req']}: slot == now byte for byte. "
                f"UPDATE_CARD PUT /12/accounts/{u['account_id']}/cards/{u['unit']}: dry run req 4336b3a5-8ace-4f64-8757-9c16f8486305 "
                f"(body = name + components as read without read-only media_metadata, only components[1].destination.url changed; gateway echo == expected body) "
                f"-> live req {post0['write_req']} (idempotency_key a9131000-0000-4000-8000-000000000000, 1 attempt) "
                f"-> read-back GET_CARD req {post0['get_req']}: url == new byte for byte; all other card fields unchanged "
                f"(name, media_key, title, destination type, card_type; updated_at {post0['after'].get('updated_at')})."
            )
        else:
            a, b = nf[u['unit']]
            r['before'] = ''
            r['after_live'] = ''
            r['result'] = 'Skipped'
            r['detail'] = (
                f"changed since plan: card {u['unit']} is not found in account {u['account_id']}, so the live slot could not be read "
                f"(pre-read GET_CARD req {a}: 404 NOT_FOUND 'Card {u['unit']} was not found for Account 4503599737345965'; "
                f"re-read with with_deleted=true req {b}: same 404). It matches none of now / alt_now / new, so NO write was made "
                f"(no dry run, no live call). No other card or tweet was looked up or touched (a different card would not be in the input). "
                f"Separately, a local read-only Bash lookup of earlier run files for this account's three units was denied by the session "
                f"safety check ('Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Real-World Transactions].'); "
                f"it was not repeated or re-routed and the decision did not depend on it."
            )
        out.append(r)

print(json.dumps(out, ensure_ascii=False, indent=1))
print('COUNT', len(out), sum(len(u['changes']) for u in units))
