#!/usr/bin/env python3
"""
test_verify.py — proves the publish gate still catches what it was built for.

A gate nobody tests is a gate that quietly stops working. Each case below is a
state this repo has actually been in, or one line away from.

    python3 test_verify.py

Exit 0 = the gate holds. Exit 1 = the gate has a hole; do not trust a green
verify.py until this passes again.

THE CONTACT DATA IS NOT HERE, AND THE SUITE STILL RUNS
data/trust-contacts.json and data/people-moves.json hold real named NHS staff.
They were removed from this public repo on 17/08/2026 and live in the private repo
msh-hub-private, reaching members through the gated endpoint. Every contacts, tags
and moves case reads them off disk, so this suite briefly left with them — which
meant the public verify.py, the gate the Hub's own data passes through, ran with
nothing testing it.

So main() manufactures a synthetic pair for the run via tests/fixtures/contacts.py
when the real files are absent, and deletes it afterwards. In the private repo the
real files are present and the fixture stands aside. Two cases still skip here and
print their reason: the git replay of the 24/07 incident, whose commit the history
purge rewrote away, and the retention case, which needs the private harvester's
RETENTION_MONTHS. Neither is papered over, and the 24/07 fault itself is covered
here by a synthetic equivalent.
"""
import atexit
import concurrent.futures as cf
import datetime
import signal
import hashlib, json, os, re, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)

sys.path.insert(0, os.path.join(REPO, "tests", "fixtures"))
import contacts as fixture_contacts        # noqa: E402  (needs the path above)


def retention_months():
    """The retention the harvester actually enforces, or None if it is not here.

    verify.py reads RETENTION_MONTHS out of scripts/refresh_fts_contacts.py so it
    checks what runs rather than what a config claims. That harvester moved to the
    private repo with the data, so in the public repo there is no figure to read
    and verify.py disables the retention check and says so in a warning.

    That is honest behaviour, and it is NOT something to paper over: writing a
    stub harvester here so the number could be read would make the gate assert a
    retention rule that nothing in this repo enforces. So the case that tests
    retention skips here, out loud, and runs for real in the private repo.
    """
    try:
        src = open(os.path.join(REPO, "scripts", "refresh_fts_contacts.py")).read()
    except OSError:
        return None
    m = re.search(r"^RETENTION_MONTHS\s*=\s*(\d+)", src, re.M)
    return int(m.group(1)) if m else None

# The commit that published 145 false job changes to the Hub, 24/07/2026.
INCIDENT_COMMIT = "dcdd9eb"
FILES = ["data/people-moves.json", "data/trust-contacts.json", "app/mst-logic.js"]

# Files a case CREATES that the repo does not have yet. restore() takes these
# away again; everything else it restores by copying the snapshot back. A path
# only lands here when the case that wrote it found nothing there, so a file
# another session lands mid-run is never deleted by this.
CREATED = []


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


class Skip(str):
    """A case that cannot run HERE, with the reason said out loud.

    Returning None already skipped a case, but printed "fixture unavailable" for
    every reason there could be. A skip nobody can read is how a suite ends up
    reporting a green gate over checks that stopped running months ago — so a
    skip that is expected in one repo and not the other has to name itself.
    """


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
        # The history was REWRITTEN on 17/08/2026 to purge the two contact files,
        # so every commit got a new SHA and this one no longer resolves in the
        # public repo. Skipping is right — replaying a real incident from real
        # data is exactly what cannot happen in a repo the data has left. The
        # synthetic equivalents (IMPOSSIBLE HANDOVER via the moves cases below)
        # still exercise the same check.
        return Skip("the incident commit %s was rewritten out of this repo by the "
                    "17/08/2026 history purge; replays in msh-hub-private" % INCIDENT_COMMIT)
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



def seed_clean_plus(extra_framework):
    """The seed with every unsourced value/award claim stripped, plus ONE bad entry.

    Written this way deliberately. When these cases were added the live seed
    already held five unsourced money figures, so a case that merely injected a
    sixth would have "passed" on the pre-existing ones and proved nothing. The
    clean-then-inject shape means the gate has to reject THIS entry, and the case
    keeps its meaning after the real data is fixed.
    """
    d = json.load(open("data/supplier-seed.json"))
    suppliers = d.get("suppliers") if isinstance(d, dict) else d
    if isinstance(suppliers, dict):
        suppliers = list(suppliers.values())
    for s in suppliers or []:
        for f in (s.get("frameworks") or []):
            if f.get("source") or f.get("url") or f.get("capturedOn"):
                continue
            f.pop("value", None)
            for field in ("dates", "note"):
                v = f.get(field) or ""
                if re.search(r"award|re-?tender", v, re.I):
                    f[field] = ""
    (suppliers or [{}])[0].setdefault("frameworks", []).append(extra_framework)
    json.dump(d, open("data/supplier-seed.json", "w"))


@case("a framework money value published with no source")
def _(tmp):
    # £140m ex VAT sat on the IV Cannula entry for months with no link. A rep
    # quotes that to a category manager who negotiates the contract for a living.
    seed_clean_plus({"name": "NHS Supply Chain — Invented Category",
                     "value": "£140m ex VAT", "dates": "01/04/2027-31/03/2031"})
    return "no source, url or capturedOn"


@case("a framework award date published with no source")
def _(tmp):
    # An award date is a claim with a fuse on it: correct when typed, misleading
    # the day after. Nothing re-reads a curated entry, so it must carry a notice.
    seed_clean_plus({"name": "NHS Supply Chain — Invented Category",
                     "dates": "award ~27/07/2026"})
    return "asserts an award or re-tender"


def seed_supplier_plus(**fields):
    """The seed's first supplier, given one deliberately bad leadership/partnership.

    Same shape as seed_clean_plus() above and for the same reason: injected onto
    a supplier that carries neither field today, so the case proves the gate
    rejects THIS entry rather than passing on something pre-existing.
    """
    d = json.load(open("data/supplier-seed.json"))
    suppliers = d.get("suppliers") if isinstance(d, dict) else d
    if isinstance(suppliers, dict):
        suppliers = list(suppliers.values())
    (suppliers or [{}])[0].update(fields)
    json.dump(d, open("data/supplier-seed.json", "w"))


@case("a career claim about a named person with no source URL")
def _(tmp):
    # The 24/07/2026 class of error with different names in it: a plausible,
    # unevidenced statement about a real, identifiable person, on a paid product.
    seed_supplier_plus(leadership={"people": [
        {"name": "A Named Person", "role": "Founder", "officer": False,
         "claims": [{"text": "Eighteen years running a rival's patient-handling division."}]}]})
    return "no source URL"


@case("a leadership claim sourced over plain HTTP")
def _(tmp):
    seed_supplier_plus(leadership={"people": [
        {"name": "A Named Person", "role": "Founder", "officer": False,
         "claims": [{"text": "Ran a rival's division.",
                     "url": "http://example.invalid/profile"}]}]})
    return "non-HTTPS source"


@case("someone published as a Companies House officer with no appointed date")
def _(tmp):
    # officer:true asserts a register fact, and the register states a date for
    # every officer — so no date means the register was never actually read.
    seed_supplier_plus(leadership={"people": [
        {"name": "A Named Person", "role": "Director", "officer": True, "claims": []}]})
    return "no appointed date"


@case("a partnership row with no source URL")
def _(tmp):
    seed_supplier_plus(partnerships=[
        {"with": "A Counterparty Ltd", "covers": "Exclusive UK distribution",
         "confidence": "confirmed"}])
    return "has no source URL"


@case("prose migrated to a panel but left behind in the index's alerts")
def _(tmp):
    # THE 19/08/2026 ERROR. mergeSuppliers() does not copy `alerts` from the
    # seed, so removing prose from the SEED's alerts changes nothing a member
    # sees — the index still serves it, the new panel renders the same fact
    # beside it, and one fact has two homes on a paid product.
    PROSE = ("A 2024 incorporation whose leadership is not new to patient handling, which is "
             "the main reason to read this as an emerging competitor rather than a long-tail SME.")
    d = json.load(open("data/supplier-seed.json"))
    suppliers = d.get("suppliers") if isinstance(d, dict) else d
    if isinstance(suppliers, dict):
        suppliers = list(suppliers.values())
    target = (suppliers or [{}])[0]
    target["background"] = [{"heading": "Leadership", "text": PROSE,
                             "url": "https://example.invalid/x"}]
    json.dump(d, open("data/supplier-seed.json", "w"))

    idx = json.load(open("data/supplier-index.json"))
    rec = next((s for s in idx.get("suppliers", []) if s.get("name") == target.get("name")), None)
    if rec is None:
        return Skip("the seed's first supplier has no record in supplier-index.json here")
    rec.setdefault("alerts", []).append(PROSE)      # the leftover copy
    json.dump(idx, open("data/supplier-index.json", "w"))
    return "STILL in data/supplier-index.json"


@case("background prose written straight into the alerts panel")
def _(tmp):
    # THE BUCKET REFILLING. Before typing, 272 of 383 curated alerts were
    # company background, so the panel a member reads for safety was mostly
    # corporate history. An untyped curated alert is how that came back.
    idx = json.load(open("data/supplier-index.json"))
    rec = (idx.get("suppliers") or [{}])[0]
    rec.setdefault("alerts", []).append(
        "Owned by a German parent since the 2019 buyout; UK entity confirmed at "
        "Companies House 01234567, registered office moved to Luton in 2026.")
    json.dump(idx, open("data/supplier-index.json", "w"))
    return "must declare `kind`"


@case("a curated alert typed with a word that is not a kind")
def _(tmp):
    idx = json.load(open("data/supplier-index.json"))
    rec = (idx.get("suppliers") or [{}])[0]
    rec.setdefault("alerts", []).append({"kind": "note", "text": "Something happened."})
    json.dump(idx, open("data/supplier-index.json", "w"))
    return "must declare `kind`"


@case("an alert edited in the seed but not in the index the page reads")
def _(tmp):
    # The asymmetry itself: `alerts` is the one field mergeSuppliers() does not
    # copy from the seed. Editing one file alone is silently wrong in one
    # direction or the other, and both directions shipped on 19/08/2026.
    d = json.load(open("data/supplier-seed.json"))
    suppliers = d.get("suppliers") if isinstance(d, dict) else d
    if isinstance(suppliers, dict):
        suppliers = list(suppliers.values())
    idx = json.load(open("data/supplier-index.json"))
    names = {s.get("name") for s in idx.get("suppliers", [])}
    target = next((s for s in suppliers if s.get("name") in names), None)
    if target is None:
        return Skip("no supplier appears in both the seed and the index here")
    target.setdefault("alerts", []).append(
        {"kind": "supply", "text": "A line was delisted, recorded in the seed only."})
    json.dump(d, open("data/supplier-seed.json", "w"))
    return "disagree between the seed"


@case("a background entry sourced over plain HTTP")
def _(tmp):
    seed_supplier_plus(background=[
        {"heading": "About", "text": "Founded to do a thing, per its own about page.",
         "url": "http://example.invalid/about"}])
    return "non-HTTPS source"


