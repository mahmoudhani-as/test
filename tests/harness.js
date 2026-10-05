/**
 * End-to-end check that the dashboard counts exactly what the pacing tabs count.
 *
 *   1. builds the synthetic workbook in tests/fixture.js;
 *   2. evaluates the pacing formulas Untitled.gs installs with a real spreadsheet engine
 *      (HyperFormula) over that workbook;
 *   3. runs Code.gs (getPacingDashboardData + validateDashboard) against a mock of the
 *      Apps Script spreadsheet API holding the same cells and the evaluated pacing tabs;
 *   4. loads Dashboard.html in jsdom and compares every line and total it shows with the
 *      pacing tab, for SFQC and AAQC;
 *   5. runs "Clean Adjust Raw" and checks again;
 *   6. runs Qiddiya Setup → Fix this workbook end to end on the workbook as it was before the
 *      fix (pasted Raw data, then an IMPORTRANGE copy), checks every step, then Undo.
 * The original code (git HEAD~ files passed with --old) goes through the same steps so the
 * before/after difference is measured, not asserted.
 *
 *   node tests/harness.js                 # the current files
 *   node tests/harness.js --old DIR       # also run the original files found in DIR
 */
'use strict';
var fs = require('fs'), vm = require('vm'), path = require('path');
var HyperFormula = require('hyperformula').HyperFormula;
var JSDOM = require('jsdom').JSDOM;
var fx = require('./fixture');

var ROOT = path.join(__dirname, '..');
var PACING_TABS = ['SFQC Pacing_Daily', 'AAQC Pacing_Daily'];

function serial(d) { return (d.getTime() - Date.UTC(1899, 11, 30)) / 86400000; }
function fromSerial(n) { return new Date(Date.UTC(1899, 11, 30) + Math.round(n * 86400000)); }
function colIndex(letters) { var n = 0; for (var i = 0; i < letters.length; i++) n = n * 26 + letters.charCodeAt(i) - 64; return n - 1; }
function colName(i) { var s = ''; i++; while (i > 0) { var m = (i - 1) % 26; s = String.fromCharCode(65 + m) + s; i = Math.floor((i - 1) / 26); } return s; }

/* IFERROR(VALUE(SUBSTITUTE(x,",","")),0) for one cell, as Google Sheets evaluates it. */
function sheetsValue(v) {
  if (typeof v === 'number') return v;
  if (v === null || v === undefined || v === '') return 0;
  var s = String(v).replace(/,/g, '').trim().replace(/^(-?)\$/, '$1');
  if (!s) return 0;
  var n = Number(s);
  return isFinite(n) ? n : 0;
}

