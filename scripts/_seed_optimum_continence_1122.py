#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 22/11/2026, Urology and Bowel Management.

Optimum Medical (Optimum Medical Solutions Limited, Companies House 06779883,
domain optimummedical.co.uk per its seed record and its 15/10/2026 own-site
capture in data/supplier-products.json) is awarded on NHS Supply Chain's
Urology and Bowel Management framework (Lots 1, 2, 3 and 5). Its 15/10/2026
capture read 41 products from each product's own page but filed all of them
under one flat "Uncategorised" division (the product URLs carry no division
segment and the breadcrumbs name only the product), so 45 rows were HELD and
the supplier published nothing into the framework's continence scope.

Policy applied: mixed-division-mapping (data/identity-vocabulary-policy.json,
ruled 20/09/2026): map at PRODUCT level where the product is unambiguous, hold
the rest. Evidence for each product below is the manufacturer's own filing,
read live 22/11/2026 from two places on optimummedical.co.uk:
  1. the site's own Products menu, which files these products under named
     divisions: "Drainage" (Ugo Leg Bags, Ugo Pro Leg Bags, Ugo Sheath,
     Ugo Foley Catheter Kit [open-ended], Ugo Foley Catheter Kit,
     Ugo 2L Drainage Bags, Ugo 3L Drainage Bags, Ugo Catheter Valve) and
     "Intermittent Self-Catheterisation (ISC)" (Aloe Hydro, Aloe Hydro+,
     Aloe Original, Aloe Meatal+, HunterCath, Smooth Nelaton);
  2. each product page's own <title> and meta description (quoted verbatim
     below), which state what the product is.

Held, NOT mapped (no unambiguous in-vocabulary category): the Fixation range
(straps, clips, sleeve, belt, Multi Fix Gentle), Ugo Hanger, Ugo Stand,
ReadyCath Flex ("Ready to Use" division does not say catheter type),
Aloe Hydro+ (a genuine ISC catheter on its own page, but build_differentiator.py's
norm() reduces "Aloe Hydro+" and "Aloe Hydro" to the same key, so seeding both
gave Aloe Hydro the Hydro+ description and dropped Hydro+ as a duplicate; held
until the product join distinguishes the two names), the
procedure/management packs (Ugo Pro, The Ugo Box variants, Ugo 4 Weeks,
Ugo Home), lubricants, wipes, swabsticks, FFP3 masks, adhesive remover.

