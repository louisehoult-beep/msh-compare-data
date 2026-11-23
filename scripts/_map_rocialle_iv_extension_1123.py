#!/usr/bin/env python3
"""One-off mapping, framework-coverage batch 23/11/2026, Intravenous Cannula and
Associated Products.

Rocialle Healthcare (Rocialle Healthcare Ltd, Companies House 11965323) is named
on NHS Supply Chain's Intravenous Cannula and Associated Products launch brief.
Its 16/11/2026 own-site capture (rocialleacutecare.com, WordPress REST API, in
data/supplier-products.json and the seed) had no division mapped, so all 758
products were HELD and the supplier published nothing into vascular scope.

Domain proof (strongest tier, read 23/11/2026): rocialleacutecare.com prints in
its own footer and privacy policy "Rocialle AcuteCare is a trading division of
Rocialle Healthcare Ltd ... Registered in England, No. 11965323".

Evidence for the mapping is the manufacturer's own filing, read live 23/11/2026
from https://www.rocialleacutecare.com/wp-json/wp/v2/product (search=extension,
search=infusion). Every product in the captured "Iv Extension Sets" division
sits under /product/iv-extension-sets/<sub>/, and the site's own sub-categories
split it cleanly:
  * microbore-extension-sets, 10cm-microbore-extension-sets,
    standard-bore-extension-sets: 12 IV extension sets -> vascular:conn
    ('IV connectors, extensions & accessories'), as for Vygon's 'IV Extensions'.
  * administration-sets: 2 vented IV infusion sets (20 drops/mL) -> bloodtx:grav
    ('Gravity administration sets'), published via the product-override tier so
    the division mapping can never shadow them (ICU Medical precedent, 07/09).
No other Rocialle division is touched: only this framework's scope is worked.

Run once: python3 scripts/_map_rocialle_iv_extension_1123.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Rocialle Healthcare"
DIVISION = "Iv Extension Sets"
TODAY = "2026-11-23"
DECIDED = "framework-coverage-batch, 23/11/2026, Intravenous Cannula and Associated Products"
SRC = "https://www.rocialleacutecare.com/product/iv-extension-sets/administration-sets/"
GRAV = {
    "Vented IV Infusion Set Air-Stop/Prime-Stop - 20 drops/mL":
        SRC + "vented-iv-infusion-set-air-stop-prime-stop-20-drops-ml/",
    "Vented IV Infusion Set 20 drops/mL":
        SRC + "vented-iv-infusion-set-20-drops-ml/",
}

sp = json.load(open("data/supplier-products.json"))["suppliers"][SUPPLIER]
div = [p["n"] for p in sp["products"] if p.get("division") == DIVISION]
missing = [n for n in GRAV if n not in div]
if missing or len(div) != 14:
    raise SystemExit("capture does not match the 23/11 read, stopping: %d rows, missing %s" % (len(div), missing))

cmap = json.load(open(MAP))
have = {(e.get("supplier"), e.get("division"), e.get("kind")) for e in cmap["entries"]}
added = 0
if (SUPPLIER, DIVISION, None) not in have:
    cmap["entries"].append({
        "supplier": SUPPLIER,
        "division": DIVISION,
        "products": 14,
        "categories": [DIVISION],
        "examples": ["Microbore Extension Set, Double-Lumen, 10cm",
                     "Standard Bore Extension Set 180cm",
                     "Minimum Volume Extension Set 150cm with Anti-siphon Valve",
                     "Microbore Extension Set, Single-Lumen, 10cm with NEUTRAL Needle-Free Site"],
        "hub": "vascular:conn",
        "notTaxonomy": False,
        "evidence": ("Rocialle AcuteCare's own site (rocialleacutecare.com, a trading division of "
                     "Rocialle Healthcare Ltd, No. 11965323 printed on the site), WordPress REST "
                     "product API read 23/11/2026: 12 of the division's 14 products sit under "
                     "/product/iv-extension-sets/ microbore-extension-sets, 10cm-microbore-extension-sets "
                     "and standard-bore-extension-sets; the other 2 sit under administration-sets and "
                     "carry their own product-override to bloodtx:grav."),
        "why": "microbore and standard-bore IV extension sets, single to triple lumen, some with needle-free sites -- IV line extensions, vascular:conn ('IV connectors, extensions & accessories'), as Vygon's 'IV Extensions'.",
        "decidedIn": DECIDED,
        "addedOn": TODAY,
    })
    added += 1
for name, url in GRAV.items():
    if (SUPPLIER, name, "product-override") in have:
        continue
    cmap["entries"].append({
        "kind": "product-override",
        "supplier": SUPPLIER,
        "division": name,
        "products": 1,
        "categories": [DIVISION],
        "examples": [name],
        "hub": "bloodtx:grav",
        "notTaxonomy": False,
        "evidence": ("Rocialle AcuteCare's own site, read 23/11/2026: the product is filed under "
                     "/product/iv-extension-sets/administration-sets/ (%s), not under an extension-set "
                     "sub-category; captured 16/11/2026 in the flat 'Iv Extension Sets' division." % url),
        "why": "a vented 20 drops/mL IV infusion set is a gravity administration set ('Gravity administration sets'), not an extension; product-override so the division's vascular:conn mapping never shadows it.",
        "decidedIn": DECIDED,
        "addedOn": TODAY,
    })
    added += 1

with open(MAP, "w") as f:
    json.dump(cmap, f, ensure_ascii=False)
print("added %d map entries for %s" % (added, SUPPLIER))

# ---------------------------------------------------------------------------
# Detail rows. build_differentiator.py publishes an own-site product only when a
# source carries it (supplier-product-detail.json or an NHSSC row); the 16/11
# capture recorded names only. Each row below is the product's own page as the
# site's WordPress REST API serves it (link + content.rendered, read 23/11/2026),
# description = the opening sentences of that page text, verbatim. The og:image
# on these pages is the generic Rocialle AcuteCare logo, so no image is recorded.
DETAIL = "data/supplier-product-detail.json"
DETAIL_ROWS = [('Microbore Extension Set, Double-Lumen, 10cm',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/10cm-microbore-extension-sets/microbore-extension-set-double-lumen-10cm/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow with an '
  'optional neutral needle-free site that prevents the risk of infection. The Male Luer Lock is ribbed to '
  'enable an easy grip and connection to the patient-side IV access. Universal 6% taper ensures compliance '
  'with ISO594 to be compatible with standardised devices.'),
 ('Microbore Extension Set 495cm',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/microbore-extension-sets/microbore-extension-set-495cm/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow. The Male Luer '
  'Lock is ribbed to enable an easy grip and connection to the patient-side IV access. Universal 6% taper '
  'ensures compliance with ISO594 to be compatible with standardised devices. The PVC tube is highly '
  'kink-resistant allowing for an optimal flow rate and is DEHP-Free Equipped with a slide clamp.'),
 ('Standard Bore Extension Set 180cm',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/standard-bore-extension-sets/standard-bore-extension-set-180cm/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow with wings for '
  'easy gripping and attachment to the IV fluid access. The Male Luer Lock is ribbed to enable an easy grip '
  'and connection to the patient-side IV access. Universal 6% taper ensures compliance with ISO594 to be '
  'compatible with standardised devices.'),
 ('Standard Bore Extension Set 30cm',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/standard-bore-extension-sets/standard-bore-extension-set-30cm/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow with wings for '
  'easy gripping and attachment to the IV fluid access. The Male Luer Lock is ribbed to enable an easy grip '
  'and connection to the patient-side IV access. Universal 6% taper ensures compliance with ISO594 to be '
  'compatible with standardised devices.'),
 ('Minimum Volume Extension Set 150cm with Anti-siphon Valve',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/standard-bore-extension-sets/minimum-volume-extension-set-150cm-with-anti-siphon-valve/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow with wings for '
  'easy gripping and attachment to the IV fluid access. The Male Luer Lock is ribbed to enable an easy grip '
  'and connection to the patient-side IV access. Universal 6% taper ensures compliance with ISO594 to be '
  'compatible with standardised devices.'),
 ('Microbore Extension Set, Triple-Lumen, 10cm',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/10cm-microbore-extension-sets/microbore-extension-set-triple-lumen-10cm/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow with an '
  'optional neutral needle-free site that prevents the risk of infection. The Male Luer Lock is ribbed to '
  'enable an easy grip and connection to the patient-side IV access. Universal 6% taper ensures compliance '
  'with ISO594 to be compatible with standardised devices.'),
 ('Microbore Extension Set, Single-Lumen, 10cm',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/10cm-microbore-extension-sets/microbore-extension-set-single-lumen-10cm/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow with an '
  'optional neutral needle-free site that prevents the risk of infection. The Male Luer Lock is ribbed to '
  'enable an easy grip and connection to the patient-side IV access. Universal 6% taper ensures compliance '
  'with ISO594 to be compatible with standardised devices.'),
 ('Microbore Extension Set, Triple-Lumen, 10cm with NEUTRAL Needle-Free Site',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/10cm-microbore-extension-sets/microbore-extension-set-triple-lumen-10cm-with-neutral-needle-free-site/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow with an '
  'optional neutral needle-free site that prevents the risk of infection. The Male Luer Lock is ribbed to '
  'enable an easy grip and connection to the patient-side IV access. Universal 6% taper ensures compliance '
  'with ISO594 to be compatible with standardised devices.'),
 ('Microbore Extension Set, Double-Lumen, 10cm with NEUTRAL Needle-Free Site',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/10cm-microbore-extension-sets/microbore-extension-set-double-lumen-10cm-with-neutral-needle-free-site/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow with an '
  'optional neutral needle-free site that prevents the risk of infection. The Male Luer Lock is ribbed to '
  'enable an easy grip and connection to the patient-side IV access. Universal 6% taper ensures compliance '
  'with ISO594 to be compatible with standardised devices.'),
 ('Microbore Extension Set, Single-Lumen, 10cm with NEUTRAL Needle-Free Site',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/10cm-microbore-extension-sets/microbore-extension-set-single-lumen-10cm-with-neutral-needle-free-site/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow with an '
  'optional neutral needle-free site that prevents the risk of infection. The Male Luer Lock is ribbed to '
  'enable an easy grip and connection to the patient-side IV access. Universal 6% taper ensures compliance '
  'with ISO594 to be compatible with standardised devices.'),
 ('Microbore Extension Set 180cm',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/microbore-extension-sets/microbore-extension-set-180cm/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow. The Male Luer '
  'Lock is ribbed to enable an easy grip and connection to the patient-side IV access. Universal 6% taper '
  'ensures compliance with ISO594 to be compatible with standardised devices. The PVC tube is highly '
  'kink-resistant allowing for an optimal flow rate and is DEHP-Free Equipped with a slide clamp.'),
 ('Microbore Extension Set 30cm',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/microbore-extension-sets/microbore-extension-set-30cm/',
  'Designed with Medical Grade Silicone, the Female Luer Lock allows for bi-directional flow. The Male Luer '
  'Lock is ribbed to enable an easy grip and connection to the patient-side IV access. Universal 6% taper '
  'ensures compliance with ISO594 to be compatible with standardised devices. The PVC tube is highly '
  'kink-resistant allowing for an optimal flow rate and is DEHP-Free Equipped with a slide clamp.'),
 ('Vented IV Infusion Set Air-Stop/Prime-Stop - 20 drops/mL',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/administration-sets/vented-iv-infusion-set-air-stop-prime-stop-20-drops-ml/',
  'Designed with Medical Grade Silicone Vented Chamber – 20 drops/mL The Male Luer Lock is ribbed to enable '
  'an easy grip and connection to the patient-side IV access. The DEHP-Free PVC tube is higher '
  'kink-resistant to create an optimal flow rate. Equipped with a roller clamp Latex-free to cater for '
  'patient requirements.'),
 ('Vented IV Infusion Set 20 drops/mL',
  'https://www.rocialleacutecare.com/product/iv-extension-sets/administration-sets/vented-iv-infusion-set-20-drops-ml/',
  'Designed with Medical Grade Silicone Vented Chamber – 20 drops/mL The Male Luer Lock is ribbed to enable '
  'an easy grip and connection to the patient-side IV access. The DEHP-Free PVC tube is higher '
  'kink-resistant to create an optimal flow rate. Equipped with a roller clamp Latex-free to cater for '
  'patient requirements.')]

detail = json.load(open(DETAIL))
d_added = 0
for name, link, desc in DETAIL_ROWS:
    if name not in div:
        raise SystemExit("detail row not in capture, stopping: %s" % name)
    key = "%s|%s" % (SUPPLIER, name.lower())
    if key in detail["products"]:
        print("detail already present, left as is:", name)
        continue
    detail["products"][key] = {
        "supplier": SUPPLIER,
        "product": name,
        "sourceUrl": link,
        "capturedDate": TODAY,
        "parsed": "structured",
        "description": desc,
        "features": None,
        "image": None,
    }
    d_added += 1
with open(DETAIL, "w") as f:
    json.dump(detail, f, ensure_ascii=False, indent=1)
print("added %d detail rows for %s" % (d_added, SUPPLIER))

# ---------------------------------------------------------------------------
# William Davies Care Limited, same framework (named on the IV Cannula launch
# brief). No website on file; its one NHS Supply Chain catalogue row, NPC
# FVH85019 (MPC HM012, "Plugs stoppers and bungs Female type Screw Caps"), is
# listed in NHS Supply Chain's own Information for Clinical Choice document
# ICC-NP-IV-Stoppers-Support-Document-5-June-2023-T1.pdf (data/icc-matrices.json,
# sub-category "IV Stoppers - White") as "IV stopper white", fits female luer
# lock "e.g., IV cannula, hypodermic". NHS-authored product type, so the item is
# unambiguous: vascular:conn. NPC-keyed so nothing else under the name moves.
WDC = "WILLIAM DAVIES CARE LIMITED"   # supplier string exactly as the NHSSC cache carries it
cmap = json.load(open(MAP))
if not any(e.get("kind") == "product-override" and e.get("npc") == "FVH85019" for e in cmap["entries"]):
    cmap["entries"].append({
        "kind": "product-override",
        "supplier": WDC,
        "division": "William Davies Care [FVH85019]",
        "npc": "FVH85019",
        "products": 1,
        "categories": [],
        "examples": ["Plugs stoppers and bungs Female type Screw Caps"],
        "hub": "vascular:conn",
        "notTaxonomy": False,
        "evidence": ("NHS Supply Chain public catalogue (data/nhssc-cache.json, NPC FVH85019, MPC HM012) and "
                     "NHS Supply Chain's Information for Clinical Choice IV Stoppers support document "
                     "(ICC-NP-IV-Stoppers-Support-Document-5-June-2023-T1.pdf, page 4, in data/icc-matrices.json), "
                     "which lists this NPC as 'IV stopper white', fits female luer lock 'e.g., IV cannula, hypodermic'."),
        "why": "an IV line stopper is an IV accessory, vascular:conn ('IV connectors, extensions & accessories'), as Vygon's 'IV Bungs & Stoppers' and BMS Critical Care's dual end stoppers.",
        "decidedIn": DECIDED,
        "addedOn": TODAY,
    })
    with open(MAP, "w") as f:
        json.dump(cmap, f, ensure_ascii=False)
    print("added NPC-keyed override FVH85019 for", WDC)
