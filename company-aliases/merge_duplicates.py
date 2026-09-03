#!/usr/bin/env python3
"""Merge duplicate supplier records in supplier-seed.json.

`match_check.py` found 11 company numbers carried by two or three SEED SUPPLIER
records - one company showing as two or three suppliers on the compare tab.
Most carry a note saying they were "Reconciled from data/compare-suppliers.json
on 07/08/2026", which is the cause: that reconciliation added a researched
Compare-tab row for a company that already had a master record.

Not all 11 are duplicates, and this merges only the ones that are. See
MERGES (safe) and HELD (not safe, and why) below.

Extended 18/08/2026 with twelve more groups, almost all of them a supplier name
misspelt on an NHS Supply Chain contract launch brief and ingested literally on
14/08 - "Wiliams", "Holdaigs", "Technologis", "Assisstive", "Interntional",
"Hunteligh". Each was checked against the Companies House register that day:
the misspelt form is not a registered company and the survivor's registered
name is. The 14/08 groups are kept in MERGES_APPLIED_2026_08_14 and asserted
still intact on every run, rather than deleted; the 18/08 groups are kept the
same way in MERGES_APPLIED_2026_08_18.

Extended 21/08/2026 with one more group: Mediq, showing twice on Company
Intelligence because NHSSC's Respiratory Solutions brief names it by its
pre-2023 identity, truncated. Register-checked that day.

  python3 merge_duplicates.py --dry-run     show what would change (default)
  python3 merge_duplicates.py --apply       write supplier-seed.json

--apply REFUSES if the msh-compare-data working tree has uncommitted changes to
supplier-seed.json. The file is single-line JSON of several megabytes: a
concurrent write from another session and this one cannot be reconciled, the
loser's work is simply gone. Land or stash the other work first.

After --apply, the repo's own gate still governs the publish:
    python3 build_supplier_index.py && python3 scripts/stamp_notice.py && python3 verify.py
verify.py must exit 0. A push to msh-compare-data IS a live publish.
"""

import json
import os
import shutil
import subprocess
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
# MSH_REPO lets this run against a scratch copy. Proving a seed change on a
# copy - build_supplier_index.py, then stamp_notice.py, then verify.py - is the
# only proof that counts: a verify against the committed index proves nothing,
# because the nightly rebuild regenerates the index from the seed.
REPO = os.environ.get("MSH_REPO") or os.path.abspath(os.path.join(HERE, ".."))
# Moved into msh-compare-data itself 03/09/2026 (was a sibling Hub/company-aliases/);
# HERE is now <repo>/company-aliases, so the repo root is just "..".
SEED = os.path.join(REPO, "data", "supplier-seed.json")
COMPARE = os.path.join(REPO, "data", "compare-suppliers.json")
PRESS = os.path.join(REPO, "data", "company-press.json")

STAMP = "Merged %s by merge_duplicates.py: one company was showing as %d suppliers."

# ---------------------------------------------------------------------------
# ALREADY APPLIED on 14/08/2026. Kept, not deleted: these rows no longer exist
# in the seed, so re-running them would look like a missing record. Instead
# main() asserts the fold is still intact - the survivor is present and carries
# every folded name as an alias. If a later edit undoes one of these merges,
# that assertion fails rather than the duplicate quietly coming back.
MERGES_APPLIED_2026_08_14 = [
    ("WS Audiology", ["WS Audiology (Sivantos/Widex)"], "00203774",
     "Sivantos and Widex merged to form WS Audiology; both records are that one company."),
    ("Oticon", ["Oticon (Demant)"], "01095512",
     "Demant is Oticon's parent group, not a second supplier."),
    ("Topcon GB Medical", ["Topcon Great Britain Medical"], "01522615",
     "The same name written two ways; registered name is TOPCON (GREAT BRITAIN) MEDICAL LIMITED."),
    ("Frontier Therapeutics", ["Frontier Therapeutics (Frontier Medical Group)"], "02552048",
     "Same company; the survivor already carries 'Frontier Medical Group' and 'Repose' as aliases."),
    ("Schulke & Mayr UK Ltd", ["Schülke UK"], "02987168",
     "Same company; the survivor already carries the umlaut spellings as aliases."),
    ("Draeger Medical UK", ["Draeger Medical"], "04310199",
     "Same company. Survivor is the UK record, which carries the MHRA alert on Atlan workstations."),
    ("Invacare UK", ["Invacare LTD"], "05178693",
     "Same company - both records carry the identical confirmed note for INVACARE LIMITED."),
]

