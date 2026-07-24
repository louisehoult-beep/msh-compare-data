#!/usr/bin/env python3
"""
verify.py — publish gate for everything this repo serves to the Medical Sales Hub.

WHY THIS EXISTS
---------------
On 24/07/2026 the Stakeholder Mapper's "recent changes in who is named" panel
went live telling members about 145 job changes at named NHS trusts. All 145
were false. Moves were detected by diffing the contact index before and after a
run, which assumes runs walk forward in time; the backfill walked backwards, so
every earlier month's names were logged as having "replaced" people they
actually preceded — Paul Greenwood, first seen 30/06, recorded as replacing
Hannah Dimmick, last seen 24/07.

The check that would have caught it is one line: a person cannot replace
somebody who was still signing notices three weeks later. It was never written,
because this repo had no gate — unlike cloud-pipeline, which has hub_verify.py
and a standing rule that nothing sends until it passes.

The same day, data/trust-contacts.json and data/people-moves.json — real named
NHS staff and their work emails — were published by accident, swept into a
commit by `git add -A` before anyone had decided they should be public.

So: nothing in this repo reaches the Hub until this script exits 0.

WHAT IT CHECKS
--------------
1. MOVES         every claimed handover must be chronologically possible, and
                 clear the gap the file itself declares. This is the incident.
2. CONTACTS      dates sane, retention honoured, opt-outs absent, trusts real,
                 names look like people rather than departments.
3. TRUST MAP     size, unique ODS codes, ICB codes from the current 36, and
                 the ICB name matching the code it is paired with.
4. CONSENT GATE  if named personal data is present, the LIVE privacy notice
                 must carry its Article 14 section and the SAME retention
                 period the code enforces. Personal data cannot outrun its
                 own notice.
5. JAVASCRIPT    every app/*.js parses. A syntax error here takes out the whole
                 Med Sales Tools page, not one panel.
6. SHRINK        datasets may not silently collapse against what is committed.

Usage
    python3 verify.py            # full run, including the live privacy check
    python3 verify.py --offline  # skip network checks (still fails on logic)
    python3 verify.py --json

Exit codes
    0  passed — safe to push
    1  FAILED — do not push until every FAIL is resolved
"""

import json, os, re, subprocess, sys, datetime, shutil
from urllib.request import Request, urlopen

DATA = "data"
PRIVACY_URL = "https://elevateandthrive.uk/privacy-policy/"
PRIVACY_MARKER = "NHS Contact Information in the Medical Sales Hub"
UA = {"User-Agent": "Mozilla/5.0 (msh-compare-data verify)"}

# The 36 ICBs effective 01/04/2026. Kept in step with scripts/refresh_trusts.py.
ICB_CODES = {
    'QOQ','QHM','QF7','QWO','QYG','QOP','QE1','QHL','QUA','QWU','QJ2','QGH',
    'QK1','QJM','QPM','QT1','QOC','QNC','S1Y5D','D7T5G','T6Y0W','QMF','QKK',
    'QWE','Z9B2Z','QRL','QKS','S9B9J','S0E4D','QOX','QUY','QT6','QJK','QVV',
    'QR1','QSL',
}
KINDS = {None, 'Ambulance service', 'Mental health', 'Community'}
DEPARTMENTAL = re.compile(
    r"\b(team|dept|department|office|procurement|purchasing|supplies|supply|"
    r"contracts?|commercial|admin|helpdesk|mailbox|enquir|info|general|shared|"
    r"group|services?|unit|division|directorate|noreply)\b", re.I)

fails, warns = [], []
def FAIL(check, msg): fails.append((check, msg))
def WARN(check, msg): warns.append((check, msg))


def load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def committed(path):
    """The version of a file currently on main, for shrink comparison."""
    try:
        out = subprocess.run(["git", "show", "HEAD:" + path],
                             capture_output=True, text=True, timeout=30)
        return json.loads(out.stdout) if out.returncode == 0 else None
    except Exception:
        return None


def today():
    return datetime.date.today()


