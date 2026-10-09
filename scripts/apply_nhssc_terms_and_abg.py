#!/usr/bin/env python3
"""Apply two accepted, queued changes to the category data (07/09/2026, Lou's
sign-off): the Boston Scientific / Avanos / J&J nhssc-term proposals, and the
bloodcoll:abg vocabulary code.

    ./begin.sh "apply-nhssc-terms-and-abg-code"            # gives you a clone, cd into it
    python3 scripts/apply_nhssc_terms_and_abg.py           # dry run
    python3 scripts/apply_nhssc_terms_and_abg.py --write
    python3 scripts/build_differentiator.py
    python3 scripts/stamp_notice.py
    python3 verify.py
    ./land.sh "..." data/...

⚠️ RUN AND VERIFIED 07/09/2026 — NEITHER CHANGE IS LIVE YET. Both are correctly
recorded in git and pass every check, but neither currently changes what a
single product's `cat` is, for two separate reasons discovered by testing this
script's own output rather than assuming it worked:

  - CHANGE 1's `term` values are descriptive labels an agent wrote, not real
    keys in data/nhssc-cache.json's `products` dict. build_differentiator.py's
    nhssc-term lookup only fires on an EXACT match to a cached search term
    (confirmed: "Promus", "Wallstent", "Victory" etc. return zero hits in the
    cache). These 14 entries need real NHS Supply Chain search terms — either
    found by searching the cache for the actual family names, or a live crawl
    for terms that genuinely aren't cached yet — before they do anything.

  - CHANGE 2's per-product override collides with build_differentiator.py's
    existing precedence: `mapped.get((co, div)) or mapped.get((co, name))`
    means the division match ("Infusion Therapy" -> vascular:conn, which
    covers 76 OTHER real IV-connector products) always wins over the
    product-name match, because `or` never evaluates the second operand once
    the first is truthy. Reordering that precedence looked like the fix, but a
    check found hundreds of existing (supplier, division) entries where the
    division string already equals a product's own name for OTHER products
    (the DHG/Talley flattened-crawl shape this file's own comment describes) —
    reordering globally was not verified safe against that number of cases in
    the time available, so it was NOT done blind. This needs either a real
    per-product override field the builder checks before the division map, or
    a case-by-case check that reordering is safe for these six suppliers only.

BOTH ARE RECORDED HONESTLY: the entries are real accepted decisions with real
evidence, kept in git as the source of truth for when the mechanism exists,
not deleted for having no effect yet. Do not assume a future re-run of this
script makes them live — check `differentiator.json` directly, the way this
comment's own investigation did.

CHANGE 1 — 14 nhssc-term ENTRIES (Boston Scientific 11, Avanos 1, J&J 2)
--------------------------------------------------------------------------
Proposed by two read-only agents 07/09/2026, each grouping a supplier's
suspended NHS Supply Chain lines by real catalogue family and mapping the
coherent ones to a single gated category, refusing the rest. Every `hub`
value is re-validated here against the live gated vocabulary before writing —
never trust a proposal file's own claim.

WHY BOSTON SCIENTIFIC'S OWN 176 LINES DID NOT NEED THIS: measured 07/09/2026,
132 of 176 already show alternatives, because a suspended line needs a
COMPETITOR's products in its category, not its own supplier's. These entries
exist for the other direction — they put Boston Scientific's OWN products into
the Differentiator with a real category, so they become available as
alternatives when a DIFFERENT supplier's line goes out of stock. That is a
real and separate improvement to the alternatives pool, which is why Lou chose
to accept them even though they were not required to close Boston's own gap.

CHANGE 2 — bloodcoll:abg
--------------------------
6 real ICU Medical arterial-blood-gas products (Pro Vent Plus, Pulsator,
Linedraw) are published today under `vascular:conn`, filed there alongside IV
connectors because no arterial-sampling code existed. Confirmed by direct
inspection of differentiator.json 07/09/2026, not taken on an agent's word —
a separate proposed code, dermatology:biopsy-punch, did NOT survive the same
check (what the data actually holds there is surgical punch forceps) and is
deliberately NOT included here.

This adds `bloodcoll:abg` to the gated vocabulary in BOTH files that must
agree (differentiator-category-map.json's own copy, and compare-suppliers.json,
the authoritative source verify.py's check_differentiator cross-checks
against), and re-homes the 6 mis-filed nhssc-term entries from vascular:conn.

ELEVEN OTHER PROPOSED CODES ARE DELIBERATELY EXCLUDED. vocabulary-gaps.md
found they have ZERO existing products behind them (EP catheters, PTA/coronary
balloons, embolisation coils, tendon instruments...). Adding an empty category
unlocks nothing and is not part of this change.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PROPOSALS_DIR = ("/Users/louisehoult/Library/CloudStorage/OneDrive-Personal/Cowork-OS/"
                  "02-Elevate-and-Thrive/Hub/eclass-mapping-2026-09-07")
CATMAP = os.path.join(REPO, "data", "differentiator-category-map.json")
COMPARE_SUPPLIERS = os.path.join(REPO, "data", "compare-suppliers.json")

# --------------------------------------------------------------------- change 2
NEW_SPEC, NEW_TYPE = "bloodcoll", "abg"
NEW_CODE = "%s:%s" % (NEW_SPEC, NEW_TYPE)
NEW_TYPE_LABEL = "Arterial blood gas sampling"
REHOME_NAME_MATCH = ("pro vent plus", "pulsator plus", "linedraw")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def add_vocab_code_flat(catmap):
    """differentiator-category-map.json's own vocabulary copy: {spec: {type: label}}."""
    vocab = catmap.setdefault("vocabulary", {})
    spec = vocab.setdefault(NEW_SPEC, {})
    if NEW_TYPE in spec:
        return False
    spec[NEW_TYPE] = NEW_TYPE_LABEL
    return True


