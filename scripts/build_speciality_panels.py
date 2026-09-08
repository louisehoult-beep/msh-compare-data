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
        "exclude": (
            r"\b(lectures? theatre|road re-?surfac\w*|water treatment|"
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
}


def compile_rule(rule):
    return {
        "fw": re.compile(rule["frameworks"], re.I),
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
                "NHS Supply Chain framework names matching /%s/i. NHSSC names a framework "
                "after its clinical category, so the name is the key; the CBU category "
                "field is far too broad to filter on." % rule["frameworks"]
            ),
            "suppliers": qualify(
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