def as_date(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


# --------------------------------------------------------------------------
# 1. MOVES — the incident check
# --------------------------------------------------------------------------
def check_moves(moves, trust_codes, blocked, contacts):
    if moves is None:
        return
    rows = moves.get("moves", [])
    gap = int(moves.get("gapDays") or 0)
    min_notices = int(moves.get("minNotices") or 0)
    # A moves file must DECLARE every rule it was generated under. Anything
    # missing means it came from an older generator, and the checks below would
    # silently skip rather than fail — which is how the Lancashire false
    # handover came back after being fixed: a background backfill rewrote the
    # file with pre-fix code and the gate waved it through. Fail closed.
    if rows:
        for flag in ("gapDays", "minNotices", "minSpanDays", "singleThreadedOnly"):
            if moves.get(flag) in (None, ""):
                FAIL("moves", "people-moves.json does not declare %r. It was written by an older "
                              "generator than the one in scripts/, so the rules it claims cannot be "
                              "checked. Re-run: python3 scripts/refresh_fts_contacts.py "
                              "--rebuild-moves" % flag)
    if rows and min_notices < 2:
        FAIL("moves", "people-moves.json declares minNotices=%s. Below 2, a single notice becomes "
                      "a claimed job change — do not publish moves on that basis." % min_notices)
    if gap <= 0:
        FAIL("moves", "people-moves.json declares no gapDays — the rule a reader "
                      "is being asked to trust must be stated in the file.")
    impossible = chrono = 0
    for m in rows:
        first, prev_last = as_date(m.get("firstSeen")), as_date(m.get("replacesLastSeen"))
        if not first:
            FAIL("moves", "move for %r has no usable firstSeen" % m.get("name")); continue
        if first > today():
            FAIL("moves", "move for %r is dated in the future (%s)" % (m.get("name"), first))
        if m.get("replaces") and not prev_last:
            FAIL("moves", "move for %r claims to replace %r with no date for that person"
                          % (m.get("name"), m.get("replaces")))
            continue
        if prev_last:
            # THE INCIDENT: you cannot take over from somebody who was still there.
            if first <= prev_last:
                impossible += 1
                if impossible <= 5:
                    FAIL("moves", "IMPOSSIBLE HANDOVER — %r first seen %s but is recorded as "
                                  "replacing %r, last seen %s. A person cannot replace someone "
                                  "who came after them."
                                  % (m.get("name"), first, m.get("replaces"), prev_last))
            elif gap and (first - prev_last).days < gap:
                chrono += 1
                if chrono <= 5:
                    FAIL("moves", "GAP TOO SHORT — %r appeared %d days after %r was last seen, "
                                  "below the %d-day rule this file declares."
                                  % (m.get("name"), (first - prev_last).days, m.get("replaces"), gap))
        if m.get("trust") and trust_codes and m["trust"] not in trust_codes:
            FAIL("moves", "move for %r is attached to trust code %r, which is not in "
                          "trust-map.json" % (m.get("name"), m["trust"]))
        if (m.get("name") or "").strip().lower() in blocked:
            FAIL("moves", "%r has opted out but still appears in people-moves.json" % m.get("name"))

        # CONCURRENT BUYERS. A trust where two contacts were active at the same
        # time has more than one buyer, so a new name cannot be read as taking
        # over from anyone. Lancashire and South Cumbria passed the gap rule and
        # the evidence floor and was still wrong on exactly this.
        if contacts:
            ent = sorted(contacts.get(m.get("trust"), []), key=lambda e: e["first"])
            for a_i in range(len(ent)):
                clash = None
                for b_i in range(a_i + 1, len(ent)):
                    a, b = ent[a_i], ent[b_i]
                    if a["last"] >= b["first"] and b["last"] >= a["first"]:
                        clash = (a["name"], b["name"]); break
                if clash:
                    FAIL("moves", "CONCURRENT BUYERS — trust %r has %r and %r active at the same "
                                  "time, so the move claimed for %r is not a handover, it is a "
                                  "trust with more than one buyer."
                                  % (m.get("trust"), clash[0], clash[1], m.get("name")))
                    break

        # EVIDENCE FLOOR. A name on a single notice is a data point, not a
        # post-holder. The first two moves that cleared the 60-day rule were
        # both one-notice-each at large trusts — i.e. two different buyers, not
        # a handover. Telling a rep someone changed role on that basis is the
        # same failure as the 145, just quieter.
        if contacts:
            held = {e["name"].lower(): e for e in contacts.get(m.get("trust"), [])}
            for who, label in ((m.get("name"), "new name"), (m.get("replaces"), "predecessor")):
                if not who:
                    continue
                e = held.get(who.lower())
                if e is None:
                    # Every claim about a person must be traceable to the index it
                    # was derived from. A name that is not there is unsourced, and
                    # unsourced is worse than thin.
                    FAIL("moves", "UNSOURCED — %s %r is not in the contact index for trust %r. "
                                  "A published claim about a named person must be traceable to "
                                  "the notices it came from."
                                  % (label, who, m.get("trust")))
                    continue
                if e.get("n", 1) < min_notices:
                    FAIL("moves", "THIN EVIDENCE — %s %r appears on only %d notice(s). One notice "
                                  "is a data point, not a post-holder; this is a trust with more "
                                  "than one buyer, not a handover."
                                  % (label, who, e.get("n", 1)))
    if impossible > 5:
        FAIL("moves", "...and %d further impossible handovers (suppressed)" % (impossible - 5))
    if chrono > 5:
        FAIL("moves", "...and %d further sub-gap handovers (suppressed)" % (chrono - 5))

    # Plausibility. Real procurement handovers are uncommon; a burst means the
    # detection has broken again, in some new way this script does not yet name.
    if trust_codes and rows:
        share = len({m.get("trust") for m in rows}) / max(len(trust_codes), 1)
        if share > 0.20:
            FAIL("moves", "%d moves across %.0f%% of all trusts — implausible. Real handovers "
                          "are rare; this is what a broken detector looks like."
                          % (len(rows), share * 100))


# --------------------------------------------------------------------------
# 2. CONTACTS
# --------------------------------------------------------------------------
def check_contacts(store, trust_codes, blocked, retention_months):
    if store is None:
        return
    trusts = store.get("trusts", {})
    cutoff = today() - datetime.timedelta(days=int(retention_months * 30.44)) if retention_months else None
    n = 0
    for code, entries in trusts.items():
        if trust_codes and code not in trust_codes:
            FAIL("contacts", "contacts filed under trust code %r, which is not in trust-map.json" % code)
        for e in entries:
            n += 1
            nm = (e.get("name") or "").strip()
            first, last = as_date(e.get("first")), as_date(e.get("last"))
            if not nm or " " not in nm:
                FAIL("contacts", "%r under %s does not look like a person's name" % (nm, code))
            if DEPARTMENTAL.search(nm):
                FAIL("contacts", "%r under %s looks like a department, not a person — a rep would "
                                 "address a desk by name" % (nm, code))
            if nm.lower() in blocked:
                FAIL("contacts", "%r has opted out but is still in the contact index" % nm)
            if not first or not last:
                FAIL("contacts", "%r under %s has unusable dates" % (nm, code)); continue
            if first > last:
                FAIL("contacts", "%r under %s: first seen %s is after last seen %s" % (nm, code, first, last))
            if last > today():
                FAIL("contacts", "%r under %s is dated in the future (%s)" % (nm, code, last))
            if cutoff and last < cutoff:
                FAIL("contacts", "%r under %s was last seen %s, past the %d-month retention this "
                                 "repo publishes. Retention is enforced on every run — if this "
                                 "fires, it stopped working." % (nm, code, last, retention_months))
            em = (e.get("email") or "").strip()
            if em and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em):
                FAIL("contacts", "%r under %s has a malformed email %r" % (nm, code, em))
    if n and store.get("contactsTotal") not in (None, n):
        WARN("contacts", "contactsTotal says %s, actual count is %d" % (store.get("contactsTotal"), n))
    return n


