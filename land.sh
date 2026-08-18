#!/usr/bin/env bash
# land.sh — the single landing lane for msh-compare-data.
#
# A push to main IS a publish (root rule 13): the Hub fetches these files
# directly and members see whatever lands within seconds. This script is the
# only route a session should use, because every incident this repo has had
# came from several writers sharing one working tree on main:
#
#   12/08  a 28-minute company-intelligence run thrown away on a lost race
#   14/08  a rebase text-merged a generated JSON file into a Frankenstein
#   18/08  four unrelated pieces of work stuck in one dirty tree, one of them
#          a stale seed that would have deleted five deep dives on push
#
# Usage:
#   ./land.sh "commit subject" path [path...]
#
# It refuses rather than guesses. Every refusal below is a real failure this
# repo has already had.
set -euo pipefail
cd "$(dirname "$0")"

SUBJECT="${1:-}"; shift || true
if [ -z "$SUBJECT" ] || [ $# -eq 0 ]; then
  echo "usage: ./land.sh \"commit subject\" path [path...]" >&2
  echo "Name the paths this piece of work owns. Never 'git add -A' in this repo:" >&2
  echo "another session's half-finished work is very often sitting beside yours." >&2
  exit 2
fi

echo "==> 1/6 fetching origin"
git fetch --quiet origin

echo "==> 2/6 checking nothing else is staged"
if ! git diff --cached --quiet; then
  echo "REFUSING: something is already staged. Landing one piece at a time is the" >&2
  echo "whole point of this script. Unstage, then re-run with your paths." >&2
  exit 1
fi

echo "==> 3/6 staging only the named paths"
git add -- "$@"
git diff --cached --name-only | sed 's/^/    /'

echo "==> 4/6 record-level no-loss check (working tree vs origin/main)"
python3 scripts/check_no_loss.py || {
  echo "REFUSING: a staged data file loses records against origin/main." >&2
  echo "Diff by record, not by line. A file that quietly lost entries is not a" >&2
  echo "conflict to git, and a plain rebase would publish the loss." >&2
  exit 1
}

echo "==> 5/6 rebasing onto origin/main, then REGENERATING nothing and re-gating"
# -X theirs is deliberately NOT used here. On a generated JSON file it keeps the
# other writer's non-conflicting hunks and produces a file whose counts header
# and rows come from different generations (14/08 incident). If the rebase
# conflicts, stop and let a human regenerate.
git rebase origin/main || {
  echo "REFUSING: rebase conflicted. Do not resolve a generated JSON file by hand" >&2
  echo "or with -X theirs. Regenerate it on top of origin/main and re-run." >&2
  git rebase --abort || true
  exit 1
}

echo "==> 6/6 gate, then push"
python3 verify.py || {
  echo "REFUSING: verify.py failed. Root rule 13 — if the gate and the data" >&2
  echo "disagree, the data is wrong. Never loosen a check to get a push through." >&2
  exit 1
}
git commit -q -m "$SUBJECT" || echo "    (nothing to commit)"
git push origin main
echo "LANDED: $SUBJECT"
