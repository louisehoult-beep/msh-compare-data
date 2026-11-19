#!/usr/bin/env python3
"""The 50 lot-source supplier names that DO reach a Hub record but whose
framework's own brief supplier list names no row that reaches it — worked name
by name at the Companies House bar, 17/11/2026.

WHAT THIS WARNING IS, AND WHY "RE-READ THE BRIEF" IS NOT THE FIX
----------------------------------------------------------------
verify._warn_unresolved_lot_names() sorts an unattached lot-source name by
whether it reaches a Hub supplier record. 50 of them do. attach_names()
resolves a source name to a supplier ON THAT BRIEF, so when the brief names no
row that reaches the same record the lot has nothing to attach to, and no alias
can reach a supplier the brief does not name.

Two things were already settled before this run and are not re-derived here:
  * Hand Hygiene — the brief states "There are 21 suppliers on the framework"
    and prints 21, while Find a Tender notice 000335-2023 awards 33. The
    brief's stated count matches its printed list, so the capture is not short:
    the owner's current list and the award notice genuinely differ.
  * Airway Management — the brief prints 54 supplier rows and its page states
    54. Also complete.
So these are per-name IDENTITY questions, not capture gaps. Each name below is
answered as one of: a genuine second name for a record the brief does name (fix
by alias), one company held twice under two records (fix by merge), or a
distinct company the brief genuinely does not name (left, with the verdict
written onto the record so the question is not asked again).

THE BAR, from data/identity-vocabulary-policy.json: two companies sharing a
NAME is not evidence; two sharing a REGISTRATION NUMBER is. A name-search
candidate cannot carry a merge — the ruling the same residuals produced earlier
today on "Uniphar Medtech", whose identityNote this run deliberately leaves
alone.

WHAT IT DOES
------------
TWO MERGES, each on a registration, not a name:

  1. "P.W.Coole & Son Limited T/A Surgical Holdings" -> "Surgical Holdings
     Limited". Companies House 03090951 SURGICAL HOLDINGS LIMITED, active,
     incorporated 14 August 1995, Unit 8 Parkside Centre, Potters Way, Temple
     Farm Industrial Estate, Southend On Sea, SS2 5SJ, records the dated
     PREVIOUS NAME "P.W. COOLE & SON LIMITED" (14 Aug 1995 - 27 Aug 2025) —
     read at Companies House 17/11/2026. data/company-financials.json already
     publishes 03090951 for "Surgical Holdings Limited" at
     matchConfidence "confirmed". Both Hub record names are therefore names of
     ONE registration, which is exactly the evidence the policy asks for. (A
     separate P.W. COOLE & SON LIMITED 11614775, incorporated 2018, is in
     Liquidation at a London insolvency address and carries no Surgical
     Holdings trading name; NHS Supply Chain's Electrosurgical brief row is
     "P.W.Coole & Son Limited T/A Surgical Holdings", which names the trading
     name and so names 03090951.)

  2. "Accrington Surgical Inst. Suppliers" -> "Accrington Surgical Instrument
     Suppliers Ltd". "Inst." is the brief's own abbreviation of "Instrument",
     and Companies House holds exactly ONE company it can abbreviate:
     ACCRINGTON SURGICAL INSTRUMENT SUPPLIERS LIMITED 05980916, active,
     incorporated 27 October 2006, Unit 6a Petre Court, Petre Road,
     Clayton-Le-Moors, Accrington, BB5 5JB (search 17/11/2026; the only other
     Accrington Surgical company, ACCRINGTON SURGICAL LTD 06046644, was
     dissolved 17 September 2015 and was itself folded into this same record by
     merge_duplicates.py on 24/08/2026 for the same reason). An abbreviation
     with one possible referent is not two companies sharing a name.

THREE ALIASES, where the brief writes the company's name as a bare word that
reaches no record, so the brief row itself is what cannot resolve:

  3. "Ortus" -> "Ortus Technology Limited". The External Defibrillation brief
     lists a bare "Ortus" with no lot, and Find a Tender award notice
     050296-2025 — the brief's own lot source — names "Ortus Technology
     Limited" on Lots 1, 2 and 3. No other framework brief names a bare
     "Ortus" (checked across data/frameworks.json 17/11/2026), so the alias
     cannot re-route another company's award.
  4. "BVM" -> "BVM Medical Ltd", and
  5. "MCT" -> "MCT Lifesciences Ltd". The Transcatheter Heart Valve brief
     lists bare "BVM" and "MCT" with no lot, and the NHS Supply Chain product
     matrix attached to that same brief names "BVM Medical Limited" (Lot 2) and
     "MCT Lifesciences Limited" (Lot 2). One document, the owner's own, writing
     one supplier two ways. Neither bare word appears on any other brief.

FORTY-FIVE VERDICTS, written to each record's identityNote and collected in
state/framework-lot-name-adjudication-1117.json, so the next run reads the
answer instead of re-deriving it.

WHAT IT DELIBERATELY DOES NOT TOUCH
-----------------------------------
  * data/frameworks.json supplier lists, data/framework-lots.json `unresolved`
    names and data/nhssc-launch-briefs.json: NHS Supply Chain's OWN words. The
    gate requires a supplierLots key to be a brief supplier verbatim, so the
    brief rows stay exactly as the owner writes them and resolve through the
    aliases instead.
  * `frameworks[].suppliers[]` inside data/speciality-panels/*.json and
    data/innovator-report.json: those are brief rows too, not record names.
  * The "Uniphar Medtech" and "Uniphar Medtech UK Ltd (Cardiac Services /
    Synapse Medical)" records: both were adjudicated earlier today and carry
    their own identityNote. Nothing here overwrites a note it did not write.
  * Non-clinical framework suppliers (catering, facilities and electrical,
    furniture, office supplies, food) get no new record. Lou has ruled; the
    Ambient Food names below are recorded as out of scope, not as a backlog.

Idempotent: a second run finds the merges done and the aliases present, reports
"already applied" and writes nothing.

    python3 scripts/_resolve_framework_lot_names_1117.py
"""
import io
import json
import os
import re
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like, describe  # noqa: E402

TODAY = "2026-11-17"
STATE = "state/framework-lot-name-adjudication-1117.json"

# ---------------------------------------------------------------- the merges

