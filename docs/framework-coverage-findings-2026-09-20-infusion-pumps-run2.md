# Framework coverage findings — Infusion Pumps, 20/09/2026 (run 2)

Run: `differentiator-framework-coverage`, picked **Infusion Pumps and Administration Sets and
Associated Products** (`bloodtx`) again — an earlier run today (`e97ac98`) left it at 22.2%
(6/27) with a findings doc and an OUTSTANDING flag, so the ledger picker surfaced it again since
its `Left` count was still non-zero.

## What was different this time

The earlier run's check of the 10 `publishedElsewhere` suppliers sampled each division's
recorded 4 examples and its `hub` category, and on that basis concluded ICU Medical (incl.
Smiths Medical)'s "Infusion Therapy" division (84 products) and Vygon (UK)'s "Vascular Access
Devices" division (28 products) held nothing that read as pump hardware or an administration
set. This run read every product name in both divisions in full (`data/supplier-products.json`),
not just the 4-example sample the division-level mapping was originally decided on.

### ICU Medical (incl. Smiths Medical) — 10 products found, genuinely mis-scoped by the sample

The "Infusion Therapy" division was mapped to `vascular:conn` on 4 sampled examples (Clave
Neutron, Nanoclave Manifolds, a needlefree connector, a large-bore extension set) — correct for
most of the division's 84 products, which genuinely are connectors, extension sets, catheters
and blood-collection consumables. But the same division also contains, by name:

- Infusion pumps (`bloodtx:pumps`): Plum 360 Large Volume Infusion Pump, Cadd Solis Vip
  Ambulatory Home Infusion System, Cadd Solis Infusion System, Medfusion 4000 Wireless Syringe
  Infusion Pump.
- Pump-dedicated administration/extension sets (`bloodtx:pump`): Plum Dedicated Sets, Cadd
  Medication Cassette Reservoirs With Flow Stop Free Flow Protection, Cadd Administration Sets
  With Flow Stop Free Flow Protection, Cadd Extension Sets, Cadd Administration Sets With Air
  Eliminating Filter, Cadd High Volume Administration Sets With Flow Stop Free Flow Protection.

This is the same shape of miss the division already had one prior fix for — 6 arterial-blood-gas
products (Pro Vent Plus etc.) were pulled out to `bloodcoll:abg` via the `product-override` tier
on 07/09/2026, for the same reason (a 4-example sample under-represents an 84-product division).
Added 10 more `product-override` entries the same way, so the division's `vascular:conn` mapping
is untouched for its other ~68 products.

### Vygon (UK) — 1 product found

The "Vascular Access Devices" division is mapped to `vascular:sec` on its PICC/tunnelled/midline
catheter products, correctly for those. One product in the same division — "Accufuser® Elastomeric
Infusion Pump" — is filed by the supplier under its own "Elastomeric Pumps" sub-category and is a
disposable elastomeric infusion pump, not a vascular access device. Added as a `product-override`
to `bloodtx:disp`.

### Fresenius Kabi Ltd — reverted, do not touch (caught before landing)

I initially also added an `nhssc-term` entry mapping Fresenius Kabi's "Agilia / Volumat infusion
pump administration sets..." term to `bloodtx:pump`, on the reasoning that the term's own name
names an infusion pump range. **This was wrong to add** — the earlier run today had already found
and mapped this exact (supplier, term) pair to `pharma:iv`, deliberately, at a dedicated mapping
sprint (`decidedIn: "NHSSC map sprint 28/08/2026"`), and explicitly declined to change it,
writing it up as a judgement call for Lou (OUTSTANDING ^o563) rather than deciding it themselves.
My new entry would have silently won the lookup in `build_differentiator.py` (later entries for
the same key override earlier ones) and overturned that recorded decision without a ruling —
exactly the failure the brief's hard rules exist to prevent. Caught by diffing the map against
`git show HEAD:...` before landing; the entry has been removed, `pharma:iv` is restored, and
Fresenius Kabi is back in `publishedElsewhere`, unchanged from the earlier run today. No new
OUTSTANDING item needed — ^o563 already covers it; do not duplicate.

**Process note for future runs of this pipeline**: before adding an `nhssc-term` or
`product-override` entry, diff-check the target (supplier, term)/(supplier, division) key against
the current map first — a `publishedElsewhere` bucket means "not published into this framework's
categories," not "unmapped." It can already carry a deliberate mapping to a different category.

## Net result

- ICU Medical (incl. Smiths Medical): now published into `bloodtx:pumps` and `bloodtx:pump`.
- Vygon (UK): now published into `bloodtx:disp`.
- Fresenius Kabi Ltd: unchanged, `pharma:iv` as decided 28/08/2026.
- `verify.py` passes.

## Before / after

- Before this run: 22.2% (6/27 published), 11 left.
- After this run: 33.3% (9/27 published), 8 left.
