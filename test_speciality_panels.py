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

print("\nTHE CLINICAL VOCABULARY IS ABSENT FROM THE DATA, AND SAID SO")
# Zero rows in 3,314 contain any of these. They stay in the include because each
# can only mean this speciality, but not one row reaches the panel through them.
# If one ever does, that is a genuine new notice, not a leak.
for word in ["frailty", "geriatric", "delirium", "reablement",
             "urgent community response", "discharge to assess"]:
    check("nothing published on '%s' today" % word, word not in ftitles)
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
print("NUTRITION AND DIETETICS (page 2927)")
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


print()
if fails:
    print("%d FAILED: %s" % (len(fails), "; ".join(fails)))
    sys.exit(1)
print("all invariants hold")