MERGES = [
    {
        "keep": "Surgical Holdings Limited",
        "fold": "P.W.Coole & Son Limited T/A Surgical Holdings",
        "number": "03090951",
        "aliases": [
            "P.W.Coole & Son Limited T/A Surgical Holdings",
            "P.W. Coole & Son Limited T/A Surgical Holdings",
            "P.W. Coole & Son Ltd",
            "P.W.Coole & Son Limited",
        ],
        "note": (
            "MERGED %(today)s working the framework-lots residuals: the Hub held one company as two "
            "records, \"Surgical Holdings Limited\" and \"P.W.Coole & Son Limited T/A Surgical "
            "Holdings\". Companies House 03090951 SURGICAL HOLDINGS LIMITED, active, incorporated "
            "14 August 1995, Unit 8 Parkside Centre, Potters Way, Temple Farm Industrial Estate, "
            "Southend On Sea, SS2 5SJ, records the dated previous name \"P.W. COOLE & SON LIMITED\" "
            "(14 Aug 1995 to 27 Aug 2025), read at Companies House %(today)s; "
            "data/company-financials.json already publishes 03090951 for this record at "
            "matchConfidence \"confirmed\". Both names are therefore names of ONE registration, "
            "which is the evidence data/identity-vocabulary-policy.json requires before two records "
            "become one — a shared registration number, never a shared name. A separate P.W. COOLE "
            "& SON LIMITED 11614775 (incorporated 2018) is in Liquidation at a London insolvency "
            "address and carries no Surgical Holdings trading name, so NHS Supply Chain's "
            "Electrosurgical Consumables brief row \"P.W.Coole & Son Limited T/A Surgical "
            "Holdings\" (2024/S 000-001161), which names the trading name, names 03090951. Both "
            "names are kept as aliases, so every award stays findable under the name its own source "
            "uses, and the brief row itself is untouched. Effect: the Electrosurgical Consumables "
            "lot source \"P.W.Coole & Son Limited\" (Lots 1 and 6) now has a brief row to attach to."
        ),
    },
    {
        "keep": "Accrington Surgical Instrument Suppliers Ltd",
        "fold": "Accrington Surgical Inst. Suppliers",
        "number": "05980916",
        "aliases": [
            "Accrington Surgical Inst. Suppliers",
            "Accrington Surgical Inst Suppliers",
        ],
        "note": (
            "MERGED %(today)s working the framework-lots residuals: the Hub held one company as two "
            "records, \"Accrington Surgical Instrument Suppliers Ltd\" and NHS Supply Chain's own "
            "abbreviation of it on the Procedure Packs brief, \"Accrington Surgical Inst. "
            "Suppliers\" (2023/S 000-031398). \"Inst.\" is an abbreviation of \"Instrument\", and "
            "Companies House holds exactly one company it can abbreviate: ACCRINGTON SURGICAL "
            "INSTRUMENT SUPPLIERS LIMITED 05980916, active, incorporated 27 October 2006, Unit 6a "
            "Petre Court, Petre Road, Clayton-Le-Moors, Accrington, BB5 5JB (name search %(today)s; "
            "the only other Accrington Surgical company, ACCRINGTON SURGICAL LTD 06046644, was "
            "dissolved 17 September 2015 and was itself folded into this record by "
            "merge_duplicates.py on 24/08/2026 on the same reading). An abbreviation with one "
            "possible referent is not two companies sharing a name, which is what "
            "data/identity-vocabulary-policy.json refuses to merge on. The abbreviation is kept as "
            "an alias and the brief row is untouched. Effect: the Procedure Packs lot source "
            "\"Accrington Surgical Instrument Suppliers Ltd\" (Lots 1 and 2) now has a brief row to "
            "attach to."
        ),
    },
]

# --------------------------------------------------------------- the aliases

ALIASES = [
    {
        "record": "Ortus Technology Limited",
        "add": ["Ortus"],
        "note": (
            "Checked %(today)s working the framework-lots residuals. NHS Supply Chain's External "
            "Defibrillation Devices brief lists this company as a bare \"Ortus\" with no lot, while "
            "that brief's own lot source — Find a Tender contract award notice 050296-2025 — names "
            "\"Ortus Technology Limited\" on Lots 1, 2 and 3. One owner's own documents writing one "
            "supplier two ways, so the brief's spelling is recorded here as an alias and the brief "
            "row is left as NHS Supply Chain writes it. No other framework brief names a bare "
            "\"Ortus\" (checked across data/frameworks.json %(today)s), so the alias cannot "
            "re-route another company's award; the Hub's separate \"Ortus-iHealth\" record is a "
            "different company and is named in full wherever it appears."
        ),
    },
    {
        "record": "BVM Medical Ltd",
        "add": ["BVM"],
        "note": (
            "Checked %(today)s working the framework-lots residuals. Two separate questions, two "
            "answers. (1) Transcatheter Heart Valve Repair, Replacement and Associated Devices: the "
            "brief lists this company as a bare \"BVM\" with no lot, while the NHS Supply Chain "
            "product matrix attached to that same brief (Product-Matrix-Transcatheter-Heart-Valve-"
            "09-September-2026-MT.xlsx) names \"BVM Medical Limited\" on Lot 2. One owner's own "
            "document writing one supplier two ways, so \"BVM\" is recorded here as an alias and "
            "the brief row is untouched. No other framework brief names a bare \"BVM\". (2) "
            "Neuromodulation Devices: the lot source names \"BVM MEDICAL LTD\" at Lot 3, but that "
            "brief's own supplier row is \"Creed Health - novated from BVM Medical Ltd\", which "
            "resolves to the separate \"Creed Medical Ltd\" record. A novation moves the contract to "
            "another company, so the Lot 3 holder on that framework is the novatee the brief names, "
            "not this record, and the lot correctly does not attach here."
        ),
    },
    {
        "record": "MCT Lifesciences Ltd",
        "add": ["MCT"],
        "note": (
            "Checked %(today)s working the framework-lots residuals. NHS Supply Chain's "
            "Transcatheter Heart Valve brief lists this company as a bare \"MCT\" with no lot, while "
            "the product matrix attached to that same brief (Product-Matrix-Transcatheter-Heart-"
            "Valve-09-September-2026-MT.xlsx) names \"MCT Lifesciences Limited\" on Lot 2. One "
            "owner's own document writing one supplier two ways, so \"MCT\" is recorded here as an "
            "alias and the brief row is left as NHS Supply Chain writes it. No other framework brief "
            "names a bare \"MCT\" (checked across data/frameworks.json %(today)s); the Endoscopy, "
            "Robotic Medical Equipment and Syringes briefs all name this company in full."
        ),
    },
]

# -------------------------------------------------------------- the verdicts
# Left unattached ON PURPOSE. One entry per Hub record; `names` lists the
# framework and the lot-source spelling that reaches it.

PRE = "Checked %(today)s working the framework-lots residuals. "
NOTICE_ONLY = (
    "The lot source names this company, but the framework's own brief supplier list carries no row "
    "that reaches this record (checked with scripts/company_match.py, the module "
    "verify._lot_name_resolver() itself uses). attach_names() can only attach a lot to a supplier ON "
    "THAT BRIEF, so there is nothing to attach to and no alias can create one — an alias would have "
    "to point at a brief row that does not exist. The brief and its lot source genuinely name "
    "different supplier sets; the owner's current list is what the Hub shows as the framework's "
    "suppliers. Left unattached. What would change it: NHS Supply Chain naming the company on the "
    "brief itself. Recorded in state/framework-lot-name-adjudication-1117.json."
)

