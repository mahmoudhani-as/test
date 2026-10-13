import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/meta4_work')
from lib import *
from dof83 import dof_all_optout

# top-level creative fields that are copied as-is on create (others in the raw read are derived/read-only)
COPY = ['name', 'object_story_spec', 'asset_feed_spec', 'creative_sourcing_spec', 'media_sourcing_spec', 'format_transformation_spec',
        'portrait_customizations', 'threads_user_id', 'url_tags', 'authorization_category', 'contextual_multi_ads',
        'platform_customizations', 'interactive_components_spec', 'source_instagram_media_id', 'branded_content',
        'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec', 'link_destination_display_url', 'applink_treatment',
        'page_welcome_message', 'product_set_id', 'template_url']
DERIVED = ['id', 'body', 'title', 'call_to_action', 'instagram_user_id', 'object_type', 'use_page_actor_override',
           'effective_authorization_category', 'video_id', 'image_hash', 'link_url', 'object_url']


def build(ad_id, raw_file, cl):
    raw, _ = load_raw(W + raw_file, cl)
    unknown = [k for k in raw if k not in COPY and k not in DERIVED]
    assert not unknown, ('unhandled fields', unknown)
    u = unit(ad_id)
    for c, cur, v in classify(u, raw):
        print(v, c['slot'], '| cur==now:', cur == c['now'])
        assert v == 'Write', v
    p = {k: copy.deepcopy(raw[k]) for k in COPY if k in raw}
    # video_data: a signed image_url is regenerated on each read; send image_hash when present
    vd = p.get('object_story_spec', {}).get('video_data')
    if vd and 'image_hash' in vd and 'image_url' in vd:
        vd.pop('image_url')
    for c in u['changes']:
        set_slot(p, c['slot'], c['new'])
    p['degrees_of_freedom_spec'] = dof_all_optout()
    print('invisible chars in payload:', invisible(p))
    # diff vs the original (for the copied fields)
    o = {k: raw[k] for k in p if k in raw}
    o['degrees_of_freedom_spec'] = dof_all_optout()
    for l in diff(o, p):
        print('  diff', l[:160])
    json.dump(p, open(W + 'payload_%s.json' % ad_id, 'w'), ensure_ascii=False, indent=1)
    print('PAYLOAD_ASCII', json.dumps(p, ensure_ascii=True))
    return raw, p


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], int(sys.argv[3]))
