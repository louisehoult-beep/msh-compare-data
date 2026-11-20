#!/usr/bin/env python3
"""Key Opinion Leader (KOL) finder: writes data/kol-finder.json for Build Your Network (page 1882).

WHAT THIS IS
------------
Every person below was read on 22/10/2026 from a public page of the body named,
and the page is recorded against them (source_url). Nothing is carried from memory
or from a search snippet. Dermatology first, then continence, wound care and tissue viability, vascular access and diabetes; the structure holds any
speciality in data/speciality-map.json (canonicalSpecialities), and a speciality
with no checked people renders an honest empty state.

SOURCES READ (22/10/2026; Wounds UK editorial board added 29/10/2026)
-------------------------
WUK   Wounds UK journal, wounds-uk.com/about-us/editorial-board/ (read 29/10/2026;
      that source carries its own checked date).
BAD   British Association of Dermatologists, /about-the-bad/leadership-team
      (officers, regional representatives, co-opted and ex-officio members), and
      badannualmeeting.co.uk /keynotes-speakers/ (106th Annual Meeting, Manchester,
      30 June to 2 July 2026, plenary speakers) and /organising-committee/.
      Paid staff on the leadership page are deliberately NOT listed: they are
      employees, not clinical opinion leaders.
BDNG  British Dermatological Nursing Group, bdng.org.uk home page "Committee"
      tab, cross-checked against the Companies House officers register (company
      07035369). Directors only; the company secretary is administrative.
PCDS  Primary Care Dermatology Society, pcds.org.uk/committee-profile and
      /trustees. Roles are copied from the page. The page's own abbreviations
      that cannot be expanded from the page (DfD, PCP) are left out of role text.
SDS   Scottish Dermatological Society, sds.org.uk home page: the president's own
      message and the secretary named for membership nominations.

NOT FOUND, SAID SO
------------------
NHS Supply Chain's medical technology contacts page (read 22/10/2026) has no
dermatology, skin or wound care section, so supply chain contacts for dermatology
is an honest empty state pointing at the category directory. Evidence authors are
limited to people a source page names as an author or guideline chair; no
publication list has been read, so none is claimed.

PRIVACY (Medical Sales Register privacy rule: public sources only)
-----------------------------------------------------------------
Name, public role, organisation as the body itself shows it, and the page it came
from. No email, phone, address or private data. LinkedIn is a SEARCH link built from
name plus body, never a matched or stored profile. Anyone listed can ask for removal:
names added to data/contacts-optout.json ("names") are filtered out here.

USAGE
    python3 scripts/build_kol_finder.py          # write data/kol-finder.json
    python3 scripts/stamp_notice.py              # re-stamp the ownership notice
    python3 scripts/check_kol_finder.py          # gate (exit 0 = pass)
"""
import json
import pathlib
import datetime
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "kol-finder.json"
CHECKED = "2026-11-12"  # all 14 script sources re-read 12/11/2026; no people changes

CLASSES = [
    ("board", "Board and committee members"),
    ("speaker", "Conference speakers"),
    ("evidence", "Evidence authors"),
    ("editor", "Journalists, editors and commentators"),
    ("supply", "Supply chain contacts"),
    ("clinical", "Named hospital unit consultants"),
    ("trust", "Trust leaders and managers"),
]
# Key opinion leaders are the people a professional body puts forward; the other classes
# are people who run or buy for a trust. The finder's "Key opinion leaders" filter uses this.
KOL_CLASSES = ("board", "speaker", "evidence", "editor")

