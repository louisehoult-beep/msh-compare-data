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
    * test_previous_names.py asserts that Gemini Surgical UK stays a separate
      seed record until Lou rules on rename-versus-sale. A seed merge folded it
      into Healthcare 25 Ltd anyway. Nothing noticed, because nothing ran it.

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
}

# Green on clean main, 18/09/2026. Total runtime ~45s, nearly all of it
# test_dead_company_check.py.
RUN = [
    "test_breadcrumb_division.py",
    "test_company_match_overrides.py",
    "test_company_tiers.py",
    "test_coverage_ledger.py",
    "test_crawl_site_concurrency.py",
    "test_dead_company_check.py",
    "test_merge_seed_on_retry.py",
    "test_numeric_slug_detail.py",
    "test_product_detail_cursor.py",
    "test_product_dossiers.py",
    "test_product_specs.py",
    "test_seed_domains.py",
    "test_speciality_news.py",
    "test_speciality_news_pipeline_merge.py",
    "test_stale_brief_rows.py",
    "test_supplier_index_awards.py",
]

# Red on clean main 18/09/2026, each for a reason that is its own decision.
# These are NOT excused — they are tracked. Fix the cause, then move the file up
# into RUN in the same change.
KNOWN_RED = {
    "test_previous_names.py":
        "^o535 — three failures. The one that matters: a seed merge folded "
        "Gemini Surgical UK into Healthcare 25 Ltd, which this test forbids "
        "until Lou rules on rename-versus-sale. Also 6 register-sourced "
        "previous names that are not aliases (so no search finds them), and 2 "
        "new name collisions (Lowenstein, Nipro). Lou's decision, not a fix.",
    "test_product_types.py":
        "^o536 — test-isolation bug, not a data fault. All three 'real, "
        "currently-shipped files' checks pass. One synthetic fixture case trips "
        "verify.py's own shrink guard, because the fixture's cut-down "
        "product-types.json looks like 164 lost entries against the committed "
        "one. The case needs isolating from the shrink guard.",
    "test_speciality_panels.py":
        "^o537 — 9 failures, mostly hard-coded expected counts that drifted as "
        "the data grew (8 awards -> 11, 33 -> 35, 19+8 suppliers -> 25, five "
        "unresolved names -> four). One looks real and is not drift: 42 awards "
        "matched but only 40 shown. Also rebuilds data/speciality-panels/ as a "
        "side effect, so it dirties the tree it runs in.",
}


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
        started = time.time()
        p = subprocess.run([sys.executable, t], capture_output=True, text=True)
        took = time.time() - started
        print("%-42s %6.1fs  %s" % (t, took, "ok" if p.returncode == 0 else "FAILED"))
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
