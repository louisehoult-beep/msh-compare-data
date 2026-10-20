/* Medical Sales Intelligence Hub — "NPM Finder": every NHS Supply Chain
   National Pricing Matrix (NPM) category beside its live framework.
   Git-served, same pattern as icb-watch.js: the Hub page carries only a mount
   (<div id="msh-npmfinder">) and a fetch + new Function loader. Edit here,
   never in wp-admin.

   Data: data/npm-finder.json, written weekly by scripts/refresh_npm_finder.py
   (nhssc-launch-briefs.yml). Which suppliers offer each NPM is published by
   NHS Supply Chain only to signed-in customers, so this page never names them
   unless the public launch brief does in its own sentence. */
(function(){
  var MOUNT_ID = 'msh-npmfinder';
  var SRC = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/npm-finder.json';
  var FRAMEWORKS_PAGE = '/medical-sales-hub/tender-history/';

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

  var CSS = '.npmf,.npmf *{box-sizing:border-box}.npmf{overflow-wrap:anywhere;margin-top:22px;background:#ffffff;border:1px solid #e7e1d4;border-top:3px solid #A8842C;border-radius:12px;padding:20px 22px;color:#0B1C33;font-size:14px;line-height:1.55;font-family:Inter,system-ui,sans-serif}'
    + '.npmf h3{font-size:20px;margin:0 0 4px;color:#0B1C33}'
    + '.npmf .npmf-sub{color:#37485a;margin:0 0 14px}'
    + '.npmf .npmf-stats{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 14px}'
    + '.npmf .npmf-stat{background:#0B1C33;border-radius:10px;padding:10px 14px;min-width:150px}'
    + '.npmf .npmf-stat b{display:block;font-size:22px;color:#E0BE8E}'
    + '.npmf .npmf-stat span{font-size:12.5px;color:#EDE7DC}'
    + '.npmf details.npmf-how{background:#F5F1E8;border:1px solid #E7E2D6;border-radius:10px;padding:10px 14px;margin:0 0 14px}'
    + '.npmf details.npmf-how summary{cursor:pointer;font-weight:700;color:#14304F}'
    + '.npmf details.npmf-how p{margin:8px 0 0;color:#0B1C33}'
    + '.npmf .npmf-controls{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 12px}'
    + '.npmf input,.npmf select{font:inherit;font-size:14px;padding:8px 10px;border:1px solid #d9d1bf;border-radius:8px;background:#ffffff;color:#0B1C33}'
    + '.npmf input{flex:1 1 260px}'
    + '.npmf .npmf-card{border:1px solid #e7e1d4;border-radius:10px;padding:12px 14px;margin:0 0 10px;background:#fdfcf9}'
    + '.npmf .npmf-card h4{font-size:15.5px;margin:0 0 4px;color:#0B1C33}'
    + '.npmf .npmf-row{margin:3px 0}'
    + '.npmf .npmf-row .k{display:inline-block;min-width:170px;color:#37485a;font-size:13px}'
    + '.npmf .npmf-quote{margin:8px 0 6px;padding:8px 12px;background:#F5F1E8;border-left:3px solid #A8842C;color:#0B1C33;font-size:13.5px}'
    + '.npmf .npmf-who{font-size:13px;color:#37485a;margin:4px 0 0}'
    + '.npmf .npmf-tag{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px;background:#F5F1E8;color:#14304F;margin-left:6px;border:1px solid #E7E2D6}'
    + '.npmf a{color:#14304F;text-decoration:underline}'
    + '.npmf .npmf-none{color:#37485a;font-style:italic}'
    + '.npmf .npmf-foot{font-size:12.5px;color:#37485a;margin-top:12px}'
    + '@media (max-width:640px){.npmf{padding:16px}.npmf .npmf-row .k{display:block;min-width:0}}';

  function card(c){
    var fw = c.framework, br = c.brief || {};
    var h = '<div class="npmf-card"><h4>' + esc(c.category) + '</h4>';
    if (fw) {
      h += '<div class="npmf-row"><span class="k">Framework</span>'
        + (fw.url ? '<a href="' + esc(fw.url) + '" target="_blank" rel="noopener">' + esc(fw.name) + ' &#8599;</a>' : esc(fw.name)) + '</div>';
      if (fw.starts || fw.ends) h += '<div class="npmf-row"><span class="k">Runs</span>' + esc(fw.starts || '?') + ' to ' + esc(fw.ends || '?') + '</div>';
      if (fw.reference) h += '<div class="npmf-row"><span class="k">Notice reference</span>' + esc(fw.reference) + '</div>';
      if (fw.supplyRoute) h += '<div class="npmf-row"><span class="k">Supply route</span>' + esc(fw.supplyRoute) + '</div>';
      if (fw.supplierCount) h += '<div class="npmf-row"><span class="k">Suppliers on the framework</span>' + fw.supplierCount
        + ' (<a href="' + FRAMEWORKS_PAGE + '">see them in Frameworks and Awards</a>)</div>';
      if (br.statement) h += '<div class="npmf-quote">&#8220;' + esc(br.statement) + '&#8221; <span style="color:#37485a">(launch brief)</span></div>';
      else if (br.read === false) h += '<p class="npmf-none">The launch brief could not be read on the last run.</p>';
      h += '<p class="npmf-who">Which suppliers offer it, and their price tiers, are in NHS Supply Chain\'s NPM download for signed-in customers. Your Hospital Care Team can take you through it.</p>';
    } else {
      h += '<p class="npmf-none">No live framework on the Hub has this name. The NPM may sit on an earlier or renamed framework: check with your Hospital Care Team.</p>';
    }
    return h + '</div>';
  }

  function render(m, d){
    var cats = d.categories || [];
    var g = d.guidance || {};
    var h = '<style>' + CSS + '</style><div class="npmf">'
      + '<h3>All National Pricing Matrix (NPM) categories</h3>'
      + '<p class="npmf-sub">Every framework category where NHS Supply Chain offers a National Pricing Matrix (NPM), with the framework it sits on. Find the product area here, then ask your Hospital Care Team to take you through the NPM.</p>'
      + '<div class="npmf-stats">'
      + '<div class="npmf-stat"><b>' + cats.length + '</b><span>NPM categories</span></div>'
      + '<div class="npmf-stat"><b>' + (d.matchedCount || 0) + '</b><span>matched to a live framework</span></div>'
      + '<div class="npmf-stat"><b>' + ukDate(d.generated) + '</b><span>last read from NHS Supply Chain</span></div>'
      + '</div>';
    if (g.what || g.who || g.how) {
      h += '<details class="npmf-how"><summary>What an NPM is, who can use one and how to sign up (NHS Supply Chain\'s words)</summary>'
        + (g.what ? '<p><b>What it is.</b> ' + esc(g.what) + '</p>' : '')
        + (g.who ? '<p><b>Who can use one.</b> ' + esc(g.who) + '</p>' : '')
        + (g.how ? '<p><b>How to sign up.</b> ' + esc(g.how) + '</p>' : '')
        + '</details>';
    }
    h += '<div class="npmf-controls"><input type="search" placeholder="Search a product area, for example cannula or wound" aria-label="Search NPM categories">'
      + '<select aria-label="Filter"><option value="all">All categories</option><option value="matched">Matched to a framework</option><option value="unmatched">Not matched</option></select></div>'
      + '<div class="npmf-list"></div>'
      + '<p class="npmf-foot">Source: <a href="' + esc(d.source_url) + '" target="_blank" rel="noopener">NHS Supply Chain, National Pricing Matrices</a> and each framework\'s public launch brief, read weekly. '
      + esc(d.notFetched || '') + '</p></div>';
    m.innerHTML = h;

    var list = m.querySelector('.npmf-list'), q = m.querySelector('input'), f = m.querySelector('select');
    function draw(){
      var term = (q.value || '').toLowerCase().trim(), mode = f.value;
      var shown = cats.filter(function(c){
        if (mode === 'matched' && !c.framework) return false;
        if (mode === 'unmatched' && c.framework) return false;
        if (!term) return true;
        var hay = (c.category + ' ' + (c.framework ? c.framework.name : '') + ' ' + ((c.brief || {}).statement || '')).toLowerCase();
        return hay.indexOf(term) >= 0;
      });
      list.innerHTML = shown.length ? shown.map(card).join('')
        : '<p class="npmf-none">No NPM category matches that search.</p>';
    }
    q.addEventListener('input', draw);
    f.addEventListener('change', draw);
    draw();
  }

  function mount(){
    var m = document.getElementById(MOUNT_ID);
    if (!m) return false;
    fetch(SRC + '?cb=' + new Date().toISOString().slice(0, 10))
      .then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function(d){ render(m, d); })
      .catch(function(){
        m.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:#0B1C33;background:#F5F1E8;padding:12px 14px;border-radius:8px;">'
          + 'The NPM Finder is temporarily unavailable. Please try again shortly.</div>';
      });
    return true;
  }

  if (!mount()) {
    var tries = 0;
    var t = setInterval(function(){ if (mount() || ++tries > 40) clearInterval(t); }, 120);
  }
})();
