# `data/interview-prep.json` — the `co` record field map

**Written 18/08/2026.** Derived by reading how the Interview Prep page's own JavaScript
consumes each key (`Website/interview-prep-page.html`, the single inline `<script>`), not
from the lost builder's source. Every statement below is a statement about what the page
actually does with the value.

The generator is `scripts/build_interview_prep.py`. It is the only thing that may write the
`co` array. The other top-level keys — `_notice`, `roles`, `specs`, `routes`, `confs`,
`cross` — are editorial and are never touched.

## The record

`co` is a list of company records, sorted case-insensitively by `n`. Optional keys are
**omitted entirely** when empty: the page's `ipHas()` treats `undefined`, `null`, `''` and
zero-length as absent and every panel it drives has a written empty state, so an omitted key
is a supported state and an empty array is not.

| Key | Type | Source | What the page does with it |
|---|---|---|---|
| `n` | string | `supplier-index.json` → `suppliers[].name` (canonical) | The dropdown option value and label, the panel heading, and the seed for the Google News, Glassdoor and LinkedIn searches. `ipCo()` looks a company up by exact `n`, so a name the index cannot resolve is a company the rest of the Hub cannot find. |
| `r` | string | `company-financials.json` → `registeredName` | **Rendered unconditionally.** "Registered name" row, and named in the running prose of the "How to stand out" and "What to do next" panels. |
| `no` | string | `company-financials.json` → `companyNumber` | **Rendered unconditionally.** Printed as the "Company number" row and concatenated into three Companies House URLs (`/company/<no>` twice, `/company/<no>/filing-history`). An empty value produces a link to `/company/` — a broken page, not an empty state. This is why a company with no register record is omitted. |
| `st` | string | `status` | "Register status" row. |
| `ac` | string | `accountsCategory` | "Accounts filed as" row. |
| `am` | date `YYYY-MM-DD` | `accountsMadeUpTo` | "Latest accounts made up to", reformatted to DD/MM/YYYY by `ipDate()`. |
| `inc` | date `YYYY-MM-DD` | `incorporated` | "Incorporated", same reformat. |
| `e` | number | `employees` | "Employees, as tagged in those accounts", and the divisor for the revenue-per-head sentence. |
| `t` | number | `turnoverGBP` | **Read by nothing in the current page.** Latest tagged turnover; kept because the record has always carried it and dropping a field silently is how a consumer breaks later. |
| `ts` | list of `[periodEnd, value]` | `turnoverSeries[].periodEnd` / `.value` | The turnover bar chart, the period table, the growth percentage, and the revenue-per-head line. Absent ⇒ the page prints the "no machine-readable turnover" explanation and a filing-history link. |
| `o` | list of `"NAME — Role"`, max 4 | `officers.current[]` | **Read by nothing in the current page.** Register facts already published in full in `company-financials.json` in this same repository, so it adds no exposure. |
| `sp` | list of strings | `specialities` | "Where the Hub has them selling" chips. Also the pool the fallback competitor set is drawn from. |
| `pr` | list of strings, max 8 | `products` | "What they sell" chips. |
| `vo` | string | `voice.line` (**not** `voice.angle`) | "How they position themselves in this market", labelled on the page as the Hub's own editorial summary. |
| `ln` | list of `[label, url]`, max 3 | `links[].label` / `.url` | The "Go and look for yourself" row, before the three links the page always appends (Companies House, Glassdoor, LinkedIn). |
| `f` | list of `[name, dates, url]`, max 4, deduplicated by name | `frameworks[].name` / `.dates` / `.url` | "Named on these national agreements". An empty `dates` renders as "not stated on the captured brief". Absent ⇒ the "no published national agreement" note, which is a written empty state, not a gap. |
| `cp` | list of `[company, sharedCount]`, max 8 | **derived** — see below | Competitor chips plus the shared-agreements bar chart, and the first three also seed the press searches. `sharedCount` is what the bars are drawn from, so it must be the real count. |
| `nr` | list of company names, max 8 | **derived fallback** — see below | Rendered only when `cp` is absent, under wording that says plainly it is a speciality-tag fallback. |
| `aw` | list of `[title, buyer, value, date, url]`, max 3 | `awards[]` | "Recent public contract awards to this company". |
| `nw` | list of `[headline, date, publisher, url]`, max 3 | `news[].headline` / `.date` / `.sources[0]` | "In the press". Only the first recorded source of each item is carried; the page renders one publisher per row. |
| `al` | list of strings, max 2 | `alerts[]`, strings only | "Ownership and corporate background", each string its own paragraph. |

