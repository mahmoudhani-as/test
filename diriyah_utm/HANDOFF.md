# Diriyah / Wadi Safar UTM fix: handoff

State at the stop on 12-Oct-2026 (about 14:25 UTC, Whathead asked to sign in again). Everything needed to carry on is in this folder (`diriyah_utm/`).
Copy it to your scratchpad and work there. Do not edit the repo's own app files (`Code.gs`, etc.); they are unrelated.

## What the user asked for and decided

The task: make every final-URL UTM, in every ad account whose name contains "Diriyah" or "Wadi" (Meta, TikTok, Snapchat, X, Google Ads, LinkedIn), follow the
"Diriyah - Campaign Nomenclature Generator" (`in/e2e…xlsx`), which the user calls "the bible". Apply the changes live through the
**Whathead MCP** (`mcp__Whathed_MCP__*`), verify each one, then report the % wrong before and after in an Excel workbook with the ad name on every row.

The rules decided with the user, all binding:
- **Schema:**
  - `utm_campaign = uid_campaign-name_monYY_objective`
  - `utm_term = uid_adset-name_adset-lang`
  - `utm_content = uid_ad-name_format_ad-lang`
  - All lower case. Source and medium come from the Mappings lists.
- **No `utm_id`.** Remove it wherever it appears.
- **Objective** is always added to utm_campaign.
- **Uids** are only the 8-hex codes in Campaign_Code_Generator. If the generator has no code for a name, drop the code. Manazel: use the generator code if it has one.
- **Month** is the month the ad first served (first day with impressions, in the account time zone). "Be extremely accurate." Never served: leave the month out.
- **kva / kvb / kvd** are programmatic-only. On social or search, the ad token is unknown, so it is left out.
- **Ritz Google search** uses `78f964bb_rcsr-search_search_{lang}`.
- **Shared creatives, cards or sub-creatives** that serve ads needing different URLs go to the user to split by hand.
- **12-Oct omit rule:** "for unknown figures like ad tokens write the utm without them". If a part cannot be sourced, leave it out; never invent it.
  If a whole parameter has no known part, drop the parameter.
- **12-Oct:** "apply everything that can be applied", including the Meta 1–7 and X 1–6 batches. If the safety check blocks them again, they go on the user's manual list.
- **12-Oct (apply6 approval):** every remaining apply6 write is approved (1,433 changes in 1,159 units), URL (+ tied UTM field) only. Safety-blocked writes are recorded,
  not worked around; at the end the user is told which permission rule lets them through. Stop everything if Whathead asks to sign in again.

## State at the stop (12-Oct-2026, about 14:25 UTC)

On 12-Oct the user approved every remaining write in `apply6/` (1,433 changes in 1,159 units), including the 176 safety-blocked ones, with these rules: change only the
destination URL (plus a tied UTM field such as TikTok utm_params) and nothing else, at most 2 attempts per write, never delete, never touch anything outside the batch files,
never retry the 19 platform-refused slots, do not work around the safety check, and **stop all runs if Whathead asks to sign in again**.

The `apply6` runs were started (13 workflow runs, ids in `apply6/runs.json`). At about 14:24 UTC Whathead asked to sign in again (X batch 9, Snapchat batch 2, X batch 8),
so **every run was stopped**, as the user asked. Whathead answered again a minute later (fresh login 14:24:40 UTC), but nothing was resumed: the user decides.

**Results of the apply6 run at the stop** (last result line per change; `python3 scripts/check_apply.py . apply6`, every Fixed line equals the plan byte for byte):

| Outcome | Changes |
|---|---|
| Written and read back byte for byte | 314 (Google 5, Meta 36, Snapchat 100, TikTok 59, X 114) |
| Already correct when re-read (no write) | 64 |
| Blocked by the session safety check (not worked around) | 403 (Google 204, Meta 131, Snapchat 56, X 12) |
| Held for the user: TikTok Spark Push (see below) | 72 so far (99 Spark Push units in the plan) |
| Refused by the platform | 9 (8 archived Meta ads, 1 TikTok Spark Pull with expired authorisation) |
| Not written because of the sign-in prompt | 14 |
| No result yet (batch not reached, or in flight at the stop) | 557 (Meta 283, TikTok 194, Snapchat 65, X 15); per batch in `apply6/batches_at_stop.json` |

- X batch 5 wrote and verified 5 cards whose result lines could not be recorded (the safety check denied the local append; it was not worked around):
  units 1981346935652176185, 1981346935845032417, 1981346934557463016, 1981367758236635343, 1981367507114946900. A re-read will show them as correct.
