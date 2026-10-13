#!/bin/bash
# Build + recalc + check the 13-Oct final workbook after apply10-12 (run from the diriyah_utm folder)
set -e
OUT=out/Diriyah_UTM_Verification_2026-10-13_final3.xlsx
FINAL=1 APPLY=apply6,apply7,apply8,apply9,apply10,apply11,apply12 PENDING_LABEL='Not written' \
REFUSED_FILE=work/excl_platform_refused_v5.json WADI_FILE=work/wadi_safar_meta_needs_page_v2.json \
REREAD_DATE='13-Oct-2026 13:45-14:38 UTC for the 9 accounts written or tried after 12:30 UTC (TikTok read at 14:27-14:38, after the Spark Push re-publish), 13-Oct 12:05-12:34 UTC for Google Visit Diriyah and the 2 X accounts, and 12-Oct-2026 for the other 9 accounts (no write since)' \
python3 scripts/build_final2.py . $OUT reread5 round10
python3 scripts/check_summary.py $OUT work/summary_expected.json --replace
