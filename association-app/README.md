# Association for Industry Professional Nurses: member app

Progressive web app (React + TypeScript front end, Node + SQLite back end). Spec: `../association-industry-nurses-app-spec.md`.

## Run

```bash
npm install
npm run build
ADMIN_EMAILS=you@example.com npm start      # http://localhost:3000
npm test                                     # API tests
```

For development run `npm run dev:server` and `npm run dev:client` (client on :5173 proxies `/api`).

## Settings (environment)

| Variable | Meaning |
|---|---|
| `ADMIN_EMAILS` | Comma-separated. These sign-ups are approved automatically and get the Admin area. |
| `BASE_URL` | Public address, used in sign-in links. Use `https://` in production. |
| `MAIL_WEBHOOK_URL` | Address that receives `{to, subject, text}` as JSON and sends the email. Until set, sign-in links are printed in the server log and shown on screen (dev mode). |
| `DB_PATH` | SQLite file, default `data/app.db`. Back it up. |
| `PORT` | Default 3000. |

## What is in v1

Sign-up with NMC PIN format check and manual approval; email sign-in links; events (seeded from the live conferences page, checked 26/10/2026, undated events show "date not confirmed", calendar file for dated ones); jobs (each links to the employer's own listing, clicks logged); community channels with replies, reports and moderation; opt-in member directory; resources; in-app alerts; profile with data export and account deletion; admin approval queue, moderation, content forms and weekly numbers.

Not in v1: CPD log, accreditation, payments, push notifications, mentor booking.

## Before going live

- Connect a mail sender (`MAIL_WEBHOOK_URL`) and set `BASE_URL`.
- Host it under the Association's domain, `medsalesintelligencehub.co.uk`. A Node host is needed; WordPress cannot run it.
- Check each member's PIN on the NMC register before approving (the app checks format only).
- Add a privacy notice link to the join form.