/* ------------------------------------------------------------------ pacing formulas */
function evaluatePacing(wb, spec) {
  var sheets = {};
  Object.keys(wb).forEach(function (name) {
    if (PACING_TABS.indexOf(name) >= 0) return;
    sheets[name] = wb[name].map(function (r) {
      return r.map(function (v) { return v instanceof Date ? serial(v) : (v === undefined || v === '' ? null : v); });
    });
  });
  // HyperFormula does not vectorise SUBSTITUTE/VALUE inside SUMPRODUCT, so row 24's
  // element-wise VALUE(SUBSTITUTE(...)) is precomputed into a helper sheet per source.
  ['Raw manual', 'Raw data BACKUP 20260807-1642'].forEach(function (src) {
    var h = wb[src].map(function (r) { return r.map(sheetsValue); });
    while (h.length < 10001) h.push([0]);
    while (sheets[src].length < 10001) sheets[src].push([null]);
    sheets[src + ' NUM'] = h;
  });
  var errors = [];
  PACING_TABS.forEach(function (tab) {
    var grid = [];
    for (var r = 0; r < 53; r++) grid.push(new Array(24).fill(null));
    grid[1][1] = serial(wb[tab][1][1]); grid[1][2] = serial(wb[tab][1][2]);
    Object.keys(spec[tab]).forEach(function (a1) {
      var m = /^([A-Z]+)(\d+)$/.exec(a1), f = spec[tab][a1];
      f = f.replace(/IFERROR\(VALUE\(SUBSTITUTE\('([^']+)'!(\$[A-Z]+\$\d+:\$[A-Z]+\$\d+),",",""\)\),0\)/g,
        function (all, sh, rng) { return "'" + sh + " NUM'!" + rng; });
      grid[+m[2] - 1][colIndex(m[1])] = f === '' ? null : f;
    });
    sheets[tab] = grid;
  });
  var hf = HyperFormula.buildFromSheets(sheets, { licenseKey: 'gpl-v3', useArrayArithmetic: true,
    dateFormats: ['MM/DD/YYYY'] });
  var out = {};
  PACING_TABS.forEach(function (tab) {
    var vals = hf.getSheetValues(hf.getSheetId(tab));
    out[tab] = vals.map(function (row, ri) {
      return row.map(function (v, ci) {
        if (v && typeof v === 'object' && v.value) {
          if (spec[tab][colName(ci) + (ri + 1)] && !/^(P|Q|R|S|T|U|V|W)$/.test(colName(ci))) {
            errors.push(tab + '!' + colName(ci) + (ri + 1) + ' ' + v.value + ' ' + (v.message || ''));
          }
          return v.value;
        }
        return v;
      });
    });
  });
  hf.destroy();
  if (errors.length) throw new Error('Formula errors:\n' + errors.slice(0, 20).join('\n'));
  return out;
}
function pv(vals, a1) {
  var m = /^([A-Z]+)(\d+)$/.exec(a1), row = vals[+m[2] - 1] || [], v = row[colIndex(m[1])];
  return typeof v === 'number' ? v : 0;
}

/* ------------------------------------------------------------------ Apps Script mock */
function makeSpreadsheet(wb, tz) {
  var sheets = [];
  // A cell holds a value (v) and, separately, a formula (f, keyed "row,col"). setFormula keeps the
  // formula text as the value too, since nothing here evaluates it; put() writes a value only,
  // the way Sheets shows a formula's result.
  function Sheet(name, values) {
    this.name = name; this.hidden = false; this.fmt = {}; this.f = {};
    this.v = values.map(function (r) { return r.map(function (x) { return x === undefined || x === null ? '' : x; }); });
  }
  Sheet.prototype.getName = function () { return this.name; };
  Sheet.prototype.setName = function (n) { this.name = n; return this; };
  Sheet.prototype.hideSheet = function () { this.hidden = true; return this; };
  Sheet.prototype.copyTo = function () {
    var s = new Sheet('Copy of ' + this.name, this.v); s.f = JSON.parse(JSON.stringify(this.f)); sheets.push(s); return s;
  };
  Sheet.prototype.showSheet = function () { this.hidden = false; return this; };
  Sheet.prototype.getLastRow = function () {
    for (var r = this.v.length - 1; r >= 0; r--) if (this.v[r].some(function (x) { return x !== ''; })) return r + 1;
    return 0;
  };
  Sheet.prototype.getLastColumn = function () {
    var c = 0; this.v.forEach(function (r) { for (var i = r.length - 1; i >= 0; i--) if (r[i] !== '') { c = Math.max(c, i + 1); break; } });
    return c;
  };
  Sheet.prototype.getMaxRows = function () { return Math.max(1000, this.v.length); };
  Sheet.prototype.getMaxColumns = function () { return Math.max(26, this.getLastColumn()); };
  Sheet.prototype.insertRowsAfter = function () { return this; };
  Sheet.prototype.insertColumnsAfter = function () { return this; };
  Sheet.prototype.deleteRows = function () { return this; };
  Sheet.prototype.deleteColumns = function () { return this; };
  Sheet.prototype.setFrozenRows = function () { return this; };
  Sheet.prototype.setTabColor = function () { return this; };
  Sheet.prototype.setColumnWidth = function () { return this; };
  Sheet.prototype.setConditionalFormatRules = function () { return this; };
  Sheet.prototype.clear = function () { this.v = []; this.f = {}; return this; };
  Sheet.prototype.clearContents = Sheet.prototype.clear;
  Sheet.prototype.getDataRange = function () { return new Range(this, 1, 1, Math.max(1, this.getLastRow()), Math.max(1, this.getLastColumn())); };
  Sheet.prototype.getRange = function (a, b, c, d) {
    if (typeof a === 'number') return new Range(this, a, b, c || 1, d || 1);
    var m = /^([A-Z]+)(\d*)(?::([A-Z]+)(\d*))?$/.exec(a);
    var r1 = m[2] ? +m[2] : 1, c1 = colIndex(m[1]) + 1;
    if (!m[3]) return new Range(this, r1, c1, 1, 1);
    var c2 = colIndex(m[3]) + 1, r2 = m[4] ? +m[4] : Math.max(r1, this.getLastRow());
    return new Range(this, r1, c1, r2 - r1 + 1, c2 - c1 + 1);
  };
  Sheet.prototype.cell = function (r, c) { var row = this.v[r - 1]; return row && row[c - 1] !== undefined ? row[c - 1] : ''; };
  Sheet.prototype.put = function (r, c, x) {
    while (this.v.length < r) this.v.push([]);
    var row = this.v[r - 1]; while (row.length < c) row.push('');
    row[c - 1] = x;
  };
  function Range(sh, r, c, nr, nc) { this.sh = sh; this.r = r; this.c = c; this.nr = nr; this.nc = nc; }
  Range.prototype.each = function (fn) { for (var i = 0; i < this.nr; i++) for (var j = 0; j < this.nc; j++) fn(this.r + i, this.c + j, i, j); };
  Range.prototype.getValues = function () {
    var out = []; for (var i = 0; i < this.nr; i++) { var row = []; for (var j = 0; j < this.nc; j++) row.push(this.sh.cell(this.r + i, this.c + j)); out.push(row); }
    return out;
  };
  Range.prototype.getValue = function () { return this.sh.cell(this.r, this.c); };
  Range.prototype.getDisplayValue = function () { return this.getDisplayValues()[0][0]; };
  Range.prototype.getNumberFormat = function () { return this.sh.fmt[this.c] || ''; };
  Range.prototype.getDisplayValues = function () {
    return this.getValues().map(function (row) {
      return row.map(function (x) {
        return x instanceof Date ? (x.getUTCMonth() + 1) + '/' + x.getUTCDate() + '/' + x.getUTCFullYear() : String(x);
      });
    });
  };
  Range.prototype.getFormulas = function () {
    var out = []; for (var i = 0; i < this.nr; i++) { var row = []; for (var j = 0; j < this.nc; j++) row.push(this.sh.f[(this.r + i) + ',' + (this.c + j)] || ''); out.push(row); }
    return out;
  };
  Range.prototype.getFormula = function () { return this.sh.f[this.r + ',' + this.c] || ''; };
  Range.prototype.setValues = function (vals) {
    var sh = this.sh;
    this.each(function (r, c, i, j) {
      var x = vals[i][j];
      delete sh.f[r + ',' + c];
      if (typeof x === 'string' && sh.fmt[c] !== '@') {
        if (/^\d{4}-\d{2}-\d{2}$/.test(x)) x = fx.D(x);                      // Sheets parses ISO dates
        else if (/^-?\d+(\.\d+)?$/.test(x)) x = Number(x);
        else if (x.charAt(0) === '=') sh.f[r + ',' + c] = x;                  // and stores "=…" as a formula
      }
      sh.put(r, c, x);
    });
    return this;
  };
  Range.prototype.setValue = function (x) { delete this.sh.f[this.r + ',' + this.c]; this.sh.put(this.r, this.c, x); return this; };
  Range.prototype.setFormula = function (f) { this.sh.f[this.r + ',' + this.c] = f; this.sh.put(this.r, this.c, f); return this; };
  Range.prototype.clearContent = function () { var sh = this.sh; this.each(function (r, c) { delete sh.f[r + ',' + c]; if (sh.v[r - 1]) sh.put(r, c, ''); }); return this; };
  Range.prototype.setNumberFormat = function (f) { for (var j = 0; j < this.nc; j++) this.sh.fmt[this.c + j] = f; return this; };
  ['setFontWeight', 'setFontSize', 'setBackground', 'setFontColor', 'setHorizontalAlignment'].forEach(function (k) {
    Range.prototype[k] = function () { return this; };
  });

  Object.keys(wb).forEach(function (name) { sheets.push(new Sheet(name, wb[name])); });
  var ss = {
    sheets: sheets,
    getSheetByName: function (n) { return sheets.filter(function (s) { return s.name === n; })[0] || null; },
    getSheets: function () { return sheets.slice(); },
    insertSheet: function (n) { var s = new Sheet(n, []); sheets.push(s); return s; },
    deleteSheet: function (s) { sheets.splice(sheets.indexOf(s), 1); },
    getSpreadsheetTimeZone: function () { return tz; },
    getName: function () { return 'Synthetic Daily Report'; },
    getId: function () { return 'synthetic'; },
    setActiveSheet: function () {}
  };
  return ss;
}
function formatDate(date, tz, fmt) {
  var p = {};
  new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).formatToParts(date)
    .forEach(function (x) { p[x.type] = x.value; });
  return fmt.replace('yyyy', p.year).replace('MM', p.month).replace('dd', p.day).replace('HH', p.hour)
    .replace('mm', p.minute).replace('ss', p.second);
}
function loadServer(files, ss) {
  var logs = [], triggers = [], store = {};
  var props = { getProperty: function (k) { return store[k] == null ? null : store[k]; },
                setProperty: function (k, v) { store[k] = String(v); } };
  var ctx = {
    SpreadsheetApp: {
      getActive: function () { return ss; }, getActiveSpreadsheet: function () { return ss; },
      openById: function () { return ss; }, flush: function () {},
      getUi: function () { throw new Error('no UI'); },
      newConditionalFormatRule: function () { var b = { whenTextEqualTo: function () { return b; }, setBackground: function () { return b; }, setRanges: function () { return b; }, build: function () { return {}; } }; return b; }
    },
    Utilities: { formatDate: formatDate },
    Logger: { log: function () { logs.push([].slice.call(arguments).join(' ')); } },
    Session: { getEffectiveUser: function () { return { getEmail: function () { return 'test@example.com'; } }; },
               getActiveUser: function () { return { getEmail: function () { return 'test@example.com'; } }; } },
    LockService: { getDocumentLock: function () { return { waitLock: function () {}, releaseLock: function () {} }; },
                   getScriptLock: function () { return { waitLock: function () {}, tryLock: function () { return true; }, releaseLock: function () {} }; } },
    PropertiesService: { getDocumentProperties: function () { return props; } },
    ScriptApp: { getProjectTriggers: function () { return triggers.slice(); },
      newTrigger: function (fn) { var b = { timeBased: function () { return b; }, everyHours: function () { return b; },
        create: function () { triggers.push({ getHandlerFunction: function () { return fn; } }); } }; return b; },
      deleteTrigger: function (t) { triggers.splice(triggers.indexOf(t), 1); } },
    HtmlService: {}, DriveApp: {}, MimeType: {}, console: console,
    Date: Date            // one realm, so instanceof Date works on the fixture's cells
  };
  vm.createContext(ctx);
  files.forEach(function (f) { vm.runInContext(fs.readFileSync(f, 'utf8'), ctx, { filename: f }); });
  ctx.__logs = logs;
  return ctx;
}
function putPacing(ss, vals) {
  PACING_TABS.forEach(function (tab) {
    var sh = ss.getSheetByName(tab);
    vals[tab].forEach(function (row, ri) {
      row.forEach(function (v, ci) {
        if (ri === 1 && (ci === 1 || ci === 2)) return;            // keep B2:C2 as dates
        sh.put(ri + 1, ci + 1, typeof v === 'number' ? v : (v === null ? '' : v));
      });
    });
  });
}
function sheetToWb(ss) {
  var wb = {};
  ss.sheets.forEach(function (s) { wb[s.name] = s.v.map(function (r) { return r.slice(); }); });
  return wb;
}

