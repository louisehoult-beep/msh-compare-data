# Total Orthopaedic Solutions 3 — framework-coverage batch, 23/09/2026 (2nd run)

Continuation of today's earlier TOS3 run
(`docs/framework-coverage-findings-2026-09-23-tos3.md`), which left coverage
at 26.7% (27/101, Left 19) after confirming Ultrasound Scanners, CT Scanners,
Operating Theatres, Polymer Aprons, Surgical Instruments and Examination
Gloves all still exhausted. This run picked up where that one stopped:
Total Orthopaedic Solutions 3 remained the lowest-coverage STARTED
framework with real `Left`.

## Johnson & Johnson MedTech — RESOLVED, 27 → 28 published suppliers

The ledger buckets J&J MedTech as `publishedElsewhere`: it already
publishes 24 Ethicon products (sutures, staplers, energy devices — theatres/
mis) from the NHSSC catalogue, which hid the fact that its own-site crawl
(jnjmedtech.com, 868 products, verified 08/09/2026) ALSO carries the DePuy
Synthes orthopaedic range, sitting entirely in one flat "Uncategorised"
division of 709 sitemap-derived names. `publishedElsewhere` suppliers are
not offered to the picker as crawl/mapping work, so this range had never
been looked at for this framework.

**No identity ruling needed.** A separate seed record, "DePuy Synthes (J&J
MedTech)", also lists TOS3 in its own `frameworks` field, which looked at
first like a parent/subsidiary award-crediting question. It isn't:
`data/frameworks.json`'s actual TOS3 supplier roster (the ledger's real
awardee list) names only "Johnson & Johnson Medical Ltd", which resolves
via the existing alias registry straight to the "Johnson & Johnson MedTech"
seed record. "DePuy Synthes (J&J MedTech)" is not one of the 101 awarded
suppliers the ledger counts for this framework at all — its own
`frameworks` entry for TOS3 looks like leftover bookkeeping, left untouched
(a different record, out of scope for this batch). The award and the
product range are the same UK legal entity's own site; this is a plain
mapping job, not a merge decision.

### 127 products mapped, product-level (mixed-division-mapping)

Only products whose own name unambiguously names orthopaedic anatomy or an
orthopaedic-specific Synthes/DePuy trade term (LCP, intramedullary nailing,
named arthroplasty systems) were mapped, via
`scripts/_seed_jjmedtech_ortho_overrides_0923.py`:
ortho:implant (32 — knee/hip/shoulder arthroplasty systems, spine implants,
acetabular components), ortho:trauma (85 — LCP fracture-fixation plates,
intramedullary nails, pelvic/foot/ankle fixation systems), ortho:cement (5 —
vertebroplasty/kyphoplasty balloon and cement systems), ortho:equip (6 —
named instrument sets, Velys robotic hip navigation).

Deliberately excluded, left held:
- **Craniomaxillofacial (CMF)**: Matrixorbital/Matrixmandible/Trumatch Cmf
  products name orbital/mandible/cranial anatomy — a different speciality.
- **Veterinary orthopaedics**: TPLO/TTA (Tibial Plateau Levelling
  Osteotomy / Tibial Tuberosity Advancement) and Pancarpal Arthrodesis are
  canine procedures (DePuy Synthes Vet) — not NHS human care, out of scope
  for an NHS Supply Chain framework entirely.
- **Foreign-language duplicate captures**: jnjmedtech.com's sitemap carries
  a separate URL/title per locale for the same product (Spanish,
  Portuguese, Dutch, German). Only the English capture of each product was
  mapped this run.
