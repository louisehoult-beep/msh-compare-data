# Framework coverage batch — findings, 15/09/2026

Run of the `differentiator-framework-coverage` scheduled task.

## Lowest-coverage picks re-checked, all still confirmed dead ends

Regenerated the ledger fresh. The pick order was unchanged from 14/09: **Digital Diagnostic
Solutions** (16.7%), **Insulin Pumps, CGM & Hybrid Closed Loop** (16.7%), **Infusion Pumps**
(18.5%), **Electrodes, Ultrasound Gels, Defibrillation** (18.9%), **Ultrasound Scanners**
(19.0%). All five were re-checked against this run's evidence and confirmed unchanged:

- **Digital Diagnostic Solutions**: already resolved as a structural ceiling (`^o422`,
  `^o465`-adjacent) — the 9 `Left` suppliers are large multinationals (Philips, Siemens
  Healthineers, GE HealthCare, Roche, Draeger, Olympus, Leica, Haemonetics, Sysmex) whose
  global sites either refuse crawl outright or publish nothing under digital:hw/sw. No new
  route found. Not worked.
- **Insulin Pumps, CGM & Hybrid Closed Loop**: re-confirmed the `^o469` ledger bug (Abbott and
  Medtronic already correctly refused under their real seed identities; the ledger's
  literal-name match against the framework's award-list spelling doesn't reach those refusal
  records). Urathon Europe's CGM product line still doesn't appear in its crawled catalogue.
  Not worked.
- **Infusion Pumps**: `Left` is now just the 1 held (BMS Critical Care, `^o473`) and 1
  needDomain (Arcomedical, `^o475`) items already logged 14/09. No new work available.
- **Electrodes, Ultrasound Gels, Defibrillation**: Electro Spyres (`^o434`) and Salter Labs UK
  Ltd (`^o403`, decision-queue item 2) already logged. No new work available.
- **Ultrasound Scanners**: its one `held` supplier, "MIS Healthcare", is the well-documented
  duplicate-identity tie with the separately-tracked "Medical Imaging Systems (MIS
  Healthcare)" record (`^o377`) — same domain (mishealthcare.co.uk), confirmed live again this
  run, but neither record carries a Companies House number, so Lou's standing merge rule
  (shared CH number or keep separate) still isn't met. Left alone, exactly as `^o377`
  instructs. Its 2 `needDomain` suppliers (FUJIFILM Sonosite, Hitachi Medical Systems UK) were
  both already attempted and refused (large-parent-site pattern). No new work available.

Also checked but not worked: **Total Orthopaedic Solutions 3** (19.8%, 59 left) — the 4
`NEVER ATTEMPTED` suppliers added 14/09 without domains (Globus Medical UK Ltd, M.D.M Medical
Ltd, NuVasive UK Ltd, Ortho Solutions UK Ltd) were tried again this run with `--search`:
Globus Medical UK Ltd's obvious candidate (globusmedical.com) resolved but never names the UK
entity on the page; NuVasive UK Ltd's obvious candidate (nuvasive.com) didn't answer under the
tool's candidate-file route (worth checking separately — see below). M.D.M and Ortho Solutions
had no candidate at all. None proved. This research was done in a clone that was abandoned
after a rebase conflict (see below) rather than re-run, so it isn't recorded in
`state/domain-seeding-report.json` — a future run will re-attempt these 4 and find the same
result, which costs a little time but loses nothing.

## Framework worked: Patient Monitoring Equipment, Bedside Equipment Alarm Monitoring Systems

Chose this framework because its 4 `unresolvedNames` (top priority in the brief's own working
order) hadn't been touched by any previous run: **AC Cossor & Son (Surgical) Ltd**, **Probo UK
Ltd**, **Nihon Kohden UK Ltd**, **Spacelabs Healthcare Ltd**.

- **Nihon Kohden UK Ltd** — resolved as the correct spelling of the existing seed record
  "Nihon Koden" (missing the 'h'), which was on file from a different framework (External
  Defibrillation Devices). Confirmed via the company's own site, eu.nihonkohden.com: it
  publishes both resuscitation/defibrillator products (matching the existing record's
  framework) and patient-monitoring products (matching the new one) — one real company on
  both frameworks. Added the alias, no company number asserted (a Companies House name search
  is not evidence under rule 11).
