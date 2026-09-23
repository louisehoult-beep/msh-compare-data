/* Medical Sales Intelligence Hub: phone app.
   Mounts on #msh-mobile-app. One members-only Hub page carries this loader
   and nothing else; this file turns that page into a full-screen phone app
   with a thumb-reach bottom bar, one tab per tool:

     Prep       app/meeting-prep.js     (#msh-meeting-prep)
     Suppliers  app/supplier-search.js  (#msh-supplier-search)
     Compare    app/comparison.js       (#msh-compare-tool)
     Company    app/company-report.js   (#msh-company-report)
     Search     app/hub-search.js       (#ethHubSearch)

   THE TOOLS ARE NOT COPIED. Each tab creates the mount element its tool
   already looks for, then fetches and runs that tool's own file from this
   repo, the same way the desktop Hub pages' loaders do. A fix to a tool
   lands in the app on the same push. Tools load on first tap, not on page
   load, and stay in memory so switching tabs keeps what the member typed.

   WHY IT LIVES ON A HUB PAGE AND NOT ON GITHUB PAGES (Lou, 23/09/2026):
   the app is for paying members only. The page sits under the Hub's
   subscriber-only parent, so PMS does the gating, and Meeting Prep's gated
   data (window.MSH_GATE) only exists on a logged-in Hub page.

   Installing: the page gets a web app manifest and iOS home-screen tags, so
   "Add to Home Screen" opens it full screen with its own icon. The Install
   button uses Chrome's own prompt where the browser offers one, and shows
   the steps where it does not (iPhone). */
