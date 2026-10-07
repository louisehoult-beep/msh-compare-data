/* Medical Sales Hub: My Hub, the member's home screen (rebuilt 2026-10).
   Spec: 02-Elevate-and-Thrive/Hub/My-Hub-Home-2026-10/SPEC.md, phase 1.
   Approved mock-up: my-hub-mockup.html in the same folder (01/10/2026); on
   phones What's new opens as a slim one-line strip.

   Page 4404 (/medical-sales-hub/my-hub/) carries a loader only
   (hub/pages/my-hub.html). This file loads the rest from this repo, in order:
     app/hub-icons.js        one icon per Hub page, shared with the nav
     app/hub-account.js      the member's saved state (/wp-json/msh/v1/my-hub)
     app/my-hub-logic.js     pure functions (test_my_hub_logic.py)
     app/my-hub-feeds.js     Key news and On the desk
     app/my-hub-overlays.js  tools, search, specialities, pages, briefing, tour
     app/my-hub.css          the mock-up's design, scoped to #msh-my-hub
   plus hub/my-hub-catalogue.json and hub/whats-new.json, then draws:
     masthead (greeting, date, specialities, What's new), the fixed icon bar
     (Specialities, My specialities / Everything, Tools, Evidence Library,
     Weekly briefing, Saved, Search, How it works, What's new), the
     getting-started checklist, Key news and On the desk, and a side column
     (Your pages, Saved, the Monday briefing panel), a footer, and the phone
     tab bar (Home, Tools, Library, Briefing, Search).

   BASE is the one place the repo address lives. When msh-compare-data moves
   behind the WordPress proxy (Hub/repo-private-migration-plan-2026-09-29.md,
   option A) this line and the page loader change, nothing else.
   window.MSH_MYHUB_BASE overrides it for the local preview only. */
