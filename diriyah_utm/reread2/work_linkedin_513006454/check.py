import glob, os, sys, collections
W = os.path.dirname(os.path.abspath(__file__))
OLD = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/live/li513'
HOLD = {'S':'STOPPED','CED':'CAMPAIGN_END_DATE_HOLD','CS':'CAMPAIGN_STOPPED','CGS':'CAMPAIGN_GROUP_STATUS_HOLD','CGE':'CAMPAIGN_GROUP_END_DATE_HOLD',
        'CGTB':'CAMPAIGN_GROUP_TOTAL_BUDGET_HOLD','UR':'UNDER_REVIEW','CAC':'CAMPAIGN_AUDIENCE_COUNT_HOLD','REJ':'REJECTED'}
def load_new():
    rows = []
    for p in sorted(glob.glob(f'{W}/cr_p*.tsv')):
        for n, l in enumerate(open(p, encoding='utf-8'), 1):
            l = l.rstrip('\n')
            if not l: continue
            parts = l.split('\t')
            assert len(parts) == 10, (p, n, len(parts), l)
            cid, name, camp, ct, ref, ist, srv, rev, holds, created = parts
            assert cid.isdigit() and camp.isdigit() and created.isdigit(), (p, n, l)
            assert ct in ('R', 'D', 'I', 'O'), (p, n, ct)
            assert srv in ('T', 'F'), (p, n, srv)
            hs = [h for h in holds.split(',') if h]
            for h in hs: assert h in HOLD or h.isupper(), (p, n, h)
            rows.append(dict(id=cid, name=name, camp=camp, ct=ct, ref=ref, ist=ist, srv=srv == 'T', rev=rev,
                             holds=[HOLD.get(h, h) for h in hs], created=int(created), page=os.path.basename(p), line=n))
    return rows
def load_old():
    old = {}
    for p in sorted(glob.glob(f'{OLD}/cr_p*.tsv')):
        for l in open(p, encoding='utf-8'):
            l = l.rstrip('\n')
            if not l: continue
            parts = l.split('\t'); parts += [''] * (8 - len(parts))
            cid, name, camp, st, serving, ctype, ref, review = parts
            old[cid] = dict(name=name, camp=camp, ist=st, srv=serving == 'true', ct=('I' if ref.startswith('urn:li:adInMailContent') else {'reference':'R','documentAd':'D'}.get(ctype, ctype)), ref=ref, rev=review)
    return old
if __name__ == '__main__':
    new, old = load_new(), load_old()
    ids = [r['id'] for r in new]
    print('new rows', len(new), 'unique', len(set(ids)), 'old rows', len(old))
    d = [k for k, v in collections.Counter(ids).items() if v > 1]
    if d: print('DUP ids', d)
    if ids != sorted(ids, key=int): print('WARNING: ids not ascending')
    for r in new:
        o = old.get(r['id'])
        if not o: print('NOT IN 11-OCT RAW:', r['id'], r['name'], r['ct'], r['ref'], r['ist'], r['created'], r['page'], r['line']); continue
        for k in ('name', 'camp', 'ref', 'ct'):
            if (o[k] or '') != (r[k] or '') and not (k == 'name' and o[k] == '' and r[k] == r['id']):
                print(f'DIFF {k}:', r['id'], repr(o[k]), '->', repr(r[k]), r['page'], r['line'])
        for k in ('ist', 'srv', 'rev'):
            if o[k] != r[k]: print(f'chg {k}:', r['id'], o[k], '->', r[k], r['page'], r['line'])
