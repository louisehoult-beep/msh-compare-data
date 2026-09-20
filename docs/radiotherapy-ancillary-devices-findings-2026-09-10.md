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

## 2. Xiel Ltd — SUPERSEDED 20/09/2026. Both halves of this finding were wrong.

**This section originally said Xiel Ltd's Radiotherapy division was correctly mapped to
`imaging:mobile`, and that it only read as a coverage gap because the framework did not
route the `imaging` speciality. Neither claim survived checking on 20/09/2026. The
division has been remapped and the reasoning is below, kept because the mistake is an
instructive one.**

**a. The mapping was wrong, and the original reading came from three product names.**
The 10/09 finding rested on "Sensus SRT-100, Cablon Medical CNERGY Go!, C-Rad Catalyst+
HD PT" and on `imaging:mobile`'s label reading "Mobile & RT simulation". Read in full on
20/09/2026 from `data/supplier-products.json`, the division's 23 products are almost
entirely radiotherapy patient positioning and immobilisation: MOLDCARE RI II,
thermoplastics for radiation therapy, vacuum bags and positioning cushions, the Aerial
proton couch top, TBI STEP, and the belly/pelvic, prone-breast, lung-board, paediatric
and SRS positioning solutions. None of those is a mobile imaging unit or a radiotherapy
simulator. The label has to be read inside its own speciality — `imaging` is
"Diagnostics and imaging", so `mobile` means mobile imaging equipment and RT simulators,
not immobilisation hardware. A thermoplastic mask is not diagnostic imaging.

The division is now mapped to `oncology:posn` ("Radiotherapy patient positioning and
immobilisation devices"), a type added 20/09/2026 under the identity policy table's
vocabulary-gap policy and named from this framework's own title. The two Sensus SRT-100
units are superficial radiotherapy TREATMENT systems rather than positioning devices and
are split out at product level to `oncology:radio`.

**b. The routing claim was factually wrong.** This section said the framework's route
"only sends the `oncology` speciality to this framework's URL — not `imaging`". It sends
both. `data/compare-suppliers.json` carries a route to
`radiotherapy-ancillary-devices` under `imaging` AND under `oncology`, and did so at
commit `399085f`, before any of the 20/09 changes — checked by reading that commit's own
copy of the file. `build_coverage_ledger.py`'s `inScope` check therefore WOULD have
counted Xiel's `imaging:mobile` products toward this framework. Whatever made the
supplier read as outstanding work, it was not the routing.

**c. There is no hidden ledger bug here, and nothing was mis-scoped in silence.** The
worry this section raised — that `inScope` (`c.split(":")[0] in specKeys`) quietly
under-counts frameworks — was checked across the whole ledger on 20/09/2026. Frameworks
with no speciality routed to them are not silently mis-scoped: they are given the
explicit state `UNMAPPED`, the route string "no Hub speciality mapped to this framework",
and their own table in `docs/COVERAGE-LEDGER.md`, which documents what UNMAPPED means.
The behaviour is deliberate, labelled and already visible. Do not "fix" it as a bug.

**The lesson worth keeping:** a category label read on its own, against three example
product names, is not evidence of a correct mapping. Read the division's full product
list out of `data/supplier-products.json` before concluding that an existing mapping is
right — that is the same check that would have caught this on 10/09.
