#!/bin/bash
# personal-alerts-shadow.sh - LaunchAgent uk.co.elevateandthrive.personal-alerts-shadow (added 04/11/2026).
#
# Scores the personal Monday briefing and phone triggers on made-up profiles. Sends nothing, reads
# no member data, commits nothing. The scorecard goes to OneDrive, never to this public repo.
#
# RUNS: Monday 06:50, and at load when no success in the last 7 days or today is Monday with none
# today (a Mac asleep on Monday catches up on wake). `--force` ignores the rule. Read from the
# local mirror's main by the plist, so a change merged to main takes effect on the next run.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export GIT_TERMINAL_PROMPT=0
LOG="$HOME/Library/Logs/personal-alerts-shadow.log"
STAMP="$HOME/.claude/state/personal-alerts-shadow.last-success"
ORIGIN_URL="https://github.com/louisehoult-beep/msh-compare-data.git"
MIRROR="${MSH_MIRROR:-$HOME/.claude/msh-mirror/msh-compare-data.git}"
WORK_ROOT="${MSH_WORK_ROOT:-$HOME/.claude/msh-work}"
OUT="$HOME/Library/CloudStorage/OneDrive-Personal/Cowork-OS/02-Elevate-and-Thrive/Hub/Personal-Alerts-Shadow"
TODAY="$(date +%F)"
mkdir -p "$(dirname "$STAMP")" "$(dirname "$LOG")" "$WORK_ROOT" "$OUT"
exec >>"$LOG" 2>&1
echo "== $(date '+%F %T') personal-alerts-shadow start"

if [ "${1:-}" != "--force" ]; then
  last=""; [ -f "$STAMP" ] && last="$(cat "$STAMP")"
  need=0
  if [ -z "$last" ]; then need=1
  elif [ "$(date +%u)" = "1" ] && [ "$last" != "$TODAY" ]; then need=1
  else
    age_days=$(( ( $(date +%s) - $(date -j -f %F "$last" +%s 2>/dev/null || echo 0) ) / 86400 ))
    [ "$age_days" -ge 7 ] && need=1
  fi
  if [ "$need" = "0" ]; then echo "nothing due (last success $last)"; exit 0; fi
fi

if [ ! -d "$MIRROR" ]; then git clone --bare "$ORIGIN_URL" "$MIRROR" || { echo "FAIL: mirror clone"; exit 1; }; fi
git -C "$MIRROR" fetch --quiet origin main:main || { echo "FAIL: mirror fetch"; exit 1; }
DEST="$WORK_ROOT/personal-alerts-shadow-$(date +%Y%m%d-%H%M%S)-$$"
git clone --quiet --local --shared "$MIRROR" "$DEST" -b main || { echo "FAIL: clone"; exit 1; }
cd "$DEST" || exit 1

python3 scripts/personal_alerts_shadow.py --today "$TODAY" --out "$OUT" --check-links 25
rc=$?
cd "$HOME" && rm -rf "$DEST"
if [ "$rc" = "0" ]; then echo "$TODAY" > "$STAMP"; fi
echo "== done (rc=$rc)"
exit "$rc"
