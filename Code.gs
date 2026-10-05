/**
 * Qiddiya Media Pacing — dashboard server
 *
 * The dashboard is a second view of the two Pacing_Daily tabs, so it counts with the
 * pacing tabs' own rules: the same source cells, the same filters, the same line split,
 * the same date floors. Every rule is written down once, in this file:
 *
 *   PACING_LINES      which pacing row a platform × objective lands on, and its date floor
 *   OBJECTIVE_TOKENS  the campaign-name taxonomy (Raw data column M is generated from it)
 *   _adjustLine()     which pacing row an Adjust channel × objective lands on
 *   _ga4Bucket()      which pacing row a paid GA4 session lands on
 *
 * Untitled.gs generates the pacing formulas from the same definitions, so the tab and the
 * dashboard cannot drift apart again.
 *
 * Data problems (Adjust dates Sheets mis-parsed, overlapping Adjust imports, numbers
 * stored as text, campaigns with no portal) are fixed IN THE SHEET by "Clean Adjust Raw"
 * and the setup script — never patched silently inside the dashboard, because the pacing
 * tab would still be wrong. Until they are fixed the dashboard lists them in a banner.
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
  // Pacing row 24 (InMobi): Raw manual from 1 Sep, the Raw data backup for 2 Jul - 31 Aug.
  INMOBI_MANUAL_FROM: '2026-09-01',
  INMOBI_BACKUP_TILL: '2026-08-31',
  INMOBI_LAST_ROW: 10000,           // row 24 reads $A$2:$A$10000
  // Portal identifiers exactly as the pacing formulas test them.
  ADJUST_APP: { SFQC: 'Six Flags', AAQC: 'Aquarabia' },                           // Adjust Raw!D
  APPLE_APP: { SFQC: 'Six Flags Qiddiya City', AAQC: 'Aquarabia Qiddiya City' },  // APPLE1!B
  GA4_PROPERTY: { SFQC: 'six flags', AAQC: 'aquarabia' },                         // GA4!B "Six Flags*"
  // GA4: a session is paid when the default channel group is one of these two.
  PAID_GROUPS: ['paid search', 'paid social'],
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
 * once, not once per matching wildcard as the old SUMIFS sums did. Raw data column M is
 * generated from this table (Untitled.gs), so edit it here and re-run step 3.
 */
