#!/usr/bin/env bash
# begin.sh — start a piece of work on msh-compare-data in your own throwaway clone.
#
# WHY THIS EXISTS (replaces session-lock.sh + wt.sh + shared_tree_check.py, 08/09/2026)
#   Every session and 6+ scheduled tasks used to edit ONE shared OneDrive checkout.
#   Three real incidents came from that (12/08, 14/08, 18/08, 25/08, 26/08 — see
#   land.sh's own header). The fixes tried since were all forms of taking turns on
#   that one tree: per-session worktrees (retired 03/09/2026, Lou found six
#   abandoned), then a claim/release lock (session-lock.sh) plus a Stop hook that
#   scanned the shared tree on every session's every turn — which kept telling
#   completely unrelated sessions "another task is working" because it was checking
#   a tree they had never touched. Lou called this out 08/09/2026: real, but
#   pointless noise, costing time and tokens on every unrelated task.
#
#   The actual fix is not a better lock. It's not sharing a working tree at all.
#   This script hands you a private, disposable clone in seconds (it shares git
#   objects with a local mirror via --shared, so it costs no meaningful disk or
#   time even on this repo's ~1GB history). Nobody else can ever be mid-edit in
#   your clone, so there is nothing to claim, nothing to check, nothing to be told
#   about. The only remaining contention point is the actual push to GitHub, and
#   git already refuses that atomically if someone else landed first — land.sh
#   handles that by fetching + rebasing + retrying, same as it always has.
#
# USAGE
#   From anywhere:
#     /path/to/msh-compare-data/begin.sh "name-of-the-work"
#   It prints the path to your new clone. cd there, edit, run verify.py, then:
#     ./land.sh "commit subject" path [path...]
#   land.sh deletes your clone itself once it has landed successfully. If you
#   abandon the work instead, just delete the printed directory yourself — or
#   leave it: anything under ~/.claude/msh-work/ older than 4 hours is swept
#   automatically the next time begin.sh runs (see reap_stale below), so nothing
#   accumulates the way the old worktrees did.
#
# WHAT IT DOES NOT DO
#   It is not a lock and does not need to be. It does not touch the shared
#   OneDrive checkout at all — that checkout is now a read-only browsing copy,
#   refreshed by `git pull` when someone wants to look, never edited directly.
set -euo pipefail

ORIGIN_URL="https://github.com/louisehoult-beep/msh-compare-data.git"
MIRROR="${MSH_MIRROR:-$HOME/.claude/msh-mirror/msh-compare-data.git}"
WORK_ROOT="${MSH_WORK_ROOT:-$HOME/.claude/msh-work}"
STALE_HOURS="${MSH_WORK_STALE_HOURS:-4}"

LABEL="${1:-}"
if [ -z "$LABEL" ]; then
  echo "usage: ./begin.sh \"name-of-the-work\"" >&2
  echo "Name it after the work, not yourself — 'trust-profiles-batch-14', not 'session3'." >&2
  exit 2
fi
SAFE_LABEL="$(echo "$LABEL" | tr -c 'A-Za-z0-9._-' '-' | sed 's/-\{2,\}/-/g')"

reap_stale() {
  # Safety net for a session that crashed before land.sh could clean up after
  # itself. Anything this old was abandoned, not in-flight — nothing legitimate
  # runs against this repo for 4+ hours (supplier-deep-capture, the longest, has
  # taken 12h once, but that is the exception logged in its own task description,
  # not the rule; err on the side of a slightly-too-long window over deleting live
  # work). Best-effort: never let a reap failure stop you starting new work.
  [ -d "$WORK_ROOT" ] || return 0
  find "$WORK_ROOT" -maxdepth 1 -mindepth 1 -type d -mmin "+$((STALE_HOURS * 60))" -print 2>/dev/null | while read -r stale; do
    echo "==> clearing stale clone (older than ${STALE_HOURS}h, left over from an" >&2
    echo "    interrupted run): $stale" >&2
    rm -rf "$stale" 2>/dev/null || true
  done
}
reap_stale

mkdir -p "$MIRROR" 2>/dev/null || true
if [ ! -d "$MIRROR" ]; then
  echo "==> no local mirror yet — creating one (one-off, ~1GB, may take a minute)"
  mkdir -p "$(dirname "$MIRROR")"
  git clone --bare "$ORIGIN_URL" "$MIRROR"
fi

echo "==> fetching latest main" >&2
git -C "$MIRROR" fetch --quiet origin main:main

mkdir -p "$WORK_ROOT"
DEST="$WORK_ROOT/${SAFE_LABEL}-$(date +%Y%m%d-%H%M%S)-$$"
git clone --quiet --local --shared "$MIRROR" "$DEST" -b main

# CRITICAL: `git clone <local-path> <dest>` always points the clone's "origin"
# at the local path it was cloned FROM — here, the local mirror — never at the
# mirror's own origin. Left uncorrected, land.sh's "git push origin HEAD:main"
# would push to the local mirror and report LANDED without ever reaching
# GitHub: a silent no-op that never publishes, discovered 08/09/2026 testing
# the very first real land through this script. Every clone's origin must
# point at the real remote, not at the mirror it was cloned from.
git -C "$DEST" remote set-url origin "$ORIGIN_URL"

echo "$DEST"