- **Probo UK Ltd** — resolved as an imprecise rendering of the existing seed record "Probo
  Medical (formerly MIUS)" (Probo Medical Ltd, 03466990). No company named exactly "Probo UK
  Ltd" exists at Companies House; Probo Medical's own NHS Supply Chain saving case study
  covers the IRadimed MRI-compatible patient monitor, exactly this framework's product class.
  Added the alias.
- **AC Cossor & Son (Surgical) Ltd** (trading as Accoson, part of HCE Medical Group) — new
  supplier record added, framework award only. Crawl of accoson.com refused (no WordPress
  product post type, no WooCommerce Store API — not a standard catalogue site). **Registration
  number left unconfirmed and needs a ruling — see OUTSTANDING.**
- **Spacelabs Healthcare Ltd** — new supplier record added. Crawled: 585 products across 7
  divisions. "Patient Monitoring Supplies" (454) and "Uncategorized" (9, despite the generic
  label — its own examples are telemetry leadwires) both read clearly as `monitoring:sens`
  (ECG cables, BP cuffs, temperature probes, sample lines, leadwires — sensors/consumables
  used with Spacelabs monitors, not the monitors themselves). Mapped. The other 5 divisions
  (Cardiology Supplies, Batteries, Paper, Anesthesia Supplies, and a 1-product
  battery-pack division named after a monitor model) were left held — genuinely ambiguous
  (Cardiology Supplies could be `cardiology:consum` as easily as `monitoring:sens`) or plainly
  out of a speciality's scope (batteries, paper), not guessed.

  Product-detail capture (needed for a product to publish, not just to be mapped — see
  technical note below) is a slice, not the full range: 245 of 585 products (42%) have their
  own-page detail captured, all within the mapped divisions. 213 of those now publish under
  `monitoring:sens`. The remaining ~209 products in the two mapped divisions are correctly
  mapped but still HELD pending their own detail-page capture in a future run
  (`scripts/crawl_supplier_product_detail.py --supplier "Spacelabs Healthcare Ltd" --domain
  spacelabshealthcare.com`, resumable).

### Technical note for future runs: mapping alone does not publish

`scripts/build_differentiator.py` only publishes an own-crawled product when it has a `hub`
category **and** at least one `sources` entry, and the only way a manufacturer-crawled product
gets a `sources` entry is via `data/supplier-product-detail.json` (a separate per-product-page
crawl, `scripts/crawl_supplier_product_detail.py`) or an NHS Supply Chain name match. The brief
mentions only `crawl_supplier_site.py` (the range-listing crawl) as the step before mapping;
for a supplier with no NHSSC catalogue overlap, that step alone is not enough — a mapped
division still holds every product until the detail crawl runs too. Worth adding to the brief
so a future run doesn't mistake "mapped, still held" for a bug.

### Technical note: the company-alias registry needs a manual rebuild after editing the seed

`scripts/build_coverage_ledger.py` and `company-aliases/company_alias.py resolve` both read
`company-aliases/company-alias-registry.json`, a **pre-built cache** of the seed's names and
aliases — not the seed file directly. An alias added straight to `supplier-seed.json` is
invisible to both until `python3 company-aliases/company_alias.py build` is re-run. Without
that step this run's alias resolutions would have looked like they hadn't taken effect at all
(the ledger still reported all 4 names as `unresolved`, and the two aliased records as
`unknown`, after the seed edit and before the rebuild). Worth adding to the brief's step 4.

### A rebase conflict, resolved by redo-on-fresh-clone, not by hand

`land.sh` hit a rebase conflict on `data/supplier-seed.json` against a peer commit that landed
mid-run (`ea50106`, unrelated Infusion Pumps domain research). Per
[[msh-compare-data-peer-landed-redo-not-rebase]], aborted the rebase, took a fresh clone from
the new `origin/main`, and replayed this run's edits (seed edits, the two crawls' output
merged in directly rather than re-crawled live, the category-map union and mapping, the
compare-suppliers.json ref fix) on top of it. Landed clean on the second attempt.

