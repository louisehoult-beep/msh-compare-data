#!/usr/bin/env python3
"""One-off seed: 9 product-override entries for Sovereign Medical -> ortho:brace.

Framework-coverage batch, 26/09/2026, Total Orthopaedic Solutions 3. Sovereign
Medical's crawl (data/supplier-products.json) came back as a single flat
"Uncategorised" division of 9 named products because sovereignmedical.co.uk's
Wix JSON-LD carries no category field. Every product name was checked against
the live product pages (two read directly: Madglove Assist, PRESSORELAX) and
against the homepage, which identifies the company as a UK orthopaedic-implant
and hand-surgery supplier. All 9 are bracing/cryotherapy/compression items,
matching ortho:brace's own vocabulary description exactly. See OUTSTANDING.md
for nothing — this one needed no ruling, just product-level reading.
"""
import json

MAP = "data/differentiator-category-map.json"
EVIDENCE = "the supplier's own site filing (sovereignmedical.co.uk), read by scripts/crawl_supplier_site.py; 2 product pages read directly on 26/09/2026 to confirm the category"

PRODUCTS = [
    ("ABDOBACK® Abdominal belt",
     "Post-operative abdominal support belt — bracing, matching ortho:brace's own description (Bracing, cryotherapy & compression)."),
    ("ABDOHIP® Abdominal belt",
     "Post-operative abdominal/hip support belt — bracing, matching ortho:brace's own description."),
    ("ANKLEFREEZ® Cryotherapy",
     "Ankle cryotherapy brace — matches ortho:brace's own description exactly."),
    ("HANDFREEZ® Cryotherapy wrist brace",
     "Wrist cryotherapy brace — matches ortho:brace's own description exactly."),
    ("KNEEFREEZ® Cryotherapy knee brace",
     "Knee cryotherapy brace — matches ortho:brace's own description exactly."),
    ("Madglove Assist",
     "Read on the live product page (sovereignmedical.co.uk/product-page/madglove-assist, checked 26/09/2026): a wrist/hand splint that stabilises the wrist and corrects hand position for rehabilitation — bracing, matching ortho:brace's own description."),
    ("Madglove Custom Kits",
     "Custom-fit kit for the Madglove Assist hand/wrist splint (same product line, confirmed on the live site) — bracing, same category as Madglove Assist."),
    ("PRESSORELAX®",
     "Read on the live product page (sovereignmedical.co.uk/product-page/pressorelax, checked 26/09/2026): combines cold therapy with pneumatic compression and a ligament knee brace for post-surgical/sports-injury knee recovery — cryotherapy and compression, matching ortho:brace's own description exactly."),
    ("SHOULDERFREEZ® Cryotherapy shoulder brace",
     "Shoulder cryotherapy brace — matches ortho:brace's own description exactly."),
]


def main():
    doc = json.load(open(MAP))
    existing = {(e.get("supplier"), e.get("division")) for e in doc["entries"]}
    added = 0
    for name, why in PRODUCTS:
        key = ("Sovereign Medical", name)
        if key in existing:
            print("SKIP (already present): %s" % name)
            continue
        doc["entries"].append({
            "kind": "product-override",
            "supplier": "Sovereign Medical",
            "division": name,
            "products": 1,
            "categories": [],
            "examples": [name],
            "hub": "ortho:brace",
            "notTaxonomy": False,
            "evidence": EVIDENCE,
            "why": why,
            "decidedIn": "_seed_sovereign_medical_ortho_brace_override_0926.py",
        })
        added += 1
    json.dump(doc, open(MAP, "w"), indent=1, ensure_ascii=False)
    print("Added %d product-override entries for Sovereign Medical -> ortho:brace" % added)


if __name__ == "__main__":
    main()
