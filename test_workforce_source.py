"""Offline tests for scripts/refresh_workforce_source.py (25/11/2026)."""
import datetime
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import refresh_workforce_source as rws

ZIP = ("https://files.digital.nhs.uk/40/532D4E/NHS%20HCHS%20Workforce%20Statistics%2C%20"
       "Trusts%20and%20core%20organisations%20-%20CSV%20data%20files%2C%20August%202026.zip")
TODAY = datetime.date(2026, 11, 25)


def fake(pages):
    def g(url):
        if url not in pages:
            raise IOError("404 %s" % url)
        return pages[url]
    return g


INDEX_HTML = ('<a href="/data-and-information/publications/statistical/nhs-workforce-statistics/september-2026">S</a>'
              '<a href="/data-and-information/publications/statistical/nhs-workforce-statistics/august-2026">A</a>'
              '<a href="/data-and-information/publications/statistical/nhs-workforce-statistics/december-2026">future</a>')


class WorkforceSource(unittest.TestCase):
    def test_newest_with_zip_wins_and_future_skipped(self):
        pages = {rws.INDEX: INDEX_HTML,
                 rws.INDEX + "/september-2026": "no zip here",
                 rws.INDEX + "/august-2026": '<a href="%s">zip</a>' % ZIP}
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "w.json")
            self.assertEqual(rws.main(fake(pages), TODAY, out), 0)
            doc = json.load(open(out))
        self.assertEqual(doc["publication"], rws.INDEX + "/august-2026")
        self.assertEqual(doc["file"], ZIP)
        self.assertEqual(doc["readOn"], "2026-11-25")

    def test_nothing_found_leaves_file_alone(self):
        pages = {rws.INDEX: INDEX_HTML}
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "w.json")
            open(out, "w").write('{"keep": 1}')
            self.assertEqual(rws.main(fake(pages), TODAY, out), 1)
            self.assertEqual(json.load(open(out)), {"keep": 1})


if __name__ == "__main__":
    unittest.main()
