# Association for Industry Professional Nurses: member app

React + TypeScript app (website and Capacitor phone apps) on Supabase, the same host as Live Desk. Spec: `../association-industry-nurses-app-spec.md`.

| Piece | Where |
|---|---|
| Tables (all `ain_*`, row-level security on, no public policies) and seed events, channels, resources | `../supabase/migrations/20261026180000_industry_nurses_app.sql` |
| API: edge function `industrynurses` (same `/api/...` routes as the old Node server) | `../supabase/functions/industrynurses/` |
| Sign-in | Supabase Auth email code (6 digits). Reviewers can use email and password. |
| Client | `client/` |

Server address: `https://vbthumugbzyqndirmyns.supabase.co/functions/v1/industrynurses` (set in `npm run build:app`).

## Run and test

```bash
npm install
npm test            # Deno: rules plus the real handler against an in-memory Postgres (PGlite) loaded with the real migration
npm run build:app   # client pointed at Supabase; then `npx cap sync`
```

## Settings

Function secret `ADMIN_EMAILS` (comma separated): those sign-ups are approved automatically and get the Admin area. Everything else is injected by Supabase.

## What is in v1

Sign-up with NMC PIN format check and manual approval; email code sign-in; events (seeded from the live conferences page, checked 26/10/2026, undated events show "date not confirmed", calendar file for dated ones); jobs (each links to the employer's own listing, clicks logged); community channels with replies, reports, blocking and moderation; opt-in member directory; resources; in-app alerts; profile with data export and account deletion; admin approval queue, moderation, content forms and weekly numbers.

Not in v1: CPD log, accreditation, payments, push notifications, mentor booking.

The app checks the PIN format only. Check each PIN on the NMC register before approving.

Deployment and store steps: `DEPLOY.md`.
