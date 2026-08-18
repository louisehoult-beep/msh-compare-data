/* Medical Sales Hub — Hospital prescribing dispensed in the community.
   Mounts on #msh-hospital-prescribing.

   WHAT A MEMBER IS LOOKING AT, AND WHAT THEY ARE NOT
   --------------------------------------------------
   Items PRESCRIBED BY AN NHS TRUST in England and DISPENSED IN A COMMUNITY
   PHARMACY. It is NOT in-hospital usage and it is NOT GP prescribing. A rep who
   reads a trust's row as "what this trust uses" has read it wrong, so the scope
   line is rendered on the panel every time and is not collapsible. Do not remove
   it to tidy the layout.

   WHY IT IS WORTH HAVING ANYWAY
   -----------------------------
   Because it is real, named, trust-level movement with no customer integration
   at all, and because the BNF code carries the brand. Characters 10-11 of the
   code are the product segment: "AA" is the generic and anything else is a
   brand, so one molecule at one trust splits into "how much went to my brand"
   and "how much went to generics". Most CRMs do not surface that.

   THE RULES THIS PANEL PUBLISHES
   ------------------------------
   All four are read from index.json rather than restated here, so the panel and
   the builder cannot drift apart. They are printed under the table, because a
   derived number a reader cannot audit is worth nothing on a paid product.

   THE EVIDENCE FLOOR IS THE POINT, NOT A DETAIL
   ---------------------------------------------
   A trust going from 1 item to 2 is +100%. Publishing that as a trend would be
   the derived-claim failure rule 14 exists to prevent, so no percentage is shown
   where the baseline month is under index.minBaselineItems; the cell says "too
   few to trend" instead. If the panel ever looks empty, that is the honest
   answer and not a bug to tune away.

   COST: none. Static files on GitHub, computed in the member's browser. */
