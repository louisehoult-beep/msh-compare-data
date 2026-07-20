/* NHS Intelligence Hub — "Who's who: what we can name, and what you have to earn"
   Git-served, same pattern as mst-logic.js / comptab.js. Edit data/whos-who.html
   in this repo, never in wp-admin.

   Mounts into #msh-whoswho. Built 20/07/2026 from the Stakeholder Mapper's own
   role library (17 roles in app/mst-logic.js) plus the real-names research of the
   same date. Every availability verdict is traced to a primary source.

   Why it exists: the mapper tells a rep which roles decide a purchase, but says
   nothing about whether those people can actually be identified. Across ODS, CQC,
   CIPS, the royal colleges, trust board papers and FOI, filtered over 20,000+
   named individuals: procurement 3, IPC 1, MDSO 1, Category Manager 0. The roles
   that decide device purchases are precisely the ones no register lists. */
(function(){
  var MOUNT_ID = 'msh-whoswho';
  var SRC = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/whos-who.html';

  function mount(){
    var m = document.getElementById(MOUNT_ID);
    if (!m) return false;
    fetch(SRC + '?cb=' + Date.now())
      .then(function(r){ if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(function(html){ m.innerHTML = html; })
      .catch(function(){
        m.innerHTML = '<div style="font-family:Inter,system-ui,sans-serif;color:#8a6d00;'
          + 'padding:14px;">The who&rsquo;s-who name map is temporarily unavailable — '
          + 'please try again shortly.</div>';
      });
    return true;
  }

  if (!mount()){
    // Mount point may not be parsed yet depending on block order.
    var tries = 0;
    var t = setInterval(function(){ if (mount() || ++tries > 40) clearInterval(t); }, 120);
  }
})();
