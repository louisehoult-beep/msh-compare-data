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

  /* Eleventh fetch, added 25/08/2026. NHS Supply Chain framework awards that
     are public on Find a Tender but not yet on NHSSC's own contract launch
     brief — see scripts/refresh_pending_awards.py. Optional like the awards
     feed above: if it does not load, the pending-award panel simply does not
     render (it already renders nothing when a company has none), never a
     claim that no award exists. */
  var PENDING = BASE + 'data/pending-awards.json' + CB;

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

  /* Tenth fetch, added 21/08/2026. The Compare/Differentiator product feed —
     the same gated, categorised product data the Compare Your Product tool
     reads. This is what makes a TRUE product-level competitor list possible:
     each row already carries a comparison-locked category (`cat`) and a
     source URL on the supplier's own site, so two products can only be put
     side by side where their `cat` is identical — never a speciality guess.
     Optional like the four before it: if it does not load, the new
     "Also selling in this category" block says so and the rest of the
     report is unaffected. */
  var DIFF = BASE + 'data/differentiator.json' + CB;

  /* This page's own URL, captured once at load. Every company cross-link is
     this URL plus ?company=<name> — see coHref() below. Captured rather than
     hardcoded so the tool keeps cross-linking correctly if the report is ever
     mounted on a differently-slugged page, and captured HERE, in the host
     page, because the printable pack is written into an about:blank popup
     where location carries nothing to build a link from. */
  var REPORT_URL = (function () {
    try {
      var l = window.location;
      if (l && l.pathname) { return (l.origin ? l.origin : '') + l.pathname; }
    } catch (e) { /* fall through to the published path */ }
    return 'https://medsalesintelligencehub.co.uk/medical-sales-hub/company-report/';
  })();

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

  /* seed.image ("hero image", page standard §2A) is read straight from the
     seed as an <img src>. Every value recorded so far has been a full
     external URL (the company's own site, a favicon service), so raw src
     worked. The first REPO-SERVED hero (an asset committed under assets/
     and referenced by its repo-relative path) exposed that raw src resolves
     a relative path against the WordPress page the widget is embedded on,
     not against this repo — a silent 404, not an error anyone would notice.
     Every other repo-served asset on this page (LOGO[].file) is already
     BASE-prefixed; this brings seed.image in line with that instead of
     inventing a second convention. */
  function imgSrc(v) {
    var s = String(v || '');
    if (!s) return '';
    return /^https?:\/\//i.test(s) ? s : BASE + s;
  }

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
     HOUSE STYLESHEET — redesigned 18/08/2026, respaced and de-collided
     18/08/2026 (pm).

     ONE stylesheet, shipped inside this file, used by BOTH the on-page card
     and the printable pack, so the two surfaces cannot drift apart. It is
     entirely self-contained: no external stylesheet, no web font, no CDN
     script — the Hub page must render this with zero third-party requests.

     TWO HOST RULES REACH IN, AND BOTH HAD TO BE BEATEN ON THEIR OWN TERMS.
     Read this before "tidying" any selector below.

     1. EVERY SELECTOR CARRIES A `.mcr ` PREFIX. The Hub page's own token
        block declares `.msh *{margin:0;padding:0;box-sizing:border-box}`,
        and this report mounts inside `div.msh`. A bare `.mcr-card` and
        `.msh *` are BOTH specificity 0,1,0, so the tie breaks on document
        order — and this style element is appended to <head> while the page's
        block sits in the body, so the page won every tie. Measured live on
        18/08/2026: .mcr-body, .mcr-card and .mcr-part all computed to
        padding 0, which is why the report's text sat hard against the card
        edges. The prefix makes each rule 0,2,0 and settles it on
        specificity rather than on where the <style> happens to land.

     2. THE PICKER FIELDS CARRY !important. The theme's own form rule is
        `textarea:not(.block-editor-plain-text), input:not([type="submit"])
        :not([type="checkbox"]):not([type="radio"]):not([type="range"])…`
        — specificity 0,4,1, which no sane class selector reaches. It paints
        `--wp--custom--input-background`, a near-black navy, so the company
        box rendered as dark ink on a dark ground and the member could not
        read what they had typed. !important is the correct instrument for a
        rule that specific; do not swap it for more classes.

     THE REPORT'S OUTER CAP IS RESPONSIVE, NOT FLAT — widened 19/08/2026 after
     Lou flagged the page as "not full width" on her own screen. A flat
     1180px card centred in a 2,450px window left ~635px of dead space each
     side; min(1600px,96vw) keeps that gutter to a normal margin on a wide
     monitor while still capping out well short of full-bleed on anything
     wider. This cap is on .mcr-report only, never on .mcr itself: the
     printable pack sets its own measure on <body class="mcr">, and a
     max-width on .mcr would out-specify it. It was never the fix for
     unreadable text, either — that job stays with the `max-width:66em` on
     prose blocks (.mcr-part-s and similar), which is untouched here and is
     the thing actually protecting line length.

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
    'color:var(--mcr-body);font-size:14px;line-height:1.62;}',
    '.mcr *{box-sizing:border-box;}',
    '.mcr p{margin:0 0 12px;}',
    '.mcr p:last-child{margin-bottom:0;}',
    '.mcr a{color:var(--mcr-gold);font-weight:600;text-decoration:none;}',
    '.mcr a:hover{text-decoration:underline;}',
    /* Cross-link to another company's report. HOUSE GOLD, deliberately, not
       var(--mcr-accent-ink): the accent is the company's own colour and it
       carries rules and edges only, never copy — and these links sit inside
       body copy and table cells. It must not set a weight either, because a
       name here inherits a weight that already means something (bold marks
       the company being read in the filing table). Quiet underline, no second
       colour fighting the prose. */
    '.mcr .mcr-colink{color:var(--mcr-gold);font-weight:inherit;text-decoration:none;',
    'border-bottom:1px solid rgba(168,132,44,.42);}',
    '.mcr .mcr-colink:hover{border-bottom-color:var(--mcr-gold);}',

    /* --- report shell + masthead ------------------------------------- */
    /* The measure. min(1600px,96vw): fills most of a wide monitor while
       leaving a real margin on anything wider still, and on a normal
       laptop screen 96vw is already narrower than 1600px so nothing
       changes there. See the note above the STYLE array for why this
       isn't a flat number any more. */
    '.mcr .mcr-report{max-width:min(1600px,96vw);margin:0 auto;border:1px solid var(--mcr-line);',
    'border-radius:14px;background:#fdfcf9;overflow:hidden;',
    'box-shadow:0 2px 16px rgba(11,28,51,.07);}',
    '.mcr .mcr-mast{position:relative;padding:30px 34px 24px;',
    'background:linear-gradient(135deg,#0B1C33 0%,#132B4A 55%,#1B3A5F 100%);',
    '-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr .mcr-mast:before{content:"";position:absolute;left:0;right:0;top:0;height:5px;',
    'background:var(--mcr-accent);-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr .mcr-mast-row{display:flex;gap:20px;align-items:center;flex-wrap:wrap;}',
    /* The plate the company's own mark sits on. The ring is the company's
       colour on navy — the one place in the report where its colour touches
       its own mark. A company with no colour gets the house Antique Gold ring,
       which is what this line was before there were any colours to use. */
    '.mcr .mcr-logo{width:74px;height:74px;flex:0 0 74px;border-radius:14px;background:#fff;',
    'overflow:hidden;display:flex;align-items:center;justify-content:center;',
    'box-shadow:0 3px 12px rgba(0,0,0,.24);border:2px solid var(--mcr-accent);',
    '-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr .mcr-kicker{font-size:9.5px;letter-spacing:2.2px;text-transform:uppercase;font-weight:700;',
    'color:#E0BE8E;margin:0 0 8px;}',
    '.mcr .mcr-h1{color:#fff;font-size:27px;font-weight:700;line-height:1.16;letter-spacing:.2px;margin:0;}',
    '.mcr .mcr-tagline{color:rgba(237,231,220,.86);font-size:12.5px;font-weight:600;',
    'margin-top:7px;line-height:1.5;}',
    '.mcr .mcr-links{display:flex;gap:8px;flex-wrap:wrap;margin-left:auto;}',
    '.mcr .mcr-links a{font-size:11px;font-weight:700;letter-spacing:.4px;padding:8px 15px;',
    'border-radius:99px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.34);',
    'color:#fff;white-space:nowrap;}',
    '.mcr .mcr-links a:hover{background:rgba(255,255,255,.24);text-decoration:none;}',
    '.mcr .mcr-mast-meta{margin-top:18px;padding-top:14px;border-top:1px solid rgba(255,255,255,.16);',
    'font-size:11px;line-height:1.8;color:#9FB0C5;}',
    '.mcr .mcr-mast-meta b{color:#DBE3EE;font-weight:600;}',

    /* --- body, parts, cards ------------------------------------------ */
    '.mcr .mcr-body{padding:6px 30px 30px;}',
    /* Part dividers. The short bar sitting on the divider is the company's
       colour on light — it repeats the accent four or five times down a long
       report without ever becoming the report's own colour scheme. */
    '.mcr .mcr-part{position:relative;margin:34px 0 0;padding-top:20px;',
    'border-top:2px solid var(--mcr-line);}',
    '.mcr .mcr-part:before{content:"";position:absolute;left:0;top:-2px;width:38px;height:2px;',
    'background:var(--mcr-accent-ink);-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr .mcr-part-n{font-size:10px;letter-spacing:2px;text-transform:uppercase;font-weight:700;',
    'color:var(--mcr-gold);}',
    '.mcr .mcr-part-t{font-size:17px;font-weight:700;color:var(--mcr-navy);line-height:1.3;margin-top:4px;}',
    '.mcr .mcr-part-s{font-size:12.5px;color:var(--mcr-dim);line-height:1.62;margin-top:6px;max-width:66em;}',
    '.mcr .mcr-card{background:#fff;border:1px solid var(--mcr-line);border-radius:12px;',
    'padding:22px 24px;margin:16px 0 0;box-shadow:0 1px 2px rgba(29,39,51,.05);}',
    '.mcr .mcr-card-t{display:flex;align-items:center;gap:9px;font-size:11px;letter-spacing:1.4px;',
    'text-transform:uppercase;font-weight:700;color:var(--mcr-navy);margin:0 0 14px;}',
    '.mcr .mcr-card-t:before{content:"";flex:0 0 16px;height:2px;background:var(--mcr-gold);',
    '-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    /* The deliberate empty state. Thin data is the normal case here, so a
       panel with nothing behind it is drawn as a finished, quiet thing —
       dashed edge, no drop shadow, ivory ground — never as a blank box that
       reads as a page that failed to load. */
    '.mcr .mcr-card--empty{background:#faf8f3;border-style:dashed;border-color:#ded6c4;box-shadow:none;}',
    '.mcr .mcr-card--empty .mcr-card-t{color:#8d8677;}',
    '.mcr .mcr-card--empty .mcr-card-t:before{background:#cfc6b2;}',
    /* Collapsible panels. A well-covered company runs to twenty-odd panels,
       which is a very long scroll for a member looking for one of them, so
       every panel is a native <details>. Native is the whole point: the
       keyboard behaviour, the screen-reader expanded/collapsed state and
       the browser's own in-page find are all free and correct, and the page
       still makes zero third-party requests. The first two panels of a
       report open on load so it never lands looking empty. */
    '.mcr details.mcr-card{display:block;}',
    '.mcr details.mcr-card>summary{cursor:pointer;list-style:none;}',
    '.mcr details.mcr-card>summary::-webkit-details-marker{display:none;}',
    '.mcr details.mcr-card>summary::marker{content:"";}',
    /* Closed, the panel is title only, so the title's 14px bottom margin
       would leave a dead band inside the card. */
    '.mcr details.mcr-card:not([open])>summary.mcr-card-t{margin-bottom:0;}',
    '.mcr details.mcr-card>summary:focus-visible{outline:2px solid var(--mcr-gold);outline-offset:3px;}',
    /* The chevron is drawn from two borders rather than an image or a font,
       so it inherits the gold and costs no request. It points down when the
       panel is shut and up when it is open, which is the affordance that
       tells a member the title is a control at all. */
    '.mcr .mcr-card-x{margin-left:auto;flex:0 0 auto;width:8px;height:8px;',
    'border-right:2px solid var(--mcr-gold);border-bottom:2px solid var(--mcr-gold);',
    'transform:translateY(-2px) rotate(45deg);transition:transform .18s ease;}',
    '.mcr details.mcr-card[open]>summary .mcr-card-x{transform:translateY(2px) rotate(-135deg);}',
    '.mcr .mcr-card--empty .mcr-card-x{border-color:#cfc6b2;}',
    /* CLOSED-PANEL GRID — added 19/08/2026. A well-covered company runs to
       20-odd panels and only the first two open on load (see the note two
       screens up), so the rest used to stack one full-width row each —
       measured on GBUK's report: 23 closed panels, 1,118px wide, 64px tall,
       holding nothing but a title. groupClosedPanels() (below, in show())
       wraps each run of consecutive closed <details> in one of these at
       render time; it never touches the print pack, which forces every
       panel open before it wraps anything (see buildPack). A panel opened
       from inside the grid spans the full row via the plain [open] rule
       below — no :has() needed, since it only has to react to its own
       state, not a sibling's. */
    '.mcr .mcr-toc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;margin:16px 0 0;}',
    '.mcr .mcr-toc-grid details.mcr-card{margin:0;padding:14px 16px;}',
    '.mcr .mcr-toc-grid details.mcr-card[open]{grid-column:1/-1;padding:22px 24px;}',
    '.mcr .mcr-note{font-size:12.5px;color:var(--mcr-dim);line-height:1.68;}',
    '.mcr .mcr-good{font-size:12.5px;color:#2e7d5b;line-height:1.68;}',
    /* --- alerts & recalls -------------------------------------------- */
    /* One item, three states. The neutral border is a curated note; the red is
       a genuine recall; the dashed ivory is an entry with no source link, and
       it deliberately borrows .mcr-card--empty's language rather than adding a
       new one, because it means the same thing: honestly incomplete. */
    '.mcr .mcr-alert{padding:9px 11px;margin:0 0 7px;background:#fff;border-radius:7px;',
    'border-left:3px solid var(--mcr-line);font-size:13px;color:var(--mcr-body);line-height:1.6;}',
    '.mcr .mcr-alert--recall{border-left-color:#b84a5c;}',
    '.mcr .mcr-alert--recall .mcr-alert-d{color:#b84a5c;}',
    '.mcr .mcr-alert--unsourced{background:#faf8f3;border-left-style:dashed;box-shadow:none;}',
    '.mcr .mcr-alert-x{color:var(--mcr-body);}',
    '.mcr .mcr-alert-u{color:var(--mcr-gold);}',
    '.mcr .mcr-alert .mcr-note{margin-top:4px;}',
    '.mcr .mcr-rule{margin:0 0 14px;padding:13px 16px;background:var(--mcr-soft);',
    'border-left:3px solid var(--mcr-gold);border-radius:0 8px 8px 0;font-size:12px;',
    'color:#4a5766;line-height:1.65;}',
    '.mcr .mcr-rule-h{display:block;font-size:9.5px;letter-spacing:1.6px;text-transform:uppercase;',
    'font-weight:700;color:var(--mcr-gold);margin-bottom:5px;}',

    /* Company facts, as tiles rather than a single-column table — added
       19/08/2026. Five or six short facts used to be one per full-width
       row; a long value (registered office, latest accounts wording) still
       needs the full row, everything else packs two or three across. The
       wide/compact split is decided in fact() by the value's own length,
       not hardcoded per label, so it holds however the register data
       varies from company to company. */
    '.mcr .mcr-facts{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px 18px;}',
    '.mcr .mcr-fact--wide{grid-column:1/-1;}',
    '.mcr .mcr-fact-k{font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;font-weight:700;color:var(--mcr-dim);margin-bottom:3px;}',
    '.mcr .mcr-fact-v{font-size:13px;color:var(--mcr-ink);line-height:1.5;}',
    /* Frameworks, two columns on a wide card — added 19/08/2026. GBUK's 23
       rows used one full-width line each for what is a three-line entry;
       two columns roughly halves the scroll. Each row keeps its own
       border-bottom, so the grid reads as a table without being one. */
    '.mcr .mcr-fw-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:0 28px;}',

    /* --- chips, source lines, tables ---------------------------------- */
    '.mcr .mcr-chip{display:inline-block;background:#fff;color:#37485a;border:1px solid var(--mcr-line);',
    'border-radius:99px;padding:5px 12px;font-size:11.5px;font-weight:600;line-height:1.5;',
    'margin:0 7px 7px 0;}',
    '.mcr .mcr-chip--gold{background:#f6efdd;border-color:#e7d8b3;color:#7a5b14;}',
    /* Framework-category chips — deliberately NOT the plain white product-chip
       style or the gold speciality style, so a reader can never mistake an
       NHS Supply Chain framework category label for a curated branded product
       name. Dashed border marks it as a derived/sourced tag, not a fact typed
       in by hand; SOFT/DIM are the same house tones used for provenance text
       elsewhere on this page (mcr-src). */
    '.mcr .mcr-chip--muted{background:' + SOFT + ';border-style:dashed;border-color:' + LINE + ';color:' + DIM + ';}',
    '.mcr .mcr-src{margin-top:14px;padding-top:10px;border-top:1px dotted var(--mcr-line);',
    'font-size:11.5px;color:var(--mcr-dim);line-height:1.65;}',
    '.mcr .mcr-asof{white-space:nowrap;}',
    /* Wide tables scroll inside their own card rather than widening it. */
    '.mcr .mcr-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;}',
    '.mcr .mcr-btn{cursor:pointer;background:linear-gradient(180deg,#D4AF7A,#B8935A);color:#0B1C33;',
    'border:0;border-radius:99px;padding:10px 20px;font-size:12.5px;font-weight:700;letter-spacing:.03em;',
    '-webkit-print-color-adjust:exact;print-color-adjust:exact;}',
    '.mcr .mcr-btn:hover{background:linear-gradient(180deg,#E0BE8E,#C49B5C);}',

    /* --- the picker --------------------------------------------------- */
    /* !important throughout: see note 2 at the top of this stylesheet. The
       theme's form rule is 0,4,1 and paints a near-black ground. */
    '.mcr .mcr-lab{display:block;font-size:10.5px;font-weight:700;letter-spacing:1.4px;',
    'text-transform:uppercase;color:var(--mcr-dim);margin:0 0 7px;}',
    '.mcr .mcr-field{width:100%;max-width:520px;border-radius:99px;font:inherit;',
    'padding:12px 18px!important;font-size:14.5px!important;',
    'background:#fff!important;background-image:none!important;',
    'color:var(--mcr-ink)!important;-webkit-text-fill-color:var(--mcr-ink)!important;',
    'caret-color:var(--mcr-ink)!important;border:1px solid var(--mcr-line)!important;',
    'box-shadow:none;outline:none;appearance:none;-webkit-appearance:none;}',
    /* The select keeps a chevron, since stripping the native appearance also
       strips the affordance that says it opens a list. */
    '.mcr select.mcr-field{padding-right:40px!important;',
    'background:#fff url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'12\' height=\'8\'%3E%3Cpath d=\'M1 1l5 5 5-5\' fill=\'none\' stroke=\'%2375808d\' stroke-width=\'2\'/%3E%3C/svg%3E") no-repeat right 17px center!important;}',
    '.mcr .mcr-field::placeholder{color:#9aa3ad;-webkit-text-fill-color:#9aa3ad;opacity:1;}',
    '.mcr .mcr-field:focus{border-color:#C49B5C!important;box-shadow:0 0 0 3px rgba(196,155,92,.16);}',
    '.mcr .mcr-quick{cursor:pointer;background:#fff;border:1px solid var(--mcr-line);border-radius:99px;',
    'padding:7px 14px;font-size:12px;font-weight:600;color:var(--mcr-navy);}',
    '.mcr .mcr-quick:hover{background:var(--mcr-soft);border-color:#C49B5C;}',

    /* --- phones ------------------------------------------------------- */
    '@media (max-width:640px){',
    '.mcr .mcr-body{padding:4px 16px 20px;}',
    '.mcr .mcr-mast{padding:22px 18px 18px;}',
    '.mcr .mcr-mast-row{gap:14px;}',
    '.mcr .mcr-logo{width:54px;height:54px;flex:0 0 54px;border-radius:11px;}',
    '.mcr .mcr-h1{font-size:20.5px;}',
    '.mcr .mcr-links{margin-left:0;width:100%;}',
    '.mcr .mcr-card{padding:16px 16px;border-radius:11px;}',
    '.mcr .mcr-part{margin-top:26px;}',
    '.mcr .mcr-part-t{font-size:15.5px;}',
    '}',

    /* --- print: the downloadable pack --------------------------------- */
    '@media print{',
    '.mcr .mcr-report{border:0;box-shadow:none;border-radius:0;max-width:none;}',
    '.mcr .mcr-body{padding:0;}',
    '.mcr .mcr-card{box-shadow:none;break-inside:avoid;page-break-inside:avoid;margin-top:12px;}',
    /* A shut <details> hides its body from PRINT as well as from the screen,
       so a collapsed panel would come out of the printer as a heading with
       nothing under it. The pack build stamps `open` on every panel before it
       writes the document, which is the mechanism that is relied on; the rules
       below are the second line, for anyone printing the on-page card straight
       from the browser rather than through the pack button. Both forms are
       here because the engines hide the body differently: older ones set
       display:none on the children, current Chrome hides the ::details-content
       slot, which only the pseudo-element reaches. Measured in Chrome on
       18/08/2026: the child rule alone did not reveal a shut panel, the
       ::details-content rule did. The chevron is dropped in print — on paper
       there is nothing to click. */
    '.mcr details.mcr-card::details-content{content-visibility:visible;display:block;block-size:auto;}',
    '.mcr details.mcr-card>*{display:revert;content-visibility:visible;}',
    '.mcr details.mcr-card:not([open])>summary.mcr-card-t{margin-bottom:14px;}',
    '.mcr .mcr-card-x{display:none;}',
    '.mcr .mcr-part{break-before:auto;break-after:avoid;page-break-after:avoid;}',
    '.mcr .mcr-btn{display:none;}',
    '.mcr a{text-decoration:none;}',
    /* On paper a cross-link is a dead link, so it reads as what it is: the
       company's name in the surrounding text's own weight and colour. */
    '.mcr .mcr-colink{color:inherit;font-weight:inherit;border-bottom:0;}',
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
  /* How many panels a report opens on load. Two is enough to prove the page
     rendered without burying the rest of it. */
  var SEC_OPEN = 2;
  var secCount = 0;
  /* Called at the top of composeSections, so "the first two" always means the
     first two panels of the report being built now, however many reports the
     member has already looked at in this session. */
  function resetSections() { secCount = 0; }
  function sec(title, html) {
    var body = String(html == null ? '' : html);
    var single = /^\s*<div class="mcr-note"/.test(body) &&
                 body.indexOf('mcr-note') === body.lastIndexOf('mcr-note');
    var open = secCount < SEC_OPEN ? ' open' : '';
    secCount += 1;
    return '<details' + open + ' class="mcr-card' + (single ? ' mcr-card--empty' : '') + '">' +
      '<summary class="mcr-card-t">' + title + '<span class="mcr-card-x" aria-hidden="true"></span></summary>' +
      body + '</details>';
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
      if (sd.productCategories && sd.productCategories.length) s.productCategories = sd.productCategories;
      if (sd.frameworks && sd.frameworks.length) s.frameworks = sd.frameworks;
      if (sd.specialities && sd.specialities.length) s.specialities = sd.specialities;
      if (sd.repsWatch) s.repsWatch = sd.repsWatch;
      /* Leadership and partnerships (19/08/2026) — same rule as every field
         above: the seed is human-owned, the nightly index rebuild never
         overwrites it, so the seed's copy wins and is the durable route. An
         alert-only write (the 692d14a workaround) never reaches this merge
         and is exactly the trap that migration replaced. */
      if (sd.leadership) s.leadership = sd.leadership;
      if (sd.partnerships && sd.partnerships.length) s.partnerships = sd.partnerships;
      if (sd.frameworkTiming) s.frameworkTiming = sd.frameworkTiming;
      if (sd.background && sd.background.length) s.background = sd.background;
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
  function chip(text, tone, href, title) {
    var cls = 'mcr-chip' + (tone === 'gold' ? ' mcr-chip--gold' : '') + (tone === 'muted' ? ' mcr-chip--muted' : '');
    var titleAttr = title ? ' title="' + esc(title) + '"' : '';
    if (href) {
      return '<a class="' + cls + '" href="' + esc(href) + '"' + titleAttr + '>' + esc(text) + '</a>';
    }
    return '<span class="' + cls + '"' + titleAttr + '>' + esc(text) + '</span>';
  }

  function identity(s) {
    /* Image with monogram fallback — copied from supplier-search.js so the two
       tools cannot drift apart visually. */
    var _w = String(s.name || '').replace(/^the\s+/i, '').split(/[\s\-—,\.]+/).filter(Boolean);
    var inits = esc((/^[A-Za-z0-9]{2,4}$/.test(_w[0] || '') ? _w[0] : _w.slice(0, 2).map(function (w) { return w[0]; }).join('')).toUpperCase());
    var ph = '<div style="width:56px;height:56px;flex:0 0 56px;border-radius:10px;background:#efe9db;border:1px solid ' + LINE + ';display:flex;align-items:center;justify-content:center;font-weight:700;color:' + G + ';font-size:16px;">' + inits + '</div>';
    var thumb = s.image
      ? '<img src="' + esc(imgSrc(s.image)) + '" alt="" referrerpolicy="no-referrer" loading="lazy" style="width:56px;height:56px;flex:0 0 56px;border-radius:10px;object-fit:contain;background:#fff;border:1px solid ' + LINE + ';" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div style="display:none;width:56px;height:56px;flex:0 0 56px;border-radius:10px;background:#efe9db;border:1px solid ' + LINE + ';align-items:center;justify-content:center;font-weight:700;color:' + G + ';font-size:16px;">' + inits + '</div>'
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

  var MAX_DIFF_COMPETITORS = 24;

  /* Competitors, by product — added 21/08/2026, replacing "Same speciality,
     no shared framework" (Lou's call, same day). That panel matched on a
     speciality TAG; this matches on the Compare/Differentiator feed's own
     gated, comparison-locked `cat` — the identical rule the Compare Your
     Product tool uses to decide two products can be shown side by side.
     Same source, same rule, no new claim invented for this page.

     Unlike every other competitor panel on this report, THIS ONE LINKS OUT
     TO THE COMPETITOR'S OWN WEBSITE, not to their Hub report — Lou's
     explicit instruction (21/08/2026): "the company list and the product
     name". The link target is the exact source URL the differentiator
     record was read from (data/differentiator.json `sources[].url`), never
     a guessed or constructed URL, per root rule 16 — a fact whose link
     cannot be produced is not published, so a row with no source URL and
     no domain is dropped rather than shown unlinked. */
  function productCompetitorsBlock(s, ctx) {
    var D = ctx.diff;
    if (!D || !D.bySupplierKey) {
      return gap('Not built for this view — the Compare/Differentiator product feed was unreachable.');
    }
    var mine = D.bySupplierKey[coKey(s.name)] || [];
    if (!mine.length) {
      (s.aliases || []).forEach(function (a) {
        var k = coKey(a);
        if (k && D.bySupplierKey[k]) mine = mine.concat(D.bySupplierKey[k]);
      });
    }
    if (!mine.length) {
      return gap('Not captured for this company yet — no product on the Compare/Differentiator feed carries a gated category for ' + esc(s.name) + '.');
    }

    var myCats = {}, catOrder = [];
    mine.forEach(function (p) {
      if (!myCats[p.cat]) { myCats[p.cat] = 1; catOrder.push(p.cat); }
    });

    var body = '', anyShown = 0;
    catOrder.sort(cmpName).forEach(function (cat) {
      var field = (D.byCat[cat] || []).filter(function (p) { return coKey(p.supplier) !== coKey(s.name); });
      if (!field.length) return;

      /* Group the competing field by company, so one competitor with three
         products in this category is one row, not three. */
      var byCo = {}, coOrder = [];
      field.forEach(function (p) {
        var k = coKey(p.supplier);
        if (!byCo[k]) { byCo[k] = { supplier: p.supplier, domain: p.domain, products: [], url: '' }; coOrder.push(k); }
        byCo[k].products.push(p.name);
        if (!byCo[k].url) {
          var src = (p.sources || [])[0];
          byCo[k].url = (src && src.url) || (p.domain ? 'https://' + p.domain : '');
        }
      });
      /* A row that can carry no link at all — no source URL and no domain
         — is dropped, not shown as plain text: this panel's entire point is
         the outbound link, so a name with nowhere to send a rep is not the
         claim this panel makes. */
      var rows = coOrder.map(function (k) { return byCo[k]; }).filter(function (c) { return !!c.url; });
      if (!rows.length) return;
      rows.sort(function (a, b) { return cmpName(a.supplier, b.supplier); });
      anyShown++;

      var myNames = mine.filter(function (p) { return p.cat === cat; }).map(function (p) { return p.name; });
      var shown = rows.slice(0, MAX_DIFF_COMPETITORS);

      body += '<div style="margin:0 0 12px;border:1px solid ' + LINE + ';border-radius:10px;padding:12px 14px;background:' + SOFT + ';page-break-inside:avoid;break-inside:avoid;">' +
        '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + esc(catLabel(cat)) + '</div>' +
        '<div style="font-size:12px;color:' + DIM + ';margin:4px 0 9px;line-height:1.6;">' + esc(s.name) + '&rsquo;s own product(s) here: ' + myNames.map(esc).join(', ') +
        ' &middot; ' + rows.length + ' other supplier(s) with a product in this same category' +
        (rows.length > shown.length ? (', showing the first ' + shown.length + ' alphabetically') : '') + '.</div>' +
        shown.map(function (c) {
          return '<div style="padding:6px 0;border-bottom:1px solid #f0ece3;font-size:13px;line-height:1.5;">' +
            '<a href="' + esc(c.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:700;">' + esc(c.supplier) + ' &#8599;</a>' +
            '<br><span style="color:' + DIM + ';font-size:12px;">' + c.products.slice(0, 6).map(esc).join(', ') +
            (c.products.length > 6 ? ' &middot; +' + (c.products.length - 6) + ' more' : '') + '</span>' +
            '</div>';
        }).join('') +
        '</div>';
    });

    if (!anyShown) {
      return gap(esc(s.name) + '&rsquo;s own category/categories on the Compare feed carry no other supplier with a linkable product yet.');
    }
    return rule('Every company below has at least one product recorded in the <b>same comparison-locked category</b> as ' + esc(s.name) + ' on the Compare/Differentiator feed — the identical rule the Compare Your Product tool uses, never a speciality guess. Each name links to the exact page its product was read from, or the company&rsquo;s own site where no product-page URL was recorded. A category with no other linkable supplier is not shown.') + body;
  }

  /* differentiator.json's `cat` is a machine key ("continence:ic"), never
     shown verbatim. The human label lives in
     data/differentiator-category-map.json, a fetch this page does not make
     (it would be an eleventh network call for one heading string) — so this
     is a readable rendering of the key itself, not a looked-up label. Not a
     fabricated name: every word in it comes from the key this row was
     actually filed under. */
  function catLabel(cat) {
    return String(cat || '').split(':').map(function (part) {
      return part.replace(/[-_]/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    }).join(' – ');
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
    if (deep) bits.push((deep.products || []).length + ' product(s) verified against the company’s own website' + (deep.verified ? ' (verified ' + esc(deep.verified) + ')' : ''));
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
          /* NPC -> NHS Supply Chain catalogue entry.
             RULE: the catalogue item page is https://pilot.supplychain.nhs.uk/product/<NPC>,
             the NPC used verbatim as the final path segment. Nothing else is derived from
             the code: the NPC prefix is NOT the eClass code (GCC611 sits under eClass GPC),
             so category, framework and supplier are never inferred from it here.
             PROVED 18/08/2026 against the live catalogue, which is browsable without a login.
             Seven real NPCs taken from the feed the table renders (data/nhssc-cache.json,
             whose own _meta.source is pilot.supplychain.nhs.uk) were loaded in a browser and
             the rendered page checked to name that exact product: HHH85203, FCP85802, GCC611,
             ECA85001, KBD4107, FGE378, GHB12442. Status alone is worthless as proof here —
             the app is client-rendered and returns HTTP 200 for any string, including the
             control code ZZZ99999, which renders an empty page with no product on it.
             Only codes present in the catalogue feed are linked, so no invented code is
             ever turned into a URL. The code stays visible as the link text, so the
             printable pack still reads correctly on paper. */
          var npcUrl = it.npc ? 'https://pilot.supplychain.nhs.uk/product/' + encodeURIComponent(it.npc) : '';
          var npcCell = npcUrl
            ? '<a href="' + esc(npcUrl) + '" target="_blank" rel="noopener" title="Open this line in the NHS Supply Chain catalogue" style="color:' + G + ';font-weight:600;">' + esc(it.npc) + '</a>'
            : esc(it.npc);
          return '<tr>' +
            '<td style="padding:9px 14px 9px 0;border-bottom:1px solid #f0ece3;font-size:12.5px;color:#37485a;">' + esc(it.desc) + '</td>' +
            '<td style="padding:9px 14px 9px 0;border-bottom:1px solid #f0ece3;font-size:12px;color:' + G + ';font-weight:600;white-space:nowrap;">' + npcCell + '</td>' +
            '<td style="padding:9px 14px 9px 0;border-bottom:1px solid #f0ece3;font-size:12px;color:' + DIM + ';white-space:nowrap;">' + esc(it.pack) + '</td>' +
            '</tr>';
        }).join('');
        return '<div style="margin:0 0 10px;border:1px solid ' + LINE + ';border-radius:8px;background:#fff;overflow:hidden;">' +
          '<div style="padding:7px 10px;background:' + SOFT + ';font-size:12.5px;font-weight:700;color:' + INK + ';border-bottom:1px solid ' + LINE + ';">' +
          esc(fam) + ' <span style="font-weight:400;color:' + DIM + ';">&middot; ' + fams[fam].length + ' line(s)</span></div>' +
          '<div class="mcr-scroll"><table style="border-collapse:collapse;width:100%;min-width:460px;">' +
          '<tr><th style="text-align:left;padding:9px 14px 9px 0;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">CATALOGUE DESCRIPTION</th>' +
          '<th style="text-align:left;padding:9px 14px 9px 0;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">NPC</th>' +
          '<th style="text-align:left;padding:9px 14px 9px 0;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">PACK</th></tr>' +
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
      // Product NAMES, not just division counts. Until 25/08/2026 this block
      // printed "Uncategorised · 1925 product(s)" and nothing else — a true
      // count with no product a rep could actually read. Lou's instruction,
      // 25/08/2026: when there is no company-filed category to group by,
      // show the products themselves rather than a bare number. Applies to
      // every division, not only the flat/`hasDivisions:false` case, because
      // a named division with an unlisted 300 products is the same gap in
      // miniature.
      var byDiv = {};
      (deep.products || []).forEach(function (p) {
        (byDiv[p.division] = byDiv[p.division] || []).push(p.n);
      });
      var flatRange = deep.hasDivisions === false;
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">' +
        (flatRange ? 'Full verified range — no company-filed category' : 'Full verified range, by the company’s own divisions') +
        '</div>' +
        (deep.filingRule ? '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 6px;">' + esc(deep.filingRule) + '</div>' : '') +
        deep.divisions.map(function (d) {
          var names = (byDiv[d.name] || []).slice().sort(function (a, b) { return a.localeCompare(b); });
          var label = (flatRange && d.name === 'Uncategorised') ? 'All products' : d.name;
          return '<div style="padding:6px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b style="color:' + INK + ';">' + esc(label) + '</b>' +
            ' <span style="color:' + DIM + ';">· ' + d.products + ' product(s)' +
            (d.specialities && d.specialities.length ? ' · ' + d.specialities.map(esc).join(', ') : '') + '</span>' +
            (names.length ? '<div class="mcr-scroll" style="max-height:190px;overflow-y:auto;margin:6px 0 2px;padding:8px 10px;border:1px solid ' + LINE + ';border-radius:6px;background:#fff;font-size:12px;color:' + DIM + ';line-height:1.7;">' +
              names.map(esc).join(' &middot; ') + '</div>' : '') +
            '</div>';
        }).join('') +
        (deep.notSold ? '<div style="font-size:11.5px;color:#8a4a58;margin:6px 0 0;"><b>Verified absences:</b> ' + esc(deep.notSold) + '</div>' : '');
    }

    if (s.products && s.products.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">Headline products (curated)</div>' +
        s.products.map(function (p) { return chip(typeof p === 'string' ? p : (p && p.n) || '', ''); }).join('');
    }

    /* Framework category labels — added 25/08/2026, backfilled by
       scripts/backfill_product_categories.py onto 772 suppliers. This is a
       DIFFERENT kind of fact from `products` above: `products` is a curated,
       branded/model-level product name; `productCategories` is an NHS Supply
       Chain framework CATEGORY label a supplier was sourced against, not a
       product or brand name. Kept in its own labelled block with its own
       chip style (dashed, muted — see .mcr-chip--muted) so the two can never
       be read as one list, per root rule 14 (derived claims need a stated
       rule and can't masquerade as a directly-sourced fact). Each chip's
       title carries the framework it was captured from and the date, the
       same provenance pattern used for the NPC catalogue link above. */
    if (s.productCategories && s.productCategories.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:12px 0 4px;">NHS Supply Chain framework categories</div>' +
        '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 6px;">Category labels this supplier was sourced against on an NHS Supply Chain framework — not curated product names, and not the same claim as the headline products above. Hover a chip for its source framework and capture date.</div>' +
        s.productCategories.map(function (pc) {
          var cat = (pc && pc.category) || '';
          var src = (pc && pc.source) || {};
          var titleBits = [];
          if (src.frameworkName) titleBits.push(src.frameworkName);
          if (src.frameworkRef) titleBits.push('ref ' + src.frameworkRef);
          if (src.capturedOn) titleBits.push('captured ' + src.capturedOn);
          return chip(cat, 'muted', null, titleBits.join(' — '));
        }).join('');
    }

    /* Competitors, by product — added 21/08/2026 (Lou's call), replacing
       "Same speciality, no shared framework". Deliberately last inside this
       section. Gated on `body` already being non-empty: a company with no
       product presence recorded anywhere gets the single "No product or
       brand indexed" refusal below, not that message plus a second, equally
       empty "not captured" for competitors it cannot possibly have found. */
    if (body) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:16px 0 4px;">Also selling in this category</div>' +
        productCompetitorsBlock(s, ctx);
    }

    if (!body) {
      return sec('Products', gap('No product or brand indexed for this company yet — the range has not been captured, which is not the same as a company with no products.'));
    }

    /* The honest partial: headline chips alone are NOT a product listing. */
    if (!cr.items.length && !deep) {
      body += '<div style="font-size:11.5px;color:' + DIM + ';margin-top:8px;">The full listing for this company has not been captured yet: no catalogue match has been run and the company’s own website has not been verified. What is above is the curated headline set, not the range.</div>';
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
  /* Framework expiry runway. Audit item 4.1, built 18/08/2026.

     `fwEnded` answered one binary question — has this framework already ended.
     That is the least useful moment to find out. A rep needs to know that the
     framework carrying their range ends in six weeks while there is still time
     to do something about it: on 18/08/2026 four of the 122 live frameworks end
     within 90 days and 31 within a year, and one of those, Infusion Pumps, has
     a successor whose go-live is roughly ten months after the incumbent stops.

     THE RULE, printed in the panel so a reader can judge it (root rule 14).
     The runway is the difference between today and the `ends` date recorded on
     that framework's own NHS Supply Chain contract launch brief. Nothing else
     feeds it. It is not a prediction, it says nothing about whether a successor
     has been awarded, and it must never be read as one — the successor question
     is answered by the brief, not by arithmetic.

     THE EVIDENCE FLOOR. A date this cannot parse produces NO badge at all. It
     does not fall back to a guess and it does not silently render a wrong
     runway, because a confident "ENDS IN 3 WEEKS" computed from a misread date
     is worse than no badge. Dates are parsed explicitly rather than through
     Date.parse, whose handling of "31 August 2027" is implementation-defined
     and differs between engines; all 122 recorded end dates parse under the
     explicit reader, checked on 18/08/2026. */
  var FW_MONTHS = {
    january: 0, february: 1, march: 2, april: 3, may: 4, june: 5,
    july: 6, august: 7, september: 8, october: 9, november: 10, december: 11
  };
  function fwDate(ends) {
    if (!ends) return null;
    var t = String(ends).trim();
    /* "31 August 2027" and "31 Aug 2027", the shape every brief uses. */
    var m = t.match(/^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$/);
    if (m) {
      var mi = null, key = m[2].toLowerCase();
      Object.keys(FW_MONTHS).forEach(function (full) {
        if (full === key || full.slice(0, 3) === key) mi = FW_MONTHS[full];
      });
      if (mi === null) return null;
      return new Date(Number(m[3]), mi, Number(m[1]));
    }
    /* ISO, in case a future feed writes it that way. */
    var iso = t.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (iso) return new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]));
    return null;
  }
  function fwDaysLeft(ends) {
    var d = fwDate(ends);
    if (!d) return null;
    var now = new Date();
    now = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return Math.round((d - now) / 86400000);
  }
  /* One badge, four states. Beyond a year there is no badge: a framework
     running to 2029 is simply not news, and a badge on every row would make
     the four that matter invisible. */
  function fwEnded(ends) {
    var days = fwDaysLeft(ends);
    if (days === null) return '';
    var bg, bd, fg, label;
    if (days < 0) {
      bg = '#f2f2f2'; bd = '#dcdcdc'; fg = '#5b6675'; label = 'ENDED';
    } else if (days <= 90) {
      bg = '#fdecef'; bd = '#f0c4cc'; fg = '#b84a5c';
      label = days < 14
        ? 'ENDS IN ' + days + (days === 1 ? ' DAY' : ' DAYS')
        : 'ENDS IN ' + Math.round(days / 7) + ' WEEKS';
    } else if (days <= 365) {
      bg = '#fbf3e2'; bd = '#e7d8b3'; fg = '#7a5b14';
      label = 'ENDS IN ' + Math.round(days / 30.44) + ' MONTHS';
    } else {
      return '';
    }
    return ' <span style="background:' + bg + ';border:1px solid ' + bd + ';color:' + fg +
      ';font-size:10px;font-weight:700;letter-spacing:.06em;border-radius:99px;padding:1px 7px;white-space:nowrap;">' +
      label + '</span>';
  }

  function frameworks(s, ctx) {
    var hits = supplierFrameworks(s, ctx);
    var curated = (s.frameworks || []);

    if (!hits.length && !curated.length) {
      var emptyBody = gap('No NHS Supply Chain contract launch brief names this company, and nothing is curated for it. Plenty of ranges are sold direct, off framework, and NHS Supply Chain is only one buying route, so read this as "not named on the briefs captured so far", never as proof they hold no place anywhere.');
      /* frameworkTiming (19/08/2026) — where a company is on no framework, this
         names the one it would compete on and says why the timing explains the
         absence, rather than leaving "not on a framework" to be read as a
         quality signal. Renders inside this panel, never as a section of its
         own — it is timing context for the empty state above, not a listing. */
      var ft = s.frameworkTiming;
      if (ft && ft.framework) {
        emptyBody += '<div style="margin-top:12px;padding:10px 12px;border:1px dashed ' + LINE + ';border-radius:7px;font-size:13px;line-height:1.6;color:#37485a;">' +
          '<b style="color:' + INK + ';">Framework it would compete on:</b> ' + esc(ft.framework) +
          (ft.reference ? ' <span style="color:' + DIM + ';">(ref ' + esc(ft.reference) + ')</span>' : '') +
          (ft.term ? '<br>Term: ' + esc(ft.term) : '') +
          (ft.supplierCount ? ' <span style="color:' + DIM + ';">&middot; ' + esc(String(ft.supplierCount)) + ' suppliers</span>' : '') +
          (ft.companyIncorporated ? '<br>This company incorporated ' + esc(ft.companyIncorporated) : '') +
          (ft.note ? '<div style="margin-top:6px;font-size:12px;color:' + DIM + ';">' + esc(ft.note) + '</div>' : '') +
          (ft.url ? srcLine('<a href="' + esc(ft.url) + '" target="_blank" rel="noopener">' + esc(ft.source || 'contract launch brief') + ' &#8599;</a>') : '') +
          '</div>';
      }
      return sec('Frameworks', emptyBody);
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

      /* Two columns on a wide card (mcr-fw-grid, added 19/08/2026) — see the
         note beside it in STYLE. */
      body += '<div class="mcr-fw-grid">' + hits.map(function (h) {
        var f = h.fw;
        var lots = (f.supplierLots || {});
        var myLots = [];
        h.matched.forEach(function (m) { if (lots[m]) { myLots = myLots.concat(lots[m]); } });
        return '<div style="padding:9px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;line-height:1.55;">' +
          '<b>' + fwLinked(f.name, null, 'NHS Supply Chain') + '</b>' +
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
      }).join('') + '</div>';
    }

    if (curated.length) {
      body += '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';margin:14px 0 4px;">Also tracked by hand</div>' +
        '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 6px;">Tender-watch notes: re-tender values, award criteria and award dates, which the launch briefs do not carry. Curated, not read from a brief.</div>' +
        '<div class="mcr-fw-grid">' + curated.map(function (f) {
          return '<div style="padding:8px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;line-height:1.55;"><b>' + fwLinked(f.name, f.key, '') + '</b>' +
            (f.value ? ' <span style="color:' + GREEN + ';font-weight:700;">' + esc(f.value) + '</span>' : '') +
            (f.dates ? ' <span style="color:' + DIM + ';">&middot; ' + esc(f.dates) + '</span>' : '') +
            (f.note ? '<br><span style="color:#37485a;font-size:12.5px;">' + esc(f.note) + '</span>' : '') + '</div>';
        }).join('') + '</div>';
    }
    return sec('Frameworks', body);
  }

  /* ---------------------------------------------------------------------
     PENDING FRAMEWORK AWARDS — read from Find a Tender, NOT from NHS Supply
     Chain's own brief (data/pending-awards.json, scripts/refresh_pending_
     awards.py). Deliberately a SEPARATE panel from Frameworks above: an award
     notice is public months before NHSSC publishes its own brief for it, and
     the Frameworks panel's evidence floor is right to wait for that brief —
     so this panel exists to say "awarded, not yet on NHSSC's own page" rather
     than either overstating the Frameworks panel's source or leaving members
     unable to see a real, sourced award. It renders ONLY while both are true;
     the moment NHSSC's own brief lands this panel retires itself on the next
     data refresh, and the Frameworks panel above is what to trust from then.
     Added 25/08/2026 after Lou flagged the Intravenous Cannula and Associated
     Products award (starts 01/04/2027) missing from Mediq Healthcare UK's
     report despite being live on the Hub's Live Desk.
     --------------------------------------------------------------------- */
  function pendingAwardsFor(s, ctx) {
    var doc = ctx.pending;
    if (!doc || !doc.companies) return [];
    return doc.companies[s.name] || [];
  }

  function pendingAwardRow(a, sub) {
    var cs = uk(a.contractStart), ce = uk(a.contractEnd), cx = uk(a.contractExtendedEnd);
    var term = cs ? ('starts ' + esc(cs) + (ce ? ' to ' + esc(ce) : '') +
      (cx && cx !== ce ? ' (extension option to ' + esc(cx) + ')' : '')) : '';
    var matchedAs = (a.matchedAs && a.matchedAs[sub.name]) || '';
    return '<div style="padding:9px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;line-height:1.55;">' +
      '<b>' + esc(a.title) + '</b> ' +
      '<span style="background:#fbf3e2;border:1px solid #e7d8b3;color:#7a5b14;font-size:10px;font-weight:700;letter-spacing:.06em;border-radius:99px;padding:1px 7px;white-space:nowrap;">AWARDED &middot; NOT YET ON NHSSC&rsquo;S OWN BRIEF</span>' +
      '<br><span style="font-size:12.5px;color:#37485a;">' + esc(a.buyer || 'buyer not named') +
      (term ? ' &middot; ' + term : '') +
      (a.awardDate ? ' &middot; awarded ' + esc(uk(a.awardDate)) : '') + '</span>' +
      (matchedAs ? '<br><span style="font-size:12.5px;color:' + DIM + ';">named on the notice as &ldquo;' + esc(matchedAs) + '&rdquo;</span>' : '') +
      '<br><span style="font-size:12.5px;color:' + DIM + ';">' +
      (a.noticeSuppliers ? a.noticeSuppliers.length + ' supplier(s) named on the award notice' : '') +
      ' &middot; <a href="' + esc(a.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">Find a Tender notice &#8599;</a></span>' +
      '</div>';
  }

  function pendingFrameworkAwards(sub, ctx) {
    var rows = pendingAwardsFor(sub, ctx);
    if (!ctx.pending || !rows.length) return '';
    var body = rule('This company is named on an NHS Supply Chain framework award notice on Find a Tender, but NHS Supply Chain has not yet published its OWN contract launch brief for it — so it cannot appear in the Frameworks panel above, which is deliberately scoped to that brief alone (root rule 16). ' +
      esc(ctx.pending.rule || '') +
      '<br><br><b>How this company was identified:</b> ' + esc(ctx.pending.matchRule || ''));
    body += rows.map(function (a) { return pendingAwardRow(a, sub); }).join('');
    return sec('Pending framework award' + (rows.length > 1 ? 's' : ''), body);
  }

  function alerts(s) {
    var raw = s.alerts || [];
    if (!raw.length) {
      return sec('Alerts &amp; recalls', good('No current alert indexed for this company.'));
    }
    var all = raw.map(alertShape);
    /* Recalls before curated notes. A recall is a dated safety event a rep may
       have to answer for on a visit; a note is background. Both filters are
       stable, so the seed's own order survives inside each group and an entry
       with no date is never moved relative to its neighbours — no sort on date
       is attempted, because 170 entries hold no date at all and any date sort
       would have to invent a position for them. */
    var ordered = all.filter(function (n) { return n.recall; })
      .concat(all.filter(function (n) { return !n.recall; }));
    var unsourced = all.filter(function (n) { return !n.url; }).length;
    var allQuiet = unsourced === all.length;
    var body = ordered.map(function (n) { return alertItem(n, allQuiet); }).join('');
    if (unsourced) {
      body += gap(allQuiet
        ? (all.length === 1
            ? 'This entry carries no source link, so treat it as a prompt to check rather than as a corroborated fact.'
            : 'None of these ' + all.length + ' entries carries a source link, so treat them as prompts to check rather than as corroborated facts.')
        : unsourced + ' of these ' + all.length + ' entries carry no source link and are shown on a dashed edge. Treat those as prompts to check rather than as corroborated facts.');
    }
    return sec('Alerts &amp; recalls', body);
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
        return !!coResolve(n, ctx);
      }).length;
      body += '<div style="margin:0 0 12px;border:1px solid ' + LINE + ';border-radius:10px;padding:12px 14px;background:' + SOFT + ';page-break-inside:avoid;break-inside:avoid;-webkit-print-color-adjust:exact;print-color-adjust:exact;">' +
        '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + fwLinked(grp.name, null, 'NHS Supply Chain') + '</div>' +
        '<div style="font-size:12px;color:' + DIM + ';margin:4px 0 9px;line-height:1.6;">' + grp.others.length +
        ' other supplier(s) on this framework &middot; ' + grp.total + ' in total, including ' + esc(sub.name) + '.' +
        (grp.reference ? ' &middot; ref ' + esc(grp.reference) : '') +
        (grp.ends ? ' &middot; runs to ' + esc(grp.ends) : '') +
        ' &middot; <a href="' + esc(grp.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">brief &#8599;</a></div>' +
        '<div>' + grp.others.map(function (n) {
          var lots = grp.lots && grp.lots[n];
          var hub = coResolve(n, ctx);
          /* Gold already meant "this Hub holds a profile"; that is now also
             exactly the set of chips that open one. The brief sometimes names
             a group's other trading entity, which resolves back to the company
             being read — no self-link, so that chip stays a plain chip. */
          var href = (hub && hub.name !== sub.name) ? coHref(hub.name) : '';
          return chip(n + (lots && lots.length ? ' \u00b7 ' + lots.join(', ') : ''), hub ? 'gold' : '', href);
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
        '<b style="color:' + INK + ';">' + coName(r.name, ctx, sub.name) + '</b>' +
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
  /* Three tiers, not two: probable < corroborated < confirmed. Figures and
     the confirmed-only field filing profile read matchConfidence by NAME,
     always === 'confirmed' — never a negated comparison against 'probable'.
     A negated-comparison guard reads true for 'corroborated' too, which is
     exactly how a new tier would silently become 'confirmed' by accident.
     Added 03/09/2026 alongside the 'corroborated' tier. See test T1. */
  function isConfirmed(rec) {
    return String((rec && rec.matchConfidence) || '').toLowerCase() === 'confirmed';
  }
  function isCorroborated(rec) {
    return String((rec && rec.matchConfidence) || '').toLowerCase() === 'corroborated';
  }

  /* Tile, not a table row (changed 19/08/2026 — see mcr-facts in STYLE). A
     value over ~34 characters of visible text is judged too long for a
     compact tile and spans the full row instead; that threshold is on the
     value's own length so it holds for whichever facts a given company
     happens to have, rather than a fixed list of "these labels are long". */
  function fact(label, value, forceWide) {
    var plain = String(value).replace(/<[^>]+>/g, '');
    var wide = forceWide || plain.length > 34;
    return '<div class="mcr-fact' + (wide ? ' mcr-fact--wide' : '') + '">' +
      '<div class="mcr-fact-k">' + label + '</div>' +
      '<div class="mcr-fact-v">' + value + '</div></div>';
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
        esc(fin.coverage || 'a small set of companies') + '.' +
        ' The full register fetch runs when the Companies House API key arrives — absence here is a coverage gap, not a company without filings.'));
    }

    /* A record with no company number carries no identity at all — the match
       was cleared by hand as the wrong company (data/company-match-overrides.json).
       Return the empty state BEFORE the caveat box, which would otherwise say
       "register facts are shown for orientation" directly above "the record
       carries no register facts". Added 03/09/2026 with the 35 identity clears:
       the identity rows below render unconditionally, so until those records
       were cleared a wrong company name and number published to members while
       only the figures were withheld. */
    if (!rec.companyNumber && !rec.registeredName) {
      return sec(TITLE, gap('No company is attached to this supplier. A previous match was cleared as the wrong company, and nothing is shown here until a match is confirmed against two independent sources. This is a deliberate blank, not a coverage gap.'));
    }

    var probable = isProbable(rec);
    var confirmed = isConfirmed(rec);
    var corroborated = isCorroborated(rec);
    var rows = '';
    if (rec.registeredName) {
      /* The register's own previous-name history, bracketed after the current
         name so a member searching an old name recognises the company. Added
         03/09/2026 at Lou's request: Healthcare 25 Ltd's registered previous
         name is GEMINI SURGICAL UK LTD, and a rep who knows the old name found
         nothing.

         WORDING MATTERS. Companies House records a change of registered NAME on
         one company number. That is all it records. It does NOT tell you the
         business was not sold, split or bought — so this says "formerly
         registered as", never "formerly known as" or "was". The Gemini Surgical
         rename-versus-sale question is still open and this line must not
         pre-empt it. */
      var former = '';
      if (rec.previousNames && rec.previousNames.length) {
        former = ' <span style="color:' + DIM + ';font-weight:400;">(formerly registered as ' +
          rec.previousNames.slice(0, 3).map(function (p) {
            return esc(p.name) + (p.to ? ' until ' + esc(dateUK(p.to)) : '');
          }).join('; ') +
          (rec.previousNames.length > 3 ? '; and ' + (rec.previousNames.length - 3) + ' earlier' : '') +
          ')</span>';
      }
      rows += fact('Registered name', '<b>' + esc(rec.registeredName) + '</b>' +
        (rec.companyNumber ? ' &middot; ' + esc(rec.companyNumber) : '') + former, true);
    }
    if (rec.status) rows += fact('Status', esc(rec.status));
    if (rec.incorporated) rows += fact('Incorporated', esc(dateUK(rec.incorporated)));
    if (rec.registeredOffice) rows += fact('Registered office', esc(rec.registeredOffice), true);
    if (rec.sic && rec.sic.length) rows += fact('SIC', rec.sic.map(esc).join(', '));
    if (rec.accountsFilingVerbatim) rows += fact('Latest accounts', esc(rec.accountsFilingVerbatim), true);

    /* Turnover has three honest states and they must not blur:
       a figure (with its made-up-to date), disclosed-but-not-extracted, or
       not disclosed at all (legally permitted below the small thresholds).
       Gated on `confirmed` BY NAME, never on a negated probable check — a corroborated match
       is not confirmed by name and must carry no figure either. See test T1. */
    if (confirmed) {
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
    } else if (corroborated) {
      /* The labelled basis line, ABOVE the register facts, per root rule 14 —
         a reader must be able to judge the attachment before reading it as
         fact. Never a footnote. `corroboratedBy` is written by
         scripts/refresh_companies_house.py's independent_corroborator() and
         names the ONE independent source that earned this tier (never a
         Companies House name search, an aggregator, a shared group, or a
         shared mass-registration address). */
      body += '<div style="margin:0 0 9px;padding:8px 11px;background:#f2ede0;border-left:3px solid #8a6d3b;border-radius:0 7px 7px 0;font-size:12px;color:#4d3f24;line-height:1.55;">' +
        '<b>CORROBORATED MATCH &mdash; NOT CONFIRMED BY NAME.</b> These Companies House records are shown for ' +
        esc(rec.registeredName || 'this company') + (rec.companyNumber ? ' (' + esc(rec.companyNumber) + ')' : '') +
        '. The registered name and this supplier’s trading name share no distinguishing word, so the match is not confirmed on the name. ' +
        'It is attached because ' + esc(rec.corroboratedBy || 'a curator recorded an independent corroborator') + '. ' +
        'Register facts are Companies House’s; the attachment to this supplier is ours. No figure is carried and this company is excluded from the field filing profile below.</div>';
    } else if (rec.matchedOn) {
      body += '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 8px;">Matched on: ' + esc(rec.matchedOn) + '</div>';
    }
    body += rows ? ('<div class="mcr-facts">' + rows + '</div>') : gap('The record carries no register facts.');
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

  /* ---------------------------------------------------------------------
     COMPANY BACKGROUND. Added 19/08/2026.

     WHY THIS EXISTS. `alerts[]` is one bucket holding two unlike things: a
     dated MHRA safety event a rep may have to answer for on a visit, and
     curated background prose about how a company sells. alertShape() sorts
     recalls above notes, but they still render under one heading — so
     "Alerts & recalls" was where a company's mission statement, its training
     framework and its catalogue structure ended up, which reads to a member
     as though the company has six safety problems. Background belongs in
     Part 1 with the rest of who they are.

     Each entry keeps its own source and read date. An entry with no source
     is drawn on the same dashed edge the alerts panel uses for honest
     incompleteness and says so — thin background is common and must be
     visibly thin, never quietly dressed as corroborated.
     --------------------------------------------------------------------- */
  function panelBackground(s) {
    var TITLE = 'Company background';
    var rows = s.background || [];
    if (!rows.length) {
      return sec(TITLE, gap('Not captured for this company yet.'));
    }
    var unsourced = rows.filter(function (r) { return !r.url; }).length;
    var body = rows.map(function (r) {
      var thin = !r.url;
      return '<div style="padding:10px 12px;margin:0 0 9px;border-radius:7px;' +
        (thin ? 'border:1px dashed ' + LINE + ';background:' + SOFT + ';' : 'border-bottom:1px solid #f0ece3;border-radius:0;padding:9px 0;') + '">' +
        (r.heading ? '<div style="font-size:12.5px;font-weight:700;color:' + INK + ';letter-spacing:.02em;margin:0 0 4px;">' + esc(r.heading) + '</div>' : '') +
        '<div style="font-size:13.5px;color:#37485a;line-height:1.65;">' + esc(r.text) + '</div>' +
        (r.url
          ? srcLine('<a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.source || 'source') + ' &#8599;</a>' +
              (r.readOn ? ' &middot; ' + asOf('read ' + esc(dateUK(r.readOn))) : ''))
          : '<div style="margin-top:5px;font-size:11.5px;color:' + DIM + ';">No source link held for this entry &mdash; treat it as a prompt to check, not as a corroborated fact.</div>') +
        '</div>';
    }).join('');
    if (unsourced) {
      body += gap(unsourced === rows.length
        ? 'None of these entries carries a source link, so treat them as prompts to check rather than as corroborated facts.'
        : unsourced + ' of these ' + rows.length + ' entries carry no source link and are shown on a dashed edge.');
    }
    return sec(TITLE, body);
  }

  /* ---------------------------------------------------------------------
     LEADERSHIP. Added 19/08/2026 so the Jeenie founder/prior-experience
     material (put in alerts[] by mistake in 692d14a, migrated here in the
     same commit that adds this panel) has structure instead of prose.
     Renders in Part 1, after Company information.

     Two kinds of fact, kept visibly separate: an OFFICER STATUS line, which
     is a Companies House register fact (or its absence — a person the
     register does not carry is an employee, not an officer, and the panel
     says so rather than leaving that to be inferred); and CLAIMS, each the
     named person's own published account of their prior experience, each
     linked to its own source. A claim with no source url does not reach
     this panel — verify.py refuses to publish one.
     --------------------------------------------------------------------- */
  function panelLeadership(s) {
    var TITLE = 'Leadership';
    var L = s.leadership;
    if (!L || !L.people || !L.people.length) {
      return sec(TITLE, gap('Not captured for this company yet.'));
    }
    var body = rule('Officer status — director or sole director, with an appointed date — is read from the <b>Companies House public register</b>. A person this record names who does not appear on that register is stated as an employee, never as an officer. Prior-experience claims are the named person&rsquo;s own published account, each linked to its own source; they are reported as claims, not independently verified beyond that the person made them.');
    body += L.people.map(function (p) {
      var badge = p.officer
        ? '<span style="color:' + GREEN + ';font-weight:700;">Companies House officer</span>' +
          (p.appointed ? ' <span style="color:' + DIM + ';">&middot; appointed ' + esc(p.appointed) + '</span>' : '')
        : '<span style="color:' + DIM + ';">Not on the Companies House register &mdash; an employee, not an officer</span>';
      var claims = (p.claims || []).map(function (c) {
        return '<div style="padding:6px 0 0;font-size:12.5px;color:#37485a;line-height:1.55;">' + esc(c.text) +
          (c.url ? ' <a href="' + esc(c.url) + '" target="_blank" rel="noopener" style="color:' + G + ';font-weight:600;">' + esc(c.source || 'source') + ' &#8599;</a>' : '') +
          '</div>';
      }).join('');
      var note = p.note ? '<div style="margin-top:6px;font-size:11.5px;color:' + DIM + ';line-height:1.5;">' + esc(p.note) + '</div>' : '';
      return '<div style="padding:10px 0;border-bottom:1px solid #f0ece3;">' +
        '<b style="color:' + INK + ';font-size:14px;">' + esc(p.name) + '</b>' +
        (p.role ? ' <span style="color:' + DIM + ';">&middot; ' + esc(p.role) + '</span>' : '') +
        '<br>' + badge + claims + note + '</div>';
    }).join('');
    if (L.source) {
      body += srcLine(esc(L.source) + (L.readOn ? ' &middot; ' + asOf('read ' + esc(dateUK(L.readOn))) : ''));
    }
    return sec(TITLE, body);
  }

  /* ---------------------------------------------------------------------
     PARTNERSHIPS. Added 19/08/2026, same migration as leadership above.
     Renders in Part 2, before Frameworks.

     `confidence` is a first-class, always-shown state — never inferred from
     whether a url is present. The Jeenie/Arjo entry is the reason this
     exists: both parties state the arrangement, it appears on neither of
     their own websites, and it must never be allowed to read as a verified
     commercial agreement just because it has a source link. A row with no
     source url does not reach this panel — verify.py refuses to publish one.
     --------------------------------------------------------------------- */
  function panelPartnerships(s) {
    var TITLE = 'Partnerships';
    var rows = s.partnerships || [];
    if (!rows.length) {
      return sec(TITLE, gap('Not captured for this company yet.'));
    }
    var body = rule('Every row is a dated distribution or partnership arrangement, carrying the confidence the arrangement itself supports — <b>confirmed</b> where an independent source or both parties&rsquo; own primary materials state it as a contract, or <b>claimed by the parties, not independently confirmed</b> where it is stated by the parties but not otherwise evidenced. A claimed arrangement is never rendered as a verified commercial agreement.');
    body += rows.map(function (p) {
      var confirmed = String(p.confidence || '').toLowerCase() === 'confirmed';
      var badge = confirmed
        ? '<span style="background:#eaf6ea;border:1px solid #bfe3bf;color:' + GREEN + ';font-size:10px;font-weight:700;letter-spacing:.06em;border-radius:99px;padding:1px 7px;white-space:nowrap;">CONFIRMED</span>'
        : '<span style="background:#f7ecdc;border:1px solid #e7d8b3;color:#7a5b14;font-size:10px;font-weight:700;letter-spacing:.06em;border-radius:99px;padding:1px 7px;white-space:nowrap;">' + esc(p.confidence || 'CLAIMED BY THE PARTIES, NOT INDEPENDENTLY CONFIRMED') + '</span>';
      return '<div style="padding:9px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;line-height:1.55;">' +
        '<b style="color:' + INK + ';">' + esc(p.with) + '</b> ' + badge +
        (p.date ? ' <span style="color:' + DIM + ';">&middot; ' + esc(p.date) + '</span>' : '') +
        (p.covers ? '<br><span style="color:#37485a;">' + esc(p.covers) + '</span>' : '') +
        (p.territory ? ' <span style="color:' + DIM + ';">&middot; ' + esc(p.territory) + '</span>' : '') +
        (p.note ? '<div style="margin-top:4px;font-size:12px;color:' + DIM + ';">' + esc(p.note) + '</div>' : '') +
        (p.url ? srcLine('<a href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(p.source || 'source') + ' &#8599;</a>') : '') +
        '</div>';
    }).join('');
    return sec(TITLE, body);
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
        /* Gated on `confirmed` BY NAME, never `!isProbable` — a corroborated
           match must not enter the confirmed-only field filing profile
           either. See test T1. */
        if (r && isConfirmed(r) && String(r.accountsCategory || '').trim()) {
          resolved.push({ name: n, rec: r });
        } else {
          unresolved.push({ name: n, rec: r });
        }
      });

      /* THE HALF-THE-FIELD FLOOR. resolved * 2 < total refuses the panel. */
      if (resolved.length * 2 < everyone.length) {
        body += '<div style="margin:0 0 12px;border:1px dashed #ded6c4;border-radius:10px;padding:12px 14px;background:#faf8f3;page-break-inside:avoid;break-inside:avoid;">' +
          '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + fwLinked(grp.name, null, 'NHS Supply Chain') + '</div>' +
          gap('Not shown: of the ' + everyone.length + ' suppliers on this framework, only ' + resolved.length +
            ' resolve to a confirmed Companies House record with an accounts filing. That is below half the field, and a size profile of under half a field misleads more than it informs. Unresolved: ' +
            unresolved.map(function (u) { return esc(u.name); }).join(', ') + '. Confirming identities is what fixes this; lowering the bar is not.') +
          '</div>';
        return;
      }
      rendered += 1;

      var rows = resolved.map(function (r) {
        var me = r.name === sub.name;
        return '<tr>' +
          '<td style="padding:9px 14px 9px 0;border-bottom:1px solid #f0ece3;font-size:12.5px;color:' + INK + ';' + (me ? 'font-weight:700;' : '') + '">' + coName(r.name, ctx, sub.name) + (me ? ' ◂' : '') + '</td>' +
          '<td style="padding:9px 14px 9px 0;border-bottom:1px solid #f0ece3;font-size:12.5px;color:#37485a;">' + esc(r.rec.accountsFilingVerbatim || r.rec.accountsCategory) + '</td>' +
          '<td style="padding:9px 14px 9px 0;border-bottom:1px solid #f0ece3;font-size:12px;color:' + DIM + ';white-space:nowrap;">' + esc(r.rec.incorporated ? ('inc. ' + r.rec.incorporated.slice(0, 4)) : '') + '</td>' +
          '</tr>';
      }).join('');

      body += '<div style="margin:0 0 12px;border:1px solid ' + LINE + ';border-radius:10px;padding:12px 14px;background:' + SOFT + ';page-break-inside:avoid;break-inside:avoid;-webkit-print-color-adjust:exact;print-color-adjust:exact;">' +
        '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + fwLinked(grp.name, null, 'NHS Supply Chain') + '</div>' +
        '<div style="font-size:12px;color:' + DIM + ';margin:4px 0 9px;line-height:1.6;">' + everyone.length + ' supplier(s) on this framework · ' +
        resolved.length + ' resolved to a confirmed filing · ' + unresolved.length + ' unresolved.</div>' +
        '<div class="mcr-scroll"><table style="border-collapse:collapse;width:100%;min-width:420px;">' +
        '<tr><th style="text-align:left;padding:9px 14px 9px 0;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">SUPPLIER</th>' +
        '<th style="text-align:left;padding:9px 14px 9px 0;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';">MOST RECENT ACCOUNTS FILING</th>' +
        '<th style="text-align:left;padding:9px 14px 9px 0;font-size:10.5px;letter-spacing:1px;color:' + DIM + ';border-bottom:1px solid ' + LINE + ';"></th></tr>' +
        rows + '</table></div>';

      if (unresolved.length) {
        body += '<div style="font-size:12px;color:' + DIM + ';margin-top:7px;">Unresolved, feeding nothing: ' +
          unresolved.map(function (u) {
            var why = u.rec ? (!isConfirmed(u.rec) ? 'identity not confirmed' : 'no accounts filing recorded') : 'no Companies House record fetched';
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
    return '<img src="' + esc(imgSrc(s.image)) + '" alt="" referrerpolicy="no-referrer" loading="lazy" ' +
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
      return sec('Divisions &amp; specialities', '<div style="font-size:11.5px;color:' + DIM + ';margin:0 0 11px;line-height:1.6;">The company’s own division structure, verified against the company’s own website' +
        (deep.verified ? ' on ' + esc(deep.verified) : '') + '; product counts come from the verified range at the bottom of this report.</div>' +
        '<div style="' + GRID + '">' + cards + '</div>');
    }
    if (s.specialities && s.specialities.length) {
      cards = s.specialities.map(function (sp) {
        return '<div style="' + CARD + '">' +
          '<div style="font-size:13.5px;font-weight:700;color:' + INK + ';line-height:1.35;">' + esc(sp) + '</div>' +
          '<div style="margin-top:7px;font-size:12px;color:' + DIM + ';line-height:1.6;">Recorded speciality · division-level product counts arrive once the company’s own website is verified.</div>' +
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

  /* Normalises all three accepted shapes onto one record. Absent keys come
     back as empty strings, never undefined, so alertItem() tests truthiness
     and never has to print a placeholder. */
  function alertShape(a) {
    var o = (a && typeof a === 'object') ? a : {};
    if (typeof a === 'string') o = { text: a };
    var title = String(o.title || '');
    return {
      recall: !!title,
      /* Curated alerts are typed at the data layer: "safety" (a recall, field
         safety notice or regulator action) or "supply" (delisted, suspended,
         discontinued, end-of-life, unavailable). Before that typing existed
         this panel was one bucket, and 272 of 383 curated entries in it were
         company background — so a genuine Class I recall sat in the same
         undifferentiated list as a note about a site move. An issue-derived
         alert carries no kind and is drawn exactly as it always was. */
      kind: String(o.kind || ''),
      date: String(o.date || ''),
      title: title,
      text: String(o.text || o.detail || ''),
      use: String(o.use || ''),
      url: String(o.url || ''),
      source: String(o.source || '')
    };
  }

  /* One drawing for every alert. An entry with no source still renders in
     full — thin data is the normal case here — but it is drawn in the same
     visual language the report already uses for honest incompleteness
     (.mcr-card--empty: dashed edge, ivory ground) and says so in a dim line,
     so a member can see at a glance what is corroborated. */
  function alertItem(n, quiet) {
    var sourced = !!n.url;
    var cls = 'mcr-alert' + (n.recall ? ' mcr-alert--recall' : '') +
              (sourced ? '' : ' mcr-alert--unsourced');
    var head = '';
    /* One word saying which kind of alert this is, so a recall and a delisting
       are not read as the same thing at a glance. */
    if (n.kind === 'safety' || n.kind === 'supply') {
      var safety = n.kind === 'safety';
      head += '<span style="background:' + (safety ? '#fdecef' : '#f7ecdc') +
        ';border:1px solid ' + (safety ? '#f0c4cc' : '#e7d8b3') +
        ';color:' + (safety ? '#b84a5c' : '#7a5b14') +
        ';font-size:10px;font-weight:700;letter-spacing:.06em;border-radius:99px;' +
        'padding:1px 7px;white-space:nowrap;margin-right:6px;">' +
        (safety ? 'SAFETY' : 'SUPPLY') + '</span>';
    }
    if (n.date) head += '<b class="mcr-alert-d">' + esc(n.date) + '</b>';
    if (n.title) head += (head ? ' — ' : '') + '<b>' + esc(n.title) + '</b>';
    var out = '<div class="' + cls + '">';
    if (head) out += head + (n.text ? '<br>' : '');
    if (n.text) out += '<span class="mcr-alert-x">' + esc(n.text) + '</span>';
    if (n.use) out += '<br><span class="mcr-alert-u">▸ ' + esc(n.use) + '</span>';
    if (sourced) {
      out += '<br><a href="' + esc(n.url) + '" target="_blank" rel="noopener">' +
        esc(n.source || 'source') + ' ↗</a>';
    } else if (n.source) {
      out += '<div class="mcr-note">Source given as ' + esc(n.source) + '. No link held.</div>';
    } else if (!quiet) {
      /* Suppressed when nothing in the panel is sourced: the panel's own line
         already says it once, and repeating it on every entry would read as a
         fault rather than as the ordinary state of a thin record. */
      out += '<div class="mcr-note">No source link held for this entry.</div>';
    }
    return out + '</div>';
  }

  /* ------------------------------------------------------------------
     LINKING A FRAMEWORK NAME TO THE HUB'S FRAMEWORK HUB.

     ANCHOR PROOF, established 18/08/2026, recorded here so nobody has to
     re-derive it:

     - The target page is WordPress page 678,
       /medical-sales-hub/frameworks/ ("Framework Hub"). A logged-out fetch
       returns HTTP 200 carrying the "This page is for Hub members" gate, so
       the page exists and is subscriber-gated. It is not empty.
     - No file in the repo's app/ directory renders that page; its markup is
       page content, read via the WordPress API for page 678.
     - Its anchors are assigned at runtime by the page's own inline anchor
       script (marker comment ETH-ANCHORS-FRAMEWORKS), which walks every h1
       and h2 and gives it an id from a fixed map: fw-nhssc, fw-sbs, fw-ccs,
       fw-noecpc, fw-hte, fw-nhssc-categories, fw-sbs-directory, fw-law,
       fw-start, fw-win, fw-downloads, fw-renewal. Anything unmapped falls
       back to sec- plus a slug of the heading.
     - Those headings are BUYING ORGANISATIONS and guidance sections. The page
       carries no heading, no row and no id for an individual framework: a
       search of the page content for framework names such as "Advanced Wound
       Care" finds only running prose, never a target. PER-FRAMEWORK ANCHORS
       DO NOT EXIST.

     So the deepest honest link is the section for the buying organisation the
     framework sits under, and a framework whose owning body cannot be named
     gets the plain page link. Nothing here invents an anchor.
     ------------------------------------------------------------------ */
  function fwHref(key, name, org) {
    var MAP = [
      ['NHS SUPPLY CHAIN', 'fw-nhssc'],
      ['SUPPLY CHAIN', 'fw-nhssc'],
      ['NHS SBS', 'fw-sbs'],
      ['SHARED BUSINESS SERVICES', 'fw-sbs'],
      ['CROWN COMMERCIAL', 'fw-ccs'],
      ['GOVERNMENT COMMERCIAL AGENCY', 'fw-ccs'],
      ['CCS', 'fw-ccs'],
      ['NOE CPC', 'fw-noecpc'],
      ['HEALTHTRUST EUROPE', 'fw-hte'],
      ['HEALTH TRUST EUROPE', 'fw-hte'],
      ['HTE', 'fw-hte']
    ];
    var PAGE = '/medical-sales-hub/frameworks/';
    var t = String(name || key || '').toUpperCase();
    if (!t.replace(/[^A-Z0-9]/g, '')) return null;
    var hay = (String(org || '').toUpperCase() + ' ' + t);
    for (var i = 0; i < MAP.length; i++) {
      if (new RegExp('\\b' + MAP[i][0] + '\\b').test(hay)) return PAGE + '#' + MAP[i][1];
    }
    return PAGE;
  }

  /* The framework name as it should be printed: escaped, and wrapped in an
     internal link when fwHref gives one. Same tab deliberately, this is a Hub
     page. Plain text when there is nothing sensible to link to. */
  function fwLinked(name, key, org) {
    var txt = esc(name);
    var href = fwHref(key || null, name, org || '');
    if (!href) return txt;
    return '<a href="' + href + '" style="color:inherit;text-decoration:underline;text-decoration-color:' + G + ';text-underline-offset:2px;">' + txt + '</a>';
  }

  /* ---------------------------------------------------------------------
     COMPANY CROSS-LINKS. A report names other companies in four places — the
     framework co-listing, the same-speciality list, the field filing profile
     and the chips built from them. Each of those names is a company a member
     may want to read next, and until now they had to scroll back and retype it.

     THE TARGET IS THE `?company=` DEEP LINK HANDLED AT THE BOTTOM OF boot().
     No second entry point was built for this: the link is the same page with a
     different query string, so the browser loads the page afresh, boot() runs
     again, and the name is resolved through find()/show() exactly as a typed
     name is. Nothing here can reach a company the picker itself could not.

     A NAME THAT DOES NOT RESOLVE IS DELIBERATELY LEFT AS PLAIN TEXT. The
     contract launch briefs name companies this Hub has never indexed; linking
     one would open the picker on a dead query, and "No match for …" under a
     link a member just clicked reads as a broken report rather than as an
     honestly unindexed company. Plain text is the correct output there.
     --------------------------------------------------------------------- */
  function coResolve(name, ctx) {
    if (!name || !ctx) return null;
    return ctx.byName[name] || (ctx.byKey ? ctx.byKey[coKey(name)] : null) || null;
  }

  function coHref(name) {
    return REPORT_URL + '?company=' + encodeURIComponent(String(name || ''));
  }

  /* Name as HTML: linked to its own report where the renderer can resolve it,
     plain text otherwise, and plain text for the company being read — a report
     that links to itself is a dead loop dressed up as a route out. */
  function coName(name, ctx, selfName, label) {
    var text = esc(label == null ? name : label);
    if (!name || name === selfName) return text;
    var rec = coResolve(name, ctx);
    if (!rec || rec.name === selfName) return text;
    return '<a class="mcr-colink" href="' + esc(coHref(rec.name)) + '">' + text + '</a>';
  }

  function composeSections(sub, ctx) {
    resetSections();
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
    h += panelBackground(sub);
    h += panelLeadership(sub);
    h += panelCompanyFacts(sub, ctx);
    h += ownershipBlock(sub);

    /* -- 2 · Growth, near the top by design ----------------------------- */
    h += growthChart(sub, ctx);

    /* -- 3 · Specialities / divisions as cards -------------------------- */
    h += part('2', 'What they sell, and how it reaches the NHS',
      'Clinical areas, NHS Supply Chain framework positions read from the buying organisation’s own contract launch briefs, and awards named on statutory notices.');
    h += divisionCards(sub, ctx);
    h += panelPartnerships(sub);
    h += frameworks(sub, ctx);
    h += pendingFrameworkAwards(sub, ctx);
    h += panelAwards(sub, ctx);
    h += repsWatch(sub);

    /* -- 4 · Competitors ------------------------------------------------ */
    h += part('3', 'The field around them <span style="font-size:10px;letter-spacing:1.6px;text-transform:uppercase;color:' + G + ';vertical-align:3px;">&nbsp;· derived</span>',
      'The panels in this part are <b>computed by this page</b>, not read from a source. Each prints the rule it was computed under and refuses to render on thin evidence. None ranks anyone, and none prints a market-share figure — the filing profile shows which statutory regime each confirmed supplier files under, which is the sourceable part of “how big are they”. Read the rule before you quote any of it.');
    var co = coListing(sub, ctx);
    h += panelCoListed(sub, ctx, co);
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
      'The long listing, deliberately last: catalogue-verified lines, items confirmed off catalogue, and the full own-site range where the company’s own website has been verified.');
    h += productListing(sub, ctx);

    return h;
  }

  function report(sub, ctx) {
    var h = '<article class="mcr-report" style="' + accentVars(sub) + '">';
    h += masthead(sub, ctx, null);
    h += '<div class="mcr-body">';

    /* Stage 5 entry point. The pack is the same composer rendered for
       print — it adds no claims, so the button lives on the card. */
    /* Two entry points, not one. "Take it into the meeting" is the rep already
       selling for this company; "interviewing here" is the candidate about to be
       interviewed BY it, which is a different job and was the reason members had
       to leave the Hub to prepare. The interview link carries the company name in
       ?company= so Interview Prep opens on the same record this report is showing,
       rather than making them find it again in a picker. Added 18/08/2026 (Lou). */
    h += '<div style="display:flex;justify-content:flex-end;align-items:center;gap:12px;margin:14px 0 0;flex-wrap:wrap;">' +
      '<span style="font-size:11.5px;color:' + DIM + ';">Take it into the meeting:</span>' +
      '<button id="mcrPack" class="mcr-btn">Download / print this report</button>' +
      '<span style="font-size:11.5px;color:' + DIM + ';">Interviewing here:</span>' +
      '<a class="mcr-btn" style="text-decoration:none;display:inline-block;" href="/medical-sales-hub/interview-prep/?company=' +
      encodeURIComponent(sub.name || '') + '">Prepare for an interview with ' + esc(sub.name || 'this company') + '</a></div>';

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
      return '<div style="font-size:12px;color:' + DIM + ';line-height:1.6;">Per-speciality sections need this company’s own website to be verified, which has not happened yet — the range above is the curated and catalogue-verified view. This is the same verification that built the GBUK tree and runs supplier by supplier.</div>';
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

    /* Every panel is stamped open before the pack is written. The pack is a
       document to be read end to end, on paper or in a PDF, where a collapsed
       panel is not a tidier page — it is a missing one. The regex only adds
       the attribute where it is absent, so the two panels that were already
       open are left alone. */
    inner = inner.replace(/<details(?! open)/g, '<details open');

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

  /* Packs runs of consecutive closed panels into a .mcr-toc-grid — added
     19/08/2026, the fix for the 23-closed-panels-in-a-column problem (see
     the note beside .mcr-toc-grid in STYLE). Runs on the live on-page DOM
     only, right after result.innerHTML is set in show(); the print pack
     builds its own HTML from composeSections() and forces every panel
     open before it does, so it never sees an unopened <details> to group
     and this function has nothing to do there.
     A run of exactly one closed panel is left where it is — grouping a
     single item into its own one-tile "grid" would just add a wrapper div
     for no visual gain, and it's cheaper to skip than to special-case. */
  function groupClosedPanels(root) {
    var body = root.querySelector('.mcr-body');
    if (!body) return;
    var kids = Array.prototype.slice.call(body.children);
    var i = 0;
    function isClosedPanel(el) {
      return el.tagName === 'DETAILS' && el.classList.contains('mcr-card') && !el.open;
    }
    while (i < kids.length) {
      if (isClosedPanel(kids[i])) {
        var run = [kids[i]];
        var j = i + 1;
        while (j < kids.length && isClosedPanel(kids[j])) { run.push(kids[j]); j++; }
        if (run.length > 1) {
          var grid = document.createElement('div');
          grid.className = 'mcr-toc-grid';
          body.insertBefore(grid, run[0]);
          run.forEach(function (node) { grid.appendChild(node); });
        }
        i = j;
      } else {
        i++;
      }
    }
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

  /* Differentiator/Compare feed, indexed two ways — added 21/08/2026.
     byCat: category -> every published product in it, across every supplier.
     bySupplierKey: coKey(supplier name) -> that supplier's own published
     products. Both come from the same array, so a company's own products and
     the competing products in the same category can never disagree about
     what "in this category" means. Unpublished rows (data/differentiator.json
     .held — no gated category, or no source) are not in `products` at all,
     so nothing here needs to re-check the gate; it was already applied when
     the file was written. */
  function diffIndex(diffDoc) {
    var byCat = {}, bySupplierKey = {};
    ((diffDoc && diffDoc.products) || []).forEach(function (p) {
      if (!p || !p.cat || !p.supplier) return;
      if (!byCat[p.cat]) byCat[p.cat] = [];
      byCat[p.cat].push(p);
      var k = coKey(p.supplier);
      if (!k) return;
      if (!bySupplierKey[k]) bySupplierKey[k] = [];
      bySupplierKey[k].push(p);
    });
    return { byCat: byCat, bySupplierKey: bySupplierKey };
  }

  function boot(index, seed, specMap, prodFile, fin, cache, fwDoc, awards, logoDoc, diffDoc, pendingDoc) {
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
      pending: pendingDoc || null,
      diffDoc: diffDoc || null,
      diff: diffIndex(diffDoc),
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
      if (s) groupClosedPanels(result);
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
         P.awards, P.logos, P.differentiator, P.pending);
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
    fetch(LOGOS).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(DIFF).then(function (r) { return r.json(); }).catch(function () { return null; }),
    fetch(PENDING).then(function (r) { return r.json(); }).catch(function () { return null; })
  ]).then(function (res) { boot(res[0], res[1], res[2], res[3], res[4], res[5], res[6], res[7], res[8], res[9], res[10]); })
    .catch(function () {
      MOUNT.innerHTML = '<div class="mcr"><div class="mcr-card mcr-card--empty">' +
        '<div class="mcr-card-t">Company intelligence report</div>' +
        '<div class="mcr-note">The company report is loading its data — if this persists, the index feed is temporarily unreachable. Nothing is missing from the report; the report has not loaded.</div></div></div>';
    });
})();
