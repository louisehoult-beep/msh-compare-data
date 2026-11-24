#!/usr/bin/env python3
"""One-off: Enteral Feeding, Bile Bags and Associated Products framework-coverage
batch, 24/11/2026.

1. RICHARDSON HEALTHCARE -- HOMONYM CORRECTION (rule 10 / rule 8 sweep).
   The seed record (Richardson Healthcare Ltd, 04190638, Elstree, wound care and
   clinical consumables, NHS Supply Chain awardee) linked to directmedimaging.com and
   carried an ownership statement that it "no longer trades under that name" after
   an acquisition by DirectMed Imaging / Tri-Imaging Solutions. That acquisition was
   of a DIFFERENT, US business: Tri-Imaging's own release (directmedimaging.com/
   directmed-imaging-acquires-richardson-healthcare/, read 24/11/2026) describes an
   imaging-parts business manufacturing in LaFox, Illinois. The UK company still
   trades at richardsonhealthcare.com (read 24/11/2026: Elstree address, wound care,
   procedure packs, IV care, urology, respiratory).
   Domain proved on the REGISTRATION tier: https://richardsonhealthcare.com/
   terms-and-conditions/ states "Richardson Healthcare Ltd's company registration is
   04190638" (read 24/11/2026); Companies House 04190638 = RICHARDSON HEALTHCARE
   LIMITED, active (read 24/11/2026).
   The wrong link and both copies of the ownership claim are removed; a curator note
   records the homonym so it is not reintroduced (scripts/_publish_brand_presence_
   ownership_1118.py wrote it; that one-off must not be re-run for this record).

2. VOCABULARY GAP: nutrition:bile (standing vocabulary-gap policy, no escalation).
   PROMPTED BY: GenX MediCare Ltd's NHS Supply Chain catalogue lines "GenX Ryles Tube"
   (FWM4167/4169/4177/4189..., read by scripts/refresh_nhssc_cache.py --supplier
   "GenX MediCare Ltd" on 24/11/2026). A Ryles tube is a wide-bore nasogastric
   aspiration/drainage tube; nutrition:dev ("Feeding devices & tubes") would be
   actively wrong. NAME SOURCE: the framework's own Lot 5, "Bile Bags, Ryles Tubes and
   Levin Tubes" (contract launch brief, read 24/11/2026), which NHS Supply Chain keeps
   separate from Lot 2 "Enteral Feeding Devices". No existing type is renamed or
   re-scoped.

3. PRODUCT OVERRIDES (mixed-division-mapping; product name alone decides):
   - GenX MediCare Ltd, NHSSC item "GenX Ryles Tube" -> nutrition:bile.
   - Vygon (UK): five "Nutrisafe2 ... Nasogastric ... Feeding Tube" products and the
     "Nutrisafe2 Feeding Tube Obturator" sit in the "Neonatology and Paediatrics"
     division (mapped neonatal:feed + neonatal:equip). The names say enteral feeding
     tube outright, so nutrition:dev is ADDED; both neonatal categories are kept, so
     nothing leaves the neonatal view. Same treatment as Helapet's "Enteral Feeding
     Tubes - Neonatology / Paediatrics" (nutrition:dev, 16/11/2026). "Ready Set Feed"
     is not named as a tube or device and stays as it was.
"""
import json, sys
sys.path.insert(0, "scripts")
import seed_format

TODAY = "2026-11-24"
DECIDED = "framework-coverage-batch, 24/11/2026, Enteral Feeding, Bile Bags and Associated Products"
SEED, MAP, CMP = "data/supplier-seed.json", "data/differentiator-category-map.json", "data/compare-suppliers.json"

# ---- 1. Richardson
seed = json.load(open(SEED))
r = [s for s in seed["suppliers"] if s["name"] == "Richardson Healthcare"]
assert len(r) == 1
r = r[0]
r["links"] = [l for l in r["links"] if "directmedimaging" not in l["url"]]
if not any("richardsonhealthcare.com" in l["url"] for l in r["links"]):
    r["links"].insert(0, {"label": "Website", "url": "https://richardsonhealthcare.com/",
        "source": "Proved richardsonhealthcare.com by registration number on 2026-11-24: the site's "
                  "Terms and Conditions page (https://richardsonhealthcare.com/terms-and-conditions/) "
                  "states \"Richardson Healthcare Ltd's company registration is 04190638\"."})
r["companyNumberProof"] = {"number": "04190638", "route": "website-registration",
    "url": "https://richardsonhealthcare.com/terms-and-conditions/",
    "evidence": "Richardson Healthcare Ltd's company registration is 04190638",
    "checkedOn": TODAY}
r.pop("ownership", None)
r.pop("ownershipCheckedOn", None)
dd = r.get("deepDive") or {}
dd["ownership"] = [p for p in dd.get("ownership", []) if "DirectMed" not in p and "Tri-Imaging" not in p]
notes = r.setdefault("_curatorNotes", [])
if not any(n.get("heading") == "Not the US Richardson Healthcare" for n in notes):
    notes.append({"heading": "Not the US Richardson Healthcare",
        "text": "Corrected 24/11/2026. This record had been linked to directmedimaging.com and said the "
                "company no longer traded after an acquisition by DirectMed Imaging (now Tri-Imaging "
                "Solutions). That acquisition was of a different, US business: Tri-Imaging's own release "
                "(https://directmedimaging.com/directmed-imaging-acquires-richardson-healthcare/, read "
                "24/11/2026) describes an imaging-parts business manufacturing in LaFox, Illinois. "
                "Richardson Healthcare Ltd (04190638) still trades at richardsonhealthcare.com from Elstree, "
                "Hertfordshire. Never link or attribute DirectMed Imaging or Tri-Imaging Solutions to this "
                "record."})
