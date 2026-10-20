#!/bin/bash
# digital-sources-weekly.sh - LaunchAgent uk.co.elevateandthrive.digital-sources-weekly (added 20/10/2026).
#
# WHY IT RUNS ON THE MAC: digital.nhs.uk (NHS App partner lists, Digital Maturity Assessment)
# answers GitHub's runners with HTTP 403 and england.nhs.uk (Federated Data Platform lists)
# answers them with HTTP 202 and an empty body, so digital-lane.yml cannot refresh these two
# sources. This job reads them from the Mac, in a throwaway clone (never the OneDrive checkout),
# and lands the two data files through land.sh, the repo's single landing lane (fetch, record-
# level no-loss check, rebase, gate, push with retry). No Claude, no allowance used.
#
# RUNS: Monday 07:10 local time, and at load when no successful run in the last 7 days or when
# today is Monday and today has no success yet (a Mac asleep or off on Monday morning catches up
# on wake). `--force` ignores the rule.
#
# Installed by the plist, which pipes this file from the local mirror's main, so a change merged
# to main takes effect on the next run with nothing to copy.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export GIT_TERMINAL_PROMPT=0
LOG="$HOME/Library/Logs/digital-sources-weekly.log"
STATE_DIR="$HOME/.claude/state"
STAMP="$STATE_DIR/digital-sources-weekly.last-success"
ORIGIN_URL="https://github.com/louisehoult-beep/msh-compare-data.git"
MIRROR="${MSH_MIRROR:-$HOME/.claude/msh-mirror/msh-compare-data.git}"
WORK_ROOT="${MSH_WORK_ROOT:-$HOME/.claude/msh-work}"
TODAY="$(date +%F)"
mkdir -p "$STATE_DIR" "$(dirname "$LOG")" "$WORK_ROOT"
exec >>"$LOG" 2>&1
echo "== $(date '+%F %T') digital-sources-weekly start"

if [ "${1:-}" != "--force" ]; then
  last=""; [ -f "$STAMP" ] && last="$(cat "$STAMP")"
  dow="$(date +%u)"
  need=0
  if [ -z "$last" ]; then need=1
  elif [ "$dow" = "1" ] && [ "$last" != "$TODAY" ]; then need=1
  else
    age_days=$(( ( $(date +%s) - $(date -j -f %F "$last" +%s 2>/dev/null || echo 0) ) / 86400 ))
    [ "$age_days" -ge 7 ] && need=1
  fi
  if [ "$need" = "0" ]; then echo "nothing due (last success $last)"; exit 0; fi
fi

# Mirror and throwaway clone, same shape as begin.sh.
if [ ! -d "$MIRROR" ]; then git clone --bare "$ORIGIN_URL" "$MIRROR" || { echo "FAIL: mirror clone"; exit 1; }; fi
git -C "$MIRROR" fetch --quiet origin main:main || { echo "FAIL: mirror fetch"; exit 1; }
DEST="$WORK_ROOT/digital-sources-weekly-$(date +%Y%m%d-%H%M%S)-$$"
git clone --quiet --local --shared "$MIRROR" "$DEST" -b main || { echo "FAIL: clone"; exit 1; }
git -C "$DEST" remote set-url origin "$ORIGIN_URL"
# Identity for the commit land.sh makes; local to this clone only.
git -C "$DEST" config user.name "digital-sources-bot"
git -C "$DEST" config user.email "actions@github.com"
cd "$DEST" || exit 1

fail=0
python3 scripts/refresh_digital_sources.py || { echo "digital sources: not refreshed"; fail=1; }
python3 scripts/refresh_fdp_live.py || { echo "Federated Data Platform: not refreshed"; fail=1; }
python3 scripts/stamp_notice.py || true

if git diff --quiet -- data/digital-sources.json data/trust-digital-profile.json; then
  echo "unchanged: nothing to land"
  rm -rf "$DEST"
  [ "$fail" = "0" ] && echo "$TODAY" > "$STAMP"
  echo "== done (unchanged, fail=$fail)"
  exit "$fail"
fi

if bash ./land.sh "Digital sources and Federated Data Platform profile $TODAY (Mac refresh)" \
     data/digital-sources.json data/trust-digital-profile.json; then
  echo "$TODAY" > "$STAMP"
  echo "== done (landed, fail=$fail)"
  exit "$fail"
fi
echo "FAIL: land.sh refused; clone left at $DEST for inspection (reaped after 4h)"
exit 1