SOURCES = {
    "bad-leadership": {
        "short": "BAD leadership team",
        "body": "British Association of Dermatologists (BAD)",
        "title": "Meet the Leadership Team",
        "url": "https://www.bad.org.uk/about-the-bad/leadership-team",
        "note": "Officers, regional representatives, co-opted and ex-officio members of the Executive Committee, with terms as shown. Paid staff are not listed."},
    "bad-speakers": {
        "short": "BAD Annual Meeting speakers",
        "body": "British Association of Dermatologists (BAD) Annual Meeting",
        "title": "Keynote, Invited and Guest Speakers (106th Annual Meeting, Manchester, 30 June to 2 July 2026)",
        "url": "https://badannualmeeting.co.uk/keynotes-speakers/",
        "note": "Plenary speakers only. The programme page gives names without affiliations, so none is shown."},
    "bad-organising": {
        "short": "BAD Annual Meeting committee",
        "body": "British Association of Dermatologists (BAD) Annual Meeting",
        "title": "Conference and Events Committee 2026 to 2027",
        "url": "https://badannualmeeting.co.uk/organising-committee/",
        "note": "Committee members who are clinicians."},
    "bdng-committee": {
        "short": "BDNG committee",
        "body": "British Dermatological Nursing Group (BDNG)",
        "title": "Committee",
        "url": "https://bdng.org.uk/",
        "note": "Committee tab on the home page."},
    "bdng-companies-house": {
        "short": "Companies House officers",
        "body": "Companies House",
        "title": "Officers of The British Dermatological Nursing Group (company 07035369)",
        "url": "https://find-and-update.company-information.service.gov.uk/company/07035369/officers",
        "note": "Statutory register of directors. Used to confirm the BDNG trustees."},
    "pcds-committee": {
        "short": "PCDS committee",
        "body": "Primary Care Dermatology Society (PCDS)",
        "title": "The PCDS Committee",
        "url": "https://www.pcds.org.uk/committee-profile",
        "note": "Roles as the page shows them."},
    "pcds-trustees": {
        "short": "PCDS trustees",
        "body": "Primary Care Dermatology Society (PCDS)",
        "title": "Meet the Trustees",
        "url": "https://www.pcds.org.uk/trustees",
        "note": "Trustees heading; some entries state no trustee role."},
    "sds-home": {
        "short": "SDS home page",
        "body": "Scottish Dermatological Society (SDS)",
        "title": "Welcome to the SDS",
        "url": "https://www.sds.org.uk/",
        "note": "President's message and the secretary named for nominations."},
    "acp-exec": {
        "short": "ACP executive",
        "body": "Association for Continence Professionals (ACP, also known as the Association for Continence Advice)",
        "title": "Meet Our Executive Members",
        "url": "https://acpcontinence.co.uk/acp-exec/",
        "note": "Executive members as the page lists them. Each member is shown with the role the page gives. Commercial advisors and patrons are on separate pages and are not listed."},
    "tvs-charity": {
        "short": "TVS trustees (Charity Commission)",
        "body": "Tissue Viability Society (TVS)",
        "title": "Trustees of the Tissue Viability Society (charity 1180844), Charity Commission register",
        "url": "https://register-of-charities.charitycommission.gov.uk/en/charity-search/-/charity-details/5129933/trustees",
        "note": "Statutory register of trustees, under the Open Government Licence v3.0. The Society's own site was not found, so the register is the source."},
    "vasbi-team": {
        "short": "VASBI team",
        "body": "Vascular Access Society of Britain and Ireland (VASBI)",
        "title": "Meet the Team",
        "url": "https://www.vasbi.org.uk/about/meet-the-team/",
        "note": "VASBI's remit is vascular access for haemodialysis (fistulas, grafts and lines). Clinicians only; the patient representative is not listed."},
    "abcd-committee": {
        "short": "ABCD committee",
        "body": "Association of British Clinical Diabetologists (ABCD)",
        "title": "ABCD Committee",
        "url": "https://abcd.care/committee",
        "note": "The officers the page names, plus the DTN-UK Chair it lists alongside them. The page's Committee Members section was empty when read, and it shows no affiliations."},
    "wuk-editorial": {
        "short": "Wounds UK editorial board",
        "body": "Wounds UK (journal)",
        "title": "Wounds UK Editorial board",
        "url": "https://wounds-uk.com/about-us/editorial-board/",
        "checked": "2026-10-29",
        "note": "The journal's own editorial board page. Only the Clinical Editor and Academic Editor have a role on the page; the others are listed under the Editorial board heading. Affiliations are copied as the page shows them."},
}

DERM = ["dermatology"]
DERM_PC = DERM  # canonicalSpecialities has no primary care id; the PCDS body note says primary care

# person: name -> dict(appearances=[...], specialities, classes)
PEOPLE = {}


def add(name, source, role, org=None, classes=("board",), term=None, specialities=DERM, body=None, region=None, shown_as=None, note=None):
    p = PEOPLE.setdefault(name, {"name": name, "appearances": [], "specialities": [], "classes": []})
    p["appearances"].append({
        "body": body, "role": role, "organisation": org, "term": term,
        "source": source, "source_url": SOURCES[source]["url"], "checked": SOURCES[source].get("checked", CHECKED),
    })
    if shown_as:
        p["appearances"][-1]["spelling_on_source"] = shown_as
    if note:
        p["appearances"][-1]["note"] = note
    for s in specialities:
        if s not in p["specialities"]:
            p["specialities"].append(s)
    for c in classes:
        if c not in p["classes"]:
            p["classes"].append(c)
    if region and not p.get("region"):
        p["region"] = region


