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

  var TYPES = ['antisepsis','antiseptic','chlorhexidine','skin prep','skin disinfect','disinfectant','applicator','swabstick','swab','tourniquet','blood culture','cannula','picc','midline','catheter','iol','intraocular','phaco','hearing aid','cochlear','stent','balloon','guidewire','sheath','mesh','suture','stapler','staple','skin closure','wound closure','tissue adhesive','glue','haemostat','sealant','dressing','foam','hydrocolloid','alginate','hydrofiber','silver','collagen','honey','barrier film','film dressing','bandage','compression','tape','plaster','npwt','negative pressure','glove','gown','drape','wipe','sanitiser','irrigation','ventilator','anaesthesia','laryngoscope','airway','tracheostomy','tracheal','bronchoscope','endoscope','colonoscope','gastroscope','scope','infusion pump','syringe pump','pump','syringe','needle','lancet','connector','stopcock','extension set','giving set','iv set','flush','implant','knee','hip','shoulder','robot','freezer','refrigerator','incubator','analyser','sequencer','defibrillator','monitor','ultrasound','mri','ct ','x-ray','mammography','bed','mattress','hoist','sling','wheelchair','cushion','dialyser','dialysis','apheresis','linac','brachytherapy','pacemaker','ablation','tavi','biopsy','warmer','warming','securement','ostomy','urostomy','stoma','nephrostomy','foley','feeding','enteral','feeding tube','peg tube','slide sheet','glucose','sensor','test strip','electrode','scalpel','blade','forceps','retractor','trocar','clip','clamp','specimen','drainage','chest drain','suction','mask','circuit','cpap','oxygen','nebuliser','filter','lubricant'];
  var KEYPOINTS = {
    'BD — Becton, Dickinson': { 'nexiva': 'Closed IV system — fewer blood exposures/disconnections vs an open cannula', 'chloraprep': 'Single-use 2% CHG / 70% IPA sterile applicator' },
    'Coloplast': { 'speedicath': 'Ready-to-use hydrophilic catheter — no water needed' },
    'Smith+Nephew': { 'pico': 'Single-use NPWT, no canister — NICE MTG43 evidence' }
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
    wrap.appendChild(el('div', 'font-size:14px;line-height:1.6;color:#4a5766;max-width:720px;margin-bottom:12px;', 'Type <strong>your product</strong> — the tool finds the competing products automatically and compares them like-for-like, showing the <strong>real NHS Supply Chain detail on the page</strong>: product image, description and every pack’s NPC / MPC code.'));

    var bar = el('div', 'display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:12px;margin-bottom:14px;');
    var pbox = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:300px;flex:2;');
    pbox.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', 'Your product'));
    var inp = el('input', 'padding:9px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;'); inp.type='text'; inp.setAttribute('list','msh-prod-list'); inp.placeholder='e.g. BD Nexiva, Aquacel, SpeediCath…';
    var dl = el('datalist'); dl.id='msh-prod-list';
    var seen={}; PRODUCTS.forEach(function(p){ var v=p.name+'  ·  '+p.supplier; if(!seen[v]){ seen[v]=1; var o=el('option'); o.value=v; dl.appendChild(o);} });
    pbox.appendChild(inp); pbox.appendChild(dl); bar.appendChild(pbox);
    var btn = el('button', 'background:' + OX + ';color:#fff;border:0;border-radius:8px;padding:10px 18px;font-weight:700;font-size:14px;cursor:pointer;', 'Compare');
    bar.appendChild(btn); wrap.appendChild(bar);

    // Secondary / optional refinement — the like-for-like comparison is the main output.
    var opt = el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:flex-end;margin:-6px 0 14px;padding-left:2px;');
    opt.appendChild(el('span', 'font-size:12px;color:#8a8778;align-self:center;', 'Optional — tailor the “how to use it” note:'));
    var selAng = mkSelect('What matters most (optional)', ['', 'Price / cost', 'Value & capacity', 'Clinical evidence', 'Sustainability', 'Objection handling (MSTP)']);
    opt.appendChild(selAng.box); wrap.appendChild(opt);
    function mkSelect(label, opts){
      var box = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:210px;');
      box.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#9a958a;', esc(label)));
      var sel = el('select', 'padding:7px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:13px;background:#fff;color:#6b7684;');
      opts.forEach(function(o){ var op = el('option'); op.value = o; op.textContent = o || '— none —'; sel.appendChild(op); });
      box.appendChild(sel); return { box: box, sel: sel };
    }

    var out = el('div', 'margin-top:6px;'); wrap.appendChild(out);
    MOUNT.innerHTML = ''; MOUNT.appendChild(wrap);

    btn.addEventListener('click', function(){
      var v = inp.value.trim();
      var mine = PRODUCTS.filter(function(p){ return (p.name+'  ·  '+p.supplier) === v; })[0]
              || PRODUCTS.filter(function(p){ return p.name.toLowerCase() === v.toLowerCase(); })[0]
              || PRODUCTS.filter(function(p){ return v && p.name.toLowerCase().indexOf(v.toLowerCase()) !== -1; })[0];
      out.innerHTML = compare(mine, selAng.sel.value);
      addCopy(out);
      out.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

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
        same.sort(function(a, b){ return specOverlap(mine.specs, b.specs) - specOverlap(mine.specs, a.specs); });
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
      } else {
        codeCell = '<a href="' + lookupUrl(p.name) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-weight:600;">look up &#8599;</a>';
      }
      return '<tr style="' + hl + 'border-bottom:1px solid ' + LINE + ';vertical-align:top;">'
        + '<td style="padding:7px 9px;">' + prodCell + '</td>'
        + '<td style="padding:7px 9px;">' + esc(p.supplier) + '</td>'
        + '<td style="padding:7px 9px;color:#5a6470;font-size:12.5px;">' + (p.framework ? esc(p.framework) : '<span style="color:#8a8778;">—</span>') + '</td>'
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
        + '<li><strong>Reframe</strong> to your edge: ' + esc(edge) + (mine.framework ? ' — and it’s on ' + esc(mine.framework) + '.' : '.') + '</li>'
        + '<li><strong>One more question:</strong> “If I could show you where ' + esc(mine.name) + ' saves time or reduces a complication versus ' + esc(top ? top.name : 'your current option') + ', would that be worth a short trial?”</li>'
        + '</ul>';
    }

    function compare(mine, angle){
      if (!mine){ return '<div style="color:#8a6d00;font-size:14px;padding:8px 0;">Type your product above (start typing to pick from the list) and press Compare.</div>'; }
      var comps = competitorsOf(mine);
      var h = '<div style="font-size:13px;color:#6b7684;margin:6px 0 4px;">Your product: <strong>' + esc(mine.name) + '</strong> (' + esc(mine.supplier) + ')' + (mine.type ? ' · type: ' + esc(mine.type) : '') + ' · ' + comps.length + ' competing products found</div>';

      // Like-for-like table (primary output)
      h += '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13.5px;min-width:680px;background:#fff;border:1px solid ' + LINE + ';border-radius:10px;">'
        + '<thead><tr style="background:' + OX + ';color:#fff;text-align:left;"><th style="padding:8px 9px;">Product</th><th style="padding:8px 9px;">Supplier</th><th style="padding:8px 9px;">On framework</th><th style="padding:8px 9px;">NHSSC code (live)</th><th style="padding:8px 9px;">Key point</th></tr></thead><tbody>'
        + row(mine, true) + comps.map(function(p){ return row(p, false); }).join('') + '</tbody></table></div>';
      if (!comps.length) h += '<div style="font-size:12.5px;color:#8a8778;margin-top:4px;">No competing products matched automatically — broaden the product name or check the supplier directory.</div>';

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
      if (mine.framework) diffs.push('You’re on <strong>' + esc(mine.framework) + '</strong> — make the buying route easy.');
      var offFw = comps.filter(function(p){ return !p.framework; }).length;
      if (offFw) diffs.push(offFw + ' competing product(s) show no confirmed framework — a route advantage worth naming.');
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

      h += '<div style="font-size:12px;color:#8a8778;">Product names are the suppliers’ own; framework is top-level (verify the lot at source); NPC / MPC codes and images are from the public NHS Supply Chain catalogue (prices need login). Nothing is invented.</div>';
      return h;
    }

    function addCopy(container){
      if (!container.textContent || container.textContent.indexOf('Type your product') !== -1) return;
      var b = el('button', 'background:' + INK + ';color:#fff;border:0;border-radius:8px;padding:8px 14px;font-weight:700;font-size:13px;cursor:pointer;margin:4px 0 10px;', 'Copy brief');
      b.addEventListener('click', function(){ var t = container.innerText.replace('Copy brief','').trim(); if (navigator.clipboard) { navigator.clipboard.writeText(t); b.textContent='Copied ✓'; setTimeout(function(){ b.textContent='Copy brief'; }, 1500); } });
      container.insertBefore(b, container.firstChild);
    }
  }
})();
