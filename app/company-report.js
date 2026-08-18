/* Medical Sales Hub — Company Report (Stages 1–5)
   Mounts on #msh-company-report. Member types or picks a company; the page
   renders one report card, and Stage 5 turns that card into a printable
   interview pack — one document per supplier, sectioned by speciality.

   SPEC: docs/COMPANY-REPORT-METHOD.md. That document was written before this
   code and governs it — if this file and that document disagree, THIS FILE IS
   WRONG. Read it before changing anything below the Stage 2 divider.

   Stage 1 panels are READ FROM SOURCE (supplier-index.json merged with the
   human-curated supplier-seed.json). Stage 3 is also read from source
   (data/company-financials.json — Companies House facts, manual interim until
   the API key exists). Stages 2 and 4 are DERIVED, so per root rule 14 each
   one prints the rule it was derived under, refuses to fire on thin evidence,
   and has an honest empty state naming what is missing. Stage 5 adds no new
   claims: it re-presents panels 1–4, and a refused panel stays refused in the
   printed pack — named, never blanked.

   WHAT THIS FILE STILL DELIBERATELY DOES NOT DO
   ---------------------------------------------
   No market-share percentage, ever, and no arithmetic that could become one.
   Stage 4 publishes a FILING PROFILE: the count on the lot and each confirmed
   supplier's statutory accounts filing. Only matchConfidence === "confirmed"
   records feed it; a probable name-search match is shown as identity-not-
   confirmed and carries no figures. Inventing more than that is precisely the
   class of error that put 145 false job changes in front of paying members on
   24/07/2026. An absent panel here means "not built yet" or "refused on thin
   evidence" — the panel says which — never "nothing found". */
