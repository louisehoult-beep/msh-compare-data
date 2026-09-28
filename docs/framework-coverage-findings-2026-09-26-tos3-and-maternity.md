# Framework coverage — TOS3 and Maternity, findings 26/09/2026

Moved out of `OUTSTANDING.md` 28/09/2026 (over the 400-char line limit) by
`out-of-hours-backlog-clearer` — content unchanged, just relocated. Original items ^o620,
^o622.

## TOS3 (Total Orthopaedic Solutions 3) — ^o620

3 suppliers' domains resolved this run:

- **Marquardt UK** (marquardt-uk.com, registration-number match) — robots/API refuse crawl,
  bespoke CMS, no product-path fix in scope.
- **Advita Ortho UK Limited** (uk.advita.com, address-tier match) — crawled clean but
  captured its literature-library "product" post type (videos/brochures/code-of-conduct
  PDFs), not the real device pages at `/shoulder/equinoxe-*/` and
  `/vantage-total-ankle-system/`. Held correctly, nav-labels-are-not-products shape; needs a
  targeted product-path recrawl, out of scope for this batch.
- **Contura Orthopaedics Ltd** (contura.com, address-tier match) — robots.txt refuses crawl.

**Sovereign Medical published:** 9 products (ABDOBACK/ABDOHIP belts, 4 FREEZ-brand
cryotherapy braces, 2 Madglove splints, PRESSORELAX kit) mapped to the existing `ortho:brace`
category and given per-product detail via a targeted `crawl_supplier_product_detail.py` run —
verified against 2 live product pages.

Coverage 29.7% → 30.7% (30→31 published, 16→13 left).

Still needDomain: Future Health Works Ltd (separate OUTSTANDING item, ^o621), M.D.M Medical
Ltd (in liquidation, no findable site), Orthopediatrics EU Limited (registered office is a
nominee/agent address, does not match its real Swansea trading office — domain-proof-tier
near-miss, correctly unresolved), Permedica UK Limited (no UK-specific site found), Surgalign
UK Ltd (parent Surgalign Holdings filed Chapter 11 bankruptcy June 2023, hardware/biologics
assets sold to Xtant Medical, digital health to Augmedics — likely defunct, no route).

## Maternity — ^o622

Organon UK's mixed "Uncategorised" catalogue (pharma spanning many specialities) resolved per
the standing mixed-division-mapping policy: 4 unambiguous products (MIUDELLA copper IUS,
XACIATO vaginal gel, NuvaRing, NEXPLANON) product-override mapped to `womens:sex`/`gyn` and
given per-product source pages.

Coverage 29.8% → 31.6% (17→18 published, 17→16 left).

Ambiguous dual-indication items (Pregnyl/hCG, Follistim/FSH, Ganirelix, Celestone Soluspan)
correctly left held, not mapped.

**Separate finding, not investigated further (out of scope for this batch):** Vernacare's own
crawl (117 products, incl. a "Womens Health" division of 6 already mapped to `womens:mat`)
shows only 7 published + 19 held in `differentiator.json`'s complete `heldBySupplier` count —
~91 products unaccounted for by either bucket. Worth a dedicated pipeline check of
`build_differentiator.py`'s own-source loop; not chased here since it isn't specific to this
framework and touching it risks every supplier.
