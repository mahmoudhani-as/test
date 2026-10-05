/**
 * Qiddiya Media Pacing — dashboard server
 *
 * The dashboard is a second view of the two Pacing_Daily tabs, so it counts with the
 * pacing tabs' own rules: the same source cells, the same filters, the same line split,
 * the same date floors. Every rule is written down once, in this file:
 *
 *   PACING_LINES      which pacing row a platform × objective lands on, and its date floor
 *   OBJECTIVE_TOKENS  the campaign-name taxonomy (Raw data's objective column P is generated from it)
 *   _adjustLine()     which pacing row an Adjust channel × objective lands on
 *   _ga4Bucket()      which pacing row a paid GA4 session lands on
 *
 * Untitled.gs generates the pacing formulas from the same definitions, so the tab and the
 * dashboard cannot drift apart again.
 *
 * Data problems are listed in the dashboard banner. Adjust Raw is the one source the script
 * corrects (dates Sheets mis-parsed, overlapping or mislabelled imports, numbers stored as
 * text, channel labels): "Adjust Clean" holds the corrected copy the pacing formulas read, and
 * the dashboard reads Adjust Raw through the same corrections in memory, so both agree. Raw
 * data's portal is decided from the campaign name (column Q, _rawPortal_), because the source
 * workbook's column B files every name that does not start with "SFQC" under AAQC. Every
 * other problem (campaigns with no portal, text numbers in Raw data) is fixed in the source.
 *
 * Run validateDashboard() after any source or formula change; it compares the payload
 * with both pacing tabs cell by cell, totals row included.
 */

var CFG = {
  RAW: 'Raw data',
  RAW_MANUAL: 'Raw manual',
  RAW_BACKUP: 'Raw data BACKUP 20260807-1642',
  APPLE: 'APPLE1',
  ADJUST: 'Adjust Raw',
  // Where the old CSV importer wrote. The pacing formulas never read it, which is one of
  // the reasons the dashboard and the tab disagreed. "Clean Adjust Raw" folds its rows into
  // Adjust Raw and retires it; the importer now writes to Adjust Raw directly.
  ADJUST_LEGACY: 'Adjust Current',
  // The corrected copy of Adjust Raw that the pacing formulas read (dates repaired, duplicate
  // and mislabelled imports removed). The script rebuilds it — hourly, from the menu, and
  // whenever the dashboard finds it out of date. Adjust Raw itself is never modified, so it
  // can stay an IMPORTRANGE from the source workbook.
  ADJUST_CLEAN: 'Adjust Clean',
  // Raw data column holding each row's pacing objective. P sits outside an IMPORTRANGE of
  // A:O, so the column can be added without breaking an imported Raw data tab.
  OBJECTIVE_COL: 'P',
  // Raw data column holding each row's portal (SFQC / AAQC / UNMAPPED), worked out from the
  // campaign name (_rawPortal_), column B only where the name carries no portal. Q also sits
  // outside the A:O import. The pacing formulas filter on it instead of column B.
  PORTAL_COL: 'Q',
  GA4: 'GA4',
  PACING: 'SFQC Pacing_Daily',      // holds the window in B2:C2 (Raw data N2:O2 follows it)
  PACING_TABS: { SFQC: 'SFQC Pacing_Daily', AAQC: 'AAQC Pacing_Daily' },
  // LEAVE THIS BLANK unless you know you need it. A bound script finds its own
  // spreadsheet. If you do fill it in, it must be a sheet the account running the
  // script can open — pointing it at a sheet on another account is what produces
  // PERMISSION_DENIED.
  SHEET_ID: '',
  FX: 3.78,                         // SAR per USD — matches column F on the pacing tabs
  TZ: 'Asia/Riyadh',
  // Adjust: the awareness/YouTube rows (7-10) have no floor, every other row starts here.
  ADJUST_FROM: '2026-07-02',
  // Pacing row 24 (InMobi): the Raw data backup holds 16 Jul - 2 Aug; Raw manual is read from
  // 3 Aug. InMobi days still missing (3 - 31 Aug) go into Raw manual in the SOURCE workbook when
  // this file's Raw manual is an IMPORTRANGE (as in V4). Never type into an imported tab.
  INMOBI_MANUAL_FROM: '2026-08-03',
  INMOBI_BACKUP_TILL: '2026-08-02',
  INMOBI_LAST_ROW: 10000,           // row 24 reads $A$2:$A$10000
  // Portal identifiers exactly as the pacing formulas test them.
  ADJUST_APP: { SFQC: 'Six Flags', AAQC: 'Aquarabia' },                           // Adjust Raw!D
  APPLE_APP: { SFQC: 'Six Flags Qiddiya City', AAQC: 'Aquarabia Qiddiya City' },  // APPLE1!B
  GA4_PROPERTY: { SFQC: 'six flags', AAQC: 'aquarabia' },                         // GA4!B "Six Flags*"
  // GA4: a session is paid when the default channel group is one of these two.
  PAID_GROUPS: ['paid search', 'paid social'],
  // Hidden "<tab> BACKUP <stamp>" copies kept per tab; older ones are deleted (each is a full
  // copy of the tab, and the workbook is capped at 10M cells).
  BACKUPS_KEPT: 3,
  // Adjust "Untrusted Devices" (Adjust's fraud filter: anonymous IPs, anomalies) is not a paid
  // network. true = counted as Organic, so no pacing row or dashboard line counts it.
  ADJUST_EXCLUDE_UNTRUSTED: true,
  // Revenue (column X) on the four web lines — Snapchat awareness, TikTok awareness,
  // TikTok Search, Google Search. true = GA4 web revenue, which is what the live report's
  // X7, X8, X15 and X16 use. false = Adjust revenue. Change it here and re-run
  // "Qiddiya Setup -> Fix this workbook": the tab and the dashboard switch together.
  WEB_REVENUE_FROM_GA4: true
};

var FLOOR_JUL2 = '2026-07-02';

/*
 * The pacing rows. One row = one platform × objective. `floor` is the media date floor
 * the row carries (a string for both portals, or one per portal); `ga4` is the GA4 bucket
 * whose paid transactions land in column M; `web` marks the four web lines (see
 * CFG.WEB_REVENUE_FROM_GA4); `source` marks rows that do not read Raw data.
 */
var PACING_LINES = [
  { row: 7,  plat: 'Snapchat', obj: 'Awareness',  label: 'Snapchat — Awareness', ga4: 'Snapchat', web: true },
  { row: 8,  plat: 'TikTok',   obj: 'Awareness',  label: 'TikTok — Awareness',   ga4: 'TikTok',   web: true },
  { row: 9,  plat: 'X',        obj: 'Awareness',  label: 'X — Awareness' },
  { row: 10, plat: 'Google',   obj: 'Awareness',  label: 'YouTube — Awareness' },
  { row: 15, plat: 'TikTok',   obj: 'Search',     label: 'TikTok Search',  ga4: 'TikTok-cpc', web: true },
  { row: 16, plat: 'Google',   obj: 'Search',     label: 'Google Search',  ga4: 'Google', web: true, floor: FLOOR_JUL2 },
  { row: 17, plat: 'Snapchat', obj: 'Conversion', label: 'Snapchat App',   floor: FLOOR_JUL2 },
  { row: 18, plat: 'TikTok',   obj: 'Conversion', label: 'TikTok App' },
  { row: 19, plat: 'Meta',     obj: 'Conversion', label: 'Meta App',       ga4: 'Meta',
    floor: { SFQC: '2026-07-02', AAQC: '2026-07-01' } },
  { row: 20, plat: 'X',        obj: 'Conversion', label: 'X App',          floor: FLOOR_JUL2 },
  { row: 21, plat: 'Google',   obj: 'Conversion', label: 'Google App Ads', floor: FLOOR_JUL2 },
  { row: 22, plat: 'Apple',    obj: 'Conversion', label: 'Apple Ads',      floor: FLOOR_JUL2, source: 'APPLE1' },
  { row: 23, plat: 'Bidease',  obj: 'Conversion', label: 'Bidease',        floor: FLOOR_JUL2 },
  { row: 24, plat: 'InMobi',   obj: 'Conversion', label: 'InMobi',         floor: FLOOR_JUL2, source: 'InMobi' },
  { row: 25, plat: 'InMotion', obj: 'Conversion', label: 'InMotion',       floor: FLOOR_JUL2 },
  { row: 26, plat: 'Other',    obj: 'Other',      label: 'Other (Adjust / GA4 only)', ga4: 'Other', source: 'none' }
];
var LINE_BY_KEY = {};
PACING_LINES.forEach(function (l) { l.key = l.plat + '|' + l.obj; LINE_BY_KEY[l.key] = l; });

/*
 * One authoritative campaign taxonomy for platform delivery rows. Awareness is tested
 * before Search, and each row lands on exactly one line — so a name such as
 * "SFQC_Snapchat_AWRN_..." (which contains both "snapchat_awr" and "_awrn_") is counted
 * once, not once per matching wildcard as the old SUMIFS sums did. Raw data's objective column
 * (P) is generated from this table (Untitled.gs), so edit it here and re-run Qiddiya Setup →
 * Fix this workbook (not step 3, which replaces Raw data with the Supermetrics formula).
 */
var OBJECTIVE_TOKENS = {
  Snapchat: {
    Awareness: ['snapchat_awr', '_awrn_', 'takeover', 'take over', 'take-over',
      'first story', 'first_story', 'first-story']
  },
  TikTok: {
    Awareness: ['tiktok_awr', '_awrn_'],
    Search: ['_tt_search', '_conv_sal_', '_search_cu', '_web_bra+gen']
  },
  X: { Awareness: ['x_awr', '_awrn_'] },
  Google: { Awareness: ['_yt_'], Search: ['sem'] }
};

/**
 * ONE BUTTON. Pick this in the Apps Script Run dropdown and press Run, or use
 * Pacing dashboard -> Open from the sheet. Both do the same thing.
 * Running it from the editor needs the spreadsheet open in another tab — that is
 * where the dialog appears.
 */
function OPEN_DASHBOARD() {
  showDashboard();
}

/**
 * Serves the dashboard at the deployment URL. For the first release use New
 * deployment. For every later release edit the SAME active deployment and select
 * New version; its client-facing /exec URL stays unchanged.
 * "Execute as: Me" lets a viewer see the numbers without access to the sheet itself,
 * so pick who has access deliberately.
 */
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Dashboard')
    .setTitle('Qiddiya Media Pacing')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
/**
 * Apps Script keeps only one onOpen() per project. Untitled.gs owns it and calls this,
 * so both the "Qiddiya Setup" and the "Pacing dashboard" menus appear.
 */
function dashboardMenu_() {
  SpreadsheetApp.getUi().createMenu('Pacing dashboard')
    .addItem('Open', 'showDashboard')
    .addItem('Import latest Adjust CSVs', 'showAdjustImporter')
    .addItem('Clean Adjust Raw (dates, duplicates)', 'cleanAdjustRaw')
    .addItem('Validate against the pacing tabs', 'validateDashboard')
    .addItem('Export a standalone HTML file', 'exportStandalone')
    .addSeparator()
    .addItem('Check the setup', 'checkSetup')
    .addToUi();
}

function showDashboard() {
  var html = HtmlService.createHtmlOutputFromFile('Dashboard')
    .setWidth(1600).setHeight(950);
  SpreadsheetApp.getUi().showModalDialog(html, 'Qiddiya Media Pacing');
}

/* ------------------------------------------------------------------ helpers */

/**
 * The spreadsheet, whether we are running from the sheet menu or from a deployed web
 * app. A bound script normally gets it from getActive(); CFG.SHEET_ID is the escape
 * hatch if a deployment ever hands us nothing. The setup script (Untitled.gs) always works
 * on the bound spreadsheet, so a SHEET_ID naming a different file is refused: otherwise
 * "Fix this workbook" would repair one file and rebuild Adjust Clean in another. The account
 * name goes to the log only — these messages can reach a web-app visitor.
 */
function _ss() {
  var bound = null;
  try { bound = SpreadsheetApp.getActive(); } catch (e) { bound = null; }
  if (CFG.SHEET_ID) {
    if (bound && bound.getId() !== CFG.SHEET_ID) {
      throw new Error('CFG.SHEET_ID (' + CFG.SHEET_ID + ') is not the spreadsheet this script is bound to. ' +
        'Clear CFG.SHEET_ID: the setup menu always works on the bound spreadsheet.');
    }
    if (bound) return bound;
    try {
      return SpreadsheetApp.openById(CFG.SHEET_ID);
    } catch (e) {
      Logger.log('CFG.SHEET_ID cannot be opened by ' + who_());
      throw new Error('CFG.SHEET_ID points at a spreadsheet this account cannot open (' +
        CFG.SHEET_ID + '). Either clear CFG.SHEET_ID so the script uses the sheet it is ' +
        'bound to, or share that spreadsheet with the account the script runs as (see the log).');
    }
  }
  if (!bound) {
    throw new Error('No spreadsheet in scope. Bind this script to the sheet (Extensions → ' +
      'Apps Script from inside it), or set CFG.SHEET_ID.');
  }
  return bound;
}
function who_() {
  try { return Session.getEffectiveUser().getEmail() || 'this account'; }
  catch (e) { return 'this account'; }
}

/**
 * The web app runs as the owner for anyone with the link, and google.script.run can call
 * every server function whose name does not end in "_". Everything that changes the
 * workbook, writes to Drive or reveals setup details starts with this: it runs only for
 * the person the script is executing as (from the sheet's menus, the editor or a trigger),
 * never for a web-app visitor. Two paths are deliberately open, and both only rebuild an
 * existing "Adjust Clean" the pacing tabs read, when Adjust Raw has changed, returning nothing:
 * a dashboard load and refreshAdjustClean (the hourly trigger's handler).
 * Reading either account needs the userinfo.email scope: without it (an appsscript.json that
 * was not replaced) the effective account is unreadable, and that gets its own message
 * instead of the web-link one.
 */
function requireSheetUser_() {
  // Inside the spreadsheet (its menus, or a dialog opened from them) the sheet's UI exists;
  // from the web-app link it never does. That decides on its own, so menu commands work
  // whether or not the email permission in appsscript.json has been granted.
  try { SpreadsheetApp.getUi(); return; } catch (eUi) { /* not in the sheet's UI */ }
  // Apps Script editor's Run button and the hourly trigger: the script runs as the person
  // who started it, so the two accounts are the same.
  var effective = '', err = null;
  try { effective = Session.getEffectiveUser().getEmail(); } catch (e) { err = e; }
  if (!effective) {
    throw new Error('Run this from the spreadsheet\'s menus (Qiddiya Setup or Pacing dashboard). From the ' +
      'Apps Script editor it needs to read which Google account is running it' +
      (err ? ' (' + (err.message || err) + ')' : '') + ': open Project Settings, tick "Show appsscript.json", ' +
      'replace appsscript.json with the one from FIXES.md (it adds the userinfo.email scope), save and run ' +
      'it again, accepting the authorisation prompt.');
  }
  var active = '';
  try { active = Session.getActiveUser().getEmail(); } catch (e) {}
  if (active !== effective) {
    throw new Error('This can only be run from the spreadsheet (Extensions or the sheet\'s menus), ' +
      'not from the dashboard link.');
  }
}

/**
 * A tab whose content is the output of one formula in A1 or A2 (IMPORTRANGE, QUERY, a
 * Supermetrics LET): writing into it would break the formula, so the script only reads it.
 */
function _formulaTab_(sh) {
  if (!sh) return '';
  var f = sh.getRange('A1').getFormula() || sh.getRange('A2').getFormula();
  return f ? String(f) : '';
}
function _importSource_(f) {
  var m = /IMPORTRANGE\(\s*"([^"]+)"\s*,\s*"'?([^"'!]+)'?!/i.exec(f || '');
  return m ? { key: m[1].replace(/^.*\/d\/([^/]+).*$/, '$1'), tab: m[2] } : null;
}

/**
 * What both pacing tabs' formulas read, from the formulas themselves (not from which tabs or
 * columns exist): Adjust Clean in the Adjust columns K:L, Raw data's Objective (P) and Portal (Q)
 * columns in the media rows E7:E25. Fix this workbook / Repair install formulas that read all
 * three; Undo, "Install the original doc formulas" or a hand edit put back ones that do not.
 */
function _pacingReads_(ss) {
  var out = { clean: true, objective: true, portal: true };
  var needles = {
    clean: "'" + CFG.ADJUST_CLEAN + "'!",
    objective: "'" + CFG.RAW + "'!$" + CFG.OBJECTIVE_COL + ':$' + CFG.OBJECTIVE_COL,
    portal: "'" + CFG.RAW + "'!$" + CFG.PORTAL_COL + ':$' + CFG.PORTAL_COL
  };
  ['SFQC', 'AAQC'].forEach(function (b) {
    var sh = ss.getSheetByName(CFG.PACING_TABS[b]), f = [];
    try { if (sh) f = sh.getRange('E7:L26').getFormulas(); } catch (e) { f = []; }
    function has(needle, c0, c1) {           // columns of E:L, 0-based from E
      return f.some(function (r) {
        for (var c = c0; c <= c1; c++) if (String(r[c] || '').indexOf(needle) >= 0) return true;
        return false;
      });
    }
    out.clean = out.clean && has(needles.clean, 6, 7);            // K:L
    out.objective = out.objective && has(needles.objective, 0, 0); // E
    out.portal = out.portal && has(needles.portal, 0, 0);
  });
  return out;
}

/**
 * Run this when something says PERMISSION_DENIED. It prints who the script is running
 * as, which spreadsheet it reached, and which tabs it can see.
 */
