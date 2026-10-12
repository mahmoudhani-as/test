import json, re, sys, datetime
root = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
inp = json.load(open(f'{root}/reread/in/linkedin_512278713.json'))
live = json.load(open(f'{root}/reread2/work_linkedin_512278713/live_creatives.json'))
out_path = f'{root}/reread2/out/linkedin_512278713.jsonl'
new_path = f'{root}/reread2/out/new_linkedin_512278713.jsonl'

cr = {}
for c in live['creatives']:
    cid, intended, serving, created, lastmod, camp, ref, name, hk, review = c
    cr[cid] = dict(intended=intended, serving=serving, created=created, lastmod=lastmod,
                   camp=camp, ref=ref, name=name, holds=live[hk], review=review)
camps = live['campaigns']
pull_11oct_ms = int(datetime.datetime(2026, 10, 11, tzinfo=datetime.timezone.utc).timestamp() * 1000)

def fmt(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

problems = []
lines = []
for r in inp:
    ad = r['ad_id']
    c = cr.get(ad)
    if c is None:
        lines.append(dict(platform='linkedin', account_id='512278713', ad_id=ad, slot=r['slot'], url=None,
                          status_now='NOT_FOUND', creative_id_now=None, found=False,
                          note='Creative not returned by GET /rest/adAccounts/512278713/creatives with all intendedStatuses - creative no longer exists (deleted).'))
        problems.append(f'{ad}: missing')
        continue
    status_now = 'SERVING' if c['serving'] else 'NOT_SERVING (' + ','.join(c['holds']) + ')'
    m = re.match(r'post\((urn:li:[A-Za-z]+:\d+)\)', r['slot'])
    slot_ref = m.group(1) if m else None
    same_ref = (slot_ref == c['ref'])
    if not same_ref:
        problems.append(f'{ad}: post ref changed {slot_ref} -> {c["ref"]}')
    if ('urn:li:sponsoredCreative:' + ad) != r['creative_id']:
        problems.append(f'{ad}: creative id mismatch {r["creative_id"]}')
    unchanged = (status_now == r['status_11oct'])
    cname, cstatus, cformat, cgroup = camps[c['camp']]
    note = (
        f"Post-based sponsored creative; content.reference={c['ref']} "
        + ("(same post as 11-Oct slot). " if same_ref else f"(CHANGED from 11-Oct slot post {slot_ref}). ")
        + "Landing URL lives on the post, not the creative; Posts API BATCH_GET still 403 ACCESS_DENIED "
        + "'partnerApiPostsExternal.BATCH_GET.20260701' on 12-Oct reread2 - url kept null (unreadable, as on 11-Oct). "
        + f"intendedStatus={c['intended']}; isServing={str(c['serving']).lower()}; review={c['review']}; "
        + f"campaign urn:li:sponsoredCampaign:{c['camp']} '{cname}' status={cstatus} format={cformat} "
        + f"(group urn:li:sponsoredCampaignGroup:{cgroup}); "
        + f"creative lastModifiedAt {fmt(c['lastmod'])} "
        + ("(before 11-Oct pull). " if c['lastmod'] < pull_11oct_ms else "(AFTER 11-Oct pull). ")
        + ("Status unchanged vs 11-Oct." if unchanged else f"Status changed vs 11-Oct (was {r['status_11oct']}).")
    )
    lines.append(dict(platform='linkedin', account_id='512278713', ad_id=ad, slot=r['slot'], url=None,
                      status_now=status_now, creative_id_now='urn:li:sponsoredCreative:' + ad, found=True, note=note))

with open(out_path, 'w') as f:
    for l in lines:
        f.write(json.dumps(l, ensure_ascii=False) + '\n')

# Task 2: creatives in the account that are not in the input
in_ids = {r['ad_id'] for r in inp}
new_ads = [cid for cid in cr if cid not in in_ids]
with open(new_path, 'w') as f:
    pass  # filled below only if new ads exist
print('new ads (not in input):', new_ads)
print('problems:', problems)
print('wrote', len(lines), 'lines')
