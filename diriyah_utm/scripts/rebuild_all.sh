#!/bin/bash
# v5 chain: legacy rebuild -> omit rule (+ sitelinks) -> targets -> month = first serving -> sibling consistency
set -e
cd "$(dirname "$0")/.."
python3 scripts/build_legacy_plan.py > work/log_legacy.txt
python3 scripts/build_omit_plan.py . > work/log_omit.txt
python3 scripts/targets.py . > work/log_targets.txt
python3 scripts/fix_months.py . > work/log_months.txt
python3 scripts/consistency.py . > work/log_consistency.txt
tail -n 3 work/log_omit.txt work/log_targets.txt work/log_months.txt work/log_consistency.txt
