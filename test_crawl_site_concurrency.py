#!/usr/bin/env python3
"""Proof that scripts/crawl_supplier_site.py cannot lose a capture to a second
copy of itself running in the same clone — the fix for OUTSTANDING ^o397.

WHAT WENT WRONG WITHOUT IT
--------------------------
The script is a read-modify-write on ONE json file: main() loads
data/supplier-products.json whole at startup, adds each supplier's range to
that in-memory document as it crawls, and saves the whole thing back. Two
invocations in one clone therefore start from the same document and the one
that finishes LAST writes its copy over the other's work. On 09/09/2026 a slow
crawl was backgrounded while others ran and the Econix, Inpress and NeedleDock
captures simply disappeared; they had to be re-crawled to get them back.

The rule was written down ("never run two concurrent invocations on one
clone") but nothing enforced it, and a rule that only lives in a note gets
broken by the next session that has not read the note.

Run:  python3 test_crawl_site_concurrency.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import crawl_supplier_site as c


class TheLockRefusesASecondCrawl(unittest.TestCase):
    def test_a_second_claim_on_the_same_file_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "supplier-products.json")
            open(out, "w").write("{}")
            held = c.claim_out_file(out)
            try:
                with self.assertRaises(c.AnotherCrawlIsRunning):
                    c.claim_out_file(out)
            finally:
                held.close()

    def test_the_refusal_says_what_to_do_instead(self):
        """A refusal that does not name the way forward just reads as broken."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "supplier-products.json")
            open(out, "w").write("{}")
            held = c.claim_out_file(out)
            try:
                c.claim_out_file(out)
            except c.AnotherCrawlIsRunning as e:
                msg = str(e)
                self.assertIn("begin.sh", msg)
                self.assertIn(out, msg)
                self.assertIn("pid", msg)
            finally:
                held.close()

    def test_the_lock_is_released_when_the_holder_closes_it(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "supplier-products.json")
            open(out, "w").write("{}")
            c.claim_out_file(out).close()
            second = c.claim_out_file(out)      # must not raise
            second.close()

    def test_a_different_output_file_is_not_blocked(self):
        """Parallel crawling in separate clones must stay possible — each clone
        has its own working tree and so its own output file."""
        with tempfile.TemporaryDirectory() as d:
            a = os.path.join(d, "clone-a.json")
            b = os.path.join(d, "clone-b.json")
            for f in (a, b):
                open(f, "w").write("{}")
            ha, hb = c.claim_out_file(a), c.claim_out_file(b)
            ha.close(); hb.close()

    def test_the_lock_survives_across_processes_not_just_within_one(self):
        """flock is per open file description: a lock that only held inside one
        process would not stop the backgrounded-crawl case at all."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "supplier-products.json")
            open(out, "w").write("{}")
            held = c.claim_out_file(out)
            try:
                probe = subprocess.run(
                    [sys.executable, "-c",
                     "import sys; sys.path.insert(0, %r)\n"
                     "import crawl_supplier_site as c\n"
                     "try:\n"
                     "    c.claim_out_file(%r)\n"
                     "    print('CLAIMED')\n"
                     "except c.AnotherCrawlIsRunning:\n"
                     "    print('REFUSED')\n"
                     % (os.path.join(HERE, "scripts"), out)],
                    capture_output=True, text=True, timeout=60)
                self.assertIn("REFUSED", probe.stdout,
                              "a separate process was allowed to claim a file this "
                              "one holds — stderr: %s" % probe.stderr[-500:])
            finally:
                held.close()


class TheSaveIsAtomic(unittest.TestCase):
    def test_it_writes_through_a_temp_file_and_leaves_none_behind(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "supplier-products.json")
            c.atomic_write_json(out, {"suppliers": {"X": {"products": [1, 2]}}})
            self.assertEqual(json.load(open(out))["suppliers"]["X"]["products"], [1, 2])
            self.assertFalse(os.path.exists(out + ".tmp"))

    def test_a_failed_write_leaves_the_previous_file_intact(self):
        """The whole point of the rename: a dump that raises part-way must not
        have already truncated the real file."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "supplier-products.json")
            c.atomic_write_json(out, {"suppliers": {"X": 1}})

            class Unserialisable:
                pass

            with self.assertRaises(TypeError):
                c.atomic_write_json(out, {"suppliers": {"X": Unserialisable()}})
            self.assertEqual(json.load(open(out)), {"suppliers": {"X": 1}},
                             "the previous capture was destroyed by a failed write")


class MainStillClaimsTheFile(unittest.TestCase):
    """A guard nothing calls is not a guard."""

    def test_main_claims_the_output_file_before_it_loads_it(self):
        src = open(os.path.join(HERE, "scripts", "crawl_supplier_site.py"),
                   encoding="utf-8").read()
        body = src.split("def main():", 1)[1]
        claim = body.find("claim_out_file(OUT)")
        load = body.find('json.load(open(OUT')
        self.assertNotEqual(claim, -1, "main() no longer claims the output file")
        self.assertNotEqual(load, -1, "main() no longer loads the output file")
        self.assertLess(claim, load,
                        "main() loads the output file before claiming it, so the "
                        "load-vs-save race this guard exists to close is still open")

    def test_the_writer_goes_through_the_atomic_helper(self):
        src = open(os.path.join(HERE, "scripts", "crawl_supplier_site.py"),
                   encoding="utf-8").read()
        body = src.split("def main():", 1)[1]
        self.assertIn("atomic_write_json(OUT", body)
        self.assertNotIn('open(OUT, "w"', body,
                         "something in main() still truncates the output file in place")


class TheScratchFilesStayOutOfHistory(unittest.TestCase):
    """supplier-capture.yml commits with `git add data`, and the lock sits beside
    the data file it guards. A committed lock would carry one runner's pid into
    every checkout and read as real state."""

    def test_the_lock_and_temp_files_are_gitignored(self):
        ignore = os.path.join(HERE, ".gitignore")
        if not os.path.exists(ignore):
            self.skipTest("no .gitignore in this checkout")
        body = open(ignore, encoding="utf-8").read()
        self.assertIn("data/*.lock", body)
        self.assertIn("data/*.tmp", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
