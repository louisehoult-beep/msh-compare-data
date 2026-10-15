#!/usr/bin/env python3
"""Land six of the ten re-crawls held on 09/10/2026 (^o635), 15/10/2026.

Each capture was read live this session with crawl_supplier_site.crawl() and
passed through tidy_capture() (the guard added in the same change). Usage:
    python3 scripts/_land_held_recrawls_1015.py <dir holding <key>.json captures>

Re-curation of the category map, each checked at the supplier's own site
15/10/2026:
- Macromed: 18 product-overrides renamed from URL-slug names to the names the
  product pages print (same products, same categories).
- Wassenburg: products-sitemap.xml lists exactly 10 products. The 11 old
  division entries were keyed on slug divisions full of brochure filenames
  (33 "products" under EndoHigh PAA). Each becomes a product-override on its
  product's printed name with the same category; Endofender is no longer on
  the site, so its entry goes.
- VWS: /products/hemoro-4-one-home-hemodialysis-machine now prints "Hemoro 4
  One Single Dialysis Patient RO Unit", a water-treatment unit, so renal:hd
  was wrong and it moves to renal:water. /products/nephro-safe now prints
  "Renal Disinfection Systems" (heat disinfection for dialysis water), renal:water.
- PDI, Welland, Vitalograph: only their flat 'Uncategorised' entry, recounted.
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import crawl_supplier_site as cs

CAP = sys.argv[1]
LAND = {"pdi": "PDI (EMEA)", "welland": "Welland Medical Ltd", "vitalograph": "Vitalograph",
        "macromed": "Macromed UK Ltd", "wassenburg": "Wassenburg Medical", "vws": "VWS (UK) Ltd"}
NOTE = (" Re-curated 15/10/2026 (^o635) to the name the product's own page now prints, "
        "after the per-page re-crawl replaced the URL-slug name.")

MACROMED = {"Cerv X": "Cerv-x™", "Pezo": "Pezo™", "Tezo": "Tezo™", "Add": "ADD™",
            "Addplus": "ADDplus™", "Cosmicmia": "CosmicMIA™", "Neon3": "Neon3™",
            "Obeliscpro": "ObeliscPRO™", "Osmium": "Osmium™", "Ucentum": "uCentum™",
            "Intraspine": "IntraSPINE®", "Gbm Cervical Cage": "GBM Cervical Cage",
            "Golden Gate": "Golden Gate™", "Mambo": "Mambo™", "Ogmend": "OGMend",
            "Osmycin Antibiotic Allograft": "Osmycin", "Magnetos Putty": "MagnetOs Putty",
            "Magnetos Granules": "MagnetOs Granules"}
WASSENBURG = {"Endohigh Paa Detergent": "EndoHigh® PAA and Detergent Process Chemicals",
              "Endocart": "EndoCart: The transport solution for all types of endoscopes",
              "Endohigh Gta Detergent": "EndoHigh® GTA and Detergent process chemicals",
              "Dry300D": "WASSENBURG® DRY300D Pass Through Drying Cabinet",
              "Wassenburg Boiler": "Wassenburg Boiler - Wassenburg Medical",
              "Wd440 2": "WASSENBURG WD440 Toploader Endoscope Washer-Disinfector",
              "Wd440 Pt": "WASSENBURG WD440 PT pass through endoscope reprocessor",
              "Dry320 2": "WASSENBURG® DRY320 Drying and storage cabinet",
              "Wd4200": "WASSENBURG WD4200 Toploader endoscope reprocessor",
              "Traceability Software Endoexpert Manager":
                  "WASSENBURG Traceability Software - Wassenburg Medical"}
VWS = {"Hemoro 4 One Home Hemodialysis Machine": ("Hemoro 4 One Single Dialysis Patient RO Unit", "renal:water",
        "The product page (veoliawatertechnologies.co.uk/products/hemoro-4-one-home-hemodialysis-machine, "
        "read 15/10/2026) now names it a single-patient reverse osmosis unit: it purifies water for home "
        "dialysis, it is not the dialysis machine. renal:hd was wrong; renal:water."),
       "Nephro Safe": ("Renal Disinfection Systems", "renal:water",
        "The page at /products/nephro-safe now prints 'Renal Disinfection Systems', heat disinfection "
        "systems for renal dialysis water (read 15/10/2026).")}

prod = json.load(open(cs.OUT, encoding="utf-8"))
caps = {}
for key, name in LAND.items():
    shaped = json.load(open(os.path.join(CAP, key + ".json")))["shaped"]
    shaped, notes = cs.tidy_capture(shaped)
    existing = prod["suppliers"].get(name) or {}
    for k in ("aliases", "companyNo", "notSold", "tubesNote", "domainWarning"):
        if k in existing:
            shaped[k] = existing[k]
    prod["suppliers"][name] = shaped
    prod.get("refusals", {}).pop(name, None)
    caps[name] = shaped
    print("captured %-22s %3d products, %d division(s); %s" % (name, len(shaped["products"]),
          len(shaped["divisions"]), "; ".join(notes) or "no tidy needed"))
cs.atomic_write_json(cs.OUT, prod)

MAP = "data/differentiator-category-map.json"
m = json.load(open(MAP, encoding="utf-8"))
names = {s: {p["n"] for p in c["products"]} for s, c in caps.items()}
out = []
for e in m["entries"]:
    sup = e.get("supplier")
    if sup not in caps:
        out.append(e); continue
    if e.get("kind") == "nhssc-term":
        out.append(e); continue
    div = e.get("division")
    if sup == "Macromed UK Ltd" and e.get("kind") == "product-override":
        new = MACROMED[div]
        assert new in names[sup], new
        e["division"] = new; e["examples"] = [new]; e["evidence"] = e.get("evidence", "") + NOTE
    elif sup == "VWS (UK) Ltd" and e.get("kind") == "product-override":
        new, hub, why = VWS[div]
        assert new in names[sup], new
        e["division"] = new; e["examples"] = [new]; e["hub"] = hub
        e["why"] = why; e["evidence"] = e.get("evidence", "") + NOTE
    elif sup == "Wassenburg Medical":
        if div == "Endofender":
            print("dropped Wassenburg 'Endofender': not in products-sitemap.xml, 15/10/2026")
            continue
        new = WASSENBURG[div]
        assert new in names[sup], new
        e.update({"kind": "product-override", "division": new, "products": 1, "examples": [new],
                  "evidence": "the supplier's own site filing (products-sitemap.xml, 10 products, each "
                              "page's own name), read by scripts/crawl_supplier_site.py 15/10/2026." + NOTE})
    elif div == "Uncategorised":
        c = caps[sup]
        if [d["name"] for d in c["divisions"]] == ["Water Treatment Products"]:
            # VWS: the per-page read found the site's one real crumb, so its
            # range moves from 'Uncategorised' to that division, unmapped as before.
            e["division"] = "Water Treatment Products"
            e["structure_note"] = "renamed from 'Uncategorised' 15/10/2026: the product pages' own breadcrumb"
        d0 = e["division"]
        e["products"] = sum(1 for p in c["products"] if p.get("division") == d0)
        e["examples"] = [p["n"] for p in c["products"] if p.get("division") == d0][:4]
    out.append(e)
# Wassenburg is now flat: give it the same honest 'Uncategorised' entry every flat range has.
if not any(e.get("supplier") == "Wassenburg Medical" and e.get("division") == "Uncategorised" for e in out):
    out.append({"supplier": "Wassenburg Medical", "division": "Uncategorised", "products": 10,
                "categories": [], "examples": sorted(names["Wassenburg Medical"])[:4], "hub": None,
                "notTaxonomy": True,
                "evidence": "the supplier's own site filing, read by scripts/crawl_supplier_site.py"})
m["entries"] = out
with open(MAP, "w", encoding="utf-8") as f:
    json.dump(m, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("category map rewritten")
