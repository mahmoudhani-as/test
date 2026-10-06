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
5. **Raw data column B files every campaign whose name does not start with "SFQC" under Aquarabia**,
   including Six Flags' $50,000 "First Story" takeover on 4 Oct. V4 now takes the portal from the
   campaign name, in Raw data column Q (section 3).
6. **Adjust Clean holds exactly what is counted.** Its installs and bookings columns add up
   to the dashboard's *All* view (Both portals) and row 28 (77,020 installs on the 5 Oct copy, against
   84,639 in Adjust Raw). Today's partial day is left out until the day is over, as the dashboard and
   C2 = TODAY()-1 leave it out. It is rebuilt **every time the dashboard loads or refreshes** if Adjust
   Raw has changed or a new day has started (section 3).
7. **A few fixes belong in the source workbook**, which V4 imports from: TikTok purchases are counted
   twice there, and Raw manual rows above row 50 never reach Raw data (section 6).

Every counting rule now lives in `Code.gs`, and the pacing formulas are generated from the same rules,
so the dashboard and the tabs cannot drift apart. In V4 the script never writes into a tab that is
imported from another workbook (section 3).

**Tested**

| | figures compared | differ from the pacing tab |
|---|---:|---:|
| Original code, synthetic workbook | 288 | **124** (the KPI cards showed "—" for Revenue, ROAS, Installs and Bookings) |
| Fixed code, synthetic workbook: as built, after *Clean Adjust Raw*, after a CSV import, with the GA4-revenue switch off | 350 each | **0** |
| *Fix this workbook* on the synthetic workbook (a pasted copy and an IMPORTRANGE copy), then *Undo* | every check passes | 0 writes into imported columns |
| The web link: an anonymous visitor calls all 62 public functions, before and after *Fix* | every check passes | nothing in the workbook changes |
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
| L2 | Media rows, both tabs | Wildcard-only SUMIFS with no date window | SFQC's "till 1 Sep" was ignored for media. `_AWRN_` takeover rows matched no row: SFQC 182 rows ($103,009); AAQC 102 rows ($3,678), plus 9 empty "First Story 4/10 ARB" rows (23 Sep–1 Oct, all zeros) |
| L3 | Check block | C39 vs C40 | SFQC **MISMATCH $79,860**, AAQC **MISMATCH −$8,212**; G42 showed CHECK on both |
| L4 | Row 24 (InMobi) | Read partial Raw data rows. Raw manual impressions were stored as text ("15,62,702") | SFQC InMobi showed 6.8M impressions instead of 156M; AAQC InMobi spend was $0 |
| L5 | Adjust Raw | 1,839 text dates, 926 day/month swaps, 419 rows repeated by overlapping imports, and a 1,051-row export pasted again under Aquarabia (section 4). Also 362 rows filed under "Other": Untrusted Devices 228, WhatsApp Organic Share 72, Pangle 56, Twitter 6 | September installs were missing and AAQC counted Six Flags results. Row 26 counted fraud-filtered and organic installs as paid |
| L6 | Windows | SFQC ran 22 Jun–1 Sep (typed), AAQC 21 Jun–yesterday | The two tabs and the dashboard reported different periods |
| L7 | Row 28 | F28 and J28 left out the awareness rows 7–10 while X28 included them. The AAQC F28/J28 summed rows 14–24. Only F, J, K, L, M, P and X were totalled | **P28 ROAS divided all revenue by part of the spend**, so it was overstated. AAQC spend skipped InMotion |
| L8 | Raw data column B (set by the source workbook's Raw data!A2) | `IF(LEFT(UPPER(name),4)="SFQC","SFQC","AAQC")`: every name that does not start with "SFQC" is AAQC | X "DNU SFQC-…Six Flags_X_App Installs" ($387) was counted under AAQC. The Snapchat "First Story 4/10 ARB" takeover ($50,000 on 4 Oct, past the source's 1 Oct window) would land on AAQC row 7 (+14% AAQC spend), and no check cell would catch it. Now decided from the name (section 3) |
| L9 | Raw data column L, TikTok (source workbook) | Purchase events + **Purchase events (SKAN)** + Complete payment events. SKAN measures the same iOS purchases a second time (installs already leave SKAN out) | TikTok N18 overstated: SFQC 1,707 instead of 1,276, AAQC 2,929 instead of 2,240 (N28 about 4% high, V18/V28 too). Fixed in the source (section 6) |

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
| 9 | Media rows and C39 filtered on Raw data column B (L8). | They filter on Raw data column Q, the portal the campaign name carries. |

## 3. How V4 is built: nothing is written into imported tabs