# ---------------------------------------------------------------------------
# 18/08/2026. Twelve groups, all of them one trading company written two (or
# three) ways. Ten of the twelve are a misspelling that entered the seed on
# 14/08 straight off an NHS Supply Chain contract launch brief - NHSSC's own
# briefs spell supplier names inconsistently and sometimes wrongly, and the
# ingest takes the brief's spelling literally. Each one below was checked
# against the Companies House register on 18/08/2026: in every case the
# misspelt form is not a registered company and the survivor's registered name
# is. A shared company number was never on its own the reason to merge.
MERGES_APPLIED_2026_08_18 = [
    ("Williams Medical Supplies", ["Wiliams Medical Supplies Limited"], "04240054",
     "NHSSC's brief for 2026/S 000-012699 spells it \"Wiliams\"; the register has no "
     "company of that spelling and one WILLIAMS MEDICAL SUPPLIES LIMITED (04240054, "
     "Rhymney, SIC 47749), which the survivor already carries as an alias."),
    ("Henry Schein UK Holdings", ["Henry Schein UK Holdaigs Ltd"], "11584480",
     "\"Holdaigs\" is a transposition of \"Holdings\" on NHSSC's brief for 2023/S "
     "000-011885. The register holds HENRY SCHEIN UK HOLDINGS LIMITED (11584480) and "
     "nothing resembling \"Holdaigs\"; the survivor's number is confirmed, not probable."),
    ("NISSHA Medical Technologies", ["NISSHA Medical Technologis Ltd"], "05999241",
     "\"Technologis\" is a dropped 'e' on NHSSC's brief for 2025/S 000-032216. The "
     "register holds NISSHA MEDICAL TECHNOLOGIES LTD (05999241) and no other UK "
     "NISSHA medical company."),
    ("Medequip Assistive Technology", ["Medequip Assisstive Technology Ltd"], "04198824",
     "\"Assisstive\" is a doubled 's' on NHSSC's brief for 2022/S 000-033396. The "
     "register holds MEDEQUIP ASSISTIVE TECHNOLOGY LIMITED (04198824) and no company "
     "of the misspelt form."),
    ("Performance Health International Limited", ["Performance Health Interntional"],
     "04374752",
     "\"Interntional\" is a dropped 'a' on NHSSC's brief for 2022/S 000-033396. The "
     "register holds PERFORMANCE HEALTH INTERNATIONAL LIMITED (04374752); both records "
     "sit on Aids for Daily Living."),
    ("Draeger Medical UK", ["Dräger UK"], "04310199",
     "One company written with and without the umlaut. Both records are the medical "
     "business - anaesthesia machines, airway management and patient monitoring appear "
     "on both - not DRAEGER SAFETY UK LTD (00777464), which is the group's other UK "
     "company and is not a Hub supplier. Survivor is the record matched to DRAEGER "
     "MEDICAL UK LIMITED (04310199) and carrying the Atlan MHRA alert."),
    ("Otto Bock Healthcare PLC", ["Ottobock UK"], "01271967",
     "Ottobock's only UK company is OTTO BOCK HEALTHCARE PLC (01271967), whose own "
     "register entry lists OTTO BOCK UK LIMITED among its previous names. Both records "
     "carry prosthetic components; the survivor is the one on the registered name."),
    ("D.P. Medical Systems Limited", ["DP Medical Systems", "DP Medical"], "02088954",
     "THREE records, one company, and NHSSC itself is the proof: the frameworks inside "
     "the record called \"DP Medical\" carry notes reading 'named ... as \"DP Medical "
     "Systems Limited\"' and '... as \"DP Medical Systems Ltd\"'. All three trade as "
     "D.P. MEDICAL SYSTEMS LIMITED (02088954, Chessington, dpmedicalsys.com). The "
     "\"DP Medical\" record was additionally mis-matched to DP MEDICAL LIMITED "
     "(10379481, Cannock, SIC 96090 other service activities) - a different company; "
     "that financials entry is left orphaned by this merge, as intended."),
    ("Arjo", ["Arjo Hunteligh UK Ltd"], None,
     "\"Hunteligh\" is a transposition of \"Huntleigh\" on NHSSC's brief for 2024/S "
     "000-011959. ArjoHuntleigh was renamed Arjo in 2017; the register shows "
     "ARJOHUNTLEIGH UK as a closed overseas branch (BR006744) and ARJO UK LIMITED "
     "(10842512) as the live UK company. Merged on the entity, NOT on a number - the "
     "survivor's own company match is itself wrong (ARJO CONSULTING LTD, 13973896, "
     "management consultancy, incorporated 2022) and is reported separately, not "
     "silently inherited as evidence."),
    ("OscarTech UK", ["Oscar Tech UK Ltd"], "09196814",
     "The same name with and without a space. The register holds one OSCARTECH UK LTD "
     "(09196814); the survivor already carries \"OscarTech UK Ltd\" as an alias."),
    ("SP Services (UK) Ltd", ["SP Services Limited"], "03424705",
     "The register settles the survivor: 03424705 is registered SP SERVICES (UK) "
     "LIMITED (Telford, SIC 46460), with S P SERVICES (UK) LIMITED and S.P. SERVICES "
     "(TELFORD) among its previous names. There is no company registered as \"SP "
     "Services Limited\" - the only near match, S.P. SERVICES (PRESSURE WASHERS) "
     "LIMITED (01404824), is in liquidation and is not a medical supplier. Both "
     "records sit on the same two NHSSC frameworks."),
    ("Baxter / Hillrom", ["Hill-rom - now part of Baxter"], "02250372",
     "NOT on the list this run started from - found while verifying the Baxter rows. "
     "The 14/08 NHSSC row literally names itself Hill-Rom, and the survivor IS the "
     "Hub's Hill-Rom record (matched to HILL-ROM LIMITED, 02250372). Folding it in "
     "PRESERVES the deliberate Hillrom / Baxter Healthcare split recorded in the "
     "survivor's own note rather than undoing it."),
]

# ---------------------------------------------------------------------------
# 21/08/2026. One group. Mediq showed as two suppliers on Company Intelligence
# because NHS Supply Chain's own Respiratory Solutions brief names the supplier
# with its pre-2023 identity appended and truncated to 40 characters: "Mediq
# Healthcare Uk Limited Ex Bunzl Hea" is "Mediq Healthcare UK Limited (ex Bunzl
# Healthcare)" cut off mid-word. Verified at the register on 21/08/2026, not
# inferred from the string: MEDIQ HEALTHCARE UK LIMITED (00062537) carries
# BUNZL RETAIL & HEALTHCARE SUPPLIES LIMITED as a previous name, ceased
# 12/06/2023, and the company publishes 00062537 in its own website footer.
MERGES_APPLIED_2026_08_21 = [
    ("Mediq Healthcare UK Ltd", ["Mediq Healthcare Uk Limited Ex Bunzl Hea"], "00062537",
     "One company written two ways. NHSSC's contract launch brief for Respiratory "
     "Solutions (1 August 2022 to 15 June 2027, 37 suppliers) lists the supplier as "
     "\"Mediq Healthcare Uk Limited Ex Bunzl Hea\" - the brief's own former-name "
     "designation, truncated. The Companies House register settles it: MEDIQ "
     "HEALTHCARE UK LIMITED (00062537, Mediq House, Castle Donington) was registered "
     "BUNZL RETAIL & HEALTHCARE SUPPLIES LIMITED until 12/06/2023, and no company of "
     "the NHSSC spelling exists on the register. The survivor already carries the "
     "confirmed number and the financials record; the folded record had neither. "
     "Checked at the register and against the brief on 21/08/2026."),
]

