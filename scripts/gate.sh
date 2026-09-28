#!/usr/bin/env bash
# gate.sh — prune aged calendar rows, then run the publish gate.
#
# WHY (^o221, 28/09/2026). calendar-prune.yml is cron'd for 01:50 UTC but GitHub
# starts it anywhere from 06:47 to 13:23, hours AFTER supplier-capture (02:20)
# and the other overnight writers. So a row that aged past midnight failed every
# writer's verify.py before the prune ever ran. Pruning inside each writer, right
# before its own gate, means timing can no longer race: whichever job runs first
# cleans the calendar for itself. calendar-prune.yml stays as the backstop that
# commits the prune on a quiet day.
#
# prune_calendar.py only removes what verify.py would reject (same rules as
# calendar_build.py) and refuses a prune that would gut the file, so this cannot
# hide a real problem: a refusal fails the gate exactly as before.
#
#   bash scripts/gate.sh [verify.py args...]
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/prune_calendar.py
exec python3 verify.py "$@"
