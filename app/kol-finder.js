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
  function inSpeciality(p, spec) { return !spec || p.specialities.indexOf(spec) !== -1; }
  function filter(people, f) {
    var q = String(f.q || '').toLowerCase().trim();
    return people.filter(function (p) {
      if (!inSpeciality(p, f.spec)) { return false; }
      if (f.cls && p.classes.indexOf(f.cls) === -1) { return false; }
      if (f.body && p.bodies.indexOf(f.body) === -1) { return false; }
      if (q) {
        var hay = (p.name + ' ' + p.appearances.map(function (a) { return a.role + ' ' + (a.organisation || ''); }).join(' ')).toLowerCase();
        if (hay.indexOf(q) === -1) { return false; }
      }
      return true;
    });
  }
  function counts(people, spec) {
    var c = { all: 0 };
    people.forEach(function (p) {
      if (!inSpeciality(p, spec)) { return; }
      c.all++;
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
    for (var j = 0; j < ids.length; j++) { if (c[ids[j]]) { return ids[j]; } }
    return ids[0];
  }

  var _pure = { esc: esc, ukDate: ukDate, filter: filter, counts: counts, specCounts: specCounts, pickSpeciality: pickSpeciality };
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
    return '<article class="kolf-card"><h3>' + esc(p.name) + '</h3>' + roles + '<div class="kolf-tags">' + tags + '</div>'
      + '<div class="kolf-links">' + src + '<a href="' + esc(p.linkedin_search) + '" target="_blank" rel="noopener">Find on LinkedIn (search)</a></div></article>';
  }
  var CLASS_LABEL = {};
  var SRC_SHORT = {};

  function run(doc, mount) {
    doc.classes.forEach(function (c) { CLASS_LABEL[c.id] = c.label; });
    doc.sources.forEach(function (s) { SRC_SHORT[s.id] = s.short; });
    var BODY_LABEL = { BAD: 'British Association of Dermatologists (BAD)', BDNG: 'British Dermatological Nursing Group (BDNG)', PCDS: 'Primary Care Dermatology Society (PCDS)', SDS: 'Scottish Dermatological Society (SDS)' };
    var qs = '';
    try { qs = new URLSearchParams(location.search).get('speciality') || ''; } catch (e) {}
    var st = { spec: pickSpeciality(doc, [qs]), cls: '', body: '', q: '' };
    var sc = specCounts(doc.people);
    var specOpts = doc.specialities.map(function (s) {
      return '<option value="' + esc(s.id) + '">' + esc(s.label) + (sc[s.id] ? ' (' + sc[s.id] + ')' : ' (none checked yet)') + '</option>';
    }).join('');
    var bodyOpts = '<option value="">All bodies</option>' + doc.bodies.map(function (b) {
      return '<option value="' + esc(b.id) + '">' + esc(BODY_LABEL[b.id] || b.id) + '</option>';
    }).join('');
    var srcList = doc.sources.map(function (s) {
      return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.body) + ': ' + esc(s.title) + '</a>, read ' + ukDate(s.checked) + '. ' + esc(s.note) + '</li>';
    }).join('');
    mount.innerHTML = '<style>' + CSS + '</style><div class="kolf">'
      + '<h2>Find a Key Opinion Leader (KOL)</h2>'
      + '<p class="kolf-sub">People the professional bodies themselves put forward in public: the board and committee members who steer a speciality, the speakers they invite, the editors and guideline authors. Pick a speciality, then narrow by who they are. Dermatology is first; other specialities show as soon as their sources are checked.</p>'
      + '<div class="kolf-controls"><label>Speciality<select id="kolf-spec">' + specOpts + '</select></label>'
      + '<label>Body<select id="kolf-body">' + bodyOpts + '</select></label>'
      + '<label>Search name or role<input id="kolf-q" type="search" placeholder="for example Scotland, editor, guidelines"></label></div>'
      + '<div class="kolf-chips" id="kolf-chips"></div><p class="kolf-count" id="kolf-count" aria-live="polite"></p>'
      + '<div id="kolf-out"></div>'
      + '<details><summary>Where this comes from, and why it is lawful</summary><p>Every name was read on the date shown from a page the body itself publishes. Only the name, the public role and the page it came from are held. No email address, phone number or home detail is stored, and paid staff are not listed. The lawful basis is legitimate interests under the UK General Data Protection Regulation (UK GDPR), Article 6(1)(f): a member of the Hub finding the people a speciality publicly puts forward. The LinkedIn link is a search built from the name and the body, so it leads you to profiles to judge for yourself. Nothing is matched or stored.</p>'
      + '<p>Anyone listed can ask to be removed at <a href="mailto:contact@elevateandthrive.uk">contact@elevateandthrive.uk</a> and is dropped at the next build. Roles change at each election, so check the source page before you write to anyone.</p>'
      + '<p>Pages read:</p><ul>' + srcList + '</ul></details></div>';

    var specSel = mount.querySelector('#kolf-spec');
    specSel.value = st.spec;
    function draw() {
      var c = counts(doc.people, st.spec);
      var chips = [['', 'Everyone', c.all]].concat(doc.classes.map(function (k) { return [k.id, k.label, c[k.id] || 0]; }));
      mount.querySelector('#kolf-chips').innerHTML = chips.map(function (k) {
        return '<button type="button" class="kolf-chip" data-c="' + esc(k[0]) + '" aria-pressed="' + (st.cls === k[0]) + '">' + esc(k[1]) + ' (' + k[2] + ')</button>';
      }).join('');
      var list = filter(doc.people, st);
      var out = mount.querySelector('#kolf-out');
      var label = (doc.specialities.filter(function (s) { return s.id === st.spec; })[0] || {}).label || st.spec;
      mount.querySelector('#kolf-count').textContent = list.length + (list.length === 1 ? ' person' : ' people') + ' for ' + label;
      if (list.length) {
        out.innerHTML = '<div class="kolf-grid">' + list.map(card).join('') + '</div>';
      } else if (!c.all) {
        out.innerHTML = '<div class="kolf-empty"><b>No checked people for ' + esc(label) + ' yet.</b>We publish a name only after reading it on the speciality body\'s own public page, so this stays empty until that is done. Dermatology has the full set to see how it will look.</div>';
      } else if (st.cls && doc.empty[st.cls] && !c[st.cls]) {
        out.innerHTML = '<div class="kolf-empty"><b>Nobody listed in this group.</b>' + esc(doc.empty[st.cls]) + '</div>';
      } else {
        out.innerHTML = '<div class="kolf-empty"><b>Nobody matches those filters.</b>Clear the search or choose Everyone.</div>';
      }
    }
    specSel.addEventListener('change', function () { st.spec = specSel.value; st.cls = ''; draw(); });
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
      }
    };
    /* A signed-in member's My Hub speciality, when they have not chosen one in the link. */
    if (!qs && root.fetch && (root.mshRestNonce || root.mshPrefsNonce)) {
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
