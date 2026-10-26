import test from 'node:test';
import assert from 'node:assert/strict';
import { openDb } from './db.js';
import { seed } from './seed.js';
import { createApp } from './app.js';

async function boot() {
  const db = openDb(':memory:');
  seed(db);
  db.prepare("INSERT INTO members (email,name,nmc_pin,role_category,employer_type,status,consent_at) VALUES ('rev@example.com','Reviewer','00A0000A','Other','Other','approved',datetime('now'))").run();
  const server = createApp(db, { adminEmails: ['admin@example.com'], devLinks: true, reviewer: { email: 'rev@example.com', code: '424242' } }).listen(0); server.unref();
  const base = `http://localhost:${server.address().port}`;
  const client = () => {
    let cookie = '';
    const call = async (method, path, body) => {
      const r = await fetch(base + path, { method, headers: { 'content-type': 'application/json', cookie }, body: body ? JSON.stringify(body) : undefined });
      const sc = r.headers.get('set-cookie');
      if (sc) cookie = sc.split(';')[0];
      const ct = r.headers.get('content-type') || '';
      return { status: r.status, body: ct.includes('json') ? await r.json() : await r.text() };
    };
    return call;
  };
  return { db, server, client };
}
const signup = (email, extra = {}) => ({ email, name: 'Test Nurse', nmc_pin: '12A3456E', role_category: 'Clinical educator', employer_type: 'Medical device company', consent: true, ...extra });
async function join(call, email, extra) {
  const r = await call('POST', '/api/auth/signup', signup(email, extra));
  assert.equal(r.status, 200, JSON.stringify(r.body));
  const token = r.body.devLink.split('/verify/')[1];
  assert.equal((await call('POST', '/api/auth/verify', { token })).status, 200);
}

test('signup validates PIN and consent', async () => {
  const { server, client } = await boot();
  const call = client();
  assert.equal((await call('POST', '/api/auth/signup', signup('a@example.com', { nmc_pin: 'bad' }))).status, 400);
  assert.equal((await call('POST', '/api/auth/signup', signup('a@example.com', { consent: false }))).status, 400);
  server.close();
});

test('pending members are gated, approved members are not', async () => {
  const { server, client } = await boot();
  const admin = client(), nurse = client();
  await join(admin, 'admin@example.com');
  await join(nurse, 'nurse@example.com');
  assert.equal((await nurse('GET', '/api/channels')).status, 403);
  assert.equal((await nurse('GET', '/api/jobs')).status, 403);
  const pending = (await admin('GET', '/api/admin/pending')).body;
  assert.equal(pending.length, 1);
  assert.equal((await nurse('GET', '/api/admin/pending')).status, 403);
  await admin('POST', `/api/admin/members/${pending[0].id}/decision`, { decision: 'approve' });
  assert.equal((await nurse('GET', '/api/channels')).status, 200);
  server.close();
});

test('login token is single use and unknown emails look the same', async () => {
  const { server, client } = await boot();
  const call = client();
  const r = await call('POST', '/api/auth/signup', signup('x@example.com'));
  const token = r.body.devLink.split('/verify/')[1];
  assert.equal((await call('POST', '/api/auth/verify', { token })).status, 200);
  assert.equal((await client()('POST', '/api/auth/verify', { token })).status, 400);
  const unknown = await call('POST', '/api/auth/request', { email: 'nobody@example.com' });
  assert.deepEqual(unknown.body, { ok: true });
  server.close();
});

test('community: post, reply, notify, report, hide', async () => {
  const { server, client, db } = await boot();
  const admin = client(), a = client(), b = client();
  await join(admin, 'admin@example.com');
  await join(a, 'a@example.com');
  await join(b, 'b@example.com');
  for (const m of db.prepare("SELECT id FROM members WHERE is_admin = 0").all()) db.prepare("UPDATE members SET status='approved' WHERE id=?").run(m.id);
  const t = await a('POST', '/api/channels/moving-into-industry/posts', { body: 'How did you move across?' });
  assert.equal(t.status, 200);
  await b('POST', '/api/channels/moving-into-industry/posts', { body: 'Start with NAMDET.', parent_id: t.body.id });
  assert.equal((await a('GET', '/api/me')).body.unread, 1);
  const thread = (await a('GET', '/api/channels/moving-into-industry/posts')).body.threads[0];
  assert.equal(thread.replies.length, 1);
  assert.equal((await a('POST', `/api/posts/${t.body.id}/report`, { reason: 'test' })).status, 200);
  const reports = (await admin('GET', '/api/admin/reports')).body;
  assert.equal(reports.length, 1);
  await admin('POST', `/api/admin/reports/${reports[0].id}/resolve`, { hide: true });
  assert.equal((await a('GET', '/api/channels/moving-into-industry/posts')).body.threads.length, 0);
  server.close();
});

