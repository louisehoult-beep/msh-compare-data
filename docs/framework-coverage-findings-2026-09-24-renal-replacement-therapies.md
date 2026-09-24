# Framework coverage findings — Renal Replacement Therapies Services, Technologies and Consumables — 24/09/2026

Picked as the lowest-coverage STARTED framework with `Left` > 0 that was not
already in `docs/framework-coverage-exhausted.json` or
`data/coverage-deferrals.json` (the 7 frameworks ahead of it on the ledger's
"lowest-coverage STARTED" list were all already exhausted). Coverage 28.0%
(7/25) at start.

## What moved

**MedScience Distribution published.** Its 315-product capture files under
30+ divisions taken from the supplier's own site filing, none of which maps
to renal — but one product's own name is unambiguous: "Fistula & Renal
Procedure Packs – Sterile, Ready-to-Use Dialysis & Access Care Kits", filed
under the generic "Dressing Packs" division. Fistula/renal procedure packs
are an established named product line for arteriovenous-fistula
haemodialysis access (cross-checked against the same category sold by
365healthcare.com and ITL BioMedical). Added as a `kind: product-override`
entry -> `renal:hd`, per the mixed-division-mapping policy
(`data/identity-vocabulary-policy.json`), in
`scripts/_seed_medscience_renal_override_0924.py`.

The division's two other "Renal"-named products (Concave Round Neck Renal
retractors, under "Surgical Instruments & Accessories") are surgical
retraction instruments for renal *surgery*, a different speciality from
replacement-therapy dialysis access, and are correctly left at
`surgical:retract` — not touched.

Coverage after: **32.0% (8/25)**.

## What did not move, and why

- **BD — Becton, Dickinson (54 products), LINC Medical (4), Acime UK Ltd
  (25)** — the other three `publishedElsewhereNeedingCategory` suppliers.
  Every captured product name was scanned; none is renal/dialysis/CRRT/
  peritoneal. BD's captured range (NHS Supply Chain catalogue cache only,
  not a full site crawl) is vascular access, blood transfusion and
  continence; LINC is drainage; Acime is furniture and rehab equipment.
  Correctly published elsewhere — no mapping bug, nothing to fix.
- **VWS (UK) Ltd (heldNeedingCategory)** — Veolia Water Technologies' UK
  arm, crawled as a flat 53-product list (no division structure — the
  sitemap capture carries no company filing) of process names: Actiflo,
  Alizair, Anoxkaldnes MBBR, and similar. These read as Veolia's general
  industrial/municipal water-treatment technology names, with no product
  name carrying any medical or dialysis indication. `renal:water` ("Water
  treatment & managed service") exists in the Hub's own vocabulary and is
  plausibly what VWS was actually awarded for, but the mixed-division-
  mapping policy requires the *product's own name* to unambiguously
  identify the speciality before it is promoted — none of these 53 do.
  Correctly held. This is a genuine capture-quality gap, not a ruling
  question: the crawl may be reading the wrong part of Veolia's site (a
  generic industrial catalogue rather than a healthcare/dialysis-specific
  section, if one exists), which is a re-crawl/targeting question for a
  future run, not something to force-map now.
- **Nipro Medical UK Ltd, Xtra-Med (needDomain)** — both searched for a
  primary-source domain this run.
  - Xtra-Med's own site (xtra-med.com) is plainly the right trade (AVF
    cannulation needles, vascular-access surveillance, haemostasis devices
    for dialysis patients) and prints a postal address (Thorneycroft Farm,
    Kettleshulme, Cheshire SK23 7RG), but that address is the *director's*
    correspondence address on Companies House, not XTRA MED LIMITED's
    (05968756) registered office (Ian Woodward Accountancy Ltd, 57 High
    Street, Rowley Regis, West Midlands B65 0EH). No registration number
    appears anywhere on the site. Same shape as the Carleton Medical
    near-miss in `docs/domain-proof-address-route.md` — refused under the
    domain-proof-tier policy, not recorded.
  - Nipro Medical UK Ltd's only findable web presence is the global group
    site (nipro-group.com), including a page titled for the Southampton UK
    location; neither that page nor its immediate contact pages print an
    address or registration number for the UK entity (06993337, registered
    office Units 12-14 South Point Ensign Way, Hamble Le Rice, Southampton
    SO31 4RF). No proof route this run.

All 7 actionable items on this framework are now accounted for. Added to
`docs/framework-coverage-exhausted.json` so a future run doesn't
re-investigate the same dead ends — see `wouldReopenIf` there for what would
change that.

## A stale note spotted in passing, not acted on (out of scope this run)

`docs/framework-coverage-exhausted.json`'s Ultrasound Scanners entry
(22/09/2026) gives as part of its reason that Celtic SMR Ltd needs "a
per-product override capability... that is out of scope for a data batch."
That capability now exists and was already in active use before this run
(`kind: product-override` in `scripts/build_differentiator.py`, used by
today's earlier Meril/Macromed orthopaedics batch and by this run's
MedScience fix). Whether it actually solves Celtic SMR's CMS-artefact
problem needs its own look — not touched here, since Ultrasound Scanners is
a different framework from the one picked this run.
