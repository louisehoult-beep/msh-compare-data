/* Medical Sales Hub — My Hub, built by the member.
   The member ticks the Hub pages they want and My Hub becomes their own front
   page: their tiles in their order, plus the latest live news from every
   speciality they pinned. Replaces the three-question shortlist (role,
   speciality, setting) that picked five links for them (Lou, 23/09/2026:
   "so they can select the things from the Hub they want to see").

   Mounted on <div id="msh-my-hub"></div> on /medical-sales-hub/my-hub/. The
   WordPress page carries a loader only; edit the code HERE.

   WHAT CAN BE PICKED: hub/my-hub-catalogue.json, published pages only. A
   saved id that is no longer in the catalogue is dropped from view, never
   shown as a dead link, and kept in storage so re-adding the page restores it.

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
  var API = '/wp-json/msh/v1/my-hub';
  var PREFS = '/wp-json/msh/v1/prefs';
  var LS = 'msh_my_hub_pins_v1';
  var NEWS_MAX = 8;

  var CAT = null, BYID = {}, pins = [], where = 'none', seeded = false;
  var draft = null, query = '';

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function nonce() { return window.mshRestNonce || window.mshPrefsNonce || ''; }
  function lsGet() { try { var v = JSON.parse(localStorage.getItem(LS) || 'null'); return Array.isArray(v) ? v : null; } catch (e) { return null; } }
  function lsSet(v) { try { localStorage.setItem(LS, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function visible(list) { return list.filter(function (id) { return !!BYID[id]; }); }
  function fmtDate(d) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(d || '');
    return m ? m[3] + '/' + m[2] + '/' + m[1] : '';
  }

  function css() {
    if (document.getElementById('msh-myh2-css')) { return; }
    var st = document.createElement('style');
    st.id = 'msh-myh2-css';
    st.textContent = [
      '.msh .mh-bar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:16px;}',
      '.msh .mh-bar h2{font-size:11.5px;letter-spacing:2px;font-weight:700;color:var(--gold);text-transform:uppercase;}',
      '.msh .mh-btn{background:var(--gold);color:#fff;border:0;border-radius:8px;padding:10px 18px;font:700 13.5px Inter,sans-serif;cursor:pointer;}',
      '.msh .mh-btn:hover{background:#8a6215;}',
      '.msh .mh-btn.ghost{background:#fff;color:var(--ink);border:1px solid var(--border);}',
      '.msh .mh-btn.ghost:hover{border-color:var(--gold);color:var(--gold);}',
      '.msh .mh-tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;}',
      '.msh .mh-tile{display:block;background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 16px;}',
      '.msh .mh-tile:hover{border-color:var(--gold);}',
      '.msh .mh-tile b{display:block;font-size:14.5px;line-height:1.35;color:var(--ink);}',
      '.msh .mh-tile span{display:block;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--dim);margin-top:6px;}',
      '.msh .mh-panel{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:20px 22px;box-shadow:0 1px 3px rgba(29,39,51,.06);margin-bottom:18px;}',
      '.msh .mh-empty{text-align:center;color:var(--dim);line-height:1.65;}',
      '.msh .mh-empty p{max-width:520px;margin:0 auto 14px;}',
      '.msh .mh-note{font-size:12.5px;color:var(--dim);line-height:1.6;margin-top:12px;}',
      '.msh .mh-note.warn{color:#8a4b12;}',
      '.msh .mh-news{list-style:none;}',
      '.msh .mh-news li{padding:11px 0;border-bottom:1px solid var(--border);line-height:1.45;}',
      '.msh .mh-news li:last-child{border-bottom:0;}',
      '.msh .mh-news a{font-weight:600;color:var(--ink);}',
      '.msh .mh-news a:hover{color:var(--gold);}',
      '.msh .mh-news small{display:block;font-size:11.5px;color:var(--dim);margin-top:3px;}',
      '.msh .mh-tools{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;}',
      '.msh .mh-tools input,.msh .mh-tools select{flex:1 1 220px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;font:14px Inter,sans-serif;color:var(--ink);background:#fff;}',
      '.msh .mh-group{border-top:1px solid var(--border);padding:12px 0;}',
      '.msh .mh-group summary{cursor:pointer;font-weight:700;font-size:13.5px;display:flex;justify-content:space-between;gap:10px;}',
      '.msh .mh-group summary em{font-style:normal;font-weight:600;font-size:12px;color:var(--dim);}',
      '.msh .mh-opts{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:4px 14px;margin-top:10px;}',
      '.msh .mh-opts label{display:flex;gap:8px;align-items:flex-start;font-size:13.5px;line-height:1.4;padding:5px 0;cursor:pointer;}',
      '.msh .mh-opts input{margin-top:3px;accent-color:var(--gold);}',
      '.msh .mh-order{list-style:none;counter-reset:o;}',
      '.msh .mh-order li{display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--border);font-size:13.5px;}',
      '.msh .mh-order li span{flex:1;}',
      '.msh .mh-order button{background:#fff;border:1px solid var(--border);border-radius:6px;width:30px;height:28px;cursor:pointer;color:var(--ink);font-size:13px;}',
      '.msh .mh-order button:hover{border-color:var(--gold);color:var(--gold);}',
      '.msh .mh-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px;}',
      '.msh .mh-link{background:none;border:0;color:var(--gold);font:600 12px Inter,sans-serif;cursor:pointer;padding:0;}'
    ].join('');
    document.head.appendChild(st);
  }

  function groupLabel(gid) {
    var g = (CAT.groups || []).filter(function (x) { return x.id === gid; })[0];
    return g ? g.label : '';
  }

  /* ---------- the member's page ---------- */
  function renderView() {
    var list = visible(pins);
    var h = '<div class="mh-bar"><h2>Your page</h2>'
      + '<button type="button" class="mh-btn" data-act="edit">' + (list.length ? 'Choose what’s on it' : 'Build my page') + '</button></div>';
    if (!list.length) {
      h += '<div class="mh-panel mh-empty"><p>Pick the Hub pages you use most: your specialities, the desks you check, the tools you open. They’ll sit here, in your order, every time you log in. Your specialities also bring their latest news with them.</p>'
        + '<button type="button" class="mh-btn" data-act="edit">Build my page</button></div>';
    } else {
      if (seeded) {
        h += '<p class="mh-note">This is a starting point from the interests you set earlier. Nothing is saved until you choose and save.</p>';
      }
      h += '<div class="mh-tiles">' + list.map(function (id) {
        var it = BYID[id];
        return '<a class="mh-tile" href="' + esc(it.url) + '"><b>' + esc(it.label) + '</b><span>' + esc(groupLabel(it.group)) + '</span></a>';
      }).join('') + '</div>';
      h += '<div id="mh-news-slot"></div>';
    }
    h += saveNote();
    mount.innerHTML = h;
    if (list.length) { loadNews(list); }
  }

  function saveNote() {
    if (where === 'account') { return '<p class="mh-note">Saved to your Hub account, so it follows you across devices.</p>'; }
    if (where === 'device') { return '<p class="mh-note warn">Saved on this device only. Your account couldn’t be reached, so your choices won’t show on another phone or computer yet.</p>'; }
    return '';
  }

  function loadNews(list) {
    var specs = list.filter(function (id) { return BYID[id].news; });
    var slot = document.getElementById('mh-news-slot');
    if (!specs.length || !slot) { return; }
    var got = [], left = specs.length;
    specs.forEach(function (id) {
      fetch(NEWS_URL + encodeURIComponent(id) + '.json', { cache: 'no-cache' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { ((d && d.items) || []).forEach(function (it) { if (it && it.title && it.link) { got.push({ it: it, spec: id }); } }); })
        .catch(function () {})
        .then(function () { if (--left === 0) { paintNews(got, slot); } });
    });
  }

  function paintNews(got, slot) {
    if (!got.length) { return; }
    var seen = {};
    got = got.filter(function (g) { if (seen[g.it.link]) { return false; } seen[g.it.link] = 1; return true; });
    got.sort(function (a, b) { return String(b.it.published || '').localeCompare(String(a.it.published || '')); });
    slot.innerHTML = '<div class="mh-panel" style="margin-top:18px;"><div class="mh-bar"><h2>Latest from your specialities</h2></div>'
      + '<ul class="mh-news">' + got.slice(0, NEWS_MAX).map(function (g) {
        var meta = [BYID[g.spec].label, fmtDate(g.it.published), g.it.source].filter(Boolean).join(' · ');
        return '<li><a href="' + esc(g.it.link) + '" target="_blank" rel="noopener">' + esc(g.it.title) + '</a><small>' + esc(meta) + '</small></li>';
      }).join('') + '</ul><p class="mh-note">Updated daily. Each line names its source. Open the speciality page for the full feed.</p></div>';
  }

  /* ---------- choosing ---------- */
  function renderEdit() {
    var chosen = {};
    draft.forEach(function (id) { chosen[id] = 1; });
    var q = query.toLowerCase();
    var roles = CAT.roles || {};
    var h = '<div class="mh-bar"><h2>Choose what’s on your page</h2><em style="font-style:normal;font-size:12.5px;color:var(--dim);">' + draft.length + ' chosen</em></div>'
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
      + '<button type="button" class="mh-btn ghost" data-act="cancel">Cancel</button></div>';
    mount.innerHTML = h;
    var qi = document.getElementById('mh-q');
    if (qi && query) { qi.focus(); qi.setSelectionRange(query.length, query.length); }
  }

  function startEdit() { draft = visible(pins).slice(); query = ''; renderEdit(); }

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
    var t = e.target.closest ? e.target.closest('button') : null;
    if (!t) { return; }
    var act = t.getAttribute('data-act');
    if (act === 'edit') { startEdit(); return; }
    if (act === 'cancel') { draft = null; renderView(); return; }
    if (act === 'save') { save(); return; }
    if (act === 'clear') { draft = []; renderEdit(); return; }
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
        mount.innerHTML = '<div class="mh-panel mh-empty"><p>Log in to the Hub to build and save your page.</p><a class="mh-btn" href="/login/">Log in</a></div>';
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
