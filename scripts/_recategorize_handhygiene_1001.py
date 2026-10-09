#!/usr/bin/env python3
"""One-off, idempotent: re-file two existing Hand Hygiene framework awardees'
already-captured NHS Supply Chain terms from skin-prep:disinfect into
infection:handhygiene, now that category exists (added 01/10/2026, earlier run
today, differentiator-framework-coverage).

WHY. Both terms' own `why` field already says they were filed under
skin-prep:disinfect only because it was "the closest available skin/hand
disinfectant category" at the time they were decided (NHSSC map sprint
28/08/2026) -- infection:handhygiene ("Hand hygiene (sanitisers & dispensers)",
data/compare-suppliers.json) did not exist yet. Their own catalogue evidence is
alcohol hand rub in bottles, not surgical-site/skin antisepsis, so now that the
correct category exists this is a correction of a since-superseded "closest
available" call, not a new ruling or a guess:

  - Ecolab / "Skinman Soft Protect FF (virucidal hand disinfectant)" --
    examples are "Cleanser alcohol hand rub Liquid Bottle 500ml/100ml" --
    hand rub, not a skin/surgical-site disinfectant.
  - Paul Hartmann (HARTMANN) / "Sterillium med (hand disinfectant)" --
    examples are "Cleanser alcohol hand rub Liquid bottle 1000ml/100ml/500ml"
    -- same thing, Hartmann's own flagship hand-rub brand.

Checked and NOT moved, because their own evidence is genuinely not hand
products (surgical/device antisepsis or surface disinfection, correctly filed
where they are): PDI's Sani-Cloth/Super Sani-Cloth (surface wipes) and
Prevantics (skin/device antiseptic applicators + pre-op scrub, hub is already
a list spanning skin-prep:disinfect + skin-prep:prep); Schulke & Mayr's
Octenisan (antimicrobial body wash/bed-bath/nasal decolonisation, not a hand
product) and mikrozid (sporicidal surface/device wipes); Diversey's Titan
(spillage disinfectant granules). None of these five terms' example lines
describe a hand rub or hand wash.

Does not touch any other framework's or supplier's data. Scope: Hand Hygiene
framework coverage batch, differentiator-framework-coverage, 01/10/2026.

Writes data/differentiator-category-map.json only (seed_format.write_like).
Then run: build_differentiator.py, stamp_notice.py, build_coverage_ledger.py.
Run from the repo root: python3 scripts/_recategorize_handhygiene_1001.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like  # noqa: E402

CMAP = "data/differentiator-category-map.json"
OLD_CAT = "skin-prep:disinfect"
NEW_CAT = "infection:handhygiene"
TARGETS = {
    ("Ecolab", "Skinman Soft Protect FF (virucidal hand disinfectant)"),
    ("Paul Hartmann (HARTMANN)", "Sterillium med (hand disinfectant)"),
}
NOTE = (
    "Recategorised 01/10/2026 (differentiator-framework-coverage, Hand Hygiene "
    "batch): this term's own evidence is alcohol hand rub, filed under "
    "skin-prep:disinfect as \"the closest available\" category on 28/08/2026 "
    "before infection:handhygiene existed. infection:handhygiene was added "
    "01/10/2026; this term now has a correct home."
)


def main():
    cm = json.loads(open(CMAP, "rb").read())
    ents = cm["entries"]
    moved = []
    for e in ents:
        key = (e.get("supplier"), e.get("term"))
        if key in TARGETS and e.get("kind") == "nhssc-term" and e.get("hub") == OLD_CAT:
            e["hub"] = NEW_CAT
            e["_recategorisedFrom"] = OLD_CAT
            e["_recategorisedNote"] = NOTE
            moved.append(key)
    missing = TARGETS - set(moved)
    if missing:
        sys.exit("expected entries not found or already moved: %s" % sorted(missing))
    write_like(CMAP, cm)
    print("category map: %d entries moved %s -> %s: %s" % (
        len(moved), OLD_CAT, NEW_CAT, sorted(moved)))


if __name__ == "__main__":
    main()
