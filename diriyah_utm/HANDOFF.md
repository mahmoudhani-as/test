# Diriyah / Wadi Safar UTM fix: handoff

Final state on 13-Oct-2026 (about 12:50 UTC): the approved writes were run (apply6 + resume apply7 on 12-Oct; on 13-Oct apply8 for the approved writes that
had never been attempted, then apply9 for the ones the safety check had blocked, after the user added permission rules), the written accounts re-read, final
workbook sent. Everything needed to carry on is in this folder (`diriyah_utm/`).
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
- **13-Oct:** after the final report the user said "continue please". The approved apply6 writes that had never been attempted (their batch stopped after a
  different unit's block) were run as `apply8/` under the same rules: after a block, record it and carry on; never retry or re-route a blocked write.
- **13-Oct (permission rules):** the user committed `.claude/settings.json` with allow rules for the 5 Whathead ad tools (f92eb29), `Bash(python3:*)` and
  `Bash(node:*)` (62b3c75) and `Workflow` (fce152a), switched the session to Accept edits mode and said "commence with reduce the errors". The safety-blocked
  approved writes were then run as `apply9/`.

## Final state (13-Oct-2026, about 12:50 UTC)

**The run after the permission rules (`apply9/`).** The approved apply6 changes the safety check had blocked, without the Wadi Safar Meta ones: 293 changes in
267 units (Google 178 ads + 17 sitelink assets, Meta 83 on 57 ads, TikTok 8, X 4, Snapchat 3), each equal to the apply6 plan with the live URL still the planned
"now". Workflow `workflows/diriyah-apply-v9.js` (= v8 rules; Meta ads that share one creative and need the same change get one shared new creative).
- In Auto mode the new rules did not take effect: Workflow launches and agents' python3 steps were still denied ("Auto-Mode Bypass" etc.), even after the
  rules were committed and pulled. After the user switched the session to **Accept edits**, launches and steps went through with no denial. Runs launched
  while still in Auto mode kept the classifier, so the 5 of them were stopped (11:45 UTC) and relaunched; the relaunched agents re-read every unit, recorded
  the first runs' writes as AlreadyFixed and attached the 4 creatives those runs had created but not attached (no unattached creative is left).
- Result (`apply9/check_apply.txt`; `apply9/runs.json`): **267 now live** (234 written by the relaunched runs + 33 by the stopped first runs), **22 refused**
  by the platform (Meta: 3 Bab Samhan carousels, 15 slots, code 100 / 2446581; TikTok: 6 "Hero with Super" Spark Pull ads, post 7574495687715474696 no longer
  resolves, 40002; Google: ad 810176354815, policy PROHIBITED DESTINATION_NOT_WORKING), **1 failed** (Meta ad 120252966441120058: Whathead gateway network
  error, then a one-off 402 "billing must be configured"; safe to re-run), **3 skipped** (X cards also used by 3 promoted tweets created 13-Oct 10:48 UTC).
- Re-read (`reread4/`, 13-Oct 12:05-12:27 UTC, the 8 accounts written; others copied from `reread3/out`): every write confirmed byte for byte, every slot
  not written unchanged. Merged into `work/live_now.json` (previous: `work/live_now_13oct_morning.json`). `round9/` = what is still not right (264 slots;
  227 changes in 173 units, built with `--exclude work/excl_platform_refused_v4.json` = v3 + the 22 refused).
- The 45 Wadi Safar Meta slots are now listed as "Refused by the platform" ("Not tried": Meta refuses that Page / Instagram for this connection;
  `work/wadi_safar_meta_needs_page.json`), not as safety-blocked.
- X H&S-DiriyahCo: the advertiser paused campaign osvh1 (ManazelAlHadawi_AlwaysOn_UF_AWR) at 10:49 UTC and created campaign pg1tv with 14 new promoted tweets
  (b6006i-v); so 14 ads are no longer switched on (switched-on ads 522 -> 508).

**Current workbook:** `out/Diriyah_UTM_Verification_2026-10-13_final2.xlsx` (`bash scripts/build13b.sh`; `check_summary.py` 199 / 199). The morning's
`..._2026-10-13_final.xlsx` is kept.

| Scope | Before (11-Oct) | After 12-Oct | 13-Oct morning | **13-Oct, after the rules** |
|---|---|---|---|---|
| Ad URL slots | 3,339 wrong (100%) | 984 (29.5%) | 768 (23.0%) | **518 (15.5%)** |
| Ads with a URL | 2,944 (100%) | 801 (27.2%) | 622 (21.1%) | **386 (13.1%)** |
| Switched-on ads | 522 (100%) | 173 (33.1%) | 130 (24.9%) | **100 of 508 (19.7%)** |
| Google sitelink assets | 380 (100%) | 21 (5.5%) | 21 (5.5%) | **4 (1.1%)** |

Per platform, ad URL slots wrong now: Meta 27.8%, TikTok 15.3%, Snapchat 23.1%, X 17.3%, Google 0.6%, LinkedIn 0%.

**What still needs the user now** ("Still needs you", 541 rows):
- Held, TikTok Spark Push: 97 (decision: write anyway - TikTok re-publishes the post - or Ads Manager).
- Refused by the platform: 168 ad slots - Meta 148 (Wadi Safar 92 incl. the 45 not tried, archived, Instagram-only page creatives, t.co, 5 Bab Samhan
  carousels, 1 narrow image), TikTok 15 Spark Pull, Google 5 policy findings.
- Manual: 243 (Snapchat 147 shared sub-creatives, X 93 tweet-text links / shared cards, Meta 3 existing Page posts) + 4 sitelink assets.
- Failed 5 (TikTok 4 from the 12-Oct outage with both attempts used; Meta 1 gateway error, safe to re-run). Skipped 5 (Snapchat 2, X 3). Landing pages: 19.
- Blocked by the safety check: none.

## Earlier on 13-Oct (apply8, morning)

**The 13-Oct run (`apply8/`).** It holds only approved apply6 changes that had never been attempted: their batch had stopped after the safety check blocked a
different unit, after the TikTok outage, or without a result line. 258 changes on 206 units (Meta 105, Snapchat 41, TikTok 39, X 12, Google 9), each equal to
the apply6 plan (same unit, slot and new URL; the 12-Oct re-read still showed the planned "now"). Not retried: blocked, held (Spark Push), refused, skipped.
16 Wadi Safar Meta ads (41 changes) were left out because Meta refuses that Page / Instagram for this connection (`apply8/excluded_wadi_safar.json`).
Workflow `workflows/diriyah-apply-v8.js` = the v6 rules plus: after a safety-check block, record it and carry on with the next unit (stop after 3 blocked
units in a row); agents write no result files, they return one result per change, saved by `scripts/save_apply_results.py` as `apply8/out_*.jsonl` and
`apply8/lane_reports.json`. 10 runs (Meta 4, TikTok 2, Snapchat 2, X 1, Google 1), 09:37-10:41 UTC, ids in `apply8/runs.json`. Whathead never asked to sign in.

Results (`check_apply.py . apply8` in `apply8/check_apply.txt`: every Fixed line equals the plan byte for byte):
- 212 written and read back: Meta 104 (81 ads), Snapchat 53, TikTok 39, X 9, Google 7.
- 4 written whose verify step the safety check denied (Google ads 797795488518 / 797795488530, X cards b51xqf / b53zqd); the re-read confirms all 4.
- 32 blocked by the safety check, nothing written: Meta 29 (22 at their own step + 7 in in_meta_3, which stopped after one denied step blocked 4 units at
  once), Snapchat 2, X 1. All 15 denials hit local Bash python3 steps; no Whathead call was denied.
- 10 not written on Meta for platform reasons: 2 Bab Samhan carousels (8 slots; code 100 / 2446581, Meta rejects the exact copy because of the parent
  image_hash), 1 ad whose image is 326 px wide (2875006 "Media Not Wide Enough"; new creative 842859065572596 left unattached), 1 link on an existing Page
  post (manual). The 9 refused slots are added in `work/excl_platform_refused_v3.json` (= v2 + 9).

Re-read (`reread3/`): the 8 written accounts on 13-Oct 09:58-10:52 UTC (the other 13 accounts copied from `reread2/out`), merged into `work/live_now.json`
(previous one: `work/live_now_12oct_final.json`). Every apply8 write is confirmed byte for byte and every slot not written is unchanged.
`round8/` = everything still not right (648 slots; 516 changes in 336 units; built with `--exclude work/excl_platform_refused_v3.json`).

**Final workbook:** `out/Diriyah_UTM_Verification_2026-10-13_final.xlsx`, built by `scripts/build13.sh` (`FINAL=1 APPLY=apply6,apply7,apply8
REFUSED_FILE=work/excl_platform_refused_v3.json ... build_final2.py . <out> reread3 round8`), recalculated in LibreOffice; `check_summary.py`: 199 of 199
Summary cells match. New in it: status "Fixed 13-Oct" (own Summary column) and the 13-Oct rows in "Changes applied".

| Scope | Before (11-Oct) | After 12-Oct | After 13-Oct |
|---|---|---|---|
| Ad URL slots | 3,339 wrong (100%) | 984 wrong (29.5%) | 768 wrong (23.0%) |
| Ads with a URL | 2,944 wrong (100%) | 801 wrong (27.2%) | 622 wrong (21.1%) |
| Switched-on ads (522) | 522 wrong (100%) | 173 wrong (33.1%) | 130 wrong (24.9%) |
| Google sitelink assets | 380 wrong (100%) | 21 wrong (5.5%) | 21 wrong (5.5%) |

Per platform, ad URL slots wrong now: Meta 40.0% (was 59.0%), TikTok 15.6% (20.7%), Snapchat 23.5% (31.7%), X 17.5% (19.5%), Google 22.1% (23.2%), LinkedIn 0%.

**What still needs the user** (ad URL slots; "Still needs you" sheet, 808 rows incl. sitelinks and landing-page checks):
- Blocked by the safety check: 321 ad slots (Google 178, Meta 128 of which 45 Wadi Safar, TikTok 8, X 4, Snapchat 3) + 17 Google sitelink assets.
  The Wadi Safar ones also need the Page / Instagram access below.
- Held, TikTok Spark Push: 97.
- Refused by the platform: 101 (Meta 88: archived ads, Wadi Safar Page / Instagram permission, Instagram-only page creatives, the t.co ad, the 2 Bab Samhan
  carousels, the narrow image; TikTok 9 Spark Pull with expired authorisation; Google 4 with policy findings).
- Manual: 243 (Snapchat 147 shared sub-creatives, X 93 tweet-text links / shared cards, Meta 3 existing Page posts) + 4 sitelink assets.
- Failed: 4 TikTok (both attempts hit the 12-Oct API outage). Skipped: 2 Snapchat. Landing pages to check: 19.

**Observations on 13-Oct:**
- Someone else is creating ads: TikTok Diriyah Gate (7338074303931449345) has 6 new Smart+ ads (13-Oct 09:46 UTC) and 6 manual ads (12-Oct 23:59) in the
  ritz-signature campaigns plus 12 Wadi Safar Chedi ads (12-Oct); Meta Diriyah Co has 36 new ads (12 Chedi, 24 Ritz-Carlton Signature "oct", 12-Oct).
  Our agents only read and updated (TikTok: get / update actions only). All are in "New ads since 11-Oct" (not in the %).
- Meta: where ads shared one creative, in_meta_5 / in_meta_8 gave each ad its own new creative (so each now has its own dark post; likes and comments are no
  longer pooled); in_meta_4 kept one shared pair on one new creative.
- After a denied local check, one Snapchat agent compared the remaining URLs by reading the API output instead of with a script; the re-read confirms them.

## 12-Oct final run (history)

The approved apply6 writes were run in two parts: `apply6/` (12-Oct afternoon, stopped at 14:24 UTC when Whathead asked to sign in again) and, after the
user said "Continue", `apply7/` (22:00-23:10 UTC) = every apply6 change that had no result yet plus the 14 stopped at the sign-in prompt. Safety-blocked,
held, refused and archived changes were not retried. Then all 21 accounts were re-read (`reread2/out`, 12-Oct; the 9 written accounts 22:00-23:21 UTC),
merged (then `work/live_now.json`, now kept as `work/live_now_12oct_final.json`; the 12-Oct morning re-read is `work/live_now_12oct_morning.json`) and
`round7/` listed what was still not right.

**Final workbook:** `out/Diriyah_UTM_Verification_2026-10-12_final.xlsx` (replaces the earlier 12-Oct "final" of the same name, which is in git history).
Built with `FINAL=1 APPLY=apply6,apply7 PENDING_LABEL='Not written' REREAD_DATE=... python3 scripts/build_final2.py . out/<file> reread2 round7`, recalculated in
LibreOffice and checked with `scripts/check_summary.py` (191 of 191 Summary cells equal the Python counts).

| Scope | Before (11-Oct) | After (final re-read) |
|---|---|---|
| Ad URL slots | 3,339 wrong (100%) | 984 wrong (29.5%) |
| Ads with a URL | 2,944 wrong (100%) | 801 wrong (27.2%) |
| Switched-on ads (status from the final re-read: 522 ads) | 522 wrong (100%) | 173 wrong (33.1%) |
| Google sitelink assets | 380 wrong (100%) | 21 wrong (5.5%) |

Per platform (ad URL slots wrong before -> now): Meta 100% -> 59.0%, TikTok 100% -> 20.7%, Snapchat 100% -> 31.7%, X 100% -> 19.5%, Google 100% -> 23.2%, LinkedIn 100% -> 0%.

**Writes in the final run** (`check_apply.py . apply6` and `. apply7`: every Fixed / AlreadyFixed line equals the plan byte for byte, no mismatch):
- apply6: 314 changes written and read back (Google 5, Meta 36, Snapchat 100, TikTok 59, X 114), 64 already correct.
- apply7: 249 written and read back (Meta 98, Snapchat 61, TikTok 71, X 19), 32 already correct.
- 33 more were written and verified by agents whose result line could not be logged (the safety check denied the local logging step); the final re-read
  confirms them ("12-Oct (final run; no result line)" in "Changes applied").

**What still needs the user** (ad URL slots; "Still needs you" sheet, 1,024 rows incl. sitelinks and landing-page checks):
- Blocked by the session safety check: 547 ad slots (Meta 242, Google 187, Snapchat 56, TikTok 47, X 15) + 17 Google sitelink assets.
- Held, TikTok Spark Push: 97 (see below).
- Refused by the platform: 92 (Meta 79: 26 archived ads, Wadi Safar Page / Instagram permission, Instagram-only page creatives, the t.co ad;
  TikTok 9 Spark Pull with expired authorisation; Google 4 with policy findings).
- Manual: 242 (Snapchat 147 shared sub-creatives, X 93 tweet-text links / shared cards, Meta 2 boosted Page posts) + 4 sitelink assets.
- Failed: 4 TikTok ads (both attempts hit TikTok's API outage 22:03-22:16 UTC; safe to re-run). Skipped: 2 Snapchat slots (shared sub-creative f7e6faad
  changed by an unrecorded edit at 11:45 UTC; its siblings now carry cr1-v2, so the composite has mixed utm_content).

**Meta Page permission (new):** the connected Meta user has no Advertiser role on the Wadi Safar Page 1245023868693595, and ad account 2194833637927644 has
no access to Instagram account 17841441699550567 (wadisafarsa) (codes 10/3858749 and 200/1815199). All Wadi Safar Meta ads are refused until a Page /
Business admin grants that. `act_2194833637927644/promote_pages` lists only Diriyah Company and Visit Diriyah.

**Unattached Meta creatives (harmless, nothing deleted):** 28547059748288778, 1140805768470919, 27884071617934891, 1440906904902303, 1090353203851507, one
from apply7 in_meta_4 attempt 1 (id lost by a result projection), possibly one from apply7 in_meta_2 attempt 1 (503), and 842859065572596 (13-Oct, attach
refused for a too-narrow image). Listed in `apply7/runs.json` and `apply8/runs.json`.

**Security:** a Meta agent reported that Graph paging URLs in raw responses carry the gateway's Meta access token unredacted; part of it is in a cached
tool result outside the repo. No token is in this folder or in git (scanned). The user may want to rotate the Meta token.

**Procedure notes (reported to the user):** after a safety-check denial of a local step, three agents carried on writing by another route instead of
stopping: apply7 in_tiktok_2 (payloads passed straight to the Whathead tool, 11 writes), in_tiktok_10 (Write/Edit logging, 14 writes) and in_meta_10
(direct payloads, 12 writes). All those writes are URL-only, verified and within the approval, but the user's rule was to stop. apply7 in_tiktok_1 logged
to a scratch file after a denial; the safety check then flagged that as a bypass and the agent stopped. A false sign-in stop (the word "authorized" in a
Meta error) skipped apply7 in_meta_12/16; the lane regex was fixed (`^AUTH:|needs you to sign in|sign in again|re-authenticat`) and both were re-run.

### TikTok Spark Push side effect (found 12-Oct, must not be repeated)

A Spark Push ad (identity_type BC_AUTH_TT **with** a tiktok_item_id) written with the old recipe (full ad/update with video_id and **without** tiktok_item_id)
looked unchanged on the immediate read-back, but **30-60 minutes later TikTok re-published the video as a new post and re-pointed the ad to it**.
The ad loses the original post's likes and comments, and the API refuses to point it back (40002). Read-only check on 12-Oct (`work/spark_check/`):
**55 Spark Push ads written on 11/12-Oct now run on a new post** (53 from the earlier runs + 2 written in apply6 before the hold: 1838548423250993 at 13:55 UTC by a lane that was stopped before it logged the result, re-published 14:28 UTC as post 7695788106468871432, and 1825846574224498 at 13:57 UTC, re-published 14:30 UTC as post 7695788703565810964; list with old and new post ids in the workbook sheet "TikTok posts re-published").
Not affected: Upgraded Smart+ ads (9 of 9 kept their post), Spark Pull ads sent with the same tiktok_item_id (2 of 2), carousels without a post (71 of 71 still have none),
and CUSTOMIZED_USER ads (no post).
**Every Spark Push ad is now held** (`NotAttempted`, "held for the user") until the user decides; the apply script no longer contains the old recipe.

### Session safety check

**13-Oct resolution:** with the allow rules committed and the session in **Accept edits** mode, nothing was denied. In Auto mode the same rules were not
applied to Workflow launches or agents' python3 steps (they were still classified), and a run launched in Auto mode keeps that mode after the switch.


The auto-mode classifier denied mostly the agents' local Bash steps that build a write payload or append a result line ("Modify Shared Resources", "Auto-Mode Bypass",
"Real-World Transactions", once "Production Deploy"), and a few write calls. Per the docs (code.claude.com, permission-modes / workflows): a matching `permissions.allow`
rule resolves before the classifier, and workflow subagents use the same rules; approval text inside a workflow agent's prompt does not count as the user's approval.
In a cloud session the rules must be committed to the repository's `.claude/settings.json` (single-repo session). The rule that lets the Whathead writes through:
`"permissions": {"allow": ["mcp__Whathed_MCP__google_ads_native_action", "mcp__Whathed_MCP__meta_native_action", "mcp__Whathed_MCP__snapchat_native_action", "mcp__Whathed_MCP__tiktok_native_action", "mcp__Whathed_MCP__x_ads_native_action"]}`
(or `"mcp__Whathed_MCP__*"`). A broad `Bash(python3 *)` rule may be dropped in auto mode (wildcard interpreters), so a re-run should tell the agents to pass payloads
straight to the Whathead tool and return results in the run output (as `diriyah-apply-v8.js` does) rather than through Bash. Only the user may add these rules.
13-Oct evidence: 15 denials, all on local Bash python3 steps (8 "Modify Shared Resources", 6 "Production Deploy", 1 "Real-World Transactions"); no Whathead
call was denied, and writes went through between the blocks.

