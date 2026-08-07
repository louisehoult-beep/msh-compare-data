# Company Report — derivation rules and schema

Written 06/08/2026, before the code, because root rule 14 requires a derived claim to
carry the rule it was derived under. Everything the Company Report asserts that was
*computed* rather than *read from a source* is specified here. If the code and this
document disagree, the code is wrong.

Origin: the James Moloney call (Clinical Selection, 06/08/2026). He asked for company
reports carrying competitors, market share, turnover, size, products, frameworks and
press. Two of those — **competitors** and **market share** — are derived claims and are
the reason this document exists.

---

## The two claims that are NOT facts

### 1. "Competitors" is framework co-listing, and must say so

We do not know who competes with whom. What we know is **who is listed on the same
framework lot**. Those overlap heavily but are not the same thing: two suppliers on the
same lot may sell into entirely different clinical niches, and a genuine competitor may
be absent from the framework altogether (direct-supply products, per the call — Severn's
range has no framework at all).

**Rule.** The panel is labelled *"Also on this framework"*, never *"Competitors"*. The
derivation is printed in the panel: which framework, which lot, and the date the framework
data was captured. A supplier that shares a speciality but no framework appears in a
separate, clearly-headed *"Same speciality, no shared framework"* list — never merged into
the first.

**Evidence floor.** Fewer than two suppliers on the lot → the panel does not render. One
supplier on a framework is a framework with one supplier, not a competitive field.

**Invariant.** Every name rendered must resolve to a supplier record carrying that
framework. A name that cannot be resolved is a bug, not a near-miss — drop the panel.

### 2. Market share is a position band, never a percentage

James was explicit that nobody has this data — Drive DeVilbiss's own commercial director
told him their internal share figure is a guess. Publishing a percentage would be
inventing a fact, and it is exactly the class of error that put 145 false job changes in
front of members on 24/07/2026.

**Rule.** No percentage is ever published as market share. What is published is a
**position band**, built from two things we can actually source:

- the **count** of suppliers on the relevant framework lot (from our own framework data), and
- each supplier's **statutory accounts category** (from Companies House — see below),
  which is a legally-defined turnover band, not our estimate.

The output reads, e.g.: *"11 suppliers on this lot. Three file large-company accounts
(statutory turnover threshold above £X), six medium, two small."* It never reads
*"GBUK holds 12% of this market."*

**Evidence floor — the panel refuses to fire when:**
- fewer than two suppliers are on the lot;
- no framework is indexed for the speciality;
- fewer than half the listed suppliers have a resolved accounts category (a size
  comparison built on a third of the field is not a size comparison).

Each of those has its own honest empty state naming what is missing. An empty panel is
never a reason to lower a threshold.

**Invariants (these are what `verify.py` tests):**
- No string rendered in a share context may contain `%`.
- The count quoted in the prose equals the number of rows rendered. (Same failure class
  as the cluster `rule` count check, which exists because prose drifted from data before.)
- Every band label comes from the fixed statutory set below — never computed ad hoc.
- Every company named resolves to a supplier record.

---

## Company size — what Companies House can and cannot give us

**The API does not return turnover.** The Companies House public REST API returns the
company profile — number, status, incorporation date, SIC codes, registered office,
accounts next-due and made-up-to dates, and the accounts *category*. It does **not**
return financial figures. Turnover appears only inside the filed accounts document
(iXBRL), and **only when the company files full accounts** — small and micro companies
are legally permitted to omit the profit-and-loss account entirely, and most UK medtech
subsidiaries do.

So "turnover" as James asked for it is not universally available at any price. What *is*
available for every UK company is the **accounts category** — the type of accounts the
company last filed, which is governed by the statutory size thresholds.

**The category is not a five-value size ladder, and must never be treated as one.**
Companies House publishes seventeen values (source: CH's own `api-enumerations/constants.yml`,
confirmed against the company-profile spec):

```
null, full, small, medium, group, dormant, interim, initial,
total-exemption-full, total-exemption-small, partial-exemption,
audit-exemption-subsidiary, filing-exemption-subsidiary, micro-entity,
no-accounts-type-available, audited-abridged, unaudited-abridged
```

Several of these are common and **none of them maps cleanly onto a size band** —
`total-exemption-small`, `unaudited-abridged` and `no-accounts-type-available` in
particular. `scripts/refresh_companies_house.py` therefore writes the raw enum value
verbatim and assigns no band at all.

**Rule for Stage 4.** Any mapping from category to size band is a derived claim and lives
in Stage 4, not in the fetcher. It must handle all seventeen values explicitly, and a
value it cannot confidently place is **unplaced** — it counts toward the "resolved" floor
as a miss, never as a guess. A company whose category is `no-accounts-type-available` has
an unknown size; it does not have a small one.

**The numeric thresholds are deliberately not written in this file** — they are a fact with
a shelf life (root rule 12) and they changed for periods beginning on or after 6 April
2025. `scripts/refresh_companies_house.py` fetches them from GOV.UK at build time (verified
06/08/2026 against SI 2024/1303 as well, both agreeing) and writes them into the data file
with the date read and the verbatim sentence each figure came from. If the source wording
moves, the script aborts rather than carrying a previous value forward.

