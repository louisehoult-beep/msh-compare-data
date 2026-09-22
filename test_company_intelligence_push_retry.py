#!/usr/bin/env python3
"""Prove the company-intelligence push-retry loop survives a lost push race.

WHY THIS EXISTS
  On 21/09/2026 the scheduled "Company intelligence" run (35579949455) did an
  hour and five minutes of real work — frameworks, Companies House profiles,
  filed accounts, awards — passed the gate, committed, and then lost the push
  race to another writer. The retry loop is there for exactly that, and it threw
  the whole hour away instead:

      [merge_seed_on_retry] wrote data/supplier-seed.json: 1239 merged, ...
      error: cannot rebase: Your index contains uncommitted changes.
      error: Please commit or stash them.
      REBASE CONFLICT on a non-seed file - refusing to push. Abort and re-run.

  scripts/merge_seed_on_retry.py writes the merged seed into the WORKING TREE.
  The loop staged it with `git add` and went straight into `git rebase`, and
  rebase refuses outright on a dirty index. The message even says "on a non-seed
  file", which is the opposite of what happened — there was no conflict at all,
  only an uncommitted index. cb4e0fb fixed it by committing (amending) the
  merged seed before the rebase.

  That bug was invisible to every test in this repo, because every test here
  checks Python and the bug was in workflow YAML. It also only fires on a race,
  so it can sit green for weeks and then eat an hour of Companies House quota
  the one morning two writers overlap. Hence this file: it runs the workflow's
  OWN shell, extracted from the YAML, against a synthetic repo that reproduces
  the 21/09 race, and it fails if anyone puts the broken sequence back.

WHAT IS REAL AND WHAT IS STUBBED
  Real: the entire `run:` script of the "Commit updates" step, read out of
  .github/workflows/company-intelligence.yml at test time. Not a copy — a copy
  would drift from the workflow silently, which is the whole failure mode here.
  Real: git, and a real lost push race against a real (local, bare) origin.

  Stdlib only, including the YAML block-scalar read: the "Repo unit tests" job
  installs no packages, so a third-party import here turns that job red rather
  than testing anything (it did, on 22/09/2026).

  Stubbed: scripts/merge_seed_on_retry.py and verify.py. This test is about the
  GIT SEQUENCE around them, not about either one — merge_seed_on_retry.py has
  its own suite in test_merge_seed_on_retry.py, and verify.py has test_verify.py.
  The stub merge does the same SHAPE of thing the real one does (CI-owned fields
  from HEAD, curated fields preserved from origin/main), because the assertions
  below are about whether that result survives the rebase, not how it is
  computed.

Offline. No network, no API keys. ~7s, nearly all of it the loop's own
`sleep 5`. Leaves the tree clean: everything happens under a temp dir.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
WORKFLOW = os.path.join(REPO, ".github", "workflows", "company-intelligence.yml")
STEP_NAME = "Commit updates"

# The six files the step's `git add` names. They all have to exist in the
# synthetic repo or the step dies on the add for the wrong reason.
TRACKED = [
    "data/frameworks.json",
    "data/company-financials.json",
    "data/company-awards.json",
    "data/pending-awards.json",
    "data/supplier-index.json",
    "data/supplier-seed.json",
]

# The stub stands in for scripts/merge_seed_on_retry.py: read the seed as
# origin/main now has it, read the seed as this run built it, and produce the
# field-level merge — CI-owned fields from HEAD, curated fields from origin/main.
MERGE_STUB = '''#!/usr/bin/env python3
"""Stand-in for merge_seed_on_retry.py. Same shape, two fields, no schema."""
import json, subprocess, sys

theirs = json.loads(subprocess.run(
    ["git", "show", "origin/main:data/supplier-seed.json"],
    capture_output=True, text=True, check=True).stdout)
ours = json.loads(subprocess.run(
    ["git", "show", "HEAD:data/supplier-seed.json"],
    capture_output=True, text=True, check=True).stdout)

merged = dict(theirs)
merged["ci_owned"] = ours["ci_owned"]          # this run's regenerated data wins
merged["curated"] = theirs["curated"]          # a human's edit on main is kept
with open("data/supplier-seed.json", "w") as fh:
    json.dump(merged, fh)
print("[merge_seed_on_retry stub] wrote data/supplier-seed.json")
'''

VERIFY_STUB = '#!/usr/bin/env python3\nprint("[verify stub] gate passed")\n'


def run(cmd, cwd, check=True, env=None):
    full = dict(os.environ)
    full.update(env or {})
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True,
                          text=True, env=full)


# Markers that must appear in whatever we extract. The danger with pulling text
# out of a file is not a loud parse error, it is quietly extracting the WRONG
# text and then proving nothing about the real workflow. If the step is renamed,
# restructured, or the extractor drifts, these turn that into a failure.
EXPECTED_IN_SCRIPT = [
    "pushed=0",
    "scripts/merge_seed_on_retry.py",
    "git rebase origin/main",
    "git add data/supplier-seed.json",
]


def commit_script():
    """The 'Commit updates' step's shell, straight out of the workflow YAML.

    Hand-rolled rather than pyyaml on purpose. The "Repo unit tests" job in
    verify.yml installs nothing — it is checkout, setup-python, run — so every
    test here is stdlib-only. Adding a pip step to a 45-second job for one
    import is the wrong trade, and on 22/09/2026 importing yaml here turned that
    job red on main and fired the phone alert. All this needs is one `run: |`
    block scalar, which is a dozen lines of indentation handling.
    """
    with open(WORKFLOW, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    # Find the step, then its `run: |` key.
    i = next((n for n, l in enumerate(lines)
              if l.strip() == "- name: %s" % STEP_NAME), None)
    if i is None:
        raise AssertionError(
            "no %r step in %s — the step was renamed and this test now proves "
            "nothing. Point it at the new name." % (STEP_NAME, WORKFLOW))
    run_at = next((n for n in range(i, len(lines))
                   if lines[n].strip() in ("run: |", "run: |-", "run: |+")), None)
    if run_at is None:
        raise AssertionError(
            "the %r step no longer holds a `run: |` block in %s. Whatever it "
            "runs now is untested by this file." % (STEP_NAME, WORKFLOW))

    # A block scalar's body is every following line indented deeper than the
    # first body line's indent; blank lines belong to it whatever their width.
    body = lines[run_at + 1:]
    first = next((l for l in body if l.strip()), "")
    indent = len(first) - len(first.lstrip(" "))
    out = []
    for line in body:
        if not line.strip():
            out.append("")
            continue
        if len(line) - len(line.lstrip(" ")) < indent:
            break
        out.append(line[indent:])
    script = "\n".join(out).rstrip("\n") + "\n"

    missing = [m for m in EXPECTED_IN_SCRIPT if m not in script]
    if missing:
        raise AssertionError(
            "extracted the %r step but it is missing %s. Either the step "
            "changed shape or this extractor is picking up the wrong text — "
            "either way this test is no longer checking the retry loop."
            % (STEP_NAME, ", ".join(repr(m) for m in missing)))
    return script


def build_race(root, script):
    """A runner clone mid-race: it has committed, a peer has landed first.

    Returns the runner clone's path. The state afterwards is exactly the
    21/09 one: our commit is on top of the origin/main we started from, and
    origin/main has since moved on with a peer's curated edit to the seed.
    """
    origin = os.path.join(root, "origin.git")
    run(["git", "init", "-q", "--bare", origin], cwd=root)

    # --- the starting point both sides share -----------------------------
    seed = os.path.join(root, "seed")
    run(["git", "clone", "-q", origin, seed], cwd=root)
    run(["git", "config", "user.email", "t@example.invalid"], cwd=seed)
    run(["git", "config", "user.name", "t"], cwd=seed)
    os.makedirs(os.path.join(seed, "data"))
    os.makedirs(os.path.join(seed, "scripts"))
    for path in TRACKED:
        with open(os.path.join(seed, path), "w") as fh:
            if path.endswith("supplier-seed.json"):
                json.dump({"ci_owned": "week-0", "curated": "hand-written"}, fh)
            else:
                json.dump({"generated": "week-0"}, fh)

    merge = os.path.join(seed, "scripts", "merge_seed_on_retry.py")
    with open(merge, "w") as fh:
        fh.write(MERGE_STUB)
    os.chmod(merge, 0o755)
    with open(os.path.join(seed, "verify.py"), "w") as fh:
        fh.write(VERIFY_STUB)

    run(["git", "add", "-A"], cwd=seed)
    run(["git", "commit", "-qm", "base"], cwd=seed)
    run(["git", "branch", "-M", "main"], cwd=seed)
    run(["git", "push", "-q", "origin", "main"], cwd=seed)

    # --- the runner: an hour of work, committed, not yet pushed ----------
    runner = os.path.join(root, "runner")
    run(["git", "clone", "-q", origin, runner], cwd=root)
    run(["git", "config", "user.email", "t@example.invalid"], cwd=runner)
    run(["git", "config", "user.name", "t"], cwd=runner)
    for path in TRACKED:
        with open(os.path.join(runner, path), "w") as fh:
            if path.endswith("supplier-seed.json"):
                json.dump({"ci_owned": "week-1", "curated": "hand-written"}, fh)
            else:
                json.dump({"generated": "week-1"}, fh)

    # --- the peer lands first, touching the one file we also touched ----
    run(["git", "pull", "-q"], cwd=seed)
    with open(os.path.join(seed, "data", "supplier-seed.json"), "w") as fh:
        json.dump({"ci_owned": "week-0", "curated": "LOU-EDITED-THIS"}, fh)
    run(["git", "add", "-A"], cwd=seed)
    run(["git", "commit", "-qm", "curated edit landed by a peer"], cwd=seed)
    run(["git", "push", "-q", "origin", "main"], cwd=seed)

    # Outside the working tree on purpose: a script file dropped inside the
    # clone would show up as untracked and make the "did the loop leave the tree
    # clean?" assertion below fail on the harness rather than on the loop.
    with open(os.path.join(root, "step.sh"), "w") as fh:
        fh.write(script)
    return runner


def exercise(root, script):
    """Run the step's shell against the race. Returns the CompletedProcess."""
    runner = build_race(root, script)
    tmp = os.path.join(root, "runner-temp")
    os.makedirs(tmp, exist_ok=True)
    return runner, subprocess.run(
        ["bash", "-e", os.path.join(root, "step.sh")], cwd=runner,
        capture_output=True, text=True,
        env=dict(os.environ, RUNNER_TEMP=tmp, GIT_TERMINAL_PROMPT="0"))


