#!/usr/bin/env python3
"""One-off: add anaesthesia:airway, 28/09/2026 (^o285).

Ruling under the standing vocabulary-gap policy (data/identity-vocabulary-policy.json,
20/09/2026) -- add-only, no per-case escalation required. ^o285 is listed in that
policy's appliesTo.

PROMPTED BY: Avicenna Surgical Limited's own-site division "Airways Management"
(laryngoscope blades, reusable laryngoscope handles, laryngeal accessories,
endotracheal accessories), held unmapped because no type fits. The nearest existing
types would be wrong: ent:intub is intubating ENDOSCOPES, respiratory:resp is
respiratory therapy and breathing circuits, anaesthesia:anaes is anaesthesia machines.

NAME SOURCE: NHS Supply Chain's own framework "Airway Management Products and
Associated Equipment" (contract launch brief, supplychain.nhs.uk/product-information/
contract-launch-brief/airways-management/, read 28/09/2026), Lots 1 and 2:
"Laryngoscopes, Video Laryngoscopes, Tracheal Intubation Equipment, Single Use Upper
Airway Devices ..." and "Endotracheal Tubes, Endobronchial Tubes and Blockers,
Tracheostomy Tubes, Supraglottic Airways and Simple Airway Adjuncts"; and Avicenna's
own division wording, "Airways Management".

NOT A DUPLICATE: the label excludes what existing types already hold -- flexible
intubating endoscopes stay ent:intub (Lot 1's endoscope line), breathing systems stay
respiratory:resp (Lot 3), tracheostomy stoma aftercare stays ent:stoma. No existing
type is renamed, merged or re-scoped.

THE OTHER HALF OF ^o285 IS NOT A GAP: Avicenna's "Patient Wear" division (patient
gowns, medical gowns, gynaecological skirt, examination underpants) maps to the
existing workwear:linen, "Bedding, gowns & hospital linen", which already carries
patient gowns, hospital pyjamas and disposable underwear from Interweave Textiles,
Crest Medical and Mediq. Adding a "patient clothing" type would fork that type, which
the policy's guard forbids.

Both copies must move together (verify.py gates them against each other):
  - data/compare-suppliers.json  ("specialities" -- the GATED vocabulary)
  - data/differentiator-category-map.json ("vocabulary" -- the working copy)

Run once: python3 scripts/_add_vocab_type_anaes_airway_0928.py
"""
import json

NEW_TYPE = {"anaesthesia": {
    "airway": "Airway management (laryngoscopes, tracheal intubation equipment, "
              "endotracheal tubes, supraglottic airways and airway adjuncts; not "
              "intubating endoscopes or breathing circuits)",
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
