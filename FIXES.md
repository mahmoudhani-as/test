# Qiddiya pacing dashboard — why the numbers were wrong, and the fix

## Short version

There were two problems at once:

1. **The dashboard did not count the way the pacing tabs count.** It read extra tabs, dropped
   real rows, split campaigns into lines with its own rules, took revenue from a different
   source, re-assigned Adjust rows to the other portal, and blanked its KPI cards whenever one
   line had no Adjust rows.
2. **The pacing tabs have counting and total bugs of their own.** Some campaigns were counted
   twice, some were counted nowhere, and row 28 added up different rows in different columns, so
   the ROAS on the report was overstated.

The fix puts every rule in one place (`Code.gs`). The pacing formulas are now *generated* from
those same rules (`Untitled.gs`), so the dashboard and the tab cannot drift apart again. Problems
in the data itself (Adjust dates that Sheets mis-read, overlapping Adjust imports) are now fixed
**in the sheet**, by a new "Clean Adjust Raw" command. That way both the report and the dashboard
are correct; the dashboard no longer patches them quietly in the browser.

**Tested.** I built a synthetic copy of the workbook that contains every one of these traps and
evaluated the real pacing formulas on it with a spreadsheet engine:

| | figures compared | differ from the pacing tab |
|---|---|---|
| Original code | 288 | **118** (KPI cards showed "—" for Revenue, ROAS, Installs and Bookings) |
| Fixed code | 350 | **0** |
| Fixed code, after Clean Adjust Raw / a CSV import / the GA4-revenue switch | 350 | **0** |
| **Your live workbook** (typed copy), after *Fix this workbook* | 350 | **0** — and 416/416 cells equal an independent recomputation (section 8) |

---

## 1. Why the dashboard disagreed with the pacing tabs

| # | What the dashboard did | Effect |
|---|---|---|
| 1 | Added rows from `Raw data BACKUP 20260807-1642` and from the native platform tabs (META, Snapchat, TikTok, Google, X) on top of Raw data. Raw data already holds all of that, because the Supermetrics queries start on 21 Jun. | Any campaign spelled differently in the backup (spacing, case, old naming) was **counted twice**. None of those rows are on the pacing tab. |
| 2 | De-duplicated Raw data by platform + portal + campaign + day. | Two genuine rows with the same campaign name on the same day (a re-created campaign, split manual rows) counted **once**. SUMIFS counts both. |
| 3 | Split campaigns into lines with its own token list (takeover, first_story…), while the tab used wildcard SUMIFS. | Different Awareness / Search / App splits on Snapchat, TikTok and Google. |
| 4 | Put every non-awareness X campaign on X App. The tab took only `*_x_app*`. | X App differed. |
| 5 | Took revenue on rows 7, 8, 15 and 16 from GA4 and dropped their Adjust revenue. The installed tab (`PACING_ALL`) reads Adjust revenue on **every** row, so 4 lines, the total and ROAS differed. The dashboard also left out the Adjust **Other** row (26), which the tab adds into X28 and L28. | Revenue and ROAS did not match. |
| 6 | Read `Adjust Current` whenever it existed (the tab never reads it). Re-assigned rows to a portal by campaign name instead of the app column. Moved Twitter installs from Other to X. Silently repaired dates and removed duplicates. | Adjust installs, bookings and revenue came from different numbers than the tab's. |
| 7 | Put any objective on the single Meta / Apple / Bidease / InMobi / InMotion lines. The tab only read `Conversion`. Google `Awareness` vs `YouTube`, Snapchat `Search` and similar labels also landed differently. | Adjust lines differed. |
| 8 | GA4: matched the property name exactly (the tab uses `"Six Flags*"`), matched the channel group case-sensitively, bucketed `snap` anywhere in the source (the tab uses starts-with), and dropped X web sales (the tab puts them in row 26). | GA4 purchases differed. |
| 9 | Used a 1 Jul floor for Meta in both portals. The tab uses 2 Jul for SFQC. | SFQC Meta differed when the window starts before 2 Jul. |
| 10 | Took InMobi from Raw manual + backup on every date. The tab uses Raw manual from 1 Sep and the backup for 2 Jul – 31 Aug. | InMobi differed. |
| 11 | **Blanked Revenue, ROAS, Installs and Bookings ("—")** whenever any spending line had no Adjust rows in the selected dates. That is normal for awareness lines and short ranges. The day table and line totals were blanked too. | The headline numbers "disappeared". |
| 12 | The Attribution and "How it adds up" GA4 tables ignored the date filter and listed one row per day × campaign instead of one per source. | Wrong web numbers on those screens. |
| 13 | One Adjust row with a blank channel stopped the whole dashboard ("missing channel or objective"). Exactly 5,000 Adjust rows did too. | "Could not read the sheets". |
| 14 | Smaller bugs: run-rate and pace divided by days not yet delivered; the trend tooltip crashed for Installs and Bookings; the ROAS tooltip showed "$". | Misleading per-day figures and errors. |
| 15 | The "Pacing dashboard" menu never appeared: `onOpen()` in Untitled.gs did not call `dashboardMenu_()`. | No Validate, Import or Export menu in the sheet. |

