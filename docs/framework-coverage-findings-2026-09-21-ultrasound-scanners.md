# Framework coverage findings — 21/09/2026 (Ultrasound Scanners follow-up)

Picked framework: **Ultrasound Scanners and Associated Options and Related
Services** (`ultrasound` speciality), 23.8% (5/21), Left 6 — the ledger's own
lowest-coverage-with-work-left pick.

## Confirms the same-day Renal Replacement Therapies finding, with more detail

`docs/framework-coverage-findings-2026-09-21-renal-replacement.md` (a parallel
run today) already checked this framework and moved on, finding no genuine
ultrasound-scanner product for any of the 6 remaining suppliers. This run
re-checked all 6 independently and reaches the same conclusion, with one
addition:

- **Philips, Siemens Healthineers** — crawl refused (site returns no
  readable catalogue); only currently-captured products are unrelated NHSSC
  items (Philips Respironics CPAP, Siemens Atellica/EPOC pathology
  analysers). No change possible without recrawling a recorded refusal,
  which the brief forbids.
- **Hologic UK** — 95 own-site held products, all genuinely non-ultrasound
  (Faxitron specimen radiography, Panther/Aptima molecular diagnostics,
  Selenia/3Dimensions mammography, NovaSure/MyoSure/Sonata gynae devices —
  Sonata is already correctly published under `womens:gyn`, not ultrasound,
  because it's a fibroid-ablation device that merely uses ultrasound
  guidance, not a diagnostic scanner). No genuine ultrasound scanner in the
  crawled range.
- **BioSpectrum Ltd** — 29 published products, all urology/gynaecology/
  ENT/general-surgery (endourology instruments). No ultrasound line.
- **ProSys International Ltd** — crawl refused (robots.txt); only captured
  product is an unrelated NHSSC stub (Secco needle-safety device).
- **Celtic SMR Ltd — NEW DETAIL.** The company's own site
  (celticsmr.co.uk) genuinely does sell human-healthcare diagnostic
  ultrasound scanners: `/products/healthcare/diagnostic-ultrasound/`
  describes "The SonoScape Diagnostic Ultrasound Range" and names six real
  models (E2, X3, E11, P25 Elite, P60, S80 Elite) — this is NOT the
  veterinary-only business the existing held record suggested. **Still does
  not publish**, for a structural reason, not a mapping one:
  - The site's sitemap exposes each of these as its own component-page URL
    under `.../diagnostic-ultrasound/page-components/product-pods/<slug>/`
    — a CMS artifact, not a product catalogue path — mixed in the SAME
    sitemap section as marketing/FAQ components (`who-are-celticsmr`,
    `calendly-form`, `frequently-asked-questions`, etc.).
  - Targeting the narrow `product-pods` segment alone yields only 7 URLs,
    below `crawl_supplier_site.py`'s `MIN_PRODUCTS` (8) floor, so it's
    refused as "too few to call a catalogue".
  - Targeting the wider `diagnostic-ultrasound` segment yields 14 URLs
    (enough to pass the floor) but the real scanner names and the CMS
    junk both land under the same `division: "Page Components"` value —
    and `differentiator-category-map.json` maps by `(supplier, division)`,
    never by product name, so mapping this division to `ultrasound:*`
    would publish "Calendly Form" and "Who Are We Celticsmr" as ultrasound
    scanner products. Tried, confirmed, reverted — not committed.
  - This is the `nav-labels-are-not-products` shape from
    `data/identity-vocabulary-policy.json`: "a capture whose entries are
    predominantly navigation is treated as a FAILED capture... held for
    recrawl, not discarded." No ruling needed; held is correct. A future
    fix needs a script capability this run doesn't have — either a
    per-product override route for a sitemap-only capture (the VWS/Nipro
    shape already logged at ^o551/^o570/^o573), or a smarter component-page
    filter that only follows `product-pods` leaves once named individually.
    Not attempted as a script change in this run — out of scope for a data
    batch.

**No data change made for this framework.** Coverage unchanged at 23.8%
(5/21).

