#!/usr/bin/env python3
r"""A revised NHSBSA month must not read as a month that was never published.

Added 18/09/2026, from the re-verification pass before the hospital-prescribing
tool was given a Hub page (^o49).

THE DEFECT
----------
`resources()` matched a monthly CSV with `re.search(r"(\d{6})$", name)`. The `$`
anchored the six digits to the end of the resource name, so NHSBSA's revised
files — named `HOSPITAL_DISP_COMMUNITY_202505FINAL` — matched nothing and were
dropped silently.

The consequence was not a visible error. `build()` takes a calendar range and
carries any month it cannot find as null, deliberately, so that an unpublished
month draws as a break in the line rather than as a collapse to zero. A month
that IS published but is invisible to the matcher takes exactly that same path:
it becomes a permanent, confidently-drawn gap, captioned "not published by
NHSBSA", in a sparkline where real data exists.

May 2025 is the worked example. The 15/08/2026 build recorded it as never
published, which was true that day. NHSBSA later published it as
`...202505FINAL`, and the tool would have gone on asserting the gap for as long
as the file was in the window.

THE RULE
--------
The six digits may be followed by an optional revision word. Where one month has
both a plain and a revised resource, the revised one wins — it is the later,
corrected file, and preferring the plain one would publish superseded numbers.

  python3 -m unittest test_hospital_prescribing_resources    exit 0 = holds
"""
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "scripts", "refresh_hospital_prescribing.py")


def load():
    spec = importlib.util.spec_from_file_location("rhp_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def package(*resources):
    """A CKAN package_show body carrying exactly these resources."""
    return json.dumps({"result": {"resources": list(resources)}})


def res(name, fmt="CSV", url=None):
    return {"name": name, "format": fmt, "url": url or ("https://x/%s.csv" % name.lower())}


class RevisedMonths(unittest.TestCase):
    def setUp(self):
        self.mod = load()
        self._real_fetch = self.mod.fetch

    def tearDown(self):
        self.mod.fetch = self._real_fetch

    def resources_from(self, *rs):
        self.mod.fetch = lambda url, timeout=None: package(*rs)
        return dict(self.mod.resources())

    def test_a_revised_month_is_found(self):
        """The exact shape that was invisible: a FINAL-suffixed month, alone."""
        got = self.resources_from(res("HOSPITAL_DISP_COMMUNITY_202505FINAL"))
        self.assertIn("202505", got,
                      "a revised month must not read as never published")

    def test_a_plain_month_is_still_found(self):
        got = self.resources_from(res("HOSPITAL_DISP_COMMUNITY_202606"))
        self.assertIn("202606", got)

    def test_the_revision_beats_the_plain_file(self):
        """Both exist for one month: publish the corrected numbers, not the first ones."""
        got = self.resources_from(
            res("HOSPITAL_DISP_COMMUNITY_202505"),
            res("HOSPITAL_DISP_COMMUNITY_202505FINAL"),
        )
        self.assertEqual(len(got), 1, "one month must yield one resource")
        self.assertTrue(got["202505"].endswith("202505final.csv"),
                        "the revised file must win, got %s" % got["202505"])

    def test_the_revision_wins_whichever_order_it_arrives_in(self):
        """CKAN does not promise an order, so the outcome must not depend on one."""
        got = self.resources_from(
            res("HOSPITAL_DISP_COMMUNITY_202505FINAL"),
            res("HOSPITAL_DISP_COMMUNITY_202505"),
        )
        self.assertTrue(got["202505"].endswith("202505final.csv"))

    def test_non_csv_resources_are_still_ignored(self):
        got = self.resources_from(res("HOSPITAL_DISP_COMMUNITY_202606", fmt="XLSX"))
        self.assertEqual(got, {}, "only CSV resources are readable by the builder")

    def test_a_name_with_no_month_is_ignored(self):
        got = self.resources_from(res("HOSPITAL_DISP_COMMUNITY_METADATA"))
        self.assertEqual(got, {}, "a name carrying no YYYYMM is not a monthly file")

    def test_months_come_back_oldest_first(self):
        self.mod.fetch = lambda url, timeout=None: package(
            res("HOSPITAL_DISP_COMMUNITY_202606"),
            res("HOSPITAL_DISP_COMMUNITY_202505FINAL"),
            res("HOSPITAL_DISP_COMMUNITY_202601"),
        )
        periods = [p for p, _u in self.mod.resources()]
        self.assertEqual(periods, sorted(periods),
                         "build() takes the last name as 'latest' and relies on this")


if __name__ == "__main__":
    unittest.main()
