// Live Desk app. One screen at a time, rendered into #app.
//
//   sign-in  ->  (no access) access screen: connect Hub membership, or subscribe
//            ->  (access)    Desk | Alerts | Account
//
// Server: the Supabase Edge Function "livedesk" (supabase/functions/livedesk).
// Hub members connect by opening the Hub's "Live Desk app" page, which hands a
// member pass back through LINK_SCHEME (docs/hub-page-livedesk-app-link.html).
// Store rules (App Store 3.1.1 and 3.1.3(b), UK storefront): the app never
// links to, names or prices any way to buy outside the app. A Hub member just
// connects; everyone else subscribes in the app.

import { createClient } from '@supabase/supabase-js';
import { App } from '@capacitor/app';
import { Browser } from '@capacitor/browser';
import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';
import { SplashScreen } from '@capacitor/splash-screen';
import { StatusBar, Style } from '@capacitor/status-bar';
import { FirebaseMessaging } from '@capacitor-firebase/messaging';
import { Purchases } from '@revenuecat/purchases-capacitor';
import { CONFIG } from './config.js';
import {
  filterFeed, itemsFromNotification, newCount, passFromLink, safeUrl, shortDate, stamp,
} from './logic.js';

const NATIVE = Capacitor.isNativePlatform();
const PLATFORM = Capacitor.getPlatform(); // 'ios' | 'android' | 'web'
const $app = document.getElementById('app');

// ---------------------------------------------------------------- storage
const store = {
  async get(k) { return (await Preferences.get({ key: k })).value; },
  async set(k, v) { await Preferences.set({ key: k, value: v }); },
  async del(k) { await Preferences.remove({ key: k }); },
  async getJSON(k, d) { try { return JSON.parse(await this.get(k)) ?? d; } catch { return d; } },
  async setJSON(k, v) { await this.set(k, JSON.stringify(v)); },
};

const sb = createClient(CONFIG.supabaseUrl, CONFIG.supabaseAnonKey, {
  auth: {
    storage: { getItem: (k) => store.get(k), setItem: (k, v) => store.set(k, v), removeItem: (k) => store.del(k) },
    persistSession: true, autoRefreshToken: true, detectSessionInUrl: false,
  },
});

// ---------------------------------------------------------------- state
const S = {
  user: null,
  status: null,       // from the server: {access, via, relink, hub_until, store_until}
  feed: null,
  feedFrom: null,     // 'live' | 'cache'
  tab: 'desk',
  chosen: [],         // speciality slugs for the Desk filter and alerts
  mine: false,        // Desk filter on?
  alertsOn: false,
  lastAlert: null,    // {at, items}
  busy: '',
  packages: null,
  note: '',
};

// ---------------------------------------------------------------- helpers
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const label = (slug) => (CONFIG.specialities.find((s) => s.slug === slug) || {}).label || slug;

async function api(action, extra = {}) {
  const { data } = await sb.auth.getSession();
  const token = data.session && data.session.access_token;
  if (!token) return { status: 401, body: { ok: false, why: 'login' } };
  try {
    const r = await fetch(CONFIG.supabaseUrl + '/functions/v1/livedesk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', apikey: CONFIG.supabaseAnonKey, Authorization: 'Bearer ' + token },
      body: JSON.stringify({ action, ...extra }),
    });
    return { status: r.status, body: await r.json().catch(() => ({})) };
  } catch {
    return { status: 0, body: { ok: false, why: 'offline' } };
  }
}

function open(url) {
  const u = safeUrl(url);
  if (u) Browser.open({ url: u, presentationStyle: 'popover' });
}

function setBusy(msg) { S.busy = msg; render(); }

// ---------------------------------------------------------------- flows
async function loadStatus() {
  const r = await api('status');
  if (r.status === 200) { S.status = r.body; await store.setJSON('status', r.body); }
  else if (r.status === 0) S.status = await store.getJSON('status', null);
  return S.status;
}