# ---------------------------------------------------------------------------
# 21/08/2026, third pass. Two more groups, both from
# Data-Verification/framework-key-collision-fix-2026-08-21.md's "not fixed"
# list — genuine same-company duplicates, distinct from that file's other two
# pairs (Abbott, Cardiac Services), which are real, differently-numbered
# companies and stay split. Applied directly via merge_records() /
# repoint_compare_refs() / repoint_press(), not through the MERGES list below,
# to avoid touching that list's own pending work.
MERGES_APPLIED_2026_08_21B = [
    ("Eden Medical (UK) Limited", ["Eden Medical"], "SC345525",
     "One trading company, two Hub rows. The company's own website "
     "(edenmedical.co.uk) names itself \"Eden Medical (UK) Limited\", company "
     "number SC345525 (Loanhead, Midlothian) - the exact name NHS Supply "
     "Chain's Airway Management brief uses. Its Respiratory Solutions brief "
     "instead uses the bare shorthand \"Eden Medical\" for the same award, not "
     "a second registered company. A separate active company, EDEN MEDICAL "
     "LIMITED (SC363425, formerly Elgin Medical Limited), shares the same "
     "registered office and a director (Simon John Krievs) but is not the "
     "entity either brief names or the website identifies as, and holds no "
     "Hub framework award. Checked at Companies House and against "
     "edenmedical.co.uk on 21/08/2026."),
    ("Seca Ltd", ["SECA UK Ltd"], "01430864",
     "One trading company, two Hub rows. SECA LIMITED (01430864, Seca House, "
     "40 Barn Street, Digbeth, Birmingham - UK distributor for the German "
     "seca medical scales and measurement brand) is the only active "
     "UK-registered \"Seca\" company; there is no separate \"SECA UK Ltd\" on "
     "the register (the only similarly-named company, SECAUK LTD 14846649, is "
     "an unrelated dissolved London company with no medical-sector "
     "connection). NHS Supply Chain's two briefs simply spell the same "
     "supplier two ways - \"Seca Ltd\" and \"SECA UK Ltd\". Checked at "
     "Companies House on 21/08/2026."),
]

# ---------------------------------------------------------------------------
# 21/08/2026, second pass. Lou's decision, taken on the evidence below: the
# third record for the same legal entity goes in too.
#
# "Bunzl Retail & Healthcare Supplies Ltd" is not a company that exists any
# more. It is the registered name 00062537 carried until 12/06/2023, and no
# other GB company holds it. Its own financials entry was matched to NF004224 -
# an OVERSEA-COMPANY registration (Larne, converted-closed), not a trading
# company, which is the giveaway that the name-search match had nowhere real to
# land. That orphaned financials entry is deleted alongside this merge rather
# than left pointing at a closed registration.
#
# The caution that held it back, recorded so a later reader can weigh it: the
# Examination Gloves framework began 27/11/2023, AFTER the rename, so NHS Supply
# Chain awarded under a name the register had already retired. That is NHSSC's
# supplier record being stale - the same defect that produced "Ex Bunzl Hea" -
# not evidence of a second company. "Bunzl Healthcare" stays a separate record
# and stays in HELD: it is a different question, and its own company match is a
# name-search guess.
#
# CONFIRMED APPLIED (found 24/08/2026, moved here from MERGES where it was left
# behind after being written to the real seed - it was blocking every later run
# of --apply, since a stale MERGES entry naming an already-folded record dies
# with "named in MERGES but not found in the seed" before anything else can be
# checked or written): Mediq Healthcare UK Ltd's aliases already carry "Bunzl
# Retail & Healthcare Supplies Ltd" and no separate record for it exists.
MERGES_APPLIED_2026_08_21C = [
    ("Mediq Healthcare UK Ltd", ["Bunzl Retail & Healthcare Supplies Ltd"], "00062537",
     "The same legal entity under its pre-2023 registered name. Companies House shows "
     "MEDIQ HEALTHCARE UK LIMITED (00062537) with BUNZL RETAIL & HEALTHCARE SUPPLIES "
     "LIMITED as a previous name, ceased 12/06/2023; the only other register hit for "
     "that name is NF004224, an oversea-company registration that is converted-closed "
     "and never traded as a separate business. The folded record's two NHSSC framework "
     "rows (Examination Gloves 2023/S 000-016807 and Infusion Pumps Project_12 ITT_382) "
     "are Mediq's and move with it. Checked at the register on 21/08/2026; merged on "
     "Lou's decision the same day."),
]

# ---------------------------------------------------------------------------
# APPLIED on 24/08/2026 (commit db99a3c), picking up OUTSTANDING ^o45. Two
# groups, neither a match_check.py SHARED-NUMBER finding (neither record
# carried a companyNumberCandidate before that day), so the gate had never had
# a number to catch either pair on. Both confirmed at Companies House and
# merged as one company under two brief names - the same shape as the
# already-applied Dräger, Otto Bock and Mediq folds - and are NOT genuine
# business-line splits like Avanos, which stays held.
MERGES_APPLIED_2026_08_24 = [
    ("Artivion UK Ltd", ["Artivion UK Ltd (CryoLife Europa, Ltd)"], "03837138",
     "One trading company under two brief names, not a genuine business-line split like "
     "Avanos. Companies House 03837138 traded as CRYOLIFE EUROPA LTD until it rebranded to "
     "ARTIVION UK LTD (confirmed at the register's filing history and against ABHI's own "
     "membership page, which lists the company as \"Artivion (CryoLife Europa Ltd)\", "
     "https://www.abhi.org.uk/membership/company/549/artivion-cryolife-europa-ltd). NHS "
     "Supply Chain's two briefs (Wound Closure 2025/S 000-001071 and Medical Technology "
     "2024/S 000-020906) simply name the same UK entity under its old and new trading "
     "names, the same shape as the already-applied Dräger/Drager and Otto Bock/Ottobock "
     "folds. Checked at the register on 24/08/2026."),
    ("Aquilant Critical Care", ["Aquilant Ltd Bd Bas Critical"], "02090807",
     "One trading company, two NHS Supply Chain brief names. AQUILANT LIMITED (02090807, "
     "Basingstoke, medical device distributor) is the only active UK-registered \"Aquilant\" "
     "company on the register — there is no second entity for either brief name to belong "
     "to. \"Aquilant Ltd Bd Bas Critical\", on the Respiratory Solutions brief, reads as that "
     "brief's own truncated/decorated form of the company's name (the same shape as the "
     "already-applied Mediq \"Ex Bunzl Hea\" truncation), not a second company. Checked at "
     "the register on 24/08/2026; neither record carried a companyNumberCandidate before "
     "this, so match_check.py's SHARED-NUMBER check had never had a number to catch this "
     "pair on."),
]

