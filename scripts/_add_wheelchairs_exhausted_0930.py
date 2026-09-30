#!/usr/bin/env python3
"""One-off, framework-coverage batch 30/09/2026.

Wheelchairs, Specialist Seating and Related Services checked at 32.3%
(10/31). All 6 Left items (5 publishedElsewhere + 1 heldOnly) checked and
none moves -- see the entry's own `reason` below for the per-supplier detail.
Recorded in docs/framework-coverage-exhausted.json so the routine does not
re-investigate it without new evidence (data/identity-vocabulary-policy.json
is not engaged here -- this is a "nothing left to crawl" finding, not an
identity/vocabulary ruling).

Run once: python3 scripts/_add_wheelchairs_exhausted_0930.py
"""
import json

PATH = "docs/framework-coverage-exhausted.json"

ENTRY = {
    "framework": "Wheelchairs, Specialist Seating and Related Services",
    "checkedOn": "2026-09-30",
    "coverageAtCheck": "32.3% (10/31)",
    "suppliersChecked": [
        "AM Healthcare Group", "BES Healthcare", "Otto Bock Healthcare PLC",
        "Blatchford Limited", "Peacocks Medical Group", "Aayan Medical Imaging Limited"
    ],
    "reason": (
        "All 6 Left items (5 publishedElsewhere + 1 heldOnly) checked and none moves. "
        "AM Healthcare Group's full captured range (Foot Ankle, Knee, Back, Neck, Wrist "
        "Hand, Elbow, Hip divisions, 28 products) is already mapped product-by-product to "
        "orthotics types (afo/brace/spine/upper) -- confirmed no wheelchair or seating item "
        "in the range. BES Healthcare's full captured range (Assistive Technology, Infection "
        "Prevention, Pressure Mapping, 122 products) is already mapped to orthotics:upper/"
        "brace, ssd:endo/cssd and monitoring:spec -- confirmed no wheelchair or seating item. "
        "Otto Bock Healthcare PLC's 429-code flat catalogue was worked under the mixed-"
        "division-mapping policy on 20/09/2026 (^o423 Policy 5 pass): 39 codes had readable "
        "detail and resolved to orthotics:prosth/afo/paed/brace/materials, the remaining 390 "
        "are bare SKU codes with no description and stay held under the vocabulary-gap guard "
        "(never map a bare SKU) -- none of the readable 39 is a wheelchair. Blatchford Limited "
        "and Peacocks Medical Group have no website crawl (both domains are recorded refused "
        "-- blatchfordmobility.com and peacocks.net, checked 31/08/2026, WordPress API 404/"
        "empty sitemap on both -- never re-crawled from this table per the hard rule) and "
        "their only captured products come via the NHS Supply Chain public catalogue route: "
        "Blatchford's 10 catalogue lines are all TurboMed Xtern drop-foot AFO exoskeletons "
        "(mapped orthotics:afo), Peacocks' 36 catalogue lines are all positioning aids "
        "(mapped handling:mattress) -- neither NHSSC catalogue slice contains a wheelchair "
        "or specialist seating line. Aayan Medical Imaging Limited was crawled in full "
        "(partialRead: false, 18 of 18 site-declared products captured, all filed by the "
        "company's own taxonomy under 'Medical Imaging') -- the company's own marketing "
        "copy mentions supplying 'MRI-safe products, patient trolleys, wheelchairs, and "
        "more' in passing, but carries no wheelchair or seating item as a catalogued "
        "product; there is nothing to add without inventing a product record the site does "
        "not carry."
    ),
    "wouldReopenIf": (
        "Any of AM Healthcare Group, BES Healthcare or Otto Bock Healthcare PLC's site "
        "crawl changes and adds a wheelchair/seating product; Blatchford Limited's or "
        "Peacocks Medical Group's site becomes readable, or either gets a new NHSSC "
        "catalogue line; Aayan Medical Imaging Limited's site adds a catalogued wheelchair "
        "product; or a new supplier is awarded on this framework."
    ),
}

doc = json.load(open(PATH))
names = {e.get("framework") for e in doc["frameworks"]}
if ENTRY["framework"] in names:
    raise SystemExit("already present, aborting: %r" % ENTRY["framework"])

doc["frameworks"].append(ENTRY)
with open(PATH, "w") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("added, total entries:", len(doc["frameworks"]))
