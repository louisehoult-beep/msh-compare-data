/* My Hub company brief: "What you should know" (2026-10).
   A member ticks the companies they work for (up to five). My Hub then shows,
   for each: its top news, the facts that bear on it, and the same for its
   closest competitors. Specialities still narrow Key news and On the desk;
   this block follows the company.

   DATA, read-only, built by scripts/build_company_key_info.py from files the
   Hub already publishes, so every line carries its own source and date:
     data/company-key-info/index.json   the picker: id, name, aliases
     data/company-key-info/<id>.json    one company: head (top news), f (facts),
                                        comp (competitors, each with facts)
   The ticks live on the member's account (state.companies, app/hub-account.js).
   A file that fails to load shows an honest "could not load", never old copy.

   Registers MSH_MYHUB.company = { load, html, modalHtml, openPicker }.
   Loaded by app/my-hub.js, before app/my-hub-overlays.js. */
(function () {
  'use strict';
  var M = window.MSH_MYHUB;
  if (!M) { return; }
  var L = window.MSH_MYHUB_LOGIC;

  var MAX = 5, PICK_SHOWN = 40, FACTS_SHOWN = 6;
  var KINDS = { news: 'News', tariff: 'Drug Tariff', discontinued: 'Still on formularies', share: 'Market share', award: 'Contract award', framework: 'Framework', formulary: 'Formulary' };
  var INDEX = null;               // null loading, false failed, else { built, companies }
  var CO = {};                    // id -> data | false (failed) | undefined (not asked yet)
  var draft = [], expanded = {};

  function esc(s) { return M.esc(s); }
  function svg(n) { return M.svg(n); }
  function ids() { return (M.acct && M.acct.state && M.acct.state.companies) || []; }
  function raw(path) {
    return fetch(M.base + path, { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error(path + ' ' + r.status); } return r.json(); });
  }
  function repaint() { var el = document.getElementById('mx-know'); if (el) { el.innerHTML = html(); } }
  function stamp(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ''));
    if (!m) { return ''; }
    var mon = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][+m[2] - 1];
    return (+m[3]) + ' ' + mon + ' ' + m[1];
  }

  /* ---------- loading ---------- */
  function load() {
    ids().forEach(function (id) {
      if (CO[id] !== undefined) { return; }
      CO[id] = null;
      raw('data/company-key-info/' + encodeURIComponent(id) + '.json')
        .then(function (d) { CO[id] = d; }, function () { CO[id] = false; })
        .then(repaint);
    });
  }
  function loadIndex() {
    if (INDEX !== null) { return; }
    raw('data/company-key-info/index.json').then(function (d) { INDEX = d; }, function () { INDEX = false; }).then(renderPick);
  }

  /* ---------- the block ---------- */
  function factLi(f, withKind) {
    var u = f.u ? L.safeUrl(f.u) : '';
    var meta = [f.s, ['news', 'tariff', 'discontinued', 'formulary', 'award'].indexOf(f.k) !== -1 ? stamp(f.d) : ''].filter(Boolean).join(', ');
    return '<li><span class="kt k-' + esc(f.k) + '">' + esc(KINDS[f.k] || 'Note') + '</span><div><b>'
      + (u ? '<a href="' + esc(u) + '"' + (/^\//.test(u) ? '' : ' target="_blank" rel="noopener"') + '>' + esc(f.t) + '</a>' : esc(f.t)) + '</b>'
      + (f.x ? '<p>' + esc(f.x) + '</p>' : '') + (meta ? '<small>' + esc(meta) + '</small>' : '') + '</div></li>';
  }
  function listOf(facts, key, shown) {
    var open = expanded[key], rows = open ? facts : facts.slice(0, shown);
    return '<ul class="kn-l">' + rows.map(factLi).join('') + '</ul>'
      + (facts.length > shown ? '<button type="button" class="mx-link" data-know="' + esc(key) + '" data-k="kn-' + esc(key) + '">'
        + (open ? 'Show fewer' : 'Show all ' + facts.length) + '</button>' : '');
  }
  function companyHtml(id) {
    var d = CO[id];
    if (d === null || d === undefined) { return '<section class="kn-co" aria-busy="true"><p class="kn-note">Loading what you should know.</p></section>'; }
    if (d === false) { return '<section class="kn-co"><p class="kn-note">Could not load this company just now. Try again in a minute.</p></section>'; }
    var rest = d.f.filter(function (f) { return d.head.indexOf(f) === -1 && !d.head.some(function (h) { return h.t === f.t; }); });
    var h = '<section class="kn-co" aria-labelledby="kn-' + esc(id) + '"><h3 id="kn-' + esc(id) + '">' + esc(d.n) + '</h3>';
    h += '<div class="kn-sub">Top news for you</div>'
      + (d.head.length ? '<ul class="kn-l">' + d.head.map(factLi).join('') + '</ul>'
        : '<p class="kn-note">Nothing new about ' + esc(d.n) + ' in the Hub’s sources in the last four months.</p>');
    if (rest.length) { h += '<div class="kn-sub">What else you should know</div>' + listOf(rest, id + '-f', FACTS_SHOWN); }
    if (d.comp.length) {
      h += '<div class="kn-sub">Your competitors</div><div class="kn-comps">' + d.comp.map(function (c) {
        return '<div class="kn-c"><h4>' + esc(c.n) + '</h4><p class="kn-why">' + esc(c.why) + '</p><ul class="kn-l">' + c.f.map(factLi).join('') + '</ul></div>';
      }).join('') + '</div>';
    }
    return h + '<p class="kn-foot">Built ' + esc(stamp(d.built)) + ' from the Hub’s own data. Each line links to its source.</p></section>';
  }
  function html() {
    var mine = ids();
    if (!mine.length) {
      return '<section class="card know kn-empty" aria-labelledby="mx-kn-t"><div><h2 id="mx-kn-t">What you should know</h2>'
        + '<p>Tell us which company you work for. We’ll show its top news, what affects it, and what its competitors are doing.</p></div>'
        + '<button type="button" class="btn navy" data-open="m-company" data-k="kn-pick">' + svg('grid') + 'Choose your company</button></section>';
    }
    return '<section class="card know" aria-labelledby="mx-kn-t"><div class="sec-h"><h2 id="mx-kn-t">What you should know</h2>'
      + '<span class="n">' + mine.length + (mine.length === 1 ? ' company' : ' companies') + '</span>'
      + '<button type="button" class="more" data-open="m-company" data-k="kn-edit">Change</button></div>'
      + mine.map(companyHtml).join('') + '</section>';
  }

  /* ---------- the picker ---------- */
  function modalHtml() {
    return '<div class="scrim" id="m-company" role="dialog" aria-modal="true" aria-labelledby="m-company-t"><div class="modal sm">'
      + '<div class="mh"><span class="mi">' + svg('grid') + '</span><h2 id="m-company-t">Your company</h2><button type="button" class="icon-btn" data-close aria-label="Close">' + svg('x') + '</button></div>'
      + '<div class="mb"><p class="mx-lede">Tick the companies you work for, up to five. My Hub shows their news, what affects them and what their competitors are doing.</p>'
      + '<label class="field">' + svg('search') + '<span class="sr">Find a company</span><input id="mx-cf" type="search" placeholder="Type your company name" autocomplete="off" spellcheck="false"></label>'
      + '<div class="specs cos" id="mx-cos" role="group" aria-label="Companies"></div></div>'
      + '<div class="mf"><small id="mx-co-n"></small><button type="button" class="btn ghost" data-close>Cancel</button><button type="button" class="btn navy" data-act="company-save" id="mx-co-save">Save</button></div>'
      + '</div></div>';
  }
  function openPicker() {
    draft = ids().slice();
    var f = document.getElementById('mx-cf');
    if (f) { f.value = ''; }
    loadIndex();
    renderPick();
  }
  function nameOf(id) {
    var c = INDEX ? INDEX.companies.filter(function (x) { return x.id === id; })[0] : null;
    return c ? c.n : (CO[id] ? CO[id].n : id);
  }
  function renderPick() {
    var box = document.getElementById('mx-cos'), note = document.getElementById('mx-co-n');
    if (!box) { return; }
    var q = String((document.getElementById('mx-cf') || {}).value || '').toLowerCase().trim();
    var rows = [];
    if (INDEX === null) { box.innerHTML = '<p class="kn-note">Loading companies.</p>'; return; }
    if (INDEX === false) { box.innerHTML = '<p class="kn-note">Could not load the company list just now.</p>'; return; }
    var chosen = draft.map(function (id) { return { id: id, n: nameOf(id) }; });
    if (q) {
      rows = INDEX.companies.filter(function (c) {
        return c.n.toLowerCase().indexOf(q) !== -1 || (c.a || []).some(function (a) { return a.indexOf(q) !== -1; });
      }).slice(0, PICK_SHOWN);
    } else { rows = chosen; }
    var full = draft.length >= MAX;
    box.innerHTML = rows.length ? rows.map(function (c) {
      var on = draft.indexOf(c.id) !== -1;
      return '<label><input type="checkbox" data-co="' + esc(c.id) + '"' + (on ? ' checked' : '') + (!on && full ? ' disabled' : '') + '>' + esc(c.n) + '</label>';
    }).join('') : '<p class="kn-note">' + (q ? 'No company matches that. Try a shorter name or a brand.' : 'Type your company name to find it.') + '</p>';
    if (note) { note.textContent = draft.length + ' of ' + MAX + ' chosen' + (full ? ', the most you can choose' : ''); }
  }
  function save() {
    var list = draft.slice(0, MAX);
    if (M.ui) { M.ui.close(); }
    M.saveState({ companies: list }).then(function () {
      load();
      M.toast(M.acct.where === 'account' ? 'Saved to your account.' : 'Saved on this device only.');
    });
  }

  M.mount.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('[data-know],[data-act="company-save"]') : null;
    if (!t) { return; }
    if (t.hasAttribute('data-know')) {
      var k = t.getAttribute('data-know');
      expanded[k] = !expanded[k];
      repaint();
      return;
    }
    save();
  });
  M.mount.addEventListener('change', function (e) {
    var t = e.target;
    if (!t || !t.getAttribute || !t.hasAttribute('data-co')) { return; }
    var id = t.getAttribute('data-co'), i = draft.indexOf(id);
    if (t.checked) { if (i === -1) { if (draft.length < MAX) { draft.push(id); } } } else { if (i !== -1) { draft.splice(i, 1); } }
    renderPick();
  });
  M.mount.addEventListener('input', function (e) { if (e.target && e.target.id === 'mx-cf') { renderPick(); } });

  M.company = { load: load, html: html, modalHtml: modalHtml, openPicker: openPicker };
})();