async function loadFeed() {
  const r = await api('feed');
  if (r.status === 200 && r.body.feed) {
    S.feed = r.body.feed; S.feedFrom = 'live';
    await store.setJSON('feed', S.feed);
  } else if (r.status === 402) {
    S.status = { ...(S.status || {}), ...r.body, access: false };
  } else {
    S.feed = await store.getJSON('feed', null); S.feedFrom = S.feed ? 'cache' : null;
  }
}

async function afterSignIn(user) {
  S.user = user;
  if (NATIVE && CONFIG.revenueCatKey[PLATFORM]) {
    try { await Purchases.logIn({ appUserID: user.id }); } catch { /* offline: retried next launch */ }
  }
  await loadStatus();
  if (S.status && S.status.access) await loadFeed();
  else await loadOfferings();
  render();
  if (S.alertsOn) registerDevice();
}

const PERIOD = { MONTHLY: 'month', ANNUAL: 'year', WEEKLY: 'week', SIX_MONTH: '6 months', THREE_MONTH: '3 months' };

async function loadOfferings() {
  if (!NATIVE || !CONFIG.revenueCatKey[PLATFORM]) return;
  try {
    const o = await Purchases.getOfferings();
    S.packages = (o.current?.availablePackages || []).map((p) => ({
      id: p.identifier,
      title: p.product.title || (PERIOD[p.packageType] === 'year' ? 'Annual' : 'Monthly'),
      price: p.product.priceString,
      period: PERIOD[p.packageType] || '',
    }));
  } catch { S.packages = []; }
}

async function sendCode(email) {
  setBusy('Sending your code...');
  const { error } = await sb.auth.signInWithOtp({ email, options: { shouldCreateUser: true } });
  S.busy = '';
  if (error) { S.note = 'That did not work. Check the email address and try again.'; render(); return false; }
  S.note = '';
  return true;
}

async function verifyCode(email, code) {
  setBusy('Checking...');
  const { data, error } = await sb.auth.verifyOtp({ email, token: code, type: 'email' });
  S.busy = '';
  if (error || !data.user) { S.note = 'That code did not match, or it has expired. Try again.'; render(); return; }
  S.note = '';
  await afterSignIn(data.user);
}

async function connectHub() {
  await Browser.open({ url: CONFIG.hubLinkUrl, presentationStyle: 'popover' });
}

async function linkWithPass(pass) {
  try { await Browser.close(); } catch { /* already closed */ }
  setBusy('Connecting your Hub membership...');
  const r = await api('link', { pass });
  S.busy = '';
  if (r.status === 200) {
    S.status = r.body; S.note = '';
    await loadFeed(); S.tab = 'desk';
  } else {
    S.note = r.body.why === 'pass'
      ? 'The Hub did not confirm a membership that includes the Live Desk. If you think it should, contact us from the Account tab.'
      : 'Could not connect just now. Check your connection and try again.';
  }
  render();
}

async function subscribe(pkgId) {
  setBusy('Opening the store...');
  try {
    const offerings = await Purchases.getOfferings();
    const pkg = (offerings.current?.availablePackages || []).find((p) => p.identifier === pkgId);
    if (!pkg) throw new Error('package');
    await Purchases.purchasePackage({ aPackage: pkg });
    await waitForAccess();
  } catch (e) {
    S.busy = '';
    if (!(e && (e.userCancelled || e.code === '1'))) S.note = 'The purchase did not complete. You have not been charged.';
    render();
  }
}

async function restore() {
  setBusy('Restoring purchases...');
  try { await Purchases.restorePurchases(); await waitForAccess(); }
  catch { S.busy = ''; S.note = 'Nothing to restore on this store account.'; render(); }
}

// The store tells our server through RevenueCat's webhook, usually within seconds.
async function waitForAccess() {
  for (let i = 0; i < 10; i++) {
    await loadStatus();
    if (S.status && S.status.access) { await loadFeed(); S.busy = ''; S.tab = 'desk'; render(); return; }
    await new Promise((res) => setTimeout(res, 2000));
  }
  S.busy = '';
  S.note = 'Your purchase went through. Access can take a minute to arrive: tap Check again.';
  render();
}