def break_it(script):
    """The pre-cb4e0fb sequence: stage the merged seed, never commit it.

    A regression test that cannot fail is decoration. This reproduces the exact
    shape of the 21/09 bug so the test below can prove it still catches it.
    """
    lines = script.split("\n")
    # Work on line numbers, not on a hard-coded indent: pyyaml strips the block
    # scalar's own indentation, so matching on leading spaces would break the
    # day someone re-indents the YAML and this test would go quietly green.
    start = next(i for i, l in enumerate(lines)
                 if l.strip() == "git add data/supplier-seed.json")
    end = next(i for i, l in enumerate(lines)
               if l.strip().startswith("# Rebase everything else onto origin/main"))
    # Keep the `git add`, drop the commit/amend block that cb4e0fb introduced.
    return "\n".join(lines[:start + 1] + lines[end:])


def main():
    failures = []
    script = commit_script()

    # ---------------------------------------------------------------- 1 ---
    # The fix holds: the race is survived and nothing is thrown away.
    root = tempfile.mkdtemp(prefix="ci-push-retry-")
    try:
        runner, proc = exercise(root, script)
        if proc.returncode != 0:
            failures.append(
                "the retry loop failed on a lost push race — this is the "
                "21/09/2026 bug (run 35579949455), where an hour of work was "
                "discarded instead of retried.\n--- stdout ---\n%s\n--- stderr "
                "---\n%s" % (proc.stdout[-2000:], proc.stderr[-2000:]))
        else:
            landed = run(["git", "show", "origin/main:data/supplier-seed.json"],
                         cwd=runner).stdout
            seed = json.loads(landed)
            # The whole point of the retry: BOTH sides' work is on main.
            if seed.get("ci_owned") != "week-1":
                failures.append(
                    "this run's regenerated data did not reach main after the "
                    "retry (ci_owned=%r, expected 'week-1'). The hour of work "
                    "was silently dropped." % seed.get("ci_owned"))
            if seed.get("curated") != "LOU-EDITED-THIS":
                failures.append(
                    "the peer's curated edit was overwritten by the retry "
                    "(curated=%r, expected 'LOU-EDITED-THIS'). This is the "
                    "`-X theirs` data-loss class the loop's own comments "
                    "forbid." % seed.get("curated"))
            others = json.loads(run(
                ["git", "show", "origin/main:data/frameworks.json"],
                cwd=runner).stdout)
            if others.get("generated") != "week-1":
                failures.append(
                    "a non-seed file this run regenerated did not reach main "
                    "(frameworks.json generated=%r, expected 'week-1')."
                    % others.get("generated"))
            dirty = run(["git", "status", "--porcelain"], cwd=runner).stdout.strip()
            if dirty:
                failures.append(
                    "the loop left the working tree dirty after landing:\n%s" % dirty)
            if "pushed on attempt" not in proc.stdout:
                failures.append(
                    "the loop reported success without ever saying it pushed — "
                    "check the loop still actually pushes.\n%s" % proc.stdout[-1000:])
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ---------------------------------------------------------------- 2 ---
    # The test itself still bites: put the bug back and it must go red.
    root = tempfile.mkdtemp(prefix="ci-push-retry-broken-")
    try:
        _, proc = exercise(root, break_it(script))
        if proc.returncode == 0:
            failures.append(
                "SELF-TEST: the pre-cb4e0fb sequence (stage the merged seed, "
                "never commit it) PASSED. That sequence is the 21/09 bug, so "
                "this test is no longer detecting anything and the green above "
                "means nothing.")
        elif "cannot rebase" not in (proc.stdout + proc.stderr):
            failures.append(
                "SELF-TEST: the broken sequence failed, but not with the "
                "\"cannot rebase: Your index contains uncommitted changes\" "
                "symptom this test is built around. It may now be failing for "
                "an unrelated reason, which would hide a real "
                "regression.\n--- stdout ---\n%s\n--- stderr ---\n%s"
                % (proc.stdout[-1500:], proc.stderr[-1500:]))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print("FAILED (%d):\n" % len(failures))
        for f in failures:
            print("  - %s\n" % f)
        return 1
    print("company-intelligence push-retry: 2 cases passed.")
    print("  - a lost push race is survived; this run's data and the peer's "
          "curated edit both land")
    print("  - the pre-cb4e0fb sequence still fails, so this test still catches "
          "the 21/09 bug")
    return 0


if __name__ == "__main__":
    sys.exit(main())
