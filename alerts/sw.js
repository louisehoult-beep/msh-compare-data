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
// A tap opens this page INSIDE the alerts app. It lists the items the push
// carried, read back from the cache below, so no Hub login is needed to see
// them (24/09/2026: opening the Hub from a tap landed on a login screen).
var LATEST = 'latest.html';
var STORE = 'msh-alerts';
var STORE_KEY = 'latest-alert.json';
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
    data: { url: new URL(data.url || LATEST, self.registration.scope).href }
  };
  // Show first (iOS requires every push to put a notification up), then log
  // that this phone received and showed it. Added 23/09/2026: Apple accepted
  // a test for Lou's iPhone but nothing appeared, and without this there was
  // no way to tell "never arrived" from "arrived, not shown" (Focus, settings).
  data.receivedAt = new Date().toISOString();
  event.waitUntil(
    keep(data).then(function () { return self.registration.showNotification(title, options); })
      .then(function () { return logEvent('received-shown', options.tag); },
            function (err) { return logEvent('received-show-failed', String(err && (err.message || err))); })
  );
});

// Save the alert so latest.html can show its items. Never blocks the notification.
function keep(data) {
  return caches.open(STORE).then(function (c) {
    return c.put(STORE_KEY, new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json' } }));
  }).catch(function () {});
}

// Best effort, never throws: one row in the Supabase push_events table, using
// the same public anon key the sign-up page uses (insert-only).
function logEvent(stage, detail) {
  return fetch('config.json', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (c) {
    if (!c.supabaseUrl || !c.supabaseAnonKey) { return; }
    return fetch(c.supabaseUrl + '/rest/v1/push_events', {
      method: 'POST',
      headers: { 'apikey': c.supabaseAnonKey, 'Authorization': 'Bearer ' + c.supabaseAnonKey,
                 'Content-Type': 'application/json', 'Prefer': 'return=minimal' },
      body: JSON.stringify({ stage: stage, detail: String(detail || '').slice(0, 300),
                             permission: (self.Notification && Notification.permission) || null,
                             user_agent: String(self.navigator && navigator.userAgent || '').slice(0, 200) })
    });
  }).catch(function () {});
}

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || new URL(LATEST, self.registration.scope).href;
  // openWindow first: it is what reliably brings the app forward on iPhone.
  // 24/09/2026: navigating an already-open app window instead did nothing at
  // all on Lou's iPhone when she tapped. If openWindow is refused, fall back
  // to focusing any open app window. Every tap is logged either way.
  event.waitUntil(
    self.clients.openWindow(url).then(function (w) {
      return logEvent(w ? 'tap-opened' : 'tap-opened-null', url);
    }).catch(function (err) {
      return self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
        var c = list.filter(function (x) { return x.url.indexOf(self.registration.scope) === 0; })[0];
        return (c ? c.focus() : null);
      }).then(function () {
        return logEvent('tap-open-failed', String(err && (err.message || err)));
      }, function (err2) {
        return logEvent('tap-open-failed', String(err && (err.message || err)) + ' / ' + String(err2));
      });
    })
  );
});
