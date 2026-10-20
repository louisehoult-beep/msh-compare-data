"""digital_lane_rules.py: the stated rules for the digital health lane (20/10/2026).

WHY THIS EXISTS. The Hub's tender and company-award feeds are CPV 33 (medical
equipment) by construction, and refresh_open_tenders.py excludes "software",
"licence", "saas" and "it services" on purpose. That is right for those feeds and
is not changed. It also meant a health technology seller saw zero open tenders on
the digital page while 258 NHS-buyer software and IT notices already sat in
data/framework-awards.json. The digital lane is a SEPARATE file
(data/digital-lane.json) with its own rule, so the medical feeds do not regress.
Source: reports/Hub health tech intelligence gap.md, build plan, "Next 30 days".

THE LANE RULE (stated in the output file too, root rule: state the rule).
  A Find a Tender or Contracts Finder notice is in the lane when BOTH
    (a) the buyer name is an NHS body: contains "NHS", "Integrated Care Board" or
        "Health Board" (the same pattern refresh_framework_awards.py uses; bare
        "Trust" is not a match, because academy and housing trusts flood it), and
    (b) a CPV code on the notice begins 48 (software package and information
        systems) or 72 (IT services: consulting, software development, Internet
        and support).
  An Atamis (NHS eCommercial) opportunity carries no CPV code, so its own
  "Category" text stands in for (b): DIGITAL_CATEGORY below. Every Atamis
  authority is an NHS body by construction of that system.

THE CLINICAL FLAG. CPV 48 and 72 are bought for payroll, finance, HR, printing and
network kit as much as for clinical systems, so being in the lane is not a claim
that a row is health technology. A row is flagged `clinical` only when its TITLE
matches CLINICAL_DIGITAL. The speciality panel shows clinical rows only; the file
holds every lane row so the count of what was left out is visible.
"""
import re

NHS_BUYER = re.compile(r"\bNHS\b|\bIntegrated Care Board\b|\bHealth Board\b", re.I)

DIGITAL_CPV_PREFIXES = ("48", "72")

# Atamis "Category" values that stand in for CPV 48/72. Hardware, printers,
# cabling, telecoms lines and network kit are NOT here: those are estates and
# infrastructure, and the capital-estates page is their home.
DIGITAL_CATEGORY = re.compile(
    r"\b(software|information systems?|information technology|SaaS|"
    r"IT (?:support|services|managed|management|consultancy|software)|^IT$|"
    r"IT/IS|data (?:services|analysis|software)|database|"
    r"management information systems|web platform)\b", re.I)

# Clinical digital terms, matched on the TITLE only. Each term names a clinical
# system or a regulated digital product, never a department or a bare word.
# Bare "software", "digital", "IT" and "licence" are refused for the reason the
# digital speciality rule in build_speciality_panels.py gives: they reach film
# licences, address look-ups, facilities software and DocuSign.
CLINICAL_DIGITAL = re.compile(
    r"(?<![\w-])("
    r"electronic patient records?|(?-i:EPR)|electronic health records?|(?-i:EHR)|"
    r"patient administration system|clinical systems?|clinical data repository|"
    r"electronic prescrib\w*|e-?prescrib\w*|(?-i:ePMA)|"
    r"electronic document management|(?-i:EDMS)|e-?observations?|"
    r"cyber ?security|interoperab\w*|clinical decision support|digital dictation|"
    r"speech recognition|shared care records?|health information exchange|"
    r"(?-i:AI)|artificial intelligence|machine learning|ambient voice|(?-i:AVT)|"
    r"virtual wards?|remote (?:patient )?monitoring|tele-?(?:health|medicine|dermatology)|"
    r"patient portal|patient engagement (?:platform|portal)|online consultation|"
    r"federated data platform|(?-i:FDP)|video consultations?|"
    r"digital health(?: systems?| services?)?|health (?:and social care )?apps?|"
    r"digital primary care|electronic pre-?operative assessment|endoscopy management systems?|"
    r"(?-i:PACS)|radiology information system|(?-i:RIS)|laboratory information|(?-i:LIMS)|"
    r"digital pathology|software as a medical device|(?-i:SaMD)|(?-i:DTAC)|"
    r"population health management"
    r")(?![\w-])", re.I)


def nhs_buyer(name):
    return bool(NHS_BUYER.search(name or ""))


def digital_cpvs(cpvs):
    return sorted({str(c) for c in (cpvs or []) if str(c)[:2] in DIGITAL_CPV_PREFIXES})


def in_lane(buyer, cpvs):
    return nhs_buyer(buyer) and bool(digital_cpvs(cpvs))


def digital_category(category):
    return bool(DIGITAL_CATEGORY.search((category or "").strip()))


def clinical(title):
    return bool(CLINICAL_DIGITAL.search(title or ""))
