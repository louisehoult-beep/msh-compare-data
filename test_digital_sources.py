#!/usr/bin/env python3
"""
test_digital_sources.py - prove scripts/refresh_digital_sources.py parses NHS App partner
tables and keeps last week's block when a source cannot be read. No network. Stdlib only.

  python3 test_digital_sources.py     exit 0 = pass.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import refresh_digital_sources as rds  # noqa: E402

APP = """<main><h3>Online consultations</h3><table>
<tr><th>Organisation</th><th>Product</th><th>Functionality</th></tr>
<tr><td>Accurx</td><td>Patient Triage</td><td>Medical query: ask</td></tr></table>
<h3>Primary care</h3><table>
<tr><th>Organisation</th><th>Functionality</th></tr>
<tr><td>Abtrace*</td><td>Notifications and Messaging: text</td></tr></table>
<h3>Secondary care</h3><table>
<tr><th>Organisation</th><th>Product</th><th>Functionality</th></tr>
<tr><td>None currently planned</td><td></td><td></td></tr></table>
<p>Last edited: 25 September 2026 3:50 pm</p></main>"""


class App(unittest.TestCase):
    def test_rows(self):
        rows = rds.app_rows(APP, "live")
        self.assertEqual([(r["section"], r["organisation"], r["product"]) for r in rows],
                         [("Online consultations", "Accurx", "Patient Triage"),
                          ("Primary care", "Abtrace", None)])

    def test_functionality_text_not_copied(self):
        self.assertNotIn("Medical query", str(rds.app_rows(APP, "live")))

    def test_empty_page_raises(self):
        with self.assertRaises(RuntimeError):
            rds.build_app(lambda u: "<main></main>", "2026-10-20")


class Build(unittest.TestCase):
    def test_total_failure_raises(self):
        def f(url, **k):
            raise RuntimeError("down")
        with self.assertRaises(RuntimeError):
            rds.build(f, "2026-10-20")

    def test_failed_block_keeps_previous_and_flags(self):
        def f(url, **k):
            if "digital-maturity" in url:
                raise RuntimeError("down")
            return APP
        prev = {"dma": {"verifiedOn": "2026-10-13", "providers": []}}
        doc = rds.build(f, "2026-10-20", prev)
        self.assertIn("staleNote", doc["dma"])
        self.assertEqual(doc["dma"]["verifiedOn"], "2026-10-13")
        self.assertEqual(len(doc["nhsApp"]["rows"]), 6)

    def test_not_added_carries_reasons(self):
        doc = rds.build(lambda u, **k: APP, "2026-10-20", {"dma": {"verifiedOn": "x"}})
        names = [n["source"] for n in doc["notAdded"]]
        self.assertTrue(any("PARD" in n for n in names) and any("SBRI" in n for n in names))
        self.assertTrue(all(n["reason"].startswith("Not added") for n in doc["notAdded"]))


if __name__ == "__main__":
    unittest.main()
