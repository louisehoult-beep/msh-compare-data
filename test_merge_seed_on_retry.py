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
        # seed_format.py travels with it: merge_seed_on_retry.py imports it to
        # write the seed back in whatever byte format the file already has
        # (`^o584`), so a mini-repo without it is not a runnable mini-repo.
        shutil.copy(
            os.path.join(os.path.dirname(__file__), "scripts", "seed_format.py"),
            os.path.join(self.tmpdir, "scripts", "seed_format.py"),
        )
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


WORKFLOW = os.path.join(os.path.dirname(__file__), ".github", "workflows",
                        "company-intelligence.yml")


def _extract_retry_block():
    """Pull the real push/retry shell out of company-intelligence.yml.

    Read from the workflow rather than copying it here on purpose: a copy would
    drift, and then this test would be proving something the workflow no longer
    does. Plain text parsing, not PyYAML — the unit-tests job runs a clean
    setup-python with no pip install, so only the standard library is available.
    """
    with open(WORKFLOW, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == "pushed=0")
    indent = len(lines[start]) - len(lines[start].lstrip())
    out = []
    for l in lines[start:]:
        if l.strip() and not l.startswith(" " * indent):
            break
        out.append(l[indent:] if l.strip() else "")
    return "\n".join(out)


class RetryPushTest(unittest.TestCase):
    """The retry path must survive a lost push race and actually land the work.

    On 21/09/2026 the 08:49 company-intelligence run spent an hour fetching
    Companies House data, lost the push race to another writer, ran the seed
    merge correctly — and then died on `git rebase` with "cannot rebase: Your
    index contains uncommitted changes", because the merged seed had been
    staged with `git add` and never committed. The whole run's work was thrown
    away. Nothing tested the shell, so nothing caught it.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.origin = os.path.join(self.root, "origin.git")
        self.work = os.path.join(self.root, "work")
        subprocess.check_call(["git", "init", "-q", "--bare", "-b", "main", self.origin])
        self._seed_origin()
        subprocess.check_call(["git", "clone", "-q", self.origin, self.work])
        self._git(self.work, "config", "user.email", "test@example.com")
        self._git(self.work, "config", "user.name", "test")

    def _git(self, cwd, *args):
        return subprocess.check_output(["git"] + list(args), cwd=cwd, text=True,
                                       stderr=subprocess.STDOUT)

    def _seed_origin(self):
        boot = os.path.join(self.root, "boot")
        subprocess.check_call(["git", "clone", "-q", self.origin, boot])
        self._git(boot, "config", "user.email", "test@example.com")
        self._git(boot, "config", "user.name", "test")
        os.makedirs(os.path.join(boot, "data"))
        os.makedirs(os.path.join(boot, "scripts"))
        import shutil
        shutil.copy(os.path.join(os.path.dirname(__file__), "scripts",
                                 "merge_seed_on_retry.py"),
                    os.path.join(boot, "scripts", "merge_seed_on_retry.py"))
        # Its helper has to come too — see the note in FullScriptTest.setUp.
        shutil.copy(os.path.join(os.path.dirname(__file__), "scripts",
                                 "seed_format.py"),
                    os.path.join(boot, "scripts", "seed_format.py"))
        # The gate is stubbed to pass. What is under test here is whether the
        # retry path reaches the gate at all and lands the commit — not the gate.
        with open(os.path.join(boot, "verify.py"), "w") as fh:
            fh.write("import sys\nsys.exit(0)\n")
        self._write_seed(boot, [{"name": "Acme Medical Ltd", "links": [],
                                 "companyNumber": None}])
        with open(os.path.join(boot, "data", "frameworks.json"), "w") as fh:
            fh.write("{}\n")
        self._git(boot, "add", "-A")
        self._git(boot, "commit", "-qm", "base")
        self._git(boot, "push", "-q", "origin", "main")

    def _write_seed(self, repo, suppliers):
        # One line, no trailing newline: supplier-seed.json really is written
        # this way, and that is exactly why git cannot text-merge it.
        with open(os.path.join(repo, "data", "supplier-seed.json"), "w") as fh:
            json.dump({"_notice": {"owner": "test"}, "note": "test",
                       "suppliers": suppliers}, fh)

    def _read_origin_seed(self):
        blob = subprocess.check_output(
            ["git", "show", "main:data/supplier-seed.json"],
            cwd=self.origin, text=True)
        return json.loads(blob)

    def _peer_lands(self, touch_seed):
        """Another writer pushes first, so our push is rejected."""
        peer = os.path.join(self.root, "peer")
        subprocess.check_call(["git", "clone", "-q", self.origin, peer])
        self._git(peer, "config", "user.email", "peer@example.com")
        self._git(peer, "config", "user.name", "peer")
        if touch_seed:
            # A curated link — the exact thing the 15/09/2026 bug discarded.
            self._write_seed(peer, [{
                "name": "Acme Medical Ltd",
                "links": [{"url": "https://acme.example", "evidence": "curated"}],
                "companyNumber": None}])
        with open(os.path.join(peer, "data", "peer-file.json"), "w") as fh:
            fh.write('{"peer": true}\n')
        self._git(peer, "add", "-A")
        self._git(peer, "commit", "-qm", "peer work")
        self._git(peer, "push", "-q", "origin", "main")

    def _run_retry(self):
        """Our run commits its work, then executes the workflow's retry shell."""
        self._write_seed(self.work, [{"name": "Acme Medical Ltd", "links": [],
                                      "companyNumber": "12345678"}])
        self._git(self.work, "add", "data/supplier-seed.json")
        self._git(self.work, "commit", "-qm", "company intelligence: test run")
        script = "set -e\n" + _extract_retry_block()
        return subprocess.run(["bash", "-c", script], cwd=self.work,
                              capture_output=True, text=True)

    def test_retry_lands_the_work_when_a_peer_did_not_touch_the_seed(self):
        self._peer_lands(touch_seed=False)
        r = self._run_retry()
        self.assertEqual(r.returncode, 0,
                         "retry path failed:\n" + r.stdout + r.stderr)
        seed = self._read_origin_seed()
        acme = next(s for s in seed["suppliers"] if s["name"] == "Acme Medical Ltd")
        self.assertEqual(acme["companyNumber"], "12345678",
                         "this run's work was thrown away by the retry")
        self.assertIn("peer-file.json",
                      self._git(self.origin, "ls-tree", "--name-only", "main", "data/"),
                      "the peer's commit was lost")

    def test_retry_keeps_a_curated_link_a_peer_landed_on_the_seed(self):
        self._peer_lands(touch_seed=True)
        r = self._run_retry()
        self.assertEqual(r.returncode, 0,
                         "retry path failed on a seed conflict:\n" + r.stdout + r.stderr)
        seed = self._read_origin_seed()
        acme = next(s for s in seed["suppliers"] if s["name"] == "Acme Medical Ltd")
        self.assertEqual(acme["companyNumber"], "12345678",
                         "this run's company number was lost")
        self.assertEqual(acme["links"],
                         [{"url": "https://acme.example", "evidence": "curated"}],
                         "the peer's curated link was discarded - this is the "
                         "^o478 data-loss bug coming back")

    def test_a_real_conflict_on_another_file_still_refuses_to_push(self):
        """The loud failure must stay loud. Only the seed may be auto-resolved."""
        self._peer_lands(touch_seed=False)
        # Both sides change frameworks.json differently: a genuine conflict.
        peer2 = os.path.join(self.root, "peer2")
        subprocess.check_call(["git", "clone", "-q", self.origin, peer2])
        self._git(peer2, "config", "user.email", "peer@example.com")
        self._git(peer2, "config", "user.name", "peer")
        with open(os.path.join(peer2, "data", "frameworks.json"), "w") as fh:
            fh.write('{"theirs": 1}\n')
        self._git(peer2, "add", "-A")
        self._git(peer2, "commit", "-qm", "peer frameworks")
        self._git(peer2, "push", "-q", "origin", "main")

        with open(os.path.join(self.work, "data", "frameworks.json"), "w") as fh:
            fh.write('{"ours": 1}\n')
        self._git(self.work, "add", "data/frameworks.json")
        self._git(self.work, "commit", "-qm", "our frameworks")
        r = self._run_retry()
        self.assertNotEqual(r.returncode, 0,
                            "a real conflict on a non-seed file must stop the run")
        self.assertIn("REBASE CONFLICT on a non-seed file", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
