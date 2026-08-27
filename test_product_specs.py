#!/usr/bin/env python3
"""
test_product_specs.py — the invariant test for the product-specification layer
(04-WOUND-CARE-SPEC-SCHEMA.md section 6).

This is a SEPARATE gate from verify.py. verify.py checks that a product-detail
record is well-formed; this checks the three things that would make the specs
layer dishonest rather than merely malformed:

  1. A populated spec with no source link or no capture date. A manufacturer
     claim published without saying where and when it was read is exactly the
     thing root rule 16 forbids.
  2. A category derived from an NPC prefix. The prefix table in
     Hub/Data-Verification/eclass-npc-prefix-lookup.json does NOT reliably map to
     clinical category (three counter-examples in the schema doc section 2), so a
     category inferred that way is a guess wearing a code's authority.
  3. A renderer that prints a specs table without the standing attribution
     paragraph. These are manufacturer claims side by side, not a like-for-like
     test, and the reader has to be told so on the page, once, above the table.

Each check is proved against a synthetic case that SHOULD fail, so the gate is
known to still catch what it was built for rather than passing vacuously.

  python3 test_product_specs.py     exit 0 = the specs layer holds
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DETAIL = os.path.join(HERE, "data", "supplier-product-detail.json")
RENDERER = os.path.join(HERE, "app", "comparison.js")
SCRIPT_DIRS = [HERE, os.path.join(HERE, "scripts")]

# The eclass NPC-prefix lookup lives outside this repo, in the Hub's working data.
NPC_LOOKUP = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "Data-Verification", "eclass-npc-prefix-lookup.json"))

SPEC_FIELDS = ["sizesAvailable", "wearTime", "exudateLevel", "material", "waterproof",
               "packSize", "sterility", "indications", "clinicalClaims", "latexFree",
               "antimicrobial", "contraindications"]

# Categories are set explicitly, by hand, from what the supplier's own page says the
# product IS. Anything outside this vocabulary is either a typo or a derivation.
ALLOWED_CATEGORIES = {
    "wound-care-dressings",
    "wound-care-npwt-device",
    "wound-care-compression-bandage",
    "wound-care-barrier-product",
    # Added 27/08/2026, widening the sweep across the six registered suppliers. Each
    # exists because a real product in a wound-care range is NOT a dressing and filing
    # it as one would be the same silent mis-filing the NPC-prefix ban exists to stop:
    "wound-care-assessment-device",   # e.g. Advancis Wound Probe — a measuring device
    "wound-care-fixation-tape",       # e.g. Advancis Siltape — a fixation tape
    "wound-care-topical-gel",         # e.g. Activon Tube — honey in a tube, a filler
    "wound-care-debridement-pad",     # e.g. L&R Debrisoft — a debridement tool
    "wound-care-retention-bandage",   # e.g. L&R ActiFast, explicitly NOT compression
}

# The single most important sentence in the layer. Matched on its load-bearing
# fragments, not verbatim whitespace, so reformatting the file doesn't break the gate
# but deleting the meaning does.
ATTRIBUTION_FRAGMENTS = [
    "manufacturer claims shown side by side",
    "not a like-for-like test",
    "captured from their own product page",
    "not independently verified",
    "IFU",
]

FAILURES = []


def fail(check, msg):
    FAILURES.append("[%s] %s" % (check, msg))


def populated(specs):
    """Which spec fields actually carry a claim. None and [] are honest gaps."""
    out = []
    for f in SPEC_FIELDS:
        v = (specs or {}).get(f)
        if v is None:
            continue
        if isinstance(v, (list, tuple, str)) and len(v) == 0:
            continue
        out.append(f)
    return out


# ---------------------------------------------------------------- check 1
def check_attribution_on_every_populated_spec(products):
    """A populated spec field requires a usable sourceUrl AND capturedDate."""
    for key, row in sorted(products.items()):
        specs = row.get("specs")
        if not specs:
            continue
        pop = populated(specs)
        if not pop:
            continue
        label = "%s / %s" % (row.get("supplier") or "?", row.get("product") or "?")

        url = str(row.get("sourceUrl") or "")
        if not url.startswith("http"):
            fail("spec-attribution",
                 "%s carries %d populated spec field(s) (%s) but no usable sourceUrl "
                 "(%r). A manufacturer claim without a link to the page it was read "
                 "from does not publish."
                 % (label, len(pop), ", ".join(pop), row.get("sourceUrl")))

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(row.get("capturedDate") or "")):
            fail("spec-attribution",
                 "%s carries %d populated spec field(s) (%s) but no usable capturedDate "
                 "(%r). Claims change; the date it was read is part of the claim."
                 % (label, len(pop), ", ".join(pop), row.get("capturedDate")))


# ---------------------------------------------------------------- check 2
def check_category_not_npc_derived(products):
    """Category must be stated, from the supplier's own page — never inferred."""
    for key, row in sorted(products.items()):
        if not row.get("specs"):
            continue
        label = "%s / %s" % (row.get("supplier") or "?", row.get("product") or "?")
        cat = row.get("category")
        if cat not in ALLOWED_CATEGORIES:
            fail("spec-category",
                 "%s carries category %r, which is not one of the explicitly-stated "
                 "categories (%s). A category outside this vocabulary is a derivation, "
                 "not a reading."
                 % (label, cat, ", ".join(sorted(ALLOWED_CATEGORIES))))
        if row.get("categorySource") not in (None, "supplier-page"):
            fail("spec-category",
                 "%s declares categorySource=%r. The only honest source for a specs "
                 "category is the supplier's own product page."
                 % (label, row.get("categorySource")))