var OBJECTIVE_TOKENS = {
  Snapchat: {
    Awareness: ['snapchat_awr', '_awrn_', 'takeover', 'take over', 'take-over',
      'first story', 'first_story', 'first-story']
  },
  TikTok: {
    Awareness: ['tiktok_awr', '_awrn_'],
    Search: ['_tt_search', '_conv_sal_']
  },
  X: { Awareness: ['x_awr'] },
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
 * hatch if a deployment ever hands us nothing.
 */
function _ss() {
  if (CFG.SHEET_ID) {
    try {
      return SpreadsheetApp.openById(CFG.SHEET_ID);
    } catch (e) {
      throw new Error('CFG.SHEET_ID points at a spreadsheet this account cannot open (' +
        CFG.SHEET_ID + '). Either clear CFG.SHEET_ID so the script uses the sheet it is ' +
        'bound to, or share that spreadsheet with ' + _who() + '.');
    }
  }
  var ss = SpreadsheetApp.getActive();
  if (!ss) {
    throw new Error('No spreadsheet in scope. Bind this script to the sheet (Extensions → ' +
      'Apps Script from inside it), or set CFG.SHEET_ID to a sheet ' + _who() + ' can open.');
  }
  return ss;
}
function _who() {
  try { return Session.getEffectiveUser().getEmail() || 'this account'; }
  catch (e) { return 'this account'; }
}

/**
 * Run this when something says PERMISSION_DENIED. It prints who the script is running
 * as, which spreadsheet it reached, and which tabs it can see.
 */
function checkSetup() {
  var out = [];
  out.push('Running as: ' + _who());
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
  [CFG.RAW, CFG.RAW_MANUAL, CFG.RAW_BACKUP, CFG.APPLE, CFG.ADJUST, CFG.GA4,
    CFG.PACING_TABS.SFQC, CFG.PACING_TABS.AAQC].forEach(function (n) {
    var sh = ss.getSheetByName(n);
    out.push((sh ? '  found  ' : '  MISSING ') + n + (sh ? ' · ' + sh.getLastRow() + ' rows' : ''));
  });
  var raw = ss.getSheetByName(CFG.RAW);
  if (raw) {
    var m1 = String(raw.getRange('M1').getValue()).trim();
    out.push('  Raw data column M: ' + (m1 === 'Objective' ? 'Objective (current formula)' :
      'missing — run Qiddiya Setup -> Fix this workbook'));
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
function _day(v, tz) {
  if (v instanceof Date) return Utilities.formatDate(v, tz || CFG.TZ, 'yyyy-MM-dd');
  return String(v || '').slice(0, 10);
}
/** A date criterion in SUMIFS only ever matches a real date cell, never text. */
function _dateCell(v, tz) {
  return v instanceof Date ? Utilities.formatDate(v, tz || CFG.TZ, 'yyyy-MM-dd') : '';
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
 * Source cells are never rewritten here. */
function _adjustReversedRows(rows, col, tz) {
  var marked = {};
  function nativeParts(v) {
    if (!(v instanceof Date)) return null;
    var p = _day(v, tz).split('-').map(Number);
    return { y: p[0], m: p[1], d: p[2], iso: _day(v, tz) };
  }
  function swapped(v) {
    var p = nativeParts(v);
    if (!p || p.d > 12) return '';
    return p.y + '-' + ('0' + p.d).slice(-2) + '-' + ('0' + p.m).slice(-2);
  }
  function nextDay(iso) {
    var p = iso.split('-').map(Number);
    var d = new Date(Date.UTC(p[0], p[1] - 1, p[2] + 1));
    return Utilities.formatDate(d, 'UTC', 'yyyy-MM-dd');
  }

  // An unambiguous text day (13–31) anchors the native Date block immediately
  // before it. Every member of that block has day == the text month.
  for (var i = 1; i < rows.length; i++) {
    if (typeof rows[i][col] !== 'string') continue;
    var a = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(rows[i][col].trim());
    if (!a || +a[1] <= 12) continue;
    var targetMonth = +a[2], targetYear = +a[3];
    for (var k = i - 1; k >= 1; k--) {
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
      var cur = nativeParts(rows[r][col]);
      if (!cur || cur.y !== first.y || cur.d !== first.d) break;
      months[cur.m] = 1;
      if (cur.m < lastMonth) ordered = false;
      lastMonth = cur.m;
      r++;
    }
    if (ordered && Object.keys(months).length >= 3)
      for (var q = start; q < r; q++) marked[q] = true;
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
/** Column index (1-based) of a header, or 0. */
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

/** Platform + campaign -> objective. Fallback only: Raw data column M is authoritative. */
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

  /* ---- window: SFQC Pacing_Daily B2:C2, the same window Raw data N2:O2 follows ---- */
  var pac = ss.getSheetByName(CFG.PACING);
  var from = pac ? _day(pac.getRange('B2').getValue(), tz) : '';
  var till = pac ? _day(pac.getRange('C2').getValue(), tz) : '';
  var aPac = ss.getSheetByName(CFG.PACING_TABS.AAQC);
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

  /* ---- Raw data (rows 7-21, 23, 25): A platform, B portal, C campaign, D day, E reach,
          F impressions, G spend, H link clicks, I clicks, J views, K installs, L purchases,
          M objective ---- */
  var rv = _sheet(CFG.RAW).getDataRange().getValues();
  var rawHdr = rv[0] || [];
  var hasObjective = String(rawHdr[12] == null ? '' : rawHdr[12]).trim().toLowerCase() === 'objective';
  if (!hasObjective) {
    issue('warn', 'Raw data has no Objective column (M), so this dashboard is splitting campaigns ' +
      'into lines itself while the pacing tab still uses its old wildcard sums. Run Qiddiya Setup → ' +
      'Fix this workbook once; after that both read the same column.');
  }
  var unmapped = { spend: 0, names: {} }, offLine = {}, rawBadDates = 0;
  for (var i = 1; i < rv.length; i++) {
    var r = rv[i];
    if (r[0] === '' || r[0] === null) continue;
    var day = _dateCell(r[3], tz);
    if (!day) { rawBadDates++; continue; }
    if (!inWindow(day)) continue;
    var plat = _canonPlat(r[0]);
    var camp = String(r[2] == null ? '' : r[2]);
    var brand = _brandCell(r[1]);
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
    var obj = hasObjective ? String(r[12] == null ? '' : r[12]) : _objective(plat, camp);
    var line = plat ? LINE_BY_KEY[plat + '|' + obj] : null;
    if (!line || line.source) {
      var ok = String(r[0]) + ' / ' + obj + ' / ' + brand;
      offLine[ok] = (offLine[ok] || 0) + spend;
      reconRow(brand, 'raw', day, r[5], r[6], 'offline');
      continue;
    }
    var floor = _mediaFloor(line, brand);
    if (floor && day < floor) { reconRow(brand, 'raw', day, r[5], r[6], 'prefloor'); continue; }
    reconRow(brand, 'raw', day, r[5], r[6], 'counted', false, plat === 'X' ? CFG.FX : 1);
    // X reports nothing in "Clicks (all)" — its pacing rows read link clicks (I9=J9, I20=J20)
    addRaw(line, brand, camp, day,
      [_cellNum(r[4]), _cellNum(r[5]), spend, _cellNum(r[7]),
       plat === 'X' ? _cellNum(r[7]) : _cellNum(r[8]),
       _cellNum(r[9]), _cellNum(r[10]), _cellNum(r[11])]);
  }
  if (unmapped.spend > 0.5) {
    var top = Object.keys(unmapped.names).sort(function (a, b) {
      return unmapped.names[b] - unmapped.names[a];
    }).slice(0, 5);
    issue('crit', money(unmapped.spend) + ' of Raw data spend in the window has no portal in column B ' +
      '(the campaign name carries neither an SFQC nor an AAQC token), so no pacing row and no dashboard ' +
      'line counts it. Largest: ' + top.join('; ') + '.');
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

  /* ---- Apple Ads (row 22) — APPLE1 by position: A date, B app, D spend, E impressions,
          F taps (clicks and link clicks), G installs. No views, no purchases. ---- */
  var appleLine = LINE_BY_KEY['Apple|Conversion'];
  var apv = _sheet(CFG.APPLE).getDataRange().getValues();
  var apHdr = apv[0] || [];
  _headerProblems(apHdr, APPLE_EXPECT, CFG.APPLE).forEach(function (p) {
    issue('crit', p + ' — pacing row 22 reads APPLE1 by position.');
  });
  var appleCampCol = _col(apHdr, 'Campaign Name') - 1;
  if (appleCampCol < 0) appleCampCol = 2;
  for (var ai = 1; ai < apv.length; ai++) {
    var ar = apv[ai];
    var appleBrand = _matchBrand(CFG.APPLE_APP, ar[1]);
    if (!appleBrand) continue;
    var appleDay = _dateCell(ar[0], tz);
    if (!inWindow(appleDay)) continue;
    if (appleDay < _mediaFloor(appleLine, appleBrand)) {
      reconRow(appleBrand, 'apple', appleDay, ar[4], ar[3], 'prefloor');
      continue;
    }
    reconRow(appleBrand, 'apple', appleDay, ar[4], ar[3], 'counted');
    var taps = _cellNum(ar[5]);
    addRaw(appleLine, appleBrand, String(ar[appleCampCol] == null ? '' : ar[appleCampCol]), appleDay,
      [0, _cellNum(ar[4]), _cellNum(ar[3]), taps, taps, 0, _cellNum(ar[6]), 0]);
  }

  /* ---- InMobi (row 24): Raw manual from 1 Sep, the Raw data backup for 2 Jul - 31 Aug,
          rows 2-10000, numbers parsed with VALUE(), exactly as the row's SUMPRODUCTs ---- */
  var inmobiLine = LINE_BY_KEY['InMobi|Conversion'];
  function readInMobi(sheetName, lo, hi, src) {
    var sh = ss.getSheetByName(sheetName);
    if (!sh) {
      issue('crit', 'Tab "' + sheetName + '" is missing — pacing row 24 (InMobi) reads it.');
      return;
    }
    var v = sh.getDataRange().getValues();
    var last = Math.min(v.length, CFG.INMOBI_LAST_ROW);
    for (var mi = 1; mi < last; mi++) {
      var mr = v[mi];
      var mb = _brandCell(mr[1]), md = _dateCell(mr[3], tz);
      if (!mb || !inWindow(md)) continue;
      if (String(mr[0] == null ? '' : mr[0]).toLowerCase() !== 'inmobi') {
        // Raw manual's other rows (Bidease) are copies of Raw data rows, which rows 23/25 read;
        // the backup's other rows are an old copy of Raw data and are not shown at all.
        if (src === 'manual') reconRow(mb, src, md, mr[5], mr[6], 'not_inmobi');
        continue;
      }
      var lower = _later(from, lo), upper = _sooner(loadTill, hi);
      if ((lower && md < lower) || (upper && md > upper)) {
        reconRow(mb, src, md, mr[5], mr[6], 'inmobi_out');
        continue;
      }
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

  /* ---- Adjust Raw (columns K, L, X): by position, like the formulas — A day, D app,
          E revenue, G paid installs, H installs, I bookings, J channel, K objective.
          Every row counts once per occurrence, as SUMIFS counts it; duplicates and
          unreadable dates are reported, and "Clean Adjust Raw" removes them for both. ---- */
  var ash = _sheet(CFG.ADJUST);
  var av = ash.getDataRange().getValues();
  _headerProblems(av[0] || [], ADJUST_EXPECT, CFG.ADJUST).forEach(function (p) {
    issue('crit', p + ' — the pacing formulas read Adjust Raw by position.');
  });
  var reversed = _adjustReversedRows(av, 0, tz);
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
     channels: the dashboard reads Adjust Raw through the same corrections "Clean Adjust Raw"
     writes into the tab, so its installs, bookings and revenue are right before the tab is
     cleaned. The pacing formulas still read the tab as it stands — the banner says by how much. */
  var tabAgg = aAgg, cleanLog = null, adjRecon = {};
  // the "Check it against the tabs" table: every Adjust Raw row by what happens to it
  function adjTally(b, d, k, v) {
    var key = b + '|' + d + '|' + k;
    var e = adjRecon[key] || (adjRecon[key] = { b: b, d: d, k: k, i: 0, o: 0, r: 0, n: 0 });
    e.i += _cellNum(v[7]); e.o += _cellNum(v[8]); e.r += _cellNum(v[4]); e.n++;
  }
  if (!asTab) {
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
  var fixHint = ' Run Pacing dashboard → Clean Adjust Raw: it repairs the tab both the pacing ' +
    'formulas and this dashboard read (a backup and a change log are kept).';
  var needsClean = cleanLog && cleanLog.some(function (r) {
    return /Text date|swap|Duplicate|Number stored as text|Twitter|Missing channel|replaced|folded/.test(r[1]);
  });
  if (needsClean) {
    var kinds = {};
    cleanLog.forEach(function (r) {
      var k = /Text date/.test(r[1]) ? 'text' : /swap/.test(r[1]) ? 'swap' : /Duplicate/.test(r[1]) ? 'dup'
        : /Number stored as text/.test(r[1]) ? 'num' : /Twitter|Missing channel/.test(r[1]) ? 'label'
        : /replaced|folded/.test(r[1]) ? 'legacy' : '';
      if (k) kinds[k] = (kinds[k] || 0) + 1;
    });
    var parts = [];
    if (kinds.text) parts.push(count(kinds.text) + ' days stored as text (e.g. 13/09/2026)');
    if (kinds.swap) parts.push(count(kinds.swap) + ' day/month-swapped dates');
    if (kinds.dup) parts.push(count(kinds.dup) + ' rows repeated by overlapping imports');
    if (kinds.num) parts.push(count(kinds.num) + ' numbers stored as text');
    if (kinds.label) parts.push(count(kinds.label) + ' rows with a missing or wrong channel');
    if (legacyRows) parts.push(count(legacyRows) + ' rows still in "' + CFG.ADJUST_LEGACY + '"');
    // what the pacing tabs show for their own dates, against the corrected figures
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
    issue('crit', 'Adjust Raw needs cleaning: ' + parts.join(', ') + '. This dashboard corrects them as ' +
      'it reads the tab, so the Adjust installs, bookings and revenue shown here are right. The pacing ' +
      'tabs read the tab as it stands' + (cmp.length ? ' and show ' + cmp.join('; ') + ' for ' +
      from + ' → ' + till : '') + '. Run Pacing dashboard → Clean Adjust Raw once (Qiddiya Setup → ' +
      'Fix this workbook includes it) and the tabs will match.');
  } else if (textDates && !cleanLog) {
    issue('crit', count(textDates) + ' Adjust Raw rows hold their day as text (e.g. 13/09/2026). ' +
      'SUMIFS cannot read a text date, so neither the pacing tab nor this dashboard counts their ' +
      'installs, bookings or revenue.' + fixHint);
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
          F source / medium, G transactions, H revenue ---- */
  var gv = _sheet(CFG.GA4).getDataRange().getValues();
  _headerProblems(gv[0] || [], GA4_EXPECT, CFG.GA4).forEach(function (p) {
    issue('crit', p + ' — the pacing formulas read GA4 by position.');
  });
  var gMap = {};
  for (var k = 1; k < gv.length; k++) {
    var g = gv[k];
    var gBrand = _ga4Brand(g[1]);
    if (!gBrand) continue;
    if (CFG.PAID_GROUPS.indexOf(String(g[4] == null ? '' : g[4]).toLowerCase()) < 0) continue;
    var gd = _dateCell(g[2], tz);
    if (!inWindow(gd)) continue;
    var bucket = _ga4Bucket(g[5], g[3]);
    var gci = _campIndex(g[3]);
    var gk = [gBrand, bucket, gd, gci].join('\u0001');
    var ge = gMap[gk] || (gMap[gk] = { brand: gBrand, bucket: bucket, line: GA4_LINE[bucket],
      day: gd, ci: gci, tx: 0, revenue: 0 });
    ge.tx += _cellNum(g[6]);
    ge.revenue += _cellNum(g[7]);
  }
  var ga4 = Object.keys(gMap).map(function (key) {
    var e = gMap[key];
    e.revenue = Math.round(e.revenue * 100) / 100;
    return e;
  });

  /* ---- lines that spend but whose channel never appears in Adjust Raw at all ---- */
  var noAdjustFeed = {};
  raw.forEach(function (row) {
    if (row[6] > 0 && !channelsSeen[row[1] + '|' + row[0]]) noAdjustFeed[row[1] + '|' + row[0]] = 1;
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
      'the tabs, type a later date into SFQC C2 (Qiddiya Setup → Fix this workbook sets it to yesterday).');
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
      health: { issues: issues, noAdjustFeed: Object.keys(noAdjustFeed).sort() },
      sourceCoverage: {
        media: _coverageValues(mediaCoverage),
        adjust: _coverageValues(adjustCoverage),
        ga4: _coverageValues(ga4Coverage)
      },
      generated: 'Refreshed ' + Utilities.formatDate(new Date(), CFG.TZ, 'yyyy-MM-dd HH:mm')
    },
    raw: raw, adjust: adjust, ga4: ga4, camps: _campList,
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
  var ss = _ss();
  // Lines: the dashboard's counting against the formulas, both reading Adjust Raw as it stands.
  // Data quality: what the dashboard banner says (including how far the tabs are off).
  var p = getPacingDashboardData({ asTab: true });
  var shown = getPacingDashboardData();
  var out = [], bad = 0, total = 0;
  function row(a, b, c, d, e, f) { out.push([a, b, c, d, e, f]); }
  function cmp(brand, line, metric, dash, pacing) {
    total++;
    var diff = dash - pacing;
    var ok = Math.abs(diff) <= Math.max(0.02, Math.abs(pacing) * 0.0005);
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
    cmp(brand, 'Total', 'ROAS (P28)', sum.spend ? sum.revenue / (sum.spend * CFG.FX) : 0, cell(28, 16));
    var gaTx = 0, gaRev = 0;
    p.ga4.forEach(function (g) {
      if (g.brand === brand && g.day >= rep.start && g.day <= rep.end) { gaTx += g.tx; gaRev += g.revenue; }
    });
    cmp(brand, 'GA4 paid', 'Transactions (C49)', gaTx, cell(49, 3));
    cmp(brand, 'GA4 paid', 'Revenue (D49)', gaRev, cell(49, 4));
    cmp(brand, 'Check block', 'Spend not on a line (C41)', 0, cell(41, 3));
  });

  var issues = shown.meta.health.issues;
  row('', '', '', '', '', '');
  row('DATA QUALITY', issues.length ? issues.length + ' issue(s)' : 'no issues', '', '', '', '');
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
  var msg = (bad === 0 ? 'All ' + total + ' figures match the pacing tabs.' :
      bad + ' of ' + total + ' figures differ — see the "Dashboard Validation" tab. If the totals ' +
      'row or whole lines differ, run Qiddiya Setup → Fix this workbook first.') +
    (critical ? '\n\n' + critical + ' data issue(s) affect BOTH the pacing tab and the dashboard — ' +
      'listed at the bottom of the tab.' : '');
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
 * to fill blanks; existing labels in Adjust Raw are never overwritten by it, except the
 * Twitter rows the old export filed under Other.
 */
function _adjustClassify(network, campaign) {
  var n = String(network == null ? '' : network).trim();
  if (/\borganic\b/i.test(n)) return { channel: 'Organic', objective: 'Organic' };
  var ch = /^Snapchat/i.test(n) ? 'Snapchat'
    : /^(Facebook|Instagram|Off-Facebook|Meta|Audience Network|Messenger)\b/i.test(n) ? 'Meta'
    : /^Apple Search Ads/i.test(n) ? 'Apple'
    : /^(Google|YouTube|AdWords)/i.test(n) ? 'Google'
    : /^Bidease/i.test(n) ? 'Bidease'
    : /^InMobi/i.test(n) ? 'InMobi'
    : /^InMotion/i.test(n) ? 'InMotion'
    : /^(Twitter|X Ads|X)\b/i.test(n) ? 'X'
    : /^TikTok/i.test(n) ? 'TikTok'
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
function _stamp() { return Utilities.formatDate(new Date(), CFG.TZ, 'yyyyMMdd-HHmm'); }

/**
 * Reads Adjust Raw into clean rows: real ISO days (text dd/MM and Sheets' day/month swaps
 * repaired), numbers as numbers, trimmed labels, blanks classified. Nothing is written.
 */
function _adjustReadClean_(sh, tz, log) {
  var range = sh.getDataRange();
  var values = range.getValues(), display = range.getDisplayValues(), formulas = range.getFormulas();
  var header = values[0] || [];
  var problems = _headerProblems(header, ADJUST_EXPECT, CFG.ADJUST);
  if (problems.length) {
    throw new Error(problems.join('\n') + '\n\nThe pacing formulas read Adjust Raw by position, so ' +
      'the columns must be in this order: ' + ADJUST_LAYOUT.join(', ') + '.');
  }
  for (var fr = 1; fr < formulas.length; fr++) {
    for (var fc = 0; fc < formulas[fr].length; fc++) {
      if (formulas[fr][fc]) {
        throw new Error('Adjust Raw has a formula in row ' + (fr + 1) + ', column ' +
          String.fromCharCode(65 + fc) + '. The cleaner only rewrites a values-only export.');
      }
    }
  }
  var width = Math.max(header.length, ADJUST_LAYOUT.length);
  var reversed = _adjustReversedRows(values, 0, tz);
  var rows = [];
  for (var j = 1; j < values.length; j++) {
    var v = values[j].slice();
    while (v.length < width) v.push('');
    if (v.every(_blank)) continue;
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
    if (/^Twitter Installs$/i.test(String(v[1])) && (_blank(v[9]) || /^other$/i.test(String(v[9])))) {
      var tw = _adjustClassify(v[1], v[2]);
      log.push([j + 1, 'Twitter Installs moved from "' + v[9] + '" to channel X', v[9] + ' / ' + v[10],
        tw.channel + ' / ' + tw.objective]);
      v[9] = tw.channel; v[10] = tw.objective;
    } else if (_blank(v[9]) || _blank(v[10])) {
      var cls = _adjustClassify(v[1], v[2]);
      log.push([j + 1, 'Missing channel/objective filled', v[9] + ' / ' + v[10],
        (_blank(v[9]) ? cls.channel : v[9]) + ' / ' + (_blank(v[10]) ? cls.objective : v[10])]);
      if (_blank(v[9])) v[9] = cls.channel;
      if (_blank(v[10])) v[10] = cls.objective;
    }
    rows.push({ v: v, day: iso, dateFixed: dateFixed });
  }
  return { header: header, width: width, rows: rows };
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

/** Replace, per app, every row whose day falls inside the incoming rows' date range. */
function _adjustUpsert_(data, incoming, label, log) {
  var ranges = {};
  incoming.forEach(function (r) {
    var app = String(r[3]).toLowerCase();
    var e = ranges[app] || (ranges[app] = { min: r[0], max: r[0] });
    if (r[0] < e.min) e.min = r[0];
    if (r[0] > e.max) e.max = r[0];
  });
  var replaced = 0;
  data.rows = data.rows.filter(function (row) {
    if (!row.day) return true;
    var e = ranges[String(row.v[3]).toLowerCase()];
    if (e && row.day >= e.min && row.day <= e.max) { replaced++; return false; }
    return true;
  });
  incoming.forEach(function (r) {
    var v = r.slice();
    while (v.length < data.width) v.push('');
    data.rows.push({ v: v, day: v[0] });
  });
  Object.keys(ranges).forEach(function (app) {
    log.push(['', label + ': ' + app + ' ' + ranges[app].min + ' → ' + ranges[app].max +
      ' replaced', '', '']);
  });
  return { replaced: replaced, added: incoming.length, ranges: ranges };
}

function _backupValues(ss, sh, name) {
  var rows = Math.max(1, sh.getLastRow()), cols = Math.max(1, sh.getLastColumn());
  var values = sh.getRange(1, 1, rows, cols).getValues();
  var old = ss.getSheetByName(name);
  if (old) ss.deleteSheet(old);
  var dst = ss.insertSheet(name, ss.getSheets().length);
  if (dst.getMaxColumns() < cols) dst.insertColumnsAfter(dst.getMaxColumns(), cols - dst.getMaxColumns());
  if (dst.getMaxRows() < rows) dst.insertRowsAfter(dst.getMaxRows(), rows - dst.getMaxRows());
  dst.getRange(1, 1, rows, cols).setValues(values);
  dst.hideSheet();
  return dst;
}

function _adjustWrite_(sh, data) {
  data.rows.sort(function (a, b) {
    if (!a.day !== !b.day) return a.day ? -1 : 1;              // unreadable rows go last
    var ka = [a.day, String(a.v[3]), String(a.v[1]), String(a.v[2])].join('\u0001');
    var kb = [b.day, String(b.v[3]), String(b.v[1]), String(b.v[2])].join('\u0001');
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
  var out = data.rows.map(function (r) { return r.v.slice(0, data.width); });
  var last = sh.getLastRow();
  if (last > 1) sh.getRange(2, 1, last - 1, Math.max(data.width, sh.getLastColumn())).clearContent();
  if (!out.length) return 0;
  if (sh.getMaxRows() < out.length + 1) sh.insertRowsAfter(sh.getMaxRows(), out.length + 1 - sh.getMaxRows());
  // Labels are stored as plain text so a campaign name can never be re-read as a date or
  // a formula; the day is written as yyyy-mm-dd, which every locale reads as a real date.
  [2, 3, 4, 10, 11].forEach(function (c) { sh.getRange(2, c, out.length, 1).setNumberFormat('@'); });
  sh.getRange(2, 1, out.length, 1).setNumberFormat('yyyy-mm-dd');
  sh.getRange(2, 1, out.length, data.width).setValues(out);
  return out.length;
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
  var data = _adjustReadClean_(sh, tz, log);
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
  var dropped = _adjustDedupe_(data, log);
  return { data: data, merged: merged, legacy: legacy, dropped: dropped };
}

/**
 * Repairs Adjust Raw in place so the pacing formulas and the dashboard both read it
 * correctly: text and day/month-swapped dates become real dates, overlapping imports are
 * de-duplicated, numbers stored as text become numbers, Twitter Installs move from Other to
 * X, and any rows left in the old "Adjust Current" tab are folded in. A values-only backup
 * and a line-by-line log are written first. Safe to run as often as you like.
 */
function cleanAdjustRaw() {
  var msg = cleanAdjustRaw_();
  try { SpreadsheetApp.getUi().alert(msg); } catch (e) { /* no UI attached */ }
  return msg;
}

/** cleanAdjustRaw() without the dialog, so "Fix this workbook" can run it as one step. */
function cleanAdjustRaw_() {
  var lock = LockService.getDocumentLock();
  lock.waitLock(30000);
  try {
    var ss = _ss(), tz = ss.getSpreadsheetTimeZone(), stamp = _stamp();
    var sh = _sheet(CFG.ADJUST), log = [];
    var before = Math.max(0, sh.getLastRow() - 1);
    var cd = _adjustCleanData_(ss, sh, tz, log);
    var data = cd.data, merged = cd.merged, legacy = cd.legacy, dropped = cd.dropped;
    _backupValues(ss, sh, CFG.ADJUST + ' BACKUP ' + stamp);
    var after = _adjustWrite_(sh, data);
    if (merged) legacy.setName(CFG.ADJUST_LEGACY + ' (merged ' + stamp + ')').hideSheet();
    var fixedDates = log.filter(function (r) { return /date|swap/i.test(r[1]) && r[3] !== ''; }).length;
    var unreadable = log.filter(function (r) { return /not readable/.test(r[1]); }).length;
    var msg = 'Adjust Raw cleaned: ' + before + ' rows in, ' + after + ' rows out.\n' +
      '· ' + fixedDates + ' dates repaired' + (unreadable ? ', ' + unreadable + ' still unreadable (see log)' : '') + '\n' +
      '· ' + dropped + ' duplicate rows removed\n' +
      (merged ? '· ' + merged.added + ' rows folded in from "' + CFG.ADJUST_LEGACY + '" (' +
        merged.replaced + ' older rows for the same days replaced)\n' : '') +
      'Backup: "' + CFG.ADJUST + ' BACKUP ' + stamp + '". Every change is listed in "Adjust Raw cleanup log".';
    _writeLog(ss, 'Clean Adjust Raw · ' + stamp, log);
    SpreadsheetApp.flush();
    Logger.log(msg);
    return msg;
  } finally {
    lock.releaseLock();
  }
}

/** Called by the import dialog with one parsed table per CSV file. */
function importAdjustCsv(files) {
  if (!files || !files.length) throw new Error('No CSV data received.');
  var required = ['day', 'network', 'campaign_network', 'app', 'all_revenue', 'paid_installs',
    'installs', 'bookingconfirmed_events'];
  var sums = {}, order = [], apps = {};
  files.forEach(function (table, fileIndex) {
    if (!table || table.length < 2) throw new Error('CSV ' + (fileIndex + 1) + ' is empty.');
    var header = table[0].map(function (x) { return String(x || '').replace(/^﻿/, '').trim(); });
    var pos = {}; header.forEach(function (x, i) { pos[x] = i; });
    required.forEach(function (x) {
      if (pos[x] == null) throw new Error('CSV ' + (fileIndex + 1) + ' is missing "' + x + '".');
    });
    table.slice(1).forEach(function (r, ri) {
      var app = String(r[pos.app] || '').trim();
      if (!_matchBrand(CFG.ADJUST_APP, app)) return;
      var day = String(r[pos.day] || '').trim();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) {
        throw new Error('CSV ' + (fileIndex + 1) + ' row ' + (ri + 2) + ': day "' + day +
          '" is not yyyy-mm-dd. Export from Adjust again without opening the file in Excel first.');
      }
      var network = String(r[pos.network] || '').trim();
      var campaign = String(r[pos.campaign_network] || '').trim();
      var cls = _adjustClassify(network, campaign);
      apps[app] = true;
      // Within one export a repeated key is a further breakdown (OS, country) of the same
      // day — those rows are added together, never de-duplicated.
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
  });
  var incoming = order.map(function (k) { return sums[k]; });
  if (!incoming.length) throw new Error('No Six Flags or Aquarabia rows were found.');

  var lock = LockService.getDocumentLock();
  lock.waitLock(30000);
  try {
    var ss = _ss(), tz = ss.getSpreadsheetTimeZone(), stamp = _stamp(), log = [];
    var sh = ss.getSheetByName(CFG.ADJUST);
    if (!sh) {
      sh = ss.insertSheet(CFG.ADJUST);
      sh.getRange(1, 1, 1, ADJUST_LAYOUT.length).setValues([ADJUST_LAYOUT]).setFontWeight('bold');
      sh.setFrozenRows(1);
    }
    var data = _adjustReadClean_(sh, tz, log);
    var res = _adjustUpsert_(data, incoming, 'Import', log);
    var dropped = _adjustDedupe_(data, log);
    if (sh.getLastRow() > 1) _backupValues(ss, sh, CFG.ADJUST + ' BACKUP ' + stamp);
    var total = _adjustWrite_(sh, data);
    _writeLog(ss, 'Adjust import · ' + stamp, log);
    SpreadsheetApp.flush();
    return 'Imported ' + res.added + ' rows for ' + Object.keys(apps).join(' + ') + ' (' +
      Object.keys(res.ranges).map(function (a) { return a + ' ' + res.ranges[a].min + ' → ' + res.ranges[a].max; })
        .join(', ') + '), replacing ' + res.replaced + ' older rows for those days' +
      (dropped ? ' and ' + dropped + ' duplicates elsewhere' : '') + '.\nAdjust Raw now has ' + total +
      ' rows. The pacing tabs have recalculated; press Refresh on the dashboard.';
  } finally {
    lock.releaseLock();
  }
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
  var payload = getPacingDashboardData();
  var html = HtmlService.createHtmlOutputFromFile('Dashboard').getContent();
  var stamp = Utilities.formatDate(new Date(), CFG.TZ, 'yyyy-MM-dd HH:mm');

  var banner = '<div style="background:#201e1d;color:#f8f4f4;padding:7px 18px;' +
    'font:600 11px Archivo,system-ui,sans-serif;letter-spacing:.06em">' +
    'SNAPSHOT · ' + payload.meta.start + ' → ' + payload.meta.end +
    ' · exported ' + stamp + ' · not live</div>';

  // The payload has to be parsed, not evaluated, so a stray character in a campaign
  // name can never become code. </script> inside a string would close the tag early.
  var json = JSON.stringify(payload).split('<\/').join('<\\/');
  var inject = '<script>var EMBEDDED_PAYLOAD = JSON.parse(' +
    JSON.stringify(json).split('<\/').join('<\\/') + ');<\/script>';

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
