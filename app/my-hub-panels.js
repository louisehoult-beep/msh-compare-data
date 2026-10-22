/* My Hub pinned panels (2026-10-22): the panels a member starred on a
   speciality page (app/speciality-panels.js), drawn on their own My Hub.
   A pin is a saved item of kind "panel" (app/hub-account.js), so each member
   has their own set. Pure helpers are in app/hub-panels.js.

   DATA, read-only, only for the panels pinned:
     data/speciality-panels/<slug>.json   GP prescribing markets
     data/hub-calendar.json               dates (the same file the Calendar uses)
   A file that fails to load shows an honest "could not load" and a link to the
   page, never old copy. Unpin is the existing data-unstar action in my-hub.js.

   Registers MSH_MYHUB.panels = { load, html }. Loaded by app/my-hub.js. */
(function () {
  'use strict';
  var M = window.MSH_MYHUB;
  if (!M) { return; }
  var P = window.MSH_PANELS;

  var CAL_SHOWN = 6;
  var SPEC = {};      // slug -> panels json | false
  var CAL = null;     // null loading/not asked, false failed, else entries
  var asked = { cal: false };

  function esc(s) { return M.esc(s); }
  function raw(path) {
    return fetch(M.base + path, { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error(path + ' ' + r.status); } return r.json(); });
  }
  function repaint() { var el = document.getElementById('mx-panels'); if (el) { el.innerHTML = html(); } }
  function pins() { return P.pinnedPanels((M.acct && M.acct.state && M.acct.state.stars) || []); }
  function nameOf(slug) { var it = M.byId[slug]; return it ? it.label : slug; }
  function nf(x) { return Number(x).toLocaleString('en-GB'); }
  function pct(x) { return x === null || x === undefined ? 'too few to trend' : (x > 0 ? '+' : '') + x.toFixed(1) + '%'; }

  function load() {
    pins().forEach(function (s) {
      var k = P.parsePanelKey(s.u);
      if (k.kind === 'gp') {
        if (SPEC[k.slug] === undefined) {
          SPEC[k.slug] = null;
          raw('data/speciality-panels/' + encodeURIComponent(k.slug) + '.json').then(function (d) { SPEC[k.slug] = d; }, function () { SPEC[k.slug] = false; }).then(repaint);
        }
      } else if (k.kind === 'calendar' && !asked.cal) {
        asked.cal = true;
        raw('data/hub-calendar.json').then(function (d) { CAL = (d && d.entries) || []; }, function () { CAL = false; }).then(repaint);
      }
    });
  }

  function card(s, title, sub, body, link) {
    return '<section class="card panel mx-pinned" aria-label="' + esc(title) + '"><div class="ph"><span class="pi">' + M.svg('star') + '</span><h3>' + esc(title) + '</h3>'
      + '<button type="button" class="star" aria-pressed="true" data-unstar="' + esc(s.u) + '" aria-label="Unpin ' + esc(title) + ' from My Hub">' + M.svg('star') + '</button></div>'
      + (sub ? '<p class="note">' + esc(sub) + '</p>' : '') + body
      + '<a class="foot" href="' + esc(M.L.safeUrl(link)) + '">Open on ' + esc(nameOf(P.parsePanelKey(s.u).slug)) + ' page' + M.svg('right') + '</a></section>';
  }
  function gpCard(s, k) {
    var d = SPEC[k.slug], page = k.page;
    var title = nameOf(k.slug) + ': GP prescribing';
    if (d === null || d === undefined) { return card(s, title, '', '<ul><li class="mx-sk"><span class="sk w40"></span><span class="sk w90"></span></li></ul>', page); }
    var g = d ? P.gpSummary(d, k.id) : null;
    if (!g) { return card(s, title, '', '<p class="empty">This panel could not load, or is no longer on the page. Open the page to see it.</p>', page); }
    var rows = g.top.map(function (t) {
      return '<tr><td>' + esc(t.label) + '</td><td class="num">' + (t.share === null || t.share === undefined ? '' : t.share.toFixed(1) + '%') + '</td><td class="num">' + pct(t.yoy) + '</td></tr>';
    }).join('');
    return card(s, nameOf(k.slug) + ': ' + g.label, g.period + '. ' + nf(g.items) + ' items, £' + nf(g.cost) + ' actual cost, ' + pct(g.itemsYoY) + ' items against a year earlier.',
      '<div class="mx-scroll"><table class="mx-tbl"><tr><th>Leading products</th><th class="num">Share</th><th class="num">vs a year earlier</th></tr>' + rows + '</table></div>'
      + '<p class="note">Share is product share of items, not company share. ' + esc(g.attribution) + '</p>', page);
  }
  function calCard(s, k) {
    var title = nameOf(k.slug) + ' calendar';
    if (CAL === null) { return card(s, title, '', '<ul><li class="mx-sk"><span class="sk w40"></span><span class="sk w90"></span></li></ul>', k.page); }
    if (CAL === false) { return card(s, title, '', '<p class="empty">The Calendar is unavailable just now.</p>', k.page); }
    var rows = P.calendarRows(CAL, k.slug, M.today);
    if (!rows.length) { return card(s, title, '', '<p class="empty">No dated event is recorded for this speciality. Nothing is estimated from a previous year.</p>', k.page); }
    var body = '<ul>' + rows.slice(0, CAL_SHOWN).map(function (e) {
      return '<li class="mx-calrow"><span class="d">' + esc(P.fmtDate(e.date)) + '</span><span><a href="' + esc(M.L.safeUrl(e.source)) + '" target="_blank" rel="noopener"><b>' + esc(e.title) + '</b></a>'
        + '<small>' + esc(P.typeLabel(e)) + (e.location ? ', ' + esc(e.location) : '') + '</small></span>'
        + '<button type="button" class="more" data-ics="' + esc(e.id) + '" data-ics-slug="' + esc(k.slug) + '" data-k="ics-' + esc(e.id) + '" aria-label="Add ' + esc(e.title) + ' to my calendar">Add</button></li>';
    }).join('') + '</ul>'
      + '<button type="button" class="btn navy mx-full" data-ics="all" data-ics-slug="' + esc(k.slug) + '" data-k="ics-all-' + esc(k.slug) + '">Add all ' + rows.length + ' to my calendar</button>';
    return card(s, title, rows.length > CAL_SHOWN ? 'Next ' + CAL_SHOWN + ' of ' + rows.length + '. Add all for the full list.' : '', body, k.page);
  }

  function html() {
    var list = pins();
    if (!list.length) { return ''; }
    var h = '<div class="sec-h"><h2 id="mx-pn-t">Pinned from your specialities</h2><span class="n">' + list.length + (list.length === 1 ? ' panel' : ' panels') + '</span></div><div class="mx-pinned-grid">';
    list.forEach(function (s) {
      var k = P.parsePanelKey(s.u);
      h += k.kind === 'gp' ? gpCard(s, k) : calCard(s, k);
    });
    return h + '</div>';
  }

  /* Add to my calendar, from a pinned calendar card. */
  function wire() {
    M.mount.addEventListener('click', function (e) {
      var t = e.target.closest ? e.target.closest('[data-ics]') : null;
      if (!t || !CAL) { return; }
      var slug = t.getAttribute('data-ics-slug'), id = t.getAttribute('data-ics');
      var rows = P.calendarRows(CAL, slug, M.today);
      if (id !== 'all') { rows = rows.filter(function (r) { return r.id === id; }); }
      if (!rows.length) { return; }
      var blob = new Blob([P.ics(rows, slug, nameOf(slug) + ' (Medical Sales Hub)', new Date().toISOString())], { type: 'text/calendar;charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = P.icsName(slug, id === 'all' ? '' : id);
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      M.toast(id === 'all' ? 'Calendar file downloaded.' : 'Added. Open the file to save it.');
    });
  }
  wire();

  M.panels = { load: load, html: html };
})();
