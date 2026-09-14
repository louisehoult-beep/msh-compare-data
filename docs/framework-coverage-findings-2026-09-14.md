# Framework coverage batch — findings, 14/09/2026

Run of the `differentiator-framework-coverage` scheduled task.

## Frameworks investigated but not worked — already blocked, already logged

The ledger's own lowest-coverage-STARTED-with-work-left pick was, in order:
**Radiotherapy Ancillary Devices** (15.4%), **Digital Diagnostic Solutions** (16.7%),
**Insulin Pumps, CGM & Hybrid Closed Loop** (16.7%), **Infusion Pumps** (18.5%),
**Electrodes, Ultrasound Gels, Defibrillation** (18.9%). All five were checked against
this run's evidence before being set aside — none had a permitted route this run:

- **Radiotherapy Ancillary Devices**: re-confirmed unchanged. Xiel Ltd's 23 "Radiotherapy"
  products (Sensus SRT-100, thermoplastics, vacuum bags & positioning cushions, TBI STEP,
  SRS Solution) are genuinely ancillary/dosimetry/patient-positioning devices with no
  matching oncology vocabulary term (`oncology:radio` is defined as capital equipment —
  linacs, gamma knife, afterloaders — and does not fit; `oncology:acc` is procedure
  consumables). Medical Imaging Systems (MIS Healthcare) and Promedics Orthopaedics Ltd's
  captured ranges (CT/MRI/DXA scanners; orthopaedic bracing/immobilisers respectively) show
  nothing resembling this framework's scope. Already logged: `^o434`, `^o465`, and item 3 of
  `Hub/identity-vocab-decision-queue.md` (`^o411`, routing-scope tie, Lou's ruling pending).
  This is now the 4th run in a row (10, 11, 13, 14/09) confirming zero movement here — worth
  actioning `^o452`/`^o411` directly, or teaching the picker to skip a framework whose entire
  Left list is already in the decision queue.
- **Digital Diagnostic Solutions**: already resolved as structurally blocked (queue item 4,
  superseded) — no new investigation needed.
- **Insulin Pumps, CGM & Hybrid Closed Loop** (NEW investigation this run): the 3 `Left`
  suppliers — Abbott Laboratories Limited, Medtronic, Urathon Europe Ltd — turned out to have
  no permitted route either, for three different reasons:
  - Abbott and Medtronic are **already correctly refused** under their real seed identities
    (curated records "Abbott Diabetes Care", refused 20/08/2026, and "Medtronic", refused
    08/09/2026 — both re-confirmed by dry-run this run, same refusal). The coverage ledger
    counts them as `publishedElsewhere` "actionable" because the framework's literal NHSSC
    award-list name ("Abbott Laboratories Limited") doesn't canonicalise to the curated
    "Abbott Diabetes Care" seed record the refusal is actually recorded against — a
    name-canonicalisation gap in the ledger, not real available work. **New finding, not
    previously logged** — see OUTSTANDING.
  - Urathon Europe Ltd's curated note names a real, dated product ("Yuwell Anytime CGM
    (CT-3 system) — exclusive UK distribution since 01/05/2025") but their crawled catalogue
    (104 products, 5 divisions: Mobility Aids, Moving & Handling, Bathing/Showering/Toilet
    Aids, Around the Home, Bedroom Aids) has nothing matching it. Re-crawled this run
    (dry-run, urathon.com) — identical 104/5 result, confirming the CGM product line sits
    somewhere the standard sitemap crawl doesn't reach. Not something to force.
- **Electrodes, Ultrasound Gels, Defibrillation**: Electro Spyres already logged (`^o434`);
  its one `needDomain` supplier, Salter Labs UK Ltd, is already queued at decision-queue
  item 2 (`^o403`) — a genuine T/A identity tie, not decided here.

## Framework worked: Total Orthopaedic Solutions 3

Moved to the next lowest-coverage framework with real, forceable work rather than
re-investigate five confirmed dead ends. 19.8% coverage (20/101 published), 52 of its
60 `Left` items are `needDomain` — the largest such backlog of any framework. (A previous
run earlier today already added 4 unresolved suppliers to the seed without domains —
Globus Medical, NuVasive, Ortho Solutions, M.D.M Medical — see `^o467` re M.D.M's
liquidation flag; left untouched this run.)

Researched candidate domains (web search, not a scraped search engine — the same
`--candidates-file` route the domain-seeding tool documents) for 15 of the 52 `needDomain`
suppliers and ran `scripts/seed_supplier_domains.py` per supplier against those
candidates, keeping the strong registration-number proof bar (no `--accept-name`):

- **1 proven**: **NSK United Kingdom Limited** → `nsk-shop.co.uk`, proved by Companies
  House registration number 06042707 matching the site's own published number. Crawled:
  745 products across 12 divisions. All 12 divisions read as dental equipment (Contra-angles,
  Oral Hygiene, Dental Laboratory, Air Turbines, Clinical Micromotors, Endodontics,
  Autoclave, Mobile Dentistry) except "Surgical" (171 products — Surgic Pro2/VarioSurg bone
  and oral-maxillofacial surgery motors, implant-preparation and sinus-lift tips, sagittal/
  oscillating/reciprocating saw blades). The "Surgical" division's own naming is
  oral-surgery/dental-implant terminology throughout (sinus lift, root planing, extraction,
  MulTipeg abutment analogues) with no orthopaedic (hip/knee/spine/trauma) products visible
  anywhere in the 745. Held, not mapped into `ortho:*` — forcing bone-saw-shaped products
  into an orthopaedic category on the strength of the tool's name alone would be exactly the
  kind of guess this brief prohibits. Logged to OUTSTANDING as an identity/scope question:
  is NSK genuinely supplying a distinct orthopaedic line not on their public dental
  storefront, or is the framework award for a narrower lot than their catalogue shows?
- **14 refused on the strong bar**: Orthofix Limited, Materialise, Medartis Ltd,
  Paragon 28, Spineart UK Ltd, implantcast UK, joimax UK, TRB Chemedica (UK) Ltd,
  KLS Martin UK Limited, Silony Medical Ltd, Osteon Medical Ltd, Neptune Medical Limited,
  3D Metal Printing Ltd, Biomet 3i UK Ltd (ZimVie) — each read, but the site never states
  a registration number matching the Companies House number already recorded for that
  supplier (mostly global/parent-company sites for UK subsidiaries, or a UK site that
  simply doesn't publish its number). Correct, honest refusals — not written to the seed.
  Their curated list stands.

## A repo-formatting side-fix, not framework data

`verify.py`'s `check_notice_citations` false-positived on NSK's newly-written link
evidence: the raw scraped address fragment `seed_supplier_domains.py` writes into
`links[].source` included the street name "Rutherford Close", and the word "Close" matched
the check's deadline-word regex (`clos(?:e|es|ed|ing)`) sitting within 300 characters of
the framework's bare notice number `2023/S 000-025037` in the neighbouring `note` field —
an accidental collision between a British street-name suffix and a deadline-detection
word list, not a real deadline-citation problem. Trimmed the quoted fragment to drop the
street name (kept the registration number, company name and postcode — the actual
evidence) rather than touch the check itself. **This can recur for any future supplier
whose registered address ends in "Close", "Rise", "Ending" etc.** — worth a narrower
regex or a JSON-structure-aware check rather than a whole-file text scan, but that is a
`verify.py` change affecting every future run, out of scope for one framework's data this
session. Logged to OUTSTANDING.

## Coverage movement

Total Orthopaedic Solutions 3: 20/101 published (19.8%) → 20/101 published (19.8%,
unchanged — NSK's range didn't map into an in-scope category). `needDomain` 52 → 51,
`heldNeedingCategory` 3 → 4. Real forward motion (a domain found and proven, a genuine
745-product capture on record) even though the published count didn't move this run —
matches the brief's own point that coverage % is not the only signal of progress.

## Second run 14/09 — Infusion Pumps and Administration Sets and Associated Products

Coverage-ledger regeneration this run showed the same lowest-coverage pick order as the
earlier run today (Radiotherapy 15.4%, Digital Diagnostic Solutions 16.7%, Insulin Pumps
16.7%, Infusion Pumps 18.5%). Radiotherapy, Digital Diagnostic Solutions and Insulin Pumps
were already confirmed dead ends earlier today (see above) and re-confirmed unchanged
against this run's fresh ledger. Worked **Infusion Pumps and Administration Sets and
Associated Products** (18.5%, 5/27 published), whose 7 `needDomain` suppliers had not yet
been attempted today.

All 7 were already correctly identity-resolved in the seed (own distinct records, `company_alias.py`
returns exact-name/no-conflict for each), so no identity work was needed — only domain-finding.
Researched primary sources (company's own site, exhibitor listings, Bloomberg company profile,
LinkedIn) for each of the 7:

- **BMS Critical Care Ltd** → `bmscriticalcare.com`, confirmed via the company's own About page.
  Crawled: 24 products across 8 divisions (PE/PVC Syringe Pump Lines, ECO RANGE, EasiFlush
  NeedleFree Range, 4 Way Stopcock & Lines, T34 Compatible Line, EasiFlo Flow Regulator Set,
  Wide Bore Lines, Accessories) — IV administration lines, stopcocks and needle-free connectors.
  Held, not mapped: no `differentiator-category-map.json` entry yet for this supplier. Logged to
  OUTSTANDING (`^o473`) rather than guessed at a category, per the brief's rule against forcing
  mapping decisions in this run.
- **BECTON DICKINSON (CME) U.K. LIMITED** → `cme-infusion.com`, confirmed via Bloomberg company
  profile tying the company number directly to "CME Medical UK Ltd". Crawl refused: robots.txt
  disallows automated reading. No products captured, so the pre-existing identity-tie flag
  against the published "BD — Becton, Dickinson" record (`^o466`, already logged before this run)
  is unaffected — nothing was published under either name this run.
- **Eitan Medical UK Ltd** → `eitanmedical.com`, confirmed via the company's own UK-launch press
  release. Crawl refused: robots.txt disallows automated reading.
- **Qualasept Ltd t/a Bath ASU** → `bathasu.com`, confirmed as the trading name's own site. Crawl
  refused: WordPress API exposes no product post type and no WooCommerce Store API — Bath ASU is
  an aseptic-compounding manufacturer, not a catalogue storefront.
- **TLB Medical Supplies** → `tlbmedicalsupplies.com`, confirmed as the registered entity's own
  site. Crawl refused: robots.txt disallows automated reading.
- **Braun and Company Limited** → `brauninternational.com`, confirmed via its own exhibitor
  listing (ebme.co.uk), but the domain now resolves to an expired-domain parking page
  (`exp.gname.net`) rather than the company's site — crawl correctly refused it as unreachable.
  Logged to OUTSTANDING (`^o474`).
- **Arcomedical Infusion Ltd**: no domain added. `arcomed.com` (used in the company's own email
  address) is the Swiss parent arcomed AG's site (recently acquired by CODAN), with no UK/NHS
  mention; the UK-specific domain LinkedIn lists (`arcomed.co.uk`) does not resolve. Left
  un-domained rather than risk filing the Swiss parent's catalogue under the UK entity's name.
  Logged to OUTSTANDING (`^o475`).

All 6 domains added to `supplier-seed.json` as `links: [{"label": "Website", ...}]` entries
(round-trip verified against the file's current minified format before writing).

## Coverage movement

Infusion Pumps and Administration Sets and Associated Products: 5/27 published (18.5%) →
5/27 published (18.5%, unchanged — BMS Critical Care's capture didn't map into an in-scope
category). `needDomain` 7 → 1 (Arcomedical Infusion Ltd only), `heldNeedingCategory` 0 → 1.
Real forward motion (2 domains proven and crawled — one live capture, one confirmed-dead — plus
3 honest robots.txt/no-catalogue refusals recorded) even though the published count did not
move this run, matching the brief's point that coverage % is not the only signal of progress.
