import { openDb } from './db.js';
import { seed } from './seed.js';
import { createApp } from './app.js';

const db = openDb();
seed(db);
const port = Number(process.env.PORT || 3000);
const baseUrl = process.env.BASE_URL || `http://localhost:${port}`;
// Until a mail service is connected, sign-in links are printed here and returned to the browser in dev mode.
const devLinks = process.env.DEV_LINKS === '1' || !(process.env.MAIL_WEBHOOK_URL || process.env.RESEND_API_KEY);
const sendMail = async (to, subject, text) => {
  if (process.env.RESEND_API_KEY) {
    const r = await fetch('https://api.resend.com/emails', { method: 'POST', headers: { 'content-type': 'application/json', authorization: `Bearer ${process.env.RESEND_API_KEY}` },
      body: JSON.stringify({ from: process.env.MAIL_FROM, to, subject, text }) });
    if (!r.ok) throw new Error(`Resend returned ${r.status}`);
  } else if (process.env.MAIL_WEBHOOK_URL) {
    const r = await fetch(process.env.MAIL_WEBHOOK_URL, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ to, subject, text }) });
    if (!r.ok) throw new Error(`Mail webhook returned ${r.status}`);
  } else console.log(`[mail to ${to}] ${subject}\n${text}\n`);
};
// App store reviewers cannot receive email, so one pre-approved account signs in with a fixed code.
const reviewer = process.env.REVIEWER_EMAIL && process.env.REVIEWER_CODE
  ? { email: process.env.REVIEWER_EMAIL.toLowerCase(), code: process.env.REVIEWER_CODE } : null;
if (reviewer) {
  db.prepare(`INSERT OR IGNORE INTO members (email, name, nmc_pin, role_category, employer_type, status, verified_at, consent_at)
    VALUES (?, 'App Store Reviewer', '00A0000A', 'Other', 'Other', 'approved', datetime('now'), datetime('now'))`).run(reviewer.email);
}
createApp(db, { reviewer, adminEmails: (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map((s) => s.trim()).filter(Boolean), sendMail, baseUrl, devLinks })
  .listen(port, () => console.log(`Association app on ${baseUrl}${devLinks ? ' (dev sign-in links ON)' : ''}`));