(function () {
  var MOUNT = document.getElementById('msh-mobile-app');
  if (!MOUNT) { return; }
  if (MOUNT.getAttribute('data-msh-app') === 'v1') { return; }
  MOUNT.setAttribute('data-msh-app', 'v1');

  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var NAVY = '#0B1C33', GOLD = '#E0BE8E', INK = '#132238', DIM = '#5b6675', BG = '#f6f7f9', LINE = '#dfe3ea';
  var ICON192 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAABqklEQVR42u3SQQ0AIAwAsf2xgIv5RBJakIIHXgOanIJLY80hHRcWCCABJIAEkASQABJAAkgCSAAJIAEkASSAdDWg1lMPB5AAEkACCCCAABJAAkgAAQQQQAJIAAkgAQSQABJAAkgAASSABJAAEkAAAQSQABJAAggggAASQAJIALkMEEACSAAJIAEEkAASQAJIAAEEEEACSAAJIIAAAkgACSABBBBAAAkgASSABBBAAkgACSABBJAAEkACSAABBBBAAkgACSCAAAJIAAkgASSAABJAAkgACSCABJAAEkACCCCAABJAAkgAAQQQQAJIAAkgiwECSAAJIAEkgAASQAJIAAkggAACSAAJIAEEEEAACSABJIAAAgggASSABJAAAkgACSABJIAAEkACSAAJIIAAAkgACSABBBBAAAkgASSABBBAAkgACSABBJAAEkACSAABBBBAAkgACSCAAAJIAAkgAQQQQAAJIAEkgAQQQAJIAAkgAQQQQAAJIAEkgAACCCABJIAEEEAAASSABJD+BSQBJIAEkAASQC4IIAEkgASQBJAAEkACSAJIAKlsG9Hiv5/cJlL6AAAAAElFTkSuQmCC';
  var ICON512 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAIAAAB7GkOtAAAHtklEQVR42u3VUQ0AIAhFUf6pYAt7GoksRjEHcraTAN5249YBYKBwAgABAEAAABAAAAQAAAEAQAAAEAAABAAAAQBAAAAQAAAEAAABAEAAABAAAAQAAAEAQAAAEAAABAAAAQBAAAAQAAABAEAAABAAAAQAAAEAQAAAEAAABAAAAQBAAAAQAAAEAAABAEAAABAAAAQAAAEAoHkAcm2AsQQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAAvB8QAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABMACAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAALAAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAATA+wEBEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAACwAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAATAAgABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAAAEQAAABEAAAARAAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAQAQAAEAEAABABAAAAEQAAABEAAAARAAAAEQAAABOCXAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgAgAE4AIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAIAAACAAAAgCAAAAgAAAIAABtPZlSqdgDpTHVAAAAAElFTkSuQmCC';

  var I = {
    prep: '<path d="M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1z"/><path d="M8 5H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><path d="M8 12l2.5 2.5L16 9"/>',
    suppliers: '<path d="M3 21h18"/><path d="M5 21V8l7-4 7 4v13"/><path d="M9 21v-5h6v5"/><path d="M9 11h.01M15 11h.01"/>',
    compare: '<path d="M7 4v16"/><path d="M17 4v16"/><path d="M3 8l4-4 4 4"/><path d="M13 16l4 4 4-4"/>',
    company: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.5-4.5"/>',
    install: '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/>'
  };
  function svg(name, size) {
    return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + I[name] + '</svg>';
  }

  var TABS = [
    { key: 'prep', label: 'Prep', title: 'Meeting Prep', file: 'app/meeting-prep.js', mount: 'msh-meeting-prep' },
    { key: 'suppliers', label: 'Suppliers', title: 'Supplier Search', file: 'app/supplier-search.js', mount: 'msh-supplier-search' },
    { key: 'compare', label: 'Compare', title: 'Product Compare', file: 'app/comparison.js', mount: 'msh-compare-tool' },
    { key: 'company', label: 'Company', title: 'Company Report', file: 'app/company-report.js', mount: 'msh-company-report' },
    { key: 'search', label: 'Search', title: 'Hub Search', file: 'app/hub-search.js', mount: 'ethHubSearch', dark: true }
  ];
  var BY = {};
  TABS.forEach(function (t) { BY[t.key] = t; });

  /* ---------- home-screen install: manifest + iOS tags ---------- */
  function headTag(tag, attrs) {
    var n = document.createElement(tag);
    for (var k in attrs) { if (attrs.hasOwnProperty(k)) { n.setAttribute(k, attrs[k]); } }
    document.head.appendChild(n);
  }
  (function installTags() {
    var here = location.href.split('#')[0];
    var manifest = {
      name: 'Medical Sales Intelligence Hub',
      short_name: 'Med Sales Hub',
      id: here,
      start_url: here,
      scope: here.replace(/[^\/]*$/, ''),
      display: 'standalone',
      background_color: NAVY,
      theme_color: NAVY,
      icons: [
        { src: ICON192, sizes: '192x192', type: 'image/png', purpose: 'any' },
        { src: ICON512, sizes: '512x512', type: 'image/png', purpose: 'any' }
      ]
    };
    var old = document.querySelector('link[rel="manifest"]');
    if (old) { old.parentNode.removeChild(old); }
    headTag('link', { rel: 'manifest', href: 'data:application/manifest+json,' + encodeURIComponent(JSON.stringify(manifest)) });
    headTag('link', { rel: 'apple-touch-icon', href: ICON192 });
    headTag('meta', { name: 'apple-mobile-web-app-capable', content: 'yes' });
    headTag('meta', { name: 'mobile-web-app-capable', content: 'yes' });
    headTag('meta', { name: 'apple-mobile-web-app-title', content: 'Med Sales Hub' });
    headTag('meta', { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' });
    var tc = document.querySelector('meta[name="theme-color"]');
    if (tc) { tc.setAttribute('content', NAVY); } else { headTag('meta', { name: 'theme-color', content: NAVY }); }
    var vp = document.querySelector('meta[name="viewport"]');
    var vpc = 'width=device-width, initial-scale=1, viewport-fit=cover';
    if (vp) { vp.setAttribute('content', vpc); } else { headTag('meta', { name: 'viewport', content: vpc }); }
  })();

  /* ---------- styles ---------- */
  /* Everything is scoped to #msh-app so the rest of the Hub is untouched.
     The tools were built for desktop and carry inline min-widths of 180 to
     300px on their form boxes; on a phone those force sideways scrolling,
     so they are released here rather than edited in each tool. */
  var css =
    'html.msh-app-on,html.msh-app-on body{overflow:hidden!important;height:100%;}' +
    '#msh-app{position:fixed;inset:0;z-index:2147483000;display:flex;flex-direction:column;background:' + BG + ';color:' + INK + ';' +
      'font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%;}' +
    '#msh-app *{box-sizing:border-box;}' +
    '#msh-app .ma-top{background:' + NAVY + ';color:#fff;padding:calc(10px + env(safe-area-inset-top)) 16px 10px;display:flex;align-items:center;gap:12px;flex:0 0 auto;}' +
    '#msh-app .ma-kick{font-size:10.5px;letter-spacing:1.6px;text-transform:uppercase;color:' + GOLD + ';font-weight:800;}' +
    '#msh-app .ma-title{font-size:20px;font-weight:800;line-height:1.2;margin:0;}' +
    '#msh-app .ma-inst{margin-left:auto;display:none;align-items:center;gap:6px;background:' + GOLD + ';color:' + NAVY + ';border:0;border-radius:22px;' +
      'min-height:44px;padding:0 16px;font:inherit;font-size:14px;font-weight:800;cursor:pointer;}' +
    '#msh-app .ma-inst.show{display:inline-flex;}' +
    '#msh-app .ma-main{flex:1 1 auto;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;padding:12px 12px 24px;}' +
    '#msh-app .ma-panel{display:none;max-width:720px;margin:0 auto;}' +
    '#msh-app .ma-panel.on{display:block;}' +
    '#msh-app .ma-panel.dark .ma-host{background:' + NAVY + ';border-radius:12px;padding:16px;}' +
    '#msh-app .ma-state{text-align:center;padding:48px 16px;color:' + DIM + ';}' +
    '#msh-app .ma-state button{margin-top:14px;min-height:52px;padding:0 28px;border-radius:26px;border:0;background:' + NAVY + ';color:#fff;font:inherit;font-weight:800;cursor:pointer;}' +
    '#msh-app .ma-spin{width:32px;height:32px;border-radius:50%;border:3px solid ' + LINE + ';border-top-color:' + NAVY + ';margin:0 auto 12px;animation:maspin .8s linear infinite;}' +
    '@keyframes maspin{to{transform:rotate(360deg);}}' +
    '#msh-app .ma-nav{flex:0 0 auto;display:flex;background:#fff;border-top:1px solid ' + LINE + ';padding-bottom:env(safe-area-inset-bottom);box-shadow:0 -2px 10px rgba(11,28,51,.06);}' +
    '#msh-app .ma-nav button{flex:1 1 0;min-width:0;min-height:64px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;' +
      'background:none;border:0;border-top:3px solid transparent;color:' + DIM + ';font:inherit;font-size:12px;font-weight:700;cursor:pointer;' +
      '-webkit-tap-highlight-color:transparent;touch-action:manipulation;}' +
    '#msh-app .ma-nav button.on{color:' + NAVY + ';border-top-color:' + GOLD + ';}' +
    '#msh-app .ma-nav button:active{background:#f0f2f6;}' +
    /* phone fixes applied to the tools themselves */
    '#msh-app .ma-host div[style*="min-width"]{min-width:0!important;}' +
    '#msh-app .ma-host div[style*="flex-wrap"]>div[style*="min-width"]{flex:1 1 100%!important;}' +
    '#msh-app .ma-host>.ma-state{display:none;}' +
    '#msh-app .ma-host.empty>.ma-state{display:block;}' +
    '#msh-app .ma-host input,#msh-app .ma-host select,#msh-app .ma-host textarea{font-size:16px!important;min-height:48px;max-width:100%;}' +
    '#msh-app .ma-host input[type=checkbox],#msh-app .ma-host input[type=radio]{min-height:0;width:22px;height:22px;}' +
    '#msh-app .ma-host button,#msh-app .ma-host [role=button]{min-height:48px;touch-action:manipulation;}' +
    '#msh-app .ma-host table{display:block;max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;}' +
    '#msh-app .ma-host img{max-width:100%;height:auto;}' +
    '#msh-app .ma-sheet{position:fixed;inset:0;background:rgba(11,28,51,.55);display:none;align-items:flex-end;z-index:2147483001;}' +
    '#msh-app .ma-sheet.on{display:flex;}' +
    '#msh-app .ma-sheet>div{background:#fff;width:100%;border-radius:16px 16px 0 0;padding:20px 20px calc(20px + env(safe-area-inset-bottom));}' +
    '#msh-app .ma-sheet h2{font-size:18px;margin:0 0 10px;}' +
    '#msh-app .ma-sheet ol{margin:0 0 16px;padding-left:22px;}' +
    '#msh-app .ma-sheet li{margin-bottom:8px;}' +
    '#msh-app .ma-sheet button{width:100%;min-height:52px;border-radius:26px;border:0;background:' + NAVY + ';color:#fff;font:inherit;font-weight:800;cursor:pointer;}';
  var st = document.createElement('style');
  st.id = 'msh-app-css';
  st.textContent = css;
  document.head.appendChild(st);

  /* ---------- shell ---------- */
  var app = document.createElement('div');
  app.id = 'msh-app';
  app.innerHTML =
    '<header class="ma-top"><div><div class="ma-kick">Med Sales Intelligence Hub</div><h1 class="ma-title" id="maTitle"></h1></div>' +
      '<button type="button" class="ma-inst" id="maInst">' + svg('install', 18) + 'Install</button></header>' +
    '<main class="ma-main" id="maMain"></main>' +
    '<nav class="ma-nav" id="maNav" aria-label="Hub tools"></nav>' +
    '<div class="ma-sheet" id="maSheet" role="dialog" aria-modal="true" aria-labelledby="maSheetH"><div>' +
      '<h2 id="maSheetH">Put the Hub on your home screen</h2><ol id="maSteps"></ol>' +
      '<button type="button" id="maSheetX">Got it</button></div></div>';
  MOUNT.appendChild(app);
  document.documentElement.classList.add('msh-app-on');

  var main = document.getElementById('maMain');
  var nav = document.getElementById('maNav');
  var titleEl = document.getElementById('maTitle');
  var panels = {};

  TABS.forEach(function (t) {
    var p = document.createElement('section');
    p.className = 'ma-panel' + (t.dark ? ' dark' : '');
    p.setAttribute('aria-label', t.title);
    main.appendChild(p);
    panels[t.key] = p;

    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('data-tab', t.key);
    b.innerHTML = svg(t.key, 26) + '<span>' + t.label + '</span>';
    b.addEventListener('click', function () { go(t.key, true); });
    nav.appendChild(b);
  });

  /* ---------- loading a tool ---------- */
  var loaded = {};
  function load(t) {
    var p = panels[t.key];
    if (loaded[t.key]) { return; }
    loaded[t.key] = 'loading';
    p.innerHTML = '<div class="ma-state"><div class="ma-spin"></div>Loading ' + t.title + '…</div>';
    fetch(BASE + t.file + '?v=' + Date.now(), { cache: 'no-store' })
      .then(function (r) { if (!r.ok) { throw new Error('HTTP ' + r.status); } return r.text(); })
      .then(function (code) {
        p.innerHTML = '';
        var host = document.createElement('div');
        host.className = 'ma-host empty';
        var m = document.createElement('div');
        m.id = t.mount;
        host.appendChild(m);
        /* Some tools leave their mount empty while their data downloads.
           Keep the spinner up until the tool puts something in it. */
        var wait = document.createElement('div');
        wait.className = 'ma-state';
        wait.innerHTML = '<div class="ma-spin"></div>Loading ' + t.title + '\u2026';
        host.appendChild(wait);
        p.appendChild(host);
        function filled() {
          if (!m.firstChild) { return false; }
          host.classList.remove('empty');
          if (t.key === 'search') { openSearch(m); }
          return true;
        }
        var s = document.createElement('script');
        s.textContent = code + '\n//# sourceURL=' + t.file;
        document.body.appendChild(s);
        loaded[t.key] = 'done';
        if (!filled() && window.MutationObserver) {
          var mo = new MutationObserver(function () { if (filled()) { mo.disconnect(); } });
          mo.observe(m, { childList: true });
        }
      })
      .catch(function () {
        loaded[t.key] = false;
        p.innerHTML = '<div class="ma-state">' + t.title + ' didn’t load. Check your signal and try again.<br>' +
          '<button type="button">Try again</button></div>';
        p.querySelector('button').addEventListener('click', function () { load(t); });
      });
  }

  /* Hub search starts collapsed on the desktop Live Desk so it doesn't push
     the headlines down. In the app it has a tab to itself, so open it. */
  function openSearch(m) {
    var tg = m.querySelector('#ethHubToggle');
    if (tg && tg.getAttribute('aria-expanded') !== 'true') { tg.click(); }
  }

  /* ---------- tabs + back button ---------- */
  var LS = 'msh-app-tab';
  var current = null;
  function go(key, push) {
    var t = BY[key] || TABS[0];
    if (current === t.key) { main.scrollTop = 0; return; }
    current = t.key;
    TABS.forEach(function (x) { panels[x.key].classList.toggle('on', x.key === t.key); });
    Array.prototype.forEach.call(nav.children, function (b) {
      var on = b.getAttribute('data-tab') === t.key;
      b.classList.toggle('on', on);
      if (on) { b.setAttribute('aria-current', 'page'); } else { b.removeAttribute('aria-current'); }
    });
    titleEl.textContent = t.title;
    main.scrollTop = 0;
    load(t);
    try { localStorage.setItem(LS, t.key); } catch (e) {}
    if (push && location.hash !== '#' + t.key) { history.pushState(null, '', '#' + t.key); }
  }
  window.addEventListener('popstate', function () {
    var k = location.hash.replace('#', '');
    if (BY[k]) { go(k, false); }
  });
  var start = location.hash.replace('#', '');
  if (!BY[start]) { try { start = localStorage.getItem(LS); } catch (e) { start = null; } }
  go(BY[start] ? start : TABS[0].key, false);

  /* ---------- install button ---------- */
  var instBtn = document.getElementById('maInst');
  var sheet = document.getElementById('maSheet');
  var standalone = (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) || navigator.standalone === true;
  var ua = navigator.userAgent || '';
  var isIOS = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
  var deferred = null;

  function steps() {
    var list = isIOS
      ? ['Tap the <strong>Share</strong> button (the square with an arrow). In Safari it’s at the bottom of the screen; in Chrome it’s at the top right.',
         'Scroll down and tap <strong>Add to Home Screen</strong>.',
         'Tap <strong>Add</strong>. The Hub opens full screen from its own icon. Log in once the first time you open it.']
      : ['Tap your browser’s <strong>menu</strong> (⋮, top right).',
         'Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.',
         'Confirm. The Hub opens from its own icon. Log in once the first time you open it.'];
    document.getElementById('maSteps').innerHTML = list.map(function (s) { return '<li>' + s + '</li>'; }).join('');
  }
  if (!standalone) { instBtn.classList.add('show'); }
  window.addEventListener('beforeinstallprompt', function (e) { e.preventDefault(); deferred = e; });
  window.addEventListener('appinstalled', function () { instBtn.classList.remove('show'); });
  instBtn.addEventListener('click', function () {
    if (deferred) {
      deferred.prompt();
      deferred.userChoice.then(function (c) { if (c && c.outcome === 'accepted') { instBtn.classList.remove('show'); } });
      deferred = null;
      return;
    }
    steps();
    sheet.classList.add('on');
  });
  document.getElementById('maSheetX').addEventListener('click', function () { sheet.classList.remove('on'); });
  sheet.addEventListener('click', function (e) { if (e.target === sheet) { sheet.classList.remove('on'); } });
})();
