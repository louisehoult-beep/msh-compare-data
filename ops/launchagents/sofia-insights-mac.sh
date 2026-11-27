#!/bin/bash
# sofia-insights-mac.sh - LaunchAgent uk.co.elevateandthrive.sofia-insights-mac (added 27/11/2026).
#
# WHY IT RUNS ON THE MAC: www.england.nhs.uk answers GitHub's runners with HTTP 202 and an empty
# body (run 45999313239), so sofia-insights.yml cannot verify the items that cite it and holds
# them. This job runs the same refresh from the Mac, in a throwaway clone (never the OneDrive
# checkout), passes the same Sofia gate and lands through land.sh. If this Mac cannot read a
# source either, nothing is landed. No Claude, no allowance used.
#
# RUNS: 07:20, 09:30 and 13:00 local, and at load; each exits at once after the day's first
# success. A Mac asleep all day means those items do not show that day (nothing stale shows).
# `--force` ignores the day stamp.
#
# Installed by the plist, which pipes this file from the local mirror's main.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export GIT_TERMINAL_PROMPT=0
LOG="$HOME/Library/Logs/sofia-insights-mac.log"
STATE_DIR="$HOME/.claude/state"
STAMP="$STATE_DIR/sofia-insights-mac.last-success"
ORIGIN_URL="https://github.com/louisehoult-beep/msh-compare-data.git"
MIRROR="${MSH_MIRROR:-$HOME/.claude/msh-mirror/msh-compare-data.git}"
WORK_ROOT="${MSH_WORK_ROOT:-$HOME/.claude/msh-work}"
TODAY="$(TZ=Europe/London date +%F)"
DATA=data/sofia-insights.json
HELD=state/sofia-held.json
mkdir -p "$STATE_DIR" "$(dirname "$LOG")" "$WORK_ROOT"
exec >>"$LOG" 2>&1
echo "== $(date '+%F %T') sofia-insights-mac start"

if [ "${1:-}" != "--force" ] && [ "$(cat "$STAMP" 2>/dev/null)" = "$TODAY" ]; then
  echo "already done today"; exit 0
fi

if [ ! -d "$MIRROR" ]; then git clone --bare "$ORIGIN_URL" "$MIRROR" || { echo "FAIL: mirror clone"; exit 1; }; fi
git -C "$MIRROR" fetch --quiet origin main:main || { echo "FAIL: mirror fetch"; exit 1; }
DEST="$WORK_ROOT/sofia-insights-mac-$(date +%Y%m%d-%H%M%S)-$$"
git clone --quiet --local --shared "$MIRROR" "$DEST" -b main || { echo "FAIL: clone"; exit 1; }
git -C "$DEST" remote set-url origin "$ORIGIN_URL"
git -C "$DEST" config user.name "sofia-insights-bot"
git -C "$DEST" config user.email "actions@github.com"
cd "$DEST" || exit 1

python3 scripts/refresh_sofia_insights.py || { echo "FAIL: refresh"; exit 1; }
if grep -q 'not readable from this machine' "$HELD"; then
  echo "FAIL: this Mac could not read a source either: nothing landed"; exit 1
fi
python3 scripts/check_sofia_insights.py || { echo "FAIL: Sofia gate"; exit 1; }

# Same items as already live (only the check time moved): nothing to land.
if python3 - "$DATA" <<'PY'
import json, subprocess, sys
new = json.load(open(sys.argv[1]))
old = json.loads(subprocess.run(['git', 'show', 'HEAD:' + sys.argv[1]], capture_output=True, text=True, check=True).stdout)
sys.exit(0 if (old['dataAsOf'], old['items']) == (new['dataAsOf'], new['items']) else 1)
PY
then
  echo "$TODAY" > "$STAMP"; rm -rf "$DEST"; echo "== done (already live)"; exit 0
fi

# The file is rebuilt daily, so an item that no longer verifies or has aged out is meant to go.
# Each one is named here and passed to the no-loss check by id.
ALLOW=()
while IFS= read -r id; do
  [ -n "$id" ] || continue
  echo "dropped since the live file: $id"
  ALLOW+=(--allow "$id")
done < <(python3 - "$DATA" <<'PY'
import json, subprocess, sys
new = {i['id'] for i in json.load(open(sys.argv[1]))['items']}
old = json.loads(subprocess.run(['git', 'show', 'HEAD:' + sys.argv[1]], capture_output=True, text=True, check=True).stdout)
print('\n'.join(i['id'] for i in old['items'] if i['id'] not in new))
PY
)

python3 scripts/stamp_notice.py || { echo "FAIL: stamp"; exit 1; }
git diff --name-only | grep -vxE "$DATA|$HELD" | while IFS= read -r f; do git checkout -q -- "$f"; done

if bash ./land.sh "Sofia insights $TODAY (Mac read)" ${ALLOW[@]+"${ALLOW[@]}"} "$DATA" "$HELD"; then
  echo "$TODAY" > "$STAMP"; echo "== done (landed)"; exit 0
fi
echo "FAIL: land.sh refused; clone left at $DEST for inspection (reaped after 4h)"
exit 1
