#!/usr/bin/env python3
"""NHS App partner history — the append-only store behind drop-off detection.

WHY THIS FILE EXISTS
  data/digital-sources.json holds the CURRENT reading of NHS England's three NHS
  App partner lists (on 02/11/2026: live 80, integrating 25, planned 7). Because
  only the current reading is stored, a product that falls off the live list
  between two readings cannot be detected at all — the old row is simply gone.

  A product leaving the live list is the closest thing the digital side has to a
  withdrawal, so it is worth keeping. This script keeps it, on the pattern
  data/compare-issues.json already uses: an APPEND-ONLY store that only ever
  ADDS. It never edits and never removes an existing reading or departure, so a
  hand-written 'use' line on a departure survives every later run.

WHAT IT CANNOT DO YET, AND MUST NOT CLAIM
  Nothing is detectable until the store holds TWO readings. On the first run
  departures is empty, and that emptiness is not a finding — it means there is
  nothing to compare against. The file says so in `detectionRule`, and
  `promiseRule` records that this must not be promised on the Hub page until a
  second reading exists.

THE OVERLAP, WHICH LOOKS LIKE A BUG AND IS NOT
  The owner's three pages overlap: on the 02/11/2026 reading four partners
  appeared on two lists at once (TPP in Primary care was both live and
  integrating; CISCO/Healthcare Communications, EBO and University Hospital
  Southampton's My Medical Record were each both live and planned). So an entry
  does NOT have one stage. It holds a SET of stages, and leaving the live list
  is judged on the live list alone — never inferred from a stage looking lower.

IDENTITY
  A row's identity is organisation + product + section, all three as the owner
  spells them, normalised only for whitespace and case when keyed. Stage is NOT
  part of identity: stage is the thing being watched. The 4-tuple with stage is
  unique in the source, and the 3-tuple is unique per stage, which is what makes
  the set-of-stages model exact rather than lossy.

HOW A READING IS KEYED
  By a fingerprint of (verifiedOn, pages, entries). Re-running on an unchanged
  source adds nothing. A second, genuinely different reading taken on the same
  date is appended as its own reading rather than overwriting the first, because
  this store never edits.

    python3 scripts/build_nhs_app_history.py
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SRC = os.path.join(DATA, "digital-sources.json")
OUT = os.path.join(DATA, "nhs-app-partner-history.json")

# The owner's own three lists, in the order the owner presents them.
STAGE_ORDER = ["live", "integrating", "planned"]
WATCHED_STAGE = "live"

APPEND_ONLY_RULE = (
    "APPEND-ONLY store. A run only ADDS: a reading whose fingerprint is not "
    "already held, and a departure not already recorded. It never edits and "
    "never removes an existing reading or departure. Hand-written 'use' lines "
    "on a departure are added by editing this file directly and are never "
    "touched by automation."
)

DETECTION_RULE = (
    "A product leaving the live list can only be seen by comparing two "
    "readings. While this store holds one reading, departures is empty because "
    "there is nothing to compare against, not because nothing has left."
)

PROMISE_RULE = (
    "Not to be shown or promised on any Hub page until this store holds at "
    "least two readings."
)

OVERLAP_RULE = (
    "The owner's three lists overlap: one partner can appear on more than one "
    "of them at the same reading (four did on the 02/11/2026 reading). An "
    "entry therefore holds a SET of stages, not one stage, and leaving the "
    "live list is judged on the live list alone. A stage set that looks lower "
    "is never read as a demotion."
)

CLAIM_RULE = (
    "A partner no longer on the live list is a question to ask, not a "
    "withdrawal, a suspension, a failure or a judgement on the supplier. The "
    "owner states these lists are not an extensive directory of live services. "
    "A row may leave for reasons the owner does not publish, including a page "
    "edit."
)

IDENTITY_RULE = (
    "A row's identity is organisation + product + section as the owner spells "
    "them, normalised only for case and whitespace when keyed. Stage is not "
    "part of identity: stage is what is being watched."
)


def norm(value):
    """Whitespace- and case-normalise one field for keying. Empty for absent."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def entry_key(organisation, product, section):
    return "|".join([norm(organisation), norm(product), norm(section)])


def slug(text):
    out = re.sub(r"[^a-z0-9]+", "-", norm(text)).strip("-")
    return out or "unnamed"


def stage_sort(stages):
    known = [s for s in STAGE_ORDER if s in stages]
    other = sorted(s for s in stages if s not in STAGE_ORDER)
    return known + other


def read_entries(rows):
    """Collapse the source rows into one entry per identity, holding its stages."""
    by_key = {}
    for row in rows:
        organisation = row.get("organisation")
        product = row.get("product")
        section = row.get("section")
        key = entry_key(organisation, product, section)
        entry = by_key.get(key)
        if entry is None:
            entry = by_key[key] = {
                "k": key,
                "organisation": organisation,
                "product": product,
                "section": section,
                "stages": [],
            }
        stage = row.get("stage")
        if stage and stage not in entry["stages"]:
            entry["stages"].append(stage)
    for entry in by_key.values():
        entry["stages"] = stage_sort(entry["stages"])
    return [by_key[k] for k in sorted(by_key)]


