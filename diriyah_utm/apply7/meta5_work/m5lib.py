import json, copy, re, os
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_5.json'
OUT = ROOT + '/apply7/out_meta_5.jsonl'
W = ROOT + '/apply7/meta5_work/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'

DOF_83 = """adapt_to_placement add_text_overlay ads_with_benefits advantage_plus_creative app_highlights audio
auto_promotion_tag biz_ai carousel_to_video catalog_feed_tag creative_stickers customize_product_recommendation
cv_transformation description_automation dha_optimization dynamic_cta_text dynamic_partner_content
enable_ncs_testimonials enhance_cta fb_feed_tag fb_reels_tag fb_story_tag feed_caption_optimization generate_cta
hide_price hyperlink_formatting ig_feed_tag ig_glados_feed ig_reels_tag ig_stream_tag ig_video_native_subtitle
image_animation image_auto_crop image_background_gen image_banner image_brightness_and_contrast image_end_card
image_enhancement image_templates image_text_translation image_touchups image_uncrop inline_comment
local_store_extension media_liquidity_animated_image media_order media_type_automation multi_creative_post_carousel
multi_photo_to_video music_generation pac_genai_recomposition pac_recomposition pac_relaxation product_browsing
product_extensions product_metadata_automation product_tags profile_card profile_extension replace_media_text
reveal_details_over_time show_destination_blurbs show_summary site_extensions standard_enhancements_catalog
text_extraction_for_headline text_extraction_for_tap_target text_formatting_optimization text_generation
text_optimizations text_overlay_translation text_translation translate_voiceover video_auto_crop video_filtering
video_highlight video_highlights video_to_image video_uncrop video_uncrop_9x16_to_9x18 video_voiceover
wa_mm_image_filtering wa_mm_text_truncation_length""".split()
assert len(DOF_83) == 83 and len(set(DOF_83)) == 83


def dof_all_optout():
    return {"creative_features_spec": {n: {"enroll_status": "OPT_OUT"} for n in DOF_83}}


def units():
    return json.load(open(IN))


def unit(ad_id):
    for u in units():
        if u['unit'] == ad_id:
            return u
    raise KeyError(ad_id)


def excluded(ad_id, slot):
    for x in json.load(open(EXCL)):
        if str(x.get('ad_id')) == str(ad_id) and x.get('slot') == slot:
            return True
    return False


def same_url(a, b):
    """same scheme/host/path/fragment and the same query params in any order"""
    if a is None or b is None:
        return False
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def _walk(obj, part):
    m = re.fullmatch(r'(\w+)\[(\d+)\]', part)
    if m:
        return obj[m.group(1)][int(m.group(2))]
    return obj[part]


def get_slot(creative, slot):
    assert slot.startswith('creative.')
    cur = creative
    for part in slot[len('creative.'):].split('.'):
        cur = _walk(cur, part)
    return cur


def set_slot(creative, slot, value):
    parts = slot[len('creative.'):].split('.')
    cur = creative
    for part in parts[:-1]:
        cur = _walk(cur, part)
    last = parts[-1]
    m = re.fullmatch(r'(\w+)\[(\d+)\]', last)
    if m:
        cur[m.group(1)][int(m.group(2))] = value
    else:
        assert last in cur, (slot, 'missing leaf')
        cur[last] = value


def full_url(creative, slot):
    """landing URL incl. url_tags if any"""
    v = get_slot(creative, slot)
    tags = creative.get('url_tags')
    if tags:
        v = v + ('&' if '?' in v else '?') + tags
    return v


def classify(u, creative):
    res = []
    for c in u['changes']:
        try:
            cur = full_url(creative, c['slot'])
        except Exception:
            cur = None
        if cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in c['alt_now']:
            v = 'Write'
        else:
            v = 'Skipped'
        res.append((c, cur, v))
    return res


def diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f'+ {path}.{k} = {json.dumps(b[k], ensure_ascii=False)[:300]}')
            elif k not in b:
                out.append(f'- {path}.{k} = {json.dumps(a[k], ensure_ascii=False)[:300]}')
            else:
                out += diff(a[k], b[k], f'{path}.{k}')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f'~ {path} len {len(a)} -> {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f'{path}[{i}]')
    else:
        if a != b:
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:300]} -> {json.dumps(b, ensure_ascii=False)[:300]}')
    return out


