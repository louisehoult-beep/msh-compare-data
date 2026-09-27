# Surgical Instruments framework — U.K. Medical Limited identity finding (27/09/2026)

## What was checked

Framework-coverage batch run picked **Surgical Instruments** (lowest-coverage STARTED
framework with real `Left`, per `docs/COVERAGE-LEDGER.md`: 26.0%, 17 left). Its three
genuinely actionable items (excluding the 14 `publishedElsewhere`/open-^o469 items):

1. **Steris IMS Ltd** — held, uncategorised. Its crawl (`healthcare.steris.com`, sitemap-derived)
   returns division/category labels as product names ("Central Sterile Services Department
   Accessories", "Electrosurgical Products", etc.) — a textbook match for the standing
   `nav-labels-are-not-products` policy in `data/identity-vocabulary-policy.json`. No ruling
   needed; correctly held for recrawl once a real product path exists. No action taken.
2. **Scientific Medical Clinical Limited** — no domain in seed. Re-searched today
   (web search on the company name, on its NI041931 Companies House number, and on its
   registered address) found no company website. Confirms the existing seed note ("no
   company website could be located"). Left as-is.
3. **U.K. Medical Limited** — no domain in seed, `companyNumberCandidate` 01455141
   marked only `candidate`. Investigated below.

## U.K. Medical Limited — what was found

The seed's `companyNumberCandidate` (01455141, "U.K. MEDICAL LIMITED") is **wrong**: that
number is actually **U.K. MEDICAL HOLDINGS LTD**, incorporated 1979, SIC "activities of
distribution holding companies" — a holding company, not a trading entity. It was found by
a plain Companies House name search on 02/09/2026 and never confirmed (rule 11) — correctly
never graduated past `candidate`.

Following the LinkedIn page for "UK Medical Ltd" (tagline "It's Interventional") led to
**itsinterventional.com**, whose own footer states "Registered in England No. 2144870" at
"Albreda House, Lydgate Lane, Sheffield, S10 5FH". Companies House's own record for
**02144870** shows a **previous name**: "U.K. MEDICAL LIMITED" from incorporation
(06/07/1987) until it renamed to "IT'S INTERVENTIONAL LIMITED" on 25/01/2022.
(https://find-and-update.company-information.service.gov.uk/company/02144870)

Company number **2144870 is already a separate, fully confirmed seed record** —
"It's Interventional Limited" — with `matchConfidence: confirmed` (proved by its own
website's registration line on 2026-08-14), holding two other NHS Supply Chain framework
awards (Endoscopy, Endourology and Oncology Ablation Consumables; Syringes, Needles and
Associated Products), `products: []` (never crawled).

So the "U.K. Medical Limited" that NHS Supply Chain names on the Surgical Instruments
brief (2020/S 170-412524) is, on this evidence, the same real company as the Hub's
existing "It's Interventional Limited" record, under its pre-2022 legal name.

## What was done vs left for a decision

- **Done:** the wrong 01455141 candidate on the "U.K. Medical Limited" record was flagged
  in-place (`companyNumberCandidate.matchedOn` and the record's `note`) with the full
  evidence trail above, so it can never be mistaken for confirmed. No merge performed —
  no products moved, no framework re-attributed, no alias added between the two records.
- **Left for Lou (OUTSTANDING ^o624):** deciding which record is canonical and merging
  "U.K. Medical Limited"'s Surgical Instruments award into "It's Interventional Limited"
  (or vice versa). This is the same duplicate-record shape as GBUK Group (^o333) and
  Polystar Plastics Ltd (^o334) on Polymer Aprons — a merge that touches both records'
  framework history, `company-logos.json`, `compare-suppliers.json` and
  `hub-search-index.json`, so it's a deliberate decision rather than an automated batch
  step. Once merged, "It's Interventional Limited" could then be crawled
  (itsinterventional.com) to work toward coverage on all three of its frameworks at once.

## Coverage impact this run

None. Surgical Instruments stays at 26.0% (13/50 published) — this run corrected a wrong
company-number candidate and surfaced a genuine merge decision; it did not crawl, resolve
a domain, or publish a new category mapping.