/* ------------------------------------------------------------------ the browser */
function loadClient(htmlFile, payload) {
  var html = fs.readFileSync(htmlFile, 'utf8');
  var json = JSON.stringify(payload);                       // google.script.run serialises
  var dom = new JSDOM(html, {
    runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse: function (w) {
      var ctx2d = new Proxy({}, {
        get: function (t, p) {
          if (p === 'createLinearGradient') return function () { return { addColorStop: function () {} }; };
          if (p === 'measureText') return function () { return { width: 10 }; };
          if (p in t) return t[p];
          return function () {};
        },
        set: function (t, p, v) { t[p] = v; return true; }
      });
      w.HTMLCanvasElement.prototype.getContext = function () { return ctx2d; };
      var handler = null;
      var run = {
        withSuccessHandler: function (fn) { handler = fn; return run; },
        withFailureHandler: function () { return run; },
        getPacingDashboardData: function () { handler(JSON.parse(json)); }
      };
      w.google = { script: { run: run } };
    }
  });
  var w = dom.window;
  var err = w.document.getElementById('error');
  if (err && err.style.display === 'block') throw new Error('Dashboard failed: ' + err.textContent);
  return w;
}

/* ------------------------------------------------------------------ comparisons */
var LINES = [[7, 'Snapchat|Awareness'], [8, 'TikTok|Awareness'], [9, 'X|Awareness'], [10, 'Google|Awareness'],
  [15, 'TikTok|Search'], [16, 'Google|Search'], [17, 'Snapchat|Conversion'], [18, 'TikTok|Conversion'],
  [19, 'Meta|Conversion'], [20, 'X|Conversion'], [21, 'Google|Conversion'], [22, 'Apple|Conversion'],
  [23, 'Bidease|Conversion'], [24, 'InMobi|Conversion'], [25, 'InMotion|Conversion'], [26, 'Other|Other']];
