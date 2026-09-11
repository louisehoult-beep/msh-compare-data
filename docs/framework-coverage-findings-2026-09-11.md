# Framework coverage batch — findings, 11/09/2026

Run of the `differentiator-framework-coverage` scheduled task. Framework worked:
**Electrodes, Ultrasound Gels, Defibrillation and Related Consumables** (cardiology
speciality). Coverage moved 6/37 published (16.2%) → 7/37 published (18.9%).

## What moved

- Found and added confirmed domains for 5 of the framework's 6 `needDomain`
  suppliers: Electro Spyres Healthcare Limited (electrospyres.com), Techmed
  Charts UK Limited (techmedcharts.co.uk), Zoll Medical UK Limited (zoll.com),
  Meditrade UK Ltd (meditradeuk.com), Medevolve Limited (medevolve.co.uk, plus
  the alias "Medevolve UK Ltd" it trades under — Companies House 08022604).
  Salter Labs UK Ltd was left with no domain: no UK-specific site was found by
  search, only the US parent (salterlabs.com).
- Crawled all 5. Electro Spyres (46 products) and Zoll (49 products, 5
  divisions) captured successfully. Techmed Charts and Meditrade UK Ltd were
  refused — the site's WordPress API exposes no product post type and the
  WooCommerce Store API returned 404 on both, a genuine site-structure refusal,
  not something to force. Medevolve's domain did not answer at all (TLS error,
  both via the crawler and a manual fetch) — recorded as refused, not guessed.
- Mapped 2 of Zoll's 5 divisions with evidence: "Accessories" (7 products —
  SurePower Defibrillator Battery System, Battery Finder, Pro Padz, OneStep,
  CPR Uni Padz, Pedi Padz, Hospital) → `cardiology:defib`, and "Software And
  Data" (12 products — RescueNet CaseReview/CodeNet/12 Lead/Live, Device
  Dashboard, EMS and Fire Software, Clinical Data Assistance) → `digital:sw`.
  Ran `crawl_supplier_product_detail.py` afterwards so the mapped rows carry a
  source and actually publish (40 of 49 products captured this run; 3 of the 7
  Accessories products and 3 of the 12 Software products still lack a captured
  detail page and remain held pending a future run).

## Left unmapped — genuine judgement calls, not decided here

- **Zoll's "Emergency Care" division (28 products)** genuinely spans several
  Hub categories at once — AEDs/defibrillators (`cardiology:defib`/`capital`),
  ventilators (Z Vent, Bellavista range, 3100 HFOV, LTV Series →
  `respiratory:vent`), and patient monitors (Propaq MD/M → `monitoring:gen`)
  — with no further division breakdown from the site to split it by. Mapping
  the whole division to one category, or to a list, would show ventilators
  compared as defibrillators and vice versa. "Critical Care" (1 product,
  Iqool — a cooling/temperature-management device) and "Uncategorised" (1
  product, "Sleep Apnea" — reads as a category link, not a real product) are
  too small/ambiguous to map alone.
- **Electro Spyres Healthcare Limited** crawls as one flat "Uncategorised"
  division (46 products) with no sub-division breakdown, spanning ultrasound
  gels, ECG electrodes, wound dressings and electrosurgical accessories — a
  genuinely mixed product range. The mapping tool only supports a decision
  per (supplier, division) pair, not per product, so this can't be mapped
  without misfiling some products under a category they don't belong to.
  Per-product detail crawl also failed for all 40 pages attempted this run
  ("could not isolate usable product content from navigation/boilerplate"),
  so even a division-level mapping would still not publish today.
- **Henleys Medical Supplies Limited** (held before this run, untouched):
  same shape — one flat "Uncategorised" division, 179 products, and only 4
  examples visible (SpO2 Extensions, reusable BP cuffs, ECG cables, Funnels).
  Most of that looks like exactly this framework's monitoring/cardiology
  consumables, but "Funnels" doesn't fit, and 175 of the 179 products have no
  visible example at all — mapping the whole division on 4 samples risks
  misfiling the rest. Needs someone to read the company's own site directly.

## Adjacent frameworks checked, not worked (out of run scope)

- **Digital Diagnostic Solutions** (13.0% coverage) was the ledger's own
  top pick this run, but every one of its 11 remaining `left` suppliers
  (Draeger Medical UK, Epredia, Getinge, Haemonetics, Huntleigh, Olympus
  (KeyMed), Leica Microsystems (UK), Philips, Roche Diagnostics UK, Siemens
  Healthineers, Sysmex UK) sits in `publishedElsewhereNeedingCategory` —
  each already publishes real crawled products under other Hub categories
  (pathology, cardiology, theatres, respiratory, etc.) but none under
  `digital:*`. This may be a structural ceiling rather than a gap: this
  repo's own `compare-suppliers.json` already documents, for the `digital`
  speciality, that "software and managed services are bought Direct, produce
  no catalogue line, and have no comparable unit" — these suppliers'
  diversified crawled catalogues are consumer/consumables product lines, and
  their actual digital-diagnostics offering (imaging IT, LIMS, connectivity
  platforms) is plausibly enterprise software with no browsable catalogue
  page to crawl at all. Nothing was changed here — worth a decision on
  whether this framework should be marked structurally blocked instead of
  low-coverage, before another run re-picks it and re-investigates the same
  11 suppliers from scratch.
- **Radiotherapy Ancillary Devices incl Dosimetry Patient Positioning and QA
  Devices** (15.4% coverage): its one `heldNeedingCategory` supplier,
  Promedics Orthopaedics Ltd, has a large crawled catalogue (429 products
  across ~35 divisions) that is entirely general orthopaedic bracing,
  splinting, collars and slings — nothing resembling dosimetry, patient
  positioning or QA equipment. Either this company's radiotherapy-specific
  product line is not on the crawled site, or the framework award covers a
  narrow lot not reflected in its public catalogue. Not something to guess
  at — left unmapped.
