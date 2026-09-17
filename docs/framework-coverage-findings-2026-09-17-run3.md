# Framework coverage findings — 17/09/2026, third run

Run of the `differentiator-framework-coverage` scheduled task.

## Picker check: Insulin Pumps and Digital Diagnostic Solutions confirmed exhausted again

Regenerated the ledger fresh. The two lowest-coverage STARTED frameworks
(16.7% Insulin Pumps, Continuous Glucose Monitoring...; 18.5% Digital
Diagnostic Solutions) both show `Left` counts made up entirely of
`publishedElsewhereNeedingCategory` with zero crawlable/need-domain/held
suppliers — same conclusion as every 17/09 run before this one. For Insulin
Pumps specifically (3 left, all `publishedElsewhere`), dug into all three:

- **Abbott Laboratories Limited** — NHS Supply Chain's own launch brief names
  the framework awardee "Abbott Laboratories Ltd", and this exact framework
  also appears independently in the seed's **separate** "Abbott Diabetes
  Care" record (which actually holds the FreeStyle Libre CGM range). Both
  Abbott entities' own domains (`abbott.co.uk`) are already recorded refused
  (no crawlable catalogue) on 20/08 and 31/08. Whether "Abbott Diabetes
  Care"'s products should credit "Abbott Laboratories Limited" for this
  framework's coverage is a genuine company-identity/routing question — see
  OUTSTANDING.
- **Medtronic** — refused on medtronic.com (08/09) and the NHSSC catalogue
  cache carries no diabetes/CGM/pump items for Medtronic under any term
  (checked directly). Not a decision to make — there is currently no
  permitted route to this supplier's diabetes range at all, by crawl or by
  NHSSC catalogue. Structurally blocked, not logged to OUTSTANDING (nothing
  for Lou to rule on).
- **Urathon Europe Ltd** — confirmed via their own site
  (`urathon.com/yuwellanytime/`) that they distribute a real, named product,
  the Yuwell Anytime CT-3 CGM system, launched in the UK 01/05/2025. It sits
  on a standalone marketing microsite page, not under the site's normal
  `/product/` catalogue structure that `crawl_supplier_site.py` reads (dry-run
  confirmed: still 104 products, page not picked up even with
  `--product-path yuwellanytime`). There is no supported way in this pipeline
  to durably add one manually-verified product outside the crawl: `doc["suppliers"][name] = shaped`
  fully replaces the supplier's record on every future crawl of Urathon, so a
  hand-inserted product would be silently wiped the next time anyone crawls
  this supplier. Left uncaptured rather than hacked in — see OUTSTANDING.

Neither of these three suppliers moved. Not deferring the framework yet
(that mechanism is for a framework picked and re-confirmed with zero
movement across multiple runs — this is the first run to actually dig into
these three suppliers by name rather than just re-confirming the ledger's
own `publishedElsewhere` bucket, and two of the three now have a stated path
forward: an OUTSTANDING ruling for Abbott, a tooling gap for Urathon).

## Moved instead: Operating Theatres Equipment and Related Accessories and Services

20.9% → **23.3%** (9/43 → **10/43** published), `Left` 21 → 17.

### Domains researched and proven (6 of 9 `needDomain` suppliers)

Web-searched each, confirmed identity via a primary source before writing to
`data/supplier-seed.json`:

- **Brandon Medical Company Ltd** → `brandon-medical.com` — site's own title
  self-identifies; domain was already on record as an alias, just never
  linked.
- **Newmaw Medical Ltd** → `www.newmawmedical.com` — site title states
  "Welcome To Newmaw Medical Ltd : Newmaw Medical Ltd", exact match.
- **NJ Devices Ltd t/a Ocean Med** → `www.ocean-med.co.uk` — NHS Supply
  Chain's own brief already asserts this exact trading-name pairing; an NHS
  trust's own published expenditure report independently names "NJ Devices
  Ltd" trading as "Ocean Med"; the site brands itself "Ocean-Med" (social
  handles @oceanmeduk) with a Gynaecology/Urology/ENT/Colorectal/
  Maxillofacial/Plastics range matching that description.
- **Promed Limited** → `promedltd.com` — **registration-tier proof**: its own
  contact page states "Promed Limited ... Registered number: 3170800",
  matching Companies House 03170800 exactly.
- **Ryna Medical Uk Limited** → `rynamedical.co.uk` — own homepage states
  "RYNA MEDICAL UK LIMITED is the sole UK distributor..." and describes an
  Operating Theatre/ITU/CCU range (LED Operating Lights, Operating Tables,
  Patient Trolleys), matching this framework's own scope exactly.
- **Soluvos Medical Ltd** → `www.soluvos.com` — site title states "Soluvos
  Medical ENT Laryngology Lasers...", exact match.

