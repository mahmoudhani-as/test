# usage: python3 -I stop_recs.py <reason_text> [--write]
# Builds NotAttempted records for every unit not yet recorded in out_tiktok_6.jsonl (regular ads: before/after_live = pre-read cur;
# Smart+ ads not read: before/after_live empty). Unit-specific Failed records must be written separately before this.
import json, sys, subprocess, os
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt6_work')
from common import *
reason=sys.argv[1]
done=set()
if os.path.exists(OUT):
    for line in open(OUT):
        if line.strip(): done.add(json.loads(line)['unit'])
D=json.load(open(T+'decisions.json')) if os.path.exists(T+'decisions.json') else {}
recs=[]
for u in INP:
    ad=u['unit']
    if ad in done: continue
    d=D.get(ad)
    if d:
        if d['cls']=='SMART_PLUS':
            st=f"pre-read smart_plus/ad/get req {d['rid']}: landing_page_url_list[{d['slot_index']}] {'== now' if d['decision']=='Write' else d['decision']} (operation_status {d['op']}, secondary_status {d['sec']}, modify_time {d['modify_time']}). "
        else:
            st=(f"pre-read ad/get req {d['rid']}: URL == now ({d['cls']} {d['ad_format']}, identity {d['identity_id']}, adgroup {d['adgroup_id']}, utm_params {len(d['utm_before'])} keys, no utm_id; "
                f"operation_status {d['op']}, secondary_status {d['sec']}, modify_time {d['modify_time']}); payload ready in apply7/tt6_work/payload_{ad}.json. ")
        before=after=d['cur']
    else:
        st="not read: smart_plus/ad/get failed with TikTok 52404/51002 on every try (reqs 20261013060503BD859DEF87F1AC10784E, 202610130605104CA30FDEF704DB3DC8AD, 20261013060729A52F69D6C227DAF2D250, 202610130607521D98F409BA835BF040BD, 2026101306101959DE410E5A6BD0322325, 2026101306112777C92122A444E960B7E7, 20261013061301CF90A1DDB41BDE61E07A, 202610130615030D8B006104915C234145). "
        before=after=''
    recs.append({"ad_id":ad,"result":"NotAttempted","before":before,"after_live":after,"detail":"Not written: "+reason+" "+st+"Nothing was sent for this ad; safe to re-run (re-read first)."})
json.dump(recs,open(T+'rec_stop.json','w'),ensure_ascii=False)
for r in recs: print(r['ad_id'], r['result'], '|', r['detail'][:260])
print(len(recs),'records')
if '--write' in sys.argv: subprocess.run(['python3','-I',T+'rec.py',T+'rec_stop.json'],check=True)
