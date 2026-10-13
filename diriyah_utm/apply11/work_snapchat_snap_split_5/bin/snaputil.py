import json, sys, copy
from urllib.parse import urlsplit, parse_qsl

W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_snapchat_snap_split_5'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/in_snapchat_snap_split_5.json'

EXCLUDE = {'id', 'updated_at', 'created_at', 'review_status', 'review_status_details',
           'semantic_id', 'packaging_status'}

def units():
    return json.load(open(IN))

def url_equiv(a, b):
    if a is None or b is None:
        return False
    sa, sb = urlsplit(a), urlsplit(b)
    if (sa.scheme, sa.netloc, sa.path, sa.fragment) != (sb.scheme, sb.netloc, sb.path, sb.fragment):
        return False
    return sorted(parse_qsl(sa.query, keep_blank_values=True)) == sorted(parse_qsl(sb.query, keep_blank_values=True))

def classify(cur, ch):
    if cur == ch['new'] or url_equiv(cur, ch['new']):
        return 'AlreadyFixed'
    if cur == ch['now'] or cur in ch.get('alt_now', []):
        return 'Write'
    if url_equiv(cur, ch['now']) or any(url_equiv(cur, x) for x in ch.get('alt_now', [])):
        return 'Write(equiv)'
    return 'Skipped'

def build_copy(creative, new_url=None, composite_ids=None):
    c = {k: copy.deepcopy(v) for k, v in creative.items() if k not in EXCLUDE}
    if new_url is not None:
        c['web_view_properties']['url'] = new_url
    if composite_ids is not None:
        c['composite_properties']['creative_ids'] = list(composite_ids)
    return c

def diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f'+{path}.{k}')
            elif k not in b:
                out.append(f'-{path}.{k}')
            else:
                out += diff(a[k], b[k], f'{path}.{k}')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f'~{path} len {len(a)}!={len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f'{path}[{i}]')
    elif a != b:
        out.append(f'~{path}: {a!r} -> {b!r}')
    return out