**A live false positive caught and fixed.** A same-session run of
`scripts/seed_supplier_domains.py --accept-name` (its own weak, explicitly
untrusted name-guess tier) "proved" Promed Limited against `promed.com` — a
domain-brokerage/for-sale page whose title merely contains the string
"PROMED". `state/domain-seeding-report.json`'s Promed Limited entry has been
corrected in place to the real registration-tier proof above, so a future
`--write` doesn't seed the wrong domain. The same run's automated "parked or
for-sale domain" check also wrongly flagged `ocean-med.co.uk` and
`rynamedical.co.uk` — both read as genuine, functioning sites by direct
browser fetch. Worth a wider look at how many of that script's other
"proven" name-tier entries are similarly wrong — see OUTSTANDING.

**3 left unconfirmed, no domain guessed:**
- **Ferno (UK) Limited** — genuine UK subsidiary of the global Ferno
  patient-handling brand, but its web presence is a section of the global
  `ferno.com` site that never self-identifies as the specific UK legal
  entity; `seed_supplier_domains.py` independently refused it on the same
  test.
- **Ingles Ltd** — NHS Supply Chain's own brief names the supplier exactly
  "Ingles Ltd" (confirmed by reading the live brief page). Every search only
  surfaces "Ingles Medical Limited" (Companies House 08650170) as a
  candidate, never "Ingles Ltd" as a distinct registered name. Per rule 10,
  not treated as the same company without confirmation — logged to
  OUTSTANDING rather than guessed.
- **Lynton Lasers** — `lynton.co.uk` (the correct, well-known company) is
  behind a bot-challenge page that returned no content to read; genuinely
  inaccessible right now, not a decision.

### Crawled, and what came of it

- **Brandon Medical Company Ltd** — 38 products, 4 divisions (sitemap route),
  then `crawl_supplier_product_detail.py` captured all 38 individual product
  pages for sourcing.
- **Promed Limited** — 23 products, 4 divisions (own taxonomy), then
  `crawl_supplier_product_detail.py` captured 20 of 23 (site time budget
  spent; 3 left for a future run to pick up automatically).
- **Newmaw Medical Ltd, NJ Devices Ltd t/a Ocean Med, Ryna Medical Uk
  Limited, Soluvos Medical Ltd** — all four are genuine, live sites but none
  exposes a crawlable product API/sitemap (checked and refused with reasons
  recorded, dated 17/09/2026).

### Category mapping

- **Brandon Medical Company Ltd** → `theatres:capital` for 3 of 4 divisions:
  Medical Lighting (12, surgical/examination lights — "lights" is named
  explicitly in this type's own definition), Architectural (7, operating
  tables and supply/service pendants — "tables" also named explicitly; the
  Ultra Clean Ventilation Canopy is fixed theatre-integration infrastructure),
  Medical Audio Video (10, Symposia integrated-theatre AV/PACS/recording
  systems — "OR integration", again named explicitly). **Now published,
  moved this framework's coverage.**
  Left held: Power Control (9 — UPS/transformers/busbars/earthing/control
  panels; genuine theatre electrical infrastructure, but not tables/lights/OR
  integration and not a consumable, so not forced into `theatres:capital`; no
  other gated type fits electrical distribution plant).
- **Promed Limited** → `endourology:laser` for Medical Lasers (7:
  Leonardo/Sphinx/Revolix Holmium/Thulium surgical lasers, used for
  endourology lithotripsy) and Laser Fibres (3, consumables for the same
  systems). **This is the more precise, correct home for these products —
  not `theatres:capital`, which is tables/lights/OR-integration, not energy
  platforms — so it publishes the products correctly but does NOT move this
  framework's own coverage number**, since `endourology:laser` sits outside
  this framework's `catsInScope`. Left held: Single Use Videoscope (5,
  Scivita ureteroscope/cystoscope + trolley/processor/display accessories —
  no gated "scope" type exists under `endourology`) and Accessories (9, a
  genuine mixed bag of laser hand pieces, stent removers, tumescent-
  anaesthesia kit and PPE).

### Left for a future run

- **Howard Wright Europe** (10 products, all in a crawler fallback
  "Uncategorised" bucket, `notTaxonomy: true` — beds, a stretcher trolley, a
  bathing trolley, mattresses and one examination couch). A genuine mixed
  bag needing per-product overrides, not a blanket division mapping, and the
  real category home for most of these (patient-handling beds/mattresses) is
  outside this framework's scope anyway, same shape as Promed above.
- Ferno (UK) Limited, Ingles Ltd, Lynton Lasers — domains not found/
  confirmable this run (see above).
- The 11 `publishedElsewhereNeedingCategory` suppliers already on the
  framework (Acime UK Ltd, Arjo, Boston Scientific, Coloplast, Cook Medical,
  Draeger Medical UK, Felgains, Baxter/Hillrom, Ideal Medical Solutions,
  Olympus (KeyMed), LINET UK) — not looked at this run, left for the next
  pass on this framework.
