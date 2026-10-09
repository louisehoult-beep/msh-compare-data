"""One-off, 28/09/2026: stop Pentland Medical's Otiom dementia-monitoring devices
publishing as First Aid.

Pentland's site files all nine of its products in one WooCommerce category,
"Medical Supplies" (product_cat-medical-supplies on every page, read live
28/09/2026): the Hema-T Combat Arterial Tourniquet and eight Otiom items. The
division was mapped to BOTH digital:tec and wound:fa (map part
Pentland-Medical-Ltd--sprint-0831-surgical.json), and a multi-category division
publishes EVERY product in EVERY listed category — so each Otiom tag, home base,
charger and kit was also a wound:fa First Aid product, and the tourniquet was
also a telecare device.

The page for each product says what it is: "OTIOM – Monitoring Device for People
With Dementia – For Private Homes" (h1, pentlandmedical.co.uk, 28/09/2026) and
the tag / home base / charger / kits are that system's parts; "Hema-T™ Combat
Arterial Tourniquet" is first aid. So the division becomes wound:fa and the
eight Otiom products take digital:tec by product-override (the division's own
evidence cannot split them — one site category holds both).

Run once from the repo root, then rebuild the Differentiator.
"""
import json

MAP = "data/differentiator-category-map.json"
PART = "data/differentiator-map-parts/Pentland-Medical-Ltd--sprint-0831-surgical.json"
CO = "Pentland Medical Ltd"
DIV = "Medical Supplies"
DIV_WHY = ("the division's one non-Otiom product, the Hema-T Combat Arterial Tourniquet, "
           "is first aid; the eight Otiom dementia-monitoring products in the same site "
           "category take digital:tec by product-override (28/09/2026)")
OTIOM = [
    "OTIOM – Monitoring Device for People With Dementia – For Private Homes",
    "Additional Otiom Tag",
    "Additional Otiom Home Base",
    "Additional Otiom Charger",
    "Otiom Wireless Charger",
    "Starter Kit (containing 1 x Otiom Tag; 2 x Otiom Homebase; 1 x Otiom Charger)",
    "Large Kit (containing 1 x Otiom Tag; 3 x Otiom Homebase; 1 x Otiom Charger)",
    "Extra-Large Kit (containing 1 x Otiom Tag; 4 x Otiom Homebase; 1 x Otiom Charger)",
]


def write(path, doc, newline=True):
    with open(path, "w") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + ("\n" if newline else ""))


def main():
    doc = json.load(open(MAP))
    entries = doc["entries"]
    div = [e for e in entries if e.get("supplier") == CO and e.get("division") == DIV
           and e.get("kind") not in ("nhssc-term", "product-override")]
    assert len(div) == 1, div
    div[0]["hub"] = "wound:fa"
    div[0]["why"] = DIV_WHY
    have = {(e.get("supplier"), e.get("division")) for e in entries
            if e.get("kind") == "product-override"}
    added = 0
    for name in OTIOM:
        if (CO, name) in have:
            continue
        entries.append({
            "kind": "product-override",
            "supplier": CO,
            "division": name,
            "products": 1,
            "categories": ["Medical Supplies"],
            "examples": [name],
            "hub": "digital:tec",
            "notTaxonomy": False,
            "evidence": "the product's own page on pentlandmedical.co.uk, read 28/09/2026: "
                        "the Otiom system is a GPS monitoring device for people with dementia "
                        "(tag, home bases, charger); the site files it in one 'Medical "
                        "Supplies' category with a tourniquet",
            "why": "an Otiom tag, home base, charger or kit is part of a dementia wander-"
                   "monitoring system — technology-enabled care, not first aid",
            "decidedIn": "_seed_pentland_otiom_tec_override_0928.py",
        })
        added += 1
    doc["counts"]["mapped"] = sum(1 for e in entries if e.get("hub"))
    write(MAP, doc)

    part = json.load(open(PART))
    for dcs in part["decisions"]:
        if dcs["division"] == DIV:
            dcs["hub"] = "wound:fa"
            dcs["why"] = DIV_WHY
    write(PART, part, newline=False)
    print("division -> wound:fa; %d Otiom product-override(s) added" % added)


if __name__ == "__main__":
    main()
