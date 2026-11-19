#!/usr/bin/env python3
"""Fixture tests for scripts/build_nhs_app_history.py (no network, writes nothing).

What these guard, in the order a wrong answer would hurt a member:

  * APPEND-ONLY. A second run must not edit or drop a reading, a departure, or
    a hand-written 'use' line on a departure. That property is the whole point
    of the store, and it is the one a later convenience fix would break.
  * The overlap. The owner's three lists overlap — four partners were on two
    lists at once in the 02/11/2026 reading — so an entry holds a SET of
    stages. A model with one stage per entry silently loses the live row and
    would report a departure that never happened.
  * Leaving the live list is judged on the live list ALONE. A partner that is
    still live and has merely also appeared on the planned list has not left.
  * The first reading detects nothing, and says so rather than reporting zero
    departures as a clean bill.

  python3 test_nhs_app_history.py
"""
import copy
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("bnah", "scripts/build_nhs_app_history.py")
bnah = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bnah)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(label)
        print("FAIL  %s: got %r, wanted %r" % (label, got, want))
    else:
        print("ok    %s" % label)


def check_true(label, got):
    check(label, bool(got), True)


def doc(verified_on, rows, data_as_of=None):
    return {
        "generated": verified_on,
        "dataAsOf": data_as_of or verified_on,
        "source": "digital.nhs.uk (NHS England Digital) pages and data file",
        "termsUrl": "https://digital.nhs.uk/about-nhs-digital/terms-and-conditions",
        "nhsApp": {
            "licence": "Contains information from NHS England, Open Government Licence",
            "verifiedOn": verified_on,
            "pages": [
                {"stage": "live", "url": "https://example.invalid/live",
                 "pageLastEdited": "25 September 2026",
                 "rows": sum(1 for r in rows if r["stage"] == "live")},
                {"stage": "planned", "url": "https://example.invalid/planned",
                 "pageLastEdited": "16 September 2026",
                 "rows": sum(1 for r in rows if r["stage"] == "planned")},
            ],
            "rows": rows,
        },
    }


def row(stage, section, organisation, product=None):
    return {"stage": stage, "section": section,
            "organisation": organisation, "product": product}


# The first reading: three live partners, one of which (Overlap Co) is also on
# the planned list, exactly as four real partners were on 02/11/2026.
FIRST = [
    row("live", "Primary care", "Alpha Health", "Alpha Triage"),
    row("live", "Secondary care appointments", "Beta Systems", "Beta Portal"),
    row("live", "Secondary care appointments", "Overlap Co", "Healthcare Comms"),
    row("planned", "Secondary care appointments", "Overlap Co", "Healthcare Comms"),
    row("integrating", "Primary care", "Gamma Ltd"),
]

# 1. The first reading is stored and detects nothing.
store, added, new = bnah.append(bnah.empty_store(), doc("2026-11-02", FIRST))
check("the first reading is added", added is not None, True)
check("one reading is held", len(store["readings"]), 1)
check("the first reading finds no departures", new, [])
check("the first reading records no departures", store["departures"], [])
check_true("the detection rule says one reading detects nothing",
           "nothing to compare against" in store["detectionRule"])
check_true("the store refuses to be promised on a page yet",
           "two readings" in store["promiseRule"])

# 2. The overlap: five source rows collapse to four entries, and the partner on
#    two lists keeps BOTH stages. Losing the live stage here would invent a
#    departure at the next reading.
reading = store["readings"][0]
check("five rows collapse to four entries", len(reading["entries"]), 4)
entries = {e["k"]: e for e in reading["entries"]}
overlap = entries[bnah.entry_key("Overlap Co", "Healthcare Comms",
                                 "Secondary care appointments")]
check("the overlapping partner holds both stages", overlap["stages"],
      ["live", "planned"])
check("the live count counts the overlapping partner once",
      reading["counts"]["live"], 3)
