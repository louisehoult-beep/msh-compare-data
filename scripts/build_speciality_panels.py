#!/usr/bin/env python3
"""Build the per-speciality slice that feeds the two new tabs on a speciality page.

WHY THIS EXISTS. Until 07/09/2026 the "Suppliers, frameworks & related" tab on every
speciality page was three links out — Supplier Directory, Framework Hub, Compare tab —
and a list of neighbouring specialities. A rep on the wound care page got no wound care
frameworks, no wound care suppliers, no wound care tenders. Lou's instruction, 07/09/2026:
the sections have to be FILTERED to the speciality, and suppliers get their own tab.

WHAT IT PRODUCES. data/speciality-panels/<slug>.json — one small file per speciality,
holding only that speciality's slice of frameworks, suppliers, awards, tenders and the
Drug Tariff. Small on purpose: the page must not pull 13MB of Drug Tariff or 6MB of
supplier index to render a panel.

THE EVIDENCE FLOOR (root rule 14). A speciality with no rule in SPECIALITY_RULES gets
NO panel — it is written with `defined: false` and the renderer shows an honest empty
state. It never falls back to a loose keyword guess, because that is exactly what the
existing tender-history `spec` field does and it is wrong more often than it is right:
of the 16 rows it tags tissue-viability-and-wound-care, 10 are false positives matched
on "tissue", "viability", "pressure" or "compression" — Kew Gardens' seed viability
X-ray cabinet, donated corneal eye tissue, Paper Hygiene and Toilet Tissue, a chest
compression system, a high pressure test rig. None of those may reach a paying member.

Every rule this script applies is written into the file it produces, so a reader can
judge the filter for themselves (rule 14a). test_speciality_panels.py holds the
invariants that fail if the matching breaks (rule 14b).

USAGE
  python3 scripts/build_speciality_panels.py                     # every defined speciality
  python3 scripts/build_speciality_panels.py tissue-viability-and-wound-care
"""
import json
import os
import re
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "speciality-panels")

# ONE NAME PER COMPANY (company-aliases/README.md). NHS Supply Chain spells the same
# firm differently on two of its own framework pages: "Molnlycke Health Care Ltd" on
# Advanced Wound Care and "Molnlycke Healthcare" on Pressure Area Care; "ConvaTec
# Limited" and "ConvaTec Ltd"; "KCI Medical Ltd" and "KCI Medical Limited", which are
# both Solventum now. Published raw, that is one supplier looking like two and a count
# inflated by 15. Every name goes through the registry before it reaches a member.
sys.path.insert(0, os.path.join(ROOT, "company-aliases"))
import company_alias  # noqa: E402

