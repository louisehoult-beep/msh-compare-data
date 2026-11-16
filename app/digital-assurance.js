/* Medical Sales Hub, Digital supplier assurance (/medical-sales-hub/digital-assurance/).
   Mounts on #msh-digital-assurance.

   WHAT IT IS. The digital answer to the physical Hub's suspended-lines list. There is no
   digital equivalent of a suspended catalogue line, because a digital product is bought
   through a framework lot under an assurance regime and not as a stock code. What can be
   given is the same SHAPE: something a trust's information governance team can block a
   purchase on, who in the same area is current, and the question the member can ask
   without making a claim of their own.

   WHERE THE FIGURES COME FROM. data/digital-assurance.json, built by
   scripts/build_digital_assurance.py from the Data Security and Protection Toolkit (DSPT)
   reading in data/dspt-supplier-check.json, the specialities in data/supplier-seed.json
   and the routes to market in data/digital-frameworks.json. Nothing is computed here: the
   page renders the file, and anything the file lacks prints as "Not verified"
   (HUB-VERIFICATION-STANDARD), never filled in.

   THE RULES ARE PRINTED, NOT HIDDEN. The toolkit year rolls in June, so the cut between
   current and behind is a judgement with a date on it. yearRule, claimRule, matchRule and
   unmatchedRule come out of the data file and are shown on the page in full, the way
   laneRule and clinicalRule are shown on the digital lane. A supplier that is behind is
   never called unsafe, non-compliant or barred, and a supplier that is current is never
   called endorsed. */
