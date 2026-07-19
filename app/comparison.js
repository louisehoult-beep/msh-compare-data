/* NHS Intelligence Hub — Product Comparison tool (PRODUCT-FIRST, with live NHSSC detail).
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
  var IDX = BASE + 'data/supplier-index.json?cb=' + Date.now();
  var CFG = BASE + 'data/prep-config.json?cb=' + Date.now();
  var SEED = BASE + 'data/supplier-seed.json?cb=' + Date.now();
  var NHSSC = BASE + 'data/nhssc-cache.json?cb=' + Date.now();

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
    fetch(NHSSC).then(function(r){return r.json();}).catch(function(){return {products:{}};})
  ]).then(function(res){ render(res[0], res[1], res[2], res[3]); })
    .catch(function(){ MOUNT.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:#8a6d00;">Comparison tool temporarily unavailable — please try again shortly.</div>'; });

  function render(index, cfg, seed, nhssc){
    var suppliers = (index && index.suppliers) || [];
    var seedMap = {}; ((seed && seed.suppliers) || []).forEach(function(s){ seedMap[s.name] = s; });
    suppliers.forEach(function(s){ var sd = seedMap[s.name]; if (sd){ ['voice','products','frameworks','specialities'].forEach(function(k){ if (sd[k] && (!Array.isArray(sd[k]) || sd[k].length)) s[k] = sd[k]; }); } });
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
    suppliers.forEach(function(s){
      (s.products || []).forEach(function(p){
        var name = typeof p === 'string' ? p : (p && p.name);
        if (!name) return;
        PRODUCTS.push({ name: name, code: (p && p.code) || '', supplier: s.name, specs: s.specialities || [], framework: (s.frameworks && s.frameworks[0] && s.frameworks[0].name) || '', fwDates: (s.frameworks && s.frameworks[0] && s.frameworks[0].dates) || '', voice: s.voice, type: typeForProduct(name) });
      });
    });
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

    var wrap = el('div', 'font-family:Inter,system-ui,sans-serif;color:' + INK + ';');
    wrap.appendChild(el('div', 'text-transform:uppercase;letter-spacing:2px;font-size:11px;font-weight:700;color:' + OX + ';', 'NHS Intelligence Hub'));
    wrap.appendChild(el('div', 'font-size:24px;font-weight:800;margin:2px 0 4px;', 'Product Comparison'));
    wrap.appendChild(el('div', 'font-size:14px;line-height:1.6;color:#4a5766;max-width:720px;margin-bottom:12px;', 'Pick your <strong>company</strong>, narrow by <strong>speciality</strong> and <strong>product type</strong>, then type the <strong>product name or an NHSSC code</strong> — the tool finds the competing products automatically and compares them like-for-like, with the <strong>real NHS Supply Chain detail on the page</strong>: product image, description and every pack’s NPC / MPC code.'));

    // Search flow: 1 Company -> 2 Speciality (from the supplier directory) ->
    // 3 Product type -> 4 product name OR NHSSC code -> Compare.
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
    var bar = el('div', 'display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:12px;margin-bottom:10px;');
    var supNames0 = [], supSeen0 = {};
    PRODUCTS.forEach(function(p){ if (!supSeen0[p.supplier]){ supSeen0[p.supplier] = 1; supNames0.push(p.supplier); } });
    supNames0.sort(function(a,b){ return a.toLowerCase() < b.toLowerCase() ? -1 : 1; });
    var selSup = mkSelect('1 · Company', [''].concat(supNames0));
    var selSpec = mkSelect('2 · Speciality', ['']); selSpec.sel.disabled = true;
    var selType = mkSelect('3 · Product type', ['']); selType.sel.disabled = true;
    var pbox = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:260px;flex:2;');
    pbox.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', '4 · Product name or NHSSC code'));
    var inp = el('input', 'padding:10px 12px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;background:#fff !important;color:#20303f !important;'); inp.type='text'; inp.setAttribute('list','msh-prod-list'); inp.placeholder='e.g. Pahacel — or a code like ELS924';
    var dl = el('datalist'); dl.id='msh-prod-list';
    pbox.appendChild(inp); pbox.appendChild(dl);
    var btn = el('button', 'background:#6B2A34 !important;color:#ffffff !important;border:0;border-radius:8px;padding:12px 24px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.3px;box-shadow:0 1px 3px rgba(0,0,0,.15);', 'Compare');
    bar.appendChild(selSup.box); bar.appendChild(selSpec.box); bar.appendChild(selType.box); bar.appendChild(pbox); bar.appendChild(btn);
    wrap.appendChild(bar);
    function rawTypesFor(sup, spec){
      var allowed = spec ? SPECMAP[spec.toLowerCase()] : null;
      var seenT = {}, out = [];
      PRODUCTS.forEach(function(p){
        if (sup && p.supplier !== sup) return;
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
    selSup.sel.addEventListener('change', function(){
      var sup = selSup.sel.value;
      var s = SUPOBJ[sup];
      fillSel(selSpec.sel, (s && s.specialities || []).slice().sort());
      selSpec.sel.disabled = !sup;
      fillSel(selType.sel, rawTypesFor(sup, ''), function(t){ return t.charAt(0).toUpperCase() + t.slice(1); });
      selType.sel.disabled = !sup;
      refreshList();
    });
    selSpec.sel.addEventListener('change', function(){
      fillSel(selType.sel, rawTypesFor(selSup.sel.value, selSpec.sel.value), function(t){ return t.charAt(0).toUpperCase() + t.slice(1); });
      refreshList();
    });
    selType.sel.addEventListener('change', refreshList);
    refreshList();

    // Your edge: the reason the trust would switch — the case builder leads with this.
    var opt = el('div', 'display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin:-6px 0 14px;padding-left:2px;');
    var ebox = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:300px;flex:2;');
    ebox.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', 'Your edge — what are you giving them? (recommended)'));
    var edgeInp = el('input', 'padding:9px 12px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13.5px;background:#fff !important;color:#20303f !important;');
    edgeInp.type = 'text'; edgeInp.placeholder = 'e.g. 15% saving vs incumbent · next-day supply · on-site training · UK stockholding';
    ebox.appendChild(edgeInp); opt.appendChild(ebox);
    var selAng = mkSelect('Objection / angle (optional)', ['', 'Price / cost', 'Value & capacity', 'Clinical evidence', 'Sustainability', 'Objection handling (MSTP)']);
    opt.appendChild(selAng.box); wrap.appendChild(opt);
    function mkSelect(label, opts){
      var box = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:210px;');
      box.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#9a958a;', esc(label)));
      var sel = el('select', 'padding:9px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13.5px;background:#ffffff !important;color:#20303f !important;');
      opts.forEach(function(o){ var op = el('option'); op.value = o; op.textContent = o || '— none —'; sel.appendChild(op); });
      box.appendChild(sel); return { box: box, sel: sel };
    }

    var out = el('div', 'margin-top:6px;'); out.id='msh-compare-out'; wrap.appendChild(out);
    MOUNT.innerHTML = ''; MOUNT.appendChild(wrap);

    function doCompare(){
      var v = inp.value.trim();
      var pool = subset();
      var mine = null;
      // NHSSC code search: NPC or MPC typed directly.
      var code = v.toUpperCase().replace(/[^A-Z0-9]/g, '');
      if (code.length >= 4 && /\d/.test(code)){
        for (var ck in cp){
          if ((cp[ck].items || []).some(function(it){ return it.npc === code || it.mpc === code; })){
            mine = PRODUCTS.filter(function(p){ return nk(p.name) === nk(ck); })[0];
            if (mine) break;
          }
        }
      }
      function find(list){
        return list.filter(function(p){ return (p.name+'  ·  '+p.supplier) === v; })[0]
            || list.filter(function(p){ return p.name.toLowerCase() === v.toLowerCase(); })[0]
            || list.filter(function(p){ return v && p.name.toLowerCase().indexOf(v.toLowerCase()) !== -1; })[0];
      }
      if (!mine && v) mine = find(pool) || find(PRODUCTS);
      if (!mine && !v && pool.length && pool.length <= 1) mine = pool[0];
      out.innerHTML = compare(mine, selAng.sel.value, edgeInp.value.trim());
      addCopy(out);
      var hb = out.querySelector('#msh-handoff');
      if (hb){
        hb.addEventListener('click', function(){
          var payload = { company: hb.getAttribute('data-supplier'), product: hb.getAttribute('data-product'), edge: edgeInp.value.trim(), ts: Date.now() };
          try { localStorage.setItem('mshPrepHandoff', JSON.stringify(payload)); } catch(e){}
          try { window.dispatchEvent(new CustomEvent('msh-prep-handoff', { detail: payload })); } catch(e){}
        });
      }
      out.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    btn.addEventListener('click', doCompare);

    function link(text, id){ return '<a href="https://elevateandthrive.uk/?page_id=' + id + '" style="color:' + GOLD + ';font-weight:600;">' + text + '</a>'; }
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

    function objection(mine, comps){
      var top = comps[0];
      var edge = kp(mine) || (mine.voice && mine.voice.angle) || 'your product’s strength';
      var c = top ? top.name + ' (' + top.supplier + ')' : 'their current product';
      return 'Handle it the MSTP way — <strong>Acknowledge &rarr; Reframe &rarr; One more question</strong>:'
        + '<ul style="margin:4px 0 0;padding-left:18px;">'
        + '<li><strong>Acknowledge:</strong> “' + esc(c) + ' is a solid choice — I can see why you use it.”</li>'
        + '<li><strong>Reframe</strong> to your edge: ' + esc(edge) + (fwFor(mine) ? ' — and it’s on ' + esc(fwFor(mine)) + '.' : (detailFor(mine) ? ' — and it’s on the live NHS Supply Chain catalogue.' : '.')) + '</li>'
        + '<li><strong>One more question:</strong> “If I could show you where ' + esc(mine.name) + ' saves time or reduces a complication versus ' + esc(top ? top.name : 'your current option') + ', would that be worth a short trial?”</li>'
        + '</ul>';
    }

    function compare(mine, angle, edge){
      if (!mine){ return '<div style="color:#8a6d00;font-size:14px;padding:8px 0;">Type your product above (start typing to pick from the list) and press Compare.</div>'; }
      var comps = competitorsOf(mine);
      var h = '<div style="font-size:13px;color:#6b7684;margin:6px 0 4px;">Your product: <strong>' + esc(mine.name) + '</strong> (' + esc(mine.supplier) + ')' + (mine.type ? ' · type: ' + esc(mine.type) : '') + ' · ' + comps.length + ' competing products found</div>';

      // Like-for-like table (primary output)
      h += '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13.5px;min-width:680px;background:#fff;border:1px solid ' + LINE + ';border-radius:10px;">'
        + '<thead><tr style="background:' + OX + ';color:#fff;text-align:left;"><th style="padding:8px 9px;">Product</th><th style="padding:8px 9px;">Supplier</th><th style="padding:8px 9px;">On framework</th><th style="padding:8px 9px;">NHSSC code (live)</th><th style="padding:8px 9px;">Key point</th></tr></thead><tbody>'
        + row(mine, true) + comps.map(function(p){ return row(p, false); }).join('') + '</tbody></table></div>';
      if (!comps.length) h += '<div style="font-size:12.5px;color:#8a8778;margin-top:4px;">No competing products matched automatically — broaden the product name or check the supplier directory.</div>';

      // THE CASE FOR SWITCHING. A trust with a working incumbent needs a REASON to
      // change — find one in the data, take the rep's edge if given, and only then
      // use like-for-like as the closer (low-risk switch). Never lead with "it's
      // the same" — lead with what the trust gains.
      var top = comps[0];
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
      var myA0 = attrsOf(mine);
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
      var reasons = [];
      if (edge) reasons.push('<strong>Your edge (lead with this):</strong> ' + esc(edge) + '. That is the reason for the meeting — everything below supports it.');
      var wobbly = comps.filter(function(p){ var d2 = detailFor(p); return d2 && d2.items.some(function(it){ return it.status; }); }).slice(0, 2);
      if (wobbly.length){
        reasons.push('<strong>Supply reliability:</strong> ' + wobbly.map(function(p){ return esc(p.name) + ' (' + esc(p.supplier) + ')'; }).join(' and ') + ' currently show a suspended or updated pack on the live catalogue. If that is their incumbent, continuity of supply is your opening — a stockout is the one problem procurement cannot ignore.');
      }
      if (comps.length){
        reasons.push('<strong>Second-source resilience:</strong> NHS value-based procurement scores supply-chain resilience, not just price. A like-for-like second source de-risks a single-supplier category — you are not asking them to drop anyone, just to dual-source sensibly.');
      }
      var dTop = top && detailFor(top);
      if (dMine && dTop && dMine.items.length > dTop.items.length){
        reasons.push('<strong>Range fit:</strong> you list ' + dMine.items.length + ' pack formats against ' + dTop.items.length + ' for ' + esc(top.name) + ' — match the format conversation to how their theatres actually order.');
      }
      if (kp(mine)) reasons.push('<strong>Product edge:</strong> ' + esc(kp(mine)) + '.');
      // Material / mechanism reasons drawn from the catalogue descriptions
      if (myA0 && myA0.material){
        var porcineRivals = comps.slice(0,6).filter(function(p){ var a=attrsOf(p); return a && /porcine|gelatin|collagen/.test(a.material||'') && !/porcine|gelatin|collagen/.test(myA0.material); });
        if (porcineRivals.length){ reasons.push('<strong>Material consideration:</strong> ' + porcineRivals.map(function(p){ return esc(p.name); }).join(' and ') + ' are animal-derived (see differences below); yours is ' + esc(myA0.material) + ' — for some patients and faith groups that is a genuine clinical-choice reason.'); }
        var bioRivals = comps.slice(0,6).filter(function(p){ var a=attrsOf(p); return a && /biologic/.test(a.material||'') && !/biologic/.test(myA0.material); });
        if (bioRivals.length){ reasons.push('<strong>Prep, storage and cost class:</strong> ' + bioRivals.map(function(p){ return esc(p.name); }).join(' and ') + ' carry biologic components (prep/storage/cost implications); yours is ready off the shelf.'); }
        if (/biologic/.test(myA0.material)){ reasons.push('<strong>Performance positioning:</strong> your active biologic mechanism is the premium argument — position on speed and reliability of haemostasis, not price.'); }
      }
      if (myA0 && myA0.reg && /licensed/.test(myA0.reg)){
        var biocideRivals = comps.slice(0,6).filter(function(p){ var a = attrsOf(p); return a && a.reg && /biocide/.test(a.reg); });
        if (biocideRivals.length){ reasons.push('<strong>Regulatory status (your strongest card):</strong> the catalogue lists your product as a <em>medicinal product</em> while ' + biocideRivals.map(function(p){ return esc(p.name); }).join(' and ') + ' is listed as a <em>biocide</em>. For skin prep before an invasive procedure, a licensed medicine with that indication is the defensible procurement choice — verify both products\u2019 SmPC/labelling, then lead with the licence.'); }
      }
      if (myA0 && myA0.reg && /biocide/.test(myA0.reg)){
        var licRivals = comps.slice(0,6).filter(function(p){ var a = attrsOf(p); return a && a.reg && /licensed/.test(a.reg); });
        if (licRivals.length){ reasons.push('<strong>Be ready for the licence question:</strong> ' + licRivals.map(function(p){ return esc(p.name); }).join(' and ') + ' is listed on the catalogue as a licensed <em>medicinal product</em> while yours is listed as a <em>biocide</em>. If the intended use is pre-procedure skin prep, expect medicines-policy scrutiny — know your regulatory position and intended-use wording before the meeting.'); }
      }
      if (myA0 && myA0.latex === 'latex-free'){
        var latexRivals = comps.slice(0,6).filter(function(p){ var a = attrsOf(p); return a && a.latex === 'natural rubber latex'; });
        if (latexRivals.length){ reasons.push('<strong>Latex-free:</strong> ' + latexRivals.map(function(p){ return esc(p.name); }).join(' and ') + ' is natural rubber latex on the catalogue listing; yours is latex-free — latex allergy affects patients <em>and</em> staff, and many trust policies now default to latex-free. A genuine clinical-choice reason.'); }
      }
      if (myA0 && myA0.silver){
        var plainRivals = comps.slice(0,6).filter(function(p){ var a = attrsOf(p); return a && !a.silver; });
        if (plainRivals.length === comps.slice(0,6).length && comps.length){ reasons.push('<strong>Antimicrobial element:</strong> your catalogue entry carries a silver/antimicrobial component the listed competitors\u2019 entries do not mention — infection prevention is a scored, board-level priority. Confirm the claim wording against your IFU before quoting it clinically.'); }
      }
      reasons.push('<strong>Sustainability:</strong> carbon is scored at tender (Evergreen from Apr 2026) — if your product or packaging carries a carbon advantage, quantify it in the Sustainability Calculator; it feeds the tender weighting.');
      reasons.push('<strong>Price check:</strong> framework prices are visible to catalogue account holders — compare unit and whole-life cost there before the meeting; if you win on price, that is the simplest case of all.');
      var caseHtml;
      if (!edge && !wobbly.length && !kp(mine)){
        caseHtml = '<div style="background:#fbf3df;border:1px solid #e8d5a8;border-radius:8px;padding:10px 14px;margin:0 0 8px;font-size:13.5px;color:#7a5b14;"><strong>The data shows no obvious switch reason — so what’s yours?</strong> If nothing is wrong with their current supplier, the trust has no reason to change. Type your edge above (a price saving, next-day supply, service and training, UK stockholding, clinical preference) and the case builds around it.</div>'
          + (reasons.length ? '<ul style="margin:2px 0 0;padding-left:18px;">' + reasons.map(function(x){ return '<li style="margin:3px 0;">' + x + '</li>'; }).join('') + '</ul>' : '');
      } else {
        caseHtml = '<ul style="margin:2px 0 0;padding-left:18px;">' + reasons.map(function(x){ return '<li style="margin:3px 0;">' + x + '</li>'; }).join('') + '</ul>';
      }
      // like-for-like as the CLOSER, never the opener
      if (top){
        var myWords = (mine.name + ' ' + ((dMine && dMine.items[0].desc) || '')).toLowerCase().match(/[a-z]{5,}/g) || [];
        var topWords = (top.name + ' ' + ((dTop && dTop.items[0].desc) || '')).toLowerCase().match(/[a-z]{5,}/g) || [];
        var topStem = {}; topWords.forEach(function(w){ topStem[w.slice(0,8)] = 1; });
        var sharedSeen = {}, shared = [];
        myWords.forEach(function(w){ var s = w.slice(0,8); if (topStem[s] && !sharedSeen[s]){ sharedSeen[s] = 1; shared.push(w); } });
        var trueTwin = comps.filter(sameSteps)[0];
        if (trueTwin){
          caseHtml += '<div style="margin-top:10px;padding:10px 14px;background:#edf5ee;border-left:3px solid ' + GRN + ';border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.6;color:#39424d;"><strong>Then true like-for-like closes it.</strong> ' + esc(trueTwin.name) + ' is the same product type in the same format — the same steps to use, just from a different supplier. That means no retraining, no change to how theatres work, a simple side-by-side evaluation and a straight swap on the order template. Switching is a low-risk decision — that is the point to make, not \u201cwe\u2019re the same\u201d.</div>';
        } else if (top){
          var ta2 = attrsOf(top);
          var sameForm2 = myA0 && ta2 && myA0.form && ta2.form && myA0.form === ta2.form;
          if (sameForm2){
            caseHtml += '<div style="margin-top:10px;padding:10px 14px;background:#edf5ee;border-left:3px solid ' + GRN + ';border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.6;color:#39424d;"><strong>Then make the evaluation easy.</strong> ' + esc(top.name) + ' is the same format, so the physical steps are familiar and the evaluation is light. It is still not a \u201cstraight swap\u201d claim — the status or material difference above is exactly what the evaluation should test and document. That honesty is your credibility.</div>';
          } else {
            caseHtml += '<div style="margin-top:10px;padding:10px 14px;background:#edf5ee;border-left:3px solid ' + GRN + ';border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.6;color:#39424d;"><strong>Then make the switch easy.</strong> ' + esc(top.name) + ' is the same class but a different format — the evaluation is still straightforward, but be upfront that the steps differ and plan familiarisation/training into your offer. Owning that honestly is more credible than glossing it.</div>';
          }
        }
      }
      if (fwFor(mine)) caseHtml += '<div style="margin-top:8px;font-size:13px;color:#5a6470;"><strong>Buying route:</strong> you’re on ' + esc(fwFor(mine)) + ' — ordering is the easy part.</div>';
      else if (dMine) caseHtml += '<div style="margin-top:8px;font-size:13px;color:#5a6470;"><strong>Buying route:</strong> you’re live on the NHS Supply Chain catalogue (codes below) — ordering is the easy part.</div>';
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GRN + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">The case for switching — what are you giving them?</div><div style="font-size:14px;line-height:1.65;color:#39424d;margin-top:6px;">' + caseHtml + '</div></div>';

      // WHY TRUSTS ACTUALLY SWITCH — the evidenced drivers (researched & sourced),
      // auto-mapped: which does THIS case activate? Ticked = live in your case now.
      var DRIVERS = [
        {n:'Cost pressure / CIP savings', ev:'Product switches are a standard cost-improvement lever (Carter set a \u00a3700m procurement savings target; system needs \u00a311bn in 2025/26).', src:'https://www.gov.uk/government/news/review-shows-how-nhs-hospitals-can-save-money-and-improve-care',
          on: /sav|price|cost|%|cheap/i.test(edge||''), note:'your edge is a saving — quantify it against their CIP target'},
        {n:'Contract / framework renewal cycle', ev:'Frameworks run 2\u20134 years and new suppliers join at re-tender \u2014 the natural switch window.', src:'https://www.supplychain.nhs.uk/suppliers/contract-and-tender-process/',
          on: /award|202[6-8]/.test(mine.fwDates||''), note: mine.fwDates ? ('your framework timing: ' + mine.fwDates) : 'check the category\u2019s renewal date in the Procurement Calendar'},
        {n:'Value-based procurement scoring', ev:'DHSC national standard: five value domains carry a minimum 60% combined weighting; whole-life cost is capped at 40% \u2014 better-value challengers can beat cheaper incumbents.', src:'https://www.gov.uk/government/publications/value-based-procurement-for-medical-technology',
          on: true, note:'build the number in the Value Case Calculator \u2014 this is the scoring system your case is judged in'},
        {n:'Supply disruption / discontinuation', ev:'A forced suture switch in South Yorkshire saved \u00a3553,000 and spread to two more trusts \u2014 disruption is a proven switch trigger.', src:'https://www.supplychain.nhs.uk/news-article/suture-switch-collaboration/',
          on: (typeof wobbly !== 'undefined' && wobbly.length > 0), note:'a rival line shows a suspended/updated pack \u2014 lead with continuity of supply'},
        {n:'Supply-chain resilience / dual sourcing', ev:'Resilience is one of the five scored VBP value domains \u2014 a like-for-like second source de-risks a single-supplier category.', src:'https://www.nhsconfed.org/publications/supply-chain-resilience',
          on: comps.length > 0, note:'position as sensible dual-sourcing, not a rip-and-replace'},
        {n:'Standardisation / rationalising variation', ev:'Carter found 30,000 suppliers, 20,000 brands and 400,000+ product codes across 22 trusts \u2014 consolidation is policy.', src:'https://www.gov.uk/government/news/review-shows-how-nhs-hospitals-can-save-money-and-improve-care',
          on: comps.length >= 5, note:'a fragmented category \u2014 offer to simplify their range'},
        {n:'Clinical evaluation & clinician acceptance', ev:'Switches stick when clinicians co-own the evaluation; resistance breeds workarounds (published NHS evidence).', src:'https://pmc.ncbi.nlm.nih.gov/articles/PMC8512597/',
          on: (typeof trueTwin !== 'undefined' && !!trueTwin), note:'true like-for-like = a light evaluation \u2014 design it WITH their clinical lead'},
        {n:'Training & implementation support (scored)', ev:'Ease of use, training and implementation support are explicitly scored inside the mandatory 60% VBP value weighting.', src:'https://www.gov.uk/government/publications/value-based-procurement-for-medical-technology',
          on: ((typeof trueTwin !== 'undefined' && !!trueTwin) || /train|support|implement|educat/i.test(edge||'')), note:'same-steps switch or a training offer \u2014 either scores here'},
        {n:'Safety alerts & regulation', ev:'MHRA alerts and regulation force substitutions (e.g. the 2013 Sharps Regulations drove NHS-wide device switches).', src:'https://www.hse.gov.uk/pubns/hsis7.htm',
          on: false, note:'watch the Live Desk \u2014 if an alert touches the incumbent, this becomes your strongest driver overnight'},
        {n:'Sustainability / net zero', ev:'10% minimum social value weighting now; full scope 1\u20133 Carbon Reduction Plans required from April 2027.', src:'https://www.england.nhs.uk/long-read/2027-nhs-carbon-reduction-plan-requirements/',
          on: /carbon|sustain|green|packag/i.test(edge||''), note:'if you hold a carbon/packaging advantage, it is scored \u2014 quantify it in the Sustainability Calculator'},
        {n:'Relationships & trust', ev:'Established supplier contacts cement incumbents (published NHS evidence) \u2014 which is why the relationship IS the strategy.', src:'https://pmc.ncbi.nlm.nih.gov/articles/PMC8512597/',
          on: true, note:'people buy from people \u2014 your presence, service and follow-through are a scored and felt differentiator'},
        {n:'GIRFT data exposure', ev:'GIRFT\u2019s specialty reports flag procurement variation and directly prompt trusts to review products.', src:'https://gettingitrightfirsttime.co.uk/',
          on: /theatre|surg/i.test((mine.specs||[]).join(' ')) || mine.type === 'haemostat', note:'a surgical category \u2014 GIRFT variation data supports the standardisation conversation'}
      ];
      var dOn = DRIVERS.filter(function(d){ return d.on; });
      var dOff = DRIVERS.filter(function(d){ return !d.on; });
      function drow(d, on){
        return '<li style="margin:4px 0;' + (on ? '' : 'opacity:.55;') + '"><strong>' + (on ? '\u2713 ' : '\u00b7 ') + esc(d.n) + '</strong> — ' + d.ev + (on && d.note ? ' <span style="color:#14432f;font-weight:600;">Your case: ' + d.note + '.</span>' : (d.note ? ' <span style="color:#8a8778;">' + d.note + '.</span>' : '')) + ' <a href="' + d.src + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-size:11px;font-weight:600;">source &#8599;</a></li>';
      }
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GOLD + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">Why trusts actually switch — and where your case lands</div><div style="font-size:12px;color:#6b7684;margin:2px 0 6px;">The evidenced switch drivers from published NHS sources. \u2713 = active in your case now (' + dOn.length + ' of ' + DRIVERS.length + ').</div><ul style="margin:2px 0 0;padding-left:18px;font-size:13px;line-height:1.6;color:#39424d;">' + dOn.map(function(d){ return drow(d, true); }).join('') + dOff.map(function(d){ return drow(d, false); }).join('') + '</ul></div>';

      // WHY ONE OVER THE OTHER — real differences derived from the live catalogue
      // descriptions (material / mechanism / format / readiness), each with why it
      // matters in the buying conversation. Honest: only what the data supports.
      var myA = attrsOf(mine);
      function sellable(a){ return !!(a && (a.material || a.form || a.reg || a.latex || a.silver || a.bloodctl || a.needlefree || a.tint || a.dehp)); }
      if (myA && (sellable(myA) || comps.slice(0,5).some(function(p){ return sellable(attrsOf(p)); }))){
        var diffs2 = [];
        comps.slice(0, 5).forEach(function(p){
          var pa = attrsOf(p); if (!pa) return;
          var line = '<strong>vs ' + esc(p.name) + '</strong> (' + esc(p.supplier) + '): ';
          var pts = [];
          if (pa.material && myA.material && pa.material !== myA.material){
            pts.push('they are ' + esc(pa.material) + ', you are ' + esc(myA.material));
            if (/porcine/.test(pa.material) && /plant/.test(myA.material)) pts.push('<em>why it matters:</em> porcine-origin products are declined by some patients on faith or personal grounds — a plant-derived alternative removes that conversation entirely');
            else if (/biologic/.test(pa.material) && !/biologic/.test(myA.material)) pts.push('<em>why it matters:</em> biologic components bring preparation, storage and cost considerations a ready-to-use mechanical haemostat avoids');
            else if (/biologic/.test(myA.material) && !/biologic/.test(pa.material)) pts.push('<em>why it matters:</em> your active biologic mechanism is the premium argument — position on speed/reliability of haemostasis, not price');
          }
          if (pa.form && myA.form && pa.form !== myA.form){
            pts.push('their format is ' + esc(pa.form) + ', yours is ' + esc(myA.form));
            if (/flowable/.test(pa.form) && /fabric|sponge|patch/.test(myA.form)) pts.push('<em>why it matters:</em> a flowable needs an applicator and prep at the table; a fabric is open-and-apply');
          }
          if ((myA.reg || pa.reg) && myA.reg !== pa.reg){
            pts.push('the catalogue lists yours as ' + esc(myA.reg || 'unstated') + ' and theirs as ' + esc(pa.reg || 'unstated'));
            if (myA.reg && /licensed/.test(myA.reg) && pa.reg && /biocide/.test(pa.reg)) pts.push('<em>why it matters:</em> for skin prep before invasive procedures, medicines and IPC policies generally require a licensed medicine with that indication — a biocide is for general skin disinfection. This is the difference that wins the meeting; verify both SmPCs/labels first');
            else if (myA.reg && /biocide/.test(myA.reg) && pa.reg && /licensed/.test(pa.reg)) pts.push('<em>why it matters:</em> expect the licensing question if the use is pre-procedure skin prep — prepare your regulatory answer before the meeting');
          }
          if ((myA.latex || pa.latex) && myA.latex !== pa.latex){
            pts.push('yours is ' + esc(myA.latex || 'latex status unstated') + ', theirs is ' + esc(pa.latex || 'latex status unstated'));
            if (myA.latex === 'latex-free' && pa.latex === 'natural rubber latex') pts.push('<em>why it matters:</em> latex allergy (patients and staff) makes latex-free the default in many trust policies');
          }
          if (myA.silver && !pa.silver) pts.push('your entry carries a silver/antimicrobial element theirs does not mention — an infection-prevention angle (confirm against your IFU before quoting clinically)');
          if (pa.silver && !myA.silver) pts.push('their entry carries a silver/antimicrobial element yours does not — be ready to answer the infection-prevention question');
          if (myA.bloodctl && !pa.bloodctl) pts.push('your entry specifies blood-control technology theirs does not mention — a sharps/exposure-safety angle (the 2013 Sharps Regulations make exposure reduction a legal duty)');
          if (pa.bloodctl && !myA.bloodctl) pts.push('their entry specifies blood-control technology yours does not — know your answer on exposure safety');
          if (myA.needlefree && !pa.needlefree) pts.push('your entry includes an integrated needle-free connector theirs does not mention — fewer parts to order and fewer connections to break');
          if (myA.tint && !pa.tint) pts.push('your entry is a tinted solution and theirs does not mention tint — clinicians can see exactly where skin has been prepped');
          if (pa.tint && !myA.tint) pts.push('their entry is a tinted solution and yours does not mention tint — be ready for the visible-coverage point');
          if (pa.dehp && !myA.dehp) pts.push('their entry notes DEHP and yours does not mention it — if your product is DEHP-free, that supports the safety and sustainability conversation (verify before claiming)');
          if (!pts.length && (myA.material || myA.form) && pa.packs !== myA.packs) pts.push('closest match in material and format — the differences are pack range (' + myA.packs + ' vs ' + pa.packs + '), price and service, so your edge above carries the argument');
          if (pts.length) diffs2.push(line + pts.join('; ') + '.');
        });
        if (diffs2.length){
          h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + OX + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">Why one over the other — real differences from the catalogue data</div><div style="font-size:13.5px;line-height:1.65;color:#39424d;margin-top:6px;"><ul style="margin:2px 0 0;padding-left:18px;">' + diffs2.map(function(x){ return '<li style="margin:4px 0;">' + x + '</li>'; }).join('') + '</ul></div><div style="font-size:11.5px;color:#8a8778;margin-top:6px;">Derived from the products’ own NHS Supply Chain catalogue descriptions. Class-level differences — always confirm specifics against the manufacturer’s IFU before quoting clinically.</div></div>';
        }
      }

      // On-page product detail (image + every pack code) for your product + top competitors
      var withDetail = [mine].concat(comps).filter(function(p){ return detailFor(p); });
      if (withDetail.length){
        var cards = withDetail.slice(0, 7).map(function(p){ return detailCard(p, p === mine); }).join('');
        h += '<div style="margin:14px 0 4px;font-size:15px;font-weight:800;">Product detail — live from NHS Supply Chain</div>';
        h += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;">' + cards + '</div>';
        h += '<div style="font-size:11.5px;color:#8a8778;margin-top:6px;">Images, descriptions, pack sizes and NPC / MPC codes are drawn from the public NHS Supply Chain catalogue. Prices need a customer login.</div>';
      }

      // real difference
      var diffs = [];
      if (fwFor(mine)) diffs.push('You’re on <strong>' + esc(fwFor(mine)) + '</strong> — make the buying route easy.');
      else if (detailFor(mine)) diffs.push('You’re listed on the live NHS Supply Chain catalogue (codes below) — make the buying route easy.');
      var offFw = comps.filter(function(p){ return !fwFor(p) && !detailFor(p); }).length;
      if (offFw) diffs.push(offFw + ' competing product(s) show no confirmed framework or live catalogue listing — a route advantage worth naming.');
      if (kp(mine)) diffs.push('Your edge: ' + esc(kp(mine)));
      diffs.push('The detailed spec difference: use the AI prompt below (or it answers itself once the Hub AI is live).');
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + OX + ';border-radius:10px;padding:14px 16px;margin:14px 0 12px;"><div style="font-size:15px;font-weight:800;">The real difference — and how to use it</div><div style="font-size:14px;line-height:1.6;color:#39424d;margin-top:4px;"><ul style="margin:2px 0 0;padding-left:18px;">' + diffs.map(function(x){return '<li style="margin:2px 0;">'+x+'</li>';}).join('') + '</ul></div></div>';

      // optional angle
      var body;
      if (angle === 'Objection handling (MSTP)') body = objection(mine, comps);
      else body = (angle && ANGLE[angle] ? ANGLE[angle] : 'Optional — pick “what matters most” above for a tailored play, including Objection handling (MSTP): Acknowledge &rarr; Reframe &rarr; One more question.') + ' ' + link('Open the Value Case Calculator', 1109) + '.';
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GOLD + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">How you could use this' + (angle ? ' — ' + esc(angle) : ' (optional)') + '</div><div style="font-size:14px;line-height:1.65;color:#39424d;margin-top:4px;">' + body + '</div></div>';

      // AI prompt
      var names = comps.slice(0,4).map(function(p){ return p.name; }).join(', ') || 'the competing products';
      var prompt = 'Compare ' + mine.name + ' (' + mine.supplier + ') against ' + names + ' for an NHS buyer: the key clinical and practical differences, where each wins, and how I sell ' + mine.name + ' against them. Bullet points.';
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