Dict-form entries in `alerts` are structured framework and product notes, not company
background, and are not carried. Maintenance notes left by the Hub's own editors — those
opening "Removed", "Cleaned up", "Re-tagged", "Full product-list spot-check" or "CATALOGUE IS
WIDER THAN THE STORE FRONT PAGE" — are dropped: they describe edits to the dataset, not the
company, and the published file carried eight of them.

## `meta`

`n`, `built`, `coAsOf` (from `company-financials.json`'s `dataAsOf`) and `supAsOf` (from
`supplier-index.json`'s `dataAsOf`) are regenerated each run; `coAsOf` and `supAsOf` are both
printed on the page as the "sources" line. `rtAsOf` and `contact` are editorial. The builder
adds `cpRule`, `nrRule`, `omitRule`, `omittedNoRegister` and `builtBy`, so the derivation
rules travel inside the published file (root rule 14) rather than only in this document.

## Names

Every record is keyed on the canonical `supplier-index.json` name, resolved through
`scripts/company_match.py` — the Hub's exact-only alias rule, no fuzzy matching, an
unresolved name a stop rather than a guess. Competitor names in `cp` and `nr` are the same
canonical names and are additionally required to be a company this file itself publishes, so
every competitor the page renders can then be selected from the dropdown.

## The two derived fields, and when they refuse to fire

`cp` is the only claim on this page that is computed rather than read.

**The rule.** Companies named on the same national agreements, ranked by how many they share.
Same-group companies are excluded by name root. Ties are broken first by how *specific* the
shared agreements are — a shared place on a six-supplier roster is evidence of head-to-head
competition, a shared place on a hundred-and-twenty-supplier roster is barely evidence at all
— and then by how many specialities the two companies also share.

**The refusal.** A tied group is published whole or not at all. Where a group would have to
be cut part-way to fit the eight slots, it is dropped rather than cut, because the cut would
be alphabetical accident presented as a ranking. Where that leaves nothing, `cp` is omitted
and the page falls through to `nr`, or to its "no competitor set could be derived" state.
This is why a company on one 122-supplier laboratory framework and nothing else gets no
competitor panel: 118 companies share exactly that one agreement with it and the evidence
does not rank them. The published file used to name eight of those 118 in an order nothing in
the data justified.

`nr` follows the same shape one level down: companies sharing at least one speciality, ranked
by how many they share, then by how narrow those specialities are, then by how focused the
other company is; tied groups whole or not at all.

## Invariants

`scripts/build_interview_prep.py --check` re-derives and tests every claim and writes nothing
if any fails: canonical and unique names; a registered name and company number on every
record; the number agreeing with `company-financials.json`; `cp` and `nr` never both present;
every competitor selectable, never the company itself and never its own group; competitor
counts positive integers in non-increasing order; every cap respected and no key present but
empty; every embedded link `http`-scheme; every turnover row a date and a number.

A failing invariant is a data problem. Loosening one to make a run succeed is the 24/07/2026
incident with different words in it.

## Known gap

`verify.py` — the publish gate — does not read `data/interview-prep.json` at all, so the
invariants above are enforced only by the builder. Folding them into the gate is the right
next step, and belongs in the same change as any future edit to `verify.py`.
