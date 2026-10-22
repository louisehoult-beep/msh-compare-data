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

  var api = {
    slugId: slugId, panelKey: panelKey, parsePanelKey: parsePanelKey, isPanelStar: isPanelStar, pinnedPanels: pinnedPanels,
    calendarRows: calendarRows, fmtDate: fmtDate, typeLabel: typeLabel, ics: ics, icsName: icsName, hubLink: hubLink,
    gpSummary: gpSummary, CAL_TYPES: CAL_TYPES
  };
  root.MSH_PANELS = api;
  if (typeof module === 'object') { if (module) { if (module.exports) { module.exports = api; } } }
})(typeof window !== 'undefined' ? window : globalThis);