async function registerDevice() {
  if (!NATIVE) return;
  try {
    const perm = await FirebaseMessaging.requestPermissions();
    if (perm.receive !== 'granted') {
      S.alertsOn = false; await store.set('alertsOn', '0');
      S.note = 'Alerts are switched off for this app in your phone settings.'; render(); return;
    }
    const { token } = await FirebaseMessaging.getToken();
    await store.set('pushToken', token);
    await api('device', { token, platform: PLATFORM, specialities: S.chosen });
  } catch { /* retried on next launch */ }
}

async function alertsOff() {
  const token = await store.get('pushToken');
  if (token) await api('device-off', { token });
}

async function signOut() {
  if (S.alertsOn) await alertsOff();
  try { if (NATIVE && CONFIG.revenueCatKey[PLATFORM]) await Purchases.logOut(); } catch { /* anonymous already */ }
  await sb.auth.signOut();
  await store.del('feed'); await store.del('status');
  Object.assign(S, { user: null, status: null, feed: null, tab: 'desk', note: '' });
  render();
}

async function deleteAccount() {
  setBusy('Deleting your account...');
  const r = await api('delete-account');
  if (r.status === 200) {
    S.busy = '';
    await signOut();
    S.note = 'Your account and everything stored with it has been deleted. Any store subscription is managed in your store account settings.';
    render();
  } else {
    S.busy = ''; S.note = 'Could not delete just now. Check your connection and try again.'; render();
  }
}

// ---------------------------------------------------------------- views
function header(sub) {
  return `<header class="top"><div class="brand">LIVE <span>DESK</span></div>${sub ? `<div class="sub">${sub}</div>` : ''}</header>`;
}

function viewSignIn() {
  const sent = !!S.pendingEmail;
  return `${header('UK medtech and NHS market intelligence, live')}
  <main class="pad">
    <h1>${sent ? 'Enter your code' : 'Sign in'}</h1>
    <p class="lead">${sent ? `We sent a 6-digit code to <b>${esc(S.pendingEmail)}</b>.` : 'Enter your email and we will send you a sign-in code. No password needed.'}</p>
    ${sent
      ? `<input id="code" inputmode="numeric" autocomplete="one-time-code" maxlength="8" placeholder="Code">
         <button id="verify" class="btn">Sign in</button>
         <button id="back" class="link">Use a different email</button>`
      : S.withPassword
        ? `<input id="email" type="email" autocomplete="email" placeholder="you@company.com">
           <input id="password" type="password" autocomplete="current-password" placeholder="Password">
           <button id="pwsignin" class="btn">Sign in</button>
           <button id="usecode" class="link">Sign in with an email code instead</button>`
        : `<input id="email" type="email" autocomplete="email" placeholder="you@company.com">
           <button id="send" class="btn">Send my code</button>
           <button id="usepw" class="link">I have a password</button>`}
    ${S.note ? `<p class="note">${esc(S.note)}</p>` : ''}
    <p class="small">By signing in you agree to the <a data-open="${CONFIG.termsUrl}">terms</a> and <a data-open="${CONFIG.privacyUrl}">privacy policy</a>.</p>
  </main>`;
}

function viewAccess() {
  const relink = S.status && S.status.relink;
  // Prices come from the store itself (App Store rule 3.1.2: show the real price and period).
  const plans = (S.packages || []).map((p) => `<button class="plan" data-plan="${esc(p.id)}"><b>${esc(p.title)}</b><span>${esc(p.price)}${p.period ? ' per ' + esc(p.period) : ''}</span></button>`).join('')
    || '<p class="small">Subscription options could not be loaded. Check your connection and reopen the app.</p>';
  return `${header()}
  <main class="pad">
    <h1>${relink ? 'Reconnect your Hub membership' : 'Get the Live Desk'}</h1>
    <section class="card">
      <h2>Hub member?</h2>
      <p>${relink ? 'Your Hub connection needs a quick monthly check.' : 'The Live Desk app is included in Hub membership.'} Connect once and you are in.</p>
      <button id="hub" class="btn">${relink ? 'Reconnect' : 'Connect my Hub membership'}</button>
    </section>
    ${CONFIG.revenueCatKey[PLATFORM] ? `<section class="card">
      <h2>Subscribe</h2>
      <p>Every Live Desk panel, updated hourly, with alerts for your specialities.</p>
      ${plans}
      <p class="small">Payment is charged to your ${PLATFORM === 'ios' ? 'Apple ID' : 'Google Play'} account. The subscription renews automatically unless cancelled at least 24 hours before the end of the current period. Manage or cancel in your ${PLATFORM === 'ios' ? 'App Store' : 'Google Play'} account settings.</p>
      <button id="restore" class="link">Restore purchases</button>
      <button id="check" class="link">Check again</button>
    </section>` : ''}
    ${S.note ? `<p class="note">${esc(S.note)}</p>` : ''}
    <p class="small"><a data-open="${CONFIG.termsUrl}">Terms of use</a> · <a data-open="${CONFIG.privacyUrl}">Privacy policy</a> · <button id="signout" class="link inline">Sign out</button></p>
  </main>`;
}

