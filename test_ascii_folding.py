#!/usr/bin/env python3
"""An accented supplier name must be findable under its plain spelling.

Added 19/09/2026, after the Hub's own search returned NOTHING for "Molnlycke"
and nothing for "Ossur" — two of the best-known names in the catalogue.

THE BUG. Every normaliser in this repo ended with a strip to [a-z0-9]. A strip
cannot tell an accented letter from punctuation, so it replaced the letter with
a SPACE rather than with its base letter:

    "Molnlycke"  ->  "m lnlycke"
    "Ossur UK"   ->  "ssur uk"
    "Drager"     ->  "dr ger"

Both sides of every comparison were mangled the same way, so the mangled forms
matched each other and nothing else. A member typing the name the way it is
written on the product box got "no results", which on this Hub reads as "that
supplier is not on the framework" — a false statement about a real company.

THE FIX is to fold to the ASCII base letter BEFORE the strip, in all three
normalisers, and to fold the same way in the browser so the query and the index
agree. These tests hold the three in step and prove the plain spelling resolves.

They are deliberately data-driven off supplier-seed.json rather than hard-coding
a list of eleven names: a twelfth accented supplier added next month is then
covered without anyone remembering this file exists.
"""
import importlib.util
import json
import os
import re
import sys
import unicodedata
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "company-aliases"))

import company_alias as ca  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BSI = _load("bsi_index", "build_supplier_index.py")
BSE = _load("bse_search", "build_search_index.py")

SEED = json.load(open(os.path.join(HERE, "data", "supplier-seed.json")))
SUPPLIERS = SEED.get("suppliers", SEED) if isinstance(SEED, dict) else SEED

JS = open(os.path.join(HERE, "app", "hub-search.js")).read()


def plain(s):
    """The spelling a member types: the accented name with the accents dropped."""
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def accented_names():
    """Every seed name or alias carrying a letter outside ASCII."""
    out = []
    for s in SUPPLIERS:
        for raw in [s.get("name")] + list(s.get("aliases") or []):
            if raw and any(ord(c) > 127 for c in raw) and plain(raw) != raw:
                out.append((s.get("name"), raw))
    return out


class AsciiFoldingTests(unittest.TestCase):

    def test_the_seed_actually_contains_accented_names(self):
        """If this ever goes to zero the rest of the file is silently vacuous."""
        found = accented_names()
        self.assertGreaterEqual(len(found), 10,
                                "expected the accented suppliers (Molnlycke, Ossur, "
                                "Drager, bioMerieux, Schulke...) still to be in the seed")

    def test_no_normaliser_turns_a_letter_into_a_space(self):
        """The bug itself, stated once per normaliser."""
        for label, fn in (("company_alias.norm", ca.norm),
                          ("build_supplier_index.norm", BSI.norm)):
            for canonical, raw in accented_names():
                got = fn(raw)
                self.assertEqual(got, fn(plain(raw)),
                                 "%s: %r and its plain spelling %r must normalise "
                                 "alike, got %r" % (label, raw, plain(raw), got))

    def test_the_plain_spelling_resolves_to_the_same_company(self):
        """The member-visible promise: type it without the accent, find it.

        Stated as a token count as well as an equality, because the failure mode
        was not a mismatch but a SPLIT: one word silently became two, and both
        halves were then too short to match anything."""
        for canonical, raw in accented_names():
            a = ca.norm(raw)
            self.assertEqual(a, ca.norm(plain(raw)),
                             "%r resolves differently from %r" % (raw, plain(raw)))
            self.assertEqual(len(a.split()), len(ca.norm(plain(raw)).split()),
                             "%r normalised to %r — a dropped letter split a word"
                             % (raw, a))

    def test_folding_merges_nothing_that_was_distinct(self):
        """Folding must widen matching, never collapse two real companies into one.

        This is the check that makes the change safe to land: measured across the
        whole seed, folding may only ADD keys, never put two different canonical
        suppliers behind one key that did not already share one.
        """
        def keys(transform):
            m = {}
            for s in SUPPLIERS:
                for raw in [s.get("name")] + list(s.get("aliases") or []):
                    if not raw:
                        continue
                    m.setdefault(transform(raw), set()).add(s.get("name"))
            return m

        unfolded = keys(lambda x: re.sub(r"\s+", " ", re.sub(
            r"[^a-z0-9]+", " ", str(x).lower().replace("&", " and "))).strip())
        folded = keys(ca.norm)
        new_collisions = {k: v for k, v in folded.items()
                          if len(v) > 1 and len(unfolded.get(k, set())) <= 1}
        self.assertEqual(new_collisions, {},
                         "ASCII-folding created a NEW cross-supplier collision; that "
                         "would publish one company's frameworks under another's name")

    def test_the_search_index_builder_folds_supplier_keywords(self):
        """data/hub-search-index.json is what the browser actually searches."""
        recs = BSE.supplier_records()
        self.assertGreater(len(recs), 500, "supplier records did not load")
        for r in recs:
            self.assertNotRegex(
                " " + r["k"] + " ", r" (m lnlycke|ssur|dr ger|biom rieux|sch lke|l wenstein|esp re) ",
                "search keywords for %r still hold a letter-dropped token" % r["t"])
        by_title = {r["t"]: r["k"] for r in recs}
        for title, token in (("Mölnlycke", "molnlycke"),
                             ("Össur UK", "ossur"),
                             ("bioMérieux UK", "biomerieux")):
            self.assertIn(title, by_title, "%s left the seed — update this test" % title)
            self.assertIn(token, by_title[title].split(),
                          "%s must be searchable as %r" % (title, token))

    def test_the_browser_folds_the_query_the_same_way(self):
        """A folded index and an unfolded query miss each other just as badly.

        app/hub-search.js runs in the member's browser, so it cannot import the
        Python fold. These assertions keep the two implementations in step.
        """
        self.assertIn("function fold(", JS, "app/hub-search.js lost its fold()")
        self.assertIn("normalize('NFKD')", JS,
                      "fold() must decompose before stripping combining marks")
        self.assertIn("return fold(q).toLowerCase()", JS,
                      "clean() must fold the member's query BEFORE the [^a-z0-9] strip")
        for field in ("p._t", "s._h", "s._w", "doc.records[i]._t", "doc.records[i]._k"):
            self.assertRegex(JS, re.escape(field) + r"\s*=\s*' '\s*\+\s*fold\(",
                             "%s is compared against a folded query, so it must be "
                             "folded too" % field)

    def test_the_three_python_folds_agree(self):
        """One fold, three copies (no shared import across these entry points)."""
        probe = "Mölnlycke Össur Dräger bioMérieux Schülke " \
                "Ørn Espère Weiße Łódź"
        self.assertEqual(ca.ascii_fold(probe), BSI.ascii_fold(probe))
        self.assertEqual(ca.ascii_fold(probe), BSE.ascii_fold(probe))
        self.assertTrue(all(ord(c) < 128 for c in ca.ascii_fold(probe)),
                        "fold left a non-ASCII character: %r" % ca.ascii_fold(probe))


if __name__ == "__main__":
    unittest.main(verbosity=2)
