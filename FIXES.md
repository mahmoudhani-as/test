# Qiddiya pacing dashboard — what was wrong, and the fix

This is the Apps Script project bound to **V4- SFQC & AAQC Daily Report** (SFQC = Six Flags, AAQC =
Aquarabia). `Code.gs` is the dashboard server and holds every counting rule. `Untitled.gs` holds the
setup menu and the pacing formulas. `Dashboard.html` is the page, `appsscript.json` the manifest, and
`tests/` the synthetic test.

## Short version

1. **The dashboard did not count the way the pacing tabs count**, so the two never agreed (section 1).
2. **The pacing tabs had counting bugs of their own.** Some rows matched nothing, row 28 totalled
   different rows in different columns, and the ROAS divided all revenue by part of the spend (section 2).
3. **The Adjust data was wrong in the sheet.** It had text dates, day/month swaps and overlapping
   imports, and one export was pasted a second time under Aquarabia (sections 2 and 4).
4. **The web link let anyone run the setup functions as you** (section 5).

Every counting rule now lives in `Code.gs`, and the pacing formulas are generated from the same rules,
so the dashboard and the tabs cannot drift apart. In V4 the script never writes into a tab that is
imported from another workbook (section 3).

**Tested**

| | figures compared | differ from the pacing tab |
|---|---:|---:|
| Original code, synthetic workbook | 288 | **118** (the KPI cards showed "—" for Revenue, ROAS, Installs and Bookings) |
| Fixed code, synthetic workbook: as built, after *Clean Adjust Raw*, after a CSV import, with the GA4-revenue switch off | 350 each | **0** |
| *Fix this workbook* on the synthetic workbook (a pasted copy and an IMPORTRANGE copy), then *Undo* | every check passes | 0 writes into imported columns |
| **Your live workbook** (typed copy of 5 Oct), after *Fix this workbook* | 350 | **0**. An independent recount from the raw rows matches all 416 pacing cells it checks |

---

## 1. Why the dashboard disagreed with the pacing tabs

| # | What the dashboard did | Effect |
|---|---|---|
| 1 | Added rows from the Raw data backup and from the platform tabs (META, Snapchat, TikTok, Google, X) on top of Raw data, which already holds them. | Campaigns spelled differently in the backup were **counted twice**. |
| 2 | De-duplicated Raw data by platform + portal + campaign + day. | Two genuine rows for the same campaign and day counted **once**. SUMIFS counts both. |
| 3 | Split campaigns into lines with its own token list. | Different Awareness / Search / App splits on Snapchat, TikTok and Google. |
| 4 | Put every non-awareness X campaign on X App, while the tab took only `*_x_app*`. | X App differed. |
| 5 | The tab and the dashboard disagreed on which rows took GA4 revenue (rows 7, 8, 15 and 16), and the dashboard left out Adjust row 26 (Other). | Revenue and ROAS differed. One switch, `CFG.WEB_REVENUE_FROM_GA4`, now sets both. Its default is `true`, as on the live tab. |
| 6 | Read `Adjust Current`, which the tab never reads. It also gave Adjust rows a portal from the campaign name instead of the app column, and repaired dates and channels with its own rules, which the tab did not apply. | Adjust installs, bookings and revenue differed from the tab. The dashboard still corrects Adjust Raw as it reads it, but now with the same code that builds the tab the formulas read (section 3). |
| 7 | Put any objective on the single-line channels (Meta, Apple, Bidease, InMobi, InMotion), while the tab read only `Conversion`. | Adjust lines differed. |
| 8 | GA4: matched the property name exactly (the tab uses `"Six Flags*"`) and the channel group case-sensitively. It bucketed `snap` anywhere in the source (the tab uses starts-with), and dropped paid sales that have no bucket of their own (the tab puts them in row 26). | GA4 purchases differed. Only Paid Search and Paid Social count as paid. GA4 files X's web sales under Display or Paid Other, so neither side counts them. |
| 9 | Used a 1 Jul floor for Meta in both portals. The tab uses 2 Jul for SFQC. | SFQC Meta differed. |
| 10 | Took InMobi from Raw manual plus the backup on every date, while the tab split them by date. | InMobi differed. Both now read the backup up to 2 Aug and Raw manual from 3 Aug. |
| 11 | Blanked Revenue, ROAS, Installs and Bookings whenever one spending line had no Adjust rows. | The headline numbers disappeared. |
| 12 | The GA4 tables ignored the date filter and listed one row per day × campaign. | Wrong web numbers on those screens. |
| 13 | One Adjust row with a blank channel, or exactly 5,000 Adjust rows, stopped the dashboard. | "Could not read the sheets". |
| 14 | Run-rate and pace divided by days not yet delivered. The trend tooltip crashed for installs. | Misleading per-day figures. |
| 15 | `onOpen()` never called `dashboardMenu_()`. | No Pacing dashboard menu. |

