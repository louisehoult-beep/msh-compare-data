/* Medical Sales Intelligence Hub: "Stock alerts" feed, a filtered view of the current NHS Supply Chain
   supply-issue notices (ICNs) in data/compare-issues.json for one product area. Added 18/11/2026 for a
   Meril UK request (out-of-stock notifications for surgical stapling, sutures and hernia mesh).

   WHAT IT IS, AND IS NOT
     A read-only feed: a count, the latest date, and one card per notice with a link to the notice itself.
     It is NOT a push or email alert. Nothing is sent and no secret is needed. A member sees new notices
     by opening the page (or pinning it on My Hub). Push alerts (alerts/index.html) still carry speciality
     news only.

   HOW A DESK PAGE USES IT
     Put <div id="msh-stockalerts" data-area="stapling-sutures-mesh"></div> on the page and load this file
     with the same fetch + new Function loader as app/kol-finder.js. ?area=<key> in the page link overrides
     data-area. Areas are in AREAS below.

   MATCHING
     A notice is listed when its title, status text or tactical line (p, s, use in compare-issues.json)
     contains one of the area's words. The card says which words matched, so a rep can see why it is there.
     A notice is marked "closed" only when its own status text says the notice is closed or resolved; open
     the notice for the current position, because the status text is a snapshot.

   Loaded with new Function(); require()-able under node, where only the pure functions (_pure) are
   exercised: test_stock_alerts.py. */
