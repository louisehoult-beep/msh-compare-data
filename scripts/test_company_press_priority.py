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
    return lambda *a, **k: json.dumps(payload).encode("utf-8")


SUPPLIERS = [{"name": "Boston Scientific", "note": "x"},
             {"name": "Zeta Ltd", "note": "x"},
             {"name": "Alpha Ltd"},
             {"name": "Beta Ltd"}]
STAMPS = {"Boston Scientific": "2026-08-18", "Zeta Ltd": "2026-01-01",
          "Alpha Ltd": "2026-01-01", "Beta Ltd": "2026-02-01"}


class ItFailsOpen(unittest.TestCase):
    """Every one of these must yield [] and let the run continue. This is an
    optimisation, never a dependency."""

    def test_network_error(self):
        def boom(*a, **k):
            raise OSError("unreachable")
        self.assertEqual([], r.priority_names(fetcher=boom))

    def test_not_json(self):
        self.assertEqual([], r.priority_names(fetcher=lambda *a, **k: b"<html>"))

    def test_no_timestamp(self):
        self.assertEqual([], r.priority_names(
            fetcher=feed({"suppliers": ["Boston Scientific"]})))

    def test_a_stale_file_is_ignored(self):
        """If the Live Desk stops writing it, yesterday's names must not be
        re-queried forever."""
        self.assertEqual([], r.priority_names(
            fetcher=feed({"generatedAt": "2020-01-01",
                          "suppliers": ["Boston Scientific"]})))

    def test_a_future_dated_file_is_ignored(self):
        self.assertEqual([], r.priority_names(
            fetcher=feed({"generatedAt": "2099-01-01",
                          "suppliers": ["Boston Scientific"]})))

    def test_junk_entries_are_dropped_not_queried(self):
        out = r.priority_names(
            fetcher=feed({"generatedAt": r.today_iso(),
                          "suppliers": ["Boston Scientific", "", None, 7, {"a": 1}]}))
        self.assertEqual(["Boston Scientific"], out)

    def test_the_list_is_capped(self):
        out = r.priority_names(fetcher=feed(
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


if __name__ == "__main__":
    unittest.main()
