/* Medical Sales Hub, ICB pack for dermatology emollients. Mounts on #msh-icb-pack.

   WHAT IT IS. A rep picks an Integrated Care Board and an emollient brand and gets one
   editable page of starting figures for a value-proposition pack: national overview,
   the ICB's brand share and trend, the highest-prescribing Primary Care Networks, a
   heat-map of variation across them, dermatology Referral to Treatment waits,
   deprivation, the over-the-counter context, and a ranking of every ICB for picking a
   market access focus. "Save edited copy" downloads the page as it now stands.

   WHERE THE FIGURES COME FROM. data/icb-pack/ (built by scripts/build_icb_pack.py from
   NHSBSA prescribing, NHS England waiting times, the Indices of Deprivation 2025 and
   NHS Digital registered patients, all Open Government Licence). Nothing is computed
   here beyond sums and ratios of those files, and anything the files lack is printed
   as "Not verified" (HUB-VERIFICATION-STANDARD), never filled in.

   DEFINITIONS PRINTED ON THE PAGE, NOT HIDDEN: the market is BNF 130201 plus 2122; a
   brand is the first word of the NHSBSA presentation name; a trend needs a baseline of
   at least index.minBaselineItems items or it reads "too few to trend"; the PCN spread
   is the coefficient of variation of 12-month items per 1,000 registered patients.
   There is no composite score: the focus is picked by reading the columns. */
