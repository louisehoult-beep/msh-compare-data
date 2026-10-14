/* Medical Sales Hub — speciality news.
   Adds a small "Live feed" block of recent trade-press/journal items into a
   speciality page's News band, mounted on any element carrying
   data-speciality-news="<slug>".

   ADDITIVE ONLY, NEVER DESTRUCTIVE. Checked across all 23 tagged speciality
   pages on 15/09/2026: 22 of them already hold hand-written, individually
   sourced static <div class="news-item"> entries inside this exact mount
   element (2 to 8 each) — only Patient Moving and Handling's mount was
   genuinely empty. An earlier version of this file did `mount.innerHTML =
   ...`, which would have silently deleted every one of those verified items
   the moment this script ran. Never do that again: this file only ever
   INSERTS at the front of the mount (insertAdjacentHTML 'afterbegin') and
   never reads or clears what was already there. If there are zero live
   items, it inserts nothing at all — the page's own static content and its
   own empty-state note (if any) are left completely alone either way.

   EVERY ITEM CARRIES ITS SOURCE, and that is what discharges the Hub's
   verification standard (root rule 12/16) here: a reader can see whether a
   line came from Hub intelligence or from a named trade title, and judge it
   on that. The band label says what the block holds and how current it is,
   and does not repeat a blanket "not individually checked" caveat over the
   top of source lines that are already there (Lou, 16/09/2026).

   Follows the exact pattern proved live by app/speciality-panels.js
   (07/09/2026): a loader script on the WordPress page fetches this file from
   raw.githubusercontent.com and evals it; this file itself fetches its data
   JSON the same way. Nothing about the WordPress page's own giant HTML block
   needs touching again once the loader + mount attribute are in place.

   Data: data/speciality-news/<slug>.json, built by
   scripts/build_speciality_news.py in this repo. See that script's docstring
   and 02-Elevate-and-Thrive/Hub/speciality-page-news-pipeline-gap-2026-09-15.md
   for why this exists as a repo separate from cloud-pipeline. */
