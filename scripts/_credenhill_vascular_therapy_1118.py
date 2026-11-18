#!/usr/bin/env python3
"""Attach Vascular Therapy and Associated Products to the Credenhill record.

WHY THIS WAS A GAP, NOT AN OVERSIGHT
------------------------------------
data/framework-lots.json already resolves the brief row "Daylong Direct
(Credenhill)" to "Credenhill Ltd (trading as Daylong Direct)" and holds its
Lots 4, 5 and 10. Twenty of the framework's 23 brief rows carry a matching
`frameworks` entry on their own record; two more are deliberately unmatched
("Gardamed Limited (Barcelcom SA)" and "crxcompression.com" reach no Hub
record). Credenhill was the ONLY confirmed row whose record did not carry the
framework, so the lot showed but the record did not say why.

An earlier handover said this was "left to the nightly job on purpose". That is
wrong: scripts/backfill_seed_from_frameworks.py only ADDS records for companies
held in no Hub section, so it skips Credenhill by design, and no workflow calls
it at all. It would never have happened on its own.

WHAT THIS ASSERTS, AND ON WHAT EVIDENCE
---------------------------------------
Exactly what its 20 siblings assert, in the same shape: this company is named on
this framework's own NHS Supply Chain contract launch brief, and its lots come
from the Find a Tender contract award notice because the brief publishes no
per-supplier lot breakdown.

The award notice was read AT SOURCE on 18/11/2026 (Lou's standing rule: never
state a company is on a framework or lot without a same-day check of the notice
itself). Notice 2023/S 000-032322, OCID ocds-h6vhtk-03c513, published
1 November 2023, NHS Supply Chain, 10 lots awarded 2 October 2023. "Daylong
Direct" appears as a contractor on Lot 4 (Graduated Compression Hosiery and
Accessories), Lot 5 (Upper & Lower Limb Compression Garments and Accessories)
and Lot 10 (Compression Garment Applicators Reusable) — the three lots
framework-lots.json already held, confirmed one by one against the OCDS award
release rather than taken from it. Record:
~/.claude/framework-claims/032322-2023-2026-11-18.json.

The notice names the trading name "Daylong Direct" with no company number. The
link to Credenhill Ltd is the Hub's own recorded alias, not an inference made
here; the record already carries "Daylong Direct" and "Daylong Direct
(Credenhill)" among its aliases, which is how company_match resolves it
'confirmed'. No company number is asserted, and none is changed.

Re-running writes nothing.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import seed_format

RECORD = "Credenhill Ltd (trading as Daylong Direct)"
FRAMEWORK = "Vascular Therapy and Associated Products"

ENTRY = {
    "name": FRAMEWORK,
    "dates": "28 February 2024 to 27 February 2028",
    "note": (
        "Named on NHS Supply Chain's own contract launch brief for this "
        "framework, as \"Daylong Direct (Credenhill)\". 23 suppliers on the "
        "framework. Lot 4, Lot 5 and Lot 10 per Find a Tender contract award "
        "notice 032322-2023 (the contract launch brief itself publishes no "
        "per-supplier lot breakdown), where the awarded contractor is named by "
        "the trading name \"Daylong Direct\" with no company number; the link "
        "to Credenhill Ltd is this record's own recorded alias. Lot source read "
        "2026-11-18."
    ),
    "reference": "2023/S 000-012286",
    "category": "Rehabilitation and Community",
    "supplierCount": 23,
    "url": "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/vascular-therapy-and-associated-products/",
    "source": "nhssc-brief",
    "capturedOn": "2026-11-15",
    "lotSourceUrl": "https://www.find-tender.service.gov.uk/Notice/032322-2023",
}


def apply(path):
    with open(path) as fh:
        doc = json.load(fh)
    touched = 0
    for rec in doc["suppliers"]:
        if rec.get("name") != RECORD:
            continue
        names = [f.get("name") for f in rec.get("frameworks", [])]
        if FRAMEWORK in names:
            print("  %s: already carries %r, nothing written"
                  % (os.path.basename(path), FRAMEWORK))
            return 0
        rec.setdefault("frameworks", []).append(dict(ENTRY))
        touched += 1
    if not touched:
        raise SystemExit("record %r not found in %s" % (RECORD, path))
    fmt, round_trips = seed_format.write_like(path, doc)
    print(" ", seed_format.describe(path, fmt, round_trips))
    return touched


def main():
    total = 0
    for name in ("supplier-seed.json", "supplier-index.json"):
        total += apply(os.path.join(ROOT, "data", name))
    print("\n%d record(s) gained %r." % (total, FRAMEWORK))
    if total:
        print("Now: bash scripts/gate.sh")


if __name__ == "__main__":
    main()
