import { openDb } from './db.js';
import { seed } from './seed.js';
import { createApp } from './app.js';

const db = openDb();
seed(db);
const port = Number(process.env.PORT || 3000);
const baseUrl = process.env.BASE_URL || `http://localhost:${port}`;
// Until a mail service is connected, sign-in links are printed here and returned to the browser in dev mode.
const devLinks = process.env.DEV_LINKS === '1' || !process.env.MAIL_WEBHOOK_URL;
const sendMail = async (to, subject, text) => {
  if (process.env.MAIL_WEBHOOK_URL) {
    const r = await fetch(process.env.MAIL_WEBHOOK_URL, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ to, subject, text }) });
    if (!r.ok) throw new Error(`Mail webhook returned ${r.status}`);
  } else console.log(`[mail to ${to}] ${subject}\n${text}\n`);
};
createApp(db, { adminEmails: (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map((s) => s.trim()).filter(Boolean), sendMail, baseUrl, devLinks })
  .listen(port, () => console.log(`Association app on ${baseUrl}${devLinks ? ' (dev sign-in links ON)' : ''}`));