Why the detail rows are seeded here rather than by
scripts/crawl_supplier_product_detail.py: that crawler was run on these pages
22/11/2026 and its heuristic route returned menu boilerplate ("Find out more
about Ugo Fix Gentle (catheter clip)") as the description for three pages and
nothing usable for three more. That capture was discarded, not published. The
description below is the page's own declared meta description, which is a
data field the page publishes about itself, so it is recorded as structured.

Run once: python3 scripts/_seed_optimum_continence_1122.py
"""
import json

DETAIL = "data/supplier-product-detail.json"
MAP = "data/differentiator-category-map.json"
SUPPLIER = "Optimum Medical"
TODAY = "2026-11-22"
BASE = "https://optimummedical.co.uk/product/"
UP = "https://optimummedical.co.uk/wp-content/uploads/"

# (exact product name as in data/supplier-products.json, url slug, hub,
#  site division, page title, verbatim meta description, og:image path)
ENTRIES = [
    ("Ugo Leg Bags", "ugo-leg-bags/", "continence:dr", "Drainage",
     "Ugo Leg Bags - Optimum Medical",
     "Ugo Leg Bags are safe, effective and simple to use. Hospital and community leg bags, available in 350ml, 500ml and 750ml with Lever Tap or T Tap drainage.",
     "2016/12/ugo-leg-bag-featured.jpg"),
    ("Ugo Pro Leg Bags", "ugo-pro-leg-bags/", "continence:dr", "Drainage",
     "Ugo Pro Leg Bags - Optimum Medical",
     "Ugo Pro Leg Bags are urine leg bags supplied sterile with a disposable apron and pair of nitrile gloves in each pouch. Available in four variations.",
     "2022/03/ugopro-legbags-.jpg"),
    ("Ugo 2L Drainage Bags", "ugo-2l-drainage-bags/", "continence:dr", "Drainage",
     "Ugo 2L Drainage Bags - Optimum Medical",
     "Ugo 2L Drainage Bags are available sterile or non-sterile, with a choice of lever tap/T tap. Kink-free overnight urine drainage. Receive your free sample.",
     "2016/11/ugo-drainage-bags-featured.jpg"),
    ("Ugo 3L Drainage Bags", "ugo-3l-drainage-bags/", "continence:dr", "Drainage",
     "Ugo 3L Drainage Bags - Optimum Medical",
     "Ugo 3L Drainage Bags are available in sterile and non-sterile bags, suitable for link drainage systems. Designed for high urine output with a 3L capacity.",
     "2025/06/ugo15-3L-drainage-bags-.jpg"),
    ("Ugo Catheter Valve", "ugo-catheter-valve/", "continence:dr", "Drainage",
     "Ugo Catheter Valve - Optimum Medical",
     "The Ugo Catheter Valve is discreet, comfortable and easy to use, giving patients the confidence they need to carry on living independent lives.",
     "2016/07/ugo-valve-featured.jpg"),
    ("Ugo Sheath", "ugo-sheath/", "continence:sh", "Drainage",
     "Ugo Sheath - penile sheath for male urinary incontinence - Optimum Medical",
     "Ugo Sheath is a penile sheath, a comfortable alternative to incontinence pads for males with urinary incontinence. Up to 97% less plastic than other sheaths.",
     "2019/11/ugo-sheaths-.jpg"),
    ("Ugo Foley Catheter", "ugo-foley-catheter/", "continence:ind", "Drainage",
     "Ugo Foley Catheter Kit - supplied with syringes - Optimum Medical",
     "All silicone Foley catheter supplied with syringes for deflation and inflation. Suitable for transurethral and suprapubic catheterisation. Sizes 12CH-18CH.",
     "2020/02/ugo-Foley.jpg"),
    ("Ugo Foley Catheter Kit [open-ended]", "open-ended-ugo-foley-catheter/", "continence:ind", "Drainage",
     "Ugo Foley Catheter Kit [open-ended] - 100% Silicone - Optimum Medical",
     "All silicone open-ended Foley catheter supplied with syringes for deflation and inflation. Ugo Foley Catheter [open-ended] is supplied in sizes 12CH-18CH.",
     "2025/05/ugo_foley_OE_and_syringes1080x1080.jpg"),
    ("Aloe Hydro", "aloe-hydro/", "continence:ic", "Intermittent Self-Catheterisation (ISC)",
     "Aloe Hydro - Optimum Medical",
     "Our Aloe Hydro is a coated Intermittent Self catheterisation (ISC) catheter featuring a Nelaton tip. Provided with a sterile water sachet.",
     "2023/02/AloeHydro_featured-1.jpg"),
    ("Aloe Original", "aloe-original/", "continence:ic", "Intermittent Self-Catheterisation (ISC)",
     "Aloe Original - Optimum Medical",
     "Our Aloe Original Intermittent Self Catheterisation (ISC) catheter features our hydrophilic coating, activated with water, and a Nelaton tip.",
     "2023/01/AloeOriginal_featured.jpg"),
    ("Aloe Meatal+", "aloe-meatal/", "continence:ic", "Intermittent Self-Catheterisation (ISC)",
     "Aloe Meatal+ - Optimum Medical",
     "Our Aloe Meatal + is a dilation catheter featuring our hydrophilic coating, designed for people living with, or at risk of developing urethral strictures.",
     "2023/01/AloeMeatalPlus_featured.jpg"),
    ("HunterCath", "hunter-cath/", "continence:ic", "Intermittent Self-Catheterisation (ISC)",
     "HunterCath - Optimum Medical",
     "Our HunterCath is a non-coated, DEHP-free ISC catheter with a smooth flexible tip. The Hunter Cath is suitable for a wide range of ISC catheter users.",
     "2023/01/HunterCath_featured.jpg"),
    ("Smooth Nelaton", "smooth-nelaton/", "continence:ic", "Intermittent Self-Catheterisation (ISC)",
     "Smooth Nelaton - Optimum Medical",
     "The Smooth Nelaton is an ISC catheter, which features smooth rounded drainage holes to improve comfort during catheter insertion and removal.",
     "2023/01/SmoothNelaton_featured.jpg"),
]

WHY = {
    "continence:dr": "the manufacturer files it under its own 'Drainage' division and the product page describes a urine drainage bag, leg bag or catheter valve -- 'Drainage bags & valves'",
    "continence:sh": "the manufacturer files it under its own 'Drainage' division and the product page calls it a penile sheath for male urinary incontinence -- 'Sheaths'",
    "continence:ind": "the manufacturer files it under its own 'Drainage' division and the product page describes an all-silicone Foley catheter -- 'Indwelling (Foley) catheters'",
    "continence:ic": "the manufacturer files it under its own 'Intermittent Self-Catheterisation (ISC)' division and the product page describes an ISC catheter -- 'Intermittent catheters'",
}

# Check every name against the capture first: a name that is not in the
# capture would map nothing and must stop the run, not pass silently.
sp = json.load(open("data/supplier-products.json"))["suppliers"][SUPPLIER]
captured = {p["n"] for p in sp["products"]}
missing = [e[0] for e in ENTRIES if e[0] not in captured]
if missing:
    raise SystemExit("not in the 15/10 capture, stopping: %s" % missing)

detail = json.load(open(DETAIL))
cmap = json.load(open(MAP))
existing = {(e.get("supplier"), e.get("division")) for e in cmap["entries"]
            if e.get("kind") == "product-override"}

d_added = m_added = 0
for name, slug, hub, division, title, desc, img in ENTRIES:
    key = "%s|%s" % (SUPPLIER, name.lower())
    if key not in detail["products"]:
        detail["products"][key] = {
            "supplier": SUPPLIER,
            "product": name,
            "sourceUrl": BASE + slug,
            "capturedDate": TODAY,
            "parsed": "structured",
            "description": desc,
            "features": None,
            "image": UP + img,
        }
        d_added += 1
    else:
        print("detail already present, left as is:", name)
    if (SUPPLIER, name) in existing:
        print("product-override already present, left as is:", name)
        continue
    cmap["entries"].append({
        "kind": "product-override",
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": ["Uncategorised"],
        "examples": [name],
        "hub": hub,
        "notTaxonomy": False,
        "evidence": ("Optimum Medical's own site (optimummedical.co.uk), read 22/11/2026: "
                     "the Products menu files it under '%s', and its product page %s%s "
                     "(HTTP 200, title \"%s\") states: \"%s\" Own-site capture "
                     "15/10/2026 in data/supplier-products.json filed it in the flat "
                     "'Uncategorised' range." % (division, BASE, slug, title, desc)),
        "why": WHY[hub],
        "decidedIn": "framework-coverage-batch, 22/11/2026, Urology and Bowel Management (policy mixed-division-mapping)",
        "addedOn": TODAY,
    })
    m_added += 1

with open(DETAIL, "w") as f:
    json.dump(detail, f, ensure_ascii=False, indent=1)
with open(MAP, "w") as f:
    json.dump(cmap, f, ensure_ascii=False)
print("added %d detail rows, %d product-override entries for %s" % (d_added, m_added, SUPPLIER))
