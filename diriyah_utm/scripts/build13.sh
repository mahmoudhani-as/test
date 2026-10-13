#!/bin/bash
# Build + recalc + check the 13-Oct final workbook (run from the diriyah_utm folder)
set -e
OUT=out/Diriyah_UTM_Verification_2026-10-13_final.xlsx
PERMISSION_RULE='To let the blocked writes through: in auto mode a workflow agent'"'"'s instructions do not count as your approval, so add this allow rule to the repository'"'"'s .claude/settings.json and commit it: {"permissions": {"allow": ["mcp__Whathed_MCP__google_ads_native_action", "mcp__Whathed_MCP__meta_native_action", "mcp__Whathed_MCP__snapchat_native_action", "mcp__Whathed_MCP__tiktok_native_action", "mcp__Whathed_MCP__x_ads_native_action"]}} (or "mcp__Whathed_MCP__*"). On 13-Oct no Whathead call was denied: every block hit an agent'"'"'s local python3 step (building or checking a payload, or bookkeeping). A broad Bash(python3 *) rule may not be honoured in auto mode, so the next run should send payloads straight to the Whathead tools and return its results in the run output (as the 13-Oct run already did).' \
FINAL=1 APPLY=apply6,apply7,apply8 PENDING_LABEL='Not written' REFUSED_FILE=work/excl_platform_refused_v3.json \
REREAD_DATE='13-Oct-2026 (09:58-10:52 UTC) for the 8 accounts written on 13-Oct and 12-Oct-2026 for the other 13 accounts' \
python3 scripts/build_final2.py . $OUT reread3 round8
