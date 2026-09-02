# Hub Verification Standard

**Mirrored into this repo 02/09/2026** so the cloud trust-profile batch routine can read it
(cloud sessions cannot reach OneDrive). The OneDrive original at
`02-Elevate-and-Thrive/HUB-VERIFICATION-STANDARD.md` stays canonical for the whole Hub, of
which trust profiles are one small part — re-copy here after any change there.

**Applies to:** everything published under the Medical Sales Hub or Elevate & Thrive name — the Rep's Briefing, the Hub teaser, Live Desk panels, trackers, LinkedIn posts, and any Hub page.

**Status:** binding on every scheduled task and every manual send. Created 21/07/2026 after a factual error reached subscribers.

---

## What went wrong, and why the rules below are shaped this way

On 20 July 2026 the Rep's Briefing told 19 subscribers that NHS SBS framework **SBS10142 expired on 1 August 2026** and that "this week is the last realistic window" to act. The framework actually runs to **1 August 2027**. The claim had been written into a scheduled-task instruction file weeks earlier and copied forward every run without ever being re-checked.

The same edition carried six contract links that did not resolve, a supplier count that did not match the live page, and a footer link to a preferences page that has never existed.

Four failure modes, all preventable:

1. **A fact was stored in an instruction file.** Instructions do not expire; facts do.
2. **Nothing mechanically checked the output before it sent.**
3. **Urgency was attached to an unverified claim.** A wrong fact is embarrassing; a wrong fact with "act now" attached costs credibility.
4. **Links were published without being opened.**

---

## The rules

### 1. No fact lives in an instruction file

Task files may contain *methods* — where to look, how to format, which group to send to. They must not contain *facts with a shelf life*: expiry dates, prices, counts, framework terms, personnel.

If a task needs such a fact, it fetches it at run time and cites where it came from. Anything already embedded gets replaced with a fetch instruction.

**Exception:** stable identifiers (plan IDs, group IDs, page IDs, API endpoints) are configuration, not facts. Those belong in the task file.

### 2. Every claim carries its source, in the same breath

No figure, date, deadline or attribution appears without a link within the same bullet or paragraph. If it cannot be sourced, it does not go in. "It was in the store" is not a source — the store is a cache of someone else's page, and the page is the authority.

### 3. Deadlines and urgency get a higher bar

Any claim that something **expires, closes, or must be acted on by a date** must be verified against the owning organisation's own page *on the day of publication* — not from the store, not from a previous edition, not from memory.

Quote the source's own wording. If NHS SBS says "02 August 2021 – 01 August 2027", say that, not a paraphrase.

Never write "under two weeks", "last chance" or "act now" unless the underlying date has been verified that day.

### 4. Every link is opened before it ships

Run `hub_verify.py` (below). Any FAIL blocks the send. A link that redirects to a sign-in page, an error page or a search page is a dead link, not a working one.

### 5. Counts come from the live page

"98 verified suppliers" must match what the Supplier Directory actually displays today. Derived numbers drift as content grows; re-read the page rather than trusting a curated note.

### 6. Two sources that agree are not two sources

If a check merely repeats the claim being checked, it has verified nothing. When confirming something load-bearing, go to the owning organisation's own page and quote it. This applies to verification subagents especially — they anchor on the claim they are given.

### 7. Corrections are published, not quietly patched

If something wrong has gone to subscribers, the next edition says so plainly and briefly. Silent edits to the archive are not enough.

### 8. One error found means a HUB-WIDE SWEEP for the same error — every time, no exceptions

**Added 06/08/2026 by Lou, after the SBS10142 date came back.**

Finding and fixing one instance is **half** the job. The moment any factual error is found, the next
action — before moving on, before reporting it fixed — is to **search every Hub page for the same
error and correct every copy**.

