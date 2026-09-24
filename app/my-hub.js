/* Medical Sales Hub — My Hub, the member's working front page.
   Lou, 24/09/2026: "this will be the page reps work from". So the page leads
   with what changed, not with a list of links:

     1. Key news: the newest stories across every speciality feed, lead story
        open, the rest one click from their summary, "Show all" for the lot.
     2. The top items from each Hub section: Coming up (events and awareness
        days), Safety alerts (MHRA), Procurement deadlines (framework and
        contract dates). Four each, "Show all" drops the rest down, and every
        panel links to its full Hub page.
     3. The member's own pages, as tiles, in their order (unchanged from
        23/09/2026: "so they can select the things from the Hub they want to
        see").

   A "Your specialities / Whole Hub" switch narrows news, events and
   procurement to the specialities the member pinned. MHRA alerts are never
   narrowed: gov.uk tags them with its own specialism list, which does not map
   to Hub pages, and a filter that guesses could hide a recall.

   Mounted on <div id="msh-my-hub"></div> on /medical-sales-hub/my-hub/. The
   WordPress page carries a loader only; edit the code HERE.

   WHAT CAN BE PICKED: hub/my-hub-catalogue.json, published pages only. A
   saved id that is no longer in the catalogue is dropped from view, never
   shown as a dead link, and kept in storage so re-adding the page restores it.

   DATA, all read-only from this repo, the same files the section pages use:
     data/speciality-news/<id>.json  news (one file per speciality)
     data/hub-calendar.json          events, awareness days, procurement dates
     data/mhra-alerts.json           MHRA device and patient safety alerts
   A feed that fails to load shows an honest empty panel, never stale copy.

   WHERE CHOICES ARE SAVED, in order:
     1. The member's Hub account, via /wp-json/msh/v1/my-hub (WPCode snippet
        hub/wpcode/my-hub-pins.php, user meta msh_hub_pins). Follows them
        across devices.
     2. This browser (localStorage), if the account save is unavailable. The
        page says so, so nobody thinks a phone copy is on their laptop.
   First visit with nothing saved: seeded from the interests already set on
   the old My Hub (/wp-json/msh/v1/prefs), shown as a starting point. */