# --------------------------------------------------------------------------
# 3. TRUST MAP
# --------------------------------------------------------------------------
def check_trust_map(tm):
    if tm is None:
        FAIL("trustmap", "data/trust-map.json is missing — the trust picker cannot work without it.")
        return set()
    trusts = tm.get("trusts", [])
    if len(trusts) < 180:
        FAIL("trustmap", "only %d trusts — expected ~200. Refusing a shrunken directory." % len(trusts))
    codes = [t.get("code") for t in trusts]
    dupes = {c for c in codes if codes.count(c) > 1}
    if dupes:
        FAIL("trustmap", "duplicate ODS codes: %s" % ", ".join(sorted(dupes)[:8]))
    for t in trusts:
        if t.get("kind") not in KINDS:
            FAIL("trustmap", "%s has kind %r, which is not one the UI knows how to group"
                             % (t.get("n"), t.get("kind")))
        if t.get("nation") == "England":
            if t.get("icb") not in ICB_CODES:
                FAIL("trustmap", "%s has ICB code %r, not one of the 36 effective 01/04/2026. "
                                 "If the April 2027 round has landed, update ICB_CODES here AND "
                                 "in scripts/refresh_trusts.py together."
                                 % (t.get("n"), t.get("icb")))
            if not t.get("icbName"):
                FAIL("trustmap", "%s has an ICB code but no ICB name" % t.get("n"))
        elif t.get("icb"):
            FAIL("trustmap", "%s is tagged %s but carries an ICB code" % (t.get("n"), t.get("nation")))
    return set(codes)


