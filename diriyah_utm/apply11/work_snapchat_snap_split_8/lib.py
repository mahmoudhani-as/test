import json
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_snapchat_snap_split_8/'
INP='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/in_snapchat_snap_split_8.json'
DROP={"id","updated_at","created_at","packaging_status","review_status","review_status_details","semantic_id"}
def units(): return json.load(open(INP))
def same_url(a,b):
    if a==b: return True
    A=urlsplit(a); B=urlsplit(b)
    return (A.scheme,A.netloc,A.path,A.fragment)==(B.scheme,B.netloc,B.path,B.fragment) and sorted(parse_qsl(A.query,keep_blank_values=True))==sorted(parse_qsl(B.query,keep_blank_values=True))
def classify(cur,ch):
    if same_url(cur,ch['new']): return 'AlreadyFixed'
    if cur==ch['now'] or cur in ch.get('alt_now',[]): return 'write'
    return 'Skipped'
def copy_creative(c, url=None, creative_ids=None):
    n={k:v for k,v in c.items() if k not in DROP}
    if url is not None:
        n['web_view_properties']=dict(n['web_view_properties']); n['web_view_properties']['url']=url
    if creative_ids is not None:
        n['composite_properties']=dict(n['composite_properties']); n['composite_properties']['creative_ids']=list(creative_ids)
    return n
