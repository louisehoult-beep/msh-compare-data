/* Medical Sales Hub — My Hub, the member's working front page.
   Lou, 24/09/2026: "this will be the page reps work from", and then of the
   first build: "I need it super professional". So the page reads like a desk
   terminal, not a list of links:

     0. Today's briefing (in the navy masthead): four counts computed from the
        live feeds, each a jump to its section. Nothing is estimated: a feed
        that fails shows "Unavailable", never a number.
     1. Key news, laid out as a front page: a lead story, two secondary
        stories with their summaries, and a column of headlines that open in
        place. "Show all" drops the rest down.
     2. On the desk: Coming up (events and awareness days, as an agenda),
        Safety alerts (MHRA, with severity), Procurement deadlines (framework
        and contract dates, as a countdown). Top items each, "Show all" for
        the rest, and every panel links to its full Hub page.
     3. The member's own pages, as tiles, in their order (unchanged from
        23/09/2026: "so they can select the things from the Hub they want to
        see").

   A sticky bar carries the section jumps, the "Your specialities / Whole Hub"
   switch and the Customise button. The switch narrows news, events and
   procurement to the specialities the member pinned. MHRA alerts are never
   narrowed: gov.uk tags them with its own specialism list, which does not map
   to Hub pages, and a filter that guesses could hide a recall.

   Mounted on <div id="msh-my-hub"></div> on /medical-sales-hub/my-hub/. The
   briefing fills <div id="myh-brief"></div> in the masthead if the page has
   one, otherwise it renders at the top of the mount. The WordPress page
   carries a loader only; edit the code HERE.

   Palette (round 2, 24/09/2026): navy and gold core, plus the Oxblood & Blush
   extended accent from 00-Resources/brand-guide.md (26/08/2026). The page is
   spaced by anchor bands: navy masthead (page shell), an oxblood band for
   "On the desk", a blush-fill band for "Your pages"; everything else light.
   Repeating cards and lists alternate gold (odd) and oxblood (even). The gold
   sheen gradient is used for accent bars and hover edges only: no text sits
   on it, because white and navy both fail contrast on part of the gradient.
   Band photos are absolute URLs from the Hub media library (a relative url()
   404s on Hub pages), always under a dark overlay.

   Theme notes, learned the hard way: the Hub theme out-specifies h1/h2/p
   colour and font, so every heading and paragraph colour below is a literal
   hex with !important. A site snippet force-opens every `.msh details`, so
   nothing here uses <details>. `.msh header`, `.msh footer` and `.msh nav`
   are styled by the page shell and the nav snippet, so none are used here.

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

  var NEWS_SEC = 2;       // secondary stories beside the lead
  var NEWS_LIST = 6;      // headlines in the column
  var NEWS_TOP = 1 + NEWS_SEC + NEWS_LIST;   // stories above "Show all"
  var PANEL_TOP = 5;      // rows per desk panel before "Show all"
  var EVENT_DAYS = 90;    // how far ahead "Coming up" looks
  var PROC_DAYS = 180;    // procurement dates are planned further out
  var NEW_DAYS = 14;      // an alert this recent carries a "New" flag
  var SOON_DAYS = 30;     // a procurement date this close is marked as soon

  var PAGES = {
    news: '/medical-sales-hub/news/',
    calendar: '/medical-sales-hub/calendar/',
    mhra: '/medical-sales-hub/mhra-regulatory-desk/',
    procurement: '/medical-sales-hub/tender-history/'
  };
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  var CAT = null, BYID = {}, pins = [], where = 'none', seeded = false;
  var draft = null, query = '', grpOpen = {};
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
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function isoDay(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
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
  function fmtShort(s) {
    var d = parseDay(s);
    return d ? d.getDate() + ' ' + MONTHS[d.getMonth()] : '';
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
  /* News timestamps carry a time and an offset; show them in the reader's
     own day: "Today, 11:00", "Yesterday", or the date. */
  function newsStamp(s) {
    var d = s ? new Date(s) : null;
    if (!d || isNaN(d)) { return { day: '', label: '' }; }
    var day = isoDay(d), hasTime = /T\d{2}:\d{2}/.test(s);
    if (day === TODAY) { return { day: day, label: 'Today' + (hasTime ? ', ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) : '') }; }
    if (day === addDays(TODAY, -1)) { return { day: day, label: 'Yesterday' }; }
    return { day: day, label: fmtShort(day) + (day.slice(0, 4) === TODAY.slice(0, 4) ? '' : ' ' + day.slice(0, 4)) };
  }
  function money(v) {
    if (typeof v !== 'number' || !isFinite(v)) { return ''; }
    if (v >= 1e6) { return '£' + (Math.round(v / 1e5) / 10) + 'm'; }
    if (v >= 1e3) { return '£' + Math.round(v / 1e3) + 'k'; }
    return '£' + Math.round(v);
  }

  /* ---------- icons: line icons, currentColor, no emoji ---------- */
  var ICON = {
    news: '<path d="M4 5.5h13v13a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 4 18.5z"/><path d="M17 9h2.5v9.5A1.5 1.5 0 0 1 18 20"/><path d="M7 9h7M7 12.5h7M7 16h4.5"/>',
    cal: '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/>',
    alert: '<path d="M12 3.2l7.5 2.8v5.6c0 4.3-3.1 7.9-7.5 9.2-4.4-1.3-7.5-4.9-7.5-9.2V6z"/><path d="M12 8.2v4.6M12 15.8v.1"/>',
    proc: '<path d="M9 3.5h6v3H9z"/><path d="M7.5 5H5.5v15.5h13V5h-2"/><path d="M8.5 11.5h7M8.5 15h4.5"/>',
    pages: '<rect x="4" y="4" width="6.5" height="6.5" rx="1.4"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.4"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.4"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.4"/>',
    tools: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.2L4 16.8V20h3.2l5.3-5.3a4 4 0 0 0 5.2-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
    live: '<path d="M3 12h4l2.5-6 5 12 2.5-6h4"/>',
    nhs: '<path d="M4 20.5V8l8-4 8 4v12.5"/><path d="M2.5 20.5h19M12 9v5M9.5 11.5h5M9.5 20.5v-3h5v3"/>',
    career: '<rect x="3.5" y="7.5" width="17" height="12" rx="2"/><path d="M9 7.5v-2A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5v2M3.5 13h17"/>',
    clinical: '<path d="M6 3.5v5a4 4 0 0 0 8 0v-5"/><path d="M10 12.5v2a5 5 0 0 0 10 0v-2"/><circle cx="20" cy="10.5" r="2"/>',
    help: '<circle cx="12" cy="12" r="8.5"/><path d="M9.6 9.5a2.5 2.5 0 0 1 4.8 1c0 1.7-2.4 2-2.4 3.5M12 17v.1"/>',
    spec: '<path d="M9.5 4h5v5.5H20v5h-5.5V20h-5v-5.5H4v-5h5.5z"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    bell: '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    chat: '<path d="M4 5.5h16v11H9l-5 4z"/><path d="M8 10h8M8 13h5"/>',
    building: '<rect x="4" y="3.5" width="10" height="17"/><path d="M14 9h6v11.5M2.5 20.5h19M7 7.5h1M10 7.5h1M7 11h1M10 11h1M7 14.5h1M10 14.5h1"/>',
    report: '<path d="M6 3.5h8.5L19 8v12.5H6z"/><path d="M14 3.5V8h5M9.5 17v-3M12.5 17v-5M15.5 17v-2"/>',
    chart: '<path d="M4 4v16h16"/><path d="M7.5 15l3.5-4 3 2.5 5-6"/>',
    compass: '<circle cx="12" cy="12" r="8.5"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
    map: '<path d="M3.5 6.5l5.5-2.5 6 2.5 5.5-2.5v13.5l-5.5 2.5-6-2.5-5.5 2.5z"/><path d="M9 4v13.5M15 6.5V20"/>',
    book: '<path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H19v13H5.5A1.5 1.5 0 0 0 4 18.5z"/><path d="M4 18.5A1.5 1.5 0 0 0 5.5 20H19v-3"/>',
    mic: '<rect x="9" y="3.5" width="6" height="10" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5v3"/>',
    play: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M10 9.5v5l4.5-2.5z"/>',
    cap: '<path d="M2.5 9.5L12 5l9.5 4.5L12 14z"/><path d="M6.5 11.5v4c1.5 1.5 3.5 2.2 5.5 2.2s4-.7 5.5-2.2v-4M21.5 9.5v5"/>',
    users: '<circle cx="9" cy="8.5" r="3.2"/><path d="M3 19.5c.6-3.2 3-5 6-5s5.4 1.8 6 5"/><path d="M15.5 5.6a3.2 3.2 0 0 1 0 6M17.5 14.8c1.8.7 3 2.3 3.5 4.7"/>',
    download: '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M4.5 19.5h15"/>',
    pound: '<path d="M16 6.5A4 4 0 0 0 9 8.8V19.5M6.5 13h7M6.5 19.5h11"/>',
    target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/>',
    radar: '<circle cx="12" cy="12" r="8.5"/><path d="M12 12l5.5-5.5M12 7.5a4.5 4.5 0 1 0 4.5 4.5"/>',
    truck: '<path d="M2.5 6.5h11v10h-11zM13.5 10h4l3 3v3.5h-7"/><circle cx="6.5" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
    star: '<path d="M12 3.8l2.5 5.2 5.6.7-4.1 3.9 1 5.6L12 16.5l-5 2.7 1-5.6-4.1-3.9 5.6-.7z"/>',
    scales: '<path d="M12 4v16M7 20.5h10M5 7.5h14M5 7.5l-2.5 6a2.5 2.5 0 0 0 5 0zM19 7.5l-2.5 6a2.5 2.5 0 0 0 5 0z"/>',
    flask: '<path d="M9.5 3.5h5M10.5 3.5v6L5 19a1 1 0 0 0 .9 1.5h12.2A1 1 0 0 0 19 19l-5.5-9.5v-6"/><path d="M7.5 15h9"/>',
    route: '<circle cx="6" cy="18" r="2.2"/><circle cx="18" cy="6" r="2.2"/><path d="M8.2 18H15a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h6.8"/>',
    leaf: '<path d="M5 19c0-8 5-13.5 15-14-.5 10-6 15-14 15"/><path d="M5 19l7-7"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l8.5-8.5M16.5 6.5l2.5 2.5M14 9l2 2"/>',
    pill: '<rect x="3" y="8.5" width="18" height="7" rx="3.5" transform="rotate(-45 12 12)"/><path d="M9.5 9.5l5 5"/>',
    globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.5 3.5 5.5 3.5 8.5s-1 6-3.5 8.5c-2.5-2.5-3.5-5.5-3.5-8.5s1-6 3.5-8.5"/>',
    doc: '<path d="M6 3.5h8.5L19 8v12.5H6z"/><path d="M14 3.5V8h5M9 12.5h6M9 16h4"/>',
    monitor: '<rect x="3.5" y="4.5" width="17" height="11.5" rx="1.5"/><path d="M9 20h6M12 16v4"/>'
  };
  function icon(k) { return '<svg class="mh-ic" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + (ICON[k] || ICON.pages) + '</svg>'; }

  /* Hub pages by kind. Each catalogue group has its own icon and accent, and
     some pages have their own icon; anything not listed falls back to its
     group's, so a page added to the catalogue needs no change here. Icons
     only: every link, label and group still comes from the catalogue. */
  var GROUP_UI = {
    specialities: { ic: 'spec', short: 'Specialities' },
    tools: { ic: 'tools', short: 'Tools' },
    live: { ic: 'live', short: 'Live desks' },
    procurement: { ic: 'proc', short: 'Procurement' },
    nhs: { ic: 'nhs', short: 'NHS know-how' },
    career: { ic: 'career', short: 'Career' },
    clinical: { ic: 'clinical', short: 'Clinical Hub' },
    account: { ic: 'help', short: 'Help' }
  };
  var LAUNCH_GROUPS = ['tools', 'live', 'procurement', 'nhs', 'career', 'clinical', 'account'];
  var QUICK = ['med-sales-tools', 'live-desk', 'calendar', 'frameworks', 'mhra-regulatory-desk', 'suppliers', 'company-report', 'ask'];
  var ITEM_IC = {
    'live-desk': 'live', news: 'news', 'sales-triggers': 'target', 'supply-disruption-tracker': 'truck', 'mhra-regulatory-desk': 'alert',
    'market-watch-subscribers-only': 'chart', 'the-radar': 'radar', 'intelligence-feed': 'monitor', calendar: 'cal', 'capital-estates-watch': 'nhs',
    'nhs-workforce-watch': 'users', frameworks: 'proc', 'tender-history': 'report', 'nhssc-guide': 'book', 'price-intelligence': 'pound', cpv: 'search',
    'procurement-act': 'scales', 'value-based-procurement': 'scales', 'voice-of-procurement': 'chat', 'private-sector': 'building', 'four-nations': 'globe',
    'nhs-online': 'monitor', 'med-sales-tools': 'tools', 'value-equation': 'scales', 'company-report': 'report', suppliers: 'building',
    'who-are-the-competitors': 'users', 'market-intelligence': 'chart', briefings: 'doc', 'hospital-prescribing-by-trust': 'pill',
    'icb-diabetes-tech-tracker': 'live', girft: 'target', pathways: 'route', 'clinical-evidence-library': 'flask', analysis: 'chart',
    'nhs-structure-map': 'map', reference: 'book', 'tr-reports': 'report', glossary: 'book', 'access-accreditation-codes': 'key',
    'sustainability-net-zero': 'leaf', 'device-sales-entry': 'compass', 'pharmaceutical-sales': 'pill', careers: 'career', 'interview-prep': 'chat',
    courses: 'cap', webinars: 'play', podcasts: 'mic', 'build-your-network': 'users', 'sales-icons': 'star', downloads: 'download',
    'clinical-to-commercial-routes': 'route', 'cpd-for-a-commercial-cv': 'doc', 'training-investment-watch': 'pound', 'funded-clinical-training': 'cap',
    clinical: 'clinical', 'clinical-training': 'cap', 'clinical-listen-watch': 'play', 'clinical-jobs': 'career', 'clinical-cv': 'doc',
    'clinical-resources': 'book', 'clinical-portfolio': 'doc', 'care-standard-portfolio': 'doc', 'phone-alerts': 'bell', ask: 'chat',
    'find-your-speciality': 'compass'
  };
  function itemIcon(it) { return ITEM_IC[it.id] || (GROUP_UI[it.group] || {}).ic || 'pages'; }
  function groupShort(gid) { return (GROUP_UI[gid] || {}).short || groupLabel(gid); }
  var ARR = '<span class="mh-arr" aria-hidden="true">→</span>';
  var EXT = '<span class="mh-arr" aria-hidden="true">↗</span>';

  function css() {
    if (document.getElementById('msh-myh4-css')) { return; }
    var SERIF = "'Source Serif 4','Source Serif Pro',Georgia,'Times New Roman',serif";
    var SANS = "'Inter',-apple-system,'Segoe UI',system-ui,sans-serif";
    var MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace";
    var st = document.createElement('style');
    st.id = 'msh-myh4-css';
    st.textContent = [
      /* tokens. --gd is the gold deepened for small text on white (5.8:1); the
         brand gold #A8842C is kept for rules and accents, where 3.5:1 is fine. */
      '#msh-my-hub,#myh-brief{--navy:#0B1C33;--navy2:#14304F;--gold:#A8842C;--goldl:#E0BE8E;--gd:#7E6118;--warm:#EDE7DC;--ink:#1D2733;--mute:#5B6573;--line:#E6E0D4;--line2:#EFEAE0;--bg:#f7f4ee;--red:#A12B2B;--tint:#E9EEF5;--ox:#6B2A34;--blush:#C9A9A6;--blf:#F3E4E1;--blb:#e3c3bd;--blt:#7A4A44;--parch:#F8F8F6;}',
      '.msh{overflow-x:clip;}',
      '#msh-my-hub{font-family:' + SANS + ';color:#1D2733;font-size:14.5px;line-height:1.5;font-feature-settings:"cv11","ss01";}',
      '.msh #msh-my-hub p,.msh #msh-my-hub li,.msh #myh-brief p{color:inherit!important;font-family:inherit!important;}',
      '.msh #msh-my-hub h2,.msh #msh-my-hub h3{font-family:' + SANS + '!important;margin:0;}',
      '.msh #msh-my-hub a{text-decoration:none;}',
      '.msh #msh-my-hub .mh-ic{width:18px;height:18px;flex:none;display:block;}',
      '.msh #msh-my-hub .mh-arr{display:inline-block;color:#7E6118;transition:transform .15s ease;margin-left:4px;}',
      '.msh #msh-my-hub a:hover .mh-arr{transform:translateX(2px);}',
      '.msh #msh-my-hub button{font-family:' + SANS + ';}',
      '.msh #msh-my-hub :focus-visible{outline:2px solid #A8842C;outline-offset:2px;border-radius:4px;}',

      /* ---- briefing strip (sits on navy) ---- */
      '#myh-brief{font-family:' + SANS + ';}',
      '#myh-brief .mh-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid rgba(224,190,142,.28);}',
      '#myh-brief .mh-kpi{display:block;padding:18px 22px 4px 0;text-decoration:none;position:relative;}',
      '#myh-brief .mh-kpi + .mh-kpi{padding-left:22px;border-left:1px solid rgba(219,227,238,.14);}',
      '#myh-brief .mh-kpi .l{display:flex;align-items:center;gap:10px;font-size:10.5px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#E0BE8E!important;}',
      '#myh-brief .mh-kpi .l .ib{flex:none;width:30px;height:30px;border-radius:9px;display:flex;align-items:center;justify-content:center;background:rgba(224,190,142,.12);border:1px solid rgba(224,190,142,.35);color:#E0BE8E;}',
      '#myh-brief .mh-kpi .l .ib.rd{background:rgba(201,169,166,.14);border-color:rgba(201,169,166,.45);color:#F3E4E1;}',
      '#myh-brief .mh-kpi .l .mh-ic{width:16px;height:16px;display:block;}',
      '#myh-brief .mh-kpi:hover .l .ib{background:#E0BE8E;color:#0B1C33;border-color:#E0BE8E;}',
      '#myh-brief .mh-kpi .v{display:flex;align-items:baseline;gap:10px;margin-top:8px;font-size:40px;line-height:1;font-weight:600;letter-spacing:-1px;color:#FFFFFF!important;font-variant-numeric:tabular-nums;}',
      '#myh-brief .mh-kpi .v.na{font-size:15px;letter-spacing:0;font-weight:600;color:#DBE3EE!important;padding:12px 0 11px;}',
      '#myh-brief .mh-kpi .d{display:block;margin-top:8px;font-size:12px;color:#DBE3EE!important;line-height:1.45;}',
      '#myh-brief .mh-kpi .go{font-size:12px;font-weight:600;letter-spacing:0;color:#E0BE8E!important;opacity:0;transition:opacity .15s;}',
      '#myh-brief .mh-kpi:hover .go,#myh-brief .mh-kpi:focus-visible .go{opacity:1;}',
      '#myh-brief .mh-kpi:hover .v{color:#F5F1E8!important;}',
      '#myh-brief .mh-kpi .sk{display:block;height:40px;width:64px;border-radius:6px;margin-top:8px;background:linear-gradient(90deg,rgba(219,227,238,.08),rgba(219,227,238,.18),rgba(219,227,238,.08));background-size:200% 100%;animation:mhsh 1.4s linear infinite;}',
      '#myh-brief .mh-kpi-note{font-size:11.5px;color:#DBE3EE!important;padding:10px 0 0;opacity:.85;}',
      '.msh #myh-brief.mh-brief-inline{background:linear-gradient(120deg,#0B1C33,#14304F);border-radius:14px;padding:6px 24px 16px;margin-bottom:22px;}',
      '@media(max-width:900px){#myh-brief .mh-kpis{grid-template-columns:repeat(2,minmax(0,1fr));}#myh-brief .mh-kpi:nth-child(3){padding-left:0;border-left:0;}#myh-brief .mh-kpi:nth-child(n+3){border-top:1px solid rgba(219,227,238,.14);}#myh-brief .mh-kpi{padding-bottom:14px;}}',
      '@media(max-width:480px){#myh-brief .mh-kpi{padding:14px 12px 12px 0;}#myh-brief .mh-kpi + .mh-kpi{padding-left:14px;}#myh-brief .mh-kpi:nth-child(3){padding-left:0;}#myh-brief .mh-kpi .v{font-size:32px;}#myh-brief .mh-kpi .d{font-size:11.5px;}}',

      /* ---- sticky section bar ---- */
      '#msh-my-hub .mh-bar{position:sticky;top:var(--wp-admin--admin-bar--height,0px);z-index:30;margin:-30px 0 34px;background:rgba(255,255,255,.94);-webkit-backdrop-filter:saturate(1.4) blur(10px);backdrop-filter:saturate(1.4) blur(10px);border:1px solid #E6E0D4;border-radius:12px;box-shadow:0 1px 2px rgba(11,28,51,.04),0 8px 24px -12px rgba(11,28,51,.18);}',
      '#msh-my-hub .mh-bar-in{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:8px 8px 8px 10px;}',
      '#msh-my-hub .mh-jumps{display:flex;gap:2px;min-width:0;}',
      '#msh-my-hub .mh-jumps a{display:inline-flex;align-items:center;gap:7px;padding:8px 12px;border-radius:8px;font-size:13px;font-weight:600;color:#5B6573;white-space:nowrap;transition:background .15s,color .15s;}',
      '#msh-my-hub .mh-jumps a:hover{background:#F4F0E8;color:#0B1C33;}',
      '#msh-my-hub .mh-jumps a.on{color:#0B1C33;background:linear-gradient(115deg,#8C6A1C 0%,#C9A227 45%,#8C6A1C 100%) left bottom / 100% 2px no-repeat,#EDE7DC;}',
      '#msh-my-hub .mh-jumps a .c{font-size:11px;font-weight:600;color:#5B6573;font-variant-numeric:tabular-nums;}',
      '#msh-my-hub .mh-jumps a.on .c{color:#1D2733;}',
      '#msh-my-hub .mh-bar-r{display:flex;align-items:center;gap:10px;flex:none;}',
      '#msh-my-hub .mh-scope{display:inline-flex;background:#F4F0E8;border:1px solid #E6E0D4;border-radius:9px;padding:3px;}',
      '#msh-my-hub .mh-scope button{border:0;background:none;border-radius:7px;padding:7px 13px;font-size:12.5px;font-weight:600;color:#1D2733;cursor:pointer;white-space:nowrap;transition:background .15s,color .15s;}',
      '#msh-my-hub .mh-scope button[aria-pressed="true"]{background:#0B1C33;color:#FFFFFF;box-shadow:0 1px 2px rgba(11,28,51,.3);}',
      '#msh-my-hub .mh-scope button:disabled{color:#8b949e;cursor:not-allowed;}',
      '@media(max-width:1180px){#msh-my-hub .mh-jumps a .c{display:none;}}',
      '@media(max-width:1000px){#msh-my-hub .mh-jumps{display:none;}#msh-my-hub .mh-bar-in{padding:8px;}#msh-my-hub .mh-bar-r{flex:1;justify-content:space-between;}}',
      '@media(max-width:480px){#msh-my-hub .mh-bar-r{gap:6px;min-width:0;}#msh-my-hub .mh-scope button{padding:7px 9px;font-size:12px;}#msh-my-hub .mh-bar .mh-btn{padding:9px 11px;font-size:12.5px;}#msh-my-hub .mh-bar .mh-btn .mh-ic{display:none;}#msh-my-hub .mh-bar-in{padding:6px;}}',
      '@media(max-width:340px){#msh-my-hub .mh-scope button{padding:7px 6px;}}',

      /* ---- buttons ---- */
      '#msh-my-hub .mh-btn{display:inline-flex;align-items:center;gap:8px;background:#0B1C33;color:#FFFFFF!important;border:1px solid #0B1C33;border-radius:9px;padding:9px 16px;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;transition:background .15s,box-shadow .15s;}',
      '#msh-my-hub .mh-btn:hover{background:linear-gradient(#14304F,#14304F) padding-box,linear-gradient(115deg,#8C6A1C 0%,#C9A227 45%,#8C6A1C 100%) border-box;border-color:transparent;box-shadow:0 4px 14px -4px rgba(11,28,51,.45);}',
      '#msh-my-hub .mh-btn.ghost{background:#FFFFFF;color:#1D2733!important;border-color:#D9D1C2;}',
      '#msh-my-hub .mh-btn.ghost:hover{border-color:#A8842C;box-shadow:none;}',
      '#msh-my-hub .mh-btn .mh-ic{width:15px;height:15px;}',
      '#msh-my-hub .mh-link{background:none;border:0;color:#7E6118;font-size:12.5px;font-weight:600;cursor:pointer;padding:0;}',
      '#msh-my-hub .mh-link:hover{color:#0B1C33;text-decoration:underline;}',

      /* ---- section headers ---- */
      '#msh-my-hub .mh-sec{margin-bottom:44px;scroll-margin-top:84px;}',
      '#msh-my-hub .mh-sh{display:flex;align-items:center;gap:14px;margin-bottom:16px;}',
      '#msh-my-hub .mh-sh .no{font-family:' + MONO + ';font-size:11.5px;font-weight:600;color:#7E6118;letter-spacing:.5px;}',
      '.msh #msh-my-hub .mh-sh h2.mh-h2{font-family:' + SERIF + '!important;font-size:26px;font-weight:600;letter-spacing:-.3px;line-height:1.1;color:#0B1C33!important;}',
      '#msh-my-hub .mh-sh .rule{flex:1;height:2px;min-width:20px;background:linear-gradient(115deg,#8C6A1C 0%,#C9A227 45%,#8C6A1C 100%) left center / 56px 2px no-repeat,linear-gradient(#D9D1C2,#D9D1C2) left center / 100% 1px no-repeat;}',
      '#msh-my-hub .mh-sh .aux{font-size:12.5px;color:#5B6573;white-space:nowrap;}',
      '#msh-my-hub .mh-sh a.more{font-size:13px;font-weight:600;color:#14304F;white-space:nowrap;}',
      '#msh-my-hub .mh-sh a.more:hover{color:#0B1C33;text-decoration:underline;text-decoration-color:#A8842C;text-underline-offset:3px;}',
      '@media(max-width:640px){#msh-my-hub .mh-sh{flex-wrap:wrap;gap:6px 12px;}#msh-my-hub .mh-sh .rule{display:none;}#msh-my-hub .mh-sh a.more{margin-left:auto;}.msh #msh-my-hub .mh-sh h2.mh-h2{font-size:22px;}#msh-my-hub .mh-sh .aux{display:none;}}',

      /* ---- cards ---- */
      '#msh-my-hub .mh-card{background:#F8F8F6;border:1px solid #D6CDBD;border-radius:14px;box-shadow:0 1px 2px rgba(11,28,51,.06),0 14px 34px -22px rgba(11,28,51,.45);}',

      /* ---- callout (no specialities pinned) ---- */
      '#msh-my-hub .mh-callout{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;background:#F3E4E1;border:1px solid #e3c3bd;border-left:3px solid #6B2A34;border-radius:12px;padding:16px 20px;margin:-12px 0 34px;}',
      '#msh-my-hub .mh-callout b{display:block;font-size:14.5px;color:#0B1C33;}',
      '#msh-my-hub .mh-callout span{display:block;font-size:13px;color:#7A4A44;margin-top:2px;max-width:760px;}',

      /* ---- key news: front page ---- */
      '#msh-my-hub .mh-front{padding:26px;}',
      '#msh-my-hub .mh-fp{display:grid;gap:0 30px;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1.05fr);grid-template-areas:"lead lead list" "s1 s2 list";grid-template-rows:min-content 1fr;}',
      '#msh-my-hub .mh-fp .a-lead{grid-area:lead;}#msh-my-hub .mh-fp .a-s1{grid-area:s1;}#msh-my-hub .mh-fp .a-s2{grid-area:s2;}#msh-my-hub .mh-fp .a-list{grid-area:list;}',
      '#msh-my-hub .mh-fp .a-s1,#msh-my-hub .mh-fp .a-s2{margin-top:26px;}',
      '#msh-my-hub .mh-fp .a-s2{border-left:1px solid #E6E0D4;padding-left:28px;}',
      '#msh-my-hub .mh-fp .a-list{border-left:1px solid #E6E0D4;padding-left:28px;}',
      '@media(min-width:1800px){#msh-my-hub .mh-fp{grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,.9fr) minmax(0,.9fr);grid-template-areas:"lead lead s1 s2" "list list list list";}#msh-my-hub .mh-fp .a-s1,#msh-my-hub .mh-fp .a-s2{margin-top:0;}#msh-my-hub .mh-fp .a-s1{border-left:0;padding-left:0;}#msh-my-hub .mh-fp .a-list{border-left:0;padding-left:0;margin-top:30px;}#msh-my-hub .mh-fp .a-list .mh-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));column-gap:30px;}#msh-my-hub .mh-fp .a-list .mh-item:nth-last-child(-n+3){border-bottom:0;}}',
      '@media(max-width:1180px){#msh-my-hub .mh-fp{grid-template-columns:minmax(0,1fr) minmax(0,1fr);grid-template-areas:"lead lead" "s1 s2" "list list";gap:0 28px;}#msh-my-hub .mh-fp .a-list{border-left:0;padding-left:0;margin-top:26px;border-top:1px solid #E6E0D4;padding-top:20px;}}',
      '@media(max-width:700px){#msh-my-hub .mh-front{padding:14px;}#msh-my-hub .mh-lead{padding:24px 20px 20px;}#msh-my-hub .mh-lead:before{left:20px;}#msh-my-hub .mh-fp{grid-template-columns:minmax(0,1fr);grid-template-areas:"lead" "s1" "s2" "list";}#msh-my-hub .mh-fp .a-s2{border-left:0;padding-left:0;border-top:1px solid #E6E0D4;padding-top:20px;margin-top:20px;}}',
      /* lead */
      '#msh-my-hub .mh-lead{position:relative;overflow:hidden;background:#0B1C33;background-image:radial-gradient(120% 90% at 100% 0%,rgba(224,190,142,.14) 0%,rgba(224,190,142,0) 55%),linear-gradient(160deg,#0B1C33 0%,#14304F 100%);border-radius:12px;padding:30px 32px 26px;display:flex;flex-direction:column;gap:14px;height:100%;}',
      '#msh-my-hub .mh-lead:before{content:"";position:absolute;left:32px;top:0;width:56px;height:3px;background:linear-gradient(115deg,#8C6A1C 0%,#C9A227 45%,#8C6A1C 100%);}',
      '#msh-my-hub .mh-lead:after{content:"";position:absolute;inset:0;pointer-events:none;background-image:repeating-linear-gradient(135deg,rgba(224,190,142,.035) 0 1px,transparent 1px 14px);}',
      '#msh-my-hub .mh-lead > *{position:relative;z-index:1;}',
      '#msh-my-hub .mh-lead .k{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:11px;letter-spacing:1.5px;font-weight:700;text-transform:uppercase;color:#E0BE8E!important;}',
      '#msh-my-hub .mh-lead .k .dot{width:3px;height:3px;border-radius:50%;background:#E0BE8E;}',
      '.msh #msh-my-hub .mh-lead h3.t{font-family:' + SERIF + '!important;font-size:clamp(24px,1.9vw,34px);line-height:1.18;font-weight:600;letter-spacing:-.4px;color:#FFFFFF!important;}',
      '.msh #msh-my-hub .mh-lead h3.t a{color:#FFFFFF!important;background-image:linear-gradient(#E0BE8E,#E0BE8E);background-size:0 1px;background-repeat:no-repeat;background-position:0 100%;transition:background-size .25s ease;}',
      '.msh #msh-my-hub .mh-lead h3.t a:hover{background-size:100% 1px;}',
      '.msh #msh-my-hub .mh-lead p.s{font-size:15.5px;line-height:1.65;color:#DBE3EE!important;max-width:72ch;}',
      '#msh-my-hub .mh-lead .m{font-size:12.5px;color:#DBE3EE!important;}',
      '#msh-my-hub .mh-lead .acts{display:flex;gap:10px;flex-wrap:wrap;margin-top:auto;padding-top:10px;}',
      '.msh #msh-my-hub .mh-lead .acts a{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;padding:9px 14px;border-radius:8px;color:#0B1C33!important;background:#E0BE8E;transition:background .15s;}',
      '.msh #msh-my-hub .mh-lead .acts a:hover{background:#F5F1E8;}',
      '.msh #msh-my-hub .mh-lead .acts a .mh-arr{color:#0B1C33;}',
      '.msh #msh-my-hub .mh-lead .acts a.sec{background:transparent;color:#FFFFFF!important;border:1px solid rgba(224,190,142,.5);}',
      '.msh #msh-my-hub .mh-lead .acts a.sec:hover{border-color:#E0BE8E;background:rgba(224,190,142,.08);}',
      '.msh #msh-my-hub .mh-lead .acts a.sec .mh-arr{color:#E0BE8E;}',
      /* column heads inside the front page */
      '#msh-my-hub .mh-colh{display:flex;align-items:center;justify-content:space-between;font-size:10.5px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#5B6573;padding-bottom:10px;margin-bottom:4px;border-bottom:2px solid #0B1C33;}',
      '@media(max-width:700px){#msh-my-hub .mh-colh.mh-colh2{display:none;}}',
      '#msh-my-hub .a-list .mh-item:nth-child(even) .kk,#msh-my-hub .mh-rest .mh-item:nth-child(even) .kk,#msh-my-hub .a-s2 .mh-s .kk{color:#6B2A34;}',
      '#msh-my-hub .a-list .mh-item:nth-child(even) .kk .tm,#msh-my-hub .mh-rest .mh-item:nth-child(even) .kk .tm{color:#5B6573;}',
      /* secondary stories */
      '#msh-my-hub .mh-s .kk{display:block;font-size:10.5px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;color:#7E6118;margin:12px 0 8px;}',
      '.msh #msh-my-hub .mh-s h3.t{font-family:' + SERIF + '!important;font-size:20px;line-height:1.28;font-weight:600;letter-spacing:-.2px;color:#0B1C33!important;}',
      '.msh #msh-my-hub .mh-s h3.t a{color:#0B1C33!important;}',
      '.msh #msh-my-hub .mh-s h3.t a:hover{text-decoration:underline;text-decoration-color:#A8842C;text-underline-offset:4px;text-decoration-thickness:1px;}',
      '.msh #msh-my-hub .mh-s p.s{font-size:14px;line-height:1.62;color:#3A4552!important;margin-top:10px;display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden;}',
      '#msh-my-hub .mh-s .m{display:block;font-size:12px;color:#5B6573;margin-top:10px;}',
      '#msh-my-hub .mh-s .lk{margin-top:10px;}',
      /* badges */
      '#msh-my-hub .mh-opp{display:inline-block;padding:2px 7px;border-radius:4px;background:#E0BE8E;color:#0B1C33!important;font-size:9.5px;font-weight:800;letter-spacing:1px;text-transform:uppercase;line-height:1.5;vertical-align:1px;}',
      '#msh-my-hub .mh-new{display:inline-flex;align-items:center;gap:5px;padding:2px 7px;border-radius:4px;background:#A12B2B;color:#FFFFFF!important;font-size:9.5px;font-weight:800;letter-spacing:1px;text-transform:uppercase;line-height:1.5;}',
      '#msh-my-hub .mh-tag{display:inline-block;font-size:9.5px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:2px 7px;border-radius:4px;line-height:1.5;}',
      '#msh-my-hub .mh-tag.ev,#msh-my-hub .mh-tag.ds,#msh-my-hub .mh-tag.ct{background:#E9EEF5;color:#14304F;}',
      '#msh-my-hub .mh-tag.aw,#msh-my-hub .mh-tag.fw{background:#F3ECDC;color:#6B5418;}',
      '#msh-my-hub .mh-tag.np{background:#A12B2B;color:#FFFFFF;}',
      '#msh-my-hub .mh-tag.on{background:#0B1C33;color:#E0BE8E;}',
      '#msh-my-hub .mh-ref{font-family:' + MONO + ';font-size:11px;color:#5B6573;letter-spacing:.2px;}',

      /* ---- rows (headlines, events, alerts, procurement) ---- */
      '#msh-my-hub .mh-list{list-style:none;margin:0;padding:0;}',
      '#msh-my-hub .mh-item{border-bottom:1px solid #EFEAE0;}',
      '#msh-my-hub .mh-item:last-child{border-bottom:0;}',
      '#msh-my-hub .mh-row{display:flex;gap:14px;align-items:flex-start;width:100%;background:none;border:0;text-align:left;padding:13px 4px;cursor:pointer;font:inherit;color:#1D2733;border-radius:8px;transition:background .12s;}',
      '#msh-my-hub .mh-row:hover{background:#FAF7F1;}',
      '#msh-my-hub .mh-row .bd{flex:1;min-width:0;}',
      '#msh-my-hub .mh-row .kk{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:5px;font-size:10.5px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#7E6118;}',
      '#msh-my-hub .mh-row .kk .tm{color:#5B6573;letter-spacing:.3px;text-transform:none;font-weight:600;font-size:11.5px;margin-left:auto;}',
      '#msh-my-hub .mh-row .tt{display:block;font-weight:600;font-size:14.5px;line-height:1.42;color:#1D2733;}',
      '#msh-my-hub .mh-row .tt.serif{font-family:' + SERIF + ';font-size:16.5px;font-weight:600;line-height:1.35;color:#0B1C33;}',
      '#msh-my-hub .mh-row:hover .tt{color:#14304F;text-decoration:underline;text-decoration-color:#A8842C;text-underline-offset:3px;text-decoration-thickness:1px;}',
      '#msh-my-hub .mh-row .mm{display:block;font-size:12px;color:#5B6573;margin-top:4px;}',
      '#msh-my-hub .mh-row .ch{flex:none;width:22px;height:22px;border-radius:6px;border:1px solid #E6E0D4;position:relative;margin-top:1px;transition:transform .2s,border-color .15s,background .15s;}',
      '#msh-my-hub .mh-row .ch:after{content:"";position:absolute;left:7px;top:5px;width:5px;height:5px;border-right:1.6px solid #5B6573;border-bottom:1.6px solid #5B6573;transform:rotate(45deg);}',
      '#msh-my-hub .mh-row:hover .ch{border-color:#A8842C;}',
      '#msh-my-hub .mh-item.open .mh-row .ch{transform:rotate(180deg);background:#0B1C33;border-color:#0B1C33;}',
      '#msh-my-hub .mh-item.open .mh-row .ch:after{border-color:#E0BE8E;}',
      '#msh-my-hub .mh-det{display:none;padding:0 4px 16px 4px;font-size:13.5px;line-height:1.62;color:#1D2733;}',
      '#msh-my-hub .mh-item.open .mh-det{display:block;animation:mhin .18s ease;}',
      '#msh-my-hub .mh-det p{margin:0 0 9px;}',
      '#msh-my-hub .mh-det .why{background:#F7F4EE;border-left:2px solid #A8842C;padding:9px 13px;border-radius:0 8px 8px 0;}',
      '#msh-my-hub .mh-det .why b{display:block;font-size:10px;letter-spacing:1.3px;text-transform:uppercase;color:#7E6118;margin-bottom:2px;}',
      '#msh-my-hub .lk{display:flex;gap:6px 18px;flex-wrap:wrap;}',
      '#msh-my-hub .lk a{font-weight:600;font-size:12.5px;color:#14304F;}',
      '#msh-my-hub .lk a:hover{color:#0B1C33;text-decoration:underline;text-decoration-color:#A8842C;text-underline-offset:3px;}',
      '#msh-my-hub .mh-withchip .mh-det{padding-left:76px;}',
      '@media(max-width:640px){#msh-my-hub .mh-withchip .mh-det{padding-left:4px;}}',
      /* "show all" */
      '#msh-my-hub .mh-more{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;margin-top:10px;background:#FFFFFF;border:1px solid #E6E0D4;border-radius:9px;padding:10px 12px;font-size:12.5px;font-weight:600;color:#1D2733;cursor:pointer;transition:border-color .15s,background .15s;}',
      '#msh-my-hub .mh-more:hover{border-color:#A8842C;background:#FAF7F1;}',
      '#msh-my-hub .mh-more .n{font-variant-numeric:tabular-nums;color:#5B6573;font-weight:600;}',
      '#msh-my-hub .mh-more .cv{width:6px;height:6px;border-right:1.6px solid #A8842C;border-bottom:1.6px solid #A8842C;transform:rotate(45deg);margin-top:-3px;transition:transform .2s;}',
      '#msh-my-hub .mh-more[aria-expanded="true"] .cv{transform:rotate(-135deg);margin-top:3px;}',
      '#msh-my-hub .mh-rest{margin-top:22px;padding-top:6px;border-top:1px solid #E6E0D4;}',
      '#msh-my-hub .mh-rest .mh-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));column-gap:30px;}',
      '#msh-my-hub .mh-rest .mh-item:last-child{border-bottom:1px solid #EFEAE0;}',
      '@media(max-width:640px){#msh-my-hub .mh-rest .mh-list{grid-template-columns:minmax(0,1fr);}}',

      /* ---- the desk: three panels ---- */
      '#msh-my-hub .mh-desk{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px;align-items:start;}',
      '@media(max-width:1280px){#msh-my-hub .mh-desk{grid-template-columns:repeat(2,minmax(0,1fr));}#msh-my-hub .mh-desk > #mh-proc{grid-column:1 / -1;}}',
      '@media(max-width:820px){#msh-my-hub .mh-desk{grid-template-columns:minmax(0,1fr);}}',
      '#msh-my-hub .mh-panel{position:relative;padding:22px 22px 18px;scroll-margin-top:84px;overflow:hidden;}',
      '#msh-my-hub .mh-desk > .mh-panel:before{content:"";position:absolute;left:0;right:0;top:0;height:3px;background:linear-gradient(115deg,#8C6A1C 0%,#C9A227 45%,#8C6A1C 100%);}',
      '#msh-my-hub .mh-desk > .mh-panel:nth-child(even):before{background:#6B2A34;}',
      '#msh-my-hub .mh-ph .ib.ox{background:#6B2A34;color:#F3E4E1;}',
      '#msh-my-hub .mh-ph{display:flex;flex-wrap:wrap;align-items:flex-start;gap:6px 12px;padding-bottom:14px;margin-bottom:4px;border-bottom:1px solid #E6E0D4;}',
      '#msh-my-hub .mh-ph .ib{flex:none;width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#0B1C33;color:#E0BE8E;}',
      '#msh-my-hub .mh-ph .ib.red{background:#A12B2B;color:#FFFFFF;}',
      '#msh-my-hub .mh-ph .tx{flex:1 1 210px;min-width:0;}',
      '.msh #msh-my-hub .mh-ph h2.mh-h3{display:flex;align-items:center;gap:8px;font-size:16px;font-weight:700;letter-spacing:-.1px;color:#0B1C33!important;line-height:1.25;}',
      '#msh-my-hub .mh-ph h2 .n{font-size:11.5px;font-weight:600;color:#5B6573;background:#F4F0E8;border:1px solid #E6E0D4;border-radius:999px;padding:1px 8px;font-variant-numeric:tabular-nums;}',
      '#msh-my-hub .mh-ph .sub{display:block;font-size:12.5px;color:#5B6573;margin-top:3px;line-height:1.45;}',
      '#msh-my-hub .mh-ph a.full{flex:none;font-size:12.5px;font-weight:600;color:#14304F;white-space:nowrap;margin-top:2px;}',
      '#msh-my-hub .mh-ph a.full:hover{text-decoration:underline;text-decoration-color:#A8842C;text-underline-offset:3px;}',
      '@media(max-width:480px){#msh-my-hub .mh-panel{padding:16px 14px 14px;}}',
      '#msh-my-hub .mh-empty{color:#5B6573;line-height:1.65;font-size:13.5px;padding:18px 4px 6px;}',
      '#msh-my-hub .mh-empty button{background:none;border:0;color:#14304F;font-size:13.5px;font-weight:700;cursor:pointer;padding:0;text-decoration:underline;text-decoration-color:#A8842C;text-underline-offset:3px;}',
      /* agenda (events) */
      '#msh-my-hub .mh-grp{list-style:none;font-size:10.5px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:#7E6118;padding:14px 4px 2px;}',
      '#msh-my-hub .mh-grp:first-child{padding-top:10px;}',
      '#msh-my-hub .mh-chip{flex:none;width:58px;text-align:center;line-height:1.1;padding:6px 0 5px;border-radius:9px;background:#F7F4EE;border:1px solid #E6E0D4;}',
      '#msh-my-hub .mh-chip i{display:block;font-style:normal;font-size:9.5px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#5B6573;}',
      '#msh-my-hub .mh-chip b{display:block;font-size:21px;font-weight:600;color:#0B1C33;letter-spacing:-.5px;margin:1px 0;font-variant-numeric:tabular-nums;}',
      '#msh-my-hub .mh-chip.now{background:#0B1C33;border-color:#0B1C33;}',
      '#msh-my-hub .mh-chip.now i{color:#E0BE8E;}#msh-my-hub .mh-chip.now b{color:#FFFFFF;}',
      /* countdown (procurement) */
      '#msh-my-hub .mh-cd{flex:none;width:58px;text-align:center;padding:6px 0 5px;border-radius:9px;border:1px solid #E6E0D4;background:#FFFFFF;line-height:1.1;}',
      '#msh-my-hub .mh-cd b{display:block;font-size:21px;font-weight:600;color:#0B1C33;letter-spacing:-.5px;font-variant-numeric:tabular-nums;}',
      '#msh-my-hub .mh-cd i{display:block;font-style:normal;font-size:9.5px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#5B6573;margin-top:1px;}',
      '#msh-my-hub .mh-cd.soon{background:#0B1C33;border-color:#0B1C33;}',
      '#msh-my-hub .mh-cd.soon b{color:#FFFFFF;}#msh-my-hub .mh-cd.soon i{color:#E0BE8E;}',
      '#msh-my-hub .mh-val{font-variant-numeric:tabular-nums;font-weight:700;color:#0B1C33;}',
      /* severity (alerts) */
      '#msh-my-hub .mh-sev{flex:none;width:3px;align-self:stretch;border-radius:3px;background:#14304F;margin:2px 0;}',
      '#msh-my-hub .mh-sev.np{background:#A12B2B;}',
      '#msh-my-hub .mh-sev.old{background:#D9D1C2;}',
      '#msh-my-hub .mh-alerts .mh-det{padding-left:21px;}',

      /* ---- your pages ---- */
      '#msh-my-hub .mh-tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;}',
      '.msh #msh-my-hub a.mh-tile{position:relative;display:flex;flex-direction:column;justify-content:space-between;min-height:118px;background:#FFFFFF;border:1px solid #D6CDBD;border-radius:12px;padding:16px 18px;color:#1D2733;box-shadow:0 1px 2px rgba(11,28,51,.05);transition:border-color .15s,box-shadow .2s,transform .2s;}',
      '.msh #msh-my-hub a.mh-tile:hover{border-color:#0B1C33;box-shadow:0 12px 28px -14px rgba(11,28,51,.35);transform:translateY(-2px);}',
      '#msh-my-hub .mh-tile .tp{display:flex;align-items:center;justify-content:space-between;gap:8px;}',
      '#msh-my-hub .mh-tile .no{font-family:' + MONO + ';font-size:11px;color:#7E6118;font-weight:600;}',
      '#msh-my-hub .mh-tile .gp{font-size:10px;letter-spacing:1.2px;text-transform:uppercase;color:#5B6573;font-weight:700;}',
      '#msh-my-hub .mh-tile b{display:block;font-size:15.5px;line-height:1.3;color:#0B1C33;font-weight:600;margin-top:18px;padding-right:22px;}',
      '#msh-my-hub .mh-tile .go{position:absolute;right:16px;bottom:15px;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#7E6118;transition:background .15s,color .15s;}',
      '#msh-my-hub .mh-tile:hover .go{background:#0B1C33;color:#E0BE8E;}',
      '.msh #msh-my-hub a.mh-tile:before{content:"";position:absolute;left:18px;top:-1px;width:32px;height:3px;border-radius:0 0 2px 2px;background:linear-gradient(115deg,#8C6A1C 0%,#C9A227 45%,#8C6A1C 100%);}',
      '.msh #msh-my-hub a.mh-tile:nth-child(even):before{background:#6B2A34;}',
      '#msh-my-hub .mh-tile:nth-child(even) .no{color:#6B2A34;}',
      '.msh #msh-my-hub a.mh-tile:nth-child(even):hover{border-color:#6B2A34;}',
      '#msh-my-hub .mh-tile:nth-child(even):hover .go{background:#6B2A34;color:#F3E4E1;}',
      '#msh-my-hub .mh-note{font-size:12.5px;color:#5B6573;line-height:1.6;margin-top:14px;display:flex;align-items:center;gap:8px;}',
      '#msh-my-hub .mh-note:before{content:"";width:6px;height:6px;border-radius:50%;background:#A8842C;flex:none;}',
      '#msh-my-hub .mh-note.warn{color:#7a2424;}#msh-my-hub .mh-note.warn:before{background:#A12B2B;}',
      '#msh-my-hub .mh-note.plain:before{display:none;}',
      '#msh-my-hub .mh-blank{border:1px dashed #CFC6B5;border-radius:14px;padding:34px 28px;text-align:center;background:#FFFFFF;}',
      '#msh-my-hub .mh-blank .ib{width:44px;height:44px;margin:0 auto 14px;border-radius:12px;background:#0B1C33;color:#E0BE8E;display:flex;align-items:center;justify-content:center;}',
      '.msh #msh-my-hub .mh-blank h3{font-family:' + SERIF + '!important;font-size:21px;font-weight:600;color:#0B1C33!important;}',
      '#msh-my-hub .mh-blank span.t{display:block;max-width:560px;margin:8px auto 18px;font-size:14px;color:#5B6573;line-height:1.6;}',

      /* ---- anchor bands: full-bleed from inside the mount ---- */
      '#msh-my-hub .mh-band{margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw);padding:46px calc(50vw - 50%) 50px;margin-bottom:48px;scroll-margin-top:60px;}',
      '#msh-my-hub .mh-band.ox{background-color:#6B2A34;background-image:linear-gradient(180deg,rgba(107,42,52,.98) 0,rgba(107,42,52,.97) 120px,rgba(96,36,46,.9) 440px,rgba(79,30,38,.94) 100%),url(https://medsalesintelligencehub.co.uk/wp-content/uploads/2026/09/tender-history-masthead.jpg);background-size:cover;background-position:center 40%;border-top:1px solid #4F1E26;border-bottom:0;margin-bottom:0;}',
      '#msh-my-hub .mh-band.ox + .mh-band.bl{border-top:0;box-shadow:inset 0 1px 0 #e3c3bd;}',
      '#msh-my-hub .mh-band.ox .mh-sh .no{color:#F3E4E1;}',
      '.msh #msh-my-hub .mh-band.ox .mh-sh h2.mh-h2{color:#FFFFFF!important;}',
      '#msh-my-hub .mh-band.ox .mh-sh .aux{color:#F5F1E8;}',
      '#msh-my-hub .mh-band.ox .mh-sh .rule{background:linear-gradient(115deg,#8C6A1C 0%,#C9A227 45%,#8C6A1C 100%) left center / 56px 2px no-repeat,linear-gradient(rgba(201,169,166,.45),rgba(201,169,166,.45)) left center / 100% 1px no-repeat;}',
      '#msh-my-hub .mh-band.ox .mh-card{border-color:#4F1E26;box-shadow:0 18px 40px -24px rgba(20,4,8,.8);}',
      '#msh-my-hub .mh-band.bl{background:#F3E4E1;border-top:1px solid #e3c3bd;border-bottom:1px solid #e3c3bd;margin-bottom:0;}',
      '#msh-my-hub .mh-band.bl .mh-sh .no{color:#6B2A34;}',
      '#msh-my-hub .mh-band.bl .mh-sh .aux{color:#7A4A44;}',
      '#msh-my-hub .mh-band.bl .mh-sh .rule{background:linear-gradient(115deg,#8C6A1C 0%,#C9A227 45%,#8C6A1C 100%) left center / 56px 2px no-repeat,linear-gradient(#e3c3bd,#e3c3bd) left center / 100% 1px no-repeat;}',
      '#msh-my-hub .mh-band.bl .mh-note{color:#7A4A44;}',
      '#msh-my-hub .mh-band.bl .mh-note.warn{color:#7a2424;}',
      '#msh-my-hub .mh-band.bl .mh-blank{border-color:#e3c3bd;background:#FFFFFF;}',
      '@media(max-width:640px){#msh-my-hub .mh-band{padding-top:32px;padding-bottom:34px;margin-bottom:36px;}}',
      '#msh-my-hub .mh-edit{padding-bottom:44px;}',

      /* ---- skeletons ---- */
      '#msh-my-hub .sk{display:block;border-radius:6px;background:linear-gradient(90deg,#F1ECE3 0%,#F8F5EF 50%,#F1ECE3 100%);background-size:200% 100%;animation:mhsh 1.4s linear infinite;}',
      '#msh-my-hub .sk.dk{background:linear-gradient(90deg,rgba(219,227,238,.08),rgba(219,227,238,.18),rgba(219,227,238,.08));background-size:200% 100%;}',
      '#msh-my-hub .sk-row{display:flex;gap:14px;padding:14px 4px;border-bottom:1px solid #EFEAE0;}',
      '#msh-my-hub .sk-row:last-child{border-bottom:0;}',
      '@keyframes mhsh{0%{background-position:100% 0}100%{background-position:-100% 0}}',
      '@keyframes mhin{from{opacity:0;transform:translateY(-3px)}to{opacity:1;transform:none}}',
      '@media (prefers-reduced-motion:reduce){#msh-my-hub *,#myh-brief *{animation:none!important;transition:none!important;}}',

      /* ---- editor ---- */
      '#msh-my-hub .mh-edhead{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;flex-wrap:wrap;padding:22px 0 20px;margin-bottom:22px;border-bottom:1px solid #D9D1C2;}',
      '#msh-my-hub .mh-eyebrow{display:block;font-family:' + MONO + ';font-size:11.5px;font-weight:600;color:#7E6118;margin-bottom:6px;}',
      '.msh #msh-my-hub .mh-edhead h2.mh-h2{font-family:' + SERIF + '!important;font-size:28px;font-weight:600;color:#0B1C33!important;letter-spacing:-.3px;}',
      '#msh-my-hub .mh-edhead .sub{display:block;font-size:13.5px;color:#5B6573;margin-top:6px;max-width:680px;line-height:1.55;}',
      '#msh-my-hub .mh-edhead .act{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}',
      '#msh-my-hub .mh-edhead .cnt{font-size:12.5px;color:#5B6573;margin-right:6px;}',
      '#msh-my-hub .mh-edhead .cnt b{font-size:18px;color:#0B1C33;font-variant-numeric:tabular-nums;margin-right:3px;}',
      '#msh-my-hub .mh-edgrid{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:22px;align-items:start;}',
      '@media(min-width:1900px){#msh-my-hub .mh-edgrid{grid-template-columns:minmax(0,1fr) 440px;}}',
      '@media(max-width:1000px){#msh-my-hub .mh-edgrid{grid-template-columns:minmax(0,1fr);}}',
      '#msh-my-hub .mh-cat{padding:20px 22px 8px;}',
      '#msh-my-hub .mh-tools{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;}',
      '#msh-my-hub .mh-tools input,#msh-my-hub .mh-tools select{flex:1 1 220px;min-width:0;height:42px;padding:0 13px;border:1px solid #D9D1C2;border-radius:9px;font-family:inherit;font-size:14px;color:#1D2733;background:#FFFFFF;}',
      '#msh-my-hub .mh-tools input:focus,#msh-my-hub .mh-tools select:focus{outline:none;border-color:#0B1C33;box-shadow:0 0 0 3px rgba(168,132,44,.22);}',
      '#msh-my-hub .mh-group{border-top:1px solid #EFEAE0;}',
      '#msh-my-hub .mh-gh{display:flex;align-items:center;gap:10px;width:100%;background:none;border:0;padding:14px 2px;cursor:pointer;text-align:left;font-size:14px;font-weight:700;color:#0B1C33;}',
      '#msh-my-hub .mh-gh em{font-style:normal;font-weight:600;font-size:12px;color:#5B6573;margin-left:auto;font-variant-numeric:tabular-nums;}',
      '#msh-my-hub .mh-gh em.has{color:#7E6118;}',
      '#msh-my-hub .mh-gh .cv{width:6px;height:6px;border-right:1.6px solid #5B6573;border-bottom:1.6px solid #5B6573;transform:rotate(-45deg);transition:transform .2s;margin:0 4px;}',
      '#msh-my-hub .mh-group.open .mh-gh .cv{transform:rotate(45deg);}',
      '#msh-my-hub .mh-group .mh-opts{display:none;}',
      '#msh-my-hub .mh-group.open .mh-opts{display:grid;}',
      '#msh-my-hub .mh-opts{grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:6px;padding:0 0 16px;}',
      '#msh-my-hub .mh-opts label{display:flex;gap:10px;align-items:flex-start;font-size:13.5px;line-height:1.4;padding:9px 11px;cursor:pointer;border:1px solid #EFEAE0;border-radius:9px;background:#FFFFFF;transition:border-color .12s,background .12s;}',
      '#msh-my-hub .mh-opts label:hover{border-color:#CFC6B5;}',
      '#msh-my-hub .mh-opts label.on{border-color:#0B1C33;background:#F7F4EE;}',
      '#msh-my-hub .mh-opts input{margin-top:2px;accent-color:#0B1C33;width:15px;height:15px;flex:none;}',
      '#msh-my-hub .mh-opts small{display:inline-block;margin-left:4px;font-size:10px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:#7E6118;}',
      '#msh-my-hub .mh-ord{padding:18px 18px 16px;position:sticky;top:calc(var(--wp-admin--admin-bar--height,0px) + 16px);}',
      '#msh-my-hub .mh-ord .hd{display:flex;align-items:center;justify-content:space-between;padding-bottom:10px;border-bottom:2px solid #0B1C33;margin-bottom:4px;}',
      '.msh #msh-my-hub .mh-ord h3{font-size:12px!important;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:#0B1C33!important;}',
      '#msh-my-hub .mh-order{list-style:none;margin:0;padding:0;max-height:none;}',
      '#msh-my-hub .mh-order li{display:flex;align-items:center;gap:6px;padding:8px 0;border-bottom:1px solid #EFEAE0;font-size:13.5px;}',
      '#msh-my-hub .mh-order li .i{font-family:' + MONO + ';font-size:11px;color:#7E6118;width:22px;flex:none;}',
      '#msh-my-hub .mh-order li span.l{flex:1;min-width:0;}',
      '#msh-my-hub .mh-order button{background:#FFFFFF;border:1px solid #E6E0D4;border-radius:7px;width:28px;height:28px;cursor:pointer;color:#1D2733;font-size:12px;flex:none;}',
      '#msh-my-hub .mh-order button:hover:not(:disabled){border-color:#0B1C33;}',
      '#msh-my-hub .mh-order button:disabled{opacity:.35;cursor:default;}',
      '#msh-my-hub .mh-ord .none{font-size:13px;color:#5B6573;padding:14px 0 4px;line-height:1.55;}',
      '#msh-my-hub .mh-ord .ft{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap;}',

      /* ---- round 3: group accents. Icon on a coloured square; every pair
         clears 3:1 for the icon, and no text sits on these. ---- */
      '#msh-my-hub .ga,.msh #mh-tl .ga{flex:none;display:flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:11px;border:1px solid transparent;}',
      '#msh-my-hub .ga .mh-ic,.msh #mh-tl .ga .mh-ic{width:20px;height:20px;}',
      '#msh-my-hub .ga.g-tools,.msh #mh-tl .ga.g-tools{background:#0B1C33;color:#E0BE8E;}',
      '#msh-my-hub .ga.g-live,.msh #mh-tl .ga.g-live{background:#6B2A34;color:#F3E4E1;}',
      '#msh-my-hub .ga.g-procurement,.msh #mh-tl .ga.g-procurement{background:#14304F;color:#FFFFFF;}',
      '#msh-my-hub .ga.g-nhs,.msh #mh-tl .ga.g-nhs{background:#F3E4E1;border-color:#e3c3bd;color:#6B2A34;}',
      '#msh-my-hub .ga.g-career,.msh #mh-tl .ga.g-career{background:#F3ECDC;border-color:#E3D3AE;color:#6B5418;}',
      '#msh-my-hub .ga.g-clinical,.msh #mh-tl .ga.g-clinical{background:#E9EEF5;border-color:#CCD7E5;color:#14304F;}',
      '#msh-my-hub .ga.g-account,.msh #mh-tl .ga.g-account{background:#EDE7DC;border-color:#DCD3C2;color:#3A4552;}',
      '#msh-my-hub .ga.g-specialities{background:#7E6118;color:#FFFFFF;}',

      /* ---- section heads with an icon, count pill ---- */
      '#msh-my-hub .mh-sh .sic{flex:none;width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#0B1C33;color:#E0BE8E;}',
      '#msh-my-hub .mh-band.ox .mh-sh .sic{background:#F3E4E1;color:#6B2A34;}',
      '#msh-my-hub .mh-band.bl .mh-sh .sic{background:#6B2A34;color:#F3E4E1;}',
      '#msh-my-hub .mh-sh .pill{flex:none;font-size:12px;font-weight:700;color:#0B1C33;background:#EDE7DC;border-radius:999px;padding:2px 10px;font-variant-numeric:tabular-nums;}',
      '#msh-my-hub .mh-band.bl .mh-sh .pill{background:#FFFFFF;color:#6B2A34;border:1px solid #e3c3bd;}',
      '.msh #msh-my-hub .mh-sh a.more{display:inline-flex;align-items:center;min-height:36px;padding:0 14px;border:1px solid #D6CDBD;border-radius:999px;background:#FFFFFF;}',
      '.msh #msh-my-hub .mh-sh a.more:hover{border-color:#0B1C33;text-decoration:none;}',

      /* ---- panel window tag and full-page link ---- */
      '#msh-my-hub .mh-ph .sub{display:inline-block;margin-top:5px;font-size:10.5px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#5B6573;}',
      '#msh-my-hub .mh-ph .sub.all{color:#A12B2B;}',
      '.msh #msh-my-hub .mh-ph a.full{display:inline-flex;align-items:center;min-height:34px;padding:0 12px;border:1px solid #E6E0D4;border-radius:999px;background:#FFFFFF;margin-top:0;}',
      '.msh #msh-my-hub .mh-ph a.full:hover{border-color:#0B1C33;text-decoration:none;}',
      '#msh-my-hub .mh-more{min-height:44px;}',
      '@media(max-width:480px){#msh-my-hub .mh-ph .tx{flex:1 1 0;}}',
      /* fewer words on the front page: summaries are a taste, the story is one click */
      '.msh #msh-my-hub .mh-s p.s{-webkit-line-clamp:3;}',
      '.msh #msh-my-hub .mh-lead p.s{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}',
      '@media(max-width:700px){.msh #msh-my-hub .mh-s p.s{display:none;}.msh #msh-my-hub .mh-lead p.s{font-size:14.5px;}}',
      '@media(max-width:1000px){#msh-my-hub .mh-bar-r{justify-content:flex-start;}#msh-my-hub .mh-bar-r .mh-scope{margin-right:auto;}}',

      /* ---- sticky bar: Tools button ---- */
      '#msh-my-hub .mh-btn.tl{background:#E0BE8E;border-color:#C9A227;color:#0B1C33!important;}',
      '#msh-my-hub .mh-btn.tl:hover,#msh-my-hub .mh-btn.tl[aria-expanded="true"]{background:#F0D7AE;border-color:#8C6A1C;box-shadow:0 4px 14px -4px rgba(140,106,28,.55);}',
      '#msh-my-hub .mh-bar .mh-btn{min-height:40px;}',
      '#msh-my-hub .mh-scope button{min-height:34px;}',
      '#msh-my-hub .mh-scope .sh{display:none;}',
      '@media(max-width:560px){#msh-my-hub .mh-scope .lg{display:none;}#msh-my-hub .mh-scope .sh{display:inline;}#msh-my-hub .mh-bar .mh-btn.cz .t{display:none;}#msh-my-hub .mh-bar .mh-btn .mh-ic{display:block;}#msh-my-hub .mh-bar .mh-btn.cz{padding:9px 11px;}}',

      /* ---- quick tools row ---- */
      '#msh-my-hub .mh-quick{margin:0 0 40px;}',
      '#msh-my-hub .mh-qg{display:grid;grid-template-columns:repeat(var(--qn,9),minmax(0,1fr));gap:12px;}',
      '.msh #msh-my-hub .mh-qt{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:12px;min-height:124px;padding:20px 10px 16px;background:#FFFFFF;border:1px solid #D6CDBD;border-radius:14px;color:#0B1C33;text-align:center;cursor:pointer;font:inherit;box-shadow:0 1px 2px rgba(11,28,51,.05);transition:border-color .15s,box-shadow .2s,transform .2s;}',
      '.msh #msh-my-hub .mh-qt:hover{border-color:#0B1C33;transform:translateY(-2px);box-shadow:0 14px 28px -16px rgba(11,28,51,.4);color:#0B1C33;}',
      '.msh #msh-my-hub .mh-qt .ga{width:48px;height:48px;border-radius:13px;}',
      '.msh #msh-my-hub .mh-qt .ga .mh-ic{width:23px;height:23px;}',
      '#msh-my-hub .mh-qt .lb{font-size:13.5px;font-weight:600;line-height:1.3;color:#0B1C33;}',
      '.msh #msh-my-hub button.mh-qt.all{background:#0B1C33;border-color:#0B1C33;}',
      '.msh #msh-my-hub button.mh-qt.all .lb{color:#FFFFFF;}',
      '.msh #msh-my-hub button.mh-qt.all .ga{background:#E0BE8E;color:#0B1C33;}',
      '.msh #msh-my-hub button.mh-qt.all:hover{background:#14304F;}',
      '@media(max-width:1280px){#msh-my-hub .mh-qg{grid-template-columns:repeat(3,minmax(0,1fr));}.msh #msh-my-hub .mh-qt{flex-direction:row;min-height:64px;padding:10px 14px;text-align:left;gap:14px;}.msh #msh-my-hub .mh-qt .ga{width:42px;height:42px;}}',
      '@media(max-width:640px){#msh-my-hub .mh-qg{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}.msh #msh-my-hub .mh-qt{padding:9px 10px;gap:10px;min-height:60px;border-radius:12px;}.msh #msh-my-hub .mh-qt .ga{width:36px;height:36px;border-radius:10px;}.msh #msh-my-hub .mh-qt .ga .mh-ic{width:19px;height:19px;}#msh-my-hub .mh-qt .lb{font-size:12.5px;}.msh #msh-my-hub .mh-qt.all{grid-column:1 / -1;justify-content:center;}#msh-my-hub .mh-quick{margin-bottom:30px;}}',

      /* ---- Tools launcher: an overlay panel, one screen of icon tiles ---- */
      '.msh #mh-tl{display:none;position:fixed;inset:0;z-index:100000;font-family:' + SANS + ';color:#1D2733;font-size:14.5px;line-height:1.45;}',
      '.msh #mh-tl.open{display:block;}',
      '.msh #mh-tl .mh-ic{width:18px;height:18px;display:block;flex:none;}',
      '.msh #mh-tl .bg{position:absolute;inset:0;background:rgba(11,28,51,.62);-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px);animation:mhfade .15s ease;}',
      '.msh #mh-tl .pn{position:relative;display:flex;flex-direction:column;width:min(1480px,calc(100% - 48px));max-height:calc(100vh - 80px);margin:40px auto 0;background:#F8F8F6;border-radius:18px;overflow:hidden;box-shadow:0 30px 80px -20px rgba(4,12,24,.7);animation:mhpop .18s ease;}',
      '.msh #mh-tl .hd{position:relative;flex:none;background:#0B1C33;background-image:radial-gradient(90% 140% at 100% 0%,rgba(224,190,142,.16) 0%,rgba(224,190,142,0) 60%),linear-gradient(160deg,#0B1C33 0%,#14304F 100%);padding:22px 26px 18px;}',
      '.msh #mh-tl .hd:before{content:"";position:absolute;left:26px;top:0;width:56px;height:3px;background:linear-gradient(115deg,#8C6A1C 0%,#C9A227 45%,#8C6A1C 100%);}',
      '.msh #mh-tl .tr{display:flex;align-items:center;gap:12px;margin-bottom:16px;}',
      '.msh #mh-tl h2.tt{font-family:' + SERIF + '!important;font-size:26px!important;font-weight:600;letter-spacing:-.3px;line-height:1.1;color:#FFFFFF!important;margin:0;}',
      '.msh #mh-tl .tr .n{font-size:12px;font-weight:700;color:#0B1C33;background:#E0BE8E;border-radius:999px;padding:2px 10px;font-variant-numeric:tabular-nums;}',
      '.msh #mh-tl .x{margin-left:auto;width:44px;height:44px;border-radius:11px;border:1px solid rgba(224,190,142,.45);background:transparent;color:#FFFFFF;cursor:pointer;display:flex;align-items:center;justify-content:center;}',
      '.msh #mh-tl .x:hover{background:rgba(224,190,142,.14);border-color:#E0BE8E;}',
      '.msh #mh-tl .sr{position:relative;}',
      '.msh #mh-tl .sr .mh-ic{position:absolute;left:15px;top:50%;margin-top:-9px;color:#5B6573;pointer-events:none;}',
      '.msh #mh-tl input.q{width:100%;height:50px;padding:0 16px 0 44px;border:1px solid #FFFFFF;border-radius:12px;background:#FFFFFF;font-family:inherit;font-size:16px;color:#1D2733;box-shadow:none;margin:0;}',
      '.msh #mh-tl input.q:focus{outline:none;box-shadow:0 0 0 3px rgba(224,190,142,.65);}',
      '.msh #mh-tl .ch{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px;}',
      '.msh #mh-tl .ch button{display:inline-flex;align-items:center;gap:7px;min-height:34px;padding:0 13px 0 10px;border-radius:999px;border:1px solid rgba(219,227,238,.3);background:transparent;color:#DBE3EE;font-family:inherit;font-size:12.5px;font-weight:600;cursor:pointer;}',
      '.msh #mh-tl .ch button .mh-ic{width:15px;height:15px;}',
      '.msh #mh-tl .ch button:hover{border-color:#E0BE8E;color:#FFFFFF;}',
      '.msh #mh-tl .ch button[aria-pressed="true"]{background:#E0BE8E;border-color:#E0BE8E;color:#0B1C33;}',
      '.msh #mh-tl .bd{flex:1 1 auto;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:22px 26px 28px;}',
      '.msh #mh-tl .grp{margin-bottom:24px;}',
      '.msh #mh-tl .grp:last-child{margin-bottom:0;}',
      '.msh #mh-tl .gh{display:flex;align-items:center;gap:10px;margin-bottom:10px;}',
      '.msh #mh-tl .gh .ga{width:28px;height:28px;border-radius:8px;}',
      '.msh #mh-tl .gh .ga .mh-ic{width:15px;height:15px;}',
      '.msh #mh-tl h3.gt{font-family:' + SANS + '!important;font-size:12px!important;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;color:#0B1C33!important;margin:0;}',
      '.msh #mh-tl .gh .c{font-size:12px;font-weight:600;color:#5B6573;font-variant-numeric:tabular-nums;}',
      '.msh #mh-tl .gh:after{content:"";flex:1;height:1px;background:#E1D9CB;}',
      '.msh #mh-tl .gg{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;}',
      '.msh #mh-tl a.ti .ga{width:34px;height:34px;border-radius:9px;}',
      '.msh #mh-tl a.ti .ga .mh-ic{width:17px;height:17px;}',
      '.msh #mh-tl a.ti{display:flex;align-items:center;gap:11px;min-height:54px;padding:8px 12px 8px 9px;background:#FFFFFF;border:1px solid #E6E0D4;border-radius:12px;color:#0B1C33!important;text-decoration:none!important;transition:border-color .12s,box-shadow .15s,transform .15s;}',
      '.msh #mh-tl a.ti:hover{border-color:#0B1C33;box-shadow:0 10px 22px -14px rgba(11,28,51,.45);transform:translateY(-1px);}',
      '.msh #mh-tl a.ti:focus-visible{outline:2px solid #A8842C;outline-offset:2px;}',
      '.msh #mh-tl a.ti .lb{font-size:13.5px;font-weight:600;line-height:1.3;color:#0B1C33;}',
      '.msh #mh-tl a.ti mark{background:#F3E4E1;color:#0B1C33;border-radius:3px;padding:0 1px;}',
      '.msh #mh-tl .no{padding:30px 4px;text-align:center;color:#5B6573;font-size:14px;}',
      '.msh #mh-tl .no button{background:none;border:0;color:#14304F;font:inherit;font-weight:700;cursor:pointer;text-decoration:underline;text-decoration-color:#A8842C;text-underline-offset:3px;}',
      '@media(max-width:640px){.msh #mh-tl .pn{width:100%;margin:0;max-height:100vh;height:100%;border-radius:0;}.msh #mh-tl .hd{padding:16px 16px 14px;}.msh #mh-tl .hd:before{left:16px;}.msh #mh-tl h2.tt{font-size:22px!important;}.msh #mh-tl .tr{margin-bottom:12px;}.msh #mh-tl .ch{flex-wrap:nowrap;overflow-x:auto;margin-left:-16px;margin-right:-16px;padding:0 16px 2px;scrollbar-width:none;}.msh #mh-tl .ch button{flex:none;}.msh #mh-tl .bd{padding:16px 16px 28px;}.msh #mh-tl .gg{grid-template-columns:repeat(2,minmax(0,1fr));}.msh #mh-tl a.ti{min-height:56px;padding:8px 10px 8px 8px;gap:9px;}.msh #mh-tl a.ti .ga{width:34px;height:34px;border-radius:9px;}.msh #mh-tl a.ti .ga .mh-ic{width:17px;height:17px;}.msh #mh-tl a.ti .lb{font-size:12.5px;}}',
      '@keyframes mhfade{from{opacity:0}to{opacity:1}}',
      '@keyframes mhpop{from{opacity:0;transform:translateY(-8px) scale(.99)}to{opacity:1;transform:none}}',
      '@media (prefers-reduced-motion:reduce){.msh #mh-tl *{animation:none!important;transition:none!important;}}',

      /* ---- your pages: icon tiles ---- */
      '.msh #msh-my-hub a.mh-tile{min-height:0;flex-direction:row;align-items:center;justify-content:flex-start;gap:14px;padding:16px 50px 16px 16px;}',
      '.msh #msh-my-hub a.mh-tile:before{display:none;}',
      '#msh-my-hub .mh-tile .tx{display:block;min-width:0;}',
      '#msh-my-hub .mh-tile .gp{display:block;font-size:10px;letter-spacing:1.2px;text-transform:uppercase;color:#5B6573;font-weight:700;}',
      '#msh-my-hub .mh-tile b{margin-top:3px;padding-right:0;}',
      '#msh-my-hub .mh-tile .go{top:50%;bottom:auto;margin-top:-14px;width:28px;height:28px;border:1px solid #E6E0D4;}',
      '#msh-my-hub .mh-tile:hover .go,#msh-my-hub .mh-tile:nth-child(even):hover .go{background:#0B1C33;color:#E0BE8E;border-color:#0B1C33;}',
      '.msh #msh-my-hub a.mh-tile:nth-child(even):hover{border-color:#0B1C33;}',
      '#msh-my-hub .mh-tiles{grid-template-columns:repeat(auto-fill,minmax(260px,1fr));}',
      '@media(max-width:640px){#msh-my-hub .mh-tiles{grid-template-columns:minmax(0,1fr);gap:8px;}.msh #msh-my-hub a.mh-tile{padding:12px 48px 12px 12px;}}',

      /* ---- layout width: fill big monitors, keep measure sane ---- */
      '#msh-my-hub .mh-in{max-width:2280px;margin:0 auto;}'
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
            // A few feed items carry a future "published" date (event listings
            // dated to the event). They are not today's news, so they sort after
            // everything already published instead of sitting on top of it.
            var now = new Date().toISOString();
            got.sort(function (a, b) {
              var fa = String(a.it.published || '') > now ? 1 : 0, fb = String(b.it.published || '') > now ? 1 : 0;
              if (fa !== fb) { return fa - fb; }
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

  /* ---------- the lists, shared by panels, briefing and section bar ----------
     Each returns null while loading, false if the feed failed, else an array. */
  function newsList() {
    var l = FEED.news;
    if (!l) { return l; }
    return spread(l.filter(function (g) { return specMatch([g.spec]); }));
  }
  function eventsList() {
    var cal = FEED.cal;
    if (!cal) { return cal; }
    var end = addDays(TODAY, EVENT_DAYS);
    return cal.filter(function (e) {
      return (e.type === 'event' || e.type === 'awareness') && (e.endDate || e.date) >= TODAY && e.date <= end && specMatch(e.specialities);
    }).sort(function (a, b) { return String(a.date).localeCompare(String(b.date)); });
  }
  function alertsList() { return FEED.mhra; }
  var PROC = {
    'framework-start': ['fw', 'Framework starts'],
    'framework-end': ['fw', 'Framework ends'],
    'contract-expiry': ['ct', 'Contract ends'],
    'action-deadline': ['ct', 'Deadline']
  };
  function procList() {
    var cal = FEED.cal;
    if (!cal) { return cal; }
    var end = addDays(TODAY, PROC_DAYS);
    return cal.filter(function (e) { return PROC[e.type] && e.date >= TODAY && e.date <= end && specMatch(e.specialities); })
      .sort(function (a, b) { return String(a.date).localeCompare(String(b.date)); });
  }

  /* ---------- rows ---------- */
  function row(key, head, detail, lead) {
    var open = !!openRows[key];
    return '<li class="mh-item' + (open ? ' open' : '') + '">'
      + '<button type="button" class="mh-row" data-row="' + esc(key) + '" aria-expanded="' + (open ? 'true' : 'false') + '">'
      + (lead || '') + '<span class="bd">' + head + '</span><span class="ch" aria-hidden="true"></span></button>'
      + '<div class="mh-det">' + detail + '</div></li>';
  }
  function links(list) {
    var seen = {};
    var h = list.filter(function (l) {
      if (!l || !l.url || seen[l.url]) { return false; }
      seen[l.url] = 1; return true;
    }).map(function (l) {
      var ext = /^https?:/.test(l.url) && l.url.indexOf('medsalesintelligencehub.co.uk') === -1;
      return '<a href="' + esc(l.url) + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + '>' + esc(l.label) + (ext ? EXT : ARR) + '</a>';
    }).join('');
    return h ? '<div class="lk">' + h + '</div>' : '';
  }
  function why(label, text) { return text ? '<p class="why"><b>' + esc(label) + '</b>' + esc(text) + '</p>' : ''; }
  function moreBtn(panel, total, shown, noun) {
    if (total <= shown) { return ''; }
    var open = !!openPanels[panel];
    return '<button type="button" class="mh-more" data-more="' + panel + '" aria-expanded="' + (open ? 'true' : 'false') + '">'
      + (open ? 'Show fewer' : 'Show all <span class="n">' + total + '</span> ' + noun) + '<span class="cv" aria-hidden="true"></span></button>';
  }
  function emptyMine(what, all) {
    return '<p class="mh-empty">Nothing ' + what + ' for your specialities. <button type="button" data-scope="all">Show the whole Hub' + (all ? ' (' + all + ')' : '') + '</button></p>';
  }
  /* The same list with the speciality filter off, for honest empty states. */
  function wholeHub(fn) { var keep = scope; scope = 'all'; var l = fn(); scope = keep; return l ? l.length : 0; }
  function skRows(n, chip) {
    var h = '';
    for (var i = 0; i < n; i++) {
      h += '<div class="sk-row">' + (chip ? '<span class="sk" style="width:58px;height:52px;flex:none;border-radius:9px;"></span>' : '')
        + '<span style="flex:1;"><span class="sk" style="width:38%;height:9px;margin:3px 0 9px;"></span><span class="sk" style="width:' + (92 - i * 7) + '%;height:13px;"></span><span class="sk" style="width:55%;height:10px;margin-top:9px;"></span></span></div>';
    }
    return h;
  }
  function panelHead(id, ico, title, count, sub, href, hrefLabel, tone, subCls) {
    return '<div class="mh-ph"><span class="ib' + (tone ? ' ' + tone : '') + '">' + icon(ico) + '</span><span class="tx"><h2 class="mh-h3">' + title
      + (count !== null ? ' <span class="n">' + count + '</span>' : '') + '</h2><span class="sub' + (subCls ? ' ' + subCls : '') + '">' + sub + '</span></span>'
      + '<a class="full" href="' + href + '">' + hrefLabel + ARR + '</a></div>';
  }
  function secHead(ico, title, count, href, hrefLabel) {
    return '<div class="mh-sh"><span class="sic">' + icon(ico) + '</span><h2 class="mh-h2">' + title + '</h2>'
      + (count !== null && count !== undefined && count !== '' ? '<span class="pill">' + count + '</span>' : '') + '<span class="rule"></span>'
      + (href ? '<a class="more" href="' + href + '">' + hrefLabel + ARR + '</a>' : '') + '</div>';
  }

  /* ---------- key news: the front page ---------- */
  function newsSection() {
    var list = newsList();
    var h = '<section class="mh-sec" id="mh-news">' + secHead('news', 'Key news', list ? list.length : null, PAGES.news, 'All news') + '<div class="mh-card mh-front">';
    if (list === null) {
      return h + '<div class="mh-fp"><div class="a-lead"><div class="mh-lead" style="min-height:340px;"><span class="sk dk" style="width:30%;height:10px;"></span><span class="sk dk" style="width:92%;height:26px;margin-top:10px;"></span><span class="sk dk" style="width:70%;height:26px;"></span><span class="sk dk" style="width:96%;height:12px;margin-top:14px;"></span><span class="sk dk" style="width:88%;height:12px;"></span><span class="sk dk" style="width:60%;height:12px;"></span></div></div>'
        + '<div class="a-s1">' + skRows(1) + '</div><div class="a-s2">' + skRows(1) + '</div><div class="a-list">' + skRows(5) + '</div></div></div></section>';
    }
    if (list === false) { return h + '<p class="mh-empty">News is unavailable just now.</p></div></section>'; }
    if (!list.length) { return h + (narrowed() ? emptyMine('new', wholeHub(newsList)) : '<p class="mh-empty">No news in the last 60 days.</p>') + '</div></section>'; }

    var lead = list[0], it = lead.it, spec = BYID[lead.spec], ls = newsStamp(it.published);
    h += '<div class="mh-fp"><div class="a-lead"><article class="mh-lead">'
      + '<span class="k">' + (it.opportunity ? '<span class="mh-opp">Opportunity</span>' : '') + '<span>Lead story</span><span class="dot"></span><span>' + esc(spec.label) + '</span></span>'
      + '<h3 class="t"><a href="' + esc(it.link) + '" target="_blank" rel="noopener">' + esc(it.title) + '</a></h3>'
      + (it.summary ? '<p class="s">' + esc(it.summary) + '</p>' : '')
      + '<span class="m">' + esc([ls.label, it.source].filter(Boolean).join(' · ')) + '</span>'
      + '<div class="acts"><a href="' + esc(it.link) + '" target="_blank" rel="noopener">Read story' + EXT + '</a>'
      + '<a class="sec" href="' + esc(spec.url) + '">' + esc(spec.label) + ARR + '</a></div></article></div>';

    var secs = list.slice(1, 1 + NEWS_SEC);
    secs.forEach(function (g, i) {
      var s = g.it, sp = BYID[g.spec], st = newsStamp(s.published);
      h += '<div class="a-s' + (i + 1) + '">' + (i === 0 ? '<div class="mh-colh"><span>Also leading</span></div>' : '<div class="mh-colh mh-colh2"><span>Also leading</span></div>')
        + '<article class="mh-s"><span class="kk">' + (s.opportunity ? '<span class="mh-opp">Opportunity</span> ' : '') + esc(sp.label) + '</span>'
        + '<h3 class="t"><a href="' + esc(s.link) + '" target="_blank" rel="noopener">' + esc(s.title) + '</a></h3>'
        + (s.summary ? '<p class="s">' + esc(s.summary) + '</p>' : '')
        + '<span class="m">' + esc([st.label, s.source].filter(Boolean).join(' · ')) + '</span>'
        + links([{ label: 'Full story', url: s.link }, { label: sp.label, url: sp.url }]) + '</article></div>';
    });

    var heads = list.slice(1 + NEWS_SEC, NEWS_TOP);
    if (heads.length) {
      h += '<div class="a-list"><div class="mh-colh"><span>Latest headlines</span></div><ul class="mh-list">' + heads.map(newsRow).join('') + '</ul></div>';
    }
    h += '</div>';
    if (openPanels.news) {
      h += '<div class="mh-rest"><ul class="mh-list">' + list.slice(NEWS_TOP).map(newsRow).join('') + '</ul></div>';
    }
    h += moreBtn('news', list.length, NEWS_TOP, 'stories');
    return h + '</div></section>';
  }
  /* The stories above "Show all" carry at most two per speciality, so one
     busy trade feed can't fill the top of the page. Newest first still holds
     inside that, and nothing is dropped: the rest follow in date order.
     The cap only bites when enough specialities are in scope to fill it. */
  function spread(list) {
    var top = [], rest = [], per = {};
    list.forEach(function (g) {
      if (top.length < NEWS_TOP && (per[g.spec] || 0) < 2) { top.push(g); per[g.spec] = (per[g.spec] || 0) + 1; }
      else { rest.push(g); }
    });
    // With only a few specialities in scope the cap can leave gaps; fill them
    // with the next newest, then keep the top in date order.
    while (top.length < NEWS_TOP && rest.length) { top.push(rest.shift()); }
    var now = new Date().toISOString();
    top.sort(function (a, b) {
      var fa = String(a.it.published || '') > now ? 1 : 0, fb = String(b.it.published || '') > now ? 1 : 0;
      return (fa - fb) || String(b.it.published || '').localeCompare(String(a.it.published || ''));
    });
    return top.concat(rest);
  }
  function newsRow(g) {
    var it = g.it, spec = BYID[g.spec], st = newsStamp(it.published);
    var head = '<span class="kk">' + (it.opportunity ? '<span class="mh-opp">Opportunity</span>' : '') + '<span>' + esc(spec.label) + '</span><span class="tm">' + esc(st.label) + '</span></span>'
      + '<span class="tt serif">' + esc(it.title) + '</span>'
      + (it.source ? '<span class="mm">' + esc(it.source) + '</span>' : '');
    var det = (it.summary ? '<p>' + esc(it.summary) + '</p>' : '')
      + links([{ label: 'Read story', url: it.link }, { label: spec.label, url: spec.url }]);
    return row('n:' + it.link, head, det);
  }

  /* ---------- coming up: events and awareness days, as an agenda ---------- */
  function dateChip(e) {
    var d = parseDay(e.date);
    if (!d) { return '<span class="mh-chip"></span>'; }
    var now = e.date < TODAY;   // started before today and still running
    if (now) { return '<span class="mh-chip now"><i>On</i><b>now</b><i>to ' + esc(fmtShort(e.endDate)) + '</i></span>'; }
    return '<span class="mh-chip' + (e.date === TODAY ? ' now' : '') + '"><i>' + DAYS[d.getDay()] + '</i><b>' + d.getDate() + '</b><i>' + MONTHS[d.getMonth()] + '</i></span>';
  }
  function eventsPanel() {
    var list = eventsList();
    var h = '<div class="mh-card mh-panel" id="mh-events">' + panelHead('mh-events', 'cal', 'Coming up', list ? list.length : null,
      'Next ' + EVENT_DAYS + ' days', PAGES.calendar, 'Calendar');
    if (list === null) { return h + skRows(4, true) + '</div>'; }
    if (list === false) { return h + '<p class="mh-empty">The Calendar is unavailable just now.</p></div>'; }
    if (!list.length) { return h + (narrowed() ? emptyMine('coming up', wholeHub(eventsList)) : '<p class="mh-empty">Nothing in the next ' + EVENT_DAYS + ' days.</p>') + '</div>'; }
    var shown = openPanels.events ? list : list.slice(0, PANEL_TOP);
    var wk = addDays(TODAY, 6), mo = addDays(TODAY, 30), last = '';
    var body = shown.map(function (e) {
      var band = e.date <= wk ? 'Next 7 days' : (e.date <= mo ? '8 to 30 days' : 'Later');
      var g = band !== last ? '<li class="mh-grp">' + band + '</li>' : '';
      last = band;
      var aw = e.type === 'awareness';
      var ongoing = e.date < TODAY;
      var when = e.endDate ? fmtDate(e.date) + ' to ' + fmtDate(e.endDate) : fmtDate(e.date);
      var head = '<span class="kk"><span class="mh-tag ' + (aw ? 'aw">Awareness' : 'ev">Event') + '</span>' + (ongoing ? '<span class="mh-tag on">On now</span>' : '')
        + '<span class="tm">' + esc(ongoing ? 'Ends ' + fmtShort(e.endDate) : whenLabel(e.date)) + '</span></span>'
        + '<span class="tt">' + esc(e.title) + '</span>'
        + (e.location || e.owner ? '<span class="mm">' + esc(e.location || e.owner) + '</span>' : '');
      var det = '<p>' + esc([when, e.location, e.audience].filter(Boolean).join(' · ')) + '</p>'
        + why('Rep angle', e.repAction)
        + (e.note && (!e.location || e.note.indexOf(e.location) === -1) ? '<p>' + esc(e.note) + '</p>' : '')
        + links((e.links || []).concat(e.source ? [{ label: 'Organiser’s page', url: e.source }] : []));
      return g + row('e:' + e.id, head, det, dateChip(e));
    }).join('');
    return h + '<ul class="mh-list mh-withchip">' + body + '</ul>' + moreBtn('events', list.length, PANEL_TOP, 'events') + '</div>';
  }

  /* ---------- safety alerts: MHRA, never narrowed ---------- */
  function alertsPanel() {
    var list = alertsList();
    var h = '<div class="mh-card mh-panel mh-alerts" id="mh-alerts">' + panelHead('mh-alerts', 'alert', 'Safety alerts', list ? list.length : null,
      'All specialities', PAGES.mhra, 'MHRA Desk', 'red', 'all');
    if (list === null) { return h + skRows(4) + '</div>'; }
    if (list === false) { return h + '<p class="mh-empty">MHRA alerts are unavailable just now.</p></div>'; }
    if (!list.length) { return h + '<p class="mh-empty">No alerts in the current window.</p></div>'; }
    var shown = openPanels.alerts ? list : list.slice(0, PANEL_TOP);
    var body = shown.map(function (a) {
      var nat = a.alertType === 'national-patient-safety';
      var n = daysFrom(a.issuedDate);
      var fresh = n !== null && n >= -NEW_DAYS;
      var head = '<span class="kk">' + (fresh ? '<span class="mh-new">New</span>' : '')
        + '<span class="mh-tag ' + (nat ? 'np">Patient safety' : 'ds">Device safety') + '</span>'
        + (a.reference ? '<span class="mh-ref">' + esc(a.reference) + '</span>' : '')
        + '<span class="tm">' + esc(whenLabel(a.issuedDate)) + '</span></span>'
        + '<span class="tt">' + esc(String(a.title || '').replace(/\s*\(?\b(DSI|NatPSA)\/[^\s)]*\)?\s*$/i, '')) + '</span>'
        + '<span class="mm">Issued ' + esc(fmtDate(a.issuedDate)) + '</span>';
      var det = (a.description ? '<p>' + esc(a.description) + '</p>' : '')
        + why('For reps', a.play)
        + links([{ label: 'Alert on GOV.UK', url: a.url }]);
      return row('a:' + (a.reference || a.url), head, det, '<span class="mh-sev' + (nat ? ' np' : (fresh ? '' : ' old')) + '" aria-hidden="true"></span>');
    }).join('');
    return h + '<ul class="mh-list">' + body + '</ul>' + moreBtn('alerts', list.length, PANEL_TOP, 'alerts') + '</div>';
  }

  /* ---------- procurement deadlines, as a countdown ---------- */
  function countdown(s) {
    var n = daysFrom(s);
    if (n === null) { return '<span class="mh-cd"></span>'; }
    var soon = n <= SOON_DAYS;
    if (n === 0) { return '<span class="mh-cd soon"><b>0</b><i>Today</i></span>'; }
    return '<span class="mh-cd' + (soon ? ' soon' : '') + '"><b>' + n + '</b><i>' + (n === 1 ? 'day' : 'days') + '</i></span>';
  }
  function procPanel() {
    var list = procList();
    var h = '<div class="mh-card mh-panel" id="mh-proc">' + panelHead('mh-proc', 'proc', 'Procurement deadlines', list ? list.length : null,
      'Next 6 months', PAGES.procurement, 'Tenders', 'ox');
    if (list === null) { return h + skRows(4, true) + '</div>'; }
    if (list === false) { return h + '<p class="mh-empty">The Calendar is unavailable just now.</p></div>'; }
    if (!list.length) { return h + (narrowed() ? emptyMine('due', wholeHub(procList)) : '<p class="mh-empty">Nothing due in the next six months.</p>') + '</div>'; }
    var shown = openPanels.proc ? list : list.slice(0, PANEL_TOP);
    var body = shown.map(function (e) {
      var t = PROC[e.type];
      var head = '<span class="kk"><span class="mh-tag ' + t[0] + '">' + t[1] + '</span><span class="tm">' + esc(fmtDate(e.date)) + '</span></span>'
        + '<span class="tt">' + esc(String(e.title || '').replace(/^(Framework (starts|expires|ends)|Contract expires):\s*/i, '')) + '</span>'
        + '<span class="mm">' + esc(e.buyer || e.owner || '') + (money(e.value) ? (e.buyer || e.owner ? ' · ' : '') + '<span class="mh-val">' + esc(money(e.value)) + '</span>' : '') + '</span>';
      var det = '<p>' + esc([fmtDate(e.date), e.buyer ? 'Buyer: ' + e.buyer : '', e.supplier ? 'Supplier: ' + e.supplier : '', e.supplierCount ? e.supplierCount + ' suppliers' : ''].filter(Boolean).join(' · ')) + '</p>'
        + why('Note', e.note)
        + links(e.links || (e.source ? [{ label: 'Source notice', url: e.source }] : []));
      return row('p:' + e.id, head, det, countdown(e.date));
    }).join('');
    return h + '<ul class="mh-list mh-withchip">' + body + '</ul>' + moreBtn('proc', list.length, PANEL_TOP, 'dates') + '</div>';
  }

  function deskSection() {
    return '<section class="mh-sec mh-band ox" id="mh-desk">' + secHead('bell', 'On the desk', null, '', '')
      + '<div class="mh-desk">' + eventsPanel() + alertsPanel() + procPanel() + '</div></section>';
  }

  /* ---------- today's briefing: four counts, all from the live feeds ---------- */
  function paintBrief() {
    var el = document.getElementById('myh-brief');
    if (!el) { return; }
    var news = newsList(), al = alertsList(), ev = eventsList(), pr = procList();
    var wk = addDays(TODAY, 6), mo = addDays(TODAY, 30);
    function cell(jump, ico, tone, label, list, count, desc) {
      var v;
      if (list === null) { v = '<span class="sk"></span>'; }
      else if (list === false) { v = '<span class="v na">Unavailable</span>'; }
      else { v = '<span class="v">' + count(list) + '<span class="go">View ' + ARR + '</span></span>'; }
      return '<a class="mh-kpi" href="#' + jump + '" data-jump="' + jump + '"><span class="l"><span class="ib' + tone + '">' + icon(ico) + '</span>' + label + '</span>' + v + '<span class="d">' + desc + '</span></a>';
    }
    var mine = narrowed();
    el.innerHTML = '<div class="mh-kpis">'
      + cell('mh-news', 'news', '', 'New stories today', news, function (l) { return l.filter(function (g) { return newsStamp(g.it.published).day === TODAY; }).length; },
        mine ? 'Your specialities' : 'All 31 feeds')
      + cell('mh-alerts', 'alert', ' rd', 'Safety alerts', al, function (l) { return l.filter(function (a) { var n = daysFrom(a.issuedDate); return n !== null && n >= -NEW_DAYS; }).length; },
        'MHRA, last ' + NEW_DAYS + ' days')
      + cell('mh-events', 'cal', '', 'Events this week', ev, function (l) { return l.filter(function (e) { return e.date <= wk; }).length; },
        'Next 7 days')
      + cell('mh-proc', 'proc', ' rd', 'Deadlines this month', pr, function (l) { return l.filter(function (e) { return e.date <= mo; }).length; },
        'Next 30 days')
      + '</div>';
  }

  /* ---------- section bar counts ---------- */
  function paintBar() {
    var c = { news: newsList(), events: eventsList(), alerts: alertsList(), proc: procList() };
    Object.keys(c).forEach(function (k) {
      var s = mount.querySelector('[data-navn="' + k + '"]');
      if (s) { s.textContent = c[k] ? String(c[k].length) : ''; }
    });
  }

  function paintSections() {
    var s = document.getElementById('mh-feeds');
    paintBrief();
    if (!s) { return; }
    s.innerHTML = newsSection() + deskSection();
    paintBar();
  }

  /* ---------- the member's page ---------- */
  function bar() {
    var can = hasSpecs();
    var mine = narrowed();
    var n = visible(pins).length;
    function j(id, label, k) { return '<a href="#' + id + '" data-jump="' + id + '">' + label + (k ? ' <span class="c" data-navn="' + k + '"></span>' : '') + '</a>'; }
    return '<div class="mh-bar" role="navigation" aria-label="My Hub sections"><div class="mh-bar-in">'
      + '<div class="mh-jumps">' + j('mh-news', 'Key news', 'news') + j('mh-events', 'Coming up', 'events') + j('mh-alerts', 'Safety alerts', 'alerts') + j('mh-proc', 'Procurement', 'proc') + j('mh-pages', 'Your pages', '') + '</div>'
      + '<div class="mh-bar-r"><div class="mh-scope" role="group" aria-label="Show news and dates for">'
      + '<button type="button" data-scope="mine" aria-pressed="' + (mine ? 'true' : 'false') + '"' + (can ? '' : ' disabled title="Pin a speciality to use this"') + '><span class="lg">Your specialities</span><span class="sh">Mine</span></button>'
      + '<button type="button" data-scope="all" aria-pressed="' + (mine ? 'false' : 'true') + '"><span class="lg">Whole Hub</span><span class="sh">All</span></button></div>'
      + '<button type="button" class="mh-btn tl" data-act="tools" aria-haspopup="dialog" aria-expanded="false" aria-controls="mh-tl">' + icon('tools') + 'Tools</button>'
      + '<button type="button" class="mh-btn cz" data-act="edit" aria-label="' + (n ? 'Customise' : 'Build my page') + '">' + icon('pages') + '<span class="t">' + (n ? 'Customise' : 'Build my page') + '</span></button></div>'
      + '</div></div>';
  }

  function callout() {
    if (hasSpecs()) { return ''; }
    var n = visible(pins).length;
    return '<div class="mh-callout"><div><b>' + (n ? 'Pin a speciality to narrow this page' : 'Make this page yours') + '</b>'
      + '<span>' + (n ? 'Showing the whole Hub.' : 'Pin your specialities and pages.') + '</span></div>'
      + '<button type="button" class="mh-btn" data-act="edit">' + icon('pages') + (n ? 'Pin a speciality' : 'Build my page') + '</button></div>';
  }

  function pagesSection() {
    var list = visible(pins);
    var h = '<section class="mh-sec mh-band bl" id="mh-pages">' + secHead('pages', 'Your pages', list.length || null, '', '');
    if (!list.length) {
      h += '<div class="mh-blank"><span class="ib">' + icon('pages') + '</span><h3>Nothing pinned yet</h3>'
        + '<span class="t">Pin the pages you use most.</span>'
        + '<button type="button" class="mh-btn" data-act="edit">' + icon('pages') + 'Build my page</button></div>';
    } else {
      if (seeded) { h += '<p class="mh-note" style="margin:0 0 14px;">Suggested from your earlier interests. Not saved yet.</p>'; }
      h += '<div class="mh-tiles">' + list.map(function (id) {
        var it = BYID[id];
        return '<a class="mh-tile" href="' + esc(it.url) + '"><span class="ga g-' + esc(it.group) + '">' + icon(itemIcon(it)) + '</span><span class="tx"><span class="gp">' + esc(groupShort(it.group)) + '</span>'
          + '<b>' + esc(it.label) + '</b></span><span class="go" aria-hidden="true">→</span></a>';
      }).join('') + '</div>';
    }
    return h + saveNote() + '</section>';
  }

  function renderView() {
    var inline = !document.getElementById('myh-brief') || mount.querySelector('#myh-brief');
    var h = '<div class="mh-in">'
      + (inline ? '<div id="myh-brief" class="mh-brief-inline"></div>' : '')
      + bar() + callout() + quickRow() + '<div id="mh-feeds"></div>' + pagesSection() + '</div>';
    mount.innerHTML = h;
    paintSections();
    loadFeeds();
    spy();
  }

  /* ---------- quick tools: the most used desks, as big icon buttons ---------- */
  function toolsBtnAttrs() { return ' data-act="tools" aria-haspopup="dialog" aria-expanded="false" aria-controls="mh-tl"'; }
  function quickRow() {
    var ids = QUICK.filter(function (id) { return !!BYID[id]; });
    if (!ids.length) { return ''; }
    return '<div class="mh-quick" role="group" aria-label="Quick tools"><div class="mh-qg" style="--qn:' + (ids.length + 1) + ';">'
      + ids.map(function (id) {
        var it = BYID[id];
        return '<a class="mh-qt" href="' + esc(it.url) + '"><span class="ga g-' + esc(it.group) + '">' + icon(itemIcon(it)) + '</span><span class="lb">' + esc(it.label) + '</span></a>';
      }).join('')
      + '<button type="button" class="mh-qt all"' + toolsBtnAttrs() + '><span class="ga">' + icon('pages') + '</span><span class="lb">All tools</span></button>'
      + '</div></div>';
  }

  /* ---------- Tools launcher: every Hub page except specialities ----------
     Built from the catalogue each time it opens, grouped by catalogue group,
     so a page added to the catalogue appears here with no change to this
     file. Filter box at the top (Enter opens the first match), group chips,
     Esc or a click outside closes, focus is held inside while open and goes
     back to the button that opened it. */
  var TL = null, tlFrom = null, tlQ = '', tlG = '';
  function tlGroups() {
    var ids = LAUNCH_GROUPS.concat((CAT.groups || []).map(function (g) { return g.id; }).filter(function (g) { return g !== 'specialities' && LAUNCH_GROUPS.indexOf(g) === -1; }));
    return ids.filter(function (g) { return CAT.items.some(function (it) { return it.group === g; }); });
  }
  function tlTotal() { var gs = tlGroups(); return CAT.items.filter(function (it) { return gs.indexOf(it.group) !== -1; }).length; }
  /* Filter matches from the start of a word ("cal" finds The Calendar, not
     every "Clinical"), and returns where, for the highlight. */
  function wordAt(text, q) {
    if (!q) { return -1; }
    var t = ' ' + String(text).toLowerCase().replace(/[^a-z0-9£]/g, ' ');
    var i = t.indexOf(' ' + q.replace(/[^a-z0-9£]/g, ' '));
    return i === -1 ? -1 : i;
  }
  function hilite(label, q) {
    var i = wordAt(label, q);
    if (i === -1) { return esc(label); }
    return esc(label.slice(0, i)) + '<mark>' + esc(label.slice(i, i + q.length)) + '</mark>' + esc(label.slice(i + q.length));
  }
  function tlBody() {
    var q = tlQ.trim().toLowerCase(), h = '';
    tlGroups().forEach(function (g) {
      if (tlG && tlG !== g) { return; }
      var gl = groupLabel(g) + ' ' + groupShort(g);
      var rows = CAT.items.filter(function (it) { return it.group === g && (!q || wordAt(it.label, q) !== -1 || wordAt(gl, q) !== -1); });
      if (!rows.length) { return; }
      h += '<section class="grp"><div class="gh"><span class="ga g-' + esc(g) + '">' + icon((GROUP_UI[g] || {}).ic) + '</span><h3 class="gt">' + esc(groupShort(g)) + '</h3><span class="c">' + rows.length + '</span></div><div class="gg">'
        + rows.map(function (it) {
          return '<a class="ti" href="' + esc(it.url) + '"><span class="ga g-' + esc(g) + '">' + icon(itemIcon(it)) + '</span><span class="lb">' + hilite(it.label, q) + '</span></a>';
        }).join('') + '</div></section>';
    });
    return h || '<p class="no">No tool matches “' + esc(tlQ) + '”. <button type="button" data-tlclear="1">Clear</button></p>';
  }
  function tlChips() {
    return '<button type="button" data-tlg="" aria-pressed="' + (tlG ? 'false' : 'true') + '">' + icon('pages') + 'All</button>'
      + tlGroups().map(function (g) {
        return '<button type="button" data-tlg="' + esc(g) + '" aria-pressed="' + (tlG === g ? 'true' : 'false') + '">' + icon((GROUP_UI[g] || {}).ic) + esc(groupShort(g)) + '</button>';
      }).join('');
  }
  function tlPaint() {
    TL.querySelector('.bd').innerHTML = tlBody();
    TL.querySelector('.ch').innerHTML = tlChips();
  }
  function tlFocusables() {
    return Array.prototype.filter.call(TL.querySelectorAll('input, button, a[href]'), function (el) { return el.offsetParent !== null || el === document.activeElement; });
  }
  function buildTL() {
    TL = document.createElement('div');
    TL.id = 'mh-tl';
    TL.innerHTML = '<div class="bg" data-tlx="1"></div><div class="pn" role="dialog" aria-modal="true" aria-labelledby="mh-tl-t"><div class="hd">'
      + '<div class="tr"><h2 class="tt" id="mh-tl-t">All tools</h2><span class="n">' + tlTotal() + '</span>'
      + '<button type="button" class="x" data-tlx="1" aria-label="Close tools">' + icon('close') + '</button></div>'
      + '<div class="sr">' + icon('search') + '<input type="search" class="q" placeholder="Find a tool or desk" aria-label="Find a tool or desk" autocomplete="off"></div>'
      + '<div class="ch" role="group" aria-label="Filter by group"></div></div><div class="bd"></div></div>';
    var host = mount.closest ? mount.closest('.msh') : null;
    if (!host) { host = document.createElement('div'); host.className = 'msh'; document.body.appendChild(host); }
    host.appendChild(TL);
    TL.addEventListener('click', function (e) {
      var t = e.target.closest ? e.target.closest('[data-tlx],[data-tlg],[data-tlclear]') : null;
      if (!t) { return; }
      if (t.hasAttribute('data-tlx')) { closeTools(); return; }
      if (t.hasAttribute('data-tlclear')) { tlQ = ''; tlG = ''; TL.querySelector('input.q').value = ''; tlPaint(); TL.querySelector('input.q').focus(); return; }
      tlG = t.getAttribute('data-tlg') || '';
      tlPaint();
      var b = TL.querySelector('[data-tlg="' + tlG + '"]');
      if (b) { b.focus(); }
    });
    TL.querySelector('input.q').addEventListener('input', function (e) { tlQ = e.target.value; TL.querySelector('.bd').innerHTML = tlBody(); });
    TL.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' || e.key === 'Esc') { e.preventDefault(); closeTools(); return; }
      if (e.key === 'Enter' && e.target.classList.contains('q')) {
        var first = TL.querySelector('.bd a.ti');
        if (first) { e.preventDefault(); window.location.href = first.getAttribute('href'); }
        return;
      }
      if (e.key !== 'Tab') { return; }
      var f = tlFocusables();
      if (!f.length) { return; }
      var a = f[0], z = f[f.length - 1];
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
      else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
    });
  }
  function setExpanded(v) {
    Array.prototype.forEach.call(document.querySelectorAll('[data-act="tools"]'), function (b) { b.setAttribute('aria-expanded', v ? 'true' : 'false'); });
  }
  function openTools(from) {
    if (!CAT) { return; }
    if (!TL) { buildTL(); }
    tlFrom = from || document.activeElement;
    tlQ = ''; tlG = '';
    TL.querySelector('input.q').value = '';
    tlPaint();
    TL.className = 'open';
    TL.querySelector('.bd').scrollTop = 0;
    document.documentElement.style.overflow = 'hidden';
    setExpanded(true);
    setTimeout(function () { var i = TL.querySelector('input.q'); if (i) { i.focus(); } }, 30);
  }
  function closeTools() {
    if (!TL || TL.className !== 'open') { return; }
    TL.className = '';
    document.documentElement.style.overflow = '';
    setExpanded(false);
    if (tlFrom && tlFrom.focus && document.body.contains(tlFrom)) { tlFrom.focus(); }
  }

  function saveNote() {
    if (where === 'account') { return '<p class="mh-note">Saved to your account.</p>'; }
    if (where === 'device') { return '<p class="mh-note warn">Saved on this device only. Your account is unavailable just now.</p>'; }
    return '';
  }

  /* ---------- section bar: highlight the section in view ---------- */
  var spyOn = false;
  function spy() {
    if (spyOn) { return; }
    spyOn = true;
    var ticking = false;
    function run() {
      ticking = false;
      var links = mount.querySelectorAll('.mh-jumps a');
      if (!links.length) { return; }
      var cur = '';
      for (var i = 0; i < links.length; i++) {
        var el = document.getElementById(links[i].getAttribute('data-jump'));
        if (el && el.getBoundingClientRect().top < 140) { cur = links[i].getAttribute('data-jump'); }
      }
      for (var k = 0; k < links.length; k++) { links[k].className = links[k].getAttribute('data-jump') === cur ? 'on' : ''; }
    }
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; window.requestAnimationFrame(run); } }, { passive: true });
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('[data-jump]') : null;
    if (!t) { return; }
    var el = document.getElementById(t.getAttribute('data-jump'));
    if (!el) { return; }
    e.preventDefault();
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  /* ---------- choosing ---------- */
  function renderEdit() {
    var chosen = {};
    draft.forEach(function (id) { chosen[id] = 1; });
    var q = query.toLowerCase();
    var roles = CAT.roles || {};
    var ord = visible(draft);
    var h = '<div class="mh-in mh-edit"><div class="mh-edhead"><div><span class="mh-eyebrow">Customise My Hub</span><h2 class="mh-h2">Choose what’s on your page</h2>'
      + '<span class="sub">Specialities you tick also narrow news and dates.</span></div>'
      + '<div class="act"><span class="cnt"><b>' + ord.length + '</b>chosen</span><button type="button" class="mh-btn ghost" data-act="cancel">Cancel</button><button type="button" class="mh-btn" data-act="save">Save my page</button></div></div>'
      + '<div class="mh-edgrid"><div class="mh-card mh-cat"><div class="mh-tools">'
      + '<input type="search" id="mh-q" placeholder="Search Hub pages…" value="' + esc(query) + '" aria-label="Search Hub pages">'
      + '<select id="mh-role" aria-label="Add a starter set for my role"><option value="">Add a starter set for my role…</option>'
      + Object.keys(roles).map(function (k) { return '<option value="' + esc(k) + '">' + esc(roles[k].label) + '</option>'; }).join('')
      + '</select></div>';
    var any = false;
    (CAT.groups || []).forEach(function (g) {
      var rows = CAT.items.filter(function (it) { return it.group === g.id && (!q || it.label.toLowerCase().indexOf(q) !== -1); });
      if (!rows.length) { return; }
      any = true;
      var n = rows.filter(function (it) { return chosen[it.id]; }).length;
      var open = q ? true : (grpOpen.hasOwnProperty(g.id) ? grpOpen[g.id] : (n > 0 || g.id === 'specialities'));
      h += '<div class="mh-group' + (open ? ' open' : '') + '"><button type="button" class="mh-gh" data-grp="' + esc(g.id) + '" aria-expanded="' + (open ? 'true' : 'false') + '"><span class="cv" aria-hidden="true"></span>' + esc(g.label)
        + ' <em' + (n ? ' class="has"' : '') + '>' + n + ' of ' + rows.length + '</em></button><div class="mh-opts">'
        + rows.map(function (it) {
          return '<label' + (chosen[it.id] ? ' class="on"' : '') + '><input type="checkbox" data-id="' + esc(it.id) + '"' + (chosen[it.id] ? ' checked' : '') + '><span>' + esc(it.label) + (it.news ? ' <small>News</small>' : '') + '</span></label>';
        }).join('') + '</div></div>';
    });
    if (!any) { h += '<p class="mh-empty">No Hub page matches “' + esc(query) + '”.</p>'; }
    h += '</div><div class="mh-card mh-ord"><div class="hd"><h3>Your page, in order</h3>' + (ord.length ? '<button type="button" class="mh-link" data-act="clear">Clear all</button>' : '') + '</div>';
    if (ord.length) {
      h += '<ol class="mh-order">' + ord.map(function (id, i) {
        return '<li><span class="i">' + pad(i + 1) + '</span><span class="l">' + esc(BYID[id].label) + '</span>'
          + '<button type="button" data-mv="' + i + '" data-d="-1" aria-label="Move up"' + (i ? '' : ' disabled') + '>↑</button>'
          + '<button type="button" data-mv="' + i + '" data-d="1" aria-label="Move down"' + (i < ord.length - 1 ? '' : ' disabled') + '>↓</button>'
          + '<button type="button" data-rm="' + esc(id) + '" aria-label="Remove">✕</button></li>';
      }).join('') + '</ol>';
    } else {
      h += '<p class="none">Nothing chosen yet.</p>';
    }
    h += '<div class="ft"><button type="button" class="mh-btn" data-act="save">Save my page</button><button type="button" class="mh-btn ghost" data-act="cancel">Cancel</button></div></div></div></div>';
    mount.innerHTML = h;
    var qi = document.getElementById('mh-q');
    if (qi && query) { qi.focus(); qi.setSelectionRange(query.length, query.length); }
  }

  function startEdit() { draft = visible(pins).slice(); query = ''; grpOpen = {}; renderEdit(); mount.scrollIntoView({ behavior: 'smooth', block: 'start' }); }

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
    if (act === 'tools') { openTools(t); return; }
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
      t.parentNode.classList.toggle('open', !!openRows[k]);
      t.setAttribute('aria-expanded', openRows[k] ? 'true' : 'false');
      return;
    }
    if (t.hasAttribute('data-more')) {
      var p = t.getAttribute('data-more');
      openPanels[p] = !openPanels[p];
      paintSections();
      if (!openPanels[p]) {
        var back = document.getElementById(p === 'news' ? 'mh-news' : p === 'events' ? 'mh-events' : p === 'alerts' ? 'mh-alerts' : 'mh-proc');
        if (back && back.getBoundingClientRect().top < 0) { back.scrollIntoView({ block: 'start' }); }
      }
      return;
    }
    if (t.hasAttribute('data-grp')) {
      var gid = t.getAttribute('data-grp');
      var wasOpen = t.parentNode.className.indexOf('open') !== -1;
      grpOpen[gid] = !wasOpen;
      t.parentNode.classList.toggle('open', !wasOpen);
      t.setAttribute('aria-expanded', !wasOpen ? 'true' : 'false');
      return;
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
    var y = window.pageYOffset;
    renderEdit();
    window.scrollTo(0, y);
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

  function skeletonPage() {
    return '<div class="mh-in"><div class="mh-bar"><div class="mh-bar-in" style="height:54px;"><span class="sk" style="width:340px;max-width:50%;height:14px;margin-left:8px;"></span><span class="sk" style="width:220px;height:34px;border-radius:9px;"></span></div></div>'
      + '<div class="mh-sec"><div class="mh-sh"><span class="sk" style="width:180px;height:24px;"></span><span class="rule"></span></div>'
      + '<div class="mh-card mh-front"><div class="mh-fp"><div class="a-lead"><div class="mh-lead" style="min-height:320px;"><span class="sk dk" style="width:30%;height:10px;"></span><span class="sk dk" style="width:90%;height:26px;margin-top:10px;"></span><span class="sk dk" style="width:64%;height:26px;"></span></div></div>'
      + '<div class="a-s1">' + skRows(1) + '</div><div class="a-s2">' + skRows(1) + '</div><div class="a-list">' + skRows(4) + '</div></div></div></div></div>';
  }

  function start() {
    css();
    mount.innerHTML = skeletonPage();
    paintBrief();
    fetch(CAT_URL, { cache: 'no-cache' }).then(function (r) { return r.json(); }).then(function (cat) {
      CAT = cat;
      (cat.items || []).forEach(function (it) { BYID[it.id] = it; });
      if (!nonce()) {
        var b = document.getElementById('myh-brief');
        if (b) { b.innerHTML = ''; }
        mount.innerHTML = '<div class="mh-in"><div class="mh-blank" style="margin-top:10px;"><span class="ib">' + icon('pages') + '</span><h3>Log in to open your desk</h3><span class="t">News, alerts, dates and your pages.</span><a class="mh-btn" href="/login/">Log in</a></div></div>';
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
      mount.innerHTML = '<p class="mh-note warn">My Hub is unavailable just now. Try the <a href="/medical-sales-hub/" style="color:#14304F;text-decoration:underline;">Live Desk</a>.</p>';
    });
  }

  start();
})();
