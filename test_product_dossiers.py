#!/usr/bin/env python3
"""
Invariant gate for the product dossiers (root rule 14).

A dossier publishes several sources about one product. Its failure mode is not a
crash - it is a quiet mis-attribution: one product's specification appearing
under another's name, or a manufacturer's marketing claim reading as an
NHS-authored measurement. These checks pin the things that would make that
happen, and each is self-tested so it cannot pass vacuously.

Usage:  python3 test_product_dossiers.py
"""

from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import build_product_dossiers as B                                  # noqa: E402

failures: list[str] = []
checks = 0


def check(ok, what):
    global checks
    checks += 1
    if not ok:
        failures.append(what)
    return ok


def test_size_stripping():
    """The pack size comes off the name and is KEPT, never discarded."""
    base, variant = B.strip_size("Tegaderm Foam dressing (adhesive) 10cm x 11cm oval")
    check(base == "Tegaderm Foam dressing (adhesive)", "size strip base: %r" % base)
    check("10cm x 11cm" in variant, "the stripped size must be kept: %r" % variant)
    # A name with no size must be returned untouched - stripping a real word out
    # of a product name is how "Allevyn Gentle Border Lite" becomes "Allevyn".
    base2, variant2 = B.strip_size("Allevyn Gentle Border Lite")
    check(base2 == "Allevyn Gentle Border Lite" and variant2 == "",
          "a name with no size must be untouched: %r / %r" % (base2, variant2))


def test_longest_family_wins():
    """A Lite dressing must not be filed under the standard one's family."""
    b = B.Builder("wound")
    b.note_family("ACME", "Allevyn Gentle")
    b.note_family("ACME", "Allevyn Gentle Border Lite")
    got = b.family_of("ACME", "Allevyn Gentle Border Lite dressing")
    check(got == "Allevyn Gentle Border Lite",
          "longest family must win, got %r" % got)
    # And a family must match on a word boundary, never mid-word: "Allevyn
    # Gentle" must not swallow a hypothetical "Allevyn Gentleman".
    check(b.family_of("ACME", "Allevyn Gentleness") is None,
          "family matching must respect word boundaries")
    check(b.family_of("ACME", "Mepilex Border") is None,
          "an unrelated product must not be given a family")


def test_published_store():
    path = os.path.join(REPO, "data", "product-dossiers-wound.json")
    if not check(os.path.exists(path), "product-dossiers-wound.json is missing"):
        return
    store = json.load(open(path))
    dossiers = store.get("dossiers") or []
    check(bool(dossiers), "the store publishes no dossiers")
    check(bool(store.get("joinRule")), "the join rule must be stated in the file")
    check(bool(store.get("readingRule")), "the reading rule must be stated in the file")

    kinds_seen = set()
    for d in dossiers:
        # Every source block must say who it is and what KIND of fact it is -
        # without the kind, a manufacturer claim reads as an NHS measurement.
        for sid, block in d["sources"].items():
            if not check(block.get("kind") in
                         ("independent", "catalogue", "manufacturer", "tariff", "regulatory"),
                         "%s: source %s has no usable kind" % (d["key"], sid)):
                return
            kinds_seen.add(block["kind"])
            if not check(bool(block.get("name")),
                         "%s: source %s is unattributed" % (d["key"], sid)):
                return

        for field, obs in d["fields"].items():
            for ob in obs:
                if not check(ob.get("source") in d["sources"],
                             "%s/%s: observation cites source %r that is not listed"
                             % (d["key"], field, ob.get("source"))):
                    return
                if not check(ob.get("scope") in ("product", "family"),
                             "%s/%s: observation has no scope" % (d["key"], field)):
                    return
                # A family-scope observation MUST name the variant it was
                # actually measured on. Without it the figure reads as this
                # product's own, which is the mis-attribution this whole
                # structure exists to prevent.
                if ob["scope"] == "family" and not check(
                        bool(ob.get("variant")),
                        "%s/%s: family-scope value %r names no variant"
                        % (d["key"], field, ob.get("value"))):
                    return

        # A family-scope observation can only exist where a family was assigned.
        if any(o["scope"] == "family" for obs in d["fields"].values() for o in obs):
            if not check(bool(d.get("family")),
                         "%s carries family-scope values but has no family" % d["key"]):
                return

    check("independent" in kinds_seen,
          "no independent (ICC) source reached any dossier — the join has broken")
    check(store["counts"]["withMoreThanOneSource"] >= 50,
          "only %s dossiers carry more than one source — the join has regressed"
          % store["counts"]["withMoreThanOneSource"])
    check(len(dossiers) >= 700,
          "only %d dossiers — the speciality filter has narrowed" % len(dossiers))


def test_no_silent_merge():
    """Self-test: two same-supplier products whose names share a prefix must
    stay two dossiers, however tempting the prefix looks."""
    b = B.Builder("wound")
    a = b.dossier_for("Advanced Medical Solutions Ltd", "ActivHeal Foam")
    c = b.dossier_for("Advanced Medical Solutions Ltd", "ActivHeal Foam Border")
    check(a is not c, "a shared name prefix must never merge two products")
    # ...but the same NPC must merge them, because that IS the same catalogue line.
    e = b.dossier_for("Advanced Medical Solutions Ltd", "Something", npc="ELA838")
    f = b.dossier_for("A Totally Different Name Ltd", "Other", npc="ELA838")
    check(e is f, "the same NPC must join two records")


for fn in (test_size_stripping, test_longest_family_wins,
           test_published_store, test_no_silent_merge):
    try:
        fn()
    except Exception as exc:                                        # noqa: BLE001
        failures.append("%s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))

if failures:
    print("PRODUCT DOSSIER GATE FAILED (%d of %d checks)" % (len(failures), checks))
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
print("product dossier gate passed: %d checks" % checks)