VERDICTS = [
    {"record": "Advanced Medical Systems Ltd", "code": "distinct-registration",
     "names": [["Advanced Wound Care", "ADVANCED MEDICAL SYSTEMS LTD.", "Lot 2"]],
     "note": PRE + "The Advanced Wound Care lot source names \"ADVANCED MEDICAL SYSTEMS LTD.\", "
     "which reaches this record; the nearest row on that brief is \"Advanced Medical Solutions "
     "Ltd\", a DIFFERENT company. Companies House holds ADVANCED MEDICAL SYSTEMS LTD. 03476650, "
     "active, incorporated 5 December 1997, 10 Manor Park, Banbury, OX16 3TB (search %(today)s), "
     "which is not Advanced Medical Solutions. Two separate registrations, so under "
     "data/identity-vocabulary-policy.json these records stay apart and the lot stays unattached: "
     "a shared word in a name is not evidence."},

    {"record": "MedScience Distribution", "code": "notice-only",
     "names": [["Advanced Wound Care", "MedScience Distribution Ltd", "Lot 1, Lot 2"]],
     "note": PRE + "No row on the 56-supplier Advanced Wound Care brief shares a word with "
     "\"MedScience Distribution Ltd\". " + NOTICE_ONLY},

    {"record": "T.J Smith & Nephew Ltd", "code": "distinct-registration",
     "names": [["Advanced Wound Care", "T.J.SMITH AND NEPHEW,LIMITED", "Lot 1, Lot 2"]],
     "note": PRE + "The Advanced Wound Care lot source names \"T.J.SMITH AND NEPHEW,LIMITED\", "
     "which reaches this record (Companies House 00093994); the brief's own row is \"Smith & "
     "Nephew\", which reaches the separate \"Smith+Nephew\" record (00156031). Those two "
     "registrations were checked at Companies House on 17/11/2026 and found to be SEPARATE "
     "companies, recorded then. Two registrations, two records, so the lot has no row of this "
     "record's on that brief and stays unattached."},

    {"record": "Aquilant Endoscopy Limited", "code": "distinct-registration",
     "names": [["Airway Management Products and Associated Equipment", "Aquilant Endoscopy Limited", "Lot 1"]],
     "note": PRE + "The Airway Management lot source names \"Aquilant Endoscopy Limited\" at Lot 1; "
     "the brief's own Aquilant row is \"Aquilant Critical Care\", a separate record. Aquilant "
     "Endoscopy (03402556) and Aquilant Critical Care (02090807) were checked at Companies House on "
     "17/11/2026 and found to be SEPARATE companies, recorded then. The lot stays unattached."},

    {"record": "Hamilton Medical UK", "code": "distinct-registration",
     "names": [["Airway Management Products and Associated Equipment", "Hamilton Medical UK Ltd", "Lot 3"]],
     "note": PRE + "The Airway Management lot source names \"Hamilton Medical UK Ltd\" at Lot 3; the "
     "brief's own row is \"Hamilton Sales And Service UK Ltd\", which is its own record. Companies "
     "House holds these as TWO registrations: HAMILTON MEDICAL UK LTD 06836131, active, incorporated "
     "4 March 2009 (previous name HAMILTON MEDICAL LIMITED), Unit J6 Fulford Drive, Minworth, Sutton "
     "Coldfield, B76 1DJ; and HAMILTON SALES & SERVICE UK LTD 02188200, active, incorporated 3 "
     "November 1987 (previous names HAMILTON ROBOTICS LTD, HAMILTON (G.B.) LIMITED, MAGNAMINSTER "
     "LIMITED), Unit 1 Forge Mills Park, Station Road, Coleshill, Birmingham, B46 1JH — both read at "
     "Companies House %(today)s. Under the parent-subsidiary-award-credit policy the award credits "
     "to the entity the source names and no alias links the two, so the lot stays unattached. What "
     "would change it: NHS Supply Chain naming Hamilton Medical UK Ltd on the brief, or a Companies "
     "House filing showing one registration absorbed the other."},

    {"record": "SAI Medical Solutions Ltd", "code": "notice-only",
     "names": [["Airway Management Products and Associated Equipment", "Sai Medical Solutions Ltd", "Lot 1, Lot 2"]],
     "note": PRE + "The only Airway Management brief row sharing a word with \"Sai Medical Solutions "
     "Ltd\" is \"Sai Quality Fruits And Veg Limited\", an unrelated company. " + NOTICE_ONLY},

    {"record": "J Heinz Foods UK Limited", "code": "out-of-scope-non-clinical",
     "names": [["Ambient Food", "H.J. Heinz Foods UK Ltd", "Lot 1, Lot 6, Lot 8"]],
     "note": PRE + "Ambient Food is a catering framework. Lou has ruled that the Hub does not carry "
     "non-clinical framework suppliers (catering, facilities and electrical, furniture, office "
     "supplies, food), so this is a DECIDED state and not a backlog item. For the record: the brief's "
     "nearest rows are \"Kraft Heinz\" and \"Premier Foods Limited\", neither of which reaches this "
     "record, and Kraft Heinz is the group, not the UK entity the lot source names. The Lot 1, 6 and "
     "8 lots stay unattached and nothing further is to be done here."},

    {"record": "Nutricia Ltd", "code": "related-entity",
     "names": [["Ambient Food", "Nutricia Ltd", "Lot 2"],
               ["Infant Feeding and Accessories", "Nutricia Ltd", "Lot 1"]],
     "note": PRE + "Two frameworks name \"Nutricia Ltd\" as a lot source, and on both the brief's own "
     "row is \"Danone Nutricia Early Life Nutrition\" (written \"Danone Nutricia: early life "
     "Nutrition\" on the Ambient Food brief), which is its own Hub record. Under the "
     "parent-subsidiary-award-credit policy in data/identity-vocabulary-policy.json these are two "
     "facts about two things: the award credits to the entity the awarding source names, and no alias "
     "links a related entity, because aliases drive award routing. The records stay apart and the "
     "lots stay unattached."},

    {"record": "Simulation Man", "code": "unconfirmable",
     "names": [["Anaesthesia Machines, Ventilators, Neonatal Equipment and Associated Products",
                "Simulation Man Ltd", "Lot 2"]],
     "note": PRE + "The Anaesthesia Machines lot source names \"Simulation Man Ltd\" at Lot 2 and no "
     "row on that brief reaches this record. This name was checked at Companies House on 17/11/2026 "
     "and could not be tied to a registration, recorded then; under the unconfirmable-awardee policy "
     "the award publishes under the name as given with no company attached. The lot stays unattached."},

    {"record": "It’s Interventional Limited", "code": "notice-only",
     "names": [["Electrodes, Ultrasound Gels, Defibrillation and Related Consumables",
                "It's Interventional Limited", "Lot 1"]],
     "note": PRE + "No row on that brief shares a word with \"It's Interventional Limited\". " + NOTICE_ONLY},

    {"record": "Vyaire Medical Products Limited", "code": "notice-only",
     "names": [["Electrodes, Ultrasound Gels, Defibrillation and Related Consumables",
                "Vyaire Medical Products Limited", "Lot 6"]],
     "note": PRE + "The Electrodes brief's three unattached rows do not include Vyaire; the company "
     "is named in full on other briefs, where its lots do attach. " + NOTICE_ONLY},

    {"record": "Soluvos Medical Ltd", "code": "notice-only",
     "names": [["Endoscopy, Endourology and Oncology Ablation Consumables and Associated Products",
                "SOLUVOS MEDICAL LTD", "Lot 2"]],
     "note": PRE + "No row on the 58-supplier Endoscopy brief reaches this record. " + NOTICE_ONLY},

    {"record": "Abbott Medical U.K. Ltd", "code": "related-entity",
     "names": [["Enteral Feeding, Bile Bags and Associated Products", "Abbott Medical U.K. Ltd", "Lot 3, Lot 4"]],
     "note": PRE + "The Enteral Feeding lot source names \"Abbott Medical U.K. Ltd\" at Lots 3 and 4; "
     "the brief's own Abbott row is \"Abbott Laboratories Limited\", a separate registration with its "
     "own Hub record. This is the worked example of the parent-subsidiary-award-credit policy: the "
     "award credits to the entity the awarding source names, financials attach to the legal entity "
     "they describe, and no alias links the two because aliases drive award routing. The records stay "
     "apart and the lot stays unattached."},

    {"record": "Iskus Health UK Limited", "code": "unsettled-identity",
     "names": [["External Breast Prosthesis and Chest Support", "Iskus Health UK Ltd", "Lot 2"],
               ["General Wound Care", "Iskus Health UK Limited", "Lot 2b"],
               ["Pressure Area Care and Patient Handling", "Iskus Health UK Ltd", "Lot 1"]],
     "note": PRE + "Three frameworks name this company as a lot source with no brief row to attach "
     "to. On General Wound Care and Pressure Area Care no row on the brief shares a word with the "
     "name at all, so there is nothing to attach to. On External Breast Prosthesis the brief's row is "
     "\"Iskus Health Ltd - Distributor for Theya Healthcare\", which is its own Hub record and names "
     "\"Iskus Health Ltd\" — NOT the UK entity this record holds. Companies House holds ISKUS HEALTH "
     "UK LTD 08946660, active, incorporated 19 March 2014, Westminster Industrial Estate, Repton "
     "Road, Measham, DE12 7DT, and no company named \"Iskus Health Ltd\" (search %(today)s; Iskus "
     "Health is an Irish group). A name that may be the Irish parent cannot be tied to this "
     "registration, and under data/identity-vocabulary-policy.json a shared name is not evidence, so "
     "the two records stay apart and all three lots stay unattached. What would settle it: the "
     "registration number published on the supplier's own site, or a Find a Tender notice naming the "
     "awardee with its number."},

    {"record": "Lyreco UK Limited", "code": "notice-only",
     "names": [["External Defibrillation Devices and Related Services and Accessories",
                "Lyreco UK Limited", "Lot 1"]],
     "note": PRE + "Find a Tender award notice 050296-2025 names \"Lyreco UK Limited\" at Lot 1, but "
     "neither of the two unattached rows on NHS Supply Chain's own brief for that framework is "
     "Lyreco, and no row on the brief reaches this record. " + NOTICE_ONLY},

    {"record": "Esteve Pharmaceuticals Ltd", "code": "notice-only",
     "names": [["Hand Hygiene and Associated Products and Services", "Esteve Pharmaceuticals Ltd", "Lot 4"]],
     "note": PRE + "This record was added on 17/11/2026 from Find a Tender award notice 000335-2023 "
     "(the Hand Hygiene lot source), which awards 33 names while NHS Supply Chain's own brief states "
     "\"There are 21 suppliers on the framework\" and prints 21 — none of them this company. The "
     "brief's stated count matches its printed list, so the capture is not short: the notice and the "
     "owner's current list genuinely differ, which is why the record's own framework entry says the "
     "owner's current list does not name it. Nothing can attach the Lot 4 lot, because there is no "
     "brief row to attach it to. See state/hand-hygiene-lot-source-adjudication.json."},

    {"record": "GOJO / Purell", "code": "notice-only",
     "names": [["Hand Hygiene and Associated Products and Services", "GOJO Industries Europe Ltd", "Lot 1, Lot 3, Lot 4"]],
     "note": PRE + "The Hand Hygiene lot source is Find a Tender award notice 000335-2023, which "
     "awards 33 names; NHS Supply Chain's brief states 21 suppliers and prints 21, naming no GOJO "
     "row. The award spelling and its variants were added to this record as aliases on 17/11/2026, "
     "but an alias cannot attach a lot to a brief row that does not exist, so Lots 1, 3 and 4 stay "
     "unattached. See state/hand-hygiene-lot-source-adjudication.json."},

    {"record": "Inivos UK Limited", "code": "notice-only",
     "names": [["Hand Hygiene and Associated Products and Services", "Inivos Ltd", "Lot 1, Lot 2, Lot 3, Lot 4, Lot 5"]],
     "note": PRE + "Find a Tender award notice 000335-2023 names \"Inivos Ltd\" on five lots; NHS "
     "Supply Chain's own Hand Hygiene brief prints 21 suppliers, matching its own stated count, and "
     "names no Inivos row. " + NOTICE_ONLY},

    {"record": "PAL International Ltd", "code": "notice-only",
     "names": [["Hand Hygiene and Associated Products and Services", "Pal International Limited", "Lot 4"],
               ["Hand Hygiene and Associated Products and Services", "Pal International Ltd", "Lot 1, Lot 3"]],
     "note": PRE + "Find a Tender award notice 000335-2023 names this company twice, as \"Pal "
     "International Limited\" (Lot 4) and \"Pal International Ltd\" (Lots 1 and 3); both reach this "
     "record. NHS Supply Chain's own Hand Hygiene brief prints 21 suppliers, matching its own stated "
     "count, and names no PAL row — its only unattached row is an unrelated company. " + NOTICE_ONLY},

    {"record": "Reliance Medical", "code": "notice-only",
     "names": [["Hand Hygiene and Associated Products and Services", "Reliance Medical Ltd", "Lot 3"]],
     "note": PRE + "Find a Tender award notice 000335-2023 names \"Reliance Medical Ltd\" at Lot 3 of "
     "Hand Hygiene; NHS Supply Chain's own brief for that framework prints 21 suppliers, matching its "
     "stated count, and names no Reliance row (the company is named in full on other briefs, where "
     "its lots do attach). " + NOTICE_ONLY},

    {"record": "SC Johnson Professional (Deb)", "code": "distinct-registration",
     "names": [["Hand Hygiene and Associated Products and Services", "SC Johnson Professional", "Lot 1, Lot 2, Lot 4"]],
     "note": PRE + "The Hand Hygiene lot source names \"SC Johnson Professional\", which reaches this "
     "record; the brief's own row is \"SC Johnson Ltd\", which is its own record. Companies House "
     "holds these as separate registrations: SC JOHNSON PROFESSIONAL LIMITED 00364651, incorporated 2 "
     "January 1941, Denby Hall Way, Denby, Ripley, DE5 8JZ (and SC JOHNSON PROFESSIONAL GROUP LIMITED "
     "04934334 at the same address), against SC JOHNSON LTD 04166155, incorporated 22 February 2001 "
     "(previous name S.C. JOHNSON LIMITED), Frimley Green, Camberley, GU16 7AJ — read at Companies "
     "House %(today)s. Two registrations, so under the parent-subsidiary-award-credit policy the "
     "award credits as named, no alias links them, and Lots 1, 2 and 4 stay unattached."},

    {"record": "Nestle Health Science UK", "code": "related-entity",
     "names": [["Infant Feeding and Accessories", "Nestle", "Lot 1, Lot 2"]],
     "note": PRE + "The Infant Feeding lot source names a bare \"Nestle\", which reaches this record; "
     "the brief's own row is \"Nestle Nutrition\", a separate Hub record. A bare group word cannot be "
     "read as naming one of several Nestle entities, and under the parent-subsidiary-award-credit "
     "policy no alias may link related entities because aliases drive award routing. Lots 1 and 2 "
     "stay unattached. What would change it: NHS Supply Chain naming the entity in full on the brief, "
     "or a Find a Tender notice naming the awardee with its registration number."},

    {"record": "Vanguard Medical Devices Ltd", "code": "related-entity",
     "names": [["Minimally Invasive Surgery, Related Equipment and Accessories", "Vanguard Medical Devices Ltd", "Lot 2"]],
     "note": PRE + "The Minimally Invasive Surgery lot source names \"Vanguard Medical Devices Ltd\", "
     "which reaches this record; the brief's own row is \"Vanguard AG\", a separate record and a "
     "non-UK entity. Under the parent-subsidiary-award-credit policy the award credits to the entity "
     "the source names and no alias links the two, so Lot 2 stays unattached."},

    {"record": "Prosum Medical Ltd", "code": "notice-only",
     "names": [["Needlefree Connection Systems and Associated Products", "Prosum Medical Ltd", "Lot 1, Lot 2, Lot 3, Lot 4"]],
     "note": PRE + "The Needlefree Connection Systems brief has no unattached supplier rows at all — "
     "every row on it already carries its lot — and none of them reaches this record. The lot source "
     "names \"Prosum Medical Ltd\" on four lots, so the two sources name different supplier sets. "
     + NOTICE_ONLY},

    {"record": "Splice Cast Ltd t/a Eureka Physiocare", "code": "distinct-registration",
     "names": [["Physiotherapy and Occupational Therapy", "Splice Cast Ltd t/a Eureka Physiocare Ltd", "Lot 1, Lot 2"]],
     "note": PRE + "The Physiotherapy and Occupational Therapy lot source names \"Splice Cast Ltd t/a "
     "Eureka Physiocare Ltd\", which reaches this record; the brief's own row is \"Eureka Physiocare "
     "(previously Splice Cast)\", which reaches the separate \"Eureka Physiocare Ltd\" record. Those "
     "are TWO registrations, not one renamed: Companies House holds SPLICE CAST LIMITED 05102276, "
     "incorporated 15 April 2004, and EUREKA PHYSIOCARE LTD 13730060, incorporated 8 November 2021, "
     "whose only previous name is EUREKA PHYSIOCARE (NEWTOWN) LTD (8 to 24 November 2021) — so "
     "13730060 was never named Splice Cast (read at Companies House %(today)s). NHS Supply Chain's "
     "\"previously\" describes a trading succession, not a shared registration, and "
     "data/identity-vocabulary-policy.json merges on a registration, never on a name. The records "
     "stay apart and Lots 1 and 2 stay unattached. What would settle it: a Companies House filing, or "
     "a statement on the company's own site, documenting that the business transferred."},

    {"record": "Essential Healthcare Solutions (UK) Ltd", "code": "notice-only",
     "names": [["Pressure Area Care and Patient Handling", "Essential Healthcare Solutions (UK) Limited", "Lot 1, Lot 2, Lot 3"]],
     "note": PRE + "No row on the 53-supplier Pressure Area Care brief reaches this record; its only "
     "unattached row is an unrelated company. " + NOTICE_ONLY},

    {"record": "Nottingham Rehab Limited (Trading as NRS Healthcare)", "code": "notice-only",
     "names": [["Pressure Area Care and Patient Handling", "Nottingham Rehab Limited", "Lot 1"]],
     "note": PRE + "The Pressure Area Care lot source names \"Nottingham Rehab Limited\" at Lot 1 and "
     "no row on that brief reaches this record (the nearest word-match is \"Wealden Rehab Ltd\", a "
     "different company). " + NOTICE_ONLY},

    {"record": "Mediq Healthcare UK Ltd", "code": "notice-only",
     "names": [["Procedure Packs", "Mediq", "Lot 1, Lot 2"]],
     "note": PRE + "The Procedure Packs lot source names a bare \"Mediq\", which reaches this record, "
     "and none of the brief's three unattached rows is Mediq. " + NOTICE_ONLY},

    {"record": "Owens and Minor Halyard Ltd", "code": "unsettled-identity",
     "names": [["Procedure Packs", "Owens & Minor Halyard UK Ltd", "Lot 1, Lot 2"]],
     "note": PRE + "The Procedure Packs lot source names \"Owens & Minor Halyard UK Ltd\", which "
     "reaches this record; the brief's own row is \"O&M Halyard Uk Limited\", which is its own Hub "
     "record carrying the name-search candidate O&M HALYARD UK LIMITED 11111792 (active, incorporated "
     "14 December 2017, Eastcastle House, 27/28 Eastcastle Street, London, W1W 8DH). 11111792 records "
     "NO previous company name, so Companies House does not tie \"Owens & Minor Halyard UK Ltd\" to "
     "it, and no company of that name was found (searches %(today)s). \"O&M\" plainly reads as Owens "
     "& Minor, but a reading is not evidence: under data/identity-vocabulary-policy.json two records "
     "merge on a shared registration number, and a name-search candidate cannot carry a merge. The "
     "records stay apart and Lots 1 and 2 stay unattached. What would settle it: the registration "
     "number published on the supplier's own site, or a Find a Tender notice naming the awardee with "
     "its number."},

    {"record": "Intersurgical", "code": "notice-only",
     "names": [["Pulse Oximetry, Capnography and Related Monitoring Technologies", "Intersurgical Limited", "Lot 2"]],
     "note": PRE + "The Pulse Oximetry lot source names \"Intersurgical Limited\" at Lot 2 and no row "
     "on that brief reaches this record (the company is named in full on other briefs, where its lots "
     "do attach). " + NOTICE_ONLY},

    {"record": "Kinetik Medical Devices", "code": "unsettled-identity",
     "names": [["Pulse Oximetry, Capnography and Related Monitoring Technologies", "Kinetik Medical Devices Limited", "Lot 1"]],
     "note": PRE + "The Pulse Oximetry lot source names \"Kinetik Medical Devices Limited\", which "
     "reaches this record; the brief's own row is \"Kinetic Medical Devices Ltd (New)\" — Kinetic "
     "with a c — which is its own Hub record. Companies House holds NO company named \"Kinetic "
     "Medical Devices\" (search %(today)s), and two Kinetik ones: KINETIK MEDICAL DEVICES LIMITED "
     "06778337, active, incorporated 22 December 2008, Talbot House Unit 11, Perrywood Business Park, "
     "Honeycrock Lane, Redhill, RH1 5JQ; and HAMSARD 3150 LIMITED 06388994, previously named KINETIK "
     "MEDICAL DEVICES, dissolved 8 March 2016. So the brief's spelling has no registration of its "
     "own, but neither Hub record carries a confirmed number and \"(New)\" suggests NHS Supply Chain "
     "is distinguishing an entity, so WHICH registration each record is cannot be settled from here. "
     "Under data/identity-vocabulary-policy.json a shared name is not evidence and a name-search "
     "candidate cannot carry a merge: the records stay apart and Lot 1 stays unattached. What would "
     "settle it: the registration number published on the supplier's own site, or a Find a Tender "
     "notice naming the awardee with its number."},

    {"record": "Stowood Scientific Instruments", "code": "notice-only",
     "names": [["Pulse Oximetry, Capnography and Related Monitoring Technologies", "Stowood Scientific Instruments Ltd", "Lot 1, Lot 2"]],
     "note": PRE + "No row on the 26-supplier Pulse Oximetry brief reaches this record. " + NOTICE_ONLY},

    {"record": "EyeTech International Ltd", "code": "notice-only",
     "names": [["Technology Enabled Care, Electronic Assistive Technology and Associated Services",
                "EyeTech International Ltd", "Lot 2"]],
     "note": PRE + "No row on the 18-supplier Technology Enabled Care brief reaches this record. " + NOTICE_ONLY},

    {"record": "Hugh Steeper Limited", "code": "notice-only",
     "names": [["Technology Enabled Care, Electronic Assistive Technology and Associated Services",
                "Hugh Steeper Ltd", "Lot 1, Lot 2, Lot 3, Lot 4"]],
     "note": PRE + "The Technology Enabled Care lot source names \"Hugh Steeper Ltd\" on four lots "
     "and no row on that brief reaches this record. " + NOTICE_ONLY},

    {"record": "J & M Medical", "code": "notice-only",
     "names": [["Textiles and Associated Products", "J & M Medical", "Lot 2"]],
     "note": PRE + "No row on the 32-supplier Textiles brief reaches this record. " + NOTICE_ONLY},

    {"record": "Henry Schein UK Holdings", "code": "distinct-registration",
     "names": [["Total Patient Assessment Device Solutions", "Henry Schein UK Holdings Ltd", "Lot 1, Lot 4, Lot 5"]],
     "note": PRE + "The Total Patient Assessment lot source names \"Henry Schein UK Holdings Ltd\", "
     "which reaches this record (companyNumberProof 11584480, from Find a Tender notice "
     "2025/S 000-032831); the brief's own row is \"Henry Schien Medical\", its own Hub record and a "
     "different thing — the Henry Schein group files several UK registrations at Gillingham, among "
     "them HENRY SCHEIN LIMITED 01820330, HENRY SCHEIN UK LIMITED 11735268, HENRY SCHEIN EUROPE "
     "LIMITED 04194906 and HENRY SCHEIN UK HOLDINGS LIMITED 11584480 (search %(today)s), and a "
     "holding company is not its trading sibling. Under the parent-subsidiary-award-credit policy the "
     "award credits to the entity the source names, no alias links related entities, and Lots 1, 4 "
     "and 5 stay unattached."},

    {"record": "Solventum (3M Health Care)", "code": "unsettled-identity",
     "names": [["Total Patient Assessment Device Solutions", "KCI Medical Limited", "Lot 4"]],
     "note": PRE + "The Total Patient Assessment lot source names \"KCI Medical Limited\", which "
     "reaches this record through its 3M/KCI aliases, and the brief's own row is \"KCI Medical Ltd "
     "(3M)\", which reaches NO Hub record at all. So the lot cannot attach from either side: the "
     "source name lands on the Solventum record while the brief row lands nowhere. KCI Medical "
     "Limited is its own UK registration, and under data/identity-vocabulary-policy.json an alias may "
     "not be added to link a related entity, because aliases drive award routing and would re-route "
     "the award away from the entity the source names. Lot 4 stays unattached. What would change it: "
     "a record for KCI Medical Limited in its own right, with its registration confirmed, which is a "
     "decision about whether the Hub holds that entity and not a backlog item."},

    {"record": "H & R Healthcare Ltd", "code": "notice-only",
     "names": [["Urology and Bowel Management", "H&R Healthcare Ltd", "Lot 1, Lot 6"]],
     "note": PRE + "No row on the 57-supplier Urology and Bowel Management brief reaches this record; "
     "none of its five unattached rows is H&R. " + NOTICE_ONLY},
]