**Rule.** Where full accounts disclose turnover and we have parsed it, the figure is shown
**with its made-up-to date**, never bare. Where they do not, the band is shown and the
absence is stated plainly — *"Files small-company accounts; turnover not disclosed
(legally permitted)"* — never left blank, and never filled with an estimate.

### Turnover is not extractable for most of this field, and that is a document-format fact

**Surveyed 07/08/2026, every full/group filer in this file (223 companies), by asking the
Companies House Document API which formats it holds for each company's most recent
accounts filing:**

| What Companies House holds | Companies | Share |
|---|---|---|
| PDF **and** iXBRL (machine-readable) | 41 | 18% |
| **PDF only** | 179 | 80% |
| Filing listed, no document served yet | 3 | 1% |

**So an automated turnover figure is available for at most 18% of the field, and a
ten-year series for fewer still.** The blocker is not the API key and never was — the key
works, and the API returns no financial figures for anybody (it never has). The blocker is
that four filers in five submit their accounts as a **PDF with no iXBRL version**, and
those PDFs are commonly scans rather than text: B. Braun Medical's 2025 filing, checked
this run, is a 7.9 MB `tiff2pdf` image that yields 184 bytes of text. There is no parse to
write for a picture of a page.

Consequences, so they are not rediscovered:

- **`turnoverNote` says which format was actually found**, per company, with the date
  checked. The previous single wording — *"not yet extracted from the iXBRL document"* —
  was untrue for 179 companies, because for them no iXBRL document exists. It has been
  replaced, not annotated (root rule 18).
- **A ten-year `growth.series` cannot be built from Companies House for this field.** Even
  Medline Industries, one of the 41, has iXBRL for only its three most recent filings; the
  2021 filing and everything before it is PDF. A series must therefore carry only the
  points that were genuinely read, each with the filing it came from, and the panel must
  state how many years it actually has. Padding a series to ten points is inventing data.
- **Where iXBRL exists, turnover is often not XBRL-tagged either.** Medline's filing tags
  `ProfitLoss` and `ProfitLossOnOrdinaryActivitiesBeforeTax` but no turnover fact, and
  carries `ReportIncludesDetailedProfitLossStatement = false`. The figure is nonetheless
  present in the rendered text of the same document (Turnover £56,273,786 for the year
  ended 31 December 2024; £48,554,872 comparative). So the extractor must read the
  document's text, not just its tagged facts — and anything it reads must be tied to the
  made-up-to date of the filing it came from.

**Matching.** A supplier in our data is matched to a Companies House record by company
number where one is already recorded, otherwise by name search. A name-search match is
recorded as `matchConfidence: "probable"` and is **not** used for any derived claim —
only confirmed matches feed the size bands. Medtech is full of similarly-named entities
(the seed already notes Abbott Diabetes Care was formerly MediSense (U.K.) Holding Ltd),
and a wrong match would attach the wrong company's finances to a named business.

**Accepted confirmation routes** (each recorded verbatim in `matchedOn` so a reader can
judge it):
1. a company number already recorded in this repo's own data and previously verified;
2. the company number published on the company's **own** website (imprint/terms page),
   agreeing with the CH record;
3. the NHSSC catalogue's **legal supplier name** for the framework products, agreeing
   exactly (modulo Ltd/Limited and punctuation) with a **single active** CH company,
   corroborated by town where the catalogue carries a depot location.
A bare name-search resemblance is none of these and stays `probable`. Route 3 exists
because the catalogue names the legal entity actually supplying the framework — it ties
the entity to the listing, which a name search cannot do.

**Manual interim (06/08/2026).** The Companies House API key is still awaited, so
`data/company-financials.json` was first populated by hand from the public register, for
the suppliers on GBUK Group's two frameworks only. Its `source` and `coverage` fields
say exactly this. `scripts/refresh_companies_house.py` replaces the file wholesale when
the key exists. One consequence recorded here so it is not "discovered" later:
`verify.py` currently accepts a **7-value** publication vocabulary for
`accountsCategory` (micro-entity, small, small-abridged, medium, full, group, dormant),
read from the wording of the filing itself; the API returns the 17-value enum above.
**The fetcher must map 17 → 7 explicitly and refuse on any value it cannot place** — do
not widen the gate's list to let an unmapped value through (root rule 13).

---

## Schema — `data/company-financials.json`

New file. **Needs a marker ref minted from the private salt before it can be published**
(`scripts/stamp_notice.py`, `REFS`) — `verify.py`'s `check_notice` fails without one.

The schema below is the API-era shape; the manual-interim file adds `coverage`,
`accountsCategoryNote`, per-record `matchedOn` / `accountsFilingVerbatim` /
`turnoverNote` / `registeredOffice`, and an `officers` block per confirmed company
(see "Notable people — rules" below). All additive; nothing below is removed.

