/* ETH-HUBSEARCH-V7 — Hub search, served from msh-compare-data.
 *
 * WHAT CHANGED FROM V6 (06/08/2026)
 * ---------------------------------
 * V6 ranked 47 Hub pages typed by hand into WordPress, matching on a title and
 * a line of synonyms. It could not see inside a page, could not see a page
 * nobody had remembered to add, and could not see the 459 suppliers that the
 * Suppliers page loads from JSON at run time. Lou's report was that it still
 * could not do what she wanted, and it structurally could not.
 *
 * V7 searches data/hub-search-index.json, which build_search_index.py rebuilds
 * daily from the Hub's own published pages, section by section. A result points
 * at the SECTION that matched, not just the page, and shows the line it matched
 * on.
 *
 * WHY THIS FILE LIVES IN THE REPO AND NOT IN THE PAGE
 * --------------------------------------------------
 * WordPress rewrites && and || into HTML entities when it renders an inline
 * script, which is a SyntaxError that kills the whole block — the reason V6 was
 * written in nested ifs. Serving the code from here removes that constraint and
 * removes WordPress from the edit path entirely: nobody has to touch page 675
 * to change how search behaves ever again. Same pattern as comptab.js and
 * supplier-search.js.
 *
 * COST: none. The index is a static file on GitHub, the search runs in the
 * member's browser, and nothing calls any paid service. There is no AI here.
 *
 * FAILURE MODE: if the index cannot be fetched, the box says so and offers
 * WordPress core search. The page 675 block also renders a plain working form
 * before this script arrives, so a total failure degrades to core search rather
 * than to an empty space.
 */