def add_vocab_code_specialities(compare_suppliers):
    """compare-suppliers.json — the AUTHORITATIVE vocabulary source
    build_differentiator.py actually reads (`load("data/compare-suppliers.json")
    ["specialities"]`). Shape is DIFFERENT from the file above:
    specialities[spec]['types'][type] = label. Getting this shape wrong means
    the code silently never becomes legal — build_differentiator.py holds every
    product tagged with it rather than erroring, so the mistake is invisible
    until someone checks whether the products actually moved. Confirmed
    07/09/2026 after exactly that happened on the first run of this script.
    """
    spec = compare_suppliers.get("specialities", {}).get(NEW_SPEC)
    if spec is None:
        raise SystemExit("ABORT: speciality '%s' not found in compare-suppliers.json "
                         "specialities — cannot add a type under a speciality that "
                         "doesn't exist. This script only adds a TYPE to an EXISTING "
                         "speciality." % NEW_SPEC)
    types = spec.setdefault("types", {})
    if NEW_TYPE in types:
        return False
    types[NEW_TYPE] = NEW_TYPE_LABEL
    return True


def apply_entries(catmap, write):
    existing = {(e.get("supplier"), e.get("term")) for e in catmap["entries"]
                if e.get("kind") == "nhssc-term"}
    legal = set()
    for spec, types in (catmap.get("vocabulary") or {}).items():
        for t in (types or {}):
            legal.add("%s:%s" % (spec, t))
    legal.add(NEW_CODE)  # will exist once change 2 is applied in the same run

    added, skipped, refused = [], [], []
    for fname in ("nhssc-terms-boston.json", "nhssc-terms-avanos-jj.json"):
        path = os.path.join(PROPOSALS_DIR, fname)
        if not os.path.exists(path):
            print("  (missing %s — skipping)" % fname)
            continue
        doc = load(path)
        for e in doc.get("entries") or []:
            key = (e.get("supplier"), e.get("term"))
            if key in existing:
                skipped.append(key)
                continue
            hub = e.get("hub")
            if hub not in legal:
                refused.append((key, hub, "not in gated vocabulary"))
                continue
            entry = {
                "kind": "nhssc-term",
                "supplier": e["supplier"],
                "term": e["term"],
                "division": None,
                "products": e.get("products", 0),
                "categories": [],
                "examples": (e.get("examples") or [])[:8],
                "hub": hub,
                "notTaxonomy": False,
                "evidence": e.get("evidence") or (
                    "NHS Supply Chain public catalogue, cached by scripts/refresh_nhssc_cache.py; "
                    "decision made on the catalogue's own item descriptions above"),
                "why": e.get("why") or e.get("reasoning") or "",
                "decidedIn": "nhssc-term batch, accepted by Lou 07/09/2026",
            }
            added.append(entry)
            existing.add(key)
    if write:
        catmap["entries"].extend(added)
    return added, skipped, refused