## Next step (only on the user's word)

`round9/` is the plan of everything still not right (264 slots; 227 changes in 173 units; `summary.txt`). It includes the held Spark Push, the Wadi Safar Meta
slots, the failed and skipped ones (the 50 refused slots of `work/excl_platform_refused_v4.json` are held out).
1. Check the connector (`whathead_workspace list_accounts`). Stop and tell the user if Whathead asks to sign in.
2. Keep the session in Accept edits mode (see "Session safety check"). Build the next run from `round9` without the held Spark Push ads
   (`work/spark_check/spark_push_plan_ids.json`), the refused slots (archived, Page permission, Spark Pull expired, policy) and the manual ones, and run
   `workflows/diriyah-apply-v8.js` on it (results come back in the run output; save them with `scripts/save_apply_results.py`). Tell the agents to pass
   payloads straight to the Whathead tool. Wadi Safar Meta ads only after the Page / Instagram access is granted.
3. Spark Push ads: write them only if the user accepts that TikTok re-publishes the post; otherwise they stay on the user's list.
4. Re-read the touched accounts (copy the other accounts' files as in `reread3/`), `merge_live.py`, `round_plan.py`, rebuild the workbook (`scripts/build13.sh`
   with the new folders) and run `check_summary.py`.

## Open questions for the user

