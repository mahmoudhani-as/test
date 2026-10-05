/**
 * A synthetic copy of the Daily Report workbook that contains every trap found while
 * diagnosing the dashboard: campaign names that match two wildcards, X and Google
 * campaigns no old row caught, pre-launch rows before the date floors, duplicate
 * campaign/day rows, an old-naming backup that overlaps the live data, Adjust rows with
 * text dates and overlapping imports, odd channel/objective labels, cross-brand Adjust
 * rows, GA4 sources the old dashboard bucketed differently, and so on.
 *
 * Dates are JS Dates at UTC midnight; the mock spreadsheet's time zone is UTC.
 */
'use strict';

function D(iso) { var p = iso.split('-').map(Number); return new Date(Date.UTC(p[0], p[1] - 1, p[2])); }
function iso(d) { return d.toISOString().slice(0, 10); }
function days(from, till) {
  var out = [], d = D(from), e = D(till);
  while (d <= e) { out.push(iso(d)); d = new Date(d.getTime() + 86400000); }
  return out;
}
var seed = 7;
function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
function n(lo, hi) { return Math.round(lo + rnd() * (hi - lo)); }
function money(lo, hi) { return Math.round((lo + rnd() * (hi - lo)) * 100) / 100; }

var WINDOW = { from: '2026-06-28', till: '2026-09-30' };
var ALL_DAYS = days('2026-06-25', '2026-10-02');      // platform tabs run past both ends

/* ---- campaigns per platform: [name, account brand (for Apple), active from, active till] ---- */
var CAMPS = {
  Snapchat: [
    ['SFQC_snapchat_awr_Reach', '2026-06-25', '2026-10-02'],
    ['SFQC_Snapchat_AWRN_Takeover', '2026-07-05', '2026-08-20'],     // matched *snapchat_awr* AND *_AWRN_*
    ['First Story Takeover Jul', '2026-07-10', '2026-07-12'],        // SFQC only through "First Story"
    ['SFQC_Snap_Takeover_Aug', '2026-08-10', '2026-08-14'],          // a takeover with no old token
    ['SFQC_SC_App_CONV_iOS', '2026-06-25', '2026-10-02'],
    ['AAQC_snapchat_awr_Reach', '2026-06-25', '2026-10-02'],
    ['AAQC_SC_App_CONV_And', '2026-06-29', '2026-10-02'],
    ['Generic_Snapchat_Test', '2026-07-01', '2026-07-20']            // no portal token -> UNMAPPED
  ],
  TikTok: [
    ['SFQC_tiktok_awr_TopView', '2026-06-25', '2026-10-02'],
    ['SFQC_TikTok_RF_AWRN_TopFeed', '2026-07-01', '2026-09-15'],     // both awareness wildcards
    ['SFQC_TT_Search_Brand', '2026-07-01', '2026-10-02'],
    ['SFQC_CONV_SAL_TT_Search', '2026-08-01', '2026-09-30'],         // both search wildcards
    ['SFQC_TikTok_AWRN_TT_Search_Test', '2026-09-01', '2026-09-05'], // awareness AND search
    ['SFQC_TikTok_App_Android', '2026-06-25', '2026-10-02'],
    ['AAQC_tiktok_awr_TopView', '2026-06-25', '2026-10-02'],
    ['AAQC_TikTok_App_iOS', '2026-06-25', '2026-10-02']
  ],
  X: [
    ['SFQC_X_AWR_Video', '2026-06-25', '2026-10-02'],
    ['SFQC_X_App_iOS', '2026-06-29', '2026-10-02'],
    ['SFQC_X_Web_Traffic', '2026-07-15', '2026-08-15'],              // neither *x_awr* nor *_x_app*
    ['AAQC_X_App_Android', '2026-06-29', '2026-10-02']
  ],
  Google: [
    ['SFQC_YT_Bumper', '2026-06-25', '2026-10-02'],                  // YouTube runs before 2 Jul
    ['SFQC_SEM_Brand', '2026-06-25', '2026-10-02'],
    ['SFQC_UAC_App_Installs', '2026-06-25', '2026-10-02'],
    ['SFQC_YT_SEM_Test', '2026-08-01', '2026-08-31'],                // *_YT_* and *sem*
    ['AAQC_SEM_Brand', '2026-06-25', '2026-10-02'],
    ['AAQC_UAC_App_Installs', '2026-06-25', '2026-10-02']
  ],
  Meta: [
    ['SFQC_Meta_App_iOS', '2026-06-25', '2026-10-02'],
    ['AAQC_Meta_App_Android', '2026-06-25', '2026-10-02'],
    ['AQQC_Meta_Retarget', '2026-08-01', '2026-09-30']               // misspelt portal token
  ],
  Apple: [
    ['SFQC_ASA_Brand', 'SFQC - Billed to MS KSA', '2026-06-25', '2026-10-02'],
    ['AAQC_ASA_Brand', 'AAQC - Billed to MS KSA', '2026-06-25', '2026-10-02']
  ]
};
function active(c, d, a, b) { return d >= a && d <= b; }

