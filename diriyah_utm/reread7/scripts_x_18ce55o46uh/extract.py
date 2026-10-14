# Extract this agent's own x_ads_native_action GET results (14-Oct-2026 re-read of X 18ce55o46uh)
# from its transcript into reread7/work_x_18ce55o46uh/raw/<action>.json, and print a summary.
import json, os, sys

T = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
     'wf_ce5fc811-84b/agent-a1e47ebfd4017713c.jsonl')
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread7/work_x_18ce55o46uh'
OUT = os.path.join(W, 'raw')
WANT = {
    'x_accounts_account_id_promoted_tweets_get': 'promoted_tweets',
    'x_accounts_account_id_tweets_get': 'tweets',
    'x_accounts_account_id_cards_get': 'cards',
    'x_accounts_account_id_line_items_get': 'line_items',
    'x_accounts_account_id_campaigns_get': 'campaigns',
}
uses, results, order = {}, {}, []
for line in open(T, encoding='utf-8'):
    try:
        o = json.loads(line)
    except Exception:
        continue
    c = (o.get('message') or {}).get('content')
    if not isinstance(c, list):
        continue
    for p in c:
        if not isinstance(p, dict):
            continue
        if p.get('type') == 'tool_use' and (p.get('name') or '').endswith('x_ads_native_action'):
            if p['id'] not in uses:
                uses[p['id']] = p.get('input') or {}
                order.append(p['id'])
        elif p.get('type') == 'tool_result' and p.get('tool_use_id') in uses:
            cc = p.get('content')
            txt = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else cc
            results[p['tool_use_id']] = txt

os.makedirs(OUT, exist_ok=True)
saved = {}
for i in order:
    inp = uses[i]
    act = inp.get('action')
    if act not in WANT or i not in results:
        continue
    res = json.loads(results[i])  # small results came back inline as JSON text
    assert res.get('success') is True and res['data'].get('success') is True, (act, str(res)[:500])
    inner = res['data']['data']
    assert inner.get('next_cursor') in (None, ''), (act, 'pagination left', inner.get('next_cursor'))
    label = WANT[act]
    saved.setdefault(label, []).append({'tool_use_id': i, 'input': inp, 'request_id': res.get('meta', {}).get('requestId'),
                                        'data': inner.get('data'), 'total_count': inner.get('total_count')})
for label, calls in saved.items():
    json.dump(calls, open(os.path.join(OUT, label + '.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(label, 'calls=', len(calls), 'items=', [len(c['data']) for c in calls],
          'total_count=', [c['total_count'] for c in calls], 'req=', [c['request_id'] for c in calls])
missing = set(WANT.values()) - set(saved)
if missing:
    sys.exit('missing results: %s' % sorted(missing))
