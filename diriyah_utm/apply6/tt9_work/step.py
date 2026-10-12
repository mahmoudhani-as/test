# usage: python3 -I step.py <written_ad_id> <pre_read_file_of_written_ad> <post_read_request_id> [<next_ad_id>]
# verifies the live call of the written ad, post-checks it, records it, and builds the next ad from the post-read.
import subprocess, sys, json
T='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt9_work/'
ad, pref, rid = sys.argv[1], sys.argv[2], sys.argv[3]
nxt = sys.argv[4] if len(sys.argv)>4 else None
def run(*a):
    o=subprocess.run(['python3','-I']+list(a),capture_output=True,text=True)
    print(o.stdout.strip()); 
    if o.returncode: print('ERR', o.stderr.strip()); sys.exit(1)
run(T+'cmpcall.py', ad, 'live')
run(T+'post.py', rid, pref, ad)
pc=json.load(open(T+f'postcheck_{ad}.json'))
if pc['url_ok'] and pc['utm_ok'] and pc['eff_equals_new'] and not pc['diffs'] and pc['status'][0]==pc['status'][1]:
    o=subprocess.run(['python3','-I',T+'mkrec.py',ad,'--write'],capture_output=True,text=True)
    print(o.stdout.strip().splitlines()[0] if o.stdout else o.stderr)
else:
    print('POSTCHECK NOT CLEAN - not recorded automatically')
if nxt:
    run(T+'build.py', f'read_{rid}.json', nxt)