@case("a partnership published with no declared confidence")
def _(tmp):
    # Without `confidence` the row renders as a verified commercial agreement,
    # which is exactly what an arrangement claimed only by the parties is not.
    seed_supplier_plus(partnerships=[
        {"with": "A Counterparty Ltd", "covers": "Exclusive UK distribution",
         "url": "https://example.invalid/announcement"}])
    return "declares no `confidence`"


def sourced(count=2, min_n=2):
    """A trust with `count` contacts each seen on at least `min_n` notices.

    The mirror of pick(): these names clear the evidence floor, so a move built on
    them reaches the date rules rather than being rejected as thin first.
    """
    for code, v in contacts().items():
        hits = [e for e in v if e.get("n", 1) >= min_n]
        if len(hits) >= count:
            return code, hits[:count]
    return None, []


@case("a handover from someone who was still there — the 24/07 incident, synthetically")
def _(tmp):
    # The replay-from-git case above cannot run in the public repo any more: the
    # purge rewrote the incident commit out of the history. This is the same
    # fault built by hand, so the check that caught 145 false job changes stays
    # tested HERE and not only in the private repo.
    code, two = sourced(2)
    if not code:
        return None
    d = moves(moves=[{"trust": code, "name": two[0]["name"], "email": "",
                      "firstSeen": "2020-01-01", "replaces": two[1]["name"],
                      "replacesLastSeen": "2026-01-01", "notice": "x", "ocid": "y"}])
    json.dump(d, open("data/people-moves.json", "w"))
    return "IMPOSSIBLE HANDOVER"


@case("a handover inside the gap the file itself declares")
def _(tmp):
    # Chronologically possible and still not a handover: two names ten days apart
    # at one trust is a rota, a cover arrangement or two buyers. The file declares
    # a 60-day rule, so the gate must hold it to its own rule.
    code, two = sourced(2)
    if not code:
        return None
    today = datetime.date.today()
    d = moves(moves=[{"trust": code, "name": two[0]["name"], "email": "",
                      "firstSeen": (today - datetime.timedelta(days=30)).isoformat(),
                      "replaces": two[1]["name"],
                      "replacesLastSeen": (today - datetime.timedelta(days=40)).isoformat(),
                      "notice": "x", "ocid": "y"}])
    json.dump(d, open("data/people-moves.json", "w"))
    return "GAP TOO SHORT"


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
    if retention_months() is None:
        return Skip("scripts/refresh_fts_contacts.py is in the private repo, so verify.py "
                    "has no retention figure to read here and disables the check. This case "
                    "runs in msh-hub-private, against the real harvester")
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


# --- researched supplier sets, added 05/08/2026 -----------------------------
# A supplier table is what a rep reads INSTEAD of doing their own research, so
# it fails in ways the notices feed cannot.

def suppliers():
    return json.load(open("data/compare-suppliers.json"))


@case("a supplier table quoting a framework that has already expired")
def _(tmp):
    # The quiet one. Nothing looks broken; a rep just walks into a tender
    # citing a route to market that ended.
    d = suppliers()
    sp = next(iter(d["specialities"].values()))
    sp["route"][0]["dates"] = "01/02/2019 – 31/01/2021"
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "framework it names ended"


@case("a warning chip pointing past the end of its speciality's notices")
def _(tmp):
    # `iss` indexes the issues array BY POSITION, so removing one notice
    # renumbers every chip after it onto the wrong recall.
    d = suppliers()
    sp = next(iter(d["specialities"].values()))
    sp["suppliers"][0]["iss"] = [99]
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "indexes the issues array BY POSITION"


@case("a supplier covering a product type the dropdown cannot offer")
def _(tmp):
    d = suppliers()
    sp = next(iter(d["specialities"].values()))
    sp["suppliers"][0]["t"] = ["notatype"]
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "not in this speciality's `types` map"


@case("a supplier set for a speciality nothing can ever select")
def _(tmp):
    # Not simply "absent from products.json SPECS" — `skin-prep` and
    # `product-match` are both absent and both render every day. The failure
    # that matters is a set for an id that is in neither SPECS nor the feed, so
    # no dropdown entry can ever reach it and the research is invisible.
    d = suppliers()
    d["specialities"]["notaspeciality"] = d["specialities"].pop(next(iter(d["specialities"])))
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "neither in products.json SPECS nor carrying notices"


@case("supplier sets shipped without the sourcing rule they were built under")
def _(tmp):
    d = suppliers()
    d["sourceRule"] = ""
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "states no sourceRule"


# --- ONE LIST: supplier and speciality vocabulary drift, added 06/08/2026 ---
# The audit that forced these: BD is spelled nine ways across five files, and
# supplier-search.js falls back to a substring match returning the FIRST hit,
# so "Becton Dickinson UK" resolves to a corrupt record whose whole name is a
# list of seven companies. Each case below is a way that gets worse.

def sup_index():
    return json.load(open("data/supplier-index.json"))


def write_sup_index(d):
    json.dump(d, open("data/supplier-index.json", "w"), ensure_ascii=False)


def first_supplier_row():
    """(doc, speciality block, a copy of its first supplier row)."""
    d = suppliers()
    for blk in d["specialities"].values():
        rows = blk.get("suppliers") or []
        if rows:
            return d, blk, json.loads(json.dumps(rows[0]))
    return None, None, None


@case("a NEW Compare-tab company name that reaches no supplier record")
def _(tmp):
    # The precise catch. Counts cannot see this — swap one offender for
    # another and the total is unchanged while a fresh mistake ships.
    if subprocess.run(["git", "show", "HEAD:data/compare-suppliers.json"],
                      capture_output=True, text=True).returncode != 0:
        return None                       # no committed baseline to diff against
    d, blk, row = first_supplier_row()
    if row is None:
        return None
    row["co"] = "Definitely Not A Real Medtech Company"
    blk["suppliers"].append(row)
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "new supplier name"


@case("a supplier record deleted from the master, orphaning a Compare-tab name")
def _(tmp):
    # The ratchet on its own: the name is not new, so only the count moves.
    # This is the realistic version — a tidy-up of supplier-index.json that
    # nobody realises the Compare tab was pointing at.
    d = sup_index()
    seed_names = {s["name"] for s in json.load(open("data/supplier-seed.json"))["suppliers"]}
    live = set()
    for blk in (suppliers().get("specialities") or {}).values():
        for r in blk.get("suppliers") or []:
            live.add(r.get("co"))
    # A record that resolves a Compare-tab name today and is NOT in the seed,
    # so removing it from the index really does orphan the name.
    victim = next((s for s in d["suppliers"]
                   if s["name"] in live and s["name"] not in seed_names), None)
    if victim is None:
        return None
    d["suppliers"] = [s for s in d["suppliers"] if s["name"] != victim["name"]]
    write_sup_index(d)
    # Was "rose from" while compare_unresolved carried a baseline. It reached 0 on
    # 07/08/2026 and graduated to a hard check, so the ratchet's rise message is
    # no longer the one this produces — the zero-tolerance message is.
    return "must stay at zero"


@case("the same company entered twice under two spellings on the Compare tab")
def _(tmp):
    d, blk, row = first_supplier_row()
    if row is None:
        return None
    row["co"] = row["co"] + " Ltd"        # normalises to the same company
    blk["suppliers"].append(row)
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "spelled more than one way"


@case("a speciality added to the dropdown but not to the canonical map")
def _(tmp):
    # Adding a speciality has to be ONE edit. Today it is two, and doing only
    # the first gives a speciality the Mapper offers and Meeting Prep cannot
    # reconcile any supplier against.
    d = json.load(open("data/products.json"))
    d["SPECS"].append({"id": "notaspeciality", "label": "Not A Speciality"})
    json.dump(d, open("data/products.json", "w"), ensure_ascii=False)
    return "speciality ids in products.json SPECS but not"


@case("a supplier tagged with a speciality string nothing can resolve")
def _(tmp):
    d = sup_index()
    d["suppliers"][0].setdefault("specialities", []).append("Some Free Text Nobody Mapped")
    write_sup_index(d)
    return "resolving to no canonical speciality"


@case("an expired framework left in the live frameworks list")
def _(tmp):
    # NHS Supply Chain leaves a brief published after its framework ends, so the
    # capture keeps returning them. Three were live on 07/08/2026, one 515 days
    # past its end date, and 24 supplier rows showed them under "Frameworks on".
    d = json.load(open("data/frameworks.json"))
    if not (d.get("expired") or []):
        return None
    d["frameworks"].append(d["expired"][0])
    json.dump(d, open("data/frameworks.json", "w"), ensure_ascii=False)
    return "already ended but are still in the live"


@case("an alias that is really another supplier record's own name")
def _(tmp):
    # Alias lookup is first-wins, so this does not create a visible duplicate —
    # it silently redirects every reference to the record that owns the name.
    # Found live on 07/08/2026: "Abbott Diagnostics" carried the alias "Abbott
    # Laboratories", so the entity listing FreeStyle Libre in the Drug Tariff
    # resolved to Abbott's diagnostics arm instead.
    d = json.load(open("data/supplier-seed.json"))
    names = [s["name"] for s in d["suppliers"]]
    if len(names) < 2:
        return None
    d["suppliers"][0].setdefault("aliases", []).append(names[1])
    json.dump(d, open("data/supplier-seed.json", "w"), ensure_ascii=False)
    return "another supplier record's own name"


@case("a supplier record whose name is a list of companies")
def _(tmp):
    # Exactly what build_supplier_index.py already did once: it lifted a
    # notice's whole supplier field in as one record, and Supplier Search now
    # returns it to anyone typing any of the seven names inside it.
    d = sup_index()
    d["suppliers"].append({
        "name": "Acme Medical Ltd, Beta Health, Gamma Devices and Delta Surgical Ltd",
        "aliases": ["Acme Medical Ltd, Beta Health, Gamma Devices and Delta Surgical Ltd"],
        "specialities": ["Wound care"]})
    write_sup_index(d)
    return "name is a list of companies"


@case("comptab.js's baked fallback naming a company the master does not hold")
def _(tmp):
    # No baseline on this one: the fallback is 16 names and it is clean. It is
    # what members see when the data fetch fails, so it is the one supplier
    # list with no way to correct it after publication.
    js = "app/comptab.js"
    lines = open(js).read().split("\n")
    m = re.match(r"^var D=(\{.*\});$", lines[1])
    if not m:
        return None
    D = json.loads(m.group(1))
    for blk in D.values():
        if blk.get("suppliers"):
            blk["suppliers"][0]["co"] = "A Company That Is In No Master List"
            break
    lines[1] = "var D=" + json.dumps(D, ensure_ascii=False) + ";"
    open(js, "w").write("\n".join(lines))
    return "baked fallback names companies that reach no supplier record"