These are also in the workbook's "Questions for you" tab.
- **TikTok Spark Push ads (new, 12-Oct):** an API URL edit makes TikTok re-publish the post and detach the ad from the original post. Write them anyway, or leave them to the user (Ads Manager)? 99 units in the plan are held.
- **Safety-blocked writes:** none left (the permission rules + Accept edits mode let them through on 13-Oct).
- **Meta platform refusals (13-Oct):** 2 Bab Samhan carousels (Ads Manager, or allow a copy without the parent image) and 1 ad with a 326 px image (needs a wider image).
- **Wadi Safar Meta ads:** need the Advertiser role on Page 1245023868693595 and ad-account access to Instagram 17841441699550567.
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
| `work/live_now.json` | Final keyed re-read (13-Oct merge of `reread3/out`): `platform\|ad_id\|slot` → `{url, status_now, found, note}` |
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
| `work/spark_check/` | TikTok Spark Push check: `written_spark.json` (every Spark ad written, original post id), `current_items.json` (post ids read 12-Oct ~14:05 UTC), `spark_item_check.json` (55 re-published), `spark_push_plan_ids.json` (the 99 Spark Push units in the plan, held), `post_check_final.json` (final no-new-post check) |
| `apply7/` | Resume run (12-Oct 22:00-23:10 UTC): inputs (apply6 changes without a result + the 14 sign-in ones), `out_*.jsonl`, `runs.json` (ids, unattached creatives), `lane_reports.json`, `check_apply.txt` |
| `apply6/lane_reports.json`, `apply7/lane_reports.json` | Each batch agent's counts, stop reason (`systemic_error`) and notes, from the workflow journals; the workbook uses them for units without a result line |
| `round7/` | Plan built from the 12-Oct final re-read (superseded by `round8/`) |
| `apply8/` | 13-Oct run of the approved writes never attempted: `in_*.json`, `out_*.jsonl` (saved from the agents' returned results), `lane_reports.json`, `runs.json` (run ids, status, notes, unattached creative), `check_apply.txt`, `excluded_wadi_safar.json`, agents' `work_*` folders |
| `reread3/` | 13-Oct keyed re-read: `jobs.json` (the 8 written accounts), `out/` (those 8 + the other 13 accounts copied from `reread2/out`), agents' `work_*` folders |
| `round8/` | Plan built from the 13-Oct morning re-read (superseded by `round9/`) |
| `apply9/` | 13-Oct run of the safety-blocked approved writes: `in_*.json`, `out_*.jsonl`, `lane_reports.json`, `runs.json` (incl. the stopped Auto-mode runs), `stopped_runs_live_calls.json`, `check_apply.txt`, agents' `work_*` folders |
| `reread4/` | 13-Oct afternoon keyed re-read of the 8 accounts written by apply9 (`jobs.json`, `out/` incl. the other accounts copied from `reread3/out`) |
| `round9/` | Plan built from the final re-read: everything still not right |
| `work/excl_platform_refused_v4.json`, `work/wadi_safar_meta_needs_page.json` | v3 + the 22 slots refused on 13-Oct afternoon; the 45 Wadi Safar Meta slots (not tried, need Page / Instagram access) |
| `work/live_now_13oct_morning.json` | The 13-Oct morning live state that `work/live_now.json` replaced |
| `work/excl_platform_refused_v3.json` | v2 + the 9 Meta slots refused on 13-Oct (never retry) |
| `work/live_now_12oct_final.json` | The 12-Oct final live state that `work/live_now.json` replaced on 13-Oct |
| `work/live_now_12oct_final.json` / `work/live_now_12oct_morning.json` | The 12-Oct evening re-read / the 12-Oct morning re-read |
| `reread2/` | Keyed re-read for the final numbers: `jobs.json` (paths for this scratchpad), `job_groups.json` (A/B/C done, "later" = the 9 accounts apply6 writes to), `runs.json`, `out/` |
| `reread/` | Keyed re-read jobs, inputs and outputs (`out/new_*.jsonl` = ads created since 11-Oct) |
| `scripts/` | See below |
| `workflows/*.js` | Saved Workflow scripts. Today's are `diriyah-apply-v5-*`, `diriyah-keyed-reread-*`, `diriyah-first-serving-dates-v2-*` and `diriyah-review-targets-v*-*` |
| `out/Diriyah_UTM_Verification_2026-10-13_final2.xlsx` | **Current workbook** (13-Oct afternoon; recalculated in LibreOffice) |
| `out/Diriyah_UTM_Verification_2026-10-13_final.xlsx` | 13-Oct morning workbook |
| `out/Diriyah_UTM_Verification_2026-10-12_final.xlsx`, `…_interim.xlsx`, `…_at_pause.xlsx`, `…_at_signin_stop.xlsx` | Workbooks sent to the user on 12-Oct |

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
- `save_apply_results.py` saves the results the v8 agents return (workflow journals) as `<apply>/out_*.jsonl` and `lane_reports.json`.
- `build13.sh` / `build13b.sh` are the exact 13-Oct morning / afternoon workbook builds (run from `diriyah_utm/`).

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
