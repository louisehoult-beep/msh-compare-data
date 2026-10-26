# Putting the Association app online and into the stores

Hosting is Supabase (project `vbthumugbzyqndirmyns`, shared with Live Desk). Fly.io and Resend are not used.

## Done 26/10/2026

* Migration `20261026180000_industry_nurses_app.sql` applied; function `industrynurses` deployed with `--no-verify-jwt` (public routes and sign-up run before anyone is signed in; the function checks the user token itself); secret `ADMIN_EMAILS=louisehoult@elevateandthrive.uk` set.
* Checked live: `/api/options` and `/api/events` answer, `/api/channels` returns 401 without sign-in.

Redeploy after a change:

```bash
supabase db push
supabase functions deploy industrynurses --no-verify-jwt --project-ref vbthumugbzyqndirmyns
```

## Sign-in email

The code email uses the project's Supabase Auth email, the same as Live Desk (OTP on, template shows `{{ .Token }}`, custom SMTP before launch per the Live Desk README). Checked 26/10/2026: custom SMTP is on (Resend, sender noreply@elevateandthrive.uk, name Medical Sales Intelligence Hub), shared with Live Desk.

## Reviewer account (App Store and Play)

Done 26/10/2026: `review@elevateandthrive.uk` (the Live Desk reviewer auth user, password unchanged, already in the Live Desk review notes) has an approved `ain_members` row, so it signs in with "I have a password". Reuse the same email and password in this app's review notes.

## Phone apps

1. App Store Connect: new app, bundle id `uk.co.medsalesintelligencehub.industrynurses`, name "Industry Nurses". Note its numeric Apple ID.
2. Play Console: new app, package `uk.co.medsalesintelligencehub.industrynurses`. The Android build reuses the Live Desk upload keystore `livedesk_upload`.
3. Codemagic: group `industrynurses` with `APP_STORE_APPLE_ID`.
4. `git tag ain-v1.0.0 && git push origin ain-v1.0.0`. Codemagic runs the tests, builds, signs and uploads to TestFlight and Play internal testing.
5. Store review needs: reviewer login above, a screen recording for Apple, and a store name, icon and description that match the app (Google rejected Live Desk on 23/10 for a mismatch).

Review points already handled: reporting and blocking of posts and members, in-app account deletion, terms and privacy links on the join form, no payments, no tracking.
