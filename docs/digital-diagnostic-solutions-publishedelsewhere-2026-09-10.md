# Digital Diagnostic Solutions — the 11 "published elsewhere" suppliers, checked 10/09/2026

`build_coverage_ledger.py` names 11 suppliers on the Digital Diagnostic Solutions
framework as `publishedElsewhereNeedingCategory` — crawled and published, just not
under `digital:hw`/`digital:sw`, described in the script's own docstring as "mapping
work, not crawl work". Checked each one individually against
`data/differentiator-category-map.json` before touching anything. Result: none is a
safe mapping fix today.

| Supplier | Crawled division(s) | Current category | Digital content? |
|---|---|---|---|
| Draeger Medical UK | (unnamed), 6 products | `neonatal:resp` | No — CPAP headgear only |
| Epredia | Immunohistochemistry, Histology Consumables, Histology Instruments, Digital Pathology, Cytology | `pathology:*` | No — "Digital Pathology" division's own examples are slides/coverslips, not software |
| Getinge | "Uncategorised" (351, HELD), + theatres:perfusion (29), ssd:endo (1) | mixed | **Maybe** — see below |
| Haemonetics | (unnamed), 1 product | `cardiology:equip` | No |
| Huntleigh | Vascular Assessment, Fetal Monitoring, Vascular Treatment, Patient Monitoring | `ultrasound:hand`, `cardiology:ctg`, `wound:comp`, `monitoring:gen` | **Maybe** — see below |
| Olympus (KeyMed) | (unnamed), 1 product | `mis:energy` | No |
| Leica Microsystems (UK) | (unnamed), 36 products | `pathology:histo` | No — histology consumables/accessories |
| Philips | (unnamed), 36 products | `respiratory:resp` | No — CPAP masks/accessories |
| Roche Diagnostics UK | 11 entries, various | `pathology:consum`, `pathology:poct`, `diabetes:strip` | No — test strips, controls, consumables |
| Siemens Healthineers | 2 entries | `pathology:poct` | No — POCT cartridges/controls |
| Sysmex UK | Flow Cytometry, Products Detail, Diagnostics, Life Science, Pathology, Oncology | `pathology:*`, `marketing:content`, none | No — lab consumables; "Life Science"/"Oncology" are marketing-site sections, not products |

## The two genuine maybes

**Getinge.** The HELD "Uncategorised" bucket (351 products, `hub: null`) carries
`data/differentiator-category-map.json`'s only example set for this supplier that
includes "Tegris" and "Talis Hub" — Tegris is Getinge's asset-tracking/workflow
software for sterile processing, and "Talis Hub" reads as a connectivity module for
its Talis anaesthesia line. Both would fit `digital:sw`'s stated scope ("clinical and
departmental software systems ... asset-tracking"). But the same 351-product bucket
is a single flat division with no internal split recorded — the other three sampled
examples ("Getinge Assured Tape Vh2O2") are sterilisation consumables, nothing to do
with digital. Tagging the whole division `digital:sw` would misclassify most of it as
software; there is no product-level field in the category map to split on.

**Huntleigh.** The "Vascular Assessment" division (15 products, `hub: ultrasound:hand`)
lists "Dopplex® Vascular Reporter Software" by name among 14 hardware Doppler probes.
Same problem: the division, not the product, carries the category.

## Why this isn't fixed today

`data/differentiator-category-map.json` entries are keyed at (supplier, division)
granularity — one `hub` value per division, not per product. Neither of the two
maybes can be resolved without either (a) a product-level category override the
schema doesn't currently support, or (b) a narrower re-crawl that gets Getinge's and
Huntleigh's software lines filed under their own division on the crawl side. Forcing
either whole division to `digital:sw` today would publish real hardware as software,
which root rule 14/HUB-VERIFICATION-STANDARD's "never force a category" bar rules out.
Left as a genuine vocabulary/schema gap, not actioned.
