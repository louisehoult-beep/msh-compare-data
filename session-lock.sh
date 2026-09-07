#!/usr/bin/env bash
# session-lock.sh — claim the shared checkout for the length of an editing session.
#
# WHY THIS EXISTS
#   Retires wt.sh (per-session worktrees, 28/08/2026-03/09/2026). Worktrees gave every
#   session its own files so nobody could overwrite another session's uncommitted work
#   mid-edit — see the two incidents `wt.sh` and
#   `Process flows for all brands/_superseded/msh-compare-data-per-session-worktrees-superseded-2026-09-03.md`
#   were built to stop. Lou asked (03/09/2026) to stop using worktrees — 03/09/2026's
#   cleanup found six of them sitting abandoned days after the work in them had landed,
#   nobody having run `./wt.sh --remove`. This gives back the one thing worktrees
#   actually protected — "only one writer touches this tree at a time" — without a
#   second directory per session to create, forget about, and have someone else ask
#   about later.
#
# THE RULE
#   Claim before you start editing `msh-compare-data` in the shared checkout. Release
#   when your work has landed (`./land.sh`). A session that skips this and edits
#   unclaimed is exactly back to the pre-28/08 shared-tree failure mode — nothing stops
#   it at the filesystem level, this is a claim, not a chroot.
#
#     ./session-lock.sh claim "trust-profiles-batch-14"
#     ...edit, run scripts, commit as you go...
#     ./land.sh "Trust profiles batch fourteen" data/prep-config.json
#     ./session-lock.sh release
#
#   `land.sh` checks this lock itself (see its own comments) and refuses to land while
#   a *different* live session holds it, so a session that forgets to claim before
#   editing still cannot land over one that did.
#
# WHAT IT DOES NOT DO
#   It does not stop a second process editing files on disk — it is a claim, checked by
#   convention, not filesystem permissions. It is exactly as strong as everyone actually
#   running `claim` first, same as `land.sh`'s own lock has always been. What it adds
#   over "just be careful" is that `land.sh` enforces it at the one point that matters —
#   nothing reaches `main` while someone else's claim is live.
set -euo pipefail
cd "$(dirname "$0")"

usage() {
  echo "usage: ./session-lock.sh claim <name> [--wait] | release | status" >&2
  echo "  claim <name>   take the lock for the work named <name>. Name it after the" >&2
  echo "                 work, not yourself — 'atamis-refresh', not 'session3'." >&2
  echo "  --wait         if already held by a live session, wait instead of refusing" >&2
  echo "                 (default wait: \$SESSION_LOCK_WAIT seconds, default 600)." >&2
  echo "  release        release the lock — only if this session holds it." >&2
  echo "  status         show who holds it, or 'free'." >&2
  exit 2
}

# ------------------------------------------------------- where the lock lives
# NOT inside .git. This checkout sits on OneDrive, and OneDrive denies the delete
# on a directory it is syncing. On 06/09/2026 a supplier-deep-capture run hit
# "OS-level permission denial on every delete attempt" clearing a stale lock and
# made no changes at all; 05/09/2026 had to clear two stale git locks and a stale
# session lock by hand (^o317). A lock that cannot be released is worse than no
# lock. So it lives outside the synced tree, keyed by the repo it guards so two
# checkouts never share one. MSH_LOCK_ROOT overrides it for a test.
LOCK_ROOT="${MSH_LOCK_ROOT:-$HOME/.claude/msh-locks}"
REPO_KEY="$(git rev-parse --show-toplevel | shasum | awk '{print $1}' | cut -c1-12)"
LOCK_DIR="$LOCK_ROOT/$REPO_KEY/session.lock"
STAMP="$LOCK_DIR/owner.json"

# Only meaningful for a few hours after 07/09/2026: a session that claimed under
# the old in-.git location before this change is invisible to the new path, and
# taking the tree from underneath it is the exact failure this lock exists to
# stop. Checked on claim, never written to.
LEGACY_LOCK_DIR="$(git rev-parse --git-common-dir)/session.lock"

THIS_SESSION="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_CODE_HOST_SESSION_ID:-}}"
THIS_PID="${CLAUDE_PID:-$$}"
[ -n "$THIS_SESSION" ] || THIS_SESSION="pid-$THIS_PID"

read_field() {
  # read_field FIELD — a value out of $STAMP, or "" if absent/unreadable.
  [ -f "$STAMP" ] || { echo ""; return 0; }
  python3 -c '
import json, sys
try:
    print(json.load(open(sys.argv[1])).get(sys.argv[2], ""))
except Exception:
    print("")
' "$STAMP" "$1"
}

holder_pid_alive() {
  # A lock directory with no stamp yet is a claim in flight: the claimer has done
  # its atomic mkdir but has not written owner.json. Absence of proof is not proof
  # of staleness, so report ALIVE and leave it alone — clearing it here would
  # reintroduce, in a smaller window, the very overwrite this lock prevents. A
  # genuinely corrupt stampless lock therefore needs --force, which is correct.
  [ -f "$STAMP" ] || return 0
  local pid; pid="$(read_field pid)"
  [ -n "$pid" ] || return 0
  ps -p "$pid" >/dev/null 2>&1
}

