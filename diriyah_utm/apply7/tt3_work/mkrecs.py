# usage: python3 -I mkrecs.py <pre_read_files> <mode> <ad_id> ...   mode = already | notattempted
# Prints result records (one JSON line each) built from decisions.json and the pre-read; does not write any file.
import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt3_work')
from common import *
pre={}
for fn in sys.argv[1].split(','):
    m,rid=load_list(fn if fn.startswith('/') else T+fn); pre.update(m)
mode=sys.argv[2]
D=json.load(open(T+'decisions.json'))
OUTAGE=("TikTok API outage at the time of this run: every live ad/update in this lane failed upstream (unit 1814445683228689: Whathead 'tiktok API request timed out after 40000ms', "
        "then TikTok 51002 'Internal service connection timeout' req 20261013060938F82040F02278049E347D; unit 1814418146114561: TikTok 51002 req 2026101306124234A6E2A3432D66369893), "
        "lanes tiktok_1 and tiktok_2 failed their first writes the same way, and ad/get and pixel/list were also returning 51002/51010; this lane was stopped to avoid hammering the API")
for ad in sys.argv[3:]:
    u=INPD[ad]; ch=u['changes'][0]; d=D[ad]; a=pre[ad]
    ub=[k for k,v in d['utm_before']]
    if d['cls']=='CUSTOMIZED_USER':
        desc=(f"CUSTOMIZED_USER manual {d['ad_format']} (identity {d['identity_id']}, no tiktok_item_id), adgroup {d['adgroup_id']}, video_id {d['video_id']}, "
              f"{len(d['image_ids'] or [])} image, CTA {d['cta']}")
    else:
        desc=(f"{d['ad_format']}, BC_AUTH_TT identity {d['identity_id']} / BC {d['bc']}, no tiktok_item_id (not a post, so not a Spark Push hold), adgroup {d['adgroup_id']}, "
              f"music_id {d['music_id']}, {len(d['image_ids'] or [])} image, {d['cta_kind']} {d['cta']}, dark_post {d['dark_post']}, enhancement list {d['enh']}")
    tn=d['text']
    st=f"{d['op']} / {d['sec']}; modify_time {d['modify_time']}"
    if mode=='already':
        ok = equiv(d['cur'],ch['new']) and a['landing_page_url']==ch['new']
        assert ok
        up=[(x['key'],x['value']) for x in (a.get('utm_params') or [])]
        q=[(x['key'],x['value']) for x in utm_from(ch['new'])]
        detail=(f"Pre-read ad/get req {d['rid']}: landing_page_url == new byte for byte; utm_params {len(up)} keys "
                f"{'== the UTMs of new' if sorted(up)==sorted(q) else 'DIFFER from new'}{' (no utm_id)' if 'utm_id' not in [k for k,v in up] else ' WITH utm_id'}; no write. "
                f"{desc}; {st}. The 12-Oct apply6 run (tt9) had prepared this write at 14:24 UTC and was stopped at the sign-in prompt with no result line; its 14:24:47 UTC read still showed the old URL, so that write landed after it.")
        rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],
             "before":d['cur'],"after_expected":ch['new'],"after_live":a['landing_page_url'],"result":"AlreadyFixed","new_entity_ids":"","detail":detail}
    else:
        assert d['decision']=='Write' and d['cur']==ch['now']
        extra=''
        if tn['trailing_ws']: extra+=" ad_text ends with a trailing space (the gateway trims it; accepted by the user, would be noted as 'ad_text trailing space trimmed by gateway')."
        detail=(f"Not attempted: {OUTAGE}. Pre-read ad/get req {d['rid']}: landing_page_url == now byte for byte ({desc}; utm_params {len(ub)} keys {ub}, no utm_id; {st}). "
                f"Full ad/update payload built and checked (every creative field as read, only landing_page_url = new and utm_params = the UTMs of new, no utm_id; pixel as exact string 7347671240183693330), "
                f"but no dry run or live write was sent.{extra} Safe to re-run later with the same recipe.")
        rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],
             "before":d['cur'],"after_expected":ch['new'],"after_live":d['cur'],"result":"NotAttempted","new_entity_ids":"","detail":detail}
    print(json.dumps(rec,ensure_ascii=False))