// counts and money to the cent, like validateDashboard (float noise is ~1e-9)
function close(a, b) { return Math.abs(a - b) <= 0.01; }

function compareClient(w, vals, label) {
  var diffs = [];
  ['SFQC', 'AAQC'].forEach(function (brand) {
    w.setBrand(brand);
    w.presetTab();                     // the dates the tabs count, if "All" runs further
    var tab = vals[brand + ' Pacing_Daily'];
    var ln = w.lines(), by = {};
    ln.forEach(function (l) { by[l.plat + '|' + l.obj] = l; });
    var sum = { spend: 0, lpv: 0, bookings: 0, adjInst: 0, ga4Tx: 0, revenue: 0 };
    ln.forEach(function (l) {
      sum.spend += l.spend; sum.lpv += l.lpv || 0; sum.bookings += l.bookings; sum.adjInst += l.adjInst;
      sum.ga4Tx += l.ga4Tx || 0; sum.revenue += l.revenue;
    });
    LINES.forEach(function (x) {
      var row = x[0], l = by[x[1]] || { spend: 0, impr: 0, clicks: 0, lpv: 0, inst: 0, purch: 0, bookings: 0, adjInst: 0, ga4Tx: 0, revenue: 0 };
      var checks = [['E', l.spend, 'spend'], ['G', l.impr, 'impressions'], ['I', l.clicks, 'clicks'],
        ['N', l.purch, 'purchases'], ['O', l.inst, 'platform installs'],
        ['K', l.bookings, 'Adjust purchases'], ['L', l.adjInst, 'Adjust installs'], ['M', l.ga4Tx || 0, 'GA4 purchases'],
        ['X', l.revenue, 'revenue']];
      checks.forEach(function (c) {
        if (row === 26 && 'EGINO'.indexOf(c[0]) >= 0) return;
        var p = pv(tab, c[0] + row);
        if (!close(c[1], p)) diffs.push(brand + ' row ' + row + ' (' + x[1] + ') ' + c[2] + ': dashboard ' + c[1].toFixed(2) + ' vs tab ' + p.toFixed(2));
      });
    });
    [['F28', sum.spend * 3.78, 'total spend SAR'], ['J28', sum.lpv, 'total link clicks'], ['K28', sum.bookings, 'total Adjust purchases'],
     ['L28', sum.adjInst, 'total Adjust installs'], ['M28', sum.ga4Tx, 'total GA4 purchases'], ['X28', sum.revenue, 'total revenue'],
     ['P28', sum.spend ? sum.revenue / (sum.spend * 3.78) : 0, 'ROAS']].forEach(function (c) {
      var p = pv(tab, c[0]);
      if (!close(c[1], p)) diffs.push(brand + ' ' + c[0] + ' ' + c[2] + ': dashboard ' + c[1].toFixed(2) + ' vs tab ' + p.toFixed(2));
    });
  });
  return diffs;
}
function renderAllViews(w) {
  var problems = [];
  ['SFQC', 'AAQC', 'BOTH'].forEach(function (b) {
    w.setBrand(b);
    // "Check it against the tabs" must end on the same total as the KPI cards
    try {
      w.setView('method');
      var foot = w.document.querySelector('tfoot');
      if (w.DATA.recon && w.DATA.recon.length && (!foot || !/= Impressions and Spend cards/.test(foot.textContent))) {
        problems.push(b + ': source-tab check does not match the cards (' + (foot ? foot.textContent : 'no table') + ')');
      }
      var feet = w.document.querySelectorAll('tfoot');
      if (w.DATA.reconAdjust && w.DATA.reconAdjust.length &&
          ![].some.call(feet, function (f) { return /= Installs and Bookings cards/.test(f.textContent); })) {
        problems.push(b + ': Adjust check does not match the cards');
      }
    } catch (e) { problems.push(b + '/recon: ' + e.message); }
    ['summary', 'trend', 'platforms', 'campaigns', 'attribution', 'method'].forEach(function (v) {
      try { w.setView(v); } catch (e) { problems.push(b + '/' + v + ': ' + e.message); }
    });
  });
  try { w.setObj('Awareness'); w.setPlat('Snapchat'); w.preset(7); w.setView('summary'); w.clearFilters(); }
  catch (e) { problems.push('filters: ' + e.message); }
  return problems;
}
/* The KPI cards as the user sees them (text), for one portal. */
function kpis(w, brand) {
  w.setBrand(brand); w.setView('summary');
  var out = {};
  w.document.querySelectorAll('#kpis .kpi').forEach(function (k) {
    out[k.querySelector('.k').textContent.trim()] = k.querySelector('.v').textContent.trim();
  });
  return out;
}

/* ------------------------------------------------------------------ Fix this workbook */
/* The repair the user runs once on the live file, end to end on the synthetic workbook as it
   was before any fix: no Objective column, numbers stored as text in Raw manual, the original
   doc formulas on the pacing tabs. Then a re-run, the evaluated tabs against the dashboard,
   Quick check, Undo — and the same repair on a copy whose sources are IMPORTRANGE mirrors. */