# ---------------------------------------------------------------------------
# ALREADY APPLIED on 25/08/2026 (commit 90b43e5). Prepared 24/08/2026, second
# pass: the 10 SHARED-NUMBER pairs from match_check.py that had never been
# triaged. Seven are one company under two names - in every case a 14/08
# contract-launch-brief record standing alongside the record the Hub already
# held - and each was checked at the Companies House register on 24/08/2026
# before being written here. The other three are NOT merges and are in HELD
# below: Direct Healthcare Group / Talley, Numed and Teleflex.
#
# The survivor is the record a rep would name, and the registered form wins
# where both records are brief-derived stubs.
MERGES_APPLIED_2026_08_25 = [
    ("Hugh Steeper Limited", ["Hugh Steeper T/A Steeper"], "00173865",
     "One company, two brief names. HUGH STEEPER LIMITED (00173865, incorporated "
     "23/03/1921, active, Unit 3 Stourton Link, Leeds) is the only Hugh Steeper on the "
     "register; 'Steeper' is its trading name, and the other register hits at that same "
     "address are group companies (Steeper Holdings 05571486, RSL Steeper Group 04782018), "
     "not a second supplier. The folded record's Prosthetic Components framework "
     "(2025/S 000-005015) joins the survivor's Orthotics, Podiatry and Immobilisation. "
     "Checked at the register on 24/08/2026."),
    ("Bayer", ["Bayer Public Limited Company"], "00935048",
     "The folded record IS the survivor's registered name. BAYER PUBLIC LIMITED COMPANY "
     "(00935048, incorporated 08/07/1968, active, 400 South Oak Way, Reading, SIC 46460) "
     "is the number already confirmed on the Bayer record by a curator; the second record "
     "is NHS Supply Chain's Contrast Injectors brief (2021/S 000-007768) naming the same "
     "company in full. Checked at the register on 24/08/2026."),
    ("Sigvaris", ["Sigvaris Britain Ltd"], "02724989",
     "One company, two names. SIGVARIS BRITAIN LIMITED (02724989, incorporated 23/06/1992, "
     "active, Andover; incorporated as TONETORM LIMITED and renamed 27/11/1992) is the only "
     "Sigvaris company on the register. The folded record's Vascular Therapy framework "
     "(2023/S 000-012286) joins the survivor's NHS SBS SBS10142. Checked at the register "
     "on 24/08/2026."),
    ("Accrington Surgical Instrument Suppliers Ltd", ["Accrington Surgical"], "05980916",
     "One company, two brief names, and the short form is deliberately NOT the survivor. "
     "ACCRINGTON SURGICAL INSTRUMENT SUPPLIERS LIMITED (05980916, incorporated 27/10/2006, "
     "active, Westhoughton, SIC 32500) is the live supplier. The register also carries "
     "ACCRINGTON SURGICAL LTD (06046644), DISSOLVED 17/09/2015, which cannot hold the "
     "Surgical Instruments framework the folded record was added from (2020/S 170-412524) "
     "because it did not exist by then - so keeping the long registered form as the "
     "survivor stops the dissolved namesake being resolved to later. Checked at the "
     "register on 24/08/2026."),
    ("Bespoke Prosthetics & Orthotics Ltd", ["Bespoke Prosthetics Ltd"], "09523234",
     "One company, two brief names. BESPOKE PROSTHETICS & ORTHOTICS LTD (09523234, "
     "incorporated 02/04/2015, active, Scissett, Huddersfield, SIC 32500) is the only "
     "match on the register - there is no 'BESPOKE PROSTHETICS LTD' registered for the "
     "folded name to belong to. Its Prosthetic Components framework (2025/S 000-005015) "
     "joins the survivor's Orthotics, Podiatry and Immobilisation. Checked at the "
     "register on 24/08/2026."),
    ("GenX MediCare Ltd", ["Gen X Medicare"], "09614874",
     "One company, two spacings of one name. GENX MEDICARE LTD (09614874, incorporated "
     "29/05/2015, active, Huddersfield; previously PRECISION SURGICARE LTD to 14/05/2018) "
     "is the only match on the register. The folded record's Medical Pulp, Macerators and "
     "Support Products framework (ITT_596) joins the survivor's four. Checked at the "
     "register on 24/08/2026."),
    ("Oswell Penda", ["Oswell Penda Pharmaceutical Ltd"], "11146087",
     "One company, two names. OSWELL PENDA PHARMACEUTICAL LTD (11146087, incorporated "
     "11/01/2018, active, Oswestry, SIC 32500 and 46460) is the only Oswell Penda on the "
     "register. The folded record's Advanced Wound Care framework (2024/S 000-029271) "
     "joins the survivor's NHS SBS SBS10142. Checked at the register on 24/08/2026."),
]

