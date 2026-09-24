# Total Orthopaedic Solutions 3 — framework-coverage batch, 24/09/2026

Picked as the lowest-coverage STARTED framework with real `Left` this run, after
Ultrasound Scanners, CT Scanners, Polymer Aprons, Operating Theatres, Surgical
Instruments, Examination Gloves and Laboratory Diagnostics were all confirmed
still-exhausted (unchanged since 22–23/09, see
`docs/framework-coverage-exhausted.json`).

## Two suppliers' held ranges checked product-by-product; two crossed into published

**Meril UK Pvt Ltd.** 277 held products across 12 flat divisions (infection
prevention, diagnostics, vascular/peripheral-vascular/neurovascular
intervention, endo surgery, urology, cardiac surgery, ENT, orthopaedics,
sports medicine, surgical robots) — a genuinely mixed-division supplier
(`data/identity-vocabulary-policy.json`). Checked the "Orthopedics" (23),
"Sports Medicine" (22) and "Surgical Robots" (5) divisions product-by-product
against Meril's own merillife.com product pages. 38 product-override entries
added via `scripts/_seed_meril_orthopedics_overrides_0924.py`:

- 4 total knee implant systems (Desti Knee, Freedom, Opulent, Opulent Uni)
  and 7 total hip implant components (the Latitud range + Auric Bionik) →
  `ortho:implant`, confirmed against merillife.com/our-products/orthopedics/.
- 14 Sports Medicine soft-tissue-fixation implants (the Rotafix suture-anchor
  range, Filahook, Flexibutton, Endostud, the four Bio Ference/Ference
  interference screws, the two meniscal-repair systems) → `ortho:implant`,
  matching the existing Conmed "Implants And Suture Anchors" and Arthrex
  suture-anchor precedents already in the map.
- 10 fracture-fixation devices (plate-and-screw systems, six named
  intramedullary nailing systems) → `ortho:trauma`.
- 4 joint-replacement robotic-system captures (Misso Robotic System / Cuvis
  Joint, each captured twice under two category pages — "Orthopedics" and
  "Surgical Robots" — not de-duplicated this run, see below) →
  `ortho:equip`, matching the existing Stryker "Robotic Consumables — Total
  Knee" precedent.

Left held, checked and confirmed a different speciality or not
orthopaedic-specific: "Peek Peek" (unexplained fragment name, no confirmable
identity); "Handx Robotics" / "Mizzo Flex Sa Robotics" / "Mizzo Endo 4000"
(confirmed via merillife.com as general-surgery/soft-tissue robotic
platforms — urology, gynae, thoracic, colorectal, bariatric, ENT, GI,
oncology — not orthopaedic); the "Persist" arthroscopy-tower range (four
endoscopes/cameras, two monitors, shaver system, cold light source, trolley)
and "Spinuss Rf Console" (confirmed via web search as an RF ablation console
used in spinal endoscopy/sports medicine/ENT) — established precedent in
this map files this shape as `mis:energy`/`theatres:theatre` rather than
`ortho:equip` (Farla Medical "Arthroscopy Ablation Probe" → `mis:energy`,
Stryker "Arthroscopic Pumps and Tubing Systems" → `theatres:theatre`, Conmed
"Edge Bipolar Arthroscopic Rf System" → `mis:energy`), so correctly
categorising it is a different speciality's work, out of scope here. The
remaining 8 divisions (360 Infection Prevention Solution, Diagnostics,
Vascular Intervention, Endo Surgery beyond its already-mapped
staple/trocar/clips/energy rows, Urology, Cardiac Surgery, Peripheral
Vascular Intervention, Ent, Neurovascular) are real ranges in different
specialities, untouched.

None of the 38 published (all landed in `held`) — Meril's capture carries no
manufacturer detail record (`data/supplier-product-detail.json`) and no
NHSSC catalogue match for any of these specific product names, the same
capture-route-gap shape as Hospital Innovations (^o551/^o458-class,
`docs/framework-coverage-findings-2026-09-23-tos3.md`). Correct and harmless:
they will start publishing the moment that gap is fixed, with no further
mapping work needed.

