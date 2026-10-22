/* My Hub logic: the pure functions behind the home screen (2026-10).
   No DOM, no fetch, no clock: every function takes "today" or "now" as an
   argument, so test_my_hub_logic.py can run each one under node with fixed
   inputs. app/my-hub.js and app/my-hub-feeds.js call these; the feed rules
   below are the ones My Hub has used since 24/09/2026, moved here unchanged
   apart from taking their inputs as arguments.

   Loaded with new Function() by app/my-hub.js; require()-able under node. */
(function (root) {
  'use strict';
  if (root.MSH_MYHUB_LOGIC && typeof module === 'undefined') { return; }

  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  /* ---------- dates: ISO in, UK out, local calendar days ---------- */
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function isoDay(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function parseDay(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || '');
    return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
  }
  function addDays(s, n) { var d = parseDay(s); d.setDate(d.getDate() + n); return isoDay(d); }
  function fmtDate(s) { var d = parseDay(s); return d ? d.getDate() + ' ' + MONTHS[d.getMonth()] + ' ' + d.getFullYear() : ''; }
  function fmtShort(s) { var d = parseDay(s); return d ? d.getDate() + ' ' + MONTHS[d.getMonth()] : ''; }
  function daysFrom(s, today) {
    var d = parseDay(s), t = parseDay(today);
    if (!d) { return null; }
    if (!t) { return null; }
    return Math.round((d - t) / 86400000);
  }
  function whenLabel(s, today) {
    var n = daysFrom(s, today);
    if (n === null) { return ''; }
    if (n === 0) { return 'Today'; }
    if (n === 1) { return 'Tomorrow'; }
    if (n === -1) { return 'Yesterday'; }
    if (n > 1) { return 'In ' + n + ' days'; }
    return (-n) + ' days ago';
  }
  /* News timestamps carry a time and an offset: "Today, 11:00", "Yesterday",
     or the date, in the reader's own day. */
  function newsStamp(s, today) {
    var d = s ? new Date(s) : null;
    if (!d || isNaN(d)) { return { day: '', label: '' }; }
    var day = isoDay(d), hasTime = /T\d{2}:\d{2}/.test(s);
    if (day === today) { return { day: day, label: 'Today' + (hasTime ? ', ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) : '') }; }
    if (day === addDays(today, -1)) { return { day: day, label: 'Yesterday' }; }
    return { day: day, label: fmtShort(day) + (day.slice(0, 4) === today.slice(0, 4) ? '' : ' ' + day.slice(0, 4)) };
  }
  function money(v) {
    if (typeof v !== 'number' || !isFinite(v)) { return ''; }
    if (v >= 1e6) { return '\u00a3' + (Math.round(v / 1e5) / 10) + 'm'; }
    if (v >= 1e3) { return '\u00a3' + Math.round(v / 1e3) + 'k'; }
    return '\u00a3' + Math.round(v);
  }

  /* ---------- feeds ---------- */
  /* Job adverts ride in on some society feeds; they are jobs, not news
     (Lou, 24/09/2026). The builder tags them kind:"job". */
  function isJob(it) { return it.kind === 'job' || /^\s*(job advert|vacancy)\b/i.test(String(it.title || '')); }
  /* End a feed summary on its last full sentence, or the last whole word and
     an ellipsis; a summary that already ends properly is left alone. */
  function tidy(s) {
    s = String(s || '').replace(/\s*The post .{0,200}? appeared first on .*$/i, '').replace(/\s*(\[(\u2026|\.\.\.)\]|\[\s*\]|\u2026)\s*$/, '').trim();
    if (!s || /[.!?\u201d"\u2019')\]]$/.test(s)) { return s; }
    var dot = Math.max(s.lastIndexOf('. '), s.lastIndexOf('? '), s.lastIndexOf('! '));
    if (dot >= 80) { return s.slice(0, dot + 1); }
    var sp = s.lastIndexOf(' ');
    return (sp > 40 ? s.slice(0, sp) : s).replace(/[\s,;:\u2013-]+$/, '') + '\u2026';
  }
  /* One story syndicated under two links is one story. Future-dated items
     (event listings) sort after everything already published. */
  function dedupeNews(got, nowIso) {
    var seen = {};
    var out = got.filter(function (g) {
      var k = String(g.it.title).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
      if (seen[g.it.link] || seen[k]) { return false; }
      seen[g.it.link] = 1; seen[k] = 1; return true;
    });
    out.sort(function (a, b) {
      var fa = String(a.it.published || '') > nowIso ? 1 : 0, fb = String(b.it.published || '') > nowIso ? 1 : 0;
      if (fa !== fb) { return fa - fb; }
      var c = String(b.it.published || '').localeCompare(String(a.it.published || ''));
      return c || (b.it.opportunity ? 1 : 0) - (a.it.opportunity ? 1 : 0);
    });
    return out;
  }
  function inScope(specs, mine, narrowed) {
    if (!narrowed) { return true; }
    return (specs || []).some(function (s) { return !!mine[s]; });
  }
  /* At most two stories per speciality above "Show all", so one busy feed
     cannot fill the top; nothing is dropped, the rest follow in date order. */
  function spread(list, top, nowIso) {
    var head = [], rest = [], per = {};
    list.forEach(function (g) {
      var n = per[g.spec] || 0;
      if (head.length < top) {
        if (n < 2) { head.push(g); per[g.spec] = n + 1; return; }
      }
      rest.push(g);
    });
    while (head.length < top) {
      if (!rest.length) { break; }
      head.push(rest.shift());
    }
    head.sort(function (a, b) {
      var fa = String(a.it.published || '') > nowIso ? 1 : 0, fb = String(b.it.published || '') > nowIso ? 1 : 0;
      return (fa - fb) || String(b.it.published || '').localeCompare(String(a.it.published || ''));
    });
    return head.concat(rest);
  }
  /* Each list function returns null while loading, false if the feed failed,
     else an array, exactly as the feed itself does. */
  function newsList(feed, mine, narrowed, top, nowIso) {
    if (!feed) { return feed; }
    return spread(feed.filter(function (g) { return !isJob(g.it) ? inScope([g.spec], mine, narrowed) : false; }), top, nowIso);
  }
  function jobsList(feed, mine, narrowed) {
    if (!feed) { return feed; }
    return feed.filter(function (g) { return isJob(g.it) ? inScope([g.spec], mine, narrowed) : false; });
  }
  function eventsList(cal, mine, narrowed, today, days) {
    if (!cal) { return cal; }
    var end = addDays(today, days);
    return cal.filter(function (e) {
      if (e.type !== 'event') { if (e.type !== 'awareness') { return false; } }
      if ((e.endDate || e.date) < today) { return false; }
      if (e.date > end) { return false; }
      return inScope(e.specialities, mine, narrowed);
    }).sort(function (a, b) { return String(a.date).localeCompare(String(b.date)); });
  }
  var PROC = {
    'framework-start': ['fw', 'Framework starts'],
    'framework-end': ['fw', 'Framework ends'],
    'contract-expiry': ['ct', 'Contract ends'],
    'action-deadline': ['ct', 'Deadline']
  };
  function procList(cal, mine, narrowed, today, days) {
    if (!cal) { return cal; }
    var end = addDays(today, days);
    return cal.filter(function (e) {
      if (!PROC[e.type]) { return false; }
      if (e.date < today) { return false; }
      if (e.date > end) { return false; }
      return inScope(e.specialities, mine, narrowed);
    }).sort(function (a, b) { return String(a.date).localeCompare(String(b.date)); });
  }

  /* ---------- What's new ---------- */
  /* Entries the member has not marked seen, dated within the last
     `windowDays` (so a new member is not greeted by a year of changes),
     never future-dated, newest first. */
  function whatsNewUnseen(entries, seen, today, windowDays) {
    var s = {};
    (seen || []).forEach(function (id) { s[id] = 1; });
    var from = addDays(today, -windowDays);
    return (entries || []).filter(function (e) {
      if (!e) { return false; }
      if (!e.id) { return false; }
      if (s[e.id]) { return false; }
      return String(e.date) >= from ? String(e.date) <= today : false;
    }).sort(function (a, b) { return String(b.date).localeCompare(String(a.date)) || String(a.id).localeCompare(String(b.id)); });
  }
  /* Box or pill (ruling F10). Minimise is remembered in the browser as the
     newest unseen id: the full box opens only on the first visit after a new
     entry; once minimised the pill shows until a newer entry arrives. */
  function whatsNewMode(unseen, minimisedId) {
    if (!unseen || !unseen.length) { return 'none'; }
    return unseen[0].id === minimisedId ? 'pill' : 'box';
  }
  /* The My Hub controls that carry a "new" dot: the showMe target of an
     unseen entry, when it is a control rather than a page path. */
  function dotTargets(unseen) {
    var o = {};
    unseen.forEach(function (e) {
      if (e.showMe) { if (e.showMe.charAt(0) !== '/') { o[e.showMe] = 1; } }
    });
    return o;
  }
  function idsForTarget(unseen, target) {
    return unseen.filter(function (e) { return e.showMe === target; }).map(function (e) { return e.id; });
  }

  /* ---------- getting-started checklist (five steps, spec item 5) ---------- */
  var STEPS = [
    ['profile', 'Choose your profile'],
    ['spec', 'Pick specialities'],
    ['brief', 'Weekly briefing'],
    ['phone', 'Add to Home Screen'],
    ['tour', 'Take the tour']
  ];
  function checklist(s) {
    var done = {
      profile: !!s.route,
      spec: s.specCount > 0,
      brief: !!s.briefing,
      phone: s.phone ? true : !!s.standalone,
      tour: !!s.tour
    };
    var sub = {
      profile: s.route ? (s.routeName || 'Chosen') : 'Sets your nav',
      spec: s.specCount ? s.specCount + ' chosen' : 'Sets your news',
      brief: s.briefing ? 'On the list' : 'Coming soon',
      phone: 'One tap on your phone',
      tour: 'Nine quick stops'
    };
    var steps = STEPS.map(function (p) { return { key: p[0], label: p[1], sub: sub[p[0]], done: done[p[0]] }; });
    var n = steps.filter(function (x) { return x.done; }).length;
    return { steps: steps, done: n, total: steps.length, complete: n === steps.length };
  }

  /* ---------- words ---------- */
  function greeting(h) { return h < 12 ? 'Good morning' : (h < 18 ? 'Good afternoon' : 'Good evening'); }
  function joinNames(names) {
    if (!names.length) { return ''; }
    if (names.length === 1) { return names[0]; }
    return names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1];
  }
  function specShort(labels) {
    if (!labels.length) { return 'None chosen'; }
    return String(labels[0]).split(/ and |,/)[0] + (labels.length > 1 ? ' +' + (labels.length - 1) : '');
  }

  /* ---------- Clinical Evidence Library (page 3791 reads one #band-id) ---------- */
  var LIB = '/medical-sales-hub/clinical-evidence-library/';
  function libraryTargets(specIds, byId, narrowed) {
    var all = [{ label: 'All specialities', url: LIB }];
    if (!narrowed) { return all; }
    var out = [];
    specIds.forEach(function (id) {
      var it = byId[id];
      if (it) { if (it.libraryBand) { out.push({ label: it.label, url: LIB + '#' + it.libraryBand }); } }
    });
    return out.length ? out : all;
  }

  /* ---------- picker: browse by profile (Lou, 01/10/2026) ---------- */
  /* Specialities are reached from every profile through Find Your
     Speciality, so they show under every profile chip. */
  function byProfile(items, profile) {
    if (!profile || profile === 'all') { return items.slice(); }
    return items.filter(function (it) {
      if (it.group === 'specialities') { return true; }
      return (it.profiles || []).indexOf(profile) !== -1;
    });
  }

  /* A URL from a third-party feed is only ever used as an href if it is http(s)
     or root-relative. javascript:, data:, protocol-relative (//host) and
     backslash tricks (/\host) all become '#'. */
  function safeUrl(u) {
    var s = typeof u === 'string' ? u : '';
    if (/^https?:\/\/\S/i.test(s)) { return s; }
    if (/^\/(?![\/\\])/.test(s)) { return s; }
    return '#';
  }

  /* The tools launcher list (Lou, 01/10/2026). Not narrowed, or no specialities
     picked: every item. Narrowed: items with no `specialities` (general) plus
     items whose `specialities` meet `mine` (an object keyed by speciality id).
     Input order kept, inputs untouched. */
  function toolsFor(items, mine, narrowed) {
    var list = Array.isArray(items) ? items : [];
    var m = mine || {};
    var any = Object.keys(m).length > 0;
    if (!narrowed || !any) { return list.slice(); }
    return list.filter(function (it) {
      var sp = it && it.specialities;
      if (!Array.isArray(sp) || !sp.length) { return true; }
      return sp.some(function (id) { return Object.prototype.hasOwnProperty.call(m, id); });
    });
  }

  /* ---------- the snapshot (22/10/2026) ---------- */
  var LONG_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  function periodLabel(p) {
    var m = /^(\d{4})(\d{2})$/.exec(String(p || ''));
    return m && +m[2] >= 1 && +m[2] <= 12 ? LONG_MONTHS[+m[2] - 1] + ' ' + m[1] : '';
  }
  /* Headline figures for each prescribing market a speciality file defines
     (data/speciality-panels/<slug>.json, gpPrescribing). Null when the
     speciality has no defined market. Nothing is computed here: every number
     is the file's own. */
  function marketHeadlines(panels) {
    var gp = panels ? panels.gpPrescribing : null;
    if (!gp || !gp.defined) { return null; }
    var ms = (gp.markets || []).filter(function (m) { return m && m.items !== undefined && m.items !== null && periodLabel(m.latestPeriod); }).map(function (m) {
      var t = (m.topNational || [])[0];
      return {
        id: m.id, label: m.label, short: String(m.label || '').split(':')[0], period: periodLabel(m.latestPeriod),
        items: m.items, cost: m.cost, itemsYoY: m.itemsYoY === undefined ? null : m.itemsYoY,
        lead: t ? { label: t.label, share: t.share === undefined ? null : t.share, yoy: t.yoy === undefined ? null : t.yoy } : null
      };
    });
    if (!ms.length) { return null; }
    return { markets: ms, source: gp.source || '', sourceUrl: gp.sourceUrl || '', attribution: gp.attribution || '', scope: gp.scope || '' };
  }
  /* ICB changes from data/icb-watch.json. Structure is national, so the facts
     line is the same for every speciality; an event is marked "relevant" only
     when its own text names one of the speciality's terms. Terms come from
     TERMS, else the speciality's label, never a guess. */
  var TERMS = { dermatology: ['dermatolog', 'skin', 'emollient', 'eczema', 'psoria', 'acne'] };
  function termsFor(specs) {
    var out = [];
    (specs || []).forEach(function (s) {
      var t = TERMS[s.id] || [String(s.label || '').toLowerCase()];
      t.forEach(function (x) { if (x && out.indexOf(x) === -1) { out.push(x); } });
    });
    return out;
  }
  function icbChanges(watch, specs, today, days) {
    if (!watch || !Array.isArray(watch.events)) { return null; }
    var from = addDays(today, -days), terms = termsFor(specs);
    var ev = watch.events.filter(function (e) { return e && e.headline && e.date >= from && e.date <= today; }).map(function (e) {
      var txt = (String(e.headline) + ' ' + String(e.detail || '')).toLowerCase();
      return { id: e.id, date: e.date, kind: e.kind, headline: e.headline, sources: e.sources || [], relevant: terms.some(function (t) { return txt.indexOf(t) !== -1; }) };
    });
    ev.sort(function (a, b) {
      return (b.relevant ? 1 : 0) - (a.relevant ? 1 : 0) || (a.kind === 'curated' ? 0 : 1) - (b.kind === 'curated' ? 0 : 1) || String(b.date).localeCompare(String(a.date));
    });
    var ends = (watch.abolished || []).map(function (a) { return a.legalEnd; }).filter(Boolean).sort();
    return {
      asOf: watch.asOf || '', count: watch.count === undefined ? null : watch.count, abolished: (watch.abolished || []).length,
      lastAbolished: ends.length ? ends[ends.length - 1] : '', clusters: (watch.clusters || []).length, events: ev, windowDays: days
    };
  }

  var api = {
    periodLabel: periodLabel, marketHeadlines: marketHeadlines, icbChanges: icbChanges, termsFor: termsFor,
    safeUrl: safeUrl, toolsFor: toolsFor,
    MONTHS: MONTHS, PROC: PROC, pad: pad, isoDay: isoDay, parseDay: parseDay, addDays: addDays,
    fmtDate: fmtDate, fmtShort: fmtShort, daysFrom: daysFrom, whenLabel: whenLabel,
    newsStamp: newsStamp, money: money, isJob: isJob, tidy: tidy, dedupeNews: dedupeNews,
    inScope: inScope, spread: spread, newsList: newsList, jobsList: jobsList,
    eventsList: eventsList, procList: procList, whatsNewUnseen: whatsNewUnseen, whatsNewMode: whatsNewMode,
    dotTargets: dotTargets, idsForTarget: idsForTarget, checklist: checklist,
    greeting: greeting, joinNames: joinNames, specShort: specShort,
    libraryTargets: libraryTargets, byProfile: byProfile
  };
  if (typeof module === 'object') { if (module) { if (module.exports) { module.exports = api; } } }
  root.MSH_MYHUB_LOGIC = api;
})(typeof window !== 'undefined' ? window : globalThis);