(function (root) {
  'use strict';

  var MOUNT_ID = 'msh-stockalerts';
  var SRC = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/compare-issues.json';
  var TRACKER = '/medical-sales-hub/supply-disruption-tracker/';

  var AREAS = {
    'stapling-sutures-mesh': {
      label: 'Surgical stapling, sutures and hernia mesh',
      kinds: [
        { id: 'stapling', label: 'Stapling', re: /stapl/i },
        { id: 'sutures', label: 'Sutures', re: /sutur/i },
        { id: 'mesh', label: 'Mesh', re: /\bmesh\b|hernia/i }
      ]
    },
    'stapling-sutures': {
      label: 'Surgical stapling and sutures',
      kinds: [
        { id: 'stapling', label: 'Stapling', re: /stapl/i },
        { id: 'sutures', label: 'Sutures', re: /sutur/i }
      ]
    }
  };
  var MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
  var CLOSED_RE = /notice is closed|supply issue is resolved|has been closed|notice has closed/i;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function ukDate(iso) {
    if (!iso) { return ''; }
    var p = String(iso).slice(0, 10).split('-');
    return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : esc(iso);
  }
  /* "Aug 2026" -> "2026-08"; firstSeen "2026-08-19" is preferred when present. */
  function sortKey(it) {
    if (it.firstSeen) { return String(it.firstSeen).slice(0, 10); }
    var m = /^([A-Za-z]{3})\w* (20\d\d)$/.exec(String(it.d || ''));
    return m && MONTHS[m[1].toLowerCase()] ? m[2] + '-' + (MONTHS[m[1].toLowerCase()] < 10 ? '0' : '') + MONTHS[m[1].toLowerCase()] + '-00' : '';
  }
  function pickArea(key) { return AREAS[key] ? key : 'stapling-sutures-mesh'; }

  /* Every matching notice across all specialities, newest first, each once. */
  function match(doc, areaKey) {
    var area = AREAS[pickArea(areaKey)];
    var seen = {}, out = [];
    var specs = (doc && doc.specialities) || {};
    Object.keys(specs).forEach(function (sp) {
      ((specs[sp] && specs[sp].issues) || []).forEach(function (it) {
        if (!it || !it.id || seen[it.id]) { return; }
        var hay = [it.p, it.s, it.use].join(' ');
        var kinds = area.kinds.filter(function (k) { return k.re.test(hay); }).map(function (k) { return k.id; });
        if (!kinds.length) { return; }
        seen[it.id] = 1;
        out.push({
          id: it.id, speciality: sp, title: it.p, company: it.co, month: it.d, url: it.url,
          kinds: kinds, closed: CLOSED_RE.test(String(it.s || '')), sort: sortKey(it)
        });
      });
    });
    out.sort(function (a, b) { return a.sort < b.sort ? 1 : a.sort > b.sort ? -1 : 0; });
    return out;
  }
  function summary(list) {
    var open = list.filter(function (x) { return !x.closed; });
    return { total: list.length, open: open.length, latest: list.length ? list[0].month : '' };
  }

  var _pure = { esc: esc, ukDate: ukDate, sortKey: sortKey, pickArea: pickArea, match: match, summary: summary, AREAS: AREAS };
  if (typeof module !== 'undefined' && module.exports) { module.exports = { _pure: _pure }; return; }

  var CSS = '.stk,.stk *{box-sizing:border-box}.stk{overflow-wrap:anywhere;color:#0B1C33;font-family:Inter,-apple-system,"Segoe UI",system-ui,sans-serif}'
    + '.stk h2{font-family:"Cormorant Garamond",Georgia,serif;font-size:28px;font-weight:600;margin:0 0 6px}'
    + '.stk .stk-sub{margin:0 0 14px;line-height:1.6;color:#1D2733;max-width:820px}'
    + '.stk .stk-count{font-weight:700;margin:0 0 12px}'
    + '.stk ul{list-style:none;margin:0;padding:0;display:grid;gap:12px}'
    + '.stk li{background:#fff;border:1px solid #d9d1bf;border-left:4px solid #A8842C;border-radius:10px;padding:12px 14px}'
    + '.stk li.closed{border-left-color:#8a7d5c;opacity:.85}'
    + '.stk .stk-t{font-weight:600;margin:0 0 4px;line-height:1.45}.stk .stk-m{font-size:13.5px;color:#37485a;margin:0 0 6px}'
    + '.stk .stk-tag{display:inline-block;font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:99px;background:#0B1C33;color:#E0BE8E;margin-right:6px}'
    + '.stk a{color:#0B1C33;font-weight:600;text-decoration:underline}';

  function run(doc, mount) {
    var key = pickArea(mount.getAttribute('data-area'));
    try { var a = new URLSearchParams(location.search).get('area'); if (a && AREAS[a]) { key = a; } } catch (e) {}
    var list = match(doc, key), sm = summary(list);
    var label = AREAS[key].label;
    var kl = {}; AREAS[key].kinds.forEach(function (k) { kl[k.id] = k.label; });
    mount.innerHTML = '<style>' + CSS + '</style><div class="stk"><h2>Stock alerts: ' + esc(label) + '</h2>'
      + '<p class="stk-sub">Current NHS Supply Chain supply-issue notices that mention these products, from the Hub\'s weekly-refreshed feed (data as at ' + esc(doc.dataAsOf || '') + '). '
      + 'This page lists them; it does not send alerts. Open a notice for its latest status. Individual suspended lines are on the <a href="' + TRACKER + '">Supply Disruption Tracker</a>.</p>'
      + '<p class="stk-count">' + sm.total + (sm.total === 1 ? ' notice' : ' notices') + ', ' + sm.open + ' not marked closed' + (sm.latest ? ', latest dated ' + esc(sm.latest) : '') + '</p>'
      + (list.length ? '<ul>' + list.map(function (x) {
        return '<li class="' + (x.closed ? 'closed' : '') + '"><p class="stk-t">' + esc(x.title) + '</p>'
          + '<p class="stk-m">' + esc(x.company) + ', ' + esc(x.month) + (x.closed ? ', status text says closed' : '') + '</p>'
          + '<div>' + x.kinds.map(function (k) { return '<span class="stk-tag">' + esc(kl[k] || k) + '</span>'; }).join('')
          + (x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">Read the notice</a>' : '') + '</div></li>';
      }).join('') + '</ul>' : '<p class="stk-sub">No current notice mentions these products.</p>')
      + '</div>';
  }

  function start() {
    var mount = document.getElementById(MOUNT_ID);
    if (!mount) { return; }
    fetch(root.mshStockSrc || SRC, { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error(r.status); } return r.json(); })
      .then(function (doc) { run(doc, mount); })
      .catch(function () { mount.innerHTML = 'Stock alerts are temporarily unavailable. Please try again shortly.'; });
  }
  start();
})(typeof window !== 'undefined' ? window : this);