## Moved to Minimally Invasive Surgery instead

Same shape repeats there (`Advanced Medical Solutions`, `W.L. Gore` already
flagged ^o562; `Healthcare 25 Ltd` already flagged ^o534; most of the
remaining 12 `publishedElsewhereNeedingCategory` suppliers are large
diversified manufacturers whose crawled range is real but genuinely not an
MIS product — Bolton Surgical's forceps/curettes, Reflex Medical's
defibrillation range, Starkstrom's theatre capital equipment, Kebomed's
nutrition device, B. Braun/Medline/Mölnlycke/Stryker all refused or
publishing an unrelated NHSSC stub).

**One genuinely new lead: Minitouch Ltd (domain).** Recorded 20/09/2026 as
"domain NOT recorded, refused... under the domain-proof-tier policy's
serviced-office guard" — the only address found for minitouch.eu
(1 Hutton Close, Bishop Auckland) is a mass company-formation registered
office shared by ~398 companies, so an address match there proves nothing.

This run found different evidence: minitouch.eu **itself hosts** a Modern
Slavery Statement and a Carbon Reduction Plan, both self-published, both
explicitly naming the organisation "Minitouch LTD" — a NAME
self-declaration by the site, not an address coincidence. Companies House
holds exactly one active company of that exact name (07933081).
`scripts/seed_supplier_domains.py --candidates-file ... --accept-name`
independently proved the same domain on its own weaker "site title" tier
(the homepage `<title>` reads "minitouch Outpatient Endometrial Ablation",
which contains the company name) — a second, tool-native confirmation on a
different signal from the same page. Recorded `www.minitouch.eu` as a
`Company website` link on the seed record, with both proof routes cited in
the source note (`--write`'s own output reformats the whole 6.4MB seed file
to one minified line — reverted; added the link and note by hand instead,
a 12-line diff, matching the format the Renal Replacement run used the same
day. Flagged as a script issue below).

Ran the real crawl once the domain was on record:
`crawl_supplier_site.py --supplier "Minitouch Ltd" --domain www.minitouch.eu`
— refused, cleanly: no WordPress API, no WooCommerce Store API, no sitemap.
The site is a single-page brochure for one product ("minitouch Outpatient
Endometrial Ablation", consistent with `mis:gynae`) with no product-listing
structure of any kind. **Coverage doesn't move** (still needs a source
before it can publish, same as VWS/^o551/^o570/^o573), but the supplier
moved from "no domain on record, no attempt possible" to "domain proved,
genuinely attempted, cleanly refused" — a real state change even without a
percentage change. A manual single-product entry was not attempted: the
pipeline's supplier-products.json capture format is provenance-tracked per
crawl, not for hand-entry.

**Script issue found, not fixed this run:** `seed_supplier_domains.py`'s
`--write` path (line ~1131) hardcodes `json.dump(..., separators=(",",
":"))`, writing the whole seed file as one minified line, on the stated
assumption "supplier-seed.json is stored minified on a single line." That
assumption is false today — the file is pretty-printed with `indent=2` (see
e.g. commit e5c2bb9 earlier the same day, a clean 34-line diff for the
Renal Replacement alias additions). Running `--write` turns a 12-line
intended change into a ~110,000-line diff that would bury the actual edit
in every future review. Not run to completion this time (reverted before
committing); a future run should either fix the hardcoded format or avoid
`--write` and hand-edit the `links` array as this run did.

## What did NOT move

- Ultrasound Scanners: 23.8% (5/21), unchanged — confirmed exhausted for
  today's permitted routes, matching the parallel Renal Replacement run's
  same-day finding.
- CT Scanners and Associated Options and Related Services: checked, same
  shape (Philips/Siemens Healthineers/Stryker refused or NHSSC-stub-only,
  no genuine CT scanner in range) — not worked further.
- Polymer Aprons: checked, sole remaining actionable supplier (GBUK Group)
  is a known pending identity-merge decision reserved for Lou (^o333,
  07/09/2026) — left untouched, not re-flagged.