# ---------------------------------------------------------------------------
# ALREADY APPLIED on 25/08/2026 (commit f3d6379). These four sat in HELD as
# "NEEDS A DECISION" / "INTENTIONAL SPLIT" until Lou gave the decision that day:
# "if the Companies House number shows the same then always merge, if not then
# keep separate." They are recorded here, and removed from HELD, so the file
# does not go on telling the next reader that a settled question is still open
# (root rule 18). Each `why` is the survivor's own merge note in the seed.
MERGES_APPLIED_2026_08_25B = [
    ("Avanos Medical UK Limited", ["Avanos Medical (RF pain)"], "09051011",
     "Lou's decision, overriding the original product-line HELD entry: RF pain (COOLIEF "
     "neuromodulation) and enteral feeding (MIC-KEY, CORTRAK) are recorded on the register "
     "under the same entity, AVANOS MEDICAL UK LIMITED (09051011)."),
    ("Abbott Diagnostics", ["Abbott Rapid Diagnostics"], "01716581",
     "Lou's decision: both carry 01716581 on the register. The survivor now covers BOTH "
     "core lab AND point-of-care/rapid testing (formerly Alere), flagged explicitly in its "
     "note at Lou's request so the fold cannot be mistaken for a core-lab-only record."),
    ("Duncan Technical Services", ["DD Products and Services"], "01196676",
     "Lou's decision, overriding the original HELD entry. Duncan Technical Services is kept "
     "as the survivor name - the name reps meet - with DD Products and Services folded in "
     "as the registered supplying entity behind it."),
    ("Essity UK Limited (formerly BSN Medical Ltd)",
     ["Essity (BSN medical)", "Essity UK TENA Health & Medical",
      "Essity UK TENA Heath & Medical"], "03226403",
     "Lou's decision, applying her own rule. Four seed rows shared ESSITY UK LIMITED "
     "(03226403): the BSN Medical wound-care record, the TENA continence record, and a "
     "second TENA record carrying a one-letter typo ('Heath') found while researching this. "
     "Essity UK Ltd - Health & Medical Solutions stays SEPARATE - its number (03665635, "
     "Essity Holding UK Limited) is different and only probably matched."),
]

# ---------------------------------------------------------------------------
# 25/08/2026: the two Becton Dickinson depot records, found by the
# supplier-alias-enrichment task rather than by match_check.py - which never saw
# them, because neither carries a company number for it to match on. They are
# NHS Supply Chain ACCOUNT names, not companies: one framework brief
# (2022/S 000-005941, Intravenous Cannula and Associated Products, 21 suppliers)
# names the same supplier twice, once per delivery point.
#
# This is the one merge in this file that does NOT rest on a shared company
# number, so the evidence is set out in full rather than a register line.
#
# ALREADY APPLIED (found 27/08/2026, moved here from MERGES where it was left
# behind after being written to the real seed - it was blocking every later
# run of --apply with "named in MERGES but not found in the seed", the same
# stale-entry trap the 21/08 Mediq/Bunzl fold hit on 24/08).
MERGES_APPLIED_2026_08_25C = [
    ("BD — Becton, Dickinson",
     ["Becton Dickinson Uk Ltd Ed Wokingham", "Becton Dickinson Uk Ltd Stock Oxford"],
     None,
     "One company, one framework, two NHS Supply Chain delivery points - NOT a shared "
     "company number, and deliberately merged without one. Both folded records carry "
     "`companyNumberNote: no Companies House match could be established`, and that is "
     "correct: the register holds no BECTON DICKINSON UK LTD at all (checked 25/08/2026 - "
     "the BD entities are BECTON, DICKINSON U.K. LIMITED 00852702, BECTON DICKINSON (CME) "
     "U.K. LIMITED 04236707 and BECTON DICKINSON INFUSION THERAPY UK 00536128, all at "
     "1030 Eskdale Road, Winnersh Triangle, Wokingham RG41 5TS). 'Becton Dickinson Uk Ltd "
     "Ed Wokingham' and 'Becton Dickinson Uk Ltd Stock Oxford' are that trading name plus "
     "a depot qualifier, and both were ingested on 14/08/2026 from ONE brief - same "
     "framework, same reference 2022/S 000-005941, same 21-supplier count, same dates "
     "27/03/2023 to 31/03/2027. The survivor already names 00852702 in its own curated "
     "note, tied to 'the NHS Supply Chain catalogue names the framework supplier as "
     "BECTON DICKINSON UK LTD with Wokingham depot codes', and already carries 'Becton "
     "Dickinson UK Ltd' as an alias - so neither folded record could ever win a lookup, "
     "it could only double-count BD as three competitors on the compare tab. The fold "
     "also upgrades real data: the survivor's IV Cannula framework entry carries no "
     "reference, and the folded ones carry the full 2022/S 000-005941 record. Merged on "
     "Lou's explicit instruction, 25/08/2026."),
]

MERGES = [
    ("Kimal PLC", ["Kimal PLC Stock"], "00827857",
     "One company, a depot/stock qualifier appended to the name - the same shape as the "
     "already-applied BD Wokingham/Oxford and Mediq 'Ex Bunzl Hea' folds. 'Kimal PLC "
     "Stock' was ingested 14/08/2026 from NHS Supply Chain's own contract launch brief "
     "for Intravenous Accessories and Pressure Monitoring Accessories (Project_112 "
     "ITT_460) and its own companyNumberNote already names 'Kimal PLC' as the nearest "
     "register hit. Confirmed at the register on 27/08/2026: KIMAL PLC (00827857, "
     "Worcester Six Business Park, incorporated 19/11/1964, previously KIMAL SCIENTIFIC "
     "PRODUCTS LIMITED) is Active and is the only exact-name match. NOT the same company "
     "as Kimal Renal Care (matched to KIMAL RENAL CARE LIMITED 06839033, dissolved), "
     "which stays a separate, held record - a different business, not a channel variant. "
     "Lou approved merging both this and the (already-applied) Mediq pair on 18/08/2026."),
]

