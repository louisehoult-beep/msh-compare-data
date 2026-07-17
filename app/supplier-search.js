/* Medical Sales Hub — Supplier Intelligence Search
   Loaded by a tiny loader on WP page 677. Full code lives in
   github.com/louisehoult-beep/msh-compare-data/app/supplier-search.js
   Data: data/supplier-index.json (same repo). */
(function(){
  var DATA_URL='https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/supplier-index.json';
  var MOUNT=document.getElementById('msh-supplier-search');
  if(!MOUNT) return;
  var G='#a8842c', INK='#1d2733', DIM='#75808d', LINE='#e6e0d4', RED='#b84a5c', GREEN='#2e7d5b';
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function norm(s){return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();}

  function shell(){
    MOUNT.innerHTML=''+
    '<div style="font-family:Inter,-apple-system,Segoe UI,sans-serif;background:#fff;border:1px solid '+LINE+';border-top:3px solid '+G+';border-radius:12px;box-shadow:0 1px 3px rgba(29,39,51,.06);overflow:hidden;margin:0 0 8px;">'+
      '<div style="padding:16px 18px 6px;">'+
        '<div style="font-size:11.5px;letter-spacing:2px;font-weight:700;color:'+G+';">SUPPLIER INTELLIGENCE SEARCH</div>'+
        '<p style="margin:5px 0 12px;font-size:13.5px;color:'+DIM+';">Type a supplier or brand — get their frameworks, products, and live alerts/recalls, all in one place. <span id="mssCount"></span></p>'+
        '<input id="mssInput" list="mssList" autocomplete="off" placeholder="e.g. BD, Vygon, Coloplast, Nexiva…" '+
          'style="width:100%;max-width:520px;padding:11px 16px;border-radius:99px;border:1px solid '+LINE+';font:inherit;font-size:15px;color:'+INK+';outline:none;">'+
        '<datalist id="mssList"></datalist>'+
        '<div id="mssChips" style="margin:10px 0 2px;display:flex;flex-wrap:wrap;gap:6px;"></div>'+
      '</div>'+
      '<div id="mssResult" style="padding:2px 18px 18px;"></div>'+
    '</div>';
  }

  function card(s){
    function sec(title,html){return '<div style="margin:14px 0 0;"><div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;font-weight:700;color:'+DIM+';margin-bottom:6px;">'+title+'</div>'+html+'</div>';}
    var h='<div style="border:1px solid '+LINE+';border-radius:11px;padding:16px 18px;background:#fdfcf9;">';
    h+='<div style="font-size:20px;font-weight:700;color:'+INK+';">'+esc(s.name)+'</div>';
    if(s.note) h+='<p style="margin:4px 0 0;font-size:13.5px;color:#37485a;">'+esc(s.note)+'</p>';
    if(s.specialities&&s.specialities.length) h+='<div style="margin-top:8px;">'+s.specialities.map(function(x){return '<span style="display:inline-block;background:#f3ead2;color:#7a5b14;border-radius:99px;padding:3px 10px;font-size:11.5px;font-weight:600;margin-right:6px;">'+esc(x)+'</span>';}).join('')+'</div>';

    // frameworks
    if(s.frameworks&&s.frameworks.length){
      h+=sec('Frameworks on', s.frameworks.map(function(f){
        return '<div style="padding:7px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;"><b>'+esc(f.name)+'</b>'+
          (f.value?' <span style="color:'+GREEN+';font-weight:700;">'+esc(f.value)+'</span>':'')+
          (f.dates?' <span style="color:'+DIM+';">· '+esc(f.dates)+'</span>':'')+
          (f.note?'<br><span style="color:#37485a;font-size:12.5px;">'+esc(f.note)+'</span>':'')+'</div>';
      }).join(''));
    } else h+=sec('Frameworks on','<div style="font-size:13px;color:'+DIM+';">No framework indexed yet.</div>');

    // products
    if(s.products&&s.products.length){
      h+=sec('Products / brands', s.products.map(function(p){return '<span style="display:inline-block;border:1px solid '+LINE+';border-radius:99px;padding:4px 11px;font-size:12.5px;margin:0 5px 5px 0;color:#37485a;">'+esc(p)+'</span>';}).join(''));
    }

    // alerts
    if(s.alerts&&s.alerts.length){
      h+=sec('Alerts &amp; recalls', s.alerts.map(function(a){
        return '<div style="padding:9px 11px;margin:0 0 7px;border-left:3px solid '+RED+';background:#fff;border-radius:7px;font-size:13px;">'+
          '<b style="color:'+RED+';">'+esc(a.date)+'</b> — <b>'+esc(a.title)+'</b>'+
          '<br><span style="color:#37485a;">'+esc(a.detail)+'</span>'+
          (a.use?'<br><span style="color:'+G+';">▸ '+esc(a.use)+'</span>':'')+
          (a.url?' <a href="'+esc(a.url)+'" target="_blank" rel="noopener" style="color:'+G+';font-weight:600;">source ↗</a>':'')+'</div>';
      }).join(''));
    } else h+=sec('Alerts &amp; recalls','<div style="font-size:13px;color:'+GREEN+';">No current alert indexed.</div>');

    // links
    if(s.links&&s.links.length){
      h+=sec('Links', s.links.map(function(l){return '<a href="'+esc(l.url)+'" target="_blank" rel="noopener" style="color:'+G+';font-weight:600;font-size:13px;margin-right:14px;">'+esc(l.label)+' ↗</a>';}).join(''));
    }
    h+='<div style="margin-top:14px;padding-top:10px;border-top:1px solid '+LINE+';font-size:11px;color:'+DIM+';">Related Hub pages: '+
       '<a href="/medical-sales-hub/frameworks/" style="color:'+G+';">Frameworks</a> · '+
       '<a href="/medical-sales-hub/awards/" style="color:'+G+';">Award Tracker</a> · '+
       '<a href="/medical-sales-hub/" style="color:'+G+';">Live Desk (alerts)</a> · '+
       '<a href="/medical-sales-hub/news/" style="color:'+G+';">News</a></div>';
    h+='</div>';
    return h;
  }

  function run(data){
    var sup=data.suppliers||[];
    shell();
    var input=document.getElementById('mssInput'), list=document.getElementById('mssList'),
        result=document.getElementById('mssResult'), chips=document.getElementById('mssChips'),
        count=document.getElementById('mssCount');
    count.textContent=sup.length+' suppliers indexed · data as of '+(data.dataAsOf||'');
    list.innerHTML=sup.map(function(s){return '<option value="'+esc(s.name)+'">';}).join('');
    // quick chips
    var quick=['BD — Becton, Dickinson','Vygon (UK)','GBUK Group','Coloplast','Abbott Diabetes Care'];
    chips.innerHTML=quick.filter(function(q){return sup.some(function(s){return s.name===q;});})
      .map(function(q){return '<button data-q="'+esc(q)+'" style="cursor:pointer;background:#f7f4ee;border:1px solid '+LINE+';border-radius:99px;padding:5px 12px;font-size:12px;color:'+INK+';">'+esc(q.split(' — ')[0])+'</button>';}).join('');
    function find(q){
      var n=norm(q);
      if(!n) return null;
      var hit=sup.filter(function(s){return norm(s.name)===n||(s.aliases||[]).some(function(a){return norm(a)===n;});})[0];
      if(hit) return hit;
      // partial: name/alias/product contains
      return sup.filter(function(s){
        if(norm(s.name).indexOf(n)>-1) return true;
        if((s.aliases||[]).some(function(a){return norm(a).indexOf(n)>-1;})) return true;
        if((s.products||[]).some(function(p){return norm(p).indexOf(n)>-1;})) return true;
        return false;
      })[0]||null;
    }
    function show(q){
      var s=find(q);
      result.innerHTML = s ? card(s) :
        '<div style="padding:14px 4px;font-size:13.5px;color:'+DIM+';">No match for “'+esc(q)+'”. Coverage is the tracked-supplier set ('+sup.length+' indexed) — a supplier not here is <b>not yet indexed</b>, not “nothing found”.</div>';
    }
    input.addEventListener('change',function(){show(input.value);});
    input.addEventListener('keydown',function(e){if(e.key==='Enter')show(input.value);});
    chips.addEventListener('click',function(e){var b=e.target.closest('button');if(b){input.value=b.getAttribute('data-q');show(input.value);}});
  }

  if(window.MSH_SUPPLIER_INDEX){ run(window.MSH_SUPPLIER_INDEX); return; }
  fetch(DATA_URL,{cache:'no-store'}).then(function(r){return r.json();}).then(run).catch(function(){
    MOUNT.innerHTML='<div style="font-family:Inter,sans-serif;color:'+DIM+';font-size:13px;padding:12px;">Supplier search is loading its data — if this persists, the index feed is temporarily unreachable.</div>';
  });
})();