function rowHtml(r) {
  if (r.kind === 'note') return `<li class="note-row">${esc(r.title)}</li>`;
  const members = r.kind === 'story' && r.members && r.members.length
    ? `<div class="members">${r.members.map((m, i) => `<a data-open="${esc(m.url)}">${i + 1}. ${esc(m.title || 'Notice')}</a>`).join('')}</div>` : '';
  return `<li class="${r.new ? 'is-new' : ''}${r.lead ? ' is-lead' : ''}">
    <div class="meta">${r.lead ? '<span class="chip lead">TOP STORY</span>' : ''}${r.new ? '<span class="chip new">NEW</span>' : ''}<span class="d">${esc(shortDate(r.date))}</span></div>
    <a class="t" data-open="${esc(r.url)}">${esc(r.title)}</a>
    ${r.badge ? `<div class="badge">${esc(r.badge)}</div>` : ''}
    ${r.use ? `<div class="use">Use it: ${esc(r.use)}</div>` : ''}
    ${members}
  </li>`;
}

function viewDesk() {
  if (!S.feed) {
    return `<main class="pad"><p class="lead">${S.feedFrom === null ? 'No connection, and nothing saved on this phone yet. Try again when you are online.' : 'Loading the Live Desk...'}</p><button id="refresh" class="btn">Try again</button></main>`;
  }
  const panels = filterFeed(S.feed, S.mine ? S.chosen : []);
  const ticker = (S.feed.ticker || []).map((t) => `<a class="tick" data-open="${esc(t.url)}"><span class="tag">${esc(t.tag)}</span>${t.badge ? `<b>${esc(t.badge)}</b> ` : ''}${esc(t.title)}</a>`).join('');
  const body = panels.length ? panels.map((p) => `<section class="panel"><h2>${esc(p.title)}</h2><ul>${p.rows.map(rowHtml).join('')}</ul></section>`).join('')
    : '<p class="lead">Nothing in your specialities on the desk right now. Switch to All to see everything.</p>';
  return `<div class="asof">${S.feedFrom === 'cache' ? 'Offline: last update ' : 'Updated '}${esc(stamp(S.feed.as_of))} <button id="refresh" class="link inline">Refresh</button></div>
    ${ticker ? `<div class="ticker">${ticker}</div>` : ''}
    <div class="filter">
      <button class="seg ${S.mine ? '' : 'on'}" data-mine="0">All</button>
      <button class="seg ${S.mine ? 'on' : ''}" data-mine="1">My specialities${S.chosen.length ? ` (${S.chosen.length})` : ''}</button>
      <span class="count">${newCount(panels)} new</span>
    </div>
    ${S.mine && !S.chosen.length ? '<p class="pad small">Pick your specialities in the Alerts tab.</p>' : ''}
    <main>${body}</main>`;
}