function formulaGrid(sh) {
  var out = {};
  Object.keys(sh.f).sort().forEach(function (k) { out[k] = sh.f[k]; });
  return out;
}
/* Reads the generated objective ARRAYFORMULA the way Sheets would, without Code.gs. */
function objectiveFromFormula(f) {
  var tests = [], re = /IF\(\(vplat="([^"]+)"\)\*REGEXMATCH\(vcamp,"([^"]+)"\),"([^"]+)",/g, m;
  while ((m = re.exec(f))) tests.push([m[1].toLowerCase(), new RegExp(m[2]), m[3]]);
  return function (plat, camp) {
    var p = String(plat).trim().toLowerCase(), c = String(camp).toLowerCase();
    for (var i = 0; i < tests.length; i++) if (tests[i][0] === p && tests[i][1].test(c)) return tests[i][2];
    return 'Conversion';
  };
}
function fixStage(files) {
  console.log('\n==================== Qiddiya Setup → Fix this workbook (synthetic, before any fix) ====================');
  var fails = [];
  function check(ok, what) { console.log('   ' + (ok ? 'ok  ' : 'FAIL') + ' ' + what); if (!ok) fails.push(what); }
  var ss = makeSpreadsheet(fx.workbook(false), 'UTC');
  var ctx = loadServer(files.gs, ss);
  ctx.writeFormulas_(ss, ctx.PACING_ALL);                    // the tabs as they were: the doc's formulas
  var before = {};
  PACING_TABS.forEach(function (t) { before[t] = JSON.stringify(formulaGrid(ss.getSheetByName(t))); });
  var adjBefore = JSON.stringify(ss.getSheetByName('Adjust Raw').v);
  ctx.fixThisWorkbook();

  var raw = ss.getSheetByName('Raw data'), col = ctx.CFG.OBJECTIVE_COL.charCodeAt(0) - 64;
  var f2 = raw.getRange(ctx.CFG.OBJECTIVE_COL + '2').getFormula();
  check(raw.cell(1, col) === 'Objective' && f2 === ctx.objectiveColumnFormula_(),
    'Raw data ' + ctx.CFG.OBJECTIVE_COL + '1 = Objective and ' + ctx.CFG.OBJECTIVE_COL + '2 holds the objective ARRAYFORMULA');
  var objOf = objectiveFromFormula(f2), differ = 0;
  for (var r = 2; r <= raw.getLastRow(); r++) {
    if (raw.cell(r, 1) === '') continue;
    var o = objOf(raw.cell(r, 1), raw.cell(r, 3));
    if (o !== ctx._objective(String(raw.cell(r, 1)), String(raw.cell(r, 3)))) differ++;
    raw.put(r, col, o);                                       // what Sheets shows once the formula runs
  }
  check(differ === 0, 'the objective formula, read independently, equals Code.gs _objective() on every row (' + differ + ' differ)');
  var textNums = 0;
  ss.getSheetByName('Raw manual').v.slice(1).forEach(function (row) {
    row.slice(4, 12).forEach(function (x) { if (typeof x === 'string' && /^[\d,.\s$-]+$/.test(x) && /\d/.test(x)) textNums++; });
  });
  check(textNums === 0, 'Raw manual E:L holds no numbers stored as text (' + textNums + ')');
  var sf = ss.getSheetByName(PACING_TABS[0]), aa = ss.getSheetByName(PACING_TABS[1]);
  check(sf.getRange('C2').getFormula() === '=TODAY()-1' && aa.getRange('B2').getFormula() === "='SFQC Pacing_Daily'!B2" &&
    aa.getRange('C2').getFormula() === "='SFQC Pacing_Daily'!C2", 'SFQC C2 = TODAY()-1 and AAQC B2:C2 follow SFQC');
  var clean = ss.getSheetByName(ctx.CFG.ADJUST_CLEAN);
  check(!!clean && clean.cell(1, 1) === 'day' && clean.getLastRow() > 100, '"Adjust Clean" built (' + (clean ? clean.getLastRow() - 1 : 0) + ' rows)');
  check(JSON.stringify(ss.getSheetByName('Adjust Raw').v) === adjBefore, 'Adjust Raw not modified');
  check(ctx.ScriptApp.getProjectTriggers().length === 1, 'hourly refreshAdjustClean trigger installed');
  var spec = ctx.buildPacingSpec_(), wrong = 0;
  PACING_TABS.forEach(function (t) {
    var sh = ss.getSheetByName(t);
    Object.keys(spec[t]).forEach(function (a1) {
      var want = spec[t][a1], rg = sh.getRange(a1);
      var got = want === '' ? rg.getValue() + rg.getFormula() : want.charAt(0) === '=' ? rg.getFormula() : rg.getValue();
      if (got !== want) wrong++;
    });
  });
  check(wrong === 0, 'both pacing tabs hold the generated formulas, totals, checks and labels (' + wrong + ' cells differ)');
  var bks = ss.sheets.filter(function (x) { return / Pacing_Daily BACKUP /.test(x.name); });
  check(bks.length === 2 && bks.every(function (x) { return x.hidden; }), 'two hidden pacing backups');

  // the user types a fixed period end; Sheets evaluates AAQC's links. A second run keeps both.
  var till = fx.D(fx.WINDOW.till), from = sf.cell(2, 2);
  sf.getRange('C2').setValue(till);
  aa.put(2, 2, from); aa.put(2, 3, till);
  ctx.fixThisWorkbook();
  check(sf.getRange('C2').getFormula() === '' && sf.cell(2, 3) === till, 'a second run keeps the period typed into SFQC C2');
  check(ss.sheets.filter(function (x) { return / Pacing_Daily BACKUP /.test(x.name); }).length === 2,
    'a second run adds no pacing backup (Undo still goes back to before the first run)');
  check(ss.sheets.filter(function (x) { return /^Raw manual BACKUP /.test(x.name); }).length === 1,
    'a second run makes no second Raw manual backup');
  check(raw.getRange(ctx.CFG.OBJECTIVE_COL + '2').getFormula() === ctx.objectiveColumnFormula_(), 'a second run leaves the objective formula');
  aa.put(2, 2, from); aa.put(2, 3, till);

  // the evaluated tabs against the server and the page
  var wbNow = sheetToWb(ss);                                  // the pacing backups are not inputs
  Object.keys(wbNow).forEach(function (n) { if (/ Pacing_Daily BACKUP /.test(n)) delete wbNow[n]; });
  var vals = evaluatePacing(wbNow, ctx.buildPacingSpec_());
  putPacing(ss, vals);
  ctx.validateDashboard();
  var vsh = ss.getSheetByName('Dashboard Validation');
  var badRows = vsh.v.filter(function (x) { return x[5] === 'CHECK' && x[0] !== 'FIX' && x[0] !== 'RESULT'; });
  console.log('   validateDashboard: ' + vsh.v[2].slice(1, 5).join(' · '));
  badRows.slice(0, 5).forEach(function (x) { console.log('      CHECK ' + x.slice(0, 5).join(' | ')); });
  check(badRows.length === 0, 'validateDashboard: every figure matches the evaluated tabs');
  var w = loadClient(files.html, ctx.getPacingDashboardData());
  var d = compareClient(w, vals, 'fixed');
  d.slice(0, 5).forEach(function (x) { console.log('      ' + x); });
  check(d.length === 0, 'Dashboard page = pacing tabs, line by line and in total (' + d.length + ' differ)');
  w.close();
  var qc = '';
  try { ctx.verifyOnly(); } catch (e) { qc = e.message; }
  // the fixture's deliberate no-portal campaigns are a genuine coverage problem; nothing else may fail
  var qcOther = qc.split('\n').filter(function (l) { return /^(Raw data|SFQC Pacing_Daily|AAQC Pacing_Daily)/.test(l); });
  check(qcOther.length === 0, 'Quick check finds nothing wrong with Raw data or the pacing tabs' + (qcOther.length ? ': ' + qcOther.join(' / ') : ''));

  // Undo puts the pre-fix formulas back and switches the hourly refresh off
  ctx.rollback();
  var restored = PACING_TABS.every(function (t) { return JSON.stringify(formulaGrid(ss.getSheetByName(t))) === before[t]; });
  check(restored, 'Undo "Fix this workbook" restores both pacing tabs to the formulas they had before the first run');
  check(ctx.ScriptApp.getProjectTriggers().length === 0, 'Undo removes the hourly trigger');

  /* ---- V4: Raw data, Raw manual, Adjust Raw and APPLE1 are IMPORTRANGE mirrors ---- */
  console.log('   -- the same repair when the sources are IMPORTRANGE mirrors --');
  var ss2 = makeSpreadsheet(fx.workbook(false), 'UTC');
  var MIRROR = { 'Raw data': 15, 'Raw manual': 15, 'Adjust Raw': 11, 'APPLE1': 15 }, writes = [];
  Object.keys(MIRROR).forEach(function (name) {
    var sh = ss2.getSheetByName(name), width = MIRROR[name], put = sh.put.bind(sh);
    sh.f['1,1'] = '=IMPORTRANGE("1srcKey","' + name + '!A:O")';
    sh.put = function (row, c, x) { if (c <= width) writes.push(name + '!' + colName(c - 1) + row); return put(row, c, x); };
  });
  var ctx2 = loadServer(files.gs, ss2);
  ctx2.writeFormulas_(ss2, ctx2.PACING_ALL);
  ctx2.fixThisWorkbook();
  check(writes.length === 0, 'no write into an imported column (' + writes.slice(0, 5).join(' ') + ')');
  var raw2 = ss2.getSheetByName('Raw data');
  check(raw2.cell(1, col) === 'Objective' && raw2.getRange(ctx2.CFG.OBJECTIVE_COL + '2').getFormula() === ctx2.objectiveColumnFormula_(),
    'objective column added beside the import, in ' + ctx2.CFG.OBJECTIVE_COL);
  check(!!ss2.getSheetByName(ctx2.CFG.ADJUST_CLEAN), '"Adjust Clean" built from the mirrored Adjust Raw');
  check(!ss2.sheets.some(function (x) { return /^Raw manual BACKUP /.test(x.name); }),
    'imported Raw manual left as it is (no conversion, no backup)');
  var refused = '';
  try { ctx2.importAdjustCsv([[['day', 'network', 'campaign_network', 'app', 'all_revenue', 'paid_installs', 'installs',
    'bookingconfirmed_events'], ['2026-09-01', 'Facebook Installs', 'x', 'Six Flags', 1, 1, 1, 1]]]); } catch (e) { refused = e.message; }
  check(/IMPORTRANGE/.test(refused), 'the CSV importer refuses to write into the mirrored Adjust Raw');
  console.log('   Fix this workbook: ' + (fails.length ? fails.length + ' check(s) failed' : 'every check passed'));
  return fails.length;
}

