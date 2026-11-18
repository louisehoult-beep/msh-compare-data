#!/usr/bin/env python3
"""Verdicts on the two lot-source names that reach two rows on one brief, and
the identityNotes that keep them from being re-asked. 18/11/2026 (pm).

Companion to scripts/_detach_nestle_beverages_lots_1118.py. Commit fd12566 read
both owner pages and both Companies House positions correctly and fixed the real
defect; this records the verdicts in the repo's own form, and records why one of
the two names goes back into quarantine.

  Urology and Bowel Management (2023/S 000-011173) — ATTACHED, stays.
      The brief states 57 suppliers and prints 57, naming both "Clinisupplies
      Ltd" and "Clinisupplies GB Limited". Companies House: CLINISUPPLIES
      LIMITED 04013240 (13 June 2000) and CLINISUPPLIES GB LIMITED 02503030
      (17 May 1990), one Watford address, two registrations — so two companies,
      and the shared address is not evidence otherwise. The award notice names
      "Clinisupplies Limited", 04013240's own registered name, which is the
      company this Hub record resolves to. Lots 1, 2, 3, 5 and 10 attach to the
      "Clinisupplies Ltd" row.

  Beverages, Confectionary and Snacks (2024/S 000-020103) — QUARANTINED, on
  purpose. The brief states 44 and prints 44, naming both "Nestle Ltd" and
      "Nestle UK". Neither row is a duplicate, so there is nothing to
      de-duplicate here either. The notice names "Nestle UK Ltd", which the
      territory tier narrows to the "Nestle UK" row — but the only Nestle-keyed
      Hub record is Nestle Health Science UK, the clinical nutrition arm, which
      holds a bare alias "nestle" and neither row verbatim.
      app/company-report.js renders a company, not a row, so that attachment put
      a confectionery and beverages Lot 1 and Lot 13 on that record's card. Its
      own identityNote had already ruled this shape out on 17/11/2026. Beverages
      is food, out of scope for Hub records under Lou's 17/11/2026 ruling, so no
      record is to be added for the entity the notice names, and the lots stay
      unattached.

Neither brief's supplier list is edited. It is a capture, verified against the
page's own stated count, and refresh_frameworks.parse_suppliers() refuses a list
that does not match that count.

Run (idempotent):
    python3 scripts/_adjudicate_two_brief_rows_one_key_1118.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from seed_format import write_like, describe  # noqa: E402

SEED = os.path.join(ROOT, "data", "supplier-seed.json")
INDEX = os.path.join(ROOT, "data", "supplier-index.json")
ADJ = os.path.join(ROOT, "state", "two-brief-rows-one-key-adjudication-1118.json")

CLINI_NOTE = (
    "Checked 2026-11-18 working the framework-lots residuals. NHS Supply Chain's "
    "Urology and Bowel Management brief (2023/S 000-011173) prints TWO rows, "
    "\"Clinisupplies Ltd\" and \"Clinisupplies GB Limited\", and states 57 suppliers, "
    "which is exactly what the capture holds — so neither row is a duplicate and the "
    "capture is not to be edited. Companies House, read the same day: CLINISUPPLIES "
    "LIMITED 04013240 and CLINISUPPLIES GB LIMITED 02503030, two registrations at one "
    "Watford address, so two companies; under data/identity-vocabulary-policy.json a "
    "shared name or address is not evidence, a shared number is. THIS RECORD IS "
    "04013240 — its own note resolves it there against the NHS Supply Chain "
    "catalogue's legal entity. Find a Tender award notice 032330-2023 names "
    "\"Clinisupplies Limited\", 04013240's registered name exactly, so Lots 1, 2, 3, 5 "
    "and 10 are this record's and are attached to the \"Clinisupplies Ltd\" row. "
    "\"Clinisupplies GB Limited\" MUST NOT become an alias here. RESIDUAL, recorded so "
    "it is not re-found as new: 02503030 has no Hub record, and company_match.key() "
    "still strips the \"GB\", so anything that resolves a brief row to a company routes "
    "that row here too — which is why this record's framework card can still list that "
    "spelling among the names it was matched on. Narrowing that is a change to "
    "company_match.resolve() and would move award routing repo-wide, so it is a "
    "separate question, not a loose end of this one. What would settle it: a Hub record "
    "for 02503030.")

NESTLE_ADD = (
    " Re-checked 2026-11-18 for the Beverages, Confectionary and Snacks lot source, "
    "and this verdict was applied to it. That brief prints TWO Nestle rows, \"Nestle "
    "Ltd\" and \"Nestle UK\" (plus \"Nestle Waters & Healthy Beverages UK\"), and states "
    "44 suppliers, which the capture matches — so neither is a duplicate row to remove. "
    "The award notice names \"Nestle UK Ltd\". attach_names()' territory tier narrows "
    "that to the \"Nestle UK\" row, and commit fd12566 attached Lots 1 and 13 there on "
    "the reading that a brief row is not a record. But app/company-report.js renders a "
    "COMPANY, not a row: coKey() strips \"ltd\" and \"uk\", so both rows collapse onto "
    "this record's bare \"nestle\" alias and fwLotLine() unions their lots — which put a "
    "confectionery and beverages Lot 1 and Lot 13 on this card, which is not the "
    "awardee. Reverted the same day by scripts/_detach_nestle_beverages_lots_1118.py, "
    "and the tier now requires the seed to hold BOTH the notice's name and the row "
    "verbatim on one record, which this record does not. Beverages Lots 1 and 13 stay "
    "unattached for the same reason Infant Feeding Lots 1 and 2 do.")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def apply_to(doc, label):
    changes = []
    for s in doc.get("suppliers") or []:
        if s.get("name") == "Clinisupplies":
            if s.get("identityNote") != CLINI_NOTE:
                s["identityNote"] = CLINI_NOTE
                changes.append("%s: identityNote on Clinisupplies" % label)
        elif s.get("name") == "Nestle Health Science UK":
            cur = s.get("identityNote") or ""
            if NESTLE_ADD.strip() not in cur:
                s["identityNote"] = (cur + NESTLE_ADD).strip()
                changes.append("%s: identityNote extended on Nestle Health Science UK" % label)
    return changes


DOC = {
    "_notice": ("Verdicts on the two lot-source supplier names that reach two rows on "
                "one framework's own brief supplier list. Written 18/11/2026."),
    "checkedOn": "2026-11-18",
    "rule": ("The brief's supplier list is a capture of the owner's published page, "
             "verified against that page's own stated supplier count, and is never "
             "edited to resolve a Hub-side ambiguity. A lot attaches to a brief row "
             "only where the seed holds BOTH the notice's name and that row verbatim "
             "on one record."),
    "frameworks": [
        {
            "framework": "Urology and Bowel Management",
            "reference": "2023/S 000-011173",
            "lotSourceName": "Clinisupplies Limited",
            "briefRows": ["Clinisupplies Ltd", "Clinisupplies GB Limited"],
            "statedSupplierCount": 57,
            "printedSupplierCount": 57,
            "duplicateRow": False,
            "companiesHouse": [
                {"name": "CLINISUPPLIES LIMITED", "number": "04013240",
                 "incorporated": "2000-06-13",
                 "address": "1 Blackmoor Lane, Watford, England, WD18 8GA"},
                {"name": "CLINISUPPLIES GB LIMITED", "number": "02503030",
                 "incorporated": "1990-05-17",
                 "address": "1 Blackmoor Lane, Croxley Park, Watford, England, WD18 8GA"},
            ],
            "verdict": "attached",
            "lots": ["Lot 1", "Lot 2", "Lot 3", "Lot 5", "Lot 10"],
            "why": ("Two real companies, not one row printed twice. The notice names "
                    "\"Clinisupplies Limited\", the registered name of 04013240, the "
                    "company the Hub's Clinisupplies record resolves to, and that record "
                    "holds both that name and the \"Clinisupplies Ltd\" row verbatim. "
                    "No row was picked any other way."),
            "residual": ("02503030 still has no Hub record and must not become an alias of "
                         "04013240 — different numbers are evidence they are distinct. It "
                         "also still key-collapses onto the Clinisupplies record wherever a "
                         "brief row is resolved to a company, because company_match.key() "
                         "strips the \"GB\". Narrowing that would move award routing "
                         "repo-wide, so it is a separate question."),
        },
        {
            "framework": "Beverages, Confectionary and Snacks",
            "reference": "2024/S 000-020103",
            "lotSourceName": "Nestle UK Ltd",
            "briefRows": ["Nestle Ltd", "Nestle UK",
                          "Nestle Waters & Healthy Beverages UK"],
            "statedSupplierCount": 44,
            "printedSupplierCount": 44,
            "duplicateRow": False,
            "verdict": "stays quarantined, on purpose",
            "lots": ["Lot 1", "Lot 13"],
            "why": ("Also two real rows, not a duplicate, so there is nothing to "
                    "de-duplicate. Food, which Lou ruled out of scope for Hub records on "
                    "17/11/2026, so no record is to be added for the entity the notice "
                    "names. The only Nestle-keyed Hub record, Nestle Health Science UK, is "
                    "the clinical nutrition arm and holds neither row verbatim — only a "
                    "bare \"Nestle\", which its own 17/11/2026 verdict rules out as a way "
                    "of naming one of several Nestle entities. Commit fd12566 attached the "
                    "lots to the \"Nestle UK\" row; because app/company-report.js renders a "
                    "company rather than a row, that published a confectionery and "
                    "beverages Lot 1 and Lot 13 on the clinical nutrition arm's card, and "
                    "it was reverted the same day."),
            "whatWouldChangeIt": ("NHS Supply Chain printing the entity in full on the "
                                  "brief, or a Find a Tender notice naming the awardee with "
                                  "its registration number."),
        },
    ],
    "warningAfterThisRun": ("The gate's TWO OR MORE rows line counts 1 name, "
                            "Beverages/\"Nestle UK Ltd\", decided above. It is a DECIDED "
                            "state, not a backlog item."),
}


def main():
    any_change = False
    for path, label in ((SEED, "data/supplier-seed.json"),
                        (INDEX, "data/supplier-index.json")):
        doc = load(path)
        changes = apply_to(doc, label)
        if not changes:
            print("%s: already applied, nothing written" % label)
            continue
        any_change = True
        fmt, rt = write_like(path, doc)
        print(describe(path, fmt, rt))
        for c in changes:
            print("   %s" % c)
    before = None
    if os.path.exists(ADJ):
        try:
            before = load(ADJ)
        except ValueError:
            before = None
    if before == DOC:
        print("state/two-brief-rows-one-key-adjudication-1118.json already current")
    else:
        fmt, rt = write_like(ADJ, DOC)
        print(describe(ADJ, fmt, rt))
    if not any_change:
        print("no supplier change needed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
