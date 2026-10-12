# Diriyah / Wadi Safar UTM fix: handoff

State on 12-Oct-2026, written by the session that did the audit. Everything needed to carry on is in this folder (`diriyah_utm/`).
Copy it to your scratchpad and work there. Do not edit the repo's own app files (`Code.gs`, etc.); they are unrelated.

## What the user asked for and decided

The task: make every final-URL UTM, in every ad account whose name contains "Diriyah" or "Wadi" (Meta, TikTok, Snapchat, X, Google Ads, LinkedIn), follow the
"Diriyah - Campaign Nomenclature Generator" (`in/e2e…xlsx`), which the user calls "the bible". Apply the changes live through the
**Whathead MCP** (`mcp__Whathed_MCP__*`), then report the % wrong before and after, in an Excel workbook with the ad name on every row.

The rules decided with the user, all binding:
- **Schema:**
  - `utm_campaign = uid_campaign-name_monYY_objective`
  - `utm_term = uid_adset-name_adset-lang`
  - `utm_content = uid_ad-name_format_ad-lang`
  - All lower case. Source and medium come from the Mappings lists.
- **No `utm_id`.** Remove it wherever it appears.
- **Objective** is always added to utm_campaign.
- **Uids** are only the 8-hex codes in Campaign_Code_Generator. If the generator has no code for a name, drop the code ("drop the code if it doesn't exist in the generator sheet").
  - Manazel: if the generator has it, use it; otherwise drop it.
- **Month** is the month the ad first served (first day with impressions, in the account time zone). "Be extremely accurate."
- **kva / kvb / kvd** are programmatic-only. On social or search, the ad token is unknown, so it is left out (see the 12-Oct rule below).
- **Ritz Google search** uses `78f964bb_rcsr-search_search_{lang}`.
- **Shared creatives or cards** that serve ads needing different URLs go to the user to split by hand (Snapchat and X only; Meta copies the creative per ad anyway).
- **12-Oct rule (latest):** "for unknown figures like ad tokens write the utm without them". If a schema part cannot be sourced, leave it out. Never invent it.
  - This covers: no usable name, never served (no month), kva, sitelinks with no code, and a campaign shared by several sitelinks.
  - If a whole parameter has no known part, drop the parameter.
  - Implemented in `scripts/omit.py` and `scripts/build_omit_plan.py`.
- **12-Oct:** "apply everything that can be applied". This includes the Meta 1–7 and X 1–6 batches that the session safety check blocked earlier and that had been set aside for the user to do by hand.
  - Try them again.
  - If the safety check blocks them again, they go back on the user's manual list.

## Numbers so far

The live pull was on 11-Oct.

**Before:** every one of 3,339 ad URL slots was wrong (100%), as were all 2,944 ads with a URL and all 653 switched-on ads. 380 Google sitelinks were also wrong.

**Fixed live and read back:** 291 slots. All of them still match the final rules.

**Waiting on the connector:**

| What | Slots | Notes |
|---|---|---|
| Second edits | 102 | Made live on 11-Oct with an older rebuild version. Google kept `googlesearch`/`tactical`/`rsa1`; TikTok/X kept `aud`/`ret`; 6 Snapchat say `display` on a video. `targets.py` shows them as "needs edit". |
| Prepared legacy and generator fixes | 739 | `apply3/in_*.json`, built from the final rules. Includes the 6 Snapchat "outcome unknown" slots and the Meta partial below. |
| Meta 1–7 and X 1–6 batches | 277 | Earlier blocked by the safety check. Rebuild their inputs from `work/apply_plan_legacy.json`; the old `apply2/in_meta_6.json` has 4 stale URLs. |
| Omit-rule URLs ready | 253 ads + 1,689 sitelink placements (380 assets) | `work/omit_items.json` |
| Omit-rule URLs not yet buildable | 1,648 slots on 1,601 ads | Need their first-serving month pulled (`work/omit_need_serving.json`), then rerun `build_omit_plan.py`. |
| Shared creatives for the user to split | 27 units | Snapchat 18, X 9 (`apply_plan_v5.json` → skipped). The first-plan shared ones are in `apply_plan.json` → skipped. |

## Files

