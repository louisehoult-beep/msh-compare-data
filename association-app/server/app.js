import express from 'express';
import { randomBytes, randomInt, timingSafeEqual } from 'node:crypto';
import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const PIN_RE = /^\d{2}[A-Z]\d{4}[A-Z]$/;
const ROLES = ['Clinical educator', 'Clinical specialist', 'Application specialist', 'Clinical affairs or regulatory', 'Sales or account management', 'Training or consultancy', 'Moving into industry', 'Other'];
const EMPLOYERS = ['Medical device company', 'Pharmaceutical company', 'Diagnostics company', 'Agency or consultancy', 'Between roles', 'Still in the NHS'];
const iso = (ms) => new Date(Date.now() + ms).toISOString();
const bad = (res, msg, code = 400) => res.status(code).json({ error: msg });
const str = (v, max = 200) => (typeof v === 'string' ? v.trim().slice(0, max) : '');
const isUrl = (u) => /^https?:\/\/[^\s]+$/i.test(u);

const NATIVE_ORIGINS = ['capacitor://localhost', 'https://localhost', 'http://localhost'];
const same = (a, b) => a.length === b.length && timingSafeEqual(Buffer.from(a), Buffer.from(b));

export function createApp(db, { adminEmails = [], sendMail = async () => {}, baseUrl = '', devLinks = false, reviewer = null } = {}) {
  const app = express();
  app.use(express.json({ limit: '50kb' }));
  // The phone apps load from capacitor://localhost, so they need cross-origin access to this API.
  app.use((req, res, next) => {
    const o = req.headers.origin;
    if (o && NATIVE_ORIGINS.includes(o)) {
      res.set({ 'Access-Control-Allow-Origin': o, 'Access-Control-Allow-Headers': 'content-type, authorization', 'Access-Control-Allow-Methods': 'GET,POST,PATCH,DELETE,OPTIONS', Vary: 'Origin' });
      if (req.method === 'OPTIONS') return res.sendStatus(204);
    }
    next();
  });

  const publicMember = (m) => ({ id: m.id, name: m.name, email: m.email, role_category: m.role_category, employer_type: m.employer_type,
    speciality: m.speciality, region: m.region, directory_visible: !!m.directory_visible, mentoring: m.mentoring,
    email_notifications: !!m.email_notifications, status: m.status, is_admin: !!m.is_admin });

  // ---- session middleware
  app.use((req, _res, next) => {
    const cookie = /(?:^|; )sid=([a-f0-9]+)/.exec(req.headers.cookie || '');
    const bearer = /^Bearer ([a-f0-9]+)$/.exec(req.headers.authorization || '');
    const sid = bearer ? bearer[1] : cookie?.[1];
    req.member = null;
    if (sid) {
      const row = db.prepare(`SELECT m.* FROM sessions s JOIN members m ON m.id = s.member_id WHERE s.id = ? AND s.expires_at > ?`).get(sid, iso(0));
      if (row) req.member = row;
    }
    next();
  });
  const needAuth = (req, res, next) => (req.member ? next() : bad(res, 'Please sign in.', 401));
  const needApproved = (req, res, next) => (req.member?.status === 'approved' ? next() : bad(res, 'Your membership is waiting for approval.', 403));
  const needAdmin = (req, res, next) => (req.member?.is_admin ? next() : bad(res, 'Admins only.', 403));
  const notify = (memberId, text, link = '') => db.prepare('INSERT INTO notifications (member_id, text, link) VALUES (?,?,?)').run(memberId, text, link);

  // ---- auth
  app.get('/api/options', (_q, res) => res.json({ roles: ROLES, employers: EMPLOYERS }));

  app.post('/api/auth/signup', async (req, res) => {
    const b = req.body || {};
    const email = str(b.email).toLowerCase();
    const name = str(b.name, 100);
    const pin = str(b.nmc_pin, 8).toUpperCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return bad(res, 'Enter a valid email address.');
    if (!name) return bad(res, 'Enter your name.');
    if (!PIN_RE.test(pin)) return bad(res, 'Your NMC PIN looks like 12A3456E: two digits, a letter, four digits, a letter.');
    if (!ROLES.includes(b.role_category)) return bad(res, 'Choose your role.');
    if (!EMPLOYERS.includes(b.employer_type)) return bad(res, 'Choose your employer type.');
    if (b.consent !== true) return bad(res, 'Please agree to the privacy notice to join.');
    if (db.prepare('SELECT 1 FROM members WHERE email = ?').get(email)) return bad(res, 'That email is already registered. Use "Sign in".', 409);
    const isAdmin = adminEmails.includes(email) ? 1 : 0;
    const info = db.prepare(`INSERT INTO members (email, name, nmc_pin, role_category, employer_type, speciality, region, status, is_admin, verified_at, consent_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?)`).run(email, name, pin, b.role_category, b.employer_type, str(b.speciality, 100), str(b.region, 100),
      isAdmin ? 'approved' : 'pending', isAdmin, isAdmin ? iso(0) : null, iso(0));
    for (const a of db.prepare('SELECT id FROM members WHERE is_admin = 1 AND id != ?').all(info.lastInsertRowid)) notify(a.id, `New member waiting for approval: ${name}`, '/admin');
    res.json({ ok: true, ...(await issueLink(Number(info.lastInsertRowid), email)) });
  });

  async function issueLink(memberId, email) {
    const token = randomBytes(24).toString('hex');
    const code = String(randomInt(0, 1000000)).padStart(6, '0');
    db.prepare('INSERT INTO login_tokens (token, member_id, expires_at, code) VALUES (?,?,?,?)').run(token, memberId, iso(15 * 60 * 1000), code);
    const link = `${baseUrl}/#/verify/${token}`;
    await sendMail(email, 'Your sign-in link', `Sign in with this link within 15 minutes:\n\n${link}\n\nUsing the phone app? Type this code instead: ${code}\n\nIf you did not ask for it, ignore this email.`);
    return devLinks ? { devLink: link, devCode: code } : {};
  }

  app.post('/api/auth/request', async (req, res) => {
    const email = str(req.body?.email).toLowerCase();
    const m = db.prepare('SELECT id FROM members WHERE email = ?').get(email);
    // Same answer whether or not the email is registered, so the form cannot be used to probe for members.
    res.json({ ok: true, ...(m ? await issueLink(m.id, email) : {}) });
  });

  function startSession(res, memberId) {
    const sid = randomBytes(24).toString('hex');
    db.prepare('INSERT INTO sessions (id, member_id, expires_at) VALUES (?,?,?)').run(sid, memberId, iso(30 * 24 * 3600 * 1000));
    res.setHeader('Set-Cookie', `sid=${sid}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${30 * 24 * 3600}${baseUrl.startsWith('https') ? '; Secure' : ''}`);
    return sid;
  }

  // Sign in with the emailed link token (web), or with email plus the 6-digit code (phone app).
  app.post('/api/auth/verify', (req, res) => {
    const email = str(req.body?.email).toLowerCase();
    const code = str(req.body?.code, 6);
    if (reviewer && email && code && email === reviewer.email && same(code, reviewer.code)) {
      const m = db.prepare('SELECT id FROM members WHERE email = ?').get(email);
      if (m) return res.json({ ok: true, session: startSession(res, m.id) });
    }
    let t;
    if (email && code) {
      t = db.prepare(`SELECT lt.* FROM login_tokens lt JOIN members m ON m.id = lt.member_id WHERE m.email = ? AND lt.used = 0 AND lt.expires_at > ? ORDER BY lt.rowid DESC LIMIT 1`).get(email, iso(0));
      if (t) {
        if (t.attempts >= 5) return bad(res, 'Too many wrong codes. Request a new one.', 429);
        if (!t.code || !same(code, t.code)) { db.prepare('UPDATE login_tokens SET attempts = attempts + 1 WHERE token = ?').run(t.token); t = null; }
      }
    } else {
      t = db.prepare('SELECT * FROM login_tokens WHERE token = ? AND used = 0 AND expires_at > ?').get(str(req.body?.token, 100), iso(0));
    }
    if (!t) return bad(res, 'That link or code has expired, was already used, or is wrong. Request a new one.', 400);
    db.prepare('UPDATE login_tokens SET used = 1 WHERE token = ?').run(t.token);
    res.json({ ok: true, session: startSession(res, t.member_id) });
  });

  app.post('/api/auth/logout', (req, res) => {
    const cookie = /(?:^|; )sid=([a-f0-9]+)/.exec(req.headers.cookie || '');
    const bearer = /^Bearer ([a-f0-9]+)$/.exec(req.headers.authorization || '');
    const sid = bearer ? bearer[1] : cookie?.[1];
    if (sid) db.prepare('DELETE FROM sessions WHERE id = ?').run(sid);
    res.setHeader('Set-Cookie', 'sid=; HttpOnly; Path=/; Max-Age=0');
    res.json({ ok: true });
  });

  app.get('/api/me', (req, res) => {
    if (!req.member) return res.json({ member: null });
    const unread = db.prepare('SELECT COUNT(*) c FROM notifications WHERE member_id = ? AND read = 0').get(req.member.id).c;
    res.json({ member: publicMember(req.member), unread });
  });

  app.patch('/api/me', needAuth, (req, res) => {
    const b = req.body || {};
    const m = req.member;
    const mentoring = ['none', 'mentor', 'mentee', 'both'].includes(b.mentoring) ? b.mentoring : m.mentoring;
    const role = ROLES.includes(b.role_category) ? b.role_category : m.role_category;
    const emp = EMPLOYERS.includes(b.employer_type) ? b.employer_type : m.employer_type;
    db.prepare(`UPDATE members SET name=?, role_category=?, employer_type=?, speciality=?, region=?, directory_visible=?, mentoring=?, email_notifications=? WHERE id=?`)
      .run(str(b.name, 100) || m.name, role, emp, str(b.speciality ?? m.speciality, 100), str(b.region ?? m.region, 100),
        b.directory_visible === undefined ? m.directory_visible : b.directory_visible ? 1 : 0, mentoring,
        b.email_notifications === undefined ? m.email_notifications : b.email_notifications ? 1 : 0, m.id);
    res.json({ member: publicMember(db.prepare('SELECT * FROM members WHERE id = ?').get(m.id)) });
  });

  // Member can delete their own account and data (UK GDPR erasure).
  app.delete('/api/me', needAuth, (req, res) => {
    db.prepare('UPDATE posts SET body = ?, hidden = 1 WHERE member_id = ?').run('[deleted]', req.member.id);
    db.exec('PRAGMA foreign_keys = OFF');
    try {
      db.prepare('DELETE FROM reports WHERE member_id = ?').run(req.member.id);
      db.prepare('UPDATE jobs SET posted_by = NULL WHERE posted_by = ?').run(req.member.id);
      db.prepare('DELETE FROM members WHERE id = ?').run(req.member.id);
      db.prepare('DELETE FROM sessions WHERE member_id = ?').run(req.member.id);
      db.prepare('DELETE FROM login_tokens WHERE member_id = ?').run(req.member.id);
      db.prepare('DELETE FROM notifications WHERE member_id = ?').run(req.member.id);
      db.prepare('DELETE FROM event_saves WHERE member_id = ?').run(req.member.id);
      db.prepare('DELETE FROM job_clicks WHERE member_id = ?').run(req.member.id);
    } finally { db.exec('PRAGMA foreign_keys = ON'); }
    res.setHeader('Set-Cookie', 'sid=; HttpOnly; Path=/; Max-Age=0');
    res.json({ ok: true });
  });

  app.get('/api/me/export', needAuth, (req, res) => {
    const m = db.prepare('SELECT * FROM members WHERE id = ?').get(req.member.id);
    res.json({ member: m,
      posts: db.prepare('SELECT * FROM posts WHERE member_id = ?').all(m.id),
      saved_events: db.prepare('SELECT event_id FROM event_saves WHERE member_id = ?').all(m.id),
      job_clicks: db.prepare('SELECT job_id, created_at FROM job_clicks WHERE member_id = ?').all(m.id) });
  });

  // ---- notifications
  app.get('/api/notifications', needAuth, (req, res) => {
    res.json(db.prepare('SELECT * FROM notifications WHERE member_id = ? ORDER BY id DESC LIMIT 50').all(req.member.id));
  });
  app.post('/api/notifications/read', needAuth, (req, res) => {
    db.prepare('UPDATE notifications SET read = 1 WHERE member_id = ?').run(req.member.id);
    res.json({ ok: true });
  });

  // ---- events (public read; saves need a member)
  app.get('/api/events', (req, res) => {
    const rows = db.prepare(`SELECT e.*, ${req.member ? '(SELECT 1 FROM event_saves s WHERE s.event_id = e.id AND s.member_id = ?)' : '0'} AS saved
      FROM events e ORDER BY (start_date IS NULL), start_date, title`).all(...(req.member ? [req.member.id] : []));
    res.json(rows.map((e) => ({ ...e, saved: !!e.saved, members_only: !!e.members_only })));
  });
  app.post('/api/events/:id/save', needAuth, (req, res) => {
    db.prepare('INSERT OR IGNORE INTO event_saves (event_id, member_id) VALUES (?,?)').run(req.params.id, req.member.id);
    res.json({ ok: true });
  });
  app.delete('/api/events/:id/save', needAuth, (req, res) => {
    db.prepare('DELETE FROM event_saves WHERE event_id = ? AND member_id = ?').run(req.params.id, req.member.id);
    res.json({ ok: true });
  });
  app.get('/api/events/:id.ics', (req, res) => {
    const e = db.prepare('SELECT * FROM events WHERE id = ?').get(req.params.id);
    if (!e || !e.start_date) return bad(res, 'This event has no confirmed date.', 404);
    const d = (s) => s.replaceAll('-', '');
    const end = new Date(`${e.end_date || e.start_date}T00:00:00Z`);
    end.setUTCDate(end.getUTCDate() + 1);
    const esc = (s) => String(s || '').replace(/[\;,]/g, (c) => '\\' + c).replace(/\n/g, '\\n');
    res.type('text/calendar').set('Content-Disposition', `attachment; filename="event-${e.id}.ics"`).send([
      'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Association for Industry Professional Nurses//EN', 'BEGIN:VEVENT',
      `UID:event-${e.id}@medsalesintelligencehub.co.uk`, `DTSTAMP:${new Date().toISOString().replace(/[-:]|\.\d+/g, '')}`,
      `DTSTART;VALUE=DATE:${d(e.start_date)}`, `DTEND;VALUE=DATE:${end.toISOString().slice(0, 10).replaceAll('-', '')}`,
      `SUMMARY:${esc(e.title)}`, `LOCATION:${esc(e.venue)}`, `DESCRIPTION:${esc(e.detail + ' Confirm on the organiser site: ' + e.source_url)}`,
      'END:VEVENT', 'END:VCALENDAR'].join('\r\n'));
  });
  app.post('/api/admin/events', needAuth, needAdmin, (req, res) => {
    const b = req.body || {};
    if (!str(b.title) || !isUrl(str(b.source_url, 500))) return bad(res, 'Title and a source link are needed.');
    const date = (v) => (/^\d{4}-\d{2}-\d{2}$/.test(v || '') ? v : null);
    const info = db.prepare(`INSERT INTO events (title, organiser, detail, start_date, end_date, venue, source_url, group_label, members_only, verified_at)
      VALUES (?,?,?,?,?,?,?,?,?,?)`).run(str(b.title), str(b.organiser), str(b.detail, 1000), date(b.start_date), date(b.end_date), str(b.venue) || null,
      str(b.source_url, 500), str(b.group_label), b.members_only ? 1 : 0, iso(0).slice(0, 10));
    res.json({ id: Number(info.lastInsertRowid) });
  });

  // ---- jobs
  app.get('/api/jobs', needAuth, needApproved, (req, res) => {
    const where = ['(expires_at IS NULL OR expires_at >= date(\'now\'))'];
    const args = [];
    for (const k of ['speciality', 'seniority']) if (req.query[k]) { where.push(`${k} = ?`); args.push(str(req.query[k])); }
    if (req.query.q) { where.push('(title LIKE ? OR employer LIKE ? OR location LIKE ?)'); const q = `%${str(req.query.q, 60)}%`; args.push(q, q, q); }
    if (req.query.remote === '1') where.push('remote = 1');
    res.json(db.prepare(`SELECT * FROM jobs WHERE ${where.join(' AND ')} ORDER BY id DESC`).all(...args).map((j) => ({ ...j, remote: !!j.remote })));
  });
  app.post('/api/jobs/:id/click', needAuth, needApproved, (req, res) => {
    const j = db.prepare('SELECT source_url FROM jobs WHERE id = ?').get(req.params.id);
    if (!j) return bad(res, 'Job not found.', 404);
    db.prepare('INSERT INTO job_clicks (job_id, member_id) VALUES (?,?)').run(req.params.id, req.member.id);
    res.json({ url: j.source_url });
  });
  app.post('/api/admin/jobs', needAuth, needAdmin, (req, res) => {
    const b = req.body || {};
    if (!str(b.employer) || !str(b.title) || !isUrl(str(b.source_url, 500))) return bad(res, 'Employer, title and the employer\'s own listing link are all needed.');
    const info = db.prepare(`INSERT INTO jobs (employer, title, location, speciality, seniority, remote, source_url, expires_at, posted_by) VALUES (?,?,?,?,?,?,?,?,?)`)
      .run(str(b.employer), str(b.title), str(b.location), str(b.speciality), str(b.seniority), b.remote ? 1 : 0, str(b.source_url, 500),
        /^\d{4}-\d{2}-\d{2}$/.test(b.expires_at || '') ? b.expires_at : null, req.member.id);
    res.json({ id: Number(info.lastInsertRowid) });
  });
  app.delete('/api/admin/jobs/:id', needAuth, needAdmin, (req, res) => { db.prepare('DELETE FROM jobs WHERE id = ?').run(req.params.id); res.json({ ok: true }); });

  // ---- resources
  app.get('/api/resources', needAuth, needApproved, (_q, res) => res.json(db.prepare('SELECT * FROM resources ORDER BY id DESC').all()));
  app.post('/api/admin/resources', needAuth, needAdmin, (req, res) => {
    const b = req.body || {};
    if (!str(b.title) || !isUrl(str(b.url, 500))) return bad(res, 'Title and link are needed.');
    const info = db.prepare('INSERT INTO resources (title, kind, url, summary) VALUES (?,?,?,?)').run(str(b.title), str(b.kind) || 'Link', str(b.url, 500), str(b.summary, 500));
    res.json({ id: Number(info.lastInsertRowid) });
  });
  app.delete('/api/admin/resources/:id', needAuth, needAdmin, (req, res) => { db.prepare('DELETE FROM resources WHERE id = ?').run(req.params.id); res.json({ ok: true }); });

  // ---- directory (opt-in only)
  app.get('/api/directory', needAuth, needApproved, (req, res) => {
    const where = ['status = \'approved\'', 'directory_visible = 1'];
    const args = [];
    if (req.query.mentoring === '1') where.push('mentoring != \'none\'');
    if (req.query.q) { where.push('(name LIKE ? OR speciality LIKE ? OR region LIKE ?)'); const q = `%${str(req.query.q, 60)}%`; args.push(q, q, q); }
    res.json(db.prepare(`SELECT id, name, role_category, employer_type, speciality, region, mentoring FROM members WHERE ${where.join(' AND ')} ORDER BY name`).all(...args));
  });

  // ---- community
  app.get('/api/channels', needAuth, needApproved, (_q, res) => res.json(db.prepare(
    `SELECT c.*, (SELECT COUNT(*) FROM posts p WHERE p.channel_id = c.id AND p.parent_id IS NULL AND p.hidden = 0) AS threads FROM channels c ORDER BY sort`).all()));
  const postRow = `p.id, p.parent_id, p.body, p.created_at, m.name AS author, m.role_category AS author_role, p.member_id`;
  app.get('/api/channels/:slug/posts', needAuth, needApproved, (req, res) => {
    const c = db.prepare('SELECT * FROM channels WHERE slug = ?').get(req.params.slug);
    if (!c) return bad(res, 'Channel not found.', 404);
    const threads = db.prepare(`SELECT ${postRow} FROM posts p JOIN members m ON m.id = p.member_id WHERE p.channel_id = ? AND p.parent_id IS NULL AND p.hidden = 0 AND p.member_id NOT IN (SELECT blocked_id FROM blocks WHERE blocker_id = ?) ORDER BY p.id DESC LIMIT 100`).all(c.id, req.member.id);
    const replies = threads.length ? db.prepare(`SELECT ${postRow} FROM posts p JOIN members m ON m.id = p.member_id WHERE p.parent_id IN (${threads.map(() => '?').join(',')}) AND p.hidden = 0 AND p.member_id NOT IN (SELECT blocked_id FROM blocks WHERE blocker_id = ?) ORDER BY p.id`).all(...threads.map((t) => t.id), req.member.id) : [];
    res.json({ channel: c, threads: threads.map((t) => ({ ...t, replies: replies.filter((r) => r.parent_id === t.id) })) });
  });
  app.post('/api/channels/:slug/posts', needAuth, needApproved, (req, res) => {
    const c = db.prepare('SELECT * FROM channels WHERE slug = ?').get(req.params.slug);
    const body = str(req.body?.body, 3000);
    if (!c) return bad(res, 'Channel not found.', 404);
    if (!body) return bad(res, 'Write something first.');
    let parent = null;
    if (req.body?.parent_id) {
      parent = db.prepare('SELECT * FROM posts WHERE id = ? AND channel_id = ? AND parent_id IS NULL AND hidden = 0').get(req.body.parent_id, c.id);
      if (!parent) return bad(res, 'That thread is not available.', 404);
    }
    const info = db.prepare('INSERT INTO posts (channel_id, parent_id, member_id, body) VALUES (?,?,?,?)').run(c.id, parent ? parent.id : null, req.member.id, body);
    if (parent && parent.member_id !== req.member.id) notify(parent.member_id, `${req.member.name} replied to your post in ${c.title}`, `/community/${c.slug}`);
    res.json({ id: Number(info.lastInsertRowid) });
  });
  app.delete('/api/posts/:id', needAuth, needApproved, (req, res) => {
    const p = db.prepare('SELECT * FROM posts WHERE id = ?').get(req.params.id);
    if (!p || (p.member_id !== req.member.id && !req.member.is_admin)) return bad(res, 'Not allowed.', 403);
    db.prepare('UPDATE posts SET hidden = 1 WHERE id = ? OR parent_id = ?').run(p.id, p.id);
    res.json({ ok: true });
  });
  app.post('/api/posts/:id/report', needAuth, needApproved, (req, res) => {
    const p = db.prepare('SELECT id FROM posts WHERE id = ? AND hidden = 0').get(req.params.id);
    if (!p) return bad(res, 'Post not found.', 404);
    db.prepare('INSERT OR IGNORE INTO reports (post_id, member_id, reason) VALUES (?,?,?)').run(p.id, req.member.id, str(req.body?.reason, 300) || 'No reason given');
    for (const a of db.prepare('SELECT id FROM members WHERE is_admin = 1').all()) notify(a.id, 'A post was reported', '/admin');
    res.json({ ok: true });
  });

  // Members can block anyone whose posts they do not want to see (required for apps with user-generated content).
  app.post('/api/members/:id/block', needAuth, needApproved, (req, res) => {
    const id = Number(req.params.id);
    if (id === req.member.id || !db.prepare('SELECT 1 FROM members WHERE id = ?').get(id)) return bad(res, 'Not allowed.', 400);
    db.prepare('INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?,?)').run(req.member.id, id);
    for (const a of db.prepare('SELECT id FROM members WHERE is_admin = 1').all()) notify(a.id, 'A member was blocked by another member', '/admin');
    res.json({ ok: true });
  });

  // ---- admin
  app.get('/api/admin/pending', needAuth, needAdmin, (_q, res) => res.json(db.prepare(
    `SELECT id, name, email, nmc_pin, role_category, employer_type, speciality, region, created_at FROM members WHERE status = 'pending' ORDER BY id`).all()));
  app.post('/api/admin/members/:id/decision', needAuth, needAdmin, (req, res) => {
    const approve = req.body?.decision === 'approve';
    const m = db.prepare('SELECT * FROM members WHERE id = ?').get(req.params.id);
    if (!m) return bad(res, 'Member not found.', 404);
    db.prepare('UPDATE members SET status = ?, verified_at = ? WHERE id = ?').run(approve ? 'approved' : 'rejected', approve ? iso(0) : null, m.id);
    if (approve) notify(m.id, 'Your membership is approved. Welcome.', '/');
    res.json({ ok: true });
  });
  app.get('/api/admin/reports', needAuth, needAdmin, (_q, res) => res.json(db.prepare(
    `SELECT r.id, r.reason, r.created_at, p.id AS post_id, p.body, p.hidden, m.name AS author FROM reports r JOIN posts p ON p.id = r.post_id JOIN members m ON m.id = p.member_id WHERE r.resolved = 0 ORDER BY r.id`).all()));
  app.post('/api/admin/reports/:id/resolve', needAuth, needAdmin, (req, res) => {
    const r = db.prepare('SELECT * FROM reports WHERE id = ?').get(req.params.id);
    if (!r) return bad(res, 'Report not found.', 404);
    if (req.body?.hide) db.prepare('UPDATE posts SET hidden = 1 WHERE id = ? OR parent_id = ?').run(r.post_id, r.post_id);
    db.prepare('UPDATE reports SET resolved = 1 WHERE post_id = ?').run(r.post_id);
    res.json({ ok: true });
  });
  app.get('/api/admin/stats', needAuth, needAdmin, (_q, res) => {
    const c = (sql) => db.prepare(sql).get().c;
    res.json({
      approved_members: c(`SELECT COUNT(*) c FROM members WHERE status = 'approved'`),
      pending_members: c(`SELECT COUNT(*) c FROM members WHERE status = 'pending'`),
      joined_last_7_days: c(`SELECT COUNT(*) c FROM members WHERE created_at >= datetime('now','-7 days')`),
      active_last_7_days: c(`SELECT COUNT(DISTINCT member_id) c FROM (SELECT member_id FROM posts WHERE created_at >= datetime('now','-7 days') UNION ALL SELECT member_id FROM job_clicks WHERE created_at >= datetime('now','-7 days'))`),
      profiles_in_directory: c(`SELECT COUNT(*) c FROM members WHERE directory_visible = 1`),
      event_saves: c('SELECT COUNT(*) c FROM event_saves'),
      job_clicks: c('SELECT COUNT(*) c FROM job_clicks'),
      by_employer_type: db.prepare(`SELECT employer_type AS label, COUNT(*) AS n FROM members WHERE status = 'approved' GROUP BY employer_type ORDER BY n DESC`).all(),
      by_role: db.prepare(`SELECT role_category AS label, COUNT(*) AS n FROM members WHERE status = 'approved' GROUP BY role_category ORDER BY n DESC`).all(),
    });
  });

  app.use('/api', (_q, res) => bad(res, 'Not found.', 404));

  // ---- static front end (after `npm run build`)
  const dist = join(here, '..', 'client', 'dist');
  if (existsSync(dist)) {
    app.use(express.static(dist));
    app.get('*', (_q, res) => res.sendFile(join(dist, 'index.html')));
  }
  return app;
}