BAD = "BAD"
L = "bad-leadership"
# Officers
add("Dr Anshoo Sahota", L, "President", "Barts Health NHS Trust", term="July 2026 to July 2028", body=BAD)
add("Dr Tamara Griffiths", L, "Immediate Past President", "University of Manchester / Salford Royal NHS Foundation Trust", term="July 2026 to July 2027", body=BAD)
add("Dr Stephen Keohane", L, "Clinical Vice President", "Portsmouth Hospitals University NHS Trust", term="July 2026 to July 2028", body=BAD)
add("Dr Simon Tso", L, "Honorary Treasurer", "South Warwickshire University NHS Foundation Trust", term="July 2025 to July 2028", body=BAD)
add("Dr Victoria Swale", L, "Honorary Secretary", "Royal Free London NHS Foundation Trust", term="July 2025 to July 2027", body=BAD)
add("Dr Graham Johnston", L, "Assistant Honorary Secretary", "University Hospitals of Leicester NHS Trust", term="July 2025 to July 2027", body=BAD)
add("Professor John Lear", L, "Research Vice President", "Cheshire Hospitals NHS Foundation Trust", term="July 2025 to July 2027", body=BAD, classes=("board", "evidence"))
add("Professor Minal Singh", L, "Education Vice President", "Salford Royal NHS Foundation Trust", term="July 2023 to July 2027", body=BAD)
add("Professor John McGrath", L, "Editor, British Journal of Dermatology (BJD)", "Guy's and St Thomas' NHS Foundation Trust", term="July 2024 to July 2029", body=BAD, classes=("board", "editor"))
# Regional representatives
for n, r, t in [
    ("Dr Manpreet Sagoo", "Trainee Representative", "July 2025 to July 2027"),
    ("Dr Domniki Iatropoulou", "Trainee Co-representative", "July 2025 to July 2027"),
    ("Dr Elizabeth McMullen", "Republic of Ireland and Northern Ireland Representative", "July 2024 to July 2027"),
    ("Dr Paula Beattie", "Scotland Representative", "October 2025 to July 2027"),
    ("Dr Richard Goodwin", "Wales Representative", "July 2024 to July 2027"),
    ("Dr Nasim Rouhani", "North London Representative", "July 2025 to July 2028"),
    ("Dr Helen Frow", "South West Representative", "July 2025 to July 2028"),
    ("Dr Saul Halpern", "South East Representative", "July 2023 to July 2027"),
    ("Dr Bjorn Thomas", "South London Representative", "July 2026 to July 2029"),
    ("Dr Inge Kreuser-Genis", "Oxford and Thames Representative", "January 2025 to July 2027"),
    ("Dr Pamela Todd", "East of England Representative", "July 2025 to July 2028"),
    ("Professor Viktoria Eleftheriadou", "West Midlands Representative", "July 2025 to July 2028"),
    ("Dr Harriet O'Neill", "East Midlands Representative", "July 2025 to July 2028"),
    ("Dr Emma McMullen", "North West Representative", "July 2026 to July 2029"),
    ("Dr Sura Sahib", "Yorkshire and The Humber Representative", "July 2026 to July 2029"),
    ("Dr Sharmela Darné", "North East Representative", "July 2026 to July 2029"),
]:
    add(n, L, r, None, term=t, body=BAD)
# Co-opted and ex-officio
add("Dr Shalini Narayan", L, "Chair, Specialty Advisory Committee of the Joint Royal Colleges of Physicians Training Board", None, term="Co-opted member", body=BAD)
add("Professor Nick Levell", L, "Getting It Right First Time (GIRFT) Lead for Dermatology", None, term="Co-opted member", body=BAD)
add("Dr Ser-Ling Chua", L, "Chair, Therapy and Guidelines Sub-Committee", None, term="Co-opted member", body=BAD, classes=("board", "evidence"))
add("Dr David de Berker", L, "European Academy of Dermatology and Venereology (EADV) Representative", None, term="Co-opted member", body=BAD)
add("Professor Anthony Bewley", L, "European Academy of Dermatology and Venereology (EADV) Representative", None, term="Co-opted member", body=BAD)
add("Dr Sheru George", L, "Chair, NHS National Casemix Expert Working Group", None, term="Co-opted member", body=BAD)
add("Professor Christopher Bunker", L, "Honorary Secretary, British Skin Foundation", None, term="Co-opted member", body=BAD)
add("Dr Farhad Handjani", L, "Chair, Specialty and Associate Specialist (SAS) Sub-Committee", None, term="Co-opted member", body=BAD)
add("Dr Paola Di Meglio", L, "Chair, British Society for Investigative Dermatology (BSID)", None, term="Ex-officio member", body=BAD)
# Conference and Events Committee (clinicians not already on the leadership page)
O = "bad-organising"
add("Professor Mike Ardern-Jones", O, "Abstract Selection Committee Chair and Academic Representative, Conference and Events Committee", None, term="2026 to 2027", body=BAD, shown_as="Prof Mike Arden-Jones")
add("Dr Nicola Huntington", O, "Specialty and Associate Specialist (SAS) Representative, Conference and Events Committee", None, term="2026 to 2027", body=BAD)
# 106th Annual Meeting plenary speakers (names as the page shows them; affiliations not given)
SP = "bad-speakers"
for day, names in [
    ("Tuesday 30 June 2026", ["Professor Stella Vig", "Professor Giuseppe Argenziano", "Dr Natalie Stone", "Dr Rubeta Matin", "Dr Paola Pasquali", "Dr John O'Driscoll"]),
    ("Wednesday 1 July 2026", ["Dr Hassan Galadari", "Dr Junqian Zhang", "Dr Nirusha Lachman", "Dr Zoe Venables", "Professor Chris Griffiths", "Dr Ruth Lamb", "Professor Carsten Flohr", "Dr Matthew Harries", "Professor Nick Reynolds", "Professor Mike Ardern-Jones"]),
    ("Thursday 2 July 2026", ["Professor Ncoza Dlova", "Professor Hywel Williams", "Dr Hiva Fassihi", "Professor Gil Yosopovitch", "Professor Michael Simpson", "Dr Rachel Abbott", "Professor Seemal Desai"]),
]:
    for n in names:
        add(n, SP, "Plenary speaker, 106th BAD Annual Meeting (Manchester)", None, term=day, classes=("speaker",), body=BAD)
