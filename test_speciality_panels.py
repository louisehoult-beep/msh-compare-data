#!/usr/bin/env python3
"""Invariants for the per-speciality panel slices (root rule 14b).

Every case here replays something that actually went wrong, or would have.
The point of the file is that the wound care panel cannot silently start
showing Kew Gardens' seed viability X-ray cabinet again.

  python3 test_speciality_panels.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import build_speciality_panels as B  # noqa: E402

WOUND = "tissue-viability-and-wound-care"
HANDLING = "therapies-physio-and-ot"
VASCULAR = "vascular-surgery-and-pad"
CONTINENCE = "continence-bladder-and-bowel"
THEATRES = "theatres-and-surgical"
ORTHO = "orthopaedics-and-trauma"
PLASTICS = "plastics-burns-and-reconstruction"
FRAILTY = "frailty-and-older-people"
IR = "interventional-radiology"
CARDIAC = "cardiology-and-cardiac-surgery"
NUTRITION = "nutrition-and-dietetics"
OBESITY = "obesity-and-weight-management"
NEURO = "neurology-and-neurosurgery"
PALLIATIVE = "palliative-and-end-of-life-care"
PATHOLOGY = "pathology-and-laboratory-medicine"
RADIOLOGY = "radiology-and-imaging"
RENAL = "renal"
HAEM = "haematology-and-patient-blood-management"
MATERNITY = "maternity-and-neonatal"
GYNAE = "gynaecology-and-womens-health"
PAEDS = "paediatrics"
VASCACCESS = "vascular-access-and-iv-therapy"
UROLOGY = "urology"
RESP = "respiratory"
STROKE = "stroke"
OPHTH = "ophthalmology"
CC = "critical-care"
ENT = "ent-and-head-and-neck"
AUDIO = "audiology-and-hearing"
COLO = "colorectal-gi-and-endoscopy"
DERM = "dermatology"
IPC = "infection-prevention-and-control"
ONC = "oncology-and-sact"
fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("  — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def load_panel(slug):
    p = os.path.join(HERE, "data", "speciality-panels", slug + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


print("Rebuilding the wound care slice from live data...")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), WOUND],
               check=True, capture_output=True)
d = load_panel(WOUND)

print("\nFALSE POSITIVES — titles the old keyword rule let through")
# The `spec` field on tender-history.json tags all of these
# tissue-viability-and-wound-care. They matched on "tissue", "viability",
# "pressure" or "compression" and not one of them is wound care.
titles = " || ".join((a.get("title") or "") for a in d["awards"]).lower()
for bad in ["seed viability", "corneal", "eye tissue", "toilet tissue",
            "chest compression", "test rig", "laminar flow", "pressure infus",
            "newborn transport harness"]:
    check("excluded: %s" % bad, bad not in titles)

print("\nTRUE POSITIVES — awards that must be on this patch")
for good in ["negative pressure wound therapy", "wound closure", "dressings",
             "lymphoedema", "debridement"]:
    check("present: %s" % good, good in titles)

print("\nFRAMEWORKS")
names = [f["name"] for f in d["frameworks"]]
for want in ["Advanced Wound Care", "General Wound Care", "Negative Pressure Wound Therapy",
             "Pressure Area Care and Patient Handling", "Wound Closure"]:
    check("framework present: %s" % want, want in names)
check("every framework carries an end date",
      all(f.get("ends") for f in d["frameworks"]))
check("every framework carries its NHSSC url",
      all(f.get("url") for f in d["frameworks"]))
check("no framework outside this speciality crept in", len(names) == 5,
      "got %d: %s" % (len(names), names))

print("\nSUPPLIERS")
sup = d["suppliers"]
check("suppliers are drawn from the frameworks, not empty", len(sup) > 100)
check("alias merge actually reduced the raw NHSSC list", len(sup) < 155,
      "got %d, expected fewer than the 155 raw framework-page names" % len(sup))
check("no supplier listed twice", len(sup) == len(set(s["name"] for s in sup)))
check("alias variants are merged, not published as separate suppliers",
      not any(s["name"] in ("Molnlycke Healthcare", "ConvaTec Ltd", "KCI Medical Limited")
              for s in sup))
molnlycke = [s for s in sup if "lnlycke" in s["name"]]
check("Molnlycke appears exactly once", len(molnlycke) == 1,
      "got %s" % [s["name"] for s in molnlycke])
check("a merged supplier shows both NHSSC spellings",
      bool(molnlycke) and len(molnlycke[0]["variants"]) == 2)
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in sup))
check("every supplier names at least one framework",
      all(s["frameworks"] for s in sup))
check("every named framework is one of this speciality's",
      all(set(s["frameworks"]) <= set(names) for s in sup))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((d.get("rules") or {}).get(k)))
check("dataAsOf stated for every source",
      all(d["dataAsOf"].get(k) for k in ["frameworks", "tenderHistory", "drugTariff"]))
check("licence notice carried", bool(d.get("_notice", {}).get("owner")))

print("\nEVIDENCE FLOOR — an undefined speciality publishes nothing")
u = B.build("a-speciality-with-no-rule", {
    "notice": {"owner": "x"}, "frameworks": {"frameworks": []},
    "tender_history": {"schema": [], "rows": []}, "framework_awards": {"awards": []},
    "open_tenders": {"notices": []}, "drug_tariff": {"schema": [], "rows": []}})
check("undefined speciality is marked undefined", u.get("defined") is False)
check("undefined speciality carries no frameworks key", "frameworks" not in u)
check("undefined speciality says why it is empty", bool(u.get("whyEmpty")))

print("\nSIZE — the page must not pull the Drug Tariff whole")
kb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", WOUND + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % kb, kb < 200)
check("Drug Tariff is summarised, not shipped",
      "rows" not in (d.get("drugTariff") or {}) and d["drugTariff"]["lineCount"] > 1000)

print("\n" + "=" * 70)
print("PATIENT MOVING AND HANDLING (slug therapies-physio-and-ot, page 2913)")
print("=" * 70)
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), HANDLING],
               check=True, capture_output=True)
h = load_panel(HANDLING)

check("the label is the page's name, not its legacy slug",
      h.get("label") == "Patient Moving and Handling", "got %r" % h.get("label"))

print("\nFALSE POSITIVES — every one matched `include` and was read and rejected")
htitles = " || ".join((a.get("title") or "") for a in h["awards"]).lower()
# Translink's B7R is a Volvo bus chassis. Wheelchair lifts on public buses, twice.
check("excluded: b7r bus wheelchair lifts", "b7r" not in htitles)
check("excluded: wheelchair lifts", "wheelchair lift" not in htitles)
# Choice Housing, a housing association: shower and mobility goods adaptations, twice.
check("excluded: housing disabled adaptations", "disabled adaptations" not in htitles)
# An Access to Work reasonable adjustment for one employee, not a procurement.
check("excluded: staff Access to Work wheelchair waiver", "atw grant" not in htitles)
# EpiGuard biocontainment transport isolators via Leidos. Not moving and handling.
check("excluded: HCID tactical patient transfer", "hcid" not in htitles)
# Occupational physio bought by employers for their own staff. Never in `include`.
check("excluded: sports physiotherapy", "sports physiotherapy" not in htitles)
check("excluded: employer physiotherapy services contracts",
      "physiotherapy services" not in htitles)

print("\nTRUE POSITIVES — awards that must be on this patch")
for good in ["pressure area care and patient handling", "hoist", "bariatric",
             "aids for daily living", "wheelchair", "mattress", "specialist seating",
             "falls prevention", "postural support"]:
    check("present: %s" % good, good in htitles)

print("\nFRAMEWORKS")
hnames = [f["name"] for f in h["frameworks"]]
for want in ["Aids for Daily Living", "Physiotherapy and Occupational Therapy",
             "Pressure Area Care and Patient Handling",
             "Wheelchairs, Specialist Seating and Related Services"]:
    check("framework present: %s" % want, want in hnames)
check("exactly this speciality's four frameworks", len(hnames) == 4,
      "got %d: %s" % (len(hnames), hnames))
# These belong to the Rehabilitation, Prosthetics and Orthotics page, not this one.
for other in ["Orthotics, Podiatry and Immobilisation",
              "Prosthetic Components and Associated Products",
              "External Breast Prosthesis and Chest Support",
              "Technology Enabled Care, Electronic Assistive Technology and Lone Worker Devices"]:
    check("another speciality's framework stays out: %s" % other, other not in hnames)
check("every framework carries an end date", all(f.get("ends") for f in h["frameworks"]))
check("every framework carries its NHSSC url", all(f.get("url") for f in h["frameworks"]))

print("\nSUPPLIERS")
hsup = h["suppliers"]
check("suppliers are drawn from the frameworks, not empty", len(hsup) > 90)
check("alias merge actually reduced the raw NHSSC list", len(hsup) < 137,
      "got %d, expected fewer than the 137 raw framework-page names" % len(hsup))
check("no supplier listed twice", len(hsup) == len(set(s["name"] for s in hsup)))
check("every supplier names at least one framework", all(s["frameworks"] for s in hsup))
check("every named framework is one of this speciality's",
      all(set(s["frameworks"]) <= set(hnames) for s in hsup))
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in hsup))

print("\nNO DRUG TARIFF, SAID HONESTLY (rule 14)")
check("no tariff panel is published", h.get("drugTariff") is None)
check("the drugTariff rule explains the absence rather than reading 'Part '",
      "No Drug Tariff part applies" in (h.get("rules") or {}).get("drugTariff", ""))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((h.get("rules") or {}).get(k)))
check("licence notice carried", bool(h.get("_notice", {}).get("owner")))
hkb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", HANDLING + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % hkb, hkb < 200)


print("\n" + "=" * 70)
print("VASCULAR SURGERY AND PAD (slug vascular-surgery-and-pad, page 2802)")
print("=" * 70)
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), VASCULAR],
               check=True, capture_output=True)
v = load_panel(VASCULAR)

check("the label spells out peripheral arterial disease",
      v.get("label") == "Vascular Surgery and Peripheral Arterial Disease", "got %r" % v.get("label"))

print("\nFALSE POSITIVES — every one matched `include` and was read and rejected")
vtitles = " || ".join((a.get("title") or "") for a in v["awards"]).lower()
# NHS England's anti-VEGF framework, twice. Retinal vascular disease is ophthalmology.
check("excluded: medical retinal vascular treatments", "retinal" not in vtitles)
# NHS Wales. Cannulae and central lines are the IV therapy patch, not vascular surgery.
check("excluded: vascular access accessories", "vascular access" not in vtitles)
# Hull. Interventional neuroradiology and stroke thrombectomy.
check("excluded: neuro vascular radiology consumables",
      "neuro vascular" not in vtitles and "neurovascular" not in vtitles)

print("\nNEVER MATCHED AT ALL — the include list is narrow enough to keep these out")
# These are why `aortic`, `stent`, `catheter`, `balloon` and `graft` are not bare
# terms in `include`. All are coronary, urology, renal or cardiac-valve work.
for bad in ["pci consumbeles", "cardiology stents", "cath labs", "memokath",
            "aortic root", "mitral valve", "impella", "heart pumps",
            "fistula needles", "central venous catheters"]:
    check("never admitted: %s" % bad, bad not in vtitles)

print("\nTRUE POSITIVES — awards that must be on this patch")
for good in ["vascular grafts", "insourcing of vascular surgery",
             "national vascular registry", "interventional radiology",
             "stent graft"]:
    check("present: %s" % good, good in vtitles)

print("\nFRAMEWORKS")
vnames = [f["name"] for f in v["frameworks"]]
for want in ["Vascular Therapy and Associated Products",
             "Angiography, Hybrid Theatres, Capital Equipment, Related Accessories and Services"]:
    check("framework present: %s" % want, want in vnames)
check("exactly this speciality's two frameworks", len(vnames) == 2,
      "got %d: %s" % (len(vnames), vnames))
# Vascular access and IV therapy have their own NHSSC frameworks. A `vascular`
# match on the framework NAME must not reach across to them.
for other in ["Central Venous Catheters and Associated Products",
              "Intravenous Cannula and Associated Products",
              "Intravenous Accessories and Pressure Monitoring Accessories",
              "Renal Replacement Therapies Services, Technologies and Consumables"]:
    check("another speciality's framework stays out: %s" % other, other not in vnames)
check("every framework carries an end date", all(f.get("ends") for f in v["frameworks"]))
check("every framework carries its NHSSC url", all(f.get("url") for f in v["frameworks"]))

print("\nSUPPLIERS")
vsup = v["suppliers"]
check("suppliers are drawn from the frameworks, not empty", len(vsup) > 30)
check("alias merge did not inflate the raw NHSSC list", len(vsup) <= 37,
      "got %d, expected no more than the 37 raw framework-page names" % len(vsup))
check("no supplier listed twice", len(vsup) == len(set(s["name"] for s in vsup)))
check("every supplier names at least one framework", all(s["frameworks"] for s in vsup))
check("every named framework is one of this speciality's",
      all(set(s["frameworks"]) <= set(vnames) for s in vsup))
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in vsup))

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
# The IC/IR framework this patch actually buys its implants through is not in
# frameworks.json. The panel must say so on both counts it affects, or the two
# frameworks it does hold read as the whole buying picture.
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "2021/S 000-017565" in (v.get("rules") or {}).get(k, ""))
check("the missing IC/IR suppliers are named as uncounted",
      "not counted" in (v.get("rules") or {}).get("suppliers", ""))

print("\nNO DRUG TARIFF AND NO CPV, SAID HONESTLY (rule 14)")
check("no tariff panel is published", v.get("drugTariff") is None)
check("the drugTariff rule explains the absence",
      "No Drug Tariff part applies" in (v.get("rules") or {}).get("drugTariff", ""))
check("the awards rule states that no CPV family corroborates",
      "No CPV family corroborates" in (v.get("rules") or {}).get("awards", ""))
check("no award claims CPV corroboration",
      not any(a.get("cpvCorroborates") for a in v["awards"]))
# The specialities that DO have a CPV list must keep saying so.
check("a speciality with a CPV list still states it",
      "CPV code beginning 3314111" in (d.get("rules") or {}).get("awards", ""))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((v.get("rules") or {}).get(k)))
check("licence notice carried", bool(v.get("_notice", {}).get("owner")))
vkb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", VASCULAR + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % vkb, vkb < 200)


print("\n" + "=" * 70)
print("CONTINENCE, BLADDER AND BOWEL (slug continence-bladder-and-bowel, page 2910)")
print("=" * 70)
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), CONTINENCE],
               check=True, capture_output=True)
c = load_panel(CONTINENCE)

check("the label is the page's own name",
      c.get("label") == "Continence, Bladder and Bowel", "got %r" % c.get("label"))

print("\nTHE MATCHER ITSELF — synthetic titles, so these hold when the data changes")
# Run the compiled rule directly rather than only over today's rows. Every title
# below is a real one from tender-history.json or framework-awards.json, or a
# minimal version of one, and each was read before being classed.
crx = B.compile_rule(B.SPECIALITY_RULES[CONTINENCE])
must_match = [
    "Continence Home Delivery - Brent CLCH",
    "Indwelling Urinary Catheters & Drainage Bags",
    "Urinary Catheters & Drainage Bags",
    "Stoma Acute Patient",
    "Faecal Management System",
    "Continence Pads & Garments",
    "NP57122 Supply and Delivery of Continence Products",
    "Invitation to Tender for the Supply of Urine Meters",
    "National Framework Agreement for the Provision of Prescription Hub Services "
    "(Stoma and/or Catheter)",
]
for t in must_match:
    check("matches: %s" % t[:60], B.match_title(crx, t), "did not match")
must_not_match = [
    # Matched `include` and were read and rejected — these are the exclude list.
    "Evacuated Blood Collection Systems and Urine Collection Systems",
    "Managed Service for Catheterisation Lab, Cardio Thoracic Centre and Vascular",
    "Tower 2 - Surgical Mesh, Fixation Devices, Stress Incontinence and Bulking Agents",
    # Never admitted at all: this is why `catheter`, `urology`, `urinary`, `bowel`,
    # `faecal`, `pad`, `absorbent`, `irrigation` and `toilet` are not bare terms.
    "Central Venous Catheters and Associated Products",
    "Supply of Renal Catheters and Fistula Packs",
    "HRIM Solid State Catheter",
    "Procurement of Impella Structural Heart Catheter Device",
    "Urology Consumables",
    "Provision of Maintenance & Consumables for Urology Robot",
    "GGC0584 Endourology Disposable Products",
    "NH2659 Urology Cystoscopy Surveillance Service",
    "NP36126 Antibiotic & Genito Urinary Medicines",
    "NHSS Bowel Screening Test Kits and Analysers",
    "NHS Scotland Bowel Screening FIT Kits, Distribution and Analysers",
    "Faecal Immunochemical Testing (FIT) to provide support for patients identified "
    "with symptoms associated with bowel cancer",
    "GP13A.UK. Grid Pad 13A,",
    "Absorbents",
    "IV Fluids & Irrigation Solutions",
    "Paper Hygiene and Toilet Tissue",
    "The Supply and Delivery of High Back Slings, Dress Toileting Slings, Electric "
    "Hoists, Stand Aids and Stand Aid Slings",
    "National Framework Agreement for Transperineal Prostate Biopsy System",
    "Memokath stents for BCH Urology service",
    # Diagnostics. Real bladder work, deliberately out of scope for this page.
    "Bladder Scanners",
    "CUBESCAN BIOCON-700-S BLADDER SCANNER",
    "ESNEFT3207 Urodynamics",
]
for t in must_not_match:
    check("never admitted: %s" % t[:60], not B.match_title(crx, t), "matched and should not")

print("\nAND THE SAME, ON TODAY'S PUBLISHED SLICE")
ctitles = " || ".join((a.get("title") or "") for a in c["awards"]).lower()
for bad in ["blood collection", "catheterisation lab", "surgical mesh",
            "stress incontinence", "bowel screening", "immunochemical",
            "grid pad", "genito urinary", "urology consumables", "endourology",
            "renal catheter", "central venous", "bladder scanner", "urodynamics",
            "toilet tissue", "toileting", "prostate", "memokath"]:
    check("excluded: %s" % bad, bad not in ctitles)
for good in ["continence home delivery", "stoma and/or catheter",
             "indwelling urinary catheters", "faecal management",
             "continence pads", "urine meters", "continence goods and services"]:
    check("present: %s" % good, good in ctitles)
check("every award shown is one the matcher still admits",
      all(B.match_title(crx, a["title"]) for a in c["awards"]))

print("\nFRAMEWORKS")
cnames = [f["name"] for f in c["frameworks"]]
for want in ["Disposable and Washable Continence Care", "Urology and Bowel Management"]:
    check("framework present: %s" % want, want in cnames)
check("exactly the two frameworks the page names", len(cnames) == 2,
      "got %d: %s" % (len(cnames), cnames))
# Each of these carries a continence, catheter or bowel word and belongs to another
# page: diagnostics, colorectal and endoscopy, urology, and IV therapy.
for other in ["Bladder Scanners and Associated Options and Related Services",
              "Endoscopy, Endourology and Oncology Ablation Consumables and Associated Products",
              "Male Intra-Urethral Catheter with Magnet Control",
              "Central Venous Catheters and Associated Products"]:
    check("another speciality's framework stays out: %s" % other, other not in cnames)
check("every framework carries an end date", all(f.get("ends") for f in c["frameworks"]))
check("every framework carries its NHSSC url", all(f.get("url") for f in c["frameworks"]))

print("\nSUPPLIERS")
csup = c["suppliers"]
check("suppliers are drawn from the frameworks, not empty", len(csup) > 55)
check("alias merge actually reduced the raw NHSSC list", len(csup) < 69,
      "got %d, expected fewer than the 69 raw framework-page names" % len(csup))
check("no supplier listed twice", len(csup) == len(set(s["name"] for s in csup)))
check("every supplier names at least one framework", all(s["frameworks"] for s in csup))
check("every named framework is one of this speciality's",
      all(set(s["frameworks"]) <= set(cnames) for s in csup))
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in csup))
# NHSSC spells these two firms differently on its own two framework pages.
for firm, spellings in (("Abena", 2), ("Essity", 2), ("Clinisupplies", 2)):
    rec = [s for s in csup if firm.lower() in s["name"].lower()]
    check("%s appears exactly once" % firm, len(rec) == 1,
          "got %s" % [s["name"] for s in rec])
    check("%s shows both NHSSC spellings" % firm,
          bool(rec) and len(rec[0]["variants"]) == spellings)

print("\nDRUG TARIFF — the dual-listed part label must not be dropped")
t = c.get("drugTariff") or {}
check("a tariff panel is published", bool(t))
for p in ("IXB", "IXC"):
    check("part carried: %s" % p, p in (t.get("parts") or []))
# NHSBSA writes six Manfred Sauer lines under the literal part "IXB & IXC".
# Matching is on the exact part string, so omitting this label loses them silently.
check("the dual-listed IXB & IXC label is carried, not silently dropped",
      "IXB & IXC" in (t.get("parts") or []))
check("IXA is not claimed — that is the wound care page's part",
      "IXA" not in (t.get("parts") or []))
check("the tariff is summarised, not shipped whole",
      "rows" not in t and t.get("lineCount", 0) > 9000)
check("the tariff names its effective month", bool(t.get("effectiveMonth")))

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
# Without this, 63 framework names read as the continence market. They are not:
# the larger half of this patch is prescribed in the community on Part IX.
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (c.get("rules") or {}).get(k, ""))
check("the prescription route is named as the uncounted half",
      "dispensing appliance contractors" in (c.get("rules") or {}).get("suppliers", ""))

print("\nNO CPV, SAID HONESTLY (rule 14)")
check("the awards rule states that no CPV family corroborates",
      "No CPV family corroborates" in (c.get("rules") or {}).get("awards", ""))
check("no award claims CPV corroboration",
      not any(a.get("cpvCorroborates") for a in c["awards"]))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((c.get("rules") or {}).get(k)))
check("licence notice carried", bool(c.get("_notice", {}).get("owner")))
ckb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", CONTINENCE + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % ckb, ckb < 200)


# ---------------------------------------------------------------------------
print("\n\n=== THEATRES AND SURGICAL (page 2798) ===")
print("Rebuilding the theatres slice from live data...")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), THEATRES],
               check=True, capture_output=True)
h = load_panel(THEATRES)
hrx = B.compile_rule(B.SPECIALITY_RULES[THEATRES])

print("\nFALSE POSITIVES — every one matched a draft rule and was read and rejected")
must_not_match = [
    # "theatre" the building, not the operating theatre.
    "HFT-26-27 DN720 Roofing Works: The Lectures Theatre at Willerby Hill",
    "Blue Light road Re-Surface Block 35 Beevers Theatres SJUH",
    # An estates water and salt contract that happens to serve decontamination plant.
    "Maintenance of Water Treatment Systems including Supply and Delivery of Salt "
    "relating to a range of Hospital Equip including Decontamination and Renal "
    "Equipment, Chemical and Microbiological Water Testing and Provision of "
    "Associated Testing Consumables",
    # Respiratory and critical care, matched on the word airway inside the phrase.
    "Preliminary Market Engagement for Consumables for Continuous Positive Airway "
    "Pressure (CPAP) and Adaptive Support Ventilation",
    # A mixed pharmacy basket in which anaesthetics is one category of four.
    "NP40925 Analgesics, Anaesthetics, Musculoskeletal & Joint Disease Medicines",
    # Haematology, matched on "haemostat".
    "NP646 Haemostatic & Coagulation Products",
    # Pharmacy aseptic isolators, the same false positive wound care excludes.
    "BCU-DCO-63450 Purchase of Positive Pressure Laminar Flow Isolators for Pharmacy, "
    "Ysbyty Gwynedd",
    # Laboratory autoclaves. Seven of the eight "autoclave" hits were these, which is
    # why the term is not in the include list at all.
    "202223 1605 - RCE Rotating Autoclave",
    "PURCH2250 Provision of Contract Agreement for the CL3 Compliant Double Ended "
    "Autoclave and Associated Parts",
    "Microbiology Autoclave Replacement",
    "Site Autoclave Service and Validation",
    "UKRI-6261 Self-Steam Generating Autoclave",
    # A radiology CO2 injector, which is why bare "insufflat" is not in the include.
    "Southend & Broomfield -Bracco -Protocol CO2 insufflators maintenance 5 years",
    # Everything bare "sterile" dragged in: pharmacy aseptics, PPE, neonatal feeding,
    # farm biosecurity, pathology and ventilated-patient critical care.
    "Aseptically Manipulated or Terminally Sterile Medicinal Products",
    "Sterile Nitrile Examination Gloves",
    "Sterile Milk Bottles [ 4692898 ]",
    "The Supply of Sterile Boot Swab Kits to the Animal and Plant Health Agency",
    "Non-Sterile Single Use Type IIR Facemasks without Anti-Fog Strip",
    "NSSCOVID-19 -281 Non Sterile AGP Disposable Gowns",
    "Sterile Closed Tracheal Suction Systems (3225312)",
    "Radiopharmaceutical Products, Generators and Sterile Nitrogen Vials",
    "Sterile Collection Trays (4918803)",
    # A stationery order must never be able to reach a member on "stapler".
    "Supply of Office Stationery including Staplers and Hole Punches",
    # Added 09/09/2026. The overnight feed brought this in and it matched on
    # "decontaminat\\w*". It is asbestos removal from a plant room at West
    # Hertfordshire — estates work, like the water treatment row, and the same reason
    # bare "decontamination" is never used on the framework pattern. It was caught
    # before it reached a member. This case exists so it cannot come back.
    "WHHT - Emergency DCU Supply and Plant Room Asbestos Decontamination Services",
]
for t in must_not_match:
    check("never admitted: %s" % t[:60], not B.match_title(hrx, t), "matched and should not")

print("\nTRUE POSITIVES — the exclusions must not take these with them")
must_match = [
    # The coagulation exclusion is the pair of words on purpose: excluding the single
    # word would have dropped this genuine electrosurgery award.
    "Purchase of Electrosurgical Devices (Cut & Coagulation, Uterine Ablation)",
    # The medicines exclusion must not reach a narrow anaesthetic-agent contract.
    "Anaesthetic Gases (Sevoflurane & Isoflurane)",
    "NHS National Framework Agreement for the supply of Inhalation Anaesthetics and Vaporisers",
    # Bare "airway" still has to work; only the CPAP phrase is taken back out.
    "Airway Management",
    "Surgical Staplers, Cutters & Clip Appliers and consumables",
    "Minimally Invasive - Energy and Stapling Devices",
    "Sterile Services Equipment for Somerset NHS Foundation Trust",
    "Sterilisation Tray Liners and Sterilisation Paper.",
    "Tray Wrap & Sterilisation Products",
    "Wound Closure Products",
    "Surgical Sutures",
    "Hire of Mobile EDU Decontamination Unit",
]
for t in must_match:
    check("admitted: %s" % t[:60], B.match_title(hrx, t), "did not match and should")

print("\nAND THE SAME, ON TODAY'S PUBLISHED SLICE")
htitles = " || ".join((a.get("title") or "") for a in h["awards"]).lower()
for bad in ["lectures theatre", "roofing", "re-surface", "water treatment", "cpap",
            "positive airway pressure", "musculoskeletal", "coagulation products",
            "autoclave", "laminar flow", "insufflator", "examination gloves",
            "milk bottles", "boot swab", "radiopharmaceutical"]:
    check("excluded: %s" % bad, bad not in htitles)
for good in ["minimally invasive surgery", "anaesthetic machines", "airway management",
             "procedure packs", "surgical gloves", "washer disinfector",
             "video laryngoscope", "diathermy", "surgical robot", "operating table",
             "decontamination unit"]:
    check("present: %s" % good, good in htitles)
check("every award shown is one the matcher still admits",
      all(B.match_title(hrx, a["title"]) for a in h["awards"]))

print("\nFRAMEWORKS")
hnames = [f["name"] for f in h["frameworks"]]
for want in ["Airway Management Products and Associated Equipment",
             "Electrosurgical Consumables and Related Accessories",
             "Instrument Decontamination and Accessories",
             "Minimally Invasive Surgery, Related Equipment and Accessories",
             "Operating Theatres Equipment and Related Accessories and Services",
             "Procedure Packs", "Robotic Medical Equipment and Associated Accessories",
             "Surgical Gloves", "Surgical Instruments",
             "Tray Wrap and Sterilisation Equipment", "Wound Closure"]:
    check("framework present: %s" % want, want in hnames)
check("exactly the thirteen frameworks this patch carries", len(hnames) == 13,
      "got %d: %s" % (len(hnames), hnames))
# Each of these carries a theatre-sounding word and belongs somewhere else: the
# vascular page, estates, the ward, single-speciality implants and capital, and the
# endoscopy and respiratory pages.
for other in ["Angiography, Hybrid Theatres, Capital Equipment, Related Accessories and Services",
              "Environmental Decontamination",
              "Examination Gloves",
              "Surgical Mesh",
              "Surgical Navigation Systems with Associated Options and Related Services",
              "Flexible Endoscopes and Associated Options and Related Services",
              "Endoscopy, Endourology and Oncology Ablation Consumables and Associated Products",
              "Non Invasive Ventilation, Sleep Therapy, CPAP and Sleep Monitoring Diagnostics"]:
    check("another speciality's framework stays out: %s" % other, other not in hnames)
check("no Men's and Women's Health implants framework crept in",
      not any(n.startswith("Surgical Implants for Men") for n in hnames))
check("every framework carries an end date", all(f.get("ends") for f in h["frameworks"]))
check("every framework carries its NHSSC url", all(f.get("url") for f in h["frameworks"]))

print("\nSUPPLIERS")
hsup = h["suppliers"]
raw = sum(len(f["suppliers"]) for f in h["frameworks"])
check("suppliers are drawn from the frameworks, not empty", len(hsup) > 200)
check("alias merge actually reduced the raw NHSSC list", len(hsup) < raw,
      "got %d, expected fewer than the %d raw framework-page names" % (len(hsup), raw))
check("no supplier listed twice", len(hsup) == len(set(s["name"] for s in hsup)))
check("every supplier names at least one framework", all(s["frameworks"] for s in hsup))
check("every named framework is one of this speciality's",
      all(set(s["frameworks"]) <= set(hnames) for s in hsup))
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in hsup))

print("\nNO DRUG TARIFF, SAID HONESTLY (rule 14)")
check("no tariff panel is published for this patch", h.get("drugTariff") is None)
check("the tariff rule says why rather than going quiet",
      "No Drug Tariff part applies" in (h.get("rules") or {}).get("drugTariff", ""))

print("\nCPV CORROBORATES, IT NEVER ADMITS")
check("the awards rule names the CPV families claimed",
      "33162" in (h.get("rules") or {}).get("awards", ""))
check("at least one award records CPV corroboration",
      any(a.get("cpvCorroborates") for a in h["awards"]))
# The guard that matters: a CPV hit alone must not be able to publish a row.
check("a theatre CPV code cannot admit a title that does not match",
      not B.match_title(hrx, "Newborn Transport Harnesses for London Ambulance"))

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
# Without this, thirteen framework names read as the theatres market. They are not.
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (h.get("rules") or {}).get(k, ""))
check("the other buying routes are named as uncounted",
      "HealthTrust Europe" in (h.get("rules") or {}).get("suppliers", ""))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((h.get("rules") or {}).get(k)))
check("licence notice carried", bool(h.get("_notice", {}).get("owner")))
hkb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", THEATRES + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % hkb, hkb < 200)


# ---------------------------------------------------------------------------
print("\n\n=== ORTHOPAEDICS AND TRAUMA (page 2799) ===")
print("Rebuilding the orthopaedics slice from live data...")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), ORTHO],
               check=True, capture_output=True)
o = load_panel(ORTHO)
orx = B.compile_rule(B.SPECIALITY_RULES[ORTHO])

print("\nFALSE POSITIVES — every one matched a draft rule and was read and rejected")
o_must_not_match = [
    # A mixed pharmacy basket caught on the word musculoskeletal. Theatres and
    # Surgical excludes the same notice for the same reason.
    "NP40925 Analgesics, Anaesthetics, Musculoskeletal & Joint Disease Medicines",
    # Chronic pain neuromodulation, not spinal surgery.
    "Neuromodulation/Spinal Cord Stimulators, Intrathecal Drug Pumps, "
    "Radiofrequency Ablation and Associated Products",
    # Spinal and epidural anaesthesia needles. The word spinal here is the
    # anaesthetic route, not the spine.
    "Spinal, Epidural and Associated Products",
    # Psychological trauma, in an NHS England research notice. The single reason
    # bare "trauma" needs a guard at all.
    "Impact of HPV self-testing- insights & good practice in FGM, sexual abuse&trauma",
    # A referral IT platform for a gene therapy. Neurology, and software.
    "Referapatient for zolgensma for spinal muscular atrophy",
    # Audiology. This is why bare "bone" is not in the include list.
    "Bone Conduction",
    # Cardiac, matched only because it carries the word prosthesis.
    "Procurement of ONX Mechanical Aoritic/Mitral Valve, ON-X Ascending Aortic "
    "Prosthesis with Valsalva Graft",
    "External Breast Prosthesis [4233683]",
    "CLI-OJEU-45806 SURGICALLY IMPLANTED BREAST PROSTHESES",
    # Limb prosthetics and orthotics: the Rehabilitation, Prosthetics and Orthotics
    # patch, not this one.
    "Supply of Prosthetics",
    "Prosthetic Components and Associated Products",
    "Orthotics Service and Products Provision",
    "ORTHOTIC PRODUCTS AND SERVICES (INCLUDING PROSTHETIC SERVICES) (SBS10247)",
    "Orthoses Products and Provision of Orthotic Service",
    "Podiatry Orthoses Consumables [5820615]",
    "Custom Made Podiatry Orthoses for the South Eastern Health and Social Care "
    "Trust (SEHSCT)",
    # The one arguable row that dropping "podiatr" whole costs. Podiatric surgery is
    # its own profession and its own framework lot.
    "ESNEFT2762 Purchase of Power Tools for Podiatric Surgery",
]
for t in o_must_not_match:
    check("never admitted: %s" % t[:60], not B.match_title(orx, t), "matched and should not")

print("\nTRUE POSITIVES — the exclusions must not take these with them")
o_must_match = [
    # The successor to the framework this whole page turns on.
    "Total Orthopaedic Solutions 4",
    "Total Orthopaedic Solutions 3 (TOS3) (FaT)",
    "KGH Lot 1.5 Trauma Implants Medartis",
    # The FGM and sexual abuse exclusion must not reach a genuine trauma implant row.
    "UHN Lot 1.5 Trauma Implants Orthopaedics EU Ltd",
    "All Wales Orthopaedic, Trauma and Joint Replacement Framework",
    # The epidural and spinal cord stimulator exclusions must not reach real spine.
    "Bridging Contract - Replacement of Spinal Implants and Consumables",
    "Purchase of Orthopaedic Spinal & Scoliosis Implants & Consumables",
    "ESNEFT2394 Purchase of Spinal Navigation System",
    "Internal/External fixation",
    "TOS3 lot 1.8 Cement",
    "NHSSC - TOS3 1.8a Bone Prep Award",
    "Cardiff and Vale Knee Contract",
    "Needle Arthroscopy with Disposable Instruments",
    "Orthopaedic Surgical Robotic System (Hip Application)",
    "Purchase of Orthopaedic Hip & Knee Implants & Consumables",
    "Foot & Ankle Implants",
]
for t in o_must_match:
    check("admitted: %s" % t[:60], B.match_title(orx, t), "did not match and should")

print("\nAND THE SAME, ON TODAY'S PUBLISHED SLICE")
otitles = " || ".join((a.get("title") or "") for a in o["awards"]).lower()
for bad in ["orthotic", "orthoses", "podiatr", "prosthes", "epidural", "spinal cord",
            "medicines", "sexual abuse", "zolgensma", "bone conduction",
            "neuromodulation", "breast"]:
    check("excluded: %s" % bad, bad not in otitles)
for good in ["orthopaedic power tools", "trauma implants", "spinal implants",
             "arthroscopy", "knee", "bone prep", "total orthopaedic solutions 4",
             "internal/external fixation", "tourniquet"]:
    check("present: %s" % good, good in otitles)
check("every award shown is one the matcher still admits",
      all(B.match_title(orx, a["title"]) for a in o["awards"]))

print("\nFRAMEWORKS")
onames = [f["name"] for f in o["frameworks"]]
for want in ["Total Orthopaedic Solutions 3",
             "Surgical Navigation Systems with Associated Options and Related Services"]:
    check("framework present: %s" % want, want in onames)
check("exactly the two frameworks this patch carries", len(onames) == 2,
      "got %d: %s" % (len(onames), onames))
# Each of these carries an orthopaedic-sounding word and belongs somewhere else.
for other in [
        # Soft-tissue and urology robotics. Not one orthopaedic robot vendor is on it,
        # so it stays with Theatres and Surgical.
        "Robotic Medical Equipment and Associated Accessories",
        # The Rehabilitation, Prosthetics and Orthotics patch.
        "Orthotics, Podiatry and Immobilisation",
        "Prosthetic Components and Associated Products",
        "External Breast Prosthesis and Chest Support",
        # DXA scanning: diagnostic imaging and bone health, not orthopaedic surgery.
        "Bone Densitometers, Associated Options and Related Services",
        # Matched a draft pattern only on the word implantable.
        "Audiological Diagnostics Implantable Devices and Services"]:
    check("another speciality's framework stays out: %s" % other, other not in onames)
check("no Men's and Women's Health implants framework crept in",
      not any(n.startswith("Surgical Implants for Men") for n in onames))
check("every framework carries an end date", all(f.get("ends") for f in o["frameworks"]))
check("every framework carries its NHSSC url", all(f.get("url") for f in o["frameworks"]))

print("\nSUPPLIERS")
osup = o["suppliers"]
oraw = sum(len(f["suppliers"]) for f in o["frameworks"])
check("suppliers are drawn from the frameworks, not empty", len(osup) > 90)
check("alias merge actually reduced the raw NHSSC list", len(osup) < oraw,
      "got %d, expected fewer than the %d raw framework-page names" % (len(osup), oraw))
check("no supplier listed twice", len(osup) == len(set(s["name"] for s in osup)))
check("every supplier names at least one framework", all(s["frameworks"] for s in osup))
check("every named framework is one of this speciality's",
      all(set(s["frameworks"]) <= set(onames) for s in osup))
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in osup))

print("\nNO DRUG TARIFF, SAID HONESTLY (rule 14)")
check("no tariff panel is published for this patch", o.get("drugTariff") is None)
check("the tariff rule says why rather than going quiet",
      "No Drug Tariff part applies" in (o.get("rules") or {}).get("drugTariff", ""))

print("\nCPV CORROBORATES, IT NEVER ADMITS")
check("the awards rule names the CPV families claimed",
      "33183" in (o.get("rules") or {}).get("awards", ""))
check("at least one award records CPV corroboration",
      any(a.get("cpvCorroborates") for a in o["awards"]))
# The guard that matters, on three real notices that carry an orthopaedic CPV code
# and are not this speciality. The last one carries 85121283 inside a basket of
# twenty-five codes: filed under all of them, bought under one.
for cpv_only in ["Prosthetics and Orthotics Rehabilitation Service",
                 "Orthotic Footwear",
                 "Provision of Insourced and Outsourced Clinical Services Framework "
                 "(Framework Reopening)"]:
    check("an orthopaedic CPV code cannot admit: %s" % cpv_only[:50],
          not B.match_title(orx, cpv_only))

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
# Without this, 101 supplier names on TOS3 read as the orthopaedic market. They are not.
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (o.get("rules") or {}).get(k, ""))
check("the other buying routes are named as uncounted",
      "NHS Wales Shared Services" in (o.get("rules") or {}).get("suppliers", ""))
check("the shared navigation framework is declared shared",
      "shared with" in (o.get("rules") or {}).get("frameworks", ""))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((o.get("rules") or {}).get(k)))
check("licence notice carried", bool(o.get("_notice", {}).get("owner")))
okb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", ORTHO + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % okb, okb < 200)


print("\n\n=== PLASTICS, BURNS AND RECONSTRUCTION (page 2841) ===")
print("Rebuilding the plastics slice from live data...")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), PLASTICS],
               check=True, capture_output=True)
p = load_panel(PLASTICS)
prx = B.compile_rule(B.SPECIALITY_RULES[PLASTICS])

print("\nFALSE POSITIVES — the two rows the natural include really did let through")
ptitles = " || ".join((a.get("title") or "") for a in p["awards"]).lower()
# "Weishaupt Burners at Ysbyty Cwm Rhondda and Royal Glamorgan Hospital" is boiler
# plant, caught by burn\w*. "External Breast Prosthesis" is the post-mastectomy
# appliance, a Rehabilitation and Community route, caught by breast prosthes\w*.
for bad in ["weishaupt", "burner"]:
    check("excluded: %s" % bad, bad not in ptitles)
check("excluded: external breast prosthesis",
      "external breast prosthes" not in ptitles)
check("the estates burner row cannot match",
      not B.match_title(prx, "Weishaupt Burners at Ysbyty Cwm Rhondda and Royal Glamorgan Hospital"))
for ext in ["External Breast Prosthesis [4233683]", "External Breast Prosthesis"]:
    check("the external appliance cannot match: %s" % ext[:40],
          not B.match_title(prx, ext))

print("\nTERMS DELIBERATELY NOT CLAIMED — each would have pulled another page's work")
# Every string here is a real title from this data that a wider pattern would have
# admitted. bare "plastic" is the material; bare "skin" is infection prevention,
# pharmacy and cancer triage; bare "graft" is vascular; bare "laser" is ENT, urology
# and the laboratory; bare "breast" is imaging and oncology; dermatology is its own
# page; cranioplasty and cleft are declined as ambiguous on the title (rule 14).
for other in [
        "Motorized Patient Couch and Plastic Composite Outer Covers for a new MRI Scanner Design",
        "Skin Cleansing and Disinfection",
        "ENT, Ophthalmology & Skin Medicines/Medical Devices",
        "NHS Essex Integrated Care Board (ICB) Urgent Skin Cancer Dermoscopy Triage service",
        "Procurement of Jotec E-Vita Open Neo Stent Graft, AMDS Dissection Stent",
        "Vascular Grafts [2989252]",
        "ESNEFT2730 Purchase of ENT Laser",
        "POS Broomfield - Candela - laser GMAX PRO - 4 yrs maintenance",
        "Philips Epiq Elite Diagnostic Ultrasound for Breast Clinic CHH",
        "Insourcing of Breast Radiology Services",
        "Provision of Oncotype DX Breast Recurrence ScoreTM Assay",
        "Community Dermatology Service",
        "Supply of dermatoscopes & image transfer system",
        "Provision of Cranioplasties",
        "Cleft Registry and Audit Network (CRANE)",
        "ESNEFT3116 Purchase of Oscar Pro System"]:
    check("stays out: %s" % other[:52], not B.match_title(prx, other))

print("\nTRUE POSITIVES — awards that must be on this patch")
for good in ["cryoskin", "novosorb", "burns unit", "breast implants",
             "surgically implanted breast prostheses", "temporising matrix"]:
    check("present: %s" % good, good in ptitles)
check("every award shown is one the matcher still admits",
      all(B.match_title(prx, a["title"]) for a in p["awards"]))
check("the whole matched set is published, nothing silently capped",
      p["counts"]["awardsShown"] == p["counts"]["awardsMatched"])
# Three Find a Tender notices published the same day, three different notice ids.
# They are three awards, not one row de-duplicated badly.
cryo = [a for a in p["awards"] if "cryoskin" in (a["title"] or "").lower()]
check("the three Cryoskin awards are three distinct notices",
      len(set(a["url"] for a in cryo)) == len(cryo) == 3)

print("\nFRAMEWORKS")
pnames = [f["name"] for f in p["frameworks"]]
check("framework present: Advanced Wound Care", "Advanced Wound Care" in pnames)
check("exactly the one framework this patch carries", len(pnames) == 1,
      "got %d: %s" % (len(pnames), pnames))
# Each carries a word from this patch's vocabulary and belongs somewhere else.
for other in ["Reusable Plastic Medical Hollowware",
              "Skin Cleansing, Disinfection and Hygiene",
              "External Breast Prosthesis and Chest Support",
              "General Wound Care",
              "Negative Pressure Wound Therapy"]:
    check("another speciality's framework stays out: %s" % other, other not in pnames)
check("every framework carries an end date", all(f.get("ends") for f in p["frameworks"]))
check("every framework carries its NHSSC url", all(f.get("url") for f in p["frameworks"]))

print("\nSUPPLIERS")
psup = p["suppliers"]
praw = sum(len(f["suppliers"]) for f in p["frameworks"])
check("suppliers are drawn from the framework, not empty", len(psup) > 40)
check("no supplier listed twice", len(psup) == len(set(s["name"] for s in psup)))
check("every supplier names at least one framework", all(s["frameworks"] for s in psup))
check("every named framework is this speciality's",
      all(set(s["frameworks"]) <= set(pnames) for s in psup))
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in psup))
check("the supplier count matches the framework page's own stated total",
      len(psup) == praw == 56, "got %d resolved from %d raw" % (len(psup), praw))

print("\nNO DRUG TARIFF, SAID HONESTLY (rule 14)")
# Silicone scar products do sit in Part IXA, but IXA is the dressings and hosiery
# part and the builder can only filter by part. Publishing it here would put the
# wound care summary under a plastics heading.
check("no tariff panel is published for this patch", p.get("drugTariff") is None)
check("the tariff rule says why rather than going quiet",
      "No Drug Tariff part applies" in (p.get("rules") or {}).get("drugTariff", ""))

print("\nNO CPV CLAIMED, SAID HONESTLY")
# The only matching notices carrying a CPV code are the three Cryoskin awards and all
# three carry 33140000, medical consumables. Generic to the point of meaningless.
check("no CPV family is claimed for this patch",
      not B.SPECIALITY_RULES[PLASTICS].get("cpv"))
check("the awards rule says no CPV corroborates rather than going quiet",
      "No CPV family corroborates" in (p.get("rules") or {}).get("awards", ""))
check("no award claims CPV corroboration",
      not any(a.get("cpvCorroborates") for a in p["awards"]))

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
# Without this, 56 Advanced Wound Care suppliers read as a burns supplier list.
# NHS Supply Chain publishes no lot-by-lot breakdown, so they are not one.
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (p.get("rules") or {}).get(k, ""))
check("the missing lot breakdown is named",
      "lot-by-lot" in (p.get("rules") or {}).get("suppliers", ""))
check("the routes with no framework at all are named as uncounted",
      "Blood and Transplant" in (p.get("rules") or {}).get("suppliers", ""))

print("\nAN EMPTY PANEL IS AN HONEST ANSWER, NOT A REASON TO WIDEN (rule 14)")
check("no open tender on this patch today, and none invented",
      p["openTenders"] == [])
check("the open-tender rule says an empty list means none open",
      "empty list means" in (p.get("rules") or {}).get("openTenders", ""))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((p.get("rules") or {}).get(k)))
check("licence notice carried", bool(p.get("_notice", {}).get("owner")))
pkb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", PLASTICS + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % pkb, pkb < 200)



print("\n" + "=" * 72)
print("FRAILTY AND OLDER PEOPLE (page 2921)")
print("=" * 72)
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), FRAILTY],
               check=True, capture_output=True)
fr = load_panel(FRAILTY)
frx = B.compile_rule(B.SPECIALITY_RULES[FRAILTY])
ftitles = " || ".join((a.get("title") or "") for a in fr["awards"]).lower()

print("\nFALSE POSITIVES — every one matched a real row and was wrong")
# "aging" inside "imaging" is the single most dangerous pattern on this patch:
# thirty rows in this data would arrive on the frailty page as scanners. The rule
# uses neither "aging" nor "ageing".
for other in [
        "ESNEFT3075 Purchase of Neonatal Imaging System",
        "Magnetic Resonance Imaging System Replacement",
        "Static Medical Imaging Equipment",
        "Hyperspectral Imaging Equipment",
        "Night Vision Imaging System (NVIS) Replacement Programme",
        "Multimodal Imaging Platform Procurement",
        # bare "older people": nought out of two. Mental health workforce education,
        # and a housing association's own furniture supply.
        "Adult and Older People (AOP) mental health and Psychological Therapies for "
        "Severe Mental Health Problems (PTSMHP) education programmes RFI",
        "Supply and delivery of Older People Furniture and associated Services",
        # bare "rehabilitation": nineteen rows, not one of them this speciality.
        "Residential detoxification and rehabilitation service for residents",
        "Brain Injury Rehabilitation Service.",
        "Neurological Rehabilitation Service",
        "Provision of Residential Rehabilitation Services for Border Force",
        "Prosthetics and Orthotics Rehabilitation Service",
        # the palliative page's rows, not this one's. One is a children's service.
        "Palliative and End of Life Care and Community Services",
        "West Yorkshire CYP Palliative and End of Life Care Out of Hours Service "
        "- 24/7 Advice and Call-Out Support",
        "National Audit of Care at the End of Life (NACEL)",
        # "dementia" is core vocabulary and stays in; this is the one row it got
        # wrong, and "ligature" is the whole exclusion list.
        "Consultancy Services for IP&C, Ligature and Dementia issues at Angelton "
        "Clinic & Ysbyty Cwm Cynon",
        # declined as ambiguous on the title (rule 14), not excluded by accident.
        "Ardwyn - Supported Living",
        "SOL30141 SOL Extra Care Solihull Retirement Village",
        "HMP Wandsworth- Domiciliary Care",
        # "Healthcare at Home" is a homecare medicines route, not this patch. The
        # include's "hospital at home" must not reach it.
        "Immunoglobulin -Healthcare at Home",
        "Ustekinumab (Stelara) Healthcare at Home",
        # \bcare technology\b must not match "Healthcare Technology" — the word
        # boundary is the entire reason that pattern is safe to carry.
        "YPO - 001284 Community & Healthcare Technology Equipment & Associated Services",
        # \bcare homes?\b must not match "healthcare home"-shaped titles either.
        "Healthcare Homes Group supplies"]:
    check("stays out: %s" % other[:52], not B.match_title(frx, other))

print("\nTRUE POSITIVES — awards that must be on this patch")
for good in ["telecare", "community equipment", "care home", "intermediate care",
             "virtual ward", "technology enabled care", "falls prevention",
             "independent living", "digital care alarms", "nursing care beds"]:
    check("present: %s" % good, good in ftitles)
check("every award shown is one the matcher still admits",
      all(B.match_title(frx, a["title"]) for a in fr["awards"]))
check("the whole matched set is published, nothing silently capped",
      fr["counts"]["awardsShown"] == fr["counts"]["awardsMatched"])
# The community half of this pathway is bought by councils, not trusts. If that
# ever stops being true of the awards list, the filter has drifted.
councils = [a for a in fr["awards"]
            if "council" in (a.get("buyer") or "").lower()
            or "borough" in (a.get("buyer") or "").lower()]
check("the local-authority route dominates the awards, as the page says it does",
      len(councils) >= 15, "got %d of %d" % (len(councils), len(fr["awards"])))

print("\nTHE CLINICAL VOCABULARY IS MOSTLY ABSENT FROM THE DATA, AND SAID SO")
# These were zero rows in 3,314 when the rule was written. They stay in the
# include because each can only mean this speciality, and this block records
# which of them the data has since caught up with.
#
# REABLEMENT MOVED, 10/09/2026, and it moved the way this block said it would:
# "Reablement Care Service" (London Borough of Enfield, 08/09/2026) is a genuine
# award on this patch and the panel is right to publish it. The word is now
# asserted PRESENT rather than absent, because leaving it in the absent list
# would make a correctly working filter look like a broken one on every run.
for word in ["frailty", "geriatric", "delirium",
             "urgent community response", "discharge to assess"]:
    check("nothing published on '%s' today" % word, word not in ftitles)
check("reablement is published now that a real notice exists for it",
      "reablement" in ftitles)
check("the include still carries the speciality's own vocabulary",
      all(w in B.SPECIALITY_RULES[FRAILTY]["include"]
          for w in ["frailty", "geriatric", "delirium", "reablement"]))

print("\nFRAMEWORKS")
fnames = [f["name"] for f in fr["frameworks"]]
check("framework present: Technology Enabled Care",
      any(n.startswith("Technology Enabled Care") for n in fnames))
check("exactly the one framework this patch carries", len(fnames) == 1,
      "got %d: %s" % (len(fnames), fnames))
# All three carry this population's equipment and all three are the Patient Moving
# and Handling page's. Claiming them would republish that page's supplier list.
for other in ["Aids for Daily Living", "Pressure Area Care and Patient Handling",
              "Wheelchairs, Specialist Seating and Related Services",
              "Physiotherapy and Occupational Therapy",
              "Disposable and Washable Continence Care"]:
    check("another speciality's framework stays out: %s" % other, other not in fnames)
check("every framework carries its NHSSC url", all(f.get("url") for f in fr["frameworks"]))

print("\nSUPPLIERS")
fsup = fr["suppliers"]
fraw = sum(len(f["suppliers"]) for f in fr["frameworks"])
check("suppliers are drawn from the framework, not empty", len(fsup) > 0)
check("no supplier listed twice", len(fsup) == len(set(s["name"] for s in fsup)))
check("every supplier names at least one framework", all(s["frameworks"] for s in fsup))
check("every named framework is this speciality's",
      all(set(s["frameworks"]) <= set(fnames) for s in fsup))
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in fsup))
check("the supplier count matches the framework page's own stated total",
      len(fsup) == fraw == 18, "got %d resolved from %d raw" % (len(fsup), fraw))

print("\nCPV CORROBORATES, IT NEVER ADMITS")
# 85144100 is residential nursing care and is the one code here specific to this
# patch. 85323000, community health services, sits on the two intermediate care
# rows and would look like the obvious key — until you read the other forty
# notices carrying it: CAMHS tier 4 beds, suicide prevention, smoking cessation,
# dental services in Gwent, a drug test on arrest scheme.
check("the narrow residential-care code is the one claimed",
      B.SPECIALITY_RULES[FRAILTY].get("cpv") == ("85144100",))
check("the community-health catch-all is not claimed",
      "85323000" not in (B.SPECIALITY_RULES[FRAILTY].get("cpv") or ()))
check("corroboration is recorded where the feed carries the code",
      any(a.get("cpvCorroborates") for a in fr["awards"]))
check("no award reached the panel on CPV alone",
      all(B.match_title(frx, a["title"]) for a in fr["awards"] if a.get("cpvCorroborates")))

print("\nNO DRUG TARIFF, SAID HONESTLY (rule 14)")
# Older people are the largest users of Parts IXA and IXB, but the tariff has no
# frailty part and the builder filters by part, not product. Claiming IXB would
# publish the continence page's summary under a frailty heading.
check("no tariff panel is published for this patch", fr.get("drugTariff") is None)
check("the tariff rule says why rather than going quiet",
      "No Drug Tariff part applies" in (fr.get("rules") or {}).get("drugTariff", ""))

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
# One framework out of 121 is not this speciality's buying route, and 18 telecare
# suppliers are not the frailty market. Both have to say so on the page.
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (fr.get("rules") or {}).get(k, ""))
check("the absence of any frailty framework is named",
      "no framework for frailty" in (fr.get("rules") or {}).get("frameworks", "").lower())
check("the sibling page carrying the equipment is named",
      "Patient Moving and Handling" in (fr.get("rules") or {}).get("suppliers", ""))

print("\nAN EMPTY PANEL IS AN HONEST ANSWER, NOT A REASON TO WIDEN (rule 14)")
check("no open tender on this patch today, and none invented",
      fr["openTenders"] == [])
check("the open-tender rule says an empty list means none open",
      "empty list means" in (fr.get("rules") or {}).get("openTenders", ""))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((fr.get("rules") or {}).get(k)))
check("licence notice carried", bool(fr.get("_notice", {}).get("owner")))
fkb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", FRAILTY + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % fkb, fkb < 200)


print("\n" + "=" * 72)
print("INTERVENTIONAL RADIOLOGY (page 2842)")
print("=" * 72)
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), IR],
               check=True, capture_output=True)
ir = load_panel(IR)
irx = B.compile_rule(B.SPECIALITY_RULES[IR])
irtitles = " || ".join((a.get("title") or "") for a in ir["awards"]).lower()

print("\nFALSE POSITIVES — every one matched a real row and was wrong")
# "Anti-Embolism Stockings" is the one that matters most: the natural "embolis\w*"
# form of the include matches the word EMBOLISM, and VTE prophylaxis stockings are
# the opposite of this speciality's business. Without the guard, NHS Wales'
# compression stocking contract arrives on the IR page.
for other in [
        "Anti-Embolism Stockings",
        "Interventional Implantable Cardiac Devices and Accessories 5643930",
        "Interventional and Diagnostic Cardiac Cath Lab Consumables [3935547]",
        "Percutaneous Catheter Delivered Heart Pumps",
]:
    check("excluded: %s" % other[:52], not B.match_title(irx, other))
    check("absent from the panel: %s" % other[:52], other.lower() not in irtitles)

# Terms deliberately not claimed, each tried and read. If a future edit widens the
# include to any of them, these fail before the panel ships.
for other in [
        "Breast Biopsy Needle NPM",
        "National Framework Agreement for Transperineal Prostate Biopsy System",
        "Endometrial Ablation Devices and Uterine Tissue Removal Systems",
        "Prostatic Ablation Devices",
        "Oncology Ablation Consumables",
        "Cath Labs and Cardiology Stents",
        "Memokath stents for BCH Urology service",
        "Purchase of Fluoroscopy Equipment",
        "Suction Consumables, Wound Drainage, Autologous Blood Systems and Related Accessories",
        "4183924 External Ventricular Drainage (EVD)",
        "WSFT - Capital Projects - CCTV Drainage Survey for New Hospital Development",
        "Update of ONYX imaging platform and existing hardware for Public Health Wales",
        "Purchase of replacement coil for Logiq E10S",
        "Auto-injectors for PET-CT Service",
        "Contract for the supply of Duodote autoinjectors",
]:
    check("not claimed: %s" % other[:52], not B.match_title(irx, other))

print("\nTRUE POSITIVES — awards that must be on this patch")
for good in ["interventional radiology products",
             "np68424 interventional radiology",
             "contrast media",
             "lipiodol",
             "percutaneous instrument insertion"]:
    check("present: %s" % good, good in irtitles)
# The headline framework award and the July 2026 biopsy move, both named on the
# page's own Buying route section.
check("the NHS Supply Chain IC/IR/INR framework award is on the panel",
      "interventional neuroradiology" in irtitles)
check("the framework the biopsy codes moved to on 01/07/2026 is on the panel",
      "needles including biopsy" in irtitles)

print("\nSCOPE DECISION, TESTED SO IT CANNOT DRIFT SILENTLY")
# INR is admitted because the page publishes it (a section headed "Thrombectomy and
# thrombolysis — peripheral and neurovascular", and Lot 2 with its 16 suppliers).
# The exclusion list must never grow a neuroradiology pattern: NHS Supply Chain's
# own framework title carries the word NEURORADIOLOGY, so excluding it would drop
# this patch's headline framework award — the same trap the vascular rule records.
check("the two Scottish INR awards are admitted",
      "inr and thrombectomy consumables" in irtitles
      and "interventional neuro radiology and thrombectomy" in irtitles)
check("no neuroradiology exclusion, which would drop the headline framework",
      "neuroradiolog" not in B.SPECIALITY_RULES[IR]["exclude"].lower())

print("\nFRAMEWORKS")
irnames = [f["name"] for f in ir["frameworks"]]
check("exactly the two parsable frameworks on this patch", len(irnames) == 2,
      "got %r" % irnames)
for want in ["Contrast Injectors, Consumables and Associated Options and Related Services",
             "Angiography, Hybrid Theatres, Capital Equipment, Related Accessories and Services"]:
    check("framework present: %s" % want[:48], want in irnames)
# Reference 2021/S 000-007768 is shared by eleven imaging briefs. Only the contrast
# injectors one is this speciality; the other ten are Radiology and Imaging's.
for other in ["CT Scanners and Associated Options and Related Services",
              "Magnetic Resonance Imaging Scanners and Associated Option and Related Services",
              "Fluoroscopy and Associated Options and Related Services",
              "Mammography Imaging Systems and Associated Options and Related Services",
              "Ultrasound Scanners and Associated Options and Related Services",
              "Nuclear Medicine Imaging and Associated Options and Related Services",
              "Static X-Ray and Associated Options and Related Services",
              "Mobile X-Ray Systems and Associated Option and Related Services",
              "Endoscopy, Endourology and Oncology Ablation Consumables and Associated Products"]:
    check("not claimed from a shared reference: %s" % other[:44], other not in irnames)
check("every framework carries an end date",
      all(f.get("ends") for f in ir["frameworks"]))

print("\nSUPPLIERS ARE READ OFF THE FRAMEWORK, NEVER GUESSED")
irsup = ir["suppliers"]
irnamed = {s["name"] for s in irsup}
check("every named supplier is on one of this speciality's frameworks",
      all(set(s["frameworks"]) <= set(irnames) for s in irsup))
# The page names the five contrast injector suppliers off the National Product
# Matrix dated 10 March 2026. All five must be here, under whatever name the alias
# registry resolves them to.
allnames = " || ".join(irnamed | {v for s in irsup for v in s["variants"]}).lower()
for want in ["bayer", "bracco", "guerbet", "mis healthcare", "synapse medical"]:
    check("contrast injector supplier present: %s" % want, want in allnames)
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in irsup))
check("no supplier appears twice under two spellings",
      len(irnamed) == len(irsup))

print("\nCPV CORROBORATES, IT NEVER ADMITS")
# 33696800 is X-ray contrast media and is the one code in this data specific to
# this patch. 33110000 (imaging equipment) and 33140000 (medical consumables) sit
# on the other matching notice and corroborate everything, so neither is claimed.
check("the narrow contrast-media code is the one claimed",
      B.SPECIALITY_RULES[IR].get("cpv") == ("33696800",))
for generic in ("33110000", "33140000"):
    check("the catch-all %s is not claimed" % generic,
          generic not in (B.SPECIALITY_RULES[IR].get("cpv") or ()))
check("no award reached the panel on CPV alone",
      all(B.match_title(irx, a["title"]) for a in ir["awards"] if a.get("cpvCorroborates")))

print("\nNO DRUG TARIFF, SAID HONESTLY (rule 14)")
# Part IX reimburses dressings and hosiery, incontinence and stoma appliances.
# Nothing an IR suite buys is listed there and the page claims no tariff presence.
check("no tariff panel is published for this patch", ir.get("drugTariff") is None)
check("the tariff rule says why rather than going quiet",
      "No Drug Tariff part applies" in (ir.get("rules") or {}).get("drugTariff", ""))

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
# This speciality's own framework is in frameworks.json's `unparsed` list, so its
# 67 suppliers cannot be counted. A panel that showed 19 suppliers without saying
# so would read as the IR supplier market, which it is not.
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (ir.get("rules") or {}).get(k, ""))
irfw = (ir.get("rules") or {}).get("frameworks", "")
check("the unparsable headline framework is named",
      "2021/S 000-017565" in irfw)
check("the two routes with no NHS Supply Chain page are named",
      "2026/S 000-002484" in irfw and "NP68424" in irfw)

print("\nAN EMPTY PANEL IS AN HONEST ANSWER, NOT A REASON TO WIDEN (rule 14)")
check("no open tender on this patch today, and none invented",
      ir["openTenders"] == [])
check("the open-tender rule says an empty list means none open",
      "empty list means" in (ir.get("rules") or {}).get("openTenders", ""))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((ir.get("rules") or {}).get(k)))
check("licence notice carried", bool(ir.get("_notice", {}).get("owner")))
irkb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", IR + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % irkb, irkb < 200)

print("\n" + "=" * 72)
print("CARDIOLOGY AND CARDIAC SURGERY (page 2801)")
print("=" * 72)
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), CARDIAC],
               check=True, capture_output=True)
ca = load_panel(CARDIAC)
cax = B.compile_rule(B.SPECIALITY_RULES[CARDIAC])

print("\nFALSE POSITIVES — every one matched `include` and was read and rejected")
catitles = " || ".join((a.get("title") or "") for a in ca["awards"]).lower()
# Each of these is a real row in tender-history.json or framework-awards.json.
for bad, why in [
    ("lifeport", "Organ Recovery Systems kidney transport perfusion, not bypass"),
    ("cold static perfusion", "NHS Blood and Transplant organ preservation solution"),
    ("respiratory medicines", "a Scottish national pharmacy contract, not devices"),
    ("ophthalmology visual electrophysiology", "visual evoked potentials, not cardiac EP"),
    ("principal designer", "an architect's CDM appointment, CPV 71315200"),
    ("scientists training programme", "NHS England workforce commissioning, CPV 80000000"),
    ("anaesthetics machines", "a four-item basket bought by anaesthesia and critical care"),
]:
    check("excluded: %s (%s)" % (bad, why), bad not in catitles)
# These never reach `include` at all, because the loose term that would admit them
# was refused. Each is a real row that a wider pattern would have published here.
for bad in ["healthy hearts", "htg valves", "external ventricular drainage",
            "memokath", "endometrial ablation", "uterine ablation",
            "diffractometer", "tavistock", "zetaview", "extavia",
            "defibrillators and aeds", "chest compression"]:
    check("never admitted: %s" % bad, bad not in catitles)
# CARDIFF is the reason bare "cardi" is refused.
check("bare 'cardi' refused so CARDIFF cannot match",
      not cax["inc"].search("CPD Courses 26/27 Cardiff University")
      and not cax["inc"].search("PUBLIC HEALTH WALES BTW CARDIFF - BUILDING WORKS"))
check("TAVI needs a boundary on both sides",
      not cax["inc"].search("TAVISTOCK EDUCATION AND TRAINING")
      and not cax["inc"].search("Interferon Beta-1b (Extavia)")
      and bool(cax["inc"].search("TAVI valve delivery system")))
check("VAD is not matched, because VAD is also a vascular access device",
      not cax["inc"].search("Vascular Access Device (VAD) Consumables")
      and bool(cax["inc"].search("Ventricular Assist Device")))
check("FFR is not matched, because it matches DIFFRACTOMETER",
      not cax["inc"].search("Supply of an X-ray Diffractometer"))

print("\nTRUE POSITIVES — awards that must be on this patch")
for want in ["cardiac rhythm management", "structural heart", "impella",
             "heart valves", "pacemakers", "cardioplegia", "cath lab",
             "perfusion heart lung", "echocardiogram", "ecg",
             "aortic root", "cardiology stents"]:
    check("present: %s" % want, want in catitles)
# Checked against the rule, not against the panel, because AWARD_CAP shows the 40
# most recent of the 58 matched and these sit below that line today. The invariant
# is that the rule admits them, which is what would break if a pattern were lost.
for want in ["TRANSCATHETER HEART VALVE REPAIR, REPLACEMENT AND ASSOCIATED DEVICES",
             "Procurement of ONX Mechanical Aoritic/Mitral Valve, ON-X Ascending "
             "Aortic Prosthesis with Valsalva Graft",
             "Atriclip Gillinov-Cosgrove:  Left Atrial Appendage Exclusion System Device",
             "Percutaneous Catheter Delivered Heart Pumps",
             "Cardiopulmonary Bypass Oxygenators with Customised Tubing Pack [2339172]",
             "Cardiac Surgery Consumables [4152960]",
             "Purchase of ECMO Trolley",
             "Consumables for Continuous Cardiac Ouput (CCO) Monitoring"]:
    check("rule admits: %s" % want[:44], B.match_title(cax, want))
check("at least 40 awards matched", ca["counts"]["awardsMatched"] >= 40)
check("every award shown really matches the published rule",
      all(B.match_title(cax, a["title"]) for a in ca["awards"]))

print("\nFRAMEWORKS ARE THE SPECIALITY'S OWN, AND RESUSCITATION IS NOT ONE")
canames = {f["name"] for f in ca["frameworks"]}
for want in ["Cardiac and Pulmonary Diagnostics and Exercise (Stress) Testing Solutions",
             "Structural Heart and Ventricular Assist Devices",
             "Perfusion Devices, Consumables and Associated Equipment",
             "Angiography, Hybrid Theatres, Capital Equipment, Related Accessories and Services"]:
    check("framework claimed: %s" % want[:46], want in canames)
# Both were read and both are resuscitation or general ward consumables. Claiming
# them would put public-access AED distributors and an office-supplies wholesaler
# on this page as cardiology suppliers.
for other in ["External Defibrillation Devices and Related Services and Accessories",
              "Electrodes, Ultrasound Gels, Defibrillation and Related Consumables",
              "Patient Monitoring Equipment, Bedside Equipment Alarm Monitoring Systems, "
              "Related Products and Services",
              "Central Venous Catheters and Associated Products"]:
    check("resuscitation/general ward not claimed: %s" % other[:44], other not in canames)
# Cardiac and Pulmonary Diagnostics went live on 27 July 2026 and NHS Supply Chain
# publishes no end date for it on the brief. That is the record, not a gap in the
# parse, so the test states the exception by name rather than asserting something
# untrue. If any OTHER framework loses its end date, this fails.
check("every framework carries a reference and a start date",
      all(f.get("reference") and f.get("starts") for f in ca["frameworks"]))
check("only the one framework with no published end date lacks one",
      {f["name"] for f in ca["frameworks"] if not f.get("ends")}
      == {"Cardiac and Pulmonary Diagnostics and Exercise (Stress) Testing Solutions"})
# The angiography suite is shared with interventional radiology and vascular
# surgery on purpose. If that sharing ever silently stops, this fails.
check("the angio suite is shared with interventional radiology, not duplicated away",
      "Angiography, Hybrid Theatres, Capital Equipment, Related Accessories and Services"
      in {f["name"] for f in ir["frameworks"]})

print("\nSUPPLIERS ARE READ OFF THE FRAMEWORK, NEVER GUESSED")
casup = ca["suppliers"]
canamed = {s["name"] for s in casup}
check("every named supplier is on one of this speciality's frameworks",
      all(set(s["frameworks"]) <= set(canames) for s in casup))
caall = " || ".join(canamed | {v for s in casup for v in s["variants"]}).lower()
# Named on the Structural Heart and VAD and Perfusion briefs read at NHS Supply Chain.
for want in ["abbott", "edwards lifesciences", "medtronic", "abiomed",
             "livanova", "getinge", "terumo", "corcym"]:
    check("structural heart / perfusion supplier present: %s" % want, want in caall)
# Named on the External Defibrillation brief and nowhere else on this patch. If one
# of these appears, the resuscitation framework has been claimed by mistake.
for bad in ["british heart foundation", "martek lifecare", "aero healthcare",
            "lyreco"]:
    check("resuscitation/office supplier absent: %s" % bad, bad not in caall)
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in casup))
check("no supplier appears twice under two spellings",
      len(canamed) == len(casup))

print("\nCPV CORROBORATES, IT NEVER ADMITS")
# All four descriptions were read back from Find a Tender's own OCDS API on
# 09/09/2026: 33112340 Echocardiographs, 33121500 Electrocardiogram, 33123
# Cardiovascular devices, 85121231 Cardiology services. Every one fires.
check("only cardiac-specific families are claimed",
      B.SPECIALITY_RULES[CARDIAC].get("cpv") == ("33112340", "33121500", "33123", "85121231"))
for generic in ("33100000", "33110000", "33140000", "33190000", "33124100", "33121000"):
    check("the catch-all %s is not claimed" % generic,
          generic not in (B.SPECIALITY_RULES[CARDIAC].get("cpv") or ()))
check("no award reached the panel on CPV alone",
      all(B.match_title(cax, a["title"]) for a in ca["awards"] if a.get("cpvCorroborates")))
check("at least one award is corroborated by CPV",
      any(a.get("cpvCorroborates") for a in ca["awards"]))

print("\nNO DRUG TARIFF, SAID HONESTLY (rule 14)")
# Pacemakers, leads, coronary stents, heart valves, oxygenators and cath lab
# capital are not reimbursed through Part IX.
check("no tariff panel is published for this patch", ca.get("drugTariff") is None)
check("the tariff rule says why rather than going quiet",
      "No Drug Tariff part applies" in (ca.get("rules") or {}).get("drugTariff", ""))

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (ca.get("rules") or {}).get(k, ""))
cafw = (ca.get("rules") or {}).get("frameworks", "")
check("the unparsable headline framework is named", "2021/S 000-017565" in cafw)
check("its end date and successor are named",
      "26 February 2027" in cafw and "2026/S 000-043775" in cafw)
check("the resuscitation frameworks are named as deliberately absent",
      "External Defibrillation" in cafw)

print("\nAN EMPTY PANEL IS AN HONEST ANSWER, NOT A REASON TO WIDEN (rule 14)")
check("no open tender on this patch today, and none invented",
      ca["openTenders"] == [])
check("the open-tender rule says an empty list means none open",
      "empty list means" in (ca.get("rules") or {}).get("openTenders", ""))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((ca.get("rules") or {}).get(k)))
check("licence notice carried", bool(ca.get("_notice", {}).get("owner")))
cakb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", CARDIAC + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % cakb, cakb < 200)

print("\n" + "=" * 70)
print("NUTRITION AND DIETETICS (page 2911)")
print("=" * 70)
print("Rebuilding the nutrition and dietetics slice from live data...")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), NUTRITION],
               check=True, capture_output=True)
nu = load_panel(NUTRITION)
nux = B.compile_rule(B.SPECIALITY_RULES[NUTRITION])
nutitles = " || ".join((a.get("title") or "") for a in nu["awards"]).lower()

print("\nFALSE POSITIVES — every one matched the include list and was rejected")
# The four exclusion patterns, tested against the exact real titles that put them
# there. Each has to be admitted by `include` and then thrown out by `exclude`,
# otherwise the guard is decoration rather than a working filter.
for title, why in [
    ("Gastro Intestinal, Endocrine, Nutrition & Blood Generic Medicines",
     "Scottish generic medicines basket, Kent Pharmaceuticals"),
    ("Gastrointestinal, Endocrine, Nutrition & Blood Medicines",
     "the same basket, 2025 award"),
    ("Procurement of Peg-asparaginase Injection from Alloga   UK",
     "PEGylated chemotherapy enzyme, Belfast HSCT"),
    ("CPD Courses 26/27 British Dietetic Association (BDA)",
     "workforce training, CPV 80000000"),
    ("NHS National Framework for Generics Orals, Non-Parenteral & Housekeeping",
     "generic oral medicines, NHS England"),
]:
    check("include admits it (so the guard is doing work): %s" % why,
          bool(nux["inc"].search(title)))
    check("exclude rejects it: %s" % why, not B.match_title(nux, title))

# Kept out at the include stage instead, because "food" and "catering" are hospital
# catering on this patch, not dietetics.
for title, why in [
    ("Central Procurement of Vitamin D  Food Supplements Clinically Extremely Vulnerable",
     "DHSC shielding vitamin mailout, BNF 0906"),
    ("BVD PCR Test Kits for Serum and Milk Samples", "bovine viral diarrhoea, SRUC"),
    ("Breast Pumps and Breast Milk Collection Sets [5180689]",
     "maternity and neonatal, which has its own page"),
    ("Sterile Milk Bottles [ 4692898 ]", "milk kitchen hardware, maternity and neonatal"),
]:
    check("never admitted in the first place: %s" % why, not B.match_title(nux, title))

for bad in ["endocrine", "asparaginase", "cpd courses", "non-parenteral", "vitamin d",
            "serum and milk", "breast pump", "sterile milk bottles", "ambient food"]:
    check("absent from the published panel: %s" % bad, bad not in nutitles)

print("\nTRUE POSITIVES — awards that must be on this patch")
for good in ["enteral feeding, bile bags and associated products",
             "home parenteral nutrition", "unlicensed parenteral nutrition",
             "enteral feeds", "nutritional supplies", "enteral feeding pumps",
             "parenteral nutrition formulation bags for neo nates"]:
    check("present: %s" % good, good in nutitles)
check("nothing was lost to the exclusion list: every matched award is published",
      nu["counts"]["awardsShown"] == nu["counts"]["awardsMatched"] == 26,
      "shown=%s matched=%s" % (nu["counts"]["awardsShown"], nu["counts"]["awardsMatched"]))

print("\nFRAMEWORKS")
nunames = [f["name"] for f in nu["frameworks"]]
for want in ["Enteral Feeding, Bile Bags and Associated Products",
             "Infant Feeding and Accessories"]:
    check("framework present: %s" % want, want in nunames)
check("exactly two frameworks, and no third crept in", len(nunames) == 2,
      "got %d: %s" % (len(nunames), nunames))
# The catering trap. Aymes and Danone Nutricia are both named on Ambient Food, so a
# supplier-led filter would pull the whole NHSSC Food category onto a dietetics page.
for bad in ["Ambient Food", "Fresh Food DPS", "Multi Temperature Food Solutions",
            "Food Vending Solutions", "Catering Consumables and Equipment"]:
    check("catering framework kept out: %s" % bad, bad not in nunames)
# \bbile\b matches "Mobile". Four NHSSC frameworks start with that word.
for bad in ["Mobile X-Ray Systems and Associated Option and Related Services",
            "Mobile Image Intensifiers and Associated Options and Related Services"]:
    check("the Mobile/bile collision is not made: %s" % bad[:28], bad not in nunames)
check("every framework carries an end date", all(f.get("ends") for f in nu["frameworks"]))
check("every framework carries its NHSSC url", all(f.get("url") for f in nu["frameworks"]))
check("both framework references are the ones the page verified",
      sorted(f["reference"] for f in nu["frameworks"]) ==
      ["2023/S 000-011743", "2025/S 000-028317"])

print("\nSUPPLIERS ARE READ OFF THE FRAMEWORK, NEVER GUESSED")
nusup = nu["suppliers"]
check("every named supplier is on one of this speciality's frameworks",
      all(set(s["frameworks"]) <= set(nunames) for s in nusup))
check("no supplier appears twice", len(nusup) == len(set(s["name"] for s in nusup)))
nuall = " || ".join({s["name"] for s in nusup} |
                    {v for s in nusup for v in s["variants"]}).lower()
# Named on the two contract launch briefs read at NHS Supply Chain.
for want in ["nutricia", "abbott", "fresenius kabi", "vygon", "avanos", "medicina",
             "hipp", "kendal nutricare", "ardo", "medela"]:
    check("framework supplier present: %s" % want, want in nuall)
# Named on Ambient Food and the other catering frameworks and nowhere else on this
# patch. If one appears, a catering framework has been claimed by mistake.
for bad in ["weetabix", "walkers snacks", "tilda", "brake bros", "kraft heinz",
            "premier foods", "unilever"]:
    check("catering supplier absent: %s" % bad, bad not in nuall)
# GBUK Enteral and Kendal Nutricare are on both frameworks, spelled two ways across
# NHSSC's own pages. 19 + 18 = 37 raw names, 35 companies.
check("the alias merge actually reduced the raw NHSSC list", len(nusup) == 35,
      "got %d, expected 35 from 37 raw names" % len(nusup))
gbuk = [s for s in nusup if "gbuk" in s["name"].lower()]
check("GBUK appears exactly once", len(gbuk) == 1, "got %s" % [s["name"] for s in gbuk])
check("GBUK is credited on both frameworks",
      bool(gbuk) and len(gbuk[0]["frameworks"]) == 2)
check("a merged supplier shows both NHSSC spellings",
      bool(gbuk) and len(gbuk[0]["variants"]) == 2)
check("an unresolved name is flagged, never silently merged",
      all(("resolved" in s) for s in nusup))

print("\nCPV CORROBORATES, IT NEVER ADMITS")
# 33692200 Parenteral nutrition products, read back from Find a Tender's own OCDS API
# on 09/09/2026 (release ocds-h6vhtk-06eba1, notice 080876-2026).
check("only the parenteral nutrition family is claimed",
      B.SPECIALITY_RULES[NUTRITION].get("cpv") == ("33692200",))
# 33692300 Enteral feeds and 15882000 Dietetic products would both look right here.
# Neither appears on a single notice in this data, so neither is claimed.
for unfired in ("33692300", "15882000", "33600000", "33690000", "15800000"):
    check("the unfired family %s is not claimed" % unfired,
          unfired not in (B.SPECIALITY_RULES[NUTRITION].get("cpv") or ()))
check("no award reached the panel on CPV alone",
      all(B.match_title(nux, a["title"]) for a in nu["awards"] if a.get("cpvCorroborates")))
check("at least one award is corroborated by CPV",
      any(a.get("cpvCorroborates") for a in nu["awards"]))

print("\nNO DRUG TARIFF, SAID HONESTLY (rule 14)")
# Part IX carries no enteral feeding or nutrition category at all. Feeds, oral
# nutritional supplements and gluten-free products are reimbursed under Part XV,
# borderline substances, on ACBS approval, which is a different list entirely.
check("no tariff panel is published for this patch", nu.get("drugTariff") is None)
check("no tariff part is claimed", not B.SPECIALITY_RULES[NUTRITION].get("tariffParts"))
check("the tariff rule says why rather than going quiet",
      "No Drug Tariff part applies" in (nu.get("rules") or {}).get("drugTariff", ""))
check("Part XV is named as the real reimbursement route",
      "Part XV" in (nu.get("rules") or {}).get("frameworks", ""))

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (nu.get("rules") or {}).get(k, ""))
nufw = (nu.get("rules") or {}).get("frameworks", "")
check("the community market this panel cannot see is quantified", "638.2m" in nufw)
check("both framework references and their end dates are named",
      "2025/S 000-028317" in nufw and "13 July 2027" in nufw
      and "2023/S 000-011743" in nufw and "28 February 2028" in nufw)
check("the concentration a rep needs is stated", "68.7%" in nufw)

print("\nAN EMPTY PANEL IS AN HONEST ANSWER, NOT A REASON TO WIDEN (rule 14)")
check("no open tender on this patch today, and none invented", nu["openTenders"] == [])
check("the open-tender rule says an empty list means none open",
      "empty list means" in (nu.get("rules") or {}).get("openTenders", ""))

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((nu.get("rules") or {}).get(k)))
check("licence notice carried", bool(nu.get("_notice", {}).get("owner")))
nukb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", NUTRITION + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % nukb, nukb < 200)


# ---------------------------------------------------------------------------
print("\nOBESITY AND WEIGHT MANAGEMENT (page 2927)")
print("Rebuilding the obesity and weight management slice from live data...")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), OBESITY],
               check=True, capture_output=True)
ob = load_panel(OBESITY)
obx = B.compile_rule(B.SPECIALITY_RULES[OBESITY])

print("\nFALSE POSITIVES — every one matched the include list and was read and rejected")
# All four are real rows from the 09/09/2026 derivation. Three are kept out at the
# include stage (the bare tier and lifestyle patterns were never adopted); the
# fourth cannot be, because "obese" is the core word of the speciality.
for bad in [
    "Tier 2 Cardiology and Direct Access Diagnostics",
    "CAMHs Tier 4 Beds and associated services",
    "NHS South West London ICB - Long-Term Conditions (LTC) Community Outreach, Expert "
    "Patient Programme (EPP) LTC Self-Management And Pentathlon Healthy Lifestyle "
    "Programme Services.",
    "Combined Safety Syringes and Needles for COVID-19 Vaccination Programme - "
    "Morbidly Obese Requirement",
]:
    check("excluded: %s" % bad[:58], not B.match_title(obx, bad))

# The COVID guard has to be the reason, not a coincidence of the include list.
check("the COVID vaccination row is caught by the exclude list, not missed by include",
      bool(obx["inc"].search("Combined Safety Syringes and Needles for COVID-19 "
                            "Vaccination Programme - Morbidly Obese Requirement")))
# ...and the guard must stay narrow enough to keep a genuine row.
check("the COVID guard does not throw away a genuine pen needle row",
      B.match_title(obx, "Supply of Wegovy Pen Needles and Sharps Disposal"))

print("\nTRUE POSITIVES — rows that must be present")
obt = " || ".join((a.get("title") or "") for a in ob["awards"]).lower()
for good in ["obesity pathway innovation programme",
             "child tier 2 weight management service",
             "bariatric equipment rental",
             "bariatric hire contract",
             "level 3 digital weight management service"]:
    check("present: %s" % good, good in obt)
check("every award matched is shown (8 of 8)",
      ob["counts"]["awardsShown"] == ob["counts"]["awardsMatched"] == 8,
      "shown=%s matched=%s" % (ob["counts"]["awardsShown"], ob["counts"]["awardsMatched"]))

print("\nNO FRAMEWORK IS A FINDING, NOT A GAP (rule 14)")
check("the rule declares no framework rather than a pattern that finds none",
      B.SPECIALITY_RULES[OBESITY]["frameworks"] is None)
check("no framework is published", ob["frameworks"] == [] and ob["counts"]["frameworks"] == 0)
check("no supplier list is published", ob["suppliers"] == [] and ob["counts"]["suppliers"] == 0)
obfw = (ob.get("rules") or {}).get("frameworks", "")
obsup = (ob.get("rules") or {}).get("suppliers", "")
check("the frameworks rule says outright that none covers this speciality",
      "NO NHS Supply Chain framework covers this speciality" in obfw)
check("the suppliers rule explains why the list is empty",
      "no supplier list is published" in obsup.lower() and "keyword guess" in obsup.lower())

# THE TRAP. Arjo won both bariatric contracts and sits on four NHSSC frameworks,
# every one of them another page's. If a later edit reaches for one to fill this
# panel out, this fails.
print("\nTHE SHARED-SUPPLIER TRAP MUST STAY REFUSED")
for stolen in ["Pressure Area Care and Patient Handling", "Aids for Daily Living",
               "Operating Theatres Equipment and Related Accessories and Services",
               "Vascular Therapy and Associated Products"]:
    check("not claimed from another page: %s" % stolen[:44],
          not any(f.get("name") == stolen for f in ob["frameworks"]))

print("\nNOTHING IS CLAIMED THAT THE DATA DOES NOT SUPPORT")
check("no CPV family is claimed", not B.SPECIALITY_RULES[OBESITY].get("cpv"))
check("no tariff part is claimed", not B.SPECIALITY_RULES[OBESITY].get("tariffParts"))
check("no Drug Tariff block is published", ob.get("drugTariff") is None)
check("no open tender on this patch today, and none invented", ob["openTenders"] == [])
# The molecule names were deliberately not adopted: dual-licensed, and the
# diabetes and endocrinology page has its own claim on them.
for straddler in ["Supply of Tirzepatide", "Semaglutide Injection Framework",
                  "Mounjaro KwikPen Supply", "Liraglutide Tender"]:
    check("dual-licensed molecule not claimed: %s" % straddler[:34],
          not B.match_title(obx, straddler))
# ...but the obesity-only brands are.
check("obesity-only brands are claimed", B.match_title(obx, "Provision of Orlistat and Mysimba"))

print("\nTHE COVERAGE LIMIT IS STATED, NOT HIDDEN")
check("the prescribing route this panel cannot see is quantified", "574,302,390" in obfw)
check("the share of England's prescribing bill is stated", "4.93%" in obfw)
check("the bariatric surgery volume is stated", "7,260" in obfw)
check("absence from the panel is not presented as absence from the market",
      "Absence from this panel is not absence from this market" in obfw)

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((ob.get("rules") or {}).get(k)))
check("licence notice carried", bool(ob.get("_notice", {}).get("owner")))
obkb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", OBESITY + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % obkb, obkb < 200)

print("\nTHE RENDERER HAS AN HONEST EMPTY STATE FOR BOTH TABS")
_js = open(os.path.join(HERE, "app", "speciality-panels.js"), encoding="utf-8").read()
check("frameworks tab does not render a header-only table",
      "if (!d.frameworks.length) {" in _js
      and "No NHS Supply Chain framework covers this speciality." in _js)
check("suppliers tab does not render a search box over an empty table",
      "if (!d.suppliers.length) {" in _js
      and "No supplier list is published for this speciality." in _js)


# ---------------------------------------------------------------------------
print("\nNEUROLOGY AND NEUROSURGERY (page 2800)")
print("Rebuilding the neurology and neurosurgery slice from live data...")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), NEURO],
               check=True, capture_output=True)
ne = load_panel(NEURO)
nex = B.compile_rule(B.SPECIALITY_RULES[NEURO])

print("\nFALSE POSITIVES — every one is a real row that a wider rule matched and was read and rejected")
for bad in [
    # Oncology. "neuroendocrine" is why the include list names the neuro- compounds
    # one by one instead of matching the prefix.
    "Purchase of AAA Netspot - Diagnostic Imaging Agent Kit to Detect Neuroendocrine Tumours",
    "Purchase of 177Lu- Dotatate (Lutathera ®) to treat patients with neuroendocrine tumours",
    # Children's autism and ADHD support, and an estates audit.
    "Neurodevelopmental Support for Children, Families and Professionals",
    "Neurodiverse Environmental Audits",
    # An MRI scanner is the radiology and imaging page's patch whatever the suite
    # it stands in is called.
    "Neuro MRI: MRI 1 and MRI 3",
    # Rehabilitation beds and services, which are the rehabilitation page's.
    "Brain Injury Rehabilitation Service.",
    "Provision of Specialist Level 2b Neuro-rehabilitation Beds",
    "Neurological Rehabilitation Service",
    # Breast biopsy, which is why bare "stereotactic" was never adopted.
    "PR8980 - RFL Mammography Equipment consumables for Stereotactic Procedure",
    # Orthopaedic spine and anaesthesia, which is why bare "spinal" was never adopted.
    "Purchase of Orthopaedic Spinal & Scoliosis Implants & Consumables",
    "Bridging Contract - Replacement of Spinal Implants and Consumables",
    "BWC - Edge Medical Ltd - Spinal Surgical consumables",
    "Spinal, Epidural and Associated Products",
    "Epidural Pumps",
    # Laboratory, ophthalmic and ENT microscopes, which is why only the qualified
    # "operating microscope" is used.
    "BX53 Microscope",
    "ESNEFT3184 Purchase of Ophthalmic Microscope",
    "ESNEFT2728 Purchase of ENT Microscope for Theatre",
    "PURCH2281 PROVISION OF A CONTRACT FOR A MULTI-SPECTRAL LIGHT SHEET MICROSCOPE & "
    "ASSOCIATED MAINTENANCE",
    # Stroke has its own page and its own pathway.
    "Provision of Transport for Stroke and Suspected Stroke Patients",
    "Early Stroke Discharge Service",
    "Stroke Central Monitor",
    # A referral platform for a commissioned gene therapy, not a neurology purchase.
    "Referapatient for zolgensma for spinal muscular atrophy",
    # INR is the international normalised ratio far more often than it is
    # interventional neuroradiology, and the title cannot tell them apart.
    "INR and Thrombectomy Consumables",
    # The multi-speciality NHSSC framework, counted on the cardiology and
    # interventional radiology pages.
    "INTERVENTIONAL CARDIOLOGY, INTERVENTIONAL RADIOLOGY AND INTERVENTIONAL "
    "NEURORADIOLOGY, CARDIAC RHYTHM MANAGEMENT AND ELECTROPHYSIOLOGY",
]:
    check("excluded: %s" % bad[:58], not B.match_title(nex, bad))

print("\nTHE EXCLUDE LIST MUST BE THE REASON, NOT A COINCIDENCE OF THE INCLUDE LIST")
# Both exclusions exist because the include list really does reach these rows. If a
# later edit narrows the include list, these stop testing anything, so assert both
# halves: the include matches, and the exclude is what stops it.
for caught in ["Neurological Rehabilitation Service",
               "INTERVENTIONAL CARDIOLOGY, INTERVENTIONAL RADIOLOGY AND INTERVENTIONAL "
               "NEURORADIOLOGY, CARDIAC RHYTHM MANAGEMENT AND ELECTROPHYSIOLOGY"]:
    check("include reaches it, exclude stops it: %s" % caught[:40],
          bool(nex["inc"].search(caught)) and bool(nex["exc"].search(caught)))
# ...and the rehabilitation guard must stay narrow enough to keep the genuine rows.
check("the rehabilitation guard does not throw away a genuine neurophysiology row",
      B.match_title(nex, "Neurophysiology Insourced Services"))

print("\nTRUE POSITIVES — rows that must be on this patch")
net = " || ".join((a.get("title") or "") for a in ne["awards"]).lower()
for good in ["neurosurgery consumables", "provision of cranioplasties",
             "dural repair patches", "external ventricular drainage",
             "intracranial pressure monitoring kits", "nerve conduction studies",
             "intraoperative neurophysiological monitoring",
             "neuromodulation devices consumables", "operating microscopes",
             "interventional neuro radiology"]:
    check("present: %s" % good, good in net)
check("every award matched is shown (33 of 33)",
      ne["counts"]["awardsShown"] == ne["counts"]["awardsMatched"] == 33,
      "shown=%s matched=%s" % (ne["counts"]["awardsShown"], ne["counts"]["awardsMatched"]))

print("\nFRAMEWORKS — two claimed, three named and left to the pages they belong to")
nenames = [f["name"] for f in ne["frameworks"]]
for want in ["Neuromodulation Devices and Associated Products",
             "Surgical Navigation Systems with Associated Options and Related Services"]:
    check("claimed: %s" % want[:46], want in nenames)
check("exactly two frameworks claimed", len(nenames) == 2, "got %s" % nenames)
# Each of these carries a slice of this speciality and each is refused, with the
# reason in the rule. If a later edit reaches for one to fill the panel out, this
# fails.
for notmine in ["Robotic Medical Equipment and Associated Accessories",
                "Total Orthopaedic Solutions 3"]:
    check("not claimed from another page: %s" % notmine[:44], notmine not in nenames)
# The microscopes framework is in frameworks.json's `unparsed` list, so it cannot be
# claimed even though its Lot 1 carries Neurological Operating. Its award notice does
# reach the Awards list, which is asserted above.
check("the unparsed microscopes framework is not claimed",
      not any("Microscopes" in n for n in nenames))
check("the neuromodulation framework end date is carried",
      any(f.get("ends") == "18 March 2028" for f in ne["frameworks"]))

print("\nSUPPLIERS — the frameworks' own lists, one name per company")
nesup = ne["suppliers"]
check("28 suppliers from 29 raw names across the two frameworks",
      len(nesup) == 28, "got %d" % len(nesup))
medtronic = [s for s in nesup if s["name"] == "Medtronic"]
check("Medtronic appears exactly once", len(medtronic) == 1,
      "got %s" % [s["name"] for s in nesup if "medtronic" in s["name"].lower()])
check("Medtronic is credited on both frameworks",
      bool(medtronic) and len(medtronic[0]["frameworks"]) == 2)
# The alias registry keeps T.J. Smith and Nephew (Companies House 00093994) separate
# from Smith+Nephew (00156031) on purpose. It must be flagged, never merged and never
# dropped.
tj = [s for s in nesup if s["name"].lower().startswith("t.j.smith")]
check("T.J. Smith and Nephew is kept as NHSSC wrote it", len(tj) == 1)
check("...and flagged unresolved rather than merged into Smith+Nephew",
      bool(tj) and tj[0]["resolved"] is False)
check("no supplier from Total Orthopaedic Solutions 3 leaked in",
      not any(s["name"] in ("Zimmer Biomet Limited", "Arthrex Ltd", "Corin Ltd")
              for s in nesup))
# The robotics framework's other five suppliers hold no neurological lot. If the
# framework is ever claimed, they arrive with it and this fails.
for offpatch in ("CMR Surgical Ltd", "Intuitive Surgical Limited", "Procept Biorobotics"):
    check("no robotics-only supplier on this patch: %s" % offpatch,
          not any(s["name"] == offpatch for s in nesup))

print("\nNOTHING IS CLAIMED THAT THE DATA DOES NOT SUPPORT")
check("no CPV family is claimed", not B.SPECIALITY_RULES[NEURO].get("cpv"))
check("the awards rule says why no CPV family is claimed",
      "No CPV family corroborates" in (ne.get("rules") or {}).get("awards", ""))
check("no award reached the panel on CPV alone",
      all(B.match_title(nex, a["title"]) for a in ne["awards"]))
check("no tariff part is claimed", not B.SPECIALITY_RULES[NEURO].get("tariffParts"))
check("no Drug Tariff block is published", ne.get("drugTariff") is None)
check("the tariff rule says why rather than going quiet",
      "No Drug Tariff part applies" in (ne.get("rules") or {}).get("drugTariff", ""))
check("no open tender on this patch today, and none invented", ne["openTenders"] == [])

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
nefw = (ne.get("rules") or {}).get("frameworks", "")
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (ne.get("rules") or {}).get(k, ""))
check("the products with no framework at all are named",
      "cranial implants" in nefw and "aneurysm clips" in nefw)
check("the size of the brief index that was read is stated", "140 unique briefs" in nefw)
check("the three uncounted frameworks are named, not dropped",
      "Robotic Medical Equipment" in nefw and "Total Orthopaedic Solutions 3" in nefw
      and "Microscopes" in nefw)
check("absence from the panel is not presented as absence from the market",
      "being absent from one is not evidence of absence from this market" in nefw)

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((ne.get("rules") or {}).get(k)))
check("licence notice carried", bool(ne.get("_notice", {}).get("owner")))
nekb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", NEURO + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % nekb, nekb < 200)


# ---------------------------------------------------------------------------
print("\nPALLIATIVE AND END-OF-LIFE CARE (page 2924)")
print("Rebuilding the palliative and end-of-life care slice from live data...")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), PALLIATIVE],
               check=True, capture_output=True)
pa = load_panel(PALLIATIVE)
pax = B.compile_rule(B.SPECIALITY_RULES[PALLIATIVE])

print("\nFALSE POSITIVES — every one is a real row that a wider rule matched and was read and rejected")
for bad in [
    # THE EXCLUSION THAT EXISTS. National pandemic stockpile intravenous giving sets,
    # bought by the Secretary of State. "Administration sets" is kept in the include
    # list because it is this framework's own product name; the stockpile is swept out.
    "RPG Medical Administration Sets for Pandemic Preparedness 25/26",
    "Medical Administration Sets for Pandemic Preparedness 24/25",
    # Diabetes and a trauma rapid infuser, which is why bare "infusion pump" was
    # never adopted. All three genuine category contracts say "syringe pump" or
    # "syringe driver" in the same title, so nothing is lost by refusing it.
    "Insulin Infusion Pumps, Continuous Glucose Monitoring Systems and Associated Consumables",
    "Rapid Infuser Blood/IV Infusion Pump",
    # A rheumatology biologic. An injection is not a continuous subcutaneous infusion,
    # which is why bare "subcutaneous" was never adopted.
    "Tocilizumab Subcutaneous Injection (RoActemra®)",
    # Bereavement support is part of end-of-life care in NG142, but not one bereavement
    # row in this data is the palliative kind: a maternity room fit-out, two suicide
    # bereavement services and a mortuary and funeral contract.
    "NGH - Maternity Bereavement Suite",
    "Provision of Suicide Bereavement Support Services",
    "Specialist Support Service For People Bereaved By Suicide",
    "Provision of Bereavement and Mortuary Services (Funeral)",
    "Kings Park Mortuary and Medical Records Store Demolition Works",
    # Terminal sterilisation, not terminal care.
    "Aseptically Manipulated or Terminally Sterile Medicinal Products Framework (Lot 5)",
    "Aseptically Manipulated or Terminally Sterile Medicinal Products",
    # A clinical guidelines app. EOL also means end of life for an ASSET at least as
    # often as for a patient, so the abbreviation is refused in both readings.
    "PAHT - EOLAS Medical Subscription",
    # Neither is a DNACPR or ReSPECT matter.
    "Purchase of Baby Warmers with Resuscitation",
    "Resuscitation Council Course Manuals and Registration Fee - ALS, ILS and PILS courses",
    # A council social care bed contract.
    "Residential, respite and nursing care beds",
    # Named here because the panel must never reach for the neighbouring patches whose
    # frameworks the page also lists. Each is another page's market.
    "Disposable and Washable Continence Care",
    "Wheelchairs, Specialist Seating and Related Services",
    "Pressure Area Care and Patient Handling",
]:
    check("excluded: %s" % bad[:58], not B.match_title(pax, bad))

print("\nTHE EXCLUDE LIST MUST BE THE REASON, NOT A COINCIDENCE OF THE INCLUDE LIST")
# The one exclusion exists because the include list really does reach these rows. If a
# later edit narrows the include list, this stops testing anything, so assert both
# halves: the include matches, and the exclude is what stops it.
for caught in ["RPG Medical Administration Sets for Pandemic Preparedness 25/26",
               "Medical Administration Sets for Pandemic Preparedness 24/25"]:
    check("include reaches it, exclude stops it: %s" % caught[:44],
          bool(pax["inc"].search(caught)) and bool(pax["exc"].search(caught)))
# ...and the pandemic guard must stay narrow enough to keep the genuine set rows.
check("the pandemic guard does not throw away a genuine administration set row",
      B.match_title(pax, "Infusion Pumps, Syringe Pumps, Administration Sets and Associated Equipment"))

print("\nTRUE POSITIVES — rows that must be on this patch")
pat = " || ".join((a.get("title") or "") for a in pa["awards"]).lower()
for good in ["palliative care medicines transport service",
             "bodyguard t syringe drivers",
             "pharmaceutical stock supplies to independent hospices",
             "palliative and end of life care and community services",
             "national audit of care at the end of life",
             "ambulatory pumps, subcutaneous, administration and gravity sets",
             "infusion pumps, syringe pumps, administration sets"]:
    check("present: %s" % good[:52], good in pat)
check("every award matched is shown (9 of 9)",
      pa["counts"]["awardsShown"] == pa["counts"]["awardsMatched"] == 9,
      "shown=%s matched=%s" % (pa["counts"]["awardsShown"], pa["counts"]["awardsMatched"]))

print("\nFRAMEWORKS — one claimed, six named and left to the routes they belong to")
panames = [f["name"] for f in pa["frameworks"]]
check("claimed: Infusion Pumps and Administration Sets and Associated Products",
      "Infusion Pumps and Administration Sets and Associated Products" in panames)
check("exactly one framework claimed", len(panames) == 1, "got %s" % panames)
# The five NHSSC frameworks the page also lists as buying routes are each counted on
# the page whose patch they primarily are. If a later edit reaches for one to fill this
# panel out, this fails.
for notmine in ["Pressure Area Care and Patient Handling",
                "Wheelchairs, Specialist Seating and Related Services",
                "Aids for Daily Living",
                "Disposable and Washable Continence Care",
                "Technology Enabled Care, Electronic Assistive Technology and Lone Worker Devices"]:
    check("not claimed from another page: %s" % notmine[:44], notmine not in panames)
# The commercial fact this whole patch turns on this quarter.
check("the framework expiry that the page leads on is carried",
      any(f.get("ends") == "30 September 2026" for f in pa["frameworks"]))
check("its NHS Supply Chain reference is carried",
      any(f.get("reference") == "Project_12 ITT_382" for f in pa["frameworks"]))
# NHS Supply Chain states no supplier total on this brief. That must travel with the
# count, never be quietly presented as a verified 27.
check("the unverified supplier count is flagged as NHSSC left it",
      any("UNVERIFIED COUNT" in (f.get("supplierSource") or "") for f in pa["frameworks"]))

print("\nSUPPLIERS — the framework's own list, one name per company")
pasup = pa["suppliers"]
check("26 suppliers from the 27 names NHS Supply Chain lists",
      len(pasup) == 26, "got %d" % len(pasup))
# The page's own warning is that 27 rows are not 27 competitors. The registry must
# actually collapse the ICU Medical group, or the panel repeats the error the page
# tells a rep to avoid.
icu = [s for s in pasup if s["name"] == "ICU Medical (incl. Smiths Medical)"]
check("ICU Medical and Smiths Medical resolve to one entry", len(icu) == 1)
check("...and both NHSSC spellings are shown against it",
      bool(icu) and sorted(icu[0]["variants"]) == ["ICU UK Medical Ltd", "Smiths Medical International Ltd"])
# Two Becton Dickinson legal entities, which the page names as two entities of one
# group. THE THING BEING PROTECTED IS THAT THEY STAY TWO. Merging them would tell a
# rep there is one BD on this framework when NHS Supply Chain names two, and
# dropping either would lose a competitor.
#
# UPDATED 10/09/2026. This pair used to assert the CME entity was UNRESOLVED,
# because it was not in the alias registry when the rule was written. Commit
# 84602d4 ("Infusion Pumps framework: BD (CME) record") deliberately onboarded it
# as an entity in its own right, so it now resolves to itself and the panel has no
# unresolved suppliers at all. The old assertion described the registry's gap, not
# the guarantee, and it is replaced rather than left standing with a note.
cme = [s for s in pasup if "CME" in s["name"]]
check("the Becton Dickinson (CME) entity is kept as NHSSC wrote it", len(cme) == 1)
check("...as its own company, never merged into the other BD entity",
      bool(cme) and cme[0]["name"] != "BD — Becton, Dickinson"
      and any(s["name"] == "BD — Becton, Dickinson" for s in pasup))
check("no supplier on this framework is left unresolved",
      pa["counts"]["suppliersUnresolved"] == 0,
      "got %s" % pa["counts"]["suppliersUnresolved"])
# Eitan holds the framework in its own right. It must be present: the page's Suppliers
# section turns on Eitan being on the framework but having no part in the T34.
check("Eitan Medical is present in its own right",
      any(s["name"].lower().startswith("eitan") for s in pasup))
# No supplier may arrive from a framework this page does not claim.
for offpatch in ("Juzo", "Sigvaris Britain Ltd", "Molnlycke Health Care Ltd"):
    check("no supplier from an unclaimed framework: %s" % offpatch,
          not any(s["name"] == offpatch for s in pasup))

print("\nNOTHING IS CLAIMED THAT THE DATA DOES NOT SUPPORT")
check("no CPV family is claimed", not B.SPECIALITY_RULES[PALLIATIVE].get("cpv"))
check("the awards rule says why no CPV family is claimed",
      "No CPV family corroborates" in (pa.get("rules") or {}).get("awards", ""))
check("no award reached the panel on CPV alone",
      all(B.match_title(pax, a["title"]) for a in pa["awards"]))
# Part IX genuinely reaches dying patients at home. It is still refused here, because
# IXA, IXB and IXC are the tissue viability, continence and stoma pages' lists.
check("no tariff part is claimed", not B.SPECIALITY_RULES[PALLIATIVE].get("tariffParts"))
check("no Drug Tariff block is published", pa.get("drugTariff") is None)
check("the tariff rule says why rather than going quiet",
      "No Drug Tariff part applies" in (pa.get("rules") or {}).get("drugTariff", ""))
check("no open tender on this patch today, and none invented", pa["openTenders"] == [])

print("\nTHE COVERAGE LIMIT IS PUBLISHED, NOT HIDDEN (rule 14)")
pafw = (pa.get("rules") or {}).get("frameworks", "")
for k in ("frameworks", "suppliers"):
    check("coverage limit stated on the %s rule" % k,
          "COVERAGE LIMIT" in (pa.get("rules") or {}).get(k, ""))
# The defining fact about this patch: most of the addressable estate is not the NHS
# and cannot appear in any procurement dataset.
check("the non-NHS hospice estate is quantified rather than implied",
      "288 registered hospice locations" in pafw and "167 providers are not NHS bodies" in pafw)
check("the NHS SBS route is named and its absence explained",
      "SBS10015" in pafw and "NHS Supply Chain briefs only" in pafw)
check("the five frameworks counted elsewhere are named, not dropped",
      "Pressure Area Care and Patient Handling" in pafw
      and "Disposable and Washable Continence Care" in pafw
      and "Technology Enabled Care" in pafw)
check("the 26-against-27 supplier count is explained where a member will see it",
      "reads 26 and not 27" in pafw)
check("27 names are not presented as 27 competitors",
      "27 names are not 27 competitors" in pafw)

print("\nTHE RULE TRAVELS WITH THE DATA (rule 14a)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((pa.get("rules") or {}).get(k)))
check("licence notice carried", bool(pa.get("_notice", {}).get("owner")))
pakb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", PALLIATIVE + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % pakb, pakb < 200)

# ---------------------------------------------------------------------------
# PATHOLOGY AND LABORATORY MEDICINE (page 2827), added 09/09/2026.
#
# This patch's whole difficulty is that laboratory medicine shares its entire
# vocabulary with academic research, veterinary science, forensic science, water
# hygiene and bioprocessing, all of which buy the same instruments from the same
# companies. Every excluded case below is a REAL row that matched the include list
# and was wrong, so each of these assertions fails the moment the filter loosens.
# ---------------------------------------------------------------------------
print("\nPATHOLOGY AND LABORATORY MEDICINE")
pt = load_panel(PATHOLOGY)
check("panel is defined", pt.get("defined") is True)

# Checked over the WHOLE corpus of 3,314 award and tender titles, not over the 40
# rows the slice publishes. A false positive that happened to fall below the display
# cap would still be a broken filter, and a true positive that aged out of the top 40
# would still have to be caught. Both are cap-independent here on purpose.
_pt_rule = B.SPECIALITY_RULES[PATHOLOGY]
_pt_rx = B.compile_rule(_pt_rule)
_pt_th = B.load("tender-history.json")
_pt_ix = {k: i for i, k in enumerate(_pt_th["schema"])}
_pt_corpus = [r[_pt_ix["t"]] or "" for r in _pt_th["rows"]]
_pt_corpus += [(a.get("title") or "") for a in B.load("framework-awards.json")["awards"]]
pt_titles = [t for t in _pt_corpus if B.match_title(_pt_rx, t)]
pt_all = " || ".join(pt_titles)


def pt_absent(label, needle):
    check("excluded: %s" % label, needle.lower() not in pt_all.lower(), needle)


def pt_present(label, needle):
    check("present: %s" % label,
          any(needle.lower() in t.lower() for t in pt_titles), needle)


print("  the two frameworks, and only those two")
pt_fw = sorted(f["name"] for f in pt["frameworks"])
check("Laboratory Diagnostics, POCT and Pathology Managed Services is carried",
      any("Laboratory Diagnostics" in n for n in pt_fw))
check("Blood Collection Devices is carried", "Blood Collection Devices" in pt_fw)
check("exactly two frameworks", len(pt_fw) == 2, str(pt_fw))
# Digital Diagnostic Solutions carries a real laboratory strand but roughly twenty
# radiology and imaging-AI firms alongside it, with no supplier-by-lot split in this
# dataset. Specimen Cabinets is specimen RADIOGRAPHY: Hologic, Cirdan, MIS. Neither
# may be claimed here, and the rule says so rather than dropping them silently.
check("Digital Diagnostic Solutions is not claimed",
      not any("Digital Diagnostic" in n for n in pt_fw))
check("Specimen Cabinets is not claimed (it is specimen radiography)",
      not any("Specimen Cabinet" in n for n in pt_fw))
check("the defining framework's own supplier count is carried unaltered",
      any(f.get("supplierCount") == 122 for f in pt["frameworks"]))

print("  false positives that a loose filter WOULD publish")
# Veterinary and agricultural science buys the same PCR machines and slide scanners.
pt_absent("veterinary molecular biology kits", "Veterinary Molecular Biology")
pt_absent("bovine viral diarrhoea PCR on milk samples", "BVD PCR Test Kits")
pt_absent("Johne's disease ELISA (cattle)", "Johne")
pt_absent("AFBI's digital pathology slide scanner", "AFBI")
pt_absent("farm biosecurity boot swabs", "Boot Swab")
# Forensic science is a different discipline with no NHS market.
pt_absent("forensic DNA quantification PCR", "HUMAN QUANTIFICATION")
pt_absent("forensic QIAGEN extraction kits", "QIAGEN Extraction Kits")
# Research-only single-cell and spatial platforms are not diagnostics.
pt_absent("10x Genomics research platform", "10x Genomics")
pt_absent("Chromium single-cell instruments", "Chromium Instrument")
pt_absent("spatial and single-cell genomics platform", "spatial genomics")
pt_absent("generic molecular biology reagents", "Molecular Biology Reagents")
pt_absent("stored-trial-serum biomarker assay reagents", "Biomarker Assay")
pt_absent("cell culture media", "Tissue Culture Media")
# Water and environmental microbiology is not a patient sample.
pt_absent("IDEXX Colilert water coliform testing", "Coliert")
pt_absent("IDEXX Quanti-Tray water testing", "Quanti Tray")
pt_absent("water treatment maintenance", "Water Treatment Systems")
# Another speciality's instrument wearing this one's word.
pt_absent("ophthalmology visual field analysers", "Visual Field Analyser")
pt_absent("ophthalmology ocular analyser", "OCULAR ANALYSER")
pt_absent("diathermy (cut and coagulation)", "Electrosurgical Devices")
pt_absent("accelerator cryostats, not histology ones", "Cooling System")
pt_absent("point-of-care ULTRASOUND simulator", "PoCUS")
pt_absent("an endoscopy list, not a FIT laboratory", "General Endoscopy Services")
# Not a laboratory contract at all.
pt_absent("a locum pathologist engagement", "NHS Pathologist")
pt_absent("overseas AMR aid programme reagents", "Fleming Fund")
pt_absent("generic research label reagents", "Label Reagents")
# A GBP 15m tender too thin to place: CPV 33140000 medical consumables, one-sentence
# description, and "haemostatic" is the surgical word, not the laboratory one.
check("the NP646 haemostatic tender is not claimed as pathology",
      not any("Haemostatic" in (t.get("title") or "") for t in pt["openTenders"]))
# The feed's own loose `spec` field tags this row pathology on the word "collection".
pt_absent("breast milk collection sets (the feed's own false positive)", "Breast Pump")

print("  true positives that must survive")
pt_present("the pathology LIMS pre-market engagement", "Pathology IT LIMS")
pt_present("a histopathology cryostat", "Cryostat for Pathology")
pt_present("cellular pathology referrals", "Cellular Pathology Referrals")
pt_present("a microbiology managed service", "Microbiology Services Managed Service")
pt_present("culture media", "Culture Media")
pt_present("HLA typing (histocompatibility and immunogenetics)", "HLA")
pt_present("blood transfusion systems", "Blood Transfusion")
pt_present("blood gas analysers", "Blood Gas")
pt_present("immunohistochemistry", "Immunohistochemistry")
pt_present("newborn screening", "Newborn Screening")
pt_present("whole genome sequencing", "Genome Sequencing")
pt_present("blood collection devices", "Blood Collection")
pt_present("antimicrobial susceptibility and bacterial ID", "Bacteria")
pt_present("point-of-care testing", "Point of Care")

print("  the derived claims carry their rule and their limits (rules 14a, 14c)")
ptfw = (pt.get("rules") or {}).get("frameworks", "")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((pt.get("rules") or {}).get(k)))
check("coverage limit stated on the frameworks rule", "WHAT THE COUNTS" in ptfw)
check("122 suppliers are not presented as 122 competitors",
      "not 122 competitors" in ptfw)
check("the never-awarded Lot 7 is stated, not smoothed over",
      "Lot 7" in ptfw and "never awarded" in ptfw)
check("the three frameworks left to other pages are named, not dropped",
      "Digital Diagnostic Solutions" in ptfw and "Specimen Cabinets" in ptfw)
check("the two coronial histology buyers are declared rather than hidden",
      "Police and Crime Commissioner" in ptfw)
# Part IX is dressings, incontinence, stoma and elastic hosiery. A diagnostic test is
# not an appliance and is never dispensed against an FP10, so there is nothing to claim.
check("no Drug Tariff part is claimed for a laboratory speciality",
      pt.get("drugTariff") is None)
_pt_dt = (pt.get("rules") or {}).get("drugTariff", "")
check("the absence of a Drug Tariff part is explained, not silent",
      "No Drug Tariff part applies" in _pt_dt
      and "reaching for the nearest part" in _pt_dt)
# awardsMatched is post-deduplication (the two feeds overlap at the recent end), so
# it can only ever be smaller than the raw match count, never larger.
_pt_raw = len([t for t in _pt_corpus if B.match_title(_pt_rx, t)])
check("the published match count is not inflated above what the filter returns",
      pt["counts"]["awardsShown"] <= pt["counts"]["awardsMatched"] <= _pt_raw,
      "shown %d, matched %d, raw %d" % (
          pt["counts"]["awardsShown"], pt["counts"]["awardsMatched"], _pt_raw))
check("every published award title is one the rule actually accepts",
      all(B.match_title(_pt_rx, a.get("title") or "") for a in pt["awards"]))
check("licence notice carried", bool(pt.get("_notice", {}).get("owner")))
ptkb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", PATHOLOGY + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % ptkb, ptkb < 200)


# ---------------------------------------------------------------------------
# RADIOLOGY AND IMAGING (page 2915), added 09/09/2026.
#
# Two things make this patch easy to get wrong. First, its whole vocabulary is
# shared with physical science: X-ray means crystallography to a chemistry
# department, computed tomography means dimensional metrology to an engineering
# one, and "imaging" means a plate reader to a cell biologist. Second, it borders
# interventional radiology, and the two pages have to divide a single word.
# Every excluded case below is a REAL row that matched the include list and was
# read and rejected, so each assertion fails the moment the filter loosens.
# ---------------------------------------------------------------------------
print("\nRADIOLOGY AND IMAGING")
ri = load_panel(RADIOLOGY)
check("panel is defined", ri.get("defined") is True)

# Checked over the WHOLE corpus of 3,314 titles, not over the 40 rows the slice
# publishes, so a false positive below the display cap still fails the test.
_ri_rule = B.SPECIALITY_RULES[RADIOLOGY]
_ri_rx = B.compile_rule(_ri_rule)
_ri_th = B.load("tender-history.json")
_ri_ix = {k: i for i, k in enumerate(_ri_th["schema"])}
_ri_corpus = [r[_ri_ix["t"]] or "" for r in _ri_th["rows"]]
_ri_corpus += [(a.get("title") or "") for a in B.load("framework-awards.json")["awards"]]
ri_titles = [t for t in _ri_corpus if B.match_title(_ri_rx, t)]
ri_all = " || ".join(ri_titles)


def ri_absent(label, needle):
    check("excluded: %s" % label, needle.lower() not in ri_all.lower(), needle)


def ri_present(label, needle):
    check("present: %s" % label,
          any(needle.lower() in t.lower() for t in ri_titles), needle)


print("  the twelve frameworks the page's own Buying route names, and only those")
ri_fw = sorted(f["name"] for f in ri["frameworks"])
check("exactly twelve frameworks", len(ri_fw) == 12, str(ri_fw))
for _need in ["CT Scanners", "Magnetic Resonance Imaging Scanners", "Static X-Ray",
              "Mobile X-Ray", "Mammography Imaging", "Nuclear Medicine Imaging",
              "Bone Densitometers", "Ultrasound Scanners", "Fluoroscopy",
              "Mobile Image Intensifiers", "Contrast Injectors",
              "Digital Diagnostic Solutions"]:
    check("carried: %s" % _need, any(_need in n for n in ri_fw))
# The eleven modality briefs SHARE reference 2021/S 000-007768 with a twelfth brief
# that is not this speciality's. The page says outright that "the reference
# identifies a category, not an agreement", so the rule matches brief names. If
# anyone ever switches it to the reference, this is the assertion that fails.
check("Bladder Scanners is not claimed, though it shares the reference",
      not any("Bladder Scanner" in n for n in ri_fw))
# Claimed by interventional radiology and by vascular surgery, both correctly. This
# page's own Buying route section names twelve briefs and this is not one of them.
check("Angiography and Hybrid Theatres is left to the two pages that work in it",
      not any("Angiography" in n for n in ri_fw))
check("eleven of the twelve share the one reference",
      sum(1 for f in ri["frameworks"] if f.get("reference") == "2021/S 000-007768") == 11)
# Every one of the eleven states the same hard stop, both 24-month extensions already
# inside the 72-month term. If a refresh ever silently rolls one over, this fails.
check("all eleven modality briefs still end 31 March 2028",
      all(f.get("ends") == "31 March 2028" for f in ri["frameworks"]
          if f.get("reference") == "2021/S 000-007768"))

print("  false positives that a loose filter WOULD publish")
# Physical science buys X-ray instruments that are not imaging modalities.
ri_absent("X-ray powder diffractometers (crystallography)", "Powder Diffractometer")
ri_absent("single-crystal diffractometers at a chemistry school", "School of Chemistry")
ri_absent("Diamond Light Source's diffractometer", "8041768")
ri_absent("X-ray absorption/emission spectroscopy", "Spectroscopy")
ri_absent("industrial metrology CT", "Nikon Metrology")
ri_absent("an X-ray tomography microscope", "Tomography Microscope")
ri_absent("a materials-science mid-kV CT system", "mid-kV")
ri_absent("Kew's seed viability X-ray cabinet", "Seed viability")
ri_absent("National Museums Scotland's X-ray unit", "National Museums")
ri_absent("blood and laboratory X-ray irradiators", "Irradiators")
# Preclinical and veterinary imaging is a different machine and a different market.
ri_absent("a preclinical nanoScan PET/CT", "Preclinical PET")
ri_absent("a preclinical ultrasound imaging system", "Preclinical Ultrasound")
ri_absent("in vivo micro-ultrasound", "MICRO-ULTRASOUND")
ri_absent("MicroPET-MRI", "MicroPET")
ri_absent("micro CT scanners", "Micro CT")
ri_absent("standing modular equine MRI", "Equine")
ri_absent("functional ultrasound (a neuroscience research technique)", "Functional Ultrasound")
ri_absent("couch components for an MRI scanner being designed", "Scanner Design")
# Interventional radiology's ground, which this page does not claim.
ri_absent("interventional radiology products", "Interventional Radiology Products")
ri_absent("NHS Scotland's interventional radiology award", "NP68424")
ri_absent("mobile interventional radiology tables", "Interventional Radiology Tables")
ri_absent("interventional neuroradiology and thrombectomy", "Thrombectomy")
ri_absent("the IC/IR/INR framework award", "CARDIAC RHYTHM MANAGEMENT")
ri_absent("neuro vascular radiology consumables", "NEURO VASCULAR")
ri_absent("CT guidance for percutaneous instrument insertion", "percutaneous")
ri_absent("an MRI-guided laser ablation system", "Laser Ablation")
ri_absent("cath lab and pacing procedure packs", "Pacing Packs")
ri_absent("intravascular ultrasound (interventional cardiology)", "Intravascular Ultrasound")
# Other departments wearing this speciality's words.
ri_absent("dental X-ray systems", "Dental Xray")
ri_absent("panoramic dental X-ray", "Panoramic Xray")
ri_absent("digitising dental X-ray", "Digitise Dental")
ri_absent("Planmeca oral X-ray maintenance", "Planmeca")
ri_absent("ultrasound gel, bought on the consumables framework", "Ultrasound Gel")
ri_absent("therapeutic high-intensity focused ultrasound", "focused ultrasound")
ri_absent("FibroScan, which its own title calls non-imaging", "Non-Imaging")
ri_absent("a PoCUS training manikin", "PoCUS")
# MRI Software Ltd is a property-management vendor. This is the single reason the
# \bmri\b term needs a guard at all.
ri_absent("MRI Software's Planet housing product", "MRI Planet")
# Ministry of Defence platform support: NDT radiography and EOD screening.
ri_absent("MoD X-ray generators and film processors", "Film Processors")
ri_absent("EOD lightweight X-ray capability", "lightweight x-ray")
# Terms that were tried across the whole corpus and refused for being wrong more
# often than right. Each of these is a row a bare term WOULD have admitted.
ri_absent("an endoscopic imaging system (bare 'imaging')", "EVIS X1")
ri_absent("an ophthalmic imaging machine (bare 'imaging')", "Ophthalmic Imaging")
ri_absent("a cell imaging plate reader (bare 'imaging')", "Cell imaging")
ri_absent("a night vision imaging system for aircrew (bare 'imaging')", "Night Vision")
ri_absent("the ONYX software platform (bare 'imaging')", "ONYX imaging")
ri_absent("a research multimodal imaging platform", "Multimodal Imaging Platform")
ri_absent("teledermatoscopy (bare 'image transfer')", "dermatoscopes")
ri_absent("bowel screening kits (bare 'screening')", "Bowel Screening")
ri_absent("newborn screening kits (bare 'screening')", "Newborn Screening")
ri_absent("digital pathology slide scanners (bare 'scanner')", "Slide Scanner")
ri_absent("airport baggage scanners (bare 'scanner')", "baggage scanner")
ri_absent("bladder scanners (bare 'scanner')", "Bladder Scanner")
ri_absent("research scan time at a contract research organisation", "Invicro")
# Echocardiography is a cardiology test and the page's own DM01 rule says so.
ri_absent("an echocardiography insourcing contract", "Echocardiography Service")
ri_absent("an echocardiogram service at a CDC", "Echocardiogram")

print("  true positives that must survive any tightening")
ri_present("mobile digital radiography (Samsung GC85)", "GC85")
ri_present("outsourced radiology reporting", "Outsourced Radiology Reporting")
ri_present("insourcing radiographers, which is the workforce constraint",
           "Insourcing of Radiographers")
ri_present("teleradiology", "Teleradiology")
ri_present("a PACS interface integration project", "PACS")
ri_present("a radiology order communications solution", "Order Communications")
ri_present("relocatable MRI", "Relocatable MRI")
ri_present("mobile CT trailer maintenance", "MOBILE CT TRAILER")
ri_present("non-obstetric ultrasound insourcing (one of the DM01 five)",
           "Non-Obstetric Ultrasound")
ri_present("fluoroscopy suite enabling works", "Fluoroscopy Suite")
ri_present("digital mammography equipment", "Digital Mammography")
ri_present("SPECT/CT gamma camera", "Gamma Camera")
ri_present("nuclear medicine radiopharmacy", "Nuclear Medicine")
ri_present("PET dose dispensing", "PET Dose")
ri_present("contrast media and barium", "Barium")
ri_present("contrast injector consumables", "CONTRAST MEDIA INJECTION CONSUMABLES")
ri_present("X-ray protective wear", "Protective Wear")
ri_present("radiation protection services", "Radiation Protection")
ri_present("the Quality Standard for Imaging subscription", "Quality Standard for Imaging")
ri_present("NHS Scotland's multi-modality imaging framework", "Multi Modality Imaging")
# The plural was missed on the first draft: "Replacement of City X-Rays" matched
# nothing because the term was written x[- ]?ray with no optional s.
ri_present("a plural X-Rays title", "City X-Rays")

print("  the supplier list is the frameworks' own, and it corroborates the page")
# The page's Deep dive derives, independently of this panel and from the eleven
# product matrices rather than the supplier lists, that MIS Healthcare appears on
# more of the imaging briefs than GE or Siemens. Two separate routes to the same
# ordering is the check that the framework filter picked the right twelve.
_ri_by_name = {s["name"]: len(s["frameworks"]) for s in ri["suppliers"]}
_ri_mis = max((v for k, v in _ri_by_name.items() if "MIS Healthcare" in k), default=0)
_ri_ge = max((v for k, v in _ri_by_name.items() if k == "GE HealthCare"), default=0)
check("MIS Healthcare, a distributor, is on more of these frameworks than GE",
      _ri_mis > _ri_ge and _ri_mis >= 11, "MIS %d, GE %d" % (_ri_mis, _ri_ge))
check("the supplier list is not empty and not the whole directory",
      50 < ri["counts"]["suppliers"] < 200, str(ri["counts"]["suppliers"]))
# NHS Supply Chain writes "GE" and "Siemens" bare on the nuclear medicine brief. The
# registry refuses to resolve a bare two-letter token, and the builder flags rather
# than guessing. That refusal is correct and must not be papered over here.
check("unresolved supplier names are flagged, not silently merged",
      ri["counts"]["suppliersUnresolved"] >= 1)

print("  the derived claims carry their rule and their limits (rules 14a, 14c)")
rifw = (ri.get("rules") or {}).get("frameworks", "")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((ri.get("rules") or {}).get(k)))
check("coverage note carried on the frameworks rule", "COVERAGE" in rifw)
check("the shared reference is explained, not left to imply an agreement",
      "identifies a category and not an agreement" in rifw)
check("the brief that shares the reference and is not claimed is named",
      "Bladder Scanners" in rifw)
check("the devolved and regional routes are declared as absent, not hidden",
      "NP167/22" in rifw)
# Part IX is dressings, incontinence, stoma and elastic hosiery. A scanner is not an
# appliance and is never dispensed against an FP10, so there is nothing to claim.
check("no Drug Tariff part is claimed for an imaging speciality",
      ri.get("drugTariff") is None)
_ri_dt = (ri.get("rules") or {}).get("drugTariff", "")
check("the absence of a Drug Tariff part is explained, not silent",
      "No Drug Tariff part applies" in _ri_dt
      and "reaching for the nearest part" in _ri_dt)
# An empty open-tender list is the honest answer, not a gap to be padded.
check("no open tender is invented for an empty day",
      ri["counts"]["openTenders"] == len(ri["openTenders"]))
_ri_raw = len([t for t in _ri_corpus if B.match_title(_ri_rx, t)])
check("the published match count is not inflated above what the filter returns",
      ri["counts"]["awardsShown"] <= ri["counts"]["awardsMatched"] <= _ri_raw,
      "shown %d, matched %d, raw %d" % (
          ri["counts"]["awardsShown"], ri["counts"]["awardsMatched"], _ri_raw))
check("every published award title is one the rule actually accepts",
      all(B.match_title(_ri_rx, a.get("title") or "") for a in ri["awards"]))
check("licence notice carried", bool(ri.get("_notice", {}).get("owner")))
rikb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", RADIOLOGY + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % rikb, rikb < 200)



# ---------------------------------------------------------------------------
# RENAL (page 2917), added 09/09/2026.
#
# This is the first rule in the file with NO EXCLUSION LIST, and that is exactly
# why it needs the most testing. Nothing was excluded because nothing had to be:
# all 36 hits were read and every one is renal replacement therapy. The safety
# was bought in the include list instead, by refusing seven loose terms that
# every future editor will be tempted to add back. Each refusal below is a REAL
# row that the loose term would have admitted, so the assertion fails the moment
# someone widens the pattern.
# ---------------------------------------------------------------------------
print("\nRENAL")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), RENAL],
               check=True, capture_output=True)
rn = load_panel(RENAL)
check("panel is defined", rn.get("defined") is True)

# Checked over the WHOLE corpus of 3,314 titles, not over the 40 rows the slice
# publishes, so a false positive below the display cap still fails the test.
_rn_rule = B.SPECIALITY_RULES[RENAL]
_rn_rx = B.compile_rule(_rn_rule)
_rn_th = B.load("tender-history.json")
_rn_ix = {k: i for i, k in enumerate(_rn_th["schema"])}
_rn_corpus = [r[_rn_ix["t"]] or "" for r in _rn_th["rows"]]
_rn_corpus += [(a.get("title") or "") for a in B.load("framework-awards.json")["awards"]]
rn_titles = [t for t in _rn_corpus if B.match_title(_rn_rx, t)]

print("  the loose terms stay refused — each of these is a real row")
# bare "kidney" would admit nothing extra today, but a kidney dish is medical
# hollowware and a kidney stone is urology. bare "nephr*" would admit a
# nephrostomy, which is interventional radiology.
# bare "transplant": both hits in this data are corneal.
for bad in [
        "Supply of donated eye tissue used for corneal transplantation and other surgery",
        # Apheresis: NHSBT and the blood services, counted on the haematology page.
        "Plasmapheresis Collection Systems",
        "Support of existing NHSBT owned Multi-functional Apheresis Systems",
        "Spectra Optia Apheresis System x2",
        "Support of existing NHSBT Low Density Lipid (LDL) Removal Apheresis",
        "Lipoprotein Apheresis",
        # Water purification at NHS Blood and Transplant, bought from Veolia, who
        # IS on the renal framework. The supplier is not the test; the title is.
        "Supply & Maintenance of New and Existing Water Purification",
        # Multi-organ transplant logistics, not renal.
        "Framework Agreement for the Supply of Cold Static Perfusion Fluid UW Solution",
        "Supply of cold static perfusion fluid solution",
        "Framework Agreement for the Supply of Retrieval Packs",
        # A kidney research biobank at Cardiff University, not renal procurement.
        "NURTuRE-AKI biobank Custom tubing",
        # Transplant tissue typing belongs to pathology and laboratory medicine.
        "Supply of HLA Sequencing Systems",
        "HLA Typing for Immunogenetics",
        # Urology is not nephrology.
        "Urology Consumables",
        "Memokath stents for BCH Urology service",
        "Intravascular Lithotripsy Equipment and Consumables - 4307395",
        # Renal anaemia drugs are a medicines contract, not a device one.
        "NP40725 Erythropoietin Stimulating Agents",
        # Rows the feed's own `spec` field tags renal and which are not.
        "Supply of Micro Pastettes",
        "Consumable products used in Minimally Invasive Surgery",
        "Supply of Cryopreservation Freezing Bags",
        "Red Cell Washing System",
        "Genotyping Microarray Kits",
        "Supply of Copper Sulphate Solution",
]:
    check("never admitted: %s" % bad[:60], not B.match_title(_rn_rx, bad), "matched and should not")

print("  the genuine patch is admitted")
for good in [
        "Renal Replacement Consumables",
        "C453377 - Renal Dialysis machines x 4",
        "Purchase of Dialysis Machines",
        "Call-Off Order - FY26/27 - Home Peritoneal Dialysis - Hull",
        "Haemodialysis Machines & Consumables",
        "Hemodialysis consumables and spare parts for 5008H Cordiax Machines",
        "Continuous Renal Replacement Therapies (CRRT) Consumables",
        "Purchase of CRRT Consumables and Fluids",
        "ITU Haemofiltration",
        "Supply of Hemofiltration Equipment and Consumables",
        "Nephral 500ST Artificial Kidneys",
        "Nipro Fistula needles",
        "Supply of Renal Catheters and Fistula Packs",
        "Satellite Dialysis Services",
        "RRT Stockpile Call Off Terms - Fresenius",
]:
    check("admitted: %s" % good[:60], B.match_title(_rn_rx, good), "did not match and should")

# The one mixed contract that is admitted on its own words. It is kept because
# its title names Renal Equipment; if a future editor adds a "water treatment"
# exclusion to tidy the panel, this row goes and the coverage note lies.
check("the Belfast mixed water treatment contract is admitted on its own title",
      any("Decontamination and Renal Equipment" in t for t in rn_titles))

print("  the framework filter picks the one framework and no neighbours")
_rn_names = [f["name"] for f in rn["frameworks"]]
check("framework present: Renal Replacement Therapies",
      any(n.startswith("Renal Replacement Therapies") for n in _rn_names))
check("exactly one framework is claimed", len(_rn_names) == 1, str(_rn_names))
for other in ["Central Venous Catheters and Associated Products",
              "Urology and Bowel Management",
              "Male Intra-Urethral Catheter with Magnet Control",
              "Infusion Pumps and Administration Sets and Associated Products"]:
    check("another speciality's framework stays out: %s" % other, other not in _rn_names)

print("  the suppliers are the framework's own, resolved to one name per company")
# NHS Supply Chain lists 25 names; Nikkiso Belgium BV and Nikkiso Europe GmbH are
# one company. Published raw that is a count inflated by one and a rep chasing two
# distributors that are the same firm.
_rn_nik = [s for s in rn["suppliers"] if "Nikkiso" in s["name"]]
check("Nikkiso appears exactly once", len(_rn_nik) == 1, str([s["name"] for s in _rn_nik]))
check("Nikkiso shows both NHSSC spellings",
      len(_rn_nik) == 1 and len(_rn_nik[0]["variants"]) == 2, str(_rn_nik))
check("supplier count is the framework's 25 names less the one merge",
      rn["counts"]["suppliers"] == 24, str(rn["counts"]["suppliers"]))
check("unresolved supplier names are flagged, not silently merged",
      rn["counts"]["suppliersUnresolved"] >= 1)

print("  the derived claims carry their rule and their limits (rules 14a, 14c)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((rn.get("rules") or {}).get(k)))
_rn_aw = (rn.get("rules") or {}).get("awards", "")
# The published wording must say there is no exclusion list rather than printing
# a regex that cannot match and claiming it caught real false positives.
check("the absent exclusion list is declared, not faked",
      "NO EXCLUSION LIST IS APPLIED" in _rn_aw)
check("no never-matching regex is published as if it were an exclusion list",
      "(?!x)x" not in _rn_aw)
# The coverage note is appended to the frameworks and suppliers rules, which is
# where a reader judging the supplier list will be looking.
_rn_note = (rn.get("rules") or {}).get("frameworks", "")
check("the CRRT overlap with critical care is declared, not hidden",
      "CONTINUOUS RENAL REPLACEMENT THERAPY IS CLAIMED BY THIS PAGE" in _rn_note)
check("Baxter and Vantive are declared as one incumbent, not two",
      "Read them as one incumbent, not two." in _rn_note)
check("the supplier-count difference is explained on the suppliers rule",
      "Nikkiso" in (rn.get("rules") or {}).get("suppliers", ""))
# Part IX is dressings, incontinence, stoma and elastic hosiery. Home dialysis
# fluids are delivered under the trust's own contract, not dispensed on an FP10.
check("no Drug Tariff part is claimed for renal", rn.get("drugTariff") is None)
_rn_dt = (rn.get("rules") or {}).get("drugTariff", "")
check("the absence of a Drug Tariff part is explained, not silent",
      "No Drug Tariff part applies" in _rn_dt
      and "reaching for the nearest part" in _rn_dt)
check("no open tender is invented for an empty day",
      rn["counts"]["openTenders"] == len(rn["openTenders"]))
_rn_raw = len([t for t in _rn_corpus if B.match_title(_rn_rx, t)])
check("the published match count is not inflated above what the filter returns",
      rn["counts"]["awardsShown"] <= rn["counts"]["awardsMatched"] <= _rn_raw,
      "shown %d, matched %d, raw %d" % (
          rn["counts"]["awardsShown"], rn["counts"]["awardsMatched"], _rn_raw))
check("every published award title is one the rule actually accepts",
      all(B.match_title(_rn_rx, a.get("title") or "") for a in rn["awards"]))
check("licence notice carried", bool(rn.get("_notice", {}).get("owner")))
_rn_kb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", RENAL + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % _rn_kb, _rn_kb < 200)

# ---------------------------------------------------------------------------
# HAEMATOLOGY AND PATIENT BLOOD MANAGEMENT (page 2809), added 09/09/2026.
#
# The word "blood" is the most dangerous single token in the whole dataset: it
# appears on blood pressure cuffs, blood glucose strips, blood gas analysers, a
# mixed pharmacy medicines basket, dried blood spot screening, a molecular
# extraction platform, a clozapine monitoring service and a courier contract for
# carrying blood tests. Not one of those is this speciality. Every case below is
# a REAL row that a widened pattern would admit, so the assertions fail the
# moment somebody reaches for the bare word.
# ---------------------------------------------------------------------------
print("\nHAEMATOLOGY AND PATIENT BLOOD MANAGEMENT")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), HAEM],
               check=True, capture_output=True)
hb = load_panel(HAEM)
check("panel is defined", hb.get("defined") is True)

_hb_rule = B.SPECIALITY_RULES[HAEM]
_hb_rx = B.compile_rule(_hb_rule)
_hb_th = B.load("tender-history.json")
_hb_ix = {k: i for i, k in enumerate(_hb_th["schema"])}
_hb_corpus = [r[_hb_ix["t"]] or "" for r in _hb_th["rows"]]
_hb_corpus += [(a.get("title") or "") for a in B.load("framework-awards.json")["awards"]]

print("  bare 'blood' stays refused — every one of these is a real row")
for bad in [
        "Blood Pressure Cuffs and Support Products",
        "PROVISION OF BLOOD GLUCOSE METERS",
        "CLI-STA-52156 Professional Blood Glucose Testing Strips, Consumables and QC Material",
        "Supply of Replacement Blood Gas Analysers and Consumables",
        "Blood Gas Managed Service for Betsi Cadwaladr University Health Board",
        "Gastrointestinal, Endocrine, Nutrition & Blood Medicines",
        "Dried Blood Spot Testing",
        "Blood Extraction Platform",
        "Clozapine Tablets and Blood Testing Service",
        "Provision of Taxi, Courier, parcel and Transport of Human Tissues & Blood  Tests",
        "Blood Culture pathway- Health economic analysis",
        # Two titles too bare to call either way. Refusing them is the point of
        # rule 14: publishing nothing beats publishing a guess.
        "Blood Analyser",
        "Blood Kiosks",
]:
    check("never admitted: %s" % bad[:62], not B.match_title(_hb_rx, bad), "matched and should not")

print("  the other loose terms stay refused — also real rows")
for bad in [
        # bare "plasma": analytical chemistry at a university.
        "Inductively Coupled Plasma Optical Emission Spectrometer (ICP-OES)",
        # bare "coagulation" and bare "haemostat": diathermy, and an open notice
        # that cannot be told from surgical haemostats on its title.
        "Purchase of Electrosurgical Devices (Cut & Coagulation, Uterine Ablation)",
        "NP646 Haemostatic & Coagulation Products",
        # Pharmacological VTE prophylaxis is pharmacy's, in the page's own words.
        "Heparins & Anticoagulants",
        "NHS Framework Agreement for the Supply of Direct Oral Anticoagulant (DOAC) "
        "Medicines for the NHS in England",
        # bare "thromb*" and bare "INR". In the first title the letters INR mean
        # Interventional NeuroRadiology, not International Normalised Ratio.
        "INR and Thrombectomy Consumables",
        "Interventional Neuro Radiology and Thrombectomy Consumables",
        # bare "perfusion": kidney and multi-organ transplant preservation, which
        # the renal rule refuses for the same reason, then the cardiac bypass and
        # ECMO rows, which are the cardiology and cardiac surgery page's.
        "Contract Award Notice for the Provision of LifePort Perfusion Consumables",
        "Framework Agreement for the Supply of Cold Static Perfusion Fluid UW Solution",
        "NHS Golden Jubilee Cardiac Perfusion Consumables",
        "Cardiopulmonary Bypass Oxygenators with Customised Tubing Pack [2339172]",
        "Blood Cardioplegia Sets",
        "Purchase of ECMO Trolley",
        "Maintenance Perfusion Heart and Lung Machine",
        "Monitoring devices for continuous measurement of blood parameters during "
        "extracorporeal circulation",
        "Maintenance - CDI 550 blood parameter monitors - PW004",
        # bare "tourniquet": surgical limb tourniquets, not the phlebotomy kind.
        "The Supply of Multi-Use Pneumatic Tourniquet Devices",
        "Purchase of Orthopaedic Power Tools, Bone Cement, Mixing Systems, "
        "Pulse Lavage & Tourniquets",
        # bare "stem cell": haemato-oncology, which the page routes to Oncology
        # and SACT. The donation forms below still admit the blood service rows.
        "Stem Cell and Immunotherapy Services",
]:
    check("never admitted: %s" % bad[:62], not B.match_title(_hb_rx, bad), "matched and should not")

print("  the one exclusion pattern earns its place")
# The single entry in `exclude`. Ophthalmic viscoelastic device — the gel used in
# cataract surgery — shares its whole name with viscoelastic haemostatic testing.
# Viscoelastic testing is one of the two things the page says to lead with, so the
# include term stays and this row is taken back out.
check("never admitted: Intraocular Lenses, Viscoelastics & Phaco machines",
      not B.match_title(_hb_rx, "Intraocular Lenses, Viscoelastics & Phaco machines"))
check("the exclusion list is a real one, not a never-matching placeholder",
      bool(_hb_rule["exclude"]) and "(?!x)x" not in (_hb_rule["exclude"] or ""))

print("  the genuine patch is admitted")
for good in [
        # Patient blood management: cell salvage and viscoelastic testing.
        "Suction Consumables, Wound Drainage, Autologous Blood Systems and Related Accessories",
        "HEY/17/177 CELL SALVAGE EQUIPMENT AND CONSUMABLES",
        "The Supply and Support of TEG-6 Viscoelastic Monitors - VTN",
        "WSFT - Pathology - Hemostasis Management TEG 65 Analyser",
        # Pathway two: VTE prevention, mechanical prophylaxis.
        "Anti-Embolism Stockings",
        "Intermittent Pneumatic Compression",
        # The transfusion pathway and its laboratory.
        "Maintenance of Blood Transfusion Systems",
        "Red Cell Reagents",
        "Red Cell Washing System",
        "Donation and Patient Testing - Automated Red Cell Immunohaematology",
        "Automated Immunohaematology System",
        "Blood Collection NPM Agreement",
        "Sampling Device for the Bacterial Screening of Platelets [3983168]",
        "International Blood Pack 1",
        # The -pheresis family, which the renal rule sends here by name. The
        # pattern is \w*pheresis\w* precisely so plasmapheresis and photopheresis
        # cannot fall through a leading word boundary.
        "Plasmapheresis Collection Systems",
        "Support of existing NHSBT owned Extracorporeal Photopheresis (ECP) Systems",
        # Component manufacture at the blood services.
        "UK Domestic Plasma Fractionation Service",
        "UK Derived & Manufactured Dried Plasma Component",
        "WBS-FTS-63787 Replacement of Rapid Plasma/Blast Freezer Equipment",
        "Supply of Cord Blood Collection Systems",
        # Donor work. NOTE THE TYPO: the Welsh Blood Service notice really is
        # spelled "Doner". The pattern is `bone marrow don\w*` for that reason and
        # narrowing it to `donor` silently drops the row.
        "Welsh Blood Service Bone Marrow Doner Service",
        "2526-087-STA-WBS Medical Evaluation of Prospective Stem Cell Donors",
        # Inherited bleeding and haemoglobin disorders. No other Hub page holds them.
        "Sickle Cell and Thalassemia lab clinical support 2027",
        "NHS Framework - Blood Disorders including Haemophilia A and B - July 2024",
        "NHS National Framework Agreement for the Supply of Recombinant Von Willebrand Factor",
        # Rapid and pressurised infusion.
        "Rapid Infuser Blood/IV Infusion Pump",
]:
    check("admitted: %s" % good[:62], B.match_title(_hb_rx, good), "did not match and should")

print("  the framework filter claims two of the page's seven and no more")
_hb_names = [f["name"] for f in hb["frameworks"]]
check("exactly two frameworks are claimed", len(_hb_names) == 2, str(_hb_names))
for want in ["Blood Collection Devices", "Pressure Infusers and Associated Products"]:
    check("framework present: %s" % want, want in _hb_names)
# The three the page names that are other pages' frameworks. Claiming any of them
# whole would put 122 genomics and digital pathology firms, 23 compression hosiery
# firms, or 9 cardiac bypass firms under a haematology Suppliers heading.
for other in ["Laboratory Diagnostics, Point of Care Testing and Pathology Managed Services",
              "Vascular Therapy and Associated Products",
              "Perfusion Devices, Consumables and Associated Equipment",
              "Central Venous Catheters and Associated Products",
              "Renal Replacement Therapies Services, Technologies and Consumables"]:
    check("another speciality's framework stays out: %s" % other[:56], other not in _hb_names)
# The two of the seven that are absent from the dataset entirely. If either is
# ever added to frameworks.json this fails, which is the prompt to claim it.
_hb_all_fw = [f.get("name") or "" for f in B.load("frameworks.json")["frameworks"]]
for missing in ["Suction", "Blood Draw Tools"]:
    check("still absent from frameworks.json, and the note says so: %s" % missing,
          not any(missing in n for n in _hb_all_fw))

print("  the suppliers are the frameworks' own, resolved to one name per company")
check("supplier count matches the two frameworks' 19 + 8 names",
      hb["counts"]["suppliers"] == 26, str(hb["counts"]["suppliers"]))
check("no supplier name is left unresolved",
      hb["counts"]["suppliersUnresolved"] == 0, str(hb["counts"]["suppliersUnresolved"]))
# Reflex Medical is on both frameworks under two spellings and is correctly one row.
_hb_reflex = [s for s in hb["suppliers"] if "Reflex" in s["name"]]
check("Reflex Medical appears exactly once across both frameworks",
      len(_hb_reflex) == 1, str([s["name"] for s in _hb_reflex]))
check("Reflex Medical is shown on both frameworks",
      len(_hb_reflex) == 1 and len(_hb_reflex[0]["frameworks"]) == 2)
_hb_note = (hb.get("rules") or {}).get("frameworks", "")
# GBUK is held as TWO records in supplier-seed.json — NHS Supply Chain writes
# "GBUK Ltd" on one framework and "GB UK Ltd" on the other, and no company by the
# second name exists on the active Companies House register. Until the seed is
# merged the panel must say so out loud; after it is merged there will be one row
# and the declaration is no longer needed. Both states pass, silence does not.
_hb_gbuk = [s for s in hb["suppliers"] if s["name"].upper().replace(" ", "").startswith("GBUK")]
check("GBUK is either merged to one row or declared as two",
      len(_hb_gbuk) == 1 or "ONE COMPANY APPEARS TWICE" in _hb_note,
      str([s["name"] for s in _hb_gbuk]))

print("  the derived claims carry their rule and their limits (rules 14a, 14c)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((hb.get("rules") or {}).get(k)))
check("the two frameworks claimed out of seven are explained, not hidden",
      "the Frameworks tab below claims two of them" in _hb_note)
check("the two frameworks missing from the dataset are declared",
      "TWO OF THE SEVEN ARE NOT IN THE HUB'S FRAMEWORK DATASET AT ALL" in _hb_note)
check("the blood component monopoly is declared, since no panel can ever show it",
      "BLOOD COMPONENTS ARE NOT PROCURED AT ALL" in _hb_note)
check("the wider award scope is declared against the page's two pathways",
      "THE AWARDS LIST IS WIDER THAN THE TWO CLINICAL PATHWAYS" in _hb_note)
# Part IX is dressings and elastic hosiery, incontinence and stoma — community
# FP10 appliances. Blood components are invoiced by NHSBT, cell salvage is capital,
# and hospital anti-embolism stockings are issued on the ward, not prescribed.
check("no Drug Tariff part is claimed for haematology", hb.get("drugTariff") is None)
_hb_dt = (hb.get("rules") or {}).get("drugTariff", "")
check("the absence of a Drug Tariff part is explained, not silent",
      "No Drug Tariff part applies" in _hb_dt and "reaching for the nearest part" in _hb_dt)
# Every CPV prefix claimed must actually fire on a real notice. A family listed
# from the code book and never seen corroborates nothing.
_hb_fa = B.load("framework-awards.json")["awards"]
for _pfx in _hb_rule["cpv"]:
    _fires = any(
        B.match_title(_hb_rx, a.get("title") or "")
        and any(str(c).startswith(_pfx) for c in (a.get("cpv") or []))
        for a in _hb_fa)
    check("CPV prefix %s fires on a real notice" % _pfx, _fires)
check("no open tender is invented for an empty day",
      hb["counts"]["openTenders"] == len(hb["openTenders"]))
_hb_raw = len([t for t in _hb_corpus if B.match_title(_hb_rx, t)])
check("the published match count is not inflated above what the filter returns",
      hb["counts"]["awardsShown"] <= hb["counts"]["awardsMatched"] <= _hb_raw,
      "shown %d, matched %d, raw %d" % (
          hb["counts"]["awardsShown"], hb["counts"]["awardsMatched"], _hb_raw))
check("every published award title is one the rule actually accepts",
      all(B.match_title(_hb_rx, a.get("title") or "") for a in hb["awards"]))
check("licence notice carried", bool(hb.get("_notice", {}).get("owner")))
_hb_kb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", HAEM + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % _hb_kb, _hb_kb < 200)


# ---------------------------------------------------------------------------
# MATERNITY AND NEONATAL. Two pathways bought separately, and a patch where the
# ordinary words are the dangerous ones: breast, milk, infant, baby, incubator,
# fetal, labour, delivery, cord. Every case below is a REAL row that a widened
# pattern would admit or a real row a narrowed one would lose.
# ---------------------------------------------------------------------------
print("\nMATERNITY AND NEONATAL")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), MATERNITY],
               check=True, capture_output=True)
mn = load_panel(MATERNITY)
check("panel is defined", mn.get("defined") is True)

_mn_rule = B.SPECIALITY_RULES[MATERNITY]
_mn_rx = B.compile_rule(_mn_rule)
_mn_th = B.load("tender-history.json")
_mn_ix = {k: i for i, k in enumerate(_mn_th["schema"])}
_mn_corpus = [r[_mn_ix["t"]] or "" for r in _mn_th["rows"]]
_mn_corpus += [(a.get("title") or "") for a in B.load("framework-awards.json")["awards"]]

print("  the exclusion list earns its place — 'non-obstetric' means the opposite")
# The word "obstetric" here is defining what the contract EXCLUDES. Four real rows,
# two buyers. No narrowing of the include list can reach this; the negation has to
# be matched.
for bad in [
        "Non-Obstetrical Ultrasound – East Surrey – CAN",
        "Non-Obstetric Ultrasound Service – East Surrey – CAN",
        "Insourced Non-Obstetric Ultrasound Services YSTH",
        "PSR Urgent Award for Insourced Non-Obstetric Ultrasound Services YSTH",
]:
    check("never admitted: %s" % bad[:62], not B.match_title(_mn_rx, bad))
check("the exclusion list is a real one, not a never-matching placeholder",
      bool(_mn_rule["exclude"]) and "(?!x)x" not in (_mn_rule["exclude"] or ""))

print("  the ordinary words stay refused — every one of these is a real row")
for bad in [
        # bare "breast" — eleven rows, all oncology, plastics or radiology.
        "Philips Epiq Elite Diagnostic Ultrasound for Breast Clinic CHH",
        "Breast Biopsy Needle NPM",
        "HEY/18/161 BREAST IMPLANTS",
        "CLI-OJEU-45806 SURGICALLY IMPLANTED BREAST PROSTHESES",
        "External Breast Prosthesis [4233683]",
        "Provision of Oncotype DX Breast Recurrence ScoreTM Assay",
        "Maintenance of Mobile Breast Screening Tailers and Mobile MRI Trailers",
        "Insourcing of Breast Radiology Services",
        "Insourced Breast Surgery Imaging and OP Services - USC (HHP)",
        "Breast Service Support (insourced capacity)",
        # bare "milk" — hospital catering and cattle.
        "Provision of Milk & Bread - University Hospitals of Morecambe Bay",
        "BVD PCR Test Kits for Serum and Milk Samples",
        # bare "infant" and bare "baby" — council services and welfare schemes.
        "Parent Infant Psychotherapy to families in East Sussex",
        "Market Engagement Event – Brent Parent and Infant Relationship Service (PAIRS)",
        "Supply & Distribution of Baby Packs  (1)",
        "Baby Bundles",
        # bare "incubator" — laboratory and blood bank, every one.
        "Platelet Incubator for CGH",
        "Supply & Maintenance of Platelet Agitator and Incubator equipment",
        "BINDER CB170 CO₂ incubators",
        # bare "fetal"/"foetal" — the standard cell culture reagent.
        "Supply of BVD-free Foetal Bovine Serum to APHA",
        # bare "labour" — work, not childbirth.
        "YAS 58 2026_27 (DA Non FW) Various Ortus Parts & Labour",
        # bare "uterine" — gynaecology, which has its own page.
        "Purchase of Electrosurgical Devices (Cut & Coagulation, Uterine Ablation)",
        "Endometrial Ablation Devices and Uterine Tissue Removal Systems",
        # bare "sanitary" / "period" — council welfare schemes.
        "Provision of Sanitary Products",
        "Period Dignity Programme – Supply of Sanitary / Feminine Care Products",
        # bare "cord" — neuromodulation, and cord blood banking which is haematology's.
        "Neuromodulation/Spinal Cord Stimulators, Intrathecal Drug Pumps, Radiofrequency Ablation and Associated Products",
        "Supply of Cord Blood Collection Systems",
        # "blood spot" — adult virology.
        "Dried Blood Spot Testing",
        # anaesthesia, gynaecology, radiology and net zero.
        "Mobile Entonox Destruction Devices",
        "Spinal, Epidural and Associated Products",
        "Epidural Pumps",
        "Vaginal Speculum",
        "ESNEFT3156 Purchase of Ultrasound Scanners",
        "PROJ007278_Replacement of Trans-Rectal Ultrasound Scanner",
        # termination of pregnancy is the gynaecology and women's health page's.
        "Complex Termination of Pregnancy (CTOP) Services across the South East",
]:
    check("never admitted: %s" % bad[:62], not B.match_title(_mn_rx, bad))

print("  the genuine patch is admitted")
for good in [
        # The maternity pathway.
        "Lease_PROJ004570_Antenatal Ultrasound Scanner",
        "Supply of Surgical Positioning Table and Leg Positioning Accessories for Maternity and Gynaecology Procedures",
        "NGH - Maternity Bereavement Suite",
        "Button Hole CTG Belts [4806692]",
        "Fetal Cushions [3299279]",
        "Obstetrics and Vinyl Pessaries",
        "Pessaries [4186866]",
        "Preliminary Market Engagement Questionnaire - Pessaries",
        "0P002079 - Colposcope - Capital - Central Delivery Suite RSCH",
        # The neonatal pathway.
        "Purchase of Neonatal Resus Systems",
        "ESNEFT3075 Purchase of Neonatal Imaging System",
        "NP14220 Neonatal and Paediatric Tracheostomy Tubes",
        "Neonatal Equipment, Adult, Paediatric & Neonatal Phototherapy Devices and Associated Accessories & Services",
        "Purchase of Baby Warmers with Resuscitation",
        "Maintenance of Infant Ventilators",
        "Spare Parts for Draeger Isolette Incubators [3995346]",
        "Newborn Transport Harnesses for London Ambulance",
        "Purchase of BiliCare Transcutaneous Bilirubin Meter & Case",
        # Feeding, expression and milk banking.
        "Breast Pumps and Breast Milk Collection Sets [5180689]",
        "Sterile Milk Bottles [ 4692898 ]",
        "DHSC: GPH: Mothers Living with HIV Formula Milk Funding Scheme 2027",
        # Newborn screening.
        "SMA Newborn Screening Kits",
        "Newborn Bloodspot Cards",
        "Procurement of Test Kits for Newborn Screening of Cystic Fibrosis (CF), Congenital Hypothyroidism (CHT) and the Maintena",
]:
    check("admitted: %s" % good[:62], B.match_title(_mn_rx, good), "did not match and should")

# THE UNDERSCORE CASE, kept as its own assertion because it is the one that would
# be lost silently. An underscore is a word character, so \b would not fire before
# "Antenatal" in "Lease_PROJ004570_Antenatal Ultrasound Scanner" and the only
# antenatal scanner award in the data would vanish with no error anywhere.
check("a word boundary is not \\b: punctuation-glued titles still match",
      B.match_title(_mn_rx, "Lease_PROJ004570_Antenatal Ultrasound Scanner")
      and B.match_title(_mn_rx, "X_NEONATAL_KIT")
      and not B.match_title(_mn_rx, "PRENEONATALX"))

print("  the framework filter claims the page's four and no more")
_mn_names = [f["name"] for f in mn["frameworks"]]
check("exactly four frameworks are claimed", len(_mn_names) == 4, str(_mn_names))
for want in ["Maternity, Obstetrics, Gynaecology and Sexual Health Products",
             "Obstetrics and Vinyl Pessaries",
             "Infant Feeding and Accessories",
             "Anaesthesia Machines, Ventilators, Neonatal Equipment and Phototherapy Systems, "
             "Related Accessories and Services"]:
    check("framework present: %s" % want[:56], want in _mn_names)
for other in ["External Breast Prosthesis and Chest Support",
              "Non Invasive Ventilation, Sleep Therapy, CPAP and Sleep Monitoring Diagnostics"]:
    check("another speciality's framework stays out: %s" % other[:52], other not in _mn_names)

print("  the six delisted companies are OUT of the supplier list (root rule 13)")
# frameworks.json holds 57 names for the maternity framework and flags the count as
# UNVERIFIED. NHS Supply Chain's brief prints 51 suppliers and then six more under
# "The following suppliers are being delisted at the start of the new framework".
# 57 = 51 + 6. Published raw it would name six companies as competitors on a
# framework they have left.
_mn_mat = [f for f in mn["frameworks"] if f["name"].startswith("Maternity, Obstetrics")][0]
check("the maternity framework shows 51 suppliers, not 57",
      _mn_mat["supplierCount"] == 51 and len(_mn_mat["suppliers"]) == 51,
      "count %s, listed %d" % (_mn_mat["supplierCount"], len(_mn_mat["suppliers"])))
_mn_delisted = ["Bray Group Limited", "Cardiac Services UK Ltd", "Durbin Plc",
                "Medichill UK Ltd", "Valley Northern", "Viomedex Ltd"]
# A delisted name must not reach the Suppliers tab AS A SUPPLIER ON THE MATERNITY
# AGREEMENT. Bray is the case that makes the distinction matter: Bray Group Ltd
# (Bray Healthcare) genuinely holds Obstetrics and Vinyl Pessaries, so it belongs
# on the tab — just never against the framework it was delisted from.
_mn_on_maternity = [
    s for s in mn["suppliers"]
    if any(f.startswith("Maternity, Obstetrics") for f in s["frameworks"])]
_mn_mat_names = " | ".join(
    s["name"] + " " + " ".join(s["variants"]) for s in _mn_on_maternity)
for gone in _mn_delisted:
    check("delisted, so not a supplier: %s" % gone, gone not in _mn_mat["suppliers"])
    check("delisted, so not credited to that framework: %s" % gone,
          gone not in _mn_mat_names)
check("the maternity agreement credits exactly its 51 current suppliers",
      len(_mn_on_maternity) == 51, "got %d" % len(_mn_on_maternity))
check("the six are recorded against the framework, not dropped",
      sorted(_mn_mat["delisted"] or []) == sorted(_mn_delisted), str(_mn_mat["delisted"]))
# Bray holds the pessaries agreement under a different spelling and must survive.
check("Bray survives on the pessaries agreement it does hold",
      any("Bray" in s["name"] for s in mn["suppliers"]))
# If the crawler is ever fixed upstream, the correction must FAIL rather than
# silently do nothing. Replay it against a framework record that no longer carries
# the delisted names.
_mn_fake = {"frameworks": [dict(_mn_mat, suppliers=["Argon Medical Devices UK Ltd"],
                                name="Maternity, Obstetrics, Gynaecology and Sexual Health Products")]}
try:
    B.build_frameworks(_mn_rx, _mn_rule, _mn_fake)
    check("the delisted correction fails loudly when the data changes under it", False,
          "it returned quietly")
except SystemExit:
    check("the delisted correction fails loudly when the data changes under it", True)

print("  the derived claims carry their rule and their limits (rules 14a, 14c)")
for k in ["frameworks", "suppliers", "awards", "openTenders", "drugTariff"]:
    check("rule stated: %s" % k, bool((mn.get("rules") or {}).get(k)))
_mn_note = (mn.get("rules") or {}).get("frameworks", "")
check("the lot limits on two of the four agreements are declared",
      "COVERAGE LIMIT, STATED RATHER THAN HIDDEN" in _mn_note
      and "only Lot 3 is neonatal equipment" in _mn_note)
check("the delisted correction is declared to the reader",
      "SIX DELISTED COMPANIES HAVE BEEN TAKEN OUT" in _mn_note)
check("the brief's own contradictory supplier count is declared",
      "THE SUPPLIER COUNT ON THAT BRIEF DOES NOT ADD UP" in _mn_note)
check("the loss of the neonatal agreement is declared",
      "THE NEONATAL CATEGORY NO LONGER HAS AN AGREEMENT OF ITS OWN" in _mn_note)
check("the two mixed contracts are declared, not hidden",
      "TWO AWARDS BELOW ARE MIXED CONTRACTS" in _mn_note)
check("what this page does NOT claim is stated",
      "Gynaecology, sexual health, fertility and termination of pregnancy are NOT counted" in _mn_note)

# Part IX is dressings and elastic hosiery, incontinence and stoma. Nothing on this
# patch is dispensed against an FP10.
check("no Drug Tariff part is claimed for maternity and neonatal", mn.get("drugTariff") is None)
_mn_dt = (mn.get("rules") or {}).get("drugTariff", "")
check("the absence of a Drug Tariff part is explained, not silent",
      "No Drug Tariff part applies" in _mn_dt and "reaching for the nearest part" in _mn_dt)

# Every CPV prefix claimed must actually fire on a real notice.
_mn_fa = B.load("framework-awards.json")["awards"]
for _pfx in _mn_rule["cpv"]:
    _fires = any(
        B.match_title(_mn_rx, a.get("title") or "")
        and any(str(c).startswith(_pfx) for c in (a.get("cpv") or []))
        for a in _mn_fa)
    check("CPV prefix %s fires on a real notice" % _pfx, _fires)
# ...and CPV must never admit on its own. 33750 also sits on "Baby Bundles", which
# the title filter refuses.
check("CPV cannot admit a notice the title filter refuses",
      not any(a.get("title") == "Baby Bundles" for a in mn["awards"]))

check("no open tender is invented for an empty day",
      mn["counts"]["openTenders"] == len(mn["openTenders"]))
_mn_raw = len([t for t in _mn_corpus if B.match_title(_mn_rx, t)])
check("the published match count is not inflated above what the filter returns",
      mn["counts"]["awardsShown"] <= mn["counts"]["awardsMatched"] <= _mn_raw,
      "shown %d, matched %d, raw %d" % (
          mn["counts"]["awardsShown"], mn["counts"]["awardsMatched"], _mn_raw))
check("every published award title is one the rule actually accepts",
      all(B.match_title(_mn_rx, a.get("title") or "") for a in mn["awards"]))
check("licence notice carried", bool(mn.get("_notice", {}).get("owner")))
_mn_kb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", MATERNITY + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % _mn_kb, _mn_kb < 200)


# ---------------------------------------------------------------------------
# GYNAECOLOGY AND WOMEN'S HEALTH. Two pathways, NG88 and NG123, and a patch whose
# danger is not one loose word but SUBSTRINGS: "uter" lives inside Computer and
# Outer, "ovar" inside Novartis, "IUS" inside Fresenius and Fabius, "HRT" inside a
# reference number. It is also the first speciality whose Drug Tariff lines are a
# SLICE of a part rather than the part, so there is an invariant for that too.
# ---------------------------------------------------------------------------
print("\nGYNAECOLOGY AND WOMEN'S HEALTH")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), GYNAE],
               check=True, capture_output=True)
gy = load_panel(GYNAE)
check("panel is defined", gy.get("defined") is True)

_gy_rule = B.SPECIALITY_RULES[GYNAE]
_gy_rx = B.compile_rule(_gy_rule)
_gy_th = B.load("tender-history.json")
_gy_ix = {k: i for i, k in enumerate(_gy_th["schema"])}
_gy_corpus = [r[_gy_ix["t"]] or "" for r in _gy_th["rows"]]
_gy_corpus += [(a.get("title") or "") for a in B.load("framework-awards.json")["awards"]]

print("  the substring traps stay shut — every one of these is a real row")
for bad in [
        # "uter" inside Computer and Outer. Only uterine/uterus/intrauterine are used.
        "Motorized Patient Couch and Plastic Composite Outer Covers for a new MRI Scanner Design",
        "Procurement of a Computer Aided Facilities Management (CAFM) System",
        # "ovar" inside Novartis. Only ovarian/ovary/ovaries are used.
        "NOVARTIS PHARMACEUTICALS UK LTD (WT) - WT2024-11, WT2024-12, WT2024-13 - RIBOCICLIB [KISQALI]",
        "Procurement of Midostaurin from Novartis UK",
        # "IUS" inside Fresenius, Excelsius and Fabius. Only LNG-IUS is used.
        "C461962 - W148888 - Waiver for the Supply of Fresenius Spare Parts",
        "ExcelsiusGPS robot with 5 year servicing",
        "The Support of Fabius tiro anaesthesia apparatus",
        "RRT Stockpile Call Off Terms - Fresenius",
        # "HRT" inside a contract reference number.
        "CHRT503-2021-22 -DS/DN - Greater Manchester Pharmacy Logistics Supply Chain Service",
        # "coil" is an MRI part here, never the contraceptive kind.
        "1917/ITT/LW Supply and Installation of Rx coils for MRI scanners",
        "Purchase of replacement coil for Logiq E10S",
]:
    check("never admitted: %s" % bad[:58], not B.match_title(_gy_rx, bad))

print("  the ordinary words stay refused — each was tried and read")
for bad in [
        # "menstrual" — a Leidos/Bunzl hygiene supply contract, not gynaecology.
        # Only the phrase "heavy menstrual bleeding" is used.
        "The Supply of Menstrual Products",
        # "sling" — patient handling hoist slings.
        "The Supply and Delivery of High Back Slings, Dress Toileting Slings, Electric Hoists, Stand Aids",
        # "mesh" — the include says "surgical mesh", so hernia never reaches here.
        "Hernia Mesh incl. Fixation",
        "NP51820 Hernia Mesh",
        # "obstetric" is refused outright, which is why this page never has to
        # write the exclusion the maternity rule needs for the same four rows.
        "Non-Obstetric Ultrasound Service – East Surrey – CAN",
        "Non-Obstetrical Ultrasound – East Surrey – CAN",
        "Insourced Non-Obstetric Ultrasound Services YSTH",
        "PSR Urgent Award for Insourced Non-Obstetric Ultrasound Services YSTH",
        # HPV vaccination is a national immunisation programme. The feed's `spec`
        # field tags both of these rows as this speciality. It is wrong.
        "Human Papillomavirus (HPV) vaccine (2025)",
        "Human papillomavirus vaccine 2021",
        "Improving HPV uptake in school leavers living in areas of high deprivation",
        # STI testing — one row is already pathology's, and neither is gynaecology.
        "WSFT - Pathology - STI Testing",
        # Bare HIV is antiretroviral pharmacy and commissioned HIV services.
        "HIV Medicines",
        "NP43324 HIV Generic Medicines",
        "South London HIV Peer Support and Advice & Advocacy Services",
        # Botulinum toxin covers every indication; none of these is a gynae buy.
        "NP90323(a) Botulinum Toxin Type A Medicines (Botox®)",
        "NP90323(c) Botulinum Toxin Type A Medicines (Xeomin®)",
        # Hologic sells into mammography and cytology as well as gynaecology, and
        # this row is already counted on pathology. Only "novasure" is used.
        "Roche - Hologic - Cytology - Equipment and Consumables MSC",
        # Names no organ. Genuinely ambiguous on the title, so it is declined.
        "Tissue removal devices and accessories",
        # Bare "screening" is bowel, lung, eye, TB, newborn and genetic screening.
        "NHSS Bowel Screening Test Kits and Analysers",
        "Lung Cancer Screening - DAP C",
        "Procurement of Test Kits for Newborn Screening of Cystic Fibrosis (CF)",
        # Bare "cervical" is a spine and collar word, so only the cervical
        # screening / smear / cytology forms are used.
        "Cervical Collars and Spinal Immobilisation",
]:
    check("never admitted: %s" % bad[:58], not B.match_title(_gy_rx, bad))

print("  breast stays with plastics — this page counts the framework, not the awards")
# The page has a section headed BREAST IMPLANTS, EXPANDERS AND EXTERNAL PROSTHESES,
# but plastics, burns and reconstruction already claims these four awards. Counting
# them twice would tell a rep nothing new.
for bad in [
        "HEY/18/161 BREAST IMPLANTS",
        "CLI-OJEU-45806 SURGICALLY IMPLANTED BREAST PROSTHESES",
        "External Breast Prosthesis",
        "External Breast Prosthesis [4233683]",
        "Breast Pumps and Breast Milk Collection Sets [5180689]",
        "Maintenance of Mobile Breast Screening Tailers and Mobile MRI Trailers",
]:
    check("breast award left to its own page: %s" % bad[:48], not B.match_title(_gy_rx, bad))

print("  true positives — awards that must be on this patch")
for good in [
        "Provision of Outsourcing Gynaecology Services for Barking, Havering & Redbridge University Hospital NHS Trust",
        "All Wales Womens Health Obs & Gynae Consumables",
        "Hysteroscopes",
        "Replacement of Hysteroscopy Scopes",
        "Endometrial Ablation Devices and Uterine Tissue Removal Systems",
        # Only reachable through the brand name, exactly as "isolette" is on the
        # maternity patch. Hologic's endometrial ablation system.
        "2 X HOLOGIC NOVASURE RFC2010 RF CONTROLLERS",
        "Pessaries [4186866]",
        "Obstetrics and Vinyl Pessaries",
        "0P002079 - Colposcope - Capital - Central Delivery Suite RSCH",
        "ESNEFT3207 Urodynamics",
        # Continence hands the surgical stress-incontinence ground to this page and
        # excludes it by name on its own; it must therefore land somewhere.
        "Tower 2 - Surgical Mesh, Fixation Devices, Stress Incontinence and Bulking Agents",
        "Complex Termination of Pregnancy (CTOP) Services across the South East",
        "NP36726 Fertility Medicines",
        "NP57421 Condoms and related Products",
        "Vaginal Speculum",
        "AA-563-24 TW Provision of Intrauterine Shaver and associate units",
]:
    check("admitted: %s" % good[:58], B.match_title(_gy_rx, good))

print("  the six agreements, and only those six")
_gy_want = {
    "Maternity, Obstetrics, Gynaecology and Sexual Health Products",
    "Obstetrics and Vinyl Pessaries",
    "Rigid Endoscopy and Associated Options and Related Services",
    "Minimally Invasive Surgery, Related Equipment and Accessories",
    "Surgical Mesh",
    "Surgical Implants for Men’s and Women’s Health",
}
_gy_got = {f["name"] for f in gy["frameworks"]}
check("exactly the six agreements the page's Buying route blocks name",
      _gy_got == _gy_want, "got %s" % sorted(_gy_got - _gy_want))
# Named refusals. Each is a framework that exists in frameworks.json and is NOT
# this page's, and each would inflate the Suppliers tab if it crept in.
_gy_fw_rx = B.compile_rule(_gy_rule)["fw"]
for bad in [
        "External Breast Prosthesis and Chest Support",
        "Neuromodulation Devices and Associated Products",
        "Procedure Packs",
        "Electrosurgical Consumables and Related Accessories",
        "Mammography Imaging Systems and Associated Options and Related Services",
        "Urology and Bowel Management",
        "Disposable and Washable Continence Care",
        "Bladder Scanners and Associated Options and Related Services",
        "Flexible Endoscopes and Associated Options and Related Services",
]:
    check("framework not claimed: %s" % bad[:52], not _gy_fw_rx.search(bad))

print("  the delisted six are removed here as well as on maternity")
# A shared framework corrected on one page and published raw on the other is the
# same class of defect as a wired page with no data behind it.
_gy_shared = [f for f in gy["frameworks"]
              if f["name"] == "Maternity, Obstetrics, Gynaecology and Sexual Health Products"][0]
check("the shared agreement shows 51 suppliers, not 57",
      _gy_shared["supplierCount"] == 51, "got %s" % _gy_shared["supplierCount"])
check("all six delisted companies are recorded rather than dropped",
      len(_gy_shared["delisted"] or []) == 6)
_gy_names = " || ".join(
    s["name"] + " " + " ".join(s["variants"]) for s in gy["suppliers"]).lower()
for gone in ["cardiac services", "durbin", "medichill", "valley northern", "viomedex"]:
    check("delisted company absent from the Suppliers tab: %s" % gone, gone not in _gy_names)
# Bray holds the pessary agreement and was delisted from the other, so it must
# still appear — but only against the pessaries.
_gy_bray = [s for s in gy["suppliers"] if "bray" in s["name"].lower()]
check("Bray appears on the pessary agreement only",
      len(_gy_bray) == 1 and _gy_bray[0]["frameworks"] == ["Obstetrics and Vinyl Pessaries"],
      "got %s" % [(s["name"], s["frameworks"]) for s in _gy_bray])

print("  the Drug Tariff is a SLICE of Part IXA, never the whole part")
_gy_dt = gy["drugTariff"]
check("Part IXA is claimed", _gy_dt["parts"] == ["IXA"])
check("and it is narrowed by a stated product filter", _gy_dt["vmpFilter"] == "pessar")
# The whole of Part IXA is 56,833 lines of dressings and elastic hosiery. If this
# ever approaches that, the filter has stopped being applied and Juzo and Sigvaris
# are about to be published as gynaecology's leading suppliers.
_gy_ixa_all = len([r for r in B.load("drug-tariff-part-ix.json")["rows"] if r[0] == "IXA"])
check("the slice is a small fraction of Part IXA (%d of %d lines)"
      % (_gy_dt["lineCount"], _gy_ixa_all),
      _gy_dt["lineCount"] < _gy_ixa_all / 100)
check("every counted line is a pessary line", _gy_dt["lineCount"] == 257,
      "got %s" % _gy_dt["lineCount"])
check("64 distinct virtual medicinal products, as the page states",
      _gy_dt["vmpCount"] == 64, "got %s" % _gy_dt["vmpCount"])
check("eight suppliers, as the page states",
      _gy_dt["supplierCount"] == 8, "got %s" % _gy_dt["supplierCount"])
# The dressing and hosiery names that dominate Part IXA must never surface here.
_gy_dt_names = " ".join(s["name"] for s in _gy_dt["topSuppliers"]).lower()
for bad in ["juzo", "sigvaris", "molnlycke", "smith & nephew", "convatec"]:
    check("no Part IXA dressing/hosiery supplier leaks in: %s" % bad, bad not in _gy_dt_names)
check("the published rule states the slicing, so a reader can judge it",
      "narrowed to the lines whose virtual medicinal product" in gy["rules"]["drugTariff"]
      and "/pessar/i" in gy["rules"]["drugTariff"])

print("  no exclusion list, and the file says why rather than hiding it")
check("exclude is genuinely None, not a never-matching placeholder",
      _gy_rule["exclude"] is None)
check("the published rule explains the absence",
      "NO EXCLUSION LIST IS APPLIED" in gy["rules"]["awards"])
check("no CPV family is claimed, and the absence is explained",
      _gy_rule["cpv"] is None and "No CPV family corroborates" in gy["rules"]["awards"])

print("  the coverage limits are stated, not hidden")
_gy_note = gy["rules"]["frameworks"]
for phrase in ["no gynaecology category", "Lot 6", "British Hernia Society",
               "Operating Theatre and Outpatient Microscopes", "Neuromodulation"]:
    check("coverage note carries: %s" % phrase, phrase in _gy_note)

check("no open tender is invented for an empty day",
      gy["counts"]["openTenders"] == len(gy["openTenders"]))
_gy_raw = len([t for t in _gy_corpus if B.match_title(_gy_rx, t)])
check("the published match count is not inflated above what the filter returns",
      gy["counts"]["awardsShown"] <= gy["counts"]["awardsMatched"] <= _gy_raw,
      "shown %d, matched %d, raw %d" % (
          gy["counts"]["awardsShown"], gy["counts"]["awardsMatched"], _gy_raw))
check("every published award title is one the rule actually accepts",
      all(B.match_title(_gy_rx, a.get("title") or "") for a in gy["awards"]))
check("licence notice carried", bool(gy.get("_notice", {}).get("owner")))
_gy_kb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", GYNAE + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % _gy_kb, _gy_kb < 200)


# ===========================================================================
# PAEDIATRICS (page 2929). The second speciality in the rollout with no NHS
# Supply Chain framework of its own, and the first where that is true because
# NHSSC organises by PRODUCT and this speciality is a POPULATION. Nine adult
# agreements carry paediatric lots; none of them is paediatrics' and claiming
# them would have published roughly 150 office furniture, wheelchair and apron
# manufacturers as this speciality's named suppliers.
# ===========================================================================
print("\nRebuilding the paediatrics slice from live data...")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), PAEDS],
               check=True, capture_output=True)
pd_ = load_panel(PAEDS)
check("the paediatrics slice exists at all", pd_ is not None)
_pd_rule = B.SPECIALITY_RULES[PAEDS]
_pd_rx = B.compile_rule(_pd_rule)

print("  bare child / children is REFUSED, and these are the rows that is refused for")
# 36 titles carry the word and roughly four are this speciality's market. Every
# one below is a real contract in the feeds. If any of them ever matches, the
# word has been admitted to the include list and this tab has become a listing
# of children's mental health, social care and public health commissioning.
for bad in [
        "CAMHs Tier 4 Beds and associated services",
        "Mental Health Support Services for Children and Young People in Liverpool and Knowsley",
        "Digital Mental Health and Emotional Wellbeing Service for Children and Young People",
        "Black Country Self Harm Digital Therapeutic Child and Family Service",
        "Children and Young People Safe Space Support Services",
        "Therapeutic support and mental health services for children in care",
        "NHS SY ICB - Initial Health Check for Looked After Children - Doncaster",
        "Child Sexual Abuse (CSA) Services - Emotional Wellbeing and Support Service and Training for Educational Professionals",
        "Integrated 0-19 Healthy Child Programme Service",
        "Knowsley 0-19(25) Healthy Child Programme",
        "715926485 - Defence Healthy Child Program",
        "0-19 Health Visiting and School Nursing",
        "Inactivated influenza vaccine for children 2025",
        "Contract for the supply of inactivated influenza vaccine for children's flu programme",
        "NHSE1117 Child Only Dental Services",
        "Childsmilie",
        "Child Vision Screening Service (Provider Selection Regime) (Most Suitable Provider Process)",
        "Child Tier 2 Weight Management Service",
        "Neurodevelopmental Support for Children, Families and Professionals",
        "Provision of ASD/ADHD Assessment and Support for Children and Young People across Mid and South Essex",
        # A hospital garden. The clearest demonstration that the word carries no
        # clinical meaning on its own.
        "NGH - Children's Garden",
        "LGA children's improvement - Health Engagement Advisors (HEA) with notice",
]:
    check("child-word row left off this patch: %s" % bad[:56], not B.match_title(_pd_rx, bad))

print("  PICU on this data means PSYCHIATRIC intensive care every time")
for bad in [
        "Mental Health PICU provision",
        "North Staffordshire Combined Healthcare NHS Trust Out of Area Psychiatric Intensive Care (PICU) Placement",
]:
    check("PICU row not read as paediatric: %s" % bad[:52], not B.match_title(_pd_rx, bad))

print("  adult neurodevelopmental services stay off a children's page")
for bad in [
        "Adult ADHD assessment service",
        "Autism/ADHD Diagnostic Assessment and Treatment – Adults",
        "Adult ADHD Services",
        "Pre- and Post-Diagnostics Service for Adults with Autism",
        "Autism Spectrum Disorder Assessments",
]:
    check("adult ADHD/autism row refused: %s" % bad[:52], not B.match_title(_pd_rx, bad))

print("  the neonatal vocabulary is left to the page that owns it")
for bad in [
        "Maintenance of Infant Ventilators",
        "Parent Infant Psychotherapy to families in East Sussex",
        "Market Engagement Event – Brent Parent and Infant Relationship Service (PAIRS)",
        "Purchase of Baby Warmers with Resuscitation",
        "Supply & Distribution of Baby Packs  (1)",
        "Baby Bundles",
        "Breast Pumps and Breast Milk Collection Sets [5180689]",
]:
    check("maternity/neonatal row not claimed here: %s" % bad[:52], not B.match_title(_pd_rx, bad))

print("  bare tracheostomy is adult ENT and critical care")
for bad in [
        "Tracheostomy Tubes and Accessories",
        "Tracheostomy Tubes, Tube Holders and Accessories - 5806781",
]:
    check("adult tracheostomy row refused: %s" % bad[:52], not B.match_title(_pd_rx, bad))

print("  true positives — awards that must be on this patch")
for good in [
        "Specialised Paediatric Whole-Body MRI Surveillance for Cancer Predisposing Syndromes",
        "Paediatric Videoflouroscopy Service for CLEFT patients",
        "Paediatric Occupational Therapy for Special Schools",
        "Childrens Community Health Services",
        "Framework  Agreement for Supply of Adult and Paediatric Nutrition Products",
        "Manuals / Registrations for Advanced Paediatric Life Support Courses.",
        # Reached through the qualified equipment phrase, never through "children".
        "Aids for Daily Living Equipment for Children and Young People Framework Agreement",
        "All Wales Women & Child Health Consumables",
        "Supply of Children's Buggies and Adult & Children's Wheelchairs",
        "Parenteral Nutrition for Adults and Paediatrics",
        "Neonatal Equipment, Adult, Paediatric & Neonatal Phototherapy Devices and Associated Accessories & Services",
        "NP14220 Neonatal and Paediatric Tracheostomy Tubes",
]:
    check("admitted: %s" % good[:58], B.match_title(_pd_rx, good))

print("  no framework and no supplier list, said in the data rather than left blank")
check("frameworks is genuinely None, not a pattern that finds nothing today",
      _pd_rule["frameworks"] is None)
check("the frameworks list is empty", pd_["counts"]["frameworks"] == 0 and not pd_["frameworks"])
check("the suppliers list is empty for the same reason",
      pd_["counts"]["suppliers"] == 0 and not pd_["suppliers"])
check("the published rule says no framework covers this speciality",
      "NO NHS Supply Chain framework covers this speciality" in pd_["rules"]["frameworks"])
# The nine agreements are the useful thing this panel can say. If the coverage
# note loses them the panel stops being worth reading.
for phrase in ["Lot 23 crutches", "paediatric buggies inside Lot 1",
               "Lot 4 adult", "Infant Feeding and Accessories",
               "Peripheral IV Site Monitoring Device", "2022/S 000-033396",
               "2026/S 000-031173", "roughly 150 companies"]:
    check("coverage note carries: %s" % phrase, phrase in pd_["rules"]["frameworks"])
check("the note says what is deliberately not counted",
      "Children's mental health" in pd_["rules"]["frameworks"])

print("  the Drug Tariff slice reproduces the page's own published figures")
_pd_dt = pd_["drugTariff"]
check("three parts are claimed", _pd_dt["parts"] == ["IXA", "IXB", "IXC"])
check("and they are narrowed by a stated product filter",
      _pd_dt["vmpFilter"] == "p[ae]ediatric|child|infant|junior")
check("473 lines, the figure the page publishes", _pd_dt["lineCount"] == 473,
      "got %s" % _pd_dt["lineCount"])
check("52 suppliers list a paediatric-named line",
      _pd_dt["supplierCount"] == 52, "got %s" % _pd_dt["supplierCount"])
# The whole of the three parts is 66,293 lines. If the slice ever approaches that,
# the filter has stopped being applied and the entire dressings and stoma
# catalogue is about to be published as paediatrics'.
_pd_all = len([r for r in B.load("drug-tariff-part-ix.json")["rows"]
               if r[0] in ("IXA", "IXB", "IXC")])
check("the slice is well under one per cent of the three parts (%d of %d)"
      % (_pd_dt["lineCount"], _pd_all), _pd_dt["lineCount"] < _pd_all / 100)
# The brand-name search is the whole reason Part IXC appears at all. Searching the
# generic description alone returns 258 lines, every one of them IXA.
_pd_dtrows = [r for r in B.load("drug-tariff-part-ix.json")["rows"]
              if r[0] in ("IXA", "IXB", "IXC")]
import re as _re
_pd_vrx = _re.compile(_pd_rule["tariffVmp"], _re.I)
check("the rule reads the brand name as well as the generic one",
      tuple(_pd_rule.get("tariffFields") or ()) == ("vmp", "amp"))
check("generic-name-only would lose Part IXC entirely, which is why it is not used",
      len([r for r in _pd_dtrows if _pd_vrx.search(r[2] or "")]) == 258)
check("the published rule states the limit of the counting rule",
      "is invisible to it" in pd_["rules"]["drugTariff"])
_pd_top = {x["name"]: x["lines"] for x in _pd_dt["topSuppliers"]}
for name, lines in [("Dermacea Ltd", 54), ("Kavendor Ltd", 52), ("Coloplast Ltd", 26),
                    ("Flexicare Medical Ltd", 23), ("Charles S Bullen Stomacare Ltd", 22)]:
    check("top supplier matches the page: %s %d lines" % (name, lines),
          _pd_top.get(name) == lines, "got %s" % _pd_top.get(name))

print("  no exclusion list, and the file says why rather than hiding it")
check("exclude is genuinely None, not a never-matching placeholder",
      _pd_rule["exclude"] is None)
check("the published rule explains the absence",
      "NO EXCLUSION LIST IS APPLIED" in pd_["rules"]["awards"])
check("no CPV family is claimed, and the absence is explained",
      _pd_rule["cpv"] is None and "No CPV family corroborates" in pd_["rules"]["awards"])
check("no open tender is invented for an empty day",
      pd_["counts"]["openTenders"] == len(pd_["openTenders"]))
check("every published award title is one the rule actually accepts",
      all(B.match_title(_pd_rx, a.get("title") or "") for a in pd_["awards"]))
check("licence notice carried", bool(pd_.get("_notice", {}).get("owner")))
_pd_kb = os.path.getsize(os.path.join(HERE, "data", "speciality-panels", PAEDS + ".json")) // 1024
check("slice stays under 200 KB (is %d KB)" % _pd_kb, _pd_kb < 200)


# ===========================================================================
# DRUG TARIFF PRICES ARE POUNDS, NOT PENCE. NHSBSA publishes Part IX prices in
# pence and until 10/09/2026 build_tariff passed them straight to a renderer
# that prints a pound sign in front of them. Three live panels were telling
# paying members that Part IXA reimburses "from £3.0 to £46900.0" when the real
# range is £0.03 to £469.00. Checked arithmetically against the source rows so
# it cannot silently come back.
# ===========================================================================
print("\nDrug Tariff prices are published in pounds, not NHSBSA's pence")
_dt_doc = B.load("drug-tariff-part-ix.json")
_dt_ix = {k: i for i, k in enumerate(_dt_doc["schema"])}
for _slug, _r in sorted(B.SPECIALITY_RULES.items()):
    if not _r.get("tariffParts"):
        continue
    _pan = load_panel(_slug)
    _t = (_pan or {}).get("drugTariff")
    if not _t:
        continue
    _rows = [r for r in _dt_doc["rows"] if r[_dt_ix["part"]] in tuple(_r["tariffParts"])]
    if _r.get("tariffVmp"):
        _f = tuple(_r.get("tariffFields") or ("vmp",))
        _rx2 = __import__("re").compile(_r["tariffVmp"], __import__("re").I)
        _rows = [r for r in _rows
                 if _rx2.search(" ".join((r[_dt_ix[k]] or "") for k in _f))]
    _raw = [float(r[_dt_ix["price"]]) for r in _rows
            if str(r[_dt_ix["price"]]).strip() not in ("", "None")]
    check("%s publishes the tariff range in pounds" % _slug,
          abs(_t["priceMax"] - round(max(_raw) / 100.0, 2)) < 0.005
          and abs(_t["priceMin"] - round(min(_raw) / 100.0, 2)) < 0.005,
          "panel %s..%s, source pence %s..%s" % (
              _t["priceMin"], _t["priceMax"], min(_raw), max(_raw)))
    # Part IX reimburses appliances. A four-figure line would be a pence value
    # that slipped through rather than a real dressing.
    check("%s tariff top price is a plausible appliance price" % _slug,
          _t["priceMax"] < 1000, "got %s" % _t["priceMax"])


# The tariff slicing must not have changed any panel that does not ask for it.
# FIVE RULES SLICE A PART, and each is here because the part it slices is not its
# speciality: gynaecology takes the 257 pessary lines out of Part IXA's 56,833,
# paediatrics takes the 473 lines whose product or brand name says paediatric, child,
# infant or junior out of Parts IXA, IXB and IXC, urology takes the 3,108 catheter,
# urostomy and catheter-drainage lines out of the same three parts, respiratory
# takes 608 lines out of Part IXA — the tracheostomy breathing aid, tube holder,
# cleaning device and laryngectomy protector families plus the peak flow meters —
# and ophthalmology takes the 223 lines of the community ocular surface range,
# which is 89 virtual medicinal products of ocular lubricants, lid hygiene
# products and hypertonic saline, added 10/09/2026. That leaves the dressing and
# elastic hosiery lines to tissue viability, including the tracheostomy DRESSING
# range, which is a dressing, and the eye pad, which is on both pages because it
# is one product with two clinical homes. Adding a slug to this set is a decision
# about a published claim, never a way past a failing check.
# ENT and head and neck, added 10/09/2026, takes 645 Part IXA lines: the whole
# tracheostomy and laryngectomy range (582 of which respiratory also claims, on
# purpose and stated in both files), plus the voice prosthesis cleaning brushes,
# tracheostomy dressings, ear drops, nasal preparations and the one auto
# inflation device that no other page reaches.
# Dermatology, added 11/09/2026, takes 87 Part IXA lines: the reimbursed emollient
# range, 28 virtual medicinal products from 19 companies. It is the sixth slice and
# the one whose page has no framework at all, so the tariff IS its supplier list.
# The pattern never uses bare "paraffin", because "Paraffin gauze dressing sterile"
# is a wound contact layer and tissue viability's, and it anchors "urea" on a word
# boundary and a percentage, because "Curea" ends in those four letters and would
# otherwise bring thirteen wound dressing lines with it.
_TARIFF_FILTER_EARNED = {GYNAE, PAEDS, UROLOGY, RESP, OPHTH, ENT, DERM}
for _slug, _r in sorted(B.SPECIALITY_RULES.items()):
    if _r.get("tariffVmp") and _slug not in _TARIFF_FILTER_EARNED:
        check("%s must not have grown a tariff filter unnoticed" % _slug, False)


# ---------------------------------------------------------------------------
# VASCULAR ACCESS AND IV THERAPY. The patch is the line, not what goes down it.
# Its two dangers are opposites. One is that "intravenous" and "IV" appear on
# every medicine and fluid bought by that route, so the include admits fourteen
# pharmacy contracts unless the dose form is refused. The other is that the word
# "vascular" belongs to a DIFFERENT page: NHS Supply Chain's "Vascular Therapy and
# Associated Products" is compression and mechanical VTE prophylaxis, and it is
# vascular-surgery-and-pad's framework, not this one.
# ---------------------------------------------------------------------------
print("\nVASCULAR ACCESS AND IV THERAPY")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), VASCACCESS],
               check=True, capture_output=True)
va = load_panel(VASCACCESS)
check("panel is defined", va.get("defined") is True)

_va_rule = B.SPECIALITY_RULES[VASCACCESS]
_va_rx = B.compile_rule(_va_rule)

print("  the route is not the product — every one of these is a real row that matched")
for bad in [
        # Monoclonals. \w+mab was checked against the whole corpus first: it matches
        # 41 titles and all 41 are drugs, so it refuses nothing real.
        "Bevacizumab IV Infusion Vials",
        "Ravulizumab IV Infusion",
        "ALLOGA UK LTD (WT) - WT2024-04 - MOGAMULIZUMAB (POTELIGEO) 20 mg in 5mL "
        "Concentrate for IV Infusion;1 Vial Pack",
        # Dose form, not device. None of the sixteen true positives carries a dose.
        "Procurement of MIFAMURTIDE (PAS) 4 mg Intravenous Infusion",
        "Supply, Storage, and Maintenance of Glucose 10% and 50% 500ml iv infusion",
        # Named substances the dose-form signature does not reach.
        "Hepatitis B immunoglobulin intravenous use (IV)",
        "Erythropoietin Stimulating Agents & Intravenous Iron",
        # Fluids are pharmacy wholesale. Seven rows, all of them medicines supply.
        "The Supply, Storage, and Management of Intravenous Fluids",
        "The Supply and Storage of Intravenous Fluids and Peritoneal dialysis fluids",
        "Intravenous & Topical Fluids",
        "IV Fluids & Irrigation Solutions",
        "Dynamic Purchasing System (DPS) for the Supply of Antibiotics and IV Fluids",
        "Dynamic Purchasing System (DPS) for the Supply of Antibiotics and IV Fluids "
        "(Quarterly Notice)",
]:
    check("never admitted: %s" % bad[:58], not B.match_title(_va_rx, bad))

print("  the word is not the route — cannula and pump both belong to other patches")
for bad in [
        # "cannula" without a vein. Respiratory.
        "The supply of Nasal Cannula & Oxygen Masks for Pandemic Preparedness 24/25",
        # An insulin pump is subcutaneous. Diabetes, and on no framework above.
        "Insulin Infusion Pumps, Continuous Glucose Monitoring Systems and Associated Consumables",
]:
    check("never admitted: %s" % bad[:58], not B.match_title(_va_rx, bad))

print("  true positives — awards that must be on this patch")
for good in [
        # The framework's own award notice. It is PLURAL, and an end-anchored
        # include pattern silently drops it; that is how this rule failed its first
        # draft, so it is pinned here.
        ": Central Venous Catheters and Associated Products",
        "Intravenous Cannula and Associated Products",
        "Needlefree Connection Systems and Associated Products",
        "IV Cannulae",
        "Vascular Access Accessories",
        "Intravenous and Pressure Monitoring Accessories",
        "Infusion Pumps, Syringe Pumps, Administration Sets and Associated Equipment",
        "Extension Sets",
        "Needle Free Access Devices and IV Accessories",
]:
    check("admitted: %s" % good[:58], B.match_title(_va_rx, good))

print("  the six frameworks, and the three refused by name")
_va_fw = {f["name"] for f in va["frameworks"]}
check("six frameworks exactly", len(va["frameworks"]) == 6,
      ", ".join(sorted(_va_fw)))
for name in [
        "Central Venous Catheters and Associated Products",
        "Intravenous Cannula and Associated Products",
        "Intravenous Accessories and Pressure Monitoring Accessories",
        "Needlefree Connection Systems and Associated Products",
        "Infusion Pumps and Administration Sets and Associated Products",
        "Extension Sets and Lines",
]:
    check("framework carried: %s" % name[:52], name in _va_fw)
# THE TRAP. Compression hosiery — Juzo, Sigvaris, Haddenham, Medi, Thuasne — reaching
# a vascular ACCESS page would be the wound care "seed viability" failure repeated.
_va_fwrx = B.compile_rule(_va_rule)
for name in [
        "Vascular Therapy and Associated Products",   # compression, vascular-surgery-and-pad's
        "Blood Collection Devices",                   # pathology's and haematology's
        "Syringes, Needles and Associated Products",  # a product, not a clinical category
]:
    check("framework refused: %s" % name[:52], name not in _va_fw)

print("  no Drug Tariff part, and that was checked not assumed")
# Part IX's only hits on this include list are tracheostomy inner cannulae and a
# needle-free INSULIN system. Neither is vascular access, and these devices are not
# FP10 reimbursable, so reaching for IXA here would publish another page's products.
check("declares no tariff part", _va_rule.get("tariffParts") is None)
check("carries no Drug Tariff lines", not va.get("drugTariff"))

print("  one name per company")
_va_names = [s["name"] for s in va["suppliers"]]
check("no duplicate supplier names", len(_va_names) == len(set(_va_names)))
# "ALL ROUTES" is an SCCL supply-route marker, not part of a company name. Left
# unaliased it published Fresenius Kabi twice, once under each spelling.
check("Fresenius Kabi appears exactly once",
      sum(1 for n in _va_names if "Fresenius Kabi" in n) == 1,
      ", ".join(n for n in _va_names if "Fresenius Kabi" in n))
check("no supply-route marker survives in a supplier name",
      not [n for n in _va_names if "All Routes" in n],
      ", ".join(n for n in _va_names if "All Routes" in n))



# ---------------------------------------------------------------------------
# UROLOGY. Three dangers, and all three are about words that look urological
# and are not. "Neurology" contains the letters of urology, so an unanchored
# pattern turns a urology tab into a neurology insourcing list. Intravascular
# lithotripsy is the same physics as kidney stone lithotripsy and the opposite
# patch. And Part IXA holds 85 catheter product families of which one, the
# indwelling pleural drainage catheter, is respiratory.
# ---------------------------------------------------------------------------
print("\nUROLOGY")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), UROLOGY],
               check=True, capture_output=True)
ur = load_panel(UROLOGY)
check("panel is defined", ur.get("defined") is True)

_ur_rule = B.SPECIALITY_RULES[UROLOGY]
_ur_rx = B.compile_rule(_ur_rule)

print("  NEUROLOGY is not urology, and the letters say otherwise")
# Seven real rows in the feeds. Every one of them matches a pattern written as
# "urolog" without a leading word boundary. If any is ever admitted, this tab has
# become an outpatient insourcing listing.
for bad in [
        "WPL07040 - Neurology Insourcing",
        "Provision of Outsourced Neurology Services for Barking, Havering & Redbridge "
        "University Hospital NHS Trust",
        "Sub Contract Insourcing of Neurology Out Patient Activity 2026-27",
        "NP30923 Psychiatry and Neurology Medicines",
        "NP30925 Psychiatry and Neurology Medicines",
        "Neurological Rehabilitation Service",
        "Neuromodulation/Spinal Cord Stimulators, Intrathecal Drug Pumps, "
        "Radiofrequency Ablation and Associated Products",
]:
    check("neurology row refused: %s" % bad[:52], not B.match_title(_ur_rx, bad))

print("  the one false positive the include list produced, and it is excluded by name")
# Shockwave Medical's coronary and peripheral IVL. Same physics, opposite patch.
check("intravascular lithotripsy refused",
      not B.match_title(_ur_rx, "Intravascular Lithotripsy Equipment and Consumables - 4307395"))
check("and the exclusion is the only one the rule carries",
      _ur_rule["exclude"] == r"\b(intravascular)\b")

print("  the loose terms were refused in the include, not argued with afterwards")
for bad in [
        # bare "urinary" — the pharmacy patch, three real rows.
        "Antibiotic, Antiviral & Genito Urinary Medicines",
        "NP36124 Antibiotic, Antiviral & Genito Urinary Medicines",
        "NP36126 Antibiotic & Genito Urinary Medicines",
        # bare "urine" — pathology specimen tubes.
        "Evacuated Blood Collection Systems and Urine Collection Systems",
        # bare "catheterisation" — a cardiac cath lab.
        "Managed Service for Catheterisation Lab, Cardio Thoracic Centre and Vascular",
        # bare "brachytherap" — an HDR afterloader treats cervix and breast too.
        "NHS Grampian HDR Brachytherapy Afterloader",
        # bare "endoscop" — 36 rows and almost none of them this patch.
        "Colon Capsule Endoscopy (CCE)",
        "Purchase of Nasendoscopes",
        "Automated Endoscope Washer Disinfectors",
        "Replacement of Hysteroscopy Scopes",
        "NHSGJ0089/22 Supply of Endoscopic Vessel Harvesting Tools and Associated Consumables",
        "Endoscopy Insourcing Services-Bowel Screening Wales and Weekend Diagnostics Activity",
        # bare "laser" — ophthalmology, ENT, burns and dermatology.
        "ESNEFT2730 Purchase of ENT Laser",
        "Contract for UltraPulse Alpha Laser for Burns Unit with Point of Sale Maintenance",
        "Topcon - Pascal Synthesis Y4 laser - PPM maintenance",
        "Cook Optical Laser Fibres",
        # bare "ablation" — endometrial, radiofrequency, spinal.
        "Endometrial Ablation Devices and Uterine Tissue Removal Systems",
        "Radiofrequency Ablation Device and Consumables [3115211]",
        # bare "stent" — eight of nine hits are cardiac or aortic.
        "Cardiology Stents - DES",
        "Exstent Personalised External Aortic Root Support",
        # bare "stone" — a place name, not a calculus.
        "Maidstone and Tunbridge Wells Managed Equipment Service",
        # bare "orchid" — a flower.
        "Orchid Ward Refurbishment",
        # bare "catheter" — the continence rule's own list of what it drags in.
        "HRIM Solid State Catheter",
        "Renal Catheter & Fistula Packs",
]:
    check("never admitted: %s" % bad[:58], not B.match_title(_ur_rx, bad))

print("  true positives — awards that must be on this patch")
for good in [
        "Urology Consumables",
        "Urology Products (2529408)",
        "GGC0584 Endourology Disposable Products",
        "Endoscopy, Endourology & Oncology Ablation Consumables & Associated Products",
        "NH2659 Urology Cystoscopy Surveillance Service",
        "ESNEFT3207 Urodynamics",
        "Prostatic Ablation Devices",
        "National Framework Agreement for Transperineal Prostate Biopsy System",
        "C455465 - Lithotriptor",
        "WSFT - Theatres - EBME - Lithotripter Maintenance",
        # The holmium laser is the urology laser, and this row reaches the panel on
        # that word alone — "Optical Laser Fibres" on its own never does.
        "Optical Laser Fibre Consumables for CyberHo 100 Holmium Laser System (4839792)",
        "Auriga XL & Holmium Pulse 120 Service Agreement",
        "Green Light Laser",
        "Bladder Scanner Purchase",
        "CUBESCAN BIOCON-700-S BLADDER SCANNER",
        "Urinary Catheters & Drainage Bags",
        "Invitation to Tender for the Supply of Urine Meters",
        "Memokath stents for BCH Urology service",
        "Provision of Maintenance & Consumables for Urology Robot",
]:
    check("admitted: %s" % good[:58], B.match_title(_ur_rx, good))

print("  the nine frameworks, and the six refused by name")
_ur_fw = {f["name"] for f in ur["frameworks"]}
check("nine frameworks exactly", len(ur["frameworks"]) == 9, ", ".join(sorted(_ur_fw)))
for name in [
        "Urology and Bowel Management",
        "Endoscopy, Endourology and Oncology Ablation Consumables and Associated Products",
        "Male Intra-Urethral Catheter with Magnet Control",
        "Lithotripsy and Associated Options and Related Services",
        "Bladder Scanners and Associated Options and Related Services",
        "Brachytherapy Seeds and Associated Accessories",
        "Rigid Endoscopy and Associated Options and Related Services",
        "Flexible Endoscopes and Associated Options and Related Services",
]:
    check("framework carried: %s" % name[:52], name in _ur_fw)
# The apostrophe in this one is NHS Supply Chain's own curly character, which is
# why the pattern stops at "surgical implants for men".
check("framework carried: Surgical Implants for Men's and Women's Health",
      any(n.startswith("Surgical Implants for Men") for n in _ur_fw))
# THE TRAP. Neuromodulation is 23 pain-management suppliers, Electrosurgical
# Consumables 33 diathermy ones and Robotic Medical Equipment six capital houses.
# All three carry urological product and none of them is a urology agreement.
for name in [
        "Neuromodulation Devices and Associated Products",       # neurology's
        "Electrosurgical Consumables and Related Accessories",   # theatres'
        "Robotic Medical Equipment and Associated Accessories",  # theatres'
        "Disposable and Washable Continence Care",               # continence's
        "Central Venous Catheters and Associated Products",      # vascular access'
        "Ear, Nose and Throat (ENT) Endoscopes and Associated Options and Related Services",
]:
    check("framework refused: %s" % name[:52], name not in _ur_fw)

print("  the Drug Tariff slice is a slice, and the pleural catheter is not in it")
_ur_dt = ur["drugTariff"]
check("three parts are claimed", _ur_dt["parts"] == ["IXA", "IXB", "IXC"])
check("and narrowed by a stated product filter", bool(_ur_dt["vmpFilter"]))
check("3,108 lines", _ur_dt["lineCount"] == 3108, "got %s" % _ur_dt["lineCount"])
check("92 virtual medicinal products, every one of them read",
      _ur_dt["vmpCount"] == 92, "got %s" % _ur_dt["vmpCount"])
check("55 suppliers list a line on this patch",
      _ur_dt["supplierCount"] == 55, "got %s" % _ur_dt["supplierCount"])
import re as _ur_re
_ur_vrx = _ur_re.compile(_ur_rule["tariffVmp"], _ur_re.I)
# THE ONE THAT MATTERS. Bare "catheter" over Part IXA returns 85 product families
# and 84 are urinary. This is the eighty-fifth, and it is respiratory.
check("the indwelling pleural drainage catheter is not a urology line",
      not _ur_vrx.search("Indwelling pleural drainage systems catheter"))
# Containment is the continence page's half of Part IXB, not this page's.
for bad in ["Disposable pads for light incontinence", "Washable absorbent pants",
            "Colostomy bags", "Ileostomy bags"]:
    check("containment or colorectal line left off: %s" % bad[:46],
          not _ur_vrx.search(bad))
for good in ["Nelaton catheter male 12Ch", "Foley catheter paediatric 8Ch",
             "Urinary suprapubic catheter 16Ch", "Urostomy bags",
             "Incontinence sheaths", "Sterile leg bags", "Catheter valves"]:
    check("tariff line carried: %s" % good[:46], bool(_ur_vrx.search(good)))
# The whole of the three parts is 66,293 lines. If the slice ever approaches that,
# the filter has stopped being applied and the dressings catalogue is about to be
# published as urology's.
_ur_all = len([r for r in B.load("drug-tariff-part-ix.json")["rows"]
               if r[0] in ("IXA", "IXB", "IXC")])
check("the slice is under a tenth of the three parts (%d of %d)"
      % (_ur_dt["lineCount"], _ur_all), _ur_dt["lineCount"] < _ur_all / 10)

print("  CPV corroborates and never admits")
check("one CPV prefix, the urology exploration devices family",
      _ur_rule["cpv"] == ("33125",))
# Every award on this panel title-matched. If one ever appears that did not, the
# builder's title-match-required rule has been loosened.
check("every award shown was admitted by its title, not by a CPV code",
      all(B.match_title(_ur_rx, a["title"]) for a in ur["awards"]))

print("  the coverage note says what is shared and what is missing")
for phrase in ["Rigid Endoscopy and Flexible Endoscopes",
               "Maintenance, Repair and Calibration of Medical Equipment",
               "2021/S 000-007768",
               "dispensing appliance contractors"]:
    check("coverage note carries: %s" % phrase[:52], phrase in ur["rules"]["frameworks"])

print("  one name per company")
_ur_names = [s["name"] for s in ur["suppliers"]]
check("no duplicate supplier names", len(_ur_names) == len(set(_ur_names)))
check("Coloplast appears exactly once",
      sum(1 for n in _ur_names if n.startswith("Coloplast")) == 1,
      ", ".join(n for n in _ur_names if "Coloplast" in n))



# ---------------------------------------------------------------------------
# RESPIRATORY. Four dangers, and every one of them was a real hit that was read
# and rejected. A building has ventilation and so does a patient. "Rough
# sleeping" and an ICB insomnia service both contain the word sleep. A
# heart-lung machine is cardiac perfusion and a cardiopulmonary bypass
# oxygenator contains the letters of oxygen. And anaesthesia sits on the same
# framework as ventilators without being this patch.
# ---------------------------------------------------------------------------
print("\nRESPIRATORY")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), RESP],
               check=True, capture_output=True)
rs = load_panel(RESP)
check("panel is defined", rs.get("defined") is True)
check("label is the page's own", rs["label"] == "Respiratory")

_rs_rule = B.SPECIALITY_RULES[RESP]
_rs_rx = B.compile_rule(_rs_rule)

print("  a building is ventilated too")
# Both are real rows in framework-awards.json. Bare "ventilat" admits them, which
# is why the include names "ventilator" and the qualified clinical forms instead.
for bad in ["Provision of Ventilation and Other Remediation Works",
            "Ventilation Verification"]:
    check("HVAC row refused: %s" % bad[:52], not B.match_title(_rs_rx, bad))

print("  sleep is not sleep apnoea")
# Three real rows. A homelessness contract and an ICB insomnia service must never
# reach a respiratory panel on the strength of one word.
for bad in ["Universal Sleep Support Model - NHS West Yorkshire Integrated Care Board "
            "(Bradford District and Craven Health and Care Partnership)",
            "Provision of Drug and Alcohol Support for  Rough Sleepers",
            "Rough Sleeping Drug and Alcohol Psychology Service"]:
    check("sleep row refused: %s" % bad[:52], not B.match_title(_rs_rx, bad))

print("  a heart-lung machine is cardiac perfusion")
for bad in ["Capital Purchase of Heart and Lung Machines with associated Maintenance "
            "and Heater Cooler Units",
            "LivaNova Essenz Perfusion Heart Lung System",
            "Maintenance Perfusion Heart and Lung Machine",
            "Cardiopulmonary Bypass Oxygenators with Customised Tubing Pack [2339172]",
            "Managed Service for Catheterisation Lab, Cardio Thoracic Centre and Vascular"]:
    check("cardiac row refused: %s" % bad[:52], not B.match_title(_rs_rx, bad))

print("  anaesthesia, monitoring, pathology and public health stay on their own pages")
for bad in ["Anaesthetic Gases (Sevoflurane & Isoflurane)",
            "NHS National Framework Agreement for the supply of Inhalation Anaesthetics "
            "and Vaporisers",
            "Purchase of 5 Anaesthetic Machines",
            "ESNEFT2684 Purchase of Anaesthetic Machines",
            "MER T&A Philips - 6 x anaesthetic monitors",
            "Provision of Anaesthetic Management Software",
            "Medacs Anaesthetics Insourcing",
            "The Support of Fabius tiro anaesthesia apparatus",
            "Serenity vaporisers",
            "Sevoflurane and Vaporisers",
            "Pulse Oximetry Consumables",
            "Pulse Oximetry Sensors [4827016]",
            "Pulse Oximetry, Capnography and Related Patient Monitoring Technologies",
            "Blood Gas Managed Service for Betsi Cadwaladr University Health Board",
            "Supply of Replacement Blood Gas Analysers and Consumables",
            "Suction Consumables",
            "Suction Consumables, Wound Drainage, Autologous Blood Systems and Related "
            "Accessories",
            "Suction Controllers (three types) & associated filters",
            "Suction Devices and Tubing",
            "Allen Carr Easyway Smoking Cessation Programme",
            "Smoking Cessation Service in SMEs",
            "Local Stop Smoking Services and Support (LSSSSG)",
            "Global Tuberculosis Screening Service",
            "NEL ICB Latent Tuberculosis Infection (LTBI) Screening Programme (Lots 1-6)",
            "Provision of Medical Gases in Cylinders",
            "STW26-03 AE for Medical Gas",
            "Lung Cancer Screening - DAP C",
            "Replacement Ultrasound Machine for Lung Cancer Diagnostic",
            "Purchase of Baby Warmers with Resuscitation",
            "Resuscitation Council Course Manuals and Registration Fee - ALS, ILS and "
            "PILS courses"]:
    check("off-patch row refused: %s" % bad[:52], not B.match_title(_rs_rx, bad))

print("  the three exclusions, each one a hit that was read and rejected")
for bad, why in [
        ("Most Suitable Provider: Hyperbaric Oxygen Therapy (HBOT) Services for all ages",
         "hyperbaric oxygen is not respiratory medicine"),
        ("WSFT - Pathology - COPD - 6 EPOC devices service cover",
         "an epoc is a blood gas analyser and the title says Pathology"),
        ("Procurement of Test Kits for Newborn Screening of Cystic Fibrosis (CF), "
         "Congenital Hypothyroidism (CHT) and the Maintena",
         "a newborn bloodspot card screens for nine conditions"),
]:
    check("excluded (%s): %s" % (why[:44], bad[:40]), not B.match_title(_rs_rx, bad))

print("  and the rows that must be present")
for good in ["Respiratory Solutions",
             "Non-Invasive Ventilation, Sleep Therapy (CPAP) and Sleep Monitoring "
             "(Diagnostics)",
             "Airway Management Products and Associated Equipment",
             "Supply of Critical Care Ventilators and Associated Support Services "
             "(Dräger Evita V800)",
             "Pulmonary Function Testing Equipment (Maintenance of) PS5002/25",
             "Lung Function Equipment",
             "Fractional Exhaled Nitric Oxide (FeNO) Equipment and Consumables [4638012]",
             "Asthma Diagnostic Hubs - Fractional exhaled Nitric Oxide (FeNO) Machines, "
             "Consumables and Support",
             "Oxygen Therapy & Inhalation",
             "NP37314 Medical Liquid Oxygen and Associated Equipment and Services",
             "Contract for Amikacin liposomal with nebulisation (with device)",
             "NP94023a-d Ellipta Inhalers",
             "Tracheostomy Tubes, Tube Holders and Accessories - 5806781",
             "Sterile Closed Tracheal Suction Systems (3225312)",
             "Robotic Bronchoscopy System",
             "BTH23-143 Sleep Apnoea Service",
             "ESNEFT3212 Purchase of Sleep Study Equipment",
             "North Cumbria Acute Respiratory Infection Services",
             "Kaftrio - Vertex - Cystic Fibrosis"]:
    check("row carried: %s" % good[:52], B.match_title(_rs_rx, good))

print("  four frameworks, which is the page's own number")
_rs_fw = [f["name"] for f in rs["frameworks"]]
check("exactly four", len(_rs_fw) == 4, "; ".join(_rs_fw))
for name in ["Respiratory Solutions",
             "Non Invasive Ventilation, Sleep Therapy, CPAP and Sleep Monitoring "
             "Diagnostics",
             "Airway Management Products and Associated Equipment",
             "Anaesthesia Machines, Ventilators, Neonatal Equipment and Phototherapy "
             "Systems, Related Accessories and Services"]:
    check("framework carried: %s" % name[:52], name in _rs_fw)
# Refused on purpose. The monitoring framework is nobody's and stays nobody's here,
# because the page names four frameworks and a fifth would contradict it in front of
# the same member. The other three belong to pages that already claim them.
for name in ["Pulse Oximetry, Capnography and Related Monitoring Technologies",
             "Cardiac and Pulmonary Diagnostics and Exercise (Stress) Testing Solutions",
             "Perfusion Devices, Consumables and Associated Equipment",
             "Patient Monitoring Equipment, Bedside Equipment Alarm Monitoring Systems, "
             "Related Products and Services"]:
    check("framework refused: %s" % name[:52], name not in _rs_fw)

print("  the supplier list is the page's own overlap finding")
_rs_names = [s["name"] for s in rs["suppliers"]]
check("no duplicate supplier names", len(_rs_names) == len(set(_rs_names)))
# The page states, from its own reading of the four published lists, that exactly one
# supplier is on all four and that five hold three each. If the alias registry ever
# splits one of those names in two, this panel and the page stop agreeing.
for name in ["Draeger Medical UK", "Armstrong Medical (Eakin Respiratory)",
             "Fisher & Paykel Healthcare", "Flexicare Medical",
             "Henleys Medical Supplies Limited", "Intersurgical"]:
    check("supplier present exactly once: %s" % name[:44],
          sum(1 for n in _rs_names if n == name) == 1)

print("  Part IXA is sliced, and a dressing is not a respiratory line")
_rs_dt = rs["drugTariff"]
check("one part is claimed", _rs_dt["parts"] == ["IXA"])
check("and narrowed by a stated product filter", bool(_rs_dt["vmpFilter"]))
check("608 lines", _rs_dt["lineCount"] == 608, "got %s" % _rs_dt["lineCount"])
check("7 virtual medicinal products, every one of them read",
      _rs_dt["vmpCount"] == 7, "got %s" % _rs_dt["vmpCount"])
check("23 suppliers list a line on this patch",
      _rs_dt["supplierCount"] == 23, "got %s" % _rs_dt["supplierCount"])
import re as _rs_re
_rs_vrx = _rs_re.compile(_rs_rule["tariffVmp"], _rs_re.I)
# THE ONE THAT MATTERS. Bare "tracheostomy" over Part IXA also returns the
# tracheostomy dressing range, which is a dressing and is tissue viability's.
for bad in ["Tracheostomy dressing sterile 8cm x 10cm",
            "Tracheostomy dressing sterile 5cm x 6.5cm",
            "Polyurethane foam film dressing sterile without adhesive border "
            "10cm x 10cm square (fenestrated)",
            "Absorbent perforated dressing with adhesive border 10cm x 10cm",
            "Compression hosiery below knee class 2"]:
    check("tariff line left off: %s" % bad[:46], not _rs_vrx.search(bad))
for good in ["Tracheostomy breathing aids", "Tracheostomy tube holders",
             "Tracheostomy cleaning devices",
             "Tracheostomy and laryngectomy protectors",
             "Peak flow meter standard range", "Peak flow meter low range",
             "Peak flow meter replacement mouthpiece plastic"]:
    check("tariff line carried: %s" % good[:46], bool(_rs_vrx.search(good)))
# Part IXA whole is 56,833 lines of dressings and hosiery. If the slice ever
# approaches that, the filter has stopped being applied.
_rs_all = len([r for r in B.load("drug-tariff-part-ix.json")["rows"] if r[0] == "IXA"])
check("the slice is under a fiftieth of Part IXA (%d of %d)"
      % (_rs_dt["lineCount"], _rs_all), _rs_dt["lineCount"] < _rs_all / 50)

print("  CPV corroborates and never admits")
check("one CPV prefix, the gas therapy and respiratory devices family",
      _rs_rule["cpv"] == ("33157",))
# 33157500 is the hyperbaric chamber code and it sits inside the 33157 family.
# "Diving Life Support (DLS) In-Service Support (ISS)" carries it. The only thing
# keeping a Royal Navy diving contract off this panel is the title gate.
check("the diving life support notice is refused on its title",
      not B.match_title(_rs_rx, "Diving Life Support (DLS) In-Service Support (ISS)"))
check("every award shown was admitted by its title, not by a CPV code",
      all(B.match_title(_rs_rx, a["title"]) for a in rs["awards"]))

print("  the coverage note says what is shared and what is missing")
for phrase in ["Medical and Surgical Consumables",
               "maternity and neonatal",
               "Home Oxygen Service contracts",
               "BNF Chapter 3"]:
    check("coverage note carries: %s" % phrase[:52], phrase in rs["rules"]["frameworks"])



# ---------------------------------------------------------------------------
# STROKE. The page's own subtitle states the finding: there is no stroke
# framework, and thrombectomy sits on Lot 2 of an agreement whose title begins
# "Interventional Cardiology". Three dangers here. A stroke is also a unit of
# cardiac output, and this panel genuinely carries a patient monitor. The words
# clot, retrieval, perfusion and genotyping all belong to this pathway in
# clinical English and to somebody else entirely in this data. And the one
# framework that matters cannot be counted, so the panel has to say why without
# claiming a framework it cannot evidence.
# ---------------------------------------------------------------------------
print("\nSTROKE")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), STROKE],
               check=True, capture_output=True)
sk = load_panel(STROKE)
check("panel is defined", sk.get("defined") is True)
check("label is the page's own", sk["label"] == "Stroke")

_sk_rule = B.SPECIALITY_RULES[STROKE]
_sk_rx = B.compile_rule(_sk_rule)

print("  a stroke is also a unit of cardiac output")
# THE ONE THAT MATTERS. "Stroke Central Monitor" is a row this panel carries, so
# patient monitoring notices do reach it. "stroke volume" appears more than forty
# times in the Hub's own supplier product data as a haemodynamic parameter (Deltex
# CardioQ-ODM, LiDCO, Cogent) and as a bag valve mask spec (Ambu Spur II). Without
# the exclusion the first such notice published lands on the stroke page.
for bad in ["Cardiac Output and Stroke Volume Monitoring",
            "Stroke Volume Variation Sensors and Consumables",
            "Oesophageal Doppler Monitor measuring Stroke Volume and Cardiac Output",
            "Supply of Bag Valve Masks (stroke volume 1500ml)"]:
    check("cardiac output row refused: %s" % bad[:50], not B.match_title(_sk_rx, bad))

print("  the words that belong to this pathway and to somebody else in this data")
# Every one of these is a real row that a wider draft matched and that was read
# and rejected on 10/09/2026.
for bad, why in [
        ("Patient Dry Wiping Cloths [5075392]", "cloth contains clot"),
        ("Framework Agreement for the Supply of Retrieval Packs", "organ retrieval, NHSBT"),
        ("South Thames Retrieval Service (STRS) Patient Transport Services",
         "paediatric retrieval transport"),
        ("LivaNova Essenz Perfusion Heart Lung System", "cardiac perfusion"),
        ("Contract Award Notice for the Provision of LifePort Perfusion Consumables",
         "kidney perfusion"),
        ("Framework Agreement for the Supply of Cold Static Perfusion Fluid UW Solution",
         "organ preservation"),
        ("NHS Golden Jubilee Cardiac Perfusion Consumables", "cardiac perfusion"),
        ("Genotyping Microarray Kits", "NHSBT red cell genotyping"),
        ("FOR THE SUPPLY OF  RCI GENOTYPING CONSUMABLES AND MAINTENANCE",
         "NHSBT immunohaematology"),
        ("WPL07040 - Neurology Insourcing", "neurology outpatient capacity"),
        ("Neurological Rehabilitation Service", "the rehabilitation page's"),
        ("Estates Capital Project - Trevor Gibbens Unit Strategic Outline Case",
         "Trevor is not Trevo"),
]:
    check("cut at the include stage (%s): %s" % (why[:34], bad[:38]),
          not B.match_title(_sk_rx, bad))

print("  and the eight rows that must be present, every one read on 10/09/2026")
for good in ["Stroke Central Monitor",
             "Interventional Neuro Radiology and Thrombectomy Consumables",
             "INR and Thrombectomy Consumables",
             "INTERVENTIONAL CARDIOLOGY, INTERVENTIONAL RADIOLOGY AND INTERVENTIONAL "
             "NEURORADIOLOGY, CARDIAC RHYTHM MANAGEMENT AND ELE",
             "Provision of Transport for Stroke and Suspected Stroke Patients",
             "Early Stroke Discharge Service",
             "Community Stroke Service for Newham (2026/27)",
             "City & Hackney Post Stroke Community Service"]:
    check("row carried: %s" % good[:52], B.match_title(_sk_rx, good))
check("exactly eight, and every one of them was read",
      sk["counts"]["awardsMatched"] == 8, "got %s" % sk["counts"]["awardsMatched"])
check("nothing is held back from the reader",
      sk["counts"]["awardsShown"] == sk["counts"]["awardsMatched"])

print("  no framework is counted, and the panel says which one it cannot count")
check("no framework claimed", sk["counts"]["frameworks"] == 0)
check("the framework list is genuinely empty", sk["frameworks"] == [])
check("the suppliers list is genuinely empty", sk["suppliers"] == [])
check("the rule declares the absence rather than faking it with a pattern",
      _sk_rule["frameworks"] is None)
# The default wording for "frameworks": None says every NHSSC framework name was
# read and none is this speciality's. That is true of obesity and paediatrics and
# FALSE here, so this rule overrides it. If the override is ever dropped the panel
# starts telling a member something untrue.
check("the false default sentence is not published",
      "none of them is this speciality's" not in sk["rules"]["frameworks"])
check("the true finding is published instead",
      "THE REASON IS NOT THAT NONE EXISTS" in sk["rules"]["frameworks"])
for phrase in ["2021/S 000-017565", "Interventional Neuroradiology", "unparsed",
               "26 February 2027", "Product Matrix", "12 February 2026",
               "Neuromodulation Devices", "Digital Diagnostic Solutions"]:
    check("frameworks finding carries: %s" % phrase[:44],
          phrase in sk["rules"]["frameworks"])
check("the suppliers tab explains its own emptiness",
      "publishes no supplier names" in sk["rules"]["suppliers"])

print("  the exclusion says where its evidence came from")
# Every other rule's exclusion list was derived from an award row. This one was
# not, and the published text has to say so rather than assert the house sentence.
check("the rule carries an exclusion list at all", bool(_sk_rule.get("exclude")))
check("the default award-row claim is not published",
      "every pattern in it matched a real notice" not in sk["rules"]["awards"])
check("the true provenance is published instead",
      "not derived from an award row" in sk["rules"]["awards"])

print("  no CPV family and no Drug Tariff part, both checked rather than skipped")
check("no CPV prefix claimed", not _sk_rule.get("cpv"))
check("every award was admitted by its title",
      all(B.match_title(_sk_rx, a["title"]) for a in sk["awards"]))
# The four service notices carry 85143000, 85121200, 85323000 and 85100000. All
# generic. If a stroke-specific CPV family ever appears this check still holds,
# but the rule should then be revisited rather than left alone.
_sk_cpv = sorted({c for a in sk["awards"] for c in (a.get("cpv") or [])})
check("only generic health service CPV codes are present",
      all(c.startswith("85") for c in _sk_cpv), ", ".join(_sk_cpv))
check("no Drug Tariff part is claimed", sk["drugTariff"] is None)
check("and the panel says why", "nothing on this patch is listed there"
      in sk["rules"]["drugTariff"])

print("  the two shared award notices are shared on purpose")
# The interventional radiology and neurology panels carry these too. That overlap
# is deliberate: the same notice really is bought by all three patches. If it ever
# stops appearing on the others, one of the rules has drifted.
_ir_titles = {a["title"] for a in load_panel(IR)["awards"]}
_nr_titles = {a["title"] for a in load_panel(NEURO)["awards"]}
check("interventional radiology still carries the thrombectomy consumables notice",
      "Interventional Neuro Radiology and Thrombectomy Consumables" in _ir_titles)
check("neurology still carries it too",
      "Interventional Neuro Radiology and Thrombectomy Consumables" in _nr_titles)
# And the divergence from the neurology rule is deliberate: neurology excludes the
# framework award notice because its page names five agreements and not that one.
check("neurology still refuses the interventional framework award",
      not any(t.upper().startswith("INTERVENTIONAL CARDIOLOGY") for t in _nr_titles))
check("stroke carries it, because this page names it as the buying route",
      any(a["title"].upper().startswith("INTERVENTIONAL CARDIOLOGY")
          for a in sk["awards"]))


# ---------------------------------------------------------------------------
# OPHTHALMOLOGY. Three dangers on this patch. The bare word "eye" is also
# personal protective equipment. Three of this rule's own terms land together on
# a university's small-animal research rig. And "OCT" is a coronary imaging
# catheter as often as it is a retinal scan. Against that, this is the first
# speciality since wound care whose Drug Tariff presence is substantial, and the
# page it feeds said in prose that it had none.
# ---------------------------------------------------------------------------
print("\nOPHTHALMOLOGY")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), OPHTH],
               check=True, capture_output=True)
op = load_panel(OPHTH)
check("panel is defined", op.get("defined") is True)
check("label is the page's own", op["label"] == "Ophthalmology")

_op_rule = B.SPECIALITY_RULES[OPHTH]
_op_rx = B.compile_rule(_op_rule)

print("  the three false positives, every one a real row read on 10/09/2026")
for bad, why in [
        ("Single Use Eye Protection", "PPE goggles and visors, SCCL"),
        ("QUB/2597/24 a Fully Integrated Small Animal In-Vivo Ophthalmic Retinal "
         "Ocular Imaging System", "preclinical research rig, QUB"),
        ("Intravascular Optical Coherence Tomography (OCT)", "coronary OCT, Golden Jubilee"),
]:
    check("refused (%s): %s" % (why[:32], bad[:40]), not B.match_title(_op_rx, bad))

print("  the terms refused from the include rather than argued with afterwards")
# Each of these is a real row in this data. None is ophthalmology, and none of
# them may ever be admitted by widening a term back out.
for bad, why in [
        ("Orthotics Service and Products Provision", "provision contains vision"),
        ("Provision of Wigs and Wig Services", "provision contains vision"),
        ("Optical Laser Fibre Consumables for CyberHo 100 Holmium Laser System (4839792)",
         "urology lithotripsy fibres"),
        ("Cook Optical Laser Fibres", "urology lithotripsy fibres"),
        ("Inductively Coupled Plasma Optical Emission Spectrometer (ICP-OES)",
         "analytical chemistry"),
        ("Bevacizumab IV Infusion Vials", "oncology IV, not intravitreal"),
]:
    check("cut at the include stage (%s): %s" % (why[:30], bad[:40]),
          not B.match_title(_op_rx, bad))

print("  and the rows that must be present, every one read on 10/09/2026")
for good in ["FTS - Complete Ophthalmology Solutions 3",
             "Intraocular Lenses, Viscoelastics & Phaco machines",
             "Vitreoretinal and Cataract Machines",
             "NHSE1060 Diabetic Eye Screening Programme",
             "Stable Glaucoma Monitoring in Surrey Downs - CAN",
             "Ru-106 Eye Applicators",
             "Aflibercept Intravitreal Prefilled Syringe",
             "NP33922 Ranibizumab",
             "NP90425 Faricimab (Vabysmo®)",
             "CARL ZEISS IOL MASTER 700 SYSTEM",
             "Purchase of Visual Field Analysers",
             "Low Vision Aid Supply and Recycling Services to WGOS - Low Vision"]:
    check("admitted: %s" % good[:52], B.match_title(_op_rx, good))

print("  the corneal tissue notices are wound care's false positive and this page's true one")
# "Supply of donated eye tissue used for corneal transplantation and other
# surgery" is one of the ten rows the loose `spec` field wrongly tags wound care.
# It is genuinely ophthalmology, and both halves of that have to stay true.
_op_titles = " || ".join((a.get("title") or "") for a in op["awards"]).lower()
check("ophthalmology carries the corneal transplantation notices",
      "corneal transplantation" in _op_titles)
check("wound care still refuses them",
      "corneal transplantation" not in
      " || ".join((a.get("title") or "") for a in d["awards"]).lower())

print("  aflibercept is admitted bare, and the reason it is safe is checked not assumed")
# Bare "aflibercept" is admitted because all six notices carrying it in this data
# are intravitreal. The oncology form is ziv-aflibercept or Zaltrap. If either
# string ever appears in a notice title, this rule needs an exclusion and this
# check is what says so.
_op_onc = [a["title"] for a in op["awards"]
           if "ziv-aflibercept" in a["title"].lower() or "zaltrap" in a["title"].lower()]
check("no oncology aflibercept notice has reached this panel", not _op_onc,
      "; ".join(_op_onc))
check("every award was admitted by its title",
      all(B.match_title(_op_rx, a["title"]) for a in op["awards"]))

print("  one framework, and it is the only one")
check("exactly one framework", len(op["frameworks"]) == 1,
      "got %d" % len(op["frameworks"]))
check("and it is Complete Ophthalmology Solutions 3",
      op["frameworks"][0]["name"] == "Complete Ophthalmology Solutions 3")
check("NHS Supply Chain's own supplier count is carried through unchanged",
      op["counts"]["suppliers"] == 53, "got %d" % op["counts"]["suppliers"])

print("  PART IXA IS NOT EMPTY ON THIS PATCH, WHICH THE PAGE PROSE HAD SAID IT WAS")
# Page 2831 stated in prose, when it was rebuilt on 10/09/2026, that "none of this
# speciality's product is dispensed on FP10 against Drug Tariff Part IX". NHSBSA's
# own Part IXA carries the entire community ocular surface range. The prose was
# corrected the same day. These are the numbers that were checked, and if the
# slice ever falls back to nothing the claim has to be revisited, not the check.
check("a Drug Tariff part is claimed", op["drugTariff"] is not None)
check("it is Part IXA", op["drugTariff"]["parts"] == ["IXA"])
check("the ocular surface range is present in full",
      op["drugTariff"]["vmpCount"] >= 80, "got %s" % op["drugTariff"]["vmpCount"])
check("over more than 200 reimbursement lines",
      op["drugTariff"]["lineCount"] >= 200, "got %s" % op["drugTariff"]["lineCount"])
check("prices are in pounds, not the pence NHSBSA publishes",
      op["drugTariff"]["priceMax"] < 100, "got %s" % op["drugTariff"]["priceMax"])
# The prefix form of the pattern exists for these two and nothing else.
_op_vmp = B.re.compile(_op_rule["tariffVmp"], B.re.I)
for good in ["Generic AccuSoft eyelid wipes", "Generic Blepha EyeBag",
             "Sodium hyaluronate 0.2% eye drops preservative free",
             "Artificial eye lubricants"]:
    check("tariff line selected: %s" % good[:44], bool(_op_vmp.search(good)))
# And nothing outside the eye range may ride in on it.
for bad in ["Artificial saliva gel", "Voice prosthesis cleaning brush",
            "Sodium hyaluronate 40mg/20ml intravesical solution pre-filled syringes",
            "Sodium hyaluronate cream"]:
    check("tariff line refused: %s" % bad[:44], not _op_vmp.search(bad))


# ---------------------------------------------------------------------------
# CRITICAL CARE (page 2826). Added 10/09/2026.
# The patch is ITU and HDU: organ support, patient monitoring, infusion and
# continuous renal replacement. Nearly every term on it has a loose form that is
# a false-positive nest, so most of the work is in what the include list refuses.
# ---------------------------------------------------------------------------
cc = load_panel(CC)
check("critical care panel exists", cc is not None)
if cc:
    _cc_rule = B.SPECIALITY_RULES[CC]
    _cc_rx = B.compile_rule(_cc_rule)

    print("  the six real rows the include list let through that are NOT critical care")
    # Each of these matched the include pattern in this data and was read and found
    # wrong. They are why the exclusion list exists at all.
    for bad, why in [
            ("For the Supply of ITU Medicine  Covid-19 Preparedness - Propofol "
             "1g/50ml emulsion for infusion vial.", "DHSC pharmacy stockpile, not hardware"),
            ("ITU  Medicines and  End  of  Life Care Medicines for Covid-19 preparedness.",
             "DHSC pharmacy stockpile"),
            ("Supportive Medicines - additional products (ITU, Antibiotics & EOI medicines)",
             "DHSC pharmacy stockpile"),
            ("Insulin Infusion Pumps, Continuous Glucose Monitoring Systems and "
             "Associated Consumables", "diabetes device, its own NHSSC framework"),
            ("Non-Invasive CPAP Ventilators", "respiratory's NIV and sleep framework"),
            ("North Staffordshire Combined Healthcare NHS Trust Out of Area "
             "Psychiatric Intensive Care (PICU) Placement", "mental health bed placement"),
    ]:
        check("excluded (%s): %s" % (why[:34], bad[:40]), not B.match_title(_cc_rx, bad))

    print("  and the loose terms refused from the include rather than argued with after")
    # Every one of these is a real row in this data. None is critical care, and none
    # of them may ever be admitted by widening a term back out.
    for bad, why in [
            ("Ventilation Verification", "building HVAC validation, Hillingdon"),
            ("Provision of Ventilation and Other Remediation Works", "building works"),
            ("Multiparameter Sondes for Fresh Water Monitoring", "water quality, Exeter"),
            ("SCE0076- High Dependency Bed Service", "social care placements, Leicester CC"),
            ("Manuals / Registrations for Advanced Paediatric Life Support Courses.",
             "course manuals"),
            ("Diving Life Support (DLS) In-Service Support (ISS)", "Defence Equipment"),
            ("Support of existing NHSBT owned Extracorporeal Photopheresis (ECP) Systems",
             "photopheresis, not ECMO"),
            ("Monitoring devices for continuous measurement of blood parameters during "
             "extracorporeal circulation", "cardiopulmonary bypass"),
            ("Suction Consumables", "general ward and theatre suction"),
            ("BSP-25-003 SUPPLY OF AUTOMATED EXTERNAL DEFIBRILLATORS (AED) AND ANCILLARIES",
             "school AEDs, Education Authority"),
            ("Airway Management", "theatres and respiratory's framework"),
            ("Supply of Replacement Blood Gas Analysers and Consumables", "pathology"),
            ("Remote Monitoring of Vital Signs", "council telecare, Dumfries and Galloway"),
    ]:
        check("cut at the include stage (%s): %s" % (why[:30], bad[:38]),
              not B.match_title(_cc_rx, bad))

    print("  the sixteen drug rows that bare \"infusion\" would have admitted")
    # 30 rows in tender-history.json carry "infusion" and over half of them are the
    # phrase "solution for infusion" on a pharmacy buy. The include names the device
    # forms individually for exactly this reason.
    for bad in ["NIVOLUMAB 240MG/RELATLIMAB 80MG (OPDUALAG ) Solution for Infusion 1 Vial Pack",
                "LONCASTUXIMAB 10 mg Powder for Soln for Infusion 1 Vial Box",
                "Ravulizumab IV Infusion",
                "Ciprofloxacin solution for infusion 2024",
                "Generic Drugs - Injections/Infusions",
                "ZOLGENSMA 2 X 10 EXP 13 VECTOR GENOMES/ML Solution for Infusion 1 Treatment Pack Pack",
                "Supply, Storage, and Maintenance of Glucose 10% and 50% 500ml iv infusion",
                "Procurement of ANDEXANET ALFA Powder for Soln for Infusion from Alexion Pharma UK",
                "Bevacizumab IV Infusion Vials",
                "IV Cannulae and Associated Infusion Set (5973078)"]:
        check("no drug or cannula row: %s" % bad[:46], not B.match_title(_cc_rx, bad))

    print("  and the rows that must be present, every one read on 10/09/2026")
    for good in ["Supply of Critical Care Ventilators and Associated Support Services "
                 "(Dräger Evita V800)",
                 "Intensive Care Ventilator Circuits (3510059)",
                 "Capital Purchase of Hamilton T1 Transport Ventilator",
                 "ITU Haemofiltration Machines, Fluids and Consumables",
                 "Continuous Renal Replacement Therapies (CRRT) Consumables",
                 "Purchase of ECMO Trolley",
                 "Patient Monitoring Equipment, Bedside Equipment Alarm Monitoring "
                 "Systems and Related Products and Services",
                 "Pulse Oximetry, Capnography and Related Patient Monitoring Technologies",
                 "Infusion Pumps, Syringe Pumps, Administration Sets and Associated Equipment",
                 "Sterile Closed Tracheal Suction Systems (3225312)",
                 "Tracheostomy Tubes, Tube Holders and Accessories - 5806781",
                 "Vital Signs Monitors and Associated Equipment"]:
        check("admitted: %s" % good[:52], B.match_title(_cc_rx, good))

    check("every award was admitted by its title",
          all(B.match_title(_cc_rx, a["title"]) for a in cc["awards"]))
    _cc_titles = " || ".join((a.get("title") or "") for a in cc["awards"]).lower()
    check("no \"solution for infusion\" pharmacy row reached the panel",
          "solution for infusion" not in _cc_titles)
    check("no psychiatric intensive care placement reached the panel",
          "psychiatric" not in _cc_titles)

    print("  four frameworks, the four the page's own scope and calendar name")
    check("exactly four frameworks", len(cc["frameworks"]) == 4,
          "got %d" % len(cc["frameworks"]))
    _cc_fw = sorted(f["name"] for f in cc["frameworks"])
    for want in ["Anaesthesia Machines, Ventilators, Neonatal Equipment",
                 "Infusion Pumps and Administration Sets",
                 "Patient Monitoring Equipment, Bedside Equipment Alarm Monitoring",
                 "Renal Replacement Therapies Services, Technologies and Consumables"]:
        check("framework carried: %s" % want[:50],
              any(n.startswith(want) for n in _cc_fw))
    # The page's calendar prints these four gold expiry dates. If frameworks.json
    # ever disagrees with the page, one of the two is wrong and it has to be looked
    # at, not smoothed over.
    _cc_ends = {f["name"][:24]: f.get("ends") for f in cc["frameworks"]}
    for key, when in [("Infusion Pumps and Admin", "30 September 2026"),
                      ("Renal Replacement Therap", "27 March 2028"),
                      ("Patient Monitoring Equip", "7 June 2028"),
                      ("Anaesthesia Machines, Ve", "28 February 2029")]:
        check("expiry still matches the page's calendar: %s" % key,
              _cc_ends.get(key) == when, "got %s" % _cc_ends.get(key))
    # The oximetry and capnography framework is deliberately NOT counted here, and
    # that omission is recorded in the published coverage note rather than hidden.
    check("the pulse oximetry framework is not silently counted",
          not any("Pulse Oximetry" in f["name"] for f in cc["frameworks"]))
    check("and the coverage note says so in the published file",
          "Pulse Oximetry" in (cc["rules"]["frameworks"] or ""))

    print("  no Drug Tariff part, and that is a finding")
    # Part IX reimburses dressings, hosiery, incontinence and stoma appliances
    # dispensed in the community. Ventilators, monitors, infusion pumps and CRRT
    # machines are hospital capital and appear nowhere in it.
    check("no tariff is claimed", cc["drugTariff"] is None)
    check("and the published rule says why",
          "No Drug Tariff part applies" in cc["rules"]["drugTariff"])
    check("suppliers come only from the four frameworks",
          cc["counts"]["suppliers"] > 0 and
          all(s.get("frameworks") for s in cc["suppliers"]))


# ---------------------------------------------------------------------------
# ENT AND HEAD AND NECK. Three dangers, and the first is not a false positive at
# all. This patch borders audiology so closely that eight genuine purchases on
# the same clinical territory belong to the neighbouring page, so the boundary
# has to be enforced by a test or it will drift back. The second is the word
# laryngoscope, which reaches the emergency department and the anaesthetic room
# far more often than it reaches ENT. The third is that a nasal cannula is oxygen
# therapy.
# ---------------------------------------------------------------------------
print("\nENT AND HEAD AND NECK")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), ENT],
               check=True, capture_output=True)
en = load_panel(ENT)
check("panel is defined", en.get("defined") is True)
check("label is the page's own", en["label"] == "ENT and Head and Neck")

_en_rule = B.SPECIALITY_RULES[ENT]
_en_rx = B.compile_rule(_en_rule)

print("  the one false positive, a real row read on 10/09/2026")
check("refused (oxygen therapy, DHSC): nasal cannula pandemic stock",
      not B.match_title(_en_rx,
          "The supply of Nasal Cannula & Oxygen Masks for Pandemic Preparedness 24/25"))

print("  the laryngoscope rows, refused from the include not argued with after")
# All five are real rows in tender-history.json. The intubating laryngoscope and
# the ENT rhino-laryngoscope share a word and nothing else. If any of these ever
# starts matching, the include has been widened and this patch has quietly
# annexed the airway.
for bad in ["ED C-MAC Video Laryngoscope",
            "ESNEFT3113 Purchase of Video Laryngoscopes",
            "ESNEFT Purchase of Video Laryngoscopes",
            "Laryngoscope Blades and Associated Consumables",
            "Laryngoscope Handles and Blades"]:
    check("refused (airway, not ENT): %s" % bad[:44], not B.match_title(_en_rx, bad))

print("  the audiology boundary — genuine purchases that are the other page's")
# These are NOT wrong matches. Every one is a real purchase on this clinical
# territory, and each belongs to audiology-and-hearing because that page owns the
# Audiological Diagnostics Implantable Devices and Services framework. The
# boundary is a decision, so it gets a test.
for other in ["Hearing Aid Batteries",
              "Audiology Products",
              "981 - Audiology Equipment",
              "Audiological Equipment",
              "Audiological Diagnostics, Implantable Devices, Accessories & Services 2024",
              "Cochlear Implants and Accessories",
              "Hearing Aids, Hearing Aid Batteries, Custom Ear Moulds and Hearing Aid Accessories",
              "Preliminary Market Engagement Questionnaire for Cochlear Implants and Accessories"]:
    check("left to audiology: %s" % other[:44], not B.match_title(_en_rx, other))

print("  and the rows that must keep reaching it")
for good in ["WSFT - Capital Purchase - ENT - Disinfection equipment incl Warranty device",
             "WSFT - ENT - Werewolf Generator service contract",
             "Purchase of Nasendoscopes",
             "ESNEFT2730 Purchase of ENT Laser",
             "ESNEFT2728 Purchase of ENT Microscope for Theatre",
             "Tracheostomy Tubes, Tube Holders and Accessories - 5806781",
             "ENT, Ophthalmology & Skin Medicines/Medical Devices",
             "Provision of Bespoke Dental Implants",
             "Provision of 3D Dental Implants",
             "NP14220 Neonatal and Paediatric Tracheostomy Tubes",
             "ENT Outsourcing",
             "WPL06900 - Urology and OMFS Insourcing"]:
    check("admitted: %s" % good[:52], B.match_title(_en_rx, good))

check("every award was admitted by its title",
      all(B.match_title(_en_rx, a["title"]) for a in en["awards"]))
_en_titles = " || ".join((a.get("title") or "") for a in en["awards"]).lower()
check("no laryngoscope row reached the panel", "laryngoscop" not in _en_titles)
check("no audiology row reached the panel",
      "audiolog" not in _en_titles and "hearing" not in _en_titles
      and "cochlear" not in _en_titles)

print("  two frameworks, and the third is refused upstream on purpose")
check("exactly two frameworks", len(en["frameworks"]) == 2,
      "got %d" % len(en["frameworks"]))
_en_fw = sorted(f["name"] for f in en["frameworks"])
for want in ["Ear, Nose and Throat (ENT) Endoscopes",
             "Rigid Endoscopy and Associated Options"]:
    check("framework carried: %s" % want[:48],
          any(n.startswith(want) for n in _en_fw))
# frameworks.json holds the Dental Technologies brief in `unparsed` because NHS
# Supply Chain's own page states 33 suppliers and 35 parse. That refusal is the
# gate working, and the published coverage note has to keep saying so.
check("Dental Technologies is not silently counted",
      not any("Dental Technologies" in f["name"] for f in en["frameworks"]))
check("and the published rule says why it is missing",
      "Dental Technologies" in (en["rules"]["frameworks"] or ""))
# The ENT framework carries the flexible and video scopes and 7 suppliers; the
# rigid ENT set is on a framework that does not say ENT in its name and carries
# 18. If either count moves, the page's own prose is wrong too.
def _en_count(prefix):
    for f in en["frameworks"]:
        if f["name"].startswith(prefix):
            return f.get("supplierCount")
    return None
check("ENT Endoscopes still names 7 suppliers",
      _en_count("Ear, Nose and Throat (ENT)") == 7,
      "got %s" % _en_count("Ear, Nose and Throat (ENT)"))
check("Rigid Endoscopy still names 18 suppliers",
      _en_count("Rigid Endoscopy") == 18,
      "got %s" % _en_count("Rigid Endoscopy"))
check("both still end 31 March 2028",
      all(f.get("ends") == "31 March 2028" for f in en["frameworks"]))

print("  the Drug Tariff slice, and the ostomy range it must never eat")
_en_t = en["drugTariff"]
check("Part IXA only", _en_t["parts"] == ["IXA"])
check("645 lines from 19 virtual products",
      _en_t["lineCount"] == 645 and _en_t["vmpCount"] == 19,
      "got %s lines / %s vmps" % (_en_t["lineCount"], _en_t["vmpCount"]))
check("31 suppliers", _en_t["supplierCount"] == 31, "got %s" % _en_t["supplierCount"])
check("Severn Healthcare leads it",
      _en_t["topSuppliers"][0]["name"] == "Severn Healthcare Technologies Ltd")
# Stoma caps were tested and refused: all 14 lines are Part IXC ostomy appliances
# (Assura Minicap, Nova MiniCap, Confidence Gold), not laryngectomy stoma covers.
import re as _en_re
_en_vrx = _en_re.compile(_en_rule["tariffVmp"], _en_re.I)
for bad in ["Stoma caps", "Ostomy bag covers", "Ileostomy bags", "Ostomy belts",
            "Lymphoedema garments thigh length open toe with waist/hip attachment",
            "Incontinence sheaths", "Peak flow meter standard range"]:
    check("tariff filter refuses: %s" % bad[:44], not _en_vrx.search(bad))
for good in ["Tracheostomy breathing aids", "Voice prosthesis cleaning brush",
             "Auto inflation device", "Olive oil ear drops", "Nasal aspirator"]:
    check("tariff filter admits: %s" % good[:44], bool(_en_vrx.search(good)))
check("the overlap with respiratory is published, not hidden",
      "respiratory" in (en["rules"].get("drugTariff") or "").lower()
      or "RESPIRATORY" in (en["rules"].get("frameworks") or ""))
check("suppliers come only from the two frameworks",
      en["counts"]["suppliers"] > 0 and
      all(s.get("frameworks") for s in en["suppliers"]))



# ---------------------------------------------------------------------------
# AUDIOLOGY AND HEARING. Four dangers, and only one of them is an ordinary false
# positive. The first is the word "audio", which in this data reaches a
# government department's conference AV contract. The second is that the CPV code
# for audiology services, 85121240, sits on that same AV contract and inside two
# 25-code baskets, so this patch is the sharpest proof in the dataset that CPV
# must corroborate and never admit. The third is the border with ENT: this page
# owns hearing and balance, that page owns ear surgery, and both rules have to
# hold the line from their own side. The fourth is the supplier count, where one
# company is named twice because the Hub's seed carries it as two records.
# ---------------------------------------------------------------------------
print("\nAUDIOLOGY AND HEARING")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), AUDIO],
               check=True, capture_output=True)
au = load_panel(AUDIO)
check("panel is defined", au.get("defined") is True)
check("label is the page's own", au["label"] == "Audiology and Hearing")

_au_rule = B.SPECIALITY_RULES[AUDIO]
_au_rx = B.compile_rule(_au_rule)

print("  the one false positive, a real row read on 10/09/2026")
# Mersey and West Lancashire Teaching Hospitals, CPV 80561000 — health training
# services. It reached the panel on "deaf" and it is workforce education, not a
# purchase of hearing products or a commissioned hearing service.
check("refused (staff training, not a hearing purchase): Deaf Awareness Training Courses",
      not B.match_title(_au_rx, "Deaf Awareness Training Courses"))
# ...and the row "deaf" was admitted for must keep reaching the panel, or the
# exclusion has been widened into the thing it was meant to protect.
check("but deaf people's equipment still reaches it",
      B.match_title(_au_rx, "HH072-25-HB Specialist Environmental Aids for Deaf People"))

print("  bare audio, refused from the include and not argued with afterwards")
check("refused (a conference, DESNZ): Audio Visual (AV) Event Support",
      not B.match_title(_au_rx, "Audio Visual (AV) Event Support For International Conference"))

print("  bare sound would annex every ultrasound row in the dataset")
for bad in ["Philips Epiq Elite Diagnostic Ultrasound for Breast Clinic CHH",
            "0P002146 Fujifilm Sonosite Ultrasound machine ED SRH - Direct Award Purchase",
            "PROJ007278_Replacement of Trans-Rectal Ultrasound Scanner",
            "TE9 Portable Diagnostic Ultrasound System",
            "GE bkActiv Ultrasound"]:
    check("refused (imaging, not hearing): %s" % bad[:44], not B.match_title(_au_rx, bad))

print("  bare implant would annex orthopaedics and cardiology")
for bad in ["Foot & Ankle Implants", "KGH Lot 1.5 Trauma Implants Medartis",
            "Orthopaedic Ankle Replacement Implants", "IMPLANTABLE LOOP RECORDER",
            "Provision of Bespoke Dental Implants"]:
    check("refused (another patch's implant): %s" % bad[:44], not B.match_title(_au_rx, bad))
# IMPLANTABLE LOOP RECORDER is in that list for a second reason: this include
# carries "hearing loop" and "induction loop" but never a bare "loop", and a
# cardiac loop recorder is what a bare one would reach first.

print("  speech and language therapy is a neighbouring service, not this one")
for bad in ["Provision of 'Experts at Hand' Educational Psychologists, Speech and Language "
            "and Occupational Therapy Support - Market Engagement",
            "Experts at Hand Sheffield - Speech and Language Therapy and Occupational Therapy"]:
    check("refused (SLT, not audiology): %s" % bad[:44], not B.match_title(_au_rx, bad))

print("  the ENT border, held from this side too")
# The mirror of the audiology boundary test on the ENT rule. These are genuine
# purchases on the neighbouring page's patch — ear surgery, not hearing — and if
# any of them starts matching, this page has annexed the operating theatre.
for other in ["WSFT - Capital Purchase - ENT - Disinfection equipment incl Warranty device",
              "WSFT - ENT - Werewolf Generator service contract",
              "ESNEFT2730 Purchase of ENT Laser",
              "ESNEFT2728 Purchase of ENT Microscope for Theatre",
              "ENT, Ophthalmology & Skin Medicines/Medical Devices",
              "ENT Outsourcing",
              "Purchase of Nasendoscopes",
              "Tracheostomy Tubes, Tube Holders and Accessories - 5806781"]:
    check("left to ENT: %s" % other[:44], not B.match_title(_au_rx, other))

print("  and the rows that must keep reaching it")
for good in ["Hearing Aid Batteries",
             "Audiology Products",
             "981 - Audiology Equipment",
             "Audiological Equipment",
             "Audiological Diagnostics, Implantable Devices, Accessories & Services 2024",
             "Cochlear Implants and Accessories",
             "Hearing Aids, Hearing Aid Batteries, Custom Ear Moulds and Hearing Aid Accessories",
             "Preliminary Market Engagement Questionnaire for Cochlear Implants and Accessories",
             "Adult Community Audiology Services",
             "Community Audiology - NHS Birmingham and Solihull ICB",
             "Diatec - calibration of Audiology equipment",
             "Bone Conduction",
             "Audiology"]:
    check("admitted: %s" % good[:52], B.match_title(_au_rx, good))

check("every award was admitted by its title",
      all(B.match_title(_au_rx, a["title"]) for a in au["awards"]))
check("16 awards matched and all 16 are shown",
      au["counts"]["awardsMatched"] == 16 and au["counts"]["awardsShown"] == 16,
      "got %s matched / %s shown" % (au["counts"]["awardsMatched"], au["counts"]["awardsShown"]))
_au_titles = " || ".join((a.get("title") or "") for a in au["awards"]).lower()
check("no ultrasound row reached the panel", "ultrasound" not in _au_titles)
check("no audio visual row reached the panel", "audio visual" not in _au_titles)
check("no deaf awareness row reached the panel", "deaf awareness" not in _au_titles)

print("  CPV corroborates and never admits — the proof case for the whole dataset")
# 85121240 is the ENT-or-audiology-services code and it really does sit on a
# Department for Energy Security and Net Zero conference AV contract. If CPV ever
# starts admitting, that notice is published to a paying member as audiology.
check("85121240 is carried as corroboration", "85121240" in tuple(_au_rule["cpv"]))
check("33185200, cochlear implant, is carried too", "33185200" in tuple(_au_rule["cpv"]))
check("but the AV conference row is still refused on its title",
      not B.match_title(_au_rx, "Audio Visual (AV) Event Support For International Conference"))
check("and so are the 25-code baskets",
      not B.match_title(_au_rx, "Employee Benefits and Occupational Health Services")
      and not B.match_title(_au_rx,
          "Provision of Insourced and Outsourced Clinical Services Framework (Framework Reopening)"))

print("  two frameworks, and the one with 'ear' in its name is not one of them")
check("exactly two frameworks", len(au["frameworks"]) == 2,
      "got %d" % len(au["frameworks"]))
_au_fw = sorted(f["name"] for f in au["frameworks"])
check("Audiological Diagnostics is carried",
      any(n.startswith("Audiological Diagnostics Implantable Devices") for n in _au_fw))
check("Hearing Aids, Batteries and Custom Ear Moulds is carried",
      any(n.startswith("Hearing Aids, Hearing Aid Batteries") for n in _au_fw))
# The ENT endoscopes framework is the only other NHSSC name carrying "ear". It is
# ENT surgery's and that page claims it explicitly. Two pages claiming one
# framework is sometimes correct — Rigid Endoscopy is on ENT and urology both —
# but this is not one of those, and the pattern is written so it cannot reach it.
check("ENT Endoscopes is NOT claimed here",
      not any("Ear, Nose and Throat" in f["name"] for f in au["frameworks"]))

def _au_count(prefix):
    for f in au["frameworks"]:
        if f["name"].startswith(prefix):
            return f.get("supplierCount")
    return None
# Both counts are verified against NHS Supply Chain's own stated total on the
# brief. If either moves, the brief has been reissued and the page's prose needs
# re-reading before it publishes again.
check("Audiological Diagnostics still names 15 suppliers",
      _au_count("Audiological Diagnostics") == 15, "got %s" % _au_count("Audiological Diagnostics"))
check("Hearing Aids still names 13 suppliers",
      _au_count("Hearing Aids, Hearing Aid Batteries") == 13,
      "got %s" % _au_count("Hearing Aids, Hearing Aid Batteries"))
# The two end dates are the page's whole news story: the agreements expire
# thirteen months apart and the successor is not awarded.
_au_ends = sorted(f.get("ends") or "" for f in au["frameworks"])
check("the two end dates are still 1 April 2028 and 26 March 2027",
      _au_ends == ["1 April 2028", "26 March 2027"], "got %s" % _au_ends)

print("  no Drug Tariff, and that is measured rather than assumed")
# All 66,400 lines of Part IX were searched for hearing, audiolog, cochlear,
# tinnitus, ear mould, auditory and deaf. The answer is zero: hearing aids,
# batteries, earmoulds and implants are hospital-supplied, not FP10-reimbursed.
check("no tariff part is claimed", _au_rule.get("tariffParts") is None)
check("and the panel carries none", au.get("drugTariff") is None)
check("the published rule says why rather than going quiet",
      "Part IX" in (au["rules"].get("drugTariff") or ""))

print("  the supplier count, and the one company that is named twice")
check("no supplier name failed to resolve", au["counts"]["suppliersUnresolved"] == 0)
check("suppliers come only from the two frameworks",
      au["counts"]["suppliers"] > 0 and all(s.get("frameworks") for s in au["suppliers"]))
_au_names = {s["name"] for s in au["suppliers"]}
for want in ["Advanced Bionics", "Cochlear Europe", "MED-EL", "Oticon", "Puretone"]:
    check("supplier carried: %s" % want, want in _au_names)
# Companies House 00203774 was SIEMENS HEARING INSTRUMENTS LTD, became SIVANTOS
# LIMITED on 20/03/2015 and has been WS AUDIOLOGY LIMITED since 29/09/2022. NHS
# Supply Chain named it Sivantos on the 2022 agreement and WS Audiology on the
# 2024 one, which is right for each signing date. The Hub's supplier seed holds
# the two names as two supplier records, so the alias registry cannot merge them
# and the panel shows 25 entries for 24 companies. That is disclosed in the
# published file, and this test fails if the disclosure is ever dropped while the
# duplicate is still there.
_au_dup = {"WS Audiology", "Sivantos Limited"} <= _au_names
check("the seed still carries 00203774 under both its names", _au_dup)
if _au_dup:
    check("and the panel says so in its own published text",
          "Sivantos" in (au["rules"]["suppliers"] or "")
          and "00203774" in (au["rules"]["suppliers"] or ""))
    check("25 entries for 24 companies", au["counts"]["suppliers"] == 25,
          "got %s" % au["counts"]["suppliers"])

print("  open tenders — empty is the honest answer, not a miss")
check("no open notice on this patch today", au["openTenders"] == [])
check("and the rule says an empty list means none was open, not none was sought",
      "empty" in (au["rules"].get("openTenders") or "").lower())



# ---------------------------------------------------------------------------
# COLORECTAL, GI AND ENDOSCOPY. Four dangers. The first is that "endoscopy" is a
# technique, not a speciality: the same word buys a colonoscope, an arthroscope,
# a nasendoscope and a saphenous vein harvesting system, and only one of those is
# this patch. The second is the letters FIT, which are the most important test on
# this page and also the ordinary English word in "Supply and Fit including
# Styling of Wigs". The third is the border with continence, which owns bowel
# management and the catheter while this page owns bowel screening and the stoma,
# with Part IXC deliberately claimed by both. The fourth is Part IX itself: this
# is the second largest tariff patch in the dataset and claiming one part too
# many would put catheter suppliers at the top of a colorectal panel.
# ---------------------------------------------------------------------------
print("\nCOLORECTAL, GI AND ENDOSCOPY")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), COLO],
               check=True, capture_output=True)
co = load_panel(COLO)
check("panel is defined", co.get("defined") is True)
check("label is the page's own", co["label"] == "Colorectal, GI and Endoscopy")

_co_rule = B.SPECIALITY_RULES[COLO]
_co_rx = B.compile_rule(_co_rule)

print("  the false positives, every one a real row read on 11/09/2026")
# NHS Golden Jubilee, both of them. Endoscopic saphenous vein harvesting is how
# the conduit for a coronary artery bypass graft is taken. It is cardiac surgery
# and it reached this panel on the word "endoscopic".
for bad in ["NHSGJ0089/22 Supply of Endoscopic Vessel Harvesting Tools and Associated Consumables",
            "NHSGJ0098/22 Supply of Table Attached Compact Display Monitor for Endoscopic "
            "Vessel Harvesting System"]:
    check("refused (cardiac surgery): %s" % bad[:52], not B.match_title(_co_rx, bad))
# Birmingham Women's and Children's. Infant craniosynostosis surgery and the
# moulding helmets worn afterwards, matched on "endoscopic-assisted".
check("refused (infant neurosurgery): Craniofacial Orthotics and Helmet Therapy",
      not B.match_title(_co_rx,
          "Pre-Market Engagement for Craniofacial Orthotics and Helmet Therapy Services for "
          "Endoscopic-Assisted Suturectomy Patients and Craniofacial Orthotist Services"))
# NOTHING IS REFUSED FOR BEING RIGID RATHER THAN FLEXIBLE, and the first version
# of this rule got that wrong on 11/09/2026: it excluded NHS Scotland's rigid
# endoscopy award as arthroscopy while the panel's own Frameworks tab published
# the Rigid Endoscopy framework as this patch's scope route. NHS Supply Chain
# publishes Flexible Endoscopes and Rigid Endoscopy under ONE reference, 2021/S
# 000-007768, and the page's Deep dive says so. One position, not two.
for good in ["Rigid Endoscopy Equipment, Accessories and Maintenance and Repair",
             "Flexible Video, Capsule & Rigid Endoscopy Equipment Including Accessories, "
             "Maintenance and Repair",
             "Flexible Video Endoscopy Equipment Including Maintenance and Capsule Endoscopy"]:
    check("scope awards reach it, rigid and flexible alike: %s" % good[:44],
          B.match_title(_co_rx, good))
# NHS Scotland, Kent Pharmaceuticals. Genuinely gastrointestinal and genuinely
# not this panel: one pharmacy wholesale award across four therapeutic areas.
check("refused (pharmacy wholesale): Gastrointestinal, Endocrine, Nutrition & Blood Medicines",
      not B.match_title(_co_rx, "Gastrointestinal, Endocrine, Nutrition & Blood Medicines"))
# Somerset, from Aquilant Endoscopy. Refused because the title cannot say whether
# it is unsedated upper GI endoscopy or ENT nasendoscopy — not because it was
# shown to be ENT. That difference is published, and this checks it still is.
check("refused (unattributable): Purchase of transnasal endoscopes and accessories",
      not B.match_title(_co_rx, "Purchase of transnasal endoscopes and accessories"))
check("and the panel publishes WHY that one differs from the other four",
      "could not be attributed" in (co["rules"].get("awards") or ""))

print("  bare FIT is the most dangerous three letters in the dataset")
for bad in ["Supply and Fit including Styling of Wigs Service",
            "16_26 Flooring (Supply, Fit and Refurbishment)",
            "Supply, Delivery and Fitting of Wigs"]:
    check("refused (the ordinary English word): %s" % bad[:44], not B.match_title(_co_rx, bad))
for good in ["NHS Scotland Bowel Screening FIT Kits, Distribution and Analysers",
             "Faecal Immunochemical Testing (FIT) to provide support for patients identified "
             "with symptoms associated with bowel cancer"]:
    check("but the FIT pathway still reaches it: %s" % good[:44], B.match_title(_co_rx, good))

print("  the continence border, held from this side")
# Faecal management systems are bowel containment for a bedbound patient and the
# continence page claims them by name. Bare "faecal" would annex them.
for other in ["Faecal Management System", "Faecal Management Systems",
              "NP57122 Supply and Delivery of Continence Products",
              "Bulk Delivery of Continence Products for Community Services",
              "Continence Home Delivery - Brent CLCH"]:
    check("left to continence: %s" % other[:44], not B.match_title(_co_rx, other))

print("  bare scope would annex three other pages")
for bad in ["Replacement of Hysteroscopy Scopes", "Scopes Model 11272VH",
            "Scope Application service level agreement", "Flexible Scopes"]:
    check("refused (cannot be attributed from the title): %s" % bad[:44],
          not B.match_title(_co_rx, bad))

print("  the words refused on risk, each with the thing it would reach")
# polypropylene is surgical mesh and suture; trans-oesophageal echo is cardiology;
# the gastric band is the obesity page's; laparoscopy and trans-rectal ultrasound
# are theatres and urology; instrument washer-disinfectors are sterile services.
for bad in ["Polypropylene Mesh and Fixation Devices",
            "Trans-oesophageal Echocardiography Probes",
            "Gastric Band Adjustment Service",
            "Laparoscopic Ligation Clips & Appliers",
            "Contract for Laparoscopic Sets Service Agreement",
            "PROJ007278_Replacement of Trans-Rectal Ultrasound Scanner",
            "AA-84-22-MC NP143/21 Instrument Washer Disinfectors",
            "Washer Disinfector Units Maintenance (202-134 & 202-135)",
            "Maintenance of Fibroscan machines",
            "Outpatient Network Hepatology Insourcing",
            "Provision of Enteral Feeding Pumps, Feeds and Consumables to Hospital Sites"]:
    check("refused (another patch): %s" % bad[:48], not B.match_title(_co_rx, bad))
# ...and the two endoscope washer contracts that DO say endoscope must stay.
for good in ["Automated Endoscope Washer Disinfectors",
             "Service, Validation and weekly testing of Poka Yoke Endoscope Washers",
             "[3807864] - Spare Parts for Cantel RapidAER Endoscope Washer Disinfector, "
             "Cantel EDC10T2 Endoscope Drying Cabinet and Supporting Products"]:
    check("but endoscope decontamination still reaches it: %s" % good[:44],
          B.match_title(_co_rx, good))

print("  and the rows that must keep reaching it")
for good in ["Endoscopy, Endourology & Oncology Ablation Consumables & Associated Products",
             "Colon Capsule Endoscopy (CCE)",
             "NHSS Bowel Screening Test Kits and Analysers",
             "Insourcing of Bowel Screening and General Endoscopy Services at Aneurin Bevan "
             "University Health Board",
             "Outpatient Network Gastroenterology Insourcing",
             "Co-Developing the 'Digestive Disease Centre' at University Hospital Southampton",
             "Stoma Acute Patient",
             "National Framework Agreement for the Provision of Prescription Hub Services "
             "(Stoma and/or Catheter)",
             "Purchase of Flexible Endoscopes",
             "EVIS X1 Endoscopic Imaging System",
             "Wireless Capsule Endoscopy Equipment and Capsules [3498209]"]:
    check("admitted: %s" % good[:52], B.match_title(_co_rx, good))

check("every award was admitted by its title",
      all(B.match_title(_co_rx, a["title"]) for a in co["awards"]))
check("40 awards matched and all 40 are shown",
      co["counts"]["awardsMatched"] == 40 and co["counts"]["awardsShown"] == 40,
      "got %s matched / %s shown" % (co["counts"]["awardsMatched"], co["counts"]["awardsShown"]))
_co_titles = " || ".join((a.get("title") or "") for a in co["awards"]).lower()
for gone in ["vessel harvesting", "craniofacial", "transnasal", "wigs", "flooring",
             "faecal management", "hysteroscopy"]:
    check("no %s row reached the panel" % gone, gone not in _co_titles)
check("the rigid scope award DID reach it",
      "rigid endoscopy equipment, accessories" in _co_titles)

print("  CPV corroborates and never admits")
# 33168000 and 33168100 are the endoscopy and endoscope codes, and across the
# whole award feed the 33168 family also sits on Total Orthopaedic Solutions 4
# and on Minimally Invasive Surgery. Admitted on CPV, this panel would open with
# an orthopaedic implant framework.
check("33168 is carried as corroboration", "33168" in tuple(_co_rule["cpv"]))
check("but the orthopaedic framework carrying the same code is refused on its title",
      not B.match_title(_co_rx, "Total Orthopaedic Solutions 4"))
check("and so is the laparoscopy framework carrying it",
      not B.match_title(_co_rx, "Minimally Invasive Surgery"))

print("  five frameworks — the five the page's own Deep dive names, no more and no fewer")
# THE PAGE IS THE AUTHORITY HERE AND THIS TEST EXISTS BECAUSE THE PANEL ONCE
# DISAGREED WITH IT. Page 2830's Deep dive carries a section headed "The buying
# route, exactly — five agreements, and one of them is not a framework at all".
# A first version of this rule claimed three, having read the clinical pathway
# section and the NHSSC framework names but not that one, and published a panel
# that contradicted its own page.
check("exactly five frameworks", len(co["frameworks"]) == 5, "got %d" % len(co["frameworks"]))
_co_fw = sorted(f["name"] for f in co["frameworks"])
for want in ["Flexible Endoscopes and Associated Options and Related Services",
             "Rigid Endoscopy and Associated Options and Related Services",
             "Endoscopy, Endourology and Oncology Ablation Consumables and Associated Products",
             "Decontamination Capital Equipment, Associated Accessories and Services",
             "Urology and Bowel Management"]:
    check("carried: %s" % want[:52], want in _co_fw)
# The two scope agreements share one NHS Supply Chain reference, which is the
# page's own headline finding about this patch's capital route.
def _co_ref(prefix):
    for f in co["frameworks"]:
        if f["name"].startswith(prefix):
            return f.get("reference")
    return None
check("the two scope agreements still share one reference",
      _co_ref("Flexible Endoscopes") == _co_ref("Rigid Endoscopy") == "2021/S 000-007768",
      "flexible %s / rigid %s" % (_co_ref("Flexible Endoscopes"), _co_ref("Rigid Endoscopy")))
# Each of these is a real NHSSC framework whose name contains a word this rule
# matches on, or nearly does, and each belongs to a neighbouring page.
for other in ["Ear, Nose and Throat (ENT) Endoscopes and Associated Options and Related Services",
              "Instrument Decontamination and Accessories",
              "Environmental Decontamination",
              "Enteral Feeding, Bile Bags and Associated Products",
              "Minimally Invasive Surgery, Related Equipment and Accessories"]:
    check("NOT claimed: %s" % other[:52], not any(f["name"] == other for f in co["frameworks"]))

def _co_count(prefix):
    for f in co["frameworks"]:
        if f["name"].startswith(prefix):
            return f.get("supplierCount")
    return None
# Two counts are verified against NHS Supply Chain's own stated total. If either
# moves, the brief has been reissued and the page's prose needs re-reading.
check("Endoscopy, Endourology still names 58 suppliers",
      _co_count("Endoscopy, Endourology") == 58, "got %s" % _co_count("Endoscopy, Endourology"))
check("Decontamination Capital still names 20 suppliers",
      _co_count("Decontamination Capital") == 20, "got %s" % _co_count("Decontamination Capital"))
check("Urology and Bowel Management still names 57 suppliers",
      _co_count("Urology and Bowel") == 57, "got %s" % _co_count("Urology and Bowel"))
check("Rigid Endoscopy carries 18 parsed names",
      _co_count("Rigid Endoscopy") == 18, "got %s" % _co_count("Rigid Endoscopy"))
# Urology and Bowel Management is claimed for six of its eighteen lots. The other
# twelve are the continence page's, and the panel has to keep saying so or a
# member reads a catheter supplier as a stoma supplier.
check("the lot-level basis for the stoma framework is published",
      "Stoma Appliances" in (co["rules"].get("frameworks") or "")
      or "18 lots" in (co["rules"].get("frameworks") or ""))
# The third is NOT verified, NHS Supply Chain states no total on that brief, and
# the panel has to keep saying so rather than presenting five as a fact.
check("Flexible Endoscopes carries 5 parsed names", _co_count("Flexible Endoscopes") == 5,
      "got %s" % _co_count("Flexible Endoscopes"))
check("and the panel still declares that count UNVERIFIED",
      any("UNVERIFIED" in (f.get("supplierSource") or "")
          for f in co["frameworks"] if f["name"].startswith("Flexible Endoscopes")))
check("the shared ownership of the decontamination framework is published",
      "sterile services" in (co["rules"].get("frameworks") or "").lower()
      or "sterile services" in (co["rules"].get("suppliers") or "").lower())

print("  Part IXC only — one part too many would rewrite the market")
check("only IXC is claimed", tuple(_co_rule["tariffParts"]) == ("IXC",))
_co_t = co["drugTariff"]
check("the panel carries it", _co_t is not None and _co_t["parts"] == ["IXC"])
check("8,218 stoma lines", _co_t["lineCount"] == 8218, "got %s" % _co_t["lineCount"])
# 68 is the same supplier count the page's own market intelligence states for the
# £433.5m a year England spend on Part IXC. If these ever diverge, one of the two
# is out of date and the page must not keep publishing both.
check("68 suppliers, the same number the page states", _co_t["supplierCount"] == 68,
      "got %s" % _co_t["supplierCount"])
check("Coloplast leads it on line count", _co_t["topSuppliers"][0]["name"] == "Coloplast Ltd")
check("no vmp filter is applied — the whole part is the patch",
      _co_t.get("vmpFilter") is None)
# Prices are pence in NHSBSA's file and pounds in the panel. A four-figure max
# here would mean the pence-to-pounds conversion has been lost again.
check("prices are in pounds, not pence", _co_t["priceMax"] < 1000,
      "max %s" % _co_t["priceMax"])
# IXA is dressings and hosiery; IXB is incontinence appliances; the literal part
# "IXB & IXC" is six Manfred Sauer catheter lines. All three are other pages'.
for part in ["IXA", "IXB", "IXB & IXC", "IXR"]:
    check("%s is not claimed here" % part, part not in tuple(_co_rule["tariffParts"]))

print("  the stoma overlap with continence is deliberate and published")
check("continence claims Part IXC too",
      "IXC" in tuple(B.SPECIALITY_RULES[CONTINENCE]["tariffParts"]))
check("and this panel says the overlap is on purpose",
      "continence" in (co["rules"].get("drugTariff") or "").lower()
      or "continence" in (co["rules"].get("suppliers") or "").lower())

print("  suppliers, and the two names the alias registry cannot resolve")
check("suppliers come only from the five frameworks",
      co["counts"]["suppliers"] > 0 and all(s.get("frameworks") for s in co["suppliers"]))
check("130 suppliers across the five frameworks", co["counts"]["suppliers"] == 130,
      "got %s" % co["counts"]["suppliers"])
_co_unres = sorted(s["name"] for s in co["suppliers"] if not s["resolved"])
# Kept exactly as NHS Supply Chain wrote them and flagged, never dropped and
# never quietly merged into something that looks close. "Salts Healthcare
# (Ostomy)" is the one worth watching: the Drug Tariff names the same firm
# "Salts Healthcare", so one company appears under two spellings in two tabs of
# the same panel. That is an alias-registry gap, recorded here rather than fixed
# inside a speciality build, because company-aliases is shared data.
check("exactly five names are still unresolved and they are the expected five",
      _co_unres == ["Emmat Medical", "KCI Medical Limited (3m)", "Omnimed Limited",
                    "Salts Healthcare (Ostomy)", "Varian Medical Systems"],
      "got %s" % _co_unres)
check("the count of unresolved names is published", co["counts"]["suppliersUnresolved"] == 5)
_co_names = {s["name"] for s in co["suppliers"]}
for want in ["Boston Scientific", "Olympus (KeyMed)", "Pentax Medical", "Wassenburg Medical",
             "Micro-Tech (UK) Ltd"]:
    check("supplier carried: %s" % want, want in _co_names)
# ONE NAME PER COMPANY, and this patch is the case that needs it: NHS Supply
# Chain spells Olympus three different ways across the frameworks here --
# "Olympus KeyMed" on Flexible Endoscopes, "KeyMed (Medical and Industrial
# Equipment) Ltd" on the consumables agreement and "Keymed (Medical & Industrial
# Equipment) Limited" on Decontamination Capital. Published raw that is the
# biggest name on the patch appearing as three suppliers.
_co_oly = [s for s in co["suppliers"] if s["name"] == "Olympus (KeyMed)"]
check("Olympus is one supplier, not three", len(_co_oly) == 1)
check("and it is named on four of the five frameworks",
      bool(_co_oly) and len(_co_oly[0]["frameworks"]) == 4)
check("with the three NHSSC spellings kept visible",
      bool(_co_oly) and len(_co_oly[0]["variants"]) == 3)

print("  open tenders — empty is the honest answer, not a miss")
check("no open notice on this patch today", co["openTenders"] == [])


# ---------------------------------------------------------------------------
# DERMATOLOGY. The first speciality whose framework answer is "none, and here are
# the two lots instead", so the invariants have to hold a NEGATIVE as well as a
# positive: the frameworks and suppliers sections must stay empty and the finding
# must keep naming both agreements. The include's danger is "skin", which NHS
# Supply Chain uses for hand hygiene and Swansea Bay uses for burns allograft, and
# "phototherapy", which in this data means neonatal jaundice every single time.
# ---------------------------------------------------------------------------
print("\nDERMATOLOGY")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), DERM],
               check=True, capture_output=True)
de = load_panel(DERM)
check("panel is defined", de.get("defined") is True)

_de_rule = B.SPECIALITY_RULES[DERM]
_de_rx = B.compile_rule(_de_rule)

print("  no framework is claimed, and the emptiness is the finding")
check("frameworks list is empty", de["frameworks"] == [])
check("suppliers list is empty", de["suppliers"] == [])
check("the rule text is the written finding, not the default wording",
      "NO NHS SUPPLY CHAIN FRAMEWORK IS COUNTED HERE" in de["rules"]["frameworks"])
for ref in ["2025/S 000-032216", "2026/S 000-008108",
            "Total Patient Assessment Device Solutions",
            "Adult and Paediatric Phototherapy Devices"]:
    check("the finding still names %s" % ref[:44], ref in de["rules"]["frameworks"])
check("and it still says why neither is counted",
      "never per lot" in de["rules"]["frameworks"])

print("  the thirteen true positives — every one was read before it was published")
_de_titles = [a["title"] for a in de["awards"]]
for want in [
        "Community Dermatology Support Services",
        "The Provision of Lancashire and South Cumbria Adult Teledermatology Service",
        "North East London Community Dermatology Service",
        "Services Contract for Dermatology",
        "NHS Essex Integrated Care Board (ICB) Urgent Skin Cancer Dermoscopy Triage service",
        "Supply of dermatoscopes & image transfer system",
        "ENT, Ophthalmology & Skin Medicines/Medical Devices",
]:
    check("carried: %s" % want[:58], want in _de_titles)
check("both West Yorkshire awards stand, they are two providers not one notice",
      sum(1 for t in _de_titles if t.startswith("NHSWYICB")) == 2)
check("every award shown matched on its title", de["counts"]["awardsMatched"] == len(_de_titles))

print("  bare \"skin\" stays refused — both of these are real rows on other pages")
for bad in [
        # NHS Supply Chain's hand hygiene and patient wash agreement. Infection
        # prevention's, and the next slug in this rollout.
        "Skin Cleansing and Disinfection",
        "Skin Cleansing, Disinfection and Hygiene",
        # Cadaveric skin allograft for burns. Swansea Bay, three rows in the feed.
        "Cryopreserved Skin - Cryoskin",
        # Surgical closure and wound care, both claimed by name on their own pages.
        "Skin Closure Strips and Associated Products",
        "Skin integrity and pressure area care products",
]:
    check("never admitted: %s" % bad[:56], not B.match_title(_de_rx, bad))

print("  bare \"phototherapy\" stays refused — in this data it is always neonatal")
for bad in [
        "Neonatal Equipment, Adult, Paediatric & Neonatal Phototherapy Devices and "
        "Associated Accessories & Services",
        "Anaesthesia Machines, Ventilators, Neonatal Equipment and Phototherapy Systems",
        "Supply of Neonatal Phototherapy Units",
]:
    check("never admitted: %s" % bad[:56], not B.match_title(_de_rx, bad))

print("  the other nine loose words stay refused, each with the row that proved it")
for bad in [
        # laser — eighteen rows, none dermatology, and two unattributable.
        "POS Broomfield - Candela - laser GMAX PRO - 4 yrs maintenance",
        "Acupulse Laser Service Contract",
        "ESNEFT2730 Purchase of ENT Laser",
        "Green Light Laser",
        # wig — refused deliberately; the page says the NHSSC wigs agreement is not
        # a dermatology agreement, so the panel cannot claim nine wig awards.
        "Supply of Wigs",
        "Fully Managed Wig Service",
        "Supply, Repair and Maintenance of Wigs and Accessories",
        "Supply of Wigs and Accessories",
        # hair — schools and colleges buying groups, and "chair" inside "wheelchair".
        "Hair and Beauty Framework",
        "Hair, Beauty and Wigs Supplies",
        "Wheelchairs, Specialist Seating and Related Services",
        # topical — route of administration, not skin.
        "Intravenous & Topical Fluids",
        "Generic Drugs - Topicals & Miscellaneous",
        # lesion — breast surgery.
        "National Framework Agreement for Non-Wire Lesion Localisation and Sentinel "
        "Lymph Node Location Products",
        # squamous cell — only the cutaneous form is admitted.
        "Head and Neck Squamous Cell Carcinoma Pathway Services",
        # cryo — ablation, preservation and pathology cryostats.
        "BOSTON - ICEFX CRYOBLATION SYSTEM EQUIPMENT AND CONSUMABLE AGREEMENT",
        "BCU-DCO-63480 - Purchase of Cryostat for Pathology at Glan Clwyd Hospital",
        # sunscreen — Ministry of Defence logistics, not the NHS.
        "The Supply Of Sunscreen",
        "LSL/MED/0150 - The Supply of Sunscreen - VTN",
        # biopsy — breast and transperineal prostate.
        "Breast Biopsy Needle NPM",
        "National Framework Agreement for Transperineal Prostate Biopsy System",
        # the diabetic eye screening programme carries CPV 85121282 and must never
        # be admitted on it: CPV corroborates, it never admits.
        "NHSE1060 Diabetic Eye Screening Programme",
        "Provision of Insourced and Outsourced Clinical Services Framework (Framework Reopening)",
]:
    check("never admitted: %s" % bad[:56], not B.match_title(_de_rx, bad))

print("  the dermatology vocabulary that matches nothing today still would")
for want in [
        "Supply of Narrowband UVB Phototherapy Cabinets",
        "Psoriasis Biologic Pathway Service",
        "Community Eczema and Atopic Dermatitis Service",
        "Hidradenitis Suppurativa Pathway Redesign",
        "Isotretinoin Shared Care Service",
        "Mohs Micrographic Surgery Service",
        "Cutaneous Squamous Cell Carcinoma Treatment Pathway",
]:
    check("would be admitted: %s" % want[:52], B.match_title(_de_rx, want))

print("  the Drug Tariff slice is emollients, and only emollients")
_de_t = de["drugTariff"]
check("Part IXA only", _de_t["parts"] == ["IXA"])
check("it is a slice, not the part — IXA whole is 56,833 lines",
      0 < _de_t["lineCount"] < 500)
check("and it names a real supplier set", 5 <= _de_t["supplierCount"] <= 60)
check("prices are pounds, not the pence NHSBSA publishes", _de_t["priceMax"] < 100)
_de_vrx = __import__("re").compile(_de_rule["tariffVmp"], __import__("re").I)
print("  the tariff pattern's own traps stay shut")
for bad in [
        # a wound contact layer, not an emollient — this is why bare "paraffin"
        # is never used.
        "Paraffin gauze dressing sterile 10cm x 10cm",
        "Paraffin gauze dressing sterile 5cm x 5cm",
        # "Curea" ends in the letters u-r-e-a. A bare "urea" takes all 13 of its
        # wound dressing lines.
        "Generic Curea P1 dressing 10cm x 10cm square",
        "Generic Curea P2 dressing 15cm x 15cm square",
        # peristomal skin care, Part IXC, the stoma pages'.
        "Ostomy skin protectives",
        # scar management, plastics and burns.
        "Silicone gel sheet 13cm x 13cm square",
        # gynaecology.
        "Vaginal moisturisers",
        # Full Marks head lice solution. Refused so the slice stays describable as
        # the emollient range.
        "Cyclomethicone 50% / Isopropyl myristate 50% solution",
        # compression hosiery, which is what claiming IXA whole would have brought.
        "Class 2 below knee compression stocking",
]:
    check("tariff never counts: %s" % bad[:52], not _de_vrx.search(bad))
for want in [
        "Generic AproDerm emollient cream",
        "Emulsifying wax 30% / Yellow soft paraffin 30% ointment",
        "White soft paraffin 13.2% / Liquid paraffin light 10.5% cream",
        "Isopropyl myristate 15% / Liquid paraffin 15% gel",
        "Urea 10% cream",
        "Generic Diprobase Advanced Eczema cream",
        "Generic Dermatonics Once Callus Removing Balm",
]:
    check("tariff counts: %s" % want[:52], bool(_de_vrx.search(want)))

print("  open tenders — empty is the honest answer, not a miss")
check("no open notice on this patch today", de["openTenders"] == [])


# ---------------------------------------------------------------------------
# INFECTION PREVENTION AND CONTROL. The biggest framework patch in the rollout -
# sixteen NHS Supply Chain agreements matched here, out of the twenty the page
# itself counts - and the first whose frameworks are spread across THREE unrelated
# NHSSC categories, because NHS Supply Chain has no infection prevention category
# at all. That is why the framework pattern names subjects and not a category, and
# why the first invariant below is that it returns those sixteen and nothing else.
#
# The include's dangers are all words this patch shares with somebody else's
# budget: "cleaning" is estates and schools, "gloves" is radiology and first aid
# boxes, "decontamination" is asbestos, "gown" is a mortuary shroud, "curtain" is
# a shower rail, "antimicrobial" is an antibiotic, and "autoclave" is a university
# research laboratory nine times out of eleven. Four of those were refused in the
# include instead of admitted; the rest are the exclusion list, and both halves
# are tested here.
# ---------------------------------------------------------------------------
print("\nINFECTION PREVENTION AND CONTROL")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), IPC],
               check=True, capture_output=True)
ip = load_panel(IPC)
check("panel is defined", ip.get("defined") is True)

_ip_rule = B.SPECIALITY_RULES[IPC]
_ip_rx = B.compile_rule(_ip_rule)
_ip_fw = sorted(f["name"] for f in ip["frameworks"])

print("  the sixteen frameworks, by name, and no seventeenth")
_IPC_SIXTEEN = sorted([
    "Cleaning Equipment, Supplies and Associated Products",
    "Clinical and Sharps Waste Management",
    "Curtains, Blinds and Associated Services",
    "Decontamination Capital Equipment, Associated Accessories and Services",
    "Environmental Decontamination",
    "Examination Gloves",
    "Hand Hygiene and Associated Products and Services",
    "Instrument Decontamination and Accessories",
    "Medical Pulp, Macerators and Support Products",
    "Paper Hygiene",
    "Polymer Aprons",
    "Reusable Clinical and Sharps Waste Management Service",
    "Skin Cleansing, Disinfection and Hygiene",
    "Surgical Gloves",
    "Tray Wrap and Sterilisation Equipment",
    "Wipes for Surface Cleaning and Disinfection",
])
check("exactly sixteen frameworks", len(_ip_fw) == 16, "got %d" % len(_ip_fw))
check("and they are exactly the sixteen that were read", _ip_fw == _IPC_SIXTEEN,
      "unexpected: %s" % "; ".join(set(_ip_fw) ^ set(_IPC_SIXTEEN)))

print("  the framework pattern does not reach a neighbouring agreement")
for bad in [
        # "Advanced Wound Care" and "General Wound Care" are tissue viability's, and
        # neither may arrive on a pattern that contains "cleaning" or "hygiene".
        "Advanced Wound Care",
        "General Wound Care",
        # Uniforms and textiles are Facilities like Paper Hygiene is, and are NOT
        # among the twenty. The patch is not "everything Facilities buys".
        "NHS Healthcare Uniform",
        "Textiles and Associated Products",
        "National Ambulance Uniforms and General Workwear",
        # Surgical Instruments is theatres'; sterilisation of them is this patch's,
        # buying them is not.
        "Surgical Instruments",
        "Procedure Packs",
        # Catering and office consumables share the Facilities category and nothing
        # else.
        "Catering Consumables and Equipment",
        "Office Supplies",
]:
    check("framework never claimed: %s" % bad[:52],
          not __import__("re").compile(_ip_rule["frameworks"], __import__("re").I).search(bad))

print("  the true positives — every award title in the slice was read before publishing")
_ip_titles = [a["title"] for a in ip["awards"]]
for want in [
        "Community Infection Prevention and Control (IPC) Services",
        "Clinical & Sharps Waste Management",
        "Automated Endoscope Washer Disinfectors",
        "Framework for the Provision of FFP3 Masks",
        "Skin Cleansing and Disinfection",
        "Hand Hygiene Products [4016092]",
        "Tray Wrap & Sterilisation Products",
        "Non-Sterile Single Use Type IIR Facemasks without Anti-Fog Strip",
        "Sitewide Macerator upgrade",
        "Medical Pulp (4951708)",
]:
    check("carried: %s" % want[:58], want in _ip_titles)

print("  the exclusion list — every one of these is a real row that matched and was wrong")
for bad in [
        # first aid / workwear — Kent County Council and Scotland Excel buying
        # first aid boxes and safety clothing, not barrier precautions.
        "First Aid Consumables, Equipment and Disposable Gloves – Y21031",
        "First Aid Equipment, Disposable Gloves, PPE and Workwear – Y20044",
        "Supply and Delivery of Personal Protective Equipment (PPE), First Aid "
        "Materials and Workwear",
        # janitorial — a schools catering and cleaning contractor.
        "CLEANING MATERIALS & JANITORIAL SUPPLIES",
        # fuel tank — an estates job that shares one word with this patch.
        "WHHT - Specialist Fuel Tank Cleaning & Scaffolding",
        # asbestos — decontamination of a plant room, not of an instrument.
        "WHHT - Emergency DCU Supply and Plant Room Asbestos Decontamination Services",
        # radiation — lead-equivalent radiology protection, not IPC PPE.
        "Supply of Radiation Gloves",
        "X-Ray Protective Wear and Accessories",
        # shroud — patient and mortuary wear.
        "Multi-Purpose Butterfly Sleeve Gown/Shroud",
        # shower curtain — a washroom fitting, not the antimicrobial cubicle range.
        "Shower Curtains & Brackets",
        # reagent — a molecular respiratory panel bought by pathology.
        "Cepheid Cov2/FLU/RSV/MRSA Reagents",
        # isolator — a pharmacy aseptic cabinet. VHP is this patch's technology;
        # the isolator is not this patch's purchase.
        "Integrated Vapour Hydrogen Peroxide (VHP)–Isolator Module",
]:
    check("never admitted: %s" % bad[:56], not B.match_title(_ip_rx, bad))

print("  the words REFUSED IN THE INCLUDE stay refused — these never reach the exclusion list")
for bad in [
        # autoclave — nine of eleven matches are university and research-institute
        # laboratory autoclaves, and bare "Autoclave 2024" cannot be told from a
        # sterile services department on the title.
        "Autoclave 2024",
        "Autoclave",
        "Purchase of Autoclaves",
        "Replacement of Life Science Autoclaves",
        "PURCH2250 Provision of Contract Agreement for the CL3 Compliant Double Ended "
        "Autoclave and Associated Parts",
        "UKRI-6261 Self-Steam Generating Autoclave",
        "Site Autoclave Service and Validation",
        # antimicrobial — every match was a medicine or a laboratory assay.
        "Provision of a new antimicrobial to the NHS in England via a "
        "subscription-based payment model",
        "Provision of an Existing Antimicrobial to the NHS in England via a "
        "Subscription-based Payment Model",
        "Evaluation of antibiotic products for antimicrobial subscription model scheme",
        "Automated Mycobacteria Culturing Systems, Media, Manual Broth Microdilution, "
        "Antimicrobial Diffusion Discs and Test Strips",
        # bare PPE — a housing association and three councils buying hi-vis, and
        # the University of Glasgow using "PPE Ref" as a purchase-order prefix.
        "Personal Protective Equipment - Dynamic Purchasing System",
        "Personal Protective Equipment, Corporate Uniform and Equipment",
        "PPE Ref 9346 DIRECT AWARD FOR IN VIVO HIGH-FREQUENCY LINEAR ARRAY "
        "MICRO-ULTRASOUND",
        "PPE Ref 7753 Direct Award For Upgrade And Service Of 7t MRI Scanner",
        # paper hygiene — seven of nine matches are schools and councils buying
        # toilet tissue. The framework is this patch's; the award titles are not.
        "Paper Hygiene and Toilet Tissue",
        "189_24 Paper Hygiene Consumables & Dispensers (ESPO Private Label \"Smartbuy\")",
        "YPO - 001137 Paper Hygiene and Associated Dispensers",
        "70358 Supply and Delivery of Paper Hygiene Products to the Education Authority",
        "Paper Hygiene – Couch rolls",
        # hand sanitiser — the Education Authority NI and Sport NI. "hand hygiene"
        # is the procurement term this patch actually uses and it IS included.
        "FMM-20-041 Supply and Delivery of Hand Sanitiser and Dispensers",
        "DfC Sport NI – Supply and Delivery of Hand Sanitiser Dispenser and Trigger "
        "Spray Bottle",
        "NSSCOVID-19 -328 Hand Sanitiser",
        # screening and swabs — the national screening programmes and microbiology
        # consumables. Neither is infection prevention.
        "NHS Scotland Bowel Screening FIT Kits, Distribution and Analysers",
        "SMA Newborn Screening Kits",
        "NEL ICB Latent Tuberculosis Infection (LTBI) Screening Programme (Lots 1-6)",
        "Medical Wire Swabs & Consumables",
        "The Supply of Sterile Boot Swab Kits to the Animal and Plant Health Agency",
        # bare "infection" — winter respiratory services, not infection prevention.
        "North Cumbria Acute Respiratory Infection Services",
        "Northumberland Acute Respiratory Infection Service (Winter Pressures)",
        # estates spend that is real but is not one of the twenty agreements.
        "GEH Pest Control",
        "Pest Control - House Crickets",
        "Laundry services",
        "Legionella Laboratory Testing Service & Sample Collection",
        "SWAST-5126-FM Water Safety",
        "NHSL424 WEST OF SCOTLAND LAUNDRY CONTINUOUS BATCH WASHER LINE REPLACEMENT",
]:
    check("never admitted: %s" % bad[:56], not B.match_title(_ip_rx, bad))

print("  the infection prevention vocabulary that matches nothing today still would")
for want in [
        "Supply of Sterile Nitrile Examination Gloves",
        "Hand Hygiene and Associated Products and Services",
        "Environmental Decontamination and Water Purification",
        "Wipes for Surface Cleaning and Disinfection",
        "Clostridioides difficile Deep Clean Programme",
        "Carbapenemase-Producing Enterobacterales Isolation Capacity",
        "Surgical Site Infection Surveillance Service",
        "Single Use Personal Protective Equipment and Medical Protective Consumables",
        "Single Use Theatre Protective Wear and Related Consumables",
]:
    check("would be admitted: %s" % want[:52], B.match_title(_ip_rx, want))

print("  no Drug Tariff part, and it is not a close call")
check("no tariff is claimed", ip.get("drugTariff") is None)
check("and the rule says why", "No Drug Tariff part applies" in ip["rules"]["drugTariff"])

print("  CPV corroborates the two codes that are specific to this patch, and no more")
check("33191 and 90524 only", tuple(_ip_rule["cpv"]) == ("33191", "90524"))
for loose in ["90910", "90919", "33199", "50421"]:
    check("does not claim %s" % loose, loose not in _ip_rule["cpv"])

print("  the four unreadable agreements are named, not denied")
for ref in ["2021/S 000-016429", "2023/S 000-018722", "2025/S 000-077817",
            "2025/S 000-077035", "Primel Corporation Ltd"]:
    check("coverage note names %s" % ref[:40], ref in ip["rules"]["frameworks"])
check("and it says the supplier list is sixteen frameworks' worth, not twenty",
      "SIXTEEN FRAMEWORKS' WORTH, NOT TWENTY" in ip["rules"]["suppliers"])

print("  the five double-counted companies are declared rather than quietly merged")
for pair in ["Vernacare LTD (Robinson Healthcare Limited)", "Polyco Healthline Limited",
             "Globus (Shetland) Ltd", "2San Global Limited", "Reliance Medical Ltd (New)"]:
    check("declared: %s" % pair[:48], pair in ip["rules"]["suppliers"])
check("and the count is not passed off as a company count",
      "FIVE LOWER THAN THE COUNT" in ip["rules"]["suppliers"])

print("  what the refusals cost is named, not quietly lost")
for cost in ["SSD autoclave cooling water chiller", "microbiology autoclave"]:
    check("names the cost: %s" % cost[:44], cost in ip["rules"]["frameworks"])

print("  open tenders — empty is the honest answer, not a miss")
check("no open notice on this patch today", ip["openTenders"] == [])


# ---------------------------------------------------------------------------
# ONCOLOGY AND SACT. The first speciality in the rollout whose page opens on a
# procurement ABSENCE: there is no NHS Supply Chain framework for a cytotoxic or a
# chemotherapy product, the drug travels by NICE appraisal, the Cancer Drugs Fund
# and specialised commissioning instead, and the two agreements this rule matches
# are general ones a cancer service buys THROUGH. The invariants below exist
# because the two ways to get this patch wrong both look like helpfulness:
# widening to the word "cancer", which fills the panel with screening, dermoscopy
# and whole-body MRI surveillance; and picking up radiotherapy, which is a
# different modality with three unclaimed NHSSC frameworks and no speciality page
# of its own yet.
#
# It is also the sharpest case in the rollout for never reading the feed's own
# `spec` field: it tags 31 rows oncology-and-sact and 26 are wrong, having matched
# "anti-" on anti-rabies immunoglobulin, anti-D, anti-embolism stockings and
# anti-retrovirals, and having thrown in National Museums Scotland's X-ray unit.
# Those rows are tested as refusals below.
# ---------------------------------------------------------------------------
print("\nONCOLOGY AND SACT")
subprocess.run([sys.executable, os.path.join(HERE, "scripts", "build_speciality_panels.py"), ONC],
               check=True, capture_output=True)
onc = load_panel(ONC)
check("panel is defined", onc.get("defined") is True)

_onc_rule = B.SPECIALITY_RULES[ONC]
_onc_rx = B.compile_rule(_onc_rule)
_onc_fw = sorted(f["name"] for f in onc["frameworks"])

print("  the two frameworks the page itself names, and no third")
_ONC_TWO = sorted([
    "Endoscopy, Endourology and Oncology Ablation Consumables and Associated Products",
    "Infusion Pumps and Administration Sets and Associated Products",
])
check("exactly two frameworks", len(_onc_fw) == 2, "got %d" % len(_onc_fw))
check("and they are the two that were read", _onc_fw == _ONC_TWO,
      "unexpected: %s" % "; ".join(set(_onc_fw) ^ set(_ONC_TWO)))

print("  radiotherapy is a different modality and stays out until it has its own page")
for bad in [
        # Three agreements a cancer centre really does buy through, and no speciality
        # rule claims any of them. They are NOT quietly absorbed here: this page's own
        # demand section treats radiotherapy as a separate modality running a separate
        # service, and a linac is nowhere in its scope or product ranges.
        "Radiotherapy Treatment Systems and Associated Options and Related Services",
        "Radiotherapy Ancillary Devices incl Dosimetry Patient Positioning and QA Devices",
        "Radiotherapy IT Solutions and Associated Options and Related Services",
        # Already counted on the urology page.
        "Brachytherapy Seeds and Associated Accessories",
        # Cancer DETECTION, and radiology and imaging's framework.
        "Mammography Imaging Systems and Associated Options and Related Services",
        # Rehabilitation, prosthetics and orthotics'.
        "External Breast Prosthesis and Chest Support",
        # The general pharmacy and aseptic services patch, which is not this one.
        "Pharmacy Robotics and Automation",
        # Vascular access's, and a reminder that the frameworks pattern names the
        # infusion agreement in full rather than matching the word "infusion".
        "Central Venous Catheters, Intravenous Accessories and Pressure Monitoring",
]:
    check("framework refused: %s" % bad[:56], not _onc_rx["fw"].search(bad))

print("  the thirteen titles that were read one by one and are all this speciality")
for want in [
        "Framework Agreement for the Provision of Dose Banded Chemotherapy Services",
        "Oncology Ablation Consumables",
        "Endoscopy, Endourology & Oncology Ablation Consumables & Associated Products",
        "Aseptics Medicines (Including Cytotoxics)",
        "NP39724 Generic and Biosimilar Cancer Medicines",
        "Generic and Biosimilar Cancer Medicines",
        "Chemotherapy Cold Caps",
        "Aseptically Prepared Systemic Anti-Cancer Treatment (SACT)",
        "National Framework Agreement for the supply of Aseptically Prepared Cytotoxic "
        "Medicines and Monoclonal Antibodies",
        "Oncology Generic Medicines - Additions",
        "Oncology Generics Medicines",
        "Cancer Care Services in Cheshire and Merseyside",
]:
    check("admitted: %s" % want[:56], B.match_title(_onc_rx, want))

print("  cancer DIAGNOSIS is not cancer treatment, and the word alone would fill the panel with it")
for bad in [
        # Every one of these is a real row that the bare word "cancer" matched and
        # that was read and rejected. This page's own pathway section puts all of
        # them before the first product decision a rep on this patch makes.
        "Lung Cancer Screening - DAP C",
        "Non Specific Symptom Urgent Suspected Cancer pathway",
        "C The Signs Earlier Cancer Detection Platform",
        "NHS Essex Integrated Care Board (ICB) Urgent Skin Cancer Dermoscopy Triage service",
        "Specialised Paediatric Whole-Body MRI Surveillance for Cancer Predisposing Syndromes",
        "Replacement Ultrasound Machine for Lung Cancer Diagnostic",
        "SR Cancer - Multi Modal Radiology image transfer",
        "Waiver - BWC_RQ3 - 06819 - Life Technologies Limited  -  Cancer Service Panel",
        # "oncolog" bare: radiotherapy physics twice, nuclear medicine once, and the
        # pathology page's sequencing panel once.
        "Waiver - UHB_QEH - 12044 - Oncology Imaging System (OIS)-  Maintenance Contract",
        "Waiver - UHB_QEH - 12043 - Oncology Imaging Systems  -  Phantom Maintenance Contract",
        "Supply of FDG and other Radiotracers for Oncology Scanning.",
        "Next Generation Sequencing Panel for Analysis of Somatic (Solid Tumour and "
        "Haemato-oncology) Samples",
        # "aseptic" bare: pharmacy technical services, not cancer. Step 4 of this
        # page's pathway is an aseptic unit, but the word is not a cancer word.
        "NP38626 Compounded Aseptic Medicines",
        "Aseptic Isolators and Cabinets",
        "Supply and Maintenance of Aseptic Isolators",
        "Provision of Aseptic Unit Pharmaceutical Isolators",
        "NP48618 Aseptic Consumables",
        "Aseptically Manipulated or Terminally Sterile Medicinal Products",
        "EoECPH Aseptic Cleanroom Consumables and Laundry Services.",
        # "tumour" bare: two lab tests and a diagnostic imaging agent. The fourth,
        # 177Lu-Dotatate, is a real systemic anti-cancer medicine but it is molecular
        # radiotherapy, and it falls on the far side of the same modality line that
        # keeps the linacs out.
        "PROVISION OF TUMOUR PROFILING TEST",
        "Purchase of AAA Netspot - Diagnostic Imaging Agent Kit to Detect Neuroendocrine Tumours",
        "Purchase of 177Lu- Dotatate (Lutathera ®) to treat patients with neuroendocrine tumours",
        # The word boundary in front of chemotherap is load-bearing: this title says
        # in its own words that it is not this patch.
        "Supply of Nonchemotherapy Compounded Monoclonal Antibodies",
        # "monoclonal" and "biosimilar" bare: general branded and biologic medicines.
        "NHS Framework for the Midlands and East, Branded Medicines - Tranche B plus "
        "Cytokine Modulators and other Monoclonal Antibodies",
        "NP49425 Generic and Biosimilar Transition Medicines",
        "Biologic and Biosimilar Medicines",
        "Branded and Biosimilar Ophthalmology",
        # "immunotherap" bare: NHS Blood and Transplant's cell therapy and donor
        # service, not a SACT buy.
        "Stem Cell and Immunotherapy Services",
        # What the feed's own `spec` field files under oncology-and-sact. All of these
        # are tagged this speciality in tender-history.json and not one of them is.
        "NP34925c Anti Rabies immunoglobulin intramuscular use (IM)",
        "NHS Framework Agreement for Human Albumin & Normal and Anti-D Immunoglobulin",
        "Anti-Embolism Stockings",
        "Anti-Retroviral Drugs",
        "COVID-19 Reagant Agreement for Anti-body Testing",
        "Needle Syringe Programme",
        "National Museums Scotland - X Ray Unit",
        "Fluoroscopy Unit and Associated Enabling Works",
        "Nitric Oxide Therapy",
]:
    check("refused: %s" % bad[:56], not B.match_title(_onc_rx, bad))

print("  and nothing diagnostic, radiotherapy or estates reached the live panel")
_ONC_BANNED = ["screening", "dermoscopy", "radiotracer", "phantom", "sequencing",
               "linac", "linear accelerator", "brachytherap", "mammograph",
               "x ray unit", "fluoroscopy", "immunoglobulin", "anti-embolism",
               "anti-retroviral", "needle syringe"]
for a in onc["awards"]:
    low = (a["title"] or "").lower()
    check("clean award title: %s" % (a["title"] or "")[:50],
          not any(b in low for b in _ONC_BANNED))
check("every matched award is shown, none truncated",
      onc["counts"]["awardsShown"] == onc["counts"]["awardsMatched"])
check("the panel is not empty", onc["counts"]["awardsShown"] >= 10,
      "got %d" % onc["counts"]["awardsShown"])

print("  no exclusion list, and the published text says why rather than glossing it")
check("exclude is declared None", _onc_rule.get("exclude") is None)
check("and the awards rule says no exclusion list is applied",
      "NO EXCLUSION LIST IS APPLIED" in onc["rules"]["awards"])

print("  no CPV family is claimed, because none corroborates")
check("no cpv on the rule", not _onc_rule.get("cpv"))
check("and the rule says so", "No CPV family corroborates" in onc["rules"]["awards"])

print("  no Drug Tariff part, and it is not a close call")
check("no tariff is claimed", onc.get("drugTariff") is None)
check("and the rule says why", "No Drug Tariff part applies" in onc["rules"]["drugTariff"])

print("  the coverage note states the absence the whole patch turns on")
for phrase in ["no NHS Supply Chain framework for a cytotoxic or a chemotherapy product",
               "Cancer Drugs Fund",
               "Radiotherapy is not counted here",
               "no lot breakdown",
               "never a measure of anyone's oncology business"]:
    check("coverage note carries: %s" % phrase[:50], phrase in onc["rules"]["frameworks"])

print("  open tenders - empty is the honest answer, not a miss")
check("no open notice on this patch today", onc["openTenders"] == [])


# The exclude=None path must not leak to any rule that has not earned it. Five have:
# renal, gynaecology, paediatrics, dermatology and oncology, each because every hit
# its include produced was printed and read one by one and none of them was wrong,
# the loose terms having been refused in the include instead. Every other speciality
# still has to carry a real exclusion list. Adding a slug to this set is a decision,
# not a way past a failure.
_EXCLUDE_NONE_EARNED = {RENAL, GYNAE, PAEDS, DERM, ONC}
for _slug, _r in sorted(B.SPECIALITY_RULES.items()):
    if _slug in _EXCLUDE_NONE_EARNED:
        check("%s declares its empty exclusion list explicitly" % _slug,
              _r.get("exclude") is None)
        continue
    check("%s still carries an exclusion list" % _slug, bool(_r.get("exclude")))



print()
if fails:
    print("%d FAILED: %s" % (len(fails), "; ".join(fails)))
    sys.exit(1)
print("all invariants hold")