# ------------------------------------------------------------------ helpers


def rd(path):
    return json.load(io.open(path, encoding="utf-8"))


def uniq(seq):
    seen, out = set(), []
    for x in seq:
        key = x if isinstance(x, str) else json.dumps(x, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def norm_tokens(s):
    return [t for t in re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split() if t]


PROSE = ("reason", "note", "why", "evidence", "source")


def deep_merge(a, b, fold):
    """a wins, but nothing b holds is silently dropped.

    Nested maps merge recursively and lists union, so the folded record's
    matching aliases and crawl evidence survive — losing a matchAliases entry
    out of company-press.json would quietly stop that name's press ever
    matching again. Two different strings under one key are joined ONLY where
    the key is prose; a domain or a date is read by other code, so the
    survivor's value stands and the folded one is reported under
    _mergedFromDetail rather than string-joined into nonsense.
    """
    out = dict(a)
    for k, v in b.items():
        if k not in out:
            out[k] = v
        elif isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v, fold)
        elif isinstance(out[k], list) and isinstance(v, list):
            out[k] = uniq(out[k] + v)
        elif isinstance(out[k], str) and isinstance(v, str) and out[k] != v:
            if k in PROSE:
                out[k] = "%s | the merged \"%s\" record held: %s" % (out[k], fold, v)
            else:
                out.setdefault("_mergedFromDetail", {})[k] = v
    return out


