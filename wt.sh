#!/usr/bin/env bash
# wt.sh — give this session its own working tree.
#
# WHY THIS EXISTS
#   Until 28/08/2026 every session and every scheduled task edited ONE checkout of
#   this repo, on OneDrive, on main. land.sh made *landing* safe — it locks, stages
#   by path and refuses to publish someone else's pending commit. It cannot make
#   *editing* safe, because the danger is in the hours before the landing:
#
#     18/08  a commit swept in another session's half-finished verify.py and
#            stamp_notice.py and published them
#     18/08  a session overwrote verify.py wholesale and silently deleted another
#            session's in-flight 154-line check; it surfaced as 5 failing tests
#     26/08  the supplier-deep-capture run left the Delta Surgical record
#            uncommitted, the next sweep wrote over the same files, and the record
#            was gone. Nobody saw it go.
#
#   Each of those is one tree with two writers. A per-session worktree removes the
#   shared surface entirely: your files are yours, nobody can overwrite them
#   mid-edit, and an abandoned session leaves its mess in its own directory instead
#   of in everyone's.
#
# WHERE THEY LIVE
#   ~/msh-worktrees/<name> — deliberately NOT inside Cowork-OS. A checkout is 115 MB
#   of mostly-generated JSON that changes constantly; putting several of those on
#   OneDrive means gigabytes of sync churn, and OneDrive has silently reverted edits
#   in this workspace before. The repo history stays in the one shared .git.
#
# USAGE
#   ./wt.sh <name>            create or re-enter a worktree, print its path
#   ./wt.sh --list            every worktree, with its state
#   ./wt.sh --remove <name>   remove one (refuses if it holds work)
#   ./wt.sh --for-task <name> unattended: clean checkout at origin/main, or exit 3
#
#   Typical session:
#       cd "$(./wt.sh trust-profiles-batch-8)"
#       ...edit, run scripts...
#       ./land.sh "Trust profiles batch eight" data/prep-config.json
#
#   land.sh works unchanged inside a worktree: it takes the tree lock in the shared
#   .git so it still serialises against every other worktree, and it pushes HEAD to
#   main rather than the local branch.
set -euo pipefail
cd "$(dirname "$0")"

ROOT="${MSH_WORKTREE_ROOT:-$HOME/msh-worktrees}"

usage() {
  echo "usage: ./wt.sh <name> | --list | --remove <name>" >&2
  echo "  <name>: letters, digits, dot, dash, underscore. Name it after the work," >&2
  echo "          not after yourself — 'atamis-refresh', not 'session3'." >&2
  exit 2
}

# --------------------------------------------------------------------- --list
if [ "${1:-}" = "--list" ]; then
  git worktree list --porcelain | awk '/^worktree /{print $2}' | while read -r w; do
    [ -d "$w" ] || continue
    dirty="$(git -C "$w" status --porcelain 2>/dev/null | grep -vc 'backup' || true)"
    ahead="$(git -C "$w" rev-list --count origin/main..HEAD 2>/dev/null || echo '?')"
    head="$(git -C "$w" log --oneline -1 2>/dev/null || echo '(no commit)')"
    printf '%s\n    unpushed: %s   uncommitted files: %s\n    %s\n' "$w" "$ahead" "$dirty" "$head"
  done
  exit 0
fi

# ------------------------------------------------------------------- --remove
if [ "${1:-}" = "--remove" ]; then
  NAME="${2:-}"; [ -n "$NAME" ] || usage
  WT="$ROOT/$NAME"
  [ -d "$WT" ] || { echo "no such worktree: $WT" >&2; exit 1; }
  # Refuse to bin work. Both halves matter: uncommitted files vanish with the
  # directory, and a commit that never reached origin vanishes with the branch.
  if [ -n "$(git -C "$WT" status --porcelain --untracked-files=no)" ]; then
    echo "REFUSING: $NAME has uncommitted changes. Land them or revert them first:" >&2
    git -C "$WT" status --short --untracked-files=no | sed 's/^/    /' >&2
    exit 1
  fi
  AHEAD="$(git -C "$WT" rev-list --count origin/main..HEAD 2>/dev/null || echo 0)"
  if [ "$AHEAD" != "0" ]; then
    echo "REFUSING: $NAME holds $AHEAD unpushed commit(s) — removing it loses them:" >&2
    git -C "$WT" --no-pager log --oneline origin/main..HEAD | sed 's/^/    /' >&2
    exit 1
  fi
  BRANCH="$(git -C "$WT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
  git worktree remove "$WT"
  [ -n "$BRANCH" ] && [ "$BRANCH" != "HEAD" ] && git branch -D "$BRANCH" >/dev/null 2>&1 || true
  echo "removed $NAME"
  exit 0
