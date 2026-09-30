#!/usr/bin/env python3
"""Offline tests for scripts/crawl_supplier_site.py fetch behaviour.

Covers four OUTSTANDING items, all with `get` and `time.sleep` mocked (no network):
  ^o598  allowed(): one 3s retry on a first 403 for robots.txt; 401 and a repeated 403 refuse
  ^o564  reachable_host(): prefer a host that answers AND serves an XML sitemap
  ^o388  _wp_read_type(): brand-filed product_cat swaps in the site's type taxonomy
  ^o203  WordPress / Store read URLs carry orderby=date&order=asc

Run:  python3 test_crawl_fetch_behaviour.py
"""
import io
import os
import sys
import unittest
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import crawl_supplier_site as c

ROBOTS_ALLOW = "User-agent: *\nDisallow:\n"
ROBOTS_DENY = "User-agent: *\nDisallow: /\n"
SITEMAP = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'


def http_err(code):
    return urllib.error.HTTPError("https://x/", code, "err", {}, io.BytesIO(b""))


class Patched(unittest.TestCase):
    def setUp(self):
        self._get, self._sleep = c.get, c.time.sleep
        self.sleeps, self.calls = [], []
        c.time.sleep = lambda s: self.sleeps.append(s)

    def tearDown(self):
        c.get, c.time.sleep = self._get, self._sleep

    def script(self, fn):
        def g(url, as_json=False, timeout=30):
            self.calls.append(url)
            return fn(url)
        c.get = g


class RobotsRetry(Patched):
    def seq(self, *results):
        it = iter(results)

        def fn(url):
            r = next(it)
            if isinstance(r, int):
                raise http_err(r)
            return r, {}
        self.script(fn)

    def test_first_403_then_ok_is_allowed(self):
        self.seq(403, ROBOTS_ALLOW)
        self.assertTrue(c.allowed("x.co.uk"))

    def test_the_retry_waits_three_seconds(self):
        self.seq(403, ROBOTS_ALLOW)
        c.allowed("x.co.uk")
        self.assertEqual(self.sleeps, [3.0])

    def test_repeated_403_refuses(self):
        self.seq(403, 403)
        self.assertFalse(c.allowed("x.co.uk"))

    def test_403_is_retried_exactly_once(self):
        self.seq(403, 403)
        c.allowed("x.co.uk")
        self.assertEqual(len(self.calls), 2)

    def test_401_refuses_without_retry(self):
        self.seq(401)
        self.assertFalse(c.allowed("x.co.uk"))
        self.assertEqual(self.sleeps, [])

    def test_404_means_nothing_to_obey_no_retry(self):
        self.seq(404)
        self.assertTrue(c.allowed("x.co.uk"))
        self.assertEqual(len(self.calls), 1)

    def test_clean_first_read_does_not_sleep(self):
        self.seq(ROBOTS_ALLOW)
        self.assertTrue(c.allowed("x.co.uk"))
        self.assertEqual(self.sleeps, [])

    def test_retry_that_returns_a_disallow_still_refuses(self):
        self.seq(403, ROBOTS_DENY)
        self.assertFalse(c.allowed("x.co.uk"))


class ReachableHost(Patched):
    def hosts(self, answering, with_sitemap):
        def fn(url):
            host = url.split("/")[2]
            if host not in answering:
                raise OSError("no route")
            if url.endswith("/") and url.count("/") == 3:
                return "<html>" + "x" * 400 + "</html>", {}
            if host in with_sitemap and url.endswith("/sitemap.xml"):
                return SITEMAP, {}
            raise http_err(404)
        self.script(fn)

    def test_prefers_the_host_with_a_sitemap_over_the_first_answering(self):
        self.hosts({"crest.co.uk", "www.crest.co.uk"}, {"www.crest.co.uk"})
        self.assertEqual(c.reachable_host("crest.co.uk"), "www.crest.co.uk")

    def test_bare_host_wins_when_it_serves_the_sitemap(self):
        self.hosts({"oticon.co.uk", "www.oticon.co.uk"}, {"oticon.co.uk"})
        self.assertEqual(c.reachable_host("oticon.co.uk"), "oticon.co.uk")

    def test_falls_back_to_first_answering_when_neither_has_a_sitemap(self):
        self.hosts({"a.co.uk", "www.a.co.uk"}, set())
        self.assertEqual(c.reachable_host("a.co.uk"), "a.co.uk")

    def test_only_www_answers(self):
        self.hosts({"www.coloplast.co.uk"}, set())
        self.assertEqual(c.reachable_host("coloplast.co.uk"), "www.coloplast.co.uk")

    def test_nothing_answers_returns_none(self):
        self.hosts(set(), set())
        self.assertIsNone(c.reachable_host("gone.co.uk"))

    def test_html_at_sitemap_path_is_not_a_sitemap(self):
        def fn(url):
            return "<html><body>" + "page " * 200 + "</body></html>", {}
        self.script(fn)
        self.assertFalse(c._serves_xml_sitemap("spa.co.uk"))