function platformTabs() {
  var t = {};
  t.META = [['Date', 'Campaign name', 'Reach', 'Impressions', 'Cost', 'Link clicks', 'Clicks (all)',
    'Three-second video views', 'Mobile app installs', 'Mobile app purchases']];
  t.TikTok = [['Date', 'Campaign name', 'Reach', 'Impressions', 'Cost', 'Clicks', 'Clicks (All)',
    '2-second video views', 'App installs', 'Purchase events', 'Purchase events (SKAN)', 'Complete payment events']];
  t.Snapchat = [['Date', 'Campaign name', 'Impressions', 'Cost', 'Swipes', 'Total app installs', 'Purchases', 'Video views']];
  t.Google = [['Date', 'Campaign name', 'Impressions', 'Cost', 'Clicks', 'Video views', 'Conversions']];
  t.Apple = [['Date', 'Account name', 'Campaign name', 'Impressions', 'Taps', 'Cost', 'Total installs']];
  var xh = []; for (var i = 0; i < 56; i++) xh.push('m' + (i + 1));
  xh[0] = 'Date'; xh[1] = 'Campaign'; xh[2] = 'Impressions'; xh[3] = 'Cost'; xh[5] = 'Clicks';
  xh[12] = 'Video views 3s'; xh[19] = 'Installs'; xh[22] = 'Purchases';
  t.X = [xh];
  ALL_DAYS.forEach(function (d) {
    CAMPS.Meta.forEach(function (c) {
      if (!active(c, d, c[1], c[2])) return;
      t.META.push([D(d), c[0], n(800, 4000), n(5000, 30000), money(80, 600), n(50, 300), n(80, 500),
        n(500, 3000), n(5, 60), n(0, 6)]);
      // a second campaign with the very same name on the same day (re-created campaign)
      if (c[0] === 'SFQC_Meta_App_iOS' && d >= '2026-08-20' && d <= '2026-08-25') {
        t.META.push([D(d), c[0], n(100, 400), n(800, 3000), money(20, 90), n(5, 30), n(10, 40),
          n(50, 200), n(1, 8), n(0, 2)]);
      }
    });
    CAMPS.TikTok.forEach(function (c) {
      if (!active(c, d, c[1], c[2])) return;
      t.TikTok.push([D(d), c[0], n(1000, 5000), n(8000, 40000), money(60, 500), n(40, 250), n(60, 400),
        n(800, 5000), n(3, 40), n(0, 3), n(0, 2), n(0, 2)]);
    });
    CAMPS.Snapchat.forEach(function (c) {
      if (!active(c, d, c[1], c[2])) return;
      t.Snapchat.push([D(d), c[0], n(9000, 60000), money(50, 700), n(40, 300), n(2, 50), n(0, 4), n(900, 6000)]);
    });
    CAMPS.Google.forEach(function (c) {
      if (!active(c, d, c[1], c[2])) return;
      t.Google.push([D(d), c[0], n(4000, 20000), money(40, 400), n(60, 500), n(0, 2000), n(2, 40)]);
    });
    CAMPS.Apple.forEach(function (c) {
      if (!active(c, d, c[2], c[3])) return;
      t.Apple.push([D(d), c[1], c[0], n(500, 3000), n(20, 200), money(20, 200), n(5, 40)]);
    });
    CAMPS.X.forEach(function (c) {
      if (!active(c, d, c[1], c[2])) return;
      var r = new Array(56).fill(0);
      r[0] = D(d); r[1] = c[0]; r[2] = n(5000, 25000); r[3] = money(100, 900);   // SAR
      r[5] = n(30, 200); r[12] = n(300, 3000); r[19] = n(0, 20); r[22] = n(0, 3);
      t.X.push(r);
    });
  });
  return t;
}