check("the integrating count is the owner's own", reading["counts"]["integrating"], 1)
check("the planned count is the owner's own", reading["counts"]["planned"], 1)
check("the raw row count is kept beside the entries", reading["rows"], 5)
check_true("the overlap rule is published with the data",
           "more than one" in store["overlapRule"])

# 3. Re-running on the same source adds nothing at all.
before = copy.deepcopy(store)
store, added, new = bnah.append(store, doc("2026-11-02", FIRST))
check("an unchanged source adds no reading", added, None)
check("an unchanged source adds no departure", new, [])
check("an unchanged source leaves the readings alone",
      store["readings"], before["readings"])

# 4. A hand-written 'use' line on a departure survives the next run. This is the
#    property compare-issues.json documents and the one automation would break.
store["departures"].append({
    "id": "hand-written-example-2026-11-09",
    "k": "hand|written|example",
    "organisation": "Hand Written Co",
    "product": "Example",
    "section": "Primary care",
    "lastSeenLiveOn": "2026-11-02",
    "firstMissingOn": "2026-11-09",
    "stagesNow": [],
    "state": "off every list",
    "autoDetected": False,
    "use": "Lou's own line. Automation must never touch this.",
})

# The second reading: Beta Systems has gone from every list, Overlap Co has come
# off the live list but is still planned, Alpha Health is unchanged, and a new
# partner has arrived live.
SECOND = [
    row("live", "Primary care", "Alpha Health", "Alpha Triage"),
    row("planned", "Secondary care appointments", "Overlap Co", "Healthcare Comms"),
    row("integrating", "Primary care", "Gamma Ltd"),
    row("live", "Primary care", "Delta New", "Delta App"),
]
store, added, new = bnah.append(store, doc("2026-11-09", SECOND))
check("the second reading is added", added is not None, True)
check("two readings are held", len(store["readings"]), 2)
check("the hand-written line is untouched",
      store["departures"][0]["use"],
      "Lou's own line. Automation must never touch this.")
check("the hand-written departure is not re-detected",
      store["departures"][0]["autoDetected"], False)

# 5. Two departures, and only two: the arrival is not one, and the partner that
#    is still live is not one.
found = {(d["organisation"], d["state"]) for d in new}
check("two departures are detected", len(new), 2)
check_true("the partner off every list is reported as such",
           ("Beta Systems", "off every list") in found)
check_true("the partner still planned is reported as off the live list only",
           ("Overlap Co", "no longer on the live list") in found)
check_true("the arrival is not reported as a departure",
           "Delta New" not in {d["organisation"] for d in new})
check_true("the unchanged live partner is not reported",
           "Alpha Health" not in {d["organisation"] for d in new})

beta = [d for d in new if d["organisation"] == "Beta Systems"][0]
check("a departure names when it was last live", beta["lastSeenLiveOn"], "2026-11-02")
check("a departure names when it went missing", beta["firstMissingOn"], "2026-11-09")
check("a departure off every list carries no stages", beta["stagesNow"], [])
check("an auto-detected departure is marked so", beta["autoDetected"], True)
check("an auto-detected departure leaves 'use' for a human", beta["use"], "")
overlap_gone = [d for d in new if d["organisation"] == "Overlap Co"][0]
check("a partner off the live list keeps the stages it still holds",
      overlap_gone["stagesNow"], ["planned"])

# 6. The same departure is never recorded twice, even though a third reading
#    still does not have Beta Systems on the live list.
THIRD = SECOND + [row("integrating", "Primary care", "Epsilon Co", "Epsilon")]
count_before = len(store["departures"])
store, added, new = bnah.append(store, doc("2026-11-16", THIRD))
check("the third reading is added", added is not None, True)
check("a partner that left a reading ago is not reported again", new, [])
check("no departure is duplicated", len(store["departures"]), count_before)
check("three readings are held", len(store["readings"]), 3)
check("the store counts its readings", store["readingCount"], 3)
check("the store carries the latest reading date", store["lastChecked"], "2026-11-16")

