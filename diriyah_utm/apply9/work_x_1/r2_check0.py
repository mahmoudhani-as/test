import json
IN='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/in_x_1.json'
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_x_1'
u=json.load(open(IN))[0]
ch=u['changes'][0]
live="https://www.diriyah.sa/ar?utm_source=x&utm_medium=paid-social&utm_campaign=4ae01e79_summer-campaign_aug26_awr&utm_term=ar&utm_content=video_ar"
print('live==new exact:', live==ch['new'], '| live==now:', live==ch['now'], '| live in alt_now:', live in ch['alt_now'])
json.dump({'unit':u['unit'],'get_req':'72f47e39-1040-426b-8da3-58ef510aa682','slot':ch['slot'],'cur':live,'cur_eq_new':live==ch['new'],'updated_at':'2026-08-11T12:59:49Z','card_type':'VIDEO_WEBSITE','deleted':False}, open(W+'/r2_pre_0.json','w'), ensure_ascii=False)
# account id decode check
def b36(s): return int(s,36)
for a in ['18ce55o46uh','18ce55o46ul']: print(a, b36(a))
for t in ['2087162068705103873','2087162070911369492','2095131822749524008','2095139956872167629','2095139958206177684']:
    import datetime
    ms=(int(t)>>22)+1288834974657
    print(t, datetime.datetime.utcfromtimestamp(ms/1000).isoformat())
