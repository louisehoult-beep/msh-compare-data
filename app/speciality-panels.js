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
      /* The card is always light (var(--panel)), but a page may seat the panel in a dark band
         whose own rule colours its text light: Patient Handling's `.msh #suppliers-frameworks
         .inner p` (1,2,1) beat `.msh .sp-li p` and left the fact text near-white on white
         (08/10/2026). An id plus three classes (1,3,1) keeps card text dark wherever it sits. */
      '.msh #msh-spec-frameworks .sp-sec .sp-li, .msh #msh-spec-frameworks .sp-sec .sp-li p, .msh #msh-spec-frameworks .sp-sec .sp-li-u{color:var(--ink);}',
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
    var soon = 0, i, j, m;
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
    /* WHO IS ON EACH LOT (01/10/2026). Only for a framework whose owner publishes a
       lot-by-lot supplier list; the builder (lot_split) carries nothing otherwise. */
    for (i = 0; i < d.frameworks.length; i++) {
      var fl = d.frameworks[i];
      if (!fl.lots || !fl.lots.length) { continue; }
      h += '<details class="sp-lots" style="margin:10px 0 0;"><summary style="cursor:pointer;font-weight:600;font-size:13.5px;">Who is on each lot: ' + esc(fl.name) + '</summary>';
      h += '<p style="font-size:12.5px;line-height:1.55;margin:6px 0;">As named by ' + esc(fl.lotOwner || 'the framework owner') + '. Being named on a lot is a route to supply, not a share of it.</p>';
      for (j = 0; j < fl.lots.length; j++) {
        var lt = fl.lots[j];
        h += '<div style="margin:0 0 8px;"><b>' + esc(lt.id) + (lt.title ? ': ' + esc(lt.title) : '') + '</b> <span style="opacity:.75;">(' + lt.suppliers.length + ')</span><br>' +
             (lt.suppliers.length ? esc(lt.suppliers.join(', ')) : '<i>No supplier named against this lot.</i>') + '</div>';
      }
      h += '</details>';
    }
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

    /* DIGITAL BUYING SIGNALS (20/10/2026) — the digital page only. NHS-buyer notices
       with a software or IT services Common Procurement Vocabulary (CPV) code, from
       data/digital-lane.json, clinical rows only; the builder chooses the rows, this
       only draws them. Absent on every other speciality. */
    if (d.digitalLane) {
      var dl = d.digitalLane, dc = dl.counts || {};
      var dlRow = function (title, url, who, when) {
        return '<tr><td>' + (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(title) + '</a>' : esc(title)) +
               '</td><td>' + esc(who || '') + '</td><td>' + esc(when || 'not stated') + '</td></tr>';
      };
      h += '<div class="sp-sec"><h3 class="sub-h3">Digital buying signals</h3>';
      h += '<p style="font-size:13px;line-height:1.6;margin:0 0 4px;">NHS buyers\' software and IT notices, narrowed to the ones that name a clinical system or a regulated digital product. Payroll, finance and office software is held in the lane but not shown.</p>';
      h += '<div class="sp-li-g">Open now</div>';
      if (!dl.openNotices.length) {
        h += '<div class="empty-state">No clinical digital notice from an NHS buyer is open for bidding today. ' + n(dc.openNotices || 0) + ' NHS software or IT notice(s) are open, none naming a clinical system. Checked against the live feeds, not left blank.</div>';
      } else {
        h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Notice</th><th>Buyer</th><th>Closes</th></tr>';
        for (i = 0; i < dl.openNotices.length; i++) { var on = dl.openNotices[i]; h += dlRow(on.title, on.url, on.buyer, on.closingDate ? on.closingDate.slice(0, 10) : ''); }
        h += '</table></div>';
      }
      h += '<div class="sp-li-g">Market engagement and further competitions</div>';
      if (!dl.marketEngagement.length) {
        h += '<div class="empty-state">No clinical digital market engagement or further competition is open on the NHS eCommercial system today. ' + n(dc.marketEngagement || 0) + ' software or IT row(s) are open there, none naming a clinical system.</div>';
      } else {
        h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Opportunity</th><th>Authority</th><th>Responses by</th></tr>';
        for (i = 0; i < dl.marketEngagement.length; i++) { var me = dl.marketEngagement[i]; h += dlRow(me.title, me.url, me.authority, me.deadline); }
        h += '</table></div>';
      }
      h += '<div class="sp-li-g">Recent clinical digital notices and awards</div>';
      if (!dl.awards.length) {
        h += '<div class="empty-state">No clinical digital notice from an NHS buyer is held yet.</div>';
      } else {
        h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Notice</th><th>Buyer</th><th>Published</th></tr>';
        for (i = 0; i < dl.awards.length; i++) {
          var aw = dl.awards[i];
          h += dlRow(aw.title + (aw.stage && aw.stage !== 'award' ? ' (' + aw.stage + ')' : ''), aw.url,
                     aw.buyer,
                     aw.published);
        }
        h += '</table></div>';
        h += '<div class="sp-meta">' + n(dl.awards.length) + ' most recent of ' + n(dl.awardsClinicalTotal) + ' clinical rows, out of ' + n(dc.awards || 0) + ' NHS software and IT notices held.</div>';
      }
      if (dl.gates && dl.gates.pages && dl.gates.pages.length) {
        h += '<div class="sp-li-g">Gates tracker: when each owner last changed its page</div>';
        h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Gate page</th><th>Owner</th><th>Last changed</th></tr>';
        for (i = 0; i < dl.gates.pages.length; i++) {
          var gp = dl.gates.pages[i];
          h += '<tr><td><a href="' + esc(gp.url) + '" target="_blank" rel="noopener">' + esc(gp.title || gp.url) + '</a>' +
               (gp.latestChange ? '<div class="sp-li-d">' + esc(gp.latestChange) + '</div>' : '') + '</td><td>' + esc(gp.owner) +
               '</td><td>' + esc(gp.lastUpdated) + (gp.changedSinceLastRun ? ' <b>(new)</b>' : '') + '</td></tr>';
        }
        h += '</table></div><div class="sp-meta">The owner\'s own date and change note, read ' + esc(dl.gates.dataAsOf || '') + '. Nothing is summarised.</div>';
      }
      if (dl.frameworks && dl.frameworks.items && dl.frameworks.items.length) {
        h += '<div class="sp-li-g">Digital buying routes: live and coming frameworks</div>';
        for (i = 0; i < dl.frameworks.items.length; i++) {
          var fx = dl.frameworks.items[i], lotsTxt = [];
          for (var lj = 0; lj < (fx.lots || []).length; lj++) {
            var lt = fx.lots[lj];
            lotsTxt.push('Lot ' + esc(lt.lot) + (lt.name ? ' ' + esc(lt.name) : '') + (lt.suppliers !== null && lt.suppliers !== undefined ? ' (' + n(lt.suppliers) + ' suppliers)' : ''));
          }
          h += '<div class="sp-li"><div class="sp-li-h"><div class="sp-li-t"><a href="' + esc(fx.url) + '" target="_blank" rel="noopener">' + esc(fx.name) + '</a> (' + esc(fx.reference) + ')</div>' +
               '<div class="sp-li-d">' + (fx.status === 'coming' ? '<b>Coming</b> &middot; ' : '') + esc(fx.starts || 'start not stated') + ' to ' + esc(fx.ends || 'not stated') + '</div></div>';
          h += '<div class="sp-li-o">' + esc(fx.owner) + (fx.estimatedValue ? ' &middot; ' + esc(fx.estimatedValue) : '') + '</div>';
          if (lotsTxt.length) { h += '<p style="font-size:13px;">' + lotsTxt.join('; ') + '</p>'; }
          if (fx.status === 'coming') { h += '<p style="font-size:13px;">No supplier list exists until the award is published.</p>'; }
          if (fx.notVerified && fx.notVerified.length) { h += '<div class="sp-li-m">Not verified: ' + esc(fx.notVerified.map(function (x) { return typeof x === 'string' ? x : (x.item || x.what || JSON.stringify(x)); }).join(' ')) + '</div>'; }
          h += '</div>';
        }
      }
      if (dl.airlock && dl.airlock.phases) {
        h += '<div class="sp-li-g">MHRA AI Airlock cohorts</div>';
        for (i = 0; i < dl.airlock.phases.length; i++) {
          var ph = dl.airlock.phases[i];
          h += '<p style="font-size:13px;margin:8px 0 4px;"><b>' + esc(ph.phase) + '</b>' + (ph.status ? ' &middot; ' + esc(ph.status) : '') +
               (ph.sourceUrl ? ' &middot; <a href="' + esc(ph.sourceUrl) + '" target="_blank" rel="noopener">MHRA page</a>' + (ph.pageUpdated ? ', updated ' + esc(ph.pageUpdated) : '') : '') + '</p>';
          if (!ph.members.length) { h += '<div class="empty-state">' + esc(ph.note || 'No cohort has been announced for this phase.') + '</div>'; continue; }
          h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>As named by the MHRA</th><th>Regulatory theme</th></tr>';
          for (var mj = 0; mj < ph.members.length; mj++) {
            var mm = ph.members[mj];
            h += '<tr><td>' + esc([mm.company, mm.product && mm.product !== mm.company ? mm.product : ''].filter(Boolean).join(': ') || 'not named') + (mm.status && mm.status !== 'participating' ? ' (' + esc(mm.status) + ')' : '') + '</td><td>' + esc(mm.theme || '') + '</td></tr>';
          }
          h += '</table></div>';
        }
      }
      if (dl.dspt) {
        h += '<div class="sp-li-g">Data Security and Protection Toolkit (DSPT) status, digital-tagged suppliers</div>';
        if (dl.dspt.defined === false || !dl.dspt.matched.length) {
          h += '<div class="empty-state">' + esc(dl.dspt.whyEmpty || 'No digital-tagged supplier matched a published DSPT record by exact name.') + '</div>';
        } else {
          h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Supplier</th><th>Status as published</th><th>Published</th></tr>';
          for (i = 0; i < dl.dspt.matched.length; i++) { var dx = dl.dspt.matched[i]; h += '<tr><td>' + esc(dx.name) + '</td><td>' + esc(dx.status) + '</td><td>' + esc(dx.statusDate || '') + '</td></tr>'; }
          h += '</table></div><div class="sp-meta">' + n(dl.dspt.matched.length) + ' matched by exact name; ' + n(dl.dspt.unmatched) + ' digital-tagged suppliers had no exact-name record, which says nothing about their status. Source: <a href="' + esc(dl.dspt.sourceUrl) + '" target="_blank" rel="noopener">DSPT organisation search</a>, read ' + esc(dl.dspt.checked || '') + '.</div>';
        }
      }
      if (dl.icbDigital) {
        var idg = dl.icbDigital;
        var ddmy = function (iso) { var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || ''); return m ? m[3] + '/' + m[2] + '/' + m[1] : (iso || ''); };
        var idated = idg.dated || [];
        h += '<div class="sp-li-g">Integrated care board (ICB) digital leaders</div>';
        h += '<p style="font-size:13px;line-height:1.6;margin:0;">' + n(idg.published) + ' of ' + n(idg.icbs) + ' ICBs name a current digital leader on the leadership pages the Hub reads' +
             (idg.dated ? '; ' + n(idated.length) + ' more named one only in older board papers or news (starred*, not confirmed current); ' + n(idg.none) + ' name none in anything the Hub found from 2022 onwards, which is not the same as having no such role.' :
              '; ' + n(idg.notFound) + ' do not on those pages, which is not the same as having no such role; ' + n(idg.unread) + ' pages could not be read this time.') + '</p>';
        for (i = 0; i < (idg.named || []).length; i++) {
          var nm = idg.named[i];
          var who = (nm.people || []).map(function (p) { return esc(p.name) + ', ' + esc(p.title); }).join('; ') || esc((nm.titles || []).join('; '));
          h += '<p style="font-size:13px;margin:4px 0 0;">' + esc(nm.icb) + ': ' + who + (nm.source ? ' (<a href="' + esc(nm.source) + '" target="_blank" rel="noopener">source</a>)' : '') + '</p>';
        }
        for (i = 0; i < idated.length; i++) {
          var dd = idated[i];
          h += '<p style="font-size:13px;margin:4px 0 0;">' + esc(dd.icb) + ': ' + esc(dd.name) + ', ' + esc(dd.title) + '*' +
               '<br><span style="font-size:12px;">*Listed in <a href="' + esc(dd.source) + '" target="_blank" rel="noopener">' + esc(dd.document) + '</a> dated ' + esc(ddmy(dd.docDate)) + '. Not confirmed current; check before contacting.</span></p>';
        }
      }
      if (dl.fdp && dl.fdp.headline) {
        var fh = dl.fdp.headline;
        h += '<div class="sp-li-g">NHS Federated Data Platform</div>';
        h += '<p style="font-size:13px;line-height:1.6;margin:0;">' + n(fh.trustsLive) + ' NHS trusts and ' + n(fh.icbsLive) + ' integrated care boards (ICBs) live; ' +
             n(fh.trustsSignedUp) + ' trusts signed up, as at ' + esc(dl.fdp.sourceAsAt || 'not stated') + '. NHS England updated these figures on ' + esc(dl.fdp.sourceUpdatedOn || 'a date not stated') +
             (dl.fdp.sourceNextUpdate ? ', next update ' + esc(dl.fdp.sourceNextUpdate) : '') + '. ' +
             (dl.fdp.url ? '<a href="' + esc(dl.fdp.url) + '" target="_blank" rel="noopener">NHS England\'s list of live organisations</a>.' : '') + '</p>';
      }
      h += '</div>';
    }

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
        h += '<td>' + (a.url ? '<a href="' + esc(a.url) + '" target="_blank" rel="noopener">' + esc(a.title) + '</a>' : esc(a.title));
        /* A planning or tender notice is a buyer's intention, not an award (01/10/2026). */
        if (a.stage === 'planning' || a.stage === 'tender') {
          h += ' <span class="sp-chip" style="font-weight:600;">' + (a.stage === 'planning' ? 'Planning notice, not yet awarded' : 'Tender notice, not yet awarded') + '</span>';
        }
        h += '</td>';
        h += '<td>' + esc(a.buyer || 'not stated') + '</td><td>' + esc(a.supplier || (a.stage === 'planning' || a.stage === 'tender' ? 'not yet awarded' : 'not named')) + '</td></tr>';
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

    /* DRUG TARIFF PRICE MOVES — this month against last month, same slice (16/10/2026).
       Only panels whose rule opts in carry d.drugTariffMoves. */
    if (d.drugTariffMoves) {
      var tm = d.drugTariffMoves;
      var pen = function (v) { return '&pound;' + Number(v).toFixed(2); };
      var sgn = function (v) { return (v > 0 ? '+' : '') + v.toFixed(1) + '%'; };
      var pack = function (m) { return (m.qty ? m.qty + ' ' : '') + (m.uom || '') + (m.size ? ' ' + m.size : ''); };
      h += '<div class="sp-sec"><h3 class="sub-h3">Drug Tariff price moves: ' + esc(tm.previousMonth) + ' to ' + esc(tm.currentMonth) + '</h3>';
      h += '<div class="sp-tiles">';
      h += '<div class="sp-tile"><b>' + n(tm.movedCount) + '</b><span>Lines changed price</span></div>';
      h += '<div class="sp-tile"><b>' + n(tm.upCount) + ' up, ' + n(tm.downCount) + ' down</b><span>Direction</span></div>';
      h += '<div class="sp-tile"><b>' + n(tm.unchanged) + '</b><span>Lines unchanged</span></div>';
      h += '<div class="sp-tile"><b>' + n(tm.addedCount) + ' new, ' + n(tm.droppedCount) + ' gone</b><span>Lines listed or no longer listed</span></div>';
      h += '</div>';
      if (!tm.movedCount) {
        h += '<div class="empty-state">No line on this patch changed price between ' + esc(tm.previousMonth) + ' and ' + esc(tm.currentMonth) + '.</div>';
      } else {
        h += '<p style="font-size:13px;line-height:1.6;margin:0 0 10px;">Who moved:</p><div>';
        for (i = 0; i < tm.suppliers.length; i++) {
          var sp = tm.suppliers[i];
          h += '<span class="sp-chip">' + esc(sp.name) + ' &middot; ' + (sp.up + sp.down) + ' line' + ((sp.up + sp.down) === 1 ? '' : 's') +
               ' &middot; ' + sgn(sp.minPct) + (sp.minPct !== sp.maxPct ? ' to ' + sgn(sp.maxPct) : '') + '</span>';
        }
        h += '</div>';
        h += '<details class="sp-more"><summary>Show ' + tm.moves.length + (tm.movedCount > tm.moves.length ? ' of ' + n(tm.movedCount) : '') + ' lines that moved, largest first</summary>';
        h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Supplier</th><th>Product</th><th>Pack</th><th class="sp-num">Was</th><th class="sp-num">Now</th><th class="sp-num">Change</th></tr>';
        for (i = 0; i < tm.moves.length; i++) {
          var mv = tm.moves[i];
          h += '<tr><td>' + esc(mv.supplier) + '</td><td>' + esc(mv.product) + '</td><td>' + esc(pack(mv)) + '</td><td class="sp-num">' + pen(mv.was) +
               '</td><td class="sp-num">' + pen(mv.now) + '</td><td class="sp-num">' + sgn(mv.pct) + '</td></tr>';
        }
        h += '</table></div></details>';
      }
      var extra = [['New on the tariff this month', tm.added], ['Not on this month\'s tariff', tm.dropped]];
      for (var xi = 0; xi < extra.length; xi++) {
        if (extra[xi][1].length) {
          h += '<details class="sp-more"><summary>' + extra[xi][0] + ' (' + extra[xi][1].length + ')</summary><div class="sp-scroll"><table class="sp-tbl"><tr><th>Supplier</th><th>Product</th><th>Pack</th><th class="sp-num">Price</th></tr>';
          for (i = 0; i < extra[xi][1].length; i++) {
            var ex = extra[xi][1][i];
            h += '<tr><td>' + esc(ex.supplier) + '</td><td>' + esc(ex.product) + '</td><td>' + esc(pack(ex)) + '</td><td class="sp-num">' + pen(ex.now != null ? ex.now : ex.was) + '</td></tr>';
          }
          h += '</table></div></details>';
        }
      }
      h += '<div class="sp-meta">Drug Tariff reimbursement prices, not what a supplier charges. ' + esc(tm.previousMonth) + ' file as at ' + esc(tm.previousDataAsOf || 'not stated') + '; ' + esc(tm.currentMonth) + ' file as at ' + esc(tm.dataAsOf || 'not stated') + '.</div>';
      h += '</div>';
    }

    /* DISCONTINUED LINES STILL ON FORMULARIES (16/10/2026). Only panels with entries in
       data/discontinued-on-formulary.json carry d.discontinuedOnFormulary. */
    if (d.discontinuedOnFormulary) {
      var df = d.discontinuedOnFormulary;
      var dmy = function (iso) { var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || ''); return m ? m[3] + '/' + m[2] + '/' + m[1] : (iso || ''); };
      var STAT = { 'recommended': 'Recommended or ranked', 'less-cost-effective': 'Listed as less cost-effective', 'non-formulary': 'Named as non-formulary' };
      h += '<div class="sp-sec"><h3 class="sub-h3">Discontinued lines still on formularies</h3>';
      h += '<p style="font-size:13px;line-height:1.6;margin:0 0 10px;">Products the NHS Dictionary of Medicines and Devices (dm+d) records as discontinued, that a formulary document still names. Each line is quoted as printed, as read on ' + esc(dmy(df.readOn)) + '.</p>';
      for (var pi = 0; pi < df.products.length; pi++) {
        var pr = df.products[pi], pk = [];
        for (var ki = 0; ki < pr.dmd.packs.length; ki++) {
          pk.push(esc(pr.dmd.packs[ki].size) + ' discontinued ' + esc(dmy(pr.dmd.packs[ki].discontinued)));
        }
        h += '<h4 style="margin:14px 0 6px;font-size:15px;color:inherit;">' + esc(pr.name) + '</h4>';
        h += '<div class="sp-tiles">';
        h += '<div class="sp-tile"><b>' + n(pr.formularies) + '</b><span>Formularies naming it</span></div>';
        h += '<div class="sp-tile"><b>' + n(pr.counts.recommended) + '</b><span>Recommended or ranked</span></div>';
        h += '<div class="sp-tile"><b>' + n(pr.counts['less-cost-effective']) + '</b><span>Less cost-effective</span></div>';
        h += '<div class="sp-tile"><b>' + n(pr.counts['non-formulary']) + '</b><span>Named as non-formulary</span></div>';
        h += '</div>';
        h += '<div class="sp-meta">dm+d: <a href="' + esc(pr.dmd.url) + '" target="_blank" rel="noopener">' + esc(pr.dmd.status) + ', ' + esc(pr.dmd.availability.toLowerCase()) + '</a>; ' + pk.join('; ') + '. ' +
             (pr.partIxListed ? 'Listed in Drug Tariff Part IX ' + esc(pr.partIxMonth) + '.' : 'Not listed in Drug Tariff Part IX ' + esc(pr.partIxMonth) + '.') + '</div>';
        h += '<details class="sp-more"><summary>Show the formularies that name it</summary><div class="sp-scroll"><table class="sp-tbl"><tr><th>Formulary</th><th>Position</th><th>Line as printed</th><th>Document and review</th></tr>';
        for (i = 0; i < df.listings.length; i++) {
          var L = df.listings[i];
          if (L.product !== pr.id) { continue; }
          h += '<tr><td><a href="' + esc(L.url) + '" target="_blank" rel="noopener">' + esc(L.org) + '</a></td><td><b>' + esc(STAT[L.status] || L.status) + '</b><br>' + esc(L.position) +
               '</td><td>' + esc(L.line) + '</td><td>' + esc(L.document || '') + (L.documentDate ? '<br>' + esc(L.documentDate) : '') + (L.reviewDate ? '<br>' + esc(L.reviewDate) : '') + '</td></tr>';
        }
        h += '</table></div></details>';
      }
      h += '<div class="sp-meta">Retail availability is not covered: dm+d records NHS supply. A formulary not listed here was not read or does not name the product.</div>';
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
    h += ruleBlock(d.rules, ['frameworks', 'awards', 'openTenders', 'digitalLane', 'drugTariff', 'drugTariffMoves', 'discontinuedOnFormulary', 'drugTariffViiia', 'gpPrescribing', 'mhraDsu', 'localIntel']);
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
        var lotIds = s.lots && s.lots[s.frameworks[j]];
        h += '<span class="sp-chip">' + esc(s.frameworks[j]) +
             (lotIds && lotIds.length ? ' &middot; ' + esc(lotIds.map(function (x) { return x.replace(/^Lot /, ''); }).join(', ')) : '') + '</span>';
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
