/**
 * Qiddiya Media Pacing — dashboard server
 *
 * Feeds "Qiddiya Pacing Dashboard" from the same source tabs the pacing sheets read:
 * Raw data, Raw manual/history, APPLE1, Adjust Raw and GA4. Campaign objective
 * classification lives in OBJECTIVE_TOKENS and is attached to each raw row before
 * it reaches the browser. Run validateDashboard() after any source/formula change;
 * it reconciles the payload against both pacing tabs line by line.
 *
 * Column positions are resolved from the header row where the layout allows it, so a
 * Supermetrics refresh that adds a metric will not silently shift a number.
 */

var CFG = {
  RAW: 'Raw data',
  RAW_MANUAL: 'Raw manual',
  RAW_BACKUP: 'Raw data BACKUP 20260807-1642',
  APPLE: 'APPLE1',
  ADJUST: 'Adjust Raw',
  // Clean, replace-in-place snapshot populated by "Import latest Adjust CSVs".
  // The dashboard prefers it over the append-only Adjust Raw archive.
  ADJUST_CURRENT: 'Adjust Current',
  GA4: 'GA4',
  PACING: 'SFQC Pacing_Daily',      // holds the window in B2:C2
  // LEAVE THIS BLANK unless you know you need it. A bound script finds its own
  // spreadsheet. If you do fill it in, it must be a sheet the account running the
  // script can open — pointing it at a sheet on another account is what produces
  // PERMISSION_DENIED.
  SHEET_ID: '',
  FX: 3.78,                         // SAR per USD — matches column F on the pacing tabs
  TZ: 'Asia/Riyadh',
  // Date floors, copied line by line off the pacing formulas. They are not uniform:
  // the awareness rows carry none, TikTok Search and TikTok App carry none either,
  // Meta starts a day earlier, and the rest start 2 Jul. Without these the dashboard
  // picks up the pre-launch SKAN tail (installs on days with no spend) that the
  // report leaves out. Key is "platform|objective"; anything unlisted has no floor.
  FLOOR: {
    'Snapchat|Conversion': '2026-07-02',
    'Google|Search':       '2026-07-02',
    'Google|Conversion':   '2026-07-02',
    'Meta|Conversion':     '2026-07-01',
    'X|Conversion':        '2026-07-02',
    'Apple|Conversion':    '2026-07-02',
    'Bidease|Conversion':  '2026-07-02',
    'InMobi|Conversion':   '2026-07-02',
    'InMotion|Conversion': '2026-07-02'
  },
  // Adjust rows follow the same idea: awareness and YouTube unfloored, the rest from 2 Jul.
  ADJUST_FROM: '2026-07-02',
  PROPERTY_OF: { 'Six Flags Qiddiya City': 'SFQC', 'Aquarabia Qiddiya City': 'AAQC' },
  // GA4: the pacing formulas count a session as paid when the default channel group is
  // one of these two. Nothing else qualifies, whatever the medium says.
  PAID_GROUPS: ['Paid Search', 'Paid Social']
};

/*
 * One authoritative campaign taxonomy for platform delivery rows.
 * The server writes the chosen objective onto every raw row, so the browser does
 * not have to classify the same campaign a second time. Keep source-name variants
 * here; do not scatter new wildcards through the dashboard.
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
 * NOTE: install.gs already defines onOpen(). Apps Script keeps only the last
 * definition in a project, so this file must not define one too — install.gs calls
 * dashboardMenu_() instead, and both menus appear.
 */
function dashboardMenu_() {
  SpreadsheetApp.getUi().createMenu('Pacing dashboard')
    .addItem('Open', 'showDashboard')
    .addItem('Import latest Adjust CSVs', 'showAdjustImporter')
    .addItem('Validate against the pacing tabs', 'validateDashboard')
    .addItem('Export a standalone HTML file', 'exportStandalone')
    .addSeparator()
    .addItem('Check the setup', 'checkSetup')
    .addToUi();
}

/**
 * Imports one or both current Adjust CSV exports without touching Adjust Raw.
 * Each app contained in the selected files is replaced atomically in Adjust Current,
 * while the other app is preserved. Data refreshes therefore never need a deployment.
 */
function showAdjustImporter() {
  var html = HtmlService.createHtmlOutput([
    '<!doctype html><meta charset="utf-8"><style>',
    'body{font:14px Arial;padding:20px;color:#172033}h2{margin:0 0 8px}',
    'p{line-height:1.45;color:#58657a}input{display:block;margin:18px 0}',
    'button{background:#1677ff;color:white;border:0;border-radius:7px;padding:10px 16px;font-weight:700}',
    'button:disabled{opacity:.5}#s{margin-top:14px;white-space:pre-wrap}</style>',
    '<h2>Import latest Adjust exports</h2>',
    '<p>Select the latest Six Flags and Aquarabia CSV files together. Each app replaces only its previous snapshot; Adjust Raw stays unchanged.</p>',
    '<input id="f" type="file" accept=".csv,text/csv" multiple>',
    '<button id="b" onclick="go()">Import and refresh</button><div id="s"></div>',
    '<script>',
    'function csv(t){var out=[],r=[],v="",q=false;for(var i=0;i<t.length;i++){var c=t[i],n=t[i+1];if(q&&c===\'"\'&&n===\'"\'){v+=\'"\';i++;}else if(c===\'"\'){q=!q;}else if(!q&&c===","){r.push(v);v="";}else if(!q&&(c==="\\n"||c==="\\r")){if(c==="\\r"&&n==="\\n")i++;r.push(v);if(r.some(function(x){return x!==""}))out.push(r);r=[];v="";}else v+=c;}r.push(v);if(r.some(function(x){return x!==""}))out.push(r);return out;}',
    'async function go(){var fs=document.getElementById("f").files,b=document.getElementById("b"),s=document.getElementById("s");if(!fs.length){s.textContent="Choose at least one CSV.";return;}b.disabled=true;s.textContent="Reading files…";try{var all=[];for(var i=0;i<fs.length;i++)all.push(csv(await fs[i].text()));google.script.run.withSuccessHandler(function(x){s.textContent=x;b.disabled=false;}).withFailureHandler(function(e){s.textContent="Import failed: "+e.message;b.disabled=false;}).replaceAdjustCurrent(all);}catch(e){s.textContent=e.message;b.disabled=false;}}',
    '</script>'
  ].join('')).setWidth(560).setHeight(330);
  SpreadsheetApp.getUi().showModalDialog(html, 'Adjust current snapshot');
}