In V4, four source tabs are `IMPORTRANGE` mirrors of the source workbook (A1 holds the import): Raw data
(A:O), Raw manual (A:O), Adjust Raw (A:K) and APPLE1 (Apple!A:O). GA4 is filled by Supermetrics.
Writing one cell inside an import's range breaks it: A1 shows `#REF!` and the whole tab empties. So
the script works around the mirrors:

| Need | How it is done |
|---|---|
| Each media row's objective | Raw data **column P** (`CFG.OBJECTIVE_COL`), outside the imported A:O. P1 = "Objective", plus one ARRAYFORMULA in P2 generated from `OBJECTIVE_TOKENS`. Leave column P empty below P2. |
| Each media row's portal | Raw data **column Q** (`CFG.PORTAL_COL`), also outside A:O. Q1 = "Portal", plus one ARRAYFORMULA in Q2 generated from `PORTAL_TOKENS`: a name containing SFQC or Six Flags (on Snapchat also First Story) is SFQC; AAQC, AQQC, AQC- / AQC_ or Aquarabia is AAQC; any other name keeps column B, and UNMAPPED when B is neither. **Why:** the source sets column B with "starts with SFQC, else AAQC" (L8). The media rows and C39 filter on Q, and the dashboard applies the same rule. On the live copy this moves only "DNU SFQC-…" (X, $387) from AAQC to SFQC row 20; once the source window passes 4 Oct, the $50,000 "First Story 4/10 ARB" takeover lands on SFQC row 7. |
| Corrected Adjust data | The pacing formulas (K, L, X and C42–C44) read **Adjust Clean**, a tab the script owns and rebuilds from Adjust Raw. **Adjust Raw is never modified.** |
| Keeping Adjust Clean current | **Every dashboard load or refresh** builds Adjust Clean if it is missing and rebuilds it whenever Adjust Raw (or the old `Adjust Current` tab) has changed since the last build, or a new day has started, whether or not the pacing tabs read it yet. Nothing has to be run by hand. It is also rebuilt by an **hourly trigger** (`refreshAdjustClean`, which keeps an existing tab current), by *Pacing dashboard → Clean Adjust Raw*, by *Fix this workbook* and by *Validate*. If a rebuild cannot run, the banner says (critical) that K, L and X still show the previous build. |
| Raw manual numbers stored as text | A mirror is left as it is. Row 24 and the dashboard read the text numbers with VALUE(SUBSTITUTE()). A pasted Raw manual is converted, with a backup. |
| Adjust CSV import | Refuses a mirrored Adjust Raw: paste the export into the source workbook instead. In a file where Adjust Raw is a pasted table, the import writes into it. |
| Step 3 (Supermetrics formula) | Refuses a mirrored Raw data. |
| A broken or loading import | `#REF!` or `Loading…` in A1, a missing tab, a moved header, or a Raw data with no rows while Adjust and GA4 have some each raise a critical banner. *Validate* then starts with "CHECK — n critical data issue(s)" before the match count. |

**What Adjust Clean holds: only the rows the dashboard counts under *All*.** So a SUM of its installs
or bookings column equals the dashboard's *All* view with Both portals, and row 28 of the two tabs
together when C2 is yesterday. Its revenue column does too, except on the web lines (rows 7, 8, 15 and
16), where the tabs and the dashboard use GA4 web revenue instead of Adjust's. Compare with a freshly
loaded page: an open page does not reload by itself, so press **Refresh** after Adjust Raw changes. Its days run from SFQC B2 to C2 or yesterday, whichever is later.
**Today is left out until it is over**: an Adjust feed that already has part of today would otherwise
put those installs in Adjust Clean but not on the dashboard or the tabs. When the day rolls over, the
next dashboard load or hourly run adds it. On the 5 Oct copy:

| Adjust installs | |
|---|---:|
| Adjust Raw, whole column | 84,639 |
| − cross-app copy (section 4) | −3,924 |
| − rows repeated by overlapping imports | −2,315 |
| − Untrusted Devices (not paid: Organic) | −917 |
| − WhatsApp Organic Share (not paid: Organic) | −161 |
| − rows before their pacing line starts (2 Jul floor) | −302 |
| **Adjust Clean = dashboard = L28 (SFQC 37,526 + AAQC 39,494)** | **77,020** |

The rows left out are listed, with their totals, at the top of the "Adjust Raw cleanup log" tab: rows
for an app other than Six Flags / Aquarabia, rows with no readable day, rows that are not paid
(Organic), rows outside the report's days (today, or before B2), and rows dated before their line's
first day. A revenue, installs or bookings cell that is not a number (for example "$12") counts as 0
on the dashboard, in Adjust Clean and on the tabs alike, and the banner names its row.

What Adjust Clean corrects:

- text dates and day/month swaps, including short dd/MM pastes that continue the rows above them (a
  genuine early row, such as a backfill of 1–12 Jun, is never re-dated);