test('directory only shows members who opted in', async () => {
  const { server, client, db } = await boot();
  const a = client(), b = client();
  await join(a, 'a@example.com');
  await join(b, 'b@example.com', { name: 'Hidden Person' });
  db.prepare("UPDATE members SET status='approved'").run();
  assert.equal((await a('GET', '/api/directory')).body.length, 0);
  await b('PATCH', '/api/me', { directory_visible: true });
  const dir = (await a('GET', '/api/directory')).body;
  assert.equal(dir.length, 1);
  assert.equal(dir[0].email, undefined);
  assert.equal(dir[0].nmc_pin, undefined);
  server.close();
});

test('undated events have no calendar file; dated ones do', async () => {
  const { server, client, db } = await boot();
  const call = client();
  const events = (await call('GET', '/api/events')).body;
  const undated = events.find((e) => !e.start_date), dated = events.find((e) => e.start_date);
  assert.equal((await call('GET', `/api/events/${undated.id}.ics`)).status, 404);
  const ics = await call('GET', `/api/events/${dated.id}.ics`);
  assert.equal(ics.status, 200);
  assert.match(ics.body, /BEGIN:VEVENT/);
  assert.ok(db);
  server.close();
});

test('member can delete their account', async () => {
  const { server, client, db } = await boot();
  const a = client();
  await join(a, 'a@example.com');
  assert.equal((await a('DELETE', '/api/me')).status, 200);
  assert.equal(db.prepare('SELECT COUNT(*) c FROM members WHERE email = ?').get('a@example.com').c, 0);
  server.close();
});

test('phone app signs in with email plus code and a bearer token', async () => {
  const { server, client } = await boot();
  const web = client();
  const r = await web('POST', '/api/auth/signup', signup('p@example.com'));
  const phone = client();
  assert.equal((await phone('POST', '/api/auth/verify', { email: 'p@example.com', code: '000000' })).status, 400);
  const ok = await phone('POST', '/api/auth/verify', { email: 'p@example.com', code: r.body.devCode });
  assert.equal(ok.status, 200);
  const res = await fetch(`http://localhost:${server.address().port}/api/me`, { headers: { authorization: `Bearer ${ok.body.session}`, origin: 'capacitor://localhost' } });
  assert.equal((await res.json()).member.email, 'p@example.com');
  assert.equal(res.headers.get('access-control-allow-origin'), 'capacitor://localhost');
  server.close();
});

test('wrong codes lock out after five tries', async () => {
  const { server, client } = await boot();
  const c = client();
  const r = await c('POST', '/api/auth/signup', signup('l@example.com'));
  for (let i = 0; i < 5; i++) await c('POST', '/api/auth/verify', { email: 'l@example.com', code: '111111' });
  assert.equal((await c('POST', '/api/auth/verify', { email: 'l@example.com', code: r.body.devCode })).status, 429);
  server.close();
});

test('reviewer account signs in with the fixed code only', async () => {
  const { server, client } = await boot();
  const c = client();
  assert.equal((await c('POST', '/api/auth/verify', { email: 'rev@example.com', code: '000000' })).status, 400);
  assert.equal((await c('POST', '/api/auth/verify', { email: 'rev@example.com', code: '424242' })).status, 200);
  assert.equal((await c('GET', '/api/channels')).status, 200);
  server.close();
});

test('blocked members disappear from the feed', async () => {
  const { server, client, db } = await boot();
  const a = client(), b = client();
  await join(a, 'a@example.com');
  await join(b, 'b@example.com');
  db.prepare("UPDATE members SET status='approved'").run();
  await b('POST', '/api/channels/regional/posts', { body: 'Hello from B' });
  const bid = db.prepare("SELECT id FROM members WHERE email='b@example.com'").get().id;
  assert.equal((await a('GET', '/api/channels/regional/posts')).body.threads.length, 1);
  await a('POST', `/api/members/${bid}/block`);
  assert.equal((await a('GET', '/api/channels/regional/posts')).body.threads.length, 0);
  assert.equal((await b('GET', '/api/channels/regional/posts')).body.threads.length, 1);
  server.close();
});