def term(i, name, parent=0, count=5):
    return {"id": i, "name": name, "parent": parent, "count": count}


class BrandFiled(Patched):
    BASE = "https://p.co.uk/wp-json/wp/v2"
    TAXES = ["product_brand", "product_cat", "product_tag", "prod_type"]

    def site(self, cat, brand, typ):
        data = {"product_cat": cat, "product_brand": brand, "prod_type": typ}

        def fn(url):
            tax = url.split("?")[0].rsplit("/", 1)[1]
            if tax in data:
                return (data[tax] if "page=1" in url else []), {}
            if tax == "product":
                return [{"id": 1, "title": {"rendered": "Probe"}, "prod_type": [50], "product_cat": [1]}], {"X-WP-Total": "1"}
            raise http_err(404)
        self.script(fn)

    BRANDS = [term(1, "GE HealthCare"), term(2, "Philips"), term(3, "Mindray")]
    CATS_BRAND = [term(1, "GE HealthCare"), term(2, "Philips"), term(3, "Mindray"), term(4, "Uncategorized")]
    TYPES = [term(50, "Ultrasound Probes"), term(51, "Parts & Accessories")]

    def test_brand_filed_swaps_in_the_type_taxonomy(self):
        self.site(self.CATS_BRAND, self.BRANDS, self.TYPES)
        prods, cats, meta = c._wp_read_type(self.BASE, "product", self.TAXES)
        self.assertEqual(meta["brandFiledSwappedTo"], "prod_type")
        self.assertIn("product:prod_type:50", cats)
        self.assertEqual(prods[0]["cats"], ["product:prod_type:50"])

    def test_no_type_taxonomy_flags_without_swapping(self):
        self.site(self.CATS_BRAND, self.BRANDS, self.TYPES)
        prods, cats, meta = c._wp_read_type(self.BASE, "product", ["product_brand", "product_cat"])
        self.assertTrue(meta["brandFiled"])
        self.assertIsNone(meta["brandFiledSwappedTo"])
        self.assertIn("product:product_cat:1", cats)

    def test_real_categories_are_not_flagged(self):
        real = [term(1, "Ultrasound Probes"), term(2, "Ultrasound Machines"), term(3, "Parts")]
        self.site(real, self.BRANDS, self.TYPES)
        _, cats, meta = c._wp_read_type(self.BASE, "product", self.TAXES)
        self.assertFalse(meta["brandFiled"])
        self.assertIn("product:product_cat:1", cats)

    def test_type_taxonomy_never_picks_product_type(self):
        self.assertIsNone(c.type_taxonomy(["product_type", "product_cat"]))
        self.assertEqual(c.type_taxonomy(["product_type", "prod_type"]), "prod_type")

    def test_leading_digit_junk_in_a_name_still_matches_brand(self):
        cats = {"a": {"name": "2GE HealthCare", "parent": 0}, "b": {"name": "Philips", "parent": 0}}
        brands = {"x": {"name": "GE HealthCare"}, "y": {"name": "Philips"}}
        self.assertTrue(c.is_brand_filed(cats, brands))


class ReadOrder(Patched):
    def test_wp_read_urls_carry_oldest_first(self):
        def fn(url):
            tax = url.split("?")[0].rsplit("/", 1)[1]
            if tax == "product_cat":
                return [], {}
            return [], {}
        self.script(fn)
        c._wp_read_type("https://p.co.uk/wp-json/wp/v2", "product", ["product_cat"])
        reads = [u for u in self.calls if u.split("?")[0].endswith("/product")]
        self.assertTrue(reads)
        for u in reads:
            self.assertIn("orderby=date&order=asc", u)


if __name__ == "__main__":
    unittest.main(verbosity=1)
