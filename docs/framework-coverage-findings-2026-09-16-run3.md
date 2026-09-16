# Framework coverage findings — 16/09/2026, third run of the day

Picker's list checked in order: Insulin Pumps/CGM (16.7%), Digital Diagnostic Solutions
(18.5%), Electrodes/Ultrasound Gels (18.9%) and Ultrasound Scanners (19.0%) were all
already worked earlier today (see `framework-coverage-findings-2026-09-16.md` and
`framework-coverage-findings-2026-09-16-run2.md`) — re-confirmed as exhausted or
deliberately queued, not re-worked.

## A false start on Electrodes/Ultrasound Gels — corrected before landing

This run independently re-derived the same product-level fix run 1 had already found
and explicitly declined to make (`OUTSTANDING.md` ^o488: Salter Labs UK Ltd and Electro
Spyres Healthcare Limited each hold one flat division mixing genuine ECG/gel items with
unrelated products, needing a product-override decision). Before checking OUTSTANDING.md
and today's earlier findings docs, this run went ahead and added 15 product-override
entries mapping the ECG/gel items to `cardiology:ecg`/`cardiology:gel`/`cardiology:ctg`/
`cardiology:equip`. On checking OUTSTANDING.md (should have been the first step, not a
mid-run correction — noted for next time) it became clear run 1 had already reviewed the
identical evidence and left it queued deliberately. **All 15 entries and their two
decision part files were reverted before landing** — nothing from that attempt is in
this commit. Separately, testing confirmed the fix would not even have moved the
framework's coverage number: both suppliers were crawled via a route that never
populated `data/supplier-product-detail.json`, so `build_differentiator.py`'s `sources`
requirement (manufacturer detail or NHSSC) fails regardless of category mapping — see
the new step below, which is what actually unlocks this shape of problem.

**Process point for next run: check `OUTSTANDING.md` and the day's existing
`framework-coverage-findings-*.md` files for the picked framework BEFORE doing any
analysis, not after.**

## Minimally Invasive Surgery, Related Equipment and Accessories — worked this run

Picked as the next lowest-coverage STARTED framework with real actionable Left once
Electrodes/Ultrasound Gels and Ultrasound Scanners were ruled out as already-exhausted
for today (20.0%, 24 left: 11 mapped-elsewhere, 3 held, 10 needDomain).

### Domains found and confirmed for 4 of 10 `needDomain` suppliers

Each confirmed from the supplier's own site (never a name-search alone, per verification
standard rule 11 — company **numbers** were not asserted here, only domains):

- **Venturis Medical Ltd** → `venturismedical.com` — own "About" page states the UK
  address "International House, 64 Nile Street, London, N1 7SR", matching the seed's
  existing company-number-candidate record's address style exactly.
- **Winners First Trading Limited** → `winners1trading.com` — own "About us" page names
  the company and gives "7 Bell Yard, London, WC2A 2JR".
- **SRA Developments** → `bowa-medical.co.uk` — the awarded name is now a trading name:
  the company's own current site states "BOWA MEDICAL UK is the trading name of SRA
  Developments Ltd" and "In November 2016, SRA Developments Ltd was acquired by
  BOWA-electronic GmbH & Co. KG". A genuine successor-site identity, not a guess.
  `sradevelopments.co.uk` itself no longer resolves (SSL handshake failure).
- **Medecon Healthcare UK** → `medecon.co.uk` — own site's copyright footer states
  "© 2026 by Medecon Healthcare UK Ltd" at the address "9 Ridgeway, Crendon Industrial
  Park, Long Crendon, Buckinghamshire HP18 9BF". Also already named in
  `data/compare-suppliers.json`'s `mis` speciality route with the same URL and an
  "instruments" (GIMMI laparoscopic range) type — this domain find corroborates and
  completes a record only half-built there.
- **Schultz Medical (UK) Limited** → `schultzmedical.co.uk` — own site's contact
  details confirm the company name and a Southport, PR9 7RL address.

All 4 domains added to `data/supplier-seed.json`'s `links` (label "Website"), matching
the format already used for every other supplier record — no company number asserted for
any of them.

**Left unresolved, not guessed** (noted in `OUTSTANDING.md`):
- **Aquilant Limited** — part of the Healthcare21 group; no standalone Aquilant website
  found, so no domain added rather than guessing at a group site.
