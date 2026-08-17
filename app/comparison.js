/* Medical Sales Intelligence Hub — Product Comparison tool (PRODUCT-FIRST, with live NHSSC detail).
   Enter YOUR product -> it auto-finds competitor products (same device type /
   speciality across other suppliers) -> compares at product level and shows the
   REAL NHS Supply Chain detail ON the page: product image, description, every pack
   variant with its NPC / MPC code and status (cached from the public NHSSC pilot
   catalogue). Then layers on the real difference, an optional audience angle (incl.
   the MSTP objection method) and an AI prompt. Copy-brief button included. */
(function () {
  var MOUNT = document.getElementById('msh-compare-tool');
  if (!MOUNT) return;
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var GOLD = '#a8842c', OX = '#6B2A34', GRN = '#2E6B3E', INK = '#20303f', LINE = '#e6e2d8', PANEL = '#ffffff', SOFT = '#f7f5ef';
  /* The two sides, one colour each, used identically in the form and in every
     panel of the result. Slate rather than red for the competitor: on this tool
     the rival is a legitimate product, not a threat to be flagged. */
  var MINE_C = OX, MINE_BG = '#fbf3f4';
  var THEIR_C = '#2A5A6B', THEIR_BG = '#eff5f7';
  // Cache-buster changes once a day (matches the daily pipeline rebuild), not
  // on every page view — a per-millisecond buster defeats GitHub's/Fastly's
  // edge cache on every single request, which turns any GitHub-side hiccup
  // into a 100% member-facing failure instead of a partial one. 17/08/2026.
  var CB = '?cb=' + new Date().toISOString().slice(0, 10);
  var IDX = BASE + 'data/supplier-index.json' + CB;
  var CFG = BASE + 'data/prep-config.json' + CB;
  var SEED = BASE + 'data/supplier-seed.json' + CB;
  var NHSSC = BASE + 'data/nhssc-cache.json' + CB;
  /* The company's own website range — a different KIND of fact from everything
     else this tool loads, and kept separate for that reason. See the note where
     it is folded into PRODUCTS. */
  var RANGEURL = BASE + 'data/supplier-products.json' + CB;
  var RANGE = {};

  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function el(tag, css, html){ var e = document.createElement(tag); if (css) e.style.cssText = css; if (html != null) e.innerHTML = html; return e; }
  function nk(s){ return String(s||'').toLowerCase().replace(/\s+/g,' ').trim(); }

  var TYPES = ['antisepsis','antiseptic','chlorhexidine','skin prep','skin disinfect','disinfectant','applicator','swabstick','swab','tourniquet','blood culture','cannula','picc','midline','catheter','iol','intraocular','phaco','hearing aid','cochlear','stent','balloon','guidewire','sheath','mesh','suture','stapler','staple','skin closure','wound closure','tissue adhesive','glue','haemostat','sealant','dressing','foam','hydrocolloid','alginate','hydrofiber','silver','collagen','honey','barrier film','film dressing','bandage','compression','tape','plaster','npwt','negative pressure','wound','glove','gown','drape','wipe','sanitiser','irrigation','ventilator','anaesthesia','laryngoscope','airway','tracheostomy','tracheal','bronchoscope','endoscope','colonoscope','gastroscope','scope','infusion pump','syringe pump','pump','syringe','needle','lancet','connector','stopcock','extension set','giving set','iv set','flush','implant','knee','hip','shoulder','robot','freezer','refrigerator','incubator','analyser','sequencer','defibrillator','monitor','ultrasound','mri','ct scan','x-ray','mammography','bed','mattress','hoist','sling','wheelchair','cushion','dialyser','dialysis','apheresis','linac','brachytherapy','pacemaker','ablation','tavi','biopsy','warmer','warming','securement','ostomy','urostomy','stoma','nephrostomy','foley','feeding','enteral','feeding tube','peg tube','slide sheet','glucose','sensor','test strip','electrode','scalpel','blade','forceps','retractor','trocar','clip','clamp','specimen','drainage','chest drain','suction','mask','circuit','cpap','oxygen','nebuliser','filter','lubricant'];
  var KEYPOINTS = {
    'BD — Becton, Dickinson': { 'nexiva': 'Closed IV system — fewer blood exposures/disconnections vs an open cannula', 'chloraprep': 'Licensed medicinal product (UK marketing authorisation) — 2% CHG / 70% IPA sterile applicator, indicated for skin disinfection before invasive procedures' },
    'GAMA Healthcare': { 'hexi-prep': 'Licensed medicine (PL 40867/0002) — sterile 2% CHG / 70% IPA pad; its indication covers invasive procedures NOT requiring a clean-air environment (vascular access focus, per GAMA\u2019s prescribing information)' },
    'PDI (EMEA)': { 'prevantics': '2% CHG / 70% IPA applicators (clear and tinted) — listed as a PT1 skin biocide in the UK; PDI\u2019s UK site states they are not intended for pre-surgical skin antisepsis' },
    'Coloplast': { 'speedicath': 'Ready-to-use hydrophilic catheter — no water needed' },
    'Smith+Nephew': { 'pico': 'Single-use NPWT, no canister — NICE MTG43 evidence' },
    'GBUK Group': { 'pahacel': 'Oxidised regenerated cellulose (ORC) haemostat — same class as Surgicel; knit and fibrillar formats on NHS Supply Chain', 'surgiclean': 'Absorbable haemostat range alongside Pahacel' },
    'Johnson & Johnson MedTech': { 'surgicel': 'The established ORC haemostat brand (Ethicon)', 'spongostan': 'Absorbable porcine gelatin sponge', 'surgiflo': 'Flowable gelatin haemostatic matrix' },
    'Baxter Healthcare Ltd': { 'floseal': 'Flowable gelatin + thrombin haemostatic matrix', 'tisseel': 'Two-component fibrin sealant', 'hemopatch': 'Sealing haemostat patch' }
  };
  var ANGLE = {
    'Price / cost': 'Compare framework price (NHS Supply Chain, confirmed) and whole-life cost, then link it to the trust’s own savings target (their latest annual report) and build the number in the Value Case Calculator.',
    'Value & capacity': 'Frame it as value-based procurement (save AND deliver value). Quantify the capacity/outcome gain in the Value Case Calculator, not as a features list.',
    'Clinical evidence': 'Put the published evidence side by side (NICE, trials) and cite it; where you have evidence they don’t, lead with it and offer a trial.',
    'Sustainability': 'Compare carbon and reusable-vs-single-use whole-life impact; bring your Carbon Reduction Plan (Evergreen scored at tender from Apr 2026); frame value as patient, planet and public purse.',
    'Objection handling (MSTP)': 'MSTP'
  };

  MOUNT.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:' + INK + ';padding:6px 0;">Loading comparison tool…</div>';
  Promise.all([
    fetch(IDX).then(function(r){return r.json();}),
    fetch(CFG).then(function(r){return r.json();}),
    fetch(SEED).then(function(r){return r.json();}).catch(function(){return {suppliers:[]};}),
    fetch(NHSSC).then(function(r){return r.json();}).catch(function(){return {products:{}};}),
    fetch(RANGEURL).then(function(r){return r.json();}).catch(function(){return {suppliers:{}};})
  ]).then(function(res){ RANGE = (res[4] && res[4].suppliers) || {}; render(res[0], res[1], res[2], res[3]); })
    .catch(function(){ MOUNT.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:#8a6d00;">Comparison tool temporarily unavailable — please try again shortly.</div>'; });

  function render(index, cfg, seed, nhssc){
    var suppliers = (index && index.suppliers) || [];
    var seedMap = {}; ((seed && seed.suppliers) || []).forEach(function(s){ seedMap[s.name] = s; });
    suppliers.forEach(function(s){ var sd = seedMap[s.name]; if (sd){ ['voice','products','frameworks','specialities'].forEach(function(k){ if (sd[k] && (!Array.isArray(sd[k]) || sd[k].length)) s[k] = sd[k]; });
      // alerts: union of curated seed + auto-detected index, deduped by url/title
      if (sd.alerts && sd.alerts.length){ var seenA = {}, mergedA = []; sd.alerts.concat(s.alerts || []).forEach(function(a){ var kk = String(a.url || a.title || '').toLowerCase(); if (kk && seenA[kk]) return; seenA[kk] = 1; mergedA.push(a); }); s.alerts = mergedA; } } });
    var have = {}; suppliers.forEach(function(s){ have[s.name] = 1; });
    ((seed && seed.suppliers) || []).forEach(function(s){ if (!have[s.name]){ s.curated = true; suppliers.push(s); } });

    // Live NHSSC detail cache, keyed by normalised product name.
    var CACHE = {}; var cp = (nhssc && nhssc.products) || {};
    for (var k in cp){ CACHE[nk(k)] = cp[k]; }
    // Products verified as NOT catalogue lines (capital equipment, software,
    // medicines-route etc.) — shown honestly instead of a dead-end lookup link.
    var NOTCAT = {}; var ncp = (nhssc && nhssc.notCatalogue) || {};
    for (var k2 in ncp){ NOTCAT[nk(k2)] = ncp[k2]; }
    function detailFor(prod){ return CACHE[nk(prod.name)] || null; }
    function liveItem(d){ if (!d || !d.items || !d.items.length) return null; for (var i=0;i<d.items.length;i++){ if (!d.items[i].status) return d.items[i]; } return d.items[0]; }

    // Flatten to a product index.
    var PRODUCTS = [];
    var seenProd = {};
    suppliers.forEach(function(s){
      (s.products || []).forEach(function(p){
        var name = typeof p === 'string' ? p : (p && p.name);
        if (!name) return;
        seenProd[s.name + '|' + nk(name)] = 1;
        PRODUCTS.push({ name: name, code: (p && p.code) || '', supplier: s.name, specs: s.specialities || [], framework: (s.frameworks && s.frameworks[0] && s.frameworks[0].name) || '', fwDates: (s.frameworks && s.frameworks[0] && s.frameworks[0].dates) || '', voice: s.voice, type: typeForProduct(name) });
      });
    });

    /* THE COMPANY'S OWN RANGE, ON TOP OF THE PROCUREMENT RECORD.
       The lists above are what the procurement record names — framework awards
       and catalogue lines — and for a big supplier that is a fraction of what
       they sell: the index knows 45 GBUK products against the 343 on GBUK's own
       site. A rep whose product was not in that 45 could not pick it, which made
       the tool look broken for the exact person it is for.

       These are marked `fromRange` and stay marked all the way to the result,
       because they are a WEAKER fact than a catalogue line. They came off the
       company's own website, so they prove the company sells it and prove
       nothing whatever about NHS Supply Chain. The Differential already prints
       "not stated in the catalogue entry" for anything the catalogue does not
       cover, so a range product degrades honestly instead of inventing detail.

       Never overrides: a product already known from the procurement record keeps
       that provenance. */
    var rangeAdded = 0;
    (function(){
      var byKey = {};
      for (var k in RANGE){
        var r = RANGE[k];
        var keys = [k].concat(r.aliases || []);
        for (var i = 0; i < keys.length; i++){ byKey[nk(keys[i])] = r; }
      }
      suppliers.forEach(function(s){
        var r = byKey[nk(s.name)];
        if (!r){
          var al = s.aliases || [];
          for (var i = 0; i < al.length && !r; i++){ r = byKey[nk(al[i])]; }
        }
        if (!r) return;
        (r.products || []).forEach(function(p){
          var name = p && p.n;
          if (!name || seenProd[s.name + '|' + nk(name)]) return;
          seenProd[s.name + '|' + nk(name)] = 1;
          rangeAdded++;
          PRODUCTS.push({ name: name, code: '', supplier: s.name, specs: s.specialities || [],
            framework: '', fwDates: '', voice: s.voice, type: typeForProduct(name),
            fromRange: true, division: p.division || '', rangeCategory: p.category || '' });
        });
      });
    })();
    function typeOf(n){ n = (n||'').toLowerCase(); for (var i=0;i<TYPES.length;i++){ if (n.indexOf(TYPES[i]) !== -1) return TYPES[i].trim(); } return ''; }
    // Type from the product name; if the name has no category word, fall back to the
    // real NHS Supply Chain catalogue description (e.g. "Intermittent Catheter…",
    // "IV Cannula…") so cached products still match like-for-like.
    function typeForProduct(name){
      var t = typeOf(name);
      if (!t){ var d = CACHE[nk(name)]; if (d && d.items){ for (var i = 0; i < d.items.length && !t; i++){ t = typeOf(d.items[i].desc || ''); } } }
      return t;
    }
    function kp(prod){ var m = KEYPOINTS[prod.supplier]; if (!m) return ''; var n = prod.name.toLowerCase(); for (var k in m){ if (n.indexOf(k) !== -1) return m[k]; } return ''; }

    // Outside margin so the tool doesn't run to the edge of the page (Lou, 06/08/2026).
    var wrap = el('div', 'font-family:Inter,system-ui,sans-serif;color:' + INK + ';padding:0 clamp(10px,3vw,34px);box-sizing:border-box;');
    wrap.appendChild(el('div', 'text-transform:uppercase;letter-spacing:2px;font-size:11px;font-weight:700;color:' + OX + ';', 'Medical Sales Intelligence Hub'));
    wrap.appendChild(el('div', 'font-size:24px;font-weight:800;margin:2px 0 4px;', 'The Differential'));
    wrap.appendChild(el('div', 'font-size:14px;line-height:1.6;color:#4a5766;max-width:760px;margin-bottom:12px;', 'Pick your <strong>speciality</strong>, then your company and product on the left. On the right, tell us who you’re up against — a specific rival if you know one, or leave it blank and we’ll suggest your closest tracked match. You get the two <strong>side by side</strong>: real NHS Supply Chain images and codes, their catalogue facts lined up, what actually differs, and the questions to ask in the room.'));

    // Search flow: 1 Speciality -> 2 Company (only firms indexed in that
    // speciality) -> 3 Product type -> 4 product name OR NHSSC code (YOUR product), then a
    // second, explicit "Compare against" product -> Compare.
    var SUPOBJ = {}; suppliers.forEach(function(s){ SUPOBJ[s.name] = s; });
    var SPECMAP = {
      'vascular access': ['cannula','picc','midline','catheter','connector','flush','securement','needle','syringe','extension set','giving set','iv set','stopcock','infusion pump','syringe pump','pump','antisepsis','antiseptic','skin prep','skin disinfect','applicator','swabstick','swab','tourniquet','blood culture'],
      'wound care': ['dressing','foam','hydrocolloid','alginate','hydrofiber','silver','collagen','honey','barrier film','film dressing','bandage','compression','npwt','negative pressure','wound','tape','plaster','sealant'],
      'surgical haemostasis': ['haemostat','sealant','suture','stapler','staple','skin closure','wound closure','tissue adhesive','glue'],
      'enteral feeding': ['enteral','feeding','feeding tube','peg tube','syringe','connector'],
      'patient handling': ['slide sheet','sling','hoist','bed','mattress','cushion','wheelchair'],
      'continence': ['catheter','ostomy','urostomy','stoma','foley','nephrostomy','drainage'],
      'ophthalmology': ['iol','intraocular','phaco'],
      'diabetes': ['glucose','sensor','test strip','lancet','needle','pump'],
      'surgery / theatres': ['suture','stapler','staple','haemostat','sealant','drape','gown','glove','scalpel','blade','forceps','retractor','trocar','clip','clamp','mesh','skin closure','tissue adhesive','electrode','suction','warming','warmer','scope','endoscope']
    };
    /* THE TWO SIDES, SIDE BY SIDE — in the form as well as the result.
       Lou, 06/08/2026: the form stacked "your product" above "compare against",
       so the two things being compared never sat alongside each other until
       after you pressed Compare. They are now two columns, colour-coded, and
       THE SAME TWO COLOURS CARRY THROUGH TO EVERY PANEL OF THE RESULT —
       oxblood is always yours, slate is always theirs. Deliberately not
       red-vs-green: the competitor is not the villain, and a rep who is shown
       one is a rep who badmouths one. */
    var twoCol = el('div', 'display:flex;flex-wrap:wrap;gap:12px;margin-bottom:10px;align-items:stretch;');

    var colMine = el('div', 'flex:1 1 300px;min-width:0;background:' + MINE_BG + ';border:1px solid ' + MINE_C + ';border-top:3px solid ' + MINE_C + ';border-radius:10px;padding:12px;');
    colMine.appendChild(el('div', 'font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;color:' + MINE_C + ';margin:0 0 9px;', 'Your product'));
    var bar = el('div', 'display:flex;flex-direction:column;gap:10px;');
    var supNames0 = [], supSeen0 = {};
    PRODUCTS.forEach(function(p){ if (!supSeen0[p.supplier]){ supSeen0[p.supplier] = 1; supNames0.push(p.supplier); } });
    function byLower(a, b){ return a.toLowerCase() < b.toLowerCase() ? -1 : 1; }
    supNames0.sort(byLower);
    /* SPECIALITY FIRST, THEN COMPANY (Lou, 11/08/2026). Step 1 used to be a
       list of every tracked supplier, and the speciality was whatever that one
       firm happened to sell into. A rep comes at this from the clinical area,
       so the area is asked for first and the company list is cut to the firms
       actually indexed in it. Both sides are built from PRODUCTS, so the picker
       can never offer a speciality/company pair with nothing behind it. */
    var SPEC_COS = {}, ALLSPECS = [];
    PRODUCTS.forEach(function(p){
      (p.specs || []).forEach(function(sp){
        if (!sp) return;
        if (!SPEC_COS[sp]){ SPEC_COS[sp] = {}; ALLSPECS.push(sp); }
        SPEC_COS[sp][p.supplier] = 1;
      });
    });
    ALLSPECS.sort(byLower);
    function companiesIn(spec){
      if (!spec || !SPEC_COS[spec]) return supNames0.slice();
      return Object.keys(SPEC_COS[spec]).sort(byLower);
    }
    var selSpec = mkSelect('1 · Speciality', [''].concat(ALLSPECS));
    var selSup = mkSelect('2 · Company', [''].concat(supNames0));
    var selType = mkSelect('3 · Product type', ['']); selType.sel.disabled = true;
    var pbox = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:0;');
    pbox.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', '4 · Product name or NHSSC code'));
    var inp = el('input', 'padding:10px 12px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;background:#fff !important;color:#20303f !important;'); inp.type='text'; inp.setAttribute('list','msh-prod-list'); inp.placeholder='e.g. Pahacel — or a code like ELS924';
    var dl = el('datalist'); dl.id='msh-prod-list';
    pbox.appendChild(inp); pbox.appendChild(dl);
    bar.appendChild(selSpec.box); bar.appendChild(selSup.box); bar.appendChild(selType.box); bar.appendChild(pbox);
    colMine.appendChild(bar);

    /* Explicit "compare against" product — the fix for the tool silently
       auto-picking a rival with no way to name one. Left blank, it still falls
       back to the closest tracked match (see updateSuggestPlaceholder /
       runCompare below) so the tool never dead-ends a rep who doesn't know
       exactly who they're up against. */
    var colTheirs = el('div', 'flex:1 1 300px;min-width:0;background:' + THEIR_BG + ';border:1px solid ' + THEIR_C + ';border-top:3px solid ' + THEIR_C + ';border-radius:10px;padding:12px;');
    colTheirs.appendChild(el('div', 'font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;color:' + THEIR_C + ';margin:0 0 9px;', 'Their product'));
    var bar2 = el('div', 'display:flex;flex-direction:column;gap:10px;');
    var selSup2 = mkSelect('Their company (optional)', [''].concat(supNames0));
    var pbox2 = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:0;');
    pbox2.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', 'Their product name or NHSSC code'));
    var inp2 = el('input', 'padding:10px 12px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;background:#fff !important;color:#20303f !important;'); inp2.type='text'; inp2.setAttribute('list','msh-prod-list2'); inp2.placeholder='type a specific rival product or code (optional — we’ll suggest one)';
    var dl2 = el('datalist'); dl2.id='msh-prod-list2';
    pbox2.appendChild(inp2); pbox2.appendChild(dl2);
    bar2.appendChild(selSup2.box); bar2.appendChild(pbox2);
    bar2.appendChild(el('div', 'font-size:11.5px;color:#5f6b74;line-height:1.5;margin-top:2px;', 'Leave blank and we’ll pick your closest tracked match.'));
    colTheirs.appendChild(bar2);

    twoCol.appendChild(colMine); twoCol.appendChild(colTheirs);
    wrap.appendChild(twoCol);

    /* COVERAGE, STATED HONESTLY. Lou asked for a line saying the tool "only
       compares products on framework". It does not, and saying so would
       misdescribe it: PRODUCTS is built from each tracked supplier's own indexed
       range, and the framework shown against a product is merely that supplier's
       FIRST framework — many entries are on no framework at all, and some tracked
       suppliers hold none. So this says what is actually true, and offers the same
       way out: ask, and it gets added. */
    var askSub = encodeURIComponent('Product request — Medical Sales Intelligence Hub');
    var askBody = encodeURIComponent('Please add this to the comparison tool:\n\nProduct:\nCompany:\nSpeciality / what it is:\nA link if you have one:\n');
    var cov = el('div', 'font-size:12.5px;line-height:1.6;color:#6b7684;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:9px;padding:9px 13px;margin:0 0 12px;');
    cov.innerHTML = 'These dropdowns cover the <strong>' + PRODUCTS.length.toLocaleString('en-GB') + ' products indexed across ' + Object.keys(SUPOBJ).length + ' tracked suppliers</strong> — not the whole market. '
      + (rangeAdded ? '<strong>' + (PRODUCTS.length - rangeAdded).toLocaleString('en-GB') + '</strong> come from the procurement record — framework awards and NHS Supply Chain catalogue lines. The other <strong>' + rangeAdded.toLocaleString('en-GB') + '</strong> come from four suppliers’ own product websites, are marked <em>company’s own range</em> wherever they appear, and prove only that the company sells the item: they say nothing about NHS Supply Chain. ' : '')
      + 'A product that is missing is <strong>not yet indexed</strong>, not "nothing found". '
      + '<a href="mailto:louisehoult@elevateandthrive.uk?subject=' + askSub + '&body=' + askBody + '" style="color:' + GOLD + ';font-weight:600;">Ask for something to be added &rarr;</a> '
      + '<span style="color:#8a8778;">— usually live within a working day.</span>';
    wrap.appendChild(cov);
    /* Two speciality filters, and they do different jobs. SPECMAP narrows by
       DEVICE TYPE and covers nine specialities; inSpec narrows to the products
       of suppliers indexed in the speciality and covers all of them. With
       speciality now the first question, the second matters most — without it,
       picking a speciality outside SPECMAP's nine narrowed nothing at all and
       the type list still ran to every type on the Hub. */
    function inSpec(p, spec){ return !spec || (p.specs || []).indexOf(spec) !== -1; }
    function rawTypesFor(sup, spec){
      var allowed = spec ? SPECMAP[spec.toLowerCase()] : null;
      var seenT = {}, out = [];
      PRODUCTS.forEach(function(p){
        if (sup && p.supplier !== sup) return;
        if (!inSpec(p, spec)) return;
        if (!p.type) return;
        if (allowed && allowed.indexOf(p.type) === -1) return;
        if (!seenT[p.type]){ seenT[p.type] = 1; out.push(p.type); }
      });
      out.sort(); return out;
    }
    function subset(){
      var sup = selSup.sel.value, spec = selSpec.sel.value, typ = selType.sel.value;
      var allowed = (spec && !typ) ? SPECMAP[spec.toLowerCase()] : null;
      return PRODUCTS.filter(function(p){
        if (sup && p.supplier !== sup) return false;
        if (!inSpec(p, spec)) return false;
        if (typ && p.type !== typ) return false;
        if (allowed && p.type && allowed.indexOf(p.type) === -1) return false;
        return true;
      });
    }
    function refreshList(){
      dl.innerHTML = '';
      var seenO = {};
      subset().slice(0, 500).forEach(function(p){ var v = p.name + '  ·  ' + p.supplier; if (!seenO[v]){ seenO[v] = 1; var o = el('option'); o.value = v; dl.appendChild(o); } });
    }
    function fillSel(sel, opts, labelFn){
      sel.innerHTML = '';
      var o0 = el('option'); o0.value = ''; o0.textContent = '— all —'; sel.appendChild(o0);
      opts.forEach(function(o){ var op = el('option'); op.value = o; op.textContent = labelFn ? labelFn(o) : o; sel.appendChild(op); });
    }
    // "Compare against" datalist + placeholder — mirrors refreshList() above but
    // for the explicit second product, scoped to the same device type as "your
    // product" once resolved (and defaulting to "not your own supplier").
    function resolveByCodeOrName(v, pool){
      if (!v) return null;
      var code = v.toUpperCase().replace(/[^A-Z0-9]/g, '');
      if (code.length >= 4 && /\d/.test(code)){
        for (var ck in cp){
          if ((cp[ck].items || []).some(function(it){ return it.npc === code || it.mpc === code; })){
            var m = PRODUCTS.filter(function(p){ return nk(p.name) === nk(ck); })[0];
            if (m) return m;
          }
        }
      }
      function find(list){
        return list.filter(function(p){ return (p.name+'  ·  '+p.supplier) === v; })[0]
            || list.filter(function(p){ return p.name.toLowerCase() === v.toLowerCase(); })[0]
            || list.filter(function(p){ return v && p.name.toLowerCase().indexOf(v.toLowerCase()) !== -1; })[0];
      }
      return find(pool) || find(PRODUCTS);
    }
    function resolveMine(){
      var v = inp.value.trim();
      var pool = subset();
      var m = resolveByCodeOrName(v, pool);
      if (!m && !v && pool.length && pool.length <= 1) m = pool[0];
      return m;
    }
    function updateSuggestPlaceholder(){
      var mine = resolveMine();
      if (mine){
        var comps = competitorsOf(mine);
        inp2.placeholder = comps.length ? ('e.g. ' + comps[0].name + '  ·  ' + comps[0].supplier) : 'type a specific rival product or code';
      } else {
        inp2.placeholder = 'type a specific rival product or code (optional — we’ll suggest one)';
      }
    }
    /* THEIRS = ACTUAL COMPETITORS ONLY. Lou, 06/08/2026: picking a rival company
       used to list that company's WHOLE range, because a chosen supplier returned
       early and skipped the device-type test. Comparing a haemostat and selecting
       Johnson & Johnson offered CARTO 3, VARIPULSE, Impella and Monarch — ablation
       catheters and a surgical robot. The type test now applies whether or not a
       supplier has been picked, so the list only ever holds things that could
       genuinely compete with the product on the left. */
    function rivalsOf(mine, supFilter){
      return PRODUCTS.filter(function(p){
        if (mine && p.supplier === mine.supplier) return false;      // never your own range
        if (supFilter && p.supplier !== supFilter) return false;
        if (mine && mine.type && p.type && p.type !== mine.type) return false;
        if (mine && mine.type && !p.type) return false;              // untyped can't be shown to compete
        return true;
      });
    }
    function refreshList2(){
      dl2.innerHTML = '';
      var mine = resolveMine();
      var seenO = {};
      rivalsOf(mine, selSup2.sel.value).slice(0, 500).forEach(function(p){
        var v = p.name + '  ·  ' + p.supplier;
        if (!seenO[v]){ seenO[v] = 1; var o = el('option'); o.value = v; dl2.appendChild(o); }
      });
      refreshRivalCompanies(mine);
    }
    /* And the company list on the right is rebuilt from those rivals, so it holds
       only suppliers that actually offer something comparable — not all 345. */
    function refreshRivalCompanies(mine){
      var keep = selSup2.sel.value;
      var names = {}, out = [];
      rivalsOf(mine, '').forEach(function(p){ if (!names[p.supplier]){ names[p.supplier] = 1; out.push(p.supplier); } });
      out.sort(function(a, b){ return a.toLowerCase() < b.toLowerCase() ? -1 : 1; });
      var lbl = selSup2.box.querySelector('label');
      if (lbl) lbl.textContent = mine && mine.type
        ? ('Their company — ' + out.length + ' with a ' + mine.type)
        : 'Their company (optional)';
      selSup2.sel.innerHTML = '';
      var o0 = el('option'); o0.value = ''; o0.textContent = '— any competitor —'; selSup2.sel.appendChild(o0);
      out.forEach(function(n){ var o = el('option'); o.value = n; o.textContent = n; selSup2.sel.appendChild(o); });
      // Keep the rep's choice if it still competes; otherwise fall back to "any".
      selSup2.sel.value = (keep && out.indexOf(keep) !== -1) ? keep : '';
    }
    function capType(t){ return t.charAt(0).toUpperCase() + t.slice(1); }
    /* Step 1 -> 2. The company list is re-cut to the speciality every time, and
       a company already chosen is kept only if it survives the cut — leaving a
       firm selected that sells nothing in the new speciality is how the product
       list silently empties with no reason on screen. */
    selSpec.sel.addEventListener('change', function(){
      var spec = selSpec.sel.value, keep = selSup.sel.value;
      var cos = companiesIn(spec);
      fillSel(selSup.sel, cos);
      selSup.sel.value = (keep && cos.indexOf(keep) !== -1) ? keep : '';
      var lbl = selSup.box.querySelector('label');
      if (lbl) lbl.textContent = spec ? ('2 · Company — ' + cos.length + ' in this speciality') : '2 · Company';
      fillSel(selType.sel, rawTypesFor(selSup.sel.value, spec), capType);
      selType.sel.disabled = false;
      refreshList();
      refreshList2();
      updateSuggestPlaceholder();
    });
    selSup.sel.addEventListener('change', function(){
      fillSel(selType.sel, rawTypesFor(selSup.sel.value, selSpec.sel.value), capType);
      selType.sel.disabled = false;
      refreshList();
      refreshList2();
      updateSuggestPlaceholder();
    });
    selType.sel.addEventListener('change', function(){ refreshList(); refreshList2(); updateSuggestPlaceholder(); });
    inp.addEventListener('input', function(){ refreshList2(); updateSuggestPlaceholder(); });
    selSup2.sel.addEventListener('change', refreshList2);
    refreshList();
    refreshList2();
    updateSuggestPlaceholder();

    // Your edge: the reason the trust would switch — the case builder leads with this.
    var opt = el('div', 'display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin:-6px 0 14px;padding-left:2px;');
    var ebox = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:300px;flex:2;');
    ebox.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', 'Your edge — what are you giving them? (recommended)'));
    var edgeInp = el('input', 'padding:9px 12px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13.5px;background:#fff !important;color:#20303f !important;');
    edgeInp.type = 'text'; edgeInp.placeholder = 'e.g. 15% saving vs incumbent · next-day supply · on-site training · UK stockholding';
    ebox.appendChild(edgeInp); opt.appendChild(ebox);
    var selAng = mkSelect('Objection / angle (optional)', ['', 'Price / cost', 'Value & capacity', 'Clinical evidence', 'Sustainability', 'Objection handling (MSTP)']);
    opt.appendChild(selAng.box); wrap.appendChild(opt);

    // Optional prices: reps often don't have them — when they do, the savings
    // calculation becomes the number for procurement.
    var priceRow = el('div', 'display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin:-6px 0 14px;padding:10px 12px;background:' + SOFT + ';border:1px dashed ' + LINE + ';border-radius:10px;');
    priceRow.appendChild(el('div', 'flex-basis:100%;font-size:12.5px;font-weight:700;color:#5a6470;', 'Do you know the current prices? If so, add them and the savings are calculated below. (optional — leave blank if not)'));
    function mkNum(label, ph, width){
      var box = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:' + width + 'px;');
      box.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#9a958a;', esc(label)));
      var inpN = el('input', 'padding:9px 12px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13.5px;background:#fff !important;color:#20303f !important;');
      inpN.type = 'text'; inpN.inputMode = 'decimal'; inpN.placeholder = ph;
      box.appendChild(inpN); return { box: box, inp: inpN };
    }
    var pMine = mkNum('Your price per unit (\u00a3)', 'e.g. 0.85', 170);
    var pTheirs = mkNum('Their price per unit (\u00a3)', 'incumbent / competitor', 170);
    var pVol = mkNum('Units the hospital buys per year', 'e.g. 20000', 220);
    priceRow.appendChild(pMine.box); priceRow.appendChild(pTheirs.box); priceRow.appendChild(pVol.box);
    wrap.appendChild(priceRow);
    var btnRow = el('div', 'margin:-4px 0 14px;');
    var btn = el('button', 'background:#6B2A34 !important;color:#ffffff !important;border:0;border-radius:8px;padding:12px 28px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.3px;box-shadow:0 1px 3px rgba(0,0,0,.15);', 'Compare');
    btnRow.appendChild(btn);
    wrap.appendChild(btnRow);
    function numOf(inpEl){ var v = parseFloat(String(inpEl.inp.value).replace(/[\u00a3,\s]/g, '')); return (isFinite(v) && v > 0) ? v : null; }
    function mkSelect(label, opts){
      var box = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:210px;');
      box.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#9a958a;', esc(label)));
      var sel = el('select', 'padding:9px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13.5px;background:#ffffff !important;color:#20303f !important;');
      opts.forEach(function(o){ var op = el('option'); op.value = o; op.textContent = o || '— none —'; sel.appendChild(op); });
      box.appendChild(sel); return { box: box, sel: sel };
    }

    var out = el('div', 'margin-top:6px;'); out.id='msh-compare-out'; wrap.appendChild(out);
    MOUNT.innerHTML = ''; MOUNT.appendChild(wrap);

    function runCompare(theirsOverride){
      if (theirsOverride != null) inp2.value = theirsOverride;
      var typedMine = inp.value.trim();
      var typedTheirs = inp2.value.trim();
      var mine = resolveMine();
      var theirs = null, autoSuggested = false;
      if (mine){
        if (typedTheirs){
          var pool2 = PRODUCTS.filter(function(p){ return !selSup2.sel.value || p.supplier === selSup2.sel.value; });
          theirs = resolveByCodeOrName(typedTheirs, pool2);
        }
        if (!theirs && !typedTheirs){
          var comps0 = competitorsOf(mine);
          if (comps0.length){ theirs = comps0[0]; autoSuggested = true; }
        }
      }
      out.innerHTML = compare(mine, theirs, selAng.sel.value, edgeInp.value.trim(), typedMine, selSup.sel.value, typedTheirs, selSup2.sel.value, autoSuggested);
      addCopy(out);
      var hb = out.querySelector('#msh-handoff');
      if (hb){
        hb.addEventListener('click', function(){
          var payload = { company: hb.getAttribute('data-supplier'), product: hb.getAttribute('data-product'), edge: edgeInp.value.trim(), ts: Date.now() };
          try { localStorage.setItem('mshPrepHandoff', JSON.stringify(payload)); } catch(e){}
          try { window.dispatchEvent(new CustomEvent('msh-prep-handoff', { detail: payload })); } catch(e){}
        });
      }
      out.querySelectorAll('.msh-cmp-other').forEach(function(a){
        a.addEventListener('click', function(ev){
          ev.preventDefault();
          runCompare(a.getAttribute('data-name') + '  ·  ' + a.getAttribute('data-supplier'));
        });
      });
      out.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    btn.addEventListener('click', function(){ runCompare(); });

    function link(text, id){ return '<a href="/?page_id=' + id + '" style="color:' + GOLD + ';font-weight:600;">' + text + '</a>'; }
    function lookupUrl(name){ return 'https://pilot.supplychain.nhs.uk/search?query=' + encodeURIComponent(String(name).replace(/\s*\(.*?\)\s*/g,' ').trim()); }
    var GENERIC_WORDS = { 'system':1,'safety':1,'products':1,'medical':1,'range':1,'solution':1,'solutions':1,'products':1,'closed':1,'sterile':1,'single':1,'device':1,'plus':1,'ultra':1,'flex':1,'select':1,'advance':1,'advanced':1 };
    function sigTokens(name){
      return (String(name).toLowerCase().match(/[a-z]{5,}/g) || []).filter(function(w){ return !GENERIC_WORDS[w]; });
    }
    function specOverlap(a, b){ var n = 0; (a || []).forEach(function(x){ if ((b || []).indexOf(x) !== -1) n++; }); return n; }
    // Like-for-like: same device TYPE (category) only. Speciality is used to RANK
    // within the same type, never to pull in unrelated categories. If the product
    // has no recognised type, fall back to a shared distinctive product-name word.
    function competitorsOf(mine){
      var seen = {}, out = [];
      function add(p){ var k = p.name + '|' + p.supplier; if (p.supplier !== mine.supplier && !seen[k]){ seen[k] = 1; out.push(p); } }
      if (mine.type){
        var same = PRODUCTS.filter(function(p){ return p.supplier !== mine.supplier && p.type === mine.type; });
        // Rank the closest like-for-like first: overlap of 8-char word stems from the
        // product name + its live catalogue description (e.g. Pahacel [ORC] ranks
        // Surgicel [ORC] above a flowable matrix), then cached detail, then speciality.
        function stems(p){
          var d = CACHE[nk(p.name)];
          var txt = p.name + ' ' + ((d && d.items && d.items[0] && d.items[0].desc) || '');
          var out = {}; (txt.toLowerCase().match(/[a-z]{5,}/g) || []).forEach(function(w){ out[w.slice(0, 8)] = 1; });
          return out;
        }
        var myStems = stems(mine);
        function score(p){
          var n = 0, s = stems(p);
          for (var k in s){ if (myStems[k]) n++; }
          return n * 10 + (detailFor(p) ? 5 : 0) + specOverlap(mine.specs, p.specs);
        }
        same.sort(function(a, b){ return score(b) - score(a); });
        same.forEach(add);
      } else {
        var mt = sigTokens(mine.name);
        if (mt.length){
          PRODUCTS.forEach(function(p){
            if (p.supplier === mine.supplier) return;
            if (sigTokens(p.name).some(function(w){ return mt.indexOf(w) !== -1; })) add(p);
          });
        }
      }
      return out.slice(0, 12);
    }

    function thumbImg(d, px){
      var it = d && d.items && d.items.filter(function(x){ return x.img; })[0];
      if (!it) return '';
      return '<img src="' + esc(it.img) + '" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display=\'none\'" style="width:' + px + 'px;height:' + px + 'px;object-fit:contain;background:#fff;border:1px solid ' + LINE + ';border-radius:6px;flex:0 0 auto;">';
    }

    // Supplier frameworks are supplier-level facts; only attribute one to a product
    // when the product's own category appears in the framework name — never imply a
    // haemostat is "on" the supplier's cannula framework.
    function fwFor(p){
      if (!p.framework) return '';
      var f = p.framework.toLowerCase();
      if (p.type && f.indexOf(p.type) !== -1) return p.framework;
      var toks = (p.name.toLowerCase().match(/[a-z]{5,}/g) || []);
      for (var i = 0; i < toks.length; i++){ if (f.indexOf(toks[i]) !== -1) return p.framework; }
      return '';
    }
    function row(p, mine){
      var hl = mine ? 'background:#fbeef0;font-weight:600;' : '';
      var kpt = kp(p);
      var d = detailFor(p);
      var li = liveItem(d);
      var prodCell = '<div style="display:flex;align-items:center;gap:8px;">' + thumbImg(d, 30) + '<span>' + esc(p.name) + (mine ? ' <span style="color:' + OX + ';font-size:11px;">(you)</span>' : '') + '</span></div>';
      var codeCell;
      if (li){
        codeCell = '<span style="font-family:ui-monospace,Menlo,monospace;font-size:12px;">NPC ' + esc(li.npc) + (li.mpc ? ' · ' + esc(li.mpc) : '') + '</span>'
          + (d.items.length > 1 ? '<span style="color:#8a8778;font-size:11px;"> +' + (d.items.length - 1) + ' packs</span>' : '')
          + '<br><a href="' + lookupUrl(p.name) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-weight:600;font-size:11px;">all codes &#8599;</a>';
      } else if (p.code){
        codeCell = esc(p.code);
      } else if (NOTCAT[nk(p.name)]){
        codeCell = '<span style="color:#8a8778;font-size:11.5px;font-style:italic;">not a catalogue line — ' + esc(NOTCAT[nk(p.name)].reason) + '</span>';
      } else {
        codeCell = '<a href="' + lookupUrl(p.name) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-weight:600;">look up &#8599;</a>';
      }
      return '<tr style="' + hl + 'border-bottom:1px solid ' + LINE + ';vertical-align:top;">'
        + '<td style="padding:7px 9px;">' + prodCell + '</td>'
        + '<td style="padding:7px 9px;">' + esc(p.supplier) + '</td>'
        + '<td style="padding:7px 9px;color:#5a6470;font-size:12.5px;">' + (fwFor(p) ? esc(fwFor(p)) : '<span style="color:#8a8778;">—</span>') + '</td>'
        + '<td style="padding:7px 9px;color:#5a6470;">' + codeCell + '</td>'
        + '<td style="padding:7px 9px;color:#39424d;font-size:12.5px;">' + (kpt ? esc(kpt) : '<span style="color:#8a8778;">—</span>') + '</td></tr>';
    }

    function detailCard(p, mine){
      var d = detailFor(p); if (!d) return '';
      var items = d.items || []; if (!items.length) return '';
      var img = thumbImg(d, 74);
      var head = '<div style="display:flex;gap:12px;align-items:flex-start;">' + img
        + '<div style="min-width:0;"><div style="font-weight:800;font-size:14.5px;">' + esc(p.name) + (mine ? ' <span style="color:' + OX + ';font-size:11px;">(you)</span>' : '') + '</div>'
        + '<div style="font-size:12px;color:#6b7684;margin-top:1px;">' + esc(p.supplier) + '</div>'
        + '<div style="font-size:12.5px;color:#45505c;margin-top:4px;line-height:1.5;">' + esc(items[0].desc || '') + '</div></div></div>';
      var rows = items.slice(0,6).map(function(it){
        return '<tr style="border-top:1px solid ' + LINE + ';"><td style="padding:5px 8px;font-size:12px;color:#39424d;">' + esc(it.pack || '—') + '</td>'
          + '<td style="padding:5px 8px;font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:' + INK + ';">' + esc(it.npc) + (it.mpc ? ' <span style="color:#8a8778;">/ ' + esc(it.mpc) + '</span>' : '') + '</td>'
          + '<td style="padding:5px 8px;font-size:11px;">' + (it.status ? '<span style="color:#a24; font-weight:600;">' + esc(it.status) + '</span>' : '<span style="color:' + GRN + ';">live</span>') + '</td></tr>';
      }).join('');
      var table = '<div style="overflow-x:auto;margin-top:8px;"><table style="width:100%;border-collapse:collapse;min-width:320px;"><thead><tr style="text-align:left;color:#8a8778;font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;"><th style="padding:2px 8px;">Pack</th><th style="padding:2px 8px;">NPC / MPC</th><th style="padding:2px 8px;">Status</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
      var more = d.items.length > 6 ? '<div style="font-size:11px;color:#8a8778;margin-top:4px;">+' + (d.items.length - 6) + ' more packs — <a href="' + lookupUrl(p.name) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';">see all on NHS Supply Chain &#8599;</a></div>' : '';
      var bd = mine ? '2px solid ' + OX : '1px solid ' + LINE;
      return '<div style="background:#fff;border:' + bd + ';border-radius:10px;padding:12px 14px;">' + head + table + more + '</div>';
    }

    /* SIDE BY SIDE — yours and theirs, pictured, with their catalogue facts
       aligned so a rep reads ACROSS a row instead of holding two lists in their
       head. Added 06/08/2026: the head-to-head table put each product on its own
       ROW, which is the wrong axis for "what is actually different here", and the
       image was a 30px thumbnail.

       THE RULE THAT GOVERNS EVERY CELL: these attributes are derived from each
       product's own NHS Supply Chain catalogue description. An empty cell means
       THE CATALOGUE ENTRY DID NOT SAY SO — never that the product lacks the
       feature. Rendering silence as "no" would publish a false claim about
       somebody else's product on a paying page. It is also the whole reason this
       tool never reads as an attack: we state what each entry says, and let the
       difference speak. */
    var ATTRS = [
      { k: 'material',   label: 'Material' },
      { k: 'form',       label: 'Format' },
      { k: 'reg',        label: 'Regulatory status' },
      { k: 'latex',      label: 'Latex' },
      { k: 'silver',     label: 'Antimicrobial element', bool: true },
      { k: 'bloodctl',   label: 'Blood control',         bool: true },
      { k: 'needlefree', label: 'Needle-free connector',  bool: true },
      { k: 'tint',       label: 'Tinted',                 bool: true },
      { k: 'dehp',       label: 'DEHP present',           bool: true }
    ];
    var NOTSTATED = '<span style="color:#8a8778;font-style:italic;">not stated in the catalogue entry</span>';

    function bigImg(d){
      var it = d && d.items && d.items.filter(function(x){ return x.img; })[0];
      if (!it) return '<div style="height:150px;display:flex;align-items:center;justify-content:center;background:#faf8f3;border:1px dashed ' + LINE + ';border-radius:8px;color:#8a8778;font-size:12px;text-align:center;padding:0 10px;">No catalogue image held<br>for this line</div>';
      return '<a href="' + esc(it.img) + '" target="_blank" rel="noopener"><img src="' + esc(it.img) + '" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentNode.innerHTML=\'\'" style="width:100%;height:150px;object-fit:contain;background:#fff;border:1px solid ' + LINE + ';border-radius:8px;"></a>';
    }

    function sideCol(p, isMine){
      var d = detailFor(p);
      var li = liveItem(d);
      var C = isMine ? MINE_C : THEIR_C;
      var label = isMine ? 'YOURS' : 'THEIRS';
      var who = isMine ? esc(p.supplier) : esc(p.supplier);
      var tag = '<span style="background:' + C + ';color:#fff;font-size:10px;font-weight:700;letter-spacing:.08em;border-radius:99px;padding:2px 9px;">' + label + '</span>';
      var h = '<div style="flex:1 1 240px;min-width:0;background:' + (isMine ? MINE_BG : THEIR_BG) + ';border:1px solid ' + C + ';border-top:3px solid ' + C + ';border-radius:10px;padding:12px;">';
      h += '<div style="margin-bottom:8px;">' + tag + '</div>';
      h += bigImg(d);
      h += '<div style="font-weight:800;font-size:15px;margin-top:9px;line-height:1.35;">' + esc(p.name) + '</div>';
      h += '<div style="font-size:12px;color:#6b7684;margin-top:2px;">' + esc(p.supplier) + '</div>';
      /* PROVENANCE, ON THE PRODUCT ITSELF. A range product came off the
         company's own website, not the procurement record, and the coverage note
         above promises it is marked wherever it appears — so it is marked here,
         beside the name, not only in the small print. */
      if (p.fromRange){
        h += '<div style="margin-top:6px;font-size:11px;color:#6b7684;background:#fff;border:1px dashed ' + LINE + ';border-radius:7px;padding:4px 8px;line-height:1.45;">'
          + '<b>Company’s own range</b>' + (p.division ? ' &middot; ' + esc(p.division) : '')
          + '<br>From ' + esc(p.supplier) + '’s own website, not the NHS Supply Chain record. No catalogue line is claimed for it.</div>';
      }
      if (d && d.items && d.items[0] && d.items[0].desc){
        h += '<div style="font-size:12.5px;color:#45505c;margin-top:6px;line-height:1.5;">' + esc(d.items[0].desc) + '</div>';
      }
      if (li){
        h += '<div style="margin-top:8px;font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:' + INK + ';">NPC ' + esc(li.npc) + (li.mpc ? '<br><span style="color:#8a8778;">MPC ' + esc(li.mpc) + '</span>' : '') + '</div>';
        h += '<div style="font-size:11.5px;color:#5a6470;margin-top:4px;">' + (d.items.length) + ' pack variant' + (d.items.length === 1 ? '' : 's') + ' · ' +
          (d.items.some(function(it){ return it.status; })
            ? '<span style="color:#a24;font-weight:600;">a pack shows a status change</span>'
            : '<span style="color:' + GRN + ';">all live</span>') + '</div>';
        h += '<div style="margin-top:5px;"><a href="' + lookupUrl(p.name) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-weight:600;font-size:11.5px;">all codes on NHS Supply Chain &#8599;</a></div>';
      } else {
        h += '<div style="margin-top:8px;font-size:11.5px;color:#8a8778;">' +
          (NOTCAT[nk(p.name)] ? 'Not a catalogue line — ' + esc(NOTCAT[nk(p.name)].reason)
                              : 'No live catalogue detail held for this line yet.') + '</div>';
      }
      if (fwFor(p)) h += '<div style="margin-top:7px;font-size:11.5px;color:#5a6470;">On framework: ' + esc(fwFor(p)) + '</div>';
      return h + '</div>';
    }

    function sideBySide(mine, theirs, myA, theirA){
      var h = '<div style="display:flex;gap:12px;flex-wrap:wrap;margin:10px 0 0;">'
        + sideCol(mine, true) + sideCol(theirs, false) + '</div>';

      // Aligned attribute rows. A row is shown only when at least one side says
      // something — an all-silent row teaches nothing and pads the page.
      var rows = '';
      for (var i = 0; i < ATTRS.length; i++){
        var a = ATTRS[i];
        var mv = myA ? myA[a.k] : null, tv = theirA ? theirA[a.k] : null;
        if (!mv && !tv) continue;
        var mTxt, tTxt;
        if (a.bool){
          mTxt = mv ? 'Stated' : NOTSTATED;
          tTxt = tv ? 'Stated' : NOTSTATED;
        } else {
          mTxt = mv ? esc(mv) : NOTSTATED;
          tTxt = tv ? esc(tv) : NOTSTATED;
        }
        var differs = !!mv && !!tv && mv !== tv;
        var bg = differs ? 'background:#fbf6ec;' : '';
        rows += '<tr style="' + bg + 'border-top:1px solid ' + LINE + ';vertical-align:top;">'
          + '<td style="padding:7px 10px;font-size:12px;color:#6b7684;white-space:nowrap;">' + esc(a.label)
          + (differs ? ' <span title="These differ" style="color:' + OX + ';font-weight:700;">&#9670;</span>' : '') + '</td>'
          + '<td style="padding:7px 10px;font-size:12.5px;color:#39424d;' + (differs ? 'font-weight:600;' : '') + '">' + mTxt + '</td>'
          + '<td style="padding:7px 10px;font-size:12.5px;color:#39424d;' + (differs ? 'font-weight:600;' : '') + '">' + tTxt + '</td></tr>';
      }
      if (!rows){
        h += '<div style="margin-top:10px;font-size:13px;color:#39424d;background:#fff;border:1px solid ' + LINE + ';border-radius:10px;padding:12px 14px;">'
          + 'Neither catalogue entry states a material, format or regulatory detail we can line up, so there is no spec table to show. '
          + 'That is a gap in the published descriptions, not a finding about either product — compare on service, training, price and supply instead.</div>';
        return h;
      }
      h += '<div style="overflow-x:auto;margin-top:10px;"><table style="width:100%;border-collapse:collapse;min-width:420px;background:#fff;border:1px solid ' + LINE + ';border-radius:10px;">'
        + '<thead><tr style="text-align:left;background:' + SOFT + ';">'
        + '<th style="padding:8px 10px;font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:#8a8778;">What</th>'
        + '<th style="padding:8px 10px;font-size:11.5px;color:#fff;background:' + MINE_C + ';">' + esc(mine.name) + ' <span style="font-weight:400;opacity:.85;">(you)</span></th>'
        + '<th style="padding:8px 10px;font-size:11.5px;color:#fff;background:' + THEIR_C + ';">' + esc(theirs.name) + '</th></tr></thead><tbody>'
        + rows + '</tbody></table></div>'
        + '<div style="font-size:11.5px;color:#8a8778;margin-top:6px;">&#9670; marks a stated difference. Every cell is taken from that product&rsquo;s own NHS Supply Chain '
        + 'catalogue description &mdash; &ldquo;not stated&rdquo; means the entry is silent, <strong>not</strong> that the product lacks it. '
        + 'Confirm against the manufacturer&rsquo;s IFU before you quote anything clinically.</div>';
      return h;
    }

    /* PROBING QUESTIONS — derived from the differences actually found, not a
       generic list. This is the coaching half of the tool: the procurement lead
       Lou spoke to on 06/08/2026 described a rep who knew his product start to
       finish and asked her not one question, and left with no next step. Each
       question carries WHY it works, because a question a rep does not
       understand is a question they will not ask well. */
    function probingQuestions(mine, theirs, myA, theirA, theirAlerts, theirSuspended){
      var qs = [];
      qs.push({ q: 'What are you using for this today, and what made you standardise on it?',
                why: 'You cannot reframe a decision until you know what drove it. It also tells you whether you are talking to the person who made it.' });

      if (myA && theirA && myA.material && theirA.material && myA.material !== theirA.material){
        if (/porcine|animal/.test(theirA.material) && /plant|oxidised|chitosan/.test(myA.material)){
          qs.push({ q: 'How do you currently handle patients who decline an animal-derived product?',
                    why: 'Opens the difference without naming it as a fault. If they have no process, you have found a real gap rather than won an argument.' });
        } else {
          qs.push({ q: 'Does the material make a practical difference to your team in this procedure?',
                    why: 'Lets them tell you whether the spec difference matters here. Sometimes it does not — better you learn that than pitch into it.' });
        }
      }
      if (myA && theirA && myA.reg && theirA.reg && myA.reg !== theirA.reg){
        qs.push({ q: 'For this indication, does your policy require a licensed medicine or is a biocide accepted?',
                  why: 'A policy question, not a product claim. If their policy already answers it, the decision makes itself and you never had to criticise anything.' });
      }
      if (myA && theirA && myA.latex && theirA.latex && myA.latex !== theirA.latex){
        qs.push({ q: 'How does your latex policy apply in this category — for staff as well as patients?',
                  why: 'Latex policy is usually trust-wide and written down. If it applies here, that is their rule doing the work, not your pitch.' });
      }
      if (theirAlerts && theirAlerts.length){
        qs.push({ q: 'How are you covering the current notice on that line — and what is your fallback if it runs longer?',
                  why: 'Quote the official alert and stop. A live notice is a supply problem you can help with; treating it as ammunition is how you lose the account.' });
      }
      if (theirSuspended){
        qs.push({ q: 'Has availability on that code been steady for you recently?',
                  why: 'Lets them raise the supply issue themselves. Far stronger than you announcing it.' });
      }
      qs.push({ q: 'If we did nothing differently, what would this cost you over the next year — in money, time or incidents?',
                why: 'Builds the value case in their numbers, not yours. Everything you put in the Value Case Calculator should come from this answer.' });
      qs.push({ q: 'Who else would need to be comfortable before this could change?',
                why: 'Surfaces the stakeholders you have not met. Ask it early — finding out at the end that a committee sign-off exists is how deals stall.' });
      qs.push({ q: 'What would have to be true for you to trial an alternative?',
                why: 'Turns a no into a specification. Whatever they say is your actual close.' });

      return '<ol style="margin:6px 0 0;padding-left:20px;">' + qs.map(function(x){
        return '<li style="margin:0 0 9px;"><strong>' + esc(x.q) + '</strong>'
          + '<div style="font-size:12.5px;color:#6b7684;margin-top:2px;line-height:1.55;">' + esc(x.why) + '</div></li>';
      }).join('') + '</ol>';
    }

    function objection(mine, theirs){
      var edge = kp(mine) || (mine.voice && mine.voice.angle) || 'your product’s strength';
      var c = theirs ? theirs.name + ' (' + theirs.supplier + ')' : 'their current product';
      return 'Handle it the MSTP way — <strong>Acknowledge &rarr; Reframe &rarr; One more question</strong>:'
        + '<ul style="margin:4px 0 0;padding-left:18px;">'
        + '<li><strong>Acknowledge:</strong> “' + esc(c) + ' is a solid choice — I can see why you use it.”</li>'
        + '<li><strong>Reframe</strong> to your edge: ' + esc(edge) + (fwFor(mine) ? ' — and it’s on ' + esc(fwFor(mine)) + '.' : (detailFor(mine) ? ' — and it’s on the live NHS Supply Chain catalogue.' : '.')) + '</li>'
        + '<li><strong>One more question:</strong> think of one more question — your own, for this customer. What could you ask that moves them one step forward?</li>'
        + '</ul>';
    }

    function compare(mine, theirs, angle, edge, typedMine, chosenSupMine, typedTheirs, chosenSupTheirs, autoSuggested){
      if (!mine){
        if (typedMine){
          var mailSub = encodeURIComponent('Product request — Medical Sales Intelligence Hub');
          var mailBody = encodeURIComponent('Please add this product to the Product Comparison tool:\n\nProduct: ' + typedMine + '\nCompany: ' + (chosenSupMine || '(not selected)') + '\nAnything else useful (speciality, who sells it, a link):\n');
          return '<div style="background:#fbf3df;border:1px solid #e8d5a8;border-radius:10px;padding:14px 16px;font-size:14px;line-height:1.65;color:#7a5b14;">'
            + '<strong>“' + esc(typedMine) + '” isn’t tracked yet.</strong> Nothing here is guessed — products only appear once they’ve been verified against the live NHS Supply Chain catalogue and the suppliers’ own published information.'
            + '<div style="margin-top:8px;"><a href="mailto:louisehoult@elevateandthrive.uk?subject=' + mailSub + '&body=' + mailBody + '" style="display:inline-block;background:#6B2A34;color:#fff;border-radius:8px;padding:10px 18px;font-weight:700;font-size:13.5px;text-decoration:none;">Request this product &rarr;</a>'
            + '<span style="font-size:12.5px;color:#8a8778;margin-left:10px;">it goes through the same verification and is usually live within a working day</span></div></div>';
        }
        return '<div style="color:#8a6d00;font-size:14px;padding:8px 0;">Type your product above (start typing to pick from the list) and press Compare.</div>';
      }

      var allComps = competitorsOf(mine);

      if (!theirs){
        var dMineOnly = detailFor(mine);
        var selfCard = dMineOnly ? ('<div style="margin-top:12px;max-width:360px;">' + detailCard(mine, true) + '</div>') : '';
        if (typedTheirs){
          var mailSub2 = encodeURIComponent('Product request — Medical Sales Intelligence Hub');
          var mailBody2 = encodeURIComponent('Please add this product to the Product Comparison tool, so I can compare it against ' + mine.name + ' (' + mine.supplier + '):\n\nProduct: ' + typedTheirs + '\nCompany: ' + (chosenSupTheirs || '(not selected)') + '\nAnything else useful (speciality, who sells it, a link):\n');
          return '<div style="font-size:13px;color:#6b7684;margin:6px 0 4px;">Your product: <strong>' + esc(mine.name) + '</strong> (' + esc(mine.supplier) + ')</div>'
            + '<div style="background:#fbf3df;border:1px solid #e8d5a8;border-radius:10px;padding:14px 16px;font-size:14px;line-height:1.65;color:#7a5b14;">'
            + '<strong>“' + esc(typedTheirs) + '” isn’t tracked yet.</strong> Nothing here is guessed — products only appear once they’ve been verified against the live NHS Supply Chain catalogue and the suppliers’ own published information.'
            + '<div style="margin-top:8px;"><a href="mailto:louisehoult@elevateandthrive.uk?subject=' + mailSub2 + '&body=' + mailBody2 + '" style="display:inline-block;background:#6B2A34;color:#fff;border-radius:8px;padding:10px 18px;font-weight:700;font-size:13.5px;text-decoration:none;">Request this product &rarr;</a>'
            + '<span style="font-size:12.5px;color:#8a8778;margin-left:10px;">it goes through the same verification and is usually live within a working day</span></div></div>'
            + selfCard;
        }
        return '<div style="font-size:13px;color:#6b7684;margin:6px 0 4px;">Your product: <strong>' + esc(mine.name) + '</strong> (' + esc(mine.supplier) + ')</div>'
          + '<div style="color:#8a6d00;font-size:14px;padding:12px 14px;background:#fbf3df;border:1px solid #e8d5a8;border-radius:10px;">No tracked competitor products found for this product yet — type a specific rival above, or check the Supplier Intelligence search.</div>'
          + selfCard;
      }

      var h = '<div style="font-size:13px;color:#6b7684;margin:6px 0 2px;">Comparing <strong>' + esc(mine.name) + '</strong> (' + esc(mine.supplier) + ') against <strong>' + esc(theirs.name) + '</strong> (' + esc(theirs.supplier) + ')' + (mine.type ? ' · type: ' + esc(mine.type) : '') + '</div>';
      if (autoSuggested){
        h += '<div style="font-size:12.5px;color:#8a6d00;background:#fbf3df;border:1px solid #e8d5a8;border-radius:8px;padding:8px 12px;margin:4px 0 8px;">We picked <strong>' + esc(theirs.name) + '</strong> as your closest tracked match. Know exactly who you’re up against? Type their product into &ldquo;Compare against&rdquo; above and press Compare again.</div>';
      }

      /* THE DIFFERENTIAL — the primary output. Side by side, pictured, with each
         product's catalogue facts aligned so the difference can be read across a
         row. This replaced a five-column head-to-head table on 06/08/2026: that
         table put each product on its own ROW, which is the wrong axis for "what
         is actually different here", and it showed a 30px thumbnail.
         attrsOf is a hoisted function declaration, so calling it here is safe. */
      var myA0 = attrsOf(mine);
      var theirA0 = attrsOf(theirs);
      h += sideBySide(mine, theirs, myA0, theirA0);

      var dMine = detailFor(mine);
      function attrsOf(p){
        var d2 = detailFor(p); if (!d2) return null;
        var txt = (p.name + ' | ' + d2.items.map(function(it){ return it.desc || ''; }).join(' | ')).toLowerCase();
        var a = { packs: d2.items.length };
        if (/oxidised|oxidized|regenerated cellulose|\borc\b/.test(txt)) a.material = 'oxidised regenerated cellulose (plant-derived)';
        else if (/gelatin/.test(txt)) a.material = /porcine/.test(txt) ? 'porcine gelatin' : 'gelatin';
        else if (/collagen/.test(txt)) a.material = 'collagen (animal-derived)';
        else if (/fibrin|thrombin/.test(txt)) a.material = 'biologic (fibrin/thrombin)';
        else if (/chitosan/.test(txt)) a.material = 'chitosan';
        if (/fibrillar/.test(txt)) a.form = 'fibrillar fabric';
        else if (/knit|fabric/.test(txt)) a.form = 'knitted fabric';
        else if (/powder/.test(txt)) a.form = 'powder';
        else if (/matrix|applicator|flowable/.test(txt)) a.form = 'flowable matrix (applicator)';
        else if (/patch/.test(txt)) a.form = 'patch';
        else if (/sponge/.test(txt)) a.form = 'sponge';
        else if (/sealant|adhesive/.test(txt)) a.form = 'sealant/adhesive';
        if (/medicinal product/.test(txt)) a.reg = 'a licensed medicinal product';
        else if (/biocide/.test(txt)) a.reg = 'a biocide (not a licensed medicine)';
        if (/latex.?free/.test(txt)) a.latex = 'latex-free';
        else if (/\blatex\b/.test(txt)) a.latex = 'natural rubber latex';
        if (/silver alloy|silver.?coated|\bsilver\b/.test(txt)) a.silver = true;
        if (/blood control/.test(txt)) a.bloodctl = true;
        if (/needle.?free/.test(txt)) a.needlefree = true;
        if (/\btint/.test(txt)) a.tint = true;
        if (/\bdehp\b/.test(txt)) a.dehp = true;
        return a;
      }
      function sameSteps(p){
        var pa = attrsOf(p);
        if (!myA0 || !pa || !myA0.form || !pa.form || myA0.form !== pa.form) return false;
        // same format = same steps; a KNOWN material difference breaks it
        if (myA0.material && pa.material && myA0.material !== pa.material) return false;
        // a regulatory-status or latex difference also breaks a "straight swap"
        if ((myA0.reg || pa.reg) && myA0.reg !== pa.reg) return false;
        if ((myA0.latex || pa.latex) && myA0.latex !== pa.latex) return false;
        return true;
      }
      var vMine = numOf(pMine), vTheirs = numOf(pTheirs), vVol = numOf(pVol);
      var saveUnit = (vMine != null && vTheirs != null) ? (vTheirs - vMine) : null;
      var saveAnnual = (saveUnit != null && vVol != null) ? saveUnit * vVol : null;
      function gbp(n){ var neg = n < 0; n = Math.abs(n); var s = n >= 100 ? Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',') : n.toFixed(2); return (neg ? '−£' : '£') + s; }

      // THE DIFFERENCES — the specific, factual differences between these two
      // products, drawn from their own NHS Supply Chain catalogue descriptions.
      // This is the direct answer to "what's actually different, and how do I
      // use it" — a single head-to-head, not an auto-list of near-matches.
      var diffPts = [];
      if (myA0 && theirA0){
        if (theirA0.material && myA0.material && theirA0.material !== myA0.material){
          diffPts.push('<strong>Material:</strong> they are ' + esc(theirA0.material) + ', you are ' + esc(myA0.material) + '.'
            + (/porcine/.test(theirA0.material) && /plant/.test(myA0.material) ? ' <em>Why it matters:</em> porcine-origin products are declined by some patients on faith or personal grounds — a plant-derived alternative removes that conversation entirely.' : '')
            + (/biologic/.test(theirA0.material) && !/biologic/.test(myA0.material) ? ' <em>Why it matters:</em> biologic components bring preparation, storage and cost considerations a ready-to-use mechanical option avoids.' : '')
            + (/biologic/.test(myA0.material) && !/biologic/.test(theirA0.material) ? ' <em>Why it matters:</em> your active biologic mechanism is the premium argument — position on speed/reliability, not price.' : ''));
        }
        if (theirA0.form && myA0.form && theirA0.form !== myA0.form){
          diffPts.push('<strong>Format:</strong> their format is ' + esc(theirA0.form) + ', yours is ' + esc(myA0.form) + '.'
            + (/flowable/.test(theirA0.form) && /fabric|sponge|patch/.test(myA0.form) ? ' <em>Why it matters:</em> a flowable needs an applicator and prep at the table; a fabric is open-and-apply.' : ''));
        }
        if ((myA0.reg || theirA0.reg) && myA0.reg !== theirA0.reg){
          diffPts.push('<strong>Regulatory status:</strong> the catalogue lists yours as ' + esc(myA0.reg || 'unstated') + ' and theirs as ' + esc(theirA0.reg || 'unstated') + '.'
            + (myA0.reg && /licensed/.test(myA0.reg) && theirA0.reg && /biocide/.test(theirA0.reg) ? ' <em>Why it matters:</em> for skin prep before invasive procedures, medicines and IPC policies generally require a licensed medicine with that indication — a biocide is for general skin disinfection. This is the difference that wins the meeting; verify both SmPCs/labels first.' : '')
            + (myA0.reg && /biocide/.test(myA0.reg) && theirA0.reg && /licensed/.test(theirA0.reg) ? ' <em>Why it matters:</em> expect the licensing question if the use is pre-procedure skin prep — prepare your regulatory answer before the meeting.' : ''));
        }
        if ((myA0.latex || theirA0.latex) && myA0.latex !== theirA0.latex){
          diffPts.push('<strong>Latex:</strong> yours is ' + esc(myA0.latex || 'unstated') + ', theirs is ' + esc(theirA0.latex || 'unstated') + '.'
            + (myA0.latex === 'latex-free' && theirA0.latex === 'natural rubber latex' ? ' <em>Why it matters:</em> latex allergy (patients and staff) makes latex-free the default in many trust policies.' : ''));
        }
        if (myA0.silver && !theirA0.silver) diffPts.push('<strong>Antimicrobial element:</strong> your entry carries a silver/antimicrobial element theirs does not mention — an infection-prevention angle (confirm against your IFU before quoting clinically).');
        if (theirA0.silver && !myA0.silver) diffPts.push('<strong>Antimicrobial element:</strong> their entry carries a silver/antimicrobial element yours does not — be ready to answer the infection-prevention question.');
        if (myA0.bloodctl && !theirA0.bloodctl) diffPts.push('<strong>Blood control:</strong> your entry specifies blood-control technology theirs does not mention — a sharps/exposure-safety angle (the 2013 Sharps Regulations make exposure reduction a legal duty).');
        if (theirA0.bloodctl && !myA0.bloodctl) diffPts.push('<strong>Blood control:</strong> their entry specifies blood-control technology yours does not — know your answer on exposure safety.');
        if (myA0.needlefree && !theirA0.needlefree) diffPts.push('<strong>Connector:</strong> your entry includes an integrated needle-free connector theirs does not mention — fewer parts to order and fewer connections to break.');
        if (myA0.tint && !theirA0.tint) diffPts.push('<strong>Visibility:</strong> your range includes a tinted option and theirs does not mention one — clinicians can see exactly where skin has been prepped.');
        if (theirA0.tint && !myA0.tint) diffPts.push('<strong>Visibility:</strong> their range includes a tinted option and yours does not mention one — be ready for the visible-coverage point.');
        if (theirA0.dehp && !myA0.dehp) diffPts.push('<strong>DEHP:</strong> their entry notes DEHP and yours does not mention it — if your product is DEHP-free, that supports the safety and sustainability conversation (verify before claiming).');
        if (!diffPts.length && (myA0.material || myA0.form) && theirA0.packs !== myA0.packs) diffPts.push('Closest match in material and format — the differences are pack range (' + myA0.packs + ' vs ' + theirA0.packs + '), price and service, so your edge carries the argument.');
      }
      var diffHtml;
      if (diffPts.length){
        diffHtml = '<ul style="margin:2px 0 0;padding-left:18px;">' + diffPts.map(function(x){ return '<li style="margin:4px 0;">' + x + '</li>'; }).join('') + '</ul>'
          + '<div style="font-size:11.5px;color:#8a8778;margin-top:6px;">Derived from each product’s own NHS Supply Chain catalogue description. Class-level differences — always confirm specifics against the manufacturer’s IFU before quoting clinically.</div>';
      } else if (dMine && detailFor(theirs)){
        diffHtml = '<div style="font-size:13.5px;color:#39424d;">No catalogue-level material, format or regulatory difference found between these two — on paper this is a straight swap. Your differentiation is price, service, training and relationship (see below), not the product spec.</div>';
      } else {
        diffHtml = '<div style="font-size:13.5px;color:#39424d;">Live NHS Supply Chain description not held for one or both products, so a spec-level difference can’t be shown here. Use the AI prompt below for a deeper product-by-product comparison, or check each supplier’s own site.</div>';
      }
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + OX + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">The differences — and how to differentiate</div><div style="font-size:13.5px;line-height:1.65;color:#39424d;margin-top:6px;">' + diffHtml + '</div></div>';


      // THE CASE FOR SWITCHING. A trust with a working incumbent needs a REASON to
      // change — find one in the data, take the rep's edge if given, and only then
      // use like-for-like as the closer (low-risk switch). Never lead with "it's
      // the same" — lead with what the trust gains.
      var reasons = [];
      function alertsFor(p){
        var sA = SUPOBJ[p.supplier]; if (!sA || !sA.alerts || !sA.alerts.length) return [];
        var keyw = (String(p.name).split(/[\s(]/)[0] || '').toLowerCase();
        return sA.alerts.filter(function(a){ return keyw && ((a.title || '') + ' ' + (a.detail || '')).toLowerCase().indexOf(keyw) !== -1; });
      }
      var theirAlerts = alertsFor(theirs);
      var mineAlerts = alertsFor(mine);
      if (edge) reasons.push('<strong>Your edge (lead with this):</strong> ' + esc(edge) + '. That is the reason for the meeting — everything below supports it.');
      if (saveAnnual != null && saveAnnual > 0){
        reasons.push('<strong>The number for procurement:</strong> at the prices you’ve entered, switching saves ' + gbp(saveUnit) + ' per unit — ' + gbp(saveAnnual) + ' a year at ' + vVol.toLocaleString('en-GB') + ' units. Full breakdown below; verify both prices on the catalogue before you quote it.');
      } else if (saveAnnual != null && saveAnnual < 0){
        reasons.push('<strong>Price honesty:</strong> at the prices you’ve entered, you are ' + gbp(-saveUnit) + ' more per unit (' + gbp(-saveAnnual) + ' a year). Price will not win this one — build the value case instead: value-based procurement caps whole-life cost at 40% of the score, and value (training, resilience, outcomes) carries 60%.');
      }
      if (theirAlerts.length){
        var a0 = theirAlerts[0];
        reasons.push('<strong>Live MHRA / safety action on their line:</strong> ' + esc(theirs.name) + ' — ' + esc(a0.title) + (a0.date ? ' (' + esc(a0.date) + ')' : '') + '. ' + esc(a0.detail || '') + (a0.use ? ' <em>' + esc(a0.use) + '</em>' : '') + (a0.url ? ' <a href="' + a0.url + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-size:11px;font-weight:600;">official alert &#8599;</a>' : '') + ' Quote the official alert verbatim — never embellish a safety issue.');
      }
      if (mineAlerts.length){
        reasons.push('<strong>Be upfront — your own line carries an active alert:</strong> ' + esc(mineAlerts[0].title) + '. Raise it before they do, with your remediation story ready; credibility is won here.');
      }
      var dTheirs = detailFor(theirs);
      if (dTheirs && dTheirs.items.some(function(it){ return it.status; })){
        reasons.push('<strong>Supply reliability:</strong> ' + esc(theirs.name) + ' (' + esc(theirs.supplier) + ') currently shows a suspended or updated pack on the live catalogue. If that is their incumbent, continuity of supply is your opening — a stockout is the one problem procurement cannot ignore.');
      }
      reasons.push('<strong>Second-source resilience:</strong> NHS value-based procurement scores supply-chain resilience, not just price. A like-for-like second source de-risks a single-supplier category — you are not asking them to drop anyone, just to dual-source sensibly.');
      if (dMine && dTheirs && dMine.items.length > dTheirs.items.length){
        reasons.push('<strong>Range fit:</strong> you list ' + dMine.items.length + ' pack formats against ' + dTheirs.items.length + ' for ' + esc(theirs.name) + ' — match the format conversation to how their theatres actually order.');
      }
      if (kp(mine)) reasons.push('<strong>Product edge:</strong> ' + esc(kp(mine)) + '.');
      if (myA0 && theirA0 && myA0.material){
        if (/porcine|gelatin|collagen/.test(theirA0.material||'') && !/porcine|gelatin|collagen/.test(myA0.material)){ reasons.push('<strong>Material consideration:</strong> ' + esc(theirs.name) + ' is animal-derived (see differences above); yours is ' + esc(myA0.material) + ' — for some patients and faith groups that is a genuine clinical-choice reason.'); }
        if (/biologic/.test(theirA0.material||'') && !/biologic/.test(myA0.material)){ reasons.push('<strong>Prep, storage and cost class:</strong> ' + esc(theirs.name) + ' carries biologic components (prep/storage/cost implications); yours is ready off the shelf.'); }
        if (/biologic/.test(myA0.material)){ reasons.push('<strong>Performance positioning:</strong> your active biologic mechanism is the premium argument — position on speed and reliability, not price.'); }
      }
      if (myA0 && theirA0 && myA0.reg && /licensed/.test(myA0.reg) && theirA0.reg && /biocide/.test(theirA0.reg)){
        reasons.push('<strong>Regulatory status (your strongest card):</strong> the catalogue lists your product as a <em>medicinal product</em> while ' + esc(theirs.name) + ' is listed as a <em>biocide</em>. For skin prep before an invasive procedure, a licensed medicine with that indication is the defensible procurement choice — verify both products’ SmPC/labelling, then lead with the licence.');
      }
      if (myA0 && theirA0 && myA0.reg && /biocide/.test(myA0.reg) && theirA0.reg && /licensed/.test(theirA0.reg)){
        reasons.push('<strong>Be ready for the licence question:</strong> ' + esc(theirs.name) + ' is listed on the catalogue as a licensed <em>medicinal product</em> while yours is listed as a <em>biocide</em>. If the intended use is pre-procedure skin prep, expect medicines-policy scrutiny — know your regulatory position and intended-use wording before the meeting.');
      }
      if (myA0 && theirA0 && myA0.latex === 'latex-free' && theirA0.latex === 'natural rubber latex'){
        reasons.push('<strong>Latex-free:</strong> ' + esc(theirs.name) + ' is natural rubber latex on the catalogue listing; yours is latex-free — latex allergy affects patients <em>and</em> staff, and many trust policies now default to latex-free. A genuine clinical-choice reason.');
      }
      if (myA0 && myA0.silver && theirA0 && !theirA0.silver){
        reasons.push('<strong>Antimicrobial element:</strong> your catalogue entry carries a silver/antimicrobial component ' + esc(theirs.name) + '’s entry does not mention — infection prevention is a scored, board-level priority. Confirm the claim wording against your IFU before quoting it clinically.');
      }
      reasons.push('<strong>Sustainability (not checked here):</strong> this comparison has not assessed either product’s sustainability — the catalogue doesn’t carry that data. Carbon and social value are scored at tender (Evergreen from Apr 2026), so if you think your product, packaging or logistics might carry a sustainability benefit for the trust, work it up in the Carbon Saving Calculator on this page.');
      reasons.push('<strong>Price check:</strong> framework prices are visible to catalogue account holders — compare unit and whole-life cost there before the meeting; if you win on price, that is the simplest case of all.');

      /* WHAT TO ASK — built from the differences actually found above, so the
         questions change with the pairing rather than being a stock list. Built
         HERE, after theirAlerts and dTheirs exist: both are `var`s declared
         further up this function, so calling it any earlier read them as
         undefined and silently dropped the alert-derived questions. */
      var askHtml = '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GRN + ';border-radius:10px;padding:14px 16px;margin:12px 0;">'
        + '<div style="font-size:15px;font-weight:800;">What to ask them</div>'
        + '<div style="font-size:12.5px;color:#6b7684;margin-top:3px;line-height:1.55;">Knowing the difference is not the pitch &mdash; asking is. Each one says why it works, so you can adapt it in the room.</div>'
        + '<div style="font-size:13.5px;line-height:1.6;color:#39424d;margin-top:8px;">'
        + probingQuestions(mine, theirs, myA0, theirA0, theirAlerts,
            !!(dTheirs && dTheirs.items && dTheirs.items.some(function(it){ return it.status; })))
        + '</div></div>';

      var caseHtml = '<ul style="margin:2px 0 0;padding-left:18px;">' + reasons.map(function(x){ return '<li style="margin:3px 0;">' + x + '</li>'; }).join('') + '</ul>';

      // like-for-like as the CLOSER, never the opener
      if (sameSteps(theirs)){
        caseHtml += '<div style="margin-top:10px;padding:10px 14px;background:#edf5ee;border-left:3px solid ' + GRN + ';border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.6;color:#39424d;"><strong>Then true like-for-like closes it.</strong> ' + esc(theirs.name) + ' is the same product type in the same format — the same steps to use, just from a different supplier. That means no retraining, no change to how theatres work, a simple side-by-side evaluation and a straight swap on the order template. Switching is a low-risk decision — that is the point to make, not “we’re the same”.</div>';
      } else {
        var sameForm2 = myA0 && theirA0 && myA0.form && theirA0.form && myA0.form === theirA0.form;
        if (sameForm2){
          caseHtml += '<div style="margin-top:10px;padding:10px 14px;background:#edf5ee;border-left:3px solid ' + GRN + ';border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.6;color:#39424d;"><strong>Then make the evaluation easy.</strong> ' + esc(theirs.name) + ' is the same format, so the physical steps are familiar and the evaluation is light. It is still not a “straight swap” claim — the difference above is exactly what the evaluation should test and document. That honesty is your credibility.</div>';
        } else if (myA0 && theirA0){
          caseHtml += '<div style="margin-top:10px;padding:10px 14px;background:#edf5ee;border-left:3px solid ' + GRN + ';border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.6;color:#39424d;"><strong>Then make the switch easy.</strong> ' + esc(theirs.name) + ' is a different format — the evaluation is still straightforward, but be upfront that the steps differ and plan familiarisation/training into your offer. Owning that honestly is more credible than glossing it.</div>';
        }
      }
      if (fwFor(mine)) caseHtml += '<div style="margin-top:8px;font-size:13px;color:#5a6470;"><strong>Buying route:</strong> you’re on ' + esc(fwFor(mine)) + ' — ordering is the easy part.</div>';
      else if (dMine) caseHtml += '<div style="margin-top:8px;font-size:13px;color:#5a6470;"><strong>Buying route:</strong> you’re live on the NHS Supply Chain catalogue (codes below) — ordering is the easy part.</div>';
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GRN + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">How to use it — the case for switching</div><div style="font-size:14px;line-height:1.65;color:#39424d;margin-top:6px;">' + caseHtml + '</div></div>';
      h += askHtml;

      if (saveAnnual != null){
        var srows = ''
          + '<tr><td style="padding:5px 8px;color:#5a6470;">Their price per unit</td><td style="padding:5px 8px;text-align:right;font-weight:700;">' + gbp(vTheirs) + '</td></tr>'
          + '<tr style="border-top:1px solid ' + LINE + ';"><td style="padding:5px 8px;color:#5a6470;">Your price per unit</td><td style="padding:5px 8px;text-align:right;font-weight:700;">' + gbp(vMine) + '</td></tr>'
          + '<tr style="border-top:1px solid ' + LINE + ';"><td style="padding:5px 8px;color:#5a6470;">Difference per unit</td><td style="padding:5px 8px;text-align:right;font-weight:700;">' + gbp(saveUnit) + '</td></tr>'
          + '<tr style="border-top:1px solid ' + LINE + ';"><td style="padding:5px 8px;color:#5a6470;">Units per year</td><td style="padding:5px 8px;text-align:right;font-weight:700;">' + vVol.toLocaleString('en-GB') + '</td></tr>'
          + '<tr style="border-top:2px solid ' + (saveAnnual > 0 ? GRN : OX) + ';"><td style="padding:6px 8px;font-weight:800;">' + (saveAnnual > 0 ? 'Annual saving to the trust' : 'Annual cost of choosing you on price alone') + '</td><td style="padding:6px 8px;text-align:right;font-weight:800;font-size:15px;color:' + (saveAnnual > 0 ? GRN : OX) + ';">' + gbp(Math.abs(saveAnnual)) + (vTheirs ? ' <span style="font-size:11.5px;color:#6b7684;font-weight:600;">(' + Math.abs(Math.round(saveUnit / vTheirs * 100)) + '% ' + (saveAnnual > 0 ? 'less' : 'more') + ')</span>' : '') + '</td></tr>';
        var snote = saveAnnual > 0
          ? 'Put this number next to the trust’s own published savings target (their annual report / board papers — the “Help me prepare” brief pulls it) and the conversation changes. Verify both prices on the live catalogue before you quote them.'
          : 'Do not lead on price. Lead on the value side value-based procurement actually scores — training, implementation support, resilience, outcomes (60% of the score; whole-life cost is capped at 40%) — and build the number in the Value Case Calculator. Verify both prices on the live catalogue first.';
        h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + (saveAnnual > 0 ? GRN : OX) + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">The savings calculation — your numbers, worked through</div><div style="font-size:12px;color:#6b7684;margin:2px 0 8px;">Based on the prices you entered against ' + esc(theirs.name) + '. Framework prices move — always confirm on the catalogue (customer login) before quoting.</div><table style="border-collapse:collapse;min-width:300px;max-width:440px;width:100%;font-size:13px;">' + srows + '</table><div style="font-size:13px;line-height:1.6;color:#39424d;margin-top:8px;">' + snote + '</div></div>';
      }

      // WHY TRUSTS ACTUALLY SWITCH — the evidenced drivers (researched & sourced),
      // auto-mapped: which does THIS case activate? Ticked = live in your case now.
      var DRIVERS = [
        {n:'Cost pressure / CIP savings', ev:'Product switches are a standard cost-improvement lever (Carter set a £700m procurement savings target; system needs £11bn in 2025/26).', src:'https://www.gov.uk/government/news/review-shows-how-nhs-hospitals-can-save-money-and-improve-care',
          on: /sav|price|cost|%|cheap/i.test(edge||'') || (saveAnnual != null && saveAnnual > 0), note: (saveAnnual != null && saveAnnual > 0) ? ('your saving is quantified below (' + gbp(saveAnnual) + '/year) — set it against their CIP target') : 'your edge is a saving — quantify it against their CIP target'},
        {n:'Contract / framework renewal cycle', ev:'Frameworks run 2–4 years and new suppliers join at re-tender — the natural switch window.', src:'https://www.supplychain.nhs.uk/suppliers/contract-and-tender-process/',
          on: /award|202[6-8]/.test(mine.fwDates||''), note: mine.fwDates ? ('your framework timing: ' + mine.fwDates) : 'check the category’s renewal date in the Procurement Calendar'},
        {n:'Value-based procurement scoring', ev:'DHSC national standard: five value domains carry a minimum 60% combined weighting; whole-life cost is capped at 40% — better-value challengers can beat cheaper incumbents.', src:'https://www.gov.uk/government/publications/value-based-procurement-for-medical-technology',
          on: true, note:'build the number in the Value Case Calculator — this is the scoring system your case is judged in'},
        {n:'Supply disruption / discontinuation', ev:'When an incumbent discontinued high-usage suture lines, South Yorkshire ICS switched to a framework alternative, saved £553,000, and two more trusts followed — a rival’s supply problem (discontinuation, suspension or recall) is a proven switch trigger.', src:'https://www.supplychain.nhs.uk/news-article/suture-switch-collaboration/',
          on: !!(dTheirs && dTheirs.items.some(function(it){ return it.status; })), note:'their line shows a suspended/updated pack — lead with continuity of supply'},
        {n:'Supply-chain resilience / dual sourcing', ev:'Resilience is one of the five scored VBP value domains — a like-for-like second source de-risks a single-supplier category.', src:'https://www.nhsconfed.org/publications/supply-chain-resilience',
          on: true, note:'position as sensible dual-sourcing, not a rip-and-replace'},
        {n:'Standardisation / rationalising variation', ev:'Carter found 30,000 suppliers, 20,000 brands and 400,000+ product codes across 22 trusts — consolidation is policy.', src:'https://www.gov.uk/government/news/review-shows-how-nhs-hospitals-can-save-money-and-improve-care',
          on: allComps.length >= 5, note:'a fragmented category — offer to simplify their range'},
        {n:'Clinical evaluation & clinician acceptance', ev:'Switches stick when clinicians co-own the evaluation; resistance breeds workarounds (published NHS evidence).', src:'https://pmc.ncbi.nlm.nih.gov/articles/PMC8512597/',
          on: sameSteps(theirs), note:'true like-for-like = a light evaluation — design it WITH their clinical lead'},
        {n:'Training & implementation support (scored)', ev:'Ease of use, training and implementation support are explicitly scored inside the mandatory 60% VBP value weighting.', src:'https://www.gov.uk/government/publications/value-based-procurement-for-medical-technology',
          on: (sameSteps(theirs) || /train|support|implement|educat/i.test(edge||'')), note:'same-steps switch or a training offer — either scores here'},
        {n:'Safety alerts & regulation', ev:'MHRA alerts and regulation force substitutions (e.g. the 2013 Sharps Regulations drove NHS-wide device switches).', src: (theirAlerts.length && theirAlerts[0].url) ? theirAlerts[0].url : 'https://www.hse.gov.uk/pubns/hsis7.htm',
          on: theirAlerts.length > 0, note: theirAlerts.length ? ('a live MHRA action touches ' + theirs.name + ' — this is your strongest driver right now') : 'watch the Live Desk — if an alert touches the incumbent, this becomes your strongest driver overnight'},
        {n:'Sustainability / net zero', ev:'10% minimum social value weighting now; full scope 1–3 Carbon Reduction Plans required from April 2027.', src:'https://www.england.nhs.uk/long-read/2027-nhs-carbon-reduction-plan-requirements/',
          on: /carbon|sustain|green|packag/i.test(edge||''), note:'if you hold a carbon/packaging advantage, it is scored — quantify it in the Carbon Saving Calculator'},
        {n:'Relationships & trust', ev:'Established supplier contacts cement incumbents (published NHS evidence) — which is why the relationship IS the strategy.', src:'https://pmc.ncbi.nlm.nih.gov/articles/PMC8512597/',
          on: true, note:'people buy from people — your presence, service and follow-through are a scored and felt differentiator'},
        {n:'GIRFT data exposure', ev:'GIRFT’s specialty reports flag procurement variation and directly prompt trusts to review products.', src:'https://gettingitrightfirsttime.co.uk/',
          on: /theatre|surg/i.test((mine.specs||[]).join(' ')) || mine.type === 'haemostat', note:'a surgical category — GIRFT variation data supports the standardisation conversation'}
      ];
      var dOn = DRIVERS.filter(function(d){ return d.on; });
      var dOff = DRIVERS.filter(function(d){ return !d.on; });
      function drow(d, on){
        return '<li style="margin:4px 0;' + (on ? '' : 'opacity:.55;') + '"><strong>' + (on ? '✓ ' : '· ') + esc(d.n) + '</strong> — ' + d.ev + (on && d.note ? ' <span style="color:#14432f;font-weight:600;">Your case: ' + d.note + '.</span>' : (d.note ? ' <span style="color:#8a8778;">' + d.note + '.</span>' : '')) + ' <a href="' + d.src + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-size:11px;font-weight:600;">source &#8599;</a></li>';
      }
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GOLD + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">Why trusts actually switch — and where your case lands</div><div style="font-size:12px;color:#6b7684;margin:2px 0 6px;">The evidenced switch drivers from published NHS sources. ✓ = active in your case now (' + dOn.length + ' of ' + DRIVERS.length + ').</div><ul style="margin:2px 0 0;padding-left:18px;font-size:13px;line-height:1.6;color:#39424d;">' + dOn.map(function(d){ return drow(d, true); }).join('') + dOff.map(function(d){ return drow(d, false); }).join('') + '</ul></div>';

      // SIDE BY SIDE — just the two products, so the rep looks with their own eyes;
      // followed by coaching prompts the tool cannot answer for them.
      var sbs = [mine, theirs].map(function(p){
        var d3 = detailFor(p); if (!d3 || !d3.items) return null;
        var seenU = {}, imgs = [];
        d3.items.filter(function(x){ return !x.status; }).concat(d3.items.filter(function(x){ return x.status; })).forEach(function(x){
          if (x.img && !seenU[x.img]){ seenU[x.img] = 1; imgs.push(x.img); }
        });
        imgs.sort(function(a, b){ return (/group/i.test(b) ? 1 : 0) - (/group/i.test(a) ? 1 : 0); });
        return imgs.length ? { p: p, imgs: imgs.slice(0, 3) } : null;
      }).filter(Boolean);
      if (sbs.length >= 2){
        var cells = sbs.map(function(x){
          var isMine = x.p === mine;
          var ih = x.imgs.length > 1 ? 110 : 150;
          var imrow = '<div style="display:flex;gap:6px;">' + x.imgs.map(function(u){
            return '<a href="' + esc(u) + '" target="_blank" rel="noopener" style="flex:1;min-width:0;"><img src="' + esc(u) + '" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentNode.style.display=\'none\'" style="width:100%;height:' + ih + 'px;object-fit:contain;background:#fff;border:1px solid #f0ede5;border-radius:6px;"></a>';
          }).join('') + '</div>';
          return '<div style="flex:1 1 240px;max-width:340px;text-align:center;padding:10px;border:2px solid ' + (isMine ? GRN : LINE) + ';border-radius:10px;background:#fff;">' + imrow
            + '<div style="font-weight:800;font-size:13px;margin-top:6px;">' + esc(x.p.name) + (isMine ? ' <span style="color:' + GRN + ';font-size:11px;">(you)</span>' : '') + '</div>'
            + '<div style="font-size:11.5px;color:#6b7684;">' + esc(x.p.supplier) + '</div>'
            + '<div style="font-size:10.5px;color:#9a958a;margin-top:2px;">click a photo for full size</div></div>';
        }).join('');
        h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GRN + ';border-radius:10px;padding:14px 16px;margin:12px 0;">'
          + '<div style="font-size:15px;font-weight:800;">Look at them side by side — then think like the customer</div>'
          + '<div style="font-size:12.5px;color:#6b7684;margin:2px 0 10px;">Live photographs from the NHS Supply Chain catalogue, exactly as each supplier uploaded them; sometimes the product itself, sometimes in its packaging. The data above tells you what is listed; your own eyes and product knowledge find the rest.</div>'
          + '<div style="display:flex;flex-wrap:wrap;gap:12px;justify-content:flex-start;">' + cells + '</div>'
          + '<div style="margin-top:12px;padding:10px 14px;background:#fbf7ec;border-left:3px solid ' + GOLD + ';border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.65;color:#39424d;"><strong>Now add what only you know:</strong>'
          + '<ul style="margin:4px 0 0;padding-left:18px;">'
          + '<li style="margin:3px 0;">What other differences are you aware of from handling or demonstrating these products — application, feel, packaging, waste, shelf life?</li>'
          + '<li style="margin:3px 0;">What else could make this customer interested — delivery times, UK stockholding, price, sustainability, pack sizes that match how they order?</li>'
          + '<li style="margin:3px 0;">What comes with your product beyond the product itself — training, clinical support, implementation help, audit support? Training and implementation support are explicitly scored in NHS value-based procurement, so say so.</li>'
          + '</ul></div></div>';
      }

      // On-page product detail (image + every pack code) for both products
      var withDetail = [mine, theirs].filter(function(p){ return detailFor(p); });
      if (withDetail.length){
        var cards = withDetail.map(function(p){ return detailCard(p, p === mine); }).join('');
        h += '<div style="margin:14px 0 4px;font-size:15px;font-weight:800;">Product detail — live from NHS Supply Chain</div>';
        h += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;">' + cards + '</div>';
        h += '<div style="font-size:11.5px;color:#8a8778;margin-top:6px;">Images, descriptions, pack sizes and NPC / MPC codes are drawn from the public NHS Supply Chain catalogue. Prices need a customer login.</div>';
      }

      // Other tracked products in the same category — a quick way to switch who
      // you're compared against without retyping, kept secondary to the main
      // head-to-head above (the rep asked for ONE clear comparison, not a list).
      var others = allComps.filter(function(p){ return p !== theirs; }).slice(0, 5);
      if (others.length){
        h += '<div style="margin:14px 0 0;font-size:12.5px;color:#75808d;">Other tracked products in this category: ' + others.map(function(p){ return '<a href="#" class="msh-cmp-other" data-name="' + esc(p.name) + '" data-supplier="' + esc(p.supplier) + '" style="color:' + GOLD + ';font-weight:600;">' + esc(p.name) + ' (' + esc(p.supplier) + ')</a>'; }).join(', ') + ' — click one to compare against that instead.</div>';
      }

      // optional angle
      var body;
      if (angle === 'Objection handling (MSTP)') body = objection(mine, theirs);
      else body = (angle && ANGLE[angle] ? ANGLE[angle] : 'Optional — pick “what matters most” above for a tailored play, including Objection handling (MSTP): Acknowledge &rarr; Reframe &rarr; One more question.') + ' ' + link('Open the Value Case Calculator', 1109) + '.';
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GOLD + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">How you could use this' + (angle ? ' — ' + esc(angle) : ' (optional)') + '</div><div style="font-size:14px;line-height:1.65;color:#39424d;margin-top:4px;">' + body + '</div></div>';

      // AI prompt
      var prompt = 'Compare ' + mine.name + ' (' + mine.supplier + ') against ' + theirs.name + ' (' + theirs.supplier + ') for an NHS buyer: the key clinical and practical differences, where each wins, and how I sell ' + mine.name + ' against it. Bullet points.';
      h += '<div style="background:' + SOFT + ';border:1px dashed ' + GOLD + ';border-radius:10px;padding:12px 16px;margin:12px 0;"><div style="font-size:13px;font-weight:700;color:' + INK + ';">Deep product-by-product detail — copy into your AI assistant:</div><div style="font-size:13px;color:#39424d;background:#fff;border:1px solid ' + LINE + ';border-radius:6px;padding:8px 10px;margin-top:6px;font-family:ui-monospace,Menlo,monospace;">' + esc(prompt) + '</div><div style="font-size:12px;color:#8a8778;margin-top:6px;">Once the Hub’s AI integration is live, this answers itself in-tool.</div></div>';

      // Hand-off into "Help me prepare" — carries this product & supplier across.
      h += '<div style="margin:14px 0 6px;"><a href="#msh-meeting-prep" id="msh-handoff" data-supplier="' + esc(mine.supplier) + '" data-product="' + esc(mine.name) + '" style="display:inline-block;background:' + GRN + ';color:#fff;border-radius:8px;padding:11px 20px;font-weight:700;font-size:14px;text-decoration:none;">Take this into &ldquo;Help me prepare&rdquo; &rarr;</a><span style="font-size:12px;color:#8a8778;margin-left:10px;">carries this product into your meeting brief</span></div>';
      h += '<div style="font-size:12px;color:#8a8778;">Product names are the suppliers’ own; framework is top-level (verify the lot at source); NPC / MPC codes and images are from the public NHS Supply Chain catalogue (prices need login). Nothing is invented.</div>';
      return h;
    }

    function addCopy(container){
      if (!container.textContent || container.textContent.indexOf('Type your product') !== -1) return;
      var b = el('button', 'background:#a8842c !important;color:#ffffff !important;border:0;border-radius:8px;padding:9px 16px;font-weight:800;font-size:13.5px;cursor:pointer;margin:4px 0 10px;box-shadow:0 1px 3px rgba(0,0,0,.12);', 'Copy brief');
      b.addEventListener('click', function(){ var t = container.innerText.replace('Copy brief','').trim(); if (navigator.clipboard) { navigator.clipboard.writeText(t); b.textContent='Copied ✓'; setTimeout(function(){ b.textContent='Copy brief'; }, 1500); } });
      container.insertBefore(b, container.firstChild);
    }
  }
})();