# How many rows of each rolling feed a panel carries. The page shows the most recent
# and links out for the rest; an unbounded list would put a 2021 award at the top of
# a rep's screen on the strength of nothing.
AWARD_CAP = 40


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# THE RULES. One entry per speciality. Absent means no panel, never a guess.
#
# frameworks : matched against the NHSSC framework NAME. NHSSC names its own
#              frameworks after the clinical category, so the name is the honest
#              key; the CBU `category` field is far too broad (39 frameworks sit
#              under "Medical and Surgical Consumables" alone).
# include    : the award/tender title must match this.
# exclude    : ...and must not match this. Every pattern here was put in because a
#              real row in tender-history.json matched `include` and was wrong.
# cpv        : CPV code prefixes used for award feeds that carry classification.
# tariffParts: Drug Tariff Part IX parts that belong to this speciality.
# ---------------------------------------------------------------------------
SPECIALITY_RULES = {
    "tissue-viability-and-wound-care": {
        "label": "Tissue Viability and Wound Care",
        "frameworks": r"\b(wound|dressing|npwt|negative[- ]pressure|pressure area care)\b",
        "include": (
            r"\b(wound|woundcare|dressing|dressings|npwt|negative[- ]pressure wound|"
            r"tissue viability|pressure ulcer|pressure sore|pressure relieving|"
            r"pressure area care|debridement|larval therapy|"
            r"compression (?:bandag|hosiery|garment|therapy|stocking)|lymphoedema|"
            r"bandag(?:e|ing)|skin integrity|wound closure|suture|leg ulcer|"
            r"diabetic foot|venous ulcer|honey dressing|silver dressing|"
            r"foam dressing|hydrocolloid|alginate)\b"
        ),
        "exclude": (
            r"\b(seed viability|eye tissue|corneal|toilet tissue|paper hygiene|"
            r"facial tissue|chest compression|test rig|laminar flow|pressure infus|"
            r"blood pressure|pressure washer|tissue culture|breast tissue|"
            r"soft tissue (?:sarcoma|imaging))\b"
        ),
        # 33141110 dressings and the 3314111x family that hangs off it.
        "cpv": ("3314111",),
        # IXA is dressings and elastic hosiery — the compression and lymphoedema
        # range sits here, which is why Juzo and Sigvaris dominate the line count.
        "tariffParts": ("IXA",),
    },
    # PAGE 2913. The slug is legacy: the page is named "Patient Moving and Handling"
    # and its scope is falls prevention, moving and handling, and the mobility, seating
    # and pressure redistribution range. Physiotherapy and occupational therapy reach it
    # as EQUIPMENT (the NHSSC framework of that name), not as service contracts —
    # see the note on the include list below.
    "therapies-physio-and-ot": {
        "label": "Patient Moving and Handling",
        # Four NHSSC frameworks, all under the Rehabilitation and Community CBU.
        # Orthotics, Podiatry and Immobilisation, Prosthetic Components and External
        # Breast Prosthesis are deliberately NOT here: they are the Rehabilitation,
        # Prosthetics and Orthotics page's own frameworks. Technology Enabled Care is
        # left out too — it is telecare and lone worker devices, not patient handling.
        # Pressure Area Care and Patient Handling is shared with wound care on purpose:
        # one framework really does carry both the mattresses and the hoists.
        "frameworks": r"\b(patient handling|physiotherapy and occupational therapy|aids for daily living|wheelchairs?)\b",
        # NOT INCLUDED, deliberately: bare "physiotherapy" and "occupational therapy".
        # Every award they matched in this data was an employer buying occupational
        # physio for its own staff — a university sports physio contract, a fire and
        # rescue authority, a borough council — none of which is this speciality and
        # none of which can be told apart from a genuine NHS therapies contract on the
        # title alone. Root rule 14: refuse to fire on thin evidence rather than widen.
        "include": (
            r"\b(patient handling|manual handling|moving and handling|people handling|"
            r"hoists?|patient sling|hoist sling|toileting sling|standing sling|"
            r"falls prevention|falls management|falls detection|fall detection|falls service|"
            r"mobility (?:aids?|equipment|goods|services?|scooters?)|"
            r"walking aid|walking frame|rollator|crutch(?:es)?|"
            r"wheelchairs?|specialist seating|postural support|riser recliner|"
            r"profiling bed|hospital beds?|bed rails?|"
            r"mattress(?:es)?|pressure redistribut\w*|pressure relieving|pressure area care|"
            r"patient transfer|transfer board|slide sheet|glide sheet|"
            r"aids for daily living|daily living aids?|"
            r"bariatric|stand(?:ing)? aids?|turning aid|stairlift|stair lift)\b"
        ),
        # Every one of these matched a real row in tender-history.json or
        # framework-awards.json that was not this speciality:
        #   wheelchair lift / b7r  -> Translink's B7R bus wheelchair lifts, twice. A
        #                             Volvo bus chassis, not a ward.
        #   disabled adaptations   -> Choice Housing's shower and mobility goods
        #                             adaptations, twice. A housing association's
        #                             building works, not patient handling equipment.
        #   atw grant              -> "Waiver for Staff Wheelchair ATW Grant", an
        #                             Access to Work reasonable adjustment for one
        #                             employee, not a wheelchair procurement.
        #   hcid                   -> "HCID Tactical Patient Transfer", EpiGuard
        #                             biocontainment transport isolators bought through
        #                             Leidos. High consequence infectious disease
        #                             transport, not moving and handling.
        "exclude": r"\b(wheelchair lifts?|b7r|disabled adaptations|atw grant|hcid)\b",
        # 33193 wheelchairs and associated devices, 3319212 hospital beds. Corroboration
        # only — the title still has to match.
        "cpv": ("33193", "3319212"),
        # NO DRUG TARIFF PART. Part IX is dressings and hosiery (IXA), incontinence
        # (IXB), stoma (IXC) and elastic hosiery (IXR). None of it reimburses hoists,
        # mattresses, wheelchairs or daily living aids, so the panel carries none rather
        # than reaching for the nearest part.
    },
    # PAGE 2802. Scope, in the page's own words: "Peripheral arterial disease, aortic
    # work and the endovascular range that sits between vascular surgery and the IR
    # suite." Arterial and aortic, NOT vascular access (cannulae and central lines),
    # NOT interventional neuroradiology, NOT coronary work.
    "vascular-surgery-and-pad": {
        "label": "Vascular Surgery and Peripheral Arterial Disease",
        # Only two NHSSC frameworks in frameworks.json touch this patch, and they are
        # the two the page's own Buying route section names:
        #   Vascular Therapy and Associated Products (2023/S 000-012286) — compression
        #     only, as the page says. Its 23 suppliers are the hosiery and lymphoedema
        #     firms (Juzo, Sigvaris, medi, Haddenham, Thuasne, L&R), not stent grafts.
        #   Angiography, Hybrid Theatres, Capital Equipment (2025/S 000-077456) — the
        #     angio suite and hybrid theatre capital route.
        # The framework this patch actually buys its implants through, NHSSC's IC/IR
        # framework 2021/S 000-017565 Lot 1, is NOT in frameworks.json. See the
        # coverage note below: the panel says so rather than implying these two are
        # the whole picture.
        "frameworks": r"\b(vascular therapy|angiography|endovascular|aortic|peripheral vascular)\b",
        # NOT INCLUDED, deliberately: bare "aortic", "stent", "catheter", "balloon",
        # "graft", "vein" and "venous". Every one of them was tried and every one
        # pulled in coronary, urology, renal-dialysis or cardiac-valve work that
        # cannot be told from this patch on the title alone — PCI balloons and stents,
        # Memokath urology stents, Nipro dialysis fistula needles, an ON-X mechanical
        # aortic/mitral valve, ExoVasc and Exstent external aortic ROOT supports
        # (cardiac, not vascular surgery). The aortic terms below are all qualified
        # for that reason. Root rule 14: refuse to fire on thin evidence, never widen.
        "include": (
            r"\b(vascular|endovascular|evar|tevar|fevar|bevar|aneurysm|"
            r"abdominal aortic|thoraco[- ]?abdominal|aortic dissection|aortic arch|"
            r"aortic aneurysm|aortic stent|aortic graft|aortic endograft|"
            r"peripheral arter\w*|claudication|critical limb|limb ischaem\w*|limb salvage|"
            r"angioplasty|atherectomy|stent graft|endograft|"
            r"carotid|endarterectomy|varicose|sclerotherapy|arteriovenous fistula|"
            r"angiograph\w*|angiogram|interventional radiolog\w*|"
            r"ankle brachial|abpi|amputation)\b"
        ),
        # Three patterns, each put here because a real row matched `include` and was
        # read and rejected:
        #   retinal        -> "NHS National Framework for Medical Retinal Vascular
        #                     Treatments", twice, NHS England. Ophthalmology anti-VEGF
        #                     injections. Retinal vascular disease is not this patch.
        #   vascular access-> "Vascular Access Accessories", NHS Wales Shared Services.
        #                     Cannulae and central lines — the IV therapy patch, whose
        #                     own NHSSC frameworks (Central Venous Catheters,
        #                     Intravenous Cannula) are deliberately not matched above.
        #   neuro vascular -> "HEY/17/266 NEURO VASCULAR RADIOLOGY CONSUMABLES", Hull.
        #                     Interventional neuroradiology and stroke thrombectomy.
        # Note the exclusion is `neuro vascular`, NOT `neuroradiology`: NHSSC's own
        # IC/IR framework title carries the word NEURORADIOLOGY, and excluding that
        # would drop this patch's headline framework award.
        "exclude": r"\b(retinal|vascular access|neuro[- ]?vascular)\b",
        # NO CPV LIST. Not one award that matched carries a vascular-specific CPV
        # code: the managed-service notice carries fourteen general medical-equipment
        # codes, and the two service contracts carry 85100000 and 85111200, health
        # services. A prefix here would corroborate nothing, so the panel states that
        # rather than listing a family that never fires.
        # NO DRUG TARIFF PART. The page says it outright: "This patch has no Drug
        # Tariff Part IX presence." Part IX reimburses dressings and elastic hosiery,
        # incontinence and stoma appliances. Stent grafts, peripheral stents and
        # angiography capital are not listed there.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. The framework this patch buys "
            "its implants through — NHS Supply Chain's Interventional Cardiology and "
            "Interventional Radiology framework, 2021/S 000-017565 Lot 1, which carries "
            "the endovascular stent grafts, peripheral vascular stents, carotid, iliac "
            "and renal stents and aneurysm coils — is not in the Hub's framework "
            "dataset, so its twelve suppliers are not counted below. Aortic and "
            "peripheral implants also travel through NHS England's Specialised Services "
            "Devices Programme, a central supply route with no NHS Supply Chain "
            "framework page at all. What follows is therefore the compression and "
            "capital-equipment end of this patch, which is what the record holds, not "
            "the whole buying picture. The page's Deep dive covers the IC/IR route."
        ),
    },
    # PAGE 2910. Scope, in the page's own words: "Community and acute continence
    # services, catheters and containment products." Products and services, not
    # diagnostics and not surgery: bladder scanning and urodynamics belong to the
    # assessment end of the patch and are deliberately left out below, as is the
    # surgical treatment of stress incontinence, which theatres and gynaecology own.
    "continence-bladder-and-bowel": {
        "label": "Continence, Bladder and Bowel",
        # Exactly the two national frameworks the page's own Buying route and
        # framework calendar name, both read at NHS Supply Chain on 18 Aug 2026:
        #   Disposable and Washable Continence Care (2026/S 000-031173) — the
        #     containment route, 12 suppliers, live from 24 Aug 2026 to 23 Aug 2028.
        #   Urology and Bowel Management (2023/S 000-011173) — catheters, sheaths
        #     and drainage bags, 57 suppliers, expiring 20 Feb 2027.
        # "Bladder Scanners and Associated Options and Related Services" is NOT
        # matched: it is a Diagnostic Equipment CBU capital route, and adding it
        # would contradict the page's sourced statement that two national frameworks
        # carry this patch. "Endoscopy, Endourology and Oncology Ablation
        # Consumables", "Male Intra-Urethral Catheter with Magnet Control" and
        # "Central Venous Catheters and Associated Products" are likewise other
        # pages' frameworks — colorectal and endoscopy, urology, and IV therapy.
        "frameworks": r"\b(continence|urology and bowel)\b",
        # NOT INCLUDED, deliberately, and each one was tried:
        #   bare "catheter"  -> cardiac ablation, central venous, renal fistula and
        #                       HRIM manometry catheters. Qualified below instead.
        #   bare "urology"   -> "Urology Consumables", "Urology Robot", "Surgical
        #                       Urology Consumables", "Endourology Disposable
        #                       Products", "Urology Cystoscopy Surveillance Service".
        #                       All the urology page's, none of them continence.
        #   bare "urinary"   -> "Antibiotic & Genito Urinary Medicines", three times.
        #                       That is the pharmacy patch.
        #   bare "bowel"     -> "NHSS Bowel Screening Test Kits and Analysers", "NHS
        #                       Scotland Bowel Screening FIT Kits" and "Insourcing of
        #                       Bowel Screening and General Endoscopy Services".
        #                       Bowel cancer screening, not bowel management.
        #   bare "faecal"    -> "Faecal Immunochemical Testing (FIT) ... bowel cancer".
        #                       Same screening pathway. "faecal management" is used.
        #   bare "pad"       -> "GP13A.UK. Grid Pad 13A", an AAC communication device.
        #   bare "absorbent" -> "Absorbents", NHS Wales, CPV 33000000 and no other
        #                       detail. Could be continence absorbents or spillage
        #                       absorbents and the title cannot tell you which, so
        #                       the panel declines it rather than guessing (rule 14).
        #   bare "irrigation"-> "IV Fluids & Irrigation Solutions". Qualified below.
        #   bare "toilet"    -> "Paper Hygiene and Toilet Tissue", and "Dress
        #                       Toileting Slings" on a hoist contract.
        #   bladder scanning
        #   and urodynamics  -> real, and real bladder work: "Bladder Scanners",
        #                       "Bladder Scanner Purchase", "CUBESCAN BIOCON-700-S
        #                       BLADDER SCANNER" and "ESNEFT3207 Urodynamics". They
        #                       are diagnostic equipment, and this page's stated
        #                       scope is continence services, catheters and
        #                       containment. Left out so the panel matches the page.
        "include": (
            r"\b(continence|incontinen\w*|"
            r"urinary catheters?|urethral catheters?|indwelling catheters?|"
            r"intermittent catheters?|foley|suprapubic|catheterisation|catheterization|"
            r"urinary drainage|drainage bags?|leg bags?|night bags?|"
            r"catheter valves?|catheter maintenance|"
            r"urine meters?|urine collection|urine bags?|"
            r"penile sheaths?|urinary sheaths?|uridome|"
            r"stomas?|ostomy|colostomy|ileostomy|urostomy|"
            r"bowel management|bowel care|faecal management|fecal management|"
            r"anal irrigation|trans[- ]?anal irrigation|rectal irrigation|"
            r"bladder washout|bladder irrigation|"
            r"pelvic floor|continence pads?|absorbent pads?|pads and garments|"
            r"commodes?|enuresis|nocturia)\b"
        ),
        # Three patterns, each put here because a real row matched `include`, was
        # read, and was rejected:
        #   blood collection    -> "Evacuated Blood Collection Systems and Urine
        #                          Collection Systems", BSO Procurement and Logistics
        #                          Service. Pathology specimen tubes, matched on
        #                          "urine collection". Lot 7 of Urology and Bowel
        #                          Management really is Urine Collection Devices, so
        #                          the term stays and the pathology pairing goes.
        #   catheterisation lab -> "Managed Service for Catheterisation Lab, Cardio
        #                          Thoracic Centre and Vascular", Mid and South Essex.
        #                          A cardiac cath lab, matched on "catheterisation".
        #   surgical mesh       -> "Tower 2 - Surgical Mesh, Fixation Devices, Stress
        #                          Incontinence and Bulking Agents", CPP acting for
        #                          NHS Supply Chain. Twenty-odd theatre suppliers on a
        #                          surgical mesh tower. Surgical treatment of stress
        #                          urinary incontinence is the theatres and
        #                          gynaecology patch, not community and acute
        #                          continence services.
        "exclude": r"\b(blood collection|catheterisation lab|surgical mesh)\b",
        # NO CPV LIST. The only two matching notices in the award feed that carry CPV
        # codes at all carry 33140000, medical consumables, and 85100000, health
        # services. Neither is specific to this patch, so nothing is claimed rather
        # than listing a family that corroborates everything and therefore nothing.
        # Part IXB is incontinence appliances and Part IXC stoma appliances — the
        # community prescription route that is the larger half of this patch. The
        # third value is not a typo: NHSBSA lists six Manfred Sauer lines under the
        # literal part "IXB & IXC", and matching is on the exact part string, so
        # leaving it out would silently drop them.
        "tariffParts": ("IXB", "IXC", "IXB & IXC"),
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. This is a framework "
            "membership list, not a market share and not the whole buying picture. "
            "The larger part of this patch is bought in the community on "
            "prescription, through NHSBSA Drug Tariff Part IX and the dispensing "
            "appliance contractors, a route with no NHS Supply Chain framework page "
            "at all; the Drug Tariff summary is where that route appears, and the "
            "page's Market intelligence section sizes the two populations "
            "separately. Being named on a framework is not evidence of volume, and "
            "being absent from one is not evidence of absence from the market."
        ),
    },
    # PAGE 2798. Scope, in the page's own words: "Everything every surgical speciality
    # shares: anaesthesia and perioperative, sterile services and decontamination,
    # surgical closure, energy devices, robotics and theatre equipment." Cross-cutting
    # by design, so overlap with a surgical speciality page is expected and correct:
    # Wound Closure is shared with tissue viability, the orthopaedic robot rows are
    # shared with orthopaedics, exactly as Pressure Area Care is shared between wound
    # care and patient handling.
    "theatres-and-surgical": {
        "label": "Theatres and Surgical",
        # Thirteen NHSSC frameworks, matched on the distinctive words of each name
        # rather than on a broad word, because the broad words are where this patch
        # goes wrong. Five that DO carry a theatre-sounding word are left out on
        # purpose, and each was checked:
        #   Angiography, Hybrid Theatres, Capital Equipment  -> the angio suite route,
        #       already the vascular surgery page's framework. Not matched on
        #       "operating theatres", so it does not leak in.
        #   Environmental Decontamination (Facilities CBU)   -> building and room
        #       decontamination, an estates route, not sterile services. This is why
        #       the pattern is "instrument decontamination" and "decontamination
        #       capital", never bare "decontamination".
        #   Examination Gloves                               -> ward and clinic gloves.
        #       Only Surgical Gloves is this patch, so the pattern says surgical.
        #   Surgical Mesh, Surgical Navigation Systems, Surgical Implants for Men's
        #       and Women's Health                           -> single-speciality
        #       implants and capital (hernia and gynaecology mesh, orthopaedic and
        #       spinal navigation, urology and gynaecology implants). The page's own
        #       tagline and Market intelligence name neither, so the pattern is the
        #       exact names "surgical gloves" and "surgical instruments", never bare
        #       "surgical".
        #   Flexible, Rigid and ENT Endoscopes, and Endoscopy, Endourology and
        #       Oncology Ablation Consumables                -> the endoscopy and ENT
        #       pages' own frameworks.
        "frameworks": (
            r"\b(airway management|anaesthesia machines|decontamination capital|"
            r"instrument decontamination|electrosurgical|minimally invasive surgery|"
            r"operating theatres|procedure packs|robotic medical equipment|"
            r"surgical gloves|surgical instruments|tray wrap|wound closure)\b"
        ),
        # NOT INCLUDED, deliberately, and every one of these was run over all 1,972
        # rows of tender-history.json and read before it was dropped:
        #   bare "sterile"   -> "Aseptically Manipulated or Terminally Sterile
        #                       Medicinal Products" twice, "Sterile Nitrogen Vials"
        #                       twice, "Sterile Milk Bottles", "Sterile Nitrile
        #                       Examination Gloves", "Non-Sterile Type IIR Facemasks",
        #                       "Non Sterile AGP Disposable Gowns" twice, "Sterile
        #                       Boot Swab Kits" for the Animal and Plant Health
        #                       Agency, and "Sterile Closed Tracheal Suction Systems",
        #                       which is ventilated-patient critical care. Pharmacy
        #                       aseptics, PPE, neonatal feeding and farm biosecurity.
        #                       "sterile services" and "sterilis/steriliz" are used
        #                       instead and every one of those falls away.
        #   bare "autoclave" -> eight hits and seven are laboratory autoclaves: a
        #                       University of Leeds rotating autoclave, three
        #                       University of Hertfordshire ones, a University of
        #                       Glasgow CL3 containment autoclave, a University of
        #                       Warwick replacement, a Pirbright Institute service and
        #                       a UKRI steam generator, plus one NHS microbiology
        #                       autoclave. A laboratory autoclave and a sterile
        #                       services one cannot be told apart on the title, so the
        #                       term is dropped whole. It costs one true row, an SSD
        #                       autoclave cooling water chiller, and that is the right
        #                       trade (rule 14).
        #   bare "insufflat" -> its only hit was "Bracco Protocol CO2 insufflators
        #                       maintenance", a radiology CO2 injector. Laparoscopic
        #                       insufflators are CO2 insufflators too, so no exclusion
        #                       could separate them. "laparoscop" and "minimally
        #                       invasive" carry that ground instead.
        #   "laminar flow"   -> both hits were "Positive Pressure Laminar Flow
        #                       Isolators for Pharmacy". Pharmacy aseptic isolators,
        #                       the same false positive the wound care rule excludes.
        #   bare "stapler"   -> qualified below to surgical, skin, linear, circular
        #                       and stapling device, so a stationery order can never
        #                       reach a member. Both real rows still match.
        #   "energy device"  -> dropped as a term of its own. Advanced energy reaches
        #                       the panel through "electrosurg", "diatherm" and
        #                       "minimally invasive", which is how the real rows are
        #                       actually titled.
        "include": (
            r"\b(theatres?|operating table|anaesthe\w*|anesthe\w*|airway|"
            r"laryngoscop\w*|laryngeal mask|endotracheal|tracheal tube|"
            r"breathing (?:system|circuit)|catheter mount|"
            r"sterile services|sterilis\w*|steriliz\w*|decontaminat\w*|"
            r"washer disinfector|tray wrap|"
            r"surgical instrument\w*|instrument set\w*|scalpel|diatherm\w*|"
            r"electrosurg\w*|suture\w*|wound closure|"
            r"surgical stapler\w*|skin stapler\w*|linear stapler\w*|"
            r"circular stapler\w*|stapling device\w*|"
            r"tissue adhesive|skin adhesive|haemostat\w*|hemostat\w*|"
            r"procedure pack\w*|surgical drape\w*|surgical gown\w*|surgical glove\w*|"
            r"scrub suit\w*|laparoscop\w*|minimally invasive|trocar\w*|"
            r"robotic surger\w*|surgical robot\w*|perioperative|peri-operative|"
            r"smoke evacuat\w*|surgical light\w*)\b"
        ),
        # Seven patterns. Every one matched a real row, was read, and was rejected:
        #   lecture theatre     -> "DN720 Roofing Works: The Lectures Theatre at
        #                          Willerby Hill", Humber Teaching NHS FT. Roofing on
        #                          a lecture theatre, CPV 44112500. A building, not an
        #                          operating theatre.
        #   road re-surface     -> "Blue Light road Re-Surface Block 35 Beevers
        #                          Theatres SJUH", Leeds Teaching Hospitals. Road
        #                          resurfacing outside a block that happens to be
        #                          named Beevers Theatres, CPV 79311300.
        #   water treatment     -> "Maintenance of Water Treatment Systems including
        #                          Supply and Delivery of Salt relating to a range of
        #                          Hospital Equip including Decontamination and Renal
        #                          Equipment", Belfast HSC Trust. Filed under salt,
        #                          chemicals and water softeners. An estates water
        #                          contract that happens to serve decontamination
        #                          plant, not a sterile services purchase.
        #   positive airway
        #   pressure, cpap      -> "Preliminary Market Engagement for Consumables for
        #                          Continuous Positive Airway Pressure (CPAP) and
        #                          Adaptive Support Ventilation", BSO. Respiratory and
        #                          critical care, matched on the word airway inside
        #                          the phrase. Bare "airway" is kept because it is the
        #                          honest term for this patch's own framework; these
        #                          two take the phrase back out.
        #   medicines           -> "NP40925 Analgesics, Anaesthetics, Musculoskeletal
        #                          and Joint Disease Medicines", NHS National Services
        #                          Scotland. A mixed pharmacy basket in which
        #                          anaesthetics is one category of four. Narrow
        #                          anaesthetic-agent contracts such as "Anaesthetic
        #                          Gases (Sevoflurane and Isoflurane)" and "Inhalation
        #                          Anaesthetics and Vaporisers" carry no such word and
        #                          stay, which is correct: they are anaesthesia.
        #   coagulation
        #   products            -> "NP646 Haemostatic and Coagulation Products", an
        #                          open notice. Haematology and coagulation, matched
        #                          on "haemostat". The exclusion is deliberately the
        #                          pair of words and not bare "coagulation", because
        #                          "Purchase of Electrosurgical Devices (Cut and
        #                          Coagulation, Uterine Ablation)" is a true row and
        #                          excluding on the single word would have dropped it.
        #   asbestos            -> "WHHT - Emergency DCU Supply and Plant Room Asbestos
        #                          Decontamination Services", West Hertfordshire
        #                          Teaching Hospitals. Asbestos removal from a plant
        #                          room, caught on "decontaminat\w*". It arrived in the
        #                          award feed on 08/09/2026 and was spotted before it
        #                          reached a member. Estates work, like the water
        #                          treatment row above, and the same reason bare
        #                          "decontamination" is never used on the framework
        #                          pattern. It is the only row in this data carrying the
        #                          word, and asbestos can never mean sterile services.
        "exclude": (
            r"\b(lectures? theatre|road re-?surfac\w*|water treatment|asbestos|"
            r"positive airway pressure|cpap|medicines|coagulation products)\b"
        ),
        # Seven CPV families that really are this patch, read off the notices that
        # matched: 33161 electrosurgical units, 33162 operating theatre devices and
        # instruments, 33169 surgical instruments, 33171 anaesthesia and resuscitation
        # instruments, 33172 anaesthesia and resuscitation devices, 33191 sterilising
        # and disinfecting devices, and 3314112 sutures, clips and ligatures.
        # Corroboration only, recorded against the row so a reader can see the
        # classification the buyer agreed. The title still has to match.
        "cpv": ("33161", "33162", "33169", "33171", "33172", "33191", "3314112"),
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence (IXB), stoma (IXC) and elastic hosiery (IXR), all community
        # prescription routes. Nothing bought for an operating theatre is listed
        # there, so the panel carries no tariff rather than reaching for the nearest
        # part.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. This patch has no single "
            "framework and no single market-share figure: spend sits across at least "
            "thirteen separate NHS Supply Chain frameworks, each a different product "
            "category with its own buying cycle, and none publishes a unit share "
            "breakdown. Being named on a framework is not evidence of volume, and "
            "being absent from one is not evidence of absence from the market. NHS "
            "Supply Chain is also only one route here: the award record below shows "
            "theatre consumables bought through NHS Wales Shared Services, National "
            "Procurement in Scotland, HealthTrust Europe, the Collaborative "
            "Procurement Partnership and trusts' own direct awards, none of which "
            "appears in the framework list above."
        ),
    },
    # PAGE 2799. Scope, in the page's own words: "Elective joint replacement, trauma
    # and spinal surgery: implants, instrumentation and the theatre consumables that
    # go with them." Overlap with Theatres and Surgical is expected and correct, the
    # same way Pressure Area Care is shared between wound care and patient handling:
    # a theatre buying orthopaedic power tools is buying both.
    "orthopaedics-and-trauma": {
        "label": "Orthopaedics and Trauma",
        # Two NHSSC frameworks, matched on their distinctive names. Seven others in
        # frameworks.json carry an orthopaedic-sounding word and every one was checked
        # and left out:
        #   Orthotics, Podiatry and Immobilisation (63 suppliers) and Prosthetic
        #       Components and Associated Products    -> the Rehabilitation, Prosthetics
        #       and Orthotics page's own frameworks, as the patient handling rule above
        #       already records. Casting and immobilisation sit inside the first of
        #       them, which is why no plaster or casting term is claimed here either.
        #   Robotic Medical Equipment and Associated Accessories -> named suppliers are
        #       CMR Surgical, Intuitive Surgical, Medtronic, Johnson & Johnson, MCT
        #       Lifesciences and Procept Biorobotics. That is soft-tissue and urology
        #       robotics. Not one orthopaedic robot vendor is on it: no Stryker Mako, no
        #       Zimmer Biomet ROSA, no Smith & Nephew CORI. Putting it here would have
        #       added six suppliers who are not on this patch, so it stays with Theatres
        #       and Surgical. The orthopaedic robot AWARDS still reach this page on
        #       their titles, which is the honest route.
        #   Bone Densitometers, Associated Options and Related Services -> DXA scanning,
        #       a diagnostic imaging and bone-health route, not orthopaedic surgery.
        #   Surgical Implants for Men's and Women's Health -> urology and gynaecology.
        #   External Breast Prosthesis and Chest Support, and Audiological Diagnostics
        #       Implantable Devices and Services -> neither is this speciality; both
        #       matched only because they carry the words prosthesis and implantable.
        # Surgical Navigation Systems IS included: Brainlab, Medtronic and Stryker
        # navigation is the spinal and orthopaedic route, and the page's own scope names
        # spinal surgery. It is SHARED with neurosurgery and ENT (Karl Storz is on it
        # for ENT navigation), so presence on it is a buying route, never a volume claim.
        "frameworks": r"\b(total orthopaedic solutions|surgical navigation)\b",
        # NOT INCLUDED, deliberately. Each was run over all 1,972 rows of
        # tender-history.json and all 1,294 of framework-awards.json and read:
        #   "orthotic", "orthoses", "podiatr" -> fourteen rows between them and every
        #       one is the orthotics, podiatry and prosthetics patch: NHS Lothian,
        #       Lanarkshire, Greater Glasgow, NHS Wales, BSO Northern Ireland and
        #       Dorset all buying orthotic consumables or podiatry orthoses. Dropping
        #       "podiatr" whole costs one arguable row, "Purchase of Power Tools for
        #       Podiatric Surgery", and that is the right trade: podiatric surgery is
        #       its own profession and its own framework lot, not orthopaedics.
        #   bare "prosthes" / "prosthetic" -> "ON-X Ascending Aortic Prosthesis with
        #       Valsalva Graft" (cardiac), "Surgically Implanted Breast Prostheses",
        #       "External Breast Prosthesis" and "Supply of Prosthetics" (limb
        #       prosthetics). Four rows, none of them this speciality. Joint prostheses
        #       reach the panel as arthroplasty, hip, knee and implant titles instead.
        #   bare "bone" -> "Bone Conduction", a NHS Scotland audiology award. The
        #       pattern is the specific bone products below, so it never fires.
        #   bare "power tool" -> its only unique hit was the podiatric surgery row
        #       above. Orthopaedic power tools carry the word orthopaedic and match on
        #       that, so the bare term buys nothing and risks an estates purchase.
        #   bare "navigation" -> would admit neurosurgical and ENT navigation, which is
        #       not this page. "spinal navigation" reaches the real row on "spinal".
        #   "femoral", "tibial" -> dropped as vascular-ambiguous (femoral access
        #       sheaths, femoral catheters). "femur" and "acetabular" are kept because
        #       neither has any non-orthopaedic reading.
        "include": (
            r"\b(orthopaedic\w*|orthopedic\w*|orthobiologic\w*|trauma\w*|tos3|"
            r"arthroplast\w*|joint replacement|hip\b|knee\b|shoulder\b|elbow\b|ankle\b|"
            r"spinal|spine\b|scoliosis|vertebr\w*|pedicle|interbody|"
            r"kyphoplast\w*|vertebroplast\w*|discectom\w*|laminectom\w*|"
            r"fractur\w*|osteotom\w*|osteosynthes\w*|femur|acetabul\w*|"
            r"bone (?:cement|graft|substitute|prep|screw|anchor|plate|mill|void filler)|"
            r"arthroscop\w*|cruciate|meniscal|meniscus|"
            r"external fixation|fixator|intramedullary|"
            r"tourniquet\w*|sagittal saw|pulse lavage|"
            r"musculoskelet\w*|limb reconstruction)\b"
        ),
        # Five patterns. Every one matched a real notice, was read, and was rejected:
        #   medicines           -> "NP40925 Analgesics, Anaesthetics, Musculoskeletal &
        #                          Joint Disease Medicines", NHS National Services
        #                          Scotland. A mixed pharmacy basket caught on the word
        #                          musculoskeletal. The same notice is excluded from
        #                          Theatres and Surgical for the same reason.
        #   spinal cord
        #   stimulators         -> "Neuromodulation/Spinal Cord Stimulators, Intrathecal
        #                          Drug Pumps, Radiofrequency Ablation and Associated
        #                          Products", Procurement and Logistics Service. Chronic
        #                          pain neuromodulation, not spinal surgery.
        #   epidural            -> "Spinal, Epidural and Associated Products",
        #                          Procurement and Logistics Service. Spinal and
        #                          epidural anaesthesia needles and packs. The word
        #                          spinal here is the anaesthetic route, not the spine.
        #   fgm, sexual abuse   -> "Impact of HPV self-testing - insights & good
        #                          practice in FGM, sexual abuse & trauma", NHS England,
        #                          CPV 73110000 research services. Psychological trauma.
        #                          The single clearest reason bare "trauma" needs a
        #                          guard even though every other trauma row is real.
        #   spinal muscular
        #   atrophy             -> "Referapatient for zolgensma for spinal muscular
        #                          atrophy", NHS England, CPV 72000000. A referral IT
        #                          platform for a gene therapy. Neurology, and software.
        "exclude": (
            r"\b(medicines|spinal cord stimulat\w*|epidural|"
            r"fgm|sexual abuse|spinal muscular atrophy)\b"
        ),
        # The three CPV families the matching notices actually carry, read off them
        # rather than assumed: 331417 orthopaedic supplies (fracture devices, pins and
        # plates sit at 33141770), 33183 the orthopaedic devices family (33183000
        # supports, 33183100 implants, 33183200 prostheses), and 85121283, the
        # orthopaedic medical services code the insourcing and elective-capacity awards
        # are filed under. Corroboration only; the title still has to match.
        "cpv": ("331417", "33183", "85121283"),
        # SERVICE CONTRACTS ARE KEPT, deliberately, and this is the rule a reader
        # should judge: three of the matching awards are clinical capacity rather than
        # product — "Trauma & Orthopaedics Insourcing Services" (Countess of Chester),
        # "Orthopaedic Procedures" (NHS Borders) and "Electives - Trauma and
        # Orthopaedic" (Cornwall and the Isles of Scilly ICB). They are unambiguously
        # this speciality and they tell a rep where elective activity is being bought,
        # so they stay, with their CPV recorded. They are NOT product awards and should
        # not be read as implant spend.
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence appliances (IXB), stoma appliances (IXC) and elastic hosiery
        # (IXR), all community prescription routes. No implant, instrument or theatre
        # consumable on this patch is listed there, so the panel carries none.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. Total Orthopaedic Solutions 3 "
            "is the main NHS Supply Chain route for this patch and carries 101 named "
            "suppliers, but being named on it is evidence of a route, not of volume, "
            "and NHS Supply Chain is only one route. The award record below shows "
            "orthopaedic and trauma implants bought through NHS Wales Shared Services, "
            "National Procurement in Scotland, the Business Services Organisation in "
            "Northern Ireland and trusts' own direct awards, none of which appears in "
            "the framework list above. Surgical Navigation Systems is shared with "
            "neurosurgery and ENT. No unit or market-share split is published for any "
            "of it, and none is claimed here."
        ),
    },
    # PAGE 2841. Scope, in the page's own words: "Reconstruction, burns care and the
    # advanced wound biologics and skin substitute range." The page's own Buying route
    # names one national route and says outright that the second half of the patch has
    # none: "NHS Supply Chain Advanced Wound Care (Lot 11, Burns and Scar Management);
    # NHS Blood and Transplant Tissue and Eye Services for dermal allografts; no
    # dedicated national lot exists for skin substitutes". This rule is written to that
    # scope and no wider.
    "plastics-burns-and-reconstruction": {
        "label": "Plastics, Burns and Reconstruction",
        # ONE framework, the one the page names. Advanced Wound Care is SHARED with
        # tissue viability and wound care, which matches it on "wound" — that sharing is
        # correct and deliberate, the same way Pressure Area Care is shared between wound
        # care and patient handling: Lot 11 Burns and Scar Management really does sit
        # inside the wound care framework. Three other frameworks in frameworks.json
        # carry a word from this patch's vocabulary and every one was read and left out:
        #   Reusable Plastic Medical Hollowware -> polymer bowls and jugs. The word
        #       plastic here is the material, not the speciality. This is the single
        #       clearest reason no pattern on this patch may use bare "plastic".
        #   Skin Cleansing, Disinfection and Hygiene -> infection prevention, a
        #       Medical and Surgical Consumables route, not reconstruction.
        #   External Breast Prosthesis and Chest Support -> the post-mastectomy
        #       external appliance, which is the Rehabilitation, Prosthetics and
        #       Orthotics patch, as the orthopaedics rule above already records.
        #       Implant-based breast RECONSTRUCTION is this patch; an external
        #       prosthesis is not, and the exclusion below keeps them apart.
        "frameworks": r"\badvanced wound care\b",
        # NOT INCLUDED, deliberately. Each was run over all 1,972 rows of
        # tender-history.json and all 1,294 of framework-awards.json and read:
        #   bare "plastic"   -> "Motorized Patient Couch and Plastic Composite Outer
        #                       Covers for a new MRI Scanner Design". The material.
        #                       "plastic surger" is used instead and finds nothing in
        #                       this data, which is the honest answer.
        #   bare "skin"      -> "Skin Cleansing and Disinfection", "ENT, Ophthalmology
        #                       & Skin Medicines/Medical Devices" twice, and "Urgent
        #                       Skin Cancer Dermoscopy Triage service". Infection
        #                       prevention, pharmacy and cancer triage. The specific
        #                       skin terms below reach every true row without it.
        #   bare "graft"     -> "ON-X Ascending Aortic Prosthesis with Valsalva Graft",
        #                       "Jotec E-Vita Open Neo Stent Graft" and "Vascular
        #                       Grafts". All vascular surgery. "skin graft", "dermal
        #                       graft" and "epidermal graft" are used instead.
        #   bare "laser"     -> seventeen rows and one is this patch. The other sixteen
        #                       are ENT, urology holmium, ophthalmic SLT, cardiac lead
        #                       extraction, MRI-guided ablation and laboratory laser
        #                       capture microdissection. The one true row, a burns unit
        #                       CO2 laser, carries the word Burns and matches on that.
        #                       Two further Lumenis and Candela laser maintenance rows
        #                       are very probably plastics — one is at Broomfield, home
        #                       of the St Andrew's Centre for Plastic Surgery and Burns
        #                       — but nothing in either TITLE says so, and inferring the
        #                       speciality from the buyer's name is exactly the derived
        #                       claim rule 14 forbids. They stay out.
        #   bare "matrix"    -> its only four hits here are the Novosorb dermal
        #                       templates, which are true, but the word alone would
        #                       admit anything from a software matrix to a bone matrix
        #                       in the next refresh. "temporising matrix", "dermal
        #                       matrix" and the brand name carry it instead.
        #   bare "breast"    -> twelve rows and ten are breast IMAGING, screening and
        #                       oncology: an Epiq Elite ultrasound, a biopsy needle,
        #                       Oncotype DX, mobile screening trailer maintenance,
        #                       insourced breast radiology three times. Only the two
        #                       implant rows below are reconstruction.
        #   "cranioplast"    -> "Provision of Cranioplasties" is real cranial vault
        #                       reconstruction, but in the NHS it is overwhelmingly a
        #                       neurosurgical procedure after decompressive craniectomy,
        #                       and the title cannot tell you whether this contract sits
        #                       with neurosurgery or craniofacial. Ambiguous on its face,
        #                       so it is declined rather than guessed (rule 14).
        #   "cleft"          -> "Cleft Registry and Audit Network (CRANE)" and
        #                       "Paediatric Videoflouroscopy Service for CLEFT patients".
        #                       Cleft surgery is within this speciality, but a national
        #                       clinical audit registry and a speech-and-radiology
        #                       diagnostic service are neither a buying route nor
        #                       elective plastics capacity. Nothing here would tell a rep
        #                       anything true about their patch, so both stay out.
        #   "dermato"        -> nine rows, every one dermatology: teledermatology,
        #                       community dermatology services and dermatoscopes. That is
        #                       the dermatology page. Note "dermatome", the skin-graft
        #                       harvesting instrument, IS claimed below and cannot
        #                       collide with it: \bdermatome\b matches neither
        #                       "dermatology" nor "dermatoscopes".
        "include": (
            r"\b(burn\w*|"
            r"scar\w*|keloid|contracture release|"
            r"pressure garment\w*|silicone gel sheet\w*|"
            r"plastic surger\w*|reconstructive surger\w*|breast reconstruction|"
            r"free flap|flap reconstruction|microsurger\w*|"
            r"breast implant\w*|breast prosthes\w*|"
            r"skin substitut\w*|skin graft\w*|split[- ]thickness|dermatome|skin mesher|"
            r"cultured epithelial|epidermal graft\w*|"
            r"dermal (?:matrix|template|substitute|regenerat\w*|allograft|graft|scaffold)|"
            r"acellular dermal|human dermis|"
            r"cryopreserved skin|cryoskin|"
            r"temporis\w* matrix|temporiz\w* matrix|novosorb)\b"
        ),
        # Two patterns. Both matched a real row, were read, and were rejected:
        #   burner              -> "Weishaupt Burners at Ysbyty Cwm Rhondda and Royal
        #                          Glamorgan Hospital", Cwm Taf Morgannwg UHB. Boiler
        #                          burners. An estates plant contract caught by the
        #                          natural "burn\w*" form of the include, and the whole
        #                          reason that form needs a guard.
        #   external breast
        #   prosthesis          -> "External Breast Prosthesis [4233683]" (Procurement
        #                          and Logistics Service) and "External Breast
        #                          Prosthesis" (Business Services Organisation). The
        #                          post-mastectomy external appliance, a Rehabilitation
        #                          and Community route. It is not reconstruction, and it
        #                          must not sit beside the two real implant-based
        #                          reconstruction rows as if it were the same market.
        # RESIDUAL RISK, STATED: "burn\w*" would also match a place name such as
        # Burnley. No such title exists anywhere in this data today, so no pattern is
        # invented for it — but if one appears in a refresh, it belongs here.
        "exclude": r"\b(burner\w*|external breast prosthes\w*)\b",
        # NO CPV LIST. The only matching notices that carry a CPV code at all are the
        # three Cryoskin awards, and all three carry 33140000, medical consumables — the
        # same generic family the continence rule refused. A prefix here would
        # corroborate everything and therefore nothing, so none is claimed.
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence (IXB), stoma (IXC) and elastic hosiery (IXR). Silicone scar
        # products genuinely do sit inside Part IXA — GIRFT flagged their primary-care
        # availability as a procurement gap — but IXA is 56,833 lines and the builder
        # can only filter by part, not by product. Claiming IXA here would publish the
        # wound care patch's dressings-and-hosiery summary under a plastics heading and
        # tell a rep nothing true. The panel carries no tariff rather than reaching.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. Half this speciality has no "
            "national framework at all. Skin substitutes and advanced wound biologics "
            "are bought locally on a high-cost item business case, and dermal "
            "allografts come direct from NHS Blood and Transplant Tissue and Eye "
            "Services, neither of which has an NHS Supply Chain framework page, so "
            "neither appears below. The one framework that does carry this patch, "
            "Advanced Wound Care, names 56 suppliers across 18 lots and publishes NO "
            "lot-by-lot breakdown, so the supplier list below is the whole framework's "
            "membership and not a Burns and Scar Management supplier list: most of "
            "those 56 are on other, general wound care lots. Being named on the "
            "framework is not evidence of burns volume, and being absent from it is "
            "not evidence of absence from this market."
        ),
    },
    # PAGE 2921. Frailty and older people. Page id verified against the live site
    # on 08/09/2026 (title "Frailty and Older People (Subscribers only)", parent 675). The scope the page itself publishes is the
    # pathway: identification (eFI, HFRS, Clinical Frailty Scale), Comprehensive
    # Geriatric Assessment, the acute frailty front door, and then everything after it
    # leaves hospital — urgent community response, virtual wards, intermediate care,
    # Enhanced Health in Care Homes and falls (NICE NG249). The money on this patch is
    # in that community half, and the buyers are councils and ICBs, not trusts.
    "frailty-and-older-people": {
        "label": "Frailty and Older People",
        # ONE framework, and it is the only one of the 121 in frameworks.json named for
        # anything on this patch. There is no NHS Supply Chain framework called frailty,
        # older people, geriatric medicine or falls; that absence is stated in the
        # coverage note rather than papered over by claiming a neighbour's framework.
        # Technology Enabled Care is genuinely THIS speciality's route and no other page
        # claims it: the Patient Moving and Handling rule above deliberately left it out
        # ("it is telecare and lone worker devices, not patient handling"), which is
        # right from that page's side and is exactly why it belongs here.
        # NOT CLAIMED, deliberately — Aids for Daily Living, Pressure Area Care and
        # Patient Handling, and Wheelchairs, Specialist Seating and Related Services all
        # carry equipment this population uses, and all three are the Patient Moving and
        # Handling page's declared frameworks. Claiming them here would republish that
        # page's whole supplier list under a frailty heading and tell a rep nothing they
        # could not already see. The coverage note points at them instead.
        "frameworks": r"\btechnology enabled care\b",
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,342 of framework-awards.json and every hit read.
        #
        # WHAT IS NOT HERE, AND WHY. The clinical vocabulary of this speciality is
        # almost entirely absent from UK contract titles. Zero rows in 3,314 contain
        # "frail", "geriatr", "CGA", "delirium", "reablement", "urgent community",
        # "discharge to assess", "Rockwood", "polypharmac" or "4AT". Those terms are
        # kept in the include because each one can only mean this speciality, so they
        # cost nothing and will catch a future notice — but they find NOTHING today and
        # not one row below reaches this panel through them. What actually exists on
        # this patch is the community buying route: telecare, community equipment
        # services, care homes and intermediate care beds.
        #
        # REJECTED PATTERNS, each run and read:
        #   bare "aging"      -> thirty false positives, every one of them "imaging":
        #                        MRI, CT, mammography, endoscopic, in-vivo, hyperspectral,
        #                        night vision. The single most dangerous pattern on this
        #                        patch. "ageing" is not used either: it matches nothing
        #                        at all here, so it buys nothing and only risks the typo.
        #   "older people"    -> the page's own name, and it matched twice and was wrong
        #                        twice: "Adult and Older People (AOP) mental health and
        #                        Psychological Therapies for Severe Mental Health
        #                        Problems education programmes" (NHS England — mental
        #                        health workforce education) and "Supply and delivery of
        #                        Older People Furniture and associated Services"
        #                        (Sanctuary Housing Group — a housing association buying
        #                        furniture for its own schemes, the same kind of row the
        #                        Patient Moving and Handling rule rejected in Choice
        #                        Housing's adaptations). Nought out of two. Admitting it
        #                        would need an exclusion on "furniture", which would in
        #                        turn drop a genuine care home furniture contract the
        #                        next time one appears. It stays out (rule 14).
        #   bare "rehabilitation" -> nineteen rows and not one is this speciality: eight
        #                        residential drug and alcohol detoxification contracts at
        #                        Hammersmith and Fulham, brain injury and neuro-rehab,
        #                        Border Force, the Ministry of Defence, mental health
        #                        rehab, a Scottish Ambulance Service referral system.
        #                        Frailty rehabilitation is real but nothing in this data
        #                        says so on the face of a title.
        #   "palliative", "end of life", "hospice" -> four rows, all genuine, and all of
        #                        them belong to the palliative-and-end-of-life-care page,
        #                        which is a separate speciality with its own page. One of
        #                        the four is a children's service. Not claimed here.
        #   bare "respite"    -> its one hit, "Residential, respite and nursing care
        #                        beds", is genuine and is admitted below on "nursing care
        #                        beds" instead. "Respite" alone would equally admit
        #                        children's and learning disability respite, which are
        #                        other people's patches.
        #   "supported living"-> "Ardwyn - Supported Living" (Aneurin Bevan UHB). Supported
        #                        living is as often learning disability or mental health
        #                        as it is older people, and the title does not say which.
        #                        Ambiguous on its face, so declined rather than guessed.
        #   "extra care"      -> "SOL30141 SOL Extra Care Solihull Retirement Village", a
        #                        council building a retirement village. Construction, not
        #                        a route anything is sold into clinically.
        #   "domiciliary"     -> "HMP Wandsworth - Domiciliary Care". A prison.
        #   "care at home"    -> four rows, all "Healthcare at Home": immunoglobulin,
        #                        ixekizumab, nusinersen and ustekinumab homecare
        #                        medicines. A pharmacy route, not this speciality. Note
        #                        "hospital at home" below cannot collide with it.
        #   "healthcare technology" -> "YPO - 001284 Community & Healthcare Technology
        #                        Equipment & Associated Services" is probably partly this
        #                        patch, but the title covers anything a council might buy.
        #                        \bcare technology\b is used instead and cannot match
        #                        "Healthcare Technology" (no word boundary before "care"),
        #                        which is the whole reason the boundary is written that way.
        "include": (
            r"\b(frailty|frail elderly|elderly|geriatric|comprehensive geriatric|"
            r"delirium|dementia|"
            r"telecare|technology enabled care|electronic assistive technology|"
            r"care alarms?|care technology|"
            r"community equipment|social care equipment|independent living|"
            r"intermediate care|virtual ward|hospital at home|urgent community response|"
            r"reablement|discharge to assess|admission avoidance|"
            r"care homes?|nursing care beds?|"
            r"falls (?:prevention|management|risk|service|pathway|response))\b"
        ),
        # ONE pattern, because on this include exactly one row matched and was wrong:
        #   ligature -> "Consultancy Services for IP&C, Ligature and Dementia issues at
        #               Angelton Clinic & Ysbyty Cwm Cynon" (Cwm Taf Morgannwg UHB).
        #               Caught by "dementia". Angelton Clinic is a mental health unit and
        #               the contract is an estates and infection prevention consultancy
        #               about ligature risk; dementia is one line of its brief. It is not
        #               a frailty buying route, and the other two "ligature" rows in this
        #               data (ligature reduction works at Wrexham Maelor, anti-ligature
        #               bedroom doors) confirm the word is mental health estates work.
        #               Dementia itself stays in the include: it is core vocabulary here
        #               and this is the only wrong row it has ever produced.
        # A short exclusion list is the honest outcome of a narrow include, not a sign
        # the derivation was skipped: 31 of the 32 rows this rule admits were read and
        # are this speciality.
        "exclude": r"\b(ligature)\b",
        # 85144100 is "Residential nursing care services" and it is the one CPV code in
        # this data specific to this patch — the six notices carrying it are all
        # older people's residential and nursing care. It corroborates two of the rows
        # below and admits nothing on its own.
        # NOT CLAIMED: 85323000, community health services, which sits on both
        # "Step Up/Step Down Intermediate Care Bed Provision" and "Plymouth Home-Based
        # Intermediate Care" and would look like the obvious key — until you read the
        # other forty notices carrying it: CAMHS tier 4 beds, suicide prevention,
        # smoking cessation, general dental services in Gwent, multilingual counselling,
        # a drug test on arrest scheme. It corroborates everything and therefore nothing.
        "cpv": ("85144100",),
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence appliances (IXB), stoma appliances (IXC) and elastic hosiery
        # (IXR). Older people are the largest users of Parts IXA and IXB by some
        # distance, but the tariff has no frailty part and the builder can only filter
        # by part, not by product: claiming IXB here would publish the continence page's
        # whole incontinence summary under a frailty heading. No part is claimed.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. NHS Supply Chain has no framework "
            "for frailty, older people, geriatric medicine or falls, so the single "
            "framework below is not this speciality's buying route — it is the only part "
            "of it NHS Supply Chain runs. Most of this patch is bought by local "
            "authorities and integrated care boards through community equipment services, "
            "telecare contracts and care home frameworks, which is what the awards list "
            "shows and why almost every buyer there is a council. The equipment itself "
            "(hoists, profiling beds, pressure redistribution, wheelchairs, daily living "
            "aids) is bought through Aids for Daily Living, Pressure Area Care and Patient "
            "Handling, and Wheelchairs, Specialist Seating and Related Services: those are "
            "published on the Patient Moving and Handling page and are deliberately not "
            "repeated here. Being absent from the supplier list below is not evidence of "
            "absence from this market."
        ),
    },
    # PAGE 2842. Scope, in the page's own words: "The IR suite: embolisation,
    # endovascular work, tumour ablation, image-guided biopsy and drainage, and the
    # contrast media and injector range." The page publishes its four buying routes
    # explicitly, every one read at source on 08/09/2026, and this rule is written to
    # them and no wider.
    "interventional-radiology": {
        "label": "Interventional Radiology",
        # TWO frameworks, and the reason there are only two is the whole story of this
        # patch. The framework this speciality actually buys on — NHS Supply Chain
        # 2021/S 000-017565, Interventional Cardiology, Interventional Radiology and
        # Interventional Neuroradiology, Cardiac Rhythm Management and Electrophysiology
        # — IS in frameworks.json, but in its `unparsed` list, not its `frameworks`
        # list, with the recorded reason "the page states its supplier count but
        # publishes no list of names". build_frameworks reads only the parsed list, so
        # its 67 suppliers cannot be counted here. The same is true of "Operating and
        # Mobile Interventional Radiology Tables", refused because the brief states 12
        # suppliers and only 11 could be parsed. Neither is silently dropped: both are
        # named in the coverage note below.
        #
        #   Contrast Injectors, Consumables and Associated Options and Related Services
        #     (2021/S 000-007768, to 31 March 2028) is buying route 2 on the page, and
        #     its five parsed suppliers — Bayer, Bracco, Guerbet, MIS Healthcare and
        #     Synapse Medical — are exactly the five the page names off the National
        #     Product Matrix dated 10 March 2026. That agreement is corroborated, not
        #     assumed.
        #   Angiography, Hybrid Theatres, Capital Equipment, Related Accessories and
        #     Services (2025/S 000-077456) is the angio suite capital route, which is
        #     the room this speciality works in. It is SHARED with the vascular surgery
        #     and PAD page, which claims it too; that sharing is deliberate and correct,
        #     the same way Pressure Area Care is shared between wound care and patient
        #     handling. A hybrid theatre really is bought by both.
        #
        # NOT MATCHED, deliberately, and every one was read. Reference 2021/S 000-007768
        # is carried by ELEVEN separate NHS Supply Chain briefs — CT, MRI, ultrasound,
        # mammography, nuclear medicine, fluoroscopy, static and mobile X-ray among them
        # — and the page says so in terms: "The reference identifies a category, not an
        # agreement." Only the contrast injectors brief is this speciality's. The other
        # ten are the Radiology and Imaging page's, and matching on the shared reference
        # or on the word "imaging" would republish that page's whole supplier list under
        # an IR heading. Fluoroscopy is left out for the same reason: it is the general
        # screening-room route, not the IR suite. Endoscopy, Endourology and Oncology
        # Ablation Consumables is the endoscopy page's; its ablation is endoscopic, not
        # percutaneous.
        "frameworks": r"\b(angiography|contrast injectors)\b",
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,342 of framework-awards.json — 3,314 titles —
        # and every hit was read one by one before this list was fixed.
        #
        # NOT INCLUDED, deliberately, and each was tried and read:
        #   bare "ablation"  -> ten rows and at most one is this speciality. The other
        #                       nine are endoscopic oncology ablation (twice), prostatic
        #                       ablation, uterine and endometrial ablation (twice),
        #                       spinal-cord-stimulator radiofrequency ablation, a bare
        #                       "RFA Ablation" that could be cardiac or hepatic, an
        #                       MRI-guided laser ablation system, and a radiofrequency
        #                       ablation device with no speciality in the title. Gynae,
        #                       urology, endoscopy and pain. The qualified forms below
        #                       (tumour, microwave, cryo) are used instead and the one
        #                       true row, Sheffield's CT-guided percutaneous instrument
        #                       insertion, reaches the panel on "percutaneous".
        #   bare "biopsy"    -> six rows and five are breast or prostate: a breast biopsy
        #                       needle, a vacuum-assisted biopsy purchase, two Mammotome
        #                       Revolve vacuum biopsy consumable contracts and a
        #                       transperineal prostate biopsy system. The sixth is the
        #                       NHS Supply Chain framework this patch's biopsy codes
        #                       moved to on 01/07/2026, and it is matched by its own
        #                       distinctive name instead (see "needles including biopsy"
        #                       below). "biopsy needle" was tried too and buys nothing:
        #                       its only hit is the breast one.
        #   bare "drainage"  -> five rows, none of them this speciality: suction and
        #                       wound drainage, urinary catheters and drainage bags
        #                       twice, external ventricular drainage (neurosurgery) and
        #                       a CCTV drainage survey for a hospital building site.
        #                       "nephrostom" and "percutaneous" carry the real ground.
        #   bare "stent",
        #   "balloon"        -> nine stent rows and every one is coronary, urology or
        #                       aortic-cardiac: PCI balloons and stents, Cath Labs and
        #                       Cardiology Stents three times, cardiology drug-eluting
        #                       stents, Memokath urology stents twice, an Exstent
        #                       external aortic root support and a Jotec stent graft.
        #                       "balloon" alone matches nothing at all. The vascular
        #                       surgery rule refused both terms for the same reason.
        #   bare "angiograph"-> matches no award title in this data at all, and would in
        #                       a future refresh admit CT and MR angiography, which are
        #                       diagnostic imaging and the Radiology and Imaging page's.
        #                       The framework pattern above still reaches the angio suite
        #                       capital route by name, which is the honest way to it.
        #   bare "injector"  -> ten rows and six are not this patch: PET-CT
        #                       auto-injectors, a PET dose dispenser, Duodote nerve-agent
        #                       autoinjectors, and adrenaline auto-injectors for schools.
        #                       "contrast" reaches every genuine contrast-injector row
        #                       without it.
        #   bare "onyx"      -> Onyx is a Medtronic liquid embolic and would look like a
        #                       free true positive. Its only hit here is "Update of ONYX
        #                       imaging platform and existing hardware for Public Health
        #                       Wales", a software contract. Declined (rule 14).
        #   bare "coil"      -> its only hit is "Purchase of replacement coil for Logiq
        #                       E10S", an ultrasound probe coil. "embolisation coil"
        #                       would be safe and finds nothing, so nothing is claimed.
        #   "fluoroscop"     -> five rows, all diagnostic imaging capital and enabling
        #                       works (a fluoroscopy unit, a fluoroscopy suite, hybrid
        #                       room X-ray and fluoroscopy twice, an Isle of Wight
        #                       purchase). The Radiology and Imaging page's ground.
        #
        # SCOPE DECISION, STATED SO IT CAN BE JUDGED: interventional neuroradiology IS
        # admitted here. The page carries a section headed "Thrombectomy and thrombolysis
        # — peripheral and neurovascular", names Lot 2 Interventional Neuroradiology and
        # its 16 suppliers, and says outright that "selling into INR is a different
        # account". It is adjacent, the page publishes it, and NHS Supply Chain buys it
        # on the same framework, so the two Scottish INR rows below belong on this panel.
        # A reader who disagrees can see the rule and discount them.
        #
        # ONE ADMITTED ROW A READER SHOULD SEE THE REASONING ON: "CLI-OJEU-46286
        # Interventional Cardiology, Radiology, Endoscopy and Surgical Urology
        # Consumables", NHS Wales Shared Services. It is a mixed basket and three of its
        # four named specialities are other pages'. It is kept, unlike the mixed pharmacy
        # baskets the theatres and orthopaedics rules reject, because the basket is the
        # SAME product class — interventional consumables — and interventional radiology
        # is named in it as a buying category in its own right. It is a route this patch
        # is genuinely bought on, and it is not implant spend for this speciality alone.
        #
        # TERMS THAT FIND NOTHING TODAY AND ARE KEPT ANYWAY: embolisation, angioplasty,
        # atherectomy, thrombolysis, nephrostomy, endovascular, tumour/microwave/cryo
        # ablation, image-guided, uterine/prostate/genicular artery, vena cava filter.
        # None of them can mean anything but this speciality, so they cost nothing and
        # will catch the next refresh. Not one row on the panel today reaches it through
        # them, and that is stated rather than left to look like coverage.
        "include": (
            r"\b(interventional|"
            r"embolis\w*|emboliz\w*|embolic\w*|chemoembol\w*|radioembol\w*|"
            r"angioplast\w*|atherectom\w*|thrombectom\w*|thrombolys\w*|"
            r"contrast|lipiodol|percutaneous|nephrostom\w*|endovascular|"
            r"tumour ablation|tumor ablation|microwave ablation|cryoablat\w*|"
            r"image[- ]?guided|ct[- ]guided|ultrasound[- ]guided|"
            r"needles including biopsy|"
            r"uterine artery|prostate artery|genicular artery|"
            r"vena cava filter|hybrid theatre)\b"
        ),
        # Four patterns. Every one matched a real row, was read, and was rejected:
        #   anti-embolism    -> "Anti-Embolism Stockings", NHS Wales Shared Services.
        #                       Graduated compression stockings for VTE prophylaxis,
        #                       caught by the natural "embolis\w*" form on the word
        #                       EMBOLISM. Preventing an embolism is the opposite of
        #                       causing one on purpose, which is what this speciality
        #                       does, and "anti-embolic stockings" is the other common
        #                       spelling, so the guard covers both. This is the single
        #                       reason the embolisation terms need one at all.
        #   implantable
        #   cardiac          -> "Interventional Implantable Cardiac Devices and
        #                       Accessories 5643930", Regional Business Services
        #                       Organisation. Pacemakers and ICDs. Cardiac rhythm
        #                       management shares the NHS Supply Chain framework with
        #                       this patch and is not this patch.
        #   cath lab         -> "Interventional and Diagnostic Cardiac Cath Lab
        #                       Consumables [3935547]", Procurement and Logistics
        #                       Service. Interventional cardiology.
        #   heart pump       -> "Percutaneous Catheter Delivered Heart Pumps", NHS
        #                       Golden Jubilee, twice. Impella-class mechanical
        #                       circulatory support, caught on "percutaneous". Cardiac
        #                       critical care, not interventional radiology.
        "exclude": r"\b(anti[- ]?embol\w*|implantable cardiac|cath ?lab|heart pump\w*)\b",
        # ONE CPV family, and it is the only one in this data specific to this patch:
        # 33696800, X-ray contrast media, carried by "Contrast Media including Injectors
        # and Associated Products". The only other matching notice that carries CPV at
        # all carries 33110000 (imaging equipment) and 33140000 (medical consumables),
        # which corroborate everything and therefore nothing, so neither is claimed.
        # Corroboration only: the title still has to match.
        "cpv": ("33696800",),
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence appliances (IXB), stoma appliances (IXC) and elastic hosiery
        # (IXR), all community prescription routes. Nothing an interventional radiology
        # suite buys — endografts, embolics, ablation kit, biopsy and drainage sets,
        # contrast media or injectors — is listed there, and the page claims no tariff
        # presence. The panel carries none rather than reaching for the nearest part.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. The framework this speciality "
            "actually buys on is not counted below. NHS Supply Chain's Interventional "
            "Cardiology, Interventional Radiology and Interventional Neuroradiology, "
            "Cardiac Rhythm Management and Electrophysiology agreement (2021/S "
            "000-017565), whose Lot 1 carries 52 of its 67 suppliers, publishes a "
            "supplier count on its brief but no list of names, so the Hub's framework "
            "dataset records it as unparsed and its suppliers cannot be named here. "
            "Operating and Mobile Interventional Radiology Tables is missing for the "
            "same kind of reason: its brief states 12 suppliers and only 11 could be "
            "read, and a list that does not match the page is not published. Two "
            "further routes have no NHS Supply Chain framework page at all: Syringes, "
            "Needles and Associated Products (2026/S 000-002484), which took this "
            "patch's 182 biopsy product codes on 1 July 2026, and Scotland's NP68424, "
            "which has 18 lots and 27 suppliers of its own. What follows is therefore "
            "the contrast and angio-suite end of this speciality, which is what the "
            "framework record holds, plus the award trail for the rest. Being named on "
            "a framework is not evidence of volume, and being absent from one is not "
            "evidence of absence from this market. The page's Buying route section "
            "sets out all four routes with their expiry dates."
        ),
    },
    # PAGE 2801. Scope: cardiology and cardiac surgery — the catheter laboratory,
    # cardiac rhythm management and electrophysiology, structural heart, mechanical
    # circulatory support, cardiac surgery and perfusion, and cardiac physiology
    # diagnostics. Resuscitation is NOT this patch: see the framework note below.
    "cardiology-and-cardiac-surgery": {
        "label": "Cardiology and Cardiac Surgery",
        # FOUR frameworks, and the one that matters most is not among them. See the
        # coverage note: NHS Supply Chain 2021/S 000-017565, the agreement this whole
        # patch is bought on, sits in the `unparsed` list of frameworks.json because
        # its brief states a supplier count and publishes no list of names.
        #
        #   Cardiac and Pulmonary Diagnostics and Exercise (Stress) Testing Solutions
        #     (2026/S 000-012699, live from 27 July 2026, 25 suppliers) is the cardiac
        #     physiology route — ECG, ambulatory and patch monitoring, CPET. It is
        #     SHARED with respiratory on purpose: one framework really does carry both
        #     the Holter monitors and the spirometers, the same way Pressure Area Care
        #     is shared between wound care and patient handling.
        #   Structural Heart and Ventricular Assist Devices (2024/S 000-020906, 10
        #     suppliers) — TAVI, mitral and tricuspid repair, VADs.
        #   Perfusion Devices, Consumables and Associated Equipment (2024/S 000-033613,
        #     9 suppliers) — cardiopulmonary bypass. Cardiac surgery's own route.
        #   Angiography, Hybrid Theatres, Capital Equipment (2025/S 000-077456, 14
        #     suppliers) is the catheter laboratory capital route. It is claimed by
        #     three pages — this one, interventional radiology and vascular surgery —
        #     and that is correct: an angiography suite really is bought by all three,
        #     and APC Cardiovascular sits on it alongside Philips, Siemens, GE and
        #     Canon. The interventional radiology rule already states the same sharing.
        #
        # TWO FRAMEWORKS DELIBERATELY NOT MATCHED, and both were read:
        #   External Defibrillation Devices and Related Services and Accessories
        #     (2022/S 000-035844, 21 suppliers) is resuscitation, not cardiology. Its
        #     supplier list is public-access AED distributors and resuscitation
        #     training firms — British Heart Foundation, Martek Lifecare, Aero
        #     Healthcare, Imperative Training — and a cardiology account manager sells
        #     none of it. It belongs to emergency and urgent care, which is still in
        #     this rollout's queue. Implantable cardioverter defibrillators are a
        #     different market and are matched below by name.
        #   Electrodes, Ultrasound Gels, Defibrillation and Related Consumables
        #     (2023/S 000-030987, 37 suppliers) is a mixed ward-consumables basket.
        #     ECG electrodes sit on it, but so do ultrasound gel and Lyreco, KCI and
        #     Rocket Medical. Publishing its 37 names as cardiology suppliers would
        #     put an office-supplies wholesaler on this page.
        "frameworks": r"\b(angiography|cardiac and pulmonary diagnostics|perfusion devices|structural heart)\b",
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,342 of framework-awards.json — 3,314 titles —
        # and all 58 admitted titles were read one by one before this list was fixed.
        #
        # NOT INCLUDED, deliberately, and every one was tried and read:
        #   bare "cardi"      -> matches CARDIFF. "CPD Courses 26/27 Cardiff University"
        #                        and "PUBLIC HEALTH WALES BTW CARDIFF - BUILDING WORKS"
        #                        both matched it. The `cardi[ao]` form below is used
        #                        instead and takes neither.
        #   bare "heart"      -> "Healthy Hearts and Building Foundations", St Helens
        #                        Council. A council public-health programme. The
        #                        qualified forms (heart valve, heart pump, structural
        #                        heart) take every genuine row without it.
        #   bare "valve"      -> "Installation of HTG valves across all THQ Building",
        #                        Leeds. Plumbing. "heart valve", "mitral" and
        #                        "tricuspid" reach the real ones.
        #   bare "ventricular"-> "4183924 External Ventricular Drainage (EVD)".
        #                        Neurosurgery. "ventricular assist" is used instead.
        #   bare "ablation"   -> ten rows and none of them is cardiac: endoscopic
        #                        oncology ablation, uterine and endometrial ablation,
        #                        spinal cord stimulator radiofrequency ablation, an
        #                        MRI-guided laser ablation system, a CT-guided
        #                        percutaneous insertion. The interventional radiology
        #                        rule refused it for the same reason. "catheter
        #                        ablation" and "pulsed-field ablation" are used instead
        #                        and find nothing today, which is stated rather than
        #                        left to look like coverage.
        #   bare "stent"      -> Memokath urology stents twice, a Jotec aortic stent
        #                        graft. The genuine coronary rows all carry the word
        #                        CARDIOLOGY ("Cath Labs and Cardiology Stents" three
        #                        times, "Cardiology Stents - DES") and reach the panel
        #                        that way.
        #   bare "defibrillat"-> "Defibrillators", "Defibrillators and AEDs",
        #                        "Preliminary Market Engagement For Defibrillators".
        #                        External defibrillation is resuscitation, consistent
        #                        with the framework decision above. "implantable
        #                        cardioverter" is included instead.
        #   "\bicd\b"         -> its one hit, "Purchase of Pacemakers, ICD's & CRT's",
        #                        already reaches the panel on "pacemakers". ICD is also
        #                        the International Classification of Diseases and would
        #                        admit a clinical-coding contract on the next refresh,
        #                        so it is not used. "\bcrt\b" is refused for the same
        #                        reason: cathode ray tube, community response team.
        #   "\bvad\b"         -> VAD is also VASCULAR ACCESS DEVICE, which is another
        #                        page's whole speciality. "ventricular assist" is used.
        #   bare "ffr"        -> fractional flow reserve looks like a free true
        #                        positive and matches DIFFRACTOMETER: three university
        #                        X-ray diffractometer purchases. Refused outright.
        #   bare "pacing"     -> its one hit, "Radiology, Cardiology and Pacing Packs",
        #                        already reaches the panel on "cardiology". The
        #                        qualified pacing forms below are kept for the next
        #                        refresh.
        #   bare "tavi"/"tavr"-> kept, but only with word boundaries on BOTH sides.
        #                        Without the trailing boundary "tavi" matches
        #                        TAVISTOCK, ZETAVIEW and EXTAVIA (interferon beta-1b).
        #                        With it, all three fall out and nothing is lost.
        #
        # TERMS THAT FIND NOTHING TODAY AND ARE KEPT ANYWAY, stated so the list is not
        # mistaken for coverage: coronary, angina, myocardial, holter, catheter
        # ablation, pulsed-field ablation, implantable cardioverter, the qualified
        # pacing forms, TAVI, TAVR, tricuspid, atrial fibrillation and mechanical
        # circulatory. None of them can mean anything but this speciality, so they cost
        # nothing and will catch the next refresh.
        "include": (
            r"\b(cardi[ao]\w*|echocardi\w*|myocardial|coronary|angina|"
            r"\becg\b|electrocardiogra\w*|holter|"
            r"cath ?labs?\b|catheteri[sz]ation lab\w*|"
            r"pacemakers?|pacing (?:lead|wire|system|pack)s?|implantable cardioverter|"
            r"electrophysiolog\w*|pulsed[- ]field ablation|catheter ablation|"
            r"structural heart|transcatheter|\btavi\b|\btavr\b|heart valves?|"
            r"mitral|tricuspid|aortic root|"
            r"ventricular assist|impella|heart pumps?|mechanical circulatory|\becmo\b|"
            r"atrial appendage|atrial fibrillation|"
            r"perfusion|oxygenators?)\b"
        ),
        # Seven patterns. Every one matched a real row, was read, and was rejected:
        #   medicines        -> "NP35923 Cardiovascular & Respiratory Medicines" and
        #                       "Cardiovascular & Respiratory Medicines", both the
        #                       Common Services Agency. A Scottish national pharmacy
        #                       contract for cardiovascular drugs. This page covers the
        #                       device and service patch, not the medicines route, and
        #                       the theatres and orthopaedics rules reject mixed
        #                       pharmacy baskets on the same ground.
        #   ophthalm         -> "Purchase of Ophthalmology Visual Electrophysiology
        #                       System", NHS Wales. Visual evoked potentials. This is
        #                       the single reason "electrophysiolog" needs a guard, and
        #                       it needs one badly: electrophysiology is the largest
        #                       lot on this patch's successor framework.
        #   lifeport         -> "LifePort Perfusion Consumables", Manchester, twice
        #                       (an award notice and a VEAT). LifePort is Organ
        #                       Recovery Systems' kidney transport perfusion machine.
        #                       Transplant, not cardiopulmonary bypass.
        #   static perfusion,
        #   perfusion fluid  -> "Cold Static Perfusion Fluid UW Solution" and "cold
        #                       static perfusion fluid solution", both NHS Blood and
        #                       Transplant. University of Wisconsin organ preservation
        #                       solution. Two guards because the two notices word it
        #                       two ways.
        #   anaesthe         -> "Patient Monitors, Anaesthetics Machines, Ventilators &
        #                       ECG", Common Services Agency. A four-item basket in
        #                       which ECG is the minority item and anaesthesia and
        #                       critical care are the buyers. No genuine cardiac row in
        #                       this data mentions anaesthesia, so the guard costs
        #                       nothing.
        #   principal designer-> "Cath Lab 1 Refurbishment CDM Principal Designer
        #                       Services", Imperial. CPV 71315200, building consultancy
        #                       services, awarded to Ingleton Wood LLP, an architecture
        #                       and surveying practice. An architect's appointment, not
        #                       a cardiology purchase. Capital and estates ground.
        #   training programme-> "National Education and Training for NHS Healthcare
        #                       Science - Scientists Training Programme (STP) and
        #                       Echocardiography Training Programme (ETP)", NHS
        #                       England. CPV 80000000, education services, no supplier
        #                       named. Workforce commissioning, not a market contract.
        #                       The guard is "training programme", NOT "training":
        #                       "Medical Training Equipment" is part of a genuine
        #                       cardiac physiology maintenance award and must survive.
        "exclude": (
            r"\b(medicines|ophthalm\w*|lifeport|static perfusion|perfusion fluid|"
            r"anaesthe\w*|principal designer|training programme)\b"
        ),
        # FOUR CPV prefixes, and every one of them actually fires on a matching notice
        # in this data. A family that corroborates nothing is not claimed. All four
        # descriptions were read back from Find a Tender's own OCDS API on 09/09/2026,
        # not from memory:
        #   33112340  Echocardiographs
        #   33121500  Electrocardiogram
        #   33123     Cardiovascular devices, and beneath it 33123200 Electrocardiography
        #             devices and 33123230 Cardiographs
        #   85121231  Cardiology services
        # Corroboration only, never admission: the title still has to match. 33121000,
        # Long term ambulatory recording system, is deliberately left out because it is
        # not cardiac-specific, and 33182 Cardiac devices is left out because not one
        # notice in this data carries it.
        "cpv": ("33112340", "33121500", "33123", "85121231"),
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence appliances (IXB), stoma appliances (IXC) and elastic hosiery
        # (IXR), all community prescription routes. Nothing this speciality buys —
        # pacemakers, leads, coronary stents, heart valves, oxygenators, cath lab
        # capital — is listed there. The panel carries none rather than reaching.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. The single agreement this "
            "speciality is mostly bought on is not counted below. NHS Supply Chain's "
            "Interventional Cardiology, Interventional Radiology and Interventional "
            "Neuroradiology, Cardiac Rhythm Management and Electrophysiology framework "
            "(2021/S 000-017565), which carries the coronary, rhythm management, "
            "electrophysiology and intracardiac monitoring lots and 67 suppliers, "
            "publishes a supplier count on its brief but no list of names, so the Hub's "
            "framework dataset records it as unparsed and its suppliers cannot be named "
            "here. That agreement ends on 26 February 2027 and its successor, Find a "
            "Tender 2026/S 000-043775 Total Cardiology and Vascular Solutions, has an "
            "estimated award decision of 8 December 2026, so the framework picture on "
            "this patch is due to change wholesale within the year. Resuscitation is "
            "also deliberately absent: the External Defibrillation Devices framework "
            "and the Electrodes, Ultrasound Gels and Defibrillation consumables "
            "framework are not counted here, because their supplier lists are public "
            "access defibrillator distributors and general ward consumables rather than "
            "this speciality's market. What follows is therefore the structural heart, "
            "perfusion, cardiac physiology and catheter laboratory capital end of the "
            "patch, which is what the framework record holds, plus the award trail for "
            "the rest. Being named on a framework is not evidence of volume, and being "
            "absent from one is not evidence of absence from this market. The page's "
            "Buying route and Framework calendar sections set out the full picture with "
            "their expiry dates."
        ),
    },
    # PAGE 2911. The live id was read back from the WordPress.com API on 09/09/2026:
    # slug nutrition-and-dietetics, title "Nutrition and Dietetics (Subscribers only)".
    # Scope, in the page's own words: "Oral nutritional supplements, enteral tube
    # feeding and parenteral nutrition, across acute and community." The page's own
    # research, verified 08/09/2026, establishes that this is two markets sharing a
    # clinical pathway and almost nothing else: a community prescribing market worth
    # 638.2m of net ingredient cost in England in 2024/25, written on FP10 and reimbursed
    # under Part XV of the Drug Tariff, entirely outside any framework; and an acute
    # device market of 89m over the whole term of one NHS Supply Chain framework, four
    # fifths of which is syringes and tubes rather than food. This panel can only see the
    # second of those two. The coverage note below says so on the page rather than
    # leaving a reader to infer that 89m is the market.
    # PAGE 2927. The only speciality in this rollout so far whose patch carries NO
    # NHS Supply Chain framework at all. That is the commercial story of obesity and
    # weight management, not a hole in the data: the money moves on an FP10 or through
    # a hospital specialist service, and the service end is commissioned by ICBs,
    # health boards and local authorities on their own notices. The page's own build
    # (08/09/2026) reached the same finding independently from the NHSBSA Prescription
    # Cost Analysis files.
    "obesity-and-weight-management": {
        "label": "Obesity and Weight Management",
        # NO FRAMEWORK, DELIBERATELY, and this is the honest answer rather than a
        # pattern that happens to find nothing. All 121 NHSSC framework names were read
        # on 09/09/2026 and not one is this speciality's. There is no obesity, weight
        # management or bariatric framework.
        #
        # THE TRAP THAT WAS REFUSED. Arjo won both bariatric equipment contracts in this
        # data (Bariatric Equipment Rental, Lancashire Teaching Hospitals, 24/08/2026;
        # Bariatric Hire Contract, James Paget, 04/12/2025) and Arjo is named on four
        # NHSSC frameworks: Pressure Area Care and Patient Handling, Aids for Daily
        # Living, Operating Theatres Equipment, and Vascular Therapy. Claiming any of
        # them here would have produced a fuller-looking panel and a false one. Every
        # one of those four is another page's framework, counted there: the first two on
        # Patient Moving and Handling (2913), the third on Theatres and Surgical, the
        # fourth on Vascular Surgery and PAD. One shared supplier does not make a
        # patient-handling framework an obesity framework, on exactly the ground the
        # nutrition rule keeps hospital catering out. build_frameworks therefore returns
        # an empty list, the Suppliers tab is empty for the same reason, and the rules
        # block says so in the file rather than leaving a reader to wonder.
        "frameworks": None,
        # Derived by running the candidate include over all 1,972 rows of
        # tender-history.json and all 1,342 of framework-awards.json on 09/09/2026 and
        # reading all 12 hits one by one. 8 were this speciality, 4 were not.
        #
        # NOT INCLUDED, deliberately, kept out at the include stage rather than swept
        # back out at the exclude stage:
        #   tier 2 / tier 3 / tier 4 (bare) -> the weight management tiers are real
        #     vocabulary on this patch, but bare they are not this speciality at all.
        #     "Tier 2 Cardiology and Direct Access Diagnostics" (NHS Lancashire and
        #     South Cumbria ICB, FCMS (NW), 17/08/2026) and "CAMHs Tier 4 Beds and
        #     associated services" (Avon and Wiltshire Mental Health Partnership,
        #     11/08/2026) both matched. NHS commissioning tiers services of every kind.
        #     The genuine rows reach this panel on "weight management" instead, which is
        #     how "Child Tier 2 Weight Management Service" is matched.
        #   lifestyle programme / lifestyle service -> "NHS South West London ICB -
        #     Long-Term Conditions (LTC) Community Outreach, Expert Patient Programme
        #     (EPP) LTC Self-Management And Pentathlon Healthy Lifestyle Programme
        #     Services." (Asian Resource Centre of Croydon, 20/08/2026). A long-term
        #     conditions self-management contract. Healthy lifestyle is a whole public
        #     health category and most of it is not weight.
        #   exercise referral -> same ground, and not one row matched it.
        #   gastrectomy (bare) -> not one row matched, and bare gastrectomy is upper GI
        #     cancer surgery far more often than it is bariatric. Only the qualified
        #     "sleeve gastrectomy" is used.
        #   semaglutide, tirzepatide, liraglutide, Mounjaro -> not one row matched, and
        #     each is dual-licensed. This page's own build recorded the structural
        #     finding that tirzepatide and semaglutide are classified under Drugs used
        #     in diabetes, not under the BNF section named for obesity. A notice naming
        #     the molecule could as easily be the diabetes and endocrinology patch,
        #     which has its own page. The obesity-only brands are included instead:
        #     Wegovy (semaglutide 2.4mg) and Saxenda (liraglutide 3mg) are licensed for
        #     weight management only, as are orlistat, Xenical and Mysimba, and none of
        #     them can belong to another patch.
        "include": (
            r"\b(obesity|obese|adiposity|bariatric|"
            r"weight[- ]?(?:management|loss|reduction)|healthy weight|"
            r"gastric (?:band|banding|bypass|sleeve|balloon)|sleeve gastrectomy|"
            r"metabolic surgery|"
            r"orlistat|xenical|mysimba|wegovy|saxenda)\b"
        ),
        # ONE PATTERN, and it is here because a real row matched the include above and
        # was read and rejected:
        #   covid / vaccination -> "Combined Safety Syringes and Needles for COVID-19
        #     Vaccination Programme - Morbidly Obese Requirement" (NHS Supply Chain
        #     operated by DHL, Owen Mumford and Reliance Medical, 16/09/2021). It
        #     matches on "Obese" and it is a needle procurement: the phrase is a needle
        #     LENGTH specification for vaccinating patients with a higher BMI, not an
        #     obesity service or an obesity product. "obese" cannot be dropped from the
        #     include list, since it is the core word of the speciality, so it is
        #     guarded here. The guard is deliberately narrow: a COVID vaccination
        #     syringe contract is never this speciality, whereas "syringe" or "needle"
        #     on their own would throw away a genuine GLP-1 pen needle row if one ever
        #     appeared.
        "exclude": r"\b(covid(?:[- ]?19)?|vaccination)\b",
        # NO CPV FAMILY IS CLAIMED. The seven service awards on this patch carry
        # 85100000 (health services) and 85000000 (health and social work), which are
        # the whole of healthcare and corroborate nothing; the bariatric equipment
        # rental carries 33192000 and 33192120 (medical furniture and hospital beds),
        # which are the patient-handling family and belong to that page. Nothing here
        # is specific to obesity, so nothing is recorded. Corroboration that
        # corroborates every speciality equally is not corroboration.
        #
        # NO DRUG TARIFF PART, and it is worth being explicit. Part IX reimburses
        # dressings and elastic hosiery (IXA), incontinence appliances (IXB), stoma
        # appliances (IXC) and elastic hosiery (IXR). Obesity medicines are not
        # appliances and are not in Part IX at all; they are dispensed against Part
        # VIIIA and, for the specialist-service routes, not through community
        # prescribing at all. The panel carries no tariff rather than reaching.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. This panel shows the service and "
            "equipment end of this patch, and that is much the smaller end. Obesity and "
            "weight management is the one speciality in this Hub with no NHS Supply Chain "
            "framework at all, because almost none of the money is bought through one. It "
            "moves two other ways instead. The first is community prescribing: Mounjaro "
            "alone accounted for 574,302,390 of net ingredient cost across 3,064,223 items "
            "in England in 2025/26, which is 4.93% of England's entire community "
            "prescribing bill from one brand, and none of it can appear in a framework or "
            "an award notice because none of it is bought that way. The second is hospital "
            "specialist services, including the 7,260 NHS-funded bariatric procedures "
            "carried out in 2025/26. What follows is what the procurement record does "
            "hold: ICB, health board and local authority awards for tiered and digital "
            "weight management services, and trust contracts for bariatric equipment "
            "hire. Absence from this panel is not absence from this market, and no "
            "supplier list is published here at all, because there is no framework for "
            "one to be drawn from. The page's Market intelligence and Deep dive sections "
            "carry the prescribing and bariatric surgery figures with their sources."
        ),
    },
    "nutrition-and-dietetics": {
        "label": "Nutrition and Dietetics",
        # Two NHSSC frameworks and no more. Both are named on this page's own calendar
        # with expiry dates read at NHS Supply Chain's own contract launch briefs:
        #   Enteral Feeding, Bile Bags and Associated Products (2025/S 000-028317),
        #     19 suppliers, ends 13 July 2027. The acute device route, and the one the
        #     page's Buying route section names.
        #   Infant Feeding and Accessories (2023/S 000-011743), 18 suppliers, ends
        #     28 February 2028, extension already used. Roughly half its supplier list
        #     is condition-specific formula (Danone Nutricia Early Life Nutrition, HiPP,
        #     Kendal Nutricare, Nestle Nutrition, Babease, Heinz) and half is expression
        #     and feeding hardware (Ardo, Medela, MAM, Alcado). It is counted here
        #     because this page's own calendar places it on this patch, and because the
        #     maternity and neonatal page names a different buying route entirely
        #     (Maternity, Obstetrics, Gynaecology and Sexual Health Products) and does
        #     not claim it. See the note on breast pumps in the include list.
        # DELIBERATELY NOT COUNTED: the five NHSSC Food and Facilities frameworks.
        # Ambient Food, Fresh Food DPS, Multi Temperature Food Solutions, Food Vending
        # Solutions and Catering Consumables and Equipment are hospital catering, bought
        # by facilities, and their supplier lists are Weetabix, Walkers Snacks, Kraft
        # Heinz, Tilda and Brake Bros. Aymes and Danone do appear on Ambient Food, and
        # that is exactly the trap: one shared supplier does not make a catering
        # framework a dietetics framework. "food" and "catering" are therefore absent
        # from every pattern in this rule, kept out at the include stage rather than
        # swept back out at the exclude stage.
        # NOT USED, and worth recording: \bbile\b. It matches "Mobile", and NHSSC has
        # four frameworks whose names begin with that word. The enteral framework is
        # reached on "enteral" instead.
        "frameworks": r"\b(enteral|parenteral|nutrition\w*|dietet\w*|infant feeding)\b",
        # Derived by running this include over all 1,972 rows of tender-history.json and
        # all 1,342 of framework-awards.json and reading every hit. 26 rows matched and
        # were read one by one.
        #
        # NOT INCLUDED, deliberately:
        #   food, catering, hydration -> hospital catering, as above. "Central
        #     Procurement of Vitamin D Food Supplements Clinically Extremely Vulnerable"
        #     (DHSC, twice, 2021) is the reason this matters: a shielding-programme
        #     vitamin mailout, supplied by The Oxford Health Company and Cuttlefish
        #     Limited, sitting in BNF 0906 vitamins rather than the 0913 and 0914
        #     sections this page measures. Keeping "food" out keeps it out.
        #   milk (bare)   -> "BVD PCR Test Kits for Serum and Milk Samples", SRUC,
        #     supplied by IDEXX. Bovine viral diarrhoea testing in cattle. Only the
        #     qualified forms "milk kitchen" and "milk bank" are used.
        #   breast pump, breast milk collection, sterile milk bottles -> these matched
        #     real NHS rows ("Breast Pumps and Breast Milk Collection Sets [5180689]",
        #     Ardo Medical; "Sterile Milk Bottles [4692898]", Mediq) and they are
        #     genuine NHS purchases, but they are the maternity and neonatal patch,
        #     which has its own page. The framework is counted here because the page
        #     put it here; the expression hardware awards are left to the page that
        #     owns them, rather than claimed twice across the Hub.
        #   dysphagia, gluten free, coeliac -> not one row matched any of them, and each
        #     straddles another patch (speech and language therapy for the first,
        #     catering for the second). Root rule 14: no pattern earns its place by
        #     making a panel look fuller.
        "include": (
            r"\b(enteral|parenteral|nutrition|nutritional|dietetic\w*|dietitian\w*|"
            r"dietician\w*|sip feeds?|tube feed\w*|"
            r"feeding (?:tubes?|pumps?|sets?|systems?|services?|products?|"
            r"accessor\w*|consumables?)|"
            r"nasogastric|naso[- ]gastric|orogastric|oro[- ]gastric|nasojejunal|"
            r"gastrostom\w*|jejunostom\w*|peg|bile bags?|"
            r"thickeners?|thickening agents?|malnutrition|malnourish\w*|"
            r"infant formula|milk kitchens?|milk bank\w*)\b"
        ),
        # Four patterns. Every one matched a real row under the include above, was read,
        # and was rejected:
        #   endocrine       -> "Gastro Intestinal, Endocrine, Nutrition & Blood Generic
        #                      Medicines" (2021) and "Gastrointestinal, Endocrine,
        #                      Nutrition & Blood Medicines" (2025), both the Common
        #                      Services Agency, both awarded to Kent Pharmaceuticals. A
        #                      Scottish national generic medicines basket organised by
        #                      BNF chapter, in which Nutrition is one of four headings.
        #                      The guard is "endocrine" rather than "medicines" on
        #                      purpose: parenteral nutrition is genuinely bought through
        #                      pharmacy on this patch, and "medicines" would throw away
        #                      real rows. A basket that lists Endocrine alongside
        #                      Nutrition is a medicines basket, and endocrinology has its
        #                      own page in any case.
        #   asparaginase    -> "Procurement of Peg-asparaginase Injection from Alloga
        #                      UK", Belfast Health and Social Care Trust. Pegaspargase is
        #                      a PEGylated chemotherapy enzyme. It matches because a
        #                      hyphen is a word boundary, so \bpeg\b fires on
        #                      "Peg-asparaginase". PEG is kept in the include list
        #                      because percutaneous endoscopic gastrostomy is core
        #                      vocabulary on this patch, and guarded here instead.
        #   cpd             -> "CPD Courses 26/27 British Dietetic Association (BDA)",
        #                      Mid and South Essex NHS Foundation Trust, CPV 80000000,
        #                      education services. A trust buying continuing professional
        #                      development for its own dietitians. Workforce training,
        #                      not a market contract, on the same ground as the
        #                      cardiology rule's "training programme" guard.
        #   non-parenteral  -> "NHS National Framework for Generics Orals, Non-Parenteral
        #                      & Housekeeping", NHS England, CPV 33600000, pharmaceutical
        #                      products. It matches on the word "Parenteral" inside
        #                      "Non-Parenteral", which is the exact opposite of what it
        #                      says. A generic oral medicines framework.
        "exclude": r"\b(endocrine|asparaginase|cpd|non[- ]parenteral)\b",
        # ONE CPV prefix, and it fires on exactly one notice in this data, which is a
        # genuine one. 33692200 is "Parenteral nutrition products", read back from Find
        # a Tender's own OCDS API on 09/09/2026 (release ocds-h6vhtk-06eba1, notice
        # 080876-2026, "Inpatient Parenteral Nutrition Products"), not from memory.
        # 33692300 Enteral feeds and 15882000 Dietetic products are deliberately left
        # out: not one notice in this data carries either, and a family that corroborates
        # nothing is not claimed. Corroboration only, never admission: the title still
        # has to match.
        "cpv": ("33692200",),
        # NO DRUG TARIFF PART, and this one is worth being explicit about because the
        # opposite is easy to assume. Part IX reimburses dressings and elastic hosiery
        # (IXA), incontinence appliances (IXB), stoma appliances (IXC) and elastic
        # hosiery (IXR). It carries no enteral feeding or nutrition category at all: the
        # September 2026 Part IX was searched in full on 08/09/2026 for this page and
        # nothing on this patch is listed in it. Feeds, oral nutritional supplements and
        # gluten-free products are reimbursed under Part XV, borderline substances, on
        # ACBS approval, which is a different list and is not in the Hub's tariff
        # dataset. The panel carries no tariff rather than reaching for Part IXA.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. This panel shows the smaller "
            "half of this patch by value, and it is much the smaller half. Nutrition and "
            "dietetics is two markets. The community market is prescribing: 638.2m of "
            "net ingredient cost in England in 2024/25 across BNF sections 0913 and "
            "0914, decided by a dietitian, written on an FP10, gated by ACBS approval "
            "and the ICB formulary, reimbursed under Part XV of the Drug Tariff, and "
            "entirely outside every framework and every award notice counted below. Two "
            "companies, Nutricia and Abbott, hold 68.7% of that money. None of it can "
            "appear in a framework or tender feed, because none of it is bought that "
            "way. What follows is the acute device route only: NHS Supply Chain's "
            "Enteral Feeding, Bile Bags and Associated Products framework (2025/S "
            "000-028317, 19 suppliers, 89m over its full term, ending 13 July 2027), the "
            "Infant Feeding and Accessories framework (2023/S 000-011743, 18 suppliers, "
            "ending 28 February 2028), and the trust and national award trail for feeds, "
            "pumps and parenteral nutrition. Being named on a framework here is not "
            "evidence of volume, and being absent from one is not evidence of absence "
            "from this market: the largest supplier on this patch by money earns most of "
            "it through a route that has no framework at all. The page's Market "
            "intelligence section carries the community figures, their derivation rule "
            "and their source."
        ),
    },
    # PAGE 2800. Scope: neurology and neurosurgery — the neurology outpatient
    # pathway, clinical neurophysiology, elective and emergency neurosurgery, and
    # neuromodulation. Stroke is NOT this patch: it has its own page and its own
    # pathway, which is why thrombectomy and every stroke service row is kept out
    # below. Neurorehabilitation is not this patch either: those are ICB-commissioned
    # bed and community contracts and they belong to the rehabilitation page.
    "neurology-and-neurosurgery": {
        "label": "Neurology and Neurosurgery",
        # TWO frameworks out of the five the page names, and the three that are left
        # out are named here rather than quietly dropped.
        #
        #   Neuromodulation Devices and Associated Products (2023/S 000-034841, to
        #     18/03/2028) is the only NHSSC framework named after any part of this
        #     speciality. All 23 suppliers are neuromodulation suppliers, its three
        #     lots are Deep Brain Stimulation, Spinal Cord Stimulation and Other
        #     Neuromodulation, and it is unambiguously this patch's.
        #   Surgical Navigation Systems with Associated Options and Related Services
        #     (2021/S 000-007768, to 31/03/2028) is SHARED with the orthopaedics and
        #     trauma page, which claims it too. That sharing is deliberate and correct,
        #     the same way Pressure Area Care is shared between wound care and patient
        #     handling: the brief's first product category is "Cranial Neurosurgery/
        #     Spinal Surgery Navigation System" and it names Cranial and Neuro surgeons
        #     among the users, so the navigation route really is bought by both.
        #
        # NOT MATCHED, deliberately, and each was read on its own brief:
        #   Robotic Medical Equipment and Associated Accessories (2024/S 000-004668)
        #     carries Lot 2 Spinal and Neurological Robots, and that lot holds
        #     Medtronic Limited and no other supplier. Claiming the framework would put
        #     its other five suppliers — CMR Surgical, Intuitive Surgical, Johnson and
        #     Johnson Medical, MCT Lifesciences and Procept BioRobotics, none of whom
        #     holds the neurological lot — under a neurology Suppliers heading and
        #     attribute to them a neurosurgical presence the brief does not. It is
        #     counted on the Theatres and Surgical page. The award trail still reaches
        #     this panel where a notice names this patch.
        #   Total Orthopaedic Solutions 3 (2023/S 000-025037) is where spinal implants
        #     sit, and the page says so. Its supplier list is 101 names and is an
        #     orthopaedic list; republishing it here would bury the two dozen names
        #     that are this speciality's under five dozen that are not. It is counted
        #     on the orthopaedics and trauma page.
        #   Operating (Theatre and Outpatient) Microscopes and Associated Accessories
        #     (2022/S 000-020537), whose Lot 1 carries Neurological Operating, IS in
        #     frameworks.json but in its `unparsed` list, not its `frameworks` list:
        #     the brief states 10 suppliers and 8 incumbents and then names 9 and 7, so
        #     a list that does not match its own page is not published. build_frameworks
        #     reads only the parsed list, so it cannot be counted here either way. Its
        #     award notice does reach the Awards list below on "operating microscope".
        "frameworks": r"\b(neuromodulation|surgical navigation)\b",
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,342 of framework-awards.json — 3,314 titles —
        # and every hit was read one by one before this list was fixed. A first,
        # deliberately over-wide draft using bare "neuro\w*", "brain", "stereotact\w*",
        # "shunt\w*" and "aneurysm" returned 40 rows of which 10 were not this
        # speciality. Most of those were cut at the include stage rather than swept
        # back out at the exclude stage, which is why the include list names the
        # neuro- compounds one by one instead of matching the prefix.
        #
        # NOT INCLUDED, deliberately, and every one was tried and read:
        #   bare "neuro\w*"    -> catches four things that are not this speciality and
        #     nothing this speciality needs. "Purchase of AAA Netspot ... to Detect
        #     Neuroendocrine Tumours" and "Purchase of 177Lu-Dotatate (Lutathera) to
        #     treat patients with neuroendocrine tumours" (both Royal Marsden) are
        #     oncology; "Neurodevelopmental Support for Children, Families and
        #     Professionals" (NHS Cheshire and Merseyside ICB, twice) is a children's
        #     autism and ADHD support service; "Neurodiverse Environmental Audits"
        #     (Oxford Health, 10/08/2026) is an estates audit; and "Neuro MRI: MRI 1
        #     and MRI 3" (King's College, 19/08/2026) is an MRI scanner purchase, which
        #     is the radiology and imaging page's patch whatever the suite is called.
        #   bare "brain"       -> its only hit is "Brain Injury Rehabilitation Service"
        #     (NHS Norfolk and Suffolk ICB, 18/08/2026), a rehabilitation bed contract.
        #     Deep brain stimulation is matched by its own full phrase instead.
        #   bare "stereotact\w*" -> its only two hits are the same Royal Free contract
        #     twice, "PR8980 - RFL Mammography Equipment consumables for Stereotactic
        #     Procedure", which is breast biopsy. The genuine stereotactic row here,
        #     Belfast's Neurosurgery Vantage Frame, is matched on "neurosurgery".
        #   bare "shunt\w*"    -> matches Cambridge's "Medtronic Ltd - EVD and Shunts"
        #     and nothing else in this data, but a bare shunt is an arteriovenous
        #     dialysis shunt or a cardiac shunt at least as often as it is a CSF one.
        #     That row is matched on "EVD" instead, which is the neurosurgical term in
        #     the same title.
        #   bare "spinal" / "spine" -> nine rows and one at most is this speciality.
        #     "Purchase of Orthopaedic Spinal and Scoliosis Implants and Consumables"
        #     (NHS National Services Scotland, three times), "Bridging Contract -
        #     Replacement of Spinal Implants and Consumables" (Nottingham) and "BWC -
        #     Edge Medical Ltd - Spinal Surgical consumables" (Birmingham Women's and
        #     Children's) are orthopaedic spine, bought on Total Orthopaedic Solutions
        #     3; "Spinal, Epidural and Associated Products" and "Epidural Pumps" are
        #     anaesthesia. Only the qualified forms are used: "spinal cord stimulation"
        #     and "spinal navigation".
        #   bare "microscope"  -> six rows and five are not this speciality: an Olympus
        #     BX53 laboratory microscope, an ophthalmic microscope, an ENT theatre
        #     microscope, a multi-spectral light sheet research microscope at the
        #     University of Glasgow and a Class II cabinet with an integrated
        #     microscope. Only "operating microscope" is used, which matches the NHSSC
        #     framework award and nothing else.
        #   "thrombectomy"     -> stroke, which is its own page. The one row that is
        #     genuinely this patch's as well, NHS National Services Scotland's
        #     "Interventional Neuro Radiology and Thrombectomy Consumables"
        #     (28/07/2025), reaches the panel on "neuro radiology" instead.
        #   bare "INR"         -> its only hit, "INR and Thrombectomy Consumables"
        #     (NHS National Services Scotland, 23/04/2021), is the 2025 contract above
        #     under an earlier name, so the abbreviation is genuinely interventional
        #     neuroradiology there. It is still refused: INR is the international
        #     normalised ratio far more often, that is a coagulation test on the
        #     haematology patch, and nothing in the title tells the two apart. The
        #     successor contract is on the panel under its full name.
        #   "spinal muscular atrophy" -> its only hit, "Referapatient for zolgensma for
        #     spinal muscular atrophy" (NHS England, 11/08/2026), is a referral-platform
        #     contract for a commissioned gene therapy, not a neurology purchase.
        #
        # ONE EDGE CASE KEPT, and it is kept on purpose. "EMG System" (University of
        # Salford, 13/08/2026) is a university purchase, not an NHS one, and is almost
        # certainly a biomechanics laboratory rather than a clinical neurophysiology
        # department. It stays because an EMG system is genuinely this speciality's
        # product and the only thing that marks the row out is its buyer — and buyer
        # names are never matched on here, in either direction. Excluding it would mean
        # writing a rule about who is buying, which is a different and worse rule than
        # one about what is being bought.
        "include": (
            r"\b(neurolog(?:y|ical|ists?)|neurosurg\w*|neurophysiolog\w*|"
            r"neuromodulation|neurostimulat\w*|neuromonitoring|"
            r"neuro[- ]?navigation|neuro[- ]?radiolog\w*|neuro[- ]?vascular|"
            r"neuro[- ]?oncolog\w*|deep brain stimulat\w*|spinal cord stimulat\w*|"
            r"vagus nerve stimulat\w*|spinal[- ]?navigation|cranial[- ]?navigation|"
            r"operating microscopes?|intracranial|cranioplast\w*|craniotom\w*|"
            r"craniect\w*|burr hole|cranial (?:implant|fixation|plate)|"
            r"dural|dura mater|hydrocephal\w*|ventriculoperitoneal|"
            r"cerebrospinal fluid|external ventricular drain\w*|evd|"
            r"aneurysm clips?|electroencephalo\w*|eeg|emgs?|electromyograph\w*|"
            r"evoked potential|nerve conduction|epilep\w*|parkinson\w*|"
            r"multiple sclerosis|motor neuron\w*)\b"
        ),
        # Two patterns, and both were put here because a real row matched the include
        # list above and was wrong:
        #   rehabilitation          -> "Neurological Rehabilitation Service" (NHS
        #     Greater Manchester ICB, 20/08/2026). A commissioned rehabilitation
        #     service, which is the rehabilitation, prosthetics and orthotics page's
        #     patch, not a neurology or neurosurgery purchase. It also holds out
        #     "Provision of Specialist Level 2b Neuro-rehabilitation Beds" and "Brain
        #     Injury Rehabilitation Service" if either is ever reworded into a form the
        #     include list reaches.
        #   interventional cardiology -> "INTERVENTIONAL CARDIOLOGY, INTERVENTIONAL
        #     RADIOLOGY AND INTERVENTIONAL NEURORADIOLOGY, CARDIAC RHYTHM MANAGEMENT
        #     AND ELECTROPHYSIOLOGY" (NHS Supply Chain, 22/11/2022), matched on
        #     "neuroradiology". The notice really does carry an interventional
        #     neuroradiology lot, but it is the cardiology and interventional radiology
        #     pages' framework and is counted there, its neuroradiology share cannot be
        #     separated out of the title, and the page's own Buying route section names
        #     five frameworks and not this one. Publishing it here would contradict the
        #     page a reader is standing on.
        "exclude": r"\b(rehabilitation|interventional cardiology)\b",
        # NO CPV FAMILY, and that is checked rather than skipped. Every matching notice
        # in framework-awards.json that carries CPV codes at all carries only generic
        # ones: 85100000 and 85111000 health services, 85112200 outpatient services,
        # 33140000 medical consumables, 31711140 electrodes, 33698000 clinical
        # products. Not one is specific to neurology or neurosurgery, so none is
        # claimed. A CPV code could not admit a notice on its own in any case.
        #
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence appliances (IXB), stoma appliances (IXC) and elastic hosiery
        # (IXR). Nothing this speciality buys is listed there. Its community spend is
        # real and large — 411.3m pounds a year across BNF sections 4.8 and 4.9, on the
        # page's own PCA analysis — but that is Part VIII drugs, a different part of a
        # different tariff, and the panel carries none rather than reaching for the
        # nearest one.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. This speciality has no NHS "
            "Supply Chain framework of its own. The whole contract launch brief index "
            "was read on 09/09/2026 — 140 unique briefs — and not one names cranial "
            "implants, cerebrospinal fluid shunts or valves, dural substitutes, "
            "aneurysm clips, cranial fixation or hydrocephalus. Those products are "
            "bought at trust or unit level and no framework record can show them. What "
            "is counted below is the two of the five agreements the page names whose "
            "supplier lists are genuinely this patch's. Three are not counted: Robotic "
            "Medical Equipment, whose Lot 2 Spinal and Neurological Robots holds "
            "Medtronic Limited alone, and Total Orthopaedic Solutions 3, which carries "
            "spinal implants among 101 largely orthopaedic suppliers, are both counted "
            "on the pages whose frameworks they are; and Operating (Theatre and "
            "Outpatient) Microscopes, whose Lot 1 carries Neurological Operating, sits "
            "in the framework dataset's unparsed list because its brief states 10 "
            "suppliers and 8 incumbents and then names 9 and 7. Being named on a "
            "framework is not evidence of volume, and being absent from one is not "
            "evidence of absence from this market. The page's Buying route section "
            "sets out all five agreements with their expiry dates, and the date that "
            "matters most — 11 November 2026, the planned publication of the "
            "neuromodulation successor tender — is there rather than here."
        ),
    },
}


