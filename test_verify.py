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


@case("a vocabulary edit that only re-tagged the day's new contacts")
def _(tmp):
    # The realistic failure: someone widens a speciality term, the daily run
    # tags what it harvested, and the other 1,390 rows keep sorting under the
    # old rules. Nothing looks broken on screen.
    d = json.load(open("data/trust-contacts.json"))
    code = list(d["trusts"])[0]
    d["trusts"][code][0]["spec"] = ["vascular"]
    d["trusts"][code][0]["cls"] = "clinical"
    json.dump(d, open("data/trust-contacts.json", "w"))
    return "disagree with the current vocabulary"


@case("contacts published with no relevance tags at all")
def _(tmp):
    d = json.load(open("data/trust-contacts.json"))
    for code in list(d["trusts"])[:3]:
        for e in d["trusts"][code]:
            e.pop("spec", None); e.pop("cls", None)
    json.dump(d, open("data/trust-contacts.json", "w"))
    return "no tags at all"


@case("a speciality term greedy enough to claim everyone")
def _(tmp):
    # A regex widened until it matches any notice. The panel would show a
    # vascular rep every contact at every trust, and look busy doing it.
    d = json.load(open("data/trust-contacts.json"))
    for code in d["trusts"]:
        for e in d["trusts"][code]:
            e["spec"] = ["vascular"]; e["cls"] = "clinical"
    json.dump(d, open("data/trust-contacts.json", "w"))
    return "too greedy"


@case("relevance tags shipped without the rule they were derived under")
def _(tmp):
    d = json.load(open("data/trust-contacts.json"))
    d["tagRule"] = ""
    json.dump(d, open("data/trust-contacts.json", "w"))
    return "ships with its rule"


@case("a speciality tagged that the dropdown cannot select")
def _(tmp):
    # Tagging against speciality-map.json's canonical list rather than the live
    # SPECS dropdown is the easy version of this mistake: 'neonatal' is in one
    # and not the other, so every neonatal tag would be invisible.
    p = "data/products.json"
    d = json.load(open(p))
    d["SPECS"] = [s for s in d["SPECS"] if s.get("id") != "vascular"]
    json.dump(d, open(p, "w"))
    return "nobody can select"


def issues(**over):
    d = json.load(open("data/compare-issues.json"))
    d.update(over)
    return d


def put_issue(d, spec, **fields):
    """Drop one item into a speciality, for the compare-feed cases below."""
    item = {"d": "Jul 2026", "co": "", "p": "An item", "s": "x", "use": "",
            "url": "https://example.invalid/notice", "autoDetected": True}
    item.update(fields)
    d["specialities"].setdefault(spec, {"label": spec.title(), "issues": []})
    d["specialities"][spec]["issues"].append(item)
    return d


# --- the 22/07-30/07 Compare-feed false positives --------------------------
# Three items were in front of paying members for over a week, were deleted by
# hand on 29/07, and two were re-added by the refresh the next morning because
# nothing checked. These four cases are that incident, split into its parts.

@case("a gov.uk weekly round-up index page filed as if it were one notice")
def _(tmp):
    d = put_issue(issues(), "continence",
                  p="Field Safety Notices: 6 to 10 April 2026",
                  url="https://www.gov.uk/drug-device-alerts/field-safety-notices-6-to-10-april-2026")
    json.dump(d, open("data/compare-issues.json", "w"))
    return "ROUND-UP index page"


@case("a suppressed notice back in the feed after a re-run")
def _(tmp):
    sup = json.load(open("data/suppressed-notices.json"))
    url = next(iter(sup["urls"]))
    d = put_issue(issues(), "vascular", p="Judged out of scope, yet here it is", url=url)
    json.dump(d, open("data/compare-issues.json", "w"))
    return "on the suppression list but is back in the feed"


@case("a compare-feed item with no source link")
def _(tmp):
    # The dashboard keys Lou's tick boxes on this URL, so a missing one silently
    # detaches her sign-off as well as making the claim uncheckable.
    d = put_issue(issues(), "vascular", p="Unsourced claim", url="")
    json.dump(d, open("data/compare-issues.json", "w"))
    return "has no source URL"


@case("the same notice filed under two specialities")
def _(tmp):
    d = issues()
    url = "https://www.supplychain.nhs.uk/icn/duplicated-notice/"
    put_issue(d, "vascular", p="Once", url=url)
    put_issue(d, "continence", p="Twice", url=url)
    json.dump(d, open("data/compare-issues.json", "w"))
    return "filed twice"


@case("an empty compare feed")
def _(tmp):
    d = issues()
    for blk in d["specialities"].values():
        blk["issues"] = []
    json.dump(d, open("data/compare-issues.json", "w"))
    return "Compare feed is empty"


def main():
    # Snapshot every file a case might touch, so the repo is left untouched.
    tmp = tempfile.mkdtemp()
    watched = FILES + ["data/trust-map.json", "data/contacts-optout.json",
                       "data/products.json", "data/compare-issues.json",
                       "data/suppressed-notices.json"]
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
