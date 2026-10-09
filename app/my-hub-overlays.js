/* My Hub overlays: every dialog on the home screen, and the tour (2026-10).
   Markup and behaviour follow the approved mock-up
   (Hub/My-Hub-Home-2026-10/my-hub-mockup.html in Cowork-OS):
     m-tools   All tools: every catalogue page except specialities, for every
               profile (Lou, 01/10/2026), grouped, with a filter and group chips.
     m-search  Search the Hub: the Live Desk's full-text search (app/hub-search.js)
               in an embedded box, loaded the first time this opens.
     m-spec    Your specialities: one choice sets news, library and briefing.
     m-pages   Your pages: browse by profile (Company, Rep, Clinical,
               Procurement, Recruiter, All), each page labelled with the
               profiles whose nav carries it; your own profile only adds a
               starter set, it never limits what you can pick.
     m-brief   Weekly briefing: phase 2. Coming soon; the only action records
               interest on the account and promises nothing by email.
     m-how     How My Hub works, with Replay the tour.
     m-phone   Add to Home Screen, for the checklist.
     m-lib     Which speciality to open the Clinical Evidence Library at,
               when a member has more than one.
   The tour: click-through spotlight, dims the page, one control at a time,
   Back / Next / Skip and "3 of 9". Runs once (tourSeen on the account),
   replays from How it works and the masthead.

   Registers MSH_MYHUB.ui. Loaded by app/my-hub.js. */
