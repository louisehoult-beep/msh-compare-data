# Framework coverage batch — 20/09/2026 findings

Picked framework: **Minimally Invasive Surgery, Related Equipment and Accessories** (23.3%,
17 left at pick time). The ledger's two lower-coverage picks — Infusion Pumps and
Administration Sets (22.2%) and Infant Feeding and Accessories (22.2%) — were both re-checked
against the fresh ledger and found unchanged since 19/09's run 3 and run 4: every remaining
item in both is a recorded refusal, a company-identity decision already queued for Lou, or a
mapping dead end already documented. Re-picking either would have re-read the same answered
ground, so this run moved to the next real candidate with unworked material, following the
same pattern run 3/run 4 used on 19/09.

## Result: coverage unchanged at 23.3% (14/60); actionable backlog 17 → 15

No new products published this run — every lead this run resolved to an identity answer, a
recorded refusal, or a genuine no-lead/crawler-defect finding, not a new categorised product.

### `needDomain` (3) — 2 resolved to recorded refusals, 1 genuinely not found

- **Aquilant Limited** — a new candidate domain, `aquilantservices.com`, found via web search
  (the earlier attempt on 02/09 tried `aquilant.co.uk` and got no response). The site's own
  "About" text names the address "Aquilant House, Unit B1-B2 Bond Close, Kingsland Business
  Park, Basingstoke, RG24 8PZ", which matches Companies House's registered office for AQUILANT
  LIMITED (02090807) exactly — a genuine address-match confirmation, not a guess. Added to
  `data/supplier-seed.json`. `crawl_supplier_site.py` still could not reach it: neither
  `aquilantservices.com` nor `www.aquilantservices.com` answered (confirmed independently via a
  direct TLS handshake test — both fail with a handshake failure, not a timeout). Recorded as a
  refusal. Genuinely unreachable, not unfound; closes most of ^o497.
- **Bariatric Solutions International — identity resolved, closes ^o545.** ^o545 (18/09) had
  left this open between two live candidates: "Bariatric Solutions UK Limited" (14890948) or
  "Bariatric Solutions International GmbH" (Switzerland), because neither was an exact name
  match to the NHSSC brief's "Bariatric Solutions International". The **official Find a Tender
  award notice for this exact framework** (find-tender.service.gov.uk/Notice/061906-2026,
  reference 2026/S 000-061906 — the same reference NHS Supply Chain cites) names the contractor
  "Bariatric Solutions International GmbH", Stein am Rhein, Switzerland (NUTS CH052), in the
  same list as every other awarded supplier on this framework. This is the primary source
  itself, not a name-search guess between candidates, so it settles ^o545: the Swiss GmbH is
  the awarded entity, not a UK company. No UK company number exists to record. Removed the
  wrong `companyNumberCandidate` (BARIATRIC SOLUTIONS UK LIMITED) from the seed record and
  replaced it with the confirmed identity. Domain `bariatric-solutions.com` added (matches the
  Stein am Rhein address independently via a D&B profile, and sells banded gastric
  bypass/sleeve/gastric-banding devices, consistent with an MIS award). The site returns an
  anti-bot challenge (HTTP 202, redirects to `/.well-known/sgcaptcha/`) on a direct fetch, and
  `crawl_supplier_site.py` independently found its robots.txt disallows automated reading —
  recorded as a refusal.
- **Minitouch Ltd — no lead, genuinely not found.** Companies House confirms an active company
  (07933081, Bishop Auckland, "manufacture of medical and dental instruments and supplies" —
  a plausible SIC match), but no website could be found by search under that name or any
  obvious domain variant, and none were guessed/probed as a substitute. Matches the existing
  ^o546 finding from 18/09; left un-domained.

### `heldNeedingCategory` (3) — one real partial lead, two checked with no lead

- **Sela Medical UK Ltd, Surgical Division — a genuine but only partial lead, left held.**
  Already flagged in ^o461 (13/09) as needing a category decision. Checked all 5 products
  against primary/secondary sources this run: **Endograb**, **Endolift** and **Applier** are
  confirmed internal laparoscopic organ-retraction clips and their deployment applicator
  (manufactured by Virtual Ports, deployed through a 5mm laparoscopic port) — a clean
  `mis:clips` fit. **Glutack** is a laparoscopic mesh-fixation glue applicator (used with
  Glubran2 cyanoacrylate glue in laparoscopic/open hernia mesh fixation) — fits `mis:instruments`.
  **Dipromed** is a manufacturer of hernia mesh implants and urogynaecological slings — no fit
  in the `mis` vocabulary at all (an implant range, not an MIS instrument/device). The category
  map only supports a `hub` value per (supplier, division), not per product, so mapping this
  division to `["mis:clips", "mis:instruments"]` would also publish Dipromed's mesh/sling
  products under those categories — misrepresenting an implant range as laparoscopic
  instruments. Left unmapped rather than forced; written to OUTSTANDING (^o561) for a ruling on
  whether the 3-of-5 lead is worth mapping with Dipromed excluded by some other route, or
  whether the whole division stays held. This is new, useful evidence for ^o461, not a
  duplicate — ^o461 previously had no product-level detail at all.