## 2. What was wrong in the report

**The live file** (audited cell by cell on 5 Oct):

| # | Where | Problem | Effect |
|---|---|---|---|
| L1 | SFQC row 22 (Apple) | K22/L22 read **Aquarabia** Adjust rows, and H22/N22 read AAQC Raw data | Six Flags Apple installs and bookings were Aquarabia's (1,815 / 343 on both tabs) |
| L2 | Media rows, both tabs | Wildcard-only SUMIFS with no date window | SFQC's "till 1 Sep" was ignored for media. `_AWRN_` takeover rows matched no row: SFQC 182 rows ($103,009), AAQC 111 rows ($3,678) |
| L3 | Check block | C39 vs C40 | SFQC **MISMATCH $79,860**, AAQC **MISMATCH −$8,212**; G42 showed CHECK on both |
| L4 | Row 24 (InMobi) | Read partial Raw data rows. Raw manual impressions were stored as text ("15,62,702") | SFQC InMobi showed 6.8M impressions instead of 156M; AAQC InMobi spend was $0 |
| L5 | Adjust Raw | 1,839 text dates, 926 day/month swaps, 419 rows repeated by overlapping imports, and a 1,051-row export pasted again under Aquarabia (section 4). Also 362 rows filed under "Other": Untrusted Devices 228, WhatsApp Organic Share 72, Pangle 56, Twitter 6 | September installs were missing and AAQC counted Six Flags results. Row 26 counted fraud-filtered and organic installs as paid |
| L6 | Windows | SFQC ran 22 Jun–1 Sep (typed), AAQC 21 Jun–yesterday | The two tabs and the dashboard reported different periods |
| L7 | Row 28 | F28 and J28 left out the awareness rows 7–10 while X28 included them. The AAQC F28/J28 summed rows 14–24. Only F, J, K, L, M, P and X were totalled | **P28 ROAS divided all revenue by part of the spend**, so it was overstated. AAQC spend skipped InMotion |

**The formula set** of the original project doc (`PACING_ALL`), which the generated formulas start from:

| # | Bug | Now |
|---|---|---|
| 1 | One SUMIFS per wildcard, so a name matching two wildcards was counted twice and the App row was short by the same amount. (The live tabs had a single wildcard on E7, so there the `_AWRN_` rows matched nothing: L2.) | Media rows read the Objective column (P). Each row gets exactly one objective, Awareness first. |
| 2 | X App took only `*_x_app*`, and Google App had no floor on its YouTube part. | X App and Google App are true remainders. Every row has its own floor and the tab's B2:C2. |
| 3 | K28 left out row 26. N26/O26 were copies of InMotion's N25/O25. AAQC N19 used 2 Jul while the rest of the row used 1 Jul. | Row 28 sums the same rows in every column. N26/O26 are cleared, and each row has one floor. |
| 4 | Adjust columns read exact (channel, objective) pairs, so other objectives were in no row. | Single-line channels read every objective, and Conversion rows take what the other rows do not. Row 26 takes every paid channel without a row of its own. |
| 5 | GA4 cells on floored rows (M16/X16 Google Search, M19 Meta) had no floor. | They now start at the floor. Earlier sales are on no row, but still count in C49/D49 (C53 adds them back). |
| 6 | Column N on Google rows counted app-install (UAC) "conversions" as purchases. | N leaves out Google rows that report installs (K > 0), so N21 is now 0. YouTube N10 still counts Google conversions (your call). |
| 7 | Check block: C38 was an old all-time total, and C39 ignored floors, APPLE1 and InMobi. C42–C44 had no end date and ignored row 26, C43 mixed in GA4 revenue, and E41 repeated E40. | C38 and E41 are cleared. C39 and C42–C44 use the rows' windows and floors. G42 now fails only when an install lands on no row. |
| 8 | Labels B21 and B29–B31 described other formulas. | Relabelled. B9/B10, rows 32–34 and AAQC X29 (1.7) are your own content and were left alone. |

