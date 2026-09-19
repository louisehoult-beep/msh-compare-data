# Framework coverage batch — 19/09/2026 findings

Picked framework: **Total Orthopaedic Solutions 3** (21.8% coverage, 54 left — the ledger's
own top pick: 0 unresolved names, 6 `publishedElsewhereNeedingCategory`, 2 `heldNeedingCategory`,
0 crawlable, 46 `needDomain`).

## Worked, no data change: this run's honest result is documented gaps, not movement

Every actionable bucket was checked in priority order. None produced a safe write. Recorded
here so the next run does not repeat the same 46-supplier domain search from a cold start.

### `needDomain` (46) — 12 researched, 0 proved

All 46 were already in `supplier-seed.json` (no "not yet in the seed" work available). Web
search found a plausible corporate domain for 12 of them — Globus Medical UK Ltd, NuVasive UK
Ltd, Orthofix Limited, Medartis Ltd, Paragon 28, Spineart UK Ltd, Microport Scientific Ltd, KLS
Martin UK Limited, Materialise, implantcast UK, joimax UK, TRB Chemedica (UK) Ltd — all
confirmed by name and by a UK Companies House number recorded in `company-financials.json`.

None cleared the write bar (`scripts/seed_supplier_domains.py`'s registration-number proof, or
a self-declared foreign registration/VAT for a non-UK entity). Checked by hand where the
automated probe reported "site read, but it never identifies itself as this company":

- **Globus Medical UK Ltd** (06491893) — globusmedical.com is the group's global site; no UK
  registration text found on it.
- **Microport Scientific Ltd** (08641910) — microport.uk's own footer states a registration
  number, "UK 013158B", which does **not** match 08641910. Not this record's proof; left
  unseeded rather than accepted on a mismatch.
- **TRB Chemedica (UK) Ltd** (04327806) — trbchemedica.co.uk's terms page states only a VAT
  number ("787 660573"), not the Companies House number. VAT is not a recognised proof route
  for a UK-registered entity (self-declared-foreign is for suppliers with no UK CH number at
  all, which this one has).
- **Materialise** — materialise.com's guessed legal/privacy paths both 404'd; not pursued
  further this run.
- The remaining eight (NuVasive, Orthofix, Medartis, Paragon 28, Spineart, KLS Martin,
  implantcast, joimax) all returned "site read, but it never identifies itself as this
  company", "redirected to a third-party host" or "no candidate domain answered" from the
  automated probe — global corporate or merged-entity sites that don't carry a UK-specific
  registration statement on a reachable page.

**A tooling note for whoever runs this next.** `scripts/seed_supplier_domains.py --write`
merges every STRONG-proof result currently banked in `state/domain-seeding-report.json` into
`data/supplier-seed.json` on every run — not just the supplier(s) named by `--supplier`. A
`--write` call made mid-session wrote a domain for "Newell Brands" (an unrelated supplier on a
different framework, proven by an earlier unrelated sweep) alongside the intended target. Caught
before landing and reverted (`git checkout -- data/supplier-seed.json data/coverage-ledger.json
state/domain-seeding-report.json`), so nothing from that write shipped. Anyone using this script
for a single-framework batch should run **without** `--write` first, confirm the proof is for
the intended supplier only, and merge that one supplier's link into the seed by hand — `--write`
is a whole-report sweep tool, not a scoped one, despite `--supplier` scoping the *search*.

The remaining 34 `needDomain` suppliers were not attempted this run (own-name web search per
supplier is the bottleneck; left for a future run per the brief's "do not attempt every one in
one run").

### `heldNeedingCategory` (2) — genuine vocabulary gaps, not forced

- **Macromed UK Ltd** — 44 held products from `macromed.co.uk`'s flat sitemap. Read the full
  list: almost all are endoscopy/interventional-radiology items (Hilzo biliary/GI stents, ALN
  Vena Cava Filter, Cera Vascular Plug, Fustar Steerable Sheath, and similar) — matching this
  supplier's *other* award, Endoscopy, Endourology and Oncology Ablation Consumables, not this
  one. One name, "Intraspine" (a known interspinous spinal-stabilisation device), is plausibly
  orthopaedic/spine, but a single ambiguous product name from an unstructured slug list is not
  enough evidence to map on its own. No genuine orthopaedic range found in this capture.
- **NSK United Kingdom Limited** — 745 held products from `nsk-shop.co.uk`, fully structured
  by the company's own categories (Surgical, Contra-angles, Oral Hygiene, Dental Laboratory,
  Air Turbines, Clinical Micromotors, Endodontics, Autoclave, Mobile Dentistry...). Every
  division is dental equipment; nothing in the captured range is orthopaedic. This looks like a
  genuine mismatch between the NHS Supply Chain award and the crawled catalogue — either NSK's
  orthopaedic (power tool / bone-cutting) line sits on a domain or brand not yet found, or this
  award needs a different routing decision. Not something to force-map. Flagged to
  OUTSTANDING.md.

### `publishedElsewhereNeedingCategory` (6) — one real lead, left for a ruling

Checked each supplier's captured divisions against this framework's in-scope categories
(`ortho:cement`, `ortho:equip`, `ortho:implant`, `ortho:trauma`):

- **Anetic Aid Ltd, Sectra Limited, Meril UK Pvt Ltd, Mölnlycke** — captured ranges are
  theatre/wound/digital/MIS-stapling products respectively. Nothing orthopaedic in any of them.
- **Fannin (UK) Limited** — no capture at all (robots.txt-forbidden); its "publishedElsewhere"
  status comes from a route other than `differentiator-category-map.json`, so there is nothing
  here to inspect or map.
- **Johnson & Johnson MedTech** — the one genuine lead. Alongside divisions already mapped
  elsewhere (Surgery, Cardiovascular, Digital Surgery), several `hub: null` (uncategorised)
  divisions read as plausibly orthopaedic: **Power Tools** (7 products), **Robotics** (7 —
  J&J's orthopaedic robotics line is VELYS), **Enabling Tech** (7), and a single-item **Attune
  Knee System** division (1 — Attune is DePuy Synthes's branded total knee system). Not
  force-mapped this run: J&J MedTech is captured once and spans a large number of frameworks
  (`mis`, `theatres`, `oncology`, `vascsurg` are already mapped from the same capture), so
  changing its category map is a cross-framework vocabulary decision, not a single-framework
  fix, and outside this run's "don't touch other frameworks' data" rule. Flagged to
  OUTSTANDING.md as a genuine, evidenced lead for whoever does that vocabulary pass.

## No differentiator/ledger change

`data/differentiator.json` and `data/coverage-ledger.json` are unchanged from `main` — nothing
was crawled, mapped, resolved, or seeded that met the evidence bar. Total Orthopaedic Solutions 3
stays at 21.8% (22/101 published), 54 left. Rebuilding `build_differentiator.py` /
`build_coverage_ledger.py` on a clean clone confirms the ledger this run started from already
matches `main` exactly, so nothing needs re-stamping or landing this run — `./land.sh` was not
run because there is nothing to land.
