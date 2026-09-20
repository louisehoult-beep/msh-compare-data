# Framework coverage findings — Infusion Pumps, 20/09/2026

Run: `differentiator-framework-coverage`, picked **Infusion Pumps and Administration Sets and
Associated Products** (`bloodtx`), 22.2% coverage, 6/27 published, 11 left before this run.

## What was checked

All 11 items in `Left`:

- **Arcomedical Infusion Ltd** (needs domain, 1 of 11) — already fully researched on 15/09/2026
  (see its `supplier-seed.json` note). `arcomed.com` is the international CODAN-group site and
  covers the global range, not a UK-specific one; the UK office address on that site matches the
  seed record's registered office exactly. Crawling it would publish the global catalogue under
  the UK entity name, which is exactly the kind of scope mismatch the verification standard rules
  out. Left un-domained, as before. Nothing new to do here without a UK-specific source.
- **10 `publishedElsewhere` suppliers** (Avanos Medical UK Limited, Mediq Healthcare UK Ltd,
  Crest Medical Ltd, Fannin (UK) Limited, Fresenius Kabi Ltd, GBUK Group, ICU Medical (incl.
  Smiths Medical), Reliance Medical, Vygon (UK)) — each already publishes products in the
  Differentiator, but under categories outside this framework's `bloodtx:*` scope. Checked every
  captured division/term for each against the `bloodtx` vocabulary (gravity administration sets,
  pump-dedicated sets, infusion pumps, disposable pumps) for a genuine unmapped-vocabulary gap
  per the brief's step 4.
  - Nine of the ten are correctly categorised elsewhere and have no captured product that reads
    as an infusion pump, administration set or associated consumable — e.g. Fannin (UK) Limited's
    only captured product is an ECG electrode; ICU Medical's captured "Infusion Therapy" division
    is IV connectors/manifolds (`vascular:conn`), not pump hardware or admin sets; GBUK Group's
    captured range is vascular access devices. No held (uncategorised) products exist for any of
    the ten — `actionable.heldNeedingCategory` is 0 for this framework, confirmed against
    `data/differentiator-category-map.json`.
  - **Fresenius Kabi Ltd is the one exception, and it is a judgement call, not a clear miss.**
    Its NHSSC-term entry in `data/differentiator-category-map.json` reads:
    - term: "Agilia / Volumat infusion pump administration sets; CATSmart intra-operative
      autotransfusion system"
    - example: "Administration set VLON72 oncology set for infusion 0.2 filter 1 KZero needle
      free"
    - currently mapped to `pharma:iv` ("IV fluids & aseptic"), decided in the "NHSSC map sprint
      28/08/2026" on the stated reasoning "oncology infusion administration set with in-line
      filter — IV fluids & aseptic administration."

    Agilia and Volumat are Fresenius Kabi's own infusion pump ranges, so the term as written
    ("infusion pump administration sets") reads more like `bloodtx:pump` ("Pump-dedicated sets")
    than `pharma:iv`. But `pharma:iv` is a defensible read too — administration sets are
    definitionally IV-fluid delivery devices, and the existing decision was made deliberately at
    a dedicated mapping sprint, not a gap. Reclassifying it would overturn a `decidedIn`
    provenance entry made by that process, on the strength of one product record. Per the hard
    rule against inventing a category decision, this is written up rather than changed: see the
    OUTSTANDING.md line dated 20/09/2026 (^o563).

## Net result

No data changes made this run. Every actionable item was either already resolved as far as the
verification standard allows (Arcomedical), already correctly categorised elsewhere (9 of 10
`publishedElsewhere` suppliers), or a genuine judgement call now on OUTSTANDING.md (Fresenius
Kabi). The framework's coverage number (22.2%, 6/27) is unchanged by this run — that reflects the
real state, not a run that did nothing.

## Before / after

- Before: 22.2% (6/27 published), 11 left.
- After: 22.2% (6/27 published), 11 left. Unchanged — see above.
