/* Medical Sales Intelligence Hub, Capital & Estates Watch, trust-level panel.
   Git-served, same pattern as meeting-prep.js. Mounts into #msh-trust-capital.

   Built 07/09/2026. Why it exists: data/trust-pressures.json has carried ERIC
   backlog maintenance and capital equipment spend for 147 trusts since August,
   and the only thing reading it was meeting-prep.js, one trust at a time. A rep
   on Capital & Estates Watch wants the opposite view: which trusts, across a
   region, are carrying the biggest high-risk backlog and spending the most on
   equipment.

   NOTHING HERE IS DERIVED (root rule 14). Every number is ERIC's own figure for
   that trust, copied through unchanged. Sorting and filtering a published column
   is presentation, not a derived claim, so no rule statement or evidence floor is
   needed. The panel never ranks trusts by an opinion, never scores them, and
   never says "the worst" or "the biggest opportunity". It shows the publisher's
   figure with the publisher's period attached and lets the rep judge.

   Reads data/trust-pressures.json only. It does NOT read the layer-2 profiles in
   prep-config.json, so it is unaffected by the trust-profile refresh cycle. */
(function () {
  var MOUNT = document.getElementById('msh-trust-capital');
  if (!MOUNT) return;

  var GOLD = '#a8842c', INK = '#20303f', LINE = '#e6e2d8', PANEL = '#ffffff', SOFT = '#f7f5ef';
  var MUTED = '#6b7684', BODY = '#39424d';
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  // Daily cache-buster, matching hub-search.js and meeting-prep.js.
  var CB = '?cb=' + new Date().toISOString().slice(0, 10);
  var PRESSURES = BASE + 'data/trust-pressures.json' + CB;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // £ with thousands separators. ERIC publishes whole pounds.
  function gbp(n) {
    if (n == null || isNaN(n)) return 'not published';
    return '£' + Math.round(n).toLocaleString('en-GB');
  }
  // Compact form for the headline totals only.
  function gbpBig(n) {
    if (n == null || isNaN(n)) return 'not published';
    if (n >= 1e9) return '£' + (n / 1e9).toFixed(2) + 'bn';
    if (n >= 1e6) return '£' + (n / 1e6).toFixed(1) + 'm';
    return gbp(n);
  }

  MOUNT.innerHTML = '<div style="font-size:13px;color:' + MUTED + ';padding:10px 0;">Loading trust capital and estates figures…</div>';

  fetch(PRESSURES).then(function (r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function (d) {
    render(d);
  }).catch(function (e) {
    // Honest empty state. Never a silent blank panel.
    MOUNT.innerHTML = '<div style="background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:14px 16px;font-size:13.5px;color:' + BODY + ';">'
      + 'The trust capital and estates figures could not be loaded just now (' + esc(e.message) + '). '
      + 'Nothing is missing from the underlying data, this is a loading problem. Refresh the page to try again.</div>';
  });

  function render(d) {
    var raw = d.trusts || {};
    var rows = [];
    // trusts may be keyed by ODS code or be a plain array; handle both.
    if (Object.prototype.toString.call(raw) === '[object Array]') {
      rows = raw.slice();
    } else {
      Object.keys(raw).forEach(function (k) {
        var v = raw[k];
        if (v && typeof v === 'object') { v = Object.assign({}, v); v.code = v.code || k; rows.push(v); }
      });
    }
    // Only trusts ERIC actually covers. A trust with no figure gets no row,
    // rather than a row reading zero, which would be a false statement.
    rows = rows.filter(function (t) { return t.backlogHi != null || t.capEq != null; });

    var eric = (d.sources && d.sources.eric) || {};
    var ericPeriod = (d.periods && d.periods.eric) || 'not stated';
    var asOf = d.asOf || 'not stated';

    var regions = {};
    rows.forEach(function (t) { if (t.region) regions[t.region] = true; });
    var regionList = Object.keys(regions).sort();

    var state = { region: 'all', sort: 'backlogHi', q: '' };

    var wrap = document.createElement('div');
    wrap.style.cssText = 'font-family:inherit;color:' + INK + ';';

    // Headline totals. These are sums of the publisher's own per-trust figures,
    // which is arithmetic on published data, not a derived editorial claim. The
    // count of trusts is stated alongside so the total cannot be mistaken for
    // an England-wide figure: ERIC covers more trusts than the Hub holds RTT for.
    var totBacklog = 0, totCap = 0, nB = 0, nC = 0;
    rows.forEach(function (t) {
      if (t.backlogHi != null) { totBacklog += t.backlogHi; nB++; }
      if (t.capEq != null) { totCap += t.capEq; nC++; }
    });

    var head = document.createElement('div');
    head.style.cssText = 'background:' + PANEL + ';border:1px solid ' + LINE + ';border-left:3px solid ' + GOLD + ';border-radius:10px;padding:14px 16px;margin:0 0 12px;';
    head.innerHTML =
      '<div style="font-size:15px;font-weight:800;">Backlog maintenance and equipment spend, by trust</div>'
      + '<div style="font-size:12px;color:' + MUTED + ';margin:4px 0 10px;">'
      + 'Every figure is NHS Digital ERIC\'s own return for that trust for ' + esc(ericPeriod) + ', copied through unchanged. '
      + 'Nothing on this panel is ranked, scored or interpreted.</div>'
      + '<div style="display:flex;flex-wrap:wrap;gap:18px;font-size:13.5px;color:' + BODY + ';">'
      + '<div><strong style="font-size:18px;color:' + INK + ';">' + gbpBig(totBacklog) + '</strong><br>'
      + '<span style="color:' + MUTED + ';">high and significant-risk backlog maintenance, across ' + nB + ' trusts</span></div>'
      + '<div><strong style="font-size:18px;color:' + INK + ';">' + gbpBig(totCap) + '</strong><br>'
      + '<span style="color:' + MUTED + ';">capital investment in equipment, across ' + nC + ' trusts</span></div>'
      + '</div>';
    wrap.appendChild(head);

    // Controls
    var ctl = document.createElement('div');
    ctl.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px;';
    var selHtml = '<option value="all">All regions (' + rows.length + ' trusts)</option>';
    regionList.forEach(function (r) {
      var n = rows.filter(function (t) { return t.region === r; }).length;
      selHtml += '<option value="' + esc(r) + '">' + esc(r) + ' (' + n + ')</option>';
    });
    ctl.innerHTML =
      '<select id="mshtc-region" style="padding:7px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13px;background:' + PANEL + ';color:' + INK + ';">' + selHtml + '</select>'
      + '<select id="mshtc-sort" style="padding:7px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13px;background:' + PANEL + ';color:' + INK + ';">'
      + '<option value="backlogHi">Sort: highest backlog maintenance</option>'
      + '<option value="capEq">Sort: highest equipment spend</option>'
      + '<option value="name">Sort: trust name (A to Z)</option>'
      + '</select>'
      + '<input id="mshtc-q" type="search" placeholder="Find a trust" style="padding:7px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13px;min-width:180px;background:' + PANEL + ';color:' + INK + ';">';
    wrap.appendChild(ctl);

    var out = document.createElement('div');
    wrap.appendChild(out);

    // Provenance. Root rule 12: no figure without a source, no source without
    // the period it applies to.
    var foot = document.createElement('div');
    foot.style.cssText = 'margin-top:12px;padding-top:10px;border-top:1px solid ' + LINE + ';font-size:12px;color:' + MUTED + ';line-height:1.6;';
    foot.innerHTML =
      'Source: ' + (eric.url
        ? '<a href="' + esc(eric.url) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';">' + esc(eric.label || 'NHS Digital ERIC') + '</a>'
        : esc(eric.label || 'NHS Digital ERIC'))
      + ', collection period ' + esc(ericPeriod) + '. '
      + 'Snapshot taken into the Hub on ' + esc(asOf) + '. '
      + 'Trusts ERIC does not publish a figure for are not listed, rather than shown as zero.';
    wrap.appendChild(foot);

    MOUNT.innerHTML = '';
    MOUNT.appendChild(wrap);

    function draw() {
      var list = rows.filter(function (t) {
        if (state.region !== 'all' && t.region !== state.region) return false;
        if (state.q && String(t.name || '').toLowerCase().indexOf(state.q) === -1) return false;
        return true;
      });
      list.sort(function (a, b) {
        if (state.sort === 'name') return String(a.name || '').localeCompare(String(b.name || ''));
        var av = a[state.sort], bv = b[state.sort];
        if (av == null) return 1;
        if (bv == null) return -1;
        return bv - av;
      });

      if (!list.length) {
        out.innerHTML = '<div style="background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:14px 16px;font-size:13.5px;color:' + BODY + ';">No trust matches that filter. Clear the search or pick another region.</div>';
        return;
      }

      var h = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;min-width:560px;">'
        + '<thead><tr style="text-align:left;border-bottom:2px solid ' + LINE + ';">'
        + '<th style="padding:8px 6px;color:' + MUTED + ';font-weight:700;">Trust</th>'
        + '<th style="padding:8px 6px;color:' + MUTED + ';font-weight:700;">Region</th>'
        + '<th style="padding:8px 6px;color:' + MUTED + ';font-weight:700;text-align:right;">High-risk backlog</th>'
        + '<th style="padding:8px 6px;color:' + MUTED + ';font-weight:700;text-align:right;">Equipment spend</th>'
        + '</tr></thead><tbody>';
      list.forEach(function (t, i) {
        h += '<tr style="border-bottom:1px solid ' + LINE + ';background:' + (i % 2 ? SOFT : PANEL) + ';">'
          + '<td style="padding:8px 6px;color:' + INK + ';font-weight:600;">' + esc(t.name || t.code || 'Unnamed trust') + '</td>'
          + '<td style="padding:8px 6px;color:' + MUTED + ';">' + esc(t.region || 'not stated') + '</td>'
          + '<td style="padding:8px 6px;text-align:right;color:' + BODY + ';">' + gbp(t.backlogHi) + '</td>'
          + '<td style="padding:8px 6px;text-align:right;color:' + BODY + ';">' + gbp(t.capEq) + '</td>'
          + '</tr>';
      });
      h += '</tbody></table></div>'
        + '<div style="font-size:12px;color:' + MUTED + ';margin-top:8px;">Showing ' + list.length + ' of ' + rows.length + ' trusts.</div>';
      out.innerHTML = h;
    }

    document.getElementById('mshtc-region').addEventListener('change', function () { state.region = this.value; draw(); });
    document.getElementById('mshtc-sort').addEventListener('change', function () { state.sort = this.value; draw(); });
    document.getElementById('mshtc-q').addEventListener('input', function () { state.q = this.value.trim().toLowerCase(); draw(); });

    draw();
  }
})();