# Same company number, deliberately NOT merged. Each needs a decision that is
# Lou's or the data owner's, not a script's.
HELD = [
    ("Direct Healthcare Group / Talley", "00520386",
     "NOT A DUPLICATE, AND THE NUMBER IS WRONG ON ONE OF THEM. Settled on 20/08/2026 from "
     "Companies House PSC filings and recorded in Process flows for all brands/"
     "talley-is-a-direct-healthcare-group-brand.md: Talley Group Limited (00520386) and "
     "Direct Healthcare Group Holdings Limited (10023261) are separate live entities under "
     "one ultimate parent, DHG Bidco Ltd (12349117), holding separate framework positions - "
     "Talley on Negative Pressure Wound Therapy (a 6-supplier framework that would be lost "
     "inside a DHG record), DHG on Pressure Area Care and Patient Handling. They share "
     "00520386 in company-financials.json only because the DHG record was matched to "
     "TALLEY GROUP LIMITED - its own matchedOn already says the registered name does not "
     "corroborate. The DHG trading company on the register is DIRECT HEALTHCARE GROUP "
     "LIMITED (05252571, active, Unit 8 Withey Court, Caerphilly, incorporated 06/10/2004, "
     "previously QUOTABLE CUSHIONS LTD and DIRECT HEALTHCARE SERVICES LTD). Correcting a "
     "wrong number is a different operation from this script's and is not done here. "
     "Checked at the register on 24/08/2026."),
    ("Numed Healthcare / Numed Holdings Ltd (T/A Numed Healthcare)", "15982458",
     "NOT A DUPLICATE, AND THE NUMBER IS WRONG ON ONE OF THEM. Two live entities, and the "
     "register makes the relationship explicit: NUMED HOLDINGS LIMITED (01302868, active, "
     "incorporated 16/03/1977, previously CARDIOLOGIC (U.K.) LIMITED) is the PSC of NUMED "
     "HEALTHCARE LIMITED (15982458, active, incorporated 27/09/2024), holding 75%+ of "
     "shares and voting rights, notified 27/09/2024. Both are at Alliance House, Roman "
     "Ridge Road, Sheffield. Parent and subsidiary is the Talley/DHG shape, not a "
     "duplicate. Both Hub records carry 15982458 from a name search; the Holdings record's "
     "number is 01302868. Note a third register hit, NUMED HEALTHCARE LIMITED 02024335, "
     "DISSOLVED 27/03/2012 (previously NUMED CARDIAC DIAGNOSTICS LIMITED) - a name search "
     "on 'Numed Healthcare' returns two companies and only one of them is live. Checked at "
     "the register on 24/08/2026."),
    ("TFX Group Ltd, trading as Teleflex Medical / Teleflex Medical UK", "FC038449",
     "BOTH MATCHES ARE WRONG, SO THERE IS NOTHING TO MERGE ON. Both records were name-"
     "searched to TELEFLEX GLOBAL SERVICES LLC (FC038449), an oversea-company registration, "
     "which is not the UK trading entity behind either framework position. The register "
     "carries TFX GROUP LIMITED (02884361, active, Amersham, SIC 32990 and 70100 head "
     "offices), TELEFLEX LIMITED (01421176), TELEFLEX UK LIMITED (01600496) and TELEFLEX "
     "INDUSTRIES LIMITED (03137603). Nothing in either record distinguishes which entity "
     "holds Central Venous Catheters and Urology and Bowel Management (Teleflex Medical UK) "
     "from Minimally Invasive Surgery and Syringes, Needles (TFX Group) - the same shape as "
     "Henry Schein. Merging them would fuse two records on a number that belongs to "
     "neither. Needs route 1 or route 2 evidence per docs/COMPANY-REPORT-METHOD.md. "
     "Checked at the register on 24/08/2026."),
    ("Advanced Medical Solutions (AMS) / Advanced Medical Systems Ltd / "
     "\"Advanced Medial Solutions Limited\"", "02666957 (disputed)",
     "NOT A DUPLICATE, AND ONE OF THE TWO IS MIS-MATCHED. Advanced Medical Systems "
     "Ltd (Banbury, sterile-processing distributor) carries an alert in its own Hub "
     "record saying in terms 'do not confuse with Advanced Medical Solutions Limited "
     "(Companies House 02666957)' - yet company-financials.json matches that very "
     "record to 02666957 ADVANCED MEDICAL SOLUTIONS LIMITED. The register has "
     "ADVANCED MEDICAL SYSTEMS LTD. at 03476650 (Banbury, SIC 46460), which is the "
     "right company. Advanced Medical Solutions (AMS) is the AIM-listed wound-care "
     "group, matched to 03603261. Merging any of these would fuse two unrelated "
     "businesses. \"Advanced Medial Solutions Limited\" is not a seed record at all - "
     "it reaches the supplier index from data/compare-issues.json."),
    ("Henry Schien Medical", "unidentified",
     "NOTHING IDENTIFIES WHICH ENTITY IS MEANT. The register carries HENRY SCHEIN "
     "LIMITED (01820330), HENRY SCHEIN UK LIMITED (11735268), HENRY SCHEIN UK "
     "HOLDINGS LIMITED (11584480) and HENRY SCHEIN UK GLOBAL HOLDINGS LIMITED "
     "(12439337), among others. The record's only fact is a place on Total Patient "
     "Assessment Device Solutions (2025/S 000-032216), which does not distinguish "
     "between them. Folding it into the Holdings record would be a guess."),
    ("Nihon Koden", "07350287",
     "NO DUPLICATE EXISTS. The seed holds ONE row, misspelt - the register has "
     "NIHON KOHDEN UK LIMITED (07350287, Guildford) and no 'Nihon Koden'. There is "
     "nothing to merge; correcting the name is a rename, which is a different "
     "operation from this script's and is not done here."),
    ("Baxter Healthcare Corporation / ICU Medical International Ltd", "n/a",
     "NOT SEED RECORDS. Both names reach data/supplier-index.json from "
     "data/compare-issues.json (recall and delisting notices), not from "
     "supplier-seed.json, so no seed merge can remove them. Neither is published to "
     "the Interview Prep dropdown, which omits companies with no register record. "
     "Deduplicating index-only names is a change to the index build, not to the seed."),
]