/* ------------------------------------------------------------------ run */
function runVersion(label, files, opts) {
  console.log('\n==================== ' + label + ' ====================');
  var wb = fx.workbook(opts.newRawData);
  if (opts.dropBlankChannel) {
    // the original server throws "missing channel or objective" on a blank channel and the
    // whole dashboard fails to load, so its counting can only be measured without that row
    var before = wb['Adjust Raw'].length;
    wb['Adjust Raw'] = wb['Adjust Raw'].filter(function (r, i) { return i === 0 || (r[9] !== '' && r[10] !== ''); });
    console.log('(fixture: ' + (before - wb['Adjust Raw'].length) + ' blank-channel Adjust rows removed — they crash the original code)');
  }
  var ss = makeSpreadsheet(wb, 'UTC');
  var ctx = loadServer(files.gs, ss);
  // the generated formulas read "Adjust Clean", which Fix this workbook builds
  if (opts.newRawData && ctx._refreshAdjustClean_) ctx._refreshAdjustClean_(true);
  var spec = opts.newRawData ? ctx.buildPacingSpec_() : ctx.PACING_ALL;
  var vals = evaluatePacing(sheetToWb(ss), spec);
  putPacing(ss, vals);

  var payload = ctx.getPacingDashboardData();
  try { ctx.validateDashboard(); } catch (e) { console.log('validateDashboard threw: ' + e.message); }
  var vsh = ss.getSheetByName('Dashboard Validation');
  if (vsh) {
    var result = vsh.v[2];
    console.log('validateDashboard (server payload vs tab): ' + result.slice(1, 5).join(' · '));
    vsh.v.filter(function (r) { return r[5] === 'CHECK' && r[0] !== 'FIX'; }).slice(0, 8)
      .forEach(function (r) { console.log('   CHECK ' + r.slice(0, 5).join(' | ')); });
  }

  var w = loadClient(files.html, payload);
  var expect = vals;
  var diffs = compareClient(w, expect, label);
  console.log('Dashboard page vs pacing tab: ' + diffs.length + ' line/total figures differ');
  diffs.slice(0, 40).forEach(function (d) { console.log('   ' + d); });
  ['SFQC', 'AAQC'].forEach(function (b) {
    var k = kpis(w, b), tab = vals[b + ' Pacing_Daily'];
    console.log('   ' + b + ' KPI cards: ' + JSON.stringify(k));
    console.log('   ' + b + ' pacing row 28: spend SAR ' + Math.round(pv(tab, 'F28')) + ' · revenue ' + Math.round(pv(tab, 'X28')) +
      ' · Adjust installs ' + Math.round(pv(tab, 'L28')) + ' · Adjust purchases ' + Math.round(pv(tab, 'K28')) +
      ' · ROAS ' + pv(tab, 'P28').toFixed(2));
  });
  var problems = renderAllViews(w);
  console.log('Rendering every view × portal × filter: ' + (problems.length ? problems.join('; ') : 'no errors'));
  if (payload.meta && payload.meta.health) {
    console.log('Data issues reported by the dashboard (' + payload.meta.health.issues.length + '):');
    payload.meta.health.issues.forEach(function (i) { console.log('   [' + i.level + '] ' + i.text.slice(0, 160)); });
  }
  w.close();
  return { ss: ss, ctx: ctx, vals: vals, diffs: diffs, problems: problems, payload: payload };
}

