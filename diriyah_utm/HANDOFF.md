# Diriyah / Wadi Safar UTM fix: handoff

State at the pause on 12-Oct-2026 (evening). Everything needed to carry on is in this folder (`diriyah_utm/`).
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

## State at the pause (12-Oct, evening)

On 12-Oct the user confirmed "go ahead, apply the remaining writes". Later they said "pause everything for now", and every write run was stopped.
After that, the Whathead connector signed out of the session. **It must be reconnected (claude.ai > Customize > Connectors) before anything else can be read or written.**
A new session may be needed for the reconnect to take effect.

Latest workbook sent to the user: `out/Diriyah_UTM_Verification_2026-10-12_at_pause.xlsx`.
- "Now" = the 12-Oct keyed re-read overlaid with every apply5 read-back (`work/live_interim.json`).
- Its Summary formulas, recalculated in LibreOffice, match the Python counts.

| Scope | Before (11-Oct) | At the pause |
|---|---|---|
| Ad URL slots | 3,339 of 3,339 wrong (100%) | 1,680 wrong (50.3%) |
| Ads with a URL | 2,944 of 2,944 wrong (100%) | 1,341 wrong (45.6%) |
| Switched-on ads | 653 of 653 wrong (100%) | 277 wrong (42.4%) |
| Google sitelink assets | 380 of 380 wrong (100%) | 22 wrong (5.8%) |

Ad slot status at the pause:

| Status | Slots |
|---|---|
| Fixed 12-Oct | 1,472 |
| Fixed 11-Oct | 187 |
| Paused - not yet written | 1,245 |
| Not applied - safety check | 176 (Google 162, TikTok 14) |
| Manual for the user | 247 |
| Refused by the platform | 12 |

The safety-check slots were blocked by this session's auto-mode safety check even after the user's OK. The agents did not work around the block.
- If it happens again, the user can add a permission rule for the Whathead Google Ads / TikTok write actions.

**The apply5 run** (`apply5/`, built from the 12-Oct re-read, with 8 platform-refused TikTok ads held):
- `out_*.jsonl` holds 1,522 Fixed result lines: Google 940 (ads and sitelinks), X 259, Snapchat 159, TikTok 122, Meta 42.
- Every Fixed line was read back byte for byte. Use `python3 scripts/check_apply.py . apply5` to see it per batch.

**Refused by the platform (never retry; on the manual list):**
- Google, 4 ads:
  - 2 have a PROHIBITED symbols finding in their existing ad text (`788673874481`, `788673874484`).
  - 2 have other policy findings.
- Meta, 7 ads:
  - 6 are page-only creatives in Instagram-only ad sets, where Meta requires an Instagram account.
  - 1 is the `t.co` link ad. Its new creative `28547059748288778` was not attached, because Meta would show "t.co" as the headline.
- TikTok, 8 ads: 7 Spark Pull ads with expired authorisation, plus `1818763664085073`. These are in `work/excl_platform_refused.json`.
- All 19 are listed in `work/excl_platform_refused_v2.json`.

**Orphans and interrupted writes:**
- Two unattached Meta creatives exist: `28547059748288778` and `1140805768470919`. They are harmless.
- Writes that were in flight when the runs were stopped may have left one more unattached Meta creative, or a write with no result line.
- On resume every unit is re-read first and recorded as AlreadyFixed when it already has the new URL, so nothing is written twice.

## Next step: resume with `apply6/` (once Whathead is connected again)

`apply6/` is the remaining plan, built from the targets plus the state at the pause. It was made with:

```
LIVE_FILE=work/live_interim.json python3 scripts/round_plan.py . apply6 --exclude work/excl_platform_refused_v2.json
```

- **Slots:** 1,572 slots (sitelink placements included) still need an edit, in 1,159 units with 1,433 changes.
- **Units:** TikTok 331, Meta 310, Google 221 ads + 18 sitelink assets, Snapchat 153, X 126.
- **Batches:** 65, listed in `apply6/batches.json` (Google 5, Meta 26, Snapchat 8, TikTok 17, X 9).
- **Included:** the 176 safety-check slots. The user approved them, so they are retried; if the check blocks them again, they are recorded and reported.

Steps:
1. **Check the connector.** Run `ToolSearch "select:mcp__Whathed_MCP__whathead_workspace"`, then `list_accounts`.
2. **Apply.** Use `workflows/diriyah-apply-v6.js`, with args:
   - `platform`
   - `dir`: absolute path of `apply6/`
   - `root`: absolute path of `diriyah_utm/`
   - `batches`: the list from `batches.json`
   - `canary`

   On 12-Oct every platform's canary passed, so `canary:false` is fine. Split each platform's batches across 2-4 runs to go faster: the concurrency cap is 2 agents per run, and the machine had plenty of headroom with 12 runs.
   - The Workflow tool needs the user's opt-in, such as ultracode or "use a workflow". Without it, run the batches with background Agent subagents, one batch file each, using the same prompt text (COMMON + HOW[platform] from the script).
