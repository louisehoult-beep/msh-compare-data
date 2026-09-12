"""Regression cover for _breadcrumb_division / _jsonld_breadcrumb_division,
added 12/09/2026 alongside the JSON-LD fallback.

Real fixtures, not synthetic markup — one page saved from each of the three
sites that shaped this code, because each one is the reason a rule exists:
  - Henleys: the working HTML-container case, and the case that caught the
    JSON-LD-first ordering bug (its own JSON-LD trail is a SHORTER, WRONG
    "Home > Products > <product name>" that skips the real division).
  - Sense Medical: the new case — no HTML breadcrumb element at all, real
    division only reachable via JSON-LD, and a genuine trap (the crumb links
    to "/products/" not the bare root, so a naive host-only check let it
    through as if it were the division).
  - MIS Healthcare: the reason the HTML container regex matches Tailwind
    itemtype markup, not just class="breadcrumb" — a prior, already-fixed
    bug this suite pins so it cannot silently return.

Run: python3 test_breadcrumb_division.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import crawl_supplier_site as cs  # noqa: E402 (path insert must come first)

FIXTURES = os.path.join(HERE, "test_fixtures_breadcrumb")


def _load(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8", errors="replace") as fh:
        return fh.read()


class HtmlBreadcrumbStillWorks(unittest.TestCase):
    """The pre-existing route. Must not regress when JSON-LD is added."""

    def test_henleys_reads_the_real_division_not_the_product_name(self):
        body = _load("henleys_product.html")
        self.assertEqual(
            cs._breadcrumb_division(body, "www.henleysmed.com"),
            "Blood Pressure Monitoring")

    def test_mis_healthcare_tailwind_breadcrumb_still_matches(self):
        body = _load("mis_healthcare_product.html")
        division = cs._breadcrumb_division(body, "mishealthcare.co.uk")
        self.assertIsNotNone(division, "the Tailwind-class breadcrumb regression must stay fixed")


class JsonLdIsAFallbackNeverAPriority(unittest.TestCase):
    """The 12/09/2026 finding: JSON-LD and the visible HTML breadcrumb are NOT
    interchangeable data of equal quality on the same site. JSON-LD only gets
    a turn when there is no HTML breadcrumb element to read at all."""

    def test_henleys_json_ld_trail_is_shorter_and_wrong_html_wins_anyway(self):
        # Proves the trap this suite exists to catch: reading Henleys' own
        # JSON-LD in isolation returns the WRONG (shorter) answer.
        body = _load("henleys_product.html")
        wrong = cs._jsonld_breadcrumb_division(body, "www.henleysmed.com")
        self.assertEqual(wrong, "Reusable Two-Piece Blood Pressure Cuffs",
                         "if this ever changes, the JSON-LD-vs-HTML precedence "
                         "note in _breadcrumb_division needs re-reading, not deleting")
        # And confirms the real function never surfaces that wrong answer.
        right = cs._breadcrumb_division(body, "www.henleysmed.com")
        self.assertEqual(right, "Blood Pressure Monitoring")

    def test_sense_medical_falls_through_to_json_ld_when_html_has_none(self):
        body = _load("sensemedical_product.html")
        self.assertEqual(
            cs._breadcrumb_division(body, "sensemedical.co.uk"),
            "Optical Coherence Tomography (OCT)")


class GenericCatalogueCrumbsAreDroppedByLinkNotWording(unittest.TestCase):
    """A crumb whose href resolves to the site root, OR to one of the
    generic catalogue-path segments (PRODUCT_PATHS), is dropped regardless
    of what words the company happens to use for it — same philosophy as
    the HTML route's own home-crumb rule (05/09/2026)."""

    def test_our_products_crumb_is_not_mistaken_for_the_division(self):
        # This is the exact bug: "Our Products" links to /products/, one
        # path segment deep, so host-equality alone let it through.
        body = _load("sensemedical_product.html")
        division = cs._jsonld_breadcrumb_division(body, "sensemedical.co.uk")
        self.assertNotEqual(division, "Our Products")
        self.assertEqual(division, "Optical Coherence Tomography (OCT)")

    def test_a_terminal_crumb_with_no_item_url_is_not_treated_as_root(self):
        """schema.org allows the last (current-page) ListItem to omit `item`
        entirely. An absent href must never be judged a root link — that
        was the first fix attempt's own bug, caught by this exact fixture."""
        body = _load("sensemedical_product.html")
        self.assertIsNotNone(cs._jsonld_breadcrumb_division(body, "sensemedical.co.uk"))


if __name__ == "__main__":
    unittest.main()