@case("the curated banner back to firing on autoDetected alone")
def _(tmp):
    # Live on 07/08/2026: 12 curated items on Med Sales Tools carried
    # "NEW — auto-detected, verify at source" above a tactical line a human had
    # written. `autoDetected` records how an item ARRIVED and never goes false.
    # The publish gate reported success on the commit that made it worse,
    # because nothing in it read the renderer.
    js = "app/comptab.js"
    src = open(js).read()
    if "it.autoDetected&&!((it.use||'').trim())" not in src:
        return None
    open(js, "w").write(src.replace("it.autoDetected&&!((it.use||'').trim())", "it.autoDetected"))
    return "auto-detected, verify at source"


@case("a hand-added supplier row that resolves to a master but carries no ref")
def _(tmp):
    # Not hypothetical: this happened on 07/08/2026, hours after the fix, while
    # building the patient-handling set. Eight rows were written by hand without
    # `ref` and "GBUK Healthcare" split straight back out of GBUK Group. coKey()
    # falls back to `co`, which is correct for a name that reaches no master and
    # silent for one that does — so deriving `ref` once is not enough.
    d, blk, row = first_supplier_row()
    if row is None or "ref" not in row:
        return None
    for b in d["specialities"].values():
        for r in b.get("suppliers") or []:
            if r.get("co") == row["co"]:
                r.pop("ref", None)
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "carry no `ref`"


@case("the Compare tab's company picker back to matching on the display spelling")
def _(tmp):
    # Lou, 07/08/2026: picking "GBUK Group" offered Vascular access and nothing
    # else, for a company on 20 NHS Supply Chain frameworks. The picker compared
    # `s.co` exactly, so a firm spelled four ways in compare-suppliers.json was
    # four companies each holding a quarter of its footprint. It read perfectly
    # sensibly, which is why it survived. Nineteen companies were split this way.
    js = "app/comptab.js"
    src = open(js).read()
    if "coKey(s)===onlyCo" not in src:
        return None
    open(js, "w").write(src.replace("coKey(s)===onlyCo", "s.co===onlyCo"))
    return "compares `.co` against the picker"


@case("coKey() quietly dropped back to the display spelling")
def _(tmp):
    # The other half. Leave every call site alone and take the `ref` arm out of
    # the one function they all go through, and all 31 merges revert silently.
    js = "app/comptab.js"
    src = open(js).read()
    if "s.ref||s.co" not in src:
        return None
    open(js, "w").write(src.replace("(s&&(s.ref||s.co))", "(s&&s.co)"))
    return "no coKey() resolving `ref` before `co`"


@case("a framework whose countdown date drifts from its printed date range")
def _(tmp):
    # Caught a real typo on 05/08/2026: endsOn said 15/06/2027 while the range
    # said 19/06/2027. The page counts down to endsOn, so a drifted field means
    # the tab states an expiry with total confidence that the source contradicts.
    d = suppliers()
    sp = next(iter(d["specialities"].values()))
    sp["route"][0]["endsOn"] = "2099-01-01"
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "in its date range but endsOn is"


@case("a framework with no expiry the tab can count down to")
def _(tmp):
    d = suppliers()
    sp = next(iter(d["specialities"].values()))
    sp["route"][0].pop("endsOn", None)
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "has no endsOn"


@case("the unsorted holding pen published to members")
def _(tmp):
    # 06/08/2026: the first overnight run after the no-drop fallback landed put
    # 28 items in 'unsorted' — every one a generic medicines recall or an MHRA
    # monthly roundup — and all 28 were live with blank tactical lines. The tab
    # skips that pen now; this proves nobody can quietly remove the skip.
    d = issues()
    d["specialities"]["unsorted"] = {"label": "Not yet sorted by speciality", "issues": [
        {"d": "Aug 2026", "co": "", "p": "Class 2 Medicines Recall: Someone, Ramipril 5mg",
         "s": "x", "use": "", "url": "https://www.gov.uk/drug-device-alerts/unsorted-thing",
         "autoDetected": True}]}
    json.dump(d, open("data/compare-issues.json", "w"))
    js = "app/comptab.js"
    src = open(js).read()
    open(js, "w").write(src.replace("if(k==='unsorted'){continue;}", ""))
    return "no longer skips the 'unsorted' holding pen"


@case("a speciality with an empty supplier table and no reason given")
def _(tmp):
    # Medicines forced a legitimate version of this: NHS England's MPSC
    # frameworks publish no award list, so there is no public competitor set to
    # show. That is allowed — but only as a DECLARED absence with a reason a
    # reader can judge, never an empty array somebody forgot to fill.
    d = suppliers()
    k = next(iter(d["specialities"]))
    d["specialities"][k]["suppliers"] = []
    d["specialities"][k].pop("noSuppliers", None)
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "no `noSuppliers` explanation"


@case("a framework with no expiry and no reason for having none")
def _(tmp):
    d = suppliers()
    k = next(iter(d["specialities"]))
    d["specialities"][k]["route"][0].pop("endsOn", None)
    d["specialities"][k]["route"][0].pop("noExpiry", None)
    json.dump(d, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)
    return "no `noExpiry` reason"


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


# --- the Company Report, added 06/08/2026 ----------------------------------
# Two of its panels are DERIVED — "also on this framework" is co-listing rather
# than competition, and the field position band is co-listing x statutory
# accounts category. docs/COMPANY-REPORT-METHOD.md is the specification; these
# cases are its invariants, one per case.

@case("a company report turnover of 0 where null means 'not disclosed'")
def _(tmp):
    # Driven through gate() rather than in-process, deliberately: this is the
    # case that proves check_company_report is WIRED INTO main() and not merely
    # written. The rest are exercised directly, below.
    p = "data/company-financials.json"
    if not os.path.exists(p):
        CREATED.append(p)                    # restore() must take it away again
    json.dump(cr_financials(turnoverGBP=0), open(p, "w"), ensure_ascii=False, indent=1)
    # The file also has no marker ref yet, so check_notice fails alongside this
    # one. The expected phrase below is unique to the check under test.
    return "parse bug"


def cr_today(days=0):
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


def cr_financials(**over):
    """A financials file that PASSES, so each case can break exactly one thing.

    'GBUK Group' is a real name in data/supplier-seed.json — a company report
    about a company this repo holds no supplier record for is a report about
    nobody, and that is one of the cases below.
    """
    company = {
        "companyNumber": "01234567",
        "registeredName": "GBUK GROUP LIMITED",
        "matchConfidence": "confirmed",
        "status": "active",
        "incorporated": "2000-05-18",
        "accountsCategory": "full",
        "accountsMadeUpTo": "2025-03-31",
        "turnoverGBP": None,
        "employees": None,
        "sourceUrl": "https://find-and-update.company-information.service.gov.uk/company/01234567",
    }
    top = {}
    for k, v in over.items():
        if k in ("dataAsOf", "thresholds", "companies", "source"):
            top[k] = v
        else:
            company[k] = v
    d = {
        "dataAsOf": cr_today(-30),
        "source": "Companies House public data API",
        "thresholds": {
            "readFrom": "https://www.gov.uk/government/publications/company-size",
            "readOn": cr_today(-30),
            "appliesTo": "periods beginning on or after 6 April 2025",
            "bands": {"micro": {"turnover": 1}, "small": {"turnover": 2},
                      "medium": {"turnover": 3}},
        },
        "companies": {"GBUK Group": company},
    }
    d.update(top)
    return d


# A source file that passes every source invariant: no percentage in a share
# context, no count typed into prose, both evidence floors visible.
CR_GOOD_JS = """
/* Field position. No percentage is ever published as market share. */
function bands(rows){
  if(rows.length < 2){ return '<p>Fewer than two suppliers on this lot.</p>'; }
  var known = rows.filter(function(r){ return r.accountsCategory; });
  if(known.length < rows.length/2){ return '<p>Too few resolved to compare.</p>'; }
  var h = '<div style="width:100%">';
  h += '<b>'+rows.length+' suppliers on this lot.</b> ';
  h += rows.filter(function(r){return r.matchConfidence==='confirmed';}).length+' confirmed.';
  return h+'</div>';
}
"""

CR_CASES = []


def cr(name, financials, js, want):
    CR_CASES.append((name, financials, js, want))


cr("a probable name-search match carrying a turnover figure",
   cr_financials(matchConfidence="probable", turnoverGBP=18000000, accountsCategory=""),
   "", "PROBABLE match")
cr("employees of 0, which the page would render as a real figure",
   cr_financials(employees=0), "", "parse bug")
cr("an accounts category outside the statutory enum",
   cr_financials(accountsCategory="small-ish"), "", "not one of the statutory categories")
cr("a size band label invented ad hoc",
   cr_financials(band="enormous"), "", "statutory band labels")
cr("bands assigned with no thresholds block at all",
   cr_financials(thresholds=None), "", "no `thresholds` block")
cr("a thresholds block with no date it was read on",
   cr_financials(thresholds={"readFrom": "https://www.gov.uk/x", "bands": {"micro": {}}}),
   "", "no usable readOn")
cr("a thresholds block inventing a fourth statutory band",
   cr_financials(thresholds={"readFrom": "https://www.gov.uk/x", "readOn": cr_today(-1),
                             "bands": {"micro": {}, "huge": {}}}), "", "invents band")
cr("thresholds read on a date that has not happened yet",
   cr_financials(thresholds={"readFrom": "https://www.gov.uk/x", "readOn": cr_today(400),
                             "bands": {"micro": {}}}), "", "in the future")
cr("Companies House read tomorrow — dataAsOf in the future",
   cr_financials(dataAsOf=cr_today(400)), "", "dataAsOf")
cr("a company report about a company no supplier record exists for",
   cr_financials(companies={"Nonesuch Medical Holdings": {
       "matchConfidence": "confirmed",
       "registeredName": "NONESUCH MEDICAL HOLDINGS LIMITED",
       "accountsCategory": "small", "turnoverGBP": None, "employees": None}}),
   "", "does not resolve to any supplier")
cr("a turnover figure shown bare, with no made-up-to date",
   cr_financials(turnoverGBP=18000000, accountsMadeUpTo=""), "", "no accountsMadeUpTo")
cr("a market share published as a percentage", None,
   "var h='<b>Market share: '+Math.round(n/t*100)+'%</b>';", "percent sign in a market-share")
cr("a percentage in the field position panel", None,
   "h+='<div>Field position: '+p+'% of this market</div>';", "percent sign in a market-share")
cr("a count typed into the rendered prose", None,
   "h+='<p>11 suppliers on this lot.</p>';", "count typed into rendered prose")
cr("a count written out in words in the rendered prose", None,
   "h+='<p>Three file large-company accounts.</p>';", "count typed into rendered prose")
cr("probable matches, and a source that never reads matchConfidence",
   cr_financials(matchConfidence="probable"),
   "var h='<p>'+rows.length+' on this lot</p>';", "never reads matchConfidence")

