"""Combine a previous keyed re-read folder with a newer one that holds full and partial (selected rows) re-reads.
Usage: python3 scripts/merge_partial.py <dir> <base out dir> <new out dir> <jobs.json of the new re-read> <merged out dir>
  full job    -> the new file replaces the base file (and its new_*.jsonl)
  partial job -> the base file is kept and only the re-read rows (same ad_id + slot) are replaced
Prints, per account, how many rows came from the new re-read."""
import sys, os, json, glob, shutil
W, BASE, NEW, JOBS, OUT = sys.argv[1:6]
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(f'{BASE}/*.jsonl'): shutil.copy2(f, OUT)
for j in json.load(open(JOBS)):
    b = os.path.basename(j['out_file'])
    newf = os.path.join(NEW, b)
    if not os.path.exists(newf): print('MISSING new re-read', b); continue
    new = [json.loads(l) for l in open(newf) if l.strip()]
    if not j.get('partial'):
        shutil.copy2(newf, os.path.join(OUT, b))
        nb = os.path.basename(j['new_file'])
        if os.path.exists(os.path.join(NEW, nb)): shutil.copy2(os.path.join(NEW, nb), os.path.join(OUT, nb))
        print(f'{b}: full, {len(new)} rows (input {j["n_rows"]})')
        continue
    nk = {(str(x['ad_id']), x['slot']): x for x in new}
    base = [json.loads(l) for l in open(os.path.join(BASE, b)) if l.strip()]
    hit = 0
    with open(os.path.join(OUT, b), 'w') as fh:
        for x in base:
            y = nk.get((str(x['ad_id']), x['slot']))
            if y is not None: hit += 1
            fh.write(json.dumps(y if y is not None else x, ensure_ascii=False) + '\n')
    print(f'{b}: partial, {hit} of {len(new)} re-read rows merged into {len(base)} (input {j["n_rows"]})')
