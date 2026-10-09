"""Regression cover for the all-digits URL segment rule in sitemap_products,
added 21/09/2026 (^o564).

THE FAILURE THIS PINS. Route 2 reads a division out of the path segment
between the product-path token and the product's own slug. On a
database-driven site that segment is the product's ROW ID, not a category:
www.crestmedical.co.uk files every product at /product/<id>/<slug>, so all
872 of its products were captured under 872 "divisions" called "285", "286",
"287" — and supplier-search.js groups a supplier's range by division, so a
paying member saw "518234" printed as a shelf label. Oticon
(www.oticon.co.uk) has the same shape on 43 of its 46 divisions, mixed in
beside three real ones.

The honest read is that such a URL carries NO division, so the product falls
through to "Uncategorised" and hasDivisions/captureCaveat say so in words.
Inventing a grouping out of the numeric id is the thing that must not happen.

Offline: `get` is replaced with a fixture server, so this suite makes no
network requests.

Run: python3 test_numeric_id_division.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import crawl_supplier_site as cs  # noqa: E402 (path insert must come first)

HOST = "example.test"


def _sitemap(urls):
    body = ['<?xml version="1.0" encoding="utf-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        body.append("<url><loc>%s</loc></url>" % u)
    body.append("</urlset>")
    return "\n".join(body)


class _Fixture(object):
    """Stands in for cs.get for the duration of one test."""

    def __init__(self, pages):
        self.pages = pages

    def __call__(self, url, as_json=False, timeout=30):
        try:
            return self.pages[url], {}
        except KeyError:
            raise IOError("HTTP Error 404: Not Found")


def _crawl(urls):
    pages = {"https://%s/sitemap.xml" % HOST: _sitemap(urls)}
    real = cs.get
    cs.get = _Fixture(pages)
    try:
        return cs.sitemap_products(HOST)
    finally:
        cs.get = real


class NumericSegmentIsAnId(unittest.TestCase):

    def test_crest_shape_publishes_no_numeric_divisions(self):
        """/product/<id>/<slug> — the Crest Medical shape."""
        urls = ["https://%s/product/%d/product-name-%d" % (HOST, 280 + i, i)
                for i in range(20)]
        shaped, why = _crawl(urls)
        self.assertIsNotNone(shaped, why)
        divisions = {p["division"] for p in shaped["products"]}
        self.assertEqual(divisions, {"Uncategorised"},
                         "a row id must never be published as a division")
        self.assertFalse(shaped["hasDivisions"],
                         "with no division to read, the capture must say so")

    def test_a_real_division_beside_numeric_ones_survives(self):
        """The Oticon shape: some ids, some genuine category segments."""
        urls = ["https://%s/product/%d/numeric-slug-%d" % (HOST, 161200 + i, i)
                for i in range(12)]
        urls += ["https://%s/product/hearing-aids/hearing-aid-%d" % (HOST, i)
                 for i in range(12)]
        shaped, why = _crawl(urls)
        self.assertIsNotNone(shaped, why)
        by_div = {}
        for p in shaped["products"]:
            by_div.setdefault(p["division"], []).append(p["n"])
        self.assertIn("Hearing Aids", by_div,
                      "a genuine division segment must be untouched by the id rule")
        self.assertEqual(len(by_div["Hearing Aids"]), 12)
        self.assertEqual(len(by_div.get("Uncategorised", [])), 12)
        self.assertNotIn("161200", by_div)

    def test_a_descriptive_slug_containing_digits_is_not_an_id(self):
        """Only an ALL-digits segment is an id. '3m' is a division name."""
        urls = ["https://%s/product/3m/tape-%d" % (HOST, i) for i in range(20)]
        shaped, why = _crawl(urls)
        self.assertIsNotNone(shaped, why)
        self.assertEqual({p["division"] for p in shaped["products"]}, {"3M"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
