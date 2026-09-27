"""One-off: map Ideal Medical Solutions' one unambiguous wound-care product
out of its flat "Uncategorised" division (41 products, mostly surgical
staplers/mesh/energy systems/dermatomes -- correctly held under the
mixed-division-mapping policy, data/identity-vocabulary-policy.json).
Framework-coverage batch, 27/09/2026.

Melloxy Chronic Wound Gel is a named, dedicated chronic-wound antibacterial
honey/ozonated-oil gel (confirmed via the manufacturer's own product line and
independent wound-care retailers, e.g. woundcarehandbook.com and
wound-care.co.uk, read 27/09/2026) -> wound:adv (Advanced dressings).
"4DryField" (a surgical adhesion-barrier/hemostat for gynaecological/general
surgery, not applied to chronic wounds) and "Matriderm" (a dermal-matrix
implant used during surgical grafting, not a dressing) were checked and left
held -- neither is unambiguous enough by name alone for this framework's
existing wound:* types, and neither has a precedent among the Hub's ~700
published wound:adv items, which are all conventional dressings.

Per-product source captured this run by scripts/crawl_supplier_product_detail.py.

Run once, then delete.
"""
import json

PATH = "data/differentiator-category-map.json"

ENTRY = {
    "kind": "product-override",
    "supplier": "Ideal Medical Solutions",
    "division": "Melloxy Chronic Wound Gel",
    "products": 1,
    "categories": [],
    "examples": ["Melloxy Chronic Wound Gel"],
    "hub": "wound:adv",
    "notTaxonomy": False,
    "evidence": "the supplier's own site filing (ideal-ms.com), read by "
                "scripts/crawl_supplier_site.py; product detail page "
                "captured 27/09/2026 by "
                "scripts/crawl_supplier_product_detail.py",
    "why": "Melloxy is a named chronic-wound antibacterial honey/ozonated-"
           "oil gel, indicated for chronic and acute wounds, ulcers and "
           "burns -- wound:adv (Advanced dressings), by name alone.",
    "decidedIn": "_seed_ideal_ms_melloxy_override_0927.py",
}


def main():
    d = json.load(open(PATH))
    entries = d["entries"]
    key = (ENTRY["supplier"], ENTRY["division"])
    if any((e.get("supplier"), e.get("division")) == key for e in entries):
        print("SKIP already present:", key)
        return
    entries.append(ENTRY)
    json.dump(d, open(PATH, "w"), indent=1, ensure_ascii=False)
    print("added 1 product-override entry")


if __name__ == "__main__":
    main()