## Coverage movement

Patient Monitoring Equipment, Bedside Equipment Alarm Monitoring Systems, Related Products and
Services: 20.0% (7/35 published) → **22.9% (8/35 published)**. `unresolvedNames` 4 → 0.

## Second run 15/09

Ledger regenerated fresh (already reflecting the above). Same lowest-coverage pick order:
Digital Diagnostic Solutions (16.7%), Insulin Pumps, CGM & Hybrid Closed Loop (16.7%),
Infusion Pumps (18.5%) — all three re-checked and confirmed unchanged dead ends again,
with one new detail each:

- **Digital Diagnostic Solutions**: went through all 9 `publishedElsewhereNeedingCategory`
  suppliers individually rather than accepting the "structural ceiling" label at face value.
  8 of 9 (Draeger, Haemonetics, Olympus (KeyMed), Leica Microsystems, Philips, Roche
  Diagnostics, Siemens Healthineers) confirmed as before — their one crawled division has
  zero genuine digital-diagnostics content. **Epredia is a genuine exception**: its
  "Digital Pathology" division (25 products, mapped whole to `pathology:histo`) contains
  real scanner hardware (P1000/P250/P480 Dx/Rx Scanner, Midi scanners) and software
  (Slidecenter, Slidemanager, Quantcenter, CaseManager) by its own product names, alongside
  slides/consumables. Not forced: `merge_differentiator_parts.py` only fills a null `hub`,
  amending this already-decided mapping needs a deliberate hand-edit, and adding digital:hw/sw
  to the whole division would also mistag the consumables. Logged to OUTSTANDING as a ruling.
  Also found: Sysmex UK's category-map carries 3 orphaned entries (Quantcenter, Slidecenter,
  Slideviewer → `digital:sw`) referencing divisions absent from the current raw crawl — logged
  to OUTSTANDING as data hygiene, not a decision.
- **Insulin Pumps, CGM & Hybrid Closed Loop**: unchanged, `^o469`/`^o452` bug re-confirmed,
  not re-crawled again (would only repeat today's earlier result and risk the refusal-TTL
  trap the brief warns about).
- **Infusion Pumps**: unchanged, both remaining items (`^o473`, `^o475`) already logged.

## Framework worked (again): Total Orthopaedic Solutions 3

Continued the `needDomain` backlog rather than re-attempt the 4 suppliers the earlier run
today already tried and left unproven (Globus Medical UK Ltd, M.D.M Medical Ltd, NuVasive UK
Ltd, Ortho Solutions UK Ltd). Researched 14 different, not-yet-attempted `needDomain`
suppliers (WebSearch + WebFetch, registration-number proof bar, `seed_supplier_domains.py
--candidates-file --retry-unproven --supplier` run per name to stay scoped to this
framework only):

- **2 proven and written**: **Ovidius Medical Ltd** → `www.ovidius-medical.com` (privacy
  policy states company number 10054904, matching the seed's recorded number exactly) and
  **Ovidius Solutions Ltd** → `www.ovidius-solutions.co.uk` (homepage states company number
  11640816, matching exactly). Both crawled: neither exposes a WordPress or WooCommerce
  product API and neither sitemap carries product-path URLs, so both are correctly refused —
  no catalogue to read, recorded with the full reason.
- **12 refused on the strong bar** (site read, never states the seed's recorded registration
  number): Innovate Orthopaedics Ltd, Leda Orthopaedics Ltd, OrthoAccess Ltd, Sovereign
  Medical, Venturis Medical Ltd, Kaiser Medical Technology Ltd, Lavender Medical, Hospital
  Innovations, Ideal Med, Edge Medical Ltd, Cenobiologics Ltd, Arthro Dynamik Ltd. Correct,
  honest refusals — not written to the seed.

### Coverage movement, second run

Total Orthopaedic Solutions 3: 20/101 published (19.8%) → 20/101 published (19.8%,
unchanged — neither new capture had a catalogue to map). `needDomain` 50 → 48. Real forward
motion (2 domains proven and crawled, both honest refusals correctly recorded) even though
the published count did not move, matching the brief's own point that coverage % is not the
only signal of progress.
