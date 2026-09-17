# Framework coverage findings — 17/09/2026

Picker's lowest-coverage STARTED frameworks with non-zero `Left` (16.7% Insulin
Pumps, 18.5% Digital Diagnostic Solutions) were re-checked and confirmed exhausted
again — same conclusion as the 16/09 run
(`docs/framework-coverage-findings-2026-09-16.md`), which is why this file re-raises
nothing about them beyond one new, narrower finding on Digital Diagnostic Solutions
below. No changes were made to either framework's data this run.

## Digital Diagnostic Solutions — Sysmex UK re-crawled, one stale-crawl bug closed

`Sysmex UK` was on the pre-05/09/2026 stale-crawl list (OUTSTANDING ^o457/^o464:
82 suppliers crawled before the flat-URL fix, never re-crawled). Re-crawled this run
against `www.sysmex.co.uk` — 1254 products, 6 divisions, clean capture.

Its three `digital:sw` product-override entries (Quantcenter, Slidecenter, Slideviewer
— decided 13/09/2026, `data/differentiator-map-parts/Sysmex-UK--framework-coverage-0913.json`)
are correctly matched by `build_differentiator.py`'s override tier, but **all three still
publish as HELD** with reason "no source carries this product — neither the
manufacturer's own page nor NHSSC". The override only supplies the category; a product
still needs an entry in `data/supplier-product-detail.json` (via
`scripts/crawl_supplier_product_detail.py`) or an NHSSC match before it counts as a
source. Two `crawl_supplier_product_detail.py --supplier "Sysmex UK"` runs (300s budget
each) captured 66 more of Sysmex's 1254 products this session, but the crawler works
the range in something other than list-index order and both runs stayed inside a very
long flow-cytometry antibody-reagent tail (hundreds of near-identical CD-marker SKUs)
without reaching Quantcenter (index 48), Slidecenter (57) or Slideviewer (59) in the
raw product list. Confirmed via `curl` that the three pages are genuine, live product
pages (`https://www.sysmex.co.uk/products/products-detail/{quantcenter,slidecenter,
slideviewer}/`, found via the site's own products sitemap) — this is a crawl-ordering/
budget gap, not a missing-domain or identity question. Needs either several more
`--site-budget` runs of the detail crawler on Sysmex UK, or a way to target it at named
products directly. No decision needed from Lou; this is purely mechanical follow-through
already covered by ^o457/^o464.

Net effect of the re-crawl + detail-crawl continuation: 106 more products published
site-wide (34884 → 34990), mostly in existing pathology categories, not Digital
Diagnostic Solutions — so this framework's own coverage (18.5%, 8 left) is unchanged
this run.

## Ultrasound Scanners — checked, both actionable items already parked

19.0%, 9 left. `MIS Healthcare` / `Medical Imaging Systems (MIS Healthcare)` duplicate
is the already-logged identity question (^o377) — left alone, not merged. `FUJIFILM
Sonosite Ltd` (`sonosite.com`) was attempted this run: the domain resolves and starts a
TLS handshake but never completes a response within the crawler's timeout, confirmed
directly with a manual `curl -v` (same outcome) — a genuine refusal, now recorded, and
consistent with the FUJIFILM Sonosite domain-proof issue already logged (^o363/^o487).
`Hitachi Medical Systems UK Ltd` is the already-logged Hitachi/Fujifilm merge question
(^o376 — Hitachi's diagnostic-imaging business, including ultrasound, was absorbed into
Fujifilm Healthcare in a 2021 acquisition; confirmed via web search this run, adding
no new fact beyond what ^o376 already states). Nothing here needed a new OUTSTANDING
line.

## Total Orthopaedic Solutions 3 — two new suppliers crawled, both mixed divisions

19.8%, 56 left, 47 needing a domain. Two suppliers already carried a verified domain in
`data/supplier-seed.json` (added 14/08/2026, both proved by company registration number
on their own site) but had never actually been crawled:

- **Osteotec Ltd** (`www.osteotec.co.uk`) — 60 products captured, one division
  ("Body Part"). Mostly genuine spinal/extremity implants (VADER Pedicle System, Cervical
  Cage, Anterior Cervical Plate, iFuse 3D Implant System, bone-graft substitutes) but the
  same division also carries surgical instruments/consumables (Percutaneous Burrs,
  Surgical Burs, Saw blades, K-wires) that are not implants. Same shape as the Salter
  Labs/Electro Spyres finding already logged (^o488): a flat division mixing categories
  needs product-level (override-tier) decisions, not a blanket division mapping. Not
  forced — held pending that work.
- **Lindare Medical Ltd** (`www.lindaremedical.co.uk`) — 14 products captured, one
  division ("Uncategorised"). Bone cement (Kyphon Xpede/VuE — would map cleanly to
  `ortho:cement`), vertebroplasty/kyphoplasty/RF-ablation devices, and frozen tendon
  allografts (orthobiologics, no clean match in this framework's four in-scope types:
  `ortho:cement`, `ortho:equip`, `ortho:implant`, `ortho:trauma`) all sit in one
  division. Same product-level-decision shape as Osteotec above. Not forced.

Both suppliers' raw product data is now captured and available for that product-level
mapping work whenever it's picked up; this run did not invent a category for either.
