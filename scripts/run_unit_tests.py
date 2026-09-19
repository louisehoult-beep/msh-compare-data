#!/usr/bin/env python3
"""Run the repo's standalone test files — and refuse to let a new one run nowhere.

WHY THIS EXISTS (18/09/2026)
  This repo has 25 test_*.py files at its root. Until today SIX of them ran
  anywhere: test_verify.py and five named directly in their own workflows. The
  other nineteen were written, committed, and then never executed again.

  That is not theoretical rot. On 18/09/2026 four of the nineteen were already
  red on clean main, and one of them had been red since 03/09:

    * test_company_tiers.py imported company-aliases from three levels ABOVE the
      repo. The registry was moved INTO the repo by c2d9a4c, so the test only
      ever imported on a machine that still had the old folder on disk. Fixed
      the same day.
    * test_previous_names.py asserted that Gemini Surgical UK stays a separate
      seed record until Lou ruled on rename-versus-sale. A seed merge folded it
      into Healthcare 25 Ltd anyway, and nothing noticed, because nothing ran
      it. Settled 18/09 on the Find a Tender award notice the 03/09 decision
      pack had itself nominated; the test now asserts the merge and runs here.

  The same fortnight of silence let six company-match override keys go stale and
  put a wrong company number in front of paying members (^o96, fixed 18/09).

  So this script does two jobs, and the second one is the point:

    1. It runs the tests in RUN.
    2. It REFUSES if any test_*.py at the repo root is in neither RUN nor
       KNOWN_RED. A test added tomorrow cannot quietly join the nineteen — it
       either runs, or it is listed as red with a reason and an owner.

  KNOWN_RED is not a dumping ground. Every entry names what is broken and the
  OUTSTANDING id tracking it. Moving a test into KNOWN_RED to get a push through
  is the thing root rule 13 exists to stop: if the gate and the data disagree,
  the data is wrong.

Usage:
    python3 scripts/run_unit_tests.py            # run them
    python3 scripts/run_unit_tests.py --list     # just show the split
"""
import glob
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Run in their own workflow already — not re-run here, so this job stays short.
# NOTE: all but test_verify.py run on a DATA workflow's own schedule, not on
# every push, so they gate the run that produces their data rather than the
# commit that changes their code. Verified against .github/workflows/ 18/09/2026.
ELSEWHERE = {
    "test_verify.py":                     "verify.yml (selftest job)",
    "test_verify_careers.py":             "supplier-careers.yml",
    "test_careers_evidence.py":           "supplier-careers.yml",
    "test_icc_matrix.py":                 "icc-and-ccf.yml",
    "test_orphaned_product_categories.py": "company-intelligence.yml",
    "test_prune_calendar.py":             "calendar-prune.yml",
    # Added 19/09/2026 with the ASCII-folding fix, and registered here the same
    # day because it arrived unregistered and stopped this job dead (three red
    # pushes, publish gate green throughout). It runs on every push in
    # verify.yml's own selftest job, which is where a check that the Hub's
    # search still finds Molnlycke belongs.
    "test_ascii_folding.py":              "verify.yml (selftest job), search-index.yml",
}

# Green on clean main, 18/09/2026. Total runtime ~45s, nearly all of it
# test_dead_company_check.py.
RUN = [
    "test_breadcrumb_division.py",
    "test_company_match_overrides.py",
    "test_company_press_story_links.py",
    "test_company_tiers.py",
    "test_coverage_ledger.py",
    "test_crawl_site_concurrency.py",
    "test_dead_company_check.py",
    "test_hospital_prescribing_resources.py",
    "test_merge_seed_on_retry.py",
    "test_numeric_slug_detail.py",
    "test_product_detail_cursor.py",
    "test_product_types.py",
    "test_product_dossiers.py",
    "test_product_specs.py",
    "test_previous_names.py",
    "test_seed_domains.py",
    "test_speciality_news.py",
    "test_speciality_news_pipeline_merge.py",
    "test_speciality_panels.py",
    "test_stale_brief_rows.py",
    "test_supplier_index_awards.py",
]

# A test that is red for a reason that is its own decision goes HERE, not out of
# the runner: tracked, with the decision named, and moved back up into RUN in the
# same change that fixes the cause. Empty is the correct steady state.
#
# Emptied 18/09/2026. test_previous_names.py was the last entry — it forbade the
# Gemini Surgical UK / Healthcare 25 Ltd merge until rename-versus-sale was
# settled. Find a Tender 2025/S 000-077817 settled it (one supplier party, legal
# name Healthcare 25 Ltd, contact Paula@geminisurgical.co.uk, awarded after the
# rename), Lou confirmed, and the test was rewritten to assert the merge and
# moved into RUN (^o535). The Lowenstein/Löwenstein duplicate it also caught was
# merged the same day.
KNOWN_RED = {}