# ROUTE 2 — the company number the company publishes on its own site.
# A confirmation is a claim about a source. These three cases exist because the
# claim and the source live in two different files: the confidence is written to
# data/company-financials.json by scripts/refresh_companies_house.py, and the
# evidence for it to data/supplier-seed.json by scripts/confirm_company_numbers.py.
# Anything that separates them — the nightly rebuild dropping the field, a hand
# edit, a restore from an older seed — leaves a record citing a page this repo
# can no longer produce, which reads on the page as a verified fact.
cr("a route-2 confirmation whose evidence is not in the seed",
   cr_financials(matchedOn="company number published on the company's own website, agreeing "
                           "with the Companies House record — https://example.com/terms, "
                           "read 2026-08-14"),
   CR_GOOD_JS, "holds no companyNumberProof")
cr("a route-2 confirmation attached to a different company's number",
   cr_financials(companies={"AB Scientific": {
       "companyNumber": "00000001",
       "registeredName": "AB SCIENTIFIC LTD",
       "matchConfidence": "confirmed",
       "matchedOn": "company number published on the company's own website, agreeing with the "
                    "Companies House record — https://www.abscientific.com/terms-of-use/, "
                    "read 2026-08-14",
       "status": "active",
       "incorporated": "2014-05-08",
       "accountsCategory": "full",
       "accountsMadeUpTo": "2025-03-31",
       "turnoverGBP": None,
       "employees": None,
       "sourceUrl": "https://find-and-update.company-information.service.gov.uk/company/00000001",
   }}),
   CR_GOOD_JS, "belongs to a different company")

# And the other half of the job: the lookalikes it must stay QUIET on. A false
# FAIL blocks the unattended refresh workflows from committing, and the first
# false FAIL on an honest empty state is the one that gets the empty state
# deleted to make a push go through.
CR_QUIET = [
    ("a good file and a good source", cr_financials(), CR_GOOD_JS),
    # The honest version of the two route-2 cases above: AB Scientific really
    # does publish 09033854 on its own terms page, and the seed really does hold
    # the proof. If this one ever fails, the check has stopped recognising a
    # correct confirmation and the fix is the check, not the data.
    ("a route-2 confirmation that can show its working", {
        "dataAsOf": cr_today(-30),
        "source": "Companies House public data API",
        "thresholds": {
            "readFrom": "https://www.gov.uk/government/publications/company-size",
            "readOn": cr_today(-30),
            "appliesTo": "periods beginning on or after 6 April 2025",
            "bands": {"micro": {"turnover": 1}, "small": {"turnover": 2},
                      "medium": {"turnover": 3}},
        },
        "companies": {"AB Scientific": {
            "companyNumber": "09033854",
            "registeredName": "AB SCIENTIFIC LTD",
            "matchConfidence": "confirmed",
            "matchedOn": "company number published on the company's own website, agreeing with "
                         "the Companies House record — https://www.abscientific.com/terms-of-use/, "
                         "read 2026-08-14",
            "status": "active",
            "incorporated": "2014-05-08",
            "accountsCategory": "full",
            "accountsMadeUpTo": "2025-03-31",
            "turnoverGBP": None,
            "employees": None,
            "sourceUrl": "https://find-and-update.company-information.service.gov.uk/company/09033854",
        }},
    }, CR_GOOD_JS),
    ("a CSS width of 100% beside a Field position heading", None,
     "h+='<div>Field position</div><div style=\"width:100%\"></div>';"),
    ("a Share button on the interview pack, and a modulo", None,
     "h+='<button>Share</button>';var alt=i%2;h+='<div style=\"margin-left:50%\"></div>';"),
    ("a comment explaining the rule it must not break", None,
     "// never render 12% of this market as a market share\nvar h='';"),
    ("the evidence floor's own honest empty state", None,
     "if(rows.length<2){return '<p>Fewer than two suppliers on this lot.</p>';}"
     "\nif(k<rows.length/2){return '';}"),
    ("an https:// URL in a string, which naive comment-stripping would eat", None,
     "var u='https://find-and-update.company-information.service.gov.uk/company/1';"
     "\nif(rows.length<2){return '';}\nif(k<rows.length/2){return '';}"),
]


def company_report_cases():
    """The Company Report gate, driven directly.

    app/company-report.js belongs to a build in flight and
    data/company-financials.json does not exist yet. Writing a fixture over
    either from a test would race that work and could delete it on restore, so
    the JavaScript is injected instead — check_company_report takes both halves
    as arguments precisely so it can be driven this way, as link_check_cases
    does for the source-link check. One case (above) still goes through gate(),
    to prove the check is wired into main().
    """
    import importlib
    v = importlib.import_module("verify")
    failures = 0

    for name, financials, js, want in CR_CASES:
        v.fails[:] = []
        v.warns[:] = []
        v.check_company_report(financials, js)
        text = " ".join(m for _, m in v.fails)
        if not v.fails:
            print("HOLE  %s — the gate PASSED this. It should not." % name); failures += 1
        elif want.lower() not in text.lower():
            print("WEAK  %s — rejected, but not for the expected reason (%r missing)"
                  % (name, want)); failures += 1
        else:
            print("ok    %s" % name)

    for name, financials, js in CR_QUIET:
        v.fails[:] = []
        v.warns[:] = []
        v.check_company_report(financials, js)
        if v.fails:
            print("HOLE  %s — FALSE FAIL: %s"
                  % (name, " ".join(m for _, m in v.fails)[:220])); failures += 1
        else:
            print("ok    %s — no false failure" % name)

    v.fails[:] = []
    v.warns[:] = []
    return failures


def company_report_noop_case():
    """A check that nags before its feature exists is a check people mute.

    data/company-financials.json does not exist, so the Company Report gate must
    be a clean no-op on it — the same way check_shrink says nothing about a path
    that is not there. It must never FAIL the repo as it stands.
    """
    rc, out = gate()
    if "FAIL  [company-report]" in out or rc != 0:
        print("HOLE  the Company Report check fails the repo as it stands:\n%s"
              % "\n".join(l for l in out.split("\n") if "company-report" in l)[:600])
        return 1
    if not os.path.exists("data/company-financials.json") and \
            not os.path.exists("app/company-report.js"):
        if "company-report" in out:
            print("HOLE  the Company Report check is not silent while both its files are absent")
            return 1
        print("ok    the Company Report check is a clean no-op while its files do not exist")
    else:
        print("ok    the Company Report check passes the files that exist today")
    return 0


# ==========================================================================
# THE AWARD INDEX — a statutory notice attached to a NAMED company
# ==========================================================================
# scripts/refresh_awards.py is the first thing in this repo that says "this
# company won this contract". That is the 24/07/2026 failure with different
# nouns: the notice names a legal entity, the seed holds a trading name, and a
# matching layer stands between them. Every case below is a way that layer, or
# the file it writes, could put a real contract against the wrong real company
# — or put an absence in front of a member as though it were a fact about the
# company rather than about our index.
#
# Driven directly, like the Company Report cases: the check takes its three
# inputs as arguments precisely so a test does not have to write over live data
# to exercise it. The fixtures are hermetic — their own two-company seed — so a
# seed edit cannot quietly turn a case green.

CA_SEED = {"suppliers": [
    {"name": "Testco Medical", "aliases": ["Testco Medical", "TESTCO MEDICAL UK LIMITED"]},
    {"name": "Other Medical", "aliases": ["Other Medical"]},
]}


def ca_today(offset=0):
    return (datetime.date.today() + datetime.timedelta(days=offset)).isoformat()


def ca_row(**over):
    row = {
        "noticeSupplierName": "TESTCO MEDICAL UK LIMITED",
        "title": "Orthopaedic power tools",
        "buyer": "A Trust",
        "date": ca_today(-3),
        "url": "https://www.find-tender.service.gov.uk/Notice/077803-2026",
        "hubUrl": "https://medsalesintelligencehub.co.uk/medical-sales-hub/awards/",
        "source": "Find a Tender",
        "section": "tender-awards",
        "cpv": "33100000",
        "valueAmount": 94491.0,
        "valueCurrency": "GBP",
        "periodStart": None,
        "periodEnd": None,
        "company": "Testco Medical",
        "matchedOn": "recorded alias",
    }
    row.update(over)
    return row


def ca_doc(rows=None, **over):
    """A file that passes everything, so each case changes exactly one thing."""
    import importlib
    sys.path.insert(0, "scripts")
    cm = importlib.import_module("company_match")
    rows = [ca_row()] if rows is None else rows
    doc = {
        "dataAsOf": "14/08/2026",
        "generated": ca_today(-1),
        "source": "Find a Tender and Contracts Finder award-stage OCDS notices, OGL v3",
        "sectionRule": "Above threshold is a tender award; below threshold is a contract award.",
        "filterRule": "Headline CPV division 33, or a device term in the title.",
        "matchRule": cm.RULE,
        "coverage": {"complete": True, "window": {"from": ca_today(-8), "to": ca_today()},
                     "note": "Awards indexed over the windows listed."},
        "counts": {"companies": 1, "awardRows": len(rows), "unmatched": 0, "ambiguous": 0,
                   "rowsHeld": len(rows)},
        "companies": {"Testco Medical": rows},
        "unmatched": [], "ambiguous": [],
        "_rows": rows,
        "windows": [],
    }
    doc.update(over)
    return doc


# A source that renders the awards and states the absence honestly.
CA_GOOD_JS = """
var AWARDS = BASE + 'data/company-awards.json' + CB;
function awardSection(title, rows, ctx){
  if(!rows.length){ return sec(title, gap('Not captured for this company yet. The index '
    + 'has been walked, and nothing in it names this company.')); }
  return sec(title, rows.map(awardRow).join(''));
}
"""

CA_CASES = []


def ca(name, doc, js, want):
    CA_CASES.append((name, doc, js, want))


ca("an award attached to a company no supplier record exists for",
   ca_doc(**{"companies": {"Nonesuch Surgical": [ca_row(company="Nonesuch Surgical")]}}),
   "", "does not resolve to any supplier record")
ca("an award attached to a company the match rule does not reach",
   ca_doc(**{"companies": {"Other Medical": [ca_row(company="Other Medical")]}}),
   "", "disagree")
ca("an award published with no notice link",
   ca_doc([ca_row(url="")]), "", "carries no notice URL")
ca("an award with no usable date",
   ca_doc([ca_row(date="")]), "", "no usable date")
ca("an award dated after today",
   ca_doc([ca_row(date=ca_today(30))]), "", "has not happened yet")
ca("a contract value of 0, which the page would render as a free contract",
   ca_doc([ca_row(valueAmount=0)]), "", "parse bug")
ca("a contract value carried as a string",
   ca_doc([ca_row(valueAmount="94,491")]), "", "not a number")
ca("a Contracts Finder notice filed as an above-threshold tender award",
   ca_doc([ca_row(source="Contracts Finder", section="tender-awards")]),
   "", "the other feed's")
ca("an award filed under a section that does not exist",
   ca_doc([ca_row(section="framework-awards")]), "", "not one of")
ca("a header count that disagrees with the rows beneath it",
   ca_doc(**{"counts": {"companies": 1, "awardRows": 9, "unmatched": 0, "ambiguous": 0}}),
   "", "but holds")
ca("a match rule edited in the file, away from the rule that ran",
   ca_doc(matchRule="names are matched on a close resemblance"),
   "", "not the rule")
