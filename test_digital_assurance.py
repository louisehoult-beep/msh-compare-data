#!/usr/bin/env python3
"""Fixture tests for scripts/build_digital_assurance.py (no network).

Three of these guard mistakes the build actually made on 16/11/2026 and that a
reader of the page would have believed:

  * the toolkit-year cut, which decides whether a supplier is called BEHIND at
    all. Get it wrong by one year and every supplier on the previous version is
    accused of letting a cycle lapse.
  * the successor direction. The first build named Technology Enabled Care
    Services 2 as the thing to move on to when Technology Enabled Care Services
    3 closes, i.e. backwards, to an agreement that had already expired.
  * the sub-area casing in the question, which turned "Breast screening AI"
    into "breast screening ai" in a sentence the member reads out to a buyer.

And two guard the honesty rules the page rests on: an AMBIGUOUS supplier is
never counted as behind, and an alternative is never invented for a sub-area
that has no current peer.

  python3 test_digital_assurance.py
"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("bda", "scripts/build_digital_assurance.py")
bda = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bda)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(label)
        print("FAIL  %s: got %r, wanted %r" % (label, got, want))
    else:
        print("ok    %s" % label)


def check_true(label, got):
    check(label, bool(got), True)


DSPT = {
    "checked": "2026-11-16",
    "source": "DSPT Organisation Search CSV export",
    "sourceUrl": "https://www.dsptoolkit.nhs.uk/OrganisationSearch",
    "note": "Status is as published by DSPT on the checked date.",
    "suppliers": [
        {"name": "Current Co", "matchedOn": "CURRENT CO LTD", "odsCode": "A1",
         "dsptStatus": "2025-26 (version 8) - Standards met", "statusDate": "1 June 2026"},
        {"name": "Newest Co", "matchedOn": "NEWEST CO LTD", "odsCode": "A2",
         "dsptStatus": "2026-27 (version 9) - Standards exceeded", "statusDate": "1 July 2026"},
        {"name": "Lapsed AI", "matchedOn": "LAPSED AI LTD", "odsCode": "A3",
         "dsptStatus": "2024-25 (version 7) - Standards met", "statusDate": "2 June 2025"},
        {"name": "Niche AI", "matchedOn": "NICHE AI LTD", "odsCode": "A4",
         "dsptStatus": "2023-24 (version 6) - Standards met", "statusDate": "3 June 2024"},
        {"name": "Blank Co", "matchedOn": "BLANK CO LTD", "odsCode": "A5",
         "dsptStatus": "Not Published", "statusDate": ""},
        {"name": "Two Records", "matchedOn": "TWO RECORDS LTD", "ambiguous": True,
         "matches": [
             {"odsCode": "B1", "dsptName": "TWO RECORDS LTD",
              "dsptStatus": "2025-26 (version 8) - Standards met", "statusDate": "4 June 2026"},
             {"odsCode": "B2", "dsptName": "Two Records Limited",
              "dsptStatus": "2022-23 (version 5) - Standards met", "statusDate": "5 June 2023"}]},
    ],
    "unmatched": ["Zeta Health", "alpha systems"],
}

SEED = {"suppliers": [
    {"name": "Current Co", "specialities": ["Digital and medical IT"],
     "aliases": ["Current Co", "Current Co Ltd"]},
    {"name": "Newest Co", "specialities": ["Digital health / AI"]},
    {"name": "Lapsed AI", "specialities": ["Digital health / AI"]},
    # A sub-area of one. There is no other tracked supplier in it, so no
    # like-for-like alternative exists and none may be invented.
    {"name": "Niche AI", "specialities": ["Digital health / AI", "Breast screening AI"]},
    {"name": "Blank Co", "specialities": ["Digital and medical IT"]},
    {"name": "Two Records", "specialities": ["Digital and medical IT"]},
]}

FRAMEWORKS = {"dataAsOf": "2026-11-16", "source": "gca.gov.uk and find-tender", "frameworks": [
    {"name": "Technology Enabled Care Services 2", "reference": "SBS10144", "status": "live",
     "starts": "2023-01-09", "ends": "2027-10-10", "suppliers": ["CURRENT CO LTD"]},
    {"name": "Technology Enabled Care Services 3 (SBS10529)", "reference": "SBS10529",
     "starts": "2027-04-06", "ends": "2029-04-05", "suppliers": []},
    {"name": "Digital Pathology 2024 Framework", "reference": "FTS-1", "starts": None,
     "ends": None, "notVerified": "no dates published", "suppliers": []},
]}


def build(dspt=None, seed=None, frameworks=None):
    saved = bda.load
    data = {bda.DSPT: dspt or DSPT, bda.SEED: seed or SEED,
            bda.FRAMEWORKS: frameworks or FRAMEWORKS}
    bda.load = lambda p: data[p]
    try:
        return bda.build()
    finally:
        bda.load = saved


out = build()
rows = {r["name"]: r for r in out["suppliers"]}

# 1. The toolkit-year cut. The year rolls in June, so on a November reading
#    both the open year and the one before it are current.
check("2025-26 is current", rows["Current Co"]["kind"], "current")
check("2026-27 is current", rows["Newest Co"]["kind"], "current")
check("2024-25 is behind", rows["Lapsed AI"]["kind"], "behind")
check("2023-24 is behind", rows["Niche AI"]["kind"], "behind")
check("Not Published is its own kind", rows["Blank Co"]["kind"], "notPublished")
check("the cut is the documented one", bda.CURRENT_FROM_YEAR, 2025)

# 2. An ambiguous supplier claims no status and is NEVER counted as behind.
check("two records is ambiguous", rows["Two Records"]["kind"], "ambiguous")
check("ambiguous is not counted as behind", out["counts"].get("behind"), 2)
check("both conflicting records are shown", len(rows["Two Records"]["conflicting"]), 2)
check_true("the ambiguous question asks which legal entity",
           "legal entity" in rows["Two Records"]["question"])

# 3. No alternative is invented for a sub-area that has none.
# The keys are the spelled-out labels: see 4b below.
LANE = "Digital health / artificial intelligence (AI)"
NARROW = "Breast screening artificial intelligence (AI)"
alts = {a["speciality"]: a for a in rows["Niche AI"]["alternatives"]}
check("the lane offers current peers", sorted(alts[LANE]["current"]), ["Newest Co"])
check("the sub-area of one offers nobody", alts[NARROW]["current"], [])
check("the sub-area is marked narrow", alts[NARROW]["narrow"], True)
check("a behind supplier in the lane is not offered as an alternative",
      "Lapsed AI" in alts[LANE]["current"], False)

# 4. The question reads the sub-area as the seed spells it. Lower-casing it
#    turned "Breast screening AI" into "breast screening ai" on 16/11/2026.
check_true("the question keeps the area's own casing and spells the abbreviation out",
           "Breast screening artificial intelligence (AI)" in rows["Niche AI"]["question"])
check_true("the question spells the toolkit out in full",
           "Data Security and Protection Toolkit (DSPT)" in rows["Niche AI"]["question"])

# 4b. Rule 12: an abbreviation in an area label is spelled out where the
#     expansion is one this repo has read off a captured NHS source, and left
#     alone where it is not. A guessed expansion is worse than none.
check("a sub-area abbreviation is spelled out",
      bda.spell_out("Virtual wards / RPM"), "Virtual wards / remote patient monitoring (RPM)")
check("a label that is only an abbreviation is capitalised",
      bda.spell_out("EPR"), "Electronic patient record (EPR)")
check("an unknown abbreviation is left exactly as the seed spells it",
      bda.spell_out("Diabetes / CGM"), "Diabetes / CGM")
check("a label with no abbreviation is untouched",
      bda.spell_out("Wound care"), "Wound care")
check("the lane label is spelled out in the alternatives too",
      sorted(a["speciality"] for a in rows["Niche AI"]["alternatives"]),
      ["Breast screening artificial intelligence (AI)",
       "Digital health / artificial intelligence (AI)"])

# 5. Succession is directional: the earlier edition is never the successor of
#    the later one, and an undated agreement names no successor either way.
fw = {f["name"]: f for f in out["frameworks"]}
check("TECS 2 is succeeded by TECS 3",
      (fw["Technology Enabled Care Services 2"]["successor"] or {}).get("name"),
      "Technology Enabled Care Services 3 (SBS10529)")
check("TECS 3 is succeeded by nothing",
      fw["Technology Enabled Care Services 3 (SBS10529)"]["successor"], None)
check("an undated agreement names no successor",
      fw["Digital Pathology 2024 Framework"]["successor"], None)
check("an undated agreement keeps its notVerified reason",
      fw["Digital Pathology 2024 Framework"]["notVerified"], "no dates published")

# 6. Routes are matched on the supplier's own name or a curated alias, never
#    fuzzily, and the framework carries its tracked suppliers back.
check("a route is found through an alias",
      [r["name"] for r in rows["Current Co"]["routes"]], ["Technology Enabled Care Services 2"])
check("the framework lists the tracked supplier",
      fw["Technology Enabled Care Services 2"]["trackedSuppliers"], ["Current Co"])
check("a supplier on no route gets an empty list", rows["Niche AI"]["routes"], [])

# 7. Counts add up, and unmatched is reported as its own number, not folded in.
c = out["counts"]
check("tracked is matched plus unmatched", c["tracked"], len(out["suppliers"]) + c["unmatched"])
check("unmatched is counted", c["unmatched"], 2)
check("unmatched is sorted case-insensitively", out["unmatched"], ["alpha systems", "Zeta Health"])
check("current is counted", c["current"], 2)

# 8. The rules the page prints are present and carry the dates they rest on.
for key in ("yearRule", "claimRule", "matchRule", "unmatchedRule"):
    check_true("%s is published with the data" % key, bool(out.get(key)))
check("the DSPT reading date is carried", out["dsptCheckedOn"], "2026-11-16")
check("the frameworks date is carried", out["frameworksAsOf"], "2026-11-16")
check_true("the claim rule refuses to call a supplier non-compliant",
           "unsafe, non-compliant or barred" in out["claimRule"])

# 9. A current supplier is given no alternatives and no question: there is
#    nothing to raise, and offering a rival anyway would make the page a
#    competitor list rather than an assurance check.
check("a current supplier carries no alternatives", "alternatives" in rows["Current Co"], False)
check("a current supplier carries no question", "question" in rows["Current Co"], False)

print()
if FAILURES:
    print("%d FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("all digital-assurance checks passed")
