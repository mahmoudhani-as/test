# usage: python3 fixrec.py <out_json> <ad_id> [...]  -> builds Fixed records from pre-read, dry/live responses and post-check, after asserting everything matches
import json, sys
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
X=W+'tt6_work2/'
pre=json.load(open(X+'pre_all.json')); pc=json.load(open(X+'postcheck.json')); P=json.load(open(X+'payloads.json'))
inp={u['unit']:u for u in json.load(open(W+'in_tiktok_6.json'))}
out=sys.argv[1]; recs=[]
for ad in sys.argv[2:]:
    a=pre[ad]; p=pc[ad]; new=inp[ad]['changes'][0]['new']; cr=P[ad]['creatives'][0]
    dry=json.load(open(X+f'resp_dry_{ad}.json')); live=json.load(open(X+f'resp_live_{ad}.json'))
    assert dry['data']['data']['request']['body']==P[ad]
    ld=live['data']['data']; assert ld['code']==0 and live['data']['dryRun'] is False
    assert p['url_ok'] and p['utm_ok'] and not p['utm_has_id'] and not p['diffs'] and p['after_live']==new
    up_old=[(x['key'],x['value']) for x in (a.get('utm_params') or [])]
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    it=a['identity_type']
    if it=='CUSTOMIZED_USER':
        kind='CUSTOMIZED_USER manual SINGLE_VIDEO, not a Spark ad, no tiktok_item_id'
        sent='ad_name, identity %s, ad_format, video_id, image_ids, ad_text byte-identical (no trailing space), %s, display_name, avatar, aigc_disclosure_type %s, creative_authorized %s, vast_moat %s%s' % (
            a['identity_id'], ('call_to_action_id '+a['call_to_action_id']) if a.get('call_to_action_id') else ('call_to_action '+a['call_to_action']),
            a['aigc_disclosure_type'], str(a['creative_authorized']).lower(), str(a['vast_moat_enabled']).lower(),
            ''.join(', %s %s' % (k, a[k]) for k in ('vertical_video_strategy','fallback_type','dynamic_destination','shopping_ads_fallback_type') if k in cr))
    else:
        kind='AUTH_CODE Spark Pull ad, identity %s, tiktok_item_id %s (not Spark Push)' % (a['identity_id'], a['tiktok_item_id'])
        sent='ad_name, identity_type AUTH_CODE + identity_id %s + the SAME tiktok_item_id %s (exact strings), ad_format, promotional_music_disabled %s, ad_text byte-identical (no trailing space), call_to_action %s, creative_authorized %s, vast_moat %s; no video_id, no image_ids' % (
            a['identity_id'], a['tiktok_item_id'], str(a['promotional_music_disabled']).lower(), a['call_to_action'], str(a['creative_authorized']).lower(), str(a['vast_moat_enabled']).lower())
    utm_change=[(k,dict(up_old).get(k),v) for k,v in q if dict(up_old).get(k)!=v]
    detail=(f"pre-read ad/get req {a['_req']}: URL == now ({kind}; utm_params {len(up_old)} keys old values{'' if any(k=='utm_term' for k,_ in up_old) else ' (no utm_term key; utm_term only in the URL)'}, no utm_id; status {a['operation_status']} / {a['secondary_status']}). "
            f"dry_run preview body == payload; vs the live ad only landing_page_url and utm_params differ (every other creative field sent as read: {sent}; pixel sent as exact string 7347671240183693330 from pixel/list req 202610122212132E88409C2F319BA417F7). "
            f"Live full ad/update code 0 OK req {ld['request_id']}, need_audit={str(ld['data'].get('need_audit')).lower()}. "
            f"Re-read ad/get req {p['req']}: landing_page_url == new byte for byte; utm_params == the {len(q)} UTMs of new in URL order, no utm_id (changed keys: {'; '.join('%s %s -> %s' % c for c in utm_change)}); every other field identical to the pre-read"
            f"{'; tiktok_item_id unchanged '+str(p['item']) if it=='AUTH_CODE' else ''}; status unchanged ({p['op']} / {p['sec']}); modify_time {p['pre_modify_time']} -> {p['modify_time']}.")
    recs.append({'ad_id':ad,'result':'Fixed','before':a['landing_page_url'],'after_live':p['after_live'],'detail':detail})
json.dump(recs, open(X+out,'w'), ensure_ascii=False, indent=1)
for r in recs: print(r['ad_id'], r['result']); print('  ', r['detail'])