ABG_SUPPLIER = "ICU Medical (incl. Smiths Medical)"
ABG_PRODUCTS = (
    "Pro Vent Plus 1 Ml Syringe Dry Lithium Heparin",
    "Pro Vent Plus 3 Ml Dry Lithium Low Heparin",
    "Pulsator Plus Arterial Blood Sampling Kits Dry Lithium Heparin",
    "Pro Vent Plus 1 Ml Syringe Dry Lithium Low Heparin",
    "Linedraw Arterial Blood Sampling Kits",
    "Pro Vent Plus 3 Ml Syringe Dry Lithium Heparin",
)


def rehome_abg(catmap, write):
    """Confirmed 07/09/2026 by direct inspection of differentiator.json: these 6
    products sit inside ICU Medical's 82-product "Infusion Therapy" division,
    which is mapped whole to vascular:conn (IV connectors, stopcocks, extension
    sets). Re-homing the whole division would be wrong — 76 of its 82 products
    genuinely are IV connector accessories. Re-homing nothing leaves 6 arterial
    blood-gas sampling kits filed as IV connectors, which is also wrong.

    build_differentiator.py already has the fix for exactly this shape of
    problem: `mapped.get((co, div)) or mapped.get((co, name))` (see its own
    26/08/2026 DHG/Talley comment) falls back to a (supplier, PRODUCT NAME)
    match when no division match exists. So this adds one category-map entry
    per product, `division` set to the product's own exact name — no new
    mechanism, just this file's existing one, applied at the product level
    instead of the division level, which is what a real per-product exception
    is supposed to look like.
    """
    already = {(e.get("supplier"), e.get("division")) for e in catmap["entries"]}
    added = []
    for name in ABG_PRODUCTS:
        key = (ABG_SUPPLIER, name)
        if key in already:
            continue
        added.append(name)
        if write:
            catmap["entries"].append({
                "kind": "product-exact-name",
                "supplier": ABG_SUPPLIER,
                "division": name,
                "products": 1,
                "categories": [],
                "examples": [name],
                "hub": NEW_CODE,
                "notTaxonomy": False,
                "evidence": "the supplier's own site filing, read by scripts/crawl_supplier_site.py; "
                            "this product was found 07/09/2026 filed under the Infusion Therapy division "
                            "(mapped to vascular:conn), which is right for the division's other 76 products "
                            "but wrong for this one",
                "why": "Arterial blood-gas sampling kit, not an IV connector. The Infusion Therapy "
                       "division mapping is correct for the rest of the division; this product needed "
                       "its own decision, which build_differentiator.py's existing (supplier, product "
                       "name) fallback already supports.",
                "decidedIn": "bloodcoll:abg addition, accepted by Lou 07/09/2026",
            })
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    catmap = load(CATMAP)
    compare_suppliers = load(COMPARE_SUPPLIERS)

    print("CHANGE 1 — nhssc-term entries")
    added, skipped, refused = apply_entries(catmap, args.write)
    print("  to add:   %d" % len(added))
    for e in added:
        print("    + %-24s %s -> %s (%d products)" % (e["supplier"][:24], e["term"][:40], e["hub"], e["products"]))
    print("  already present, skipped: %d" % len(skipped))
    if refused:
        print("  REFUSED (bad category):", refused)

    print("\nCHANGE 2 — bloodcoll:abg vocabulary code")
    added_here = add_vocab_code_flat(catmap)
    added_cs = add_vocab_code_specialities(compare_suppliers)
    print("  added to differentiator-category-map.json vocabulary: %s" % added_here)
    print("  added to compare-suppliers.json specialities.bloodcoll.types (authoritative): %s" % added_cs)
    moved = rehome_abg(catmap, args.write)
    print("  ICU Medical product-level entries added (vascular:conn division -> bloodcoll:abg for these 6 only): %d" % len(moved))
    for t in moved:
        print("    - %s" % t)

    if not args.write:
        print("\nDRY RUN — nothing written. Re-run with --write.")
        return 0

    with open(CATMAP, "w", encoding="utf-8") as f:
        json.dump(catmap, f, ensure_ascii=False, indent=1)
    print("\nwritten -> %s" % CATMAP)
    with open(COMPARE_SUPPLIERS, "w", encoding="utf-8") as f:
        json.dump(compare_suppliers, f, ensure_ascii=False, indent=1)
    print("written -> %s" % COMPARE_SUPPLIERS)
    print("\nNow run: python3 scripts/build_differentiator.py && python3 scripts/stamp_notice.py && python3 verify.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
