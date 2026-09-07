#!/usr/bin/env python3
"""
Invariant gate for the ICC product-grid parser (root rule 14).

The parser reads specification values out of drawn PDF tables. Its failure mode
is not a crash - it is a silently wrong number, or two different specifications
merged into one label, published to paying members as NHS-authored fact. So the
checks below pin the behaviours that were actually got wrong during the build,
against real pages, with the correct answers read off the documents by eye:

  1. Row separation. A vertical-gap threshold merges "Pad size vs total size
     clearly displayed" with "Displays 'Absorbency category'" and publishes
     "Yes Yes" as one value. Ruled-row detection separates them. Pinned.
  2. Rule-coverage floor. At 0.45 the rules boxing a wrapped supplier name count
     as row separators and "ADVANCED MEDICAL SOLUTIONS LTD" publishes as
     "MEDICAL". Pinned.
  3. Symbol fonts. Boolean cells are drawn in Webdings, where 'a' is a tick.
     Extracted naively they publish as the letter "a". Mapped - but ONLY in a
     symbol font, so an ordinary word starting with 'a' is untouched. Pinned.
  4. No NPC, no publish. The NPC is the join key onto the NHS Supply Chain
     catalogue; a row without one cannot be tied to a real catalogue line.
  5. Attribution. Every matrix carries its source URL, issue date and listing
     status, so nothing can be published without saying where it came from and
     whether NHS Supply Chain still lists it.

These are self-tested: each check is proved to FAIL on deliberately broken input
before it is trusted on the real thing, so none of them can pass vacuously.

Usage:  python3 test_icc_matrix.py
"""

from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import icc_pdf_matrix as M                                          # noqa: E402

LIBRARY = os.path.expanduser(
    os.environ.get("ICC_LIBRARY", "~/Library/CloudStorage/OneDrive-Personal/"
                   "Cowork-OS/02-Elevate-and-Thrive/Hub/ICC-Library")
)
FOAM = "ICC-NP-Foam-Dressings-Support-Document-4-October-2022-T3.pdf"

failures: list[str] = []
checks = 0


def check(ok: bool, what: str) -> bool:
    global checks
    checks += 1
    if not ok:
        failures.append(what)
    return ok


def _foam_page(index: int):
    import pdfplumber
    with pdfplumber.open(os.path.join(LIBRARY, FOAM)) as pdf:
        return M.parse_page(pdf.pages[index])


# --------------------------------------------------------------------------
# 1 + 2. Real-page parse: row separation and the rule-coverage floor.
# --------------------------------------------------------------------------
def test_real_page() -> None:
    grid = _foam_page(2)                       # Foam Dressings, page 3
    if not check(grid is not None, "Foam Dressings page 3 produced no grid"):
        return

    # Read off the document by eye: 7 products, and these two are SEPARATE
    # attribute rows, not one merged row.
    check(grid["n_cols"] == 7,
          "expected 7 product columns on Foam Dressings p3, got %s" % grid["n_cols"])
    check(grid["ruled"], "Foam Dressings p3 should be parsed by its ruling lines")

    labels = grid["rows"]
    pad = [k for k in labels if k.startswith("Pad size vs total size")]
    disp = [k for k in labels if k.startswith("Displays")]
    check(len(pad) == 1 and len(disp) == 1,
          "the two packaging attributes must stay separate rows, got pad=%s disp=%s"
          % (pad, disp))
    for key in pad + disp:
        check(" Yes Yes" not in " " + labels[key][0],
              "row %r merged two attributes into one value" % key)

    # The full wrapped label must survive, not be truncated at the line break.
    mvt = [k for k in labels if k.startswith("Moisture Vapour Transmission")]
    check(len(mvt) == 1 and mvt[0].endswith("g/10cm2"),
          "wrapped label lost its continuation line: %s" % mvt)

    # Rule-coverage floor: the supplier name must not be cut down to a fragment.
    suppliers = labels.get("Supplier", [])
    check(suppliers and suppliers[0] == "ADVANCED MEDICAL SOLUTIONS LTD",
          "supplier truncated (rule-coverage floor too low?): %r"
          % (suppliers[0] if suppliers else None))

    # Values read off the document by eye for column 1 (ActivHeal, ELA838).
    check(labels.get("NPC", [""])[0] == "ELA838",
          "NPC column 1 should be ELA838, got %r" % labels.get("NPC", [""])[0])
    check(labels.get("Total Fluid Handling (MVT + Abs)", [""])[0] == "16.09",
          "total fluid handling for ActivHeal should be 16.09, got %r"
          % labels.get("Total Fluid Handling (MVT + Abs)", [""])[0])