function checkSetup() {
  requireSheetUser_();
  var out = [];
  out.push('Running as: ' + who_());
  out.push('CFG.SHEET_ID: ' + (CFG.SHEET_ID || '(blank — using the bound spreadsheet)'));
  var ss;
  try {
    ss = _ss();
    out.push('Opened: ' + ss.getName());
    out.push('Id: ' + ss.getId());
  } catch (e) {
    out.push('FAILED: ' + e.message);
    Logger.log(out.join('\n'));
    try { SpreadsheetApp.getUi().alert(out.join('\n')); } catch (e2) {}
    return out.join('\n');
  }
  [CFG.RAW, CFG.RAW_MANUAL, CFG.RAW_BACKUP, CFG.APPLE, CFG.ADJUST, CFG.ADJUST_CLEAN, CFG.GA4,
    CFG.PACING_TABS.SFQC, CFG.PACING_TABS.AAQC].forEach(function (n) {
    var sh = ss.getSheetByName(n);
    out.push((sh ? '  found  ' : '  MISSING ') + n + (sh ? ' · ' + sh.getLastRow() + ' rows' : ''));
  });
  var raw = ss.getSheetByName(CFG.RAW);
  if (raw) {
    [[CFG.OBJECTIVE_COL, 'Objective'], [CFG.PORTAL_COL, 'Portal']].forEach(function (c) {
      var m1 = String(raw.getRange(c[0] + '1').getValue()).trim();
      out.push('  Raw data column ' + c[0] + ': ' + (m1 === c[1] ? c[1] :
        'no ' + c[1] + ' column — run Qiddiya Setup -> Fix this workbook'));
    });
  }
  Logger.log(out.join('\n'));
  try { SpreadsheetApp.getUi().alert(out.join('\n')); } catch (e) {}
  return out.join('\n');
}

function _sheet(name) {
  var ss = _ss();
  var sh = ss.getSheetByName(name);
  if (sh) return sh;
  var all = ss.getSheets();                       // Supermetrics may write META, not Meta
  for (var i = 0; i < all.length; i++) {
    if (all[i].getName().toLowerCase() === name.toLowerCase()) return all[i];
  }
  throw new Error('Sheet "' + name + '" not found.');
}
/** Lenient number parse — only for imports and repairs, never for counting. */
function _num(v) {
  if (v === null || v === undefined || v === '') return 0;
  var n = typeof v === 'number' ? v : parseFloat(String(v).replace(/[, ]/g, ''));
  return isNaN(n) ? 0 : n;
}
/** What SUMIFS adds up: real numbers only. Text that looks like a number counts as 0. */
function _cellNum(v) {
  return typeof v === 'number' && isFinite(v) ? v : 0;
}
/** A non-empty cell that SUMIFS will silently skip. */
function _isTextNum(v) {
  return v !== '' && v !== null && v !== undefined && typeof v !== 'number' &&
    !(v instanceof Date) && typeof v !== 'boolean';
}
/** What IFERROR(VALUE(SUBSTITUTE(x,",","")),0) produces — pacing row 24 (InMobi). */
function _valueNum(v) {
  if (typeof v === 'number') return isFinite(v) ? v : 0;
  if (v === null || v === undefined || v instanceof Date || typeof v === 'boolean') return 0;
  // VALUE() also reads a leading currency sign ("$275.02"), which Raw manual exports carry
  var s = String(v).replace(/,/g, '').trim().replace(/^(-?)\$/, '$1');
  if (!s) return 0;
  var n = Number(s);
  return isFinite(n) ? n : 0;
}
/* Utilities.formatDate is a service call and the same ~200 dates recur on every row of
   every source tab, so each Date is formatted once per run ('yyyy-MM-dd HH:mm:ss'). */
