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
universally available, for every UK company, is the **accounts category**, which is a
statutory band:

| Category | What it means |
|---|---|
| `micro-entity` | Meets the micro thresholds |
| `small` / `small-abridged` | Meets the small-company thresholds |
| `medium` | Meets the medium thresholds |
| `full` / `group` | Above medium — full accounts, turnover usually disclosed |
| `dormant` | Not trading |

**The numeric thresholds are deliberately not written in this file** — they are a fact with
a shelf life (root rule 12) and they changed for periods beginning on or after 6 April
2025. `scripts/refresh_companies_house.py` fetches them from the primary source at build
time and writes them into the data file alongside the date they were read, so the page
always shows the threshold that was current when the band was assigned.

**Rule.** Where full accounts disclose turnover and we have parsed it, the figure is shown
**with its made-up-to date**, never bare. Where they do not, the band is shown and the
absence is stated plainly — *"Files small-company accounts; turnover not disclosed
(legally permitted)"* — never left blank, and never filled with an estimate.

**Matching.** A supplier in our data is matched to a Companies House record by company
number where one is already recorded, otherwise by name search. A name-search match is
recorded as `matchConfidence: "probable"` and is **not** used for any derived claim —
only confirmed matches feed the size bands. Medtech is full of similarly-named entities
(the seed already notes Abbott Diabetes Care was formerly MediSense (U.K.) Holding Ltd),
and a wrong match would attach the wrong company's finances to a named business.

---

## Schema — `data/company-financials.json`

New file. **Needs a marker ref minted from the private salt before it can be published**
(`scripts/stamp_notice.py`, `REFS`) — `verify.py`'s `check_notice` fails without one.

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
| Frameworks (name, value, dates) | same | No | 1 |
| Alerts / recalls | same | No | 1 |
| Press, verified by 2+ sources | same (`news[]`) | No | 1 |
| Also on this framework | framework co-listing | **Yes** | 2 |
| Same speciality, no shared framework | speciality map | **Yes** | 2 |
| Company facts (number, status, age, SIC) | Companies House | No | 3 |
| Accounts category + turnover where filed | Companies House | No | 3 |
| Field position bands | co-listing × accounts category | **Yes** | 4 |
| Interview pack (print/export) | composed of the above | No | 5 |

Stage 5 adds no new claims. It re-presents panels 1–4 for a candidate walking into an
interview, so every rule above still governs it — including that a refused panel stays
refused in the printed pack rather than quietly reappearing as a blank heading.
