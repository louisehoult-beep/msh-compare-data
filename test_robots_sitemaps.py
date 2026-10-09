"""Regression cover for robots_sitemaps(), added 09/10/2026.

sitemap_products() used to read only /sitemap.xml and /sitemap_index.xml, so a
site that declares its sitemap elsewhere in robots.txt (Stryker:
/sitemap-index.xml, Owen Mumford: /sitemaps/sitemap_index.xml) was refused as
having no sitemap. These tests pin that the declared sitemap is read first,
that another host's sitemap is never followed, and that the defaults stay.

Run: python3 test_robots_sitemaps.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import crawl_supplier_site as cs  # noqa: E402 (path insert must come first)

ROBOTS = """User-agent: *
Disallow: /admin/
Sitemap: https://www.example-med.com/sitemaps/sitemap_index.xml
sitemap:https://example-med.com/products-sitemap.xml
Sitemap: https://cdn.other-host.net/sitemap.xml
Sitemap: https://www.example-med.com/sitemaps/sitemap_index.xml
"""


class FakeGet:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def __call__(self, url, as_json=False, timeout=30):
        self.calls.append(url)
        if url in self.pages:
            return self.pages[url], {}
        raise OSError("404 " + url)


class RobotsSitemaps(unittest.TestCase):
    def setUp(self):
        self.real_get = cs.get

    def tearDown(self):
        cs.get = self.real_get

    def test_reads_declared_same_site_sitemaps_once_in_order(self):
        cs.get = FakeGet({"https://www.example-med.com/robots.txt": ROBOTS})
        self.assertEqual(cs.robots_sitemaps("www.example-med.com"), [
            "https://www.example-med.com/sitemaps/sitemap_index.xml",
            "https://example-med.com/products-sitemap.xml",
        ])

    def test_no_robots_file_means_no_declared_sitemaps(self):
        cs.get = FakeGet({})
        self.assertEqual(cs.robots_sitemaps("www.example-med.com"), [])

    def test_sitemap_products_reads_the_declared_sitemap_before_defaults(self):
        fake = FakeGet({"https://www.example-med.com/robots.txt": ROBOTS})
        cs.get = fake
        cs.sitemap_products("www.example-med.com")
        reads = [u for u in fake.calls if not u.endswith("robots.txt")]
        self.assertEqual(reads[0], "https://www.example-med.com/sitemaps/sitemap_index.xml")
        self.assertIn("https://www.example-med.com/sitemap.xml", reads)
        self.assertNotIn("https://cdn.other-host.net/sitemap.xml", reads)


if __name__ == "__main__":
    unittest.main()
