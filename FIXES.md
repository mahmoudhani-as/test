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
| Fixed code | 338 | **0** |
| Fixed code, after Clean Adjust Raw / a CSV import / the GA4-revenue switch | 338 | **0** |

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
- `validateDashboard()` now also compares the totals row (F28, J28, K28, L28, M28, X28, P28), GA4 C49/D49 and the C41 check, and lists the data issues.
- `CFG.WEB_REVENUE_FROM_GA4` (default `false`, matching the installed tab). Set it to `true` to read revenue on the four web rows from GA4, then re-run step 3; the tab and the dashboard switch together.

**Untitled.gs** (setup)
- `Raw data` gets column **M = Objective**, generated from `OBJECTIVE_TOKENS`. Each campaign gets exactly one objective, Awareness first. The portal rule also accepts the `AQQC` misspelling.
- `buildPacingSpec_()` generates the line formulas. Media rows are plain `SUMIFS(… M = objective …)` with each tab's own B2:C2 window. Adjust rows count every objective (remainders) and row 26 takes every non-organic channel without a row of its own. Row 28, N19, N26/O26 and C39/C42/C44 are fixed. Rows 22 and 24, the GA4 cells and the ratio columns stay as they were.
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
3. **Qiddiya Setup → 3 · Install the formulas.** This rebuilds Raw data with column M and writes
   the corrected pacing formulas. It does not touch the Supermetrics queries.
4. **Pacing dashboard → Clean Adjust Raw.** Run it once now, and again whenever Adjust data is
   pasted by hand. It makes a backup tab and an "Adjust Raw cleanup log" listing every change.
5. **Pacing dashboard → Validate against the pacing tabs.** You should see "All … figures match".
   Anything listed under DATA QUALITY needs fixing in the sheet; it affects the report too.
6. For the web link: **Deploy → Manage deployments → edit → New version** (the URL stays the same).
7. From now on, load Adjust exports with **Pacing dashboard → Import latest Adjust CSVs**. Once its
   rows are merged by step 4, the old `Adjust Current` tab is renamed "(merged …)" and can be deleted.

## 5. Choices you may want to change

- **Revenue (column X)** is Adjust on every row, because that is what the installed formulas do.
  The report's original design used GA4 on the four web rows. To switch, set
  `CFG.WEB_REVENUE_FROM_GA4 = true` and re-run step 3.
- **Snapchat "takeover" / "take over"** campaigns now count as Awareness. Before, the tab filed them
  under Snapchat App unless the name also had another awareness token. Edit `OBJECTIVE_TOKENS` and
  re-run step 3 to change it.
- **Totals include the awareness rows and row 26**, in every column.
- To go back to the old formulas: *Qiddiya Setup → Revert pacing formulas to the previous version*.

## 6. What will move in the report after step 3

- Snapchat and TikTok **awareness/search rows may go down** (no more double counting) and their
  **App rows go up by the same amount**. Platform totals do not change.
- **X App goes up** by any X campaign that matched neither old wildcard.
- **F28 goes up** (awareness spend is now included), so **P28 ROAS goes down** to its true value.
  AAQC F28 now includes InMotion.
- After *Clean Adjust Raw*: Adjust rows with text or swapped dates are counted (usually September),
  and overlapping imports stop being added twice.
- Raw data spend with no portal is still not counted anywhere. The dashboard banner names the
  campaigns; fix their names, or add the token to the portal rule in `RAW_FORMULA`.

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
