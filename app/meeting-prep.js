/* NHS Intelligence Hub — Meeting Prep + Product Comparison ("Help me prepare")
   Company + speciality + trust + WHO you're meeting -> a tailored brief:
   competitors & how you stack up, the right angle for that audience, the value
   case, frameworks, national context, trust strategy and who to look up.
   Reads the live supplier index + curated seed + prep-config. Served from GitHub. */
(function () {
  var MOUNT = document.getElementById('msh-meeting-prep');
  if (!MOUNT) return;
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var GOLD = '#a8842c', INK = '#20303f', LINE = '#e6e2d8', PANEL = '#ffffff', SOFT = '#f7f5ef';
  var IDX = BASE + 'data/supplier-index.json?cb=' + Date.now();
  var CFG = BASE + 'data/prep-config.json?cb=' + Date.now();
  var SEED = BASE + 'data/supplier-seed.json?cb=' + Date.now();
  var SPECMAP = BASE + 'data/speciality-map.json?cb=' + Date.now();
  var PRODUCTS = BASE + 'data/supplier-products.json?cb=' + Date.now();

  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function el(tag, css, html){ var e = document.createElement(tag); if (css) e.style.cssText = css; if (html != null) e.innerHTML = html; return e; }

  var AUD = {
    'Procurement / finance': { key:'finance', line:'Lead with money and value: what it saves now, the whole-life cost, and the capacity it frees. Tie it to the trust’s own cost and strategy priorities (from their annual report), and frame it as value-based procurement — save AND deliver value.' },
    'Clinical manager': { key:'manager', line:'Answer the rollout questions before they’re asked: how training is delivered, how you’d implement without disruption, change-management support, and the evidence it works at scale.' },
    'Clinical end-user': { key:'user', line:'Make it about the bedside: how easy it is to use, how it benefits the patient, and the time it saves the team. Offer trials, in-service training and peer evidence.' },
    'Sustainability lead': { key:'green', line:'Lead with carbon and net zero: reusable-vs-single-use whole-life impact, your Carbon Reduction Plan (Evergreen is scored at tender from Apr 2026), and packaging/energy. Frame value as patient, planet and public purse.' }
  };

  MOUNT.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:' + INK + ';padding:6px 0;">Loading meeting prep…</div>';
  Promise.all([
    fetch(IDX).then(function(r){return r.json();}),
    fetch(CFG).then(function(r){return r.json();}),
    fetch(SEED).then(function(r){return r.json();}).catch(function(){return {suppliers:[]};}),
    fetch(SPECMAP).then(function(r){return r.json();}).catch(function(){return null;}),
    fetch(PRODUCTS).then(function(r){return r.json();}).catch(function(){return null;})
  ]).then(function(res){ render(res[0], res[1], res[2], res[3], res[4]); })
    .catch(function(){ MOUNT.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:#8a6d00;">Meeting prep is temporarily unavailable — please try again shortly.</div>'; });

  function render(index, cfg, seed, specMap, prodFile){
    /* Verified full ranges live in supplier-products.json, NOT in the seed —
       supplier-seed.json is declared human-owned and never-overwritten by
       build_supplier_index.py, and Lou's hand-written product names carry
       meaning the raw catalogue titles don't. So: a supplier present in the
       products file uses that verified, speciality-tagged range; a supplier
       absent from it falls back to the seed's curated list, untagged and
       therefore unfiltered. Lets the sweep expand one supplier at a time. */
    var PRODS = (prodFile && prodFile.suppliers) || null;
    function verifiedRangeFor(name){
      if (!PRODS || !name) return null;
      if (PRODS[name]) return PRODS[name];
      for (var k in PRODS){
        var al = PRODS[k].aliases || [];
        if (al.indexOf(name) !== -1) return PRODS[k];
      }
      return null;
    }
    /* Canonical speciality vocabulary. Three lists had drifted apart and were
       matched by exact string equality: the mapper's 30, this tool's 8, and 60
       free-text strings across the suppliers. The result was that 3 of the 8
       dropdown values matched NO supplier at all - returning an empty competitor
       list that read as "no competitors" rather than "lookup failed" - and 146
       of 188 suppliers were unreachable from any speciality.
       speciality-map.json reconciles all three onto the mapper's 30. Falls back
       to the old exact-match behaviour if the map cannot be loaded. */
    var CANON = (specMap && specMap.canonicalSpecialities) || null;
    var SMAP  = (specMap && specMap.supplierSpecialityMap) || null;
    var LABEL_TO_ID = {}; if (CANON) CANON.forEach(function(c){ LABEL_TO_ID[c.label] = c.id; });
    // A supplier string may map to SEVERAL canonical ids where it genuinely spans
    // both (e.g. "Respiratory / anaesthesia"), so a supplier is reachable from
    // either side of its real market rather than an arbitrary single pick.
    function canonIds(list){
      var out = {};
      (list || []).forEach(function(s){
        var m = SMAP && SMAP[s];
        if (m && m.to) m.to.forEach(function(id){ out[id] = 1; });
        else if (LABEL_TO_ID[s]) out[LABEL_TO_ID[s]] = 1;
      });
      /* Roll child specialities into their parent (e.g. Blood collection /
         phlebotomy is filed under Vascular access in the taxonomy, with its
         own buying stakeholder — see speciality-map.json's placementNote).
         Selecting the parent must also surface child-only suppliers, same as
         mst-logic.js's SPECS[].parent rollup for the Stakeholder Mapper —
         otherwise picking "Vascular access" here silently misses GBUK and
         anyone else who only sells blood collection. */
      if (CANON) CANON.forEach(function(c){
        if (c.parent && out[c.parent]) out[c.id] = 1;
      });
      return Object.keys(out);
    }
    /* A supplier's specialities and its product tags were unconnected, so a
       supplier could sell a whole category and still be unreachable from it —
       GBUK sells 9 blood collection lines but its seed specialities never say
       "blood collection", so it returned no competitors there. Deriving the
       extra specialities from the verified product tags fixes that without
       editing the curated seed. */
    function supplierSpecIds(s){
      var ids = canonIds(s && s.specialities);
      var v = verifiedRangeFor(s && s.name);
      if (v){
        var seen = {};
        ids.forEach(function(i){ seen[i] = 1; });
        (v.products || []).forEach(function(p){ if (p.s) seen[p.s] = 1; });
        ids = Object.keys(seen);
      }
      return ids;
    }
    function sharesSpeciality(a, bSupplier){
      if (!SMAP){
        var bl = (bSupplier && bSupplier.specialities) || [];
        return (a || []).some(function(x){ return bl.indexOf(x) !== -1; });
      }
      var A = canonIds(a), B = supplierSpecIds(bSupplier);
      return A.some(function(id){ return B.indexOf(id) !== -1; });
    }
    var suppliers = (index && index.suppliers) || [];
    var seedMap = {}; ((seed && seed.suppliers) || []).forEach(function(s){ seedMap[s.name] = s; });
    suppliers.forEach(function(s){ var sd = seedMap[s.name]; if (sd){ if (sd.voice) s.voice = sd.voice; if (sd.products && sd.products.length) s.products = sd.products; if (sd.frameworks && sd.frameworks.length) s.frameworks = sd.frameworks; if (sd.specialities && sd.specialities.length) s.specialities = sd.specialities; } });
    // Union in any curated seed supplier not yet in the index, so new suppliers show immediately (independent of the refresh cadence).
    var have = {}; suppliers.forEach(function(s){ have[s.name] = 1; });
    ((seed && seed.suppliers) || []).forEach(function(s){ if (!have[s.name]){ s.curated = true; suppliers.push(s); } });
    var curated = suppliers.filter(function(s){ return s.curated; }).sort(byName);
    var rest = suppliers.filter(function(s){ return !s.curated; }).sort(byName);
    function byName(a,b){ return (a.name||'').toLowerCase() < (b.name||'').toLowerCase() ? -1 : 1; }

    var wrap = el('div', 'font-family:Inter,system-ui,sans-serif;color:' + INK + ';');
    wrap.appendChild(el('div', 'text-transform:uppercase;letter-spacing:2px;font-size:11px;font-weight:700;color:' + GOLD + ';', 'NHS Intelligence Hub'));
    wrap.appendChild(el('div', 'font-size:24px;font-weight:800;margin:2px 0 4px;', 'Help me prepare'));
    wrap.appendChild(el('div', 'font-size:14px;line-height:1.6;color:#4a5766;max-width:660px;margin-bottom:12px;', 'Pick who you are, the speciality, the trust and <strong>who you’re meeting</strong>. You get your competitors and how you stack up, the right angle for that person, the value case, and what to know about the trust — pulled from the whole Hub. Tick “early-stage” if you’re not on a product yet.'));

    var bar = el('div', 'display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:12px;margin-bottom:14px;');
    var selCo = mkSelect('Your company', [''].concat(curated.map(nm)).concat(rest.length ? ['— other suppliers —'] : []).concat(rest.map(nm)));
    // Product picker. Was missing entirely — product could only reach the brief
    // via hand-off from Product Comparison, so anyone starting here had no way
    // to say what they sell. Repopulates whenever the company changes.
    var selPr = mkSelect('Product', ['']);
    /* A product entry is either a plain string (legacy, untagged) or
       {n:'name', s:'Speciality'} once it has been speciality-tagged. Normalising
       here lets tagging roll out supplier by supplier without a flag day - a
       supplier with tags filters correctly, one without still lists its range. */
    function normProducts(co){
      var verified = verifiedRangeFor(co && co.name);
      var list = verified ? verified.products : ((co && co.products) || []);
      return list.map(function(p){
        return typeof p === 'string' ? { n: p, s: '' } : { n: p.n || p.name || '', s: p.s || p.speciality || '' };
      }).filter(function(p){ return p.n; });
    }
    function fillProducts(){
      var co = suppliers.filter(function(s){ return s.name === selCo.sel.value; })[0];
      var all = normProducts(co);
      var spec = selSp.sel.value;
      var tagged = all.filter(function(p){ return p.s; });
      // Only filter when this supplier actually has tags AND a speciality is chosen.
      // Otherwise showing a filtered-looking list would imply a scoping we can't do.
      // Compare on canonical id so a product tagged with an id, a canonical
      // label, or a legacy supplier string all resolve to the same speciality.
      function specId(v){
        if (!v) return '';
        if (LABEL_TO_ID[v]) return LABEL_TO_ID[v];
        var viaMap = SMAP && SMAP[v] && SMAP[v].to && SMAP[v].to[0];
        return viaMap || v;
      }
      var want = specId(spec);
      /* Sub-specialities. Blood collection sits UNDER vascular access — NHSSC,
         eClass, BD's own segments and GBUK's own catalogue all file it there —
         but it has a different buying centre (pathology/blood sciences), so it
         stays separately selectable. Picking the parent must therefore include
         the children, or a rep working vascular would miss half the category. */
      var kids = CANON ? CANON.filter(function(c){ return c.parent === want; })
                              .map(function(c){ return c.id; }) : [];
      var wanted = [want].concat(kids);
      var scoped = (spec && tagged.length)
        ? all.filter(function(p){ return wanted.indexOf(specId(p.s)) !== -1; })
        : all;
      var partial = spec && tagged.length && tagged.length < all.length;
      var keep = selPr.sel.value;
      selPr.sel.innerHTML = '';
      [''].concat(scoped.map(function(p){ return p.n; })).forEach(function(n){
        var op = el('option'); op.value = n;
        op.textContent = n || (!all.length ? '— pick your company first —'
          : (scoped.length ? '— choose —' : '— none listed for this speciality —'));
        selPr.sel.appendChild(op);
      });
      if (keep && scoped.some(function(p){ return p.n === keep; })) selPr.sel.value = keep;
      selPr.sel.disabled = !scoped.length;
      selPr.sel.style.background = scoped.length ? '#fff' : '#f4f2ee';
      // Be honest when the range is only part-tagged, rather than silently
      // presenting an incomplete list as if it were the whole speciality.
      var hint = document.getElementById('msh-prod-hint');
      if (hint) hint.textContent = partial
        ? 'Showing tagged products for this speciality; this supplier’s range is still being tagged.'
        : '';
    }
    selCo.sel.addEventListener('change', fillProducts);
    // Picking a product means you are not early-stage; keep the two in step.
    selPr.sel.addEventListener('change', function(){ if (selPr.sel.value) early.checked = false; });

    // Canonical 30 when the map is available, else the legacy 8 from prep-config.
    var SPEC_OPTS = CANON ? CANON.map(function(c){ return c.label; }) : (cfg.specialities || []);
    var selSp = mkSelect('Speciality', [''].concat(SPEC_OPTS));
    var profiledNames = (cfg.trusts || []).map(function(t){ return t.name; });
    // trustDirectory entries may be strings (legacy) or {n,code,town,postcode,kind} objects.
    var DIRMAP = {};
    var dirEntries = (cfg.trustDirectory || []).map(function(e){ return typeof e === 'string' ? { n: e } : e; })
      .filter(function(e){ return profiledNames.indexOf(e.n) === -1; });
    dirEntries.forEach(function(e){ DIRMAP[e.n] = e; });
    var hosp = dirEntries.filter(function(e){ return !e.kind || e.kind === 'Hospital / acute'; }).map(function(e){ return e.n; });
    var others = dirEntries.filter(function(e){ return e.kind && e.kind !== 'Hospital / acute'; }).map(function(e){ return e.n; });
    var selTr = mkSelect('Hospital / trust', ['']
      .concat(profiledNames.length ? ['— full Hub profile —'] : []).concat(profiledNames)
      .concat(hosp.length ? ['— hospital / acute trusts —'] : []).concat(hosp)
      .concat(others.length ? ['— community, mental health & ambulance —'] : []).concat(others)
      .concat(['Other / any trust']));
    var selAud = mkSelect('Who you’re meeting', ['', 'Procurement / finance', 'Clinical manager', 'Clinical end-user', 'Sustainability lead']);
    var earlyWrap = el('label', 'font-size:13px;color:#4a5766;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;');
    var early = el('input'); early.type = 'checkbox';
    earlyWrap.appendChild(early); earlyWrap.appendChild(document.createTextNode('Early-stage (no product yet)'));
    var btn = el('button', 'background:#6B2A34 !important;color:#ffffff !important;border:0;border-radius:8px;padding:12px 24px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.3px;box-shadow:0 1px 3px rgba(0,0,0,.15);', 'Prepare me');
    [selCo.box, selPr.box, selSp.box, selTr.box, selAud.box].forEach(function(b){ bar.appendChild(b); });
    // Changing speciality must re-scope the product list, not just the brief.
    selSp.sel.addEventListener('change', fillProducts);
    var prodHint = el('div', 'font-size:11.5px;color:#8a6d00;margin-top:3px;line-height:1.4;');
    prodHint.id = 'msh-prod-hint';
    selPr.box.appendChild(prodHint);
    fillProducts();
    var side = el('div', 'display:flex;flex-direction:column;gap:8px;'); side.appendChild(earlyWrap); side.appendChild(btn); bar.appendChild(side);
    wrap.appendChild(bar);
    function nm(s){ return s.name; }
    function mkSelect(label, opts){
      var box = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:180px;flex:1;');
      box.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', esc(label)));
      var sel = el('select', 'padding:9px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;background:#fff;color:' + INK + ';');
      opts.forEach(function(o){ var op = el('option'); op.value = (o.indexOf('—') === 0 ? '' : o); op.textContent = o || '— choose —'; if (o.indexOf('—') === 0) op.disabled = true; sel.appendChild(op); });
      box.appendChild(sel); return { box: box, sel: sel };
    }
    var out = el('div', 'margin-top:6px;'); out.id='msh-prep-out'; wrap.appendChild(out);
    MOUNT.innerHTML = ''; MOUNT.appendChild(wrap);

    // Hand-off from the Product Comparison tool: prefill the company and carry
    // the focus product into the brief.
    var focusProduct = '', focusEdge = '';
    var handNote = el('div', 'display:none;background:#edf5ee;border:1px solid #bcd9c7;border-radius:8px;padding:8px 12px;margin:-6px 0 12px;font-size:13px;color:#14432f;');
    wrap.insertBefore(handNote, out);
    function applyHandoff(ev){
      var h = (ev && ev.detail) || null;
      if (!h){ try { h = JSON.parse(localStorage.getItem('mshPrepHandoff') || 'null'); } catch(e){} }
      if (!h || !h.company || (Date.now() - (h.ts || 0)) > 600000) return;
      var opts = [].slice.call(selCo.sel.options).map(function(o){ return o.value; });
      if (opts.indexOf(h.company) !== -1) selCo.sel.value = h.company;
      focusProduct = h.product || '';
      focusEdge = h.edge || '';
      // Reflect the carried-over product in the picker so the two never disagree.
      fillProducts();
      if (focusProduct){
        var pOpts = [].slice.call(selPr.sel.options).map(function(o){ return o.value; });
        if (pOpts.indexOf(focusProduct) !== -1) selPr.sel.value = focusProduct;
        early.checked = false;
      }
      handNote.style.display = 'block';
      handNote.innerHTML = 'Carried over from Product Comparison: <strong>' + esc(focusProduct) + '</strong> (' + esc(h.company) + ') — pick the trust and who you&rsquo;re meeting, then <strong>Prepare me</strong>.';
    }
    window.addEventListener('msh-prep-handoff', applyHandoff);
    applyHandoff();

    function printPack(){
      var cmp = document.getElementById('msh-compare-out');
      var pk = window.open('', '_blank');
      if (!pk){ alert('Allow pop-ups to print the pack.'); return; }
      var today = new Date().toLocaleDateString('en-GB');
      pk.document.write('<!doctype html><html><head><title>Meeting pack — NHS Intelligence Hub</title><style>'
        + 'body{font-family:Georgia,"Times New Roman",serif;color:#111;margin:24px;line-height:1.5;}'
        + 'h1{font-size:20px;margin:0 0 2px;} .sub{color:#555;font-size:12px;margin-bottom:18px;}'
        + 'img{max-width:70px;height:auto;} table{border-collapse:collapse;} td,th{border-bottom:1px solid #ccc;padding:4px 8px;font-size:11px;text-align:left;}'
        + 'a{color:#111;text-decoration:none;} button,input,select,datalist{display:none!important;}'
        + '.pagebreak{page-break-before:always;} div{max-width:100%;}'
        + '@media print{ a[href]:after{content:"";} }'
        + '</style></head><body>'
        + '<h1>Meeting pack — NHS Intelligence Hub</h1>'
        + '<div class="sub">Prepared ' + today + ' · Product information from the suppliers\u2019 own websites and the NHS Supply Chain catalogue · Verify framework/status at source before quoting.</div>'
        + (cmp && cmp.innerHTML ? '<h2 style="font-size:15px;">Product comparison &amp; the case for switching</h2>' + cmp.innerHTML + '<div class="pagebreak"></div>' : '')
        + '<h2 style="font-size:15px;">Meeting brief</h2>' + out.innerHTML
        + '</body></html>');
      pk.document.close();
      setTimeout(function(){ pk.print(); }, 600);
    }
    btn.addEventListener('click', function(){
      // An explicitly chosen product wins over a stale Product Comparison hand-off.
      if (selPr.sel.value){ focusProduct = selPr.sel.value; focusEdge = ''; }
      var co = suppliers.filter(function(s){ return s.name === selCo.sel.value; })[0];
      var tr = (cfg.trusts || []).filter(function(t){ return t.name === selTr.sel.value; })[0];
      out.innerHTML = brief(co, selCo.sel.value, selSp.sel.value, tr, selTr.sel.value, selAud.sel.value, early.checked, suppliers, cfg);
      if (out.textContent && out.textContent.indexOf('Pick your company') === -1){
        var pb = el('button', 'background:#20303f !important;color:#ffffff !important;border:0;border-radius:8px;padding:10px 18px;font-weight:800;font-size:13.5px;cursor:pointer;margin:0 0 12px;box-shadow:0 1px 3px rgba(0,0,0,.15);', 'Print / download the full meeting pack');
        pb.addEventListener('click', printPack);
        out.insertBefore(pb, out.firstChild);
      }
      out.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    function panel(title, bodyHtml, accent){
      return '<div style="background:' + PANEL + ';border:1px solid ' + LINE + ';border-left:3px solid ' + (accent||GOLD) + ';border-radius:10px;padding:14px 16px;margin:10px 0;">'
        + '<div style="font-size:15px;font-weight:800;color:' + INK + ';margin-bottom:6px;">' + title + '</div>'
        + '<div style="font-size:14px;line-height:1.65;color:#39424d;">' + bodyHtml + '</div></div>';
    }
    function li(items){ return '<ul style="margin:4px 0 0;padding-left:18px;">' + items.map(function(i){ return '<li style="margin:3px 0;">' + i + '</li>'; }).join('') + '</ul>'; }
    function link(text, id){ return '<a href="https://elevateandthrive.uk/?page_id=' + id + '" style="color:' + GOLD + ';font-weight:600;">' + text + '</a>'; }
    // One-click LinkedIn lookups: the tool builds the exact people-search and
    // recent-posts search and opens them in the rep's own logged-in LinkedIn.
    // (LinkedIn blocks server-side scraping, so deep links are the robust route.)
    function trustShort(name){ return String(name || '').replace(/ NHS Foundation Trust| NHS Trust/gi, '').trim(); }
    function roleCore(role){ return String(role || '').split('/')[0].split('(')[0].trim(); }
    function liBtn(text, url){ return '<a href="' + url + '" target="_blank" rel="noopener" style="display:inline-block;background:#0a66c2;color:#fff;border-radius:99px;padding:3px 12px;font-size:11.5px;font-weight:700;text-decoration:none;margin:3px 6px 0 0;">' + text + ' &#8599;</a>'; }
    function liPeopleUrl(role, trust){ return 'https://www.linkedin.com/search/results/people/?keywords=' + encodeURIComponent('"' + trustShort(trust) + '" ' + roleCore(role)); }
    function liPostsUrl(role, trust){ return 'https://www.linkedin.com/search/results/content/?keywords=' + encodeURIComponent('"' + trustShort(trust) + '" ' + roleCore(role)) + '&sortBy=%22date_posted%22'; }

    function competitors(co, sp, all){
      var specs = sp ? [sp] : ((co && co.specialities) || []);
      if (!specs.length) return [];
      var seen = {}; var out = [];
      all.forEach(function(s){
        if (!co || s.name === co.name) return;
        var share = sharesSpeciality(specs, s);
        if (share && !seen[s.name]){ seen[s.name] = 1; out.push(s); }
      });
      out.sort(function(a,b){ return (a.curated?0:1) - (b.curated?0:1); });
      return out.slice(0, 8);
    }

    function brief(co, coName, sp, tr, trName, aud, isEarly, all, cfg){
      if (!coName){ return '<div style="color:#8a6d00;font-size:14px;padding:8px 0;">Pick your company to start (add speciality, trust and who you’re meeting for a sharper brief).</div>'; }
      var head = esc(coName) + (sp ? ' · ' + esc(sp) : '') + (trName ? ' · ' + esc(trName) : '') + (aud ? ' · ' + esc(aud) : '') + (isEarly ? ' · early-stage' : '');
      var h = '<div style="font-size:13px;color:#6b7684;margin:6px 0 2px;">Prep brief — ' + head + '</div>';
      var v = co && co.voice;
      if (v){ h += panel('How you sell', '<strong>Your angle: ' + esc(v.angle) + '.</strong> ' + esc(v.line)); }

      // Audience-tailored angle
      if (aud && AUD[aud]){ h += panel('The angle for ' + esc(aud), AUD[aud].line, '#6b7684'); }

      if (focusProduct){
        h += panel('Your focus product today', '<strong>' + esc(focusProduct) + '</strong>' + (focusEdge ? ' — <strong>your edge: ' + esc(focusEdge) + '</strong>. Lead with the edge; the like-for-like comparison (one scroll up) makes the switch low-risk.' : ' — the full like-for-like comparison, live NHS Supply Chain codes and the case for switching are one scroll up in the Product Comparison.'), '#2E6B3E');
      }

      // Competitors & how you stack up
      if (!isEarly){
        var comp = competitors(co, sp, all);
        if (comp.length){
          var rows = comp.map(function(s){ var pr = (s.products || []).slice(0,3).map(esc).join(', '); return '<strong>' + esc(s.name) + '</strong>' + (pr ? ' — ' + pr : ''); });
          h += panel('Your competitors' + (sp ? ' in ' + esc(sp) : '') + ' — and how you stack up',
            li(rows)
            + '<div style="margin-top:8px;">Compare product-for-product on the ' + link('Compare tab', 1109) + ', and open any rival’s full profile in the ' + link('supplier directory', 677) + '.'
            + ' Then make your case where you win: ' + (v ? esc(v.angle) : 'your strengths') + ' — backed by the value figure below, not a feature list.</div>', '#6B2A34');
        }
      }

      var vbp = 'Build the numbers in the <strong>Value Case Calculator</strong> (cost of the problem × frequency × efficacy × directness) and hand over a figure they can take to finance. ' + link('Open the Tools', 1109) + '.';
      h += panel('The value case', (aud && AUD[aud] && AUD[aud].key === 'green' ? 'Frame value as patient, planet and public purse. ' : (v && /price/.test(v.angle) ? 'Lead with the saving, then the value story. ' : 'Lead with value, not price — the national procurement standard. ')) + vbp);

      if (!isEarly && co && co.frameworks && co.frameworks.length){
        var fr = co.frameworks.map(function(f){ return '<strong>' + esc(f.name) + '</strong>' + (f.value ? ' — ' + esc(f.value) : '') + (f.dates ? ' <span style="color:#6b7684;">(' + esc(f.dates) + ')</span>' : '') + (f.note ? '<br><span style="color:#6b7684;">' + esc(f.note) + '</span>' : ''); });
        h += panel('Frameworks & timing', li(fr) + '<div style="margin-top:8px;">A framework’s final year is the selling window — see the ' + link('Framework Hub', 678) + '.</div>');
      }

      var nat = (cfg.nationalKeyInfo || []).map(function(n){ return '<strong>' + esc(n.title) + '</strong> — ' + esc(n.detail) + '<br><span style="color:' + GOLD + ';">Use it:</span> ' + esc(n.use); });
      if (nat.length){ h += panel('What’s changed nationally (use these)', li(nat)); }

      if (!isEarly && co && co.alerts && co.alerts.length){
        var al = co.alerts.slice(0,4).map(function(a){ return (a.date ? '<span style="color:#6b7684;">' + esc(a.date) + '</span> — ' : '') + esc(a.title || a.p || ''); });
        h += panel('Your live alerts & recalls', li(al) + '<div style="margin-top:8px;">Know your own position — and watch the ' + link('Live Desk', 675) + ' for competitors’.</div>');
      }

      if (tr){
        var body = esc(tr.context)
          + (tr.news ? '<br><span style="color:#6b7684;">Recent: ' + esc(tr.news) + '</span>' : '');
        // From their own annual report — real figures, real source, no homework.
        if (tr.reportFacts && tr.reportFacts.length){
          var rf = tr.reportFacts.map(function(f){
            return esc(f.fact) + (f.figure ? ' — <strong>' + esc(f.figure) + '</strong>' : '')
              + (f.source ? ' <a href="' + esc(f.source) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-size:11.5px;font-weight:600;">' + esc(f.where || 'source') + ' &#8599;</a>' : '');
          });
          body += '<div style="margin-top:10px;font-weight:700;">From their own annual report &amp; board papers:</div>' + li(rf);
        }
        // Named people — verified from public sources.
        if (tr.people && tr.people.length){
          var pl = tr.people.map(function(p){
            var b = '<strong>' + esc(p.name) + '</strong> — ' + esc(p.role) + (p.note ? '. <span style="color:#6b7684;">' + esc(p.note) + '</span>' : '') + '<br>';
            if (p.linkedin) b += liBtn('LinkedIn profile', p.linkedin);
            else b += liBtn('Find them on LinkedIn', 'https://www.linkedin.com/search/results/people/?keywords=' + encodeURIComponent('"' + p.name + '" ' + trustShort(tr.name)));
            b += liBtn('Their recent posts', 'https://www.linkedin.com/search/results/content/?keywords=' + encodeURIComponent('"' + p.name + '"') + '&sortBy=%22date_posted%22');
            if (p.source) b += ' <a href="' + esc(p.source) + '" target="_blank" rel="noopener" style="font-size:11.5px;color:#8a8778;">verified source &#8599;</a>';
            return b;
          });
          body += '<div style="margin-top:10px;font-weight:700;">Publicly listed contacts to be aware of:</div>' + li(pl);
        }
        // Role-level fallbacks with one-click lookups.
        var ctc = (tr.contacts || []).map(function(c){
          return '<strong>' + esc(c.role) + '</strong> — ' + esc(c.note)
            + '<br>' + liBtn('Find them on LinkedIn', liPeopleUrl(c.role, tr.name))
            + liBtn('Their recent posts', liPostsUrl(c.role, tr.name));
        });
        if (ctc.length && !(tr.people && tr.people.length)){
          body += '<div style="margin-top:8px;font-weight:700;">Who you’re meeting — looked up for you (opens in your LinkedIn):</div>' + li(ctc);
        }
        // How their procurement actually works (booking systems, team structure).
        if (tr.structure){
          body += '<div style="margin-top:10px;font-weight:700;">How their procurement works:</div><div style="font-size:13px;line-height:1.6;color:#39424d;">' + esc(tr.structure) + '</div>';
        }
        // What voices at/around the trust are saying publicly.
        if (tr.voices && tr.voices.length){
          var vl = tr.voices.map(function(v){
            return '<strong>' + esc(v.who) + '</strong>' + (v.role ? ' (' + esc(v.role) + ')' : '') + (v.date ? ' <span style="color:#8a8778;font-size:11.5px;">' + esc(v.date) + '</span>' : '') + ' — ' + esc(v.what)
              + (v.source ? ' <a href="' + esc(v.source) + '" target="_blank" rel="noopener" style="color:' + GOLD + ';font-size:11.5px;font-weight:600;">source &#8599;</a>' : '');
          });
          body += '<div style="margin-top:10px;font-weight:700;">What they’re saying publicly:</div>' + li(vl);
        }
        h += panel('The trust: ' + esc(tr.name), body);
      } else if (trName && trName !== 'Other / any trust'){
        var de = DIRMAP[trName] || {};
        var meta = [];
        if (de.town) meta.push('HQ: ' + esc(de.town) + (de.postcode ? ' (' + esc(de.postcode) + ')' : ''));
        if (de.code) meta.push('ODS code: ' + esc(de.code));
        h += panel('The trust: ' + esc(trName),
          (meta.length ? '<span style="color:#6b7684;font-size:12.5px;">' + meta.join(' · ') + ' — NHS ODS register</span><br>' : '')
          + 'No deep Hub profile yet for this trust — you still get the essentials: pull its latest annual report for strategy and cost pressures, and go straight to the right people:'
          + '<br>' + liBtn('Procurement lead on LinkedIn', liPeopleUrl('Head of Procurement', trName))
          + liBtn('Clinical leads on LinkedIn', liPeopleUrl('Clinical lead', trName))
          + ' <a href="https://www.google.com/search?q=' + encodeURIComponent('"' + trName + '" annual report') + '" target="_blank" rel="noopener" style="display:inline-block;background:#fff;border:1px solid ' + LINE + ';border-radius:99px;padding:3px 12px;font-size:11.5px;font-weight:700;color:#6B2A34;text-decoration:none;margin:3px 6px 0 0;">Find their annual report &#8599;</a>');
      } else if (trName){
        h += panel('The trust', 'No seeded profile yet — pull the trust’s latest annual report and news for its strategy and cost pressures, identify the procurement lead and a clinical champion, and read their recent public LinkedIn posts before you go in.');
      }

      var howItems = [
        'Open in your company’s voice (' + (v ? esc(v.angle) : 'your strengths') + '), pitched at ' + (aud ? esc(aud) : 'the person in the room') + '.',
        'Lead the case with the Value Calculator figure, framed as value-based procurement.',
        (tr ? 'Tie it to the trust’s stated strategy and their real pressures.' : 'Ground it in the trust’s own report and news.'),
        'Know your competitors and where you win before you walk in.',
        'Use “how are you finding the new NHS Supply Chain catalogue?” as a natural opener.'
      ];
      h += panel('How to use this in the meeting', li(howItems));
      h += '<div style="background:#fdfbf6;border:1px solid #e0c98a;border-radius:10px;padding:16px 18px;margin:14px 0 6px;text-align:center;">'
        + '<div style="font-size:14.5px;line-height:1.65;color:#39424d;"><em>The Hub has done the homework — this is your intel. Your skill as a salesperson is what turns it into a sale: people buy from people, and the relationship matters. Walk in as a partner in their care, not a supplier at the door.</em></div>'
        + '<div style="font-size:13px;color:' + GOLD + ';font-weight:700;margin-top:8px;">&ldquo;Trust is the glue of life.&rdquo; &mdash; Stephen R. Covey</div>'
        + '</div>';
      h += '<div style="font-size:12px;color:#8a8778;margin-top:6px;">Assembled from the live Hub — supplier directory, frameworks, Live Desk and Tools. Verify framework/award status at source before quoting.</div>';
      return h;
    }
  }
})();