/* Evaluate the tab from the sheet as it is now, then compare server and page with it. */
function recheck(label, ctx, ss, files) {
  var vals = evaluatePacing(sheetToWb(ss), ctx.buildPacingSpec_());
  putPacing(ss, vals);
  var p = ctx.getPacingDashboardData();
  ctx.validateDashboard();
  var vsh = ss.getSheetByName('Dashboard Validation');
  var bad = vsh.v.filter(function (r) { return r[5] === 'CHECK' && r[0] !== 'FIX' && r[0] !== 'RESULT'; });
  console.log('validateDashboard (server payload vs tab): ' + vsh.v[2].slice(1, 5).join(' · '));
  bad.slice(0, 8).forEach(function (r) { console.log('   CHECK ' + r.slice(0, 5).join(' | ')); });
  var w = loadClient(files.html, p);
  var d = compareClient(w, vals, label);
  console.log('Dashboard page vs pacing tab: ' + d.length + ' line/total figures differ');
  d.slice(0, 20).forEach(function (x) { console.log('   ' + x); });
  ['SFQC', 'AAQC'].forEach(function (b) {
    var k = kpis(w, b), tab = vals[b + ' Pacing_Daily'];
    console.log('   ' + b + ' Revenue card ' + k.Revenue + ' · ROAS card ' + k.ROAS + ' | tab X28 ' +
      Math.round(pv(tab, 'X28')) + ' · P28 ' + pv(tab, 'P28').toFixed(2));
  });
  w.close();
  return bad.length + d.length;
}

