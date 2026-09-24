# Phone alerts (web push) for members — set-up and runbook

Added 23/09/2026. Members get one phone notification a morning, only when the
daily speciality-news build has landed something new in the specialities they
chose. Tapping it opens that speciality's page on the Hub.

## The parts

| Part | Where | Job |
|---|---|---|
| Hub page 4463 "Phone Alerts (Subscribers only)" | The Hub, members only | "Turn on phone alerts" asks WordPress for a member pass and opens the alerts page with it. Source: `docs/hub-page-4463-phone-alerts.html`. |
| `alerts/index.html` | GitHub Pages, this repo | The member page: pick specialities, "Turn on alerts", "Turn off". |
| `supabase/functions/alerts-subscribe/` | Supabase Edge Function | The only writer of `push_subscriptions`. Saves a phone only with a valid member pass; turns a phone off. |
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

**Superseded 24/09/2026: members only.** The anon insert policy above is
dropped and every anon grant revoked by
`supabase/migrations/20260924160000_alerts_members_only.sql`, which also adds
`member_id`, `verified_at` and `updated_at`. See "Members only" below.

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

Changing specialities keeps the phone's push address and updates its row in
place through `alerts-subscribe` (since 24/09/2026; until then it took a new
address, and a phone that got the same one back hit a 409 and kept its old
specialities).

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

## Members only (24/09/2026)

Lou: only paying members can subscribe. Before this the page wrote to the
table with the public anon key, so anyone who found the page could sign up.

1. Hub page 4463 is members-only. Its button calls
   `admin-ajax.php?action=msh_ask_pass`, the pass WPCode snippet 4510 already
   issues for Ask the Hub: signed with `MSH_ASK_SECRET`, given **only** to a
   member whose plan opens the Live Desk (page 675), or an admin.
2. It opens the alerts page with the pass after `#m=`. The page moves it into
   the query string so an iPhone's Add to Home Screen keeps it (the manifest
   has no `start_url` for that reason).
3. The page sends the subscription and the pass to the Edge Function
   `alerts-subscribe`. It checks the pass with the same `pass.ts` as Ask the
   Hub, allowing 24 hours past the pass's expiry for the Home Screen step, and
   upserts the row with the member's WordPress user id in `member_id`.
4. Without a pass, a phone already saved by a member may change its
   specialities or turn off. Anything else gets 403 and the page sends them
   to the Hub.
5. `push_alerts.py` sends only to rows with a `member_id` (the query filters,
   and `members_only()` checks again).

Not covered yet: a member who **lapses** keeps their row until they turn
alerts off. Removing lapsed members needs WordPress to answer "is user N
still a member?" for the sender; not built.

Rows saved before 24/09/2026 have no `member_id` and are never sent to. Those
phones must turn alerts on again once, from the Hub page. The diagnose run
lists them. Delete them in the SQL editor once nobody needs them:
`delete from push_subscriptions where member_id is null;`

Deploying the function (verify_jwt off: the pass is the check):

    supabase functions deploy alerts-subscribe --no-verify-jwt --project-ref vbthumugbzyqndirmyns

Tests: `deno test supabase/functions/alerts-subscribe/rules_test.ts supabase/functions/ask-the-hub/pass_test.ts`.

## How a run goes

1. `speciality-news.yml` finishes green → `push-alerts.yml` starts.
2. `build-config` rewrites `alerts/config.json` if anything changed.
3. `send` diffs every `data/speciality-news/<slug>.json` against the seen-set,
   pulls the subscriber rows, and sends each phone one message:
   * one speciality with news: **"Stroke: 2 new items"** / headline — source;
   * several: **"Hub news: 5 new items across 3 specialities"** / "Stroke (2) · Urology (2) · …";
   * nothing in their specialities: no push.
4. Rows whose push service says 404 or 410 are deleted. Other failures are
   logged and counted, never retried (a lost buzz beats a duplicate).
5. `verify.py` gates, then the state and config are committed.

**What a tap opens (changed 24/09/2026).** `alerts/latest.html`, inside the
alerts app: the headlines the push carried (up to 12, each linking to the
source article) and an "Open <speciality> on the Hub" link per speciality.
It used to open the Hub page directly, but a tap opens inside the alerts
app's own walled-off browser, which has no Hub login, so members landed on a
login screen and then the Live Desk. The items travel in the push payload
(kept under 3 KB) and the service worker saves them to the phone's cache, so
the list is there the moment the alert is tapped, with no deploy to wait for.

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
* There is no on-page preview button. "Show me what an alert looks like" was
  removed on 23/09/2026: it did not work on Lou's iPhone and proved nothing
  about delivery anyway. Use the workflow's **test alert** instead.
* The page only says "Alerts are on" once Supabase has the row. Every visit
  re-saves the phone's subscription through `alerts-subscribe`, so a signup
  whose save never landed repairs itself when the page is next opened.
  Found 23/09/2026: Lou's iPhone showed the test button and "on" while the
  table held no iPhone row at all, because "on" was read from the phone's
  own state.

## Phones

* Android (Chrome, Edge, Samsung Internet, Firefox): works from the page directly.
* iPhone/iPad: iOS 16.4+ only, and only from the page's OWN Home Screen icon
  (Apple's rule, not ours). The icon can be added from Safari, Chrome, Edge or
  Firefox; the page detects which one and shows that browser's own steps
  (in-app browsers such as Instagram are told to open Chrome or Safari first).
  Until 23/09/2026 it told everyone to use Safari, which stopped Lou, a Chrome
  user, five times. Anywhere else on iOS the page hides the button and shows
  the steps instead. The trap: a member who has the **Hub** saved to
  their Home Screen and taps the alerts link from inside it gets the alerts
  page in a pop-over sheet, which can never get permission; it flashes and
  drops back to the Hub. They must open the link in their browser and add
  the alerts page itself.
* Desktop browsers work too; the alert appears as a system notification.

## The badge

Android draws the small status-bar badge from its transparency only, in
white. The full-colour app icon showed there as a blank square. Since
24/09/2026 `sw.js` uses `alerts/badge-96.png`, a white bars-and-arrow
silhouette drawn by `scripts/make_alert_icons.py --badge`. iOS ignores it.

## pywebpush

Pinned in `push-alerts.yml` (`pywebpush==2.5.0`, 24/09/2026). Bump it on
purpose, after a dry run, never by default.

## The app icon

`alerts/apple-touch-icon.png` (180, iPhone Home Screen), `icon-192.png` and
`icon-512.png` are built from one logo by `scripts/make_alert_icons.py`.
Since 24/09/2026 that's the Elevate and Thrive Gold logo (Hub media 2237);
the first icons were a plain navy square that read as black on an iPhone.
To change it: Actions, "Phone alerts app icons", Run workflow, paste the new
logo's URL. A logo with transparency is laid on the Hub navy with a margin,
because iOS fills transparent pixels with black.

iPhones keep the icon they had when the page was added to the Home Screen.
After a change, remove the **Hub alerts** icon, add it again from the alerts
page and turn alerts back on. Members who already have it keep the old icon
until they do the same; their alerts keep working either way.

## Rotating the VAPID key

Every existing subscription is bound to the public key. Rotating it means
every member has to re-subscribe. Only do it if the private key leaks:
`keys` → new secret → `build-config` → members re-subscribe.
