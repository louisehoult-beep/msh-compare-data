#!/usr/bin/env python3
"""Proof that scripts/crawl_supplier_product_detail.py's resume position
actually advances — the fix for OUTSTANDING ^o295 / ^o288 / ^o331.

WHAT WENT WRONG WITHOUT IT
--------------------------
The per-supplier loop took `range[:products_limit]` and stopped when the 60s
site budget ran out, so every run read the SAME prefix. Three consecutive runs
against Medical Imaging Systems captured the identical first 36 of its 105
products; Conmed UK stalled at 30 of 167 and Avicenna at 23 of 78, however
often the sweep ran. The tail of a long range was unreachable, not slow.

Each test below is written to FAIL against the old take-the-first-N behaviour
and pass against the resume cursor, so a regression that quietly restores
"start at product 1" is caught here rather than in six weeks of a range that
never finishes.

Run:  python3 test_product_detail_cursor.py
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import crawl_supplier_product_detail as c


def rng(n, prefix="Product "):
    return [{"n": "%s%d" % (prefix, i)} for i in range(1, n + 1)]


def names(slice_):
    return [p["n"] for p in slice_]


class ResumeSlice(unittest.TestCase):
    def test_no_cursor_starts_at_the_top(self):
        got, from_top = c.resume_slice(rng(105), None, 40)
        self.assertEqual(names(got)[:3], ["Product 1", "Product 2", "Product 3"])
        self.assertTrue(from_top)

    def test_second_run_does_not_repeat_the_first_run_s_products(self):
        """The whole point. Old behaviour returned Product 1.. again."""
        first, _ = c.resume_slice(rng(105), None, 40)
        second, from_top = c.resume_slice(rng(105), names(first)[-1], 40)
        self.assertFalse(from_top)
        self.assertEqual(names(second)[0], "Product 41")
        self.assertFalse(set(names(first)) & set(names(second)),
                         "the second run re-read products the first run already attempted")

    def test_three_runs_reach_the_tail_of_a_105_product_range(self):
        """MIS Healthcare's actual shape: 105 products, 36-40 a run. The old
        loop reached product 36 on run 1, 2 and 3 alike."""
        seen, last, full = [], None, rng(105)
        for _ in range(3):
            got, _ = c.resume_slice(full, last, 40)
            seen += names(got)
            last = names(got)[-1]
        self.assertIn("Product 105", seen, "the end of the range is still unreachable")
        self.assertEqual(len(set(seen)), 105, "three runs of 40 should cover the whole range once")

    def test_it_wraps_rather_than_returning_a_stub_window(self):
        """A cursor near the end must not spend a whole run on two products."""
        got, _ = c.resume_slice(rng(105), "Product 104", 40)
        self.assertEqual(len(got), 40)
        self.assertEqual(names(got)[:3], ["Product 105", "Product 1", "Product 2"])

    def test_a_forgotten_product_name_restarts_honestly(self):
        """The range is rebuilt by the site crawl; a product can disappear. The
        cursor then has nothing to resume from and must say so, not guess."""
        got, from_top = c.resume_slice(rng(105), "A product no longer sold", 40)
        self.assertTrue(from_top)
        self.assertEqual(names(got)[0], "Product 1")

    def test_a_short_range_is_returned_whole_from_the_resume_point(self):
        got, _ = c.resume_slice(rng(5), "Product 3", 40)
        self.assertEqual(names(got), ["Product 4", "Product 5", "Product 1",
                                      "Product 2", "Product 3"])

    def test_matching_is_case_and_whitespace_insensitive(self):
        """Cursors are compared with nk() because the range's own spelling of a
        name is not stable between crawls."""
        got, from_top = c.resume_slice(rng(10), "  pRoDuCt 4 ", 3)
        self.assertFalse(from_top)
        self.assertEqual(names(got), ["Product 5", "Product 6", "Product 7"])

    def test_empty_inputs_do_not_raise(self):
        self.assertEqual(c.resume_slice([], "x", 40), ([], True))
        self.assertEqual(c.resume_slice(rng(3), None, 0), ([], True))


class BootstrapCursor(unittest.TestCase):
    """The very first run after this change has no saved cursor, so without a
    bootstrap it would re-read the prefix it already holds — three wasted runs
    on MIS Healthcare before it reached anything new."""

    def store(self, supplier, names):
        return {supplier + "|" + c.nk(n): {"capturedDate": "2026-09-01"} for n in names}

    def test_it_resumes_after_the_furthest_product_already_captured(self):
        full = rng(105)
        store = self.store("MIS", ["Product %d" % i for i in range(1, 37)])
        self.assertEqual(c.bootstrap_cursor(full, store, "MIS"), "Product 36")
        got, from_top = c.resume_slice(full, c.bootstrap_cursor(full, store, "MIS"), 40)
        self.assertFalse(from_top)
        self.assertEqual(names(got)[0], "Product 37")

    def test_nothing_captured_means_no_bootstrap_and_an_honest_restart(self):
        self.assertIsNone(c.bootstrap_cursor(rng(10), {}, "MIS"))

    def test_it_takes_the_LAST_captured_in_range_order_not_the_first_gap(self):
        """Captures need not be contiguous. Taking the furthest point reached
        is what the old loop can be shown to have done; the wrap in
        resume_slice brings the run back round to any earlier gap."""
        full = rng(10)
        store = self.store("X", ["Product 1", "Product 2", "Product 7"])
        self.assertEqual(c.bootstrap_cursor(full, store, "X"), "Product 7")
        got, _ = c.resume_slice(full, "Product 7", 6)
        self.assertEqual(names(got), ["Product 8", "Product 9", "Product 10",
                                      "Product 1", "Product 2", "Product 3"])

    def test_another_supplier_s_captures_do_not_move_this_supplier(self):
        store = self.store("Someone Else", ["Product 1", "Product 2"])
        self.assertIsNone(c.bootstrap_cursor(rng(10), store, "MIS"))


class CursorFile(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "state", "cur.json")
            c.save_cursors(p, {"Conmed UK": "Product 30"})
            self.assertEqual(c.load_cursors(p), {"Conmed UK": "Product 30"})

    def test_a_missing_or_corrupt_cursor_costs_a_restart_not_a_crash(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(c.load_cursors(os.path.join(d, "nope.json")), {})
            bad = os.path.join(d, "bad.json")
            open(bad, "w").write("{not json")
            self.assertEqual(c.load_cursors(bad), {})

    def test_a_shard_out_file_gets_its_own_cursor(self):
        """Two parallel workers sharing one cursor file would each overwrite the
        other's position and both keep re-reading the same slice."""
        self.assertEqual(c.cursor_path_for(c.OUT), c.CURSOR)
        self.assertNotEqual(c.cursor_path_for("data/shard-a.json"), c.CURSOR)
        self.assertNotEqual(c.cursor_path_for("data/shard-a.json"),
                            c.cursor_path_for("data/shard-b.json"))

    def test_the_written_file_is_valid_json_with_the_documented_shape(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cur.json")
            c.save_cursors(p, {"X": "Y"})
            doc = json.load(open(p, encoding="utf-8"))
            self.assertEqual(doc["cursors"], {"X": "Y"})
            self.assertIn("_note", doc)
            self.assertIn("generated", doc)


class TheWeeklySweepKeepsTheCursor(unittest.TestCase):
    """A cursor written into a CI checkout and not committed is thrown away
    with the runner, so every weekly run would start each range at the top —
    the stall this whole change exists to fix, reintroduced silently. The same
    reasoning is why acquirer-press.yml and company-press.yml commit their
    rotation state."""

    WORKFLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            ".github", "workflows",
                            "supplier-product-detail-capture.yml")

    def test_the_workflow_stages_the_cursor_file(self):
        if not os.path.exists(self.WORKFLOW):
            self.skipTest("workflow file not present in this checkout")
        body = open(self.WORKFLOW, encoding="utf-8").read()
        self.assertIn("scripts/crawl_supplier_product_detail.py", body,
                      "this test is pointed at the wrong workflow")
        # The STAGING LINE, not merely a mention: an explanatory comment naming
        # the file would otherwise satisfy this test while the commit step had
        # quietly gone back to `git add data`.
        staged = [ln.strip() for ln in body.splitlines()
                  if ln.strip().startswith("git add") and c.CURSOR in ln]
        self.assertTrue(staged,
                        "no `git add` line in the weekly sweep names %s, so its "
                        "resume position is discarded with the CI checkout and "
                        "every run restarts each supplier's range at the top"
                        % c.CURSOR)

    def test_the_cursor_is_not_gitignored(self):
        root = os.path.dirname(os.path.abspath(__file__))
        ignore = os.path.join(root, ".gitignore")
        if not os.path.exists(ignore):
            self.skipTest("no .gitignore in this checkout")
        for line in open(ignore, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                self.assertNotIn("state/", line,
                                 "state/ is ignored, so the resume position can "
                                 "never be committed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