(function () {
  var MOUNT = document.getElementById('msh-hospital-prescribing');
  if (!MOUNT) { return; }
  if (MOUNT.getAttribute('data-eth-bound') === 'v1') { return; }
  MOUNT.setAttribute('data-eth-bound', 'v1');

  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/hospital-prescribing/';
  var G = '#a8842c', INK = '#1d2733', DIM = '#75808d', LINE = '#e6e0d4', SOFT = '#f7f4ee';
  var UP = '#8c2f39', DOWN = '#2f6b4f';
  var SHOW = 25;

  var IDX = null, SHARDS = {}, CUR = null;
  /* Indices NHSBSA did not publish, and the earliest month that DID publish —
     the trend baseline. Anchoring the comparison to periods[0] when periods[0]
     is an unpublished month compares against nothing and silently reports
     'too few to trend' for every trust in the country. */
  var MISS = {}, BASEI = 0;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function num(n) { return (n == null ? '' : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',')); }
  function money(n) {
    if (n == null) { return ''; }
    return '£' + num(Math.round(n));
  }
  function periodLabel(p) {
    var M = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return M[parseInt(String(p).slice(4, 6), 10) - 1] + ' ' + String(p).slice(0, 4);
  }
  function get(url) {
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) { throw new Error(url + ' returned ' + r.status); }
      return r.json();
    });
  }
  function sum(a) { var t = 0, i; for (i = 0; i < a.length; i++) { t += a[i] || 0; } return t; }

  /* ---------------------------------------------------------------------- */

  /* A month NHSBSA did not publish is null, and the line BREAKS there. Plotting it
     as zero would draw a cliff straight down and back up, which reads as prescribing
     having stopped that month. It did not; the file simply does not exist. */
  function sparkline(arr) {
    var w = 84, h = 20, i, x, y, cur = [], segs = [];
    var vals = arr.filter(function (v) { return v != null; });
    var max = Math.max.apply(null, vals.concat([1]));
    for (i = 0; i < arr.length; i++) {
      if (arr[i] == null) {
        if (cur.length) { segs.push(cur); cur = []; }
        continue;
      }
      x = (i * (w / Math.max(1, arr.length - 1))).toFixed(1);
      y = (h - (arr[i] / max) * (h - 2) - 1).toFixed(1);
      cur.push(x + ',' + y);
    }
    if (cur.length) { segs.push(cur); }
    return '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h +
      '" aria-hidden="true" style="vertical-align:middle">' +
      segs.map(function (s) {
        return '<polyline fill="none" stroke="' + G + '" stroke-width="1.5" points="' +
          s.join(' ') + '"/>';
      }).join('') + '</svg>';
  }

  /* The one derived number on the panel. Returns null when the baseline is below
     the floor — the caller prints the refusal, never a substitute figure. */
  function change(latest, baseline) {
    if (baseline == null || baseline < IDX.minBaselineItems) { return null; }
    return ((latest - baseline) / baseline) * 100;
  }
  function changeCell(latest, baseline) {
    var pc = change(latest, baseline);
    if (pc === null) {
      return '<span style="color:' + DIM + ';font-size:12px">too few to trend</span>';
    }
    var col = pc > 0 ? DOWN : (pc < 0 ? UP : DIM);
    var sign = pc > 0 ? '+' : '';
    return '<strong style="color:' + col + '">' + sign + pc.toFixed(0) + '%</strong>';
  }

  /* ---------------------------------------------------------------------- */

  function shell() {
    var src = IDX.source;
    return '' +
      '<div style="font:15px/1.55 Georgia,serif;color:' + INK + '">' +
      '<div style="border-left:3px solid ' + G + ';background:' + SOFT +
      ';padding:10px 14px;margin:0 0 16px">' +
      '<strong>What this is.</strong> ' + esc(IDX.scope) +
      ' Data ' + esc(periodLabel(IDX.periods[0])) + ' to ' +
      esc(periodLabel(IDX.periods[IDX.periods.length - 1])) +
      ', refreshed monthly. NHSBSA publishes roughly three months in arrears.' +
      ((IDX.missingPeriods && IDX.missingPeriods.length)
        ? ' <strong>' + IDX.missingPeriods.map(periodLabel).map(esc).join(', ') +
          (IDX.missingPeriods.length > 1 ? ' were' : ' was') +
          ' never published by NHSBSA</strong> and shows as a break in the line, not a fall.'
        : '') +
      '</div>' +
      '<div style="margin:0 0 14px">' +
      '<label for="msh-hp-q" style="display:block;font:600 13px/1.4 system-ui,sans-serif;' +
      'text-transform:uppercase;letter-spacing:.06em;color:' + DIM + ';margin-bottom:6px">' +
      'Find a molecule or brand</label>' +
      '<input id="msh-hp-q" type="search" autocomplete="off" placeholder="e.g. Aripiprazole, Epilim, methylphenidate" ' +
      'style="width:100%;max-width:460px;padding:9px 12px;border:1px solid ' + LINE +
      ';border-radius:4px;font:15px Georgia,serif;color:' + INK + '">' +
      '<div id="msh-hp-sug"></div></div>' +
      '<div id="msh-hp-out"></div>' +
      '<div style="margin-top:22px;padding-top:12px;border-top:1px solid ' + LINE +
      ';font:12px/1.6 system-ui,sans-serif;color:' + DIM + '">' +
      '<strong style="color:' + INK + '">How every figure here was derived.</strong><br>' +
      '<em>Molecule</em> — ' + esc(IDX.rules.substance) + '<br>' +
      '<em>Brand vs generic</em> — ' + esc(IDX.rules.product) + '<br>' +
      '<em>Naming</em> — ' + esc(IDX.rules.label) + '<br>' +
      '<em>Change</em> — ' + esc(IDX.rules.trend) + '<br>' +
      'Source: <a href="' + esc(src.url) + '" style="color:' + G + '">' + esc(src.name) +
      '</a>. ' + esc(src.attribution) + ' Built ' + esc(IDX.generatedOn) + '.' +
      '</div></div>';
  }

  function suggest(q) {
    var box = document.getElementById('msh-hp-sug');
    q = (q || '').trim().toLowerCase();
    if (q.length < 2) { box.innerHTML = ''; return; }
    /* Brands are matched as well as molecules. A rep types the name on their own
       detail aid, which is the brand, so a molecule-only index answers the primary
       question with "nothing found". The matched brand is shown against the
       molecule it belongs to, because that is the row they will end up reading. */
    var hits = [], i, j, s, via;
    for (i = 0; i < IDX.substances.length && hits.length < 12; i++) {
      s = IDX.substances[i];
      via = null;
      if (s.n.toLowerCase().indexOf(q) === -1) {
        for (j = 0; j < (s.b || []).length; j++) {
          if (s.b[j].toLowerCase().indexOf(q) !== -1) { via = s.b[j]; break; }
        }
        if (!via) { continue; }
      }
      hits.push({ s: s, via: via });
    }
    if (!hits.length) {
      box.innerHTML = '<div style="padding:8px 0;color:' + DIM + ';font:13px system-ui,sans-serif">' +
        'No molecule or brand under that name was dispensed in the community by an ' +
        'English NHS trust in the last ' + IDX.periods.length + ' months. That is not ' +
        'the same as it being unused — this dataset does not see in-hospital use.</div>';
      return;
    }
    box.innerHTML = '<div style="border:1px solid ' + LINE + ';border-radius:4px;margin-top:6px;' +
      'max-width:460px;overflow:hidden">' + hits.map(function (h) {
        var s = h.s;
        return '<button type="button" data-code="' + esc(s.c) + '" ' +
          'style="display:block;width:100%;text-align:left;padding:8px 12px;border:0;' +
          'border-bottom:1px solid ' + LINE + ';background:#fff;cursor:pointer;' +
          'font:14px Georgia,serif;color:' + INK + '">' +
          (h.via ? '<strong>' + esc(h.via) + '</strong> <span style="color:' + DIM +
                   '">in</span> ' + esc(s.n) : esc(s.n)) +
          '<span style="color:' + DIM + ';font-size:12px"> — ' + num(s.i) + ' items, ' +
          s.tr + ' trusts' + (s.g ? '' : ', brand only') + '</span></button>';
      }).join('') + '</div>';
    Array.prototype.forEach.call(box.querySelectorAll('button'), function (b) {
      b.addEventListener('click', function () { open(b.getAttribute('data-code')); });
    });
  }

  function open(code) {
    var meta = null, i;
    for (i = 0; i < IDX.substances.length; i++) {
      if (IDX.substances[i].c === code) { meta = IDX.substances[i]; break; }
    }
    if (!meta) { return; }
    CUR = code;
    document.getElementById('msh-hp-sug').innerHTML = '';
    var out = document.getElementById('msh-hp-out');
    out.innerHTML = '<p style="color:' + DIM + '">Loading ' + esc(meta.n) + '…</p>';
    var ch = meta.ch;
    var p = SHARDS[ch] ? Promise.resolve(SHARDS[ch])
      : get(BASE + 'ch-' + ch + '.json').then(function (d) { SHARDS[ch] = d; return d; });
    p.then(function (shard) {
      if (CUR !== code) { return; }
      out.innerHTML = table(meta, shard.s[code]);
    }).catch(function (e) {
      out.innerHTML = '<p style="color:' + UP + '">Could not load chapter ' + esc(ch) +
        ' (' + esc(e.message) + ').</p>';
    });
  }

  function table(meta, rec) {
    if (!rec) { return '<p style="color:' + DIM + '">No data held for that molecule.</p>'; }
    var n = IDX.periods.length, last = n - 1;
    var segs = rec.p, rows = [], tcode;

    for (tcode in rec.t) {
      if (!Object.prototype.hasOwnProperty.call(rec.t, tcode)) { continue; }
      var by = rec.t[tcode], tot = new Array(n), k, seg, brandLatest = 0, genLatest = 0;
      for (k = 0; k < n; k++) { tot[k] = MISS[k] ? null : 0; }
      for (seg in by) {
        if (!Object.prototype.hasOwnProperty.call(by, seg)) { continue; }
        for (k = 0; k < n; k++) { if (!MISS[k]) { tot[k] += by[seg][k] || 0; } }
        if (seg === 'AA') { genLatest += by[seg][last] || 0; }
        else { brandLatest += by[seg][last] || 0; }
      }
      rows.push({
        code: tcode, name: IDX.trusts[tcode] || tcode, series: tot,
        latest: tot[last], base: tot[BASEI],
        brand: brandLatest, gen: genLatest,
        cost: (rec.c && rec.c[tcode]) ? rec.c[tcode][last] : null,
        by: by
      });
    }
    rows.sort(function (a, b) { return b.latest - a.latest; });
    var shown = rows.slice(0, SHOW);
    var grand = rows.reduce(function (t, r) { return t + r.latest; }, 0);

    var brandNames = Object.keys(segs).filter(function (s) { return s !== 'AA'; })
      .map(function (s) { return segs[s]; });

    var h = '<h3 style="font:600 20px/1.3 Georgia,serif;color:' + INK + ';margin:4px 0 2px">' +
      esc(meta.n) + '</h3>' +
      '<p style="color:' + DIM + ';font:13px system-ui,sans-serif;margin:0 0 14px">' +
      num(grand) + ' items across ' + rows.length + ' trusts in ' +
      esc(periodLabel(IDX.periods[last])) + '. ' +
      (brandNames.length
        ? 'Brands dispensed: ' + esc(brandNames.slice(0, 6).join(', ')) +
          (brandNames.length > 6 ? ' and ' + (brandNames.length - 6) + ' more' : '') + '.'
        : 'No branded presentation dispensed in this window — generic only.') +
      (meta.g ? '' : ' <strong>No generic dispensed in this window.</strong>') +
      /* In chapters 20-23 — appliances, dressings, emollients — a BNF "chemical
         substance" code is really a CATEGORY, and a dozen unrelated brands share
         it. The heading is then the highest-volume presentation, not the molecule,
         and calling it one product would be wrong. Say so on the row rather than
         letting the member infer a single-molecule market that does not exist. */
      (!meta.g && brandNames.length > 3
        ? ' <span style="color:' + DIM + '">This BNF code groups ' + brandNames.length +
          ' separately branded products rather than one molecule, which is normal in ' +
          'appliances and emollients. The heading is the highest-volume presentation.</span>'
        : '') +
      '</p>';

    h += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;' +
      'font:14px/1.4 system-ui,sans-serif">' +
      '<thead><tr style="text-align:left;border-bottom:2px solid ' + LINE + '">' +
      '<th style="padding:7px 8px">Trust</th>' +
      '<th style="padding:7px 8px;text-align:right">Items</th>' +
      '<th style="padding:7px 8px;text-align:right">vs ' + esc(periodLabel(IDX.periods[BASEI])) + '</th>' +
      '<th style="padding:7px 8px">12 months</th>' +
      '<th style="padding:7px 8px;text-align:right">Brand share</th>' +
      '<th style="padding:7px 8px;text-align:right">Cost</th>' +
      '</tr></thead><tbody>';

    shown.forEach(function (r) {
      /* "0%" against a molecule that HAS a brand is ambiguous — it reads as either
         "no brand dispensed" or "the column is broken". A brand present but under
         half a percent is shown as <1%, and a molecule with no branded presentation
         at all gets a dash rather than a zero. */
      var tot = r.brand + r.gen;
      var share;
      if (!brandNames.length) { share = '<span style="color:' + DIM + '">—</span>'; }
      else if (tot <= 0) { share = '<span style="color:' + DIM + '">—</span>'; }
      else if (r.brand === 0) { share = '0%'; }
      else {
        var pc = (r.brand / tot) * 100;
        share = pc < 0.5 ? '&lt;1%' : Math.round(pc) + '%';
      }
      h += '<tr style="border-bottom:1px solid ' + LINE + '">' +
        '<td style="padding:7px 8px">' + esc(r.name) +
        '<div style="color:' + DIM + ';font-size:11px">' + esc(r.code) + '</div></td>' +
        '<td style="padding:7px 8px;text-align:right">' + num(r.latest) + '</td>' +
        '<td style="padding:7px 8px;text-align:right">' + changeCell(r.latest, r.base) + '</td>' +
        '<td style="padding:7px 8px">' + sparkline(r.series) + '</td>' +
        '<td style="padding:7px 8px;text-align:right">' + share + '</td>' +
        '<td style="padding:7px 8px;text-align:right">' + money(r.cost) + '</td>' +
        '</tr>';
    });
    h += '</tbody></table></div>';
    if (rows.length > SHOW) {
      h += '<p style="color:' + DIM + ';font:12px system-ui,sans-serif;margin:8px 0 0">' +
        'Showing the top ' + SHOW + ' of ' + rows.length + ' trusts by volume. ' +
        'The remaining ' + (rows.length - SHOW) + ' are in the data but not printed here.</p>';
    }
    return h;
  }

  /* ---------------------------------------------------------------------- */

  MOUNT.innerHTML = '<p style="color:' + DIM + ';font:15px Georgia,serif">Loading prescribing data…</p>';
  get(BASE + 'index.json').then(function (doc) {
    IDX = doc;
    (IDX.missingPeriods || []).forEach(function (p) {
      var i = IDX.periods.indexOf(p);
      if (i >= 0) { MISS[i] = true; }
    });
    BASEI = 0;
    while (BASEI < IDX.periods.length - 1 && MISS[BASEI]) { BASEI++; }
    MOUNT.innerHTML = shell();
    var q = document.getElementById('msh-hp-q'), t = null;
    q.addEventListener('input', function () {
      clearTimeout(t);
      t = setTimeout(function () { suggest(q.value); }, 120);
    });
  }).catch(function (e) {
    MOUNT.innerHTML = '<p style="color:' + UP + ';font:15px Georgia,serif">' +
      'Prescribing data could not be loaded (' + esc(e.message) + ').</p>';
  });
}());
