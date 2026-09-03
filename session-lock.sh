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

LOCK_DIR="$(git rev-parse --git-common-dir)/session.lock"
STAMP="$LOCK_DIR/owner.json"

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
  local pid; pid="$(read_field pid)"
  [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1
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
  mkdir -p "$LOCK_DIR"
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

    waited=0
    while [ -d "$LOCK_DIR" ]; do
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
        break
      fi
      if [ "$FORCE" = "1" ]; then
        echo "note: --force given; taking over from the live holder below:" >&2
        describe_holder >&2
        rm -rf "$LOCK_DIR"
        break
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
