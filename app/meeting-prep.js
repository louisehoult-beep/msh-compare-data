/* NHS Intelligence Hub — Meeting Prep tool ("Help me prepare")
   Reads the live supplier index + prep-config and assembles a tailored,
   brand-voice-aware pre-meeting brief. Served from GitHub, loaded by page 677.
   Self-contained; degrades gracefully. */
(function () {
  var MOUNT = document.getElementById('msh-meeting-prep');
  if (!MOUNT) return;
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var GOLD = '#a8842c', INK = '#20303f', LINE = '#e6e2d8', PANEL = '#ffffff', SOFT = '#f7f5ef';
  var IDX = BASE + 'data/supplier-index.json?cb=' + Date.now();
  var CFG = BASE + 'data/prep-config.json?cb=' + Date.now();
  var SEED = BASE + 'data/supplier-seed.json?cb=' + Date.now();

  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function el(tag, css, html){ var e = document.createElement(tag); if (css) e.style.cssText = css; if (html != null) e.innerHTML = html; return e; }

  MOUNT.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:' + INK + ';padding:6px 0;">Loading meeting prep…</div>';

  Promise.all([
    fetch(IDX).then(function(r){return r.json();}),
    fetch(CFG).then(function(r){return r.json();}),
    fetch(SEED).then(function(r){return r.json();}).catch(function(){return {suppliers:[]};})
  ])
    .then(function(res){ render(res[0], res[1], res[2]); })
    .catch(function(){ MOUNT.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:#8a6d00;">Meeting prep is temporarily unavailable — please try again shortly.</div>'; });

  function render(index, cfg, seed){
    var suppliers = (index && index.suppliers) || [];
    // Overlay the authoritative curated seed (voice/products/frameworks) so brand voice
    // is available immediately, independent of the index refresh cadence.
    var seedMap = {};
    ((seed && seed.suppliers) || []).forEach(function(s){ seedMap[s.name] = s; });
    suppliers.forEach(function(s){
      var sd = seedMap[s.name];
      if (sd){
        if (sd.voice) s.voice = sd.voice;
        if (sd.products && sd.products.length) s.products = sd.products;
        if (sd.frameworks && sd.frameworks.length) s.frameworks = sd.frameworks;
      }
    });
    var curated = suppliers.filter(function(s){ return s.curated; });
    var rest = suppliers.filter(function(s){ return !s.curated; });
    curated.sort(byName); rest.sort(byName);
    function byName(a,b){ return (a.name||'').toLowerCase() < (b.name||'').toLowerCase() ? -1 : 1; }

    var wrap = el('div', 'font-family:Inter,system-ui,sans-serif;color:' + INK + ';');

    // header
    wrap.appendChild(el('div', 'text-transform:uppercase;letter-spacing:2px;font-size:11px;font-weight:700;color:' + GOLD + ';', 'NHS Intelligence Hub'));
    wrap.appendChild(el('div', 'font-size:24px;font-weight:800;margin:2px 0 4px;', 'Help me prepare'));
    wrap.appendChild(el('div', 'font-size:14px;line-height:1.6;color:#4a5766;max-width:640px;margin-bottom:12px;', 'Pick who you are, the speciality and the trust — and get a pre-meeting brief pulled from everything the Hub holds, in the way <em>your</em> company sells. Tick “early-stage” if you are not talking about a specific product yet.'));

    // controls
    var bar = el('div', 'display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;background:' + SOFT + ';border:1px solid ' + LINE + ';border-radius:10px;padding:12px;margin-bottom:14px;');
    var selCo = mkSelect('Your company', [''].concat(curated.map(nm)).concat(rest.length ? ['— other suppliers —'] : []).concat(rest.map(nm)));
    var selSp = mkSelect('Speciality', [''].concat(cfg.specialities || []));
    var selTr = mkSelect('Hospital / trust', [''].concat((cfg.trusts || []).map(function(t){return t.name;})).concat(['Other / any trust']));
    var earlyWrap = el('label', 'font-size:13px;color:#4a5766;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;');
    var early = el('input'); early.type = 'checkbox';
    earlyWrap.appendChild(early); earlyWrap.appendChild(document.createTextNode('Early-stage (no product yet)'));
    var btn = el('button', 'background:' + INK + ';color:#fff;border:0;border-radius:8px;padding:10px 18px;font-weight:700;font-size:14px;cursor:pointer;', 'Prepare me');

    [selCo.box, selSp.box, selTr.box].forEach(function(b){ bar.appendChild(b); });
    var side = el('div', 'display:flex;flex-direction:column;gap:8px;');
    side.appendChild(earlyWrap); side.appendChild(btn); bar.appendChild(side);
    wrap.appendChild(bar);

    function nm(s){ return s.name; }
    function mkSelect(label, opts){
      var box = el('div', 'display:flex;flex-direction:column;gap:4px;min-width:190px;flex:1;');
      box.appendChild(el('label', 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7684;', esc(label)));
      var sel = el('select', 'padding:9px 10px;border:1px solid ' + LINE + ';border-radius:8px;font-size:14px;background:#fff;color:' + INK + ';');
      opts.forEach(function(o){ var op = el('option'); op.value = (o.indexOf('—') === 0 ? '' : o); op.textContent = o || '— choose —'; if (o.indexOf('—') === 0) op.disabled = true; sel.appendChild(op); });
      box.appendChild(sel);
      return { box: box, sel: sel };
    }

    var out = el('div', 'margin-top:6px;');
    wrap.appendChild(out);
    MOUNT.innerHTML = ''; MOUNT.appendChild(wrap);

    btn.addEventListener('click', function(){
      var coName = selCo.sel.value, sp = selSp.sel.value, trName = selTr.sel.value, isEarly = early.checked;
      var co = suppliers.filter(function(s){ return s.name === coName; })[0];
      var tr = (cfg.trusts || []).filter(function(t){ return t.name === trName; })[0];
      out.innerHTML = brief(co, coName, sp, tr, trName, isEarly, suppliers, cfg);
      out.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    function panel(title, bodyHtml){
      return '<div style="background:' + PANEL + ';border:1px solid ' + LINE + ';border-left:3px solid ' + GOLD + ';border-radius:10px;padding:14px 16px;margin:10px 0;">'
        + '<div style="font-size:15px;font-weight:800;color:' + INK + ';margin-bottom:6px;">' + title + '</div>'
        + '<div style="font-size:14px;line-height:1.65;color:#39424d;">' + bodyHtml + '</div></div>';
    }
    function li(items){ return '<ul style="margin:4px 0 0;padding-left:18px;">' + items.map(function(i){ return '<li style="margin:3px 0;">' + i + '</li>'; }).join('') + '</ul>'; }
    function link(text, id){ return '<a href="https://elevateandthrive.uk/?page_id=' + id + '" style="color:' + GOLD + ';font-weight:600;">' + text + '</a>'; }

    function brief(co, coName, sp, tr, trName, isEarly, all, cfg){
      if (!coName){ return '<div style="color:#8a6d00;font-size:14px;padding:8px 0;">Pick your company to start (add a speciality and trust for a sharper brief).</div>'; }
      var head = esc(coName) + (sp ? ' · ' + esc(sp) : '') + (trName ? ' · ' + esc(trName) : '') + (isEarly ? ' · early-stage' : '');
      var h = '<div style="font-size:13px;color:#6b7684;margin:6px 0 2px;">Prep brief — ' + head + '</div>';

      // 1. How you sell (brand voice)
      var v = co && co.voice;
      if (v){ h += panel('How you sell', '<strong>Your angle: ' + esc(v.angle) + '.</strong> ' + esc(v.line)); }

      // 2. Your products (skip in early-stage)
      if (!isEarly && co && co.products && co.products.length){
        h += panel('Your products to talk to', li(co.products.map(esc)) + '<div style="margin-top:8px;">Compare them against the field on the ' + link('product Compare tab', 1109) + ', and see full rival profiles in the ' + link('supplier directory', 677) + '.</div>');
      }

      // 3. The value case (VBP)
      var vbpUse = 'Build the numbers in the <strong>Value Case Calculator</strong> (cost of the problem × frequency × efficacy × directness) and hand procurement a figure they can take to finance. ' + link('Open the Tools', 1109) + '.';
      h += panel('The value case', (v && /price/.test(v.angle) ? 'Lead with the cost saving, then back it with the value story. ' : 'Lead with value, not price — it is now the national procurement standard. ') + vbpUse);

      // 4. Frameworks & timing
      if (!isEarly && co && co.frameworks && co.frameworks.length){
        var fr = co.frameworks.map(function(f){ return '<strong>' + esc(f.name) + '</strong>' + (f.value ? ' — ' + esc(f.value) : '') + (f.dates ? ' <span style="color:#6b7684;">(' + esc(f.dates) + ')</span>' : '') + (f.note ? '<br><span style="color:#6b7684;">' + esc(f.note) + '</span>' : ''); });
        h += panel('Frameworks & timing', li(fr) + '<div style="margin-top:8px;">A framework’s final year is the selling window — see the ' + link('Framework Hub', 678) + '.</div>');
      }

      // 5. Recent national developments that matter
      var nat = (cfg.nationalKeyInfo || []).map(function(n){ return '<strong>' + esc(n.title) + '</strong> — ' + esc(n.detail) + '<br><span style="color:' + GOLD + ';">Use it:</span> ' + esc(n.use); });
      if (nat.length){ h += panel('What’s changed nationally (use these)', li(nat)); }

      // 6. Own-product alerts
      if (!isEarly && co && co.alerts && co.alerts.length){
        var al = co.alerts.slice(0,4).map(function(a){ return (a.date ? '<span style="color:#6b7684;">' + esc(a.date) + '</span> — ' : '') + esc(a.title || a.p || ''); });
        h += panel('Your live alerts & recalls', li(al) + '<div style="margin-top:8px;">Know your own position before you walk in — and watch the ' + link('Live Desk', 675) + ' for competitors’.</div>');
      }

      // 7. The trust
      if (tr){
        var ctc = (tr.contacts || []).map(function(c){ return '<strong>' + esc(c.role) + '</strong> — ' + esc(c.note); });
        h += panel('The trust: ' + esc(tr.name), esc(tr.context) + (tr.news ? '<br><span style="color:#6b7684;">Recent: ' + esc(tr.news) + '</span>' : '') + (ctc.length ? '<div style="margin-top:8px;font-weight:700;">Who to look up first:</div>' + li(ctc) : ''));
      } else if (trName){
        h += panel('The trust', 'No seeded profile for this trust yet — pull its latest annual report and recent news, and identify the procurement lead and a clinical champion. Check their recent public LinkedIn posts before you go in. (I’m expanding the seeded trust profiles.)');
      }

      // 8. How to use this
      var howItems = [
        'Open on ' + (v && /price/.test(v.angle) ? 'the saving' : 'value and outcomes') + ', in your company’s voice — not a features list.',
        'Lead the business case with the Value Case Calculator figure, framed as value-based procurement.',
        (tr ? 'Reference the trust’s real situation so you sound like you already work there.' : 'Ground it in the trust’s own report and news.'),
        'Use “how are you finding the new NHS Supply Chain catalogue?” as a natural opener.'
      ];
      h += panel('How to use this in the meeting', li(howItems));

      h += '<div style="font-size:12px;color:#8a8778;margin-top:10px;">Assembled from the live Hub — supplier directory, frameworks, Live Desk and Tools. Verify framework/award status at source before quoting.</div>';
      return h;
    }
  }
})();
