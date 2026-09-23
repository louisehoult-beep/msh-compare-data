# Framework coverage — 23/09/2026, second run of the day

## Picked

Regenerated the ledger. Ultrasound Scanners, CT Scanners, Operating Theatres, Polymer
Aprons, Surgical Instruments and Examination Gloves were all already confirmed exhausted
today or on 22/09 (`docs/framework-coverage-exhausted.json`), so the next lowest-coverage
STARTED framework with real `Left` was **Laboratory Diagnostics, Point of Care Testing and
Pathology Managed Services** (27.0%, 67 left, 58 need-domain), tied on coverage % with
**Orthotics, Podiatry and Immobilisation** (27.0%, 31 left).

## Laboratory Diagnostics — no safe movement this run

Ran `seed_supplier_domains.py --candidates-file --search --retry-unproven` against the
58 need-domain suppliers plus manually researched ~15 well-known global diagnostics
companies (Bruker UK, DiaSorin, Nova Biomedical, VWR/Avantor, Promega UK, Twist Bioscience,
Revvity, Sebia UK, Diagnostica Stago UK, Genetic Signatures, pfm medical UK, Helena
Biosciences, ELITech, DWK Life Sciences, Immucor) via WebSearch/WebFetch.

None crossed the evidence bar:
- Most global corporate sites (diasorin.com, promega.com, twistbioscience.com, etc.) never
  print their UK subsidiary's Companies House number anywhere reachable — registration-tier
  proof genuinely unavailable from the site content, not a script limitation.
- **DiaSorin**: site's own UK office (Central Road, Dartford, Kent DA1 5LR) is a production
  facility, not DIASORIN LIMITED's (01993990) registered office (Ashbrook House, Blewbury,
  Oxfordshire) — a trading address, explicitly excluded by the domain-proof-tier policy's
  guard. Refused correctly.
- **pfm medical UK**: site prints its own address (Suite 3, Armcon Business Park, Poynton)
  matching Companies House exactly, but Companies House advanced search on that address
  returns 400+ (mostly dissolved, Norwegian-sounding) companies — a company-formation-mill
  signature, which the policy guard explicitly treats as no proof at all. Refused correctly.
- Immucor (IBG Immucor) has become part of Werfen brand-wise; no standalone UK domain found
  this pass — left alone rather than guessed.

No writes made to Laboratory Diagnostics this run. Left for a future run with a different
research angle (e.g. UK annual-accounts filings, which do carry the registration number, as
a candidates-file source).

## Orthotics, Podiatry and Immobilisation — worked, real movement

**3 unresolved names** (missing from `supplier-seed.json` entirely):
- **Prestige Healthcare (London) Ltd** — confirmed via Companies House (04266554) + own-site
  address match (5-7 Church Hill Road, East Barnet — a small dedicated clinic address, not a
  formation mill). Added to seed. Crawled (shop.prestigehealthcare.co.uk — the main site
  www.prestigehealthcare.co.uk carries the clinic identity but no product catalogue).
  205 products / 45 divisions captured. Mapped 12 of the cleanest divisions (Inserts, Ankle &
  Foot, Knee/Knee Brace/Osteo-Arthritis Brace/Active-Rehab Knee Braces, Wrist & Hand/Shoulder
  & Elbow/Upper Arm, Neck & Back/Back, Ligament Braces) to their exact vocabulary matches via
  `differentiator-map-parts/Prestige Healthcare (London) Ltd.json`. 24 products now publish.
  Left unmapped (footwear divisions — no category in the orthotics vocabulary covers
  orthopaedic footwear; brand-name divisions like Darco/TDO/Thrive/MAC 3/Cairn/Juzo/PodoWell;
  ambiguous podiatry-condition divisions like Splayfoot/Hammer Toes/Bunion Splint/Heel
  Pain/Arch Bridges/Calluses and Corns that could plausibly be insole or podinstr but weren't
  read closely enough this run to be confident) — genuinely held, not forced.
- **Thesis Technology Products Ltd** — confirmed via Companies House (02894920) + own-site
  address match (Brooks Green Farm, Bosham, West Sussex — a farm address). Added to seed.
  Crawled (limboproducts.co.uk). 62 products / 4 divisions, ALL of it cast-protection
  (LimbO Waterproof Protectors, Cast Accessories), PICC-line accessories, and mobility aids
  (sock aids, walking sticks) — none of it orthoses, bracing, insoles, hosiery, prosthetics
  or podiatry instruments. This is a genuine vocabulary gap: the framework's own name
  includes "Immobilisation" but the orthotics vocabulary has no matching sub-type. The
  standing vocabulary-gap policy (`data/identity-vocabulary-policy.json`) permits adding one
  without escalating, but touching the gated vocabulary (`compare-suppliers.json` +
  `differentiator-category-map.json`) for 62 products deserved a dedicated pass rather than
  a rushed addition at the end of an already-long run — left held, noted here for whoever
  picks this framework up next.
- **Reed Medical Ltd** — genuine identity conflict, left unresolved and written to
  OUTSTANDING.md (^o607): the awarded name's only active Companies House match
  (REED MEDICAL LIMITED, 02593748) is registered in Leeds, but the company's own live site
  states its registered office in Blackburn — an address that in fact belongs to the
  DISSOLVED REED MEDICAL (2011) LIMITED (07871245, dissolved 12/08/2025). Consistent with an
  unannounced recent restructure (press coverage: "recently joined the Eqwal Group") the
  website hasn't caught up with. Rule 10 — not merged on name similarity.

Ran `crawl_supplier_site.py --supplier "Darco UK Ltd..." --domain darcouk.com` for the one
`crawlable` item on the framework — robots.txt-refused, recorded honestly.

**Footlabs Ltd** (the framework's one `heldNeedingCategory` item before this run) checked
again: its 8 "products" are all site-navigation/service labels (Simple Inlays, Shoe Repairs,
Functional Foot Orthoses, Shoe Modification, etc.) from a flat sitemap capture with no
division structure — the nav-labels-are-not-products policy shape exactly. Correctly held,
no forced mapping.

## Result

Orthotics coverage: 17/63 (27.0%) → **18/63 (28.6%)**. Left: 30 (was 31) — 1 unresolved
(Reed Medical, on OUTSTANDING), 8 mapped-elsewhere, 2 held (Footlabs — correctly held;
Thesis Technology — vocabulary gap, correctly held), 18 need-domain (untouched this run).

Laboratory Diagnostics coverage: unchanged, 33/122 (27.0%). No safe route found this run.
