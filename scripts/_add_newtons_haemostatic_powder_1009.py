"""One-off: map Newtons Medical Supplies Ltd's "BP Powder" haemostatic
powder (4 pack sizes) to gastro:haem.

Found while working the Endoscopy, Endourology and Oncology Ablation
Consumables framework (coverage batch, 09/10/2026). Newtons files 12
products under a supplier-named "Endoscopy" division, but most of them are
generic hospital consumables (chlorhexidine skin sachets, overshoes,
dignity shorts, cleaning brushes, sterilisation caps, waste bags) with no
genuine endoscopy-specific fit -- the division label is the supplier's own
department grouping, not evidence the product itself is an endoscopy
device (same caution as nav-labels-are-not-products, applied here to a
real-but-misleading division name rather than a taxonomy artefact). Only
"BP Powder - British Premium Haemostatic Powder" is unambiguous: an
endoscopic haemostatic powder spray, used during GI endoscopy to control
bleeding, matching gastro:haem (Haemostasis & banding) by its own name. The
other 8 products in the division stay held, correctly, as not evidenced to
be endoscopy-specific.

Run once, then delete.
"""
import json

PATH = "data/differentiator-category-map.json"

SUPPLIER = "Newtons Medical Supplies Ltd"
HUB = "gastro:haem"
WHY = ("Endoscopic haemostatic powder spray, used during GI endoscopy to "
       "control bleeding -- \"Haemostatic\" is in the product's own name, "
       "matching gastro:haem (Haemostasis & banding). Filed by the supplier "
       "under its own \"Endoscopy\" division, but that division label is "
       "not itself evidence for the other 8 products in it (chlorhexidine "
       "sachets, overshoes, dignity shorts, cleaning brush, sterilisation "
       "cap, waste bags), which stay held.")
NAMES = [
    "BP Powder – British Premium Haemostatic Powder – Box of 5g",
    "BP Powder – British Premium Haemostatic Powder – Box of 3g",
    "BP Powder – British Premium Haemostatic Powder – Box of 2g",
    "BP Powder – British Premium Haemostatic Powder – Box of 1g",
]


def main():
    d = json.load(open(PATH))
    entries = d["entries"]
    added = 0
    for name in NAMES:
        entries.append({
            "kind": "product-override",
            "supplier": SUPPLIER,
            "division": name,
            "products": 1,
            "categories": [],
            "examples": [name],
            "hub": HUB,
            "notTaxonomy": False,
            "evidence": "the supplier's own site filing, read by scripts/crawl_supplier_site.py",
            "why": WHY,
            "decidedIn": "_add_newtons_haemostatic_powder_1009.py",
        })
        added += 1
    d["entries"] = entries
    json.dump(d, open(PATH, "w"), indent=1, ensure_ascii=False)
    print("added", added, "product-overrides")


if __name__ == "__main__":
    main()
