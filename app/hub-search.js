/* ETH-HUBSEARCH-V7 — Hub search, served from msh-compare-data.
 *
 * WHAT CHANGED FROM V6 (06/08/2026)
 * ---------------------------------
 * V6 ranked 47 Hub pages typed by hand into WordPress, matching on a title and
 * a line of synonyms. It could not see inside a page, could not see a page
 * nobody had remembered to add, and could not see the 1,304 suppliers (as at 07/09/2026) that the
 * Suppliers page loads from JSON at run time. Lou's report was that it still
 * could not do what she wanted, and it structurally could not.
 *
 * V7 searches data/hub-search-index.json, which build_search_index.py rebuilds
 * daily from the Hub's own published pages, section by section. A result names
 * the SECTION that matched, not just the page, and links straight to it.
 *
 * It does NOT quote the matching line, and must not be made to. The index is
 * served from a PUBLIC repo, so it carries headings and sorted word bags only —
 * anything readable in there republishes a paywalled product. Ruled 06/08/2026.
 *
 * WHY THIS FILE LIVES IN THE REPO AND NOT IN THE PAGE
 * --------------------------------------------------
 * WordPress rewrites && and || into HTML entities when it renders an inline
 * script, which is a SyntaxError that kills the whole block — the reason V6 was
 * written in nested ifs. Serving the code from here removes that constraint and
 * removes WordPress from the edit path entirely: nobody has to touch page 675
 * to change how search behaves ever again. Same pattern as comptab.js and
 * supplier-search.js.
 *
 * COST: none. The index is a static file on GitHub, the search runs in the
 * member's browser, and nothing calls any paid service. There is no AI here.
 *
 * FAILURE MODE: if the index cannot be fetched, the box says so and offers
 * WordPress core search. The page 675 block also renders a plain working form
 * before this script arrives, so a total failure degrades to core search rather
 * than to an empty space.
 */