- **Meril UK Pvt Ltd** — `merillife.com` is the Indian parent's global site with no
  UK-specific naming or address; same "domain-proof strong bar" shape already recorded
  in OUTSTANDING for Microport/Medartis (subsidiary-of-global-parent sites that never
  state the UK entity's own identity). Not added.
- **Lexington Medical UK Ltd** — `lexington-med.com` is the US parent's marketing site
  (Bedford, MA); no distinct UK entity named anywhere on the fetched page. Same shape as
  Meril. Not added.
- **Bariatric Solutions International** — `bariatric-solutions.com` returned no
  fetchable text (JS-rendered site); could not confirm identity from the page content, so
  left unresolved rather than assumed from the matching name alone.
- **Minitouch Ltd** — no dedicated company website found in search; only NHS patient
  leaflets for the "Minitouch" endometrial ablation procedure and Companies House itself.

### Crawl attempts on the 4 newly-domained suppliers

- Venturis Medical Ltd, Winners First Trading Limited and Medecon Healthcare UK: all
  **refused** — no readable product catalogue (WordPress/WooCommerce APIs 404, no usable
  sitemap). Recorded with reason and date; not to be re-attempted inside the refusal TTL.
- **SRA Developments** (bowa-medical.co.uk): refused — WordPress API exposes no product
  post type, no usable sitemap route.
- **Schultz Medical (UK) Limited** (schultzmedical.co.uk): **succeeded** — 248 products
  across 12 divisions (the company's own taxonomy: Dental Instruments, General Surgical
  Instruments, Ophthalmic Instruments, Electrosurgical Instruments, Laparoscopic
  Instruments, Imaging Solutions, Hysteroscopy, Soft Tissue Surgical Scissors, Tubing
  Sets, Sterilisation Containers, Gynaecology Instruments, Electrosurgical Generator).

### Schultz Medical — mapped and published

The **Laparoscopic Instruments** division (18 products: graspers, scissors, dissectors,
trocars, uterine manipulators, bipolar instruments, specimen retrieval bags — checked
against every product on the record) is a single, clean class with no products outside
it, matching `mis:instruments` ("MIS instruments, devices and consumables"). Mapped via
`data/differentiator-map-parts/Schultz-Medical-UK-Limited--framework-coverage-0916.json`
and merged.

**This alone would not have published anything** — the same `sources` gap as the
Electrodes/Ultrasound Gels false start above applied here too: `crawl_supplier_site.py`
gets names/divisions only, and `data/supplier-product-detail.json` had zero records for
this supplier. Running `scripts/crawl_supplier_product_detail.py --supplier "Schultz
Medical (UK) Limited" --domain schultzmedical.co.uk` (twice, to clear the per-run site
time budget) fetched 27 of the 248 products' own pages, including 17 of the 18
Laparoscopic Instruments products (the 18th, "Disposable Laparoscopic Trocar", did not
resolve to a live product page and was left uncaptured — not forced). Those 17 now carry
a `manufacturer` source and publish.

**Ledger effect on this framework: 12 → 13 of 60 suppliers published, 20.0% → 21.7%
coverage, Left 24 → 19** (10 fewer needDomain via 4 domain finds + 4 refusals removing
themselves from actionable Left, minus the 1 new heldOnly entry that didn't publish
until the detail crawl).

## The real lesson: category mapping alone rarely publishes anything for a fresh own-site crawl

`crawl_supplier_site.py` only ever captures product **names and divisions**. Nothing it
writes ever satisfies `build_differentiator.py`'s `sources` requirement (a manufacturer
detail record or an NHSSC match) on its own. A division can be perfectly, obviously
mapped and still publish zero products if `scripts/crawl_supplier_product_detail.py` has
never been run for that supplier — this is not a category-mapping problem and no amount
of vocabulary work fixes it. **Any future framework-coverage run that maps a
freshly-crawled own-site division should run `crawl_supplier_product_detail.py
--supplier "<name>" --domain <domain>` immediately afterward and check the ledger moved,
before reporting the mapping as done.** This is also very likely the same root cause
behind OUTSTANDING ^o457 (82 suppliers crawled before the 05/09 flat-URL fix, never
re-crawled) and ^o458 (Altomed: mapping landed, 0/40 from the detail crawler) — those are
a different failure mode (the detail crawler itself getting 0 results) but the same class
of gap (mapping ≠ publishing).
