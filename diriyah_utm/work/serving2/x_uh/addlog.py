import json, sys, os
# usage: addlog.py placement start_date 'json dict id->list|null'
f='daily_log.json'
log=json.load(open(f)) if os.path.exists(f) else []
log.append({"placement":sys.argv[1],"start":sys.argv[2],"data":json.loads(sys.argv[3])})
json.dump(log,open(f,'w'))
print(len(log))