# A speciality whose patch carries no NHS Supply Chain framework at all sets
# "frameworks": None. That is a finding, not a gap, and it is different from a
# pattern that happens to match nothing today: obesity and weight management is
# bought through an FP10 or a hospital specialist service, so there is no
# framework for a pattern to find and none will appear. NEVER_MATCHES is a regex
# that cannot match any string, so build_frameworks returns an empty list without
# the rule having to pretend to a keyword it does not have.
NEVER_MATCHES = re.compile(r"(?!x)x")


def compile_rule(rule):
    return {
        "fw": NEVER_MATCHES if rule["frameworks"] is None
              else re.compile(rule["frameworks"], re.I),
        "inc": re.compile(rule["include"], re.I),
        "exc": re.compile(rule["exclude"], re.I),
    }


def match_title(rx, title):
    t = title or ""
    return bool(rx["inc"].search(t)) and not rx["exc"].search(t)


def build_frameworks(rx, fw_doc):
    """The speciality's NHSSC frameworks, with the supplier list each one carries."""
    out = []
    for f in fw_doc["frameworks"]:
        if not rx["fw"].search(f.get("name") or ""):
            continue
        out.append({
            "name": f.get("name"),
            "url": f.get("url"),
            "reference": f.get("reference"),
            "category": f.get("category"),
            "supplyRoute": f.get("supplyRoute"),
            "starts": f.get("starts"),
            "ends": f.get("ends"),
            "supplierCount": f.get("supplierCount"),
            "supplierSource": f.get("supplierSource"),
            "suppliers": [s for s in (f.get("suppliers") or []) if isinstance(s, str)],
            "delisted": f.get("delisted"),
        })
    out.sort(key=lambda x: (x.get("name") or ""))
    return out