def die(msg, code=1):
    print("FAIL: %s" % msg, file=sys.stderr)
    sys.exit(code)


def uniq(seq):
    """Order-preserving dedupe of hashable-or-JSON-able items."""
    out, seen = [], set()
    for x in seq:
        k = json.dumps(x, sort_keys=True) if isinstance(x, (dict, list)) else x
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


# Fields that describe where a RECORD came from and how its company match went.
# They belong to the record they were written for. A survivor must never inherit
# them from a record being folded away - see merge_records().
DROP_ONLY_FIELDS = ("companyNumberNote", "reconciledFrom", "source", "verified")


def merge_records(keep, drops, number, why, today):
    """Fold every record in `drops` into `keep`. Nothing is discarded."""
    for d in drops:
        for field in ("specialities", "products", "frameworks", "alerts",
                      "news", "links", "awards", "_specialitiesEvidence"):
            a, b = keep.get(field), d.get(field)
            if not b:
                continue
            if isinstance(a, list) and isinstance(b, list):
                keep[field] = uniq(a + b)
            elif isinstance(b, list) and a is None:
                keep[field] = uniq(b)
            elif isinstance(a, dict) and isinstance(b, dict):
                merged = dict(b)          # survivor's own entries win
                merged.update(a)
                keep[field] = merged
            elif not a:
                keep[field] = b
            # a and b both present but not mergeable (e.g. two strings): the
            # survivor's value stands. Losing the other is why the fold is
            # recorded in the note.
        # every dropped name and alias must keep resolving
        keep["aliases"] = uniq((keep.get("aliases") or []) + [d["name"]]
                               + (d.get("aliases") or []))
        # fill any field the survivor lacks - EXCEPT the fields that describe the
        # DROPPED record's own provenance and match verdict. Inheriting those is
        # how a survivor with a confirmed company number ended up also carrying
        # "No Companies House match could be established" (seen twice on
        # 21/08/2026, on both Mediq folds). A note that contradicts the record it
        # sits in is the defect root rule 18 exists to stop, so these are dropped
        # on the floor and the fold is recorded in note[] instead.
        for k, v in d.items():
            if k in ("name", "aliases") or k in DROP_ONLY_FIELDS:
                continue
            if not keep.get(k) and v:
                keep[k] = v
        # and if the survivor INHERITED one on an earlier run, clear it now
        for k in DROP_ONLY_FIELDS:
            if k in ("companyNumberNote",) and keep.get(k) and number:
                keep.pop(k)
    keep["curated"] = True
    note = (keep.get("note") or "").strip()
    added = (STAMP % (today, 1 + len(drops))) + " Folded in: " + \
            ", ".join('"%s"' % d["name"] for d in drops) + \
            (". Company number %s. " % number if number else ". ") + why
    keep["note"] = (note + " " + added).strip() if note else added
    return keep


def repoint_compare_refs(rename):
    """After a seed merge, compare-suppliers.json rows still `ref` the old name.

    verify.py's compare-ref check catches exactly this - a Compare-tab row
    naming a `ref` that is not the seed's master record - so a merge that only
    touches the seed fails the gate. Discovered proving this script on a
    scratch copy, not guessed at.
    """
    if not os.path.exists(COMPARE):
        return 0
    data = json.load(open(COMPARE))
    changed = 0
    specialities = data.get("specialities") or {}
    for spec in specialities.values():
        for row in spec.get("suppliers") or []:
            if row.get("ref") in rename:
                row["ref"] = rename[row["ref"]]
                changed += 1
    if changed:
        # This file is committed pretty-printed (indent 1), unlike the seed,
        # which is one line. Writing it minified turned a 2-field edit into a
        # 4,769-line diff the first time this ran - caught by `git diff
        # --stat` looking wrong before committing, not by any check. Match the
        # file's own formatting so the diff shows only what changed.
        with open(COMPARE, "w") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    return changed


