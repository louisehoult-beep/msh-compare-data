# Framework coverage batch — 19/09/2026 (run 2) findings

Picked framework: **Surgical Instruments** (22.0% coverage, 21 left — the ledger's own top
pick after Total Orthopaedic Solutions 3, which an earlier run today (`bf175dc`) had already
exhausted with no safe movement; 0 unresolved names, 15 `publishedElsewhereNeedingCategory`,
1 `heldNeedingCategory`, 1 crawlable, 4 `needDomain`).

## Movement: 11 → 12 published, coverage 22.0% → 24.0%

**Farla Medical / Needle Holders division mapped to `surgical:needle`.** All 14 examples are
named reusable stainless-steel instruments (Instramed Halsey Needle Holder Tungsten Carbide,
Instramed Mayo Needle Holder, Instramed Halsey Needle Holder) — an exact match to the
vocabulary's `surgical:needle` definition ("Needle holders & suture passers"). Checked against
the speciality's own `routeNote`, which explicitly excludes single-use ranges ("a reusable
instrument is never compared against a sterile single-use equivalent") — none of the 14 carry
the "Sterile" marker Farla's genuinely single-use divisions use (its Forceps and Scissors
divisions, both already correctly mapped `theatres:sui`, do carry it). Added via
`data/differentiator-map-parts/Farla-Medical--framework-coverage-0919.json`, folded in with
`merge_differentiator_parts.py --apply`.

## Worked, no further safe movement this run

### `crawlable` (1) — crawled, but not usable

**Steris IMS Ltd** (`healthcare.steris.com`) — crawled clean, 69 products across 10 divisions.
Every division name and product name is a category/navigation page title from the site's own
menu ("Central Sterile Services Department Accessories", "Electrosurgical Products", "Surgical
Instruments", "Operating Room Storage Solutions"...), not a specific named instrument or product
— the crawler captured STERIS's whole equipment/service portfolio at the category level, not a
product-by-product range. None of these page titles map cleanly to a specific `surgical:*`
instrument type (bone/clamp/curette/elev/forceps/knife/needle/probe/retract/scissor/spec/suction)
without guessing. Left held rather than force-mapped.

### `needDomain` (4) — 0 proved

Ran `scripts/seed_supplier_domains.py --allow-foreign --search --retry-unproven` against all 4:
Aquilant Limited, Decree Thermo, Scientific Medical Clinical Limited, U.K. Medical Limited. None
cleared the registration-number / self-declared-foreign proof bar — "no candidate domain
answered" (Aquilant) or "site read, but it never identifies itself as this company" (the other
three). Aquilant is already a known-hard case, flagged the same way on the MIS framework
16/09/2026 (`docs/framework-coverage-findings-2026-09-16-run3.md`).

### `heldNeedingCategory` (1) — genuine structural gap, not forced

**Bolton Surgical Limited** — 2311 products. The supplier record's own `structure` string says
"No usable category structure in the site's own taxonomy — listed as one flat range"
(`hasDivisions: false`), and that is true of the `division` field only: every one of the 2311
products carries `division: "Uncategorised"`.

**It is not true of the product records as a whole, and this section originally said it was.
Corrected 19/09/2026 by the 12:10 `outstanding-sweep`, measured against `main`:** each product
also carries a `category` field, and it is populated. The 12 terms in the map entry's
`categories` field are not navigation labels — they are the distinct values of that per-product
field. The counts:

| | products | share |
|---|---|---|
| one of 8 clinical specialities (General Surgery 477, Orthopaedic/Neuro 343, Ear Nose & Throat 317, Plastic Surgery 246, GU/Gynaecology 150, Colo Rectal/Intestinal 140, Dental 87, Cardio Vascular/Thoracic 81) | 1841 | 79.7% |
| one of 145 other labels — instrument types (Forceps 24, Scissors 26, Retractors 8, Rongeurs 6…) trailing into individual instrument names | 253 | 10.9% |
| blank | 217 | 9.4% |

So four-fifths of the catalogue is already filed by clinical speciality, per product, on disk.
**A re-crawl is therefore the wrong next step** — nothing needs fetching again, and
`--product-path forceps` / `--product-path scissors` would re-read the site for structure it has
already given us. What is missing is a derivation: the builder reads `division`, which is flat,
and never looks at `category`. Bolton Surgical is the only supplier in the whole file in this
shape (one flat division, two or more distinct per-product categories), so this is a
single-supplier derivation, not a pipeline change — and the 253 instrument-type rows and 217
blanks must stay held either way, since an instrument type is not a speciality.

Bolton Surgical is a genuine reusable stainless-steel instrument maker (examples read like
premium reusable instruments — "Peet Nasal Rasp... Gold Handle", "Micro Crocodile Grasping
Forceps with Fixed Shaft"), so the 1841 are a real prize. Still not attempted — promoting a
`category` to a published grouping is a data-shape decision with a publish behind it, so it
wants an attended run, now that it has the right premise to start from.

### `publishedElsewhereNeedingCategory` (15) — one lead taken, fourteen checked and left

Checked each supplier's captured divisions against this framework's in-scope categories AND the
speciality's reusable-only `routeNote`:

- **Avicenna Surgical Limited** — "Single Use Instruments" division (`Single Use Forceps`,
  `Single Use Scalpel Handles`, `Single Use Speculums`, `Single Use Needle Holders`, `Single Use
  Scissors`...) is correctly excluded already (mapped `theatres:sui`) — this framework's own
  routeNote excludes single-use ranges by design. Not a lead.
- **Farla Medical** — the one genuine lead, taken (see above). Checked every other division
  (hundreds — Farla is a large general medical wholesaler): "Forceps" (99, `theatres:sui`,
  marked Sterile/Single — correctly single-use) and "Scissors" (34, `theatres:sui`, same) are
  already correctly routed away from this framework. "Curettes" (4 products) mixes an
  "Instramed" reusable-branded curette with an explicitly "Kai Disposable Dermal Curettes" item
  in the same division — not clean enough to map as a whole division, left unmapped rather than
  guess which are which.
- **B. Braun Medical, Beaver Visitec International, BioSpectrum, Fannin (UK), GBUK Group,
  HC21 (UK), Henry Schein UK Holdings, Kebomed UK, ProSys International, Daniels Health
  (Sharpsmart), Sheffmed, Timesco Healthcare, Vernacare** — captured ranges are orthopaedic
  implants, ophthalmology consumables, urology/gynaecology instruments, pharmaceuticals,
  wound care, vascular access, and similar; nothing reads as an unmapped reusable surgical hand
  instrument division. Vernacare's "General Surgery" (4) and "Womens Health" (6) divisions list
  only generic category names as examples ("Forceps", "General Instruments", "Needle Holders")
  rather than named products — too vague to map without guessing which specific instruments they
  actually are.

## Landed

`./land.sh` with `data/differentiator-category-map.json`, `data/differentiator.json`,
`data/coverage-ledger.json`, `data/differentiator-map-parts/Farla-Medical--framework-coverage-0919.json`,
`data/supplier-products.json` (the Steris IMS crawl), `docs/COVERAGE-LEDGER.md`,
`docs/framework-coverage-findings-2026-09-19-run2.md`. `verify.py` passed (18 pre-existing
warnings, none introduced by this batch).