ca("a file generated tomorrow",
   ca_doc(generated=ca_today(5)), "", "has not happened yet")
ca("an incomplete walk that does not admit it is incomplete",
   ca_doc(coverage={"complete": False, "window": {}, "note": "Awards indexed."}),
   "", "does not say so")
ca("a page telling a member the company has no awards",
   None,
   "var A = BASE + 'data/company-awards.json';"
   "\nh += sec('Tender awards', gap('No awards for this company.'));",
   "absolute absence")

CA_QUIET = [
    ("a good file and a good source", ca_doc(), CA_GOOD_JS),
    # An award naming a company this repo does not hold is the NORMAL case —
    # most UK medtech suppliers are not Hub seed companies. It belongs in the
    # quarantine and must not fail anything.
    ("a supplier the seed does not hold, left quarantined",
     ca_doc(**{"unmatched": [ca_row(noticeSupplierName="Pfizer Ltd", company=None,
                                    reason="no Hub company matches")],
               "counts": {"companies": 1, "awardRows": 1, "unmatched": 1, "ambiguous": 0}}),
     CA_GOOD_JS),
    ("the honest empty state, which must never read as an absolute", None, CA_GOOD_JS),
    # The words "no awards" inside a COMMENT explaining the rule must not trip
    # it — a check that fails on the comment documenting the rule is a check
    # somebody deletes the comment to satisfy.
    ("a comment explaining the absolute-absence rule", None,
     "var A = BASE + 'data/company-awards.json';"
     "\n// never say the company has no awards — say the index has not captured any\n"),
]


# ---------------------------------------------------------------------------
# THE SUPPLIER PRESS GATE (data/company-press.json)
# ---------------------------------------------------------------------------
# The hazard this feature exists to survive is a live one, checked 18/08/2026:
# "Jeenie Solutions" is a UK bariatric patient-handling supplier in Wetherby, and
# "Jeenie" is a US remote-interpreting company whose coverage is full of patients
# and healthcare. A name match plus a medical corroborator publishes the wrong
# company's funding round under a Hub supplier's name. So the seed below carries
# that exact pair of shapes, and the cases drive the real rule.
CP_SEED = {"suppliers": [
    {"name": "Jeenie Solutions",
     "aliases": ["Jeenie Solutions", "Jeenie", "Jeenie Solutions Ltd", "jeenie.uk"],
     "specialities": ["Patient handling"],
     "products": ["SHAPE bariatric empathy suit", "Liftie modular flat-lift"]},
    {"name": "Convatec", "aliases": ["Convatec", "ConvaTec Group plc"],
     "specialities": ["Wound care", "Stoma care"], "products": []},
]}


def cp_today(offset=0):
    return (datetime.date.today() + datetime.timedelta(days=offset)).isoformat()


def cp_src(**over):
    d = {"publisher": "MedTech Dive", "urlType": "publisher",
         "url": "https://www.medtechdive.com/news/convatec-rd/802196/",
         "redirectUrl": "https://news.google.com/rss/articles/CBMiABC"}
    d.update(over)
    return d


def cp_item(**over):
    d = {"headline": "Convatec plans $1B investment in R&D in the US and UK",
         "date": cp_today(-30),
         "summary": "Convatec said the UK medtech investment covers wound care sites.",
         "sources": [cp_src(),
                     cp_src(publisher="The Times",
                            url="https://www.thetimes.com/business/article/convatec")],
         "match": {"alias": "convatec", "aliasStrength": "distinctive",
                   "sectorTerm": "medtech", "relevanceTerm": "uk"},
         "verified": True, "autoDetected": True}
    d.update(over)
    return d


def cp_doc(items=None, **over):
    """A file that passes everything, so each case changes exactly one thing."""
    import importlib
    sys.path.insert(0, "scripts")
    pm = importlib.import_module("press_match")
    items = [cp_item()] if items is None else items
    block = {"Convatec": {"lastChecked": cp_today(), "items": items},
             "Jeenie Solutions": {"lastChecked": cp_today(), "items": []}}
    nsrc = sum(len(i.get("sources") or []) for i in items)
    doc = {
        "dataAsOf": "18/08/2026",
        "generated": cp_today(-1),
        "source": "Google News RSS, one query per supplier, hl=en-GB&gl=GB.",
        "matchRule": pm.RULE,
        "corroborationRule": "Two distinct reputable publishers; PR wires never count.",
        "rotationRule": "Oldest-checked first; noted suppliers every 14 days, the rest every 35.",
        "linkRule": "Redirects are resolved to the publisher, or kept and marked as redirects.",
        "emptyStateRule": "lastChecked with no items means checked and nothing met the bar.",
        "rotation": {"dailyBudget": 80, "notedCycleDays": 14, "otherCycleDays": 35},
        "coverage": {"complete": True, "suppliersNeverChecked": 0,
                     "note": "Every supplier has been checked at least once."},
        "counts": {"suppliers": 2, "suppliersWithItems": 1 if items else 0,
                   "items": len(items), "sources": nsrc,
                   "resolvedLinks": sum(1 for i in items for s in (i.get("sources") or [])
                                        if s.get("urlType") == "publisher"),
                   "redirectLinks": sum(1 for i in items for s in (i.get("sources") or [])
                                        if s.get("urlType") != "publisher")},
        "suppliers": block,
    }
    doc.update(over)
    return doc


CP_CASES = []


def cp(name, doc, want):
    CP_CASES.append((name, doc, want))


# --- THE INCIDENT THIS WAS BUILT FOR --------------------------------------
cp("the US translation company's funding round filed under Jeenie Solutions",
   cp_doc(**{"suppliers": {
       "Jeenie Solutions": {"lastChecked": cp_today(), "items": [cp_item(
           headline="Remote Interpreting Platform Jeenie Valued at USD 34m in Series A",
           summary="Jeenie connects patients with limited English proficiency to healthcare "
                   "interpreters across the US.",
           match={"alias": "jeenie", "aliasStrength": "distinctive",
                  "sectorTerm": "healthcare", "relevanceTerm": "patients"},
           sources=[cp_src(publisher="Slator", url="https://slator.com/jeenie-series-a/"),
                    cp_src(publisher="MedCity News",
                           url="https://medcitynews.com/jeenie-series-a/")])]},
       "Convatec": {"lastChecked": cp_today(), "items": []}},
       "counts": {"suppliers": 2, "suppliersWithItems": 1, "items": 1, "sources": 2,
                  "resolvedLinks": 2, "redirectLinks": 0}}),
   "re-applying the printed match rule")
cp("a story matched on a bare surname the seed shares with nothing else, uncorroborated",
   cp_doc([cp_item(headline="Jeenie named one of the fastest growing US firms",
                   summary="The healthcare interpreting business ranked on the Inc. 5000 list.",
                   match={"alias": "jeenie"},
                   sources=[cp_src(publisher="MedCity News",
                                   url="https://medcitynews.com/jeenie-inc5000/"),
                            cp_src(publisher="Fierce Healthcare",
                                   url="https://fiercehealthcare.com/jeenie")])],
          **{"suppliers": {"Jeenie Solutions": {"lastChecked": cp_today(), "items": [cp_item(
                 headline="Jeenie named one of the fastest growing US firms",
                 summary="The healthcare interpreting business ranked on the Inc. 5000 list.",
                 match={"alias": "jeenie"},
                 sources=[cp_src(publisher="MedCity News",
                                 url="https://medcitynews.com/jeenie-inc5000/"),
                          cp_src(publisher="Fierce Healthcare",
                                 url="https://fiercehealthcare.com/jeenie")])]},
             "Convatec": {"lastChecked": cp_today(), "items": []}},
             "counts": {"suppliers": 2, "suppliersWithItems": 1, "items": 1, "sources": 2,
                        "resolvedLinks": 2, "redirectLinks": 0}}),
   "re-applying the printed match rule")

# --- the corroboration bar -------------------------------------------------
cp("a story carried by only one publisher",
   cp_doc([cp_item(sources=[cp_src()])]), "distinct publisher")
cp("a story whose two sources are the same publisher twice",
   cp_doc([cp_item(sources=[cp_src(), cp_src(url="https://www.medtechdive.com/news/other/")])]),
   "distinct publisher")

# --- THE SECOND INCIDENT: corroboration about the COMPANY, not the STORY ----
# 18/08/2026. refresh_company_press.cluster() grouped headlines on token overlap
# with a floor of two shared words, and a two-token company name supplied both.
# So two unrelated stories about one company clustered and each corroborated the
# other. 13 of 34 live items were affected. The live example below is real: the
# Imperial College robotics centre was published carrying Reuters and MedTech
# Dive as its corroboration, and both were covering the Integrity Orthopaedics
# ACQUISITION. The reader was told two publishers carried this story. They had not.
cp("corroborating links that carry a different story about the same company",
   cp_doc([cp_item(
       headline="Smith+Nephew and Imperial College London launch centre for surgical robotics",
       match={"alias": "convatec", "aliasStrength": "distinctive",
              "sectorTerm": "surgical", "relevanceTerm": "london"},
       sources=[
           cp_src(publisher="BioSpace",
                  url="https://www.biospace.com/press-releases/convatec-imperial-college-london-launch-centre-surgical-robotics"),
           cp_src(publisher="MedTech Dive",
                  url="https://www.medtechdive.com/news/convatec-acquire-integrity-orthopaedics/809570/"),
           cp_src(publisher="Reuters",
                  url="https://www.reuters.com/legal/transactional/convatec-buy-integrity-orthopaedics-450-million/")])]),
   "appear to carry a DIFFERENT story")

cp("a headline that is only the company's own name, presented as corroborated",
   cp_doc([cp_item(headline="Convatec",
                   sources=[cp_src(), cp_src(publisher="The Times",
                                             url="https://www.thetimes.com/business/article/convatec")])]),
   "fewer than two substantial words")

# The other half of the rule lives in CP_QUIET, below: it must NOT fire on genuine
# corroboration worded differently, nor on URLs that carry no slug to judge.

# --- links -----------------------------------------------------------------
cp("a source with no URL at all",
   cp_doc([cp_item(sources=[cp_src(url=""), cp_src(publisher="The Times",
                                                   url="https://thetimes.com/x")])]),
   "no usable URL")
cp("a Google News redirect dressed up as the publisher's own article",
   cp_doc([cp_item(sources=[cp_src(url="https://news.google.com/rss/articles/CBMiABC"),
                            cp_src(publisher="The Times", url="https://thetimes.com/x")])]),
   "still points at news.google.com")
cp("a source filed under a urlType that does not exist",
   cp_doc([cp_item(sources=[cp_src(urlType="resolved"),
                            cp_src(publisher="The Times", url="https://thetimes.com/x")])]),
   "not one of")
cp("a source with no publisher name",
   cp_doc([cp_item(sources=[cp_src(publisher=""),
                            cp_src(publisher="The Times", url="https://thetimes.com/x"),
                            cp_src(publisher="Reuters", url="https://reuters.com/x")])]),
   "no publisher name")