## 2. Counting and total bugs in the pacing tabs themselves

| # | Bug | Effect on the report |
|---|---|---|
| 1 | Lines added one SUMIFS per wildcard. `SFQC_Snapchat_AWRN_…` matches both `*snapchat_awr*` and `*_AWRN_*`; `…_CONV_SAL_TT_Search` matches both search wildcards. | Those campaigns were counted **twice** on the awareness/search row, and the App row (a remainder) was short by the same amount. |
| 2 | X App only took `*_x_app*`. | Any other X campaign (e.g. `_X_Web_`) was **in no row**. |
| 3 | Google App (row 21) = all Google from 2 Jul − YouTube (no floor) − Search. | Wrong whenever the window starts before 2 Jul. |
| 4 | **Row 28.** F28 (spend SAR) and J28 left out the awareness rows 7-10, while X28, K28, L28 and M28 included them. | **P28 ROAS = all revenue ÷ part of the spend**, so it was overstated. |
| 5 | K28 left out row 26 while L28 included it. | Bookings total and installs total covered different rows. |
| 6 | The AAQC tab's row 28 summed rows 14-24 and 6-10. | **InMotion (row 25) was missing** from AAQC F28 and J28. |
| 7 | N26 and O26 were copies of InMotion's N25 and O25. | Row 26 showed InMotion's purchases and installs. |
| 8 | AAQC Meta purchases (N19) used a 2 Jul floor; the rest of the row used 1 Jul. | Meta CVR was computed over two different date ranges. |
| 9 | Adjust columns only read exact (channel, objective) pairs. | Meta / Apple / Bidease / InMobi / InMotion rows with another objective, Google `Awareness`, Snapchat `Search` and similar were **in no row**. |
| 10 | C39 compared the lines against a total that ignores floors, APPLE1 and InMobi; C42 and C44 had no end date. | The check cells showed MISMATCH or CHECK even when nothing was wrong. |
| 11 | Data in Adjust Raw (the formulas cannot fix this). Dates stored as text, e.g. `13/09/2026`, are skipped by SUMIFS. Day/month swaps (01/09 stored as 9 January) count on the wrong day, usually outside the window. Overlapping imports are added twice. Twitter installs were filed under Other. | September installs and bookings missing; overlaps double-counted. |

## 3. What changed

**Code.gs** (server)
- The payload reads **exactly the cells the pacing formulas read**, with the same filters:
  - Raw data (including the new column M), APPLE1 (row 22), and InMobi from Raw manual / backup with the tab's date split (row 24).
  - Adjust Raw by position and by the **app** column.
  - GA4 by position and with the tab's wildcards.