# BDNG
B = "bdng-committee"
for n, r in [("Lisa McGovern", "President"), ("Val Anderson", "Trustee"), ("Claire Lusted", "Trustee"),
             ("Karen Stephen", "Trustee"), ("Pauline Stopford-Taylor", "Trustee"), ("Emmanuel Toni", "Trustee")]:
    add(n, B, r, "British Dermatological Nursing Group", body="BDNG")
    add(n, "bdng-companies-house", "Director of the charity company, as the Companies House register shows", None, classes=("board",))
add("Polly Buchanan", B, "Journal Clinical Editor", "British Dermatological Nursing Group", body="BDNG", classes=("editor",))
add("Jackie Tomlinson", B, "Editorial Board Chair", "British Dermatological Nursing Group", body="BDNG", classes=("editor",))
# PCDS
C = "pcds-committee"
for n, r, org, cl in [
    ("Dr Julian Peace", "Executive Chair; Dermoscopy team member", "Barnsley NHS Foundation Trust (as the page's biography states)", ("board",)),
    ("Naomi Kemp", "Vice Chair; Educational Subcommittee Lead", None, ("board",)),
    ("Dr Tim Cunliffe", "Website lead; Dermoscopy team member; GP with Extended Role (GPwER) deputy", "South Tees NHS Foundation Trust (as the page's biography states)", ("board",)),
    ("Dr Angelika Razzaque", "Chief Finance Officer", "King's College Hospital (as the page's biography states)", ("board",)),
    ("Dr Christy Chou", "Surgical Lead; Educational Subcommittee", None, ("board",)),
    ("Chin Whybrew", "Dermoscopy lead", "GP partner, Cheltenham (as the page's biography states)", ("board",)),
    ("Dr Kashif Bhatti", "Skin Cancer lead; Dermoscopy Forum lead; Dermoscopy team", None, ("board",)),
    ("Dr Lorna Patterson", "Bulletin Co-editor; Essential Dermatology team member", None, ("board", "editor", "evidence")),
    ("Julie Van Onselen", "Primary care health professional team leader; Educational Subcommittee; Essential Dermatology team member", None, ("board", "evidence")),
    ("Dr Syreeta Daw", "GP with Extended Role (GPwER) lead; Bulletin co-editor; Essential Dermatology team member", None, ("board", "editor", "evidence")),
    ("Dr Stephanie Gallard", "Pharmacy lead", "Liverpool University Foundation Trust (as the page's biography states)", ("board",)),
    ("Dr Perdy Kamali", "Bulletin co-editor", None, ("board", "editor")),
    ("Sam Whitby", "Committee member, appointed December 2024", None, ("board",)),
]:
    add(n, C, r, org, body="PCDS", classes=cl, specialities=DERM_PC)
T = "pcds-trustees"
add("Dr Inma Mauri-Sole", T, "Chair of Trustees", None, body="PCDS", specialities=DERM_PC)
add("Barbara E Page MBE", T, "Honorary Member and Trustee", None, body="PCDS", specialities=DERM_PC)
add("Geoff Holmes", T, "Trustee", None, body="PCDS", specialities=DERM_PC)
add("Dr Stephen Kownacki", T, "Trustee", None, body="PCDS", specialities=DERM_PC)
# Dr Michelle Ralph, Ivan Bristow and Professor Alan M Borthwick OBE are on the Trustees page but the
# page states no trustee role for them (re-read 22/10/2026), so they are not listed as board members.
# SDS
add("Dr Paula Beattie", "sds-home", "President, Scottish Dermatological Society; Scotland's representative on the BAD Executive", None, body="SDS")
add("Dr Gordon Hale", "sds-home", "Secretary, Scottish Dermatological Society (receives membership nominations)", None, body="SDS")

# ---- Next specialities (22/10/2026). No member demand data exists in the repo, so the fallback four ----
# were used: continence, wound care and tissue viability, vascular access, diabetes. Names are copied as
# each page shows them; a person with no role on the page is listed as "listed", never given a role.
CONT = ["continence"]
X = "acp-exec"
for n, r in [("Dr Angie Rantell", "Chair"), ("Suzanne Carney", "Honorary Secretary and Website Lead"), ("Julia Thrush", "Honorary Treasurer"),
             ("Rebecca Cousins", "Conference Lead"), ("Jasmine King", "Education Lead"), ("Tracy Pouard", "Education Deputy"),
             ("Teresa Woollerton", "Newsletter Editor"), ("Darrin Powell", "Membership Deputy Lead"), ("Jane Clarke", "Committee Member")]:
    add(n, X, r, "Association for Continence Professionals", specialities=CONT, body="ACP")

WND = ["wound"]
V = "tvs-charity"
add("Sharon Neill", V, "Chair of trustees", None, term="Appointed 16 July 2020", specialities=WND, body="TVS")
for n, d in [("Sara Burr", "15 September 2026"), ("Deborah Chester Bessell", "15 September 2026"), ("Eva Harris", "15 September 2026"),
             ("Keira Bradley", "18 September 2025"), ("Heather Hodgson", "18 September 2025"), ("Sarah Bradbury", "17 September 2024"),
             ("Julie Hewish", "17 September 2024"), ("Luxmi Dhoonmoon", "17 September 2024"), ("Madeleine Coupland", "19 September 2023"),
             ("Ayesha Marshall", "1 February 2023"), ("Samantha Rooney", "22 July 2022"), ("Sharon Anne Scattergood", "22 July 2022"),
             ("Peter Worsley", "22 July 2022"), ("Clare Greenwood", "22 July 2021"), ("Victoria Murray", "22 July 2021"),
             ("Joanna Swan", "28 November 2018"), ("David Hibbitt", "28 November 2018")]:
    add(n, V, "Trustee", None, term="Appointed " + d, specialities=WND, body="TVS")