def build_suppliers(frameworks, registry):
    """Every named supplier on the speciality's own frameworks, and which ones.

    This is the speciality's supplier list as the procurement record states it:
    not a redirect to the whole directory, and not a keyword guess against the
    free-text speciality strings, which were never one vocabulary.

    Names are resolved through company-aliases first. A name the registry cannot
    resolve is kept exactly as NHS Supply Chain wrote it and flagged, never dropped
    and never quietly merged into something that looks close.
    """
    by_key = {}
    for f in frameworks:
        for s in f["suppliers"]:
            status, canonical, _how = company_alias.resolve(s, registry)
            resolved = status == "RESOLVED"
            key = canonical if resolved else s
            rec = by_key.setdefault(key, {
                "name": key, "resolved": resolved, "variants": [], "frameworks": [],
            })
            if s not in rec["variants"]:
                rec["variants"].append(s)
            if f["name"] not in rec["frameworks"]:
                rec["frameworks"].append(f["name"])
    for rec in by_key.values():
        rec["variants"].sort()
        # Only worth showing when NHSSC really did write it two ways.
        if rec["variants"] == [rec["name"]]:
            rec["variants"] = []
    out = list(by_key.values())
    # Most frameworks first: a supplier on three of the speciality's frameworks is
    # a bigger name on this patch than one on a single lot, and that ordering is
    # the only claim being made — it is a count, not a ranking of importance.
    out.sort(key=lambda x: (-len(x["frameworks"]), x["name"].lower()))
    return out


