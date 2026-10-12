"""Summarise scored.json: % wrong per ad and per URL slot, overall / platform / account, all vs switched-on."""
import json, sys, re, collections
S = json.load(open(sys.argv[1]))
OFF = re.compile(r'PAUSED|DISABLE|INVALID|NOT_SERVING|REJECTED|DONE|ARCHIVED|REMOVED|ENDED|COMPLETED|DRAFT|HOLD', re.I)
def is_on(s):
    for k in ('campaign_status', 'adset_status', 'ad_status'):
        v = s.get(k)
        if v is None: continue
        if not re.match(r'\s*(ACTIVE|ENABLE|ENABLED|SERVING)', str(v), re.I): return False
    return not OFF.search(str(s.get('effective_status') or ''))
def kind(s):
    return 'sitelink' if 'sitelink' in str(s.get('slot') or '').lower() else 'ad'
for s in S:
    s['_on'] = is_on(s); s['_kind'] = kind(s)
    s['_key'] = (s['platform'], s.get('account_id'), s.get('ad_id'), (s.get('url') or '') if s['_kind'] == 'sitelink' else s.get('slot'))

def stats(rows):
    seen = {}
    for s in rows:
        if s.get('url'): seen.setdefault(s['_key'], s)
    slots = list(seen.values())
    w = sum(1 for s in slots if s['verdict'] == 'WRONG'); c = sum(1 for s in slots if s['verdict'] == 'CORRECT'); u = sum(1 for s in slots if s['verdict'] == 'UNTRACEABLE')
    ads = collections.defaultdict(list)
    for s in rows: ads[(s['platform'], s.get('account_id'), s.get('ad_id'))].append(s)
    ad_with_url = [v for v in ads.values() if any(x.get('url') for x in v)]
    ad_wrong = sum(1 for v in ad_with_url if any(x['verdict'] == 'WRONG' for x in v))
    ad_nourl = len(ads) - len(ad_with_url)
    fixable = sum(1 for s in slots if s['derive_status'] == 'FIX')
    blocked = sum(1 for s in slots if s['derive_status'] == 'BLOCKED')
    return dict(ads=len(ads), ads_url=len(ad_with_url), ads_wrong=ad_wrong, ads_nourl=ad_nourl, slots=len(slots), wrong=w, correct=c, untr=u, fix=fixable, blocked=blocked)

def line(label, st):
    p = lambda a, b: f'{a/b:6.1%}' if b else '   n/a'
    return (f'{label:58} ads {st["ads"]:5} | with URL {st["ads_url"]:5} wrong {st["ads_wrong"]:5} {p(st["ads_wrong"], st["ads_url"])} | '
            f'URL slots {st["slots"]:5} wrong {st["wrong"]:5} {p(st["wrong"], st["slots"])} correct {st["correct"]:4} | fixable {st["fix"]:4} blocked {st["blocked"]:5} | no URL {st["ads_nourl"]:4}')

ads = [s for s in S if s['_kind'] == 'ad']; sl = [s for s in S if s['_kind'] == 'sitelink']
print(line('ALL ADS (every account)', stats(ads)))
print(line('ADS switched on (campaign+set+ad on)', stats([s for s in ads if s['_on']])))
print(line('Google sitelinks (unique asset URLs)', stats(sl)))
print()
for p in sorted({s['platform'] for s in ads}):
    print(line(f'{p}', stats([s for s in ads if s['platform'] == p])))
print()
for k in sorted({(s['platform'], s.get('account_name')) for s in ads}, key=str):
    print(line(f'{k[0]} | {str(k[1])[:45]}', stats([s for s in ads if (s['platform'], s.get('account_name')) == k])))
print()
for k in sorted({(s['platform'], s.get('account_name')) for s in ads}, key=str):
    r = [s for s in ads if (s['platform'], s.get('account_name')) == k and s['_on']]
    if r: print(line(f'ON {k[0]} | {str(k[1])[:42]}', stats(r)))