def fingerprint(reading):
    """Content hash of one reading: date, pages and entries. Not a marker."""
    payload = json.dumps(
        {
            "verifiedOn": reading["verifiedOn"],
            "pages": reading["pages"],
            "entries": reading["entries"],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_reading(doc):
    app = doc.get("nhsApp") or {}
    rows = app.get("rows") or []
    entries = read_entries(rows)
    counts = {}
    for stage in STAGE_ORDER:
        counts[stage] = sum(1 for e in entries if stage in e["stages"])
    reading = {
        "verifiedOn": app.get("verifiedOn"),
        "sourceDataAsOf": doc.get("dataAsOf"),
        "sourceGenerated": doc.get("generated"),
        "pages": app.get("pages") or [],
        "rows": len(rows),
        "counts": counts,
        "entries": entries,
    }
    # A collapse is only ever two rows of the SAME identity on DIFFERENT lists
    # (11 identities did that on the 02/11/2026 reading, 12 extra memberships,
    # mostly because the owner writes "Secondary Care Appointments" on one page
    # and "Secondary care appointments" on another). Two rows of the same
    # identity AND the same stage would be a genuinely lossy merge, so refuse
    # rather than store a short reading: stage memberships must still add up to
    # the row count.
    memberships = sum(len(e["stages"]) for e in entries)
    if memberships != len(rows):
        raise SystemExit(
            "digital-sources.json: %d rows collapsed to %d stage memberships — "
            "two rows share an identity AND a stage, which this store would "
            "lose. Nothing written." % (len(rows), memberships))

    reading["fingerprint"] = fingerprint(reading)
    return reading


def live_keys(reading):
    return {e["k"] for e in reading["entries"] if WATCHED_STAGE in e["stages"]}


def departures_between(previous, current):
    """Entries on the live list in `previous` and not on it in `current`."""
    gone = live_keys(previous) - live_keys(current)
    now_by_key = {e["k"]: e for e in current["entries"]}
    out = []
    for entry in previous["entries"]:
        if entry["k"] not in gone:
            continue
        still = now_by_key.get(entry["k"])
        stages_now = list(still["stages"]) if still else []
        out.append({
            "id": "%s-%s" % (slug(entry["k"]), current["verifiedOn"]),
            "k": entry["k"],
            "organisation": entry["organisation"],
            "product": entry["product"],
            "section": entry["section"],
            "lastSeenLiveOn": previous["verifiedOn"],
            "firstMissingOn": current["verifiedOn"],
            "stagesNow": stages_now,
            "state": ("off every list" if not stages_now
                      else "no longer on the live list"),
            "autoDetected": True,
            "use": "",
        })
    return sorted(out, key=lambda d: d["id"])


def empty_store():
    return {
        "note": APPEND_ONLY_RULE,
        "rule": IDENTITY_RULE,
        "detectionRule": DETECTION_RULE,
        "promiseRule": PROMISE_RULE,
        "overlapRule": OVERLAP_RULE,
        "claimRule": CLAIM_RULE,
        "watchedStage": WATCHED_STAGE,
        "stageOrder": list(STAGE_ORDER),
        "readings": [],
        "departures": [],
    }


def append(store, doc):
    """Return (store, added_reading, new_departures). Never edits what is held."""
    reading = build_reading(doc)
    if not reading["verifiedOn"]:
        raise SystemExit("digital-sources.json: nhsApp.verifiedOn is missing")
    if not reading["entries"]:
        raise SystemExit("digital-sources.json: nhsApp.rows is empty, nothing to store")

    # The rules are the script's, not the file's: refresh them in place so a
    # wording fix reaches the store. Nothing under readings or departures is
    # touched by this.
    fresh = empty_store()
    for field in ("note", "rule", "detectionRule", "promiseRule", "overlapRule",
                  "claimRule", "watchedStage", "stageOrder"):
        store[field] = fresh[field]
    store.setdefault("readings", [])
    store.setdefault("departures", [])

    held = {r.get("fingerprint") for r in store["readings"]}
    if reading["fingerprint"] in held:
        return store, None, []

    previous = store["readings"][-1] if store["readings"] else None
    store["readings"].append(reading)

    new = []
    if previous is not None:
        known = {d.get("id") for d in store["departures"]}
        for departure in departures_between(previous, reading):
            if departure["id"] not in known:
                store["departures"].append(departure)
                new.append(departure)

    store["source"] = doc.get("source")
    store["sourceLicence"] = (doc.get("nhsApp") or {}).get("licence")
    store["termsUrl"] = doc.get("termsUrl")
    store["lastChecked"] = reading["verifiedOn"]
    store["dataAsOf"] = reading["verifiedOn"]
    store["readingCount"] = len(store["readings"])
    return store, reading, new


def main():
    with open(SRC, encoding="utf-8") as f:
        doc = json.load(f)

    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            store = json.load(f)
    else:
        store = empty_store()

    store, added, new = append(store, doc)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=1, ensure_ascii=False)
        f.write("\n")

    count = len(store["readings"])
    if added is None:
        print("nhs-app-partner-history.json: reading already held, nothing added "
              "(%d reading(s), %d departure(s))" % (count, len(store["departures"])))
    else:
        c = added["counts"]
        print("nhs-app-partner-history.json: reading %s added — %d entries "
              "(live %d, integrating %d, planned %d); %d new departure(s); "
              "%d reading(s) held"
              % (added["verifiedOn"], len(added["entries"]), c["live"],
                 c["integrating"], c["planned"], len(new), count))
        if count < 2:
            print("  one reading only: nothing can be detected yet, and nothing "
                  "goes on the Hub page until there are two")
    for departure in new:
        print("  left the live list: %s — %s (%s), %s"
              % (departure["organisation"], departure["product"] or "no product named",
                 departure["section"], departure["state"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