def add_note(rec, note):
    """Put a verdict on a record's identityNote without ever losing what is there.

    A record may already carry an identityNote written for another reason — the
    evidence behind a company number, or an earlier adjudication the same day —
    and that is evidence too. So the verdict is APPENDED, and a verdict already
    present is left exactly as it is, which is what makes a second run of this
    script a no-op instead of a quiet overwrite.
    """
    existing = rec.get("identityNote") or ""
    if note in existing:
        return False
    rec["identityNote"] = (existing + "  " + note) if existing else note
    return True


def write(path, doc, n, what):
    fmt, rt = write_like(path, doc)
    print("%s: %s; %s" % (path, what, describe(path, fmt, rt)))
    return n


# --------------------------------------------------------------- the records


def merge_supplier_file(path, spec):
    doc = rd(path)
    sups = doc.get("suppliers") or []
    keep = [s for s in sups if isinstance(s, dict) and s.get("name") == spec["keep"]]
    fold = [s for s in sups if isinstance(s, dict) and s.get("name") == spec["fold"]]
    if keep and not fold:
        print("%s: %r already merged" % (path, spec["fold"]))
        return 0
    if not keep or not fold:
        print("%s: expected both %r and %r, found keep=%d fold=%d — SKIPPED"
              % (path, spec["keep"], spec["fold"], len(keep), len(fold)))
        return 0
    a, b = keep[0], fold[0]
    note = spec["note"] % {"today": TODAY}

    LIST_KEYS = ("aliases", "frameworks", "links", "products", "productCategories",
                 "specialities", "awards", "news", "alerts")
    for k in LIST_KEYS:
        va, vb = a.get(k), b.get(k)
        if va is None and vb is None:
            continue
        a[k] = uniq(list(va or []) + list(vb or []))
    a["aliases"] = uniq(list(a.get("aliases") or []) + [spec["keep"]] + spec["aliases"])

    # productCategories unions by whole entry, and the two records held the SAME
    # category sourced to two different framework captures, which verify.py
    # rejects ("category ... appears more than once in productCategories").
    # One record cannot hold a category twice, so the survivor's own entry
    # stands and the duplicate is dropped. Nothing is lost: the framework the
    # dropped entry was sourced to is on this record's `frameworks` list and the
    # merge itself is recorded in state/framework-lot-name-adjudication-1117.json.
    cats, seen_cat = [], set()
    for c in a.get("productCategories") or []:
        key = c.get("category") if isinstance(c, dict) else c
        if key in seen_cat:
            print("  dropped a second %r productCategories entry (one category per record)" % key)
            continue
        seen_cat.add(key)
        cats.append(c)
    if cats != (a.get("productCategories") or []):
        a["productCategories"] = cats

    notes = [n for n in (a.get("note"), b.get("note")) if n]
    a["note"] = note + (("  Previous \"%s\" record: %s" % (spec["keep"], notes[0])) if notes else "")
    if len(notes) > 1:
        a["note"] += "  Previous \"%s\" record: %s" % (spec["fold"], notes[1])
    a["identityNote"] = note
    for k in ("source", "reconciledFrom", "companyNumberNote", "_specialitiesEvidence"):
        if b.get(k) and a.get(k) and b[k] != a[k]:
            a[k] = "%s | from the merged \"%s\" record: %s" % (a[k], spec["fold"], b[k])
        elif b.get(k) and not a.get(k):
            a[k] = b[k]
    a["mergedFrom"] = uniq(list(a.get("mergedFrom") or []) + [spec["fold"]])
    a["verified"] = TODAY

    doc["suppliers"] = [s for s in sups if not (isinstance(s, dict) and s.get("name") == spec["fold"])]
    return write(path, doc, 1, "merged %r into %r" % (spec["fold"], spec["keep"]))


