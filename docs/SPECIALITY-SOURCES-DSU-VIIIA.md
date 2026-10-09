# Field spec: MHRA Drug Safety Updates and Drug Tariff Part VIIIA, for the panel builder

Added 29/09/2026. Both files are built and gated; `scripts/build_speciality_panels.py` does not read them yet. This is what it should read when it is wired.

## data/mhra-dsu.json

Writer: `scripts/refresh_mhra_dsu.py`. Workflow: `.github/workflows/mhra-dsu.yml`, daily at 02:55 UTC. Mapping table: `config/mhra-dsu-speciality-map.json`. Gate: `verify.py` `check_mhra_dsu`, plus the shrink guard.

| Field | Meaning |
|---|---|
| `dataAsOf` | ISO date of the run |
| `sourcePage` | https://www.gov.uk/drug-safety-update |
| `coverage.complete` | always true in a published file (the writer and the gate both refuse a partial walk) |
| `counts.bySpeciality` | `{panelSlug: n}` for every panel, zeros included |
| `unmappedFacets[]` | `{facet, label, updates, reason}`: GOV.UK facets that reach no panel, with the reason |
| `panelsWithNoFacet[]` | panel slugs that no GOV.UK facet maps to. For these the honest state is "MHRA does not tag Drug Safety Updates to this area", not "no safety updates" |
| `updates[]` | newest first, one per Drug Safety Update |

Each `updates[]` row:

| Field | Meaning |
|---|---|
| `title` | GOV.UK title, verbatim |
| `url` | `https://www.gov.uk/drug-safety-update/...` |
| `published` | `YYYY-MM-DD`, GOV.UK `first_published_at` |
| `updated` | `YYYY-MM-DD`, GOV.UK `public_timestamp` |
| `summary` | GOV.UK description, whitespace collapsed |
| `therapeuticAreas[]` | GOV.UK's own facet slugs (labels are in `facetLabels`) |
| `specialities[]` | Hub panel slugs, derived only from `therapeuticAreas` through the mapping table |
| `roundup` | true for the monthly "Letters and medicine recalls sent to healthcare professionals" digest |

Suggested panel use: `[r for r in updates if slug in r["specialities"]]`. Show the newest few, with the date and link. Consider leaving out `roundup` rows. Cite "MHRA Drug Safety Update, GOV.UK" with `dataAsOf`.

## data/drug-tariff-part-viiia.json

Writer: `scripts/refresh_drug_tariff_part_viiia.py`. Workflow: `.github/workflows/drug-tariff.yml`, daily at 06:40 UTC alongside Part IX. Gate: `verify.py` `check_drug_tariff_viiia`, the inline sanity gate in the workflow, and the shrink guard.

This file has the same shape as `drug-tariff-part-ix.json`: `dataAsOf`, `effectiveMonth`, `source`, `sourcePage`, `schema`, `rowCount`, `note`, `rows` (array of arrays). It adds two fields:

- `latestPublishedMonth` is the newest edition on the NHSBSA index. It is often next month, because NHSBSA publishes each edition ahead of time.
- `categoryCounts` is `{A, C, H, M}`.

`schema`: `["medicine", "packSize", "unit", "category", "price", "vmpSnomed"]`

| Column | Meaning |
|---|---|
| `medicine` | NHSBSA VMP description, verbatim |
| `packSize` | pack quantity, verbatim string |
| `unit` | pack unit (tablet, capsule, gram and so on) |
| `category` | Drug Tariff category letter: `A`, `C`, `M` or `H` |
| `price` | basic price in pence, integer (3750 means £37.50) |
| `vmpSnomed` | dm+d VMP code, the join key to prescribing data |

The file carries no speciality field. That is deliberate. Part VIIIA has no BNF chapter or therapy column, so mapping lines to specialities belongs in the panel builder, using a per-panel `medicine` regex like Part IX's `vmpFilter`. Always state `effectiveMonth` beside any price.
