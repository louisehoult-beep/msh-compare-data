/* Medical Sales Hub — speciality panels.
   Renders two tabs on a speciality page from that speciality's own slice:
     #msh-spec-frameworks  → Frameworks, awards and tenders
     #msh-spec-suppliers   → Suppliers
   Both mounts carry data-speciality="<slug>".

   Replaces the old "Suppliers, frameworks & related" tab, which was three links
   out and told a rep nothing about their own patch (Lou, 07/09/2026).

   Data: data/speciality-panels/<slug>.json, built by
   scripts/build_speciality_panels.py in this repo. Edit the code HERE, never in
   the WordPress page — the page carries a loader only. */
(function () {
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/speciality-panels/';
  var FW = document.getElementById('msh-spec-frameworks');
  var SUP = document.getElementById('msh-spec-suppliers');
  /* #msh-spec-market (30/09/2026): the computed "who holds the market" block, placed in
     the page's Market intelligence section. Optional; the page loader only needs one
     of the other two mounts to fetch this file. */
  var MKT = document.getElementById('msh-spec-market');
  if (!FW && !SUP && !MKT) { return; }
  var slug = (FW || SUP || MKT).getAttribute('data-speciality');
  if (!slug) { return; }

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function css() {
    if (document.getElementById('msh-sp-css')) { return; }
    var st = document.createElement('style');
    st.id = 'msh-sp-css';
    st.textContent = [
      '.msh .sp-tbl{width:100%;border-collapse:collapse;font-size:13px;}',
      '.msh .sp-tbl th{text-align:left;font-size:10px;letter-spacing:1.1px;text-transform:uppercase;color:var(--dim);font-weight:700;padding:0 10px 7px 0;border-bottom:1px solid var(--border);}',
      '.msh .sp-tbl td{padding:9px 10px 9px 0;border-bottom:1px solid var(--border);vertical-align:top;line-height:1.45;}',
      '.msh .sp-tbl tr:last-child td{border-bottom:0;}',
      '.msh .sp-tbl a{color:var(--gold);font-weight:600;text-decoration:none;}',
      '.msh .sp-tbl a:hover{text-decoration:underline;}',
      '.msh .sp-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;}',
      '.msh .sp-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px;}',
      '.msh .sp-tile{border:1px solid var(--border);border-radius:9px;padding:12px 14px;background:var(--panel);}',
      '.msh .sp-tile b{display:block;font-size:23px;font-weight:800;color:var(--navy);line-height:1.15;}',
      '.msh .sp-tile span{display:block;font-size:10px;letter-spacing:1px;text-transform:uppercase;color:var(--dim);font-weight:700;margin-top:4px;}',
      '.msh .sp-soon{color:#7A4A44;font-weight:700;}',
      '.msh .sp-chip{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.3px;padding:2px 8px;border-radius:99px;border:1px solid var(--border);background:var(--panel2);color:var(--dim);margin:2px 4px 2px 0;}',
      '.msh .sp-meta{font-size:11.5px;color:var(--dim);line-height:1.6;margin-top:12px;}',
      '.msh .sp-rule{margin-top:14px;}',
      '.msh .sp-rule summary{cursor:pointer;font-size:11px;letter-spacing:.8px;text-transform:uppercase;font-weight:700;color:var(--dim);}',
      '.msh .sp-rule p{font-size:12px;color:var(--dim);line-height:1.6;margin:8px 0 0;}',
      '.msh .sp-find{width:100%;max-width:340px;padding:9px 12px;border:1px solid var(--border);border-radius:8px;font-size:13.5px;background:var(--panel);color:var(--ink);margin-bottom:14px;}',
      '.msh .sp-sec{margin-top:26px;}',
      '.msh .sp-sec:first-child{margin-top:0;}',
      '.msh .sp-alt{font-size:11px;color:var(--dim);font-weight:400;margin-top:3px;line-height:1.45;}',
      '.msh .sp-li-g{font-size:11px;letter-spacing:1px;text-transform:uppercase;font-weight:700;color:var(--dim);margin:16px 0 8px;}',
      '.msh .sp-li{overflow-wrap:anywhere;min-width:0;border:1px solid var(--border);border-left:3px solid var(--gold);border-radius:8px;background:var(--panel);padding:11px 14px;margin-bottom:9px;}',
      '.msh .sp-li-h{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:baseline;justify-content:space-between;}',
      '.msh .sp-li-t{font-size:14px;font-weight:700;line-height:1.35;}',
      '.msh .sp-li-t a{color:var(--gold);text-decoration:none;}',
      '.msh .sp-li-t a:hover{text-decoration:underline;}',
      '.msh .sp-li-d{font-size:11.5px;color:var(--dim);}',
      '.msh .sp-li-o{font-size:12px;color:var(--dim);margin-top:2px;}',
      '.msh .sp-li p{font-size:13px;line-height:1.55;margin:7px 0 0;}',
      '.msh .sp-li q{display:block;font-style:italic;font-size:12.5px;margin-top:6px;padding-left:10px;border-left:2px solid var(--border);color:var(--ink);}',
      '.msh .sp-li-u{font-size:12.5px;margin-top:6px;}',
      '.msh .sp-li-u b{color:var(--navy);}',
      '.msh .sp-li-m{font-size:11px;color:var(--dim);margin-top:7px;}',
      '.msh .sp-prov{display:inline-block;font-size:9.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;padding:2px 7px;border-radius:99px;margin:0 6px 0 0;vertical-align:1px;}',
      '.msh .sp-prov-fw{background:var(--navy);color:#fff;}',
      '.msh .sp-prov-dir{background:var(--panel2);color:var(--dim);border:1px solid var(--border);}',
      '.msh .sp-note{font-size:11.5px;color:var(--dim);margin-top:4px;line-height:1.5;}',
      '.msh .sp-note a{font-weight:600;}',
      '.msh .sp-num{text-align:right;white-space:nowrap;}',
      '.msh .sp-more{margin-top:10px;}',
      '.msh .sp-more summary{cursor:pointer;font-size:12px;font-weight:700;color:var(--gold);}',
      '.msh .sp-mkt{margin-top:18px;}',
      '.msh .sp-mkt h4{font-size:14px;margin:0 0 8px;color:var(--navy);}',
      '.msh .sp-dsu{border-bottom:1px solid var(--border);padding:9px 0;}',
      '.msh .sp-dsu:last-child{border-bottom:0;}',
      '.msh .sp-dsu a{color:var(--gold);font-weight:700;text-decoration:none;}',
      '.msh .sp-dsu p{font-size:12.5px;line-height:1.5;margin:4px 0 0;color:var(--ink);}',
      '.msh .ms-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin:14px 0 6px;}',
      '.msh .ms-card{border:1px solid var(--border);border-radius:10px;background:var(--panel);padding:16px 18px;min-width:0;}',
      '.msh .ms-card h4{font-size:12px;letter-spacing:1px;text-transform:uppercase;color:var(--navy);margin:0 0 4px;font-weight:800;}',
      '.msh .ms-sub{font-size:12px;color:var(--dim);line-height:1.5;margin:0 0 10px;}',
      '.msh .ms-big{font-size:26px;font-weight:800;color:var(--navy);line-height:1.1;}',
      '.msh .ms-big small{display:block;font-size:11px;font-weight:600;color:var(--dim);letter-spacing:.3px;margin-top:3px;}',
      '.msh .ms-bar{display:grid;grid-template-columns:minmax(0,1fr) 54px;gap:2px 10px;align-items:center;margin:7px 0;font-size:13px;color:var(--ink);}',
      '.msh .ms-bar span{overflow-wrap:anywhere;}',
      '.msh .ms-bar b{text-align:right;font-weight:800;color:var(--navy);}',
      '.msh .ms-bar i{grid-column:1 / span 2;display:block;height:6px;border-radius:3px;background:var(--panel2);overflow:hidden;}',
      '.msh .ms-bar i em{display:block;height:100%;background:var(--gold);border-radius:3px;}',
      '.msh .ms-bar.ms-hi i em{background:var(--navy);}',
      '.msh .ms-pick{margin-top:18px;border:1px solid var(--border);border-radius:10px;background:var(--panel);padding:16px 18px;}',
      '.msh .ms-pick select{padding:8px 10px;border:1px solid var(--border);border-radius:8px;font-size:14px;background:var(--panel);color:var(--ink);max-width:100%;margin:6px 0 12px;}',
      '.msh .ms-find{border-left:3px solid var(--gold);background:var(--panel2);padding:12px 16px;border-radius:0 8px 8px 0;margin:14px 0 0;font-size:13.5px;line-height:1.55;color:var(--ink);}'
    ].join('');
    document.head.appendChild(st);
  }

  /* Months until a framework ends. NHSSC states these as "31 August 2027". */
  function monthsTo(txt) {
    if (!txt) { return null; }
    var d = new Date(txt);
    if (isNaN(d.getTime())) { return null; }
    return Math.round((d - new Date()) / 2629800000);
  }

  function n(x) {
    return (x === null || x === undefined) ? 'not stated' : Number(x).toLocaleString('en-GB');
  }

  function pct(x) {
    return (x === null || x === undefined) ? 'too few to trend' : (x > 0 ? '+' : '') + x.toFixed(1) + '%';
  }

  /* A framework name, linked to NHS Supply Chain's own brief where the panel carries it. */
  function fwLink(name, url) {
    return url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(name) + '</a>' : esc(name);
  }

  function fail(mount, why) {
    if (!mount) { return; }
    mount.innerHTML = '<div class="empty-state">' + esc(why) + '</div>';
  }

  function ruleBlock(rules, keys) {
    var out = '<details class="sp-rule"><summary>How this list was filtered</summary>';
    for (var i = 0; i < keys.length; i++) {
      if (rules[keys[i]]) {
        out += '<p><b>' + esc(keys[i]) + ':</b> ' + esc(rules[keys[i]]) + '</p>';
      }
    }
    return out + '</details>';
  }

  function renderFrameworks(d) {
    if (!FW) { return; }
    var h = '';
    var soon = 0, i, m;
    for (i = 0; i < d.frameworks.length; i++) {
      m = monthsTo(d.frameworks[i].ends);
      if (m !== null && m <= 12) { soon++; }
    }

    h += '<div class="sp-tiles">';
    h += '<div class="sp-tile"><b>' + d.counts.frameworks + '</b><span>Frameworks on this patch</span></div>';
    h += '<div class="sp-tile"><b>' + d.counts.suppliers + '</b><span>Framework-named suppliers</span></div>';
    h += '<div class="sp-tile"><b>' + soon + '</b><span>Expiring within a year</span></div>';
    h += '<div class="sp-tile"><b>' + d.counts.awardsMatched + '</b><span>Awards recorded</span></div>';
    h += '</div>';

    /* FRAMEWORKS. A speciality with none gets an honest empty state, not a table
       with only a header row: obesity and weight management genuinely has no NHS
       Supply Chain framework, and a bare header reads as a panel that failed. */
    h += '<div class="sp-sec"><h3 class="sub-h3">Frameworks</h3>';
    if (!d.frameworks.length) {
      h += '<div class="empty-state">No NHS Supply Chain framework covers this speciality. Every framework name was checked, so this is a fact about how the patch is bought rather than a gap in the data. See the rule below for what that means, and what this panel shows instead.</div>';
    } else {
    h += '<div class="sp-scroll"><table class="sp-tbl">';
    h += '<tr><th>Framework</th><th>Route</th><th>Ends</th><th>Suppliers</th></tr>';
    for (i = 0; i < d.frameworks.length; i++) {
      var f = d.frameworks[i];
      m = monthsTo(f.ends);
      h += '<tr><td>' + (f.url ? '<a href="' + esc(f.url) + '" target="_blank" rel="noopener">' + esc(f.name) + '</a>' : esc(f.name)) + '</td>';
      h += '<td>' + esc(f.supplyRoute || f.category || '') + '</td>';
      h += '<td>' + esc(f.ends || 'not stated');
      if (m !== null && m <= 12) { h += ' <span class="sp-soon">(' + (m <= 0 ? 'expired' : m + ' months)') + '</span>'; }
      h += '</td><td>' + esc(f.supplierCount === null || f.supplierCount === undefined ? 'not stated' : f.supplierCount) + '</td></tr>';
    }
    h += '</table></div>';
    }
    h += '</div>';

    /* OPEN TENDERS */
    h += '<div class="sp-sec"><h3 class="sub-h3">Open now</h3>';
    if (!d.openTenders.length) {
      h += '<div class="empty-state">No notice on this patch is open for bidding today. This is checked against the live feed, not left blank. When one opens it appears here.</div>';
    } else {
      h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Notice</th><th>Buyer</th><th>Closes</th></tr>';
      for (i = 0; i < d.openTenders.length; i++) {
        var o = d.openTenders[i];
        h += '<tr><td>' + (o.url ? '<a href="' + esc(o.url) + '" target="_blank" rel="noopener">' + esc(o.title) + '</a>' : esc(o.title)) + '</td>';
        h += '<td>' + esc(o.buyer) + '</td><td>' + esc(o.closingDate || 'not stated') + '</td></tr>';
      }
      h += '</table></div>';
    }
    h += '</div>';

    /* LOCAL CONTRACTS, FORMULARIES AND POLICY — hand-curated from primary sources in
       data/speciality-local-intel.json. Every item names its source and the date it
       was read; an item whose link check found the source gone is withheld by the
       builder, not here. Absent entirely on specialities nobody has curated yet. */
    if (d.localIntel && d.localIntel.length) {
      var groups = d.localIntelGroups || {};
      var order = ['routes', 'local', 'formulary', 'nations', 'policy', 'data'];
      h += '<div class="sp-sec"><h3 class="sub-h3">Local contracts, formularies and policy</h3>';
      h += '<p style="font-size:13px;line-height:1.6;margin:0 0 4px;">Contracts, formularies, board papers and national routes on this patch, each read at its own source. Who holds a contract and when it ends is the call-planning fact; the quote is the source\'s own words.</p>';
      for (var g = 0; g < order.length; g++) {
        var rows = [];
        for (i = 0; i < d.localIntel.length; i++) {
          if (d.localIntel[i].group === order[g]) { rows.push(d.localIntel[i]); }
        }
        if (!rows.length) { continue; }
        h += '<div class="sp-li-g">' + esc(groups[order[g]] || order[g]) + '</div>';
        for (i = 0; i < rows.length; i++) {
          var x = rows[i];
          h += '<div class="sp-li"><div class="sp-li-h"><div class="sp-li-t">' +
               (x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.title) + '</a>' : esc(x.title)) +
               '</div><div class="sp-li-d">' + esc(x.date || '') + (x.ends ? ' &middot; ' + (/^\d/.test(x.ends) ? 'ends ' : '') + esc(x.ends) : '') + '</div></div>';
          h += '<div class="sp-li-o">' + esc(x.org) + ' &middot; ' + esc(x.kind) + ' &middot; ' + esc(x.nation) + '</div>';
          h += '<p>' + esc(x.fact) + '</p>';
          if (x.quote) { h += '<q>' + esc(x.quote) + '</q>'; }
          if (x.use) { h += '<div class="sp-li-u"><b>For a rep:</b> ' + esc(x.use) + '</div>'; }
          h += '<div class="sp-li-m">Read at source ' + esc(x.verifiedOn) +
               (x.lastCheck && x.lastCheck.status === 'ok' ? ' &middot; link checked ' + esc(x.lastCheck.date) : '') + '</div>';
          h += '</div>';
        }
      }
      h += '</div>';
    }

    /* AWARDS */
    h += '<div class="sp-sec"><h3 class="sub-h3">Awarded contracts</h3>';
    if (!d.awards.length) {
      h += '<div class="empty-state">No award on this patch has been recorded in the feeds yet.</div>';
    } else {
      h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Date</th><th>Contract</th><th>Buyer</th><th>Awarded to</th></tr>';
      for (i = 0; i < d.awards.length; i++) {
        var a = d.awards[i];
        h += '<tr><td style="white-space:nowrap;">' + esc(a.date || '') + '</td>';
        h += '<td>' + (a.url ? '<a href="' + esc(a.url) + '" target="_blank" rel="noopener">' + esc(a.title) + '</a>' : esc(a.title)) + '</td>';
        h += '<td>' + esc(a.buyer || 'not stated') + '</td><td>' + esc(a.supplier || 'not named') + '</td></tr>';
      }
      h += '</table></div>';
      if (d.counts.awardsMatched > d.awards.length) {
        h += '<div class="sp-meta">Showing the ' + d.awards.length + ' most recent of ' + d.counts.awardsMatched + ' matched.</div>';
      }
    }
    h += '</div>';

    /* DRUG TARIFF */
    if (d.drugTariff) {
      var t = d.drugTariff;
      h += '<div class="sp-sec"><h3 class="sub-h3">Drug Tariff Part ' + esc(t.parts.join(' and ')) + '</h3>';
      h += '<div class="sp-tiles">';
      h += '<div class="sp-tile"><b>' + t.lineCount.toLocaleString() + '</b><span>Reimbursed lines</span></div>';
      h += '<div class="sp-tile"><b>' + t.supplierCount + '</b><span>Suppliers listed</span></div>';
      h += '<div class="sp-tile"><b>' + esc(t.effectiveMonth) + '</b><span>Effective month</span></div>';
      h += '</div><p style="font-size:13px;line-height:1.6;margin:0 0 10px;">The suppliers with the most reimbursed lines on this patch. A line is one product size or pack, so a long list is range breadth, not sales.</p>';
      h += '<div>';
      for (i = 0; i < t.topSuppliers.length; i++) {
        h += '<span class="sp-chip">' + esc(t.topSuppliers[i].name) + ' &middot; ' + t.topSuppliers[i].lines.toLocaleString() + '</span>';
      }
      h += '</div>';
      h += '<div class="sp-meta">Prices are the NHSBSA reimbursement price at publication (' + esc(t.effectiveMonth) + '), from &pound;' + t.priceMin + ' to &pound;' + t.priceMax + '. Not necessarily today\'s.</div>';
      h += '</div>';
    }

    /* DRUG TARIFF PART VIIIA — generic medicine basic prices, sliced by NHSBSA's own
       BNF classification of each line. */
    if (d.drugTariffViiia) {
      var v = d.drugTariffViiia, cc = v.categoryCounts || {};
      h += '<div class="sp-sec"><h3 class="sub-h3">Drug Tariff Part VIIIA: generic medicines</h3>';
      h += '<div class="sp-tiles">';
      h += '<div class="sp-tile"><b>' + n(v.lineCount) + '</b><span>Medicine lines</span></div>';
      h += '<div class="sp-tile"><b>' + n(cc.M || 0) + '</b><span>Category M</span></div>';
      h += '<div class="sp-tile"><b>' + n(cc.C || 0) + '</b><span>Category C</span></div>';
      h += '<div class="sp-tile"><b>' + esc(v.effectiveMonth) + '</b><span>Effective month</span></div>';
      h += '</div>';
      h += '<details class="sp-more"><summary>Show ' + v.linesShown + (v.lineCount > v.linesShown ? ' of ' + n(v.lineCount) : '') + ' lines, Category M first</summary>';
      h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Medicine</th><th>Pack</th><th>Cat.</th><th class="sp-num">Basic price</th></tr>';
      for (i = 0; i < v.lines.length; i++) {
        var ln = v.lines[i];
        h += '<tr><td>' + esc(ln.medicine) + '</td><td>' + esc(ln.pack) + '</td><td>' + esc(ln.category) + '</td><td class="sp-num">&pound;' + ln.price.toFixed(2) + '</td></tr>';
      }
      h += '</table></div></details>';
      h += '<div class="sp-meta">Basic prices at publication for ' + esc(v.effectiveMonth) + ', from &pound;' + v.priceMin.toFixed(2) + ' to &pound;' + v.priceMax.toFixed(2) + '. Not necessarily today\'s. ' +
           (v.bnfFilter ? 'Lines NHSBSA prescribes under BNF ' + esc(v.bnfFilter.join(' or ')) + '.' : 'Every line in the file.') + '</div>';
      h += '</div>';
    }

    /* GP PRESCRIBING — NHSBSA English Prescribing Dataset, primary care, by BNF market. */
    if (d.gpPrescribing) {
      var gp = d.gpPrescribing;
      h += '<div class="sp-sec"><h3 class="sub-h3">GP prescribing in England</h3>';
      if (!gp.defined || !gp.markets.length) {
        h += '<div class="empty-state">' + esc(gp.whyEmpty || 'No GP prescribing market is sized for this speciality.') + '</div>';
      } else {
        for (var mk = 0; mk < gp.markets.length; mk++) {
          var M = gp.markets[mk];
          var per = M.latestPeriod.slice(0, 4) + '-' + M.latestPeriod.slice(4);
          h += '<div class="sp-mkt"><h4>' + esc(M.label) + '</h4>';
          h += '<div class="sp-tiles">';
          h += '<div class="sp-tile"><b>' + n(M.items) + '</b><span>Items, ' + esc(per) + '</span></div>';
          h += '<div class="sp-tile"><b>&pound;' + n(M.cost) + '</b><span>Actual cost, ' + esc(per) + '</span></div>';
          h += '<div class="sp-tile"><b>' + n(M.items12m) + '</b><span>Items, 12 months</span></div>';
          h += '<div class="sp-tile"><b>' + pct(M.itemsYoY) + '</b><span>Items vs a year earlier</span></div>';
          h += '</div>';
          if (M.note) { h += '<p style="font-size:12.5px;line-height:1.55;margin:0 0 10px;color:var(--dim);">' + esc(M.note) + '</p>'; }
          h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Product</th><th class="sp-num">Items</th><th class="sp-num">Share</th><th class="sp-num">Cost</th><th class="sp-num">vs a year earlier</th></tr>';
          for (i = 0; i < M.topNational.length; i++) {
            var tp = M.topNational[i];
            h += '<tr><td>' + esc(tp.label) + (tp.generic ? ' <span class="sp-chip">generic</span>' : '') + '</td><td class="sp-num">' + n(tp.items) + '</td><td class="sp-num">' + (tp.share === null ? '' : tp.share.toFixed(1) + '%') + '</td><td class="sp-num">&pound;' + n(tp.cost) + '</td><td class="sp-num">' + pct(tp.yoy) + '</td></tr>';
          }
          h += '</table></div>';
          h += '<details class="sp-more"><summary>Leading products in each of ' + M.icbLeaders.length + ' ICBs</summary><div class="sp-scroll"><table class="sp-tbl"><tr><th>ICB</th><th class="sp-num">Items</th><th>Leaders (share of the ICB\'s items)</th></tr>';
          for (i = 0; i < M.icbLeaders.length; i++) {
            var ib = M.icbLeaders[i], parts = [];
            for (var q = 0; q < ib.leaders.length; q++) {
              parts.push(esc(ib.leaders[q].label) + ' ' + (ib.leaders[q].share === null ? '' : ib.leaders[q].share.toFixed(1) + '%'));
            }
            h += '<tr><td>' + esc(ib.name) + '</td><td class="sp-num">' + n(ib.items) + '</td><td>' + parts.join(' &middot; ') + '</td></tr>';
          }
          h += '</table></div></details></div>';
        }
        h += '<div class="sp-meta">' + esc(gp.source) + ', ' + esc(gp.periods[0]) + ' to ' + esc(gp.periods[1]) + '. Share is product share of items, not company share. ' + esc(gp.attribution || '') + '</div>';
      }
      h += '</div>';
    }

    /* MHRA DRUG SAFETY UPDATES — tagged by GOV.UK's own therapeutic-area facet. */
    if (d.mhraDsu) {
      var ds = d.mhraDsu;
      h += '<div class="sp-sec"><h3 class="sub-h3">MHRA Drug Safety Updates</h3>';
      if (!ds.updates.length) {
        h += '<div class="empty-state">' + esc(ds.whyEmpty || 'No Drug Safety Update is tagged to this speciality.') + '</div>';
      } else {
        for (i = 0; i < ds.updates.length; i++) {
          var u = ds.updates[i];
          h += '<div class="sp-dsu"><a href="' + esc(u.url) + '" target="_blank" rel="noopener">' + esc(u.title) + '</a>' +
               '<div class="sp-li-d">Published ' + esc(u.published) + (u.updated && u.updated !== u.published ? ' &middot; updated ' + esc(u.updated) : '') + '</div>' +
               (u.summary ? '<p>' + esc(u.summary) + '</p>' : '') + '</div>';
        }
        h += '<div class="sp-meta">The ' + ds.updates.length + ' most recent of ' + n(ds.count) + ' Drug Safety Updates GOV.UK tags to this area, as at ' + esc(ds.dataAsOf) + '. <a href="' + esc(ds.sourcePage) + '" target="_blank" rel="noopener">All Drug Safety Updates</a>.</div>';
      }
      h += '</div>';
    }

    h += '<div class="sp-meta">Frameworks as at ' + esc(d.dataAsOf.frameworks || 'not stated') +
         ' &middot; awards as at ' + esc(d.dataAsOf.tenderHistory || 'not stated') +
         ' &middot; Drug Tariff as at ' + esc(d.dataAsOf.drugTariff || 'not stated') +
         (d.dataAsOf.gpPrescribing ? ' &middot; GP prescribing built ' + esc(d.dataAsOf.gpPrescribing) : '') +
         (d.dataAsOf.mhraDsu ? ' &middot; MHRA as at ' + esc(d.dataAsOf.mhraDsu) : '') + '.</div>';
    h += ruleBlock(d.rules, ['frameworks', 'awards', 'openTenders', 'drugTariff', 'drugTariffViiia', 'gpPrescribing', 'mhraDsu', 'localIntel']);
    FW.innerHTML = h;
  }

  function renderSuppliers(d) {
    if (!SUP) { return; }
    var h = '';
    /* No framework means no supplier list can honestly be drawn. Say so, rather than
       showing a search box over an empty table, and never fall back to a keyword
       guess against the whole directory. */
    var dir = d.directorySuppliers || [];
    var i, j, s, find;
    /* No framework means no framework-named list can honestly be drawn. Say so, and
       never fall back to a keyword guess against the whole directory. Companies the
       Hub's supplier directory files under this speciality follow, labelled as such. */
    if (!d.suppliers.length) {
      h += '<div class="empty-state">No supplier list is published for this speciality. This panel names framework suppliers only where NHS Supply Chain names them on the speciality\'s own frameworks, and this patch has none for a list to be drawn from.' +
           (dir.length ? ' The companies the Hub\'s supplier directory files under this speciality are listed below, labelled directory-tagged, with any other framework they are on named against them.' : ' The awarded contracts on the previous tab do name who won them.') + '</div>';
      if (!dir.length) {
        h += ruleBlock(d.rules, ['suppliers', 'directorySuppliers']);
        SUP.innerHTML = h;
        return;
      }
    } else {
      h += '<p style="font-size:13.5px;line-height:1.65;margin:0 0 14px;">Every supplier NHS Supply Chain names on this speciality\'s own frameworks, ' +
           d.counts.suppliers + ' of them, resolved to one name per company' +
           (dir.length ? ', then ' + dir.length + ' more the Hub\'s supplier directory files under this speciality' : '') +
           '. Each row says which it is.</p>';
    }
    h += '<input class="sp-find" id="sp-find" type="search" placeholder="Find a supplier..." autocomplete="off">';
    h += '<div class="sp-scroll"><table class="sp-tbl" id="sp-suptbl">';
    h += '<tr><th>Supplier</th><th>Frameworks</th></tr>';
    for (i = 0; i < d.suppliers.length; i++) {
      s = d.suppliers[i];
      find = s.name + ' ' + (s.variants || []).join(' ');
      h += '<tr data-n="' + esc(find.toLowerCase()) + '"><td style="font-weight:600;"><span class="sp-prov sp-prov-fw">Framework-named</span>' + esc(s.name);
      if (s.directoryTagged) { h += ' <span class="sp-prov sp-prov-dir">Also directory-tagged</span>'; }
      if (s.variants && s.variants.length) {
        h += '<div class="sp-alt">NHS Supply Chain writes this as ' + esc(s.variants.join(', ')) + '</div>';
      }
      h += '</td><td>';
      for (j = 0; j < s.frameworks.length; j++) {
        h += '<span class="sp-chip">' + esc(s.frameworks[j]) + '</span>';
      }
      h += '</td></tr>';
    }
    for (i = 0; i < dir.length; i++) {
      s = dir[i];
      find = s.name + ' ' + (s.directoryName || '');
      h += '<tr data-n="' + esc(find.toLowerCase()) + '"><td style="font-weight:600;"><span class="sp-prov sp-prov-dir">Directory-tagged</span>' + esc(s.name);
      h += '<div class="sp-alt">Filed under: ' + esc((s.seedLabels || []).join(', ')) + '</div></td><td>';
      if (s.otherFrameworks.length || s.directoryFrameworks.length) {
        var parts = [];
        for (j = 0; j < s.otherFrameworks.length; j++) { parts.push(fwLink(s.otherFrameworks[j].name, s.otherFrameworks[j].url)); }
        h += s.otherFrameworks.length ? '<div class="sp-note">On another speciality\'s NHS Supply Chain framework, not counted here: ' + parts.join('; ') + '</div>' : '';
        var dparts = [];
        for (j = 0; j < s.directoryFrameworks.length; j++) {
          var df = s.directoryFrameworks[j];
          dparts.push(df.url ? '<a href="' + esc(df.url) + '" target="_blank" rel="noopener">' + esc(df.name) + '</a>' : esc(df.name));
        }
        h += s.directoryFrameworks.length ? '<div class="sp-note">The supplier directory also records: ' + dparts.join('; ') + '</div>' : '';
      } else {
        h += '<span class="sp-note">No framework on record</span>';
      }
      h += '</td></tr>';
    }
    h += '</table></div>';
    h += '<div class="sp-meta" id="sp-count"></div>';
    h += ruleBlock(d.rules, ['suppliers', 'directorySuppliers']);
    SUP.innerHTML = h;

    var box = document.getElementById('sp-find');
    var rows = SUP.querySelectorAll('#sp-suptbl tr[data-n]');
    var count = document.getElementById('sp-count');
    function apply() {
      var q = box.value.trim().toLowerCase();
      var shown = 0;
      for (var k = 0; k < rows.length; k++) {
        var hit = !q || rows[k].getAttribute('data-n').indexOf(q) !== -1;
        rows[k].style.display = hit ? '' : 'none';
        if (hit) { shown++; }
      }
      if (q) {
        count.textContent = shown + ' of ' + rows.length + ' suppliers match "' + box.value.trim() + '".';
      } else {
        var t = d.counts.suppliers + ' framework-named suppliers, from ' + d.counts.frameworks + ' frameworks' +
                (dir.length ? ', and ' + dir.length + ' directory-tagged.' : '.');
        if (d.counts.suppliersUnresolved) {
          t += ' ' + d.counts.suppliersUnresolved + ' are shown exactly as NHS Supply Chain wrote them, because the Hub\'s alias registry holds no entry for them yet.';
        }
        count.textContent = t;
      }
    }
    box.addEventListener('input', apply);
    apply();
  }

  function month(p) {
    var M = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return p ? M[parseInt(p.slice(4), 10) - 1] + ' ' + p.slice(0, 4) : '';
  }

  function bars(rows, key, labelKey, hi) {
    var max = 0, out = '';
    for (var i = 0; i < rows.length; i++) { if (rows[i][key] > max) { max = rows[i][key]; } }
    for (i = 0; i < rows.length; i++) {
      var r = rows[i], w = max ? Math.max(1, Math.round(r[key] * 100 / max)) : 0;
      out += '<div class="ms-bar' + (hi && r[labelKey] === hi ? ' ms-hi' : '') + '"><span>' + esc(r[labelKey]) +
             (r.generic ? ' <span class="sp-chip">generic</span>' : '') + '</span><b>' +
             (r.pct === null || r.pct === undefined ? '' : r.pct.toFixed(1) + '%') +
             '</b><i><em style="width:' + w + '%"></em></i></div>';
    }
    return out;
  }

  /* WHO HOLDS THE MARKET — primary care, secondary care, Drug Tariff (30/09/2026). */
  function renderMarket(d) {
    var ms = d.marketShare;
    if (!ms || !ms.markets || !ms.markets.length) {
      MKT.innerHTML = '<div class="empty-state">No computed market share is built for this speciality yet. The prescribing data only names brands where a market is a set of branded products, and none is marked for this page.</div>';
      return;
    }
    var h = '';
    for (var k = 0; k < ms.markets.length; k++) {
      var M = ms.markets[k], P = M.primary, S = M.secondary, T = M.tariff;
      var top = P.brands.slice(0, P.topN);
      h += '<h3 class="sub-h3">' + esc(M.label) + ': who holds the market</h3>';
      h += '<p class="ms-sub">Computed from NHS data at every refresh, not a market report. Three views of the same BNF codes (' + esc(M.bnf.join(', ')) + '), shown side by side and never added together, because each counts something different.</p>';
      h += '<div class="ms-grid">';
      /* Primary care */
      var pr = [];
      for (var i = 0; i < top.length; i++) { pr.push({brand: top[i].brand, generic: top[i].generic, v: top[i].items, pct: top[i].share}); }
      h += '<div class="ms-card"><h4>Primary care</h4><p class="ms-sub">GP prescriptions dispensed in England, ' + esc(month(P.latestPeriod)) + '. Brand share of items.</p>' +
           '<div class="ms-big">' + n(P.items) + '<small>items in ' + esc(month(P.latestPeriod)) + ' &middot; ' + n(P.items12m) + ' in 12 months &middot; ' + n(P.brandCount) + ' brands</small></div>' +
           bars(pr, 'v', 'brand') + '</div>';
      /* Secondary care */
      h += '<div class="ms-card"><h4>Secondary care</h4>';
      if (S && S.brands && S.brands.length) {
        var sr = [];
        for (i = 0; i < Math.min(P.topN, S.brands.length); i++) { sr.push({brand: S.brands[i].brand, generic: S.brands[i].generic, v: S.brands[i].items12m, pct: S.brands[i].share12m}); }
        h += '<p class="ms-sub">NHS trust prescriptions dispensed in a community pharmacy, ' + esc(month(S.window12m[0])) + ' to ' + esc(month(S.window12m[1])) + '. Brand share of items. Not in-hospital use.</p>' +
             '<div class="ms-big">' + n(S.items12m) + '<small>items in 12 months &middot; ' + n(S.trusts) + ' trusts &middot; ' + n(S.brandCount) + ' brands</small></div>' + bars(sr, 'v', 'brand');
      } else {
        h += '<div class="empty-state">No trust prescribing dispensed in the community is recorded for these codes.</div>';
      }
      h += '</div>';
      /* Drug Tariff */
      h += '<div class="ms-card"><h4>Drug Tariff</h4>';
      if (T && T.topSuppliers && T.topSuppliers.length) {
        var tr = [], mx = T.lineCount || 0;
        for (i = 0; i < T.topSuppliers.length; i++) {
          var ts = T.topSuppliers[i];
          tr.push({brand: ts.supplier || ts.name, v: ts.lines, pct: mx ? ts.lines * 100 / mx : null});
        }
        h += '<p class="ms-sub">Part IX lines listed for these codes, ' + esc(T.effectiveMonth) + '. Share of tariff lines by supplier: what is listed and reimbursable, not what is sold.</p>' +
             '<div class="ms-big">' + n(T.lineCount) + '<small>lines &middot; ' + n(T.supplierCount) + ' suppliers</small></div>' + bars(tr, 'v', 'brand');
      } else {
        h += '<div class="empty-state">No Drug Tariff Part IX slice applies to these codes.</div>';
      }
      h += '</div></div>';
      /* Brand picker: any brand, its share and its top ICBs */
      var id = 'ms-pick-' + k;
      h += '<div class="ms-pick"><h4 style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:var(--navy);margin:0;font-weight:800;">Pick a brand: share, trend and where it is prescribed</h4>' +
           '<select id="' + id + '" aria-label="Brand">';
      for (i = 0; i < P.brands.length; i++) {
        h += '<option value="' + i + '">' + esc(P.brands[i].brand) + ' (' + (P.brands[i].share === null ? '' : P.brands[i].share.toFixed(1) + '%') + ')</option>';
      }
      h += '</select><div id="' + id + '-out"></div></div>';
      h += '<div class="sp-meta">Primary care: ' + esc(ms.gpSource) + '. Secondary care: ' + esc((S && S.source) || 'not available') + '. Drug Tariff: NHSBSA Drug Tariff Part IX. ' + esc(ms.attribution || '') + '</div>';
    }
    h += ruleBlock(d.rules, ['marketShare']);
    MKT.innerHTML = h;

    function wire(k2) {
      var M2 = ms.markets[k2], sel = document.getElementById('ms-pick-' + k2), out = document.getElementById('ms-pick-' + k2 + '-out');
      function show() {
        var b = M2.primary.brands[parseInt(sel.value, 10)], x = '', sec = null;
        var sb = (M2.secondary && M2.secondary.brands) || [];
        for (var j = 0; j < sb.length; j++) { if (sb[j].brand === b.brand) { sec = sb[j]; } }
        x += '<div class="sp-tiles">' +
             '<div class="sp-tile"><b>' + n(b.items) + '</b><span>GP items, ' + esc(month(M2.primary.latestPeriod)) + '</span></div>' +
             '<div class="sp-tile"><b>' + (b.share === null ? '&ndash;' : b.share.toFixed(1) + '%') + '</b><span>Share of items</span></div>' +
             '<div class="sp-tile"><b>&pound;' + n(b.cost) + '</b><span>Actual cost, ' + esc(month(M2.primary.latestPeriod)) + '</span></div>' +
             '<div class="sp-tile"><b>' + pct(b.yoy) + '</b><span>Items vs a year earlier</span></div>' +
             '<div class="sp-tile"><b>' + n(b.icbsPrescribing) + '</b><span>ICBs prescribing it</span></div>' +
             '<div class="sp-tile"><b>' + (sec ? n(sec.items12m) : '0') + '</b><span>Trust items, 12 months</span></div></div>';
        if (b.products && b.products.length) { x += '<p class="ms-sub">Products counted: ' + esc(b.products.join(', ')) + '.</p>'; }
        x += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Top ICBs for ' + esc(b.brand) + '</th><th class="sp-num">Items</th><th class="sp-num">Share of the ICB\'s market</th></tr>';
        for (j = 0; j < b.topIcbs.length; j++) {
          var ic = b.topIcbs[j];
          x += '<tr><td>' + esc(ic.name) + '</td><td class="sp-num">' + n(ic.items) + '</td><td class="sp-num">' + (ic.shareOfIcb === null ? '' : ic.shareOfIcb.toFixed(1) + '%') + '</td></tr>';
        }
        x += '</table></div>';
        out.innerHTML = x;
      }
      sel.addEventListener('change', show);
      show();
    }
    for (var w = 0; w < ms.markets.length; w++) { wire(w); }
  }

  css();
  fetch(BASE + slug + '.json?cb=' + new Date().toISOString().slice(0, 13))
    .then(function (r) {
      if (!r.ok) { throw new Error('HTTP ' + r.status); }
      return r.json();
    })
    .then(function (d) {
      if (!d.defined) {
        var why = d.whyEmpty || 'No filtered data has been built for this speciality yet.';
        fail(FW, why);
        fail(SUP, why);
        fail(MKT, why);
        return;
      }
      if (FW) { renderFrameworks(d); }
      if (SUP) { renderSuppliers(d); }
      if (MKT) { renderMarket(d); }
    })
    .catch(function (e) {
      var msg = 'This panel could not load its data (' + e.message + '). Nothing is missing from the page. Reload, and if it persists it is the feed, not your access.';
      fail(FW, msg);
      fail(SUP, msg);
      fail(MKT, msg);
    });
})();
