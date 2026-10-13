"""Helpers for the snap_split lane (read-only analysis + payload building; no API calls)."""
import json
import re
import sys
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11'
WORK = BASE + '/work_snapchat_snap_split_1'
INPUT = BASE + '/in_snapchat_snap_split_1.json'

# fields never copied into a new creative (id, timestamps, review / semantic / processing status)
EXCLUDE = {'id', 'created_at', 'updated_at', 'review_status', 'review_status_details',
           'semantic_id', 'packaging_status'}


def units():
    return json.load(open(INPUT))


def url_eq_loose(a, b):
    """same scheme/host/path/fragment and same query params in any order"""
    if a is None or b is None:
        return False
    x, y = urlsplit(a), urlsplit(b)
    return (x.scheme, x.netloc, x.path, x.fragment) == (y.scheme, y.netloc, y.path, y.fragment) and \
        sorted(parse_qsl(x.query, keep_blank_values=True)) == sorted(parse_qsl(y.query, keep_blank_values=True))


def classify(cur, ch):
    if cur == ch['new'] or url_eq_loose(cur, ch['new']):
        return 'AlreadyFixed'
    if cur == ch['now'] or cur in (ch.get('alt_now') or []):
        return 'Write'
    return 'Skipped'


def slot_sub_id(slot):
    m = re.search(r'creative_ids\[(\d+)\] \(([0-9a-f-]{36})\)', slot)
    return (int(m.group(1)), m.group(2)) if m else None


def copy_creative(c, url=None, creative_ids=None):
    out = {k: v for k, v in c.items() if k not in EXCLUDE}
    out = json.loads(json.dumps(out))
    if url is not None:
        out['web_view_properties']['url'] = url
    if creative_ids is not None:
        out['composite_properties']['creative_ids'] = list(creative_ids)
    return out


def diff(a, b, path=''):
    """list differences between two json values"""
    d = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                d.append(f'{path}.{k}: missing in A')
            elif k not in b:
                d.append(f'{path}.{k}: missing in B')
            else:
                d += diff(a[k], b[k], f'{path}.{k}')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            d.append(f'{path}: len {len(a)} != {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            d += diff(x, y, f'{path}[{i}]')
    elif a != b:
        d.append(f'{path}: {a!r} != {b!r}')
    return d


def dump(obj, path):
    with open(path, 'w') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    print('ok')
