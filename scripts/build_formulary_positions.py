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
                                inferred from a redirect. THE FLAG FOLLOWS THE
                                PUBLISHER PRINTED ON THE DOCUMENT, NOT THE
                                GEOGRAPHY. An ICB named as publisher and listed
                                in the ODS abolition table sets the flag. An
                                Area Prescribing Committee, an Integrated Care
                                System partnership or a named acute trust does
                                NOT, because those bodies were not abolished —
                                a note on the row records the ICB change
                                instead. This is why the Sussex APC and the
                                Cambridgeshire and Peterborough ICS-and-trust
                                formulary rows are not flagged while the
                                Hertfordshire and West Essex, Norfolk and
                                Waveney and Suffolk and North East Essex rows
                                are.
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

# A bare "Mozilla/5.0" is rejected by some NHS site firewalls (the West
# Yorkshire APC PDF answers 403 to it and 200 to a browser), so link checks
# send a full browser string. A false 403 is as damaging as a missed 404.
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")

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
        abolished=True,
        abolitionNote="NHS Hertfordshire and West Essex ICB was abolished on 01/04/2026 into NHS Central East ICB. The site carrying this position statement says so itself: \u201cThe last day of operation for Hertfordshire and West Essex ICB was 31 March 2026. The information on this website has not been updated since 31 March 2026.\u201d The guidance is therefore frozen, not maintained.",
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
        abolished=True,
        abolitionNote="NHS Suffolk and North East Essex ICB was abolished on 01/04/2026 (ODS change summary). The three foundation-trust partners named on this joint formulary continue to exist.",
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
        abolished=True,
        abolitionNote="Published by the Integrated Medicines Optimisation Committee of NHS Suffolk and North East Essex ICB, abolished on 01/04/2026 (ODS change summary).",
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
        abolished=True,
        abolitionNote="NHS Norfolk and Waveney ICB was abolished on 01/04/2026 (ODS change summary). The joint ICB-and-trust formulary is still published under the abolished ICB's name.",
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
        statusNote="Live joint ICS-and-trust formulary. The CGM entry itself was not located at a stable direct URL on this run, so this row links the formulary root rather than a page we have not opened. Note the commissioner has changed: NHS Cambridgeshire and Peterborough ICB was abolished on 01/04/2026 and its functions passed to NHS Central East ICB, alongside Bedfordshire, Luton and Milton Keynes and Hertfordshire and West Essex. The formulary itself is published by the ICS with four foundation trusts, which is why this row is not flagged as an abolished publisher.",
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
    dict(
        body="Staffordshire & Stoke-on-Trent",
        level="ICB — Quality and Safety Committee",
        publisher="NHS Staffordshire and Stoke-on-Trent ICB Quality and Safety Committee",
        doc="Flash Glucose Monitoring and Dexcom One Commissioning Policy",
        statusNote="Version 3, ratified by the ICB Quality and Safety Committee on 11 August 2023 and issued the same day; first issued 25 April 2019. The document prints its review date as \u201cThree years from issue date unless significant changes are required\u201d, which is 11/08/2026.",
        reviewDate="11/08/2026",
        devices="FreeStyle Libre 2 \u2014 isCGM via the reader, rtCGM via the LibreLink app from July 2023. Dexcom ONE \u2014 rtCGM, same criteria as flash but usable from age 2. Specialist initiation, then primary care continues prescribing beyond the provider's 6-month review. Eligibility is type 1 needing intensive monitoring more than 8 times a day, any diabetes on haemodialysis and insulin, cystic-fibrosis-related diabetes on insulin, and pregnancy in type 1.",
        url="https://staffsstoke.icb.nhs.uk/your-nhs-integrated-care-board/our-publications/governance-handbook/all-policies/commissioning/flash-glucose-and-dexcom-one-commissoning-policy-v3-aug-2023/?layout=file",
    ),
    dict(
        body="Birmingham & Solihull",
        level="ICB \u2014 Integrated Medicines Optimisation Committee (via DMMAG)",
        publisher="Diabetes Medicines Management Advisory Group (DMMAG) on behalf of the Birmingham and Solihull (BSol) Integrated Medicines Optimisation Committee",
        doc="BSol CGM Device Comparison Table",
        statusNote="Version 1.2, publication date July 2024. The document prints \u201cReview date: 2 years or sooner if needed\u201d, which is July 2026. Prices are quoted from the Drug Tariff, May 2024.",
        reviewDate="July 2026",
        devices="Four devices, all \u201cfirst line option in line with ICB policy\u201d: FreeStyle Libre 2 (age 4+, \u00a3912.50/yr), FreeStyle Libre 2 Plus (age 2+, \u00a3912.50/yr), Dexcom ONE (age 2+, \u00a3913.50/yr including 4 transmitters) and Dexcom ONE+ (age 2+, \u00a3911.42/yr). The table records FreeStyle Libre 2 and Dexcom ONE as being discontinued within 12 months, with clinicians to upgrade patients to the Plus and ONE+ versions on repeat prescription.",
        url="https://www.birminghamandsurroundsformulary.nhs.uk/docs/files/CGM%20Device%20Comparison%20Table%20July%202024.pdf",
    ),
    dict(
        body="Black Country",
        level="ICB formulary",
        publisher="NHS Black Country ICB \u2014 Black Country Formulary, chapter 06.01.06",
        doc="Black Country Formulary 06.01.06 \u2014 Diagnostic and monitoring agents for diabetes mellitus",
        statusNote="Live formulary entry. CGM is Formulary for eligible type 1 patients and for type 2 in line with RMOC criteria, referencing the NHS England national funding arrangements for relevant diabetes patients.",
        reviewDate="",
        devices="CareSens Air, Dexcom ONE and Dexcom ONE+, FreeStyle Libre 2 and FreeStyle Libre 2 Plus \u2014 all Formulary. The chapter carries two supply warnings in the publisher's own words: Dexcom ONE \u201cwill be removed from the drug tariff as of 31st March 2026\u201d with patients to transition to ONE+ before the end of December 2025 and new prescriptions to be ONE+, and \u201cFreestyle Libre 2 will be discontinued by August 2025\u201d.",
        url="https://www.blackcountryformulary.nhs.uk/chaptersSubDetails.asp?FormularySectionID=6&SubSectionRef=06.01.06&SubSectionID=A100",
    ),
    dict(
        body="Leicester, Leicestershire & Rutland",
        level="Area Prescribing Committee",
        publisher="Leicester, Leicestershire and Rutland Area Prescribing Committee (LLR APC) Medicines Formulary",
        doc="LLR APC Formulary 06.01.06 \u2014 Blood glucose monitoring",
        statusNote="Live formulary entry. Both devices are approved \u201cwhere a patient meets the criteria detailed in the LLR APC position statement\u201d. The chapter is explicitly closed: \u201cNo other CGM sensors currently approved for use in Leicestershire.\u201d",
        reviewDate="",
        devices="FreeStyle Libre 2 Plus and Dexcom ONE+ only. This is one of the most restrictive CGM formularies captured here \u2014 no other sensor is approved.",
        url="https://www.leicestershireformulary.nhs.uk/chaptersSubDetails.asp?FormularySectionID=6&SubSectionRef=06.01.06&SubSectionID=B100",
    ),
    dict(
        body="Devon",
        level="ICB formulary \u2014 published on two place-based sites",
        publisher="Devon Formulary and Referral Website (NHS Devon), North & East and South & West",
        doc="Devon Formulary 6.1.7 \u2014 Continuous Glucose Monitors (CGM)",
        statusNote="Page last updated 18 October 2024. The page states of itself: \u201cThis page is currently under review.\u201d The North & East and South & West sites publish the same CGM chapter, so this is one Devon position, not two \u2014 recorded as one row rather than inflating the count.",
        reviewDate="",
        devices="Dexcom ONE+ (rtCGM, age 2+, 10-day sensor, \u00a324.97 per sensor, \u00a3911.41 a year) and FreeStyle Libre 2 Plus (age 2+, 15-day sensor, \u00a337.50 per sensor, \u00a3912.50 a year; isCGM with the reader, rtCGM with the LibreLink app, and rtCGM via the Omnipod 5 app when used as part of a hybrid closed loop with the Omnipod 5 pump). Both amber \u2014 specialist teams usually initiate, but initiation by confident primary care clinicians is accepted. Routinely commissioned for all type 1 and insulin-treated type 3c, and for type 2 meeting the local commissioning policy.",
        url="https://northeast.devonformularyguidance.nhs.uk/formulary/chapters/6-endocrine/6-1-drugs-used-in-diabetes/6-1-7-continuous-glucose-monitors-cgm",
    ),
    dict(
        body="Dorset",
        level="ICB formulary + Diabetes Clinical Network",
        publisher="NHS Dorset \u2014 Dorset Formulary, chapter 06.01.06 Continuous Glucose Monitoring",
        doc="Dorset Formulary 06.01.06 \u2014 Continuous Glucose Monitoring (isCGM & rtCGM)",
        statusNote="Live formulary entry carrying a \u201cCommissioning statement on the use of prescribable continuous glucose monitoring (CGM) sensors April 2026\u201d. ACCESS IS NARROWING: the chapter states that \u201cthe Diabetes Clinical Network has now approved an updated version of the NHS Dorset policy which will reduce access to CGM in type 2 diabetes\u201d, with SystmOne searches issued so PCNs can identify people prescribed CGM outside commissioning guidance. NHS Dorset audits new requests and asks practices to decline recommendations that fall outside the statement.",
        reviewDate="",
        devices="Formulary: FreeStyle Libre 2 Plus, Dexcom ONE+ and GlucoRx Aidex. FreeStyle Libre 3 Plus is Formulary for HYBRID CLOSED LOOP ONLY, age 2 and over, and only for use with the mylife Loop AID system. Primary care must code which specialist initiated the request and the qualifying diagnosis at first prescription.",
        url="https://www.dorsetformulary.nhs.uk/chaptersSubDetails.asp?FormularySectionID=6&SubSectionRef=06.01.06&SubSectionID=A100",
    ),
    dict(
        body="Herefordshire & Worcestershire",
        level="ICB formulary + four commissioning policies",
        publisher="NHS Herefordshire and Worcestershire — Herefordshire & Worcestershire Formulary, chapter 06.01.06",
        doc="Herefordshire & Worcestershire Formulary 06.01.06 — Diagnostic and monitoring agents for diabetes mellitus",
        statusNote="Live formulary entry. Unusually, the position is split across FOUR separate commissioning policies rather than one: real-time CGM in adults, intermittently scanned (flash) CGM in adults, CGM during pregnancy for people with insulin-treated diabetes, and CGM in children and young people. Every device is traffic-lighted RESTRICTED, and each carries all four policies.",
        reviewDate="",
        devices="Dexcom ONE (being replaced by ONE Plus), Dexcom ONE Plus, FreeStyle Libre 2 (being replaced by 2 Plus), FreeStyle Libre 2 Plus, FreeStyle Libre 3 and FreeStyle Libre 3 Plus — all Restricted. Both FreeStyle Libre 3 products are restricted to people living with type 1 diabetes only. The formulary records FreeStyle Libre 3 as discontinued in December 2025.",
        url="https://www.hereworcsformulary.nhs.uk/chaptersSubDetails.asp?FormularySectionID=6&SubSectionRef=06.01.06&SubSectionID=A100",
    ),
    dict(
        body="Shropshire, Telford & Wrekin",
        level="ICB commissioning policy \u2014 written with named trusts",
        publisher="NHS Shropshire, Telford and Wrekin \u2014 Medicines Management Team, Delivery and Transformation",
        doc="Commissioning Policy: Continuous Glucose Monitoring for adults with insulin-treated diabetes (including pregnancy)",
        statusNote="Version 1, approval date 08/01/2024, review date printed on the document as 08/01/2026. Authored by Claire Hand, Lead Medicines Optimisation Pharmacy Technician. Consulted with diabetes consultants and lead diabetes nurses at Shrewsbury and Telford Hospitals, the adult diabetes lead at Shropshire Community Health Trust, and the STW Diabetes Clinical Advisory Group \u2014 so the named trusts are on the face of the policy, not just the ICB.",
        reviewDate="08/01/2026",
        devices="Prescribable CGM \u2014 FreeStyle Libre 2 (isCGM with the reader, rtCGM with a smartphone) and Dexcom ONE (rtCGM) \u2014 can be initiated in any care setting. Specialist CGM such as Dexcom G6 and the Guardian 4 sensor sits outside that route. All individuals with type 1 are eligible; type 2 must meet stated criteria. Where several formulary devices meet the person's needs, the lowest-cost one is offered; use is reviewed every 6 months where possible.",
        url="https://www.shropshiretelfordandwrekin.nhs.uk/wp-content/uploads/20240129-CGM-for-Adults-with-insulin-treated-diabetes-including-pregnancy.pdf",
    ),
    dict(
        body="Somerset",
        level="ICB formulary \u2014 service delivered by a named trust",
        publisher="NHS Somerset \u2014 Somerset Joint Formulary, chapter 06.01.06 Continuous glucose monitoring",
        doc="Somerset Formulary 06.01.06 \u2014 Continuous glucose monitoring (CGM)",
        statusNote="Live formulary entry. CGM is \u201cusually managed via SFT Diabetes Intermediate Care\u201d \u2014 Somerset NHS Foundation Trust, named on the formulary as the delivering service. Approved for all type 1 and type 2 patients on multiple daily insulin injections meeting stated criteria: recurrent or severe hypoglycaemia, impaired hypoglycaemia awareness, a condition or disability preventing capillary monitoring, needing to self-measure at least 8 times a day, or insulin-treated type 2 who would otherwise need a care worker to monitor.",
        reviewDate="",
        devices="Nine rtCGM sensors on formulary \u2014 the widest CGM formulary captured here: FreeStyle Libre 2 Plus (15-day), FreeStyle Libre 3 Plus (15-day), Dexcom ONE+ (10-day), GlucoRx Aidex (15-day), Accu-Chek SmartGuide (14-day), ALLY (15-day), CareSens Air (15-day), Glucomen iCan (15-day) and Sibionics GS3-R (14-day). FreeStyle Libre 2 is listed Non Formulary, marked discontinued.",
        url="https://www.somersetformulary.nhs.uk/chaptersSubDetails.asp?FormularySectionID=6&SubSectionRef=06.01.06&SubSectionID=E100",
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
        # An abolition note is appended to the row's own wording rather than
        # replacing it: the document still says what it says, and the reader
        # needs both facts.
        if r.get("abolitionNote"):
            r["statusNote"] = (r.get("statusNote", "").rstrip()
                               + " " + r["abolitionNote"]).strip()
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
        req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
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
