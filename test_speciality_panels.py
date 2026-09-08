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


print()
if fails:
    print("%d FAILED: %s" % (len(fails), "; ".join(fails)))
    sys.exit(1)
print("all invariants hold")