(function () {
  var MOUNT = document.getElementById('msh-company-report');
  if (!MOUNT) return;

  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  // Cache-buster changes once a day (matches the daily pipeline rebuild), not
  // on every page view — a per-millisecond buster defeats GitHub's/Fastly's
  // edge cache on every single request, which turns any GitHub-side hiccup
  // into a 100% member-facing failure instead of a partial one. 17/08/2026.
  var CB = '?cb=' + new Date().toISOString().slice(0, 10);
  var IDX = BASE + 'data/supplier-index.json' + CB;
  var SEED = BASE + 'data/supplier-seed.json' + CB;
  var SPECMAP = BASE + 'data/speciality-map.json' + CB;
  var PRODUCTS = BASE + 'data/supplier-products.json' + CB;
  var FIN = BASE + 'data/company-financials.json' + CB;
  var NHSSC = BASE + 'data/nhssc-cache.json' + CB;
  var FWDATA = BASE + 'data/frameworks.json' + CB;
  /* Eighth fetch. Tender and contract awards, matched to Hub companies by
     scripts/refresh_awards.py. Optional like the six before it: if it does not
     load, the award panels say so rather than reading as an empty company. */
  var AWARDS = BASE + 'data/company-awards.json' + CB;

  /* Ninth fetch. Brand marks, fetched ONCE at build time from each company's
     own website by scripts/refresh_logos.py and stored in this repository under
     assets/logos/. The marks themselves are served from the same host as every
     other file this page reads.

     THIS REPLACES A LIVE THIRD-PARTY CALL, AND THAT IS THE POINT. The report's
     only logo route used to be a third-party logo service (Clearbit), called
     live from this file while a member watched. That host stopped resolving,
     every report quietly fell through to the monogram, and nobody found out
     until somebody read the code on 18/08/2026. A mark that is committed here can only break in a
     commit, and verify.py reads every commit before it publishes.

     Optional, like the seven before it: if the file does not load, every
     company falls back to the monogram plate, which is a finished design in its
     own right rather than a hole where a logo should be. */
  var LOGOS = BASE + 'data/company-logos.json' + CB;

  /* Same palette constants as app/supplier-search.js — one house style. */
  var G = '#a8842c', INK = '#1d2733', DIM = '#75808d', LINE = '#e6e0d4',
      RED = '#b84a5c', GREEN = '#2e7d5b', SOFT = '#f7f4ee';

  /* Speciality lists run to the low hundreds. Rendering 164 names is not a
     report, it is a phone book — so the list is capped and the cap is stated
     in the prose next to the true total, never silently applied. */
  var MAX_SPEC_ROWS = 24;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); }

  /* Company-name key for matching OUR supplier records against the names NHS
     Supply Chain prints on its own contract launch briefs. The two vocabularies
     were never the same: the briefs say "GBUK Ltd", "GBUK Healthcare",
     "GBUK Enteral Limited" for one group we hold as "GBUK Group".
     Deliberately shallow — it drops only legal-form and generic trade words.
     Stripping more would start merging genuinely different companies, and
     medtech is full of similarly-named entities. */
  var CO_SUFFIX = /\b(ltd|limited|plc|llp|inc|corp|corporation|co|company|group|holdings|international|uk|u k|gb|healthcare|health care|health|medical|medica|med|products|solutions|systems|technologies|technology|devices|device)\b/g;
  function coKey(s) {
    var k = norm(s).replace(CO_SUFFIX, ' ');
    return k.replace(/\s+/g, ' ').trim();
  }
  function cmpName(a, b) {
    var x = String(a || '').toLowerCase(), y = String(b || '').toLowerCase();
    return x < y ? -1 : (x > y ? 1 : 0);
  }

  /* ---------------------------------------------------------------------
     HOUSE STYLESHEET — redesigned 18/08/2026.

     ONE stylesheet, shipped inside this file, used by BOTH the on-page card
     and the printable pack, so the two surfaces cannot drift apart. It is
     entirely self-contained: no external stylesheet, no web font, no CDN
     script — the Hub page must render this with zero third-party requests.

     Every selector is scoped under `.mcr`, so nothing here can reach the rest
     of the WordPress page, and WordPress's own theme CSS cannot reach in.

     Colours are the brand guide's, verbatim: Midnight Navy #0B1C33 with the
     signature 135deg navy gradient, Deep Gold #A8842C for labels and rules on
     light, Light Gold #E0BE8E for gold on navy, the D4AF7A→B8935A button
     gradient. Gold never carries body copy.

     The company's own colour is TWO custom properties, not one, because this
     report has two grounds: `--mcr-accent` is the shade painted on the navy
     masthead, `--mcr-accent-ink` the shade painted on the ivory card ground.
     Both are derived from the one sampled colour and each is proved against
     the ground it lands on before it is published — see accentOnNavy() and
     accentOnIvory() below for why one value could never serve both.

     They carry RULES AND EDGES: the masthead's top edge, the ring around the
     company's own mark, the bar on each part divider, card and stat-tile top
     borders, the lede's left edge, a flagged news item. Never body copy, and
     never a whole banner — the ground stays the house navy gradient, so a
     company with no colour at all gets a report that reads as the intended
     design rather than as one missing its branding. The company colour is a
     guest in a house design.
     --------------------------------------------------------------------- */
  var STYLE = [
    '.mcr{--mcr-navy:#0B1C33;--mcr-ink:#1d2733;--mcr-body:#37485a;--mcr-dim:#75808d;',
    '--mcr-gold:#a8842c;--mcr-line:#e6e0d4;--mcr-soft:#f7f4ee;',
    /* Two accents, two grounds — see accentOnNavy()/accentOnIvory(). The
       defaults here are the brand guide's own gold pairing, so a report that
       somehow renders before boot() still looks like the house design. */
    '--mcr-accent:#C49B5C;--mcr-accent-ink:#A8842C;',
    'font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;',
    'color:var(--mcr-body);font-size:14px;line-height:1.6;}',
    '.mcr *{box-sizing:border-box;}',
    '.mcr p{margin:0 0 10px;}',
    '.mcr a{color:var(--mcr-gold);font-weight:600;text-decoration:none;}',
    '.mcr a:hover{text-decoration:underline;}',

    /* --- report shell + masthead ------------------------------------- */
    '.mcr-report{border:1px solid var(--mcr-line);border-radius:14px;background:#fdfcf9;',
    'overflow:hidden;box-shadow:0 2px 16px rgba(11,28,51,.07);}',
    '.mcr-mast{position:relative;padding:26px 26px 20px;',
    'background:linear-gradient(135deg,#0B1C33 0%,#132B4A 55%,#1B3A5F 100%);',
    '-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr-mast:before{content:"";position:absolute;left:0;right:0;top:0;height:5px;',
    'background:var(--mcr-accent);-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr-mast-row{display:flex;gap:18px;align-items:center;flex-wrap:wrap;}',
    /* The plate the company's own mark sits on. The ring is the company's
       colour on navy — the one place in the report where its colour touches
       its own mark. A company with no colour gets the house Antique Gold ring,
       which is what this line was before there were any colours to use. */
    '.mcr-logo{width:74px;height:74px;flex:0 0 74px;border-radius:14px;background:#fff;overflow:hidden;',
    'display:flex;align-items:center;justify-content:center;box-shadow:0 3px 12px rgba(0,0,0,.24);',
    'border:2px solid var(--mcr-accent);-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr-kicker{font-size:9.5px;letter-spacing:2.2px;text-transform:uppercase;font-weight:700;',
    'color:#E0BE8E;margin:0 0 7px;}',
    '.mcr-h1{color:#fff;font-size:27px;font-weight:700;line-height:1.16;letter-spacing:.2px;margin:0;}',
    '.mcr-tagline{color:rgba(237,231,220,.86);font-size:12.5px;font-weight:600;margin-top:6px;line-height:1.5;}',
    '.mcr-links{display:flex;gap:8px;flex-wrap:wrap;margin-left:auto;}',
    '.mcr-links a{font-size:11px;font-weight:700;letter-spacing:.4px;padding:8px 15px;border-radius:99px;',
    'background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.34);color:#fff;white-space:nowrap;}',
    '.mcr-links a:hover{background:rgba(255,255,255,.24);text-decoration:none;}',
    '.mcr-mast-meta{margin-top:16px;padding-top:12px;border-top:1px solid rgba(255,255,255,.16);',
    'font-size:11px;line-height:1.75;color:#9FB0C5;}',
    '.mcr-mast-meta b{color:#DBE3EE;font-weight:600;}',

    /* --- body, parts, cards ------------------------------------------ */
    '.mcr-body{padding:2px 22px 20px;}',
    /* Part dividers. The short bar sitting on the divider is the company's
       colour on light — it repeats the accent four or five times down a long
       report without ever becoming the report's own colour scheme. */
    '.mcr-part{position:relative;margin:28px 0 0;padding-top:16px;border-top:2px solid var(--mcr-line);}',
    '.mcr-part:before{content:"";position:absolute;left:0;top:-2px;width:38px;height:2px;',
    'background:var(--mcr-accent-ink);-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr-part-n{font-size:10px;letter-spacing:2px;text-transform:uppercase;font-weight:700;',
    'color:var(--mcr-gold);}',
    '.mcr-part-t{font-size:17px;font-weight:700;color:var(--mcr-navy);line-height:1.3;margin-top:3px;}',
    '.mcr-part-s{font-size:12.5px;color:var(--mcr-dim);line-height:1.6;margin-top:4px;max-width:66em;}',
    '.mcr-card{background:#fff;border:1px solid var(--mcr-line);border-radius:12px;',
    'padding:16px 18px;margin:14px 0 0;box-shadow:0 1px 2px rgba(29,39,51,.05);}',
    '.mcr-card-t{display:flex;align-items:center;gap:9px;font-size:11px;letter-spacing:1.4px;',
    'text-transform:uppercase;font-weight:700;color:var(--mcr-navy);margin:0 0 12px;}',
    '.mcr-card-t:before{content:"";flex:0 0 16px;height:2px;background:var(--mcr-gold);',
    '-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    /* The deliberate empty state. Thin data is the normal case here, so a
       panel with nothing behind it is drawn as a finished, quiet thing —
       dashed edge, no drop shadow, ivory ground — never as a blank box that
       reads as a page that failed to load. */
    '.mcr-card--empty{background:#faf8f3;border-style:dashed;border-color:#ded6c4;box-shadow:none;}',
    '.mcr-card--empty .mcr-card-t{color:#8d8677;}',
    '.mcr-card--empty .mcr-card-t:before{background:#cfc6b2;}',
    '.mcr-note{font-size:12.5px;color:var(--mcr-dim);line-height:1.65;}',
    '.mcr-good{font-size:12.5px;color:#2e7d5b;line-height:1.65;}',
    '.mcr-rule{margin:0 0 12px;padding:11px 14px;background:var(--mcr-soft);',
    'border-left:3px solid var(--mcr-gold);border-radius:0 8px 8px 0;font-size:12px;',
    'color:#4a5766;line-height:1.62;}',
    '.mcr-rule-h{display:block;font-size:9.5px;letter-spacing:1.6px;text-transform:uppercase;',
    'font-weight:700;color:var(--mcr-gold);margin-bottom:4px;}',

    /* --- chips, source lines, tables ---------------------------------- */
    '.mcr-chip{display:inline-block;background:#fff;color:#37485a;border:1px solid var(--mcr-line);',
    'border-radius:99px;padding:4px 11px;font-size:11.5px;font-weight:600;line-height:1.5;',
    'margin:0 6px 6px 0;}',
    '.mcr-chip--gold{background:#f6efdd;border-color:#e7d8b3;color:#7a5b14;}',
    '.mcr-src{margin-top:10px;padding-top:8px;border-top:1px dotted var(--mcr-line);',
    'font-size:11.5px;color:var(--mcr-dim);line-height:1.6;}',
    '.mcr-asof{white-space:nowrap;}',
    '.mcr-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;}',
    '.mcr-btn{cursor:pointer;background:linear-gradient(180deg,#D4AF7A,#B8935A);color:#0B1C33;',
    'border:0;border-radius:99px;padding:9px 18px;font-size:12.5px;font-weight:700;letter-spacing:.03em;',
    '-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr-btn:hover{background:linear-gradient(180deg,#E0BE8E,#C49B5C);}',

    /* --- the picker --------------------------------------------------- */
    '.mcr-lab{display:block;font-size:10.5px;font-weight:700;letter-spacing:1.4px;',
    'text-transform:uppercase;color:var(--mcr-dim);margin:0 0 5px;}',
    '.mcr-field{width:100%;max-width:520px;padding:11px 16px;border-radius:99px;',
    'border:1px solid var(--mcr-line);font:inherit;font-size:14.5px;color:var(--mcr-ink);',
    '-webkit-text-fill-color:var(--mcr-ink);caret-color:var(--mcr-ink);background:#fff;outline:none;}',
    '.mcr-field:focus{border-color:#C49B5C;box-shadow:0 0 0 3px rgba(196,155,92,.16);}',
    '.mcr-quick{cursor:pointer;background:#fff;border:1px solid var(--mcr-line);border-radius:99px;',
    'padding:6px 13px;font-size:12px;font-weight:600;color:var(--mcr-navy);}',
    '.mcr-quick:hover{background:var(--mcr-soft);border-color:#C49B5C;}',

    /* --- phones ------------------------------------------------------- */
    '@media (max-width:640px){',
    '.mcr-body{padding:2px 13px 16px;}',
    '.mcr-mast{padding:20px 16px 16px;}',
    '.mcr-mast-row{gap:13px;}',
    '.mcr-logo{width:54px;height:54px;flex:0 0 54px;border-radius:11px;}',
    '.mcr-h1{font-size:20.5px;}',
    '.mcr-links{margin-left:0;width:100%;}',
    '.mcr-card{padding:14px 14px;border-radius:11px;}',
    '.mcr-part-t{font-size:15.5px;}',
    '}',

    /* --- print: the downloadable pack --------------------------------- */
    '@media print{',
    '.mcr-report{border:0;box-shadow:none;border-radius:0;}',
    '.mcr-body{padding:0;}',
    '.mcr-card{box-shadow:none;break-inside:avoid;page-break-inside:avoid;margin-top:10px;}',
    '.mcr-part{break-before:auto;break-after:avoid;page-break-after:avoid;}',
    '.mcr-btn{display:none;}',
    '.mcr a{text-decoration:none;}',
    '}'
  ].join('');

  /* Injected once. A <style> element set through innerHTML is applied by the
     browser (unlike a <script>), so this needs no DOM plumbing beyond being
     present — and because it is written by this file rather than stored in the
     page, WordPress's texturiser and wpautop never see it. */
  var STYLE_ID = 'mcr-style';
  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var el = document.createElement('style');
    el.id = STYLE_ID;
    el.appendChild(document.createTextNode(STYLE));
    (document.head || document.documentElement).appendChild(el);
  }

  /* Every panel on the report is one card: an uppercase title with a short
     gold rule, then the body. A panel whose whole body is one honest empty
     note is drawn in the deliberate empty style instead — most companies are
     thin, so that state is the common one and it must read as finished. */
  function sec(title, html) {
    var body = String(html == null ? '' : html);
    var single = /^\s*<div class="mcr-note"/.test(body) &&
                 body.indexOf('mcr-note') === body.lastIndexOf('mcr-note');
    return '<section class="mcr-card' + (single ? ' mcr-card--empty' : '') + '">' +
      '<div class="mcr-card-t">' + title + '</div>' + body + '</section>';
  }
  /* Every honest empty state goes through here, so they all look the same and
     none of them can be mistaken for a zero finding. */
  function gap(text) {
    return '<div class="mcr-note">' + text + '</div>';
  }
  function good(text) {
    return '<div class="mcr-good">' + text + '</div>';
  }
  /* The printed derivation. Stage 2 panels are computed claims; this box is
     the reader's means of judging them. It is not decoration — do not drop it
     to save space. */
  function rule(text) {
    return '<div class="mcr-rule"><b class="mcr-rule-h">How this was derived</b>' + text + '</div>';
  }
  /* One treatment for every "where this came from, and when" line: a dotted
     rule, then the link and the read date together. A source and its date are
     one fact, so they are never split across the panel. */
  function srcLine(html) {
    return '<div class="mcr-src">' + html + '</div>';
  }
  function asOf(text) {
    return '<span class="mcr-asof">' + text + '</span>';
  }
  /* The feeds stamp themselves ISO; the Hub writes dates the way its members
     do (root rule 1). Display only — an unrecognised string is printed
     verbatim rather than guessed at, so nothing is ever reformatted into a
     date it did not state. */
  function dateUK(v) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v == null ? '' : v).trim());
    return m ? (m[3] + '/' + m[2] + '/' + m[1]) : String(v == null ? '' : v);
  }

  /* ---------------------------------------------------------------------
     Merge: index + human-curated seed.
     Same rule as app/meeting-prep.js — supplier-seed.json is human-owned and
     is never overwritten by the index build, so where the seed has a curated
     value it wins; a supplier present only in the seed is unioned in so a new
     entry shows immediately, independent of the refresh cadence.
     --------------------------------------------------------------------- */
  function mergeSuppliers(index, seed) {
    var suppliers = (index && index.suppliers) ? index.suppliers.slice() : [];
    var seedList = (seed && seed.suppliers) || [];
    var seedMap = {};
    seedList.forEach(function (s) { seedMap[s.name] = s; });
    suppliers.forEach(function (s) {
      var sd = seedMap[s.name];
      if (!sd) return;
      if (sd.voice) s.voice = sd.voice;
      if (sd.note) s.note = sd.note;
      if (sd.image) s.image = sd.image;
      if (sd.deepDive) s.deepDive = sd.deepDive;
      if (sd.brand) s.brand = sd.brand;
      if (sd.products && sd.products.length) s.products = sd.products;
      if (sd.frameworks && sd.frameworks.length) s.frameworks = sd.frameworks;
      if (sd.specialities && sd.specialities.length) s.specialities = sd.specialities;
      if (sd.repsWatch) s.repsWatch = sd.repsWatch;
    });
    var have = {};
    suppliers.forEach(function (s) { have[s.name] = 1; });
    seedList.forEach(function (s) { if (!have[s.name]) { s.curated = true; suppliers.push(s); } });
    return suppliers;
  }

  /* ---------------------------------------------------------------------
     Speciality canonicalisation — lifted from app/meeting-prep.js on purpose.
     Three speciality vocabularies had drifted apart and were being matched by
     exact string equality, so a lookup miss came back as an EMPTY LIST. On a
     panel like "Same speciality, no shared framework" an empty list reads as
     "nobody else sells this", when the truth was "the lookup failed". That is
     a false finding dressed as a finding, so the same reconciliation is used
     here. It falls back to exact matching if the map cannot be loaded, and
     says so in the panel when it does.
     --------------------------------------------------------------------- */
  function specCtx(specMap, prodFile) {
    var CANON = (specMap && specMap.canonicalSpecialities) || null;
    var SMAP = (specMap && specMap.supplierSpecialityMap) || null;
    var PRODS = (prodFile && prodFile.suppliers) || null;
    var LABEL_TO_ID = {}, ID_TO_LABEL = {};
    if (CANON) CANON.forEach(function (c) { LABEL_TO_ID[c.label] = c.id; ID_TO_LABEL[c.id] = c.label; });

    function verifiedRangeFor(name) {
      if (!PRODS || !name) return null;
      if (PRODS[name]) return PRODS[name];
      for (var k in PRODS) {
        var al = PRODS[k].aliases || [];
        if (al.indexOf(name) !== -1) return PRODS[k];
      }
      return null;
    }
    /* A supplier string may map to SEVERAL canonical ids where it genuinely
       spans both, so a supplier stays reachable from either side of its real
       market rather than an arbitrary single pick. Child specialities roll up
       into their parent (blood collection sits under vascular access, with a
       different buying stakeholder) — without the rollup, picking the parent
       silently misses every child-only supplier. */
    function canonIds(list) {
      var out = {};
      (list || []).forEach(function (s) {
        var m = SMAP && SMAP[s];
        if (m && m.to) m.to.forEach(function (id) { out[id] = 1; });
        else if (LABEL_TO_ID[s]) out[LABEL_TO_ID[s]] = 1;
      });
      if (CANON) CANON.forEach(function (c) { if (c.parent && out[c.parent]) out[c.id] = 1; });
      return Object.keys(out);
    }
    /* A supplier's specialities and its verified product tags were
       unconnected, so a supplier could sell a whole category and still be
       unreachable from it. Deriving the extra ids from the tagged range fixes
       that without editing the curated seed. */
    function supplierSpecIds(s) {
      var ids = canonIds(s && s.specialities);
      var v = verifiedRangeFor(s && s.name);
      if (v) {
        var seen = {};
        ids.forEach(function (i) { seen[i] = 1; });
        (v.products || []).forEach(function (p) { if (p.s) seen[p.s] = 1; });
        ids = Object.keys(seen);
      }
      return ids;
    }
    function sharedWith(subIds, other) {
      var B = supplierSpecIds(other), out = [];
      subIds.forEach(function (id) { if (B.indexOf(id) !== -1) out.push(id); });
      return out;
    }
    return {
      canonical: !!SMAP,
      count: CANON ? CANON.length : 0,
      label: function (id) { return ID_TO_LABEL[id] || id; },
      ids: supplierSpecIds,
      shared: sharedWith
    };
  }

  /* Exact-string fallback, used only when speciality-map.json is unreachable.
     Named separately so the panel can say which route produced the list. */
  function rawShared(sub, other) {
    var a = (sub && sub.specialities) || [], b = (other && other.specialities) || [], out = [];
    a.forEach(function (x) { if (b.indexOf(x) !== -1) out.push(x); });
    return out;
  }

  /* ---------------------------------------------------------------------
     STAGE 1 — read from source, nothing computed.
     --------------------------------------------------------------------- */
  function chip(text, tone) {
    return '<span class="mcr-chip' + (tone === 'gold' ? ' mcr-chip--gold' : '') + '">' +
      esc(text) + '</span>';
  }

  function identity(s) {
    /* Image with monogram fallback — copied from supplier-search.js so the two
       tools cannot drift apart visually. */
    var _w = String(s.name || '').replace(/^the\s+/i, '').split(/[\s\-—,\.]+/).filter(Boolean);
    var inits = esc((/^[A-Za-z0-9]{2,4}$/.test(_w[0] || '') ? _w[0] : _w.slice(0, 2).map(function (w) { return w[0]; }).join('')).toUpperCase());
    var ph = '<div style="width:56px;height:56px;flex:0 0 56px;border-radius:10px;background:#efe9db;border:1px solid ' + LINE + ';display:flex;align-items:center;justify-content:center;font-weight:700;color:' + G + ';font-size:16px;">' + inits + '</div>';
    var thumb = s.image
      ? '<img src="' + esc(s.image) + '" alt="" referrerpolicy="no-referrer" loading="lazy" style="width:56px;height:56px;flex:0 0 56px;border-radius:10px;object-fit:contain;background:#fff;border:1px solid ' + LINE + ';" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div style="display:none;width:56px;height:56px;flex:0 0 56px;border-radius:10px;background:#efe9db;border:1px solid ' + LINE + ';align-items:center;justify-content:center;font-weight:700;color:' + G + ';font-size:16px;">' + inits + '</div>'
      : ph;
    var h = '<div style="display:flex;gap:13px;align-items:flex-start;">' + thumb + '<div><div style="font-size:21px;font-weight:700;color:' + INK + ';line-height:1.25;">' + esc(s.name) +
      (s.autoDetected ? ' <span style="font-size:10px;font-weight:700;letter-spacing:.06em;color:#7a5b14;background:#f3e8cf;border-radius:99px;padding:2px 8px;vertical-align:3px;">AUTO — VERIFY AT SOURCE</span>' : '') + '</div>' +
      (s.note ? '<p style="margin:5px 0 0;font-size:13.5px;color:#37485a;line-height:1.55;">' + esc(s.note) + '</p>' : '') +
      '</div></div>';

    if (s.specialities && s.specialities.length) {
      h += '<div style="margin-top:9px;">' + s.specialities.map(function (x) { return chip(x, 'gold'); }).join('') + '</div>';
    } else {
      h += '<div style="margin-top:9px;">' + gap('No speciality recorded for this company yet.') + '</div>';
    }

    if (s.voice && (s.voice.line || s.voice.angle)) {
      h += sec('How they sell', '<div style="font-size:13.5px;color:#37485a;line-height:1.6;">' +
        (s.voice.angle ? '<b style="color:' + INK + ';">' + esc(s.voice.angle) + '</b><br>' : '') +
        esc(s.voice.line || '') + '</div>');
    }
    return h;
  }

  /* ---------------------------------------------------------------------
     PRODUCT LISTING — scope set by Lou, 06/08/2026:
       tier 1  catalogue-verified — rows read from the NHS Supply Chain
               catalogue (NPC code, description, pack), via nhssc-cache.json;
       tier 2  also supply, not on a framework — items confirmed on the
               company's own website but absent from the catalogue
               (nhssc-cache notCatalogue, with the reason recorded);
       tier 3  the deep verified range where a full site crawl exists
               (supplier-products.json — GBUK so far), grouped by the
               company's own divisions;
       plus the curated headline products from the index, which for most of
       the 459 suppliers is currently ALL we hold — and the panel says so
       rather than letting five chips read as a complete range.
     --------------------------------------------------------------------- */
  function cacheRowsFor(s, cache) {
    var out = { items: [], notCat: [] };
    if (!cache) return out;
    var names = {}; names[s.name] = 1;
    (s.aliases || []).forEach(function (a) { names[a] = 1; });
    var prods = cache.products || {};
    for (var k in prods) {
      var rec = prods[k];
      if (rec && names[rec.supplier]) {
        (rec.items || []).forEach(function (it) { out.items.push(it); });
      }
    }
    var nc = cache.notCatalogue || {};
    for (var k2 in nc) {
      var r2 = nc[k2];
      if (r2 && names[r2.supplier]) out.notCat.push({ name: k2, reason: r2.reason || '' });
    }
    return out;
  }

  function deepRangeFor(s, prodFile) {
    var P = (prodFile && prodFile.suppliers) || null;
    if (!P) return null;
    if (P[s.name]) return P[s.name];
    for (var k in P) {
      if ((P[k].aliases || []).indexOf(s.name) !== -1) return P[k];
    }
    return null;
  }

  function productListing(s, ctx) {
    var cr = cacheRowsFor(s, ctx.cache);
    var deep = deepRangeFor(s, ctx.prodFile);
    var body = '';

    /* Coverage statement first, built from the same arrays rendered below,
       so the claim about completeness cannot drift from the rows. */
    var bits = [];
    if (cr.items.length) {
      var _n = {};
      cr.items.forEach(function (it) { _n[it.npc || (it.name + '|' + it.desc)] = 1; });
      bits.push(Object.keys(_n).length + ' catalogue-verified line(s)');
    }
    if (cr.notCat.length) bits.push(cr.notCat.length + ' item(s) confirmed off-catalogue');
    if (deep) bits.push((deep.products || []).length + ' product(s) from a full crawl of the company’s own site' + (deep.verified ? ' (verified ' + esc(deep.verified) + ')' : ''));
    if (bits.length) {
      body += '<div style="font-size:12px;color:' + DIM + ';margin:0 0 8px;">' + bits.join(' · ') + '.</div>';
    }

    if (cr.items.length) {
      /* The cache is keyed by SEARCH QUERY, so one catalogue line is reached by
         several queries and arrives several times: 113 rows for GBUK held only
         85 distinct NPCs. The NPC is the catalogue's own product code, so it is
         the identity. Dedupe on it, then group by the catalogue's product name
         and sort, because an unsorted table with repeats is not a listing. */
      var byNpc = {}, order = [];
      cr.items.forEach(function (it) {
        var k = it.npc || (it.name + '|' + it.desc);
        if (!byNpc[k]) { byNpc[k] = it; order.push(k); }
      });
      var uniq = order.map(function (k) { return byNpc[k]; });
      var fams = {}, famOrder = [];
      uniq.forEach(function (it) {
        var f = it.name || 'Other';
        if (!fams[f]) { fams[f] = []; famOrder.push(f); }
        fams[f].push(it);
      });
      famOrder.sort(cmpName);

      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:8px 0 4px;">In the NHS Supply Chain catalogue &mdash; verified entries</div>' +
        '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 8px;">' + uniq.length + ' distinct catalogue lines across ' + famOrder.length +
        ' product families, grouped by the catalogue&rsquo;s own product name and sorted. ' +
        (cr.items.length !== uniq.length ? (cr.items.length - uniq.length) + ' duplicate rows removed (the same NPC reached by more than one search). ' : '') +
        'The catalogue does not state which framework each line sits on, so these are grouped by product family, not by framework; the framework list above is the sourced answer to that question.</div>';

      body += famOrder.map(function (fam) {
        var rows = fams[fam].slice().sort(function (a, b) { return cmpName(a.desc, b.desc); }).map(function (it) {
          return '<tr>' +
            '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12.5px;color:#37485a;">' + esc(it.desc) + '</td>' +
            '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12px;color:' + G + ';font-weight:600;white-space:nowrap;">' + esc(it.npc) + '</td>' +
            '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12px;color:' + DIM + ';white-space:nowrap;">' + esc(it.pack) + '</td>' +
            '</tr>';
        }).join('');
        return '<div style="margin:0 0 10px;border:1px solid ' + LINE + ';border-radius:8px;background:#fff;overflow:hidden;">' +
          '<div style="padding:7px 10px;background:' + SOFT + ';font-size:12.5px;font-weight:700;color:' + INK + ';border-bottom:1px solid ' + LINE + ';">' +
          esc(fam) + ' <span style="font-weight:400;color:' + DIM + ';">&middot; ' + fams[fam].length + ' line(s)</span></div>' +
          '<div class="mcr-scroll"><table style="border-collapse:collapse;width:100%;min-width:460px;">' +
          '<tr><th style="text-align:left;padding:6px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">CATALOGUE DESCRIPTION</th>' +
          '<th style="text-align:left;padding:6px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">NPC</th>' +
          '<th style="text-align:left;padding:6px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">PACK</th></tr>' +
          rows + '</table></div></div>';
      }).join('');
    }

    if (cr.notCat.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">Also supply — not in the NHSSC catalogue</div>' +
        '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 6px;">Confirmed on the company’s own site or in its published range, absent from the catalogue — typically capital equipment or direct-supply lines. The recorded reason is shown; “not on a framework yet” is a statement about the catalogue, not about the product.</div>' +
        cr.notCat.map(function (n) {
          return '<div style="padding:6px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b style="color:' + INK + ';">' + esc(n.name) + '</b>' +
            (n.reason ? ' <span style="color:' + DIM + ';">· ' + esc(n.reason) + '</span>' : '') + '</div>';
        }).join('');
    }

    if (deep && deep.divisions && deep.divisions.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">Full verified range, by the company’s own divisions</div>' +
        (deep.filingRule ? '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 6px;">' + esc(deep.filingRule) + '</div>' : '') +
        deep.divisions.map(function (d) {
          return '<div style="padding:6px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b style="color:' + INK + ';">' + esc(d.name) + '</b>' +
            ' <span style="color:' + DIM + ';">· ' + d.products + ' product(s)' +
            (d.specialities && d.specialities.length ? ' · ' + d.specialities.map(esc).join(', ') : '') + '</span></div>';
        }).join('') +
        (deep.notSold ? '<div style="font-size:11.5px;color:#8a4a58;margin:6px 0 0;"><b>Verified absences:</b> ' + esc(deep.notSold) + '</div>' : '');
    }

    if (s.products && s.products.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">Headline products (curated)</div>' +
        s.products.map(function (p) { return chip(typeof p === 'string' ? p : (p && p.n) || '', ''); }).join('');
    }

    if (!body) {
      return sec('Products', gap('No product or brand indexed for this company yet — the range has not been captured, which is not the same as a company with no products.'));
    }

    /* The honest partial: headline chips alone are NOT a product listing. */
    if (!cr.items.length && !deep) {
      body += '<div style="font-size:11.5px;color:' + DIM + ';margin-top:8px;">The full listing for this company has not been captured yet: no catalogue match has been run and no site crawl exists. What is above is the curated headline set, not the range.</div>';
    }
    return sec('Products', body);
  }

  /* ---------------------------------------------------------------------
     FRAMEWORKS — read from NHS Supply Chain's own contract launch briefs
     (data/frameworks.json), not from our hand-curated tags.

     This replaced a hand-curated list that was badly incomplete: GBUK Group
     carried two frameworks while NHSSC's own briefs name it on twenty-four.
     That mattered beyond this panel, because the competitor panels are derived
     from framework co-listing — an incomplete framework list produced an
     incomplete competitor list, stated with the same confidence.
     --------------------------------------------------------------------- */
  function fwIndex(fwDoc) {
    var byKey = {};
    ((fwDoc && fwDoc.frameworks) || []).forEach(function (f) {
      (f.suppliers || []).forEach(function (nm) {
        var k = coKey(nm);
        if (!k) return;
        if (!byKey[k]) byKey[k] = [];
        byKey[k].push({ fw: f, matched: nm });
      });
    });
    return byKey;
  }

  /* Every framework whose brief names this company, under any of its recorded
     names. The verbatim string the brief used is kept and shown — a group that
     appears as "GBUK Enteral Limited" on one framework and "GBUK Ltd" on
     another is a fact about the register, not noise to tidy away. */
  function supplierFrameworks(s, ctx) {
    if (!ctx.fwByKey) return [];
    var keys = {}, out = [], seen = {};
    [s.name].concat(s.aliases || []).forEach(function (n) {
      var k = coKey(n);
      if (k) keys[k] = 1;
    });
    Object.keys(keys).forEach(function (k) {
      (ctx.fwByKey[k] || []).forEach(function (hit) {
        if (seen[hit.fw.url]) {
          if (seen[hit.fw.url].matched.indexOf(hit.matched) === -1) {
            seen[hit.fw.url].matched.push(hit.matched);
          }
          return;
        }
        seen[hit.fw.url] = { fw: hit.fw, matched: [hit.matched] };
        out.push(seen[hit.fw.url]);
      });
    });
    out.sort(function (a, b) { return cmpName(a.fw.name, b.fw.name); });
    return out;
  }

  /* An ended framework must not read as a current position. The Compare tab has
     refused an expired route since 05/08/2026; this panel printed the end date
     and left the reader to do the arithmetic, which on 07/08/2026 meant
     Medtronic, Boston Scientific and Abbott all showing a Transcatheter Heart
     Valve framework that stopped in September 2025 as though it were live.
     Derived from the date the panel already prints, so it cannot disagree with
     it. */
  function fwEnded(ends) {
    if (!ends) return '';
    var t = Date.parse(String(ends).trim());
    if (isNaN(t) || new Date(t) >= new Date()) return '';
    return ' <span style="background:#f2f2f2;border:1px solid #dcdcdc;color:#5b6675;font-size:10px;font-weight:700;letter-spacing:.06em;border-radius:99px;padding:1px 7px;">ENDED</span>';
  }

  function frameworks(s, ctx) {
    var hits = supplierFrameworks(s, ctx);
    var curated = (s.frameworks || []);

    if (!hits.length && !curated.length) {
      return sec('Frameworks', gap('No NHS Supply Chain contract launch brief names this company, and nothing is curated for it. Plenty of ranges are sold direct, off framework, and NHS Supply Chain is only one buying route, so read this as "not named on the briefs captured so far", never as proof they hold no place anywhere.'));
    }

    var body = '';
    if (hits.length) {
      body += rule('Every framework below names this company <b>on NHS Supply Chain&rsquo;s own contract launch brief</b> for that framework, the buying organisation&rsquo;s own page, captured ' +
        esc(dateUK((ctx.fwDoc && ctx.fwDoc.dataAsOf) || 'date not recorded')) + '. Nothing here is inferred from product ranges or specialities. The name in brackets is the exact wording the brief uses, which is often a group company rather than the group.' +
        (ctx.fwDoc && ctx.fwDoc.unparsedCount
          ? ' <b>Coverage:</b> ' + ctx.fwDoc.frameworkCount + ' of ' + (ctx.fwDoc.briefsSeen || 0) +
            ' published briefs parsed; ' + ctx.fwDoc.unparsedCount + ' refused because the supplier list did not match the count the page itself states. A framework in that group cannot appear here even if this company is on it.'
          : ''));

      body += '<div style="font-size:12px;color:' + DIM + ';margin:0 0 8px;">' + hits.length + ' framework(s) name this company.</div>';

      body += hits.map(function (h) {
        var f = h.fw;
        var lots = (f.supplierLots || {});
        var myLots = [];
        h.matched.forEach(function (m) { if (lots[m]) { myLots = myLots.concat(lots[m]); } });
        return '<div style="padding:9px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;line-height:1.55;">' +
          '<b>' + esc(f.name) + '</b>' +
          ' <span style="color:' + DIM + ';">(as &ldquo;' + h.matched.map(esc).join('&rdquo;, &ldquo;') + '&rdquo;)</span>' +
          '<br><span style="font-size:12.5px;color:#37485a;">' +
          (f.category ? esc(f.category) + ' &middot; ' : '') +
          (f.reference ? 'ref ' + esc(f.reference) + ' &middot; ' : '') +
          (f.starts ? esc(f.starts) : '') + (f.ends ? ' to ' + esc(f.ends) : '') + fwEnded(f.ends) +
          (f.supplyRoute ? ' &middot; ' + esc(f.supplyRoute) : '') +
          '</span>' +
          '<br><span style="font-size:12.5px;color:' + DIM + ';">' + f.supplierCount + ' suppliers on this framework' +
          (myLots.length ? ' &middot; this company on ' + myLots.map(esc).join(', ') : '') +
          ' &middot; <a href="' + esc(f.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">contract launch brief &#8599;</a></span>' +
          '</div>';
      }).join('');
    }

    if (curated.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:14px 0 4px;">Also tracked by hand</div>' +
        '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 6px;">Tender-watch notes: re-tender values, award criteria and award dates, which the launch briefs do not carry. Curated, not read from a brief.</div>' +
        curated.map(function (f) {
          return '<div style="padding:8px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;line-height:1.55;"><b>' + esc(f.name) + '</b>' +
            (f.value ? ' <span style="color:' + GREEN + ';font-weight:700;">' + esc(f.value) + '</span>' : '') +
            (f.dates ? ' <span style="color:' + DIM + ';">&middot; ' + esc(f.dates) + '</span>' : '') +
            (f.note ? '<br><span style="color:#37485a;font-size:12.5px;">' + esc(f.note) + '</span>' : '') + '</div>';
        }).join('');
    }
    return sec('Frameworks', body);
  }

  function alerts(s) {
    if (!(s.alerts && s.alerts.length)) {
      return sec('Alerts &amp; recalls', good('No current alert indexed for this company.'));
    }
    return sec('Alerts &amp; recalls', s.alerts.map(function (a) {
      /* 169 of the indexed alerts are plain strings (a curated research note)
         rather than the {date,title,detail} object. Rendering a string through
         the object path prints an empty date and an empty title, so the two
         shapes are handled separately. */
      if (typeof a === 'string') {
        return '<div style="padding:9px 11px;margin:0 0 7px;border-left:3px solid ' + LINE + ';background:#fff;border-radius:7px;font-size:13px;color:#37485a;line-height:1.6;">' + esc(a) + '</div>';
      }
      return '<div style="padding:9px 11px;margin:0 0 7px;border-left:3px solid ' + RED + ';background:#fff;border-radius:7px;font-size:13px;line-height:1.55;">' +
        '<b style="color:' + RED + ';">' + esc(a.date) + '</b> — <b>' + esc(a.title) + '</b>' +
        '<br><span style="color:#37485a;">' + esc(a.detail) + '</span>' +
        (a.use ? '<br><span style="color:' + G + ';">▸ ' + esc(a.use) + '</span>' : '') +
        (a.url ? ' <a href="' + esc(a.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">source ↗</a>' : '') +
        '</div>';
    }).join(''));
  }

  function press(s) {
    var all = s.news || [];
    /* The heading asserts two sources. A story carrying one would make that
       heading a false claim, so it is filtered out here rather than trusted to
       have been filtered upstream, and the drop is stated. */
    var ok = all.filter(function (n) { return ((n && n.sources) || []).length >= 2; });
    var dropped = all.length - ok.length;
    if (!ok.length) {
      return sec('Press · verified by 2+ sources',
        gap(all.length
          ? 'No story for this company clears the two-source bar. ' + all.length + ' single-sourced item(s) were held back rather than shown here.'
          : 'No corroborated press indexed. A story appears here only once two independent reputable outlets carry it, so an empty panel means nothing has cleared that bar — not that nothing was written.'));
    }
    var body = ok.map(function (nw) {
      var srcs = (nw.sources || []).map(function (x) {
        return x.url
          ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">' + esc(x.publisher) + ' ↗</a>'
          : esc(x.publisher);
      }).join(' · ');
      return '<div style="padding:8px 0;border-bottom:1px solid #f0ece3;font-size:13px;line-height:1.55;">' +
        '<span style="color:' + GREEN + ';font-weight:700;">✓</span> <b>' + esc(nw.headline) + '</b>' +
        (nw.date ? ' <span style="color:' + DIM + ';">· ' + esc(nw.date) + '</span>' : '') +
        '<br><span style="color:' + DIM + ';font-size:12px;">Corroborated by: </span>' + srcs + '</div>';
    }).join('');
    if (dropped > 0) {
      body += '<div style="font-size:12px;color:' + DIM + ';margin-top:6px;">' + dropped + ' further item(s) held back — single-sourced.</div>';
    }
    return sec('Press · verified by 2+ sources', body);
  }

  /* =====================================================================
     STAGE 2 — DERIVED. Everything below carries its rule and its floor.
     ===================================================================== */

  /* Frameworks the subject holds, keyed on a normalised name. Framework names
     are recorded free-text across 459 supplier records, so an exact-string key
     would split "NHS Supply Chain — IV Cannula" from the same framework typed
     with a hyphen and quietly halve every co-listing. */
  function fwList(s) {
    var out = [], seen = {};
    (s.frameworks || []).forEach(function (f) {
      var nm = f && f.name;
      if (!nm) return;
      var k = norm(nm);
      if (!k || seen[k]) return;
      seen[k] = 1;
      out.push({ name: nm, key: k });
    });
    return out;
  }
  function holdsFramework(rec, key) {
    var fs = (rec && rec.frameworks) || [];
    for (var i = 0; i < fs.length; i++) { if (fs[i] && norm(fs[i].name) === key) return true; }
    return false;
  }

  /* Returns either a renderable set of groups, or a refusal carrying the
     reason. It never returns a half-answer: the whole panel is withheld if any
     rendered name fails to resolve, per the method doc's invariant. */
  function coListing(sub, ctx) {
    var hits = supplierFrameworks(sub, ctx);
    if (!hits.length) return { ok: false, why: 'nofw' };
    var asOf = (ctx.fwDoc && ctx.fwDoc.dataAsOf) || '';
    /* A co-listing that cannot say when it was read is an undated claim. */
    if (!asOf) return { ok: false, why: 'nodate' };

    var groups = [], thin = [];
    hits.forEach(function (h) {
      var f = h.fw;
      var all = f.suppliers || [];
      /* EVIDENCE FLOOR. One supplier on a framework is a framework with one
         supplier, not a competitive field. */
      if (all.length < 2) { thin.push(f.name); return; }
      var mine = {};
      h.matched.forEach(function (m) { mine[String(m).toLowerCase()] = 1; });
      var others = all.filter(function (n) { return !mine[String(n).toLowerCase()]; });
      others.sort(cmpName);
      groups.push({
        name: f.name, total: all.length, others: others, url: f.url,
        reference: f.reference, ends: f.ends, lots: f.supplierLots || null
      });
    });
    if (!groups.length) return { ok: false, why: 'thin', thin: thin };
    return { ok: true, groups: groups, thin: thin, asOf: asOf };
  }

  function panelCoListed(sub, ctx, res) {
    var TITLE = 'Also on this framework';
    if (!res.ok) {
      if (res.why === 'nofw') {
        return sec(TITLE, gap('No NHS Supply Chain contract launch brief captured so far names ' + esc(sub.name) + ', so there is nothing to co-list. Ranges sold direct, off framework, appear on no brief at all, and NHS Supply Chain is only one buying route. Read this as a gap in what has been captured, not as a company standing alone in its market.'));
      }
      if (res.why === 'nodate') {
        return sec(TITLE, gap('The framework capture arrived without a capture date. A co-listing that cannot say when the data was read is an undated claim, so this panel is withheld.'));
      }
      var names = (res.thin || []).map(function (n) { return '<b>' + esc(n) + '</b>'; }).join(', ');
      return sec(TITLE, gap('Not shown. ' + esc(sub.name) + ' is named on ' + (res.thin || []).length +
        ' framework(s) &mdash; ' + names + ' &mdash; each naming only one supplier, which is a framework with only one supplier on it rather than a field, so the panel does not render.'));
    }

    var body = rule('Every company below is named on the <b>same NHS Supply Chain contract launch brief</b> as ' +
      esc(sub.name) + ', that framework&rsquo;s own page on NHS Supply Chain, captured <b>' + esc(dateUK(res.asOf)) + '</b>. ' +
      'The list is the brief&rsquo;s list in full, minus this company: it is not filtered down to the companies this Hub happens to hold records for, so a name here may have no Hub profile yet. ' +
      'Where the brief breaks the framework into lots, the lot is shown; otherwise the match is at framework level, so check the lot before you use it in a call. ' +
      'Sharing a framework is not the same as competing: a framework can carry companies selling into entirely different clinical niches, and a genuine competitor may be on no framework at all.');

    res.groups.forEach(function (grp) {
      /* The count in the prose comes from the same array rendered beneath it,
         so prose and list cannot drift apart. */
      var known = grp.others.filter(function (n) {
        return !!(ctx.byName[n] || (ctx.byKey && ctx.byKey[coKey(n)]));
      }).length;
      body += '<div style="margin:0 0 12px;border:1px solid ' + LINE + ';border-radius:10px;padding:12px 14px;background:' + SOFT + ';page-break-inside:avoid;break-inside:avoid;-webkit-print-color-adjust:exact;print-color-adjust:exact;">' +
        '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + esc(grp.name) + '</div>' +
        '<div style="font-size:12px;color:' + DIM + ';margin:4px 0 9px;line-height:1.6;">' + grp.others.length +
        ' other supplier(s) on this framework &middot; ' + grp.total + ' in total, including ' + esc(sub.name) + '.' +
        (grp.reference ? ' &middot; ref ' + esc(grp.reference) : '') +
        (grp.ends ? ' &middot; runs to ' + esc(grp.ends) : '') +
        ' &middot; <a href="' + esc(grp.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">brief &#8599;</a></div>' +
        '<div>' + grp.others.map(function (n) {
          var lots = grp.lots && grp.lots[n];
          var hub = ctx.byName[n] || (ctx.byKey && ctx.byKey[coKey(n)]);
          return chip(n + (lots && lots.length ? ' \u00b7 ' + lots.join(', ') : ''), hub ? 'gold' : '');
        }).join('') + '</div>' +
        '<div style="font-size:11px;color:' + DIM + ';margin-top:7px;">' + known + ' of these ' + grp.others.length +
        ' have a profile in this Hub (gold); the rest are named on the brief but not yet indexed here.</div>' +
        '</div>';
    });

    if (res.thin && res.thin.length) {
      body += gap('Held back: ' + res.thin.map(function (n) { return esc(n); }).join(', ') +
        ' &mdash; each naming only one supplier, which is below the evidence floor for this panel.');
    }
    return sec(TITLE, body);
  }

  /* Same speciality, no shared framework. A SEPARATE list — never merged into
     the panel above, because "sells into the same clinical area" and "is on the
     same piece of paper" are different claims and a reader must be able to tell
     which one they are looking at. */
  function panelSameSpeciality(sub, ctx, coRes) {
    var TITLE = 'Same speciality, no shared framework';

    /* Everyone already named above is excluded, so a company appears in one
       list or the other, never both. */
    var already = {};
    already[sub.name] = 1;
    if (coRes.ok) {
      coRes.groups.forEach(function (g) { g.others.forEach(function (n) { already[n] = 1; }); });
    }

    var subIds = ctx.spec.ids(sub);
    var usingCanon = ctx.spec.canonical;
    if (usingCanon && !subIds.length) {
      return sec(TITLE, gap('No speciality for ' + esc(sub.name) + ' could be reconciled against the canonical speciality map, so this list cannot be built. That is a lookup gap — treat it as "not looked up", never as "nobody else sells this".'));
    }
    if (!usingCanon && !((sub.specialities || []).length)) {
      return sec(TITLE, gap('No speciality is recorded for ' + esc(sub.name) + ', so there is nothing to match on.'));
    }

    var rows = [];
    ctx.all.forEach(function (o) {
      if (already[o.name]) return;
      var shared = usingCanon ? ctx.spec.shared(subIds, o) : rawShared(sub, o);
      if (!shared.length) return;
      rows.push({
        name: o.name,
        labels: shared.map(function (id) { return usingCanon ? ctx.spec.label(id) : id; }),
        fwCount: fwList(o).length
      });
    });
    rows.sort(function (a, b) { return cmpName(a.name, b.name); });

    if (!rows.length) {
      return sec(TITLE, gap('Nothing to show. Every indexed supplier sharing a speciality with ' + esc(sub.name) +
        ' also shares a framework with them and is already named above — or no other indexed supplier covers these specialities at all. Coverage is the tracked-supplier set, so this is a statement about what is indexed, not about the market.'));
    }

    var shown = rows.slice(0, MAX_SPEC_ROWS);
    var body = rule('Companies below share at least one speciality with ' + esc(sub.name) +
      ' and are on <b>none</b> of the frameworks listed above. ' +
      (usingCanon
        ? 'Specialities are reconciled through the canonical speciality map (' + ctx.spec.count + ' canonical specialities), because the free-text speciality strings across supplier records were never one vocabulary — matching them literally returns an empty list that reads as "no one else", when what actually happened is that the lookup missed.'
        : 'The canonical speciality map could not be loaded, so this fell back to matching speciality strings exactly. That under-reports: read this list as a floor, not a field.') +
      ' A shared speciality is not a shared market — it means both sell somewhere inside the same clinical area.');

    body += '<div style="font-size:12px;color:' + DIM + ';margin:0 0 8px;">' +
      rows.length + ' indexed supplier(s) match. ' +
      (rows.length > shown.length ? ('The ' + shown.length + ' listed below are the first ' + shown.length + ' alphabetically.') : ('All ' + shown.length + ' are listed below.')) +
      '</div>';

    body += shown.map(function (r) {
      return '<div style="padding:8px 0;border-bottom:1px solid #f0ece3;font-size:13px;line-height:1.5;">' +
        '<b style="color:' + INK + ';">' + esc(r.name) + '</b>' +
        '<span style="color:' + DIM + ';"> · ' + (r.fwCount ? r.fwCount + ' framework(s) indexed, none shared with ' + esc(sub.name) : 'no framework indexed') + '</span>' +
        '<br>' + r.labels.map(function (l) { return chip(l, 'gold'); }).join('') +
        '</div>';
    }).join('');

    return sec(TITLE, body);
  }

  /* =====================================================================
     STAGE 3 — Companies House facts, READ FROM SOURCE.
     data/company-financials.json is a manual interim (public register read
     by hand, 06/08/2026) until COMPANIES_HOUSE_KEY exists; its `coverage`
     field says exactly which companies it holds. Everything rendered here is
     a register fact with its source link. Nothing is computed.
     ===================================================================== */
  function finRecFor(s, fin) {
    var C = (fin && fin.companies) || null;
    if (!C) return null;
    if (C[s.name]) return C[s.name];
    var al = s.aliases || [];
    for (var k in C) { if (al.indexOf(k) !== -1) return C[k]; }
    return null;
  }
  function isProbable(rec) {
    return String((rec && rec.matchConfidence) || '').toLowerCase() === 'probable';
  }

  function fact(label, value) {
    return '<tr><td style="padding:4px 10px 4px 0;font-size:12px;color:' + DIM + ';white-space:nowrap;vertical-align:top;">' + label + '</td>' +
      '<td style="padding:4px 0;font-size:13px;color:' + INK + ';line-height:1.5;">' + value + '</td></tr>';
  }

  function panelCompanyFacts(s, ctx) {
    var TITLE = 'Company facts · Companies House';
    var fin = ctx.fin;
    if (!fin) {
      return sec(TITLE, gap('Companies House facts are not loaded — the financials feed was unreachable. Nothing is missing from the register; the page could not read it.'));
    }
    var rec = finRecFor(s, fin);
    if (!rec) {
      return sec(TITLE, gap('Not yet fetched for this company. The current file is a manual interim covering ' +
        esc(fin.coverage || 'a small set of companies') +
        ' The full register fetch runs when the Companies House API key arrives — absence here is a coverage gap, not a company without filings.'));
    }

    var probable = isProbable(rec);
    var rows = '';
    if (rec.registeredName) rows += fact('Registered name', '<b>' + esc(rec.registeredName) + '</b>' + (rec.companyNumber ? ' · ' + esc(rec.companyNumber) : ''));
    if (rec.status) rows += fact('Status', esc(rec.status));
    if (rec.incorporated) rows += fact('Incorporated', esc(dateUK(rec.incorporated)));
    if (rec.registeredOffice) rows += fact('Registered office', esc(rec.registeredOffice));
    if (rec.sic && rec.sic.length) rows += fact('SIC', rec.sic.map(esc).join(', '));
    if (rec.accountsFilingVerbatim) rows += fact('Latest accounts', esc(rec.accountsFilingVerbatim));

    /* Turnover has three honest states and they must not blur:
       a figure (with its made-up-to date), disclosed-but-not-extracted, or
       not disclosed at all (legally permitted below the small thresholds). */
    if (!probable) {
      if (rec.turnoverGBP != null) {
        rows += fact('Turnover', '£' + Number(rec.turnoverGBP).toLocaleString('en-GB') +
          ' <span style="color:' + DIM + ';">· accounts made up to ' + esc(dateUK(rec.accountsMadeUpTo || '')) + '</span>');
      } else if (rec.turnoverNote) {
        rows += fact('Turnover', '<span style="color:' + DIM + ';">' + esc(rec.turnoverNote) + '</span>');
      } else {
        rows += fact('Turnover', '<span style="color:' + DIM + ';">not disclosed in the filed accounts (legally permitted)</span>');
      }

      /* Headcount is tagged far more often than turnover — small companies must
         disclose it even when they omit the profit and loss account — so it is
         frequently the only size figure this report can show at all. */
      if (rec.employees != null) {
        rows += fact('Employees', esc(String(rec.employees)) +
          (rec.employeesNote ? ' <span style="color:' + DIM + ';">· ' + esc(rec.employeesNote) + '</span>' : ''));
      } else if (rec.employeesNote) {
        rows += fact('Employees', '<span style="color:' + DIM + ';">' + esc(rec.employeesNote) + '</span>');
      }
    }

    var body = '';
    if (probable) {
      body += '<div style="margin:0 0 9px;padding:8px 11px;background:#f7ecdc;border-left:3px solid #b98a2e;border-radius:0 7px 7px 0;font-size:12px;color:#6b5518;line-height:1.55;">' +
        '<b>IDENTITY NOT CONFIRMED.</b> This is a probable match only — ' + esc(rec.matchedOn || 'matched by name search') +
        ' Register facts are shown for orientation; no figure is carried and this company is excluded from the field filing profile below.</div>';
    } else if (rec.matchedOn) {
      body += '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 8px;">Matched on: ' + esc(rec.matchedOn) + '</div>';
    }
    body += rows ? ('<table style="border-collapse:collapse;">' + rows + '</table>') : gap('The record carries no register facts.');
    if (rec.sourceUrl) {
      body += srcLine('<a href="' + esc(rec.sourceUrl) + '" target="_blank" rel="noopener">Companies House record ↗</a>' +
        ' &middot; ' + asOf('read ' + esc(dateUK(fin.dataAsOf || ''))));
    }
    return sec(TITLE, body);
  }

  /* Officers — statutory register facts, dated events only. The file's own
     note is printed with the list: nobody is ever said to have replaced
     anybody, because succession is not a register fact and asserting it is
     the 24/07/2026 error with different names in it. */
  function panelPeople(s, ctx) {
    var TITLE = 'Notable people · statutory register';
    var rec = ctx.fin ? finRecFor(s, ctx.fin) : null;
    var off = rec && rec.officers;
    if (!off) {
      return sec(TITLE, gap('Officer data has not been fetched for this company yet. It comes from the Companies House officers register (public), company by company — absence here is a coverage gap, not a company without directors.'));
    }
    var body = off.note ? '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 8px;">' + esc(off.note) + '</div>' : '';
    if (off.current && off.current.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:4px 0 4px;">Current officers</div>' +
        off.current.map(function (o) {
          return '<div style="padding:5px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b style="color:' + INK + ';">' + esc(o.name) + '</b>' +
            ' <span style="color:' + DIM + ';">· ' + esc(o.role) + ' · appointed ' + esc(o.appointed) + '</span></div>';
        }).join('');
    }
    if (off.recentChanges && off.recentChanges.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">Recent changes</div>' +
        off.recentChanges.map(function (o) {
          var col = o.event === 'appointed' ? GREEN : '#8a4a58';
          return '<div style="padding:5px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b style="color:' + col + ';">' + esc(o.event) + '</b>' +
            ' <b style="color:' + INK + ';">' + esc(o.name) + '</b>' +
            ' <span style="color:' + DIM + ';">· ' + esc(o.role) + ' · ' + esc(o.date) + '</span></div>';
        }).join('');
    }
    if (off.sourceUrl) {
      body += srcLine('<a href="' + esc(off.sourceUrl) + '" target="_blank" rel="noopener">Officers register ↗</a>' +
        ' &middot; ' + asOf('read ' + esc(dateUK(off.readOn || ''))));
    }
    return sec(TITLE, body || gap('The officers record is empty.'));
  }

  /* =====================================================================
     STAGE 4 — FIELD FILING PROFILE. DERIVED, and the most restrained panel
     on the page. It answers "how big are the players on this lot" with the
     only two things we can actually source: the count on the lot, and each
     CONFIRMED supplier's statutory accounts filing. It never prints a
     percentage and never invents a rank.
     ===================================================================== */
  function panelFieldProfile(sub, ctx, coRes) {
    var TITLE = 'Field filing profile';
    if (!ctx.fin) {
      return sec(TITLE, gap('Not built for this view — the company financials feed was unreachable, and a size comparison without the filings is a guess.'));
    }
    if (!coRes.ok) {
      return sec(TITLE, gap('Withheld, because the framework co-listing above is withheld — this panel profiles that field, and there is no field to profile.'));
    }

    var body = rule('For each framework above: every supplier whose identity is <b>confirmed</b> against a Companies House record (matchConfidence === "confirmed") is listed with the exact wording of its most recent accounts filing on the public register. ' +
      'Suppliers whose identity is only probable, or who file outside the UK, are named as unresolved and feed nothing. ' +
      'The panel refuses any framework where fewer than half the suppliers resolve — a size comparison built on a third of the lot is not a size comparison. ' +
      'No percentage appears here because nobody holds market-share data: what a filing tells you is which statutory regime the company files under (thresholds quoted below), not its share of anything. ' +
      'Register read ' + esc(dateUK(ctx.fin.dataAsOf || 'date not recorded')) + '; framework data captured ' + esc(dateUK(ctx.asOf)) + '.');

    var rendered = 0;
    coRes.groups.forEach(function (grp) {
      var everyone = [sub.name].concat(grp.others);
      var resolved = [], unresolved = [];
      everyone.forEach(function (n) {
        var rec = ctx.byName[n] || (ctx.byKey ? ctx.byKey[coKey(n)] : null);
        var r = rec ? finRecFor(rec, ctx.fin) : null;
        if (r && !isProbable(r) && String(r.accountsCategory || '').trim()) {
          resolved.push({ name: n, rec: r });
        } else {
          unresolved.push({ name: n, rec: r });
        }
      });

      /* THE HALF-THE-FIELD FLOOR. resolved * 2 < total refuses the panel. */
      if (resolved.length * 2 < everyone.length) {
        body += '<div style="margin:0 0 12px;border:1px dashed #ded6c4;border-radius:10px;padding:12px 14px;background:#faf8f3;page-break-inside:avoid;break-inside:avoid;">' +
          '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + esc(grp.name) + '</div>' +
          gap('Refused: of the ' + everyone.length + ' suppliers on this framework, only ' + resolved.length +
            ' resolve to a confirmed Companies House record with an accounts filing. That is below half the field, and a size profile of under half a field misleads more than it informs. Unresolved: ' +
            unresolved.map(function (u) { return esc(u.name); }).join(', ') + '. Confirming identities is what fixes this; lowering the bar is not.') +
          '</div>';
        return;
      }
      rendered += 1;

      var rows = resolved.map(function (r) {
        var me = r.name === sub.name;
        return '<tr>' +
          '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12.5px;color:' + INK + ';' + (me ? 'font-weight:700;' : '') + '">' + esc(r.name) + (me ? ' ◂' : '') + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12.5px;color:#37485a;">' + esc(r.rec.accountsFilingVerbatim || r.rec.accountsCategory) + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid #f0ece3;font-size:12px;color:' + DIM + ';white-space:nowrap;">' + esc(r.rec.incorporated ? ('inc. ' + r.rec.incorporated.slice(0, 4)) : '') + '</td>' +
          '</tr>';
      }).join('');

      body += '<div style="margin:0 0 12px;border:1px solid ' + LINE + ';border-radius:10px;padding:12px 14px;background:' + SOFT + ';page-break-inside:avoid;break-inside:avoid;-webkit-print-color-adjust:exact;print-color-adjust:exact;">' +
        '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + esc(grp.name) + '</div>' +
        '<div style="font-size:12px;color:' + DIM + ';margin:4px 0 9px;line-height:1.6;">' + everyone.length + ' supplier(s) on this framework · ' +
        resolved.length + ' resolved to a confirmed filing · ' + unresolved.length + ' unresolved.</div>' +
        '<div class="mcr-scroll"><table style="border-collapse:collapse;width:100%;min-width:420px;">' +
        '<tr><th style="text-align:left;padding:5px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">SUPPLIER</th>' +
        '<th style="text-align:left;padding:5px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">MOST RECENT ACCOUNTS FILING</th>' +
        '<th style="text-align:left;padding:5px 8px;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';"></th></tr>' +
        rows + '</table></div>';

      if (unresolved.length) {
        body += '<div style="font-size:12px;color:' + DIM + ';margin-top:7px;">Unresolved, feeding nothing: ' +
          unresolved.map(function (u) {
            var why = u.rec ? (isProbable(u.rec) ? 'identity not confirmed' : 'no accounts filing recorded') : 'no Companies House record fetched';
            return '<b>' + esc(u.name) + '</b> (' + why + ')';
          }).join(' · ') + '.</div>';
      }
      body += '</div>';
    });

    /* What "full accounts" does and does not mean, with the statutory
       thresholds quoted from the file that carries their source. */
    var th = ctx.fin.thresholds;
    if (th && th.bands) {
      var t = [];
      if (th.bands.small && th.bands.small.verbatim) t.push(esc(th.bands.small.verbatim));
      if (th.bands.medium && th.bands.medium.verbatim) t.push('Medium-sized (Companies Act 2006 s465(3)): ' + esc(th.bands.medium.verbatim));
      body += srcLine('<b style="color:#4a5766;">Reading the filings.</b> ' +
        'A company entitled to the small-companies or micro-entity regime may file reduced accounts; a FULL filing is the one made when those exemptions are not used. It does not by itself state the company’s size — the disclosed turnover inside the filed document does, and extracting those figures is the next step. Thresholds in force (' + esc(th.appliesTo || '') + '): ' +
        t.join(' — '));
    }

    if (!rendered) {
      body += gap('No framework on this report cleared the half-the-field floor, so no profile is shown. The refusals above name what is missing.');
    }
    return sec(TITLE, body);
  }

  /* =====================================================================
     PRESENTATION LAYER — redesigned 06/08/2026 to Lou's spec, folding in
     the Employer Intelligence deep dives (WP drafts 2423/2425) so those
     standalone pages can be retired. Section order is hers: company
     information first (with the growth chart near the top), then
     specialities/divisions as cards, then competitors by speciality, then
     news and people, then working-there, and the full catalogue + own-site
     listings LAST. Brand-guide defaults: navy #0B1C33 gradient where a
     company has no recorded brand colour; gold carries labels and rules,
     never body copy.
     ===================================================================== */

  function deepFor(s) { return s.deepDive || null; }

  /* Brand marks, keyed by company name, filled in by boot() from
     data/company-logos.json. Empty until then, and empty for good if that file
     does not load — every company then draws the monogram. */
  var LOGO = {};

  /* ---------------------------------------------------------------------
     CONTRAST, IN THE RENDERER AS WELL AS THE WRITER.

     scripts/refresh_logos.py already proves every colour it publishes against
     the ground it will be painted on, and verify.py re-proves it before a push.
     This is the third check, and it is here because the OTHER source of brand
     colours — the 95 `brand` records in supplier-seed.json, sampled from 128px
     favicons by scripts/refresh_brand_colours.py — predates any contrast rule
     at all. Rather than rewrite a human-curated file from a script, the rule is
     applied where the colour is actually used: a shade that cannot clear its
     floor never reaches the page, whichever file it came from.

     WCAG 2.1 relative luminance, verbatim.
     --------------------------------------------------------------------- */
  var NAVY_RGB = [11, 28, 51],        /* #0B1C33, the masthead ground */
      IVORY_RGB = [253, 252, 249];    /* #fdfcf9, the card ground */
  var MIN_ON_NAVY = 3.0, MIN_ON_IVORY = 3.0;   /* WCAG 2.1 1.4.11, non-text */

  function rgbOf(hex) {
    var h = String(hex || '').replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    if (!/^[0-9a-fA-F]{6}$/.test(h)) return null;
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }
  function lum(rgb) {
    var c = rgb.map(function (v) {
      v = v / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  function ratio(a, b) {
    var x = lum(a), y = lum(b), hi = Math.max(x, y), lo = Math.min(x, y);
    return (hi + 0.05) / (lo + 0.05);
  }
  /* Returns the hex if it clears `floor` against `ground`, otherwise null. */
  function safe(hex, ground, floor) {
    var rgb = rgbOf(hex);
    if (!rgb) return null;
    return ratio(rgb, ground) >= floor ? hex : null;
  }
  function toHex(rgb) {
    return '#' + rgb.map(function (v) {
      return ('0' + Math.max(0, Math.min(255, Math.round(v))).toString(16)).slice(-2);
    }).join('');
  }
  /* DERIVE THE SHADE RATHER THAN GIVE UP ON THE COLOUR.

     data/company-logos.json records both shades already, because the script
     that samples a mark can compute them once and write them down. The two
     OLDER colour sources cannot: deepDive.brand is a hand-picked pair and the
     95 seed records predate the whole idea. For those, refusing a colour that
     misses its floor would drop the company back to house gold — and it did:
     GBUK's hand-picked green and Jeenie's blue are both invisible on navy, so
     both mastheads went gold while the colour sat unused in the data.

     So the same rule refresh_logos.py applies at build time is applied here at
     render time: move the colour along ONE axis, in fixed steps, until it
     clears its floor. `dir` is +1 towards white (for the navy ground) or -1
     towards black (for the ivory ground). The hue never changes, and if no
     step clears the floor the company gets the house gold — an unreadable
     accent is still never published. */
  function derive(hex, ground, floor, dir) {
    var rgb = rgbOf(hex);
    if (!rgb) return null;
    var steps = [0, 0.12, 0.24, 0.36, 0.48, 0.60, 0.72, 0.82];
    for (var i = 0; i < steps.length; i++) {
      var f = steps[i];
      var cand = rgb.map(function (v) {
        return dir > 0 ? v + (255 - v) * f : v * (1 - f);
      });
      if (ratio(cand, ground) >= floor) return toHex(cand);
    }
    return null;
  }

  /* Company colour, in order of how well we can stand behind it:
       1. a colour a human checked against the brand (deepDive.brand);
       2. a colour sampled from the company's OWN BRAND MARK, fetched from its
          own website and stored in this repo, carrying both derived shades,
          both contrast ratios and the URL and date it was read from
          (data/company-logos.json, written by scripts/refresh_logos.py);
       3. a colour sampled from a 128px favicon, carrying the URL and date
          (supplier-seed `brand`, written by scripts/refresh_brand_colours.py);
       4. no colour at all.
     2 sits above 3 because a 192px brand mark from the company's own site is a
     better source than a browser-tab glyph, and because only 2 was written
     under a contrast rule. A monochrome mark yields no sample at all and falls
     through rather than publishing "this company's colour is grey". */
  function brandOf(s) {
    var d = deepFor(s);
    if (d && d.brand && d.brand.c1 && d.brand.c2) return d.brand;
    var l = LOGO[s.name];
    if (l && l.brand && l.brand.c1 && l.brand.c2) return l.brand;
    if (s.brand && s.brand.c1 && s.brand.c2) return s.brand;
    return null;
  }

  /* THE ACCENT IS TWO VALUES, NOT ONE, BECAUSE THE REPORT HAS TWO GROUNDS.

     It used to be one, and that is why it could only ever be a 5px edge. A
     single colour cannot be both visible on the navy masthead and visible on
     the ivory card ground: medtech is full of dark blues, which vanish on navy,
     and of yellows and oranges, which vanish on ivory. Testing one accent
     against one ground would have thrown away 22 of the 95 colours already held
     (Stryker's yellow, Smith+Nephew's orange) or 48 of them (every dark blue),
     depending which ground you picked.

     So the sampled colour c1 is never painted. Two shades of it are:

       --mcr-accent      on the NAVY masthead. c1 lightened until it clears 3:1.
       --mcr-accent-ink  on the IVORY card ground. c1 darkened until it clears
                         3:1 there and 4.5:1 under white text.

     refresh_logos.py computes and records both. A seed colour predating that
     rule carries neither, so the shade falls back to c1 (for navy) or c2 (for
     ivory) and is CHECKED here — if it cannot clear its floor, the company gets
     the house gold on that ground and keeps its own colour on the other.

     HOUSE DEFAULT, AND WHY IT IS GOLD. Antique Gold #C49B5C on navy (6.67:1)
     and Deep Gold #A8842C on light (3.41:1) are the brand guide's own pairing.
     A company with no colour gets a report that reads as the intended house
     design, not as a report missing its branding. */
  var HOUSE_ON_NAVY = '#C49B5C', HOUSE_ON_IVORY = '#A8842C';

  function accentOnNavy(s) {
    var b = brandOf(s);
    if (!b) return HOUSE_ON_NAVY;
    /* A recorded shade is used as recorded, and still CHECKED — a colour is
       never trusted just because a file states it. Only where none was
       recorded is one derived from c1. */
    return safe(b.accentOnNavy, NAVY_RGB, MIN_ON_NAVY) ||
           derive(b.c1, NAVY_RGB, MIN_ON_NAVY, +1) || HOUSE_ON_NAVY;
  }
  function accentOnIvory(s) {
    var b = brandOf(s);
    if (!b) return HOUSE_ON_IVORY;
    return safe(b.accentOnIvory, IVORY_RGB, MIN_ON_IVORY) ||
           derive(b.c2 || b.c1, IVORY_RGB, MIN_ON_IVORY, -1) || HOUSE_ON_IVORY;
  }
  /* Both custom properties in one string, for the report root. */
  function accentVars(s) {
    return '--mcr-accent:' + accentOnNavy(s) + ';--mcr-accent-ink:' + accentOnIvory(s) + ';';
  }

  /* The identity tile.

     WHERE THE MARK COMES FROM. The third-party logo service this function used
     to call, live, while a member watched, no longer resolves. The call could
     not succeed for any company, every report fell through to the monogram, and
     nobody found out until somebody read this file on 18/08/2026.

     THE HOST NAMES ARE DELIBERATELY NOT WRITTEN ANYWHERE IN THIS FILE, not even
     in a comment. verify.py scans the whole source for them as bare strings,
     which is a blunt check that cannot be argued with — and a check that has to
     tell a comment from a call is a check with a hole in it. So marks are
     now fetched ONCE at build time from each company's own website by
     scripts/refresh_logos.py, stored in this repository under assets/logos/,
     and served from the same host as every other file this page reads. NO
     THIRD-PARTY LOGO SERVICE IS CALLED FROM THIS FILE, and none may be added.

     THE MONOGRAM IS NOT AN APOLOGY. Most companies in this index have no
     findable mark, and that is the normal case rather than the failure case —
     so the monogram is drawn as a finished thing: a navy plate with the
     company's initials in Light Gold, which is the house lockup. A member
     looking at a monogram report should not be able to tell that anything is
     missing, because nothing is. */
  function logoImg(s, px) {
    var _w = String(s.name || '').replace(/^the\s+/i, '').split(/[\s\-—,\.]+/).filter(Boolean);
    var inits = esc((/^[A-Za-z0-9]{2,4}$/.test(_w[0] || '') ? _w[0] : _w.slice(0, 2).map(function (w) { return w[0]; }).join('')).toUpperCase());
    var mono = 'width:100%;height:100%;border-radius:inherit;background:linear-gradient(150deg,#14304F,#0B1C33);' +
      'align-items:center;justify-content:center;font-weight:800;letter-spacing:.5px;color:#E0BE8E;' +
      'font-size:' + Math.max(12, Math.round(px / (inits.length > 2 ? 4.2 : 3.1))) + 'px;' +
      '-webkit-print-color-adjust:exact;print-color-adjust:exact;';
    var fb = '<div style="display:none;' + mono + '">' + inits + '</div>';
    var swap = "this.style.display='none';this.nextElementSibling.style.display='flex';";

    /* 1. The self-hosted mark. Served from this repo, so it cannot rot without
          a commit, and it was already proved to clear the size floor when it
          was fetched. `onerror` still falls to the monogram: a file deleted
          from the repo must degrade to the house lockup, never to a broken
          image icon on a paid page. */
    var l = LOGO[s.name];
    if (l && l.file) {
      return '<img src="' + esc(BASE + l.file) + '" alt="" loading="lazy" ' +
        'style="max-width:' + (px - 14) + 'px;max-height:' + (px - 14) + 'px;object-fit:contain;" ' +
        'onerror="' + swap + '">' + fb;
    }

    /* 2. The legacy `image` field. 13 of its 15 values point at a favicon
          SERVICE — a 16px browser-tab glyph, and where the service holds
          nothing it serves its own grey placeholder arrow, which reads as a
          broken report. Those are not migrated and are not drawn: a favicon
          endpoint is treated as no logo at all. */
    var favicon = /(?:^|\/\/)(?:icons?\.|[^\/]*\/s2\/favicons)|favicons?\b/i.test(String(s.image || ''));
    if (!s.image || favicon) {
      return '<div style="display:flex;' + mono + '">' + inits + '</div>';
    }
    return '<img src="' + esc(s.image) + '" alt="" referrerpolicy="no-referrer" loading="lazy" ' +
      'style="max-width:' + (px - 14) + 'px;max-height:' + (px - 14) + 'px;object-fit:contain;" ' +
      'onerror="' + swap + '" onload="if(this.naturalWidth&lt;24){' + swap + '}">' + fb;
  }

  /* The report header. It is a masthead, not a banner: the Hub's own name and
     the document type first, then the company, then the dates the report was
     built from. A member printing this and taking it into an interview needs
     to be able to see, at a glance, what it is and how current it is.

     The ground is ALWAYS the house navy gradient. The company's own colour,
     where one was sampled, is the 5px edge along the top and nothing else —
     so the 86% of companies with no sampled colour get the intended design
     rather than something that reads as a missing asset. */
  function masthead(s, ctx, stamp) {
    var d = deepFor(s);
    /* Links come from two places: the deep-dive record (10 suppliers) and the
       supplier record itself (380 suppliers, 505 links). Only the first was
       ever rendered, so a company's own website and Companies House entry sat
       in the data and never reached the page. Merge both, deep dive first,
       de-duplicated on the URL. */
    var links = [];
    var seenLink = {};
    [].concat((d && d.links) || [], s.links || []).forEach(function (l) {
      if (!l || !l.url || !l.label) return;
      var key = String(l.url).replace(/\/+$/, '').toLowerCase();
      if (seenLink[key]) return;
      seenLink[key] = 1;
      links.push(l);
    });
    var meta = [];
    if (stamp) meta.push('Prepared <b>' + esc(stamp) + '</b>');
    if (ctx && ctx.asOf) meta.push('supplier index as of <b>' + esc(dateUK(ctx.asOf)) + '</b>');
    if (ctx && ctx.fwDoc && ctx.fwDoc.dataAsOf) meta.push('framework briefs captured <b>' + esc(dateUK(ctx.fwDoc.dataAsOf)) + '</b>');
    if (ctx && ctx.fin && ctx.fin.dataAsOf) meta.push('Companies House read <b>' + esc(dateUK(ctx.fin.dataAsOf)) + '</b>');

    return '<header class="mcr-mast">' +
      '<div class="mcr-mast-row">' +
        '<span class="mcr-logo">' + logoImg(s, 74) + '</span>' +
        '<div style="min-width:210px;">' +
          '<div class="mcr-kicker">Medical Sales Intelligence Hub &middot; Company intelligence report</div>' +
          '<h2 class="mcr-h1">' + esc(s.name) + '</h2>' +
          (d && d.tagline ? '<div class="mcr-tagline">' + esc(d.tagline) + '</div>' : '') +
        '</div>' +
        (links.length ? '<span class="mcr-links">' + links.map(function (l) {
          return '<a href="' + esc(l.url) + '" target="_blank" rel="noopener">' + esc(l.label) + '</a>';
        }).join('') + '</span>' : '') +
      '</div>' +
      (meta.length ? '<div class="mcr-mast-meta">' + meta.join(' &middot; ') +
        '<br>Every derived panel prints the rule it was computed under. Every empty panel says what is missing.</div>' : '') +
      '</header>';
  }

  /* A part divider. The report runs long, and an unbroken run of cards gives a
     reader no way to find their place — so the panels are grouped, and each
     group says in one line what it is answering. Structure only: no group
     asserts anything the panels beneath it do not already carry. */
  function part(n, title, subtitle) {
    return '<div class="mcr-part">' +
      '<div class="mcr-part-n">Part ' + esc(n) + '</div>' +
      '<div class="mcr-part-t">' + title + '</div>' +
      (subtitle ? '<div class="mcr-part-s">' + subtitle + '</div>' : '') +
      '</div>';
  }

  function ledeBox(s) {
    var d = deepFor(s);
    if (!(d && d.lede)) return '';
    return '<div class="mcr-card" style="font-size:15px;line-height:1.72;color:' + INK +
      ';border-left:4px solid var(--mcr-accent-ink);">' + esc(d.lede) + '</div>';
  }

  function statGrid(s) {
    var d = deepFor(s);
    if (!(d && d.stats && d.stats.length)) return '';
    return '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:12px;margin:2px 0 0;">' +
      d.stats.map(function (st) {
        return '<div style="background:' + SOFT + ';border:1px solid ' + LINE + ';border-top:3px solid var(--mcr-accent-ink);border-radius:10px;padding:13px 14px;-webkit-print-color-adjust:exact;print-color-adjust:exact;">' +
          '<div style="font-size:21px;font-weight:800;color:' + INK + ';line-height:1.15;letter-spacing:-.3px;">' + esc(st.v) + '</div>' +
          '<div style="font-size:9.5px;text-transform:uppercase;letter-spacing:1.3px;color:' + DIM + ';font-weight:700;margin-top:5px;">' + esc(st.l) + '</div>' +
          (st.n ? '<div style="font-size:10.5px;color:' + DIM + ';margin-top:4px;line-height:1.5;">' + esc(st.n) + '</div>' : '') +
          '</div>';
      }).join('') + '</div>';
  }

  /* The growth chart. Bars are drawn ONLY for figures actually read from a
     named filing; every other year in the frame renders as an empty slot
     labelled as unread. An empty slot is "not yet extracted", never zero —
     drawing a zero-height bar for an unread year would publish a figure
     nobody sourced, which is the whole class of error this repo gates. */
  /* Build a growth series from the FILED ACCOUNTS where one was extracted.
     This is the sourced route: every point came from a tagged (iXBRL) filing,
     and carries the period, the tag and the document it was read from. It is
     preferred over a hand-written deep-dive series because it can be traced. */
  function filedSeries(s, ctx) {
    var rec = ctx.fin ? finRecFor(s, ctx.fin) : null;
    var pts = rec && rec.turnoverSeries;
    if (!(pts && pts.length)) return null;
    var years = pts.map(function (p) { return parseInt(String(p.periodEnd).slice(0, 4), 10); });
    return {
      label: 'Turnover, from the filed accounts',
      currency: '£', unit: 'm',
      axis: { from: Math.min.apply(null, years), to: Math.max.apply(null, years) },
      axisNote: 'Each bar is the turnover tagged in that year\u2019s filed accounts at Companies House. A year with no bar is a year whose accounts carry no tagged turnover, not a year of no trading.',
      points: pts.map(function (p) {
        return { y: 'FY' + String(p.periodEnd).slice(0, 4),
                 v: Math.round(p.value / 1e6 * 10) / 10,
                 src: 'filed ' + (p.filedOn || '') };
      }),
      source: 'the iXBRL (tagged) accounts filed at Companies House' +
              (ctx.fin && ctx.fin.figuresAsOf ? ', read ' + ctx.fin.figuresAsOf : '')
    };
  }

  function growthChart(s, ctx) {
    var d = deepFor(s);
    var g = d && d.growth;
    var filed = filedSeries(s, ctx);
    if (filed) {
      /* A sourced series wins over a curated one; the curated prose is kept
         because it explains what the numbers mean. */
      g = { series: filed, prose: (g && g.prose) || null };
    }
    if (!(g && g.series && g.series.points && g.series.points.length)) {
      var frec = ctx.fin ? finRecFor(s, ctx.fin) : null;
      var why = frec && frec.turnoverNote;
      return sec('Growth', gap(why
        ? ('No turnover series can be shown for this company: ' + esc(why) +
           ' Turnover exists only inside the filed accounts, so where the accounts do not disclose it in a readable form there is nothing to chart. That is a fact about the filing, not about the company\u2019s size.')
        : 'No growth series has been extracted for this company yet. Turnover lives in the filed accounts (Companies House for UK companies, investor filings for listed groups); reading those documents is the extraction step, and it has not run here — a coverage gap, not a company that is not growing.'));
    }
    var se = g.series;
    var byYear = {};
    se.points.forEach(function (p) { byYear[p.y] = p; });
    var years = [];
    for (var y = se.axis.from; y <= se.axis.to; y++) years.push('FY' + y);
    var max = 0;
    se.points.forEach(function (p) { if (p.v > max) max = p.v; });
    /* The column is three stacked things: the value label, the bar, and the year.
       The bar must therefore be sized against the height left AFTER the two
       labels, not against the whole row — sizing it against the row pushed the
       value label off the top of the tallest bar, which is exactly what it was
       doing before 07/08/2026. */
    var H = 150;                 // row height
    var LABELS = 46;             // value label + year label + the gaps between
    var BAR_MAX = H - LABELS;
    var cols = years.map(function (yr) {
      var p = byYear[yr];
      if (p) {
        var h = Math.max(8, Math.round(p.v / max * BAR_MAX));
        return '<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;min-width:44px;">' +
          '<div style="font-size:10.5px;font-weight:800;color:' + INK + ';white-space:nowrap;line-height:1.2;flex:0 0 auto;">' + esc(se.currency) + p.v + esc(se.unit) + '</div>' +
          '<div style="width:70%;height:' + h + 'px;background:linear-gradient(180deg,#D4AF7A,#B8935A);border-radius:4px 4px 0 0;-webkit-print-color-adjust:exact;print-color-adjust:exact;"></div>' +
          '<div style="font-size:9.5px;font-weight:700;color:' + DIM + ';">' + esc(yr) + '</div></div>';
      }
      return '<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;min-width:44px;">' +
        '<div style="width:70%;height:14px;border:1px dashed ' + LINE + ';border-bottom:0;border-radius:4px 4px 0 0;"></div>' +
        '<div style="font-size:9.5px;color:#b8b0a0;">' + esc(yr) + '</div></div>';
    }).join('');

    var body = '<div style="font-size:12px;font-weight:700;color:' + INK + ';margin-bottom:12px;">' + esc(se.label) + ' <span style="color:' + DIM + ';font-weight:600;">(' + esc(se.currency) + esc(se.unit) + ')</span></div>' +
      '<div class="mcr-scroll" style="display:flex;align-items:flex-end;gap:6px;height:' + H + 'px;border-bottom:2px solid ' + LINE + ';overflow-y:visible;padding-top:4px;">' + cols + '</div>' +
      srcLine('Solid bars are figures read from ' + esc(se.source) + '. Dashed slots are years not yet extracted — an empty slot is unread, never zero. ' + esc(se.axisNote || '') + (se.pending ? ' ' + esc(se.pending) : ''));

    if (g.prose && g.prose.length) {
      body += '<div style="font-size:13.5px;line-height:1.7;color:#37485a;margin-top:12px;">' +
        g.prose.map(function (p) { return '<p style="margin:0 0 10px;">' + esc(p) + '</p>'; }).join('') + '</div>';
    }
    return sec('Growth', body);
  }

  function ownershipBlock(s) {
    var d = deepFor(s);
    if (!(d && d.ownership && d.ownership.length)) return '';
    return sec('Structure &amp; ownership', '<div style="font-size:13.5px;line-height:1.72;color:#37485a;">' +
      d.ownership.map(function (p) { return '<p style="margin:0 0 10px;">' + esc(p) + '</p>'; }).join('') + '</div>');
  }

  /* Divisions / specialities as cards — Lou's spec: they must visually
     stand out, one card each, not a chip row. Uses the company's own
     division tree where a full crawl exists; otherwise one card per
     recorded speciality. */
  function divisionCards(s, ctx) {
    var deep = deepRangeFor(s, ctx.prodFile);
    /* Card headers used to be a solid slab of the company's colour, repeated
       down the grid. On the 86% with no sampled colour that was a wall of
       navy; on the rest it swamped the page. The colour is now a 3px top edge
       and the type sits on white, which reads the same for both. */
    var TOP = 'border-top:3px solid var(--mcr-accent-ink);';
    var CARD = 'background:#fff;border:1px solid ' + LINE + ';' + TOP +
      'border-radius:11px;padding:13px 15px;box-shadow:0 1px 2px rgba(29,39,51,.05);-webkit-print-color-adjust:exact;print-color-adjust:exact;';
    var GRID = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(212px,1fr));gap:12px;';
    var cards = '';
    if (deep && deep.divisions && deep.divisions.length) {
      cards = deep.divisions.map(function (dv) {
        return '<div style="' + CARD + '">' +
          '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + esc(dv.name) + '</div>' +
          '<div style="margin-top:7px;font-size:12px;color:' + DIM + ';line-height:1.6;">' + dv.products + ' product(s) in the verified range' +
          (dv.specialities && dv.specialities.length ? '<br>Specialities: ' + dv.specialities.map(esc).join(', ') : '') +
          '</div></div>';
      }).join('');
      return sec('Divisions &amp; specialities', '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 11px;line-height:1.6;">The company’s own division structure, from the full crawl of its site; product counts come from the verified range at the bottom of this report.</div>' +
        '<div style="' + GRID + '">' + cards + '</div>');
    }
    if (s.specialities && s.specialities.length) {
      cards = s.specialities.map(function (sp) {
        return '<div style="' + CARD + '">' +
          '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + esc(sp) + '</div>' +
          '<div style="margin-top:7px;font-size:12px;color:' + DIM + ';line-height:1.6;">Recorded speciality · division-level product counts arrive with the full site crawl.</div>' +
          '</div>';
      }).join('');
      return sec('Divisions &amp; specialities', '<div style="' + GRID + '">' + cards + '</div>');
    }
    return sec('Divisions &amp; specialities', gap('No speciality recorded for this company yet.'));
  }

  function deepPeopleCards(s) {
    var d = deepFor(s);
    if (!(d && d.people && d.people.length)) return '';
    var h = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;">' +
      d.people.map(function (p) {
        return '<div style="background:#fff;border:1px solid ' + LINE + ';border-radius:10px;padding:15px 16px;' + (p.out ? 'opacity:.72;' : '') + '">' +
          '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';">' + esc(p.name) + '</div>' +
          '<div style="font-size:11px;color:' + (p.out ? DIM : G) + ';font-weight:700;margin-top:2px;">' + esc(p.role) + '</div>' +
          (p.note ? '<div style="font-size:12px;color:' + DIM + ';margin-top:6px;line-height:1.55;">' + esc(p.note) + '</div>' : '') +
          '</div>';
      }).join('') + '</div>';
    if (d.peopleNote) {
      h += '<div style="font-size:11.5px;color:' + DIM + ';background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:8px;padding:9px 13px;margin-top:10px;">' + esc(d.peopleNote) + '</div>';
    }
    return h;
  }

  function deepPress(s) {
    var d = deepFor(s);
    if (!(d && d.press && d.press.length)) return '';
    return d.press.map(function (n) {
      return '<div style="border-bottom:1px solid #f0ece3;padding:11px 0;' + (n.flagged ? 'border-left:3px solid var(--mcr-accent-ink);padding-left:12px;' : '') + '">' +
        '<div style="font-size:10px;font-weight:700;letter-spacing:1.2px;color:' + G + ';text-transform:uppercase;margin-bottom:5px;">' + esc(n.date) + '</div>' +
        '<div style="font-size:13px;line-height:1.6;color:#37485a;">' + esc(n.text) + '</div></div>';
    }).join('');
  }

  function workingThere(s) {
    var d = deepFor(s);
    if (!d) return '';
    var left = '', right = '';
    if (d.place && d.place.embed) {
      left += '<div style="border-radius:10px;overflow:hidden;border:1px solid ' + LINE + ';background:#eee;"><iframe src="' + esc(d.place.embed) + '" loading="lazy" referrerpolicy="no-referrer-when-downgrade" style="display:block;width:100%;height:210px;border:0;" title="Site location"></iframe></div>' +
        (d.place.caption ? '<div style="font-size:11px;color:' + DIM + ';margin-top:6px;line-height:1.5;">' + esc(d.place.caption) + '</div>' : '');
    }
    if (d.linkedinPeople) {
      left += '<div style="margin-top:12px;"><a href="' + esc(d.linkedinPeople) + '" target="_blank" rel="noopener" style="display:inline-block;background:#39689e;color:#fff;font-size:12px;font-weight:700;padding:9px 18px;border-radius:99px;text-decoration:none;">See who works there ↗</a></div>';
    }
    if (d.glassdoor) {
      right += '<div style="background:' + SOFT + ';border:1px solid ' + LINE + ';border-left:4px solid ' + G + ';border-radius:8px;padding:13px 15px;">' +
        '<div style="display:flex;align-items:center;gap:9px;margin-bottom:7px;"><span style="font-size:21px;font-weight:800;color:' + G + ';">' + esc(d.glassdoor.rating) + '</span><span style="font-size:11.5px;color:' + DIM + ';font-weight:600;">' + esc(d.glassdoor.scale) + '</span></div>' +
        '<div style="font-size:13px;line-height:1.6;color:' + INK + ';font-style:italic;">' + esc(d.glassdoor.summary) + '</div>' +
        '<div style="margin-top:7px;font-size:10.5px;color:' + DIM + ';">Editorial summary of public reviews, checked ' + esc(d.glassdoor.checked) + '. <a href="' + esc(d.glassdoor.url) + '" target="_blank" rel="noopener" style="color:#39689e;font-weight:600;">Read them yourself ↗</a></div></div>';
    }
    if (d.interview) {
      right += '<div style="margin-top:12px;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:12px 15px;">' +
        '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1.4px;font-weight:700;color:' + DIM + ';margin-bottom:5px;">Before you walk in</div>' +
        '<div style="font-size:13px;line-height:1.65;color:#37485a;">' + esc(d.interview) + '</div></div>';
    }
    if (d.hiring && d.hiring.length) {
      right += '<div style="margin-top:12px;font-size:13px;line-height:1.65;color:#37485a;">' +
        d.hiring.map(function (p) { return '<p style="margin:0 0 8px;">' + esc(p) + '</p>'; }).join('') + '</div>';
    }
    if (!left && !right) return '';
    return sec('Working there', '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;">' +
      '<div>' + (left || '') + '</div><div>' + (right || '') + '</div></div>');
  }

  /* ---------------------------------------------------------------------
     Report card
     --------------------------------------------------------------------- */
  /* One composer for both surfaces. The on-page card and the printed pack
     render THIS, so they cannot drift — and a panel refused here is refused
     everywhere. Section order is Lou's (06/08/2026): company information
     (with growth near the top), specialities/divisions as cards, competitors
     by speciality, news and people, working-there, and the full listings
     LAST. */
  /* ROUTE, BUYERS AND STANDING SIGNALS.
     Carried in from the Client Intelligence Profiles page (WP 1751) when that page
     was retired on 14/08/2026, so nothing it held was lost with it.

     Curated, not computed, so it prints its provenance rather than a derivation
     rule. Structural on purpose: how the volume actually reaches the NHS, who
     signs for it, and the standing signals reps act on. Framework values, renewal
     dates and live alerts are deliberately NOT restated here — they are read live
     in the Frameworks and Alerts panels, and a second hand-typed copy of a dated
     fact is the exact drift the verification standard exists to stop.

     Held for a handful of companies only, so it renders when present and is simply
     absent otherwise. It gets no empty state on purpose: an empty "what to watch"
     would read as "there is nothing to watch", which is never true. */
  function repsWatch(sub) {
    var rw = sub.repsWatch;
    if (!rw) return '';
    var buyers = rw.buyers || [], watch = rw.watch || [];
    if (!rw.route && !buyers.length && !watch.length) return '';

    var b = '';
    if (rw.route) {
      b += '<div style="font-size:13.5px;color:#37485a;line-height:1.6;">' +
        '<b style="color:' + INK + ';">Route to market.</b> ' + esc(rw.route) + '</div>';
    }
    if (buyers.length) {
      b += '<div style="margin-top:11px;"><div style="font-size:13px;color:' + INK +
        ';font-weight:700;margin-bottom:6px;">Who signs for it</div>' +
        buyers.map(function (x) { return chip(x, 'gold'); }).join('') + '</div>';
    }
    if (watch.length) {
      b += '<div style="margin-top:11px;"><div style="font-size:13px;color:' + INK +
        ';font-weight:700;margin-bottom:6px;">Standing signals reps act on</div>' +
        '<ul style="margin:0;padding-left:18px;font-size:13.5px;color:#37485a;line-height:1.65;">' +
        watch.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></div>';
    }
    if (rw.source) {
      b += '<div style="margin-top:10px;font-size:12px;color:' + DIM + ';line-height:1.55;">' +
        esc(rw.source) + '</div>';
    }
    return sec('What reps should watch', b);
  }

  /* ---------------------------------------------------------------------
     ROUTES TO MARKET — tender and contract awards (page standard §13–14),
     and the honest empty states for §15–16, which have no source at all.

     READ FROM SOURCE, NOT DERIVED. Every row is one supplier named on one
     statutory award notice, fetched by scripts/refresh_awards.py and matched
     to this company by scripts/company_match.py under an exact-only rule that
     verify.py re-derives before anything publishes. Nothing here is inferred
     from a product range, a speciality or a framework.

     THE EMPTY STATE IS THE POINT. Both feeds carry only what was published in
     the windows walked, and only where the buyer coded the notice to CPV 33.
     So an absence is a statement about THIS INDEX and is written as one. The
     page must never say a company has no awards — that is a claim about the
     company that neither feed supports, and verify.py fails the push on it.
     --------------------------------------------------------------------- */
  /* The feeds are ISO; the Hub writes dates the way its members do. */
  function uk(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ''));
    return m ? m[3] + '/' + m[2] + '/' + m[1] : '';
  }

  function awardsFor(s, ctx) {
    var doc = ctx.awards;
    if (!doc || !doc.companies) return null;
    return doc.companies[s.name] || [];
  }

  function awardRow(a) {
    var value = (typeof a.valueAmount === 'number')
      ? '<span style="color:' + GREEN + ';font-weight:700;">' +
        esc((a.valueCurrency === 'GBP' ? '£' : (a.valueCurrency ? a.valueCurrency + ' ' : '')) +
            Math.round(a.valueAmount).toLocaleString('en-GB')) + '</span>'
      /* Null is "the notice stated no value". It is never rendered as 0. */
      : '<span style="color:' + DIM + ';">value not stated on the notice</span>';
    var ps = uk(a.periodStart), pe = uk(a.periodEnd);
    /* A notice that gives the same day for both ends states a date, not a
       term. Printing "06/08/2026 to 06/08/2026" reads as a rendering bug. */
    var period = (ps && pe) ? ' &middot; ' + (ps === pe ? esc(ps) : esc(ps) + ' to ' + esc(pe)) : '';
    return '<div style="padding:9px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;line-height:1.55;">' +
      '<b>' + esc(a.title) + '</b>' +
      '<br><span style="font-size:12.5px;color:#37485a;">' + esc(a.buyer || 'buyer not named') +
      ' &middot; ' + esc(uk(a.date) || 'date not stated') + ' &middot; ' + value + period + '</span>' +
      '<br><span style="font-size:12.5px;color:' + DIM + ';">named on the notice as &ldquo;' +
      esc(a.noticeSupplierName) + '&rdquo; &middot; ' +
      '<a href="' + esc(a.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">' +
      esc(a.source) + ' notice &#8599;</a>' +
      (a.hubUrl ? ' &middot; <a href="' + esc(a.hubUrl) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">Award Tracker &#8599;</a>' : '') +
      '</span></div>';
  }

  function awardSection(title, rows, ctx, blurb) {
    if (!ctx.awards) {
      return sec(title, gap('Not captured for this company yet — the award index has not loaded, so this panel has nothing to report either way.'));
    }
    if (!rows.length) {
      var cov = ctx.awards.coverage || {};
      var from = (cov.window && cov.window.from) || (ctx.awards.windows && ctx.awards.windows.length ? ctx.awards.windows[0].from : '');
      return sec(title, gap('Not captured for this company yet. ' + esc(blurb) +
        ' The index has been walked' + (from ? ' from ' + esc(uk(from) || from) : '') +
        ', and nothing in it names this company. Both feeds carry only the windows walked, and only notices the buyer classified under CPV division 33 — so this says what the index holds, not what the company has won.'));
    }
    return sec(title, '<div style="font-size:12px;color:' + DIM + ';margin:0 0 8px;">' +
      rows.length + ' award(s) in the index name this company.</div>' +
      rows.map(awardRow).join(''));
  }

  function panelAwards(sub, ctx) {
    var all = awardsFor(sub, ctx) || [];
    var tender = all.filter(function (a) { return a.section === 'tender-awards'; });
    var contract = all.filter(function (a) { return a.section === 'contract-awards'; });
    var h = '';

    if (ctx.awards && all.length) {
      h += rule('Each award below is a single supplier named on a single statutory award notice, read from ' +
        esc(ctx.awards.source || 'the award feeds') + '. ' +
        esc(ctx.awards.sectionRule || '') +
        '<br><br><b>How this company was identified:</b> ' + esc(ctx.awards.matchRule || '') +
        (ctx.awards.coverage && ctx.awards.coverage.complete === false
          ? '<br><br><b>Coverage is incomplete.</b> ' + esc(ctx.awards.coverage.note || '')
          : ''));
    }

    h += awardSection('Tender awards', tender, ctx,
      'Above-threshold procurements are published on Find a Tender.');
    h += awardSection('Contract awards', contract, ctx,
      'Below-threshold procurements are published on Contracts Finder.');

    /* §15–16 of the page standard. No source exists for either, and a dropped
       heading would leave a member unable to tell "we hold nothing" from
       "there is nothing". So they render, labelled. */
    h += sec('Non-NHSSC sales and contracts', gap('Not captured for this company yet. Sales made outside NHS Supply Chain and outside the statutory notice thresholds are not published anywhere this Hub can read; there is no feed to capture them from, and nothing here is inferred.'));
    h += sec('CQC-related contracts', gap('Not captured for this company yet. The Care Quality Commission publishes regulated providers, not their suppliers, so a supply relationship into a regulated care setting cannot be read from it.'));
    return h;
  }

  function composeSections(sub, ctx) {
    var d = deepFor(sub);
    var h = '';

    h += ledeBox(sub);

    /* -- 1 · Company information ---------------------------------------- */
    h += part('1', 'The company',
      'Who they are, what the public register holds on them, and what the filed accounts show. Everything here is read from a source and linked to it.');
    var info = statGrid(sub);
    if (sub.note) {
      info += '<div style="font-size:13.5px;color:#37485a;line-height:1.6;margin:14px 0 0;">' + esc(sub.note) + '</div>';
    }
    if (sub.voice && (sub.voice.line || sub.voice.angle)) {
      info += '<div style="font-size:13px;color:#37485a;line-height:1.6;margin:10px 0 0;"><b style="color:' + INK + ';">How they sell' + (sub.voice.angle ? ' — ' + esc(sub.voice.angle) : '') + '.</b> ' + esc(sub.voice.line || '') + '</div>';
    }
    h += sec('Company information', info || gap('Nothing curated for this company yet beyond the panels below.'));
    h += panelCompanyFacts(sub, ctx);
    h += ownershipBlock(sub);

    /* -- 2 · Growth, near the top by design ----------------------------- */
    h += growthChart(sub, ctx);

    /* -- 3 · Specialities / divisions as cards -------------------------- */
    h += part('2', 'What they sell, and how it reaches the NHS',
      'Clinical areas, NHS Supply Chain framework positions read from the buying organisation’s own contract launch briefs, and awards named on statutory notices.');
    h += divisionCards(sub, ctx);
    h += frameworks(sub, ctx);
    h += panelAwards(sub, ctx);
    h += repsWatch(sub);

    /* -- 4 · Competitors ------------------------------------------------ */
    h += part('3', 'The field around them <span style="font-size:10px;letter-spacing:1.6px;text-transform:uppercase;color:' + G + ';vertical-align:3px;">&nbsp;· derived</span>',
      'The panels in this part are <b>computed by this page</b>, not read from a source. Each prints the rule it was computed under and refuses to render on thin evidence. None ranks anyone, and none prints a market-share figure — the filing profile shows which statutory regime each confirmed supplier files under, which is the sourceable part of “how big are they”. Read the rule before you quote any of it.');
    var co = coListing(sub, ctx);
    h += panelCoListed(sub, ctx, co);
    h += panelSameSpeciality(sub, ctx, co);
    h += panelFieldProfile(sub, ctx, co);
    if (d && d.marketPosition && d.marketPosition.length) {
      h += sec('Market position', '<div style="font-size:13.5px;line-height:1.7;color:#37485a;">' +
        d.marketPosition.map(function (p) { return '<p style="margin:0 0 8px;">' + esc(p) + '</p>'; }).join('') + '</div>');
    }

    /* -- 5 · News, alerts, people --------------------------------------- */
    h += part('4', 'Signals and people',
      'Press that clears the two-source bar, current alerts and recalls, the statutory officers register, and what it is like to work there.');
    var newsHtml = deepPress(sub);
    var pr = press(sub);
    h += newsHtml ? sec('In the press', newsHtml) + pr : pr;
    h += alerts(sub);
    var pplDeep = deepPeopleCards(sub);
    if (pplDeep) h += sec('Key people', pplDeep);
    h += panelPeople(sub, ctx);

    /* -- 6 · Working there (deep-dive extras) --------------------------- */
    h += workingThere(sub);

    /* -- 7 · The listings, deliberately last ---------------------------- */
    h += part('5', 'The range in full',
      'The long listing, deliberately last: catalogue-verified lines, items confirmed off catalogue, and the full own-site range where a crawl exists.');
    h += productListing(sub, ctx);

    return h;
  }

  function report(sub, ctx) {
    var h = '<article class="mcr-report" style="' + accentVars(sub) + '">';
    h += masthead(sub, ctx, null);
    h += '<div class="mcr-body">';

    /* Stage 5 entry point. The pack is the same composer rendered for
       print — it adds no claims, so the button lives on the card. */
    h += '<div style="display:flex;justify-content:flex-end;align-items:center;gap:12px;margin:14px 0 0;">' +
      '<span style="font-size:11.5px;color:' + DIM + ';">Take it into the meeting:</span>' +
      '<button id="mcrPack" class="mcr-btn">Download / print this report</button></div>';

    h += composeSections(sub, ctx);

    h += '<div class="mcr-src" style="margin-top:22px;">' +
      '<b style="color:' + INK + ';font-weight:700;">Related Hub pages</b><br>' +
      '<a href="/medical-sales-hub/frameworks/">Frameworks</a> &middot; ' +
      '<a href="/medical-sales-hub/awards/">Award Tracker</a> &middot; ' +
      '<a href="/medical-sales-hub/">Live Desk (alerts)</a> &middot; ' +
      '<a href="/medical-sales-hub/news/">News</a></div>';
    h += '</div></article>';
    return h;
  }

  /* =====================================================================
     STAGE 5 — the interview pack. One printable document per supplier,
     sectioned by speciality. It composes the panels above VERBATIM — the
     same functions build the same HTML, so a refused panel arrives refused,
     with its reason, and nothing can appear in print that the page would
     not show. The speciality sections re-present the verified range where a
     full crawl exists; framework and field panels are company-level, and
     the pack says so rather than pretending a per-speciality split it
     cannot source (per-speciality framework attribution needs the award
     feed tagged by product — not built, stated in OUTSTANDING).
     ===================================================================== */
  function packSpecialitySections(sub, ctx) {
    var deep = deepRangeFor(sub, ctx.prodFile);
    if (!(deep && deep.divisions && deep.divisions.length)) {
      return '<div style="font-size:12px;color:' + DIM + ';line-height:1.6;">Per-speciality sections need the full site crawl for this company, which has not run yet — the range above is the curated and catalogue-verified view. The crawl is the same mechanism that built the GBUK tree and runs supplier by supplier.</div>';
    }
    var prods = deep.products || [];
    return deep.divisions.map(function (d) {
      var mine = prods.filter(function (p) { return p.division === d.name; });
      var byCat = {};
      mine.forEach(function (p) {
        var c = p.category || 'Uncategorised';
        (byCat[c] = byCat[c] || []).push(p.n);
      });
      var cats = Object.keys(byCat).sort();
      return '<div style="margin:0 0 14px;page-break-inside:avoid;">' +
        '<div style="font-size:14px;font-weight:700;color:' + INK + ';border-bottom:2px solid ' + G + ';padding-bottom:3px;margin-bottom:6px;">' + esc(d.name) +
        ' <span style="font-weight:400;color:' + DIM + ';font-size:12px;">· ' + mine.length + ' product(s)' +
        (d.specialities && d.specialities.length ? ' · ' + d.specialities.map(esc).join(', ') : '') + '</span></div>' +
        cats.map(function (c) {
          return '<div style="font-size:12.5px;line-height:1.65;margin:0 0 4px;"><b style="color:#4a5766;">' + esc(c) + ':</b> ' +
            byCat[c].map(esc).join(' · ') + '</div>';
        }).join('') +
        '</div>';
    }).join('');
  }

  function buildPack(sub, ctx) {
    var today = new Date();
    var stamp = ('0' + today.getDate()).slice(-2) + '/' + ('0' + (today.getMonth() + 1)).slice(-2) + '/' + today.getFullYear();
    var d = deepFor(sub);
    var inner =
      '<article class="mcr-report" style="' + accentVars(sub) + '">' +
      masthead(sub, ctx, stamp) +
      '<div class="mcr-body">' +
      composeSections(sub, ctx) +
      part('6', 'The range by speciality', 'The verified range, split the way the company splits it. Company-level panels above are not re-cut per speciality, because that attribution is not sourced.') +
      sec('The range by speciality', packSpecialitySections(sub, ctx)) +
      '<div class="mcr-src" style="margin-top:22px;">' +
        'Prepared by the Medical Sales Intelligence Hub (medsalesintelligencehub.co.uk) for the member who generated it. ' +
        'Sources are linked panel by panel; derived panels print their derivation. ' +
        (d && d.sources ? 'Deep-dive sources: ' + esc(d.sources) + ' ' : '') +
        'Company marks shown are the property of their respective owners and appear for identification only. ' +
        '© Elevate and Thrive Ltd ' + today.getFullYear() + '. Not for redistribution.</div>' +
      '</div></article>';

    /* The pack is the same markup and the same stylesheet as the on-page
       card — it must be, or the printed document and the page would drift.
       The page wrapper below is all that differs: a printable measure, a
       white ground when printing, and the print button that removes itself. */
    return '<!doctype html><html lang="en-GB"><head><meta charset="utf-8">' +
      '<meta name="viewport" content="width=device-width,initial-scale=1">' +
      '<title>' + esc(sub.name) + ' — Company Intelligence Report</title>' +
      '<style>' + STYLE +
      'body{margin:26px auto;max-width:900px;padding:0 18px;background:#f2eee5;}' +
      '@media print{body{margin:0;max-width:none;padding:0;background:#fff;}' +
      '@page{margin:14mm;}}' +
      '*{-webkit-print-color-adjust:exact;print-color-adjust:exact;}</style></head>' +
      '<body class="mcr">' +
      '<div style="text-align:right;margin:0 0 12px;">' +
      '<button onclick="window.print()" class="mcr-btn">Print / save as PDF</button></div>' +
      inner + '</body></html>';
  }

  function openPack(sub, ctx) {
    var w = window.open('', '_blank');
    if (!w) return; /* popup blocked — the on-page card is the same content */
    w.document.open();
    w.document.write(buildPack(sub, ctx));
    w.document.close();
  }

  function shell() {
    injectStyle();
    MOUNT.innerHTML = '' +
      '<div class="mcr">' +
        '<div style="padding:2px 0 8px;">' +
          '<div style="font-size:10.5px;letter-spacing:2.2px;text-transform:uppercase;font-weight:700;color:' + G + ';">Company intelligence report</div>' +
          '<p style="margin:6px 0 14px;font-size:13.5px;color:' + DIM + ';line-height:1.65;max-width:62em;">Pick a speciality, then a company — get who they are, what they sell, the frameworks they hold, live alerts, corroborated press, and who else sits on those frameworks. <span id="mcrCount"></span></p>' +
          /* SPECIALITY FIRST (Lou, 11/08/2026). The box used to offer every
             indexed company at once. Choosing the clinical area first cuts the
             suggestions to the firms recorded in it — through the canonical
             speciality map, so this filters on the same reconciled ids the
             report's own panels use rather than on raw strings that drifted. */
          '<label class="mcr-lab" for="mcrSpec">1 &middot; Speciality</label>' +
          '<select id="mcrSpec" class="mcr-field" style="margin:0 0 13px;"></select>' +
          '<label class="mcr-lab" for="mcrInput">2 &middot; Company <span id="mcrScope" style="font-weight:400;text-transform:none;letter-spacing:0;color:' + DIM + ';"></span></label>' +
          '<input id="mcrInput" class="mcr-field" list="mcrList" autocomplete="off" placeholder="e.g. GBUK Group, BD, Vygon, Coloplast…">' +
          '<datalist id="mcrList"></datalist>' +
          '<div id="mcrChips" style="margin:11px 0 2px;display:flex;flex-wrap:wrap;gap:7px;"></div>' +
        '</div>' +
        '<div id="mcrResult" style="padding:4px 0 18px;"></div>' +
      '</div>';
  }

  function boot(index, seed, specMap, prodFile, fin, cache, fwDoc, awards, logoDoc) {
    /* Brand marks, by company name. Held at module scope rather than passed
       through ctx because logoImg() and brandOf() are called from the print
       pack as well as the on-page card, and threading a ninth argument through
       both would be the kind of change that gets half done. */
    LOGO = {};
    ((logoDoc && logoDoc.logos) || []).forEach(function (r) {
      if (r && r.name && r.file) LOGO[r.name] = r;
    });

    var all = mergeSuppliers(index, seed);
    var byName = {};
    all.forEach(function (s) { byName[s.name] = s; });

    /* framework key -> deduped list of supplier names holding it. Built once
       from the merged set so both the count and the rows come from the same
       place. */
    var fwMap = {};
    all.forEach(function (s) {
      fwList(s).forEach(function (f) {
        if (!fwMap[f.key]) fwMap[f.key] = [];
        if (fwMap[f.key].indexOf(s.name) === -1) fwMap[f.key].push(s.name);
      });
    });

    var ctx = {
      all: all,
      byName: byName,
      fwMap: fwMap,
      asOf: (index && index.dataAsOf) || '',
      spec: specCtx(specMap, prodFile),
      prodFile: prodFile,
      fin: fin || null,
      cache: cache || null,
      fwDoc: fwDoc || null,
      fwByKey: fwIndex(fwDoc),
      awards: awards || null,
      /* The briefs print legal names ("B. Braun Medical Limited"); this Hub
         holds trading names ("B. Braun Medical"). Matching those by exact
         string made every confirmed company on a framework look unresolved,
         so the filing profile refused even where the filings were held. */
      byKey: (function () {
        var m = {};
        all.forEach(function (s) {
          [s.name].concat(s.aliases || []).forEach(function (n) {
            var k = coKey(n);
            if (k && !m[k]) { m[k] = s; }
          });
        });
        return m;
      })()
    };

    shell();
    var input = document.getElementById('mcrInput'),
        list = document.getElementById('mcrList'),
        result = document.getElementById('mcrResult'),
        chips = document.getElementById('mcrChips'),
        count = document.getElementById('mcrCount'),
        specSel = document.getElementById('mcrSpec'),
        scopeNote = document.getElementById('mcrScope');

    count.textContent = all.length + ' companies indexed · data as of ' + (ctx.asOf || 'date not recorded');

    /* Speciality -> companies, built from the companies themselves rather than
       from the map's full canon, so every option in the picker has at least one
       company behind it. An option that opens onto an empty list is a bug a
       member reads as "nobody sells this". */
    var SPEC_COS = {};
    all.forEach(function (s) {
      ctx.spec.ids(s).forEach(function (id) {
        if (!SPEC_COS[id]) SPEC_COS[id] = [];
        SPEC_COS[id].push(s);
      });
    });
    var SPEC_IDS = Object.keys(SPEC_COS).sort(function (a, b) {
      return String(ctx.spec.label(a)).toLowerCase() < String(ctx.spec.label(b)).toLowerCase() ? -1 : 1;
    });
    var untagged = all.filter(function (s) { return !ctx.spec.ids(s).length; }).length;
    specSel.innerHTML = '<option value="">— all specialities (' + all.length + ' companies) —</option>' +
      SPEC_IDS.map(function (id) {
        return '<option value="' + esc(id) + '">' + esc(ctx.spec.label(id)) + ' · ' + SPEC_COS[id].length + '</option>';
      }).join('');

    function pool() {
      var v = specSel.value;
      return v && SPEC_COS[v] ? SPEC_COS[v] : all;
    }
    function refreshScope() {
      var p = pool(), v = specSel.value;
      list.innerHTML = p.map(function (s) { return '<option value="' + esc(s.name) + '">'; }).join('');
      var quick = v
        ? p.slice(0, 5).map(function (s) { return s.name; })
        : ['GBUK Group', 'BD — Becton, Dickinson', 'Vygon (UK)', 'Coloplast', 'Convatec'].filter(function (q) { return !!byName[q]; });
      chips.innerHTML = quick.map(function (q) {
        return '<button class="mcr-quick" data-q="' + esc(q) + '">' + esc(q.split(' — ')[0]) + '</button>';
      }).join('');
      /* Say what the filter is hiding. Companies with no speciality recorded
         drop out of every scoped list, and that is a gap in our tagging, not
         evidence they sell nothing — so it is stated rather than swallowed. */
      scopeNote.textContent = v
        ? '— ' + p.length + ' in ' + ctx.spec.label(v) + (untagged ? ' · ' + untagged + ' companies have no speciality recorded and are only reachable with the filter cleared' : '')
        : '';
    }
    refreshScope();
    specSel.addEventListener('change', function () {
      refreshScope();
      if (input.value.trim()) show(input.value);
    });

    function findIn(pool2, n) {
      var hit = pool2.filter(function (s) {
        return norm(s.name) === n || (s.aliases || []).some(function (a) { return norm(a) === n; });
      })[0];
      if (hit) return hit;
      return pool2.filter(function (s) {
        if (norm(s.name).indexOf(n) > -1) return true;
        if ((s.aliases || []).some(function (a) { return norm(a).indexOf(n) > -1; })) return true;
        if ((s.products || []).some(function (p) { return norm(typeof p === 'string' ? p : (p && p.n)).indexOf(n) > -1; })) return true;
        return false;
      })[0] || null;
    }
    /* The speciality scopes the SUGGESTIONS, never the answer. A member who
       types a real company still gets its report, with a line saying it sits
       outside the speciality on screen — refusing a company we hold a report
       for, because our own tagging did not reach it, would be the worse
       failure of the two. */
    var outOfScope = null;
    function find(q) {
      var n = norm(q);
      outOfScope = null;
      if (!n) return null;
      var inScope = findIn(pool(), n);
      if (inScope) return inScope;
      var anywhere = specSel.value ? findIn(all, n) : null;
      if (anywhere) outOfScope = anywhere;
      return anywhere;
    }
    function show(q) {
      var s = find(q);
      var flag = (s && outOfScope) ? '<div style="margin:0 0 12px;padding:10px 14px;border-left:3px solid ' + G + ';background:' + SOFT +
        ';border-radius:0 8px 8px 0;font-size:12.5px;color:' + INK + ';line-height:1.6;"><b>' + esc(s.name) +
        '</b> is not recorded under ' + esc(ctx.spec.label(specSel.value)) +
        ', so it is not in the list above. Its report is below in full.</div>' : '';
      result.innerHTML = s ? (flag + report(s, ctx)) :
        '<div style="padding:14px 4px;font-size:13.5px;color:' + DIM + ';line-height:1.6;">No match for “' + esc(q) +
        '”. Coverage is the tracked-supplier set (' + all.length + ' indexed) — a company that is not here is <b>not yet indexed</b>, not “nothing found”.</div>';
      var pk = document.getElementById('mcrPack');
      if (pk && s) pk.addEventListener('click', function () { openPack(s, ctx); });
    }
    input.addEventListener('change', function () { show(input.value); });
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') show(input.value); });
    chips.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('button') : null;
      if (b) { input.value = b.getAttribute('data-q'); show(input.value); }
    });

    if (window.MSH_COMPANY_REPORT_OPEN) show(window.MSH_COMPANY_REPORT_OPEN);

    /* ?company= deep link, e.g. from the Live Desk's supplier-press panel
       (SPEC-live-desk-supplier-press-block.md §4). Resolved the same way a
       typed name is - through find()/show(), which normalises case and
       punctuation before matching. An unresolved or absent parameter changes
       nothing: the picker is left exactly as it is with no query string. */
    try {
      var qp = new URLSearchParams(window.location.search).get('company');
      if (qp) { input.value = qp; show(qp); }
    } catch (e) { /* URLSearchParams unsupported: deep link silently no-ops, picker still works */ }

    /* Harness hook, same family as MSH_COMPANY_REPORT_OPEN: lets a test page
       pull the Stage 5 pack HTML for a named company without opening a popup
       window. Carries no data of its own — it is the same buildPack the
       button calls. */
    window.MSH_COMPANY_REPORT_BUILD = function (q) {
      var s = find(q);
      return s ? buildPack(s, ctx) : null;
    };
  }

  /* Test / preload hook, same pattern as supplier-search.js's
     window.MSH_SUPPLIER_INDEX — lets a harness run this file against local
     copies of the data without touching the network. */
  if (window.MSH_COMPANY_REPORT_DATA) {
    var P = window.MSH_COMPANY_REPORT_DATA;
    boot(P.index, P.seed, P.specMap, P.products, P.financials, P.nhssc, P.frameworks,
         P.awards, P.logos);
    return;
  }

  injectStyle();
  MOUNT.innerHTML = '<div class="mcr"><div class="mcr-card mcr-card--empty">' +
    '<div class="mcr-card-t">Company intelligence report</div>' +
    '<div class="mcr-note">Loading the index…</div></div></div>';
  // cache:'no-store' removed 17/08/2026 — the URLs already carry a daily CB,
  // so letting the browser reuse a same-day response is a feature, not a bug.
  Promise.all([
    fetch(IDX).then(function (r) { return r.json(); }),
    fetch(SEED).then(function (r) { return r.json(); }).catch(function () { return { suppliers: [] }; }),
    fetch(SPECMAP).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(PRODUCTS).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(FIN).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(NHSSC).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(FWDATA).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(AWARDS).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(LOGOS).then(function (r) { return r.json(); }).catch(function () { return null; })
  ]).then(function (res) { boot(res[0], res[1], res[2], res[3], res[4], res[5], res[6], res[7], res[8]); })
    .catch(function () {
      MOUNT.innerHTML = '<div class="mcr"><div class="mcr-card mcr-card--empty">' +
        '<div class="mcr-card-t">Company intelligence report</div>' +
        '<div class="mcr-note">The company report is loading its data — if this persists, the index feed is temporarily unreachable. Nothing is missing from the report; the report has not loaded.</div></div></div>';
    });
})();
