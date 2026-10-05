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
 *   5. runs "Clean Adjust Raw" and checks again.
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
  var s = String(v).replace(/,/g, '').trim();
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
  function Sheet(name, values) {
    this.name = name; this.hidden = false; this.fmt = {};
    this.v = values.map(function (r) { return r.map(function (x) { return x === undefined || x === null ? '' : x; }); });
  }
  Sheet.prototype.getName = function () { return this.name; };
  Sheet.prototype.setName = function (n) { this.name = n; return this; };
  Sheet.prototype.hideSheet = function () { this.hidden = true; return this; };
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
  Sheet.prototype.setFrozenRows = function () { return this; };
  Sheet.prototype.setColumnWidth = function () { return this; };
  Sheet.prototype.setConditionalFormatRules = function () { return this; };
  Sheet.prototype.clear = function () { this.v = []; return this; };
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
  Range.prototype.getDisplayValues = function () {
    return this.getValues().map(function (row) {
      return row.map(function (x) {
        return x instanceof Date ? (x.getUTCMonth() + 1) + '/' + x.getUTCDate() + '/' + x.getUTCFullYear() : String(x);
      });
    });
  };
  Range.prototype.getFormulas = function () { return this.getValues().map(function (row) { return row.map(function () { return ''; }); }); };
  Range.prototype.getFormula = function () { return ''; };
  Range.prototype.setValues = function (vals) {
    var sh = this.sh;
    this.each(function (r, c, i, j) {
      var x = vals[i][j];
      if (typeof x === 'string' && sh.fmt[c] !== '@') {
        if (/^\d{4}-\d{2}-\d{2}$/.test(x)) x = fx.D(x);                      // Sheets parses ISO dates
        else if (/^-?\d+(\.\d+)?$/.test(x)) x = Number(x);
      }
      sh.put(r, c, x);
    });
    return this;
  };
  Range.prototype.setValue = function (x) { this.sh.put(this.r, this.c, x); return this; };
  Range.prototype.setFormula = function (f) { this.sh.put(this.r, this.c, f); return this; };
  Range.prototype.clearContent = function () { var sh = this.sh; this.each(function (r, c) { if (sh.v[r - 1]) sh.put(r, c, ''); }); return this; };
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
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(date)
    .forEach(function (x) { p[x.type] = x.value; });
  return fmt.replace('yyyy', p.year).replace('MM', p.month).replace('dd', p.day).replace('HH', p.hour).replace('mm', p.minute);
}
function loadServer(files, ss) {
  var logs = [];
  var ctx = {
    SpreadsheetApp: {
      getActive: function () { return ss; }, getActiveSpreadsheet: function () { return ss; },
      openById: function () { return ss; }, flush: function () {},
      getUi: function () { throw new Error('no UI'); },
      newConditionalFormatRule: function () { var b = { whenTextEqualTo: function () { return b; }, setBackground: function () { return b; }, setRanges: function () { return b; }, build: function () { return {}; } }; return b; }
    },
    Utilities: { formatDate: formatDate },
    Logger: { log: function () { logs.push([].slice.call(arguments).join(' ')); } },
    Session: { getEffectiveUser: function () { return { getEmail: function () { return 'test@example.com'; } }; } },
    LockService: { getDocumentLock: function () { return { waitLock: function () {}, releaseLock: function () {} }; } },
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
function close(a, b) { return Math.abs(a - b) <= Math.max(0.02, Math.abs(b) * 0.0005); }

function compareClient(w, vals, label) {
  var diffs = [];
  ['SFQC', 'AAQC'].forEach(function (brand) {
    w.setBrand(brand);
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
  var spec = opts.newRawData ? ctx.buildPacingSpec_() : ctx.PACING_ALL;
  var vals = evaluatePacing(wb, spec);
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
  var diffs = compareClient(w, vals, label);
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
  var adjustLeft = p2.meta.health.issues.filter(function (i) { return /Adjust/.test(i.text); }).length;
  if (adjustLeft) { console.log('FAIL: Adjust issues remain after cleaning'); failures++; }
  // idempotent: a second clean changes nothing
  var before = JSON.stringify(cur.ss.getSheetByName('Adjust Raw').v);
  cur.ctx.cleanAdjustRaw();
  if (JSON.stringify(cur.ss.getSheetByName('Adjust Raw').v) !== before) { console.log('FAIL: second clean changed Adjust Raw'); failures++; }
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
  console.log('\n==================== FIXED CODE with CFG.WEB_REVENUE_FROM_GA4 = true ====================');
  cur.ctx.CFG.WEB_REVENUE_FROM_GA4 = true;
  failures += recheck('GA4 web revenue', cur.ctx, cur.ss, files);
  cur.ctx.CFG.WEB_REVENUE_FROM_GA4 = false;

  console.log('\n' + (failures ? 'FAILED — ' + failures + ' problem(s)' : 'PASSED — the dashboard equals the pacing tabs, line by line and in total'));
  process.exit(failures ? 1 : 0);
}
main();
