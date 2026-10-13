#!/usr/bin/env python3
"""Helper for apply9 Snapchat batch 1 (in_snapchat_1.json). Run with python3 -I.

  sh.py xt     <label> <request_id>        -> find my snapchat_native_action tool result containing request_id in my
                                              transcript; save {tool_use_id,input,result} to raw/<label>.json
  sh.py state  <u> <label>                 -> classify unit u's change against the creative in raw/<label>.json;
                                              for NOW/ALT write payload/u<u>.json = {"creatives":[full object, url=new]}
                                              and print it with non-letter non-ASCII chars as \\uXXXX escapes
  sh.py cmpdry <u> <label>                 -> compare the dry-run preview body in raw/<label>.json with payload/u<u>.json
  sh.py cmpcall <u> <label>                -> compare the payload I actually sent (tool input) with payload/u<u>.json
  sh.py diff   <before_label> <after_label> <creative_id> -> every differing field (URL / VOLATILE / OTHER)
  sh.py url    <label> <creative_id>       -> print the url and review fields exactly as read
"""
import json, sys, os, copy, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = BASE + '/apply9/in_snapchat_1.json'
W = BASE + '/apply9/work_snapchat_1'
EXCL = BASE + '/work/excl_platform_refused_v2.json'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_9ad6fd8a-5ef/agent-a9a8cd05ebc4b9d30.jsonl'
VOLATILE = {'updated_at', 'review_status', 'review_status_details', 'semantic_id', 'packaging_status'}


def units():
    return json.load(open(INP))


def same_url(a, b):
    if a == b:
        return True
    pa, pb = urlsplit(a), urlsplit(b)
    if (pa.scheme, pa.netloc, pa.path, pa.fragment) != (pb.scheme, pb.netloc, pb.path, pb.fragment):
        return False
    return sorted(parse_qsl(pa.query, keep_blank_values=True)) == sorted(parse_qsl(pb.query, keep_blank_values=True))


def classify(cur, ch):
    if same_url(cur, ch['new']):
        return 'NEW'
    if cur == ch['now']:
        return 'NOW'
    if cur in ch.get('alt_now', []):
        return 'ALT'
    return 'OTHER'


def safe_dumps(o):
    s = json.dumps(o, ensure_ascii=False)
    out = []
    for c in s:
        n = ord(c)
        if n > 126 and unicodedata.category(c) not in ('Lo', 'Ll', 'Lu'):
            if n > 0xFFFF:
                v = n - 0x10000
                out.append('\\u%04x\\u%04x' % (0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF)))
            else:
                out.append('\\u%04x' % n)
        else:
            out.append(c)
    return ''.join(out)


