# Framework coverage findings — 21/09/2026

Framework worked: **Laboratory Diagnostics, Point of Care Testing and Pathology
Managed Services** (`pathology` speciality). Coverage 23.8% → 25.4% (29 → 31 of
122 awarded suppliers published), Left 73 → 71.

## What moved

- **PHC Europe / PHCbi** — was captured under the wrong sitemap (`www.phchd.com`
  root, PHC Holdings' global/Japanese corporate site), which returned Japanese
  navigation-page titles ("診察券発行機…", "導入事例…") and repeated "PRODUCTS
  Comparative Chart" strings as if they were products — a `nav-labels-are-not-
  products` case. Re-crawled against the correct subsite already on record in
  the supplier's own seed entry (`https://www.phchd.com/eu/biomedical`, curated
  20/07/2026 but never used by the crawler) with
  `--product-path preservation --product-path incubation --product-path
  validation --product-path CO2incubators`: 91 real products, 13 divisions
  (ULT freezers, biomedical freezers, pharmaceutical/blood-bank refrigerators,
  CO2/multi-gas/heated/cooled incubators, climatic test chambers, LN2
  cryopreservation, nitrogen generators). 11 divisions mapped to
  `pathology:equip` (laboratory storage/incubation/sterilisation equipment);
  "Product Technology" (marketing feature pages, not products) and one stray
  blank-division product left held. Then ran
  `scripts/crawl_supplier_product_detail.py` with the same `--product-path`
  flags to capture manufacturer source pages (88 of 91 reached; the sitemap
  match needs the SAME `--product-path` flags as the site crawl or it silently
  falls back to the unmatchable root sitemap). Now publishes 70 products.
- **QuidelOrtho (Ortho Clinical Diagnostics UK)** — 322 products across 15
  divisions, all previously unmapped. Mapped 12 divisions this run (assay/
  reagent kits → `pathology:consum`, rapid lateral-flow/cardiac-panel tests →
  `pathology:poct`, instrument+assay divisions split as a list per Lou's
  mixed-division rule, e.g. Sofia Platform → `["pathology:equip",
  "pathology:poct"]`). Left held: "Uncategorised" (28 products, heavily mixed
  with "Redirect —" URL-redirect artifacts and service listings — a nav-label
  capture-quality problem, not a vocabulary gap), "Nulexa System" and "Ortho
  Summit System" (3–4 products each, ambiguous/generic names, too thin to
  call). **Still does not publish anything**: `quidelortho.com`'s sitemap
  files real products under `/gb/en/laboratory-professionals/...` deep
  taxonomy paths, not `/product/`-style slugs, so
  `crawl_supplier_product_detail.py`'s slug matcher (and the default
  `--product-path` list) cannot place any of them — needs its own
  `--product-path` investigation of that taxonomy before a detail crawl can
  populate sources. Left for a future run rather than guessing paths against a
  322-product site inside this session's budget.
- **LTE Scientific Limited** — 51 products, single flat "Uncategorised"
  division (site has no navigation structure), all genuinely laboratory
  decontamination/sterilisation equipment (autoclaves, washer-disinfectors,
  ovens, incubators, safety cabinets, fume cupboards) or its servicing.
  Mapped to `pathology:equip`. This supplier already had a manufacturer
  detail-crawl on record from 08/09/2026, so it published immediately once
  mapped: 40 of 51 products now live (the other 11 presumably still lack a
  matched detail page from that earlier crawl — not re-attempted this run).
- **Agilent Technologies UK** — one remaining unmapped division, "Vacuum
  Technologies" (3 products: pump/spares for the GC-MS range). Mapped to
  `pathology:equip`, consistent with Agilent's other 22 already-mapped
  divisions. **Cannot publish**: `agilent.com`'s robots.txt disallows
  automated reading outright (confirmed live, 21/09/2026), so no source page
  can ever be captured via this route. Structurally blocked, not a decision —
  left held.

## Cleanup: a dead part file was blocking every merge

`data/differentiator-map-parts/Electro Spyres Healthcare Limited.json`
(committed in `cea3740`, cardiology framework) proposed 8 decisions keyed on
URL-slug strings ("ultragel-ug50-ultrasound-gel-300ml-bottle") as if they were
division names. `merge_differentiator_parts.py` refuses any (supplier,
division) pair not already in the worklist, on principle — a part file cannot
propose a product-override, only a real division decision — so every one of
these 8 was refused on every run, and the script's `--apply` will not write
ANYTHING while any file has an unresolved refusal, blocking this framework's
merge and every other agent's for as long as the file sat there.

Checked before touching it: all 8 decisions are **already fully applied**,
byte-identical categorisation, under the correct real division names
(`UltraGel™ UG-50 300ml Clear Bottle` → `cardiology:gel`, `VitaTrode™ Midi-ACF
(36mm diameter) [Radiolucent]` → `cardiology:ecg`, etc.) already live in
`data/differentiator-category-map.json`. The file was pure dead duplicate
leftover carrying zero information not already published. Deleted it as
repo hygiene — no cardiology framework data changed, only a broken staging
artifact was removed so the merge pipeline works again for everyone.

## Also run: `scripts/union_differentiator_pairs.py --apply`

The PHC Europe recrawl produced entirely new (supplier, division) pairs the
worklist didn't have yet (new domain, new site structure). Ran the union
script to register them before the map decisions could apply — it is
append-only and touched no existing entry. It also picked up 11 new pairs for
Paragon 28 and 10 for Electro Spyres Healthcare Limited (unrelated suppliers,
already in `data/supplier-products.json` from other work) — these are now in
the worklist, unmapped, for whoever next works those frameworks.

## Process note for future runs

`./begin.sh` hands you a clone path, but **every single shell command in this
harness resets to the task's tracked "primary working directory" between tool
calls** — a `cd` in one command does not carry into the next one. Prefix every
command with `cd "$CLONE" &&` (or the literal path) for the whole session,
including one-liners, or work silently lands in the shared read-only checkout
instead. Caught this run before any commit: `git status` in the checkout
showed 3 modified/deleted files after several crawl/merge commands had run
there by mistake; reverted with `git checkout --` before any of it was staged
or pushed, no harm done.