(function () {
  var MOUNT = document.getElementById('msh-icb-pack');
  if (!MOUNT) return;

  var NAVY = '#0B1C33', DEEP = '#14304F', GOLD = '#A8842C', GOLDL = '#E0BE8E', INK = '#1D2733', WARM = '#EDE7DC';
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/icb-pack/';
  var CB = '?cb=' + new Date().toISOString().slice(0, 10);
  var NV = 'Not verified';
  var DEFAULT_ICB = 'QHL', DEFAULT_BRAND = 'qv';

  var CSS = '.icbp{font:15px/1.5 Georgia,serif;color:' + INK + '}.icbp *{box-sizing:border-box}'
    + '.icbp .band{padding:26px 0}.icbp .dark{background:' + NAVY + ';color:#F5F1E8}.icbp .warm{background:' + WARM + '}'
    + '.icbp .col{max-width:1080px;margin:0 auto;padding:0 40px}@media(max-width:600px){.icbp .col{padding:0 20px}}'
    + '.icbp h1,.icbp h2{font-family:Didot,"Bodoni 72",Georgia,serif;margin:0 0 10px}.icbp h1{font-size:32px}.icbp h2{font-size:24px;color:' + NAVY + '}'
    + '.icbp h3{font:700 15px Helvetica,Arial,sans-serif;color:' + NAVY + ';margin:16px 0 6px}'
    + '.icbp .dark h1,.icbp .dark h2,.icbp .dark p{color:#F5F1E8}'
    + '.icbp .eyebrow{font:700 12px/1 Helvetica,Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:' + NAVY + ';margin-bottom:8px}'
    + '.icbp .dark .eyebrow{color:' + GOLDL + '}.icbp table{border-collapse:collapse;width:100%;font:13px/1.4 Helvetica,Arial,sans-serif}'
    + '.icbp th,.icbp td{padding:6px 8px;border-bottom:1px solid #d8d2c4;text-align:right}.icbp th:first-child,.icbp td:first-child{text-align:left}'
    + '.icbp th{background:' + DEEP + ';color:#fff}.icbp .sort th{cursor:pointer}'
    + '.icbp .kpis{display:flex;flex-wrap:wrap;gap:14px;margin:12px 0}.icbp .kpi{border-left:4px solid ' + GOLD + ';padding:4px 12px;min-width:150px}'
    + '.icbp .kpi b{display:block;font:700 24px Georgia,serif;color:' + NAVY + '}.icbp .kpi span{font:12px Helvetica,Arial,sans-serif}'
    + '.icbp .nv{color:#7A1F1F;font-weight:700}.icbp .dark .nv{color:' + GOLDL + '}.icbp .edit{border:1px dashed ' + GOLD + ';padding:10px;min-height:70px;background:#fff}'
    + '.icbp .note{font:12px/1.5 Helvetica,Arial,sans-serif;color:#39424d}.icbp .scroll{overflow-x:auto}'
    + '.icbp button{background:' + DEEP + ';color:#fff;border:1px solid ' + GOLDL + ';padding:9px 16px;font:14px Helvetica,Arial,sans-serif;cursor:pointer;margin-right:8px}'
    + '.icbp select{font:14px Helvetica,Arial,sans-serif;padding:8px;color:' + INK + ';background:#fff;border:1px solid ' + GOLD + ';max-width:100%}'
    + '.icbp label{font:700 12px Helvetica,Arial,sans-serif;display:block;margin-bottom:4px}.icbp .pick{display:flex;gap:18px;flex-wrap:wrap;margin:12px 0}'
    + '.icbp .hm td{text-align:center;font-size:11px;padding:4px 3px;min-width:34px}.icbp .hm td:first-child{min-width:230px;text-align:left}'
    + '@media print{.icbp button,.icbp .pick{display:none}.icbp .dark{-webkit-print-color-adjust:exact;print-color-adjust:exact}}';

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function sum(a, from) { var t = 0; for (var i = from || 0; i < a.length; i++) t += a[i] || 0; return t; }
  function last12(a) { return a.slice(-12); }
  function num(x, d) { return x == null ? '<span class="nv">' + NV + '</span>' : Number(x).toLocaleString('en-GB', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); }
  function pc(x, d) { return x == null ? '<span class="nv">' + NV + '</span>' : Number(x).toFixed(d == null ? 1 : d) + '%'; }
  function money(x) { return '£' + Math.round(x).toLocaleString('en-GB'); }
  function ratio(a, b) { return b ? 100 * a / b : null; }
  function mlabel(p) { var m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']; return m[+p.slice(4) - 1] + ' ' + p.slice(0, 4); }
  function trend(series, floor) { var b = series[0], n = series[series.length - 1]; return b < floor ? null : 100 * (n - b) / b; }
  function trendTxt(t) { return t == null ? 'too few to trend' : (t >= 0 ? '+' : '') + t.toFixed(1) + '%'; }

  function ramp(v, lo, hi) {
    if (v == null || hi === lo) return ['#EDE7DC', INK];
    var t = Math.max(0, Math.min(1, (v - lo) / (hi - lo))), a = [237, 231, 220], b = [20, 48, 79];
    var c = a.map(function (x, i) { return Math.round(x + (b[i] - x) * t); });
    return ['rgb(' + c.join(',') + ')', t > 0.45 ? '#FFFFFF' : INK];
  }

  function line(series, labels, colour) {
    var mx = Math.max.apply(null, series), w = 640, h = 170;
    if (!series.length || !mx) return '<p class="note">No items.</p>';
    var pts = series.map(function (v, i) { return [40 + i * (w - 60) / Math.max(1, series.length - 1), h - 28 - v / mx * (h - 50), v]; });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
    var dots = pts.map(function (p) { return '<circle cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="3" fill="' + colour + '"/>'; }).join('');
    var ticks = pts.map(function (p, i) { return (i % 3 === 0 || i === pts.length - 1) ? '<text x="' + p[0].toFixed(1) + '" y="' + (h - 8) + '" font-size="10" text-anchor="middle" fill="' + INK + '">' + esc(labels[i]) + '</text>' : ''; }).join('');
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="monthly series" style="width:100%;max-width:' + w + 'px"><text x="4" y="14" font-size="10" fill="' + INK + '">max ' + Math.round(mx).toLocaleString('en-GB') + '</text><path d="' + d + '" fill="none" stroke="' + colour + '" stroke-width="2"/>' + dots + ticks + '</svg>';
  }

  function cvOf(vals) {
    if (vals.length < 3) return null;
    var m = vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
    if (!m) return null;
    return Math.sqrt(vals.reduce(function (a, b) { return a + (b - m) * (b - m); }, 0) / vals.length) / m;
  }

  var IDX = null, SHARD = {};
  MOUNT.innerHTML = '<style>' + CSS + '</style><div class="icbp"><div class="band"><div class="col">Loading the Integrated Care Board pack…</div></div></div>';

  function get(path) {
    return fetch(BASE + path + CB).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  }
  function fail(e) {
    MOUNT.innerHTML = '<style>' + CSS + '</style><div class="icbp"><div class="band"><div class="col"><p>The pack could not be loaded just now (' + esc(e.message) + '). This is a loading problem, not missing data. Refresh to try again.</p></div></div></div>';
  }

  get('index.json').then(function (d) {
    IDX = d;
    var q = new URLSearchParams(location.search);
    var icb = q.get('icb') || DEFAULT_ICB, brand = q.get('brand') || DEFAULT_BRAND;
    if (!IDX.icbs[icb]) icb = DEFAULT_ICB;
    if (!IDX.rank[brand]) brand = IDX.brands[0].key;
    show(icb, brand);
  }).catch(fail);

  function show(icb, brand) {
    var p = SHARD[icb] ? Promise.resolve(SHARD[icb]) : get('icb-' + icb + '.json').then(function (s) { SHARD[icb] = s; return s; });
    p.then(function (s) { render(icb, brand, s); }).catch(fail);
  }

  function brandLabel(k) { for (var i = 0; i < IDX.brands.length; i++) if (IDX.brands[i].key === k) return IDX.brands[i].label; return k; }

  function render(icb, brand, S) {
    var D = IDX, per = D.periods, labels = per.map(mlabel), floor = D.minBaselineItems;
    var M = D.icbs[icb], BL = brandLabel(brand), nm = M.pretty;
    var nb = D.national.items[brand], nm_ = D.national.items._market, nbc = D.national.cost[brand];
    var rk = D.rank[brand][icb], bi = S.brands[brand].items, bcost = S.brands[brand].cost;

    // pickers
    var icbOpts = Object.keys(D.icbs).sort(function (a, b) { return D.icbs[a].pretty.localeCompare(D.icbs[b].pretty); })
      .map(function (c) { return '<option value="' + c + '"' + (c === icb ? ' selected' : '') + '>' + esc(D.icbs[c].pretty) + '</option>'; }).join('');
    var brandOpts = D.brands.map(function (b) { return '<option value="' + b.key + '"' + (b.key === brand ? ' selected' : '') + '>' + esc(b.label) + '</option>'; }).join('');

    // 1 national
    var natRtt = D.national.rtt;
    var nat = '<div class="kpis"><div class="kpi"><b>' + num(sum(last12(nb))) + '</b><span>' + esc(BL) + ' items, 12 months to ' + labels[labels.length - 1] + '</span></div>'
      + '<div class="kpi"><b>' + pc(ratio(sum(last12(nb)), sum(last12(nm_)))) + '</b><span>' + esc(BL) + ' share of emollient items (our market definition)</span></div>'
      + '<div class="kpi"><b>' + trendTxt(trend(nb, floor)) + '</b><span>' + esc(BL) + ' items ' + labels[labels.length - 1] + ' against ' + labels[0] + '</span></div>'
      + '<div class="kpi"><b>' + money(sum(last12(nbc))) + '</b><span>' + esc(BL) + ' actual cost, 12 months</span></div></div>'
      + '<p>' + (natRtt ? 'Dermatology, England, ' + esc(D.rttPeriod) + ': ' + num(natRtt.total) + ' incomplete pathways, median wait ' + num(natRtt.median, 1) + ' weeks, ' + num(natRtt.w52) + ' waiting 52 weeks or more.' : NV) + '</p>';

    // 2 ICB view
    var m12 = sum(last12(S.market.items));
    var prod = S.topProducts.slice(0, 12).map(function (t) { return '<tr><td>' + esc(t.label) + '</td><td>' + num(t.items12) + '</td><td>' + pc(ratio(t.items12, m12)) + '</td></tr>'; }).join('');
    var icbv = '<div class="kpis"><div class="kpi"><b>' + num(sum(last12(bi))) + '</b><span>' + esc(BL) + ' items, 12 months</span></div>'
      + '<div class="kpi"><b>' + pc(rk.share12) + '</b><span>share of emollient items in ' + esc(nm) + '</span></div>'
      + '<div class="kpi"><b>' + trendTxt(trend(bi, floor)) + '</b><span>' + esc(BL) + ' items ' + labels[labels.length - 1] + ' against ' + labels[0] + '</span></div>'
      + '<div class="kpi"><b>' + money(sum(last12(bcost))) + '</b><span>' + esc(BL) + ' actual cost, 12 months</span></div></div>'
      + line(bi, labels, DEEP)
      + '<p class="note">Monthly ' + esc(BL) + ' items in the ICB. Emollient items in the ICB: ' + num(m12) + ' in the 12 months.</p>'
      + '<h3>Top emollient products in the ICB (12 months, items)</h3><table><tr><th>Product</th><th>Items</th><th>Share of emollient items</th></tr>' + prod + '</table>';

    // 2b hospital use (NHSBSA Secondary Care Medicines Data)
    var H = S.hospital || { brands: {}, trusts: [] }, hb = H.brands[brand], hnat = (D.hospital.national[brand] || []);
    var hosp;
    if (hb) {
      var htr = H.trusts.map(function (t) { return { name: t.name, c: t.cost12[brand] || 0 }; }).filter(function (t) { return t.c > 0; }).sort(function (a, b) { return b.c - a.c; });
      hosp = '<div class="kpis"><div class="kpi"><b>' + money(sum(last12(hb))) + '</b><span>' + esc(BL) + ' issued by trust pharmacies in ' + esc(nm) + ', indicative cost, 12 months</span></div>'
        + '<div class="kpi"><b>' + pc(ratio(sum(last12(hb)), sum(last12(hnat)))) + '</b><span>of England\'s ' + esc(BL) + ' hospital issues (indicative cost)</span></div></div>'
        + line(hb, labels, GOLD)
        + '<h3>By trust (12 months, indicative cost)</h3><table><tr><th>Trust</th><th>' + esc(BL) + ' indicative cost</th></tr>'
        + htr.map(function (t) { return '<tr><td>' + esc(t.name) + '</td><td>' + money(t.c) + '</td></tr>'; }).join('') + '</table>';
    } else if (hnat.length) {
      hosp = '<p>No ' + esc(BL) + ' issues are recorded for the trusts in ' + esc(nm) + ' in these 13 months (England: ' + money(sum(last12(hnat))) + ' indicative cost).</p>';
    } else {
      hosp = '<p><span class="nv">' + NV + '</span>: no brand-named ' + esc(BL) + ' products in the hospital data.</p>';
    }
    hosp += '<p class="note">' + esc(D.hospital.scope) + ' Trusts are assigned to ICBs from the NHS Organisation Data Service (trust map, April 2026 ICBs).</p>';

    // 3 PCNs
    var rows = S.pcns.filter(function (c) { return c.list > 0; }).map(function (c) {
      var series = c.brands[brand], q12 = sum(last12(series)), mm = sum(last12(c.market));
      return { name: c.name, list: c.list, series: series, q12: q12, per1000: q12 / c.list * 1000, share: ratio(q12, mm), m12: mm };
    });
    var top = rows.slice().sort(function (a, b) { return b.q12 - a.q12; }).slice(0, 10).map(function (r) {
      return '<tr><td>' + esc(r.name) + '</td><td>' + num(r.q12) + '</td><td>' + num(r.list) + '</td><td>' + num(r.per1000, 1) + '</td><td>' + pc(r.share) + '</td></tr>';
    }).join('');
    var allv = []; rows.forEach(function (r) { r.series.forEach(function (v) { allv.push(v / r.list * 1000); }); });
    var lo = Math.min.apply(null, allv), hi = Math.max.apply(null, allv);
    var hm = rows.slice().sort(function (a, b) { return b.per1000 - a.per1000; }).map(function (r) {
      return '<tr><td>' + esc(r.name) + '</td>' + r.series.map(function (v) { var x = v / r.list * 1000, c = ramp(x, lo, hi); return '<td style="background:' + c[0] + ';color:' + c[1] + '">' + x.toFixed(1) + '</td>'; }).join('') + '</tr>';
    }).join('');
    var cover = ratio(rows.reduce(function (a, r) { return a + r.m12; }, 0), m12);
    var pcn = '<h3>Highest-prescribing Primary Care Networks (PCNs), 12 months</h3><table><tr><th>PCN</th><th>' + esc(BL) + ' items</th><th>Registered patients</th><th>Items per 1,000 patients</th><th>Share of emollient items</th></tr>' + top + '</table>'
      + '<p class="note">Registered patients: NHS Digital practice totals, October 2026 snapshot, applied to every month. A PCN is the sum of its member practices as NHS Digital maps them today. PCN figures cover registered GP practices: ' + pc(cover) + ' of the ICB emollient items in the 12 months; the rest come from prescriber codes that have no PCN.</p>'
      + '<h3>Variation across the ICB\'s PCNs: ' + esc(BL) + ' items per 1,000 registered patients, by month</h3><div class="scroll"><table class="hm"><tr><th>PCN</th>' + labels.map(function (l) { return '<th>' + esc(l) + '</th>'; }).join('') + '</tr>' + hm + '</table></div>'
      + '<p class="note">Colour runs from the lowest to the highest cell in this ICB (' + lo.toFixed(1) + ' to ' + hi.toFixed(1) + '). Spread across PCNs (coefficient of variation of 12-month items per 1,000): ' + (rk.cv == null ? '<span class="nv">' + NV + '</span>' : rk.cv.toFixed(2)) + ', over ' + rk.nPcn + ' PCNs.</p>';

    // 4 RTT
    var r = M.rtt, rtt;
    if (r) {
      rtt = '<div class="kpis"><div class="kpi"><b>' + num(r.total) + '</b><span>incomplete dermatology pathways</span></div>'
        + '<div class="kpi"><b>' + num(r.median, 1) + '</b><span>median wait, weeks (England ' + (natRtt ? num(natRtt.median, 1) : NV) + ')</span></div>'
        + '<div class="kpi"><b>' + pc(ratio(r.w18, r.total)) + '</b><span>within 18 weeks (England ' + (natRtt ? pc(ratio(natRtt.w18, natRtt.total)) : NV) + ')</span></div>'
        + '<div class="kpi"><b>' + num(r.w52) + '</b><span>waiting 52 weeks or more</span></div></div>'
        + '<p class="note">NHS England Referral to Treatment (RTT), incomplete pathways, commissioner basis, ICB sheet, treatment function C_330 Dermatology Service, ' + esc(D.rttPeriod) + '. Commissioner basis means patients registered with this ICB, wherever they are treated.</p>';
      var rl = D.rttPeriods.map(mlabel), rs = M.rttSeries;
      rtt += rs ? '<h3>Incomplete dermatology pathways, by month</h3>' + line(rs.total, rl, DEEP) + '<h3>Median wait (weeks), by month</h3>' + line(rs.median, rl, GOLD)
        + '<p class="note">England median by month: ' + D.national.rttSeries.median.join(', ') + '. A 13-month series exists only for ICBs whose code is unchanged since April 2025.</p>'
        : '<p><span class="nv">' + NV + '</span>: no 13-month series, this ICB was created by the April 2026 mergers.</p>';
    } else rtt = '<p><span class="nv">' + NV + '</span></p>';

    // 5 IMD
    var imd = M.imd ? '<div class="kpis"><div class="kpi"><b>' + M.imd.rank + ' of ' + Object.keys(D.icbs).length + '</b><span>rank of average score (1 = most deprived ICB)</span></div>'
      + '<div class="kpi"><b>' + num(M.imd.score, 2) + '</b><span>average Index of Multiple Deprivation (IMD) score</span></div>'
      + '<div class="kpi"><b>' + pc(100 * M.imd.prop10) + '</b><span>of neighbourhoods (LSOAs) in the most deprived 10% nationally</span></div></div>'
      + '<p class="note">English Indices of Deprivation 2025: population-weighted mean of neighbourhood scores (mid-2022 population), neighbourhoods assigned to ICBs as at April 2026 (ONS lookup). Same method as the official ICB summaries, which it reproduces on the ICBs unchanged since 2024.</p>'
      : '<p><span class="nv">' + NV + '</span></p>';

    // 6 OTC context
    var otc = '<p><b>National position (verified at source, 22/10/2026).</b> NHS England policy guidance, "Items which should not routinely be prescribed in primary care" (published 3 August 2023, updated 19 August 2025), lists bath and shower preparations for dry and pruritic skin conditions as prescribe only in exceptional circumstances, with the advice to substitute leave-on emollients. It does not list plain leave-on emollients.</p>'
      + (M.otc
        ? '<p><b>This ICB\'s own position (read at source, ' + esc(M.otc.verifiedOn) + ').</b></p><ul>' + M.otc.points.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>'
          + '<p class="note">Sources: ' + M.otc.sources.map(function (s) { return '<a href="' + esc(s.url) + '" style="color:' + DEEP + '">' + esc(s.title) + '</a>'; }).join('; ') + '. ' + esc(M.otc.limits) + '</p>'
        : '<p><b>This ICB\'s own over-the-counter policy: <span class="nv">' + NV + '</span>.</b> Local positions sit in each ICB\'s own formulary or Area Prescribing Committee documents. What would settle it: that page, or a written answer from the ICB medicines optimisation team. Write what you find here.</p>')
      + '<div class="edit" contenteditable="true">ICB policy notes: </div>';

    // 7 ranking, for the chosen brand
    var codes = Object.keys(D.icbs), R = D.rank[brand];
    function rankMap(get, desc) { var a = codes.filter(function (c) { return get(c) != null; }).sort(function (x, y) { return desc ? get(y) - get(x) : get(x) - get(y); }), m = {}; a.forEach(function (c, i) { m[c] = i + 1; }); return m; }
    var rShare = rankMap(function (c) { return R[c].share12; }), rCv = rankMap(function (c) { return R[c].cv; }, true);
    var trs = codes.sort(function (a, b) { return D.icbs[a].pretty.localeCompare(D.icbs[b].pretty); }).map(function (c) {
      var x = R[c], mm = D.icbs[c], rr = mm.rtt;
      function td(v, txt) { return '<td data-v="' + (v == null ? '' : v) + '">' + txt + '</td>'; }
      return '<tr' + (c === icb ? ' style="background:#F3E9D2"' : '') + '><td>' + esc(mm.pretty) + '</td>' + td(x.share12, pc(x.share12)) + td(rShare[c], rShare[c] || '') + td(x.cv, x.cv == null ? NV : x.cv.toFixed(2)) + td(rCv[c], rCv[c] || '')
        + td(mm.imd && mm.imd.rank, mm.imd ? mm.imd.rank : NV) + td(rr && rr.median, rr ? num(rr.median, 1) : NV) + td(rr && rr.w52, rr ? num(rr.w52) : NV) + '</tr>';
    }).join('');
    var rank = '<div class="scroll"><table id="icbp-rank" class="sort"><tr><th>ICB</th><th>' + esc(BL) + ' share of emollient items</th><th>Rank (1 = lowest share)</th><th>PCN spread (CV)</th><th>Rank (1 = most varied)</th><th>IMD rank of ' + codes.length + ' (1 = most deprived)</th><th>Dermatology median wait (weeks)</th><th>Dermatology 52 weeks or more</th></tr>' + trs + '</table></div>'
      + '<p class="note">Click a heading to sort. No composite score: pick the focus by reading the columns, not by a formula we invented. Share and spread are our definitions, printed below.</p>';

    var srcs = D.licences.map(function (l) { return '<li>' + esc(l.source) + ': ' + esc(l.licence) + '</li>'; }).join('');

    MOUNT.innerHTML = '<style>' + CSS + '</style><div class="icbp" id="icbp-page">'
      + '<div class="band dark"><div class="col"><div class="eyebrow">Medical Sales Intelligence Hub · starting figures</div>'
      + '<h1 contenteditable="true">' + esc(BL) + ' — ' + esc(nm) + '</h1>'
      + '<p>Dermatology emollients, from open data only. Every figure is from a named published source; anything that could not be verified is marked <span class="nv">Not verified</span>. Every block is editable in your browser: change it, then save an edited copy.</p>'
      + '<div class="pick"><div><label for="icbp-icb">Integrated Care Board (ICB)</label><select id="icbp-icb">' + icbOpts + '</select></div>'
      + '<div><label for="icbp-brand">Brand</label><select id="icbp-brand">' + brandOpts + '</select></div></div>'
      + '<p><button id="icbp-save">Save edited copy</button><button id="icbp-print">Print or save as PDF</button></p></div></div>'
      + sec('', '1 · National overview', 'England', nat + '<p class="note">Market definition: ' + esc(D.market) + '. Brand: the first word of the NHSBSA presentation name. Items are the NHSBSA English Prescribing Dataset, primary care, 12 months to ' + labels[labels.length - 1] + '.</p>')
      + sec('warm', '2 · ICB view', 'Brand share and trend', icbv)
      + sec('', '2b · Hospital use', 'Secondary care: medicines issued by trust pharmacies', hosp)
      + sec('warm', '3 · Primary Care Networks', 'Where it is prescribed, and how much it varies', pcn)
      + sec('', '4 · Dermatology waiting times', 'Referral to Treatment (RTT)', rtt)
      + sec('warm', '5 · Deprivation', 'Index of Multiple Deprivation (IMD)', imd)
      + sec('', '6 · Context', 'Moves towards over-the-counter', otc)
      + sec('warm', '7 · Choosing a focus', 'All ICBs side by side', rank)
      + sec('', '8 · Your notes', 'Value proposition starting points', '<div class="edit" contenteditable="true">Type here: what the figures say for this ICB, the access barrier, the ask.</div>')
      + '<div class="band"><div class="col"><div class="eyebrow">Definitions, sources and licences</div>'
      + '<p class="note">Trend: latest month against the same month a year earlier, shown only where that baseline is at least ' + floor + ' items. Share: brand items divided by emollient items over the latest 12 months. PCN spread: coefficient of variation of 12-month brand items per 1,000 registered patients across the ICB\'s PCNs. Built ' + esc(D.generatedOn) + '.</p><ul class="note">' + srcs + '</ul></div></div></div>';

    function go() { var i = document.getElementById('icbp-icb').value, b = document.getElementById('icbp-brand').value; if (history.replaceState) history.replaceState(null, '', '?icb=' + i + '&brand=' + b); show(i, b); }
    document.getElementById('icbp-icb').onchange = go;
    document.getElementById('icbp-brand').onchange = go;
    document.getElementById('icbp-print').onclick = function () { window.print(); };
    document.getElementById('icbp-save').onclick = function () {
      var page = document.getElementById('icbp-page').cloneNode(true);
      [].forEach.call(page.querySelectorAll('.pick,button'), function (n) { n.parentNode.removeChild(n); });
      var h = '<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ICB pack ' + esc(BL) + ' ' + esc(nm) + '</title><style>body{margin:0}' + CSS + '</style></head><body>' + page.outerHTML + '</body></html>';
      var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([h], { type: 'text/html' }));
      a.download = 'icb-pack-' + icb + '-' + brand + '.html'; document.body.appendChild(a); a.click(); document.body.removeChild(a);
    };
    var t = document.getElementById('icbp-rank');
    [].forEach.call(t.rows[0].cells, function (th, i) {
      th.onclick = function () {
        var asc = th.getAttribute('data-asc') !== '1'; th.setAttribute('data-asc', asc ? '1' : '0');
        var body = [].slice.call(t.rows, 1);
        body.sort(function (a, b) {
          var x = a.cells[i].getAttribute('data-v') || a.cells[i].textContent, y = b.cells[i].getAttribute('data-v') || b.cells[i].textContent, nx = parseFloat(x), ny = parseFloat(y);
          var c = (isNaN(nx) || isNaN(ny)) ? String(x).localeCompare(String(y)) : nx - ny; return asc ? c : -c;
        });
        body.forEach(function (row) { t.tBodies[0].appendChild(row); });
      };
    });
  }

  function sec(cls, eyebrow, h2, body) {
    return '<div class="band ' + cls + '"><div class="col"><div class="eyebrow">' + eyebrow + '</div><h2>' + h2 + '</h2>' + body + '</div></div>';
  }
})();