- Writes in flight when the runs were stopped may have no result line (or, on Meta, an unattached new creative). Every unit is re-read first on resume, so nothing is written twice.

**Re-read (`reread2/`) at the stop:** 12 of the 21 jobs are done (every account apply6 does not write to: Google 9282725829 and 9863260160, LinkedIn x3,
Meta 1033388761412991, TikTok 7280828159585468418, Snapchat 623ccdb3 / 7eee5995 / 8a1750fe / 189a5ada / 377f9c96). The Google 8324286739 re-read was stopped.
Still to re-read: Google 8324286739, Meta 1198625455580757 and 2194833637927644, Snapchat b736921f and ebe8d66e, TikTok 7338057963233443842 and 7338074303931449345,
X 18ce55o46uh and 18ce55o46ul (`reread2/job_groups.json`, group "later").

**Interim workbook:** `out/Diriyah_UTM_Verification_2026-10-12_at_signin_stop.xlsx` (recalculated in LibreOffice; all 191 Summary cells equal the Python counts).
"Now" = `work/live_interim2.json` = the at-pause state + the 12 re-read accounts + every apply6 read-back (`scripts/interim_live.py`).

| Scope | Before (11-Oct) | At the stop |
|---|---|---|
| Ad URL slots | 3,339 wrong (100%) | 1,303 wrong (39.0%) |
| Ads with a URL | 2,944 wrong (100%) | 1,041 wrong (35.4%) |
| Switched-on ads | 653 wrong (100%) | 246 wrong (37.7%) |
| Google sitelink assets | 380 wrong (100%) | 21 wrong (5.5%) |

### TikTok Spark Push side effect (found 12-Oct, must not be repeated)

A Spark Push ad (identity_type BC_AUTH_TT **with** a tiktok_item_id) written with the old recipe (full ad/update with video_id and **without** tiktok_item_id)
looked unchanged on the immediate read-back, but **30-60 minutes later TikTok re-published the video as a new post and re-pointed the ad to it**.
The ad loses the original post's likes and comments, and the API refuses to point it back (40002). Read-only check on 12-Oct (`work/spark_check/`):
**53 of the 76 Spark ads written on 11/12-Oct now run on a new post** (list with old and new post ids in the workbook sheet "TikTok posts re-published").
Not affected: Upgraded Smart+ ads (9 of 9 kept their post), Spark Pull ads sent with the same tiktok_item_id (2 of 2), carousels without a post (71 of 71 still have none),
and CUSTOMIZED_USER ads (no post). Ad 1825846574224498 was written this way on 12-Oct at 13:57 UTC before the finding; at 14:22 UTC it still had its original post - re-check it.
**Every Spark Push ad is now held** (`NotAttempted`, "held for the user") until the user decides; the apply script no longer contains the old recipe.

### Session safety check

The auto-mode classifier denied mostly the agents' local Bash steps that build a write payload or append a result line ("Modify Shared Resources", "Auto-Mode Bypass",
"Real-World Transactions", once "Production Deploy"), and a few write calls. Per the docs (code.claude.com, permission-modes / workflows): a matching `permissions.allow`
rule resolves before the classifier, and workflow subagents use the same rules; approval text inside a workflow agent's prompt does not count as the user's approval.
In a cloud session the rules must be committed to the repository's `.claude/settings.json` (single-repo session). The rule that lets the Whathead writes through:
`"permissions": {"allow": ["mcp__Whathed_MCP__google_ads_native_action", "mcp__Whathed_MCP__meta_native_action", "mcp__Whathed_MCP__snapchat_native_action", "mcp__Whathed_MCP__tiktok_native_action", "mcp__Whathed_MCP__x_ads_native_action"]}`
(or `"mcp__Whathed_MCP__*"`). A broad `Bash(python3 *)` rule may be dropped in auto mode (wildcard interpreters), so a re-run should tell the agents to pass payloads
straight to the Whathead tool and record results with the Write/Edit tool rather than Bash. Only the user may add these rules.

## Next step: resume (only when the user says so)

