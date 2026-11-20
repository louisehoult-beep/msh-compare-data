/* Medical Sales Intelligence Hub — "Who's who: what we can name, and what you have to earn"
   Git-served, same pattern as mst-logic.js / comptab.js. Edit data/whos-who.html
   in this repo, never in wp-admin.

   Mounts into #msh-whoswho. Built 20/07/2026 from the Stakeholder Mapper's own
   role library (17 roles in app/mst-logic.js) plus the real-names research of the
   same date. Every availability verdict is traced to a primary source.
   20/11/2026: the library has 18 roles (17 + patient); counts corrected to 18.

   Why it exists: the mapper tells a rep which roles decide a purchase, but says
   nothing about whether those people can actually be identified. Across ODS, CQC,
   CIPS, the royal colleges, trust board papers and FOI, filtered over 20,000+
   named individuals: procurement 3, IPC 1, MDSO 1, Category Manager 0. The roles
   that decide device purchases are precisely the ones no register lists. */
(function(){
  var MOUNT_ID = 'msh-whoswho';
  var SRC = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/whos-who.html';


  /* Speciality view (20/11/2026, Hub Analysts live test: Niamh showed the same
     roles for every speciality, e.g. urology listed TVN and dietetics). When the
     mount carries data-speciality, or the page URL has ?spec=, only the roles the
     Stakeholder Mapper's own product templates use for that speciality are shown,
     read from data/products.json (P[].t / tp / x / xp through the same TPL as
     app/mst-logic.js). The rest are folded behind "Show all 18 roles", never
     deleted. No speciality, or one the mapper has no products for: unchanged. */
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/';
  var TPL = {dev:['payer','decision_maker','user','ebme'],con:['payer','decision_maker','user'],
    ipc:['payer','decision_maker','user','ipc'],micro:['payer','decision_maker','user','ipc','microbiology'],
    tv:['payer','decision_maker','user','tissue_viability'],proc:['payer','decision_maker','user','procurement'],
    rx:['payer','medicines','user'],cap:['payer','decision_maker','user','ebme','procurement'],
    mh:['manual_handling','tissue_viability','ipc','decision_maker','user','procurement','payer'],
    mhcap:['manual_handling','tissue_viability','ebme','decision_maker','user','procurement','payer']};
  // Hub speciality page slug -> the mapper's speciality ids (data/products.json SPECS).
  var HUB2MAP = {
    'audiology-and-hearing':['audiology'], 'cardiology-and-cardiac-surgery':['cardiology'],
    'colorectal-gi-and-endoscopy':['endoscopy','gastro','ostomy'], 'continence-bladder-and-bowel':['continence'],
    'critical-care':['anaesthesia','monitoring'], 'dermatology':['dermatology'],
    'diabetes-and-endocrinology':['diabetes'], 'digital-and-medical-it':['digital','it'],
    'emergency-and-urgent-care':['monitoring','anaesthesia'], 'ent-and-head-and-neck':['ent'],
    'frailty-and-older-people':['handling','continence','wound','rehab'],
    'gynaecology-and-womens-health':['womens'], 'haematology-and-patient-blood-management':['bloodtx','bloodcoll'],
    'infection-prevention-and-control':['infection','skin-prep'], 'interventional-radiology':['imaging','vascsurg'],
    'maternity-and-neonatal':['womens','neonatal'], 'neurology-and-neurosurgery':['neuro'],
    'nutrition-and-dietetics':['nutrition'], 'oncology-and-sact':['oncology'], 'ophthalmology':['ophthalmology'],
    'orthopaedics-and-trauma':['ortho'], 'paediatrics':['neonatal'],
    'pathology-and-laboratory-medicine':['pathology'], 'patient-handling':['handling'],
    'pharmacy-and-medicines':['pharma'], 'plastics-burns-and-reconstruction':['wound','closure'],
    'radiology-and-imaging':['imaging','ultrasound','nuclear'],
    'rehabilitation-prosthetics-and-orthotics':['rehab','orthotics'], 'renal':['renal'],
    'respiratory':['respiratory'], 'sepsis-and-the-deteriorating-patient':['monitoring','infection'],
    'sterile-services':['ssd'], 'stroke':['neuro'],
    'theatres-and-surgical':['theatres','surgical','mis','closure'],
    'tissue-viability-and-wound-care':['wound'], 'urology':['continence','endourology'],
    'vascular-access-and-iv-therapy':['vascular'], 'vascular-surgery-and-pad':['vascsurg']
  };
  function specSlug(m){
    var s = m.getAttribute('data-speciality') || '';
    if (!s) { try { s = new URLSearchParams(location.search).get('spec') || ''; } catch (e) {} }
    return String(s).toLowerCase().replace(/[^a-z-]/g, '');
  }
  function bySpeciality(m){
    var slug = specSlug(m);
    if (!slug) return;
    fetch(BASE + 'data/products.json?cb=' + new Date().toISOString().slice(0, 10))
      .then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function(d){
        var specs = d.SPECS || [], ids = HUB2MAP[slug] || [];
        if (!ids.length && specs.some(function(x){ return x.id === slug; })) ids = [slug];
        if (!ids.length) return;
        specs.forEach(function(x){ if (x.parent && ids.indexOf(x.parent) >= 0 && ids.indexOf(x.id) < 0) ids.push(x.id); });
        var used = {patient: 1}, nProd = 0;
        (d.P || []).forEach(function(p){
          if (ids.indexOf(p.s) < 0) return;
          nProd++;
          [].concat(TPL[p.t] || [], TPL[p.tp] || [], p.x || [], p.xp || []).forEach(function(k){ used[k] = 1; });
        });
        if (!nProd) return;
        var label = m.getAttribute('data-speciality-label')
          || (specs.filter(function(x){ return x.id === ids[0]; })[0] || {}).label || slug;
        apply(m, used, label, nProd, ids[0]);
      })
      .catch(function(){});
  }
  function apply(m, used, label, nProd, mapId){
    var cards = m.querySelectorAll('[data-roles]'), off = 0;
    var keys = Object.keys(used).filter(function(k){ return k !== 'patient'; });
    for (var i = 0; i < cards.length; i++) {
      var rs = cards[i].getAttribute('data-roles').split(' ');
      var hit = rs.indexOf('any') >= 0 || rs.some(function(r){ return used[r]; });
      if (!hit) { cards[i].classList.add('wwm__role--off'); off++; }
    }
    // Per-tier count for this speciality, and a note where a tier has none.
    var tiers = m.querySelectorAll('.wwm__card');
    for (var t = 0; t < tiers.length; t++) {
      var all = tiers[t].querySelectorAll('[data-roles]');
      if (!all.length) continue;
      var seen = {};
      for (var j = 0; j < all.length; j++) {
        if (all[j].classList.contains('wwm__role--off')) continue;
        all[j].getAttribute('data-roles').split(' ').forEach(function(r){ if (used[r]) seen[r] = 1; });
      }
      var n = Object.keys(seen).length;
      var cnt = tiers[t].querySelector('.wwm__count');
      if (cnt) cnt.insertAdjacentHTML('beforeend', '<span class="wwm__specn"> · ' + n + ' used in ' + esc(label) + '</span>');
    }
    var st = document.createElement('style');
    st.textContent = '.wwm .wwm__role--off{display:none}.wwm.wwm--all .wwm__role--off{display:block;opacity:.55}'
      + '.wwm__specbar{background:#f3ead2;border-left:3px solid #b8902f;border-radius:0 8px 8px 0;padding:12px 15px;margin:0 0 18px;font-size:14px;color:#11202f}'
      + '.wwm__specbar button{margin-left:8px;font:inherit;font-size:13px;font-weight:700;padding:4px 10px;border:1px solid #b8902f;border-radius:6px;background:#fff;color:#11202f;cursor:pointer}'
      + '.wwm__specn{color:#6b5a2a}';
    document.head.appendChild(st);
    var root = m.querySelector('.wwm'), lede = m.querySelector('.wwm__lede');
    if (!root || !lede) return;
    var bar = document.createElement('div');
    bar.className = 'wwm__specbar';
    bar.innerHTML = '<b>' + esc(label) + ':</b> the Stakeholder Mapper&rsquo;s ' + nProd + ' product template'
      + (nProd === 1 ? '' : 's') + ' for this speciality use <b>' + keys.length + ' of its 18 roles</b>, plus the patient. '
      + 'Those are shown below' + (off ? '; the other ' + off + ' role card' + (off === 1 ? ' is' : 's are') + ' folded away.' : '.')
      + (off ? ' <button type="button" aria-pressed="false">Show all 18 roles</button>' : '');
    lede.parentNode.insertBefore(bar, lede.nextSibling);
    var b = bar.querySelector('button');
    if (b) b.addEventListener('click', function(){
      var on = root.classList.toggle('wwm--all');
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.textContent = on ? 'Show ' + label + ' roles only' : 'Show all 18 roles';
    });
    // The Stakeholder Mapper accepts ?mapper=<id> (app/mst-logic.js, 20/11/2026):
    // carry the speciality on any mapper link on this page.
    var links = document.querySelectorAll('a[href*="#view-mapper"]');
    for (var k = 0; k < links.length; k++) {
      try {
        var u = new URL(links[k].href, location.href);
        u.searchParams.set('mapper', mapId);
        links[k].href = u.toString();
      } catch (e) {}
    }
  }
  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  function mount(){
    var m = document.getElementById(MOUNT_ID);
    if (!m) return false;
    // Cache-buster changes once a day, not on every page view — see
    // 17/08/2026 note in hub-search.js.
    fetch(SRC + '?cb=' + new Date().toISOString().slice(0, 10))
      .then(function(r){ if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(function(html){ m.innerHTML = html; try { bySpeciality(m); } catch (e) {} })
      .catch(function(){
        m.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:#8a6d00;'
          + 'padding:14px;">The who&rsquo;s-who name map is temporarily unavailable — '
          + 'please try again shortly.</div>';
      });
    return true;
  }

  // The ICB watch (app/icb-watch.js, 30/09/2026) rides on this loader: page 884
  // already fetches this file from git, so the ICB panel needs no wp-admin edit.
  // It places its own mount in section 2 and is a no-op on any other page.
  if (/nhs-structure-map/.test(location.pathname) || document.getElementById('msh-icbwatch')) {
    fetch('https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/app/icb-watch.js?cb='
          + new Date().toISOString().slice(0, 10))
      .then(function(r){ return r.text(); })
      .then(function(t){ (new Function(t))(); })
      .catch(function(){});
  }

  if (!mount()){
    // Mount point may not be parsed yet depending on block order.
    var tries = 0;
    var t = setInterval(function(){ if (mount() || ++tries > 40) clearInterval(t); }, 120);
  }
})();