# Tests that REBUILD repo data as a side effect of running. They are legitimate
# — test_speciality_panels.py has to rebuild the panels to assert on them — but
# this runner also fires from hooks/pre-push, and leaving a working tree dirty
# mid-push is how a stray generated file ends up committed by accident. So the
# runner puts back exactly what such a test rebuilt.
#
# It CANNOT protect an uncommitted edit of its own: the test overwrites those
# files the moment it runs, before anything here sees them. Tried and measured
# 18/09/2026 — a hand-edited dermatology.json was destroyed by the rebuild, and
# skipping the restore for it only left the rebuilt version sitting there
# instead. So the honest behaviour is to REFUSE up front when the test's own
# output paths are already dirty, and say what to do, rather than quietly
# destroy work.
DIRTIES_TREE = {
    "test_speciality_panels.py": ["data/speciality-panels"],
}


def _dirty_paths():
    """Paths git currently reports as changed. Empty on any git failure — this
    is a convenience, and it must never be the reason a test run fails."""
    try:
        out = subprocess.run(["git", "status", "--porcelain"],
                             capture_output=True, text=True, cwd=ROOT)
        if out.returncode != 0:
            return None
        return {line[3:].strip() for line in out.stdout.splitlines() if line.strip()}
    except Exception:
        return None


def _restore(before, after, roots):
    """git checkout -- the generated files this test rebuilt.

    Only reached once the clash check above has established that nothing under
    `roots` was dirty beforehand, so everything new here is the test's own
    output and safe to throw away.
    """
    if before is None or after is None:
        return []
    new = sorted(p for p in (after - before)
                 if any(p.startswith(r.rstrip("/") + "/") or p == r for r in roots))
    if new:
        subprocess.run(["git", "checkout", "--"] + new, cwd=ROOT,
                       capture_output=True, text=True)
    return new


def main():
    os.chdir(ROOT)
    found = set(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "test_*.py")))
    accounted = set(RUN) | set(KNOWN_RED) | set(ELSEWHERE)

    unaccounted = sorted(found - accounted)
    if unaccounted:
        print("REFUSING: test file(s) in neither RUN nor KNOWN_RED nor ELSEWHERE.")
        print("A test nothing runs is a test that rots. Add it to RUN in")
        print("scripts/run_unit_tests.py, or to KNOWN_RED with a reason and an")
        print("OUTSTANDING id:")
        for t in unaccounted:
            print("    %s" % t)
        return 1

    missing = sorted(accounted - found)
    if missing:
        print("REFUSING: listed test file(s) do not exist — the list has gone stale:")
        for t in missing:
            print("    %s" % t)
        return 1

    if "--list" in sys.argv:
        print("RUN (%d):" % len(RUN))
        for t in RUN:
            print("    %s" % t)
        print("KNOWN_RED (%d):" % len(KNOWN_RED))
        for t, why in sorted(KNOWN_RED.items()):
            print("    %s\n        %s" % (t, why))
        print("ELSEWHERE (%d):" % len(ELSEWHERE))
        for t, where in sorted(ELSEWHERE.items()):
            print("    %-40s %s" % (t, where))
        return 0

    print("%d test file(s) to run; %d known-red and tracked; %d run in their own "
          "workflow." % (len(RUN), len(KNOWN_RED), len(ELSEWHERE)))
    failed = []
    for t in RUN:
        roots = DIRTIES_TREE.get(t)
        before = _dirty_paths() if roots else None
        if roots and before is not None:
            clash = sorted(p for p in before
                           if any(p.startswith(r.rstrip("/") + "/") or p == r for r in roots))
            if clash:
                print("%-42s %6s  REFUSED" % (t, "-"))
                print("    %s rebuilds %s, which would destroy these uncommitted "
                      "changes:" % (t, ", ".join(roots)))
                for c in clash[:10]:
                    print("        %s" % c)
                if len(clash) > 10:
                    print("        ... and %d more" % (len(clash) - 10))
                print("    Commit or stash them, then run again.")
                failed.append((t, "refused: uncommitted changes under %s" % ", ".join(roots)))
                continue
        started = time.time()
        p = subprocess.run([sys.executable, t], capture_output=True, text=True)
        took = time.time() - started
        restored = _restore(before, _dirty_paths(), roots) if roots else []
        note = "" if not restored else "  (put back %d rebuilt file(s))" % len(restored)
        print("%-42s %6.1fs  %s%s" % (t, took, "ok" if p.returncode == 0 else "FAILED", note))
        if p.returncode != 0:
            failed.append((t, (p.stdout or "") + (p.stderr or "")))
        sys.stdout.flush()

    if not failed:
        print("\nAll %d passed." % len(RUN))
        return 0

    for t, out in failed:
        print("\n" + "=" * 70)
        print("FAILED: %s" % t)
        print("=" * 70)
        print(out[-4000:])
    print("\n%d of %d FAILED." % (len(failed), len(RUN)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