This rule exists because the exact incident at the top of this document happened **twice**. On
20/07/2026 the Rep's Briefing told subscribers SBS10142 expired 01 Aug 2026 when it runs to 01 Aug
2027. The fact was removed from the scheduled-task instruction file and this Standard was written —
but **nobody swept the pages that had already copied the claim**. It sat on Rep Briefings and Clinical
Pathways for another seventeen days, through **ten separate edits** that added 225,000 characters,
and was only found on 06/08/2026 because Lou happened to ask an unrelated question about wound care.

Root rule 18 already says a wrong fact rarely lives in one place. That was not enough, because it is a
principle with no trigger. This is the trigger.

**The sweep, as an action:**

1. Take the **wrong value itself** (`01 Aug 2026`), not the topic. Search on the string.
2. Search **every Hub page**, not the one it was reported on. Rep Briefings and Clinical Pathways are
   the biggest carriers — 575,000 and 329,000 characters — and neither is checked by anything.
3. Check each hit **in context** before changing it: the same string may be correct elsewhere for a
   different framework. Confirm the hit belongs to the thing that is wrong.
4. **Correct every instance in the same pass.** Not a follow-up task, not a note in OUTSTANDING.
5. **Verify after saving** — count the occurrences of the wrong value and confirm it is zero.
6. Record in OUTSTANDING **how many instances were found and on which pages**, so a recurrence is
   visible as a recurrence.

**A fix is not finished until the sweep has run and the count is zero.**

---

### 9. Source discipline — verify at build time, never with a caveat

Moved here from root CLAUDE.md rule 16 on 11/08/2026: it was 2,700 characters of publishing detail
sitting in the constitution, restating rules 2, 11, 12 and 14. The rule is unchanged.

Every fact published to the Hub, the Rep's Briefing, or any member-facing asset is verified as it is
written, not flagged for the reader to check later. "Never invent" is not the same as "never repeat
unverified" — this covers the second.

- **Facts about a named organisation** (site/hospital counts, footprint, ownership, structure, dates)
  come from that organisation's own website, regulator record or company filing, **fetched this run**.
  A web-search summary is a pointer to a source, never the source itself.
- **A statistic credited to a named body** (PHIN, NHS England, NICE, DHSC, MHRA, GIRFT) must appear
  verbatim in that body's own publication. If it appears only in trade coverage, attribute it to that
  outlet by name or drop it. Never let trade press inherit the authority of the body it reports on.
- **Conflicting sources mean fetch the primary source** — never average, round or hedge. Never write
  "around X" to paper over an unresolved conflict; a hedge may not even contain the true value.
- **Never fill a gap with an assumption.** If a source omits geography, scope or date, fetch it or omit
  the claim. State England, GB or UK explicitly; never write "nationwide".
- **Trade press is legitimate for events** (launches, M&A, partnerships, appointments, awards) where it
  is the reporting outlet. It is not a source for an organisation's own structural facts.
- **Conference/event listings are a carve-out** (Lou, 23/07/2026). An event advertised on LinkedIn or on
  the organiser's own channel is a trusted source for that event's own date, venue and format — add it to
  the Conferences calendar and publish. The one guardrail: if the date **conflicts** with another source,
  pause and ask Lou. Scoped to event date/venue/format only; it does not touch statistics, NHS policy or
  an organisation's structural facts. You still need the datum itself — if the date isn't in what Lou
  supplied and isn't on a public organiser page, ask her.
- The house caveat "verify against the primary source before using in a pitch" exists so a sales person
  re-checks against their own account context. It **never** discharges the duty to verify before publishing.
- Applies equally to drafts: drafts get published between runs, so an unverified figure reaches subscribers.
- **Wiring an automated source (`sources.py`) is a publish, not a fetch test.** HTTP 200 + parses proves
  the URL works; it proves nothing about whether the URL is the *right scope* for the page it feeds. Added
  26/08/2026 after `hse_msd_statistics` was wired to HSE's GB-wide overview page (511,000 workers, all
  sectors) while the live page it feeds already cited HSE's sector-specific report (52,000 workers, human
  health and social work) — caught before it reached a briefing, not after. Before adding any statistics
  or regulatory source: read what the target page(s) already cite, and confirm the new source's scope
  (geography, sector, population) matches. A same-topic source at the wrong scope is a wrong number with a
  real URL behind it — worse than an obviously invented one, because it passes the "has a source" check.

