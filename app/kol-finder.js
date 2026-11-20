/* Medical Sales Intelligence Hub: "Key Opinion Leader (KOL) finder" on Build Your Network
   (page 1882). Added 22/10/2026. Git-served, same pattern as npm-finder.js: the Hub
   page carries only a mount (<div id="msh-kolfinder">) and a fetch + new Function
   loader. Edit here, never in wp-admin.

   Data: data/kol-finder.json, written by scripts/build_kol_finder.py and gated by
   scripts/check_kol_finder.py. Every person carries the public page they were read
   from and the date it was checked. No contact details are held; LinkedIn is a search
   link only. A speciality or class with no checked people shows an honest empty state.

   The speciality filter uses the canonical speciality ids (data/speciality-map.json).
   It starts from ?speciality=<id>, then from the member's My Hub speciality when they
   are signed in, then from the first speciality that has people. window.mshKol.forSpecialities(ids)
   returns the people for a list of ids, for My Hub to use later.

   Loaded with new Function(); require()-able under node, where only the pure functions
   (_pure) are exercised: test_kol_finder.py. */
(function (root) {
  'use strict';

  var MOUNT_ID = 'msh-kolfinder';
  var SRC = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/kol-finder.json';

  /* ---------- pure ---------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function ukDate(iso) {
    if (!iso) { return ''; }
    var p = String(iso).slice(0, 10).split('-');
    return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : esc(iso);
  }
  /* spec: '' = every speciality; '@group' = the list in f.group (a company desk's own specialities). */
  function inSpeciality(p, spec, group) {
    if (!spec) { return true; }
    if (spec === '@group') { return (group || []).some(function (g) { return p.specialities.indexOf(g) !== -1; }); }
    return p.specialities.indexOf(spec) !== -1;
  }
  /* Where: trust code, ICB code or region name; hospital narrows inside a trust. */
  function inPlace(p, f) {
    if (f.region && p.region !== f.region) { return false; }
    if (f.icb && p.icb !== f.icb) { return false; }
    if (f.trust && p.trustCode !== f.trust) { return false; }
    if (f.hosp && p.hospital !== f.hosp) { return false; }
    return true;
  }
  function inClass(p, cls) {
    if (!cls) { return true; }
    if (cls === '@kol') { return !!p.kol; }
    return p.classes.indexOf(cls) !== -1;
  }
  function filter(people, f) {
    var q = String(f.q || '').toLowerCase().trim();
    return people.filter(function (p) {
      if (!inSpeciality(p, f.spec, f.group)) { return false; }
      if (!inPlace(p, f)) { return false; }
      if (!inClass(p, f.cls)) { return false; }
      if (f.body && p.bodies.indexOf(f.body) === -1) { return false; }
      if (q) {
        var hay = (p.name + ' ' + [p.job_title, p.trust, p.trustName, p.hospital, p.icbName].join(' ') + ' '
          + p.appearances.map(function (a) { return a.role + ' ' + (a.organisation || ''); }).join(' ')).toLowerCase();
        if (hay.indexOf(q) === -1) { return false; }
      }
      return true;
    });
  }
  function counts(people, spec, f) {
    var c = { all: 0, '@kol': 0 };
    f = f || {};
    people.forEach(function (p) {
      if (!inSpeciality(p, spec, f.group) || !inPlace(p, f)) { return; }
      c.all++;
      if (p.kol) { c['@kol']++; }
      p.classes.forEach(function (k) { c[k] = (c[k] || 0) + 1; });
    });
    return c;
  }
  function specCounts(people) {
    var c = {};
    people.forEach(function (p) { p.specialities.forEach(function (s) { c[s] = (c[s] || 0) + 1; }); });
    return c;
  }
  function pickSpeciality(doc, wanted) {
    var c = specCounts(doc.people);
    var ids = doc.specialities.map(function (s) { return s.id; });
    for (var i = 0; i < wanted.length; i++) {
      if (wanted[i] && ids.indexOf(wanted[i]) !== -1) { return wanted[i]; }
    }
    if (c.dermatology) { return 'dermatology'; }
    for (var j = 0; j < ids.length; j++) { if (c[ids[j]]) { return ids[j]; } }
    return ids[0];
  }

  /* Places present among the people: [{region, icbs:[{code,name,trusts:[{code,name,hospitals:[...]}]}]}] */
  function places(people) {
    var R = {};
    people.forEach(function (p) {
      if (!p.trustCode) { return; }
      var rg = p.region || 'Other';
      var r = R[rg] = R[rg] || {};
      var ik = p.icb || '-';
      var i = r[ik] = r[ik] || { code: p.icb || '', name: p.icbName || 'No integrated care board', trusts: {} };
      var t = i.trusts[p.trustCode] = i.trusts[p.trustCode] || { code: p.trustCode, name: p.trustName || p.trust || p.trustCode, n: 0, hospitals: {} };
      t.n++;
      if (p.hospital) { t.hospitals[p.hospital] = (t.hospitals[p.hospital] || 0) + 1; }
    });
    var byName = function (a, b) { return a.name < b.name ? -1 : 1; };
    return Object.keys(R).sort().map(function (rg) {
      return { region: rg, icbs: Object.keys(R[rg]).map(function (k) {
        var i = R[rg][k];
        return { code: i.code, name: i.name, trusts: Object.keys(i.trusts).map(function (c) { return i.trusts[c]; }).sort(byName) };
      }).sort(byName) };
    });
  }

  var _pure = { esc: esc, ukDate: ukDate, filter: filter, counts: counts, specCounts: specCounts, pickSpeciality: pickSpeciality, places: places };
  if (typeof module !== 'undefined' && module.exports) { module.exports = { _pure: _pure }; return; }

  /* ---------- view ---------- */
  var CSS = '.kolf,.kolf *{box-sizing:border-box}.kolf{overflow-wrap:anywhere;color:#0B1C33;font-family:Inter,-apple-system,"Segoe UI",system-ui,sans-serif}'
    + '.kolf h2{font-family:"Cormorant Garamond",Georgia,serif;font-size:30px;font-weight:600;margin:0 0 6px;color:#0B1C33}'
    + '.kolf h3{font-size:16px;margin:0;color:#0B1C33}'
    + '.kolf .kolf-sub{color:#1D2733;margin:0 0 16px;line-height:1.6;max-width:820px}'
    + '.kolf .kolf-controls{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 12px}'
    + '.kolf label{display:flex;flex-direction:column;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#14304F;gap:4px;flex:1 1 220px;min-width:0}'
    + '.kolf select,.kolf input{width:100%;max-width:100%;min-width:0;font:inherit;font-size:14.5px;font-weight:500;letter-spacing:0;text-transform:none;padding:9px 10px;border:1px solid #bfb49c;border-radius:8px;background:#fff;color:#0B1C33}'
    + '.kolf .kolf-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}'
    + '.kolf .kolf-chip{font:inherit;font-size:13.5px;font-weight:600;padding:8px 14px;border-radius:99px;border:1px solid #0B1C33;background:#fff;color:#0B1C33;cursor:pointer}'
    + '.kolf .kolf-chip[aria-pressed="true"]{background:#0B1C33;color:#F5F1E8}'
    + '.kolf .kolf-count{font-size:14px;color:#1D2733;margin:0 0 12px}'
    + '.kolf .kolf-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}'
    + '.kolf .kolf-card{background:#fff;border:1px solid #d9d1bf;border-top:3px solid #A8842C;border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:8px}'
    + '.kolf .kolf-role{margin:0;font-size:14px;line-height:1.5;color:#1D2733}'
    + '.kolf .kolf-role small{display:block;color:#37485a;font-size:12.5px}'
    + '.kolf .kolf-tags{display:flex;flex-wrap:wrap;gap:6px}'
    + '.kolf .kolf-tag{font-size:11.5px;font-weight:700;letter-spacing:.04em;padding:3px 10px;border-radius:99px;background:#0B1C33;color:#E0BE8E}'
    + '.kolf .kolf-tag.cls{background:#F5F1E8;color:#0B1C33;border:1px solid #bfb49c}'
    + '.kolf-jt{margin:2px 0 6px;color:#14304F;font-size:.95em}'
    + '.kolf .kolf-where{margin:0;font-size:12.5px;color:#46566A}'
    + '.kolf .kolf-chip.kol{border-color:#A8842C}.kolf .kolf-chip.kol[aria-pressed="true"]{background:#A8842C;color:#0B1C33}'
    + '.kolf .kolf-clear{font:inherit;font-size:13px;font-weight:600;background:none;border:0;color:#14304F;text-decoration:underline;cursor:pointer;padding:0;margin:0 0 12px}'
    + '.kolf .kolf-links{margin-top:auto;font-size:13px;display:flex;flex-wrap:wrap;gap:6px 14px}'
    + '.kolf .kolf-links a{color:#0B1C33;font-weight:600;text-decoration:underline}'
    + '.kolf .kolf-empty{background:#fff;border:1px dashed #8a7d5c;border-radius:12px;padding:18px 20px;color:#0B1C33;line-height:1.6}'
    + '.kolf .kolf-empty b{display:block;margin-bottom:4px}'
    + '.kolf details{background:#fff;border:1px solid #d9d1bf;border-radius:10px;padding:10px 14px;margin:18px 0 0}'
    + '.kolf summary{cursor:pointer;font-weight:700;color:#14304F}'
    + '.kolf details p,.kolf details li{color:#1D2733;line-height:1.6;margin:8px 0 0}'
    + '.kolf details ul{margin:6px 0 0;padding-left:20px}'
    + '.kolf details a{color:#0B1C33;text-decoration:underline}';

  function card(p) {
    var a = p.appearances;
    var roles = a.map(function (x) {
      return '<p class="kolf-role"><b>' + esc(x.role) + '</b>' + (x.organisation ? ', ' + esc(x.organisation) : '')
        + (x.term ? '<small>' + esc(x.term) + '</small>' : '') + '</p>';
    }).join('');
    var tags = p.bodies.map(function (b) { return '<span class="kolf-tag">' + esc(b) + '</span>'; }).join('')
      + p.classes.map(function (c) { return '<span class="kolf-tag cls">' + esc(CLASS_LABEL[c] || c) + '</span>'; }).join('');
    var seen = {};
    var src = a.filter(function (x) { if (seen[x.source_url]) { return false; } seen[x.source_url] = 1; return true; }).map(function (x) {
      return '<a href="' + esc(x.source_url) + '" target="_blank" rel="noopener">' + esc(SRC_SHORT[x.source] || 'Source') + ', checked ' + ukDate(x.checked) + '</a>';
    }).join('');
    return '<article class="kolf-card"><h3>' + esc(p.name) + '</h3>'
      + (p.job_title || p.trust ? '<p class="kolf-jt">' + esc([p.job_title, p.trust].filter(Boolean).join(', ')) + '</p>' : '')
      + (p.trustCode ? '<p class="kolf-where">' + esc([p.hospital, p.trustName, (p.icbName || '').replace(/ Integrated Care Board$/, '')].filter(Boolean).join(' · ')) + '</p>' : '') + roles + '<div class="kolf-tags">' + tags + '</div>'
      + '<div class="kolf-links">' + src + (p.linkedin_url
        ? '<a href="' + esc(p.linkedin_url) + '" target="_blank" rel="noopener">LinkedIn profile</a>'
        : '<a href="' + esc(p.linkedin_search) + '" target="_blank" rel="noopener">Find on LinkedIn (search)</a>') + '</div></article>';
  }
  var CLASS_LABEL = {};
  var SRC_SHORT = {};

  function run(doc, mount) {
    doc.classes.forEach(function (c) { CLASS_LABEL[c.id] = c.label; });
    doc.sources.forEach(function (s) { SRC_SHORT[s.id] = s.short; });
    var BODY_LABEL = { BAD: 'British Association of Dermatologists (BAD)', BDNG: 'British Dermatological Nursing Group (BDNG)', PCDS: 'Primary Care Dermatology Society (PCDS)', SDS: 'Scottish Dermatological Society (SDS)' };
    var qs = '', qq = '', qt = '', qi = '', qr = '', qh = '', qk = '';
    try {
      var up = new URLSearchParams(location.search);
      qs = up.get('speciality') || ''; qq = (up.get('q') || '').slice(0, 80);
      qt = up.get('trust') || ''; qi = up.get('icb') || ''; qr = up.get('region') || ''; qh = up.get('hospital') || ''; qk = up.get('kol') || '';
    } catch (e) {}
    /* A company desk can mount the finder with its own specialities: data-specs="mis,theatres" data-specs-label="Meril UK specialities". */
    var group = String(mount.getAttribute('data-specs') || '').split(',').map(function (x) { return x.trim(); }).filter(Boolean);
    var groupLabel = mount.getAttribute('data-specs-label') || 'This desk\'s specialities';
    var regionsOnly = String(mount.getAttribute('data-regions') || '').split('|').filter(Boolean);
    var st = { spec: qs === 'all' ? '' : (qs || (group.length ? '@group' : pickSpeciality(doc, [qs]))), group: group, cls: qk ? '@kol' : '', body: '', q: qq,
      region: qr, icb: qi, trust: qt, hosp: qh };
    if (qt && !qs) { st.spec = ''; }
    var sc = specCounts(doc.people);
    var specOpts = '<option value="">All specialities (' + doc.people.length + ')</option>'
      + (group.length ? '<option value="@group">' + esc(groupLabel) + '</option>' : '')
      + doc.specialities.map(function (s) {
        return '<option value="' + esc(s.id) + '">' + esc(s.label) + (sc[s.id] ? ' (' + sc[s.id] + ')' : ' (none checked yet)') + '</option>';
      }).join('');
    var BODY_NAME = {};
    doc.bodies.forEach(function (b) { BODY_NAME[b.id] = BODY_LABEL[b.id] || b.label || b.id; });
    function bodyOptsFor(spec) {
      var have = {};
      doc.people.forEach(function (p) {
        if (inSpeciality(p, spec, group)) { p.bodies.forEach(function (b) { have[b] = 1; }); }
      });
      return '<option value="">All bodies</option>' + doc.bodies.filter(function (b) { return have[b.id]; }).map(function (b) {
        return '<option value="' + esc(b.id) + '">' + esc(BODY_NAME[b.id]) + '</option>';
      }).join('');
    }
    var PL = places(doc.people).filter(function (r) { return !regionsOnly.length || regionsOnly.indexOf(r.region) !== -1; });
    function areaOpts() {
      return '<option value="">All regions and ICBs</option>' + PL.map(function (r) {
        return '<option value="r:' + esc(r.region) + '">' + esc(r.region) + ' (whole region)</option><optgroup label="' + esc(r.region) + '">'
          + r.icbs.filter(function (i) { return i.code; }).map(function (i) {
            return '<option value="i:' + esc(i.code) + '">' + esc(i.name.replace(/ Integrated Care Board$/, '')) + '</option>';
          }).join('') + '</optgroup>';
      }).join('');
    }
    function trustOpts() {
      var out = '<option value="">All trusts</option>';
      PL.forEach(function (r) {
        if (st.region && r.region !== st.region) { return; }
        r.icbs.forEach(function (i) {
          if (st.icb && i.code !== st.icb) { return; }
          var t = i.trusts.map(function (t) { return '<option value="' + esc(t.code) + '">' + esc(t.name) + ' (' + t.n + ')</option>'; }).join('');
          if (t) { out += '<optgroup label="' + esc(i.name.replace(/ Integrated Care Board$/, '')) + '">' + t + '</optgroup>'; }
        });
      });
      return out;
    }
    function hospOpts() {
      var t = null;
      PL.forEach(function (r) { r.icbs.forEach(function (i) { i.trusts.forEach(function (x) { if (x.code === st.trust) { t = x; } }); }); });
      var names = t ? Object.keys(t.hospitals).sort() : [];
      return '<option value="">' + (st.trust ? (names.length ? 'All hospitals in this trust' : 'No one filed to a single hospital yet') : 'Choose a trust first') + '</option>'
        + names.map(function (h) { return '<option value="' + esc(h) + '">' + esc(h) + ' (' + t.hospitals[h] + ')</option>'; }).join('');
    }
    var srcList = doc.sources.map(function (s) {
      return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.body) + ': ' + esc(s.title) + '</a>, read ' + ukDate(s.checked) + '. ' + esc(s.note) + '</li>';
    }).join('');
    var title = mount.getAttribute('data-title') || 'Find a Key Opinion Leader (KOL)';
    mount.innerHTML = '<style>' + CSS + '</style><div class="kolf">'
      + '<h2>' + esc(title) + '</h2>'
      + '<p class="kolf-sub">Key opinion leaders the professional bodies themselves put forward in public (board and committee members, invited speakers, editors and guideline authors), plus the trust leaders, buyers and named consultants our desks have read on trusts\' own pages. Filter by speciality, by key opinion leader, and by region, integrated care board (ICB), trust or hospital. Every name links to the page it came from.</p>'
      + '<div class="kolf-controls"><label>Speciality<select id="kolf-spec">' + specOpts + '</select></label>'
      + '<label>Region or ICB<select id="kolf-area">' + areaOpts() + '</select></label>'
      + '<label>Trust<select id="kolf-trust"></select></label>'
      + '<label>Hospital<select id="kolf-hosp"></select></label></div>'
      + '<div class="kolf-controls"><label>Body<select id="kolf-body">' + bodyOptsFor(st.spec) + '</select></label>'
      + '<label>Search name, role, trust or hospital<input id="kolf-q" type="search" placeholder="for example Lincoln, procurement, thoracic"></label></div>'
      + '<div class="kolf-chips" id="kolf-chips"></div><p class="kolf-count" id="kolf-count" aria-live="polite"></p>'
      + '<div id="kolf-out"></div>'
      + '<details><summary>Where this comes from, and why it is lawful</summary><p>Every name was read on the date shown from a page the body or trust itself publishes. Only the name, the public role and the page it came from are held. No email address, phone number or postal address is held, and LinkedIn is a search link unless a public result matched the same person.</p>'
      + '<p>Anyone listed can ask to be removed at <a href="mailto:contact@elevateandthrive.uk">contact@elevateandthrive.uk</a> and is dropped at the next build. Roles change, so check the source page before you write to anyone.</p>'
      + '<p>Pages read:</p><ul>' + srcList + '</ul></details></div>';

    var specSel = mount.querySelector('#kolf-spec');
    var areaSel = mount.querySelector('#kolf-area');
    var trustSel = mount.querySelector('#kolf-trust');
    var hospSel = mount.querySelector('#kolf-hosp');
    specSel.value = st.spec;
    mount.querySelector('#kolf-q').value = st.q;
    if (st.trust && !st.icb && !st.region) {
      PL.forEach(function (r) { r.icbs.forEach(function (i) { i.trusts.forEach(function (t) { if (t.code === st.trust) { st.icb = i.code; } }); }); });
    }
    areaSel.value = st.icb ? 'i:' + st.icb : (st.region ? 'r:' + st.region : '');
    function syncPlace() {
      trustSel.innerHTML = trustOpts(); trustSel.value = st.trust;
      if (trustSel.value !== st.trust) { st.trust = ''; st.hosp = ''; }
      hospSel.innerHTML = hospOpts(); hospSel.value = st.hosp; hospSel.disabled = !st.trust;
      if (hospSel.value !== st.hosp) { st.hosp = ''; }
    }
    syncPlace();
    function draw() {
      var c = counts(doc.people, st.spec, st);
      var chips = [['', 'Everyone', c.all], ['@kol', 'Key opinion leaders', c['@kol']]].concat(doc.classes.map(function (k) { return [k.id, k.label, c[k.id] || 0]; }));
      mount.querySelector('#kolf-chips').innerHTML = chips.filter(function (k) { return k[0] === '' || k[0] === '@kol' || k[2]; }).map(function (k) {
        return '<button type="button" class="kolf-chip' + (k[0] === '@kol' ? ' kol' : '') + '" data-c="' + esc(k[0]) + '" aria-pressed="' + (st.cls === k[0]) + '">' + esc(k[1]) + ' (' + k[2] + ')</button>';
      }).join('');
      var list = filter(doc.people, st);
      var out = mount.querySelector('#kolf-out');
      var label = st.spec === '@group' ? groupLabel : (st.spec ? ((doc.specialities.filter(function (s) { return s.id === st.spec; })[0] || {}).label || st.spec) : 'all specialities');
      var where = st.hosp || (st.trust ? trustSel.options[trustSel.selectedIndex].text.replace(/ \(\d+\)$/, '') : (areaSel.value ? areaSel.options[areaSel.selectedIndex].text : ''));
      mount.querySelector('#kolf-count').textContent = list.length + (list.length === 1 ? ' person' : ' people') + ' for ' + label + (where ? ', ' + where : '');
      if (list.length) {
        out.innerHTML = '<div class="kolf-grid">' + list.map(card).join('') + '</div>';
      } else if (!c.all && (st.trust || st.icb || st.region)) {
        out.innerHTML = '<div class="kolf-empty"><b>Nobody checked here yet for ' + esc(label) + '.</b>Try All specialities, or widen the area. We add a name only after reading it on a public page.</div>';
      } else if (!c.all) {
        out.innerHTML = '<div class="kolf-empty"><b>No checked people for ' + esc(label) + ' yet.</b>We publish a name only after reading it on the speciality body\'s own public page, so this stays empty until that is done.</div>';
      } else if (st.cls && doc.empty[st.cls] && !c[st.cls]) {
        out.innerHTML = '<div class="kolf-empty"><b>Nobody listed in this group.</b>' + esc(doc.empty[st.cls]) + '</div>';
      } else {
        out.innerHTML = '<div class="kolf-empty"><b>Nobody matches those filters.</b>Clear the search or choose Everyone.</div>';
      }
    }
    specSel.addEventListener('change', function () {
      st.spec = specSel.value; st.body = '';
      mount.querySelector('#kolf-body').innerHTML = bodyOptsFor(st.spec);
      draw();
    });
    areaSel.addEventListener('change', function () {
      var v = areaSel.value; st.region = v.indexOf('r:') === 0 ? v.slice(2) : ''; st.icb = v.indexOf('i:') === 0 ? v.slice(2) : '';
      st.trust = ''; st.hosp = ''; syncPlace(); draw();
    });
    trustSel.addEventListener('change', function () { st.trust = trustSel.value; st.hosp = ''; syncPlace(); draw(); });
    hospSel.addEventListener('change', function () { st.hosp = hospSel.value; draw(); });
    mount.querySelector('#kolf-body').addEventListener('change', function (e) { st.body = e.target.value; draw(); });
    mount.querySelector('#kolf-q').addEventListener('input', function (e) { st.q = e.target.value; draw(); });
    mount.querySelector('#kolf-chips').addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('button[data-c]') : null;
      if (b) { st.cls = b.getAttribute('data-c'); draw(); }
    });
    draw();

    root.mshKol = {
      forSpecialities: function (ids) {
        return doc.people.filter(function (p) { return (ids || []).some(function (i) { return p.specialities.indexOf(i) !== -1; }); });
      },
      forTrust: function (code) { return doc.people.filter(function (p) { return p.trustCode === code; }); }
    };
    /* A signed-in member's My Hub speciality, when they have not chosen one in the link. */
    if (!qs && !qt && !group.length && root.fetch && (root.mshRestNonce || root.mshPrefsNonce)) {
      root.fetch('/wp-json/msh/v1/prefs', { credentials: 'same-origin', headers: { 'X-WP-Nonce': root.mshRestNonce || root.mshPrefsNonce } })
        .then(function (r) { return r.json(); })
        .then(function (p) {
          var s = p && p.interests ? p.interests.speciality : '';
          if (s && s !== st.spec && specCounts(doc.people)[s]) { st.spec = s; specSel.value = s; draw(); }
        }).catch(function () {});
    }
  }

  function start() {
    var mount = document.getElementById(MOUNT_ID);
    if (!mount) { return; }
    fetch(root.mshKolSrc || SRC, { cache: 'no-cache' }).then(function (r) { if (!r.ok) { throw new Error(r.status); } return r.json(); })
      .then(function (doc) { run(doc, mount); })
      .catch(function () { mount.innerHTML = 'The KOL finder is temporarily unavailable. Please try again shortly.'; });
  }
  start();
})(typeof window !== 'undefined' ? window : this);
