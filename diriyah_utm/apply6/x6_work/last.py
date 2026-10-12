# print the tool_use id of the most recent x_ads_native_action call with the given action
import sys, json
exec(open('/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x6_work/tr.py').read().split("if __name__")[0])
calls, order, results = load()
act=sys.argv[1]
ids=[i for i in order if calls[i][0].endswith('x_ads_native_action') and calls[i][1].get('action')==act]
print(ids[-1])