**Macromed UK Ltd.** 44 held products under one flat "Uncategorised"
division (macromed.co.uk's sitemap carries no division structure) — spans
spinal implants and vascular/GI interventional devices. Macromed's own site
organises 22 of the 44 under two brand archives
(`product-category/spinal-products/`, 4 items, and
`product-category/interventional-products/`, 18 items); the rest exist as
live product pages outside any current taxonomy term. 18 product-override
entries added via `scripts/_seed_macromed_spine_overrides_0924.py`, each
independently confirmed against the originating manufacturer's own site
(ulrich medical AG for 12 spinal-implant-hardware items — cerv-X, pezo,
tezo, ADD/ADDplus, cosmicMIA, neon3, obeliscPRO, osmium, uCentum, golden
gate, mambo; Cousin Biotech for IntraSPINE; Woven Orthopedic Technologies
for OGMend, FDA 510(k)-cleared for spine surgery) → `ortho:implant` (15,
including GBM Cervical Cage matched from Macromed's own spinal-products
archive), and DBM Medical/Kuros Biosciences for the antibiotic allograft and
MagnetOs bone-graft-substitute range → `ortho:equip` (3), matching the
existing Hospital Innovations/Lindare Medical precedent that allograft/
bone-graft material files as `ortho:equip` not `ortho:implant`.

Left held/unconfirmed this run: Gangi-SoftGuard and the Morrison Steerable
Needle (confirmed via web search as AprioMed interventional-radiology
biopsy-needle devices, not orthopaedic); Bishop Microcatheter, Run & Run,
Amica MW/RF Ablation, Jeti Thrombectomy System (read as vascular/
interventional by name and by sitting outside the spinal-products archive,
but not individually source-confirmed this run); the 18-item interventional-
products archive (Hilzo stent range, ALN Vena Cava Filter, Cera Vascular
Plug, Fustar Steerable Sheath, BioMimics 3D, Angiodroid, NeverTouch
Gold-Tip EVLT Fibre, the two Dophi ablation systems, Micro Stent, Blueflow)
— confirmed vascular/GI devices, different speciality.

**3 of the 18 Macromed overrides published**: Neon3, Osmycin Antibiotic
Allograft and Ogmend already carried a manufacturer detail record from an
earlier, unrelated detail-crawl (`readOn: 2026-09-08`), so — unlike the
other 15 — they cleared `build_differentiator.py`'s publish gate immediately.
Macromed UK Ltd crosses from `heldOnly` into `published` on this framework.

## Two suppliers examined and confirmed no route

**NSK United Kingdom Limited.** 745 held products, all under nsk-shop.co.uk
divisions (Oral Hygiene, Autoclave, Air Turbines, Clinical Micromotors,
Surgical, Contra-angles, Dental Laboratory, Mobile Dentistry, Endodontics,
Couplings, Maintenance, Spare parts & components) — every division is
dental equipment (handpieces, turbines, contra-angles, dental implant
surgery motors), confirmed by division/product names. This Hub's vocabulary
does carry a `dental` speciality (`dental:equip` = "Chairs, handpieces &
lab") that would fit this range, but mapping 745 products to a different
speciality is out of scope for an ortho-framework batch — no product in the
captured range is orthopaedic, so nothing here helps Total Orthopaedic
Solutions 3. Left held and unmapped; a future dental-framework batch (or a
`data/coverage-deferrals.json`-style policy question about whether "NSK
United Kingdom Limited" as awarded genuinely trades in orthopaedics at all,
given its only public storefront is 100% dental) is the right next step, not
recorded to OUTSTANDING.md this run since it is not a decision blocking
progress — simply out of scope.

**TRB Chemedica (UK) Ltd.** 9 held products, mostly hyaluronic-acid
viscosupplementation joint/tendon injections (OSTENIL, OSTENIL MINI,
OSTENIL PLUS, OSTENIL TENDON, ArthroZheal®) plus an ultrasound course
listing ("Introduction to MSK Ultrasound Course") and "HAXL One". These are
genuinely orthopaedic-adjacent (osteoarthritis joint-lubricant injections)
but do not fit any of this framework's four in-scope categories
(`ortho:cement`/`equip`/`implant`/`trauma` — bone cement, equipment,
hardware implants, fracture fixation; none is an injectable pharmaceutical
category). Left held rather than forced into a category that doesn't
describe them — a genuine scope mismatch, not a mapping gap.

**Sovereign Medical.** 1 captured-nothing-counted item — already correctly
mapped to `ortho:brace` (ABDOBACK abdominal belt, cryotherapy knee/ankle
braces) but blocked by the same capture-route/detail-record gap as Hospital
Innovations. Moot for this framework's coverage regardless: `ortho:brace`
is not one of Total Orthopaedic Solutions 3's four in-scope categories.

## Domain search: unchanged since yesterday

The 8 `needDomain` suppliers (Contura Orthopaedics, Advita Ortho UK,
Permedica UK, Orthopediatrics EU, Marquardt UK, M.D.M Medical, Future
Health Works, Surgalign UK) were exhaustively re-checked yesterday
(23/09/2026, `docs/framework-coverage-findings-2026-09-23-tos3.md`) with no
confirmable domain found for any of them. Not re-searched today —
re-litigating an unchanged, same-day-verified negative result would not be
new work.

## Net effect on Total Orthopaedic Solutions 3's ledger this run

Coverage moved from 27.7% (28/101) to **28.7% (29/101)** — Macromed UK Ltd
crossed into `published`. `Left` dropped from 18 to 17 (Meril UK Pvt Ltd
moved from `heldOnly` into `publishedElsewhere` — its 38 new ortho mappings
are correct and will publish once the capture-route-detail gap is fixed, but
the bucket move itself does not change the `Left` count, per
`scripts/build_coverage_ledger.py`'s own documented behaviour — a supplier
publishing anything anywhere is counted once under
`publishedElsewhereNeedingCategory`, not `heldNeedingCategory`).

Remaining actionable (17): 8 needDomain (exhausted, no route — candidate for
`framework-coverage-exhausted.json` if the framework is picked again with an
unchanged supplier set), 2 heldNeedingCategory (Hospital Innovations and NSK
United Kingdom Limited — both examined, capture-route gap and
different-speciality respectively, no route this run), 6
publishedElsewhereNeedingCategory (Anetic Aid, Fannin UK, Mölnlycke, Sectra
— zero held remainder, fully resolved; Meril UK Pvt Ltd — checked in full
this run; TRB Chemedica — checked, genuine scope mismatch), 1
capturedNothingCounted (Sovereign Medical — capture-route gap, and moot for
this framework's scope regardless).