/* Raw manual: the platforms with no connector. InMobi numbers are text with commas. */
function rawManual() {
  var rows = [['A', 'Campaign', 'Campaign name', 'Day', 'Reach', 'Impressions', 'Amount spent (USD)',
    'Link clicks', 'Clicks (all)', '3-second video plays', 'App installs', 'Purchases']];
  days('2026-07-01', '2026-09-30').forEach(function (d) {
    var spend = money(500, 1500);
    rows.push(['InMobi', 'SFQC', 'SFQC_InMobi_DSP', D(d), 0, String(n(10000, 90000)),
      spend.toLocaleString('en-US'), String(n(50, 300)), String(n(60, 400)), 0, String(n(5, 50)), String(n(0, 4))]);
    if (d >= '2026-08-01') {
      rows.push(['InMobi', 'AAQC', 'AAQC_InMobi_DSP', D(d), 0, String(n(5000, 40000)),
        money(200, 900).toLocaleString('en-US'), '10', '12', 0, '3', '0']);
    }
    rows.push(['Bidease', 'SFQC', 'SFQC_Bidease_iOS', D(d), 0, n(5000, 20000), money(100, 400), n(10, 80), n(20, 90), 0, n(2, 20), n(0, 2)]);
    if (d >= '2026-07-20') rows.push(['InMotion', 'AAQC', 'AAQC_InMotion', D(d), 0, n(3000, 9000), money(50, 200), n(5, 40), n(5, 50), 0, n(1, 9), 0]);
  });
  return rows;
}

/* The backup of the pre-Supermetrics Raw data (taken 7 Aug): the same deliveries under
   older campaign spellings, plus InMobi history that differs slightly from Raw manual. */
function rawBackup() {
  var rows = [['A', 'Campaign', 'Campaign name', 'Day', 'Reach', 'Impressions', 'Amount spent (USD)',
    'Link clicks', 'Clicks (all)', '3-second video plays', 'App installs', 'Purchases']];
  days('2026-07-01', '2026-08-07').forEach(function (d) {
    rows.push(['Meta', 'SFQC', 'SFQC Meta App iOS', D(d), n(800, 4000), n(5000, 30000), money(80, 600), n(50, 300), n(80, 500), n(500, 3000), n(5, 60), n(0, 6)]);
    rows.push(['TikTok', 'SFQC', 'SFQC_TikTok_App_Android ', D(d), n(800, 4000), n(5000, 30000), money(60, 500), n(40, 250), n(60, 400), n(800, 5000), n(3, 40), n(0, 3)]);
    rows.push(['InMobi', 'SFQC', 'SFQC_InMobi_DSP', D(d), 0, n(10000, 90000), money(500, 1500), n(50, 300), n(60, 400), 0, n(5, 50), n(0, 4)]);
  });
  return rows;
}

function apple1() {
  var rows = [['Date', 'App Name', 'Campaign Name', 'Spend', 'Impressions', 'Taps', 'Installs (Total)']];
  ALL_DAYS.forEach(function (d) {
    rows.push([D(d), 'Six Flags Qiddiya City', 'SFQC_ASA_Brand', money(30, 250), n(500, 3000), n(20, 200), n(5, 40)]);
    rows.push([D(d), 'Aquarabia Qiddiya City', 'AAQC_ASA_Brand', money(20, 150), n(300, 2000), n(10, 120), n(3, 30)]);
  });
  return rows;
}

/* Adjust Raw: A day, B network, C campaign, D app, E revenue, F est revenue, G paid installs,
   H installs, I bookings, J channel, K objective. */
