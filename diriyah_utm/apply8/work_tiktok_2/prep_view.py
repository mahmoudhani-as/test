import sys,json
t=sys.stdin.read()
a,_,p=t.partition('PAYLOAD:')
c=json.loads(a)
print({k:c.get(k) for k in ('ad','request_id','order','decision','match','utm_extra','utm_conflict','ad_name_matches_plan','advertiser_ok','op','sec','modify_time','ac_keys')})
print('materials:', [(m['fmt'],m['identity_type'],m['item']) for m in c.get('materials',[])])
print('cur:', c.get('cur'))
if p.strip(): print('PAYLOAD:', p.strip())
