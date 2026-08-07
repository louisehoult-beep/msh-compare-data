/* Medical Sales Hub — Supplier Intelligence Search
   Loaded by a tiny loader on WP page 677. Full code lives in
   github.com/louisehoult-beep/msh-compare-data/app/supplier-search.js
   Data: data/supplier-index.json (same repo). */
(function(){
  var DATA_URL='https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/supplier-index.json';
  /* THE FULL RANGE, WHERE WE HOLD ONE — and it is a DIFFERENT KIND OF FACT from
     everything else on this card. `supplier-index.json` products are the ones
     the procurement record names: framework awards, catalogue lines, recalls.
     `supplier-products.json` is the company's own website range, captured by
     scripts/crawl_supplier_site.py. It is much bigger (GBUK 343 against the 45
     the index knows) and it is how the company organises itself, which is what
     a rep meets in the room.
     It is NOT the procurement record and must never be shown as if it were, so
     it renders in its own section, under the company's own division names, with
     the capture route stated. Four suppliers have one today. */
  var RANGE_URL='https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/supplier-products.json';
  var RANGE={};
  var MOUNT=document.getElementById('msh-supplier-search');
  if(!MOUNT) return;
  /* Resolve a supplier record to its full range by name or alias, both ways
     round: the range file carries its own aliases (GBUK's include "GBUK Vascular"
     and "GBUK Healthcare") and the index record carries 23 more. Matching on the
     display name alone would find GBUK and miss anything filed under a variant. */
  function rangeFor(s){
    if(!s) return null;
    var keys={}, i;
    var mine=[s.name].concat(s.aliases||[]);
    for(i=0;i<mine.length;i++){ if(mine[i]) keys[norm(mine[i])]=1; }
    for(var k in RANGE){
      if(keys[norm(k)]) return RANGE[k];
      var al=RANGE[k].aliases||[];
      for(i=0;i<al.length;i++){ if(keys[norm(al[i])]) return RANGE[k]; }
    }
    return null;
  }
  var G='#a8842c', INK='#1d2733', DIM='#75808d', LINE='#e6e0d4', RED='#b84a5c', GREEN='#2e7d5b';
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function norm(s){return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();}

  function shell(){
    MOUNT.innerHTML=''+
    '<div style="font-family:Inter,-apple-system,Segoe UI,sans-serif;margin:0;">'+
      '<div style="padding:2px 0 6px;">'+
        '<div style="font-size:11.5px;letter-spacing:2px;font-weight:700;color:'+G+';">SUPPLIER INTELLIGENCE SEARCH</div>'+
        '<p style="margin:5px 0 12px;font-size:13.5px;color:'+DIM+';">Type a supplier or brand — get their frameworks, products, and live alerts/recalls, all in one place. <span id="mssCount"></span></p>'+
        '<input id="mssInput" list="mssList" autocomplete="off" placeholder="e.g. BD, Vygon, Coloplast, Nexiva…" '+
          'style="width:100%;max-width:520px;padding:11px 16px;border-radius:99px;border:1px solid '+LINE+';font:inherit;font-size:15px;color:'+INK+';background:#ffffff;-webkit-text-fill-color:'+INK+';caret-color:'+INK+';outline:none;">'+
        '<datalist id="mssList"></datalist>'+
        '<div id="mssChips" style="margin:10px 0 2px;display:flex;flex-wrap:wrap;gap:6px;"></div>'+
      '</div>'+
      '<div id="mssResult" style="padding:2px 18px 18px;"></div>'+
    '</div>';
  }

  function card(s){
    function sec(title,html){return '<div style="margin:14px 0 0;"><div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;font-weight:700;color:'+DIM+';margin-bottom:6px;">'+title+'</div>'+html+'</div>';}
    var h='<div style="border:1px solid '+LINE+';border-radius:11px;padding:16px 18px;background:#fdfcf9;">';
    // header: image/monogram + name
    var _w=s.name.replace(/^the\s+/i,'').split(/[\s\-—,\.]+/).filter(Boolean);var inits=esc((/^[A-Za-z0-9]{2,4}$/.test(_w[0]||'')?_w[0]:_w.slice(0,2).map(function(w){return w[0];}).join('')).toUpperCase());
    var ph='<div style="width:56px;height:56px;flex:0 0 56px;border-radius:10px;background:#efe9db;border:1px solid '+LINE+';display:flex;align-items:center;justify-content:center;font-weight:700;color:'+G+';font-size:16px;">'+inits+'</div>';
    var thumb = s.image ? '<img src="'+esc(s.image)+'" alt="" referrerpolicy="no-referrer" loading="lazy" style="width:56px;height:56px;flex:0 0 56px;border-radius:10px;object-fit:contain;background:#fff;border:1px solid '+LINE+';" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div style="display:none;width:56px;height:56px;flex:0 0 56px;border-radius:10px;background:#efe9db;border:1px solid '+LINE+';align-items:center;justify-content:center;font-weight:700;color:'+G+';font-size:16px;">'+inits+'</div>' : ph;
    h+='<div style="display:flex;gap:13px;align-items:flex-start;">'+thumb+'<div><div style="font-size:20px;font-weight:700;color:'+INK+';">'+esc(s.name)+(s.autoDetected?' <span style="font-size:10px;font-weight:700;letter-spacing:.06em;color:#7a5b14;background:#f3e8cf;border-radius:99px;padding:2px 8px;vertical-align:3px;">AUTO — VERIFY AT SOURCE</span>':'')+'</div>'+
      (s.note?'<p style="margin:4px 0 0;font-size:13.5px;color:#37485a;">'+esc(s.note)+'</p>':'')+'</div></div>';
    if(s.specialities&&s.specialities.length) h+='<div style="margin-top:8px;">'+s.specialities.map(function(x){return '<span style="display:inline-block;background:#f3ead2;color:#7a5b14;border-radius:99px;padding:3px 10px;font-size:11.5px;font-weight:600;margin-right:6px;">'+esc(x)+'</span>';}).join('')+'</div>';

    /* FRAMEWORKS — AND A HARD SPLIT BETWEEN LIVE AND ENDED.
       Until 07/08/2026 every row sat under one heading, "Frameworks on", with
       its date range printed beside it and nothing else. Twenty-four rows named
       a framework that had already ended — Medtronic, Boston Scientific and
       Abbott all showed "Transcatheter Heart Valve … 18 September 2023 to 17
       September 2025" as a current position, ten months after it stopped. A rep
       reads a heading, not a date range.

       The end date is parsed from the row's own `dates` string here rather than
       trusted from a flag, so this holds however the row was written and
       whichever file it came from. A framework that has ended is real
       intelligence — it usually means the incumbency has just reset — so it
       moves to its own heading instead of being deleted. */
    function fwEnd(f){
      var m=/(?:to|–|-|—)\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*$/.exec(String((f&&f.dates)||'').trim());
      if(!m){return null;}
      var t=Date.parse(m[1]);
      return isNaN(t)?null:new Date(t);
    }
    function fwRow(f,ended){
      return '<div style="padding:7px 0;border-bottom:1px solid #f0ece3;font-size:13.5px;'+(ended?'opacity:.75;':'')+'"><b>'+esc(f.name)+'</b>'+
        (ended?' <span style="background:#f2f2f2;border:1px solid #dcdcdc;color:#5b6675;font-size:10px;font-weight:700;letter-spacing:.06em;border-radius:99px;padding:2px 8px;">ENDED</span>':'')+
        (f.value?' <span style="color:'+GREEN+';font-weight:700;">'+esc(f.value)+'</span>':'')+
        (f.dates?' <span style="color:'+DIM+';">· '+esc(f.dates)+'</span>':'')+
        (f.note?'<br><span style="color:#37485a;font-size:12.5px;">'+esc(f.note)+'</span>':'')+'</div>';
    }
    if(s.frameworks&&s.frameworks.length){
      var now=new Date(), live=[], gone=[];
      s.frameworks.forEach(function(f){ var e=fwEnd(f); (e&&e<now?gone:live).push(f); });
      if(live.length) h+=sec('Frameworks on', live.map(function(f){return fwRow(f,false);}).join(''));
      else h+=sec('Frameworks on','<div style="font-size:13px;color:'+DIM+';">No live framework indexed'+(gone.length?' — but see below':'')+'.</div>');
      if(gone.length) h+=sec('Frameworks that have ENDED — do not quote these as current',
        '<div style="font-size:11.5px;color:'+DIM+';margin:0 0 6px;">Kept because an expired framework is worth knowing about: it usually means the incumbency has just reset. It is not a route to market today.</div>'
        + gone.map(function(f){return fwRow(f,true);}).join(''));
    } else h+=sec('Frameworks on','<div style="font-size:13px;color:'+DIM+';">No framework indexed yet.</div>');

    // products
    if(s.products&&s.products.length){
      h+=sec('Products / brands', s.products.map(function(p){return '<span style="display:inline-block;border:1px solid '+LINE+';border-radius:99px;padding:4px 11px;font-size:12.5px;margin:0 5px 5px 0;color:#37485a;">'+esc(p)+'</span>';}).join(''));
    }

    /* Full range, by the company's own divisions. Collapsed by default: 733
       lines unrolled above the alerts would bury them. */
    var rng=rangeFor(s);
    if(rng&&(rng.products||[]).length){
      var byDiv={}, order=[];
      (rng.products||[]).forEach(function(p){
        var dv=(p&&p.division)||'Other';
        if(!byDiv[dv]){byDiv[dv]=[];order.push(dv);}
        byDiv[dv].push(p);
      });
      order.sort(function(a,b){return byDiv[b].length-byDiv[a].length;});
      var body='<div style="font-size:11.5px;color:'+DIM+';margin:0 0 8px;line-height:1.55;">'+
        'The company’s own website range, in its own divisions — <b>not</b> the procurement '+
        'record. Captured '+esc(rng.verified||(rng.source?'':'—'))+
        (rng.source?' from '+esc(String(rng.source).slice(0,120)):'')+'. '+
        'Useful for knowing what they actually sell; for what the NHS has bought, read the '+
        'frameworks above.'+
        (rng.captureCaveat?'<br><br><b>How this one was captured:</b> '+esc(rng.captureCaveat):'')+
        '</div>';
      order.forEach(function(dv){
        var items=byDiv[dv];
        body+='<details style="margin:0 0 6px;border:1px solid '+LINE+';border-radius:8px;background:#fff;">'+
          '<summary style="cursor:pointer;padding:8px 12px;font-size:13px;font-weight:600;color:'+INK+';">'+
          esc(dv)+' <span style="color:'+DIM+';font-weight:400;">· '+items.length+'</span></summary>'+
          '<div style="padding:2px 12px 10px;">'+
          items.map(function(p){
            var cat=p&&p.category;
            return '<span style="display:inline-block;border:1px solid '+LINE+';border-radius:99px;'+
              'padding:3px 10px;font-size:12px;margin:0 5px 5px 0;color:#37485a;"'+
              (cat?' title="'+esc(cat)+'"':'')+'>'+esc(p&&p.n)+'</span>';
          }).join('')+'</div></details>';
      });
      h+=sec('Full range — '+(rng.products||[]).length+' products across '+order.length+
             ' of their own divisions', body);
    }

    // awards
    if(s.awards&&s.awards.length){
      var aw=s.awards.slice(0,8);
      h+=sec('Awards won ('+s.awards.length+')', aw.map(function(a){
        return '<div style="padding:7px 0;border-bottom:1px solid #f0ece3;font-size:13px;"><b>'+esc(a.title||'Contract')+'</b>'+
          (a.value?' <span style="color:'+GREEN+';font-weight:700;">'+esc(a.value)+'</span>':'')+
          (a.date?' <span style="color:'+DIM+';">· '+esc(a.date)+'</span>':'')+
          (a.buyer?'<br><span style="color:#37485a;font-size:12.5px;">Buyer: '+esc(a.buyer)+'</span>':'')+
          (a.url?' <a href="'+esc(a.url)+'" target="_blank" rel="noopener" style="color:'+G+';font-weight:600;">↗</a>':'')+'</div>';
      }).join('') + (s.awards.length>8?'<div style="font-size:12px;color:'+DIM+';margin-top:4px;">+'+(s.awards.length-8)+' more — see the Award Tracker.</div>':''));
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

    // news (only stories corroborated by >=2 reputable sources reach here)
    if(s.news&&s.news.length){
      h+=sec('News · verified by 2+ sources', s.news.map(function(nw){
        var srcs=(nw.sources||[]).map(function(x){return x.url?'<a href="'+esc(x.url)+'" target="_blank" rel="noopener" style="color:'+G+';font-weight:600;">'+esc(x.publisher)+' ↗</a>':esc(x.publisher);}).join(' · ');
        return '<div style="padding:8px 0;border-bottom:1px solid #f0ece3;font-size:13px;">'+
          '<span style="color:'+GREEN+';font-weight:700;">✓</span> <b>'+esc(nw.headline)+'</b>'+
          (nw.date?' <span style="color:'+DIM+';">· '+esc(nw.date)+'</span>':'')+
          '<br><span style="color:'+DIM+';font-size:12px;">Corroborated by: </span>'+srcs+'</div>';
      }).join(''));
    }
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
      // partial: name/alias contains
      var part=sup.filter(function(s){
        if(norm(s.name).indexOf(n)>-1) return true;
        if((s.aliases||[]).some(function(a){return norm(a).indexOf(n)>-1;})) return true;
        return false;
      })[0];
      if(part) return part;
      /* Only now fall back to product names, and search the FULL RANGE as well
         as the index's short list — "Nutrisafe2" is a real Vygon product and
         used to return nothing because the index knows 8 Vygon products and the
         company sells 200.
         Product matching is deliberately LAST. It is the arm that returned
         Dentaquip for "KaVo", because Dentaquip's product list contains the word
         — so it must never outrank a company whose own name matches. */
      var byProd=sup.filter(function(s){
        if((s.products||[]).some(function(p){return norm(p).indexOf(n)>-1;})) return true;
        var r=rangeFor(s);
        return !!(r&&(r.products||[]).some(function(p){return norm(p&&p.n).indexOf(n)>-1;}));
      })[0];
      return byProd||null;
    }
    function show(q){
      var s=find(q);
      result.innerHTML = s ? card(s) :
        '<div style="padding:14px 4px;font-size:13.5px;color:'+DIM+';">No match for “'+esc(q)+'”. Coverage is the tracked-supplier set ('+sup.length+' indexed) — a supplier not here is <b>not yet indexed</b>, not “nothing found”.</div>';
    }
    input.addEventListener('change',function(){show(input.value);});
    input.addEventListener('keydown',function(e){if(e.key==='Enter')show(input.value);});
    chips.addEventListener('click',function(e){var b=e.target.closest('button');if(b){input.value=b.getAttribute('data-q');show(input.value);}});

    // DEEP LINK — added 06/08/2026 for Hub search.
    // The Hub's search index carries a record per supplier, because these 459
    // names are loaded from JSON at run time and appear in no page's HTML, so
    // they were unfindable anywhere on the Hub. Those results link here as
    // #q=<name>. Without this, the link lands on the page and the member has to
    // type the name they just searched for a second time.
    function fromHash(){
      var h=String(window.location.hash||'');
      if(h.indexOf('#q=')!==0) return;
      var q='';
      try { q=decodeURIComponent(h.slice(3).replace(/\+/g,' ')); } catch(e){ q=h.slice(3); }
      q=q.trim();
      if(!q) return;
      input.value=q;
      show(q);
      try { input.scrollIntoView({block:'center'}); } catch(e){}
    }
    fromHash();
    window.addEventListener('hashchange',fromHash);
  }

  /* The range file is a bonus, never a dependency: if it fails the page shows
     exactly what it showed before it existed. The index is the one that matters,
     so it keeps its own error state. */
  function loadRange(){
    return fetch(RANGE_URL,{cache:'no-store'})
      .then(function(r){return r.json();})
      .then(function(j){ RANGE=(j&&j.suppliers)||{}; })
      .catch(function(){ RANGE={}; });
  }
  if(window.MSH_SUPPLIER_INDEX){ var d0=window.MSH_SUPPLIER_INDEX; loadRange().then(function(){run(d0);}); return; }
  loadRange()
    .then(function(){return fetch(DATA_URL,{cache:'no-store'});})
    .then(function(r){return r.json();}).then(run).catch(function(){
    MOUNT.innerHTML='<div style="font-family:Inter,sans-serif;color:'+DIM+';font-size:13px;padding:12px;">Supplier search is loading its data — if this persists, the index feed is temporarily unreachable.</div>';
  });
})();
