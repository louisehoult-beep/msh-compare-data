# Framework coverage findings - Operating Theatres Equipment, 20/09/2026

Run: `differentiator-framework-coverage`, picked **Operating Theatres Equipment and Related
Accessories and Services** (`theatres`), 23.3% coverage, 10/43 published, 16 left before this
run. Picked over the nominal lowest-coverage frameworks because Infusion Pumps (22.2%) and
Minimally Invasive Surgery (23.3%) were both already worked to their structural ceiling earlier
today (see `framework-coverage-findings-2026-09-20-infusion-pumps.md` and today's `c39040a`
commit) with no further permitted route, and Infant Feeding's 4 remaining items are the
already-flagged Babease/Nutricia identity gaps (^o559, ^o560).

## What was checked and done

- **Howard Wright Europe** (`heldNeedingCategory`, 1 of 16): crawled 25/08/2026, held as a flat
  10-product "Uncategorised" range (the site's sitemap carries no division structure, so every
  product name is a URL slug: S24, M9 Bed, M8 Bed, M7 Examination Couch, Pacific Shower Bathing
  Trolley, Prema Compact/Ward/Stretcher Mattress, M9 Stretcher Trolley, M10 Bed). Each product's
  own name is unambiguous evidence of its type, the same basis already used for Anetic Aid Ltd,
  Medalin Limited, Sectra Limited, Tristel Solutions Limited and Sense Medical Limited elsewhere
  in `data/differentiator-category-map.json`. Confirmed S24 on howardwright.com/s24: an electric
  stretcher/trolley (Trauma and Transfer configurations). Added 10 `product-override` entries:
  - `handling:bed`, products M8 Bed, M9 Bed, M10 Bed
  - `handling:mattress`, products Prema Compact Mattress, Prema Ward Mattress, Prema Stretcher
    Mattress
  - `handling:furniture`, products S24, M7 Examination Couch, M9 Stretcher Trolley, Pacific
    Shower Bathing Trolley

  Howard Wright Europe is awarded on Pressure Area Care and Patient Handling (2025/S 000-086469)
  as well as this framework. None of these products read as operating-theatres equipment
  (`theatres:capital/electro/perfusion/theatre/warm`), so this move does not publish Howard
  Wright into the Operating Theatres framework: it correctly reclassifies it as
  `publishedElsewhereNeedingCategory` there and, separately, moves it to published on Pressure
  Area Care and Patient Handling (25 pub to 26 pub on that framework, confirmed by re-running
  the ledger).

- **Ferno (UK) Limited** (`needDomain`, 1 of 16): found the company's own website,
  ferno.com/uk (UK section of the global Ferno Corporation site; the seed record's existing
  Companies House candidate, 01007475, is at the same Cleckheaton address the site's contact
  page gives). Added the link to `data/supplier-seed.json`. Crawled it: refused, correctly.
  Independently confirmed by reading `https://ferno.com/sitemap` by hand (the URL robots.txt
  actually points to; `/sitemap.xml` 404s): it lists only category/collection pages
  (`/uk/ems/patient-handling/ambulance-cots`, `/uk/rescue/litters-stretchers`, etc.), never an
  individual named product. There is no product-level catalogue on this site to read, not a
  missing domain, so it is now recorded as a genuine, evidenced refusal rather than left as an
  unresolved gap.

- **Lynton Lasers** (`needDomain`, 1 of 16): found the company's own website, lynton.co.uk
  (UK laser/IPL aesthetic-equipment manufacturer, Holmes Chapel, Cheshire, matching the seed
  record's registered-office note). Added the link to `data/supplier-seed.json`. Crawled it:
  refused, robots.txt disallows automated reading. Recorded as a genuine refusal.

- **Ingles Ltd** (`needDomain`, 1 of 16): could not confirm a company or website. A web search
  for "Ingles Ltd" in an endoscopy/surgical/theatres context returns nothing usable; the only
  Companies House hit under a similar name is Ingles Medical Limited (Bicester), with no
  evidence tying it to either of the two frameworks (Operating Theatres, Endoscopy, Endourology
  and Oncology Ablation Consumables) it is awarded on. This is the same dead end already on
  record: `OUTSTANDING.md` ^o525 (17/09/2026) flags exactly this gap. No new item added; this
  run independently reconfirms ^o525 rather than duplicating it.

- **12 `publishedElsewhere` suppliers**: not re-checked individually this run (time budget);
  left for a future pass. None were touched.

## Net result

Real movement on this framework: `heldNeedingCategory` 1 to 0, `needDomain` 3 to 1 (Ferno and
Lynton Lasers moved into `refused`, evidenced; Ingles Ltd remains genuinely unresolved).
`suppliersPublished` on Operating Theatres itself is unchanged at 10/43 (23.3%): none of this
run's work produced a theatres-category product, which is the honest outcome given what was
actually found, not a miss. Pressure Area Care and Patient Handling gained one supplier (25 to
26 published, coverage rose in step) as a side effect of the Howard Wright mapping.

## Before / after (Operating Theatres)

- Before: 23.3% (10/43 published), 16 left.
- After: 23.3% (10/43 published), 14 left (2 items resolved to evidenced refusals, 1 category
  gap closed, 1 item, Ingles Ltd, left open on OUTSTANDING.md).