## 3. How V4 is built: nothing is written into imported tabs

In V4, four source tabs are `IMPORTRANGE` mirrors of the source workbook (A1 holds the import): Raw data
(A:O), Raw manual (A:O), Adjust Raw (A:K) and APPLE1 (Apple!A:O). GA4 is filled by Supermetrics.
Writing one cell inside an import's range breaks it: A1 shows `#REF!` and the whole tab empties. So
the script works around the mirrors:

| Need | How it is done |
|---|---|
| Each media row's objective | Raw data **column P** (`CFG.OBJECTIVE_COL`), outside the imported A:O. P1 = "Objective", plus one ARRAYFORMULA in P2 generated from `OBJECTIVE_TOKENS`. Leave column P empty below P2. |
| Corrected Adjust data | The pacing formulas (K, L, X and C42–C44) read **Adjust Clean**, a tab the script owns and rebuilds from Adjust Raw. **Adjust Raw is never modified.** |
| Keeping Adjust Clean current | It is rebuilt by an **hourly trigger** (`refreshAdjustClean`), by *Pacing dashboard → Clean Adjust Raw*, by *Fix this workbook*, and by the dashboard whenever it finds Adjust Raw has changed since the last build. |
| Raw manual numbers stored as text | A mirror is left as it is. Row 24 and the dashboard read the text numbers with VALUE(SUBSTITUTE()). A pasted Raw manual is converted, with a backup. |
| Adjust CSV import | Refuses a mirrored Adjust Raw: paste the export into the source workbook instead. In a file where Adjust Raw is a pasted table, the import writes into it. |
| Step 3 (Supermetrics formula) | Refuses a mirrored Raw data. |
| A broken or loading import | `#REF!` or `Loading…` in A1, a missing tab, a moved header, or a Raw data with no rows while Adjust and GA4 have some each raise a critical banner. *Validate* then starts with "CHECK — n critical data issue(s)" before the match count. |

What Adjust Clean corrects:

- text dates and day/month swaps, including short dd/MM pastes;
- overlapping imports (the later import wins, but an all-zero row never replaces a non-zero one);
- cross-app copies (section 4);
- numbers stored as text;
- channel labels: Twitter → X, Pangle → TikTok, Untrusted Devices and "Organic Share" → Organic, and blank channels from the network;
- rows left in the old `Adjust Current` tab, which are folded in.

Every rebuild (hourly, from the menu, by *Fix this workbook* or by the dashboard) rewrites the "Adjust Raw cleanup log" tab with each correction. The dashboard reads Adjust Raw through the
same code in memory, so its Adjust figures are right even before *Fix this workbook* has run. *Validate*
reads Adjust Clean, as the formulas do.

## 4. The cross-app copy in Adjust Raw (rows 9861–10911)

Adjust Raw rows **9861–10911** (1,051 rows, days 15–28 Sep) are an export of both apps pasted a second
time with app = "Aquarabia". 420 of these rows carry Six Flags campaign names, and 1,041 of them repeat
a row found elsewhere in the tab. So AAQC was counting Six Flags installs, bookings and revenue. The
duplicate rule could not catch them, because its key includes the app.

The cleaner now finds such a block: a run of consecutive rows under one app that includes rows named for
the other portal, on days that app already has rows outside the run. It leaves the block out of Adjust Clean and the
dashboard and logs "Cross-app copy removed". SFQC is unchanged. AAQC, 22 Jun – 4 Oct:

| AAQC | with the copies | without them (now) |
|---|---:|---:|
| Adjust installs (L28) | 40,880 | **39,494** (−1,386) |
| Adjust bookings (K28) | 4,558 | **4,354** (−204) |
| Revenue SAR (X28) | 4,806,543 | **4,658,143** (−148,400) |
| ROAS (P28) | 3.65 | **3.53** |
| Installs 15–28 Sep | 4,995 | 3,609 (−28%) |
| Bidease installs (L23) | 772 | 443 |

Optionally, delete that block in the source workbook's Adjust Raw. The script already leaves it out, so
no number moves.

## 5. Web link security

`appsscript.json` deploys the web app as *Anyone, even anonymous*, running as you. Before this version,
anyone with the /exec link could call the script's server functions as you through `google.script.run`.
These included the old *Undo everything* (it replaced Raw data with the 7 Aug backup), the Adjust importer,
*Fix this workbook*, the formula reverts and *Check the setup*.

Now every menu function, and every other function that changes the workbook, imports or exports to
Drive, starts with `requireSheetUser_()`. It runs only when the person running it is the account the
script runs as: from the sheet's menus, the editor or the hourly trigger. A visitor using the web link
gets "This can only be run from the spreadsheet…". The dashboard itself still loads from the link, and
**anyone with the link can still see the numbers**. Change `access` if that is not intended.

Two scopes were added: `userinfo.email` (the guard compares emails) and `script.scriptapp` (the hourly
trigger). **Everyone who uses the menus must authorise once more.** You must also **deploy a new version
of the web app** (section 6, step 6). Until then the link runs the old, unguarded code.

## 6. Install

1. Open V4 → **Extensions → Apps Script**. Replace **Code.gs**, **Untitled.gs** and **Dashboard.html**
   with the files in this folder.
2. **Project Settings** (gear icon) → tick **Show "appsscript.json" manifest file in editor**. Back in the
   editor, open `appsscript.json`, replace its contents with this folder's file, and save.
3. Reload the spreadsheet. The **Qiddiya Setup** and **Pacing dashboard** menus appear.
4. **Qiddiya Setup → Fix this workbook (one run).** Google asks you to authorise the new permissions.
   Allow them, then run it again if it stopped there. It does the following:
   - hidden backups of both pacing tabs (first run only);
   - the Objective column in Raw data P;
   - Adjust Clean, plus the hourly refresh;
   - one date window: AAQC B2:C2 follow SFQC, and SFQC C2 becomes `=TODAY()-1` (first run only);
   - the generated formulas, totals, checks and labels on both tabs.

   It writes nothing into Raw data A:O, Raw manual, Adjust Raw or APPLE1. It is safe to re-run.
5. **Pacing dashboard → Validate against the pacing tabs.** Expect "All 350 figures match the pacing
   tabs", followed by a few notes. The 5 Oct copy gave the 5 notes listed in section 7.
6. Redeploy the web app: **Deploy → Manage deployments → edit (pencil) → Version: New version → Deploy**.
   The URL stays the same.
7. In the **source workbook**, set Raw data **O2** to `=TODAY()-1`. Raw data's N2:O2 there decide which
   days reach V4. Today they point at that file's own SFQC B2:C2, typed as 22 Jun – 1 Oct. Without
   this change, V4's media stops on 1 Oct while Adjust, GA4 and APPLE1 keep growing, so ROAS and CPI
   are overstated from 2 Oct on.

**From then on**

- **Adjust:** paste new Adjust exports into the source workbook's Adjust Raw, as today. Adjust Clean
  follows within the hour, or straight away with *Pacing dashboard → Clean Adjust Raw*, or when the
  dashboard is opened.
- **Raw data column P:** leave the formula in P2 alone. If Raw data is ever a pasted table, paste A:O only.
- **Rule changes:** after editing `OBJECTIVE_TOKENS` or any other rule in Code.gs, re-run *Fix this
  workbook*.
