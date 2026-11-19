"""Cover for the three crawler gaps closed 27/10/2026 (attended change).

1. A site with no sitemap: bounded link following (link_follow_products).
2. Choosing the UK sitemap: market named in a file name, a top-level <urlset>
   that lists country sitemaps as ordinary links, an undeclared /en-gb/sitemap.xml,
   and the UK twin of a declared non-UK locale sitemap.
3. Product URLs ending in a page file name (x.html, index-<market>.html): the
   name comes from the parent segment, never the file name.

Stdlib only, no network: cs.get is replaced by a fixture.
Run: python3 test_crawl_range_gaps.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import crawl_supplier_site as cs  # noqa: E402

HOST = "www.example-med.com"


def _urlset(urls):
    return ('<?xml version="1.0"?><urlset>%s</urlset>'
            % "".join("<url><loc>%s</loc></url>" % u for u in urls))


def _index(urls):
    return ('<?xml version="1.0"?><sitemapindex>%s</sitemapindex>'
            % "".join("<sitemap><loc>%s</loc></sitemap>" % u for u in urls))


class Fx:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def __call__(self, url, as_json=False, timeout=30):
        self.calls.append(url)
        if url in self.pages:
            return self.pages[url], {}
        raise IOError("HTTP Error 404: Not Found")


class Base(unittest.TestCase):
    def setUp(self):
        self.real_get, self.real_pause = cs.get, cs.PAUSE

    def tearDown(self):
        cs.get = self.real_get

    def run_sitemap(self, pages, **kw):
        fx = Fx(pages)
        cs.get = fx
        return cs.sitemap_products(HOST, **kw), fx


def names(result):
    shaped, why = result
    assert shaped is not None, why
    return sorted(p["n"] for p in shaped["products"])


class FileNameLeaves(Base):
    def test_helpers(self):
        self.assertTrue(cs.is_index_file("index-eu.html"))
        self.assertTrue(cs.is_index_file("index-eu-eemea.html"))
        self.assertTrue(cs.is_index_file("default.aspx"))
        self.assertFalse(cs.is_index_file("index-guide-for-nurses-and-carers.html"))
        self.assertFalse(cs.is_index_file("indexer.html"))
        self.assertFalse(cs.is_index_file("index"))
        self.assertEqual(cs.page_stem("dynagen.html"), "dynagen")
        self.assertEqual(cs.page_stem("dynagen"), "dynagen")
        self.assertEqual(cs.page_stem("sheet.pdf"), "sheet.pdf")

    def test_html_leaf_loses_extension(self):
        urls = ["https://%s/products/wound/dressing-%s.html" % (HOST, c) for c in "abcdefgh"]
        urls += ["https://%s/products/stoma/pouch-%s.html" % (HOST, c) for c in "abcd"]
        (shaped, why), _ = self.run_sitemap({"https://%s/sitemap.xml" % HOST: _urlset(urls)})
        self.assertIsNotNone(shaped, why)
        self.assertIn("Dressing A", [p["n"] for p in shaped["products"]])
        self.assertFalse([p for p in shaped["products"] if "html" in p["n"].lower()])

    def test_locale_index_file_is_named_from_parent(self):
        urls = []
        for c in "abcdefgh":
            urls += ["https://%s/gb/en/ortho/products/prod-%s/index-eu.html" % (HOST, c),
                     "https://%s/gb/en/ortho/products/prod-%s/index-eu-eemea.html" % (HOST, c)]
        urls += ["https://%s/gb/en/ent/products/solo-%s.html" % (HOST, c) for c in "ab"]
        # per-page enrichment is out of scope here: flat results go through
        # numeric_slug_products, which reads each page, so stub it to the URL slugs.
        real = cs.numeric_slug_products
        cs.numeric_slug_products = lambda d, us, reason=None, fallback_label=None: (None, "stub")
        try:
            r, _ = self.run_sitemap({"https://%s/sitemap.xml" % HOST: _urlset(urls)})
        finally:
            cs.numeric_slug_products = real
        got = names(r)
        self.assertIn("Prod A", got)
        self.assertIn("Solo A", got)
        self.assertEqual(got.count("Prod A"), 1)          # two locale files, one product
        self.assertFalse([n for n in got if "Index" in n or "Html" in n])


class UkSitemapChoice(Base):
    def test_uk_token_in_file_name(self):
        self.assertTrue(cs.uk_sitemap_url("https://x.net/a.sitemap.gb-sitemap.xml"))
        self.assertTrue(cs.uk_sitemap_url("https://x.com/en-gb/sitemap.xml"))
        self.assertFalse(cs.uk_sitemap_url("https://x.net/a.sitemap.de-sitemap.xml"))
        self.assertFalse(cs.uk_sitemap_url("https://x.net/a.sitemap.gbx-sitemap.xml"))

    def test_other_market_sibling(self):
        uk = ["https://x.net/s.gb-sitemap.xml"]
        self.assertTrue(cs.other_market_sibling("https://x.net/s.de-sitemap.xml", uk))
        self.assertFalse(cs.other_market_sibling("https://x.net/s.gb-sitemap.xml", uk))
        self.assertFalse(cs.other_market_sibling("https://x.net/products-sitemap.xml", uk))

    def test_index_with_market_named_files_reads_only_uk(self):
        gb = ["https://%s/gb/en/ent/products/gb-item-%s.html" % (HOST, c) for c in "abcdefghij"]
        de = ["https://%s/de/de/ent/products/de-item-%s.html" % (HOST, c) for c in "abcdefghij"]
        pages = {
            "https://%s/sitemap.xml" % HOST: _index([
                "https://%s/s.de-sitemap.xml" % HOST, "https://%s/s.gb-sitemap.xml" % HOST,
                "https://%s/s.fr-sitemap.xml" % HOST]),
            "https://%s/s.gb-sitemap.xml" % HOST: _urlset(gb),
            "https://%s/s.de-sitemap.xml" % HOST: _urlset(de),
        }
        r, fx = self.run_sitemap(pages)
        self.assertNotIn("https://%s/s.de-sitemap.xml" % HOST, fx.calls)
        self.assertNotIn("https://%s/s.fr-sitemap.xml" % HOST, fx.calls)
        self.assertTrue(all(n.lower().replace(" ", "-").startswith("gb-item") for n in names(r)))

    def test_urlset_listing_country_sitemaps_is_followed_to_the_uk_one(self):
        top = ["https://%s/%s/sitemap.xml" % (HOST, m)
               for m in ("fr-fr", "en-gb", "de-de", "en-au")] + ["https://%s/" % HOST]
        uk = ["https://%s/en-gb/products/bracing/kneebrace-%s" % (HOST, c) for c in "abcdefghij"]
        fr = ["https://%s/fr-fr/produits/fr-%s" % (HOST, c) for c in "abcdefghij"]
        pages = {"https://%s/sitemap.xml" % HOST: _urlset(top),
                 "https://%s/en-gb/sitemap.xml" % HOST: _urlset(uk),
                 "https://%s/fr-fr/sitemap.xml" % HOST: _urlset(fr)}
        r, fx = self.run_sitemap(pages)
        self.assertNotIn("https://%s/fr-fr/sitemap.xml" % HOST, fx.calls)
        self.assertEqual(len(names(r)), 10)

    def test_ordinary_urlset_is_not_mistaken_for_an_index(self):
        self.assertFalse(cs.urlset_lists_sitemaps(
            ["https://x.com/products/a", "https://x.com/products/b", "https://x.com/sitemap.xml"]))
        self.assertTrue(cs.urlset_lists_sitemaps(
            ["https://x.com/en-gb/sitemap.xml", "https://x.com/fr-fr/sitemap.xml"]))

    def test_undeclared_uk_sitemap_is_probed_when_nothing_else_has_products(self):
        uk = ["https://%s/en-gb/products/devices/item-%s" % (HOST, c) for c in "abcdefghij"]
        pages = {"https://%s/sitemap.xml" % HOST: _urlset([]),
                 "https://%s/en-gb/sitemap.xml" % HOST: _urlset(uk)}
        r, fx = self.run_sitemap(pages)
        self.assertEqual(len(names(r)), 10)

    def test_no_probe_when_the_site_already_has_products(self):
        urls = ["https://%s/products/a/item-%s" % (HOST, c) for c in "abcdefghij"]
        r, fx = self.run_sitemap({"https://%s/sitemap.xml" % HOST: _urlset(urls)})
        self.assertNotIn("https://%s/en-gb/sitemap.xml" % HOST, fx.calls)

    def test_declared_non_uk_locale_sitemap_gets_its_uk_twin(self):
        self.assertEqual(
            cs.uk_siblings_of_locale_sitemap("https://x.com/de-de/google-sitemap.php"),
            ["https://x.com/en-gb/google-sitemap.php", "https://x.com/en-uk/google-sitemap.php"])
        self.assertEqual(cs.uk_siblings_of_locale_sitemap("https://x.com/en-gb/sitemap.xml"), [])
        self.assertEqual(cs.uk_siblings_of_locale_sitemap("https://x.com/sitemap.xml"), [])


ROBOTS_OK = "User-agent: *\nDisallow: /private/\n"


def _page(*hrefs):
    return "<html><body>%s</body></html>" % "".join('<a href="%s">x</a>' % h for h in hrefs)


class LinkFollowing(Base):
    def run_follow(self, pages, **kw):
        fx = Fx(pages)
        cs.get = fx
        self.real_pause, cs.PAUSE = cs.PAUSE, 0
        try:
            return cs.link_follow_products(HOST, **kw), fx
        finally:
            cs.PAUSE = self.real_pause

    def site(self, n=10):
        pages = {"https://%s/robots.txt" % HOST: ROBOTS_OK,
                 "https://%s/" % HOST: _page("/en-gb/products", "/about", "https://other.com/products/x",
                                           "/private/products/secret")}
        pages["https://%s/en-gb/products" % HOST] = _page(
            "/en-gb/products/knees/", "/en-gb/products/orthotics/")
        pages["https://%s/en-gb/products/knees" % HOST] = _page(
            *["/en-gb/products/knees/knee-%d/" % i for i in range(n)])
        pages["https://%s/en-gb/products/orthotics" % HOST] = _page(
            *["/en-gb/products/orthotics/brace-%d" % i for i in range(4)] + ["/about"])
        return pages

    def test_finds_products_by_following_category_links(self):
        (shaped, why), fx = self.run_follow(self.site())
        self.assertIsNotNone(shaped, why)
        got = {p["n"] for p in shaped["products"]}
        self.assertIn("Knee 0", got)
        self.assertIn("Brace 3", got)
        self.assertNotIn("Knees", got)                    # category pages are prefixes
        self.assertEqual(shaped["structureFrom"], "links")
        self.assertIn("no sitemap", shaped["captureCaveat"])

    def test_stays_on_this_site_and_honours_robots(self):
        (shaped, why), fx = self.run_follow(self.site())
        self.assertFalse([c for c in fx.calls if "other.com" in c])
        self.assertFalse([c for c in fx.calls if "/private/" in c])
        self.assertNotIn("https://%s/about" % HOST, fx.calls)

    def test_robots_disallowing_the_product_path_reads_nothing(self):
        pages = self.site()
        pages["https://%s/robots.txt" % HOST] = "User-agent: *\nDisallow: /en-gb/products\n"
        (shaped, why), fx = self.run_follow(pages)
        self.assertIsNone(shaped)
        self.assertFalse([c for c in fx.calls if "/en-gb/products" in c])

    def test_page_cap_refuses_rather_than_publishing_a_partial_read(self):
        old = cs.LINK_FOLLOW_MAX_PAGES
        cs.LINK_FOLLOW_MAX_PAGES = 3
        try:
            (shaped, why), _ = self.run_follow(self.site(30))
        finally:
            cs.LINK_FOLLOW_MAX_PAGES = old
        self.assertIsNone(shaped)
        self.assertIn("cap", why)

    def test_nothing_found_is_a_clean_refusal(self):
        (shaped, why), _ = self.run_follow({"https://%s/robots.txt" % HOST: ROBOTS_OK,
                                            "https://%s/" % HOST: _page("/about")})
        self.assertIsNone(shaped)

    def test_fallback_only_when_the_site_has_no_sitemap_at_all(self):
        # a site whose sitemap is readable but holds no products must not be crawled by links
        fx = Fx({"https://%s/sitemap.xml" % HOST: _urlset(["https://%s/about" % HOST])})
        cs.get = fx
        cs.sitemap_products(HOST)
        self.assertEqual(cs.sitemap_products.urls_read, 1)
        cs.get = Fx({})
        cs.sitemap_products(HOST)
        self.assertEqual(cs.sitemap_products.urls_read, 0)


if __name__ == "__main__":
    unittest.main()
