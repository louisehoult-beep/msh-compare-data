/* Medical Sales Hub — Top NHS suppliers by framework presence.
   Mounts on #msh-top10 (Suppliers page 677, anchor #top10).

   WHY THIS IS COMPUTED IN THE BROWSER AND NOT TYPED INTO THE PAGE
   --------------------------------------------------------------
   The ranking is a function of data/frameworks.json, which is rebuilt from NHS
   Supply Chain's own contract launch briefs. Typing a list into WordPress would
   freeze it at the moment somebody pasted it, and it would drift silently the
   next time a framework is re-awarded. Rendering it here means the page is
   always the current answer, and there is exactly one copy of the underlying
   fact — the same reason every other Hub surface reads these files.

   THE RULE THIS PANEL PUBLISHES, AND ITS LIMIT
   --------------------------------------------
   "Top" here means ONE thing, stated on the panel: the number of NHS Supply
   Chain frameworks whose own brief names that supplier. It is NOT revenue, NOT
   NHS spend and NOT market share — nobody publishes those per supplier, and the
   Hub does not invent them.

   It is counted PER SUPPLIER NAME AS PRINTED ON THE BRIEFS. A group that trades
   under several names (GBUK Ltd, GBUK Healthcare, GBUK Enteral Limited) is
   counted per name, so a group's true footprint can be larger than its row here.
   That is stated on the panel rather than fixed by guessing which names belong
   to which parent: merging names by resemblance is how the wrong company gets
   credited with another company's frameworks.

   COST: none. Static file on GitHub, computed in the member's browser. */