(function () {
  'use strict';

  var INDEX_URL = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/hub-search-index.json';

  var NAVY = '#0B1C33', GOLD = '#C49B5C', PANEL = '#0f172a',
      LINE = '#33415a', RULE = '#1e293b', TEXT = '#e2e8f0', DIM = '#94a3b8';

  /* TWO PLACES THIS CAN MOUNT (24/09/2026).
   * #ethHubSearch is the original full-width bar. The Live Desk masthead
   * rebuild now hides it (display:none) and draws its own small "What do you
   * want to do today?" box, .msh .qsearch, as a plain form posting to /?s=.
   * On this site /?s= is intercepted by Jetpack Instant Search, so members
   * typing a goal there got Jetpack's AI overlay instead of the Hub planner.
   * Both are bound here: whichever one the page shows is the one that works. */
  var MOUNT = document.getElementById('ethHubSearch');
  var MAST = document.querySelector('.msh .qsearch');
  if (!MOUNT && !MAST) { return; }
  var ROOT = document.documentElement;
  if (ROOT.getAttribute('data-eth-hubsearch') === 'v8') { return; }
  ROOT.setAttribute('data-eth-hubsearch', 'v8');

  // Words that carry no signal in a query. A rep types "what does ICB stand
  // for"; only "icb" narrows anything.
  var STOP = (' the a an of for in on at to is are am was were do does did how what ' +
              'where which who whom why when i my me we our you your can could should ' +
              'would with and or but if it its this that these those from by as be ' +
              'about into any all get got need want find show tell explain ' +
              // Added 06/08/2026 after live testing: "what does ICB stand for"
              // ranked Dermatology first, because "stand" was doing real work in
              // the score. These are the words people wrap a question in.
              'stand stands mean means meaning called know ').split(' ');

  var TASKS = [
    ['Prepare for a meeting', '/medical-sales-hub/med-sales-tools/#tool-prep'],
    ['Compare against a competitor', '/medical-sales-hub/med-sales-tools/#tool-compare'],
    ['Research a supplier', '/medical-sales-hub/med-sales-tools/#tool-supplier'],
    ['Map the stakeholders', '/medical-sales-hub/med-sales-tools/#sec-map'],
    ['Track a contract award', '/medical-sales-hub/awards/#q'],
    ['Check a framework or tender route', '/medical-sales-hub/frameworks/#fw-nhssc'],
    ['Check framework renewal dates', '/medical-sales-hub/frameworks/#fw-renewal'],
    ['Check price intelligence', '/medical-sales-hub/price-intelligence/'],
    ['Find a CPV code', '/medical-sales-hub/cpv/'],
    ['Understand TR reports', '/medical-sales-hub/reference/tr-reports/'],
    ['Ask for something to be added', '/medical-sales-hub/ask/']
  ];

  var DATA = null, LOADING = false, FAILED = false, input = null, box = null,
      body = null, toggle = null, chev = null;

  function esc(x) {
    return String(x)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ASCII-FOLD BEFORE ANY [^a-z0-9] STRIP.
   *
   * clean() used to strip straight to [a-z0-9 ], which maps an accented letter
   * to a SPACE rather than to its base letter. Both sides of the comparison
   * were broken by it: the index held 'm lnlycke' for Molnlycke and 'ssur' for
   * Ossur, and a member typing either name plainly got nothing back (found
   * 18/09/2026 — 11 suppliers, incl. bioMerieux, Drager, Schulke). Folding here
   * and in prepare() means the accented and unaccented spellings both work,
   * whichever the member types. The Python side folds identically in
   * build_search_index.py's ascii_fold(). */
  var FOLD_PAIRS = [
    ['\u00f8', 'o'], ['\u00d8', 'O'], ['\u00df', 'ss'],
    ['\u00e6', 'ae'], ['\u00c6', 'AE'], ['\u0153', 'oe'], ['\u0152', 'OE'],
    ['\u0111', 'd'], ['\u0110', 'D'], ['\u0142', 'l'], ['\u0141', 'L'],
    ['\u00f0', 'd'], ['\u00d0', 'D'], ['\u00fe', 'th'], ['\u00de', 'TH'],
    ['\u0131', 'i']
  ];

  function fold(x) {
    var s = String(x == null ? '' : x), i;
    for (i = 0; i < FOLD_PAIRS.length; i++) {
      s = s.split(FOLD_PAIRS[i][0]).join(FOLD_PAIRS[i][1]);
    }
    if (s.normalize) {
      s = s.normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
    }
    return s;
  }

  function clean(q) {
    return fold(q).toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function tokenise(q) {
    var parts = clean(q).split(' '), out = [], i;
    for (i = 0; i < parts.length; i++) {
      if (!parts[i]) { continue; }
      if (STOP.indexOf(parts[i]) !== -1) { continue; }
      out.push(parts[i]);
    }
    return out.length ? out : parts.filter(Boolean);
  }

  /* WHOLE WORDS ONLY, with a deliberate singular/plural pair. Nothing looser.
   *
   * V5 matched raw substrings, so "what does ICB stand for" hit "Under-STAND-ing
   * TR Reports". V6 fixed that by matching word STARTS — and word starts are
   * still too loose: tested live on 06/08/2026, the same query put Dermatology
   * above the NHS structure map, because "stand" is a prefix of "standard".
   *
   * Both haystacks are space-padded at each end, so ' tok ' can only match a
   * complete word. The one intentional stretch is singular/plural: "reports"
   * finds "report" and vice versa. */
  function hits(hay, tok) {
    if (hay.indexOf(' ' + tok + ' ') !== -1) { return true; }
    if (tok.length > 3) {
      if (tok.charAt(tok.length - 1) === 's') {
        if (hay.indexOf(' ' + tok.slice(0, -1) + ' ') !== -1) { return true; }
      } else if (hay.indexOf(' ' + tok + 's ') !== -1) { return true; }
    }
    return false;
  }

  /* Lowercased, space-padded copies are built once at load so a keystroke is a
   * scan over prepared strings rather than 4,000 toLowerCase() calls. */
  function prepare(doc) {
    var i, j, p, s;
    for (i = 0; i < doc.pages.length; i++) {
      p = doc.pages[i];
      p._t = ' ' + fold(p.t).toLowerCase() + ' ';
      for (j = 0; j < p.sec.length; j++) {
        s = p.sec[j];
        s._h = ' ' + fold(s.h).toLowerCase() + ' ';
        /* `w` is a bag of words, not prose: unique, alphabetised, stopwords
         * dropped. The index is served from a public repo, so it deliberately
         * carries nothing that can be read back as the Hub's paid content. That
         * is why there is no snippet under a result — do not add one by putting
         * text back in the index. */
        s._w = ' ' + fold(s.w).toLowerCase() + ' ';
      }
    }
    for (i = 0; i < doc.records.length; i++) {
      doc.records[i]._t = ' ' + fold(doc.records[i].t).toLowerCase() + ' ';
      doc.records[i]._k = ' ' + fold(doc.records[i].k).toLowerCase() + ' ';
    }
    return doc;
  }

  function scorePage(p, toks, phrase) {
    var s = 0, best = null, bestS = 0, i, j, sec, ss, covered = {}, tok;

    if (phrase.length > 2 && p._t.indexOf(phrase) !== -1) { s += 140; }
    for (i = 0; i < toks.length; i++) {
      if (hits(p._t, toks[i])) { s += 18; covered[toks[i]] = 1; }
    }

    for (j = 0; j < p.sec.length; j++) {
      sec = p.sec[j];
      ss = 0;
      /* A phrase can only be matched against a heading. The body is a sorted
       * bag of words, so word order does not survive in it and there is no
       * phrase left to find — which is exactly the property that stops the
       * index being readable. */
      if (phrase.length > 2 && sec._h.indexOf(phrase) !== -1) { ss += 90; }
      for (i = 0; i < toks.length; i++) {
        tok = toks[i];
        if (hits(sec._h, tok)) { ss += 12; covered[tok] = 1; }
        else if (hits(sec._w, tok)) { ss += 6; covered[tok] = 1; }
      }
      if (ss > bestS) { bestS = ss; best = sec; }
    }

    /* Score the BEST section, never the sum of all of them.
     *
     * Summing rewards size: Clinical Pathways has 60 sections, so on a sum it
     * out-scored the actual answer on almost anything. Tested live 06/08/2026,
     * "value based procurement" returned INFECTION PREVENTION above the
     * Value-Based Procurement page, and "what does ICB stand for" returned WOUND
     * CARE above "ICB — Integrated Care Board". A member does not want the
     * biggest page, they want the passage that answers them. */
    s += bestS;

    // Everything the member typed appears somewhere on this page. That is a
    // much stronger signal than a big pile of one repeated word.
    var all = true;
    for (i = 0; i < toks.length; i++) { if (!covered[toks[i]]) { all = false; } }
    if (all && toks.length) { s += 45; }

    return { s: s, sec: best };
  }

  function scoreRecord(r, toks, phrase) {
    var s = 0, i, named = false;
    if (phrase.length > 2) {
      if (r._t.indexOf(phrase) !== -1) { s += 130; named = true; }
      else if (r._k.indexOf(phrase) !== -1) { s += 45; }
    }
    for (i = 0; i < toks.length; i++) {
      if (hits(r._t, toks[i])) { s += 22; named = true; }
      else if (hits(r._k, toks[i])) { s += 7; }
    }
    /* A supplier record is one of 1,304 records (as at 07/09/2026) with names, aliases, specialities and
     * framework titles. One incidental keyword hit — "tender close april 2026"
     * brushing against a framework name — is not a reason to put a company in
     * front of a member who asked about a deadline. Either the query touched
     * the company's own name, or it has to earn its place on keywords alone. */
    if (!named && s < 45) { return 0; }
    return s;
  }

  /* THERE IS NO SNIPPET FUNCTION, AND THAT IS DELIBERATE.
   * An earlier build quoted the matching line under each result, which meant the
   * index had to carry running text from every Hub page — and the index is
   * served from a PUBLIC repo, so that published the paid product. Lou ruled on
   * it, 06/08/2026: the index carries headings and bags of words only. A result
   * gives the section and links straight to it. If the quoted line is ever
   * wanted back, move the index behind the login first. */

  /* Deep-link to a section that has no id of its own.
   *
   * Only 3 of 772 sections in the live index carry an anchor — Hub panels are
   * mostly `<div class="panel"><h2>TITLE</h2>` with nothing to link to. Without
   * this, "links straight to the section" means "lands at the top of the page"
   * for 769 of them.
   *
   * A text fragment (#:~:text=) makes the browser find and scroll to the words
   * itself, so no id is needed. Chrome, Edge and Safari 16+ support it; anything
   * else ignores the fragment and lands at the top of the page, which is exactly
   * where it would have landed anyway. There is no downside case.
   *
   * Only the first few words are used: an indexed heading can carry a trailing
   * source label ("MHRA ALERTS & RECALLS GOV.UK") that is a separate element on
   * the page, and a fragment spanning both would match nothing. */
  function textFragment(heading) {
    var words = String(heading || '').trim().split(/\s+/).slice(0, 6).join(' ');
    if (words.length < 4) { return ''; }
    return '#:~:text=' + encodeURIComponent(words);
  }

  function rank(q) {
    var toks = tokenise(q), phrase = clean(q), out = [], i, r, sc;
    if (!toks.length) { return out; }

    for (i = 0; i < DATA.pages.length; i++) {
      r = scorePage(DATA.pages[i], toks, phrase);
      if (r.s > 0) {
        out.push({ kind: 'page', s: r.s, page: DATA.pages[i], sec: r.sec });
      }
    }
    for (i = 0; i < DATA.records.length; i++) {
      sc = scoreRecord(DATA.records[i], toks, phrase);
      if (sc > 0) { out.push({ kind: 'rec', s: sc, rec: DATA.records[i] }); }
    }
    if (!out.length) { return out; }
    out.sort(function (a, b) { return b.s - a.s; });

    /* Cut the long tail. Once results are ranked, everything scoring a small
     * fraction of the best hit is a word that happened to appear, not an answer
     * — and a list padded with those is indistinguishable to a reader from the
     * "returns all random stuff" search this replaced. Showing three good
     * results and stopping is the honest output. */
    var floor = Math.max(12, out[0].s * 0.18);
    out = out.filter(function (r) { return r.s >= floor; });
    return out.slice(0, 10);
  }

  /* ---------------------------------------------------------------- planner
   * "WHAT DO YOU WANT TO DO TODAY?" ANSWERED AS A PLAN, NOT JUST A SEARCH.
   * Added 23/09/2026. A member types a goal in their own words ("meeting with
   * the tissue viability lead at Leeds about Molnlycke on Thursday") and gets
   * an ordered route through the Hub tools that fit it, above the ordinary
   * search results.
   *
   * COST: none, same as the search. This is keyword rules plus the supplier
   * names already in the index, run in the member's browser. No AI service,
   * no API key, no per-member charge. It must stay that way: a paid model
   * here would bill Lou for every member keystroke.
   *
   * It only ever suggests pages that exist. If nothing in the goal is
   * recognised, no plan is shown and the search results stand alone. */
  var GOALS = [
    { id: 'meeting', words: ['meeting', 'meet', 'call', 'visit', 'appointment', 'pitch', 'present',
        'presentation', 'demo', 'introduce', 'intro', 'catch up with', 'seeing'],
      steps: [
        ['Prepare for the meeting', '/medical-sales-hub/med-sales-tools/#tool-prep',
         'Builds your brief for the customer and the product in front of them.'],
        ['Map who else is in the room', '/medical-sales-hub/med-sales-tools/#sec-map',
         'Who decides, who influences, who signs.']
      ] },
    { id: 'compare', words: ['compare', 'competitor', 'competitors', 'competition', 'versus', 'vs',
        'against', 'rival', 'switch', 'convert', 'conversion', 'displace'],
      steps: [
        ['Compare against the competitor', '/medical-sales-hub/med-sales-tools/#tool-compare',
         'Side by side, with open recalls and supply gaps flagged.'],
        ['See who else sells in this area', '/medical-sales-hub/who-are-the-competitors/', '']
      ] },
    { id: 'tender', words: ['tender', 'tenders', 'framework', 'frameworks', 'contract', 'contracts',
        'award', 'awards', 'bid', 'renewal', 'procurement', 'itt', 'pqq'],
      steps: [
        ['Check the framework or tender route', '/medical-sales-hub/frameworks/#fw-nhssc', ''],
        ['Check renewal dates', '/medical-sales-hub/frameworks/#fw-renewal',
         'Know when the window opens before your competitor does.'],
        ['Look up past awards and tenders', '/medical-sales-hub/tender-history/', '']
      ] },
    { id: 'people', words: ['stakeholder', 'stakeholders', 'decision maker', 'decision makers',
        'buyer', 'buyers', 'who buys', 'who decides', 'budget holder', 'org chart', 'map'],
      steps: [
        ['Map the stakeholders', '/medical-sales-hub/med-sales-tools/#sec-map', ''],
        ['See how the NHS fits together', '/medical-sales-hub/nhs-structure-map/',
         'Trust, ICB and national roles in one view.']
      ] },
    { id: 'price', words: ['price', 'prices', 'pricing', 'cost', 'costs', 'cheaper', 'expensive',
        'saving', 'savings', 'value', 'budget'],
      steps: [
        ['Check price intelligence', '/medical-sales-hub/price-intelligence/', ''],
        ['Build the value case', '/medical-sales-hub/med-sales-tools/value-equation/', ''],
        ['Value-based procurement explained', '/medical-sales-hub/value-based-procurement/', '']
      ] },
    { id: 'supply', words: ['recall', 'recalls', 'shortage', 'shortages', 'supply', 'out of stock',
        'alert', 'alerts', 'fsn', 'delisted', 'delisting', 'discontinued', 'mhra'],
      steps: [
        ['Check the Supply Disruption Tracker', '/medical-sales-hub/supply-disruption-tracker/', ''],
        ['Check the MHRA Regulatory Desk', '/medical-sales-hub/mhra-regulatory-desk/', '']
      ] },
    // Not a bare "role": "the ICB role in formulary" is not a job hunt.
    { id: 'career', words: ['interview', 'interviews', 'job', 'jobs', 'cv', 'career', 'new job',
        'hired', 'hiring', 'application', 'apply', 'first sales', 'break into', 'get into'],
      steps: [
        ['Prepare for the interview', '/medical-sales-hub/interview-prep/', ''],
        ['Visit the Career Centre', '/medical-sales-hub/careers/', ''],
        ['Clinical to commercial routes', '/medical-sales-hub/clinical-to-commercial-routes/', '']
      ] },
    { id: 'territory', words: ['new territory', 'territory', 'patch', 'new to', 'prospect',
        'prospects', 'prospecting', 'target', 'targets', 'where to start', 'new area', 'new role'],
      steps: [
        ['Find your speciality', '/medical-sales-hub/find-your-speciality/', ''],
        ['Check the Sales Triggers Desk', '/medical-sales-hub/sales-triggers/',
         'Events that open a door this week.'],
        ['See capital and estates spend', '/medical-sales-hub/capital-estates-watch/', '']
      ] },
    // Not "today" or "this week": they ride along on almost any goal.
    { id: 'news', words: ['news', 'latest', 'whats new', 'what s new', 'catch up', 'catching up',
        'headlines'],
      steps: [
        ['Start at the Live Desk', '/medical-sales-hub/', 'Today’s headlines for reps.'],
        ['Check the Sales Triggers Desk', '/medical-sales-hub/sales-triggers/', ''],
        ['See what’s coming up', '/medical-sales-hub/calendar/', '']
      ] },
    { id: 'learn', words: ['learn', 'understand', 'explain', 'course', 'courses', 'cpd', 'training',
        'glossary', 'acronym'],
      steps: [
        ['Look it up in the Glossary', '/medical-sales-hub/glossary/', ''],
        ['Browse Courses and CPD', '/medical-sales-hub/courses/', '']
      ] }
  ];

  // Words a rep uses for a speciality, mapped to its Hub page. Whole-word match.
  var SPECS = [
    ['wound', '/medical-sales-hub/tissue-viability-and-wound-care/', 'Tissue Viability and Wound Care'],
    ['wounds', '/medical-sales-hub/tissue-viability-and-wound-care/', 'Tissue Viability and Wound Care'],
    ['tissue viability', '/medical-sales-hub/tissue-viability-and-wound-care/', 'Tissue Viability and Wound Care'],
    ['dressing', '/medical-sales-hub/tissue-viability-and-wound-care/', 'Tissue Viability and Wound Care'],
    ['dressings', '/medical-sales-hub/tissue-viability-and-wound-care/', 'Tissue Viability and Wound Care'],
    ['stroke', '/medical-sales-hub/stroke/', 'Stroke'],
    ['theatre', '/medical-sales-hub/theatres-and-surgical/', 'Theatres and Surgical'],
    ['theatres', '/medical-sales-hub/theatres-and-surgical/', 'Theatres and Surgical'],
    ['surgical', '/medical-sales-hub/theatres-and-surgical/', 'Theatres and Surgical'],
    ['ortho', '/medical-sales-hub/orthopaedics-and-trauma/', 'Orthopaedics and Trauma'],
    ['orthopaedic', '/medical-sales-hub/orthopaedics-and-trauma/', 'Orthopaedics and Trauma'],
    ['orthopaedics', '/medical-sales-hub/orthopaedics-and-trauma/', 'Orthopaedics and Trauma'],
    ['trauma', '/medical-sales-hub/orthopaedics-and-trauma/', 'Orthopaedics and Trauma'],
    ['neuro', '/medical-sales-hub/neurology-and-neurosurgery/', 'Neurology and Neurosurgery'],
    ['neurology', '/medical-sales-hub/neurology-and-neurosurgery/', 'Neurology and Neurosurgery'],
    ['cardiology', '/medical-sales-hub/cardiology-and-cardiac-surgery/', 'Cardiology and Cardiac Surgery'],
    ['cardiac', '/medical-sales-hub/cardiology-and-cardiac-surgery/', 'Cardiology and Cardiac Surgery'],
    ['vascular', '/medical-sales-hub/vascular-surgery-and-pad/', 'Vascular Surgery and PAD'],
    ['urology', '/medical-sales-hub/urology/', 'Urology'],
    ['critical care', '/medical-sales-hub/critical-care/', 'Critical Care'],
    ['icu', '/medical-sales-hub/critical-care/', 'Critical Care'],
    ['itu', '/medical-sales-hub/critical-care/', 'Critical Care'],
    ['pathology', '/medical-sales-hub/pathology-and-laboratory-medicine/', 'Pathology and Laboratory Medicine'],
    ['lab', '/medical-sales-hub/pathology-and-laboratory-medicine/', 'Pathology and Laboratory Medicine'],
    ['endoscopy', '/medical-sales-hub/colorectal-gi-and-endoscopy/', 'Colorectal, GI and Endoscopy'],
    ['colorectal', '/medical-sales-hub/colorectal-gi-and-endoscopy/', 'Colorectal, GI and Endoscopy'],
    ['stoma', '/medical-sales-hub/colorectal-gi-and-endoscopy/', 'Colorectal, GI and Endoscopy'],
    ['ophthalmology', '/medical-sales-hub/ophthalmology/', 'Ophthalmology'],
    ['eye', '/medical-sales-hub/ophthalmology/', 'Ophthalmology'],
    ['ent', '/medical-sales-hub/ent-and-head-and-neck/', 'ENT and Head and Neck'],
    ['gynaecology', '/medical-sales-hub/gynaecology-and-womens-health/', 'Gynaecology and Women’s Health'],
    ['plastics', '/medical-sales-hub/plastics-burns-and-reconstruction/', 'Plastics, Burns and Reconstruction'],
    ['burns', '/medical-sales-hub/plastics-burns-and-reconstruction/', 'Plastics, Burns and Reconstruction'],
    ['interventional radiology', '/medical-sales-hub/interventional-radiology/', 'Interventional Radiology'],
    ['respiratory', '/medical-sales-hub/respiratory/', 'Respiratory'],
    ['diabetes', '/medical-sales-hub/diabetes-and-endocrinology/', 'Diabetes and Endocrinology'],
    ['renal', '/medical-sales-hub/renal/', 'Renal'],
    ['dialysis', '/medical-sales-hub/renal/', 'Renal'],
    ['oncology', '/medical-sales-hub/oncology-and-sact/', 'Oncology and SACT'],
    ['cancer', '/medical-sales-hub/oncology-and-sact/', 'Oncology and SACT'],
    ['haematology', '/medical-sales-hub/haematology-and-patient-blood-management/', 'Haematology and Patient Blood Management'],
    ['pain', '/medical-sales-hub/pain-management/', 'Pain Management'],
    ['maternity', '/medical-sales-hub/maternity-and-neonatal/', 'Maternity and Neonatal'],
    ['neonatal', '/medical-sales-hub/maternity-and-neonatal/', 'Maternity and Neonatal'],
    ['rehab', '/medical-sales-hub/rehabilitation-prosthetics-and-orthotics/', 'Rehabilitation, Prosthetics and Orthotics'],
    ['continence', '/medical-sales-hub/continence-bladder-and-bowel/', 'Continence, Bladder and Bowel'],
    ['catheter', '/medical-sales-hub/continence-bladder-and-bowel/', 'Continence, Bladder and Bowel'],
    ['nutrition', '/medical-sales-hub/nutrition-and-dietetics/', 'Nutrition and Dietetics'],
    ['iv', '/medical-sales-hub/vascular-access-and-iv-therapy/', 'Vascular Access and IV Therapy'],
    ['vascular access', '/medical-sales-hub/vascular-access-and-iv-therapy/', 'Vascular Access and IV Therapy'],
    ['patient handling', '/medical-sales-hub/patient-handling/', 'Patient Moving and Handling'],
    ['infection', '/medical-sales-hub/infection-prevention-and-control/', 'Infection Prevention and Control'],
    ['ipc', '/medical-sales-hub/infection-prevention-and-control/', 'Infection Prevention and Control'],
    ['radiology', '/medical-sales-hub/radiology-and-imaging/', 'Radiology and Imaging'],
    ['imaging', '/medical-sales-hub/radiology-and-imaging/', 'Radiology and Imaging'],
    ['pharmacy', '/medical-sales-hub/pharmacy-and-medicines/', 'Pharmacy and Medicines'],
    ['audiology', '/medical-sales-hub/audiology-and-hearing/', 'Audiology and Hearing'],
    ['gp', '/medical-sales-hub/primary-care-and-general-practice/', 'Primary Care and General Practice'],
    ['primary care', '/medical-sales-hub/primary-care-and-general-practice/', 'Primary Care and General Practice'],
    ['digital', '/medical-sales-hub/digital-and-medical-it/', 'Digital and Medical IT'],
    ['sepsis', '/medical-sales-hub/sepsis-and-the-deteriorating-patient/', 'Sepsis and the Deteriorating Patient'],
    ['frailty', '/medical-sales-hub/frailty-and-older-people/', 'Frailty and Older People'],
    ['falls', '/medical-sales-hub/fall-prevention-medical-sales-market-insights/', 'Fall Prevention'],
    ['emergency', '/medical-sales-hub/emergency-and-urgent-care/', 'Emergency and Urgent Care'],
    ['mental health', '/medical-sales-hub/mental-health/', 'Mental Health'],
    ['palliative', '/medical-sales-hub/palliative-and-end-of-life-care/', 'Palliative and End-of-Life Care'],
    ['dermatology', '/medical-sales-hub/dermatology/', 'Dermatology'],
    ['paediatrics', '/medical-sales-hub/paediatrics/', 'Paediatrics'],
    ['paediatric', '/medical-sales-hub/paediatrics/', 'Paediatrics'],
    ['obesity', '/medical-sales-hub/obesity-and-weight-management/', 'Obesity and Weight Management']
  ];

  function has(hay, phrase) { return hay.indexOf(' ' + phrase + ' ') !== -1; }

  /* A supplier is recognised only when its full name appears as whole words in
   * the goal. Names shorter than four letters are skipped: "BD" or "3M" as a
   * bare token collides with ordinary words too easily, and a wrong company in
   * a plan is worse than none (the search results below still find them).
   * Longest name wins, so "Smith & Nephew" beats a shorter partial. */
  // Supplier names in the index that are also ordinary words or place names.
  var NOT_NAMES = ' banner bray formal instinctive liberator mast medi northwood possum southgate ';

  function findSupplier(hay) {
    var best = null, i, r, n;
    if (!DATA) { return null; }
    for (i = 0; i < DATA.records.length; i++) {
      r = DATA.records[i];
      n = r._n;
      if (n === undefined) {
        n = r._n = clean(String(r.t).replace(/\b(ltd|limited|plc|uk|group|inc|llc|gmbh)\b\.?/gi, ' '));
      }
      if (n.length < 4 || NOT_NAMES.indexOf(' ' + n + ' ') !== -1) { continue; }
      if (has(hay, n) && (!best || n.length > best._n.length)) { best = r; }
    }
    return best;
  }

  function plan(q) {
    var hay = ' ' + clean(q) + ' ', steps = [], seen = {}, i, j, g, sp = null, sup;

    function add(title, href, why) {
      if (seen[href]) { return; }
      seen[href] = 1;
      steps.push([title, href, why || '']);
    }

    for (i = 0; i < SPECS.length; i++) {
      if (has(hay, SPECS[i][0])) { sp = SPECS[i]; break; }
    }
    sup = findSupplier(hay);

    var goals = [];
    for (i = 0; i < GOALS.length; i++) {
      g = GOALS[i];
      for (j = 0; j < g.words.length; j++) {
        if (has(hay, clean(g.words[j]))) { goals.push(g); break; }
      }
    }
    if (!goals.length && !sp && !sup) { return null; }

    // First step of each goal, in the order the goals are listed, then the rest.
    for (i = 0; i < goals.length; i++) { add.apply(null, goals[i].steps[0]); }
    if (sup) {
      add('Open the ' + sup.t + ' company report',
          '/medical-sales-hub/company-report/?company=' + encodeURIComponent(sup.t),
          'Products, frameworks, awards and news in one place.');
    }
    if (sp) {
      add('Read the ' + sp[2] + ' page', sp[1], 'Pathway, buyers and suppliers for this area.');
    }
    for (i = 0; i < goals.length; i++) {
      for (j = 1; j < goals[i].steps.length; j++) { add.apply(null, goals[i].steps[j]); }
    }
    if (sp || sup) {
      add('Check for recalls and supply gaps', '/medical-sales-hub/supply-disruption-tracker/',
          'Worth knowing before anyone raises it with you.');
    }
    return steps.slice(0, 5);
  }

  function planHtml(steps) {
    var html = '<div style="padding:12px 14px 6px;color:' + GOLD + ';font-size:11px;letter-spacing:1.2px;' +
               'font-weight:700;text-transform:uppercase;">Your plan for today</div>', i, s;
    for (i = 0; i < steps.length; i++) {
      s = steps[i];
      html += '<a href="' + esc(s[1]) + '" style="display:flex;gap:12px;align-items:flex-start;padding:10px 14px;' +
              'color:' + TEXT + ';text-decoration:none;border-top:1px solid ' + RULE + ';">' +
              '<span style="flex:0 0 auto;width:24px;height:24px;border-radius:50%;background:' + GOLD + ';' +
              'color:' + NAVY + ';font-size:13px;font-weight:700;display:inline-flex;align-items:center;' +
              'justify-content:center;">' + (i + 1) + '</span>' +
              '<span><span style="display:block;font-size:14px;font-weight:600;">' + esc(s[0]) + '</span>' +
              (s[2] ? '<span style="display:block;color:#a8b3c4;font-size:12.5px;line-height:1.5;margin-top:2px;">' +
                      esc(s[2]) + '</span>' : '') +
              '</span></a>';
    }
    return html + '<div style="height:10px;border-bottom:2px solid ' + LINE + ';"></div>';
  }

  /* THE PLAN AND JETPACK'S AI, SIDE BY SIDE (24/09/2026).
   * The plan is rules over pages Lou has checked. Jetpack's AI answer writes
   * prose from the site's content, which reads well but is generated: on its
   * first test it stated framework numbers and expiry dates nobody had checked.
   * So the two sit together but never blend. The plan and matches come first
   * and Enter still opens plan step 1; the AI is one clearly labelled card
   * that hands the same question to Jetpack (/?s= opens its overlay), with
   * the check-the-facts line on the card itself. Nothing Jetpack writes is
   * copied into this panel. */
  function aiCard(q) {
    return '<a href="/?s=' + encodeURIComponent(q) + '" style="display:flex;gap:12px;align-items:center;' +
           'margin:10px 14px;padding:11px 13px;border:1px solid ' + GOLD + ';border-radius:8px;' +
           'background:rgba(196,155,92,.08);color:' + TEXT + ';text-decoration:none;">' +
           '<span style="flex:0 0 auto;padding:3px 7px;border-radius:5px;background:' + GOLD + ';color:' + NAVY + ';' +
           'font-size:10.5px;font-weight:800;letter-spacing:.08em;">AI</span>' +
           '<span style="flex:1;min-width:0;"><span style="display:block;font-size:14px;font-weight:600;">' +
           'Get a written answer from the Hub AI</span>' +
           '<span style="display:block;color:#a8b3c4;font-size:12px;line-height:1.45;margin-top:2px;">' +
           'AI-generated from Hub content. Check key facts on the pages it links before you use them.</span></span>' +
           '<span style="flex:0 0 auto;color:' + GOLD + ';font-size:16px;">\u2192</span></a>';
  }

  // ------------------------------------------------------------------ render
  function shell() {
    var chips = TASKS.map(function (t) {
      return '<a href="' + esc(t[1]) + '" style="display:block;padding:11px 14px;border-radius:8px;' +
             'border:1px solid ' + LINE + ';background:' + PANEL + ';color:' + TEXT + ';font-size:13.5px;' +
             'line-height:1.35;text-decoration:none;font-weight:500;">' + esc(t[0]) + '</a>';
    }).join('');

    /* COLLAPSED BY DEFAULT (18/08/2026). The box, the hint and the twelve task
     * chips used to occupy the full width of the screen above the first panel,
     * so a member arriving at the Live Desk scrolled past the search before
     * reaching a single headline. It now opens on click and shuts again, and
     * the index is still only fetched on first contact, never on page load. */
    MOUNT.innerHTML =
      '<div id="ethHubToggle" role="button" tabindex="0" aria-expanded="false" aria-controls="ethHubBody" ' +
      'style="display:flex;align-items:center;gap:12px;cursor:pointer;-webkit-user-select:none;user-select:none;">' +
        '<span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;' +
        'border-radius:50%;background:' + GOLD + ';color:' + NAVY + ';font-size:21px;font-weight:700;line-height:1;flex:0 0 auto;">?</span>' +
        '<span style="color:#fff;font-size:17px;font-weight:700;">What do you want to do today?</span>' +
        '<span id="ethHubChev" style="margin-left:auto;color:' + GOLD + ';font-size:12px;font-weight:700;' +
        'letter-spacing:.12em;white-space:nowrap;">SEARCH +</span>' +
      '</div>' +
      '<div id="ethHubBody" style="display:none;margin-top:14px;">' +
      '<div style="display:flex;gap:10px;margin:0 0 8px;width:100%;">' +
        '<input id="ethHubInput" type="search" autocomplete="off" aria-label="Search the Hub" ' +
        'placeholder="Tell me your goal, e.g. meeting with a wound care lead about Molnlycke" ' +
        'style="flex:1;min-width:0;padding:13px 16px;border-radius:8px;border:1px solid ' + LINE + ';' +
        'background:' + PANEL + ';color:#fff;font-size:14.5px;font-family:inherit;box-sizing:border-box;">' +
        '<button type="button" id="ethHubGo" style="padding:13px 28px;border-radius:8px;border:none;' +
        'background:' + GOLD + ';color:' + NAVY + ';font-weight:700;font-size:14.5px;cursor:pointer;' +
        'font-family:inherit;white-space:nowrap;">Go</button>' +
      '</div>' +
      '<div id="ethHubResults" style="display:none;background:' + PANEL + ';border:1px solid ' + LINE + ';' +
      'border-radius:8px;margin:0 0 12px;overflow:hidden;max-height:60vh;overflow-y:auto;"></div>' +
      '<p id="ethHubHint" style="margin:0 0 16px;color:' + DIM + ';font-size:12.5px;">' +
      'Type what you\u2019re working on and get a step-by-step plan, or search inside every Hub page. ' +
      'Or jump straight to a task.</p>' +
      '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:9px;width:100%;">' +
      chips + '</div>' +
      '</div>';

    input = document.getElementById('ethHubInput');
    box = document.getElementById('ethHubResults');
    body = document.getElementById('ethHubBody');
    toggle = document.getElementById('ethHubToggle');
    chev = document.getElementById('ethHubChev');
  }

  function isOpen() { return body.style.display !== 'none'; }

  function setOpen(open) {
    body.style.display = open ? 'block' : 'none';
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    chev.textContent = open ? 'SEARCH \u2013' : 'SEARCH +';
    if (open) { load(); input.focus(); }
  }

  function row(href, title, kicker, body) {
    return '<a href="' + esc(href) + '" style="display:block;padding:11px 14px;color:' + TEXT + ';' +
           'text-decoration:none;border-top:1px solid ' + RULE + ';">' +
           '<span style="display:block;font-size:14px;font-weight:600;">' + esc(title) + '</span>' +
           (kicker ? '<span style="display:block;color:' + GOLD + ';font-size:11px;font-weight:700;' +
                     'letter-spacing:.8px;text-transform:uppercase;margin-top:3px;">' + esc(kicker) + '</span>' : '') +
           (body ? '<span style="display:block;color:#a8b3c4;font-size:12.5px;line-height:1.5;margin-top:4px;">' +
                   body + '</span>' : '') +
           '</a>';
  }

  function note(text) {
    return '<div style="padding:12px 14px;color:' + DIM + ';font-size:13px;">' + text + '</div>';
  }

  function render() {
    var q = input.value ? input.value.trim() : '';
    if (q.length < 2) { box.style.display = 'none'; box.innerHTML = ''; return; }

    box.style.display = 'block';

    if (FAILED) {
      box.innerHTML = note('Hub search cannot reach its index right now.') + aiCard(q);
      return;
    }
    if (!DATA) {
      box.innerHTML = note('Loading the Hub index…');
      load();
      return;
    }

    var toks = tokenise(q), res = rank(q), steps = plan(q), i, r, html, href, kicker;
    var top = (steps ? planHtml(steps) : '') + aiCard(q);
    // With a plan on screen the matches are supporting reading, not the answer.
    if (steps) { res = res.slice(0, 4); }

    if (!res.length) {
      box.innerHTML = top + note('No Hub page matches those words. Ask the AI above, or try a ' +
        'broader word such as framework, tender, pricing, pathway or glossary.');
      return;
    }

    html = top + '<div style="padding:8px 14px 4px;color:' + DIM + ';font-size:11px;letter-spacing:1.2px;' +
           'font-weight:700;text-transform:uppercase;">' + res.length +
           (res.length === 1 ? ' match' : ' matches') + (steps ? ' to read next' : ' on the Hub') + '</div>';

    for (i = 0; i < res.length; i++) {
      r = res[i];
      if (r.kind === 'rec') {
        html += row(r.rec.u, r.rec.t, r.rec.c || 'Record', 'Opens the supplier record on the Suppliers page');
      } else {
        href = r.page.u;
        kicker = r.page.t;
        if (r.sec) {
          if (r.sec.a) { href = r.page.u + '#' + r.sec.a; }
          else { href = r.page.u + textFragment(r.sec.h); }
          /* Show the PAGE path, never `href`. When href carries a text
           * fragment, printing it puts a line of percent-encoding under every
           * result ("#:~:text=Evergreen%20Level%201%3A%20pass%20this%20or"),
           * which reads like a bug. The link still carries the fragment. */
          html += row(href, r.sec.h || r.page.t,
                      r.sec.h && r.sec.h !== r.page.t ? kicker : '',
                      esc(r.page.u));
        } else {
          html += row(href, r.page.t, '', esc(r.page.u));
        }
      }
    }

    box.innerHTML = html;
  }

  // -------------------------------------------------------------------- data
  function load() {
    if (LOADING || DATA || FAILED) { return; }
    LOADING = true;
    // Cache-buster changes once a day (matches the daily pipeline rebuild),
    // not on every page view. A per-millisecond buster, plus cache:'no-store'
    // below, forced every single member's request past every cache layer
    // straight to GitHub's origin — fine normally, but during a GitHub-side
    // error spike (e.g. the 17/08/2026 raw-content incident) it turns a
    // partial outage into a 100% search failure for every member. Letting
    // the edge and browser cache hold a same-day copy means most loads are
    // shielded from a transient origin problem. 17/08/2026.
    var url = INDEX_URL + '?cb=' + new Date().toISOString().slice(0, 10);
    fetch(url)
      .then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.json();
      })
      .then(function (doc) {
        if (!doc || !doc.pages || !doc.pages.length) { throw new Error('empty index'); }
        if (!doc.records) { doc.records = []; }
        DATA = prepare(doc);
        LOADING = false;
        render();
      })
      .catch(function () {
        LOADING = false;
        FAILED = true;
        render();
      });
  }

  // -------------------------------------------------------------------- wire
  var timer = null;
  function schedule() {
    if (timer) { clearTimeout(timer); }
    timer = setTimeout(render, 90);
  }

  // render() draws into whichever input/box pair the member is using. Each
  // place calls use() before it renders, so the two never draw into each other.
  function use(i, b) { input = i; box = b; }

  // Enter opens the first plan step or match. It never falls through to /?s=
  // on its own: that URL opens Jetpack's overlay, which is exactly what this
  // box exists to replace. The "search every page" link stays for a member who
  // chooses it.
  function goFirst(i, b) {
    var links = b.style.display !== 'none' ? b.querySelectorAll('a[href]') : [], k, h;
    for (k = 0; k < links.length; k++) {
      h = links[k].getAttribute('href');
      if (h.indexOf('/?s=') !== 0) { window.location.assign(h); return; }
    }
  }

  if (MOUNT) {
    shell();
    var barInput = input, barBox = box;

    // The index is fetched on first contact with the box, never on page load, so
    // the Live Desk is not made slower for the members who never search.
    barInput.addEventListener('focus', function () { use(barInput, barBox); load(); });
    barInput.addEventListener('input', function () { use(barInput, barBox); load(); schedule(); });
    barInput.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') { return; }
      e.preventDefault();
      use(barInput, barBox);
      var first = barBox.querySelector('a[href]');
      if (first && barBox.style.display !== 'none') { window.location.assign(first.getAttribute('href')); }
    });
    toggle.addEventListener('click', function () { use(barInput, barBox); setOpen(!isOpen()); });
    toggle.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') { return; }
      e.preventDefault();
      use(barInput, barBox);
      setOpen(!isOpen());
    });

    document.getElementById('ethHubGo').addEventListener('click', function () {
      use(barInput, barBox);
      goFirst(barInput, barBox);
    });
  }

  /* ------------------------------------------------------- masthead box
   * The masthead box is 300px wide, so results cannot sit inside it. They open
   * in a panel under it, fixed to the viewport rather than absolute inside the
   * masthead: the masthead carries a background photo and overlay, and a panel
   * positioned inside it would be clipped or sit under the overlay.
   *
   * The page's <form> is REPLACED, not just listened to. Jetpack Instant Search
   * binds to search inputs (name="s") when the page loads and opens its own
   * overlay on submit. A fresh form with no name="s" carries none of Jetpack's
   * listeners and matches none of its selectors, and submit is stopped in the
   * capture phase as a second guard. With JavaScript off, the page's original
   * form is untouched and still falls back to site search. */
  function bindMast(q) {
    var old = q.querySelector('form');
    if (!old) { return; }

    var form = document.createElement('form');
    form.setAttribute('role', 'presentation');
    form.setAttribute('autocomplete', 'off');
    form.innerHTML =
      '<input type="text" aria-label="Tell the Hub what you want to do today" autocomplete="off" ' +
      'spellcheck="false" placeholder="e.g. meeting about Molnlycke">' +
      '<button type="submit">Plan</button>';
    old.parentNode.replaceChild(form, old);

    var mInput = form.querySelector('input'), mBox = document.createElement('div');
    mBox.setAttribute('role', 'region');
    mBox.setAttribute('aria-label', 'Your plan and matching Hub pages');
    mBox.style.cssText = 'display:none;position:fixed;z-index:2147483000;background:' + NAVY + ';' +
      'border:1px solid ' + LINE + ';border-top:3px solid ' + GOLD + ';border-radius:10px;' +
      'box-shadow:0 18px 48px rgba(0,0,0,.45),0 2px 6px rgba(0,0,0,.3);overflow-y:auto;' +
      'font-family:Inter,-apple-system,"Segoe UI",Arial,sans-serif;text-align:left;' +
      '-webkit-font-smoothing:antialiased;';
    document.body.appendChild(mBox);

    // Under the box, right edges aligned, wide enough to read, never off-screen.
    function place() {
      var r = q.getBoundingClientRect(), vw = window.innerWidth, vh = window.innerHeight;
      var w = Math.min(600, vw - 32), left = Math.min(r.right - w, vw - w - 16);
      if (left < 16) { left = 16; }
      mBox.style.width = w + 'px';
      mBox.style.left = left + 'px';
      mBox.style.top = (r.bottom + 8) + 'px';
      mBox.style.maxHeight = Math.max(220, vh - r.bottom - 24) + 'px';
    }
    function refresh() { use(mInput, mBox); render(); if (mBox.style.display !== 'none') { place(); } }
    function close() { mBox.style.display = 'none'; }

    mInput.addEventListener('focus', function () { use(mInput, mBox); load(); if (mInput.value.trim().length > 1) { refresh(); } });
    mInput.addEventListener('input', function () {
      use(mInput, mBox); load();
      if (timer) { clearTimeout(timer); }
      timer = setTimeout(refresh, 90);
    });
    mInput.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { close(); mInput.blur(); }
    });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      e.stopPropagation();
      use(mInput, mBox);
      goFirst(mInput, mBox);
    }, true);

    document.addEventListener('mousedown', function (e) {
      if (mBox.style.display === 'none') { return; }
      if (mBox.contains(e.target) || q.contains(e.target)) { return; }
      close();
    });
    window.addEventListener('resize', function () { if (mBox.style.display !== 'none') { place(); } });
    window.addEventListener('scroll', function () { if (mBox.style.display !== 'none') { place(); } }, true);
  }

  if (MAST) { bindMast(MAST); }

  // Lets the page, or a test harness, supply the index directly.
  if (window.MSH_HUB_SEARCH_INDEX) {
    DATA = prepare(window.MSH_HUB_SEARCH_INDEX);
  }

  // Harness hook: lets a test call the planner directly. Carries no data.
  window.MSH_HUB_PLAN = plan;
})();