- Removed the backup merge, the native-tab fill-in and the per-campaign de-duplication. Every source row counts once, as SUMIFS counts it.
- One definition of every line: `PACING_LINES` (rows, floors, GA4 bucket), `OBJECTIVE_TOKENS` (campaign → objective), `_adjustLine()` (Adjust → row, including the new row 26 Other) and `_ga4Bucket()`.
- **Data-health report.** Sent with the payload and shown as a banner: spend with no portal (UNMAPPED), text dates, swapped dates, duplicates, numbers stored as text, blank channels, an AAQC window that differs from SFQC, header layouts that no longer match the formulas, and the 5,000-row truncation. These are warnings now, not crashes.
- **`cleanAdjustRaw()`** (menu: *Pacing dashboard → Clean Adjust Raw*) repairs Adjust Raw in place:
  - real dates, numbers instead of text, de-duplicated overlaps (the later import wins, but an all-zero partial refresh never erases data), Twitter → X, blank channels filled;
  - folds in any old `Adjust Current` rows;
  - makes a values-only backup and writes a line-by-line log. Running it twice changes nothing.
- **`importAdjustCsv()`.** The CSV import now writes **into Adjust Raw**, so the report updates too. For each app it replaces exactly the days the file covers. Split rows inside one export (e.g. iOS + Android) are added together, not dropped. The labels it writes use the tab's vocabulary (YouTube, Awareness, Search).
- `validateDashboard()` now also compares the whole totals row (E–J, N, O, F, K, L, M, X, P of row 28), GA4 C49/D49 and the C41 check, and lists the data issues.
- `CFG.WEB_REVENUE_FROM_GA4` (default `true`, matching the live tab: GA4 revenue on the four web rows). Set it to `false` for Adjust revenue everywhere, then re-run *Fix this workbook*; the tab and the dashboard switch together.
- `_valueNum()` reads a leading "$", as Sheets' VALUE() does.

**Untitled.gs** (setup)
- `Raw data` gets column **M = Objective**, generated from `OBJECTIVE_TOKENS`. Each campaign gets exactly one objective, Awareness first. The portal rule also accepts the `AQQC` misspelling.
- `buildPacingSpec_()` generates the line formulas. Media rows are plain `SUMIFS(… M = objective …)` with each tab's own B2:C2 window. Adjust rows count every objective (remainders) and row 26 takes every non-organic channel without a row of its own. Row 28, N19, N26/O26 and C39/C42/C44 are fixed. Rows 22 and 24, the GA4 cells and the ratio columns stay as they were.
- New **Qiddiya Setup → Fix this workbook (one run)** (`fixThisWorkbook()`): hidden backups, the Objective column on a pasted Raw data, Raw manual text numbers, *Clean Adjust Raw*, one date window, and the formulas below. Safe to re-run.
- Row 28 totals every media column (E–J, N, O) with its ratios (Q–W), not only F and J.
- `onOpen()` now also adds the Pacing dashboard menu.
- New *Revert pacing formulas to the previous version*. *Undo everything* restores the previous formulas too, and no longer confuses an Adjust backup with a Raw data backup.
- The Validation tab and the install checks were updated for the new structure (coverage = spend with no portal; text dates in Adjust).

**Dashboard.html** (browser)
- No classification of its own. Every row arrives already tagged with its pacing row, so every view, filter and total uses the same lines. The "Every line" table is in pacing-row order, and its Total = row 28.
- Revenue, ROAS, Installs and Bookings are always shown. A channel with no Adjust data at all gets a "no feed" tag instead of blanking the cards.
- GA4 tables are per source and follow the dates. A new "GA4 purchase" column (M) is added, and row 26 (Other) is shown.
- Run-rate and pace use delivered days. The tooltip, format and wrap bugs above are fixed. The data-issue banner is new.

`appsscript.json` is unchanged.

## 4. How to install