- **Step 3 (Install the formulas):** do not use it for rule changes. It only switches a pasted Raw data
  to the Supermetrics formula, keeps a values backup of the pasted table first, and refuses an imported
  Raw data.

## 7. What to expect

**Totals before → after** on the typed copy of the live file:

- **Before:** the live tabs as they stood on 5 Oct. SFQC media and Adjust rows had no end date, but SFQC's
  GA4 cells, X7/X8/X15/X16 and row 26 stopped at its C2 (1 Sep). AAQC ran 21 Jun – 4 Oct.
- **After:** both tabs run 22 Jun – 4 Oct. The data ends 30 Sep – 1 Oct.

| | SFQC before | SFQC after | AAQC before | AAQC after |
|---|---:|---:|---:|---:|
| Spend USD (rows 7–25) | 401,928 | 522,776 | 326,457 | 348,840 |
| Impressions | 328,667,886 | 504,288,904 | 244,705,267 | 373,040,287 |
| Clicks | 3,411,665 | 3,823,930 | 2,406,843 | 2,644,091 |
| Adjust installs (L28) | 31,427 | 37,526 | 38,172 | 39,494 |
| Adjust bookings (K28) | 3,719 | 4,535 | 4,060 | 4,354 |
| GA4 purchases (M28) | 579 | 703 | 1,670 | 1,664 |
| Revenue SAR (X28) | 2,294,223 | 3,353,817 | 4,339,894 | 4,658,143 |
| Spend SAR (F28) | 1,157,372 | 1,976,093 | 1,020,596 | 1,318,616 |
| ROAS (P28) | 1.98 | 1.70 | 4.25 | 3.53 |
| Spend not on a line (C41) | 79,860 | 0 | −8,212 | 0 |

- **SFQC GA4 579 → 703.** The longer window alone gives 740, and 221,655 SAR of the revenue rise is that
  window's GA4 web revenue. The 2 Jul floor on Google Search and Meta GA4 then takes 37 purchases back.
- **ROAS falls mainly because F28 now includes the awareness spend** (L7).
- **Where the other moves come from:**
  - SFQC Snapchat awareness $18,822 → $121,832: the `_AWRN_` rows (L2).
  - SFQC InMobi $5,183 → $23,021 and 6.8M → 156.2M impressions; AAQC InMobi $0 → $18,706 (L4).
  - Adjust: the September dates are now read (L5), the cross-app copies are out (section 4), and row 26
    is now 0, because Untrusted Devices and WhatsApp Organic Share are Organic and Pangle is TikTok App.
- **Row 28 now also totals** spend USD, impressions, views, clicks and platform purchases/installs, with
  their ratios. N28 is 10,059 (SFQC) and 16,800 (AAQC) without Google's app-install conversions.

**The dashboard after the fix** ("All", 22 Jun – 4 Oct). The cards equal row 28:

| | SFQC | AAQC |
|---|---:|---:|
| Spend | $522,776 | $348,840 |
| Revenue | 3,353,817 SAR | 4,658,143 SAR |
| ROAS | 1.70× | 3.53× |
| Installs (Adjust) · CPI without awareness (blended) | 37,526 · $8.99 ($13.93) | 39,494 · $7.40 ($8.83) |
| Bookings (Adjust) · CPA without awareness (blended) | 4,535 · $75.58 ($115.28) | 4,354 · $67.93 ($80.12) |
| Daily run-rate | $5,228 | $3,488 |

"All" runs to C2 (4 Oct), so the ROAS, CPI and CPA cards add "partial: Adjust to 30/09, GA4 web to
28/09". 7d and 14d end on 30 Sep, the last day both media and Adjust reached. For example, SFQC 7d
shows ROAS 4.34×, CPI $16.33 and CPA $79.90.

**Notes left in the banner and on *Validate*** (none critical):

- **InMobi 3–31 Aug:** SFQC has 5,244 installs, 556 bookings and 416,069 SAR, and AAQC 2,821, 405 and
  306,820 SAR, on days with no spend row (section 8).
