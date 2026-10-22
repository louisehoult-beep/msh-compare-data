/* Hub chrome: two small additions on every Hub page (My Hub home screen, 2026-10).
   Loaded by one line at the end of WPCode snippet 1331 (Hub Master Nav);
   source of that line: hub/wpcode/nav-1331-hub-chrome-loader.html.

   1. NAV ICONS. Every nav dropdown entry gets the icon its page has on My Hub
      (app/hub-icons.js, named in hub/my-hub-catalogue.json). Snippet 1331
      rebuilds the nav when it syncs the profile from the account, so a
      MutationObserver re-applies them. It watches childList only, never
      attributes, and marks each link it has done, so its own insertions
      cannot set it off again (mutationobserver-classlist-infinite-loop).
   2. PAGE BAR. A slim white bar under the nav with the page's icon and name
      and a Save star (spec item 6). A starred page is listed under Saved on
      My Hub and follows the member across devices (app/hub-account.js).
      Not drawn on My Hub, which has its own, or on Choose your profile.

   3. NAV GAPS (22/10/2026, Ego Pharmaceuticals call). Snippet 1331 is not in
      this repo, so three nav fixes live here and apply on every profile at once:
      a My Hub link that is always in the top nav, a Search button that opens the
      Hub planner (app/hub-search.js) from any page, and Build Your Network in the
      profiles that need it (NAV_ADD). Each is idempotent, so a nav rebuild only
      re-runs them. When 1331 itself lists them, these find them and do nothing.
   4. BACK TO MY HUB. A member who opened a page from My Hub gets a "My Hub"
      Back button in the page bar, which returns to My Hub, not to whichever
      page the browser history holds.

   Logged-in members on /medical-sales-hub/ pages only. Fails silently: if
   anything here cannot load, the page and the nav are exactly as before. */
