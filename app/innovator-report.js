/* Medical Sales Intelligence Hub — Innovator Market Analysis Report. Mounts on #msh-innovator-report.

   WHAT IT IS. An early-stage innovator picks their speciality, product type, stage,
   geography and purpose, and gets one exportable market-analysis report: eight
   sections, the innovator's own claim in their words and the NHS evidence beside it,
   every factual row carrying its source link and the date that source was read.
   "Save edited copy" downloads the report as it now stands; "Print or save as PDF"
   prints it to A4. Built for a grant funding application or an investment deck.

   BUILT THE WAY app/icb-pack.js IS BUILT, and for the same reason: the Hub has no PDF
   library and does not need one. The report is rendered client-side from the repo's
   own JSON, the fields the innovator fills in are contenteditable, and the export is
   a Blob download plus window.print(). No jspdf, no html2pdf, no server-side render.

   THE ONE RULE THIS FILE EXISTS TO KEEP. A grant assessor reading the printed PDF
   must be able to tell, without being told, which lines are the innovator's claim and
   which are the Hub's evidence. So every block the innovator writes sits inside a
   .mine box that carries its own header strip — YOUR WORDS, named to their
   organisation, "not verified by the Medical Sales Intelligence Hub" — and that strip
   prints. Every Hub row carries a source link and an "as read on" date. Nothing is
   inferred, nothing is averaged into a score, and where a source could not be read
   the report says so and prints the last good reading the Hub holds, with its date,
   rather than dropping the section.

   WHERE THE FIGURES COME FROM.
     data/innovator-report.json   built by scripts/build_innovator_report.py: the
                                  competitor set and its award history, the framework
                                  rows, the Stakeholder Mapper's role library, the
                                  digital arm, and every source file's own as-of date
     data/products.json           speciality list, product and problem list, framework
                                  family, national priority, Clinical Evidence Library
     data/icb-watch.json          Integrated Care Board (ICB) list, leaders and changes
     data/open-tenders.json       open tender notices (Find a Tender, Contracts Finder)
     data/pending-awards.json     awards published but not yet started
     data/trust-pressures.json    Referral to Treatment (RTT) waits, by speciality

   Any one of those five secondary files can fail to load without taking the report
   with it: the section says which file could not be read and what the Hub last held. */
