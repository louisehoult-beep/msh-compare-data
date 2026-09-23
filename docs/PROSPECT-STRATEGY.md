# Prospecting without LinkedIn or Clay

**Written 22/09/2026.** Method, not customer data. This repo is public, so nothing
here names a prospect; the lists live in `tmp/prospects/` (gitignored) and are
built on demand by `scripts/build_prospect_lists.py`.

## The idea

LinkedIn and Clay find people by title. That gives a name and no reason to reply.
The Hub already captures, daily, the events that make a company need what Elevate
and Thrive sells: a fresh framework award, a rival's product delisted, a vacancy on
its own careers page, a set of accounts showing growth. Those are triggers, they
are public, and they are verifiable by the person receiving the message.

So the prospect list is built from triggers, one list per product, and the first
touch is the intelligence itself, not a pitch. The recipient gets a fact about
their own market that they can check in thirty seconds, with the Hub page that
holds the rest. That is what earns a reply.

The builder reads only files this repo already verifies:
`supplier-index.json`, `company-financials.json`, `supplier-careers.json`,
`framework-awards.json`, `compare-issues.json`, `mhra-alerts.json`,
`company-press.json`, `hub-calendar.json` and `speciality-label-map.json`.
Every row carries the evidence that put it there.

```
python3 scripts/build_prospect_lists.py            # writes tmp/prospects/*.csv + summary.md
python3 scripts/build_prospect_lists.py --days 60  # tighter award and press window
```

## Product 1: the Hub (medsalesintelligencehub.co.uk)

**Ideal fit.** A UK supplier with 10 to 249 employees, named on at least one NHS
Supply Chain framework, with a live trigger in the last 90 days. Big enough to
have field reps, too small to have anyone whose job is market intelligence. The
director on the Companies House register is usually the person who signs.

**How they are found.** `hub-team-prospects.csv`. Score, with the evidence in the
`triggers` column:

* Fresh Find a Tender award naming the company (+3).
* A rival's live supply gap or delisting on the Compare tab in a shared speciality (+2).
* Open UK commercial roles on the company's own careers page (+2).
* Size band 10 to 249 (+2), under 10 (+1), 250 plus (0).
* Turnover up 10% or more on the last tagged accounts (+1).
* Corroborated press in the window (+1), MHRA alert in the speciality (+1).

A row needs a live trigger and a score of 5 or more. A framework place plus a
size band is a profile, not a reason to write this week.

**How they are reached.** The `lead_with` column names the Hub page that answers
the trigger, and `meet_at` names the next conference in their speciality from the
Hub calendar.

* Competitor gap: send the Compare tab line for that speciality. "Kimal's BioFlo
  PICCs are delisted until December; three trusts on your patch use them. The
  Compare tab has the notice and the switching angle."
* Fresh award: send Meeting Prep for the awarding trust. "You were named on the
  cannula framework on 18/08. Here is the waiting-list and pressure profile for
  the first trust your reps should walk into."
* Conference: print the speciality's live issues on one page and hand it over at
  the stand. The rep on the stand is the user; the director at the back is the buyer.

Channels, in order: the company's own published sales or contact address with
the notice reference in the subject line; a letter to the registered office
addressed to the director named in `company-financials.json` (register facts,
lawful, and almost nobody does it); the stand. Never a LinkedIn message.

## Product 2: Medical Sales Training Programme

Two buyers, two lists.

**Employers.** `training-employers.csv`: companies advertising associate,
graduate, trainee or junior commercial roles in the UK today, read from their
own applicant tracking systems. The advert is the trigger; the offer is the new
hire's first ninety days. Reach the hiring manager through the same route as the
Hub list, timed to the advert closing.

