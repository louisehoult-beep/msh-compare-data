#!/bin/zsh
# Company Report render harness — headless runner.
#
#   ./run.sh                        # tests app/company-report.js as committed
#   ./run.sh ../../some-build.js    # tests any candidate build
#
# Serves the repo root, drives the harness in headless Chrome at a REAL
# 1400px viewport, prints the JSON result and exits 1 on any failure.
#
# The viewport matters. The renderer has a phone breakpoint at max-width:640px
# that respaces .mcr-card from 22px 24px to 16px, and some embedded browser
# panes report innerWidth 0, which makes every media query resolve to the
# narrowest rule. A run that does not fix the width tests the phone rule while
# claiming to test the desktop one. The harness declares which breakpoint it
# measured; this runner makes sure that answer is "desktop".
set -e
SRC="${1:-../../app/company-report.js}"
PORT="${PORT:-8931}"
HERE="${0:A:h}"
ROOT="${HERE:h:h}"          # repo root: tests/company-report -> tests -> repo
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE="$(mktemp -d)"
OUT="$(mktemp)"

SERVER_PID=""
if ! curl -sf -o /dev/null "http://127.0.0.1:$PORT/tests/company-report/test_company_report.html"; then
  (cd "$ROOT" && python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1) &
  SERVER_PID=$!
  sleep 2
fi
cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null
  rm -rf "$PROFILE" "$OUT"
}
trap cleanup EXIT

# Chrome is started in the background and killed as soon as the harness has
# written its result. --dump-dom flushes the DOM once the page settles, but the
# process itself can linger well past that, so waiting on it would hang.
"$CHROME" --headless=new --disable-gpu --no-first-run --no-default-browser-check \
  --user-data-dir="$PROFILE" --window-size=1400,1000 --virtual-time-budget=30000 \
  --dump-dom "http://127.0.0.1:$PORT/tests/company-report/test_company_report.html?src=$SRC" \
  >"$OUT" 2>/dev/null &
CHROME_PID=$!
for i in {1..60}; do
  grep -q 'HARNESS_RESULT_JSON:{' "$OUT" 2>/dev/null && break
  kill -0 "$CHROME_PID" 2>/dev/null || break
  sleep 2
done
kill "$CHROME_PID" 2>/dev/null || true
pkill -f "$PROFILE" 2>/dev/null || true

python3 - "$OUT" <<'PY'
import re, json, sys, io
h = io.open(sys.argv[1], encoding='utf-8', errors='replace').read()
m = re.findall(r'HARNESS_RESULT_JSON:(\{.*?\}):END', h, re.S)
if not m:
    print('HARNESS DID NOT COMPLETE — no result written. The renderer may have thrown on load.')
    sys.exit(2)
d = json.loads(m[0])
print(json.dumps(d, indent=1))
print('')
print('renderer  : %s' % d['renderer'])
print('breakpoint: %s' % d['breakpoint'])
print('pass %d  fail %d  skipped %d' % (d['pass'], d['fail'], d['skip']))
for f in d['failures']:
    print('  FAIL  %s' % f)
sys.exit(1 if d['fail'] else 0)
PY
