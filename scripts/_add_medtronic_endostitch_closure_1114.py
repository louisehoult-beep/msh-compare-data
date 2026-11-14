#!/usr/bin/env python3
"""One-off category fix, framework-coverage batch 14/11/2026.

Medtronic's NHS Supply Chain catalogue term "V-Loc / Endo Stitch (wound
closure / endoscopic suturing)" has never had a (supplier, term) category
decision -- it holds two items of two different genuine types, so a single
blanket category for the whole term would misfile one of them:

  - FSH86567 "ENDO CLIP", desc "Single Load Clip Appliers Minimal Access
    Endo 33cm Shaft 5mm Clips" -- a clip applier, matching the Hub's existing
    mis:clips category (the same type used for other MIS clip appliers,
    e.g. TFX Group's Weck Hem-o-lok clip applier).
  - FGP199 "Auto Suture Endostitch", desc "Laparoscopic Suturing endo stitch
    instrument x3" -- a genuine endoscopic suturing instrument, matching
    closure:sutures (Wound Closure framework).

Added as two product-override entries, keyed on each item's own nhsscName
(opt-in, additive -- see build_differentiator.py's comment on this tier),
per the mixed-division-mapping policy (data/identity-vocabulary-policy.json):
map at product level where the product's own name/description is
unambiguous, never blanket the whole term.

Run once: python3 scripts/_add_medtronic_endostitch_closure_1114.py
"""
import json

PATH = "data/differentiator-category-map.json"

ENTRIES = [
    {
        "kind": "product-override",
        "supplier": "Medtronic",
        "division": "ENDO CLIP",
        "products": 1,
        "categories": [],
        "examples": ["Single Load Clip Appliers Minimal Access Endo 33cm Shaft 5mm Clips"],
        "hub": "mis:clips",
        "notTaxonomy": False,
        "evidence": (
            "NHS Supply Chain public catalogue, cached by scripts/refresh_nhssc_cache.py, "
            "term \"V-Loc / Endo Stitch (wound closure / endoscopic suturing)\" under "
            "Medtronic: NPC FSH86567, nhsscName \"ENDO CLIP\"."
        ),
        "why": (
            "A single-load clip applier, the same product type as other MIS clip "
            "appliers already filed under mis:clips (e.g. TFX Group Ltd's Weck "
            "Hem-o-lok clip applier). Not a wound-closure item."
        ),
        "decidedIn": "Wound Closure framework-coverage batch 14/11/2026",
    },
    {
        "kind": "product-override",
        "supplier": "Medtronic",
        "division": "Auto Suture Endostitch",
        "products": 1,
        "categories": [],
        "examples": ["Laparoscopic Suturing endo stitch instrument x3"],
        "hub": "closure:sutures",
        "notTaxonomy": False,
        "evidence": (
            "NHS Supply Chain public catalogue, cached by scripts/refresh_nhssc_cache.py, "
            "term \"V-Loc / Endo Stitch (wound closure / endoscopic suturing)\" under "
            "Medtronic: NPC FGP199, nhsscName \"Auto Suture Endostitch\"."
        ),
        "why": (
            "A genuine endoscopic suturing instrument -- the term's own name "
            "(\"wound closure / endoscopic suturing\") and the item's description "
            "both confirm it. Matches closure:sutures (Wound Closure framework)."
        ),
        "decidedIn": "Wound Closure framework-coverage batch 14/11/2026",
    },
]

doc = json.load(open(PATH))
existing = {(e.get("supplier"), e.get("division")) for e in doc["entries"]}
added = 0
for entry in ENTRIES:
    key = (entry["supplier"], entry["division"])
    if key in existing:
        continue
    doc["entries"].append(entry)
    added += 1

if not added:
    raise SystemExit("already present, aborting")

with open(PATH, "w") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=False)
    f.write("\n")
print("added", added, "Medtronic override(s), total entries:", len(doc["entries"]))
