import json,sys
inp=json.load(open(sys.argv[1]))
unit=[u for u in inp if u['unit']==sys.argv[3]][0]
obj=json.load(open(sys.argv[2]))
cur=obj['web_view_properties']['url']
ch=unit['changes'][0]
state = 'NEW' if cur==ch['new'] else ('NOW' if cur==ch['now'] else ('ALT' if cur in ch['alt_now'] else 'OTHER'))
print('state',state)
obj['web_view_properties']['url']=ch['new']
print(json.dumps({"creatives":[obj]},ensure_ascii=False))
