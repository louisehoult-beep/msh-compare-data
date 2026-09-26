# Framework coverage batch — findings, 26/09/2026

Run of the `differentiator-framework-coverage` scheduled task.

## Picked

Regenerated the ledger. The strict lowest-coverage-STARTED pick order was CT Scanners
(25.0%), Polymer Aprons (25.0%), Operating Theatres (25.6%), Surgical Instruments (26.0%),
Examination Gloves (26.3%), Laboratory Diagnostics (27.0%), Ultrasound Scanners (28.6%) and
Clinical and Sharps Waste Management (28.6%) — all eight already confirmed exhausted (checked
22–25/09) in `docs/framework-coverage-exhausted.json`, so skipped without re-investigation.
Next in order was **Minimally Invasive Surgery, Related Equipment and Accessories** (30.0%,
10 left), investigated fresh this run.

## Minimally Invasive Surgery — investigated, confirmed exhausted

All 10 remaining actionable items checked (9 `publishedElsewhere`, 1 `heldOnly`). B. Braun
Medical, Fannin (UK) Limited, Medline Industries and Stryker already carry recorded
crawl-refusals for this framework — not re-crawled. The other 5 `publishedElsewhere`
suppliers were checked product-by-product against their real, crawled ranges: Advanced
Medical Solutions (wound/gastro/skin-prep), Kebomed UK Ltd (nutrition devices), Reflex
Medical Limited (761 held products checked — first-aid/AED/patient-monitoring/PPE, nothing
surgical), Bolton Surgical Limited (418 held products checked — traditional open-surgery
hand instruments organised by department: ENT, orthopaedic/neuro, plastic, GU/gynae,
colorectal, dental, cardiothoracic; none laparoscopic/MIS), W.L. Gore & Associates (31 held
products checked — vascular grafts/stents, hernia mesh and staple-line reinforcement
(Seamguard); Seamguard is used alongside surgical staplers but its fit to any one in-scope
MIS category isn't unambiguous from the name alone — correctly held per the
mixed-division-mapping policy guard, not forced). Healthcare 25 Ltd's 1 held item is an
already-documented nav-labels-are-not-products case. No permitted route on any of the 10.
Logged to `docs/framework-coverage-exhausted.json`.

## Next pick: Orthotics, Podiatry and Immobilisation — worked, real movement

Next lowest-coverage non-exhausted STARTED framework: 30.2% (19/63), 25 left (8
mapped-elsewhere, 2 held, 15 need-domain — none previously attempted in
`state/domain-seeding-report.json`).

Web-researched (WebSearch/WebFetch, not a scraped search engine) primary sources for 8 of
the 15 need-domain suppliers, holding the domain-proof-tier bar (registration number, or a
registered-office ADDRESS match per the identity-vocabulary-policy ruling of 20/09/2026):

- **Birmingham Orthotic Services** → `birminghamorthotics.co.uk`, PROVEN by address match:
  site's own contact page ("Link One Trading Estate, Great Bridge, Tipton, DY4 7BU") matches
  BIRMINGHAM ORTHOTIC SERVICES LTD's (12086348, active) registered office ("A10 Link One
  Trading Estate, George Henry Road, Tipton, DY4 7BU"). A confusingly similar company,
  BIRMINGHAM ORTHOTICS LTD (12045881), was checked and ruled out — dissolved 2019-10-15,
  registered office in Stafford, unrelated. This closes identity/domain work already
  recorded in the seed record's own note (verified 25/08/2026) but never written to `links`.
  Crawled: refused (WordPress API exposes no product post type, no usable sitemap/WooCommerce
  route) — a real business (bespoke insoles/AFOs/footwear adaptations) with no browsable
  online catalogue, correctly recorded as a refusal, not a thin capture.
- **C&S Footwear Adaptions Ltd** → `www.candsfootwear.co.uk`, PROVEN by address match: site's
  own About Us page ("Unit 24, Station Road Industrial Estate, Old Whittington, Chesterfield,
  S41 9QX") against C & S FOOTWEAR ADAPTIONS LIMITED's (04438620, active) registered office
  ("Unit 24 Station Lane Industrial Estate..."). Confirmed via independent property listings
  that "Station Lane" is the estate's correct name — the site's own "Station Road" is a
  naming slip, not a different location. Crawled: refused (no product API/catalogue) —
  consistent with the company's stated business (footwear repairs/adaptations and
  made-to-measure insoles, not an online product range).