function main() {
  var args = process.argv.slice(2), oldDir = null;
  if (args[0] === '--old') oldDir = args[1];
  var failures = 0;
  if (oldDir) {
    runVersion('ORIGINAL CODE', { gs: [path.join(oldDir, 'Code.gs'), path.join(oldDir, 'Untitled.gs')],
      html: path.join(oldDir, 'Dashboard.html') }, { newRawData: false, dropBlankChannel: true });
  }
  var files = { gs: [path.join(ROOT, 'Code.gs'), path.join(ROOT, 'Untitled.gs')], html: path.join(ROOT, 'Dashboard.html') };
  var cur = runVersion('FIXED CODE', files, { newRawData: true });
  failures += cur.diffs.length + cur.problems.length;
  var vsh = cur.ss.getSheetByName('Dashboard Validation');
  var bad = vsh.v.filter(function (r) { return r[5] === 'CHECK' && r[0] !== 'FIX' && r[0] !== 'RESULT'; }).length;
  failures += bad;

  /* ---- Clean Adjust Raw, then everything again on the repaired sheet ---- */
  console.log('\n==================== FIXED CODE after "Clean Adjust Raw" ====================');
  var msg = cur.ctx.cleanAdjustRaw();
  console.log(msg.split('\n').map(function (l) { return '   ' + l; }).join('\n'));
  var wb2 = sheetToWb(cur.ss);
  var vals2 = evaluatePacing(wb2, cur.ctx.buildPacingSpec_());
  putPacing(cur.ss, vals2);
  var p2 = cur.ctx.getPacingDashboardData();
  cur.ctx.validateDashboard();
  var vsh2 = cur.ss.getSheetByName('Dashboard Validation');
  console.log('validateDashboard (server payload vs tab): ' + vsh2.v[2].slice(1, 5).join(' · '));
  var w2 = loadClient(files.html, p2);
  var d2 = compareClient(w2, vals2, 'after clean');
  console.log('Dashboard page vs pacing tab: ' + d2.length + ' line/total figures differ');
  d2.slice(0, 20).forEach(function (d) { console.log('   ' + d); });
  console.log('Data issues still reported (' + p2.meta.health.issues.length + '):');
  p2.meta.health.issues.forEach(function (i) { console.log('   [' + i.level + '] ' + i.text.slice(0, 160)); });
  failures += d2.length + vsh2.v.filter(function (r) { return r[5] === 'CHECK' && r[0] !== 'FIX' && r[0] !== 'RESULT'; }).length;
  var adjustLeft = p2.meta.health.issues.filter(function (i) { return /Adjust/.test(i.text) && i.level === 'crit'; }).length;
  if (adjustLeft) { console.log('FAIL: critical Adjust issues remain after cleaning'); failures++; }
  // Adjust Raw is never modified; a second rebuild of Adjust Clean changes nothing
  var rawBefore = JSON.stringify(cur.ss.getSheetByName('Adjust Raw').v);
  var before = JSON.stringify(cur.ss.getSheetByName('Adjust Clean').v);
  cur.ctx.cleanAdjustRaw();
  if (JSON.stringify(cur.ss.getSheetByName('Adjust Clean').v) !== before) { console.log('FAIL: second clean changed Adjust Clean'); failures++; }
  if (JSON.stringify(cur.ss.getSheetByName('Adjust Raw').v) !== rawBefore) { console.log('FAIL: clean modified Adjust Raw'); failures++; }
  else console.log('Second "Clean Adjust Raw" run: no changes (idempotent)');
  w2.close();

  /* ---- the CSV importer writes into Adjust Raw and replaces the days it covers ---- */
  console.log('\n==================== FIXED CODE after an Adjust CSV import ====================');
  var head = ['day', 'network', 'campaign_network', 'app', 'all_revenue', 'general revenue_revenue_est',
    'paid_installs', 'installs', 'bookingconfirmed_events', 'os_name'];
  var csv = [head];
  var importDays = [];
  for (var dd = 20; dd <= 30; dd++) importDays.push('2026-09-' + dd);
  importDays.forEach(function (day) {
    csv.push([day, 'Facebook Installs', 'SFQC_Meta_App_iOS', 'Six Flags', '100.5', '100.5', '7', '9', '2', 'ios']);
    csv.push([day, 'Facebook Installs', 'SFQC_Meta_App_iOS', 'Six Flags', '50', '50', '3', '4', '1', 'android']);
    csv.push([day, 'Google Ads YouTube', 'SFQC_YT_Bumper', 'Six Flags', '0', '0', '5', '6', '0', 'ios']);
    csv.push([day, 'Snapchat Installs', 'SFQC_snapchat_awr_Reach', 'Six Flags', '20', '20', '2', '2', '1', 'ios']);
    csv.push([day, 'TikTok SAN', 'SFQC_TT_Search_Brand', 'Six Flags', '30', '30', '3', '3', '1', 'ios']);
    csv.push([day, 'Twitter Installs', 'SFQC_X_AWR_Video', 'Six Flags', '0', '0', '1', '1', '0', 'ios']);
    csv.push([day, 'Organic', 'Organic', 'Six Flags', '999', '999', '0', '50', '9', 'ios']);
  });
  console.log('   ' + cur.ctx.importAdjustCsv([csv]).split('\n').join('\n   '));
  var arows = cur.ss.getSheetByName('Adjust Raw').v.slice(1).filter(function (r) {
    return r[0] instanceof Date && r[3] === 'Six Flags' && fx.iso(r[0]) >= '2026-09-20' && fx.iso(r[0]) <= '2026-09-30';
  });
  var fb = arows.filter(function (r) { return r[1] === 'Facebook Installs' && fx.iso(r[0]) === '2026-09-25'; });
  var importOk = arows.length === importDays.length * 6 && fb.length === 1 && fb[0][7] === 13 && fb[0][8] === 3;
  var labels = {};
  arows.forEach(function (r) { labels[r[1]] = r[9] + ' / ' + r[10]; });
  console.log('   Six Flags rows for 20-30 Sep now: ' + arows.length + ' (expected ' + importDays.length * 6 +
    '); Facebook 25 Sep installs ' + (fb[0] && fb[0][7]) + ' (iOS 9 + Android 4) · labels ' + JSON.stringify(labels));
  if (!importOk) { console.log('FAIL: import did not replace the period / sum the breakdown'); failures++; }
  failures += recheck('after import', cur.ctx, cur.ss, files);

  /* ---- the GA4-revenue switch moves the tab and the dashboard together ---- */
  var ga4Default = !!cur.ctx.CFG.WEB_REVENUE_FROM_GA4;
  console.log('\n==================== FIXED CODE with CFG.WEB_REVENUE_FROM_GA4 = ' + !ga4Default + ' ====================');
  cur.ctx.CFG.WEB_REVENUE_FROM_GA4 = !ga4Default;
  failures += recheck('web revenue switched', cur.ctx, cur.ss, files);
  cur.ctx.CFG.WEB_REVENUE_FROM_GA4 = ga4Default;

  failures += fixStage(files);

  console.log('\n' + (failures ? 'FAILED — ' + failures + ' problem(s)' : 'PASSED — the dashboard equals the pacing tabs, line by line and in total'));
  process.exit(failures ? 1 : 0);
}
if (require.main === module) main();
else module.exports = { makeSpreadsheet: makeSpreadsheet, loadServer: loadServer, evaluatePacing: evaluatePacing,
  putPacing: putPacing, sheetToWb: sheetToWb, loadClient: loadClient, compareClient: compareClient,
  kpis: kpis, pv: pv, serial: serial, fromSerial: fromSerial, colIndex: colIndex, colName: colName };
