/* Medical Sales Intelligence Hub, speciality pages, "longest waits by trust".
   Git-served, same pattern as meeting-prep.js. Mounts into #msh-trust-waits.

   Built 07/09/2026. Why it exists: data/trust-pressures.json carries the median
   RTT wait BY TREATMENT FUNCTION for every trust NHS England publishes one for.
   A rep reading the Urology page is a urology rep, and the question they have is
   "which trusts in my patch have the longest urology waits", which no Hub page
   answered. Meeting Prep could not answer it either: it needs you to name the
   trust first.

   SELF-LIMITING BY DESIGN. NHS England publishes this split for EIGHT treatment
   functions only. The panel renders on the speciality pages that map to one of
   those eight and removes itself silently everywhere else, so the other pages
   are unaffected and nobody has to maintain a per-page list. An unmapped page is
   a page with no data, not a bug.

   THE MAPPING IS EXPLICIT, NEVER FUZZY (root rule 10's reasoning, applied to
   speciality names). A Hub speciality page is only wired to an RTT treatment
   function where the two genuinely describe the same thing. Where a Hub page
   covers more or less than an RTT function, it is left unmapped rather than
   matched on resemblance: "Theatres and Surgical" and "Colorectal, GI and
   Endoscopy" both overlap RTT's "General Surgery" without being it, so neither
   is mapped here. A page that should carry a specific function can say so
   explicitly with data-rtt on the mount, which always wins.

   NOTHING HERE IS DERIVED (root rule 14). The figure shown is NHS England's own
   published median wait for that trust and that treatment function. Ordering a
   published column is presentation, not a derived claim. The panel does not
   score, rank editorially, or call any trust an opportunity. */
