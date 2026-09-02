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
#   ./wt.sh <name> --force    re-enter even if another live session/task owns it
#   ./wt.sh --list            every worktree, with its state and its owner
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
#
# OWNERSHIP STAMP — added 01/09/2026, after ^o159
#   A named worktree is reusable by design ("come back to your own work"), and
#   `--for-task <name>` always resolves to the same `$ROOT/<name>` an interactive
#   session would get from `./wt.sh <name>`. Nothing stopped an interactive session
#   picking the exact name a scheduled task uses and landing in its tree while the
#   task was still running in it — which happened to the differentiator weekend
#   sprint on 31/08/2026: an interactive session rebuilt on top of the task's
#   in-flight edit and both wrote `differentiator.json` within the same 3 minutes.
#
#   Every successful hand-back of a worktree path now writes `.wt-owner.json`
#   inside it (untracked — see .gitignore) recording who holds it: session id,
#   pid, kind (interactive/task), host, timestamp. Every entry checks it first:
#     - stamp absent, or its pid is dead        -> free; take it, restamp
#     - stamp's session id matches this session -> it is yours; restamp
#     - stamp's pid is alive, different session -> REFUSE (exit 3 for --for-task,
#       exit 1 for interactive) and print who holds it, so the collision is a
#       loud refusal instead of a silent double-write
#   `--force` overrides the interactive refusal for the rare case you are certain
#   the other process is actually dead and the stamp just outlived it (e.g. the
#   machine was put to sleep mid-run). There is no `--force` for `--for-task`:
#   an unattended run has nobody to judge that call, so it always just refuses.
set -euo pipefail
cd "$(dirname "$0")"

# ROOT MISMATCH — added 02/09/2026, after the supplier-deep-capture run
#   ROOT is $HOME/msh-worktrees for a normal session. A run whose $HOME is not the
#   one that created the worktrees resolves ROOT to a directory that does not exist,
#   so `[ ! -d "$WT" ]` is true, `git worktree add` runs anyway, and git dies with
#   "fatal: 'wt/<name>' is already checked out at ...". That is exit 128, not exit 3,
#   and it reads like leftover work when in fact the tree is clean and untouched.
#   The supplier-deep-capture run on 02/09/2026 was reported FAILED on that basis.
#   MSH_WORKTREE_ROOT overrides ROOT; the two checks in --for-task below turn the
#   remaining mismatches into a stated exit 3 instead of a misleading git fatal.
ROOT="${MSH_WORKTREE_ROOT:-$HOME/msh-worktrees}"

# registered_worktree BRANCH — where git already holds a worktree for BRANCH, or
# empty. Read from the shared .git, so it is true regardless of what ROOT resolves to.
# No early `exit` in the awk: under `set -o pipefail` that closes the pipe on git
# and the whole function returns 141.
registered_worktree() {
  git worktree list --porcelain | awk -v b="branch refs/heads/$1" '
    /^worktree /{w=substr($0,10)} $0 == b && !f {print w; f=1}'
}

usage() {
  echo "usage: ./wt.sh <name> [--force] | --list | --remove <name>" >&2
  echo "  <name>: letters, digits, dot, dash, underscore. Name it after the work," >&2
  echo "          not after yourself — 'atamis-refresh', not 'session3'." >&2
  exit 2
}

# Who is running this invocation. Claude Code sets these for the life of the
# session (stable across every Bash call in it), unattended task runs get the
# same env since a scheduled task is itself a Claude session. Falls back to the
# raw shell pid so the check still degrades to "is *a* process alive" outside
# Claude Code rather than silently doing nothing.
THIS_SESSION="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_CODE_HOST_SESSION_ID:-}}"
THIS_PID="${CLAUDE_PID:-$$}"
[ -n "$THIS_SESSION" ] || THIS_SESSION="pid-$THIS_PID"

# stamp_owner WT KIND NAME — record that THIS_SESSION/THIS_PID now holds WT.
# Untracked file; a `git reset --hard` on WT does not touch it.
stamp_owner() {
  python3 -c '
import json, os, socket, sys, time
wt, kind, name, sid, pid = sys.argv[1:6]
json.dump({
    "worktree": name, "kind": kind, "session_id": sid, "pid": int(pid),
    "host": socket.gethostname(), "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, open(os.path.join(wt, ".wt-owner.json"), "w"))
' "$1" "$2" "$3" "$THIS_SESSION" "$THIS_PID"
}

# describe_owner WT — one-line summary of the stamp in WT, or "(no stamp)".
describe_owner() {
  [ -f "$1/.wt-owner.json" ] || { echo "(no stamp)"; return 0; }
  python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1] + "/.wt-owner.json"))
except Exception:
    print("(unreadable stamp)"); sys.exit(0)
print("%s  session=%s  pid=%s  host=%s  since=%s" % (
    d.get("kind","?"), d.get("session_id","?"), d.get("pid","?"),
    d.get("host","?"), d.get("started_at","?")))
' "$1"
}

# owner_pid_alive WT — 0 if WT has a stamp AND that pid is still running.
owner_pid_alive() {
  [ -f "$1/.wt-owner.json" ] || return 1
  pid="$(python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1]+"/.wt-owner.json")).get("pid",""))
except Exception: print("")' "$1")"
  [ -n "$pid" ] || return 1
  ps -p "$pid" >/dev/null 2>&1
}

# owner_session WT — the session id in WT's stamp, or empty.
owner_session() {
  [ -f "$1/.wt-owner.json" ] || { echo ""; return 0; }
  python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1]+"/.wt-owner.json")).get("session_id",""))
