# Phone alerts (web push) for members — set-up and runbook

Added 23/09/2026. Members get one phone notification a morning, only when the
daily speciality-news build has landed something new in the specialities they
chose. Tapping it opens that speciality's page on the Hub.

## The parts

| Part | Where | Job |
|---|---|---|
| `alerts/index.html` | GitHub Pages, this repo | The member page: pick specialities, "Turn on alerts", "Turn off". |
| `alerts/sw.js` | GitHub Pages | Service worker: shows the notification, opens the page on tap. |
| `alerts/config.json` | Generated, committed | Public values only: VAPID public key, Supabase URL + anon key, speciality list. |
| Supabase table `push_subscriptions` | Lou's Supabase project | Where the browser stores each phone's push address. Not in this repo: a push address lets its holder buzz that phone. |
| `scripts/push_alerts.py` | This repo | `build-config`, `send`, `keys`. |
| `.github/workflows/push-alerts.yml` | GitHub Actions | Runs after every successful "Speciality news refresh". |
| `state/push-alerts.json` | Committed by the workflow | Which item links have already been pushed. Delete it to re-seed without sending. |

Why web push and not email: MailerLite is a campaign tool, and a daily
per-speciality campaign to a segment per speciality is thirty campaigns a
morning. A web push is one HTTP call per phone, costs nothing, and the phone
itself is the subscriber, so no member data beyond a push address is held.

## One-time set-up (Lou)

### 1. Supabase table

In the Supabase project, SQL editor, run:

```sql
create table if not exists public.push_subscriptions (
  id           bigint generated always as identity primary key,
  endpoint     text not null unique,
  p256dh       text not null,
  auth         text not null,
  specialities text[] not null default '{}',   -- empty = every speciality
  user_agent   text,
  created_at   timestamptz not null default now()
);

alter table public.push_subscriptions enable row level security;

-- The page inserts with the ANON key. It may insert, and nothing else:
-- no select (so nobody can list other phones' addresses), no update, no delete.
create policy "anon may subscribe"
  on public.push_subscriptions
  for insert to anon
  with check (true);

grant insert on public.push_subscriptions to anon;
```

The sender uses the **service-role** key, which bypasses row-level security,
to read the table and delete rows whose push service answers 404/410.

**Diagnostics table (added 23/09/2026).** The page logs where a phone got
stuck (iPhone not opened from the Home Screen, permission refused, save
failed) so nobody has to ask a member to read out an error. Insert-only for
anon, same as the subscriptions table; nothing personal beyond the browser's
user-agent string.

```sql
create table if not exists public.push_events (
  id          bigint generated always as identity primary key,
  stage       text not null,        -- subscribed | fail-permission | fail-subscribe | fail-save | fail-resave | ios-not-home-screen | unsupported | fail-boot
  detail      text,
  standalone  boolean,
  permission  text,
  user_agent  text,
  created_at  timestamptz not null default now()
);
alter table public.push_events enable row level security;
create policy "anon may log" on public.push_events for insert to anon with check (true);
grant insert on public.push_events to anon;
```

Read it in the Supabase SQL editor:
`select * from push_events order by created_at desc limit 50;`

Changing specialities on the page = the browser drops its old push address
and takes a new one, then inserts a new row. The old row is pruned on the
next send. So the anon role never needs update or delete.

### 2. GitHub secrets (repo Settings, Secrets and variables, Actions)

| Secret | Value |
|---|---|
| `VAPID_PRIVATE_KEY` | The private half of the key pair minted 23/09/2026 (handed over in the session that built this, or mint a new pair: `python3 scripts/push_alerts.py keys`, then also re-run `build-config` so the public half in `alerts/config.json` matches). |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` (Supabase, Project Settings, API). |
| `SUPABASE_ANON_KEY` | The `anon` `public` key from the same page. Ends up in `alerts/config.json`, which is fine: it is designed to sit in a web page. |
| `SUPABASE_SERVICE_KEY` | The `service_role` key. Never goes anywhere but the Actions runner. |

Until all four exist the workflow runs, prints a warning, sends nothing and
marks the day's items seen (nobody can have subscribed yet).

### 3. GitHub Pages

Repo Settings, Pages, Source "Deploy from a branch", branch `main`, folder
`/ (root)`. The `.nojekyll` file at the root stops Jekyll touching anything.
The member page is then at:

    https://louisehoult-beep.github.io/msh-compare-data/alerts/

Optional, nicer: a custom domain such as `alerts.medsalesintelligencehub.co.uk`
(CNAME to `louisehoult-beep.github.io`, then set it on the Pages settings
page). Notifications then show the Hub's own domain instead of github.io.

### 4. Link it from the Hub

A draft page "Phone Alerts (Subscribers only)" under page 675 was created in
the session that built this; publish it and add it to the member menu. The
button simply links to the Pages URL above.

## How a run goes

1. `speciality-news.yml` finishes green → `push-alerts.yml` starts.
2. `build-config` rewrites `alerts/config.json` if anything changed.
3. `send` diffs every `data/speciality-news/<slug>.json` against the seen-set,
   pulls the subscriber rows, and sends each phone one message:
   * one speciality with news: **"Stroke: 2 new items"** / headline — source, opens the Stroke page;
   * several: **"Hub news: 5 new items across 3 specialities"** / "Stroke (2) · Urology (2) · …", opens the Hub;
   * nothing in their specialities: no push.
4. Rows whose push service says 404 or 410 are deleted. Other failures are
   logged and counted, never retried (a lost buzz beats a duplicate).
5. `verify.py` gates, then the state and config are committed.

Same-day tag (`msh-news-YYYYMMDD`) means a manual re-run the same morning
replaces the notification on the lock screen rather than stacking a second.

## Checking it

* Dry run: Actions, "Phone alerts (web push)…", Run workflow, tick dry run.
  Prints the messages that would go out; changes nothing.
* Real test to every subscribed phone: Run workflow, tick **test alert**.
  Sends "Test alert: phone alerts are working" to every row now; the news
  seen-set is untouched, so the next morning's digest is unaffected.
* Locally: `python3 scripts/push_alerts.py send --dry-run`.
* Unit tests: `python3 test_push_alerts.py` (registered in
  `scripts/run_unit_tests.py`).
* A member can tap "Show me what an alert looks like" on the page: that is a
  local notification from the service worker, no server involved. It proves
  nothing about delivery; the page says so under the button.
* The page only says "Alerts are on" once Supabase has the row. Every visit
  re-saves the phone's subscription (a 409 means it is already on file), so a
  signup whose save never landed repairs itself when the page is next opened.
  Found 23/09/2026: Lou's iPhone showed the test button and "on" while the
  table held no iPhone row at all, because "on" was read from the phone's
  own state.

## Phones

* Android (Chrome, Edge, Samsung Internet, Firefox): works from the page directly.
* iPhone/iPad: iOS 16.4+ only, and only from the page's OWN Home Screen icon
  (Safari rule, not ours). Anywhere else on iOS the page hides the button and
  shows three steps instead. The trap: a member who has the **Hub** saved to
  their Home Screen and taps the alerts link from inside it gets the alerts
  page in a pop-over sheet, which can never get permission; it flashes and
  drops back to the Hub. They must open the link in Safari and add the
  alerts page itself.
* Desktop browsers work too; the alert appears as a system notification.

## Rotating the VAPID key

Every existing subscription is bound to the public key. Rotating it means
every member has to re-subscribe. Only do it if the private key leaks:
`keys` → new secret → `build-config` → members re-subscribe.
