import sys,json
t=sys.stdin.read(); a,_,b=t.partition('AFTER_LIVE:'); o=json.loads(a)
o.pop('utm_params_after',None); print(json.dumps(o)); print('AFTER_LIVE:',b.strip())