VAC = ["vascular"]
T2 = "vasbi-team"
for n, r, o in [
    ("Mr Jeremy Crane", "President", "Imperial College Healthcare NHS Trust"),
    ("Dr Jennifer Hanko", "Vice President", "Belfast Health and Social Care Trust"),
    ("Dr Kate Steiner", "Treasurer", "East and North Herts NHS Trust"),
    ("Mr Hiren Mistry", "Website lead", "King's College Hospital NHS Foundation Trust"),
    ("Margaret Aitken", "Council member (Vascular Access Clinical Nurse Specialist)", "Queen Elizabeth University Hospital, Glasgow"),
    ("Alison Swain", "Council member (Renal Vascular Access Sister)", "Royal Berkshire Hospital, Reading"),
    ("Dr Saeed Ahmed", "Council member (Consultant Interventional Nephrologist)", "Sunderland Royal Hospital"),
    ("Professor David Kingsmore", "Council member (Consultant Vascular and Renal Transplant Surgeon)", "Queen Elizabeth University Hospital, Glasgow"),
    ("Mr Damian McGrogan", "Council member (Consultant Transplant and Vascular Access Surgeon)", "Belfast City Hospital"),
]:
    add(n, T2, r, o, specialities=VAC, body="VASBI")

DIA = ["diabetes"]
# Wounds UK editorial board (read 29/10/2026). Names and affiliations exactly as the page shows them.
W = "wuk-editorial"
add("Jacqui Fletcher OBE", W, "Clinical Editor", "Independent Wound Care Advisor", classes=("editor",), specialities=WND, body="Wounds UK")
add("Samantha Holloway", W, "Academic Editor", "Reader, Programme Director, Cardiff University School of Medicine, Cardiff", classes=("editor",), specialities=WND, body="Wounds UK")
for n, o in [
    ("Leanne Atkin", "PhD, MHSc, RGN, Vascular Nurse Consultant/Associate Professor, Mid Yorks NHS Trust/ University of Huddersfield"),
    ("Alexandra Bishop", "MSc, BSc, Consultant Nurse, Tissue Viability, University Hospitals Plymouth NHS Trust"),
    ("Luxmi Dhoonmoon", "BSc, MSc, Nurse Consultant Tissue Viability, London North West University Healthcare NHS Trust"),
    ("Fiona Downie", "RGN, PGCE, MSc, Senior Lecturer Advanced Practice, Department of Nursing and Midwifery, Anglia Ruskin University, Cambridge"),
    ("Rachael Durrans", "MSc, MCSP, FHEA, Senior Lecturer Physiotherapy, University of Huddersfield"),
    ("Valerie Edwards-Jones", "PhD, CSci, FIBMS, Emeritus Professor of Medical Microbiology, Manchester Metropolitan University"),
    ("Gilly Glendewar", "Clinical Nurse Specialist Tissue Viability, Queen’s Nurse Family Nursing & Home Care, Le Bas Centre, St Helier, Jersey"),
    ("Vanessa Goulding", "BSc (Hons), MSc, PGCert, National Strategic Lead for Diabetes Footcare (Wales), Podiatry Professional Lead (Cardiff and Vale University Health Board)"),
    ("Karl Guttormsen", "BSc(Hons), MSc, PGCert, Podiatrist, Advanced Clinical Practitioner Acute Medicine, North Manchester General Hospital, Manchester NHS Foundation Trust, Manchester"),
    ("Heather Hodgson", "RGN, BSc, MN, PGD, Lead Nurse Tissue Viability, NHS Greater Glasgow and Clyde"),
    ("Anita Kilroy-Findley", "Clinical Lead Tissue Viability, Leicestershire Partnership NHS Trust, Loughborough"),
    ("Ellie Lindsay OBE", "Life President and Founder of the Lindsay Leg Club Foundation; Honorary Professor, The College of Phlebology, London; Independent Specialist Practitioner; Visiting Fellow, Queensland University of Technology; Visiting Senior Fellow, University of Suffolk; Associate Lecturer CRICP, Thames Valley University, London"),
    ("Jeanette Milne", "RGN, BSc, Post Grad Dip, Head of Nursing, Northumbria Healthcare NHS Foundation Trust"),
    ("Elizabeth Nichols", "BNurs (Hons), MSc, RN, DN, Tissue Viability Nurse Specialist, Your Healthcare CIC, Kingston upon Thames"),
    ("Karen Ousey", "PhD, MA, PGDE, DPPN, RN, CMgr MCMI, FHEA, Professor of Skin Integrity, University of Huddersfield; Immediate Past President ISTAP; World Union of Wound Healing Societies recorder"),
    ("Kelly Phillips", "RGN, BSc, MSc, Skin Integrity Nurse Consultant, Trust Advanced Practice Strategic Lead, Doncaster and Bassetlaw Teaching Hospitals NHS Foundation Trust"),
    ("Susy Pramod", "MSc, PGCert CliRes, RN, Tissue Viability Matron, The Christie NHS Foundation Trust, Manchester"),
    ("Hollie Robinson", "RGN, CMgr, FCMI, Strategic Tissue Viability Lead, South Warwickshire University Foundation Trust"),
    ("Ray Samuriwo", "PhD, RGN, Associate Professor, Edinburgh Napier University, Edinburgh"),
    ("Jackie Stephen-Haynes", "RGN, MSc, PGCert Ed and Post Grad Dip research , District Nurse qualifications, Professor in Wound and Tissue Repair, Birmingham City University, Chair, Wound Care Alliance UK"),
    ("John Stephenson", "Reader in Biomedical Statistics, School of Human and Health Sciences, University of Huddersfield"),
    ("Joshua Totty", "MBBS, MRCS, PGCertHPE, PGCertRes, MD(Res), FHEA, Academic Clinical Lecturer in Plastic Surgery, University of Hull, Visiting NIHR Research Fellow, University of York, Registrar in Plastic and Reconstructive Surgery (ST8), Leeds Teaching Hospitals NHS Trust Yorkshire and Humber Deanery"),
    ("Amy Verdon", "RN, BSc Specialist Practitioner Tissue Viability, PG Cert HEPP, Tissue Viability Clinical Nurse Specialist, Acute Tissue Viability Team, University Hospitals Coventry and Warwickshire"),
    ("Kim Whitlock", "Tissue Viability Matron, Infection Control and Tissue Viability, North Bristol NHS Trust, Southmead Hospital, Bristol"),
]:
    add(n, W, "Editorial board member (listed under the page's Editorial board heading; the page shows no further role)", o, classes=("editor",), specialities=WND, body="Wounds UK")