(function () {
  var MOUNT = document.getElementById('msh-innovator-report');
  if (!MOUNT) return;

  var NAVY = '#0B1C33', DEEP = '#14304F', GOLD = '#A8842C', GOLDL = '#E0BE8E',
      INK = '#1D2733', WARM = '#EDE7DC', WINE = '#4A1526';
  var RAW = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/';
  var CB = '?cb=' + new Date().toISOString().slice(0, 10);
  var NV = 'Not verified';
  var HUB = 'https://medsalesintelligencehub.co.uk/medical-sales-hub/';

  /* Product types. `tpl` is the Stakeholder Mapper template key this product type
     maps onto (data/innovator-report.json carries the mapper's own templates);
     `digital` turns on the digital route and the digital competitor set. */
  var TYPES = [
    { id: 'consumable', label: 'Consumable', tpl: 'con', digital: false },
    { id: 'device', label: 'Device (single-use or reusable)', tpl: 'dev', digital: false },
    { id: 'capital', label: 'Capital equipment', tpl: 'cap', digital: false },
    { id: 'software', label: 'Software or digital service', tpl: 'proc', digital: true },
    { id: 'diagnostic', label: 'Diagnostic (test or assay)', tpl: 'micro', digital: false },
    { id: 'diagnostic-sw', label: 'Diagnostic software or algorithm', tpl: 'micro', digital: true },
    { id: 'service', label: 'Service or pathway redesign', tpl: 'proc', digital: false },
    { id: 'medicine', label: 'Medicine or prescribable product', tpl: 'rx', digital: false }
  ];

  var STAGES = [
    { id: 'idea', label: 'Idea' },
    { id: 'prototype', label: 'Prototype' },
    { id: 'evidence', label: 'First evidence' },
    { id: 'first-site', label: 'First NHS site' },
    { id: 'scaling', label: 'Scaling' }
  ];

  /* Purpose changes the emphasis line at the head of each section — what the reader
     is actually testing — and nothing else. The sections, and their order, are the
     same either way: a report whose contents move about is a report an assessor
     cannot follow back to a previous version. */
  var PURPOSES = [
    { id: 'grant', label: 'Grant funding application' },
    { id: 'investment', label: 'Investment deck' }
  ];

  var EMPHASIS = {
    grant: {
      2: 'A grant assessor is testing whether the problem is real, sized and someone else’s published figure, not yours.',
      3: 'A grant assessor is testing whether you know who already holds this ground, because an unmet need with four incumbents is not an unmet need.',
      4: 'A grant assessor is testing whether there is a lawful route to a paying NHS customer at the end of the project.',
      5: 'A grant assessor is testing whether you know who has to say yes, by role, not by name.',
      6: 'A grant assessor is testing whether the market is moving now, or whether you are describing it from a year-old report.',
      7: 'This is the paragraph the assessor scores. Everything above it is the evidence it has to survive.'
    },
    investment: {
      2: 'An investor is testing the size of the prize and whether the figure comes from somewhere they can check.',
      3: 'An investor is testing who you displace, how entrenched they are, and what their NHS contract history says about how hard that will be.',
      4: 'An investor is testing time to revenue: which framework, when it reopens, and what happens if you miss that window.',
      5: 'An investor is testing length of sales cycle: how many people have to agree before money moves.',
      6: 'An investor is testing whether there is live demand they can see for themselves.',
      7: 'This is the slide. Everything above it is why it is credible.'
    }
  };

  var CSS = '.inr{font:15px/1.55 Georgia,serif;color:' + INK + '}.inr *{box-sizing:border-box}'
    + '.inr .band{padding:28px 0}.inr .dark{background:' + NAVY + ';color:#F5F1E8}'
    + '.inr .wine{background:' + WINE + ';color:#F5F1E8}.inr .warm{background:' + WARM + '}'
    + '.inr .col{max-width:none;margin:0;padding:0 40px}@media(max-width:600px){.inr .col{padding:0 20px}}'
    + '.inr h1,.inr h2{font-family:Didot,"Bodoni 72",Georgia,serif;margin:0 0 10px}'
    + '.inr h1{font-size:32px;line-height:1.15}.inr h2{font-size:25px;color:' + NAVY + '}'
    + '.inr h3{font:700 15px Helvetica,Arial,sans-serif;color:' + NAVY + ';margin:18px 0 6px}'
    + '.inr .dark h1,.inr .dark h2,.inr .dark h3,.inr .dark p,.inr .dark label,.inr .dark span,.inr .dark li,.inr .dark td,.inr .dark th,'
    + '.inr .wine h1,.inr .wine h2,.inr .wine h3,.inr .wine p,.inr .wine label,.inr .wine span,.inr .wine li{color:#F5F1E8}'
    + 'body .wp-site-blocks .inr .dark h1,body .wp-site-blocks .inr .dark h2,body .wp-site-blocks .inr .dark h3,body .wp-site-blocks .inr .dark p,'
    + 'body .wp-site-blocks .inr .dark label,body .wp-site-blocks .inr .dark span,body .wp-site-blocks .inr .dark li,'
    + 'body .wp-site-blocks .inr .wine h1,body .wp-site-blocks .inr .wine h2,body .wp-site-blocks .inr .wine p,'
    + 'body .wp-site-blocks .inr .wine span,body .wp-site-blocks .inr .wine li{color:#F5F1E8!important}'
    + 'body .wp-site-blocks .inr .dark .eyebrow,body .wp-site-blocks .inr .wine .eyebrow,body .wp-site-blocks .inr .dark .nv{color:' + GOLDL + '!important}'
    + '.inr .eyebrow{font:700 12px/1.3 Helvetica,Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:' + NAVY + ';margin-bottom:8px}'
    + '.inr .dark .eyebrow,.inr .wine .eyebrow{color:' + GOLDL + '}'
    + '.inr .emph{font:italic 14px/1.5 Georgia,serif;color:' + DEEP + ';border-left:4px solid ' + GOLD + ';padding:2px 0 2px 12px;margin:0 0 14px}'
    + '.inr table{border-collapse:collapse;width:100%;font:13px/1.45 Helvetica,Arial,sans-serif;margin:6px 0}'
    + '.inr th,.inr td{padding:6px 8px;border-bottom:1px solid #d8d2c4;text-align:left;vertical-align:top}'
    + '.inr tr:nth-child(even) td{background:rgba(255,255,255,.55)}.inr .warm tr:nth-child(even) td{background:rgba(255,255,255,.45)}'
    + '.inr th{background:' + DEEP + ';color:#fff;font-weight:700}.inr td.n,.inr th.n{text-align:right;white-space:nowrap}'
    + '.inr a{color:' + DEEP + '}.inr .dark a,.inr .wine a{color:' + GOLDL + '}'
    + '.inr .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:14px 0 18px}'
    + '.inr .kpi{background:#fff;border:1px solid #d8d2c4;border-top:4px solid ' + GOLD + ';padding:12px 14px;'
    + 'box-shadow:0 1px 2px rgba(14,27,48,.06);break-inside:avoid}'
    + '.inr .kpi b{display:block;font:700 26px/1.15 Georgia,serif;color:' + NAVY + ';margin-bottom:4px}'
    + '.inr .kpi span{font:12px/1.45 Helvetica,Arial,sans-serif;display:block;color:#39424d}'
    /* Section heads: a numbered badge so a reader can find "section 4" in a printed copy. */
    + '.inr h2 .sn{display:inline-block;min-width:1.6em;height:1.6em;line-height:1.6em;text-align:center;'
    + 'background:' + NAVY + ';color:' + GOLDL + ';border-radius:50%;font:700 17px/1.6em Helvetica,Arial,sans-serif;'
    + 'margin-right:12px;vertical-align:4px}'
    + '.inr .dark h2 .sn,.inr .wine h2 .sn{background:' + GOLD + ';color:#fff}'
    + '.inr .band>.col>.eyebrow{display:inline-block;border-bottom:2px solid ' + GOLD + ';padding-bottom:4px}'
    /* At a glance: the five picks, read back as the figures each section will show. */
    + '.inr .glance{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:20px 0 6px}'
    + '.inr .gl{display:block;text-decoration:none;background:rgba(255,255,255,.06);border:1px solid rgba(224,190,142,.35);'
    + 'border-left:4px solid ' + GOLD + ';padding:12px 14px;transition:background .15s}'
    + '.inr .gl:hover{background:rgba(255,255,255,.12)}'
    + '.inr .dark .gl b{display:block;font:700 24px/1.2 Georgia,serif;color:' + GOLDL + '!important;margin-bottom:4px}'
    + '.inr .dark .gl span{display:block;font:12px/1.45 Helvetica,Arial,sans-serif;color:#F5F1E8}'
    + '.inr .dark .gl i{display:block;font:700 10px/1.3 Helvetica,Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;'
    + 'font-style:normal;color:' + GOLDL + '!important;margin-top:8px}'
    + '.inr .toc{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 0;padding:0;list-style:none}'
    + '.inr .toc a{display:inline-block;font:700 12px/1 Helvetica,Arial,sans-serif;color:#F5F1E8;text-decoration:none;'
    + 'border:1px solid rgba(224,190,142,.5);border-radius:20px;padding:8px 12px}'
    + '.inr .toc a:hover{background:' + GOLD + ';border-color:' + GOLD + '}'
    + '.inr .more-rows{display:none}.inr .showall .more-rows{display:table-row}'
    + '.inr .tgl{background:#fff;color:' + DEEP + ';border:1px solid ' + DEEP + ';font:700 13px Helvetica,Arial,sans-serif;padding:8px 14px;margin:8px 0 0}'
    + '.inr .soft{color:#8a8578;font-style:italic}'
    + '@media(max-width:640px){.inr h1{font-size:26px}.inr h2{font-size:21px}'
    + '.inr table.stack,.inr table.stack tbody,.inr table.stack tr,.inr table.stack td{display:block;width:100%}'
    + '.inr table.stack tr:first-child{display:none}'
    + '.inr table.stack tr{border:1px solid #d8d2c4;background:#fff;margin:0 0 10px;padding:6px 10px}'
    + '.inr table.stack td{border:0;padding:4px 0;text-align:left!important;white-space:normal!important}'
    + '.inr table.stack td[data-label]:before{content:attr(data-label);display:block;font:700 10px/1.4 Helvetica,Arial,sans-serif;'
    + 'letter-spacing:.08em;text-transform:uppercase;color:#6b6556}'
    + '.inr table.stack tr.more-rows{display:none}.inr .showall table.stack tr.more-rows{display:block}.inr .scroll{overflow:visible}}'
    + '.inr .nv{color:#7A1F1F;font-weight:700}.inr .dark .nv{color:' + GOLDL + '}'
    + '.inr .src{font:11px/1.4 Helvetica,Arial,sans-serif;color:#39424d}'
    + '.inr .note{font:12px/1.55 Helvetica,Arial,sans-serif;color:#39424d}'
    + '.inr .scroll{overflow-x:auto}'
    /* Regional support cards (section 5). */
    + '.inr .rg{margin:22px 0 8px;padding-top:6px;border-top:1px solid #d8d2c4}'
    + '.inr .rg-h{font:700 12px/1.3 Helvetica,Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;'
    + 'color:' + DEEP + ';margin:20px 0 10px}'
    + '.inr .rg-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}'
    + '.inr .rg-card{background:#fff;border:1px solid #d8d2c4;border-top:4px solid ' + DEEP + ';padding:14px 16px 12px;'
    + 'display:flex;flex-direction:column;break-inside:avoid;page-break-inside:avoid;'
    + 'box-shadow:0 1px 2px rgba(14,27,48,.06);transition:box-shadow .15s,transform .15s}'
    + '.inr .rg-card:hover{box-shadow:0 6px 18px rgba(14,27,48,.12);transform:translateY(-2px)}'
    + '.inr .rg-hit{border-top-color:' + GOLD + ';background:#FFFCF4}'
    + '.inr .rg-case{border-top-color:' + WINE + '}.inr .rg-case.rg-hit{border-top-color:' + GOLD + '}'
    + '.inr .rg-kind{font:700 10px/1.3 Helvetica,Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:#6b6556}'
    + '.inr .rg-chip{align-self:flex-start;margin-top:6px;font:700 10px/1 Helvetica,Arial,sans-serif;letter-spacing:.06em;'
    + 'text-transform:uppercase;background:' + GOLD + ';color:#fff;padding:5px 8px;border-radius:2px}'
    + '.inr .rg-name{font:700 16px/1.3 Georgia,serif;color:' + NAVY + ';margin:8px 0 6px}'
    + '.inr .rg-what{font:13px/1.5 Helvetica,Arial,sans-serif;color:#39424d;margin:0 0 10px;flex:1}'
    + '.inr .rg-go{font:700 12px/1.4 Helvetica,Arial,sans-serif}.inr .rg-go a{text-decoration:none;border-bottom:1px solid ' + GOLD + '}'
    + '@media print{.inr .rg-card{box-shadow:none;transform:none}.inr .rg-grid{grid-template-columns:1fr 1fr}}'
    /* The innovator's own words. The header strip is the whole point and it prints. */
    + '.inr .mine{border:2px dashed ' + GOLD + ';background:#fff;margin:10px 0 4px}'
    + '.inr .mine>.lab{font:700 11px/1.4 Helvetica,Arial,sans-serif;letter-spacing:.1em;text-transform:uppercase;'
    + 'background:' + GOLD + ';color:#fff;padding:5px 10px}'
    + '.inr .mine>.ask{font:12px/1.5 Helvetica,Arial,sans-serif;color:#39424d;padding:8px 12px 0}'
    + '.inr .mine>.w{padding:10px 12px 12px;min-height:72px;outline:none}'
    + '.inr .mine>.w:empty:before{content:attr(data-ph);color:#8a8578;font-style:italic}'
    /* Hub evidence. The strip is the counterpart, so the two never read as one voice. */
    + '.inr .ev{border-left:4px solid ' + DEEP + ';padding-left:12px;margin:10px 0}'
    + '.inr .evlab{font:700 11px/1.4 Helvetica,Arial,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:' + DEEP + ';margin-bottom:6px}'
    + '.inr .gap{border:2px solid #7A1F1F;background:#FBF4F4;padding:10px 12px;margin:10px 0;font:13px/1.55 Helvetica,Arial,sans-serif}'
    + '.inr button{background:' + DEEP + ';color:#fff;border:1px solid ' + GOLDL + ';padding:10px 18px;'
    + 'font:14px Helvetica,Arial,sans-serif;cursor:pointer;margin:0 8px 8px 0}'
    + '.inr select,.inr input{font:14px Helvetica,Arial,sans-serif;padding:8px;color:' + INK + ';background:#fff;'
    + 'border:1px solid ' + GOLD + ';max-width:100%;width:100%}'
    + '.inr label{font:700 12px Helvetica,Arial,sans-serif;display:block;margin-bottom:4px}'
    + '.inr .pick{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:16px 0}'
    + '.inr .foot{font:12px/1.6 Helvetica,Arial,sans-serif}'
    + '@media print{.inr .pick,.inr button,.inr .noprint{display:none!important}'
    + '.inr .band{padding:14px 0}.inr .kpis,.inr .glance,.inr .rg-grid{break-inside:avoid}.inr .col{max-width:none;padding:0 10mm}'
    + '.inr .dark,.inr .wine,.inr .warm,.inr .mine>.lab,.inr th{-webkit-print-color-adjust:exact;print-color-adjust:exact}'
    /* The .ask line coaches the innovator while they write. It is not content a grant
       assessor should read, so it stays on screen and in the saved copy (which is still
       editable) but drops out of the print. Not .noprint: save() strips those outright. */
    + '.inr .mine>.ask{display:none}'
    + '.inr h2{break-after:avoid}.inr table{font-size:10pt}.inr a{text-decoration:none}'
    + '.inr .mine{break-inside:avoid}.inr .more-rows{display:table-row!important}'
    + '.inr .kpi,.inr .gl{box-shadow:none;-webkit-print-color-adjust:exact;print-color-adjust:exact}'
    + '.inr .toc,.inr .tgl{display:none!important}.inr tr{break-inside:avoid}}';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function q(name) { return new URLSearchParams(location.search).get(name) || ''; }
  function clean(s) { return String(s || '').replace(/[^A-Za-z0-9 .,&'()-]/g, '').slice(0, 90); }
  function num(x) { return x == null ? '<span class="nv">' + NV + '</span>' : Number(x).toLocaleString('en-GB'); }
  function money(x) {
    if (x == null) return '<span class="nv">' + NV + '</span>';
    return '£' + Math.round(x).toLocaleString('en-GB');
  }
  function ukdate(iso) {
    if (!iso) return NV;
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso));
    return m ? m[3] + '/' + m[2] + '/' + m[1] : String(iso);
  }
  function today() {
    var d = new Date();
    function p(n) { return (n < 10 ? '0' : '') + n; }
    return p(d.getDate()) + '/' + p(d.getMonth() + 1) + '/' + d.getFullYear();
  }
  /* A date range where one or both ends may be missing. "Not verified to Not verified"
     is what a naive join produces and it reads as a fault in the report rather than a
     gap in the source, so a range with nothing in it says so once. */
  function span(a, b, fmt) {
    var f = fmt || function (x) { return esc(x); };
    if (!a && !b) return '<span class="nv">' + NV + '</span>';
    if (a && !b) return 'from ' + f(a) + ', end date <span class="nv">' + NV + '</span>';
    if (!a && b) return 'start date <span class="nv">' + NV + '</span>, to <b>' + f(b) + '</b>';
    return f(a) + ' to <b>' + f(b) + '</b>';
  }
  function link(url, text) {
    if (!url) return esc(text || '');
    return '<a href="' + esc(url) + '" rel="noopener">' + esc(text || url) + '</a>';
  }
  /* "live as of" is the Hub's own freshness convention: the date the SOURCE was last
     read, never the date the page was opened. */
  function asOf(d) { return d ? 'live as of ' + ukdate(d) : 'live as of <span class="nv">' + NV + '</span>'; }

  var GAPS = [];
  function gapNote(file, lastGood) {
    return '<div class="gap"><b>' + esc(file) + ' could not be read just now.</b> '
      + 'This is a loading problem, not missing data, and nothing has been substituted for it. '
      + (lastGood
        ? 'The last reading the Hub holds for this file is dated <b>' + esc(ukdate(lastGood))
          + '</b>, recorded when the report’s own data file was built. Refresh to try the live read again.'
        : 'The Hub holds no recorded date for this file, so no last good reading can be shown. Refresh to try again.')
      + '</div>';
  }

  MOUNT.innerHTML = '<style>' + CSS + '</style><div class="inr"><div class="band"><div class="col">'
    + 'Loading the Innovator Market Analysis Report…</div></div></div>';

  function get(file) {
    return fetch(RAW + file + CB).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }
  function soft(file, dateKey) {
    /* A secondary file. A failure is recorded and the section reports it; it never
       takes the report down. */
    return get(file).then(function (d) { return d; }, function () {
      GAPS.push(file);
      return null;
    });
  }

  var B = null, P = null, ICB = null, TEN = null, PEND = null, PRESS = null;

  get('innovator-report.json').then(function (bundle) {
    B = bundle;
    return Promise.all([
      soft('products.json'), soft('icb-watch.json'), soft('open-tenders.json'),
      soft('pending-awards.json'), soft('trust-pressures.json')
    ]);
  }).then(function (rest) {
    P = rest[0]; ICB = rest[1]; TEN = rest[2]; PEND = rest[3]; PRESS = rest[4];
    boot();
  }).catch(function (e) {
    MOUNT.innerHTML = '<style>' + CSS + '</style><div class="inr"><div class="band"><div class="col">'
      + '<h2>The report could not be loaded</h2><p>Its own data file could not be fetched ('
      + esc(e.message) + '). This is a loading problem, not missing data: nothing has been '
      + 'substituted and no part of the report has been written from memory. Refresh to try again.</p>'
      + '</div></div></div>';
  });

  function boot() {
    var state = {
      spec: q('spec') || 'wound',
      type: q('type') || 'device',
      stage: q('stage') || 'prototype',
      geo: q('geo') || 'national',
      purpose: q('purpose') === 'investment' ? 'investment' : 'grant',
      org: clean(q('org'))
    };
    if (!B.specialities[state.spec] && !hasAnySpec(state.spec)) state.spec = 'wound';
    render(state);
  }

  function hasAnySpec(id) {
    var l = B.specialityList || [];
    for (var i = 0; i < l.length; i++) if (l[i].id === id) return true;
    return false;
  }
  function specLabel(id) {
    if (B.specialities[id] && B.specialities[id].label) return B.specialities[id].label;
    var l = B.specialityList || [];
    for (var i = 0; i < l.length; i++) if (l[i].id === id) return l[i].label;
    return id;
  }
  function typeOf(id) {
    for (var i = 0; i < TYPES.length; i++) if (TYPES[i].id === id) return TYPES[i];
    return TYPES[1];
  }
  function stageLabel(id) {
    for (var i = 0; i < STAGES.length; i++) if (STAGES[i].id === id) return STAGES[i].label;
    return id;
  }
  function icbList() { return (ICB && ICB.icbs) ? ICB.icbs.slice() : []; }
  function icbByCode(code) {
    var l = icbList();
    for (var i = 0; i < l.length; i++) if (l[i].code === code) return l[i];
    return null;
  }

  /* ------------------------------------------------------------------ blocks */

  function sec(cls, n, eyebrow, title, body) {
    return '<div class="band ' + cls + '" id="inr-s' + n + '"><div class="col"><div class="eyebrow">'
      + esc(eyebrow) + '</div><h2><span class="sn">' + n + '</span>' + esc(title) + '</h2>' + body
      + '</div></div>';
  }
  function evidence(label, body) {
    return '<div class="ev"><div class="evlab">Hub evidence · ' + label + '</div>' + body + '</div>';
  }
  function mine(org, ask, ph, id) {
    return '<div class="mine"><div class="lab">Your words · written by '
      + esc(org || 'the applicant') + ' · not verified by the Medical Sales Intelligence Hub</div>'
      + '<div class="ask">' + ask + '</div>'
      + '<div class="w" id="' + id + '" contenteditable="true" data-ph="' + esc(ph) + '"></div></div>';
  }

  /* 1 — the product and the claim */
  function s1(st) {
    var sp = B.specialities[st.spec], t = typeOf(st.type);
    var problems = [];
    if (P && P.P) {
      for (var i = 0; i < P.P.length && problems.length < 6; i++) {
        if (P.P[i].s === st.spec) problems.push(P.P[i].n + ': ' + P.P[i].p);
      }
    }
    var prompt = problems.length
      ? evidence(asOf(B.generatedOn),
          '<p class="note">The problems the Hub already holds for ' + esc(specLabel(st.spec))
          + ', from the Stakeholder Mapper’s product list. These are here to show you the '
          + 'level a buyer expects a problem stated at. <b>They are not your problem</b>: '
          + 'write your own in the box below.</p><ul class="note">'
          + problems.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('')
          + '</ul><p class="src">Source: data/products.json, the Hub’s own product and problem '
          + 'list, as used by the ' + link(B.hubPages.mapper, 'Stakeholder Mapper') + '.</p>')
      : '';
    return prompt
      + mine(st.org, 'In one sentence, what is it? Name the product, what it does and who uses it. '
        + 'No adjectives: a reader who has never heard of you has to be able to repeat it back.',
        'One sentence. What it is, what it does, who uses it.', 'inr-w1')
      + mine(st.org, 'What is the clinical problem? State it as the NHS would recognise it: the '
        + 'harm, the delay or the cost that happens today, in the pathway where it happens.',
        'The problem as a clinician or a commissioner would state it.', 'inr-w2')
      + mine(st.org, 'What is your claimed benefit, and what is it measured against? Give the '
        + 'comparator and the effect size you are claiming. If you do not have one yet, say so '
        + 'here. A stated gap reads better than a number you cannot evidence.',
        'The claim, the comparator, the effect size, or the honest statement that you do not have it yet.', 'inr-w3')
      + '<p class="note"><b>Product type:</b> ' + esc(t.label) + ' · <b>Stage:</b> '
      + esc(stageLabel(st.stage)) + ' · <b>Speciality:</b> ' + esc(specLabel(st.spec))
      + ' · <b>Geography:</b> ' + esc(geoLabel(st)) + '. These are the five answers this '
      + 'report was generated from; every section below is filtered by them.</p>';
  }

  function geoLabel(st) {
    if (st.geo === 'national') return 'England, national';
    var m = icbByCode(st.geo);
    return m ? m.name : st.geo;
  }

  /* 2 — the market */
  function s2(st) {
    var out = '', band = B.specialities[st.spec] && B.specialities[st.spec].evidenceBand;
    if (!P) {
      out += gapNote('data/products.json', null);
    } else {
      var fam = (P.FW || {})[st.spec], prio = (P.PRIORITY || {})[st.spec];
      var kp = '<div class="kpis">';
      kp += '<div class="kpi"><b>' + esc(specLabel(st.spec)) + '</b><span>the speciality this '
        + 'report is filtered to</span></div>';
      kp += '<div class="kpi"><b>' + (ICB ? num(ICB.count) : '<span class="nv">' + NV + '</span>')
        + '</b><span>Integrated Care Boards (ICBs) in England, the commissioning layer you have '
        + 'to sell through</span></div>';
      kp += '<div class="kpi"><b>' + (PRESS ? num(PRESS.count) : '<span class="nv">' + NV + '</span>')
        + '</b><span>acute NHS trusts in the Hub’s pressure set</span></div></div>';
      out += kp;
      out += '<h3>Where this speciality sits in NHS buying</h3>';
      out += fam
        ? '<p>' + esc(fam.fam) + '. ' + link(fam.cat, 'The category page it buys through')
          + '.</p><p class="src">Source: data/products.json, the Hub’s framework family map. '
          + asOf(B.generatedOn) + '.</p>'
        : '<p><span class="nv">' + NV + '</span>: the Hub holds no framework family for this '
          + 'speciality. What would settle it: the NHS Supply Chain category page for the product, '
          + 'read at source.</p>';
      out += '<h3>The national priority this speciality is funded against</h3>';
      out += prio
        ? '<p>' + esc(prio) + '</p><p class="src">Source: data/products.json, the Hub’s '
          + 'national priority map. ' + asOf(B.generatedOn) + '.</p>'
        : '<p><span class="nv">' + NV + '</span>: the Hub holds no national priority line for '
          + 'this speciality. What would settle it: the current NHS planning guidance, read for '
          + 'this speciality.</p>';

      var hi = band ? (P.EVIDENCE_HIGHLIGHTS || {})[band] : null;
      out += '<h3>The published burden figures the Hub holds</h3>';
      if (hi && hi.rows && hi.rows.length) {
        out += '<div class="scroll"><table><tr><th>Reference</th><th>Study type</th>'
          + '<th>Finding</th></tr>'
          + hi.rows.map(function (r) {
            return '<tr><td>' + esc(r.ref || NV) + '</td><td>' + esc(r.kind || NV) + '</td><td>'
              + esc(r.finding || NV) + '</td></tr>';
          }).join('') + '</table></div>'
          + '<p class="src">Source: the Hub’s ' + link(B.hubPages.evidence, 'Clinical Evidence Library')
          + ', band “' + esc(hi.band_title || band) + '”, area “' + esc(hi.area || '')
          + '”, as held in data/products.json. ' + asOf(B.generatedOn) + '. These are '
          + 'published studies with their own citations: cite the study, not this report.</p>';
      } else {
        out += '<p><span class="nv">' + NV + '</span>: the Hub holds no Clinical Evidence Library '
          + 'band for ' + esc(specLabel(st.spec)) + ' yet, so no burden figure is shown and none '
          + 'has been estimated. What would settle it: a Getting It Right First Time (GIRFT) report '
          + 'for this speciality, or a published prevalence study. The Hub’s '
          + link(B.hubPages.girft, 'GIRFT Specialty Intelligence') + ' page is where to start.</p>';
      }
    }

    out += '<h3>Waiting times in this speciality</h3>';
    if (!PRESS) {
      out += gapNote('data/trust-pressures.json', (B.sources['trust-pressures.json'] || {}).asOf);
    } else {
      var spname = rttName(st.spec);
      if (!spname) {
        out += '<p><span class="nv">Not applicable</span>: NHS England publishes no Referral to '
          + 'Treatment (RTT) waiting time for ' + esc(specLabel(st.spec)) + ' as a treatment '
          + 'function, so no waiting figure is shown and nothing is substituted for it.</p>';
      } else {
        var rows = rttRows(st, spname);
        if (!rows.length) {
          out += '<p><span class="nv">' + NV + '</span>: no trust in the selected geography '
            + 'reports an RTT median for ' + esc(spname) + ' in this reading.</p>';
        } else {
          out += '<div class="scroll"><table><tr><th>NHS trust</th><th>Region</th>'
            + '<th class="n">' + esc(spname) + ' median wait (weeks)</th>'
            + '<th class="n">All-speciality waiting list</th>'
            + '<th class="n">Waiting 52 weeks or more</th></tr>'
            + rows.slice(0, 12).map(function (r) {
              return '<tr><td>' + esc(r.name) + '</td><td>' + esc(r.region || NV) + '</td>'
                + '<td class="n">' + (r.med == null ? NV : r.med) + '</td>'
                + '<td class="n">' + num(r.wl) + '</td><td class="n">' + num(r.w52) + '</td></tr>';
            }).join('') + '</table></div>'
            + '<p class="src">Longest ' + esc(spname) + ' median first. Source: '
            + link('https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/',
                   'NHS England, Referral to Treatment (RTT) waiting times, incomplete pathways')
            + ', Open Government Licence, as held in data/trust-pressures.json. '
            + asOf((B.sources['trust-pressures.json'] || {}).asOf) + '. '
            + (rows.length > 12 ? 'Showing the 12 longest of ' + rows.length + ' trusts. ' : '')
            + 'A long wait is a pressure, not a sale: it tells you where a case for change is '
            + 'already being made for you.</p>';
        }
      }
    }
    return out;
  }

  /* trust-pressures holds per-speciality medians under NHS England's own treatment-function
     names, which are not the Hub's speciality keys. The map below is the exact set of names
     that file carries; a speciality not in it has no published RTT line and the report says so
     rather than borrowing another speciality's figure. */
  var RTT_NAMES = {
    ortho: 'Trauma & Orthopaedics', endourology: 'Urology', continence: 'Urology',
    ent: 'ENT (Ear, Nose & Throat)', audiology: 'ENT (Ear, Nose & Throat)',
    ophthalmology: 'Ophthalmology', cardiology: 'Cardiology', dermatology: 'Dermatology',
    womens: 'Gynaecology', surgical: 'General Surgery', theatres: 'General Surgery',
    mis: 'General Surgery', closure: 'General Surgery'
  };
  function rttName(spec) { return RTT_NAMES[spec] || null; }
  function rttRows(st, spname) {
    var out = [], ts = (PRESS && PRESS.trusts) || {};
    var want = st.geo === 'national' ? null : (icbByCode(st.geo) || {}).region;
    Object.keys(ts).forEach(function (code) {
      var t = ts[code];
      if (!t || !t.spec || t.spec[spname] == null) return;
      if (want && t.region !== want) return;
      out.push({ name: t.name, region: t.region, med: t.spec[spname], wl: t.wl, w52: t.w52 });
    });
    out.sort(function (a, b) { return (b.med || 0) - (a.med || 0); });
    return out;
  }

  /* 3 — who already sells here */
  function s3(st) {
    var sp = B.specialities[st.spec], t = typeOf(st.type), out = '';
    if (!sp) {
      out += '<p><span class="nv">' + NV + '</span>: the Hub holds no researched competitor set '
        + 'for ' + esc(specLabel(st.spec)) + '. That is a gap in the Hub, not a finding about the '
        + 'market: it does not mean nobody sells here. What would settle it: the current NHS '
        + 'Supply Chain contract launch brief for this category, read supplier by supplier. The '
        + 'Hub’s ' + link(B.hubPages.competitors, 'Who Are the Competitors?') + ' page and its '
        + link(B.hubPages.suppliers, 'Suppliers') + ' directory are where the researched sets live.</p>';
    } else {
      var rows = sp.suppliers || [], TOP = 10;
      out += '<div class="kpis">'
        + '<div class="kpi"><b>' + num(sp.supplierCount) + '</b><span>companies the Hub holds in '
        + 'the researched ' + esc(sp.label) + ' supplier set</span></div>'
        + '<div class="kpi"><b>' + num(sp.matchedCount) + '</b><span>of them with at least one NHS '
        + 'award row in the Hub’s award set</span></div>'
        + '<div class="kpi"><b>' + num(rows.length ? rows[0].awardCount : null) + '</b><span>award '
        + 'rows held for the most contracted company, ' + esc(rows.length ? (rows[0].co || '') : '')
        + '</span></div></div>';
      /* The column headers carry the "any speciality" caveat themselves. The caveat
         used to sit only in the source note underneath, and a reader scanning the
         table saw "Dental Drills Managed Service" in a wound care report and read it
         as a mistake. The header is where the reader is looking. */
      out += '<p class="note"><b>Read this table as: how established is this company as an '
        + 'NHS supplier.</b> The award columns are every NHS award row the Hub holds for that '
        + 'legal entity <b>in any speciality</b>, not only in ' + esc(sp.label) + '. A large '
        + 'supplier’s most recent award will often be nothing to do with your product. '
        + 'That is the point: it is who you are competing with for a buyer’s attention.</p>';
      out += '<div class="scroll" id="inr-s3t"><table><tr><th>Company (legal entity)</th><th>Brands</th>'
        + '<th class="n">NHS award rows held, any speciality</th>'
        + '<th>Most recent NHS award row, any speciality</th></tr>'
        + rows.map(function (r, ri) {
          var last = r.awards && r.awards[0];
          var cell;
          if (!r.matched) {
            cell = '<span class="nv">No award row in the Hub’s set.</span> That is not the '
              + 'same as no contracts: this company may sell through a framework call-off that '
              + 'publishes no award notice.';
          } else {
            cell = esc(last.title || NV) + '<br><span class="src">' + esc(last.buyer || NV) + ' · '
              + esc(ukdate(last.date)) + ' · ' + (last.valueAmount == null ? 'value not published'
              : money(last.valueAmount)) + ' · ' + link(last.url, last.source || 'notice') + '</span>';
          }
          /* The brands field is a full sentence when no brand is held. In a 40-row table
             that sentence repeated is noise: the cell says "Not verified" and the note under
             the table carries the rest. */
          var br = !r.brands || /^Not verified/.test(r.brands)
            ? '<span class="soft">Not verified</span>' : esc(r.brands);
          return '<tr' + (ri >= TOP ? ' class="more-rows"' : '') + '><td>'
            + (r.url ? link(r.url, r.co) : esc(r.co || NV))
            + (r.ref && r.ref !== r.co ? '<br><span class="src">Hub master record: ' + esc(r.ref) + '</span>' : '')
            + '</td><td>' + br + '</td>'
            + '<td class="n">' + num(r.awardCount) + '</td><td>' + cell + '</td></tr>';
        }).join('') + '</table></div>'
        + (rows.length > TOP ? '<button type="button" class="tgl" data-tgl="inr-s3t">Show all '
          + rows.length + ' companies</button>' : '');
      out += '<p class="src">Most contracted first'
        + (rows.length > TOP ? '; the ' + TOP + ' most contracted show on screen, every row prints' : '')
        + '. “Not verified” under Brands means the Hub has not yet captured brand-level detail '
        + 'for that company: see the supplier’s own site. The supplier set is the Hub’s own '
        + 'researched set for this speciality (data/compare-suppliers.json, human-curated, '
        + 'verified ' + esc((B.sources['compare-suppliers.json'] || {}).verifiedOn || NV)
        + '); every framework name, its dates and its supplier list come from that framework’s '
        + 'own contract launch brief on supplychain.nhs.uk. Award rows are '
        + link('https://www.find-tender.service.gov.uk/', 'Find a Tender') + ' and '
        + link('https://www.contractsfinder.service.gov.uk/', 'Contracts Finder') + ' notices, '
        + 'Open Government Licence, as held in data/company-awards.json, '
        + asOf(parseUk((B.sources['company-awards.json'] || {}).dataAsOf)) + '. '
        + '<b>Read the award count carefully:</b> it is every NHS award row the Hub holds for that '
        + 'legal entity in any speciality, as the column headers say. ' + esc(B.matchRule) + '</p>';
      if (sp.routeNote) {
        out += '<p class="note"><b>What the Hub records about this supplier set:</b> '
          + esc(sp.routeNote) + '</p>';
      }
    }

    if (t.digital) {
      out += '<h3>Digital health competitors: companies with a digital NHS award</h3>';
      var dc = B.digitalCompetitors || [];
      out += '<div class="scroll"><table><tr><th>Company</th><th class="n">Digital award rows</th>'
        + '<th>Most recent</th></tr>'
        + dc.slice(0, 20).map(function (r) {
          var last = r.awards && r.awards[0];
          return '<tr><td>' + esc(r.co) + '</td><td class="n">' + num(r.awardCount) + '</td><td>'
            + (last ? esc(last.title || NV) + '<br><span class="src">' + esc(last.buyer || NV)
              + ' · ' + esc(ukdate(last.date)) + ' · '
              + (last.valueAmount == null ? 'value not published' : money(last.valueAmount))
              + ' · ' + link(last.url, last.source || 'notice') + '</span>'
              : '<span class="nv">' + NV + '</span>') + '</td></tr>';
        }).join('') + '</table></div>'
        + '<p class="src">The 20 most contracted of ' + dc.length + ' companies. Source: '
        + 'data/company-digital-awards.json, Find a Tender and Contracts Finder notices carrying '
        + 'a digital Common Procurement Vocabulary (CPV) code, Open Government Licence, '
        + asOf(parseUk((B.sources['company-digital-awards.json'] || {}).dataAsOf)) + '. '
        + 'This is a competitor set built from who has actually won a digital NHS contract, not '
        + 'from who is listed on a framework. ' + esc(B.digitalArmRule) + '</p>';
    }
    return out;
  }

  function parseUk(s) {
    /* dataAsOf is written either as 15/11/2026 or 2026-11-15 across the data files. */
    if (!s) return null;
    var m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(String(s));
    return m ? m[3] + '-' + m[2] + '-' + m[1] : String(s);
  }

  /* 4 — how it gets bought */
  function s4(st) {
    var sp = B.specialities[st.spec], t = typeOf(st.type), out = '';
    out += '<h3>NHS Supply Chain frameworks for this speciality</h3>';
    var fws = (sp && sp.frameworks) || [];
    if (!fws.length) {
      out += '<p><span class="nv">' + NV + '</span>: the Hub matches no NHS Supply Chain framework '
        + 'to ' + esc(specLabel(st.spec)) + '. What would settle it: the '
        + link('https://www.supplychain.nhs.uk/product-information/contract-launch-briefs/',
               'NHS Supply Chain contract launch briefs') + ' index, read for this category.</p>';
    } else {
      out += '<div class="scroll"><table><tr><th>Framework</th><th>Reference</th>'
        + '<th>Runs</th><th>Supply route</th><th class="n">Suppliers on it</th>'
        + '<th>Successor or renewal</th></tr>'
        + fws.map(function (f) {
          var succ = [];
          (f.signals || []).forEach(function (s) {
            succ.push('<b>' + esc(s.label || s.kind) + '.</b> ' + esc(s.text || '') + ' '
              + link(s.sourceUrl, s.sourceTitle || 'source')
              + (s.checked ? ' <span class="src">read ' + esc(ukdate(s.checked)) + '</span>' : ''));
          });
          (f.calendar || []).forEach(function (c) {
            succ.push('<b>NHS Supply Chain procurement calendar.</b> Planned publication: '
              + esc(c.plannedPublication || NV) + '; contract go-live: '
              + esc(c.contractGoLive || NV) + '.');
          });
          return '<tr><td>' + link(f.url, f.name) + '</td><td>' + esc(f.reference || NV) + '</td>'
            + '<td>' + span(f.starts, f.ends) + '</td>'
            + '<td>' + esc(f.supplyRoute || NV) + '</td>'
            + '<td class="n">' + num((f.suppliers || []).length || null) + '</td>'
            + '<td>' + (succ.length ? succ.join('<br>')
              : '<span class="nv">Nothing recorded.</span> The Hub holds no renewal signal and no '
                + 'procurement-calendar row for this framework, so no successor date is shown and '
                + 'none has been guessed.') + '</td></tr>';
        }).join('') + '</table></div>'
        + '<p class="src">Source: each framework’s own contract launch brief on '
        + 'supplychain.nhs.uk, fetched by the Hub (data/frameworks.json, '
        + asOf((B.sources['frameworks.json'] || {}).dataAsOf) + '); renewal signals from '
        + 'data/framework-directory-extra.json, each read at the named source; calendar rows from '
        + 'the NHS Supply Chain procurement calendar page (last updated '
        + esc((B.procurementCalendar || {}).pageLastUpdated || NV) + '). '
        + esc(B.frameworkMatchRule) + ' Full directory: '
        + link(B.hubPages.frameworks, 'Frameworks, Tenders, Awards, Drug Tariff and Contracts') + '.</p>';
    }

    if (sp && (sp.route || []).length) {
      out += '<h3>What the Hub records about the route itself</h3><ul class="note">'
        + sp.route.map(function (r) {
          return '<li>' + link(r.url, r.name) + ', ' + esc(r.dates || NV)
            + (r.note ? '. ' + esc(r.note) : '') + '</li>';
        }).join('') + '</ul>'
        + '<p class="src">Source: data/compare-suppliers.json, the Hub’s curated route per '
        + 'speciality, verified ' + esc((B.sources['compare-suppliers.json'] || {}).verifiedOn || NV)
        + '.</p>';
    }

    if (t.digital) {
      out += '<h3>Digital and technology routes</h3>';
      var dfw = B.digitalFrameworks || [];
      out += '<div class="scroll"><table><tr><th>Agreement</th><th>Reference</th><th>Owner</th>'
        + '<th>Runs</th><th>Type</th><th class="n">Suppliers listed</th></tr>'
        + dfw.map(function (f) {
          return '<tr><td>' + link(f.url, f.name) + (f.term ? '<br><span class="src">' + esc(f.term)
            + '</span>' : '') + '</td><td>' + esc(f.reference || NV) + '</td><td>'
            + esc(f.owner || NV) + '</td><td>' + span(f.starts, f.ends, function (x) { return esc(ukdate(x)); })
            + '</td><td>' + esc(f.agreementType || NV) + '</td>'
            + '<td class="n">' + num(f.supplierCount || null) + '</td></tr>';
        }).join('') + '</table></div>'
        + '<p class="src">Source: data/digital-frameworks.json: '
        + esc((B.sources['digital-frameworks.json'] || {}).source || NV) + ', '
        + asOf((B.sources['digital-frameworks.json'] || {}).dataAsOf) + '. Supplier counts are the '
        + 'sum of each agreement’s lot supplier lists as published on its own page; the lists '
        + 'themselves are on that page, not reproduced here. Hub page: '
        + link(B.hubPages.digitalRoutes, 'How the NHS Buys Digital Health: Frameworks and Routes') + '.</p>';

      var ob = (B.otherBodies || []).filter(function (r) { return r.digital; });
      out += '<h3>Digital and technology frameworks run by other bodies</h3>'
        + '<div class="scroll"><table><tr><th>Framework</th><th>Owner</th><th>Reference</th>'
        + '<th>Runs</th><th>Regime</th></tr>'
        + ob.map(function (r) {
          return '<tr><td>' + link(r.url, r.name) + '</td><td>' + esc(r.owner || NV) + '</td>'
            + '<td>' + esc(r.reference || NV) + '</td><td>' + span(r.starts, r.ends)
            + '</td><td>' + esc(r.regime || NV) + '</td></tr>';
        }).join('') + '</table></div>'
        + '<p class="src">' + ob.length + ' of ' + (B.otherBodies || []).length + ' other-body '
        + 'framework rows. Source: data/framework-directory-extra.json: '
        + esc((B.sources['framework-directory-extra.json'] || {}).checkedAt || NV) + '. '
        + esc(B.digitalRule) + '</p>';
    } else {
      out += '<p class="note">Digital and technology framework routes are not shown because the '
        + 'product type selected is ' + esc(t.label).toLowerCase() + '. Change the product type to '
        + 'a software or algorithm option to see the G-Cloud, Government Commercial Agency and '
        + 'NHS Shared Business Services digital routes.</p>';
    }

    out += mine(st.org, 'Which route are you going for, and where are you on it today? Name the '
      + 'framework or the direct route, say whether you are on it, and if you are not, name the '
      + 'reopening or tender date you are working to.',
      'The route, your position on it today, and the date you are working to.', 'inr-w4');
    return out;
  }

  /* The Stakeholder Mapper's role text is reproduced verbatim — it is the Hub's own
     wording and this report does not rewrite it — and that text uses abbreviations the
     mapper's page spells out elsewhere. Hub rule: the first use of an abbreviation in
     running text is written in full. So the ones that actually appear in the roles on
     THIS report are expanded underneath the table, and anything else goes to the Hub's
     own glossary rather than being guessed at here. */
  var ABBR = [
    ['CQC', 'Care Quality Commission'],
    ['NICE', 'National Institute for Health and Care Excellence'],
    ['GIRFT', 'Getting It Right First Time'],
    ['PCN', 'Primary Care Network'],
    ['EBME', 'Electro-Biomedical Engineering'],
    ['LOLER', 'the Lifting Operations and Lifting Equipment Regulations 1998'],
    ['MHOR', 'the Manual Handling Operations Regulations 1992'],
    ['IR(ME)R', 'the Ionising Radiation (Medical Exposure) Regulations 2017'],
    ['IPC', 'Infection Prevention and Control'],
    ['AMR', 'antimicrobial resistance'],
    ['HCAI', 'healthcare-associated infection'],
    ['SSI', 'surgical site infection'],
    ['TVN', 'tissue viability nurse'],
    ['MUST', 'the Malnutrition Universal Screening Tool'],
    ['ONS', 'oral nutritional supplements'],
    ['SACT', 'Systemic Anti-Cancer Therapy'],
    ['PN', 'parenteral nutrition'],
    ['JAG', 'the Joint Advisory Group on Gastrointestinal Endoscopy'],
    ['HTM', 'Health Technical Memorandum'],
    ['RCT', 'randomised controlled trial'],
    ['ODEP', 'the Orthopaedic Data Evaluation Panel'],
    ['MTG', 'Medical Technologies Guidance'],
    ['IPG', 'Interventional Procedures Guidance'],
    ['H&S', 'health and safety']
  ];
  /* icb-watch writes board roles as bare keys. These are the only two it uses. */
  var BOARD_ROLE = { chair: 'Chair', ceo: 'Chief Executive' };
  var ROLE_WORDS = { cfo: 'Chief Finance Officer', cmo: 'Chief Medical Officer', cno: 'Chief Nursing Officer' };
  function boardRole(r) { return BOARD_ROLE[r] || r; }

  function clusterOf(code) {
    var cs = (ICB && ICB.clusters) || [];
    for (var i = 0; i < cs.length; i++) if (cs[i].indexOf(code) >= 0) return cs[i];
    return [code];
  }

  function glossaryFor(keys) {
    var text = keys.map(function (k) {
      var r = (B.stakeholderRoles || {})[k] || {};
      return [r.role, r.whoSec, r.whoPri, r.cares, r.evidence, r.hook, r.risk].join(' ');
    }).join(' ');
    var found = ABBR.filter(function (p) { return text.indexOf(p[0]) >= 0; });
    if (!found.length) return '';
    return '<p class="note"><b>Abbreviations used in the table above:</b> '
      + found.map(function (p) { return esc(p[0]) + ', ' + esc(p[1]); }).join('; ')
      + '. Anything else: the Hub’s ' + link(HUB + 'glossary/', 'Glossary') + '.</p>';
  }

  /* 5 — who decides */
  function s5(st) {
    var t = typeOf(st.type), out = '';
    var keys = (B.stakeholderTemplates || {})[t.tpl] || [];
    /* The mapper adds a product-specific extra role (its `tp`) on top of the template;
       the first product in this speciality that carries one is used, and the report says so. */
    var extra = null;
    if (P && P.P) {
      for (var i = 0; i < P.P.length; i++) {
        if (P.P[i].s === st.spec && P.P[i].tp) { extra = P.P[i].tp; break; }
      }
    }
    var all = keys.slice();
    if (extra && all.indexOf(extra) < 0) all.push(extra);

    out += '<h3>The roles that have to agree</h3>';
    if (!all.length) {
      out += '<p><span class="nv">' + NV + '</span>: no stakeholder template is held for this '
        + 'product type.</p>';
    } else {
      out += '<div class="scroll"><table><tr><th>Role</th><th>Who that is in an acute trust</th>'
        + '<th>Who that is in primary care and the ICB</th><th>What they care about</th>'
        + '<th>Evidence they will demand</th></tr>'
        + all.map(function (k) {
          var r = (B.stakeholderRoles || {})[k];
          if (!r) return '';
          return '<tr><td><b>' + esc(r.role) + '</b></td><td>' + esc(r.whoSec || NV) + '</td>'
            + '<td>' + esc(r.whoPri || r.whoSec || NV) + '</td><td>' + esc(r.cares || NV) + '</td>'
            + '<td>' + esc(r.evidence || NV) + '</td></tr>';
        }).join('') + '</table></div>'
        + '<p class="src">Source: the Hub’s own '
        + link(B.hubPages.mapper, 'Stakeholder Mapper') + ', role library read straight out of '
        + 'app/mst-logic.js by scripts/build_innovator_report.py so the two cannot drift apart. '
        + 'The roles shown are the mapper’s own set for a '
        + esc(t.label.toLowerCase())
        + (extra ? ', plus the ' + esc(((B.stakeholderRoles || {})[extra] || {}).role || extra)
          + ' role, which the mapper adds for products in this speciality' : '')
        + '. These are roles, not named people. The names are yours to find and go in the box below.</p>';
      out += glossaryFor(all);
      var risky = all.filter(function (k) { return ((B.stakeholderRoles || {})[k] || {}).risk; });
      if (risky.length) {
        out += '<h3>Where adoption stalls</h3><ul class="note">'
          + risky.map(function (k) {
            var r = B.stakeholderRoles[k];
            return '<li><b>' + esc(r.role) + ':</b> ' + esc(r.risk) + '</li>';
          }).join('') + '</ul>';
      }
    }

    out += '<h3>Who is in post in the geography you selected</h3>';
    if (!ICB) {
      out += gapNote('data/icb-watch.json', parseUk((B.sources['icb-watch.json'] || {}).asOf));
    } else if (st.geo === 'national') {
      out += '<p class="note">No ICB roles are listed because the geography selected is '
        + 'England, national. Pick an Integrated Care Board (ICB) above to list its board and '
        + 'executive roles, each with the page they were read from. There are ' + num(ICB.count)
        + ' ICBs in England, counted from '
        + link(ICB.countSource, 'the NHS Organisation Data Service directory')
        + '.</p><p class="src">Source: data/icb-watch.json, '
        + asOf(parseUk(ICB.asOf)) + '. Hub page: ' + link(B.hubPages.icbPack, 'the ICB Pack') + '.</p>';
    } else {
      var m = icbByCode(st.geo);
      if (!m) {
        out += '<p><span class="nv">' + NV + '</span>: that ICB code is not in the Hub’s list.</p>';
      } else {
        var ld = (m.leaders || []).map(function (l) {
          return '<tr><td>' + esc(boardRole(l.role))
            + (l.qualifier ? ' <span class="src">(' + esc(l.qualifier) + ')</span>' : '')
            + '</td><td>'
            + link(m.leadersSource, 'NHS England, integrated care in your area') + '</td>'
            + '<td><span class="src">' + (ICB.leadersCheckedOn ? 'read ' + esc(ukdate(ICB.leadersCheckedOn))
              : NV) + '</span></td></tr>';
        });
        /* Executives are grouped by role family so the finance people sit together, and
           a name whose last sighting is older than the Hub's own last sweep is flagged:
           that is the file telling you, in its own data, that the page no longer lists
           them. It is not a claim they have left — the wording says exactly what it is. */
        var execs = (m.execs || []).slice().sort(function (a, b) {
          var f = String(a.family || '').localeCompare(String(b.family || ''));
          return f || String(a.title || '').localeCompare(String(b.title || ''));
        });
        var swept = ICB.leadersCheckedOn;
        var ex = execs.map(function (e) {
          var stale = swept && e.lastSeen && e.lastSeen < swept;
          return '<tr><td>' + esc(e.title)
            + (stale ? '<br><span class="nv">Not listed in the Hub’s latest sweep.</span>' : '')
            + '</td><td>'
            + link(e.url, 'the ICB’s own leadership page') + '</td>'
            + '<td><span class="src">first seen ' + esc(ukdate(e.firstSeen)) + ', last seen '
            + esc(ukdate(e.lastSeen))
            + (stale ? '; the Hub last swept this page ' + esc(ukdate(swept))
              + ', so this post-holder was not on it then' : '')
            + '</span></td></tr>';
        });
        out += '<p><b>' + esc(m.name) + '</b> (' + esc(m.code) + '), ' + esc(m.region || NV)
          + (m.legalStart ? ', legally established ' + esc(ukdate(m.legalStart)) : '') + '.</p>';
        out += (ld.length || ex.length)
          ? '<div class="scroll"><table><tr><th>Role</th><th>Read from</th>'
            + '<th>When</th></tr>' + ld.join('') + ex.join('') + '</table></div>'
            + '<p class="note">Roles only. The report names no individuals: post-holders change '
            + 'and the linked page is always the current one, so read the names there.</p>'
          : '<p><span class="nv">' + NV + '</span>: no leaders or executives are held for this ICB.</p>';
        var evs = (ICB.events || []).filter(function (e) { return e.icb === m.code; });
        if (evs.length) {
          out += '<h3>Changes the Hub has recorded here</h3><ul class="note">'
            + evs.map(function (e) {
              /* A leadership event names the person in its headline and detail. The report
                 names no individuals, so it keeps only the role and points at the page. */
              var txt;
              if (e.kind === 'leadership') {
                txt = 'A change of ' + esc(boardRole(ROLE_WORDS[e.role] || e.role || 'post-holder'))
                  + ' is recorded on the ICB’s own leadership page.';
              } else {
                /* Headline only: the detail lines quote minutes and name people. A name left in
                   a headline ("Firstname Surname sits as...") is replaced by the role it holds. */
                txt = esc(String(e.headline || '').replace(
                  /:\s+(?:(?:Dr|Mr|Mrs|Ms|Prof)\.?\s+)?[A-Z][a-z'-]+\s+[A-Z][A-Za-z'-]+\s+(?=[a-z])/,
                  ': a named post-holder ')) + '.';
              }
              return '<li><b>' + esc(ukdate(e.date)) + '.</b> ' + txt + ' '
                + (e.sources || []).map(function (u) {
                  return link(u, 'source');
                }).join(' ') + '</li>';
            }).join('') + '</ul>'
            + '<p class="note">A role that has just changed hands is the one meeting you can still '
            + 'get: a new post-holder is reviewing what they inherited.</p>';
        }
        var cl = clusterOf(m.code);
        if (cl.length > 1) {
          out += '<p class="note"><b>This ICB shares an executive team.</b> The Hub records it in '
            + 'a cluster with ' + cl.filter(function (c) { return c !== m.code; })
              .map(function (c) { var o = icbByCode(c); return esc(o ? o.name : c); }).join(' and ')
            + '. Separate legal entities, one executive team: work them as one account, not '
            + cl.length + '.</p>';
        }
        out += '<p class="src">Source: data/icb-watch.json: each row read at the page named '
          + 'beside it; board leaders from NHS England’s own list, executives from the '
          + 'ICB’s own leadership page. ' + asOf(parseUk(ICB.asOf)) + ', leaders re-read '
          + esc(ukdate(ICB.leadersCheckedOn)) + '.</p>';
      }
    }
    out += regionalHelp(st);
    out += mine(st.org, 'Name your actual contacts against the roles above, and say which of them '
      + 'you have spoken to. An empty row is an honest answer and a funder can read it; a guess '
      + 'cannot survive a question.',
      'Role, name, organisation, whether you have spoken to them.', 'inr-w5');
    return out;
  }

  /* Regional innovation support. scripts/regional-innovation.json (published inside this bundle) is hand-curated: each row
     is an organisation's own public page, read on the date the file records. Shown only when
     the ICB picked sits in a region the file covers; a row tagged with the speciality picked
     is marked, nothing is hidden. No named individuals: a role changes hands, a page does not. */
  function regionalHelp(st) {
    var RG = (B.regionalSupport || {}).regions || {};
    if (st.geo === 'national') {
      var have = Object.keys(RG);
      return have.length ? '<p class="note">Pick an ICB in ' + esc(have.join(' or '))
        + ' above to see the regional research and innovation bodies that can help you in.</p>' : '';
    }
    var m = icbByCode(st.geo), R = m && RG[m.region];
    if (!R) { return ''; }
    var spl = specLabel(st.spec);
    function hit(x) { return (x.specs || []).indexOf(st.spec) >= 0; }
    function card(r, g, star) {
      return '<div class="rg-card' + (star ? ' rg-hit' : '') + '">'
        + (star ? '<div class="rg-kind">' + esc(g) + '</div>' : '')
        + (star ? '<div class="rg-chip">Matches ' + esc(spl) + '</div>' : '')
        + '<div class="rg-name">' + esc(r.name) + '</div>'
        + '<p class="rg-what">' + esc(r.what) + '</p>'
        + '<div class="rg-go">' + link(r.url, 'Read their page') + '</div></div>';
    }
    var all = [], kinds = 0;
    (R.groups || []).forEach(function (g) {
      (g.rows || []).forEach(function (r) { all.push({ r: r, g: g.title }); });
      kinds++;
    });
    var hits = all.filter(function (x) { return hit(x.r); });
    var exHits = (R.examples || []).filter(hit).length;

    var out = '<div class="rg"><h3>Who can help you in: ' + esc(m.region) + '</h3>'
      + (R.intro ? '<p class="note">' + esc(R.intro) + '</p>' : '')
      + '<div class="kpis"><div class="kpi"><b>' + all.length + '</b><span>research and innovation '
      + 'bodies listed for ' + esc(m.region) + ', each linked to its own page</span></div>'
      + '<div class="kpi"><b>' + hits.length + '</b><span>name ' + esc(spl) + ' among their own '
      + 'stated themes</span></div>'
      + '<div class="kpi"><b>' + (R.examples || []).length + '</b><span>products from this region that '
      + 'have taken this route' + (exHits ? ', ' + exHits + ' in ' + esc(spl) : '') + '</span></div></div>';

    out += '<p class="rg-h">Start here for ' + esc(spl) + '</p>';
    out += hits.length
      ? '<div class="rg-grid">' + hits.map(function (x) { return card(x.r, x.g, true); }).join('') + '</div>'
      : '<p class="note">No body in this list names ' + esc(spl) + ' among its own stated themes. '
        + 'Start with innovation and NHS adoption support below: their job is to route you to the '
        + 'team that owns your problem.</p>';

    (R.groups || []).forEach(function (g) {
      var rest = (g.rows || []).filter(function (r) { return !hit(r); });
      if (!rest.length) { return; }
      out += '<p class="rg-h">' + esc(g.title) + '</p><div class="rg-grid">'
        + rest.map(function (r) { return card(r, g.title, false); }).join('') + '</div>';
    });

    var ex = (R.examples || []).slice().sort(function (a, b) { return hit(b) - hit(a); });
    if (ex.length) {
      out += '<p class="rg-h">Routes that have worked here</p><div class="rg-grid rg-ex">'
        + ex.map(function (e) {
          return '<div class="rg-card rg-case' + (hit(e) ? ' rg-hit' : '') + '">'
            + '<div class="rg-kind">Worked example</div>'
            + (hit(e) ? '<div class="rg-chip">Matches ' + esc(spl) + '</div>' : '')
            + '<div class="rg-name">' + esc(e.name) + '</div><p class="rg-what">' + esc(e.what) + '</p>'
            + '<div class="rg-go">' + (e.sources || []).map(function (x) {
              return link(x.url, x.label || 'source');
            }).join(' · ') + '</div></div>';
        }).join('') + '</div>';
    }
    out += '<p class="src">Source: the Hub’s regional innovation list, each card read at the page it '
      + 'links to; ' + asOf(R.readOn) + '.' + (R.basis ? ' ' + esc(R.basis) : '')
      + ' The “matches” flag means the body’s own page names that area; it is not a '
      + 'recommendation.</p></div>';
    return out;
  }

  /* 6 — what is happening now */
  function s6(st) {
    var sp = B.specialities[st.spec], slug = sp && sp.tenderSlug, out = '';
    var t = typeOf(st.type);
    out += '<h3>Open tenders in this speciality</h3>';
    if (!TEN) {
      out += gapNote('data/open-tenders.json', parseUk((B.sources['open-tenders.json'] || {}).dataAsOf));
    } else if (!slug) {
      out += '<p><span class="nv">' + NV + '</span>: the Hub cannot filter the tender feed to '
        + esc(specLabel(st.spec)) + ', because this speciality has no Clinical Evidence Library '
        + 'band and so no desk slug to match notices against. ' + esc(B.tenderSlugRule)
        + ' All ' + num((TEN.counts || {}).openNotices) + ' open notices in this reading are on the '
        + link(B.hubPages.frameworks, 'Frameworks, Tenders, Awards, Drug Tariff and Contracts')
        + ' page. Read them there rather than take a filtered list the Hub cannot stand behind.</p>';
    } else {
      var ns = (TEN.notices || []).filter(function (n) { return n.speciality === slug; });
      if (!ns.length) {
        out += '<p>No open tender notice in this reading carries the '
          + esc(slug) + ' speciality tag. <b>That is not the same as no tenders:</b> '
          + esc(TEN.specialityRule) + ' Of ' + num((TEN.counts || {}).openNotices)
          + ' open notices, ' + num(((TEN.counts || {}).bySpeciality || {}).unclassified)
          + ' carry no recognised speciality term in their title at all. Read the whole list on the '
          + link(B.hubPages.frameworks, 'tenders page') + '.</p>';
      } else {
        out += '<div class="scroll"><table><tr><th>Notice</th><th>Buyer</th><th>Published</th>'
          + '<th>Closes</th><th class="n">Value</th></tr>'
          + ns.map(function (n) {
            return '<tr><td>' + link(n.url, n.title) + '<br><span class="src">' + esc(n.source || '')
              + (n.cpv ? ' · Common Procurement Vocabulary (CPV) ' + esc(n.cpv) : '')
              + '</span></td><td>' + esc(n.buyer || NV) + '</td><td>' + esc(ukdate(n.date))
              + '</td><td>' + esc(ukdate((n.closingDate || '').slice(0, 10))) + '</td>'
              + '<td class="n">' + (n.valueAmount == null ? 'not published' : money(n.valueAmount))
              + '</td></tr>';
          }).join('') + '</table></div>'
          + '<p class="src">Source: ' + esc(TEN.source || NV) + ', as held in '
          + 'data/open-tenders.json, ' + asOf(parseUk(TEN.dataAsOf)) + '. ' + esc(TEN.scopeRule || '')
          + '</p>';
      }
    }

    if (t.digital) {
      var dln = (B.sources || {})['digital-lane.json'] || {};
      var don = B.digitalOpenNotices || [], dme = B.digitalMarketEngagement || [];
      out += '<h3>Digital and technology notices now open</h3>';
      out += don.length
        ? '<div class="scroll"><table><tr><th>Notice</th><th>Buyer</th><th>Published</th>'
          + '<th>Closes</th><th class="n">Value</th></tr>'
          + don.map(function (n) {
            return '<tr><td>' + link(n.url, n.title) + '<br><span class="src">' + esc(n.source || '')
              + (n.stage ? ' · ' + esc(n.stage) : '')
              + (n.cpv ? ' · Common Procurement Vocabulary (CPV) ' + esc(n.cpv) : '')
              + '</span></td><td>' + esc(n.buyer || NV) + '</td><td>' + esc(ukdate(n.date))
              + '</td><td>' + esc(ukdate((n.closingDate || '').slice(0, 10)) || NV) + '</td>'
              + '<td class="n">' + (n.valueAmount == null ? 'not published' : money(n.valueAmount))
              + '</td></tr>';
          }).join('') + '</table></div>'
        : '<p>No digital or technology notice is open in this reading.</p>';
      if (dme.length) {
        out += '<h3>Digital market engagement open to suppliers</h3>'
          + '<div class="scroll"><table><tr><th>Exercise</th><th>Authority</th><th>Category</th>'
          + '<th>Opens</th><th>Deadline</th></tr>'
          + dme.map(function (m) {
            return '<tr><td>' + link(m.url, m.title) + (m.ref ? '<br><span class="src">reference '
              + esc(m.ref) + '</span>' : '') + '</td><td>' + esc(m.authority || NV) + '</td>'
              + '<td>' + esc(m.category || NV) + '</td><td>' + esc(ukdate(m.opens) || NV)
              + '</td><td>' + esc(ukdate(m.deadline) || NV) + '</td></tr>';
          }).join('') + '</table></div>'
          + '<p class="src">Preliminary market engagement is the stage before a tender: it is '
          + 'where an early-stage supplier can still shape what gets specified.</p>';
      }
      out += '<p class="src">Source: ' + esc(dln.source || NV) + ', as held in '
        + 'data/digital-lane.json, ' + asOf(dln.dataAsOf) + '. This is the digital lane of the '
        + 'same two feeds as the medical rows above, carried here because the digital '
        + 'specialities have no Clinical Evidence Library band and so cannot be filtered out of '
        + 'the medical feed. ' + esc(dln.scopeNote || '') + '</p>';
    }

    out += '<h3>Awards published but not yet started</h3>';
    if (!PEND) {
      out += gapNote('data/pending-awards.json', parseUk((B.sources['pending-awards.json'] || {}).dataAsOf));
    } else {
      var aw = PEND.awards || [];
      out += aw.length
        ? '<div class="scroll"><table><tr><th>Framework or contract</th><th>Buyer</th>'
          + '<th>Awarded</th><th>Runs</th><th class="n">Suppliers named</th></tr>'
          + aw.map(function (a) {
            return '<tr><td>' + link(a.url, a.title) + '<br><span class="src">reference '
              + esc(a.reference || NV) + '</span></td><td>' + esc(a.buyer || NV) + '</td>'
              + '<td>' + esc(ukdate(a.awardDate)) + '</td><td>'
              + span(a.contractStart, a.contractEnd, function (x) { return esc(ukdate(x)); })
              + (a.contractExtendedEnd ? ' (extendable to ' + esc(ukdate(a.contractExtendedEnd)) + ')' : '')
              + '</td><td class="n">' + num((a.noticeSuppliers || []).length) + '</td></tr>';
          }).join('') + '</table></div>'
          + '<p class="src">Every pending award the Hub holds, across all specialities. A '
          + 'framework that has been awarded but has not started is the one you can still plan '
          + 'around. Source: ' + esc(PEND.source || NV) + ', ' + asOf(parseUk(PEND.dataAsOf)) + '.</p>'
        : '<p>No award in the Hub’s set has been published but not yet started in this reading.</p>';
    }

    out += '<h3>What the incumbents have been winning lately, in any speciality</h3>';
    if (!sp) {
      out += '<p><span class="nv">' + NV + '</span>: no competitor set for this speciality, so no '
        + 'recent award rows can be listed for it.</p>';
    } else {
      out += '<p class="note"><b>This is incumbent activity, not activity in your market.</b> '
        + 'These are the most recent NHS award rows the Hub holds for the companies in the '
        + esc(sp.label) + ' competitor set, <b>across every speciality they sell into</b>. Many '
        + 'will have nothing to do with ' + esc(sp.label) + '. It is here to show how often these '
        + 'companies are in front of NHS buyers and what else they are selling them, not to '
        + 'size your market. The market activity is the open tenders and pending awards above.</p>';
      var recent = [];
      (sp.suppliers || []).forEach(function (r) {
        (r.awards || []).forEach(function (a) { recent.push({ co: r.co, a: a }); });
      });
      recent.sort(function (x, y) { return (y.a.date || '').localeCompare(x.a.date || ''); });
      out += recent.length
        ? '<div class="scroll"><table><tr><th>Company</th><th>Award</th><th>Buyer</th>'
          + '<th>Date</th><th class="n">Value</th></tr>'
          + recent.slice(0, 15).map(function (x) {
            return '<tr><td>' + esc(x.co) + '</td><td>' + link(x.a.url, x.a.title) + '</td>'
              + '<td>' + esc(x.a.buyer || NV) + '</td><td>' + esc(ukdate(x.a.date)) + '</td>'
              + '<td class="n">' + (x.a.valueAmount == null ? 'not published' : money(x.a.valueAmount))
              + '</td></tr>';
          }).join('') + '</table></div>'
          + '<p class="src">The 15 most recent of the ' + recent.length + ' award rows the Hub '
          + 'carries for this competitor set (up to ' + B.awardsPerCompany + ' per company). '
          + 'Source: Find a Tender and Contracts Finder notices, Open Government Licence, '
          + asOf(parseUk((B.sources['company-awards.json'] || {}).dataAsOf)) + '.</p>'
        : '<p>No award rows are held for this competitor set.</p>';
    }
    return out;
  }

  /* 7 — the gap the innovator is claiming */
  function s7(st) {
    var sp = B.specialities[st.spec], t = typeOf(st.type);
    var fws = (sp && sp.frameworks) || [];
    var keys = ((B.stakeholderTemplates || {})[t.tpl] || []).map(function (k) {
      return ((B.stakeholderRoles || {})[k] || {}).role || k;
    });
    var slug = sp && sp.tenderSlug;
    var open = (TEN && slug) ? (TEN.notices || []).filter(function (n) { return n.speciality === slug; }).length : null;

    var side = '<h3>The evidence this paragraph has to survive</h3><ul class="note">'
      + '<li><b>Incumbents:</b> ' + (sp ? num(sp.supplierCount) + ' companies in the Hub’s '
        + 'researched ' + esc(sp.label) + ' set, ' + num(sp.matchedCount) + ' of them with NHS '
        + 'award rows' : 'no researched set for this speciality') + '. (Section 3.)</li>'
      + '<li><b>Route:</b> ' + (fws.length ? fws.map(function (f) {
          return esc(f.name) + (f.ends ? ' (runs to ' + esc(f.ends) + ')' : '');
        }).join('; ')
        : 'no NHS Supply Chain framework matched')
      + (t.digital ? '; plus ' + ((B.digitalFrameworks || []).length) + ' digital and technology '
        + 'agreements and ' + ((B.otherBodies || []).filter(function (r) { return r.digital; }).length)
        + ' other-body digital frameworks' : '') + '. (Section 4.)</li>'
      + '<li><b>Who has to agree:</b> ' + (keys.length ? esc(keys.join(', '))
        : 'no template held') + '. (Section 5.)</li>'
      + '<li><b>Open tenders carrying this speciality tag:</b> '
      + (open == null ? 'the feed could not be filtered for this speciality'
        : num(open)) + '. (Section 6.)</li>'
      + '</ul><p class="src">Every figure in this list is the same figure, from the same source, '
      + 'as the section it names. Nothing here is new.</p>';

    return side
      + mine(st.org, 'State the gap you are claiming, against the evidence above. Name the '
        + 'incumbents you are not displacing as well as the ones you are. If the evidence above '
        + 'says the ground is already held, say what you do that the holders do not, and how you '
        + 'know. A funder reads this paragraph next to that table.',
        'The gap, named against the incumbents and the route above.', 'inr-w6')
      + mine(st.org, 'What would change your mind? Name the result, the comparator or the price '
        + 'point at which your claim stops holding. An applicant who can answer this is the one '
        + 'who gets funded.',
        'The condition under which your own claim fails.', 'inr-w7');
  }

  /* 8 — sources and date */
  function s8(st) {
    var S = B.sources || {}, rows = Object.keys(S).sort().map(function (k) {
      var v = S[k] || {};
      var d = v.dataAsOf || v.asOf || v.verifiedOn || v.checkedAt || v.pageLastUpdated || null;
      var src = v.source || v.sourceRule || v.rule || v.note || v.laneRule || '';
      if (v.sourceUrls) {
        src += ' ' + Object.keys(v.sourceUrls).map(function (n) {
          return link(v.sourceUrls[n], n);
        }).join(', ');
      }
      /* A date is printed in UK form; a sentence recording how a file was checked is
         printed as written, because it says more than a date would. */
      var when = !d ? '<span class="nv">' + NV + '</span>'
        : (/^\d{4}-\d{2}-\d{2}/.test(String(d)) ? esc(ukdate(d)) : esc(String(d)));
      return '<tr><td>' + esc(k) + '</td><td>' + when + '</td><td>' + src + '</td></tr>';
    }).join('');

    var out = '<div class="scroll"><table><tr><th>Hub data file</th>'
      + '<th>Date that source was last read</th><th>What it is and where it came from</th></tr>'
      + rows + '</table></div>';
    out += '<p class="note"><b>Report generated ' + today() + '</b>'
      + (st.org ? ' for ' + esc(st.org) : '')
      + '. Each section above carries its own “live as of” date, which is the date the '
      + 'source was read, not the date this report was opened. Where a source could not be read, '
      + 'the section says so and shows the last good reading the Hub holds. Nothing is '
      + 'substituted and nothing is omitted silently.</p>';
    if (GAPS.length) {
      out += '<div class="gap"><b>' + GAPS.length + ' source'
        + (GAPS.length > 1 ? 's' : '') + ' could not be read when this report was generated:</b> '
        + GAPS.map(esc).join(', ') + '. The sections that use them say so in place of a figure. '
        + 'Regenerate the report later for a live read.</div>';
    }
    out += '<p class="note"><b>What this report is not.</b> It is not an endorsement of the '
      + 'product, and it contains no estimate, score or projection. Every factual row is a row '
      + 'from a named published source with a link to it. Everything in a gold dashed box was '
      + 'written by ' + esc(st.org || 'the applicant') + ' and has not been checked by the '
      + 'Medical Sales Intelligence Hub. A reader who wants to check a figure should follow its '
      + 'link to the source, not cite this report.</p>';
    out += '<p class="note">Data in this report is © Elevate and Thrive Ltd 2026 and is '
      + 'supplied to the subscriber who generated it for use in their own funding application or '
      + 'investor materials. Compiled in part from Open Government Licence sources, each named '
      + 'above. Terms: ' + link('https://medsalesintelligencehub.co.uk/terms/',
        'medsalesintelligencehub.co.uk/terms') + '.</p>';
    return out;
  }

  /* At a glance. Each tile is a figure a section below prints, from the same source, read
     back at the top so a change of picker shows at once what moved. Nothing here is new:
     the tile names the section that carries the figure and its source. */
  function glance(st) {
    var sp = B.specialities[st.spec], fws = (sp && sp.frameworks) || [];
    var slug = sp && sp.tenderSlug, spl = specLabel(st.spec);
    var open = (TEN && slug) ? (TEN.notices || []).filter(function (n) { return n.speciality === slug; }).length : null;
    var nvb = '<span class="nv">' + NV + '</span>';
    function tile(n, big, txt) {
      return '<a class="gl" href="#inr-s' + n + '"><b>' + big + '</b><span>' + txt + '</span>'
        + '<i>Section ' + n + '</i></a>';
    }
    var t = [];
    t.push(tile('3', sp ? num(sp.supplierCount) : nvb, sp
      ? 'companies in the Hub’s researched ' + esc(spl) + ' supplier set, '
        + num(sp.matchedCount) + ' with an NHS award row'
      : 'the Hub holds no researched supplier set for ' + esc(spl) + ' yet'));
    var f = fws[0];
    t.push(tile('4', f ? (f.ends ? esc(f.ends) : nvb) : nvb, f
      ? esc(f.name) + (f.ends ? ' runs to this date' : '') + (fws.length > 1 ? ', one of ' + fws.length + ' frameworks' : '')
      : 'no NHS Supply Chain framework matched to ' + esc(spl)));
    var RG = (B.regionalSupport || {}).regions || {}, m = st.geo === 'national' ? null : icbByCode(st.geo);
    var R = m && RG[m.region];
    if (R) {
      var n = 0, hit = 0;
      (R.groups || []).forEach(function (g) {
        (g.rows || []).forEach(function (r) { n++; if ((r.specs || []).indexOf(st.spec) >= 0) hit++; });
      });
      t.push(tile('5', String(n), 'research and innovation bodies in ' + esc(m.region)
        + (hit ? ', ' + hit + ' naming ' + esc(spl) : '')));
    } else {
      t.push(tile('5', m ? esc(m.code) : (ICB ? num(ICB.count) : nvb), m
        ? esc(m.name) + ', its board and executives by role'
        : 'Integrated Care Boards in England; pick one to see its roles'));
    }
    t.push(tile('6', open == null ? nvb : num(open), 'open tender notices carrying the '
      + esc(spl) + ' tag in the Hub’s latest reading'));
    return '<div class="glance">' + t.join('') + '</div>';
  }

  /* ------------------------------------------------------------------ render */

  function render(st) {
    var E = EMPHASIS[st.purpose];
    function em(n) { return '<p class="emph">' + esc(E[n]) + '</p>'; }

    var specOpts = (B.specialityList || []).slice().sort(function (a, b) {
      return String(a.label).localeCompare(String(b.label));
    }).map(function (s) {
      var has = !!B.specialities[s.id];
      return '<option value="' + esc(s.id) + '"' + (s.id === st.spec ? ' selected' : '') + '>'
        + esc(specLabel(s.id)) + (has ? '' : ' (no competitor set held)') + '</option>';
    }).join('');
    var typeOpts = TYPES.map(function (t) {
      return '<option value="' + t.id + '"' + (t.id === st.type ? ' selected' : '') + '>'
        + esc(t.label) + '</option>';
    }).join('');
    var stageOpts = STAGES.map(function (s) {
      return '<option value="' + s.id + '"' + (s.id === st.stage ? ' selected' : '') + '>'
        + esc(s.label) + '</option>';
    }).join('');
    var purpOpts = PURPOSES.map(function (p) {
      return '<option value="' + p.id + '"' + (p.id === st.purpose ? ' selected' : '') + '>'
        + esc(p.label) + '</option>';
    }).join('');
    var geoOpts = '<option value="national"' + (st.geo === 'national' ? ' selected' : '')
      + '>England, national</option>'
      + icbList().slice().sort(function (a, b) {
        return String(a.name).localeCompare(String(b.name));
      }).map(function (m) {
        return '<option value="' + esc(m.code) + '"' + (m.code === st.geo ? ' selected' : '') + '>'
          + esc(m.name) + '</option>';
      }).join('');

    var head = '<div class="band dark"><div class="col">'
      + '<div class="eyebrow">Medical Sales Intelligence Hub · Innovator Market Analysis Report</div>'
      + '<h1 contenteditable="true" id="inr-title">' + esc(specLabel(st.spec))
      + ': NHS market analysis</h1>'
      + '<p>Eight sections of NHS market evidence for an early-stage innovator, generated '
      + today() + ' from the Hub’s own data. Every factual row carries its source link and '
      + 'the date that source was read. The boxes with a gold dashed border are yours to write: '
      + 'they are labelled as yours, and that label prints, so a grant assessor or an investor '
      + 'can always tell your claim from the Hub’s evidence.</p>'
      + '<div class="pick">'
      + '<div><label for="inr-org">Your organisation (printed on every page)</label>'
      + '<input id="inr-org" type="text" maxlength="90" value="' + esc(st.org)
      + '" placeholder="Your company or university"></div>'
      + '<div><label for="inr-spec">Speciality</label><select id="inr-spec">' + specOpts + '</select></div>'
      + '<div><label for="inr-type">Product type</label><select id="inr-type">' + typeOpts + '</select></div>'
      + '<div><label for="inr-stage">Stage</label><select id="inr-stage">' + stageOpts + '</select></div>'
      + '<div><label for="inr-geo">Geography</label><select id="inr-geo">' + geoOpts + '</select></div>'
      + '<div><label for="inr-purpose">Purpose</label><select id="inr-purpose">' + purpOpts + '</select></div>'
      + '</div>'
      + glance(st)
      + '<ul class="toc noprint">' + [['1', 'Product and claim'], ['2', 'Market'], ['3', 'Who sells here'],
        ['4', 'How it is bought'], ['5', 'Who decides'], ['6', 'Happening now'], ['7', 'Your gap'],
        ['8', 'Sources']].map(function (x) {
          return '<li><a href="#inr-s' + x[0] + '">' + x[0] + ' · ' + x[1] + '</a></li>';
        }).join('') + '</ul>'
      + '<p style="margin-top:18px"><button id="inr-save" type="button">Save edited copy</button>'
      + '<button id="inr-print" type="button">Print or save as PDF</button></p>'
      + '<p class="note noprint" style="color:#F5F1E8">Fill the gold boxes in, then save an edited '
      + 'copy: the download is a single file you can reopen, keep editing and print. Changing a '
      + 'picker regenerates the evidence and clears the boxes, so fill them in last.</p>'
      + '</div></div>';

    MOUNT.innerHTML = '<style>' + CSS + '</style><div class="inr" id="inr-page">' + head
      + sec('', '1', 'Your words · the only section the Hub does not write', 'The product and the claim', s1(st))
      + sec('warm', '2', 'Hub evidence · ' + asOf(B.generatedOn), 'The market', em(2) + s2(st))
      + sec('', '3', 'Hub evidence · ' + asOf(parseUk((B.sources['company-awards.json'] || {}).dataAsOf)),
            'Who already sells here', em(3) + s3(st))
      + sec('warm', '4', 'Hub evidence · ' + asOf((B.sources['frameworks.json'] || {}).dataAsOf),
            'How it gets bought', em(4) + s4(st))
      + sec('', '5', 'Hub evidence · ' + asOf(parseUk((B.sources['icb-watch.json'] || {}).asOf)),
            'Who decides', em(5) + s5(st))
      + sec('warm', '6', 'Hub evidence · ' + asOf(parseUk((B.sources['open-tenders.json'] || {}).dataAsOf)),
            'What is happening now', em(6) + s6(st))
      + sec('wine', '7', 'Your words · with the evidence beside it', 'The gap you are claiming', em(7) + s7(st))
      + sec('', '8', 'Hub evidence · every source, with its date', 'Sources and date', s8(st))
      + '<div class="band dark"><div class="col"><p class="foot">Generated from the Medical Sales '
      + 'Intelligence Hub on ' + today() + (st.org ? ' for ' + esc(st.org) : '')
      + '. Speciality: ' + esc(specLabel(st.spec)) + ' · product type: '
      + esc(typeOf(st.type).label) + ' · stage: ' + esc(stageLabel(st.stage))
      + ' · geography: ' + esc(geoLabel(st)) + ' · prepared as a '
      + esc((st.purpose === 'investment' ? 'investment deck' : 'grant funding application'))
      + ' input. medsalesintelligencehub.co.uk</p></div></div>'
      + '</div>';

    wire(st);
  }

  function wire(st) {
    /* Every table carries its column names on each cell, so on a phone the rows stack as
       labelled cards instead of a strip a reader has to scroll sideways. */
    [].forEach.call(MOUNT.querySelectorAll('table'), function (tb) {
      var hs = [].map.call(tb.querySelectorAll('tr:first-child th'), function (h) { return h.textContent; });
      if (!hs.length) return;
      tb.classList.add('stack');
      [].forEach.call(tb.querySelectorAll('tr'), function (tr) {
        [].forEach.call(tr.children, function (td, i) {
          if (td.tagName === 'TD' && hs[i]) td.setAttribute('data-label', hs[i]);
        });
      });
    });
    [].forEach.call(MOUNT.querySelectorAll('button[data-tgl]'), function (b) {
      var box = document.getElementById(b.getAttribute('data-tgl')), lab = b.textContent;
      b.onclick = function () {
        var on = box.classList.toggle('showall');
        b.textContent = on ? 'Show the top 10 only' : lab;
      };
    });
    function val(id) { var e = document.getElementById(id); return e ? e.value : ''; }
    function go() {
      var next = {
        spec: val('inr-spec'), type: val('inr-type'), stage: val('inr-stage'),
        geo: val('inr-geo'), purpose: val('inr-purpose'), org: clean(val('inr-org'))
      };
      if (history.replaceState) {
        history.replaceState(null, '', '?spec=' + encodeURIComponent(next.spec)
          + '&type=' + encodeURIComponent(next.type) + '&stage=' + encodeURIComponent(next.stage)
          + '&geo=' + encodeURIComponent(next.geo) + '&purpose=' + encodeURIComponent(next.purpose)
          + '&org=' + encodeURIComponent(next.org));
      }
      render(next);
    }
    ['inr-spec', 'inr-type', 'inr-stage', 'inr-geo', 'inr-purpose'].forEach(function (id) {
      var e = document.getElementById(id);
      if (e) e.onchange = go;
    });
    var org = document.getElementById('inr-org');
    if (org) {
      org.onchange = go;
      org.onblur = function () { if (clean(this.value) !== st.org) go(); };
    }
    var pr = document.getElementById('inr-print');
    if (pr) pr.onclick = function () { window.print(); };
    var sv = document.getElementById('inr-save');
    if (sv) sv.onclick = function () { save(st); };
  }

  function save(st) {
    var page = document.getElementById('inr-page').cloneNode(true);
    /* The pickers and the buttons are the live tool, not the report: strip them so the
       saved file is the report as it stands, reopenable and printable on its own. The
       editable boxes stay editable in the saved copy, which is how an innovator keeps
       working on it after they close the Hub. */
    [].forEach.call(page.querySelectorAll('.pick,button,.noprint'), function (n) {
      n.parentNode.removeChild(n);
    });
    /* The toggle went with the buttons, so the saved copy shows every row. */
    [].forEach.call(page.querySelectorAll('.scroll'), function (n) { n.classList.add('showall'); });
    var who = st.org ? st.org.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '').toLowerCase() : 'innovator';
    var title = 'NHS market analysis: ' + specLabel(st.spec) + (st.org ? ', ' + st.org : '');
    var html = '<!doctype html><html lang="en-GB"><head><meta charset="utf-8">'
      + '<meta name="viewport" content="width=device-width,initial-scale=1">'
      + '<title>' + esc(title) + '</title>'
      + '<style>body{margin:0;background:#fff}' + CSS + '</style></head><body>'
      + page.outerHTML + '</body></html>';
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
    a.download = 'nhs-market-analysis-' + st.spec + '-' + who + '-'
      + new Date().toISOString().slice(0, 10) + '.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
})();
