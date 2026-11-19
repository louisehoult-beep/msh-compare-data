"""One-off seeder, framework-coverage batch 28/10/2026, working Endoscopy,
Endourology and Oncology Ablation Consumables (catsInScope includes
oncology:abl, oncology:acc, oncology:stent).

Varian (Siemens Healthineers) is awarded on this framework (Lot 3, "Varian
Medical Systems"). Its seed record previously carried only a radiotherapy
deep-dive and no own-site product crawl, so crawl_supplier_site.py was run
against varian.com (28/10/2026) and returned 54 products in 9 divisions.
One of those, "Interventional Oncology" (7 rows), is a genuinely mixed
division: cryoablation/microwave-ablation consoles, embolization
consumables, and one non-product education page, all filed together
(mixed-division-mapping policy applies: map at product level where the
product's own name unambiguously identifies its speciality, hold the
remainder).

Confirmed against Varian/Siemens Healthineers' own Interventional Oncology
product page (varian.com/products/interventional-oncology, redirects to
cancercare.siemens-healthineers.com/products/interventional-oncology, read
28/10/2026) and a web search corroborating CryoCare CS as the earlier
console in the same CryoCare family as CryoCare Touch (medicalexpo.de /
fortecmedical.com reseller listings, 28/10/2026):

  - Cryocare Touch -- the site's own Cryoablation Solutions category ->
    oncology:abl.
  - Isolis -- the site's own Cryoablation Solutions category -> oncology:abl.
  - Cryocare Cs -- not named on the current page, but confirmed via
    reseller/distributor listings as the earlier CryoCare console in the
    same family as CryoCare Touch (same cryoablation function, simpler
    software) -> oncology:abl.
  - Intelliblate -- the site's own Microwave Ablation Solutions category,
    described as microwave ablation ("minimally invasive, image-guided
    procedures that use electromagnetic energy to heat and destroy
    tumors") -> oncology:abl.
  - Oncozene Microspheres -- the site's own Embolization Solutions
    category, embolization microspheres -> oncology:acc (procedure
    consumables), by the same reasoning as Vygon's CSTD and OncoSem's
    Components entries already in this map.
  - Sniper -- the site's own Embolization Solutions category -> oncology:acc.
  - Medical Education -- not a product at all (a resources/education page
    picked up by the sitemap crawl under the same division) -> left
    unmapped, nav-labels-are-not-products policy.

Run once: python3 scripts/_seed_varian_interventional_oncology_overrides_1028.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Varian (Siemens Healthineers)"

EVIDENCE = (
    "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
    "under the 'Interventional Oncology' division; confirmed via varian.com/"
    "products/interventional-oncology (redirects to cancercare.siemens-"
    "healthineers.com/products/interventional-oncology), read 28/10/2026."
)

ENTRIES = [
    ("Cryocare Touch", "oncology:abl",
     "cryoablation console, listed under Varian/Siemens Healthineers' own "
     "Cryoablation Solutions category on its Interventional Oncology page."),
    ("Isolis", "oncology:abl",
     "listed under Varian/Siemens Healthineers' own Cryoablation Solutions "
     "category on its Interventional Oncology page."),
    ("Cryocare Cs", "oncology:abl",
     "the earlier console in the same CryoCare cryoablation family as "
     "CryoCare Touch, per reseller/distributor listings (medicalexpo.de, "
     "fortecmedical.com) confirming it as a cryoablation system with the "
     "same function and a simpler software interface."),
    ("Intelliblate", "oncology:abl",
     "listed under Varian/Siemens Healthineers' own Microwave Ablation "
     "Solutions category, described there as image-guided microwave "
     "ablation to heat and destroy tumours."),
    ("Oncozene Microspheres", "oncology:acc",
     "embolization microspheres, listed under Varian/Siemens Healthineers' "
     "own Embolization Solutions category -- a procedure consumable, same "
     "reasoning as Vygon's CSTD and OncoSem's Components entries already "
     "mapped to oncology:acc."),
    ("Sniper", "oncology:acc",
     "listed under Varian/Siemens Healthineers' own Embolization Solutions "
     "category -- a procedure consumable."),
]


def main():
    doc = json.load(open(MAP))
    known = {(e["supplier"], e["division"]) for e in doc["entries"]}
    added = 0
    for product, hub, why in ENTRIES:
        key = (SUPPLIER, product)
        if key in known:
            print("already present, skipping:", product)
            continue
        doc["entries"].append({
            "kind": "product-override",
            "supplier": SUPPLIER,
            "division": product,
            "products": 1,
            "categories": ["Interventional Oncology"],
            "examples": [product],
            "hub": hub,
            "notTaxonomy": False,
            "evidence": EVIDENCE,
            "why": why,
            "decidedIn": "_seed_varian_interventional_oncology_overrides_1028.py",
        })
        added += 1
    doc["counts"]["pairs"] = len(doc["entries"])
    with open(MAP, "w") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("added %d product-override entries" % added)


if __name__ == "__main__":
    main()