def repoint_press(rename):
    """Fold the dropped names' press blocks into the survivor's.

    Found by proving the 18/08 merge on a scratch copy, exactly as
    repoint_compare_refs was on 14/08. data/company-press.json is keyed by
    SUPPLIER NAME and verify.py's company-press check fails on any key that
    does not resolve to a seed record - so a seed-only merge leaves thirteen
    orphan keys and the gate refuses the push.

    verify.py also requires the counts header to equal the rows, so the six
    counts are recomputed here by the same traversal it uses. They are
    recomputed, never adjusted by hand: a counts header that drifted from its
    own rows is the 14/08/2026 defect that check exists to catch.

    data/company-awards.json has the same problem and its own sanctioned fix,
    which the gate prints: python3 scripts/refresh_awards.py --rematch.
    """
    if not os.path.exists(PRESS):
        return 0
    doc = json.load(open(PRESS))
    sup = doc.get("suppliers") or {}
    moved = 0
    for drop, keep in rename.items():
        if drop not in sup:
            continue
        block = sup.pop(drop)
        moved += 1
        target = sup.setdefault(keep, {"items": []})
        items = target.get("items") or []
        have = {(i.get("headline"), i.get("date")) for i in items}
        for row in (block.get("items") or []):
            if (row.get("headline"), row.get("date")) not in have:
                items.append(row)
                have.add((row.get("headline"), row.get("date")))
        if items:
            target["items"] = items
        # lastChecked: the OLDER of the two is the honest one - the survivor
        # has not been checked under the folded name since that date.
        for f in ("lastChecked",):
            a, b = target.get(f), block.get(f)
            if b and (not a or str(b) < str(a)):
                target[f] = b
    if not moved:
        return 0

    items_seen = sources_seen = resolved_seen = redirect_seen = with_items = 0
    for rec in sup.values():
        rows = (rec or {}).get("items") or []
        if rows:
            with_items += 1
        for row in rows:
            items_seen += 1
            for src in (row.get("sources") or []):
                sources_seen += 1
                if (src or {}).get("urlType") == "publisher":
                    resolved_seen += 1
                else:
                    redirect_seen += 1
    doc.setdefault("counts", {}).update({
        "suppliers": len(sup), "suppliersWithItems": with_items,
        "items": items_seen, "sources": sources_seen,
        "resolvedLinks": resolved_seen, "redirectLinks": redirect_seen})

    with open(PRESS, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return moved


def main(argv):
    apply_it = "--apply" in argv
    today = datetime.date.today().strftime("%d/%m/%Y")

    if apply_it:
        try:
            dirty = subprocess.run(
                ["git", "-C", REPO, "status", "--porcelain",
                 "data/supplier-seed.json", "data/compare-suppliers.json"],
                capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception as exc:
            die("could not check the working tree (%s). Not writing." % exc)
        if dirty:
            die("data/supplier-seed.json has uncommitted changes (%s).\n"
                "       Another session is working in this repo. This file is one\n"
                "       enormous line of JSON - whoever writes second wins and the\n"
                "       other's work is gone. Land or stash it, then re-run." % dirty)

    data = json.load(open(SEED))
    suppliers = data["suppliers"]
    by_name = {s["name"]: s for s in suppliers}

    # The 14/08 folds must still be intact. A survivor that has lost a folded
    # name from its aliases means the duplicate is on its way back.
    undone = []
    for keep_name, drop_names, _number, _why in (
            MERGES_APPLIED_2026_08_14 + MERGES_APPLIED_2026_08_18
            + MERGES_APPLIED_2026_08_21 + MERGES_APPLIED_2026_08_21B
            + MERGES_APPLIED_2026_08_21C + MERGES_APPLIED_2026_08_24
            + MERGES_APPLIED_2026_08_25 + MERGES_APPLIED_2026_08_25B
            + MERGES_APPLIED_2026_08_25C):
        keep = by_name.get(keep_name)
        if keep is None:
            undone.append("%s: survivor missing" % keep_name)
            continue
        aliases = set(keep.get("aliases") or [])
        for dn in drop_names:
            if dn in by_name:
                undone.append("%s: '%s' is a live record again" % (keep_name, dn))
            elif dn not in aliases:
                undone.append("%s: '%s' no longer resolves as an alias" % (keep_name, dn))
    if undone:
        die("the 14/08, 18/08 and 21/08/2026 merges are no longer intact:\n       "
            + "\n       ".join(undone))

    planned, missing = [], []
    for keep_name, drop_names, number, why in MERGES:
        if keep_name not in by_name:
            missing.append(keep_name)
            continue
        drops = [by_name[n] for n in drop_names if n in by_name]
        if not drops:
            missing.append(" / ".join(drop_names))
            continue
        planned.append((keep_name, drops, number, why))

    print("SUPPLIER DUPLICATE MERGE  (%s)\n" % ("APPLY" if apply_it else "dry run"))
    print("Merging %d group(s):\n" % len(planned))
    for keep_name, drops, number, why in planned:
        keep = by_name[keep_name]
        print("  %s  <-  %s" % (keep_name, ", ".join(d["name"] for d in drops)))
        print("     company %s | %s" % (number or "n/a (merged on entity evidence)", why))
        print("     frameworks %d -> %d, products %d -> %d, specialities %s"
              % (len(keep.get("frameworks") or []),
                 len(uniq((keep.get("frameworks") or [])
                          + [f for d in drops for f in (d.get("frameworks") or [])])),
                 len(keep.get("products") or []),
                 len(uniq((keep.get("products") or [])
                          + [p for d in drops for p in (d.get("products") or [])])),
                 sorted(set((keep.get("specialities") or [])
                            + [s for d in drops for s in (d.get("specialities") or [])]))))
        print()

    if missing:
        # A merge that silently does not happen is worse than one that fails:
        # the duplicate stays live and the run still looks successful. The
        # umlaut in "Schulke UK" vs "Schülke UK" skipped a group exactly this
        # way on the first dry run.
        die("named in MERGES but not found in the seed: %s\n"
            "       Either the record was renamed or the spelling here is wrong. "
            "Fix MERGES before anything is written." % ", ".join(missing))

    print("Holding %d group(s) that share a number but must NOT be merged:\n" % len(HELD))
    for label, number, why in HELD:
        print("  %s  (%s)" % (label, number))
        print("     %s\n" % why)

    if not apply_it:
        print("Dry run - nothing written. Re-run with --apply.")
        return 0

    drop_names = {d["name"] for _, drops, _, _ in planned for d in drops}
    rename = {d["name"]: keep_name for keep_name, drops, _, _ in planned for d in drops}
    for keep_name, drops, number, why in planned:
        merge_records(by_name[keep_name], drops, number, why, today)
    data["suppliers"] = [s for s in suppliers if s["name"] not in drop_names]

    backup = SEED + ".backup_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(SEED, backup)
    with open(SEED, "w") as fh:
        json.dump(data, fh, separators=(",", ":"), ensure_ascii=False)
    print("Backed up to %s" % os.path.basename(backup))
    print("Wrote %s - %d suppliers (was %d)."
          % (os.path.basename(SEED), len(data["suppliers"]), len(suppliers)))

    compare_changed = repoint_compare_refs(rename)
    if compare_changed:
        print("Repointed %d compare-suppliers.json row(s) whose `ref` named a "
              "now-merged supplier." % compare_changed)
    press_moved = repoint_press(rename)
    if press_moved:
        print("Folded %d company-press.json block(s) into their survivor and "
              "recomputed the counts header." % press_moved)

    print("\nNow run, in the repo, and do not push unless verify.py exits 0:")
    print("  python3 scripts/refresh_awards.py --rematch   # award keys still name the merged-away records")
    print("  python3 build_supplier_index.py && python3 scripts/stamp_notice.py && python3 verify.py")
    print("  python3 scripts/build_interview_prep.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