def load_persisted(path):
    blocks = json.load(open(path))
    txt = ''.join(b['text'] for b in blocks if b.get('type') == 'text')
    return json.loads(txt)


def has_trunc(o):
    if isinstance(o, dict):
        return any('mcp_trunc' in k.lower() for k in o) or any(has_trunc(v) for v in o.values())
    if isinstance(o, list):
        return any(has_trunc(v) for v in o)
    if isinstance(o, str):
        return 'TRUNCATED' in o or 'more items truncated' in o
    return False


def check_dof(creative):
    """True when the creative's DOF spec is exactly the 83 features all OPT_OUT (only other key allowed: none)"""
    d = creative.get('degrees_of_freedom_spec')
    return d == dof_all_optout()


# derived / read-only top-level fields that are not sent on create
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash',
            'call_to_action', 'call_to_action_type', 'image_crops', 'instagram_user_id', 'video_id',
            'object_story_id', 'effective_authorization_category', 'enable_direct_install',
            'enable_launch_instant_app', 'instagram_permalink_url', 'thumbnail_id'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
            'creative_sourcing_spec', 'media_sourcing_spec', 'format_transformation_spec', 'threads_user_id',
            'authorization_category', 'portrait_customizations', 'url_tags', 'source_instagram_media_id',
            'platform_customizations', 'branded_content', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'link_destination_display_url', 'page_welcome_message', 'applink_treatment',
            'interactive_components_spec', 'template_url', 'product_set_id', 'recommender_settings',
            'facebook_branded_content', 'instagram_branded_content', 'bundle_folder_id',
            'categorization_criteria', 'place_page_set_id', 'object_id', 'link_url', 'object_url']


def build_payload(creative, changes):
    unknown = [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP]
    assert not unknown, ('unhandled creative fields', unknown)
    assert not creative.get('url_tags'), 'creative has url_tags - handle by hand'
    p = {}
    for k in KEEP_TOP:
        if k in creative:
            p[k] = copy.deepcopy(creative[k])
    vd = p.get('object_story_spec', {}).get('video_data')
    if vd and 'image_hash' in vd:
        vd.pop('image_url', None)  # Meta returns both; only one may be sent
    view = {'object_story_spec': p.get('object_story_spec'), 'asset_feed_spec': p.get('asset_feed_spec')}
    for ch in changes:
        old = get_slot(view, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(view, ch['slot'], ch['new'])
    return p


IGNORE_DERIVED = ('.id', '.name', '.effective_object_story_id', '.effective_instagram_media_id',
                  '.instagram_permalink_url', '.thumbnail_id', '.video_id', '.status')


def compare_creatives(old, new, changes):
    """expected: new == old with only the slot(s) changed (+ derived ids). Returns unexpected diff lines."""
    exp = copy.deepcopy(old)
    for ch in changes:
        set_slot(exp, ch['slot'], ch['new'])
        # top-level mirrors of the video CTA link
        if ch['slot'] == 'creative.object_story_spec.video_data.call_to_action.value.link' and 'call_to_action' in exp:
            exp['call_to_action']['value']['link'] = ch['new']
    out = []
    for line in diff(exp, new):
        path = line[2:].split(' ')[0].rstrip(':')
        if path in IGNORE_DERIVED:
            continue
        if path.endswith('.image_url') or '.site_link_image_url' in path:
            continue  # signed CDN URLs regenerate on every read
        out.append(line)
    return out


def record(ad_id, change_idx, before, after_live, result, new_ids, detail):
    u = unit(ad_id)
    c = u['changes'][change_idx]
    if result == 'Fixed':
        assert after_live == c['new'], 'after mismatch'
        assert before == c['now'] or before in c['alt_now'], 'before not now/alt_now'
    if result == 'AlreadyFixed':
        assert same_url(before, c['new'])
    rec = {"platform": "meta", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
           "after_expected": c['new'], "after_live": after_live, "result": result,
           "new_entity_ids": new_ids, "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print('recorded', ad_id, c['slot'], result, 'after==new:', after_live == c['new'])
