"""The Live Desk priority handoff (27/08/2026).

The rotation is a 14-day cycle, so Boston Scientific's last check was 18/08 and
its cyberattack of the 26th could not have reached the SUPPLIER PRESS panel until
~01/09. The Live Desk now names suppliers with news and this run queries them
sooner.

These tests exist for one reason above all: this must NEVER be able to break or
delay a refresh, and it must NEVER be able to make something publish. Most of
them are failure paths.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refresh_company_press as r


def feed(payload):
    """A delivered handoff file with this content."""
    return lambda: json.dumps(payload)


def absent():
    """No file delivered — what a stopped delivery looks like."""
    return None


SUPPLIERS = [{"name": "Boston Scientific", "note": "x"},
             {"name": "Zeta Ltd", "note": "x"},
             {"name": "Alpha Ltd"},
             {"name": "Beta Ltd"}]
STAMPS = {"Boston Scientific": "2026-08-18", "Zeta Ltd": "2026-01-01",
          "Alpha Ltd": "2026-01-01", "Beta Ltd": "2026-02-01"}


class ItFailsOpen(unittest.TestCase):
    """Every one of these must yield [] and let the run continue. This is an
    optimisation, never a dependency."""

    def test_the_file_is_not_there(self):
        self.assertEqual([], r.priority_names(reader=absent))

    def test_reader_raises(self):
        def boom():
            raise OSError("unreadable")
        self.assertEqual([], r.priority_names(reader=boom))

    def test_not_json(self):
        self.assertEqual([], r.priority_names(reader=lambda: "<html>"))

    def test_no_timestamp(self):
        self.assertEqual([], r.priority_names(
            reader=feed({"suppliers": ["Boston Scientific"]})))

    def test_a_stale_file_is_ignored(self):
        """If the Live Desk stops writing it, yesterday's names must not be
        re-queried forever."""
        self.assertEqual([], r.priority_names(
            reader=feed({"generatedAt": "2020-01-01",
                          "suppliers": ["Boston Scientific"]})))

    def test_a_future_dated_file_is_ignored(self):
        self.assertEqual([], r.priority_names(
            reader=feed({"generatedAt": "2099-01-01",
                          "suppliers": ["Boston Scientific"]})))

    def test_junk_entries_are_dropped_not_queried(self):
        out = r.priority_names(
            reader=feed({"generatedAt": r.today_iso(),
                          "suppliers": ["Boston Scientific", "", None, 7, {"a": 1}]}))
        self.assertEqual(["Boston Scientific"], out)

    def test_the_list_is_capped(self):
        out = r.priority_names(reader=feed(
            {"generatedAt": r.today_iso(),
             "suppliers": ["S%d" % i for i in range(500)]}))
        self.assertLessEqual(len(out), r.PRIORITY_MAX_NAMES)


class ItChangesOrderAndNothingElse(unittest.TestCase):

    def test_a_flagged_supplier_jumps_the_queue(self):
        base, _, _ = r.plan(SUPPLIERS, STAMPS)
        self.assertNotIn("Boston Scientific", [s["name"] for s in base])
        out, _, _ = r.plan(SUPPLIERS, STAMPS, priority=["Boston Scientific"])
        self.assertEqual(out[0]["name"], "Boston Scientific")

    def test_it_comes_out_of_the_same_budget(self):
        """The daily cap is a politeness limit on Google News. Jumping the queue
        must not raise it."""
        base, _, _ = r.plan(SUPPLIERS, STAMPS)
        out, _, _ = r.plan(SUPPLIERS, STAMPS, priority=["Boston Scientific"])
        self.assertEqual(len(base), len(out))

    def test_a_name_not_in_the_seed_is_ignored_not_queried(self):
        base, _, _ = r.plan(SUPPLIERS, STAMPS)
        out, _, _ = r.plan(SUPPLIERS, STAMPS, priority=["Some Company Ltd"])
        self.assertEqual([s["name"] for s in base], [s["name"] for s in out])

    def test_an_empty_priority_list_is_the_plain_rotation(self):
        base, _, _ = r.plan(SUPPLIERS, STAMPS)
        out, _, _ = r.plan(SUPPLIERS, STAMPS, priority=[])
        self.assertEqual([s["name"] for s in base], [s["name"] for s in out])

    def test_a_flagged_supplier_is_not_listed_twice(self):
        out, _, _ = r.plan(SUPPLIERS, STAMPS, priority=["Zeta Ltd"])
        names = [s["name"] for s in out]
        self.assertEqual(len(names), len(set(names)))


class ItMustNotFailSilently(unittest.TestCase):
    """The 404 of 27/08/2026 (see PRIORITY_PATH) was invisible because a failure
    and a quiet day produced identical output. These tests exist so that a
    delivery which has stopped arriving is always distinguishable in the log."""

    def _log(self, **kw):
        out = []
        real, r.log = r.log, out.append
        try:
            r.priority_names(**kw)
        finally:
            r.log = real
        return " | ".join(out)

    def test_a_missing_file_says_so_loudly(self):
        self.assertIn("NOT DELIVERED", self._log(reader=absent))

    def test_unreadable_says_so_loudly(self):
        self.assertIn("UNREADABLE", self._log(reader=lambda: "<html>"))

    def test_stale_says_so_loudly(self):
        msg = self._log(reader=feed({"generatedAt": "2020-01-01",
                                     "suppliers": ["Boston Scientific"]}))
        self.assertIn("STALE", msg)

    def test_a_genuinely_quiet_day_is_not_shouted_about(self):
        msg = self._log(reader=feed({"generatedAt": r.today_iso(), "suppliers": []}))
        self.assertIn("no suppliers flagged", msg)
        for alarm in ("NOT DELIVERED", "UNREADABLE", "STALE"):
            self.assertNotIn(alarm, msg)

    def test_the_three_failures_are_distinguishable_from_each_other(self):
        seen = {self._log(reader=absent),
                self._log(reader=lambda: "<html>"),
                self._log(reader=feed({"generatedAt": "2020-01-01",
                                       "suppliers": ["X"]}))}
        self.assertEqual(3, len(seen))

    def test_it_never_fetches_over_the_network(self):
        """The bug was a cross-repo fetch of a PRIVATE repo. There must be no
        URL left to regress to."""
        src = open(r.__file__.replace(".pyc", ".py")).read()
        self.assertNotIn("raw.githubusercontent.com", src)


if __name__ == "__main__":
    unittest.main()