# 7. A departure that is a genuinely new event IS recorded, so the de-duplication
#    above cannot be passing by refusing everything.
FOURTH = [r for r in THIRD if r["organisation"] != "Alpha Health"]
store, added, new = bnah.append(store, doc("2026-11-23", FOURTH))
check("a new departure at a later reading is recorded", len(new), 1)
check("the new departure is the partner that just left",
      new[0]["organisation"], "Alpha Health")
check("the new departure dates from the reading before it",
      new[0]["lastSeenLiveOn"], "2026-11-16")

# 8. Identity ignores case and stray whitespace but keeps the owner's spelling.
check("keys are case- and whitespace-normalised",
      bnah.entry_key("  Alpha   Health ", "Alpha Triage", "Primary Care"),
      bnah.entry_key("alpha health", "alpha triage", "primary care"))
first_entry = [e for e in store["readings"][0]["entries"]
               if e["organisation"] == "Alpha Health"][0]
check("the owner's own spelling is kept on the entry",
      first_entry["organisation"], "Alpha Health")
check("a missing product is kept as absent, not invented",
      entries[bnah.entry_key("Gamma Ltd", None, "Primary care")]["product"], None)

# 9. Stage is not part of identity: the same partner on two lists is ONE entry,
#    which is what makes the live-list test exact.
check("stage is not part of the key",
      bnah.entry_key("Overlap Co", "Healthcare Comms", "Secondary care appointments"),
      overlap["k"])

# 10. The honesty rules travel with the data and refuse the words a reader would
#     otherwise supply.
for key in ("note", "rule", "detectionRule", "promiseRule", "overlapRule",
            "claimRule"):
    check_true("%s is published with the data" % key, bool(store.get(key)))
check_true("the append-only rule says it never edits or removes",
           "never edits" in store["note"] and "never removes" in store["note"])
check_true("the claim rule refuses to call a departure a withdrawal",
           "not a withdrawal" in store["claimRule"])
check_true("the claim rule allows for a mere page edit",
           "page edit" in store["claimRule"])
check("the watched stage is the live list", store["watchedStage"], "live")
check("the source is carried", store["source"],
      "digital.nhs.uk (NHS England Digital) pages and data file")
check_true("the licence is carried", bool(store["sourceLicence"]))

# 11. The owner spells the same section two ways across its own pages
#     ("Secondary care appointments" / "Secondary Care Appointments" — nine
#     partners on the 02/11/2026 reading). Those are one partner on two lists,
#     not two partners, so they collapse.
CASED = [
    row("live", "Secondary care appointments", "Netcall", "PatientHub"),
    row("integrating", "Secondary Care Appointments", "Netcall", "PatientHub"),
]
cased, _, _ = bnah.append(bnah.empty_store(), doc("2026-12-07", CASED))
check("a section spelled two ways is still one partner",
      len(cased["readings"][0]["entries"]), 1)
check("that partner holds both lists",
      cased["readings"][0]["entries"][0]["stages"], ["live", "integrating"])

# 12. Two rows sharing an identity AND a stage would be a lossy merge, so the
#     build refuses rather than storing a reading that is quietly short.
LOSSY = [
    row("live", "Primary care", "Alpha Health", "Alpha Triage"),
    row("live", "Primary care", "Alpha Health", "Alpha Triage"),
]
try:
    bnah.append(bnah.empty_store(), doc("2026-12-14", LOSSY))
    check("a lossy same-stage merge is refused", "stored", "refused")
except SystemExit:
    check("a lossy same-stage merge is refused", "refused", "refused")

# 13. A reading with no rows is refused rather than stored as an empty list,
#     which would read as every partner having left at once.
try:
    bnah.append(bnah.empty_store(), doc("2026-11-30", []))
    check("an empty reading is refused", "stored", "refused")
except SystemExit:
    check("an empty reading is refused", "refused", "refused")

print()
if FAILURES:
    print("%d FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("all nhs-app-partner-history checks passed")
