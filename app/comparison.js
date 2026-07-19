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
    'BD — Becton, Dickinson': { 'nexiva': 'Closed IV system — fewer blood exposures/disconnections vs an open cannula', 'chloraprep': 'Single-use 2% CHG / 70% IPA sterile applicator' },
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
        PRODUCTS.push({ name: name, code: (p && p.code) || '', supplier: s.name, specs: s.specialities || [], framework: (s.frameworks && s.frameworks[0] && s.frameworks[0].name) || '', voice: s.voice, type: typeForProduct(name) });
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
      'vascular access': ['cannula','picc','midline','catheter','connector','flush','securement','needle','syringe','extension set','giving set','iv set','stopcock','infusion pump','syringe pump','pump'],
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

    var out = el('div', 'margin-top:6px;'); wrap.appendChild(out);
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
      var caseHtml;
      if (!edge && !wobbly.length && !kp(mine)){
        caseHtml = '<div style="background:#fbf3df;border:1px solid #e8d5a8;border-radius:8px;padding:10px 14px;margin:0 0 8px;font-size:13.5px;color:#7a5b14;"><strong>The data shows no obvious switch reason — so what\\u2019s yours?</strong> If nothing is wrong with their current supplier, the trust has no reason to change. Type your edge above (a price saving, next-day supply, service and training, UK stockholding, clinical preference) and the case builds around it.</div>'
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
        caseHtml += '<div style="margin-top:10px;padding:10px 14px;background:#edf5ee;border-left:3px solid ' + GRN + ';border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.6;color:#39424d;"><strong>Then like-for-like closes it.</strong> Once your reason is on the table, being the same class as ' + esc(top.name) + (shared.length ? ' (' + esc(shared.slice(0,3).join(', ')) + ')' : '') + ' works <em>for</em> you: no clinical retraining, no pathway change, a straightforward side-by-side evaluation and simple substitution on the order template. Switching becomes a low-risk decision for the trust — that is the point to make, not \\u201cwe\\u2019re the same\\u201d.</div>';
      }
      if (fwFor(mine)) caseHtml += '<div style="margin-top:8px;font-size:13px;color:#5a6470;"><strong>Buying route:</strong> you\\u2019re on ' + esc(fwFor(mine)) + ' — ordering is the easy part.</div>';
      else if (dMine) caseHtml += '<div style="margin-top:8px;font-size:13px;color:#5a6470;"><strong>Buying route:</strong> you\\u2019re live on the NHS Supply Chain catalogue (codes below) — ordering is the easy part.</div>';
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GRN + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">The case for switching — what are you giving them?</div><div style="font-size:14px;line-height:1.65;color:#39424d;margin-top:6px;">' + caseHtml + '</div></div>';

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
