# One scan: prints TikTok successes (live update code 0, smart_plus get code 0, pixel list code 0) newer than argv[1] (TikTok request-id time prefix).
import subprocess, sys
since=sys.argv[1]
out=subprocess.run(['python3','-I','/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt6_work/health.py','400'],capture_output=True,text=True).stdout
for line in out.splitlines():
    t=eval(line)
    if t[0]>since and t[3] and t[2] in ('tiktok_ad_update','tiktok_smart_plus_ad_get','tiktok_smart_plus_ad_update','tiktok_pixel_list_get'):
        print('TIKTOK_OK', line)
