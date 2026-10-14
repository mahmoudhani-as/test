#!/bin/bash
# 14-Oct: merge the re-read after the team's manual changes, rebuild + recalc + check the workbook (run from the diriyah_utm folder)
set -e
python3 scripts/merge_partial.py . reread5/out reread7/out reread7/jobs.json reread8/out
python3 scripts/merge_live.py . reread8/out
OUT=out/Diriyah_UTM_Verification_2026-10-14.xlsx
PREV_LIVE=work/live_now_13oct_final.json TEAM_MARKS=work/team_marks_14oct.json TEAM_DAY=14-Oct TEAM_REREAD="${TEAM_REREAD:-14-Oct 14:47-15:10 UTC}" \
FINAL=1 APPLY=apply6,apply7,apply8,apply9,apply10,apply11,apply12,apply13 PENDING_LABEL='Not written' \
REFUSED_FILE=work/excl_platform_refused_v5.json WADI_FILE=work/wadi_safar_meta_needs_page_v2.json \
REREAD_DATE="${REREAD_DATE:-14-Oct-2026 after the manual changes by your team (full re-read of the 5 accounts they edited, and of every slot still wrong in Snapchat and X); all other slots as re-read on 13-Oct (no change since)}" \
python3 scripts/build_final2.py . $OUT reread8 round10
python3 scripts/check_summary.py $OUT work/summary_expected.json --replace