# --- dates and the empty state --------------------------------------------
cp("a press item with no ISO date",
   cp_doc([cp_item(date="")]), "no usable ISO date")
cp("a press item dated in the future",
   cp_doc([cp_item(date=cp_today(30))]), "has not happened yet")
cp("a supplier block with no lastChecked, so an empty panel reads as broken",
   cp_doc(**{"suppliers": {"Convatec": {"items": []},
                           "Jeenie Solutions": {"lastChecked": cp_today(), "items": []}},
             "counts": {"suppliers": 2, "suppliersWithItems": 0, "items": 0, "sources": 0,
                        "resolvedLinks": 0, "redirectLinks": 0}}),
   "no usable lastChecked")
cp("a lastChecked stamp in the future",
   cp_doc(**{"suppliers": {"Convatec": {"lastChecked": cp_today(9), "items": []},
                           "Jeenie Solutions": {"lastChecked": cp_today(), "items": []}},
             "counts": {"suppliers": 2, "suppliersWithItems": 0, "items": 0, "sources": 0,
                        "resolvedLinks": 0, "redirectLinks": 0}}),
   "has not happened yet")
cp("a file generated tomorrow", cp_doc(generated=cp_today(5)), "has not happened yet")

# --- the header/rows drift (the 14/08/2026 rebase defect) ------------------
cp("a counts header from one generation over rows from another",
   cp_doc(**{"counts": {"suppliers": 2, "suppliersWithItems": 1, "items": 9, "sources": 2,
                        "resolvedLinks": 2, "redirectLinks": 0}}),
   "but holds")
cp("a resolvedLinks count that does not match the links beneath it",
   cp_doc(**{"counts": {"suppliers": 2, "suppliersWithItems": 1, "items": 1, "sources": 2,
                        "resolvedLinks": 7, "redirectLinks": 0}}),
   "but holds")

# --- the printed rule and the honest partial sweep -------------------------
cp("a match rule edited in the file, away from the rule that ran",
   cp_doc(matchRule="stories are matched on the company name"), "not the rule")
cp("a file that publishes no rotation rule at all",
   cp_doc(rotationRule=""), "carries no rotationRule")
cp("a partial rotation that does not admit it is partial",
   cp_doc(coverage={"complete": False, "suppliersNeverChecked": 900,
                    "note": "Suppliers checked on rotation."}),
   "does not say so")
cp("press attached to a company no supplier record exists for",
   cp_doc(**{"suppliers": {"Nonesuch Surgical": {"lastChecked": cp_today(), "items": []},
                           "Convatec": {"lastChecked": cp_today(), "items": []},
                           "Jeenie Solutions": {"lastChecked": cp_today(), "items": []}},
             "counts": {"suppliers": 3, "suppliersWithItems": 0, "items": 0, "sources": 0,
                        "resolvedLinks": 0, "redirectLinks": 0}}),
   "does not resolve to any supplier record")
cp("evidence shown to the reader that is not the evidence the rule used",
   cp_doc([cp_item(match={"alias": "convatec group plc"})]),
   "not the evidence that was used")

CP_QUIET = [
    ("a good file", cp_doc()),
    # The other half of the 18/08/2026 corroboration invariant. Two publishers
    # WORD the same story differently, and both slugs carry it — this must pass.
    # The obvious wrong fix for that defect is to demand the slugs match closely,
    # which would block genuine corroboration; this case is what stops it.
    ("two publishers wording the SAME story differently",
     cp_doc([cp_item(
         headline="Convatec plans $1B investment in R&D in the US and UK",
         sources=[
             cp_src(publisher="MedTech Dive",
                    url="https://www.medtechdive.com/news/convatec-to-invest-1b-global-rd/"),
             cp_src(publisher="The Times",
                    url="https://www.thetimes.com/business/article/convatec-investment-rd-uk-sites")])])),
    # ID-style and section-only URLs carry no headline in the path, so there is
    # nothing to compare and the check must stay silent rather than guess.
    # Absence of evidence is not evidence. The live case that forced this:
    # koreabiomed.com/news/articleView.html?idxno scored five "words" — none of
    # which say anything about the story.
    ("sources whose URLs are ID-based, carrying no slug to judge",
     cp_doc([cp_item(
         sources=[cp_src(publisher="MedWatch",
                         url="https://medwatch.com/News/medtech/article18754541.ece"),
                  cp_src(publisher="Korea Biomedical Review",
                         url="https://www.koreabiomed.com/news/articleView.html?idxno")])])),
    # The honest empty state is the WHOLE POINT of lastChecked. It must never fail.
    ("a supplier checked with nothing meeting the bar",
     cp_doc(**{"suppliers": {"Convatec": {"lastChecked": cp_today(), "items": []},
                             "Jeenie Solutions": {"lastChecked": cp_today(), "items": []}},
               "counts": {"suppliers": 2, "suppliersWithItems": 0, "items": 0, "sources": 0,
                          "resolvedLinks": 0, "redirectLinks": 0}})),
    # A link that would not resolve is KEPT and MARKED. That is the honest state,
    # not a failure — a gate that failed on it would push somebody to mislabel it.
    ("an unresolved redirect, correctly marked as one",
     cp_doc([cp_item(sources=[
         cp_src(urlType="google-news-redirect",
                url="https://news.google.com/rss/articles/CBMiABC"),
         cp_src(publisher="The Times", url="https://thetimes.com/x")])],
         **{"counts": {"suppliers": 2, "suppliersWithItems": 1, "items": 1, "sources": 2,
                       "resolvedLinks": 1, "redirectLinks": 1}})),
    ("a partial rotation that says so",
     cp_doc(coverage={"complete": False, "suppliersNeverChecked": 900,
                      "note": "INCOMPLETE: 900 of 1216 suppliers have not been reached yet."})),
]


def company_press_cases():
    """The press gate, driven directly."""
    import importlib
    v = importlib.import_module("verify")
    failures = 0

    for name, doc, want in CP_CASES:
        v.fails[:] = []
        v.warns[:] = []
        v.check_company_press(doc, CP_SEED)
        text = " ".join(m for _, m in v.fails)
        if not v.fails:
            print("HOLE  %s — the gate PASSED this. It should not." % name); failures += 1
        elif want.lower() not in text.lower():
            print("WEAK  %s — rejected, but not for the expected reason (%r missing)"
                  % (name, want)); failures += 1
        else:
            print("ok    %s" % name)

    for name, doc in CP_QUIET:
        v.fails[:] = []
        v.warns[:] = []
        v.check_company_press(doc, CP_SEED)
        if v.fails:
            print("HOLE  %s — FALSE FAIL: %s"
                  % (name, " ".join(m for _, m in v.fails)[:220])); failures += 1
        else:
            print("ok    %s — no false failure" % name)

    # The no-op. The feature is optional, so an absent file must gate nothing.
    v.fails[:] = []
    v.warns[:] = []
    v.check_company_press(None, CP_SEED)
    if v.fails:
        print("HOLE  an absent company-press.json must gate nothing"); failures += 1
    else:
        print("ok    an absent company-press.json gates nothing")

    return failures


def company_awards_cases():
    """The award gate, driven directly."""
    import importlib
    v = importlib.import_module("verify")
    failures = 0

    for name, doc, js, want in CA_CASES:
        v.fails[:] = []
        v.warns[:] = []
        v.check_company_awards(doc, CA_SEED, js)
        text = " ".join(m for _, m in v.fails)
        if not v.fails:
            print("HOLE  %s — the gate PASSED this. It should not." % name); failures += 1
        elif want.lower() not in text.lower():
            print("WEAK  %s — rejected, but not for the expected reason (%r missing)"
                  % (name, want)); failures += 1
        else:
            print("ok    %s" % name)

    for name, doc, js in CA_QUIET:
        v.fails[:] = []
        v.warns[:] = []
        v.check_company_awards(doc, CA_SEED, js)
        if v.fails:
            print("HOLE  %s — FALSE FAIL: %s"
                  % (name, " ".join(m for _, m in v.fails)[:220])); failures += 1
        else:
            print("ok    %s — no false failure" % name)

    # The stale-quarantine WARNING. A seed that has since gained the alias means
    # real awards are missing from the page — a coverage miss, not a false
    # claim, so it must warn and must NOT block the unattended workflows.
    v.fails[:] = []
    v.warns[:] = []
    stale = ca_doc(**{"unmatched": [ca_row(company=None, reason="no Hub company matches")],
                      "counts": {"companies": 1, "awardRows": 1, "unmatched": 1,
                                 "ambiguous": 0}})
    v.check_company_awards(stale, CA_SEED, CA_GOOD_JS)
    warned = "rematch" in " ".join(m for _, m in v.warns).lower()
    if v.fails or not warned:
        print("HOLE  a quarantined award that now resolves is not reported as a stale "
              "quarantine (fails=%d, warned=%s)" % (len(v.fails), warned)); failures += 1
    else:
        print("ok    a quarantined award that now resolves warns, and does not block")

    # And the no-op. A check that nags before its data exists is a check people
    # mute — the same rule as the Company Report's no-op case.
    v.fails[:] = []
    v.warns[:] = []
    v.check_company_awards(None, CA_SEED, "")
    if v.fails or v.warns:
        print("HOLE  the award gate is not silent when neither half exists"); failures += 1
    else:
        print("ok    the award gate is a clean no-op while its files do not exist")

    v.fails[:] = []
    v.warns[:] = []
    return failures


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


# --------------------------------------------------------------------------
# HUB SEARCH INDEX
# --------------------------------------------------------------------------
# The index is built by a crawl, and a crawl fails quietly. Every case here is a
# state where data/hub-search-index.json still parses, still looks plausible in
# a diff, and still breaks search for every member — which is precisely why the
# gate has to hold them rather than a person spotting them.
SEARCH_PATH = "data/hub-search-index.json"


def search_index(**over):
    """A minimal but valid index, stamped so only the fault under test fails."""
    sys.path.insert(0, "scripts")
    import stamp_notice
    doc = {
        "_notice": stamp_notice.notice_for("hub-search-index.json"),
        "generated": "2026-08-06T20:00:00Z",
        "dataAsOf": "2026-08-06",
        "pages": [{
            "id": 1874, "t": "Value-Based Procurement",
            "u": "/medical-sales-hub/value-based-procurement/",
            "sec": [{"h": "THE FIVE VALUE DOMAINS", "a": "vbp-domains",
                     "w": "chain efficiency patient purpose social staff supply value"}],
        }],
        "records": [{"t": "Coloplast", "u": "/medical-sales-hub/suppliers/#q=Coloplast",
                     "k": "coloplast urology continence", "c": "Supplier"}],
    }
    doc.update(over)
    return doc


def write_search(doc):
    if not os.path.exists(SEARCH_PATH):
        CREATED.append(SEARCH_PATH)
    json.dump(doc, open(SEARCH_PATH, "w"), indent=1, ensure_ascii=False)


@case("a search index with no pages at all (a crawl that returned nothing)")
def _(tmp):
    write_search(search_index(pages=[]))
    return "no pages"


