#!/usr/bin/env python3
"""One-off: add rehab:vision, batch 12/09/2026.

Ruling: low-vision assistive/magnification devices (video magnifiers, braille
displays, text-to-speech readers) have no home anywhere in the vocabulary.
Checked and rejected: ophthalmology (a clinical/surgical-department bucket —
these are daily-living aids bought by community/OT/low-vision-clinic teams,
not eye-department surgical or diagnostic equipment) and digital (its five
types are departmental IT/telecare, not personal assistive devices). rehab
already houses exactly this kind of product for a different disability —
`rehab:comms` is AAC/communication aids — so a vision-equivalent type
belongs alongside it, not bolted onto a clinical speciality it does not
serve.

Both copies must move together (verify.py gates them against each other):
  - data/compare-suppliers.json  ("specialities" — the GATED vocabulary)
  - data/differentiator-category-map.json ("vocabulary" — the working copy)

Run once: python3 scripts/_add_vocab_type_rehab_vision_0912.py
"""
import json

NEW_TYPE = {"rehab": {
    "vision": "Low-vision assistive devices (video magnifiers, braille "
              "displays, text-to-speech readers)",
}}

for path, get in (
    ("data/compare-suppliers.json",
     lambda d: {s: v.setdefault("types", {}) for s, v in d["specialities"].items()}),
    ("data/differentiator-category-map.json",
     lambda d: d["vocabulary"]),
):
    doc = json.load(open(path))
    types_by_spec = get(doc)
    added = 0
    for spec, types in NEW_TYPE.items():
        for code, label in types.items():
            if code in types_by_spec[spec]:
                print("%s: %s:%s already present, skipping" % (path, spec, code))
                continue
            types_by_spec[spec][code] = label
            added += 1
    json.dump(doc, open(path, "w"), ensure_ascii=False, indent=1)
    print("%s: added %d type(s)" % (path, added))
