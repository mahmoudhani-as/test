# ids.py <action> <card_id> [dry|live] -> latest matching x_ads_native_action tool_use id
import sys, json
exec(open('/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x6_work/tr.py').read().split("if __name__")[0])
calls, order, results = load()
act, cid = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv)>3 else None
ids=[]
for i in order:
    n, inp = calls[i]
    if not n.endswith('x_ads_native_action') or inp.get('action')!=act: continue
    if (inp.get('path_params') or {}).get('card_id')!=cid: continue
    if mode=='dry' and inp.get('dry_run') is not True: continue
    if mode=='live' and inp.get('dry_run') is not False: continue
    if i not in results: continue
    ids.append(i)
print(ids[-1] if ids else 'NONE')
