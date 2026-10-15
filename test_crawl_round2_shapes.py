#!/usr/bin/env python3
"""test_crawl_round2_shapes.py — the shapes that kept four re-crawls held after
the 15/10/2026 first round (Otto Bock, Sectra, Optimum Medical, Insulet).

  1. Several locale prefixes, one UK (ottobock.com: /en-gb/, /it-it/, /fr-fr/ ...,
     no unprefixed copy): keep only the UK-locale catalogue, and read only the UK
     sub-sitemap from a locale index.
  2. A product page whose <h1> is a sentence (Sectra): the <title> names it.
  3. Blog posts filed under the product path (Optimum Medical: posts at
     /products/<slug>/): dropped when they come only from post-sitemap.xml and the
     site has a product sitemap of its own, or sit under /blog/ or /news/.
Offline, every fetch is a fixture.   python3 test_crawl_round2_shapes.py   exit 0 = pass
"""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
sys.path.insert(0, HERE)
import crawl_supplier_site as cs                     # noqa: E402
from test_crawl_junk_shapes import _Fixture, _sitemap, _u, HOST   # noqa: E402


def _index(urls):
    return ('<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join("<sitemap><loc>%s</loc></sitemap>" % u for u in urls) + "</sitemapindex>")


def _run(pages):
    real = cs.get
    fx = _Fixture(pages)
    cs.get = fx
    try:
        return cs.sitemap_products(HOST), fx
    finally:
        cs.get = real


class LocalePrefixFilter(unittest.TestCase):
    def test_only_the_uk_locale_is_kept_when_there_is_no_unprefixed_copy(self):
        gb = [_u("en-gb/products/orthotics/brace-%s" % c) for c in "abcdefghij"]
        it = [_u("it-it/products/ortesi/tutore-%s" % c) for c in "abcdefghij"]
        fr = [_u("fr-fr/products/orthese/attelle-%s" % c) for c in "abcdefghij"]
        (res, err), _ = _run({"https://%s/sitemap.xml" % HOST: _sitemap(gb + it + fr)})
        self.assertIsNone(err)
        self.assertEqual(len(res["products"]), 10)
        self.assertEqual({p["division"] for p in res["products"]}, {"Orthotics"})

    def test_a_site_with_a_single_uk_prefix_is_unchanged(self):
        gb = [_u("en-gb/products/orthotics/brace-%s" % c) for c in "abcdefghij"]
        (res, err), _ = _run({"https://%s/sitemap.xml" % HOST: _sitemap(gb)})
        self.assertEqual(len(res["products"]), 10)

    def test_no_uk_locale_means_nothing_is_dropped(self):
        it = [_u("it-it/products/ortesi/tutore-%s" % c) for c in "abcdefghij"]
        fr = [_u("fr-fr/products/orthese/attelle-%s" % c) for c in "abcdefghij"]
        (res, err), _ = _run({"https://%s/sitemap.xml" % HOST: _sitemap(it + fr)})
        self.assertEqual(len(res["products"]), 20)

    def test_a_locale_index_reads_only_the_uk_sub_sitemap(self):
        gb = [_u("en-gb/products/orthotics/brace-%s" % c) for c in "abcdefghij"]
        it = [_u("it-it/products/ortesi/tutore-%s" % c) for c in "abcdefghij"]
        pages = {"https://%s/sitemap.xml" % HOST: _index([_u("it-it/sitemap.xml"), _u("en-gb/sitemap.xml"),
                                                          _u("fr-fr/sitemap.xml")]),
                 _u("en-gb/sitemap.xml"): _sitemap(gb), _u("it-it/sitemap.xml"): _sitemap(it),
                 _u("fr-fr/sitemap.xml"): _sitemap(it)}
        (res, err), fx = _run(pages)
        self.assertEqual(len(res["products"]), 10)
        self.assertNotIn(_u("it-it/sitemap.xml"), fx.fetched)
        self.assertNotIn(_u("fr-fr/sitemap.xml"), fx.fetched)


class SentenceHeadingUsesTitle(unittest.TestCase):
    def page(self, title, h1):
        return "<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % (title, h1)

    def test_tagline_h1_yields_to_the_title(self):
        self.assertEqual(cs._page_title(self.page("Sectra 3D Print | Sectra Medical",
                                                  "Print your orthopaedic cases in 3D")), "Sectra 3D Print")

    def test_a_long_product_name_containing_the_title_name_is_kept(self):
        h1 = "AQUACEL Ribbon Dressing with Strengthening Fiber"
        self.assertEqual(cs._page_title(self.page("AQUACEL Ribbon Dressing - Wound | ConvaTec", h1)), h1)

    def test_short_h1_is_kept(self):
        self.assertEqual(cs._page_title(self.page("Something else | Co", "Ugo Leg Bags")), "Ugo Leg Bags")

    def test_a_long_title_is_not_preferred_to_the_heading(self):
        h1 = "Easily add artificial intelligence to your clinical workflows"
        t = "Easily add artificial intelligence to your clinical workflows today and tomorrow | Co"
        self.assertEqual(cs._page_title(self.page(t, h1)), h1)

    def test_no_title_keeps_the_heading(self):
        self.assertEqual(cs._page_title("<html><body><h1>Print your orthopaedic cases in 3D</h1></body></html>"),
                         "Print your orthopaedic cases in 3D")


class BlogPostsAreNotProducts(unittest.TestCase):
    def test_post_sitemap_urls_are_dropped_when_a_product_sitemap_exists(self):
        prods = [_u("product/item-%s/" % c) for c in "abcdefghij"]
        posts = [_u("products/news-item-%s/" % c) for c in "abcdefghij"]
        pages = {"https://%s/sitemap.xml" % HOST: _index([_u("post-sitemap.xml"), _u("product-sitemap.xml")]),
                 _u("post-sitemap.xml"): _sitemap(posts), _u("product-sitemap.xml"): _sitemap(prods)}
        for u in prods:
            pages[u] = "<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % (u[-8:], u[-8:-1])
        (res, err), _ = _run(pages)
        self.assertIsNone(err)
        self.assertEqual(len(res["products"]), 10)
        self.assertFalse(any("news-item" in p["n"].lower() for p in res["products"]))

    def test_without_a_product_sitemap_posts_stay(self):
        posts = [_u("products/wound/item-%s" % c) for c in "abcdefghij"]
        pages = {"https://%s/sitemap.xml" % HOST: _index([_u("post-sitemap.xml")]),
                 _u("post-sitemap.xml"): _sitemap(posts)}
        (res, err), _ = _run(pages)
        self.assertEqual(len(res["products"]), 10)

    def test_blog_and_news_path_segments_are_dropped(self):
        prod = [_u("products/wound/dressing-%s" % c) for c in "abcdefghij"]
        blog = [_u("products/blog/post-%s" % c) for c in "abc"] + [_u("products/news/story-a")]
        (res, err), _ = _run({"https://%s/sitemap.xml" % HOST: _sitemap(prod + blog)})
        self.assertEqual(len(res["products"]), 10)


class InsuletIsARecordedRefusal(unittest.TestCase):
    def test_published_data_matches_the_decision(self):
        import json
        with open(os.path.join(HERE, "data", "supplier-products.json"), encoding="utf-8") as f:
            d = json.load(f)
        # scripts/_land_held_recrawls_1015b.py: omnipod.com is two systems' marketing pages, not a range.
        self.assertIn("Insulet International Ltd", d["refusals"])
        self.assertNotIn("Insulet International Ltd", d["suppliers"])
        names = [p["n"] for s in d["suppliers"].values() for p in s["products"]]
        self.assertNotIn("Thanks", names)


if __name__ == "__main__":
    unittest.main()