| File | What it holds |
|---|---|
| `in/` | The generator workbook (`e2e…`) and the 7-Oct "open_items_resolved" sheet (`cdc1…`) |
| `live/*.jsonl` | 11-Oct live inventory: one row per URL slot, with ids, names and statuses |
| `work/scored.json` | The same rows with violations and the derive result |
| `work/apply_plan.json` | First plan: 146 generator fixes, all applied |
| `work/legacy_clash_items.json`, `work/apply_plan_legacy.json` | Legacy rebuild with the final rules (v4: format-word cut, strict creative-token check) |
| `work/legacy_flagged.json` | What the legacy rebuild could not build. Input to the omit rule |
| `work/omit_items.json`, `work/omit_need_serving.json`, `work/apply_plan_v5.json` | Omit rule output, and the merged plan of legacy + omit units |
| `work/first_serving_all.json` | `platform\|ad_id` → first serving date |
| `work/serving_out_*.json` | Per-account serving pulls, including `never_served` |
| `apply/`, `apply2/` | Inputs and results (`out_*.jsonl`) of the 11-Oct live runs. `result=Fixed` means read back and matched |
| `apply3/` | Prepared batches (745 slots) for the reconnect |
| `scripts/` | `nomen.py` (checker), `derive.py` (generator derivation), `legacy.py` (legacy rebuild), `omit.py` + `build_omit_plan.py` (12-Oct rule), `targets.py` (final target per slot + diff against a fresh pull), `build_final.py` (workbook), `score_live.py`, `build_legacy_plan.py` |
| `workflows/*.js` | Saved Workflow scripts. Run them with `scriptPath` after copying them somewhere readable: inventory, first-serving dates, apply (legacy apply has every platform's write recipe), verify |
| `payloads/` | Ready TikTok Spark payloads (tt2) and Meta payloads (m8) |
| `out/Diriyah_UTM_Verification_2026-10-11_final.xlsx` | Workbook the user has now |

## Steps for the next session

1. **Check the connector.** Run `ToolSearch "select:mcp__Whathed_MCP__whathead_workspace"`, then `whathead_workspace` `list_accounts`. If the connector is not authenticated, stop and tell the user.
2. **Fresh live pull.** Pull the current inventory (`workflows/diriyah-inventory-platform-*.js`, one run per platform) into `live_now/`.
3. **Diff.** Run `python3 scripts/targets.py <dir> live_now`. This gives `work/diff.json`, the slots whose live URL ≠ target. It includes the 102 second edits and the 6 Snapchat unknowns, so nothing is applied twice.
4. **Apply now, in parallel.** Use one apply workflow per platform (`workflows/diriyah-apply-legacy-fixes-*.js`, args `{platform, dir, batches}`). The workflow concurrency cap is 2, so run the platforms side by side. Build the batch files from `diff.json`, grouped into edit units (meta=ad, tiktok=ad, google=ad, snapchat=creative, x=tweet/card, linkedin=creative).
   - The prompt says "user-approved 11-Oct". Update it to say that on 12-Oct the user asked to apply everything, under the 12-Oct omit rule.
5. **Pull serving months.** In parallel with step 4, pull first-serving dates for `work/omit_need_serving.json` (workflow `diriyah-first-serving-dates-*.js`; jobs per account with `ids_file`).
   - Merge the dates into `work/first_serving_all.json` and the `serving_out_*` files (keep `never_served`).
   - Rerun `build_omit_plan.py`, then `targets.py`, and apply the new diff.
   - Sitelinks: rerun after the pull too, because more Google campaigns get a name then.
6. **Review before writing.** Before each big apply, have independent agents check a sample of the target URLs against the generator, adversarially. Past mistakes:
   - `aud`/`ret` audience tags copied as creative names
   - `rsa1`/`googlesearch`/`tactical` kept
   - wrong format
   - old tokens naming another creative

   Every target must pass `omit.check_omit` (the legacy and generator ones pass it too).
7. **Final step.** Do a fresh pull, run `targets.py` for the after %, then rebuild the workbook (`build_final.py` reads `apply*/out` files and needs adapting to `targets.py`/`diff.json`). Send it with `SendUserFile`.
   - Summary: before %, after %, fixed counts.
   - Tabs: every URL with the ad name, changes applied, manual for the user (shared creatives, anything blocked), what was left out per URL, 7-Oct audit, rules.

## Write recipes (proven on 11-Oct; also in the apply workflow script)

Every write follows the same sequence: re-read the live entity → if the URL ≠ "now", skip → `dry_run:true` → check only the URL changes → `dry_run:false` → read back and compare byte for byte. Never retry a write more than twice, and never delete anything.

- **Meta.** Creatives are immutable. Create a new creative that is identical except for the URL, then `POST /<ad_id>` with `creative={"creative_id":…}`. Do not send status. The ad goes back to review (`IN_PROCESS`).
  - Partial from 11-Oct: ad `120253320126610058` already has its new creative `4372459552897444` (kv3 URL). Read that creative back and attach it. Do not create another one.
  - The ready payloads in `payloads/payload_<ad_id>.json` were built from the 11-Oct rule. They match the final targets for those kv ads, but check them against `targets.json`.
- **Snapchat.** Full-object `PUT /v1/adaccounts/{id}/creatives` with only `web_view_properties.url` changed. Composite creatives: edit each sub-creative.
  - 6 slots have an unknown outcome (sign-in expired mid-PUT): creatives `7f09c298`, `9cfff83c`, `d375f2e9`, `deb24163`, `217cc0c5`, `be196a04`. Re-read them first.
- **TikTok.**
  - Manual ads: full `/v1.3/ad/update/`. Send `utm_params` matching the new URL (no `utm_id`).
  - Pixel ids and item ids lose precision through the gateway. Send the exact string (pixel `7347671240183693330`, from `pixel/list`).
  - Smart+ ads: `smart_plus/ad/update`.
  - Spark Ads (`BC_AUTH_TT`, identity `7d136a20-71e2-5fb6-9927-ad76b915fac7`, BC `6846326855419559942`): send the identity fields unchanged plus `video_id`/`image_ids`/`ad_text`/CTA as read, and **leave out `tiktok_item_id`**. This worked on ad `1826384400556033`. Sending `tiktok_item_id` gives `40002` "identity of Spark Ads cannot be updated".
  - The gateway trims a trailing space from `ad_text`. The user said to apply everything, so applying is accepted; record the trim. Affected ads: `1825846574224498`, `1825846579472434`, `1825848985421841`, `1825848991400002`, `1825844845218882`, `1825846957500434`, `1840139996127298`.
- **Google.** For ads, `AdService` MutateAds `final_urls`, `update_mask` `final_urls`. For sitelinks, `AssetService` MutateAssets update `final_urls` on the asset. A shared asset gets one URL for all its placements; the target was built to be valid for all of them.
- **X.** `UPDATE_CARD` with the full components/slides and the new `destination.url`. `IMAGE_WEBSITE` cards must include `experiment_signals`, otherwise the PUT clears them. Skip a card that is shared with tweets outside the unit.
- **LinkedIn.** `inMailContents` `PARTIAL_UPDATE`. The gateway reports HTTP 204 as `BACKEND_ERROR`, but the write succeeds, so verify by GET.