def str_report(obj, path=''):
    res = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            res += str_report(v, path + '.' + k if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            res += str_report(v, '%s[%d]' % (path, i))
    elif isinstance(obj, str):
        odd = [(i, 'U+%04X' % ord(c), unicodedata.name(c, '?')) for i, c in enumerate(obj)
               if (ord(c) > 126 and unicodedata.category(c) not in ('Lo', 'Ll', 'Lu')) or c in '\t\r\n']
        if odd or '  ' in obj or obj != obj.strip() or any(ord(c) > 126 for c in obj):
            res.append('%s len=%d odd=%s double_space=%s edge_space=%s' % (path, len(obj), odd, '  ' in obj, obj != obj.strip()))
    return res


def result_text(content):
    if isinstance(content, str):
        return content
    parts = []
    for p in content or []:
        if isinstance(p, dict) and p.get('type') == 'text':
            parts.append(p.get('text', ''))
    return ''.join(parts)


def cmd_xt(label, rid):
    uses, hits = {}, []
    for line in open(T):
        try:
            o = json.loads(line)
        except Exception:
            continue
        c = (o.get('message') or {}).get('content')
        if not isinstance(c, list):
            continue
        for p in c:
            if not isinstance(p, dict):
                continue
            if p.get('type') == 'tool_use' and 'snapchat_native_action' in (p.get('name') or ''):
                uses[p['id']] = p.get('input')
            elif p.get('type') == 'tool_result' and p.get('tool_use_id') in uses:
                txt = result_text(p.get('content'))
                if rid in txt:
                    hits.append((p['tool_use_id'], uses[p['tool_use_id']], txt))
    if len(hits) != 1:
        raise SystemExit('expected exactly 1 tool result with %s, found %d' % (rid, len(hits)))
    tid, inp, txt = hits[0]
    res = json.loads(txt)
    os.makedirs(W + '/raw', exist_ok=True)
    json.dump({'tool_use_id': tid, 'input': inp, 'result': res}, open(W + '/raw/%s.json' % label, 'w'), ensure_ascii=False)
    print('saved raw/%s.json tool_use_id=%s action=%s dry_run=%s' % (label, tid, inp.get('action'), inp.get('dry_run')))


def load_raw(label):
    return json.load(open(W + '/raw/%s.json' % label))


def creatives_in(obj):
    """all creative dicts (having id + web_view_properties) anywhere in obj"""
    out = []
    if isinstance(obj, dict):
        if 'id' in obj and 'web_view_properties' in obj and 'ad_account_id' in obj:
            out.append(obj)
        else:
            for v in obj.values():
                out += creatives_in(v)
    elif isinstance(obj, list):
        for v in obj:
            out += creatives_in(v)
    return out


def get_creative(label, cid, where='result'):
    r = load_raw(label)[where]
    found = [c for c in creatives_in(r) if c['id'] == cid]
    if len(found) != 1:
        raise SystemExit('expected 1 creative %s in raw/%s.json[%s], found %d' % (cid, label, where, len(found)))
    return found[0]


def cmd_state(ui, label):
    u = units()[ui]
    assert len(u['changes']) == 1
    ch = u['changes'][0]
    assert ch['slot'] == 'creative.web_view_properties.url', ch['slot']
    excl = [e for e in json.load(open(EXCL)) if e.get('platform') == 'snapchat'
            and (e.get('ad_id') in u['ad_ids'] or e.get('ad_id') == u['unit']) and e.get('slot') == ch['slot']]
    o = get_creative(label, u['unit'])
    assert o['ad_account_id'] == u['account_id'], 'account mismatch'
    cur = o['web_view_properties']['url']
    st = classify(cur, ch)
    print('u%d %s type=%s ad_product=%s review=%s updated=%s state=%s excluded=%s' % (
        ui, u['unit'], o.get('type'), o.get('ad_product'), o.get('review_status'), o.get('updated_at'), st, bool(excl)))
    print('  cur', cur)
    for line in str_report(o):
        print('  STR', line)
    if st in ('NOW', 'ALT') and not excl:
        p = copy.deepcopy(o)
        p['web_view_properties']['url'] = ch['new']
        os.makedirs(W + '/payload', exist_ok=True)
        json.dump({'creatives': [p]}, open(W + '/payload/u%d.json' % ui, 'w'), ensure_ascii=False)
        print('payload_file payload/u%d.json' % ui)
        print(safe_dumps({'creatives': [p]}))


def flat(obj, path=''):
    out = {}
    if isinstance(obj, dict):
        if not obj:
            out[path] = {}
        for k, v in obj.items():
            out.update(flat(v, path + '.' + k if path else k))
    elif isinstance(obj, list):
        if not obj:
            out[path] = []
        for i, v in enumerate(obj):
            out.update(flat(v, '%s[%d]' % (path, i)))
    else:
        out[path] = obj
    return out


def find_body(obj):
    """the {'creatives':[...]} body inside a dry-run preview"""
    if isinstance(obj, dict):
        if 'creatives' in obj and isinstance(obj['creatives'], list) and obj['creatives'] and isinstance(obj['creatives'][0], dict) and 'web_view_properties' in obj['creatives'][0]:
            return obj
        for v in obj.values():
            b = find_body(v)
            if b is not None:
                return b
    elif isinstance(obj, list):
        for v in obj:
            b = find_body(v)
            if b is not None:
                return b
    return None


def cmp_objs(a, b):
    fa, fb = flat(a), flat(b)
    diffs = [(k, fa.get(k, '<missing>'), fb.get(k, '<missing>')) for k in sorted(set(fa) | set(fb)) if fa.get(k, '<missing>') != fb.get(k, '<missing>')]
    return diffs


def cmd_cmpdry(ui, label):
    pay = json.load(open(W + '/payload/u%d.json' % ui))
    r = load_raw(label)
    body = find_body(r['result'])
    if body is None:
        print('no creatives body found in the preview; preview text:')
        print(json.dumps(r['result'], ensure_ascii=True)[:4000])
        return
    d = cmp_objs(pay, body)
    print('preview body == payload: %s ; differences: %d' % (body == pay, len(d)))
    for k, x, y in d:
        print('  DIFF', k, repr(x)[:200], '->', repr(y)[:200])
    print('preview (escaped):', json.dumps(r['result'], ensure_ascii=True)[:6000])


def cmd_cmpcall(ui, label):
    pay = json.load(open(W + '/payload/u%d.json' % ui))
    r = load_raw(label)
    sent = r['input'].get('payload')
    if isinstance(sent, str):
        sent = json.loads(sent)
    d = cmp_objs(pay, sent)
    print('sent payload == built payload: %s ; differences: %d ; dry_run=%s ad_account_id=%s' % (
        sent == pay, len(d), r['input'].get('dry_run'), r['input'].get('ad_account_id')))
    for k, x, y in d:
        print('  DIFF', k, repr(x)[:200], '->', repr(y)[:200])


def cmd_diff(bl, al, cid):
    B, A = get_creative(bl, cid), get_creative(al, cid)
    other = []
    for k, vb, va in cmp_objs(B, A):
        tag = 'URL' if k == 'web_view_properties.url' else ('VOLATILE' if k in VOLATILE else 'OTHER')
        if tag == 'OTHER':
            other.append(k)
        print('  %s %s: %r -> %r' % (tag, k, str(vb)[:300], str(va)[:300]))
    print('%s OTHER_FIELD_CHANGES=%d %s' % (cid, len(other), other))


def cmd_url(label, cid):
    o = get_creative(label, cid)
    print('URL=' + o['web_view_properties']['url'])
    print('review_status=%s review_status_details=%r updated_at=%s semantic_id=%s' % (
        o.get('review_status'), o.get('review_status_details'), o.get('updated_at'), o.get('semantic_id')))


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'xt':
        cmd_xt(args[0], args[1])
    elif cmd == 'state':
        cmd_state(int(args[0]), args[1])
    elif cmd == 'cmpdry':
        cmd_cmpdry(int(args[0]), args[1])
    elif cmd == 'cmpcall':
        cmd_cmpcall(int(args[0]), args[1])
    elif cmd == 'diff':
        cmd_diff(args[0], args[1], args[2])
    elif cmd == 'url':
        cmd_url(args[0], args[1])
    else:
        raise SystemExit('unknown command')
