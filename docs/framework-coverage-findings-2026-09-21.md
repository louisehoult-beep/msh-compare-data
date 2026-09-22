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
  call).

  **CORRECTED 22/09/2026 — the paragraph that stood here was wrong, and
  `^o570` carried the error for a day.** It said `quidelortho.com` files its
  real products under `/gb/en/laboratory-professionals/...` deep taxonomy
  paths that the slug matcher and the default `--product-path` list cannot
  place, and that the supplier therefore needed a `--product-path`
  investigation before any detail crawl could work. Measured against the
  site's own sitemap index on 22/09/2026, that is not what the site does.
  Its GB sitemap holds 741 URLs, of which **310 sit under `/gb/en/products/`**
  and only 76 under `/gb/en/laboratory-professionals/` (mostly resource and
  landing pages). `products` is already in `find_product_url()`'s default
  segment list, the pattern matches anywhere in the path, and the product's
  own slug is the last segment — so the default matcher places these products
  exactly as it is, on `/global/en/products/<family>/<slug>`. No
  `--product-path` flag was needed and none was used.

  **The real constraint was run time, not path shape.** `SITE_BUDGET_S` is 60
  seconds per supplier and the sitemap-index build alone consumed most of it,
  so each default-budget run reached one product. Re-run as
  `--supplier "QuidelOrtho (Ortho Clinical Diagnostics UK)" --products-limit
  200 --site-budget 480` — the flag that exists for exactly this case — it
  captured **306 of 322 products**, and QuidelOrtho went from **0 to 309
  published rows** (repo total 36,009 → 36,318, nothing else moved).
  `verify.py` exit 0, 19 warnings, identical to the baseline measured on the
  unmodified tree in the same session.

  **One real fault was found on the way, and is NOT fixed here.** Two of the
  five runs against this site aborted with "robots.txt disallows automated
  reading — skipped entirely" and captured nothing, while
  `quidelortho.com/robots.txt` reads `User-agent: * / Allow: /` and
  `base.allowed("quidelortho.com")` returns `True` when called directly,
  before and after each aborted run. The refusal is transient — most likely a
  burst-triggered 403 on `/robots.txt`, which `allowed()` deliberately treats
  as a site-wide refusal. Changing that rule is a behaviour change affecting
  every supplier, so it was not made unattended; it is raised as its own
  OUTSTANDING item instead. Until it is decided, a run that reports this
  refusal should simply be re-run before the supplier is believed to be
  refusing.
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
