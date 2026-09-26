"""One-off: add product-override entries for Organon UK's 4 unambiguous
women's-health products, found sitting in its flat 'Uncategorised' division
alongside a general pharma portfolio (statins, asthma, Parkinson's,
antidepressant, biosimilars) that is correctly held per the mixed-division-
mapping policy (data/identity-vocabulary-policy.json). These 4 are
unambiguous by product name/description alone, with no inference from the
rest of Organon's catalogue:
  - MIUDELLA (copper intrauterine system) -> womens:sex (contraceptive IUD)
  - XACIATO (clindamycin phosphate) vaginal gel -> womens:gyn (treats BV,
    a gynaecological condition; not itself a contraceptive)
  - NuvaRing (etonogestrel/ethinyl estradiol vaginal ring) -> womens:sex
    (combined hormonal contraceptive)
  - NEXPLANON (etonogestrel implant) -> womens:sex (contraceptive implant;
    etonogestrel has no other approved indication)
Framework-coverage batch, 26/09/2026. Per-product detail pages captured this
run (scripts/crawl_supplier_product_detail.py) so each has a manufacturer
source; run once, then delete.
"""
import json

PATH = "data/differentiator-category-map.json"

ENTRIES = [
    {
        "kind": "product-override",
        "supplier": "Organon UK",
        "division": "MIUDELLA® (copper intrauterine system)",
        "products": 1,
        "categories": [],
        "examples": ["MIUDELLA® (copper intrauterine system)"],
        "hub": "womens:sex",
        "notTaxonomy": False,
        "evidence": "the supplier's own site filing (organon.com), read by "
                    "scripts/crawl_supplier_site.py; product detail page "
                    "captured 26/09/2026 by "
                    "scripts/crawl_supplier_product_detail.py",
        "why": "A copper intrauterine system is a contraceptive device by "
               "name alone — womens:sex (Sexual health & contraception).",
        "decidedIn": "_seed_organon_womens_override_0926.py",
    },
    {
        "kind": "product-override",
        "supplier": "Organon UK",
        "division": "XACIATO® (clindamycin phosphate) vaginal gel",
        "products": 1,
        "categories": [],
        "examples": ["XACIATO® (clindamycin phosphate) vaginal gel"],
        "hub": "womens:gyn",
        "notTaxonomy": False,
        "evidence": "the supplier's own site filing (organon.com), read by "
                    "scripts/crawl_supplier_site.py; product detail page "
                    "captured 26/09/2026 by "
                    "scripts/crawl_supplier_product_detail.py",
        "why": "A vaginal gel treating bacterial vaginosis is a "
               "gynaecological product by name alone — womens:gyn "
               "(Gynaecology & examination), not a contraceptive.",
        "decidedIn": "_seed_organon_womens_override_0926.py",
    },
    {
        "kind": "product-override",
        "supplier": "Organon UK",
        "division": "NuvaRing® (etonogestrel/ethinyl estradiol vaginal ring)",
        "products": 1,
        "categories": [],
        "examples": ["NuvaRing® (etonogestrel/ethinyl estradiol vaginal ring)"],
        "hub": "womens:sex",
        "notTaxonomy": False,
        "evidence": "the supplier's own site filing (organon.com), read by "
                    "scripts/crawl_supplier_site.py; product detail page "
                    "captured 26/09/2026 by "
                    "scripts/crawl_supplier_product_detail.py",
        "why": "A combined hormonal vaginal ring is a contraceptive by name "
               "alone — womens:sex (Sexual health & contraception).",
        "decidedIn": "_seed_organon_womens_override_0926.py",
    },
    {
        "kind": "product-override",
        "supplier": "Organon UK",
        "division": "NEXPLANON® (etonogestrel implant) Radiopaque Subdermal Use Only",
        "products": 1,
        "categories": [],
        "examples": ["NEXPLANON® (etonogestrel implant) Radiopaque Subdermal Use Only"],
        "hub": "womens:sex",
        "notTaxonomy": False,
        "evidence": "the supplier's own site filing (organon.com), read by "
                    "scripts/crawl_supplier_site.py; product detail page "
                    "captured 26/09/2026 by "
                    "scripts/crawl_supplier_product_detail.py",
        "why": "Etonogestrel subdermal implants have no approved indication "
               "other than contraception — womens:sex (Sexual health & "
               "contraception).",
        "decidedIn": "_seed_organon_womens_override_0926.py",
    },
]


def main():
    d = json.load(open(PATH))
    existing = {(e.get("supplier"), e.get("division")) for e in d["entries"]}
    added = 0
    for e in ENTRIES:
        key = (e["supplier"], e["division"])
        if key in existing:
            print("SKIP already present:", key)
            continue
        d["entries"].append(e)
        added += 1
    json.dump(d, open(PATH, "w"), indent=1, ensure_ascii=False)
    print("added", added, "entries")


if __name__ == "__main__":
    main()
