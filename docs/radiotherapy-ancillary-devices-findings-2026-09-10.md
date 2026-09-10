# Radiotherapy Ancillary Devices — two findings, checked 10/09/2026

Working the lowest-coverage-with-work-left framework this run. 5 of 8 "Left" suppliers
(Brainlab Ltd, Healthcare Supply Solutions Limited, Oncology Systems Ltd (OSL), PTW-UK Ltd,
Vision RT Ltd) had verified domains found and added to `data/supplier-seed.json`, then
crawled: none runs WordPress/WooCommerce or publishes a readable product sitemap, so all
five are now recorded as genuine refusals rather than "needs domain" — real movement, not a
mapping fix. The remaining 3 are the two findings below plus MIS Healthcare (already
extensively logged under ^o320/^o328/^o329/^o405 — not repeated here).

## 1. Promedics identity mismatch — not merged, not mapped

NHS Supply Chain's own contract launch brief for this framework
(https://www.supplychain.nhs.uk/product-information/contract-launch-brief/radiotherapy-ancillary-devices-incl-dosimetry-patient-positioning-and-qa-devices/)
names an awarded supplier **"Promedics Ltd"**, exact wording, fetched 10/09/2026.

The Hub's alias registry resolves this to the existing **"Promedics Orthopaedics Ltd"**
seed record (Blackburn-based orthotics/bracing company; aliases already on file include
"Promedics" and "MARPLACE (NUMBER 722) LIMITED"). That company's live site
(promedics.co.uk, fetched 10/09/2026) has 38 crawled divisions — Wrist & Hand, Spinal
Support, Knee Braces, Ankle & Footwear, Arm & Upper Body, Paediatric, splints, collars,
braces — and **zero mention of radiotherapy, oncology, dosimetry or patient positioning for
radiotherapy anywhere on the site.**

Companies House `advanced-search` for active companies containing "Promedics" (checked
10/09/2026) returns only two: PROMEDICS ORTHOPAEDICS LIMITED (06455477) and AK PROMEDICS
LIMITED (13851541, Luton) — no standalone active "Promedics Ltd" to re-point the award to.

**Not resolved either way.** Two live possibilities: (a) Promedics Orthopaedics Ltd
genuinely does supply radiotherapy positioning devices (e.g. Orfit thermoplastic sheet,
which the company's own "Accessories" division already lists and which is a material used
for both orthotic splinting and radiotherapy immobilisation masks) through a trade/NHS-only
catalogue that isn't on its public retail site; or (b) the awarded "Promedics Ltd" is a
different, now-dissolved entity and the alias merge is wrong. **No action taken** — none of
the 38 divisions has been mapped to a radiotherapy category, and the alias has not been
changed. This needs Lou's ruling, not a guess.

## 2. Xiel Ltd — correctly categorised, but the framework doesn't route to its category

Xiel Ltd's "Radiotherapy" division (23 products — Sensus SRT-100, Cablon Medical CNERGY
Go!, C-Rad Catalyst+ HD PT — genuine radiotherapy positioning/simulation kit) is already
mapped in `data/differentiator-category-map.json` to `imaging:mobile`, whose vocabulary
label in `data/compare-suppliers.json` is literally **"Mobile & RT simulation"**. That is
this framework's own business.

But `data/compare-suppliers.json`'s `infection`-style `route` mechanism only sends the
`oncology` speciality to this framework's URL — not `imaging`, which is where the
vocabulary already places RT simulation kit, and arguably not `nuclear` either
(`nuclear:dosim` = "Personnel & environmental radiation dosimetry", also named in this
framework's own title). Because of that, `build_coverage_ledger.py`'s inScope check
(`c.split(":")[0] in specKeys`) never counts Xiel's correctly-filed products toward this
framework's coverage — it shows as `publishedElsewhere` instead, which reads as a mapping
gap when the mapping is actually already right.

**Not changed.** Widening a framework's speciality route touches how every framework's
coverage is computed, not just this one — a routing-scope decision, not a single-supplier
fix, and out of scope for a batch limited to one framework's own data.