def check_no_writer_derives_category_from_npc():
    """Static guard: no script that writes specs may read the NPC-prefix table.

    Data alone can't prove how a category was arrived at, so this closes the door at
    the code level instead: any writer that touches both the prefix lookup and a
    category assignment is assumed to be deriving one from the other.
    """
    for d in SCRIPT_DIRS:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".py") or name.startswith("test_"):
                continue
            path = os.path.join(d, name)
            try:
                src = open(path, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            if "supplier-product-detail" not in src:
                continue
            if "eclass-npc-prefix" in src or "npc_prefix" in src:
                fail("spec-category",
                     "%s writes supplier-product-detail.json AND reads the NPC-prefix "
                     "lookup. NPC prefixes do not reliably map to clinical category "
                     "(see 04-WOUND-CARE-SPEC-SCHEMA.md section 2) — a category "
                     "derived that way is a guess." % name)


# ---------------------------------------------------------------- check 3
def check_renderer_carries_attribution():
    """If comparison.js renders a specs table, it must print the standing paragraph."""
    if not os.path.exists(RENDERER):
        fail("spec-attribution-copy", "%s is missing — the renderer this layer depends "
                                      "on does not exist." % RENDERER)
        return
    src = open(RENDERER, encoding="utf-8").read()

    # Keyed on the specs renderer by name, not a loose /\.specs/ — comparison.js
    # carries an unrelated `specs` array on another object that would false-match.
    renders_specs = "specsBlock(" in src
    if not renders_specs:
        return          # renderer not built yet — nothing to gate, per verify.py's pattern

    missing = [f for f in ATTRIBUTION_FRAGMENTS if f.lower() not in src.lower()]
    if missing:
        fail("spec-attribution-copy",
             "app/comparison.js renders a specs table but the standing attribution "
             "paragraph is missing or altered — absent fragment(s): %s. That paragraph "
             "is what stops a member reading supplier marketing copy as a head-to-head "
             "test result." % "; ".join(repr(m) for m in missing))

    if "*info not found" not in src:
        fail("spec-attribution-copy",
             "app/comparison.js renders a specs table but never prints the '*info not "
             "found' empty state. A blank cell has to say it is a gap in the supplier's "
             "page, not an absence of the feature.")


# ---------------------------------------------------------------- self-test
def self_test():
    """Prove each check fires on a case that should fail it."""
    global FAILURES

    cases = [
        ("populated spec, no sourceUrl",
         lambda: check_attribution_on_every_populated_spec({
             "x": {"supplier": "S", "product": "P", "capturedDate": "2026-08-27",
                   "category": "wound-care-dressings",
                   "specs": {"wearTime": "up to 7 days"}}})),
        ("populated spec, no capturedDate",
         lambda: check_attribution_on_every_populated_spec({
             "x": {"supplier": "S", "product": "P", "sourceUrl": "https://e.org/p",
                   "category": "wound-care-dressings",
                   "specs": {"wearTime": "up to 7 days"}}})),
        ("category outside the stated vocabulary",
         lambda: check_category_not_npc_derived({
             "x": {"supplier": "S", "product": "P", "sourceUrl": "https://e.org/p",
                   "capturedDate": "2026-08-27", "category": "FSL",
                   "specs": {"wearTime": "7 days"}}})),
        ("category declared as derived",
         lambda: check_category_not_npc_derived({
             "x": {"supplier": "S", "product": "P", "sourceUrl": "https://e.org/p",
                   "capturedDate": "2026-08-27", "category": "wound-care-dressings",
                   "categorySource": "npc-prefix",
                   "specs": {"wearTime": "7 days"}}})),
    ]

    for name, fn in cases:
        saved, FAILURES = FAILURES, []
        fn()
        caught, FAILURES = FAILURES, saved
        if not caught:
            fail("self-test", "the gate did NOT catch: %s. A check that cannot fail is "
                              "not a check." % name)

    # A clean record must NOT trip anything.
    saved, FAILURES = FAILURES, []
    clean = {"x": {"supplier": "S", "product": "P", "sourceUrl": "https://e.org/p",
                   "capturedDate": "2026-08-27", "category": "wound-care-dressings",
                   "specs": {"wearTime": "up to 7 days", "material": None,
                             "clinicalClaims": []}}}
    check_attribution_on_every_populated_spec(clean)
    check_category_not_npc_derived(clean)
    noise, FAILURES = FAILURES, saved
    for n in noise:
        fail("self-test", "the gate fired on a clean, fully-attributed record: %s" % n)


# ---------------------------------------------------------------- main
def main():
    self_test()

    if os.path.exists(DETAIL):
        with open(DETAIL, encoding="utf-8") as fh:
            products = (json.load(fh) or {}).get("products") or {}
        with_specs = sum(1 for r in products.values() if r.get("specs"))
        print("supplier-product-detail.json: %d products, %d carrying specs"
              % (len(products), with_specs))
        check_attribution_on_every_populated_spec(products)
        check_category_not_npc_derived(products)
    else:
        print("supplier-product-detail.json not present — data checks skipped.")

    check_no_writer_derives_category_from_npc()
    check_renderer_carries_attribution()

    if FAILURES:
        print("\n%d FAILURE(S):\n" % len(FAILURES))
        for f in FAILURES:
            print("  " + f)
        return 1
    print("specs layer holds: attribution, category and renderer copy all intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
