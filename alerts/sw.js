/* Medical Sales Intelligence Hub — phone alerts service worker.

   Served from this repo by GitHub Pages at /msh-compare-data/alerts/sw.js and
   registered by alerts/index.html. It does exactly two things: show the
   notification a push carries, and open the page it points at when tapped.

   The payload is the JSON built by scripts/push_alerts.py build_message():
     { "title": "...", "body": "...", "url": "https://...", "tag": "msh-news-YYYYMMDD" }
   The tag means a second push on the same day REPLACES the first on the
   lock screen rather than stacking — one line per day, never a pile.

   No caching, no fetch handler, no offline anything: this worker exists for
   push and nothing else, so it can never serve a stale page. */
'use strict';

var HUB_HOME = 'https://medsalesintelligencehub.co.uk/medical-sales-hub/';
var ICON = 'icon-192.png';

self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });

self.addEventListener('push', function (event) {
  var data = {};
  try { data = event.data ? event.data.json() : {}; } catch (err) {
    data = { body: event.data ? event.data.text() : '' };
  }
  var title = data.title || 'Medical Sales Intelligence Hub';
  var options = {
    body: data.body || 'New items on the Hub.',
    icon: ICON,
    badge: ICON,
    tag: data.tag || 'msh-news',
    renotify: true,
    data: { url: data.url || HUB_HOME }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || HUB_HOME;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
      for (var i = 0; i < list.length; i++) {
        if (list[i].url === url && 'focus' in list[i]) { return list[i].focus(); }
      }
      return self.clients.openWindow(url);
    })
  );
});