describe_holder() {
  [ -d "$LOCK_DIR" ] || { echo "free"; return 0; }
  [ -f "$STAMP" ] || { echo "held (no stamp — treat as foreign, do not assume it is safe to clear)"; return 0; }
  python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print("held (unreadable stamp)"); sys.exit(0)
print("%s  session=%s  pid=%s  host=%s  since=%s" % (
    d.get("name","?"), d.get("session_id","?"), d.get("pid","?"),
    d.get("host","?"), d.get("started_at","?")))
' "$STAMP"
}

write_stamp() {
  # Does NOT create $LOCK_DIR — the caller has already created it with a bare
  # mkdir, which is the atomic test-and-set. Creating it here too would make that
  # guarantee meaningless.
  python3 -c '
import json, socket, sys, time
name, sid, pid = sys.argv[1:4]
json.dump({
    "name": name, "session_id": sid, "pid": int(pid),
    "host": socket.gethostname(), "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, open(sys.argv[4], "w"))
' "$1" "$THIS_SESSION" "$THIS_PID" "$STAMP"
}

case "${1:-}" in
  status)
    describe_holder
    exit 0
    ;;

  lock-path)
    # Single source of truth for where the claim lives. land.sh asks for it
    # rather than recomputing the path, so the two can never drift apart.
    echo "$LOCK_DIR"
    exit 0
    ;;

  release)
    if [ ! -d "$LOCK_DIR" ]; then
      echo "already free"
      exit 0
    fi
    HOLDER_SESSION="$(read_field session_id)"
    if [ "$HOLDER_SESSION" != "$THIS_SESSION" ]; then
      echo "REFUSING: this lock is not yours to release:" >&2
      describe_holder >&2
      echo "If that session is actually dead, use 'claim <name> --force' instead of" >&2
      echo "releasing someone else's lock blind." >&2
      exit 1
    fi
    rm -rf "$LOCK_DIR"
    echo "released"
    exit 0
    ;;

  claim)
    NAME="${2:-}"; [ -n "$NAME" ] || usage
    WAIT=0; FORCE=0
    for a in "$@"; do
      [ "$a" = "--wait" ] && WAIT=1
      [ "$a" = "--force" ] && FORCE=1
    done
    WAIT_SECONDS="${SESSION_LOCK_WAIT:-600}"

    if [ -d "$LEGACY_LOCK_DIR" ] && [ -f "$LEGACY_LOCK_DIR/owner.json" ]; then
      LEGACY_SESSION="$(python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("session_id",""))
except Exception: print("")' "$LEGACY_LOCK_DIR/owner.json" 2>/dev/null || echo "")"
      LEGACY_PID="$(python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("pid",""))
except Exception: print("")' "$LEGACY_LOCK_DIR/owner.json" 2>/dev/null || echo "")"
      # A legacy lock held by THIS session is the migration case: the session
      # claimed under the old path, then this very change moved the path. It is
      # our own claim, so it blocks nothing.
      [ "$LEGACY_SESSION" = "$THIS_SESSION" ] && LEGACY_PID=""
      if [ -n "$LEGACY_PID" ] && ps -p "$LEGACY_PID" >/dev/null 2>&1; then
        echo "REFUSING: a live session holds the OLD in-.git claim (pre-07/09/2026)." >&2
        echo "  $LEGACY_LOCK_DIR (pid $LEGACY_PID)" >&2
        echo "Wait for it to finish, then claim again. Do not delete that lock by hand" >&2
        echo "while its process is alive." >&2
        exit 1
      fi
    fi

    mkdir -p "$(dirname "$LOCK_DIR")"

    waited=0
    # `mkdir` WITHOUT -p is the whole mutual exclusion: it fails if the directory
    # already exists, so exactly one caller can win. The previous `mkdir -p` in
    # write_stamp always succeeded, which meant two sessions could both fall
    # through this loop and both stamp the lock — the second silently erasing the
    # first's claim (06/09/2026, ^o317). land.sh's own land.lock always used this
    # pattern; this is session.lock catching up.
    while ! mkdir "$LOCK_DIR" 2>/dev/null; do
      HOLDER_SESSION="$(read_field session_id)"
      if [ "$HOLDER_SESSION" = "$THIS_SESSION" ]; then
        echo "already held by this session:"
        describe_holder
        exit 0
      fi
      if ! holder_pid_alive; then
        echo "note: previous holder's process is gone; clearing stale lock:" >&2
        describe_holder >&2
        rm -rf "$LOCK_DIR"
        continue
      fi
      if [ "$FORCE" = "1" ]; then
        echo "note: --force given; taking over from the live holder below:" >&2
        describe_holder >&2
        rm -rf "$LOCK_DIR"
        continue
      fi
      if [ "$WAIT" != "1" ]; then
        echo "REFUSING: the tree is claimed by a live session:" >&2
        describe_holder >&2
        echo "Wait for it to release, or re-run with --wait." >&2
        exit 1
      fi
      if [ "$waited" -eq 0 ]; then
        echo "==> waiting for the tree lock:" >&2
        describe_holder >&2
      fi
      if [ "$waited" -ge "$WAIT_SECONDS" ]; then
        echo "REFUSING: still held after ${WAIT_SECONDS}s:" >&2
        describe_holder >&2
        exit 1
      fi
      sleep 5
      waited=$((waited + 5))
    done

    write_stamp "$NAME"
    echo "claimed: $NAME"
    echo "release with: ./session-lock.sh release"
    exit 0
    ;;

  *)
    usage
    ;;
esac
