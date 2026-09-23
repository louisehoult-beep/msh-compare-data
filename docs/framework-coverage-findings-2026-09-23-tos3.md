# Total Orthopaedic Solutions 3 — framework-coverage batch, 23/09/2026

Picked as the lowest-coverage STARTED framework with real `Left` this run, after
Ultrasound Scanners, CT Scanners, Operating Theatres and Polymer Aprons were all
confirmed still-exhausted (unchanged since 22/09) and Surgical Instruments and
Examination Gloves were newly confirmed exhausted (see
`docs/framework-coverage-exhausted.json`).

## Two suppliers moved from `needDomain` to a definite state

**Lavender Medical.** Web search found lavendermedical.com; its own About Us
page names the legal entity "Lavender Medical Limited" and gives the address
"646 Blackhorse Road, Letchworth Garden City, SG6 1HD", which matches
Companies House's registered office for LAVENDER MEDICAL LIMITED (06828106)
exactly — an on-site legal-entity-name match, stronger than the
domain-proof-tier address-only tier. Domain added to `supplier-seed.json`.
`crawl_supplier_site.py --supplier "Lavender Medical" --domain lavendermedical.com`
returned "robots.txt disallows automated reading of this site" — a genuine,
recorded refusal, not a re-crawl of an existing one.

**Hospital Innovations.** Web search found hospitalinnovations.com; its own
footer/contact page names "Hospital Innovations Limited" and its South Wales
headquarters (Concept House, Talbot Green Business Park, CF72 9FG), matching
Companies House's registered office for HOSPITAL INNOVATIONS LIMITED
(04261709) exactly. Domain added to `supplier-seed.json`.
`crawl_supplier_site.py --supplier "Hospital Innovations" --domain www.hospitalinnovations.com`
read all 83 of 83 product pages cleanly (0 unread) via the schema.org
per-page/breadcrumb fallback route.

### The 83 products span several specialities (mixed-division-mapping)

Hospital Innovations is a UK tissue bank / allograft supplier. Its catalogue
covers orthopaedic bone-graft and revision-instrument products, spine
(PliaFX), sports medicine (NanoFX, Hyalofast, meniscus/tendon allograft),
ENT/CMF (Piezotome/Piezomed rhinoplasty and CMF tips), and plastics/breast
reconstruction (DermACELL, Fortiva porcine dermis, Tutomesh bovine
pericardium) — one flat "Uncategorised" division cannot take a single hub tag
(mixed-division-mapping policy, `data/identity-vocabulary-policy.json`).

11 products whose own name unambiguously names orthopaedic anatomy or an
orthopaedic-specific surgical term were mapped to `ortho:equip` (matching the
existing precedent for allograft/tendon material already in the map — Lindare
Medical Ltd's "Allograft Cancellous Bone" and frozen tendons are both
`ortho:equip`, not `ortho:implant`), via
`scripts/_seed_hospital_innovations_ortho_overrides_0923.py`:

- Allograft Femoral and Humeral Heads
- Allograft HTO Wedges
- Stulberg Hip Positioner
- Stulberg Leg Positioner
- Fromm - Femur and Tibia Triangles
- Tibial Wedge Clamp
- CupX - Acetabular Cup Extraction System
- Femoral Component Extractor
- Glenosphere Component Retractor
- Bodycad Fine Osteotomy™
- Orthovise™

The remaining 72 stay held: generic bone-graft shapes with no anatomic
specificity (chips, cubes, particulate, cortical struts/plates/dowels/wedges,
iliac crest/ilium strips — used across dental, spine and orthopaedic surgery
alike), Osteochondral Allograft/Meniscus Allograft (reads as Sports Med, filed
Uncategorised rather than under the supplier's own "Sports Med" division),
named orthopaedic-surgery instruments that trade knowledge — not the product
name alone — identifies (Hohmann Retractor, Bone Hooks, Jones Mallet,
Universal Screw Removal System), "Innomed Complete Catalogue" (a catalogue
link mislabelled as a product), and the spine/sports-med/ENT/dermal items
(real products, different specialities, out of scope for this framework this
run).

## The mapping does not publish anything yet — a capture-route gap

After `build_differentiator.py` + `stamp_notice.py`, total published count
was unchanged (36,378, exactly as before this run) and Hospital Innovations'
full 83 products landed in `held`, including all 11 mapped ones.

Cause: `crawl_supplier_site.py`'s per-page schema.org/breadcrumb fallback path
(used here because "the product URLs carry no path segment between the
product-path segment and the product's own slug" for the normal division
route) reads each page successfully (0 of 83 unread) and extracts the
product's name and division, but does not write a
`data/supplier-product-detail.json` record (description/image/sourceUrl) for
any of them. `build_differentiator.py`'s publish gate requires either a
manufacturer detail record OR an NHSSC catalogue match before a category
mapping can turn into a published row ("no source carries this product —
neither the manufacturer's own page nor NHSSC"); Hospital Innovations has
neither, so every one of the 83 products — mapped or not — stays held.

This is the same shape as Electro Spyres (^o551) and Altomed (^o458): a
capture-route problem, not a mapping one, and fixing it means teaching
`crawl_supplier_site.py`'s fallback path to also persist a detail record per
page — a script change, out of scope for a data batch. The domain and the 11
mappings are left in place: they are correct and harmless now, and will
start publishing the moment that capture-route gap is fixed, with no further
mapping work needed.

## Net effect on Total Orthopaedic Solutions 3's ledger this run

Coverage unchanged today (27/101, 26.7%) — no supplier crossed into
`published`. Two of the ten `needDomain` suppliers are now resolved to a
definite, sourced state (1 refused, 1 blocked on the capture-route gap
above) rather than an open domain search; eight remain unconfirmed this run
(Contura Orthopaedics — see ^o588 for its own domain-proof mismatch,
confirmed unchanged in this run's fetch of contura.com — Advita Ortho UK,
Permedica UK, Orthopediatrics EU, Marquardt UK, M.D.M Medical, Future Health
Works, and Surgalign UK — the last now known to sit under a bankrupt US
parent, Surgalign Holdings, Chapter 11 in 2023).

Candidate domains checked and rejected for the remaining eight (none met the
domain-proof-tier bar — a name match to a global/parent site is not
sufficient, an address or on-site legal-entity-name match is required):
Advita Ortho UK's uk.advita.com carries no legal-entity or address
information anywhere on the site or its linked legal notice; Contura
Orthopaedics' contura.com footer copyright reads "Contura International Ltd",
a different legal entity; Permedica UK's only findable site is the Italian
parent's (permedica.it), with no UK-specific presence; M.D.M Medical's only
address hit (Southampton, via a supplier directory) does not match Companies
House's registered office (London) for the company.