- **Bidease SFQC 4–14 Sep:** 333 installs, 26 bookings and 13,948 SAR with no spend row.
- **X campaign under AAQC:** "DNU SFQC-…Six Flags_X_App Installs" is filed under AAQC in Raw data
  column B ($387).
- **Adjust Raw's own problems:** listed, with a note that they are corrected in Adjust Clean.
- **On the page only:** an "Adjust feed dropped?" note for SFQC Google and AAQC Google. SFQC Google had
  7 Adjust installs on $11,487 in the last 14 days, against 24 per $1,000 before, while Google claims 3,901.

## 8. Gaps the script cannot fill

- **InMobi 3–31 Aug.** No tab holds InMobi spend for those days: the backup tab ends on 2 Aug, and Raw
  manual starts on 1 Sep. Adjust does have installs on those days (section 7), so row 24's CPI, CPA and
  ROAS are overstated until the spend is in.
  - **Where to paste:** Raw manual **in the source workbook** (V4's Raw manual is imported from it).
  - **Columns:** A = `InMobi`, B = `SFQC` or `AAQC`, C = campaign name, D = the day as a real date,
    F = impressions, G = spend USD, and H–L if you have them.
  - **What reads it:** row 24 and the dashboard read Raw manual from 3 Aug (`CFG.INMOBI_MANUAL_FROM`)
    and the backup tab up to 2 Aug (`CFG.INMOBI_BACKUP_TILL`). The banner note goes away once the days
    are in.
- **Bidease SFQC 4–14 Sep.** Bidease is read from Raw data, so those days' spend has to reach Raw data
  wherever the source workbook gets Bidease from.
- **The source workbook's window.** See section 6, step 7.
- **"DNU SFQC-…_X_App Installs" under AAQC.** If SFQC pays for it, correct column B in the source.

## 9. Undo and backups

- **Qiddiya Setup → Undo "Fix this workbook"** puts both pacing tabs back exactly as they were before the
  first fix, formulas and B2:C2 included, from the hidden "SFQC/AAQC Pacing_Daily BACKUP <stamp>"
  copies. It also removes the hourly trigger, and asks before it starts.
  - It does not touch Raw data, GA4, Raw manual, Adjust Raw, APPLE1 or "Raw data BACKUP 20260807-1642".
  - Raw data column P and Adjust Clean stay. The old formulas ignore them, so you can delete them by hand.
  - Later runs of *Fix this workbook* make no new pacing backups, so Undo always goes back to the tabs
    as they were before the first fix.
- **Install the original doc formulas (not an undo)** installs `PACING_ALL`, the formula set from the
  original project doc. That is not what the live tabs had. To go back to the unified formulas, use
  *Repair Pacing_Daily formulas* or *Fix this workbook*.
- **Values backups** ("Adjust Raw BACKUP …" before an import, "Raw manual BACKUP …" when a pasted Raw
  manual is converted, "Raw data BACKUP …" before step 3) have stamps to the second. Only the newest 3
  per tab are kept (`CFG.BACKUPS_KEPT`).
- **Never delete "Raw data BACKUP 20260807-1642".** It is data: row 24 reads its InMobi rows for
  16 Jul – 2 Aug, and the script never prunes it.
- **File → Version history** remains the full undo.

## 10. Choices you may want to change

- **Revenue on the four web rows** (7, 8, 15, 16) comes from GA4, as on the live tab, and every other
  row uses Adjust. For Adjust everywhere, set `CFG.WEB_REVENUE_FROM_GA4 = false` and re-run *Fix this
  workbook*. The tab and the dashboard switch together.
- **`CFG.ADJUST_EXCLUDE_UNTRUSTED`** (default `true`) counts Adjust "Untrusted Devices" as Organic, so
  no row counts it. Set it to `false` to put it back on row 26.
- **Snapchat "takeover" and "_AWRN_" campaigns are Awareness.** To change that, edit `OBJECTIVE_TOKENS`
  and re-run *Fix this workbook*.
- **YouTube (N10)** still counts Google "conversions" as platform purchases.
- **Totals include the awareness rows and row 26**, in every column.
  - On the dashboard, CPI and CPA leave out the awareness rows (7–10) and row 26, and show the blended
    figure beside them.
  - ROAS, spend, every total and the line tables stay blended, so they still match row 28.
- **One date window.** AAQC B2:C2 follow SFQC, and SFQC C2 is `=TODAY()-1`. To report a fixed period,
  type a date into SFQC C2. Re-running the fix keeps it.
- **Dashboard dates:**
  - **All** runs from SFQC B2 to the later of C2 and the latest day with data.
  - **Tab period** shows exactly what the tabs count. The button is offered only when the tabs' B2:C2
    is shorter than All. *Validate* always compares that period.
  - **7d / 14d** end on the last day both media and Adjust reached for the portal and lines on screen.
- **Daily run-rate** counts from the selection's first day with spend to its last delivered day. Over
  the full period, the projection adds that rate for the days still ahead.

## 11. What changed, file by file

**Code.gs** (server)

- **Same cells as the formulas.** The payload reads Raw data (with column P), APPLE1, InMobi (Raw manual
  from 3 Aug, the backup up to 2 Aug), Adjust by position and app column, and GA4 with the tab's wildcards.
  The backup merge, the native-tab fill-in and the de-duplication are gone, so every Raw data row counts
  once, as SUMIFS counts it. Adjust is the exception: it is read through the cleaner's corrections, as
  the tab reads Adjust Clean. GA4 rows dated before their line's floor go to `ga4PreFloor` (C49 only).
- **One definition of every line:** `PACING_LINES`, `OBJECTIVE_TOKENS`, `_adjustLine()`, `_ga4Bucket()`.
- **Adjust:** the cleaner and Adjust Clean (section 3), with `_adjustDropMislabelled_` for the cross-app
  copies and `_adjustClassify` for Organic and Pangle. `importAdjustCsv` refuses a mirror, adds up split
  rows within one file, lets a later file replace an earlier file's app-days, replaces exactly the
  app-days present, refuses a 5,000-row export, leaves today out, backs up, then rebuilds Adjust Clean.
- **Data-health banner** (note or critical). It covers:
  - spend with no portal or no row, and column B disagreeing with the campaign's portal;
  - missing, broken or loading tabs, moved headers, and an empty Raw data;
  - Adjust problems, including unreadable and future days;
  - spend gaps (`meta.health.spendGaps`), times of day on the C2 day, B2 after C2, and the AAQC window.

  Each note says whether the tabs, the dashboard or both are affected.
- **`validateDashboard`** compares 350 figures to the cent, reading Adjust Clean as the formulas do: every
  line, row 28 (E–J, N, O, F, K, L, M, X, P), C49/D49 and C41. With a critical issue, the result starts
  with "CHECK".
- **Housekeeping:**
  - `requireSheetUser_()` guards the menu functions (section 5).
  - `_ss()` refuses a `CFG.SHEET_ID` that is not the bound file.
  - Backups are stamped to the second and pruned.
  - Date formatting is cached: a dashboard load made about 147,000 `formatDate` calls, and now about 120.

**Untitled.gs** (setup)

- **`fixThisWorkbook()`** runs the steps in section 6.
- **`buildPacingSpec_()`** generates:
  - the media rows (SUMIFS on column P, with each row's floor and the tab's B2:C2);
  - rows 22 and 24 from `CFG`;
  - the Adjust rows from Adjust Clean;
  - the GA4 floors, and Google N without UAC;
  - row 28 with ratios, plus the check cells and labels (section 2).
- **Menu:** the menu gained *Install the original doc formulas (not an undo)* and *Undo "Fix this
  workbook"*, and `onOpen()` now adds the Pacing dashboard menu too.
- **Step 3** refuses an imported Raw data and backs up a pasted one. *Quick check* and the Validation tab
  check column P and Adjust Clean.

**Dashboard.html** (browser)

- **No classification of its own.** Every row arrives tagged with its pacing row. "Every line" is in
  pacing-row order, and its total is row 28. Revenue, ROAS, Installs and Bookings are always shown.
- **CPI and CPA leave out the awareness rows** and show the blended figure beside them. This applies to
  the cards, rankings, trend and week-over-week.
- **Dates and pace:**
  - Run-rate counts from the first day with spend.
  - 7d/14d end on the last day media and Adjust reached.
  - A "partial: Adjust to dd/mm" note appears when spend runs past a feed.
- **Week-over-week CPI** uses Adjust installs by day.
- **Smaller fixes:**
  - campaign "Days" counts days that delivered;
  - "Where the money went" shows "—" with no spend;
  - unattributed rows carry their portal tag in Both mode;
  - a platform that claims less than 0.7× what Adjust verifies is marked "platform under-reports";
  - the health banner keeps its open or closed state;
  - the light-mode source tags are fixed.
- **"Adjust feed dropped?" tag and note.** They appear when a channel's Adjust installs per $ over the
  last 14 days fall below a tenth of the 28 days before, or when the platform claims at least 10× what
  Adjust verifies. Both windows need $2,000+ spend. The check runs in the browser only.
- **How it adds up → Check it against the tabs** walks each source tab from its plain SUM() to the cards.
  - Media example, SFQC, all dates:

    | Step | Impressions |
    |---|---:|
    | Raw data SUM() | 354,253,073 |
    | + Raw manual SUM() | 23,701,280 |
    | + APPLE1 SUM() | 621,306 |
    | + InMobi stored as text (115,027,745 in Raw manual, 30,063,025 in Raw data) | 145,090,770 |
    | − Raw data InMobi copies | −36,827,172 |
    | − Raw manual Bidease copies | −23,701,280 |
    | + InMobi in the backup tab | 41,150,927 |
    | **= counted** | **504,288,904** |

  - Adjust example: SFQC 38,159 − 483 organic − 147 copies − 3 before the row starts = **37,526**
    installs; AAQC 46,480 − 595 − 6,092 − 299 = **39,494**.
  - With a Platform or Objective filter on, the footer says the table covers every platform.
- **The Method page** describes the current rules: the InMobi dates, column P, Adjust Clean, the CPI/CPA
  exception, and what All / Tab period / 7d cover.

**appsscript.json**: adds the `userinfo.email` and `script.scriptapp` scopes. The web-app settings are
unchanged.

## 12. Tests

```
cd tests && npm install && node harness.js
```

The harness builds `tests/fixture.js`, a synthetic workbook with each trap above. It evaluates the
generated pacing formulas with HyperFormula and runs Code.gs against a mock of the Apps Script API. The
mock stores formulas separately, so a write into an import is caught. It then loads Dashboard.html in
jsdom.

- **Four passes:** as built, after *Clean Adjust Raw*, after a CSV import, and with
  `CFG.WEB_REVENUE_FROM_GA4` flipped to `false`.
  - In each pass, `validateDashboard` compares 350 figures: every line and all of row 28.
  - The page check covers every line (E, G, I, N, O, K, L, M, X) and row 28's F, J, K, L, M, X and P.
    The server check covers the rest of row 28.
  - Every view × portal × filter is rendered without errors.
- ***Fix this workbook*, on a pasted copy:**
  - the column-P formula, which, read independently, equals Code.gs on every row;
  - text numbers converted, the date window, Adjust Clean built and Adjust Raw untouched;
  - the trigger, every generated cell and the two hidden backups;
  - an unchanged re-run, 0 differ, and a clean Quick check;
  - Undo restores the exact pre-fix formulas and removes the trigger.
- ***Fix this workbook*, on an IMPORTRANGE copy:** 0 writes into imported columns, column P added,
  Adjust Clean built, Raw manual untouched, and the importer refuses.
- It ends with `PASSED`.
- `--old DIR` first runs the original files through the same server check (288 compared, 118 differ).
  It currently stops at the page check, which the original page cannot run.

Checks run on the typed copy of the live workbook, outside the repo:

- *Fix this workbook*, then *Validate*: 350 compared, 350 match. The page against the tabs: 0 differ.
- An independent Python recount from the raw rows: 416 pacing cells, 0 differ.
- A simulation of V4's IMPORTRANGE tabs: 0 writes into imported columns, and the importer refused.
