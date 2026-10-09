"""One-off: map Griffiths and Nielsen Ltd's genuine wound-care range into
Advanced Wound Care. Framework-coverage batch, 27/09/2026.

Griffiths and Nielsen Ltd is awarded on Advanced Wound Care but sat entirely
in publishedElsewhereNeedingCategory (its captured range publishes under
other frameworks' categories -- sharps/clinical-waste, DVT prophylaxis,
compression, etc). Its own site (gandn.com) also carries two divisions with
genuine wound-care products that were captured but never mapped (hub: null):

  "Wound Dressings" (9 products, all Silverlon(R) silver dressings and
  B-WISE superabsorbent/silicone/gelling-fibre/charcoal dressings by name --
  https://www.gandn.com/) -- an unambiguous single-category division, mapped
  wholesale to wound:adv (Advanced dressings).

  "Wound Care and Prevention" (2 products) is a MIXED division needing
  product-level overrides (mixed-division-mapping policy,
  data/identity-vocabulary-policy.json):
    - Debritom+ Device: a micro water jet hydrosurgery device for wound
      debridement and irrigation (confirmed via clinicaltrials.gov study
      records for the device, e.g. NCT04514783, read 27/09/2026) ->
      wound:deb (Debridement & irrigation).
    - Spincare Device: an electrospinning device that sprays a protective
      nanofibre matrix onto burns/wounds (confirmed via published clinical
      literature on the SpinCare System, e.g. PMC11303125, read 27/09/2026)
      -> wound:adv (Advanced dressings), the closest existing type to a
      sprayed wound-covering technology.

Per-product source records for all 11 products were captured this run by
scripts/crawl_supplier_product_detail.py so build_differentiator.py's
own-source gate is satisfied.

Run once, then delete.
"""
import json

PATH = "data/differentiator-category-map.json"

PRODUCT_OVERRIDES = [
    {
        "kind": "product-override",
        "supplier": "Griffiths and Nielsen Ltd",
        "division": "Debritom+ Device",
        "products": 1,
        "categories": [],
        "examples": ["Debritom+ Device"],
        "hub": "wound:deb",
        "notTaxonomy": False,
        "evidence": "the supplier's own site filing (gandn.com), read by "
                    "scripts/crawl_supplier_site.py; product detail page "
                    "captured 27/09/2026 by "
                    "scripts/crawl_supplier_product_detail.py",
        "why": "Debritom+ is a micro water jet hydrosurgery device for wound "
               "debridement and irrigation, confirmed via published "
               "clinicaltrials.gov study records for the device -- "
               "wound:deb (Debridement & irrigation).",
        "decidedIn": "_seed_griffiths_nielsen_wound_overrides_0927.py",
    },
    {
        "kind": "product-override",
        "supplier": "Griffiths and Nielsen Ltd",
        "division": "Spincare Device",
        "products": 1,
        "categories": [],
        "examples": ["Spincare Device"],
        "hub": "wound:adv",
        "notTaxonomy": False,
        "evidence": "the supplier's own site filing (gandn.com), read by "
                    "scripts/crawl_supplier_site.py; product detail page "
                    "captured 27/09/2026 by "
                    "scripts/crawl_supplier_product_detail.py",
        "why": "The SpinCare System sprays an electrospun nanofibre matrix "
               "onto burns/wounds as a protective covering, confirmed via "
               "published clinical literature on the device -- wound:adv "
               "(Advanced dressings), the closest existing type to a "
               "sprayed wound-covering technology.",
        "decidedIn": "_seed_griffiths_nielsen_wound_overrides_0927.py",
    },
]


def main():
    d = json.load(open(PATH))
    entries = d["entries"]

    updated_division = False
    for e in entries:
        if (e.get("supplier") == "Griffiths and Nielsen Ltd"
                and e.get("division") == "Wound Dressings"
                and e.get("kind") is None):
            if e.get("hub"):
                print("Wound Dressings division already has hub=%r, leaving alone"
                      % e.get("hub"))
            else:
                e["hub"] = "wound:adv"
                e["why"] = ("All 9 named products are Silverlon(R) silver "
                             "dressings and B-WISE superabsorbent/silicone/"
                             "gelling-fibre/charcoal dressings -- an "
                             "unambiguous advanced-wound-dressing division. "
                             "wound:adv (Advanced dressings).")
                e["decidedIn"] = "_seed_griffiths_nielsen_wound_overrides_0927.py"
                updated_division = True
            break
    else:
        raise SystemExit("Wound Dressings division entry not found")

    existing = {(e.get("supplier"), e.get("division")) for e in entries}
    added = 0
    for e in PRODUCT_OVERRIDES:
        key = (e["supplier"], e["division"])
        if key in existing:
            print("SKIP already present:", key)
            continue
        entries.append(e)
        added += 1

    json.dump(d, open(PATH, "w"), indent=1, ensure_ascii=False)
    print("updated Wound Dressings division hub:", updated_division)
    print("added", added, "product-override entries")


if __name__ == "__main__":
    main()