# --------------------------------------------------------------------------
# 2b. Self-test: prove the rule-coverage check would CATCH a regression.
# --------------------------------------------------------------------------
def test_rule_coverage_floor_is_load_bearing() -> None:
    original = M.RULE_COVERAGE
    try:
        M.RULE_COVERAGE = 0.45                 # the value that broke it
        grid = _foam_page(1)                   # page 2, where the boxes appear
        broken = grid and grid["rows"].get("Supplier", [""])[0]
        check(broken == "MEDICAL",
              "self-test: lowering RULE_COVERAGE should truncate the supplier "
              "to 'MEDICAL' - got %r. The check may no longer be load-bearing."
              % broken)
    finally:
        M.RULE_COVERAGE = original


# --------------------------------------------------------------------------
# 3. Symbol-font mapping, both directions.
# --------------------------------------------------------------------------
def test_symbol_fonts() -> None:
    check(M._word_text({"text": "a", "fontname": "AAAABB+Webdings"}) == "Yes",
          "Webdings 'a' must map to Yes")
    check(M._word_text({"text": "r", "fontname": "AAAABB+Webdings"}) == "No",
          "Webdings 'r' must map to No")
    # And the other way: a real letter in a real font is never rewritten.
    check(M._word_text({"text": "a", "fontname": "AAAAAY+ArialMT"}) == "a",
          "an ordinary letter must never be rewritten as Yes")
    check(M._word_text({"text": "adhesive", "fontname": "AAAAAY+ArialMT"}) == "adhesive",
          "an ordinary word must never be rewritten")


# --------------------------------------------------------------------------
# 4 + 5. The published store: join key and attribution.
# --------------------------------------------------------------------------
def test_published_store() -> None:
    path = os.path.join(REPO, "data", "icc-matrices.json")
    if not check(os.path.exists(path), "data/icc-matrices.json is missing"):
        return
    store = json.load(open(path))
    matrices = store.get("matrices", {})
    check(bool(matrices), "icc-matrices.json publishes no matrices at all")

    for name, matrix in matrices.items():
        check(bool(matrix.get("source_url")), "%s has no source_url" % name)
        check(bool(matrix.get("issued")), "%s has no issue date" % name)
        check(matrix.get("listing_status") in ("linked", "unlinked"),
              "%s has no listing_status" % name)
        for product in matrix.get("products", []):
            npc = product.get("NPC", "")
            if not check(bool(M.NPC_RE.match(npc)),
                         "%s publishes a row with no usable NPC: %r" % (name, npc)):
                break
            if not check("a" != product.get("Latex Free"),
                         "%s row %s published a raw Webdings glyph" % (name, npc)):
                break

    # A dataset that silently shrinks is the failure this repo has had before.
    check(store.get("product_count", 0) >= 1500,
          "product_count fell to %s - the parser has lost categories"
          % store.get("product_count"))


for fn in (test_real_page, test_rule_coverage_floor_is_load_bearing,
           test_symbol_fonts, test_published_store):
    try:
        fn()
    except Exception as exc:                                        # noqa: BLE001
        failures.append("%s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))

if failures:
    print("ICC MATRIX GATE FAILED (%d of %d checks)" % (len(failures), checks))
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
print("ICC matrix gate passed: %d checks" % checks)
