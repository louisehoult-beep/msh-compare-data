# Framework coverage batch — 19/09/2026 (run 4) findings

Picked framework: **Patient Monitoring Equipment, Bedside Equipment Alarm Monitoring Systems,
Related Products and Services** (22.9%, 16 left at pick time). The ledger's two lower-coverage
picks — Infusion Pumps and Administration Sets (22.2%) and Infant Feeding and Accessories
(22.2%) — were both already worked to exhaustion earlier today (see run 3's findings): every
remaining item in both is either a recorded refusal, a company-identity decision already
queued for Lou, or a mapping dead end. Re-picking either would have re-read the same answered
ground, so this run moved to the next real candidate with unworked material.

## Result: coverage 22.9% (8/35) → 31.4% (11/35). Three suppliers newly published.

### `needDomain` (10 attempted) — 7 domains resolved and added, 2 crawled successfully

| Supplier | Domain (primary-source confirmed) | Crawl result |
|---|---|---|
| Neurogen Ltd | neurogenmedical.com | **18 products captured** |
| Penlon | penlon.com | **73 products captured** |
| Dot Medical Limited | dot-medical.com | refused (not WordPress/WooCommerce, no product sitemap) |
| EDAN Medical (UK) Ltd | edanmedicaluk.ltd | refused (same shape) |
| TBG Solutions Limited | tbg-solutions.com | refused (same shape) |
| UNEEG Medical UK Ltd | uneeg.com | refused (same shape) |
| Viamed Ltd | viamed.co.uk | refused (same shape) |

Every domain was confirmed against a primary source before use — Companies House registered
office matching the site's own footer/about address exactly (EDAN, TBG Solutions, Viamed,
Penlon), or the site's own Terms of Use naming the company and number (Neurogen), or the
site's own text plus its NHS Supply Chain framework presence (Dot Medical). None were
pattern-matched from an old link.

**UNEEG Medical UK Ltd — used the group's single global site deliberately.** UNEEG medical A/S
(Denmark) has no separate UK-only catalogue; its one global site (uneeg.com) explicitly serves
UK-licensed clinicians and names UK as one of its four subsidiary markets. Unlike a diversified
multinational's global site (the Arcomedical/CODAN case from 15/09/2026, where crawling the
parent would misattribute an unrelated international range to the UK entity), UNEEG's whole
worldwide business is one narrow device family — long-term ambulatory EEG monitoring — so there
is no misattribution risk. Not yet crawled this run (refused: no WordPress/WooCommerce route);
left as a recorded refusal for a future retry with `--product-path`.

### `needDomain` (3 left, genuinely blocked — not re-attempted, not guessed)

- **Nihon Koden (NHS Supply Chain's own spelling; the real company is "Nihon Kohden UK
  Limited", Companies House 07350287, Guildford)** — Nihon Kohden has no UK-specific
  catalogue; its product range is published only on the shared regional site
  (eu.nihonkohden.com), which covers many countries' stock. Crawling it would misattribute the
  whole European range to the UK entity, the same risk flagged for Arcomedical/CODAN on
  15/09/2026. Left un-domained.
- **Optima Medical Ltd (Companies House 03737869, Guildford — 75%+ owned by Natus
  Manufacturing Limited)** — its own former catalogue domain, optimamedical.com, now
  301-redirects permanently to natus.com, the parent's global site. Optima Medical's own
  product range has been absorbed into Natus's; there is no longer a UK-specific site to crawl
  without the same cross-border misattribution risk. Left un-domained.
- **Pro Health Solutions Limited — identity does not match, written to OUTSTANDING.md.** The
  only UK company of this exact name found (Companies House 06804587, "PRO-HEALTH SOLUTIONS
  LTD", trading as IVVION) makes food supplements and vitamins — nothing to do with patient
  monitoring or bedside alarm equipment. Either NHS Supply Chain's brief names a different,
  unlisted entity, or this is the wrong company entirely. Not guessed; left unresolved.

### `heldNeedingCategory` (1) — Deltex Medical Ltd, genuine category confirmed but crawl data unusable

Deltex's CardioQ-ODM is confirmed, from the manufacturer's own product page, to be a
haemodynamic monitor (oesophageal Doppler, measures stroke volume/cardiac output in real
time) — squarely `monitoring:spec`. But the crawl under the "Cardioq Odm" and "Cardioq Odm
Plus" divisions captured navigational sub-page titles ("How The ODM Works", "Technical
Specification", "Accuracy Precision", "Pressure Parameters"), not real distinct products.
Mapping the division would publish these titles as if they were purchasable items — worse
than leaving it held. Written to OUTSTANDING.md as a crawler-capture problem, same shape as
the Healthcare 25 (^o534) and Electro Spyres (^o551) findings: needs a better product-boundary
detection on this site, not a mapping decision.

### `publishedElsewhereNeedingCategory` (5 checked, 1 resolved via a missing crawl step, 4 no lead)

- **HC21 (UK) Ltd — resolved.** Its "Monitoring" division (Nellcor pulse oximetry, Nellcor
  bedside SpO2 PM100N, Genius 3 tympanic thermometer, FILAC 3000) was already mapped to
  `monitoring:gen` by an earlier run, but none of the four had ever had
  `crawl_supplier_product_detail.py` run against them — no source, so `build_differentiator.py`
  held them anyway ("no source carries this product"). Ran the targeted detail crawl for the
  four named products; all four captured; all four now publish. **This is a general finding,
  not specific to HC21**: a division can carry a correct category mapping and still never
  publish until its products also go through the separate detail-crawl step — the two are not
  the same job, and coverage-ledger's "mapped elsewhere" count cannot tell them apart.
- **Philips, Draeger Medical UK — no lead.** Both are fully curated (`t: [gen, spec, alarm]` in
  `data/compare-suppliers.json`'s monitoring speciality) but both are recorded refusals
  (robots.txt / no readable catalogue) with no own-site crawl data, so nothing to map.
- **Probo Medical (formerly MIUS)** — captured range is entirely used/refurbished ultrasound
  scanner brands (GE, Philips, Siemens, Mindray, etc. as division names) — an imaging reseller,
  not a monitoring/alarm supplier. No lead.
- **Zoll Medical UK Limited** — checked its one "Critical Care" item (Iqool, a targeted
  temperature-management/cooling system) — that is `theatres:warm` territory, not monitoring.
  No lead in this speciality.

## Landed

`./land.sh` with `data/supplier-seed.json`, `data/supplier-products.json`,
`data/supplier-product-detail.json`, `data/differentiator-category-map.json`,
`data/differentiator-map-parts`, `data/differentiator.json`, `data/coverage-ledger.json`,
`docs/COVERAGE-LEDGER.md`, `docs/framework-coverage-findings-2026-09-19-run4.md`. `verify.py`
must pass before push.

Two items written to `OUTSTANDING.md` (Cowork-OS root, not this repo): Pro Health Solutions
Limited's identity mismatch, and Deltex Medical's unusable CardioQ crawl data.
