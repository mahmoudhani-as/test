"""Estimate the serialized size of Whathead MCP results (json.dumps indent=2, ensure_ascii=False) for TikTok ad/get and
smart_plus/ad/get id batches, using the 12-Oct snapshot (reread2) as a proxy for record contents."""
import json, sys
BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
SNAP = json.load(open(f'{BASE}/reread2/work_tiktok_7338074303931449345/snapshot_current.json', encoding='utf-8'))

def wrapper(action, path, items, page_size=100, sp=False):
    pi = ({'page': 1, 'page_size': page_size, 'total_number': len(items), 'total_page': 1} if sp else
          {'page': 1, 'page_size': page_size, 'total_page': 1, 'total_number': len(items)})
    return {'success': True, 'data': {'success': True, 'action': action, 'method': 'GET', 'path': path, 'dryRun': False,
            'data': {'code': 0, 'message': 'OK', 'request_id': '2026101318042800000000000000000000',
                     'data': {'list': items, 'page_info': pi}},
            'meta': {'tiktokRequestId': '2026101318042800000000000000000000', 'waitedMs': 1234, 'throttled': False,
                     'warnings': [], 'preflightBlocking': False}},
            'meta': {'requestId': '81160a7f-a1b3-4464-b4f1-1a4df1bb9b32', 'latencyMs': 5579}}

def size(obj):
    t = json.dumps(obj, indent=2, ensure_ascii=False)
    return len(t), len(t.encode('utf-8'))

def item_cost(rec):
    """incremental size of one list item (including the ',\n' separator) at list depth"""
    a = wrapper('tiktok_ad_get', '/v1.3/ad/get/', [rec, rec])
    b = wrapper('tiktok_ad_get', '/v1.3/ad/get/', [rec])
    return size(a)[1] - size(b)[1]