- **Bolton Surgical Limited — checked, no lead for this speciality.** ^o550 (19/09) already
  established that its flat "Uncategorised" division is not actually structureless — 1,841 of
  2,311 products (79.7%) carry a real per-product `category` string from the site's own
  filing (Ear Nose & Throat, Orthopaedic/Neuro, Curettes, Middle Ear Instruments, etc.) — but
  none of those per-product categories is a minimally-invasive/laparoscopic one. A keyword
  sweep for laparoscopic/trocar/endoscopic/stapling terms across all 2,311 products found only
  14 hits, and on inspection these are monopolar-generator connector cables that plug into a
  laparoscope/endoscope, plus two "Tilley" trocars — which are a traditional ENT
  (nasal/sinus) instrument despite the name, not a laparoscopic access trocar. Bolton Surgical
  is a general reusable-instrument manufacturer spanning many surgical specialities; no genuine
  MIS-specific product line exists in its catalogue. No mapping made; no OUTSTANDING item
  needed (^o550 already owns this supplier's structure).
- **Healthcare 25 Ltd** — already fully covered by the existing ^o534 (18/09) crawler-capture
  finding (its "products" are the site's own nav/category labels, not real products). Not
  re-touched this run.

### `publishedElsewhereNeedingCategory` (11 checked) — two crawler-capture defects found, rest no lead

- **Advanced Medical Solutions (AMS) and W.L. Gore & Associates — crawl data unusable, not a
  mapping gap.** Checked every unmapped division for both. AMS's "Uncategorised", "Other
  Technologies", "Sutures & Supplies" and "Surgical" divisions list entries such as "Laparoscopic
  Instruments", "Clips", "Vascular Temporary Occlusion (VTO)" and "Sutures, Clips & VTO" —
  these read exactly like genuine MIS product-line evidence, but cross-checking against
  `data/supplier-products.json`'s raw crawl record shows they are the site's own WooCommerce
  category-taxonomy labels captured as if they were individual products (each one is a
  category page title, not a purchasable item). W.L. Gore's ~30 unmapped divisions show the
  same pattern even more clearly: every "product" example is a page-section heading
  ("Specifications", "MRI Safety", "Physician Resources", "Clinical Data", "Value Summary"),
  never an actual device name. Mapping either supplier's divisions here would publish these
  fake "products" as if they were real MIS instruments. Same shape as ^o534 (Healthcare 25) and
  ^o551 (Electro Spyres) — a crawler product-boundary problem, not a mapping decision. Written
  to OUTSTANDING (new item, crawler fix needed).
- **Hologic UK** — its one unmapped division is specimen radiography systems (Faxitron) and
  the Panther molecular diagnostics platform — pathology/diagnostics equipment, not MIS. No
  lead.
- **Reflex Medical Limited** — all unmapped divisions (patient monitoring, PPE, medical
  bags/kits, rescue/mass-casualty equipment, wound closure sutures/Gigli saw) are ambulance and
  emergency-care ranges, not laparoscopic. No lead.
- **B. Braun Medical, Fannin (UK) Limited, Kebomed UK Ltd, Medline Industries, Starkstrom
  Limited, Stryker** — no unmapped (`hub: null`) divisions exist for any of these six; every
  division they carry is already mapped to a category elsewhere. Genuinely nothing to check —
  they sit in `publishedElsewhere` correctly, with no route into `mis` for this framework.

## OUTSTANDING.md

- ^o545 (Bariatric Solutions International identity) — **closed**, resolved above.
- ^o497 (MIS needDomain backlog) — updated to reflect the current, smaller set (Aquilant,
  Minitouch only).
- ^o461 (Sela Medical Surgical Division) — updated with the new per-product evidence; still
  open, now genuinely actionable as a ruling rather than an open-ended "needs a decision".
- New item added: AMS/W.L. Gore crawler-capture defect (same shape as ^o534/^o551).

## Landed

`./land.sh` with `data/supplier-seed.json`, `data/supplier-products.json`,
`data/differentiator.json`, `data/coverage-ledger.json`, `docs/COVERAGE-LEDGER.md`,
`docs/framework-coverage-findings-2026-09-20.md`. `verify.py` must pass before push.