fi

# ------------------------------------------------------------------ --for-task
#
# Unattended entry point. A scheduled task must never have to judge whose work is
# in the tree — that judgement is what destroyed the Delta Surgical record on
# 26/08/2026, and an unattended run has nobody to ask. So this either hands back a
# clean checkout at origin/main, or it refuses and says why. It never discards.
#
#   WT="$(./wt.sh --for-task supplier-deep-capture)" || { report FAILED; exit; }
#
# Exit 0 = $WT is yours, clean, current. Exit 3 = last run left work behind; the
# task should report FAILED with the message and stop, so a human can look.
if [ "${1:-}" = "--for-task" ]; then
  NAME="${2:-}"; [ -n "$NAME" ] || usage
  WT="$ROOT/$NAME"

  if [ ! -d "$WT" ]; then
    mkdir -p "$ROOT"
    git fetch --quiet origin
    BRANCH="wt/$NAME"
    if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
      git worktree add "$WT" "$BRANCH" >&2
    else
      git worktree add -b "$BRANCH" "$WT" origin/main >&2
    fi
  fi

  git -C "$WT" fetch --quiet origin

  # Same definition of "destroyable work" the Stop guard uses: any tracked change,
  # plus untracked files under data/ or app/ that are not dated backups.
  LEFTOVER="$(git -C "$WT" status --porcelain | awk '
    substr($0,1,2) == "??" {
      p = substr($0,4)
      if (tolower(p) ~ /backup/) next
      if (p !~ /^(data|app)\//) next
      print "    untracked  " p; next
    }
    { print "    " substr($0,1,2) " " substr($0,4) }')"
  if [ -n "$LEFTOVER" ]; then
    echo "REFUSING: $NAME still holds work from a previous run:" >&2
    echo "$LEFTOVER" >&2
    echo "Land it or revert it by hand. This run must not start on top of it, and" >&2
    echo "must not discard it — that is how the Delta Surgical record was lost." >&2
    exit 3
  fi

  AHEAD="$(git -C "$WT" rev-list --count origin/main..HEAD 2>/dev/null || echo 0)"
  if [ "$AHEAD" != "0" ]; then
    echo "REFUSING: $NAME holds $AHEAD commit(s) that never reached origin:" >&2
    git -C "$WT" --no-pager log --oneline origin/main..HEAD | sed 's/^/    /' >&2
    echo "A previous run committed and failed to push. Read them, then land or drop" >&2
    echo "them by hand before this task runs again." >&2
    exit 3
  fi

  # Proven clean and nothing unpushed, so this discards nothing.
  git -C "$WT" reset --quiet --hard origin/main
  echo "$WT"
  exit 0
fi

# ---------------------------------------------------------------------- create
NAME="${1:-}"
[ -n "$NAME" ] || usage
case "$NAME" in
  --*) usage ;;
  *[!A-Za-z0-9._-]*)
    echo "REFUSING: '$NAME' has characters that will break paths." >&2; usage ;;
esac

WT="$ROOT/$NAME"

# Already there: re-entering is the normal case when a session comes back to its
# own work, so say what state it is in rather than treating it as an error.
if [ -d "$WT" ]; then
  echo "reusing existing worktree" >&2
  git -C "$WT" fetch --quiet origin || true
  AHEAD="$(git -C "$WT" rev-list --count origin/main..HEAD 2>/dev/null || echo '?')"
  BEHIND="$(git -C "$WT" rev-list --count HEAD..origin/main 2>/dev/null || echo '?')"
  DIRTY="$(git -C "$WT" status --porcelain --untracked-files=no | wc -l | tr -d ' ')"
  echo "  unpushed commits: $AHEAD   behind origin/main: $BEHIND   uncommitted: $DIRTY" >&2
  echo "$WT"
  exit 0
fi

mkdir -p "$ROOT"
git fetch --quiet origin

# Branch per worktree. Two worktrees cannot check out the same branch, and a
# detached HEAD loses the work if the directory is removed without looking — a
# named branch means `git branch` still shows it and --remove can refuse.
BRANCH="wt/$NAME"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git worktree add "$WT" "$BRANCH" >&2
else
  git worktree add -b "$BRANCH" "$WT" origin/main >&2
fi

echo "" >&2
echo "worktree ready — this checkout is yours alone:" >&2
echo "    cd $WT" >&2
echo "" >&2
echo "Land your work from inside it, naming only your own paths:" >&2
echo "    ./land.sh \"subject\" path [path...]" >&2
echo "" >&2
echo "$WT"
