/* Medical Sales Intelligence Hub: hospitals and named contacts under each trust in
   "Trusts by ICB" on How the NHS Fits Together (page 884). Added 20/11/2026 (Lou, after
   the Meril UK call: "add all hospitals within a trust ... with all the contacts within
   each trust too").

   Git-served, same pattern as kol-finder.js: page 884 carries a fetch + new Function
   loader; this script finds the existing trust lists (#msh-trustdir and #msh-trustdir-*),
   and under each trust link adds a fold: the trust's hospitals (data/trust-sites.json,
   from NHS ODS) and the named people filed to that trust (data/kol-finder.json, each with
   the public page it came from). It changes nothing else on the page.

   Trust links on the page are written by hand ("Liverpool Women's NHS FT"), so each is
   matched to an ODS trust by its words; a link that matches no trust clearly is left as it
   is rather than guessed. */
(function (root) {
  'use strict';
  var RAW = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/';
  var NET = '/medical-sales-hub/build-your-network/';
  var STOP = { nhs: 1, the: 1, foundation: 1, trust: 1, ft: 1, group: 1, of: 1, and: 1, '': 1 };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function words(s) {
    return String(s || '').toLowerCase().replace(/&/g, ' and ').replace(/[’']/g, '').replace(/[^a-z0-9 ]+/g, ' ')
      .split(/\s+/).filter(function (w) { return !STOP[w]; });
  }
  function score(a, b) {
    var A = {}, n = 0, i;
    for (i = 0; i < a.length; i++) { A[a[i]] = 1; }
    var B = {};
    for (i = 0; i < b.length; i++) { B[b[i]] = 1; if (A[b[i]]) { n++; } }
    var u = Object.keys(A).length + Object.keys(B).length - n;
    return u ? n / u : 0;
  }
  /* Best ODS trust for a link's words: clearly best, and at least 0.6 overlap. */
  function match(text, trusts) {
    var w = words(text), best = null, bs = 0, second = 0;
    trusts.forEach(function (t) {
      var s = score(w, t._w);
      if (s > bs) { second = bs; bs = s; best = t; } else if (s > second) { second = s; }
    });
    return bs >= 0.6 && bs - second >= 0.15 ? best : null;
  }
  var _pure = { words: words, score: score, match: match };
  if (typeof module !== 'undefined' && module.exports) { module.exports = { _pure: _pure }; return; }

  var CSS = '.tds{margin:4px 0 2px;font-size:13px}.tds summary{cursor:pointer;color:#14304F;font-weight:600;list-style:none}'
    + '.tds summary::-webkit-details-marker{display:none}.tds summary:before{content:"+ ";font-weight:700}.tds[open] summary:before{content:"− "}'
    + '.tds .tds-b{background:#F5F1E8;border-radius:6px;padding:8px 10px;margin:6px 0 4px}'
    + '.tds h5{margin:6px 0 4px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#46566A}'
    + '.tds ul{margin:0 0 6px;padding-left:16px}.tds li{margin:0 0 3px;line-height:1.45;list-style:disc}'
    + '.tds .tds-s{font-size:11.5px;color:#46566A}.tds a{text-decoration:underline}.tds .tds-go{font-weight:600}';

  function block(t, sites, people) {
    var h = sites && sites.hospitals ? sites.hospitals : [];
    var other = sites ? sites.otherSites || 0 : 0;
    var hp = '<h5>Hospitals (' + h.length + ')</h5>' + (h.length
      ? '<ul>' + h.map(function (x) { return '<li>' + esc(x.name) + (x.postcode ? ' <span class="tds-s">' + esc(x.postcode) + '</span>' : '') + '</li>'; }).join('') + '</ul>'
      : '<p class="tds-s">No site named as a hospital in NHS ODS.</p>')
      + (other ? '<p class="tds-s">And ' + other + ' other registered sites (clinics, units and community bases).</p>' : '');
    var top = people.slice(0, 12);
    var pp = '<h5>Named contacts (' + people.length + ')</h5>' + (people.length
      ? '<ul>' + top.map(function (p) {
        var a = p.appearances[0] || {};
        return '<li><b>' + esc(p.name) + '</b>, ' + esc(a.role || '') + (p.hospital ? ' (' + esc(p.hospital) + ')' : '')
          + (a.source_url ? ' <a class="tds-s" href="' + esc(a.source_url) + '" target="_blank" rel="noopener">source</a>' : '') + '</li>';
      }).join('') + '</ul>'
      : '<p class="tds-s">Nobody checked at a public source yet.</p>')
      + '<a class="tds-go" href="' + NET + '?speciality=all&amp;trust=' + encodeURIComponent(t.code) + '">'
      + (people.length > top.length ? 'See all ' + people.length + ' and filter' : 'Open in Build Your Network') + ' &rarr;</a>';
    return '<details class="tds"><summary>Hospitals ' + h.length + ' · Contacts ' + people.length + '</summary><div class="tds-b">' + hp + pp
      + '<p class="tds-s">Hospitals from NHS ODS, as at ' + esc(sites && sites._asOf || '') + '. Contacts from public pages, each linked.</p></div></details>';
  }

  function run(tm, ts, kol) {
    var trusts = tm.trusts.map(function (t) { t._w = words(t.n); return t; });
    var byTrust = {};
    (kol.people || []).forEach(function (p) { if (p.trustCode) { (byTrust[p.trustCode] = byTrust[p.trustCode] || []).push(p); } });
    Object.keys(byTrust).forEach(function (k) {
      byTrust[k].sort(function (a, b) { return (b.classes.indexOf('supply') !== -1) - (a.classes.indexOf('supply') !== -1) || (a.name < b.name ? -1 : 1); });
    });
    var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    var lists = document.querySelectorAll('[id^="msh-trustdir"] .tdcard li');
    [].forEach.call(lists, function (li) {
      if (li.querySelector('.tds')) { return; }
      var a = li.querySelector('a'); if (!a) { return; }
      var t = match(a.textContent, trusts); if (!t) { return; }
      var s = ts.trusts[t.code]; if (s) { s._asOf = String(ts.asOf || '').split('-').reverse().join('/'); }
      var wrap = document.createElement('div');
      wrap.innerHTML = block(t, s, byTrust[t.code] || []);
      li.appendChild(wrap.firstChild);
    });
  }

  function start() {
    if (!document.querySelector('[id^="msh-trustdir"]')) { return; }
    var cb = '?cb=' + Math.floor(Date.now() / 3600000);
    var j = function (f) { return fetch(RAW + f + cb).then(function (r) { if (!r.ok) { throw new Error(f); } return r.json(); }); };
    Promise.all([j('trust-map.json'), j('trust-sites.json'), j('kol-finder.json')])
      .then(function (d) { run(d[0], d[1], d[2]); })
      .catch(function () {});
  }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', start); } else { start(); }
})(typeof window !== 'undefined' ? window : this);