(function () {
  var MOUNT = document.getElementById('msh-trust-waits');
  if (!MOUNT) return;

  var GOLD = '#a8842c', INK = '#20303f', LINE = '#e6e2d8', PANEL = '#ffffff', SOFT = '#f7f5ef';
  var MUTED = '#6b7684', BODY = '#39424d';
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var CB = '?cb=' + new Date().toISOString().slice(0, 10);
  var PRESSURES = BASE + 'data/trust-pressures.json' + CB;

  /* Hub speciality page name -> RTT treatment function, exact matches only.
     Keys are lower-cased Hub page names with "and"/"&" normalised. */
  var MAP = {
    'orthopaedics and trauma': 'Trauma & Orthopaedics',
    'trauma and orthopaedics': 'Trauma & Orthopaedics',
    'cardiology and cardiac surgery': 'Cardiology',
    'cardiology': 'Cardiology',
    'gynaecology and womens health': 'Gynaecology',
    'gynaecology': 'Gynaecology',
    'urology': 'Urology',
    'ent and head and neck': 'ENT (Ear, Nose & Throat)',
    'ent': 'ENT (Ear, Nose & Throat)',
    'ophthalmology': 'Ophthalmology',
    'dermatology': 'Dermatology',
    'general surgery': 'General Surgery'
  };

  function norm(s) {
    return String(s || '')
      .toLowerCase()
      .replace(/[’']/g, '')
      .replace(/&/g, 'and')
      .replace(/[^a-z ]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // An explicit data-rtt always wins over the name lookup.
  var explicit = MOUNT.getAttribute('data-rtt');
  var specName = MOUNT.getAttribute('data-speciality') || '';
  var rttKey = explicit || MAP[norm(specName)] || null;

  if (!rttKey) {
    // Not one of the eight NHS England publishes. Remove the mount entirely so
    // the page shows no empty heading and no "coming soon" promise.
    MOUNT.parentNode && MOUNT.parentNode.removeChild(MOUNT);
    return;
  }

  MOUNT.innerHTML = '<div style="font-size:13px;color:' + MUTED + ';padding:10px 0;">Loading trust waiting times…</div>';

  fetch(PRESSURES).then(function (r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function (d) {
    render(d);
  }).catch(function (e) {
    MOUNT.innerHTML = '<div style="background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:14px 16px;font-size:13.5px;color:' + BODY + ';">'
      + 'Trust waiting times could not be loaded just now (' + esc(e.message) + '). This is a loading problem, not missing data. Refresh to try again.</div>';
  });

  function render(d) {
    var raw = d.trusts || {};
    var rows = [];
    if (Object.prototype.toString.call(raw) === '[object Array]') {
      rows = raw.slice();
    } else {
      Object.keys(raw).forEach(function (k) {
        var v = raw[k];
        if (v && typeof v === 'object') { v = Object.assign({}, v); v.code = v.code || k; rows.push(v); }
      });
    }

    // Only trusts with a published median for THIS treatment function.
    rows = rows.map(function (t) {
      var spec = t.spec || {};
      return { name: t.name, region: t.region, code: t.code, wait: spec[rttKey], wl: t.wl, pct18: t.pct18 };
    }).filter(function (t) { return t.wait != null; });

    if (!rows.length) {
      MOUNT.parentNode && MOUNT.parentNode.removeChild(MOUNT);
      return;
    }

    var rtt = (d.sources && d.sources.rtt) || {};
    var period = (d.periods && d.periods.rtt) || 'not stated';
    var asOf = d.asOf || 'not stated';
    var nat = d.national || {};

    var regions = {};
    rows.forEach(function (t) { if (t.region) regions[t.region] = true; });
    var regionList = Object.keys(regions).sort();

    var state = { region: 'all', limit: 15 };

    var wrap = document.createElement('div');
    wrap.style.cssText = 'font-family:inherit;color:' + INK + ';';

    var head = document.createElement('div');
    head.style.cssText = 'background:' + PANEL + ';border:1px solid ' + LINE + ';border-left:3px solid ' + GOLD + ';border-radius:10px;padding:14px 16px;margin:0 0 12px;';
    head.innerHTML =
      '<div style="font-size:15px;font-weight:800;">Median wait for ' + esc(rttKey) + ', by trust</div>'
      + '<div style="font-size:12px;color:' + MUTED + ';margin:4px 0 0;">'
      + 'NHS England\'s own published median wait in weeks for this treatment function, RTT period ' + esc(period) + ', for the '
      + rows.length + ' trusts it publishes one for. Longest first. Nothing here is scored or interpreted, and a long wait is a '
      + 'fact about the trust\'s position, not a judgement about the trust.'
      + (nat.pct18 != null ? ' For context, ' + esc(String(nat.pct18)) + '% of the England waiting list was within 18 weeks in the same period, against the 92% constitutional standard.' : '')
      + '</div>';
    wrap.appendChild(head);

    var ctl = document.createElement('div');
    ctl.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px;';
    var selHtml = '<option value="all">All regions (' + rows.length + ' trusts)</option>';
    regionList.forEach(function (r) {
      var n = rows.filter(function (t) { return t.region === r; }).length;
      selHtml += '<option value="' + esc(r) + '">' + esc(r) + ' (' + n + ')</option>';
    });
    ctl.innerHTML =
      '<select id="mshtw-region" style="padding:7px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13px;background:' + PANEL + ';color:' + INK + ';">' + selHtml + '</select>'
      + '<button id="mshtw-all" type="button" style="padding:7px 12px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13px;background:' + PANEL + ';color:' + INK + ';cursor:pointer;">Show all trusts</button>';
    wrap.appendChild(ctl);

    var out = document.createElement('div');
    wrap.appendChild(out);

    var foot = document.createElement('div');
    foot.style.cssText = 'margin-top:12px;padding-top:10px;border-top:1px solid ' + LINE + ';font-size:12px;color:' + MUTED + ';line-height:1.6;';
    foot.innerHTML =
      'Source: ' + (rtt.url
        ? '<a href="' + esc(rtt.url) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';">' + esc(rtt.label || 'NHS England RTT waiting times') + '</a>'
        : esc(rtt.label || 'NHS England RTT waiting times'))
      + ', period ' + esc(period) + '. Snapshot taken into the Hub on ' + esc(asOf) + '. '
      + 'Trusts NHS England does not publish a ' + esc(rttKey) + ' median for are not listed.';
    wrap.appendChild(foot);

    MOUNT.innerHTML = '';
    MOUNT.appendChild(wrap);

    function draw() {
      var list = rows.filter(function (t) {
        return state.region === 'all' || t.region === state.region;
      });
      list.sort(function (a, b) { return b.wait - a.wait; });
      var shown = list.slice(0, state.limit);

      if (!shown.length) {
        out.innerHTML = '<div style="background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:14px 16px;font-size:13.5px;color:' + BODY + ';">No trust in that region has a published ' + esc(rttKey) + ' median for this period.</div>';
        return;
      }

      var h = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;min-width:520px;">'
        + '<thead><tr style="text-align:left;border-bottom:2px solid ' + LINE + ';">'
        + '<th style="padding:8px 6px;color:' + MUTED + ';font-weight:700;">Trust</th>'
        + '<th style="padding:8px 6px;color:' + MUTED + ';font-weight:700;">Region</th>'
        + '<th style="padding:8px 6px;color:' + MUTED + ';font-weight:700;text-align:right;">Median wait</th>'
        + '<th style="padding:8px 6px;color:' + MUTED + ';font-weight:700;text-align:right;">Whole waiting list</th>'
        + '</tr></thead><tbody>';
      shown.forEach(function (t, i) {
        h += '<tr style="border-bottom:1px solid ' + LINE + ';background:' + (i % 2 ? SOFT : PANEL) + ';">'
          + '<td style="padding:8px 6px;color:' + INK + ';font-weight:600;">' + esc(t.name || t.code || 'Unnamed trust') + '</td>'
          + '<td style="padding:8px 6px;color:' + MUTED + ';">' + esc(t.region || 'not stated') + '</td>'
          + '<td style="padding:8px 6px;text-align:right;color:' + BODY + ';"><strong>' + esc(String(t.wait)) + '</strong> weeks</td>'
          + '<td style="padding:8px 6px;text-align:right;color:' + BODY + ';">' + (t.wl != null ? Number(t.wl).toLocaleString('en-GB') : 'not published') + '</td>'
          + '</tr>';
      });
      h += '</tbody></table></div>'
        + '<div style="font-size:12px;color:' + MUTED + ';margin-top:8px;">Showing ' + shown.length + ' of ' + list.length + ' trusts with a published ' + esc(rttKey) + ' median.</div>';
      out.innerHTML = h;
    }

    document.getElementById('mshtw-region').addEventListener('change', function () { state.region = this.value; draw(); });
    document.getElementById('mshtw-all').addEventListener('click', function () {
      state.limit = state.limit === 15 ? 1e6 : 15;
      this.textContent = state.limit === 15 ? 'Show all trusts' : 'Show top 15 only';
      draw();
    });

    draw();
  }
})();