- **Category/landing-page-shaped captures** ("Biologics Spine Trauma
  Solutions", "3D Patient Specific Anatomic Spine Model", "Conduit Lateral
  Switch Plate", "Locking Reconstruction Mini Plate System"): read as a
  section heading or an unclear one-off rather than a named product.

### Capture-route gap, closed for this supplier

Today's earlier run found Hospital Innovations' 11 mapped products stayed
held because its sitemap-derived capture never wrote a
`data/supplier-product-detail.json` record, and called the fix (teaching
the range-crawler's fallback path to persist a detail record) "a script
change, out of scope for a data batch." That framing was wrong: a
PURPOSE-BUILT script for exactly this, `scripts/crawl_supplier_product_detail.py`,
already exists and does not need any change — its route B (locate the
product's URL from the site's own XML sitemap by matching the product
name, then read the page's JSON-LD or a heuristic text extraction) reads
jnjmedtech.com's pages cleanly with no code change at all.

Ran `crawl_supplier_product_detail.py --supplier "Johnson & Johnson MedTech"
--domain jnjmedtech.com` against all 127 named products (`--site-budget 900
--products-limit 200`): 111 captured this run (16 skipped — mostly pages
the heuristic extractor couldn't isolate content from, e.g. "Coda Anterior
Cervical Plate" — left held, not guessed), plus records already on file
from an earlier capture.

**One bad capture caught and removed before publish.** The sitemap
name-match for "Volt Proximal Humerus Plating System" resolved to
`.../products/robotics/ottava-robotic-surgical-system/system/` — an
unrelated robotic-surgery product page, not the named plate system.
Checked every one of the 149 J&J MedTech detail records for a word-overlap
mismatch between the product name and its captured URL slug; this was the
only one flagged. Deleted the bad record from
`data/supplier-product-detail.json` before running `build_differentiator.py`,
so it stays correctly held rather than publishing wrong content under the
right name.

### Net effect

`build_differentiator.py`: 36,378 → 36,488 published (+110). J&J MedTech
now publishes 134 products total (24 Ethicon + 110 DePuy Synthes: 74
ortho:trauma, 29 ortho:implant, 5 ortho:equip, 2 ortho:cement), moving it
from `publishedElsewhere` into `published` for this framework's `ortho`
speciality gate.

TOS3 coverage: 26.7% (27/101, Left 19) → **27.7% (28/101, Left 18)**.

## Macromed UK Ltd — identified but not yet mapped this run

Held under one flat "Uncategorised" division of 44 sitemap-derived slug
names (`hasDivisions: false`), spanning vascular stents (Hilzo biliary/
oesophageal/pyloric/colonic/ureteric stents), a vena cava filter, ablation
systems and vascular plugs — none of it orthopaedic — alongside a genuine
spine/bone-graft range. `WebFetch` of macromed.co.uk confirmed its own
navigation is only two divisions, "Spine" and "Interventional"; the
sitemap-derived flat capture lost that structure, matching the
Globus Medical UK Ltd / Joint Operations precedent for Macromed's own
"Spine" division (already ortho:implant in the map for those two).

Confirmed via each product's own page on macromed.co.uk (primary source,
not inference):
- **IntraSPINE®** — dynamic interlaminar stabilisation device.
- **GBM Cervical Cage** — 3D-printed titanium cervical/lumbar interbody
  fusion cage.
- **Osmycin** — antibiotic-elution allograft for orthopaedic/spinal
  infection prevention.
- **MagnetOs Putty / MagnetOs Granules** — synthetic bone graft substitute
  for spinal fusion, extremities and pelvis.

All five would map to ortho:implant on the existing Conmed UK Ltd/Acumed
Ltd "Biologics"/"Bone Void Fillers" precedent (branded, manufactured graft
products, as distinct from Lindare Medical Ltd's raw allograft-material
ortho:equip precedent). **Not mapped or detail-crawled this run** — left
for a future run — because Macromed has the same sitemap-only capture
shape as Hospital Innovations, so mapping alone will not publish anything
without also running `crawl_supplier_product_detail.py` for these five
names, and this run's time went to the much larger, already-confirmed
J&J MedTech range instead. The rest of Macromed's 44-item range (stents,
vascular plugs, ablation, vena cava filter) is genuinely a different
speciality (vascular/interventional radiology/GI) and stays held.

## NSK United Kingdom Limited — confirmed correctly held, no route

745 products, entirely dental equipment (handpieces, endodontics, dental
laboratory, oral hygiene — divisions: Spare parts & components, Surgical,
Contra-angles, Oral Hygiene, Dental Laboratory, Air Turbines, Clinical
Micromotors, Endodontics, Autoclave, Mobile Dentistry). The one item
naming "bone surgery" — "VarioSurg Tips – Bone Surgery" (and its
duplicate) — sits inside NSK's own "Surgical" division alongside
Endodontics/Perio/Implant Preparation/Sinus Lift/Extraction tips: a dental
oral-surgery piezosurgery attachment, not an orthopaedic-specific product
by name. No unambiguous orthopaedic item exists in NSK's range — correctly
held, no ruling needed (mixed-division-mapping guard: a dominant-context
reading is never sufficient).
