#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 31/10/2026.

Labcold's own-site capture (data/supplier-products.json, verified 18/08/2026
against Companies House 00271055) already carries two divisions mapped to an
in-scope category for "Laboratory Diagnostics, Point of Care Testing and
Pathology Managed Services" (data/differentiator-category-map.json: both
"Laboratory Refrigeration" and "Blood Product Storage" -> hub pathology:equip,
mapped by an earlier, unrelated pass). All 19 products in those two divisions
were nonetheless HELD, for the separate reason build_differentiator.py checks
after the category: "no source carries this product -- neither the
manufacturer's own page nor NHSSC" (no entry existed in
data/supplier-product-detail.json). This is the exact shape already on record
for Celtic SMR Ltd on 25/09/2026 (docs/framework-coverage-exhausted.json,
Ultrasound Scanners entry): a correct category mapping with no per-product
source behind it.

Fetched live 31/10/2026, read via WebFetch:
- https://www.labcold.com/laboratory-refrigeration (11 products)
- https://www.labcold.com/blood-product-storage (8 products)

Both pages are Labcold's own first-party product pages (labcold.com, the
domain already confirmed in data/supplier-products.json's own identity note).
Every product name below matches, character for character, the "n" field
already on record in data/supplier-products.json for Labcold -- nothing
renamed, nothing invented. Descriptions below are the page's own wording,
trimmed; images are the page's own product photos, absolute-ized from the
site-relative paths the page returns.