- overlapping imports (the later import wins, but an all-zero row never replaces a non-zero one);
- cross-app copies (section 4);
- numbers stored as text;
- channel labels: Twitter → X, Pangle → TikTok, Untrusted Devices and "Organic Share" → Organic, and blank channels from the network;
- rows left in the old `Adjust Current` tab, which are folded in.

Every rebuild rewrites the "Adjust Raw cleanup log" tab with each correction. A rebuild writes over the
old rows and then trims what is left, so a failed write keeps the previous copy and is retried by the
next dashboard load or hourly run; a short Adjust Clean raises a critical banner. The dashboard reads
Adjust Raw through the same code in memory, so its Adjust figures are right even before *Fix this
workbook* has run (until then the pacing tabs still read Adjust Raw, and the banner says so). *Validate* reads what the formulas read (Adjust Clean after *Fix*).

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
| ROAS (P28) | 3.65 | **3.54** |
| Installs 15–28 Sep | 4,995 | 3,609 (−28%) |
| Bidease installs (L23) | 772 | 443 |

Optionally, delete that block in the source workbook's Adjust Raw. The script already leaves it out, so
no number moves.

## 5. Web link security

`appsscript.json` deploys the web app as *Anyone, even anonymous*, running as you. Before this version,
anyone with the /exec link could call the script's server functions as you through `google.script.run`.
These included the old *Undo everything* (it replaced Raw data with the 7 Aug backup), the Adjust importer,
*Fix this workbook*, the formula reverts and *Check the setup*.

