/* Medical Sales Intelligence Hub — "ICB watch": the Integrated Care Board count,
   clusters, leaders and recent changes, on the NHS structure page (WP 884).
   Git-served, same pattern as whos-who.js: page 884 carries only a mount
   (<div id="msh-icbwatch">) and a fetch + new Function loader. Edit here, never
   in wp-admin.

   Data: data/icb-watch.json, written daily by scripts/refresh_icb_watch.py
   (icb-watch.yml). Every name shown is linked to the page it was read from.
   Nothing here states a future ICB number: NHS England has published none. */
(function(){
  var MOUNT_ID = 'msh-icbwatch';
  var SRC = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/icb-watch.json';
  var FAM = {medicines:'Medicines lead', cmo:'Medical leadership', nursing:'Nursing, clinical and quality', cfo:'Finance'};

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function ukDate(iso){
    if (!iso) return '';
    var p = String(iso).slice(0, 10).split('-');
    return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : esc(iso);
  }
  function host(u){ try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return 'source'; } }
  function srcLinks(urls){
    return (urls || []).map(function(u){
      return '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(host(u)) + ' &#8599;</a>';
    }).join(' · ');
  }
  function shortName(n){ return String(n || '').replace(/^NHS /, '').replace(/ Integrated Care Board$/, ''); }

  var CSS = '.icbw,.icbw *{box-sizing:border-box}.icbw{overflow-wrap:anywhere;margin-top:22px;background:#ffffff;border:1px solid #e7e1d4;border-top:3px solid #b8902f;border-radius:12px;padding:20px 22px;color:#11202f;font-size:14px;line-height:1.55}'
    + '.icbw h3{font-size:18px;margin:0 0 4px;color:#11202f}'
    + '.icbw .icbw-sub{color:#37485a;margin:0 0 14px}'
    + '.icbw .icbw-stats{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 14px}'
    + '.icbw .icbw-stat{background:#0e1b2a;color:#ffffff;border-radius:10px;padding:10px 14px;min-width:150px}'
    + '.icbw .icbw-stat b{display:block;font-size:22px;color:#E0BE8E}'
    + '.icbw .icbw-stat span{font-size:12.5px;color:#EDE7DC}'
    + '.icbw blockquote{margin:0 0 16px;padding:10px 14px;background:#f3ead2;border-left:3px solid #b8902f;color:#11202f;font-size:13.5px}'
    + '.icbw h4{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#6b5a2a;margin:18px 0 8px}'
    + '.icbw .icbw-ev{border-bottom:1px solid #efe9dd;padding:10px 0}'
    + '.icbw .icbw-ev:last-child{border-bottom:0}'
    + '.icbw .icbw-when{font-size:12px;color:#37485a;font-weight:600}'
    + '.icbw .icbw-ev b{color:#11202f}'
    + '.icbw details summary{cursor:pointer;color:#6b5a2a;font-size:13px;margin-top:4px}'
    + '.icbw details p{margin:6px 0 0;color:#11202f}'
    + '.icbw .icbw-src{font-size:12.5px;color:#37485a}'
    + '.icbw .icbw-src a{color:#6b5a2a;text-decoration:underline}'
    + '.icbw .icbw-controls{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 10px}'
    + '.icbw select,.icbw input{font:inherit;font-size:13.5px;padding:7px 10px;border:1px solid #d9d1bf;border-radius:8px;background:#ffffff;color:#11202f}'
    + '.icbw .icbw-card{border:1px solid #e7e1d4;border-radius:10px;padding:12px 14px;margin:0 0 10px;background:#fdfcf9}'
    + '.icbw .icbw-card h5{font-size:15px;margin:0 0 2px;color:#11202f}'
    + '.icbw .icbw-meta{font-size:12.5px;color:#37485a;margin:0 0 6px}'
    + '.icbw .icbw-tag{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px;background:#f3ead2;color:#5a4712;margin-left:6px}'
    + '.icbw .icbw-row{margin:3px 0}'
    + '.icbw .icbw-row .k{display:inline-block;min-width:190px;color:#37485a;font-size:13px}'
    + '.icbw .icbw-none{color:#37485a;font-style:italic}'
    + '.icbw .icbw-foot{font-size:12.5px;color:#37485a;margin-top:12px}'
    + '@media (max-width:640px){.icbw{padding:16px}.icbw .icbw-row .k{display:block;min-width:0}}';

  function eventHtml(ev, byCode){
    var who = ev.icb && byCode[ev.icb] ? shortName(byCode[ev.icb].name) : 'All ICBs';
    return '<div class="icbw-ev"><div class="icbw-when">' + ukDate(ev.date) + ' · ' + esc(who) + '</div>'
      + '<b>' + esc(ev.headline) + '</b>'
      + '<details><summary>What the source says</summary><p>' + esc(ev.detail) + '</p>'
      + '<p class="icbw-src">Source: ' + srcLinks(ev.sources)
      + (ev.verifiedOn ? ' · checked by the Hub ' + ukDate(ev.verifiedOn) : '') + '</p></details></div>';
  }

  function leaderLine(i, role, label){
    var l = (i.leaders || []).filter(function(x){ return x.role === role; })[0];
    if (!l || !l.name) return '<div class="icbw-row"><span class="k">' + label + '</span><span class="icbw-none">Not listed by NHS England</span></div>';
    return '<div class="icbw-row"><span class="k">' + label + '</span>' + esc(l.name)
      + (l.qualifier ? '<span class="icbw-tag">' + esc(l.qualifier) + '</span>' : '') + '</div>';
  }

  function execLines(i, byCode){
    var out = '';
    ['medicines', 'cmo', 'nursing', 'cfo'].forEach(function(f){
      var hits = (i.execs || []).filter(function(e){ return e.family === f; });
      if (hits.length) {
        out += '<div class="icbw-row"><span class="k">' + FAM[f] + '</span>' + hits.map(function(e){
          return esc(e.name) + ', ' + esc(e.title) + (e.stale ? ' <span class="icbw-tag">last seen ' + ukDate(e.lastSeen) + '</span>' : '')
            + ' <span class="icbw-src">(<a href="' + esc(e.url) + '" target="_blank" rel="noopener">source &#8599;</a>)</span>';
        }).join('; ') + '</div>';
      } else if (f === 'medicines') {
        var partner = null;
        (i.clusterCodes || []).forEach(function(c){
          var p = byCode[c];
          if (!partner && p) {
            var m = (p.execs || []).filter(function(e){ return e.family === 'medicines'; })[0];
            if (m) partner = {icb: p, e: m};
          }
        });
        out += '<div class="icbw-row"><span class="k">' + FAM[f] + '</span><span class="icbw-none">Not named on this ICB’s leadership page</span>'
          + (partner ? '. Its cluster partner ' + esc(shortName(partner.icb.name)) + ' names ' + esc(partner.e.name) + ', ' + esc(partner.e.title)
             + ' <span class="icbw-src">(<a href="' + esc(partner.e.url) + '" target="_blank" rel="noopener">source &#8599;</a>)</span>' : '')
          + '</div>';
      }
    });
    return out;
  }

  function cardHtml(i, byCode){
    var cl = (i.clusterCodes || []).map(function(c){ return byCode[c] ? shortName(byCode[c].name) : c; });
    var evs = (i._events || []);
    return '<div class="icbw-card" data-region="' + esc(i.region) + '" data-q="' + esc((i.name + ' ' + cl.join(' ')).toLowerCase()) + '">'
      + '<h5>' + esc(shortName(i.name)) + ' ICB</h5>'
      + '<div class="icbw-meta">' + esc(i.region || '') + (cl.length ? ' · clusters with ' + esc(cl.join(' and ')) + ' (shared leadership, separate legal bodies)' : '') + '</div>'
      + leaderLine(i, 'chair', 'Chair') + leaderLine(i, 'ceo', 'Chief executive')
      + execLines(i, byCode)
      + (evs.length ? '<div class="icbw-row"><span class="k">Recent changes</span>' + evs.map(function(e){ return ukDate(e.date) + ': ' + esc(e.headline); }).join('<br>') + '</div>' : '')
      + '<div class="icbw-src" style="margin-top:6px">Chair and chief executive: <a href="' + esc(i.leadersSource) + '" target="_blank" rel="noopener">NHS England &#8599;</a>'
      + ((i.execSources || []).length ? ' · executives read from ' + srcLinks(i.execSources) : ' · this ICB’s own leadership page could not be read automatically')
      + '</div></div>';
  }

  function render(m, d){
    var byCode = {};
    (d.icbs || []).forEach(function(i){ byCode[i.code] = i; i._events = []; i.clusterCodes = []; });
    (d.clusters || []).forEach(function(c){
      c.forEach(function(code){ if (byCode[code]) byCode[code].clusterCodes = c.filter(function(x){ return x !== code; }); });
    });
    (d.events || []).forEach(function(ev){
      [ev.icb].concat(ev.alsoIcbs || []).forEach(function(c){ if (c && byCode[c]) byCode[c]._events.push(ev); });
    });
    var inClusters = 0; (d.clusters || []).forEach(function(c){ inClusters += c.length; });
    var regions = []; (d.icbs || []).forEach(function(i){ if (i.region && regions.indexOf(i.region) < 0) regions.push(i.region); });
    regions.sort();
    var st = d.nationalStatement || {};
    var recent = (d.events || []).slice(0, 12);

    var h = '<style>' + CSS + '</style><div class="icbw">'
      + '<h3>ICB watch: mergers, clusters and who leads each Integrated Care Board (ICB)</h3>'
      + '<p class="icbw-sub">Refreshed daily from the NHS register, NHS England and each ICB’s own leadership page. Data as of ' + esc(d.asOf) + '.</p>'
      + '<div class="icbw-stats">'
      + '<div class="icbw-stat"><b>' + esc(d.count) + '</b><span>ICBs legally in existence today</span></div>'
      + '<div class="icbw-stat"><b>' + (d.clusters || []).length + '</b><span>clusters, covering ' + inClusters + ' ICBs</span></div>'
      + '<div class="icbw-stat"><b>' + (d.abolished || []).length + '</b><span>ICBs abolished on ' + ukDate(((d.abolished || [])[0] || {}).legalEnd) + '</span></div>'
      + '</div>'
      + (st.text ? '<blockquote><b>NHS England’s current position on further mergers:</b> “' + esc(st.text) + '” <span class="icbw-src">(<a href="' + esc(st.url) + '" target="_blank" rel="noopener">NHS England &#8599;</a>, checked ' + ukDate(st.checkedOn) + ')</span></blockquote>' : '')
      + '<h4>Recent changes</h4>'
      + (recent.length ? recent.map(function(e){ return eventHtml(e, byCode); }).join('')
                       : '<p class="icbw-none">No ICB leadership or structure change has been recorded in the last six months.</p>')
      + '<h4>Every ICB</h4>'
      + '<div class="icbw-controls"><select id="icbw-region"><option value="">All regions</option>'
      + regions.map(function(r){ return '<option>' + esc(r) + '</option>'; }).join('') + '</select>'
      + '<input id="icbw-q" type="search" placeholder="Find an ICB" aria-label="Find an ICB"></div>'
      + '<div id="icbw-cards">' + (d.icbs || []).slice().sort(function(a, b){ return (a.region + a.name).localeCompare(b.region + b.name); })
          .map(function(i){ return cardHtml(i, byCode); }).join('') + '</div>'
      + '<p class="icbw-foot">How this works: the ICB count comes from the NHS Organisation Data Service, filtered on legal end date. A new office-holder is shown only once they have been read on two separate days, and someone who simply stops appearing on a page is never reported as having left. Most ICBs do not name their medicines lead on their leadership pages; where one does, it is shown with its source. Board papers and committee minutes are checked by hand and marked with the date the Hub checked them.</p>'
      + '</div>';
    m.innerHTML = h;

    var sel = document.getElementById('icbw-region'), q = document.getElementById('icbw-q');
    function filter(){
      var r = sel.value, t = (q.value || '').toLowerCase();
      var cards = m.querySelectorAll('.icbw-card');
      for (var k = 0; k < cards.length; k++) {
        var c = cards[k];
        var ok = (!r || c.getAttribute('data-region') === r) ? (!t || c.getAttribute('data-q').indexOf(t) >= 0) : false;
        c.style.display = ok ? '' : 'none';
      }
    }
    sel.addEventListener('change', filter);
    q.addEventListener('input', filter);
  }

  /* Page 884's own text (in wp-admin) said "~26 expected by 2027", "Midlands 11
     ICBs (→ 5)", "South West 7 ICBs (→ 3)" and that the remaining mergers "are
     decided in summer 2026". None of that is in any NHS England source: the
     Midlands and South West figures are CLUSTER counts, clusters stay separate
     legal bodies, and NHS England has published no future number (checked
     30/09/2026). Same arrangement as fixNote() in mst-logic.js for page 1109:
     corrected here, in version control beside the data, and each replacement
     is a no-op once the wp-admin text is fixed at source. */
  function fixStructureText(){
    var root = document.querySelector('.msh') || document.body;
    var swaps = [
      [/\s*[—–-]\s*the mergers are levelling them to roughly 3[–-]5 each\./,
       '. In the Midlands, the South West and London, 20 ICBs already work in 9 clusters that share a chair, a chief executive and teams while remaining separate legal bodies.'],
      [/<b>~26<\/b>\s*expected by 2027/, '<b>9</b> clusters (20 ICBs)'],
      [/A further, unconfirmed round is proposed for April 2027\./,
       'A further round is proposed for April 2027 but is not confirmed: NHS England says future decisions on ICB footprints will be taken in light of Local Government Reorganisation, and has published no target number.'],
      [/<b>11<\/b> ICBs \(→ 5\)/, '<b>11</b> ICBs (in 5 clusters)'],
      [/<b>7<\/b> ICBs \(→ 3\)/, '<b>7</b> ICBs (in 3 clusters)'],
      [/<b>4<\/b> ICBs \(merged from 5, Apr 2026\)/, '<b>4</b> ICBs (merged from 5, Apr 2026; South East and South West London cluster)'],
      [/\s*[—–-]\s*part of a longer move toward an expected <b>~26<\/b> by 2027\./, '. The 12 abolished ICBs legally ended on 31 March 2026.'],
      [/the remaining ICB mergers and boundary changes are decided in summer 2026 and land in <b>April 2027<\/b> \(North East (&amp;|&) Yorkshire and North West unchanged so far\)\./,
       'ICB clusters were asked to give NHS England their views on future merged footprints by 14 July 2026, for a possible round in <b>April 2027</b>. As at 30 September 2026 no decision has been published, and NHS England says future footprints will be decided in light of Local Government Reorganisation (North East $1 Yorkshire and North West have no clusters).'],
      [/<b>Last reviewed:<\/b> June 2026/, '<b>Last reviewed:</b> 30 September 2026']
    ];
    var els = root.querySelectorAll('p, span, div.cnt, div.what, div.reviewbar span');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el.children.length > 12) continue;
      var h = el.innerHTML, h2 = h;
      for (var k = 0; k < swaps.length; k++) h2 = h2.replace(swaps[k][0], swaps[k][1]);
      if (h2 !== h) el.innerHTML = h2;
    }
  }

  /* Page 884 has no mount of its own yet: place one at the end of section 2
     ("The 36 ICBs, by NHS region"). A mount added in wp-admin wins. */
  function ensureMount(){
    if (document.getElementById(MOUNT_ID)) return true;
    var hs = document.querySelectorAll('.msh h2');
    for (var i = 0; i < hs.length; i++) {
      if (/ICBs, by NHS region/.test(hs[i].textContent)) {
        var d = document.createElement('div');
        d.id = MOUNT_ID;
        hs[i].parentNode.appendChild(d);
        return true;
      }
    }
    return false;
  }

  function mount(){
    ensureMount();
    var m = document.getElementById(MOUNT_ID);
    if (!m) return false;
    try { fixStructureText(); } catch (e) {}
    fetch(SRC + '?cb=' + new Date().toISOString().slice(0, 10))
      .then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function(d){ render(m, d); })
      .catch(function(){
        m.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:#11202f;background:#f3ead2;padding:12px 14px;border-radius:8px;">'
          + 'The ICB watch is temporarily unavailable. Please try again shortly.</div>';
      });
    return true;
  }

  if (!mount()) {
    var tries = 0;
    var t = setInterval(function(){ if (mount() || ++tries > 40) clearInterval(t); }, 120);
  }
})();