def build_awards(rx, rule, th_doc, fa_doc):
    """Awarded contracts on this patch, from the two award feeds."""
    rows = []
    schema = th_doc["schema"]
    ix = {k: i for i, k in enumerate(schema)}
    for r in th_doc["rows"]:
        title = r[ix["t"]]
        if not match_title(rx, title):
            continue
        rows.append({
            "title": title,
            "buyer": r[ix["b"]],
            "supplier": r[ix["sup"]],
            "date": r[ix["d"]],
            "url": r[ix["u"]],
            "value": r[ix["v"]],
            "periodEnd": r[ix["pe"]],
            "source": "tender-history",
        })
    # CPV CORROBORATES, IT NEVER ADMITS. A CPV code on a notice carrying a basket of
    # them says what family the buyer filed it under, not what is being bought:
    # "Newborn Transport Harnesses for London Ambulance" carries 33141116, the dressing
    # packs code, alongside three others. Accepting on CPV alone put that on the wound
    # care page. The title has to match; the CPV is recorded so a reader can see the
    # classification agreed.
    cpv_prefixes = tuple(rule.get("cpv") or ())
    for a in fa_doc["awards"]:
        cpvs = [str(c) for c in (a.get("cpv") or [])]
        if not match_title(rx, a.get("title")):
            continue
        by_cpv = bool(cpv_prefixes) and any(c.startswith(cpv_prefixes) for c in cpvs)
        buyer = a.get("buyer")
        if isinstance(buyer, dict):
            buyer = buyer.get("name")
        rows.append({
            "title": a.get("title"),
            "buyer": buyer,
            "supplier": ", ".join(
                (s.get("name") if isinstance(s, dict) else str(s))
                for s in (a.get("suppliers") or [])
            ) or None,
            "date": a.get("published"),
            "url": a.get("url"),
            "value": None,
            "periodEnd": None,
            "cpv": cpvs,
            "isFramework": a.get("is_framework"),
            "source": "framework-awards",
            "cpvCorroborates": by_cpv,
        })
    # De-duplicate on the notice URL: the two feeds overlap at the recent end.
    seen, uniq = set(), []
    for r in sorted(rows, key=lambda x: (x.get("date") or ""), reverse=True):
        k = r.get("url") or (r.get("title"), r.get("date"))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq[:AWARD_CAP], len(uniq)


