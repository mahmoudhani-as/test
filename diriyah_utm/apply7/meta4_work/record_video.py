import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/meta4_work')
from lib import *

# usage: record_video.py ad_id orig_file orig_cl new_file new_cl ad_after_file preread_utc attempt
ad_id, orig_file, orig_cl, new_file, new_cl, ad_file, pre_utc, attempt = sys.argv[1:9]
orig, _ = load_raw(W + orig_file, int(orig_cl))
newc, _ = load_raw(W + new_file, int(new_cl))
ad = json.load(open(W + ad_file))
u = unit(ad_id)
assert len(u['changes']) == 1
c = u['changes'][0]
after_ad = full_url(ad['creative'], c['slot'])
after_cr = get_slot(newc, c['slot'])
before = get_slot(orig, c['slot'])
ok = after_ad == c['new'] and after_cr == c['new'] and ad['creative']['id'] == newc['id'] and before == c['now'] and not ad['creative'].get('url_tags')
print('ad read-back == new:', after_ad == c['new'], '| creative read-back == new:', after_cr == c['new'], '| creative id ok:', ad['creative']['id'] == newc['id'], '| before==now:', before == c['now'])
assert ok
vd = orig['object_story_spec']['video_data']
extras = []
if 'media_sourcing_spec' in orig:
    extras.append('media_sourcing_spec title')
detail = ("Pre-read 12-Oct %s UTC (raw Graph batch GET; transcribed body = Content-Length %s bytes): ad status %s (pre-read %s) on creative %s (= plan), no url_tags, slot equalled plan 'now'. "
          "Exact copy built by script (object_story_spec page %s / IG %s, video_data video_id %s, title and message as read, image_hash %s (the signed image_url is derived from it and was not sent), "
          "CTA %s with link_format %s; %screative_sourcing_spec destination_screenshot OPT_OUT; degrees_of_freedom_spec 83 features all OPT_OUT as read; threads_user_id; same name) with only the CTA link set to 'new'. "
          "Dry-run preview checked; live create attempt %s of 2 created %s. Read back (raw batch GET, Content-Length %s; degrees_of_freedom_spec 4133 = original) and compared by script: identical except the link, the id, "
          "Meta's name-dedupe suffix (name now '%s') and Meta-derived read-only fields: %sa re-signed video_data.image_url for the same image_hash, top-level read-only video_id now %s (was %s on the old creative; the spec video_id %s is unchanged). "
          "Ad POST /%s creative={creative_id:%s} success=true; status not sent. Read-back: ad creative %s, status/configured_status %s (unchanged), effective_status %s (re-review; was %s); slot equals 'new' byte for byte.") % (
    pre_utc, orig_cl, ad['configured_status'], u.get('status_11oct'), orig['id'],
    orig['object_story_spec']['page_id'], orig['object_story_spec']['instagram_user_id'], vd['video_id'], vd.get('image_hash'),
    vd['call_to_action']['type'], vd['call_to_action']['value'].get('link_format'), (', '.join(extras) + '; ') if extras else '',
    attempt, newc['id'], new_cl, newc['name'][-60:], ('link_url (= new link), ' if newc.get('link_url') == c['new'] else ''), newc.get('video_id'), orig.get('video_id'), vd['video_id'],
    ad_id, newc['id'], ad['creative']['id'], ad['configured_status'], ad['effective_status'], u.get('status_11oct'))
record(ad_id, 0, before, after_ad, 'Fixed', 'creative:%s' % newc['id'], detail)
progress(ad=ad_id, new_creative=newc['id'], step='verified+recorded Fixed')
