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
import concurrent.futures as cf
import json, os, re, shutil, subprocess, sys, tempfile

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


# --- dates and pinned clusters, added 05/08/2026 ---------------------------
# Return and resolution dates moved out of the notice's prose and into a field
# so the tab can count down to them. That makes them the first thing on the page
# a rep will act on without opening the source, so each case below is a way the
# countdown could confidently state something untrue.

@case("a return deadline the page would count down to, in a format it cannot read")
def _(tmp):
    d = put_issue(issues(), "skin-prep", p="Return the stock",
                  url="https://www.supplychain.nhs.uk/icn/return-me/",
                  dates=[{"kind": "deadline", "on": "14/08/2026", "what": "Return by"}])
    json.dump(d, open("data/compare-issues.json", "w"))
    return "not a plain ISO"


@case("a date of a kind the tab does not know how to colour")
def _(tmp):
    # 'deadline' is red and counts down; 'resolve' never is. An unknown kind
    # would fall through to the resolution styling, quietly demoting a deadline.
    d = put_issue(issues(), "skin-prep", p="Something happens",
                  url="https://www.supplychain.nhs.uk/icn/unknown-kind/",
                  dates=[{"kind": "return", "on": "2026-08-14", "what": "Return by"}])
    json.dump(d, open("data/compare-issues.json", "w"))
    return "unknown kind"


@case("a notice marked resolved on a date that has not happened yet")
def _(tmp):
    d = put_issue(issues(), "vascular", p="Closed in advance",
                  url="https://www.supplychain.nhs.uk/icn/resolved-in-future/",
                  dates=[{"kind": "resolved", "on": "2099-01-01", "what": "Notice marked resolved"}])
    json.dump(d, open("data/compare-issues.json", "w"))
    return "a date in the future"


@case("a pinned cluster pointing at a notice that is no longer in the feed")
def _(tmp):
    # The cluster holds no facts of its own, only pointers, so this is the one
    # way it can go wrong: a notice is removed and the pinned panel keeps
    # advertising it.
    d = issues()
    d["clusters"] = [{"id": "chlorhexidine", "title": "One running story",
                      "rule": "Membership rule: every open chlorhexidine notice.",
                      "urls": ["https://www.supplychain.nhs.uk/icn/deleted-yesterday/"]}]
    json.dump(d, open("data/compare-issues.json", "w"))
    return "not in the feed"


@case("a pinned cluster whose stated count no longer matches what it pins")
def _(tmp):
    d = issues()
    url = next(i["url"] for b in d["specialities"].values() for i in b["issues"])
    d["clusters"] = [{"id": "chlorhexidine", "title": "One running story",
                      "rule": "Membership rule: chlorhexidine notices. Eight notices, 8 notices.",
                      "urls": [url]}]
    json.dump(d, open("data/compare-issues.json", "w"))
    return "in its membership rule but pins"


@case("a pinned cluster that never says what put a notice in it")
def _(tmp):
    d = issues()
    url = next(i["url"] for b in d["specialities"].values() for i in b["issues"])
    d["clusters"] = [{"id": "chlorhexidine", "title": "One running story", "urls": [url]}]
    json.dump(d, open("data/compare-issues.json", "w"))
    return "states no membership rule"


@case("an empty compare feed")
def _(tmp):
    d = issues()
    for blk in d["specialities"].values():
        blk["issues"] = []
    json.dump(d, open("data/compare-issues.json", "w"))
    return "Compare feed is empty"


@case("a data file published with its ownership notice stripped")
def _(tmp):
    # The realistic route to this is not sabotage: build_supplier_index.py
    # rebuilds its output from scratch, so any generator that forgets to
    # re-stamp ships an unmarked file to a public repo.
    d = json.load(open("data/products.json"))
    d.pop("_notice", None)
    json.dump(d, open("data/products.json", "w"), ensure_ascii=False, indent=1)
    return "missing its ownership notice"


@case("an ownership notice quietly altered")
def _(tmp):
    # If the copyright line, the terms link or the marker ref can drift without
    # the gate noticing, the notice proves nothing about the copy that carries it.
    d = json.load(open("data/products.json"))
    d["_notice"]["terms"] = "https://example.com/terms/"
    json.dump(d, open("data/products.json", "w"), ensure_ascii=False, indent=1)
    return "drifted"


