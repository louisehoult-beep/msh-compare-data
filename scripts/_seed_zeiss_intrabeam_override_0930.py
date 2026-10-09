#!/usr/bin/env python3
"""One-off, 30/09/2026 (^o625): publish Carl Zeiss Ltd's ZEISS INTRABEAM 600 in
the Differentiator for the "Radiotherapy Treatment Systems and Associated
Options and Related Services" framework (catsInScope includes oncology:radio).

Manual product capture route, sanctioned by Lou 30/09/2026 (Cowork-OS
02-Elevate-and-Thrive/Process flows for all brands/manual-product-capture-route.md).
The product already sits on Zeiss's seed record (7d9619f). Follows the Celtic
SMR precedent (4be8bf0, scripts/_seed_celtic_smr_ultrasound_overrides_0925.py):
one supplier-product-detail.json record read from the product's own page on
the manufacturer's own site, plus one kind="product-override" map entry.

One step the Celtic case did not need: Celtic SMR already had a
supplier-products.json capture carrying the product names, and
build_differentiator.py only publishes products that capture carries. Carl
Zeiss Ltd had no capture at all (its only published rows are NHSSC IOL items
via an nhssc-term entry), so this adds a one-product record, marked
partialRead with a filingRule saying it is a single hand-read page and not
Zeiss's range (the MIP UK "Representative capture, not exhaustive" shape).

Source, read 30/09/2026 in Chrome (curl/WebFetch get HTTP 403 from zeiss.com):
  https://www.zeiss.com/meditec/en/products/intraoperative-radiotherapy-systems.html
robots.txt (zeiss.com): User-Agent * Allow *; disallows only ?nodefault and
_jcr_content paths. Description and features are the page's own sentences,
verbatim, with its footnote reference numerals removed. Nothing inferred: no
spec value is recorded that the page does not state (the page links a
Technical Specifications PDF; it was not read and nothing from it is used).

Category: the page names it an intraoperative radiotherapy (IORT) system, an
X-ray source delivering radiation to the tumour bed during surgery.
oncology:radio is "Radiotherapy capital equipment (linacs, gamma knife,
brachytherapy afterloaders)" — the capital-equipment treatment type, as
distinct from posn (positioning) and dosim (dosimetry/QA).

Run once from the repo root: python3 scripts/_seed_zeiss_intrabeam_override_0930.py
"""
import json

SUPPLIER = "Carl Zeiss Ltd"
NAME = "ZEISS INTRABEAM 600"
DIVISION = "Intraoperative radiotherapy systems"
URL = "https://www.zeiss.com/meditec/en/products/intraoperative-radiotherapy-systems.html"
DATE = "2026-09-30"
HUB = "oncology:radio"

RANGE = "data/supplier-products.json"
DETAIL = "data/supplier-product-detail.json"
MAP = "data/differentiator-category-map.json"


def save(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


# 1. Range record (the builder's product list).
sp = json.load(open(RANGE, encoding="utf-8"))
if SUPPLIER in sp["suppliers"]:
    names = {p["n"] for p in sp["suppliers"][SUPPLIER]["products"]}
    assert NAME in names, "Carl Zeiss Ltd now has a capture without INTRABEAM; re-plan"
    print("range: already present")
else:
    sp["suppliers"][SUPPLIER] = {
        "domain": "zeiss.com",
        "verified": DATE,
        "source": "zeiss.com, the product's own page read by hand in Chrome this run "
                  "(manual product capture route, sanctioned 30/09/2026): " + URL,
        "structureFrom": "the page's own product-category name",
        "hasDivisions": True,
        "partialRead": True,
        "structure": "One product page read by hand, filed under the category name "
                     "zeiss.com gives that page.",
        "filingRule": "Single-product manual capture, not Zeiss's range: one page read by "
                      "hand on 30/09/2026 so this product can publish in the Differentiator. "
                      "Carl Zeiss Ltd's wider range (ophthalmology, surgical microscopes) is "
                      "not captured here; see the curated product list.",
        "divisions": [{"name": DIVISION, "products": 1}],
        "products": [{"n": NAME, "division": DIVISION}],
    }
    save(RANGE, sp)
    print("range: added 1-product record")

# 2. Detail record (the builder's manufacturer source).
dd = json.load(open(DETAIL, encoding="utf-8"))
key = SUPPLIER + "|" + NAME.lower()
if key in dd["products"]:
    print("detail: already present")
else:
    dd["products"][key] = {
        "supplier": SUPPLIER,
        "product": NAME,
        "sourceUrl": URL,
        "capturedDate": DATE,
        "parsed": "structured",
        "description": (
            "ZEISS INTRABEAM 600 enables targeted irradiation of various tumor types. "
            "The X-ray source (XRS) with different applicator types creates a very focused "
            "radiation field. This leads to a targeted local high dose irradiation and "
            "enables increased tumor bed sterilization. A very low radiation scattering "
            "spares healthy structures and organs at risk from radiation reducing unwanted "
            "side-effects in contrary to conventional treatment workflows."
        ),
        "features": [
            "The ZEISS INTRABEAM Spherical Applicator can be used for the intracavitary "
            "intraoperative delivery of radiation to the tumor bed, e.g. at the time of "
            "breast conserving surgery.",
            "The ZEISS INTRABEAM Needle Applicator can be used for the interstitial "
            "irradiation of tumors, e.g. in the treatment of vertebral metastases or brain tumors.",
            "The ZEISS INTRABEAM Flat Applicator can be used for the treatment of the tumor "
            "bed on surgically exposed surfaces, e.g. tumors of the gastrointestinal tract.",
            "The ZEISS INTRABEAM Surface Applicator can be used in the treatment of the tumor "
            "bed on the surface of the body, for example, irradiation of non-melanoma skin cancers.",
        ],
        "image": None,
    }
    save(DETAIL, dd)
    print("detail: added", key)

# 3. product-override map entry (the recorded category decision).
doc = json.load(open(MAP, encoding="utf-8"))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
if (SUPPLIER, NAME) in known:
    print("map: already present")
else:
    doc["entries"].append({
        "supplier": SUPPLIER,
        "division": NAME,
        "products": 1,
        "categories": [],
        "examples": [NAME],
        "hub": HUB,
        "notTaxonomy": False,
        "kind": "product-override",
        "evidence": "zeiss.com's own page for this product (" + URL + ", read 30/09/2026) "
                    "names it an intraoperative radiotherapy system: an X-ray source with "
                    "Spherical, Needle, Flat and Surface applicators irradiating the tumour "
                    "bed during surgery. Carl Zeiss Ltd is named on NHSSC's Radiotherapy "
                    "Treatment Systems contract launch brief.",
        "why": "Radiotherapy treatment capital equipment, not positioning (posn) or "
               "dosimetry/QA (dosim).",
    })
    doc["counts"]["pairs"] = len(doc["entries"])
    save(MAP, doc)
    print("map: added product-override (hub=%s)" % HUB)
