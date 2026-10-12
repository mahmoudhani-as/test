import json, os, re, sys, datetime, collections
W = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, W)
from check import load_new
ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = f'{ROOT}/reread/in/linkedin_513006454.json'
OUT = f'{ROOT}/reread2/out/linkedin_513006454.jsonl'
NEW = f'{ROOT}/reread2/out/new_linkedin_513006454.jsonl'
ACC, ACC_NAME = '513006454', 'Diriyah Company Paid Campaigns'
POSTS_403 = ("Posts API still unreadable on the 12-Oct re-read (HTTP 403 ACCESS_DENIED "
             "'partnerApiPostsExternal.BATCH_GET.20260701'), so the landing URL stored on the post cannot be read - url kept null as on 11-Oct.")
# campaigns / groups read 12-Oct for the new ads
CAMPS = {'895959103': dict(name='company_ritz-signature_2026_oct_residential_adset-id-3e71b680_en_all_mf_prospecting', status='PAUSED', group='1204661933', objective='WEBSITE_VISIT'),
         '895979133': dict(name='company_ritz-signature_2026_oct_residential_adset-id-3e71b680_en_all_mf_prospecting', status='PAUSED', group='1221216003', objective='WEBSITE_CONVERSION')}
GROUPS = {'1204661933': dict(name='linkedin_company_ritz-signature_tac_2026_aug_ritz-carlton-signature_cam-id-bb1cac08_mf_cond_ksa', status='ACTIVE'),
          '1221216003': dict(name='linkedin_company_ritz-signature_tac_2026_aug_ritz-carlton-signature_cam-id-bb1cac08_lf_conv_ksa', status='ACTIVE')}

def iso(ms): return datetime.datetime.fromtimestamp(ms / 1000, datetime.UTC).strftime('%Y-%m-%d %H:%M UTC')
def status(c, camp_note=''):
    rev = c['rev'] or 'none'
    if c['srv']:
        return f"SERVING; review={rev}; status={c['ist']}"
    s = f"NOT_SERVING; review={rev}; status={c['ist']}"
    if c['holds']: s += '; hold=' + ','.join(c['holds']) + camp_note
    return s

cr = {r['id']: r for r in load_new()}
im = {}
for l in open(f'{W}/inmail.tsv', encoding='utf-8'):
    l = l.rstrip('\n')
    if l:
        u, url, cta, mod, name = l.split('\t'); im[u] = dict(url=url, cta=cta, mod=int(mod), name=name)
rows = json.load(open(IN, encoding='utf-8'))
out, stats = [], collections.Counter()
for r in rows:
    c = cr.get(r['ad_id'])
    base = dict(platform='linkedin', account_id=ACC, ad_id=r['ad_id'], slot=r['slot'])
    if c is None or c['ist'] in ('REMOVED', 'PENDING_DELETION'):
        out.append(dict(base, url=None, status_now=(c and c['ist']) or 'DELETED', creative_id_now=r['creative_id'], found=False,
                        note='Creative no longer in the account creatives list (deleted/removed).' if c is None else f"Creative intendedStatus={c['ist']} (removed)."))
        stats['not_found'] += 1; continue
    st = status(c)
    old_prefix = r['status_11oct']
    now_prefix = st.split('; status=')[0]
    stchg = ('Delivery status unchanged since 11-Oct.' if now_prefix == old_prefix else f'Delivery status changed since 11-Oct: {old_prefix} -> {now_prefix}.') + f" Creative intendedStatus={c['ist']}, isServing={'true' if c['srv'] else 'false'}" + (f", servingHoldReasons={','.join(c['holds'])}." if c['holds'] else '.')
    m = re.match(r'inMailContent\((urn:li:adInMailContent:\d+)\)\.subContent\.regular\.callToActionLandingPageUrl$', r['slot'])
    if m:
        urn = m.group(1)
        assert c['ct'] == 'I' and c['ref'] == urn, (r['ad_id'], c['ref'], urn)
        v = im[urn]
        url = v['url']
        chg = 'URL unchanged since 11-Oct.' if url == r['url_11oct'] else 'URL changed since 11-Oct (edited ' + iso(v['mod']) + ').'
        note = (f"Sponsored Message (Message Ad) creative; content.reference={urn} (same inMailContent as 11-Oct slot); "
                f"read via BATCH_GET /rest/inMailContents, subContent.regular.callToActionLandingPageUrl; CTA text '{v['cta']}'; "
                f"inMailContent lastModifiedAt {iso(v['mod'])}. {chg} {stchg}")
        stats['inmail'] += 1; stats['url_changed' if url != r['url_11oct'] else 'url_same'] += 1
    else:
        m = re.match(r'creative\.(content\.reference|content\.documentAd\.reference) -> post (urn:li:(?:share|ugcPost):\d+) \(post content\.article\.source / CTA landing page\)$', r['slot'])
        assert m, r['slot']
        kind, post = m.groups()
        assert c['ref'] == post and c['ct'] == ('D' if 'documentAd' in kind else 'R'), (r['ad_id'], c['ref'], post, c['ct'])
        assert r['url_11oct'] is None
        url = None
        note = (f"{'Document ad' if c['ct'] == 'D' else 'Post-based Sponsored Content'} creative; {kind}={post} (same post as 11-Oct slot). "
                f"Landing URL lives on the referenced post. {POSTS_403} {stchg}")
        if not c['name']: note += ' Creative has no name set in API (name null).'
        stats['post'] += 1
    out.append(dict(base, url=url, status_now=st, creative_id_now=f"urn:li:sponsoredCreative:{c['id']}", found=True, note=note))
    stats['found'] += 1
    stats['serving' if c['srv'] else 'not_serving'] += 1
    if now_prefix != old_prefix: stats['status_changed'] += 1

with open(OUT, 'w', encoding='utf-8') as f:
    for o in out: f.write(json.dumps(o) + '\n')

inids = {r['ad_id'] for r in rows}
new = []
for c in sorted(cr.values(), key=lambda x: int(x['id'])):
    if c['id'] in inids or c['ist'] in ('REMOVED', 'PENDING_DELETION'): continue
    assert c['ct'] == 'I', c   # only Message Ads are new in this account
    camp = CAMPS[c['camp']]; grp = GROUPS[camp['group']]
    v = im[c['ref']]
    new.append(dict(platform='linkedin', account_id=ACC, account_name=ACC_NAME, campaign_name=grp['name'], adset_name=camp['name'],
                    ad_id=c['id'], ad_name=c['name'] or None,
                    effective_status=status(c, f" (campaign {c['camp']} {camp['status']}; campaign group {camp['group']} {grp['status']})"),
                    slot=f"inMailContent({c['ref']}).subContent.regular.callToActionLandingPageUrl", url=v['url']))
with open(NEW, 'w', encoding='utf-8') as f:
    for o in new: f.write(json.dumps(o) + '\n')
print(dict(stats)); print('new ads', len(new))
for o in new: print(' ', o['ad_id'], o['created'] if 'created' in o else '', o['effective_status'])