(function () {
  'use strict';

  var INDEX_URL = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/hub-search-index.json';

  var NAVY = '#0B1C33', GOLD = '#C49B5C', PANEL = '#0f172a',
      LINE = '#33415a', RULE = '#1e293b', TEXT = '#e2e8f0', DIM = '#94a3b8';

  var MOUNT = document.getElementById('ethHubSearch');
  if (!MOUNT) { return; }
  if (MOUNT.getAttribute('data-eth-bound') === 'v7') { return; }
  MOUNT.setAttribute('data-eth-bound', 'v7');

  // Words that carry no signal in a query. A rep types "what does ICB stand
  // for"; only "icb" narrows anything.
  var STOP = (' the a an of for in on at to is are am was were do does did how what ' +
              'where which who whom why when i my me we our you your can could should ' +
              'would with and or but if it its this that these those from by as be ' +
              'about into any all get got need want find show tell explain ').split(' ');

  var TASKS = [
    ['Prepare for a meeting', '/medical-sales-hub/med-sales-tools/#tool-prep'],
    ['Compare against a competitor', '/medical-sales-hub/med-sales-tools/#tool-compare'],
    ['Research a supplier', '/medical-sales-hub/med-sales-tools/#tool-supplier'],
    ['Map the stakeholders', '/medical-sales-hub/med-sales-tools/#sec-map'],
    ['Track a contract award', '/medical-sales-hub/awards/#q'],
    ['Check a framework or tender route', '/medical-sales-hub/frameworks/#fw-nhssc'],
    ['Check framework renewal dates', '/medical-sales-hub/frameworks/#fw-renewal'],
    ['Check price intelligence', '/medical-sales-hub/price-intelligence/'],
    ['Find a CPV code', '/medical-sales-hub/cpv/'],
    ['Understand TR reports', '/medical-sales-hub/reference/tr-reports/'],
    ['Ask for something to be added', '/medical-sales-hub/ask/']
  ];

  var DATA = null, LOADING = false, FAILED = false, input = null, box = null;

  function esc(x) {
    return String(x)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function clean(q) {
    return String(q).toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function tokenise(q) {
    var parts = clean(q).split(' '), out = [], i;
    for (i = 0; i < parts.length; i++) {
      if (!parts[i]) { continue; }
      if (STOP.indexOf(parts[i]) !== -1) { continue; }
      out.push(parts[i]);
    }
    return out.length ? out : parts.filter(Boolean);
  }

  /* Match on WORD START, never raw substring. V5 matched substrings, which made
   * "what does ICB stand for" hit "Under-STAND-ing TR Reports" — the exact class
   * of nonsense result this whole rebuild exists to remove. */
  function hits(hay, tok) {
    if (hay.indexOf(' ' + tok) !== -1) { return true; }
    if (tok.length > 3 && tok.charAt(tok.length - 1) === 's') {
      if (hay.indexOf(' ' + tok.slice(0, -1)) !== -1) { return true; }
    }
    return false;
  }

  /* Lowercased, space-padded copies are built once at load so a keystroke is a
   * scan over prepared strings rather than 4,000 toLowerCase() calls. */
  function prepare(doc) {
    var i, j, p, s;
    for (i = 0; i < doc.pages.length; i++) {
      p = doc.pages[i];
      p._t = ' ' + String(p.t || '').toLowerCase();
      for (j = 0; j < p.sec.length; j++) {
        s = p.sec[j];
        s._h = ' ' + String(s.h || '').toLowerCase();
        /* `w` is a bag of words, not prose: unique, alphabetised, stopwords
         * dropped. The index is served from a public repo, so it deliberately
         * carries nothing that can be read back as the Hub's paid content. That
         * is why there is no snippet under a result — do not add one by putting
         * text back in the index. */
        s._w = ' ' + String(s.w || '').toLowerCase();
      }
    }
    for (i = 0; i < doc.records.length; i++) {
      doc.records[i]._t = ' ' + String(doc.records[i].t || '').toLowerCase();
      doc.records[i]._k = ' ' + String(doc.records[i].k || '');
    }
    return doc;
  }

  function scorePage(p, toks, phrase) {
    var s = 0, best = null, bestS = 0, i, j, sec, ss, covered = {}, tok;

    if (phrase.length > 2 && p._t.indexOf(phrase) !== -1) { s += 140; }
    for (i = 0; i < toks.length; i++) {
      if (hits(p._t, toks[i])) { s += 18; covered[toks[i]] = 1; }
    }

    for (j = 0; j < p.sec.length; j++) {
      sec = p.sec[j];
      ss = 0;
      /* A phrase can only be matched against a heading. The body is a sorted
       * bag of words, so word order does not survive in it and there is no
       * phrase left to find — which is exactly the property that stops the
       * index being readable. */
      if (phrase.length > 2 && sec._h.indexOf(phrase) !== -1) { ss += 90; }
      for (i = 0; i < toks.length; i++) {
        tok = toks[i];
        if (hits(sec._h, tok)) { ss += 12; covered[tok] = 1; }
        else if (hits(sec._w, tok)) { ss += 6; covered[tok] = 1; }
      }
      if (ss > bestS) { bestS = ss; best = sec; }
      s += ss;
    }

    // Everything the member typed appears somewhere on this page. That is a
    // much stronger signal than a big pile of one repeated word.
    var all = true;
    for (i = 0; i < toks.length; i++) { if (!covered[toks[i]]) { all = false; } }
    if (all && toks.length) { s += 45; }

    return { s: s, sec: best };
  }

  function scoreRecord(r, toks, phrase) {
    var s = 0, i, named = false;
    if (phrase.length > 2) {
      if (r._t.indexOf(phrase) !== -1) { s += 130; named = true; }
      else if (r._k.indexOf(phrase) !== -1) { s += 45; }
    }
    for (i = 0; i < toks.length; i++) {
      if (hits(r._t, toks[i])) { s += 22; named = true; }
      else if (hits(r._k, toks[i])) { s += 7; }
    }
    /* A supplier record is 459 rows of names, aliases, specialities and
     * framework titles. One incidental keyword hit — "tender close april 2026"
     * brushing against a framework name — is not a reason to put a company in
     * front of a member who asked about a deadline. Either the query touched
     * the company's own name, or it has to earn its place on keywords alone. */
    if (!named && s < 45) { return 0; }
    return s;
  }

  /* THERE IS NO SNIPPET FUNCTION, AND THAT IS DELIBERATE.
   * An earlier build quoted the matching line under each result, which meant the
   * index had to carry running text from every Hub page — and the index is
   * served from a PUBLIC repo, so that published the paid product. Lou ruled on
   * it, 06/08/2026: the index carries headings and bags of words only. A result
   * gives the section and links straight to it. If the quoted line is ever
   * wanted back, move the index behind the login first. */

  /* Deep-link to a section that has no id of its own.
   *
   * Only 3 of 772 sections in the live index carry an anchor — Hub panels are
   * mostly `<div class="panel"><h2>TITLE</h2>` with nothing to link to. Without
   * this, "links straight to the section" means "lands at the top of the page"
   * for 769 of them.
   *
   * A text fragment (#:~:text=) makes the browser find and scroll to the words
   * itself, so no id is needed. Chrome, Edge and Safari 16+ support it; anything
   * else ignores the fragment and lands at the top of the page, which is exactly
   * where it would have landed anyway. There is no downside case.
   *
   * Only the first few words are used: an indexed heading can carry a trailing
   * source label ("MHRA ALERTS & RECALLS GOV.UK") that is a separate element on
   * the page, and a fragment spanning both would match nothing. */
  function textFragment(heading) {
    var words = String(heading || '').trim().split(/\s+/).slice(0, 6).join(' ');
    if (words.length < 4) { return ''; }
    return '#:~:text=' + encodeURIComponent(words);
  }

  function rank(q) {
    var toks = tokenise(q), phrase = clean(q), out = [], i, r, sc;
    if (!toks.length) { return out; }

    for (i = 0; i < DATA.pages.length; i++) {
      r = scorePage(DATA.pages[i], toks, phrase);
      if (r.s > 0) {
        out.push({ kind: 'page', s: r.s, page: DATA.pages[i], sec: r.sec });
      }
    }
    for (i = 0; i < DATA.records.length; i++) {
      sc = scoreRecord(DATA.records[i], toks, phrase);
      if (sc > 0) { out.push({ kind: 'rec', s: sc, rec: DATA.records[i] }); }
    }
    if (!out.length) { return out; }
    out.sort(function (a, b) { return b.s - a.s; });

    /* Cut the long tail. Once results are ranked, everything scoring a small
     * fraction of the best hit is a word that happened to appear, not an answer
     * — and a list padded with those is indistinguishable to a reader from the
     * "returns all random stuff" search this replaced. Showing three good
     * results and stopping is the honest output. */
    var floor = Math.max(12, out[0].s * 0.18);
    out = out.filter(function (r) { return r.s >= floor; });
    return out.slice(0, 10);
  }

  // ------------------------------------------------------------------ render
  function shell() {
    var chips = TASKS.map(function (t) {
      return '<a href="' + esc(t[1]) + '" style="display:block;padding:11px 14px;border-radius:8px;' +
             'border:1px solid ' + LINE + ';background:' + PANEL + ';color:' + TEXT + ';font-size:13.5px;' +
             'line-height:1.35;text-decoration:none;font-weight:500;">' + esc(t[0]) + '</a>';
    }).join('');

    MOUNT.innerHTML =
      '<div style="display:flex;align-items:center;gap:12px;margin:0 0 14px;">' +
        '<span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;' +
        'border-radius:50%;background:' + GOLD + ';color:' + NAVY + ';font-size:21px;font-weight:700;line-height:1;flex:0 0 auto;">?</span>' +
        '<span style="color:#fff;font-size:17px;font-weight:700;">What do you want to do today?</span>' +
      '</div>' +
      '<div style="display:flex;gap:10px;margin:0 0 8px;width:100%;">' +
        '<input id="ethHubInput" type="search" autocomplete="off" aria-label="Search the Hub" ' +
        'placeholder="Search every Hub page — a supplier, a framework, a term, a question" ' +
        'style="flex:1;min-width:0;padding:13px 16px;border-radius:8px;border:1px solid ' + LINE + ';' +
        'background:' + PANEL + ';color:#fff;font-size:14.5px;font-family:inherit;box-sizing:border-box;">' +
        '<button type="button" id="ethHubGo" style="padding:13px 28px;border-radius:8px;border:none;' +
        'background:' + GOLD + ';color:' + NAVY + ';font-weight:700;font-size:14.5px;cursor:pointer;' +
        'font-family:inherit;white-space:nowrap;">Go</button>' +
      '</div>' +
      '<div id="ethHubResults" style="display:none;background:' + PANEL + ';border:1px solid ' + LINE + ';' +
      'border-radius:8px;margin:0 0 12px;overflow:hidden;max-height:60vh;overflow-y:auto;"></div>' +
      '<p id="ethHubHint" style="margin:0 0 16px;color:' + DIM + ';font-size:12.5px;">' +
      'Searches inside every Hub page, not just the titles. Or jump straight to a task.</p>' +
      '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:9px;width:100%;">' +
      chips + '</div>';

    input = document.getElementById('ethHubInput');
    box = document.getElementById('ethHubResults');
  }

  function row(href, title, kicker, body) {
    return '<a href="' + esc(href) + '" style="display:block;padding:11px 14px;color:' + TEXT + ';' +
           'text-decoration:none;border-top:1px solid ' + RULE + ';">' +
           '<span style="display:block;font-size:14px;font-weight:600;">' + esc(title) + '</span>' +
           (kicker ? '<span style="display:block;color:' + GOLD + ';font-size:11px;font-weight:700;' +
                     'letter-spacing:.8px;text-transform:uppercase;margin-top:3px;">' + esc(kicker) + '</span>' : '') +
           (body ? '<span style="display:block;color:#a8b3c4;font-size:12.5px;line-height:1.5;margin-top:4px;">' +
                   body + '</span>' : '') +
           '</a>';
  }

  function note(text) {
    return '<div style="padding:12px 14px;color:' + DIM + ';font-size:13px;">' + text + '</div>';
  }

  function render() {
    var q = input.value ? input.value.trim() : '';
    if (q.length < 2) { box.style.display = 'none'; box.innerHTML = ''; return; }

    box.style.display = 'block';

    if (FAILED) {
      box.innerHTML = note('Hub search cannot reach its index right now. ' +
        '<a href="/?s=' + encodeURIComponent(q) + '" style="color:' + GOLD + ';font-weight:700;">' +
        'Search every page and post instead</a>.');
      return;
    }
    if (!DATA) {
      box.innerHTML = note('Loading the Hub index…');
      load();
      return;
    }

    var toks = tokenise(q), res = rank(q), i, r, html, href, kicker;

    if (!res.length) {
      box.innerHTML = note('Nothing on the Hub matches that. ' +
        '<a href="/?s=' + encodeURIComponent(q) + '" style="color:' + GOLD + ';font-weight:700;">' +
        'Search every page and post instead</a>, or try a broader word such as framework, ' +
        'tender, pricing, pathway or glossary.');
      return;
    }

    html = '<div style="padding:8px 14px 4px;color:' + DIM + ';font-size:11px;letter-spacing:1.2px;' +
           'font-weight:700;text-transform:uppercase;">' + res.length +
           (res.length === 1 ? ' match' : ' matches') + ' on the Hub</div>';

    for (i = 0; i < res.length; i++) {
      r = res[i];
      if (r.kind === 'rec') {
        html += row(r.rec.u, r.rec.t, r.rec.c || 'Record', 'Opens the supplier record on the Suppliers page');
      } else {
        href = r.page.u;
        kicker = r.page.t;
        if (r.sec) {
          if (r.sec.a) { href = r.page.u + '#' + r.sec.a; }
          else { href = r.page.u + textFragment(r.sec.h); }
          html += row(href, r.sec.h || r.page.t,
                      r.sec.h && r.sec.h !== r.page.t ? kicker : '',
                      esc(href));
        } else {
          html += row(href, r.page.t, '', esc(href));
        }
      }
    }

    html += '<div style="padding:9px 14px;border-top:1px solid ' + RULE + ';">' +
            '<a href="/?s=' + encodeURIComponent(q) + '" style="color:' + DIM + ';font-size:12px;' +
            'text-decoration:none;">Not what you wanted? Search every page and post →</a></div>';

    box.innerHTML = html;
  }

  // -------------------------------------------------------------------- data
  function load() {
    if (LOADING || DATA || FAILED) { return; }
    LOADING = true;
    var url = INDEX_URL + '?cb=' + Date.now();
    fetch(url, { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.json();
      })
      .then(function (doc) {
        if (!doc || !doc.pages || !doc.pages.length) { throw new Error('empty index'); }
        if (!doc.records) { doc.records = []; }
        DATA = prepare(doc);
        LOADING = false;
        render();
      })
      .catch(function () {
        LOADING = false;
        FAILED = true;
        render();
      });
  }

  // -------------------------------------------------------------------- wire
  shell();

  var timer = null;
  function schedule() {
    if (timer) { clearTimeout(timer); }
    timer = setTimeout(render, 90);
  }

  // The index is fetched on first contact with the box, never on page load, so
  // the Live Desk is not made slower for the members who never search.
  input.addEventListener('focus', load);
  input.addEventListener('input', function () { load(); schedule(); });
  input.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') { return; }
    e.preventDefault();
    var first = box.querySelector('a[href]');
    if (first && box.style.display !== 'none') { window.location.assign(first.getAttribute('href')); }
  });
  document.getElementById('ethHubGo').addEventListener('click', function () {
    var first = box.querySelector('a[href]');
    if (first && box.style.display !== 'none') { window.location.assign(first.getAttribute('href')); return; }
    var q = input.value ? input.value.trim() : '';
    if (q) { window.location.assign('/?s=' + encodeURIComponent(q)); }
  });

  // Lets the page, or a test harness, supply the index directly.
  if (window.MSH_HUB_SEARCH_INDEX) {
    DATA = prepare(window.MSH_HUB_SEARCH_INDEX);
  }
})();