var _dayCache = {};
function _dayTime(v, tz) {
  var z = tz || CFG.TZ, k = v.getTime() + '|' + z;
  return _dayCache[k] || (_dayCache[k] = Utilities.formatDate(v, z, 'yyyy-MM-dd HH:mm:ss'));
}
function _day(v, tz) {
  if (v instanceof Date) return _dayTime(v, tz).slice(0, 10);
  return String(v || '').slice(0, 10);
}
/** A date criterion in SUMIFS only ever matches a real date cell, never text. */
function _dateCell(v, tz) {
  return v instanceof Date ? _dayTime(v, tz).slice(0, 10) : '';
}
/** A Date cell that is not midnight: "<="&C2 leaves it out on C2's own day. */
function _hasTime(v, tz) {
  return v instanceof Date && _dayTime(v, tz).slice(11) !== '00:00:00';
}
function _later(a, b) { return !a ? b : !b ? a : (a > b ? a : b); }
function _sooner(a, b) { return !a ? b : !b ? a : (a < b ? a : b); }
function _hasOwn(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
/** Yesterday in the sheet's time zone — what =TODAY()-1 shows. */
function _yesterday(tz) {
  var d = new Date(Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd') + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}
function _dateSpine(from, till) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(from || '') || !/^\d{4}-\d{2}-\d{2}$/.test(till || ''))
    return [];
  var a = from.split('-').map(Number), b = till.split('-').map(Number);
  var cursor = new Date(Date.UTC(a[0], a[1] - 1, a[2]));
  var last = new Date(Date.UTC(b[0], b[1] - 1, b[2]));
  if (cursor > last) throw new Error('Invalid report window: start date is after end date.');
  var out = [];
  while (cursor <= last) {
    out.push(Utilities.formatDate(cursor, 'UTC', 'yyyy-MM-dd'));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return out;
}
function _touchCoverage(map, key, day, fields) {
  if (!day) return;
  var e = map[key];
  if (!e) {
    e = fields || {};
    e.first = day;
    e.last = day;
    map[key] = e;
    return;
  }
  if (day < e.first) e.first = day;
  if (day > e.last) e.last = day;
}
function _coverageValues(map) {
  return Object.keys(map).sort().map(function (key) { return map[key]; });
}
/** Adjust Raw can contain dd/MM/yyyy text beside dates auto-parsed as MM/dd/yyyy.
 * Used by the cleaner (and to count suspect rows); the dashboard itself counts only
 * real date cells, exactly like the pacing formulas. */
function _adjustDay(v, row, reverseDmy, tz) {
  if (v instanceof Date) {
    if (!reverseDmy) return _day(v, tz);
    var parts = _day(v, tz).split('-');
    var year = +parts[0], month = +parts[1], day = +parts[2];
    // Dates such as 13 September cannot have been produced by swapping 13/09;
    // leave an already-valid date alone when the same import contains both kinds.
    if (day > 12) return _day(v, tz);
    return year + '-' + ('0' + day).slice(-2) + '-' + ('0' + month).slice(-2);
  }
  var s = String(v == null ? '' : v).trim();
  var dmy = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s);
  if (dmy) {
    var d = +dmy[1], m = +dmy[2], y = +dmy[3];
    var check = new Date(y, m - 1, d);
    if (check.getFullYear() !== y || check.getMonth() !== m - 1 || check.getDate() !== d)
      throw new Error('Adjust Raw row ' + row + ': invalid date ' + s);
    return y + '-' + ('0' + m).slice(-2) + '-' + ('0' + d).slice(-2);
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    var y2 = +s.slice(0, 4), m2 = +s.slice(5, 7), d2 = +s.slice(8, 10);
    var isoCheck = new Date(y2, m2 - 1, d2);
    if (isoCheck.getFullYear() !== y2 || isoCheck.getMonth() !== m2 - 1 || isoCheck.getDate() !== d2)
      throw new Error('Adjust Raw row ' + row + ': invalid date ' + s);
    return s;
  }
  throw new Error('Adjust Raw row ' + row + ': unrecognised date ' + s);
}
/** Return the exact native-Date rows that Sheets reversed while importing dd/MM.
 *
 * A workbook-wide swap is unsafe: the same sheet also contains genuine 9 July and
 * 9 August rows. The broken September batch is identifiable as a contiguous run of
 * Jan-9, Feb-9 ... Dec-9 followed by the unambiguous text date 13/09. This marks
 * only that import cohort, and can also continue from 30/09 to a swapped 01/10.
 * Blank cells (empty rows between pastes) do not break a run.
 * win ({lo, from, hi}, optional — see _adjustSwapWindow_): a short dd/MM paste such as
 * 01/10 + 02/10, stored as 10 Jan / 10 Feb, has no anchor; a native date outside lo..hi
 * whose swap lands inside from..hi AND continues the dated row before it (in sheet order,
 * within a week) is that case, and is marked too. A genuine early row (a tab that starts on
 * 1 Jun, a backfill of 1-12 Jun) sits next to its own neighbouring days, so it never is.
 * Source cells are never rewritten here. */
function _adjustReversedRows(rows, col, tz, win) {
  var marked = {};
  function blank(v) { return v === '' || v === null || v === undefined; }
  function nativeParts(v) {
    if (!(v instanceof Date)) return null;
    var iso = _day(v, tz), p = iso.split('-').map(Number);
    return { y: p[0], m: p[1], d: p[2], iso: iso };
  }
  function swapped(v) {
    var p = nativeParts(v);
    if (!p || p.d > 12) return '';
    return p.y + '-' + ('0' + p.d).slice(-2) + '-' + ('0' + p.m).slice(-2);
  }
  function nextDay(iso) {
    var p = iso.split('-').map(Number);
    return _day(new Date(Date.UTC(p[0], p[1] - 1, p[2] + 1)), 'UTC');
  }

  // An unambiguous text day (13–31) anchors the native Date block immediately
  // before it. Every member of that block has day == the text month.
  for (var i = 1; i < rows.length; i++) {
    if (typeof rows[i][col] !== 'string') continue;
    var a = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(rows[i][col].trim());
    if (!a || +a[1] <= 12) continue;
    var targetMonth = +a[2], targetYear = +a[3];
    for (var k = i - 1; k >= 1; k--) {
      if (blank(rows[k][col])) continue;
      var p = nativeParts(rows[k][col]);
      if (!p || p.y !== targetYear || p.d !== targetMonth) break;
      marked[k] = true;
    }
  }

  // If an export ends before day 13, the same corruption is still a distinctive
  // contiguous run: one constant day number across at least three source months.
  var r = 1;
  while (r < rows.length) {
    var first = nativeParts(rows[r][col]);
    if (!first || first.d > 12) { r++; continue; }
    var start = r, months = {}, lastMonth = 0, ordered = true;
    while (r < rows.length) {
      if (blank(rows[r][col])) { r++; continue; }
      var cur = nativeParts(rows[r][col]);
      if (!cur || cur.y !== first.y || cur.d !== first.d) break;
      months[cur.m] = 1;
      if (cur.m < lastMonth) ordered = false;
      lastMonth = cur.m;
      r++;
    }
    if (ordered && Object.keys(months).length >= 3)
      for (var q = start; q < r; q++) if (!blank(rows[q][col])) marked[q] = true;
  }

  if (win && win.auto) {
    // lo/from: the earliest day the tab states unambiguously (day of month 13-31, as a real
    // date or as dd/MM text). A day-12-or-lower date before it whose swap lands inside the
    // tab's own span is a short dd/MM paste the two rules above cannot see.
    var lo = '';
    for (var u = 1; u < rows.length; u++) {
      var uv = rows[u][col], iso = '';
      var un = nativeParts(uv);
      if (un && un.d > 12) iso = un.iso;
      else if (typeof uv === 'string') {
        var ut = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(uv.trim());
        if (ut && +ut[1] > 12) iso = ut[3] + '-' + ('0' + ut[2]).slice(-2) + '-' + ('0' + ut[1]).slice(-2);
      }
      if (iso && (!lo || iso < lo)) lo = iso;
    }
    win = lo ? { lo: lo, from: lo, hi: win.hi } : null;
  }
  if (win) {
    // A short paste sits right after the rows it continues: its swapped day must follow the
    // previous dated row (in sheet order) within a week. A genuine early row sits next to its
    // own neighbouring days, so its swap (weeks or months away) never qualifies.
    var prevEff = '';
    for (var w = 1; w < rows.length; w++) {
      var cell = rows[w][col];
      if (blank(cell)) continue;
      var np = nativeParts(cell), sw = np && swapped(cell);
      if (np && !marked[w] && sw && prevEff && (np.iso < win.lo || np.iso > win.hi) &&
          sw >= win.from && sw <= win.hi && sw >= prevEff &&
          sw <= _day(new Date(Date.UTC(+prevEff.slice(0, 4), +prevEff.slice(5, 7) - 1, +prevEff.slice(8, 10) + 7)), 'UTC'))
        marked[w] = true;
      if (np) prevEff = marked[w] ? swapped(cell) : np.iso;
      else if (typeof cell === 'string' && /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.test(cell.trim())) {
        try { prevEff = _adjustDay(cell, w + 1, false, tz); } catch (e) { /* keep the previous day */ }
      }
    }
  }

  // Continue an explicit dd/MM sequence across a month boundary. Example:
  // 30/09 text followed by a native Jan-10 cell is really 01/10.
  var cursor = '';
  for (var j = 1; j < rows.length; j++) {
    var value = rows[j][col];
    if (typeof value === 'string') {
      var m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(value.trim());
      if (m) {
        try { cursor = _adjustDay(value, j + 1, false, tz); } catch (e) { cursor = ''; }
      }
      continue;
    }
    var original = nativeParts(value), rev = swapped(value);
    if (!original) continue;
    if (marked[j]) { cursor = rev; continue; }
    if (cursor && rev && (rev === cursor || rev === nextDay(cursor))) {
      marked[j] = true; cursor = rev; continue;
    }
    if (cursor && (original.iso === cursor || original.iso === nextDay(cursor))) {
      cursor = original.iso; continue;
    }
    cursor = '';
  }
  return marked;
}
/** The window _adjustReversedRows tests short pastes against: Adjust Raw's earliest unambiguous day .. today. */
function _adjustSwapWindow_(ss, tz) {
  // The window comes from Adjust Raw's own dates (see _adjustReversedRows), never from the
  // report's B2: moving B2 to a new flight must not re-date older, genuine rows.
  return { auto: true, hi: Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd') };
}
/** Column index (1-based) of a header, or 0. */
/** Raw data's objective column: CFG.OBJECTIVE_COL (P) when headed "Objective", else M. */
function _objectiveIndex_(header) {
  var p = CFG.OBJECTIVE_COL.charCodeAt(0) - 65;
  function isObj(i) { return String(header[i] == null ? '' : header[i]).trim().toLowerCase() === 'objective'; }
  return isObj(p) ? p : isObj(12) ? 12 : -1;
}
function _col(header, name) {
  for (var i = 0; i < header.length; i++) {
    if (String(header[i]).trim() === name) return i + 1;
  }
  return 0;
}
/** Header names the pacing formulas assume at fixed positions; returns what is off. */
function _headerProblems(header, expected, tabName) {
  var out = [];
  Object.keys(expected).forEach(function (i) {
    var want = String(expected[i]).toLowerCase();
    var got = String(header[i] == null ? '' : header[i]).trim().toLowerCase();
    if (got !== want) {
      out.push(tabName + ' column ' + String.fromCharCode(65 + Number(i)) + ' should be "' +
        expected[i] + '" but is "' + (header[i] == null ? '' : header[i]) + '"');
    }
  });
  return out;
}

/**
 * Campaign names are the join between Raw data, Adjust and GA4, so they have to
 * travel with every row. Sent verbatim they would be the largest thing in the
 * payload, so each distinct name is stored once in payload.camps and the rows carry
 * its index. The client rehydrates them in one pass at boot.
 */
var _campList, _campIx;
function _campReset() { _campList = []; _campIx = {}; }
function _campIndex(name) {
  var k = '#' + String(name == null ? '' : name).trim();   // '#' keeps Object.prototype keys out
  if (_campIx[k] === undefined) {
    _campIx[k] = _campList.length;
    _campList.push(k.slice(1));
  }
  return _campIx[k];
}

/** Platform + campaign -> objective. Fallback only: Raw data's objective column is authoritative. */
function _objective(plat, campaign) {
  var c = String(campaign || '').toLowerCase();
  var rules = OBJECTIVE_TOKENS[plat] || {};
  var order = ['Awareness', 'Search'];
  for (var i = 0; i < order.length; i++) {
    var objective = order[i], tokens = rules[objective] || [];
    for (var j = 0; j < tokens.length; j++) {
      if (c.indexOf(tokens[j]) >= 0) return objective;
    }
  }
  return 'Conversion';
}

/* Platform and portal names as SUMIFS compares them: case-insensitive, otherwise exact. */
var KNOWN_PLATFORMS = { snapchat: 'Snapchat', tiktok: 'TikTok', x: 'X', google: 'Google',
  meta: 'Meta', apple: 'Apple', bidease: 'Bidease', inmobi: 'InMobi', inmotion: 'InMotion' };
function _canonPlat(v) {
  var k = String(v == null ? '' : v).toLowerCase();
  return _hasOwn(KNOWN_PLATFORMS, k) ? KNOWN_PLATFORMS[k] : '';
}
function _brandCell(v) {
  var b = String(v == null ? '' : v).toUpperCase();
  return b === 'SFQC' || b === 'AAQC' ? b : '';
}
/*
 * The portal a campaign name carries (tested on the upper-cased name, SFQC first; FIRST STORY
 * only on Snapchat, where the Six Flags takeovers run under that name). Raw data's portal
 * column Q is generated from these patterns (Untitled.gs portalColumnFormula_), so the pacing
 * formulas and this dashboard file every row the same way. The live source workbook's column B
 * does NOT follow this rule: it files every name that does not start with "SFQC" under AAQC.
 * Plain regular expressions that read the same in JavaScript and in Sheets' REGEXMATCH (RE2).
 */
var PORTAL_TOKENS = { SFQC: 'SFQC|SIX[ _-]?FLAGS', SFQC_SNAPCHAT: 'FIRST[ _-]?STORY', AAQC: 'AAQC|AQQC|AQC[-_]|AQUARABIA' };
function _campaignPortal_(plat, camp) {
  var u = String(camp == null ? '' : camp).toUpperCase();
  if (new RegExp(PORTAL_TOKENS.SFQC).test(u) ||
      (plat === 'Snapchat' && new RegExp(PORTAL_TOKENS.SFQC_SNAPCHAT).test(u))) return 'SFQC';
  if (new RegExp(PORTAL_TOKENS.AAQC).test(u)) return 'AAQC';
  return '';
}
/** A Raw data row's portal, as column Q computes it: the name decides, column B where it carries none. */
function _rawPortal_(platCell, camp, bCell) {
  return _campaignPortal_(_canonPlat(platCell), camp) || _brandCell(bCell);
}
/** Raw data's portal column: CFG.PORTAL_COL (Q) when headed "Portal", else -1. */
function _portalIndex_(header) {
  var q = CFG.PORTAL_COL.charCodeAt(0) - 65;
  return String(header[q] == null ? '' : header[q]).trim().toLowerCase() === 'portal' ? q : -1;
}
function _matchBrand(map, v) {
  var s = String(v == null ? '' : v).toLowerCase();
  for (var b in map) if (_hasOwn(map, b) && map[b].toLowerCase() === s) return b;
  return '';
}
function _ga4Brand(property) {
  var s = String(property == null ? '' : property).toLowerCase();
  for (var b in CFG.GA4_PROPERTY)
    if (_hasOwn(CFG.GA4_PROPERTY, b) && s.indexOf(CFG.GA4_PROPERTY[b]) === 0) return b;
  return '';
}
function _mediaFloor(line, brand) {
  var f = line.floor;
  if (!f) return '';
  return typeof f === 'string' ? f : (f[brand] || '');
}
function _adjustFloor(line) {
  return line.obj === 'Awareness' ? '' : CFG.ADJUST_FROM;
}

/**
 * Adjust channel + objective -> pacing line key. Mirrors the K/L/X formulas:
 *   Meta, Apple, Bidease, InMobi, InMotion   one row each, every objective
 *   Google   YouTube/Awareness -> row 10, Search -> row 16, everything else -> row 21
 *   TikTok   Awareness -> row 8, Search -> row 15, everything else -> row 18
 *   Snapchat / X   Awareness -> row 7 / 9, everything else -> row 17 / 20
 *   Organic  never counted
 *   anything else (Other, blank, a new partner) -> row 26, so nothing paid disappears
 * Case-insensitive like SUMIFS, but not trimmed — "Meta " is not "Meta" to SUMIFS either.
 */
var ADJUST_ONE_LINE = { Meta: 1, Apple: 1, Bidease: 1, InMobi: 1, InMotion: 1 };
function _adjustLine(channel, objective) {
  var ch = String(channel == null ? '' : channel);
  if (ch.toLowerCase() === 'organic') return '';
  var c = _canonPlat(ch);
  if (!c) return 'Other|Other';
  if (ADJUST_ONE_LINE[c]) return c + '|Conversion';
  var o = String(objective == null ? '' : objective).toLowerCase();
  if (c === 'Google') {
    return o === 'youtube' || o === 'awareness' ? 'Google|Awareness' :
      o === 'search' ? 'Google|Search' : 'Google|Conversion';
  }
  if (o === 'awareness') return c + '|Awareness';
  if (o === 'search' && c === 'TikTok') return 'TikTok|Search';
  return c + '|Conversion';
}

/**
 * GA4 source/medium -> bucket, exactly as column M of the pacing tabs reads it:
 *   snap*                                 -> row 7
 *   tiktok* with "search" in the campaign -> row 15, other tiktok* -> row 8
 *   google*                               -> row 16
 *   instagram* facebook* "fb *" "ig *" meta* -> row 19
 *   everything else that is paid          -> row 26 (M26 is the remainder)
 */
var GA4_LINE = { Snapchat: 'Snapchat|Awareness', TikTok: 'TikTok|Awareness',
  'TikTok-cpc': 'TikTok|Search', Google: 'Google|Search', Meta: 'Meta|Conversion',
  Other: 'Other|Other' };
function _ga4Bucket(sourceMedium, campaign) {
  var s = String(sourceMedium == null ? '' : sourceMedium).toLowerCase();
  if (s.indexOf('snap') === 0) return 'Snapchat';
  if (s.indexOf('tiktok') === 0) {
    return String(campaign == null ? '' : campaign).toLowerCase().indexOf('search') >= 0 ?
      'TikTok-cpc' : 'TikTok';
  }
  if (s.indexOf('google') === 0) return 'Google';
  if (/^(instagram|facebook|fb |ig |meta)/.test(s)) return 'Meta';
  return 'Other';
}

/* Fixed column positions the pacing formulas read (0-based index -> header). */
var ADJUST_LAYOUT = ['day', 'network', 'campaign_network', 'app', 'all_revenue',
  'general revenue_revenue_est', 'paid_installs', 'installs', 'bookingconfirmed_events',
  'channel', 'objective'];
var ADJUST_EXPECT = { 0: 'day', 1: 'network', 2: 'campaign_network', 3: 'app',
  4: 'all_revenue', 6: 'paid_installs', 7: 'installs', 8: 'bookingconfirmed_events',
  9: 'channel', 10: 'objective' };
var RAW_EXPECT = { 0: 'A', 1: 'Campaign', 2: 'Campaign name', 3: 'Day', 5: 'Impressions',
  6: 'Amount spent (USD)' };                                   // Raw data, Raw manual, the backup
var APPLE_EXPECT = { 0: 'Date', 1: 'App Name', 3: 'Spend', 4: 'Impressions', 5: 'Taps',
  6: 'Installs (Total)' };
var GA4_EXPECT = { 1: 'GA4 property', 2: 'Date', 3: 'Session campaign name',
  4: 'Session default channel grouping', 5: 'Session source / medium', 6: 'Transactions',
  7: 'Purchase revenue' };

/* ------------------------------------------------------------------ payload */

function getPacingDashboardData(opts) {
  // opts.asTab: read Adjust Raw exactly as the pacing formulas do (validateDashboard uses it)
  var asTab = !!(opts && opts.asTab);
  var ss = _ss();
  var tz = ss.getSpreadsheetTimeZone ? ss.getSpreadsheetTimeZone() : CFG.TZ;
  _campReset();
  var issues = [];
  function issue(level, text) { issues.push({ level: level, text: text }); }
  function money(v) { return '$' + Math.round(v).toLocaleString('en-US'); }
  function count(n) { return Number(n).toLocaleString('en-US'); }
  /* A source tab's values. A missing tab, or an import that is broken or still loading
     (IMPORTRANGE shows #REF! / Loading… in A1 and nothing below), is a banner — the other
     sources still load. */
  function sourceValues(name, rowsNote, expect) {
    var sh = null;
    try { sh = _sheet(name); } catch (e) {
      issue('crit', 'Tab "' + name + '" is missing (renamed or deleted) — pacing ' + rowsNote + ' read it ' +
        'and show #REF!, and this dashboard has nothing for them.');
      return [[]];
    }
    var v = sh.getDataRange().getValues(), a1 = String(v[0] && v[0][0] != null ? v[0][0] : '').trim();
    if (/^#|^loading/i.test(a1)) {
      issue('crit', '"' + name + '" shows ' + a1 + ' in A1: its import is broken or still loading, so pacing ' +
        rowsNote + ' and this dashboard read nothing from it. Open the tab and check the IMPORTRANGE.');
      return [[]];
    }
    _headerProblems(v[0] || [], expect, name).forEach(function (p) {
      issue('crit', p + ' — pacing ' + rowsNote + ' read "' + name + '" by position.');
    });
    return v;
  }
  var timedOnTill = 0;              // dated C2 with a time of day: "<="&C2 leaves them out
  function timed(v, day) { if (day === till && _hasTime(v, tz)) timedOnTill++; }

  /* ---- window: SFQC Pacing_Daily B2:C2, the same window Raw data N2:O2 follows ---- */
  var pac = ss.getSheetByName(CFG.PACING);
  var from = pac ? _day(pac.getRange('B2').getValue(), tz) : '';
  var till = pac ? _day(pac.getRange('C2').getValue(), tz) : '';
  var aPac = ss.getSheetByName(CFG.PACING_TABS.AAQC);
  // what the pacing formulas actually read: Undo, "Install the original doc formulas" or a hand
  // edit can put formulas back that read Adjust Raw as it stands and filter on Raw data column B
  var reads = _pacingReads_(ss);
  if (aPac) {
    var af = _day(aPac.getRange('B2').getValue(), tz), at = _day(aPac.getRange('C2').getValue(), tz);
    if (af !== from || at !== till) {
      issue('crit', 'AAQC Pacing_Daily runs ' + af + ' → ' + at + ' but SFQC Pacing_Daily runs ' +
        from + ' → ' + till + '. Raw data and this dashboard follow the SFQC dates, so the AAQC ' +
        'tab cannot agree with either. Put the same dates in B2:C2 on both tabs.');
    }
  }
  // The tabs count B2:C2. The dashboard loads every day from B2 to the latest day with data
  // (yesterday, or C2 if that is later), so a C2 left on an old date never cuts "All" short.
  // It opens on everything; the "Tab period" button shows exactly what the tabs count.
  var loadTill = _later(till, _yesterday(tz));
  function inWindow(day) { return !!day && (!from || day >= from) && day <= loadTill; }

  /* Per source tab and day: what a plain SUM() of the tab sees, what is stored as text, what
     is left out and why, and what is counted — the Method page's "Check it against the tabs"
     table, so every total can be traced back to the tabs by hand. */
  var reconMap = {};
  function tally(brand, src, day, cat, impr, spend) {
    var k = brand + '|' + src + '|' + day + '|' + cat;
    var e = reconMap[k] || (reconMap[k] = { b: brand, s: src, d: day, k: cat, i: 0, p: 0, n: 0 });
    e.i += impr; e.p += spend; e.n++;
  }
  // outcome: 'counted' or the reason the row is left out. readsText: the pacing row reads the
  // cells with VALUE() (InMobi), not SUMIFS (which skips text). spendDiv: 3.78 for X.
  function reconRow(brand, src, day, imprCell, spendCell, outcome, readsText, spendDiv) {
    var vi = _valueNum(imprCell), vs = _valueNum(spendCell);
    var ni = _cellNum(imprCell), ns = _cellNum(spendCell);
    tally(brand, src, day, 'sum', ni, ns);
    if (vi !== ni || vs !== ns) tally(brand, src, day, 'text', vi - ni, vs - ns);
    if (outcome !== 'counted') { tally(brand, src, day, outcome, vi, vs); return; }
    var ci = readsText ? vi : ni, cs = readsText ? vs : ns;
    if (ci !== vi || cs !== vs) tally(brand, src, day, 'textSkipped', vi - ci, vs - cs);
    var div = spendDiv || 1;
    if (div !== 1) tally(brand, src, day, 'fx', 0, cs - cs / div);
    tally(brand, src, day, 'counted', ci, cs / div);
  }

  var raw = [], dayset = {}, platset = {};
  function addRaw(line, brand, camp, day, m) {
    // [platform, brand, campaign, day, reach, impressions, spend, link clicks, clicks,
    //  views, installs, purchases, objective] — one entry per source row, never merged:
    // SUMIFS adds every row, so the dashboard does too.
    raw.push([line.plat, brand, _campIndex(camp), day].concat(m, [line.obj]));
    dayset[day] = 1; platset[line.plat] = 1;
  }

  /* ---- Raw data (rows 7-21, 23, 25): A platform, B portal as the source sets it, C campaign,
          D day, E reach, F impressions, G spend, H link clicks, I clicks, J views, K installs,
          L purchases, P objective (CFG.OBJECTIVE_COL), Q portal (CFG.PORTAL_COL) ---- */
  var rv = sourceValues(CFG.RAW, 'rows 7-21, 23 and 25', RAW_EXPECT);
  var rawHdr = rv[0] || [];
  var objIdx = _objectiveIndex_(rawHdr);
  var hasObjective = objIdx >= 0;
  if (!hasObjective && rv.length > 1) {
    issue('warn', 'Raw data has no Objective column (' + CFG.OBJECTIVE_COL + '), so this dashboard is splitting campaigns ' +
      'into lines itself while the pacing tab still uses its old wildcard sums. Run Qiddiya Setup → ' +
      'Fix this workbook once; after that both read the same column.');
  } else if (hasObjective && rv.length > 1 && !reads.objective) {
    issue('warn', 'The pacing tabs do not read Raw data\'s Objective column (' + CFG.OBJECTIVE_COL + ') — they hold ' +
      'formulas from before Fix this workbook (e.g. after Undo, or "Install the original doc formulas") — so they still ' +
      'use the old wildcard sums while this dashboard uses column ' + CFG.OBJECTIVE_COL + '. Run Qiddiya Setup → Repair ' +
      'Pacing_Daily formulas (or Fix this workbook) to make them agree.');
  }
  // the portal: column Q once Fix this workbook has added it (what the pacing formulas filter
  // on), otherwise the same rule worked out here
  var portalIdx = _portalIndex_(rawHdr), hasPortal = portalIdx >= 0;
  var tabsUseB = !reads.portal;
  if (reads.portal && !hasPortal) {
    issue('crit', 'The pacing formulas filter on Raw data column ' + CFG.PORTAL_COL + ' (Portal), but that column has ' +
      'no "Portal" header, so media rows 7-21, 23 and 25 count 0. Run Qiddiya Setup → Fix this workbook.');
  }
  if (reads.objective && !hasObjective) {
    issue('crit', 'The pacing formulas filter on Raw data column ' + CFG.OBJECTIVE_COL + ' (Objective), but that column ' +
      'has no "Objective" header, so media rows 7-21, 23 and 25 count 0. Run Qiddiya Setup → Fix this workbook.');
  }
  function rowPortal(r) { return hasPortal ? _brandCell(r[portalIdx]) : _rawPortal_(r[0], r[2], r[1]); }
  var unmapped = { spend: 0, names: {} }, offLine = {}, rawBadDates = 0, rawInWindow = 0, crossPortal = {};
  // what Raw data holds per platform | portal (column B) | day, to find Raw manual rows that never reached it
  var rawSeen = {}, rawLast = '';
  for (var i = 1; i < rv.length; i++) {
    var r = rv[i];
    if (r[0] === '' || r[0] === null) continue;
    var day = _dateCell(r[3], tz);
    // rows the dashboard cannot place are still tallied, so the check table's SUM() is the column's
    var rb0 = rowPortal(r);
    if (!day) { rawBadDates++; if (rb0) reconRow(rb0, 'raw', '', r[5], r[6], 'nodate'); continue; }
    var rsk = String(r[0]).toLowerCase() + '|' + _brandCell(r[1]) + '|' + day;
    rawSeen[rsk] = (rawSeen[rsk] || 0) + _valueNum(r[6]);
    rawLast = _later(rawLast, day);
    if (!inWindow(day)) { if (rb0) reconRow(rb0, 'raw', day, r[5], r[6], 'outside'); continue; }
    rawInWindow++;
    var plat = _canonPlat(r[0]);
    var camp = String(r[2] == null ? '' : r[2]);
    var brand = rb0;
    var spend = _cellNum(r[6]) / (plat === 'X' ? CFG.FX : 1);   // X is billed in SAR
    if (!brand) {
      unmapped.spend += spend;
      var un = String(r[0]) + ' · ' + camp;
      unmapped.names[un] = (unmapped.names[un] || 0) + spend;
      continue;
    }
    // Apple is row 22 (APPLE1) and InMobi is row 24 (Raw manual + backup) on the pacing
    // tab; their Raw data copies are never read there, so they are not read here either.
    if (plat === 'Apple' || plat === 'InMobi') {
      reconRow(brand, 'raw', day, r[5], r[6], plat === 'InMobi' ? 'inmobi_copy' : 'apple_copy');
      continue;
    }
    // the portal the name gives against the one column B (the source workbook's rule) gives
    var bPortal = _brandCell(r[1]);
    if (bPortal !== brand && (_cellNum(r[5]) || _cellNum(r[6]))) {
      var cpk = String(r[0]) + ' · ' + camp + ' — filed under ' + brand + ' by its name; column B says ' + (bPortal || 'nothing');
      crossPortal[cpk] = (crossPortal[cpk] || 0) + spend;
    }
    var obj = hasObjective ? String(r[objIdx] == null ? '' : r[objIdx]) : _objective(plat, camp);
    var line = plat ? LINE_BY_KEY[plat + '|' + obj] : null;
    if (!line || line.source) {
      var ok = String(r[0]) + ' / ' + obj + ' / ' + brand;
      offLine[ok] = (offLine[ok] || 0) + spend;
      reconRow(brand, 'raw', day, r[5], r[6], 'offline');
      continue;
    }
    var floor = _mediaFloor(line, brand);
    if (floor && day < floor) { reconRow(brand, 'raw', day, r[5], r[6], 'prefloor'); continue; }
    timed(r[3], day);
    reconRow(brand, 'raw', day, r[5], r[6], 'counted', false, plat === 'X' ? CFG.FX : 1);
    // X reports nothing in "Clicks (all)" — its pacing rows read link clicks (I9=J9, I20=J20).
    // Google "Conversions" fill both K and L; on app-install (UAC) rows they are the installs,
    // so they are not purchases (pacing N of the Google rows leaves out rows with K > 0).
    addRaw(line, brand, camp, day,
      [_cellNum(r[4]), _cellNum(r[5]), spend, _cellNum(r[7]),
       plat === 'X' ? _cellNum(r[7]) : _cellNum(r[8]),
       _cellNum(r[9]), _cellNum(r[10]),
       plat === 'Google' && _cellNum(r[10]) > 0 ? 0 : _cellNum(r[11])]);
  }
  // Raw data's own window ends at O2 ("Till", the source's report window, imported with A:O),
  // else on its last day: Raw manual rows after that are outside it, not missing from it
  var rawTill = (String(rawHdr[14] == null ? '' : rawHdr[14]).trim() === 'Till' && rv[1] && _dateCell(rv[1][14], tz)) || rawLast;
  var rawFrom = String(rawHdr[13] == null ? '' : rawHdr[13]).trim() === 'From' && rv[1] && _dateCell(rv[1][13], tz) || '';
  if (unmapped.spend > 0.5) {
    var top = Object.keys(unmapped.names).sort(function (a, b) {
      return unmapped.names[b] - unmapped.names[a];
    }).slice(0, 5);
    issue('crit', money(unmapped.spend) + ' of Raw data spend in the window has no portal: neither the campaign name ' +
      '(SFQC, Six Flags, AAQC, AQQC, AQC-, Aquarabia; on Snapchat also First Story) nor column B names SFQC or AAQC' + (hasPortal ? ' (column ' +
      CFG.PORTAL_COL + ' shows UNMAPPED)' : '') + ', so no pacing row and no dashboard line counts it. Largest: ' +
      top.join('; ') + '. Rename the campaign so its name carries its portal.');
  }
  Object.keys(offLine).forEach(function (k) {
    if (offLine[k] > 0.5) {
      issue('crit', money(offLine[k]) + ' of Raw data spend is on "' + k + '", which has no row on the ' +
        'pacing tab. Add a row for it, or fix the platform name in Raw manual.');
    }
  });
  if (rawBadDates) {
    issue('warn', count(rawBadDates) + ' Raw data rows have a Day that is not a date; SUMIFS skips them.');
  }
  var crossKeys = Object.keys(crossPortal).sort(function (a, b) { return crossPortal[b] - crossPortal[a]; });
  if (crossKeys.length) {
    var crossSpend = crossKeys.reduce(function (t, k) { return t + crossPortal[k]; }, 0);
    var crossList = crossKeys.slice(0, 3).map(function (k) { return k + ' (' + money(crossPortal[k]) + ')'; }).join('; ') +
      (crossKeys.length > 3 ? '; …' : '');
    var bRule = 'Column B comes from the source workbook, whose Raw data files every name that does not start ' +
      'with "SFQC" under AAQC.';
    if (tabsUseB && crossSpend > 0.5) {
      issue('crit', money(crossSpend) + ' of Raw data spend is on ' + crossKeys.length + ' campaign(s) whose name carries ' +
        'another portal than column B: ' + crossList + '. ' + bRule + ' This dashboard files them by their name; the ' +
        'pacing tabs ' + (hasPortal ? 'hold formulas that still filter on column B (from before Fix this workbook, e.g. ' +
        'after Undo)' : 'still filter on column B, because Raw data has no Portal column (' + CFG.PORTAL_COL + ') yet') +
        ', so they count this spend under the other portal. Run Qiddiya Setup → Fix this workbook: it adds column ' +
        CFG.PORTAL_COL + ' and points the pacing formulas at it.');
    } else {
      issue('warn', crossKeys.length + ' campaign(s) are filed under the portal their name carries, not the one in ' +
        'column B: ' + crossList + '. ' + bRule + ' ' + (tabsUseB ? 'The pacing tabs still filter on column B; ' +
        'Qiddiya Setup → Fix this workbook points them at column ' + CFG.PORTAL_COL + '.' : 'Column ' + CFG.PORTAL_COL +
        ' (Portal) applies the same rule, so the pacing tabs and this dashboard agree.') + ' If a campaign really ' +
        'belongs to the other portal, rename it so its name carries that portal ("SFQC-…" / "AQC-…").');
    }
  }

  /* ---- Apple Ads (row 22) — APPLE1 by position: A date, B app, D spend, E impressions,
          F taps (clicks and link clicks), G installs. No views, no purchases. ---- */
  var appleLine = LINE_BY_KEY['Apple|Conversion'];
  var apv = sourceValues(CFG.APPLE, 'row 22', APPLE_EXPECT);
  var apHdr = apv[0] || [];
  var appleCampCol = _col(apHdr, 'Campaign Name') - 1;
  if (appleCampCol < 0) appleCampCol = 2;
  for (var ai = 1; ai < apv.length; ai++) {
    var ar = apv[ai];
    var appleBrand = _matchBrand(CFG.APPLE_APP, ar[1]);
    if (!appleBrand) continue;
    var appleDay = _dateCell(ar[0], tz);
    if (!inWindow(appleDay)) { reconRow(appleBrand, 'apple', appleDay || '', ar[4], ar[3], appleDay ? 'outside' : 'nodate'); continue; }
    if (appleDay < _mediaFloor(appleLine, appleBrand)) {
      reconRow(appleBrand, 'apple', appleDay, ar[4], ar[3], 'prefloor');
      continue;
    }
    timed(ar[0], appleDay);
    reconRow(appleBrand, 'apple', appleDay, ar[4], ar[3], 'counted');
    var taps = _cellNum(ar[5]);
    addRaw(appleLine, appleBrand, String(ar[appleCampCol] == null ? '' : ar[appleCampCol]), appleDay,
      [0, _cellNum(ar[4]), _cellNum(ar[3]), taps, taps, 0, _cellNum(ar[6]), 0]);
  }

  /* ---- InMobi (row 24): Raw manual from CFG.INMOBI_MANUAL_FROM, the Raw data backup from
          2 Jul to CFG.INMOBI_BACKUP_TILL, rows 2-10000, numbers parsed with VALUE(), exactly
          as the row's SUMPRODUCTs ---- */
  var inmobiLine = LINE_BY_KEY['InMobi|Conversion'];
  var manualOther = [];
  function readInMobi(sheetName, lo, hi, src) {
    var sh = ss.getSheetByName(sheetName);
    if (!sh) {
      issue('crit', 'Tab "' + sheetName + '" is missing — pacing row 24 (InMobi) reads it.');
      return;
    }
    var v = sourceValues(sheetName, 'row 24 (InMobi)', RAW_EXPECT);
    var last = Math.min(v.length, CFG.INMOBI_LAST_ROW);
    for (var mi = 1; mi < last; mi++) {
      var mr = v[mi];
      var mb = _brandCell(mr[1]), md = _dateCell(mr[3], tz);
      if (!mb) continue;
      if (!inWindow(md)) {
        if (src === 'manual' || String(mr[0] == null ? '' : mr[0]).toLowerCase() === 'inmobi') {
          reconRow(mb, src, md || '', mr[5], mr[6], md ? 'outside' : 'nodate');
        }
        continue;
      }
      if (String(mr[0] == null ? '' : mr[0]).toLowerCase() !== 'inmobi') {
        // Raw manual's other rows (Bidease, InMotion) count through their copies in Raw data, which
        // rows 23/25 read — whether each one reached Raw data is checked below; the backup's
        // other rows are an old copy of Raw data and are not shown at all.
        if (src === 'manual') manualOther.push({ b: mb, d: md, row: mi + 1, r: mr });
        continue;
      }
      var lower = _later(from, lo), upper = _sooner(loadTill, hi);
      if ((lower && md < lower) || (upper && md > upper)) {
        reconRow(mb, src, md, mr[5], mr[6], 'inmobi_out');
        continue;
      }
      timed(mr[3], md);
      reconRow(mb, src, md, mr[5], mr[6], 'counted', true);
      addRaw(inmobiLine, mb, String(mr[2] == null ? '' : mr[2]), md,
        [_valueNum(mr[4]), _valueNum(mr[5]), _valueNum(mr[6]), _valueNum(mr[7]),
         _valueNum(mr[8]), _valueNum(mr[9]), _valueNum(mr[10]), _valueNum(mr[11])]);
    }
    if (v.length > CFG.INMOBI_LAST_ROW) {
      issue('warn', sheetName + ' has rows below row 10,000; pacing row 24 stops reading there.');
    }
  }
  readInMobi(CFG.RAW_MANUAL, CFG.INMOBI_MANUAL_FROM, '', 'manual');
  readInMobi(CFG.RAW_BACKUP, FLOOR_JUL2, CFG.INMOBI_BACKUP_TILL, 'backup');
  // A Raw manual Bidease / InMotion row counts only if Raw data copied it. The source workbook's
  // Raw data reads Raw manual from row 50 down ('Raw manual'!$A$50:$L), and that start moves down
  // whenever rows are inserted above it, so a row typed higher up never reaches Raw data. Compared
  // per platform + portal + day (Raw data keeps the unrounded spend, hence the tolerance); days
  // after Raw data's own window (O2) are outside it, not missing.
  var mGroups = {}, missing = [], missingSpend = 0;
  manualOther.forEach(function (m) {
    var k = String(m.r[0]).toLowerCase() + '|' + m.b + '|' + m.d;
    (mGroups[k] = mGroups[k] || []).push(m);
  });
  Object.keys(mGroups).forEach(function (k) {
    var g = mGroups[k], want = 0, have = rawSeen[k];
    g.forEach(function (m) { want += _valueNum(m.r[6]); });
    var there = (rawTill && g[0].d > rawTill) || (rawFrom && g[0].d < rawFrom) ||
      (have != null && have + 0.01 >= want * 0.995);
    g.forEach(function (m) {
      reconRow(m.b, 'manual', m.d, m.r[5], m.r[6], there ? 'not_inmobi' : 'manual_missing');
      if (!there) { missing.push(m); missingSpend += _valueNum(m.r[6]); }
    });
  });
  if (missing.length) {
    missing.sort(function (a, b) { return a.row - b.row; });
    issue('crit', count(missing.length) + ' Raw manual row(s) are not in Raw data (' + missing.slice(0, 5).map(function (m) {
      return 'row ' + m.row + ': ' + m.r[0] + ' ' + m.b + ' ' + m.d;
    }).join('; ') + (missing.length > 5 ? '; …' : '') + ', ' + money(missingSpend) + '), so pacing rows 23/25, row 28 and ' +
      'this dashboard do not count them. The source workbook\'s Raw data reads Raw manual only from row 50 down ' +
      '(\'Raw manual\'!$A$50:$L), and that start moves down whenever rows are inserted above it. In the source ' +
      'workbook, move these rows to row 50 or below (inside or under the existing Bidease rows) — or change both ' +
      '\'Raw manual\'!$A$50 references in its Raw data!A2 to $A$2, after checking that the source\'s own report does ' +
      'not then count the InMobi rows above row 50 twice.');
  }

  /* ---- Adjust Raw (columns K, L, X): by position, like the formulas — A day, D app,
          E revenue, G paid installs, H installs, I bookings, J channel, K objective.
          The exception to "fix it in the source": the dashboard reads Adjust Raw through the
          corrections "Adjust Clean" holds (dates, duplicate and mislabelled imports, channel
          labels), the copy the pacing formulas read; what it changed is in the banner. ---- */
  // the pacing formulas read "Adjust Clean" once Fix this workbook has pointed them at it — decided
  // from their formulas, not from whether the tab exists (Undo, "Install the original doc formulas"
  // or "Clean Adjust Raw" before Fix leave the tab beside formulas that read Adjust Raw). asTab
  // reads what they read; the dashboard itself reads Adjust Raw through the same corrections.
  var adjCleanSh = ss.getSheetByName(CFG.ADJUST_CLEAN), ash = null;
  var tabsClean = !!adjCleanSh && reads.clean;
  try { ash = asTab && tabsClean ? adjCleanSh : _sheet(CFG.ADJUST); } catch (eA) {
    issue('crit', 'Tab "' + CFG.ADJUST + '" is missing (renamed or deleted) — pacing columns K, L and X read it ' +
      'through "' + CFG.ADJUST_CLEAN + '", and this dashboard has no Adjust installs, bookings or revenue.');
  }
  var av = ash ? ash.getDataRange().getValues() : [[]];
  var cleanState = '', cleanErr = '';
  // The cleaning runs on every dashboard load and refresh: "Adjust Clean" is built the first
  // time and rebuilt whenever Adjust Raw (or the day) has changed since the last build —
  // whether or not the pacing tabs read it yet (they do once Fix this workbook has run).
  if (!asTab && ash && (!adjCleanSh ||
      PropertiesService.getDocumentProperties().getProperty('adjustCleanFp') !== _adjustFingerprint_(av, ss))) {
    try {
      var rr = _refreshAdjustClean_(!adjCleanSh);
      cleanState = rr.busy ? 'stale' : rr.rebuilt ? 'rebuilt' : '';
      if (rr.rebuilt && !adjCleanSh) { adjCleanSh = ss.getSheetByName(CFG.ADJUST_CLEAN); tabsClean = !!adjCleanSh && reads.clean; }
    } catch (eRb) { cleanState = 'stale'; cleanErr = String(eRb && eRb.message || eRb); }
  }
  if (ash) {
    _headerProblems(av[0] || [], ADJUST_EXPECT, CFG.ADJUST).forEach(function (p) {
      issue('crit', p + ' — the pacing formulas read Adjust Raw by position.');
    });
  }
  var swapWin = _adjustSwapWindow_(ss, tz), todayIso = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');
  var reversed = _adjustReversedRows(av, 0, tz, swapWin);
  var swappedRows = Object.keys(reversed).filter(function (j) {
    return _matchBrand(CFG.ADJUST_APP, av[j][3]);
  }).length;
  var aAgg = {}, seenKeys = {}, channelsSeen = {};
  function addAdjust(agg, appBrand, lineKey, channel, d, camp, revenue, paidInst, inst, bookings) {
    var ci = _campIndex(String(camp == null ? '' : camp));
    var channelName = String(channel == null ? '' : channel) || '(blank)';
    var ak = [appBrand, lineKey, channelName, d, ci].join('\u0001');
    var e = agg[ak] || (agg[ak] = { brand: appBrand, line: lineKey, channel: channelName,
      day: d, ci: ci, revenue: 0, paidInst: 0, inst: 0, bookings: 0 });
    e.revenue += revenue; e.paidInst += paidInst; e.inst += inst; e.bookings += bookings;
  }
  var adjustDataRows = 0, textDates = 0, dupRows = 0, textNums = 0, blankChannel = 0;
  for (var j = 1; j < av.length; j++) {
    var a = av[j];
    if (a[0] === '' || a[0] === null) continue;
    adjustDataRows++;
    var appBrand = _matchBrand(CFG.ADJUST_APP, a[3]);
    if (!appBrand) continue;
    var d = _dateCell(a[0], tz);
    var lineKey = _adjustLine(a[9], a[10]);
    if (!lineKey) continue;                                  // Organic
    if (!d) { textDates++; continue; }
    var dupKey = JSON.stringify([d, String(a[3]).toLowerCase(), String(a[1]), String(a[2])]);
    if (seenKeys[dupKey]) dupRows++; else seenKeys[dupKey] = 1;
    channelsSeen[appBrand + '|' + lineKey.split('|')[0]] = 1;
    if (a[9] === '' || a[9] === null) blankChannel++;
    if (!inWindow(d)) continue;
    var aLine = LINE_BY_KEY[lineKey];
    var aFloor = _adjustFloor(aLine);
    if (aFloor && d < aFloor) continue;
    if (_isTextNum(a[4]) || _isTextNum(a[6]) || _isTextNum(a[7]) || _isTextNum(a[8])) textNums++;
    addAdjust(aAgg, appBrand, lineKey, a[9], d, a[2], _cellNum(a[4]), _cellNum(a[6]), _cellNum(a[7]), _cellNum(a[8]));
  }
  var legacy = ss.getSheetByName(CFG.ADJUST_LEGACY);
  var legacyRows = legacy && legacy.getLastRow() > 1 ? legacy.getLastRow() - 1 : 0;

  /* Text dates, day/month swaps, overlapping imports, text numbers, blank or mislabelled
     channels: the dashboard reads Adjust Raw through the same corrections "Adjust Clean"
     holds, so its installs, bookings and revenue are right even before Fix this workbook has
     pointed the pacing formulas at "Adjust Clean". Until then the tabs read Adjust Raw as it
     stands — the banner says by how much. */
  var tabAgg = aAgg, cleanLog = null, adjRecon = {}, futureRows = 0;
  // the "Check it against the tabs" table: every Adjust Raw row by what happens to it
  function adjTally(b, d, k, v) {
    var key = b + '|' + d + '|' + k;
    var e = adjRecon[key] || (adjRecon[key] = { b: b, d: d, k: k, i: 0, o: 0, r: 0, n: 0 });
    e.i += _cellNum(v[7]); e.o += _cellNum(v[8]); e.r += _cellNum(v[4]); e.n++;
  }
  if (!asTab && ash) {
    try {
      cleanLog = [];
      var cd = _adjustCleanData_(ss, ash, tz, cleanLog);
      aAgg = {};
      (cd.data.removed || []).forEach(function (row) {
        var rb = _matchBrand(CFG.ADJUST_APP, row.v[3]);
        if (!rb) return;
        adjTally(rb, row.day, 'sum', row.v);
        adjTally(rb, row.day, 'dup', row.v);
      });
      cd.data.rows.forEach(function (row) {
        var v = row.v, cdDay = row.day;
        var cBrand = _matchBrand(CFG.ADJUST_APP, v[3]);
        if (!cBrand) return;
        adjTally(cBrand, cdDay, 'sum', v);
        if (!cdDay) { adjTally(cBrand, cdDay, 'nodate', v); return; }
        if (cdDay > todayIso) futureRows++;
        var cLine = _adjustLine(v[9], v[10]);
        if (!cLine) { adjTally(cBrand, cdDay, 'organic', v); return; }
        channelsSeen[cBrand + '|' + cLine.split('|')[0]] = 1;
        if (!inWindow(cdDay)) { adjTally(cBrand, cdDay, 'outside', v); return; }
        var cFloor = _adjustFloor(LINE_BY_KEY[cLine]);
        if (cFloor && cdDay < cFloor) { adjTally(cBrand, cdDay, 'prefloor', v); return; }
        if (row.dateFixed) adjTally(cBrand, cdDay, 'dateFixed', v);
        adjTally(cBrand, cdDay, 'counted', v);
        addAdjust(aAgg, cBrand, cLine, v[9], cdDay, v[2], _cellNum(v[4]), _cellNum(v[6]), _cellNum(v[7]), _cellNum(v[8]));
      });
    } catch (err) {
      aAgg = tabAgg; cleanLog = null; adjRecon = {};
      issue('warn', 'Adjust Raw could not be corrected while reading it (' + err.message + '), so its ' +
        'figures are shown as the tab stands.');
    }
  }
  var adjust = Object.keys(aAgg).map(function (k) {
    var e = aAgg[k];
    e.revenue = Math.round(e.revenue * 100) / 100;
    return e;
  });
  var fixHint = ' Run Qiddiya Setup → Fix this workbook (once; later Pacing dashboard → Clean Adjust Raw): the ' +
    'pacing formulas then read the corrected copy "' + CFG.ADJUST_CLEAN + '". Adjust Raw itself is not changed.';
  var needsClean = cleanLog && cleanLog.some(function (r) {
    return /Text date|swap|Duplicate|Cross-app|Number stored as text|moved from|Missing channel|replaced|folded/.test(r[1]);
  });
  if (needsClean) {
    var kinds = {};
    cleanLog.forEach(function (r) {
      var k = /Text date/.test(r[1]) ? 'text' : /swap/.test(r[1]) ? 'swap' : /Duplicate/.test(r[1]) ? 'dup'
        : /Cross-app/.test(r[1]) ? 'xapp'
        : /Number stored as text/.test(r[1]) ? 'num' : /moved from|Missing channel/.test(r[1]) ? 'label'
        : /replaced|folded/.test(r[1]) ? 'legacy' : '';
      if (k) kinds[k] = (kinds[k] || 0) + 1;
    });
    var parts = [];
    if (kinds.text) parts.push(count(kinds.text) + ' rows with a text date (e.g. 13/09/2026)');
    if (kinds.swap) parts.push(count(kinds.swap) + ' day/month-swapped dates');
    if (kinds.xapp) parts.push(count(cd.xapp) + ' rows pasted a second time under the wrong app');
    if (kinds.dup) parts.push(count(kinds.dup) + ' rows repeated by overlapping imports');
    if (kinds.num) parts.push(count(kinds.num) + ' numbers stored as text');
    if (kinds.label) parts.push(count(kinds.label) + ' rows with a missing or wrong channel');
    if (legacyRows) parts.push(count(legacyRows) + ' rows still in "' + CFG.ADJUST_LEGACY + '"');
    // Adjust Raw as it stands against the corrected figures, both counted with the line rules
    // Fix this workbook installs over SFQC's dates — not what the old formulas on the tabs show
    var cmp = [];
    ['SFQC', 'AAQC'].forEach(function (b) {
      var t = { inst: 0, book: 0 }, c = { inst: 0, book: 0 };
      [[tabAgg, t], [aAgg, c]].forEach(function (pair) {
        Object.keys(pair[0]).forEach(function (k) {
          var e = pair[0][k];
          if (e.brand !== b || (from && e.day < from) || (till && e.day > till)) return;
          pair[1].inst += e.inst; pair[1].book += e.bookings;
        });
      });
      if (Math.round(t.inst) !== Math.round(c.inst) || Math.round(t.book) !== Math.round(c.book)) {
        cmp.push(b + ' ' + count(Math.round(t.inst)) + ' installs / ' + count(Math.round(t.book)) +
          ' bookings instead of ' + count(Math.round(c.inst)) + ' / ' + count(Math.round(c.book)));
      }
    });
    if (tabsClean) {
      issue('warn', 'Adjust Raw has ' + parts.join(', ') + '. They are corrected in "' + CFG.ADJUST_CLEAN +
        '", which both the pacing tabs and this dashboard read. Fix the exports at the source when you can.');
    } else {
      issue('crit', 'Adjust Raw has ' + parts.join(', ') + '. This dashboard corrects them as it reads ' +
        'the tab, so the Adjust installs, bookings and revenue shown here are right. The pacing tabs still ' +
        'read the tab as it stands' + (adjCleanSh ? ' ("' + CFG.ADJUST_CLEAN + '" exists, but the pacing formulas ' +
        'do not read it: they were restored by Undo or "Install the original doc formulas", or edited by hand)' : '') +
        (cmp.length ? ' — counted that way, with the line rules Fix this workbook installs, it gives ' +
        cmp.join('; ') + ' for ' + from + ' → ' + till : '') + '. Run Qiddiya Setup → Fix this workbook (or Repair ' +
        'Pacing_Daily formulas): the tabs then read the corrected copy.');
    }
  } else if (textDates && !cleanLog) {
    issue('crit', count(textDates) + ' Adjust Raw rows hold their day as text (e.g. 13/09/2026). ' +
      'SUMIFS cannot read a text date, so neither the pacing tab nor this dashboard counts their ' +
      'installs, bookings or revenue.' + fixHint);
  }
  // Adjust Clean behind Adjust Raw: the pacing tabs (K, L, X, C42-C44) show the previous build
  if (cleanState === 'stale') {
    issue('crit', '"' + CFG.ADJUST_CLEAN + '" was built at ' +
      (PropertiesService.getDocumentProperties().getProperty('adjustCleanAt') || 'an earlier run') +
      ' from an older Adjust Raw and could not be rebuilt just now' + (cleanErr ? ' (' + cleanErr + ')' : ' (another ' +
      'run was rebuilding it)') + ': pacing columns K, L and X and C42-C44 still show the previous Adjust figures, ' +
      'while this dashboard shows Adjust Raw as it is now. Press Refresh in a minute, or run Pacing dashboard → ' +
      'Clean Adjust Raw.');
  } else if (tabsClean && !asTab && cd && adjCleanSh) {
    // a rebuild that failed half-way (Adjust Clean cleared, the rows never written) leaves it short
    var have = Math.max(0, adjCleanSh.getLastRow() - 1);
    var want = cd.data.rows.filter(function (row) { return !_adjustLeftOut_(row, { from: from, till: loadTill }); }).length;
    if (have < want) {
      issue('crit', '"' + CFG.ADJUST_CLEAN + '" holds ' + count(have) + ' rows where Adjust Raw gives ' + count(want) +
        ' (its last rebuild did not finish), so pacing columns K, L and X and row 28 are understated. Run ' +
        'Pacing dashboard → Clean Adjust Raw.');
    }
  }
  var unreadable = cleanLog ? cleanLog.filter(function (r) { return /not readable/.test(r[1]); }) : [];
  if (unreadable.length) {
    issue('crit', count(unreadable.length) + ' Adjust Raw rows have a day that is not a date (row ' +
      unreadable.slice(0, 5).map(function (r) { return r[0]; }).join(', ') + (unreadable.length > 5 ? ' …' : '') +
      ', e.g. "' + unreadable[0][2] + '"), so neither the pacing tabs nor this dashboard count their installs, ' +
      'bookings or revenue. Correct the day in the source.');
  }
  if (futureRows) {
    issue('warn', count(futureRows) + ' Adjust Raw rows are dated after today — most likely a dd/MM paste that ' +
      'Sheets read the other way round. Neither the pacing tabs nor this dashboard count them; correct the day ' +
      'in the source.');
  }
  if (swappedRows && !needsClean) {
    issue('crit', count(swappedRows) + ' Adjust Raw dates look day/month-swapped by Sheets ' +
      '(01/09 stored as 9 January). Those rows are counted on the wrong day — usually outside the ' +
      'window, i.e. not at all.' + fixHint);
  }
  if (dupRows && !needsClean) {
    issue('crit', count(dupRows) + ' Adjust Raw rows repeat a day + app + network + campaign that is ' +
      'already in the tab (overlapping imports), so the pacing tab and this dashboard add them twice.' +
      fixHint);
  }
  if (textNums && !needsClean) {
    issue('warn', count(textNums) + ' Adjust Raw rows in the window have a number stored as text; ' +
      'SUMIFS counts those cells as 0.' + fixHint);
  }
  if (blankChannel && !needsClean) {
    issue('warn', count(blankChannel) + ' Adjust Raw rows have no channel (column J); they are ' +
      'counted on the Other row.' + fixHint);
  }
  if (adjustDataRows === 5000) {
    issue('crit', 'Adjust Raw has exactly 5,000 data rows — the size at which an Adjust export ' +
      'truncates. Re-export the period in smaller date batches and import them.');
  }
  if (legacyRows && !needsClean) {
    issue('warn', '"' + CFG.ADJUST_LEGACY + '" still holds ' + count(legacy.getLastRow() - 1) +
      ' imported rows that neither the pacing tab nor this dashboard reads.' + fixHint);
  }

  /* ---- GA4 (column M): by position — B property, C date, D campaign, E channel group,
          F source / medium, G transactions, H revenue. A bucket whose row has a date floor
          (Google Search, Meta) counts from that floor, like the row's media and Adjust cells;
          paid sales before it (an earlier flight) are on no row and go to ga4PreFloor, which
          only the GA4 paid total (C49) includes. ---- */
  var gv = sourceValues(CFG.GA4, 'column M (and X on the web rows)', GA4_EXPECT);
  var gMap = {}, gPreMap = {};
  for (var k = 1; k < gv.length; k++) {
    var g = gv[k];
    var gBrand = _ga4Brand(g[1]);
    if (!gBrand) continue;
    if (CFG.PAID_GROUPS.indexOf(String(g[4] == null ? '' : g[4]).toLowerCase()) < 0) continue;
    var gd = _dateCell(g[2], tz);
    if (!inWindow(gd)) continue;
    timed(g[2], gd);
    var bucket = _ga4Bucket(g[5], g[3]);
    var gFloor = _mediaFloor(LINE_BY_KEY[GA4_LINE[bucket]], gBrand);
    var gTarget = gFloor && gd < gFloor ? gPreMap : gMap;
    var gci = _campIndex(g[3]);
    var gk = [gBrand, bucket, gd, gci].join('\u0001');
    var ge = gTarget[gk] || (gTarget[gk] = { brand: gBrand, bucket: bucket, line: GA4_LINE[bucket],
      day: gd, ci: gci, tx: 0, revenue: 0 });
    ge.tx += _cellNum(g[6]);
    ge.revenue += _cellNum(g[7]);
  }
  function ga4List(map) {
    return Object.keys(map).map(function (key) {
      var e = map[key];
      e.revenue = Math.round(e.revenue * 100) / 100;
      return e;
    });
  }
  var ga4 = ga4List(gMap), ga4PreFloor = ga4List(gPreMap);

  if (!rawInWindow && (adjust.length || ga4.length)) {
    issue('crit', 'Raw data has no rows in the window while Adjust and GA4 do — its import is probably broken ' +
      'or still loading, so every media row (spend, impressions, clicks) shows 0. Open Raw data and check it.');
  }
  if (timedOnTill) {
    issue('warn', count(timedOnTill) + ' source rows dated ' + till + ' (SFQC C2) carry a time of day. The pacing ' +
      'tabs count up to ' + till + ' 00:00 and leave them out; this dashboard counts the whole day.');
  }

  /* ---- lines that spend but whose channel never appears in Adjust Raw at all ---- */
  var noAdjustFeed = {};
  raw.forEach(function (row) {
    if (row[6] > 0 && !channelsSeen[row[1] + '|' + row[0]]) noAdjustFeed[row[1] + '|' + row[0]] = 1;
  });

  /* ---- and the reverse: Adjust installs on days a line has no spend row (a spend paste that is
          missing). Only days up to the line's last spend day, with 10+ installs, so lagged
          bookings and a source that is simply a day behind do not count. Nothing is dropped:
          CPI and ROAS of the line are overstated until those days are pasted. ---- */
  var mediaDays = {}, mediaLast = {};
  raw.forEach(function (row) {
    var mk = row[1] + '|' + row[0] + '|' + row[12];
    (mediaDays[mk] = mediaDays[mk] || {})[row[3]] = 1;
    mediaLast[mk] = _later(mediaLast[mk] || '', row[3]);
  });
  var gapDays = {};
  adjust.forEach(function (e) {
    var gl = LINE_BY_KEY[e.line], gk2 = e.brand + '|' + e.line;
    if (!gl || gl.source === 'none' || !mediaLast[gk2] || e.day > mediaLast[gk2]) return;
    if (e.day < _mediaFloor(gl, e.brand) || mediaDays[gk2][e.day]) return;
    var x = ((gapDays[gk2] = gapDays[gk2] || {})[e.day] = gapDays[gk2][e.day] || { inst: 0, book: 0, rev: 0 });
    x.inst += e.inst; x.book += e.bookings; x.rev += e.revenue;
  });
  var spendGaps = {};
  // where the missing spend goes: Raw manual (InMobi; Bidease and InMotion through Raw data) — in the
  // SOURCE workbook when this file's copy is an IMPORTRANGE, since typing into an import breaks it
  var manualF = '', rawF = '';
  try { manualF = _formulaTab_(ss.getSheetByName(CFG.RAW_MANUAL)); } catch (eM) {}
  try { rawF = _formulaTab_(ss.getSheetByName(CFG.RAW)); } catch (eR) {}
  function pasteWhere(gl) {
    if (gl.source === 'InMobi') {
      return /IMPORTRANGE/i.test(manualF) ? ' (InMobi: into Raw manual in the SOURCE workbook — this file\'s Raw manual ' +
        'is an IMPORTRANGE of it, and typing rows here breaks the import)' : ' (InMobi: into Raw manual)';
    }
    if (gl.plat === 'Bidease' || gl.plat === 'InMotion') {
      return /IMPORTRANGE/i.test(rawF) ? ' (' + gl.plat + ': into Raw manual in the SOURCE workbook, at row 50 or below, ' +
        'which its Raw data copies — never into this file\'s imported tabs)' : rawF ? ' (' + gl.plat + ': into Raw manual, ' +
        'which Raw data copies)' : ' (' + gl.plat + ': into Raw data)';
    }
    return '';
  }
  Object.keys(gapDays).sort().forEach(function (gk2) {
    var ds = Object.keys(gapDays[gk2]).filter(function (d) { return gapDays[gk2][d].inst >= 10; }).sort();
    if (!ds.length) return;
    var t = { inst: 0, book: 0, rev: 0 };
    ds.forEach(function (d) { var x = gapDays[gk2][d]; t.inst += x.inst; t.book += x.book; t.rev += x.rev; });
    var gp = gk2.split('|'), gl = LINE_BY_KEY[gp[1] + '|' + gp[2]];
    spendGaps[gk2] = { days: ds, inst: t.inst, bookings: t.book, revenue: Math.round(t.rev * 100) / 100 };
    issue('warn', gl.label + ' ' + gp[0] + ': ' + count(Math.round(t.inst)) + ' Adjust installs, ' +
      count(Math.round(t.book)) + ' bookings and ' + count(Math.round(t.rev)) + ' SAR on ' + ds.length +
      ' day(s) between ' + ds[0] + ' and ' + ds[ds.length - 1] + ' that have no spend row. They are counted, ' +
      'so the CPI, CPA and ROAS of pacing row ' + gl.row + ' are overstated until the spend for those days is ' +
      'pasted' + pasteWhere(gl) + '.');
  });

  // Source freshness is not the same thing as arithmetic reconciliation. Keep
  // the actual first/last row dates in the payload so the UI can say, for
  // example, that media and Adjust reach 30 Sep while GA4 reaches 29 Sep.
  var mediaCoverage = {}, adjustCoverage = {}, ga4Coverage = {};
  raw.forEach(function (row) {
    _touchCoverage(mediaCoverage, row[1] + '|' + row[0] + '|' + row[12], row[3],
      { brand: row[1], platform: row[0], objective: row[12] });
  });
  adjust.forEach(function (e) {
    var p = e.line.split('|');
    _touchCoverage(adjustCoverage, e.brand + '|' + e.line, e.day,
      { brand: e.brand, platform: p[0], objective: p[1] });
  });
  ga4.forEach(function (e) {
    var p = e.line.split('|');
    _touchCoverage(ga4Coverage, e.brand + '|' + e.line, e.day,
      { brand: e.brand, platform: p[0], objective: p[1], bucket: e.bucket });
  });

  // The picker and 7d/14d presets must use calendar days, not only days that had
  // media spend. Otherwise no-spend dates disappear and Adjust/GA4-only activity
  // shifts into the wrong period.
  var lastData = '';
  Object.keys(dayset).forEach(function (d) { lastData = _later(lastData, d); });
  adjust.forEach(function (e) { lastData = _later(lastData, e.day); });
  ga4.forEach(function (e) { lastData = _later(lastData, e.day); });
  var end = _later(till, lastData);
  if (till && end > till) {
    issue('warn', 'The pacing tabs stop at ' + till + ' (SFQC Pacing_Daily C2) but the data runs to ' +
      end + '. "All" shows everything; "Tab period" shows exactly what the tabs count. To extend ' +
      'the tabs, type a later date into SFQC C2 (the first run of Qiddiya Setup → Fix this workbook sets ' +
      'it to =TODAY()-1).');
  }
  if (from && end && end < from) {
    issue('warn', 'SFQC Pacing_Daily B2 (' + from + ') is after C2 (' + till + ') — the period has not started yet, ' +
      'so there is nothing to show.');
    end = from;
  }
  var days = _dateSpine(from, end);
  if (!days.length) days = Object.keys(dayset).sort();
  return {
    meta: {
      start: from || days[0], end: end || days[days.length - 1], days: days,
      // what the pacing tabs count (B2:C2); the dashboard's "Tab period" button
      report: { start: from || days[0], end: till || end || days[days.length - 1] },
      plats: Object.keys(platset).sort(), fx: CFG.FX,
      lines: PACING_LINES.map(function (l) {
        return { row: l.row, key: l.key, plat: l.plat, obj: l.obj, label: l.label,
          web: !!l.web, media: l.source !== 'none' };
      }),
      webRevenueFromGa4: !!CFG.WEB_REVENUE_FROM_GA4,
      // what the pacing formulas read, from their formulas: Adjust Clean (else Adjust Raw as it
      // stands), Raw data's Objective column and its Portal column (else column B)
      tabsReadClean: tabsClean, tabsReadObjective: reads.objective, tabsReadPortal: reads.portal,
      portalColumn: hasPortal,
      objectiveTokens: OBJECTIVE_TOKENS,          // the page spells the line rules from these
      health: { issues: issues, noAdjustFeed: Object.keys(noAdjustFeed).sort(), spendGaps: spendGaps },
      sourceCoverage: {
        media: _coverageValues(mediaCoverage),
        adjust: _coverageValues(adjustCoverage),
        ga4: _coverageValues(ga4Coverage)
      },
      generated: 'Refreshed ' + Utilities.formatDate(new Date(), CFG.TZ, 'yyyy-MM-dd HH:mm')
    },
    raw: raw, adjust: adjust, ga4: ga4, ga4PreFloor: ga4PreFloor, camps: _campList,
    reconAdjust: Object.keys(adjRecon).map(function (k) {
      var e = adjRecon[k];
      e.r = Math.round(e.r * 100) / 100;
      return e;
    }),
    recon: Object.keys(reconMap).map(function (k) {
      var e = reconMap[k];
      e.i = Math.round(e.i * 100) / 100; e.p = Math.round(e.p * 100) / 100;
      return e;
    })
  };
}

/* ------------------------------------------------------------------ validation */

/** Payload -> per-line totals for one portal, in pacing-tab terms. */
function _lineTotals(p, brand) {
  var out = {}, rep = p.meta.report || {};
  function inTab(day) { return (!rep.start || day >= rep.start) && (!rep.end || day <= rep.end); }
  PACING_LINES.forEach(function (l) {
    out[l.key] = { spend: 0, impr: 0, views: 0, clicks: 0, lpv: 0, purch: 0, inst: 0,
      bookings: 0, adjInst: 0, adjRev: 0, ga4Tx: 0, ga4Rev: 0, revenue: 0 };
  });
  p.raw.forEach(function (r) {
    var e = r[1] === brand && inTab(r[3]) && out[r[0] + '|' + r[12]];
    if (!e) return;
    e.spend += r[6]; e.impr += r[5]; e.lpv += r[7]; e.clicks += r[8];
    e.views += r[9]; e.inst += r[10]; e.purch += r[11];
  });
  p.adjust.forEach(function (a) {
    var e = a.brand === brand && inTab(a.day) && out[a.line];
    if (!e) return;
    e.bookings += a.bookings; e.adjInst += a.inst; e.adjRev += a.revenue;
  });
  p.ga4.forEach(function (g) {
    var e = g.brand === brand && inTab(g.day) && out[g.line];
    if (!e) return;
    e.ga4Tx += g.tx; e.ga4Rev += g.revenue;
  });
  PACING_LINES.forEach(function (l) {
    var e = out[l.key];
    e.revenue = CFG.WEB_REVENUE_FROM_GA4 && l.web ? e.ga4Rev : e.adjRev;
  });
  return out;
}

/**
 * Reconciles the payload against the two pacing tabs, line by line and metric by
 * metric — and the totals row — and writes the result to a "Dashboard Validation" tab.
 * Data-quality issues (the dashboard banner) are listed underneath.
 */
function validateDashboard() {
  requireSheetUser_();
  var ss = _ss();
  // Bring "Adjust Clean" up to date first (waiting for a rebuild another run has started), so the
  // asTab read and the pacing grids read the same build; a dashboard read in between would rebuild
  // it and leave the two sides on different copies. If it cannot be rebuilt, the dashboard read
  // below reports that as a critical issue.
  if (_adjustCleanStale_(ss)) {
    try { _refreshAdjustClean_(false, 60000); } catch (eRb) { Logger.log('Adjust Clean rebuild before Validate: ' + eRb.message); }
  }
  // Data quality: what the dashboard banner says (including how far the tabs are off).
  // Lines: the dashboard's counting against the formulas, reading what the formulas read.
  var shown = getPacingDashboardData();
  var p = getPacingDashboardData({ asTab: true });
  var out = [], bad = 0, total = 0;
  function row(a, b, c, d, e, f) { out.push([a, b, c, d, e, f]); }
  // Counts and money must agree to the cent (float noise is ~1e-9); a relative tolerance would
  // let whole campaign-days through on the big totals. Ratios (ROAS) pass their own tolerance.
  function cmp(brand, line, metric, dash, pacing, tol) {
    total++;
    var diff = dash - pacing;
    var ok = Math.abs(diff) <= (tol || 0.01);
    if (!ok) bad++;
    row(brand, line, metric, Math.round(dash * 100) / 100,
        Math.round(pacing * 100) / 100, ok ? 'OK' : 'CHECK');
  }

  row('DASHBOARD vs PACING TABS', Utilities.formatDate(new Date(), CFG.TZ, 'yyyy-MM-dd HH:mm'),
      '', '', '', '');
  var rep = p.meta.report;
  row('Window (pacing tabs B2:C2)', rep.start, 'to', rep.end, '', '');

  // [payload field, pacing column (1-based), label]
  var MEDIA = [['spend', 5, 'Spend USD (E)'], ['impr', 7, 'Impressions (G)'],
    ['views', 8, 'Views (H)'], ['clicks', 9, 'Clicks (I)'], ['lpv', 10, 'Link clicks (J)'],
    ['purch', 14, 'Platform purchases (N)'], ['inst', 15, 'Platform installs (O)']];

  ['SFQC', 'AAQC'].forEach(function (brand) {
    var ws = ss.getSheetByName(CFG.PACING_TABS[brand]);
    if (!ws) { row(brand, 'tab missing', '', '', '', 'CHECK'); bad++; total++; return; }
    var grid = ws.getRange(1, 1, 53, 24).getValues();
    function cell(r, c) { var v = grid[r - 1][c - 1]; return typeof v === 'number' ? v : 0; }
    var t = _lineTotals(p, brand);
    var sum = { spend: 0, impr: 0, views: 0, clicks: 0, lpv: 0, purch: 0, inst: 0,
      bookings: 0, adjInst: 0, ga4Tx: 0, revenue: 0 };

    row('', '', '', '', '', '');
    row(brand + ' · LINES', 'Dashboard', 'Pacing', '', '', '');
    PACING_LINES.forEach(function (l) {
      var e = t[l.key];
      if (l.source !== 'none') {
        MEDIA.forEach(function (m) {
          cmp(brand, l.label, m[2], e[m[0]], cell(l.row, m[1]));
          sum[m[0]] += e[m[0]];
        });
      }
      cmp(brand, l.label, 'Adjust purchase (K)', e.bookings, cell(l.row, 11));
      cmp(brand, l.label, 'Adjust install (L)', e.adjInst, cell(l.row, 12));
      if (l.ga4) cmp(brand, l.label, 'GA4 purchase (M)', e.ga4Tx, cell(l.row, 13));
      cmp(brand, l.label, 'Revenue SAR (X)', e.revenue, cell(l.row, 24));
      sum.bookings += e.bookings; sum.adjInst += e.adjInst; sum.ga4Tx += e.ga4Tx;
      sum.revenue += e.revenue;
    });

    row('', '', '', '', '', '');
    row(brand + ' · TOTALS (row 28)', 'Dashboard', 'Pacing', '', '', '');
    MEDIA.forEach(function (m) { cmp(brand, 'Total', m[2].replace(')', '28)'), sum[m[0]], cell(28, m[1])); });
    cmp(brand, 'Total', 'Spend SAR (F28)', sum.spend * CFG.FX, cell(28, 6));
    cmp(brand, 'Total', 'Adjust purchase (K28)', sum.bookings, cell(28, 11));
    cmp(brand, 'Total', 'Adjust install (L28)', sum.adjInst, cell(28, 12));
    cmp(brand, 'Total', 'GA4 purchase (M28)', sum.ga4Tx, cell(28, 13));
    cmp(brand, 'Total', 'Revenue SAR (X28)', sum.revenue, cell(28, 24));
    cmp(brand, 'Total', 'ROAS (P28)', sum.spend ? sum.revenue / (sum.spend * CFG.FX) : 0, cell(28, 16), 1e-6);
    // C49/D49 are every paid GA4 sale in B2:C2, including those before a row's start date
    var gaTx = 0, gaRev = 0;
    p.ga4.concat(p.ga4PreFloor || []).forEach(function (g) {
      if (g.brand === brand && g.day >= rep.start && g.day <= rep.end) { gaTx += g.tx; gaRev += g.revenue; }
    });
    cmp(brand, 'GA4 paid', 'Transactions (C49)', gaTx, cell(49, 3));
    cmp(brand, 'GA4 paid', 'Revenue (D49)', gaRev, cell(49, 4));
    cmp(brand, 'Check block', 'Spend not on a line (C41)', 0, cell(41, 3));
  });

  var issues = shown.meta.health.issues;
  // Adjust Raw changed, or Adjust Clean could not be rebuilt, while this check ran: the Adjust
  // figures may then compare two different builds, which re-running Fix would not change
  var adjustMoving = _adjustCleanStale_(ss);
  row('', '', '', '', '', '');
  row('DATA QUALITY', issues.length ? issues.length + ' issue(s)' : 'no issues', '', '', '', '');
  if (adjustMoving) {
    row('NOTE', '"' + CFG.ADJUST_CLEAN + '" is behind Adjust Raw (Adjust Raw changed while this check ran, or the ' +
      'rebuild could not run). Run Validate again in a minute.', '', '', '', '');
  }
  issues.forEach(function (it) {
    row(it.level === 'crit' ? 'FIX' : 'NOTE', it.text, '', '', '', it.level === 'crit' ? 'CHECK' : '');
  });

  var critical = issues.filter(function (it) { return it.level === 'crit'; }).length;
  out.splice(2, 0, ['RESULT', total + ' figures compared',
                    (total - bad) + ' match', bad + ' differ',
                    critical + ' data issue(s) to fix',
                    bad === 0 && critical === 0 ? 'OK' : 'CHECK']);

  var sh = ss.getSheetByName('Dashboard Validation');
  if (!sh) sh = ss.insertSheet('Dashboard Validation');
  sh.clear();
  sh.getRange(1, 1, out.length, 6).setValues(out);
  sh.getRange('A1').setFontSize(14).setFontWeight('bold');
  sh.getRange('A3:F3').setFontWeight('bold');
  out.forEach(function (r, i) {
    if (String(r[0]).indexOf(' · ') > -1 || r[0] === 'DATA QUALITY') {
      sh.getRange(i + 1, 1, 1, 6).setFontWeight('bold').setBackground('#000050').setFontColor('#ffffff');
    }
    if (r[5] === 'OK') sh.getRange(i + 1, 6).setBackground('#d9ead3');
    if (r[5] === 'CHECK') sh.getRange(i + 1, 6).setBackground('#f4cccc');
  });
  sh.setColumnWidth(1, 200); sh.setColumnWidth(2, 190); sh.setColumnWidth(3, 190);
  sh.setColumnWidth(4, 130); sh.setColumnWidth(5, 245); sh.setColumnWidth(6, 140);
  sh.setFrozenRows(3);
  ss.setActiveSheet(sh);
  Logger.log('%s figures compared, %s match, %s differ, %s data issues', total, total - bad, bad, critical);
  // Both sides read the same tabs, so a broken or empty source matches perfectly: with a
  // critical data issue the result is never reported as a plain "all match".
  var msg = (critical ? 'CHECK — ' + critical + ' critical data issue(s), listed at the bottom of the ' +
      '"Dashboard Validation" tab. The dashboard and the tabs read the same sources, so they can match and ' +
      'still both be wrong until these are fixed.\n\n' : '') +
    (bad === 0 ? 'All ' + total + ' figures match the pacing tabs.' :
      bad + ' of ' + total + ' figures differ — see the "Dashboard Validation" tab. ' + (adjustMoving ?
      '"' + CFG.ADJUST_CLEAN + '" is behind Adjust Raw, so run Validate again in a minute before anything else.' :
      'If the totals row or whole lines differ, run Qiddiya Setup → Fix this workbook first.')) +
    (issues.length > critical ? '\n\n' + (issues.length - critical) + ' note(s) are listed there too; each says ' +
      'whether it affects the pacing tabs, this dashboard or both.' : '');
  try { SpreadsheetApp.getUi().alert(msg); } catch (e) { /* no UI attached */ }
  return { total: total, bad: bad, critical: critical };
}

/* ------------------------------------------------------------------ Adjust Raw upkeep */

/**
 * Imports one or both Adjust CSV exports INTO Adjust Raw — the tab the pacing formulas
 * read — so the report and the dashboard update together. For each app in the files,
 * the rows already in Adjust Raw for the days the file covers are replaced (a re-export
 * of the same period restates attribution); every other day is kept.
 */
function showAdjustImporter() {
  var html = HtmlService.createHtmlOutput([
    '<!doctype html><meta charset="utf-8"><style>',
    'body{font:14px Arial;padding:20px;color:#172033}h2{margin:0 0 8px}',
    'p{line-height:1.45;color:#58657a}input{display:block;margin:18px 0}',
    'button{background:#1677ff;color:white;border:0;border-radius:7px;padding:10px 16px;font-weight:700}',
    'button:disabled{opacity:.5}#s{margin-top:14px;white-space:pre-wrap}</style>',
    '<h2>Import Adjust exports into Adjust Raw</h2>',
    '<p>Select the Six Flags and/or Aquarabia CSV files. For each app, the days the file covers ',
    'replace what Adjust Raw holds for those days; earlier days are kept. A backup is made first. ',
    'The pacing tabs and the dashboard both update.</p>',
    '<input id="f" type="file" accept=".csv,text/csv" multiple>',
    '<button id="b" onclick="go()">Import and refresh</button><div id="s"></div>',
    '<script>',
    'function csv(t){var out=[],r=[],v="",q=false;for(var i=0;i<t.length;i++){var c=t[i],n=t[i+1];if(q&&c===\'"\'&&n===\'"\'){v+=\'"\';i++;}else if(c===\'"\'){q=!q;}else if(!q&&c===","){r.push(v);v="";}else if(!q&&(c==="\\n"||c==="\\r")){if(c==="\\r"&&n==="\\n")i++;r.push(v);if(r.some(function(x){return x!==""}))out.push(r);r=[];v="";}else v+=c;}r.push(v);if(r.some(function(x){return x!==""}))out.push(r);return out;}',
    'async function go(){var fs=document.getElementById("f").files,b=document.getElementById("b"),s=document.getElementById("s");if(!fs.length){s.textContent="Choose at least one CSV.";return;}b.disabled=true;s.textContent="Reading files…";try{var all=[];for(var i=0;i<fs.length;i++)all.push(csv(await fs[i].text()));google.script.run.withSuccessHandler(function(x){s.textContent=x;b.disabled=false;}).withFailureHandler(function(e){s.textContent="Import failed: "+e.message;b.disabled=false;}).importAdjustCsv(all);}catch(e){s.textContent=e.message;b.disabled=false;}}',
    '</script>'
  ].join('')).setWidth(560).setHeight(360);
  SpreadsheetApp.getUi().showModalDialog(html, 'Adjust import');
}

/**
 * Adjust network + campaign -> channel and objective, in the vocabulary the pacing
 * formulas read (Google awareness is "YouTube", as row 10 expects). Used for imports and
 * to fill blanks; existing labels are never overwritten by it, except rows labelled Other
 * (or blank) that it can place: Twitter Installs -> X, Pangle (TikTok's placement network)
 * -> TikTok, and installs that are not paid -> Organic — a network or campaign called
 * organic (WhatsApp "Organic Share"), and Adjust's fraud filter "Untrusted Devices" (see
 * CFG.ADJUST_EXCLUDE_UNTRUSTED). Organic is on no pacing row.
 */
function _adjustClassify(network, campaign) {
  var n = String(network == null ? '' : network).trim();
  var c = String(campaign == null ? '' : campaign).trim();
  if (/\borganic\b/i.test(n) || /\borganic\b/i.test(c) ||
      (CFG.ADJUST_EXCLUDE_UNTRUSTED && /^Untrusted Devices\b/i.test(n)))
    return { channel: 'Organic', objective: 'Organic' };
  var ch = /^Snapchat/i.test(n) ? 'Snapchat'
    : /^(Facebook|Instagram|Off-Facebook|Meta|Audience Network|Messenger)\b/i.test(n) ? 'Meta'
    : /^Apple Search Ads/i.test(n) ? 'Apple'
    : /^(Google|YouTube|AdWords)/i.test(n) ? 'Google'
    : /^Bidease/i.test(n) ? 'Bidease'
    : /^InMobi/i.test(n) ? 'InMobi'
    : /^InMotion/i.test(n) ? 'InMotion'
    : /^(Twitter|X Ads|X)\b/i.test(n) ? 'X'
    : /^(TikTok|Pangle)\b/i.test(n) ? 'TikTok'
    : 'Other';
  if (ch === 'Google') {
    var o = _objective('Google', campaign);
    if (/YouTube/i.test(n) || o === 'Awareness') return { channel: ch, objective: 'YouTube' };
    if (/Search/i.test(n) || o === 'Search') return { channel: ch, objective: 'Search' };
    return { channel: ch, objective: 'Conversion' };
  }
  if (ch === 'Snapchat' || ch === 'TikTok' || ch === 'X') {
    return { channel: ch, objective: _objective(ch, campaign) };
  }
  return { channel: ch, objective: 'Conversion' };
}

function _numericText(v) {
  if (typeof v !== 'string') return null;
  var s = v.replace(/[, ]/g, '');
  return /^-?(?:\d+\.?\d*|\.\d+)$/.test(s) ? +s : null;
}
function _blank(v) { return v === '' || v === null || v === undefined; }
function _adjustAllZero(v) { return !_num(v[4]) && !_num(v[6]) && !_num(v[7]) && !_num(v[8]); }
// to the second: a backup made in the same minute as another must not replace it
function _stamp() { return Utilities.formatDate(new Date(), CFG.TZ, 'yyyyMMdd-HHmmss'); }

/**
 * Reads Adjust Raw into clean rows: real ISO days (text dd/MM and Sheets' day/month swaps
 * repaired), numbers as numbers, trimmed labels, blank or Other channels classified. Nothing
 * is written. win: see _adjustReversedRows. data.read / data.blank count the rows read.
 */
function _adjustReadClean_(sh, tz, log, win) {
  var range = sh.getDataRange();
  var values = range.getValues(), display = range.getDisplayValues();
  var header = values[0] || [];
  var problems = _headerProblems(header, ADJUST_EXPECT, CFG.ADJUST);
  if (problems.length) {
    throw new Error(problems.join('\n') + '\n\nThe pacing formulas read Adjust Raw by position, so ' +
      'the columns must be in this order: ' + ADJUST_LAYOUT.join(', ') + '.');
  }
  var width = Math.max(header.length, ADJUST_LAYOUT.length);
  var reversed = _adjustReversedRows(values, 0, tz, win);
  var rows = [], blankRows = 0;
  for (var j = 1; j < values.length; j++) {
    var v = values[j].slice();
    while (v.length < width) v.push('');
    if (v.every(_blank)) { blankRows++; continue; }
    var shown = display[j][0];
    var iso;
    try {
      iso = v[0] instanceof Date ? _adjustDay(v[0], j + 1, !!reversed[j], tz)
        : _adjustDay(String(shown || v[0]).trim(), j + 1, false, tz);
    } catch (e) {
      log.push([j + 1, 'Date not readable — row left as it is', shown, '']);
      rows.push({ v: v, day: '' });
      continue;
    }
    var dateFixed = !(v[0] instanceof Date) || iso !== _day(v[0], tz);
    if (!(v[0] instanceof Date)) log.push([j + 1, 'Text date converted to a real date', shown, iso]);
    else if (iso !== _day(v[0], tz)) log.push([j + 1, 'Day/month swap reversed', shown, iso]);
    v[0] = iso;
    [4, 5, 6, 7, 8].forEach(function (c) {
      if (_blank(v[c]) || typeof v[c] === 'number') return;
      var n = _numericText(v[c]);
      if (n !== null) {
        log.push([j + 1, 'Number stored as text converted (' + ADJUST_LAYOUT[c] + ')', String(v[c]), n]);
        v[c] = n;
      } else {
        log.push([j + 1, 'Not a number — left as it is (' + ADJUST_LAYOUT[c] + ')', String(v[c]), '']);
      }
    });
    [1, 2, 3, 9, 10].forEach(function (c) {
      if (typeof v[c] === 'string' && v[c] !== v[c].trim()) v[c] = v[c].trim();
    });
    var rc = /^other$/i.test(String(v[9])) ? _adjustClassify(v[1], v[2]) : null;
    if (rc && rc.channel !== 'Other') {
      // Twitter Installs, Pangle, Untrusted Devices, Organic Share: filed under Other by the export
      log.push([j + 1, v[1] + ' moved from "' + v[9] + '" to channel ' + rc.channel +
        (rc.channel === 'Organic' ? ' (not paid)' : ''), v[9] + ' / ' + v[10], rc.channel + ' / ' + rc.objective]);
      v[9] = rc.channel; v[10] = rc.objective;
    } else if (_blank(v[9]) || _blank(v[10])) {
      var cls = _adjustClassify(v[1], v[2]);
      log.push([j + 1, 'Missing channel/objective filled', v[9] + ' / ' + v[10],
        (_blank(v[9]) ? cls.channel : v[9]) + ' / ' + (_blank(v[10]) ? cls.objective : v[10])]);
      if (_blank(v[9])) v[9] = cls.channel;
      if (_blank(v[10])) v[10] = cls.objective;
    }
    rows.push({ v: v, day: iso, dateFixed: dateFixed });
  }
  return { header: header, width: width, rows: rows, read: rows.length, blank: blankRows };
}

/**
 * Overlapping imports: one row per day + app + network + campaign. The later row wins
 * (Adjust restates attribution), except that a later all-zero partial refresh never
 * erases an earlier non-zero row.
 */
function _adjustDedupe_(data, log) {
  var groups = {};
  data.rows.forEach(function (row, i) {
    if (!row.day) return;
    var v = row.v;
    var k = JSON.stringify([row.day, String(v[3]).toLowerCase(), String(v[1]), String(v[2])]);
    (groups[k] = groups[k] || []).push(i);
  });
  var drop = {};
  Object.keys(groups).forEach(function (k) {
    var ix = groups[k];
    if (ix.length < 2) return;
    var keep = ix[ix.length - 1];
    if (_adjustAllZero(data.rows[keep].v)) {
      for (var q = ix.length - 2; q >= 0; q--) {
        if (!_adjustAllZero(data.rows[ix[q]].v)) { keep = ix[q]; break; }
      }
    }
    ix.forEach(function (i) {
      if (i === keep) return;
      drop[i] = 1;
      var v = data.rows[i].v;
      log.push(['', 'Duplicate removed (kept the later import)', [v[0], v[3], v[1], v[2]].join(' · '),
        'installs ' + v[7] + ', bookings ' + v[8] + ', revenue ' + v[4]]);
    });
  });
  data.removed = (data.removed || []).concat(data.rows.filter(function (r, i) { return drop[i]; }));
  data.rows = data.rows.filter(function (r, i) { return !drop[i]; });
  return Object.keys(drop).length;
}

/**
 * Replace, per app, the existing rows of exactly the days the incoming rows hold — never
 * the days in between two files, which an export does not cover.
 */
function _adjustUpsert_(data, incoming, label, log) {
  var days = {}, ranges = {};
  incoming.forEach(function (r) {
    var app = String(r[3]).toLowerCase();
    days[app + '|' + r[0]] = 1;
    var e = ranges[app] || (ranges[app] = { min: r[0], max: r[0], days: {} });
    if (r[0] < e.min) e.min = r[0];
    if (r[0] > e.max) e.max = r[0];
    e.days[r[0]] = 1;
  });
  var replaced = 0;
  data.rows = data.rows.filter(function (row) {
    if (!row.day) return true;
    if (days[String(row.v[3]).toLowerCase() + '|' + row.day]) { replaced++; return false; }
    return true;
  });
  incoming.forEach(function (r) {
    var v = r.slice();
    while (v.length < data.width) v.push('');
    data.rows.push({ v: v, day: v[0] });
  });
  Object.keys(ranges).forEach(function (app) {
    log.push(['', label + ': ' + app + ' ' + ranges[app].min + ' → ' + ranges[app].max + ' (' +
      Object.keys(ranges[app].days).length + ' days) replaced', '', '']);
  });
  return { replaced: replaced, added: incoming.length, ranges: ranges };
}

/**
 * Values-only hidden copy of a tab, its grid cut to the data (a new tab starts at 1000 x 26
 * cells, and the workbook holds 10M), keeping only the newest CFG.BACKUPS_KEPT copies of
 * that tab. Untitled.gs's backupValues_ is the same thing by tab name.
 */
function _backupValues(ss, sh, name) {
  var rows = Math.max(1, sh.getLastRow()), cols = Math.max(1, sh.getLastColumn());
  var values = sh.getRange(1, 1, rows, cols).getValues();
  var old = ss.getSheetByName(name);
  if (old) ss.deleteSheet(old);
  var dst = ss.insertSheet(name, ss.getSheets().length);
  if (dst.getMaxColumns() < cols) dst.insertColumnsAfter(dst.getMaxColumns(), cols - dst.getMaxColumns());
  if (dst.getMaxRows() < rows) dst.insertRowsAfter(dst.getMaxRows(), rows - dst.getMaxRows());
  dst.getRange(1, 1, rows, cols).setValues(values);
  if (dst.getMaxColumns() > cols) dst.deleteColumns(cols + 1, dst.getMaxColumns() - cols);
  if (dst.getMaxRows() > rows) dst.deleteRows(rows + 1, dst.getMaxRows() - rows);
  dst.hideSheet();
  _pruneBackups_(ss, name.replace(/ BACKUP \d{8}-\d{4,6}$/, ''), CFG.BACKUPS_KEPT);
  return dst;
}
/**
 * Deletes all but the newest `keep` "<tab> BACKUP <stamp>" copies of one tab. The InMobi
 * source CFG.RAW_BACKUP is named like a backup but is data (pacing row 24), so it is never
 * touched.
 */
function _pruneBackups_(ss, tab, keep) {
  var re = new RegExp('^' + tab.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' BACKUP \\d{8}-\\d{4,6}$');
  var all = ss.getSheets().filter(function (x) {
    var n = x.getName();
    return n !== CFG.RAW_BACKUP && re.test(n);
  }).sort(function (a, b) { return a.getName() < b.getName() ? 1 : -1; });   // newest first
  all.slice(keep).forEach(function (x) { ss.deleteSheet(x); });
  return Math.max(0, all.length - keep);
}

/**
 * Writes the rows over the old ones in place, then clears only what is left below (and right of)
 * them. The previous complete copy therefore survives a write that fails or times out — the
 * tab is never left empty, not even for the seconds a large write takes. Row 1 (headers, the
 * Adjust Clean note in M1) is never touched.
 */
function _adjustWrite_(sh, data) {
  data.rows.sort(function (a, b) {
    if (!a.day !== !b.day) return a.day ? -1 : 1;              // unreadable rows go last
    var ka = [a.day, String(a.v[3]), String(a.v[1]), String(a.v[2])].join('\u0001');
    var kb = [b.day, String(b.v[3]), String(b.v[1]), String(b.v[2])].join('\u0001');
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
  var out = data.rows.map(function (r) { return r.v.slice(0, data.width); });
  var last = sh.getLastRow(), lastCol = sh.getLastColumn(), n = out.length, w = data.width;
  if (n) {
    if (sh.getMaxRows() < n + 1) sh.insertRowsAfter(sh.getMaxRows(), n + 1 - sh.getMaxRows());
    // Labels are stored as plain text so a campaign name can never be re-read as a date or
    // a formula; the day is written as yyyy-mm-dd, which every locale reads as a real date.
    [2, 3, 4, 10, 11].forEach(function (c) { sh.getRange(2, c, n, 1).setNumberFormat('@'); });
    sh.getRange(2, 1, n, 1).setNumberFormat('yyyy-mm-dd');
    sh.getRange(2, 1, n, w).setValues(out);                   // overwrites the old rows in place
  }
  if (last > n + 1) sh.getRange(n + 2, 1, last - n - 1, Math.max(w, lastCol)).clearContent();   // the old tail
  var kept = Math.min(last, n + 1);
  if (lastCol > w && kept > 1) sh.getRange(2, w + 1, kept - 1, lastCol - w).clearContent();   // stray columns
  return n;
}

function _writeLog(ss, title, log) {
  var name = 'Adjust Raw cleanup log';
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  sh.clear();
  sh.getRange('C:D').setNumberFormat('@');           // show before/after exactly as text
  var rows = [[title, '', '', ''], ['Source row', 'Action', 'Before', 'After']].concat(
    log.slice(0, 50000).map(function (r) { return [r[0], r[1], String(r[2]), String(r[3])]; }));
  sh.getRange(1, 1, rows.length, 4).setValues(rows);
  sh.getRange('A1').setFontWeight('bold').setFontSize(13);
  sh.getRange('A2:D2').setFontWeight('bold');
  sh.setFrozenRows(2);
}

/**
 * Adjust Raw read and corrected in memory — real days, numbers and labels, the rows still in
 * the old "Adjust Current" tab folded in, overlapping imports de-duplicated. Nothing is
 * written: "Clean Adjust Raw" writes the result back, the dashboard reads it directly.
 */
function _adjustCleanData_(ss, sh, tz, log) {
  var data = _adjustReadClean_(sh, tz, log, _adjustSwapWindow_(ss, tz));
  var merged = null, legacy = ss.getSheetByName(CFG.ADJUST_LEGACY);
  if (legacy && legacy.getLastRow() > 1) {
    var lv = legacy.getDataRange().getValues(), lh = lv[0].map(function (h) { return String(h).trim(); });
    var pos = {}; lh.forEach(function (h, i) { pos[h] = i; });
    var sums = {}, incoming = [];
    lv.slice(1).forEach(function (r) {
      var day = _dateCell(r[pos.day], tz) || String(r[pos.day] || '').slice(0, 10);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return;
      var network = String(r[pos.network] || '').trim();
      var campaign = String(r[pos.campaign_network] || '').trim();
      var app = String(r[pos.app] || '').trim();
      // One export: a repeated key is a further breakdown of the same day, so add it up.
      var key = JSON.stringify([day, app.toLowerCase(), network, campaign]);
      var e = sums[key];
      if (!e) {
        // The old importer had no YouTube / awareness rules, so its labels are redone.
        var cls = _adjustClassify(network, campaign);
        e = sums[key] = [day, network, campaign, app, 0, 0, 0, 0, 0, cls.channel, cls.objective];
        incoming.push(e);
      }
      e[4] += _num(r[pos.all_revenue]);
      e[5] += pos['general revenue_revenue_est'] == null ? 0 : _num(r[pos['general revenue_revenue_est']]);
      e[6] += _num(r[pos.paid_installs]);
      e[7] += _num(r[pos.installs]);
      e[8] += _num(r[pos.bookingconfirmed_events]);
    });
    if (incoming.length) merged = _adjustUpsert_(data, incoming, CFG.ADJUST_LEGACY, log);
  }
  var xapp = _adjustDropMislabelled_(data, log);
  var dropped = _adjustDedupe_(data, log);
  return { data: data, merged: merged, legacy: legacy, dropped: dropped, xapp: xapp };
}

/** Which portal a row's network + campaign names, if exactly one. */
var ADJUST_NAME_BRAND = {
  SFQC: /(^|[^a-z])sfqc[-_ ]|six ?flags|sixflags/i,
  AAQC: /(^|[^a-z])(aqc|aqqc)[-_ ]|aquarabia|aquaarabia/i
};
function _adjustNameBrand_(v) {
  var t = String(v[1] == null ? '' : v[1]) + ' ' + String(v[2] == null ? '' : v[2]);
  var sf = ADJUST_NAME_BRAND.SFQC.test(t), aq = ADJUST_NAME_BRAND.AAQC.test(t);
  return sf && !aq ? 'SFQC' : aq && !sf ? 'AAQC' : '';
}
/**
 * Export pasted under the wrong app. On the live file a both-apps export for 15-28 Sep was
 * pasted with every row's app set to "Aquarabia": 411 of its 420 Six Flags campaign rows
 * are field-for-field copies of rows already filed under Six Flags, and its generic rows
 * (Apple "unknown", Expired Attributions, Untrusted Devices) copy Six Flags values too.
 * The app is part of the duplicate key, so the cleaner kept them all for Aquarabia.
 *
 * A run of consecutive rows with one app that holds 20+ rows naming the other portal,
 * extended over its neighbours dated inside the same days, is dropped whole — but only if
 * every app-day in it also has rows outside it, so no day can lose its data. Elsewhere a
 * row naming the other portal is dropped only when an identical row (same day, network,
 * campaign and figures) exists under that portal; otherwise it is left as it is.
 */
function _adjustDropMislabelled_(data, log) {
  var rows = data.rows, n = rows.length;
  function app(i) { return String(rows[i].v[3] == null ? '' : rows[i].v[3]).trim().toLowerCase(); }
  var bad = rows.map(function (r) {
    var ab = _matchBrand(CFG.ADJUST_APP, r.v[3]), nb = _adjustNameBrand_(r.v);
    return ab && nb && ab !== nb ? nb : '';
  });
  var drop = {}, runRows = 0, twinRows = 0;
  for (var i = 0; i < n;) {
    var j = i;
    while (j + 1 < n && app(j + 1) === app(i)) j++;
    var idx = [];
    for (var k = i; k <= j; k++) if (bad[k] && rows[k].day) idx.push(k);
    if (idx.length >= 20) {
      var lo = rows[idx[0]].day, hi = lo;
      idx.forEach(function (q) { if (rows[q].day < lo) lo = rows[q].day; if (rows[q].day > hi) hi = rows[q].day; });
      var a = idx[0], b = idx[idx.length - 1];
      while (a - 1 >= i && rows[a - 1].day && rows[a - 1].day >= lo && rows[a - 1].day <= hi) a--;
      while (b + 1 <= j && rows[b + 1].day && rows[b + 1].day >= lo && rows[b + 1].day <= hi) b++;
      var inside = {}, outside = {};
      for (var q = a; q <= b; q++) inside[rows[q].day] = 1;
      for (var o = 0; o < n; o++) if ((o < a || o > b) && app(o) === app(a) && rows[o].day) outside[rows[o].day] = 1;
      if (Object.keys(inside).every(function (d) { return outside[d]; })) {
        for (var z = a; z <= b; z++) drop[z] = 1;
        runRows += b - a + 1;
        log.push(['', 'Cross-app copy removed: ' + (b - a + 1) + ' consecutive rows filed under "' +
          rows[a].v[3] + '" for ' + lo + ' → ' + hi + ', ' + idx.length + ' of them naming the other portal', '', '']);
      }
    }
    i = j + 1;
  }
  // single rows naming the other portal: drop only an exact copy of a row filed there
  var sig = {};
  function key(v, appName) {
    return JSON.stringify([String(appName).toLowerCase(), v[0], String(v[1]), String(v[2]),
      _num(v[4]), _num(v[6]), _num(v[7]), _num(v[8])]);
  }
  rows.forEach(function (r, x) { if (!drop[x]) sig[key(r.v, r.v[3])] = 1; });
  rows.forEach(function (r, x) {
    if (drop[x] || !bad[x]) return;
    if (sig[key(r.v, CFG.ADJUST_APP[bad[x]])]) {
      drop[x] = 1; twinRows++;
      log.push(['', 'Cross-app copy removed (identical row under ' + CFG.ADJUST_APP[bad[x]] + ')',
        [r.v[0], r.v[3], r.v[1], r.v[2]].join(' · '), '']);
    }
  });
  data.removed = (data.removed || []).concat(rows.filter(function (r, x) { return drop[x]; }));
  data.rows = rows.filter(function (r, x) { return !drop[x]; });
  return runRows + twinRows;
}

/**
 * The days the dashboard's "All" counts: SFQC Pacing_Daily B2 to C2 or yesterday, whichever is
 * later (today is left out until it is over, as C2 = TODAY()-1 does). getPacingDashboardData
 * loads exactly this window, and Adjust Clean holds exactly these days.
 */
function _reportWindow_(ss) {
  var tz = ss.getSpreadsheetTimeZone(), pac = ss.getSheetByName(CFG.PACING);
  var from = pac ? _day(pac.getRange('B2').getValue(), tz) : '';
  var till = pac ? _day(pac.getRange('C2').getValue(), tz) : '';
  return { from: from, till: _later(till, _yesterday(tz)) };
}

/**
 * Why a corrected Adjust row is not counted by the dashboard's "All" ('' when it is counted) —
 * the same tests, in the same order, as the dashboard's own loop. win = _reportWindow_().
 */
function _adjustLeftOut_(row, win) {
  if (!_matchBrand(CFG.ADJUST_APP, row.v[3])) return 'noapp';
  if (!row.day) return 'nodate';
  var line = _adjustLine(row.v[9], row.v[10]);
  if (!line) return 'organic';
  if (win && win.from && row.day < win.from) return 'before';
  if (win && win.till && row.day > win.till) return 'after';
  var fl = _adjustFloor(LINE_BY_KEY[line]);
  return fl && row.day < fl ? 'prefloor' : '';
}

/*
 * Tells whether Adjust Clean is current: changes whenever anything the cleaner reads changes —
 * every Adjust Raw row that is not fully blank (a dateless row splits the runs the cross-app rule
 * tests), in order, every column, and the old "Adjust Current" tab it folds in. ADJUST_CLEAN_RULES
 * is bumped whenever the cleaner's rules change, so the next hourly run rebuilds Adjust Clean.
 */
var ADJUST_CLEAN_RULES = '4';   // 3: only counted rows are written; 4: and only the days "All" counts
function _adjustFingerprint_(values, ss) {
  var h = 0, rows = 0;
  function mix(t) { for (var c = 0; c < t.length; c++) h = (h * 31 + t.charCodeAt(c)) | 0; }
  function cell(x) { return x instanceof Date ? 'd' + x.getTime() : String(x == null ? '' : x); }
  for (var i = 1; i < values.length; i++) {
    var v = values[i];
    if (v.every(_blank)) continue;                // the cleaner skips only fully blank rows
    rows++;
    mix(v.map(cell).join('|') + '\n');
  }
  var lg = ss && ss.getSheetByName(CFG.ADJUST_LEGACY);
  if (lg && lg.getLastRow() > 1) {
    mix('#legacy\n');
    lg.getDataRange().getValues().forEach(function (r) { mix(r.map(cell).join('|') + '\n'); });
  }
  // the window is part of it: when the day rolls over (or B2:C2 change) Adjust Clean takes in
  // the new day at the next dashboard load or hourly run, even if Adjust Raw has not changed
  var win = ss ? _reportWindow_(ss) : { from: '', till: '' };
  return ADJUST_CLEAN_RULES + ':' + win.from + '..' + win.till + ':' + rows + ':' + h;
}
/** Adjust Clean is read by the pacing tabs and no longer matches Adjust Raw. */
function _adjustCleanStale_(ss) {
  if (!ss.getSheetByName(CFG.ADJUST_CLEAN) || !_pacingReads_(ss).clean) return false;
  var src = ss.getSheetByName(CFG.ADJUST);
  if (!src) return false;
  return PropertiesService.getDocumentProperties().getProperty('adjustCleanFp') !==
    _adjustFingerprint_(src.getDataRange().getValues(), ss);
}

/**
 * Rebuilds "Adjust Clean" from Adjust Raw (and any old "Adjust Current" rows).
 *   force: always (Fix this workbook, Clean Adjust Raw, the CSV import — all gated); creates the tab.
 *   not forced (dashboard load, hourly trigger): only when Adjust Raw or the report window (a new
 *   day) has changed since the last build; never creates the tab (the dashboard forces the first
 *   build), and decides that before taking the script lock.
 * waitMs: how long to wait for another run's rebuild (default 60 s forced, 5 s not).
 * Returns { rebuilt: true, log, cd, rows, at }, { current: true, at } when nothing had changed,
 * { unused: true } when the tabs do not read Adjust Clean, or { busy: true } when another run
 * held the lock.
 */
function _refreshAdjustClean_(force, waitMs) {
  var props = PropertiesService.getDocumentProperties();
  if (!force) {
    var ss0 = _ss();
    // a stale-only rebuild keeps an existing tab current whether or not the pacing tabs read it
    // yet; creating it is left to forced runs and the dashboard's first load
    if (!ss0.getSheetByName(CFG.ADJUST_CLEAN)) return { unused: true };
    var fp0 = _adjustFingerprint_(_sheet(CFG.ADJUST).getDataRange().getValues(), ss0);
    if (props.getProperty('adjustCleanFp') === fp0) return { current: true, at: props.getProperty('adjustCleanAt') };
  }
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(waitMs || (force ? 60000 : 5000))) return { busy: true };
  try {
    var ss = _ss(), tz = ss.getSpreadsheetTimeZone();
    var src = _sheet(CFG.ADJUST);
    var fp = _adjustFingerprint_(src.getDataRange().getValues(), ss);
    var dst = ss.getSheetByName(CFG.ADJUST_CLEAN);
    // another run may have rebuilt it while this one waited for the lock
    if (!force && dst && props.getProperty('adjustCleanFp') === fp) return { current: true, at: props.getProperty('adjustCleanAt') };
    var log = [];
    var cd = _adjustCleanData_(ss, src, tz, log);
    if (!dst) {
      dst = ss.insertSheet(CFG.ADJUST_CLEAN, ss.getSheets().length);
      dst.setTabColor('#999999');
    }
    if (dst.getMaxColumns() < ADJUST_LAYOUT.length) {
      dst.insertColumnsAfter(dst.getMaxColumns(), ADJUST_LAYOUT.length - dst.getMaxColumns());
    }
    dst.getRange(1, 1, 1, ADJUST_LAYOUT.length).setValues([ADJUST_LAYOUT]).setFontWeight('bold');
    dst.setFrozenRows(1);
    cd.data.width = ADJUST_LAYOUT.length;
    // until the write has finished the stored fingerprint matches nothing, so a write that fails
    // or times out is retried by the next dashboard load or hourly run, forced or not
    props.deleteProperty('adjustCleanFp');
    // Only rows the dashboard's "All" counts go into the tab: rows for another app, organic
    // (incl. Untrusted Devices and WhatsApp shares), rows outside the report's days (today
    // until it is over), rows dated before their pacing row starts and rows with no readable
    // day are left out — the formulas would skip them anyway — so SUM of its installs column
    // is the installs the dashboard shows under All and row 28 counts.
    var win = _reportWindow_(ss), left = {}, LEFT_WHY = {
      noapp: 'for an app other than ' + Object.keys(CFG.ADJUST_APP).map(function (b) {
        return CFG.ADJUST_APP[b]; }).join(' / ') + ' (column D)',
      nodate: 'with no readable day',
      organic: 'not paid (Organic, Untrusted Devices, WhatsApp shares)',
      before: 'dated before the report starts (SFQC Pacing_Daily B2, ' + win.from + ')',
      after: 'dated after ' + win.till + ' (today and later: a day is added once it is over)',
      prefloor: 'dated before their pacing row starts (' + CFG.ADJUST_FROM + ' on the conversion rows)' };
    var counted = cd.data.rows.filter(function (row) {
      var v = row.v, why = _adjustLeftOut_(row, win);
      if (!why) return true;
      var e = left[why] || (left[why] = { rows: 0, inst: 0, book: 0, rev: 0 });
      e.rows++; e.inst += _cellNum(v[7]); e.book += _cellNum(v[8]); e.rev += _cellNum(v[4]);
      return false;
    });
    Object.keys(left).forEach(function (k) {
      log.push(['', 'Left out of "' + CFG.ADJUST_CLEAN + '": ' + left[k].rows + ' rows ' + LEFT_WHY[k],
        '', left[k].inst + ' installs, ' + left[k].book + ' bookings, ' + Math.round(left[k].rev) + ' revenue']);
    });
    var rows = _adjustWrite_(dst, { rows: counted, width: cd.data.width });
    var at = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd HH:mm');
    dst.getRange('M1').setValue('Built by the script from "' + CFG.ADJUST + '" at ' + at + ' — only the rows ' +
      'the dashboard counts under All, ' + win.from + ' to ' + win.till + ' (copies, duplicates, organic, other ' +
      'apps, today and pre-launch rows left out; see "Adjust Raw cleanup log"). Do not edit; the pacing tabs ' +
      'read this tab.');
    props.setProperty('adjustCleanFp', fp);
    props.setProperty('adjustCleanAt', at);
    _writeLog(ss, 'Adjust Clean · ' + at, log);   // every rebuild, so the log never lags the tab
    SpreadsheetApp.flush();
    return { rebuilt: true, log: log, cd: cd, rows: rows, at: at };
  } finally {
    lock.releaseLock();
  }
}
/**
 * Hourly trigger: keeps "Adjust Clean" in step with Adjust Raw. It does no more than a dashboard
 * load does — rebuild an Adjust Clean the pacing tabs read, only when Adjust Raw has changed — and
 * returns nothing, so calling it through the dashboard link gains nothing. Forced rebuilds are
 * Pacing dashboard → Clean Adjust Raw and Fix this workbook, both limited to the sheet's users.
 * After Undo "Fix this workbook" (adjustCleanOff) a trigger removes itself at its next run: a
 * trigger runs as the account that created it, which is the only one that can see and delete it.
 */
function refreshAdjustClean(e) {
  var props = PropertiesService.getDocumentProperties();
  if (props.getProperty('adjustCleanOff')) {
    try {
      var gone = 0;
      ScriptApp.getProjectTriggers().forEach(function (t) {
        if (t.getHandlerFunction() === 'refreshAdjustClean') { ScriptApp.deleteTrigger(t); gone++; }
      });
      if (gone) {
        var me = who_(), by = (props.getProperty('adjustCleanTriggerBy') || '').split(',').filter(function (x) {
          return x && x !== me;
        });
        props.setProperty('adjustCleanTriggerBy', by.join(','));
      }
    } catch (eT) { Logger.log('refreshAdjustClean: ' + eT.message); }
    return;
  }
  _refreshAdjustClean_(false);
}

/**
 * Rebuilds "Adjust Clean", the corrected copy of Adjust Raw the pacing formulas read: text and
 * day/month-swapped dates become real dates, overlapping and mislabelled imports are dropped,
 * numbers stored as text become numbers, rows the export filed under Other get their channel
 * (Twitter -> X, Pangle -> TikTok, Untrusted Devices / Organic Share -> Organic), and rows
 * left in the old "Adjust Current" tab are folded in. Adjust Raw itself is never changed; a
 * line-by-line log is written. Safe to run as often as you like.
 */
function cleanAdjustRaw() {
  requireSheetUser_();
  var msg = cleanAdjustRaw_();
  try { SpreadsheetApp.getUi().alert(msg); } catch (e) { /* no UI attached */ }
  return msg;
}

/** cleanAdjustRaw() without the dialog, so "Fix this workbook" can run it as one step. */
function cleanAdjustRaw_() {
  var res = _refreshAdjustClean_(true);
  if (!res || !res.rebuilt) throw new Error('Another run is rebuilding "' + CFG.ADJUST_CLEAN + '" — try again in a minute.');
  var log = res.log, cd = res.cd;
  var fixedDates = log.filter(function (r) { return /Text date|swap/i.test(r[1]); }).length;
  var unreadable = log.filter(function (r) { return /not readable/.test(r[1]); }).length;
  var labels = log.filter(function (r) { return /moved from|Missing channel/.test(r[1]); }).length;
  var msg = '"' + CFG.ADJUST_CLEAN + '" rebuilt from "' + CFG.ADJUST + '": ' + cd.data.read + ' rows read (' +
    cd.data.blank + ' empty rows skipped), ' + res.rows + ' rows written.\n' +
    '· ' + fixedDates + ' dates repaired' + (unreadable ? ', ' + unreadable + ' still unreadable (see log)' : '') + '\n' +
    '· ' + labels + ' rows given a channel (Other / blank)\n' +
    '· ' + cd.xapp + ' rows pasted under the wrong app removed\n' +
    '· ' + cd.dropped + ' duplicate rows from overlapping imports removed\n' +
    (cd.merged ? '· ' + cd.merged.added + ' rows folded in from "' + CFG.ADJUST_LEGACY + '"\n' : '') +
    '"' + CFG.ADJUST + '" itself is not changed. Every correction is listed in "Adjust Raw cleanup log".';
  Logger.log(msg);
  return msg;
}

/** Called by the import dialog with one parsed table per CSV file. */
function importAdjustCsv(files) {
  requireSheetUser_();
  if (!files || !files.length) throw new Error('No CSV data received.');
  var required = ['day', 'network', 'campaign_network', 'app', 'all_revenue', 'paid_installs',
    'installs', 'bookingconfirmed_events'];
  var ss0 = _ss(), sh0 = ss0.getSheetByName(CFG.ADJUST);
  var f0 = _formulaTab_(sh0);
  if (f0) {
    var srcInfo = _importSource_(f0);
    throw new Error('"' + CFG.ADJUST + '" in this file is ' + (srcInfo ? 'an IMPORTRANGE of "' + srcInfo.tab +
      '" in another workbook' : 'the output of a formula') + ', so the import cannot write into it without ' +
      'breaking it. Paste the Adjust export into that source tab instead; this file picks it up and ' +
      '"' + CFG.ADJUST_CLEAN + '" is rebuilt within the hour (or now: Pacing dashboard → Clean Adjust Raw).');
  }
  var today = Utilities.formatDate(new Date(), ss0.getSpreadsheetTimeZone(), 'yyyy-MM-dd');
  var incoming = [], apps = {}, skipped = 0, partial = 0;
  files.forEach(function (table, fileIndex) {
    if (!table || table.length < 2) throw new Error('CSV ' + (fileIndex + 1) + ' is empty.');
    if (table.length - 1 === 5000) {
      throw new Error('CSV ' + (fileIndex + 1) + ' has exactly 5,000 rows — the size at which an Adjust ' +
        'export is cut off, so its last day is incomplete. Export a shorter date range.');
    }
    var header = table[0].map(function (x) { return String(x || '').replace(/^\uFEFF/, '').trim(); });
    var pos = {}; header.forEach(function (x, i) { pos[x] = i; });
    required.forEach(function (x) {
      if (pos[x] == null) throw new Error('CSV ' + (fileIndex + 1) + ' is missing "' + x + '".');
    });
    // Within ONE export a repeated key is a further breakdown (OS, country) of the same day,
    // so it is added up. Across files nothing is added: a later file replaces an earlier
    // file's days.
    var sums = {}, order = [];
    table.slice(1).forEach(function (r, ri) {
      var app = String(r[pos.app] || '').trim();
      if (!_matchBrand(CFG.ADJUST_APP, app)) return;
      var day = String(r[pos.day] || '').trim();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) {
        throw new Error('CSV ' + (fileIndex + 1) + ' row ' + (ri + 2) + ': day "' + day +
          '" is not yyyy-mm-dd. Export from Adjust again without opening the file in Excel first.');
      }
      if (day >= today) { partial++; return; }            // today is still accumulating
      var network = String(r[pos.network] || '').trim();
      var campaign = String(r[pos.campaign_network] || '').trim();
      var cls = _adjustClassify(network, campaign);
      apps[app] = true;
      var key = JSON.stringify([day, app.toLowerCase(), network, campaign]);
      var e = sums[key];
      if (!e) {
        e = sums[key] = [day, network, campaign, app, 0, 0, 0, 0, 0, cls.channel, cls.objective];
        order.push(key);
      }
      e[4] += _num(r[pos.all_revenue]);
      e[5] += pos['general revenue_revenue_est'] == null ? 0 : _num(r[pos['general revenue_revenue_est']]);
      e[6] += _num(r[pos.paid_installs]);
      e[7] += _num(r[pos.installs]);
      e[8] += _num(r[pos.bookingconfirmed_events]);
    });
    var rows = order.map(function (k) { return sums[k]; });
    // a later file replaces the app-days an earlier file already supplied
    var mine = {};
    rows.forEach(function (r) { mine[String(r[3]).toLowerCase() + '|' + r[0]] = 1; });
    var before = incoming.length;
    incoming = incoming.filter(function (r) { return !mine[String(r[3]).toLowerCase() + '|' + r[0]]; });
    skipped += before - incoming.length;
    incoming = incoming.concat(rows);
  });
  if (!incoming.length) throw new Error('No Six Flags or Aquarabia rows for days before today were found.');

  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var ss = _ss(), tz = ss.getSpreadsheetTimeZone(), stamp = _stamp(), log = [];
    var sh = ss.getSheetByName(CFG.ADJUST);
    if (!sh) {
      sh = ss.insertSheet(CFG.ADJUST);
      sh.getRange(1, 1, 1, ADJUST_LAYOUT.length).setValues([ADJUST_LAYOUT]).setFontWeight('bold');
      sh.setFrozenRows(1);
    }
    var data = _adjustReadClean_(sh, tz, log, _adjustSwapWindow_(ss, tz));
    var res = _adjustUpsert_(data, incoming, 'Import', log);
    var dropped = _adjustDedupe_(data, log);
    if (sh.getLastRow() > 1) _backupValues(ss, sh, CFG.ADJUST + ' BACKUP ' + stamp);
    var total = _adjustWrite_(sh, data);
    _writeLog(ss, 'Adjust import · ' + stamp, log);
    SpreadsheetApp.flush();
  } finally {
    lock.releaseLock();
  }
  if (ss.getSheetByName(CFG.ADJUST_CLEAN)) _refreshAdjustClean_(true);
  return 'Imported ' + res.added + ' rows for ' + Object.keys(apps).join(' + ') + ' (' +
    Object.keys(res.ranges).map(function (a) {
      return a + ' ' + res.ranges[a].min + ' → ' + res.ranges[a].max + ', ' + Object.keys(res.ranges[a].days).length + ' days';
    }).join('; ') + '), replacing ' + res.replaced + ' older rows for exactly those days' +
    (dropped ? ' and ' + dropped + ' duplicates elsewhere' : '') +
    (skipped ? '. ' + skipped + ' rows from an earlier file were replaced by a later file for the same days' : '') +
    (partial ? '. ' + partial + ' rows dated today were left out (the day is not complete)' : '') +
    '.\nAdjust Raw now has ' + total + ' rows. The pacing tabs have recalculated; press Refresh on the dashboard.';
}
/** Older dialogs call this name. */
function replaceAdjustCurrent(files) { return importAdjustCsv(files); }

/* ------------------------------------------------------------------ standalone export */

/**
 * Writes a single self-contained HTML file to Drive with the current numbers baked in.
 * It opens in any browser with no Google account behind it — useful when the Workspace
 * policy will not let a web app be shared outside the organisation.
 *
 * It is a snapshot, not a live view: re-run it whenever you want fresh numbers.
 */
function exportStandalone() {
  requireSheetUser_();
  var payload = getPacingDashboardData();
  var html = HtmlService.createHtmlOutputFromFile('Dashboard').getContent();
  var stamp = Utilities.formatDate(new Date(), CFG.TZ, 'yyyy-MM-dd HH:mm');

  var banner = '<div style="background:#201e1d;color:#f8f4f4;padding:7px 18px;' +
    'font:600 11px Archivo,system-ui,sans-serif;letter-spacing:.06em">' +
    'SNAPSHOT · ' + payload.meta.start + ' → ' + payload.meta.end +
    ' · exported ' + stamp + ' · not live</div>';

  // The payload has to be parsed, not evaluated, so a stray character in a campaign
  // name can never become code. Every '<' in the script text is written as \u003c (and the JS
  // line separators U+2028/U+2029 escaped too): the text can then form neither '</script>',
  // which would close the tag early, nor '<!--<script', which would keep it from closing.
  // Inside the JS string literal \u003c reads back as '<', so the payload round-trips exactly.
  var json = JSON.stringify(payload);
  var inject = '<script>var EMBEDDED_PAYLOAD = JSON.parse(' +
    JSON.stringify(json).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029') +
    ');<\/script>';

  // Anchor on the opening tag only — the template carries attributes on it.
  var at = html.indexOf('<div id="app"');
  if (at < 0) throw new Error('Dashboard.html has no <div id="app"> to inject into.');
  html = html.slice(0, at) + inject + banner + html.slice(at);

  var name = 'Qiddiya Pacing ' + Utilities.formatDate(new Date(), CFG.TZ, 'yyyy-MM-dd HHmm') + '.html';
  var file = DriveApp.createFile(name, html, MimeType.HTML);
  Logger.log('Saved %s (%s KB)\n%s', name, Math.round(html.length / 1024), file.getUrl());
  try {
    SpreadsheetApp.getUi().alert('Saved to your Drive as\n\n' + name + '\n\n' +
      Math.round(html.length / 1024) + ' KB · opens in any browser, no Google account needed.\n\n' +
      file.getUrl());
  } catch (e) { /* no UI attached — the log has the link */ }
  return file.getUrl();
}