(function () {
  'use strict';
  var M = window.MSH_MYHUB;
  if (!M) { return; }
  var L = window.MSH_MYHUB_LOGIC;

  var openId = null, lastFocus = null, tGroup = 'all', pProfile = 'all', draft = [], specDraft = [], searchLoaded = false;
  /* Parked features (the spec parks phone alerts) are never promoted from here:
     not in All tools, Popular pages or the page picker. */
  var PARKED = ['phone-alerts'];
  var POPULAR = ['live-desk', 'tender-history', 'suppliers', 'calendar', 'mhra-regulatory-desk', 'company-report'];

  function esc(s) { return M.esc(s); }
  function href(u) { return esc(L.safeUrl(u)); }
  function listed() { return (M.cat.items || []).filter(function (i) { return PARKED.indexOf(i.id) === -1; }); }
  /* The tools launcher only: narrowed to the member's specialities when the page is. */
  function toolItems() { return L.toolsFor(listed(), M.mine(), M.narrowed()); }
  function popularIds() { return POPULAR.filter(function (id) { return PARKED.indexOf(id) === -1 && !!M.byId[id]; }); }
  function svg(n) { return M.svg(n); }
  function $(sel) { return M.mount.querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || M.mount).querySelectorAll(sel)); }

  function modal(id, size, glyph, title, body, foot) {
    return '<div class="scrim" id="' + id + '" role="dialog" aria-modal="true" aria-labelledby="' + id + '-t"><div class="modal' + (size ? ' ' + size : '') + '">'
      + '<div class="mh"><span class="mi">' + svg(glyph) + '</span><h2 id="' + id + '-t">' + title + '</h2><button type="button" class="icon-btn" data-close aria-label="Close">' + svg('x') + '</button></div>'
      + '<div class="mb">' + body + '</div>' + (foot ? '<div class="mf">' + foot + '</div>' : '') + '</div></div>';
  }
  function field(id, label, placeholder) {
    return '<label class="field">' + svg('search') + '<span class="sr">' + label + '</span><input id="' + id + '" type="search" placeholder="' + placeholder + '" autocomplete="off" spellcheck="false"></label>';
  }

  function modalsHtml() {
    var how = [
      ['steth', '<b>Pick your specialities once.</b> They set your news, library and briefing.'],
      ['filter', '<b>Switch to Everything</b> to see the whole Hub. Safety alerts always show in full.'],
      ['star', '<b>Star anything</b> to keep it under Saved, on any device.'],
      ['search', '<b>Press Ctrl K</b> (Cmd K on a Mac) to search from My Hub.']
    ];
    return modal('m-tools', '', 'grid', 'All tools', field('mx-tf', 'Filter tools', 'Filter tools, for example frameworks')
        + '<div class="chips" id="mx-tchips" role="group" aria-label="Tool groups"></div>'
        + '<p class="scope-note" id="mx-tnote"></p><div id="mx-tgroups"></div>')
      + '<div class="scrim" id="m-search" role="dialog" aria-modal="true" aria-labelledby="m-search-t"><div class="modal sm mx-search">'
      + '<div class="mh"><h2 id="m-search-t" class="sr">Search the Hub</h2><div class="mx-embed" data-hub-search-embed><label class="field">' + svg('search')
      + '<span class="sr">Search the Hub</span><input id="mx-sq" type="search" placeholder="Search every Hub page" autocomplete="off" spellcheck="false"><kbd>Esc</kbd></label></div>'
      + '<button type="button" class="icon-btn" data-close aria-label="Close search">' + svg('x') + '</button></div>'
      + '<div class="mb"><div class="res" id="mx-spop"></div><div class="mx-sres" data-hub-search-results></div></div></div></div>'
      + modal('m-spec', 'sm', 'steth', 'Your specialities', '<p class="mx-lede">One choice sets your news, library and briefing.</p>'
        + '<div class="mx-mt">' + field('mx-spf', 'Filter specialities', 'Filter specialities') + '</div><div class="specs" id="mx-specs"></div>',
        '<small id="mx-spec-n"></small><button type="button" class="btn ghost" data-close>Cancel</button><button type="button" class="btn navy" data-act="spec-save">Save specialities</button>')
      + modal('m-pages', '', 'grid', 'Your pages', '<p class="mx-lede">Pick from any profile. Your own profile only sets where you start.</p>'
        + '<div class="chips" id="mx-pchips" role="group" aria-label="Browse by profile"></div>' + field('mx-pq', 'Search Hub pages', 'Search Hub pages')
        + '<div class="mx-pgrid"><div id="mx-plist"></div><div class="mx-pord"><h3>Your page, in order</h3><ol id="mx-pord"></ol></div></div>',
        '<small id="mx-pn"></small><button type="button" class="btn ghost" data-act="pages-starter">Add my profile\u2019s starter set</button><button type="button" class="btn ghost" data-close>Cancel</button><button type="button" class="btn navy" data-act="pages-save">Save my pages</button>')
      + modal('m-brief', 'sm', 'mail', 'Weekly briefing', '<p class="mx-lede">Every Monday morning, built from your specialities. A section with nothing in it is left out. It has not started yet.</p>'
        + '<label class="opt locked"><input type="checkbox" checked disabled><span><b>Safety alerts</b><span>Always included, for every member</span></span></label>'
        + '<label class="opt locked"><input type="checkbox" checked disabled><span><b>New stories in your specialities</b><span>Only the ones worth your time</span></span></label>'
        + '<label class="opt locked"><input type="checkbox" checked disabled><span><b>Tenders and framework deadlines</b><span>Closing in the next fortnight</span></span></label>'
        + '<label class="opt locked"><input type="checkbox" checked disabled><span><b>Events</b><span>In the next fortnight</span></span></label>',
        '<small id="mx-brief-note">We\u2019ll show it on My Hub when it starts.</small><button type="button" class="btn ghost" data-close>Not now</button><button type="button" class="btn navy" data-act="brief-go" id="mx-brief-go">Tell me when it starts</button>')
      + modal('m-how', 'sm', 'help', 'How My Hub works', '<ul class="howlist">' + how.map(function (h) { return '<li><span class="c">' + svg(h[0]) + '</span><span>' + h[1] + '</span></li>'; }).join('') + '</ul>',
        '<button type="button" class="btn navy" data-act="tour">' + svg('play') + 'Replay the tour</button>')
      + modal('m-phone', 'sm', 'phone', 'Add My Hub to your Home Screen', '<ul class="howlist">'
        + '<li><span class="c">' + svg('phone') + '</span><span>In your phone\u2019s browser, open this page and tap <b>Share</b>, then <b>Add to Home Screen</b>.</span></li>'
        + '<li><span class="c">' + svg('phone') + '</span><span>If you do not see Share, open the browser\u2019s menu and look for <b>Add to Home Screen</b> or <b>Install app</b>.</span></li></ul>',
        '<button type="button" class="btn ghost" data-close>Not now</button><button type="button" class="btn navy" data-act="phone-done">I\u2019ve added it</button>')
      + modal('m-lib', 'sm', 'book', 'Clinical Evidence Library', '<p class="mx-lede">Open the library at one of your specialities.</p><div class="res" id="mx-lib"></div>')
      + '<div class="tour" id="mx-tour" role="dialog" aria-modal="true" aria-labelledby="mx-tip-t" aria-describedby="mx-tip-p"><svg class="dim" aria-hidden="true"><path id="mx-dimp"/></svg>'
      + '<div class="hole" id="mx-hole"></div><div class="tip" id="mx-tip"><i class="arrow" id="mx-tip-arrow"></i><div class="cnt" id="mx-tip-c"></div><h3 id="mx-tip-t"></h3><p id="mx-tip-p"></p>'
      + '<div class="pips" id="mx-tip-pips" aria-hidden="true"></div><div class="tf"><button type="button" class="skip" id="mx-t-skip">Skip</button>'
      + '<button type="button" class="btn ghost" id="mx-t-back">Back</button><button type="button" class="btn navy" id="mx-t-next">Next</button></div></div></div>';
  }

  /* ---------- open, close, focus ---------- */
  function open(id, opener) {
    if (openId) { close(); }
    var m = document.getElementById(id);
    if (!m) { return; }
    lastFocus = opener || document.activeElement;
    openId = id;
    if (!m.classList.contains('open')) { m.classList.add('open'); }
    if (id === 'm-tools') { tGroup = 'all'; $('#mx-tf').value = ''; toolChips(); renderTools(); }
    if (id === 'm-search') { $('#mx-sq').value = ''; popular(); loadSearch(); }
    if (id === 'm-spec') { specDraft = M.specIds().slice(); $('#mx-spf').value = ''; renderSpecs(); }
    if (id === 'm-pages') { draft = M.visiblePins().slice(); pProfile = 'all'; $('#mx-pq').value = ''; pageChips(); renderPages(); }
    if (id === 'm-brief') { briefFoot(); }
    var f = m.querySelector('input:not([disabled])') || m.querySelector('button:not([disabled])');
    setTimeout(function () { if (f) { f.focus(); } }, 30);
  }
  function close() {
    if (!openId) { return; }
    var m = document.getElementById(openId);
    if (m) { if (m.classList.contains('open')) { m.classList.remove('open'); } }
    openId = null;
    if (lastFocus) { if (lastFocus.focus) { if (document.body.contains(lastFocus)) { lastFocus.focus(); } } }
  }
  function focusables(m) {
    return $$('button:not([disabled]),input:not([disabled]),a[href],textarea', m).filter(function (x) { return x.offsetParent !== null; });
  }

  /* ---------- tools ---------- */
  function toolGroups() { return (M.cat.groups || []).filter(function (g) { return g.id !== 'specialities'; }); }
  function toolChips() {
    $('#mx-tchips').innerHTML = '<button type="button" class="chip" data-g="all" aria-pressed="' + (tGroup === 'all') + '">All</button>'
      + toolGroups().map(function (g) { return '<button type="button" class="chip" data-g="' + esc(g.id) + '" aria-pressed="' + (tGroup === g.id) + '">' + esc(g.label) + '</button>'; }).join('');
  }
  function toolNote() {
    var n = M.narrowed(), note = $('#mx-tnote');
    var had = !!(note && document.activeElement && note.contains(document.activeElement));
    $('#mx-tnote').innerHTML = svg('filter') + (n
      ? '<span>Showing tools for your specialities. Everything shows the rest. <button type="button" class="mx-link" data-scope="all" data-k="tools-all">Show Everything</button></span>'
      : '<span>Every Hub tool, whichever profile you chose.</span>');
    if (had) { $('#mx-tf').focus(); }   // the button just rewrote itself away: keep focus in the launcher
  }
  function renderTools() {
    toolNote();
    var q = String($('#mx-tf').value || '').toLowerCase().trim();
    var shown = toolItems();
    var html = toolGroups().filter(function (g) { return tGroup === 'all' ? true : g.id === tGroup; }).map(function (g) {
      var items = shown.filter(function (i) { return i.group === g.id ? (!q ? true : i.label.toLowerCase().indexOf(q) !== -1) : false; });
      if (!items.length) { return ''; }
      return '<div class="tgroup"><h3>' + esc(g.label) + '</h3><div class="tgrid">' + items.map(function (i) {
        return '<a class="tl k-' + esc(i.kind || 'tool') + '" href="' + href(i.url) + '"><span class="ti">' + svg(M.I.forItem(i)) + '</span>' + esc(i.label) + '</a>';
      }).join('') + '</div></div>';
    }).join('');
    $('#mx-tgroups').innerHTML = html || '<p class="empty mx-mt">No tool matches \u201c' + esc(q) + '\u201d. Try Search to look through every Hub page.</p>';
  }

  /* ---------- search ---------- */
  function popular() {
    var box = $('#mx-spop');
    box.style.display = '';
    box.innerHTML = '<h3>Popular pages</h3>' + popularIds().map(function (id) {
      var it = M.byId[id];
      return '<a class="k-' + esc(it.kind || 'tool') + '" href="' + href(it.url) + '">' + svg(M.I.forItem(it)) + esc(it.label) + '</a>';
    }).join('');
  }
  function loadSearch() {
    if (searchLoaded) { return; }
    searchLoaded = true;
    fetch(M.base + 'app/hub-search.js', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) { throw new Error(r.status); } return r.text(); })
      .then(function (s) { (new Function(s))(); })
      .catch(function () {
        searchLoaded = false;
        var b = $('[data-hub-search-results]');
        b.style.display = 'block';
        b.innerHTML = '<p class="empty mx-pad">Search is unavailable just now. Try again in a minute.</p>';
      });
  }

  /* ---------- specialities ---------- */
  function renderSpecs() {
    var q = String($('#mx-spf').value || '').toLowerCase();
    var list = listed().filter(function (i) { return i.group === 'specialities' ? (!q ? true : i.label.toLowerCase().indexOf(q) !== -1) : false; });
    $('#mx-specs').innerHTML = list.map(function (i) {
      return '<label><input type="checkbox" data-spec="' + esc(i.id) + '"' + (specDraft.indexOf(i.id) !== -1 ? ' checked' : '') + '>' + esc(i.label) + '</label>';
    }).join('') || '<p class="empty">No speciality matches that. Try a shorter word.</p>';
    $('#mx-spec-n').textContent = specDraft.length + ' chosen';
  }
  function saveSpecs() {
    var keep = M.visiblePins().filter(function (id) { return M.byId[id].group !== 'specialities' ? true : specDraft.indexOf(id) !== -1; });
    specDraft.forEach(function (id) { if (keep.indexOf(id) === -1) { keep.push(id); } });
    close();
    M.setPins(keep).then(function () { M.toast(specDraft.length ? 'Specialities saved.' : 'Showing the whole Hub.'); });
  }

  /* ---------- your pages ---------- */
  function pageChips() {
    var prof = M.cat.profiles || {};
    $('#mx-pchips').innerHTML = '<button type="button" class="chip" data-pf="all" aria-pressed="' + (pProfile === 'all') + '">All</button>'
      + Object.keys(prof).map(function (k) { return '<button type="button" class="chip" data-pf="' + esc(k) + '" aria-pressed="' + (pProfile === k) + '">' + esc(prof[k]) + '</button>'; }).join('');
  }
  function renderPages() {
    var prof = M.cat.profiles || {}, q = String($('#mx-pq').value || '').toLowerCase().trim();
    var items = L.byProfile(listed(), pProfile).filter(function (i) { return !q ? true : i.label.toLowerCase().indexOf(q) !== -1; });
    var html = (M.cat.groups || []).map(function (g) {
      var rows = items.filter(function (i) { return i.group === g.id; });
      if (!rows.length) { return ''; }
      return '<div class="mx-pgroup"><h3>' + esc(g.label) + '</h3>' + rows.map(function (i) {
        var tags = g.id === 'specialities' ? '<span class="mx-ptag">Every profile</span>'
          : (i.profiles || []).map(function (p) { return '<span class="mx-ptag">' + esc(prof[p] || p) + '</span>'; }).join('');
        return '<label class="mx-prow"><input type="checkbox" data-pick="' + esc(i.id) + '"' + (draft.indexOf(i.id) !== -1 ? ' checked' : '') + '><span><b>' + esc(i.label) + '</b>'
          + (tags ? '<span class="mx-ptags">' + tags + '</span>' : '') + '</span></label>';
      }).join('') + '</div>';
    }).join('');
    $('#mx-plist').innerHTML = html || '<p class="empty mx-mt">No Hub page matches \u201c' + esc(q) + '\u201d.</p>';
    renderOrder();
  }
  function renderOrder() {
    var ord = draft.filter(function (id) { return !!M.byId[id]; });
    $('#mx-pord').innerHTML = ord.length ? ord.map(function (id, i) {
      return '<li><span>' + esc(M.byId[id].label) + '</span>'
        + '<button type="button" data-mv="' + i + '" data-d="-1" aria-label="Move ' + esc(M.byId[id].label) + ' up"' + (i ? '' : ' disabled') + '>' + svg('up') + '</button>'
        + '<button type="button" data-mv="' + i + '" data-d="1" aria-label="Move ' + esc(M.byId[id].label) + ' down"' + (i !== ord.length - 1 ? '' : ' disabled') + '>' + svg('down') + '</button>'
        + '<button type="button" data-rm="' + esc(id) + '" aria-label="Remove ' + esc(M.byId[id].label) + '">' + svg('x') + '</button></li>';
    }).join('') : '<li class="empty">Nothing chosen yet.</li>';
    $('#mx-pn').textContent = ord.length + ' chosen';
  }
  function starter() {
    var ids = (M.cat.profileStarters || {})[M.route()] || [];
    if (!ids.length) { M.toast('Choose your profile first, then add its starter set.'); return; }
    ids.forEach(function (id) { if (M.byId[id]) { if (draft.indexOf(id) === -1) { draft.push(id); } } });
    renderPages();
  }
  function savePages() {
    var list = draft.filter(function (id) { return !!M.byId[id]; });
    close();
    M.setPins(list).then(function () { M.toast(M.acct.where === 'account' ? 'Saved to your account.' : 'Saved on this device only.'); });
  }

  /* ---------- briefing ---------- */
  function briefFoot() {
    var on = M.acct.state.briefing, go = $('#mx-brief-go');
    go.style.display = on ? 'none' : '';
    $('#mx-brief-note').textContent = on ? 'You\u2019re on the list. We\u2019ll show it on My Hub when it starts.' : 'We\u2019ll show it on My Hub when it starts.';
  }

  /* ---------- library chooser ---------- */
  function openLibrary(targets) {
    $('#mx-lib').innerHTML = targets.map(function (t) { return '<a href="' + href(t.url) + '">' + svg('book') + esc(t.label) + '</a>'; }).join('')
      + '<a href="/medical-sales-hub/clinical-evidence-library/">' + svg('book') + 'All specialities</a>';
    open('m-lib');
  }

  /* ---------- the tour ---------- */
  var STEPS = [
    ['spec', 'Your specialities', 'Choose the specialities you sell into. That one choice sets your news, library and briefing.'],
    ['scope', 'My specialities or Everything', 'Narrow the page to your specialities, or switch to the whole Hub. Safety alerts always show in full.'],
    ['tools', 'Tools', 'Every Hub tool in one place, grouped and searchable.'],
    ['library', 'Clinical Evidence Library', 'Studies and guidance for your specialities, ready for a customer conversation.'],
    ['briefing', 'Weekly briefing', 'A Monday email with what changed in your specialities. Coming soon.'],
    ['saved', 'Saved', 'Anything you star lands here, on every device you use.'],
    ['search', 'Search', 'Search every Hub page. Press Ctrl K on My Hub to jump straight here.'],
    ['how', 'How it works', 'A one-minute guide, and the place to replay this tour.'],
    ['new', 'What\u2019s new', 'New tools and changes to the Hub. The number shows what you haven\u2019t seen yet.']
  ];
  var tourOn = false, ti = 0, tourFrom = null;
  function startTour(i) {
    close();
    tourFrom = document.activeElement;
    tourOn = true;
    var t = $('#mx-tour');
    if (!t.classList.contains('on')) { t.classList.add('on'); }
    $('#mx-tip-pips').innerHTML = STEPS.map(function () { return '<i></i>'; }).join('');
    window.scrollTo(0, 0);
    show(i || 0);
  }
  function endTour(finished) {
    tourOn = false;
    var t = $('#mx-tour');
    if (t.classList.contains('on')) { t.classList.remove('on'); }
    var patch = { tourSeen: true };
    if (finished) { patch.tour = true; }
    M.saveState(patch);
    if (tourFrom) { if (tourFrom.focus) { if (document.body.contains(tourFrom)) { tourFrom.focus(); } } }
  }
  /* Which step to show: from i, step in dir (1 or -1) to the first one whose
     target is present; if none that way, look the other way; -1 when no step
     has a target at all. Pure, so it is tested without a DOM. */
  function pickStep(i, dir, present) {
    var n = present.length, k;
    i = Math.max(0, Math.min(n - 1, i));
    for (k = i; k >= 0 && k < n; k += dir) { if (present[k]) { return k; } }
    for (k = i - dir; k >= 0 && k < n; k -= dir) { if (present[k]) { return k; } }
    return -1;
  }
  function closeTourQuietly() {
    tourOn = false;
    var t = $('#mx-tour');
    if (t.classList.contains('on')) { t.classList.remove('on'); }
    if (tourFrom) { if (tourFrom.focus) { if (document.body.contains(tourFrom)) { tourFrom.focus(); } } }
  }
  function lastStep() {
    var last = -1;
    STEPS.forEach(function (st, n) { if (M.mount.querySelector('[data-tour="' + st[0] + '"]')) { last = n; } });
    return last;
  }
  function show(i, dir) {
    var present = STEPS.map(function (st) { return !!M.mount.querySelector('[data-tour="' + st[0] + '"]'); });
    var pick = pickStep(i, dir || 1, present);
    if (pick === -1) { closeTourQuietly(); return; }
    ti = pick;
    var lastPresent = present.lastIndexOf(true), firstPresent = present.indexOf(true);
    var s = STEPS[ti], el = M.mount.querySelector('[data-tour="' + s[0] + '"]');
    var r = el.getBoundingClientRect(), pad = 6;
    if (r.top < 70 || r.bottom > innerHeight - 200) { el.scrollIntoView({ block: 'center' }); r = el.getBoundingClientRect(); }
    var hole = $('#mx-hole'), tip = $('#mx-tip');
    hole.style.cssText = 'top:' + (r.top - pad) + 'px;left:' + (r.left - pad) + 'px;width:' + (r.width + pad * 2) + 'px;height:' + (r.height + pad * 2) + 'px';
    var x = r.left - pad, y = r.top - pad, w = r.width + pad * 2, hh = r.height + pad * 2, k = 16, W = innerWidth, H = innerHeight;
    $('#mx-dimp').setAttribute('d', 'M0 0H' + W + 'V' + H + 'H0Z M' + (x + k) + ' ' + y + 'H' + (x + w - k) + 'Q' + (x + w) + ' ' + y + ' ' + (x + w) + ' ' + (y + k)
      + 'V' + (y + hh - k) + 'Q' + (x + w) + ' ' + (y + hh) + ' ' + (x + w - k) + ' ' + (y + hh) + 'H' + (x + k) + 'Q' + x + ' ' + (y + hh) + ' ' + x + ' ' + (y + hh - k)
      + 'V' + (y + k) + 'Q' + x + ' ' + y + ' ' + (x + k) + ' ' + y + 'Z');
    $('#mx-tip-c').textContent = (ti + 1) + ' of ' + STEPS.length;
    $('#mx-tip-t').textContent = s[1];
    $('#mx-tip-p').textContent = s[2];
    $$('#mx-tip-pips i').forEach(function (p, n) {
      var on = n <= ti, has = p.classList.contains('on');
      if (on) { if (!has) { p.classList.add('on'); } } else { if (has) { p.classList.remove('on'); } }
    });
    $('#mx-t-back').style.visibility = ti === firstPresent ? 'hidden' : 'visible';
    $('#mx-t-next').textContent = ti === lastPresent ? 'Finish' : 'Next';
    var tw = Math.min(320, innerWidth - 32), th = tip.offsetHeight || 190;
    var left = Math.max(16, Math.min(r.left + r.width / 2 - tw / 2, innerWidth - tw - 16));
    var below = r.bottom + pad + 14 + th < innerHeight;
    var top = below ? r.bottom + pad + 14 : r.top - pad - 14 - th;
    if (below) { if (tip.classList.contains('above')) { tip.classList.remove('above'); } } else { if (!tip.classList.contains('above')) { tip.classList.add('above'); } }
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
    $('#mx-tip-arrow').style.left = Math.max(18, Math.min(r.left + r.width / 2 - left - 7, tw - 32)) + 'px';
    $('#mx-t-next').focus();
  }

  /* ---------- events ---------- */
  var wired = false;
  function wire() {
    if (wired) { return; }
    wired = true;
    M.mount.addEventListener('click', function (e) {
      var t = e.target;
      if (t.classList) { if (t.classList.contains('scrim')) { close(); return; } }
      var c = t.closest ? t.closest('[data-close],[data-g],[data-pf],[data-mv],[data-rm],#mx-t-next,#mx-t-back,#mx-t-skip,[data-act="spec-save"],[data-act="pages-save"],[data-act="pages-starter"],[data-act="brief-go"],[data-act="phone-done"]') : null;
      if (!c) { return; }
      if (c.hasAttribute('data-close')) { close(); return; }
      if (c.hasAttribute('data-g')) {
        tGroup = c.getAttribute('data-g');
        $$('#mx-tchips .chip').forEach(function (x) { x.setAttribute('aria-pressed', String(x === c)); });
        renderTools(); return;
      }
      if (c.hasAttribute('data-pf')) {
        pProfile = c.getAttribute('data-pf');
        $$('#mx-pchips .chip').forEach(function (x) { x.setAttribute('aria-pressed', String(x === c)); });
        renderPages(); return;
      }
      if (c.hasAttribute('data-mv')) {
        var ord = draft.filter(function (id) { return !!M.byId[id]; }), i = +c.getAttribute('data-mv'), j = i + (+c.getAttribute('data-d'));
        if (j < 0) { return; }
        if (j >= ord.length) { return; }
        var tmp = ord[i]; ord[i] = ord[j]; ord[j] = tmp; draft = ord; renderOrder(); return;
      }
      if (c.hasAttribute('data-rm')) {
        var rid = c.getAttribute('data-rm');
        draft = draft.filter(function (x) { return x !== rid; });
        renderPages(); return;
      }
      if (c.id === 'mx-t-next') { if (ti >= lastStep()) { endTour(true); } else { show(ti + 1, 1); } return; }
      if (c.id === 'mx-t-back') { show(ti - 1, -1); return; }
      if (c.id === 'mx-t-skip') { endTour(false); return; }
      var act = c.getAttribute('data-act');
      if (act === 'spec-save') { saveSpecs(); return; }
      if (act === 'pages-save') { savePages(); return; }
      if (act === 'pages-starter') { starter(); return; }
      if (act === 'brief-go') { close(); M.saveState({ briefing: true }).then(function () { M.toast('You\u2019re on the list.'); }); return; }
      if (act === 'phone-done') { close(); M.saveState({ phone: true }).then(function () { M.toast('Done. Open My Hub from your Home Screen.'); }); }
    });
    M.mount.addEventListener('change', function (e) {
      var t = e.target;
      if (t.hasAttribute('data-spec')) {
        var id = t.getAttribute('data-spec');
        if (t.checked) { if (specDraft.indexOf(id) === -1) { specDraft.push(id); } } else { specDraft = specDraft.filter(function (x) { return x !== id; }); }
        $('#mx-spec-n').textContent = specDraft.length + ' chosen';
        return;
      }
      if (t.hasAttribute('data-pick')) {
        var pid = t.getAttribute('data-pick');
        if (t.checked) { if (draft.indexOf(pid) === -1) { draft.push(pid); } } else { draft = draft.filter(function (x) { return x !== pid; }); }
        renderOrder();
      }
    });
    M.mount.addEventListener('input', function (e) {
      var id = e.target.id;
      if (id === 'mx-tf') { renderTools(); }
      if (id === 'mx-spf') { renderSpecs(); }
      if (id === 'mx-pq') { renderPages(); }
      if (id === 'mx-sq') { $('#mx-spop').style.display = e.target.value.trim().length > 1 ? 'none' : ''; }
    });
    document.addEventListener('keydown', function (e) {
      var k = String(e.key || '').toLowerCase();
      if (k === 'k') {
        if (e.ctrlKey || e.metaKey) { e.preventDefault(); if (tourOn) { endTour(false); } open('m-search'); return; }
      }
      if (e.key === 'Escape') { if (tourOn) { endTour(false); return; } close(); return; }
      if (tourOn) {
        if (e.key === 'Tab') {
          var tf = ['mx-t-back', 'mx-t-next', 'mx-t-skip'].map(function (x) { return document.getElementById(x); })
            .filter(function (x) { return x ? getComputedStyle(x).visibility !== 'hidden' : false; });
          if (tf.length) {
            e.preventDefault();
            var at = tf.indexOf(document.activeElement), nx = at === -1 ? 0 : at + (e.shiftKey ? -1 : 1);
            tf[(nx + tf.length) % tf.length].focus();
          }
          return;
        }
        if (e.key === 'ArrowRight') { $('#mx-t-next').click(); }
        if (e.key === 'ArrowLeft') { if (ti > 0) { show(ti - 1, -1); } }
        return;
      }
      if (e.key === 'Tab') {
        if (!openId) { return; }
        var f = focusables(document.getElementById(openId));
        if (!f.length) { return; }
        var a = f[0], z = f[f.length - 1];
        if (e.shiftKey) { if (document.activeElement === a) { e.preventDefault(); z.focus(); } }
        else { if (document.activeElement === z) { e.preventDefault(); a.focus(); } }
      }
    });
    window.addEventListener('resize', function () { if (tourOn) { show(ti, 1); } });
  }

  /* The ids each list offers, without touching the DOM (tests read this). */
  function lists() {
    return {
      tools: toolGroups().reduce(function (a, g) { return a.concat(toolItems().filter(function (i) { return i.group === g.id; }).map(function (i) { return i.id; })); }, []),
      popular: popularIds(),
      picker: listed().map(function (i) { return i.id; })
    };
  }

  M.ui = { refreshTools: function () { if (openId === 'm-tools') { renderTools(); } }, pickStep: pickStep, lists: lists, modalsHtml: modalsHtml, wire: wire, open: open, close: close, startTour: startTour, openLibrary: openLibrary, isTourOn: function () { return tourOn; } };
})();
