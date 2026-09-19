# Framework coverage batch — 19/09/2026 (run 3) findings

Picked framework: **Infusion Pumps and Administration Sets and Associated Products** first
(22.2%, 11 left — the ledger's top pick this run), then switched to **Infant Feeding and
Accessories** (also 22.2%, 11 left) once Infusion Pumps turned out to have no permitted route
left. Both are logged below.

## Infusion Pumps and Administration Sets and Associated Products — worked, no movement possible

0 unresolved names, 10 `publishedElsewhereNeedingCategory`, 1 `needDomain`. Checked every item:

- **ICU Medical (incl. Smiths Medical) / "Infusion Therapy" division (84 products)** — already
  mapped to `vascular:conn` ("IV connectors, extensions & accessories"), and the mapping is
  correct: its own recorded examples (Clave Neutron, Nanoclave Manifolds and Stopcocks,
  needlefree IV connector, large bore extension set) are genuinely connectors/extension-set
  consumables, not pumps or administration sets. Not a mapping bug.
- **Crest Medical Ltd** — none of its (numerous, numerically-keyed) divisions carry any
  infusion/pump/administration-set/giving-set terms in their categories or examples. No lead.
- **Avanos Medical UK Limited** — captured range is Chronic Pain (COOLIEF) and Digestive
  Health (MIC-KEY, CORTRAK enteral). Neither line is infusion pumps or admin sets.
- **GBUK Group** — already tracked as a pending merge decision, ^o333 (07/09/2026). Its stub
  record explicitly says do not crawl.
- **Mediq Healthcare UK Ltd, Fannin (UK) Limited, Fresenius Kabi Ltd, Reliance Medical** — all
  four are recorded refusals (site unreadable), correctly excluded from re-crawl. They land in
  `publishedElsewhere` because they already publish products captured under other names/ranges,
  not because of anything actionable here.
- **Arcomedical Infusion Ltd (`needDomain`)** — already fully researched on 15/09/2026 (see the
  seed record's own note): `arcomed.co.uk` does not resolve (confirmed again today, DNS
  failure), and `arcomed.com` is the international CODAN group site covering the whole global
  range, which would misattribute foreign stock to the UK entity if crawled. Correctly left
  un-domained. Re-confirmed, not re-decided.

No changes made to this framework's data — every route already exhausted or correctly blocked.
Low coverage here is not neglect; it is the honest ceiling.

## Infant Feeding and Accessories — movement: 11 → 4 left, coverage unchanged at 22.2%

Coverage % didn't move (no new products captured), but the actionable backlog shrank from 11 to
4 by resolving every reachable name/domain gap and documenting the rest.

### `needDomain` (6) — all 6 attempted, all 6 refused (properly recorded, not left open)

Primary-source domain found and added to `data/supplier-seed.json` for each, then crawled with
`scripts/crawl_supplier_site.py --supplier ... --domain ...`:

| Supplier | Companies House | Domain | Crawl result |
|---|---|---|---|
| Alcado Limited | 07446966, active | alcado.co.uk | WordPress API unreadable |
| HiPP UK Ltd | 04498995, active | hipp.co.uk | HTTP 429 on every endpoint (rate-limited/WAF) |
| J Heinz Foods UK Limited | 08322668 "H.J. Heinz Foods UK Limited", active | heinzbaby.co.uk | Domain 301s to kraftheinz.com's marketing page, not a catalogue |
| MAM UK Ltd | 02380020 "MAM (UK) Limited", active | mambaby.com/gb | HTTP 404 on WP/WooCommerce APIs |
| Newell Brands | 00104102 "Newell Brands UK Limited", active | nuk.com | HTTP 404 on WP/WooCommerce APIs |
| Sinapi Biomedical UK | 14901052, active | sinapibiomedical.co.uk | robots.txt disallows |

All six are now recorded refusals with dated reasons — genuinely attempted, not silently
dropped. None had a second, better domain to try; each is the company's own confirmed site
(verified either via Companies House cross-match on registered activity, or the site's own
about/footer naming the entity).

### Unresolved names (2 in the brief) → 1 resolved, 1 left for Lou

- **Nestle Nutrition** — resolved. The NHS Supply Chain brief names a Nestlé division, not a
  registered company. SMA Nutrition's own site (smababy.co.uk/terms-and-conditions) names
  "Nestlé UK Ltd" as the operating entity; Companies House 00051491 NESTLE UK LTD. is the only
  active UK Nestlé entity of that name. SMA is Nestlé's UK infant-formula brand — an exact
  product-line match for this framework. Added as a new seed record (kept distinct from the
  existing "Nestle Health Science UK" record, a different division on different frameworks — do
  not merge the two). Domain set to smababy.co.uk (the brand site), not the general
  nestle.co.uk corporate site, to avoid pulling in unrelated confectionery/coffee/pet-food
  ranges. Crawled: HTTP 404 on WP/WooCommerce APIs, refused — recorded honestly.
- **Babease Limited** — NOT resolved, left unknown. Companies House has no single live match:
  "Babease Limited" (07473497) dissolved 01/11/2023, "Babease Foods Limited" (12320133) in
  liquidation, "Babease With Jess Ltd" (15880100) dissolved 11/08/2026. The framework brief
  names "Babease Limited" exactly, matching the dissolved entity. Publishing this supplier as
  live would very likely be wrong. Written to OUTSTANDING.md rather than guessed.

### `heldOnly` / `duplicateOfCapturedSupplier` (1) — identity/merge decision, not touched

**Danone Nutricia Early Life Nutrition** — the seed record's own domain (nutricia.co.uk) is
already captured under a different canonical name, "Nutricia Ltd". Same shape as the GBUK
Ltd/GBUK Group duplicate (^o333): crawling this record again would file the same catalogue
twice and double-count it in the ledger. The fix is a merge decision, which is Lou's to make,
not a re-crawl. Written to OUTSTANDING.md.

### `publishedElsewhere` (2) — checked, no lead

Laborie Medical Technologies UK Ltd and Medela: both already publish elsewhere; neither's
captured divisions carry infant-feeding/neonatal terms that this framework's `neonatal:*`
categories would cover. No action.

## Landed

`./land.sh` with `data/supplier-seed.json`, `data/supplier-products.json`,
`company-aliases/company-alias-registry.json`, `data/differentiator.json`,
`data/coverage-ledger.json`, `docs/COVERAGE-LEDGER.md`,
`docs/framework-coverage-findings-2026-09-19-run3.md`. `verify.py` must pass before push.

Two judgement calls written to `OUTSTANDING.md` (Cowork-OS root, not this repo): Babease
Limited's trading status/identity, and the Danone Nutricia / Nutricia Ltd merge decision.