function adjustRaw() {
  var rows = [['day', 'network', 'campaign_network', 'app', 'all_revenue', 'general revenue_revenue_est',
    'paid_installs', 'installs', 'bookingconfirmed_events', 'channel', 'objective']];
  var spec = [
    ['Snapchat Installs', 'SFQC_snapchat_awr_Reach', 'Six Flags', 'Snapchat', 'Awareness'],
    ['Snapchat Installs', 'SFQC_SC_App_CONV_iOS', 'Six Flags', 'Snapchat', 'Conversion'],
    ['Snapchat Installs', 'SFQC_SC_App_CONV_iOS', 'Six Flags', 'Snapchat', 'Search'],        // odd label
    ['Snapchat Installs', 'AAQC_SC_App_CONV_And', 'Aquarabia', 'Snapchat', 'Conversion'],
    ['TikTok SAN', 'SFQC_tiktok_awr_TopView', 'Six Flags', 'TikTok', 'Awareness'],
    ['TikTok SAN', 'SFQC_TT_Search_Brand', 'Six Flags', 'TikTok', 'Search'],
    ['TikTok SAN', 'SFQC_TikTok_App_Android', 'Six Flags', 'TikTok', 'Conversion'],
    ['TikTok SAN', 'AAQC_TikTok_App_iOS', 'Aquarabia', 'TikTok', 'Conversion'],
    ['Twitter Installs', 'SFQC_X_App_iOS', 'Six Flags', 'Other', 'Conversion'],             // X filed as Other
    ['Twitter Installs', 'SFQC_X_AWR_Video', 'Six Flags', 'X', 'Awareness'],
    ['Google Ads YouTube', 'SFQC_YT_Bumper', 'Six Flags', 'Google', 'YouTube'],
    ['Google Ads Video', 'SFQC_YT_Bumper', 'Six Flags', 'Google', 'Awareness'],              // label variant
    ['Google Ads Search', 'SFQC_SEM_Brand', 'Six Flags', 'Google', 'Search'],
    ['Google Ads ACI', 'SFQC_UAC_App_Installs', 'Six Flags', 'Google', 'Conversion'],
    ['Google Ads ACI', 'AAQC_UAC_App_Installs', 'Aquarabia', 'Google', 'Conversion'],
    ['Facebook Installs', 'SFQC_Meta_App_iOS', 'Six Flags', 'Meta', 'Conversion'],
    ['Instagram Installs', 'SFQC_Meta_App_iOS', 'Six Flags', 'Meta', 'Awareness'],           // lumped channel
    ['Facebook Installs', 'AAQC_Meta_App_Android', 'Aquarabia', 'Meta', 'Conversion'],
    ['Facebook Installs', 'SFQC_Meta_App_iOS', 'Aquarabia', 'Meta', 'Conversion'],           // SFQC name, AAQC app
    ['Apple Search Ads', 'unknown', 'Six Flags', 'Apple', 'Conversion'],
    ['Apple Search Ads', 'unknown', 'Aquarabia', 'Apple', 'Conversion'],
    ['Bidease', 'SFQC_Bidease_iOS', 'Six Flags', 'Bidease', 'Conversion'],
    ['InMotion', 'AAQC_InMotion', 'Aquarabia', 'InMotion', 'Conversion'],
    ['Untrusted Devices', 'Expired Attributions', 'Six Flags', 'Other', 'Conversion'],
    ['Unattributed', 'unknown', 'Six Flags', '', ''],                                         // blank channel
    ['Organic', 'Organic', 'Six Flags', 'Organic', 'Organic'],
    ['Organic', 'Organic', 'Aquarabia', 'Organic', 'Organic']
  ];
  days('2026-06-26', '2026-10-01').forEach(function (d) {
    spec.forEach(function (s, i) {
      if (rnd() < 0.15) return;
      var inst = n(0, 40), book = n(0, 8), rev = money(0, 900) * (book ? 1 : 0);
      var cell = D(d);
      // a September batch pasted by hand: unambiguous days arrive as text
      if (d >= '2026-09-13' && d <= '2026-09-15' && i % 5 === 0) cell = d.slice(8, 10) + '/' + d.slice(5, 7) + '/' + d.slice(0, 4);
      rows.push([cell, s[0], s[1], s[2], rev, rev, inst, inst + n(0, 5), book, s[3], s[4]]);
    });
  });
  // an overlapping re-import of 31 Aug: the same rows appended again
  var again = rows.filter(function (r) { return r[0] instanceof Date && iso(r[0]) === '2026-08-31'; })
    .map(function (r) { return r.slice(); });
  return rows.concat(again);
}

/* GA4: A account, B property, C date, D campaign, E channel group, F source / medium,
   G transactions, H revenue. */