- **One error found means a HUB-WIDE SWEEP for the same error — every time, no exceptions.** Rule 8 above
  applies to source-wiring too: finding one scope-mismatched source is a reason to check every other
  regulatory/statistics entry in `sources.py` for the same class of mistake (a GB-wide figure feeding a
  sector- or category-specific page), not just fix the one found. Not yet done for the existing registry —
  logged as an open item, not swept silently.

### 10. One name per company — resolve it before you publish it

Added 14/08/2026. The same company reaches us under a different name from every source: NHS Supply
Chain writes "Stryker UK Limited", Find a Tender writes "STRYKER UK LTD", the trade press writes
"Stryker", the company's own site writes "Stryker UK". Unresolved, that publishes one company as two,
splits its frameworks across two rows, and returns "no results" to a member who searched the name the
company actually uses. It also quietly breaks rule 8's completeness test — a competitor set that lists
the same company twice under two spellings is not the whole picture.

- **Every company name published to the Hub, the Rep's Briefing or any member-facing asset is resolved
  through the alias registry first**: `Hub/company-aliases/company_alias.py`. Exit 0 = resolved,
  1 = unresolved, 2 = ambiguous.

  ```bash
  python3 "Hub/company-aliases/company_alias.py" resolve "STRYKER UK LTD"
  ```

- **A name that will not resolve does not publish.** It is a question, not a guess. Confirm which
  company it is against Companies House or the company's own site, record the alias, then publish.
- **Never merge two names because they look alike.** No fuzzy or substring matching, ever — that is how
  homonyms get merged, and a merged homonym is a false statement about a real company published under
  the Hub's name. "Pentax Medical UK Limited" is not "Pentax UK Limited". The tool prints similar-looking
  names as a hint for a person; they are never an answer.
- **Two different real companies can share a name, and those stay ambiguous.** GS MEDICAL HEALTHCARE
  LTD (10425778, Selby) sits inside GBUK; GS MEDICAL LIMITED (NI659208, Antrim) does not. An ambiguous
  name is published with the distinguishing detail — full registered name, or name plus company number
  — or not at all. Declared ambiguities carry their evidence, so a new accidental collision still fails.
- **Record the alias where it survives.** For a Hub supplier that means its record in
  `supplier-seed.json`, because the nightly rebuild regenerates the index from the seed and throws away
  anything written only to the index. The overlay is for companies not in the seed.

Full process: `Process flows for all brands/company-alias-check-process.md`.

### 11. A company number is a claim, and a name search is not evidence for it

Added 14/08/2026. Rule 10 gets the name right. This one gets the **company** right, which is a
different failure and a worse one: a wrong company number does not look wrong. It publishes a real
company's turnover, employee count, accounts and filing history under another company's name, on a
paid product, and every figure on the page is internally consistent.

- **A company number attached to a supplier must come from a recorded source** — the number written
  in the supplier's own material, its website registration line, or a procurement listing that names
  the legal entity. **A name search on Companies House is not one of those.** Matching "Genmed" to
  the first Companies House result called Genmed is the same class of reasoning as matching two
  names because they look alike, and rule 10 already forbids that.
- **Anything derived from an unconfirmed number is unconfirmed too.** Do not chain: two records
  sharing a `probable` number is not evidence they are the same company, because the number may be
  wrong on both. Two Hub records were matched to SOLVENTUM IRELAND LIMITED, a Belfast mail-order
  company incorporated 24/02/2026; treating that shared number as proof would have merged two real
  suppliers into one wrong one.
- **These invariants must pass before anything company-level publishes:**

  ```bash
  python3 "Hub/company-aliases/match_check.py"
  ```

  Exit 0 = clean, 1 = findings. It fails on a company that trades in something else, a registered
  name that resolves to a company already settled as different, a record whose own `matchedOn`
  admits the name does not correspond, two supplier records sharing one number, and a company
  **incorporated after a framework the Hub says it holds** — a company cannot win a framework
  before it exists.
