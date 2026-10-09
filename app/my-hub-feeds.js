/* My Hub feeds: Key news and On the desk (Coming up, Safety alerts,
   Procurement deadlines, and Jobs when there are any), drawn in the approved
   mock-up's markup (2026-10). The rules for what shows are in
   app/my-hub-logic.js and have not changed since 24/09/2026.

   DATA, read-only, the same files the section pages use:
     data/speciality-news/<id>.json  news (one file per speciality)
     data/hub-calendar.json          events, awareness days, procurement dates
     data/mhra-alerts.json           device and patient safety alerts
   A feed that fails to load shows an honest empty panel, never stale copy.
   Safety alerts are never narrowed to the member's specialities: gov.uk tags
   them with its own specialism list, which does not map to Hub pages, and a
   guessed filter could hide a recall.

   Registers MSH_MYHUB.feeds = { load(), html() }. Loaded by app/my-hub.js. */
(function () {
  'use strict';
  var M = window.MSH_MYHUB;
  if (!M) { return; }
  var L = window.MSH_MYHUB_LOGIC;

  var NEWS_TOP = 9, PANEL_TOP = 4, EVENT_DAYS = 90, PROC_DAYS = 180, NEW_DAYS = 14, SOON_DAYS = 30;
  var PAGES = {
    news: '/medical-sales-hub/news/',
    calendar: '/medical-sales-hub/calendar/',
    mhra: '/medical-sales-hub/mhra-regulatory-desk/',
    procurement: '/medical-sales-hub/tender-history/',
    jobs: '/medical-sales-hub/clinical-jobs/'
  };
  var FEED = { news: null, cal: null, mhra: null };   // null = loading, false = failed
  var openRows = {}, openPanels = {};

  function esc(s) { return M.esc(s); }
  function svg(n) { return M.svg(n); }
  function nowIso() { return new Date().toISOString(); }
  function raw(path) {
    return fetch(M.base + path, { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error(path + ' ' + r.status); } return r.json(); });
  }

  function load() {
    if (FEED.news === null) {
      var ids = M.cat.items.filter(function (it) { return it.news; }).map(function (it) { return it.id; });
      var got = [], left = ids.length, ok = 0;
      if (!left) { FEED.news = []; }
      ids.forEach(function (id) {
        raw('data/speciality-news/' + encodeURIComponent(id) + '.json')
          .then(function (d) {
            ok++;
            ((d && d.items) || []).forEach(function (it) { if (it) { if (it.title) { if (/^https?:\/\/\S/i.test(String(it.link || ''))) { got.push({ it: it, spec: id }); } } } });
          })
          .catch(function () {})
          .then(function () {
            left--;
            if (left) { return; }
            FEED.news = ok ? L.dedupeNews(got, nowIso()) : false;
            M.paintFeeds();
          });
      });
    }
    if (FEED.cal === null) {
      raw('data/hub-calendar.json').then(function (d) { FEED.cal = (d && d.entries) || []; })
        .catch(function () { FEED.cal = false; }).then(M.paintFeeds);
    }
    if (FEED.mhra === null) {
      raw('data/mhra-alerts.json').then(function (d) {
        FEED.mhra = ((d && d.alerts) || []).slice().sort(function (a, b) { return String(b.issuedDate || '').localeCompare(String(a.issuedDate || '')); });
      }).catch(function () { FEED.mhra = false; }).then(M.paintFeeds);
    }
  }

  function news() { return L.newsList(FEED.news, M.mine(), M.narrowed(), NEWS_TOP, nowIso()); }
  function jobs() { return L.jobsList(FEED.news, M.mine(), M.narrowed()); }
  function events() { return L.eventsList(FEED.cal, M.mine(), M.narrowed(), M.today, EVENT_DAYS); }
  function procs() { return L.procList(FEED.cal, M.mine(), M.narrowed(), M.today, PROC_DAYS); }
  /* The same list with the speciality filter off, for an honest empty state. */
  function wholeHub(fn) {
    var keep = M.narrowed, l;
    M.narrowed = function () { return false; };
    try { l = fn(); } finally { M.narrowed = keep; }
    return l ? l.length : 0;
  }

  function emptyMine(what, all) {
    return '<p class="empty">Nothing ' + what + ' for your specialities. <button type="button" class="mx-link" data-scope="all" data-k="empty-all-' + what.replace(/\s+/g, '-') + '">Show everything' + (all ? ' (' + all + ')' : '') + '</button></p>';
  }
  function moreBtn(panel, total, shown, noun) {
    if (total <= shown) { return ''; }
    var open = !!openPanels[panel];
    return '<button type="button" class="more mx-more" data-more="' + panel + '" data-k="more-' + panel + '" aria-expanded="' + open + '">'
      + (open ? 'Show fewer' : 'Show all ' + total + ' ' + noun) + svg(open ? 'up' : 'down') + '</button>';
  }
  function skel(n) {
    var h = '';
    for (var i = 0; i !== n; i++) { h += '<li class="mx-sk"><span class="sk w40"></span><span class="sk w90"></span></li>'; }
    return h;
  }
  function links(list) {
    var seen = {};
    var h = list.filter(function (l) {
      if (!l) { return false; }
      if (!l.url) { return false; }
      var u = L.safeUrl(l.url);
      if (seen[u]) { return false; }
      seen[u] = 1; return true;
    }).map(function (l) {
      var u = L.safeUrl(l.url);
      var ext = /^https?:/.test(u) ? u.indexOf('medsalesintelligencehub.co.uk') === -1 : false;
      return '<a href="' + esc(u) + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + '>' + esc(l.label) + '</a>';
    }).join('');
    return h ? '<div class="lk">' + h + '</div>' : '';
  }
  function why(label, text) { return text ? '<p class="why"><b>' + esc(label) + '</b>' + esc(text) + '</p>' : ''; }

  /* ---------- Key news ---------- */
  function starBtn(it) {
    var on = M.A.isStarred(L.safeUrl(it.link));
    return '<button type="button" class="star" data-star="' + esc(L.safeUrl(it.link)) + '" data-star-t="' + esc(it.title) + '" aria-pressed="' + on + '" aria-label="' + (on ? 'Remove from Saved' : 'Save this story') + '">' + svg('star') + '</button>';
  }
  function keyNews() {
    var list = news(), n = M.specIds().length;
    var line = M.narrowed() ? 'From your ' + n + (n === 1 ? ' speciality' : ' specialities') : 'From every speciality';
    var h = '<section aria-labelledby="mx-kn-t"><div class="sec-h"><h2 id="mx-kn-t">Key news</h2><span class="n">' + esc(line) + '</span>'
      + '<a class="more" href="' + PAGES.news + '">All news' + svg('right') + '</a></div>';
    if (list === null) {
      return h + '<div class="card news" aria-busy="true"><div class="lead"><span class="sk dk w40"></span><span class="sk dk w90 h26"></span><span class="sk dk w60 h26"></span></div><ul class="nlist">' + skel(4) + '</ul></div></section>';
    }
    if (list === false) { return h + '<div class="card mx-pad"><p class="empty">News is unavailable just now.</p></div></section>'; }
    if (!list.length) {
      return h + '<div class="card mx-pad">' + (M.narrowed() ? emptyMine('new', wholeHub(news)) : '<p class="empty">No news in the last 60 days.</p>') + '</div></section>';
    }
    var lead = list[0], it = lead.it, sp = M.byId[lead.spec], st = L.newsStamp(it.published, M.today);
    h += '<div class="card news"><article class="lead"><span class="stag">' + esc(sp.label) + '</span>'
      + (it.opportunity ? '<span class="mx-opp">Opportunity</span>' : '')
      + '<h3><a href="' + esc(L.safeUrl(it.link)) + '" target="_blank" rel="noopener">' + esc(it.title) + '</a></h3>'
      + (it.summary ? '<p>' + esc(L.tidy(it.summary)) + '</p>' : '')
      + '<div class="row"><span class="time">' + esc([it.source, st.label].filter(Boolean).join(', ')) + '</span>' + starBtn(it)
      + '<a class="btn ghost" href="' + esc(L.safeUrl(it.link)) + '" target="_blank" rel="noopener">Read story</a></div></article>';
    var rest = list.slice(1, openPanels.news ? list.length : NEWS_TOP);
    h += '<ul class="nlist">' + rest.map(function (g) {
      var s = g.it, p = M.byId[g.spec], t = L.newsStamp(s.published, M.today);
      return '<li><div class="nrow"><div class="top"><span class="stag">' + esc(p.label) + '</span><time>' + esc(t.label) + '</time></div>' + starBtn(s)
        + '<a href="' + esc(L.safeUrl(s.link)) + '" target="_blank" rel="noopener"><h4>' + esc(s.title) + '</h4></a></div></li>';
    }).join('') + '</ul></div>';
    return h + moreBtn('news', list.length, NEWS_TOP, 'stories') + '</section>';
  }

  /* ---------- On the desk ---------- */
  function prow(key, lead, title, sub, detail) {
    var open = !!openRows[key];
    return '<li class="mx-pi' + (open ? ' open' : '') + '"><button type="button" class="prow" data-row="' + esc(key) + '" aria-expanded="' + open + '">'
      + lead + '<div><h4>' + esc(title) + '</h4><p>' + esc(sub) + '</p></div></button><div class="pdet">' + detail + '</div></li>';
  }
  /* Photo headers (approved mock-up v4): a navy-washed photo behind the panel title. */
  var PHOTO = {
    'mh-events': ['https://medsalesintelligencehub.co.uk/wp-content/uploads/2026/07/4-meeting-handshake.jpg', '110,50,12'],
    'mh-alerts': ['https://medsalesintelligencehub.co.uk/wp-content/uploads/2026/09/nbe-mhra-photo-web.jpg', '74,21,38'],
    'mh-proc': ['https://medsalesintelligencehub.co.uk/wp-content/uploads/2026/09/tender-history-masthead.jpg', '11,79,85']
  };
  function panel(id, glyph, title, note, href, hrefLabel, body, cls) {
    var ph = PHOTO[id];
    return '<div class="card panel' + (cls ? ' ' + cls : '') + (id === 'mh-proc' ? ' proc' : '') + (ph ? ' imgd' : '') + '" id="' + id + '"' + (ph ? ' style="--pimg:url(' + ph[0] + ');--pov:' + ph[1] + '"' : '') + '><div class="ph"><span class="pi">' + svg(id === 'mh-proc' ? 'file-badge' : glyph) + '</span><h3>' + title + '</h3></div>'
      + (note ? '<p class="note">' + note + '</p>' : '') + body + '<a class="foot" href="' + href + '">' + hrefLabel + svg('right') + '</a></div>';
  }
  function dateLead(e) {
    var d = L.parseDay(e.date);
    if (e.date < M.today) { return '<span class="date mx-now"><b>On</b><span>now</span></span>'; }
    return d ? '<span class="date"><b>' + L.pad(d.getDate()) + '</b><span>' + L.MONTHS[d.getMonth()] + '</span></span>' : '<span class="date"></span>';
  }
  function eventsPanel() {
    var list = events();
    var title = 'Coming up', foot = 'The Calendar';
    if (list === null) { return panel('mh-events', 'cal', title, '', PAGES.calendar, foot, '<ul>' + skel(3) + '</ul>'); }
    if (list === false) { return panel('mh-events', 'cal', title, '', PAGES.calendar, foot, '<p class="empty">The Calendar is unavailable just now.</p>'); }
    if (!list.length) { return panel('mh-events', 'cal', title, '', PAGES.calendar, foot, M.narrowed() ? emptyMine('coming up', wholeHub(events)) : '<p class="empty">Nothing in the next ' + EVENT_DAYS + ' days.</p>'); }
    var shown = openPanels.events ? list : list.slice(0, PANEL_TOP);
    var body = '<ul>' + shown.map(function (e) {
      var aw = e.type === 'awareness';
      var when = e.endDate ? L.fmtDate(e.date) + ' to ' + L.fmtDate(e.endDate) : L.fmtDate(e.date);
      var sub = (aw ? 'Awareness day' : 'Event') + (e.date < M.today ? ', ends ' + L.fmtShort(e.endDate) : ', ' + L.whenLabel(e.date, M.today).toLowerCase());
      var det = '<p>' + esc([when, e.location, e.audience].filter(Boolean).join(', ')) + '</p>' + why('Rep angle', e.repAction)
        + (e.note ? '<p>' + esc(e.note) + '</p>' : '') + links((e.links || []).concat(e.source ? [{ label: 'Organiser\u2019s page', url: e.source }] : []));
      return prow('e:' + e.id, dateLead(e), e.title, sub, det);
    }).join('') + '</ul>' + moreBtn('events', list.length, PANEL_TOP, 'events');
    return panel('mh-events', 'cal', title, '', PAGES.calendar, foot, body);
  }
  function alertsPanel() {
    var list = FEED.mhra;
    var note = 'All alerts, whatever you follow';
    if (list === null) { return panel('mh-alerts', 'alert', 'Safety alerts', note, PAGES.mhra, 'MHRA Regulatory Desk', '<ul>' + skel(3) + '</ul>', 'alerts'); }
    if (list === false) { return panel('mh-alerts', 'alert', 'Safety alerts', note, PAGES.mhra, 'MHRA Regulatory Desk', '<p class="empty">Safety alerts are unavailable just now.</p>', 'alerts'); }
    if (!list.length) { return panel('mh-alerts', 'alert', 'Safety alerts', note, PAGES.mhra, 'MHRA Regulatory Desk', '<p class="empty">No alerts in the current window.</p>', 'alerts'); }
    var shown = openPanels.alerts ? list : list.slice(0, PANEL_TOP);
    var body = '<ul>' + shown.map(function (a) {
      var nat = a.alertType === 'national-patient-safety';
      var n = L.daysFrom(a.issuedDate, M.today);
      var fresh = n !== null ? n >= -NEW_DAYS : false;
      var title = String(a.title || '').replace(/\s*\(?\b(DSI|NatPSA)\/[^\s)]*\)?\s*$/i, '');
      var sub = (fresh ? 'New. ' : '') + (nat ? 'Patient safety alert' : 'Device safety') + ', issued ' + L.fmtShort(a.issuedDate);
      var det = (a.description ? '<p>' + esc(a.description) + '</p>' : '') + why('For reps', a.play) + links([{ label: 'The alert on GOV.UK', url: a.url }]);
      return prow('a:' + (a.reference || a.url), '<span class="alv">' + svg('alert') + '</span>', title, sub, det);
    }).join('') + '</ul>' + moreBtn('alerts', list.length, PANEL_TOP, 'alerts');
    return panel('mh-alerts', 'alert', 'Safety alerts', note, PAGES.mhra, 'MHRA Regulatory Desk', body, 'alerts');
  }
  function countdown(s) {
    var n = L.daysFrom(s, M.today);
    if (n === null) { return '<span class="days"></span>'; }
    if (n === 0) { return '<span class="days soon"><b>0</b><span>today</span></span>'; }
    return '<span class="days' + (n <= SOON_DAYS ? ' soon' : '') + '"><b>' + n + '</b><span>' + (n === 1 ? 'day' : 'days') + '</span></span>';
  }
  function procPanel() {
    var list = procs();
    var title = 'Procurement deadlines', foot = 'Frameworks and tenders';
    if (list === null) { return panel('mh-proc', 'clip', title, '', PAGES.procurement, foot, '<ul>' + skel(3) + '</ul>'); }
    if (list === false) { return panel('mh-proc', 'clip', title, '', PAGES.procurement, foot, '<p class="empty">Procurement dates are unavailable just now.</p>'); }
    if (!list.length) { return panel('mh-proc', 'clip', title, '', PAGES.procurement, foot, M.narrowed() ? emptyMine('due', wholeHub(procs)) : '<p class="empty">Nothing due in the next six months.</p>'); }
    var shown = openPanels.proc ? list : list.slice(0, PANEL_TOP);
    var body = '<ul>' + shown.map(function (e) {
      var t = L.PROC[e.type];
      var name = String(e.title || '').replace(/^(Framework (starts|expires|ends)|Contract expires):\s*/i, '');
      var who = e.buyer || e.owner || '';
      var sub = t[1] + ' ' + L.fmtShort(e.date) + (who ? ', ' + who : '') + (L.money(e.value) ? ', ' + L.money(e.value) : '');
      var det = '<p>' + esc([L.fmtDate(e.date), e.buyer ? 'Buyer: ' + e.buyer : '', e.supplier ? 'Supplier: ' + e.supplier : '', e.supplierCount ? e.supplierCount + ' suppliers' : ''].filter(Boolean).join(', ')) + '</p>'
        + why('Note', e.note) + links(e.links || (e.source ? [{ label: 'Source notice', url: e.source }] : []));
      return prow('p:' + e.id, countdown(e.date), name, sub, det);
    }).join('') + '</ul>' + moreBtn('proc', list.length, PANEL_TOP, 'dates');
    return panel('mh-proc', 'clip', title, '', PAGES.procurement, foot, body);
  }
  function jobsPanel(list) {
    var shown = openPanels.jobs ? list : list.slice(0, PANEL_TOP);
    var body = '<ul>' + shown.map(function (g) {
      var it = g.it, sp = M.byId[g.spec], st = L.newsStamp(it.published, M.today);
      var p = String(it.title || '').replace(/^\s*(job advert|vacancy)\s*[\u2013:-]?\s*/i, '').split(/\s+[\u2013-]\s+/);
      var employer = p.length > 1 ? p[0] : '', role = p.length > 1 ? p.slice(1).join(', ') : p[0];
      var det = (it.summary ? '<p>' + esc(L.tidy(it.summary)) + '</p>' : '') + (it.source ? '<p>Posted by ' + esc(it.source) + '</p>' : '')
        + links([{ label: 'View the advert', url: it.link }, { label: sp.label, url: sp.url }]);
      return prow('j:' + it.link, '<span class="alv">' + svg('case') + '</span>', role, [employer || it.source || '', st.label].filter(Boolean).join(', '), det);
    }).join('') + '</ul>' + moreBtn('jobs', list.length, PANEL_TOP, 'jobs');
    return panel('mh-jobs', 'case', 'Jobs', 'From the speciality feeds', PAGES.jobs, 'Jobs board', body);
  }

  function html() {
    var j = jobs(), withJobs = j ? j.length > 0 : false;
    return keyNews() + '<section class="desk' + (withJobs ? ' four' : '') + '" aria-label="On the desk">'
      + eventsPanel() + alertsPanel() + procPanel() + (withJobs ? jobsPanel(j) : '') + '</section>';
  }

  /* Rows open in place; "Show all" opens a panel. */
  M.mount.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('[data-row],[data-more]') : null;
    if (!t) { return; }
    if (t.hasAttribute('data-row')) {
      var k = t.getAttribute('data-row');
      openRows[k] = !openRows[k];
      var li = t.parentNode;
      if (openRows[k]) { if (!li.classList.contains('open')) { li.classList.add('open'); } }
      else { if (li.classList.contains('open')) { li.classList.remove('open'); } }
      t.setAttribute('aria-expanded', openRows[k] ? 'true' : 'false');
      return;
    }
    var p = t.getAttribute('data-more');
    openPanels[p] = !openPanels[p];
    M.paintFeeds();
  });

  M.feeds = { load: load, html: html };
})();
