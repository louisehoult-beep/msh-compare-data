#!/usr/bin/env python3
"""One-off: add ortho:inject, framework-coverage batch 27/09/2026.

Ruling under the standing vocabulary-gap policy (data/identity-vocabulary-policy.json,
20/09/2026) -- add-only, no per-case escalation required.

TRB Chemedica (UK) Ltd (own-site crawl, trbchemedica.co.uk) is a confirmed, real range
of hyaluronic-acid viscosupplementation and regenerative injectable products for joint
and soft-tissue care -- OSTENIL / OSTENIL PLUS / OSTENIL MINI / OSTENIL TENDON (sodium
hyaluronate joint and tendon injections), ArthroZheal (R) (autologous bioactive matrix
for arthroscopic cartilage/tendon/ligament repair) and VISCOSEAL (hyaluronan solution
used after arthroscopy/joint lavage) -- but the ortho vocabulary has no matching type:
cement/implant/trauma/equip/brace are all a device, a fixation product or a piece of
equipment, none of them an injectable. The Total Orthopaedic Solutions 3 framework's own
routeNote already names this as one of Lot 1's 12 sub-lots: "regenerative technology".

Named from the framework's own language (NHS Supply Chain's "regenerative technology"
sub-lot, data/compare-suppliers.json specialities.ortho.routeNote).

Both copies must move together (verify.py gates them against each other):
  - data/compare-suppliers.json  ("specialities" -- the GATED vocabulary)
  - data/differentiator-category-map.json ("vocabulary" -- the working copy)

Run once: python3 scripts/_add_vocab_type_ortho_inject_0927.py
"""
import json

NEW_TYPE = {"ortho": {
    "inject": "Regenerative technology & injections (viscosupplementation, "
              "autologous/bioactive matrices)",
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
