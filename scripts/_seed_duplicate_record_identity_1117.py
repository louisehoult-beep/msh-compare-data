#!/usr/bin/env python3
"""One-off seeder, framework-lots residual batch 17/11/2026.

WHY
---
The framework-lots gate's second warning counts 50 lot-source supplier names
that resolve to a Hub company the framework's OWN brief supplier list does not
name, so the lot has no brief row to attach to and no alias can reach it. Five
of those are not absences at all: they are the Hub holding what might be one
company under two records, with the brief naming one record and the lot source
naming the other. Each was checked at Companies House on 17/11/2026, under the
only merge evidence data/identity-vocabulary-policy.json accepts:

    "Two companies sharing a name is not evidence; two sharing a registration
     number is."  (parent-subsidiary-award-credit, guard)

One of the five is proved to be a single legal entity; two are proved to be
separate companies and were already recorded as such; two cannot be tied to a
registration number at all and stay apart. This script records what was found
on the records themselves, in `identityNote`, so the work is not repeated and so
the evidence for or against a merge sits beside the record it concerns.

It does NOT merge any record. A merge deletes a live Hub company page and
touches 17 data files per company (awards, financials, logos, search index,
compare, tariff, coverage ledger, press, products, calendar), so it is Lou's
call, not a side effect of a lot fix.

WHAT IT WRITES
--------------
  * Credenhill — `identityNote` and `companyNumberProof` (route 2:
    data/company-financials.json already holds 00547046 for this record as
    `probable` "name search ... NOT verified against a recorded number", and the
    company's own site publishes that same number, which is exactly what
    docs/COMPANY-REPORT-METHOD.md route 2 asks for).
  * Daylong Direct — `identityNote` only. No proof field: there is no
    data/company-financials.json record for this name to agree with, and
    scripts/confirm_company_numbers.py skips that case for the same reason
    ("nothing to agree with"). Writing one would start publishing Credenhill
    Ltd's accounts on a second Hub page before Lou has ruled on the merge.
  * Simulation Man and @SimulationMan Ltd — `identityNote` recording that the
    register holds no company named "Simulation Man", that @SIMULATIONMAN LTD
    12391166 is the only resembling registration, and what would settle it.
  * Uniphar Medtech — `identityNote` recording why the bare brief name cannot be
    tied to one registration.

Aliases are untouched. `aliases` DRIVES AWARD ROUTING
(backfill_seed_from_frameworks.py), so nothing here can re-route an award.

Idempotent: a record that already carries the note this script writes is left
alone, and an unchanged run writes no file.

    python3 scripts/_seed_duplicate_record_identity_1117.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like, describe  # noqa: E402

SEED = "data/supplier-seed.json"
INDEX = "data/supplier-index.json"
CHECKED = "2026-11-17"

CREDENHILL_EVIDENCE = (
    "Credenhill Ltd T/A Daylong Direct. Registered in England, company number "
    "00547046. Registered office: Unit 5 Soloman Road, Cossall Industrial "
    "Estate, Ilkeston, England, DE7 5UD."
)

# The shared finding, written from each record's own side.
ONE_ENTITY = (
    "Checked %s working the framework-lots residuals. The Hub's \"Credenhill\" and "
    "\"Daylong Direct\" records are ONE legal entity: Companies House 00547046 "
    "CREDENHILL LIMITED, active, incorporated 1 April 1955, registered office Unit 5 "
    "Soloman Road, Cossall Industrial Estate, Ilkeston, England, DE7 5UD "
    "(https://find-and-update.company-information.service.gov.uk/company/00547046, read %s). "
    "The company's own site states verbatim: \"%s\" (credenhill.co.uk, read %s), and "
    "daylongdirect.co.uk states \"Daylong Direct is the trading name for Credenhill "
    "Limited.\" (read %s). NHS Supply Chain's own Vascular Therapy and Associated "
    "Products brief (2023/S 000-012286) names the awarded supplier \"Daylong Direct "
    "(Credenhill)\", so the awarding source makes the same identification. "
    "NOT MERGED: a merge removes a live Hub company page and touches 17 data files, so "
    "it is Lou's decision, not a side effect of a lot fix. Until the records are one, "
    "two framework lots stay unattached: the Orthotics, Podiatry and Immobilisation lot "
    "source names \"Credenhill Limited\" while that brief's own supplier row is \"Daylong "
    "Direct\", and the Vascular Therapy lot source names \"Daylong Direct\" while that "
    "brief's row is \"Daylong Direct (Credenhill)\"."
) % (CHECKED, CHECKED, CREDENHILL_EVIDENCE, CHECKED, CHECKED)

SIMULATION = (
    "Checked %s working the framework-lots residuals. \"Simulation Man\" (this Hub "
    "record, from the Simulation Devices and Services brief 2022/S 000-031912) and "
    "\"@SimulationMan Ltd\" (from the Anaesthesia Machines, Ventilators, Neonatal "
    "Equipment and Phototherapy Systems brief 2026/S 000-008108) may be one company, "
    "and are NOT treated as one. Companies House holds NO company named \"Simulation "
    "Man\" (searches for \"simulation man\" and \"simulationman\", %s); the only "
    "resembling registration is @SIMULATIONMAN LTD 12391166, active, incorporated 8 "
    "January 2020, 83/84 Livingstone Road Walworth Business Park, Andover, Hampshire "
    "SP10 5QZ, SIC 70229 "
    "(https://find-and-update.company-information.service.gov.uk/company/12391166). "
    "Suggestive but not proof: on the Anaesthesia framework the brief's own supplier row "
    "is \"@SimulationMan Ltd\" while that framework's lot source names \"Simulation Man "
    "Ltd\" — one award under two spellings. The domain simulationman.co.uk is parked (it "
    "redirects to a lander, %s), so there is no route-2 registration proof for either "
    "record, and data/identity-vocabulary-policy.json accepts only a shared registration "
    "number as evidence that two records are one company. What would settle it: a "
    "company number on the supplier's own site, or a Find a Tender award notice for "
    "either framework naming the supplier with its registration number."
) % (CHECKED, CHECKED, CHECKED)

UNIPHAR = (
    "Checked %s working the framework-lots residuals. This record (the bare name NHS "
    "Supply Chain uses on the Minimally Invasive Surgery and Total Patient Assessment "
    "Device Solutions briefs) is NOT merged into \"Uniphar Medtech UK Ltd (Cardiac "
    "Services / Synapse Medical)\" (Companies House NI018037, confirmed), because the "
    "bare name cannot be tied to one registration. Companies House holds UNIPHAR MEDTECH "
    "UK LIMITED NI018037 and UNIPHAR MEDTECH HOLDINGS UK LIMITED NI040976 at the same "
    "Belfast address and no company named \"Uniphar Medtech Limited\" (search %s); NHS "
    "Supply Chain separately names \"Uniphar Medtech Ltd\" on the Perfusion brief and "
    "\"Uniphar Medtech Ltd t/a M.E.D. Surgical\", the group's IRISH entity, as a lot "
    "source elsewhere. This record's own companyNumberCandidate NI018037 came from a "
    "name search and carries its own caution; under "
    "data/identity-vocabulary-policy.json a shared name is not evidence and a shared "
    "registration number is, so a name-search candidate cannot carry a merge. Effect "
    "while they stay apart: the Airway Management lot source \"Uniphar Medtech UK "
    "Limited\" resolves here while that brief's row is the Cardiac Services record, and "
    "the Total Patient Assessment lot source \"Uniphar Medtech UK Limited T/A Cardiac "
    "Services\" resolves there while that brief's row is this one — both lots stay "
    "unattached. What would settle it: the registration number published on the "
    "supplier's own site (unipharmedtech.com is script-rendered and printed none on %s), "
    "or a Find a Tender award notice naming the awardee with its number."
) % (CHECKED, CHECKED, CHECKED)

PROOF = {
    "number": "00547046",
    "route": "website-registration",
    "url": "https://credenhill.co.uk/",
    "evidence": "site states registration number 00547046 (%s)" % CREDENHILL_EVIDENCE,
    "checkedOn": CHECKED,
}

# name -> fields to set on the record, in both files.
WRITES = {
    "Credenhill": {"identityNote": ONE_ENTITY, "companyNumberProof": PROOF},
    "Daylong Direct": {"identityNote": ONE_ENTITY},
    "Simulation Man": {"identityNote": SIMULATION},
    "@SimulationMan Ltd": {"identityNote": SIMULATION},
    "Uniphar Medtech": {"identityNote": UNIPHAR},
}


def apply(path):
    doc = json.load(io.open(path, encoding="utf-8"))
    changed, missing = 0, []
    by_name = {}
    for s in doc.get("suppliers") or []:
        if isinstance(s, dict) and s.get("name"):
            by_name.setdefault(s["name"], []).append(s)
    for name, fields in WRITES.items():
        recs = by_name.get(name) or []
        if not recs:
            missing.append(name)
            continue
        for rec in recs:
            for key, value in fields.items():
                if rec.get(key) == value:
                    continue
                rec[key] = value
                changed += 1
    if missing:
        print("%s: NOT FOUND, skipped: %s" % (path, ", ".join(sorted(missing))))
    if not changed:
        print("%s: already up to date, not rewritten" % path)
        return 0
    fmt, round_trips = write_like(path, doc)
    print("%s: %d field(s) written; %s" % (path, changed, describe(path, fmt, round_trips)))
    return changed


if __name__ == "__main__":
    total = apply(SEED) + apply(INDEX)
    print("done: %d field(s) written in all" % total)
