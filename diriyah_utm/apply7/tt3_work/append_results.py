# usage: python3 -I append_results.py [--print]
# Builds the remaining result lines of this lane and appends them to apply7/out_tiktok_3.jsonl (unless --print):
#   1814418146114561 Failed (1 live attempt, TikTok 51002, read-back unchanged), 1814418145780737 AlreadyFixed,
#   and NotAttempted for the 17 units not tried after the TikTok write outage stopped the lane.
import json, sys, subprocess
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt3_work')
from common import *

done=set()
for l in open(OUT,encoding='utf-8'):
    l=l.strip()
    if l: done.add(json.loads(l)['unit'])

recs=[]
# 1) 1814418146114561: one live attempt failed upstream; read-back unchanged
ad='1814418146114561'; u=INPD[ad]; ch=u['changes'][0]
rb,rb_rid=load_list(T+'read_20261013061353DED6A7B6622FD8B5ACAF.json')
a=rb[ad]; pre,_=load_list(T+'pre_read_1.json'); p=pre[ad]
assert a['landing_page_url']==ch['now'] and p['landing_page_url']==ch['now'] and a['modify_time']==p['modify_time']
diffs=[k for k in sorted(set(a)|set(p)) if a.get(k,'<absent>')!=p.get(k,'<absent>')]
assert diffs==[], diffs
recs.append({"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":ad,"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],
  "before":p['landing_page_url'],"after_expected":ch['new'],"after_live":a['landing_page_url'],"result":"Failed","new_entity_ids":"",
  "detail":("Not written: the live ad/update attempt failed on TikTok's side (TikTok API outage, not permission or call shape); ad unchanged. "
            "CUSTOMIZED_USER manual SINGLE_VIDEO ad (identity 7350277519361425409, no tiktok_item_id), adgroup 1813630708433938, video_id v10033g50000csh48ufog65o05r6d5og, 1 image, CTA LEARN_MORE. "
            "Pre-read ad/get req 20261013060316F5B666DED915F3E415AC and fresh re-read req 20261013061206A3ECC617723C49B94853 just before the write: landing_page_url == now byte for byte "
            "(utm_params 4 keys source/medium/campaign/content, no utm_term, no utm_id; ENABLE / AD_STATUS_CAMPAIGN_DISABLE; modify_time 2026-10-12 14:51:42, an ad-group-wide stamp from outside this run). "
            "dry_run OK: call input and preview body == built payload; every creative field as read (ad_name, identity, ad_format, video_id, image_ids, ad_text byte-identical with no edge whitespace, "
            "display_name, avatar, aigc NOT_DECLARED, creative_authorized true, vast_moat false, CTA) with only landing_page_url = new and utm_params = the 5 UTMs of new (no utm_id); "
            "pixel sent as exact string 7347671240183693330. Live attempt 1: TikTok 51002 'Internal service connection timeout. Please try again.' req 2026101306124234A6E2A3432D66369893. "
            "Read-back ad/get req "+rb_rid+" (after two more 51002 read errors): landing_page_url and utm_params still the old values, every field identical to the pre-read, "
            "modify_time unchanged 2026-10-12 14:51:42, status unchanged. Second attempt not used: every TikTok ad/update in this run was failing upstream (0 of 13 across the TikTok lanes "
            "per lane tiktok_4), so this lane was stopped to avoid hammering the API. Safe to re-run later with the same payload.")})

# 2) AlreadyFixed + NotAttempted from the generator (stdout only)
def gen(mode, ads):
    r=subprocess.run(['python3','-I',T+'mkrecs.py','pre_read_1.json,pre_read_2.json',mode]+ads,check=True,capture_output=True,text=True,cwd=T)
    return [json.loads(x) for x in r.stdout.splitlines() if x.strip()]
recs+=gen('already',['1814418145780737'])
NA=['1814445680372753','1814445680366609','1814418146108417','1814418146102273','1814418145775681','1814418145769473','1814418145764353',
    '1814418145294337','1814418145289217','1814418145283073','1814418145277953','1814418145271809','1814418143542289','1814418143536193',
    '1814418143531073','1859905652203922','1859903519347842']
recs+=gen('notattempted',NA)

recs=[r for r in recs if r['unit'] not in done]
units=[r['unit'] for r in recs]
assert len(units)==len(set(units))
assert set(units)|done=={u['unit'] for u in INP}, (set(units)|done) ^ {u['unit'] for u in INP}
for r in recs:
    assert r['after_expected']==INPD[r['unit']]['changes'][0]['new']
    assert set(r)=={"platform","account_id","unit_type","unit","ad_ids","ad_names","slot","before","after_expected","after_live","result","new_entity_ids","detail"}
if '--print' in sys.argv:
    for r in recs: print(r['unit'], r['result'], len(r['detail']))
    print(len(recs),'records (not written)')
else:
    append_records(recs)
    print('appended', len(recs))
