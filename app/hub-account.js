/* Hub account: a member's My Hub choices and state, on every Hub page.
   Talks to /wp-json/msh/v1/my-hub (WPCode snippet from
   hub/wpcode/my-hub-pins.php). Used by app/my-hub.js (the home screen) and
   app/hub-chrome.js (the Save star on every Hub page).

   WHERE THINGS ARE SAVED, in order (unchanged from My Hub, 23/09/2026):
     1. The member's Hub account, so it follows them across devices.
     2. This browser (localStorage), when the account cannot be reached. The
        next visit that reaches an account with nothing saved moves the
        browser copy into the account.

   The cleaning rules in normState()/cleanStar() are the same as the PHP
   snippet's msh_hub_state_clean()/msh_hub_star_clean(); the server is the
   authority, these keep the browser copy in the same shape.
   test_my_hub_state.py runs both on the same cases and compares.

   Loaded with new Function(); require()-able under node (only the pure
   functions are exercised there). */
(function (root) {
  'use strict';
  if (root.MSH_ACCOUNT && typeof module === 'undefined') { return; }

  var API = '/wp-json/msh/v1/my-hub';
  var LS_PINS = 'msh_my_hub_pins_v1';
  var LS_STATE = 'msh_hub_state_v1';
  var MAX_STARS = 200, MAX_SEEN = 300;
  var HOST = /^https:\/\/(www\.)?medsalesintelligencehub\.co\.uk(?=\/|$)/;

  /* ---------- pure: the same rules as the PHP snippet ---------- */
  function blank() {
    return { v: 1, wnSeen: [], tour: false, tourSeen: false, briefing: false, phone: false, scope: 'mine', stars: [] };
  }
  function starKey(u) {
    u = String(u === null || u === undefined ? '' : u).trim();
    var m = u.replace(HOST, '');
    if (m !== u) { if (m === '') { m = '/'; } }
    return m;
  }
  function cleanStar(s) {
    if (!s || typeof s !== 'object' || Array.isArray(s)) { return null; }
    var u = starKey(s.u);
    if (typeof s.u !== 'string' || typeof s.t !== 'string') { return null; }
    if (u.length > 500) { return null; }
    if (/^\/[\/\\]/.test(u)) { return null; }
    if (!/^(https:\/\/[^\s"<>]+|\/[^\s"<>]*)$/.test(u)) { return null; }
    var t = Array.from(s.t.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim()).slice(0, 200).join('');
    if (!t) { return null; }
    var at = typeof s.at === 'string' ? (/^\d{4}-\d{2}-\d{2}$/.test(s.at) ? s.at : '') : '';
    return { u: u, t: t, k: s.k === 'story' ? 'story' : 'page', at: at };
  }
  function normState(s) {
    var out = blank();
    if (!s || typeof s !== 'object' || Array.isArray(s)) { return out; }
    if (Array.isArray(s.wnSeen)) {
      var seen = [];
      s.wnSeen.slice(0, 2000).forEach(function (id) {
        if (typeof id === 'string') {
          if (/^[a-z0-9-]{1,64}$/.test(id)) { if (seen.indexOf(id) === -1) { seen.push(id); } }
        }
      });
      out.wnSeen = seen.slice(-MAX_SEEN);
    }
    ['tour', 'tourSeen', 'briefing', 'phone'].forEach(function (k) { out[k] = s[k] === true; });
    out.scope = s.scope === 'all' ? 'all' : 'mine';
    if (Array.isArray(s.stars)) {
      var have = {};
      for (var i = 0; i < Math.min(s.stars.length, 2000); i++) {
        var c = cleanStar(s.stars[i]);
        if (c) { if (!have[c.u]) { have[c.u] = 1; out.stars.push(c); } }
        if (out.stars.length >= MAX_STARS) { break; }
      }
    }
    return out;
  }
  function applyBody(old, body, today) {
    var st = normState(old);
    if (body.state && typeof body.state === 'object' && !Array.isArray(body.state)) {
      Object.keys(st).forEach(function (k) {
        if (k !== 'v') { if (Object.prototype.hasOwnProperty.call(body.state, k)) { st[k] = body.state[k]; } }
      });
      st = normState(st);
    }
    if (body.star && typeof body.star === 'object' && !Array.isArray(body.star)) {
      var c = cleanStar({ u: body.star.u, t: body.star.t, k: body.star.k, at: String(today) });
      if (c) { st.stars = [c].concat(st.stars.filter(function (x) { return x.u !== c.u; })).slice(0, MAX_STARS); }
    }
    if (typeof body.unstar === 'string') {
      var key = starKey(body.unstar);
      st.stars = st.stars.filter(function (x) { return x.u !== key; });
    }
    return st;
  }

  /* ---------- the account ---------- */
  function nonce() { return root.mshRestNonce || root.mshPrefsNonce || ''; }
  function lsGet(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function today() {
    var d = new Date();
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }
  function req(method, body) {
    var o = { method: method, credentials: 'same-origin', cache: 'no-store', headers: { 'X-WP-Nonce': nonce() } };
    if (body) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(body); }
    return fetch(API, o).then(function (r) { if (!r.ok) { throw new Error('my-hub ' + r.status); } return r.json(); });
  }

  var CUR = null, LOADING = null;
  /* Every POST goes through one chain: the server reads, changes and writes
     the whole record, so two at once would lose one, and responses arriving
     out of order must not roll the local copy back. PENDING counts queued
     writes; a response is adopted only when it answers the latest one. */
  var CHAIN = Promise.resolve(), PENDING = 0;
  function send(body, adopt) {
    PENDING++;
    var p = CHAIN.then(function () {
      return req('POST', body).then(function (d) {
        PENDING--;
        if (PENDING === 0) { adopt(d); }
        return true;
      }, function () { PENDING--; return false; });
    });
    CHAIN = p;
    return p;
  }
  function fromServer(d) {
    return { where: 'account', pins: Array.isArray(d.pins) ? d.pins : [], pinsSaved: !!d.saved, state: normState(d.state) };
  }
  function load() {
    if (CUR) { return Promise.resolve(CUR); }
    if (LOADING) { return LOADING; }
    var localState = lsGet(LS_STATE), localPins = lsGet(LS_PINS);
    if (!nonce()) {
      CUR = { where: 'none', pins: [], pinsSaved: false, state: normState(localState) };
      return Promise.resolve(CUR);
    }
    LOADING = req('GET').then(function (d) {
      CUR = fromServer(d);
      var push = {}, any = false;
      if (!d.stateSaved) { if (localState) { push.state = normState(localState); any = true; } }
      if (!CUR.pinsSaved) { if (Array.isArray(localPins)) { if (localPins.length) { push.pins = localPins; any = true; } } }
      if (!any) { return CUR; }
      return send(push, function (d2) { CUR = fromServer(d2); }).then(function () { return CUR; });
    }, function () {
      CUR = { where: 'browser', pins: Array.isArray(localPins) ? localPins : [], pinsSaved: false, state: normState(localState) };
      return CUR;
    });
    return LOADING;
  }
  /* Change the local copy at once, then tell the account. */
  function commit(body) {
    CUR.state = applyBody(CUR.state, body, today());
    lsSet(LS_STATE, CUR.state);
    if (CUR.where !== 'account') { return Promise.resolve(CUR); }
    return send(body, function (d) { CUR = fromServer(d); lsSet(LS_STATE, CUR.state); }).then(function (ok) {
      if (!ok) { CUR.where = 'browser'; }
      return CUR;
    });
  }
  function saveState(patch) { return load().then(function () { return commit({ state: patch }); }); }
  function star(item) { return load().then(function () { return commit({ star: { u: starKey(item.u), t: item.t, k: item.k } }); }); }
  function unstar(u) { return load().then(function () { return commit({ unstar: starKey(u) }); }); }
  function isStarred(u) {
    if (!CUR) { return false; }
    var k = starKey(u);
    return CUR.state.stars.some(function (x) { return x.u === k; });
  }
  function savePins(pins) {
    return load().then(function () {
      CUR.pins = pins.slice();
      lsSet(LS_PINS, CUR.pins);
      if (CUR.where !== 'account') { return CUR; }
      return send({ pins: CUR.pins }, function (d) { CUR = fromServer(d); }).then(function (ok) {
        if (!ok) { CUR.where = 'browser'; }
        return CUR;
      });
    });
  }

  var api = {
    load: load, saveState: saveState, star: star, unstar: unstar, isStarred: isStarred, savePins: savePins,
    _pure: { blank: blank, starKey: starKey, cleanStar: cleanStar, normState: normState, applyBody: applyBody }
  };
  if (typeof module === 'object') { if (module) { if (module.exports) { module.exports = api; } } }
  root.MSH_ACCOUNT = api;
})(typeof window !== 'undefined' ? window : globalThis);
