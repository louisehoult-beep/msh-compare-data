#!/usr/bin/env python3
"""One-off: add 6 new vocabulary types, batch 12/09/2026.

Each was found genuinely missing during a review of the "no category fits"
backlog — a real product-family gap, not a division that could already be
mapped. Every one was verified against the supplier's own live category page
before being proposed; see the batch report for evidence.

Both copies must move together (verify.py gates them against each other):
  - data/compare-suppliers.json  ("specialities" — the GATED vocabulary)
  - data/differentiator-category-map.json ("vocabulary" — the working copy
    agents read; verify.py's check_differentiator() diffs the two)

Run once: python3 scripts/_add_vocab_types_0912.py
"""
import json

NEW_TYPES = {
    "rehab": {
        "mounts": "Mounting systems for communication aids & assistive "
                  "technology (wheelchair, table & floor mounts)",
        "sensory": "Multi-sensory environment & interactive sensory room "
                   "equipment",
    },
    "womens": {
        "period": "Period care (tampons, sanitary pads & panty liners)",
    },
    "theatres": {
        "sharps": "Intra-operative sharps safety devices",
    },
    "imaging": {
        "dxa": "DXA / bone densitometry scanners",
        "pet": "Molecular imaging / PET-CT scanners",
    },
}

for path, get in (
    ("data/compare-suppliers.json",
     lambda d: {s: v.setdefault("types", {}) for s, v in d["specialities"].items()}),
    ("data/differentiator-category-map.json",
     lambda d: d["vocabulary"]),
):
    doc = json.load(open(path))
    types_by_spec = get(doc)
    added = 0
    for spec, types in NEW_TYPES.items():
        for code, label in types.items():
            if code in types_by_spec[spec]:
                print("%s: %s:%s already present, skipping" % (path, spec, code))
                continue
            types_by_spec[spec][code] = label
            added += 1
    json.dump(doc, open(path, "w"), ensure_ascii=False, indent=1)
    print("%s: added %d type(s)" % (path, added))
