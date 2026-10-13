"""Builds the final results array (printed to stdout, not saved) from this agent's own transcript."""
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_meta_meta_carousel_no_parent_image_1')
import clib

CALLS = clib.calls()


def whcalls(action, pred):
    out = []
    for cid, name, inp, res in CALLS:
        if 'Whathed' in name and inp.get('action') == action and pred(inp):
            out.append((cid, inp, clib.parse_result(res)))
    return out


def rid(d):
    return (d or {}).get('meta', {}).get('requestId')


results = []
summary = []
for u in clib.units():
    ad_id = u['unit']
    pay = json.load(open(clib.W + 'payload_%s.json' % ad_id))
    ad_reads = whcalls('meta_ad_id_get', lambda i: (i.get('path_params') or {}).get('ad_id') == ad_id)
    pre_ad = ad_reads[0][2]['data']['data']
    post_ad = ad_reads[-1][2]['data']['data']
    cr_reads = whcalls('meta_creative_id_get', lambda i: (i.get('path_params') or {}).get('creative_id') == u['creative_id'])
    orig = cr_reads[-1][2]['data']['data']
    creates = whcalls('meta_ad_account_id_adcreatives_create', lambda i: i.get('payload') == pay)
    dry = [c for c in creates if c[1].get('dry_run')]
    live = [c for c in creates if c[1].get('dry_run') is False]
    assert len(dry) == 1 and len(live) == 1, (ad_id, len(dry), len(live))
    assert dry[0][2]['data']['data']['request']['body'] == pay
    new_id = live[0][2]['data']['data']['id']
    new_reads = whcalls('meta_creative_id_get', lambda i: (i.get('path_params') or {}).get('creative_id') == new_id)
    new_cr = new_reads[-1][2]['data']['data']
    upd = whcalls('meta_ad_id_update', lambda i: (i.get('path_params') or {}).get('ad_id') == ad_id)
    udry = [c for c in upd if c[1].get('dry_run')]
    ulive = [c for c in upd if c[1].get('dry_run') is False]
    assert len(udry) == 1 and len(ulive) == 1, (ad_id, len(udry), len(ulive))
    assert ulive[0][1]['payload'] == {'creative': {'creative_id': new_id}}
    assert ulive[0][2]['data']['data'] == {'success': True}
    assert post_ad['creative']['id'] == new_id
    removed = orig['object_story_spec']['link_data'].get('image_hash')
    ig_note = ('instagram_user_id %s sent top-level as read (the original creative has it top-level only)' % orig.get('instagram_user_id')
               if 'instagram_user_id' in pay else
               'page %s / IG %s as read' % (orig['object_story_spec']['page_id'], orig['object_story_spec'].get('instagram_user_id')))
    dof_note = ('original degrees_of_freedom_spec (9 features OPT_OUT) kept' if 'degrees_of_freedom_spec' in orig
                else 'original had no degrees_of_freedom_spec (none sent)')
    base_detail = (
        'recipe meta_carousel_no_parent_image. Pre-read ad req %s (ad configured %s / effective %s on creative %s) and creative req %s: slot == now. '
        'New creative %s = exact copy of %s with the listed URLs = new and WITHOUT the parent object_story_spec.link_data.image_hash %s (no link_data.picture in the read); '
        '%d child_attachments (cards) exactly as read (image_hash, name, description, CTA BOOK_TRAVEL), message, CTA, %s, format_transformation_spec, portrait_customizations, '
        'contextual_multi_ads, threads_user_id, authorization_category as read; %s. Dry-run req %s (body == payload), live create req %s accepted (no 2446581 this time). '
        'Read-back req %s: every listed URL == new, no parent image_hash, cards unchanged; Meta itself appended a date-hash suffix to the name (%s), '
        'filled degrees_of_freedom_spec with %d features all OPT_OUT and added creative_sourcing_spec.destination_screenshot_spec OPT_OUT (server defaults, all opt-outs). '
        'Attach POST /%s creative={creative_id:%s} (no status sent): dry-run req %s, live req %s success. Re-read ad req %s: on creative %s, configured %s, effective %s '
        '(re-review, expected; it was %s before the write). Old creative %s left untouched.'
    ) % (
        rid(ad_reads[0][2]), pre_ad['configured_status'], pre_ad['effective_status'], pre_ad['creative']['id'], rid(cr_reads[-1][2]),
        new_id, u['creative_id'], removed,
        len(orig['object_story_spec']['link_data']['child_attachments']), ig_note, dof_note,
        rid(dry[0][2]), rid(live[0][2]),
        rid(new_reads[-1][2]), new_cr['name'],
        len(new_cr.get('degrees_of_freedom_spec', {}).get('creative_features_spec', {})),
        ad_id, new_id, rid(udry[0][2]), rid(ulive[0][2]), rid(ad_reads[-1][2]), post_ad['creative']['id'],
        post_ad['configured_status'], post_ad['effective_status'], pre_ad['effective_status'], u['creative_id'])
    short_detail = ('Same unit and same single new creative %s as link_data.link (recipe meta_carousel_no_parent_image, parent image_hash %s not sent, '
                    'cards as read): pre-read creative req %s slot == now; create dry-run req %s / live req %s; read-back req %s slot == new; '
                    'attach live req %s; ad re-read req %s on creative %s, configured %s, effective %s (re-review).') % (
        new_id, removed, rid(cr_reads[-1][2]), rid(dry[0][2]), rid(live[0][2]), rid(new_reads[-1][2]), rid(ulive[0][2]),
        rid(ad_reads[-1][2]), post_ad['creative']['id'], post_ad['configured_status'], post_ad['effective_status'])
    for k, c in enumerate(u['changes']):
        before = clib.full_url(orig, c['slot'])
        assert before == c['now']
        after = clib.full_url(post_ad['creative'], c['slot'])
        res = 'Fixed' if after == c['new'] else 'Failed'
        results.append({
            'platform': 'meta', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': ad_id,
            'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': c['slot'], 'before': before,
            'after_expected': c['new'], 'after_live': after, 'result': res, 'new_entity_ids': 'creative %s' % new_id,
            'detail': base_detail if k == 0 else short_detail})
        summary.append((ad_id, c['slot'][-30:], res))

for s in summary:
    print('#', *s, file=sys.stderr)
print(json.dumps(results, ensure_ascii=False))
