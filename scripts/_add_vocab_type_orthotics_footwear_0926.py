#!/usr/bin/env python3
"""One-off: add orthotics:footwear, framework-coverage batch 26/09/2026.

Ruling under the standing vocabulary-gap policy (data/identity-vocabulary-policy.json,
20/09/2026) -- add-only, no per-case escalation required.

Piedro Ltd (own-site crawl, piedro-uk.co.uk, 252 products across 5 divisions) is a
confirmed, real range of orthopaedic and therapeutic footwear -- exactly the kind of
product the "Orthotics, Podiatry and Immobilisation" NHS Supply Chain framework awards,
but the orthotics vocabulary has no matching type: afo/brace/hosiery/insole/materials/
paed/podinstr/prosth/spine/upper are all either a device, a material or an instrument,
none of them a finished shoe. The nearest existing type (insole) would be actively wrong
-- these are whole orthopaedic shoes, not insoles fitted inside a patient's own footwear.
Already flagged as an open gap in docs/framework-coverage-findings-2026-09-23-orthotics-lab-diagnostics.md
(Thesis Technology Products Ltd's cast-protection range surfaced the same missing
"Immobilisation" vocabulary; this is the footwear half of the same framework-name gap).

Named from the framework's own language ("Orthotics, Podiatry and Immobilisation") and
NHS Supply Chain's own sub-lot term for this product class, "orthopaedic footwear".

Both copies must move together (verify.py gates them against each other):
  - data/compare-suppliers.json  ("specialities" -- the GATED vocabulary)
  - data/differentiator-category-map.json ("vocabulary" -- the working copy)

Run once: python3 scripts/_add_vocab_type_orthotics_footwear_0926.py
"""
import json

NEW_TYPE = {"orthotics": {
    "footwear": "Orthopaedic and therapeutic footwear (finished shoes, not insoles "
                "fitted inside a patient's own footwear)",
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
