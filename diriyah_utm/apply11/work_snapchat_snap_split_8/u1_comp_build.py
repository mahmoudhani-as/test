import json,sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_snapchat_snap_split_8/')
from lib import *
r=json.load(open(W+'u1_reads.json'))
created={"request_id":"d345e0e8-0fb6-4a24-acd2-c357864b7a6f","gateway_request_id":"58882fab-5985-41f8-9fb2-ec4ad0d537a1",
 "map":[["3864d4f7-b493-46dc-af94-6dcd20ea8a3c","41e48018-72a7-4f59-8544-e813760954ae","6f7ee413-325f-479e-aadb-aaa8b82c8e73"],
        ["186ec042-b20e-419a-88f2-51963737a89f","193521c0-dd68-4dce-a704-8ab9bc3591c0","a53ced5c-72c6-4477-8981-04886529c9b7"],
        ["c3ee3d39-8723-4067-842a-9313d81eb257","05a638d9-7308-458a-9658-3a771e8ba835","f7c9456b-6705-414b-bd6c-117c3a8fe14f"],
        ["d1caa22d-4eb9-46e1-8127-12f135157bfe","9017926c-c310-43ba-938e-a54c21752b50","18ed5cb9-3ec4-4677-9361-cddce463f6d2"],
        ["0fc2aeb8-4922-4bdd-a707-353ba83b2f65","271db6de-876d-4483-ac67-47f528099e2b","f6bccb48-b9cf-41f4-9594-debf67281760"],
        ["9ebe2063-bbbc-46ef-b5b4-9cb326eb9af1","5de1fa28-f53f-4942-b7a4-ceb052bb1b26","06a9e91a-8926-4eaa-b7fa-e3ecb8a39706"]]}
subs={s['id']:s for s in r['subs']}
for old,new,media in created['map']: assert subs[old]['top_snap_media_id']==media
json.dump(created,open(W+'u1_created_subs.json','w'),indent=1)
old_ids=r['composite']['composite_properties']['creative_ids']
m={o:n for o,n,_ in created['map']}
new_ids=[m.get(i,i) for i in old_ids]
p={"creatives":[copy_creative(r['composite'], creative_ids=new_ids)]}
json.dump(p,open(W+'u1_payload_comp.json','w'),ensure_ascii=False,indent=1)
print(json.dumps(p,ensure_ascii=False))