- **It deliberately does not fail on `probable` alone.** 380 of 598 records carry it; a gate that
  fails 380 times is a gate nobody runs. Reducing that number is the route-2 confirmation work in
  `msh-compare-data`. This gate catches the ones already provably wrong.
- **Publishing nothing beats publishing the wrong company.** Where the right number cannot be
  established, the record carries no number and the company report shows no financials. Do not
  guess which company it is — Genmed's correct entity is still unestablished, and that is the
  correct state to be in until somebody sources it.

### 12. Report the fact, not a verdict on it — and a gap is a gap, never a red flag

Added 26/08/2026, by Lou, after Mediq Healthcare UK's Company Intelligence Report carried an amber
"IDENTITY NOT CONFIRMED" box — wrong, its identity was in fact confirmable — sitting next to a
prose discussion of restructuring costs, rising borrowing and a fresh equity injection. Neither
fact was false on its own. Together, an unconfirmed-identity flag beside loss-and-debt language
reads as "something's wrong here", and that reading would have been unfair: the company is mid an
owner-funded rebuild, not in difficulty, and its parent put £14m of fresh cash in eight months
after the loss the page was flagging. A member reading that page would not have the full picture,
and nobody at Mediq — or at any supplier — should ever have reason to think the Hub was talking
about them negatively.

**Every company report is written so a supplier could read it about themselves and find it fair.**
That does not mean omitting a real figure — turnover, a loss, a borrowing increase, an acquisition
mid-integration are all facts this Hub exists to surface accurately. It means three things about
*how* they are written:

- **State the number. Do not verdict it.** "Operating loss of £4.5m, including £6.2m of one-off
  restructuring costs" is a fact. "Barely making money" and "the board most needs fixed" are a
  verdict — Claude's or a curator's own judgement dressed as description — and root rule 2 already
  says never to invent; a verdict on a company's health is not something this Hub was asked to
  invent either. If a figure needs context to be read fairly (a short accounting period, a
  restructuring charge, a deliberate investment phase), give the context in the same breath, from
  the company's own filing or strategic report — not a caveat bolted on afterwards.
- **A gap in published information is a gap, not a signal.** "Accounts not yet filed", "turnover
  not extracted from a scanned PDF", "identity not yet confirmed against a recorded source" all mean
  exactly one thing: **more information is needed to see the full picture**, and that is the phrase
  to use. None of them mean, and must never imply, that something is being hidden or that the
  company is in difficulty. Where a gap sits beside other financial figures on the same record,
  say plainly that the gap does not change how those figures should be read.
- **Get the identity and match status right before anything else renders.** An "IDENTITY NOT
  CONFIRMED" box, or any other gap-flagging language, is itself a claim under rule 11 — it must be
  checked against the same recorded-source bar before it is shown, not left at its last-set value
  while the rest of the record moves on. The Mediq incident was exactly this: the company's own
  website footer had confirmed the number, but the financials record still carried the generic
  `probable` / name-search caveat text from before that was checked.

**The one-error sweep (rule 8) applies here too.** Any company whose deep dive discusses a loss,
an operating loss, a pre-tax loss, net liabilities or going concern language is checked for the
same conflict: confirm its `matchConfidence` is `confirmed` in `company-financials.json`, and read
the surrounding prose for a verdict rather than a fact. Run this after any new deep dive that
touches a loss-making or debt-carrying period, before it publishes:

```bash
python3 -c "
import json
seed = json.load(open('Medical-Sales-Hub/Website/msh-compare-data/data/supplier-seed.json'))
fin = json.load(open('Medical-Sales-Hub/Website/msh-compare-data/data/company-financials.json'))['companies']
flags = ('operating loss','loss before tax','loss for the','pre-tax loss','net liabilities','going concern')
for s in seed['suppliers']:
    dd = s.get('deepDive')
    if dd and any(w in json.dumps(dd).lower() for w in flags):
        print(s['name'], '->', (fin.get(s['name']) or {}).get('matchConfidence'))
"
```