except Exception: print("")' "$1"
}

# check_owner WT — 0 if WT is free to take (no stamp, stale stamp, or already
# ours), 1 if a different, live session/task holds it. Never destructive by
# itself; callers decide what "1" means for them.
check_owner() {
  local wt="$1" sid
  [ -f "$wt/.wt-owner.json" ] || return 0
  sid="$(owner_session "$wt")"
  [ "$sid" = "$THIS_SESSION" ] && return 0
  owner_pid_alive "$wt" || { echo "note: previous owner's process is gone; taking over" >&2; return 0; }
  return 1
}

# --------------------------------------------------------------------- --list
if [ "${1:-}" = "--list" ]; then
  git worktree list --porcelain | awk '/^worktree /{print $2}' | while read -r w; do
    [ -d "$w" ] || continue
    dirty="$(git -C "$w" status --porcelain 2>/dev/null | grep -vc 'backup' || true)"
    ahead="$(git -C "$w" rev-list --count origin/main..HEAD 2>/dev/null || echo '?')"
    head="$(git -C "$w" log --oneline -1 2>/dev/null || echo '(no commit)')"
    owner="$(describe_owner "$w")"
    live="free"
    owner_pid_alive "$w" && live="LIVE"
    printf '%s\n    unpushed: %s   uncommitted files: %s   owner: [%s] %s\n    %s\n' \
      "$w" "$ahead" "$dirty" "$live" "$owner" "$head"
  done
  exit 0
fi

# ------------------------------------------------------------------- --remove
if [ "${1:-}" = "--remove" ]; then
  NAME="${2:-}"; [ -n "$NAME" ] || usage
  WT="$ROOT/$NAME"
  [ -d "$WT" ] || { echo "no such worktree: $WT" >&2; exit 1; }
  if ! check_owner "$WT"; then
    echo "REFUSING: $NAME is currently held by a live session/task:" >&2
    echo "    $(describe_owner "$WT")" >&2
    echo "Removing it out from under a running process is how work gets lost. Wait" >&2
    echo "for it to finish, or confirm it is actually dead before removing." >&2
    exit 1
  fi
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

  # If git already holds this branch's worktree somewhere other than $WT, ROOT is
  # wrong for this environment. A second one is impossible, and calling it leftover
  # work would be a lie about a tree nobody has touched. Say what it actually is.
  REG="$(registered_worktree "wt/$NAME")"
  if [ -n "$REG" ] && [ "$REG" != "$WT" ]; then
    echo "REFUSING: wt/$NAME is already checked out at" >&2
    echo "    $REG" >&2
    echo "but this environment resolves the worktree root to" >&2
    echo "    $ROOT" >&2
    echo "Nothing is wrong with that tree and it holds no lost work — this run just" >&2
    echo "cannot see it under that name. Set MSH_WORKTREE_ROOT to the directory" >&2
    echo "containing the path above, or run where it resolves, then try again." >&2
    exit 3
  fi

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

  # A worktree records an absolute gitdir. If this environment cannot resolve that
  # path the checkout cannot be driven from here at all, and every git call below
  # would fail one at a time in the middle of a run. Fail once, up front, clearly.
  if ! git -C "$WT" rev-parse --git-dir >/dev/null 2>&1; then
    echo "REFUSING: $WT exists but its gitdir is unreachable from this environment:" >&2
    sed 's/^/    /' "$WT/.git" >&2 2>/dev/null || true
    echo "The checkout is intact and holds no lost work; it simply cannot be driven" >&2
    echo "from here. Run this task where that path resolves." >&2
    exit 3
  fi

  # An unattended run has nobody to ask, so this never overrides a live owner —
  # it refuses exactly like the leftover-work and unpushed-commit checks below.
  if ! check_owner "$WT"; then
    echo "REFUSING: $NAME is currently held by a live session/task:" >&2
    echo "    $(describe_owner "$WT")" >&2
    echo "This run must not start on top of another live writer. Report FAILED and" >&2
    echo "stop; a human should confirm the other run is actually finished." >&2
    exit 3
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
  stamp_owner "$WT" "task" "$NAME"
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
FORCE=0
[ "${2:-}" = "--force" ] && FORCE=1

WT="$ROOT/$NAME"

# Already there: re-entering is the normal case when a session comes back to its
# own work, so say what state it is in rather than treating it as an error.
if [ -d "$WT" ]; then
  echo "reusing existing worktree" >&2
  if ! check_owner "$WT"; then
    if [ "$FORCE" = "1" ]; then
      echo "note: --force given; taking over from the live owner below:" >&2
      echo "    $(describe_owner "$WT")" >&2
    else
      echo "" >&2
      echo "REFUSING: $NAME is currently held by a different live session/task:" >&2
      echo "    $(describe_owner "$WT")" >&2
      echo "Two writers in one worktree is exactly what wt.sh exists to prevent." >&2
      echo "Wait for it, pick a different name for your own work, or re-run with" >&2
      echo "--force if you are certain that run is actually dead." >&2
      exit 1
    fi
  fi
  stamp_owner "$WT" "interactive" "$NAME"
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
stamp_owner "$WT" "interactive" "$NAME"

echo "" >&2
echo "worktree ready — this checkout is yours alone:" >&2
echo "    cd $WT" >&2
echo "" >&2
echo "Land your work from inside it, naming only your own paths:" >&2
echo "    ./land.sh \"subject\" path [path...]" >&2
echo "" >&2
echo "$WT"
