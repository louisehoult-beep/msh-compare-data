#!/usr/bin/env python3
"""
build_formulary_positions.py — data/formulary-positions.json, the Hub's
trust-and-system-level formulary directory for diabetes technology (CGM/HCL).

WHY THIS FILE EXISTS
--------------------
Lou, 04/09/2026: "Formulary is still almost empty and carries none of the ICB
trust or system formulary data", and "Formulary needs to be trust specific with
links."

What the Formulary tab carried before this was a nine-row static table ported
from retired page 1754. It named nine commissioning bodies, summarised each
position in a phrase, and put the SOURCE IN PLAIN TEXT — "nottsapc.nhs.uk",
"bucksformulary.nhs.uk" — with no link a rep could open. That is the specific
thing Lou asked to fix.

This file replaces it with a linked, per-document directory. Every row names the
body that ACTUALLY PUBLISHED the document, at the level the source itself
publishes at. That matters and is the point of "trust specific": a large share of
England's CGM positions are not published by an ICB at all. They are published by
an Area Prescribing Committee (Nottinghamshire APC), a regional treatment
advisory group (NTAG), a joint ICB-and-trust formulary (Norfolk and Waveney ICB
and Group Trust Formulary; Suffolk and North East Essex with ESNEFT, West Suffolk
and Norfolk and Suffolk foundation trusts), or by named acute trusts running a
shared pathway (North East London: Barts Health, Homerton Healthcare and BHRUT).
Forcing all of those up to "the ICB" would have been a tidier table and a less
true one.

THE VERIFICATION RULE (root rule 14 — state the rule in the file)
-----------------------------------------------------------------
1. Every row's `url` was fetched on the `verified` date and returned HTTP 200.
   No row carries a URL that was pattern-matched, inferred from a sibling
   document, or taken from a search-result summary. Re-check with --check-links.
2. `doc`, `publisher`, `statusNote`, `reviewDate` and `devices` are transcribed
   from the document itself, not from search snippets or trade coverage.
3. `status` is DERIVED, and this is the only derived field. The rule, in full:
      - "Publisher abolished"   the body named on the document ceased to exist
                                on 01/04/2026 (ICB mergers phase 1). Sourced to
                                NHS England Digital's ODS change summary, not
                                inferred from a redirect.
      - "Past review date"      the document PRINTS a review date and that date
                                is in the past today.
      - "Expired"               the publisher itself says the document has
                                expired. Their word, not our arithmetic.
      - "Current"               the document prints a review date in the future.
      - "No review date printed"  exactly that. Never inferred as current.
      - "Not verified"          we could not open a source today. The row still
                                appears, saying so. It never carries a position.
   A row is never promoted to "Current" because it looks recent.
4. Where a source could not be verified, the row says "Not verified" and carries
   NO position, NO devices and NO review date. Publishing nothing is the correct
   output on thin evidence (root rule 14). NHS Essex ICB is the live example:
   the Mid and South Essex SRP 037 URL the old table pointed at now 404s because
   the ICB was abolished, and essex.icb.nhs.uk is behind a Cloudflare challenge
   that this run could not pass. So it says so.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
Coverage is diabetes technology only. A multi-therapy-area formulary directory
is a separate and much larger project and is not started — see the Formulary
follow-on line in OUTSTANDING.md. This file must never be padded out with a
therapy area nobody has verified.

USAGE
    python3 scripts/build_formulary_positions.py               # rebuild the JSON
    python3 scripts/build_formulary_positions.py --check-links # re-open every URL

Run stamp_notice.py after this, then verify.py, then push.
"""
import json
import pathlib
import sys
from datetime import date

OUT = pathlib.Path("data/formulary-positions.json")

VERIFIED = "2026-09-04"

# The 01/04/2026 ICB reconfiguration. Source, quoted in the page copy:
# https://digital.nhs.uk/services/organisation-data-service/upcoming-code-changes/icb-mergers-2026-change-summary
# "There will be 6 new ICBs established across England through the abolition of
#  12 existing ICBs."  42 - 12 + 6 = 36.
ICB_MERGER_SOURCE = (
    "https://digital.nhs.uk/services/organisation-data-service/"
    "upcoming-code-changes/icb-mergers-2026-change-summary"
)

