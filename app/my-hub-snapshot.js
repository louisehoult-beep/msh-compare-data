/* My Hub snapshot (22/10/2026): the top of My Hub for a member's chosen
   specialities. Customer feedback (Aneeka Hussain, Ego Pharmaceuticals,
   dermatology): My Hub should be a personal dashboard so she never has to go
   searching, and the full Hub overwhelms. So this is four short cards, each
   with a link that goes deeper; the longer desk sits under "More".

     Key news          top three stories for the specialities
     Market snapshot   latest GP prescribing headline per defined market
     Coming up         next three dated items
     ICB changes       structure facts and recent changes, relevant ones first

   DATA, read-only, files the Hub already publishes, every card names its source:
     data/speciality-news/<id>.json    via MSH_MYHUB.feeds.FEED (already loaded)
     data/hub-calendar.json            via MSH_MYHUB.feeds.FEED
     data/speciality-panels/<slug>.json  gpPrescribing (NHSBSA EPD)
     data/icb-watch.json
   A file that fails to load shows an honest "unavailable", never old copy. No
   speciality picked shows one prompt. Pinned panels stay in their own block.

   Registers MSH_MYHUB.snapshot = { load, html }. Loaded by app/my-hub.js. */
(function () {
  'use strict';
  var M = window.MSH_MYHUB;
  if (!M) { return; }
  var L = window.MSH_MYHUB_LOGIC;

  var NEWS_N = 3, CAL_N = 3, ICB_N = 3, ICB_DAYS = 120, EVENT_DAYS = 90, SPEC_MAX = 3;
  var PANELS = {};          // slug -> panels json | false (failed) | null (loading)
  var ICB = null;           // null loading, false failed, else icb-watch json
  var asked = false;

  function esc(s) { return M.esc(s); }
  function raw(path) {
    return fetch(M.base + path, { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error(path + ' ' + r.status); } return r.json(); });
  }
  function repaint() { var el = document.getElementById('mx-snap'); if (el) { el.innerHTML = html(); } }
  function specs() { return M.specIds().map(function (id) { return M.byId[id]; }); }
  function nf(x) { return Number(x).toLocaleString('en-GB'); }
  function pct(x) { return x === null || x === undefined ? 'too few to trend' : (x > 0 ? '+' : '') + Number(x).toFixed(1) + '%'; }
  function feed() { return M.feeds ? M.feeds.FEED : { news: null, cal: null }; }

  function load() {
    specs().slice(0, SPEC_MAX).forEach(function (s) {
      if (PANELS[s.id] === undefined) {
        PANELS[s.id] = null;
        raw('data/speciality-panels/' + encodeURIComponent(s.id) + '.json').then(function (d) { PANELS[s.id] = d; }, function () { PANELS[s.id] = false; }).then(repaint);
      }
    });
    if (!asked) {
      asked = true;
      raw('data/icb-watch.json').then(function (d) { ICB = d; }, function () { ICB = false; }).then(repaint);
    }
  }

  function skel() { return '<ul><li class="mx-sk"><span class="sk w40"></span><span class="sk w90"></span></li></ul>'; }
  function card(cls, icon, title, body, href, label, src) {
    return '<section class="card panel snap ' + cls + '" aria-label="' + esc(title) + '"><div class="ph"><span class="pi">' + M.svg(icon) + '</span><h3>' + esc(title) + '</h3></div>'
      + body + (src ? '<p class="note">' + src + '</p>' : '')
      + '<a class="foot" href="' + esc(href) + '">' + esc(label) + M.svg('right') + '</a></section>';
  }
  function emptyIn(what) { return '<p class="empty">' + esc(what) + '</p>'; }

  function newsCard() {
    var f = feed().news, body;
    if (f === null) { body = skel(); }
    else if (f === false) { body = emptyIn('News is unavailable just now.'); }
    else {
      var list = L.newsList(f, M.mine(), true, NEWS_N, new Date().toISOString()).slice(0, NEWS_N);
      body = list.length ? '<ul class="snap-l">' + list.map(function (g) {
        var st = L.newsStamp(g.it.published, M.today);
        return '<li><a href="' + esc(L.safeUrl(g.it.link)) + '" target="_blank" rel="noopener"><b>' + esc(g.it.title) + '</b></a><small>'
          + esc([M.byId[g.spec].label, g.it.source, st.label].filter(Boolean).join(', ')) + '</small></li>';
      }).join('') + '</ul>' : emptyIn('No news for your specialities in the last 60 days.');
    }
    return card('k-news', 'news', 'Key news', body, '/medical-sales-hub/news/', 'All news');
  }

  function marketCard() {
    var rows = '', ready = true, notes = [], src = null, shownSpecs = specs().slice(0, SPEC_MAX);
    shownSpecs.forEach(function (s) {
      var p = PANELS[s.id];
      if (p === null || p === undefined) { ready = false; return; }
      var h = p ? L.marketHeadlines(p) : false;
      if (h === false) { notes.push(s.label + ': prescribing data unavailable just now.'); return; }
      if (!h) { notes.push('No prescribing market is defined for ' + s.label + ' yet.'); return; }
      src = src || h;
      h.markets.forEach(function (m) {
        rows += '<li><b>' + (shownSpecs.length > 1 ? esc(s.label) + ': ' : '') + esc(m.short) + '</b>'
          + '<span class="snap-fig">' + nf(m.items) + ' items, £' + nf(m.cost) + '</span>'
          + '<small>' + esc(m.period) + ', ' + esc(pct(m.itemsYoY)) + ' items against a year earlier'
          + (m.lead ? '. Leading product ' + esc(m.lead.label) + (m.lead.share === null ? '' : ', ' + Number(m.lead.share).toFixed(1) + '% of items') : '') + '</small></li>';
      });
    });
    var body = !ready ? skel() : (rows ? '<ul class="snap-l">' + rows + '</ul>' : '')
      + notes.map(function (n) { return '<p class="empty">' + esc(n) + '</p>'; }).join('');
    if (ready) { if (!rows) { if (!notes.length) { body = emptyIn('No prescribing figures for your specialities.'); } } }
    var note = src ? 'GP practice prescribing in England, per month. Data: <a href="' + esc(src.sourceUrl) + '" target="_blank" rel="noopener">NHSBSA English Prescribing Dataset</a>. '
      + esc(src.attribution) : '';
    var first = shownSpecs[0];
    return card('k-mkt', 'bar-chart', 'Market snapshot', body, first ? first.url : '/medical-sales-hub/', first ? 'Open the ' + first.label + ' page' : 'Open the Hub', ready ? note : '');
  }

  function calCard() {
    var f = feed().cal, body;
    if (f === null) { body = skel(); }
    else if (f === false) { body = emptyIn('The Calendar is unavailable just now.'); }
    else {
      var list = L.eventsList(f, M.mine(), true, M.today, EVENT_DAYS).slice(0, CAL_N);
      body = list.length ? '<ul class="snap-l">' + list.map(function (e) {
        var when = e.endDate ? L.fmtDate(e.date) + ' to ' + L.fmtDate(e.endDate) : L.fmtDate(e.date);
        var a = e.source ? '<a href="' + esc(L.safeUrl(e.source)) + '" target="_blank" rel="noopener"><b>' + esc(e.title) + '</b></a>' : '<b>' + esc(e.title) + '</b>';
        return '<li>' + a + '<small>' + esc([when, e.location].filter(Boolean).join(', ')) + '</small></li>';
      }).join('') + '</ul>' : emptyIn('Nothing dated for your specialities in the next ' + EVENT_DAYS + ' days.');
    }
    return card('k-cal', 'cal', 'Coming up', body, '/medical-sales-hub/calendar/', 'The Calendar');
  }

  function icbCard() {
    var body, src = '';
    if (ICB === null) { body = skel(); }
    else if (ICB === false) { body = emptyIn('ICB changes are unavailable just now.'); }
    else {
      var c = L.icbChanges(ICB, specs(), M.today, ICB_DAYS);
      if (!c) { body = emptyIn('ICB changes are unavailable just now.'); }
      else {
        body = '<p class="snap-fact"><b>' + (c.count === null ? '' : c.count + ' ICBs') + '</b>'
          + (c.abolished ? ', ' + c.abolished + ' abolished' + (c.lastAbolished ? ' (last legal end ' + esc(L.fmtDate(c.lastAbolished)) + ')' : '') : '')
          + (c.clusters ? ', ' + c.clusters + ' clusters sharing leadership' : '') + '.</p>';
        var ev = c.events.slice(0, ICB_N);
        body += ev.length ? '<ul class="snap-l">' + ev.map(function (e) {
          var u = e.sources[0] ? L.safeUrl(e.sources[0]) : '';
          return '<li>' + (u ? '<a href="' + esc(u) + '" target="_blank" rel="noopener"><b>' + esc(e.headline) + '</b></a>' : '<b>' + esc(e.headline) + '</b>')
            + '<small>' + esc(L.fmtDate(e.date)) + (e.relevant ? ', names your speciality' : '') + '</small></li>';
        }).join('') + '</ul>' : emptyIn('No ICB change recorded in the last ' + ICB_DAYS + ' days.');
        src = 'NHS structure is national, so the facts apply to every speciality. Changes are marked when their own text names your speciality. Checked ' + esc(c.asOf) + '. Source: NHS Organisation Data Service and each ICB’s own pages.';
      }
    }
    return card('k-icb', 'network', 'ICB changes', body, '/medical-sales-hub/nhs-structure-map/', 'NHS structure map', src);
  }

  function html() {
    var s = specs();
    if (!s.length) {
      return '<section class="snap-empty card" aria-label="Your snapshot"><h2>Your snapshot</h2><p>Pick your specialities and this page shows their news, prescribing figures, dates and ICB changes in one place.</p>'
        + '<button type="button" class="btn navy" data-open="m-spec" data-k="snap-pick">Pick your specialities</button></section>';
    }
    return '<div class="sec-h"><h2 id="mx-sn-t">Your snapshot</h2><span class="n">' + esc(M.L.joinNames(s.map(function (x) { return x.label; }))) + '</span></div>'
      + '<div class="snap-grid">' + newsCard() + marketCard() + calCard() + icbCard() + '</div>';
  }

  M.snapshot = { load: load, html: html };
})();
