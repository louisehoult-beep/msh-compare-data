#!/usr/bin/env python3
"""One-off, idempotent: My Hub home screen (phase 1, 01/10/2026) catalogue fields.

    python3 scripts/_my_hub_icons_bands_1001.py

Writes into hub/my-hub-catalogue.json, and nothing else:
  * `icon` on every non-speciality item: its own glyph from app/hub-icons.js
    (Lou, 01/10/2026: "an icon for every tool and frequently used page").
  * `libraryBand` on every speciality: the band id the Clinical Evidence Library
    (page 3791) opens with `#<band-id>`, or null where the library has no band.
    Band ids read from the live page 3791 on 30/09/2026
    (Hub/Wound-Care-Updates-2026-09-30/page-3791-live-20260930-150720.html,
    the `.stab[data-band]` tabs), matched to catalogue labels word for word.
    Theatres and Surgical has no band on 3791, so it is null, not guessed.
  * top-level `profiles` (display names for the five nav profiles) and
    `profileStarters` (the pages a new member's My Hub starts with, by the
    profile they chose; every one is in that profile's live nav, checked
    01/10/2026, and test_my_hub_catalogue.py keeps it that way).
Item `profiles` lists are written by scripts/build_my_hub_profiles.py, not here.
Run it twice and the second run changes nothing.
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(HERE, "hub", "my-hub-catalogue.json")

ICONS = {
    "live-desk": "radio", "news": "news", "sales-triggers": "target",
    "supply-disruption-tracker": "truck", "mhra-regulatory-desk": "shield-alert",
    "market-watch-subscribers-only": "trending-up", "the-radar": "radar",
    "intelligence-feed": "rss", "calendar": "calendar-days",
    "capital-estates-watch": "hospital", "nhs-workforce-watch": "users",
    "frameworks": "clip", "tender-history": "history", "nhssc-guide": "package",
    "price-intelligence": "pound", "cpv": "hash", "procurement-act": "scale",
    "value-based-procurement": "badge-check", "voice-of-procurement": "megaphone",
    "private-sector": "building", "four-nations": "globe", "nhs-online": "monitor-smartphone",
    "med-sales-tools": "wrench", "value-equation": "calculator", "company-report": "file-chart",
    "suppliers": "factory", "who-are-the-competitors": "swords",
    "market-intelligence": "pie-chart", "briefings": "notebook-pen",
    "hospital-prescribing-by-trust": "pill", "icb-diabetes-tech-tracker": "droplet",
    "girft": "gauge", "pathways": "route", "clinical-evidence-library": "book",
    "analysis": "bar-chart",
    "nhs-structure-map": "network", "reference": "library", "tr-reports": "receipt",
    "glossary": "book-a", "access-accreditation-codes": "id-card",
    "sustainability-net-zero": "leaf", "device-sales-entry": "compass",
    "pharmaceutical-sales": "flask",
    "fall-prevention-medical-sales-market-insights": "footprints",
    "careers": "case", "interview-prep": "messages", "courses": "graduation-cap",
    "webinars": "video", "podcasts": "mic", "build-your-network": "share",
    "sales-icons": "award", "downloads": "download",
    "clinical-to-commercial-routes": "signpost", "cpd-for-a-commercial-cv": "file-user",
    "training-investment-watch": "coins", "funded-clinical-training": "hand-coins",
    "clinical": "heart", "clinical-training": "presentation",
    "clinical-listen-watch": "headphones", "clinical-jobs": "user-search",
    "clinical-cv": "file", "clinical-resources": "folder-open",
    "clinical-portfolio": "folder-check", "care-standard-portfolio": "hand-heart",
    "phone-alerts": "bell", "ask": "message-question", "find-your-speciality": "locate",
}

BANDS = {
    "audiology-and-hearing": "audiology-hearing",
    "cardiology-and-cardiac-surgery": "cardiology-cardiac-surgery",
    "colorectal-gi-and-endoscopy": "colorectal-gi-endoscopy",
    "continence-bladder-and-bowel": "continence-bladder-bowel",
    "critical-care": "critical-care",
    "dermatology": "dermatology",
    "diabetes-and-endocrinology": "diabetes-endocrinology",
    "digital-and-medical-it": "digital-medical-it",
    "emergency-and-urgent-care": "emergency-urgent-care",
    "ent-and-head-and-neck": "ent-head-neck",
    "frailty-and-older-people": "frailty-older-people",
    "gynaecology-and-womens-health": "gynaecology-womens-health",
    "haematology-and-patient-blood-management": "haematology-pbm",
    "infection-prevention-and-control": "infection-prevention-control",
    "interventional-radiology": "interventional-radiology",
    "maternity-and-neonatal": "maternity-neonatal",
    "mental-health": "mental-health",
    "neurology-and-neurosurgery": "neurology-neurosurgery",
    "nutrition-and-dietetics": "nutrition-dietetics",
    "obesity-and-weight-management": "obesity-weight-management",
    "oncology-and-sact": "oncology-sact",
    "ophthalmology": "ophthalmology",
    "orthopaedics-and-trauma": "orthopaedics-trauma",
    "paediatrics": "paediatrics",
    "pain-management": "pain-management",
    "palliative-and-end-of-life-care": "palliative-eol",
    "pathology-and-laboratory-medicine": "pathology-lab-medicine",
    "patient-handling": "patient-handling",
    "pharmacy-and-medicines": "pharmacy-medicines",
    "plastics-burns-and-reconstruction": "plastics-burns-reconstruction",
    "primary-care-and-general-practice": "primary-care",
    "radiology-and-imaging": "radiology-imaging",
    "rehabilitation-prosthetics-and-orthotics": "rehab-prosthetics-orthotics",
    "renal": "renal",
    "respiratory": "respiratory",
    "sepsis-and-the-deteriorating-patient": "sepsis-deteriorating-patient",
    "stroke": "stroke",
    "theatres-and-surgical": None,
    "tissue-viability-and-wound-care": "wound-care",
    "urology": "urology",
    "vascular-access-and-iv-therapy": "vascular-access-iv",
    "vascular-surgery-and-pad": "vascular-surgery-pad",
}

PROFILES = {"company": "Company", "rep": "Rep", "clinical": "Clinical",
            "procurement": "Procurement", "recruit": "Recruiter"}

STARTERS = {
    "company": ["live-desk", "company-report", "who-are-the-competitors", "suppliers", "sales-triggers", "market-intelligence"],
    "rep": ["live-desk", "briefings", "calendar", "med-sales-tools", "sales-triggers", "supply-disruption-tracker"],
    "clinical": ["clinical", "clinical-evidence-library", "clinical-training", "clinical-to-commercial-routes", "clinical-jobs"],
    "procurement": ["tender-history", "nhssc-guide", "price-intelligence", "value-based-procurement", "suppliers"],
    "recruit": ["careers", "interview-prep", "courses", "podcasts", "company-report"],
}

README = (
    "What a member can put on My Hub. Page configuration, not Hub intelligence data, so it lives "
    "in hub/ and not data/. Every entry is a published Hub page (checked against the WordPress page "
    "list 23/09/2026). Add a page here and it appears in the picker; ids are what members' saved "
    "choices hold, so never rename one. Fields: icon (non-speciality pages: a glyph in "
    "app/hub-icons.js, one per page), libraryBand (specialities: the Clinical Evidence Library "
    "band id, or null), profiles (the nav profiles that list the page, written by "
    "scripts/build_my_hub_profiles.py from the live nav). profileStarters are the pages a new "
    "member starts with, by profile. Role starters come from the original My Hub shortlist "
    "logic. Checked by test_my_hub_catalogue.py."
)


def main():
    with open(CAT, encoding="utf-8") as f:
        cat = json.load(f)
    seen = set()
    for it in cat["items"]:
        if it["group"] == "specialities":
            it.pop("icon", None)
            it["libraryBand"] = BANDS[it["id"]]
        else:
            it["icon"] = ICONS[it["id"]]
            it.pop("libraryBand", None)
        seen.add(it["id"])
    missing = (set(ICONS) | set(BANDS)) - seen
    if missing:
        raise SystemExit("not in the catalogue: " + ", ".join(sorted(missing)))
    cat["_readme"] = README
    cat["profiles"] = PROFILES
    cat["profileStarters"] = STARTERS
    with open(CAT, "w", encoding="utf-8") as f:
        f.write(json.dumps(cat, indent=1, ensure_ascii=False))
    print("icons: %d, library bands: %d (null: %d), profiles: %d" % (
        len(ICONS), len(BANDS), sum(1 for v in BANDS.values() if v is None), len(PROFILES)))


if __name__ == "__main__":
    main()
