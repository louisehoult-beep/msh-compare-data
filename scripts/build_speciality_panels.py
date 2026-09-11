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
#              None means the include list produced no false positive to exclude.
#              That is only ever written after every hit has been read one by one,
#              and it is a statement about the include list being narrow enough,
#              never a shortcut past the reading. See the renal rule, where the
#              loose terms were refused in the include instead of admitted and
#              then argued with here.
# cpv        : CPV code prefixes used for award feeds that carry classification.
# tariffParts: Drug Tariff Part IX parts that belong to this speciality.
#
# excludeFinding
#            : OPTIONAL. The default wording for a rule that HAS an exclusion list
#              states that every pattern in it matched a real notice that was not
#              this speciality. That is the standard and it is true of every rule
#              that does not set this key. Stroke is the one exception so far and
#              it is written out rather than glossed: no award title in this data
#              carries "stroke volume", so the pattern was derived from more than
#              forty real matches in the Hub's own supplier product data, where the
#              phrase is a cardiac output parameter or a bag valve mask spec. It is
#              still a match that was read and found wrong, which is the standard
#              that matters, but it is not an award row and the published text has
#              to say which it was.
# frameworksFinding
#            : OPTIONAL, and only ever set alongside "frameworks": None. The
#              default wording for a speciality with no framework says that every
#              NHSSC framework name was read and none of them is this
#              speciality's. For obesity and for paediatrics that is true. For
#              stroke it is not: the agreement that patch buys on exists, and the
#              reason it is not counted is that NHS Supply Chain's brief for it
#              publishes a supplier count and no names, so the Hub's framework
#              record holds it in `unparsed` and build_frameworks cannot read it.
#              Those are two different findings and a member is owed the right
#              one. This key replaces the opening statement of the frameworks and
#              suppliers rule text with the one that is true for the patch, rather
#              than leaving a false sentence standing and correcting it in the
#              coverage note underneath. A rule that does not set it gets the
#              default wording unchanged.
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
    # PAGE 2912. Vascular access DEVICES and the giving of intravenous therapy: the
    # cannula, the PICC, the central line, the connector, the pump and the set. It is
    # NOT the drug or the fluid that travels down them, and it is not arterial disease
    # — vascular-surgery-and-pad owns that, and owns the "Vascular Therapy" framework
    # name, which is a trap: NHS Supply Chain's "Vascular Therapy and Associated
    # Products" is mechanical VTE prophylaxis and compression, its supplier list being
    # Juzo, Sigvaris, Haddenham, Medi, Thuasne and Urgo. Nothing on it is vascular
    # access. The frameworks pattern below is written to name the six agreements that
    # are, not to match the word "vascular".
    "vascular-access-and-iv-therapy": {
        "label": "Vascular Access and IV Therapy",
        # Six NHSSC frameworks, five of them under Medical and Surgical Consumables.
        # Infusion Pumps and Administration Sets is deliberately SHARED with
        # palliative-and-end-of-life-care: one agreement really does carry both the
        # ward infusion pump and the syringe driver, exactly as Pressure Area Care is
        # shared between wound care and patient handling.
        # DELIBERATELY NOT CLAIMED, each checked and rejected:
        #   Vascular Therapy and Associated Products — compression, see above.
        #   Blood Collection Devices — venepuncture consumables, already claimed by
        #     pathology-and-laboratory-medicine and haematology-and-patient-blood-
        #     management. Sampling is diagnostics, not therapy; a third claim on it
        #     would inflate this page's supplier count with tube and vacutainer firms.
        #   Syringes, Needles and Associated Products — 52 suppliers, and the syringe
        #     is a general consumable used by every speciality that injects anything.
        #     A framework named after a product, not a clinical category, is the one
        #     case the framework-name rule does not hold, so it is left out.
        "frameworks": (
            r"\b(central venous catheter|intravenous (?:cannula|accessories)|"
            r"needlefree connection|infusion pumps and administration sets|"
            r"extension sets and lines)"
        ),
        # No trailing \b on the group: NHSSC and the notice feeds disagree on plurals
        # ("Central Venous Catheters and Associated Products" against "central venous
        # catheter"), and an end-anchored pattern silently drops the framework's own
        # award notice. That is how this rule failed its first draft.
        "include": (
            r"\b(vascular access|picc\b|peripherally inserted central|midline catheter|"
            r"central venous (?:catheter|access|line)|central line|"
            r"intravenous|iv\b|cannulae?\b|cannulation|"
            r"infusion pump|syringe driver|syringe pump|administration set|giving set|"
            r"needle[- ]?free|venepunctur|venipunctur|phlebotom|"
            r"port-?a-?cath|implantable port|totally implantable venous|tivad|"
            r"hickman|groshong|broviac|arterial line|arterial catheter|"
            r"extension set|catheter securement|opat\b|outpatient parenteral|"
            r"infusion therapy)"
        ),
        # Derived, not guessed: the include above was run over all 1,972 rows of
        # tender-history.json and all 1,397 of framework-awards.json and every hit
        # read. It returned 33 tender-history rows, of which 17 were wrong. They fall
        # into exactly two families and every pattern here comes from one of them.
        #
        # 1. THE ROUTE IS NOT THE PRODUCT. Fourteen of the seventeen are medicines and
        #    fluids that happen to be given intravenously — "Bevacizumab IV Infusion
        #    Vials", "Hepatitis B immunoglobulin intravenous use (IV)", "Glucose 10%
        #    and 50% 500ml iv infusion", "DPS for the Supply of Antibiotics and IV
        #    Fluids", "Intravenous Fluids and Peritoneal dialysis fluids". A rep on
        #    this page sells the line, not what goes down it. \w+mab was checked
        #    against the whole corpus before being used: it matches 41 titles and all
        #    41 are monoclonal antibodies, so it excludes nothing real. The dose-form
        #    signature (a number followed by mg/ml/mcg, "vial", "concentrate for",
        #    "powder for", "solution for infusion", "pre-filled") catches the rest
        #    generically rather than naming drugs one at a time; it fires on none of
        #    the 16 true positives, which carry no dose.
        # 2. THE WORD IS NOT THE ROUTE. "Nasal Cannula & Oxygen Masks" is respiratory,
        #    and "Insulin Infusion Pumps, Continuous Glucose Monitoring Systems" is
        #    diabetes — an insulin pump is subcutaneous and belongs to no lot on any
        #    framework above.
        #
        # KNOWN AND ACCEPTED COST: bare \bfluids?\b would also drop a genuine
        # "IV fluid administration set" notice if one is ever published. Dropping a
        # true positive is the safe direction and rule 14 prefers an honest empty
        # line to a wrong one; the seven fluid-supply contracts it removes today are
        # all pharmacy wholesale, none of them a device.
        "exclude": (
            r"\b(nasal cannula|\w+mab\b|fluids?\b|irrigation|insulin|glucose|"
            r"erythropoietin|immunoglobulin|antibiotics?\b|"
            r"\d+\s?m(?:g|l|cg)\b|vials?\b|concentrate for|powder for|"
            r"solution for (?:infusion|injection)|pre-?filled)"
        ),
        # Observed, not looked up. These are the prefixes actually carried by the
        # framework-awards rows this rule keeps: 33141220 on both IV cannula notices,
        # 331941x on the infusion pump and infusion device notices, 33141624 on the
        # administration set notice. CPV corroborates and never admits, so a code that
        # has never been seen on this patch is not listed on the strength of what the
        # CPV schedule says it means.
        "cpv": ("33141220", "331941", "33141624"),
        # NO tariffParts, and this was checked rather than assumed. Part IX was
        # searched for every term in the include list: the only hits are tracheostomy
        # inner cannulae (respiratory) under IXA and a needle-free INSULIN delivery
        # system (diabetes). Vascular access devices are hospital-supplied and are not
        # FP10 reimbursable, so no part of the Drug Tariff belongs to this page.
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
    # PAGE 2915. Scope, in the page's own words: "Diagnostic imaging departments, the
    # eleven-framework capital estate that serves them, and the reporting capacity that
    # is the real constraint." Diagnostic imaging, NOT interventional radiology: the
    # angio suite, embolics, ablation kit and percutaneous work are the Interventional
    # Radiology page's, and that page's rule says in terms that CT, MRI, ultrasound,
    # mammography, nuclear medicine, fluoroscopy and static and mobile X-ray are "the
    # Radiology and Imaging page's". This rule holds the other side of that line.
    "radiology-and-imaging": {
        "label": "Radiology and Imaging",
        # TWELVE frameworks, and they are exactly the twelve the page's own Buying route
        # section names, all read on NHS Supply Chain's contract launch briefs 08/09/2026:
        # the eleven modality briefs that share reference 2021/S 000-007768 and expire
        # together on 31 March 2028 with both 24-month extensions used, plus Digital
        # Diagnostic Solutions (2025/S 000-043444, expiring 31 July 2027), which is the
        # PACS, RIS, VNA, dose monitoring and diagnostic AI route. The pattern names each
        # brief rather than matching the shared reference, and that is deliberate: the
        # page says outright that "the reference identifies a category, not an agreement",
        # and a thirteenth brief carries the same reference — Bladder Scanners, which is
        # the continence and urology assessment device and is not in the page's eleven.
        # Matching on 2021/S 000-007768 would publish it here.
        #
        # The CBU `category` field is no use either: "Diagnostic Equipment and Services"
        # also holds Laboratory Diagnostics (122 suppliers), Cardiac and Pulmonary
        # Diagnostics, Audiological Diagnostics and the bladder scanners.
        #
        # NOT MATCHED, deliberately: Angiography, Hybrid Theatres, Capital Equipment
        # (2025/S 000-077456). It is a real imaging room, and both the interventional
        # radiology and the vascular surgery pages claim it, correctly. This page's own
        # Buying route section does not: it names twelve briefs and that is not one of
        # them. The page is the authority on its own scope, so the angio suite stays with
        # the two pages that work in it.
        "frameworks": (
            r"\b(ct scanners|magnetic resonance imaging scanners|static x-ray|mobile x-ray|"
            r"mammography imaging|nuclear medicine imaging|bone densitometers|"
            r"ultrasound scanners|fluoroscopy|mobile image intensifiers|contrast injectors|"
            r"digital diagnostic solutions)\b"
        ),
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,342 of framework-awards.json — 3,314 titles — and
        # all 152 hits of the first draft were read one by one, with their buyers, before
        # this list was fixed. 104 rows survive.
        #
        # THE RULE THIS PANEL MATCHES ON IS PRODUCT CLASS, NOT BUYER. A clinical imaging
        # modality is on this panel whoever bought it, so a university's 3 Tesla MRI, a
        # research council's DEXA and a Queen's University Belfast ultrasound system are
        # all here: they are the same machines, sold by the same firms, that a trust buys.
        # An instrument that is NOT a clinical imaging modality is not here whoever bought
        # it, which is what most of the exclusion list below removes. Stating the rule
        # this way round is the only way it can be applied consistently, because the
        # builder matches titles and never buyer names.
        #
        # NOT INCLUDED, deliberately, and every one was tried and read:
        #   bare "imaging"   -> 34 rows and fewer than half are this patch. The others are
        #                       an endoscopic imaging system, an ophthalmic imaging
        #                       machine, a small-animal retinal imaging system, a cell
        #                       imaging plate reader, a time-lapse incubation imaging
        #                       system, a hyperspectral imaging rig, an in vivo imaging
        #                       system, a night vision imaging system for aircrew, and the
        #                       ONYX software platform the interventional radiology rule
        #                       also refused. The qualified forms — diagnostic imaging,
        #                       medical imaging, multi-modality imaging — are used instead.
        #   "multimodal
        #    imaging"        -> its only hit is the University of Edinburgh's Multimodal
        #                       Imaging Platform, a research platform. "Multi Modality
        #                       Imaging" is kept because its only hit is NHS Scotland's
        #                       NP167/22 equipment framework, which is this patch.
        #   "image transfer" -> two hits and one is "Supply of dermatoscopes & image
        #                       transfer system", dermatology teledermatoscopy. Genomics
        #                       England's "Multi Modal Radiology image transfer" reaches
        #                       the panel on "radiology" instead, without the term.
        #   bare "scanner"   -> bladder scanners, digital pathology slide scanners, a
        #                       fibroscanner, an automated ultrasonic vessel inspection
        #                       scanner and three airport baggage scanners. The modality
        #                       terms reach every real one.
        #   bare "screening" -> 19 rows and one is imaging. The other eighteen are bowel,
        #                       newborn, genetic, STI, cystic fibrosis, SCID and diabetic
        #                       eye screening. "breast screening" is used instead, which
        #                       is mammography and can be nothing else.
        #   "radiopharma-
        #    ceutical"       -> ten rows, and the title never says whether the product is
        #                       a diagnostic imaging tracer or therapeutic molecular
        #                       radiotherapy, which is a different patch bought on a
        #                       different route. Radiopharmaceuticals are also bought
        #                       through radiopharmacy, not through any of the twelve
        #                       frameworks above. Refused rather than widened (rule 14).
        #                       The two rows that genuinely are imaging reach the panel by
        #                       their own names — "Nuclear Medicine" and "Diagnostic
        #                       Imaging Agent Kit".
        #   "echo",
        #   "echocardiograph"-> four rows, and the page's own DM01 rule excludes
        #                       echocardiography in terms: "Echocardiography is excluded
        #                       because it is a cardiology test". It is the Cardiology and
        #                       Cardiac Surgery page's. Note the consequence, stated so it
        #                       can be judged: "Purchase of a Vivid E95 Ultrasound Machine"
        #                       IS on this panel, because its title says ultrasound
        #                       machine, even though a Vivid E95 is a cardiac system. The
        #                       title is what the rule can see.
        #   "\bvna\b"        -> matches nothing here and could mean anything in a future
        #                       refresh. "vendor neutral archive" is used instead.
        #
        # TERMS THAT FIND NOTHING TODAY AND ARE KEPT ANYWAY: tomosynthesis, image
        # intensifier, vendor neutral archive, picture archiving, positron emission, bone
        # densitometer, densitometry, lead apron. None of them can mean anything but this
        # speciality, so they cost nothing and will catch the next refresh. Not one row on
        # the panel today reaches it through them, and that is stated rather than left to
        # look like coverage.
        "include": (
            r"\b(radiolog\w*|radiograph\w*|radiograhic|teleradiolog\w*|"
            r"diagnostic imaging|medical imaging|multi[- ]?modality imaging|"
            r"quality standard for imaging|"
            r"x[- ]?rays?|\bmris?\b|magnetic resonance|\bct\b|computed tomograph\w*|"
            r"ultrasounds?|mammograph\w*|tomosynthesis|breast screening|"
            r"nuclear medicine|\bspect\b|positron emission|pet[/ -]?ct|pet dose|"
            r"gamma cameras?|fluoroscop\w*|image intensifiers?|c[- ]?arms?|"
            r"bone densitometer\w*|densitometr\w*|absorptiometry|\bdexa\b|"
            r"\bpacs\b|picture archiv\w*|vendor neutral archive|"
            r"contrast media|contrast injectors?|barium|"
            r"radiation protect\w*|radiation gloves?|lead aprons?)\b"
        ),
        # Every pattern below matched a real row, was read with its buyer, and was
        # rejected. Grouped by why.
        #
        # ANOTHER PAGE'S GROUND, not a mistake in the feed:
        #   interventional   -> eight rows, all the Interventional Radiology page's: two
        #                       "Interventional Radiology Products", NP68424, the mobile
        #                       IR tables framework, the Scottish INR and thrombectomy
        #                       consumables, CLI-OJEU-46286 and NHS Supply Chain's own
        #                       IC/IR/INR agreement.
        #   percutaneous     -> Sheffield's "CT guidance technology for percutaneous
        #                       instrument insertion and ablation volume validation".
        #                       The IR rule claims it by name and it is IR's.
        #   ablation         -> "Purchase of MRI-Guided Laser Ablation System", KCH
        #                       Interventional Facilities Management. Ablation is a
        #                       therapeutic act, not an imaging modality, whatever guides
        #                       it. No row kept here carries the word.
        #   neuro vascular   -> "HEY/17/266 NEURO VASCULAR RADIOLOGY CONSUMABLES", Hull.
        #                       Interventional neuroradiology, which the IR page admits
        #                       and this one does not. Excluded as "neuro vascular", not
        #                       "neuroradiology", for the same reason the vascular rule
        #                       gives.
        #   pacing           -> "Radiology, Cardiology and Pacing Packs", NHS Grampian.
        #                       Cath lab and IR procedure packs. A diagnostic imaging
        #                       department does not buy pacing packs.
        #   intravascular    -> "Purchase of 3 x Intravascular Ultrasounds", King's. IVUS
        #                       is an interventional cardiology catheter.
        #   dental,
        #   oral x-ray,
        #   panoramic        -> four rows: a dental X-ray system, a panoramic X-ray
        #                       system, equipment to digitise dental X-ray, and the
        #                       maintenance of Planmeca oral xray equipment. Dental
        #                       radiography is its own patch, its own kit and its own
        #                       buyer inside a trust.
        #   ultrasound gel   -> two rows, both bought on NHS Supply Chain's Electrodes,
        #                       Ultrasound Gels, Defibrillation and Related Consumables
        #                       framework, which is none of the twelve above and is shared
        #                       with resuscitation and cardiac physiology.
        #   hifu, high-
        #   intensity focused-> three rows. HIFU is a therapeutic ultrasound modality
        #                       (prostate and uterine), not a diagnostic one.
        #
        # NOT A CLINICAL IMAGING MODALITY AT ALL, whoever bought it:
        #   diffractomet*    -> five X-ray diffractometers: two School of Chemistry
        #                       purchases at St Andrews, Cardiff, Glasgow and Diamond
        #                       Light Source. Crystallography.
        #   spectroscop*     -> "X-ray Absorption/Emission Spectroscopy", Warwick.
        #   metrology        -> "Nikon Metrology XT H 225 X-ray CT system", Birmingham.
        #                       Industrial computed tomography for dimensional metrology.
        #   microscope       -> "MRC LMB High Resolution 3D X-ray Tomography Microscope".
        #   mid-kV           -> "A mid-kV X-ray Computed Tomography System for CiMAT",
        #                       Warwick. Mid-kV is a materials-testing tube specification;
        #                       no clinical scanner notice carries it.
        #   irradiator       -> "Provision of X-Ray Irradiators", Public Health England.
        #                       Blood and laboratory irradiation, not imaging.
        #   museum           -> "National Museums Scotland - X Ray Unit". Heritage.
        #   seed viability   -> "RBGKEW1500 - Seed viability X-ray cabinet", Kew. The same
        #                       row the wound care rule had to exclude on "viability".
        #   preclinical,
        #   in vivo, micro-CT,
        #   micro-PET, micro-
        #   ultrasound       -> seven research instruments: a nanoScan preclinical PET/CT,
        #                       a preclinical ultrasound imaging system, an in vivo
        #                       high-frequency micro-ultrasound array, MicroPET-MRI, and
        #                       two Micro CT Scanners. Small-animal imaging is a different
        #                       machine sold by different firms.
        #   equine,
        #   veterinary       -> "Standing Modular Equine MRI", Glasgow.
        #   functional
        #   ultrasound       -> "Functional Ultrasound Scanner", Edinburgh. fUS is a
        #                       neuroscience research technique, not a clinical modality.
        #   scanner design   -> "Motorized Patient Couch and Plastic Composite Outer
        #                       Covers for a new MRI Scanner Design", Aberdeen. Components
        #                       supplied INTO a scanner being designed, not a scanner
        #                       bought.
        #   simulator        -> "Point of Care Ultrasound (PoCUS) female patient simulator
        #                       upgrades", NHS Golden Jubilee, twice. A training manikin.
        #   non-imaging      -> "Standalone Non-Imaging Vibration-Controlled Ultrasound
        #                       System", twice. FibroScan liver elastography, and the
        #                       title says non-imaging itself.
        #   invicro          -> "Use of PET and MRI imaging facilities, plus [11C]
        #                       radiopharmaceuticals at Invicro LLC", Exeter. Buying
        #                       research scan time at a contract research organisation is
        #                       neither equipment nor NHS clinical capacity. Excluded on
        #                       the CRO's name rather than on "imaging facilities", which
        #                       would silently drop a genuine NHS managed-facility notice
        #                       in a future refresh.
        #   mri planet       -> "Annual MRI Planet Cloud Fee ... Invoice MRIUK1061277",
        #                       Humber Teaching NHS Foundation Trust. MRI Software Ltd is
        #                       a property-management software vendor whose initials
        #                       collide with magnetic resonance imaging. Planet is its
        #                       housing product. This is the single reason \bmri\b needs
        #                       a guard at all.
        #
        # ONE EXCLUSION THAT IS A CONTRACTING PHRASE, NOT A PRODUCT CLASS, SAID PLAINLY:
        #   in-service
        #   support          -> three Ministry of Defence platform-support notices, and
        #                       nothing else in 3,314 titles carries the phrase. Two are
        #                       demonstrably not clinical: "In-Service Support of X-Ray
        #                       Generators, Real Time Systems and Film Processors", which
        #                       is non-destructive-testing radiography, and "Procurement
        #                       and In Service Support lightweight x-ray capability",
        #                       bought by the Specialist EOD&S, Exploitation and
        #                       Countermeasures Team, which is explosive ordnance
        #                       screening. The third, a portable digital X-ray system,
        #                       could be a deployable clinical unit and cannot be told
        #                       from its title. Dropping one possible true positive is the
        #                       right side to err on (rule 14), and it is recorded here
        #                       rather than hidden.
        "exclude": (
            r"\b(interventional|percutaneous|ablation|neuro[- ]?vascular|pacing|"
            r"intravascular|dental|oral x[- ]?rays?|panoramic|ultrasound gels?|"
            r"hifu|high[- ]intensity focused|"
            r"diffractomet\w*|spectroscop\w*|metrology|microscope|mid[- ]?kv|"
            r"irradiator\w*|museum\w*|seed viability|"
            r"preclinical|pre[- ]clinical|in[- ]vivo|micro[- ]?ct|micro[- ]?pet|"
            r"micro[- ]?ultrasound|equine|veterinar\w*|functional ultrasound|"
            r"scanner design|simulators?|non[- ]?imaging|invicro|mri planet|"
            r"in[- ]service support)\b"
        ),
        # THREE CPV FAMILIES, all of which fire on rows this rule already admits:
        # 3311 is the imaging-equipment family (33110000 imaging equipment, 33111000
        # X-ray devices, 33113000 magnetic resonance imaging equipment all appear here);
        # 85150 is medical imaging SERVICES, which is the insourcing, outsourcing and
        # reporting half of this patch and carries six of the rows below; 33696800 is
        # X-ray contrast media, shared with interventional radiology because contrast
        # injectors is genuinely both patches' framework.
        #
        # Corroboration only, and this speciality is the clearest illustration in the
        # whole file of why a CPV code may never admit a notice on its own: 85150000,
        # "medical imaging services", is also carried by an echocardiogram service at
        # Wisbech and Ely, a colon capsule endoscopy contract and an insourced breast
        # SURGERY list, and 33112300 sits on three airport baggage scanners. The title
        # still has to match.
        "cpv": ("3311", "85150", "33696800"),
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence appliances (IXB), stoma appliances (IXC) and elastic hosiery
        # (IXR), all community prescription routes. Nothing an imaging department buys —
        # scanners, X-ray rooms, contrast media, PACS, radiation protection or reporting
        # capacity — is listed there, and the page claims no tariff presence. The panel
        # carries none rather than reaching for the nearest part.
        "coverageNote": (
            "COVERAGE, STATED RATHER THAN ASSUMED. Unlike the interventional radiology "
            "and vascular surgery patches, every NHS Supply Chain framework this "
            "speciality buys on parsed cleanly, so the twelve below really are the whole "
            "national route: the eleven modality briefs that share reference 2021/S "
            "000-007768 and expire together on 31 March 2028 with both 24-month "
            "extensions already used, and Digital Diagnostic Solutions (2025/S "
            "000-043444, expiring 31 July 2027) for PACS, RIS, VNA, dose monitoring and "
            "diagnostic AI. Two limits are worth knowing. First, that shared reference "
            "identifies a category and not an agreement: a thirteenth brief carries it, "
            "Bladder Scanners, which is the continence and urology assessment device and "
            "is not counted here. Second, the devolved nations and the regional "
            "collaboratives buy on their own routes, which have no NHS Supply Chain "
            "framework page and so contribute no suppliers below — NHS Scotland's "
            "NP167/22 multi-modality imaging equipment framework and NHS Wales Shared "
            "Services' contrast and imaging awards both appear in the award trail and in "
            "neither the framework list nor the supplier count. Being named on a "
            "framework is not evidence of volume, and being absent from one is not "
            "evidence of absence from this market."
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
        #     because this page's own calendar places it on this patch, AND ALSO ON THE
        #     MATERNITY AND NEONATAL PAGE, which names it as one of the four NHS Supply
        #     Chain agreements on its patch. Shared deliberately, in the way Pressure
        #     Area Care is shared between wound care and patient handling: one framework
        #     really does carry both the condition-specific formula a dietitian
        #     prescribes and the expression hardware a neonatal unit buys. Corrected
        #     09/09/2026 — this note previously said the maternity page claimed a
        #     different route and did not claim this one, which its own Buying route
        #     section contradicts. See the note on breast pumps in the include list.
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
    # PAGE 2746. Hyperacute stroke and mechanical thrombectomy. The page's own
    # subtitle states the structural finding this rule has to encode: "There is no
    # stroke framework: the devices sit on Lot 2, Interventional Neuroradiology, of
    # the interventional cardiology agreement, and that agreement expires on 26
    # February 2027."
    "stroke": {
        "label": "Stroke",
        # NO FRAMEWORK IS COUNTED, and the reason is different from obesity's and
        # paediatrics'. Those two patches have no NHSSC framework at all. This one
        # has exactly one and the Hub cannot read it.
        #
        # NHS Supply Chain 2021/S 000-017565, Interventional Cardiology,
        # Interventional Radiology and Interventional Neuroradiology, Cardiac Rhythm
        # Management and Electrophysiology, carries Lot 2 Interventional
        # Neuroradiology, which is where mechanical thrombectomy and the neurovascular
        # access range are bought. Its brief was read on 10/09/2026: category Medical
        # Technology, supply route eDirect, five lots, 27 February 2023 to 26 February
        # 2027, a 48 month term with its 24 month extension already inside it. It is
        # in frameworks.json but in the `unparsed` list, with the recorded reason "the
        # page states its supplier count but publishes no list of names".
        # build_frameworks reads only the parsed list, so it cannot be counted here.
        # That is stated in the finding below rather than dressed up as an absence.
        #
        # TWO PARSED FRAMEWORKS WERE REFUSED, and each was read on its own brief:
        #   Neuromodulation Devices and Associated Products (2023/S 000-034841, to 18
        #     March 2028) is where vagus nerve stimulation for post stroke
        #     rehabilitation sits, and the page names it for that. Its three lots are
        #     Deep Brain Stimulation, Spinal Cord Stimulation and Other
        #     Neuromodulation, and its 23 suppliers are a neuromodulation field.
        #     Claiming it would put all 23 under a stroke Suppliers heading on the
        #     strength of one category whose own evidence the page reports as Cochrane
        #     "very uncertain". It is counted on the neurology and neurosurgery page.
        #   Digital Diagnostic Solutions (2025/S 000-043444, to 31 July 2027) is the
        #     route the page names for advanced stroke imaging software. Its 54
        #     suppliers are a general digital diagnostics field, and HTG708 names only
        #     three products usable in the NHS. Claiming the agreement would present
        #     fifty one firms with no stroke imaging proposition as this patch's
        #     market.
        # Both refusals are the paediatrics ground: a lot or a line inside a broader
        # agreement does not make the agreement's supplier list this speciality's.
        "frameworks": None,
        "frameworksFinding": {
            "frameworks": (
                "NO NHS SUPPLY CHAIN FRAMEWORK IS COUNTED HERE, AND THE REASON IS NOT THAT "
                "NONE EXISTS. This patch buys on Lot 2, Interventional Neuroradiology, of "
                "2021/S 000-017565. That agreement is in the Hub's framework record but in "
                "its unparsed list, because NHS Supply Chain's brief for it states a "
                "supplier count and publishes no list of names, so it cannot be captured "
                "from that source. A framework this panel cannot evidence is not counted, "
                "and the Suppliers tab is empty for the same reason rather than a "
                "different one."
            ),
            "suppliers": (
                "No supplier list is published for this speciality. This panel names "
                "suppliers only where a framework record names them, and the one agreement "
                "this patch buys on publishes no supplier names on its brief. It will not "
                "fall back to a keyword guess against the supplier directory, and it will "
                "not carry a hand keyed list either, because both would give a member a "
                "supplier table without the alias resolution and the provenance every "
                "other supplier list on the Hub carries."
            ),
        },
        # DERIVED, not guessed. A deliberately over wide draft was run over all 1,972
        # rows of tender-history.json, all 1,397 of framework-awards.json and the 6
        # open notices, 3,375 titles in all, on 10/09/2026, and every hit was read one
        # by one. The draft carried "clot", "retriev", "cerebr", "carotid", "ischaem",
        # "TIA", "hyperacute", "dysphagia", "swallow", "CYP2C19", "genotyp",
        # "haemorrhag", "aspiration", "perfusion", "SSNAP" and "CVA" alongside the
        # three terms kept. Eight titles survive and all eight are this speciality.
        #
        # NOT INCLUDED, deliberately, and each was tried and read. As with neurology,
        # the wrong ones are cut at the include stage rather than swept back out at
        # the exclude stage:
        #   bare "clot"        -> its only hit is "Patient Dry Wiping Cloths", because
        #     "cloth" contains the letters. "clot retriever" and "thrombus" match
        #     nothing at all in this data.
        #   bare "retriev"     -> NHS Blood and Transplant's organ "Retrieval Packs"
        #     and Guy's and St Thomas' "South Thames Retrieval Service (STRS) Patient
        #     Transport Services", a paediatric transport contract. Neither is a stent
        #     retriever.
        #   "perfusion"        -> nine rows and every one is cardiac bypass or organ
        #     perfusion: a LivaNova Essenz heart lung system, NHS Golden Jubilee
        #     cardiac perfusion consumables, LifePort kidney perfusion consumables
        #     twice, cold static perfusion fluid twice. CT perfusion is the imaging
        #     this patch turns on under NOSIP and HTG708, and not one notice in this
        #     data carries it, so the term buys nothing and costs nine false positives.
        #   "genotyp" / "CYP2C19" -> HTG724 puts point of care CYP2C19 testing on this
        #     pathway, but "CYP2C19" matches no title in this data and "genotyp"
        #     matches only NHS Blood and Transplant's red cell immunohaematology
        #     genotyping consumables and microarray kits, which are pathology's.
        #   bare "cerebr", "carotid", "ischaem", "thrombolys", "alteplase",
        #   "tenecteplase", "embolect", "neurovascul", "microcatheter", "occlusion",
        #   "endarterect", "hyperacute", "dysphagia", "swallow", "haemorrhag",
        #   "aspiration", "reperfusion", "SSNAP", "NIHSS", "modified Rankin",
        #   "RapidAI", "e-Stroke", "DTAC" -> every one of them matches nothing at all
        #   in this data. They are left out rather than carried as decoration: a
        #   pattern that has never been tested against a hit is a pattern nobody has
        #   read. Carotid intervention is refused on a second ground as well, because
        #   the page routes it to vascular surgery's own frameworks rather than Lot 2.
        #   bare "neurolog\w*" -> six rows, and they are the neurology and
        #     neurosurgery page's: "WPL07040 - Neurology Insourcing" (University
        #     Hospital Southampton) is an outpatient capacity contract and
        #     "Neurological Rehabilitation Service" (NHS Greater Manchester ICB) is a
        #     commissioned rehabilitation service. Stroke reaches its own ground on
        #     "stroke" and on the interventional neuroradiology term instead.
        #
        # THE FOUR SERVICE CONTRACTS ARE KEPT ON PURPOSE. "Provision of Transport for
        # Stroke and Suspected Stroke Patients" (Somerset), "Early Stroke Discharge
        # Service" (Essex Partnership University), "Community Stroke Service for
        # Newham" and "City & Hackney Post Stroke Community Service" (both NHS North
        # East London ICB) are commissioned services, not product purchases. They stay
        # because they are named for this speciality, belong to no other page, and are
        # the contracts SSNAP's own recommendations 1, 3, 4 and 5 are addressed to:
        # onset to hospital time, hyperacute inpatient care, seven day rehabilitation
        # including integrated community stroke services, and the six month review.
        # This follows the palliative and end of life care panel, which carries a
        # rapid response service, an out of hours service and a medicines transport
        # service on the same ground. It is the opposite of the neurology rule's
        # refusal of "Neurological Rehabilitation Service", and deliberately so: that
        # contract belongs to the rehabilitation page, and these belong to no page but
        # this one.
        #
        # THE FRAMEWORK AWARD NOTICE IS KEPT, AND THIS DIVERGES FROM THE NEUROLOGY
        # RULE ON PURPOSE. "INTERVENTIONAL CARDIOLOGY, INTERVENTIONAL RADIOLOGY AND
        # INTERVENTIONAL NEURORADIOLOGY, CARDIAC RHYTHM MANAGEMENT AND ELECTROPHYSIOLOGY"
        # (NHS Supply Chain, 22/11/2022) is the award notice for 2021/S 000-017565.
        # The neurology rule excludes it because the neurology page's Buying route
        # names five agreements and not that one, so publishing it there would
        # contradict the page a reader is standing on. Here the page names it as the
        # buying route in its own subtitle, so refusing it would contradict this page
        # instead. The interventional radiology and vascular surgery panels carry the
        # same notice already; the overlap is deliberate, the way Pressure Area Care
        # is shared between wound care and patient handling.
        "include": (
            r"\b(strokes?|thrombectom\w*|neuro[- ]?radiolog\w*)\b"
        ),
        # ONE PATTERN, AND ITS EVIDENCE IS NAMED RATHER THAN IMPLIED. No award title
        # in this data carries "stroke volume", so this exclusion was not derived from
        # an award row the way every other rule's was. It is derived from a real match
        # in the Hub's own data all the same: "stroke volume" appears more than forty
        # times across supplier-product-detail.json, differentiator.json and
        # product-dossiers-respiratory.json, in every case as a cardiac output
        # parameter on a haemodynamic monitor (Deltex CardioQ-ODM, LiDCO, Cogent,
        # INVOS) or as a bag valve mask specification (Ambu Spur II). Those are
        # cardiology, critical care and resuscitation, not this patch.
        #
        # It is written here rather than left to a future refresh because "Stroke
        # Central Monitor" is one of the eight rows this rule genuinely carries. That
        # proves patient monitoring notices reach this panel, and a haemodynamic
        # monitor is the immediate neighbour of a stroke unit monitor in the same
        # product family. Without this pattern the first "Cardiac Output and Stroke
        # Volume Monitoring" notice to be published would appear on the stroke page as
        # this speciality's. That is a match that has been read in this data and found
        # to be wrong, which is the standard, and it is the only pattern here: nothing
        # is carried on a guess.
        "exclude": r"\bstroke volumes?\b",
        "excludeFinding": (
            "THE ONE EXCLUSION, AND WHERE ITS EVIDENCE CAME FROM. No award title in this "
            "data carries the phrase \"stroke volume\", so unlike every other speciality's "
            "exclusion list this pattern was not derived from an award row. It was derived "
            "from a real match all the same: \"stroke volume\" appears more than forty times "
            "across the Hub's own supplier product data, every time as a cardiac output "
            "parameter on a haemodynamic monitor or as a bag valve mask specification, which "
            "is cardiology, critical care and resuscitation rather than this patch. It is "
            "written now rather than after the event because \"Stroke Central Monitor\" is "
            "one of the notices this rule genuinely carries, so patient monitoring notices "
            "do reach this panel and a haemodynamic monitor is the nearest neighbour to a "
            "stroke unit monitor in the same product family."
        ),
        # NO CPV FAMILY, and that is checked rather than skipped. The four notices in
        # framework-awards.json that this rule matches carry 85143000 ambulance
        # services, 85121200 medical specialist services, 85323000 community health
        # services and 85100000 health services. Every one is generic and not one is
        # specific to stroke, so none is claimed. A CPV code could not admit a notice
        # on its own in any case.
        #
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence appliances (IXB), stoma appliances (IXC) and elastic hosiery
        # (IXR). Nothing this speciality buys is listed there. Its medicines half is
        # real and is the pathway's front door, but tenecteplase (TA990) and alteplase
        # (TA264) are hospital pharmacy and the trust formulary, which is Part VIII of
        # a different tariff and a different buyer. The panel carries none rather than
        # reaching for the nearest part.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. There is no stroke framework, and "
            "this page says so in its own subtitle. Mechanical thrombectomy and the "
            "neurovascular access range are bought on Lot 2, Interventional Neuroradiology, "
            "of NHS Supply Chain 2021/S 000-017565, Interventional Cardiology, "
            "Interventional Radiology and Interventional Neuroradiology, Cardiac Rhythm "
            "Management and Electrophysiology. Read on NHS Supply Chain's own contract "
            "launch brief on 10 September 2026: category Medical Technology, supply route "
            "eDirect, five lots, running 27 February 2023 to 26 February 2027, a 48 month "
            "term with its 24 month extension already inside it, so it cannot roll. THE LOT "
            "2 FIELD IS KNOWN, IT IS SIMPLY NOT IN THE FRAMEWORK RECORD. The brief's own "
            "Product Matrix, an Excel file dated 12 February 2026, was downloaded and "
            "parsed independently on 10 September 2026 and gives what the brief withholds: "
            "67 suppliers across the five lots, 52 on Lot 1, 16 on Lot 2, 13 on Lot 3, 15 "
            "on Lot 4 and 7 on Lot 5. Sixteen firms hold Lot 2 and seven of them hold Lot 2 "
            "and no other lot, which is the pure play neurovascular field: Acandis GMBH, "
            "Kaneka Pharma Europe NV, Microvention UK Limited, Phenox UK Limited, Rapid "
            "Medical Sub. UK Limited, Sela Medical UK Limited and Stryker UK Limited, in "
            "the matrix's own spelling. The Suppliers tab above is empty all the same, "
            "because it is built only from framework records that publish supplier names "
            "and this one does not. This page's own Product ranges and Buying route "
            "sections carry the Lot 2 position in full, and the date that matters most, 26 "
            "February 2027, is there rather than here. TWO PARSED FRAMEWORKS WERE REFUSED, "
            "and each was read. Neuromodulation Devices and Associated Products (2023/S "
            "000-034841, to 18 March 2028) is where vagus nerve stimulation for post stroke "
            "rehabilitation sits, but its three lots are Deep Brain Stimulation, Spinal "
            "Cord Stimulation and Other Neuromodulation and its 23 suppliers are a "
            "neuromodulation field; it is counted on the neurology and neurosurgery page. "
            "Digital Diagnostic Solutions (2025/S 000-043444, to 31 July 2027) is the route "
            "named here for advanced stroke imaging software, but its 54 suppliers are a "
            "general digital diagnostics field and NICE HTG708 names only three products "
            "usable in the NHS. A lot or a line inside a broader agreement does not make "
            "that agreement's supplier list this speciality's. Being named on a framework "
            "is not evidence of volume, and being absent from one is not evidence of "
            "absence from this market."
        ),
    },
    "pathology-and-laboratory-medicine": {
        "label": "Pathology and Laboratory Medicine",
        # TWO frameworks, named rather than pattern-guessed, and the first one is what
        # this whole patch runs on. NHS Supply Chain's "Laboratory Diagnostics, Point of
        # Care Testing and Pathology Managed Services" (2023/S 000-028831, 12 March 2024
        # to 11 March 2028, 48 months with no extension language in the term sentence)
        # carries 122 suppliers across seven live lots, and its Lot 7 Outsourcing was
        # never awarded: NHS Supply Chain states it "has not been awarded and will be
        # going back out to tender", with no date published. Page 2827 leads on exactly
        # that. "Blood Collection Devices" (2024/S 000-033791, 13 October 2025 to
        # 12 October 2027, 19 suppliers) is the pre-analytical half of the same market:
        # Greiner Bio-One, Sarstedt, BD, Radiometer and Siemens Healthcare Diagnostics
        # sell the tube the sample arrives in, and the tube decides the assay.
        #
        # THREE FURTHER FRAMEWORKS WERE READ AND REFUSED, each named rather than quietly
        # dropped, because all three carry the word "diagnostics" and would look like
        # obvious inclusions to the next person editing this rule:
        #   Digital Diagnostic Solutions (2025/S 000-043444, 54 suppliers) genuinely
        #     carries a laboratory strand — Clinisys, CGM Lab, Magentus, Soliton IT and
        #     InterSystems are laboratory information systems, Leica Microsystems and
        #     Epredia are digital pathology, Roche Diagnostics and Sysmex are analyser
        #     houses. It also carries roughly twenty radiology PACS and imaging-AI firms
        #     (Agfa, Sectra, Intelerad, Infinitt, Aidoc, Aidence, Radiobotics,
        #     Harrison-AI, Lucida, Hexarad, InferVision, Feedback), a cardiology cluster
        #     (Circle, HeartFlow, inHeart, Cardiac Services) and an endoscopy cluster
        #     (Endosoft, Karl Storz, KeyMed). The brief publishes NO supplier-by-lot
        #     split in this dataset, so the pathology strand cannot be separated from the
        #     rest. Claiming it whole would put twenty imaging vendors under a pathology
        #     Suppliers heading. It is primarily the radiology and imaging page's
        #     framework and is left to it.
        #   Specimen Cabinets and Associated Options and Related Services (5 suppliers)
        #     is NOT laboratory equipment despite its name. Its suppliers are Hologic,
        #     Cirdan Imaging, Medical Imaging Systems, BD and Synapse Medical, and its
        #     reference 2021/S 000-007768 is the shared imaging reference. A specimen
        #     cabinet here is an intra-operative specimen RADIOGRAPHY cabinet, an X-ray
        #     unit. The word "specimen" does not make a framework pathology.
        #   Cardiac and Pulmonary Diagnostics, Audiological Diagnostics and the sleep
        #     monitoring diagnostics framework are cardiology, audiology and respiratory
        #     respectively, and are named here only so nobody re-tests them.
        "frameworks": r"\b(laboratory diagnostics|blood collection devices)\b",
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,342 of framework-awards.json — 3,314 titles —
        # and every surviving hit was read one by one. The list returns 174 rows
        # (159 distinct title-and-buyer pairs) and all of them are this speciality.
        #
        # THE STRUCTURAL PROBLEM ON THIS PATCH, and why the obvious words are refused:
        # laboratory medicine shares its entire vocabulary with academic research,
        # veterinary science, forensic science, water hygiene and bioprocessing, all of
        # which buy the same instruments from the same companies. Four words that look
        # like the natural keys for this speciality are therefore NOT in the include
        # list, and each was tried first and its hits read:
        #   bare "laborator*"  -> 22 hits, of which about four are clinical. The word is
        #     owned by universities (Portsmouth, Swansea, APUC, SUPC, LSHTM), water
        #     utilities (Northumbrian Water, NI Water), a nuclear site (Sellafield),
        #     a city council and a dental laboratory. Only "laboratory medicine" and
        #     "laboratory diagnostics" are kept, because only those two are unambiguous;
        #     the genuine clinical rows the bare word would have caught are all reached
        #     through "reagents", "biochemistry" or "mycology" instead, so nothing is
        #     lost. "laboratory consumables" is deliberately NOT kept: it is the exact
        #     phrase the water utilities and universities use.
        #   bare "lab" / "labs" -> 11 hits, and the cath lab owns it. Six of them are
        #     cardiac catheterisation laboratories and one is a cath lab refurbishment.
        #   bare "microscop*"  -> 11 hits, of which eight are somebody else's: NHS Supply
        #     Chain's own Operating Microscopes framework, an ENT microscope and an
        #     ophthalmic microscope at East Suffolk and North Essex, Belfast's theatre
        #     microscope maintenance, an MRC X-ray tomography microscope and a Glasgow
        #     multi-spectral light sheet microscope. Refused rather than kept and then
        #     argued with in the exclusion list. Digital pathology microscopy is reached
        #     through "digital pathology" and "slide scanner" instead.
        #   bare "screening"   -> 19 hits, of which about eight are laboratory. The rest
        #     are child vision screening, diabetic eye screening twice, lung cancer
        #     screening, mobile breast screening trailers, an immigration TB screening
        #     service for the Home Office, a surveillance service and a Dundee research
        #     genotyping array. Only the named laboratory programmes are kept: newborn,
        #     bloodspot, genetic, bowel, cervical and bacterial screening. The one row
        #     this costs is Leeds Teaching Hospitals' "Purchase of Screening Kits", and
        #     checking its supplier proves the refusal right: it is Natus Nicolet, whose
        #     screening kits are newborn HEARING screening, not laboratory work at all.
        # Three more were refused for the same reason and are recorded so they are not
        # retried: bare "molecular" (its largest single hit is NHS England's national
        # framework for low molecular WEIGHT heparin, a drug contract); bare "INR" (its
        # only hit is "INR and Thrombectomy Consumables", where INR is Interventional
        # NeuroRadiology, not the clotting ratio); and bare "chromatograph" (both hits
        # are Cell and Gene Therapy Catapult bioprocessing columns, not analytical
        # chemistry). "cervical" and "HPV" are refused too: cervical also means the
        # cervical spine, and of six HPV hits three are vaccination and uptake work.
        #
        # Four more terms were tried LAST, after the feed's own loose `spec` field was
        # read to see what this rule was missing, and all four were refused:
        #   "lateral flow"     -> 10 hits, and every one is the 2021 DHSC mass-testing
        #     programme: manufacture contracts, raw materials for manufacture, five
        #     near-identical antigen device notices, and a staff-testing contract bought
        #     through the Nuclear Decommissioning Authority's shared services alliance.
        #     Self-test antigen devices distributed nationally are a closed pandemic
        #     market, not laboratory medicine procurement, and every row sits below the
        #     40-row cap in any case, so including them would have raised a headline
        #     count and shown a member nothing. The COVID rows that ARE kept are the
        #     laboratory-performed ones — PCR, serology, ELISA — bought by PHE, NHS
        #     Scotland and NHS trusts to run in their own laboratories.
        #   "extraction kit"   -> 2 hits. One is PHE's RapiPREP nucleic acid extraction
        #     kit, which "nucleic acid" already catches, and the other is QIAGEN
        #     extraction kits for Forensic Science Northern Ireland, whose title carries
        #     no forensic word at all — only its buyer does, and the exclusion list can
        #     only see titles. Refusing the term costs nothing and removes the row.
        #   "liquid handler"   -> 6 genuine laboratory-automation rows at PHE and DHSC,
        #     and one Scottish Police Authority automated liquid handler that, again,
        #     nothing in its title separates from them. Refused for the same reason,
        #     which does cost three PHE and DHSC rows. Better than publishing a police
        #     forensic instrument as a pathology award.
        #   "blood glucose"    -> 3 hits. Professional glucose meters and strips are
        #     genuinely run by hospital point-of-care testing teams inside pathology,
        #     and two of the three were bought by mental health trusts for physical
        #     health monitoring. The patch is contested with diabetes and endocrinology,
        #     and this page does not need to claim it: point-of-care testing is already
        #     reached through the framework's own name and through titles that say
        #     "point of care". Publishing nothing on a contested patch is the right
        #     output.
        # "bacteria" is included only in qualified forms — bacterial ID, bacteria
        # testing, mycobacteria, susceptibility testing, antimicrobial diffusion discs —
        # because bare "bacterial" catches breathing-circuit "Bacterial and Viral
        # Filters" and "Pulmonary Function Bacterial Viral Filters", which are
        # respiratory consumables.
        #
        # Included with no hit today, because each is unambiguous on this patch and
        # nothing else in health buys it: microtome, tissue processor, flow cytometry,
        # mass spectrometry, histocompatibility, toxicology, parasitology, blood bank,
        # cervical screening, cervical cytology, phlebotomy, venepuncture, vacutainer,
        # blood sciences, urinalysis and in vitro diagnostic. "autostainer" is included
        # with one hit, an immunohistochemistry autostainer at the University of
        # Glasgow, and is spelled with the optional prefix because a plain word-boundary
        # "stainer" does not match "Autostainer" — the form every vendor actually uses.
        "include": (
            r"\b(patholog\w*|histolog\w*|cytolog\w*|immunohistochem\w*|microbiolog\w*|"
            r"biochem\w*|haematolog\w*|hematolog\w*|immunolog\w*|virolog\w*|serolog\w*|"
            r"toxicolog\w*|mycolog\w*|parasitolog\w*|blood scienc\w*|"
            r"reagents?|assays?|analys(?:er|ers|or|ors)|"
            r"laboratory (?:medicine|diagnostic\w*)|"
            r"blood collection|phlebotom\w*|venepunctur\w*|venipunctur\w*|vacutainer|"
            r"specimen (?:bags?|containers?|transport|collection|pots?|tubes?|reception)|"
            r"transport of human tissue\w*|"
            r"point[- ]of[- ]care|\bPOCT\b|"
            r"\bPCR\b|next generation sequencing|\bNGS\b|sequencing|genomic\w*|"
            r"nucleic acid|genotyping|\bRCI\b|"
            r"mycobacteria\w*|bacterial id\b|bacteria testing|susceptibility testing|"
            r"antimicrobial susceptib\w*|antimicrobial diffusion disc\w*|"
            r"cytogenetic\w*|exome|molecular (?:diagnostic\w*|patholog\w*|test\w*)|"
            r"\bacgh\b|slide scanner|digital patholog\w*|"
            r"cryostat|microtome|tissue processor|(?:auto)?stainers?|"
            r"\bLIMS\b|laboratory information (?:management )?system\w*|"
            r"transfusion|blood group\w*|red cell|blood bank|"
            r"newborn screening|bloodspot|blood[- ]spot|genetic screening|bowel screening|"
            r"cervical screening|cervical cytolog\w*|bacterial screening|"
            r"\bFIT kits?\b|faecal immunochemical|"
            r"culture media|blood culture|swabs?|agar|"
            r"blood gas|coagulation|haemostasis|hemostasis|"
            r"immunoassay|\bELISA\b|mass spectrom\w*|flow cytometr\w*|"
            r"\bHLA\b|tissue typing|histocompatib\w*|"
            r"urinalys\w*|urine (?:collection|culture|specimen|sample)\w*|"
            r"in vitro diagnostic\w*|test kits?|testing kits?)\b"
        ),
        # EVERY PATTERN HERE FIRED ON A REAL ROW THAT MATCHED THE INCLUDE LIST AND WAS
        # WRONG. There are no speculative entries: the rule was rebuilt until each one
        # could be shown the title it caught. They fall into six families.
        #
        # VETERINARY AND AGRICULTURAL. The same PCR machines, ELISA kits and slide
        # scanners are bought to test cattle and soil. "Veterinary Molecular Biology Test
        # Kits" and "BVD PCR Test Kits for Serum and Milk Samples" are Scotland's Rural
        # College testing for bovine viral diarrhoea; "Provision of Johne's Elisa Test
        # Kits" is Johne's disease in cattle; DAERA and AFBI are Northern Ireland's
        # Agri-Food and Biosciences Institute, which bought both a digital pathology
        # slide scanner and TSE (BSE) rapid test kits; and the Animal and Plant Health
        # Agency's sterile boot swab kits are farm biosecurity.
        # FORENSIC SCIENCE. "HUMAN QUANTIFICATION REAL-TIME PCR SYSTEMS" is Forensic
        # Science Northern Ireland, part of the Department of Justice, quantifying DNA
        # for identification. FSNI appears on five notices in this data and is a
        # different discipline from clinical laboratory medicine, with different
        # vendors and no NHS market. Coronial HISTOPATHOLOGY is a different matter and
        # is kept — see the note under the counts below.
        # ACADEMIC RESEARCH PLATFORMS. Single-cell and spatial biology instruments are
        # research tools, not diagnostics: 10x Genomics at Birmingham and Edinburgh,
        # Glasgow's Chromium instruments and its spatial and single-cell platform at
        # Manchester, UKRI's Illumina NextSeq consumables, Glasgow's generic "Molecular
        # Biology Reagents" and its biomarker assay reagents for stored trial serum, and
        # UKRI's "Label Reagents". "Tissue culture" media is cell culture, and is
        # already excluded on the wound care page for the same reason.
        # WATER AND ENVIRONMENTAL MICROBIOLOGY. IDEXX Colilert and Quanti-Tray are
        # coliform counting in water, and Belfast's water treatment maintenance contract
        # matched on "microbiological water testing". None of it is a patient sample.
        # ANOTHER SPECIALITY'S INSTRUMENT WEARING THIS ONE'S WORD. "Purchase of Visual
        # Field Analysers" and "REICHERT OCULAR ANALYSER" are ophthalmology;
        # "Electrosurgical Devices (Cut & Coagulation, Uterine Ablation)" is diathermy;
        # the two UKRI "Cooling System (CryoStat)" notices are accelerator cryostats,
        # not histology ones; and "Insourcing of Bowel Screening and General Endoscopy
        # Services" is an endoscopy list, not a FIT laboratory. "Point of Care
        # Ultrasound (PoCUS) female patient simulator upgrades" is a training manikin:
        # point-of-care testing and point-of-care ultrasound share four words and
        # nothing else.
        # A TENDER TOO THIN TO PLACE. "NP646 Haemostatic & Coagulation Products" is an
        # NHS Scotland planning notice worth GBP 15,000,000 that matched on
        # "coagulation". Its full description on Find a Tender is one sentence — "The
        # Supply of Haemostatic & Coagulation Products within a healthcare environment
        # throughout the whole of Scotland" — and its only CPV code is 33140000, medical
        # consumables, not one of the laboratory reagent or analyser families. A
        # coagulation LABORATORY contract would carry 33696 or 38434. On the evidence
        # available it is at least as likely to be topical surgical haemostats, so it is
        # refused: haemostatic, the adjective for a product that stops bleeding, is a
        # surgical word, while haemostasis, the discipline, is the laboratory one, and
        # the exclusion is written to catch only the first. A GBP 15m lead published on
        # the wrong page is worse than no lead.
        # NOT A LABORATORY CONTRACT AT ALL. "NHS Pathologist" is Kent County Council
        # engaging a pathologist, a staffing contract with no laboratory goods or
        # service in it. "DHSC:GH: Fleming Fund" is the UK's overseas antimicrobial
        # resistance aid programme, buying reagents for laboratories in other countries.
        "exclude": (
            r"(veterinar\w*|\bAFBI\b|DAERA|animal and plant health|boot swab|\bBVD\b|"
            r"milk samples|johne|spongiform|nhs pathologist|\bFSNI\b|10x genomics|"
            r"chromium instrument|spatial genomics|single[- ]cell|"
            r"nextseq sequencing consumables|molecular biology reagents|label reagents|"
            r"biomarker assay|tissue culture|cooling system|visual field|ocular analys\w*|"
            r"electrosurgical|cut & coagulation|quanti[- ]?tray|coliert|colilert|"
            r"water treatment|fleming fund|endoscopy|point of care ultrasound|\bpocus\b|"
            r"haemostatic|hemostatic)"
        ),
        # CPV CORROBORATES, IT NEVER ADMITS, and on this patch the classification is
        # unusually clean because laboratory medicine has its own families: 33696*
        # reagents (33696100 blood grouping, 33696200 blood test, 33696300 chemical,
        # 33696500 laboratory), 85145000 services provided by medical laboratories,
        # 851118* pathology and blood analysis services, 38434* analysers, 24931250
        # culture media, 33124130 diagnostic supplies and 33141625 diagnostic kits.
        # The generic codes these notices also carry — 33100000 medical equipment,
        # 50000000 repair, 64120000 courier, 22820000 forms, 85100000 health services —
        # are deliberately not listed, because they corroborate nothing.
        "cpv": ("33696", "85145", "851118", "38434", "2493125", "33124130", "33141625"),
        # NO DRUG TARIFF PART, and this is an absence rather than a refusal. Part IX is
        # the reimbursement list for appliances dispensed in primary care: IXA dressings
        # and elastic hosiery, IXB incontinence appliances, IXC stoma appliances, IXR
        # elastic hosiery. There is no laboratory part, because a diagnostic test is not
        # an appliance and is never dispensed against an FP10. The field is left out
        # rather than reached for.
        "coverageNote": (
            "WHAT THE COUNTS BELOW DO AND DO NOT COVER. The 122 suppliers on Laboratory "
            "Diagnostics, Point of Care Testing and Pathology Managed Services are the "
            "names NHS Supply Chain lists across seven lots, and the count matches the "
            "total on its own product matrix. They are not 122 competitors for any one "
            "piece of business: no supplier is on all seven lots, only Roche Diagnostics "
            "and VWR International are on six, and 71 of the 122 are on exactly one lot. "
            "Lot 7, Outsourcing, was never awarded at all, so no supplier below is a "
            "route to a managed pathology service through this agreement. This panel "
            "carries no lot-by-lot split because the product matrix is not part of this "
            "dataset; page 2827 sets the lot structure out in full. "
            "Three NHS Supply Chain frameworks that carry a genuine laboratory strand "
            "are counted elsewhere and named in the rule rather than dropped: Digital "
            "Diagnostic Solutions, whose 54 suppliers mix laboratory information "
            "systems and digital pathology with about twenty radiology and imaging-AI "
            "firms and which publishes no supplier-by-lot split, is left to the "
            "radiology and imaging page; Specimen Cabinets is specimen radiography, an "
            "X-ray framework, despite its name; and the cardiac, audiological and sleep "
            "diagnostics frameworks belong to their own specialities. "
            "The awards list is filtered on contract titles, so it shows what a buyer "
            "chose to call a purchase. Two rows in it are histology service contracts "
            "bought by Police and Crime Commissioners rather than by the NHS. They are "
            "kept, and the buyer is named on each row, because coronial histopathology "
            "is the same discipline bought from the same laboratories; forensic DNA "
            "profiling, which is not, is excluded. Several rows are academic buyers "
            "— Queen's University Belfast, the London School of Hygiene and Tropical "
            "Medicine, the Liverpool School of Tropical Medicine — kept on the same "
            "test: the product is a clinical diagnostic one and the buyer is stated. "
            "Research-only single-cell and spatial biology platforms are excluded, "
            "whoever bought them."
        ),
    },
    "palliative-and-end-of-life-care": {
        "label": "Palliative and End-of-Life Care",
        # ONE framework, and it is the one this patch is defined by. NHS Supply Chain's
        # "Infusion Pumps and Administration Sets and Associated Products"
        # (Project_12 ITT_382) is where syringe drivers and their dedicated giving sets
        # sit, it holds 27 named suppliers, and it ENDS ON 30 SEPTEMBER 2026 with no
        # successor named on the brief. Page 2924 leads on exactly that.
        #
        # The page names SEVEN buying routes. Six are deliberately not claimed here, and
        # each is named rather than quietly dropped:
        #   NHS SBS10015 Acute and Community Health and Social Care Equipment (expires
        #     31/12/2026) is the community equipment route and is real, but it is an NHS
        #     Shared Business Services agreement. frameworks.json is built from NHS
        #     Supply Chain contract launch briefs only, so SBS10015 is not in this
        #     dataset at all and cannot be counted from it. The page carries it in its
        #     Buying route section with its own source link, which is where it belongs.
        #   Pressure Area Care and Patient Handling (53 suppliers) is counted on the
        #     tissue viability and patient handling pages, which is already two.
        #   Wheelchairs, Specialist Seating and Related Services (31) and Aids for Daily
        #     Living (31) are counted on the Patient Moving and Handling page.
        #   Disposable and Washable Continence Care (12) is counted on the continence,
        #     bladder and bowel page.
        #   Technology Enabled Care, Electronic Assistive Technology and Lone Worker
        #     Devices (18) is counted on the frailty and older people page.
        # Those five are genuinely bought for dying patients, and the page says so. They
        # are still not republished here, for the reason the page itself gives in its own
        # framework calendar note: "wound care, ostomy and nutrition frameworks that
        # touch a dying patient are carried on their own Hub pages rather than
        # duplicated here." Claiming them would put 145 mobility, continence and telecare
        # suppliers under a palliative Suppliers heading and bury the 27 that are this
        # patch's actual market. Sharing a framework across two pages is done where the
        # supplier list genuinely belongs to both, as Pressure Area Care does for wound
        # care and patient handling. A wheelchair framework's supplier list does not
        # become a palliative supplier list because hospices use wheelchairs.
        "frameworks": r"\binfusion pumps and administration sets\b",
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,342 of framework-awards.json — 3,314 titles —
        # and every hit was read one by one. The list returns 9 rows and all 9 are this
        # speciality.
        #
        # NOT INCLUDED, deliberately, and every one was tried and its hits read:
        #   bare "infusion pumps?"  -> four of its six hits are not this speciality.
        #     "Insulin Infusion Pumps, Continuous Glucose Monitoring Systems and
        #     Associated Consumables" (NHS National Services Scotland, twice) is
        #     diabetes, and "Rapid Infuser Blood/IV Infusion Pump" (University Hospitals
        #     of Derby and Burton, 19/08/2026) is a trauma and theatre rapid infuser.
        #     Nothing is lost by refusing it: all three genuine multi-product category
        #     contracts in this data also say "syringe pump" or "syringe driver" in the
        #     same title, so they are matched on the qualified term instead. A ward
        #     volumetric pump fleet is not a palliative purchase and this page will not
        #     claim one.
        #   bare "subcutaneous"     -> catches "Tocilizumab Subcutaneous Injection
        #     (RoActemra)" (NHS National Services Scotland, 03/02/2021), a rheumatology
        #     biologic. A subcutaneous injection is not a continuous subcutaneous
        #     infusion. Only the infusion, set, line and administration forms are used.
        #   bare "bereavement"      -> all four of its hits are somebody else's patch:
        #     "NGH - Maternity Bereavement Suite" (Northampton General, 07/09/2026) is a
        #     maternity room fit-out, "Provision of Suicide Bereavement Support Services"
        #     (Aneurin Bevan, 07/09/2026) and "Specialist Support Service For People
        #     Bereaved By Suicide" (Kent County Council, 04/09/2026) are mental health
        #     services, and "Provision of Bereavement and Mortuary Services (Funeral)"
        #     (North West Anglia, 28/08/2026) is a mortuary and funeral contract.
        #     Bereavement support is part of end-of-life care in NG142, but not one row
        #     in this data is the palliative kind, so the term is refused rather than
        #     kept and then argued with in the exclusion list.
        #   bare "mortuary"         -> its two hits are the funeral contract above and
        #     "Kings Park Mortuary and Medical Records Store Demolition Works" (Dorset
        #     HealthCare, 19/08/2026), which is a demolition. Care after death is not
        #     this dataset's mortuary spend.
        #   bare "terminal"         -> both its hits are "Aseptically Manipulated or
        #     Terminally Sterile Medicinal Products" (NHS South West Acutes and Peninsula
        #     Purchasing, 20/08/2024). Terminal sterilisation, not terminal care.
        #   bare "EOL"              -> "PAHT - EOLAS Medical Subscription" (Princess
        #     Alexandra Hospital, 02/09/2026) is a clinical guidelines app. The
        #     abbreviation also means end of life for an ASSET at least as often as for a
        #     patient, so it is refused in both readings.
        #   bare "resuscitation"    -> "Purchase of Baby Warmers with Resuscitation"
        #     (King's College, 25/04/2024) and "Resuscitation Council Course Manuals"
        #     (Southern Health and Social Care Trust, 31/01/2024). Neither is a DNACPR or
        #     ReSPECT matter, and neither is this patch.
        #   bare "respite"          -> its only hit, "Residential, respite and nursing
        #     care beds" (Comhairle nan Eilean Siar, 21/08/2026), is a council social
        #     care bed contract.
        #   opioid and anxiolytic drug names (morphine, diamorphine, midazolam, hyoscine,
        #     levomepromazine, and "opioid" itself) -> not one hit in 3,314 titles. They
        #     are refused for the future as well as the present: a morphine supply
        #     contract is acute pain or anaesthesia at least as often as it is palliative,
        #     and nothing in a title separates the two.
        #
        # Included with no hit today, because each is unambiguous on this patch and
        # nothing else buys it: continuous subcutaneous infusion, advance care planning,
        # anticipatory medicines and anticipatory prescribing.
        "include": (
            r"\b(palliative|hospices?|end[- ]of[- ]life|end of life|"
            r"syringe drivers?|syringe pumps?|ambulatory (?:syringe |infusion )?pumps?|"
            r"(?:continuous )?subcutaneous (?:infusion|set|administration|line)s?|"
            r"administration sets?|giving sets?|gravity sets?|"
            r"advance care plan\w*|anticipatory (?:medicines?|medication|prescrib\w*))\b"
        ),
        # ONE pattern, and it was put here because three real rows matched the include
        # list above and were wrong: "RPG Medical Administration Sets for Pandemic
        # Preparedness 25/26" (13/01/2026) and "Medical Administration Sets for Pandemic
        # Preparedness 24/25" (23/09/2025 and 22/09/2025), all three bought by the
        # Secretary of State for Health and Social Care. Those are national stockpile
        # intravenous giving sets held against a pandemic. Administration and giving sets
        # are kept in the include list because they are this framework's own named
        # products and the page's own words for them are "syringe drivers and giving
        # sets"; the stockpile is swept back out because a pandemic reserve is not a
        # palliative purchase.
        "exclude": r"\bpandemic preparedness\b",
        # NO CPV FAMILY, and it was checked rather than skipped. The only matching notice
        # carrying device codes at all is the Northern Ireland market engagement, and it
        # carries 33194110 infusion pumps and 33194120 infusion supplies — the whole
        # infusion family, shared with anaesthesia, oncology, diabetes and critical care,
        # not a palliative code. Every other matching notice carries only generic service
        # codes: 85323000 community health, 85100000 and 85000000 health services,
        # 60100000 road transport and 64120000 courier services. Not one is specific to
        # this speciality, so none is claimed. A CPV code could not admit a notice on its
        # own in any case.
        #
        # NO DRUG TARIFF PART, and this one is a deliberate refusal rather than an
        # absence. Part IX genuinely does reach dying patients at home: IXA dressings and
        # elastic hosiery, IXB incontinence appliances and IXC stoma appliances are all
        # used in end-of-life care, and page 2924's own Buying route section says so.
        # They are still not claimed here. IXA is 56,833 lines, and those three parts are
        # the tissue viability, continence and stoma pages' reimbursement lists;
        # republishing them under a palliative heading would present another speciality's
        # market as this one's and tell a rep nothing about a syringe driver. The page
        # names the route and links it. This panel carries no tariff.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. On this patch the buyer is very "
            "often not the NHS, and no framework record can show that. CQC's own care "
            "directory, produced 01 September 2026, lists 288 registered hospice "
            "locations in England across 210 providers, of which 167 providers are not "
            "NHS bodies, and 201 of the 288 locations carry a registered charity number "
            "in CQC's own file. That estate spends its own money and is under no "
            "obligation to use any NHS framework at all. None of that spend appears "
            "below, because it is not "
            "procured through anything this dataset records. What is counted is the one "
            "NHS Supply Chain framework this speciality is defined by, and it expires "
            "on 30 September 2026 with no successor named on its brief. Six further "
            "buying routes the page claims are counted elsewhere or are outside this "
            "dataset: NHS SBS10015 is an NHS Shared Business Services agreement and "
            "frameworks.json is built from NHS Supply Chain briefs only; Pressure Area "
            "Care and Patient Handling, Wheelchairs and Specialist Seating, Aids for "
            "Daily Living, Disposable and Washable Continence Care and Technology "
            "Enabled Care are all counted on the pages whose frameworks they primarily "
            "are. The supplier count also needs reading with care: NHS Supply Chain "
            "states no supplier total on its own brief for this framework, so the 27 is "
            "a count of the names it lists, and 27 names are not 27 competitors — two "
            "are Becton Dickinson entities, two more are the same ICU Medical group, "
            "and the T34 and the BodyGuard-T are the same company's products. The "
            "Suppliers count below reads 26 and not 27 for exactly that reason: NHS "
            "Supply Chain's two spellings of the ICU Medical group resolve to one entry. "
            "The page's Suppliers section sets out which names collapse into which group."
        ),
    },    # PAGE 2845. Scope as the page itself states it: dialysis, kidney transplantation
    # and chronic kidney disease.
    "renal": {
        "label": "Renal",
        # ONE framework, and it is the whole patch. "Renal Replacement Therapies
        # Services, Technologies and Consumables" (2023/S 000-017117, 28 March 2024 to
        # 27 March 2028, 25 suppliers, Diagnostic Equipment and Services CBU) is the
        # only NHS Supply Chain agreement named after this speciality. All 121 framework
        # names were read; three near neighbours carry renal product but are refused,
        # and are named here so nobody re-tests them:
        #   Central Venous Catheters and Associated Products (18 suppliers) does carry
        #     tunnelled dialysis lines, but the framework is vascular access for
        #     intensive care, oncology and parenteral nutrition as well, it publishes no
        #     supplier-by-lot split in this dataset, and claiming it whole would put
        #     eighteen vascular access firms under a renal Suppliers heading.
        #   Urology and Bowel Management and Male Intra-Urethral Catheter with Magnet
        #     Control are urology, not nephrology. A kidney stone is not renal medicine,
        #     and both are the continence, bladder and bowel page's frameworks.
        #   Infusion Pumps and Administration Sets is claimed by palliative and
        #     end-of-life care; nothing in its name is renal.
        "frameworks": r"\brenal replacement therap(?:y|ies)\b",
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,342 of framework-awards.json — 3,314 titles —
        # and all 36 surviving hits were read one by one. Every one of them is renal
        # replacement therapy: dialysis machines and consumables, peritoneal dialysis
        # fluids, CRRT, ITU haemofiltration, artificial kidneys, fistula needles,
        # dialysis catheters, satellite dialysis services and the DHSC RRT stockpile.
        #
        # WHY THERE IS NO EXCLUSION LIST. There was nothing to exclude: this pattern
        # produced no false positive at all. That is a real property of the patch —
        # renal vocabulary is unusually unshared — but it was reached by refusing the
        # loose terms in the include list, not by admitting them and arguing back.
        # Seven were tried first and every one of their hits was read:
        #   bare "kidney"    -> refused. Its only hits are the four Belfast "Nephral
        #     500ST Artificial Kidneys" rows, which "artificial kidney" catches on its
        #     own. The bare word is left out because a kidney dish is medical
        #     hollowware and a kidney stone is urology, and neither should ever be able
        #     to reach this panel on one word.
        #   bare "nephr*"    -> refused for the same reason and it costs nothing: its
        #     only hits today are those same four Nephral rows. A nephrostomy is
        #     interventional radiology and a nephrectomy is surgery. Only "nephrology"
        #     is kept, as an unambiguous term with no hit today.
        #   bare "transplant" -> refused. Both hits are corneal transplantation, at
        #     Queen Victoria Hospital and Moorfields. Only "kidney transplant" and
        #     "renal transplant" are kept, neither of which has a hit today.
        #   bare "fistula"   -> refused in favour of the qualified forms. All three of
        #     its hits are genuine here (Nipro fistula needles at Leeds, and NHS
        #     Lanarkshire's renal catheter and fistula packs twice), but an anal fistula
        #     is colorectal and the word must not be able to carry that in.
        #   "apheresis" and "plasma exchange" -> refused, 13 hits and none of them this
        #     page's. They are NHS Blood and Transplant, the Scottish National Blood
        #     Transfusion Service and trust transfusion departments buying Spectra Optia
        #     and LDL apheresis. TerumoBCT sits on the renal framework and Spectra Optia
        #     does therapeutic plasma exchange, which is exactly what makes the word
        #     look right; the contracts are haematology and patient blood management
        #     ones and are counted on that page.
        #   "water treatment" / "water purification" -> refused as terms. NHS Blood and
        #     Transplant's "Supply & Maintenance of New and Existing Water Purification"
        #     went to Veolia Water Technologies, who is on the renal framework, and it
        #     is still blood-processing water at NHSBT, not a dialysis unit. Belfast's
        #     water treatment contract IS admitted, but only because its own title names
        #     "Renal Equipment" — see the coverage note.
        #   bare "AKI"       -> refused. Its one hit is "NURTuRE-AKI biobank Custom
        #     tubing", bought by Cardiff University for a kidney research biobank.
        #   Organ retrieval was refused with it: NHSBT's cold static perfusion fluid
        #     (UW solution) and retrieval packs are multi-organ transplant logistics,
        #     not renal, and nothing in their titles separates a kidney from a liver.
        #
        # NEVER READ THE FEED'S OWN `spec` FIELD AND TRUST IT. It tags 41 rows renal and
        # 31 of them are wrong: micro pastettes, minimally invasive surgery consumables,
        # a Sentimag magnetic seed system, cryopreservation freezing bags, HLA
        # sequencing, blood pack and red cell washing contracts, copper sulphate
        # solution, genotyping microarrays and a veterinary pharmaceutical framework.
        "include": (
            r"\b(renal|dialys\w*|haemodialy\w*|hemodialy\w*|"
            r"haemofiltrat\w*|hemofiltrat\w*|haemodiafil\w*|hemodiafil\w*|"
            r"artificial kidney\w*|kidney transplant\w*|renal transplant\w*|"
            r"chronic kidney\w*|nephrolog\w*|"
            r"\bCRRT\b|\bRRT\b|fistula (?:needle|pack)\w*)\b"
        ),
        # NOTHING TO EXCLUDE. See the note above: this is written only because all 36
        # hits were read and every one is this speciality, and it is the one field a
        # future editor should fill the moment a false positive appears rather than
        # widening anything.
        "exclude": None,
        # CPV CORROBORATES, IT NEVER ADMITS. Renal has its own family and it shows on
        # this patch: 33181* renal support devices (33181000 on Northern Ireland's CRRT
        # and urology maintenance contract, 33181500 renal care consumables on Swansea
        # Bay's CRRT consumables), 3369280 dialysis solutions, and 85111900 hospital
        # dialysis services, which is the code Guy's and St Thomas' filed Satellite
        # Dialysis Services under. The generic codes these notices also carry —
        # 33140000 medical consumables, 33000000, 50000000 repair — are not listed,
        # because they corroborate nothing.
        "cpv": ("33181", "3369280", "85111900"),
        # NO DRUG TARIFF PART, and this is an absence rather than a refusal. Part IX
        # reimburses appliances dispensed in primary care against an FP10: IXA dressings
        # and elastic hosiery, IXB incontinence, IXC stoma, IXR elastic hosiery. Home
        # dialysis fluids and consumables are not dispensed that way — they are
        # delivered to the patient's home under the trust's own contract, which is what
        # Hull's "Home Peritoneal Dialysis" call-off with Vantive is — so there is no
        # renal part to claim.
        "coverageNote": (
            "WHAT THE COUNTS BELOW DO AND DO NOT COVER. NHS Supply Chain lists 25 "
            "supplier names on Renal Replacement Therapies Services, Technologies and "
            "Consumables, and that count matches the total stated on its own page. The "
            "Suppliers tab shows 24, because Nikkiso Belgium BV and Nikkiso Europe GmbH "
            "are one company and the Hub resolves them to one entry with both spellings "
            "against it. They are not 24 competitors for any one piece of business "
            "either: the framework spans haemodialysis machines, peritoneal dialysis, "
            "continuous renal replacement therapy, water treatment and body composition "
            "monitoring, and no lot-by-lot split is published in this dataset, so a "
            "supplier's presence here means it is on the agreement somewhere, not that "
            "it competes for the line you are selling. "
            "ONE COMPANY APPEARS UNDER TWO NAMES IN THE AWARDS LIST. Baxter Healthcare "
            "and Vantive are the same renal business either side of a change of owner, "
            "which is why NHS Supply Chain itself writes the supplier as \"Vantive "
            "Limited (formerly part of Baxter Healthcare Ltd)\" on the framework above. "
            "Awards are shown with the supplier name the notice carries and are not "
            "re-resolved, so older rows say Baxter and recent ones say Vantive. Read "
            "them as one incumbent, not two. "
            "CONTINUOUS RENAL REPLACEMENT THERAPY IS CLAIMED BY THIS PAGE and the "
            "critical care page will meet the same contracts. Every award below whose "
            "title says ITU, haemofiltration or CRRT was bought by intensive care rather "
            "than by a renal directorate. They are kept here because NHS Supply Chain "
            "itself files them under Renal Replacement Therapies and because the "
            "suppliers on them — Fresenius Medical Care, Vantive, Nikkiso and B. Braun — "
            "are this framework's suppliers. "
            "TWO AWARDS ARE MIXED CONTRACTS and are kept because their own titles say "
            "so, with the full title shown on the row. Belfast Health and Social Care "
            "Trust's water treatment maintenance covers decontamination equipment and "
            "microbiological water testing as well as renal equipment; the renal element "
            "is the dialysis water plant, and Veolia Water Technologies is on the "
            "framework above. The Regional Business Services Organisation's maintenance "
            "contract covers continuous renal replacement therapy and urology equipment "
            "together, and its urology half belongs to another page. "
            "The awards list is filtered on contract titles, so it shows what a buyer "
            "chose to call a purchase. Organ retrieval and transplant preservation "
            "contracts at NHS Blood and Transplant are excluded because they are "
            "multi-organ, and transplant tissue typing is counted on the pathology and "
            "laboratory medicine page."
        ),
    },
    # PAGE 2906. Scope, in the page's own words: two pathways that are bought by
    # different people. "The transfusion pathway is owned by the hospital transfusion
    # team; the VTE prevention pathway is owned by the thrombosis committee and the
    # ward." The page's own Related specialities line sends theatre consumables to
    # Theatres and surgical, haemato-oncology to Oncology and SACT, and the wider
    # laboratory to Pathology and laboratory medicine.
    "haematology-and-patient-blood-management": {
        "label": "Haematology and Patient Blood Management",
        # TWO FRAMEWORKS, NOT THE SEVEN THE PAGE NAMES, AND THE GAP IS DELIBERATE.
        # The page's Buying route section names seven NHS Supply Chain agreements that
        # each carry a slice of this patch. Two of the seven are not in frameworks.json
        # at all, and three are other pages' frameworks whose supplier lists cannot be
        # split. All five are named in the coverage note rather than quietly dropped.
        #   Blood Collection Devices (2024/S 000-033791, 19 suppliers) IS claimed. One
        #     lot, and the whole of it is blood collection: it absorbed the former Blood
        #     Collection Systems and Blood Lancets framework and the former Blood
        #     Culture Collection Systems framework. Pathology and laboratory medicine
        #     claims it too, and that is correct — a vacutainer is bought once and used
        #     by both — in the same way Pressure Area Care is shared between wound care
        #     and patient handling.
        #   Pressure Infusers and Associated Products (2025/S 000-047797, 8 suppliers)
        #     IS claimed. Rapid pressurised infusion of blood and fluid, no other page
        #     claims it, and it is the newest agreement on this patch: live from
        #     1 September 2026, with the brief promising a Core List refresh by mini
        #     competition within 12 months of go-live.
        # REFUSED, and each was checked rather than assumed:
        #   Laboratory Diagnostics, Point of Care Testing and Pathology Managed Services
        #     (2023/S 000-028831) carries 122 suppliers across seven lots, of which only
        #     Lot 2, Blood and Cellular Sciences, is this patch. frameworks.json records
        #     supplierLots as None for it, so there is no split to apply, and claiming it
        #     whole would put 122 genomics, digital pathology and point of care firms
        #     under a haematology Suppliers heading. This is the same refusal the renal
        #     rule makes over Central Venous Catheters.
        #   Vascular Therapy and Associated Products (2023/S 000-012286) carries 23
        #     suppliers across ten lots, of which Lots 1 to 3 are the anti-embolism
        #     stockings and intermittent pneumatic compression garments. Again no lot
        #     split, and the other seven lots are compression hosiery, lymphoedema and
        #     neuromuscular electrostimulation. The page says it outright: it is "a
        #     Rehabilitation and Community category agreement, not a haematology one".
        #     It is the vascular surgery page's framework and is counted there.
        #   Perfusion Devices, Consumables and Associated Equipment (2024/S 000-033613)
        #     is cardiopulmonary bypass, cardioplegia, oxygenators and ECMO. That is
        #     cardiac surgery and critical care, it is already the cardiology and
        #     cardiac surgery page's framework, and the perfusion vocabulary is refused
        #     from the include list below for the same reason.
        #   Suction, Wound Drainage, Autologous Blood Systems and Related Consumables
        #     (302060/1487175) and Blood Draw Tools and Accessories (2024/S 000-009366)
        #     are BOTH ABSENT from frameworks.json — all 121 names were read. The first
        #     is the only national route to cell salvage, so this is a real hole and the
        #     coverage note says so. Their award notices still reach the panel through
        #     the awards feed, because those are matched on title, not on framework.
        "frameworks": r"\b(blood collection devices|pressure infusers)\b",
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json, all 1,397 of framework-awards.json and the 6 open notices
        # — 3,375 titles — and every surviving hit was read one by one, then every term
        # was run again on its own to see what only it brought in.
        #
        # NOT INCLUDED, deliberately. Each was tried, its hits were read, and it was
        # refused rather than admitted and then argued with in the exclusion list:
        #   bare "blood"      -> the single worst term on this patch. It matches Blood
        #     Pressure Cuffs, three blood glucose contracts, three blood gas ones,
        #     "Gastrointestinal, Endocrine, Nutrition & Blood Medicines" twice, Dried
        #     Blood Spot Testing, a Blood Extraction Platform that is a molecular
        #     nucleic-acid extractor, "Clozapine Tablets and Blood Testing Service"
        #     twice, a taxi and courier contract for transporting blood tests, a health
        #     economic analysis of the blood culture pathway, and two titles too bare to
        #     call at all — "Blood Analyser" and "Blood Kiosks". Every genuine row is
        #     reached below through a qualified pair instead.
        #   bare "plasma"     -> "Inductively Coupled Plasma Optical Emission
        #     Spectrometer (ICP-OES)", University of Sussex. Analytical chemistry. The
        #     qualified forms below carry every real row.
        #   bare "coagulation"-> "Purchase of Electrosurgical Devices (Cut & Coagulation,
        #     Uterine Ablation)". Diathermy. It also takes out the open notice "NP646
        #     Haemostatic & Coagulation Products", which is ambiguous between surgical
        #     haemostats and coagulation reagents on the title alone and is therefore
        #     refused by both this page and theatres.
        #   bare "haemostat"  -> surgical haemostats, the same ambiguity. Only the
        #     -stasis form is used, which is the viscoelastic testing term.
        #   "anticoagulant", "heparin", "warfarin", "DOAC" -> "Heparins &
        #     Anticoagulants" and the NHS England Direct Oral Anticoagulant framework
        #     are real and are real anticoagulation, but the page puts them out of scope
        #     in its own words: pharmacological VTE prophylaxis is "bought through
        #     pharmacy, not through this patch".
        #   bare "thromb*"    -> "INR and Thrombectomy Consumables" and "Interventional
        #     Neuro Radiology and Thrombectomy Consumables", both NHS National Services
        #     Scotland. Stroke thrombectomy. The qualified thrombo- terms below are kept
        #     because they cannot carry that.
        #   bare "INR"        -> the same notice, and the reason it matched is worth
        #     recording: in "INR and Thrombectomy Consumables" the letters mean
        #     Interventional NeuroRadiology, not International Normalised Ratio. Refused
        #     outright; there is no way to tell the two apart on a title.
        #   bare "perfusion"  -> two LifePort organ perfusion contracts and two NHSBT
        #     cold static perfusion fluid (UW solution) ones, all kidney and multi-organ
        #     transplant preservation, which the renal rule refuses for the same reason.
        #     The cardiac bypass vocabulary — cardiopulmonary bypass, cardioplegia,
        #     oxygenator, ECMO — is refused with it: eight further rows, all of them
        #     cardiac surgery and critical care, and all of them the cardiology and
        #     cardiac surgery page's.
        #   bare "tourniquet" -> "The Supply of Multi-Use Pneumatic Tourniquet Devices"
        #     and an orthopaedic power tools bundle. Surgical limb tourniquets, not the
        #     phlebotomy kind.
        #   bare "stem cell" and bare "bone marrow" -> refused in favour of the donation
        #     forms. Both of today's hits are blood service donor work and both survive
        #     below, but an orthopaedic bone marrow aspirate concentrate and an ophthalmic
        #     limbal stem cell graft both carry these words and neither may reach this
        #     panel on them. "Stem Cell and Immunotherapy Services" at Newcastle is lost
        #     by that decision and it is the right trade: it is haemato-oncology, which
        #     the page's own Related specialities line routes to Oncology and SACT.
        #   bare "embolism"   -> only the qualified "anti-embolism" and "pulmonary
        #     embolism" are used, so an embolisation coil can never arrive here.
        #
        # NEVER READ THE FEED'S OWN `spec` FIELD AND TRUST IT. It is not used here and
        # must not be: it is a loose keyword match, and on the neighbouring wound care
        # patch it tags 10 false positives out of 16.
        "include": (
            r"\b(transfus\w*|h(?:ae|e)matolog\w*|immunoh(?:ae|e)matolog\w*|"
            r"h(?:ae|e)moglobin\w*|h(?:ae|e)moglobinopath\w*|an(?:ae|e)mia|"
            r"patient blood management|"
            r"blood component\w*|blood product\w*|blood bank\w*|blood group\w*|"
            r"blood pack\w*|blood collection|blood culture collection|"
            r"blood cell separator\w*|blood lancet\w*|blood warm\w*|blood and plasma|"
            r"blood don\w*|blood disorder\w*|blood service\w*|blood fridge\w*|"
            r"blood tracking|cord blood|whole blood|red cell\w*|"
            r"platelet\w*|cryoprecipitat\w*|granulocyte\w*|buffy coat\w*|"
            r"fresh frozen plasma|dried plasma|plasma component\w*|plasma exchange|"
            r"plasma fractionation|plasma storage|"
            r"plasma[\s/]*(?:blast[\s/]*)?freezer|"
            r"\w*pheresis\w*|bone marrow don\w*|stem cell don\w*|\bRhD\b|"
            r"cell salvage|autologous blood|autotransfus\w*|tranexamic|"
            r"viscoelastic\w*|thromboelast\w*|\bTEG\b|\bROTEM\b|sonoclot|"
            r"h(?:ae|e)mostasis|"
            r"rapid infuser\w*|pressure infuser\w*|major h(?:ae|e)morrhage|"
            r"anti[- ]?embolism|intermittent pneumatic compression|"
            r"venous thromboembol\w*|\bVTE\b|deep vein thromb\w*|\bDVT\b|"
            r"pulmonary embolism|thromboprophylax\w*|thrombophilia|"
            r"h(?:ae|e)mophil\w*|von willebrand|sickle cell|thalass\w*)\b"
        ),
        # ONE PATTERN, and it is here because one real row matched `include` and was
        # read and rejected:
        #   intraocular / phaco -> "Intraocular Lenses, Viscoelastics & Phaco machines".
        #     Ophthalmic viscoelastic device — the gel injected into the anterior chamber
        #     during cataract surgery. It shares its whole name with viscoelastic
        #     haemostatic testing and shares nothing else. Viscoelastic testing is named
        #     on the page as one of the two things to lead with, so the term stays and
        #     the cataract row goes.
        # Every other term above was narrowed until it produced no false positive, and
        # the notes on the refused terms record what each one caught before it was
        # dropped. This is the field to fill the moment a new false positive appears —
        # never widen anything to compensate.
        "exclude": r"\b(intraocular|phaco\w*)\b",
        # CPV CORROBORATES, IT NEVER ADMITS. Six prefixes, and every one of them fires
        # on a real row in this data rather than being listed on the strength of the
        # code book: 336961 blood-grouping reagents and 336962 blood-testing reagents
        # (Red Cell Reagents at National Services Scotland, and the Automated
        # Immunohaematology System), 3843457 haematology analysers (the Welsh Blood
        # Service analyser), 3843452 blood analysers, 3314150 haematological consumables
        # and 8511181 blood-analysis services (the Welsh Blood Service stem cell donor
        # evaluation). The generic codes these same notices also carry — 50000000
        # repair, 33100000, 85100000, 38000000 — are left out because they corroborate
        # everything and therefore nothing.
        "cpv": ("336961", "336962", "3843452", "3843457", "3314150", "8511181"),
        # NO DRUG TARIFF PART. Part IX reimburses appliances dispensed in primary care
        # against an FP10: IXA dressings and elastic hosiery, IXB incontinence, IXC
        # stoma, IXR elastic hosiery. Nothing on this patch is dispensed that way. Blood
        # components are invoiced to hospitals by NHS Blood and Transplant against a
        # national price list, cell salvage and viscoelastic testing are hospital
        # capital, and hospital anti-embolism stockings are issued on the ward, not
        # prescribed — Part IXA elastic hosiery is the community venous disease and
        # lymphoedema range, which is the wound care page's. So the panel carries no
        # tariff rather than reaching for the nearest part.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. There is no NHS Supply Chain "
            "haematology framework. The page's Buying route section names seven "
            "agreements written for other categories that each carry a slice of this "
            "patch, and the Frameworks tab below claims two of them. Blood Collection "
            "Devices and Pressure Infusers and Associated Products are claimed because "
            "each is wholly this patch. Laboratory Diagnostics, Point of Care Testing "
            "and Pathology Managed Services (122 suppliers) and Vascular Therapy and "
            "Associated Products (23 suppliers) are NOT claimed: this patch is one lot "
            "of seven on the first and three lots of ten on the second, neither "
            "publishes a supplier-by-lot split in this dataset, and claiming either "
            "whole would put genomics, digital pathology or compression hosiery firms "
            "under a haematology Suppliers heading. Perfusion Devices, Consumables and "
            "Associated Equipment is not claimed either: cardiopulmonary bypass and "
            "ECMO are the cardiology and cardiac surgery page's. "
            "TWO OF THE SEVEN ARE NOT IN THE HUB'S FRAMEWORK DATASET AT ALL, and one of "
            "them matters. Suction, Wound Drainage, Autologous Blood Systems and Related "
            "Consumables (302060/1487175) is the only national route to cell salvage, "
            "and Blood Draw Tools and Accessories (2024/S 000-009366) carries the "
            "tourniquets and blood lancets. Neither is among the 121 framework records "
            "the Hub holds, so their suppliers are not counted below. Their own award "
            "notices do appear in the awards list, because awards are matched on the "
            "title of the notice and not on framework membership. "
            "BLOOD COMPONENTS ARE NOT PROCURED AT ALL and no framework will ever show "
            "them. Red cells, platelets, fresh frozen plasma, cryoprecipitate, "
            "granulocytes and buffy coats are manufactured and issued by NHS Blood and "
            "Transplant and invoiced to hospitals against a national price list "
            "reissued annually. There is no tender, no competitive field and no expiry "
            "date, so the largest single line of spend on this patch is structurally "
            "invisible to every panel below. The page's Market intelligence section "
            "carries the price list instead. "
            "ONE COMPANY APPEARS TWICE IN THE SUPPLIER LIST BELOW AND IS NOT YET "
            "MERGED. NHS Supply Chain names \"GBUK Ltd\" on Blood Collection Devices "
            "and \"GB UK Ltd\" on Pressure Infusers, and they are the same Yorkshire "
            "company: no company called GB UK Ltd or GB UK Limited exists on the active "
            "Companies House register, searched 09/09/2026, and the Hub\'s own record "
            "for the second spelling already carries gbukgroup.com as its website. The "
            "Hub\'s supplier seed still holds them as two records, so the count below "
            "reads 26 where 25 companies stand. Merging them changes the Compare tab as "
            "well as this panel and is being done as its own change rather than folded "
            "into this one. Read them as one supplier. "
            "THE AWARDS LIST IS WIDER THAN THE TWO CLINICAL PATHWAYS THE PAGE WALKS "
            "THROUGH. It also counts the blood services' own contracts — donor "
            "eligibility, bone marrow and stem cell donor work, apheresis, component "
            "manufacture and storage — and the inherited bleeding and haemoglobin "
            "disorders: haemophilia and von Willebrand factor, sickle cell and "
            "thalassaemia. Those are this speciality by name and no other Hub page "
            "would hold them. Haemato-oncology is not counted here; the page's own "
            "Related specialities line routes it to Oncology and SACT. "
            "TWO AWARDS ARE MIXED CONTRACTS and are kept because their own titles say "
            "so, with the full title shown on the row. The Procurement and Logistics "
            "Service's Evacuated Blood Collection Systems and Urine Collection Systems "
            "buys phlebotomy and specimen tubes together, and its urine half belongs to "
            "the continence page. The BSO's Blood and Fluid Warming Systems buys blood "
            "warming and general fluid warming on one notice. "
            "Being named on a framework is not evidence of volume, and being absent "
            "from one is not evidence of absence from the market."
        ),
    },

    # PAGE 2908. Two pathways that run in parallel and are bought separately: the
    # maternity pathway from first contact to postnatal discharge, and the neonatal
    # pathway from anticipated preterm birth to two-year follow-up. The page's own
    # Buying route card says it plainly: "Four NHS Supply Chain agreements across two
    # categories. Only one carries the word maternity; neonatal equipment is Lot 3 of
    # four on an anaesthesia framework."
    "maternity-and-neonatal": {
        "label": "Maternity and Neonatal",
        # ALL FOUR AGREEMENTS THE PAGE NAMES, and all four are in frameworks.json.
        # Matched on maternity / obstetrics / infant feeding / neonatal, which between
        # them hit these four names and no other of the 121:
        #   Maternity, Obstetrics, Gynaecology and Sexual Health Products
        #     (2019/S 214-525123, ends 30 June 2027)
        #   Obstetrics and Vinyl Pessaries (2025/S 000-007017, ends 20 August 2027)
        #   Infant Feeding and Accessories (2023/S 000-011743, ends 28 February 2028)
        #   Anaesthesia Machines, Ventilators, Neonatal Equipment and Phototherapy
        #     Systems, Related Accessories and Services (2026/S 000-008108)
        # TWO OF THE FOUR ARE SHARED WITH ANOTHER PAGE ON PURPOSE, in the same way
        # Pressure Area Care is shared between wound care and patient handling:
        #   Infant Feeding and Accessories is also nutrition and dietetics'. Half its
        #     list is condition-specific formula and half is expression and feeding
        #     hardware, and both pages' own Buying route sections name it.
        #   Anaesthesia Machines, Ventilators, Neonatal Equipment and Phototherapy
        #     Systems is also theatres and surgical's, for Lots 1 and 2. Neonatal
        #     equipment is Lot 3 and it is the only national route to it, so this page
        #     cannot omit the agreement its own neonatal half is bought through.
        # NOT CLAIMED, and each was checked against the 121 names rather than assumed:
        #   External Breast Prosthesis and Chest Support is post-mastectomy fitting,
        #     which is the rehabilitation, prosthetics and orthotics page's. It is the
        #     reason bare "breast" is refused from the include list below.
        #   Non Invasive Ventilation, Sleep Therapy, CPAP and Sleep Monitoring
        #     Diagnostics is adult respiratory and sleep. Neonatal CPAP is bought on
        #     the anaesthesia and neonatal agreement above, not on this one.
        "frameworks": r"\b(maternity|obstetrics|infant feeding|neonatal)\b",
        # SIX COMPANIES ARE REMOVED FROM THE MATERNITY FRAMEWORK'S SUPPLIER LIST
        # BECAUSE NHS SUPPLY CHAIN LISTS THEM AS DELISTED. frameworks.json holds 57
        # names for that framework and flags the count itself as UNVERIFIED. The brief
        # was read live on 09/09/2026: it prints 51 current suppliers, then the line
        # "The following suppliers are being delisted at the start of the new
        # framework:" and six more. The crawler swept that tail into the supplier list.
        # 57 = 51 + 6, exactly. Publishing it raw would tell a rep that Bray, Cardiac
        # Services, Durbin, Medichill, Valley Northern and Viomedex are competitors on
        # a framework they have just left. Corrected here rather than in
        # frameworks.json, which is regenerated by the crawler and would revert.
        "frameworkCorrections": {
            "Maternity, Obstetrics, Gynaecology and Sexual Health Products": {
                "removeSuppliers": [
                    "Bray Group Limited",
                    "Cardiac Services UK Ltd",
                    "Durbin Plc",
                    "Medichill UK Ltd",
                    "Valley Northern",
                    "Viomedex Ltd",
                ],
                "why": (
                    "51 current suppliers, read from NHS Supply Chain's own contract "
                    "launch brief on 09/09/2026. The brief's Suppliers section prints "
                    "51 entries and then names six further companies as being delisted "
                    "at the start of the new framework; the Hub's crawler read all 57 "
                    "as suppliers, and the six delisted names are taken back out here. "
                    "The brief's own prose states 54 in two places and 51 are printed, "
                    "so 51 is what the list supports and 54 is what NHS Supply Chain "
                    "asserts. Two of the 51 printed entries (Elemental Healthcare Ltd "
                    "and Pelvic Relief) may be one company shown on two lines."
                ),
            },
        },
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json, all 1,397 of framework-awards.json and the 6 open
        # notices — 3,375 titles — and every surviving hit was read one by one.
        #
        # THE WORD BOUNDARIES ARE LOOKAROUNDS, NOT \b, AND THAT IS DELIBERATE. An
        # underscore is a word character, so \bantenatal\b does not match
        # "Lease_PROJ004570_Antenatal Ultrasound Scanner" — a real Nottingham University
        # Hospitals row, and the only antenatal scanner award in the data. Losing a true
        # positive to punctuation is as wrong as admitting a false one, so the pattern
        # treats anything that is not a letter or a digit as a boundary.
        #
        # NOT INCLUDED, deliberately. Each was tried, its hits were read, and it was
        # refused rather than admitted and then argued with in the exclusion list:
        #   bare "breast"     -> the worst term on this patch by some distance. Breast
        #     imaging, breast biopsy needles, breast implants, surgically implanted
        #     breast prostheses, external breast prosthesis, Oncotype DX, mobile breast
        #     screening trailers, insourced breast radiology and breast surgery
        #     capacity. Eleven rows, none of them maternity. Only "breast pump" and
        #     "breast milk" are used.
        #   bare "milk"       -> "Provision of Milk & Bread" at Morecambe Bay (hospital
        #     catering) and "BVD PCR Test Kits for Serum and Milk Samples" at SRUC
        #     (bovine viral diarrhoea testing in cattle). Only the qualified milk terms
        #     are used.
        #   bare "infant" and bare "baby" -> "Parent Infant Psychotherapy to families in
        #     East Sussex" and the Brent Parent and Infant Relationship Service, both
        #     local-authority mental health services; "Supply & Distribution of Baby
        #     Packs" at Rotherham MBC and the Welsh Government's "Baby Bundles", both
        #     welfare schemes rather than clinical procurement. The genuine rows are
        #     reached through "infant ventilator", "baby warmer", "infant feeding" and
        #     "infant formula" instead.
        #   bare "incubator"  -> "Platelet Incubator for CGH", NHS Blood and Transplant's
        #     "Platelet Agitator and Incubator equipment", and two Cambridge "BINDER
        #     CB170 CO2 incubators". Laboratory and blood-bank incubators, every one.
        #     The neonatal kind is reached through neonatal / infant / transport
        #     incubator and through "isolette", which is Draeger's neonatal incubator
        #     name and carries the one real row ("Spare Parts for Draeger Isolette
        #     Incubators").
        #   bare "fetal"/"foetal" -> "Supply of BVD-free Foetal Bovine Serum to APHA".
        #     Foetal bovine serum is the standard cell-culture reagent and it will keep
        #     recurring, so the term is qualified rather than excluded.
        #   bare "labour"     -> "YAS 58 2026_27 (DA Non FW) Various Ortus Parts &
        #     Labour". Work, not childbirth. Only "labour ward" is used.
        #   bare "delivery"   -> the single most overloaded word in public procurement.
        #     Only the phrase "delivery suite" is used, which means the labour ward and
        #     nothing else.
        #   bare "uterine"/"uterus" -> "Purchase of Electrosurgical Devices (Cut &
        #     Coagulation, Uterine Ablation)" and "Endometrial Ablation Devices and
        #     Uterine Tissue Removal Systems". Gynaecology, which has its own Hub page.
        #   bare "phototherapy" -> Lot 4 of the neonatal agreement is ADULT and
        #     PAEDIATRIC phototherapy, which is dermatology. Neonatal phototherapy is
        #     already reached through "neonatal", so the bare word buys nothing and
        #     would one day admit a dermatology UVB cabinet.
        #   "pregnancy"       -> "Complex Termination of Pregnancy (CTOP) Services
        #     across the South East". Termination services are the gynaecology and
        #     women's health page's, as is Lot 2 Sexual Health of the framework above.
        #     It was the only row the term brought, so it is refused outright.
        #   "lactate"-safe forms only -> "lactation" is used, never "lactat\w*", which
        #     would match blood lactate and Ringer's lactate.
        #   bare "sanitary", "period", "feminine" -> North Lanarkshire Council's
        #     "Provision of Sanitary Products" and Cardiff Council's Period Dignity
        #     Programme. Council welfare schemes.
        #   bare "cord"       -> "Neuromodulation/Spinal Cord Stimulators" and NHS Blood
        #     and Transplant's "Supply of Cord Blood Collection Systems". Cord blood
        #     banking is haematology's and is claimed there by name. Only "cord clamp"
        #     and "umbilical" are used.
        #   "blood spot"      -> "Dried Blood Spot Testing" at Midlands Partnership,
        #     which is adult virology. "Newborn Bloodspot Cards" is reached through
        #     "newborn" instead.
        #   bare "entonox"    -> "Mobile Entonox Destruction Devices" at Sheffield, which
        #     is nitrous oxide abatement bought for net zero, not a labour-ward analgesia
        #     purchase.
        #   "epidural", "speculum", "ultrasound scanner" -> anaesthesia, gynaecology and
        #     radiology respectively. Six rows between them, none of them this patch.
        #   "prematur\w*"     -> refused in favour of "preterm" and "retinopathy of
        #     prematurity". "Premature termination" is a contract-law phrase.
        #
        # NEVER READ THE FEED'S OWN `spec` FIELD AND TRUST IT, and this patch is the
        # clearest demonstration in the dataset. It tags just 3 of the 1,972 rows
        # maternity-and-neonatal. All 3 are genuine and all 3 are kept, but it files
        # "Purchase of Baby Warmers with Resuscitation" under pharmacy-and-medicines,
        # "Breast Pumps and Breast Milk Collection Sets" under pathology-and-laboratory-
        # medicine, newborn screening test kits under gynaecology-and-womens-health, and
        # both "Fetal Cushions" and "Button Hole CTG Belts" under digital-and-medical-it.
        "include": (
            r"(?<![A-Za-z0-9])("
            r"maternit\w*|midwif\w*|obstetric\w*|antenatal|ante[- ]natal|"
            r"postnatal|post[- ]natal|perinatal|intrapartum|peripartum|"
            r"neonat\w*|newborn|new[- ]born|NICU|SCBU|special care baby|"
            r"delivery suite|labour ward|birthing|childbirth|home birth|stillbirth|"
            r"fo?etal (?:monitor\w*|doppler\w*|cushion\w*|pillow\w*|scalp|heart|"
            r"medicine|neuroprotect\w*|blood sampl\w*)|"
            r"CTG|cardiotocograph\w*|caesarean|cesarean|episiotom\w*|ventouse|"
            r"vacuum extract\w*|pessar\w*|cord clamp\w*|umbilical|placenta\w*|"
            r"breast pump\w*|breast milk|breastmilk|human milk|donor milk|"
            r"milk bank\w*|milk kitchen|milk bottle\w*|milk fortifier\w*|"
            r"formula milk|infant formula|infant food|infant feeding|lactation|"
            r"baby warmer\w*|infant warmer\w*|radiant warmer\w*|resuscitaire\w*|"
            r"infant ventilator\w*|infant incubator\w*|neonatal incubator\w*|"
            r"transport incubator\w*|isolette\w*|"
            r"transcutaneous bilirubin|bilirubin meter\w*|bilirubinomet\w*|jaundice|"
            r"surfactant|retinopathy of prematurity|preterm|pre[- ]term"
            r")(?![A-Za-z0-9])"
        ),
        # ONE PATTERN, and it is here because four real rows matched `include` and were
        # read and rejected:
        #   non-obstetric / non-obstetrical -> "Non-Obstetrical Ultrasound - East Surrey"
        #     and "Non-Obstetric Ultrasound Service - East Surrey" at Surrey and Sussex
        #     ICB, and "Insourced Non-Obstetric Ultrasound Services YSTH" twice at York
        #     and Scarborough. All four are general ultrasound capacity defined by
        #     EXCLUDING obstetrics. The word "obstetric" is doing the opposite of what a
        #     keyword match assumes, which is why the negation has to be matched
        #     explicitly and cannot be narrowed away in the include list.
        "exclude": r"(?<![A-Za-z0-9])non[- ]?obstetric\w*",
        # CPV CORROBORATES, IT NEVER ADMITS. Two prefixes, and both fire on a real
        # matching row rather than being listed from the code book: 15884 baby food and
        # 33750 baby care products, both on the DHSC formula milk funding scheme. They
        # corroborate the infant feeding half of this patch and nothing else — there is
        # no obstetric or neonatal-device CPV family in this data. Two codes were
        # checked and REFUSED: 33152000 incubators, which in this feed fires only on
        # Cambridge's laboratory CO2 incubators, and 3314111x dressings, which is the
        # very code that put "Newborn Transport Harnesses for London Ambulance" on the
        # wound care page. 33750 also fires on "Baby Bundles", which the title filter
        # refuses as a Welsh Government welfare scheme — and it stays refused, because a
        # CPV code cannot admit a notice on its own.
        "cpv": ("15884", "33750"),
        # NO DRUG TARIFF PART. Part IX reimburses appliances dispensed in primary care
        # against an FP10: IXA dressings and elastic hosiery, IXB incontinence, IXC
        # stoma, IXR elastic hosiery. Nothing on this patch is listed there. Maternity
        # and neonatal consumables are bought by trusts through NHS Supply Chain, the
        # neonatal equipment is capital, and infant formula reaches families through
        # Healthy Start and the DHSC scheme above rather than through Part IX. So the
        # panel carries no tariff rather than reaching for the nearest part.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. All four NHS Supply Chain "
            "agreements the page names are claimed below, and two of the four carry "
            "more than this patch. Maternity, Obstetrics, Gynaecology and Sexual "
            "Health Products has two lots, of which Lot 2 is Sexual Health; "
            "Anaesthesia Machines, Ventilators, Neonatal Equipment and Phototherapy "
            "Systems has four lots, of which only Lot 3 is neonatal equipment. NHS "
            "Supply Chain publishes no supplier-by-lot split for either, so the "
            "supplier list below is every company named on the agreement as a whole. "
            "That is why anaesthesia machine manufacturers such as Draeger, Penlon and "
            "GE appear under a maternity and neonatal Suppliers heading, and why the "
            "sexual health suppliers on the first agreement appear too. Theatres and "
            "surgical counts the same anaesthesia agreement for Lots 1 and 2, and "
            "nutrition and dietetics counts Infant Feeding and Accessories; both are "
            "genuinely shared, in the way one Pressure Area Care agreement really does "
            "carry both mattresses and hoists. "
            "SIX DELISTED COMPANIES HAVE BEEN TAKEN OUT OF THE MATERNITY SUPPLIER "
            "LIST. NHS Supply Chain's contract launch brief prints 51 current "
            "suppliers and then names Bray Group Limited, Cardiac Services UK Ltd, "
            "Durbin Plc, Medichill UK Ltd, Valley Northern and Viomedex Ltd as being "
            "delisted at the start of the new framework. The Hub's framework crawler "
            "read all 57 names as suppliers. Read live on 09/09/2026, the six are "
            "removed here, and they are recorded against the framework rather than "
            "dropped. The upstream crawler still has the fault. "
            "THE SUPPLIER COUNT ON THAT BRIEF DOES NOT ADD UP, AND NEITHER FIGURE IS "
            "SAFE TO QUOTE. The brief states 54 suppliers in its Overview and 54 again "
            "in its Suppliers section, where it also says 11 are new against 12 in the "
            "Overview. The list printed underneath contains 51 entries. This panel "
            "shows 51, because that is the number the published list supports; 54 is "
            "what NHS Supply Chain asserts. Two of the 51 (Elemental Healthcare Ltd "
            "and Pelvic Relief) may be one company presented as two lines, which is "
            "why the honest statement is 51 printed entries against a stated 54 rather "
            "than a claim about how many companies hold the framework. "
            "BRAY GROUP HOLDS ONE AGREEMENT AND WAS DELISTED FROM THE OTHER. Bray "
            "Group Ltd (Bray Healthcare) is one of only three suppliers on Obstetrics "
            "and Vinyl Pessaries, and Bray Group Limited is on the maternity "
            "agreement's delisted list. It therefore appears below on the pessaries "
            "agreement only. NHS Supply Chain states no relationship between the "
            "delisting and the pessary carve-out and this panel draws none. "
            "THE NEONATAL CATEGORY NO LONGER HAS AN AGREEMENT OF ITS OWN. Until 2 "
            "March 2026 there was a framework whose title began with the word "
            "Neonatal. Neonatal equipment is now Lot 3 of four on an agreement whose "
            "title begins Anaesthesia Machines, in the Diagnostic Equipment and "
            "Services category, bought through the Direct route with a Unique "
            "Reference Number from the Category team rather than through the stocked "
            "catalogue. Seven suppliers were delisted at the start of it, including "
            "SLE Ltd and Vyaire Medical Products Limited, and NHS Supply Chain gives "
            "no reason. "
            "TWO AWARDS BELOW ARE MIXED CONTRACTS and are kept because their own "
            "titles say so, with the full title shown on the row. The surgical "
            "positioning table bought by NHS Wales is for maternity AND gynaecology "
            "procedures, and the colposcope bought by University Hospitals Sussex is "
            "capital for the Central Delivery Suite — a gynaecology device, sited and "
            "funded on the labour ward. "
            "THE AWARDS LIST COUNTS NEWBORN SCREENING. Bloodspot cards, SMA screening "
            "kits and the cystic fibrosis and congenital hypothyroidism test kits are "
            "national newborn screening programmes delivered through maternity and "
            "neonatal services, and no other Hub page holds them. Gynaecology, sexual "
            "health, fertility and termination of pregnancy are NOT counted here; they "
            "are the gynaecology and women's health page's, which is why the open "
            "notices Womens Health and NP36726 Fertility Medicines do not appear below "
            "even though both are live today. "
            "Being named on a framework is not evidence of volume, and being absent "
            "from one is not evidence of absence from the market."
        ),
    },

    # PAGE 2836. Scope, in the page's own words: two clinically distinct pathways.
    # Benign gynaecology runs on NICE NG88 and ends in theatre or an outpatient
    # hysteroscopy suite; urogynaecology and the pelvic floor runs on NG123, is
    # governed by the mesh restriction, and ends in a regional multidisciplinary team.
    # The page also carries colposcopy and outpatient optics, the pessary economy,
    # sexual health, fertility and termination of pregnancy.
    "gynaecology-and-womens-health": {
        "label": "Gynaecology and Women's Health",
        # SIX AGREEMENTS, and every one of them is named in the page's own Buying
        # route blocks, which were read against frameworks.json on 10/09/2026. The
        # reference number and end date of all six match what the page states:
        #   Maternity, Obstetrics, Gynaecology and Sexual Health Products
        #     (2019/S 214-525123, ends 30 June 2027) — the page calls this "the
        #     consumables route for this whole patch". Shared with maternity and
        #     neonatal, which counts the obstetric half; this page counts the
        #     gynaecology and sexual health half. Maternity's own rule records that
        #     Lot 2 Sexual Health is this page's, so the two do not contradict.
        #   Obstetrics and Vinyl Pessaries (2025/S 000-007017, ends 20 August 2027) —
        #     three suppliers, the hospital half of the pessary economy. Also counted
        #     on maternity. Vinyl pessaries are fitted for pelvic organ prolapse,
        #     which is NG123 ground, so the page that carries NG123 cannot omit it.
        #   Rigid Endoscopy and Associated Options and Related Services
        #     (2021/S 000-007768, ends 31 March 2028) — hysteroscopes. Shared with
        #     urology from 10/09/2026, whose rule counts the Urology Scopes half of the
        #     same brief's product categories.
        #   Minimally Invasive Surgery, Related Equipment and Accessories
        #     (2026/S 000-061906, ends 9 August 2028) — Lot 6 is Gynaecological
        #     Endoscopy and Uterine Ablation, live 10 August 2026. Shared with
        #     theatres and surgical, which counts Lots 1 to 5.
        #   Surgical Mesh (2024/S 000-021744, ends 6 July 2027) — see the coverage
        #     note, which carries the page's own sourced warning about it.
        #   Surgical Implants for Men's and Women's Health (2025/S 000-025202, ends
        #     31 March 2028) — six suppliers, the urogynaecology implant route.
        #
        # NOT CLAIMED, and each was checked against the 121 names rather than assumed:
        #   External Breast Prosthesis and Chest Support -> post-mastectomy fitting.
        #     The maternity and neonatal rule already records this as the
        #     rehabilitation, prosthetics and orthotics page's, and a decision already
        #     taken is not reopened here to make this panel look fuller.
        #   Neuromodulation Devices and Associated Products -> the page gives it a
        #     Buying route block and then states, in its own words, that whether
        #     sacral neuromodulation for bladder is called off there is "Not verified
        #     from the public brief", because NHS Supply Chain describes the agreement
        #     as "strategic pain management solutions" and publishes no lot breakdown.
        #     Claiming it would put 23 pain-management suppliers on a gynaecology
        #     Suppliers tab on the strength of something the page itself refuses to
        #     assert. Refused until the lot split is published (rule 14c).
        #   Procedure Packs and Electrosurgical Consumables -> the page's own heading
        #     for these is "THEATRE PACKS, ELECTROSURGERY AND THE SHARED CONSUMABLE
        #     BASE". Procedure Packs Lot 2 is listed as covering "Obstetrics,
        #     Gynaecological, General Surgical, Orthopaedics, Vascular, ENT" and
        #     Electrosurgical Consumables as "commonly used in dermatological,
        #     gynaecological, cardiac" procedures. A lot shared with five other
        #     specialities is theatres', not this page's. The test applied throughout
        #     is whether a lot is NAMED for this speciality: Minimally Invasive
        #     Surgery Lot 6 is, these are not.
        #   Mammography Imaging Systems -> radiology and imaging's, and claimed there.
        #   Urology and Bowel Management, Disposable and Washable Continence Care ->
        #     continence, bladder and bowel's, and claimed there.
        #   Bladder Scanners -> the continence rule already refuses it as a Diagnostic
        #     Equipment capital route, and this page's pathway two turns on
        #     urodynamics rather than bladder scanning.
        #   Operating Theatre and Outpatient Microscopes and Associated Accessories
        #     (2022/S 000-020537) -> the colposcope route, and the page is right that
        #     it expires 4 December 2026. It CANNOT be claimed because it is not in
        #     frameworks.json at all: the crawler holds 121 names and this is not one
        #     of them. That is a coverage gap in the Hub's own data, not a judgement
        #     about the patch, and it is stated in the coverage note rather than
        #     papered over.
        "frameworks": (
            r"\b(gynaecolog\w*|pessar\w*|rigid endoscopy|minimally invasive surgery|"
            r"surgical mesh|surgical implants for men)"
        ),
        # THE SAME SIX DELISTED COMPANIES THE MATERNITY RULE REMOVES ARE REMOVED HERE.
        # frameworks.json holds 57 names for the shared maternity, obstetrics,
        # gynaecology and sexual health agreement and flags the count itself as
        # UNVERIFIED. NHS Supply Chain's own contract launch brief prints 51 current
        # suppliers and then the line "The following suppliers are being delisted at
        # the start of the new framework:" followed by six more; the crawler swept
        # that tail into the supplier list. 57 = 51 + 6, exactly. The correction is
        # duplicated rather than shared because a shared framework must not be
        # corrected on one page and published raw on the other — that is precisely the
        # defect that put "HTTP 404" panels in front of members, in a different shape.
        "frameworkCorrections": {
            "Maternity, Obstetrics, Gynaecology and Sexual Health Products": {
                "removeSuppliers": [
                    "Bray Group Limited",
                    "Cardiac Services UK Ltd",
                    "Durbin Plc",
                    "Medichill UK Ltd",
                    "Valley Northern",
                    "Viomedex Ltd",
                ],
                "why": (
                    "51 current suppliers, read from NHS Supply Chain's own contract "
                    "launch brief on 09/09/2026 and applied identically on the "
                    "maternity and neonatal page, which shares this agreement. The "
                    "brief's Suppliers section prints 51 entries and then names six "
                    "further companies as being delisted at the start of the new "
                    "framework; the Hub's crawler read all 57 as suppliers, and the "
                    "six delisted names are taken back out here. The brief's own "
                    "prose states 54 in two places and 51 are printed, so 51 is what "
                    "the list supports and 54 is what NHS Supply Chain asserts. Two "
                    "of the 51 printed entries (Elemental Healthcare Ltd and Pelvic "
                    "Relief) may be one company shown on two lines."
                ),
            },
        },
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json, all 1,397 of framework-awards.json and the 6 open
        # notices — 3,375 titles — and all 38 surviving hits were read one by one.
        #
        # THE WORD BOUNDARIES ARE LOOKAROUNDS, NOT \b, for the reason the maternity
        # rule gives: an underscore is a word character, and a real row here is
        # "0P002079 - Colposcope - Capital - Central Delivery Suite RSCH".
        #
        # NOT INCLUDED, deliberately. Each was tried, its hits were read, and it was
        # refused in the include rather than admitted and then argued with in an
        # exclusion list:
        #   bare "uter"      -> matches "Motorized Patient Couch ... for a new MRI
        #     Scanner Design" and "Procurement of a Computer Aided Facilities
        #     Management (CAFM) System". The substring is inside "Outer" and
        #     "Computer". Only uterine / uterus / intrauterine are used.
        #   bare "ovar"      -> "NOVARTIS PHARMACEUTICALS UK LTD ... RIBOCICLIB" and
        #     "Procurement of Midostaurin from Novartis UK". Only the whole words
        #     ovarian / ovary / ovaries are used.
        #   bare "IUS"       -> "Waiver for the Supply of Fresenius Spare Parts",
        #     "ExcelsiusGPS robot", "RRT Stockpile Call Off Terms - Fresenius" and
        #     "The Support of Fabius tiro anaesthesia apparatus". Only LNG-IUS is used.
        #   bare "HRT"       -> "CHRT503-2021-22 -DS/DN - Greater Manchester Pharmacy
        #     Logistics Supply Chain Service". A reference number. Refused outright;
        #     no hormone replacement row exists in this data to reach.
        #   bare "coil"      -> "Supply and Installation of Rx coils for MRI scanners"
        #     and "Purchase of replacement coil for Logiq E10S". MRI coils. The
        #     contraceptive kind is reached through contraceptive and intrauterine.
        #   bare "menstrual" -> "The Supply of Menstrual Products", bought by Leidos
        #     Supply Limited from Bunzl Cleaning & Hygiene Supplies. That is a
        #     hygiene and welfare supply contract, not gynaecology, and it is the same
        #     trap the maternity rule found in "sanitary" and "period". Only the
        #     phrase "heavy menstrual bleeding" is used, which cannot match it.
        #   bare "sling"     -> "The Supply and Delivery of High Back Slings, Dress
        #     Toileting Slings, Electric Hoists, Stand Aids and Stand Aid Slings".
        #     Patient handling. No mid-urethral sling row exists in this data, so
        #     nothing is lost and a hoist contract is kept off the page.
        #   bare "prolapse" is USED but is worth flagging for whoever reads this next:
        #     it matches nothing today, and the one foreseeable false positive is
        #     mitral valve prolapse. If a cardiology row ever appears on this panel,
        #     that is where it came from.
        #   bare "screening" -> twenty rows, and they are bowel, lung, diabetic eye,
        #     tuberculosis, newborn and genetic screening. Only the cervical forms are
        #     used, and they are qualified as cervical screening / smear / cytology
        #     because bare "cervical" is a spine and collar word.
        #   "HPV" and "papillomavirus" -> six rows. Two are the DHSC national vaccine
        #     contracts with Merck Sharpe and Dohme, three are trust HPV lines and one
        #     is a research contract on self-testing. HPV vaccination is a national
        #     immunisation programme delivered in schools to both sexes, and the page
        #     does not mention HPV once in its own text — it reaches this ground
        #     through colposcopy instead. The feed's `spec` field tags both vaccine
        #     rows gynaecology-and-womens-health; that is not a reason to publish them.
        #   "STI"            -> "Freetest.me - Online STI Screening" and "WSFT -
        #     Pathology - STI Testing". The second is already counted on pathology and
        #     laboratory medicine, and neither is a gynaecology device or service. The
        #     sexual health rows this page counts are reached through "sexual health"
        #     and "condoms" instead, and the Freetest.me row is knowingly left
        #     unmatched rather than splitting a two-row term across two pages.
        #   bare "HIV"       -> nine rows: antiretroviral therapy, HIV generic
        #     medicines, national preventative treatments, peer support and advocacy.
        #     Pharmacy and commissioned HIV services. The one genuine row, "Sexual
        #     health LARC + HIV testing", is reached through "sexual health".
        #   bare "breast"    -> twelve rows, and this page does NOT count them even
        #     though it has a section headed BREAST IMPLANTS, EXPANDERS AND EXTERNAL
        #     PROSTHESES. Plastics, burns and reconstruction already claims breast
        #     reconstruction, breast implant and breast prosthesis in its own award
        #     filter; the remainder are breast radiology, mammography trailers,
        #     Oncotype DX and breast pumps, which are radiology's, oncology's and
        #     maternity's. Publishing the same four awards under two headings tells a
        #     rep nothing new. The framework half of that section IS counted, because
        #     Surgical Implants for Men's and Women's Health is claimed above.
        #   "botulinum"      -> the three national Botulinum Toxin Type A medicines
        #     contracts (Botox, Dysport, Xeomin). They cover every indication from
        #     spasticity to bladder, and none of them is a gynaecology purchase.
        #   "Hologic"        -> five rows, of which "Roche - Hologic - Cytology" is
        #     already pathology's and two are unrelated psychological-therapies
        #     programmes that merely contain the letters. "Trustwide - Hologic -
        #     Fluent Fluid systems 2 Years Maintenance" is very probably the
        #     hysteroscopy fluid management system the page discusses under distension
        #     media, and it is STILL left unmatched: the title carries no clinical
        #     term, so counting it would mean publishing a product-knowledge claim
        #     with nothing in the record to cite. Stated here as a known gap. Only
        #     "novasure" is used, which is Hologic's endometrial ablation system and
        #     the only way to reach "2 X HOLOGIC NOVASURE RFC2010 RF CONTROLLERS".
        #   "tissue removal" -> "Tissue removal devices and accessories" names no
        #     organ and could be uterine, ENT or neurosurgical. Genuinely ambiguous on
        #     the title, so it is declined (rule 14). "Endometrial Ablation Devices and
        #     Uterine Tissue Removal Systems" is reached through endometrial.
        #   "obstetric"      -> refused outright, and this is the one term the
        #     maternity rule had to write an exclusion for. Four of its five rows are
        #     "Non-Obstetric Ultrasound" services at Surrey and Sussex and at York,
        #     which are general ultrasound capacity DEFINED BY EXCLUDING obstetrics.
        #     By not using the term at all, this rule never has to argue with them.
        #     "Obstetrics and Vinyl Pessaries" is reached through pessaries.
        #
        # NEVER READ THE FEED'S OWN `spec` FIELD AND TRUST IT. On this patch it files
        # "All Wales Womens Health Obs & Gynae Consumables" under capital-estates-watch
        # three times over, "Contraceptive Medicines" under diabetes-and-endocrinology,
        # "NP41422 Contraceptive Medicines" under pharmacy-and-medicines, "NP36722
        # Fertility Products" under continence-bladder-and-bowel, and "The Supply of
        # Menstrual Products" — a Leidos and Bunzl hygiene contract — under
        # continence-bladder-and-bowel. Meanwhile it tags the DHSC HPV vaccine
        # contracts as this speciality, which they are not.
        "include": (
            r"(?<![A-Za-z0-9])("
            r"gynaecolog\w*|gynecolog\w*|gynae\w*|"
            r"hysteroscop\w*|hysterectom\w*|colposcop\w*|"
            r"endometri\w*|uterine|uterus|intra[- ]?uterine|"
            r"fibroid\w*|myomectom\w*|adenomyosis|morcellat\w*|novasure|"
            r"pessar\w*|prolapse|urogyn\w*|vagin\w*|vulv\w*|"
            r"cervical (?:screen\w*|smear\w*|cytolog\w*)|"
            r"contracept\w*|condoms?|LNG[- ]?IUS|sexual health|"
            r"fertilit\w*|IVF|termination of pregnancy|termination services?|"
            r"ovarian|ovaries|ovary|salping\w*|oophorect\w*|"
            r"menopaus\w*|menorrhagia|heavy menstrual bleeding|polycystic ovar\w*|PCOS|"
            r"women['’]?s health|womens health|women (?:&|and) child health|"
            r"surgical mesh|transvaginal mesh|bulking agents?|"
            r"stress incontinence|stress urinary incontinence|urodynamic\w*"
            r")(?![A-Za-z0-9])"
        ),
        # NO EXCLUSION LIST, and that is a statement about the include list rather
        # than a shortcut past the reading. All 38 titles the pattern above matches
        # were read one by one and every one of them is this speciality. The loose
        # terms that WOULD have needed excluding are enumerated above and were refused
        # from the pattern instead, which is the renal rule's approach and the reason
        # "Hernia Mesh incl. Fixation" and "NP51820 Hernia Mesh" never reach this
        # panel: the include says "surgical mesh", not "mesh", so there is nothing to
        # argue with afterwards.
        "exclude": None,
        # NO CPV LIST. Not one matching notice in this data carries a CPV code
        # specific to gynaecology, so none is claimed rather than listing a family
        # that corroborates everything and therefore nothing. 33141116, the dressing
        # packs code, is the standing example of why a CPV may never admit a notice on
        # its own: it is what put "Newborn Transport Harnesses for London Ambulance"
        # on the wound care page.
        "cpv": None,
        # THE FIRST SLICED DRUG TARIFF PART ON THE HUB, and the reason build_tariff
        # grew a `tariffVmp` filter. The community pessary route really is in Part IX
        # — the page counts 257 lines across 64 virtual medicinal products from eight
        # suppliers — but those lines sit INSIDE Part IXA, whose other 56,576 lines
        # are dressings and elastic hosiery and belong to tissue viability. Claiming
        # IXA whole would have made Juzo and Sigvaris the leading suppliers on a
        # gynaecology panel. Filtering IXA to the pessary lines reproduces the page's
        # figures exactly: 257 lines, 64 products, and BBI Healthcare, GBUK
        # Healthcare, Medicare Colgate, Mediplus, Pioneer Medical Europe, R&J Medical,
        # TriOn Pharma and a Generic Supplier entry — the same eight the page names.
        # "Lactic acid 250mg pessaries" is a medicated vaginal pessary rather than a
        # prolapse device; it is a women's health product on the same route and is
        # counted.
        "tariffParts": ("IXA",),
        "tariffVmp": r"pessar",
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. There is no gynaecology "
            "category at NHS Supply Chain. Its briefs sit in six categories, none of "
            "which is a population or a speciality, so this patch is scattered across "
            "agreements owned by different category teams with different expiry "
            "dates. Six agreements are counted below and every one of them carries "
            "more than gynaecology. Maternity, Obstetrics, Gynaecology and Sexual "
            "Health Products has two lots and the obstetric half is the maternity and "
            "neonatal page's. Minimally Invasive Surgery has eight lots, of which "
            "only Lot 6, Gynaecological Endoscopy and Uterine Ablation, is named for "
            "this speciality; theatres and surgical counts Lots 1 to 5. Surgical "
            "Implants for Men's and Women's Health is half men's health, which is why "
            "companies known for penile implants and for breast implants both appear "
            "under a gynaecology Suppliers heading. NHS Supply Chain publishes no "
            "supplier-by-lot split for any of the three, so the supplier list is "
            "every company named on each agreement as a whole. "
            "THE SIX DELISTED COMPANIES ARE REMOVED, exactly as they are on the "
            "maternity and neonatal page, which shares that agreement. NHS Supply "
            "Chain's contract launch brief prints 51 current suppliers and then names "
            "Bray Group Limited, Cardiac Services UK Ltd, Durbin Plc, Medichill UK "
            "Ltd, Valley Northern and Viomedex Ltd as being delisted at the start of "
            "the new framework; the Hub's crawler read all 57 as suppliers. The brief "
            "states 54 in its own prose and prints 51, so 51 is what the published "
            "list supports and 54 is what NHS Supply Chain asserts. The upstream "
            "crawler still has the fault. "
            "THE SURGICAL MESH AGREEMENT IS COUNTED, WITH THE PAGE'S OWN WARNING "
            "ATTACHED. Its four lots are Synthetic, Biological, Specialist and "
            "Fixation Devices, and its published Clinical Information section names "
            "its clinical engagement as the British Hernia Society, the Association "
            "of Laparoscopic Surgeons of UK and Ireland, the Royal College of "
            "Surgeons, NHS consultant surgeons and key surgical mesh suppliers. No "
            "gynaecology or urogynaecology body is named, and the word prolapse "
            "appears once in the whole brief. The agreement is a route to this patch "
            "and the supplier list is real; it was not written with a urogynaecology "
            "customer in the room, and this panel says so rather than implying "
            "otherwise. Separately, transvaginal mesh repair of vaginal wall prolapse "
            "sits in NICE's research-only tier under HTG456 while mid-urethral slings "
            "for stress urinary incontinence do not, and the two are constantly "
            "conflated; the page sets out that distinction with its sources. "
            "ONE ROUTE THE PAGE NAMES IS MISSING FROM THIS PANEL BECAUSE THE HUB'S "
            "DATA DOES NOT HOLD IT. Operating Theatre and Outpatient Microscopes and "
            "Associated Accessories (2022/S 000-020537), the colposcope route, is not "
            "among the 121 framework records the Hub has crawled, so it cannot be "
            "shown here. The page carries it, including its 4 December 2026 expiry. "
            "That is a gap in this panel's source data, not a finding about the "
            "market. Neuromodulation Devices and Associated Products is also left "
            "out, because NHS Supply Chain publishes no lot breakdown for it and "
            "whether sacral neuromodulation for bladder is called off there is not "
            "verifiable from the public brief. "
            "THE AWARDS LIST COUNTS SEXUAL HEALTH, CONTRACEPTION, FERTILITY AND "
            "TERMINATION OF PREGNANCY, which the maternity and neonatal page "
            "explicitly does not, and it does NOT count breast implants, breast "
            "prostheses or breast reconstruction, which plastics, burns and "
            "reconstruction already counts. Three awards are shared with another page "
            "on purpose and each is shared because its own title says so: the "
            "surgical positioning table bought by NHS Wales is for maternity AND "
            "gynaecology procedures, the colposcope bought by University Hospitals "
            "Sussex is a gynaecology device sited on the Central Delivery Suite, and "
            "the electrosurgical devices bought for cut, coagulation and uterine "
            "ablation are a theatres purchase doing a gynaecology job. "
            "Being named on a framework is not evidence of volume, and being absent "
            "from one is not evidence of absence from the market."
        ),
    },
    # PAGE 2926. The live id was read back from the WordPress.com API on 10/09/2026:
    # slug paediatrics, title "Paediatrics (Subscribers only)". Scope, in the page's
    # own words: "General child health. Paediatric
    # product is a lot, a size band or a line inside somebody else's framework —
    # there is no children's category anywhere in NHS Supply Chain."
    #
    # THIS IS THE SECOND SPECIALITY IN THE ROLLOUT WITH NO FRAMEWORK OF ITS OWN, and
    # unlike obesity it is not because the money moves outside procurement. It is
    # because NHS Supply Chain organises by PRODUCT and paediatrics is a POPULATION.
    # All 121 framework names in frameworks.json were read on 10/09/2026 and not one
    # is a children's category; the page reached the same finding independently from
    # NHS Supply Chain's own 140 contract launch briefs. Cardiology gets a category
    # because cardiac devices are a product class. A child needs a smaller version of
    # almost everything, so there is no distinct thing to make a category out of.
    "paediatrics": {
        "label": "Paediatrics",
        # NO FRAMEWORK, DELIBERATELY, and this is the hardest refusal in the rollout
        # so far because there WERE nine candidates and every one of them is real.
        #
        # WHAT WAS REFUSED, AND WHY IT WOULD HAVE BEEN A FALSE STATEMENT. The page's
        # own research names nine NHS Supply Chain agreements that carry paediatric
        # product, eight of which are in frameworks.json and were re-read there on
        # 10/09/2026 against their references and dates. Claiming them here would have
        # produced a "Frameworks on this patch" tile reading 8 and a Suppliers tab of
        # roughly 150 companies presented as this speciality's market. Almost none of
        # them sells a paediatric product. Office and Outdoor Furniture is on the list
        # because Lot 5 is children's and play furniture; its 28 suppliers are office
        # furniture manufacturers. Wheelchairs, Specialist Seating and Related Services
        # is on it because paediatric buggies sit inside Lot 1's product list; its 31
        # suppliers are overwhelmingly adult powered and manual chair makers. A rep
        # reading that tab would take away a supplier list for a market that does not
        # exist as a market. That is exactly the ground on which the obesity rule
        # refuses to claim Arjo's four patient-handling frameworks, and it is refused
        # here for the same reason: a paediatric LOT inside an adult agreement does
        # not make the agreement, or its supplier list, paediatrics'.
        #
        # THE NINE ARE NOT LOST. They are named in the coverage note below with their
        # references, dates and the specific lot or line that is paediatric, and the
        # page's own Buying route and Framework calendar sections carry them in full
        # with the expiry dates. Naming eight agreements and the one paediatric lot in
        # each is a true and useful statement. Publishing their combined supplier list
        # under the heading "Named suppliers" is not.
        "frameworks": None,
        # DERIVED, not guessed. Every pattern below was run over all 1,972 rows of
        # tender-history.json, all 1,397 of framework-awards.json and the 6 open
        # notices — 3,375 titles — on 10/09/2026, and every surviving hit was read one
        # by one. Twelve unique titles survive and all twelve are this speciality.
        #
        # BARE "child" AND "children" ARE REFUSED, and this is the whole judgement on
        # this patch. The term matches 36 titles and roughly four of them are this
        # speciality's procurement market. The other thirty-two are children's mental
        # health (CAMHS tier 4 beds, self-harm digital therapeutics, emotional
        # wellbeing counselling, "Children and Young People Safe Space Support
        # Services"), children's social care (looked-after-children health checks,
        # child sexual abuse services, therapeutic support for children in care),
        # public health nursing ("Integrated 0-19 Healthy Child Programme",
        # "0-19 Health Visiting and School Nursing", the Defence Healthy Child
        # Program), childhood immunisation (three separate inactivated influenza
        # vaccine contracts let by DHSC), child dental services, Scotland's Childsmile
        # oral health programme, and one hospital garden ("NGH - Children's Garden",
        # Northampton General). Those are real contracts with real buyers and they are
        # a different market from the one this page serves. Admitting the word and
        # then arguing with it in an exclusion list would need a dozen patterns and
        # would still let the next council wellbeing contract through, so the word is
        # refused at the include stage and the four genuine rows are reached through
        # qualified phrases that generalise instead.
        #
        # ALSO NOT INCLUDED, deliberately, each tried and its hits read:
        #   neonat* / newborn / infant / baby -> the maternity and neonatal page's,
        #     claimed there by name. This page's pathway starts after the newborn
        #     period. "Maintenance of Infant Ventilators" (Hywel Dda) is maternity's;
        #     "Parent Infant Psychotherapy" (East Sussex) and the Brent Parent and
        #     Infant Relationship Service are local authority mental health, which
        #     maternity refuses on the same ground. The two genuinely shared rows,
        #     "Neonatal Equipment, Adult, Paediatric & Neonatal Phototherapy Devices"
        #     and "NP14220 Neonatal and Paediatric Tracheostomy Tubes", reach this
        #     panel through the word paediatric that is in both titles, so nothing is
        #     lost by leaving the neonatal vocabulary to the page that owns it.
        #   ADHD / autism / ASD -> nine hits and six are explicitly ADULT services
        #     ("Adult ADHD assessment service", "Autism/ADHD Diagnostic Assessment and
        #     Treatment – Adults", "Adult ADHD Services", "Pre- and Post-Diagnostics
        #     Service for Adults with Autism"). The children's ones are commissioned
        #     as neurodevelopmental and mental health services, not as paediatric
        #     medicine. The community paediatrics assessment backlog those services
        #     sit behind is on the page itself, with NHS England's figures.
        #   neurodevelopmental -> one hit, and it is a children's one, but the word
        #     carries no age at all and the next adult neurodevelopmental pathway
        #     notice would match it. Refused rather than admitted on a single row.
        #   PICU -> five hits and every one is a PSYCHIATRIC intensive care unit, not
        #     a paediatric one. "Mental Health PICU provision" (Pennine Care) and
        #     "Out of Area Psychiatric Intensive Care (PICU) Placement" (North
        #     Staffordshire Combined Healthcare). The abbreviation is shared and on
        #     this data it means psychiatric every time.
        #   tracheostomy (bare) -> four hits, three of them adult ENT and critical
        #     care tube contracts. The paediatric one names itself.
        #   PEWS, Martha's Rule, bronchiolitis, croup, NICU, weaning, toddler,
        #     juvenile, youth, kids, safeguarding, under-5s -> zero hits each. They
        #     are the page's clinical vocabulary, not its procurement vocabulary, and
        #     a pattern that matches nothing today is a pattern nobody has read the
        #     hits of. Left out.
        #
        # NEVER READ THE FEED'S OWN `spec` FIELD AND TRUST IT. It tags exactly one of
        # the 1,972 tender-history rows paediatrics — the Advanced Paediatric Life
        # Support courses — and misfiles the rest: "Framework Agreement for Supply of
        # Adult and Paediatric Nutrition Products" and "Supply of Children's Buggies
        # and Adult & Children's Wheelchairs" both under audiology-and-hearing,
        # "Aids for Daily Living Equipment for Children and Young People" and the
        # paediatric phototherapy award both under theatres-and-surgical, "All Wales
        # Women & Child Health Consumables" under gynaecology-and-womens-health, and
        # the neonatal and paediatric tracheostomy tubes under maternity-and-neonatal.
        "include": (
            r"(?<![A-Za-z0-9])("
            r"p[ae]ediatric\w*|"
            # Paediatric mobility and continence product, which is where the money on
            # this patch is and which the adult agreements carry as named lots. Every
            # one of these is a phrase, never the bare word: "children's wheelchair"
            # cannot be a council wellbeing contract, "children" on its own can.
            r"child(?:ren)?'?s? (?:bugg(?:y|ies)|wheelchair\w*|walking (?:aid|frame)\w*|"
            r"crutch\w*|seating|nappi\w*|pull[- ]ups?)|"
            # "child health" is the page's own name for the patch and, unlike "child",
            # it does not match the Healthy Child Programme contracts, which are
            # written "Healthy Child Programme" and carry no "child health" anywhere.
            r"child health|child(?:ren)?'?s? community health|"
            r"(?:equipment|aids?|consumables?|devices?|appliances?|products?) for children"
            r")(?![A-Za-z0-9])"
        ),
        # NO EXCLUSION LIST, and it is None rather than a pattern that happens to
        # match nothing. All twelve surviving titles were read one by one on
        # 10/09/2026 and not one of them is another speciality's:
        #   Specialised Paediatric Whole-Body MRI Surveillance for Cancer Predisposing
        #     Syndromes (NHS England, 17/08/2026)
        #   Paediatric Videoflouroscopy Service for CLEFT patients (Nottingham
        #     University Hospitals, 14/08/2026)
        #   Paediatric Occupational Therapy for Special Schools (North Tyneside
        #     Borough Council, 12/08/2026)
        #   Childrens Community Health Services (NHS Bristol, North Somerset and South
        #     Gloucestershire ICB, 10/08/2026)
        #   Framework Agreement for Supply of Adult and Paediatric Nutrition Products
        #     (East Midlands Pharmacy Collaborative, 13/07/2026)
        #   Manuals / Registrations for Advanced Paediatric Life Support Courses
        #     (Southern Health and Social Care Trust, 31/01/2024)
        #   Aids for Daily Living Equipment for Children and Young People Framework
        #     Agreement (The Highland Council, 17/01/2024)
        #   All Wales Women & Child Health Consumables (NHS Wales Shared Services
        #     Partnership, 10/01/2023)
        #   Supply of Children's Buggies and Adult & Children's Wheelchairs (NHS
        #     National Services Scotland, 27/09/2022)
        #   Parenteral Nutrition for Adults and Paediatrics (NHS National Services
        #     Scotland, 05/11/2021)
        #   Neonatal Equipment, Adult, Paediatric & Neonatal Phototherapy Devices and
        #     Associated Accessories & Services (NHS Supply Chain, 10/09/2021)
        #   NP14220 Neonatal and Paediatric Tracheostomy Tubes (NHS National Services
        #     Scotland, 05/02/2021)
        # Four of those are shared with another page on purpose and each is shared
        # because its own title says so: the two nutrition contracts are adult AND
        # paediatric and are nutrition and dietetics' too, the phototherapy award is
        # the predecessor of the agreement maternity and neonatal claims, and the
        # tracheostomy tubes are neonatal AND paediatric.
        "exclude": None,
        # NO CPV FAMILY IS CLAIMED. The three award-feed rows on this patch carry
        # 85100000 (health services), 85000000 (health and social work services) and
        # 85323000 (community health services). Those are the whole of healthcare and
        # they corroborate every speciality equally, which is not corroboration.
        # There is no paediatric CPV code in the classification at all: CPV describes
        # what is bought, not who it is bought for, which is the same structural fact
        # that leaves this speciality without a Supply Chain category.
        "cpv": None,
        # THE DRUG TARIFF IS A SLICE OF THREE PARTS, NEVER THE PARTS WHOLE, and the
        # slicing rule is the page's own, reproduced here exactly so the panel and the
        # page cannot drift apart. Part IX carries 66,400 lines for September 2026.
        # Searching the virtual AND actual medicinal product names of every line for
        # paediatric, child, infant or junior returns 473 — 0.71% — of which 353 are
        # in IXA, 111 in IXC (stoma) and 9 in IXB (incontinence appliances). Those are
        # the page's published figures and this filter reproduces all four exactly.
        #
        # THE LIMIT OF THE RULE IS PUBLISHED WITH IT, because it is a real one: a
        # paediatric product named without one of those four words — a small-size
        # adult line used in children — is invisible to it. Understating the count is
        # the safe direction to be wrong in and it is stated rather than hidden.
        #
        # WHY THE ACTUAL MEDICINAL PRODUCT NAME IS SEARCHED TOO, which no other rule
        # does: the brand name is where the paediatric marker often lives. Sanofi's
        # JuniorSTAR half-unit insulin pen carries nothing paediatric in its virtual
        # product description ("Hypodermic insulin injection pen reusable for 3ml
        # cartridge 0.5 unit dial up") and is a children's dosing device. Searching
        # the virtual name alone returns 258 lines, all of them IXA, and loses Part
        # IXC's 111 paediatric stoma lines entirely.
        "tariffParts": ("IXA", "IXB", "IXC"),
        "tariffVmp": r"p[ae]ediatric|child|infant|junior",
        "tariffFields": ("vmp", "amp"),
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. There is no paediatric "
            "category at NHS Supply Chain and no paediatric framework, so this panel "
            "publishes no framework list and no supplier list. That is a finding "
            "about how children's product is bought, not a gap in the data: NHS "
            "Supply Chain organises its 140 agreements by product — Medical and "
            "Surgical Consumables, Rehabilitation and Community, Diagnostic Equipment "
            "and Services, Medical Technology, Facilities and Office Solutions, Food "
            "— and none of those is a population. Paediatric product is a lot, a size "
            "band or a line inside an adult agreement. "
            "NINE AGREEMENTS CARRY IT, AND NAMING THEM IS THE USEFUL THING THIS PANEL "
            "CAN DO. Eight are in the Hub's framework record and were re-read there "
            "on 10/09/2026: 2022/S 000-033396, the walking aids and simple aids for "
            "daily living agreement, 1 November 2023 to 31 October 2027, 31 "
            "suppliers, which is the only one of the nine giving paediatric product "
            "numbered lots of its own (Lot 23 crutches, Lot 28 posture walkers, Lot "
            "30 walking frames); Wheelchairs, Specialist Seating and Related Services "
            "(2024/S 000-039981), 9 June 2025 to 8 June 2027, 31 suppliers, with "
            "paediatric buggies inside Lot 1's product list rather than as a lot; "
            "Disposable and Washable Continence Care (2026/S 000-031173), 24 August "
            "2026 to 23 August 2028, 12 suppliers, Lot 2 paediatric nappies and pull "
            "ups and Lot 3 paediatric body worn washables; Anaesthesia Machines, "
            "Ventilators, Neonatal Equipment and Phototherapy Systems (2026/S "
            "000-008108), 2 March 2026 to 28 February 2029, 25 suppliers, Lot 4 adult "
            "and paediatric phototherapy; Infant Feeding and Accessories (2023/S "
            "000-011743), 29 February 2024 to 28 February 2028, 18 suppliers, the "
            "only one of the 140 agreements written for children as a population and "
            "it is food and feeding equipment rather than clinical device; Polymer "
            "Aprons (2023/S 000-014652), 9 October 2023 to 8 October 2027, 8 "
            "suppliers, one paediatric apron beyond the standard range; Polymer "
            "Products (2022/S 171-486016), from 31 October 2022 with no end date "
            "published, 5 suppliers, child-size items returned to catalogue; and "
            "Office and Outdoor Furniture (2025/S 000-046095), 25 November 2025 to 24 "
            "November 2028, 28 suppliers, Lot 5 children's and play furniture, which "
            "is not clinical and is here because NICE NG204 1.8.1 requires an "
            "environment appropriate to a child's age and developmental stage. The "
            "ninth, Peripheral IV Site Monitoring Device (2025/S 000-043122, 16 "
            "February 2026 to 15 February 2027), is a one-year agreement for a single "
            "named product and NHS Supply Chain publishes no supplier list for it, so "
            "the Hub's framework record holds it unparsed. "
            "WHY THOSE EIGHT ARE NOT CLAIMED AS THIS SPECIALITY'S FRAMEWORKS. Their "
            "combined supplier lists run to roughly 150 companies, the great majority "
            "of which sell no paediatric product at all — Office and Outdoor "
            "Furniture's 28 are office furniture manufacturers, and the wheelchair "
            "agreement's 31 are overwhelmingly adult chair makers. Published under "
            "the heading Named suppliers they would describe a paediatric market that "
            "does not exist. A paediatric lot inside an adult agreement does not make "
            "the agreement, or its supplier list, this speciality's, and each of the "
            "eight is counted on the page whose product class it is. "
            "WHAT THIS PANEL DOES SHOW: the award trail for contracts whose own title "
            "says paediatric or names children's equipment, and the paediatric slice "
            "of the Drug Tariff. Children's mental health, children's social care, "
            "school nursing and health visiting, childhood immunisation and child "
            "dental services are deliberately not counted here. They are commissioned "
            "by different buyers on different notices and they would fill this tab "
            "with contracts a rep on this patch cannot sell into. Being absent from "
            "this panel is not being absent from this market. The page's Buying "
            "route, Framework calendar and Deep dive sections carry the full picture "
            "with their sources and their expiry dates."
        ),
    },
    # PAGE 2803. Scope, in the page's own tagline: "Stones, scopes, stents and lasers,
    # the prostate and bladder cancer pathways, and the catheter that goes home with the
    # patient." Urology is the rare speciality with an NHS Supply Chain agreement carrying
    # its own name, and that agreement goes to tender on 11/09/2026.
    "urology": {
        "label": "Urology",
        # NINE AGREEMENTS. Every one is named on the page's own Buying route and
        # framework tables, and all nine were matched back against the 121 names in
        # frameworks.json on 10/09/2026:
        #   Urology and Bowel Management (2023/S 000-011173, 57 suppliers, ends
        #     20/02/2027) — the only agreement in the whole NHSSC portfolio named after
        #     this speciality. Lot 1 internal urinary catheters, Lot 2 external
        #     catheters and sheaths, Lot 3 urine drainage bags, Lot 4 urine flow
        #     monitoring, Lot 6 bladder washout, Lot 15 urodynamics and surgery, Lot 18
        #     urethral bulking agents. Shared with continence, bladder and bowel, which
        #     counts the bowel and containment half. Both pages are right: the
        #     agreement really does carry both, exactly as Pressure Area Care is shared
        #     between tissue viability and patient moving and handling.
        #   Endoscopy, Endourology and Oncology Ablation Consumables and Associated
        #     Products (2024/S 000-029975, 58 suppliers) — endourology is in the
        #     agreement's own name. Not claimed by any other page today.
        #   Male Intra-Urethral Catheter with Magnet Control (2026/S 000-013783, one
        #     supplier, Ingenion Medical Ltd).
        #   Lithotripsy and Associated Options and Related Services (3 suppliers) —
        #     NHSSC's own brief: lithotripsy is "performed by Urologists".
        #   Bladder Scanners and Associated Options and Related Services (11) —
        #     NHSSC's own brief: "Used by Urology professionals and Continence Nurse
        #     Specialists". The continence rule refused it as a Diagnostic Equipment
        #     capital route outside that page's stated scope, and the gynaecology rule
        #     refused it too, so claiming it here creates no contradiction.
        #   Brachytherapy Seeds and Associated Accessories (2) — NHSSC's own brief:
        #     the seeds "implant low dose rate radiation to the prostate".
        #   Rigid Endoscopy and Associated Options and Related Services (18) — the
        #     brief's product categories include Urology Scopes. Shared with
        #     gynaecology, whose rule counts the hysteroscope half; that rule's comment
        #     saying it was unclaimed elsewhere is corrected in the same change.
        #   Flexible Endoscopes and Associated Options and Related Services (5) — the
        #     brief's product categories include cystoscopes and ureteroscopes. STATED
        #     LIMIT: the same brief's own summary describes the framework as
        #     gastrointestinal, so it is a shared route rather than a urology one, and
        #     its five suppliers are endoscope manufacturers, not urology houses.
        #   Surgical Implants for Men's and Women's Health (2025/S 000-025202, 6) —
        #     Lot 1 names testicular implants and penile implants. Shared with
        #     gynaecology, which counts the urogynaecology half.
        #
        # NOT CLAIMED, and each was checked against the 121 names rather than assumed:
        #   Neuromodulation Devices and Associated Products -> already claimed by
        #     neurology and neurosurgery, and that is the right home. The page carries
        #     it on clinical grounds because Axonics Modulation Technologies UK Limited
        #     is on its published supplier list and sacral neuromodulation for
        #     overactive bladder is called off against it, and the page says plainly
        #     that the brief contains no urological word at all and describes itself as
        #     "strategic pain management solutions". NHSSC publishes no lot breakdown,
        #     so claiming the agreement here would put 23 pain-management suppliers
        #     under a urology Suppliers heading on the strength of one supplier name.
        #     Refused for the panel on the same reasoning the gynaecology rule refused
        #     it (rule 14c). The page keeps its own sourced row and its own caveat.
        #   Electrosurgical Consumables and Related Accessories -> theatres and
        #     surgical's, and claimed there. Its brief lists "urological" as one of
        #     eleven specialities electrosurgery is used in. A consumable shared with
        #     ten other specialities is theatres', not this page's.
        #   Robotic Medical Equipment and Associated Accessories -> theatres and
        #     surgical's, and claimed there. Lot 1 is minimally invasive generally and
        #     names prostate removal alongside hysterectomy, thyroid and gastric
        #     bypass. No lot is named for urology, which is the test applied throughout.
        #   Disposable and Washable Continence Care -> continence, bladder and bowel's,
        #     and claimed there. The page itself calls it "containment rather than
        #     urology proper".
        #   Central Venous Catheters and Associated Products -> vascular access and IV
        #     therapy's. A central venous catheter is not a urinary one.
        #   Ear, Nose and Throat (ENT) Endoscopes -> the ENT page's, which is why the
        #     pattern says "flexible endoscopes" and "rigid endoscopy" by name and
        #     never bare "endoscop".
        "frameworks": (
            r"\b(urology and bowel|endourology|intra-urethral|lithotripsy|"
            r"bladder scanners|brachytherapy seeds|rigid endoscopy|flexible endoscopes|"
            r"surgical implants for men)\b"
        ),
        # DERIVED, not guessed. The pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,397 of framework-awards.json — 3,369 titles —
        # and all 29 surviving hits were read one by one on 10/09/2026. Every one of
        # them is this patch: urology consumables and products, endourology disposables,
        # bladder scanners, a lithotriptor and two lithotripter service contracts, three
        # holmium laser service and fibre contracts and a GreenLight laser, urodynamics,
        # prostatic ablation, two transperineal prostate biopsy contracts, Memokath
        # ureteric stents, urinary catheters and drainage bags, urine meters, a urology
        # robot maintenance contract, a cystoscopy surveillance service, urology
        # insourcing and a urology bootcamp.
        #
        # NOT INCLUDED, deliberately, and every one was run over the 3,369 titles and
        # its hits read before it was dropped:
        #   bare "endoscop"   -> 36 hits and almost none of them urology: capsule
        #     endoscopy, bowel screening insourcing, nasendoscopes, endoscope washer
        #     disinfectors, endoscopic vessel harvesting, hysteroscopy scopes. The
        #     urology ground is carried by "endourolog" and "cystoscop", which is how
        #     the real rows are actually titled.
        #   bare "brachytherap" -> its only hit is "NHS Grampian HDR Brachytherapy
        #     Afterloader". A high dose rate afterloader treats cervical, endometrial
        #     and breast disease as well as prostate, and the title cannot tell you
        #     which. "brachytherapy seeds" is used instead — the low dose rate prostate
        #     product NHSSC's own framework is named after — and it costs the panel
        #     nothing today because that row is not this page's.
        #   bare "bladder"    -> refused because a gall bladder is not a urinary one.
        #     The qualified forms below catch all three real rows (two bladder scanner
        #     purchases and a CUBESCAN) without the bare word ever being able to carry
        #     a hepatobiliary contract in.
        #   bare "urinary"    -> three of its five hits are "Antibiotic and Genito
        #     Urinary Medicines", which is the pharmacy patch. "urinary catheter" is
        #     used and both real rows still match.
        #   bare "catheter" and bare "catheterisation" -> refused. The continence rule
        #     records what bare "catheter" drags in (cardiac ablation, central venous,
        #     renal fistula and HRIM manometry catheters) and "catheterisation"'s only
        #     hit here is "Managed Service for Catheterisation Lab, Cardio Thoracic
        #     Centre and Vascular", a cardiac cath lab. Refusing them in the include
        #     means neither can reach a member even if the exclusion list is edited
        #     later.
        #   bare "urine"      -> one of its two hits is "Evacuated Blood Collection
        #     Systems and Urine Collection Systems", pathology specimen tubes. "urine
        #     meter" is used and the real row still matches.
        #   bare "stent"      -> nine hits and eight are cardiac or aortic. The one
        #     urology row, Memokath stents for BCH Urology service, matches on
        #     "Urology" anyway. Qualified ureteric and prostatic forms are kept.
        #   bare "stone"      -> refused. Maidstone, Basingstoke and every other place
        #     name containing it would match. The qualified stone forms are kept.
        #   bare "orchid"     -> refused. An orchid is a flower and an Orchid Ward is a
        #     ward. "orchidectom" and "orchidopex" are kept.
        #   bare "laser" and "optical laser fibre" -> refused, 16 hits and most are
        #     ophthalmology, dermatology, ENT and burns. Holmium and thulium are the
        #     urology lasers by name and are used instead; "Optical Laser Fibre
        #     Consumables for CyberHo 100 Holmium Laser System" still matches on
        #     "Holmium".
        #   bare "ablation"   -> 10 hits, mostly endometrial, radiofrequency and
        #     spinal. "Prostatic Ablation Devices" matches on "prostat".
        "include": (
            r"\b(urolog\w*|endourolog\w*|prostat\w*|transurethral|turp|turbt|holep|"
            r"cystoscop\w*|ureterosc\w*|nephroscop\w*|resectoscop\w*|"
            r"urodynam\w*|uroflow\w*|lithotrip\w*|eswl|pcnl|"
            r"ureter\w*|urethr\w*|nephrostom\w*|nephrolithotom\w*|"
            r"penile|testicular|orchidectom\w*|orchidopex\w*|vasectomy|varicocele|"
            r"circumcision|erectile dysfunction|"
            r"holmium|thulium|green ?light laser|brachytherapy seeds?|"
            r"urinary catheters?|urostom\w*|"
            r"bladder scanner\w*|bladder cancer|bladder tumou?r|overactive bladder|"
            r"neurogenic bladder|bladder washout|bladder irrigation|"
            r"bladder instillation|urine meters?|urine flow)\b"
        ),
        # ONE PATTERN, and it is here because a real row matched `include`, was read,
        # and was rejected:
        #   intravascular -> "Intravascular Lithotripsy Equipment and Consumables -
        #                    4307395", Procurement and Logistics Service, awarded to
        #                    SHOCKWAVE MEDICAL INC. Intravascular lithotripsy breaks
        #                    calcified plaque in a coronary or peripheral artery. It is
        #                    the same physics and the opposite patch, and it belongs to
        #                    cardiology and vascular surgery. It is the only false
        #                    positive the include list produced.
        "exclude": r"\b(intravascular)\b",
        # CPV 33125000 is "Urology, exploration devices", read on the notice itself at
        # find-tender.service.gov.uk/Notice/078238-2026 on 10/09/2026. Exactly one
        # notice in this feed carries it, "Maintenance of Continuous Renal Replacement
        # Therapy and Urology Equipment", and that notice title-matches anyway — which
        # is the point. The code corroborates; it never admits.
        "cpv": ("33125",),
        # THE PART IS NOT THE SPECIALITY, so all three parts are sliced, never claimed
        # whole. Part IXA is 56,833 lines of which 1,730 are urinary catheters and
        # catheter care: Nelaton, Foley, dilatation, reusable and suprapubic catheters,
        # catheterisation packs, catheter maintenance solutions, retaining straps,
        # safety valves and securement devices. The other 55,000 are dressings and
        # elastic hosiery and are the tissue viability page's. Part IXB is 1,242 lines
        # of incontinence appliances, of which 595 are the catheter drainage range —
        # incontinence sheaths, leg bags and catheter valves — and the rest are
        # absorbent pads and garments, which are containment and are the continence
        # page's. Part IXC is 8,218 stoma lines of which 783 are urostomy bags, the
        # urinary diversion range; colostomy and ileostomy are colorectal.
        #
        # ONE FALSE POSITIVE WAS FOUND AND DESIGNED OUT RATHER THAN EXCLUDED. Bare
        # "catheter" over Part IXA returns 85 virtual medicinal products and 84 of them
        # are urinary; the eighty-fifth is "Indwelling pleural drainage systems
        # catheter", which is respiratory. build_tariff has no exclusion mechanism, so
        # the pattern names the catheter families instead of the bare word and that row
        # cannot reach the panel. The selection is 3,108 lines across 92 virtual
        # medicinal products, and every one of the 92 was read.
        #
        # STATED LIMIT: the IXB and IXC slices overlap the continence, bladder and
        # bowel page, which claims those parts whole. That is deliberate. A leg bag is
        # bought by the same nurse for the same catheter, and both pages showing it is
        # honest where one page hiding it would not be.
        "tariffParts": ("IXA", "IXB", "IXC"),
        "tariffVmp": (
            r"\b(nelaton|foley|dilatation catheter|reusable catheter|"
            r"catheterisation packs?|"
            r"catheter (?:disposable|retaining|safety|securement|maintenance|valves?)|"
            r"urinar\w*|urostom\w*|uridome|suprapubic|penile sheaths?|"
            r"incontinence sheaths?|leg bags?|night bags?|"
            r"bladder (?:infusion|irrigat\w*|washout)|urine (?:meters?|bags?))\b"
        ),
        "coverageNote": (
            "COVERAGE LIMITS, STATED RATHER THAN HIDDEN. Two of the nine agreements "
            "above, Rigid Endoscopy and Flexible Endoscopes, are capital routes shared "
            "with other specialities, and their suppliers are endoscope manufacturers "
            "rather than urology houses; three more, Urology and Bowel Management, "
            "Surgical Implants for Men's and Women's Health and Brachytherapy Seeds, "
            "are shared with continence, gynaecology and oncology. Being named on a "
            "framework is not evidence of volume on this patch, and being absent from "
            "one is not evidence of absence from the market. One agreement the page "
            "carries is missing here for a data reason rather than a judgement: "
            "Maintenance, Repair and Calibration of Medical Equipment, which names "
            "urodynamics and lithotripsy equipment among the estates it maintains, is "
            "not one of the 121 framework names the Hub's crawler holds, so it cannot "
            "be claimed. Five of the nine agreements share one procurement reference, "
            "2021/S 000-007768, and all five end on 31 March 2028 — that reference "
            "wraps NHS Supply Chain's whole diagnostic capital portfolio and 22 of its "
            "140 briefs carry it, so its expiry is not a urology event. Finally, the "
            "larger half of the catheter economy is bought in the community on "
            "prescription through NHSBSA Drug Tariff Part IX and the dispensing "
            "appliance contractors, a route with no NHS Supply Chain framework page at "
            "all; the Drug Tariff summary is where it appears."
        ),
    },

    # PAGE 2843. Scope, taken from the page itself rather than from the word
    # "respiratory": airways disease and inhaled therapy, oxygen, aerosol and
    # nebuliser therapy, lung function and diagnostics, non-invasive ventilation,
    # CPAP and sleep, airway management and tracheostomy, and ventilators. The page
    # carries NO thoracic oncology section, NO tuberculosis service section and NO
    # cystic fibrosis section, and the refusals below follow that scope rather than
    # widening past it.
    "respiratory": {
        "label": "Respiratory",
        # FOUR AGREEMENTS, and the number is the page's own. Its Buying route, its
        # framework calendar, its Deep dive and its Verification table all name the
        # same four, each read on its NHS Supply Chain contract launch brief on
        # 07/09/2026, and the page says in terms that "four frameworks cover this
        # patch". All four were matched back against the 121 names in frameworks.json
        # on 10/09/2026 and the pattern below returns exactly those four:
        #   Respiratory Solutions (37 suppliers across 6 product lots, ends
        #     15/06/2027) — the framework the patch is named after. Lot 1 oxygen
        #     therapy, Lot 2 aerosol therapy, Lot 3 respiratory therapy including
        #     spirometers, peak flow meters, FeNO analysers, cough assist and
        #     compressor nebulisers, Lot 5 the diagnostics lot NHS Supply Chain says
        #     was developed with respiratory specialists, Lot 6 consumables. The
        #     nearest expiry on the patch, and it has already taken a 24-month and an
        #     11-month extension.
        #   Non Invasive Ventilation, Sleep Therapy, CPAP and Sleep Monitoring
        #     Diagnostics (2025/S 000-023362, 28 suppliers, one lot, ends 28/09/2027).
        #   Airway Management Products and Associated Equipment (2023/S 000-005729,
        #     54 suppliers, ends 21/07/2028). SHARED with theatres and surgical, which
        #     claims it too, and rightly: the page's own words are that airway
        #     management is "largely a theatre and critical care conversation, but the
        #     same accounts hold the ventilated respiratory patients". It is also
        #     categorised under Medical and Surgical Consumables, so a search of NHS
        #     Supply Chain for "respiratory" does not find it — which is exactly why
        #     the CBU category field is never the key here.
        #   Anaesthesia Machines, Ventilators, Neonatal Equipment and Phototherapy
        #     Systems, Related Accessories and Services (2026/S 000-008108, 25
        #     suppliers, ends 28/02/2029). SHARED with theatres and surgical and with
        #     maternity and neonatal, which claim the anaesthesia and the neonatal
        #     halves. This page claims it for the ventilator half only, which is the
        #     half the page names.
        #
        # NOT CLAIMED, each checked against the 121 names rather than assumed:
        #   Pulse Oximetry, Capnography and Related Monitoring Technologies (26
        #     suppliers) -> claimed by nobody, and still refused. It is a patient
        #     monitoring framework, capnography is an anaesthesia and critical care
        #     measurement, and the page names four frameworks and not five. Claiming a
        #     fifth here would put the panel and the page in contradiction in front of
        #     the same member (root rule 18). Overnight pulse oximetry does appear on
        #     the page, as the sleep screening test and as an ARTP competency, and the
        #     include list reaches those rows through "sleep monitoring" and "sleep
        #     diagnostics" instead.
        #   Cardiac and Pulmonary Diagnostics and Exercise (Stress) Testing Solutions
        #     -> cardiology and cardiac surgery's, and claimed there. Its award row
        #     does reach this panel on the title, because cardiopulmonary exercise
        #     testing is lung function and the page names CPET, but the framework
        #     itself stays where it is.
        #   Enteral Feeding, Patient Monitoring Equipment, Electrodes and the medical
        #     gas routes -> not this patch. Piped and cylinder medical gases are an
        #     estates and pharmacy category covering nitrous oxide, medical air and
        #     surgical CO2 as well as oxygen.
        "frameworks": (
            r"\b(respiratory solutions|non invasive ventilation|airway management|"
            r"anaesthesia machines)\b"
        ),
        # DERIVED, not guessed. The pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,397 of framework-awards.json — 3,369 titles —
        # on 10/09/2026, and all 80 surviving titles were read one by one. Every one
        # is this patch: the four NHSSC agreements themselves, respiratory therapy
        # services and consumables, three regional Acute Respiratory Infection
        # services, FeNO and asthma diagnostic hubs, lung function and pulmonary
        # function testing equipment and filters, Ellipta inhalers, nebulised
        # amikacin, three cystic fibrosis modulator contracts, oxygen therapy,
        # manifolds, liquid oxygen and pandemic oxygen masks, inhaled nitric oxide,
        # CPAP and ASV equipment and consumables, two sleep apnoea services and a
        # sleep study equipment purchase, tracheostomy tubes, holders and closed
        # tracheal suction, breathing systems and circuits, video laryngoscopes and
        # intubating devices, a robotic bronchoscopy system, respiratory metagenomic
        # sequencing, and sixteen rows of the 2020-21 Ventilator Challenge and Rapid
        # Manufacture Ventilator System programme.
        #
        # NOT INCLUDED, deliberately. Every term below was run over the same 3,369
        # titles and its hits were read before it was dropped, which is why none of
        # them needs an exclusion later:
        #   bare "anaesthe*"  -> 11 hits and only the ventilator ones are this patch:
        #     sevoflurane and isoflurane, inhalation anaesthetics and vaporisers,
        #     anaesthetic monitors, anaesthetic management software, anaesthetics
        #     insourcing, an analgesics and anaesthetics medicines contract, and three
        #     anaesthetic machine purchases. Anaesthesia is theatres and surgical's
        #     patch and is claimed there. "breathing circuit" and "breathing system"
        #     are used instead and still catch the two circuit contracts.
        #   bare "ventilation" -> refused because a building has it too: "Provision of
        #     Ventilation and Other Remediation Works" and "Ventilation Verification"
        #     are HVAC contracts. "ventilator" plus the qualified clinical forms
        #     (non-invasive, mechanical, home, nasal, neonatal, infant, patient, jet,
        #     transport, critical care) catch every real row and neither HVAC contract
        #     can reach a member even if the exclusion list is edited later.
        #   bare "sleep"      -> its hits include "Universal Sleep Support Model" from
        #     an ICB, which is an insomnia and sleep-behaviour service, and two rough
        #     sleeping drug and alcohol contracts. The qualified forms below catch all
        #     five real sleep rows without the bare word ever being able to carry a
        #     homelessness contract onto a respiratory page.
        #   bare "lung"       -> three of its six hits are heart-lung machines and
        #     perfusion systems, which are cardiac surgery. "lung function" is used.
        #   "lung cancer"     -> refused, and this is a scope decision rather than a
        #     data one. "Lung Cancer Screening - DAP C" and "Replacement Ultrasound
        #     Machine for Lung Cancer Diagnostic" are real and are respiratory-adjacent,
        #     but the page carries no thoracic oncology or screening section and
        #     Targeted Lung Health Checks are a population radiology programme.
        #     "bronchoscop" IS included, because bronchoscopy is the respiratory
        #     physician's own instrument whatever the indication.
        #   bare "pulmon*"    -> "Cardiopulmonary Bypass Oxygenators with Customised
        #     Tubing Pack" is perfusion. The pattern says "pulmonary function",
        #     "pulmonary diagnostic" and "pulmonary rehabilitation", and the word
        #     boundary means "Cardiopulmonary" cannot match any of them.
        #   "oximet" and "capnograph" -> refused for the same reason the Pulse
        #     Oximetry framework is not claimed above. Their three hits are monitoring
        #     consumables, sensors and the framework itself.
        #   bare "suction"    -> four hits and three are general theatre and ward
        #     suction sold alongside wound drainage and autologous blood systems.
        #     "tracheal" catches the one real row, Sterile Closed Tracheal Suction.
        #   "blood gas"       -> two hits, both pathology point-of-care managed
        #     services, and claimed by pathology and laboratory medicine. Blood gas
        #     sampling appears on this page only as an ARTP competency certificate.
        #   "smoking cessation" and "tobacco" -> five hits, all local authority and
        #     ICB public health commissioning, including a workplace scheme and a
        #     behaviour-change advertising campaign. The page carries smoking only as
        #     NICE NG115's long-term oxygen exclusion and as a calendar date.
        #   "tuberculosis"    -> two hits, an ICB latent TB screening programme and a
        #     "Global Tuberculosis Screening Service" which is the pre-entry
        #     immigration screening market. TB reaches the page as a BTS/BIA/NICE
        #     guideline news item, not as a procurement route.
        #   "medical gas"     -> two hits, cylinder supply and an estates gas contract.
        #     The oxygen-specific rows (BOC Oxygen Manifolds, Medical Liquid Oxygen)
        #     match on "oxygen" and the generic gas category stays out.
        #   "resuscitat", "vaporis", "humidificat" and bare "thoracic" -> refused.
        #     Their hits are baby warmers, Resuscitation Council course manuals,
        #     sevoflurane vaporisers, and a cardiac catheterisation lab at a Cardio
        #     Thoracic Centre. "humidificat" has no hit at all and could only ever
        #     arrive as plant machinery.
        "include": (
            r"\b(respirator\w*|"
            r"pulmonary function\w*|pulmonary diagnostic\w*|pulmonary rehabilitation|"
            r"lung function|lung volume|"
            r"asthma|copd|chronic obstructive pulmonary|"
            r"bronchoscop\w*|bronchodilat\w*|bronchiectasis|"
            r"spirometr\w*|spirometer\w*|peak flow|"
            r"feno|fractional exhaled nitric oxide|nitric oxide|"
            r"oxygen|nebulis\w*|nebuliz\w*|inhaler\w*|"
            r"ventilator\w*|"
            r"(?:non-?invasive|mechanical|home|nasal|neonatal|infant|patient|jet|"
            r"transport|critical care) ventilation|"
            r"cpap|bipap|continuous positive airway pressure|"
            r"sleep (?:apnoea|apnea|therapy|monitoring|diagnostic\w*|stud\w*)|"
            r"apnoea|apnea|polysomnograph\w*|"
            r"airway\w*|intubat\w*|laryngoscop\w*|"
            r"tracheostom\w*|tracheotom\w*|tracheal|endotracheal|"
            r"breathing circuit\w*|breathing system\w*|"
            r"cystic fibrosis|"
            r"pleural|chest drain\w*|pneumothorax|pneumonia|"
            r"cough assist|high[- ]flow nasal)\b"
        ),
        # THREE PATTERNS, and each is here because a real row matched `include`, was
        # read, and was rejected:
        #   hyperbaric      -> "Most Suitable Provider: Hyperbaric Oxygen Therapy
        #                      (HBOT) Services for all ages". HBOT treats decompression
        #                      illness, radiation injury and non-healing wounds. It is
        #                      oxygen and it is not respiratory medicine.
        #   epoc device     -> "WSFT - Pathology - COPD - 6 EPOC devices service
        #                      cover". The epoc is a blood gas point-of-care analyser
        #                      and the title says Pathology. Whether "COPD" there names
        #                      a pathway or a contract code cannot be told from the
        #                      title, so it is refused rather than guessed at (rule 2).
        #   newborn screening -> "Procurement of Test Kits for Newborn Screening of
        #                      Cystic Fibrosis (CF), Congenital Hypothyroidism (CHT)".
        #                      A newborn bloodspot card screens for nine conditions and
        #                      is the neonatal screening programme's, not respiratory's.
        "exclude": r"\b(hyperbaric|epoc devices?|newborn screening)\b",
        # CPV 33157 is the "Gas therapy and respiratory devices" family — 33157000 the
        # family itself, 33157100 medical gas masks, 33157400 medical breathing
        # devices. Two rows in this panel carry it (Airway Management Products, and the
        # CPAP and ASV consumables market engagement). Exactly one other notice in the
        # whole feed carries a 33157 code and it is instructive: "Diving Life Support
        # (DLS) In-Service Support (ISS)" is filed under 33157500, hyperbaric chambers,
        # alongside diving gear and compressor codes. It cannot reach this panel,
        # because the title gate refuses it. That is the rule working: the CPV
        # corroborates a title match, it never admits on its own.
        "cpv": ("33157",),
        # PART IXA, SLICED, NEVER CLAIMED WHOLE. Part IXA is 56,833 lines and 56,225
        # of them are the dressing and elastic hosiery range that belongs to tissue
        # viability and wound care. Inside it sit two genuinely respiratory
        # reimbursement ranges, 608 lines across 7 virtual medicinal products, and
        # every one of the 7 was read: Tracheostomy breathing aids (483 lines), the
        # Tracheostomy and laryngectomy protectors (58), Tracheostomy tube holders
        # (24), Tracheostomy cleaning devices (17), and the peak flow meters —
        # standard range (15), low range (8) and replacement plastic mouthpieces (3).
        # 23 suppliers, led by Severn Healthcare Technologies and Atos Medical, and
        # reimbursement from £0.38 to £174.18.
        #
        # ONE FAMILY WAS FOUND AND DESIGNED OUT RATHER THAN EXCLUDED. Bare
        # "tracheostomy" over Part IXA also returns 11 tracheostomy dressing lines and
        # one fenestrated polyurethane foam dressing. Those are dressings, which is
        # tissue viability's product and tissue viability's part; build_tariff has no
        # exclusion mechanism, so the pattern names the four tracheostomy care
        # families rather than the bare word and no dressing line can reach the panel.
        #
        # STATED LIMIT, because it is the larger half of the money. The community
        # respiratory economy is overwhelmingly Part VIII drugs on FP10 — £1.219bn net
        # ingredient cost and 77.6m items in England in 2024/25, the fourth largest BNF
        # chapter — and Part IX carries none of it. Inhalers, and therefore Chiesi's
        # 35.8%, GSK's 18.5% and AstraZeneca's 9.5% community share, are not in this
        # summary and must never be read out of it. The page's own community section
        # is where that market lives.
        "tariffParts": ("IXA",),
        "tariffVmp": (
            r"peak flow meter|"
            r"tracheostomy (?:breathing aid|tube holder|cleaning device)|"
            r"tracheostomy and laryngectomy protector"
        ),
        "coverageNote": (
            "COVERAGE LIMITS, STATED RATHER THAN HIDDEN. Two of the four agreements "
            "above are shared routes rather than respiratory ones: Airway Management "
            "Products is categorised by NHS Supply Chain under Medical and Surgical "
            "Consumables and is claimed by theatres and surgical, and Anaesthesia "
            "Machines, Ventilators, Neonatal Equipment and Phototherapy Systems is "
            "claimed by theatres and surgical and by maternity and neonatal, with this "
            "page claiming only the ventilator half. Being named on a framework is not "
            "evidence of volume on this patch, and being absent from one is not "
            "evidence of absence from the market. The supplier list is built from the "
            "four frameworks, so it counts airway and anaesthesia houses alongside "
            "respiratory ones; the page's own overlap analysis is the better guide to "
            "who is really on this patch, and it finds one supplier on all four lists "
            "and five on three. Home oxygen is the largest gap and it is a real one: "
            "it is bought through regional Home Oxygen Service contracts, not through "
            "any national NHS Supply Chain framework, so it appears in awards and "
            "tenders and nowhere else. The community medicines half of this patch — "
            "the larger half by money — is FP10 prescribing under BNF Chapter 3 and "
            "has no framework and no Drug Tariff Part IX presence at all."
        ),
    },
    # PAGE 2831. One NHS Supply Chain framework, one large community reimbursement
    # range, and a title vocabulary that is unusually clean once three words are
    # taken out of it.
    # PAGE 2826. Scope, in the page's own words: "ITU and HDU: organ support, patient
    # monitoring, infusion and continuous renal replacement — four separate frameworks,
    # four separate expiry dates, and no single critical care agreement to sell into."
    # Adult and paediatric intensive care. NOT the anaesthetic room (theatres), NOT
    # sleep and home ventilation (respiratory), NOT chronic in-centre dialysis (renal),
    # NOT peripheral cannulation (vascular access).
    "critical-care": {
        "label": "Critical Care",
        # THE FOUR THE PAGE NAMES, AND ONLY THOSE. Each one's expiry date in
        # frameworks.json matches the gold date the page's own calendar already
        # carries: Infusion Pumps 30 September 2026, Renal Replacement Therapies
        # 27 March 2028, Patient Monitoring 7 June 2028, Anaesthesia Machines and
        # Ventilators 28 February 2029. Deliberately NOT here, though every one of
        # them is used on an intensive care unit:
        #   Pulse Oximetry, Capnography and Related Monitoring Technologies
        #                        -> unclaimed by any speciality rule, and adding it
        #                           would make five frameworks on a page whose own
        #                           prose says four and lists four expiry dates. The
        #                           gap is real and is recorded rather than papered
        #                           over; it is the speciality PAGE that would have to
        #                           change first, not this filter.
        #   Airway Management Products               -> theatres and respiratory's.
        #   Non Invasive Ventilation, Sleep Therapy, CPAP -> respiratory's.
        #   Central Venous Catheters, Intravenous Accessories and Pressure Monitoring
        #                                            -> vascular access's.
        #   Enteral Feeding, Bile Bags                -> nutrition and dietetics'.
        #   External Defibrillation Devices           -> not this patch: every
        #                           defibrillator notice in this data is a community
        #                           or public-access AED, one of them bought by an
        #                           Education Authority for schools.
        "frameworks": r"(infusion pumps|renal replacement therap|patient monitoring equipment|anaesthesia machines)",
        # WRITTEN NARROW ON PURPOSE, because the loose form of nearly every term on
        # this patch is a false-positive nest and refusing it in the include is
        # cleaner than admitting it and arguing with it in the exclude:
        #   "ventilation" (not used)  -> 31 rows carry it and two are buildings:
        #                                Hillingdon's "Ventilation Verification" and
        #                                Buckinghamshire's "Provision of Ventilation
        #                                and Other Remediation Works". "ventilators?"
        #                                is the device and reaches neither.
        #   "infusion" (not used)     -> 30 rows, and 16 of them are DRUGS: nivolumab,
        #                                mogamulizumab, ravulizumab, gemcitabine,
        #                                Zolgensma, "Generic Drugs - Injections/
        #                                Infusions". Every one of them is the phrase
        #                                "solution for infusion" on a pharmacy buy.
        #                                The device terms are named individually here.
        #   "multiparameter" (not used) -> its one row is the University of Exeter
        #                                buying multiparameter sondes for fresh water
        #                                monitoring.
        #   "high dependency" (not used) -> its one row is Leicester City Council's
        #                                "High Dependency Bed Service", social care
        #                                placements, not an HDU. "high dependency
        #                                unit" is used instead and matches nothing
        #                                today, which is the honest answer.
        #   "life support" (not used)  -> two rows, both wrong: Advanced Paediatric
        #                                Life Support COURSE manuals, and Defence
        #                                Equipment and Support's Diving Life Support.
        #   "extracorporeal" (not used) -> three rows, none of them critical care:
        #                                NHSBT's extracorporeal photopheresis systems
        #                                twice, and blood-parameter monitoring during
        #                                cardiopulmonary bypass. "ecmo" is used
        #                                instead and reaches the one true row.
        #   "suction" (not used)       -> five rows of general theatre and ward
        #                                suction. Only "tracheal suction" is distinctly
        #                                intensive care.
        #   "resuscitation", "defibrillator", "airway", "blood gas" (not used)
        #                             -> resuscitation and defibrillation rows are
        #                                course manuals, neonatal baby warmers and
        #                                public-access AEDs; airway and blood gas are
        #                                the theatres and pathology pages' patches.
        "include": (
            r"\b(critical care|intensive care|itu|high dependency unit|"
            r"ventilators?|mechanical ventilation|"
            r"ecmo|extracorporeal membrane oxygenation|"
            r"patient monitors?|patient monitoring|vital signs? monitors?|"
            r"pulse oximet\w*|capnograph\w*|"
            r"infusion pumps?|infusion device|infusion system|rapid infuser|"
            r"administration sets?|syringe (?:pumps?|drivers?)|"
            r"crrt|renal replacement|h[ae]mofiltration|"
            r"tracheostom\w*|tracheal suction)\b"
        ),
        # Every one of these matched a real row that the include list let through and
        # that is not this speciality. All 71 titles the include list returned were
        # read one by one; these six are the ones that were wrong.
        #   medicines -> "For the Supply of ITU Medicine Covid-19 Preparedness -
        #                Propofol 1g/50ml emulsion for infusion vial", "ITU Medicines
        #                and End of Life Care Medicines for Covid-19 preparedness" and
        #                "Supportive Medicines - additional products (ITU, Antibiotics
        #                & EOI medicines)". All three are DHSC pharmacy stockpile buys
        #                that say ITU because of the ward the drug is used on. This
        #                page is organ support, monitoring and infusion hardware; the
        #                drugs that run through the pumps are not on it.
        #   insulin   -> "Insulin Infusion Pumps, Continuous Glucose Monitoring Systems
        #                and Associated Consumables". An insulin pump is a diabetes
        #                device on its own NHSSC framework, not an ITU infusion pump.
        #   cpap      -> "Non-Invasive CPAP Ventilators". CPAP and adaptive servo
        #                ventilation sit on NHS Supply Chain's Non Invasive
        #                Ventilation, Sleep Therapy and CPAP framework, which is the
        #                respiratory page's, not this one's.
        #   psychiatric intensive care
        #             -> "North Staffordshire Combined Healthcare NHS Trust Out of
        #                Area Psychiatric Intensive Care (PICU) Placement". A mental
        #                health bed placement. Note that the bare acronym PICU is NOT
        #                excluded, because elsewhere it means paediatric intensive
        #                care; only the spelled-out psychiatric phrase is.
        "exclude": r"\b(medicines?|insulin|cpap|psychiatric intensive care)\b",
        # 33194 transfusion and infusion devices, 33195 patient monitoring systems,
        # 33181 renal support devices — the three families that actually corroborate a
        # matching row in this data. CORROBORATION ONLY, and this patch shows why the
        # builder refuses to admit on CPV: Cwm Taf Morgannwg filed "Supply of Critical
        # Care Ventilators (Dräger Evita V800)" under CPV 39714100, which sits in the
        # building ventilation and air-conditioning family, not the medical one. A
        # filter that trusted CPV would have thrown out a real ICU ventilator award and
        # let in an air handling unit.
        "cpv": ("33194", "33195", "33181"),
        # NO DRUG TARIFF PART, and not for want of looking. Part IX reimburses
        # dressings and elastic hosiery (IXA), incontinence appliances (IXB), stoma
        # appliances (IXC) and elastic hosiery (IXR) dispensed in the community on
        # prescription. Ventilators, patient monitors, infusion pumps and CRRT
        # machines are hospital capital and hospital consumables and appear nowhere in
        # it. The panel carries none rather than reaching for the nearest part.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. These are the four NHS Supply "
            "Chain frameworks this page's own scope names, and being on one is not the "
            "same as selling to critical care. Each of the four is bought by wards far "
            "beyond the intensive care unit — the patient monitoring framework covers "
            "every bedside in the hospital, the anaesthesia framework covers the "
            "theatre suite and the neonatal unit — so a supplier counted here is a "
            "supplier on an agreement critical care buys through, never a measure of "
            "its critical care business. Three routes onto an ICU are missing from "
            "this count entirely: NHS Supply Chain's Pulse Oximetry, Capnography and "
            "Related Monitoring Technologies framework, which no speciality page yet "
            "claims; the Airway Management, Central Venous Catheter and Non Invasive "
            "Ventilation frameworks, counted on the theatres, vascular access and "
            "respiratory pages; and ECMO and specialist organ support, which NHS "
            "England commissions centrally through its Specialised Services route with "
            "no NHS Supply Chain framework page at all."
        ),
    },
    "emergency-and-urgent-care": {
        "label": "Emergency and Urgent Care",
        # FIVE AGREEMENTS, AND THE NUMBER IS THE PAGE'S OWN. Page 2922 says in terms
        # that there is "no single national route" and that "five NHS Supply Chain
        # frameworks carry the department's own kit". Its Buying route, its framework
        # calendar, its four Product ranges cards and its "five frameworks, side by
        # side" table all name the same five. Every reference and every expiry below
        # was matched back against the 121 names in frameworks.json on 11/09/2026 and
        # the pattern returns exactly those five and nothing else:
        #   External Defibrillation Devices and Related Services and Accessories
        #     (2022/S 000-035844, Direct route, 31/07/2023 to 30/07/2027, 3 lots,
        #     21 suppliers). Lot 1 AEDs with optional manual override, Lot 2 manual
        #     defibrillators, Lot 3 mechanical chest compression.
        #   Electrodes, Ultrasound Gels, Defibrillation and Related Consumables
        #     (2023/S 000-030987, Stocked and eDirect, 01/02/2024 to 31/01/2028, 37
        #     suppliers). The pads and ECG electrodes the devices above consume, and
        #     deliberately a separate agreement: NHS Supply Chain's own framework page
        #     says the device framework "will cover the capital purchase of the
        #     devices, but replacement consumables need to be purchased via" this one.
        #   Airway Management Products and Associated Equipment (2023/S 000-005729,
        #     22/07/2024 to 21/07/2028, 4 lots, 54 suppliers). SHARED, and the page
        #     says so: NHS Supply Chain describes it as covering products used "within
        #     NHS theatres, wards, Intensive Care Units (ICU), Accident and Emergency
        #     (A&E) areas, and ambulances". Theatres and surgical and respiratory both
        #     claim it and are right to.
        #   Respiratory Solutions (01/08/2022 to 15/06/2027, 6 lots, 37 suppliers).
        #     Claimed here for LOT 4, ANAESTHESIA AND RESUSCITATION ONLY — bag-valve
        #     masks, CPR masks, anaesthetic facemasks, absorbers and corrugated
        #     tubing. The other five lots are respiratory's and are claimed there.
        #   Simulation Devices and Services (2022/S 000-031912, Direct route,
        #     09/05/2023 to 08/05/2027, one lot, 7 suppliers). The first of the five
        #     to expire. NO OTHER SPECIALITY RULE CLAIMS IT, which was checked across
        #     all 34 rules rather than assumed, and it belongs here because the
        #     agreement exists precisely because resuscitation and simulation manikins
        #     were removed from the External Defibrillation Devices framework.
        #
        # NOT CLAIMED, each checked against the 121 names rather than assumed:
        #   Patient Monitoring Equipment, Infusion Pumps, Renal Replacement Therapies,
        #     Anaesthesia Machines and Ventilators -> critical care's four, claimed
        #     there. An emergency department uses all of them; being used in a place
        #     is not the same as being bought by it, and the page names five.
        #   Pulse Oximetry, Capnography and Related Monitoring Technologies -> still
        #     claimed by nobody, and still refused here for the same reason critical
        #     care and respiratory refused it. The gap is recorded in the coverage
        #     note rather than papered over by the page that happens to be next.
        "frameworks": (
            r"\b(simulation devices|external defibrillation|electrodes, ultrasound gels|"
            r"airway management|respiratory solutions)\b"
        ),
        # DERIVED, NOT GUESSED. The pattern below was run over all 1,972 rows of
        # tender-history.json and all 1,474 of framework-awards.json — 3,446 titles —
        # on 11/09/2026, and all 43 surviving titles were read one by one. 37 are this
        # patch and 6 were not; those 6 are the whole of the exclude list below.
        #
        # WRITTEN NARROW ON PURPOSE. The loose form of almost every word on this patch
        # is a false-positive nest, and refusing a term in the include is cleaner than
        # admitting it and then arguing with it in the exclude:
        #   bare "emergency" (NOT USED) -> 18 hits and 11 are buildings and vehicles:
        #     three separate emergency LIGHTING contracts, theatre emergency battery
        #     units, high voltage switchgear "emergency response", an emergency DCU
        #     and asbestos decontamination job, a housing association's alarms and
        #     entry systems, and three NON-emergency patient transport contracts that
        #     match on the very word that says they are not this patch. The qualified
        #     forms "emergency department", "emergency care" and "emergency medicine"
        #     are used instead and no lighting contract can reach a member even if
        #     this exclude list is edited later.
        #   "emergency medical" (NOT USED) -> both its hits are non-NHS workplace
        #     first aid: Thames Valley Police's "First Aid Emergency Medical
        #     Consumables and Equipment" and South Western Railway's "Provision of
        #     Emergency Medical Technician and Paramedic services".
        #   bare "first aid" (NOT USED) -> 16 hits and every one is a council, police
        #     force, fire service or buying consortium stocking workplace first aid
        #     kits: South Ayrshire, ESPO, Kent, Derbyshire, Hertfordshire, Lancashire,
        #     YPO, Scotland Excel, the Civil Nuclear Police Authority. Workplace first
        #     aid is a different market with different buyers and is not on this page.
        #   bare "urgent" (NOT USED) -> 12 hits and 7 are wrong: urgent suspected
        #     CANCER pathways, an urgent skin cancer dermoscopy triage service, an
        #     urgent non-obstetric ultrasound insourcing award, and "PIlgrim Urgent
        #     Pipe Replacement Works". "urgent care" and "urgent treatment centre" are
        #     used instead.
        #   bare "triage" (NOT USED) -> 3 hits and 2 are other specialities' (skin
        #     cancer dermoscopy, type 1 diabetes monitoring). The third, "The Supply
        #     of Triage Cards", is Leidos Supply buying military major-incident triage
        #     tags. Triage is the defining activity of this patch and the feed carries
        #     no NHS triage procurement at all; that is the honest answer and the
        #     pattern says nothing rather than reaching for the defence row.
        #   bare "resuscitat" (NOT USED) -> 2 hits, both refused for the same reasons
        #     critical care refused them: "Purchase of Baby Warmers with Resuscitation"
        #     is neonatal, and "Resuscitation Council Course Manuals and Registration
        #     Fee" is a book and a course fee, not a product on this patch. The
        #     resuscitation EQUIPMENT rows are reached through "chest compression",
        #     "defibrillat" and "manikin" instead.
        #   bare "aed" (NOT USED) -> its second hit is Surrey and Borders Partnership's
        #     "Provision Monitoring of service for the AED waitlist (10403)", a mental
        #     health trust waitlist where AED is not a defibrillator at all. Every real
        #     AED row spells "DEFIBRILLATORS" somewhere in the title and is reached by
        #     "defibrillat" without the acronym ever being used.
        #   bare "ambulance" (NOT USED) -> 10 hits and 6 are wrong: heat
        #     decarbonisation of four ambulance STATIONS, a station building
        #     improvement job, ambulance DRIVER TRAINING VEHICLES, two non-emergency
        #     patient transport notices and newborn transport harnesses. "ambulance
        #     services?" returns 4, of which 3 are this patch and the fourth is
        #     excluded below by name.
        #   bare "stretcher" (NOT USED) -> "Xtract Stretchers" is Hereford and
        #     Worcester FIRE AND RESCUE SERVICE buying extrication equipment. Fire and
        #     rescue casualty extrication is a neighbouring market with its own buyers
        #     and it is not the NHS ambulance service. "trolley beds" and "scoops and
        #     spineboards" reach both real rows — London Ambulance's trolley beds and
        #     Yorkshire Ambulance's scoops and spineboards — and the fire service
        #     cannot arrive through either.
        #   bare "electrode" (NOT USED) -> "Provision of EEG Electrodes" is
        #     neurology's. The named forms below reach all four real ECG and
        #     monitoring electrode rows and EEG cannot arrive through any of them.
        #   bare "utc" (NOT USED) -> its extra hit is "UNDERTAKE CAR PARK RESURFACING
        #     WORK AS PER ATTACHED QUOTE OUTSIDE UTC". "urgent treatment centre" is
        #     used and reaches all four real UTC rows.
        #   bare "111" (NOT USED) -> it happens to be clean today, on two rows, but a
        #     bare three-digit number in a corpus full of lot and reference numbers is
        #     a future false positive waiting to happen. "nhs 111" is used; the second
        #     row, BLMK's "Integrated Urgent Care (111 & Out of Hours) Service",
        #     arrives through "urgent care" anyway.
        #   bare "out of hours" (NOT USED) -> 3 hits and 2 are other services' — a
        #     Bromley out-of-hours PRIMARY CARE home visiting service and a West
        #     Yorkshire children's PALLIATIVE care out-of-hours advice line.
        #   "accident and emergency" and "a&e" (NOT USED) -> zero hits in the whole
        #     3,446-title corpus. The department's own name appears in no notice
        #     title in this feed. Recorded because an empty result is a finding.
        "include": (
            r"\b(emergency department|emergency care|emergency medicine|"
            r"urgent care|urgent treatment centre|"
            r"nhs 111|"
            r"ambulance services?|pre[- ]hospital|"
            r"defibrillat\w*|chest compression|"
            r"electrodes, ultrasound|patient diagnostic and monitoring electrodes|"
            r"ecg electrodes?|ultrasound gels?|"
            r"airway management|laryngoscop\w*|"
            r"simulations?|manikins?|mannequins?|"
            r"trolley beds?|scoops? and spineboards?|spineboards?)\b"
        ),
        # FOUR PATTERNS, SIX ROWS, AND EVERY ONE WAS READ BEFORE IT WAS EXCLUDED:
        #   dental        -> "C002027 Dental Simulation Units supply and installation"
        #                    (NHS Education for Scotland, dental phantom heads) and
        #                    "Dental Urgent Care Helpline(s) across the South West".
        #                    Dental simulation and dental urgent care are a separate
        #                    commissioning route with a separate contract holder.
        #   mental health -> "Mental Health Emergency Department (MH ED)" and "Mental
        #                    Health Recovery Workers - Mental Health Urgent Care
        #                    Department". Both are mental health staffing and service
        #                    commissions that borrow this patch's vocabulary for a
        #                    crisis pathway. Psychiatric liaison IS on page 2922, as a
        #                    clinical topic; the contracts are the mental health
        #                    trust's, not the emergency department's.
        #   gynaecolog    -> "Mannequin Gynaecology" (Gloucestershire Hospitals
        #                    Subsidiary Company). A gynaecological training model,
        #                    reached by "mannequin" and nothing else about it.
        #   decarbonisation -> "Heat Decarbonisation for 4 Ambulance Stations at East
        #                    Midlands Ambulance Service NHS Trust". An estates and net
        #                    zero capital scheme that reaches "ambulance service"
        #                    through the buyer's name sitting inside the title.
        "exclude": r"\b(dental|mental health|gynaecolog\w*|decarbonisation)\b",
        # CPV CORROBORATES, IT NEVER ADMITS, and 85143000 is the clearest
        # demonstration of that rule anywhere in this file. All four labels below were
        # read on 11/09/2026 from Regulation (EC) No 213/2008, the CPV regulation
        # itself, on EUR-Lex, rather than recalled:
        #   33182100 Defibrillator        — 2 notices in the feed carry it, both
        #                                   defibrillator buys.
        #   33172200 Resuscitation devices — the defibrillator market engagement and a
        #                                   cardio-respiratory systems maintenance
        #                                   contract. 33172100 Anaesthesia devices is
        #                                   deliberately NOT claimed: it is theatres'.
        #   31711140 Electrodes            — the monitoring electrodes market
        #                                   engagement, and "Provision of EEG
        #                                   Electrodes", which is neurology's and
        #                                   which the title gate refuses.
        #   85143000 Ambulance services    — TEN notices in this feed carry it and
        #                                   only TWO are this patch. The other eight
        #                                   are non-emergency patient transport, a
        #                                   stroke transport service, a paediatric
        #                                   retrieval service's patient transport, a
        #                                   dedicated hospital discharge vehicle and a
        #                                   secure transport contract. A filter that
        #                                   admitted on this code would have put all
        #                                   eight on an emergency care page. The title
        #                                   has to match; the code is recorded so a
        #                                   reader can see the classification agreed.
        "cpv": ("33182100", "33172200", "31711140", "85143000"),
        # NO DRUG TARIFF PART, AND THIS WAS PROVEN RATHER THAN ASSUMED. Page 2922
        # states that "nothing on this patch is dispensed on FP10 or listed in Part
        # IX". That claim was tested against the Hub's own tariff dataset on
        # 11/09/2026 by searching every Part IX row for defibrillator, manikin,
        # electrode, laryngoscope, resuscitation, airway, ambulance, simulation,
        # spineboard, scoop and ECG: zero rows matched, across IXA, IXB, IXB & IXC,
        # IXC and IXR. Part IX reimburses appliances dispensed in the community on
        # prescription; defibrillators, pads, airway adjuncts and training manikins
        # are hospital and ambulance-trust capital and consumables and appear nowhere
        # in it. The panel carries no tariff rather than reaching for the nearest part.
        "coverageNote": (
            "COVERAGE LIMITS, STATED RATHER THAN HIDDEN. Two of the five agreements "
            "above are shared routes rather than emergency care ones, and this page "
            "claims only part of each: Airway Management Products is claimed by "
            "theatres and surgical and by respiratory, and NHS Supply Chain's own "
            "description has it covering theatres, wards, intensive care and "
            "ambulances as well as A&E; Respiratory Solutions is respiratory's "
            "framework and is claimed here for Lot 4, Anaesthesia and Resuscitation, "
            "alone. The supplier list is built from all five frameworks whole, because "
            "NHS Supply Chain publishes suppliers per framework and not per lot, so a "
            "supplier counted here may be on this page only through a lot this patch "
            "does not buy. Being named on a framework is not evidence of volume on "
            "this patch, and being absent from one is not evidence of absence from the "
            "market. Three further limits are real and are named rather than left to "
            "be discovered. NHS Supply Chain's Pulse Oximetry, Capnography and Related "
            "Monitoring Technologies framework is claimed by no speciality page at "
            "all, so that route onto an emergency department is missing from every "
            "count on the Hub. The patient monitoring, infusion and ventilator "
            "agreements an emergency department uses daily are counted on the critical "
            "care page, because that is where they are bought. And the largest part of "
            "this patch by money has no framework at all: NHS 111, integrated urgent "
            "care, urgent treatment centre provision and urgent community response are "
            "commissioned by integrated care boards contract by contract, which is why "
            "they appear in the awards and tenders below and nowhere else. Four rows "
            "in that award list have buyers outside an NHS acute or ambulance trust "
            "and are kept deliberately, because the product and the supplier are the "
            "same market: a schools defibrillator purchase by Northern Ireland's "
            "Education Authority, which is public-access defibrillation; a university's "
            "simulation manikin purchase; a Ministry of Defence pre-hospital blood "
            "warming system; and the one medicines row on the panel, methoxyflurane "
            "(Penthrox) bought by the Welsh Ambulance Service, which is a pre-hospital "
            "analgesic with no other setting."
        ),
    },
    "pain-management": {
        "label": "Pain Management",
        # WRITTEN 11/09/2026, alongside the page-2907 build. Pain management is the
        # one speciality several other rules have been explicitly RESERVING a
        # framework for: gynaecology and plastics both refuse Neuromodulation
        # Devices in their own comments on the grounds that it is "pain
        # management's ground". This rule claims it, and claims only what page 2907
        # itself names.
        #
        # CLAIMED, each read at NHS Supply Chain's own contract launch brief on
        # 11/09/2026 and matched back to frameworks.json the same day:
        #   Neuromodulation Devices and Associated Products (2023/S 000-034841,
        #     18 March 2024 to 18 March 2028, 23 suppliers, three lots: Deep Brain
        #     Stimulation, Spinal Cord Stimulation, Other Neuromodulation). THIS
        #     PATCH'S OWN. It is the ONLY one of the 140 NHS Supply Chain contract
        #     launch briefs whose text claims pain management -- "a variety of
        #     strategic pain management solutions" -- and no brief TITLE in the
        #     whole catalogue contains the word "pain". Not shared with anybody.
        #     Caveat that belongs on the page and on this panel: NHSSC publishes no
        #     supplier-to-lot map, and several of the 23 are not pain companies at
        #     all (Inspire and Nyxoah are hypoglossal nerve stimulation for sleep
        #     apnoea, Phagenesis is pharyngeal stimulation for dysphagia, Flow
        #     Neuroscience is tDCS for depression). The supplier panel is therefore
        #     the framework's field, not a pain market-share table.
        #   Infusion Pumps and Administration Sets and Associated Products
        #     (Project_12 ITT_382, 3 October 2022 to 30 September 2026, 27
        #     suppliers, four lots). SHARED with critical care, palliative care and
        #     sepsis, all of which already claim it. It is here for the acute pain
        #     service: Lot 1 carries the patient-controlled analgesia pumps and
        #     Lot 4 the disposable elastomeric infusors used for continuous local
        #     anaesthetic. Nineteen days from expiry at the time of writing, with
        #     its 24-month extension already spent.
        #   Syringes, Needles and Associated Products (2026/S 000-002484, 52
        #     suppliers). SHARED, and shared very widely. It is here because the
        #     consumable under every diagnostic medial branch block, epidural and
        #     radiofrequency cannula on this patch sits on it, and because page
        #     2907 tells a rep to say so out loud rather than claim a pain
        #     framework that does not exist.
        "frameworks": (
            r"(neuromodulation|infusion pumps and administration sets|"
            r"syringes, needles)"
        ),
        # AWARDS: WRITTEN AS NARROW AS THE DATA ALLOWS, AND IT IS VERY NARROW.
        # The include is applied to BOTH award feeds. All 1,474 rows in
        # framework-awards.json and the whole of tender-history.json were searched
        # on 11/09/2026 for stimulat, neuro, pain, infusion, syringe, needle,
        # epidural, anaesthe, analges and catheter. The honest yield is FOUR rows,
        # all four read individually and all four kept:
        #   "Chronic Pain Service across Cheshire and Merseyside" -- NHS Cheshire
        #     and Merseyside ICB to Pastel Health Ltd, 25 August 2026, CPV 85100000.
        #     An ICB buying a whole chronic pain service from an independent
        #     provider, which is the shape this patch is moving into.
        #   "Provision of Outsourced Pain Management Services for Barking, Havering
        #     & Redbridge University Hospital NHS Trust" -- TWO notices, 21 and 24
        #     August 2026, and they are NOT a duplicate: one awards to Nuffield
        #     Health (The Holly Hospital) and one to Spire Healthcare PLC. One trust
        #     outsourcing its pain service to two independent providers in the same
        #     week. Keeping both is correct; deduplicating on title would lose a
        #     supplier.
        #   "Pain Management Pumps and Consumables [3632005]" -- Procurement and
        #     Logistics Service to Smiths Medical International Ltd, 5 November
        #     2021, from tender-history. The ONLY product award on this patch in
        #     either feed, and it is five years old and Northern Irish.
        #
        # THE FINDING THAT MATTERS: three of the four awards are for a SERVICE, and
        # two of those three hand a pain service to an independent provider. The
        # award data on this patch is about who runs the clinic, not about what the
        # clinic buys.
        #
        # DELIBERATELY NOT MATCHED, each checked row by row:
        #   bare "pain"        -> reaches "Hammersmith & Fulham MHU Refurbishment
        #                         Painting Works". Requiring "chronic pain" or
        #                         "pain management" reaches all four genuine rows
        #                         and never reaches the decorators.
        #   "stimulat"         -> ZERO rows in the framework-awards feed. There is
        #                         no published neuromodulation device award in this
        #                         data at all, which is itself the finding: the
        #                         devices move on the NHSSC framework by eDirect
        #                         order, not by individually noticed contract.
        #   "neuro"            -> 13 rows and every one is neurology or
        #                         neurophysiology insourcing, or neurodevelopmental
        #                         support for children. Neurology and neurosurgery's
        #                         patch, claimed there.
        #   "infusion"         -> 5 rows: an agalsidase alfa homecare line, a
        #                         generic injections and infusions contract, an IV
        #                         cannula set, a rapid infuser (already judged a
        #                         false positive on the palliative patch by finding
        #                         62 and again on sepsis) and a preliminary market
        #                         engagement notice for infusion and syringe pumps.
        #                         The last is genuinely relevant to acute pain but
        #                         is a market-engagement notice, not an award, and
        #                         it is equally critical care's and palliative's.
        #   "syringe"/"needle" -> 4 rows: two homecare biologic pre-filled syringe
        #                         contracts (rheumatology), the same market
        #                         engagement notice, and one syringes-and-needles
        #                         buy. The consumable frameworks are claimed above;
        #                         these award rows are not this speciality's.
        #   "epidural", "analges" -> ZERO rows each.
        "include": (
            r"(chronic pain|pain management)"
        ),
        # No exclude is needed and none is written: the include is already narrow
        # enough that every row it returns was read and is genuine. Writing a
        # decorative exclude would suggest a false positive exists that does not.
        "exclude": None,
        "coverageNote": (
            "Pain management has ONE framework of its own -- Neuromodulation Devices "
            "and Associated Products -- and it is the only agreement in NHS Supply "
            "Chain's whole 140-brief catalogue whose text claims this speciality; no "
            "brief title in the catalogue contains the word \u201cpain\u201d at all. "
            "The other two agreements shown here are shared general agreements that "
            "pain services buy through rather than own, and their supplier counts are "
            "borrowed: Infusion Pumps is also claimed by critical care, palliative "
            "care and sepsis, and Syringes, Needles is claimed very widely. Three of "
            "the four award rows are for a SERVICE rather than a product, and two of "
            "those three hand one trust’s pain service to an independent provider "
            "in the same week; the only product award in either feed is a 2021 Northern "
            "Irish pain-pump contract. A search of all 1,474 award rows for stimulat, "
            "neuro, infusion, syringe, needle, epidural, anaesthe, analges and catheter "
            "returned no neuromodulation device award of any kind, because those devices "
            "move by eDirect order on the framework rather than by individually noticed "
            "contract. The Drug Tariff reaches "
            "this patch too: four rows out of 66,400 in the September 2026 Part IX "
            "touch pain, three of them the same pulsed electromagnetic device at "
            "\u00a313.95, so no Part IX panel is published here."
        ),
    },
    "sepsis-and-the-deteriorating-patient": {
        "label": "Sepsis and the Deteriorating Patient",
        # NOBODY BUYS SEPSIS, AND THE FILTER HAS TO SAY SO. There is no NHS Supply
        # Chain framework with sepsis, deterioration or early warning in its name —
        # all 121 names in frameworks.json were read on 11/09/2026 and the only one
        # that even touches the vocabulary is the Laboratory Diagnostics agreement,
        # which reaches it through point of care testing. So this rule claims the
        # FOUR agreements page 2920 itself names, each matched back to its reference
        # and dates in frameworks.json on 11/09/2026, and the pattern returns exactly
        # those four and nothing else:
        #   Laboratory Diagnostics, Point of Care Testing and Pathology Managed
        #     Services (2023/S 000-028831, 12 March 2024 to 11 March 2028, 122
        #     suppliers). SHARED with pathology and laboratory medicine, which claims
        #     it as its own patch and is right to. It is here for the blood gas,
        #     lactate, blood culture and rapid molecular half of the sepsis pathway.
        #   Infusion Pumps and Administration Sets and Associated Products
        #     (Project_12 ITT_382, 3 October 2022 to 30 September 2026, 27 suppliers).
        #     SHARED with critical care and with palliative care. The nearest of the
        #     four expiries and the reason this page has a live clock on it.
        #   Intravenous Cannula and Associated Products (2022/S 000-005941, 27 March
        #     2023 to 31 March 2027, 21 suppliers).
        #   Pressure Infusers and Associated Products (2025/S 000-047797, started
        #     1 September 2026). frameworks.json carries NO end date for this one;
        #     NHS Supply Chain's own brief says 31 August 2028 with an option to
        #     extend 24 months, and page 2920 quotes it. The panel publishes the
        #     field as the source holds it rather than back-filling a date the feed
        #     does not carry — the gap is named in the coverage note instead.
        #
        # DELIBERATELY NOT CLAIMED, each checked against the 121 names:
        #   Patient Monitoring Equipment, Anaesthesia Machines and Ventilators,
        #     Renal Replacement Therapies -> critical care's, claimed there. A
        #     deteriorating patient is monitored on all of them; being used on a
        #     deteriorating patient is not the same as being bought for this pathway,
        #     and page 2920 names four frameworks, not seven.
        #   Pulse Oximetry, Capnography and Related Monitoring Technologies -> still
        #     claimed by no speciality rule, and refused here for the same reason
        #     critical care, emergency and respiratory refused it. The gap is recorded
        #     in the coverage note rather than filled by whichever page came last.
        #   External Defibrillation Devices, Simulation Devices -> emergency and
        #     urgent care's.
        #   Blood Collection Devices -> pathology's pre-analytical half.
        "frameworks": (
            r"(laboratory diagnostics|infusion pumps and administration sets|"
            r"intravenous cannula|pressure infusers)"
        ),
        # WRITTEN NARROW, because on this patch the loose form of almost every term
        # is somebody else's market and refusing it in the include is cleaner than
        # admitting it and arguing with it below:
        #   "septic" (not used)     -> 15 rows and every one is ASEPTIC: compounded
        #                              aseptic medicines, aseptic isolators, aseptic
        #                              pharmaceutical units. Pharmacy compounding, not
        #                              sepsis. "\bsepsis\b" reaches none of them and
        #                              matches nothing in this data at all, which is
        #                              the honest answer for a syndrome nobody
        #                              procures by name.
        #   "point of care" (not used) -> 5 rows and all 5 are wrong: two PoCUS
        #                              ultrasound simulator upgrades, a county
        #                              council's testing contract, an NHS Scotland
        #                              COVID-19 buy and a point of care HbA1c
        #                              analyser. The two point-of-care tests this
        #                              pathway actually turns on are named
        #                              individually, as "blood gas analys*" and
        #                              "blood culture".
        #   "cannula" bare (not used) -> "The supply of Nasal Cannula & Oxygen Masks
        #                              for Pandemic Preparedness 24/25" is oxygen
        #                              delivery and belongs to respiratory. Requiring
        #                              "iv" or "intravenous" in front reaches the
        #                              three genuine intravenous rows and never
        #                              reaches that one.
        #   "patient monitoring" (not used) -> 40 rows carry "monitor" and the term
        #                              would pull in the whole bedside-monitoring
        #                              estate, which is critical care's patch.
        #                              "vital signs monitor" is the track-and-trigger
        #                              device and matches one row, correctly. Note it
        #                              does NOT reach "Remote Monitoring of Vital
        #                              Signs", which is Dumfries and Galloway COUNCIL
        #                              buying telecare, because the words are the
        #                              other way round.
        #   "antibiotic", "antimicrobial", "medicines" (not used) -> page 2920 states
        #                              in terms that antimicrobials are on none of
        #                              these frameworks and go through pharmacy and
        #                              the local formulary. The 14 rows these terms
        #                              match are pharmacy buys and DHSC stockpiles,
        #                              and the page's own scope puts them off this
        #                              patch.
        #   "culture" bare (not used) -> mycobacterium bovis solid media, tissue
        #                              culture media and three microbiology culture
        #                              media contracts. "blood culture" is the sepsis
        #                              diagnostic and matches two rows, both right.
        "include": (
            r"\b(sepsis|septic shock|septic(?:a|ae)mia|"
            r"deteriorating patient|early warning score|news2|track and trigger|"
            r"e-?observations?|critical care outreach|rapid response team|"
            r"procalcitonin|blood culture|blood gas analys\w*|lactate analys\w*|"
            r"vital signs? monitors?|"
            r"pressure infus(?:er|or)\w*|"
            r"(?:iv|intravenous) cannulae?|"
            r"infusion pumps?|administration sets?)\b"
        ),
        # All 16 titles the include list returned across both award feeds were read
        # one by one on 11/09/2026. These three are the ones that were wrong.
        #   insulin        -> "Insulin Infusion Pumps, Continuous Glucose Monitoring
        #                     Systems and Associated Consumables", twice, both NHS
        #                     National Services Scotland. An insulin pump is a
        #                     diabetes device on its own agreement, not a resuscitation
        #                     pump. Critical care excludes it for the same reason.
        #   syringe driver -> "[4801618] Spare Parts for BodyGuard T Syringe Drivers
        #                     and Infusion Pumps". A BodyGuard T is an ambulatory
        #                     subcutaneous syringe driver and this is a spare-parts
        #                     buy; the feed tags it oncology and that is nearer the
        #                     truth than this page. Note "syringe PUMPS" is not
        #                     excluded — it appears in two genuine multi-product
        #                     infusion contracts that are on this patch.
        #   rapid infuser  -> "Rapid Infuser Blood/IV Infusion Pump", University
        #                     Hospitals of Derby and Burton. A trauma rapid infuser,
        #                     already judged a false positive on the palliative care
        #                     patch (rollout plan finding 62) and the same judgement
        #                     holds here: rapid infusion with blood warming is major
        #                     haemorrhage kit, and page 2920's fluid route is pressure
        #                     infusers and giving sets.
        "exclude": r"\b(insulin|syringe drivers?|rapid infuser)\b",
        # CORROBORATION ONLY. 33194 is transfusion and infusion devices and 3314122 is
        # intravenous cannulae — the two families the matched notices in this data
        # were actually filed under. Nothing is admitted on a code: NHS England's
        # "Blood Culture pathway- Health economic analysis" carries 79315000 research
        # services and 85100000 health services and no medical device code at all,
        # and it is the single most on-patch row in the whole slice.
        "cpv": ("33194", "3314122"),
        # NO DRUG TARIFF PART, and it was looked for rather than assumed. Part IX
        # reimburses dressings and elastic hosiery (IXA), incontinence appliances
        # (IXB), stoma appliances (IXC) and chemical reagents (IXR) dispensed in the
        # community. IXR is the only part that could plausibly carry a sepsis test and
        # all 101 of its rows in the September 2026 file are diabetes and
        # anticoagulation consumables — blood glucose and ketone strips, INR and urine
        # strips. Nothing on this pathway is dispensed on an FP10. The panel carries
        # no tariff rather than reaching for the nearest part.
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN. Sepsis is a pathway, not a "
            "product category, and every number in this panel is borrowed from an "
            "agreement bought for something broader. All four frameworks here are "
            "shared: the Laboratory Diagnostics agreement is counted on the pathology "
            "page, the infusion pumps agreement on the critical care and palliative "
            "care pages, and all four are used across wards that have nothing to do "
            "with deterioration. A supplier counted here is a supplier on an agreement "
            "this pathway buys through, never a measure of its sepsis business. Three "
            "things this count cannot reach at all. Antimicrobials, which are the "
            "single largest recurring spend on the Sepsis Six, sit on no framework "
            "here and go through pharmacy and the local formulary. E-observation and "
            "deterioration software, which is what NHS England's Sepsis modern service "
            "framework actually commits to standardising, is on no NHS Supply Chain "
            "framework at all and is bought trust by trust through digital "
            "procurement with a clinical safety case. And NHS Supply Chain's Pulse "
            "Oximetry, Capnography and Related Monitoring Technologies framework, "
            "which no speciality page yet claims, is refused here rather than swept up "
            "by whichever page happened to be built last. One field is published as "
            "the source holds it and not as the speciality page states it: "
            "frameworks.json carries no end date for the Pressure Infusers agreement, "
            "where NHS Supply Chain's own contract launch brief says 31 August 2028. "
            "Four of the fifteen awards below are Department of Health and Social Care "
            "pandemic-preparedness stockpile buys rather than trust purchases, and they "
            "are kept deliberately: the product in each is intravenous cannulae or "
            "intravenous giving sets, which is exactly what two of the frameworks above "
            "carry. Read them as national stockpiling, not as a trust opening a "
            "conversation."
        ),
    },
    "ophthalmology": {
        "label": "Ophthalmology",
        # ONE FRAMEWORK, AND THE PATTERN IS DELIBERATELY THE BARE STEM. All 121
        # NHSSC framework names were read: exactly one, "Complete Ophthalmology
        # Solutions 3" (Medical Technology CBU, 3 November 2025 to 2 November 2027,
        # 53 suppliers), is this speciality's. Nothing else in the list is an eye
        # framework under another word — checked against "eye", "ocular", "vision",
        # "optic", "lens", "cataract" and "retina" over every name, expired list and
        # unparsed entry, and none of them returned anything. So the stem matches
        # what it should and there is no second name to reach for.
        "frameworks": r"\bophthalm\w*",
        # EVERY MATCH WAS READ, ALL 63 OF THEM, ACROSS ALL THREE FEEDS. Terms kept
        # because a real notice needed them and the notice was genuinely this
        # speciality: "Ru-106 Eye Applicators" (ruthenium-106 plaque brachytherapy
        # for ocular tumours), "Supply of Pouches for Serum Eye Drops" (NHSBT's
        # serum eye drop service), "Mercaptamine Eye Drops", the donated corneal
        # tissue contracts at Queen Victoria Hospital and Moorfields, "Eyesi
        # Surgical Complete Simulator", "CARL ZEISS IOL MASTER 700 SYSTEM" and
        # "IOL's and associated Products".
        #
        # REFUSED FROM THE INCLUDE RATHER THAN EXCLUDED AFTERWARDS:
        #   bare "vision"   -> matches the word "provision", which appears in 100+
        #                      titles of every speciality. Only "low vision",
        #                      "visual field", "visual acuity" and "visual
        #                      electrophysiology" are admitted.
        #   bare "optic"    -> "Optical Laser Fibre Consumables for CyberHo 100
        #                      Holmium Laser System" and two more Cook optical laser
        #                      fibre awards are urology lithotripsy, and
        #                      "Inductively Coupled Plasma Optical Emission
        #                      Spectrometer" is analytical chemistry. Only "optical
        #                      coherence tomography" and "optic nerve" are admitted.
        #   bare "lens"     -> admitted only as "intraocular", "contact lens" or
        #                      "spectacle"; a bare lens is a camera part.
        #   "bevacizumab"   -> "Bevacizumab IV Infusion Vials" (NHS National
        #                      Services Scotland) is the oncology intravenous
        #                      product, not the off-label intravitreal use. The
        #                      title cannot tell the two apart, so it is refused.
        #   "oct"           -> never used as a bare abbreviation: it is also the
        #                      month.
        # "aflibercept", "ranibizumab" and "faricimab" ARE admitted bare. All six
        # aflibercept notices in this data are intravitreal (2mg, 8mg and 3.6mg in
        # 90 microlitres pre-filled syringes) and all are wet AMD. The oncology form
        # of aflibercept is spelled ziv-aflibercept or branded Zaltrap, and neither
        # string appears anywhere in this repository's data — checked, not assumed.
        # If one ever arrives it will need excluding, and the invariant in
        # test_speciality_panels.py is what will show it.
        "include": (
            r"\b(ophthalm\w*|ocular|intra-?ocular|intravitreal|"
            r"vitreoretinal|vitrectomy|cataract|phaco\w*|iol|eyesi|"
            r"retina|retinal|retinopath\w*|macula|macular|"
            r"glaucoma|tonomet\w*|"
            r"cornea|corneal|keratoplasty|keratoconus|keratomet\w*|"
            r"optometr\w*|orthopt\w*|"
            r"slit lamp|fundus camera|optical coherence tomograph\w*|optic nerve|"
            r"eye|"
            r"low vision|visual field\w*|visual acuity|visual electrophysiolog\w*|"
            r"squint|strabismus|blepharo\w*|oculoplast\w*|lacrimal|punctal|"
            r"ranibizumab|aflibercept|brolucizumab|faricimab|pegaptanib|verteporfin|"
            r"spectacle\w*|contact lens\w*)\b"
        ),
        # THREE PATTERNS, and each is here because a real row matched `include`, was
        # read, and was rejected:
        #   eye protection -> "Single Use Eye Protection", Supply Chain Coordination
        #                     Limited. Goggles and visors. That is personal
        #                     protective equipment and infection prevention's patch,
        #                     and it is the highest-volume false positive the bare
        #                     word "eye" produces.
        #   small animal   -> "QUB/2597/24 a Fully Integrated Small Animal In-Vivo
        #                     Ophthalmic Retinal Ocular Imaging System", Queen's
        #                     University Belfast. A preclinical research rig. It
        #                     carries three of this rule's terms at once and is not
        #                     an NHS ophthalmology purchase by any reading. Same
        #                     shape as Kew Gardens' seed viability X-ray cabinet on
        #                     the wound care page.
        #   intravascular  -> "Intravascular Optical Coherence Tomography (OCT)",
        #                     NHS Golden Jubilee. Intravascular OCT is a coronary
        #                     imaging catheter. Same three letters, different organ;
        #                     it belongs to cardiology.
        "exclude": r"\b(eye protection|small animal|intravascular)\b",
        # THE THREE OPHTHALMOLOGY-SPECIFIC CPV CODES SEEN ON GENUINE NOTICES IN THIS
        # DATA: 33122000 on the orthoptic device replacement, the Wales
        # Ophthalmology and Vision Care consumables award and the corneal topography
        # maintenance; 33731110 on "IOL's and associated Products"; 85121281 on
        # Community Ophthalmology twice, Community Ophthalmology Service and Stable
        # Glaucoma Monitoring in Surrey Downs. They corroborate only. The Diabetic
        # Eye Screening Programme award, which is genuinely this speciality, carries
        # none of them and reaches the panel on its title alone — which is the point
        # of the title gate being the admitting one.
        "cpv": ("33122000", "33731110", "85121281"),
        # PART IXA, SLICED, AND IT IS A LARGER RANGE THAN THIS PAGE PREVIOUSLY SAID.
        # Part IXA is 56,833 lines of appliances. Inside it sits the whole community
        # ocular surface range: 223 lines, 89 virtual medicinal products, 36
        # suppliers, reimbursed from £0.61 to £25.25. Every one of the 89 was read.
        # They are the ocular lubricants (sodium hyaluronate, carmellose,
        # hypromellose, carbomer and polyvinyl alcohol eye drops, gels and
        # ointments, preserved and preservative free), the lid hygiene range
        # (AccuSoft and Evolve eyelid wipes, Epimax eyelid ointment, the Meibopatch,
        # Optase and Clinitas warm compresses, the Blepha EyeBag), sodium chloride
        # 5% and 6% for corneal oedema, artificial eye lubricants, the eye drop
        # dispenser and the eye pad. Leading suppliers by line count are TriOn
        # Pharma, Visufarma UK, Aspire Pharma, Blumont Healthcare and Scope
        # Ophthalmics.
        #
        # WHY THE PATTERN IS A PREFIX AND NOT A WHOLE WORD. "\beye" rather than
        # "\beye\b" is needed for "eyelid" and for "Generic Blepha EyeBag", which a
        # whole-word match loses; it was then checked against every Part IX row and
        # selects nothing outside IXA and nothing that is not ophthalmic. "ocular",
        # "corneal", "conjunctiv" and "lacrimal" were tested over both the virtual
        # and the brand name across all five parts and match zero rows, so they are
        # not in the pattern: an alternative that cannot fire is noise in a rule a
        # member is asked to judge.
        #
        # ONE OVERLAP, STATED. "Eye pad No 16 with bandage BPC" is an eye dressing
        # and is also inside the Part IXA range that tissue viability and wound care
        # claims whole. It is counted on both pages and that is correct: it is one
        # product with two clinical homes, not a double count of two things.
        "tariffParts": ("IXA",),
        "tariffVmp": r"\beye",
        "coverageNote": (
            "COVERAGE LIMITS, STATED RATHER THAN HIDDEN. This patch splits in two and "
            "only one half has a national route. The hospital half — intraocular "
            "lenses, viscoelastics, phaco and vitreoretinal capital, surgical packs, "
            "instruments, glaucoma stents and the anti-VEGF drugs, which are "
            "hospital-administered high-cost medicines — is bought on Complete "
            "Ophthalmology Solutions 3, on regional and national framework awards, or "
            "trust by trust, and that is what the frameworks, suppliers and awards "
            "above show. The community half is the ocular surface range in Drug "
            "Tariff Part IXA below, which is a different set of suppliers almost "
            "entirely and is prescribed rather than tendered. Being named on the "
            "framework is not evidence of volume, and being absent from it is not "
            "evidence of absence from the market: high street optometry, the General "
            "Ophthalmic Services contract and the independent-sector cataract "
            "providers who now hold a growing share of this speciality's activity buy "
            "outside NHS Supply Chain entirely and appear here only when they publish "
            "an award notice."
        ),
    },

    "ent-and-head-and-neck": {
        "label": "ENT and Head and Neck",
        # THREE FRAMEWORKS, AND THE PATTERN NAMES ALL THREE EXPLICITLY BECAUSE NHS
        # SUPPLY CHAIN'S NAMING IS COUNTER-INTUITIVE IN BOTH DIRECTIONS ON THIS PATCH.
        # All 110 NHSSC framework names were read for this build.
        #   "Ear, Nose and Throat (ENT) Endoscopes and Associated Options and Related
        #     Services" is the one with the speciality's name on it. Its own Product
        #     Categories section lists only Fibre Optic Endoscopes, Intubating
        #     Endoscopes, Video Endoscopes and Video Processors / Light Source -- it is
        #     the FLEXIBLE and video half of the patch and nothing else.
        #   "Rigid Endoscopy and Associated Options and Related Services" does not say
        #     ENT in its title, and "ENT Scopes" is one of the nine product categories
        #     it publishes. The rigid ENT set is bought there, from 18 suppliers, not
        #     from the 7 on the framework named after the speciality. It is also
        #     claimed by the urology page, correctly: one agreement, several clinical
        #     homes, the same way an eye pad is counted on both wound care and
        #     ophthalmology.
        #   "Dental Technologies, Implants and Related Consumables and Services" carries
        #     the OMFS half. Its brief states in its own words that it covers "multiple
        #     dental disciplines including orthodontics and maxillofacial". It is named
        #     in this pattern but it does NOT reach the panel, and that is correct
        #     behaviour rather than a miss: frameworks.json holds it in `unparsed` with
        #     the reason "the page states 33 suppliers but 35 were parsed - refusing
        #     rather than publishing a list that does not match the page". The brief
        #     renders three delisted names (Hospital Services, Straumann, Wyvern) in the
        #     same block as the awarded ones, and its own awarded list prints "RPA
        #     Dental Equipment" twice, so 32 distinct awarded names + 3 delisted = 35
        #     against a stated 33. The refusal is the gate working. Do not loosen it to
        #     make this panel show three frameworks; the coverage note says what is
        #     missing and why.
        # DELIBERATELY NOT CLAIMED, each for a stated reason, not an oversight:
        #   "Flexible Endoscopes and Associated Options and Related Services" shares the
        #     ENT framework's procurement reference but publishes ten product
        #     categories -- bronchoscopes, gastroscopes, duodenoscopes, cystoscopes,
        #     ureteroscopes and the rest -- and not one of them is an ENT scope. Its own
        #     overview says it is used "by Endoscopy and Gastroenterology professionals".
        #   "Audiological Diagnostics Implantable Devices and Services" is the
        #     audiology-and-hearing page's framework, and the boundary between these two
        #     pages is drawn there.
        #   "Airway Management Products and Associated Equipment" holds the tracheostomy
        #     tubes and is claimed by theatres-and-surgical and critical care.
        "frameworks": r"(ear,? nose and throat|\(ENT\)|rigid endoscopy|dental technologies)",
        # EVERY MATCH WAS READ. The unrefined version of this pattern returned 28 rows
        # in tender-history.json and 8 in framework-awards.json. Sixteen survive, and
        # the twelve that do not were removed by refusing terms in the include rather
        # than excluding them afterwards, which is the standard the renal and
        # ophthalmology rules set.
        #
        # REFUSED FROM THE INCLUDE:
        #   hearing, audiolog*, audiometr*, cochlear, tinnitus, ear mould, vestibular
        #                 -> eight real rows (Hearing Aid Batteries, Audiology Products
        #                    twice, 981 Audiology Equipment, Audiological Equipment,
        #                    Audiological Diagnostics Implantable Devices Accessories &
        #                    Services 2024, Cochlear Implants and Accessories, Hearing
        #                    Aids Hearing Aid Batteries Custom Ear Moulds). None of
        #                    those is a false positive -- every one is a genuine
        #                    purchase on this clinical territory. They are refused
        #                    because they belong to the audiology-and-hearing page, and
        #                    a boundary between two pages is not the same thing as a
        #                    wrong match. Said plainly here so nobody "fixes" it later.
        #   laryngoscop*  -> five rows, and all five are airway management rather than
        #                    ENT: "ED C-MAC Video Laryngoscope", "ESNEFT3113 Purchase of
        #                    Video Laryngoscopes", "ESNEFT Purchase of Video
        #                    Laryngoscopes", "Laryngoscope Blades and Associated
        #                    Consumables", "Laryngoscope Handles and Blades". The
        #                    intubating laryngoscope and the ENT rhino-laryngoscope
        #                    share a word and nothing else. ENT's own scopes reach this
        #                    panel as "nasendoscope", which is admitted.
        #   bare "sinus"  -> coronary sinus and sinus rhythm are cardiology. Only
        #                    "sinusitis", "rhinosinusitis" and "paranasal" are admitted.
        #   bare "pharyn" -> the oropharyngeal airway is anaesthesia's.
        #   bare "ear"    -> nothing is lost by dropping it once hearing is refused, and
        #                    it is the highest-risk single word in the list.
        # ADMITTED AND WORTH SAYING WHY: "dental implant*" is admitted although two of
        # its three rows are Leidos Supply Limited, which is Defence Medical Services
        # rather than NHS. Bespoke dental implants are an OMFS product wherever they are
        # bought, and the buyer is published beside each row so a reader can judge it.
        "include": (
            r"\b(ENT|otolaryng\w*|otolog\w*|rhinolog\w*|rhinoplast\w*|rhinosinusit\w*|"
            r"septoplast\w*|turbinate\w*|"
            r"nasal|nose|nasendoscop\w*|paranasal|sinusitis|"
            r"tonsil\w*|adenoid\w*|grommet\w*|tympan\w*|myringo\w*|mastoid\w*|otitis|"
            r"otoscop\w*|stapes|"
            r"epistaxis|tracheostom\w*|laryngectom\w*|voice prosthes\w*|"
            r"head and neck|maxillofacial|OMFS|oral surgery|orthognathic|dental implant\w*|"
            r"thyroidectom\w*|parathyroid\w*|salivary|parotid|throat)\b"
        ),
        # ONE PATTERN, AND IT IS HERE BECAUSE A REAL ROW MATCHED AND WAS WRONG.
        # "The supply of Nasal Cannula & Oxygen Masks for Pandemic Preparedness 24/25",
        # Secretary of State for Health and Social Care. A nasal cannula is oxygen
        # therapy: it goes in the nose and has nothing to do with this speciality. The
        # neighbouring forms are excluded with it before one of them arrives.
        "exclude": r"\b(nasal cannula\w*|nasal high flow|nasal prong\w*|nasal oxygen|nasogastric)\b",
        # THE TWO CPV CODES SEEN ON GENUINE ROWS IN THIS DATA: 85121240, on Kettering
        # General Hospital's ENT Outsourcing notice, is the ENT services code;
        # 85111100 is on University Hospital Southampton's Urology and OMFS Insourcing
        # award. They corroborate only -- both of this patch's live procurement rows
        # reach the panel on their titles.
        "cpv": ("85121240", "85111100"),
        # PART IXA, SLICED, AND IT IS A REAL COMMUNITY MARKET THAT A HOSPITAL-FACING
        # ENT REP NEVER SEES. 645 lines, 19 virtual medicinal products, 31 suppliers,
        # reimbursed from 33p to 174.18 pounds, all inside Part IXA. It is the
        # head and neck cancer survivorship range -- tracheostomy breathing aids (483
        # lines on their own), tracheostomy and laryngectomy protectors, tube holders,
        # cleaning devices, tracheostomy dressings and voice prosthesis cleaning
        # brushes -- plus the small primary care ENT range: olive oil, sodium
        # bicarbonate and Burow's solution ear drops, sea water and sodium chloride
        # nasal preparations, the nasal aspirator, and one auto inflation device.
        #
        # WHY THE PATTERN IS A LIST OF ANCHORED NAMES AND NOT A KEYWORD. Part IXA is
        # 56,833 lines and the loose ENT words select rubbish from it: "nasal" alone
        # reaches sodium chloride nebuliser solutions, and "ear" reaches every
        # lymphoedema garment with "waist/hip" in the description via "wear". Each of
        # the 19 virtual products below was read and named. Stoma caps were tested and
        # REFUSED: all 14 lines are Part IXC ostomy appliances (Assura Minicap, Nova
        # MiniCap, Confidence Gold), not laryngectomy stoma covers, and they belong to
        # colorectal-gi-and-endoscopy.
        #
        # THE OVERLAP WITH RESPIRATORY, MEASURED AND STATED RATHER THAN DISCOVERED
        # LATER. The respiratory rule already claims four of these families -- peak flow
        # meters plus tracheostomy breathing aids, tube holders and cleaning devices and
        # the tracheostomy and laryngectomy protectors -- 608 Part IXA lines in all.
        # 582 of this rule's 645 lines are the same rows. That is deliberate and it is
        # correct: the tracheostomy and laryngectomy range has two clinical homes, the
        # head and neck surgeon and cancer multidisciplinary team who create and manage
        # the stoma, and the respiratory team who manage the airway through it. The 63
        # lines that are ONLY on this page are the ones no respiratory reading reaches:
        # 15 voice prosthesis cleaning brushes, 15 tracheostomy dressings, 21 ear drop
        # lines, 11 nasal preparation lines and the single auto inflation device. The
        # 26 peak flow meter lines are respiratory's alone and are not claimed here.
        # Whoever next rebuilds the respiratory page should decide whether the voice
        # prosthesis and laryngectomy protector families belong there at all; this build
        # did not change another speciality's rule, it recorded the question.
        #
        # ONE FURTHER OVERLAP, STATED. The tracheostomy dressings are dressings and also
        # sit inside the Part IXA range that tissue viability and wound care claims
        # whole. Counted on both, correctly: one product, two clinical homes.
        "tariffParts": ("IXA",),
        "tariffVmp": (
            r"^(Tracheostomy|Voice prosthesis|Laryngectomy|Auto inflation device|"
            r"Olive oil ear drops|Sodium bicarbonate 5% ear drops|Burow|"
            r"Sea water nasal spray|Sesame oil nasal spray|Nasal aspirator|"
            r"Sodium chloride 0\.9% nasal drops)"
        ),
        "coverageNote": (
            "COVERAGE LIMITS, STATED RATHER THAN HIDDEN. This patch is two specialities "
            "sharing a page -- ear, nose and throat surgery and oral and maxillofacial "
            "surgery -- and neither of them buys most of its product through an "
            "agreement with its own name on it. The framework named after ENT covers "
            "flexible and video endoscopes only; the rigid ENT set is on Rigid "
            "Endoscopy, and the OMFS half is on Dental Technologies. Everything else "
            "this patch uses -- the microdebriders, coblation wands, image guidance "
            "systems, operating microscopes, nerve monitors, sinus balloons, tonsil "
            "instruments, tracheostomy tubes and the head and neck cancer implants -- "
            "is bought on cross-speciality agreements owned by theatres, capital or "
            "critical care, or trust by trust. Being named on a framework here is not "
            "evidence of volume on this patch, and being absent from one is not "
            "evidence of absence from the market. The audiology half of ear surgery -- "
            "cochlear implants, bone conduction devices, diagnostic and fitting "
            "equipment -- is on the Audiological Diagnostics Implantable Devices and "
            "Services framework and is counted on the audiology and hearing page, not "
            "here. ONE FRAMEWORK IS MISSING FROM THE LIST ABOVE ON PURPOSE. Dental "
            "Technologies, Implants and Related Consumables and Services (2023/S "
            "000-008274, 5 January 2024 to 4 January 2028, 11 lots) is this patch's "
            "OMFS agreement and the Hub refuses to publish its supplier list, because "
            "NHS Supply Chain's own brief states 33 suppliers and the page parses 35: "
            "it renders three delisted names in the same block as the awarded ones and "
            "prints RPA Dental Equipment twice. A list that does not match the page it "
            "came from is not published here. Read the brief itself for that "
            "framework. THE DRUG TARIFF PANEL BELOW OVERLAPS THE RESPIRATORY PAGE ON "
            "PURPOSE: 582 of its 645 lines are the tracheostomy and laryngectomy range, "
            "which is counted there too because the airway through the stoma is "
            "respiratory's and the stoma itself is this speciality's. The 63 lines "
            "unique to this page are the voice prosthesis cleaning brushes, the "
            "tracheostomy dressings, the ear drops, the nasal preparations and the one "
            "auto inflation device."
        ),
    },
    # PAGE 2917. Scope, in the page's own words: "Adult and paediatric audiology,
    # hearing aids, implants, tinnitus and balance." The ear as an ORGAN OF HEARING
    # AND BALANCE, not the ear as a surgical site: mastoid, tympanoplasty, grommets
    # and stapes surgery are the ENT and head and neck page's, and that page's rule
    # draws the same boundary from the other side.
    "audiology-and-hearing": {
        "label": "Audiology and Hearing",
        # TWO FRAMEWORKS, AND THEY ARE THE WHOLE NHS SUPPLY CHAIN ROUTE FOR THIS
        # PATCH. All 121 framework names in frameworks.json were read for this build.
        #   "Audiological Diagnostics Implantable Devices and Services"
        #     (2023/S 000-007624, 2 April 2024 to 1 April 2028, 15 suppliers) is the
        #     diagnostic and implantable half: the cochlear, bone conduction and
        #     middle ear implant manufacturers (Advanced Bionics, Cochlear Europe,
        #     Med-El) sitting alongside the test-booth and diagnostic firms
        #     (Amplivox, Interacoustics, Otodynamics, Natus Nicolet, Guymark, Diatec).
        #   "Hearing Aids, Hearing Aid Batteries, Custom Ear Moulds and Hearing Aid
        #     Accessories" (2022/S 000-010796, 27 March 2023 to 26 March 2027, 13
        #     suppliers) is the aid, battery and earmould half.
        # Both parse cleanly and both counts are verified against NHS Supply Chain's
        # own stated total on the brief (15 and 13), so neither is in `unparsed` and
        # neither needs a frameworkCorrections entry.
        # DELIBERATELY NOT CLAIMED:
        #   "Ear, Nose and Throat (ENT) Endoscopes and Associated Options and Related
        #     Services" is the only other framework whose name carries the word "ear".
        #     It is flexible and video endoscopes for ENT surgery and it belongs to
        #     ent-and-head-and-neck, which claims it explicitly. The pattern below is
        #     written so it cannot reach it: "audiolog", "hearing aid", "cochlear" and
        #     "ear mould" are all absent from that title.
        "frameworks": r"\b(audiolog\w*|hearing aids?|cochlear|ear moulds?)\b",
        # EVERY MATCH WAS READ, ONE BY ONE. The include below returns 17 rows across
        # the two award feeds -- 10 in tender-history.json and 7 in
        # framework-awards.json -- and 16 of the 17 are genuinely this speciality:
        # the two NHS Supply Chain agreements themselves, NHS Wales' Audiology
        # Products twice, NHS Scotland's Audiological Equipment and Bone Conduction,
        # Northern Ireland's Cochlear Implants and Accessories and its 2026 market
        # engagement for the successor, three ICB community audiology services
        # (Hampshire and the Isle of Wight, Cornwall, Birmingham and Solihull), a
        # Royal Berkshire hearing aid battery call-off, an Aston University audiology
        # equipment purchase, a Norfolk and Norwich audiology calibration contract and
        # NHS Highland's environmental aids for deaf people.
        #
        # WHAT THE FEED'S OWN `spec` FIELD SAYS ABOUT THOSE SAME ROWS, AND WHY IT IS
        # NEVER READ HERE: of the 10 tender-history rows, it tags ONE correctly. It
        # files Audiology Products under continence-bladder-and-bowel (twice),
        # Audiological Equipment and Audiological Diagnostics under
        # theatres-and-surgical, Cochlear Implants and Accessories under
        # orthopaedics-and-trauma, and Hearing Aids, Hearing Aid Batteries, Custom Ear
        # Moulds under gynaecology-and-womens-health. Nine wrong out of ten.
        #
        # REFUSED FROM THE INCLUDE, each with what it actually did:
        #   bare "audio"  -> reaches "Audio Visual (AV) Event Support For
        #                    International Conference", Department for Energy Security
        #                    and Net Zero. Refused in favour of "audiolog\w*", which
        #                    cannot reach it.
        #   bare "sound"  -> 41 rows in tender-history alone, and they are ultrasound:
        #                    the word is a substring of the biggest imaging term in
        #                    the dataset.
        #   bare "implant"-> 25 rows across the two feeds, and they are orthopaedic
        #                    and dental. Only the qualified forms are admitted:
        #                    "cochlear", "auditory implant", "bone conduction",
        #                    "bone anchored".
        #   "speech"      -> two real rows, both Experts at Hand educational
        #                    psychology, speech and language and occupational therapy
        #                    support. Speech and language therapy is a neighbouring
        #                    service, not audiology, and neither row is a product
        #                    purchase on this patch.
        #   bare "hearing"-> REFUSED ON RISK, NOT ON AN OBSERVED WRONG MATCH, and said
        #                    plainly so nobody "corrects" it later. In this data today
        #                    it matches exactly two rows and both are genuine. It is
        #                    still refused, because in public procurement the commonest
        #                    sense of the word is a tribunal, appeal or court hearing,
        #                    and nothing at all is lost by dropping it: both rows are
        #                    caught by "hearing aid".
        #   bare "ear"    -> the same judgement. With a word boundary it matches only
        #                    the genuine Custom Ear Moulds row today, but it is the
        #                    highest-risk single word available here and the title it
        #                    would most likely reach next is "Ear, Nose and Throat",
        #                    which is the neighbouring page's. "ear mould" is admitted
        #                    instead.
        #   bare "balance"-> matches nothing in this data and would reach fluid
        #                    balance, balance sheets and balance of plant if it did.
        #                    The vestibular half of this patch is admitted as
        #                    "vestibular" and "balance clinic", which mean one thing.
        "include": (
            r"\b(audiolog\w*|audiometr\w*|"
            r"hearing aids?|hearing loss|hearing screening|hearing assessment|"
            r"hearing therap\w*|hearing services?|hearing care|hearing tests?|"
            r"hearing loop|assistive listening|induction loop|"
            r"cochlear|auditory implant\w*|auditory brainstem|"
            r"bone conduction|bone anchored|"
            r"ear moulds?|earmoulds?|"
            r"tinnitus|otoacoustic|tympanometr\w*|ototox\w*|"
            r"vestibular|balance clinic|"
            r"deaf|deafness)\b"
        ),
        # ONE PATTERN, AND IT IS HERE BECAUSE A REAL ROW MATCHED AND WAS WRONG.
        # "Deaf Awareness Training Courses", Mersey and West Lancashire Teaching
        # Hospitals NHS Trust, CPV 80561000 -- health training services. It reached the
        # panel on "deaf" and it is a workforce education contract, not a purchase of
        # hearing products or a commissioned hearing service. A rep on this patch
        # cannot sell into it. "deaf" itself stays admitted, because the row it was
        # put there for -- NHS Highland's "Specialist Environmental Aids for Deaf
        # People", won by Sarabec -- is exactly this market.
        "exclude": r"\bdeaf awareness\b",
        # THE TWO CPV CODES SEEN ON GENUINE ROWS: 33185200 is cochlear implant, on
        # Northern Ireland's market engagement notice; 85121240 is ENT or audiology
        # services, on all three ICB community audiology awards. They corroborate and
        # they never admit, and this patch is the clearest proof of that rule in the
        # whole dataset: 85121240 also sits on "Audio Visual (AV) Event Support For
        # International Conference" for the Department for Energy Security and Net
        # Zero, and inside 25-code baskets on the Government Commercial Agency's
        # Employee Benefits and Occupational Health Services and the Countess of
        # Chester's insourcing framework. Admitted on CPV, a government department's
        # conference AV contract would be published to a paying member as audiology.
        "cpv": ("33185200", "85121240"),
        # NO DRUG TARIFF PART, AND THIS ONE IS MEASURED RATHER THAN ASSUMED. All
        # 66,400 lines of Part IX were searched for "hearing", "audiolog", "cochlear",
        # "tinnitus", "ear mould", "auditory" and "deaf". The result is zero. Part IX
        # reimburses dressings and elastic hosiery (IXA), incontinence (IXB), stoma
        # (IXC) and elastic hosiery (IXR); hearing aids, batteries, earmoulds and
        # implants are supplied through hospital audiology departments and the two
        # NHS Supply Chain agreements above, not prescribed on an FP10. The panel
        # carries no tariff rather than reaching for the nearest part.
        "coverageNote": (
            "COVERAGE LIMITS, STATED RATHER THAN HIDDEN. Both of this patch's national "
            "agreements are in their final years -- Hearing Aids, Hearing Aid "
            "Batteries, Custom Ear Moulds and Hearing Aid Accessories ends 26 March "
            "2027 and Audiological Diagnostics Implantable Devices and Services ends 1 "
            "April 2028 -- and their successor has not been awarded, so it is not in "
            "the Hub's framework dataset and cannot be. Being named on either "
            "framework below is a statement about the current agreements only. TWO "
            "ROWS THAT ARE PROBABLY THIS SPECIALITY ARE NOT COUNTED, and it is worth "
            "saying which rather than letting a reader assume the feed is complete. "
            "Leeds Teaching Hospitals' \"Purchase of Screening Kits\", won by Natus "
            "Nicolet UK, is very likely newborn hearing screening, and Diatec "
            "Diagnostics' \"New equipment (2 x Titan)\" is very likely the "
            "Interacoustics Titan tympanometry and otoacoustic emissions platform. "
            "Both are refused because neither title can carry the claim on its own: "
            "screening kits are bought for a dozen clinical purposes and Titan is a "
            "product name in several industries. Matching either on the supplier's "
            "name instead of the title would admit every notice a diagnostics "
            "distributor ever won. THE SUPPLIER COUNT BELOW IS ONE HIGHER THAN THE "
            "NUMBER OF COMPANIES, AND HERE IS WHY. WS Audiology and Sivantos Limited "
            "are the same firm: Companies House 00203774 was SIEMENS HEARING "
            "INSTRUMENTS LTD, became SIVANTOS LIMITED on 20 March 2015 and has been "
            "WS AUDIOLOGY LIMITED since 29 September 2022. NHS Supply Chain named it "
            "Sivantos Limited on the 2022 hearing aid agreement and WS Audiology on "
            "the 2024 audiological diagnostics agreement, which is correct for the "
            "date each was signed. The Hub's supplier seed still holds the two names "
            "as two separate supplier records, so the alias registry cannot merge "
            "them and the list below shows 25 entries for 24 companies. The names are "
            "published exactly as the procurement record states them; merging the two "
            "seed records is a change to shared supplier data that affects the "
            "compare tab as well as this panel, so it is recorded here rather than "
            "made quietly inside a single speciality build. THE SURGICAL HALF OF EAR "
            "CARE IS NOT HERE: "
            "mastoid, tympanoplasty, grommet and stapes work, the ENT endoscopes "
            "framework and the operating microscopes those procedures use are on the "
            "ENT and head and neck page, which claims them explicitly. This page is "
            "hearing and balance -- assessment, aids, implants, tinnitus and "
            "vestibular."
        ),
    },

    # PAGE 2830. Scope, in the page's own words: a person with a bowel symptom moving
    # through the English NHS, from the GP's quantitative FIT, through the bowel cancer
    # screening programme, into the endoscopy unit, on to theatre, and out to a stoma
    # prescribed on FP10. So this patch is three markets that a rep sells into
    # separately -- the FIT assay in the pathology laboratory, the endoscopy unit's
    # capital, consumables and decontamination, and the community stoma appliance
    # range -- and the rule below has to reach all three without reaching the
    # neighbouring pages that own the surgery, the catheter and the feed.
    "colorectal-gi-and-endoscopy": {
        "label": "Colorectal, GI and Endoscopy",
        # FIVE FRAMEWORKS, AND THEY ARE THE FIVE THE PAGE'S OWN DEEP DIVE NAMES. All
        # 121 framework names in frameworks.json were read for this build, and the
        # page's "The buying route, exactly - five agreements, and one of them is not
        # a framework at all" section is the authority for which five. THIS WAS GOT
        # WRONG ONCE, ON 11/09/2026, AND IS RECORDED RATHER THAN QUIETLY FIXED: a
        # first version of this rule claimed three, having read the page's clinical
        # pathway section and the NHSSC framework names but not the Deep dive, and it
        # published a panel that contradicted the page it sits on. Rigid Endoscopy and
        # Urology and Bowel Management were restored the same night.
        #   "Flexible Endoscopes and Associated Options and Related Services"
        #     (2021/S 000-007768, 1 April 2022 to 31 March 2028) is the scope and
        #     stack: FUJIFILM, Karl Storz, Olympus KeyMed, Pentax and Richard Wolf.
        #     The page states five suppliers and five names parse, but NHS Supply
        #     Chain publishes no total of its own on that brief, so the count is
        #     carried as UNVERIFIED and said so in the coverage note.
        #   "Endoscopy, Endourology and Oncology Ablation Consumables and Associated
        #     Products" (2024/S 000-029975, 1 October 2025 to 30 September 2027, 58
        #     suppliers, eDirect) is every snare, clip, stent, biopsy forceps,
        #     injection needle and suturing device. The reference and the count both
        #     match the page's own sourced statement.
        #   "Rigid Endoscopy and Associated Options and Related Services" is
        #     published under the SAME reference as the flexible scopes, 2021/S
        #     000-007768, with the same start and end dates and the same 72-month term
        #     with both extensions already spent, and the page's Deep dive says so in
        #     terms: "For scopes, 2021/S 000-007768, which covers Flexible Endoscopes
        #     and Rigid Endoscopy under one reference". 18 suppliers. It is claimed
        #     here because the page's sourced statement claims it, and because a
        #     member asking "which framework am I on for scopes" is given one
        #     reference covering both halves.
        #   "Decontamination Capital Equipment, Associated Accessories and Services"
        #     (2024/S 000-017758, 19 February 2025 to 18 February 2027, 20 suppliers)
        #     is the washer-disinfector and the drying cabinet, and specifically its
        #     Lot 1, Endoscopy Decontamination Unit. NHS Supply Chain's own brief URL
        #     for it reads decontamination-capital-equipment-endoscopy-and-sterile-
        #     services, so it is genuinely half this patch and half theatres, and it
        #     is claimed with that shared ownership stated rather than implied.
        #   "Urology and Bowel Management" (2023/S 000-011173, 21 February 2024 to 20
        #     February 2027, 57 suppliers, 18 lots) is the stoma route, and the page
        #     names it as the fifth agreement while saying plainly that most of the
        #     money does not go through it: Lot 10 Bowel and Faecal Management, Lot 11
        #     Enema Accessories, Lot 12 Stoma Appliances, Lot 13 Stoma Accessories,
        #     Lot 14 Wound and Fistula Management and Lot 17 Chyme Infusion Systems
        #     are this patch. The other twelve lots are catheters, sheaths and
        #     containment, which are the continence page's, and that page claims the
        #     same framework for them.
        # DELIBERATELY NOT CLAIMED, each one read and rejected:
        #   "Ear, Nose and Throat (ENT) Endoscopes and Associated Options and Related
        #     Services" -- the ENT and head and neck page claims it explicitly.
        #   "Instrument Decontamination and Accessories" -- surgical instrument
        #     reprocessing and the chemistry that goes with it, which is sterile
        #     services. Endoscope reprocessing firms appear on it (Wassenburg,
        #     Partners for Endoscopy) but the framework is not this patch's, and the
        #     page's buying route names five agreements, not six.
        #   "Enteral Feeding, Bile Bags and Associated Products" -- gastrointestinal
        #     anatomy, but the nutrition and dietetics page's market: feeds, pumps and
        #     giving sets bought by a dietetics service.
        #   "Minimally Invasive Surgery, Related Equipment and Accessories" -- the
        #     laparoscopic resection in step 6 of the pathway is bought against it,
        #     but it is 60 suppliers of ports, staplers and energy devices across
        #     every surgical speciality, and theatres and surgical is where a
        #     cross-cutting framework belongs.
        "frameworks": (
            r"\b(flexible endoscopes?|rigid endoscopy|endoscopy, endourology|"
            r"decontamination capital|urology and bowel)\b"
        ),
        # EVERY MATCH WAS READ, ONE BY ONE. The include below returns 39 rows across
        # the two award feeds after exclusions -- 26 in tender-history.json and 13 in
        # framework-awards.json -- and all 39 are this patch: the NHS Supply Chain
        # endoscopy consumables agreement itself, NHS Scotland's and Northern
        # Ireland's flexible, single-use and capsule endoscopy contracts, seven trust
        # capital purchases of scopes and stacks (Somerset's EVIS X1, United
        # Lincolnshire, Cambridge, King's twice, Kettering twice), four endoscope
        # washer-disinfector and drying cabinet contracts, NHS England's Colon Capsule
        # Endoscopy programme, Southampton's Digestive Disease Centre engagement,
        # three bowel screening and general endoscopy insourcing awards in Wales, one
        # gastroenterology insourcing award in Norfolk, the two NHS Scotland bowel
        # screening FIT kit and analyser contracts, NHS Wales' FIT-for-symptomatic-
        # patients award, and three stoma appliance contracts.
        #
        # WHAT THE FEED'S OWN `spec` FIELD SAYS ABOUT THOSE SAME ROWS, AND WHY IT IS
        # NEVER READ HERE: of the 26 tender-history rows it tags five correctly. It
        # files "Purchase of Flexible Endoscopes" under pharmacy-and-medicines, both
        # Kettering endoscopy awards under primary-care-and-general-practice, the
        # Cantel endoscope washer-disinfector spares under digital-and-medical-it,
        # both "Stoma Acute Patient" awards under cardiology-and-cardiac-surgery, the
        # two NHS Scotland bowel screening FIT contracts under
        # continence-bladder-and-bowel, and NHS Wales' FIT award under critical-care.
        #
        # REFUSED FROM THE INCLUDE, each with what it actually did:
        #   bare "fit"    -> "Supply and Fit including Styling of Wigs Service" and
        #                    "16_26 Flooring (Supply, Fit and Refurbishment)". FIT is
        #                    the single most important test on this patch and the
        #                    single most dangerous three letters in the dataset.
        #                    Admitted only as "fit kits" and "faecal immunochemical",
        #                    which between them catch every genuine row.
        #   bare "bowel"  -> matches six rows today and all six are genuinely this
        #                    page's, so this is a refusal on risk and it is said
        #                    plainly. The NHS Supply Chain framework "Urology and
        #                    Bowel Management" is the continence page's, and the next
        #                    bowel management award to appear would land here on a
        #                    bare pattern. "bowel screening", "bowel cancer" and
        #                    "inflammatory bowel" are admitted instead and nothing is
        #                    lost: all six rows are still caught.
        #   bare "faecal" -> "Faecal Management System" and "Faecal Management
        #                    Systems", both ConvaTec. Faecal management systems are
        #                    bowel containment for a bedbound patient and the
        #                    continence page claims them by name.
        #   bare "scope"  -> "Replacement of Hysteroscopy Scopes" (gynaecology),
        #                    "Scopes Model 11272VH" (a Karl Storz flexible
        #                    cysto-urethroscope, urology) and "Scope Application
        #                    service level agreement", which is a software scoping
        #                    document. "Flexible Scopes", Cambridge University
        #                    Hospitals, carries CPV 33168000 and is very likely this
        #                    patch, and it is still refused: the title cannot say
        #                    whether those scopes are gastroscopes, cystoscopes or
        #                    bronchoscopes, and CPV corroborates but never admits.
        #   bare "polyp"  -> matches nothing today and would match "polypropylene",
        #                    which is surgical mesh and suture. "polypectomy" is
        #                    admitted instead.
        #   bare
        #   "oesophageal" -> refused on risk. "Trans-oesophageal" echocardiography is
        #                    cardiology and a hyphenated spelling would reach it
        #                    through a word boundary. The unambiguous forms --
        #                    oesophagogastric, oesophagectomy, oesophageal stent --
        #                    are admitted.
        #   bare "gastric"-> gastric band and gastric balloon are the obesity and
        #                    weight management page's.
        #   bare
        #   "washer
        #   disinfector"  -> "AA-84-22-MC NP143/21 Instrument Washer Disinfectors",
        #                    which is sterile services, and "Washer Disinfector Units
        #                    Maintenance (202-134 & 202-135)", Aneurin Bevan, whose
        #                    title cannot say whether the units are endoscope, bedpan
        #                    or instrument washers. Both genuine endoscope washer
        #                    contracts in the data say "endoscope" in the title and
        #                    are caught by the endoscopy pattern anyway.
        #   "laparoscopic"-> "Laparoscopic Ligation Clips & Appliers" and "Contract
        #                    for Laparoscopic Sets Service Agreement". Colorectal
        #                    resection is done laparoscopically, but so is every other
        #                    abdominal and pelvic operation, and the laparoscopic
        #                    stack is the theatres page's.
        #   bare "rectal" -> "PROJ007278_Replacement of Trans-Rectal Ultrasound
        #                    Scanner", which is a prostate biopsy probe.
        #   "fibroscan",
        #   "hepatology"  -> real rows (Belfast, Hull, Newcastle, Derby and Burton,
        #                    and a hepatology insourcing award at King's Lynn) and
        #                    real liver medicine. This page's stated scope is the
        #                    bowel symptom pathway, endoscopy and stoma; liver
        #                    fibrosis scanning is not on it and is not claimed.
        "include": (
            r"\b(endoscop\w*|"
            r"colonoscop\w*|gastroscop\w*|sigmoidoscop\w*|proctoscop\w*|"
            r"duodenoscop\w*|enteroscop\w*|colonograph\w*|"
            r"colorectal|colon cancer|bowel cancer|bowel screening|bowel preparation|"
            r"inflammatory bowel|crohn\w*|ulcerative colitis|"
            r"faecal immunochemical|faecal occult|faecal calprotectin|fit kits?|"
            r"gastrointestinal|gastroenterolog\w*|digestive disease|"
            r"stomas?|colostom\w*|ileostom\w*|ostomy|"
            r"polypectom\w*|adenoma detection|"
            r"oesophagogastr\w*|oesophagectom\w*|oesophageal stent\w*|"
            r"haemorrhoid\w*|anal fistula|proctolog\w*)\b"
        ),
        # FOUR PATTERNS. Three of them removed a row that is not this speciality; the
        # fourth removed a row nobody can attribute from its title. That difference is
        # written out in excludeFinding below rather than glossed.
        #   vessel harvesting -> two NHS Golden Jubilee awards, "Endoscopic Vessel
        #                        Harvesting Tools and Associated Consumables"
        #                        (Getinge) and the display monitor for the same system
        #                        (CardioPrecision). Endoscopic saphenous vein
        #                        harvesting for coronary artery bypass grafting. That
        #                        is cardiac surgery.
        #   craniofacial      -> "Pre-Market Engagement for Craniofacial Orthotics and
        #                        Helmet Therapy Services for Endoscopic-Assisted
        #                        Suturectomy Patients", Birmingham Women's and
        #                        Children's. Infant craniosynostosis surgery and the
        #                        moulding helmets worn afterwards.
        #   medicines         -> "Gastrointestinal, Endocrine, Nutrition & Blood
        #                        Medicines", NHS Scotland, awarded to Kent
        #                        Pharmaceuticals. Genuinely gastrointestinal, and
        #                        genuinely not this panel: it is one pharmacy
        #                        wholesale award covering four therapeutic areas at
        #                        once, and publishing it here would tell a rep that a
        #                        medicines supply contract is an endoscopy
        #                        opportunity. The page's own market intelligence
        #                        sizes GI prescribing separately, so nothing is lost.
        #   transnasal        -> "Purchase of transnasal endoscopes and accessories",
        #                        Somerset, from Aquilant Endoscopy. Transnasal
        #                        endoscopy means unsedated upper GI endoscopy through
        #                        the nose on this patch and a flexible nasendoscope on
        #                        the ENT patch, and Aquilant supplies both. Refused
        #                        because the title cannot settle it, not because it
        #                        was shown to be ENT.
        # NHS SCOTLAND'S STANDALONE "Rigid Endoscopy Equipment, Accessories and
        # Maintenance and Repair" IS ADMITTED, AND THE FIRST VERSION OF THIS RULE
        # EXCLUDED IT. It was excluded on the argument that rigid endoscopy is
        # arthroscopy and laparoscopy, which is true of part of it -- Arthrex and
        # Smith & Nephew are on the NHSSC framework of that name. It is admitted now
        # because this rule claims the Rigid Endoscopy framework, on the page's own
        # sourced statement, and a panel cannot publish that framework as this
        # patch's scope route in one tab and refuse an award for the same equipment
        # in the next. The honest position is one position, and it is this one.
        "exclude": r"\b(vessel harvesting|craniofacial|medicines|transnasal)\b",
        "excludeFinding": (
            "THREE OF THE FOUR EXCLUSION PATTERNS IN THAT RULE REMOVED A NOTICE "
            "THAT IS NOT THIS SPECIALITY: two endoscopic vessel harvesting awards "
            "that are cardiac surgery, a craniofacial helmet therapy engagement that "
            "is infant neurosurgery, and a pharmacy wholesale award covering four "
            "therapeutic areas of which gastrointestinal medicines is one. The "
            "fourth is different and is said plainly rather than counted with them: "
            "\"transnasal\" removed Somerset NHS Foundation Trust's purchase of "
            "transnasal endoscopes, which is either unsedated upper gastrointestinal "
            "endoscopy, which is this patch, or ENT nasendoscopy, which is not, and "
            "the title cannot settle which. It is refused because it could not be "
            "attributed, not because it was shown to be wrong. NOTHING IS EXCLUDED "
            "FOR BEING RIGID RATHER THAN FLEXIBLE ENDOSCOPY: this patch's scope "
            "route is one NHS Supply Chain reference covering both, so both reach "
            "this panel."
        ),
        # THE TWO ENDOSCOPY CPV CODES, AND THEY CORROBORATE ONLY. 33168000 is
        # endoscopy and endosurgery devices and 33168100 is endoscopes. Across the
        # whole award feed the 33168 family sits on six notices, and two of them are
        # "Total Orthopaedic Solutions 4" and "Minimally Invasive Surgery" -- an
        # orthopaedic implant framework and a general laparoscopy framework. Admitted
        # on CPV, this panel would open with an orthopaedic solutions award.
        "cpv": ("33168",),
        # PART IXC ONLY, AND THE COUNT CORROBORATES THE PAGE. Part IXC is stoma
        # appliances: 8,218 lines from 68 suppliers in the September 2026 tariff, and
        # 68 is the same supplier count the page's own market intelligence section
        # states for the £433.5m a year England spend. Coloplast, AMI Medical, Marlen,
        # Nu-Hope, CUI, Salts, Dansac, ConvaTec, Unora and Pelican lead it on line
        # count. NOT IXA, which is dressings and elastic hosiery; NOT IXB, which is
        # incontinence appliances and belongs to the continence page; and NOT the
        # literal part "IXB & IXC", whose six lines are Manfred Sauer catheter
        # products, which are continence's and not stoma at all.
        "tariffParts": ("IXC",),
        "coverageNote": (
            "COVERAGE LIMITS, STATED RATHER THAN HIDDEN. THE FIVE AGREEMENTS BELOW "
            "ARE THE FIVE THIS PAGE'S OWN DEEP DIVE NAMES AS THE BUYING ROUTE, AND "
            "TWO OF THEM ARE SHARED WITH A NEIGHBOURING PAGE. Decontamination "
            "Capital Equipment covers endoscopy decontamination and sterile services "
            "together, which is NHS Supply Chain's own scoping and not the Hub's: "
            "its brief URL reads decontamination-capital-equipment-endoscopy-and-"
            "sterile-services, and only its Lot 1, Endoscopy Decontamination Unit, "
            "is this patch. Urology and Bowel Management carries 18 lots and six of "
            "them are this patch -- Bowel and Faecal Management, Enema Accessories, "
            "Stoma Appliances, Stoma Accessories, Wound and Fistula Management and "
            "Chyme Infusion Systems. The other twelve are catheters, sheaths and "
            "containment, and the continence, bladder and bowel page claims the same "
            "framework for those. So a supplier named below may be on it for a "
            "product this page never sells: read the lot, not the membership. ONE "
            "SUPPLIER COUNT IS UNVERIFIED. NHS Supply Chain publishes no supplier "
            "total on the Flexible Endoscopes brief, so its five names are the five "
            "the Hub's crawler parsed and nothing confirms five is all of them; the "
            "same is true of Rigid Endoscopy's 18. Endoscopy, Endourology and "
            "Oncology Ablation Consumables (58), Decontamination Capital Equipment "
            "(20) and Urology and Bowel Management (57) all state their own totals "
            "and all three match. THE CONTRACT DATES MATTER MORE HERE THAN ON MOST "
            "PAGES. Urology and Bowel Management ends 20 February 2027, "
            "Decontamination Capital Equipment 18 February 2027 and Endoscopy, "
            "Endourology and Oncology Ablation Consumables 30 September 2027, and "
            "the two scope agreements share one reference, 2021/S 000-007768, and "
            "both end 31 March 2028 with both extensions already spent. No successor "
            "to any of them has been awarded, so none is in the Hub's framework "
            "dataset and none can be. Being named below is a statement about the "
            "current agreements only. TWO OF THE AWARDS BELOW ARE MULTI-SPECIALITY "
            "BASKETS and are included because endoscopy is named in the title, not "
            "because the whole award is this patch: NHS Wales' \"Interventional "
            "Cardiology, Radiology, Endoscopy and Surgical Urology Consumables\" and "
            "NHS Supply Chain's \"Imaging, Radiotherapy and Endoscopy Equipment\". "
            "Read them as a route in, not as an endoscopy contract value. THE STOMA "
            "ROWS APPEAR ON TWO PAGES ON PURPOSE. Stoma appliances are step 7 of "
            "this page's pathway and the largest single budget on it, and they are "
            "also containment, which is the continence page's patch. Both pages "
            "claim Part IXC and the three stoma award rows, in the same way Pressure "
            "Area Care is shared between wound care and patient handling. WHAT IS "
            "NOT HERE: the FIT assays NICE names in NG12 are bought by pathology "
            "laboratories on pathology's own managed service route and only three "
            "FIT contracts reach the award feeds at all; the theatre products in "
            "step 6 -- staplers, energy devices, ports, colonic stents, robotic "
            "consumables -- are on the theatres and surgical page's frameworks; the "
            "AI polyp detection boxes NICE names in HTG514 have no framework at all "
            "and are a trust-level licence, so no panel can carry them; and liver "
            "disease and enteral feeding are the hepatology and nutrition patches "
            "and are not claimed."
        ),
    },

    # PAGE 2925. Outpatient dermatology, teledermatology and the topical prescribing
    # bill. THIS IS THE FIRST SPECIALITY WHOSE FRAMEWORK ANSWER IS "NONE, AND HERE ARE
    # THE TWO LOTS INSTEAD", and the whole rule turns on that being said accurately.
    "dermatology": {
        "label": "Dermatology",
        # NO FRAMEWORK IS CLAIMED, AND IT IS NOT BECAUSE NOTHING TOUCHES THE PATCH.
        # NHS Supply Chain's own site search, run 11/09/2026, returns "No results found
        # for 'dermatology'". All 121 parsed framework names and all 16 unparsed ones
        # were read and not one is named for this speciality. Two agreements do carry a
        # dermatology lot and both are named in frameworksFinding below with their
        # reference, dates and lot, verified against NHS Supply Chain's own briefs on
        # 11/09/2026:
        #   Total Patient Assessment Device Solutions (2025/S 000-032216, 4 August 2026
        #     to 3 August 2028, 40 suppliers, option to extend 24 months). NHS Supply
        #     Chain's site search for "dermatoscope" returns this agreement and nothing
        #     else. Five lots: 1 blood pressure monitors and cuffs, 2 thermometers,
        #     3 patient weighing, 4 Patient Assessment Devices and Kits, 5 personal
        #     health monitors.
        #   Anaesthesia Machines, Ventilators, Neonatal Equipment and Phototherapy
        #     Systems (2026/S 000-008108, 2 March 2026 to 28 February 2029, 25
        #     suppliers), whose Lot 4 is named on the brief, verbatim, "Adult and
        #     Paediatric Phototherapy Devices". Adult phototherapy is narrowband UVB
        #     and PUVA, which is this patch; Lot 3 is neonatal jaundice equipment,
        #     which is maternity and neonatal's and is claimed there.
        # NEITHER IS CLAIMED AS A FRAMEWORK HERE, and the reason is the supplier list,
        # not the lot. frameworks.json records supplier names at AGREEMENT level, never
        # at lot level, because that is how NHS Supply Chain publishes them. Claiming
        # either agreement would put its whole list into the Suppliers tab: 40 names
        # from the first, which is Seca and Marsden weighing scales, AliveCor ECG and
        # Welch Allyn thermometers, and 25 from the second, which is Draeger, Penlon and
        # Hamilton ventilators and Atom and mOm incubators. That would tell a rep that
        # sixty-odd firms are the dermatology market. They are not, and an honest empty
        # state with both references and both lot names written into it is worth more.
        "frameworks": None,
        "frameworksFinding": {
            "frameworks": (
                "NO NHS SUPPLY CHAIN FRAMEWORK IS COUNTED HERE, AND THAT IS THE FINDING "
                "RATHER THAN A GAP. NHS Supply Chain's own website search returns \"No "
                "results found for 'dermatology'\", run 11 September 2026, and no one of "
                "the 121 framework names in the Hub's record is this speciality's. TWO "
                "AGREEMENTS DO CARRY A DERMATOLOGY LOT AND BOTH ARE NAMED HERE RATHER "
                "THAN COUNTED. Total Patient Assessment Device Solutions, 2025/S "
                "000-032216, 4 August 2026 to 3 August 2028, 40 suppliers, with an "
                "option to extend 24 months to 3 August 2030: NHS Supply Chain's site "
                "search for \"dermatoscope\" returns this agreement and no other. Its "
                "five lots are blood pressure monitors and cuffs, thermometers, patient "
                "weighing, Patient Assessment Devices and Kits, and personal health "
                "monitors; the lot a dermatoscope sits in is not stated anywhere on the "
                "public brief, because the product listing is in the Framework Matrices "
                "download, so Lot 4 is the lot whose NAME covers it and that is a "
                "reading, not a sourced statement. And Anaesthesia Machines, "
                "Ventilators, Neonatal Equipment and Phototherapy Systems, 2026/S "
                "000-008108, 2 March 2026 to 28 February 2029, 25 suppliers, whose Lot 4 "
                "the brief names verbatim as \"Adult and Paediatric Phototherapy "
                "Devices\" - adult phototherapy being narrowband UVB and PUVA, which is "
                "this patch, while Lot 3 neonatal equipment is the maternity and "
                "neonatal page's. WHY NEITHER IS COUNTED: NHS Supply Chain publishes "
                "supplier names per agreement and never per lot, so claiming either "
                "would publish its whole list as this speciality's market - weighing "
                "scales, thermometers and ECG from the first, ventilators and incubators "
                "from the second. Both references are given above so a rep can go "
                "straight to the right agreement. Every date, reference and count in "
                "this paragraph was read on NHS Supply Chain's own brief on 11 September "
                "2026."
            ),
            "suppliers": (
                "NO SUPPLIER LIST IS PUBLISHED FOR THIS SPECIALITY FROM THE FRAMEWORK "
                "ROUTE, because this panel names suppliers only where a framework record "
                "names them on this speciality's own frameworks, and this patch has "
                "none. The two agreements carrying a dermatology lot are named in the "
                "frameworks rule above, and their supplier lists are not reproduced "
                "here: both are published per agreement rather than per lot, so a list "
                "of forty patient assessment device suppliers or twenty-five anaesthesia "
                "and neonatal suppliers would name the wrong market. THE SUPPLIER "
                "ANSWER ON THIS PATCH IS THE DRUG TARIFF, NOT A FRAMEWORK. The "
                "reimbursed emollient range below names nineteen companies and they are "
                "the firms a dermatology conversation is actually had with. This panel "
                "will not fall back to a keyword guess against the supplier directory."
            ),
        },
        # EVERY MATCH WAS READ, ONE BY ONE, AND THERE ARE THIRTEEN. Ten in
        # framework-awards.json and three in tender-history.json, and all thirteen are
        # this speciality. NINE are commissioned community dermatology or teledermatology
        # services: Royal Wolverhampton (Medinet Clinical Services), North East London
        # twice, St George's (Cryotomy), Greater Manchester twice (Health Harmonie and
        # About Health), West Yorkshire twice, and Lancashire and South Cumbria's adult
        # teledermatology service. The two West Yorkshire rows are NOT one notice
        # published twice: they carry the same title and the same day and they were
        # awarded to different providers, Novus Health and DMC Healthcare, so both are
        # real and both stand. The remaining four are NHS Essex's urgent skin cancer
        # dermoscopy triage service (Mayflower Healthcare Alliance), NHS Scotland's ENT,
        # Ophthalmology and Skin Medicines contract twice, and Calderdale and
        # Huddersfield's purchase of dermatoscopes and an image transfer system.
        #
        # WHAT THE FEED'S OWN `spec` FIELD SAYS ABOUT THE SAME PATCH, AND WHY IT IS
        # NEVER READ HERE: it tags five rows dermatology and not one of the five is.
        # They are "Intravenous & Topical Fluids" (IV fluids), "Hair and Beauty
        # Framework" (APUC, a further education college beauty supplies agreement),
        # "Microbiological Safety Cabinets", "National Framework Agreement for Non-Wire
        # Lesion Localisation and Sentinel Lymph Node Location Products" (breast) and
        # "Supply of Wigs". Meanwhile it files the three genuine tender-history rows
        # under capital-estates-watch and theatres-and-surgical. Five for five wrong in,
        # three for three wrong out.
        #
        # REFUSED FROM THE INCLUDE, each with what it actually did. Every loose term
        # was refused here rather than admitted and then argued with in an exclusion
        # list, which is why `exclude` below is None.
        #   bare "skin"       -> "Skin Cleansing, Disinfection and Hygiene" (the NHS
        #                        Supply Chain hand hygiene and patient wash agreement,
        #                        which is infection prevention's) and "Cryopreserved
        #                        Skin - Cryoskin", Swansea Bay, three rows, which is
        #                        cadaveric skin allograft for burns and is the plastics,
        #                        burns and reconstruction page's by name. Admitted only
        #                        as "skin cancer", "skin lesion" and "skin medicines".
        #   bare
        #   "phototherapy"    -> the only phototherapy row in either feed is "Neonatal
        #                        Equipment, Adult, Paediatric & Neonatal Phototherapy
        #                        Devices and Associated Accessories & Services", NHS
        #                        Supply Chain 2021, the predecessor of 2026/S 000-008108.
        #                        Its adult lot is genuinely this patch, and admitting the
        #                        word to reach it would open a dermatology panel with a
        #                        neonatal incubator and ventilator award. The current
        #                        agreement and its Lot 4 are named in the frameworks
        #                        finding above instead, which is where a rep needs them.
        #                        Only "narrowband UVB" and "PUVA" are admitted, and
        #                        neither matches anything today.
        #   bare "laser"      -> eighteen rows and not one is dermatology: ENT, holmium
        #                        urology, green light prostate, ophthalmic Pascal,
        #                        cardiac lead extraction, MRI-guided ablation and two
        #                        university microdissection systems. Two are arguable and
        #                        both are refused because the title cannot settle them -
        #                        "POS Broomfield - Candela - laser GMAX PRO", a Candela
        #                        GentleMax Pro at Mid and South Essex, which is a
        #                        dermatology and aesthetic platform sited at a burns
        #                        centre, and two Lumenis AcuPulse CO2 laser maintenance
        #                        contracts, which serve ENT and dermatology alike.
        #   bare "wig"        -> nine rows, and wigs are refused DELIBERATELY and against
        #                        the pull of the clinical argument. Most NHS wig
        #                        provision is for chemotherapy alopecia, which is
        #                        oncology's, and the page above states in terms that the
        #                        NHS Supply Chain wigs agreement is not a dermatology
        #                        agreement. A panel cannot say that on the page and then
        #                        claim nine wig awards in the tab beneath it. "alopecia"
        #                        is admitted instead, which reaches an alopecia-specific
        #                        notice if one ever appears and matches nothing today.
        #   bare "hair"       -> "Hair, Beauty and Wigs Supplies" (Crescent Purchasing
        #                        Consortium, a schools and colleges buying group) and
        #                        "Hair and Beauty Framework" (APUC). Also matches
        #                        "chair" inside "wheelchair" on twenty-five rows without
        #                        a word boundary, which is its own warning.
        #   bare "topical"    -> "Intravenous & Topical Fluids", which is IV fluid
        #                        therapy, and "Generic Drugs - Topicals & Miscellaneous",
        #                        a Velindre and NHS Wales generic pharmacy basket.
        #                        Topical prescribing is the whole of this patch's budget
        #                        and the word is still refused, because in procurement
        #                        titles it means route of administration and not skin.
        #   bare "lesion"     -> "National Framework Agreement for Non-Wire Lesion
        #                        Localisation and Sentinel Lymph Node Location Products",
        #                        which is breast surgery. "skin lesion" is admitted.
        #   bare
        #   "squamous cell"   -> refused on risk: it matches nothing today, and head and
        #                        neck, lung and cervical squamous cell carcinoma would
        #                        all reach it. Only "cutaneous squamous cell" is
        #                        admitted, which is the form NICE uses for the cemiplimab
        #                        appraisal this page's calendar carries.
        #   bare "cryo"       -> ten rows and every one is cryoablation, cryopreservation
        #                        or a pathology cryostat. Dermatological cryotherapy is a
        #                        clinic procedure bought as a nitrogen flask, and it does
        #                        not reach a procurement notice at all.
        #   bare "sunscreen"  -> two rows, both Leidos Supply Limited, which runs Ministry
        #                        of Defence logistics. Not an NHS purchase.
        #   bare "biopsy"     -> six rows, all breast or transperineal prostate. Skin
        #                        punch biopsy is a consumable on a general surgical
        #                        agreement and never appears in a title.
        # ADMITTED ON PURPOSE THOUGH IT IS A THREE-SPECIALITY BASKET: NHS Scotland's
        # "ENT, Ophthalmology & Skin Medicines/Medical Devices", 2022 and 2024. The
        # colorectal rule refuses the equivalent shape - "Gastrointestinal, Endocrine,
        # Nutrition & Blood Medicines" - and the difference is stated rather than
        # glossed. There, a medicines wholesale award is not an endoscopy opportunity,
        # because that page's market is devices and it sizes GI prescribing separately.
        # Here the medicines ARE the market: this page's own strap says the money runs
        # through FP10 and ICB formularies, and a national contract for skin medicines
        # is the single clearest route to market on the patch. It is admitted with its
        # scope stated in the coverage note, not passed off as a dermatology contract.
        "include": (
            r"\b((?:tele)?dermatolog\w*|dermatoscop\w*|dermoscop\w*|"
            r"skin cancer|skin lesion\w*|skin medicines|"
            r"melanoma|basal cell carcinoma|cutaneous squamous cell|mohs|"
            r"psoria\w*|eczema|atopic dermatitis|dermatitis|acne|rosacea|urticaria|"
            r"hidradenitis|vitiligo|prurigo|pruritus|pemphig\w*|"
            r"epidermolysis bullosa|ichthyos\w*|alopecia|actinic keratos\w*|"
            r"emollient\w*|isotretinoin|narrowband uvb|narrow[- ]band uvb|puva)\b"
        ),
        # NOTHING TO EXCLUDE, AND THAT IS A STATEMENT ABOUT THE INCLUDE LIST BEING
        # NARROW ENOUGH, NEVER A SHORTCUT PAST THE READING. All thirteen rows the
        # pattern returns were read one by one and all thirteen are dermatology. The
        # eleven loose terms that would have needed an exclusion list are enumerated
        # above and were refused from the include instead, which is the renal rule's
        # discipline and the one this page needs most: "skin" alone is the third most
        # dangerous word in this dataset after "fit" and "delivery".
        "exclude": None,
        # 85121282 IS "DERMATOLOGY SERVICES" AND IT IS THE CLEANEST CPV ON THE HUB, AND
        # IT STILL ONLY CORROBORATES. Twelve notices in the award feed carry it. Ten are
        # the community dermatology and skin cancer rows below, every one of which the
        # title already admitted. The other two are "NHSE1060 Diabetic Eye Screening
        # Programme", which carries 85121280, 85121281 and 85121282 as a block of
        # specialist medical service codes, and Countess of Chester's "Provision of
        # Insourced and Outsourced Clinical Services Framework", which carries
        # twenty-five CPV codes covering every speciality in the NHS. Admitted on CPV
        # alone, this panel would open with a diabetic eye screening contract.
        "cpv": ("85121282",),
        # PART IXA, NARROWED TO THE EMOLLIENT RANGE, AND THE NARROWING IS THE POINT.
        # Part IXA whole is 56,833 lines of dressings and elastic hosiery and belongs to
        # the tissue viability page, which claims it whole. Inside it sit 87 lines from
        # 28 virtual medicinal products and 19 companies which are emollients: the
        # reimbursed creams, ointments, gels and bath additives that are the largest
        # single line in the dermatology prescribing bill this page is about. Claiming
        # the part whole would have put Juzo and Sigvaris compression hosiery at the top
        # of a dermatology panel, which is the gynaecology pessary problem exactly.
        # Thornton & Ross leads on 25 lines (Cetraben, Zerobase, Zeroderm, Zerocream,
        # Zerolatum, Flexitol), then Alliance Pharmaceuticals and Ennogen on 8, Aspire
        # on 7, Fontus on 6 and Dermatonics on 5. Reimbursement runs £1.12 to £15.77.
        # WHAT THE PATTERN DELIBERATELY DOES NOT REACH:
        #   "Paraffin gauze dressing sterile" (Jelonet, Cuticell, Neotulle, Zelaffin) is
        #     a wound contact layer, not an emollient, which is why bare "paraffin" is
        #     not used and only "white/yellow soft paraffin" and "liquid paraffin" are.
        #   "Ostomy skin protectives", the 55-line Part IXC barrier cream and barrier
        #     film range, is stoma peristomal skin care and is the continence and
        #     colorectal pages'. Only IXA is claimed, so it cannot reach this panel.
        #   "Silicone gel sheet" (Dermatix) is scar management and is the plastics,
        #     burns and reconstruction page's.
        #   "Vaginal moisturisers" (Regelle) is gynaecology's.
        #   "Cyclomethicone 50% / Isopropyl myristate 50% solution" is Full Marks head
        #     lice solution, and it is the one line refused that has a real dermatology
        #     argument: pediculosis is a skin infestation and the product is on the
        #     topical prescribing bill. It is refused because this slice is described as
        #     the emollient range and one ectoparasiticide inside it would misdescribe
        #     what is being counted. "isopropyl myristate" was dropped from the pattern
        #     to achieve it, and nothing else was lost: every AproDerm, Epimax isomol,
        #     Exmabase, MyriBase and Zerodouble gel line is still reached through
        #     "liquid paraffin".
        #   "Curea P1 / P2 dressing" is a wound dressing, and it is named here because
        #     it is the trap an unanchored pattern falls into: "Curea" ends in the
        #     letters u-r-e-a, so a bare "urea" matches all thirteen of its lines. The
        #     pattern uses "\burea \d" - word boundary, then a percentage.
        "tariffParts": ("IXA",),
        "tariffVmp": (
            r"emollient|emulsifying wax|"
            r"(?:white|yellow) soft paraffin|liquid paraffin|paraffin-free|"
            r"\burea \d|lauromacrogols|"
            r"eczema|dry skin balm|heel balm|hand balm|skin balm|callus removing"
        ),
        "coverageNote": (
            "COVERAGE LIMITS, STATED RATHER THAN HIDDEN. THIS IS A PATCH WITH NO "
            "FRAMEWORK AND THEREFORE NO FRAMEWORK SUPPLIER LIST, AND THE EMPTY "
            "FRAMEWORKS AND SUPPLIERS SECTIONS ARE THE ANSWER, NOT A FAILURE TO LOAD. "
            "NHS Supply Chain's own site search returns no results at all for "
            "'dermatology', run 11 September 2026, and its Procurement Calendar carries "
            "no dermatology row. The two agreements that do carry a dermatology lot are "
            "named in full in the frameworks rule, with their references, dates and lot "
            "names, so a rep can go to the right agreement without this panel "
            "publishing sixty-five suppliers of thermometers, weighing scales and "
            "ventilators as a dermatology market. THE AWARDS BELOW ARE SERVICE "
            "CONTRACTS, NOT PRODUCT CONTRACTS, AND THAT IS WHAT THIS MARKET LOOKS LIKE. "
            "Nine of the thirteen are Integrated Care Board and trust commissioning of "
            "community dermatology and teledermatology services - Royal Wolverhampton, "
            "North East London, St George's, Greater Manchester, West Yorkshire, "
            "Lancashire and South Cumbria - and one is NHS Essex's urgent skin cancer "
            "dermoscopy triage service. A product supplier's route into those is the "
            "provider who won them, not the notice. Only one award in the whole feed is "
            "a dermatology product purchase: Calderdale and Huddersfield's dermatoscopes "
            "and image transfer system, and it was published in 2021. TWO AWARDS ARE A "
            "THREE-SPECIALITY MEDICINES BASKET and are included because skin is named in "
            "the title, not because the whole award is this patch: NHS National Services "
            "Scotland's 'ENT, Ophthalmology & Skin Medicines/Medical Devices', 2022 and "
            "2024. Read them as a route in, not as a dermatology contract value. THE "
            "DRUG TARIFF SLICE IS EMOLLIENTS AND NOTHING ELSE. It is the reimbursed "
            "emollient range inside Part IXA and it is the honest supplier list for this "
            "patch, but it is not the whole dermatology prescribing bill: topical "
            "corticosteroids, topical retinoids, antifungals, isotretinoin and every "
            "biologic NICE has appraised for atopic dermatitis, psoriasis, prurigo "
            "nodularis and hidradenitis suppurativa are Part VIII medicines, not Part IX "
            "appliances, and no part of the Drug Tariff in this dataset carries them. "
            "THESE 87 LINES ALSO SIT INSIDE THE PART IXA TOTAL THE TISSUE VIABILITY AND "
            "WOUND CARE PAGE CARRIES WHOLE, which is stated so nobody reads the two "
            "panels as counting different things. WHAT IS NOT HERE: wigs, which most "
            "often serve chemotherapy alopecia and which NHS Supply Chain buys under an "
            "agreement this page states is not a dermatology agreement; systemic "
            "melanoma and cutaneous squamous cell carcinoma therapy, which is the "
            "oncology patch; skin graft, skin substitute and cryopreserved allograft, "
            "which are plastics, burns and reconstruction's; peristomal barrier creams, "
            "which are Part IXC and the stoma pages'; skin cleansing and disinfection, "
            "which is infection prevention's; and the AI skin lesion triage NICE names "
            "in HTG746, which is a per-referral licence bought by an individual "
            "teledermatology service and has no framework at all, so no panel can carry "
            "it."
        ),
    },

    # PAGE 2914. Scope, in the page's own words: the chain of precautions applied to
    # every patient all the time, and the escalation chain for when one of them fails.
    # Consumables (gloves, aprons, masks, gowns, hand hygiene, skin cleansing, wipes),
    # decontamination (instrument, endoscope, environmental and the capital equipment
    # behind them), waste (clinical and sharps), and the cleaning and washroom range
    # that Estates and Facilities buys. NOT antibiotics, NOT microbiology diagnostics,
    # NOT the national screening programmes.
    #
    # THE STRUCTURAL FACT THIS RULE HAS TO COPE WITH, published on the page itself:
    # NHS Supply Chain has NO infection prevention category. Twenty national agreements
    # govern this patch and they are filed under three unrelated categories - Medical
    # and Surgical Consumables, Facilities and Office Solutions, and Diagnostic
    # Equipment and Services. More frameworks than any other speciality in this Hub,
    # and no single search at NHS Supply Chain finds them. The `frameworks` pattern
    # below therefore names the subjects, not a category, and was checked to return
    # exactly sixteen and no stray.
    "infection-prevention-and-control": {
        "label": "Infection Prevention and Control",
        # SIXTEEN of the twenty. Checked against every name in frameworks.json: the
        # pattern returns these sixteen and nothing else.
        #   Cleaning Equipment, Supplies and Associated Products
        #   Clinical and Sharps Waste Management
        #   Curtains, Blinds and Associated Services
        #   Decontamination Capital Equipment, Associated Accessories and Services
        #   Environmental Decontamination
        #   Examination Gloves
        #   Hand Hygiene and Associated Products and Services
        #   Instrument Decontamination and Accessories
        #   Medical Pulp, Macerators and Support Products
        #   Paper Hygiene
        #   Polymer Aprons
        #   Reusable Clinical and Sharps Waste Management Service
        #   Skin Cleansing, Disinfection and Hygiene
        #   Surgical Gloves
        #   Tray Wrap and Sterilisation Equipment
        #   Wipes for Surface Cleaning and Disinfection
        # THE OTHER FOUR ARE NOT LOST AND NOT DENIED. They are in frameworks.json's
        # `unparsed` block, which build_frameworks cannot read, and they are named with
        # their references in the coverage note below rather than left to look like
        # they do not exist.
        "frameworks": (
            r"\b(gloves?|hand hygiene|skin cleansing|paper hygiene|polymer aprons|"
            r"tray wrap|wipes for surface|cleaning equipment|environmental decontamination|"
            r"instrument decontamination|decontamination capital|sharps waste|curtains|"
            r"macerators)\b"
        ),
        # NOT INCLUDED, DELIBERATELY. Each of these was run over all 1,972 rows of
        # tender-history.json and all 1,474 of framework-awards.json, every hit was
        # read, and the term was REFUSED in the include rather than admitted and then
        # argued with in the exclusion list (root rule 14, and the renal and therapies
        # precedent above):
        #   autoclave        -> 11 hits, 9 of them research and teaching laboratory
        #                       autoclaves: University of Hertfordshire three times,
        #                       Glasgow's CL3 containment autoclave, Leeds, Warwick,
        #                       Quadram Institute Bioscience, UKRI, the Pirbright
        #                       Institute, an Aberystwyth scientific-equipment DPS.
        #                       Bare "Autoclave 2024" carries nothing in the title to
        #                       separate a university lab from a sterile services
        #                       department, so the term is refused whole. The cost is
        #                       named in the coverage note: two genuine NHS rows go
        #                       with it.
        #   antimicrobial    -> every hit was a MEDICINE or a LABORATORY ASSAY, not an
        #                       infection prevention product: NHS England's antibiotic
        #                       subscription model twice, its evaluation notice, and
        #                       antimicrobial susceptibility diffusion discs.
        #   ppe / personal protective equipment
        #                    -> as a bare term it is workwear. Orbit Group (a housing
        #                       association), Kent County Council, Derbyshire County
        #                       Council, Scotland Excel and a London borough all buy
        #                       "PPE" that is hi-vis, boots and first aid. Nothing
        #                       genuine is lost: every clinical PPE row here is caught
        #                       by its garment - glove, apron, gown, mask.
        #   paper hygiene    -> 9 hits, 7 of them schools and councils buying toilet
        #                       tissue and washroom dispensers (Education Authority NI
        #                       four times, ESPO twice, YPO, East Riding of Yorkshire).
        #                       The framework IS this patch's and appears in the
        #                       frameworks list above; its AWARD titles cannot be told
        #                       apart from a school's toilet roll contract on the title.
        #   hand sanitiser   -> 6 hits, 3 of them Education Authority NI and Sport NI.
        #                       "Supply and Delivery of Hand Sanitiser and Dispensers"
        #                       carries nothing to separate a school from a ward. The
        #                       NHS rows are all 2020 emergency pandemic buys and the
        #                       procurement term this patch actually uses, hand hygiene,
        #                       is included.
        #   screening, swab  -> the national screening programmes (bowel, newborn, eye,
        #                       lung, TB, vision) and microbiology consumables. Neither
        #                       is infection prevention.
        #   infection (bare) -> acute respiratory infection winter services and latent
        #                       TB screening. "infection prevention" and "infection
        #                       control" are included instead.
        #   pest control, laundry, legionella, water safety
        #                    -> all real, all Estates and Facilities, and none of them
        #                       one of the twenty agreements. Named in the coverage note
        #                       rather than swept in to make the panel look fuller.
        "include": (
            r"\b(infection prevention|infection control|hand hygiene|handrub\w*|"
            r"gloves?|aprons?|gowns?|facemasks?|face masks?|surgical masks?|type iir|"
            r"ffp2|ffp3|single use personal protective equipment|"
            r"medical protective consumables|theatre wear|theatre protective wear|"
            r"decontaminat\w*|sterilis\w*|steriliz\w*|washer disinfect\w*|"
            r"washer.disinfectors?|disinfect\w*|sterile services|tray wrap|"
            r"skin cleansing|chlorhexidine|povidone iodine|wipes?|clinical waste|"
            r"sharps|healthcare waste|macerators?|medical pulp|cleaning|curtains?|"
            r"mrsa|clostridi\w*|carbapenemase|norovirus|"
            r"healthcare.associated infection|hospital.acquired infection|hcai|"
            r"surgical site infection|hydrogen peroxide|ultraviolet)\b"
        ),
        # EVERY PATTERN HERE MATCHED A REAL NOTICE THAT WAS NOT THIS SPECIALITY:
        #   first aid        -> Kent County Council's "First Aid Consumables, Equipment
        #                       and Disposable Gloves" and "First Aid Equipment,
        #                       Disposable Gloves, PPE and Workwear". A first aid box,
        #                       not a ward.
        #   workwear         -> the same two, and Scotland Excel's PPE and workwear
        #                       framework. Safety clothing for staff, not barrier
        #                       precautions for patients.
        #   janitorial       -> "CLEANING MATERIALS & JANITORIAL SUPPLIES", Fusion
        #                       School Services Limited. A schools catering and cleaning
        #                       contractor.
        #   fuel tank        -> "WHHT - Specialist Fuel Tank Cleaning & Scaffolding".
        #                       An estates job that shares one word with this patch.
        #   asbestos         -> "WHHT - Emergency DCU Supply and Plant Room Asbestos
        #                       Decontamination Services". Decontamination of a plant
        #                       room, not of an instrument.
        #   radiation        -> "Supply of Radiation Gloves", Hull University Teaching
        #                       Hospitals. Lead-equivalent radiology protection.
        #   shroud           -> "Multi-Purpose Butterfly Sleeve Gown/Shroud", Shrewsbury
        #                       and Telford. Patient and mortuary wear, not PPE.
        #   shower curtain   -> "Shower Curtains & Brackets", the same trust. A washroom
        #                       fitting, not the antimicrobial cubicle curtain range the
        #                       Curtains, Blinds framework lets.
        #   reagent          -> "Cepheid Cov2/FLU/RSV/MRSA Reagents", Cambridge
        #                       University Hospitals. A molecular respiratory panel
        #                       bought by pathology.
        #   isolator         -> "Integrated Vapour Hydrogen Peroxide (VHP)-Isolator
        #                       Module", Newcastle. A pharmacy aseptic isolator. VHP is
        #                       this patch's environmental decontamination technology,
        #                       but an isolator module is pharmacy's cabinet.
        "exclude": (
            r"\b(first aid|workwear|janitorial|fuel tank|asbestos|radiation|shrouds?|"
            r"shower curtains?|reagents?|isolator)\b"
        ),
        # 33191 sterilisation, disinfection and hygiene devices, and 90524 medical
        # waste related services. Those two are specific to this patch. The other codes
        # the matching notices carry are not and are deliberately not claimed: 90910 and
        # 90919 are general cleaning services, 33199 is medical clothing shared with
        # theatres, 50421 is repair of medical equipment. Corroboration only - the title
        # still has to match, and on a patch with no procurement category of its own the
        # CPV scatter is itself the finding.
        "cpv": ("33191", "90524"),
        # NO DRUG TARIFF PART, and this one is not a close call. Part IX reimburses
        # dressings and elastic hosiery (IXA), incontinence appliances (IXB), stoma
        # appliances (IXC) and elastic hosiery (IXR). Gloves, aprons, masks, handrub,
        # disinfectants, sharps bins and washer-disinfectors are none of those. The
        # panel carries no tariff rather than reaching for the nearest part.
        "coverageNote": (
            "COVERAGE LIMITS, STATED RATHER THAN HIDDEN. FOUR OF THIS PATCH'S TWENTY "
            "NHS SUPPLY CHAIN AGREEMENTS ARE MISSING FROM THE FRAMEWORKS LIST ABOVE, "
            "AND THEY ARE MISSING FOR A DATA REASON, NOT BECAUSE THEY DO NOT EXIST. "
            "The Hub's framework record holds them in its `unparsed` block, which means "
            "the crawler could not read a supplier list off the brief, so nothing "
            "downstream can show them. They are: Single Use Personal Protective "
            "Equipment and Medical Protective Consumables (2021/S 000-016429, 76 "
            "suppliers, published expiry 3 September 2026 already passed with the brief "
            "unchanged); Non-Sterile Single Use Fluid-Resistant Surgical Facemasks Type "
            "IIR (2023/S 000-018722, expiry 3 September 2027); Single Use Theatre "
            "Protective Wear and Related Consumables (2025/S 000-077817, expiry 25 May "
            "2029); and Hand Hygiene Active Hand Shield (2025/S 000-077035, a direct "
            "award to one supplier, Primel Corporation Ltd, expiry 14 June 2027). Go to "
            "the Speciality page's own Buying route tab for the full twenty-row table "
            "with lots, terms and supplier counts. THE SUPPLIER LIST BELOW IS THEREFORE "
            "SIXTEEN FRAMEWORKS' WORTH, NOT TWENTY. It is not the whole supplier market "
            "on this patch and the four above carry names it does not. THERE IS NO NHS "
            "SUPPLY CHAIN INFECTION PREVENTION CATEGORY. The twenty agreements sit "
            "under Medical and Surgical Consumables, Facilities and Office Solutions, "
            "and Diagnostic Equipment and Services, so no single category filter could "
            "have produced this list and none was used: the frameworks are matched by "
            "subject, and the rule is printed above so it can be judged. WHAT WAS "
            "REFUSED, AND WHAT IT COST. Bare 'autoclave' is not in the award filter "
            "because nine of its eleven matches in this data are university and "
            "research-institute laboratory autoclaves with nothing in the title to "
            "separate them from a sterile services department; the price of that "
            "refusal is two genuine NHS rows, Bedfordshire's SSD autoclave cooling "
            "water chiller and East Suffolk and North Essex's microbiology autoclave "
            "replacement, and they are named here rather than quietly lost. Bare "
            "'paper hygiene' is not in the award filter either, although the Paper "
            "Hygiene framework IS in the list above: seven of its nine award matches "
            "are schools and councils buying toilet tissue and washroom dispensers, and "
            "an NHS couch-roll contract cannot be told from them on the title. Hand "
            "sanitiser, bare PPE, screening, swabs and bare 'infection' were refused "
            "for the same reason and the detail is in the rule comments. WHAT IS NOT "
            "HERE AT ALL: antibiotics and the antimicrobial subscription model, which "
            "are medicines and pharmacy's; microbiology culture, susceptibility testing "
            "and molecular respiratory panels, which are pathology and laboratory "
            "medicine's; the national screening programmes, which are public health's; "
            "and pest control, laundry, legionella testing and water safety, which are "
            "real Estates and Facilities spend on every one of these sites but are not "
            "among the twenty agreements and are not claimed. NHS Supply Chain's "
            "successor to Environmental Decontamination is renamed Environmental "
            "Decontamination and Water Purification with a go-live of 28 March 2030, so "
            "water purification joins this patch then; it has not joined it yet. NO "
            "OPEN TENDER MATCHED TODAY, which means no notice on this patch is open for "
            "bidding in this feed, not that none was looked for. "
            "FIVE COMPANIES ARE COUNTED TWICE IN THE SUPPLIER LIST BELOW AND THE "
            "NUMBER OF COMPANIES IS THEREFORE FIVE LOWER THAN THE COUNT. This is "
            "said rather than quietly corrected, because merging two names without "
            "confirming they are one company is how a false statement about a real "
            "firm gets published. NHS Supply Chain prints each of these two ways "
            "across its own briefs and the Hub's alias registry does not yet carry "
            "the second spelling: 'Vernacare' and 'Vernacare LTD (Robinson "
            "Healthcare Limited)'; 'Polyco Healthline' and 'Polyco Healthline "
            "Limited'; 'Globus (Shetland)' and 'Globus (Shetland) Ltd'; '2 San "
            "Global' and '2San Global Limited (New to the framework and NHS Supply "
            "Chain)'; 'Reliance Medical' and 'Reliance Medical Ltd (New)'. This is "
            "the first page in the rollout to carry both spellings of any of them, "
            "because it is the first to carry sixteen frameworks at once. 58 of the "
            "205 names below are flagged unresolved for the same reason - they are "
            "the cleaning machine, janitorial and waste firms on the Facilities and "
            "Office Solutions agreements, which the registry was built for medical "
            "device companies and does not yet hold. Every one is printed exactly "
            "as NHS Supply Chain wrote it, never dropped and never merged into "
            "something that looks close."
        ),
    },
    # PAGE 2846. Systemic anti-cancer therapy: the drug, the aseptic unit that
    # prepares it, and the kit it is given through. This is the rollout's first
    # speciality whose page opens on a procurement ABSENCE, and the absence is the
    # thing this rule has to get right. In the page's own words: "not one NHS Supply
    # Chain framework for a cytotoxic or a chemotherapy product". Its build read the
    # whole NHSSC catalogue and the 59-row Procurement Calendar and found no
    # oncology, cancer, chemotherapy, cytotoxic or ablation row on the calendar at
    # all. So there is no cancer framework to match, and the two agreements below are
    # general ones that a cancer service buys THROUGH, which is a different claim and
    # is said as such in the coverage note.
    #
    # RADIOTHERAPY IS DELIBERATELY NOT HERE, and it is the biggest call on this rule.
    # frameworks.json holds four agreements a cancer centre buys through — Radiotherapy
    # Treatment Systems, Radiotherapy Ancillary Devices incl Dosimetry, Radiotherapy IT
    # Solutions, and Brachytherapy Seeds and Associated Accessories — and no speciality
    # rule claims the first three. They are left out because this page draws the
    # modality line itself and draws it repeatedly: its demand panel sets SACT's 98.6%
    # against radiotherapy's 88.9% as a different modality running a different service,
    # and nothing in its scope, its buying route or its product ranges is a linear
    # accelerator. Brachytherapy Seeds is already counted on the urology page. The
    # right home for the other three is a radiotherapy page, which does not exist yet;
    # until it does the gap is recorded here and in the coverage note rather than
    # filled by widening this rule to the word "cancer".
    "oncology-and-sact": {
        "label": "Oncology and SACT",
        # THE TWO THE PAGE NAMES, AND ONLY THOSE. Both are named in its own buying
        # route and both expiry dates match the gold dates its calendar carries:
        # Infusion Pumps, Administration Sets and Associated Products on 30 September
        # 2026 — the page's live chip, with its 24-month extension already spent inside
        # the 48-month term — and Endoscopy, Endourology and Oncology Ablation
        # Consumables on 30 September 2027, which the page calls "the next one on this
        # patch". The second is also the only agreement in the entire NHSSC catalogue
        # whose name carries the word oncology, and it carries it for tumour ablation
        # devices, not for a drug. Neither is a cancer framework. Deliberately NOT here:
        #   Radiotherapy Treatment Systems / Ancillary Devices / IT Solutions
        #                        -> see the modality note above.
        #   Brachytherapy Seeds and Associated Accessories -> urology's.
        #   Mammography Imaging Systems -> radiology and imaging's. Breast screening is
        #                        cancer detection, which this page's own pathway section
        #                        places before any product decision a rep on this patch
        #                        makes.
        #   External Breast Prosthesis and Chest Support -> the rehabilitation,
        #                        prosthetics and orthotics patch.
        "frameworks": r"\b(oncology ablation|infusion pumps and administration sets)\b",
        # WRITTEN NARROW ON PURPOSE. Every title in tender-history.json and
        # framework-awards.json carrying cancer, oncolog, chemo, cytotox, tumour,
        # aseptic, immunotherap, biosimilar, radiotherap or brachytherap was printed
        # and read — 49 rows in the history feed and the award feed's cancer rows on
        # top. The loose terms are refused here rather than admitted and then argued
        # with in an exclusion list:
        #   "cancer" (not used bare) -> 13 rows, and 8 of them are cancer DIAGNOSIS,
        #                        screening or imaging, which this page's own pathway
        #                        section puts before the first product decision on this
        #                        patch: "Lung Cancer Screening - DAP C", "Non Specific
        #                        Symptom Urgent Suspected Cancer pathway", "C The Signs
        #                        Earlier Cancer Detection Platform", "NHS Essex ICB
        #                        Urgent Skin Cancer Dermoscopy Triage service",
        #                        "Specialised Paediatric Whole-Body MRI Surveillance for
        #                        Cancer Predisposing Syndromes", "Replacement Ultrasound
        #                        Machine for Lung Cancer Diagnostic", "SR Cancer - Multi
        #                        Modal Radiology image transfer" and Life Technologies'
        #                        "Cancer Service Panel", a sequencing panel. The
        #                        qualified forms below reach the treatment rows without
        #                        any of them.
        #   "oncolog" (not used bare) -> 8 rows, 4 of them wrong: two Queen Elizabeth
        #                        Hospital waivers for an Oncology Imaging System and its
        #                        phantom maintenance, which are radiotherapy physics;
        #                        "Supply of FDG and other Radiotracers for Oncology
        #                        Scanning", which is nuclear medicine; and a Next
        #                        Generation Sequencing panel for haemato-oncology
        #                        samples, which is the pathology page's.
        #   "aseptic" (not used) -> 17 rows. Aseptic preparation is step 4 of this
        #                        page's own pathway and the step the National Cancer
        #                        Plan is putting £80m into, but the word alone is a
        #                        pharmacy technical services word: compounded aseptic
        #                        medicines, aseptic isolators, aseptic cleanroom
        #                        consumables and laundry, unlicensed aseptic specials.
        #                        None of those says cancer, and the pharmacy and
        #                        medicines page is the honest home for them. The four
        #                        aseptic rows that ARE cancer say so in their own
        #                        titles — cytotoxics, or Systemic Anti-Cancer Treatment
        #                        — and are reached by those words instead.
        #   "tumour" (not used)  -> 4 rows, 3 of them lab or imaging: a tumour profiling
        #                        test, the haemato-oncology sequencing panel, and an
        #                        AAA Netspot diagnostic imaging agent kit. The fourth,
        #                        177Lu-Dotatate (Lutathera) for neuroendocrine tumours,
        #                        IS a systemic anti-cancer medicine but it is molecular
        #                        radiotherapy given by nuclear medicine, which is the
        #                        same modality line drawn above. Losing it is the
        #                        correct outcome of that line, not an accident.
        #   "monoclonal" (not used) -> 3 rows, 2 of them wrong: "Supply of
        #                        Nonchemotherapy Compounded Monoclonal Antibodies",
        #                        which says in its own title that it is not this patch,
        #                        and a Midlands and East branded medicines tranche of
        #                        cytokine modulators. The third says cytotoxic and is
        #                        reached by that.
        #   "immunotherap" (not used) -> 1 row, "Stem Cell and Immunotherapy Services",
        #                        NHS Blood and Transplant supplying Newcastle. A cell
        #                        therapy and donor service, not a SACT buy.
        #   "biosimilar" (not used) -> 6 rows, 4 of them general pharmacy transition
        #                        and biologics agreements and one ophthalmology. The
        #                        two cancer ones say "Cancer Medicines" and are reached
        #                        by that.
        #   MOLECULE NAMES (not used) -> deliberate, and it costs this panel two real
        #                        rows: a 2022 gemcitabine infusion-bag buy and a 2021
        #                        bevacizumab vials buy. A cytotoxic drug-name list
        #                        cannot be maintained honestly against a feed that
        #                        refreshes, and several oncology molecules are another
        #                        page's medicine — bevacizumab is an ophthalmology
        #                        anti-VEGF as often as it is a cancer drug, rituximab
        #                        is rheumatology's, methotrexate is dermatology's.
        #                        Publishing two fewer awards is the correct price.
        #   "extravasation" (not used) -> no row carries it today, and the device that
        #                        would carry it tomorrow is as likely to be a contrast
        #                        media extravasation detector on a CT scanner as a
        #                        chemotherapy kit. Not reached for.
        # NOTE ON \b AND "Nonchemotherapy": the word boundary in front of chemotherap
        # is doing real work. "Supply of Nonchemotherapy Compounded Monoclonal
        # Antibodies" does not match it, which is correct and is why that row needs no
        # exclusion.
        "include": (
            r"\b(chemotherap\w*|cytotoxics?|sact|anti-?cancer|"
            r"cancer medicines?|cancer drugs?|cancer treatments?|cancer therap\w*|"
            r"cancer care|"
            r"oncology (?:generics?|ablation|medicines?|drugs?|pharmac\w*|"
            r"day unit|consumables?)|"
            r"scalp cooling|cold caps?|dose band\w*)\b"
        ),
        # NO EXCLUSION LIST, and it is earned rather than skipped. All thirteen titles
        # the include list returns were printed and read one by one and every one of
        # them is this speciality: dose banded chemotherapy services, oncology ablation
        # consumables twice, aseptics medicines including cytotoxics, aseptically
        # prepared SACT, aseptically prepared cytotoxic medicines and monoclonal
        # antibodies, generic and biosimilar cancer medicines three times, oncology
        # generic medicines twice, chemotherapy cold caps twice, and Cheshire and
        # Merseyside ICB's cancer care services award to the Clatterbridge Cancer
        # Centre. The terms that would have needed excluding were refused above.
        #
        # WHAT THE FEED'S OWN `spec` FIELD SAYS ABOUT THIS PATCH, because it is the
        # sharpest illustration in the rollout so far of why it is never read: it tags
        # 31 rows oncology-and-sact and 26 of them are wrong. It has matched on "anti-"
        # and pulled in anti-rabies immunoglobulin, anti-D immunoglobulin, anti-embolism
        # stockings, anti-retroviral drugs and a COVID-19 antibody testing reagent; it
        # has added needle syringe programmes three times, a fluoroscopy unit, and
        # National Museums Scotland buying an X-ray unit. Meanwhile it misses dose
        # banded chemotherapy services, which it files under rehabilitation,
        # prosthetics and orthotics, and chemotherapy cold caps, which it leaves
        # unclassified.
        #
        # NO CPV LIST. Only one matching notice carries a CPV code at all and it is
        # 85100000, health services. Nothing in either award feed carries an
        # antineoplastic CPV: the whole 33652xx family is absent from this data, and
        # the only 3365x codes present are 33651600, vaccines. A prefix here would
        # corroborate nothing, so none is claimed.
        #
        # NO DRUG TARIFF PART. Part IX reimburses dressings and elastic hosiery (IXA),
        # incontinence appliances (IXB), stoma appliances (IXC) and elastic hosiery
        # (IXR) dispensed in the community on prescription. Systemic anti-cancer
        # therapy is a hospital-administered or hospital-dispensed medicine funded
        # through NICE technology appraisals, the Cancer Drugs Fund and high-cost drug
        # pass-through, and appears nowhere in Part IX. The panel carries none rather
        # than reaching for the nearest part.
        "exclude": None,
        "coverageNote": (
            "COVERAGE LIMIT, STATED RATHER THAN HIDDEN, AND IT IS THE WHOLE POINT OF "
            "THIS PATCH. There is no NHS Supply Chain framework for a cytotoxic or a "
            "chemotherapy product, and the drug itself does not travel this way at "
            "all: it moves through NICE technology appraisal, the Cancer Drugs Fund, "
            "NHS England specialised commissioning and regional medicines procurement, "
            "none of which has an NHS Supply Chain framework page. The two agreements "
            "below are general ones that a cancer service buys THROUGH, not cancer "
            "agreements. Infusion Pumps, Administration Sets and Associated Products "
            "is the whole hospital's pump and giving-set route, counted on the "
            "critical care, palliative care and vascular access pages too. Endoscopy, "
            "Endourology and Oncology Ablation Consumables is the only agreement in "
            "the catalogue whose name carries the word oncology, and it carries it for "
            "tumour ablation devices; NHS Supply Chain publishes no lot breakdown for "
            "it, so all 58 of its suppliers are listed and most of them sell endoscopy "
            "rather than anything a chemotherapy day unit or an aseptic unit buys. "
            "Radiotherapy is not counted here either: its three NHS Supply Chain "
            "frameworks and Brachytherapy Seeds are a different treatment modality, "
            "which this page's own demand section treats as a different service, and "
            "no radiotherapy speciality page exists yet to hold them. A supplier named "
            "below is therefore a supplier on an agreement cancer services buy "
            "through, never a measure of anyone's oncology business."
        ),
    },

    # PAGE 2916. THE ONLY SPECIALITY IN THIS ROLLOUT WITH NO NHS SUPPLY CHAIN ROUTE AT
    # ALL. The page says so in its own At a glance tile, and this rule has to match that
    # rather than manufacture a framework list to look like every other page. Scope is
    # the medicine itself and the pharmacy that handles it: branded and generic
    # medicines procurement, aseptic and unlicensed manufacture, homecare and
    # wholesale, community pharmacy contracts, pharmacy automation and the aseptic
    # estate. NOT the device a medicine is given through - the pump, the giving set,
    # the cannula and the syringe are the vascular access and IV therapy page's, and
    # are claimed there.
    "pharmacy-and-medicines": {
        "label": "Pharmacy and Medicines",
        # NO FRAMEWORK. All 121 parsed framework names in frameworks.json and all 16
        # unparsed ones were read on 11/09/2026 and not one of them is a medicine.
        # There is no pharmacy CBU category. The three that come nearest were checked
        # by supplier list, not by name, and all three were rejected:
        #   Infusion Pumps and Administration Sets (Project_12 ITT_382) - the ward pump
        #     and giving-set route. Already counted on vascular access and IV therapy,
        #     critical care and oncology. Its 27 suppliers are B. Braun, Baxter,
        #     Becton Dickinson, Fresenius Kabi and Smiths Medical selling pumps.
        #   Syringes, Needles and Associated Products - the same patch, same reason.
        #   Robotic Medical Equipment and Associated Accessories (2024/S 000-004668) -
        #     the word "robotics" appears in the page's own buying-route tile, and this
        #     framework is NOT what it means. Its six suppliers are CMR Surgical,
        #     Intuitive Surgical, Medtronic, Johnson & Johnson Medical, MCT
        #     Lifesciences and Procept Biorobotics. That is the surgical robot market,
        #     not the pharmacy dispensing robot market (Omnicell, BD Rowa, Swisslog),
        #     and publishing it as pharmacy's framework would be flatly wrong.
        # Claiming any of the three would fill the Suppliers tab with pump and surgical
        # robot firms and tell a pharmaceutical rep that they are the pharmacy market.
        # They are not. An honest empty state with the reason written into it is worth
        # more, and the awards and tenders panel below carries the route that is real.
        "frameworks": None,
        "frameworksFinding": {
            "frameworks": (
                "NO NHS SUPPLY CHAIN FRAMEWORK IS COUNTED HERE, AND FOR THIS SPECIALITY "
                "THAT IS THE SINGLE MOST USEFUL FACT ON THE PAGE RATHER THAN A GAP. NHS "
                "Supply Chain does not buy medicines. All four pages of its contract "
                "launch brief index, 140 briefs, were read on 11 September 2026 and not "
                "one covers a medicine; there is no pharmacy category; and none of the "
                "121 framework names in the Hub's record, or the 16 it holds unparsed, "
                "is a medicine. Medicines reach the NHS by four other routes entirely - "
                "NHS England medicines procurement and its Branded and Generic "
                "Pharmaceuticals tenders, regional pharmaceutical procurement in Wales, "
                "Scotland and Northern Ireland, homecare medicines contracts, and Drug "
                "Tariff reimbursement in the community. Those are what the awards and "
                "tenders panel shows. THREE AGREEMENTS COME NEAR AND ARE NAMED RATHER "
                "THAN COUNTED. Infusion Pumps and Administration Sets and Associated "
                "Products (Project_12 ITT_382, expiring 30 September 2026) and "
                "Syringes, Needles and Associated Products are the hardware a medicine "
                "is given through, not the medicine; both are counted on the vascular "
                "access and IV therapy page. Robotic Medical Equipment and Associated "
                "Accessories (2024/S 000-004668) is named because the word robotics "
                "invites the mistake: its six suppliers are CMR Surgical, Intuitive "
                "Surgical, Medtronic, Johnson and Johnson Medical, MCT Lifesciences and "
                "Procept Biorobotics, which is the surgical robot market and not the "
                "pharmacy dispensing robot market. Pharmacy automation does appear in "
                "this panel, but as trust-level contracts for robot maintenance and "
                "refurbishment, never as an NHS Supply Chain agreement."
            ),
            "suppliers": (
                "NO SUPPLIER LIST IS PUBLISHED FOR THIS SPECIALITY FROM THE FRAMEWORK "
                "ROUTE, because this panel names suppliers only where a framework "
                "record names them and no framework belongs to this speciality. That is "
                "not the same as saying the market has no suppliers: it is that NHS "
                "Supply Chain is not where they are listed. The firms that sell "
                "medicines into the NHS appear on NHS England's Branded and Generic "
                "Pharmaceuticals framework awards, on the Scottish, Welsh and Northern "
                "Irish national contracts, and on trust-level homecare, unlicensed "
                "specials and aseptic compounding contracts - all of which appear as "
                "named awards in the panel beside this one."
            ),
        },
        # INCLUDE. Procurement vocabulary only. NO MOLECULE NAMES, deliberately, and at
        # this speciality's scale that refusal matters more than anywhere else: a
        # medicines page could be widened with a drug-name list indefinitely and it
        # would be unmaintainable against a refreshing feed and would steal every other
        # page's medicine (bevacizumab is ophthalmology's as often as oncology's,
        # methotrexate is dermatology's). The cost is visible and accepted - single
        # product awards only reach this panel when the notice also carries a company
        # or category word, as the Vertex, Jazz and Novartis rows below do.
        #
        # NOT INCLUDED, deliberately: "prescription" and "prescriptions". Both were
        # tried. In 3,452 titles they match exactly two rows and both are Cumbria County
        # Council's "Supply of Care Equipment for Daily Living (Simple Aids by
        # Prescription)", a local authority daily living aids scheme that is the patient
        # moving and handling page's ground. A term whose entire yield is false is
        # refused in the include rather than admitted and then argued with in the
        # exclude list. "Prescribing" is kept and is a different word: it matches
        # electronic prescribing systems, which are a medicines system.
        #
        # Eight terms below match nothing in today's data and are kept knowingly, not
        # by accident: civas, compounding, medication, formulary, wholesaler,
        # immunization, controlled drug in the singular, and antimicrobial stewardship.
        # Each is unambiguous medicines vocabulary that cannot plausibly mean anything
        # else in a procurement title, so each is a safe forward catch on a feed that
        # refreshes. "Controlled drugs" in the plural does match, once, and correctly.
        "include": (
            r"\b(pharmac\w*|medicines?|medicinal|medication\w*|"
            r"dispensing|dispensar(?:y|ies)|prescribing|prescriber\w*|formular\w*|"
            r"aseptic\w*|civas|compounded|compounding|unlicensed|overlabelling|"
            r"over[- ]?labelled|biosimilars?|biologics?|wholesale|wholesaler\w*|"
            r"vaccin\w*|immunisation\w*|immunization\w*|"
            r"antimicrobial stewardship|controlled drugs?|drugs?)\b"
        ),
        # EXCLUDE. Every pattern here was put in because a real row in
        # tender-history.json, framework-awards.json or open-tenders.json matched the
        # include list above and was read and found not to be this speciality.
        #   alcohol        -> fourteen rows, the largest false positive group by far and
        #                     all of them bare "drug": All Age Alcohol and Drug Treatment
        #                     Recovery Service (Rotherham), Drug and Alcohol Treatment
        #                     Recovery and Improvement (Hammersmith and Fulham, twice),
        #                     Inpatient detoxification for people who use drugs and
        #                     alcohol (Leicester, three times), SOL Drug and Alcohol
        #                     Services 2027 (Solihull), Rough Sleeping Drug and Alcohol
        #                     Psychology Service (Hampshire), Drug and Alcohol Support
        #                     for Rough Sleepers (Camden), Halton Integrated Drug and
        #                     Alcohol Treatment, Newcastle Treatment and Recovery, and
        #                     Drug, Alcohol and DNA Testing Services (Swansea). Substance
        #                     misuse commissioning by local authorities, not pharmacy.
        #   drug test      -> "BLC0339 - Drug Test on Arrest Scheme", Police and Crime
        #                     Commissioner for Durham. Forensic testing, and the one
        #                     substance-misuse row whose title carries no "alcohol".
        #   drug substance -> "AMPA PH1 Drug Substance", Cardiff University, twice. An
        #                     active ingredient manufactured for a university research
        #                     programme, not an NHS medicines contract.
        #   intrathecal drug pump
        #                  -> "Neuromodulation/Spinal Cord Stimulators, Intrathecal Drug
        #                     Pumps, Radiofrequency Ablation and Associated Products".
        #                     An implantable device tender; pain management's ground.
        #   medicine skills-> "Paramedic, Nursing & Medicine Skills Equipment",
        #                     University of Ulster, twice. Clinical skills training
        #                     equipment, where "medicine" is the profession.
        #   access to medicine
        #                  -> "Access to medicine and the professions 2026/27", NHS
        #                     England, three times, CPV 80000000 education services. A
        #                     widening participation programme for entry to the medical
        #                     professions. Same word, and nothing to do with a medicinal
        #                     product. Note this is the ONLY discipline-sense use of
        #                     "medicine" excluded: "nuclear medicine" is deliberately
        #                     NOT excluded, because its single appearance in this data is
        #                     "UHL_Radiopharmaceuticals Radiopharmacy Nuclear Medicine",
        #                     which is a genuine radiopharmacy contract and belongs here.
        #   social prescribing
        #                  -> SEL ICB (Bexley) Health and Wellbeing Coaching and
        #                     Community Health and Wellbeing Workers with Social
        #                     Prescribing. Link workers, not medicines.
        #   veterinary     -> "PURCH1851 ... Veterinary Pharmaceutical And Consumable/
        #                     Disposable Products", University of Glasgow.
        #   gambia         -> "Pharmaceutical Supplies to the MRC Unit the Gambia at
        #                     LSHTM". An overseas research unit's supplies, not UK NHS.
        #   in-orbit       -> "Unlocking Space for Business: In-orbit R&D and
        #                     manufacturing of pharmaceuticals RFI", Department for
        #                     Science, Innovation and Technology. Space manufacturing
        #                     research.
        #   postcards      -> "CHIS Measles Mumps and Rubella (MMR) Vaccine Postcards
        #                     26-28", CPV 79824000, printing. A print contract.
        #   syringes and needles
        #                  -> "Combined Safety Syringes and Needles for the COVID-19
        #                     Vaccination Programme" and its Morbidly Obese Requirement
        #                     variant. Device consumables reached through "vaccination";
        #                     both are the vascular access and IV therapy page's and are
        #                     claimed there.
        #   THE OCCUPATIONAL HEALTH VACCINATION GROUP. Seven rows, and they are the one
        #   genuinely difficult call in this rule. A vaccine SUPPLY contract is a
        #   medicines contract and is counted here. An employer buying a service to
        #   vaccinate its own staff is an occupational health contract that no vaccine
        #   manufacturer bids for, so it is not. The excluded rows are Flu Vaccine
        #   Vouchers (The Pensions Regulator), Staff Flu Vaccination Programme (Hull
        #   City Council), 846-NYC-HA Staff Flu Vaccinations (North Yorkshire), Staff
        #   Winter Vaccination Programme (Bradford Teaching Hospitals), Workforce
        #   Influenza Vaccination Programme (Lancashire), Flu Vaccination Campaign (NHS
        #   West and North London ICB), and Community and School Aged Immunisation
        #   Service (NHS England) - a delivery service, not a product.
        "exclude": (
            r"\b(alcohol|drug test\w*|drug substance|intrathecal drug pumps?|"
            r"medicine skills|access to medicine|social prescribing|"
            r"veterinary|gambia|in[- ]orbit|postcards?|syringes and needles|"
            r"staff (?:flu|winter|influenza|vaccinat)\w*|staff vaccinat\w*|"
            r"workforce influenza|flu vaccination campaign|vaccine vouchers|"
            r"immunisation service)\b"
        ),
        # 33600000 pharmaceutical products and 33651600 vaccines. Nothing wider: a bare
        # "336" prefix would reach 33696xxx laboratory reagents, which is pathology's,
        # 33693xxx nicotine replacement and e-cigarettes, which is public health's,
        # 33697110 on a Total Orthopaedic Solutions notice, and - genuinely - 33682000
        # on a flooring contract. Corroboration only; the title still has to match.
        "cpv": ("33600", "336516"),
        # NO DRUG TARIFF PART, AND THE REASON IS WORTH STATING BECAUSE IT LOOKS LIKE AN
        # OMISSION AND IS NOT. Part IX is the APPLIANCE list - dressings and elastic
        # hosiery (IXA), incontinence appliances (IXB), stoma appliances (IXC), elastic
        # hosiery (IXR). Medicines are reimbursed under Part VIII, which the Hub does
        # not hold. A community pharmacy dispenses all of Part IX, so it would be easy
        # to claim the whole of it here, and that would publish twenty thousand
        # appliance lines as this speciality's market and drown the medicine. The
        # coverage note below states the Part VIII gap in the member's own terms
        # instead.
        "coverageNote": (
            "TWO COVERAGE LIMITS, STATED RATHER THAN HIDDEN. FIRST, THE DRUG TARIFF. "
            "This page carries no Drug Tariff panel, and that is deliberate. The Hub "
            "holds Part IX of the Drug Tariff, which is the appliance list - dressings "
            "and elastic hosiery, incontinence appliances, stoma appliances. Medicines "
            "are reimbursed under Part VIII, which the Hub does not hold. A community "
            "pharmacy dispenses the whole of Part IX, so claiming it here would be easy "
            "and would bury the medicine under twenty thousand appliance lines that "
            "belong to the wound care, continence and stoma pages. The community "
            "medicines figure a rep actually needs is on this page's own money section, "
            "computed from Prescription Cost Analysis. SECOND, SINGLE-PRODUCT AWARDS. "
            "This panel matches procurement vocabulary and never drug names, so a "
            "notice titled with a molecule alone does not reach it. That is a known and "
            "accepted cost: a molecule list cannot be maintained honestly against a "
            "refreshing feed, and most molecules belong to a clinical page rather than "
            "to pharmacy - bevacizumab is ophthalmology's as often as oncology's. "
            "Single-product awards appear here only where the notice also carries a "
            "company or category word, which is why the Vertex, Jazz and Novartis rows "
            "are present and a bare molecule tender would not be."
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
        # A rule with nothing to exclude gets a regex that cannot match, for the
        # same reason build_frameworks does: the absence has to be said in the
        # data, not faked with a pattern that happens to match nothing today.
        "exc": NEVER_MATCHES if rule["exclude"] is None
               else re.compile(rule["exclude"], re.I),
    }


def match_title(rx, title):
    t = title or ""
    return bool(rx["inc"].search(t)) and not rx["exc"].search(t)


def build_frameworks(rx, rule, fw_doc):
    """The speciality's NHSSC frameworks, with the supplier list each one carries.

    A `frameworkCorrections` entry on the rule removes names that frameworks.json
    holds as suppliers but NHS Supply Chain's own brief lists as DELISTED. The
    crawler reads the brief's Suppliers section as one block, and where the brief
    ends that section with "The following suppliers are being delisted at the start
    of the new framework:" it sweeps that tail in too. Published raw, that puts
    companies which have LEFT the framework in front of a paying member as though
    they were still on it, which is worse than showing nothing.

    The correction is applied by NAME and it FAILS LOUDLY if the names are not all
    there. If the crawler is fixed upstream, or NHS Supply Chain reissues the brief,
    this build stops rather than quietly doing nothing: the list has to be re-read
    against the live page before it can be trusted again (root rule 13 — where the
    gate and the data disagree, assume the data is wrong).
    """
    corrections = rule.get("frameworkCorrections") or {}
    out = []
    for f in fw_doc["frameworks"]:
        name = f.get("name") or ""
        if not rx["fw"].search(name):
            continue
        suppliers = [s for s in (f.get("suppliers") or []) if isinstance(s, str)]
        count = f.get("supplierCount")
        source = f.get("supplierSource")
        delisted = f.get("delisted")
        corr = corrections.get(name)
        if corr:
            want = [n.lower() for n in corr["removeSuppliers"]]
            have = [s.lower() for s in suppliers]
            missing = [n for n in want if n not in have]
            if missing:
                raise SystemExit(
                    "build_speciality_panels: the delisted-supplier correction for\n"
                    "  %s\n"
                    "no longer matches frameworks.json. Not found: %s\n"
                    "Re-read NHS Supply Chain's own contract launch brief and either "
                    "update or remove the frameworkCorrections entry. Refusing to "
                    "build rather than publish a supplier list that may be wrong."
                    % (name, "; ".join(missing)))
            delisted = [s for s in suppliers if s.lower() in want]
            suppliers = [s for s in suppliers if s.lower() not in want]
            count = len(suppliers)
            source = corr["why"]
        out.append({
            "name": f.get("name"),
            "url": f.get("url"),
            "reference": f.get("reference"),
            "category": f.get("category"),
            "supplyRoute": f.get("supplyRoute"),
            "starts": f.get("starts"),
            "ends": f.get("ends"),
            "supplierCount": count,
            "supplierSource": source,
            "suppliers": suppliers,
            "delisted": delisted,
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
    56,833 lines and no panel can carry that.

    A PART IS NOT ALWAYS A SPECIALITY, WHICH IS WHY `tariffVmp` EXISTS. For wound care
    and for continence the whole part is the patch: IXA is dressings and elastic
    hosiery, IXB incontinence appliances, IXC stoma. Gynaecology is the first
    speciality where that stops being true. Its community route is 257 pessary lines
    which sit INSIDE Part IXA, alongside 56,576 dressing and hosiery lines that belong
    to tissue viability. Claiming the part whole would have put Juzo and Sigvaris at
    the top of a gynaecology panel as its leading suppliers, which is a false statement
    about the market made by a filter that was too blunt rather than wrong.

    So a rule may narrow a part by the virtual medicinal product description. The
    pattern is written into the published file (rule 14a) so a reader can see exactly
    which lines were counted, and the counts fall out of the same rows that are
    summarised, never out of a separate assertion.
    """
    parts = tuple(rule.get("tariffParts") or ())
    if not parts:
        return None
    ix = {k: i for i, k in enumerate(dt_doc["schema"])}
    rows = [r for r in dt_doc["rows"] if r[ix["part"]] in parts]
    vmp_pattern = rule.get("tariffVmp")
    # WHICH NAME THE FILTER READS. By default the virtual medicinal product
    # description, which is the generic clinical name and is where a term like
    # "pessar" lives. A rule may name more fields, and paediatrics is the case that
    # needs it: the paediatric marker often lives only in the BRAND name, so Sanofi's
    # JuniorSTAR half-unit insulin pen is a children's dosing device whose virtual
    # description says nothing about children. Searching the virtual name alone
    # returns 258 of its 473 lines and loses Part IXC's paediatric stoma range whole.
    fields = tuple(rule.get("tariffFields") or ("vmp",))
    if vmp_pattern:
        vrx = re.compile(vmp_pattern, re.I)
        rows = [r for r in rows
                if vrx.search(" ".join((r[ix[f]] or "") for f in fields))]
    if not rows:
        return None
    by_sup = {}
    prices = []
    for r in rows:
        by_sup[r[ix["supplier"]]] = by_sup.get(r[ix["supplier"]], 0) + 1
        try:
            # NHSBSA PUBLISHES PART IX PRICES IN PENCE, and until 10/09/2026 this
            # function passed them straight through to a renderer that prints a pound
            # sign in front of them. Three live panels were telling paying members
            # that Part IXA reimburses "from £3.0 to £46900.0" when the range is
            # £0.03 to £469.00, a hundredfold overstatement of every reimbursement
            # price on the Hub. Proven against the tariff's own rows rather than
            # assumed: "Foley catheter paediatric 8Ch" carries 555 and 1064 in this
            # file, and NHSBSA's September 2026 Part IX prints that line at £5.55 to
            # £10.64. Converted here, at the point the summary is built, so no panel
            # can carry the raw unit again.
            prices.append(float(r[ix["price"]]) / 100.0)
        except (TypeError, ValueError):
            pass
    top = sorted(by_sup.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    return {
        "parts": list(parts),
        "vmpFilter": vmp_pattern,
        "vmpCount": len({r[ix["vmp"]] for r in rows}) if vmp_pattern else None,
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

    frameworks = build_frameworks(rx, rule, fw_doc)
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
                (rule.get("frameworksFinding") or {}).get("frameworks")
                if rule["frameworks"] is None and rule.get("frameworksFinding") else
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
                (rule.get("frameworksFinding") or {}).get("suppliers")
                if rule["frameworks"] is None and rule.get("frameworksFinding") else
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
            "awards": ((
                ("Award-stage notices whose TITLE matches /%s/i. NO EXCLUSION LIST IS "
                 "APPLIED, because every notice this pattern matched was read one by one "
                 "and all of them are this speciality. The loose terms that would have "
                 "needed excluding were refused from the pattern above instead of "
                 "admitted and then argued with. %%s Buyer names are never matched on."
                 % rule["include"])
                if rule["exclude"] is None else
                ("Award-stage notices whose TITLE matches /%s/i and does not match /%s/i. %s "
                 "%%s Buyer names are never matched on." % (
                     rule["include"], rule["exclude"],
                     rule.get("excludeFinding")
                     or ("The exclusion list exists because every pattern in it matched a real "
                         "notice that was not this speciality.")))
            ) % (
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
                ("NHSBSA Drug Tariff Part %s for the stated effective month, narrowed to the "
                 "lines whose virtual medicinal product description or brand name matches "
                 "/%s/i, and then summarised. Both names are read because on this patch the "
                 "marker often lives only in the brand: a half-unit insulin pen sold as "
                 "JuniorSTAR is a children's dosing device whose generic description says "
                 "nothing about children. The parts are sliced rather than claimed whole "
                 "because no part of the tariff is this speciality: Part IXA alone is 56,833 "
                 "lines of dressings and elastic hosiery, which are the tissue viability "
                 "page's. THE LIMIT OF THIS RULE, STATED RATHER THAN HIDDEN: a product for "
                 "children named without one of those words, which is to say a small-size "
                 "adult line used in children, is invisible to it, so this count understates "
                 "the paediatric range and does not overstate it. Every count and price below "
                 "is taken from the lines the pattern selects. Prices are the reimbursement "
                 "price at publication, converted from the pence NHSBSA publishes, and are not "
                 "necessarily today's."
                 % ("/".join(rule["tariffParts"]), rule["tariffVmp"]))
                if rule.get("tariffParts") and rule.get("tariffVmp")
                and tuple(rule.get("tariffFields") or ("vmp",)) != ("vmp",) else
                ("NHSBSA Drug Tariff Part %s for the stated effective month, narrowed to the "
                 "lines whose virtual medicinal product description matches /%s/i, and then "
                 "summarised. The part is sliced rather than claimed whole because the part is "
                 "not this speciality: Part IXA is 56,833 lines of dressings and elastic "
                 "hosiery, which are the tissue viability page's, and only the lines this "
                 "pattern selects belong here. Every count and price below is taken from those "
                 "lines. Prices are the reimbursement price at publication, converted from the "
                 "pence NHSBSA publishes, and are not necessarily today's."
                 % ("/".join(rule["tariffParts"]), rule["tariffVmp"]))
                if rule.get("tariffParts") and rule.get("tariffVmp") else
                "NHSBSA Drug Tariff Part %s for the stated effective month, summarised. Prices "
                "are the reimbursement price at publication, converted from the pence NHSBSA "
                "publishes, and are not necessarily today's."
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
