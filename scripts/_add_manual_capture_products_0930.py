#!/usr/bin/env python3
"""One-off: products from the manual public-page capture route onto three
EXISTING seed records (OUTSTANDING ^o625, ^o551, ^o601).

Route sanctioned by Lou 30/09/2026 (02-Elevate-and-Thrive/Process flows for all
brands/manual-product-capture-route.md). Source: the staged, page-by-page capture
02-Elevate-and-Thrive/Hub/Medical-Sales-Hub/proposed-data/
manual-capture-zeiss-electrospyres-hospitalinnovations-proposed-2026-09-30.json.
Every product was read from its own public page on the supplier's own site on
30/09/2026, robots.txt checked first and allowing the path:

  * Carl Zeiss Ltd (^o625): ZEISS INTRABEAM 600, read from
    zeiss.com/meditec/en/products/intraoperative-radiotherapy-systems.html in
    Chrome (curl/WebFetch get HTTP 403). robots.txt: Allow *.
  * Electro Spyres Healthcare Limited (^o551): the 8 cardiology products whose
    product-override mappings (^o488) already publish -- 5 UltraGel UG-50 packs,
    3 VitaTrode radiolucent ECG electrodes -- each page read in Chrome (the site
    is a JS-only app). robots.txt: Allow /.
  * Hospital Innovations (^o601): the 11 products that publish under ortho:equip,
    each page read by curl (HTTP 200). robots.txt: Disallow empty. The site
    names no division, so none is given.

Lavender Medical (^o601) is NOT touched: robots.txt refuses, held per rule 2.

Each string is "<name> (<division where the page names one> -- what the
product's own page says it is)". A maker is named only where the page names it
(Bodycad). No specialities are assigned here. Each record already carries its
website link, so no domain is added. Idempotent. Writes the seed back in its own
byte format via scripts/seed_format.py.

Run once from the repo root: python3 scripts/_add_manual_capture_products_0930.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like  # noqa: E402

SEED = "data/supplier-seed.json"

ADD = {
    "Carl Zeiss Ltd": (
        [
            "ZEISS INTRABEAM 600 (Intraoperative radiotherapy systems — IORT X-ray source with spherical, needle, flat and surface applicators)",
        ],
        " Product added 30/09/2026 from ZEISS's own INTRABEAM 600 page "
        "(zeiss.com/meditec/en/products/intraoperative-radiotherapy-systems.html), "
        "read on 30/09/2026 (^o625).",
    ),
    "Electro Spyres Healthcare Limited": (
        [
            "UltraGel™ UG-50 300ml Clear Bottle (Ultrasound — ultrasound gel, UG-50/300ML/CLR)",
            "UltraGel™ UG-50 5L Jerry Can (Ultrasound — ultrasound gel, UG-50/5L/CLR)",
            "UltraGel™ UG-50 5L Flexi Bag (Ultrasound — ultrasound gel, UG-50/5L/CLRBAG)",
            "UltraGel™ UG-50 5L Stand-Up Pouch (Ultrasound — ultrasound gel, UG-50/5L/STANDUP)",
            "UltraGel™ UG-50 25g Single-Use Sachet (Ultrasound — sterile single-use ultrasound gel, UG-50/25G/STERILE)",
            "VitaTrode™ Midi-ACF (36mm diameter) [Radiolucent] (ECG Electrodes — radiolucent foam/hydrogel, pack of 50)",
            "VitaTrode™ Maxi-ASF [Radiolucent] (ECG Electrodes — radiolucent foam/hydrogel, 40x32mm, pack of 50)",
            "VitaTrode™ Mini-GP [Radiolucent] (ECG Electrodes — radiolucent foam/hydrogel, 30x25mm paediatric, pack of 50)",
        ],
        " Products (8, cardiology range only) added 30/09/2026 from Electro Spyres's "
        "own product pages on electrospyres.com, each read on 30/09/2026 (^o551); "
        "the rest of its range is not listed here.",
    ),
    "Hospital Innovations": (
        [
            "Femoral Component Extractor (universal extraction system for total knee revision)",
            "CupX - Acetabular Cup Extraction System (acetabular cup extraction)",
            "Glenosphere Component Retractor (total and reverse shoulder arthroplasty)",
            "Stulberg Hip Positioner (patient positioning for total hip and revision surgery)",
            "Stulberg Leg Positioner (knee positioning during surgery)",
            "Fromm - Femur and Tibia Triangles (femur and tibia positioning for nailing, repairs and fractures)",
            "Tibial Wedge Clamp (tibial bone removal in unicondylar and total knee arthroplasty)",
            "Allograft Femoral and Humeral Heads (allograft for bone reconstruction and revision arthroplasty)",
            "Allograft HTO Wedges (allograft for opening-wedge high tibial osteotomy)",
            "Bodycad Fine Osteotomy™ (patient-specific osteotomy solution from Bodycad)",
            "Orthovise™ (gripping and extraction instrument for orthopaedic surgery)",
        ],
        " Products (11) added 30/09/2026 from Hospital Innovations's own product "
        "pages on www.hospitalinnovations.com, each read on 30/09/2026 (^o601); a "
        "maker is named only where the product page names it.",
    ),
}


def main():
    raw = open(SEED, "rb").read()
    seed = json.loads(raw)
    for name, (products, note_add) in ADD.items():
        matches = [s for s in seed["suppliers"] if s.get("name") == name]
        if len(matches) != 1:
            sys.exit("expected exactly one %r record, found %d" % (name, len(matches)))
        rec = matches[0]
        assert len(set(products)) == len(products)
        added = 0
        for p in products:
            if p not in rec["products"]:
                rec["products"].append(p)
                added += 1
        if note_add.strip() not in rec.get("note", ""):
            rec["note"] = rec.get("note", "") + note_add
        print("%s: %d products added, %d on record" % (name, added, len(rec["products"])))
    write_like(SEED, seed)


if __name__ == "__main__":
    main()