function _adjustImportedClass(network, campaign) {
  var n = String(network || '').trim();
  if (/^Organic$/i.test(n)) return { channel: 'Organic', objective: 'Organic' };
  if (/^Snapchat Installs$/i.test(n)) return { channel: 'Snapchat', objective: 'Conversion' };
  if (/^(Facebook|Instagram|Off-Facebook) Installs$/i.test(n)) return { channel: 'Meta', objective: 'Conversion' };
  if (/^Apple Search Ads$/i.test(n)) return { channel: 'Apple', objective: 'Conversion' };
  if (/^Google Ads Search$/i.test(n)) return { channel: 'Google', objective: 'Search' };
  if (/^Google Ads /i.test(n)) return { channel: 'Google', objective: 'Conversion' };
  if (/^Bidease/i.test(n)) return { channel: 'Bidease', objective: 'Conversion' };
  if (/^InMobi/i.test(n)) return { channel: 'InMobi', objective: 'Conversion' };
  if (/^InMotion/i.test(n)) return { channel: 'InMotion', objective: 'Conversion' };
  if (/^Twitter Installs$/i.test(n)) return { channel: 'X', objective: 'Conversion' };
  if (/^TikTok SAN$/i.test(n)) {
    return { channel: 'TikTok', objective: /(?:_tt_search|_conv_sal_)/i.test(campaign) ? 'Search' :
      /(?:tiktok_awr|_awrn_)/i.test(campaign) ? 'Awareness' : 'Conversion' };
  }
  return { channel: 'Other', objective: 'Conversion' };
}