def rename_keys(doc, container, spec, merge_lists=False):
    node = doc
    for seg in container:
        node = node.get(seg) if isinstance(node, dict) else None
        if node is None:
            return 0
    if spec["fold"] not in node:
        return 0
    b = node.pop(spec["fold"])
    a = node.get(spec["keep"])
    if a is None:
        node[spec["keep"]] = b
    elif merge_lists or isinstance(a, list) or isinstance(b, list):
        node[spec["keep"]] = uniq(list(a or []) + list(b or []))
    else:
        node[spec["keep"]] = deep_merge(a or {}, b or {}, spec["fold"])
    return 1


def rename_values(node, fields, spec):
    """Set any string field in `fields` that holds the folded name to the survivor."""
    n = 0
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k in fields and isinstance(v, str) and v.strip() == spec["fold"]:
                node[k] = spec["keep"]
                n += 1
            elif k in fields and isinstance(v, list):
                new = [spec["keep"] if (isinstance(x, str) and x.strip() == spec["fold"]) else x for x in v]
                if new != v:
                    node[k] = uniq(new)
                    n += 1
            else:
                n += rename_values(v, fields, spec)
    elif isinstance(node, list):
        for v in node:
            n += rename_values(v, fields, spec)
    return n


def fix_count(doc, counts_key, container):
    """Keep a file's own counts header true to the rows this merge changed.

    verify.py fails company-awards.json and company-press.json when the header
    and the rows disagree. Folding two records into one legitimately removes a
    row, so the header moves WITH it, in the same change — regenerating either
    file would publish a day of unrelated pipeline output on top of a merge.
    """
    counts = doc.get("counts")
    node = doc.get(container)
    if not isinstance(counts, dict) or not isinstance(node, dict):
        return 0
    if counts.get(counts_key) == len(node):
        return 0
    counts[counts_key] = len(node)
    return 1


