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
      '.msh .sp-pin,.msh .sp-ics{display:inline-flex;align-items:center;gap:6px;cursor:pointer;background:var(--panel);border:1.5px solid var(--border);border-radius:99px;padding:5px 12px;font-size:12.5px;font-weight:700;color:var(--navy);line-height:1.2;text-decoration:none;font-family:inherit;}',
      '.msh .sp-pin:hover,.msh .sp-ics:hover{border-color:var(--navy);}',
      '.msh .sp-pin:focus-visible,.msh .sp-ics:focus-visible{outline:3px solid #1B5FBF;outline-offset:2px;}',
      '.msh .sp-pin[aria-pressed="true"]{background:#F7F1E3;border-color:#B8935A;color:#7E6118;}',
      '.msh .sp-pin svg{width:15px;height:15px;display:block;}',
      '.msh .sp-pin[aria-pressed="true"] svg{fill:#C9A227;stroke:#8C6A1C;}',
      '.msh .sp-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;justify-content:space-between;margin:0 0 10px;}',
      '.msh .sp-bar h4{margin:0;}',
      '.msh .sp-cal-row{display:grid;grid-template-columns:130px minmax(0,1fr) auto;gap:4px 14px;align-items:start;padding:10px 0;border-bottom:1px solid var(--border);font-size:13px;line-height:1.45;color:var(--ink);}',
      '.msh .sp-cal-row:last-child{border-bottom:0;}',
      '.msh .sp-cal-d{font-weight:700;color:var(--navy);}',
      '.msh .sp-cal-t a{color:var(--gold);font-weight:700;text-decoration:none;}',
      '.msh .sp-cal-m{font-size:11.5px;color:var(--dim);}',
      '@media (max-width:640px){.msh .sp-cal-row{grid-template-columns:minmax(0,1fr);}}',
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

  /* ---------- pin to My Hub, and the calendar (22/10/2026) ----------
     Pins are the member's own saved items (app/hub-account.js, kind "panel"),
     shown on My Hub by app/my-hub-panels.js. The buttons stay hidden for a
     visitor who is not logged in. The calendar rows are data/hub-calendar.json
     filtered to this speciality; the .ics carries only those rows. */
  var ROOT = BASE.replace('data/speciality-panels/', '');
  var PAGE = '/medical-sales-hub/' + slug + '/';
  var P = null, ACCT = null, CAL = null, PANEL = null;
  function loggedIn() { return !!(window.mshRestNonce || window.mshPrefsNonce); }
  function starSvg() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z"/></svg>';
  }
  function pinBtn(id, title) {
    return '<button type="button" class="sp-pin" hidden data-pin="' + esc(id) + '" data-pin-t="' + esc(title) + '" aria-pressed="false">' + starSvg() + '<span>Pin to My Hub</span></button>';
  }
  function pinPaint(btn) {
    var on = !!(ACCT && P && ACCT.isStarred(P.panelKey(PAGE, btn.getAttribute('data-pin'))));
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.querySelector('span').textContent = on ? 'Pinned to My Hub' : 'Pin to My Hub';
    btn.setAttribute('aria-label', (on ? 'Unpin ' : 'Pin ') + btn.getAttribute('data-pin-t') + (on ? ' from My Hub' : ' to My Hub'));
  }
  function pinPaintAll() {
    var all = document.querySelectorAll('.msh .sp-pin');
    for (var i = 0; i < all.length; i++) { all[i].hidden = !(ACCT && P); pinPaint(all[i]); }
  }
  function runSrc(src) { (new Function(src))(); }
  function getText(path) {
    return fetch(ROOT + path, { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error(path + ' ' + r.status); } return r.text(); });
  }
  function loadHelpers() {
    return Promise.all([
      window.MSH_PANELS ? '' : getText('app/hub-panels.js'),
      (window.MSH_ACCOUNT || !loggedIn()) ? '' : getText('app/hub-account.js')
    ]).then(function (got) {
      if (got[0]) { runSrc(got[0]); }
      if (got[1]) { runSrc(got[1]); }
      P = window.MSH_PANELS;
      if (loggedIn() && window.MSH_ACCOUNT) { return window.MSH_ACCOUNT.load().then(function () { ACCT = window.MSH_ACCOUNT; }); }
    });
  }
  function download(name, text) {
    var blob = new Blob([text], { type: 'text/calendar;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  function calRows() { return CAL ? P.calendarRows(CAL, slug, new Date().toISOString().slice(0, 10)) : []; }
  function calHtml() {
    var rows = calRows(), title = ((PANEL && PANEL.label) || 'This speciality') + ' calendar';
    var h = '<div class="sp-sec" id="sp-calendar"><div class="sp-bar"><h3 class="sub-h3" style="margin:0;">Calendar</h3><span>' + pinBtn('calendar', title);
    if (rows.length) { h += ' <button type="button" class="sp-ics" data-ics="all">Add all to my calendar</button>'; }
    h += '</span></div>';
    if (!rows.length) {
      return h + '<div class="empty-state">No dated conference, awareness day, framework end or contract end is recorded for this speciality yet. Nothing is estimated from a previous year.</div></div>';
    }
    for (var i = 0; i < rows.length; i++) {
      var e = rows[i], range = P.fmtDate(e.date) + (e.endDate && e.endDate > e.date ? ' to ' + P.fmtDate(e.endDate) : '');
      h += '<div class="sp-cal-row"><div class="sp-cal-d">' + esc(range) + '</div><div><div class="sp-cal-t"><a href="' + esc(e.source) + '" target="_blank" rel="noopener">' + esc(e.title) + '</a></div>' +
           '<div class="sp-cal-m">' + esc(P.typeLabel(e)) + (e.location ? ' &middot; ' + esc(e.location) : '') + (e.verified ? ' &middot; checked ' + esc(e.verified) : '') + '</div></div>' +
           '<button type="button" class="sp-ics" data-ics="' + esc(e.id) + '" aria-label="Add ' + esc(e.title) + ' to my calendar">Add to my calendar</button></div>';
    }
    return h + '<div class="sp-meta">Dates are those published by each organiser or framework owner, as held in the Hub Calendar. Each calendar entry links back to this page.</div></div>';
  }
  function wirePins(box) {
    box.addEventListener('click', function (ev) {
      var t = ev.target.closest ? ev.target.closest('[data-pin],[data-ics]') : null;
      if (!t) { return; }
      if (t.hasAttribute('data-ics')) {
        var id = t.getAttribute('data-ics'), rows = calRows();
        if (id !== 'all') { rows = rows.filter(function (r) { return r.id === id; }); }
        if (!rows.length) { return; }
        download(P.icsName(slug, id === 'all' ? '' : id), P.ics(rows, slug, ((PANEL && PANEL.label) || slug) + ' (Medical Sales Hub)', new Date().toISOString()));
        return;
      }
      if (!ACCT) { return; }
      var key = P.panelKey(PAGE, t.getAttribute('data-pin')), on = t.getAttribute('aria-pressed') !== 'true';
      t.setAttribute('aria-pressed', on ? 'true' : 'false');
      var done = on ? ACCT.star({ u: key, t: ((PANEL && PANEL.label) || slug) + ': ' + t.getAttribute('data-pin-t'), k: 'panel' }) : ACCT.unstar(key);
      done.then(function () { pinPaint(t); }, function () { pinPaint(t); });
    });
  }
  /* Called once the Frameworks panel has drawn: add the calendar, then the pins. */
  function addCalendarAndPins(d) {
    PANEL = d;
    var box = FW;
    if (!box) { return; }
    wirePins(box);
    var cal = document.createElement('div');
    cal.id = 'sp-cal-slot';
    box.appendChild(cal);
    cal.innerHTML = '<div class="empty-state">Loading the calendar.</div>';
    loadHelpers().then(function () {
      return fetch(ROOT + 'data/hub-calendar.json', { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error('calendar ' + r.status); } return r.json(); });
    }).then(function (c) {
      CAL = c.entries || [];
      cal.innerHTML = calHtml();
      pinPaintAll();
    }).catch(function () {
      cal.innerHTML = '<div class="sp-sec"><h3 class="sub-h3">Calendar</h3><div class="empty-state">The calendar could not load just now. Reload to try again.</div></div>';
      pinPaintAll();
    });
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
          h += '<div class="sp-mkt"><div class="sp-bar"><h4>' + esc(M.label) + '</h4>' + pinBtn('gp:' + M.id, 'GP prescribing, ' + M.label) + '</div>';
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

  /* HEALTH TECH COMPANY DIRECTORY (Lou, 21/10/2026) — the digital page only. Every
     Hub company record that is digital by a recorded fact (digital directory label,
     a digital framework's own supplier list, or an NHS buyer's software or IT award
     naming it exactly). Built in build_speciality_panels.py; each row opens the
     company report, which carries the products and sources. */
  function companyDirectory(d) {
    var co = d.digitalLane && d.digitalLane.companies;
    if (!co) { return ''; }
    var c = co.counts || {}, h = '', i, j, r;
    h += '<h3 id="health-tech-companies" style="margin:26px 0 6px;">Health tech company directory</h3>';
    if (!co.items || !co.items.length) {
      return h + '<div class="empty-state">No company record in the Hub\'s supplier directory is digital by a recorded fact today.</div>';
    }
    h += '<p style="font-size:13.5px;line-height:1.65;margin:0 0 10px;">' + n(c.companies) + ' health tech and digital companies with a Hub company report: ' +
         n(c.onDigitalFramework) + ' on a digital framework\'s published supplier list, ' + n(c.withDigitalAwards) +
         ' named on an NHS buyer\'s software or IT award notice, ' + n(c.withProducts) + ' with products on record. Open a name for the full company report.</p>';
    h += '<input class="sp-find" id="sp-co-find" type="search" placeholder="Find a company, framework or label..." autocomplete="off">';
    h += '<div class="sp-scroll"><table class="sp-tbl" id="sp-co-tbl"><tr><th>Company</th><th>Digital frameworks</th><th>NHS software and IT awards</th><th>Products</th></tr>';
    for (i = 0; i < co.items.length; i++) {
      r = co.items[i];
      var fw = [], find = [r.name].concat(r.labels || []);
      for (j = 0; j < (r.frameworks || []).length; j++) {
        var f = r.frameworks[j];
        find.push(f.name);
        fw.push('<span class="sp-chip">' + (f.url ? '<a href="' + esc(f.url) + '" target="_blank" rel="noopener">' + esc(f.name) + '</a>' : esc(f.name)) +
                (f.lots && f.lots.length ? ' &middot; lot ' + esc(f.lots.join(', ')) : '') + '</span>');
      }
      h += '<tr data-n="' + esc(find.join(' ').toLowerCase()) + '"><td style="font-weight:600;"><a href="' + esc(r.report) + '">' + esc(r.name) + '</a>' +
           (r.labels && r.labels.length ? '<div class="sp-alt">Filed under: ' + esc(r.labels.join(', ')) + '</div>' : '') + '</td>' +
           '<td>' + (fw.length ? fw.join(' ') : '<span class="sp-note">None on record</span>') + '</td>' +
           '<td>' + (r.digitalAwards ? n(r.digitalAwards) + (r.clinicalAwards ? ' (' + n(r.clinicalAwards) + ' clinical)' : '') +
                     (r.latestAward ? '<div class="sp-alt">latest ' + esc(r.latestAward) + '</div>' : '') : '<span class="sp-note">None in the lane</span>') + '</td>' +
           '<td>' + (r.products ? n(r.products) : '<span class="sp-note">Not captured</span>') + '</td></tr>';
    }
    h += '</table></div><div class="sp-meta" id="sp-co-count"></div>';
    h += '<div class="sp-meta">' + esc(co.rule || '') + (co.dataAsOf ? ' Data as of ' + esc(String(co.dataAsOf).slice(0, 10)) + '.' : '') + '</div>';
    return h;
  }

  function wireCompanyDirectory() {
    var box = document.getElementById('sp-co-find');
    if (!box) { return; }
    var rows = document.querySelectorAll('#sp-co-tbl tr[data-n]');
    var count = document.getElementById('sp-co-count');
    function apply() {
      var q = box.value.trim().toLowerCase(), shown = 0;
      for (var k = 0; k < rows.length; k++) {
        var hit = !q || rows[k].getAttribute('data-n').indexOf(q) !== -1;
        rows[k].style.display = hit ? '' : 'none';
        if (hit) { shown++; }
      }
      count.textContent = q ? shown + ' of ' + rows.length + ' companies match "' + box.value.trim() + '".' : rows.length + ' companies.';
    }
    box.addEventListener('input', apply);
    apply();
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
        h += companyDirectory(d);
        SUP.innerHTML = h;
        wireCompanyDirectory();
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
    h += companyDirectory(d);
    SUP.innerHTML = h;
    wireCompanyDirectory();

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
      if (M.id === 'emollients') { h += '<div id="ms-expl-' + k + '"></div><div id="ms-opp-' + k + '"></div>'; }
    }
    h += ruleBlock(d.rules, ['marketShare']);
    MKT.innerHTML = h;
    for (var xk = 0; xk < ms.markets.length; xk++) {
      var xm = document.getElementById('ms-expl-' + xk);
      if (xm) { explorer(xm); }
      var om = document.getElementById('ms-opp-' + xk);
      if (om) { icbOpp(om); }
    }

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

  /* PRESCRIBING EXPLORER (22/10/2026). Month-by-month trends, presentation level, brand
     comparison, ICB scope and PCN / practice variation for the emollient market.
     Data: data/emollient-explorer/ (scripts/build_emollient_explorer.py). Nothing here is
     estimated: every line is NHSBSA items, and every chart carries its source and period. */
  var EXPL = window.MSH_EXPLORER_BASE || 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/emollient-explorer/';
  var EX_COL = ['#14304F', '#A8842C', '#4A1526', '#1F7A8C', '#6B7785', '#2E7D4F', '#B5532A', '#5B4B8A'];

  function exCss() {
    if (document.getElementById('msh-ex-css')) { return; }
    var st = document.createElement('style');
    st.id = 'msh-ex-css';
    st.textContent = [
      '.msh .ex{margin-top:26px;border:1px solid var(--border);border-radius:10px;background:var(--panel);padding:18px 18px 14px;color:var(--ink);}',
      '.msh .ex h3{margin:0 0 4px;font-size:17px;color:var(--navy);}',
      '.msh .ex-tabs{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 14px;}',
      '.msh .ex-tabs button{font:inherit;font-size:13px;font-weight:700;padding:8px 13px;border:1px solid var(--border);border-radius:99px;background:var(--panel2);color:var(--navy);cursor:pointer;}',
      '.msh .ex-tabs button[aria-pressed="true"]{background:var(--navy);color:#fff;border-color:var(--navy);}',
      '.msh .ex-ctl{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:flex-end;margin-bottom:14px;}',
      '.msh .ex-ctl label{display:block;font-size:10px;letter-spacing:1px;text-transform:uppercase;font-weight:800;color:var(--dim);}',
      '.msh .ex-ctl>div{flex:1 1 220px;min-width:0;max-width:100%;}',
      '.msh .ex-ctl select{display:block;width:100%;margin-top:4px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;font-size:14px;background:var(--panel);color:var(--ink);max-width:100%;min-width:0;}',
      '.msh .ex-chart{margin:16px 0 4px;}',
      '.msh .ex-chart h4{font-size:13px;margin:0 0 6px;color:var(--navy);}',
      '.msh .ex-chart svg{width:100%;height:auto;display:block;overflow:visible;}',
      '.msh .ex-leg{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;margin:4px 0 6px;color:var(--ink);}',
      '.msh .ex-leg i{display:inline-block;width:18px;height:0;border-top:3px solid;vertical-align:middle;margin-right:5px;}',
      '.msh .ex-src{font-size:11.5px;color:var(--dim);line-height:1.55;margin:6px 0 0;}',
      '.msh .ex details{margin:6px 0 0;}',
      '.msh .ex details summary{cursor:pointer;font-size:12px;font-weight:700;color:var(--navy);}',
      '.msh .ex-checks{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:4px 14px;margin:6px 0 12px;}',
      '.msh .ex-checks label{font-size:13px;display:flex;gap:7px;align-items:flex-start;color:var(--ink);}',
      '.msh .ex-heat{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:6px;margin:10px 0;}',
      '.msh .ex-tile{font:inherit;text-align:left;border:1px solid var(--border);border-radius:7px;padding:8px 9px;cursor:pointer;min-height:74px;display:flex;flex-direction:column;justify-content:space-between;}',
      '.msh .ex-tile b{font-size:19px;line-height:1.1;}',
      '.msh .ex-tile span{font-size:11px;line-height:1.3;overflow-wrap:anywhere;}',
      '.msh .ex-tile[aria-pressed="true"]{outline:3px solid var(--gold);outline-offset:1px;}',
      '.msh .ex-tile.ex-low{background:repeating-linear-gradient(45deg,#fff,#fff 6px,#EEF1F5 6px,#EEF1F5 12px);color:#4A5563;cursor:default;}',
      '.msh .ex-scale{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--dim);margin:2px 0 8px;}',
      '.msh .ex-scale i{display:block;width:160px;height:10px;border-radius:5px;background:linear-gradient(90deg,#EAF0F7,#14304F);border:1px solid var(--border);}',
      '.msh .ex-sort{font:inherit;font-weight:700;font-size:12px;background:none;border:0;color:inherit;cursor:pointer;text-align:inherit;padding:0;text-decoration:underline dotted;}',
      '.msh .ex-sort[aria-pressed="true"]{color:var(--gold-ink,#7A5C12);}',
      '.msh .ex-opp .ex-row{cursor:pointer;}',
      '.msh .ex-opp .ex-row[aria-selected="true"]{outline:2px solid var(--gold);outline-offset:-2px;}',
      '.msh .ex-rk{color:var(--dim);font-size:11px;}',
      '.msh .ex-note{border-left:3px solid var(--gold);background:var(--panel2);padding:10px 14px;border-radius:0 8px 8px 0;font-size:12.5px;line-height:1.55;margin:10px 0;color:var(--ink);}'
    ].join('');
    document.head.appendChild(st);
  }

  function exShort(p) {
    var M = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return M[parseInt(p.slice(4), 10) - 1] + ' ' + p.slice(2, 4);
  }

  function exNiceMax(v) {
    if (!(v > 0)) { return 1; }
    var p = Math.pow(10, Math.floor(Math.log(v) / Math.LN10)), f = v / p;
    var s = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
    return s * p;
  }

  /* Line chart as inline SVG. series: [{name, color, dash, vals[]}]; null values break the line.
     Direct end labels plus a legend, a native tooltip on every point, and a data table below. */
  function exChart(periods, series, o) {
    var W = 640, H = 290, L = 54, R = 16, Tp = 12, B = 34, max = 0, min = o.zero === false ? Infinity : 0, i, s, m;
    for (s = 0; s < series.length; s++) {
      for (m = 0; m < series[s].vals.length; m++) {
        var v = series[s].vals[m];
        if (v !== null && v > max) { max = v; }
        if (v !== null && v < min) { min = v; }
      }
    }
    var top = exNiceMax(max), bot = 0;
    if (o.zero === false) {
      var span = (max - min) || 1, step = exNiceMax(span / 4) / (span / 4 > 5 ? 1 : 1);
      bot = Math.floor(min / step) * step; top = Math.ceil(max / step) * step; if (top === bot) { top = bot + step; }
    }
    function X(k) { return L + (W - L - R) * k / Math.max(1, periods.length - 1); }
    function Y(val) { return Tp + (H - Tp - B) * (1 - (val - bot) / (top - bot)); }
    var g = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(o.label) + '" xmlns="http://www.w3.org/2000/svg" font-family="inherit">';
    for (i = 0; i <= 4; i++) {
      var tv = bot + (top - bot) * i / 4, y = Y(tv);
      g += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y + '" y2="' + y + '" stroke="#D5DBE3" stroke-width="1"/>' +
           '<text x="' + (L - 6) + '" y="' + (y + 4) + '" text-anchor="end" font-size="11" fill="#4A5563">' + esc(o.tick(tv, top - bot)) + '</text>';
    }
    for (m = 0; m < periods.length; m++) {
      if (m % 2 === 0 || m === periods.length - 1) {
        g += '<text x="' + X(m) + '" y="' + (H - 12) + '" text-anchor="middle" font-size="11" fill="#4A5563">' + exShort(periods[m]) + '</text>';
      }
    }
    for (s = 0; s < series.length; s++) {
      var d = '', pen = false, S = series[s], last = -1;
      for (m = 0; m < S.vals.length; m++) {
        if (S.vals[m] === null) { pen = false; continue; }
        d += (pen ? 'L' : 'M') + X(m).toFixed(1) + ' ' + Y(S.vals[m]).toFixed(1);
        pen = true; last = m;
      }
      g += '<path d="' + d + '" fill="none" stroke="' + S.color + '" stroke-width="2.4" stroke-linejoin="round"' + (S.dash ? ' stroke-dasharray="' + S.dash + '"' : '') + '/>';
      for (m = 0; m < S.vals.length; m++) {
        if (S.vals[m] === null) { continue; }
        g += '<circle cx="' + X(m).toFixed(1) + '" cy="' + Y(S.vals[m]).toFixed(1) + '" r="3.2" fill="' + S.color + '"><title>' +
             esc(S.name + ', ' + month(periods[m]) + ': ' + o.fmt(S.vals[m])) + '</title></circle>';
      }
    }
    g += '</svg>';
    var leg = '<div class="ex-leg">';
    for (s = 0; s < series.length; s++) {
      leg += '<span><i style="border-color:' + series[s].color + (series[s].dash ? ';border-top-style:dashed' : '') + '"></i>' + esc(series[s].name) + '</span>';
    }
    leg += '</div>';
    var tb = '<details><summary>Show the figures</summary><div class="sp-scroll"><table class="sp-tbl"><tr><th>Month</th>';
    for (s = 0; s < series.length; s++) { tb += '<th class="sp-num">' + esc(series[s].name) + '</th>'; }
    tb += '</tr>';
    for (m = 0; m < periods.length; m++) {
      tb += '<tr><td>' + esc(month(periods[m])) + '</td>';
      for (s = 0; s < series.length; s++) { tb += '<td class="sp-num">' + (series[s].vals[m] === null ? (o.nullText || 'no items') : esc(o.fmt(series[s].vals[m]))) + '</td>'; }
      tb += '</tr>';
    }
    tb += '</table></div></details>';
    return '<div class="ex-chart"><h4>' + esc(o.title) + '</h4>' + leg + g + tb + '<p class="ex-src">' + o.src + (bot > 0 ? ' The vertical axis does not start at zero.' : '') + '</p></div>';
  }

  function explorer(mount) {
    exCss();
    mount.innerHTML = '<div class="ex"><h3>Prescribing explorer</h3><div class="empty-state">Loading the month-by-month data&hellip;</div></div>';
    fetch(EXPL + 'trends.json?cb=' + new Date().toISOString().slice(0, 13))
      .then(function (r) { if (!r.ok) { throw new Error('HTTP ' + r.status); } return r.json(); })
      .then(function (T) { exStart(mount, T); })
      .catch(function (e) {
        mount.innerHTML = '<div class="ex"><h3>Prescribing explorer</h3><div class="empty-state">The month-by-month data could not load (' + esc(e.message) + '). Nothing is missing from the rest of the page. Reload, and if it persists it is the feed, not your access.</div></div>';
      });
  }

  /* ICB OPPORTUNITY (22/10/2026). All 36 ICBs on brand share, PCN variation, deprivation and
     dermatology waiting time. Data: data/derm-icb-context/context.json
     (scripts/build_derm_icb_context.py). Every figure carries its source and period; a missing
     figure reads "Not verified". The order is an aid, not a score: the average of four ranks. */
  var OPPB = window.MSH_DERMCTX_BASE || 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/derm-icb-context/';

  function icbOpp(mount) {
    exCss();
    mount.innerHTML = '<div class="ex"><h3>ICB opportunity: where to start</h3><div class="empty-state">Loading the ICB comparison&hellip;</div></div>';
    fetch(OPPB + 'context.json?cb=' + new Date().toISOString().slice(0, 13))
      .then(function (r) { if (!r.ok) { throw new Error('HTTP ' + r.status); } return r.json(); })
      .then(function (C) { oppStart(mount, C); })
      .catch(function (e) {
        mount.innerHTML = '<div class="ex"><h3>ICB opportunity: where to start</h3><div class="empty-state">The ICB comparison could not load (' + esc(e.message) + '). Nothing is missing from the rest of the page. Reload, and if it persists it is the feed, not your access.</div></div>';
      });
  }

  function oppStart(mount, C) {
    var RP = C.periods.rtt, LAST = RP.length - 1, NV = 'Not verified';
    var S = {brand: C.brands.indexOf('QV') >= 0 ? 'QV' : C.brands[0], sort: 'avg', sel: null};
    function rankOf(vals, desc) {
      var idx = [], r = {}, i;
      for (i = 0; i < vals.length; i++) { if (vals[i] !== null && vals[i] !== undefined) { idx.push(i); } }
      idx.sort(function (a, b) { return desc ? vals[b] - vals[a] : vals[a] - vals[b]; });
      for (i = 0; i < idx.length; i++) { r[idx[i]] = i + 1; }
      return r;
    }
    function rows() {
      var I = C.icbs, b = S.brand, sh = [], sd = [], im = [], wt = [], i;
      for (i = 0; i < I.length; i++) {
        sh.push(I[i].brands[b].share);
        sd.push(I[i].brands[b].pcnSd);
        im.push(I[i].imd ? I[i].imd.score : null);
        wt.push(I[i].rtt ? I[i].rtt.median[LAST] : null);
      }
      var rs = rankOf(sh, false), rv = rankOf(sd, true), rd = rankOf(im, true), rw = rankOf(wt, true), out = [];
      for (i = 0; i < I.length; i++) {
        var rk = [rs[i], rv[i], rd[i], rw[i]], full = rk.every(function (x) { return x !== undefined; });
        out.push({i: i, icb: I[i], share: sh[i], sd: sd[i], imd: im[i], wait: wt[i], rs: rs[i], rv: rv[i], rd: rd[i], rw: rw[i],
                  avg: full ? (rk[0] + rk[1] + rk[2] + rk[3]) / 4 : null});
      }
      return out;
    }
    function f1(x, d) { return x === null || x === undefined ? NV : x.toFixed(d); }
    function cell(v, r, d, suffix) { return v === null || v === undefined ? '<td class="sp-num">' + NV + '</td>' : '<td class="sp-num">' + v.toFixed(d) + (suffix || '') + ' <span class="ex-rk">#' + r + '</span></td>'; }
    function draw() {
      var R = rows(), key = S.sort, h, k;
      var cmp = {avg: function (a, b) { return a.avg - b.avg; }, name: function (a, b) { return a.icb.name < b.icb.name ? -1 : 1; },
                 share: function (a, b) { return a.share - b.share; }, sd: function (a, b) { return b.sd - a.sd; },
                 imd: function (a, b) { return b.imd - a.imd; }, wait: function (a, b) { return b.wait - a.wait; }}[key];
      R.sort(function (a, b) {
        var va = key === 'name' ? 0 : a[key], vb = key === 'name' ? 0 : b[key];
        if (key !== 'name' && (va === null || va === undefined)) { return 1; }
        if (key !== 'name' && (vb === null || vb === undefined)) { return -1; }
        return cmp(a, b);
      });
      h = '<div class="ex"><h3>ICB opportunity: where to start</h3><p class="ms-sub">All ' + C.icbs.length + ' ICBs side by side. Each column is ranked across the ICBs (#1 = most room to grow, or most need). Click a heading to sort, a row to see its dermatology waiting-time trend.</p>';
      h += '<div class="ex-ctl"><div><label for="opp-brand">Brand</label><select id="opp-brand">';
      for (k = 0; k < C.brands.length; k++) { h += '<option' + (C.brands[k] === S.brand ? ' selected' : '') + '>' + esc(C.brands[k]) + '</option>'; }
      h += '</select></div></div>';
      function th(id, t) { return '<th class="sp-num"><button type="button" class="ex-sort" data-sort="' + id + '" aria-pressed="' + (S.sort === id ? 'true' : 'false') + '">' + t + '</button></th>'; }
      h += '<div class="sp-scroll"><table class="sp-tbl ex-opp"><tr><th><button type="button" class="ex-sort" data-sort="name" aria-pressed="' + (S.sort === 'name' ? 'true' : 'false') + '">ICB</button></th>' +
           th('avg', 'Average rank') + th('share', S.brand + ' share of emollient items') + th('sd', 'Spread between PCNs (percentage points)') +
           th('imd', 'Deprivation (IMD score)') + th('wait', 'Dermatology median wait (weeks)') + '</tr>';
      for (k = 0; k < R.length; k++) {
        var r = R[k], b = r.icb.brands[S.brand];
        h += '<tr class="ex-row" data-i="' + r.i + '" tabindex="0"' + (S.sel === r.i ? ' aria-selected="true"' : '') + '><td>' + esc(r.icb.name.replace(/^NHS /, '')) + '</td>' +
             '<td class="sp-num">' + (r.avg === null ? NV : r.avg.toFixed(1)) + '</td>' +
             cell(r.share, r.rs, 2, '%') + cell(r.sd, r.rv, 2, '') + cell(r.imd, r.rd, 1, '') + cell(r.wait, r.rw, 1, '') + '</tr>';
      }
      h += '</table></div>';
      h += '<p class="ex-note"><b>How to read the order.</b> The average rank is an ordering aid, not a score: a simple average of four ranks, each 1 to ' + C.icbs.length + ', where #1 is the lowest ' + esc(S.brand) + ' share, the widest spread between PCNs, the highest deprivation and the longest dermatology wait. It treats the four as equally important, which they are not for every brand, so sort by the column that matters to you. An ICB missing any of the four has no average rank.</p>';
      h += '<div id="opp-detail">' + detail() + '</div>';
      h += '<details><summary>Sources, periods and definitions</summary><p class="ex-src"><b>Brand share and spread between PCNs.</b> ' + esc(C.sources.items.name) + ', items, ' + esc(month(C.periods.items[0])) + ' to ' + esc(month(C.periods.items[1])) + '. ' + esc(C.sources.items.measure) + ' ' + esc(C.sources.items.attribution) + '</p>' +
           '<p class="ex-src"><b>Deprivation.</b> ' + esc(C.sources.imd.name) + '. ' + esc(C.sources.imd.measure) + ' ' + esc(C.sources.imd.method) + ' ' + esc(C.sources.imd.licence) + '.</p>' +
           '<p class="ex-src"><b>Dermatology waiting time.</b> ' + esc(C.sources.rtt.name) + ', ' + esc(month(RP[LAST])) + ', treatment function code ' + esc(C.sources.rtt.treatmentFunctionCode) + ' (' + esc(C.sources.rtt.treatmentFunction) + '), ' + esc(C.sources.rtt.basis) + '. ' + esc(C.sources.rtt.measure) + ' ' + esc(C.sources.rtt.licence) + '.</p></details></div>';
      mount.innerHTML = h;
      var bs = mount.querySelectorAll('.ex-sort'), j;
      for (j = 0; j < bs.length; j++) { bs[j].addEventListener('click', function () { S.sort = this.getAttribute('data-sort'); draw(); }); }
      var br = mount.querySelectorAll('.ex-row');
      function pickRow() { S.sel = parseInt(this.getAttribute('data-i'), 10); draw(); }
      for (j = 0; j < br.length; j++) {
        br[j].addEventListener('click', pickRow);
        br[j].addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pickRow.call(this); } });
      }
      document.getElementById('opp-brand').addEventListener('change', function () { S.brand = this.value; draw(); });
    }
    function detail() {
      if (S.sel === null) { return '<p class="ex-src">Select an ICB row to see its dermatology waiting-time trend against England.</p>'; }
      var ic = C.icbs[S.sel], t = ic.rtt, E = C.england;
      if (!t) { return '<p><span class="nv">' + NV + '</span>: no dermatology waiting-time series for ' + esc(ic.name) + '.</p>'; }
      var src = 'Source: NHS England RTT, incomplete pathways by commissioner, treatment function ' + esc(C.sources.rtt.treatmentFunctionCode) + ' (' + esc(C.sources.rtt.treatmentFunction) + '), ' + esc(month(RP[0])) + ' to ' + esc(month(RP[LAST])) + '. Open Government Licence v3.0.';
      var note = ic.rttFirstMonth !== RP[0] ? '<p class="ex-note">' + esc(ic.name) + ' was formed in April 2026, so NHS England publishes no figure for it before ' + esc(month(ic.rttFirstMonth)) + '. Earlier months are left blank, not borrowed from the ICBs it replaced.</p>' : '';
      return '<h4>' + esc(ic.name) + '</h4>' + note +
        exChart(RP, [{name: ic.name.replace(/^NHS /, ''), color: '#14304F', vals: t.median}, {name: 'England', color: '#A8842C', dash: '6 4', vals: E.median}],
                {title: 'Dermatology median wait, weeks (incomplete pathways)', label: 'Dermatology median wait in weeks by month, ' + ic.name + ' against England', zero: false, nullText: NV,
                 tick: function (v, rg) { return v.toFixed(rg < 5 ? 1 : 0); }, fmt: function (v) { return v.toFixed(1) + ' weeks'; }, src: src}) +
        exChart(RP, [{name: ic.name.replace(/^NHS /, ''), color: '#14304F', vals: t.w18pct}, {name: 'England', color: '#A8842C', dash: '6 4', vals: E.w18pct}],
                {title: 'Share of dermatology pathways waiting under 18 weeks', label: 'Share waiting under 18 weeks by month, ' + ic.name + ' against England', zero: false, nullText: NV,
                 tick: function (v) { return v.toFixed(0) + '%'; }, fmt: function (v) { return v.toFixed(1) + '%'; }, src: src}) +
        '<p class="ex-src">' + n(t.total[LAST]) + ' patients on the dermatology waiting list in ' + esc(month(RP[LAST])) + ', of whom ' + n(t.w52[LAST]) + ' had waited 52 weeks or more. Deprivation: ' + (ic.imd ? 'IMD score ' + ic.imd.score.toFixed(1) + ', rank ' + ic.imd.rank + ' of ' + C.icbs.length + ' (1 = most deprived), ' + ic.imd.prop10.toFixed(1) + '% of neighbourhoods in the most deprived 10% nationally' : NV) + '.</p>';
    }
    draw();
  }

  function shTick(v, range) { return v.toFixed(range < 1 ? 2 : (range < 10 ? 1 : 0)) + '%'; }

  function exStart(mount, T) {
    var P = T.periods, N = P.length, LAST = N - 1, floor = T.minBaselineItems || 25;
    var brandIdx = {}, i;
    for (i = 0; i < T.brands.length; i++) { brandIdx[T.brands[i].name] = i; }
    var byId = {};
    for (i = 0; i < T.products.length; i++) { byId[T.products[i].id] = T.products[i]; }
    var forms = {};
    for (i = 0; i < T.products.length; i++) { if (T.products[i].form !== 'unspecified') { forms[T.products[i].form] = (forms[T.products[i].form] || 0) + T.products[i].n.slice(-12).reduce(function (a, b) { return a + b; }, 0); } }
    var formList = Object.keys(forms).sort(function (a, b) { return forms[b] - forms[a]; }).slice(0, 4);
    function pick(name) { return brandIdx.hasOwnProperty(name) ? name : T.brands[0].name; }
    var defaultSkus = ['QV cream', 'QV Intensive ointment', 'Cetraben cream', 'Cetraben ointment', 'Epimax original cream', 'Hydromol ointment'];
    var S = {tab: 'brand', scope: 'ALL', brand: pick('QV'), a: pick('QV'), b: pick('Cetraben'), icb: T.icbs[0].code, pbrand: pick('QV'), pcn: null,
             sku: [], skuMeasure: 'share', forms: []};
    for (i = 0; i < T.products.length && S.sku.length < 6; i++) { if (defaultSkus.indexOf(T.products[i].label) >= 0) { S.sku.push(T.products[i].id); } }
    var pcnCache = {};

    function zeros() { var z = []; for (var k = 0; k < N; k++) { z.push(0); } return z; }
    function scopeName() { if (S.scope === 'ALL') { return 'England'; } for (var k = 0; k < T.icbs.length; k++) { if (T.icbs[k].code === S.scope) { return T.icbs[k].name; } } return S.scope; }
    function totalS(scope) { return scope === 'ALL' ? T.total : (T.icbTotal[scope] || zeros()); }
    function prodS(p, scope) { return scope === 'ALL' ? p.n : (p.icb[scope] || zeros()); }
    function sum(arrs) { var o = zeros(); for (var a = 0; a < arrs.length; a++) { for (var k = 0; k < N; k++) { o[k] += arrs[a][k]; } } return o; }
    function brandS(name, scope) {
      var bi = brandIdx[name], l = [];
      for (var k = 0; k < T.products.length; k++) { if (T.products[k].b === bi) { l.push(prodS(T.products[k], scope)); } }
      return sum(l);
    }
    function formS(f, scope) { var l = []; for (var k = 0; k < T.products.length; k++) { if (T.products[k].form === f) { l.push(prodS(T.products[k], scope)); } } return sum(l); }
    function share(a, t) { var o = []; for (var k = 0; k < N; k++) { o.push(t[k] > 0 ? a[k] * 100 / t[k] : null); } return o; }
    function idx(a) { var o = []; for (var k = 0; k < N; k++) { o.push(a[0] >= floor ? a[k] * 100 / a[0] : null); } return o; }
    function tot12(a) { var s2 = 0; for (var k = N - 12; k < N; k++) { s2 += a[k]; } return s2; }
    function yoy(a) { return a[0] >= floor ? Math.round((a[LAST] - a[0]) * 1000 / a[0]) / 10 : null; }
    function pc(v) { return v === null ? 'no items' : v.toFixed(1) + '%'; }
    function opt(sel, items, labelFn) {
      var o = '';
      for (var k = 0; k < items.length; k++) { o += '<option value="' + esc(items[k].v) + '"' + (items[k].v === sel ? ' selected' : '') + '>' + esc(items[k].l) + '</option>'; }
      return o;
    }
    function brandOpts(sel) {
      var l = [];
      for (var k = 0; k < T.brands.length; k++) { l.push({v: T.brands[k].name, l: T.brands[k].name + (T.brands[k].generic ? ' (generic)' : '')}); }
      return opt(sel, l);
    }
    function scopeCtl() {
      var l = [{v: 'ALL', l: 'England (national)'}];
      for (var k = 0; k < T.icbs.length; k++) { l.push({v: T.icbs[k].code, l: T.icbs[k].name}); }
      return '<div><label for="ex-scope">Where</label><select id="ex-scope">' + opt(S.scope, l) + '</select></div>';
    }
    var win = month(P[0]) + ' to ' + month(P[LAST]);
    function src(extra) {
      return 'Source: ' + esc(T.source) + ' (NHSBSA), BNF ' + esc(T.bnf.join(' and ')) + ' emollients, GP-prescribed items dispensed in the community, ' + esc(S.scope === 'ALL' ? 'England' : scopeName()) + ', ' + esc(win) + '. Share is share of items, not company share. ' + (extra || '');
    }

    function tiles(list) {
      var h = '<div class="sp-tiles">';
      for (var k = 0; k < list.length; k++) { h += '<div class="sp-tile"><b>' + list[k][0] + '</b><span>' + esc(list[k][1]) + '</span></div>'; }
      return h + '</div>';
    }

    function viewBrand() {
      var sc = S.scope, tot = totalS(sc), b = brandS(S.brand, sc), sh = share(b, tot);
      var nat = share(brandS(S.brand, 'ALL'), T.total);
      var h = '<div class="ex-ctl">' + scopeCtl() + '<div><label for="ex-brand">Brand</label><select id="ex-brand">' + brandOpts(S.brand) + '</select></div></div>';
      var yShare = sh[0] !== null && b[0] >= floor ? Math.round((sh[LAST] - sh[0]) * 10) / 10 : null;
      h += tiles([
        [pc(sh[LAST]), 'Share of items, ' + month(P[LAST])],
        [pc(tot12(tot) > 0 ? tot12(b) * 100 / tot12(tot) : null), 'Share of items, 12 months'],
        [yShare === null ? 'too few to trend' : (yShare > 0 ? '+' : '') + yShare.toFixed(1) + ' pts', 'Share change vs ' + month(P[0])],
        [pct(yoy(b)), 'Brand items vs ' + month(P[0])],
        [pct(yoy(tot)), 'Whole market items vs ' + month(P[0])]]);
      var ser = [{name: S.brand + ', ' + (sc === 'ALL' ? 'England' : scopeName()), color: EX_COL[0], vals: sh}];
      if (sc !== 'ALL') { ser.push({name: S.brand + ', England', color: EX_COL[4], dash: '6 4', vals: nat}); }
      h += exChart(P, ser, {title: S.brand + ': share of emollient items, month by month', label: S.brand + ' share of emollient items by month', zero: false, tick: shTick, fmt: pc, src: src()});
      h += exChart(P, [{name: S.brand + ' items', color: EX_COL[0], vals: idx(b)}, {name: 'All emollient items (the market)', color: EX_COL[1], vals: idx(tot)}],
                   {title: S.brand + ' against the market: items indexed to ' + month(P[0]) + ' = 100', label: S.brand + ' items against the market, indexed', zero: false, tick: function (v) { return Math.round(v); }, fmt: function (v) { return v.toFixed(1); },
                    src: src('An index of 110 is 10% more items than in ' + month(P[0]) + '. An index is shown only where that month had at least ' + floor + ' items.')});
      /* every brand in this scope */
      var rows = [];
      for (var k = 0; k < T.brands.length; k++) {
        var bs = brandS(T.brands[k].name, sc), t12 = tot12(tot);
        if (tot12(bs) > 0) { rows.push({n: T.brands[k].name, g: T.brands[k].generic, l: share(bs, tot)[LAST], f: share(bs, tot)[0], y: t12 > 0 ? tot12(bs) * 100 / t12 : null, ok: bs[0] >= floor}); }
      }
      rows.sort(function (x, y) { return y.y - x.y; });
      h += '<div class="ex-chart"><h4>Brand shares in ' + esc(scopeName()) + '</h4><div class="sp-scroll"><table class="sp-tbl"><tr><th>Brand</th><th class="sp-num">' + esc(month(P[LAST])) + '</th><th class="sp-num">12 months</th><th class="sp-num">' + esc(month(P[0])) + '</th><th class="sp-num">Change</th></tr>';
      for (k = 0; k < Math.min(15, rows.length); k++) {
        var r = rows[k], ch = r.ok && r.l !== null && r.f !== null ? r.l - r.f : null;
        h += '<tr><td>' + esc(r.n) + (r.g ? ' <span class="sp-chip">generic</span>' : '') + '</td><td class="sp-num">' + pc(r.l) + '</td><td class="sp-num">' + pc(r.y) + '</td><td class="sp-num">' + pc(r.f) + '</td><td class="sp-num">' + (ch === null ? 'too few to trend' : (ch > 0 ? '+' : '') + ch.toFixed(1) + ' pts') + '</td></tr>';
      }
      h += '</table></div><p class="ex-src">' + src('Top 15 of ' + rows.length + ' brands by 12-month items.') + '</p></div>';
      return h;
    }

    function skuLabel(p) { return p.label; }
    function viewSku() {
      var sc = S.scope, tot = totalS(sc), k, ser = [], ids = S.sku, fl = S.forms;
      var top = T.products.slice(0, 14);
      var h = '<div class="ex-ctl">' + scopeCtl() + '<div><label for="ex-meas">Measure</label><select id="ex-meas">' + opt(S.skuMeasure, [{v: 'share', l: 'Share of market items'}, {v: 'items', l: 'Items per month'}, {v: 'index', l: 'Index: ' + month(P[0]) + ' = 100 (shows movement)'}]) + '</select></div></div>';
      h += '<p class="ms-sub">Pick up to eight presentations. A presentation is one NHSBSA product line, so QV cream and QV Intensive ointment are separate lines. The form is read from the product name; where the name gives none it is not guessed.</p><div class="ex-checks">';
      var shown = {};
      for (k = 0; k < top.length; k++) { shown[top[k].id] = 1; }
      for (k = 0; k < ids.length; k++) { if (!shown[ids[k]] && byId[ids[k]]) { top.push(byId[ids[k]]); shown[ids[k]] = 1; } }
      for (k = 0; k < top.length; k++) {
        h += '<label><input type="checkbox" data-sku="' + esc(top[k].id) + '"' + (ids.indexOf(top[k].id) >= 0 ? ' checked' : '') + '> ' + esc(skuLabel(top[k])) + '</label>';
      }
      for (k = 0; k < formList.length; k++) {
        h += '<label><input type="checkbox" data-form="' + esc(formList[k]) + '"' + (fl.indexOf(formList[k]) >= 0 ? ' checked' : '') + '> All ' + esc(formList[k]) + 's, whole market</label>';
      }
      h += '</div><div class="ex-ctl"><div><label for="ex-addsku">Add another presentation</label><select id="ex-addsku"><option value="">Choose&hellip;</option>';
      for (k = 0; k < T.products.length; k++) { if (!shown[T.products[k].id]) { h += '<option value="' + esc(T.products[k].id) + '">' + esc(T.products[k].label) + '</option>'; } }
      h += '</select></div></div>';
      var rows = [];
      for (k = 0; k < ids.length; k++) { if (byId[ids[k]]) { rows.push({name: byId[ids[k]].label, vals: prodS(byId[ids[k]], sc)}); } }
      for (k = 0; k < fl.length; k++) { rows.push({name: 'All ' + fl[k] + 's (market)', vals: formS(fl[k], sc), dash: '6 4'}); }
      if (!rows.length) { return h + '<div class="empty-state">Tick at least one presentation.</div>'; }
      for (k = 0; k < rows.length; k++) {
        ser.push({name: rows[k].name, color: EX_COL[k % EX_COL.length], dash: rows[k].dash, vals: S.skuMeasure === 'share' ? share(rows[k].vals, tot) : S.skuMeasure === 'index' ? idx(rows[k].vals) : rows[k].vals});
      }
      var isShare = S.skuMeasure === 'share', isIdx = S.skuMeasure === 'index';
      h += exChart(P, ser, {title: isShare ? 'Presentations: share of all emollient items, month by month' : isIdx ? 'Presentations: items indexed to ' + month(P[0]) + ' = 100' : 'Presentations: items per month', label: 'Presentation level trend', zero: isShare || isIdx ? false : true, tick: isShare ? shTick : isIdx ? function (v) { return Math.round(v); } : function (v) { return Math.round(v).toLocaleString('en-GB'); }, fmt: isShare ? pc : isIdx ? function (v) { return v.toFixed(1); } : n, src: src('Dashed lines are every presentation of that form across all brands.' + (isIdx ? ' An index is shown only where ' + month(P[0]) + ' had at least ' + floor + ' items.' : ''))});
      h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>Presentation</th><th class="sp-num">Items ' + esc(month(P[LAST])) + '</th><th class="sp-num">Share ' + esc(month(P[LAST])) + '</th><th class="sp-num">Share 12 months</th><th class="sp-num">Items vs ' + esc(month(P[0])) + '</th></tr>';
      for (k = 0; k < rows.length; k++) {
        var v = rows[k].vals;
        h += '<tr><td>' + esc(rows[k].name) + '</td><td class="sp-num">' + n(v[LAST]) + '</td><td class="sp-num">' + pc(share(v, tot)[LAST]) + '</td><td class="sp-num">' + pc(tot12(tot) > 0 ? tot12(v) * 100 / tot12(tot) : null) + '</td><td class="sp-num">' + pct(yoy(v)) + '</td></tr>';
      }
      return h + '</table></div>';
    }

    function viewCompare() {
      var sc = S.scope, tot = totalS(sc), A = brandS(S.a, sc), B = brandS(S.b, sc);
      var h = '<div class="ex-ctl">' + scopeCtl() + '<div><label for="ex-a">Brand A</label><select id="ex-a">' + brandOpts(S.a) + '</select></div><div><label for="ex-b">Compare with</label><select id="ex-b">' + brandOpts(S.b) + '</select></div></div>';
      h += exChart(P, [{name: S.a, color: EX_COL[0], vals: share(A, tot)}, {name: S.b, color: EX_COL[1], vals: share(B, tot)}],
                   {title: S.a + ' against ' + S.b + ': share of emollient items, month by month', label: S.a + ' against ' + S.b, zero: false, tick: shTick, fmt: pc, src: src()});
      h += exChart(P, [{name: S.a, color: EX_COL[0], vals: idx(A)}, {name: S.b, color: EX_COL[1], vals: idx(B)}, {name: 'The market', color: EX_COL[4], dash: '6 4', vals: idx(tot)}],
                   {title: 'Growth against the market: items indexed to ' + month(P[0]) + ' = 100', label: 'Indexed items', zero: false, tick: function (v) { return Math.round(v); }, fmt: function (v) { return v.toFixed(1); }, src: src('Shown only where ' + month(P[0]) + ' had at least ' + floor + ' items.')});
      function row(nm, a, c) { return '<tr><td>' + esc(nm) + '</td><td class="sp-num">' + a + '</td><td class="sp-num">' + c + '</td></tr>'; }
      var sa = share(A, tot), sb = share(B, tot), t12 = tot12(tot);
      h += '<div class="sp-scroll"><table class="sp-tbl"><tr><th>' + esc(scopeName()) + '</th><th class="sp-num">' + esc(S.a) + '</th><th class="sp-num">' + esc(S.b) + '</th></tr>' +
           row('Items, ' + month(P[LAST]), n(A[LAST]), n(B[LAST])) +
           row('Share of items, ' + month(P[LAST]), pc(sa[LAST]), pc(sb[LAST])) +
           row('Share of items, 12 months', pc(t12 > 0 ? tot12(A) * 100 / t12 : null), pc(t12 > 0 ? tot12(B) * 100 / t12 : null)) +
           row('Share of items, ' + month(P[0]), pc(sa[0]), pc(sb[0])) +
           row('Items vs ' + month(P[0]), pct(yoy(A)), pct(yoy(B))) + '</table></div>';
      return h;
    }

    function viewVar() {
      var h = '<div class="ex-ctl"><div><label for="ex-icb">ICB</label><select id="ex-icb">' + opt(S.icb, T.icbs.map(function (x) { return {v: x.code, l: x.name}; })) + '</select></div>' +
              '<div><label for="ex-pb">Brand</label><select id="ex-pb">' + brandOpts(S.pbrand) + '</select></div></div><div id="ex-var"><div class="empty-state">Loading practice data&hellip;</div></div>';
      return h;
    }

    function drawVar(doc) {
      var out = document.getElementById('ex-var');
      if (!out) { return; }
      var bi = doc.brands.indexOf(S.pbrand), M = T.pcn, h = '';
      var pb = S.pbrand;
      if (bi < 0) {
        out.innerHTML = '<div class="empty-state">' + esc(pb) + ' is not one of the ' + (doc.brands.length - 1) + ' largest brands carried at practice level, so no PCN view is built for it. Pick another brand.</div>';
        return;
      }
      var pc2 = doc.pcns, i2, all = 0, br = 0;
      for (i2 = 0; i2 < pc2.length; i2++) { all += pc2[i2].t; br += pc2[i2].b[bi]; }
      var shares = [];
      for (i2 = 0; i2 < pc2.length; i2++) { if (pc2[i2].id !== 'none' && pc2[i2].t >= doc.pcnFloor) { shares.push(pc2[i2].b[bi] * 100 / pc2[i2].t); } }
      var max = shares.length ? Math.max.apply(null, shares) : 0, min = shares.length ? Math.min.apply(null, shares) : 0;
      h += tiles([[all ? (br * 100 / all).toFixed(1) + '%' : 'no items', pb + ' share across the whole ICB, ' + month(doc.window[0]) + ' to ' + month(doc.window[1])],
                  [shares.length ? min.toFixed(1) + '% to ' + max.toFixed(1) + '%' : 'not enough', 'Lowest to highest PCN (' + shares.length + ' PCNs with at least ' + n(doc.pcnFloor) + ' items)'],
                  [n(all), 'Emollient items in the ICB, 12 months']]);
      h += '<div class="ex-scale"><span>0%</span><i></i><span>' + max.toFixed(1) + '% of the PCN\'s emollient items (the highest here)</span></div><div class="ex-heat" id="ex-heat">';
      for (i2 = 0; i2 < pc2.length; i2++) {
        var p = pc2[i2];
        if (p.id === 'none') { continue; }
        if (p.t < doc.pcnFloor) {
          h += '<div class="ex-tile ex-low" role="group" aria-label="' + esc(p.name) + ': too few items"><span>' + esc(p.name) + '</span><span>Too few items to show a share (' + n(p.t) + ')</span></div>';
          continue;
        }
        var s2 = p.b[bi] * 100 / p.t, f = max ? s2 / max : 0, bg = mix(f), tx = f > 0.5 ? '#FFFFFF' : '#0B1C33';
        h += '<button type="button" class="ex-tile" data-pcn="' + esc(p.id) + '" aria-pressed="' + (S.pcn === p.id ? 'true' : 'false') + '" style="background:' + bg + ';color:' + tx + '"><span>' + esc(p.name) + '</span><b>' + s2.toFixed(1) + '%</b><span>' + n(p.b[bi]) + ' of ' + n(p.t) + ' items</span></button>';
      }
      h += '</div>';
      var none = null;
      for (i2 = 0; i2 < pc2.length; i2++) { if (pc2[i2].id === 'none') { none = pc2[i2]; } }
      if (none) { h += '<p class="ex-src">' + n(none.t) + ' items in this ICB come from practices ODS does not place in a PCN, so they are in the ICB total above but in no tile.</p>'; }
      var sel = null;
      for (i2 = 0; i2 < pc2.length; i2++) { if (pc2[i2].id === S.pcn) { sel = pc2[i2]; } }
      if (sel) {
        h += '<h4 style="margin:14px 0 6px;color:var(--navy);font-size:14px;">Practices in ' + esc(sel.name) + '</h4><div class="sp-scroll"><table class="sp-tbl"><tr><th>Practice</th><th class="sp-num">Emollient items</th><th class="sp-num">' + esc(pb) + ' items</th><th class="sp-num">' + esc(pb) + ' share</th></tr>';
        for (i2 = 0; i2 < sel.p.length; i2++) {
          var q = sel.p[i2];
          h += '<tr><td>' + esc(q.n) + ' <span class="sp-chip">' + esc(q.c) + '</span></td><td class="sp-num">' + n(q.t) + '</td><td class="sp-num">' + n(q.b[bi]) + '</td><td class="sp-num">' + (q.t >= doc.practiceFloor ? (q.b[bi] * 100 / q.t).toFixed(1) + '%' : 'too few') + '</td></tr>';
        }
        h += '</table></div>';
      } else {
        h += '<p class="ms-sub">Select a PCN tile to see its practices.</p>';
      }
      h += '<div class="ex-note">A PCN is a group of neighbouring GP practices. ' + esc(M.membershipCaveat) + ' ' + n(M.itemsNotPlacedInAnIcb) + ' of ' + n(M.itemsAtPracticeLevel) + ' practice-level items (' + (M.itemsNotPlacedInAnIcb * 100 / M.itemsAtPracticeLevel).toFixed(2) + '%) come from practices that were not open in ' + month(M.window[1]) + ' and so sit in no ICB here; they are in the national totals on the other tabs.</div>';
      h += '<p class="ex-src">Source: NHSBSA English Prescribing Dataset with SNOMED code, practice level (BNF ' + esc(T.bnf.join(' and ')) + ', items, ' + esc(month(doc.window[0])) + ' to ' + esc(month(doc.window[1])) + '). PCN membership: ' + esc(M.membershipSource) + '. A PCN with fewer than ' + n(doc.pcnFloor) + ' emollient items in the 12 months, or a practice with fewer than ' + n(doc.practiceFloor) + ', shows no share. Share is share of the PCN\'s or practice\'s own emollient items.</p>';
      out.innerHTML = h;
      var tl = out.querySelectorAll('.ex-tile[data-pcn]');
      for (var z = 0; z < tl.length; z++) {
        tl[z].addEventListener('click', function () { S.pcn = this.getAttribute('data-pcn'); drawVar(doc); });
      }
    }
    function mix(f) {
      var a = [234, 240, 247], b = [20, 48, 79], o = [];
      for (var c = 0; c < 3; c++) { o.push(Math.round(a[c] + (b[c] - a[c]) * f)); }
      return 'rgb(' + o.join(',') + ')';
    }
    function loadVar() {
      var code = S.icb;
      if (pcnCache[code]) { drawVar(pcnCache[code]); return; }
      fetch(EXPL + 'pcn/' + code + '.json?cb=' + new Date().toISOString().slice(0, 13))
        .then(function (r) { if (!r.ok) { throw new Error('HTTP ' + r.status); } return r.json(); })
        .then(function (d) { pcnCache[code] = d; if (S.icb === code && S.tab === 'var') { drawVar(d); } })
        .catch(function (e) { var o = document.getElementById('ex-var'); if (o) { o.innerHTML = '<div class="empty-state">Practice data for this ICB could not load (' + esc(e.message) + ').</div>'; } });
    }

    function draw() {
      var tabs = [['brand', 'Brand trend'], ['sku', 'Presentations'], ['cmp', 'Compare two brands'], ['var', 'PCN variation within an ICB']];
      var h = '<div class="ex"><h3>Prescribing explorer: month by month</h3><p class="ms-sub">Thirteen months of NHSBSA items for the same emollient codes as the cards above, ' + esc(win) + '. Pick England or any ICB; every line is counted, none is estimated.</p><div class="ex-tabs" role="group" aria-label="Explorer view">';
      for (var k = 0; k < tabs.length; k++) { h += '<button type="button" data-tab="' + tabs[k][0] + '" aria-pressed="' + (S.tab === tabs[k][0] ? 'true' : 'false') + '">' + tabs[k][1] + '</button>'; }
      h += '</div><div id="ex-body">' + (S.tab === 'brand' ? viewBrand() : S.tab === 'sku' ? viewSku() : S.tab === 'cmp' ? viewCompare() : viewVar()) + '</div><p class="ex-src">' + esc(T.attribution || '') + '</p></div>';
      mount.innerHTML = h;
      wire();
      if (S.tab === 'var') { loadVar(); }
    }
    function on(id, fn) { var el = document.getElementById(id); if (el) { el.addEventListener('change', function () { fn(el.value); draw(); }); } }
    function wire() {
      var bt = mount.querySelectorAll('.ex-tabs button');
      for (var k = 0; k < bt.length; k++) { bt[k].addEventListener('click', function () { S.tab = this.getAttribute('data-tab'); draw(); }); }
      on('ex-scope', function (v) { S.scope = v; });
      on('ex-brand', function (v) { S.brand = v; });
      on('ex-a', function (v) { S.a = v; });
      on('ex-b', function (v) { S.b = v; });
      on('ex-meas', function (v) { S.skuMeasure = v; });
      on('ex-icb', function (v) { S.icb = v; S.pcn = null; });
      on('ex-pb', function (v) { S.pbrand = v; });
      on('ex-addsku', function (v) { if (v && S.sku.length < 8) { S.sku.push(v); } });
      var cs = mount.querySelectorAll('input[data-sku]');
      for (k = 0; k < cs.length; k++) {
        cs[k].addEventListener('change', function () {
          var id = this.getAttribute('data-sku'), at = S.sku.indexOf(id);
          if (this.checked && S.sku.length + S.forms.length < 8) { S.sku.push(id); } else if (!this.checked && at >= 0) { S.sku.splice(at, 1); }
          draw();
        });
      }
      var cf = mount.querySelectorAll('input[data-form]');
      for (k = 0; k < cf.length; k++) {
        cf[k].addEventListener('change', function () {
          var f = this.getAttribute('data-form'), at = S.forms.indexOf(f);
          if (this.checked && S.sku.length + S.forms.length < 8) { S.forms.push(f); } else if (!this.checked && at >= 0) { S.forms.splice(at, 1); }
          draw();
        });
      }
    }
    draw();
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
      if (FW) { renderFrameworks(d); addCalendarAndPins(d); }
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
