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
  if (!FW && !SUP) { return; }
  var slug = (FW || SUP).getAttribute('data-speciality');
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
      '.msh .sp-alt{font-size:11px;color:var(--dim);font-weight:400;margin-top:3px;line-height:1.45;}'
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
    h += '<div class="sp-tile"><b>' + d.counts.suppliers + '</b><span>Named suppliers</span></div>';
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

    h += '<div class="sp-meta">Frameworks as at ' + esc(d.dataAsOf.frameworks || 'not stated') +
         ' &middot; awards as at ' + esc(d.dataAsOf.tenderHistory || 'not stated') +
         ' &middot; Drug Tariff as at ' + esc(d.dataAsOf.drugTariff || 'not stated') + '.</div>';
    h += ruleBlock(d.rules, ['frameworks', 'awards', 'openTenders', 'drugTariff']);
    FW.innerHTML = h;
  }

  function renderSuppliers(d) {
    if (!SUP) { return; }
    var h = '';
    /* No framework means no supplier list can honestly be drawn. Say so, rather than
       showing a search box over an empty table, and never fall back to a keyword
       guess against the whole directory. */
    if (!d.suppliers.length) {
      h += '<div class="empty-state">No supplier list is published for this speciality. This panel names suppliers only where NHS Supply Chain names them on the speciality\'s own frameworks, and this patch has none for a list to be drawn from. Firms that sell here do appear on NHSSC frameworks, but on other specialities\' frameworks, and they are counted on those pages. The awarded contracts on the previous tab do name who won them.</div>';
      h += ruleBlock(d.rules, ['suppliers']);
      SUP.innerHTML = h;
      return;
    }
    h += '<p style="font-size:13.5px;line-height:1.65;margin:0 0 14px;">Every supplier NHS Supply Chain names on this speciality\'s own frameworks, ' +
         d.counts.suppliers + ' of them, resolved to one name per company. Not the whole directory, and not a guess: these are the firms on the agreements a buyer on this patch actually orders through.</p>';
    h += '<input class="sp-find" id="sp-find" type="search" placeholder="Find a supplier..." autocomplete="off">';
    h += '<div class="sp-scroll"><table class="sp-tbl" id="sp-suptbl">';
    h += '<tr><th>Supplier</th><th>On these frameworks</th></tr>';
    for (var i = 0; i < d.suppliers.length; i++) {
      var s = d.suppliers[i];
      var find = s.name + ' ' + (s.variants || []).join(' ');
      h += '<tr data-n="' + esc(find.toLowerCase()) + '"><td style="font-weight:600;">' + esc(s.name);
      if (s.variants && s.variants.length) {
        h += '<div class="sp-alt">NHS Supply Chain writes this as ' + esc(s.variants.join(', ')) + '</div>';
      }
      h += '</td><td>';
      for (var j = 0; j < s.frameworks.length; j++) {
        h += '<span class="sp-chip">' + esc(s.frameworks[j]) + '</span>';
      }
      h += '</td></tr>';
    }
    h += '</table></div>';
    h += '<div class="sp-meta" id="sp-count"></div>';
    h += ruleBlock(d.rules, ['suppliers']);
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
        var t = rows.length + ' suppliers, from ' + d.counts.frameworks + ' frameworks.';
        if (d.counts.suppliersUnresolved) {
          t += ' ' + d.counts.suppliersUnresolved + ' are shown exactly as NHS Supply Chain wrote them, because the Hub\'s alias registry holds no entry for them yet.';
        }
        count.textContent = t;
      }
    }
    box.addEventListener('input', apply);
    apply();
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
        return;
      }
      renderFrameworks(d);
      renderSuppliers(d);
    })
    .catch(function (e) {
      var msg = 'This panel could not load its data (' + e.message + '). Nothing is missing from the page. Reload, and if it persists it is the feed, not your access.';
      fail(FW, msg);
      fail(SUP, msg);
    });
})();