def search_index(doc, spec):
    recs = doc.get("records") or []
    old = [r for r in recs if isinstance(r, dict) and r.get("c") == "Supplier"
           and (r.get("t") or "").strip() in (spec["keep"], spec["fold"])]
    if not any((r.get("t") or "").strip() == spec["fold"] for r in old):
        return 0
    words = norm_tokens(spec["keep"]) + [w for r in old for w in norm_tokens(r.get("k"))]
    merged = {"t": spec["keep"],
              "u": "/medical-sales-hub/suppliers/#q=" + quote(spec["keep"]),
              "k": " ".join(uniq(words)), "c": "Supplier"}
    at = recs.index(old[0])
    doc["records"] = [r for r in recs if r not in old]
    doc["records"].insert(at, merged)
    return 1


def key_info(spec):
    """Drop the folded record's generated Company Key Info page and index row.

    These files are built per record by the key-info refresh; a page for a
    record that no longer exists is a dead page, and the survivor's own page is
    rebuilt by that job, not hand-written here.
    """
    n = 0
    idx = "data/company-key-info/index.json"
    doc = rd(idx)
    cos = doc.get("companies")
    if isinstance(cos, list):
        rows = [c for c in cos if not (isinstance(c, dict) and (c.get("n") or "").strip() == spec["fold"])]
        if len(rows) != len(cos):
            doc["companies"] = rows
            if isinstance(doc.get("counts"), dict) and "companies" in doc["counts"]:
                doc["counts"]["companies"] = len(rows)
            n += write(idx, doc, 1, "dropped the %r row" % spec["fold"])
    slug = re.sub(r"[^a-z0-9]+", "-", spec["fold"].lower()).strip("-")
    page = os.path.join("data/company-key-info", slug + ".json")
    if os.path.exists(page):
        os.remove(page)
        print("%s: removed (page for a record that no longer exists)" % page)
        n += 1
    return n


def panels(spec):
    """Rename the record name in every speciality panel, and ONLY the record name.

    `suppliers[].name` is a Hub record; `frameworks[].suppliers[]` is NHS Supply
    Chain's own brief row and is left exactly as the owner writes it.
    """
    import glob
    n = 0
    for path in sorted(glob.glob(os.path.join("data", "speciality-panels", "*.json"))):
        doc = rd(path)
        hits = rename_values(doc.get("suppliers") or [], {"name", "ref", "matchedTo"}, spec)
        if hits:
            n += write(path, doc, hits, "%d record-name change(s)" % hits)
    return n


def coverage_refusals(spec):
    """Every coverage-ledger row that holds the survivor must LIST its recorded
    crawl refusal in that row's own `refusedSuppliers`.

    verify.py's rule (^o404): "a refusal is a fact about the site, not about
    which bucket the supplier fell into". The folded record had no domain, so
    the Procedure Packs row carried it under notCrawled/domainsMissing; the
    survivor's domain accringtonsurgical.co.uk is recorded as refused (it does
    not resolve), and the Complete Ophthalmology and Surgical Instruments rows
    already list that refusal. So the refusal row is added here too, in the
    exact shape the other rows use.

    Only `refusedSuppliers` changes. The supplier is deliberately NOT moved
    between buckets: `actionable` and `actionableTotal` are arithmetic over the
    buckets and verify.py checks they agree, and re-classifying a row is
    build_coverage_ledger.py's job, not this script's.
    """
    sp = rd("data/supplier-products.json")
    ref = (sp.get("refusals") or {}).get(spec["keep"])
    if not isinstance(ref, dict):
        print("data/coverage-ledger.json: no recorded refusal for %r — nothing to list" % spec["keep"])
        return 0
    row = {"supplier": spec["keep"], "domain": ref.get("domain"),
           "reason": ref.get("reason"), "checked": ref.get("checked"), "bucket": "refused"}
    BUCKETS = ("published", "publishedElsewhere", "heldOnly", "capturedNothingCounted",
               "notCrawled", "refused", "unknown")
    doc = rd("data/coverage-ledger.json")
    n = 0
    for r in doc.get("frameworks") or []:
        if not isinstance(r, dict):
            continue
        if not any(spec["keep"] in (r.get(b) or []) for b in BUCKETS):
            continue
        listed = [w for w in (r.get("refusedSuppliers") or []) if isinstance(w, dict)]
        if any(w.get("supplier") == spec["keep"] for w in listed):
            continue
        r["refusedSuppliers"] = listed + [row]
        print("  %s: now lists the recorded refusal for %r" % (r.get("framework"), spec["keep"]))
        n += 1
    if not n:
        print("data/coverage-ledger.json: every row already lists the refusal")
        return 0
    return write("data/coverage-ledger.json", doc, n, "%d row(s) given the refusal" % n)


def patch(path, fn):
    doc = rd(path)
    n = fn(doc)
    if not n:
        print("%s: nothing to change" % path)
        return 0
    return write(path, doc, n, "%d change(s)" % n)


def do_merge(spec):
    total = 0
    total += merge_supplier_file("data/supplier-seed.json", spec)
    total += merge_supplier_file("data/supplier-index.json", spec)
    total += patch("data/company-financials.json", lambda d: rename_keys(d, ("companies",), spec))
    total += patch("data/company-awards.json",
                   lambda d: rename_keys(d, ("companies",), spec, merge_lists=True)
                   + rename_values(d.get("companies", {}).get(spec["keep"]) or [], {"company"}, spec)
                   + fix_count(d, "companies", "companies"))
    total += patch("data/company-press.json",
                   lambda d: rename_keys(d, ("suppliers",), spec)
                   + fix_count(d, "suppliers", "suppliers"))
    total += patch("data/supplier-products.json", lambda d: rename_keys(d, ("refusals",), spec))
    total += patch("data/company-logos.json", lambda d: rename_values(d.get("logos") or [], {"name"}, spec))
    total += patch("data/supplier-careers.json", lambda d: rename_values(d.get("suppliers") or [], {"name"}, spec))
    total += patch("data/interview-prep.json", lambda d: rename_values(d.get("co") or [], {"n"}, spec))
    total += patch("data/coverage-ledger.json",
                   lambda d: rename_values(d.get("frameworks") or [],
                                           {"supplier", "refused", "notCrawled", "domainsMissing"}, spec))
    # `ref`/`matchedTo` must equal the master record's name; `co` stays the printed spelling
    total += patch("data/compare-suppliers.json",
                   lambda d: rename_values(d.get("specialities") or {}, {"ref"}, spec))
    total += patch("data/innovator-report.json",
                   lambda d: rename_values(d.get("specialities") or {}, {"ref", "matchedTo"}, spec))
    total += patch("data/hub-search-index.json", lambda d: search_index(d, spec))
    total += key_info(spec)
    total += panels(spec)
    total += coverage_refusals(spec)
    return total


# ----------------------------------------------------------- aliases + notes


def apply_aliases_and_notes():
    """Add the brief's own spellings as aliases, and write every verdict onto the
    record it answers — but never over an identityNote this run did not write.
    """
    changed = 0
    for path in ("data/supplier-seed.json", "data/supplier-index.json"):
        doc = rd(path)
        byname = {}
        for s in doc.get("suppliers") or []:
            if isinstance(s, dict):
                byname.setdefault(s.get("name"), s)
        n = 0
        for spec in ALIASES:
            rec = byname.get(spec["record"])
            if rec is None:
                print("%s: no record %r — SKIPPED" % (path, spec["record"]))
                continue
            before = list(rec.get("aliases") or [])
            rec["aliases"] = uniq(before + [spec["record"]] + spec["add"])
            note = add_note(rec, spec["note"] % {"today": TODAY})
            if rec.get("aliases") != before or note:
                n += 1
            rec["verified"] = TODAY
        for spec in VERDICTS:
            rec = byname.get(spec["record"])
            if rec is None:
                print("%s: no record %r — SKIPPED" % (path, spec["record"]))
                continue
            if add_note(rec, spec["note"] % {"today": TODAY}):
                n += 1
        if n:
            changed += write(path, doc, n, "%d record(s) given an alias or a verdict" % n)
        else:
            print("%s: aliases and verdicts already in place" % path)
    return changed


