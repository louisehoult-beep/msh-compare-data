#!/usr/bin/env python3
"""One-off, 27/11/2026: hold four ranges the 24/11 capture published against
data/identity-vocabulary-policy.json. Nothing is discarded: the full captured
records go to ops/held-captures/ and stay in git history (commit f7f47dff).

Run once:  python3 scripts/_hold_supplier_ranges_1127.py ADLER_LISTINGS.json
ADLER_LISTINGS.json maps each captured Adler name to the NHS Supply Chain card
read for ADLER ORTHO UK LTD on 27/11/2026, or null.
"""
import collections
import json
import os
import sys

from crawl_supplier_site import atomic_write_json

PATH = "data/supplier-products.json"
HELD = "ops/held-captures/supplier-ranges-2026-11-27.json"
DAY = "2026-11-27"
ADLER = "Adler Ortho UK Limited"

HOLDS = {
    "EUROIMMUN UK": (
        "no-parent-catalogue-credit-to-uk-subsidiary; nav-labels-are-not-products",
        "27/11/2026: euroimmun.co.uk redirects to the German parent's worldwide site euroimmun.com, "
        "whose subsidiaries page lists EUROIMMUN UK Ltd; its imprint reserves text and data mining "
        "rights. No NHS Supply Chain catalogue card found for the UK entity. Many captured entries "
        "are disease or technique page names."),
    ADLER: (
        "no-parent-catalogue-credit-to-uk-subsidiary",
        "27/11/2026: adlerortho.com is the parent's worldwide site (ADLER ORTHO UK listed on its "
        "contact page). Only the captured ranges NHS Supply Chain's catalogue lists for ADLER ORTHO "
        "UK LTD are published; the rest are held."),
    "Axonics Modulation Technologies UK Limited": (
        "no-parent-catalogue-credit-to-uk-subsidiary; nav-labels-are-not-products",
        "27/11/2026: captured from bostonscientific.com (axonics.com redirects there), Boston "
        "Scientific's worldwide catalogue, including navigation pages. NHS Supply Chain lists the "
        "Axonics lines under BOSTON SCIENTIFIC LTD, not AXONICS MODULATION TECHNOLOGIES, U.K. "
        "LIMITED (09622653); no card found under the UK entity."),
    "Eckert & Ziegler BEBIG": (
        "dissolved-awardee-successor-uncertain",
        "18/08/2026, re-read 27/11/2026: ECKERT & ZIEGLER BEBIG LIMITED (05270457) was dissolved "
        "05/03/2024 (Companies House). www.ezag.com is the German group's site and nothing read "
        "confirms it as a successor to this entity. No NHS Supply Chain catalogue card found."),
}


def main():
    listings = json.load(open(sys.argv[1], encoding="utf-8"))
    doc = json.load(open(PATH, encoding="utf-8"))
    suppliers = doc["suppliers"]
    held = {"note": "Captures held out of member view on 27/11/2026. No app reads this file. "
                    "To restore one, a document the named policy accepts is needed first; then "
                    "remove its _meta.holds entry in data/supplier-products.json.",
            "source": "data/supplier-products.json, captured 2026-11-24 (commit f7f47dff)",
            "suppliers": {n: suppliers[n] for n in HOLDS}}
    os.makedirs(os.path.dirname(HELD), exist_ok=True)
    atomic_write_json(HELD, held)

    holds = doc["_meta"].setdefault("holds", {})
    for name, (policy, reason) in HOLDS.items():
        rec = suppliers[name]
        holds[name] = {"heldOn": DAY, "policy": policy, "capture": HELD}
        doc["_meta"]["refusedOnReading"][name] = reason
        if name != ADLER:
            del suppliers[name]
            doc["refusals"][name] = {"domain": rec["domain"], "reason": reason, "checked": DAY}
            print("%s: %d removed" % (name, len(rec["products"])))
            continue
        if set(listings) != {p["n"] for p in rec["products"]}:
            sys.exit("listings file does not match the captured Adler names")
        keep = [dict(p, nhsscListing={"npc": listings[p["n"]]["npc"], "checked": DAY})
                for p in rec["products"] if listings[p["n"]]]
        holds[name]["publishable"] = [p["n"] for p in keep]
        note = ("Only the ranges NHS Supply Chain's catalogue lists for ADLER ORTHO UK LTD (read "
                "27/11/2026) are shown, named as on adlerortho.com, the parent company's site. "
                "This is not the company's full range.")
        counts = collections.Counter(p["division"] for p in keep)
        print("%s: %d removed, %d kept" % (name, len(rec["products"]) - len(keep), len(keep)))
        suppliers[name] = dict(
            rec, products=keep, captureCaveat=note, filingRule=note, structure=note,
            source="adlerortho.com names, limited to NHS Supply Chain listings for ADLER ORTHO UK LTD",
            divisions=[{"name": d, "products": c} for d, c in counts.items()])
    atomic_write_json(PATH, doc)


if __name__ == "__main__":
    main()
