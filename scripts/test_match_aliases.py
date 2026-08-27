"""press_match.match_aliases — the aliases the Live Desk carve-out may match on.

Written 27/08/2026 after the Industry Wire dropped "Fifth Baxter particulate
recall since July in the US". rank.py built its supplier pattern from canonical
names only and had never read aliases, so the short form matched nothing.

Most of these are things that must NOT happen. A single-token alias is the
easiest thing in this repo to widen carelessly: 29 of the 316 single-token
aliases at least four characters long are also ordinary English words, and one
of them is "baxter".
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import press_match as pm


def sup(name, aliases=None):
    return {"name": name, "aliases": list(aliases or [])}


UNIVERSE = {"baxter": 1, "cook": 1, "huma": 1, "acme": 2, "bd": 1}


class TheCaseItWasWrittenFor(unittest.TestCase):

    def test_baxter_short_form_is_published_capitalised(self):
        out = pm.match_aliases(sup("Baxter Healthcare Ltd", ["baxter"]), UNIVERSE)
        self.assertIn("Baxter", out["caseSensitive"])

    def test_the_full_name_stays_case_insensitive(self):
        out = pm.match_aliases(sup("Baxter Healthcare Ltd", ["baxter"]), UNIVERSE)
        self.assertIn("Baxter Healthcare Ltd", out["caseInsensitive"])
        self.assertNotIn("Baxter Healthcare Ltd", out["caseSensitive"])


class ThingsThatMustNotHappen(unittest.TestCase):

    def test_an_ambiguous_single_word_is_never_published(self):
        """The same word on two suppliers proves nothing about either."""
        out = pm.match_aliases(sup("Acme Medical", ["acme"]), UNIVERSE)
        self.assertEqual([], out["caseSensitive"])

    def test_a_short_token_is_never_published(self):
        out = pm.match_aliases(sup("BD", ["bd"]), UNIVERSE)
        self.assertEqual([], out["caseSensitive"])

    def test_casing_is_never_invented(self):
        """A single-token alias absent from the canonical name has no evidence
        for how it is capitalised, so it is not published at all."""
        out = pm.match_aliases(sup("Something Else Ltd", ["cook"]), UNIVERSE)
        self.assertEqual([], out["caseSensitive"])

    def test_a_word_never_reaches_the_case_insensitive_list(self):
        """This is the guard that keeps 'cook' from matching 'trusts cook meals'.
        Single words must ONLY ever be offered for case-sensitive matching."""
        out = pm.match_aliases(sup("Cook Medical", ["cook"]), UNIVERSE)
        self.assertNotIn("cook", [a.lower() for a in out["caseInsensitive"]])
        self.assertEqual(["Cook"], out["caseSensitive"])

    def test_an_unknown_word_is_treated_as_ambiguous(self):
        out = pm.match_aliases(sup("Zeta Medical", ["zeta"]), UNIVERSE)
        self.assertEqual([], out["caseSensitive"])


class AgainstTheRealSeed(unittest.TestCase):
    """A silently no-op alias publisher looks exactly like the bug it fixes."""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "data", "supplier-seed.json"), encoding="utf-8") as fh:
            cls.seed = json.load(fh)
        cls.universe = pm.alias_universe(cls.seed)
        cls.by = {s["name"]: s for s in cls.seed["suppliers"]}

    def test_it_still_fires_for_baxter(self):
        out = pm.match_aliases(self.by["Baxter Healthcare Ltd"], self.universe)
        self.assertIn("Baxter", out["caseSensitive"])

    def test_every_case_sensitive_alias_is_a_token_of_its_own_name(self):
        """The real invariant. The casing must be EVIDENCE taken from the seed's
        canonical name, never a capitalisation this code invented. (It is not
        simply "starts with a capital": eKare, electroCore, i3medical, iMEDicare
        and inomed are genuinely lower-case brands, and dropping them would be
        the same class of mistake as dropping Baxter.)"""
        import re
        for s in self.seed["suppliers"]:
            tokens = set(re.findall(r"[\w&'-]+", s["name"]))
            for a in pm.match_aliases(s, self.universe)["caseSensitive"]:
                self.assertIn(a, tokens, "%s -> %r" % (s["name"], a))

    def test_no_all_lowercase_alias_is_an_ordinary_word(self):
        """Capitalisation is what stops "trusts cook meals" matching Cook
        Medical. Where a brand is genuinely all lower case that protection is
        gone, so such an alias must not also be an English word. Guards the
        future: today the all-lowercase ones are inomed, ekare and i3medical."""
        RISKY = {"cook", "flow", "span", "merit", "amity", "bard", "days",
                 "evoke", "inspire", "intuitive", "nestle", "repose",
                 "resource", "ultimate", "dermal", "cardinal", "banner"}
        for s in self.seed["suppliers"]:
            for a in pm.match_aliases(s, self.universe)["caseSensitive"]:
                if a.islower():
                    self.assertNotIn(a, RISKY, "%s -> %r" % (s["name"], a))

    def test_the_case_sensitive_list_stays_a_minority(self):
        """Past a certain share this has stopped being a careful carve-out."""
        n = sum(len(pm.match_aliases(s, self.universe)["caseSensitive"])
                for s in self.seed["suppliers"])
        self.assertLess(n, len(self.seed["suppliers"]) * 0.5, n)


if __name__ == "__main__":
    unittest.main()
