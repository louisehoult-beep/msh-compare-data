# Putting the Association app online and into the stores

State on 26/10/2026: code, Docker image, Fly.io config, phone-app projects (ios/, android/) and Codemagic workflows are written and tested (11 API tests pass). Nothing is hosted or submitted yet. Native builds have not been run: this Mac has no full Xcode, so Codemagic does the first iOS and Android build, as it does for Live Desk.

Cost (checked 26/10/2026): Fly.io smallest machine $2.19 a month plus 1 GB volume $0.15 a month; Resend free plan (100 emails a day, 3,000 a month). Apple and Google accounts already paid.

## 1. Host the server (Fly.io)

```bash
brew install flyctl
fly auth login                      # needs the Fly.io account and a card
cd association-app
fly launch --copy-config --no-deploy
fly volumes create ain_data --size 1 --region lhr
fly secrets set ADMIN_EMAILS=louisehoult@elevateandthrive.uk \
  RESEND_API_KEY=... REVIEWER_EMAIL=reviewer@elevateandthrive.uk REVIEWER_CODE=<6 digits>
fly deploy
fly certs add app.medsalesintelligencehub.co.uk   # then add the DNS record Fly shows
```

`fly.toml` already sets the address, region, volume and email sender.

## 2. Sign-in emails (Resend)

Create a Resend account, add `medsalesintelligencehub.co.uk` as a sending domain, add the DNS records it shows, and create an API key (the `RESEND_API_KEY` above). Until then the app prints sign-in links in the server log only.

## 3. Phone apps

1. App Store Connect: new app, bundle id `uk.co.medsalesintelligencehub.industrynurses`, name "Industry Nurses". Note its numeric Apple ID.
2. Play Console: new app, package `uk.co.medsalesintelligencehub.industrynurses`. Create an upload keystore in Codemagic named `ain_upload`.
3. Codemagic: add group `industrynurses` with `APP_STORE_APPLE_ID`.
4. Tag a release: `git tag ain-v1.0.0 && git push origin ain-v1.0.0`. Codemagic builds, signs and uploads to TestFlight and Play internal testing.
5. Store review needs: the reviewer email and code above in the "Sign in" review notes, a screen recording for Apple, and a store name, icon and description that match the app (Live Desk was rejected by Google for a mismatch on 23/10).

Review points already handled in the app: reporting and blocking of posts and members, in-app account deletion, terms and privacy links on the join form, no payments, no tracking.
