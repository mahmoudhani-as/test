import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/meta4_work')
from lib import *
from dof83 import dof_all_optout


def verify(ad_id, old_file, old_cl, new_file, new_cl, dof_cl_old=None, dof_cl_new=None, old_id=None, new_id=None):
    old, _ = load_raw(W + old_file, old_cl)
    new, _ = load_raw(W + new_file, new_cl)
    u = unit(ad_id)
    exp = copy.deepcopy(old)
    for c in u['changes']:
        set_slot(exp, c['slot'], c['new'])
    exp['id'] = new['id']
    # top-level call_to_action is a read-only mirror of the spec CTA: mirror the slot change there too
    vd_old = old.get('object_story_spec', {}).get('video_data')
    if vd_old and 'call_to_action' in exp and exp['call_to_action'] == vd_old.get('call_to_action'):
        exp['call_to_action'] = copy.deepcopy(exp['object_story_spec']['video_data']['call_to_action'])
    d = diff(exp, new)
    derived_keys = ('~ .object_story_spec.video_data.image_url:', '+ .link_url ', '~ .video_id:')
    derived = [l for l in d if l.startswith(derived_keys)]
    other = [l for l in d if not l.startswith('~ .name:') and l not in derived]
    if any(l.startswith('~ .object_story_spec.video_data.image_url:') for l in derived):
        assert old['object_story_spec']['video_data'].get('image_hash') == new['object_story_spec']['video_data'].get('image_hash'), 'image_hash differs'
    print('Meta-derived diffs (expected):', [l[:150] for l in derived])
    print('diffs other than name/derived:', other)
    print('name old:', old['name'])
    print('name new:', new['name'])
    slots_ok = all(get_slot(new, c['slot']) == c['new'] for c in u['changes'])
    print('every slot == new (byte for byte):', slots_ok, '| url_tags:', new.get('url_tags'))
    print('invisible chars new:', invisible(new))
    if dof_cl_old is not None:
        for cid, cl in ((old['id'], dof_cl_old), (new['id'], dof_cl_new)):
            body = {"id": cid, "degrees_of_freedom_spec": dof_all_optout()}
            n = len(json.dumps(body, separators=(',', ':')).encode())
            print('dof body for', cid, 'expected', n, 'Content-Length', cl, 'MATCH' if n == cl else 'MISMATCH')
    return old, new, other, slots_ok


if __name__ == '__main__':
    a = sys.argv[1:]
    verify(a[0], a[1], int(a[2]), a[3], int(a[4]), int(a[5]) if len(a) > 5 else None, int(a[6]) if len(a) > 6 else None)
