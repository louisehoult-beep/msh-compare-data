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



print()
if fails:
    print("%d FAILED: %s" % (len(fails), "; ".join(fails)))
    sys.exit(1)
print("all invariants hold")