1. Check the connector (`whathead_workspace list_accounts`). If Whathead asks to sign in, stop and tell the user.
2. If the user added the permission rule and/or decided on the Spark Push ads, update `workflows/diriyah-apply-v6.js` (HOW.tiktok holds Spark Push ads; change it only on the user's word).
3. Re-run the apply6 batches that still have changes without a result (`apply6/batches_at_stop.json`), and the blocked ones if the rule is in place.
   Every unit is re-read first, so finished ones come back AlreadyFixed. Same args as before: {platform, dir, root, batches, canary:false}.
4. Re-read the 9 remaining accounts with `workflows/diriyah-keyed-reread-wf_bcf6cc60-eab.js` (jobs: `reread2/job_groups.json` "later"; paths already rewritten for
   this scratchpad - rewrite `in_file`/`out_file`/`new_file` again if the scratchpad path changes).
5. `python3 scripts/merge_live.py . reread2/out`, then `python3 scripts/round_plan.py . round7 --exclude work/excl_platform_refused_v2.json`.
6. Workbook: `FINAL=1 APPLY=apply6 PENDING_LABEL='Not written' python3 scripts/build_final2.py . out/Diriyah_UTM_Verification_<date>_final.xlsx reread2 round7`, then
   `python3 scripts/check_summary.py out/<file>.xlsx work/summary_expected.json --replace` (LibreOffice recalculation + check of every Summary cell).
   For an interim build: `scripts/interim_live.py` first, then `LIVE_FILE=work/live_interim2.json INTERIM='<why>'` with the same command.

## Open questions for the user

These are also in the workbook's "Questions for you" tab.
- **TikTok Spark Push ads (new, 12-Oct):** an API URL edit makes TikTok re-publish the post and detach the ad from the original post. Write them anyway, or leave them to the user (Ads Manager)? 99 units in the plan are held.
- **Resume:** the apply6 run was stopped when Whathead asked to sign in again; resume only on the user's word (and after any permission rule they add).
- **utm_medium:** the generator medium is used per source (google → paid-search, social → paid-social). Keep it, or keep old valid Mappings values?
- **Demand Gen (`gadg`):** the generator has no row for it, so the medium is left out. Should it be paid-display or paid-video?
- **`visitor-diriyah-coe`:** this template campaign name was pasted on the Bujairi, Zallal, Bab Samhan and Shopping 2026 campaigns. Only its name field is used, which merges them in reports.
- **`hs-` prefix:** it is kept on legacy H&S tokens.
- **Source:** the source follows the channel in the campaign name (instagram → meta, twitter → x).
- **Ritz rule:** it is applied to Ritz-Carlton Signature (2026) search only, not to RitzCarlton_Residences 2024.
- **Landing pages:** where the page language contradicts the ad language, the UTM follows the ad. These pages are listed in "Manual - do yourself" ("Still needs you" in final-mode workbooks).

## Files

| File | What it holds |
|---|---|
| `in/` | The generator workbook (`e2e…`) and the 7-Oct "open_items_resolved" sheet (`cdc1…`) |
| `live/*.jsonl` | 11-Oct live inventory: one row per URL slot, with ids, names and statuses |
| `work/scored.json` | The same rows with violations: the "before" |
| `work/targets.json` | **Final correct URL per slot** (5,028 slots; 20 mixed Search/Demand Gen sitelinks have no single target) |
| `work/live_now.json` | 12-Oct keyed re-read: `platform\|ad_id\|slot` → `{url, status_now, found, note}` |
| `work/first_serving_all.json`, `work/serving_out_*.json` | First serving dates and never-served notes |
| `work/month_fixes.json`, `work/consistency_fixes.json` | Every month change and every name harmonisation, with the reason |
| `work/legacy_clash_items.json`, `work/omit_items.json` | How each part of each legacy or omit target was sourced, shown as "How each part was sourced" in the workbook |
| `apply/`, `apply2/` | 11-Oct live runs (`out_*.jsonl`; `result=Fixed` means it was read back and matched) |
| `apply4/` | 12-Oct live runs: inputs and read-backs |
| `round4/` | Plan built from the 12-Oct re-read (superseded by `apply5/`) |
| `apply5/` | 12-Oct evening run: inputs, read-backs (`out_*.jsonl`), `status_at_pause.txt` |
| `apply6/` | Plan at the pause (`diff.json`, batches, `manual.json`, `held.json`, `summary.txt`) **and the 12-Oct apply6 run**: `out_*.jsonl` read-backs, `runs.json` (workflow/task ids, stopped runs), `batches_at_stop.json`, `check_at_stop.txt`, agents' `*_work/` folders |
| `work/live_interim.json` | Keyed re-read + apply5 read-backs = live state at the pause |
| `work/live_interim2.json` | `live_interim.json` + the 12 accounts re-read on 12-Oct (`reread2/out`) + every apply6 read-back = live state at the stop |
| `work/spark_check/` | TikTok Spark Push check: `written_spark.json` (every Spark ad written, original post id), `current_items.json` (post ids read 12-Oct ~14:05 UTC), `spark_item_check.json` (53 re-published) |
| `reread2/` | Keyed re-read for the final numbers: `jobs.json` (paths for this scratchpad), `job_groups.json` (A/B/C done, "later" = the 9 accounts apply6 writes to), `runs.json`, `out/` |
| `reread/` | Keyed re-read jobs, inputs and outputs (`out/new_*.jsonl` = ads created since 11-Oct) |
| `scripts/` | See below |
| `workflows/*.js` | Saved Workflow scripts. Today's are `diriyah-apply-v5-*`, `diriyah-keyed-reread-*`, `diriyah-first-serving-dates-v2-*` and `diriyah-review-targets-v*-*` |
| `out/Diriyah_UTM_Verification_2026-10-12_final.xlsx`, `…_interim.xlsx`, `…_at_pause.xlsx`, `…_at_signin_stop.xlsx` | Workbooks sent to the user on 12-Oct (the last one is current; recalculated in LibreOffice) |

Scripts:
- `nomen.py` is the checker.
- `derive.py` derives from the generator.
- `legacy.py` (v6) and `build_legacy_plan.py` do the legacy rebuild.
- `omit.py` and `build_omit_plan.py` implement the 12-Oct rule and the sitelinks.
- `targets.py` gives the final target per slot.
- `fix_months.py` sets month = first serving.
- `consistency.py` harmonises names.
- `merge_live.py` merges the re-read.
- `round_plan.py` builds the pending plan and batches.
- `build_final2.py` builds the workbook (`FINAL=1`: per-platform switched-on ads, "Still needs you", "TikTok posts re-published", statuses Refused / Blocked by safety check / Held; `INTERIM='<why>'` labels an interim build; `REFUSED_FILE` = refused-slot lists). The at-pause version is `build_final2_at_pause.py`.
- `check_summary.py` recalculates a workbook with LibreOffice and checks every Summary cell against `work/summary_expected*.json` (`--replace` keeps the recalculated copy).
- `interim_live.py` builds an interim live file from a partial re-read plus an apply run's read-backs.

## Write recipes (proven on 11 and 12-Oct; also in the apply workflow script)

Every write follows the same sequence: re-read the live entity → if the URL is not "now" or "alt_now", skip → `dry_run:true` → check that only the URL changes → `dry_run:false` → read back and compare byte for byte. At most 2 live attempts per write, never delete anything, and stop all lanes when the Whathead sign-in expires. Check side effects after 60+ minutes on a sample, not only immediately (the TikTok re-publish showed up 30-60 min later).

- **Meta.** Creatives are immutable. Create a new creative that is identical except for the URL, then `POST /<ad_id>` with `creative={"creative_id":…}`. Do not send status. The ad goes back to review (`IN_PROCESS`).
- **Snapchat.** Full-object `PUT /v1/adaccounts/{id}/creatives` with only `web_view_properties.url` changed. For composite creatives, edit each sub-creative. Sub-creatives shared by ads that need different URLs are manual.
- **TikTok.**
  - Manual ads: full `/v1.3/ad/update/` with `utm_params` matching the new URL (no `utm_id`). Send pixel and item ids as exact strings, because the gateway loses precision.
  - Smart+ ads: `smart_plus/ad/update`.
  - **Spark Push ads (BC_AUTH_TT with a tiktok_item_id): DO NOT write them with the old recipe** (video_id, no tiktok_item_id). It passes the immediate read-back,
    but TikTok re-publishes the post 30-60 min later and detaches the ad from the original post (53 of 76 ads on 11/12-Oct). They are held for the user's decision.
  - Spark Pull ads (AUTH_CODE): send the same tiktok_item_id and identity unchanged (2 of 2 kept their post). With expired authorization they cannot be edited, so they are manual.
  - BC_AUTH_TT carousels without a tiktok_item_id: full update as read (71 of 71 still have no post afterwards).
- **Google.** For ads, `AdService` MutateAds `final_urls` with `update_mask` `final_urls`. For sitelinks, `AssetService` MutateAssets on the asset. One asset carries one URL for all its placements.
- **X.** `UPDATE_CARD` with the full components and the new `destination.url`. `IMAGE_WEBSITE` cards must include `experiment_signals`. Links in a published tweet's text cannot be edited, so they are manual.
- **LinkedIn.** `inMailContents` `PARTIAL_UPDATE`. The gateway reports 204 as `BACKEND_ERROR`, so verify by GET.