def build_open_tenders(rx, slug, ot_doc):
    """Notices still open for bidding. Usually empty for a given speciality, and an
    empty list is the correct answer — never padded out with near-misses."""
    out = []
    for n in ot_doc["notices"]:
        if n.get("speciality") == slug or match_title(rx, n.get("title")):
            out.append({
                "title": n.get("title"),
                "buyer": n.get("buyer"),
                "status": n.get("status"),
                "stage": n.get("stage"),
                "closingDate": n.get("closingDate"),
                "url": n.get("url"),
                "value": n.get("valueAmount"),
                "source": n.get("source"),
            })
    return out


def build_tariff(rule, dt_doc):
    """Drug Tariff Part IX for this speciality — the reimbursement list a prescribing
    conversation actually turns on. Summarised, never shipped whole: Part IXA alone is
    56,833 lines and no panel can carry that."""
    parts = tuple(rule.get("tariffParts") or ())
    if not parts:
        return None
    ix = {k: i for i, k in enumerate(dt_doc["schema"])}
    rows = [r for r in dt_doc["rows"] if r[ix["part"]] in parts]
    if not rows:
        return None
    by_sup = {}
    prices = []
    for r in rows:
        by_sup[r[ix["supplier"]]] = by_sup.get(r[ix["supplier"]], 0) + 1
        try:
            prices.append(float(r[ix["price"]]))
        except (TypeError, ValueError):
            pass
    top = sorted(by_sup.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    return {
        "parts": list(parts),
        "effectiveMonth": dt_doc.get("effectiveMonth"),
        "dataAsOf": dt_doc.get("dataAsOf"),
        "sourcePage": dt_doc.get("sourcePage"),
        "lineCount": len(rows),
        "supplierCount": len(by_sup),
        "topSuppliers": [{"name": n, "lines": c} for n, c in top],
        "priceMin": round(min(prices), 2) if prices else None,
        "priceMax": round(max(prices), 2) if prices else None,
    }


def build(slug, sources):
    rule = SPECIALITY_RULES.get(slug)
    generated = datetime.date.today().isoformat()
    if not rule:
        return {
            "_notice": sources["notice"],
            "slug": slug,
            "defined": False,
            "generated": generated,
            "whyEmpty": (
                "No speciality rule has been written for this page yet. The panel shows "
                "nothing rather than guessing: a keyword match on the title alone is "
                "wrong more often than it is right on this data."
            ),
        }

    rx = compile_rule(rule)
    fw_doc, th_doc = sources["frameworks"], sources["tender_history"]
    fa_doc, ot_doc, dt_doc = sources["framework_awards"], sources["open_tenders"], sources["drug_tariff"]

    frameworks = build_frameworks(rx, fw_doc)
    suppliers = build_suppliers(frameworks, sources["registry"])
    awards, award_total = build_awards(rx, rule, th_doc, fa_doc)
    open_tenders = build_open_tenders(rx, slug, ot_doc)
    tariff = build_tariff(rule, dt_doc)

    note = rule.get("coverageNote")
    qualify = (lambda text: (text + " " + note) if note else text)

    return {
        "_notice": sources["notice"],
        "slug": slug,
        "label": rule["label"],
        "defined": True,
        "generated": generated,
        "dataAsOf": {
            "frameworks": fw_doc.get("dataAsOf"),
            "tenderHistory": th_doc.get("dataAsOf"),
            "frameworkAwards": fa_doc.get("generated"),
            "openTenders": ot_doc.get("dataAsOf"),
            "drugTariff": dt_doc.get("dataAsOf"),
        },
        "rules": {
            "frameworks": qualify(
                ("NO NHS Supply Chain framework covers this speciality. That is a finding "
                 "about the patch, not a missing filter: every NHSSC framework name was "
                 "read and none of them is this speciality's. Suppliers on this page are "
                 "therefore empty for the same reason, because the supplier list is built "
                 "from the speciality's own frameworks and there are none to build it "
                 "from. Where a supplier here does appear on an NHSSC framework, it is "
                 "another speciality's framework and is counted on that page.")
                if rule["frameworks"] is None else
                ("NHS Supply Chain framework names matching /%s/i. NHSSC names a framework "
                 "after its clinical category, so the name is the key; the CBU category "
                 "field is far too broad to filter on." % rule["frameworks"])
            ),
            "suppliers": qualify(
                ("No supplier list is published for this speciality, because this patch has no "
                 "NHS Supply Chain framework for one to be drawn from. This panel names "
                 "suppliers only where the procurement record names them on this speciality's "
                 "own frameworks. It will not fall back to a keyword guess against the "
                 "supplier directory, which would return firms that sell to this patch and "
                 "firms that merely mention it in the same list.")
                if rule["frameworks"] is None else
                "Every supplier NHS Supply Chain names on the frameworks above, resolved to one "
                "name per company through the Hub's alias registry, and ordered by how many of "
                "this speciality's frameworks they appear on. That count is the only claim made. "
                "It is not a ranking of size or share. Where NHS Supply Chain spelled a company "
                "two ways across its own pages, both spellings are shown against the one entry."
            ),
            "awards": (
                "Award-stage notices whose TITLE matches /%s/i and does not match /%s/i. The "
                "exclusion list exists because every pattern in it matched a real notice that "
                "was not this speciality. %s Buyer names are never matched on." % (
                    rule["include"], rule["exclude"],
                    ("A CPV code beginning %s is recorded as corroboration where the feed "
                     "carries one, but never admits a notice on its own: a notice carrying a "
                     "basket of CPV codes is filed under all of them and bought under one."
                     % " or ".join(rule["cpv"])) if rule.get("cpv") else
                    ("No CPV family corroborates this speciality: not one matching notice in "
                     "this data carries a CPV code specific to it, so none is claimed. A CPV "
                     "code could never admit a notice on its own in any case, because a notice "
                     "carrying a basket of them is filed under all and bought under one."))
            ),
            "openTenders": (
                "Notices still open for bidding, matched the same way. An empty list means no "
                "open notice on this patch today, not that none was looked for."
            ),
            "drugTariff": (
                "NHSBSA Drug Tariff Part %s for the stated effective month, summarised. Prices "
                "are the reimbursement price at publication, not necessarily today's."
                % "/".join(rule["tariffParts"])
                if rule.get("tariffParts") else
                "No Drug Tariff part applies to this speciality. Part IX reimburses dressings "
                "and elastic hosiery (IXA), incontinence appliances (IXB), stoma appliances "
                "(IXC) and elastic hosiery (IXR); nothing on this patch is listed there, so "
                "the panel carries no tariff rather than reaching for the nearest part."
            ),
        },
        "counts": {
            "frameworks": len(frameworks),
            "suppliers": len(suppliers),
            "suppliersUnresolved": sum(1 for s in suppliers if not s["resolved"]),
            "awardsShown": len(awards),
            "awardsMatched": award_total,
            "openTenders": len(open_tenders),
        },
        "frameworks": frameworks,
        "suppliers": suppliers,
        "awards": awards,
        "openTenders": open_tenders,
        "drugTariff": tariff,
    }


def main():
    sources = {
        "frameworks": load("frameworks.json"),
        "tender_history": load("tender-history.json"),
        "framework_awards": load("framework-awards.json"),
        "open_tenders": load("open-tenders.json"),
        "drug_tariff": load("drug-tariff-part-ix.json"),
    }
    # The licence and database-right wording is the house notice, carried verbatim.
    # The `ref` is NOT: a marker ref identifies one file, and reusing another file's
    # would defeat the traceability it exists for. stamp_notice.py only walks
    # data/*.json, so nothing mints one for a file in a subdirectory yet. Say so in
    # the file rather than shipping a borrowed marker.
    notice = dict(sources["open_tenders"]["_notice"])
    notice.pop("ref", None)
    notice["markerRef"] = ("Not yet minted. This file sits in data/speciality-panels/ and "
                           "scripts/stamp_notice.py walks only data/*.json.")
    sources["notice"] = notice
    sources["registry"] = company_alias.load_registry()

    slugs = sys.argv[1:] or sorted(SPECIALITY_RULES)
    os.makedirs(OUT, exist_ok=True)
    for slug in slugs:
        doc = build(slug, sources)
        path = os.path.join(OUT, slug + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
        c = doc.get("counts") or {}
        print("%-38s frameworks=%s suppliers=%s awards=%s/%s open=%s tariff=%s  (%d KB)" % (
            slug, c.get("frameworks"), c.get("suppliers"), c.get("awardsShown"),
            c.get("awardsMatched"), c.get("openTenders"),
            (doc.get("drugTariff") or {}).get("lineCount") if doc.get("drugTariff") else "-",
            os.path.getsize(path) // 1024))


if __name__ == "__main__":
    main()
