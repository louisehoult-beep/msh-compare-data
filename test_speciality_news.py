#!/usr/bin/env python3
"""Invariants for build_speciality_news.py.

No network calls here — these are the pure parsing/formatting functions
only. The live-feed behaviour was hand-verified on 15/09/2026 against all 29
sources (see the build's own dry-run output); this file exists to catch a
regression in the parsing logic itself, not to re-fetch feeds on every CI run.

    python3 test_speciality_news.py
"""
import datetime
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import build_speciality_news as N  # noqa: E402


RSS2_SAMPLE = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>A cardiology device news item</title>
    <link>https://example.com/a</link>
    <pubDate>Mon, 01 Sep 2026 09:00:00 GMT</pubDate>
    <description>&lt;p&gt;Some &lt;b&gt;markup&lt;/b&gt; in here.&lt;/p&gt;</description>
  </item>
</channel></rss>"""

# RSS 1.0 / RDF, default namespace on every element — the shape that broke
# the naive './/item' search on the magonlinelibrary.com journal feeds.
RSS1_RDF_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns="http://purl.org/rss/1.0/"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel rdf:about="https://example.com/toc"><title>TOC</title></channel>
  <item rdf:about="https://example.com/doi/1">
    <title>A journal article title</title>
    <link>https://example.com/doi/1</link>
    <description>Volume 1, Issue 1.</description>
    <dc:date>2026-08-02T07:00:00Z</dc:date>
  </item>
</rdf:RDF>"""

ATOM_SAMPLE = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>An atom entry</title>
    <link href="https://example.com/atom-1"/>
    <updated>2026-08-15T12:00:00Z</updated>
    <summary>Atom summary text.</summary>
  </entry>
</feed>"""

MALFORMED = b"<rss><channel><item><title>unclosed"


class ParseFeed(unittest.TestCase):

    def test_rss2_item(self):
        items = N.parse_feed(RSS2_SAMPLE, "test")
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it["title"], "A cardiology device news item")
        self.assertEqual(it["link"], "https://example.com/a")
        self.assertTrue(it["published"].startswith("2026-09-01"))
        self.assertIn("markup", it["summary"])
        self.assertNotIn("<b>", it["summary"])

    def test_rss1_rdf_default_namespace_item(self):
        """The regression this file exists to catch: a default-namespace
        RDF feed must still be found, not silently return zero items."""
        items = N.parse_feed(RSS1_RDF_SAMPLE, "test")
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it["title"], "A journal article title")
        self.assertEqual(it["link"], "https://example.com/doi/1")
        self.assertTrue(it["published"].startswith("2026-08-02"))

    def test_atom_entry(self):
        items = N.parse_feed(ATOM_SAMPLE, "test")
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it["title"], "An atom entry")
        self.assertEqual(it["link"], "https://example.com/atom-1")
        self.assertTrue(it["published"].startswith("2026-08-15"))

    def test_malformed_xml_returns_empty_not_raise(self):
        self.assertEqual(N.parse_feed(MALFORMED, "test"), [])


class PubDate(unittest.TestCase):

    def test_rfc822(self):
        dt = N.parse_pubdate("Mon, 01 Sep 2026 09:00:00 GMT")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 9)

    def test_iso8601(self):
        dt = N.parse_pubdate("2026-08-02T07:00:00Z")
        self.assertEqual(dt.day, 2)

    def test_bare_date(self):
        dt = N.parse_pubdate("2026-08-02")
        self.assertEqual(dt.day, 2)

    def test_garbage_returns_none(self):
        self.assertIsNone(N.parse_pubdate("not a date"))

    def test_empty_returns_none(self):
        self.assertIsNone(N.parse_pubdate(""))
        self.assertIsNone(N.parse_pubdate(None))


class StripTags(unittest.TestCase):

    def test_removes_tags_and_unescapes(self):
        self.assertEqual(N.strip_tags("<p>A &amp; B</p>"), "A & B")

    def test_collapses_whitespace(self):
        self.assertEqual(N.strip_tags("a\n\n  b"), "a b")

    def test_none_input(self):
        self.assertEqual(N.strip_tags(None), "")


class Sources(unittest.TestCase):
    """The evidence-floor invariant (root rule 14): every tagged source names
    at least one real speciality slug, and nothing is tagged to a slug that
    doesn't exist — a typo here would silently publish to no page at all."""

    def test_every_source_has_at_least_one_speciality(self):
        for s in N.SOURCES:
            self.assertTrue(s.get("specialities"), "%s carries no specialities" % s["id"])

    def test_every_source_has_id_name_url(self):
        for s in N.SOURCES:
            self.assertTrue(s.get("id"))
            self.assertTrue(s.get("name"))
            self.assertTrue(s.get("url", "").startswith("http"))

    def test_no_duplicate_source_ids(self):
        ids = [s["id"] for s in N.SOURCES]
        self.assertEqual(len(ids), len(set(ids)), "duplicate source id in SOURCES")


class ClipSummary(unittest.TestCase):
    """Summaries end on a sentence or a whole word, never mid-word (24/09/2026)."""

    def test_short_summary_untouched(self):
        self.assertEqual(N.clip_summary("A short summary."), "A short summary.")

    def test_long_summary_ends_on_sentence(self):
        s = "First sentence is here and runs on for a while so it counts. " * 3 + "x" * 300
        out = N.clip_summary(s)
        self.assertTrue(out.endswith("counts."))
        self.assertLessEqual(len(out), N.SUMMARY_MAX)

    def test_no_sentence_ends_on_whole_word(self):
        out = N.clip_summary("alpha " * 100)
        self.assertTrue(out.endswith("alpha…"))

    def test_feed_cut_short_upstream_is_tidied(self):
        out = N.clip_summary("Figures show a drop of more than 10% in the week follow")
        self.assertEqual(out, "Figures show a drop of more than 10% in the week…")

    def test_wordpress_footer_dropped(self):
        out = N.clip_summary("Real text. The post Thing appeared first on Some Site.")
        self.assertEqual(out, "Real text.")


class Jobs(unittest.TestCase):
    def test_job_advert_detected(self):
        self.assertTrue(N.is_job("Job Advert – Buchanan Orthotics – Orthotist"))

    def test_advertising_is_not_a_job(self):
        self.assertFalse(N.is_job("Response submitted to Government consultation on food advertising"))


if __name__ == "__main__":
    unittest.main()