1. In the Apps Script editor, replace **Code.gs**, **Dashboard.html** and **Untitled.gs** with the
   files in this folder. Save.
2. Reload the spreadsheet. Both the **Qiddiya Setup** and the **Pacing dashboard** menus appear.
3. **Qiddiya Setup → Fix this workbook (one run).** It applies every repair from the audit in
   section 8, in place, and makes hidden backups first. Raw data stays the pasted table it is today.
   (Step "3 · Install the formulas" is only for switching Raw data to the Supermetrics formula.)
4. **Pacing dashboard → Validate against the pacing tabs.** You should see "All … figures match"
   and no data issues.
5. For the web link: **Deploy → Manage deployments → edit → New version** (the URL stays the same).
6. From now on, load Adjust exports with **Pacing dashboard → Import latest Adjust CSVs**. If you
   paste Adjust rows by hand, run **Pacing dashboard → Clean Adjust Raw** afterwards.
7. When you paste new Raw data, paste columns **A:L only**. Column M (Objective) is a formula that
   fills itself.

## 5. Choices you may want to change

- **Revenue (column X)** on the four web rows (Snapchat and TikTok awareness, TikTok Search, Google
  Search) comes from GA4, as on the live tab today; every other row uses Adjust. For Adjust everywhere, set
  `CFG.WEB_REVENUE_FROM_GA4 = false` and re-run *Fix this workbook*.
- **Snapchat "takeover" / "_AWRN_"** campaigns count as Awareness. Edit `OBJECTIVE_TOKENS` and
  re-run *Fix this workbook* to change it.
- **Totals include the awareness rows and row 26**, in every column. Row 28 now also totals
  spend USD, impressions, views, clicks and platform purchases/installs, with their ratios.
- **One date window.** AAQC B2:C2 follow SFQC B2:C2, and SFQC C2 is `=TODAY()-1`. Type a date into
  SFQC C2 to report a fixed period.
- **The dashboard's "All" is every day with data** (from SFQC B2 to the latest source day, at most
  yesterday), whatever C2 says, and the dashboard opens on it. While C2 is earlier than the data, a
  **Tab period** button appears that shows exactly the dates the pacing tabs count, and a banner says
  so. *Validate against the pacing tabs* always compares the tab period.
