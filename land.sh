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

# ---------------------------------------------------------------- the tree lock
#
# ADDED 25/08/2026. Everything above assumes one writer at a time on this laptop,
# and nothing was enforcing it. This working tree lives on OneDrive and is shared
# by every scheduled task and every interactive session, so two of them routinely
# overlap. On 25/08 a session read a clean tree, and forty seconds later found
# `.git/index.lock` held by another routine mid-run, then two files staged that it
# had never touched. That is not a rare race — it is the normal state of a shared
# tree with no lock.
#
# `flock` is util-linux and does not exist on macOS, so this is a portable mkdir
# lock: mkdir is atomic on POSIX, and the PID inside lets a genuinely dead lock be
# cleared without a human guessing.
# --git-common-dir, NOT --git-dir. Since 28/08/2026 sessions work in their own
# worktrees (wt.sh), and in a worktree --git-dir is that worktree's private
# .git/worktrees/<name> directory. Using it would give every worktree its own
# lock, i.e. no lock at all, and the failure would be silent: each run would take
# its own lock happily and land straight into the race this exists to stop.
# --git-common-dir is the one shared .git behind every worktree.
LOCK_DIR="$(git rev-parse --git-common-dir)/land.lock"
LOCK_WAIT_SECONDS="${LAND_LOCK_WAIT:-600}"

LOCK_HELD=0

acquire_lock() {
  local waited=0
  while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    local holder
    holder="$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "")"
    if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then
      echo "clearing a stale lock left by pid $holder (no such process)" >&2
      rm -rf "$LOCK_DIR"
      continue
    fi
    if [ "$waited" -eq 0 ]; then
      echo "==> waiting for the tree lock (held by pid ${holder:-unknown})."
      echo "    Another session or scheduled task is landing. This waits rather than"
      echo "    interleaving with it, which is how half-staged trees happen."
    fi
    if [ "$waited" -ge "$LOCK_WAIT_SECONDS" ]; then
      echo "REFUSING: the tree lock was still held after ${LOCK_WAIT_SECONDS}s (pid ${holder:-unknown})." >&2
      echo "Nothing has been staged or committed. Check what that process is doing." >&2
      exit 1
    fi
    sleep 5
    waited=$((waited + 5))
  done
  echo "$$" > "$LOCK_DIR/pid"
  LOCK_HELD=1
  [ "$waited" -gt 0 ] && echo "==> tree lock acquired after ${waited}s"
  return 0
}

# Only ever release a lock THIS process acquired. Releasing unconditionally would
# mean a run that timed out waiting deleted the holder's lock on its way out and
# let the next writer barge in — the exact interleaving the lock exists to stop.
release_lock() { [ "$LOCK_HELD" = "1" ] && rm -rf "$LOCK_DIR"; }
trap release_lock EXIT INT TERM

acquire_lock

echo "==> 1/7 fetching origin"
git fetch --quiet origin

# ------------------------------------------------- somebody else's unpushed work
#
# ADDED 25/08/2026. This script ends in `git push origin main`, which pushes the
# whole BRANCH, not just the commit it made. So any commit already sitting
# unpushed goes out with yours — and a push here IS a publish (root rule 13).
#
# On 25/08 two such commits were sitting in the tree: a supplier duplicate merge
# committed by hand three days earlier, and an alias-enrichment batch that had
# committed and then failed to push because the publish gate was jammed. Both
# were fine, and both were published by a run that was not looking for them.
# Next time they might not be fine, so they get named and acknowledged instead.
PENDING="$(git rev-list --count origin/main..HEAD)"
if [ "$PENDING" -gt 0 ] && [ "${WITH_PENDING:-0}" != "1" ]; then
  echo "" >&2
  echo "REFUSING: $PENDING commit(s) are already sitting here unpushed, and a push" >&2
  echo "publishes the whole branch — so they would go live with your work:" >&2
  echo "" >&2
  git --no-pager log --oneline origin/main..HEAD | sed 's/^/    /' >&2
  echo "" >&2
  echo "Read them. If they are meant to publish, re-run with WITH_PENDING=1:" >&2
  echo "    WITH_PENDING=1 ./land.sh \"$SUBJECT\" ..." >&2
  echo "If they are not, resolve them first. Nothing has been staged." >&2
  exit 1
fi
if [ "$PENDING" -gt 0 ]; then
  echo "==> publishing $PENDING pre-existing commit(s) alongside this one (WITH_PENDING=1):"
  git --no-pager log --oneline origin/main..HEAD | sed 's/^/    /'
fi

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
python3 scripts/check_no_loss.py "${CHECK_ARGS[@]+"${CHECK_ARGS[@]}"}" || {
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
# HEAD:main, not main. In a worktree HEAD is the per-session branch wt/<name>, and
# `git push origin main` would push the stale local main instead of the work just
# rebased and gated here. In the shared tree HEAD *is* main, so this is identical.
git push origin HEAD:main
echo "LANDED: $SUBJECT"