3. **Check every batch.** Run `python3 scripts/check_apply.py . apply6`.
4. **Re-read.** Use `workflows/diriyah-keyed-reread-wf_bcf6cc60-eab.js` with `{jobs}` from `reread2/jobs.json`, which writes to `reread2/out/`. Then run:
   - `python3 scripts/merge_live.py . reread2/out`
   - `python3 scripts/round_plan.py . round7`, for anything left
5. **Rebuild the workbook.** Run `python3 scripts/build_final2.py . out/<name>.xlsx reread2 round7`, with env `APPLY=apply6`.
   - For an interim build without a re-read, use `LIVE_FILE=work/live_interim.json` and run `scripts/overlay_live.py` first.
   - Recalculate with `soffice --headless --convert-to xlsx` and check the Summary against the printed counts.

**Rebuilding targets from scratch.** Run `scripts/rebuild_all.sh`. It runs legacy → omit (+ sitelinks) → targets → fix_months → consistency.

## Open questions for the user

These are also in the workbook's "Questions for you" tab.
- **utm_medium:** the generator medium is used per source (google → paid-search, social → paid-social). Keep it, or keep old valid Mappings values?
- **Demand Gen (`gadg`):** the generator has no row for it, so the medium is left out. Should it be paid-display or paid-video?
- **`visitor-diriyah-coe`:** this template campaign name was pasted on the Bujairi, Zallal, Bab Samhan and Shopping 2026 campaigns. Only its name field is used, which merges them in reports.
- **`hs-` prefix:** it is kept on legacy H&S tokens.
- **Source:** the source follows the channel in the campaign name (instagram → meta, twitter → x).
- **Ritz rule:** it is applied to Ritz-Carlton Signature (2026) search only, not to RitzCarlton_Residences 2024.
- **Landing pages:** where the page language contradicts the ad language, the UTM follows the ad. These pages are listed in "Manual - do yourself".

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
| `apply6/` | **Remaining plan at the pause**: `diff.json`, batches, `manual.json`, `held.json`, `summary.txt` |
| `work/live_interim.json` | Keyed re-read + apply5 read-backs = live state at the pause |
| `reread/` | Keyed re-read jobs, inputs and outputs (`out/new_*.jsonl` = ads created since 11-Oct) |
| `scripts/` | See below |
| `workflows/*.js` | Saved Workflow scripts. Today's are `diriyah-apply-v5-*`, `diriyah-keyed-reread-*`, `diriyah-first-serving-dates-v2-*` and `diriyah-review-targets-v*-*` |
| `out/Diriyah_UTM_Verification_2026-10-12_final.xlsx`, `…_interim.xlsx`, `…_at_pause.xlsx` | Workbooks sent to the user on 12-Oct (the last one is current) |

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
- `build_final2.py` builds the workbook.

## Write recipes (proven on 11 and 12-Oct; also in the apply workflow script)

Every write follows the same sequence: re-read the live entity → if the URL is not "now" or "alt_now", skip → `dry_run:true` → check that only the URL changes → `dry_run:false` → read back and compare byte for byte. Never retry a write more than twice, never delete anything, and stop all lanes when the Whathead sign-in expires.

- **Meta.** Creatives are immutable. Create a new creative that is identical except for the URL, then `POST /<ad_id>` with `creative={"creative_id":…}`. Do not send status. The ad goes back to review (`IN_PROCESS`).
- **Snapchat.** Full-object `PUT /v1/adaccounts/{id}/creatives` with only `web_view_properties.url` changed. For composite creatives, edit each sub-creative. Sub-creatives shared by ads that need different URLs are manual.
- **TikTok.**
  - Manual ads: full `/v1.3/ad/update/` with `utm_params` matching the new URL (no `utm_id`). Send pixel and item ids as exact strings, because the gateway loses precision.
  - Smart+ ads: `smart_plus/ad/update`.
  - Spark Ads: send the identity fields unchanged and leave out `tiktok_item_id`.
  - Spark Pull ads with expired authorization cannot be edited, so they are manual.
- **Google.** For ads, `AdService` MutateAds `final_urls` with `update_mask` `final_urls`. For sitelinks, `AssetService` MutateAssets on the asset. One asset carries one URL for all its placements.
- **X.** `UPDATE_CARD` with the full components and the new `destination.url`. `IMAGE_WEBSITE` cards must include `experiment_signals`. Links in a published tweet's text cannot be edited, so they are manual.
- **LinkedIn.** `inMailContents` `PARTIAL_UPDATE`. The gateway reports 204 as `BACKEND_ERROR`, so verify by GET.
