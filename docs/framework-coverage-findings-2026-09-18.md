# Framework coverage batch — 18/09/2026 findings

Picked framework: **Examination Gloves** (21.1% coverage, 9 left going in), after two
higher-priority skips explained below.

## Skipped: Insulin Pumps, CGM & HCL (16.7%, the ledger's top pick)

All three remaining suppliers (Abbott Laboratories Limited, Medtronic, Urathon Europe Ltd)
turned out to already be fully investigated and queued — `identity-vocab-decision-queue.md`
entry #8 and OUTSTANDING `^o527` were both added earlier today, before this run started,
documenting the same three parent/division identity questions this run independently
re-confirmed:

- Abbott's captured products are entirely NHSSC nutrition-line data (Ensure range); Abbott's
  own site (abbott.co.uk) is recorded refused 31/08/2026. No route to the FreeStyle Libre/CGM
  range under this seed record without a ruling on which Abbott entity contracts the award.
- Medtronic's captured products are entirely NHSSC theatres/vascular/cardiology data; their
  own site (medtronic.com) is recorded refused 08/09/2026. Same shape as Abbott — no route to
  the MiniMed pump range under this seed record without a ruling.
- Urathon Europe Ltd was crawled fresh 15/09/2026 (104 products, 5 divisions: Bathing/
  Showering/Toilet Aids, Around The Home, Mobility Aids, Moving & Handling, Bedroom Aids) —
  no CGM item appears anywhere in the crawlable catalogue. Their claimed Yuwell Anytime CGM
  distribution is real (per the seed record's own evidence) but is not on a page the crawler
  can reach, matching `^o524`'s existing note about a durable manual-product mechanism.

Since every actionable supplier here needs a decision already sitting on the queue, and none
of it is crawl or mapping work, this run added a `data/coverage-deferrals.json` entry for the
framework (same mechanism as Radiotherapy Ancillary Devices) so the picker stops re-selecting
it. Coverage and Left are untouched — this only removes it from the pick list until Lou rules
on entry #8.

## Skipped: Digital Diagnostic Solutions (18.5%)

Checked before picking Examination Gloves. All 8 remaining suppliers (Draeger, Haemonetics,
Olympus/KeyMed, Leica Microsystems, Philips, Roche Diagnostics, Siemens Healthineers, Sysmex
UK) already carry recorded, dated refusals (robots.txt blocks, non-resolving domains, no
readable product API) from 20/08–31/08/2026 — this is the exact framework named in the brief's
warning about the 06/09/2026 incident where 34 already-refused suppliers were wrongly
re-crawled. `actionable.crawlable` and `actionable.needDomain` are both 0 — there is no
permitted route left on this framework right now. Not deferred (nothing here needs a ruling
from Lou, it's simply exhausted for now), just left alone.

## Worked: Examination Gloves

Priority-order work through the framework's actionable suppliers:

- **Globus (Shetland) Ltd** (held, 881 products) — already flagged `^o521` (17/09): 848 of 881
  are an unstructured "Uncategorised" sitemap-slug list, and the 15-item "Hand Protection"
  division turns out on inspection to be sub-category labels ("Surgical Gloves", "Single Use",
  "Chemical Protection", "Vending Gloves"...), not real product names — mapping any of them to
  infection:latex/nitrile/vinyl would publish fake "products". Confirmed the existing flag is
  correct; did not force a mapping.
- **Ergea UK and Ireland Limited (Althea UK and Ireland Limited)** (need domain) — already
  flagged `^o522` (17/09) as needing a human identity check before any domain is seeded. This
  run initially added ergeagroup.com and ran a crawl (0 products — the site is Managed
  Equipment Services, no product catalogue) before noticing the existing flag; **reverted**
  both the seeded link and the resulting refusal record so the framework is exactly as it was
  for this supplier, respecting the pending human check.
- **Cargo Services Far East Limited** (need domain) — confirmed via the company's own site
  (cargofe.com, page title "Cargo Services Far East", matching the framework-awarded name
  exactly) as a Hong Kong-headquartered freight forwarder. Seeded the domain and ran the
  crawler: refused (no product post type, no WooCommerce catalogue — a freight forwarder's
  site, as expected). Converts this supplier from blocked ("need domain") to a properly
  documented dead end.
- **Medicom Healthpro Ltd** (need domain) — identity confirmed (CH 12650877, active, SIC 32500
  "Manufacture of medical and dental instruments and supplies", UK subsidiary of the global
  Medicom Group per multiple independent business directories) but no distinct operating
  domain could be confirmed. medicom.com is the Medicom Group's global corporate site and does
  not name "Medicom Healthpro Ltd" anywhere found; treating it as this subsidiary's own site
  would be exactly the kind of identity chain rule 10 warns against. Left unresolved — see
  OUTSTANDING.
- **ORN International T/A Spectra Corporate** (need domain) — the literal trading name on the
  NHS Supply Chain brief is "Spectra Corporate"; spectracorporate.com/.co.uk no longer resolve
  (DNS failure, checked 18/09/2026). The parent entity ORN (INT) LIMITED (CH 07254574) trades
  as ØRN International at shop.ornworkwear.com / orn-int.com, and third-party resellers
  (bksafetywear.co.uk, misteruniform.co.uk) sell "ORN" branded gloves, but nothing found ties
  the specific "Spectra Corporate" trading name used in the NHS award to that site. Left
  unresolved — see OUTSTANDING.

No differentiator/coverage change from this framework this run (the one supplier resolved,
Cargo Services Far East, came back refused). The genuine progress is: one supplier moved from
blocked to a documented dead end, two domain-identity questions raised as fresh judgement
calls, and one already-exhausted framework (Insulin Pumps) taken out of the picker's rotation
so it stops being reselected for no movement.

---

## Addendum, 18/09/2026 (outstanding-sweep 12:10 run) — Digital Diagnostic Solutions: the three held Sysmex products now publish

`^o464` / `^o508` said the three Sysmex UK products mapped to `digital:sw` on 13/09/2026
(Quantcenter, Slidecenter, Slideviewer) would publish once `^o457`'s re-crawl ran. The
re-crawl ran on 17/09/2026 and they did **not** publish, still held with "no source carries
this product". 17/09's own findings diagnosed why: the override supplies the category, but a
product also needs a capture in `data/supplier-product-detail.json`, and two 300-second
`crawl_supplier_product_detail.py --supplier "Sysmex UK"` runs both stayed inside a long
flow-cytometry reagent tail without ever reaching indexes 48, 57 and 59 of a 1254-product
range. The three product pages had already been confirmed live by hand.

The blocker was therefore **which products a run reaches**, not whether a source exists — the
detail crawler could only ever be pointed at a supplier, never at a named product.

**Fix:** `scripts/crawl_supplier_product_detail.py` gains `--product NAME` (repeatable, with
`--supplier`). It *selects* from the supplier's own recorded range in
`data/supplier-products.json`; a name that is not already in that range is **refused and
reported, never searched for**, and each selected product still goes through the same
`capture_one()` path, so an unreadable page is still skipped rather than summarised. A
targeted run does not move or restamp the sweep's resume cursor
(`state/product-detail-cursor.json`), which is left exactly where the scheduled sweep put it.
Seven new tests in `test_product_detail_cursor.py` cover the selection, the refusal of an
invented name, and the cursor guard; the cursor-guard test was proven to fail when the guard
is removed.

**Result:** all three captured first time from Sysmex's own product pages, `parsed:
"structured"` (JSON-LD `Product` schema), on 18/09/2026:

| Product | Source read |
|---|---|
| Quantcenter | `https://www.sysmex.co.uk/products/products-detail/quantcenter/` |
| Slidecenter | `https://www.sysmex.co.uk/products/products-detail/slidecenter/` |
| Slideviewer | `https://www.sysmex.co.uk/products/products-detail/slideviewer/` |

All three now publish under `digital:sw`. Differentiator published count 35264 → 35267.

**Coverage:** Digital Diagnostic Solutions 18.5% → **20.4%** (10 → 11 suppliers published,
8 → 7 left); Sysmex UK moves out of `publishedElsewhere`. This is the first supplier to
publish under `digital:hw`/`digital:sw` in this framework, so `^o422`'s "none publishes
under digital:hw/sw" no longer holds as written — the practical ceiling it describes is
real but sits one supplier lower than recorded.

**Two other rows in this rebuild are not from this work.** A plain
`build_differentiator.py` + `build_coverage_ledger.py` rebuild on an unmodified clone of the
same `main` moves them identically: Radiotherapy Ancillary Devices (oncology → imaging,
oncology; 2 → 4 published, 15.4% → 30.8%) and Ultrasound Scanners (7 → 6 left). Both are
commit `4ae9101`'s already-landed vocabulary decisions, which never had the ledger rebuilt
after them. Verified against a control clone before committing.

## Clinical and Sharps Waste Management — G&N Laboratory identity resolved, crawled, published (run started 17:07)

**Picked Clinical and Sharps Waste Management (21.4%, 5 left) after Digital Diagnostic
Solutions (20.4%, 7 left) re-confirmed as a practical ceiling** — its 7 remaining suppliers
are the same "majors captured only incidentally elsewhere, no genuine range to categorise"
pattern already logged (`^o469`, reconfirmed again this run, unchanged).

**G&N Laboratory identity.** NHS Supply Chain's own contract launch brief names an awarded
supplier "G&N Laboratory", which the seed carried as a standalone unverified record (added
09/09/2026, no domain, no company number, `needDomain`). Confirmed same company as the
existing Hub supplier `Griffiths and Nielsen Ltd` (Advanced Wound Care / Vascular Therapy /
Syringes & Needles frameworks): `lab.gandn.com` (footer-branded "G&N Medical | Griffith &
Nielsen") is a subdomain of `gandn.com`, and its footer registered address (Stane Street,
Slinfold, Horsham, West Sussex RH13 0GN) matches the Companies House registered office for
GRIFFITHS & NIELSEN LIMITED, 01201146 — the same number this record's own
`companyNumberProof` had confirmed earlier the same day via `gandn.com`'s footer address.
Not a name-similarity guess: same domain family, same registered address as an
already-proven company number. Merged in `data/supplier-seed.json` (alias added, Clinical
and Sharps Waste Management framework transferred, standalone record deleted) and recorded
in `company-aliases/alias-overlay.json`.

**A second, unrelated wrong match found and removed in the same pass.**
`data/company-financials.json` separately carried `G&N Laboratory` -> `G & N LABORATORY
LIMITED` (06424823) — a DIFFERENT company from GRIFFITHS & NIELSEN LIMITED (01201146),
`matchConfidence: "probable"`, `matchedOn: "name search on Companies House — NOT verified
against a recorded number"`. This is exactly the bare-name-search matching rule 11
forbids, and it predates today's proper resolution. Removed rather than re-keyed, since
`Griffiths and Nielsen Ltd` already carries its own correctly-sourced financials entry
(01201146, matched by registered-office address, the same method already accepted for this
record). `data/company-press.json` also carried an orphaned `G&N Laboratory` key (empty
`items`, so nothing lost) — deleted, its alias moved onto the survivor, header counts
recomputed via `refresh_company_press.py`'s own `recount()` rather than hand-edited (root
cause of an earlier incident, 14/08/2026, per that script's own comment).

**Crawl.** `gandn.com` itself carried a same-day refusal ("the sitemap carries 0 URLs...")
from earlier today's `companyNumberProof` work. Tested live before overturning it — not "in
passing": direct calls to `scripts/crawl_supplier_site.py`'s own `sitemap_products('gandn.com')`
and a full `crawl()` retry both succeeded cleanly, reading `sitemap_index.xml` ->
`products-sitemap.xml` -> 27 real product URLs, including exactly the framework's own
products (Eco-Sharps, Sharps Containers, Griff® Pac, Griff® Carton, Griff Eco Range, Ecodas
Waste Treatment System). The earlier refusal's exact cause wasn't isolated (transient
network response, most likely, since the same domain string and same code path succeeded
minutes later) — recorded here rather than left unexplained. Re-crawled via
`--retry-refused`, captured 27 products across 10 divisions on the company's own taxonomy.

**Category mapping.** Only the two divisions inside this framework's scope
(`infection:nitrile`/`infection:ppe`/`infection:sharps`) were mapped, per the hard rule not
to touch other frameworks' data this run: `Clinical Waste Containment` (6 products: Eco-Sharps,
Griff Eco Range, Griff® Grip, Sharps Containers, Griff® Pac, Griff® Carton) and `Clinical
Waste Treatment` (1: Ecodas Waste Treatment System), both -> `infection:sharps`, evidenced by
explicit product names. Recorded in
`data/differentiator-map-parts/Griffiths-and-Nielsen-Ltd.json` and merged. The other 8
divisions (Wound Dressings, Wound Care and Prevention, Mechanical DVT Prophylaxis, Medical
Compression, Colorectal Scopes, Rehabilitation Products, Safety Needles & Syringes,
Laboratory Products — 20 products) are left unmapped: they belong to this supplier's OTHER
framework awards, out of scope for this run.

**Missing step found and fixed: mapped-but-unpublished.** After mapping + rebuilding, the 7
sharps/waste products stayed OUT of both `products` and `held` in `differentiator.json` —
traced to `build_differentiator.py`'s `if not sources: held.append(...)` gate: a
sitemap-route crawl gives a product NAME but no per-product detail page, so a mapped
division with no separate product-detail capture never publishes. Ran
`scripts/crawl_supplier_product_detail.py --supplier "Griffiths and Nielsen Ltd" --domain
gandn.com --product <name>` for all 7 named products (all captured first time, structured
JSON-LD product pages). Rebuilt: published count 35267 -> 35274, all 7 under
`infection:sharps`.

**Coverage:** Clinical and Sharps Waste Management 21.4% -> **28.6%** (3 -> 4 of 14
suppliers published, actionable 5 -> 4).

**Same gap re-found on the framework's other actionable suppliers, left unforced.** The 4
remaining `publishedElsewhereNeedingCategory` suppliers (Cardinal Health U.K. 432 Ltd, Fannin
(UK) Limited, Medline Industries — none yet in `supplier-products.json` at all — and
Vernacare, which is crawled and whose relevant divisions ARE already correctly mapped to
`infection:sharps`/`infection:ppe`) do not publish for the same "no sources" reason. Tried
`crawl_supplier_product_detail.py` against Vernacare's 17 relevant product entries
(`Large Range`, `Small Range`, `Chemopure® Gloves`, etc.) and all 17 were skipped: "the
sitemap carries no product URLs to match against". Vernacare's original crawl read from site
NAVIGATION, not a sitemap of real product pages — its "products" under these divisions are
generic size/range labels (`Large Range`, `Pocket Size Range`), not individual products with
their own page to source from. Same shape as the Globus (Shetland) Ltd Hand Protection
finding (`^o521`): mapping a navigation label as if it were a sourced product would publish
something that doesn't exist. Left held, not forced.

**Peer collision during landing.** First landing attempt (from a different clone) hit
`f65a443` (the Espere/Ossur merge, landed mid-work) — the record-level no-loss check flagged
an untouched-file drift, and once cleared, `git rebase origin/main` produced real conflicts
in the shared single-line JSON files (`company-alias-registry.json`, `company-financials.json`,
`company-press.json`, `supplier-seed.json`) despite no overlapping records, purely because
both commits touched the same minified blob. Aborted per policy (never hand-resolve a
generated JSON conflict) and redid the entire batch on a fresh `./begin.sh` clone taken after
`f65a443`, rather than resolving the rebase.
