/* NHS Intelligence Hub — Product Comparison tool (PRODUCT-FIRST).
   Enter YOUR product -> it auto-finds competitor products (same device type /
   speciality across other suppliers) -> compares at product level (name,
   supplier, framework, NHSSC code where known, key points), then layers on the
   real difference, the audience angle (incl. the MSTP objection method), the
   value case and an AI prompt. Copy-brief button included. */
(function () {
  var MOUNT = document.getElementById('msh-compare-tool');
  if (!MOUNT) return;
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var GOLD = '#a8842c', OX = '#6B2A34', GRN = '#2E6B3E', INK = '#20303f', LINE = '#e6e2d8', PANEL = '#ffffff', SOFT = '#f7f5ef';
  var IDX = BASE + 'data/supplier-index.json?cb=' + Date.now();
  var CFG = BASE + 'data/prep-config.json?cb=' + Date.now();
  var SEED = BASE + 'data/supplier-seed.json?cb=' + Date.now();

  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function el(tag, css, html){ var e = document.createElement(tag); if (css) e.style.cssText = css; if (html != null) e.innerHTML = html; return e; }

  // Device-type tokens used to auto-match competing products across suppliers.
  var TYPES = ['cannula','picc','midline','catheter','iol','intraocular','phaco','hearing aid','cochlear','stent','balloon','guidewire','sheath','mesh','suture','stapler','haemostat','sealant','dressing','foam','hydrocolloid','alginate','hydrofiber','npwt','glove','gown','drape','wipe','sanitiser','irrigation','ventilator','anaesthesia','laryngoscope','airway','bronchoscope','endoscope','colonoscope','gastroscope','scope','infusion pump','syringe pump','pump','syringe','needle','connector','flush','implant','knee','hip','shoulder','robot','freezer','refrigerator','incubator','analyser','sequencer','defibrillator','monitor','ultrasound','mri','ct ','x-ray','mammography','bed','mattress','hoist','sling','wheelchair','cushion','dialyser','dialysis','apheresis','linac','brachytherapy','pacemaker','ablation','tavi','biopsy','warmer','securement','ostomy','urostomy','enteral','feeding tube','slide sheet'];
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
    fetch(SEED).then(function(r){return r.json();}).catch(function(){return {suppliers:[]};})
  ]).then(function(res){ render(res[0], res[1], res[2]); })
    .catch(function(){ MOUNT.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:#8a6d00;">Comparison tool temporarily unavailable — please try again shortly.</div>'; });

  function render(index, cfg, seed){
    var suppliers = (index && index.suppliers) || [];
    var seedMap = {}; ((seed && seed.suppliers) || []).forEach(function(s){ seedMap[s.name] = s; });
    suppliers.forEach(function(s){ var sd = seedMap[s.name]; if (sd){ ['voice','products','frameworks','specialities'].forEach(function(k){ if (sd[k] && (!Array.isArray(sd[k]) || sd[k].length)) s[k] = sd[k]; }); } });
    var have = {}; suppliers.forEach(function(s){ have[s.name] = 1; });
    ((seed && seed.suppliers) || []).forEach(function(s){ if (!have[s.name]){ s.curated = true; suppliers.push(s); } });

    // Flatten to a product index.
    var PRODUCTS = [];
    suppliers.forEach(function(s){
      (s.products || []).forEach(function(p){
        var name = typeof p === 'string' ? p : (p && p.name);
        if (!name) return;
        PRODUCTS.push({ name: name, code: (p && p.code) || '', supplier: s.name, specs: s.specialities || [], framework: (s.frameworks && s.frameworks[0] && s.frameworks[0].name) || '', voice: s.voice, type: typeOf(name) });
      });
    });
    function typeOf(n){ n = (n||'').toLowerCase(); for (var i=0;i<TYPES.length;i++){ if (n.indexOf(TYPES[i]) !== -1) return TYPES[i].trim(); } return ''; }
    function kp(prod){ var m = KEYPOINTS[prod.supplier]; if (!m) return ''; var n = prod.name.toLowerCase(); for (var k in m){ if (n.indexOf(k) !== -1) return m[k]; } return ''; }

    var wrap = el('div', 'font-family:Inter,system-ui,sans-serif;color:' + INK + ';');
    wrap.appendChild(el('div', 'text-transform:uppercase;letter-spacing:2px;font-size:11px;font-weight:700;color:' + OX + ';', 'NHS Intelligence Hub'));
    wrap.appendChild(el('div', 'font-size:24px;font-weight:800;margin:2px 0 4px;', 'Product Comparison'));
    wrap.appendChild(el('div', 'font-size:14px;line-height:1.6;color:#4a5766;max-width:720px;margin-bottom:12px;', 'Type <strong>your product</strong> — the tool finds the competing products automatically and compares them at product level (supplier, framework, live NHSSC-code lookup, key points), then shows the real difference and how to use it.'));

    var bar = el('div', 'display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:12px;margin-bottom:14px;');
    // product autocomplete
    var pbox = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:280px;flex:2;');
    pbox.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', 'Your product'));
    var inp = el('input', 'padding:9px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;'); inp.type='text'; inp.setAttribute('list','msh-prod-list'); inp.placeholder='e.g. BD Nexiva, Aquacel, SpeediCath…';
    var dl = el('datalist'); dl.id='msh-prod-list';
    var seen={}; PRODUCTS.forEach(function(p){ var v=p.name+'  ·  '+p.supplier; if(!seen[v]){ seen[v]=1; var o=el('option'); o.value=v; dl.appendChild(o);} });
    pbox.appendChild(inp); pbox.appendChild(dl); bar.appendChild(pbox);
    var selAng = mkSelect('What matters most', ['', 'Price / cost', 'Value & capacity', 'Clinical evidence', 'Sustainability', 'Objection handling (MSTP)']);
    bar.appendChild(selAng.box);
    var btn = el('button', 'background:' + OX + ';color:#fff;border:0;border-radius:8px;padding:10px 18px;font-weight:700;font-size:14px;cursor:pointer;', 'Compare');
    bar.appendChild(btn); wrap.appendChild(bar);
    function mkSelect(label, opts){
      var box = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:190px;flex:1;');
      box.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', esc(label)));
      var sel = el('select', 'padding:9px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;background:#fff;color:' + INK + ';');
      opts.forEach(function(o){ var op = el('option'); op.value = o; op.textContent = o || '— choose —'; sel.appendChild(op); });
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
    function competitorsOf(mine){
      var byType = mine.type ? PRODUCTS.filter(function(p){ return p.supplier !== mine.supplier && p.type === mine.type; }) : [];
      var bySpec = PRODUCTS.filter(function(p){ return p.supplier !== mine.supplier && p.specs.some(function(x){ return mine.specs.indexOf(x) !== -1; }); });
      var seen = {}, out = [];
      byType.concat(bySpec).forEach(function(p){ var k = p.name + '|' + p.supplier; if (!seen[k]){ seen[k] = 1; out.push(p); } });
      return out.slice(0, 12);
    }

    function row(p, mine){
      var hl = mine ? 'background:#fbeef0;font-weight:600;' : '';
      var kpt = kp(p);
      return '<tr style="' + hl + 'border-bottom:1px solid ' + LINE + ';">'
        + '<td style="padding:7px 9px;">' + esc(p.name) + (mine ? ' <span style="color:' + OX + ';font-size:11px;">(you)</span>' : '') + '</td>'
        + '<td style="padding:7px 9px;">' + esc(p.supplier) + '</td>'
        + '<td style="padding:7px 9px;color:#5a6470;font-size:12.5px;">' + (p.framework ? esc(p.framework) : '<span style="color:#8a8778;">—</span>') + '</td>'
        + '<td style="padding:7px 9px;color:#5a6470;">' + (p.code ? esc(p.code) : '<a href="https://pilot.supplychain.nhs.uk/search?query=' + encodeURIComponent(p.name.replace(/\s*\(.*?\)\s*/g,' ').trim()) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-weight:600;">look up &#8599;</a>') + '</td>'
        + '<td style="padding:7px 9px;color:#39424d;font-size:12.5px;">' + (kpt ? esc(kpt) : '<span style="color:#8a8778;">—</span>') + '</td></tr>';
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
      var sq = mine.supplier.indexOf('—') >= 0 ? mine.supplier.split('—')[1] : mine.supplier;
      sq = sq.replace(/\(.*?\)/g,'').replace(/,/g,' ').replace(/\bLtd\b|\bLimited\b|\bUK\b|\bGroup\b/gi,'').trim();
      h += '<div style="font-size:12.5px;margin:0 0 8px;"><a href="https://pilot.supplychain.nhs.uk/search?query=' + encodeURIComponent(sq) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-weight:600;">See all of ' + esc(mine.supplier) + '&rsquo;s live products &amp; NPC codes on NHS Supply Chain &#8599;</a></div>';
      h += '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13.5px;min-width:640px;background:#fff;border:1px solid ' + LINE + ';border-radius:10px;">'
        + '<thead><tr style="background:' + OX + ';color:#fff;text-align:left;"><th style="padding:8px 9px;">Product</th><th style="padding:8px 9px;">Supplier</th><th style="padding:8px 9px;">On framework</th><th style="padding:8px 9px;">NHSSC code</th><th style="padding:8px 9px;">Key point</th></tr></thead><tbody>'
        + row(mine, true) + comps.map(function(p){ return row(p, false); }).join('') + '</tbody></table></div>';
      if (!comps.length) h += '<div style="font-size:12.5px;color:#8a8778;margin-top:4px;">No competing products matched automatically — broaden the product name or check the supplier directory.</div>';

      // real difference
      var diffs = [];
      if (mine.framework) diffs.push('You’re on <strong>' + esc(mine.framework) + '</strong> — make the buying route easy.');
      var offFw = comps.filter(function(p){ return !p.framework; }).length;
      if (offFw) diffs.push(offFw + ' competing product(s) show no confirmed framework — a route advantage worth naming.');
      if (kp(mine)) diffs.push('Your edge: ' + esc(kp(mine)));
      diffs.push('The detailed spec difference: use the AI prompt below (or it answers itself once the Hub AI is live).');
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + OX + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">The real difference — and how to use it</div><div style="font-size:14px;line-height:1.6;color:#39424d;margin-top:4px;"><ul style="margin:2px 0 0;padding-left:18px;">' + diffs.map(function(x){return '<li style="margin:2px 0;">'+x+'</li>';}).join('') + '</ul></div></div>';

      // angle
      var body;
      if (angle === 'Objection handling (MSTP)') body = objection(mine, comps);
      else body = (angle && ANGLE[angle] ? ANGLE[angle] : 'Pick “what matters most” for a tailored play — including Objection handling (MSTP): Acknowledge &rarr; Reframe &rarr; One more question.') + ' ' + link('Open the Value Case Calculator', 1109) + '.';
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GOLD + ';border-radius:10px;padding:14px 16px;margin:12px 0;"><div style="font-size:15px;font-weight:800;">How you could use this' + (angle ? ' — ' + esc(angle) : '') + '</div><div style="font-size:14px;line-height:1.65;color:#39424d;margin-top:4px;">' + body + '</div></div>';

      // AI prompt
      var names = comps.slice(0,4).map(function(p){ return p.name; }).join(', ') || 'the competing products';
      var prompt = 'Compare ' + mine.name + ' (' + mine.supplier + ') against ' + names + ' for an NHS buyer: the key clinical and practical differences, where each wins, and how I sell ' + mine.name + ' against them. Bullet points.';
      h += '<div style="background:' + SOFT + ';border:1px dashed ' + GOLD + ';border-radius:10px;padding:12px 16px;margin:12px 0;"><div style="font-size:13px;font-weight:700;color:' + INK + ';">Deep product-by-product detail — copy into your AI assistant:</div><div style="font-size:13px;color:#39424d;background:#fff;border:1px solid ' + LINE + ';border-radius:6px;padding:8px 10px;margin-top:6px;font-family:ui-monospace,Menlo,monospace;">' + esc(prompt) + '</div><div style="font-size:12px;color:#8a8778;margin-top:6px;">Once the Hub’s AI integration is live, this answers itself in-tool.</div></div>';

      h += '<div style="font-size:12px;color:#8a8778;">Product names are the suppliers’ own; framework is top-level (verify the lot at source); the <strong>NHSSC-code</strong> column links to the live public NHS Supply Chain catalogue — click to see every NPC / MPC code and pack size (prices need login). Nothing is invented.</div>';
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
