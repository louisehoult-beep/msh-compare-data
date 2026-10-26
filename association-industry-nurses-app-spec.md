# Association for Industry Professional Nurses: App Spec

Status: draft v1, 26/10/2026. Not built. Nothing here is a commitment to a launch date.

## 1. Purpose

A member app for nurses working in industry (medical device, pharma, diagnostics, clinical education, clinical affairs, sales and clinical specialist roles), and for nurses moving into industry. It makes the Association's value usable day to day: community, career support, event access and professional standing.

Home today: the Association page (WordPress 5878) and conferences page (5988) on medsalesintelligencehub.co.uk. The app extends those; it does not replace them.

## 2. Users

| Persona | Need |
|---|---|
| Industry nurse (member) | Peers, jobs, events, a voice on professional issues |
| Aspiring industry nurse (NHS, free tier) | Pathway guidance, mentoring, interview prep |
| Employer or recruiter (partner) | Reach nurses, post roles, sponsor events |
| Association admin (Lou) | Approve members, publish content, moderate, see numbers |

Market size is unknown: no official UK count of nurses in industry exists (checked 21/10/2026). The app records self-declared role and employer type at sign-up so the Association builds its own count.

## 3. MVP scope (v1)

1. **Sign-up and verification.** Email plus name, NMC PIN entered by the member, role category, employer type (company, agency, consultancy, between roles). Admin approves. Verification is a manual check against the NMC register; the app does not store anything beyond the PIN and the check date.
2. **Member directory.** Opt-in profile: name, role, speciality, region, "open to mentoring / being mentored". Private by default.
3. **Community feed.** Topic channels (moving into industry, clinical education, compliance and codes of practice, regional). Posts, replies, reports. Moderated.
4. **Events.** Association events plus the external conference listing (NAMDET, ABHI, ABPI and similar), reading the same source data as page 5988. Save, calendar add, reminders. Undated events show "date not confirmed", never a guess.
5. **Jobs board.** Partner-posted roles, saved search and alerts. Every listing needs a named employer and a source link.
6. **Resources library.** Guides, templates, recorded talks. Linked to the Medical Sales Hub clinical section where relevant (`medsalesintelligencehub.co.uk/medical-sales-hub/clinical/`).
7. **Notifications.** Push and email, per-topic opt-out.

## 4. Later (v2+)

- Mentor matching and booking.
- Employer profiles and sponsored content.
- Programme accreditation (not in v1, later date, Lou 26/10/2026): the Association can offer accreditation of programmes submitted to it for review. Would need an application and review workflow in the admin area (submission, criteria, reviewer decision, certificate, public register of accredited programmes), plus published criteria and a review panel agreed first. No accreditation claim goes in the app until that process exists.
- CPD log: personal activity record with PDF export, only after accreditation wording is settled.
- Ticketed events and partner benefits. Membership itself stays free.
- Regional meet-ups with RSVP.
- Surveys that produce the Association's own published workforce figures.
- Hub single sign-on bridge (see section 7).

## 5. Key flows

**Join:** landing → create account → NMC PIN and role → pending screen → admin approves → welcome email and first-run checklist (complete profile, join two channels, save an event).

**Find a role:** Jobs → filter (speciality, region, remote, seniority) → role detail → apply on employer's site → app logs the click for the partner report.

**Save an event:** Events → event detail (source link, "date not confirmed" if undated) → save → add to calendar → reminder.

## 6. Content and compliance rules

- Facts only from a named source checked in the session. "Not verified" where unverifiable.
- No patient-identifiable information in posts; post-time warning and a report route.
- Commercial promotion only from approved partners and labelled as such.
- UK GDPR: lawful basis recorded, data export and delete on request, NMC PIN treated as personal data, retention period set in the privacy notice.
- Accessibility: WCAG 2.2 AA minimum; contrast per brand guide.
- Abbreviations spelled out at first use in all member-facing copy.
- No prices on corporate or partner packages ("email for pricing").

## 7. Architecture

**Recommendation: build a progressive web app first**, wrapped for the app stores only if members ask for it. Reasons: one codebase, no store review delay, installable, push supported on current iOS and Android.

| Layer | Choice |
|---|---|
| Front end | React with TypeScript, PWA |
| Back end | Managed backend (Supabase or Firebase equivalent), row-level security |
| Auth | Email magic link; optional sign-in bridge to the Hub and training logins, never crossing the member types (training members never go to the Hub login and the reverse) |
| Content | Events and resources read from WordPress through its REST interface, so Lou keeps editing in one place |
| Payments | None. Membership is free. |
| Email | MailerLite (already in use) |
| Hosting | Same domain as the existing Association page (5878): `medsalesintelligencehub.co.uk`. The app is a sibling of the Association and conferences pages (5988), reached from the Association page. Association page verified live 26/10/2026 at `/association-for-industry-professional-nurses/`; proposed app path `/association-for-industry-professional-nurses/app/` (or a sibling page such as `/association-app/`), to be chosen at build. Association pages stay public and parent 0, outside the Hub members area (parent 675). |

## 8. Data model (core)

- Member: id, name, email, NMC PIN, verified_at, role_category, employer_type, speciality, region, visibility, status
- Channel, Post, Reply, Report
- Event: id, title, organiser, start (nullable), end, venue (nullable), source_url, verified_at
- Job: id, employer, title, location, source_url, expires_at, posted_by
- Resource: id, title, type, wp_post_id, access_level
- Partner: id, name, tier, contact

## 9. Admin

Approval queue, moderation queue, content publishing shortcuts, partner management, weekly numbers (joins, active members, event saves, job clicks) and a published-figures view that only counts self-declared, member-consented data.

## 10. Success measures

Set targets with Lou after the first 90 days of real data. Starting measures: verified members, weekly active members, share who complete profiles, event saves, job click-throughs, partner renewals. No targets are set here, because none have a basis yet.

## 11. Risks

| Risk | Mitigation |
|---|---|
| Empty community at launch | Seed channels with Lou's CRM contacts and existing Association pages; launch with events and jobs, which have value without a crowd |
| Verification workload | Manual approval, batch weekly; automate only if volume demands |
| Employer-conflict (a member's employer sees posts) | Private by default; channel rules |
| Scope creep | MVP list in section 3 is the cut line |

## 12. Build plan

1. Wireframes for join, feed, events, jobs (1 week).
2. Backend, auth, directory, events from WordPress (2 weeks).
3. Feed, moderation, jobs, notifications (2 weeks).
4. Admin screens and polish (1 week).
5. Closed beta with 20 to 30 members, then fix and open.

Estimates are planning guesses, not commitments.

## 13. Open decisions (need Lou)

- Which partners to approach first for the jobs board.

Decided 26/10/2026 (Lou): the app lives on the same domain as the Association page; membership is free; no CPD or accreditation in v1 (accreditation of submitted programmes comes later).