```json
{
  "_notice": { "…stamped by scripts/stamp_notice.py…" },
  "dataAsOf": "2026-08-06",
  "source": "Companies House public data API (https://api.company-information.service.gov.uk)",
  "thresholds": {
    "readFrom": "https://www.gov.uk/…",
    "readOn": "2026-08-06",
    "appliesTo": "periods beginning on or after 6 April 2025",
    "bands": { "micro": {…}, "small": {…}, "medium": {…} }
  },
  "companies": {
    "GBUK Group": {
      "companyNumber": "01234567",
      "registeredName": "GBUK GROUP LIMITED",
      "matchConfidence": "confirmed",
      "matchedOn": "company number recorded in supplier-seed alerts",
      "status": "active",
      "incorporated": "2000-05-18",
      "sic": ["46460"],
      "accountsCategory": "full",
      "accountsMadeUpTo": "2025-03-31",
      "_accountsMadeUpToNote": "read from accounts.last_accounts.period_end_on; made_up_to is deprecated in the CH spec and is only a fallback",
      "turnoverGBP": null,
      "employees": null,
      "sourceUrl": "https://find-and-update.company-information.service.gov.uk/company/01234567"
    }
  }
}
```

`turnoverGBP` and `employees` are `null` unless actually read from a filed document.
**Null means "not disclosed", and the page must render that phrase — never `0`, never a
blank cell, never an inferred figure.**

---

## Panels, and which stage builds them

| Panel | Source | Derived? | Stage |
|---|---|---|---|
| Identity, specialities, products | `supplier-seed` / `supplier-index` | No | 1 |
| Product listing (see scope below) | `nhssc-cache` / `supplier-products` | No | 1 |
| Frameworks (name, value, dates) | same | No | 1 |
| Alerts / recalls | same | No | 1 |
| Press, verified by 2+ sources | same (`news[]`) | No | 1 |
| Also on this framework | framework co-listing | **Yes** | 2 |
| Same speciality, no shared framework | speciality map | **Yes** | 2 |
| Company facts (number, status, age, SIC) | Companies House | No | 3 |
| Accounts category + turnover where filed | Companies House | No | 3 |
| Notable people (officers, dated changes) | Companies House officers register | No | 3 |
| Field filing profile | co-listing × accounts filings | **Yes** | 4 |
| Interview pack (print/export) | composed of the above | No | 5 |

Stage 5 adds no new claims. It re-presents panels 1–4 for a candidate walking into an
interview, so every rule above still governs it — including that a refused panel stays
refused in the printed pack rather than quietly reappearing as a blank heading.

---

## Product listing — scope (set by Lou, 06/08/2026)

The report's product section is three tiers, each labelled as what it is:

1. **Catalogue-verified** — rows read from the NHS Supply Chain catalogue via
   `nhssc-cache.json`: product, catalogue description, NPC code, pack. These are the
   products verifiably supplied through the framework route.
2. **Also supply — not in the NHSSC catalogue** — items confirmed on the company's own
   website or published range but absent from the catalogue (`notCatalogue`, each with
   its recorded reason). "Not on a framework yet" is a statement about the catalogue,
   never about the product.
3. **Full verified range** — where a complete crawl of the company's own site exists
   (`supplier-products.json`; GBUK Group so far), grouped by the company's own
   divisions, with verified absences stated.

Where a supplier has only the curated headline products, the panel must say the full
listing has not been captured — five chips must never read as a complete range. A
genuinely complete list of everything a company sells is not public anywhere; these
three tiers are the honest maximum, and extending tier-3 coverage is a crawl programme
(same mechanism that built the GBUK tree), supplier by supplier.

## Notable people — rules

Officers data lives inside each company's record in `data/company-financials.json`
(`officers.current`, `officers.recentChanges`), read from the public officers register,
with `readOn` and `sourceUrl`. Only `confirmed` matches carry an officers block.
**Appointments and resignations are dated events; the panel never asserts that one
person replaced another.** Succession is not a register fact — deriving it is the
24/07/2026 stakeholder-mapper error with different names in it. Trade-press appointment
coverage flows through the LinkedIn weekly sweep's Part C (`people-move` items,
primary-source verified); the sweep's Part E maintains the officers blocks weekly.

## Stage 4 as built (06/08/2026)

Stage 4 renders a **field filing profile** per framework: every confirmed supplier with
the exact wording of its most recent accounts filing, plus who is unresolved and why.
Floors, both proved in the harness: fewer than two suppliers → the co-listing itself
refuses; resolved-below-half (`resolved × 2 < field`) → that framework's profile
refuses, naming the unresolved. What a FULL filing does and does not imply is printed on
the panel, with the statutory thresholds quoted from the `thresholds` block and their
source. Turnover has three rendered states: a figure with its made-up-to date;
"disclosed in the filed accounts; not yet extracted" (full/group filings awaiting the
iXBRL parse); "not disclosed in the filed accounts (legally permitted)". A 0 is a parse
bug, never a fact.
