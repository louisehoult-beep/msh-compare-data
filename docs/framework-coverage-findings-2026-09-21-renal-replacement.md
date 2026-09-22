# Framework coverage findings — 21/09/2026 (Renal Replacement Therapies)

Framework worked: **Renal Replacement Therapies Services, Technologies and
Consumables** (`renal` speciality). Coverage 24.0% → 28.0% (6 → 7 of 25
awarded suppliers published), Left 14 → 8.

## Picker note: Ultrasound Scanners was checked and skipped, not neglected

The ledger's own pick (lowest-coverage STARTED framework with non-zero Left)
was **Ultrasound Scanners and Associated Options and Related Services**
(23.8%, 6 left, all 6 `publishedElsewhereNeedingCategory`). Checked all 6
before doing any work, per the brief's 06/09 warning that a low coverage %
can mean exhausted rather than neglected: BioSpectrum Ltd (19 crawled
products — urology/gynaecology/ENT/general-surgery only), Celtic SMR Ltd
(165 products — one "Ultrasound" item is filed under its own Veterinary
division, not human healthcare), Hologic UK (95 crawled products — Faxitron
specimen radiography, mammography, breast biopsy, molecular diagnostics;
zero ultrasound scanners), and Philips / ProSys International Ltd / Siemens
Healthineers (each refused for crawling; their only currently-captured
products are unrelated NHSSC items — Philips Respironics CPAP masks, ProSys
Secco bowel-management bags, Siemens Atellica/EPOC pathology analysers).
**None of the 6 has a single genuinely-ultrasound-scanner product under any
currently accessible source.** Moved to the next framework on the ledger's
own "lowest-coverage STARTED, work left" list instead. Left untouched —
nothing to map, nothing to re-crawl (none of the 6 carry a refusal to
overturn either).

## What moved

- **Vantive** — the framework's own supplier list names it *"Vantive Limited
  (formerly part of Baxter Healthcare Ltd)"*, which does not normalise to
  any of the existing supplier-seed aliases for the canonical "Vantive"
  record (which already carries "Vantive Limited", not this longer
  parenthetical form). Company identity re-confirmed at Companies House
  (14981842, active) — matches the record Lou's seed already holds. Added
  the exact award-source string as a new alias on the existing "Vantive"
  record (no new supplier created — one already existed, fully verified,
  with 54 NHSSC-sourced products already mapped to `renal:hd`/`renal:pd`).
  Rebuilt `company-aliases/company-alias-registry.json` via
  `company_alias.py build` (**required after any supplier-seed.json alias
  edit — a stale registry silently keeps resolving the old way**). Vantive
  now resolves and publishes for this framework immediately — no crawl
  needed, the products were already there.
- **VWS (UK) Ltd** — same shape: the framework names it *"VWS (UK) Ltd
  Trading As Veolia Water Technologies"*, one alias short of the existing
  fully-verified "VWS (UK) Ltd" record (Companies House 00327847, confirmed
  sole dedicated water-treatment provider on this framework). Added the
  alias; it now resolves (was `unknown`, now correctly counted).
  **Does not yet publish.** Its 53-product site crawl (sitemap-only, flat
  "Uncategorised" division, all names read from URL slugs) includes two
  genuinely unambiguous renal items by name alone: "Hemoro 4 One Home
  Hemodialysis Machine" (states "Hemodialysis Machine" outright) and
  "Nephro Safe" (the clinical "Nephro-" root, from a water-treatment
  supplier — mapped to the existing `renal:water` type, "Water treatment &
  managed service", not a therapy-modality type, since it's ancillary water
  infrastructure not a dialysis machine/consumable). Added both as
  `product-override` entries in `differentiator-category-map.json`. Neither
  publishes: `build_differentiator.py` requires a `sources` entry
  (manufacturer detail page or NHSSC item) before a categorised product can
  publish, and VWS has neither — the sitemap-only crawl carries no detail
  page, `crawl_supplier_product_detail.py --product "Hemoro 4 One Home
  Hemodialysis Machine" --product "Nephro Safe"` came back "sitemap carries
  no product URLs to match against" for both, and no NHSSC cache entry
  exists for this supplier. Same capture-route shape as Electro Spyres
  (^o551) — a source-gap, not a mapping decision. (QuidelOrtho, cited here as
  the same shape, was NOT: its premise was wrong and its 309 rows published on
  22/09/2026 with no code change — see framework-coverage-findings-2026-09-21.md.)
  The two decisions are banked in the category map and will publish
  automatically the moment either source becomes available.
- **Domain lookups, all refused on crawl (genuine attempts, not left
  blank):** CytoSorbents Medical UK (cytosorbents.com — robots.txt
  disallows), Maltron International Ltd (maltronint.com — no WP/Woo product
  route), Medica Advanced Technologies Ltd (uk.medica-spa.com — confirmed
  genuinely relevant, dialysis/CRRT/apheresis range visible on the site, but
  no WP/Woo product route), Terumo BCT (terumobct.com — no WP/Woo product
  route). Nikkiso Medical (nikkisomedical.eu, already on record) also
  attempted — no WP/Woo product route. All 5 now carry a proper recorded
  refusal with domain, rather than sitting as "need domain" with nothing
  tried.
- **Nipro Medical UK Ltd** — domain search surfaced `nipro-dmed.com`,
  matching the existing seed alias "NIPRO D.MED UK LTD", but it 301-redirects
  to `nipro-diagnostics.de` — Nipro's German blood-glucose diagnostics
  business, unrelated to the dialysis range this framework awards. **Not
  used.** Left as "need domain" — a future run should look for Nipro's
  actual UK dialysis-equipment site (distinct from both nipro-group.com's
  general corporate site and the diagnostics business) rather than repeating
  this search.
- **Xtra-Med** — no matching company or website found by name search. Left
  as "need domain"; may need the NHS Supply Chain award notice itself
  checked for a registered entity name, which wasn't attempted this run.

## Process note

Editing `data/supplier-seed.json` aliases does **not** by itself change what
`company_alias.resolve()` returns — `scripts/build_coverage_ledger.py` and
`scripts/build_differentiator.py` both read the pre-built
`company-aliases/company-alias-registry.json`. Ran
`python3 company-aliases/company_alias.py build` after the seed edit, before
rebuilding the differentiator; without it, the coverage figures below would
have shown 24.0% unchanged despite the alias fix already being on disk.