function ga4() {
  var rows = [['Account name', 'GA4 property', 'Date', 'Session campaign name', 'Session default channel grouping',
    'Session source / medium', 'Transactions', 'Purchase revenue']];
  var spec = [
    ['Six Flags Qiddiya City', 'SFQC_snapchat_awr_Reach', 'Paid Social', 'snapchat / paid'],
    ['Six Flags Qiddiya City', 'SFQC_TT_Search_Brand', 'Paid Search', 'tiktok / cpc'],
    ['Six Flags Qiddiya City', 'SFQC_tiktok_awr_TopView', 'Paid Social', 'tiktok / paid'],
    ['Six Flags Qiddiya City', 'SFQC_SEM_Brand', 'Paid Search', 'google / cpc'],
    ['Six Flags Qiddiya City', 'SFQC_Meta_App_iOS', 'Paid Social', 'facebook / paid'],
    ['Six Flags Qiddiya City', 'SFQC_Meta_App_iOS', 'Paid Social', 'ig / paid'],
    ['Six Flags Qiddiya City', 'SFQC_X_Web_Traffic', 'Paid Social', 'x / paid'],
    ['Six Flags Qiddiya City', '(referral)', 'Paid Social', 'l.snapchat.com / referral'],
    ['Six Flags Qiddiya City', 'newsletter', 'paid search', 'email / cpc'],               // lowercase group
    ['Six Flags Qiddiya City', '(organic)', 'Organic Search', 'google / organic'],
    ['Aquarabia Qiddiya City ', 'AAQC_SEM_Brand', 'Paid Search', 'google / cpc'],       // trailing space
    ['Aquarabia - Web', 'AAQC_Meta_App_Android', 'Paid Social', 'meta / paid'],          // other property name
    ['Aquarabia Qiddiya City ', '(organic)', 'Organic Social', 'instagram / social']
  ];
  days('2026-06-26', '2026-10-01').forEach(function (d) {
    spec.forEach(function (s) {
      if (rnd() < 0.2) return;
      var tx = n(0, 12);
      rows.push(['acct', s[0], D(d), s[1], s[2], s[3], tx, tx ? money(150, 900) * tx : 0]);
    });
  });
  return rows;
}