function viewAlerts() {
  const items = (S.lastAlert && S.lastAlert.items) || [];
  const boxes = CONFIG.specialities.map((s) => `<label class="spec"><input type="checkbox" value="${esc(s.slug)}" ${S.chosen.includes(s.slug) ? 'checked' : ''}> ${esc(s.label)}</label>`).join('');
  return `<main class="pad">
    <h1>Alerts</h1>
    <p class="lead">At 9am, 12 noon and 4pm, only when something new lands in your specialities.</p>
    <label class="toggle"><input id="alerts" type="checkbox" ${S.alertsOn ? 'checked' : ''}> Alerts on</label>
    ${items.length ? `<section class="card"><h2>Latest alert</h2><ul class="plain">${items.map((i) => `<li><a data-open="${esc(i.u)}">${esc(i.t)}</a>${i.sp ? `<span class="small"> ${esc(i.sp)}</span>` : ''}</li>`).join('')}</ul></section>` : ''}
    <h2>Your specialities</h2>
    <p class="small">None ticked means every speciality.</p>
    <div class="specs">${boxes}</div>
    ${S.note ? `<p class="note">${esc(S.note)}</p>` : ''}
  </main>`;
}

function viewAccount() {
  const st = S.status || {};
  const via = st.via === 'hub' ? `Hub membership, checked until ${esc(shortDate(st.hub_until))}`
    : st.via === 'store' ? `Subscription, renews or ends ${esc(shortDate(st.store_until))}` : 'No access';
  return `<main class="pad">
    <h1>Account</h1>
    <section class="card"><p><b>${esc(S.user && S.user.email)}</b></p><p>${via}</p></section>
    ${st.via === 'store' ? `<button id="manage" class="btn ghost">Manage subscription</button>` : ''}
    <button id="hub" class="btn ghost">${st.via === 'hub' ? 'Re-check Hub membership' : 'Connect Hub membership'}</button>
    ${CONFIG.revenueCatKey[PLATFORM] ? '<button id="restore" class="btn ghost">Restore purchases</button>' : ''}
    <p class="small"><a data-open="${CONFIG.supportUrl}">Help and contact</a> · <a data-open="${CONFIG.privacyUrl}">Privacy policy</a> · <a data-open="${CONFIG.termsUrl}">Terms</a></p>
    <button id="signout" class="btn ghost">Sign out</button>
    <button id="delete" class="link danger">Delete my account</button>
    ${S.note ? `<p class="note">${esc(S.note)}</p>` : ''}
    <p class="small">Version ${esc(CONFIG.version)}</p>
  </main>`;
}

function tabs() {
  const t = (k, l) => `<button class="tab ${S.tab === k ? 'on' : ''}" data-tab="${k}">${l}</button>`;
  return `<nav class="tabs">${t('desk', 'Desk')}${t('alerts', 'Alerts')}${t('account', 'Account')}</nav>`;
}

function render() {
  let html;
  if (S.busy) html = `${header()}<main class="pad center"><div class="spinner"></div><p>${esc(S.busy)}</p></main>`;
  else if (!S.user) html = viewSignIn();
  else if (!S.status || !S.status.access) html = viewAccess();
  else html = header() + ({ desk: viewDesk, alerts: viewAlerts, account: viewAccount }[S.tab])() + tabs();
  $app.innerHTML = html;
}

