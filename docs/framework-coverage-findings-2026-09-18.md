# Framework coverage batch — 18/09/2026 findings

Picked framework: **Examination Gloves** (21.1% coverage, 9 left going in), after two
higher-priority skips explained below.

## Skipped: Insulin Pumps, CGM & HCL (16.7%, the ledger's top pick)

All three remaining suppliers (Abbott Laboratories Limited, Medtronic, Urathon Europe Ltd)
turned out to already be fully investigated and queued — `identity-vocab-decision-queue.md`
entry #8 and OUTSTANDING `^o527` were both added earlier today, before this run started,
documenting the same three parent/division identity questions this run independently
re-confirmed:

- Abbott's captured products are entirely NHSSC nutrition-line data (Ensure range); Abbott's
  own site (abbott.co.uk) is recorded refused 31/08/2026. No route to the FreeStyle Libre/CGM
  range under this seed record without a ruling on which Abbott entity contracts the award.
- Medtronic's captured products are entirely NHSSC theatres/vascular/cardiology data; their
  own site (medtronic.com) is recorded refused 08/09/2026. Same shape as Abbott — no route to
  the MiniMed pump range under this seed record without a ruling.
- Urathon Europe Ltd was crawled fresh 15/09/2026 (104 products, 5 divisions: Bathing/
  Showering/Toilet Aids, Around The Home, Mobility Aids, Moving & Handling, Bedroom Aids) —
  no CGM item appears anywhere in the crawlable catalogue. Their claimed Yuwell Anytime CGM
  distribution is real (per the seed record's own evidence) but is not on a page the crawler
  can reach, matching `^o524`'s existing note about a durable manual-product mechanism.

Since every actionable supplier here needs a decision already sitting on the queue, and none
of it is crawl or mapping work, this run added a `data/coverage-deferrals.json` entry for the
framework (same mechanism as Radiotherapy Ancillary Devices) so the picker stops re-selecting
it. Coverage and Left are untouched — this only removes it from the pick list until Lou rules
on entry #8.

## Skipped: Digital Diagnostic Solutions (18.5%)

Checked before picking Examination Gloves. All 8 remaining suppliers (Draeger, Haemonetics,
Olympus/KeyMed, Leica Microsystems, Philips, Roche Diagnostics, Siemens Healthineers, Sysmex
UK) already carry recorded, dated refusals (robots.txt blocks, non-resolving domains, no
readable product API) from 20/08–31/08/2026 — this is the exact framework named in the brief's
warning about the 06/09/2026 incident where 34 already-refused suppliers were wrongly
re-crawled. `actionable.crawlable` and `actionable.needDomain` are both 0 — there is no
permitted route left on this framework right now. Not deferred (nothing here needs a ruling
from Lou, it's simply exhausted for now), just left alone.

## Worked: Examination Gloves

Priority-order work through the framework's actionable suppliers:

- **Globus (Shetland) Ltd** (held, 881 products) — already flagged `^o521` (17/09): 848 of 881
  are an unstructured "Uncategorised" sitemap-slug list, and the 15-item "Hand Protection"
  division turns out on inspection to be sub-category labels ("Surgical Gloves", "Single Use",
  "Chemical Protection", "Vending Gloves"...), not real product names — mapping any of them to
  infection:latex/nitrile/vinyl would publish fake "products". Confirmed the existing flag is
  correct; did not force a mapping.
- **Ergea UK and Ireland Limited (Althea UK and Ireland Limited)** (need domain) — already
  flagged `^o522` (17/09) as needing a human identity check before any domain is seeded. This
  run initially added ergeagroup.com and ran a crawl (0 products — the site is Managed
  Equipment Services, no product catalogue) before noticing the existing flag; **reverted**
  both the seeded link and the resulting refusal record so the framework is exactly as it was
  for this supplier, respecting the pending human check.
- **Cargo Services Far East Limited** (need domain) — confirmed via the company's own site
  (cargofe.com, page title "Cargo Services Far East", matching the framework-awarded name
  exactly) as a Hong Kong-headquartered freight forwarder. Seeded the domain and ran the
  crawler: refused (no product post type, no WooCommerce catalogue — a freight forwarder's
  site, as expected). Converts this supplier from blocked ("need domain") to a properly
  documented dead end.
- **Medicom Healthpro Ltd** (need domain) — identity confirmed (CH 12650877, active, SIC 32500
  "Manufacture of medical and dental instruments and supplies", UK subsidiary of the global
  Medicom Group per multiple independent business directories) but no distinct operating
  domain could be confirmed. medicom.com is the Medicom Group's global corporate site and does
  not name "Medicom Healthpro Ltd" anywhere found; treating it as this subsidiary's own site
  would be exactly the kind of identity chain rule 10 warns against. Left unresolved — see
  OUTSTANDING.
- **ORN International T/A Spectra Corporate** (need domain) — the literal trading name on the
  NHS Supply Chain brief is "Spectra Corporate"; spectracorporate.com/.co.uk no longer resolve
  (DNS failure, checked 18/09/2026). The parent entity ORN (INT) LIMITED (CH 07254574) trades
  as ØRN International at shop.ornworkwear.com / orn-int.com, and third-party resellers
  (bksafetywear.co.uk, misteruniform.co.uk) sell "ORN" branded gloves, but nothing found ties
  the specific "Spectra Corporate" trading name used in the NHS award to that site. Left
  unresolved — see OUTSTANDING.

No differentiator/coverage change from this framework this run (the one supplier resolved,
Cargo Services Far East, came back refused). The genuine progress is: one supplier moved from
blocked to a documented dead end, two domain-identity questions raised as fresh judgement
calls, and one already-exhausted framework (Insulin Pumps) taken out of the picker's rotation
so it stops being reselected for no movement.