def link_check_cases():
    """The source-link check WARNS rather than fails, so it cannot be driven
    through gate() like the cases above — a warning still exits 0, by design.
    Exercised directly instead, with the network injected.

    Three behaviours matter, and the third is the one that keeps the check
    trustworthy: if NHS Supply Chain is down or throttling, EVERY source under it
    looks dead at once. A check that cried wolf on that would be muted within a
    week and would not have caught 05/08/2026 either.
    """
    import importlib
    v = importlib.import_module("verify")
    dead = "https://www.supplychain.nhs.uk/icn/gone/"
    store = {"specialities": {"continence": {"label": "Continence / Urology", "issues": [
        {"p": "A retired notice", "url": dead},
        {"p": "A live notice", "url": "https://www.supplychain.nhs.uk/icn/alive/"}]}}}
    results, failures = [], 0

    def run(name, fetch, want_dead_warning, want_control_warning):
        nonlocal failures
        v.warns[:] = []
        v.check_source_links(store, offline=False, fetch=fetch, pause=lambda s: None)
        text = " ".join(m for _, m in v.warns).lower()
        got_dead = "gone/" in text
        # Match the abort message itself, not the phrase "control URL", which
        # also appears in the normal dead-link summary line.
        got_control = "could not run the source-link check" in text
        if got_dead == want_dead_warning and got_control == want_control_warning:
            print("ok    %s" % name)
        else:
            print("HOLE  %s — dead=%s (want %s), control=%s (want %s)"
                  % (name, got_dead, want_dead_warning, got_control, want_control_warning))
            failures += 1

    run("a dead source link in the feed",
        lambda u, timeout=15: 200 if u != dead else 404, True, False)
    run("every source link live",
        lambda u, timeout=15: 200, False, False)
    run("the whole host throttling us — must not cry wolf",
        lambda u, timeout=15: 503, False, True)

    v.warns[:] = []
    return failures


def concurrency_cases():
    """The gate must survive being run twice at once.

    On 05/08/2026 the JavaScript check wrote to a hardcoded /tmp/_verify_js.js.
    Two simultaneous runs overwrote each other's script, and the loser got a
    SYNTAX ERROR reported against an app/*.js file that parses perfectly. A false
    FAIL is not a harmless false alarm here: it blocks a push, and the refresh
    workflows commit unattended, so the data stops moving for a reason that is
    not real. Concurrent runs are normal — CI, the pre-push hook, two refresh
    workflows, and more than one Claude session.
    """
    failures = 0

    # Guard the specific regression: no shared, predictable temp path.
    # Comments are stripped first — the fix documents the old path by name, and a
    # guard that trips on its own explanation is a guard someone deletes.
    src = "\n".join(l for l in open("verify.py").read().split("\n")
                    if not l.lstrip().startswith("#"))
    if re.search(r'["\']/tmp/_?[A-Za-z0-9_]+\.js["\']', src):
        print("HOLE  the JS check writes to a hardcoded shared temp path again"); failures += 1
    else:
        print("ok    the JS check uses a private temp file, not a shared path")

    # And prove it: four gates at once must all agree, with no JS failures.
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: gate(), range(4)))
    codes = {rc for rc, _ in results}
    js_fail = [out for _, out in results if "does not parse" in out]
    if js_fail:
        print("HOLE  concurrent runs produced a bogus JS parse failure:\n%s"
              % js_fail[0][:400]); failures += 1
    elif len(codes) != 1:
        print("HOLE  concurrent runs disagreed on the exit code: %s" % codes); failures += 1
    else:
        print("ok    four concurrent gate runs agree, with no false JS failure")

    return failures


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
    failures += link_check_cases()
    failures += concurrency_cases()

    rc, out = gate()
    if rc != 0:
        print("\nWARNING: the repo did not restore cleanly — check git status.")
        failures += 1
    print()
    print("GATE HOLDS — %d case(s)." % (len(CASES) + 5) if not failures
          else "GATE HAS %d HOLE(S) — fix verify.py before trusting it." % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