(function () {
  var MOUNT = document.getElementById('msh-top10');
  if (!MOUNT) { return; }
  if (MOUNT.getAttribute('data-eth-bound') === 'v1') { return; }
  MOUNT.setAttribute('data-eth-bound', 'v1');

  var FW = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/frameworks.json';
  var IDX = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/supplier-index.json';
  var G = '#a8842c', INK = '#1d2733', DIM = '#75808d', LINE = '#e6e0d4', SOFT = '#f7f4ee';
  var SHOW = 10;
  /* THIS TOOL DELIBERATELY DOES NOT READ data/supplier-products.json, and that
     is not an oversight — every other tool was wired to it on 07/08/2026.
     This panel ranks suppliers by ONE thing: how many NHS Supply Chain contract
     launch briefs name them. The range file holds a company's own website
     catalogue and carries no framework data at all, so folding it in could only
     change the ranking by something the ranking does not measure. A supplier
     with 733 products on its own site and two frameworks belongs at two.
     The honest place for range size is the supplier's own card in Supplier
     Search and the Company Report, where both are shown side by side. */

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  var CO_SUFFIX = /\b(ltd|limited|plc|llp|inc|corp|corporation|co|company|group|holdings|international|uk|u k|gb|healthcare|health care|health|medical|medica|med|products|solutions|systems|technologies|technology|devices|device)\b/g;
  function coKey(s) {
    return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ')
      .replace(CO_SUFFIX, ' ').replace(/\s+/g, ' ').trim();
  }

  function render(fwDoc, idxDoc) {
    var frameworks = (fwDoc && fwDoc.frameworks) || [];
    if (!frameworks.length) {
      MOUNT.innerHTML = '<div style="font-size:13px;color:' + DIM + ';">The framework capture could not be read, so this ranking is not shown. Nothing is missing from the data; the page could not load it.</div>';
      return;
    }

    /* Count frameworks per supplier name. A supplier named twice on one brief
       counts once for that brief. */
    var count = {}, seenName = {};
    frameworks.forEach(function (f) {
      var here = {};
      (f.suppliers || []).forEach(function (n) {
        var k = coKey(n);
        if (!k || here[k]) { return; }
        here[k] = 1;
        count[k] = (count[k] || 0) + 1;
        if (!seenName[k]) { seenName[k] = {}; }
        seenName[k][n] = (seenName[k][n] || 0) + 1;
      });
    });

    /* Prefer the Hub's own display name where this supplier has a profile, so
       a member clicking through lands on a page that exists. */
    var display = {};
    ((idxDoc && idxDoc.suppliers) || []).forEach(function (s) {
      [s.name].concat(s.aliases || []).forEach(function (n) {
        var k = coKey(n);
        if (k && !display[k]) { display[k] = s.name; }
      });
    });

    var rows = Object.keys(count).map(function (k) {
      var name = display[k];
      if (!name) {
        var variants = seenName[k], best = '', n = -1;
        for (var v in variants) { if (variants[v] > n) { best = v; n = variants[v]; } }
        name = best;
      }
      return { key: k, name: name, n: count[k], profile: !!display[k] };
    }).sort(function (a, b) {
      if (b.n !== a.n) { return b.n - a.n; }
      return a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1;
    });

    var top = rows.slice(0, SHOW);
    var max = top.length ? top[0].n : 1;

    var h = '<div style="font-family:Inter,-apple-system,Segoe UI,sans-serif;">';
    h += '<div style="font-size:11px;letter-spacing:2px;font-weight:700;color:' + G + ';">TOP ' + top.length + ' NHS SUPPLIERS</div>';
    h += '<div style="font-size:20px;font-weight:800;color:' + INK + ';margin:4px 0 8px;">By number of NHS Supply Chain frameworks</div>';

    h += '<div style="background:' + SOFT + ';border:1px solid ' + LINE + ';border-left:3px solid ' + G + ';border-radius:0 8px 8px 0;padding:10px 13px;font-size:12px;color:#4a5766;line-height:1.6;margin:0 0 14px;">' +
      '<b style="color:' + G + ';letter-spacing:.06em;">HOW THIS IS RANKED</b><br>' +
      'The number of NHS Supply Chain frameworks whose <b>own contract launch brief names that supplier</b>, counted across ' +
      frameworks.length + ' briefs captured on ' + esc(fwDoc.dataAsOf || 'an unrecorded date') + '. ' +
      'This is <b>not</b> revenue, NHS spend or market share: nobody publishes those per supplier, so the Hub does not show them. ' +
      'Suppliers are counted <b>by the name printed on each brief</b>, so a group trading under several names is counted per name and its real footprint may be wider than the row below. ' +
      (fwDoc.unparsedCount ? fwDoc.unparsedCount + ' further brief(s) are not included, because their supplier list did not match the count the page itself states or they publish no names at all.' : '') +
      '</div>';

    h += top.map(function (r, i) {
      var pct = Math.round(r.n / max * 100);
      return '<div style="display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid #f0ece3;">' +
        '<div style="width:22px;text-align:right;font-size:13px;font-weight:800;color:' + G + ';">' + (i + 1) + '</div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-size:14px;font-weight:700;color:' + INK + ';">' + esc(r.name) +
          (r.profile ? '' : ' <span style="font-size:10.5px;font-weight:600;color:' + DIM + ';">· no Hub profile yet</span>') + '</div>' +
          '<div style="height:7px;background:#efe9db;border-radius:99px;margin-top:5px;overflow:hidden;">' +
            '<div style="height:100%;width:' + pct + '%;background:linear-gradient(90deg,#D4AF7A,#B8935A);"></div>' +
          '</div>' +
        '</div>' +
        '<div style="width:112px;text-align:right;font-size:12.5px;color:#37485a;white-space:nowrap;">' + r.n + ' frameworks</div>' +
        '</div>';
    }).join('');

    h += '<div style="font-size:11.5px;color:' + DIM + ';margin-top:10px;line-height:1.6;">' +
      'Ranked from ' + Object.keys(count).length + ' distinct supplier names across those briefs. ' +
      'Open any company in <a href="/medical-sales-hub/company-report/" style="color:' + G + ';font-weight:600;">Company Intelligence Reports</a> for its full framework list, the other suppliers on each one, and its Companies House record.' +
      '</div></div>';

    MOUNT.innerHTML = h;
  }

  if (window.MSH_TOP10_DATA) {
    render(window.MSH_TOP10_DATA.frameworks, window.MSH_TOP10_DATA.index);
    return;
  }

  MOUNT.innerHTML = '<div style="font-family:Inter,sans-serif;color:' + DIM + ';font-size:13px;">Loading the supplier ranking…</div>';
  var cb = '?cb=' + Date.now();
  Promise.all([
    fetch(FW + cb, { cache: 'no-store' }).then(function (r) { return r.json(); }),
    fetch(IDX + cb, { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return null; })
  ]).then(function (res) { render(res[0], res[1]); })
    .catch(function () {
      MOUNT.innerHTML = '<div style="font-family:Inter,sans-serif;color:' + DIM + ';font-size:13px;">The supplier ranking is loading its data — if this persists, the feed is temporarily unreachable. Nothing is missing from the ranking; it has not loaded.</div>';
    });
})();
