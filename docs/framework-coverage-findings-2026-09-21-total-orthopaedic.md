# Framework coverage findings — 21/09/2026 (Total Orthopaedic Solutions 3, follow-up run)

Picked framework: **Total Orthopaedic Solutions 3** (`ortho` speciality),
24.8% (25/101), Left 31 at the start of this run. Already worked once today
(`aec91f4` — 11 supplier domains found, Paragon 28 category mapping fixed,
23.8% → 24.8%); this is a second, independent pass at the same framework's
remaining `notCrawled`/`needDomain` suppliers, picking up where that run left
off rather than repeating it.

## Checked first: Ultrasound Scanners (the ledger's #1 pick)

Before picking Total Orthopaedic Solutions 3, checked the ledger's actual
lowest-coverage pick, Ultrasound Scanners (23.8%, 6 left, all
`publishedElsewhereNeedingCategory`). Two parallel runs today already
confirmed this exhausted for permitted routes
(`docs/framework-coverage-findings-2026-09-21-ultrasound-scanners.md`,
`docs/framework-coverage-findings-2026-09-21-renal-replacement.md`).
Independently re-checked all 6 suppliers' captured/held product ranges
(BioSpectrum Ltd, Celtic SMR Ltd, Hologic UK — captured, no genuine ultrasound
scanner in range; Philips, ProSys International Ltd, Siemens Healthineers —
refused, cannot re-crawl) and reached the same conclusion. No data change
made; moved to the next lowest-coverage framework with genuine work
available, per the brief's own guidance that a low coverage % is often the
most finished, not the most neglected.

## What moved on Total Orthopaedic Solutions 3

**5 suppliers moved from "no domain on record" to "domain proved, genuinely
attempted, cleanly refused"** — the same state-change pattern as today's
Minitouch Ltd finding (a real change even without a coverage percentage
move):

- **Bioventus Cooperatief U.A** — domain `www.bioventus.com` proved by
  name+address self-declaration: the company's own official `/contact-us/`
  page names "Bioventus Coöperatief U.A., Taurusavenue 31, 2132 LS
  Hoofddorp, The Netherlands" as its international HQ — the exact entity
  NHS Supply Chain names on the framework brief. Crawled: refused cleanly
  (no WordPress API, no WooCommerce Store API, sitemap unusable).
- **Biedermann Motech International LTD** — domain `www.biedermann.com`
  proved by name self-declaration: the German parent's own
  `/company/about-us/` page names "Biedermann Motech International
  Limited, Lincoln House, Lincoln Way, Sherburn in Elmet, Leeds LS25 6AX"
  as a UK office. **Note:** this trading address does NOT match the
  Companies House registered office for company 09466785 (4 Wharfe Mews,
  Cliffe Terrace, Wetherby LS22 6LX), so the address-match tier of the
  domain-proof-tier policy does not apply — accepted instead on the weaker
  name-self-declaration tier (Companies House holds exactly one active
  company of this exact name, and the parent's own official site names it
  as its own subsidiary), the same standard used for Minitouch Ltd
  yesterday/today. Crawled: refused cleanly.
- **Greenbone Spa** — domain `greenbone.it` proved by name self-declaration:
  the company's own `/company-overview` page gives its full legal name as
  "GREENBONE ORTHO S.p.A.", registered office Faenza, Italy — matching the
  "Greenbone Spa" named on the framework brief. Italian entity, no
  Companies House cross-check available; accepted on the same on-site
  legal-name-declaration standard used for UK entities without a printed
  registration number. Crawled: refused cleanly (no product post type, no
  Store API, sitemap unusable).
- **Cenobiologics Ltd** — domain `cenobiologics.co.uk` proved: the
  company's own dedicated UK domain, name-matched directly to the company
  name (an HTA-licensed allograft bio-implant processor, Milton Keynes;
  Companies House holds exactly one active company of this name,
  07528157). Crawled: refused — robots.txt disallows automated reading.
- **Arthro Dynamik Ltd** — domain `arthrodynamik.com` proved: the
  company's own dedicated domain, name-matched directly (Wetherby, West
  Yorkshire orthopaedic/arthroscopic custom-product design company; a
  separate Dutch entity, Arthro Dynamik B.V., also exists and is NOT this
  UK-awarded supplier — not merged). Crawled: refused — the site's API
  exposes 0 product records, a landing page rather than a catalogue.

All five domain proofs and their crawl attempts are recorded in
`data/supplier-seed.json`'s `links`/`note` fields, added by hand (never
edited `differentiator-category-map.json` or `differentiator.json` directly
for these). `Left` for this framework: 31 → 26. Coverage unchanged at 24.8%
(25/101) — none of the five had a readable catalogue, so nothing new
publishes.

