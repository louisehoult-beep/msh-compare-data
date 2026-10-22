/* Hub panels: pin a panel to My Hub, and take calendar dates away as .ics (2026-10-22).
   Pure functions, no DOM, no fetch, no clock (the caller passes "now"), so
   test_my_hub_panels.py can run them under node. Used by
   app/speciality-panels.js (the pin star and Add to my calendar on a
   speciality page) and app/my-hub-panels.js (the pinned panels on My Hub).

   A PINNED PANEL is one saved item (a "star", app/hub-account.js) of kind
   "panel". Its address is the speciality page plus a fragment:
       /medical-sales-hub/dermatology/#pin=gp:emollients
       /medical-sales-hub/dermatology/#pin=calendar
   Stars belong to the member's own account, so two members on the same
   speciality pin different things.

   CALENDAR EXPORT uses only rows already in data/hub-calendar.json, whose
   own rules say no date is estimated or rolled forward. Every event carries
   a URL back to the Hub page and its published source in the description.

   Loaded with new Function(); require()-able under node. */
(function (root) {
  'use strict';
  if (root.MSH_PANELS && typeof module === 'undefined') { return; }

  var HUB = 'https://medsalesintelligencehub.co.uk';
  var CAL_TYPES = { event: 'Event', awareness: 'Awareness day', 'framework-end': 'Framework ends', 'contract-expiry': 'Contract ends' };
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  /* ---------- pinned panels ---------- */
  function slugId(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, ''); }
  function panelKey(pagePath, panelId) {
    return String(pagePath).split('#')[0] + '#pin=' + panelId;
  }
  /* '/medical-sales-hub/dermatology/#pin=gp:skin' -> { page, slug, kind, id } or null. */
  function parsePanelKey(u) {
    var m = /^(\/medical-sales-hub\/([a-z0-9-]+)\/)#pin=([a-z0-9-]+)(?::([a-z0-9-]+))?$/.exec(String(u || ''));
    if (!m) { return null; }
    return { page: m[1], slug: m[2], kind: m[3], id: m[4] || '' };
  }
  function isPanelStar(s) { return !!s && s.k === 'panel' && !!parsePanelKey(s.u); }
  function pinnedPanels(stars) { return (stars || []).filter(isPanelStar); }

  /* ---------- calendar rows ---------- */
  /* The rows a speciality page lists: dated, with a published source, for that
     speciality, not past. Newest-first is not wanted: soonest first. */
  function calendarRows(entries, slug, today) {
    return (entries || []).filter(function (e) {
      if (!e || !CAL_TYPES[e.type]) { return false; }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(String(e.date || ''))) { return false; }
      if (!e.source) { return false; }
      if ((e.specialities || []).indexOf(slug) === -1) { return false; }
      return (e.endDate || e.date) >= today;
    }).sort(function (a, b) { return String(a.date).localeCompare(String(b.date)) || String(a.title).localeCompare(String(b.title)); });
  }
  function fmtDate(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || '');
    return m ? (+m[3]) + ' ' + MONTHS[+m[2] - 1] + ' ' + m[1] : '';
  }
  function typeLabel(e) { return CAL_TYPES[e.type] || ''; }

  /* ---------- .ics (RFC 5545) ---------- */
  function esc(s) {
    return String(s === null || s === undefined ? '' : s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
  }
  /* Lines are folded at 75 octets, continuation lines start with one space.
     Cuts fall between characters, never inside a multi-byte one. */
  function octets(ch) { var c = ch.codePointAt(0); return c < 0x80 ? 1 : c < 0x800 ? 2 : c < 0x10000 ? 3 : 4; }
  function fold(line) {
    var out = [], cur = '', n = 0, limit = 75;
    Array.from(line).forEach(function (ch) {
      var w = octets(ch);
      if (n + w > limit) { out.push(cur); cur = ' '; n = 1; limit = 75; }
      cur += ch; n += w;
    });
    out.push(cur);
    return out.join('\r\n');
  }
  function compact(iso) { return String(iso).replace(/-/g, ''); }
  function nextDay(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
    var d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3] + 1));
    return d.getUTCFullYear() + ('0' + (d.getUTCMonth() + 1)).slice(-2) + ('0' + d.getUTCDate()).slice(-2);
  }
  /* The Hub page an event points back to: its own Hub link for the speciality
     when the row has one, else the speciality page. */
  function hubLink(e, slug) {
    var want = HUB + '/medical-sales-hub/' + slug + '/';
    var links = (e.links || []).filter(function (l) { return l && l.kind === 'hub' && typeof l.url === 'string'; });
    for (var i = 0; i < links.length; i++) { if (links[i].url.indexOf(want) === 0) { return links[i].url; } }
    return want;
  }
  function vevent(e, slug, stamp) {
    var end = e.endDate && e.endDate > e.date ? e.endDate : e.date;
    var hub = hubLink(e, slug);
    var desc = [typeLabel(e) + (e.owner ? ' (' + e.owner + ')' : ''), e.note || '', 'More on the Medical Sales Hub: ' + hub, 'Published source: ' + e.source]
      .filter(function (x) { return x; }).join('\n');
    var lines = ['BEGIN:VEVENT',
      'UID:' + e.id + '@medsalesintelligencehub.co.uk',
      'DTSTAMP:' + stamp,
      'DTSTART;VALUE=DATE:' + compact(e.date),
      'DTEND;VALUE=DATE:' + nextDay(end),
      'SUMMARY:' + esc(e.title),
      'DESCRIPTION:' + esc(desc),
      'URL:' + hub];
    if (e.location) { lines.push('LOCATION:' + esc(e.location)); }
    lines.push('TRANSP:TRANSPARENT', 'END:VEVENT');
    return lines;
  }
  /* now: an ISO timestamp string such as new Date().toISOString(). */
  function ics(rows, slug, calName, now) {
    var stamp = String(now).replace(/[-:]/g, '').replace(/\.\d+/, '').slice(0, 15) + 'Z';
    var lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Medical Sales Hub//Calendar//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
      'X-WR-CALNAME:' + esc(calName)];
    rows.forEach(function (e) { lines = lines.concat(vevent(e, slug, stamp)); });
    lines.push('END:VCALENDAR');
    return lines.map(fold).join('\r\n') + '\r\n';
  }
  function icsName(slug, id) { return 'msh-' + slug + (id ? '-' + slugId(id) : '-calendar') + '.ics'; }

  /* ---------- a GP prescribing market, summarised for My Hub ---------- */
  function gpSummary(panels, marketId) {
    var gp = panels && panels.gpPrescribing;
    if (!gp || !gp.defined) { return null; }
    var m = (gp.markets || []).filter(function (x) { return x.id === marketId; })[0];
    if (!m) { return null; }
    return { label: m.label, period: String(m.latestPeriod).slice(0, 4) + '-' + String(m.latestPeriod).slice(4),
      items: m.items, cost: m.cost, itemsYoY: m.itemsYoY, top: (m.topNational || []).slice(0, 5),
      source: gp.source, attribution: gp.attribution || '' };
  }

  /* ---------- a section of the speciality page, summarised for My Hub ----------
     Pin ids "sec:<id>". Every row is the file's own text; nothing is computed
     beyond ordering and a cap. Null when the speciality has nothing for the
     section, so My Hub shows an honest "no longer on the page". */
  var SEC_TITLES = { frameworks: 'Frameworks', tenders: 'Open now', local: 'Local contracts, formularies and policy',
    awards: 'Awarded contracts', 'tariff-moves': 'Drug Tariff price moves', dsu: 'MHRA Drug Safety Updates' };
  var SEC_CAP = 5;
  function row(t, s, u) { return { t: String(t || ''), s: String(s || ''), u: u ? String(u) : '' }; }
  function parseEnd(txt) { var d = new Date(txt); return isNaN(d.getTime()) ? null : d.getTime(); }
  function sectionSummary(panels, id, today) {
    if (!panels || !SEC_TITLES[id]) { return null; }
    var d = panels, rows = [], total = 0, lede = '', asOf = '', src = '', srcUrl = '';
    if (id === 'frameworks') {
      var f = (d.frameworks || []).slice();
      total = f.length;
      f.sort(function (a, b) { var x = parseEnd(a.ends), y = parseEnd(b.ends); return (x === null ? 1e15 : x) - (y === null ? 1e15 : y); });
      rows = f.map(function (x) { return row(x.name, [x.supplyRoute || x.category, 'ends ' + (x.ends || 'not stated'), x.supplierCount === null || x.supplierCount === undefined ? '' : x.supplierCount + ' suppliers'].filter(Boolean).join(', '), x.url); });
      asOf = (d.dataAsOf || {}).frameworks || ''; src = 'NHS Supply Chain framework pages';
    } else if (id === 'tenders') {
      var o = d.openTenders || [];
      total = o.length;
      rows = o.map(function (x) { return row(x.title, [x.buyer, 'closes ' + (x.closingDate ? String(x.closingDate).slice(0, 10) : 'not stated')].filter(Boolean).join(', '), x.url); });
      asOf = (d.dataAsOf || {}).openTenders || ''; src = 'Find a Tender and Contracts Finder notices';
    } else if (id === 'awards') {
      var a = d.awards || [];
      total = a.length;
      rows = a.map(function (x) {
        var kind = x.stage === 'planning' ? 'Planning notice, not an award' : (x.stage === 'tender' ? 'Tender notice, not yet awarded' : (x.supplier ? 'Awarded to ' + x.supplier : 'Award notice'));
        return row(x.title, [fmtDate(x.date), x.buyer, kind].filter(Boolean).join(', '), x.url);
      });
      asOf = (d.dataAsOf || {}).tenderHistory || ''; src = 'Find a Tender and Contracts Finder notices';
    } else if (id === 'local') {
      var l = d.localIntel || [];
      total = l.length;
      rows = l.map(function (x) { return row(x.title, [x.org, x.kind, x.ends ? (/^\d/.test(x.ends) ? 'ends ' : '') + x.ends : ''].filter(Boolean).join(', '), x.url); });
      asOf = (d.dataAsOf || {}).localIntel || ''; src = 'each item’s own source, read by the Hub';
    } else if (id === 'dsu') {
      var u = (d.mhraDsu && d.mhraDsu.updates) || [];
      total = u.length;
      rows = u.map(function (x) { return row(x.title, 'Published ' + fmtDate(x.published), x.url); });
      asOf = (d.mhraDsu && d.mhraDsu.dataAsOf) || ''; src = 'MHRA Drug Safety Update on GOV.UK'; srcUrl = (d.mhraDsu && d.mhraDsu.sourcePage) || '';
    } else if (id === 'tariff-moves') {
      var t = d.drugTariffMoves;
      if (!t) { return null; }
      total = 1;
      lede = t.movedCount + ' of ' + t.linesCompared + ' lines changed price (' + t.upCount + ' up, ' + t.downCount + ' down), ' + t.addedCount + ' new, ' + t.droppedCount + ' no longer listed. ' + t.previousMonth + ' to ' + t.currentMonth + '.';
      rows = (t.suppliers || []).map(function (x) { return row(x.name, x.up + ' up, ' + x.down + ' down' + (x.minPct === undefined ? '' : ', ' + x.minPct + '% to ' + x.maxPct + '%'), ''); });
      asOf = t.dataAsOf || ''; src = 'NHSBSA Drug Tariff Part IX'; srcUrl = t.sourcePage || '';
    }
    if (!total) { return null; }
    return { id: id, title: SEC_TITLES[id], lede: lede, rows: rows.slice(0, SEC_CAP), total: total, asOf: asOf, source: src, sourceUrl: srcUrl };
  }

  var api = {
    slugId: slugId, panelKey: panelKey, parsePanelKey: parsePanelKey, isPanelStar: isPanelStar, pinnedPanels: pinnedPanels,
    calendarRows: calendarRows, fmtDate: fmtDate, typeLabel: typeLabel, ics: ics, icsName: icsName, hubLink: hubLink,
    gpSummary: gpSummary, sectionSummary: sectionSummary, SEC_TITLES: SEC_TITLES, CAL_TYPES: CAL_TYPES
  };
  root.MSH_PANELS = api;
  if (typeof module === 'object') { if (module) { if (module.exports) { module.exports = api; } } }
})(typeof window !== 'undefined' ? window : globalThis);
