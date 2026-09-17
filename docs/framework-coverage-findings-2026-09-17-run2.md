# Framework coverage findings — 17/09/2026, second run

Run of the `differentiator-framework-coverage` scheduled task. The picker's
lowest-coverage STARTED-with-work-left frameworks (16.7% Insulin Pumps, 18.5%
Digital Diagnostic Solutions) were re-checked against this run's fresh ledger
and confirmed exhausted again — same conclusion as the earlier 17/09 run
(`docs/framework-coverage-findings-2026-09-17.md`) and the 14/09 run
(`docs/framework-coverage-findings-2026-09-14.md`). Moved to the next
lowest-coverage framework with real, forceable work: **Complete Ophthalmology
Solutions 3** (20.8%, 11/53 published, 27 `Left`, the largest `needDomain`
backlog of any framework at 17).

## Domains researched and proven (11 of 17 `needDomain` suppliers)

Web-searched each supplier, then confirmed identity via a primary source
(the company's own site) before writing a domain to `data/supplier-seed.json`:

- **Andersen Caledonia Ltd** → `andersencaledonia.com` — name-exact match, UK/Ireland
  sterilisation company, own ophthalmic product (SP.eye intravitreal injection system).
- **Associated Optical Products** → `associatedoptical.co.uk` — trades under this exact
  name (own About page).
- **Daybreak Medical Ltd** → `daybreakmedical.co.uk` — name-exact match, exclusive UK/
  Ireland distributor for Quantel Medical and Geuder ophthalmic lasers/devices.
- **Innovant Healthcare Limited** → `innovanthealthcare.co.uk` — name-exact match, own
  site confirms an Ophthalmic product category.
- **Litechnica Ltd** → `litechnica.co.uk` — branded "Litechnica Ophthalmic Products" on
  its own site.
- **Vision Pharmaceuticals Ltd T/A Spectrum** → `spectrumophthalmics.uk` — **strong
  registration-tier proof**: its own Terms of Use states "The term Vision Pharmaceuticals
  Ltd or 'Spectrum' ... registered office is Fernbank House, Springwood Way, Macclesfield,
  Cheshire, SK10 2XA. Our company registration number is 02175795" — an exact match on
  both legal name and company number to the framework's awarded-supplier name. Company
  number added to the seed.
- **Lenstec (Barbados) Inc** → `lenstecuk.com` — own site header states "Lenstec UK |
  Refractive Surgery | Lenstec (Barbados) Inc, Durkar, Wakefield, UK", an exact legal-name
  match.
- **Scope Ophthalmics** → `scopeeyecare.com` (its original `scopeophthalmics.com` domain
  no longer resolves; the company's current live site is the rebrand).
- **Sight Sciences UK Ltd** → `sightsciences.com` — global manufacturer site; its `/ous/`
  international section carries UK-specific press material (10,000+ UK OMNI procedures).
  No distinct sightsciences.co.uk storefront exists; UK entity is Companies House 13094159.
- **Beaver Visitec International Sales Ltd** → `bvimedical.com` (bvimedical.co.uk
  redirects here) — branded "BVI Medical", the Beaver/Visitec/Malosa/Vitreq/PhysIOL
  ophthalmic surgical device brand family, UK office in Abingdon, Oxfordshire.
- **Johnson & Johnson Surgical Vision** → `jnjvisionpro.com` — J&J's own EMEA
  professional site for its Surgical Vision division.

**5 left unconfirmed at the time of this run, no domain guessed** (logged to
OUTSTANDING.md rather than guessed): EziDrops Ltd, Meticuly INNOVATIONS Ltd,
OSI INC. Ltd, Vision Matrix, Instinctive Limited.

**Update, later the same day (17/09/2026): four of the five are now proved and
seeded** — see "Second pass on the five unconfirmed suppliers" at the end of this
document. Only OSI INC. Ltd remains unresolved.

## Crawled, and what came of it

All 11 domains were crawled (`crawl_supplier_site.py`). 6 captured a genuine
product range: Andersen Caledonia (81 products), Innovant Healthcare (17),
Litechnica (64), Vision Pharmaceuticals/Spectrum (40), Beaver Visitec (42),
Johnson & Johnson Surgical Vision (111), Scope Ophthalmics (44). 5 refused
cleanly (Associated Optical Products, Daybreak Medical, Lenstec UK, Sight
Sciences — all no readable WordPress/WooCommerce/sitemap catalogue).

Checked each captured range's actual product names — not just its division
labels — before mapping anything, per the brief's rule against forcing:

- **Beaver Visitec International Sales Ltd**: clean, forceable. Divisions are the
  manufacturer's own filing (Trifocal IOL, Monofocal IOL, Phaco equipment, Phaco
  Vitrectomy Equipment, OVDs, Surgical Dyes, Micro Forceps & Scissors, Punctal
  Occluders) and map straightforwardly onto this framework's five in-scope
  categories, consistent with existing entries for similar instrument divisions
  (Uniplex, Blink Medical, Scala Surgical) already in the map. Left 2 small/junk
  divisions unmapped ("Cryo-line" — a single product named identically to its
  division, looks like a crawl artifact; "Senza categoria" — Italian for
  "Uncategorised", 1 product, too little evidence).
- **Litechnica Ltd**: clean, forceable, after checking actual product names —
  "Keeler Products" (14 products) are Keeler-brand ophthalmoscopes, retinoscope
  sets, applanation tonometers and slit lamps, all diagnostic capital equipment.
  Mapped this division plus Ophthalmic Lasers, Laser Accessories, Imaging
  Systems, Smoke Evacuator (all equip), Trial Lenses (optom), Probes (cons,
  matching the existing Scala Surgical Ltd precedent).
- **Vision Pharmaceuticals Ltd T/A Spectrum**: mapped the two clean divisions
  (IOLS → iol; Ophthalmology Surgical Instruments & Consumables → cons). Left
  "Veterinary Ophthalmic Equipment" (12 products, out of scope — not human/NHS)
  and "Clean Air Units" (2, ambiguous — theatre ventilation, not specific to this
  framework's categories) unmapped.
- **Sense Medical Limited** (a pre-existing held supplier, not one I crawled this
  run, but with clean evidence already on record): its "Uncategorised" division's
  13 products are Canon retinal cameras, Canon Xephilio OCT devices, a Canon
  autorefractor-keratometer and Kowa slit lamp/field analyser — all ophthalmic
  diagnostic capital equipment. Mapped to equip.
- **Andersen Caledonia Ltd**: NOT mapped. Checked actual products: this is a
  general multi-speciality surgical-supplies/sterilisation company. Its
  divisions ("Surgical Supplies & Instruments", "Procedure Packs", and a
  mislabelled "Google Products" division — clearly a crawl/breadcrumb artifact,
  not a real company division) mix podiatry, dental, ENT, gynaecology and
  general-surgery products with genuinely ophthalmic ones (Iris Scissors, Iris
  Forceps, Strabismus Scissors, Baraquer Eye Speculum, and one clearly-ophthalmic
  "IVT Surgical Pack"). Same shape as the Osteotec/Salter Labs finding already
  logged (^o488): needs product-level override decisions, not a blanket division
  mapping. Logged to OUTSTANDING.
- **Innovant Healthcare Limited**: NOT mapped — its own site's homepage confirmed
  an "Ophthalmic" product category, but the actual crawl of all 17 "products" is
  the site's own top-level speciality NAVIGATION MENU (Cardiac/Vascular,
  Ophthalmic, Orthopaedic, Dental, General Surgery, ENT, Anaesthesia and
  Diagnostics, Neurosurgery, Obstetrics, Gynaecology, Urology, Intestines and
  Stomach, Otology, Rhinology, Oral Maxillo-Facial, Cranio Maxillo-Facial,
  Holloware) captured as if each label were a product. This is a crawl defect,
  not evidence about the supplier — no real product range was actually read.
  Logged to OUTSTANDING; needs a `--product-path` fix or a different crawl
  approach before this supplier can be assessed at all.
- **Johnson & Johnson Surgical Vision**: NOT mapped — the crawl of jnjvisionpro.com
  returned 111 products, but the great majority are German- and Czech-language
  ACUVUE contact-lens catalogue pages ("Alle ACUVUE® Kontaktlinsen", "Všechny
  kontaktní čočky značky ACUVUE®"). ACUVUE is J&J Vision *Care* (daily contact
  lenses), not J&J Surgical Vision (IOLs/cataract devices) — the division
  actually awarded on this NHS framework. A slice, not the range, and an
  unreliable one (wrong division, wrong market language). Logged to
  OUTSTANDING rather than mapped.
- **Scope Ophthalmics**: crawled cleanly (44 products, 8 divisions — HYLO®,
  OPTASE®, Hycosan®, Eyetamins®, Omega Vision, Optase Life, ACTASE™, EvoTears®)
  but none of it fits this framework's five in-scope categories. These are
  OTC dry-eye lubricants and nutritional supplements, not surgical consumables,
  capital equipment, glaucoma drug delivery, IOLs or optometry dispensing
  items. Correctly held, not forced — no OUTSTANDING line needed, this is a
  confirmed dead end for this framework rather than an open question.

Category decisions were written as per-supplier files in
`data/differentiator-map-parts/` (Beaver-Visitec-International-Sales-Ltd,
Litechnica-Ltd, Vision-Pharmaceuticals-Ltd-T-A-Spectrum, Sense-Medical-Limited),
folded in with `merge_differentiator_parts.py --apply` (18 decisions applied, 0
refused), after first registering the newly-crawled (supplier, division) pairs
with `union_differentiator_pairs.py --apply` (56 new pairs, 399 products).

Mapping alone did not publish these products — `build_differentiator.py` also
needs a per-product source (manufacturer detail page or an NHSSC match) before
a categorised product counts as published, same mechanism already noted in
today's earlier run for Sysmex UK. Ran `crawl_supplier_product_detail.py` for
Beaver Visitec (40/42 products captured), Litechnica (40/64, budget-limited —
more products remain to detail-crawl), Vision Pharmaceuticals/Spectrum (40/40),
and Sense Medical (19/20) before the products actually published.

## Coverage movement

Complete Ophthalmology Solutions 3: **11/53 published (20.8%) → 15/53 published
(28.3%)**. `Left` 27 → 19 (8 mapped-elsewhere unchanged, held 8→8 net after the
new pairs registered, needDomain 17→6). Four suppliers newly published: Beaver
Visitec International Sales Ltd, Litechnica Ltd, Vision Pharmaceuticals Ltd T/A
Spectrum, Sense Medical Limited.

`verify.py` passed (14 pre-existing warnings, unrelated to this framework) before
landing.

## Second pass on the five unconfirmed suppliers (17/09/2026, `outstanding-sweep` 17:10)

Re-checked the five suppliers this run left without a domain (^o515). Four are
proved from the company's own site and seeded; one is genuinely unresolved.

| Supplier | Domain | Proof |
|---|---|---|
| EziDrops Ltd | `ezidrops.com` | The site sells the EziDrops eye and ear drop applicators and its own Contact Us page gives "EziDrops, The Shires, Watford, WD25 0JL" — a match to the Companies House registered office for EZIDROPS LTD (11896998), 28 The Shires, Watford, WD25 0JL, SIC 32500. |
| Instinctive Limited | `instinctiveuk.com` | The site states "© 2019 Instinctive Limited" on every page and, in its privacy policy, "write to Instinctive Limited, 16 St Cuthbert's Street, Bedford MK40 3JG" — a name-exact match to the awarded supplier name. UK supplier of ophthalmic lasers (Ziemer LDV, Avedro KXL, Navilas). One active INSTINCTIVE LIMITED at Companies House (02616259, SIC 33130 repair of electronic and optical equipment). |
| Vision Matrix | `visionmatrix.co.uk` | The site gives "Vision Matrix Ltd, 31 East Parade, Harrogate HG1 5LQ" — an exact match to the registered office of VISION MATRIX LIMITED (03152261), SIC 32500 / 46460. |
| Meticuly INNOVATIONS Ltd | `meticuly.com` | The manufacturer's own Contact page and privacy policy both name the UK entity: "United Kingdom Office — METICULY Innovations Ltd, Office 235, 23 King Street, Cambridge, CB1 1AH" — an exact match to the registered office of METICULY INNOVATIONS LTD (13771048), SIC 25990 / 32500. |
| OSI INC. Ltd | none | **Still unresolved.** OSI INC. LTD (11611660) is a real active company at 50 Ripple Road, Barking, IG11 7PG, but its SIC is 86900 "other human health activities" and no website could be tied to it. The ophthalmic "OSI" sites that do exist (e.g. `osi.za.com`) are other companies in other territories. No domain recorded. |

**The "Vision Matrix may be an artifact of the framework matrix" reading in this
run's original note was wrong** and has been corrected above: Vision Matrix Ltd is a
real, active, ophthalmic-only UK supplier trading from the registered office
Companies House holds for it.

Company numbers were **not** promoted from `companyNumberCandidate` to
`companyNumber` for any of the four: none of these sites publishes its registration
number, which is the bar `confirm_company_numbers.py` applies. The registered-office
address matches are recorded as the proof for the *domain* only.

Not crawled in this pass — `visionmatrix.co.uk` is a WooCommerce catalogue and is the
obvious next candidate for the coverage task; `instinctiveuk.com` is a brochure site
with an expired TLS certificate (http only) and has no readable catalogue.