## Checked, no domain found or resolved (left as-is, not guessed)

- **Orthopediatrics EU Limited** (CH 10642293) — registered office 71
  Queen Victoria Street, London EC4V 4BE (a formation/registered-agent-style
  address, not checked for share count this run). Parent's global site
  (orthopediatrics.com) makes no mention of a UK entity or this address.
  No domain recorded.
- **Permedica UK Limited** (CH 14736672) — registered office 4 Office
  Village Forder Way, Hampton, Peterborough PE7 8GX. Parent's own site
  (permedica.it) makes no mention of a UK office, address or subsidiary at
  all. No domain recorded.
- **Contura Orthopaedics Ltd** — the obvious candidate site (contura.com)
  self-declares its legal name as **"Contura International Limited"**, not
  "Contura Orthopaedics Ltd" — a brand/legal-entity mismatch, not a
  confirmed match. The framework award names "Contura Orthopaedics Ltd"
  specifically; contura.com/contact-us/ lists a UK address (14 Took's
  Court, London EC4A 1LB) under the "CONTURA ORTHOPAEDICS" brand heading
  but attributes it to the different legal name. Per the domain-proof-tier
  guard ("does not license a name-based merge"), not accepted as proof for
  this entity. Left unresolved, flagged below rather than guessed.
- **Advita Ortho UK Limited** — two different Companies House numbers
  turned up in search (05316864 and 16540209) for what may be the same or a
  re-registered entity; `uk.advita.com` doesn't name either one or give a
  UK address on its homepage. Left unresolved rather than picking one.
- **Surgalign UK Ltd (Formerly Pioneer Surgical Technology B.V. or RTI
  Surgical)** — the US parent, Surgalign Holdings Inc, filed for
  bankruptcy and its assets were acquired by Augmedics in 2024; trading
  status of any UK entity is unclear and needs its own check before a
  domain is attempted. Not investigated further this run.

## Held suppliers checked — no genuine ortho product to map

Checked all 4 `heldOnly` suppliers' captured product ranges against the
framework's in-scope categories (`ortho:cement`, `ortho:equip`,
`ortho:implant`, `ortho:trauma`):

- **NSK United Kingdom Limited** (745 products) — entirely dental implant
  surgery equipment (handpieces, MulTipegs/scan-body analogues, VarioSurg
  piezosurgery tips for jaw/alveolar bone work). No genuinely orthopaedic
  product in the range; correctly held, nothing to map.
- **Macromed UK Ltd** — already flagged 19/09 (^o553): 44 flat-sitemap
  products, almost all endoscopy/interventional-radiology (stents,
  ablation systems, vena cava filter), with one ambiguous spine-adjacent
  name (Intraspine). Not re-flagged; still not mappable without a real
  product-page capture.
- **Sovereign Medical** (9 products, `Uncategorised` division) — NEW,
  written to OUTSTANDING.md: unlike Macromed, this range looks
  *genuinely* and *entirely* orthopaedic — cryotherapy joint braces
  (ANKLEFREEZ, KNEEFREEZ, SHOULDERFREEZ, HANDFREEZ), abdominal/hip support
  belts (ABDOBACK, ABDOHIP), a rehab glove (Madglove) and a compression
  device (PRESSORELAX). The problem isn't ambiguity, it's that none of
  this framework's four in-scope categories (`ortho:cement`, `ortho:equip`,
  `ortho:implant`, `ortho:trauma`) are a good fit for cryotherapy/bracing
  products — this may be a genuine `vocabulary-gap` case (policy: "add the
  category type when a real range genuinely fits nothing") or these
  products may belong under a different existing Hub speciality
  (patient handling / rehab) rather than `ortho` at all. Left for a
  decision rather than guessed — see OUTSTANDING.md.
- **Symbios** (10 products) — already correctly mostly mapped (Hanche/hip,
  Genou/knee implant lines under French division names). One stray "test
  product" row and one "Technologies" division (planning software, not a
  physical product) remain held — correctly so, not products in the
  comparable sense.

## Process notes

- Confirmed again this run: every shell command resets to the harness's
  tracked working directory between tool calls (documented in today's
  earlier findings doc). Prefixed every command with the clone's absolute
  path throughout.
- `scripts/crawl_supplier_site.py` can take over 2 minutes per supplier on a
  slow/unresponsive site (Arthro Dynamik, Cenobiologics both did); ran two
  at a time in the background rather than serially timing out the
  foreground shell.
