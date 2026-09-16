"""
test_merge_seed_on_retry.py — proves that merge_seed_on_retry.py prevents
the 15/09/2026 data-loss class of bug (^o478).

Run with: python3 test_merge_seed_on_retry.py
Exit 0 = all tests pass. Exit 1 = at least one failed.
"""
import importlib.util, json, os, subprocess, sys, tempfile, textwrap, unittest


def _load_merge():
    """Import merge_seed_on_retry without executing its __main__ block."""
    spec = importlib.util.spec_from_file_location(
        "merge_seed_on_retry",
        os.path.join(os.path.dirname(__file__), "scripts", "merge_seed_on_retry.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SeedMergeTests(unittest.TestCase):

    def _make_seed(self, suppliers):
        return {"_notice": {"owner": "test"}, "note": "test", "suppliers": suppliers}

    def _run_merge(self, head_suppliers, main_suppliers):
        """Run merge_seed_on_retry.merge_supplier logic over a set of suppliers."""
        m = _load_merge()
        head_by_name = {s["name"]: s for s in head_suppliers}
        main_by_name = {s["name"]: s for s in main_suppliers}

        result = {}
        for name, main_s in main_by_name.items():
            if name in head_by_name:
                result[name] = m.merge_supplier(head_by_name[name], main_s)
            else:
                result[name] = main_s
        for name, head_s in head_by_name.items():
            if name not in main_by_name:
                result[name] = head_s
        return result

    # -----------------------------------------------------------------------
    # The 15/09/2026 Ovidius scenario: session adds links to origin/main,
    # hub-bot runs from the old base (no links), hub-bot's retry merge must
    # preserve origin/main's links rather than using hub-bot's empty version.
    # -----------------------------------------------------------------------

    def test_curated_links_preserved_from_main(self):
        """Links in origin/main are never overwritten by HEAD's empty links."""
        head_s = [
            {
                "name": "Ovidius Medical Ltd",
                "links": [],          # hub-bot read the seed BEFORE the session added links
                "companyNumber": "12345678",  # hub-bot confirmed the number
            }
        ]
        main_s = [
            {
                "name": "Ovidius Medical Ltd",
                "links": [{"url": "https://example.com", "evidence": "proved 15/09"}],
                "companyNumber": None,  # session hadn't updated the number yet
            }
        ]
        result = self._run_merge(head_s, main_s)
        rec = result["Ovidius Medical Ltd"]
        self.assertEqual(rec["links"], main_s[0]["links"],
                         "links from origin/main must be preserved when HEAD has empty links")
        self.assertEqual(rec["companyNumber"], "12345678",
                         "companyNumber from HEAD must win when HEAD is non-empty")

    def test_curated_website_preserved_from_main(self):
        """Website in origin/main is preserved when HEAD is null."""
        head_s = [{"name": "Acme Medical", "website": None, "companyNumber": "99999999"}]
        main_s = [{"name": "Acme Medical", "website": "acme-medical.co.uk", "companyNumber": None}]
        result = self._run_merge(head_s, main_s)
        rec = result["Acme Medical"]
        self.assertEqual(rec["website"], "acme-medical.co.uk",
                         "website seeded on main must survive CI run that had null website")

    def test_new_supplier_in_main_kept(self):
        """A supplier added by a concurrent session (only in origin/main) is not lost."""
        head_s = [{"name": "Old Supplier", "links": [], "companyNumber": "11111111"}]
        main_s = [
            {"name": "Old Supplier", "links": [], "companyNumber": None},
            {"name": "Brand New Supplier", "links": [{"url": "https://new.co.uk"}], "companyNumber": None},
        ]
        result = self._run_merge(head_s, main_s)
        self.assertIn("Brand New Supplier", result,
                      "new supplier added to origin/main must appear in the merged result")

    def test_new_supplier_in_head_kept(self):
        """A supplier added by this CI run (only in HEAD) is not lost."""
        head_s = [
            {"name": "Existing Supplier", "companyNumber": "22222222"},
            {"name": "CI Discovered Supplier", "companyNumber": "33333333"},
        ]
        main_s = [{"name": "Existing Supplier", "companyNumber": None}]
        result = self._run_merge(head_s, main_s)
        self.assertIn("CI Discovered Supplier", result,
                      "new supplier found by CI run must appear in the merged result")

    def test_ci_company_number_wins_over_empty_main(self):
        """CI-confirmed company number is applied when main has no number."""
        head_s = [{"name": "Zapper Ltd", "companyNumber": "77777777",
                   "companyNumberCandidate": {"confidence": "confirmed", "number": "77777777"}}]
        main_s = [{"name": "Zapper Ltd", "companyNumber": None,
                   "companyNumberCandidate": {"confidence": "candidate", "number": "77777777"}}]
        result = self._run_merge(head_s, main_s)
        rec = result["Zapper Ltd"]
        self.assertEqual(rec["companyNumber"], "77777777",
                         "CI-confirmed companyNumber must win over empty main")
        self.assertEqual(rec["companyNumberCandidate"]["confidence"], "confirmed",
                         "CI-upgraded confidence must win over candidate")

    def test_both_links_non_empty_main_wins(self):
        """When both versions have links, origin/main's take precedence (curated field)."""
        head_links = [{"url": "https://ci-found.co.uk", "evidence": "auto-seeded"}]
        main_links = [{"url": "https://human-verified.co.uk", "evidence": "verified 14/09"}]
        head_s = [{"name": "Dual Links Ltd", "links": head_links}]
        main_s = [{"name": "Dual Links Ltd", "links": main_links}]
        result = self._run_merge(head_s, main_s)
        self.assertEqual(result["Dual Links Ltd"]["links"], main_links,
                         "when both sides have links, origin/main's (curator's) value must win")

    def test_empty_seed_does_not_crash(self):
        """Merging with an empty supplier list on either side does not raise."""
        try:
            self._run_merge([], [{"name": "Lonely Supplier", "links": []}])
            self._run_merge([{"name": "Lonely Supplier", "links": []}], [])
        except Exception as exc:
            self.fail("Empty supplier list caused unexpected exception: %s" % exc)


class FullScriptTest(unittest.TestCase):
    """End-to-end test: write two seed versions, fake git, run the script."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Set up a minimal git repo so merge_seed_on_retry can call 'git show'
        subprocess.check_call(["git", "init", "-q"], cwd=self.tmpdir)
        subprocess.check_call(
            ["git", "config", "user.email", "test@example.com"], cwd=self.tmpdir
        )
        subprocess.check_call(
            ["git", "config", "user.name", "test"], cwd=self.tmpdir
        )
        os.makedirs(os.path.join(self.tmpdir, "data"), exist_ok=True)
        os.makedirs(os.path.join(self.tmpdir, "scripts"), exist_ok=True)
        # Copy the script into the tmp repo
        import shutil
        shutil.copy(
            os.path.join(os.path.dirname(__file__), "scripts", "merge_seed_on_retry.py"),
            os.path.join(self.tmpdir, "scripts", "merge_seed_on_retry.py"),
        )

    def _write_seed(self, suppliers):
        path = os.path.join(self.tmpdir, "data", "supplier-seed.json")
        with open(path, "w") as f:
            json.dump({"_notice": {"owner": "test"}, "note": "test", "suppliers": suppliers}, f, indent=2)

    def _commit_seed(self, suppliers):
        self._write_seed(suppliers)
        subprocess.check_call(["git", "add", "data/supplier-seed.json"], cwd=self.tmpdir)
        subprocess.check_call(["git", "commit", "-qm", "test-commit"], cwd=self.tmpdir)

    def _read_seed(self):
        with open(os.path.join(self.tmpdir, "data", "supplier-seed.json")) as f:
            return json.load(f)

    def test_full_merge_preserves_curated_links(self):
        # Commit origin/main version (with curated links)
        self._commit_seed([
            {
                "name": "Real Supplier Ltd",
                "links": [{"url": "https://realsupplier.co.uk", "evidence": "verified"}],
                "companyNumber": None,
            }
        ])
        # Create a fake 'origin/main' reference pointing at HEAD
        subprocess.check_call(
            ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
            cwd=self.tmpdir
        )
        # Now overwrite with HEAD version (CI run's result, no links)
        self._write_seed([
            {
                "name": "Real Supplier Ltd",
                "links": [],
                "companyNumber": "12345678",
            }
        ])

        # Run the merge script
        result = subprocess.run(
            [sys.executable, "scripts/merge_seed_on_retry.py"],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, "merge script failed: " + result.stderr)

        merged = self._read_seed()
        supplier = next(s for s in merged["suppliers"] if s["name"] == "Real Supplier Ltd")
        self.assertEqual(
            supplier["links"],
            [{"url": "https://realsupplier.co.uk", "evidence": "verified"}],
            "Curated links must survive the merge"
        )
        self.assertEqual(supplier["companyNumber"], "12345678",
                         "CI-confirmed company number must survive the merge")


if __name__ == "__main__":
    unittest.main(verbosity=2)