SCHEMA = [
    "body",        # commissioning body / system, as a rep would name it
    "level",       # the level the SOURCE publishes at — not forced up to ICB
    "publisher",   # exact publishing body as printed on the document
    "doc",         # document title, verbatim
    "status",      # derived — see rule 3 in the docstring
    "statusNote",  # the document's own approval/version wording
    "reviewDate",  # as printed on the document, or ""
    "devices",     # named devices as printed, or ""
    "url",         # verified HTTP 200 on `verified`
    "verified",
]

# ---------------------------------------------------------------------------
# The records. Every one of these was opened and read on 04/09/2026.
# `status` is left blank here and computed by derive_status() — never typed in
# by hand, so the rule above is the only thing that can set it.
# ---------------------------------------------------------------------------
RECORDS = [
    dict(
        body="South Yorkshire",
        level="ICB (via IMOC)",
        publisher="NHS South Yorkshire ICB — Integrated Medicines Optimisation Committee (IMOC)",
        doc="Guidance for Continuous Glucose Monitoring (CGM) in Adults and Children with Type 1 and Type 2 Diabetes",
        statusNote="Approved by IMOC November 2023, V1.0.",
        reviewDate="November 2026",
        devices="isCGM or rtCGM offered as a choice to all adults with type 1; advanced rtCGM secondary-care initiated only, not on FP10.",
        url="https://mot.southyorkshire.icb.nhs.uk/south-yorkshire/files/South%20Yorkshire%20Guideline%20Continuous%20Glucose%20Monitoring%20(CGM).pdf",
    ),
    dict(
        body="Hertfordshire & West Essex",
        level="ICB",
        publisher="NHS Hertfordshire and West Essex ICB",
        doc="Continuous Glucose Monitoring for Adults: Position Statement",
        statusNote="Version 3.1, March 2026. Splits devices by cost: low-cost (under £1,000) prescribable on FP10; high-cost (over £1,000) needs additional functionality justified.",
        reviewDate="",
        devices="Low-cost formulary choices: FreeStyle Libre 2 Plus, Dexcom One+, CareSens Air. High-cost: FreeStyle Libre 3 Plus, Dexcom G7, Dexcom G6, Medtronic 3 & 4.",
        url="https://www.hweclinicalguidance.nhs.uk/clinical-policies/continuous-glucose-monitoring-adults-policy/",
    ),
    dict(
        body="Gloucestershire",
        level="ICB",
        publisher="NHS Gloucestershire ICB",
        doc="All age Continuous Glucose Monitoring for patients with Diabetes — Commissioning Policy (Criteria Based Access)",
        statusNote="Adopted December 2022; Version 3, November 2024. Published May 2023.",
        reviewDate="December 2027",
        devices="",
        url="https://www.nhsglos.nhs.uk/wp-content/uploads/2025/01/Continuous-Glucose-Monitoring-1.pdf",
    ),
    dict(
        body="Thames Valley (formerly Buckinghamshire, Oxfordshire & Berkshire West)",
        level="Clinical network — Integrated Diabetes Delivery Network",
        publisher="BOB ICB Integrated Diabetes Delivery Network (hosted on the Buckinghamshire formulary)",
        doc="Guidance for the Prescribing of Continuous Glucose Monitors (CGM) for Adults with Diabetes in Primary Care",
        statusNote="Written and approved by the Integrated Diabetes Delivery Network, February 2023, v1.7. BOB ICB was abolished on 01/04/2026 and its footprint is now NHS Thames Valley ICB; the guidance remains published.",
        reviewDate="",
        devices="Group 1 devices prescribable on FP10; Group 2 devices not on FP10, secondary care only.",
        url="https://www.bucksformulary.nhs.uk/docs/BOB%20ICB%20Guidance%20for%20the%20Prescribing%20of%20Continuous%20Glucose%20Monitors.pdf",
        abolished=True,
    ),
    dict(
        body="Thames Valley (formerly Frimley)",
        level="ICB Medicines Optimisation Group",
        publisher="NHS Frimley ICB Medicines Optimisation Group (now served from NHS Thames Valley ICB's legacy area)",
        doc="Medicines Optimisation Position Statement 015 — Continuous Glucose Monitoring (CGM) in people (adults and children) living with type 1 or type 2 diabetes",
        statusNote="Approved by the Medicines Optimisation Group July 2023; issued August 2023; date of last review recorded as 'NA'. Frimley ICB was abolished on 01/04/2026 — its patch split between Thames Valley, Surrey and Sussex, and Hampshire and Isle of Wight ICBs.",
        reviewDate="July 2025",
        devices="Formulary choices: Freestyle Libre or Dexcom ONE.",
        url="https://thamesvalley.icb.nhs.uk/legacy/frimley/015-MOG-Position-statement-Continuous-Glucose-Monitoring-(CGM).pdf",
        abolished=True,
    ),
    dict(
        body="Kent & Medway",
        level="ICB (via IMOC)",
        publisher="Medicines Optimisation Team, NHS Kent and Medway — approved by IMOC",
        doc="Guidelines for the Prescribing of Continuous Glucose Monitors",
        statusNote="Version 1.1. Approved by IMOC, approval date February 2025. Commented on by EKHUFT, DVH, IMO-DWG, HCP MOGs, IDDN clinical contacts, KMMOG and IMOSG.",
        reviewDate="February 2027",
        devices="",
        url="https://www.kentandmedwayformulary.nhs.uk/media/fjkl452q/km-guidelines-for-the-prescribing-of-continuous-glucose-monitors.pdf",
    ),
    dict(
        body="West Yorkshire",
        level="ICB + Area Prescribing Committee",
        publisher="NHS West Yorkshire ICB / West Yorkshire ICS Area Prescribing Committee",
        doc="Formulary for the Commissioning Position and NHS West Yorkshire Integrated Care Board Policy — isCGM and rtCGM",
        statusNote="April 2023. Carries a device-by-device comparison covering phone compatibility, wear sites and sensor life.",
        reviewDate="",
        devices="Device comparison covers Dexcom, Abbott FreeStyle Libre, Medtronic and GlucoRx AiDEX.",
        url="http://www.wyicsapc.co.uk/wp-content/uploads/2024/02/WYICB_Formulary_for_CGM_21.04.23.pdf",
    ),
    dict(
        body="North East London",
        level="Trusts — shared pathway",
        publisher="Barts Health NHS Trust; Homerton Healthcare NHS Foundation Trust; Barking, Havering and Redbridge University Hospitals NHS Trust",
        doc="Initiation and transfer of prescribing of continuous glucose monitors (CGM) for adults living with type 1 diabetes in North East London",
        statusNote="Version 2, December 2024. CGM initiated and monitored by specialist diabetes teams; List 1 devices needing a Blueteq form stay with specialist teams, List 1 FP10 devices and List 2 devices transfer to primary care.",
        reviewDate="",
        devices="List 1 / List 2 device split; List 1 Blueteq devices are not on FP10.",
        url="https://primarycare.northeastlondon.icb.nhs.uk/wp-content/uploads/2024/12/T1DM-CGM-pathway-transfer-of-care-NEL-V2.pdf",
    ),
    dict(
        body="North East London",
        level="ICB",
        publisher="NHS North East London ICB",
        doc="Type 2 diabetes CGM implementation pathway",
        statusNote="Version 1.0, May 2024. Assesses whether people aged 18 and over living with type 2 diabetes are suitable for isCGM or rtCGM.",
        reviewDate="",
        devices="",
        url="https://primarycare.northeastlondon.icb.nhs.uk/wp-content/uploads/2024/06/T2DM-CGM-implementation-pathway-NEL-V1.0_05.2024.pdf",
    ),
    dict(
        body="North East & North Cumbria",
        level="Regional treatment advisory group",
        publisher="Northern (NHS) Treatment Advisory Group (NTAG), approved by the NENC Medicines Subcommittee",
        doc="Continuous glucose monitoring (CGM) position statement — May 2024",
        statusNote="Version 1.1. Approved by NENC Medicines Subcommittee 10/06/2024; underlying isCGM/rtCGM criteria approved September 2023.",
        reviewDate="",
        devices="NTAG recommends FreeStyle Libre 2, FreeStyle Libre 2 Plus, Dexcom ONE+ and Dexcom One.",
        url="https://ntag.nhs.uk/wp-content/uploads/2024/07/NTAG-CGM-position-statement-review-May-2024-approved-v1.1.pdf",
    ),
    dict(
        body="North East & North Cumbria",
        level="ICS joint formulary",
        publisher="North East and North Cumbria ICS Formulary",
        doc="Formulary chapter 6.1.6 — Diagnostic and monitoring agents for diabetes mellitus",
        statusNote="Formulary entry, live. Dexcom ONE+ listed as Formulary, 'Recommended for use only as per NTAG advice and NHS England Guidance'.",
        reviewDate="",
        devices="Dexcom ONE+ — Formulary.",
        url="https://www.northeastnorthcumbriaformulary.nhs.uk/chaptersSubDetails.asp?FormularySectionID=6&SubSectionRef=06.01.06&SubSectionID=B100",
    ),
    dict(
        body="Surrey & Sussex (Sussex formulary)",
        level="Joint formulary + APC",
        publisher="Sussex Formulary (Sussex Area Prescribing Committee)",
        doc="Formulary 6.4.1a — Continuous Glucose Monitoring (CGM)",
        statusNote="Live formulary entry with traffic-light status. PURPLE (specialist initiation) for adults and children with type 1 diabetes per NICE NG17/NG18. GREEN for initiation in primary care under the diabetes care Locally Commissioned Service, and for diabetes associated with cystic fibrosis on insulin.",
        reviewDate="",
        devices="Dexcom One+ (specialist initiation, two sensors supplied); FreeStyle Libre 2. Dexcom ONE discontinued May 2025 — existing patients to be switched to Dexcom ONE+ at next routine appointment.",
        url="https://www.sussexformulary.nhs.uk/therapeutic-sections/6-endocrine-system/64-diabetes-mellitus/641a-diabetes-diagnosis-and-monitoring/continuous-glucose-monitoring-cgm/",
    ),
    dict(
        body="Hampshire & Isle of Wight",
        level="ICB Priorities Committee",
        publisher="Hampshire and Isle of Wight Integrated Care Board Priorities Committee",
        doc="Policy 7: Continuous Glucose Monitoring for Diabetes in Adults (Criteria Based Access)",
        statusNote="Date of issue April 2023. The policy states it 'will be updated in light of a substantial body of new evidence or new national guidance' rather than on a fixed cycle. Supersedes SHIP Policy 7 (2016) and SHIP Policy 28 Flash Glucose Monitoring (2018).",
        reviewDate="",
        devices="",
        url="https://fundingrequests.scwcsu.nhs.uk/wp-content/uploads/2023/04/Policy-7-Continuous-Glucose-Monitoring-for-Diabetes-in-Adults-v2.pdf",
    ),
    dict(
        body="Hampshire & Isle of Wight",
        level="ICB",
        publisher="NHS Hampshire and Isle of Wight ICB — Medicines Optimisation",
        doc="Diabetes — Medicines Optimisation (CGM and Hybrid Closed Loop hub)",
        statusNote="Live index page. Carries the HIOW Hybrid Closed Loop position statement and prescribing advice, the adult CGM commissioning policy, and CGM / Dexcom / FreeStyle Libre comparison charts.",
        reviewDate="",
        devices="Maintains separate Dexcom and FreeStyle Libre comparison charts.",
        url="https://www.hantsiow.icb.nhs.uk/your-health/medicines-optimisation/information-health-care-professionals/specialities/diabetes",
    ),
    dict(
        body="Suffolk & North East Essex",
        level="ICB + trusts (joint formulary)",
        publisher="Suffolk and North East Essex ICB with East Suffolk and North East Essex NHS Foundation Trust, West Suffolk NHS Foundation Trust and Norfolk and Suffolk NHS Foundation Trust",
        doc="SNEE Formulary chapter 6.1.6 — Continuous Glucose Monitoring",
        statusNote="Live formulary entry. CGM for type 1 diabetes meeting NICE NG17; type 2 in pregnancy (excluding gestational diabetes); and type 2 patients who are hypo-unaware or experiencing recurrent hypoglycaemia.",
        reviewDate="",
        devices="",
        url="https://www.ipswichandeastsuffolkformulary.nhs.uk/chaptersSubDetails.asp?FormularySectionID=6&SubSectionRef=06.01.06&SubSectionID=A100",
    ),
    dict(
        body="Suffolk & North East Essex",
        level="ICB (via IMOC)",
        publisher="Suffolk and North East Essex Integrated Medicines Optimisation Committee",
        doc="SNEE Home Glucose Monitoring guidance",
        statusNote="Final V2, 2024. Recommends cost-effective meters and test strips aligned to the national commissioning recommendations; non-formulary strips should not be routinely prescribed.",
        reviewDate="",
        devices="",
        url="https://suffolkandnortheastessex.icb.nhs.uk/wp-content/uploads/2024/09/SNEE-Home-glucose-monitoring-Final-V2-2024-1.pdf",
    ),
    dict(
        body="Norfolk & Waveney",
        level="ICB + trusts (joint formulary)",
        publisher="Norfolk and Waveney ICB and Group Trust Formulary",
        doc="Formulary chapter 6.1.6 — Blood glucose monitoring",
        statusNote="Live joint ICB-and-trust formulary entry. Carries switch guidance for FreeStyle Libre 2 to FreeStyle Libre 2 Plus (March 2025) and FreeStyle Libre 3 to FreeStyle Libre 3 Plus (August 2025), for clinicians and for patients.",
        reviewDate="",
        devices="FreeStyle Libre 2 Plus and FreeStyle Libre 3 Plus switch pathways published.",
        url="https://www.nhsnorfolkandwaveneyicbformulary.nhs.uk/chaptersSubDetails.asp?FormularySectionID=6&SubSectionRef=06.01.06&SubSectionID=B100",
    ),
    dict(
        body="Cheshire & Merseyside",
        level="Area Prescribing Group",
        publisher="Cheshire and Merseyside Area Prescribing Group (APG)",
        doc="Decision aid for primary care prescribed glucose monitoring in people with Type 1 diabetes",
        statusNote="Version 2.0. Primary-care-prescribed rtCGM and isCGM is Amber Recommended for children and Green for adults in Cheshire and Merseyside, following use of the decision aid in a specialist setting.",
        reviewDate="July 2027",
        devices="",
        url="https://www.cheshireandmerseysideformulary.nhs.uk/docs/files/glucose_monitoring_Type1.pdf",
    ),
    dict(
        body="Cheshire & Merseyside",
        level="Area Prescribing Group",
        publisher="Cheshire and Merseyside Area Prescribing Group (APG)",
        doc="Decision aid for primary care prescribed glucose monitoring in people with Type 2 diabetes",
        statusNote="Version 2.0, published alongside the type 1 decision aid on the Cheshire and Merseyside formulary.",
        reviewDate="",
        devices="",
        url="https://www.cheshireandmerseysideformulary.nhs.uk/docs/files/glucose_monitoring_Type2.pdf",
    ),
    dict(
        body="Humber & North Yorkshire",
        level="ICB",
        publisher="NHS Humber and North Yorkshire ICB — Policy and Pathway Repository",
        doc="Continuous glucose monitoring — ICB-wide policy",
        statusNote="The repository's own note: “policy has now expired, but it is the most up to date version”. Commissioned for adults, young people and children with type 1 diabetes, and for type 2 where the person cannot engage with capillary blood glucose monitoring.",
        reviewDate="31/03/2029",
        devices="",
        url="https://hnyppr.org.uk/w/continuous-glucose-monitoring-policy",
        expired=True,
    ),
    dict(
        body="South West London",
        level="ICB (via IMOC)",
        publisher="NHS South West London ICB — SWL Integrated Medicines Optimisation Committee",
        doc="Continuous Glucose Monitoring Policy in NHS South West London",
        statusNote="Version 1.0. SWL ICB approved funding of CGM for all adults, children and young people with type 1 diabetes in May 2022, in line with NICE NG17 and NG18. Funding for type 2 diabetes is recorded as under review in SWL.",
        reviewDate="",
        devices="",
        url="https://swlimo.southwestlondon.icb.nhs.uk/wp-content/uploads/Continuous-Glucose-Monitoring-Policy-in-NHS-South-West-London-V1.0.pdf",
    ),
    dict(
        body="South West London",
        level="ICB (via IMOC)",
        publisher="NHS South West London ICB — SWL Integrated Medicines Optimisation Committee",
        doc="SWL Continuous Glucose Monitoring Guideline for Adults Living with Type 1 Diabetes",
        statusNote="Live guideline, published on the SWL IMO clinical guidance site alongside the CGM policy and the pan-London type 2 implementation document.",
        reviewDate="",
        devices="",
        url="https://swlimo.southwestlondon.icb.nhs.uk/wp-content/uploads/SWL-Continuous-Glucose-Monitoring-Guideline-for-Adults-Living-with-Type-1-Diabetes.pdf",
    ),
    dict(
        body="London (all ICBs)",
        level="NHS England region",
        publisher="NHS England — London region",
        doc="A pan-London implementation document for continuous glucose sensors for people living with type 2 diabetes",
        statusNote="Published June 2025. Referenced as the type 2 CGM implementation route by South West London IMOC.",
        reviewDate="",
        devices="",
        url="https://www.england.nhs.uk/london/wp-content/uploads/sites/8/2025/06/A-pan-London-implementation-document-for-continuous-glucose-sensors-for-people-living-with-type-2-diabetes.pdf",
    ),
    dict(
        body="Nottingham & Nottinghamshire",
        level="Area Prescribing Committee",
        publisher="Nottinghamshire Area Prescribing Committee (NottsAPC), with secondary care trust Drugs and Therapeutics Committees",
        doc="Continuous Glucose Monitoring in Patients with Diabetes Mellitus Policy",
        statusNote="Version 1.0 developed August 2022 in response to NICE NG17/NG18/NG28; document dated April 2023, revised thereafter. Approved by NottsAPC and the relevant secondary care trust Drugs and Therapeutics Committees.",
        reviewDate="",
        devices="",
        url="https://www.nottsapc.nhs.uk/media/tcibva3n/cgm-commissioning-policy-for-nottingham-and-nottinghamshire.pdf",
    ),
    dict(
        body="Greater Manchester",
        level="Regional medicines management group",
        publisher="Greater Manchester Medicines Management Group (GMMMG)",
        doc="Continuous glucose monitoring (CGM) prescribing guidance",
        statusNote="NHS Greater Manchester Integrated Care CGM prescribing guidance approved and published via GMMMG's Medicines and Devices Recommendations. The page does not print an approval or review date.",
        reviewDate="",
        devices="",
        url="https://gmmmg.nhs.uk/continuous-glucose-monitoring-cgm-guidance/",
    ),
    dict(
        body="Lancashire & South Cumbria",
        level="ICB",
        publisher="NHS Lancashire and South Cumbria ICB",
        doc="Policy for Continuous Glucose Monitoring and Flash Glucose Monitoring to patients with Diabetes Mellitus (reviewed clinical policies)",
        statusNote="Published in the ICB's reviewed clinical policy index. Updated in line with NICE guidance widening CGM and flash access to type 1, some type 2, children and young people, and pregnancy.",
        reviewDate="",
        devices="",
        url="https://www.lancashireandsouthcumbria.icb.nhs.uk/our-work/commissioning-policies/reviewed-clinical-policy",
    ),
    dict(
        body="Cambridgeshire & Peterborough",
        level="ICS + trusts (joint formulary)",
        publisher="Cambridgeshire and Peterborough Integrated Care System with Cambridge University Hospitals NHS Foundation Trust, North West Anglia NHS Foundation Trust, Royal Papworth Hospital NHS Foundation Trust and Cambridgeshire and Peterborough NHS Foundation Trust",
        doc="Cambridgeshire and Peterborough Joint Formulary",
        statusNote="Live joint ICS-and-trust formulary. The CGM entry itself was not located at a stable direct URL on this run, so this row links the formulary root rather than a page we have not opened.",
        reviewDate="",
        devices="",
        url="https://www.cambridgeshireandpeterboroughformulary.nhs.uk/",
    ),
    dict(
        body="Bristol, North Somerset & South Gloucestershire",
        level="ICB",
        publisher="NHS Bristol, North Somerset and South Gloucestershire ICB",
        doc="Continuous Glucose Monitoring Policy — FOI response FOI.ICB-2425/132",
        statusNote="Published January 2026 as a freedom of information response setting out the ICB's CGM policy position. An FOI response is the ICB's own published statement, but it is not a formulary document — treat it as a pointer to the position, not as the formulary entry.",
        reviewDate="",
        devices="",
        url="https://bnssghealthiertogether.org.uk/wp-content/uploads/2026/01/FOI.ICB-2425_132-Continuous-Glucose-Monitoring-Final-Response.pdf",
    ),
    # -------- the honest empty state. Do not fill this in without a source. ----
    dict(
        body="Essex (formerly Mid & South Essex)",
        level="ICB",
        publisher="NHS Essex ICB (created 01/04/2026 — NHS Mid and South Essex ICB abolished)",
        doc="SRP 037 Continuous Glucose Monitoring",
        statusNote="NOT VERIFIED on 04/09/2026. The Mid and South Essex URL this Hub previously cited now returns HTTP 404, and essex.icb.nhs.uk is behind a bot challenge this run could not pass. No position, device list or date is published here until the policy is opened on the new ICB's own site.",
        reviewDate="",
        devices="",
        url="",
        unverified=True,
    ),
]


