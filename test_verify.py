#!/usr/bin/env python3
"""
test_verify.py — proves the publish gate still catches what it was built for.

A gate nobody tests is a gate that quietly stops working. Each case below is a
state this repo has actually been in, or one line away from. Case 1 is the real
incident, replayed from git history rather than mocked up.

    python3 test_verify.py

Exit 0 = the gate holds. Exit 1 = the gate has a hole; do not trust a green
verify.py until this passes again.
"""
import json, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)

# The commit that published 145 false job changes to the Hub, 24/07/2026.
INCIDENT_COMMIT = "dcdd9eb"
FILES = ["data/people-moves.json", "data/trust-contacts.json", "app/mst-logic.js"]


def gate():
    """Run verify.py offline. Returns (exit_code, output)."""
    r = subprocess.run([sys.executable, "verify.py", "--offline"],
                       capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


def moves(**over):
    d = json.load(open("data/people-moves.json"))
    d.update(over)
    return d


def contacts():
    return json.load(open("data/trust-contacts.json"))["trusts"]


def pick(n_notices, count=2):
    """A trust with `count` contacts each seen on exactly n_notices notices."""
    for code, v in contacts().items():
        hits = [e for e in v if e.get("n", 1) == n_notices]
        if len(hits) >= count:
            return code, hits[:count]
    return None, []


CASES = []
def case(name):
    def deco(fn):
        CASES.append((name, fn)); return fn
    return deco


@case("the 145 false job changes that went live (replayed from git)")
def _(tmp):
    out = subprocess.run(["git", "show", "%s:data/people-moves.json" % INCIDENT_COMMIT],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None                      # history unavailable; skip rather than false-pass
    open("data/people-moves.json", "w").write(out.stdout)
    return "IMPOSSIBLE HANDOVER"


@case("a handover claimed about people who are not in the contact index")
def _(tmp):
    d = moves(moves=[{"trust": "RWD", "name": "A Person", "email": "a@nhs.net",
                      "firstSeen": "2026-07-01", "replaces": "B Person",
                      "replacesLastSeen": "2026-05-01", "notice": "x", "ocid": "y"}])
    json.dump(d, open("data/people-moves.json", "w"))
    return "UNSOURCED"


@case("a handover built on contacts seen on a single notice each")
def _(tmp):
    code, two = pick(1, 2)
    if not code:
        return None
    d = moves(moves=[{"trust": code, "name": two[0]["name"], "email": "",
                      "firstSeen": "2026-07-20", "replaces": two[1]["name"],
                      "replacesLastSeen": "2026-05-01", "notice": "x", "ocid": "y"}])
    json.dump(d, open("data/people-moves.json", "w"))
    return "THIN EVIDENCE"


@case("a move dated in the future")
def _(tmp):
    d = moves(moves=[{"trust": "RWD", "name": "A Person", "email": "",
                      "firstSeen": "2099-01-01", "replaces": None,
                      "replacesLastSeen": None, "notice": "", "ocid": ""}])
    json.dump(d, open("data/people-moves.json", "w"))
    return "future"


@case("minNotices quietly lowered to 1")
def _(tmp):
    code, two = pick(1, 2)
    if not code:
        return None
    d = moves(minNotices=1,
              moves=[{"trust": code, "name": two[0]["name"], "email": "",
                      "firstSeen": "2026-07-20", "replaces": two[1]["name"],
                      "replacesLastSeen": "2026-05-01", "notice": "x", "ocid": "y"}])
    json.dump(d, open("data/people-moves.json", "w"))
    return "minNotices"


@case("a moves file from an older generator that does not declare its rules")
def _(tmp):
    d = json.load(open("data/people-moves.json"))
    code, two = pick(1, 2)
    if not code:
        return None
    d.pop("singleThreadedOnly", None)          # what an older generator wrote
    d["moves"] = [{"trust": code, "name": two[0]["name"], "email": "",
                   "firstSeen": "2026-07-20", "replaces": two[1]["name"],
                   "replacesLastSeen": "2026-05-01", "notice": "x", "ocid": "y"}]
    json.dump(d, open("data/people-moves.json", "w"))
    return "does not declare"


@case("a contact kept past the published retention period")
def _(tmp):
    d = json.load(open("data/trust-contacts.json"))
    code = list(d["trusts"])[0]
    d["trusts"][code][0]["last"] = "2019-01-01"
    json.dump(d, open("data/trust-contacts.json", "w"))
    return "retention"


@case("a contact who has opted out reappearing in the index")
def _(tmp):
    d = json.load(open("data/trust-contacts.json"))
    code = list(d["trusts"])[0]
    name = d["trusts"][code][0]["name"]
    json.dump({"names": [name], "emails": []}, open("data/contacts-optout.json", "w"))
    return "opted out"


@case("JavaScript that does not parse")
def _(tmp):
    with open("app/mst-logic.js", "a") as f:
        f.write("\nfunction(){  // deliberately broken\n")
    return "does not parse"


@case("the trust map collapsing to a handful of rows")
def _(tmp):
    d = json.load(open("data/trust-map.json"))
    d["trusts"] = d["trusts"][:5]
    json.dump(d, open("data/trust-map.json", "w"))
    return "Refusing a shrunken directory"


def main():
    # Snapshot every file a case might touch, so the repo is left untouched.
    tmp = tempfile.mkdtemp()
    watched = FILES + ["data/trust-map.json", "data/contacts-optout.json"]
    for f in watched:
        if os.path.exists(f):
            shutil.copy(f, os.path.join(tmp, f.replace("/", "_")))

    def restore():
        for f in watched:
            src = os.path.join(tmp, f.replace("/", "_"))
            if os.path.exists(src):
                shutil.copy(src, f)

    # The gate must pass on the real, current data first — otherwise every
    # "caught it" below is meaningless.
    rc, out = gate()
    if rc != 0:
        print("SETUP FAILED — verify.py does not pass on the current data:\n" + out)
        restore(); return 1

    failures = 0
    for name, fn in CASES:
        restore()
        expect = fn(tmp)
        if expect is None:
            print("SKIP  %s (fixture unavailable)" % name); continue
        rc, out = gate()
        if rc == 0:
            print("HOLE  %s — the gate PASSED this. It should not." % name); failures += 1
        elif expect.lower() not in out.lower():
            print("WEAK  %s — rejected, but not for the expected reason (%r missing)"
                  % (name, expect)); failures += 1
        else:
            print("ok    %s" % name)

    restore()
    rc, out = gate()
    if rc != 0:
        print("\nWARNING: the repo did not restore cleanly — check git status.")
        failures += 1
    print()
    print("GATE HOLDS — %d case(s)." % len(CASES) if not failures
          else "GATE HAS %d HOLE(S) — fix verify.py before trusting it." % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