def write_state():
    doc = {
        "_notice": {
            "owner": "Elevate and Thrive Ltd, company number 17154474, England and Wales",
            "copyright": "© Elevate and Thrive Ltd 2026. All rights reserved.",
            "published": "Working state for the Medical Sales Intelligence Hub, not a member-facing file.",
        },
        "generated": TODAY,
        "decidedBy": "Claude, under data/identity-vocabulary-policy.json; no new ruling from Lou was needed",
        "question": (
            "verify._warn_unresolved_lot_names() counts 50 lot-source supplier names across 25 "
            "frameworks that DO resolve to a Hub supplier record, but whose framework's own brief "
            "supplier list names no row reaching that record, so attach_names() has nothing to "
            "attach the lot to."
        ),
        "whatIsNotTheFix": (
            "\"Re-read the brief\" is not the general answer. On Hand Hygiene the brief states 21 "
            "suppliers and prints 21 while Find a Tender notice 000335-2023 awards 33; on Airway "
            "Management the brief prints 54 and states 54. Both captures are complete — the brief "
            "and its lot source genuinely name different supplier sets."
        ),
        "bar": (
            "data/identity-vocabulary-policy.json: two companies sharing a NAME is not evidence, two "
            "sharing a REGISTRATION NUMBER is; a name-search candidate cannot carry a merge; an alias "
            "may never link a related entity, because aliases drive award routing."
        ),
        "fixed": {
            "merged": [
                {"into": m["keep"], "folded": m["fold"], "registration": m["number"],
                 "evidence": m["note"] % {"today": TODAY}} for m in MERGES],
            "aliased": [
                {"record": a["record"], "aliasesAdded": a["add"],
                 "evidence": a["note"] % {"today": TODAY}} for a in ALIASES],
        },
        "left": [
            {"record": v["record"], "code": v["code"],
             "names": [{"framework": f, "lotSourceName": s, "lots": l} for f, s, l in v["names"]],
             "verdict": v["note"] % {"today": TODAY}} for v in VERDICTS],
        "alreadyAdjudicatedElsewhere": [
            {"record": "Uniphar Medtech",
             "names": [{"framework": "Airway Management Products and Associated Equipment",
                        "lotSourceName": "Uniphar Medtech UK Limited", "lots": "Lot 2"}],
             "verdict": "Adjudicated earlier on 2026-11-17 and left apart from \"Uniphar Medtech UK "
                        "Ltd (Cardiac Services / Synapse Medical)\" because the bare name cannot be "
                        "tied to one registration (Companies House holds UNIPHAR MEDTECH UK LIMITED "
                        "NI018037 and UNIPHAR MEDTECH HOLDINGS UK LIMITED NI040976 at one Belfast "
                        "address, and the group's Irish entity is a lot source elsewhere). That "
                        "record's own identityNote carries the reasoning and is not rewritten here. STILL "
                        "OUTSTANDING, not closed: the two records stay apart, but NI018037's own "
                        "registered name IS \"Uniphar Medtech UK Limited\", and normalisation strips "
                        "\"UK\" and \"Limited\", so that lot-source name collapses onto this bare "
                        "brand record instead of the confirmed one. Re-read at Companies House "
                        "2026-11-17 by a sibling session: NI018037 UNIPHAR MEDTECH UK LIMITED active, "
                        "NI040976 UNIPHAR MEDTECH HOLDINGS UK LIMITED active. The consequence is live "
                        "and is a misattribution: ten award rows that belong to the confirmed record "
                        "sit on this one, including \"Synapse MR400 MRI Patient Monitoring System\" "
                        "(Hull University Teaching Hospitals, 2026-02-12). The fix is to add \"Uniphar "
                        "Medtech UK Limited\" and \"Uniphar Medtech UK Ltd\" as aliases to the "
                        "CONFIRMED record — no merge. DONE: landed in b983be2 on 2026-11-17. The "
                        "confirmed record now holds \"Uniphar Medtech UK Limited\" and "
                        "\"Uniphar Medtech UK Ltd\"; six award rows moved onto it (18 to 24), "
                        "the bare brand record is left with none, and four notice names with no "
                        "territory word are quarantined as ambiguous. The records are still not "
                        "merged."},
            {"record": "Uniphar Medtech UK Ltd (Cardiac Services / Synapse Medical)",
             "names": [{"framework": "Total Patient Assessment Device Solutions",
                        "lotSourceName": "Uniphar Medtech UK Limited T/A Cardiac Services",
                        "lots": "Lot 1, Lot 2"}],
             "verdict": "The other side of the same question, answered in the same place. Its "
                        "identityNote is not rewritten here. This is the record holding companyNumber "
                        "NI018037 with confidence \"confirmed\" (Companies House previous-name chain "
                        "SISK HEALTHCARE (UK) LIMITED / CARDIAC SERVICES LIMITED). The registered-name "
                        "aliases \"Uniphar Medtech UK Limited\" and \"Uniphar Medtech UK Ltd\" "
                        "belong HERE and were added in b983be2 on 2026-11-17, so lot-source and award "
                        "names in that form now reach this record instead of the bare brand "
                        "one."},
        ],
        "effectOnTheGate": (
            "Simulated offline against the stored lotsBySource with refresh_framework_lots."
            "attach_names() and the new seed on 2026-11-17: the five fixes attach and nothing else "
            "moves — Electrosurgical Consumables 1 unresolved name to 0, External Defibrillation 3 "
            "to 2, Procedure Packs 3 to 2, Transcatheter Heart Valve 6 to 4; 136 unresolved source "
            "names in all to 131, so the \"DO resolve but not on this brief\" line falls from 50 to "
            "45. data/framework-lots.json's own `unresolved` lists are NOT rewritten here: "
            "--attach-only reuses them and only a full refresh_framework_lots.py run (which re-reads "
            "the briefs) recomputes them, so the gate's count moves on the next full run, not on "
            "this commit. The same holds for the framework claims the three new aliases unlock, "
            "which backfill_seed_from_frameworks.py attaches from the briefs on its own next run."
        ),
        "notTouched": [
            "data/frameworks.json supplier lists, data/framework-lots.json unresolved names and "
            "data/nhssc-launch-briefs.json: NHS Supply Chain's own words.",
            "The \"Uniphar Medtech\" and \"Uniphar Medtech UK Ltd (Cardiac Services / Synapse "
            "Medical)\" records, adjudicated earlier on 2026-11-17 and carrying their own "
            "identityNote.",
            "Non-clinical framework suppliers (catering, facilities and electrical, furniture, "
            "office supplies, food) — Lou has ruled that the Hub does not carry them.",
        ],
    }
    counts = {
        # the 50 the gate counts: 42 under `left`, 2 merged, 3 the aliases attach,
        # 1 (Neuromodulation's "BVM MEDICAL LTD") answered inside the BVM alias
        # note as a novation, and the 2 Uniphar names adjudicated earlier today.
        "namesTheGateCounts": 50,
        "namesUnderLeft": sum(len(v["names"]) for v in VERDICTS),
        "merged": len(MERGES),
        "namesFixedByAlias": 3,
        "namesAnsweredInsideAnAliasNote": 1,
        "namesAdjudicatedElsewhere": 2,
        "recordsLeftWithVerdict": len(VERDICTS),
    }
    doc["counts"] = counts
    before = None
    if os.path.exists(STATE):
        try:
            before = rd(STATE)
        except Exception:
            before = None
    if before == doc:
        print("%s: already current" % STATE)
        return 0
    with io.open(STATE, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("%s: written (%s)" % (STATE, counts))
    return 1


if __name__ == "__main__":
    total = 0
    for spec in MERGES:
        print("--- merging %r into %r" % (spec["fold"], spec["keep"]))
        total += do_merge(spec)
    print("--- aliases and verdicts")
    total += apply_aliases_and_notes()
    total += write_state()
    print("done: %d change(s)" % total)