@case("a search index that swallowed the page header, so everything matches everything")
def _(tmp):
    doc = search_index()
    doc["pages"][0]["sec"].append({
        "h": "NAV", "a": "",
        "w": "briefings careers conferences downloads frameworks glossary icons "
             "pathways podcasts reference theatres trackers",
    })
    write_search(doc)
    return "page header in its words"


@case("a search index carrying the Live Desk's hourly rows, stale within the day")
def _(tmp):
    doc = search_index()
    doc["pages"].append({
        "id": 675, "t": "Medical Sales Intelligence Hub · Live Desk",
        "u": "/medical-sales-hub/",
        "sec": [{"h": "MHRA ALERTS & RECALLS", "a": "",
                 "w": "03 aug critical down east incident kent stood trust"}],
    })
    write_search(doc)
    return "hourly rows"


@case("a search index with readable prose put back into a section")
def _(tmp):
    # The exact regression the word bag exists to prevent: someone adds a text
    # field to get the quoted snippet line back, and this PUBLIC file starts
    # carrying the paid Hub's prose again.
    doc = search_index()
    doc["pages"][0]["sec"][0]["x"] = ("Social value, efficiency, patient and staff, supply "
                                      "chain and purpose are the five value domains.")
    write_search(doc)
    return "unexpected field"


@case("a search index whose word bag kept its original order, so the prose survives")
def _(tmp):
    doc = search_index()
    doc["pages"][0]["sec"][0]["w"] = "social value efficiency patient staff supply chain purpose"
    write_search(doc)
    return "unsorted or duplicated word bag"


@case("a search index pointing results off the Hub")
def _(tmp):
    doc = search_index()
    doc["pages"][0]["u"] = "https://example.invalid/somewhere/"
    write_search(doc)
    return "absolute or off-site URL"


@case("a search index that collapsed to a fraction of the pages it had")
def _(tmp):
    # Only meaningful once there is a committed index to compare against.
    old = subprocess.run(["git", "show", "HEAD:" + SEARCH_PATH],
                         capture_output=True, text=True)
    if old.returncode != 0:
        return None
    try:
        prev = json.loads(old.stdout)
    except ValueError:
        return None
    if len(prev.get("pages") or []) < 10:
        return None
    write_search(search_index())        # one page, against a committed many
    return "drops from"


# --------------------------------------------------------------------------
# Trust pressures. These figures are copied from NHS England, the CQC and
# UKHSA and put in front of a rep who will quote them back to the trust that
# produced them. Every case below is a way that goes wrong quietly: a column
# that moved, a trust that no longer exists, or a number nobody re-fetched.
# --------------------------------------------------------------------------
PRESSURES_PATH = "data/trust-pressures.json"


def pressures(**over):
    d = json.load(open(PRESSURES_PATH))
    d.update(over)
    return d


def write_pressures(d):
    json.dump(d, open(PRESSURES_PATH, "w"), ensure_ascii=False, indent=1)


@case("a waiting-list percentage above 100, which means the column moved")
def _(tmp):
    d = pressures()
    code = next(iter(d["trusts"]))
    d["trusts"][code]["pct18"] = 118.4
    write_pressures(d)
    return "outside the possible range"


@case("a median wait of 900 weeks, copied from the wrong column")
def _(tmp):
    d = pressures()
    code = next(iter(d["trusts"]))
    d["trusts"][code]["spec"] = {"Trauma & Orthopaedics": 900}
    write_pressures(d)
    return "cannot be right"


@case("figures filed against a trust that no longer legally exists")
def _(tmp):
    d = pressures()
    d["trusts"]["RVJ"] = {"name": "North Bristol NHS Trust", "wl": 42031}
    write_pressures(d)
    return "not in the trust map"


@case("published figures nobody has rebuilt for two RTT cycles")
def _(tmp):
    old = datetime.date.today() - datetime.timedelta(days=120)
    write_pressures(pressures(asOf=old.strftime("%d/%m/%Y")))
    return "monthly return"


@case("a trust figure with no period recorded against it")
def _(tmp):
    d = pressures()
    d["periods"] = dict(d.get("periods") or {}, rtt=None)
    write_pressures(d)
    return "no period recorded"


# --- Hospital prescribing (NHSBSA). Cases 1 and 2 are the two defects the gate
# --- actually caught on the day the panel was built, 15/08/2026.

def _hp_index(**over):
    d = json.load(open("data/hospital-prescribing/index.json"))
    d.update(over)
    return d


def _hp_write(d):
    json.dump(d, open("data/hospital-prescribing/index.json", "w"), separators=(",", ":"))


def _hp_present():
    return os.path.exists("data/hospital-prescribing/index.json")


@case("a month NHSBSA never published, closed up instead of carried as null")
def _(tmp):
    if not _hp_present():
        return None
    d = _hp_index()
    d["periods"] = [p for p in d["periods"] if p != d["periods"][1]]
    _hp_write(d)
    return "gap in the monthly series"


@case("a molecule flagged as having a generic its shard does not contain")
def _(tmp):
    if not _hp_present():
        return None
    d = _hp_index()
    for row in d["substances"]:
        if row.get("g"):
            row["g"] = False
            _hp_write(d)
            return "brand/generic rule has broken"
    return None


@case("the evidence floor lowered on the published file but not in the builder")
def _(tmp):
    if not _hp_present():
        return None
    _hp_write(_hp_index(minBaselineItems=2))
    return "not the rule applied"


@case("the prescribing panel stopped printing its refusal on thin evidence")
def _(tmp):
    p = "app/hospital-prescribing.js"
    if not os.path.exists(p):
        return None
    src = open(p, encoding="utf-8").read()
    open(p, "w", encoding="utf-8").write(src.replace("too few to trend", "n/a"))
    return "no longer prints the refusal"


@case("the prescribing index shrunk to a handful of trusts")
def _(tmp):
    if not _hp_present():
        return None
    d = _hp_index()
    keep = dict(list(d["trusts"].items())[:20])
    d["trusts"] = keep
    _hp_write(d)
    return "Refusing a shrunken"




# --------------------------------------------------------------------------
# THE BRAND-MARK LAYER (data/company-logos.json + assets/logos/)
# --------------------------------------------------------------------------
# The fault this layer was built to fix was invisible: the report called
# logo.clearbit.com live, that host stopped resolving, every report fell through
# to the monogram, and nobody found out for weeks. Moving the marks into the repo
# only helps if something reads them before they publish — so each case below is
# a way that layer can be broken while still looking fine in a diff.
#
# These drive check_company_logos() directly against a throwaway root, because
# the check reads real files off disk and the suite must never leave a half-
# written PNG in assets/logos/ for the next person's verify.py to trip over.

CL_MARK = b"not really a png, but the gate hashes bytes rather than decoding them"
CL_SHA = hashlib.sha256(CL_MARK).hexdigest()

# A colour that is proven on both grounds: #0858b8 lightened for navy, itself on
# ivory. Every ratio below is the real recomputed figure, so the good document
# has to pass unchanged.
CL_GOOD_BRAND = {
    "c1": "#0858b8",
    "c2": "#0858b8",
    "accentOnNavy": "#266cc1",
    "accentOnIvory": "#0858b8",
    "contrastOnNavy": 3.25,
    "contrastOnIvory": 6.61,
    "contrastWhiteOnC2": 6.78,
    "source": "sampled from the pixels of the company's own brand mark at "
              "https://example.invalid/logo.png on 2026-08-18",
}


def cl_root(tmp, files=(("acme-medical.png", CL_MARK),)):
    """A throwaway repo root holding assets/logos/."""
    root = tempfile.mkdtemp(dir=tmp)
    d = os.path.join(root, "assets", "logos")
    os.makedirs(d)
    for name, blob in files:
        with open(os.path.join(d, name), "wb") as f:
            f.write(blob)
    return root


def cl_doc(**over):
    row = {
        "name": "Acme Medical",
        "slug": "acme-medical",
        "file": "assets/logos/acme-medical.png",
        "source": "https://acme.invalid/apple-touch-icon.png",
        "sourceWhy": "apple-touch-icon declared by the site",
        "domain": "acme.invalid",
        "format": "png",
        "w": 180, "h": 180,
        "fetched": "2026-08-18",
        "sha256": CL_SHA,
        "bytes": len(CL_MARK),
        "brand": dict(CL_GOOD_BRAND),
    }
    row.update(over.pop("row", {}))
    doc = {
        "generated": "2026-08-18",
        "rule": "Marks are fetched once at build time from the company's own website and "
                "stored in this repository; nothing is fetched live by the page.",
        "floorPx": 148,
        "counts": {"logos": 1, "refusals": 1, "logosWithBrandColour": 1 if row.get("brand") else 0},
        "logos": [row],
        "refusals": [{"name": "Beta Devices", "domain": "beta.invalid",
                      "reason": "site read, but it publishes no mark that clears the 148px floor",
                      "reasonCode": "no-usable-mark", "checked": "2026-08-18"}],
    }
    doc.update(over)
    return doc