(function () {
  'use strict';
  if (window.MSH_HUB_CHROME) { return; }
  window.MSH_HUB_CHROME = 1;

  var BASE = window.MSH_MYHUB_BASE || 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var NO_BAR = ['/medical-sales-hub/my-hub/', '/medical-sales-hub/choose-your-profile/'];

  function norm(p) { return ('/' + String(p || '')).replace(/\/+/g, '/').replace(/\/+$/, '') + '/'; }
  var here = norm(location.pathname);
  if (here.indexOf('/medical-sales-hub/') !== 0) { return; }

  var BYURL = {};
  var MYHUB = '/medical-sales-hub/my-hub/';
  var NETWORK = ['Build Your Network', '/medical-sales-hub/build-your-network/'];
  /* Profile (the label under the logo) -> the nav group that gains Build Your
     Network. Medical sales professionals already list it under Your career;
     clinicians do not network with suppliers, so they are not here. */
  var NAV_ADD = {
    'MEDICAL SUPPLIER': 'Companies',
    'MEDICAL SALES PROFESSIONALS': 'Your career',
    'PROCUREMENT': 'Companies',
    'RECRUITMENT COMPANIES': 'Your career'
  };
  var SEARCH_SVG = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg>';

  /* Did the member come from My Hub? Remembered for the tab, so the answer
     survives a click from one subpage to the next. */
  function fromMyHub() {
    var ref = '';
    try { ref = new URL(document.referrer).pathname; } catch (e) { ref = ''; }
    try {
      if (here === MYHUB) { sessionStorage.removeItem('mshFromMyHub'); return false; }
      if (norm(ref) === MYHUB) { sessionStorage.setItem('mshFromMyHub', '1'); return true; }
      return sessionStorage.getItem('mshFromMyHub') === '1';
    } catch (e) { return norm(ref) === MYHUB; }
  }
  var CAME_FROM_MYHUB = fromMyHub();

  function text(p) {
    return fetch(BASE + p, { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error(p + ' ' + r.status); } return r.text(); });
  }

  /* The page's own name when it is not in the catalogue, or carries a query
     (a company report): the document title without the site name. */
  function pageTitle() {
    var t = String(document.title || '').split(/\s[\u2013\u2014|-]\s/)[0].replace(/\s*\(Subscribers only\)\s*$/i, '').trim();
    return t || 'Hub page';
  }

  function css() {
    if (document.getElementById('mshc-css')) { return; }
    var st = document.createElement('style');
    st.id = 'mshc-css';
    st.textContent = [
      '.msh nav .msh-dd-m a .mshc-ic{display:inline-flex;vertical-align:-3px;margin-right:8px;}',
      '.msh nav .msh-dd-m a .mshc-svg{width:16px;height:16px;display:block;}',
      '.msh .mshc-bar{width:100%;background:#FFFFFF;border-bottom:1px solid #E2DCCF;box-sizing:border-box;}',
      '.msh .mshc-bar .mshc-in{display:flex;align-items:center;gap:10px;min-height:44px;padding:6px clamp(16px,3vw,32px);box-sizing:border-box;}',
      '.msh .mshc-bar .mshc-pi{width:28px;height:28px;border-radius:8px;background:#0B1C33;color:#E3C583;display:inline-flex;align-items:center;justify-content:center;flex:none;}',
      '.msh .mshc-bar .mshc-pi .mshc-svg{width:16px;height:16px;display:block;}',
      '.msh .mshc-bar .mshc-t{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:Inter,-apple-system,"Segoe UI",system-ui,sans-serif!important;font-size:13.5px!important;font-weight:600!important;color:#0B1C33!important;line-height:1.3!important;margin:0!important;}',
      '.msh .mshc-bar .mshc-star{display:inline-flex;align-items:center;gap:6px;flex:none;cursor:pointer;background:#FFFFFF;border:1.5px solid #D6CEBE;border-radius:999px;padding:5px 12px 5px 9px;font-family:Inter,-apple-system,"Segoe UI",system-ui,sans-serif!important;font-size:13px!important;font-weight:600!important;color:#0B1C33!important;line-height:1.2!important;}',
      '.msh .mshc-bar .mshc-save{margin-left:0;}',
      '.msh .mshc-bar .mshc-star:hover{border-color:#0B1C33;}',
      '.msh .mshc-bar .mshc-star:focus-visible{outline:3px solid #1B5FBF;outline-offset:2px;}',
      '.msh .mshc-bar .mshc-star .mshc-svg{width:16px;height:16px;display:block;}',
      '.msh .mshc-bar .mshc-star[aria-pressed="true"]{background:#F7F1E3;border-color:#B8935A;color:#7E6118!important;}',
      '.msh .mshc-bar .mshc-star[aria-pressed="true"] .mshc-svg{fill:#C9A227;stroke:#8C6A1C;}',
      '.msh .mshc-bar .mshc-back{display:inline-flex;align-items:center;gap:4px;flex:none;text-decoration:none!important;background:#0B1C33;border-radius:999px;padding:5px 12px 5px 8px;font-family:Inter,-apple-system,"Segoe UI",system-ui,sans-serif!important;font-size:13px!important;font-weight:600!important;color:#FFFFFF!important;line-height:1.2!important;}',
      '.msh .mshc-bar .mshc-back:hover{background:#14304F;}',
      '.msh .mshc-bar .mshc-back:focus-visible{outline:3px solid #1B5FBF;outline-offset:2px;}',
      '.msh nav a.mshc-myhub{font-weight:700;}',
      '.msh header .mshc-sw{flex:none;order:9;margin-left:8px;display:inline-block;vertical-align:middle;}',
      '.msh header .mshc-sb{display:inline-flex;align-items:center;gap:6px;cursor:pointer;background:#FFFFFF;border:1px solid #D6CEBE;border-radius:999px;padding:6px 12px;font-family:Inter,-apple-system,"Segoe UI",system-ui,sans-serif!important;font-size:12px!important;font-weight:700!important;letter-spacing:.3px;color:#0B1C33!important;line-height:1.2!important;}',
      '.msh header .mshc-sb:hover{border-color:#0B1C33;}',
      '.msh header .mshc-sb:focus-visible{outline:3px solid #1B5FBF;outline-offset:2px;}',
      '#mshc-sp{position:fixed;z-index:2147483000;left:50%;transform:translateX(-50%);width:min(640px,calc(100vw - 24px));max-height:calc(100vh - 110px);overflow-y:auto;background:#0B1C33;border:1px solid #33415A;border-top:3px solid #C49B5C;border-radius:10px;box-shadow:0 18px 48px rgba(0,0,0,.45);padding:12px;box-sizing:border-box;}',
      '#mshc-sp[hidden]{display:none;}',
      '#mshc-sp input{width:100%;box-sizing:border-box;font:500 15px/1.3 Inter,-apple-system,"Segoe UI",system-ui,sans-serif;padding:10px 12px;border-radius:8px;border:1px solid #D6CEBE;background:#FFFFFF!important;color:#1D2733!important;}',
      '#mshc-sp [data-hub-search-results]{margin-top:10px;color:#E2E8F0;}',
      '#mshc-sp [data-hub-search-results] a{color:#E2E8F0;}',
      '@media (max-width:760px){.msh header .mshc-sw{order:2;margin-left:auto;}.msh header .mshc-sb .mshc-sl{display:none;}}',
      '@media (max-width:640px){.msh .mshc-bar .mshc-in{min-height:40px;}.msh .mshc-bar .mshc-t{font-size:13px!important;}}'
    ].join('\n');
    document.head.appendChild(st);
  }

  function decorateNav() {
    var I = window.MSH_ICONS;
    var links = document.querySelectorAll('.msh nav .msh-dd-m a');
    for (var i = 0; i !== links.length; i++) {
      var a = links[i];
      if (a.getAttribute('data-mshc')) { continue; }
      a.setAttribute('data-mshc', '1');
      var it = BYURL[norm((a.getAttribute('href') || '').replace(/^https?:\/\/[^/]+/, '').split('#')[0].split('?')[0])];
      if (!it) { continue; }
      var span = document.createElement('span');
      span.className = 'mshc-ic';
      span.setAttribute('aria-hidden', 'true');
      span.innerHTML = I.svg(I.forItem(it), 'mshc-svg');
      a.insertBefore(span, a.firstChild);
    }
  }

  /* Top-level nav links are plain <a> children of nav, dropdowns are .msh-dd.
     A My Hub link that snippet 1331 did not draw is added first, after Live Desk. */
  function ensureMyHubLink() {
    var nav = document.querySelector('.msh header nav');
    if (!nav || nav.classList.contains('msh-nolock')) { return; }
    var all = nav.querySelectorAll('a');
    for (var i = 0; i !== all.length; i++) {
      if (norm((all[i].getAttribute('href') || '').replace(/^https?:\/\/[^/]+/, '')) === MYHUB) { return; }
    }
    var a = document.createElement('a');
    a.href = MYHUB;
    a.className = 'mshc-myhub' + (here === MYHUB ? ' active' : '');
    a.textContent = 'MY HUB';
    var first = nav.firstElementChild;
    if (first && first.tagName === 'A' && first.nextSibling) { nav.insertBefore(a, first.nextSibling); }
    else { nav.insertBefore(a, nav.firstChild); }
  }

  function ensureNetworkLink() {
    var lab = document.querySelector('.msh header .msh-plabel');
    var group = lab ? NAV_ADD[String(lab.textContent || '').trim().toUpperCase()] : '';
    if (!group) { return; }
    var nav = document.querySelector('.msh header nav');
    if (!nav) { return; }
    var links = nav.querySelectorAll('a');
    for (var i = 0; i !== links.length; i++) {
      if (norm((links[i].getAttribute('href') || '').replace(/^https?:\/\/[^/]+/, '')) === norm(NETWORK[1])) { return; }
    }
    var dds = nav.querySelectorAll('.msh-dd');
    for (var j = 0; j !== dds.length; j++) {
      var t = dds[j].querySelector('.msh-dd-t');
      var m = dds[j].querySelector('.msh-dd-m');
      if (!t || !m || String(t.textContent || '').replace(/[^A-Za-z& ]/g, '').trim().toLowerCase() !== group.toLowerCase()) { continue; }
      var a = document.createElement('a');
      a.href = NETWORK[1];
      a.textContent = NETWORK[0];
      if (here === norm(NETWORK[1])) { a.className = 'active'; }
      m.appendChild(a);
      return;
    }
  }

  /* Search from any page. The box is the Live Desk's own planner
     (app/hub-search.js), mounted through its embed hook, so ranking and the Ask
     the Hub card are identical. Where the page already carries the Live Desk
     box, the button focuses that instead. */
  function ensureSearch() {
    var header = document.querySelector('.msh header');
    if (!header) { return; }
    var nav = header.querySelector('nav');
    var old = document.getElementById('mshc-sw');
    /* The header is not a flex row on the live site, so a button appended to it
       dropped onto its own line under the logo and went unnoticed (22/10/2026).
       It sits in the nav row, last, where the other links are. */
    if (old) { if (nav && old.parentNode !== nav) { nav.appendChild(old); } return; }
    var oldPanel = document.getElementById('mshc-sp');
    if (oldPanel) { oldPanel.parentNode.removeChild(oldPanel); }
    var w = document.createElement('div');
    w.id = 'mshc-sw';
    w.className = 'mshc-sw';
    w.innerHTML = '<button type="button" class="mshc-sb" aria-expanded="false" aria-controls="mshc-sp" aria-label="Search the Hub">' + SEARCH_SVG + '<span class="mshc-sl">SEARCH</span></button>';
    (nav || header).appendChild(w);
    var btn = w.querySelector('button'), panel = null, loaded = false;
    function close() { if (panel) { panel.hidden = true; } btn.setAttribute('aria-expanded', 'false'); }
    function place() { var r = header.getBoundingClientRect(); panel.style.top = Math.max(r.bottom + 6, 8) + 'px'; }
    btn.addEventListener('click', function () {
      var live = document.querySelector('.msh .qsearch input');
      if (live && live.offsetParent !== null) { live.scrollIntoView({ block: 'center' }); live.focus(); return; }
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'mshc-sp';
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-label', 'Search the Hub');
        panel.innerHTML = '<div data-hub-search-embed><input type="text" aria-label="Tell the Hub what you want to do" autocomplete="off" spellcheck="false" placeholder="What do you want to do today? e.g. meeting about Molnlycke"></div><div data-hub-search-results></div>';
        document.body.appendChild(panel);
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) { close(); btn.focus(); } });
        document.addEventListener('mousedown', function (e) { if (!panel.hidden && !panel.contains(e.target) && !w.contains(e.target)) { close(); } });
        window.addEventListener('resize', function () { if (!panel.hidden) { place(); } });
      }
      if (!panel.hidden) { close(); return; }
      panel.hidden = false;
      place();
      btn.setAttribute('aria-expanded', 'true');
      panel.querySelector('input').focus();
      if (!loaded) {
        loaded = true;
        text('app/hub-search.js').then(run).catch(function () {
          loaded = false;
          panel.querySelector('[data-hub-search-results]').innerHTML = '<p style="padding:8px 4px;margin:0;">Search is unavailable just now. Try again in a minute.</p>';
        });
      }
    });
  }

  function navFixes() { ensureMyHubLink(); ensureNetworkLink(); ensureSearch(); }

  function watchNav() {
    var nav = document.querySelector('.msh header nav');
    if (!nav) { return; }
    if (!window.MutationObserver) { return; }
    new MutationObserver(function () { decorateNav(); navFixes(); }).observe(nav, { childList: true, subtree: true });
  }

  function pageBar() {
    var I = window.MSH_ICONS, A = window.MSH_ACCOUNT;
    var header = document.querySelector('.msh header');
    if (!header) { return; }
    if (document.getElementById('mshc-bar')) { return; }
    var it = BYURL[here] || null;
    var key = here + (location.search || '');
    var title = location.search ? pageTitle() : (it ? it.label : pageTitle());
    var bar = document.createElement('div');
    bar.id = 'mshc-bar';
    bar.className = 'mshc-bar';
    bar.innerHTML = '<div class="mshc-in">' + (CAME_FROM_MYHUB ? '<a class="mshc-back" href="' + MYHUB + '" aria-label="Back to My Hub">' + '<span aria-hidden="true">\u2039</span> My Hub</a>' : '') + '<span class="mshc-pi" aria-hidden="true">' + I.svg(it ? I.forItem(it) : 'file', 'mshc-svg') + '</span>'
      + '<span class="mshc-t"></span>'
      + (it && it.group === 'specialities' ? '<button type="button" class="mshc-star mshc-add" aria-pressed="false">' + I.svg('plus', 'mshc-svg') + '<span class="mshc-l">Add to My Hub</span></button>' : '')
      + '<button type="button" class="mshc-star mshc-save" aria-pressed="false">' + I.svg('star', 'mshc-svg') + '<span class="mshc-l">Save</span></button></div>';
    bar.querySelector('.mshc-t').textContent = title;
    header.parentNode.insertBefore(bar, header.nextSibling);
    var btn = bar.querySelector('.mshc-save');
    var add = bar.querySelector('.mshc-add');
    /* One click puts this speciality on My Hub (its pinned pages, which set the
       member's specialities); another takes it off. */
    function paintAdd() {
      var on = A.hasPin(it.id);
      add.setAttribute('aria-pressed', on ? 'true' : 'false');
      add.querySelector('.mshc-l').textContent = on ? 'On My Hub' : 'Add to My Hub';
      add.setAttribute('aria-label', (on ? 'Remove ' : 'Add ') + it.label + (on ? ' from My Hub' : ' to My Hub'));
    }
    if (add) {
      A.load().then(paintAdd);
      add.addEventListener('click', function () {
        var on = add.getAttribute('aria-pressed') !== 'true';
        add.setAttribute('aria-pressed', on ? 'true' : 'false');
        (on ? A.addPin(it.id) : A.removePin(it.id)).then(paintAdd, paintAdd);
      });
    }
    function paint(on) {
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      btn.querySelector('.mshc-l').textContent = on ? 'Saved' : 'Save';
      btn.setAttribute('aria-label', on ? 'Remove ' + title + ' from Saved on My Hub' : 'Save ' + title + ' to My Hub');
    }
    paint(false);
    A.load().then(function () { paint(A.isStarred(key)); });
    btn.addEventListener('click', function () {
      var on = btn.getAttribute('aria-pressed') !== 'true';
      paint(on);
      var p = on ? A.star({ u: key, t: title, k: 'page' }) : A.unstar(key);
      p.then(function () { paint(A.isStarred(key)); }, function () { paint(!on); });
    });
  }

  function run(src) { (new Function(src))(); }

  function boot() {
    Promise.all([
      window.MSH_ICONS ? '' : text('app/hub-icons.js'),
      window.MSH_ACCOUNT ? '' : text('app/hub-account.js'),
      text('hub/my-hub-catalogue.json')
    ]).then(function (got) {
      if (got[0]) { run(got[0]); }
      if (got[1]) { run(got[1]); }
      JSON.parse(got[2]).items.forEach(function (it) { BYURL[norm(it.url)] = it; });
      css();
      decorateNav();
      navFixes();
      watchNav();
      if (NO_BAR.indexOf(here) !== -1) { return; }
      if (!(window.mshRestNonce || window.mshPrefsNonce)) { return; }
      pageBar();
    }).catch(function () {});
  }

  if (document.readyState === 'complete') { boot(); } else { window.addEventListener('load', boot); }
})();