seed_format.write_like(SEED, seed)

# ---- 2. vocabulary
LABEL = "Bile bags, Ryles tubes and Levin tubes (gastric drainage and aspiration; not feeding tubes)"
cmp = json.load(open(CMP))
cmp["specialities"]["nutrition"].setdefault("types", {}).setdefault("bile", LABEL)
seed_format.write_like(CMP, cmp)
cmap = json.load(open(MAP))
cmap["vocabulary"]["nutrition"].setdefault("bile", LABEL)

# ---- 3. overrides
have = {(e.get("supplier"), e.get("division")) for e in cmap["entries"] if e.get("kind") == "product-override"}
sp = json.load(open("data/supplier-products.json"))["suppliers"]
vy = {p["n"]: p for p in sp["Vygon (UK)"]["products"]}
VY = ["Nutrisafe2 PUR High Flow Nasogastric Feeding Tube", "Nutrisafe2 Nasogastric Silicone Feeding Tube",
      "Nutrisafe2 Nasogastric PVC Feeding Tube", "Nutrisafe2 PUR Nasogastric Feeding Tube",
      "Nutrisafe2 Nasogastric Gastro Duodenal Feeding Tube", "Nutrisafe2 Feeding Tube Obturator"]
added = 0
for n in VY:
    assert n in vy, n
    if ("Vygon (UK)", n) in have: continue
    cmap["entries"].append({"kind": "product-override", "supplier": "Vygon (UK)", "division": n, "products": 1,
        "categories": [vy[n]["division"]], "examples": [n],
        "hub": ["neonatal:feed", "neonatal:equip", "nutrition:dev"], "notTaxonomy": False,
        "evidence": "Vygon (UK)'s own site product record (data/supplier-products.json), division "
                    "'Neonatology and Paediatrics'. The product's own name says it is an enteral "
                    "(nasogastric) feeding tube or a feeding-tube accessory.",
        "why": "nutrition:dev added beside the division's two neonatal categories, which are kept unchanged; "
               "an enteral feeding tube or its accessory, by its own name.",
        "decidedIn": DECIDED, "addedOn": TODAY})
    added += 1
nh = json.load(open("data/nhssc-cache.json"))["products"]["Ryles tubes"]["items"]
assert any(i["name"] == "GenX Ryles Tube" and i["supplier"] == "GENX MEDICARE LTD" for i in nh)
if ("GenX MediCare Ltd", "GenX Ryles Tube") not in have:
    cmap["entries"].append({"kind": "product-override", "supplier": "GenX MediCare Ltd", "division": "GenX Ryles Tube",
        "products": len([i for i in nh if i["name"] == "GenX Ryles Tube"]), "categories": [],
        "examples": [i["desc"] for i in nh][:4], "hub": "nutrition:bile", "notTaxonomy": False,
        "evidence": "NHS Supply Chain public catalogue lines named 'GenX Ryles Tube', supplier GENX MEDICARE LTD, "
                    "read 24/11/2026 by scripts/refresh_nhssc_cache.py --supplier 'GenX MediCare Ltd'.",
        "why": "A Ryles tube is a nasogastric aspiration/drainage tube, the framework's own Lot 5 "
               "('Bile Bags, Ryles Tubes and Levin Tubes').",
        "decidedIn": DECIDED, "addedOn": TODAY})
    added += 1
seed_format.write_like(MAP, cmap)
print("Richardson corrected; vocab nutrition:bile; overrides added:", added)


# ---- 4. derived rows that carry the wrong website (rule 8 sweep). Patched in place:
# promote_index_to_compare.py would add 301 unrelated rows and a full
# build_innovator_report.py run carries ~6,800 unrelated changes, so only the one
# Richardson Healthcare url is touched in each.
def fix_urls(path):
    doc = json.load(open(path)); n = [0]
    def walk(o):
        if isinstance(o, dict):
            if o.get("co") == "Richardson Healthcare" and "directmedimaging" in str(o.get("url", "")):
                o["url"] = "https://richardsonhealthcare.com/"; n[0] += 1
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(doc)
    seed_format.write_like(path, doc)
    print(path, "urls fixed:", n[0])
for p in ("data/compare-suppliers.json", "data/innovator-report.json"):
    fix_urls(p)


# ---- 5. careers row. The collector's --supplier --write merge dropped 41 unrelated
# rows on 24/11/2026, so its own reading for this one supplier is applied in place:
# "[1/1] Richardson Healthcare (richardsonhealthcare.com) refused: no careers page
# found in the site's own navigation or at a conventional path". withCareersPage is
# recomputed exactly as the collector and verify.py compute it.
CAR = "data/supplier-careers.json"
car = json.load(open(CAR))
for row in car["suppliers"]:
    if row.get("name") == "Richardson Healthcare" and "directmed" in row.get("domain", ""):
        row.clear()
        row.update({"name": "Richardson Healthcare", "domain": "richardsonhealthcare.com", "checkedOn": TODAY,
                    "refused": "no careers page found in the site's own navigation or at a conventional path"})
car["counts"]["withCareersPage"] = sum(1 for r in car["suppliers"] if r.get("careersUrl"))
seed_format.write_like(CAR, car)
print("careers row corrected; withCareersPage", car["counts"]["withCareersPage"])