CL_CASES = [
    ("a recorded mark that is not in the repo",
     lambda t: (cl_doc(row={"file": "assets/logos/missing.png"}), cl_root(t), None),
     "not in the repo"),

    ("a mark whose bytes changed after it was checked",
     lambda t: (cl_doc(), cl_root(t, (("acme-medical.png", b"swapped after the check"),)), None),
     "does not match the sha256"),

    ("a mark taken from a favicon service rather than the company's own site",
     lambda t: (cl_doc(row={"source": "https://icons.duckduckgo.com/ip3/acme.com.ico"}),
                cl_root(t), None),
     "favicon SERVICE"),

    ("a mark with no source URL",
     lambda t: (cl_doc(row={"source": ""}), cl_root(t), None),
     "has no source"),

    ("a mark with no fetch date",
     lambda t: (cl_doc(row={"fetched": ""}), cl_root(t), None),
     "has no fetched"),

    ("a header count that does not match the rows it summarises",
     lambda t: (cl_doc(counts={"logos": 214, "refusals": 1, "logosWithBrandColour": 1}),
                cl_root(t), None),
     "counts.logos"),

    ("a brand-colour count that does not match the rows carrying one",
     lambda t: (cl_doc(counts={"logos": 1, "refusals": 1, "logosWithBrandColour": 9}),
                cl_root(t), None),
     "logosWithBrandColour"),

    ("an accent published invisible on the ivory card ground",
     lambda t: (cl_doc(row={"brand": dict(CL_GOOD_BRAND, accentOnIvory="#f8e808",
                                          contrastOnIvory=None, contrastWhiteOnC2=None)}),
                cl_root(t), None),
     "on the ivory card ground"),

    ("an accent published invisible on the navy masthead",
     lambda t: (cl_doc(row={"brand": dict(CL_GOOD_BRAND, accentOnNavy="#081848",
                                          contrastOnNavy=None)}),
                cl_root(t), None),
     "on the navy masthead"),

    ("a contrast ratio printed next to a colour it does not describe",
     lambda t: (cl_doc(row={"brand": dict(CL_GOOD_BRAND, contrastOnNavy=9.9)}),
                cl_root(t), None),
     "recomputes to"),

    ("a brand colour that is not a hex colour",
     lambda t: (cl_doc(row={"brand": dict(CL_GOOD_BRAND, c1="navy blue")}), cl_root(t), None),
     "not a six-digit hex"),

    ("a published colour with nothing saying what it was sampled from",
     lambda t: (cl_doc(row={"brand": dict(CL_GOOD_BRAND, source="")}), cl_root(t), None),
     "no note saying what it was sampled from"),

    ("a company with no colour and no reason given",
     lambda t: (cl_doc(row={"brand": None},
                       counts={"logos": 1, "refusals": 1, "logosWithBrandColour": 0}),
                cl_root(t), None),
     "does not say why"),

    ("bytes shipping to members that no row ever draws",
     lambda t: (cl_doc(), cl_root(t, (("acme-medical.png", CL_MARK),
                                      ("orphan.png", b"never drawn"))), None),
     "named by no row"),

    ("a refusal with no reason",
     lambda t: (cl_doc(refusals=[{"name": "Beta Devices"}]), cl_root(t), None),
     "no name or no reason"),

    ("the same company recorded twice",
     lambda t: (dict(cl_doc(), counts={"logos": 2, "refusals": 1, "logosWithBrandColour": 2},
                     logos=[cl_doc()["logos"][0], cl_doc()["logos"][0]]), cl_root(t), None),
     "appears twice"),

    ("a mark stored outside assets/logos/",
     lambda t: (cl_doc(row={"file": "../../etc/passwd"}), cl_root(t), None),
     "points outside assets/logos/"),

    ("the layer published with no rule stated",
     lambda t: (cl_doc(rule=""), cl_root(t), None),
     "states no rule"),

    ("the renderer reaching for a live third-party logo host again",
     lambda t: (cl_doc(), cl_root(t),
                "var U='https://logo.clearbit.com/'+d;function safe(x){}0.03928 --mcr-accent-ink"),
     "logo.clearbit.com"),

    ("the renderer losing its contrast guard",
     lambda t: (cl_doc(), cl_root(t), "var x=1; /* --mcr-accent-ink */"),
     "lost its contrast guard"),

    ("the two accents collapsed back into one",
     lambda t: (cl_doc(), cl_root(t), "function safe(a){} 0.03928 --mcr-accent:"),
     "--mcr-accent-ink"),
]

CL_QUIET = [
    ("a whole, honest logo layer",
     lambda t: (cl_doc(), cl_root(t), "function safe(a){} 0.03928 --mcr-accent-ink:red")),
    ("a company whose mark yielded no colour, with the refusal recorded",
     lambda t: (cl_doc(row={"brand": None,
                            "brandRefused": "no saturated colour in the mark — a monochrome "
                                            "logo yields no brand colour"},
                       counts={"logos": 1, "refusals": 1, "logosWithBrandColour": 0}),
                cl_root(t), None)),
]


def company_logos_cases(tmp):
    """The brand-mark gate, driven directly."""
    import importlib
    v = importlib.import_module("verify")
    failures = 0

    for name, build, want in CL_CASES:
        doc, root, js = build(tmp)
        v.fails[:] = []
        v.warns[:] = []
        v.check_company_logos(doc, js, root)
        text = " ".join(m for _, m in v.fails)
        if not v.fails:
            print("HOLE  %s — the gate PASSED this. It should not." % name); failures += 1
        elif want.lower() not in text.lower():
            print("WEAK  %s — rejected, but not for the expected reason (%r missing)"
                  % (name, want)); failures += 1
        else:
            print("ok    %s" % name)

    for name, build in CL_QUIET:
        doc, root, js = build(tmp)
        v.fails[:] = []
        v.warns[:] = []
        v.check_company_logos(doc, js, root)
        if v.fails:
            print("HOLE  %s — FALSE FAIL: %s"
                  % (name, " ".join(m for _, m in v.fails)[:220])); failures += 1
        else:
            print("ok    %s — no false failure" % name)

    # The no-op. The layer is optional: absent, every company draws the monogram.
    v.fails[:] = []
    v.warns[:] = []
    v.check_company_logos(None, "", tmp)
    if v.fails:
        print("HOLE  an absent company-logos.json must gate nothing"); failures += 1
    else:
        print("ok    an absent company-logos.json gates nothing")

    return failures

def main():
    # THE CONTACT FIXTURE, first of all.
    #
    # data/trust-contacts.json and data/people-moves.json hold real named NHS
    # staff. They live in the PRIVATE repo, so in this public repo they are
    # absent — and every contacts, tags and moves check in verify.py is written
    # to no-op on a missing file, which is correct for publishing and useless for
    # testing. Absent files meant a third of this suite skipped and the public
    # gate ran untested.
    #
    # So when they are missing, a synthetic pair is manufactured for the run:
    # invented names, .invalid addresses, real trust codes. When they ARE present
    # (the private repo) write() returns nothing and the real data is used
    # untouched — the suite must never quietly test invented people in the one
    # place the real ones live.
    #
    # Written BEFORE the snapshot below on purpose, so restore() puts the fixture
    # back between cases like any other data file. That also means restore()
    # cannot remove it at the end, so the paths are deleted by hand in `finally`.
    _install_cleanup()
    synthetic = fixture_contacts.write()
    _register_cleanup(lambda: fixture_contacts.remove(synthetic))
    if synthetic:
        print("fixture: synthetic %s (invented names, no real person)"
              % " + ".join(os.path.basename(p) for p in synthetic))
    try:
        return _run(tempfile.mkdtemp())
    finally:
        _cleanup()


# CLEAN UP EVEN WHEN THE RUN IS KILLED.
#
# Every case mutates a real file and restore() puts it back. That only happened at
# the end of a completed run, so a Ctrl-C, a CI timeout (this suite runs ~120
# gates and the workflow allows 30 minutes) or a killed shell left the repo
# holding a deliberately broken data file — and, once the fixture existed, two
# files of invented NHS contacts sitting in data/ where a later `git add -A` would
# find them. The next person's verify.py then fails on data nobody edited, which
# is precisely the accumulating-damage failure the derived watch list was built to
# stop; it just arrived by a different door.
#
# So the restore is registered as soon as there is something to undo, and runs on
# a normal exit, an exception, SIGINT or SIGTERM. It is idempotent: restoring
# files that are already correct copies the same bytes back.
_CLEANUP = []


def _register_cleanup(fn):
    _CLEANUP.append(fn)


def _cleanup(*_a):
    while _CLEANUP:
        try:
            _CLEANUP.pop()()
        except Exception:                                   # noqa: BLE001
            pass                    # a failing cleanup must not mask the real error


def _install_cleanup():
    atexit.register(_cleanup)
    for sig in (signal.SIGINT, signal.SIGTERM):
        prev = signal.getsignal(sig)

        def handler(signum, frame, _prev=prev):
            _cleanup()
            if callable(_prev) and _prev not in (signal.SIG_IGN, signal.SIG_DFL):
                return _prev(signum, frame)
            sys.exit(128 + signum)

        signal.signal(sig, handler)


def _run(tmp):
    # Snapshot every file a case might touch, so the repo is left untouched.
    #
    # This list used to be hand-maintained, and on 05/08/2026 the first new data
    # file in months (compare-suppliers.json) was not on it. Its cases mutated
    # the real file, restore() skipped it, and the damage ACCUMULATED across
    # cases until the gate failed on data nobody had knowingly edited — and
    # because the file was still untracked, `git checkout` could not undo it
    # either. So the watch list is now derived: every JSON file in data/ is
    # snapshotted, whether or not anyone remembered to add it.
    # Walked RECURSIVELY since 15/08/2026. data/hospital-prescribing/ is the first
    # dataset kept in a subdirectory, and a top-level listdir could not see it — so a
    # case that mutated a shard would never have been restored, which is the exact
    # accumulating-damage failure this list was derived to prevent.
    watched = FILES + sorted(
        os.path.join(dp, n)
        for dp, _dn, fns in os.walk("data") for n in fns if n.endswith(".json")
    ) + sorted(
        # app/*.js too: a case that edits comptab.js used to leave the repo
        # broken, because only mst-logic.js was named in FILES.
        os.path.join("app", n) for n in os.listdir("app") if n.endswith(".js"))
    watched = list(dict.fromkeys(watched))          # de-dupe, keep order
    for f in watched:
        if os.path.exists(f):
            shutil.copy(f, os.path.join(tmp, f.replace("/", "_")))

    def restore():
        for f in watched:
            src = os.path.join(tmp, f.replace("/", "_"))
            if os.path.exists(src):
                shutil.copy(src, f)
        # A case may create a file the repo does not have yet —
        # data/company-financials.json is one, and writing it is the only way to
        # prove the Company Report check is wired into main() rather than merely
        # written. Copying a snapshot back cannot undo a creation, so those are
        # removed by name. Only paths a case registered, and only when nothing
        # was snapshotted for them, so a file another session lands mid-run is
        # never deleted here.
        for f in CREATED:
            if not os.path.exists(os.path.join(tmp, f.replace("/", "_"))) and os.path.exists(f):
                os.remove(f)

    # From here on the repo is mutable, so make the undo unconditional: a kill
    # between two cases must not leave a deliberately broken file behind.
    _register_cleanup(restore)

    # The gate must pass on the real, current data first — otherwise every
    # "caught it" below is meaningless.
    rc, out = gate()
    if rc != 0:
        print("SETUP FAILED — verify.py does not pass on the current data:\n" + out)
        restore(); return 1

    failures = skipped = 0
    for name, fn in CASES:
        restore()
        expect = fn(tmp)
        if isinstance(expect, Skip):
            print("SKIP  %s — %s" % (name, expect)); skipped += 1; continue
        if expect is None:
            print("SKIP  %s (fixture unavailable)" % name); skipped += 1; continue
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
    failures += company_report_cases()
    failures += company_report_noop_case()
    failures += company_awards_cases()
    failures += company_press_cases()
    failures += company_logos_cases(tmp)
    failures += concurrency_cases()

    rc, out = gate()
    if rc != 0:
        print("\nWARNING: the repo did not restore cleanly — check git status.")
        failures += 1
    print()
    # The tally is itself a count in prose that has to match the rows: 3 link
    # cases + 2 concurrency cases, 1 Company Report no-op, plus the award
    # gate's own stale-quarantine and no-op cases — and every case list
    # counted rather than typed.
    extras = (5 + 1 + 2 + len(CR_CASES) + len(CR_QUIET) + len(CA_CASES)
              + len(CA_QUIET) + len(CP_CASES) + len(CP_QUIET) + 1
              + len(CL_CASES) + len(CL_QUIET) + 1)
    # Skips are printed in the tally, not just in the rows. A suite that runs 60
    # of 74 cases and says "GATE HOLDS" is telling you less than it sounds like.
    ran = len(CASES) + extras - skipped
    print("GATE HOLDS — %d case(s) run, %d skipped." % (ran, skipped) if not failures
          else "GATE HAS %d HOLE(S) — fix verify.py before trusting it." % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
