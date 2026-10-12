import json, copy, sys, unicodedata
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/meta16_work')
from lib import *

# fields copied as-is from the read creative (creation params); everything else is read-only/derived
COPY_KEYS = ['asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads', 'creative_sourcing_spec',
             'media_sourcing_spec', 'format_transformation_spec', 'portrait_customizations', 'threads_user_id',
             'authorization_category', 'url_tags', 'source_instagram_media_id', 'platform_customizations',
             'interactive_components_spec', 'regional_regulation_disclaimer_spec', 'ad_disclaimer_spec',
             'applink_treatment', 'branded_content', 'branded_content_sponsor_page_id', 'product_set_id',
             'template_url', 'template_url_spec', 'page_welcome_message', 'destination_set_id', 'dynamic_ad_voice',
             'place_page_set_id', 'playable_asset_id', 'recommender_settings', 'bundle_folder_id',
             'categorization_criteria', 'category_media_source', 'facebook_branded_content',
             'photo_album_source_object_story_id', 'collaborative_ads_lsb_image_bank_id', 'link_og_id']
# read-only / derived fields that are deliberately not sent
DERIVED = {'id', 'account_id', 'actor_id', 'status', 'object_type', 'body', 'title', 'call_to_action',
           'call_to_action_type', 'effective_authorization_category', 'effective_instagram_media_id',
           'effective_object_story_id', 'instagram_permalink_url', 'thumbnail_url', 'image_url', 'image_hash',
           'image_crops', 'video_id', 'instagram_user_id', 'use_page_actor_override', 'enable_direct_install',
           'enable_launch_instant_app', 'name', 'object_story_spec', 'link_url', 'object_url', 'object_id',
           'object_story_id', 'link_destination_display_url', 'adlabels'}


def build(ad_id, creative):
    u = unit(ad_id)
    p = {'name': creative['name']}
    if 'object_story_spec' in creative:
        p['object_story_spec'] = copy.deepcopy(creative['object_story_spec'])
    for k in COPY_KEYS:
        if k in creative:
            p[k] = copy.deepcopy(creative[k])
    unknown = [k for k in creative if k not in COPY_KEYS and k not in DERIVED]
    if unknown:
        raise SystemExit('unknown creative keys, review needed: %s' % unknown)
    dof = p.get('degrees_of_freedom_spec', {}).get('creative_features_spec', {})
    if 'standard_enhancements' in dof:
        raise SystemExit('standard_enhancements present - review')
    # change only the listed slots
    wrap = {'creative': p}
    for c in u['changes']:
        set_slot(p, c['slot'], c['new'])
    return p


def esc_dump(obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if (cat in ('Cf', 'Cc', 'Zl', 'Zp', 'Mn', 'Co', 'Cs') or (cat == 'Zs' and ch != ' ')) and ch not in '\n':
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    return ''.join(out)


def check(ad_id, creative, p):
    """verify payload == creative except listed slots"""
    u = unit(ad_id)
    orig = {'name': creative['name']}
    if 'object_story_spec' in creative:
        orig['object_story_spec'] = creative['object_story_spec']
    for k in COPY_KEYS:
        if k in creative:
            orig[k] = creative[k]
    d = diff(orig, p)
    slots = ['.' + c['slot'][len('creative.'):] for c in u['changes']]
    unexpected = [x for x in d if not any(x.startswith('~ ' + s + ':') for s in slots)]
    return d, unexpected
