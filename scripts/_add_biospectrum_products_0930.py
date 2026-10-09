#!/usr/bin/env python3
"""One-off: fill BioSpectrum Ltd's empty seed `products` list (OUTSTANDING ^o290).

Approved by Lou in chat 30/09/2026. Source: the staged, page-by-page capture
02-Elevate-and-Thrive/Hub/Medical-Sales-Hub/proposed-data/
biospectrum-products-proposed-2026-09-29.json -- 19 products, each read from
its own page on www.bio-spectrum.co.uk on 29/09/2026 (HTTP 200, robots.txt
allows all). The same 19 names already sit in data/supplier-products.json
(own-site crawl, 06/09/2026) and 18 of them publish in differentiator.json,
but the seed record carried `products: []`, so the company card showed no
products at all.

Each string is "<name> (<division> -- what the product's own page says it
is)". A maker/brand name appears only where the product page names it. No
specialities are assigned here (gated vocabulary, separate decision).

The record already carries the domain (links[] "Website"
https://www.bio-spectrum.co.uk and deepDive.domain bio-spectrum.co.uk), so no
domain is added. Idempotent. Writes the seed back in its own byte format via
scripts/seed_format.py.

Run once from the repo root: python3 scripts/_add_biospectrum_products_0930.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like  # noqa: E402

SEED = "data/supplier-seed.json"
SUPPLIER = "BioSpectrum Ltd"

PRODUCTS = [
    "Marina Medical surgical instruments (ENT — Marina Medical range, distributed)",
    "Piezotome Solo M+ (ENT — ultrasonic bone surgery device)",
    "Bile Duct Exploration Accessories (General Surgery)",
    "Single Use Choledochoscopes Range (General Surgery — biliary endoscopy)",
    "Seegen 4-way ERCP scope (General Surgery — mother/baby scope)",
    "Simai Bipolar Plasma System (Gynaecology)",
    "Scivita Single Use Hysteroscopes (Gynaecology — flexible, semi-flexible and rigid)",
    "Urolon (Gynaecology — urethral bulking agent for urinary incontinence)",
    "ClearPetra Access Sheaths (Urology — continuous-flow lithotripsy with negative pressure aspiration)",
    "Ellick Bladder Evacuator (Urology — irrigation and tissue collection in transurethral surgery)",
    "Endourology Consumables (Urology — guidewires, stone retrieval baskets, ureteral stents)",
    "GBox Laser (Urology — TULA-compatible surgical laser)",
    "Simai Genius Morcellator (Urology — BPH enucleation)",
    "HoLEP Sets (Urology — instrument set for holmium laser enucleation of the prostate)",
    "Instrumentation (Urology — reusable German-made surgical instruments)",
    "Plasma Bipolar System (Urology — TURP and BPH enucleation)",
    "Polymer Ligation Clips (Urology — laparoscopic ligation clips and appliers)",
    "S Curve Dilators (Urology — urethral dilators)",
    "Single Use Ureteroscopes and Cystoscopes (Urology)",
]

NOTE_ADD = (" Products (19) added 30/09/2026 from BioSpectrum's own product pages on "
            "www.bio-spectrum.co.uk, each page read on 29/09/2026 (^o290); a maker is "
            "named only where the product page names it.")


def main():
    raw = open(SEED, "rb").read()
    seed = json.loads(raw)
    matches = [s for s in seed["suppliers"] if s.get("name") == SUPPLIER]
    if len(matches) != 1:
        sys.exit("expected exactly one %r record, found %d" % (SUPPLIER, len(matches)))
    rec = matches[0]
    assert len(PRODUCTS) == 19 and len(set(PRODUCTS)) == 19
    added = 0
    for p in PRODUCTS:
        if p not in rec["products"]:
            rec["products"].append(p)
            added += 1
    if NOTE_ADD.strip() not in rec.get("note", ""):
        rec["note"] = rec.get("note", "") + NOTE_ADD
    write_like(SEED, seed)
    print("%s: %d products added, %d on record" % (SUPPLIER, added, len(rec["products"])))


if __name__ == "__main__":
    main()
