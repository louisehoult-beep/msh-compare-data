#!/usr/bin/env python3
"""Invariants for the cloud-pipeline merge in build_speciality_news.py.

Added 16/09/2026 with the merge itself. Separate file from
test_speciality_news.py, which covers the RSS parsing and predates this.

No network: fetch_pipeline_intel is exercised against a stubbed urlopen, and
build() against stubbed fetch + pipeline. What is actually being protected here
is the set of things that were easy to get wrong and silent when wrong:

  * the private repo needs the CONTENTS API and a token, not raw.github
  * a missing token or a failed fetch must degrade to trade-press-only, never
    raise and never fail the daily build
  * an opportunity must not be pushed off the end of a page by six older
    trade-press headlines
  * an --only run must not rewrite files for slugs it never fetched RSS for

    python3 test_speciality_news_pipeline_merge.py
"""
import io
import json
import os
import sys
import unittest
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import build_speciality_news as N  # noqa: E402


HANDOFF = {
    "generatedAt": "2026-09-16T17:43:12Z",
    "maxAgeDays": 60,
    "vocabulary": ["urology", "respiratory"],
    "specialities": {
        "urology": [
            {"id": "a1", "title": "A urology opportunity", "url": "https://example.com/u1",
             "date": "2026-09-01", "summary": "Summary text.", "source_id": "cowork_intel",
             "category": "industry", "opportunity": True},
        ],
        "respiratory": [
            {"id": "b1", "title": "A respiratory item", "url": "https://example.com/r1",
             "date": "2026-09-02", "summary": "More text.", "source_id": "cowork_intel",
             "category": "policy", "opportunity": False},
        ],
    },
}


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


def _stub_urlopen(body, captured=None):
    def _open(req, timeout=None):
        if captured is not None:
            captured.append(req)
        return _FakeResponse(body)
    return _open


class PipelineEntry(unittest.TestCase):
    def test_renames_url_and_date_to_this_scripts_names(self):
        e = N.pipeline_entry(HANDOFF["specialities"]["urology"][0])
        # The renderer only understands link/published. A row that kept url/date
        # would render with a dead link and a blank date, and look like a feed bug.
        self.assertEqual(e["link"], "https://example.com/u1")
        self.assertEqual(e["published"], "2026-09-01")
        self.assertNotIn("url", e)
        self.assertNotIn("date", e)

    def test_marks_tier_and_reason(self):
        e = N.pipeline_entry(HANDOFF["specialities"]["urology"][0])
        self.assertIs(e["verified"], True)
        self.assertIs(e["opportunity"], True)
        self.assertEqual(e["source"], N.PIPELINE_LABEL)

    def test_missing_date_becomes_none_not_empty_string(self):
        # fmtDate('') and fmtDate(null) both render blank, but sort_key calls
        # parse_pubdate, which must get None rather than "".
        e = N.pipeline_entry({"title": "t", "url": "https://x", "date": ""})
        self.assertIsNone(e["published"])

    def test_summary_is_capped_like_an_rss_item(self):
        e = N.pipeline_entry({"title": "t", "url": "https://x", "summary": "word " * 100})
        self.assertLessEqual(len(e["summary"]), N.SUMMARY_MAX + 1)
        self.assertTrue(e["summary"].endswith("word…"))


class FetchPipelineIntel(unittest.TestCase):
    def test_no_token_returns_empty_and_does_not_raise(self):
        self.assertEqual(N.fetch_pipeline_intel(token=""), {})

    def test_uses_contents_api_with_raw_accept_and_bearer_token(self):
        captured = []
        real = N.urllib.request.urlopen
        N.urllib.request.urlopen = _stub_urlopen(json.dumps(HANDOFF).encode(), captured)
        try:
            N.fetch_pipeline_intel(token="tok123")
        finally:
            N.urllib.request.urlopen = real
        req = captured[0]
        # raw.githubusercontent 404s on a private repo however good the token is.
        self.assertIn("api.github.com", req.full_url)
        self.assertNotIn("raw.githubusercontent", req.full_url)
        self.assertEqual(req.get_header("Accept"), "application/vnd.github.raw")
        self.assertEqual(req.get_header("Authorization"), "Bearer tok123")

    def test_parses_rows_into_entries_keyed_by_slug(self):
        real = N.urllib.request.urlopen
        N.urllib.request.urlopen = _stub_urlopen(json.dumps(HANDOFF).encode())
        try:
            got = N.fetch_pipeline_intel(token="tok")
        finally:
            N.urllib.request.urlopen = real
        self.assertEqual(sorted(got), ["respiratory", "urology"])
        self.assertEqual(got["urology"][0]["title"], "A urology opportunity")

    def test_http_error_degrades_to_empty(self):
        def _boom(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)
        real = N.urllib.request.urlopen
        N.urllib.request.urlopen = _boom
        try:
            self.assertEqual(N.fetch_pipeline_intel(token="expired"), {})
        finally:
            N.urllib.request.urlopen = real

    def test_unparseable_body_degrades_to_empty(self):
        real = N.urllib.request.urlopen
        N.urllib.request.urlopen = _stub_urlopen(b"<html>404</html>")
        try:
            self.assertEqual(N.fetch_pipeline_intel(token="tok"), {})
        finally:
            N.urllib.request.urlopen = real

    def test_document_without_specialities_object_degrades_to_empty(self):
        real = N.urllib.request.urlopen
        N.urllib.request.urlopen = _stub_urlopen(json.dumps({"items": []}).encode())
        try:
            self.assertEqual(N.fetch_pipeline_intel(token="tok"), {})
        finally:
            N.urllib.request.urlopen = real

    def test_rows_without_title_or_link_are_dropped(self):
        doc = {"specialities": {"urology": [
            {"title": "", "url": "https://x"},
            {"title": "t", "url": ""},
        ]}}
        real = N.urllib.request.urlopen
        N.urllib.request.urlopen = _stub_urlopen(json.dumps(doc).encode())
        try:
            self.assertEqual(N.fetch_pipeline_intel(token="tok"), {})
        finally:
            N.urllib.request.urlopen = real