def derive_status(r):
    """The ONLY place status is set. See rule 3 in the module docstring."""
    if r.get("unverified"):
        return "Not verified"
    if r.get("expired"):
        return "Expired — publisher says it is still the current version"
    if r.get("abolished"):
        return "Publisher abolished 01/04/2026 — document still published"
    rd = (r.get("reviewDate") or "").strip()
    if not rd:
        return "No review date printed"
    parsed = _parse_review(rd)
    if parsed is None:
        return "No review date printed"
    return "Past review date" if parsed < date.today() else "Current"


MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}


def _parse_review(s):
    """'November 2026' or '31/03/2029' -> a date. Anything else -> None.

    Month-only dates are read as the LAST day of that month: a document under
    review in November 2026 is not past its review date on 1 November.
    """
    s = s.strip()
    if "/" in s:
        try:
            d, m, y = (int(x) for x in s.split("/"))
            return date(y, m, d)
        except (ValueError, TypeError):
            return None
    parts = s.split()
    if len(parts) == 2 and parts[0].lower() in MONTHS:
        m, y = MONTHS[parts[0].lower()], int(parts[1])
        nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        return date.fromordinal(nxt.toordinal() - 1)
    return None


def build():
    rows = []
    for r in RECORDS:
        r = dict(r)
        r["status"] = derive_status(r)
        r["verified"] = VERIFIED
        rows.append([r.get(k, "") for k in SCHEMA])

    bodies = sorted({r[0] for r in rows})
    doc = {
        "dataAsOf": VERIFIED,
        "therapyArea": "Diabetes technology — continuous glucose monitoring (CGM) and hybrid closed loop (HCL)",
        "icbMergerSource": ICB_MERGER_SOURCE,
        "method": (
            "Every row's source URL was opened and returned HTTP 200 on dataAsOf. Titles, "
            "publishers, versions, approval wording, review dates and device names are "
            "transcribed from the document itself, never from a search summary or trade "
            "coverage. 'level' records the level the source actually publishes at — an Area "
            "Prescribing Committee, a regional advisory group, a joint ICB-and-trust "
            "formulary or named acute trusts — and is never forced up to 'ICB' for tidiness. "
            "'status' is the only derived field: it compares the review date PRINTED on the "
            "document with dataAsOf, defers to the publisher's own word where they say a "
            "document has expired, and is never promoted to 'Current' because a document "
            "looks recent. A body we could not open a source for appears with status 'Not "
            "verified' and carries no position, no devices and no date."
        ),
        "scope": (
            "Diabetes technology only. This is not a national multi-therapy-area formulary "
            "directory and must not be padded out into one without the same verification."
        ),
        "bodyCount": len(bodies),
        "rowCount": len(rows),
        "schema": SCHEMA,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote %s — %d documents across %d bodies" % (OUT, len(rows), len(bodies)))
    for st in sorted({r[SCHEMA.index("status")] for r in rows}):
        n = sum(1 for r in rows if r[SCHEMA.index("status")] == st)
        print("  %-58s %d" % (st, n))


def check_links():
    """Re-open every URL. This is the repeatable half of the process."""
    import urllib.request
    import urllib.error
    bad = 0
    for r in RECORDS:
        url = r.get("url") or ""
        if not url:
            print("SKIP (no url, status Not verified)  %s" % r["body"])
            continue
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                code = resp.getcode()
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:                      # noqa: BLE001
            code = "ERR %s" % type(e).__name__
        ok = code == 200
        bad += 0 if ok else 1
        print("%-10s %s  %s" % (code, r["body"], url))
    print("\n%d link(s) not returning 200" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    if "--check-links" in sys.argv:
        sys.exit(check_links())
    build()
