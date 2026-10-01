# Live Desk app

The Hub's Live Desk as an iPhone and Android app, with alerts. Free for Hub
members whose plan opens the Live Desk; sold separately in the app to everyone
else. Added 01/10/2026. Everything else stays on the laptop Hub.

## How it fits together

| Piece | Where | What it does |
|---|---|---|
| Feed | `medical-sales-hub-pipeline/app_feed.py` | Each hourly page 675 publish also writes the same panels and ticker as JSON to Supabase `livedesk_feed`. |
| Server | `supabase/functions/livedesk`, `livedesk-revenuecat`, migration `20261001090000_livedesk_app.sql` | Accounts, access rule, feed behind a login, Hub link, devices, account deletion, store subscriptions. |
| Hub link page | `docs/hub-page-livedesk-app-link.html` | Members-only Hub page. Hands the member pass (WPCode snippet 4510) back to the app. |
| Alerts | `scripts/push_alerts.py` + `scripts/fcm_push.py` | The same 9am, 12 noon and 4pm digest, sent to app devices through Firebase. |
| App | `livedesk-app/` (Capacitor) | Sign-in by email code, Desk, Alerts, Account, paywall. |
| Builds | `codemagic.yaml` | Tag `livedesk-vX.Y.Z` builds both apps and uploads to TestFlight and Play internal testing. |

Access rule (one place in SQL, mirrored in `livedesk/rules.ts`): Hub link
verified in the last 35 days, or a store subscription in date.

Store rules followed: Apple 3.1.3(b) (access bought elsewhere, with in-app
purchase also offered), 3.1.1 (no links or calls to action to buy outside the
app, UK storefront), 5.1.1(v) (delete account in the app), 3.1.2 (prices and
renewal terms shown from the store).

## Local

    npm install
    npm test
    npm run build        # writes src/config.js and www/app.js
    npx cap sync

## One-time set-up (in order)

1. Supabase (project vbthumugbzyqndirmyns): run the migration; deploy
   `livedesk` (JWT on) and `livedesk-revenuecat --no-verify-jwt`; set secret
   `REVENUECAT_WEBHOOK_SECRET`. Auth: enable email OTP and set the email
   template to show `{{ .Token }}`; add custom SMTP before launch.
2. Pipeline repo secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`.
3. Hub pages: `/medical-sales-hub/live-desk-app/` (link page, under the
   subscriber-only parent), `/live-desk-app-privacy/`, `/live-desk-app-support/`.
4. Firebase project: add iOS and Android apps (id
   `uk.co.medsalesintelligencehub.livedesk`), upload the APNs key, download
   both config files, create a service account; secret `FCM_SERVICE_ACCOUNT`
   in msh-compare-data.
5. App Store Connect and Play Console: create the app, subscription group and
   products (monthly, annual). RevenueCat: project, both apps, entitlement
   `livedesk`, offering with both packages, webhook to
   `https://vbthumugbzyqndirmyns.supabase.co/functions/v1/livedesk-revenuecat`.
6. Codemagic: connect this repo, environment group `livedesk` (see
   `codemagic.yaml`), App Store Connect key, Android upload keystore.
7. Tag `livedesk-v1.0.0` and push.

## App Review demo account

Apple and Google need a way in. Create a reviewer account: sign in once in the
app with the reviewer email, then in Supabase SQL:

    insert into public.livedesk_access (user_id, store_expires_at)
    select id, now() + interval '60 days' from auth.users where email = 'review@elevateandthrive.uk'
    on conflict (user_id) do update set store_expires_at = excluded.store_expires_at;

A reviewer cannot read email codes, so give the account a password
(Supabase > Authentication > Users > the user > Reset password, or create the
user there with a password) and put the email and password in the review
notes. The app's sign-in screen has "I have a password" for this.

## Store listing (draft)

* Name: Live Desk: NHS Market Intel
* Subtitle (Apple, 30 chars): Medtech and NHS news, hourly
* Category: Business. Age rating: 4+.
* Description:

  Live Desk is the UK medical sales professional's view of what changed in
  the NHS market today. MHRA alerts and recalls, supply and availability
  notices with their action deadlines, NICE guidance, tenders, NHS England and
  DHSC news, and the industry wire, refreshed every hour and ranked for
  usefulness, not volume.

  Pick the specialities you sell into and get an alert at 9am, 12 noon and
  4pm, only when something new lands.

  Medical Sales Intelligence Hub members: the app is included in your
  membership. Connect it once and you're in.

  Subscriptions renew automatically unless cancelled at least 24 hours before
  the end of the period. Manage them in your store account settings.

* Keywords (Apple, 100 chars): medical sales,NHS,medtech,MHRA,NICE,tenders,recalls,pharma,procurement,ICB
* Privacy URL: https://medsalesintelligencehub.co.uk/live-desk-app-privacy/
* Support URL: https://medsalesintelligencehub.co.uk/live-desk-app-support/
* Apple privacy labels: Email address and User ID (app functionality, linked
  to the user, not used for tracking); Purchase history (app functionality).
  No tracking.