add("Professor Ketan Dhatariya", "abcd-committee", "Chair", None, specialities=DIA, body="ABCD")
add("Dr Vijay Jayagopal", "abcd-committee", "Honorary Treasurer", None, specialities=DIA, body="ABCD")
add("Professor Hermione Price", "abcd-committee", "Honorary Secretary", None, specialities=DIA, body="ABCD")
add("Dr Sufyan Hussain", "abcd-committee", "DTN-UK Chair", None, specialities=DIA, body="ABCD")
add("Dr Aaisha Saqib", "abcd-committee", "Honorary Meeting Secretary", None, specialities=DIA, body="ABCD")

# Wording each source gives the member about itself, kept short
NOTES = {
    "BAD": "Consultant dermatologists",
    "BDNG": "Dermatology nurses and healthcare professionals",
    "PCDS": "GPs and primary care clinicians with a special interest in dermatology",
    "SDS": "Scottish consultant dermatologists",
    "ACP": "Continence nurses, physiotherapists and other bladder and bowel professionals",
    "TVS": "Tissue viability and wound care professionals (charity trustees)",
    "VASBI": "Surgeons, nephrologists, radiologists and nurses in haemodialysis vascular access",
    "ABCD": "Consultant diabetologists",
    "Wounds UK": "Editorial board of the Wounds UK journal (wound care and tissue viability)",
}

EMPTY = {
    "evidence": "No evidence authors are listed beyond people a source page names as an author or guideline chair. No publication list was read for this build, so none is claimed.",
    "supply": "No NHS Supply Chain buyers are listed here. Use the category directory to find the right buyer.",
    "editor": "No journalists or commentators are listed until a source names them.",
    "clinical": "No hospital unit consultants are listed for this speciality. A name is added only when the trust's own page names the consultant.",
}


