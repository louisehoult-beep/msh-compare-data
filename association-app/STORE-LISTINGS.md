# Industry Nurses: store listings (draft, 28/10/2026)

Association for Industry Professional Nurses member app. Bundle id and package `uk.co.medsalesintelligencehub.industrynurses`. Nothing here is submitted.

## Name rule (learned from Live Desk, Google rejection 23/10)
The store name, the home-screen name and the icon must match what the build ships. The build's home-screen name is **Industry Nurses** (`capacitor.config.json`, Info.plist, `strings.xml`) and the icon is the gold plus-in-circle on navy (`assets/icon-only.png`). So the store name is the same, and the full Association name goes in the subtitle and description. Do not rename the store listing without a new build.

## Apple (App Store Connect)
- Name (30 max): `Industry Nurses`
- Subtitle (30 max): `Association for Industry Nurses` (31: too long). Use `Nurses working in industry` (26).
- Promotional text (170): `Free for nurses in industry and nurses moving into industry: events, jobs, community and resources from the Association for Industry Professional Nurses.`
- Category: Medical (secondary: Business). Age rating: answer user-generated content yes (moderated, reporting and blocking).
- Price: Free. No in-app purchases. Territories: UK only to start.
- Keywords (100): `nurse,industry,medtech,NMC,clinical,specialist,careers,events,community,pharma,device`
- Support URL: `https://medsalesintelligencehub.co.uk/association-for-industry-professional-nurses/`
- Privacy URL: `https://medsalesintelligencehub.co.uk/privacy-policy/#industry-nurses-app` (section published 31/10/2026).
- Marketing URL: same as support.

## Google Play
- App name (30): `Industry Nurses`
- Short description (80): `Events, jobs and community for nurses working in industry.`
- Category: Medical. Free, no ads, no in-app purchases. Countries: UK.
- Content rating: user-generated content (moderated; report and block). Data safety: name, email, NMC PIN (required at sign-up, admin-only), role, employer type, region, posts, job link opens; encrypted in transit; deletion in app.
- Icon: 512x512 made from `assets/icon-only.png` (`sips -z 512 512`), identical to the shipped icon.

## Full description (both stores)
Industry Nurses is the member app of the Association for Industry Professional Nurses, for nurses who work in industry (medical device, pharma, diagnostics, clinical education, clinical affairs, clinical specialist and sales roles) and nurses who want to move into it. Membership is free.

What you can do:
- Find events, including association events and conferences, and add dated ones to your calendar. Where a date is not confirmed, the app says so.
- See jobs from named employers, each linking to the employer's own listing.
- Join moderated community channels, reply, report posts and block members.
- Choose whether to appear in the member directory. Your profile is private until you opt in.
- Read guides and resources, with links to the clinical section of the Medical Sales Hub.
- Export your data or delete your account inside the app.

Joining: sign up with your email, name, role and employer type. You enter your Nursing and Midwifery Council (NMC) PIN; the Association checks it against the NMC register before approving your membership. Your PIN is never shown to other members, employers or recruiters. You sign in with a 6-digit code sent to your email.

The Association is not an NHS or regulator service and gives no clinical or legal advice.

## Review notes (both stores)
Sign in with "I have a password": user `review@elevateandthrive.uk`, password in Keychain `LIVEDESK_REVIEWER_PASSWORD` (Lou types it into App Review Information and Play App access; Claude may not). That account has an approved member row. User-generated content controls: report and block on every post and member, moderation queue in the admin area, in-app account deletion under Profile. No payments, no tracking, no ads.

## Privacy: section published 31/10/2026 on page 433 (anchor `#industry-nurses-app`)
History: the live privacy policy (page 433) has no section for this app, and both stores need one. Add a section headed "Industry Nurses app" to page 433, then use `https://medsalesintelligencehub.co.uk/privacy-policy/#industry-nurses-app` as the privacy URL. Content to cover, taken from what the app stores: name, email, role category, employer type, region and speciality; NMC PIN (required at sign-up, used only to check the register, never shown to others); posts and replies; opt-in directory profile; link clicks on jobs; admin can see everything on your profile; export and delete in the app; contact `louisehoult@elevateandthrive.uk`. Check the exact fields against `supabase/migrations/20261026180000_industry_nurses_app.sql` and the lawful basis against the existing Hub section before publishing.

## Still needed before submitting
1. Privacy section: DONE 31/10/2026 (page 433, anchor checked live).
2. Store screenshots (iPhone 6.7" and Android phone) rendered from the app's own screens, as done for Live Desk.
3. Apple screen recording of sign-in, events, jobs, community report and block, delete account, if Apple asks (it did for Live Desk).
4. Create the store apps, Codemagic group `industrynurses`, then tag `ain-v1.0.0` (steps in `DEPLOY.md`).
5. Hold submission until Live Desk 1.0 and 1.0.2 clear review (Lou's call).