(function () {
  var MOUNT = document.getElementById('msh-digital-assurance');
  if (!MOUNT) return;

  var NAVY = '#0B1C33', DEEP = '#14304F', WINE = '#4A1526', GOLD = '#A8842C',
      GOLDL = '#E0BE8E', INK = '#1D2733', WARM = '#EDE7DC', PALE = '#F5F1E8';
  var SRC = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/digital-assurance.json';
  var CB = '?cb=' + new Date().toISOString().slice(0, 10);
  var NV = 'Not verified';

  var CSS = '.dga{font:16px/1.6 Georgia,serif;color:' + INK + '}.dga *{box-sizing:border-box}'
    + '.msh.alignfull,.msh-dga.alignfull{max-width:none!important}'
    + '.dga .band{padding:30px 0}.dga .dark{background:' + NAVY + ';color:' + PALE + '}'
    + '.dga .wine{background:' + WINE + ';color:' + PALE + '}.dga .warm{background:' + WARM + '}'
    + '.dga .col{max-width:none;margin:0;padding:0 40px}@media(max-width:600px){.dga .col{padding:0 20px}}'
    + '.dga h1,.dga h2{font-family:Didot,"Bodoni 72",Georgia,serif;margin:0 0 12px}'
    + '.dga h1{font-size:34px;line-height:1.2}.dga h2{font-size:25px;color:' + NAVY + '}'
    + '.dga h3{font:700 16px Helvetica,Arial,sans-serif;color:' + NAVY + ';margin:18px 0 6px}'
    /* The BAND runs full width with 40px margins (Lou, 16/11/2026); the running
       TEXT inside it does not. A 1,345px line of prose is unreadable, so prose
       keeps a measure and the tables, card grid and name list do not. */
    + '.dga p{margin:0 0 12px;max-width:820px}.dga .rule p{max-width:none}'
    + '.dga .dark h1,.dga .dark h2,.dga .dark h3,.dga .dark p,.dga .dark li,.dga .dark td,.dga .dark th,.dga .dark span,.dga .dark strong{color:' + PALE + '}'
    + '.dga .wine h2,.dga .wine h3,.dga .wine p,.dga .wine li,.dga .wine td,.dga .wine th,.dga .wine span,.dga .wine strong{color:' + PALE + '}'
    + 'body .wp-site-blocks .dga .dark h1,body .wp-site-blocks .dga .dark h2,body .wp-site-blocks .dga .dark h3,body .wp-site-blocks .dga .dark p,body .wp-site-blocks .dga .dark li,body .wp-site-blocks .dga .dark span,body .wp-site-blocks .dga .dark strong{color:' + PALE + '!important}'
    + 'body .wp-site-blocks .dga .wine h2,body .wp-site-blocks .dga .wine h3,body .wp-site-blocks .dga .wine p,body .wp-site-blocks .dga .wine li,body .wp-site-blocks .dga .wine span,body .wp-site-blocks .dga .wine strong{color:' + PALE + '!important}'
    + 'body .wp-site-blocks .dga .dark .eyebrow,body .wp-site-blocks .dga .wine .eyebrow{color:' + GOLDL + '!important}'
    + '.dga .eyebrow{font:700 12px/1 Helvetica,Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:' + NAVY + ';margin-bottom:10px}'
    + '.dga .dark .eyebrow,.dga .wine .eyebrow{color:' + GOLDL + '}'
    + '.dga .lede{font-size:18px;line-height:1.6;max-width:880px}'
    + '.dga .kpis{display:flex;flex-wrap:wrap;gap:16px;margin:18px 0 4px}'
    + '.dga .kpi{border-left:4px solid ' + GOLD + ';padding:4px 14px;min-width:160px}'
    + '.dga .kpi b{display:block;font:700 30px Georgia,serif;color:' + NAVY + '}'
    + '.dga .dark .kpi b,.dga .wine .kpi b{color:' + GOLDL + '}'
    + '.dga .kpi span{font:12px/1.4 Helvetica,Arial,sans-serif;display:block}'
    + '.dga .rule{border-left:4px solid ' + GOLD + ';background:#fff;padding:14px 18px;margin:14px 0}'
    + '.dga .rule p:last-child{margin-bottom:0}'
    + '.dga .rule .lbl{font:700 12px Helvetica,Arial,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:' + NAVY + ';display:block;margin-bottom:4px}'
    + '.dga .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px;margin:18px 0}'
    + '.dga .card{background:#fff;border-top:4px solid ' + GOLD + ';padding:16px 18px}'
    + '.dga .card.np{border-top-color:' + WINE + '}.dga .card.amb{border-top-color:' + DEEP + '}'
    + '.dga .card h3{margin-top:0;font-size:18px}'
    + '.dga .card dl{margin:0;font:14px/1.55 Helvetica,Arial,sans-serif}'
    + '.dga .card dt{font-weight:700;color:' + NAVY + ';margin-top:10px}.dga .card dd{margin:2px 0 0}'
    + '.dga .tag{display:inline-block;font:700 11px/1 Helvetica,Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;padding:5px 8px;border:1px solid ' + GOLD + ';color:' + NAVY + ';margin:0 6px 6px 0}'
    + '.dga .tag.bad{background:' + WINE + ';border-color:' + WINE + ';color:#fff}'
    + '.dga .tag.ok{background:' + DEEP + ';border-color:' + DEEP + ';color:#fff}'
    + '.dga table{border-collapse:collapse;width:100%;font:14px/1.5 Helvetica,Arial,sans-serif}'
    + '.dga th,.dga td{padding:8px 10px;border-bottom:1px solid #d8d2c4;text-align:left;vertical-align:top}'
    + '.dga th{background:' + DEEP + ';color:#fff;font-weight:700}'
    + '.dga .sort th{cursor:pointer}.dga .sort th:after{content:" \\2195";opacity:.45}'
    /* The zebra stripe must follow the BAND, not the table. A white wash on a
       wine band produced a pale row carrying pale text, which is rule 9's
       contrast failure in one line; on a dark band the stripe is a lift, not a
       wash. */
    + '.dga tbody tr:nth-child(even){background:rgba(255,255,255,.55)}'
    + '.dga .dark tbody tr:nth-child(even),.dga .wine tbody tr:nth-child(even){background:rgba(255,255,255,.07)}'
    + '.dga .dark th,.dga .wine th{background:rgba(0,0,0,.28);border-bottom:2px solid ' + GOLDL + '}'
    + '.dga .dark td,.dga .wine td{border-bottom-color:rgba(255,255,255,.22)}'
    + '.dga .scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}'
    + '.dga .nv{color:#7A1F1F;font-weight:700}.dga .dark .nv,.dga .wine .nv{color:' + GOLDL + '}'
    + '.dga .note{font:13px/1.6 Helvetica,Arial,sans-serif;color:#39424d}'
    + '.dga .dark .note,.dga .wine .note{color:' + GOLDL + '}'
    + '.dga .names{font:14px/1.9 Helvetica,Arial,sans-serif;columns:3;column-gap:28px}'
    + '@media(max-width:900px){.dga .names{columns:2}}@media(max-width:600px){.dga .names{columns:1}}'
    + '.dga .names span{display:block;break-inside:avoid}'
    + '.dga a{color:' + NAVY + ';text-decoration:underline}.dga .dark a,.dga .wine a{color:' + GOLDL + '}'
    + '.dga .filt{font:15px Helvetica,Arial,sans-serif;padding:9px 10px;border:1px solid ' + GOLD + ';color:' + INK + ';background:#fff;max-width:100%;width:340px}'
    + '.dga label{font:700 12px Helvetica,Arial,sans-serif;display:block;margin:0 0 5px}'
    + '@media print{.dga .filt{display:none}.dga .dark,.dga .wine{-webkit-print-color-adjust:exact;print-color-adjust:exact}}';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function nv(v) { return v == null || v === '' ? '<span class="nv">' + NV + '</span>' : esc(v); }
  function n(x) { return Number(x || 0).toLocaleString('en-GB'); }

  /* An ISO date to the way Lou writes one. Anything that is not a plain
     YYYY-MM-DD is handed back untouched rather than guessed at. */
  function uk(iso) {
    if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso || null;
    var p = iso.split('-');
    return p[2] + '/' + p[1] + '/' + p[0];
  }

  function band(cls, inner) { return '<div class="band ' + cls + '"><div class="col">' + inner + '</div></div>'; }

  function shell(inner) { return '<style>' + CSS + '</style><div class="dga">' + inner + '</div>'; }

  MOUNT.innerHTML = shell(band('dark', '<p class="lede">Loading the digital supplier assurance check…</p>'));

  fetch(SRC + CB, { cache: 'no-cache' })
    .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(render)
    .catch(function (e) {
      MOUNT.innerHTML = shell(band('dark',
        '<h1>Digital supplier assurance</h1><p class="lede">This check could not be loaded just now ('
        + esc(e.message) + '). That is a loading problem, not missing data. Refresh to try again.</p>'));
    });

  /* The alternative side of a flagged row. A narrow sub-area with no current
     peer says so in those words: the file holds no like-for-like swap and the
     page must not reach for a supplier from a different area to fill the gap. */
  function altBlock(row) {
    var alts = row.alternatives || [], out = [], narrowEmpty = [];
    for (var i = 0; i < alts.length; i++) {
      var a = alts[i];
      if (a.current && a.current.length) {
        out.push('<dd>' + esc(a.speciality) + ' — ' + n(a.current.length)
          + ' tracked supplier' + (a.current.length === 1 ? '' : 's') + ' with a current publication: '
          + esc(a.current.slice(0, 8).join(', '))
          + (a.current.length > 8 ? ', and ' + n(a.current.length - 8) + ' more in the table below' : '') + '.</dd>');
      } else if (a.narrow) {
        narrowEmpty.push(a.speciality);
      }
    }
    if (narrowEmpty.length) {
      out.push('<dd class="note">No other tracked supplier in ' + esc(narrowEmpty.join(' or '))
        + ' holds a Data Security and Protection Toolkit record at all, so there is no like-for-like'
        + ' swap to name. The comparison above is at the lane level.</dd>');
    }
    if (!out.length) out.push('<dd><span class="nv">' + NV + '</span></dd>');
    return out.join('');
  }

  function card(row) {
    var cls = row.kind === 'notPublished' ? ' np' : (row.kind === 'ambiguous' ? ' amb' : '');
    var tag = row.kind === 'behind'
      ? '<span class="tag bad">Behind the toolkit year</span>'
      : (row.kind === 'notPublished'
        ? '<span class="tag bad">Registered, not published</span>'
        : '<span class="tag">Two records, no single status</span>');
    var h = '<div class="card' + cls + '"><h3>' + esc(row.name) + '</h3>' + tag + '<dl>';
    h += '<dt>What the toolkit publishes</dt>';
    if (row.kind === 'ambiguous') {
      var cf = row.conflicting || [];
      for (var i = 0; i < cf.length; i++) {
        h += '<dd>' + nv(cf[i].dsptName) + ' — ' + nv(cf[i].dsptStatus)
          + (cf[i].statusDate ? ', published ' + esc(cf[i].statusDate) : '') + '</dd>';
      }
      if (!cf.length) h += '<dd><span class="nv">' + NV + '</span></dd>';
    } else {
      h += '<dd>' + nv(row.dsptStatus) + '</dd>';
      h += '<dd class="note">Published ' + nv(row.statusDate)
        + (row.matchedOn ? '. Matched on the name “' + esc(row.matchedOn) + '”' : '')
        + (row.odsCode ? ', organisation code ' + esc(row.odsCode) : '') + '.</dd>';
    }
    if (row.areas && row.areas.length) {
      h += '<dt>Area</dt><dd>' + esc(row.areas.join(', ')) + '</dd>';
    }
    h += '<dt>Who is current in the same area</dt>' + altBlock(row);
    if (row.routes && row.routes.length) {
      var rs = row.routes.map(function (r) {
        return esc(r.name) + (r.ends ? ' (closes ' + esc(uk(r.ends)) + ')' : '');
      });
      h += '<dt>Route to market</dt><dd>' + rs.join('; ') + '</dd>';
    }
    h += '<dt>The question to ask</dt><dd>' + nv(row.question) + '</dd>';
    return h + '</dl></div>';
  }

  function statusCell(row) {
    if (row.kind === 'current') return '<span class="tag ok">Current</span>';
    if (row.kind === 'behind') return '<span class="tag bad">Behind</span>';
    if (row.kind === 'notPublished') return '<span class="tag bad">Not published</span>';
    if (row.kind === 'ambiguous') return '<span class="tag">Ambiguous</span>';
    return '<span class="tag">No status</span>';
  }

  /* Sort key per column. The toolkit year sorts by year then version, so
     "2024-25 (version 7)" sits below "2025-26 (version 8)" instead of sorting
     as the text it happens to be. */
  function keyOf(row, i) {
    if (i === 1) return (row.yearLabel || '') + '|' + ('0' + (row.version || 0)).slice(-2);
    if (i === 2) return (row.outcome || '').toLowerCase();
    if (i === 3) return (row.areas || []).join(', ').toLowerCase();
    if (i === 4) return (row.routes || []).length;
    return row.name.toLowerCase();
  }

  function render(D) {
    var c = D.counts || {}, S = D.suppliers || [];
    var flagged = S.filter(function (r) { return r.kind === 'behind'; });
    var notPub = S.filter(function (r) { return r.kind === 'notPublished' || r.kind === 'noStatus'; });
    var amb = S.filter(function (r) { return r.kind === 'ambiguous'; });
    var attention = flagged.concat(notPub).concat(amb);

    var h = '';

    /* 1. Masthead. */
    h += band('dark',
      '<p class="eyebrow">Medical Sales Intelligence Hub</p>'
      + '<h1>Digital supplier assurance</h1>'
      + '<p class="lede">Every digital and medical information technology (IT) supplier the Hub tracks, '
      + 'checked against the Data Security and Protection Toolkit (DSPT) — the assurance an NHS trust\'s '
      + 'information governance team looks at before a digital purchase goes through. '
      + n(c.behind || 0) + ' of the ' + n(c.tracked || 0) + ' suppliers tracked have let a whole toolkit '
      + 'year pass without publishing, ' + n(c.notPublished || 0) + ' hold a registration with nothing '
      + 'published against it, and ' + n(c.unmatched || 0) + ' cannot be found in the toolkit under any '
      + 'name held for them. Each one below comes with who is current in the same area and the question '
      + 'to ask — not a claim to make.</p>'
      + '<div class="kpis">'
      + '<div class="kpi"><b>' + n(c.tracked || 0) + '</b><span>Digital suppliers tracked</span></div>'
      + '<div class="kpi"><b>' + n(c.current || 0) + '</b><span>Current publication</span></div>'
      + '<div class="kpi"><b>' + n(c.behind || 0) + '</b><span>Behind the toolkit year</span></div>'
      + '<div class="kpi"><b>' + n(c.notPublished || 0) + '</b><span>Registered, not published</span></div>'
      + '<div class="kpi"><b>' + n(c.ambiguous || 0) + '</b><span>Two records, no single status</span></div>'
      + '<div class="kpi"><b>' + n(c.unmatched || 0) + '</b><span>No name match in the toolkit</span></div>'
      + '</div>'
      + '<p class="note">Toolkit read ' + nv(uk(D.dsptCheckedOn)) + '. Routes to market as at '
      + nv(uk(D.frameworksAsOf)) + '.</p>');

    /* 2. The rules, printed in full. */
    h += band('warm',
      '<p class="eyebrow">Read this before you use it</p><h2>The rules this page applies</h2>'
      + '<div class="rule"><span class="lbl">How the toolkit year is read</span><p>' + nv(D.yearRule) + '</p></div>'
      + '<div class="rule"><span class="lbl">What this is not</span><p>' + nv(D.claimRule) + '</p></div>'
      + '<div class="rule"><span class="lbl">How a supplier is matched to a toolkit record</span><p>'
      + nv(D.matchRule) + '</p></div>');

    /* 3. The suppliers a purchase can be held up on. */
    h += band('',
      '<p class="eyebrow">The equivalent of a suspended line</p>'
      + '<h2>' + n(attention.length) + ' suppliers a trust can hold a purchase up on</h2>'
      + '<p>There is no digital version of a suspended catalogue line: digital is bought through a '
      + 'framework lot under an assurance regime, not as a stock code, and nothing publishes that a '
      + 'software product has been withdrawn. This is the nearest real thing — the supplier\'s own '
      + 'published assurance, which an information governance team reads before it signs anything.</p>'
      + (attention.length ? '<div class="cards">' + attention.map(card).join('') + '</div>'
        : '<p>Every tracked supplier with a toolkit record has a current publication. Nothing to raise today.</p>'));

    /* 4. Routes closing. */
    var fws = (D.frameworks || []);
    h += band('wine',
      '<p class="eyebrow">The other way a route closes</p><h2>When each route to market ends</h2>'
      + '<p>A digital product is not withdrawn, but the agreement it is bought through does end. '
      + 'A successor is named below only where an agreement\'s own name carries the earlier one, which '
      + 'is the only case the data settles; two agreements that merely overlap in subject matter are '
      + 'not a succession and are not presented as one.</p>'
      + '<div class="scroll"><table><thead><tr><th>Agreement</th><th>Reference</th><th>Opened</th>'
      + '<th>Closes</th><th>Named successor</th><th>Tracked suppliers on it</th></tr></thead><tbody>'
      + fws.map(function (f) {
        return '<tr><td>' + (f.url ? '<a href="' + esc(f.url) + '" rel="nofollow noopener" target="_blank">'
          + esc(f.name) + '</a>' : esc(f.name)) + '</td>'
          + '<td>' + nv(f.reference) + '</td><td>' + nv(uk(f.starts)) + '</td><td>' + nv(uk(f.ends)) + '</td>'
          + '<td>' + (f.successor ? esc(f.successor.name) + ', opens ' + esc(uk(f.successor.starts))
            : '<span class="note">None named</span>') + '</td>'
          + '<td>' + (f.trackedSuppliers && f.trackedSuppliers.length
            ? n(f.trackedSuppliers.length) + ': ' + esc(f.trackedSuppliers.slice(0, 6).join(', '))
              + (f.trackedSuppliers.length > 6 ? ', and ' + n(f.trackedSuppliers.length - 6) + ' more' : '')
            : '<span class="note">No tracked supplier on the read list</span>') + '</td></tr>';
      }).join('')
      + '</tbody></table></div>'
      + '<p class="note">Nothing on this list closes inside twelve months, so it is a column beside the '
      + 'assurance check rather than a list of its own. A supplier count of none means no supplier the '
      + 'Hub tracks appeared on the supplier list read for that agreement, not that the agreement is '
      + 'empty. Source: ' + nv(D.frameworkSource) + '</p>');

    /* 5. Every tracked supplier with a record, filterable and sortable. */
    h += band('warm',
      '<p class="eyebrow">The whole list</p><h2>Every tracked supplier with a toolkit record</h2>'
      + '<p>' + n(S.length) + ' of the ' + n(c.tracked || 0) + ' digital suppliers the Hub tracks match a '
      + 'toolkit record on an exact name. Sort by any column; type to narrow the list.</p>'
      + '<label for="dga-f">Filter by supplier, area or toolkit year</label>'
      + '<input class="filt" id="dga-f" type="search" placeholder="e.g. Accurx, radiology, 2024-25" autocomplete="off">'
      + '<div class="scroll"><table id="dga-t"><thead><tr class="sort">'
      + '<th>Supplier</th><th>Toolkit year published</th><th>Outcome</th><th>Status</th><th>Area</th>'
      + '<th>Routes to market</th></tr></thead><tbody></tbody></table></div>'
      + '<p class="note" id="dga-n"></p>');

    /* 6. Unmatched. */
    h += band('',
      '<p class="eyebrow">Worth asking about, not asserting</p>'
      + '<h2>' + n((D.unmatched || []).length) + ' suppliers with no toolkit name match</h2>'
      + '<p>' + nv(D.unmatchedRule) + '</p>'
      + '<div class="names">' + (D.unmatched || []).map(function (u) {
        return '<span>' + esc(u) + '</span>';
      }).join('') + '</div>');

    /* 7. Provenance. */
    h += band('dark',
      '<p class="eyebrow">Where this comes from</p><h2>Source and date</h2>'
      + '<p>' + nv(D.source) + '. Read at <a href="' + esc(D.sourceUrl || '#')
      + '" rel="nofollow noopener" target="_blank">the toolkit\'s own organisation search</a> on '
      + nv(uk(D.dsptCheckedOn)) + '.</p>'
      + '<p class="note">' + nv(D.dsptNote) + '</p>');

    MOUNT.innerHTML = shell(h);
    wire(S);
  }

  /* The table's own behaviour. Built as rows rather than markup-in-a-string so a
     filter keystroke re-renders only the body. */
  function wire(S) {
    var tb = MOUNT.querySelector('#dga-t tbody'), f = MOUNT.querySelector('#dga-f'),
        note = MOUNT.querySelector('#dga-n');
    if (!tb) return;
    var col = 0, dir = 1, q = '';

    function rowHtml(r) {
      return '<tr><td>' + esc(r.name) + '</td>'
        + '<td>' + (r.yearLabel ? esc(r.yearLabel) + ' (version ' + esc(r.version) + ')'
          : '<span class="note">' + (r.kind === 'ambiguous' ? 'More than one record' : 'None published') + '</span>') + '</td>'
        + '<td>' + (r.outcome ? esc(r.outcome) : '<span class="note">—</span>') + '</td>'
        + '<td>' + statusCell(r) + '</td>'
        + '<td>' + (r.areas && r.areas.length ? esc(r.areas.join(', ')) : '<span class="note">Digital and medical IT</span>') + '</td>'
        + '<td>' + (r.routes && r.routes.length
          ? esc(r.routes.map(function (x) { return x.name; }).join('; '))
          : '<span class="note">None on the read lists</span>') + '</td></tr>';
    }

    function hay(r) {
      return (r.name + ' ' + (r.yearLabel || '') + ' ' + (r.outcome || '') + ' ' + r.kind + ' '
        + (r.areas || []).join(' ') + ' '
        + (r.routes || []).map(function (x) { return x.name; }).join(' ')).toLowerCase();
    }

    function draw() {
      var rows = S.filter(function (r) { return !q || hay(r).indexOf(q) > -1; });
      rows.sort(function (a, b) {
        var x = keyOf(a, col), y = keyOf(b, col);
        return (x < y ? -1 : x > y ? 1 : 0) * dir;
      });
      tb.innerHTML = rows.map(rowHtml).join('')
        || '<tr><td colspan="6">Nothing matches that. Clear the filter to see all ' + n(S.length) + '.</td></tr>';
      note.textContent = 'Showing ' + rows.length + ' of ' + S.length + ' suppliers with a toolkit record.';
    }

    var ths = MOUNT.querySelectorAll('#dga-t thead th');
    for (var i = 0; i < ths.length; i++) {
      (function (idx) {
        ths[idx].addEventListener('click', function () {
          // The Status column sorts on the same key as the toolkit year: the
          // status IS the year, read through the rule, so sorting them apart
          // would put "Behind" above and below "Current" in the same run.
          var k = idx === 3 ? 1 : idx;
          if (k === col) { dir = -dir; } else { col = k; dir = 1; }
          draw();
        });
      })(i);
    }
    if (f) {
      f.addEventListener('input', function () { q = f.value.trim().toLowerCase(); draw(); });
    }
    draw();
  }
})();
