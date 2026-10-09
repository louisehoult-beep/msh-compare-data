/* app/careers-roles.js — Supplier job listings on the Career Centre (Hub page 679).
 *
 * Lou, 28/09/2026: "the careers page should use the job listings please. And there
 * is no max, they just need to be in the right categories or job titles."
 *
 * Reads data/supplier-careers.json (UK roles read from each supplier's own careers
 * site, one role per URL) and config/careers-relevant-roles.json (the one list of
 * relevant categories and title patterns). A role is listed when its title matches
 * a category and no exclude pattern. No maximum, no minimum supplier base.
 *
 * classify() here must agree with scripts/careers_relevance.py. test_careers_relevance.py
 * runs both over the same real titles, so a change to one that the other does not
 * share fails the test.
 *
 * The page carries a mount <div data-careers-roles> and a small loader that fetches
 * and evals this file, the same pattern as app/speciality-news.js. Additive only: if
 * anything fails the mount says so plainly and the rest of the page is untouched.
 */
(function (root) {
  'use strict';

  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var NOT_PORTABLE = /\(\?P|\(\?<[=!]|\(\?[aiLmsux]|\\[AZz]/;
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  function re(p) {
    if (NOT_PORTABLE.test(p)) { throw new Error('non-portable pattern ' + p); }
    return new RegExp(p, 'i');
  }

  function compile(cfg) {
    if (!cfg || !cfg.categories || !cfg.categories.length) { throw new Error('config has no categories'); }
    return {
      exclude: (cfg.exclude || []).map(re),
      categories: cfg.categories.map(function (c) {
        return { key: c.key, label: c.label, patterns: c.patterns.map(re) };
      })
    };
  }

  function hit(list, t) {
    for (var i = 0; i < list.length; i++) { if (list[i].test(t)) { return true; } }
    return false;
  }

  function classify(title, compiled) {
    var t = title || '';
    if (hit(compiled.exclude, t)) { return null; }
    for (var i = 0; i < compiled.categories.length; i++) {
      if (hit(compiled.categories[i].patterns, t)) { return compiled.categories[i].key; }
    }
    return null;
  }

  function relevantRoles(doc, compiled) {
    var out = [];
    (doc.suppliers || []).forEach(function (s) {
      (s.roles || []).forEach(function (r) {
        if (r.uk !== true || !r.url) { return; }
        var cat = classify(r.title, compiled);
        if (cat) {
          out.push({ supplier: s.name, category: cat, checkedOn: s.checkedOn,
                     title: r.title, location: r.location || '', url: r.url });
        }
      });
    });
    return out;
  }

  function fmtDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
    if (!m) { return ''; }
    return parseInt(m[3], 10) + ' ' + MONTHS[parseInt(m[2], 10) - 1] + ' ' + m[1];
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) { e.className = cls; }
    if (text != null) { e.textContent = text; }
    return e;
  }

  function safeUrl(u) {
    return /^https:\/\//i.test(u || '') ? u : null;
  }

  function render(mount, doc, cfg) {
    var compiled = compile(cfg);
    var roles = relevantRoles(doc, compiled);
    var labels = {}, order = {};
    compiled.categories.forEach(function (c, i) { labels[c.key] = c.label; order[c.key] = i; });
    roles.sort(function (a, b) {
      return (order[a.category] - order[b.category]) || a.title.localeCompare(b.title);
    });

    var suppliers = {}, dates = [];
    roles.forEach(function (r) { suppliers[r.supplier] = 1; if (r.checkedOn) { dates.push(r.checkedOn); } });
    var nSup = Object.keys(suppliers).length;
    dates.sort();
    var counts = doc.counts || {};

    mount.textContent = '';
    var sum = el('p', 'crj-sum');
    if (roles.length) {
      var when = dates.length ? fmtDate(dates[0]) : '';
      if (dates.length && dates[0] !== dates[dates.length - 1]) {
        when = fmtDate(dates[0]) + ' to ' + fmtDate(dates[dates.length - 1]);
      }
      sum.appendChild(el('b', null, String(roles.length)));
      sum.appendChild(document.createTextNode(' matching role' + (roles.length === 1 ? '' : 's') + ' from '));
      sum.appendChild(el('b', null, String(nSup)));
      sum.appendChild(document.createTextNode(' supplier' + (nSup === 1 ? '' : 's') + (when ? ', checked ' + when : '') + '.'));
    } else {
      sum.appendChild(el('b', null, 'No matching roles right now.'));
    }
    mount.appendChild(sum);

    var ctx = el('p', 'crj-ctx');
    ctx.textContent = 'Read from the careers sites of ' + (counts.withRoleCount != null ? counts.withRoleCount : '?') +
      ' suppliers whose vacancies can be read role by role, out of ' +
      (counts.withCareersPage != null ? counts.withCareersPage : '?') +
      ' supplier careers pages found so far. UK roles only, in the sales and commercial categories below. ' +
      'A role may have closed since its check date; the link opens the company’s own posting.';
    mount.appendChild(ctx);

    if (!roles.length) {
      mount.appendChild(el('p', 'crj-empty',
        'None of the supplier careers sites checked lists a UK role in these categories at the moment. ' +
        'The recruiter directory and live job sources further down this page cover the wider market.'));
      return;
    }

    var catCount = {};
    roles.forEach(function (r) { catCount[r.category] = (catCount[r.category] || 0) + 1; });
    var chips = el('div', 'crj-chips');
    chips.setAttribute('role', 'group');
    chips.setAttribute('aria-label', 'Filter by role category');
    var list = el('ul', 'crj-list');
    var active = 'all';

    function chip(key, text) {
      var b = el('button', 'crj-chip', text);
      b.type = 'button';
      b.setAttribute('data-k', key);
      b.setAttribute('aria-pressed', key === active ? 'true' : 'false');
      b.addEventListener('click', function () {
        active = key;
        Array.prototype.forEach.call(chips.children, function (c) {
          c.setAttribute('aria-pressed', c.getAttribute('data-k') === active ? 'true' : 'false');
        });
        draw();
      });
      chips.appendChild(b);
    }
    chip('all', 'All (' + roles.length + ')');
    compiled.categories.forEach(function (c) {
      if (catCount[c.key]) { chip(c.key, c.label + ' (' + catCount[c.key] + ')'); }
    });
    mount.appendChild(chips);
    mount.appendChild(list);

    function draw() {
      list.textContent = '';
      roles.forEach(function (r) {
        if (active !== 'all' && r.category !== active) { return; }
        var li = el('li', 'crj-row');
        var u = safeUrl(r.url);
        var t = el(u ? 'a' : 'span', 'crj-t', r.title);
        if (u) { t.href = u; t.target = '_blank'; t.rel = 'noopener'; }
        li.appendChild(t);
        var meta = el('div', 'crj-m');
        meta.appendChild(el('span', 'crj-sup', r.supplier));
        if (r.location) { meta.appendChild(el('span', 'crj-loc', r.location)); }
        if (r.checkedOn) { meta.appendChild(el('span', 'crj-chk', 'Checked ' + fmtDate(r.checkedOn))); }
        li.appendChild(meta);
        li.appendChild(el('span', 'crj-cat', labels[r.category]));
        list.appendChild(li);
      });
    }
    draw();

    // One careers site serving several supplier records: the roles are listed once,
    // under the record the data holds them against. Name the others, from the data.
    var shared = {};
    (doc.suppliers || []).forEach(function (s) {
      if (s.rolesAttributedTo && suppliers[s.rolesAttributedTo]) {
        (shared[s.rolesAttributedTo] = shared[s.rolesAttributedTo] || []).push(s.name);
      }
    });
    Object.keys(shared).forEach(function (holder) {
      mount.appendChild(el('p', 'crj-note', holder + '’s roles are listed once. The same careers site also serves ' +
        shared[holder].sort().join(', ') + '.'));
    });
  }

  function start(mount) {
    mount.setAttribute('data-ready', '1');
    var cb = '?cb=' + new Date().toISOString().slice(0, 13);
    function get(p) {
      return fetch(BASE + p + cb).then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.json();
      });
    }
    Promise.all([get('data/supplier-careers.json'), get('config/careers-relevant-roles.json')])
      .then(function (x) { render(mount, x[0], x[1]); })
      .catch(function () {
        mount.textContent = '';
        mount.appendChild(el('p', 'crj-empty',
          'The supplier job listings could not be loaded just now. Nothing is shown rather than an out-of-date list; please try again shortly.'));
      });
  }

  var api = { compile: compile, classify: classify, relevantRoles: relevantRoles };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  root.MSHCareersRoles = api;
  if (typeof document !== 'undefined') {
    var m = document.querySelector('[data-careers-roles]');
    if (m && !m.getAttribute('data-ready')) { start(m); }
  }
})(typeof window !== 'undefined' ? window : globalThis);
