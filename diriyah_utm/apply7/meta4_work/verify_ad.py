import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/meta4_work')
from lib import *


def check_ad(ad_id, ad_file, new_creative_file, new_creative_id):
    ad = json.loads(open(W + ad_file).read())
    newc = json.loads(open(W + new_creative_file).read())
    u = unit(ad_id)
    cr = ad['creative']
    print('ad', ad['id'], 'status', ad['status'], ad['configured_status'], ad['effective_status'], '| creative', cr['id'],
          '== new creative:', cr['id'] == new_creative_id, '| url_tags:', cr.get('url_tags'))
    print('ad osp == verified new creative osp:', cr['object_story_spec'] == newc['object_story_spec'])
    after = {}
    for c in u['changes']:
        v = full_url(cr, c['slot'])
        after[c['slot']] = v
        print('  ', c['slot'], 'after == new:', v == c['new'])
    return ad, after


if __name__ == '__main__':
    check_ad(*sys.argv[1:5])
