#!/usr/bin/env bash
# land.sh — the single landing lane for msh-compare-data.
#
# A push to main IS a publish (root rule 13): the Hub fetches these files
# directly and members see whatever lands within seconds. This script is the
# only route a session should use.
#
# REWRITTEN 08/09/2026: paired with begin.sh, which gives you a private
# throwaway clone instead of everyone editing one shared OneDrive checkout.
# That retires the session-claim and tree-lock machinery below (session-lock.sh,
# the land.lock mkdir-lock) — there is no longer a shared working tree for two
# writers to collide inside, so nothing to claim and nothing to wait on. The
# ONE remaining contention point is the push itself, and git already makes that
# atomic and safe: a `git push` that isn't a fast-forward is simply refused, so
# this can never silently overwrite someone else's landed work the way the
# pre-08/09 incidents did. It just fetches, rebases, and retries.
#
# Everything else here is unchanged and still exists because of a real incident:
#   12/08  a 28-minute company-intelligence run thrown away on a lost race
#   14/08  a rebase text-merged a generated JSON file into a Frankenstein
#   18/08  four unrelated pieces of work stuck in one dirty tree, one of them
#          a stale seed that would have deleted five deep dives on push
#
# Usage (run from inside a clone begin.sh gave you):
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
CLONE_ROOT="$(pwd)"

SUBJECT="${1:-}"; shift || true
if [ -z "$SUBJECT" ]; then
  echo "usage: ./land.sh \"commit subject\" [--allow identity]... path [path...]" >&2
  echo "Name the paths this piece of work owns. Never 'git add -A' — a clone from" >&2
  echo "begin.sh should only ever have your own edits in it, but name paths anyway." >&2
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
  exit 2
fi

echo "==> 1/7 fetching origin"
git fetch --quiet origin

# ------------------------------------------------- somebody else's unpushed work
#
# A clone from begin.sh starts clean, so this should never fire in normal use —
# kept as a defensive check in case land.sh is ever run somewhere that already
# had commits sitting on it (e.g. a manual clone, or a retry after a partial
# run). `git push` pushes the whole branch, not just the commit made here, and a
# push here IS a publish (root rule 13), so anything already sitting unpushed
# would go out with it unnoticed otherwise.
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

# --------------------------------------------------- rebase + push, with retry
#
# ADDED 08/09/2026, replacing the tree-lock. With everyone in their own clone,
# the only race left is two clones pushing at nearly the same moment. git
# already refuses a non-fast-forward push outright — it can never silently
# overwrite the other side, which is the actual guarantee the old lock was
# standing in for. So on a rejection this just re-fetches, re-rebases, re-gates
# and retries, a handful of times, rather than making every writer queue for a
# lock up front on the assumption a collision might happen.
ATTEMPTS="${LAND_PUSH_ATTEMPTS:-5}"
i=1
while :; do
  echo "==> 6/7 rebasing onto origin/main (attempt $i/$ATTEMPTS)"
  # -X theirs is deliberately NOT used. On a generated JSON file it keeps the
  # other writer's non-conflicting hunks and produces a file whose counts header
  # and rows come from different generations (the 14/08 incident). If the
  # rebase conflicts, stop and let a human regenerate on top of origin/main —
  # this is a real content clash, not a race, and retrying blind would be wrong.
  if ! git rebase origin/main; then
    echo "REFUSING: rebase conflicted. Do not resolve a generated JSON file by hand" >&2
    echo "or with -X theirs. Abort, regenerate on top of origin/main, and re-run." >&2
    echo "Your commit is safe — 'git rebase --abort' leaves it on the branch." >&2
    exit 1
  fi

  echo "==> 7/7 gate, then push"
  python3 verify.py || {
    echo "REFUSING: verify.py failed after the rebase. Root rule 13 — if the gate" >&2
    echo "and the data disagree, the data is wrong. Never loosen a check to get a" >&2
    echo "push through. Your commit is on the branch; fix and re-gate." >&2
    exit 1
  }

  if git push origin HEAD:main 2>/tmp/land-push-err.$$; then
    rm -f /tmp/land-push-err.$$
    break
  fi
  PUSH_ERR="$(cat /tmp/land-push-err.$$ 2>/dev/null || true)"
  rm -f /tmp/land-push-err.$$
  if [ "$i" -ge "$ATTEMPTS" ]; then
    echo "REFUSING: push still rejected after $ATTEMPTS attempts:" >&2
    echo "$PUSH_ERR" | sed 's/^/    /' >&2
    echo "Your commit is safe on this branch. Something is landing very fast right" >&2
    echo "now, or the remote genuinely refused it — check by hand." >&2
    exit 1
  fi
  echo "==> push rejected (someone else landed first) — re-fetching and retrying"
  git fetch --quiet origin
  i=$((i + 1))
done
echo "LANDED: $SUBJECT"

# ------------------------------------------------------------------ self-clean
# Only ever remove a clone begin.sh actually made, under its own directory —
# never the shared OneDrive checkout, and never anything land.sh is run from
# outside that convention.
case "$CLONE_ROOT" in
  "$HOME"/.claude/msh-work/*)
    cd /tmp
    rm -rf "$CLONE_ROOT"
    echo "==> clone cleaned up ($CLONE_ROOT)"
    ;;
esac