/* ---- Raw data, computed the way RAW_FORMULA computes it ---- */
var OBJ_TOKENS = {
  Snapchat: { Awareness: ['snapchat_awr', '_awrn_', 'takeover', 'take over', 'take-over', 'first story', 'first_story', 'first-story'] },
  TikTok: { Awareness: ['tiktok_awr', '_awrn_'], Search: ['_tt_search', '_conv_sal_'] },
  X: { Awareness: ['x_awr'] },
  Google: { Awareness: ['_yt_'], Search: ['sem'] }
};
function objective(plat, camp) {
  var c = String(camp).toLowerCase(), r = OBJ_TOKENS[plat] || {};
  for (var o of ['Awareness', 'Search']) for (var t of (r[o] || [])) if (c.indexOf(t) >= 0) return o;
  return 'Conversion';
}
function brandOf(text, plat, newRule) {
  var u = String(text).toUpperCase();
  if (/SFQC|SIX[ _-]?FLAGS/.test(u) || (plat === 'Snapchat' && /FIRST STORY/.test(u))) return 'SFQC';
  if ((newRule ? /AAQC|AQQC|AQC[-_]|AQUARABIA/ : /AAQC|AQC[-_]|AQUARABIA/).test(u)) return 'AAQC';
  return 'UNMAPPED';
}
function rawData(tabs, manual, newRule) {
  function hdr(t) { var h = {}; t[0].forEach(function (x, i) { h[x] = i; }); return h; }
  function v(x) { return x === '' || x === null || x === undefined ? 0 : x; }
  var out = [];
  var m = hdr(tabs.META);
  tabs.META.slice(1).forEach(function (r) {
    out.push(['Meta', brandOf(r[1], 'Meta', newRule), r[1], r[0], v(r[m.Reach]), v(r[m.Impressions]), v(r[m.Cost]),
      v(r[m['Link clicks']]), v(r[m['Clicks (all)']]), v(r[m['Three-second video views']]),
      v(r[m['Mobile app installs']]), v(r[m['Mobile app purchases']])]);
  });
  var t = hdr(tabs.TikTok);
  tabs.TikTok.slice(1).forEach(function (r) {
    out.push(['TikTok', brandOf(r[1], 'TikTok', newRule), r[1], r[0], v(r[t.Reach]), v(r[t.Impressions]), v(r[t.Cost]),
      v(r[t.Clicks]), v(r[t['Clicks (All)']]), v(r[t['2-second video views']]), v(r[t['App installs']]),
      v(r[t['Purchase events']]) + v(r[t['Purchase events (SKAN)']]) + v(r[t['Complete payment events']])]);
  });
  var s = hdr(tabs.Snapchat);
  tabs.Snapchat.slice(1).forEach(function (r) {
    out.push(['Snapchat', brandOf(r[1], 'Snapchat', newRule), r[1], r[0], 0, v(r[s.Impressions]), v(r[s.Cost]), 0,
      v(r[s.Swipes]), v(r[s['Video views']]), v(r[s['Total app installs']]), v(r[s.Purchases])]);
  });
  var g = hdr(tabs.Google);
  tabs.Google.slice(1).forEach(function (r) {
    var conv = v(r[g.Conversions]), nm = String(r[1]).toLowerCase();
    out.push(['Google', brandOf(r[1], 'Google', newRule), r[1], r[0], 0, v(r[g.Impressions]), v(r[g.Cost]), 0,
      v(r[g.Clicks]), v(r[g['Video views']]), nm.indexOf('uac') >= 0 || nm.indexOf('app installs') >= 0 ? conv : 0, conv]);
  });
  var a = hdr(tabs.Apple);
  tabs.Apple.slice(1).forEach(function (r) {
    out.push(['Apple', brandOf(r[a['Account name']], 'Apple', newRule), r[a['Campaign name']], r[0], 0,
      v(r[a.Impressions]), v(r[a.Cost]), 0, v(r[a.Taps]), 0, v(r[a['Total installs']]), 0]);
  });
  tabs.X.slice(1).forEach(function (r) {
    out.push(['X', brandOf(r[1], 'X', newRule), r[1], r[0], 0, v(r[2]), v(r[3]), v(r[5]), 0, v(r[12]), v(r[19]), v(r[22])]);
  });
  manual.slice(1).forEach(function (r) { out.push(r.slice(0, 12)); });
  var from = D(WINDOW.from), till = D(WINDOW.till);
  out = out.filter(function (r) { return r[3] instanceof Date && r[3] >= from && r[3] <= till; });
  var head = ['A', 'Campaign', 'Campaign name', 'Day', 'Reach', 'Impressions', 'Amount spent (USD)', 'Link clicks',
    'Clicks (all)', '3-second video plays', 'App installs', 'Purchases'];
  var rows = [head].concat(out);
  // N1:O2 hold the window, as rawData_() writes it
  while (rows[0].length < 15) rows[0].push('');
  rows[0][13] = 'From'; rows[0][14] = 'Till';
  rows[1] = rows[1].slice(); while (rows[1].length < 15) rows[1].push('');
  rows[1][13] = D(WINDOW.from); rows[1][14] = D(WINDOW.till);
  // column P: the objective, as Fix this workbook's P2 formula produces it
  if (newRule) {
    rows.forEach(function (r, i) {
      while (r.length < 16) r.push('');
      r[15] = i === 0 ? 'Objective' : objective(r[0], String(r[2]));
    });
  }
  return rows;
}

function workbook(newRule) {
  seed = 7;
  var tabs = platformTabs();
  var manual = rawManual();
  var wb = {
    'Raw data': rawData(tabs, manual, newRule),
    'Raw manual': manual,
    'Raw data BACKUP 20260807-1642': rawBackup(),
    'APPLE1': apple1(),
    'Adjust Raw': adjustRaw(),
    'GA4': ga4(),
    'SFQC Pacing_Daily': [[], ['', D(WINDOW.from), D(WINDOW.till)]],
    'AAQC Pacing_Daily': [[], ['', D(WINDOW.from), D(WINDOW.till)]]
  };
  Object.keys(tabs).forEach(function (k) { wb[k] = tabs[k]; });
  return wb;
}

module.exports = { workbook: workbook, WINDOW: WINDOW, D: D, iso: iso };
