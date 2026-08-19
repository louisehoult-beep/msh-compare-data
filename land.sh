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
#   ./land.sh "commit subject" [--allow identity]... path [path...]
#
# --allow is passed straight through to check_no_loss.py (step 4) to record a
# record-collection deletion you have already decided on and checked by hand —
# e.g. an entry that moved from a "held" summary into the published list this
# same change produces. It does not weaken the check: check_no_loss.py refuses
# by default and --allow is its own documented, per-identity opt-in, not a
# blanket bypass. Repeatable: --allow "X" --allow "Y".
#
# It refuses rather than guesses. Every refusal below is a real failure this
# repo has already had.
set -euo pipefail
cd "$(dirname "$0")"

SUBJECT="${1:-}"; shift || true
if [ -z "$SUBJECT" ]; then
  echo "usage: ./land.sh \"commit subject\" [--allow identity]... path [path...]" >&2
  echo "Name the paths this piece of work owns. Never 'git add -A' in this repo:" >&2
  echo "another session's half-finished work is very often sitting beside yours." >&2
  exit 2
fi

ALLOW=()
PATHS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --allow)
      if [ $# -lt 2 ]; then
        echo "REFUSING: --allow needs a value." >&2
        exit 2
      fi
      ALLOW+=("$2")
      shift 2
      ;;
    *)
      PATHS+=("$1")
      shift
      ;;
  esac
done

if [ ${#PATHS[@]} -eq 0 ]; then
  echo "usage: ./land.sh \"commit subject\" [--allow identity]... path [path...]" >&2
  echo "Name the paths this piece of work owns. Never 'git add -A' in this repo:" >&2
  echo "another session's half-finished work is very often sitting beside yours." >&2
  exit 2
fi

echo "==> 1/7 fetching origin"
git fetch --quiet origin

echo "==> 2/7 checking nothing else is staged"
if ! git diff --cached --quiet; then
  echo "REFUSING: something is already staged. Landing one piece at a time is the" >&2
  echo "whole point of this script. Unstage, then re-run with your paths." >&2
  exit 1
fi

echo "==> 3/7 staging only the named paths"
git add -- "${PATHS[@]}"
git diff --cached --name-only | sed 's/^/    /'

echo "==> 4/7 record-level no-loss check (working tree vs origin/main)"
CHECK_ARGS=()
for a in "${ALLOW[@]:-}"; do
  [ -n "$a" ] && CHECK_ARGS+=(--allow "$a")
done
python3 scripts/check_no_loss.py "${CHECK_ARGS[@]:-}" || {
  echo "REFUSING: a staged data file loses records against origin/main." >&2
  echo "Diff by record, not by line. A file that quietly lost entries is not a" >&2
  echo "conflict to git, and a plain rebase would publish the loss." >&2
  exit 1
}

echo "==> 5/7 committing this piece"
# The commit has to come BEFORE the rebase: git refuses to rebase with a staged
# index, and leaving the work uncommitted through a rebase is how it ends up in
# a stash nobody comes back to (there was one of those, held since 14/08).
git commit -q -m "$SUBJECT"

echo "==> 6/7 rebasing onto origin/main"
# -X theirs is deliberately NOT used. On a generated JSON file it keeps the other
# writer's non-conflicting hunks and produces a file whose counts header and rows
# come from different generations (the 14/08 incident). If the rebase conflicts,
# stop and let a human regenerate on top of origin/main.
git rebase origin/main || {
  echo "REFUSING: rebase conflicted. Do not resolve a generated JSON file by hand" >&2
  echo "or with -X theirs. Abort, regenerate on top of origin/main, and re-run." >&2
  echo "Your commit is safe — 'git rebase --abort' leaves it on the branch." >&2
  exit 1
}

echo "==> 7/7 gate, then push"
python3 verify.py || {
  echo "REFUSING: verify.py failed after the rebase. Root rule 13 — if the gate" >&2
  echo "and the data disagree, the data is wrong. Never loosen a check to get a" >&2
  echo "push through. Your commit is on the branch; fix and re-gate." >&2
  exit 1
}
git push origin main
echo "LANDED: $SUBJECT"