// ---------------------------------------------------------------- events
$app.addEventListener('click', async (e) => {
  const el = e.target.closest('button, a, [data-open]');
  if (!el) return;
  if (el.dataset.open !== undefined) { e.preventDefault(); open(el.dataset.open); return; }
  if (el.dataset.tab) { S.tab = el.dataset.tab; S.note = ''; render(); window.scrollTo(0, 0); return; }
  if (el.dataset.mine !== undefined) { S.mine = el.dataset.mine === '1'; await store.set('mine', S.mine ? '1' : '0'); render(); return; }
  if (el.dataset.plan) { subscribe(el.dataset.plan); return; }
  switch (el.id) {
    case 'send': {
      const email = (document.getElementById('email').value || '').trim().toLowerCase();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { S.note = 'Enter a valid email address.'; render(); return; }
      if (await sendCode(email)) { S.pendingEmail = email; render(); }
      return;
    }
    case 'verify': {
      const code = (document.getElementById('code').value || '').replace(/\D/g, '');
      if (code.length < 6) { S.note = 'Enter the code from the email.'; render(); return; }
      verifyCode(S.pendingEmail, code); return;
    }
    case 'back': S.pendingEmail = ''; S.note = ''; render(); return;
    // Password sign-in exists for accounts given a password in Supabase, such
    // as the App Review demo account (README). Everyone else uses a code.
    case 'usepw': S.withPassword = true; S.note = ''; render(); return;
    case 'usecode': S.withPassword = false; S.note = ''; render(); return;
    case 'pwsignin': {
      const email = (document.getElementById('email').value || '').trim().toLowerCase();
      const password = document.getElementById('password').value || '';
      setBusy('Signing in...');
      const { data, error } = await sb.auth.signInWithPassword({ email, password });
      S.busy = '';
      if (error || !data.user) { S.note = 'That email and password did not match.'; render(); return; }
      S.note = ''; await afterSignIn(data.user); return;
    }
    case 'hub': connectHub(); return;
    case 'restore': restore(); return;
    case 'check': setBusy('Checking...'); await waitForAccess(); return;
    case 'refresh': setBusy('Refreshing...'); await loadFeed(); S.busy = ''; render(); return;
    case 'manage': open(PLATFORM === 'ios' ? 'https://apps.apple.com/account/subscriptions' : 'https://play.google.com/store/account/subscriptions'); return;
    case 'signout': signOut(); return;
    case 'delete':
      if (window.confirm('Delete your Live Desk account and everything stored with it? This cannot be undone. A store subscription must be cancelled separately in your store account.')) deleteAccount();
      return;
    default:
  }
});

$app.addEventListener('change', async (e) => {
  if (e.target.id === 'alerts') {
    S.alertsOn = e.target.checked; await store.set('alertsOn', S.alertsOn ? '1' : '0');
    if (S.alertsOn) await registerDevice(); else await alertsOff();
    render(); return;
  }
  if (e.target.closest('.specs')) {
    S.chosen = [...document.querySelectorAll('.specs input:checked')].map((i) => i.value);
    await store.setJSON('chosen', S.chosen);
    if (S.alertsOn) registerDevice();
  }
});

// ---------------------------------------------------------------- start
async function start() {
  if (NATIVE) {
    try { await StatusBar.setStyle({ style: Style.Dark }); } catch { /* not all devices */ }
    App.addListener('appUrlOpen', ({ url }) => { const p = passFromLink(url); if (p) linkWithPass(p); });
    App.addListener('resume', async () => { if (S.user && S.status && S.status.access && S.tab === 'desk') { await loadFeed(); render(); } });
    if (CONFIG.revenueCatKey[PLATFORM]) {
      try { await Purchases.configure({ apiKey: CONFIG.revenueCatKey[PLATFORM] }); } catch { /* shown as no plans */ }
    }
    FirebaseMessaging.addListener('tokenReceived', async ({ token }) => {
      await store.set('pushToken', token);
      if (S.user && S.alertsOn) api('device', { token, platform: PLATFORM, specialities: S.chosen });
    });
    const keep = async (n) => {
      const items = itemsFromNotification(n && n.data);
      if (items.length) { S.lastAlert = { at: Date.now(), items }; await store.setJSON('lastAlert', S.lastAlert); }
    };
    FirebaseMessaging.addListener('notificationReceived', ({ notification }) => keep(notification));
    FirebaseMessaging.addListener('notificationActionPerformed', async ({ notification }) => {
      await keep(notification); S.tab = 'alerts'; render();
    });
    if (PLATFORM === 'android') {
      try { await FirebaseMessaging.createChannel({ id: 'alerts', name: 'Live Desk alerts', importance: 4 }); } catch { /* exists */ }
    }
  }
  S.chosen = await store.getJSON('chosen', []);
  S.mine = (await store.get('mine')) === '1';
  S.alertsOn = (await store.get('alertsOn')) === '1';
  S.lastAlert = await store.getJSON('lastAlert', null);
  S.feed = await store.getJSON('feed', null); S.feedFrom = S.feed ? 'cache' : null;

  const { data } = await sb.auth.getSession();
  if (data.session && data.session.user) await afterSignIn(data.session.user);
  else render();
  if (NATIVE) SplashScreen.hide();
}

start();