- **Piedro Ltd** → `piedro-uk.co.uk`, PROVEN by an exact address match (Unit 4 Maizefield,
  Hinckley, Leicestershire, LE10 1YF, both site and Companies House 04354646). **Crawled: 252
  products across 5 divisions, all genuine orthopaedic/therapeutic footwear** (Children,
  Adult Orthopaedic Footwear, Welsh NHS Tender Footwear, Adult Piedro PRO, plus a 2-item Soft
  Goods & Accessories division holding the AFO device itself and AFO/KAFO/SMO interface
  socks). **No existing orthotics vocabulary type covers finished orthopaedic footwear**
  (afo/brace/hosiery/insole/materials/paed/podinstr/prosth/spine/upper are all a device,
  material or instrument) — a genuine gap under the standing vocabulary-gap policy, the
  footwear half of the same "Immobilisation" gap the 23/09 run flagged for Thesis Technology
  Products Ltd's cast-protection range. Added `orthotics:footwear` (add-only, no escalation
  needed per policy) via `scripts/_add_vocab_type_orthotics_footwear_0926.py`, unioned the 5
  new (supplier, division) pairs via `scripts/union_differentiator_pairs.py --apply`, and
  mapped them via `data/differentiator-map-parts/Piedro-Ltd.json`: 4 footwear divisions →
  `orthotics:footwear`, the Soft Goods & Accessories division → `orthotics:afo` (the 2
  products there are the orthosis and its interface sock, not footwear).

  **A slice, not the range**: `build_differentiator.py`'s own-source gate holds a product with
  no per-product detail record even once its division is mapped, so
  `scripts/crawl_supplier_product_detail.py` was run for Piedro across several budget
  windows and captured **142 of the 252 products** this session (the rest — mostly further
  "Welsh NHS Tender Footwear" and "Adult Piedro PRO" model variants — are captured at
  division level in `supplier-products.json` but have no per-product detail record yet, so
  they stay held until a future run's crawl reaches them; the resume cursor is in
  `state/product-detail-cursor.json` and will pick up where this run left off).
- **Canonbury Products Limited**: registered office is a C/O accountant's address (Mercer &
  Hole, Milton Keynes) — does not, and structurally cannot, match the company's own trading
  address (Brackley, confirmed via the company's own compliance PDF). No proof route;
  left unresolved, not guessed.
- **Firefly Orthoses NI Limited**: registered office (Glendinning House, Belfast — a
  formation-agent-style address) does not match the site's own stated NI trading address
  (Garrison, Enniskillen) — a trading address is explicitly excluded by the domain-proof-tier
  policy guard. No proof route; left unresolved.
- **Podopro UK Ltd**: the only findable "Podopro" website (via dltpodiatry.co.uk) belongs to
  a *different* company (FAS Healthcare Ltd) that manufactures "Podopro" as an internal
  brand/division, not the separately-incorporated Podopro UK Ltd (07753479) actually named
  on the framework award. This is exactly the parent-subsidiary-award-credit policy shape —
  clause (c) (recording a related entity as a search alias) is suspended pending Lou's
  ruling, so no domain/alias was added; the award stays correctly credited to "Podopro UK
  Ltd" by name alone, per clause (a). No fresh escalation needed, the standing policy already
  answers this.
- **Prestige Health Footwear Ltd**: shares its registered office (5-7 Church Hill Road, East
  Barnet) with the already-seeded "Prestige Healthcare (London) Ltd" (04266554) but is a
  *different* company number (11036077) — same parent-subsidiary-award-credit shape, same
  suspended clause (c). The only footwear-named domain found (prestigefootwear.co.uk)
  resolves to an unrelated brand ("YDA UK"), not this company. No domain added.
- **Beagle Orthopaedic Ltd**: found via search (CH 06593518, registered office Bourne End,
  Buckinghamshire; a separate case-study source describes manufacturing in Blackburn — likely
  factory vs. registered office, not a conflict). The candidate site (beagleorthopaedic.com)
  returned no readable content via WebFetch (JS-rendered) — could not confirm a match this
  run. Left for a future run with a different fetch route (e.g. `crawl_supplier_site.py`
  directly, which reads the raw HTML/sitemap rather than a rendered DOM).

7 of the 15 need-domain suppliers were not attempted this run (Benefoot UK Ltd, Chaneco,
Dacey LTD, Dynamic Metrics Ltd, Ken Hall Ltd, Medezine Ltd, Medfac UK Ltd) — left for a
future run, per the brief's "not every item in one run" guidance.

The 8 `publishedElsewhere` suppliers and 2 `heldOnly` suppliers (Footlabs Ltd, Thesis
Technology Products Ltd) were re-checked against this run's fresh data and remain correctly
answered from the 23/09 findings (Peacocks Medical Group is a recorded refusal; Win Health
Medical Ltd's real range is `rehab:*`/`endourology:urodyn`/`womens:pelv`, not orthotics; the
rest — Ambu UK, Huntleigh, Joint Operations, L&R Medical/Activa, Praxis Medical, Purple
Surgical — are genuinely other specialities). No route on any of the 8+2.

## Coverage movement

Minimally Invasive Surgery: 18/60 (30.0%) → unchanged (exhausted, logged, not published
further this run).

Orthotics, Podiatry and Immobilisation: 19/63 (30.2%) → **20/63 (31.7%)**. Left: 22 (was 25)
— 0 unresolved, 8 mapped-elsewhere, 2 held, 12 need-domain (was 15). 142 Piedro Ltd products
now publish (140 `orthotics:footwear`, 2 `orthotics:afo`) — the first supplier under the new
`orthotics:footwear` type.

## Gate

`python3 scripts/stamp_notice.py` then `python3 verify.py` — PASSED, 22 warnings, none
touching this run's files (pre-existing supply-notice staleness, 404 source links and
company-register status notes, unrelated to Orthotics/MIS/Piedro).