(function () {
  var PAGE_ITEMS = 6;
  // Lou, 14/10/2026: news "doesn't disappear but stays on the speciality
  // pages until out of date, maybe a month". The file already holds a rolling
  // month (build_speciality_news.py MAX_AGE_DAYS, 31); the page now shows all
  // of it: the first PAGE_ITEMS open, the rest behind "Show all". Anything
  // dated more than MAX_AGE_DAYS ago is dropped here too, so a stalled
  // refresh can never leave stale news on a page. Undated and future-dated
  // items (events) are kept, as the builder decides those.
  var MAX_AGE_DAYS = 31;
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/speciality-news/';
  var mounts = document.querySelectorAll('[data-speciality-news]');
  if (!mounts.length) { return; }

  function css() {
    if (document.getElementById('msh-news-live-css')) { return; }
    var st = document.createElement('style');
    st.id = 'msh-news-live-css';
    st.textContent = [
      '.msh .news-live-wrap{margin-bottom:10px;padding-bottom:10px;border-bottom:1px dashed var(--border);}',
      '.msh .news-live-lbl{font-size:10px;letter-spacing:1.2px;font-weight:800;text-transform:uppercase;',
      'color:var(--dim);margin-bottom:6px;}',
      '.msh .month-highlight .news-live-lbl{color:#9aa5b5;}',
      /* Gold on navy, the Hub's own accent — marks an item the pipeline flagged
         as a commercial opportunity, which is why it has been sorted to the top.
         Dark ink on gold, never gold on gold (see the fcal-ev-links incident). */
      '.msh .news-opp{display:inline-block;margin-right:6px;padding:1px 6px;border-radius:3px;',
      'background:#E0BE8E;color:#0B1C33;font-size:9px;font-weight:800;letter-spacing:1px;',
      'text-transform:uppercase;vertical-align:1px;}',
      '.msh .news-opp.news-job{background:#F3E4E1;color:#7A4A44;border:1px solid #e3c3bd;}',
      '.msh .news-more[hidden]{display:none;}',
      '.msh .news-more-btn{display:inline-block;margin-top:8px;padding:6px 12px;border:1px solid var(--border);',
      'border-radius:4px;background:transparent;color:inherit;font:inherit;font-size:12px;font-weight:700;cursor:pointer;}',
      '.msh .news-more-btn:hover,.msh .news-more-btn:focus-visible{border-color:#A8842C;}'
    ].join('');
    document.head.appendChild(st);
  }

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fmtDate(iso) {
    if (!iso) { return ''; }
    var d = new Date(iso);
    if (isNaN(d.getTime())) { return ''; }
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
  }

  // Lou, 24/09/2026: "Jobs need to show as jobs" and no summaries cut mid-word.
  // Same rules as app/my-hub.js; the builder now does both at source, these
  // cover a file written before it did.
  function isJob(it) { return it.kind === 'job' || /^\s*(job advert|vacancy)\b/i.test(String(it.title || '')); }
  function tidy(s) {
    s = String(s || '').replace(/\s*The post .{0,200}? appeared first on .*$/i, '').replace(/\s*(\[(…|\.\.\.)\]|\[\s*\]|…)\s*$/, '').trim();
    if (!s || /[.!?”"’')\]]$/.test(s)) { return s; }
    var dot = Math.max(s.lastIndexOf('. '), s.lastIndexOf('? '), s.lastIndexOf('! '));
    if (dot >= 80) { return s.slice(0, dot + 1); }
    var sp = s.lastIndexOf(' ');
    return (sp > 40 ? s.slice(0, sp) : s).replace(/[\s,;:–-]+$/, '') + '…';
  }

  function inDate(it) {
    if (!it.published) { return true; }
    var d = new Date(it.published);
    if (isNaN(d.getTime())) { return true; }
    return (Date.now() - d.getTime()) <= MAX_AGE_DAYS * 86400000;
  }

  function render(mount, doc) {
    // The whole rolling month, opportunities first as the file orders them.
    var items = ((doc && doc.items) || []).filter(inDate);
    if (!items.length) { return; }   // additive only — nothing to add, so add nothing
    css();
    var body = '';
    var more = '';
    var anyVerified = false;
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      if (it.verified) { anyVerified = true; }
      var html = '<div class="news-item">'
        + '<div class="news-date">' + esc(fmtDate(it.published)) + '</div>'
        + '<div>'
        + '<div class="news-t">'
        + (it.opportunity ? '<span class="news-opp">Opportunity</span>' : '')
        + (isJob(it) ? '<span class="news-opp news-job">Job</span>' : '')
        + '<a href="' + esc(it.link) + '" target="_blank" rel="noopener">' + esc(it.title) + '</a></div>'
        + (it.summary ? '<div class="news-b">' + esc(tidy(it.summary)) + '</div>' : '')
        + '<div class="news-src">' + esc(it.source) + '</div>'
        + '</div></div>';
      if (i < PAGE_ITEMS) { body += html; } else { more += html; }
    }
    if (more) {
      body += '<div class="news-more" hidden>' + more + '</div>'
        + '<button type="button" class="news-more-btn" aria-expanded="false">'
        + 'Show all ' + items.length + ' from the last month</button>';
    }
    // Lou, 16/09/2026: drop the "not individually checked" caveat — every item
    // already carries its source on its own line, which is what a reader needs
    // to judge it. The label says what the block holds and how current it is;
    // the per-item source line settles any individual case.
    var label = anyVerified
      ? 'Live feed — Hub intelligence and trade press, updated daily'
      : 'Live feed — trade press, updated daily';
    var wrapper = '<div class="news-live-wrap">'
      + '<div class="news-live-lbl">' + label + '</div>'
      + body + '</div>';
    mount.insertAdjacentHTML('afterbegin', wrapper);
    var btn = mount.querySelector('.news-live-wrap .news-more-btn');
    if (btn) {
      btn.addEventListener('click', function () {
        var box = mount.querySelector('.news-live-wrap .news-more');
        var open = box.hasAttribute('hidden');
        if (open) { box.removeAttribute('hidden'); } else { box.setAttribute('hidden', ''); }
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        btn.textContent = open ? 'Show fewer' : 'Show all ' + items.length + ' from the last month';
      });
    }
  }

  for (var m = 0; m < mounts.length; m++) {
    (function (mount) {
      var slug = mount.getAttribute('data-speciality-news');
      if (!slug) { return; }
      var cacheBust = new Date().toISOString().slice(0, 13);
      var url = BASE + slug + '.json?cb=' + cacheBust;
      fetch(url).then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.json();
      }).then(function (doc) {
        render(mount, doc);
      }).catch(function () {
        // Additive only: a failed fetch changes nothing on the page. No
        // error message is shown, because there is nothing missing from
        // the page's own content to explain — only a bonus block that
        // didn't arrive this time.
      });
    })(mounts[m]);
  }
})();