def term_end(term):
    """Last day of the month in 'X to <Month> <Year>' (None if the term has no stated end)."""
    months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    m = re.search(r"\bto (\w+) (20\d\d)$", term or "")
    if not m or m.group(1).lower() not in months:
        return None
    y, mo = int(m.group(2)), months.index(m.group(1).lower()) + 1
    return datetime.date(y + mo // 12, mo % 12 + 1, 1) - datetime.timedelta(days=1)


def linkedin(name, bodies, spec_label="dermatology"):
    q = re.sub(r"^(Dr|Professor|Prof|Mrs|Mr|Miss)\s+", "", name)
    q = re.sub(r"\s+(MBE|OBE)$", "", q)
    org = {"BAD": "dermatology", "BDNG": "dermatology nurse", "PCDS": "dermatology GP", "SDS": "dermatology",
           "ACP": "continence", "TVS": "tissue viability", "VASBI": "vascular access", "ABCD": "diabetes", "Wounds UK": "wound care"}.get(bodies[0] if bodies else None, spec_label)
    return "https://www.linkedin.com/search/results/people/?keywords=" + urllib.parse.quote(q + " " + org)


LINKEDIN_RE = re.compile(r"^https://(www|uk)\.linkedin\.com/in/[A-Za-z0-9%_.\-]+/?$")


def load_linkedin():
    """data/kol-linkedin-*.json: {name: {url, basis}}. A URL is kept only if it is a profile URL with a stated basis."""
    out = {}
    for f in sorted((ROOT / "data").glob("kol-linkedin-*.json")):
        for n, v in json.loads(f.read_text()).items():
            if v.get("url") and v.get("basis") and LINKEDIN_RE.match(v["url"]):
                out[n] = v
    return out


def merge_research(sources, bodies, spec_ids):
    """Fold data/kol-sources/<speciality>.json (agent research, brief in docs/KOL-AGENT-BRIEF.md) into PEOPLE."""
    for f in sorted((ROOT / "data" / "kol-sources").glob("*.json")):
        d = json.loads(f.read_text())
        spec = d["speciality"]
        if spec not in spec_ids:
            print("skip %s: unknown speciality %s" % (f.name, spec))
            continue
        specs_here = [spec] + [x for x in d.get("alsoSpecialities", []) if x in spec_ids]
        for b in d.get("bodies", []):
            bodies.setdefault(b["id"], b["label"])
        for sc in d["sources"]:
            sources[sc["id"]] = dict({k: sc[k] for k in ("short", "body", "title", "url", "note")}, checked=sc.get("checked", d["checked"]))
        for q in d["people"]:
            if q["source"] not in sources:
                print("skip %s: unknown source" % q["name"])
                continue
            p = PEOPLE.setdefault(q["name"], {"name": q["name"], "appearances": [], "specialities": [], "classes": []})
            app = {"body": q.get("body"), "role": q["role"], "organisation": q.get("organisation"),
                   "term": q.get("term"), "source": q["source"],
                   "source_url": sources[q["source"]]["url"], "checked": sources[q["source"]]["checked"]}
            end = term_end(q.get("term"))
            if end and end < datetime.date.today():
                app["note"] = "The term end shown on the page has passed; check the page for a successor before relying on it."
            p["appearances"].append(app)
            mine = [x for x in q.get("specialities", []) if x in spec_ids] if d.get("perPersonSpecialities") else specs_here
            for sp in mine:
                if sp not in p["specialities"]:
                    p["specialities"].append(sp)
            if q.get("trustCode"):
                p.setdefault("_tc", q["trustCode"])
            if q.get("trustCode") and q.get("hospital"):
                p.setdefault("_hosp", (q["trustCode"], q["hospital"]))
            for c in q["classes"]:
                if c not in p["classes"]:
                    p["classes"].append(c)
            if q.get("title_basis") and (q.get("job_title") or q.get("trust")):
                p.setdefault("_jt", {k: q.get(k) for k in ("job_title", "trust", "title_basis")})
            if q.get("linkedin_url") and q.get("linkedin_basis") and LINKEDIN_RE.match(q["linkedin_url"]):
                p.setdefault("_li", {"url": q["linkedin_url"], "basis": q["linkedin_basis"]})


def _norm(x):
    x = str(x or "").lower().replace("&", " and ").replace("’", "'")
    x = re.sub(r"\b(nhs|the|foundation|trust|group)\b", " ", x)
    x = re.sub(r"[^a-z0-9' ]+", " ", x)
    return re.sub(r"\s+", " ", x).strip()


SITES = {}   # trust code -> its hospitals' names (trust-sites.json)
GENERIC_CORE = {"general", "community", "royal", "university", "district", "county", "city", "memorial",
                "children's", "childrens", "women's", "womens", "eye", "dental", "cottage", "war memorial"}


def hospital_in_text(p, code):
    """File a person to one hospital of their own trust, from text already held (roles, organisation,
    job title, LinkedIn snippet). Within one trust a hospital's short name is unambiguous, so the
    'Hospital' suffix may be dropped. Returns (hospital, basis) or (None, None)."""
    names = SITES.get(code) or []
    if not names:
        return None, None
    roles = " ".join(a.get("role") or "" for a in p["appearances"]) + " " + (p.get("job_title") or "")
    if len(names) > 1 and re.search(r"chief executive|chief officer|\bdirector\b|\bchair\b|non.executive|board|group\b", roles, re.I):
        return None, None   # trust-wide and group roles belong to the trust, not one site
    texts = [p.get("job_title"), p.get("trust"), p.get("linkedin_basis")]
    for a in p["appearances"]:
        texts += [a.get("role"), a.get("organisation")]
    blob = " " + " ".join(_norm(x) for x in texts if x) + " "
    tname = " " + _norm(p.get("trustName") or "") + " "
    hits = set()
    for h in names:
        full = _norm(h)
        core = re.sub(r"\s+hospital$", "", full).strip()
        if (" " + core + " ") in tname:   # "St Thomas' Hospital" inside "Guy's and St Thomas'" names the trust, not the site
            continue
        for k in {full, core}:
            if len(k) < 6 or k in GENERIC_CORE or (" " + k + " ") in tname:
                continue
            if (" " + k + " ") in blob:
                hits.add(h)
    if len(hits) == 1:
        return hits.pop(), "Hospital named in the person's role, organisation or profile text."
    if len(names) == 1:
        return names[0], "The trust's only hospital in NHS ODS."
    return None, None


def place_index():
    """Name -> (trust code, hospital or None), from trust-map.json and trust-sites.json."""
    tm = json.loads((ROOT / "data" / "trust-map.json").read_text())
    trusts = {t["code"]: t for t in tm["trusts"]}
    idx = {}
    for c, t in trusts.items():
        n = _norm(t["n"])
        if len(n) >= 6:
            idx.setdefault(n, (c, None))
    ts = ROOT / "data" / "trust-sites.json"
    if ts.exists():
        hosp_names = {}
        for c, t in json.loads(ts.read_text())["trusts"].items():
            SITES[c] = [h["name"] for h in t["hospitals"]]
            for h in t["hospitals"]:
                hosp_names.setdefault(_norm(h["name"]), set()).add((c, h["name"]))
        for n, hits in hosp_names.items():
            if len(hits) == 1 and len(n) >= 8:   # a hospital name two trusts share is ambiguous: skip it
                idx.setdefault(n, next(iter(hits)))
    return trusts, idx


def place(p, trusts, idx):
    cands = [p.get("trust")] + [a.get("organisation") for a in p["appearances"]]
    code, hosp = p.pop("_tc", None), None
    filed = p.pop("_hosp", None)
    for c in cands:
        if not c:
            continue
        for part in [c] + [x for x in re.split(r"[,(]", c) if x.strip()]:
            hit = idx.get(_norm(part))
            if hit and (not code or hit[0] == code):
                code = code or hit[0]
                hosp = hosp or hit[1]
    if not code:
        # a trust name inside a longer organisation string, for long distinctive names only
        blob = " " + " ".join(_norm(c) for c in cands if c) + " "
        best = [k for k, v in idx.items() if v[1] is None and len(k) >= 14 and (" " + k + " ") in blob]
        if len(best) == 1:
            code = idx[best[0]][0]
    if code and code in trusts:
        t = trusts[code]
        p["trustCode"], p["trustName"] = code, t["n"]
        if t.get("icb"):
            p["icb"], p["icbName"] = t["icb"], t.get("icbName")
        if t.get("region"):
            p["region"] = t["region"]
        if filed and filed[0] == code and filed[1] in SITES.get(code, []):
            hosp = filed[1]
            p["hospital"], p["hospitalBasis"] = hosp, "Hospital stated on the source page linked under the person."
        elif hosp:
            p["hospital"] = hosp
            p["hospitalBasis"] = "Hospital named in the person's organisation text."
        else:
            hosp, basis = hospital_in_text(p, code)
            if hosp:
                p["hospital"], p["hospitalBasis"] = hosp, basis
    p["kol"] = any(c in KOL_CLASSES for c in p["classes"])


def main():
    optout = set()
    try:
        d = json.loads((ROOT / "data" / "contacts-optout.json").read_text())
        optout = {n.lower() for n in d.get("names", [])}
    except Exception:
        pass
    specs = json.loads((ROOT / "data" / "speciality-map.json").read_text())["canonicalSpecialities"]
    spec_label = {x["id"]: x["label"] for x in specs}
    sources = {k: dict(v) for k, v in SOURCES.items()}
    body_labels = dict(NOTES)
    merge_research(sources, body_labels, set(spec_label))
    li = load_linkedin()
    trusts, idx = place_index()
    people = []
    for name in sorted(PEOPLE, key=lambda n: re.sub(r"^(Dr|Professor|Mrs|Mr|Miss)\s+", "", n).split()[-1].lower()):
        if name.lower() in optout or re.sub(r"^(Dr|Professor)\s+", "", name).lower() in optout:
            continue
        p = PEOPLE[name]
        bodies = []
        for a in p["appearances"]:
            if a["body"] and a["body"] not in bodies:
                bodies.append(a["body"])
        p["bodies"] = bodies
        p["classes"] = [c for c, _ in CLASSES if c in p["classes"]]
        first = spec_label.get(p["specialities"][0], "") if p["specialities"] else ""
        p["linkedin_search"] = linkedin(name, bodies, first)
        hit = li.get(name) or p.pop("_li", None)
        p.pop("_li", None)
        jt = p.pop("_jt", None)
        if jt:
            for k in ("job_title", "trust", "title_basis"):
                if jt.get(k):
                    p[k] = jt[k]
        if hit:
            p["linkedin_url"] = hit["url"]
            p["linkedin_basis"] = hit["basis"]
        place(p, trusts, idx)
        people.append(p)
    out = {
        "_meta": {
            "built": CHECKED,
            "purpose": "Key Opinion Leader (KOL) finder behind Build Your Network (page 1882). Every speciality researched from its main bodies and conference.",
            "basis": "Public-domain information published by the bodies themselves. Lawful basis: legitimate interests (UK GDPR Article 6(1)(f)), limited to name, public role and the page it came from. No contact details are held.",
            "removal": "Anyone listed can ask for removal at contact@elevateandthrive.uk. The name is added to data/contacts-optout.json and dropped at the next build.",
            "linkedin": "A profile link is held only where a public search result showed the same name with a matching role, employer or speciality (the basis is recorded). Everyone else has a search link built from the name and speciality. Nothing is scraped.",
        },
        "classes": [{"id": c, "label": l} for c, l in CLASSES],
        "kolClasses": list(KOL_CLASSES),
        "specialities": [{"id": s["id"], "label": s["label"]} for s in specs],
        "bodies": [{"id": k, "label": v} for k, v in body_labels.items()],
        "sources": [{"id": k, **v, "checked": v.get("checked", CHECKED)} for k, v in sources.items()],
        "empty": EMPTY,
        "people": people,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("wrote %s: %d people" % (OUT, len(people)))


if __name__ == "__main__":
    sys.exit(main())
