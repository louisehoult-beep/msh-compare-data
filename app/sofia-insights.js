/* MSH-SOFIA desk. Loaded by the Analysts page into #msh-sofia. Reads data/sofia-insights.json and
   shows only items verified at source TODAY (London date). Anything older never appears. */
(function () {
  var host = document.getElementById('msh-sofia');
  if (!host || host.getAttribute('data-ready')) { return; }
  host.setAttribute('data-ready', '1');
  var RAW = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var AREAS = ['Device rules', 'How buyers decide', 'Supplier duties', 'Funding and access'];

  var css = '.msh-so{display:flex;flex-direction:column;gap:28px;min-width:0;font-family:Inter,-apple-system,"Segoe UI",system-ui,sans-serif;color:#0B1C33}' +
    '.msh-so [hidden]{display:none!important}' +
    '.msh-so .so-asof{margin:0;padding:12px 16px;border-left:4px solid #A8842C;background:#F5F1E8;border-radius:0 8px 8px 0;color:#26364B}' +
    '.msh-so .so-asof strong{color:#0B1C33}' +
    '.msh-so .so-filters{display:flex;flex-wrap:wrap;gap:8px}' +
    '.msh-so .so-filters button{min-height:44px;padding:0 18px;border-radius:99px;border:1px solid #0B1C33;background:#FFFFFF;color:#0B1C33;font:600 13.5px Inter,system-ui,sans-serif;cursor:pointer;text-transform:none;letter-spacing:0}' +
    '.msh-so .so-filters button[aria-pressed="true"]{background:#0B1C33;color:#EDE7DC}' +
    '.msh-so .so-filters button:focus-visible{outline:3px solid #A8842C;outline-offset:2px}' +
    '.msh-so .so-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:18px}' +
    '.msh-so .so-item{border:1px solid #E7E2D6;border-top:3px solid #A8842C;border-radius:10px;padding:18px 20px;display:flex;flex-direction:column;gap:10px;min-width:0;overflow-wrap:anywhere;background:#FFFFFF}' +
    '.msh-so .so-tags{margin:0;display:flex;flex-wrap:wrap;gap:8px;align-items:center;font:700 11.5px Jost,"Segoe UI",system-ui,sans-serif;letter-spacing:1.4px;text-transform:uppercase;color:#4F5B6B}' +
    '.msh-so .so-flag{padding:2px 10px;border-radius:99px;background:#6B2A34;color:#FFFFFF}' +
    '.msh-so .so-flag.soft{background:#F3E4E1;color:#5A302B}' +
    '.msh-so .so-t{margin:0;padding:0;font-family:"Cormorant Garamond",Georgia,serif;font-weight:600;font-size:23px;line-height:1.2;color:#0B1C33;text-transform:none;letter-spacing:0}' +
    '.msh-so .so-s{margin:0;color:#26364B}' +
    '.msh-so .so-mean{margin:0;padding:11px 14px;border-radius:8px;background:#F5F1E8;color:#0B1C33}' +
    '.msh-so .so-mean b{display:block;font:700 11px Jost,"Segoe UI",system-ui,sans-serif;letter-spacing:1.6px;text-transform:uppercase;color:#6B2A34;margin-bottom:3px}' +
    '.msh-so .so-src{margin:auto 0 0;font-size:12.5px;color:#4F5B6B;line-height:1.7}' +
    '.msh-so .so-src a{color:#1B3A5F;text-decoration:underline;text-underline-offset:2px}' +
    '.msh-so .so-foot{margin:0;font-size:12.5px;color:#4F5B6B;max-width:90ch}';

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) { e.className = cls; }
    if (text) { e.textContent = text; }
    return e;
  }
  function londonToday() {
    return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/London', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
  }
  function longDate(iso, weekday) {
    var o = { timeZone: 'UTC', day: 'numeric', month: 'long', year: 'numeric' };
    if (weekday) { o.weekday = 'long'; }
    return new Intl.DateTimeFormat('en-GB', o).format(new Date(iso + 'T12:00:00Z')).replace(',', '');
  }
  function safeUrl(u) { return /^https:\/\//.test(u) ? u : '#'; }

  function card(i, today) {
    var c = el('article', 'so-item');
    c.setAttribute('data-area', i.area);
    var tags = el('p', 'so-tags');
    if (i.date === today) { tags.appendChild(el('span', 'so-flag', 'New today')); }
    if (i.type === 'standing' && i.deadline) {
      var passed = i.deadline < today;
      tags.appendChild(el('span', passed ? 'so-flag soft' : 'so-flag', (passed ? 'Date passed: ' : i.deadlineLabel + ': ') + longDate(i.deadline)));
    }
    tags.appendChild(el('span', '', i.area));
    if (i.date) { tags.appendChild(el('span', '', (i.type !== 'new' ? 'Dated ' : i.earlier ? 'Updated ' : 'Published ') + longDate(i.date))); }
    c.appendChild(tags);
    c.appendChild(el('h4', 'so-t', i.title));
    c.appendChild(el('p', 'so-s', i.quoted ? 'In the publisher’s words: “' + i.summary + '”' : i.summary));
    var m = el('p', 'so-mean');
    m.appendChild(el('b', '', 'What it means for sales'));
    m.appendChild(document.createTextNode(i.meaning));
    c.appendChild(m);
    var src = el('p', 'so-src');
    if (i.earlier && i.earlier.length) {
      src.appendChild(document.createTextNode('Also updated: ' + i.earlier.map(function (d) { return longDate(d); }).join(', ') + '.'));
      src.appendChild(el('br'));
    }
    src.appendChild(document.createTextNode((i.sources.length > 1 ? 'Sources: ' : 'Source: ')));
    i.sources.forEach(function (s, n) {
      if (n) { src.appendChild(document.createTextNode(' · ')); }
      var a = el('a', '', s.name);
      a.href = safeUrl(s.url);
      a.target = '_blank';
      a.rel = 'noopener';
      src.appendChild(a);
    });
    src.appendChild(document.createTextNode('. Checked ' + longDate(i.verifiedOn) + '.'));
    c.appendChild(src);
    return c;
  }

  function section(title, lede) {
    var s = el('section', 'an-sec');
    s.appendChild(el('h3', 'an-h', title));
    if (lede) { s.appendChild(el('p', 'an-lede', lede)); }
    return s;
  }
  function note(text) { host.appendChild(el('p', 'an-note', text)); }

  function render(data) {
    var today = londonToday();
    var items = (data.items || []).filter(function (i) { return i.verifiedOn === today && i.meaning && i.sources && i.sources.length; });
    if (data.dataAsOf !== today || !items.length) {
      note('Today’s source checks have not finished, so nothing is shown. Items appear only once they have been checked today.' +
        (data.dataAsOf ? ' Last completed check: ' + longDate(data.dataAsOf, true) + '.' : ''));
      return;
    }
    var style = el('style');
    style.textContent = css;
    host.appendChild(style);
    var wrap = el('div', 'msh-so');
    host.appendChild(wrap);

    var asof = el('p', 'so-asof');
    asof.appendChild(el('strong', '', 'Data as of ' + longDate(data.dataAsOf, true) + '. '));
    asof.appendChild(document.createTextNode('Each item was checked against its official source at ' + data.checkedAt + ' today.'));
    wrap.appendChild(asof);

    var filters = el('div', 'so-filters');
    filters.setAttribute('role', 'group');
    filters.setAttribute('aria-label', 'Show one subject');
    wrap.appendChild(filters);

    var fresh = items.filter(function (i) { return i.type === 'new'; }).sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    var anyToday = fresh.some(function (i) { return i.date === today; });
    var s1 = section('New changes', anyToday ? 'Today’s changes first, then the rest of the last ' + data.windowDays + ' days.' :
      'No new changes published today. These are the changes from the last ' + data.windowDays + ' days.');
    var g1 = el('div', 'so-grid');
    fresh.forEach(function (i) { g1.appendChild(card(i, today)); });
    s1.appendChild(g1);
    var none1 = el('p', 'an-note', 'No changes in this subject in the last ' + data.windowDays + ' days.');
    s1.appendChild(none1);
    wrap.appendChild(s1);

    function rank(i) { return i.deadline && i.deadline >= today ? '0' + i.deadline : '1' + String(99999999 - Number((i.date || '2000-01-01').replace(/-/g, ''))); }
    var rules = items.filter(function (i) { return i.type === 'standing'; }).sort(function (a, b) { return rank(a) < rank(b) ? -1 : 1; });
    var s2 = section('Rules and dates to know', 'In force or coming. The nearest dates are first.');
    var g2 = el('div', 'so-grid');
    rules.forEach(function (i) { g2.appendChild(card(i, today)); });
    s2.appendChild(g2);
    var none2 = el('p', 'an-note', 'Nothing in this subject today.');
    s2.appendChild(none2);
    wrap.appendChild(s2);

    wrap.appendChild(el('p', 'so-foot', 'MHRA is the Medicines and Healthcare products Regulatory Agency. PPN is a Procurement Policy Note. This page is information from public sources, not legal, regulatory or commercial advice. Speciality news is with Marcus, tenders with Helen and digital assurance with Grace.'));

    function show(area) {
      [g1, g2].forEach(function (g, n) {
        var seen = 0;
        Array.prototype.forEach.call(g.children, function (c) {
          var on = !area || c.getAttribute('data-area') === area;
          c.hidden = !on;
          if (on) { seen += 1; }
        });
        (n ? none2 : none1).hidden = seen > 0;
      });
      Array.prototype.forEach.call(filters.children, function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-f') === area)); });
    }
    [''].concat(AREAS).forEach(function (a) {
      var b = el('button', '', a || 'Everything');
      b.type = 'button';
      b.setAttribute('data-f', a);
      b.addEventListener('click', function () { show(a); });
      filters.appendChild(b);
    });
    show('');
  }

  window.fetch(RAW + 'data/sofia-insights.json?cb=' + londonToday() + '-' + new Date().getUTCHours(), { cache: 'no-cache' }).then(function (r) {
    if (!r.ok) { throw new Error(String(r.status)); }
    return r.json();
  }).then(render).catch(function () {
    note('Sofia’s insights could not load just now. Please try again shortly.');
  });
})();
