#!/usr/bin/env python3
"""Key Opinion Leader (KOL) finder: writes data/kol-finder.json for Build Your Network (page 1882).

WHAT THIS IS
------------
Every person below was read on 22/10/2026 from a public page of the body named,
and the page is recorded against them (source_url). Nothing is carried from memory
or from a search snippet. Dermatology first, then continence, wound care and tissue viability, vascular access and diabetes; the structure holds any
speciality in data/speciality-map.json (canonicalSpecialities), and a speciality
with no checked people renders an honest empty state.

SOURCES READ (22/10/2026)
-------------------------
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
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "kol-finder.json"
CHECKED = "2026-10-22"

CLASSES = [
    ("board", "Board and committee members"),
    ("speaker", "Conference speakers"),
    ("evidence", "Evidence authors"),
    ("editor", "Journalists, editors and commentators"),
    ("supply", "Supply chain contacts"),
]

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
        "note": "Executive members as the page lists them. Only the Chair, Secretary and Treasurer have a role on the page; the others are listed without one. Commercial advisors and patrons are on separate pages and are not listed."},
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
        "note": "The four officers the page names. The page's Committee Members section was empty when read, and it shows no affiliations."},
}

DERM = ["dermatology"]
DERM_PC = DERM  # canonicalSpecialities has no primary care id; the PCDS body note says primary care

# person: name -> dict(appearances=[...], specialities, classes)
PEOPLE = {}


def add(name, source, role, org=None, classes=("board",), term=None, specialities=DERM, body=None, region=None, shown_as=None, note=None):
    p = PEOPLE.setdefault(name, {"name": name, "appearances": [], "specialities": [], "classes": []})
    p["appearances"].append({
        "body": body, "role": role, "organisation": org, "term": term,
        "source": source, "source_url": SOURCES[source]["url"], "checked": CHECKED,
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
add("Professor Minal Singh", L, "Education Vice President", "Salford Royal NHS Foundation Trust", term="July 2023 to July 2026", body=BAD,
    note="The term end shown on the page (July 2026) had passed when read on 22/10/2026 and the page still listed this role; check the page for a successor before relying on it.")
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
for n, r in [("Polly Weston", "Chair"), ("Kerry Doherty", "Secretary"), ("Bo Yeung", "Treasurer")]:
    add(n, X, r, "Association for Continence Professionals", specialities=CONT, body="ACP")
for n in ["Esther Taborn", "Professor Nikki Cotterill", "Julia Thrush", "Rebecca Cousins", "Ruth Scrivens", "Dr Angie Rantell"]:
    add(n, X, "Executive member (listed on the executive page; the page shows no role)", "Association for Continence Professionals", specialities=CONT, body="ACP")

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
add("Professor Ketan Dhatariya", "abcd-committee", "Chair", None, specialities=DIA, body="ABCD")
add("Dr Vijay Jayagopal", "abcd-committee", "Honorary Treasurer", None, specialities=DIA, body="ABCD")
add("Professor Hermione Price", "abcd-committee", "Honorary Secretary", None, specialities=DIA, body="ABCD")
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
}

EMPTY = {
    "evidence": "No evidence authors are listed beyond people a source page names as an author or guideline chair. No publication list was read for this build, so none is claimed.",
    "supply": "NHS Supply Chain's medical technology contacts page has no dermatology, skin or wound care section (read 22/10/2026). Use the category directory to find the right buyer.",
    "editor": "No journalists or commentators are listed until a source names them.",
}


def linkedin(name, bodies):
    q = re.sub(r"^(Dr|Professor|Prof|Mrs|Mr|Miss)\s+", "", name)
    q = re.sub(r"\s+(MBE|OBE)$", "", q)
    org = {"BAD": "dermatology", "BDNG": "dermatology nurse", "PCDS": "dermatology GP", "SDS": "dermatology",
           "ACP": "continence", "TVS": "tissue viability", "VASBI": "vascular access", "ABCD": "diabetes"}.get(bodies[0] if bodies else None, "dermatology")
    return "https://www.linkedin.com/search/results/people/?keywords=" + urllib.parse.quote(q + " " + org)


def main():
    optout = set()
    try:
        d = json.loads((ROOT / "data" / "contacts-optout.json").read_text())
        optout = {n.lower() for n in d.get("names", [])}
    except Exception:
        pass
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
        p["linkedin_search"] = linkedin(name, bodies)
        people.append(p)
    specs = json.loads((ROOT / "data" / "speciality-map.json").read_text())["canonicalSpecialities"]
    out = {
        "_meta": {
            "built": CHECKED,
            "purpose": "Key Opinion Leader (KOL) finder behind Build Your Network (page 1882). Dermatology first.",
            "basis": "Public-domain information published by the bodies themselves. Lawful basis: legitimate interests (UK GDPR Article 6(1)(f)), limited to name, public role and the page it came from. No contact details are held.",
            "removal": "Anyone listed can ask for removal at contact@elevateandthrive.uk. The name is added to data/contacts-optout.json and dropped at the next build.",
            "linkedin": "A search link built from the name and the body. No profile is matched, scraped or stored.",
        },
        "classes": [{"id": c, "label": l} for c, l in CLASSES],
        "specialities": [{"id": s["id"], "label": s["label"]} for s in specs],
        "bodies": [{"id": k, "label": v} for k, v in NOTES.items()],
        "sources": [dict(id=k, **v, checked=CHECKED) for k, v in SOURCES.items()],
        "empty": EMPTY,
        "people": people,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("wrote %s: %d people" % (OUT, len(people)))


if __name__ == "__main__":
    sys.exit(main())