(function () {
  var mount = document.getElementById('msh-my-hub');
  if (!mount) { return; }
  var RAW = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var CAT_URL = RAW + 'hub/my-hub-catalogue.json';
  var NEWS_URL = RAW + 'data/speciality-news/';
  var CAL_URL = RAW + 'data/hub-calendar.json';
  var MHRA_URL = RAW + 'data/mhra-alerts.json';
  var API = '/wp-json/msh/v1/my-hub';
  var PREFS = '/wp-json/msh/v1/prefs';
  var LS = 'msh_my_hub_pins_v1';
  var LS_SCOPE = 'msh_my_hub_scope_v1';

  var NEWS_TOP = 6;       // lead story + five headlines before "Show all"
  var PANEL_TOP = 4;      // rows per section panel before "Show all"
  var EVENT_DAYS = 90;    // how far ahead "Coming up" looks
  var PROC_DAYS = 180;    // procurement dates are planned further out
  var NEW_DAYS = 14;      // an alert this recent carries a "New" flag

  var PAGES = {
    news: '/medical-sales-hub/news/',
    calendar: '/medical-sales-hub/calendar/',
    mhra: '/medical-sales-hub/mhra-regulatory-desk/',
    procurement: '/medical-sales-hub/tender-history/'
  };
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  var CAT = null, BYID = {}, pins = [], where = 'none', seeded = false;
  var draft = null, query = '';
  var scope = lsRaw(LS_SCOPE) === 'all' ? 'all' : 'mine';
  var FEED = { news: null, cal: null, mhra: null };   // null = loading, false = failed
  var openRows = {}, openPanels = {};

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function nonce() { return window.mshRestNonce || window.mshPrefsNonce || ''; }
  function lsRaw(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsGet() { try { var v = JSON.parse(localStorage.getItem(LS) || 'null'); return Array.isArray(v) ? v : null; } catch (e) { return null; } }
  function lsSet(v) { try { localStorage.setItem(LS, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function visible(list) { return list.filter(function (id) { return !!BYID[id]; }); }

  /* ---------- dates: ISO in, UK out, local calendar days throughout ---------- */
  function isoDay(d) {
    var m = d.getMonth() + 1, dd = d.getDate();
    return d.getFullYear() + '-' + (m < 10 ? '0' : '') + m + '-' + (dd < 10 ? '0' : '') + dd;
  }
  function parseDay(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || '');
    return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
  }
  function addDays(s, n) { var d = parseDay(s); d.setDate(d.getDate() + n); return isoDay(d); }
  var TODAY = isoDay(new Date());
  function fmtDate(s) {
    var d = parseDay(s);
    return d ? d.getDate() + ' ' + MONTHS[d.getMonth()] + ' ' + d.getFullYear() : '';
  }
  function daysFrom(s) {
    var d = parseDay(s), t = parseDay(TODAY);
    return d ? Math.round((d - t) / 86400000) : null;
  }
  function whenLabel(s) {
    var n = daysFrom(s);
    if (n === null) { return ''; }
    if (n === 0) { return 'Today'; }
    if (n === 1) { return 'Tomorrow'; }
    if (n === -1) { return 'Yesterday'; }
    if (n > 1) { return 'In ' + n + ' days'; }
    return (-n) + ' days ago';
  }
  function dateChip(s) {
    var d = parseDay(s);
    if (!d) { return '<span class="mh-chip"></span>'; }
    return '<span class="mh-chip"><i>' + DAYS[d.getDay()] + '</i><b>' + d.getDate() + '</b><i>' + MONTHS[d.getMonth()] + '</i></span>';
  }
  function money(v) {
    if (typeof v !== 'number' || !isFinite(v)) { return ''; }
    if (v >= 1e6) { return '£' + (Math.round(v / 1e5) / 10) + 'm'; }
    if (v >= 1e3) { return '£' + Math.round(v / 1e3) + 'k'; }
    return '£' + Math.round(v);
  }

  function css() {
    if (document.getElementById('msh-myh3-css')) { return; }
    var st = document.createElement('style');
    st.id = 'msh-myh3-css';
    st.textContent = [
      /* toolbar */
      '.msh .mh-toolbar{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:22px;}',
      '.msh .mh-scope{display:inline-flex;background:#fff;border:1px solid var(--border);border-radius:999px;padding:3px;}',
      '.msh .mh-scope button{border:0;background:none;border-radius:999px;padding:8px 16px;font:600 13px Inter,sans-serif;color:#1D2733;cursor:pointer;}',
      '.msh .mh-scope button[aria-pressed="true"]{background:#0B1C33;color:#FFFFFF;}',
      '.msh .mh-scope button:disabled{color:#9aa3ad;cursor:default;}',
      '.msh .mh-scope-note{font-size:12.5px;color:var(--dim);margin-left:10px;}',
      '.msh .mh-btn{display:inline-block;background:#A8842C;color:#FFFFFF;border:0;border-radius:8px;padding:10px 18px;font:700 13.5px Inter,sans-serif;cursor:pointer;}',
      '.msh .mh-btn:hover{background:#8a6c22;color:#FFFFFF;}',
      '.msh .mh-btn.ghost{background:#fff;color:#1D2733;border:1px solid var(--border);}',
      '.msh .mh-btn.ghost:hover{border-color:#A8842C;color:#A8842C;}',
      /* panels */
      '.msh .mh-panel{background:#fff;border:1px solid var(--border);border-radius:14px;padding:22px 24px;box-shadow:0 1px 3px rgba(11,28,51,.06);}',
      '.msh .mh-ph{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px;padding-bottom:12px;border-bottom:2px solid #0B1C33;}',
      '.msh .mh-ph h2{font-size:12px;letter-spacing:2px;font-weight:800;color:#0B1C33;text-transform:uppercase;display:flex;align-items:center;gap:10px;}',
      '.msh .mh-ph h2 .n{background:#0B1C33;color:#FFFFFF;border-radius:999px;font-size:11px;letter-spacing:0;padding:2px 9px;}',
      '.msh .mh-ph a{font-size:12.5px;font-weight:700;color:#A8842C;white-space:nowrap;}',
      '.msh .mh-ph a:hover{text-decoration:underline;}',
      '.msh .mh-sub{font-size:12px;color:var(--dim);margin:-6px 0 12px;line-height:1.5;}',
      '.msh .mh-empty{color:var(--dim);line-height:1.65;font-size:13.5px;padding:8px 0;}',
      '.msh .mh-empty button{background:none;border:0;color:#A8842C;font:700 13.5px Inter,sans-serif;cursor:pointer;padding:0;}',
      '.msh .mh-loading{color:var(--dim);font-size:13px;padding:10px 0;}',
      '.msh .mh-more{display:block;width:100%;margin-top:12px;background:#f7f4ee;border:1px solid var(--border);border-radius:8px;padding:9px 12px;font:700 12.5px Inter,sans-serif;color:#1D2733;cursor:pointer;text-align:center;}',
      '.msh .mh-more:hover{border-color:#A8842C;color:#A8842C;}',
      /* key news */
      '.msh .mh-news-panel{margin-bottom:22px;}',
      '.msh .mh-newsgrid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:26px;}',
      '.msh .mh-lead{background:#0B1C33;border-radius:12px;padding:24px 26px;display:flex;flex-direction:column;gap:12px;}',
      '.msh .mh-lead .k{font-size:10.5px;letter-spacing:1.6px;font-weight:800;text-transform:uppercase;color:#E0BE8E!important;}',
      '.msh .mh-panel .mh-lead a.t{font-size:21px;line-height:1.3;font-weight:700;color:#FFFFFF!important;}',
      '.msh .mh-panel .mh-lead a.t:hover{color:#E0BE8E!important;}',
      '.msh .mh-panel .mh-lead p.s{font-size:14.5px;line-height:1.65;color:#DBE3EE!important;}',
      '.msh .mh-lead .m{font-size:12px;color:#DBE3EE!important;}',
      '.msh .mh-lead .acts{display:flex;gap:16px;flex-wrap:wrap;margin-top:auto;padding-top:6px;}',
      '.msh .mh-panel .mh-lead .acts a{font-size:13px;font-weight:700;color:#E0BE8E!important;}',
      '.msh .mh-panel .mh-lead .acts a:hover{color:#FFFFFF!important;}',
      '.msh .mh-opp{display:inline-block;padding:2px 7px;border-radius:3px;background:#E0BE8E;color:#0B1C33!important;font-size:9.5px;font-weight:800;letter-spacing:1px;text-transform:uppercase;vertical-align:2px;margin-right:6px;}',
      '.msh .mh-new{display:inline-block;padding:2px 7px;border-radius:3px;background:#9b2c2c;color:#FFFFFF!important;font-size:9.5px;font-weight:800;letter-spacing:1px;text-transform:uppercase;vertical-align:2px;margin-right:6px;}',
      '.msh .mh-rest-all{columns:2 420px;column-gap:26px;margin-top:6px;}',
      '.msh .mh-rest-all .mh-item{break-inside:avoid;}',
      /* rows (news, events, alerts, procurement) */
      '.msh .mh-list{list-style:none;}',
      '.msh .mh-item{border-bottom:1px solid var(--border);}',
      '.msh .mh-item:last-child{border-bottom:0;}',
      '.msh .mh-row{display:flex;gap:12px;align-items:flex-start;width:100%;background:none;border:0;text-align:left;padding:11px 2px;cursor:pointer;font:inherit;color:#1D2733;}',
      '.msh .mh-row:hover .tt{color:#A8842C;}',
      '.msh .mh-row .bd{flex:1;min-width:0;}',
      '.msh .mh-row .tt{display:block;font-weight:600;font-size:14px;line-height:1.4;color:#1D2733;}',
      '.msh .mh-row .mm{display:block;font-size:11.5px;color:var(--dim);margin-top:3px;}',
      '.msh .mh-row .ch{flex:none;color:#9aa3ad;font-size:12px;margin-top:3px;transition:transform .15s;}',
      '.msh .mh-item.open .mh-row .ch{transform:rotate(180deg);color:#A8842C;}',
      '.msh .mh-det{display:none;padding:0 2px 14px 2px;font-size:13.5px;line-height:1.6;color:#1D2733;}',
      '.msh .mh-item.open .mh-det{display:block;}',
      '.msh .mh-det p{margin-bottom:8px;}',
      '.msh .mh-det .why{background:#f7f4ee;border-left:3px solid #A8842C;padding:8px 12px;border-radius:0 6px 6px 0;margin-bottom:8px;}',
      '.msh .mh-det .lk{display:flex;gap:14px;flex-wrap:wrap;}',
      '.msh .mh-det .lk a{font-weight:700;font-size:12.5px;color:#A8842C;}',
      '.msh .mh-det .lk a:hover{text-decoration:underline;}',
      '.msh .mh-withchip .mh-det{padding-left:62px;}',
      '.msh .mh-chip{flex:none;width:50px;border:1px solid var(--border);border-radius:8px;text-align:center;padding:4px 0;background:#fff;line-height:1.1;}',
      '.msh .mh-chip i{display:block;font-style:normal;font-size:9.5px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:var(--dim);}',
      '.msh .mh-chip b{display:block;font-size:18px;color:#0B1C33;}',
      '.msh .mh-tag{display:inline-block;font-size:10px;font-weight:800;letter-spacing:.9px;text-transform:uppercase;padding:1px 6px;border-radius:3px;margin-right:6px;vertical-align:1px;}',
      '.msh .mh-tag.ev{background:#e6edf6;color:#14304F;}',
      '.msh .mh-tag.aw{background:#e7f2ec;color:#1f5c42;}',
      '.msh .mh-tag.fw{background:#f4ecd9;color:#6b5418;}',
      '.msh .mh-tag.ct{background:#f3e3e3;color:#7a2424;}',
      '.msh .mh-tag.np{background:#9b2c2c;color:#FFFFFF;}',
      '.msh .mh-tag.ds{background:#f4ecd9;color:#6b5418;}',
      /* section grid */
      '.msh .mh-sections{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:22px;margin-bottom:22px;align-items:start;}',
      /* your pages */
      '.msh .mh-tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;}',
      '.msh .mh-tile{display:block;background:#fff;border:1px solid var(--border);border-radius:10px;padding:14px 16px;border-top:3px solid #0B1C33;}',
      '.msh .mh-tile:hover{border-color:#A8842C;border-top-color:#A8842C;}',
      '.msh .mh-tile b{display:block;font-size:14.5px;line-height:1.35;color:#1D2733;}',
      '.msh .mh-tile span{display:block;font-size:10.5px;letter-spacing:1px;text-transform:uppercase;color:var(--dim);margin-top:6px;}',
      '.msh .mh-note{font-size:12.5px;color:var(--dim);line-height:1.6;margin-top:12px;}',
      '.msh .mh-note.warn{color:#8a4b12;}',
      /* editor (unchanged behaviour) */
      '.msh .mh-bar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:16px;}',
      '.msh .mh-bar h2{font-size:11.5px;letter-spacing:2px;font-weight:700;color:#A8842C;text-transform:uppercase;}',
      '.msh .mh-edit .mh-panel{margin-bottom:18px;}',
      '.msh .mh-tools{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;}',
      '.msh .mh-tools input,.msh .mh-tools select{flex:1 1 220px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;font:14px Inter,sans-serif;color:#1D2733;background:#fff;}',
      '.msh .mh-group{border-top:1px solid var(--border);padding:12px 0;}',
      '.msh .mh-group summary{cursor:pointer;font-weight:700;font-size:13.5px;display:flex;justify-content:space-between;gap:10px;}',
      '.msh .mh-group summary em{font-style:normal;font-weight:600;font-size:12px;color:var(--dim);}',
      '.msh .mh-opts{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:4px 14px;margin-top:10px;}',
      '.msh .mh-opts label{display:flex;gap:8px;align-items:flex-start;font-size:13.5px;line-height:1.4;padding:5px 0;cursor:pointer;}',
      '.msh .mh-opts input{margin-top:3px;accent-color:#A8842C;}',
      '.msh .mh-order{list-style:none;}',
      '.msh .mh-order li{display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--border);font-size:13.5px;}',
      '.msh .mh-order li span{flex:1;}',
      '.msh .mh-order button{background:#fff;border:1px solid var(--border);border-radius:6px;width:30px;height:28px;cursor:pointer;color:#1D2733;font-size:13px;}',
      '.msh .mh-order button:hover{border-color:#A8842C;color:#A8842C;}',
      '.msh .mh-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px;}',
      '.msh .mh-link{background:none;border:0;color:#A8842C;font:600 12px Inter,sans-serif;cursor:pointer;padding:0;}',
      '@media(max-width:860px){.msh .mh-newsgrid{grid-template-columns:1fr;gap:16px;}.msh .mh-sections{grid-template-columns:1fr;}.msh .mh-panel{padding:18px 16px;}.msh .mh-withchip .mh-det{padding-left:2px;}.msh .mh-panel .mh-lead a.t{font-size:18px;}}'
    ].join('');
    document.head.appendChild(st);
  }

  function groupLabel(gid) {
    var g = (CAT.groups || []).filter(function (x) { return x.id === gid; })[0];
    return g ? g.label : '';
  }

  /* The member's pinned specialities, which the "Your specialities" switch uses. */
  function mySpecs() {
    var out = {};
    visible(pins).forEach(function (id) { if (BYID[id].group === 'specialities') { out[id] = 1; } });
    return out;
  }
  function hasSpecs() { return Object.keys(mySpecs()).length > 0; }
  function narrowed() { return scope === 'mine' && hasSpecs(); }

  /* ---------- feeds ---------- */
  function getRaw(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error(r.status); } return r.json(); });
  }
  function loadFeeds() {
    if (FEED.news === null) {
      var ids = CAT.items.filter(function (it) { return it.news; }).map(function (it) { return it.id; });
      var got = [], left = ids.length, ok = 0;
      if (!left) { FEED.news = []; }
      ids.forEach(function (id) {
        getRaw(NEWS_URL + encodeURIComponent(id) + '.json')
          .then(function (d) { ok++; ((d && d.items) || []).forEach(function (it) { if (it && it.title && it.link) { got.push({ it: it, spec: id }); } }); })
          .catch(function () {})
          .then(function () {
            if (--left) { return; }
            // One story syndicated under two links is still one story.
            var seen = {};
            got = got.filter(function (g) {
              var k = String(g.it.title).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
              if (seen[g.it.link] || seen[k]) { return false; }
              seen[g.it.link] = 1; seen[k] = 1; return true;
            });
            got.sort(function (a, b) {
              var c = String(b.it.published || '').localeCompare(String(a.it.published || ''));
              return c || (b.it.opportunity ? 1 : 0) - (a.it.opportunity ? 1 : 0);
            });
            FEED.news = ok ? got : false;
            paintSections();
          });
      });
    }
    if (FEED.cal === null) {
      getRaw(CAL_URL).then(function (d) { FEED.cal = (d && d.entries) || []; })
        .catch(function () { FEED.cal = false; }).then(paintSections);
    }
    if (FEED.mhra === null) {
      getRaw(MHRA_URL).then(function (d) {
        FEED.mhra = ((d && d.alerts) || []).slice().sort(function (a, b) { return String(b.issuedDate || '').localeCompare(String(a.issuedDate || '')); });
      }).catch(function () { FEED.mhra = false; }).then(paintSections);
    }
  }

  function specMatch(list) {
    if (!narrowed()) { return true; }
    var mine = mySpecs();
    return (list || []).some(function (s) { return !!mine[s]; });
  }

  /* ---------- rows ---------- */
  function row(key, head, detail, chip) {
    var open = !!openRows[key];
    return '<li class="mh-item' + (open ? ' open' : '') + '">'
      + '<button type="button" class="mh-row" data-row="' + esc(key) + '" aria-expanded="' + (open ? 'true' : 'false') + '">'
      + (chip || '') + '<span class="bd">' + head + '</span><span class="ch" aria-hidden="true">▾</span></button>'
      + '<div class="mh-det">' + detail + '</div></li>';
  }
  function links(list) {
    var seen = {};
    var h = list.filter(function (l) {
      if (!l || !l.url || seen[l.url]) { return false; }
      seen[l.url] = 1; return true;
    }).map(function (l) {
      var ext = /^https?:/.test(l.url) && l.url.indexOf('medsalesintelligencehub.co.uk') === -1;
      return '<a href="' + esc(l.url) + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + '>' + esc(l.label) + (ext ? ' ↗' : ' →') + '</a>';
    }).join('');
    return h ? '<div class="lk">' + h + '</div>' : '';
  }
  function moreBtn(panel, total, shown, noun) {
    if (total <= shown) { return ''; }
    var open = !!openPanels[panel];
    return '<button type="button" class="mh-more" data-more="' + panel + '" aria-expanded="' + (open ? 'true' : 'false') + '">'
      + (open ? 'Show fewer ▴' : 'Show all ' + total + ' ' + noun + ' ▾') + '</button>';
  }
  function emptyMine(what) {
    return '<p class="mh-empty">Nothing ' + what + ' for your specialities right now. <button type="button" data-scope="all">Show the whole Hub</button></p>';
  }

  /* ---------- key news ---------- */
  function newsPanel() {
    var h = '<section class="mh-panel mh-news-panel" id="mh-news"><div class="mh-ph"><h2>Key news';
    var list = FEED.news;
    if (list) { list = spread(list.filter(function (g) { return specMatch([g.spec]); })); h += ' <span class="n">' + list.length + '</span>'; }
    h += '</h2><a href="' + PAGES.news + '">All Hub news →</a></div>';
    if (list === null) { return h + '<p class="mh-loading">Loading the latest news…</p></section>'; }
    if (list === false) { return h + '<p class="mh-empty">The news feed couldn’t be reached just now. Each speciality page still carries its own feed.</p></section>'; }
    if (!list.length) { return h + (narrowed() ? emptyMine('new in the last 60 days') : '<p class="mh-empty">No news in the last 60 days.</p>') + '</section>'; }

    var lead = list[0], it = lead.it, spec = BYID[lead.spec];
    h += '<div class="mh-newsgrid"><article class="mh-lead">'
      + '<span class="k">' + (it.opportunity ? '<span class="mh-opp">Opportunity</span>' : '') + 'Latest · ' + esc(spec.label) + '</span>'
      + '<a class="t" href="' + esc(it.link) + '" target="_blank" rel="noopener">' + esc(it.title) + '</a>'
      + (it.summary ? '<p class="s">' + esc(it.summary) + '</p>' : '')
      + '<span class="m">' + esc([fmtDate(it.published), it.source].filter(Boolean).join(' · ')) + '</span>'
      + '<div class="acts"><a href="' + esc(it.link) + '" target="_blank" rel="noopener">Read the full story ↗</a>'
      + '<a href="' + esc(spec.url) + '">Open ' + esc(spec.label) + ' →</a></div></article>';

    var rest = list.slice(1);
    var showAll = !!openPanels.news;
    var top = rest.slice(0, NEWS_TOP - 1);
    h += '<ul class="mh-list">' + top.map(newsRow).join('') + '</ul></div>';
    if (showAll) { h += '<ul class="mh-list mh-rest-all">' + rest.slice(NEWS_TOP - 1).map(newsRow).join('') + '</ul>'; }
    h += moreBtn('news', list.length, NEWS_TOP, 'stories');
    return h + '</section>';
  }
  /* The stories above "Show all" carry at most two per speciality, so one
     busy trade feed can't fill the top of the page. Newest first still holds
     inside that, and nothing is dropped: the rest follow in date order. */
  function spread(list) {
    var top = [], rest = [], per = {};
    list.forEach(function (g) {
      if (top.length < NEWS_TOP && (per[g.spec] || 0) < 2) { top.push(g); per[g.spec] = (per[g.spec] || 0) + 1; }
      else { rest.push(g); }
    });
    return top.concat(rest);
  }
  function newsRow(g) {
    var it = g.it, spec = BYID[g.spec];
    var head = '<span class="tt">' + (it.opportunity ? '<span class="mh-opp">Opportunity</span>' : '') + esc(it.title) + '</span>'
      + '<span class="mm">' + esc([spec.label, fmtDate(it.published), it.source].filter(Boolean).join(' · ')) + '</span>';
    var det = (it.summary ? '<p>' + esc(it.summary) + '</p>' : '')
      + links([{ label: 'Read the full story', url: it.link }, { label: 'Open ' + spec.label, url: spec.url }]);
    return row('n:' + it.link, head, det);
  }

  /* ---------- coming up: events and awareness days ---------- */
  function eventsPanel() {
    var h = '<section class="mh-panel" id="mh-events"><div class="mh-ph"><h2>Coming up';
    var cal = FEED.cal, list = null;
    if (cal) {
      var end = addDays(TODAY, EVENT_DAYS);
      list = cal.filter(function (e) {
        return (e.type === 'event' || e.type === 'awareness') && (e.endDate || e.date) >= TODAY && e.date <= end && specMatch(e.specialities);
      }).sort(function (a, b) { return String(a.date).localeCompare(String(b.date)); });
      h += ' <span class="n">' + list.length + '</span>';
    }
    h += '</h2><a href="' + PAGES.calendar + '">The Calendar →</a></div><p class="mh-sub">Conferences, study days and awareness days in the next ' + EVENT_DAYS + ' days.</p>';
    if (cal === null) { return h + '<p class="mh-loading">Loading…</p></section>'; }
    if (cal === false) { return h + '<p class="mh-empty">The Calendar couldn’t be reached just now.</p></section>'; }
    if (!list.length) { return h + (narrowed() ? emptyMine('coming up') : '<p class="mh-empty">Nothing dated in the next ' + EVENT_DAYS + ' days.</p>') + '</section>'; }
    return h + panelList('events', list, 'events', function (e) {
      var aw = e.type === 'awareness';
      var when = e.endDate ? fmtDate(e.date) + ' to ' + fmtDate(e.endDate) : fmtDate(e.date);
      var head = '<span class="tt"><span class="mh-tag ' + (aw ? 'aw">Awareness' : 'ev">Event') + '</span>' + esc(e.title) + '</span>'
        + '<span class="mm">' + esc([whenLabel(e.date), e.location].filter(Boolean).join(' · ')) + '</span>';
      var det = '<p>' + esc([when, e.location, e.audience].filter(Boolean).join(' · ')) + '</p>'
        + (e.repAction ? '<p class="why">' + esc(e.repAction) + '</p>' : '')
        + (e.note && (!e.location || e.note.indexOf(e.location) === -1) ? '<p>' + esc(e.note) + '</p>' : '')
        + links((e.links || []).concat(e.source ? [{ label: 'Organiser’s page', url: e.source }] : []));
      return row('e:' + e.id, head, det, dateChip(e.date));
    }) + '</section>';
  }

  /* ---------- safety alerts: MHRA, never narrowed ---------- */
  function alertsPanel() {
    var list = FEED.mhra;
    var h = '<section class="mh-panel" id="mh-alerts"><div class="mh-ph"><h2>Safety alerts';
    if (list) { h += ' <span class="n">' + list.length + '</span>'; }
    h += '</h2><a href="' + PAGES.mhra + '">MHRA Regulatory Desk →</a></div><p class="mh-sub">Every recent MHRA device and patient safety alert. Not filtered by speciality, so nothing is missed.</p>';
    if (list === null) { return h + '<p class="mh-loading">Loading…</p></section>'; }
    if (list === false) { return h + '<p class="mh-empty">The MHRA feed couldn’t be reached just now. The Regulatory Desk has the full list.</p></section>'; }
    if (!list.length) { return h + '<p class="mh-empty">No alerts in the current window.</p></section>'; }
    return h + panelList('alerts', list, 'alerts', function (a) {
      var nat = a.alertType === 'national-patient-safety';
      var fresh = daysFrom(a.issuedDate) !== null && daysFrom(a.issuedDate) >= -NEW_DAYS;
      var head = '<span class="tt">' + (fresh ? '<span class="mh-new">New</span>' : '')
        + '<span class="mh-tag ' + (nat ? 'np">Patient safety' : 'ds">Device safety') + '</span>' + esc(a.title) + '</span>'
        + '<span class="mm">' + esc(['Issued ' + fmtDate(a.issuedDate), a.reference].filter(Boolean).join(' · ')) + '</span>';
      var det = (a.description ? '<p>' + esc(a.description) + '</p>' : '')
        + (a.play ? '<p class="why">' + esc(a.play) + '</p>' : '')
        + links([{ label: 'Read the alert on GOV.UK', url: a.url }]);
      return row('a:' + (a.reference || a.url), head, det);
    }) + '</section>';
  }

  /* ---------- procurement deadlines ---------- */
  var PROC = {
    'framework-start': ['fw', 'Framework starts'],
    'framework-end': ['fw', 'Framework ends'],
    'contract-expiry': ['ct', 'Contract ends'],
    'action-deadline': ['ct', 'Deadline']
  };
  function procPanel() {
    var h = '<section class="mh-panel" id="mh-proc"><div class="mh-ph"><h2>Procurement deadlines';
    var cal = FEED.cal, list = null;
    if (cal) {
      var end = addDays(TODAY, PROC_DAYS);
      list = cal.filter(function (e) { return PROC[e.type] && e.date >= TODAY && e.date <= end && specMatch(e.specialities); })
        .sort(function (a, b) { return String(a.date).localeCompare(String(b.date)); });
      h += ' <span class="n">' + list.length + '</span>';
    }
    h += '</h2><a href="' + PAGES.procurement + '">Frameworks and tenders →</a></div><p class="mh-sub">Framework and contract dates in the next six months: the re-tender windows.</p>';
    if (cal === null) { return h + '<p class="mh-loading">Loading…</p></section>'; }
    if (cal === false) { return h + '<p class="mh-empty">The Calendar couldn’t be reached just now.</p></section>'; }
    if (!list.length) { return h + (narrowed() ? emptyMine('due') : '<p class="mh-empty">No framework or contract dates in the next six months.</p>') + '</section>'; }
    return h + panelList('proc', list, 'dates', function (e) {
      var t = PROC[e.type];
      var head = '<span class="tt"><span class="mh-tag ' + t[0] + '">' + t[1] + '</span>' + esc(String(e.title || '').replace(/^(Framework (starts|expires|ends)|Contract expires):\s*/i, '')) + '</span>'
        + '<span class="mm">' + esc([whenLabel(e.date), e.buyer || e.owner, money(e.value)].filter(Boolean).join(' · ')) + '</span>';
      var det = '<p>' + esc([fmtDate(e.date), e.buyer ? 'Buyer: ' + e.buyer : '', e.supplier ? 'Supplier: ' + e.supplier : ''].filter(Boolean).join(' · ')) + '</p>'
        + (e.note ? '<p class="why">' + esc(e.note) + '</p>' : '')
        + links(e.links || (e.source ? [{ label: 'Source notice', url: e.source }] : []));
      return row('p:' + e.id, head, det, dateChip(e.date));
    }) + '</section>';
  }

  function panelList(panel, list, noun, fn) {
    var shown = openPanels[panel] ? list : list.slice(0, PANEL_TOP);
    return '<ul class="mh-list' + (panel === 'alerts' ? '' : ' mh-withchip') + '">' + shown.map(fn).join('') + '</ul>' + moreBtn(panel, list.length, PANEL_TOP, noun);
  }

  function paintSections() {
    var s = document.getElementById('mh-feeds');
    if (!s) { return; }
    s.innerHTML = newsPanel() + '<div class="mh-sections">' + eventsPanel() + alertsPanel() + procPanel() + '</div>';
  }

  /* ---------- the member's page ---------- */
  function toolbar() {
    var can = hasSpecs();
    var mine = narrowed();
    return '<div class="mh-toolbar"><div><div class="mh-scope" role="group" aria-label="Show news and dates for">'
      + '<button type="button" data-scope="mine" aria-pressed="' + (mine ? 'true' : 'false') + '"' + (can ? '' : ' disabled') + '>Your specialities</button>'
      + '<button type="button" data-scope="all" aria-pressed="' + (mine ? 'false' : 'true') + '">Whole Hub</button></div>'
      + (can ? '' : '<span class="mh-scope-note">Pin a speciality to narrow this page to your patch.</span>')
      + '</div><button type="button" class="mh-btn" data-act="edit">' + (visible(pins).length ? 'Choose what’s on my page' : 'Build my page') + '</button></div>';
  }

  function renderView() {
    var list = visible(pins);
    var h = toolbar() + '<div id="mh-feeds"></div>'
      + '<section class="mh-panel" id="mh-pages"><div class="mh-ph"><h2>Your pages';
    if (list.length) { h += ' <span class="n">' + list.length + '</span>'; }
    h += '</h2><a href="#" data-act="edit">Change →</a></div>';
    if (!list.length) {
      h += '<p class="mh-empty">Pick the Hub pages you use most: your specialities, the desks you check, the tools you open. They’ll sit here, in your order, and your specialities narrow the news and dates above to your patch.</p>'
        + '<button type="button" class="mh-btn" data-act="edit">Build my page</button>';
    } else {
      if (seeded) { h += '<p class="mh-note" style="margin:0 0 12px;">This is a starting point from the interests you set earlier. Nothing is saved until you choose and save.</p>'; }
      h += '<div class="mh-tiles">' + list.map(function (id) {
        var it = BYID[id];
        return '<a class="mh-tile" href="' + esc(it.url) + '"><b>' + esc(it.label) + '</b><span>' + esc(groupLabel(it.group)) + '</span></a>';
      }).join('') + '</div>';
    }
    h += saveNote() + '</section>';
    mount.innerHTML = h;
    paintSections();
    loadFeeds();
  }

  function saveNote() {
    if (where === 'account') { return '<p class="mh-note">Saved to your Hub account, so it follows you across devices.</p>'; }
    if (where === 'device') { return '<p class="mh-note warn">Saved on this device only. Your account couldn’t be reached, so your choices won’t show on another phone or computer yet.</p>'; }
    return '';
  }

  /* ---------- choosing ---------- */
  function renderEdit() {
    var chosen = {};
    draft.forEach(function (id) { chosen[id] = 1; });
    var q = query.toLowerCase();
    var roles = CAT.roles || {};
    var h = '<div class="mh-edit"><div class="mh-bar"><h2>Choose what’s on your page</h2><em style="font-style:normal;font-size:12.5px;color:var(--dim);">' + draft.length + ' chosen</em></div>'
      + '<div class="mh-panel"><div class="mh-tools">'
      + '<input type="search" id="mh-q" placeholder="Search Hub pages…" value="' + esc(query) + '">'
      + '<select id="mh-role"><option value="">Add a starter set for my role…</option>'
      + Object.keys(roles).map(function (k) { return '<option value="' + esc(k) + '">' + esc(roles[k].label) + '</option>'; }).join('')
      + '</select></div>';
    (CAT.groups || []).forEach(function (g) {
      var rows = CAT.items.filter(function (it) { return it.group === g.id && (!q || it.label.toLowerCase().indexOf(q) !== -1); });
      if (!rows.length) { return; }
      var n = rows.filter(function (it) { return chosen[it.id]; }).length;
      h += '<details class="mh-group"' + (q || n || g.id === 'specialities' ? ' open' : '') + '><summary>' + esc(g.label) + ' <em>' + n + ' of ' + rows.length + '</em></summary><div class="mh-opts">'
        + rows.map(function (it) {
          return '<label><input type="checkbox" data-id="' + esc(it.id) + '"' + (chosen[it.id] ? ' checked' : '') + '>' + esc(it.label) + (it.news ? ' <small style="color:var(--green);font-weight:600;">+ news</small>' : '') + '</label>';
        }).join('') + '</div></details>';
    });
    h += '</div>';
    var ord = visible(draft);
    if (ord.length) {
      h += '<div class="mh-panel"><div class="mh-bar"><h2>Your order</h2><button type="button" class="mh-link" data-act="clear">Clear all</button></div><ol class="mh-order">'
        + ord.map(function (id, i) {
          return '<li><span>' + esc(BYID[id].label) + '</span>'
            + '<button type="button" data-mv="' + i + '" data-d="-1" aria-label="Move up"' + (i ? '' : ' disabled') + '>↑</button>'
            + '<button type="button" data-mv="' + i + '" data-d="1" aria-label="Move down"' + (i < ord.length - 1 ? '' : ' disabled') + '>↓</button>'
            + '<button type="button" data-rm="' + esc(id) + '" aria-label="Remove">✕</button></li>';
        }).join('') + '</ol></div>';
    }
    h += '<div class="mh-actions"><button type="button" class="mh-btn" data-act="save">Save my page</button>'
      + '<button type="button" class="mh-btn ghost" data-act="cancel">Cancel</button></div></div>';
    mount.innerHTML = h;
    var qi = document.getElementById('mh-q');
    if (qi && query) { qi.focus(); qi.setSelectionRange(query.length, query.length); }
  }

  function startEdit() { draft = visible(pins).slice(); query = ''; renderEdit(); mount.scrollIntoView({ behavior: 'smooth', block: 'start' }); }

  function save() {
    var keep = pins.filter(function (id) { return !BYID[id]; }); // retired pages stay stored, unseen
    var next = visible(draft).concat(keep);
    pins = next; seeded = false; draft = null;
    lsSet(next);
    where = 'device';
    renderView();
    if (!nonce()) { return; }
    fetch(API, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce() }, body: JSON.stringify({ pins: next }) })
      .then(function (r) { if (r.ok) { where = 'account'; } })
      .catch(function () {})
      .then(function () { if (!draft) { renderView(); } });
  }

  mount.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('button, a[data-act]') : null;
    if (!t) { return; }
    var act = t.getAttribute('data-act');
    if (act) { e.preventDefault(); }
    if (act === 'edit') { startEdit(); return; }
    if (act === 'cancel') { draft = null; renderView(); return; }
    if (act === 'save') { save(); return; }
    if (act === 'clear') { draft = []; renderEdit(); return; }
    if (t.hasAttribute('data-scope')) {
      scope = t.getAttribute('data-scope');
      try { localStorage.setItem(LS_SCOPE, scope); } catch (err) {}
      renderView(); return;
    }
    if (t.hasAttribute('data-row')) {
      var k = t.getAttribute('data-row');
      openRows[k] = !openRows[k];
      var li = t.parentNode;
      li.className = 'mh-item' + (openRows[k] ? ' open' : '');
      t.setAttribute('aria-expanded', openRows[k] ? 'true' : 'false');
      return;
    }
    if (t.hasAttribute('data-more')) {
      var p = t.getAttribute('data-more');
      openPanels[p] = !openPanels[p];
      paintSections(); return;
    }
    if (t.hasAttribute('data-rm')) {
      var rid = t.getAttribute('data-rm');
      draft = draft.filter(function (x) { return x !== rid; }); renderEdit(); return;
    }
    if (t.hasAttribute('data-mv')) {
      var ord = visible(draft), i = +t.getAttribute('data-mv'), j = i + (+t.getAttribute('data-d'));
      if (j < 0 || j >= ord.length) { return; }
      var tmp = ord[i]; ord[i] = ord[j]; ord[j] = tmp; draft = ord; renderEdit();
    }
  });
  mount.addEventListener('change', function (e) {
    var t = e.target;
    if (t.id === 'mh-role') {
      var r = (CAT.roles || {})[t.value];
      if (r) { (r.pins || []).forEach(function (id) { if (BYID[id] && draft.indexOf(id) === -1) { draft.push(id); } }); }
      renderEdit(); return;
    }
    var id = t.getAttribute && t.getAttribute('data-id');
    if (!id) { return; }
    if (t.checked) { if (draft.indexOf(id) === -1) { draft.push(id); } }
    else { draft = draft.filter(function (x) { return x !== id; }); }
    renderEdit();
  });
  mount.addEventListener('input', function (e) {
    if (e.target.id === 'mh-q') { query = e.target.value; renderEdit(); }
  });

  /* ---------- loading ---------- */
  function fromInterests(i) {
    var out = [];
    function add(id) { if (id && BYID[id] && out.indexOf(id) === -1) { out.push(id); } }
    if (!i || !i.role) { return out; }
    add(i.speciality);
    ((CAT.roles || {})[i.role] || { pins: [] }).pins.forEach(add);
    if (i.care === 'primary') { add('primary-care-and-general-practice'); }
    else if (i.care === 'secondary') { add('pathways'); }
    return out;
  }

  function getJSON(url) {
    return fetch(url, { credentials: 'same-origin', headers: { 'X-WP-Nonce': nonce() } })
      .then(function (r) { if (!r.ok) { throw new Error(r.status); } return r.json(); });
  }

  function start() {
    css();
    mount.innerHTML = '<p class="mh-note">Loading your page…</p>';
    fetch(CAT_URL, { cache: 'no-cache' }).then(function (r) { return r.json(); }).then(function (cat) {
      CAT = cat;
      (cat.items || []).forEach(function (it) { BYID[it.id] = it; });
      if (!nonce()) {
        mount.innerHTML = '<div class="mh-panel" style="text-align:center;"><p class="mh-empty" style="margin-bottom:14px;">Log in to the Hub to build and save your page.</p><a class="mh-btn" href="/login/">Log in</a></div>';
        return;
      }
      var local = lsGet();
      getJSON(API).then(function (d) {
        if (d && d.saved) { pins = d.pins || []; where = 'account'; renderView(); return; }
        if (local && local.length) { pins = local; where = 'device'; renderView(); return; }
        return getJSON(PREFS).then(function (p) {
          pins = fromInterests(p && p.interests); seeded = pins.length > 0; renderView();
        });
      }).catch(function () {
        if (local && local.length) { pins = local; where = 'device'; renderView(); return; }
        getJSON(PREFS).then(function (p) { pins = fromInterests(p && p.interests); seeded = pins.length > 0; })
          .catch(function () {})
          .then(renderView);
      });
    }).catch(function () {
      mount.innerHTML = '<p class="mh-note warn">My Hub couldn’t load just now. Everything is still on the <a href="/medical-sales-hub/" style="color:var(--gold);">Live Desk</a>.</p>';
    });
  }

  start();
})();