Every name it prints should read `confirmed`. Anything else is checked against a recorded source
(rule 11) before the record is left live.

---

## The mechanical gate

`Medical Sales Hub/cloud-pipeline/hub_verify.py`

```bash
python3 cloud-pipeline/hub_verify.py "Hub Documents/reps-briefing-YYYY-MM-DD.md"
```

Exit code 0 = safe to send. Exit code 1 = do not send.

It checks that every URL resolves, that deadline and urgency language sits near a source link, that figures are sourced, and that no URL looks truncated. It treats 401/403/429 as "bot-blocked, check by hand" rather than broken, and treats a redirect to `/syserror`, `/notfound`, `/signedout` or a login page as a hard failure.

**This runs before every send. No exceptions, including manual ones.**

---

## Authoritative sources for contract awards and tenders

Verified working 21/07/2026.

### Find a Tender — above-threshold, UK statutory

- **API:** `https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages`
- **Parameters:** `stages=planning|tender|award`, `updatedFrom`/`updatedTo` (`YYYY-MM-DDTHH:MM:SS`), `limit` (max 100), `cursor`
- **Notice URL:** `https://www.find-tender.service.gov.uk/Notice/{id}` where `{id}` is the release `id` in the form `nnnnnn-yyyy`
- Rate-limited: honour the `Retry-After` header on 429.

### Contracts Finder — below-threshold and sub-£139k

- **API:** `https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search`
- **Notice URL:** `https://www.contractsfinder.service.gov.uk/Notice/{GUID}`

  ⚠️ **This is what broke on 20/07/2026.** The GUID is taken from the release **`id`** field with its trailing `-NNNNNN` suffix removed. It is **not** the `ocid`.

  ```
  id    "93c0e638-8aa1-4ba6-94bb-549c8210a64d-901576"
        → /Notice/93c0e638-8aa1-4ba6-94bb-549c8210a64d   ✅ resolves

  ocid  "ocds-b5fd17-4f4d84db-a23a-46b5-bf55-45399efa95cb"
        → /Notice/4f4d84db-a23a-46b5-bf55-45399efa95cb   ❌ 404
  ```

  Note the capital **N** in `/Notice/`. Lowercase `/notice/` redirects to an error page.

### NHS Supply Chain — its own awarded frameworks

- **Awarded frameworks (contract launch briefs):** `https://www.supplychain.nhs.uk/product-information/contract-launch-briefs/` — A–Z, 40 per page, each with a per-framework page giving awarded suppliers, contract type (New Contract / Contract Extension) and dates.
- **Forward pipeline:** `https://www.supplychain.nhs.uk/savings/procurement-calendar/`
- HTML only, no API, but official and the authority for NHSSC's own agreements.

### NHS Shared Business Services — its own frameworks

- `https://www.sbs.nhs.uk/services/framework-agreements/` — each framework page carries a "What dates is the framework agreement active?" section. **That section is the authority on expiry.** Nothing else is.

### Other

- NHS England tenders increasingly route through **Atamis (Health Family eCommercial System)** — worth monitoring as a source we do not yet cover.

---

## Known member-facing defects (open at 21/07/2026)

| Defect | Impact | Status |
|---|---|---|
| `/medical-sales-hub/preferences/` returns 404 | Linked in every Rep's Briefing footer as the way to tune the briefing or request intelligence. This is why the "Intel Requests — to verify" group is empty and no `info_request` field is ever populated — the feedback loop has never worked. | Needs a decision: build the page, or point the CTA at a reply-to. |
| Live Award Tracker shows 6 rows; local `Website/awards.html` has 10, with different entries | The weekly Step 2b edit is not reaching the live page. Members see a different, staler tracker than the one being maintained. | Needs a decision on which dataset is authoritative. |
| Live Desk NICE panel renders NICE site navigation ("Published", "In consultation", "In development") instead of guidance items | Six of eight rows in that panel are not intelligence. | Scraper selector needs fixing. |