Now every menu function, and every function that imports, exports or writes your source or pacing tabs,
starts with `requireSheetUser_()`. Run from the spreadsheet's menus it always goes through (the sheet's
menus cannot be reached from the web link). Run from the editor or a trigger, it goes through only when
the person running it is the account the script runs as. A visitor using the web link gets "This can
only be run from the spreadsheet…". Two paths stay open, and neither can change a number: a dashboard
load, and `refreshAdjustClean` (the hourly trigger's handler). A dashboard load builds or rebuilds
Adjust Clean from Adjust Raw when Adjust Raw has changed; the hourly handler only refreshes an existing
Adjust Clean. Both give the same result every time, and `refreshAdjustClean` returns nothing. The test suite has an anonymous visitor call all 62 public
functions before and after *Fix*: nothing in the workbook, its properties or its triggers changes, and
no Adjust data or account name comes back (a dashboard load may only build or refresh Adjust Clean and
its log). The dashboard itself still loads from the link, and
**anyone with the link can still see the numbers**. Change `access` if that is not intended.

Two scopes were added: `userinfo.email` (the guard compares emails) and `script.scriptapp` (the hourly
trigger). **Everyone who uses the menus must authorise once more.** The menus work with the old manifest
too, but the hourly trigger, and anything run from the editor, need the new one; without it, those say
"Run this from the spreadsheet's menus… replace appsscript.json" (section 6, step 2). You must also **deploy a new version of the web app** (section 6,
step 6). Until then the link runs the old, unguarded code.

## 6. Install

**Updating from the previous version of this fix** (the one that added column P): replace Code.gs,
Untitled.gs and Dashboard.html (appsscript.json is unchanged), run **Fix this workbook** again, and
redeploy the web app (step 6). *Fix* adds Raw data column Q and points the formulas at it. Until it
has run, a critical banner names the X campaign ($387) the tabs still file under AAQC. Adjust Clean is
rebuilt once, on the first dashboard load or hourly run, because its fingerprint format changed.

1. Open V4 → **Extensions → Apps Script**. Replace **Code.gs**, **Untitled.gs** and **Dashboard.html**
   with the files in this folder.
2. **Project Settings** (gear icon) → tick **Show "appsscript.json" manifest file in editor**. Back in the
   editor, open `appsscript.json`, replace its contents with this folder's file, and save. If something
   run from the editor later says "replace appsscript.json", this step was skipped. (The menus work
   either way.)
3. Reload the spreadsheet. The **Qiddiya Setup** and **Pacing dashboard** menus appear.
4. **Qiddiya Setup → Fix this workbook (one run).** Google asks you to authorise the new permissions.
   Allow them, then run it again if it stopped there. It does the following:
   - hidden backups of both pacing tabs (first run only);
   - the Objective and Portal columns in Raw data P and Q;
   - Adjust Clean, plus the hourly refresh;
   - one date window: AAQC B2:C2 follow SFQC, and SFQC C2 becomes `=TODAY()-1` (first run only);
   - the generated formulas, totals, checks and labels on both tabs.

   It writes nothing into Raw data A:O, Raw manual, Adjust Raw or APPLE1. It is safe to re-run.
5. **Pacing dashboard → Validate against the pacing tabs.** Expect "All 350 figures match the pacing
   tabs", followed by a few notes. The 5 Oct copy gave the 5 notes listed in section 7. If Adjust Raw
   has changed since the last build, *Validate* rebuilds Adjust Clean first. If it says Adjust Clean is
   behind, run *Validate* again in a minute rather than *Fix*.
6. Redeploy the web app: **Deploy → Manage deployments → edit (pencil) → Version: New version → Deploy**.
   The URL stays the same.
7. In the **source workbook**, set Raw data **O2** to `=TODAY()-1`, then make the edits listed below.
   Raw data's N2:O2 there decide which days reach V4. Today they point at that file's own SFQC B2:C2,
   typed as 22 Jun – 1 Oct. Without this change, V4's media stops on 1 Oct while Adjust, GA4 and APPLE1
   keep growing, so ROAS and CPI are overstated from 2 Oct on. Run step 4 with this version first: the
   $50,000 "First Story 4/10 ARB" row (4 Oct) arrives with column B = AAQC, and only column Q puts it on
   SFQC.

**From then on**

- **Adjust:** paste new Adjust exports into the source workbook's Adjust Raw, as today. Adjust Clean
  follows the next time the dashboard is opened or refreshed, or within the hour, or straight away with
  *Pacing dashboard → Clean Adjust Raw*. Nothing has to be run from the dashboard link.
- **Raw data columns P and Q:** leave the formulas in P2 and Q2 alone, and the cells below them empty.
  If Raw data is ever a pasted table, paste A:O only.
- **Rule changes:** after editing `OBJECTIVE_TOKENS`, `PORTAL_TOKENS` or any other rule in Code.gs,
  re-run *Fix this workbook*.
- **Step 3 (Install the formulas):** do not use it for rule changes. It only switches a pasted Raw data
  to the Supermetrics formula, keeps a values backup of the pasted table first, and refuses an imported
  Raw data.

### Changes to make in the SOURCE workbook

V4 imports Raw data A:O from the source workbook's `Raw data!A2` formula, so these edits are made there.

- **(a) TikTok purchases (L9).** In the TikTok HSTACK of `Raw data!A2`, the last column (L) is
  `IF(CHOOSECOLS(tk,iT_pe)="",0,CHOOSECOLS(tk,iT_pe))+IF(CHOOSECOLS(tk,iT_ps)="",0,CHOOSECOLS(tk,iT_ps))+IF(CHOOSECOLS(tk,iT_cp)="",0,CHOOSECOLS(tk,iT_cp))`.
  Replace it with:

  ```
  IF(CHOOSECOLS(tk,iT_pe)="",0,CHOOSECOLS(tk,iT_pe))+IF(CHOOSECOLS(tk,iT_cp)="",0,CHOOSECOLS(tk,iT_cp))
  ```

  The `iT_ps, XMATCH("Purchase events (SKAN)",hT),` line can then be deleted. Effect, to 1 Oct: SFQC
  N18 1,707 → 1,276 and AAQC N18 2,929 → 2,240; N28 10,059 → 9,628 and 16,800 → 16,111; V18 and V28
  fall with them. Spend, installs, bookings and revenue do not move. Keep Complete payment events: SFQC
  records app purchases in Purchase events, AAQC mostly in Complete payment events. This project's
  `RAW_FORMULA` (step 3) already has the change.
- **(b) Raw manual from row 50.** `Raw data!A2` reads `FILTER('Raw manual'!$A$50:$L,'Raw manual'!$A$50:$A<>"")`,
  so a Bidease or InMotion row above row 50 never reaches Raw data, rows 23/25 or the dashboard. The
  start moves down every time rows are inserted above it (it has already moved from row 2 to row 50).
  Either change both `$A$50` to `$A$2`, or always add Bidease/InMotion rows at row 50 or below (inside
  or under the existing Bidease rows, from row 60). With `$A$2`, the source's Raw data also gets the
  InMobi rows above row 50. V4 ignores Raw data's InMobi rows, so no V4 number moves, but check that the
  source's own report does not then count them twice. V4 now raises a critical banner, listing the rows,
  for any Raw manual Bidease/InMotion row that did not reach Raw data.
- **(c) Portal rule (optional).** Each HSTACK sets column B with
  `IF(LEFT(UPPER(CHOOSECOLS(x,2)),4)="SFQC","SFQC","AAQC")` (Apple: `CHOOSECOLS(ap,iA_acct)`). Replace
  each one with
  `IF(REGEXMATCH(UPPER(CHOOSECOLS(x,2)),"SFQC|SIX[ _-]?FLAGS"),"SFQC",IF(REGEXMATCH(UPPER(CHOOSECOLS(x,2)),"AAQC|AQQC|AQC[-_]|AQUARABIA"),"AAQC","UNMAPPED"))`,
  with `CHOOSECOLS(ap,iA_acct)` for `CHOOSECOLS(x,2)` on Apple, and `|FIRST STORY` added to the first
  pattern in the Snapchat HSTACK. V4 already decides from the name
  (column Q), so no V4 number moves; this makes the source's own report agree, and a name with no
  portal then shows as UNMAPPED (today only zero-spend TikTok "TOPVIEW-…" and X "Campaign — Jul 24 —
  7:23 PM" rows).
- **(d) Missing spend (section 8).** Paste InMobi 3–31 Aug (both portals) and Bidease SFQC 4–14 Sep into
  the source's **Raw manual**: InMobi anywhere (V4's row 24 reads the imported Raw manual directly),
  Bidease at row 50 or below unless (b) is done. Never type into V4's own imported tabs.

## 7. What to expect

**Totals before → after** on the typed copy of the live file:

- **Before:** the live tabs as they stood on 5 Oct. SFQC media and Adjust rows had no end date, but SFQC's
  GA4 cells, X7/X8/X15/X16 and row 26 stopped at its C2 (1 Sep). AAQC ran 21 Jun – 4 Oct.
- **After:** both tabs run 22 Jun – 4 Oct. The data ends 30 Sep – 1 Oct.

| | SFQC before | SFQC after | AAQC before | AAQC after |
|---|---:|---:|---:|---:|
| Spend USD (rows 7–25) | 401,928 | 523,163 | 326,457 | 348,453 |
| Impressions | 328,667,886 | 506,098,155 | 244,705,267 | 371,231,036 |
| Clicks | 3,411,665 | 3,826,995 | 2,406,843 | 2,641,026 |
| Adjust installs (L28) | 31,427 | 37,526 | 38,172 | 39,494 |
| Adjust bookings (K28) | 3,719 | 4,535 | 4,060 | 4,354 |
| GA4 purchases (M28) | 579 | 703 | 1,670 | 1,664 |
| Revenue SAR (X28) | 2,294,223 | 3,353,817 | 4,339,894 | 4,658,143 |
| Spend SAR (F28) | 1,157,372 | 1,977,557 | 1,020,596 | 1,317,152 |
| ROAS (P28) | 1.98 | 1.70 | 4.25 | 3.54 |
| Spend not on a line (C41) | 79,860 | 0 | −8,212 | 0 |

- **SFQC GA4 579 → 703.** The longer window alone gives 740, and 221,655 SAR of the revenue rise is that
  window's GA4 web revenue. The 2 Jul floor on Google Search and Meta GA4 then takes 37 purchases back.
- **ROAS falls mainly because F28 now includes the awareness spend** (L7).
- **Where the other moves come from:**
  - SFQC Snapchat awareness $18,822 → $121,832: the `_AWRN_` rows (L2).
  - SFQC InMobi $5,183 → $23,021 and 6.8M → 156.2M impressions; AAQC InMobi $0 → $18,706 (L4).
  - X App: "DNU SFQC-…" ($387, 1,809,251 impressions, 3,065 clicks, 41 platform installs) is on SFQC row 20 by
    its name, not on AAQC as column B says (L8).
  - Adjust: the September dates are now read (L5), the cross-app copies are out (section 4), and row 26
    is now 0, because Untrusted Devices and WhatsApp Organic Share are Organic and Pangle is TikTok App.
- **Row 28 now also totals** spend USD, impressions, views, clicks and platform purchases/installs, with
  their ratios. N28 is 10,059 (SFQC) and 16,800 (AAQC) without Google's app-install conversions, and
  9,628 / 16,111 once the TikTok SKAN term is removed in the source (section 6, (a)).
- **Link clicks (J)** is each export's own measure: Meta link clicks, TikTok clicks (destination), X
  clicks and Apple taps, with Bidease, InMobi and InMotion as entered in their column H. Snapchat and
  Google report none (their lines show "—" on the dashboard). J28 adds these different measures, so it
  is not comparable across platforms.

**The dashboard after the fix** ("All", 22 Jun – 4 Oct). The cards equal row 28:

| | SFQC | AAQC |
|---|---:|---:|
| Spend | $523,163 | $348,453 |
| Revenue | 3,353,817 SAR | 4,658,143 SAR |
| ROAS | 1.70× | 3.54× |
| Installs (Adjust) · CPI without awareness (blended) | 37,526 · $9.00 ($13.94) | 39,494 · $7.39 ($8.82) |
| Bookings (Adjust) · CPA without awareness (blended) | 4,535 · $75.67 ($115.36) | 4,354 · $67.84 ($80.03) |
| Daily run-rate | $5,232 | $3,485 |

"All" runs to C2 (4 Oct), so the ROAS, CPI and CPA cards add "partial: Adjust to 30/09, GA4 web to
28/09". 7d and 14d end on 30 Sep, the last day both media and Adjust reached. For example, SFQC 7d
shows ROAS 4.34×, CPI $16.33 and CPA $79.90.

**Notes left in the banner and on *Validate*** (none critical):

- **InMobi 3–31 Aug:** SFQC has 5,244 installs, 556 bookings and 416,069 SAR, and AAQC 2,821, 405 and
  306,820 SAR, on days with no spend row. In V4 the note says to paste the spend into Raw manual in the
  source workbook (section 8).
- **Bidease SFQC 4–14 Sep:** 333 installs, 26 bookings and 13,948 SAR with no spend row. In V4 the note
  says: into the source's Raw manual, at row 50 or below.
- **X campaign filed by its name:** "DNU SFQC-…Six Flags_X_App Installs" has column B = AAQC in the
  source, and column Q files it under SFQC ($387). The tabs and the dashboard agree.
- **Adjust Raw's own problems:** listed, with a note that they are corrected in Adjust Clean.
- **On the page only:** an "Adjust feed dropped?" note for SFQC Google and AAQC Google. SFQC Google had
  7 Adjust installs on $11,487 in the last 14 days, against 24 per $1,000 before, while Google claims 3,901.

## 8. Gaps the script cannot fill

- **InMobi 3–31 Aug.** No tab holds InMobi spend for those days: the backup tab ends on 2 Aug, and Raw
  manual starts on 1 Sep. Adjust does have installs on those days (section 7), so row 24's CPI, CPA and
  ROAS are overstated until the spend is in.
  - **Where to paste:** Raw manual **in the source workbook** (V4's Raw manual is imported from it, and
    typing into it breaks the import). Any row works: row 24 reads V4's whole Raw manual.
  - **Columns:** A = `InMobi`, B = `SFQC` or `AAQC`, C = campaign name, D = the day as a real date,
    F = impressions, G = spend USD, and H–L if you have them.
  - **What reads it:** row 24 and the dashboard read Raw manual from 3 Aug (`CFG.INMOBI_MANUAL_FROM`)
    and the backup tab up to 2 Aug (`CFG.INMOBI_BACKUP_TILL`). The banner note goes away once the days
    are in.
- **Bidease SFQC 4–14 Sep.** Bidease is read from Raw data, which the source workbook builds from its
  Raw manual, **from row 50 down** only (section 6, (b)). Add the rows to the source's Raw manual at row
  50 or below (inside or under the existing Bidease rows, from row 60), never at the top. A row that
  does not reach Raw data raises a critical banner naming it.
- **The source workbook's window.** See section 6, step 7.
- **A campaign under the wrong portal.** V4 files every Raw data row by the portal its name carries
  (column Q), so "DNU SFQC-…" is on SFQC. If a campaign really belongs to the other portal, rename it
  so its name carries that portal ("SFQC-…" / "AQC-…"). A name with no portal falls back to column B.

## 9. Undo and backups

- **Qiddiya Setup → Undo "Fix this workbook"** puts both pacing tabs back exactly as they were before the
  first fix, formulas and B2:C2 included, from the hidden "SFQC/AAQC Pacing_Daily BACKUP <stamp>"
  copies. It asks before it starts.
  - It switches the hourly refresh off for every account. Your own trigger is deleted. A trigger
    another account installed (each account that runs *Fix* gets its own, and Apps Script lists only
    your own) is switched off and removes itself at its next run, within the hour. The message names
    those accounts when known. *Fix this workbook* switches the refresh back on.
  - It does not touch Raw data, GA4, Raw manual, Adjust Raw, APPLE1 or "Raw data BACKUP 20260807-1642".
  - Raw data columns P and Q and Adjust Clean stay; *Repair Pacing_Daily formulas* reads Adjust Clean.
    The restored formulas ignore them, so you can delete them by hand.
  - The dashboard reads from the formulas what the tabs count. After Undo it says so: critical banners
    that the tabs read Adjust Raw as it stands and file "DNU SFQC-…" by column B, and a note that they
    do not read column P. Opening the dashboard still keeps Adjust Clean current, which the restored
    formulas do not read.
  - Later runs of *Fix this workbook* make no new pacing backups, so Undo always goes back to the tabs
    as they were before the first fix.
- **Install the original doc formulas (not an undo)** installs `PACING_ALL`, the formula set from the
  original project doc. That is not what the live tabs had, and the dashboard flags it as after Undo. To
  go back to the unified formulas, use *Repair Pacing_Daily formulas* or *Fix this workbook*.
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
- **Snapchat "takeover", "First Story" and "_AWRN_" campaigns are Awareness.** To change that, edit
  `OBJECTIVE_TOKENS` and re-run *Fix this workbook*.
- **The portal comes from the campaign name** (`PORTAL_TOKENS`), and from column B only when the name
  carries none. To change the rule, edit `PORTAL_TOKENS` and re-run *Fix this workbook*.
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

- **Same cells as the formulas.** The payload reads Raw data (with columns P and Q), APPLE1, InMobi (Raw
  manual from 3 Aug, the backup up to 2 Aug), Adjust by position and app column, and GA4 with the tab's
  wildcards. The backup merge, the native-tab fill-in and the de-duplication are gone, so every Raw data
  row counts once, as SUMIFS counts it. Adjust is the exception: it is read through the cleaner's
  corrections, as the tab reads Adjust Clean. GA4 rows dated before their line's floor go to
  `ga4PreFloor` (C49 only).
- **One definition of every line and portal:** `PACING_LINES`, `OBJECTIVE_TOKENS`, `PORTAL_TOKENS`
  (`_rawPortal_`), `_adjustLine()`, `_ga4Bucket()`. Without column Q yet, the dashboard applies the same
  portal rule itself.
- **Adjust:** the cleaner and Adjust Clean (section 3), with `_adjustDropMislabelled_` for the cross-app
  copies and `_adjustClassify` for Organic and Pangle. `importAdjustCsv` refuses a mirror, adds up split
  rows within one file, lets a later file replace an earlier file's app-days, replaces exactly the
  app-days present, refuses a 5,000-row export, leaves today out, backs up, then rebuilds Adjust Clean.
  The fingerprint that tells whether Adjust Clean is current covers every non-blank Adjust Raw row and
  the old `Adjust Current` tab.
- **Data-health banner** (note or critical). It follows what the pacing formulas actually read (Adjust
  Clean or Adjust Raw, columns P and Q or column B), decided from the formulas. It covers:
  - spend with no portal or no row;
  - campaigns whose name carries another portal than column B: a note once the tabs read column Q,
    critical while they still filter on column B;
  - Raw manual Bidease/InMotion rows that never reached Raw data (the source's row-50 start);
  - missing, broken or loading tabs, moved headers, and an empty Raw data;
  - Adjust problems, including unreadable and future days, and an Adjust Clean that is behind Adjust
    Raw or short of rows;
  - spend gaps (`meta.health.spendGaps`, with where to paste the spend), times of day on the C2 day, B2
    after C2, and the AAQC window.

  Each note says whether the tabs, the dashboard or both are affected.
- **`validateDashboard`** first brings Adjust Clean up to date, then compares 350 figures to the cent,
  reading what the formulas read: every line, row 28 (E–J, N, O, F, K, L, M, X, P), C49/D49 and C41.
  With a critical issue, the result starts with "CHECK".
- **Housekeeping:**
  - `requireSheetUser_()` guards the menu functions (section 5).
  - `_ss()` refuses a `CFG.SHEET_ID` that is not the bound file.
  - Backups are stamped to the second and pruned.
  - The standalone export escapes every `<` in the embedded data, so no campaign name can break the page.
  - Date formatting is cached: a dashboard load made about 147,000 `formatDate` calls, and now about
    220 (one per distinct date, plus the date spine). Every dashboard load or Refresh is a new execution,
    so the cache starts empty each time.

**Untitled.gs** (setup)

- **`fixThisWorkbook()`** runs the steps in section 6.
- **`buildPacingSpec_()`** generates:
  - the media rows (SUMIFS on columns P and Q, with each row's floor and the tab's B2:C2);
  - rows 22 and 24 from `CFG`;
  - the Adjust rows from Adjust Clean;
  - the GA4 floors, and Google N without UAC;
  - row 28 with ratios, plus the check cells (C39 on column Q) and labels (section 2).
- **Menu:** the menu gained *Install the original doc formulas (not an undo)* and *Undo "Fix this
  workbook"*, and `onOpen()` now adds the Pacing dashboard menu too. Undo switches the hourly refresh off
  for every account (section 9).
- **Step 3** refuses an imported Raw data and backs up a pasted one. Its `RAW_FORMULA` no longer adds
  TikTok's Purchase events (SKAN). *Quick check* and the Validation tab check columns P and Q and Adjust
  Clean.

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
  - the light-mode source tags are fixed;
  - Link clicks show "—" for Snapchat and Google, which report none (section 7).
- **"Adjust feed dropped?" tag and note.** They appear when a channel's Adjust installs per $ over the
  last 14 days fall below a tenth of the 28 days before, or when the platform claims at least 10× what
  Adjust verifies. Both windows need $2,000+ spend. The check runs in the browser only.
- **How it adds up → Check it against the tabs** walks each source tab from its plain SUM() to the cards.
  - Media example, SFQC, all dates:

    | Step | Impressions |
    |---|---:|
    | Raw data SUM() | 356,683,630 |
    | + stored as text (InMobi) | 30,063,025 |
    | − InMobi rows: copies of Raw manual | −36,827,172 |
    | − Apple rows: row 22 reads APPLE1 | −621,306 |
    | Raw manual SUM() | 23,701,280 |
    | + stored as text (InMobi) | 115,027,745 |
    | − Bidease rows: copies found in Raw data | −23,701,280 |
    | + InMobi in the backup tab | 41,150,927 |
    | + APPLE1 SUM() | 621,306 |
    | **= counted** | **506,098,155** |

    A Raw manual Bidease/InMotion row that is not in Raw data is listed as "not in Raw data" instead.
  - Adjust example: SFQC 38,159 − 483 organic − 147 copies − 3 before the row starts = **37,526**
    installs; AAQC 46,480 − 595 − 6,092 − 299 = **39,494**.
  - With a Platform or Objective filter on, the footer says the table covers every platform.
- **The Method page** describes the current rules: the portal from the campaign name (column Q), the
  line rules as in `OBJECTIVE_TOKENS`, the InMobi dates, column P, what column J holds per platform,
  Adjust Clean, the CPI/CPA exception, and what All / Tab period / 7d cover. It says the tabs read Adjust
  Clean only when their formulas do.

**appsscript.json**: adds the `userinfo.email` and `script.scriptapp` scopes. The web-app settings are
unchanged.

## 12. Tests

```
cd tests && npm install && node harness.js
```

The harness builds `tests/fixture.js`, a synthetic workbook with each trap above, including a "First
Story" takeover whose column B says AAQC. It evaluates the generated pacing formulas with HyperFormula
and runs Code.gs against a mock of the Apps Script API. The mock stores formulas separately, so a write
into an import is caught. It then loads Dashboard.html in jsdom.

- **Four passes:** as built, after *Clean Adjust Raw*, after a CSV import, and with
  `CFG.WEB_REVENUE_FROM_GA4` flipped to `false`.
  - In each pass, `validateDashboard` compares 350 figures: every line and all of row 28.
  - The page check covers every line (E, G, I, N, O, K, L, M, X) and row 28's F, J, K, L, M, X and P.
    The server check covers the rest of row 28.
  - Every view × portal × filter is rendered without errors.
  - A second *Clean Adjust Raw* changes nothing (the build time in M1 aside).
- ***Fix this workbook*, on a pasted copy:**
  - the column-P and column-Q formulas, which, read independently, equal Code.gs on every row;
  - text numbers converted, the date window, Adjust Clean built and Adjust Raw untouched;
  - the trigger, every generated cell and the two hidden backups;
  - an unchanged re-run, 0 differ, and a clean Quick check;
  - *Validate* right after Adjust Raw changes: 0 differ; an Adjust Clean that cannot be rebuilt is
    critical; a failed rebuild keeps the previous copy and the next load rebuilds it;
  - Undo restores the exact pre-fix formulas, the banner turns critical (Adjust, portal) with the
    column-P note, and the hourly refresh is off for every account (a leftover trigger removes itself).
- ***Fix this workbook*, on an IMPORTRANGE copy:** 0 writes into imported columns, column P added,
  Adjust Clean built, Raw manual untouched, and the importer refuses.
- **The dashboard link:** an anonymous visitor calls all 62 public functions, before and after *Fix*.
  Nothing in the workbook, its properties or triggers changes, and no account name or Adjust data comes
  back. The gate's two messages are checked.
- **Rules on hand-made inputs:** genuine early Adjust rows are not re-dated and a short dd/MM paste is;
  *Clean Adjust Raw* before *Fix* still gives the critical banner; a Raw manual Bidease row missing from
  Raw data is critical; the export survives a campaign name holding `<!--<script>`, `</script>` and
  U+2028.
- It ends with `PASSED`.
- `--old DIR` first runs the original files through the same server check (288 compared, 124 differ).
  It currently stops at the page check, which the original page cannot run.

Checks run on the typed copy of the live workbook, outside the repo:

- *Fix this workbook*, then *Validate*: 350 compared, 350 match. The page against the tabs: 0 differ.
  The column-Q formula, read independently, equals Code.gs on every row.
- Adjust Clean after *Fix*: 7,777 rows whose columns add up to the dashboard: 77,020 installs (SFQC
  37,526, AAQC 39,494), 8,889 bookings.
- An independent Python recount from the raw rows, with the portal taken from the name: 416 pacing
  cells, 0 differ.
- A simulation of V4's IMPORTRANGE tabs: 0 writes into imported columns, the Q formula agrees with
  Code.gs on all 8,636 rows, and the importer refused.
