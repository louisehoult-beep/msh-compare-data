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
      '.msh .mshc-bar .mshc-star:hover{border-color:#0B1C33;}',
      '.msh .mshc-bar .mshc-star:focus-visible{outline:3px solid #1B5FBF;outline-offset:2px;}',
      '.msh .mshc-bar .mshc-star .mshc-svg{width:16px;height:16px;display:block;}',
      '.msh .mshc-bar .mshc-star[aria-pressed="true"]{background:#F7F1E3;border-color:#B8935A;color:#7E6118!important;}',
      '.msh .mshc-bar .mshc-star[aria-pressed="true"] .mshc-svg{fill:#C9A227;stroke:#8C6A1C;}',
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

  function watchNav() {
    var nav = document.querySelector('.msh header nav');
    if (!nav) { return; }
    if (!window.MutationObserver) { return; }
    new MutationObserver(function () { decorateNav(); }).observe(nav, { childList: true, subtree: true });
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
    bar.innerHTML = '<div class="mshc-in"><span class="mshc-pi" aria-hidden="true">' + I.svg(it ? I.forItem(it) : 'file', 'mshc-svg') + '</span>'
      + '<span class="mshc-t"></span><button type="button" class="mshc-star" aria-pressed="false">' + I.svg('star', 'mshc-svg') + '<span class="mshc-l">Save</span></button></div>';
    bar.querySelector('.mshc-t').textContent = title;
    header.parentNode.insertBefore(bar, header.nextSibling);
    var btn = bar.querySelector('.mshc-star');
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
      watchNav();
      if (NO_BAR.indexOf(here) !== -1) { return; }
      if (!(window.mshRestNonce || window.mshPrefsNonce)) { return; }
      pageBar();
    }).catch(function () {});
  }

  if (document.readyState === 'complete') { boot(); } else { window.addEventListener('load', boot); }
})();