**Candidates.** `training-candidate-intents.csv`: one row per live UK commercial
role at a Hub supplier. Each row is a search-intent page target
("Interviewing at Abbott for Associate Territory Manager: what they ask and
why"), built from the role record and the company's Interview Prep entry, and
retired when the advert closes. Candidates find it while preparing, which is the
only moment they are looking.

YouTube demand, measured with vidIQ on 22/09/2026 (global monthly searches,
competition out of 100):

| Search | Monthly | Competition |
|---|---|---|
| medical device sales | 10,515 (up 164% on baseline) | 26 |
| how to get into medical sales as a nurse | 4,621 | 7 |
| medical sales interview | 4,213 | 34 |
| how to get into medical device sales with no experience | 3,969 | 22 |
| new to medical device sales | 3,534 | 33 |

The two question searches are the programme's front door: low competition,
exactly the person the programme is for. One video each, answered from the Hub's
role guide, linking to the programme and to the intent pages.

## Product 3: Clinical Interview Playbook

**Ideal fit.** A clinician applying for a clinical specialist, clinical
application or nurse advisor role at a supplier.

**How they are found.** `playbook-prospects.csv`: live clinical-commercial roles
from suppliers' own careers pages. Each role is a cohort of clinicians preparing
for the same interview in the same fortnight.

**How they are reached.**

* Intent pages per live clinical role, as above, with the Playbook as the next step.
* The "how to get into medical sales as a nurse" video and its follow-ups.
* Professional societies already listed in `interview-prep.json` under `confs`
  (Society of Tissue Viability, Wounds UK and the rest). A twenty-minute
  "from clinic to commercial" slot at a society meeting reaches the exact audience
  without a single cold message.
* The existing MailerLite segment "C2C, All Members (KY + Direct)" (77
  subscribers, 47% open rate) for referrals: every member knows a colleague who
  is thinking about it.

## Product 4: Clinical to Commercial, licensed to recruiters

**The model, proven once.** A specialist recruiter licenses the Clinical to
Commercial package for its own candidates, for a year, as a flat fee. Kirkham
Young was the first. The candidates get the preparation; the recruiter gets
candidates who interview better and a reason for clinicians to register with
them rather than a rival. Commercial terms are kept out of this public file.

**Ideal fit.** A recruitment agency that places clinicians into first
commercial roles: clinical specialist, associate territory manager, nurse
advisor. Small enough that it has no training arm of its own, busy enough to
place a steady flow of clinicians each year. Second fit: an employer's talent
or early-careers team running a graduate or associate intake.

**How they are found.** No LinkedIn needed:

* The adverts. Agencies put their own name on the medical sales roles they
  advertise on public job boards. Every agency that has advertised a
  clinical-to-commercial role in the last three months is a prospect.
* The Recruitment and Employment Confederation member directory, filtered to
  healthcare and life sciences.
* The employers in `training-employers.csv`: a company running an associate
  intake is the second fit, and its careers page names who runs it.
* Referral. The first licensee knows its competitors better than any list does.

Not verified: how many agencies meet the fit today. The first job is to build
that list from the adverts and count it.

**How they are reached.** Lead with the outcome, not the course. "Your
clinicians arrive at interview knowing how the NHS buys, with a ninety-day plan
that names hospitals." Offer the recruiter a free look at the member area for
one candidate they are placing now, so the first proof is their own placement.
Naming Kirkham Young as the first licensee needs their permission first.

## What limits the lists today

* Careers coverage is thin: 5 companies with readable role records out of 90
  with a careers page, because 63 publish no structured roles and, until
  23/09/2026, SuccessFactors and Teamtailor boards were detect-only. The
  careers script now reads both by following the listing to each job page and
  taking that page's JobPosting record (the same evidence bar as the jsonld
  route; a link with no record behind it counts nothing). Seven suppliers on
  the 22/09 rows sat on those platforms. Not verified live: this was written
  offline against fixtures (`test_careers_jobpages.py`) because the build
  container cannot reach those hosts. The Tuesday careers run is the proof.
* Employee counts exist for 216 of 1,133 companies. A company with no count
  scores as "unknown" and is not penalised, so large groups appear alongside
  the target band. Read the size band before sending.
* The calendar bridge in the script maps Compare slugs to calendar slugs by
  hand. It is used only for `meet_at`, never to change a tag.

## Rules

* Give the fact first. One trigger, one page, one question. No deck.
* Say where the detail came from in the first message, as the Stakeholder Mapper
  already does for NHS contacts.
* Corporate addresses and registered offices only. No personal email, no LinkedIn
  automation, nothing scraped from a profile.
* Ten touches a week from the top of the Hub list, logged in the CRM Pipeline
  sheet. Rebuild the lists every Monday after the weekend refreshes.
