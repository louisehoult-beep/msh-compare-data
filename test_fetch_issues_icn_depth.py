"""Regression cover for the ICN index depth and the containment vocabulary in
fetch_issues.py, added 30/09/2026.

THE FAILURE THIS PINS. fetch_issues.py read page 1 of NHS Supply Chain's ICN
index and nothing else. The index is ordered by last update, so a live
shortage that stops being updated sinks out of reach. ICN 3260 (Ontex UK Ltd
belted pads, 19 codes, three suspended, resolution 27/11/2026) was last updated
24/06/2026 and sat on page 10 of 15 on 30/09/2026: open, and never in the feed.
Even if it had been read, no continence term matched "Belted Pads", so it would
have been filed as unsorted.

What must hold:
  * an open Supply Disruption on a deep page is considered;
  * a deep Resolved disruption, and a deep recall or alert, are NOT (they are
    one-off events from before the feed existed; admitting them floods the tab);
  * everything on page 1 is still considered, as before;
  * belted/shaped/absorbent pads file under continence, and defibrillation
    pads and a tissue pad do NOT.

Offline: the fetcher is replaced with fixture pages, so no network requests.

Run: python3 test_fetch_issues_icn_depth.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_issues as F  # noqa: E402

BASE = "https://www.supplychain.nhs.uk/icn/"


def card(slug, title, date, status, typ):
    return ('<div class="post-item">\n<h3><a href="%s%s/">%s</a></h3>\n'
            '<p><small>  <strong>Ref: 2026/0000</strong> - %s</small></p>\n'
            '<p>Important Customer Notice <span class="icn-status-red">Status <strong>%s</strong>'
            '</span> <span class="icn-tag-blue">Type <strong>%s</strong></span></p>\n'
            '<a class="pull-right" href="%s%s/" aria-label="View %s">Find out more</span></a>\n'
            '</div>\n' % (BASE, slug, title, date, status, typ, BASE, slug, title))


def page(*cards):
    return '<div class="post-list">\n' + "".join(cards) + "</div>\n</div>\n<div class=\"x\"></div>"


PAGE1 = page(
    card("supply-issues-cellpath-microscope-slide-kth110",
         "Supply Issues Cellpath Microscope Slide KTH110 (ICN 3343)", "29 September 2026",
         "Resolved", "Supply Disruption"),
    card("product-update-acme-widget", "Product Update Acme Widget (ICN 3490)",
         "29 September 2026", "New", "Delisting"),
)
PAGE10 = page(
    card("supply-issues-ontex-uk-ltd-belted-pads", "Supply Issues Ontex UK Ltd Belted Pads (ICN 3260)",
         "24 June 2026", "Update", "Supply Disruption"),
    card("supply-issues-old-thing-resolved", "Supply Issues Old Thing Resolved (ICN 3100)",
         "20 June 2026", "Resolved", "Supply Disruption"),
    card("field-safety-notice-old-recall", "Field Safety Notice Old Recall Widget (ICN 2927)",
         "2 May 2025", "New", "Product Recall"),
)


def fixture_fetcher(pages):
    def f(url):
        if url == F.ICN_INDEX:
            return pages[1]
        n = int(url.rstrip("/").rsplit("/", 1)[1])
        return pages.get(n, page())       # past the end: an empty listing
    return f


class TestIcnDepth(unittest.TestCase):
    def run_pages(self, pages):
        log = []
        out = F.nhssc_notices(log, fetcher=fixture_fetcher(pages))
        return {c["url"].rsplit("/icn/", 1)[1].strip("/"): c for c in out}, log

    def test_deep_open_supply_disruption_is_considered(self):
        got, _ = self.run_pages({1: PAGE1, 2: PAGE10})
        self.assertIn("supply-issues-ontex-uk-ltd-belted-pads", got)
        self.assertEqual(got["supply-issues-ontex-uk-ltd-belted-pads"]["date"], "2026-06-24")

    def test_deep_resolved_and_recalls_are_not(self):
        got, _ = self.run_pages({1: PAGE1, 2: PAGE10})
        self.assertNotIn("supply-issues-old-thing-resolved", got)
        self.assertNotIn("field-safety-notice-old-recall", got)

    def test_page_one_unchanged(self):
        got, _ = self.run_pages({1: PAGE1, 2: PAGE10})
        # Page 1 admits everything, resolved and delisting included, as before.
        self.assertIn("supply-issues-cellpath-microscope-slide-kth110", got)
        self.assertIn("product-update-acme-widget", got)

    def test_stops_at_end_and_on_repeat(self):
        calls = []
        base = fixture_fetcher({1: PAGE1, 2: PAGE10, 3: PAGE10})

        def f(url):
            calls.append(url)
            return base(url)
        F.nhssc_notices([], fetcher=f)
        # page 3 repeats page 2's notices, so the walk stops there
        self.assertEqual(len(calls), 3)

    def test_deep_page_failure_keeps_page_one(self):
        def f(url):
            if url == F.ICN_INDEX:
                return PAGE1
            raise OSError("boom")
        log = []
        out = F.nhssc_notices(log, fetcher=f)
        self.assertEqual(len(out), 2)
        self.assertTrue(any("FAILED" in l for l in log))

    def test_markup_change_falls_back_to_links(self):
        html = '<a href="%ssupply-issues-x-y-z/">Supply Issues X Y Z (ICN 1)</a>' % BASE
        rows = F.parse_icn_index(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "")


class TestContainmentVocabulary(unittest.TestCase):
    def spec(self, title, slug):
        hay = (title + " " + slug.replace("-", " ")).lower()
        return next((s for s, kws in F.KEYWORDS.items() if any(k in hay for k in kws)), "")

    def test_belted_pads_file_as_continence(self):
        self.assertEqual(self.spec("Supply Issues Ontex UK Ltd Belted Pads (ICN 3260)",
                                   "supply-issues-ontex-uk-ltd-belted-pads"), "continence")
        self.assertEqual(self.spec("Supply Issues Acme Shaped Pads I9", "x"), "continence")
        self.assertEqual(self.spec("Supply Issues Acme Absorbent Pull-Up Pants D15", "x"), "continence")

    def test_other_pads_do_not(self):
        # Real titles on the ICN index on 30/09/2026.
        for t in ("Supply Issues Zoll Medical UK Ltd Defibrillation Pads FDJ8367 (ICN 2947)",
                  "Supply Issues Zoll Medical UK Ltd OneStep Defibrillation Pads Multiple Products (ICN 3351)",
                  "Field Safety Notice Olympus Thunderbeat Jaw Thunderbeat Probe Fracture and Tissue Pad "
                  "Detachment (ICN 3209)"):
            self.assertNotEqual(self.spec(t, "x"), "continence", t)


if __name__ == "__main__":
    unittest.main(verbosity=2)
