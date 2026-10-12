# Diriyah / Wadi Safar UTM fix: handoff

State at the end of 12-Oct-2026. Everything needed to carry on is in this folder (`diriyah_utm/`).
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

## State at the end of 12-Oct

Delivered to the user: `out/Diriyah_UTM_Verification_2026-10-12_final.xlsx`. The Summary uses COUNTIFS on "Every URL". Recalculated in LibreOffice, it matches the Python counts.

| Scope | Before (11-Oct) | Now (12-Oct keyed re-read) |
|---|---|---|
| Ad URL slots | 3,339 of 3,339 wrong (100%) | 2,848 wrong (85.3%) |
| Ads with a URL | 2,944 of 2,944 wrong (100%) | 2,458 wrong (83.5%) |
| Switched-on ads | 653 of 653 wrong (100%) | 455 wrong (69.7%) |
| Google sitelink assets | 380 of 380 wrong (100%) | 376 wrong (98.9%) |

Ad slot status now:

| Status | Slots |
|---|---|
| Fixed 12-Oct | 304 |
| Fixed 11-Oct | 187 |
| Not applied, needs the user's OK | 2,656 |
| Manual for the user | 191 (Snapchat 111, X 73, TikTok 7) |
| Failed | 1 (TikTok `1818763664085073`, ad/update rejected) |

LinkedIn: all 12 slots are correct now.

**Why the rest was not applied.** The session's auto-mode safety check blocked further live writes.
- It treated bulk edits to live ads as "Modify Shared Resources" and later as "Auto-Mode Bypass".
- After that, no more writes were attempted, and no more write workflows were launched.
- The user has to allow them, either by saying so explicitly or by adding a permission rule for `mcp__Whathed_MCP__*` writes.

Done on 12-Oct:
- First-serving dates for all 1,601 + 218 ads were pulled into `work/first_serving_all.json`. Generator months were corrected: 42 changed and 23 removed because the ad never served (`work/month_fixes.json`).
- The legacy rebuild was reworked to v6 (`scripts/legacy.py`) after 3 adversarial review rounds.
- New consistency step (`scripts/consistency.py`): one name per live campaign and per ad set, filled or replaced from strict-matching siblings (`work/consistency_fixes.json`).
- 315 slots were written and read back byte for byte: TikTok 229, X 44, Snapchat 27, Google 4 ads + 8 sitelink assets, Meta 3. The results are in `apply4/out_*.jsonl`.
  - The 2 Google ads `812832821725` and `812832821731` were written from the main session after the agent was stopped. This is noted in the workbook.
  - 7 of the 313 agent writes match an earlier rule version and need a second edit. They are already in round4.
- 7 TikTok Spark Pull ads cannot be edited through the API (expired authorization). They are on the manual list.
- A keyed re-read covered all 4,366 URL rows (`reread/out/*.jsonl`), merged into `work/live_now.json`.

## Next step: apply round 4 (once the user allows live writes)

The `round4/` folder is built from the final targets and the 12-Oct live re-read, so nothing is applied twice.
- **Slots:** 4,305 slots need an edit, in 2,649 edit units with 2,974 changes.
- **Units by platform:** Google 811 ads + 372 sitelink assets, TikTok 461, Meta 359, X 337 tweets, Snapchat 309 creatives.
- **Batches:** listed in `round4/batches.json` as `in_<platform>_<n>.json`; Google sitelinks are `in_google_sl_<n>.json`.
- **Not applied:**
  - `round4/manual.json` holds 184 shared-creative slots, 20 tweet-text links and 6 sub-creative conflicts.
  - `round4/held.json` holds the targets that fail `omit.check_omit`; these are never written.

Steps:
1. **Check the connector.** Run `ToolSearch "select:mcp__Whathed_MCP__whathead_workspace"`, then `whathead_workspace` `list_accounts`. If the connector is not authenticated, stop and tell the user.
2. **Run the apply workflow.** Use `workflows/diriyah-apply-v5-wf_9c6418e1-575.js`, one run per platform, side by side (each workflow has a concurrency cap of 2). Pass these args:
   - `platform`
   - `dir`: absolute path of `round4/`
   - `root`: absolute path of `diriyah_utm/`
   - `batches`: the platform list from `batches.json`
   - `canary`: `true`

   Results go to `round4/out_*.jsonl`. Every write re-reads the slot, compares it with `now`/`alt_now`, dry-runs, writes live, and reads back.
3. **Re-read the slots.** Use `workflows/diriyah-keyed-reread-wf_bcf6cc60-eab.js` with args `{jobs}` from `reread/jobs.json`. Then run:
   - `python3 scripts/merge_live.py .`
   - `python3 scripts/round_plan.py . round5`, which shows anything left
4. **Rebuild the workbook.** Run `python3 scripts/build_final2.py . out/<name>.xlsx`.
   - Change `DIFF` to the newest round's `diff.json`.
   - Make `glob apply*/` also match `round*/out_*.jsonl`, or move the outputs into an `applyN/` folder.
   - Recalculate with LibreOffice (`soffice --headless --convert-to xlsx`) and check the Summary against the printed counts.

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
| `round4/` | Pending plan: `diff.json`, batches, `manual.json`, `held.json`, `summary.txt` |
| `reread/` | Keyed re-read jobs, inputs and outputs (`out/new_*.jsonl` = ads created since 11-Oct) |
| `scripts/` | See below |
| `workflows/*.js` | Saved Workflow scripts. Today's are `diriyah-apply-v5-*`, `diriyah-keyed-reread-*`, `diriyah-first-serving-dates-v2-*` and `diriyah-review-targets-v*-*` |
| `out/Diriyah_UTM_Verification_2026-10-12_final.xlsx` | The workbook sent to the user on 12-Oct |

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