Run once: python3 scripts/_seed_labcold_pathology_detail_1031.py
"""
import json

DETAIL = "data/supplier-product-detail.json"
SUPPLIER = "Labcold"
TODAY = "2026-10-31"

LAB_REFRIGERATION_URL = "https://www.labcold.com/laboratory-refrigeration"
BLOOD_STORAGE_URL = "https://www.labcold.com/blood-product-storage"
IMG_BASE = "https://www.labcold.com"

ENTRIES = [
    # Laboratory Refrigeration (division already mapped: pathology:equip)
    ("Sparkfree Fridges", LAB_REFRIGERATION_URL,
     "Labcold Sparkfree fridges are built specifically for lab safety, with "
     "ignition sources removed from the interior.",
     "/storage/product_cat/cropped/RLPR1517ajar_600x600.jpg"),
    ("Sparkfree Freezers", LAB_REFRIGERATION_URL,
     "Store flammable materials safely by removing interior ignition "
     "sources, such as thermostats or lights.",
     "/storage/product_cat/cropped/RLVF1517openweb_600x600.jpg"),
    ("Sparkfree ATEX Refrigerators and Freezers", LAB_REFRIGERATION_URL,
     "Removes all internal sources of ignition and is compliant with ATEX "
     "directives.",
     "/storage/featured_image/cropped/rlpr0217atexajarweb-scaled_1742211945.webp"),
    ("Advanced Laboratory Range", LAB_REFRIGERATION_URL,
     "Designed for demanding lab environments, this range features robust "
     "construction and stainless steel interiors.",
     "/storage/product_cat/cropped/RAFR44263_600x600.jpg"),
    ("IntelliCold Sample and Reagent Fridges", LAB_REFRIGERATION_URL,
     "The IntelliCold range is purpose-built for the safe storage of "
     "temperature-sensitive samples, reagents, and vaccines.",
     "/storage/product_cat/cropped/rldf1024_1783939601.png"),
    ("-40C Labcold Laboratory Freezers", LAB_REFRIGERATION_URL,
     "Available in three sizes, these -40C freezers provide consistent, "
     "reliable ultra-low storage.",
     "/storage/product_cat/cropped/RLHE0845_600x600.jpg"),
    ("-80C Ultra Low Temp Freezers", LAB_REFRIGERATION_URL,
     "Engineered to protect high-value samples, -80C ultra-low temperature "
     "freezers offer high-performance storage.",
     "/storage/product_cat/cropped/LULT445background-scaled_600x600.jpg"),
    ("Labcold Standard Range Fridges & Freezers", LAB_REFRIGERATION_URL,
     "Designed for value without compromising reliability, the Standard "
     "Range is ideal for laboratories.",
     "/storage/product_cat/cropped/RLFR2004ajar_600x600.jpg"),
    ("Labcold Cooled Incubators", LAB_REFRIGERATION_URL,
     "Labcold cooled incubators maintain stable temperatures at or below "
     "room temperature.",
     "/storage/product_cat/cropped/RLCG0600b_600x600.jpg"),
    ("Labcold Cubed Ice Makers", LAB_REFRIGERATION_URL,
     "Constructed from stainless steel with insulated collection bins, "
     "these ice makers are built to last.",
     "/storage/product_cat/cropped/LITV-DP150_600x600.jpg"),
    ("Labcold Flake Ice Makers", LAB_REFRIGERATION_URL,
     "Efficient and hygienic, Labcold ITV flake ice makers provide a "
     "reliable source of laboratory-grade ice.",
     "/storage/product_cat/cropped/LITV-IQ135background_600x600.jpg"),
    # Blood Product Storage (division already mapped: pathology:equip)
    ("Compact Blood Bank Refrigerators", BLOOD_STORAGE_URL,
     "Space-saving without compromising on quality or compliance. Ideal "
     "for smaller facilities, clinics or emergency use.",
     "/storage/product_cat/cropped/rsbg2056md-600x600_1744790287.jpg"),
    ("Large Capacity Blood Bank Refrigerators", BLOOD_STORAGE_URL,
     "Manufactured at Labcold's UK factory, these high-volume models are "
     "designed for blood banks, with robust capacity, full compliance and "
     "built-in advanced monitoring.",
     "/storage/product_cat/cropped/rdbg2640-door-open_1765382458.jpg"),
    ("Labcold Plasma Freezers", BLOOD_STORAGE_URL,
     "Designed and built in the UK, Labcold's plasma freezers meet all "
     "required standards and provide ultra-stable performance for frozen "
     "plasma storage.",
     "/storage/product_cat/cropped/RVPF2134_600x600.jpg"),
    ("Labcold Platelet Incubators", BLOOD_STORAGE_URL,
     "Delivering precise, stable temperatures for consistent platelet "
     "storage with full compliance.",
     "/storage/product_cat/cropped/rlpi0550mdclosed-600x600_1744791312.jpg"),
    ("Labcold Platelet Agitators", BLOOD_STORAGE_URL,
     "Engineered for gentle, continuous agitation to maintain platelet "
     "viability by ensuring oxygen transfer.",
     "/storage/product_cat/cropped/6rackagit-600x600_1744791414.jpg"),
    ("Barkey Plasma Thawers", BLOOD_STORAGE_URL,
     "Labcold also offers Barkey Plasmatherm and Plasmatherm V, Class IIa "
     "certified medical devices for fast, safe thawing of plasma.",
     "/storage/product_cat/cropped/barkey-plasmathermv-30fastere-600x600_1744790457.jpg"),
    ("Labcold Insulated Transit Boxes", BLOOD_STORAGE_URL,
     "Durable, reusable and easy to clean lightweight plastic boxes for "
     "temperature-controlled transport of blood products.",
     "/storage/product_cat/cropped/rtbb0006-2-boxes-600x600_1744790812.jpg"),
    ("Labcold Blood Baskets", BLOOD_STORAGE_URL,
     "Custom-designed for Labcold shelf-model blood banks, the baskets "
     "keep blood bags organised and secure inside the unit.",
     "/storage/product_cat/cropped/bloodbasket-3-600x600_1744790728.jpg"),
]

doc = json.load(open(DETAIL))
products = doc["products"]
added = 0
for name, url, desc, img in ENTRIES:
    key = "%s|%s" % (SUPPLIER, name.lower())
    if key in products:
        print("already present, skipping:", name)
        continue
    products[key] = {
        "supplier": SUPPLIER,
        "product": name,
        "sourceUrl": url,
        "capturedDate": TODAY,
        "parsed": "structured",
        "description": desc,
        "features": None,
        "image": IMG_BASE + img,
    }
    added += 1

json.dump(doc, open(DETAIL, "w"), ensure_ascii=False)
print("added %d supplier-product-detail.json entries for Labcold" % added)