(function () {
  'use strict';
  var mount = document.getElementById('msh-my-hub');
  if (!mount) { return; }
  if (mount.getAttribute('data-mhx') === '1') { return; }
  mount.setAttribute('data-mhx', '1');

  var BASE = window.MSH_MYHUB_BASE || 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var MODULES = ['app/hub-icons.js', 'app/hub-account.js', 'app/my-hub-logic.js', 'app/my-hub-feeds.js', 'app/my-hub-overlays.js'];
  var WN_WINDOW = 60;   // days a What's new entry stays news
  var M = window.MSH_MYHUB = { base: BASE, mount: mount };

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  /* A fetch that has not answered (headers and body) within 15 seconds counts
     as failed, so a hung request reaches the honest error, not an endless
     "Loading". AbortController cancels it where the browser has one; the
     timer alone settles the promise where it does not. */
  var TIMEOUT_MS = 15000;
  function timed(url, opts, read) {
    var ctl = null;
    try { ctl = typeof AbortController === 'function' ? new AbortController() : null; } catch (e) { ctl = null; }
    if (ctl) { opts.signal = ctl.signal; }
    return new Promise(function (resolve, reject) {
      var done = false;
      var timer = setTimeout(function () {
        if (done) { return; }
        done = true;
        if (ctl) { try { ctl.abort(); } catch (e) {} }
        reject(new Error(url + ' timed out'));
      }, TIMEOUT_MS);
      fetch(url, opts).then(function (r) { if (!r.ok) { throw new Error(url + ' ' + r.status); } return read(r); })
        .then(function (v) { if (done) { return; } done = true; clearTimeout(timer); resolve(v); },
          function (e) { if (done) { return; } done = true; clearTimeout(timer); reject(e); });
    });
  }
  function text(path) {
    return timed(BASE + path, { cache: 'no-cache' }, function (r) { return r.text(); });
  }
  function nonce() { return window.mshRestNonce || window.mshPrefsNonce || ''; }
  function getJSON(url) {
    return timed(url, { credentials: 'same-origin', headers: { 'X-WP-Nonce': nonce() } }, function (r) { return r.json(); });
  }
  function setHtml(id, h) { var el = document.getElementById(id); if (el) { el.innerHTML = h; } }
  function fail() {
    mount.innerHTML = '<p class="mx-fail">My Hub is unavailable just now. Try the <a href="/medical-sales-hub/?desk=1">Live Desk</a>.</p>';
  }

  /* ---------- the member ---------- */
  M.esc = esc;
  M.specIds = function () { return M.pins.filter(function (id) { return M.byId[id] ? M.byId[id].group === 'specialities' : false; }); };
  M.mine = function () { var o = {}; M.specIds().forEach(function (id) { o[id] = 1; }); return o; };
  M.narrowed = function () { return M.acct.state.scope === 'mine' ? M.specIds().length > 0 : false; };
  M.visiblePins = function () { return M.pins.filter(function (id) { return !!M.byId[id]; }); };
  M.route = function () {
    var r = null;
    try { r = localStorage.getItem('msh-route'); } catch (e) {}
    var p = M.cat.profiles || {};
    if (r) { if (Object.prototype.hasOwnProperty.call(p, r)) { return r; } }
    return Object.prototype.hasOwnProperty.call(p, M.prefsRoute || '') ? M.prefsRoute : null;
  };
  M.byUrl = function (u) {
    var p = String(u || '').split('#')[0].split('?')[0];
    return M.urlMap[p] || null;
  };
  M.setPins = function (list) {
    var keep = M.pins.filter(function (id) { return !M.byId[id]; });   // retired pages stay stored, unseen
    M.pins = list.concat(keep);
    M.seeded = false;
    return M.A.savePins(M.pins).then(function (a) { M.acct = a; M.pins = a.pins.slice(); refresh(); });
  };
  M.saveState = function (patch) {
    return M.A.saveState(patch).then(function (a) { M.acct = a; refresh(); });
  };
  M.paintFeeds = function () { keepFocus(function () { setHtml('mx-feeds', M.feeds.html()); }); };
  var toastTimer = null;
  M.toast = function (msg) {
    var t = document.getElementById('mx-toast');
    if (!t) { return; }
    t.textContent = msg;
    if (!t.classList.contains('on')) { t.classList.add('on'); }
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { if (t.classList.contains('on')) { t.classList.remove('on'); } }, 2600);
  };

  function unseen() { return M.L.whatsNewUnseen(M.wn, M.acct.state.wnSeen, M.today, WN_WINDOW); }
  function standalone() {
    if (window.navigator.standalone === true) { return true; }
    return window.matchMedia ? window.matchMedia('(display-mode: standalone)').matches : false;
  }
  function labels() { return M.specIds().map(function (id) { return M.byId[id].label; }); }
  var isMac = /Mac|iPhone|iPad/.test(navigator.platform || '');

  /* Redrawing a region loses focus; put it back on the control with the same key. */
  function keepFocus(fn) {
    var a = document.activeElement, k = a ? (a.getAttribute ? a.getAttribute('data-k') : null) : null;
    fn();
    if (k) { var b = mount.querySelector('[data-k="' + k + '"]'); if (b) { b.focus(); } }
  }

  /* ---------- regions ---------- */
  function helloHtml() {
    var l = labels();
    return '<h1 id="mx-hello-t">' + esc(M.L.greeting(new Date().getHours())) + (M.firstName ? ', ' + esc(M.firstName) : '') + '</h1>'
      + '<p><span>' + esc(new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })) + '</span>. '
      + (l.length ? 'Your page is set to <b>' + esc(M.L.joinNames(l)) + '</b>.' : 'You are seeing the whole Hub. <b>Pick your specialities</b> to narrow it.') + '</p>'
      + '<div class="meta"><button type="button" class="chip-d" data-open="m-spec" data-k="hello-spec">' + M.svg('steth') + 'Change specialities</button>'
      + '<button type="button" class="chip-d" data-act="tour" data-k="hello-tour">' + M.svg('play') + 'Take the tour</button></div>';
  }

  function changes(n) { return n + (n === 1 ? ' change' : ' changes'); }
  /* What the slot shows. Unseen entries when there are any (strip, box and
     pill, with counts). With nothing unseen, the bar's What's new button opens
     the last WN_WINDOW days read-only: no count, no badge, Got it just closes. */
  function recent() { return M.L.whatsNewUnseen(M.wn, [], M.today, WN_WINDOW); }
  function wnEntries(view) {
    var un = unseen();
    if (un.length) { return { list: un, fresh: true }; }
    return { list: view === 'full' ? recent() : [], fresh: false };
  }
  function wnItems(list) {
    return list.map(function (e) {
      var cls = e.tag === 'New' ? 'new' : (e.tag === 'Improved' ? 'imp' : 'fix');
      return '<li><span class="tag ' + cls + '">' + esc(e.tag) + '</span><p><b>' + esc(e.title) + '.</b> ' + esc(e.text) + '</p>'
        + (e.showMe ? '<button type="button" class="show-me" data-show="' + esc(e.showMe) + '" data-k="show-' + esc(e.id) + '">Show me</button>' : '') + '</li>';
    }).join('');
  }
  function wnHtml(w) {
    var un = w.list;
    if (!un.length) { return ''; }
    var head = '<section class="wn" role="region" aria-labelledby="mx-wn-t"><div class="wn-h"><span class="spark">' + M.svg('spark') + '</span><h2 id="mx-wn-t">What\u2019s new on the Hub</h2>';
    if (!w.fresh) {
      return head + '<button type="button" class="icon-btn" data-act="wn-close" data-k="wn-close" aria-label="Close What\u2019s new">' + M.svg('x') + '</button></div><ul>'
        + wnItems(un) + '</ul><div class="wn-f"><small>No new changes since your last visit</small><button type="button" class="btn navy" data-act="wn-close" data-k="wn-ok">Got it</button></div></section>';
    }
    var n = un.length;
    return '<button type="button" class="wn-strip" id="wn-strip" data-act="wn-full" data-k="wn-strip" aria-label="Open What\u2019s new, ' + changes(n) + '"><span class="s">' + M.svg('spark') + '</span>'
      + '<span class="t"><b>What\u2019s new:</b> ' + esc(un[0].title) + '</span><span class="n">' + n + '</span></button>'
      + head + '<button type="button" class="icon-btn" data-act="wn-min" data-k="wn-min" aria-label="Minimise What\u2019s new">' + M.svg('minus') + '</button></div><ul>'
      + wnItems(un)
      + '</ul><div class="wn-f"><small>' + changes(n) + ' since your last visit</small><button type="button" class="btn navy" data-act="wn-ok" data-k="wn-ok">Got it</button></div></section>'
      + '<button type="button" class="wn-pill" data-act="wn-full" data-k="wn-pill" aria-label="Open What\u2019s new, ' + changes(n) + '"><span class="s">' + M.svg('spark') + '</span>What\u2019s new <span class="n">' + n + '</span></button>';
  }
  /* Box or pill (ruling F10). Minimise is remembered in this browser as the
     newest unseen id, so the full box opens only on the first visit after a
     new entry; after that the pill shows until a newer entry arrives. On a
     phone (640px and under) the CSS shows the slim strip in place of the box
     while the state is "open"; tapping it sets "full". */
  var LS_WN_MIN = 'msh_my_hub_wn_min_v1';
  function minimisedId() { try { return localStorage.getItem(LS_WN_MIN) || ''; } catch (e) { return ''; } }
  function rememberMin() {
    var un = unseen();
    if (!un.length) { return; }
    try { localStorage.setItem(LS_WN_MIN, un[0].id); } catch (e) {}
  }
  function wnStart() {
    var mode = M.L.whatsNewMode(unseen(), minimisedId());
    return mode === 'box' ? 'open' : (mode === 'pill' ? 'min' : 'off');
  }
  /* The slot's markup is rewritten only when what it lists changes, so a
     state save elsewhere on the page does not throw away focus inside it. */
  function setWn(state) {
    var slot = document.getElementById('wn-slot');
    if (!slot) { return; }
    var view = state;
    if (!unseen().length) { view = state === 'full' ? (recent().length ? 'full' : 'off') : 'off'; }
    M.wnView = view;
    if (view === 'min') { rememberMin(); }
    var w = wnEntries(view), sig = (w.fresh ? 'u:' : 'r:') + w.list.map(function (e) { return e.id; }).join(',');
    if (slot.getAttribute('data-sig') !== sig) {
      keepFocus(function () { slot.innerHTML = wnHtml(w); });
      slot.setAttribute('data-sig', sig);
    }
    slot.setAttribute('data-state', view);
  }

  function barHtml() {
    var un = unseen(), dots = M.L.dotTargets(un), sc = M.acct.state.scope, n = un.length;
    function ib(key, glyph, label, attrs, extra) {
      return '<button type="button" class="ib" data-tour="' + key + '" data-k="ib-' + key + '" data-new="' + (dots[key] ? 'true' : 'false') + '"' + attrs + '>'
        + '<span class="c">' + M.svg(glyph) + '</span><span class="t">' + label + '</span>' + (extra || '') + '<i class="dot" aria-hidden="true"></i></button>';
    }
    return '<div class="scope"><button type="button" class="spec-btn" data-tour="spec" data-k="ib-spec" data-open="m-spec" aria-haspopup="dialog">'
      + '<span class="ic">' + M.svg('steth') + '</span><span><span class="l1">Specialities</span><span class="l2"><span>' + esc(M.L.specShort(labels())) + '</span>' + M.svg('down') + '</span></span></button>'
      + '<div class="seg" role="group" aria-label="What to show" data-tour="scope">'
      + '<button type="button" data-scope="mine" data-k="seg-mine" aria-pressed="' + (sc === 'mine') + '">My specialities</button>'
      + '<button type="button" data-scope="all" data-k="seg-all" aria-pressed="' + (sc === 'all') + '">Everything</button></div></div>'
      + '<div class="tools-row">'
      + ib('tools', 'grid', 'Tools', ' data-open="m-tools" aria-haspopup="dialog"')
      + ib('library', 'book', 'Evidence Library', ' data-act="library"')
      + ib('briefing', 'mail', 'Weekly briefing', ' data-open="m-brief" aria-haspopup="dialog"')
      + ib('saved', 'star', 'Saved', ' data-act="saved"')
      + ib('search', 'search', 'Search', ' data-open="m-search" aria-haspopup="dialog" aria-keyshortcuts="Control+K Meta+K"', '<span class="kbd">' + (isMac ? '\u2318K' : 'Ctrl K') + '</span>')
      + ib('how', 'help', 'How it works', ' data-open="m-how" aria-haspopup="dialog"')
      + '<button type="button" class="ib" data-tour="new" data-k="ib-new" data-act="wn-full" aria-label="What\u2019s new' + (n ? ', ' + changes(n) : '') + '">'
      + '<span class="c">' + M.svg('spark') + '</span><span class="t">What\u2019s new</span>' + (n ? '<span class="badge">' + n + '</span>' : '') + '</button>'
      + '</div>';
  }

  function checklistHtml() {
    var c = M.L.checklist({
      route: M.route(), routeName: (M.cat.profiles || {})[M.route()] || '', specCount: M.specIds().length,
      briefing: M.acct.state.briefing, phone: M.acct.state.phone, standalone: standalone(), tour: M.acct.state.tour
    });
    if (c.complete) { return ''; }
    return '<section class="card gs" id="gs" aria-labelledby="mx-gs-t"><div><h2 id="mx-gs-t">Get set up</h2><p class="p">' + c.done + ' of ' + c.total + ' done. Takes about two minutes.</p>'
      + '<div class="prog" role="progressbar" aria-label="Setup progress" aria-valuemin="0" aria-valuemax="' + c.total + '" aria-valuenow="' + c.done + '"><i style="width:' + Math.round(c.done / c.total * 100) + '%"></i></div></div>'
      + '<ul class="steps">' + c.steps.map(function (s) {
        return '<li><button type="button" class="step" data-step="' + s.key + '" data-k="step-' + s.key + '" data-done="' + s.done + '"><span class="ck">' + M.svg('check') + '</span>'
          + '<span><b>' + esc(s.label) + '</b><small>' + esc(s.sub) + '</small></span></button></li>';
      }).join('') + '</ul></section>';
  }

  function pagesHtml() {
    var list = M.visiblePins();
    var h = '<div class="sec-h"><h2 id="mx-yp-t">Your pages</h2><button type="button" class="more" data-open="m-pages" data-k="pages-edit">Edit</button></div>';
    if (!list.length) {
      return h + '<p class="empty"><b>Nothing pinned yet.</b> Pin the pages you use most and they sit here.</p>'
        + '<button type="button" class="btn navy mx-full" data-open="m-pages" data-k="pages-choose">Choose pages</button>';
    }
    return h + (M.seeded ? '<p class="mx-note">Suggested from your profile. Not saved yet.</p>' : '')
      + '<div class="tiles">' + list.map(function (id) {
        var it = M.byId[id];
        return '<a class="tile k-' + esc(it.kind || 'tool') + '" href="' + esc(M.L.safeUrl(it.url)) + '"><span class="ti">' + M.svg(M.I.forItem(it)) + '</span><b>' + esc(it.label) + '</b></a>';
      }).join('') + '</div>'
      + (M.acct.where === 'browser' ? '<p class="mx-note mx-mt">Saved on this device only. Your account could not be reached.</p>' : '');
  }

  function savedHtml() {
    var s = M.acct.state.stars, shown = M.savedOpen ? s : s.slice(0, 8);
    var h = '<div class="sec-h"><h2 id="mx-sv-t">Saved</h2><span class="n">' + s.length + (s.length === 1 ? ' item' : ' items') + '</span></div><ul>';
    if (!s.length) { return h + '<li class="empty"><b>Nothing saved yet.</b> Tap the star on any story or Hub page to keep it here.</li></ul>'; }
    h += shown.map(function (x) {
      var u = M.L.safeUrl(x.u), ext = /^https?:/.test(u), it = ext ? null : M.byUrl(u);
      return '<li class="srow"><span class="si">' + M.svg(x.k === 'story' ? 'news' : (it ? M.I.forItem(it) : 'file')) + '</span>'
        + '<a href="' + esc(u) + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + '><b>' + esc(x.t) + '</b><small>' + (x.k === 'story' ? 'Story' : 'Hub page') + '</small></a>'
        + '<button type="button" class="star" aria-pressed="true" data-unstar="' + esc(x.u) + '" aria-label="Remove ' + esc(x.t) + ' from Saved">' + M.svg('star') + '</button></li>';
    }).join('') + '</ul>';
    if (s.length > 8) { h += '<button type="button" class="more mx-more" data-act="saved-all" data-k="saved-all">' + (M.savedOpen ? 'Show fewer' : 'Show all ' + s.length) + '</button>'; }
    return h;
  }

  function briefHtml() {
    var on = M.acct.state.briefing;
    return '<span class="bi">' + M.svg('mail') + '</span><h2 id="mx-br-t">Your Monday briefing<span class="soon">Coming soon</span></h2>'
      + '<p>One email on Monday morning with what changed in your specialities. Left out when there is nothing worth sending.</p>'
      + '<ul><li>' + M.svg('check') + 'New stories from your specialities</li><li>' + M.svg('check') + 'Every device and patient safety alert</li>'
      + '<li>' + M.svg('check') + 'Tenders and events in the next fortnight</li></ul>'
      + (on ? '<div class="ok mx-on" role="status">' + M.svg('check') + 'You\u2019re on the list. We\u2019ll show it here when it starts.</div>'
        : '<button type="button" class="btn brass" data-open="m-brief" data-k="brief-go">Tell me when it starts</button>');
  }

  function shell() {
    return '<section class="mast on-dark" aria-labelledby="mx-hello-t"><div class="wrap"><div class="hello" id="mx-hello"></div><div class="wn-slot" id="wn-slot" data-state="off"></div></div></section>'
      + '<div class="wrap bar-wrap"><nav class="bar" id="mx-bar" aria-label="My Hub controls"></nav></div>'
      + '<div class="mx-main" id="main"><div class="wrap"><div id="mx-gs"></div><div class="layout"><div class="stack" id="mx-feeds"></div>'
      + '<aside class="side" aria-label="Your shortcuts"><section class="card pages" id="mx-pages" aria-labelledby="mx-yp-t"></section>'
      + '<section class="card saved" id="mx-saved" aria-labelledby="mx-sv-t"></section>'
      + '<section class="brief on-dark" id="mx-brief" aria-labelledby="mx-br-t"></section></aside></div></div></div>'
      + '<footer class="mx-foot"><div class="wrap"><span>Medical Sales Intelligence Hub, by Elevate &amp; Thrive</span>'
      + '<span><a href="/medical-sales-hub/ask/">Ask the Desk</a></span></div></footer>'
      + '<nav class="tabbar" aria-label="Quick actions"><button type="button" aria-current="page" data-act="top">' + M.svg('home') + 'Home</button>'
      + '<button type="button" data-open="m-tools">' + M.svg('grid') + 'Tools</button><button type="button" data-act="library">' + M.svg('book') + 'Library</button>'
      + '<button type="button" data-open="m-brief">' + M.svg('mail') + 'Briefing</button><button type="button" data-open="m-search">' + M.svg('search') + 'Search</button></nav>'
      + M.ui.modalsHtml()
      + '<div class="toast" id="mx-toast" role="status" aria-live="polite"></div>';
  }

  function refresh() {
    keepFocus(function () {
      setHtml('mx-hello', helloHtml());
      setWn(M.wnView === 'off' ? wnStart() : M.wnView);
      setHtml('mx-bar', barHtml());
      setHtml('mx-gs', checklistHtml());
      setHtml('mx-feeds', M.feeds.html());
      setHtml('mx-pages', pagesHtml());
      setHtml('mx-saved', savedHtml());
      setHtml('mx-brief', briefHtml());
      if (M.ui) { if (M.ui.refreshTools) { M.ui.refreshTools(); } }
    });
  }

  /* ---------- actions ---------- */
  function goTo(id) {
    var el = document.getElementById(id);
    if (!el) { return; }
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (el.classList.contains('flash')) { el.classList.remove('flash'); }
    void el.offsetWidth;
    el.classList.add('flash');
  }
  function library() {
    var t = M.L.libraryTargets(M.specIds(), M.byId, M.narrowed());
    if (t.length === 1) { window.location.assign(M.L.safeUrl(t[0].url)); return; }
    M.ui.openLibrary(t);
  }
  function markSeen(ids) {
    if (!ids.length) { return; }
    M.saveState({ wnSeen: M.acct.state.wnSeen.concat(ids) });
  }
  function gotIt() {
    setWn('off');
    M.saveState({ wnSeen: M.acct.state.wnSeen.concat(M.wn.map(function (e) { return e.id; })) });
  }
  function showMe(target) {
    setWn('min');
    if (target.charAt(0) === '/') { window.location.assign(M.L.safeUrl(target)); return; }
    var modals = { tools: 'm-tools', search: 'm-search', briefing: 'm-brief', how: 'm-how', spec: 'm-spec', pages: 'm-pages' };
    if (modals[target]) { M.ui.open(modals[target]); return; }
    if (target === 'saved') { goTo('mx-saved'); return; }
    if (target === 'library') { library(); return; }
    if (target === 'checklist') { goTo('gs'); return; }
    var el = mount.querySelector('[data-tour="' + target + '"]');
    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.focus(); }
  }
  function step(key) {
    if (key === 'profile') { window.location.assign('/medical-sales-hub/choose-your-profile/'); return; }
    if (key === 'spec') { M.ui.open('m-spec'); return; }
    if (key === 'brief') { M.ui.open('m-brief'); return; }
    if (key === 'phone') { M.ui.open('m-phone'); return; }
    if (key === 'tour') { M.ui.startTour(0); }
  }
  function toggleStory(btn) {
    var u = btn.getAttribute('data-star'), t = btn.getAttribute('data-star-t');
    var p = M.A.isStarred(u) ? M.A.unstar(u) : M.A.star({ u: u, t: t, k: 'story' });
    p.then(function (a) { M.acct = a; refresh(); M.toast(M.A.isStarred(u) ? 'Saved.' : 'Removed from Saved.'); });
  }

  function wire() {
    mount.addEventListener('click', function (e) {
      var t = e.target.closest ? e.target.closest('[data-open],[data-act],[data-scope],[data-step],[data-show],[data-unstar],[data-star]') : null;
      if (!t) { return; }
      if (t.getAttribute('data-new') === 'true') {
        t.setAttribute('data-new', 'false');
        markSeen(M.L.idsForTarget(unseen(), t.getAttribute('data-tour')));
      }
      if (t.hasAttribute('data-open')) { e.preventDefault(); M.ui.open(t.getAttribute('data-open'), t); return; }
      if (t.hasAttribute('data-scope')) {
        var sc = t.getAttribute('data-scope');
        if (sc !== M.acct.state.scope) { M.saveState({ scope: sc }); }
        return;
      }
      if (t.hasAttribute('data-step')) { step(t.getAttribute('data-step')); return; }
      if (t.hasAttribute('data-show')) { showMe(t.getAttribute('data-show')); return; }
      if (t.hasAttribute('data-unstar')) {
        M.A.unstar(t.getAttribute('data-unstar')).then(function (a) { M.acct = a; refresh(); M.toast('Removed from Saved.'); });
        return;
      }
      if (t.hasAttribute('data-star')) { toggleStory(t); return; }
      var act = t.getAttribute('data-act');
      if (act === 'tour') { M.ui.startTour(0); return; }
      if (act === 'library') { library(); return; }
      if (act === 'saved') { goTo('mx-saved'); return; }
      if (act === 'saved-all') { M.savedOpen = !M.savedOpen; refresh(); return; }
      if (act === 'wn-min') { setWn('min'); return; }
      if (act === 'wn-full') {
        if (!unseen().length) { if (!recent().length) { M.toast('Nothing new in the last ' + WN_WINDOW + ' days'); return; } }
        setWn('full'); mount.querySelector('.mast').scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
      if (act === 'wn-ok') { gotIt(); return; }
      if (act === 'wn-close') { setWn('off'); return; }
      if (act === 'top') { window.scrollTo({ top: 0, behavior: 'smooth' }); }
    });
  }

  /* ---------- start ---------- */
  function seed() {
    return getJSON('/wp-json/msh/v1/prefs').then(function (p) { return p; }, function () { return null; }).then(function (p) {
      var out = [];
      function add(id) { if (id) { if (M.byId[id]) { if (out.indexOf(id) === -1) { out.push(id); } } } }
      M.prefsRoute = p ? p.profile_route : null;
      var i = p ? p.interests : null;
      if (i) { add(i.speciality); }
      ((M.cat.profileStarters || {})[M.route()] || []).forEach(add);
      if (i) { if (i.role) { (((M.cat.roles || {})[i.role] || {}).pins || []).forEach(add); } }
      if (i) { if (i.care === 'primary') { add('primary-care-and-general-practice'); } }
      M.pins = out;
      M.seeded = out.length > 0;
    });
  }
  function greet() {
    getJSON('/wp-json/wp/v2/users/me?context=edit&_fields=first_name,name').then(function (u) {
      var n = String((u ? u.first_name : '') || '').trim();
      if (!n) { if (u) { if (u.name) { if (u.name.indexOf('@') === -1) { n = String(u.name).trim().split(/\s+/)[0]; } } } }
      M.firstName = n;
      setHtml('mx-hello', helloHtml());
    }).catch(function () {});
  }
  function loggedOut() {
    mount.innerHTML = '<div class="mx-loading"><b>Log in to open your Hub.</b> <a class="mx-link" href="/login/">Log in</a></div>';
  }
  function start() {
    M.L = window.MSH_MYHUB_LOGIC; M.I = window.MSH_ICONS; M.A = window.MSH_ACCOUNT;
    M.svg = function (n, c) { return M.I.svg(n, c || 'i'); };
    M.byId = {}; M.urlMap = {};
    M.cat.items.forEach(function (it) {
      M.byId[it.id] = it;
      if (it.url.indexOf('#') === -1) { M.urlMap[it.url] = it; }   // tool views share their page's URL: the page owns it
    });
    M.today = M.L.isoDay(new Date());
    if (!nonce()) { loggedOut(); return; }
    M.A.load().then(function (acct) {
      M.acct = acct;
      M.pins = acct.pins.slice();
      M.seeded = false;
      if (!acct.pinsSaved) { if (!M.pins.length) { return seed(); } }
      return getJSON('/wp-json/msh/v1/prefs').then(function (p) { M.prefsRoute = p ? p.profile_route : null; }, function () {});
    }).then(function () {
      M.wnView = 'off';   // refresh() picks box, pill or nothing (F10)
      mount.innerHTML = shell();
      refresh();
      wire();
      M.ui.wire();
      M.feeds.load();
      greet();
      var q = /[?&]tour=(\d+)/.exec(location.search);
      if (q) { if (q[1] !== '0') { setTimeout(function () { M.ui.startTour(+q[1] - 1); }, 400); return; } }
      if (!q) { if (!M.acct.state.tourSeen) { setTimeout(function () { M.ui.startTour(0); }, 700); } }
    }).catch(fail);
  }

  function boot() {
    mount.innerHTML = '<p class="mx-loading" role="status">Loading your Hub.</p>';
    var jobs = [text('app/my-hub.css')].concat(MODULES.map(text)).concat([
      text('hub/my-hub-catalogue.json').then(JSON.parse),
      text('hub/whats-new.json').then(JSON.parse).catch(function () { return { entries: [] }; })
    ]);
    Promise.all(jobs).then(function (got) {
      if (!document.getElementById('mhx-css')) {
        var st = document.createElement('style');
        st.id = 'mhx-css';
        st.textContent = got[0];
        document.head.appendChild(st);
      }
      for (var i = 0; i !== MODULES.length; i++) { (new Function(got[1 + i]))(); }
      M.cat = got[1 + MODULES.length];
      M.wn = got[2 + MODULES.length].entries || [];
      start();
    }).catch(fail);
  }

  boot();
})();