class BuildMerge(unittest.TestCase):
    """build() end to end, with both fetches stubbed, writing to a temp dir."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self._real_out, N.OUT_DIR = N.OUT_DIR, self._tmp
        self._real_sources = N.SOURCES
        self._real_fetch = N.fetch
        self._real_pipe = N.fetch_pipeline_intel

    def tearDown(self):
        import shutil
        N.OUT_DIR = self._real_out
        N.SOURCES = self._real_sources
        N.fetch = self._real_fetch
        N.fetch_pipeline_intel = self._real_pipe
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _read(self, slug):
        with open(os.path.join(self._tmp, "%s.json" % slug), encoding="utf-8") as fh:
            return json.load(fh)

    def _rss(self, n, slug="urology", days_ago=1):
        import datetime
        base = datetime.datetime.now(datetime.timezone.utc)
        items = []
        for i in range(n):
            when = base - datetime.timedelta(days=days_ago + i)
            items.append(
                "<item><title>Trade item %d</title><link>https://example.com/t%d</link>"
                "<pubDate>%s</pubDate></item>"
                % (i, i, when.strftime("%a, %d %b %Y %H:%M:%S GMT")))
        N.SOURCES = [{"id": "fake", "name": "Fake Feed", "url": "https://feed.example",
                      "specialities": [slug]}]
        xml = ('<?xml version="1.0"?><rss version="2.0"><channel>%s</channel></rss>'
               % "".join(items)).encode()
        N.fetch = lambda url: xml

    def test_opportunity_is_not_cut_by_newer_trade_press(self):
        # The whole point of the second sort. Six fresher headlines would
        # otherwise fill the cap and drop the one item a rep can act on.
        self._rss(8, slug="urology")
        opp = dict(N.pipeline_entry(HANDOFF["specialities"]["urology"][0]))
        opp["published"] = "2026-01-01"          # deliberately the OLDEST item
        N.fetch_pipeline_intel = lambda token=None: {"urology": [opp]}
        N.build(pause=0)
        items = self._read("urology")["items"]
        self.assertEqual(len(items), N.ITEMS_PER_SPECIALITY)
        self.assertEqual(items[0]["title"], "A urology opportunity")
        self.assertIs(items[0]["opportunity"], True)

    def test_merged_slug_with_no_rss_source_still_gets_a_file(self):
        self._rss(1, slug="urology")
        N.fetch_pipeline_intel = lambda token=None: {
            "respiratory": [N.pipeline_entry(HANDOFF["specialities"]["respiratory"][0])]}
        N.build(pause=0)
        items = self._read("respiratory")["items"]
        self.assertEqual(len(items), 1)
        self.assertIs(items[0]["verified"], True)

    def test_only_run_does_not_write_pipeline_only_slugs(self):
        # An --only run fetches one RSS source. Writing respiratory.json from it
        # would rewrite that page's file with merged rows alone and wipe its
        # trade-press items.
        self._rss(1, slug="urology")
        N.fetch_pipeline_intel = lambda token=None: {
            "respiratory": [N.pipeline_entry(HANDOFF["specialities"]["respiratory"][0])]}
        N.build(only_id="fake", pause=0)
        self.assertTrue(os.path.exists(os.path.join(self._tmp, "urology.json")))
        self.assertFalse(os.path.exists(os.path.join(self._tmp, "respiratory.json")))

    def test_pipeline_failure_leaves_trade_press_intact(self):
        self._rss(3, slug="urology")
        N.fetch_pipeline_intel = lambda token=None: {}
        N.build(pause=0)
        items = self._read("urology")["items"]
        self.assertEqual(len(items), 3)
        self.assertTrue(all(not i.get("verified") for i in items))


if __name__ == "__main__":
    unittest.main(verbosity=2)