function replaceAdjustCurrent(files) {
  if (!files || !files.length) throw new Error('No CSV data received.');
  var required = ['day','network','campaign_network','app','all_revenue','paid_installs',
    'installs','bookingconfirmed_events'];
  var outputHeader = ['day','network','campaign_network','app','all_revenue',
    'general revenue_revenue_est','paid_installs','installs','bookingconfirmed_events',
    'channel','objective'];
  var incoming = [], apps = {};
  files.forEach(function (table, fileIndex) {
    if (!table || table.length < 2) throw new Error('CSV ' + (fileIndex + 1) + ' is empty.');
    var header = table[0].map(function (x) { return String(x || '').replace(/^\uFEFF/, '').trim(); });
    var pos = {}; header.forEach(function (x, i) { pos[x] = i; });
    required.forEach(function (x) { if (pos[x] == null) throw new Error('CSV ' + (fileIndex + 1) + ' is missing "' + x + '".'); });
    table.slice(1).forEach(function (r) {
      var app = String(r[pos.app] || '').trim();
      if (app !== 'Six Flags' && app !== 'Aquarabia') return;
      var day = String(r[pos.day] || '').trim();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) throw new Error('Invalid Adjust date: ' + day);
      var network = String(r[pos.network] || '').trim();
      var campaign = String(r[pos.campaign_network] || '').trim();
      var cls = _adjustImportedClass(network, campaign);
      apps[app] = true;
      incoming.push([day, network, campaign, app,
        r[pos.all_revenue] || 0,
        pos['general revenue_revenue_est'] == null ? 0 : (r[pos['general revenue_revenue_est']] || 0),
        r[pos.paid_installs] || 0, r[pos.installs] || 0,
        r[pos.bookingconfirmed_events] || 0, cls.channel, cls.objective]);
    });
  });
  var importedApps = Object.keys(apps);
  if (!importedApps.length) throw new Error('No Six Flags or Aquarabia rows were found.');
  var ss = _ss(), sh = ss.getSheetByName(CFG.ADJUST_CURRENT);
  var preserved = [];
  if (sh && sh.getLastRow() > 1) {
    var old = sh.getDataRange().getValues(), oldHeader = old[0].map(String), appCol = oldHeader.indexOf('app');
    if (appCol >= 0) preserved = old.slice(1).filter(function (r) {
      return importedApps.indexOf(String(r[appCol] || '').trim()) < 0;
    });
  }
  if (!sh) sh = ss.insertSheet(CFG.ADJUST_CURRENT);
  sh.clearContents();
  var rows = [outputHeader].concat(preserved, incoming);
  sh.getRange(1, 1, rows.length, outputHeader.length).setValues(rows);
  sh.setFrozenRows(1);
  sh.getRange(2, 1, Math.max(1, rows.length - 1), 1).setNumberFormat('yyyy-mm-dd');
  SpreadsheetApp.flush();
  return 'Imported ' + incoming.length + ' rows for ' + importedApps.join(' + ') +
    '. Adjust Current now has ' + (rows.length - 1) + ' rows. The existing dashboard link will read them on Refresh.';
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
  ['Raw data','Raw manual','Raw data BACKUP 20260807-1642','APPLE1','Adjust Raw','GA4',
    'SFQC Pacing_Daily','AAQC Pacing_Daily'].forEach(function (n) {
    var sh = ss.getSheetByName(n);
    out.push((sh ? '  found  ' : '  MISSING ') + n + (sh ? ' · ' + sh.getLastRow() + ' rows' : ''));
  });
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
function _num(v) {
  if (v === null || v === undefined || v === '') return 0;
  var n = typeof v === 'number' ? v : parseFloat(String(v).replace(/[, ]/g, ''));
  return isNaN(n) ? 0 : n;
}
function _day(v, tz) {
  if (v instanceof Date) return Utilities.formatDate(v, tz || CFG.TZ, 'yyyy-MM-dd');
  return String(v || '').slice(0, 10);
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
function _adjustNumber(v, row, name) {
  if (v === null || v === undefined || v === '') return 0;
  if (typeof v === 'number' && isFinite(v)) return v;
  var s = String(v).replace(/[, ]/g, '');
  if (/^-?(?:\d+\.?\d*|\.\d+)$/.test(s)) return +s;
  throw new Error('Adjust Raw row ' + row + ': invalid ' + name + ' (' + String(v) + ').');
}
/** Adjust Raw can contain dd/MM/yyyy text beside dates auto-parsed as MM/dd/yyyy.
 * Interpret the export at read time; never rewrite its date cells. */
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
 * Source cells are never rewritten. */
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
      if (m) cursor = _adjustDay(value, j + 1, false, tz);
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
function _adjustChannel(network, channel) {
  // The imported classification labels Twitter Installs as Other in this export.
  // The campaign belongs on the X pacing line, not the unrelated Other bucket.
  if (/^Twitter Installs$/i.test(String(network || '').trim())) return 'X';
  return channel;
}
/** Column index (1-based) of a header, or 0. */
function _col(header, name) {
  for (var i = 0; i < header.length; i++) {
    if (String(header[i]).trim() === name) return i + 1;
  }
  return 0;
}
function _brandFromCampaign(campaign, fallback) {
  var c = String(campaign || '').toLowerCase();
  // First Story is the two SFQC Snapchat takeovers; the source export omits the
  // account dimension and leaves only this campaign label.
  if (c.indexOf('first story') >= 0) return 'SFQC';
  if (c.indexOf('sfqc') >= 0 || c.indexOf('six flags') >= 0 || c.indexOf('six_flags') >= 0)
    return 'SFQC';
  if (c.indexOf('aaqc') >= 0 || c.indexOf('aqc-') >= 0 || c.indexOf('aqc_') >= 0 ||
      c.indexOf('aqqc') >= 0 || c.indexOf('aquarabia') >= 0) return 'AAQC';
  return fallback === 'SFQC' || fallback === 'AAQC' ? fallback : '';
}
function _strictNumber(v, source, row, name) {
  if (v === null || v === undefined || v === '') return 0;
  if (typeof v === 'number' && isFinite(v)) return v;
  var s = String(v).replace(/[, ]/g, '');
  if (/^-?(?:\d+\.?\d*|\.\d+)$/.test(s)) return +s;
  throw new Error(source + ' row ' + row + ': invalid ' + name + ' (' + String(v) + ').');
}
function _cols(header, names, source) {
  var out = {};
  names.forEach(function (name) {
    out[name] = _col(header, name) - 1;
    if (out[name] < 0) throw new Error(source + ' is missing the required column "' + name + '".');
  });
  return out;
}

/**
 * Campaign names are the join between Raw data, Adjust and GA4, so they have to
 * travel with every Adjust and GA4 row. Sent verbatim they would be the largest
 * thing in the payload — the same 100-character string repeated thousands of
 * times — so each distinct name is stored once in payload.camps and the rows
 * carry its index. The client rehydrates them in one pass at boot.
 *
 * The index also keeps the grouping key safe: campaign names contain "|"
 * ("...Social_CU|Q3"), which would split a "|"-joined key into the wrong parts.
 * A number never can.
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

/**
 * iOS / Android / Web from the campaign name — the dashboard slices by this.
 * Mirrors osOf() in the template so the two never disagree.
 */
function _os(campaign) {
  var c = String(campaign || '').toLowerCase();
  if (c.indexOf('ios') >= 0 || c.indexOf('iphone') >= 0) return 'iOS';
  if (c.indexOf('android') >= 0 || c.indexOf('_and_') >= 0) return 'Android';
  return 'Web';
}

/**
 * Platform + campaign -> the pacing line the row belongs to. This server result is
 * appended to each raw row and is authoritative in the dashboard.
 */
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

/**
 * GA4 source/medium -> the bucket a pacing line reads.
 * Matches the wildcards in columns M and X of the pacing tabs:
 *   snap*  -> the SnapChat awareness line
 *   tiktok* with "search" in the campaign -> the TikTok Search line (TikTok-cpc)
 *   tiktok* otherwise                     -> the TikTok awareness line
 *   google*                               -> the Google Search line
 * Meta and X are collected too; the dashboard shows them in the GA4 table but the
 * pacing lines do not read them.
 */
function _bucket(sourceMedium, campaign) {
  var s = String(sourceMedium || '').toLowerCase();
  var c = String(campaign || '').toLowerCase();
  if (s.indexOf('snap') === 0 || s.indexOf('snap') >= 0) return 'Snapchat';
  if (s.indexOf('tiktok') === 0) return c.indexOf('search') >= 0 ? 'TikTok-cpc' : 'TikTok';
  if (s.indexOf('google') === 0) return 'Google';
  if (s.indexOf('instagram') === 0 || s.indexOf('facebook') === 0 ||
      s.indexOf('fb ') === 0 || s.indexOf('ig ') === 0 || s.indexOf('meta') === 0) return 'Meta';
  if (s.indexOf('x ') === 0 || s.indexOf('twitter') >= 0 || s.indexOf('t.co') >= 0) return 'X';
  return 'Other';
}

/* ------------------------------------------------------------------ payload */

function getPacingDashboardData() {
  var ss = _ss();
  var sourceTz = ss.getSpreadsheetTimeZone ? ss.getSpreadsheetTimeZone() : CFG.TZ;
  _campReset();
  var pac = ss.getSheetByName(CFG.PACING);
  var from = pac ? _day(pac.getRange('B2').getValue(), sourceTz) : '';
  var till = pac ? _day(pac.getRange('C2').getValue(), sourceTz) : '';

  /* ---- Raw data: A platform, B brand, C campaign, D day, E reach, F impressions,
          G spend, H link clicks, I clicks, J 3-sec views, K app installs, L purchases ---- */
  var rv = _sheet(CFG.RAW).getDataRange().getValues();
  var raw = [], dayset = {}, platset = {}, rawSeen = {}, rawCoverage = {};
  function addStd(plat, brand, camp, day, metrics) {
    if (!brand || !day) return;
    var key = plat + '|' + brand + '|' + String(camp || '').trim().toLowerCase() + '|' + day;
    if (rawSeen[key]) return;
    rawSeen[key] = 1; rawCoverage[plat + '|' + brand + '|' + day] = 1;
    // Index 12 is the server-owned objective. Older clients ignore it; the current
    // client uses it so campaign taxonomy cannot drift between server and browser.
    raw.push([plat, brand, _campIndex(camp), day].concat(metrics, [_objective(plat, camp)]));
    dayset[day] = 1; platset[plat] = 1;
  }
  for (var i = 1; i < rv.length; i++) {
    var r = rv[i];
    if (!r[0]) continue;
    var plat = String(r[0]).trim(), camp = String(r[2]).trim(), day = _day(r[3], sourceTz);
    // Apple is intentionally sourced from APPLE1 below. InMobi is intentionally
    // sourced from Raw manual below: Raw data only contains a partial SFQC slice and
    // no AAQC rows in the current workbook. Ignoring both here prevents double count.
    if (/^Apple(?: Ads)?$/i.test(plat) || plat === 'InMobi') continue;
    if (from && day && (day < from || day > till)) continue;
    // Mirror the date floor each pacing line carries, or the pre-launch SKAN tail
    // (installs and purchases on days with no spend) inflates the conversion rows.
    var floor = CFG.FLOOR[plat + '|' + _objective(plat, camp)];
    if (floor && day && day < floor) continue;
    // X is funded in SAR but reports into the USD column, exactly as the pacing rows divide it
    var spend = _num(r[6]) / (plat === 'X' ? CFG.FX : 1);
    // X reports nothing in "Clicks (all)" — the pacing rows read link clicks instead (I9=J9)
    var clicks = (plat === 'X') ? _num(r[7]) : _num(r[8]);
    // the name is interned like Adjust's and GA4's — it is the same 100-character
    // string on every one of a campaign's daily rows, and repeating it is by far
    // the largest thing in the payload
    addStd(plat, _brandFromCampaign(camp, String(r[1]).trim()), camp, day,
      [_num(r[4]), _num(r[5]), Math.round(spend * 10000) / 10000,
       _num(r[7]), clicks, _num(r[9]), _num(r[10]), _num(r[11])]);
  }

  /* Standardised history from the previous Raw data generation. It fills Jul/Aug
     days but never replaces the current Raw data rows above. */
  var bv = _sheet(CFG.RAW_BACKUP).getDataRange().getValues();
  for (var bi = 1; bi < bv.length; bi++) {
    var br = bv[bi], bp = String(br[0] || '').trim();
    if (!bp || bp === 'InMobi' || /^Apple(?: Ads)?$/i.test(bp)) continue;
    var bc = String(br[2] || '').trim(), bd = _day(br[3], sourceTz);
    if (from && bd && (bd < from || bd > till)) continue;
    var bf = CFG.FLOOR[bp + '|' + _objective(bp, bc)];
    if (bf && bd && bd < bf) continue;
    var bs = _num(br[6]) / (bp === 'X' ? CFG.FX : 1);
    addStd(bp, _brandFromCampaign(bc, String(br[1] || '').trim()), bc, bd,
      [_num(br[4]), _num(br[5]), Math.round(bs * 10000) / 10000,
       _num(br[7]), bp === 'X' ? _num(br[7]) : _num(br[8]),
       _num(br[9]), _num(br[10]), _num(br[11])]);
  }

  /* Native platform tabs fill only calendar days missing from both Raw data
     generations. This closes the Aug gap without double-counting Sep rows whose
     campaign labels were normalised upstream. */
  function nativeRows(sheetName, plat, required, mapper, campaignHeader) {
    var values = _sheet(sheetName).getDataRange().getValues();
    var cols = _cols(values[0] || [], required, sheetName);
    for (var ni = 1; ni < values.length; ni++) {
      var nr = values[ni], nc = String(nr[cols[campaignHeader || 'Campaign name']] || '').trim();
      var nd = _day(nr[cols.Date], sourceTz);
      if (!nc || !nd) continue;
      if (from && (nd < from || nd > till)) continue;
      var nf = CFG.FLOOR[plat + '|' + _objective(plat, nc)];
      if (nf && nd < nf) continue;
      var nb = _brandFromCampaign(nc, '');
      if (!nb) continue;
      // Coverage is portal-specific. A SFQC row on a day must not suppress a
      // missing AAQC row (or vice versa) from the native platform fallback.
      if (rawCoverage[plat + '|' + nb + '|' + nd]) continue;
      addStd(plat, nb, nc, nd, mapper(nr, cols, ni + 1));
    }
  }
  nativeRows('META', 'Meta', ['Date','Campaign name','Reach','Impressions','Cost',
    'Link clicks','Clicks (all)','Three-second video views','Mobile app installs','Mobile app purchases'],
    function (r, c, row) { return [
      _strictNumber(r[c.Reach], 'META', row, 'Reach'),
      _strictNumber(r[c.Impressions], 'META', row, 'Impressions'),
      _strictNumber(r[c.Cost], 'META', row, 'Cost'),
      _strictNumber(r[c['Link clicks']], 'META', row, 'Link clicks'),
      _strictNumber(r[c['Clicks (all)']], 'META', row, 'Clicks (all)'),
      _strictNumber(r[c['Three-second video views']], 'META', row, 'Three-second video views'),
      _strictNumber(r[c['Mobile app installs']], 'META', row, 'Mobile app installs'),
      _strictNumber(r[c['Mobile app purchases']], 'META', row, 'Mobile app purchases')];
    });
  nativeRows('Snapchat', 'Snapchat', ['Date','Campaign name','Impressions','Cost','Swipes',
    'Total app installs','Purchases','Video views'], function (r, c, row) { return [0,
      _strictNumber(r[c.Impressions], 'Snapchat', row, 'Impressions'),
      _strictNumber(r[c.Cost], 'Snapchat', row, 'Cost'), 0,
      _strictNumber(r[c.Swipes], 'Snapchat', row, 'Swipes'),
      _strictNumber(r[c['Video views']], 'Snapchat', row, 'Video views'),
      _strictNumber(r[c['Total app installs']], 'Snapchat', row, 'Total app installs'),
      _strictNumber(r[c.Purchases], 'Snapchat', row, 'Purchases')];
    });
  nativeRows('TikTok', 'TikTok', ['Date','Campaign name','Reach','Impressions','Cost','Clicks',
    'Clicks (All)','2-second video views','App installs','Purchase events','Purchase events (SKAN)',
    'Complete payment events'],
    function (r, c, row) {
      var purchases = _strictNumber(r[c['Purchase events']], 'TikTok', row, 'Purchase events') +
        _strictNumber(r[c['Purchase events (SKAN)']], 'TikTok', row, 'Purchase events (SKAN)') +
        _strictNumber(r[c['Complete payment events']], 'TikTok', row, 'Complete payment events');
      return [_strictNumber(r[c.Reach], 'TikTok', row, 'Reach'),
        _strictNumber(r[c.Impressions], 'TikTok', row, 'Impressions'),
        _strictNumber(r[c.Cost], 'TikTok', row, 'Cost'),
        _strictNumber(r[c.Clicks], 'TikTok', row, 'Clicks'),
        _strictNumber(r[c['Clicks (All)']], 'TikTok', row, 'Clicks (All)'),
        _strictNumber(r[c['2-second video views']], 'TikTok', row, '2-second video views'),
        _strictNumber(r[c['App installs']], 'TikTok', row, 'App installs'), purchases];
    });
  nativeRows('Google', 'Google', ['Date','Campaign name','Impressions','Cost','Clicks','Video views','Conversions'],
    function (r, c, row) {
      var conv = _strictNumber(r[c.Conversions], 'Google', row, 'Conversions');
      var name = String(r[c['Campaign name']] || '').toLowerCase();
      return [0, _strictNumber(r[c.Impressions], 'Google', row, 'Impressions'),
        _strictNumber(r[c.Cost], 'Google', row, 'Cost'), 0,
        _strictNumber(r[c.Clicks], 'Google', row, 'Clicks'),
        _strictNumber(r[c['Video views']], 'Google', row, 'Video views'),
        name.indexOf('uac') >= 0 || name.indexOf('app installs') >= 0 ? conv : 0, conv];
    });
  // X has duplicate "Installs" and "Purchases" headers; its established export
  // contract uses fixed columns T and W for the app metrics.
  nativeRows('X', 'X', ['Date','Campaign','Impressions','Cost','Clicks','Video views 3s'],
    function (r, c, row) { return [0,
      _strictNumber(r[c.Impressions], 'X', row, 'Impressions'),
      Math.round((_strictNumber(r[c.Cost], 'X', row, 'Cost') / CFG.FX) * 10000) / 10000,
      _strictNumber(r[c.Clicks], 'X', row, 'Clicks'), 0,
      _strictNumber(r[c['Video views 3s']], 'X', row, 'Video views 3s'),
      _strictNumber(r[19], 'X', row, 'Installs'),
      _strictNumber(r[22], 'X', row, 'Purchases')];
    }, 'Campaign');

  /* ---- InMobi history + Raw manual: same A:L schema as Raw data. Raw data is
          incomplete (only SFQC 1-10 Sep). The backup holds Jul/Aug history and Raw
          manual holds the maintained Sep rows for both properties. Merge by
          brand+campaign+day and let Raw manual win if the same day exists in both,
          so refreshing or extending either source cannot double count. ---- */
  var imRows = {};
  function collectInMobi(values, priority) {
    for (var mi = 1; mi < values.length; mi++) {
      var mr = values[mi];
      if (String(mr[0] || '').trim() !== 'InMobi') continue;
      var manualBrand = String(mr[1] || '').trim();
      if (manualBrand !== 'SFQC' && manualBrand !== 'AAQC') continue;
      var manualCamp = String(mr[2] || '').trim();
      var manualDay = _day(mr[3], sourceTz);
      if (from && manualDay && (manualDay < from || manualDay > till)) continue;
      var manualFloor = CFG.FLOOR['InMobi|Conversion'];
      if (manualFloor && manualDay && manualDay < manualFloor) continue;
      var manualKey = manualBrand + '|' + manualCamp.toLowerCase() + '|' + manualDay;
      if (!imRows[manualKey] || priority > imRows[manualKey].priority)
        imRows[manualKey] = { priority: priority, row: mr, brand: manualBrand,
          camp: manualCamp, day: manualDay };
    }
  }
  collectInMobi(_sheet(CFG.RAW_BACKUP).getDataRange().getValues(), 1);
  collectInMobi(_sheet(CFG.RAW_MANUAL).getDataRange().getValues(), 2);
  Object.keys(imRows).sort().forEach(function (manualKey) {
    var item = imRows[manualKey], mr = item.row;
    addStd('InMobi', item.brand, item.camp, item.day,
      [_num(mr[4]), _num(mr[5]), Math.round(_num(mr[6]) * 10000) / 10000,
       _num(mr[7]), _num(mr[8]), _num(mr[9]), _num(mr[10]), _num(mr[11])]);
  });

  /* ---- Apple Search Ads (APPLE1): resolve columns by header so a connector refresh
          cannot shift the metrics. Spend is already USD; Taps serve as both click
          fields, and this export has no video-view or purchase metric. ---- */
  var apv = _sheet(CFG.APPLE).getDataRange().getValues();
  var aph = apv[0] || [], apc = {};
  ['Date','App Name','Campaign Name','Spend','Impressions','Taps','Installs (Total)']
    .forEach(function (name) {
      apc[name] = _col(aph, name) - 1;
      if (apc[name] < 0) throw new Error(CFG.APPLE + ' is missing the required column "' + name + '".');
    });
  for (var ai = 1; ai < apv.length; ai++) {
    var ar = apv[ai];
    if (!ar[apc.Date]) continue;
    var appleBrand = CFG.PROPERTY_OF[String(ar[apc['App Name']] || '').trim()];
    if (!appleBrand) continue;
    var appleDay = _day(ar[apc.Date], sourceTz);
    if (appleDay < CFG.FLOOR['Apple|Conversion']) continue;
    if (from && appleDay && (appleDay < from || appleDay > till)) continue;
    var appleCamp = String(ar[apc['Campaign Name']] || '').trim();
    var appleTaps = _num(ar[apc.Taps]);
    addStd('Apple', appleBrand, appleCamp, appleDay,
      [0, _num(ar[apc.Impressions]), Math.round(_num(ar[apc.Spend]) * 10000) / 10000,
       appleTaps, appleTaps, 0, _num(ar[apc['Installs (Total)']]), 0]);
  }

  /* ---- Adjust Raw: resolve its export columns by their headers. Channel and
          objective come from the source, never from a guessed network name. ---- */
  var adjustCurrent = _ss().getSheetByName(CFG.ADJUST_CURRENT);
  var adjustSheet = adjustCurrent && adjustCurrent.getLastRow() > 1
    ? adjustCurrent : _sheet(CFG.ADJUST);
  var adjustSourceName = adjustSheet.getName ? adjustSheet.getName() :
    (adjustCurrent && adjustCurrent.getLastRow() > 1 ? CFG.ADJUST_CURRENT : CFG.ADJUST);
  var adjustRange = adjustSheet.getDataRange();
  var av = adjustRange.getValues();
  // Display text is useful only for cells that stayed text. For native Date cells
  // it merely repeats Google's already-swapped interpretation (01/09 becomes
  // 9 January), so those must continue through the import-level reversal check.
  var avDisplay = adjustRange.getDisplayValues ? adjustRange.getDisplayValues() : null;
  var ah = av[0] || [];
  var ac = {};
  ['day','network','campaign_network','app','all_revenue','paid_installs','installs',
    'bookingconfirmed_events','channel','objective'].forEach(function (name) {
    ac[name] = _col(ah, name) - 1;
    if (ac[name] < 0) throw new Error(adjustSourceName + ' is missing the required column "' + name + '".');
  });
  var adjustDataRows = av.reduce(function (n, r, idx) { return n + (idx > 0 && r[ac.day] ? 1 : 0); }, 0);
  if (adjustDataRows === 5000)
    throw new Error(adjustSourceName + ' has exactly 5,000 data rows. This export is incomplete ' +
      'for the selected period, so the dashboard will not publish partial Adjust metrics. ' +
      'Import the complete Adjust export for both apps, in smaller date batches if needed.');
  var reversedAdjustRows = _adjustReversedRows(av, ac.day, sourceTz);
  // Monthly imports can overlap by a day. Adjust's export grain is one row per
  // app + network + campaign + day, so the later occurrence replaces the older
  // one instead of being added twice. This also keeps attribution restatements
  // from being summed with their previous value.
  var aLatest = {};
  for (var j = 1; j < av.length; j++) {
    var a = av[j];
    if (!a[ac.day]) continue;
    var appBrand = { 'Six Flags': 'SFQC', 'Aquarabia': 'AAQC' }[String(a[ac.app] || '').trim()];
    if (!appBrand) continue;
    var channel = _adjustChannel(a[ac.network], String(a[ac.channel] || '').trim());
    var objective = String(a[ac.objective] || '').trim();
    if (channel === 'Organic') continue;
    if (!channel || !objective) throw new Error('Adjust Raw row ' + (j + 1) + ': missing channel or objective.');
    var shownDay = avDisplay && avDisplay[j] ? String(avDisplay[j][ac.day] || '').trim() : '';
    var nativeDay = a[ac.day];
    var d = nativeDay instanceof Date
      ? _adjustDay(nativeDay, j + 1, !!reversedAdjustRows[j], sourceTz)
      : _adjustDay(shownDay || nativeDay, j + 1, false, sourceTz);
    // awareness and YouTube lines have no date floor; every other line starts 2 Jul
    var isAwr = (objective === 'Awareness' || objective === 'YouTube');
    if (!isAwr && d && d < CFG.ADJUST_FROM) continue;
    if (from && d && (d < from || d > till)) continue;
    // day is part of the key so the dashboard can move Adjust with the date picker —
    // without it the verified installs, bookings and revenue ignore the range.
    // campaign_network is part of it too: it is the only thing that ties a verified
    // install back to the campaign that bought it, and column C carries the same
    // name Raw data does. Without it the campaign table can only guess by spend.
    var camp = a[ac.campaign_network];
    // Some combined Adjust exports contain SFQC-named campaigns on rows whose App
    // cell says Aquarabia (and vice versa). The campaign name is the more specific
    // identifier; retain App only as the fallback for generic rows such as
    // "Expired Attributions". Without this, AAQC absorbs another brand's results.
    var brand = _brandFromCampaign(camp, appBrand);
    var ci = _campIndex(camp);
    var sourceKey = JSON.stringify([brand, String(a[ac.network] || '').trim(),
      String(camp || '').trim(), d]);
    var candidate = { brand: brand, channel: channel, objective: objective,
      os: _os(camp), day: d, ci: ci,
      revenue: _adjustNumber(a[ac.all_revenue], j + 1, 'all_revenue'),
      paidInst: _adjustNumber(a[ac.paid_installs], j + 1, 'paid_installs'),
      inst: _adjustNumber(a[ac.installs], j + 1, 'installs'),
      bookings: _adjustNumber(a[ac.bookingconfirmed_events], j + 1, 'bookingconfirmed_events') };
    var previous = aLatest[sourceKey];
    // The append-only legacy tab also contains partial zero-only refreshes for
    // Expired Attributions after the completed row for the same day. Until the
    // clean Adjust Current importer is used, do not let that partial row erase a
    // verified booking/revenue value. Ordinary campaigns still use later-wins.
    if (/^Expired Attributions$/i.test(String(camp || '').trim()) && previous) {
      var prevScore = previous.bookings * 1e12 + previous.revenue * 1e3 + previous.inst;
      var nextScore = candidate.bookings * 1e12 + candidate.revenue * 1e3 + candidate.inst;
      if (nextScore >= prevScore) aLatest[sourceKey] = candidate;
    } else {
      aLatest[sourceKey] = candidate;
    }
  }
  var aMap = {};
  Object.keys(aLatest).forEach(function (sourceKey) {
    var row = aLatest[sourceKey];
    var key = JSON.stringify([row.brand, row.channel, row.objective, row.os, row.day, row.ci]);
    var e = aMap[key] || (aMap[key] = { brand: row.brand, channel: row.channel,
      objective: row.objective, os: row.os, day: row.day, ci: row.ci,
      revenue: 0, paidInst: 0, inst: 0, bookings: 0 });
    e.revenue += row.revenue;
    e.paidInst += row.paidInst;
    e.inst += row.inst;
    e.bookings += row.bookings;
  });
  var adjust = Object.keys(aMap).map(function (k) {
    var e = aMap[k];
    return { brand: e.brand, channel: e.channel, objective: e.objective,
      os: e.os, day: e.day, ci: e.ci,
      revenue: Math.round(e.revenue * 100) / 100,
      paidInst: e.paidInst, inst: e.inst, bookings: e.bookings };
  });

  /* ---- GA4 (Supermetrics): A account, B property, C date, D campaign,
          E channel grouping, F source/medium, G transactions, H revenue ---- */
  var gsh = _sheet(CFG.GA4);
  var gLast = gsh.getLastRow();
  var gMap = {};
  if (gLast > 1) {
    var gHdr = gsh.getRange(1, 1, 1, gsh.getLastColumn()).getValues()[0];
    var cProp = _col(gHdr, 'GA4 property'), cDate = _col(gHdr, 'Date');
    var cCamp = _col(gHdr, 'Session campaign name');
    var cGrp = _col(gHdr, 'Session default channel grouping');
    var cSrc = _col(gHdr, 'Session source / medium');
    var cTx = _col(gHdr, 'Transactions'), cRev = _col(gHdr, 'Purchase revenue');
    if (!cProp || !cDate || !cGrp || !cSrc || !cTx || !cRev) {
      throw new Error('The GA4 tab does not look like the Supermetrics output — expected ' +
        '"GA4 property", "Session default channel grouping", "Session source / medium", ' +
        '"Transactions", "Purchase revenue".');
    }
    var gv = gsh.getRange(2, 1, gLast - 1, gsh.getLastColumn()).getValues();
    for (var k = 0; k < gv.length; k++) {
      var g = gv[k];
      var brand2 = CFG.PROPERTY_OF[String(g[cProp - 1] || '').trim()];
      if (!brand2) continue;
      if (CFG.PAID_GROUPS.indexOf(String(g[cGrp - 1] || '').trim()) < 0) continue;
      var d2 = _day(g[cDate - 1], sourceTz);
      if (from && d2 && (d2 < from || d2 > till)) continue;
      // Session campaign name rides along for the same reason Adjust's does: it is
      // what puts web revenue on the campaign that earned it instead of spreading it.
      var gci = _campIndex(cCamp ? g[cCamp - 1] : '');
      var kk = brand2 + '|' + _bucket(g[cSrc - 1], g[cCamp - 1]) + '|' + d2 + '|' + gci;
      var e2 = gMap[kk] || (gMap[kk] = { tx: 0, revenue: 0 });
      e2.tx += _num(g[cTx - 1]);
      e2.revenue += _num(g[cRev - 1]);
    }
  }
  var ga4 = Object.keys(gMap).map(function (k) {
    var p = k.split('|');
    return { brand: p[0], bucket: p[1], day: p[2], ci: Number(p[p.length - 1]),
      tx: gMap[k].tx, revenue: Math.round(gMap[k].revenue * 100) / 100 };
  });

  // Source freshness is not the same thing as arithmetic reconciliation. Keep
  // the actual first/last row dates in the payload so the UI can say, for
  // example, that media and Adjust reach 30 Sep while GA4 reaches 29 Sep.
  var mediaCoverage = {}, adjustCoverage = {}, ga4Coverage = {};
  raw.forEach(function (r) {
    var objective = r[12] || _objective(r[0], _campList[r[2]]);
    var key = JSON.stringify([r[1], r[0], objective]);
    _touchCoverage(mediaCoverage, key, r[3],
      { brand: r[1], platform: r[0], objective: objective });
  });
  adjust.forEach(function (a) {
    var key = JSON.stringify([a.brand, a.channel, a.objective]);
    _touchCoverage(adjustCoverage, key, a.day,
      { brand: a.brand, platform: a.channel, objective: a.objective });
  });
  ga4.forEach(function (g) {
    var key = JSON.stringify([g.brand, g.bucket]);
    _touchCoverage(ga4Coverage, key, g.day,
      { brand: g.brand, bucket: g.bucket });
  });

  // The picker and 7d/14d presets must use calendar days, not only days that had
  // media spend. Otherwise no-spend dates disappear and Adjust/GA4-only activity
  // shifts into the wrong period.
  var days = _dateSpine(from, till);
  if (!days.length) days = Object.keys(dayset).sort();
  return {
    meta: {
      start: from || days[0], end: till || days[days.length - 1], days: days,
      plats: Object.keys(platset).sort(), fx: CFG.FX,
      sourceCoverage: {
        media: _coverageValues(mediaCoverage),
        adjust: _coverageValues(adjustCoverage),
        ga4: _coverageValues(ga4Coverage)
      },
      generated: 'Refreshed ' + Utilities.formatDate(new Date(), CFG.TZ, 'yyyy-MM-dd HH:mm')
    },
    raw: raw, adjust: adjust, ga4: ga4, camps: _campList
  };
}

/* ------------------------------------------------------------------ validation */

/**
 * Reconciles the payload against the two pacing tabs, line by line and metric by
 * metric, and writes the result to a "Dashboard Validation" tab.
 *
 * This checks implementation parity with the pacing tabs. Both can read the
 * same incomplete Adjust Raw export, so source coverage is checked separately.
 */
var VAL = {
  // pacing row -> [platform, objective] for the raw-data lines
  LINES: {
    7:  ['Snapchat', 'Awareness',  'SnapChat — Awareness'],
    8:  ['TikTok',   'Awareness',  'TikTok — Awareness'],
    9:  ['X',        'Awareness',  'X — Awareness'],
    10: ['Google',   'Awareness',  'Youtube — Awareness'],
    15: ['TikTok',   'Search',     'TikTok Search'],
    16: ['Google',   'Search',     'Google Search'],
    17: ['Snapchat', 'Conversion', 'SnapChat App'],
    18: ['TikTok',   'Conversion', 'TikTok App'],
    19: ['Meta',     'Conversion', 'Meta App'],
    20: ['X',        'Conversion', 'X App'],
    21: ['Google',   'Conversion', 'Google App Ads'],
    22: ['Apple',    'Conversion', 'Apple Ads'],
    23: ['Bidease',  'Conversion', 'Bidease'],
    24: ['InMobi',   'Conversion', 'InMobi'],
    25: ['InMotion', 'Conversion', 'InMotion']
  },
  // raw payload index -> pacing column
  METRICS: [[6, 5, 'Spend USD'], [5, 7, 'Impressions'], [8, 9, 'Clicks'],
            [9, 8, 'Views'], [7, 10, 'Link clicks'], [10, 15, 'App installs'],
            [11, 14, 'Purchases']],
  // Adjust: the objective the pacing row reads, per channel
  ADJ_OBJ: { 10: 'YouTube' },
  // GA4 bucket -> pacing row
  GA_LINES: { 'Snapchat': 7, 'TikTok': 8, 'TikTok-cpc': 15, 'Google': 16, 'Meta': 19 }
};

function validateDashboard() {
  var ss = _ss();
  var p = getPacingDashboardData();
  var out = [], bad = 0, total = 0, sourceMissing = 0;
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
  row('Window', p.meta.start, 'to', p.meta.end, '', '');

  [['SFQC', 'SFQC Pacing_Daily'], ['AAQC', 'AAQC Pacing_Daily']].forEach(function (pair) {
    var brand = pair[0], ws = ss.getSheetByName(pair[1]);
    if (!ws) { row(brand, 'tab missing', '', '', '', 'CHECK'); bad++; return; }
    var grid = ws.getRange(1, 1, 30, 24).getValues();
    function cell(r, c) { var v = grid[r - 1][c - 1]; return typeof v === 'number' ? v : 0; }

    row('', '', '', '', '', '');
    row(brand + ' · RAW DATA', 'Dashboard', 'Pacing', '', '', '');
    var agg = {};
    p.raw.forEach(function (r) {
      if (r[1] !== brand) return;
      var k = r[0] + '|' + (r[12] || _objective(r[0], p.camps[r[2]]));
      var e = agg[k] || (agg[k] = [0,0,0,0,0,0,0,0,0,0,0,0]);
      for (var i = 4; i <= 11; i++) e[i] += r[i];
    });
    Object.keys(VAL.LINES).forEach(function (ln) {
      var spec = VAL.LINES[ln], e = agg[spec[0] + '|' + spec[1]] || [0,0,0,0,0,0,0,0,0,0,0,0];
      VAL.METRICS.forEach(function (m) { cmp(brand, spec[2], m[2], e[m[0]], cell(ln, m[1])); });
    });

    row('', '', '', '', '', '');
    row(brand + ' · ADJUST', 'Dashboard', 'Pacing', '', '', '');
    var aagg = {};
    p.adjust.forEach(function (a) {
      if (a.brand !== brand) return;
      var k = a.channel + '|' + a.objective;
      var e = aagg[k] || (aagg[k] = { inst: 0, bookings: 0 });
      e.inst += a.inst; e.bookings += a.bookings;
    });
    Object.keys(VAL.LINES).forEach(function (ln) {
      var spec = VAL.LINES[ln];
      var obj = VAL.ADJ_OBJ[ln] || spec[1];
      var sourceKey = spec[0] + '|' + obj;
      if (!aagg[sourceKey] && agg[spec[0] + '|' + spec[1]] &&
          agg[spec[0] + '|' + spec[1]][6] > 0) {
        sourceMissing++;
        row(brand, spec[2], 'Adjust Raw coverage', 'No source rows', '', 'SOURCE MISSING');
      }
      var e = aagg[sourceKey] || { inst: 0, bookings: 0 };
      cmp(brand, spec[2], 'Adjust Purchase', e.bookings, cell(ln, 11));
      cmp(brand, spec[2], 'Adjust Install', e.inst, cell(ln, 12));
    });

    row('', '', '', '', '', '');
    row(brand + ' · GA4', 'Dashboard', 'Pacing', '', '', '');
    Object.keys(VAL.GA_LINES).forEach(function (bucket) {
      var ln = VAL.GA_LINES[bucket];
      var hit = { tx: 0, revenue: 0 };
      p.ga4.forEach(function (g) {
        if (g.brand === brand && g.bucket === bucket) { hit.tx += g.tx; hit.revenue += g.revenue; }
      });
      cmp(brand, VAL.LINES[ln][2], 'GA4 transactions', hit.tx, cell(ln, 13));
      // the Meta row takes its revenue from Adjust, not GA4, so only its transactions compare
      if (ln !== 19) cmp(brand, VAL.LINES[ln][2], 'GA4 revenue', hit.revenue, cell(ln, 24));
    });
  });

  out.splice(2, 0, ['RESULT', total + ' figures compared',
                    (total - bad) + ' match', bad + ' differ',
                    sourceMissing + ' Adjust lines without source rows',
                    bad === 0 && sourceMissing === 0 ? 'OK' : 'CHECK']);

  var sh = ss.getSheetByName('Dashboard Validation');
  if (!sh) sh = ss.insertSheet('Dashboard Validation');
  sh.clear();
  sh.getRange(1, 1, out.length, 6).setValues(out);
  sh.getRange('A1').setFontSize(14).setFontWeight('bold');
  sh.getRange('A3:F3').setFontWeight('bold');
  out.forEach(function (r, i) {
    if (String(r[0]).indexOf(' · ') > -1) {
      sh.getRange(i + 1, 1, 1, 6).setFontWeight('bold').setBackground('#000050').setFontColor('#ffffff');
    }
    if (r[5] === 'OK') sh.getRange(i + 1, 6).setBackground('#d9ead3');
    if (r[5] === 'CHECK') sh.getRange(i + 1, 6).setBackground('#f4cccc');
    if (r[5] === 'SOURCE MISSING') sh.getRange(i + 1, 6).setBackground('#f4cccc');
  });
  sh.setColumnWidth(1, 200); sh.setColumnWidth(2, 190); sh.setColumnWidth(3, 150);
  sh.setColumnWidth(4, 130); sh.setColumnWidth(5, 245); sh.setColumnWidth(6, 140);
  sh.setFrozenRows(3);
  ss.setActiveSheet(sh);
  Logger.log('%s figures compared, %s match, %s differ', total, total - bad, bad);
  var msg = sourceMissing
    ? sourceMissing + ' Adjust lines have spend but no source rows; ' + bad +
      ' of ' + total + ' figures differ. See "Dashboard Validation".'
    : bad === 0 ? 'All ' + total + ' figures match the pacing tabs (source coverage is separate).'
    : bad + ' of ' + total + ' figures differ — see the "Dashboard Validation" tab.';
  try { SpreadsheetApp.getUi().alert(msg); } catch (e) { /* no UI attached */ }
}

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

