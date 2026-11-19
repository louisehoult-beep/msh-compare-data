#!/usr/bin/env python3
"""One-off category fix, framework-coverage batch 14/11/2026.

The existing (supplier, term) map entry for TFX Group Ltd (Teleflex Medical)'s
"Weck Hem-o-lok clips" NHSSC catalogue term already flagged a gap in its own
`why` field (NHSSC map sprint 28/08/2026): "note two skin-stapler items don't
clearly fit either [mis:clips or mis:instruments] and no hem-o-lok clip itself
appears." Three of its seven items carry nhsscName "Weck Visistat" (NPCs
FGS358, FGS098, FGS437) and are genuinely skin staplers / a skin-staple
remover -- not clip appliers or specimen-retrieval bags. Wound Closure did not
exist as a speciality until 12/11/2026
(scripts/_add_wound_closure_speciality_1112.py), so this gap had nowhere to
go before now.

Adds a product-override entry (opt-in, additive -- see build_differentiator.py's
own comment on this tier) keyed on nhsscName "Weck Visistat" under this
supplier, mapping just those three items to closure:stapler. The clip
applier ("Weck") and the three specimen-retrieval bags ("Teleflex/Weck")
keep their existing mis:clips/mis:instruments categories untouched -- product-
level mapping per the mixed-division-mapping policy
(data/identity-vocabulary-policy.json).

Run once: python3 scripts/_add_weck_visistat_stapler_override_1114.py
"""
import json

PATH = "data/differentiator-category-map.json"

ENTRY = {
    "kind": "product-override",
    "supplier": "TFX Group Ltd (Teleflex Medical)",
    "division": "Weck Visistat",
    "products": 3,
    "categories": [],
    "examples": [
        "Stapler skin disposable single patient use 35 Regular Staples",
        "Stapler skin disposable single patient use 35 Wide Staples",
        "Skin staple remover Single Use",
    ],
    "hub": "closure:stapler",
    "notTaxonomy": False,
    "evidence": (
        "NHS Supply Chain public catalogue, cached by scripts/refresh_nhssc_cache.py, "
        "term \"Weck Hem-o-lok clips\" under TFX Group Ltd (Teleflex Medical): NPCs "
        "FGS358, FGS098, FGS437, all carrying nhsscName \"Weck Visistat\" -- Weck "
        "Visistat Stapler skin disposable (35 Regular Staples, 35 Wide Staples) and "
        "the matching Skin staple remover."
    ),
    "why": (
        "These three items are genuinely skin staplers and a skin-staple remover, "
        "matching the existing closure:stapler category exactly (Wound Closure "
        "framework, framework-coverage batch 14/11/2026). The parent (supplier, term) "
        "entry for \"Weck Hem-o-lok clips\" already flagged these as not fitting its "
        "own mis:clips/mis:instruments categories (\"note two skin-stapler items "
        "don't clearly fit either and no hem-o-lok clip itself appears\") -- this "
        "override resolves that flagged gap at product level, per the "
        "mixed-division-mapping policy (data/identity-vocabulary-policy.json), "
        "leaving the clip applier and specimen-retrieval bags on their existing "
        "categories."
    ),
    "decidedIn": "Wound Closure framework-coverage batch 14/11/2026",
}

doc = json.load(open(PATH))
dupes = [e for e in doc["entries"]
         if e.get("supplier") == ENTRY["supplier"] and e.get("division") == ENTRY["division"]]
if dupes:
    raise SystemExit("already present, aborting")

doc["entries"].append(ENTRY)
with open(PATH, "w") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=False)
    f.write("\n")
print("added Weck Visistat -> closure:stapler override, total entries:", len(doc["entries"]))