- **How it adds up → Check it against the tabs** reconciles every source tab, for the portal and
  dates on screen: what a plain SUM() of the tab shows, numbers stored as text that SUM() cannot
  see, rows left out and why (InMobi rows in Raw data and Bidease rows in Raw manual are copies of
  each other's tab; X spend is SAR), and what is counted. The counted lines add up to the cards.
  Example, SFQC, all dates: your three SUMs (Raw data 354,253,073 + Raw manual 23,701,280 + APPLE1
  621,306 = 378,575,659) → + 145,090,770 text-stored InMobi (115,027,745 in Raw manual, 30,063,025 in
  Raw data) − 36,827,172 Raw data InMobi copies − 23,701,280 Raw manual Bidease copies + 41,150,927
  InMobi in the backup tab = **504,288,904**.
- **Adjust is read through the cleaner's corrections.** Text dates, day/month swaps, overlapping
  imports, text numbers and mislabelled channels are corrected in memory as the dashboard reads
  Adjust Raw (the same code *Clean Adjust Raw* writes back), so its installs, bookings and revenue
  are right before the tab is cleaned. On the live file this moved SFQC September from 459 to 8,572
  installs. Until *Clean Adjust Raw* runs, a banner says how far the pacing tabs are off.
  *Validate* still compares the formulas with the dashboard reading the tab as it stands.
  **Check it against the tabs — Adjust** walks Adjust Raw from its SUM() to the cards (SFQC:
  38,159 − 147 duplicate imports − 18 before 2 Jul = 37,994 installs).
- To go back: unhide the "… BACKUP yyyyMMdd-HHmm" tabs that *Fix this workbook* made.

## 6. What will move in the report

See section 8 for the live workbook's numbers before and after.

## 7. Re-running the check

```
cd tests && npm install && npm test        # or: node harness.js --old <folder with the original files>
```

The harness builds `tests/fixture.js` (a synthetic workbook containing each trap above).
It evaluates the pacing formulas with HyperFormula and runs Code.gs against a mock of the Apps
Script API. It then loads Dashboard.html in a headless DOM and compares every line and every
row-28 total, for SFQC and AAQC: before cleaning, after cleaning, after a CSV import, and with
the GA4-revenue switch on.

One note outside this fix: `appsscript.json` deploys the web app as *Anyone, even anonymous*, and
it runs as you. Anyone with the link can see the numbers. Change `access` if that is not intended.

## 8. Live workbook audit (5 Oct 2026)

The live file was audited cell by cell against its sources. Claude's Google connector could read it
but not edit it, so the repairs are packaged as *Qiddiya Setup → Fix this workbook*. That function
was run on an exact typed copy of the live workbook. Afterwards the dashboard matched both tabs on
all 350 figures. An independent recomputation from the raw rows, without the sheet formulas or this
code, matched all 416 pacing cells it checked.

**What was wrong in the live file**

| # | Where | Problem | Effect |
|---|---|---|---|
| L1 | SFQC row 22 (Apple) | K22/L22 read **Aquarabia** Adjust rows; H22/N22 read AAQC Raw data | Six Flags Apple installs/bookings were Aquarabia's (1,815 / 343 on both tabs) |
| L2 | Media rows, both tabs | Wildcard-only SUMIFS, no date window | SFQC "till 1 Sep" was ignored; 182 Snapchat `_AWRN_` takeover rows ($103,009) matched no row |
| L3 | Check block | C39 vs C40 | SFQC **MISMATCH $79,860**, AAQC **MISMATCH −$8,212**; G42 CHECK on both |
| L4 | Row 24 (InMobi) | Read partial Raw data rows; Raw manual impressions stored as text ("15,62,702") | SFQC InMobi 6.8M impressions instead of 156M; AAQC InMobi spend $0 |
| L5 | Adjust Raw | 1,839 text dates, 926 day/month swaps, 1,039 duplicate rows (overlapping imports 15–29 Sep), 6 Twitter rows under Other | September under/over-counted, rows outside any window |
| L6 | Windows | SFQC 22 Jun–1 Sep (static), AAQC 21 Jun–yesterday | The two tabs and the dashboard reported different periods |
| L7 | Row 28 | Only F, J, K, L, M, P, X totalled; AAQC F28/J28 summed rows 14–24 | No impressions total to compare with; AAQC spend total skipped InMotion |

**Not fixable from the sheet:** no source holds InMobi data for **3–31 Aug** (the Raw data backup ends
2 Aug, Raw manual starts 1 Sep). Paste those days into Raw manual and row 24 picks them up.

**Totals before → after** (window 22 Jun – 4 Oct)

| | SFQC before | SFQC after | AAQC before | AAQC after |
|---|---:|---:|---:|---:|
| Spend USD (rows 7–25) | 401,928 | 522,776 | 326,457 | 348,840 |
| Impressions | 328,667,886 | 504,288,904 | 244,705,267 | 373,040,287 |
| Clicks | 3,411,665 | 3,823,930 | 2,406,843 | 2,644,091 |
| Adjust installs (L28) | 31,427 | 37,994 | 38,172 | 41,424 |
| Adjust bookings (K28) | 3,719 | 4,587 | 4,060 | 4,594 |
| GA4 purchases (M28) | 579 | 740 | 1,670 | 1,670 |
| Revenue SAR (X28) | 2,294,223 | 3,395,303 | 4,339,894 | 4,840,304 |
| ROAS (P28) | 1.98 | 1.72 | 4.25 | 3.67 |
| Spend not on a line (C41) | 79,860 | 0 | −8,213 | 0 |

