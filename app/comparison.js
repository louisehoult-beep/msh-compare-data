/* NHS Intelligence Hub — Product Comparison tool.
   Head-to-head of one supplier's product vs a competitor's, in clearly-sourced
   layers: NHS Supply Chain (confirmed) -> supplier website (labelled) ->
   published evidence/notes -> then "how you could use this" guidance keyed to
   what matters (price / value & capacity / clinical / sustainability).
   Separate from the Meeting Prep tool. Reads the live index + seed + config. */
(function () {
  var MOUNT = document.getElementById('msh-compare-tool');
  if (!MOUNT) return;
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var GOLD = '#a8842c', OX = '#6B2A34', INK = '#20303f', LINE = '#e6e2d8', PANEL = '#ffffff', SOFT = '#f7f5ef';
  var IDX = BASE + 'data/supplier-index.json?cb=' + Date.now();
  var CFG = BASE + 'data/prep-config.json?cb=' + Date.now();
  var SEED = BASE + 'data/supplier-seed.json?cb=' + Date.now();

  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function el(tag, css, html){ var e = document.createElement(tag); if (css) e.style.cssText = css; if (html != null) e.innerHTML = html; return e; }

  var ANGLE = {
    'Price / cost': 'Compare the framework prices (NHS Supply Chain, confirmed) and the whole-life cost. Then link it to the trust’s own savings target — read their latest annual report / board papers — and build the number in the Value Case Calculator so procurement can take it to finance.',
    'Value & capacity': 'Frame it as value-based procurement (the national standard — save AND deliver value). Quantify the capacity or outcome gain (fewer complications, less theatre/nursing time, shorter stay) in the Value Case Calculator, not as a features list.',
    'Clinical evidence': 'Put the published evidence side by side — NICE guidance, trials, real-world data — and cite it. Where your product has evidence the competitor doesn’t, lead with it; offer a trial or in-service.',
    'Sustainability': 'Compare carbon and reusable-vs-single-use whole-life impact, packaging and energy. Bring your Carbon Reduction Plan (Evergreen is scored at tender from Apr 2026) and frame value as patient, planet and public purse.'
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
    suppliers.forEach(function(s){ var sd = seedMap[s.name]; if (sd){ ['voice','products','frameworks','specialities','evidence'].forEach(function(k){ if (sd[k] && (!Array.isArray(sd[k]) || sd[k].length)) s[k] = sd[k]; }); } });
    var have = {}; suppliers.forEach(function(s){ have[s.name] = 1; });
    ((seed && seed.suppliers) || []).forEach(function(s){ if (!have[s.name]){ s.curated = true; suppliers.push(s); } });
    suppliers.sort(function(a,b){ return (a.name||'').toLowerCase() < (b.name||'').toLowerCase() ? -1 : 1; });

    var wrap = el('div', 'font-family:Inter,system-ui,sans-serif;color:' + INK + ';');
    wrap.appendChild(el('div', 'text-transform:uppercase;letter-spacing:2px;font-size:11px;font-weight:700;color:' + OX + ';', 'NHS Intelligence Hub'));
    wrap.appendChild(el('div', 'font-size:24px;font-weight:800;margin:2px 0 4px;', 'Product Comparison'));
    wrap.appendChild(el('div', 'font-size:14px;line-height:1.6;color:#4a5766;max-width:680px;margin-bottom:12px;', 'Compare your product against a competitor, in layers you can trust: <strong>NHS Supply Chain (confirmed)</strong>, then the <strong>supplier’s own website</strong>, then <strong>published evidence</strong> — and how to use each point in the room.'));

    var bar = el('div', 'display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:12px;margin-bottom:14px;');
    var names = suppliers.map(function(s){ return s.name; });
    var selA = mkSelect('Your supplier', [''].concat(names));
    var selPA = mkText('Your product (optional)');
    var selB = mkSelect('Compare against', [''].concat(names));
    var selPB = mkText('Their product (optional)');
    var selAng = mkSelect('What matters most', ['', 'Price / cost', 'Value & capacity', 'Clinical evidence', 'Sustainability']);
    var btn = el('button', 'background:' + OX + ';color:#fff;border:0;border-radius:8px;padding:10px 18px;font-weight:700;font-size:14px;cursor:pointer;', 'Compare');
    [selA.box, selPA.box, selB.box, selPB.box, selAng.box].forEach(function(b){ bar.appendChild(b); });
    bar.appendChild(btn);
    wrap.appendChild(bar);

    function mkSelect(label, opts){
      var box = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:170px;flex:1;');
      box.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', esc(label)));
      var sel = el('select', 'padding:9px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;background:#fff;color:' + INK + ';');
      opts.forEach(function(o){ var op = el('option'); op.value = o; op.textContent = o || '— choose —'; sel.appendChild(op); });
      box.appendChild(sel); return { box: box, sel: sel };
    }
    function mkText(label){
      var box = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:150px;flex:1;');
      box.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', esc(label)));
      var inp = el('input', 'padding:9px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;'); inp.type='text';
      box.appendChild(inp); return { box: box, sel: inp };
    }

    var out = el('div', 'margin-top:6px;'); wrap.appendChild(out);
    MOUNT.innerHTML = ''; MOUNT.appendChild(wrap);

    btn.addEventListener('click', function(){
      var a = suppliers.filter(function(s){ return s.name === selA.sel.value; })[0];
      var b = suppliers.filter(function(s){ return s.name === selB.sel.value; })[0];
      out.innerHTML = compare(a, selPA.sel.value, b, selPB.sel.value, selAng.sel.value);
      out.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    function link(text, id){ return '<a href="https://elevateandthrive.uk/?page_id=' + id + '" style="color:' + GOLD + ';font-weight:600;">' + text + '</a>'; }
    function layer(title, colour, body){ return '<div style="margin:8px 0;"><div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:' + colour + ';margin-bottom:3px;">' + title + '</div><div style="font-size:13.5px;line-height:1.6;color:#39424d;">' + body + '</div></div>'; }
    function ul(items){ return items.length ? '<ul style="margin:2px 0 0;padding-left:16px;">' + items.map(function(i){ return '<li style="margin:2px 0;">' + i + '</li>'; }).join('') + '</ul>' : '<span style="color:#8a8778;">—</span>'; }

    function col(s, product){
      if (!s) return '<div style="flex:1;min-width:240px;color:#8a6d00;">Pick a supplier.</div>';
      var fw = (s.frameworks || []).map(function(f){ return '<strong>' + esc(f.name) + '</strong>' + (f.note ? ' <span style="color:#6b7684;">(' + esc(f.note) + ')</span>' : ''); });
      var pr = (s.products || []).map(esc);
      var ev = (s.evidence || []).map(function(e){ return esc(e.text || e) + (e.source ? ' — <a href="' + esc(e.source) + '" style="color:' + GOLD + ';">source</a>' : ''); });
      var pub = [];
      (s.alerts || []).slice(0,3).forEach(function(a){ pub.push('<span style="color:#b00020;">Alert:</span> ' + esc(a.title || a.p || '')); });
      (s.news || []).slice(0,3).forEach(function(n){ pub.push(esc(n.title || n.t || '') + (n.url ? ' — <a href="' + esc(n.url) + '" style="color:' + GOLD + ';">link</a>' : '')); });
      var h = '<div style="flex:1;min-width:260px;background:' + PANEL + ';border:1px solid ' + LINE + ';border-radius:10px;padding:14px 16px;">';
      h += '<div style="font-size:16px;font-weight:800;">' + esc(s.name) + '</div>';
      if (product) h += '<div style="font-size:13px;color:#6b7684;margin-bottom:4px;">Product: ' + esc(product) + '</div>';
      if (s.voice) h += '<div style="font-size:12.5px;color:' + OX + ';margin:2px 0 6px;">Sells on: ' + esc(s.voice.angle) + '</div>';
      h += layer('NHS Supply Chain — confirmed', OX, ul(fw));
      h += layer('From the supplier’s website', GOLD, ul(pr.length ? pr.slice(0,12) : []));
      h += layer('Published evidence / notes', '#2E6B3E', ev.length ? ul(ev) : (pub.length ? ul(pub) : '<span style="color:#8a8778;">None indexed — check NICE guidance / published trials for this product.</span>'));
      h += '</div>';
      return h;
    }

    function compare(a, pa, b, pb, angle){
      if (!a || !b){ return '<div style="color:#8a6d00;font-size:14px;padding:8px 0;">Pick your supplier and a competitor to compare.</div>'; }
      var h = '<div style="font-size:13px;color:#6b7684;margin:6px 0 4px;">' + esc(a.name) + (pa ? ' (' + esc(pa) + ')' : '') + '  vs  ' + esc(b.name) + (pb ? ' (' + esc(pb) + ')' : '') + '</div>';
      h += '<div style="display:flex;gap:12px;flex-wrap:wrap;">' + col(a, pa) + col(b, pb) + '</div>';
      var use = angle && ANGLE[angle] ? ANGLE[angle] : 'Pick “what matters most” above and this becomes specific — e.g. on price it links to the trust’s savings targets; on value it frames value-based procurement.';
      h += '<div style="background:#fff;border:1px solid ' + LINE + ';border-left:3px solid ' + GOLD + ';border-radius:10px;padding:14px 16px;margin:12px 0;">'
        + '<div style="font-size:15px;font-weight:800;">How you could use this' + (angle ? ' — ' + esc(angle) : '') + '</div>'
        + '<div style="font-size:14px;line-height:1.65;color:#39424d;margin-top:4px;">' + use + ' ' + link('Open the Value Case Calculator', 1109) + '.</div></div>';
      h += '<div style="font-size:12px;color:#8a8778;">Source layers are labelled: NHS Supply Chain framework membership is top-level (verify the lot at source); product lists are the supplier’s own website; “published evidence” is cited where indexed. Nothing is invented.</div>';
      return h;
    }
  }
})();