# --------------------------------------------------------------------------
# 4. CONSENT GATE — personal data may not outrun its own privacy notice
# --------------------------------------------------------------------------
def check_privacy(contact_count, retention_months, offline):
    if not contact_count:
        return
    if offline:
        WARN("privacy", "skipped the live privacy-notice check (--offline). Do not push on this.")
        return
    try:
        html = urlopen(Request(PRIVACY_URL, headers=UA), timeout=30).read().decode("utf-8", "replace")
    except Exception as e:
        FAIL("privacy", "could not read %s (%s). %d named people are in this repo and the gate "
                        "cannot confirm their privacy notice is live — treat as a failure, not a "
                        "network blip." % (PRIVACY_URL, e, contact_count))
        return
    if PRIVACY_MARKER not in html:
        FAIL("privacy", "%d named NHS contacts are about to be published, but the live privacy "
                        "notice has no %r section. Article 14 information must be up BEFORE the "
                        "data is." % (contact_count, PRIVACY_MARKER))
        return
    if retention_months:
        if not re.search(r"more than\s+%d\s+months" % retention_months, html):
            FAIL("privacy", "the code enforces %d-month retention but the published privacy notice "
                            "does not state that figure. The promise and the behaviour must match."
                            % retention_months)


# --------------------------------------------------------------------------
# 5. JAVASCRIPT
# --------------------------------------------------------------------------
JSC = "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc"

def check_js():
    runner = None
    if shutil.which("node"):
        runner = "node"
    elif os.path.exists(JSC):
        runner = "jsc"
    if not runner:
        WARN("js", "no JavaScript engine available — app/*.js not syntax-checked.")
        return
    for fn in sorted(os.listdir("app")):
        if not fn.endswith(".js"):
            continue
        path = os.path.join("app", fn)
        if runner == "node":
            r = subprocess.run(["node", "--check", path], capture_output=True, text=True, timeout=60)
            ok, err = r.returncode == 0, (r.stderr or "").strip().split("\n")[0]
        else:
            script = ("try{new Function(read(%r));print('OK');}"
                      "catch(e){print('ERR '+e);}" % os.path.abspath(path))
            tmp = "/tmp/_verify_js.js"
            open(tmp, "w").write(script)
            r = subprocess.run([JSC, tmp], capture_output=True, text=True, timeout=60)
            out = (r.stdout or "").strip()
            ok, err = out.startswith("OK"), out
        if not ok:
            FAIL("js", "%s does not parse (%s). This breaks the entire Med Sales Tools page, "
                       "not one panel." % (path, err))


# --------------------------------------------------------------------------
# 6. SHRINK GUARD
# --------------------------------------------------------------------------
def check_shrink():
    for path, count in (("data/trust-map.json", lambda d: len(d.get("trusts", []))),
                        ("data/trust-contacts.json",
                         lambda d: sum(len(v) for v in d.get("trusts", {}).values()))):
        if not os.path.exists(path):
            continue
        old = committed(path)
        if not old:
            continue
        with open(path) as f:
            new = json.load(f)
        o, n = count(old), count(new)
        if o and n < o * 0.9:
            FAIL("shrink", "%s drops from %d to %d (-%.0f%%). Say why in the commit message and "
                           "override deliberately, or find out what broke."
                           % (path, o, n, (1 - n / o) * 100))


def main():
    offline = "--offline" in sys.argv
    as_json = "--json" in sys.argv
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    optout = load("contacts-optout.json") or {}
    blocked = {n.strip().lower() for n in optout.get("names", []) if n.strip()}

    # Retention is read from the code, so the gate checks what actually runs.
    retention = None
    try:
        src = open("scripts/refresh_fts_contacts.py").read()
        m = re.search(r"^RETENTION_MONTHS\s*=\s*(\d+)", src, re.M)
        retention = int(m.group(1)) if m else None
    except Exception:
        pass
    if retention is None:
        WARN("contacts", "could not read RETENTION_MONTHS from the harvester.")

    trust_codes = check_trust_map(load("trust-map.json"))
    n = check_contacts(load("trust-contacts.json"), trust_codes, blocked, retention) or 0
    check_moves(load("people-moves.json"), trust_codes, blocked,
                (load("trust-contacts.json") or {}).get("trusts", {}))
    check_privacy(n, retention, offline)
    check_js()
    check_shrink()

    if as_json:
        print(json.dumps({"pass": not fails, "fails": fails, "warns": warns}, indent=1))
    else:
        for c, m in warns:
            print("WARN  [%s] %s" % (c, m))
        for c, m in fails:
            print("FAIL  [%s] %s" % (c, m))
        print()
        if fails:
            print("VERIFY FAILED — %d failure(s), %d warning(s). Do not push." % (len(fails), len(warns)))
        else:
            print("VERIFY PASSED — %d warning(s)." % len(warns))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
