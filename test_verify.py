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
import datetime
import json, os, re, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)

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
    return "rose from"


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

# And the other half of the job: the lookalikes it must stay QUIET on. A false
# FAIL blocks the unattended refresh workflows from committing, and the first
# false FAIL on an honest empty state is the one that gets the empty state
# deleted to make a push go through.
CR_QUIET = [
    ("a good file and a good source", cr_financials(), CR_GOOD_JS),
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


def main():
    # Snapshot every file a case might touch, so the repo is left untouched.
    #
    # This list used to be hand-maintained, and on 05/08/2026 the first new data
    # file in months (compare-suppliers.json) was not on it. Its cases mutated
    # the real file, restore() skipped it, and the damage ACCUMULATED across
    # cases until the gate failed on data nobody had knowingly edited — and
    # because the file was still untracked, `git checkout` could not undo it
    # either. So the watch list is now derived: every JSON file in data/ is
    # snapshotted, whether or not anyone remembered to add it.
    tmp = tempfile.mkdtemp()
    watched = FILES + sorted(
        os.path.join("data", n) for n in os.listdir("data") if n.endswith(".json")
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
    failures += company_report_cases()
    failures += company_report_noop_case()
    failures += concurrency_cases()

    rc, out = gate()
    if rc != 0:
        print("\nWARNING: the repo did not restore cleanly — check git status.")
        failures += 1
    print()
    # The tally is itself a count in prose that has to match the rows: 3 link
    # cases + 2 concurrency cases, 1 Company Report no-op, and the Company
    # Report cases counted rather than typed.
    extras = 5 + 1 + len(CR_CASES) + len(CR_QUIET)
    print("GATE HOLDS — %d case(s)." % (len(CASES) + extras) if not failures
          else "GATE HAS %d HOLE(S) — fix verify.py before trusting it." % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
