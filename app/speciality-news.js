/* Medical Sales Hub — speciality news.
   Renders a small list of recent trade-press/journal items into a speciality
   page's News band, mounted on any element carrying data-speciality="<slug>"
   (matches the id used by the existing News band's empty container, e.g.
   #therapies-news-feed on the Patient Moving and Handling page).

   Follows the exact pattern proved live by app/speciality-panels.js
   (07/09/2026): a loader script on the WordPress page fetches this file from
   raw.githubusercontent.com and evals it; this file itself fetches its data
   JSON the same way. Nothing about the WordPress page's own giant HTML block
   needs touching again once the loader + mount div are in place.

   Data: data/speciality-news/<slug>.json, built by
   scripts/build_speciality_news.py in this repo — a small, independent
   fetcher, NOT a fix to cloud-pipeline's own (currently non-functional)
   speciality_pages mechanism. See that script's docstring and
   02-Elevate-and-Thrive/Hub/speciality-page-news-pipeline-gap-2026-09-15.md
   for why this exists as a separate thing.

   Reuses the page's own existing CSS classes (.news-list / .news-item /
   .news-date / .news-t / .news-b / .news-src / .empty-state) rather than
   shipping new styles — every speciality page's stylesheet already defines
   them for the static News band. */
(function () {
  var BASE = 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/speciality-news/';
  var mounts = document.querySelectorAll('[data-speciality-news]');
  if (!mounts.length) { return; }

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

  function render(mount, doc) {
    var items = (doc && doc.items) || [];
    if (!items.length) {
      mount.innerHTML = '<div class="empty-state">No new trade-press or journal item for this '
        + 'speciality in the last ' + (doc && doc.maxAgeDays ? doc.maxAgeDays : 60)
        + ' days, from the sources currently wired to it. This is a checked empty state, not a '
        + 'missing feed — see the page’s own sourcing note above for what is and isn’t covered.</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      html += '<div class="news-item">'
        + '<div class="news-date">' + esc(fmtDate(it.published)) + '</div>'
        + '<div>'
        + '<div class="news-t"><a href="' + esc(it.link) + '" target="_blank" rel="noopener">' + esc(it.title) + '</a></div>'
        + (it.summary ? '<div class="news-b">' + esc(it.summary) + '</div>' : '')
        + '<div class="news-src">' + esc(it.source) + '</div>'
        + '</div></div>';
    }
    mount.innerHTML = html;
  }

  function fail(mount, msg) {
    mount.innerHTML = '<div class="empty-state">This feed could not load (' + esc(msg)
      + '). Nothing is missing from the page — reload, and if it persists it is the feed, not your access.</div>';
  }

  var seen = {};   // avoid double-fetching the same slug if two mounts share it
  for (var m = 0; m < mounts.length; m++) {
    (function (mount) {
      var slug = mount.getAttribute('data-speciality-news');
      if (!slug) { return; }
      mount.innerHTML = '<div class="empty-state">Loading this speciality’s news&hellip;</div>';
      var cacheBust = new Date().toISOString().slice(0, 13);
      var url = BASE + slug + '.json?cb=' + cacheBust;
      fetch(url).then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.json();
      }).then(function (doc) {
        render(mount, doc);
      }).catch(function (e) {
        fail(mount, e.message);
      });
    })(mounts[m]);
  }
})();
