#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 23/09/2026 (continuation of today's
earlier Total Orthopaedic Solutions 3 run).

Johnson & Johnson MedTech (jnjmedtech.com, own-site crawl verified 08/09/2026)
crawls to 868 products, 709 of them under one flat "Uncategorised" division
(sitemap-derived, no division structure). The site is the UK legal entity
"Johnson & Johnson Medical Ltd" trading as both Ethicon (sutures/staplers/
energy devices, already published under theatres/mis) AND DePuy Synthes
(orthopaedics) — one seed record, one site, two brand families. This is NOT
an identity-merge question (no ruling needed): "Johnson & Johnson Medical
Ltd" is exactly how NHS Supply Chain's own TOS3 award list names the
awardee (data/frameworks.json), which resolves via the existing alias
registry straight to this one seed record. The site genuinely carries the
DePuy Synthes range under the same domain.

NOTE: a SEPARATE seed record, "DePuy Synthes (J&J MedTech)", also lists TOS3
in its own `frameworks` field, but data/frameworks.json's actual TOS3
supplier list (the ledger's real awardee roster) names only
"Johnson & Johnson Medical Ltd" — DePuy Synthes (J&J MedTech) is not one of
the 101 awarded suppliers the ledger counts for this framework at all. That
second record's own frameworks-field entry for TOS3 looks like leftover/
incorrect bookkeeping and is left untouched here (out of scope for this
batch) rather than corrected without a clearer picture of its purpose.

Only products whose OWN NAME unambiguously names orthopaedic anatomy or an
orthopaedic-specific surgical/device term (LCP, nailing, arthroplasty system
etc, all Synthes/DePuy trade terms with no non-orthopaedic use) are mapped
here, for the ortho:cement/equip/implant/trauma types this framework's
speciality is gated to.

Excluded deliberately, left held:
  - Craniomaxillofacial (CMF) plates: Matrixorbital/Matrixmandible/Trumatch
    Cmf products name orbital/mandible/cranial anatomy, a different
    speciality (CMF/ENT), not orthopaedic.
  - Veterinary orthopaedics: "Tplo"/"Tta" (Tibial Plateau Levelling
    Osteotomy / Tibial Tuberosity Advancement) and "Pancarpal Arthrodesis"
    are canine cruciate-ligament/carpal procedures (DePuy Synthes Vet), not
    human NHS care and out of scope for an NHS Supply Chain framework
    entirely.
  - Foreign-language duplicate captures (jnjmedtech.com's sitemap carries a
    separate URL/title per locale for the same product: Spanish, Portuguese,
    Dutch, German, French). Only the English capture of each product is
    mapped this run; the same product's other-language captures stay held
    rather than mapping the same override string many times over for no
    member-facing gain in a UK Hub.
  - Category/landing-page-shaped captures ("Biologics Spine Trauma
    Solutions", "3D Patient Specific Anatomic Spine Model", "Conduit Lateral
    Switch Plate", "Locking Reconstruction Mini Plate System"): read as a
    section heading or a one-off unclear item rather than a named product,
    so left held rather than guessed (nav-labels-are-not-products policy,
    data/identity-vocabulary-policy.json).

Run once: python3 scripts/_seed_jjmedtech_ortho_overrides_0923.py
"""
import json

MAP = "data/differentiator-category-map.json"
SUPPLIER = "Johnson & Johnson MedTech"

EVIDENCE = (
    "the supplier's own site filing, read by scripts/crawl_supplier_site.py, "
    "under the flat 'Uncategorised' division; confirmed 23/09/2026 that the "
    "product's own name unambiguously names orthopaedic anatomy or an "
    "orthopaedic-specific (Synthes/DePuy trauma or arthroplasty) trade term."
)

IMPLANT = {
    "Sigma Total Knee System": "named knee arthroplasty system.",
    "Attune Revision Knee System": "named knee arthroplasty revision system.",
    "Sigma Hp Partial Knee": "named partial-knee arthroplasty system.",
    "S Rom Noiles Rotating Hinge Knee System": "named revision knee arthroplasty system.",
    "Attune Medial Stabilized Knee System": "named knee arthroplasty system.",
    "Attune Cementless Rp Knee System": "named knee arthroplasty system.",
    "Trumatch Personalized Solutions Knee": "patient-specific instrumentation named for knee arthroplasty.",
    "Global Unite Platform Shoulder System": "named shoulder arthroplasty system.",
    "Global Steptech Apg Shoulder System": "named shoulder arthroplasty system.",
    "Delta Xtend Reverse Shoulder System": "named reverse shoulder arthroplasty system.",
    "Global Icon Stemless Shoulder System": "named shoulder arthroplasty system.",
    "Inhance Shoulder System": "named shoulder arthroplasty system.",
    "Trumatch Personalised Solutions Shoulder System": "patient-specific instrumentation named for shoulder arthroplasty.",
    "Trumatch Personalized Solutions Shoulder System": "patient-specific instrumentation named for shoulder arthroplasty (US spelling capture).",
    "Corail Total Hip System": "named hip arthroplasty system.",
    "Actis Total Hip System": "named hip arthroplasty system.",
    "Actis Total Hip Solutions": "named hip arthroplasty system.",
    "Reclaim Monobloc Revision Hip System": "named revision hip arthroplasty system.",
    "Reclaim Modular Revision Hip System": "named revision hip arthroplasty system.",
    "Emphasys Femoral Solutions": "named femoral hip-arthroplasty component system.",
    "Emphasys Acetabular Solutions": "named acetabular hip-arthroplasty component system.",
    "Intrapelvic Acetabular System": "named acetabular hip-arthroplasty system.",
    "Pinnacle Acetabular Cup System": "named acetabular hip-arthroplasty cup system.",
    "Pinnacle Triflange Acetabular Cup": "named acetabular hip-arthroplasty cup.",
    "Truespan Meniscal Repair System": "named meniscal (knee) repair implant system.",
    "Expedium Anterior Spine": "named spinal implant system (anterior spine), matching the existing Globus Medical UK Ltd/Joint Operations Spine->ortho:implant precedent.",
    "Expedium Vertebral Body Derotation System": "named spinal deformity-correction implant system.",
    "Viper 2 Spine System": "named spinal implant (pedicle screw) system.",
    "Viperr Cortical Fix Fenestrated Screw System": "named spinal implant screw system.",
    "Skyline Anterior Cervical Plate System": "named cervical spine implant plate system.",
    "Skyline Anterior Cervical Plates": "named cervical spine implant plates.",
    "Coda Anterior Cervical Plate": "named cervical spine implant plate.",
    "Trialtis Spine System": "named spinal implant system.",
}

TRAUMA = {
    "Lcp Superior And Superior Anterior Clavicle Plate 35 Mm": "named clavicle fracture-fixation plate (LCP = Locking Compression Plate, Synthes trauma trade term).",
    "Lcp Superior And Superior Anterior Clavicle Plate": "named clavicle fracture-fixation plate.",
    "35 Mm Lcpr Clavicle Hook Plate": "named clavicle fracture-fixation hook plate.",
    "Lcp Clavicle Hook Plate": "named clavicle fracture-fixation hook plate.",
    "Va Lcp Clavicle Hook Plate": "named clavicle fracture-fixation hook plate.",
    "27Mm Va Lcp Clavicle Plate System": "named clavicle fracture-fixation plate system.",
    "Va Lcp Anterior Clavicle Plate": "named clavicle fracture-fixation plate.",
    "Variable Angle Lcp Clavicle System": "named clavicle fracture-fixation plate system.",
    "Trauma Recon System": "DePuy Synthes' named Trauma Recon (proximal femoral) nailing system.",
    "Va Lcp Condylar Plate": "named femoral/tibial condylar fracture-fixation plate.",
    "Va Lcp Proximal Tibial Plate": "named proximal tibia fracture-fixation plate.",
    "Variable Angle Proximal Tibia Plate": "named proximal tibia fracture-fixation plate.",
    "Lcp Proximal Tibia Plate": "named proximal tibia fracture-fixation plate.",
    "Variable Angle Curved Condylar Plate": "named condylar fracture-fixation plate.",
    "Expert Tibial Nail Etn": "named tibial intramedullary nail.",
    "Expert Tibial Nail And Expert Tibial Nail Protect": "named tibial intramedullary nail.",
    "Femoral Recon Nail": "named femoral intramedullary nail.",
    "Multiloc Humeral Nailing System": "named humeral intramedullary nailing system.",
    "Multiloc Humeral Nail": "named humeral intramedullary nail.",
    "Tfn Advanced Proximal Femoral Nailing System": "named proximal femoral intramedullary nailing system.",
    "Advanced Nailing System": "intramedullary nailing is an orthopaedic-specific fracture-fixation technique with no non-orthopaedic use.",
    "Dbx Demineralized Bone Matrix Trauma": "named bone-graft-substitute product filed under Synthes' own Trauma range.",
    "Variable Angle Locking Patella Plating System": "named patella (knee) fracture-fixation plating system.",
    "Va Lcp Periprosthetic Proximal Femur Plating System": "named periprosthetic femur fracture-fixation plate.",
    "Variable Angle Lcp Periprosthetic Proximal Femur Plating System": "named periprosthetic femur fracture-fixation plate.",
    "Variable Angle Periprosthetic Proximal Femur Plating System": "named periprosthetic femur fracture-fixation plate.",
    "Lcp Plates": "LCP (Locking Compression Plate) is Synthes' own orthopaedic trauma plate system name, not a generic term.",
    "Femoral Neck System": "named femoral-neck fracture-fixation implant system.",
    "Variable Angle Ankle Trauma System": "named ankle fracture-fixation plating system.",
    "Flexible Reamers Intramedullary Nail": "reaming instrument specific to intramedullary nail insertion.",
    "Titanium Cannulated Hindfoot Arthrodesis Nail": "named hindfoot fusion nail.",
    "Elastic Nail System Titanium": "paediatric long-bone intramedullary nailing system.",
    "Titanium Cannulated Tibial Nail": "named tibial intramedullary nail.",
    "Cannulated Adolescent Lateral Entry Femoral Nail Titanium": "named paediatric femoral intramedullary nail.",
    "Expert Cannulated Lateral Entry Femoral Recon Nail": "named femoral intramedullary nail.",
    "Locking Calcaneal Plates": "named calcaneus (heel bone) fracture-fixation plates.",
    "Frn Advanced Femoral Recon Nailing System": "named femoral intramedullary nailing system.",
    "Variable Angle Elbow System": "named elbow fracture-fixation plating system.",
    "Small Fragment Locking Compression Plate System": "named small-bone fracture-fixation LCP system.",
    "Lcp Ulna Osteotomy System 27 Mm": "named ulna fracture-fixation/osteotomy plate system.",
    "Lcp Proximal Femur Hook Plate": "named proximal femur fracture-fixation hook plate.",
    "Lcp Locking Attachment Plate": "Synthes LCP-family fracture-fixation accessory plate.",
    "Curved Locking Compression Plates Lcp System 3545 Mm": "named fracture-fixation LCP system.",
    "Lcp Distal Ulna Plate": "named distal ulna fracture-fixation plate.",
    "Slipped Capital Femoral Epiphysis Scfe Screw System": "named paediatric hip (SCFE) fixation screw system.",
    "35Mm Lcp Olecranon Plate": "named olecranon (elbow) fracture-fixation plate.",
    "Tipeek Foot Osteotomy Wedge System": "named foot osteotomy wedge implant system.",
    "Lcp Periarticular Proximal Humerus Plate": "named proximal humerus fracture-fixation plate.",
    "Lcp Hook Plate": "Synthes LCP-family fracture-fixation hook plate.",
    "Universal Locking Trochanter Stabilization Plate": "named trochanter (hip) fracture-fixation plate.",
    "Lcptm Proximal Femur Plate 45 Mm": "named proximal femur fracture-fixation plate.",
    "Lcp Proximal Femoral Plate": "named proximal femur fracture-fixation plate.",
    "Lcp Wrist Fusion Set": "named wrist fusion fixation plate set.",
    "Lcp Pilon Plate": "named tibial pilon fracture-fixation plate.",
    "Locking Compression Plate System": "Synthes' own named LCP fracture-fixation system.",
    "Lcp Distal Femur Plate": "named distal femur fracture-fixation plate.",
    "Lcp Distal Femur Plate With Liss": "named distal femur fracture-fixation plate.",
    "Lcp Distal Fibula Plate System 2735 Mm": "named distal fibula fracture-fixation plate.",
    "Lcp Distal Tibia Plates": "named distal tibia fracture-fixation plates.",
    "Lcp Anterolateral Distal Tibia Plate": "named distal tibia fracture-fixation plate.",
    "Variable Angle Lcp Two Column Volar Distal Radius Plate": "named distal radius (wrist) fracture-fixation plate.",
    "Va Lcp Two Column Volar Distal Radius Plate": "named distal radius fracture-fixation plate.",
    "Lcp Distal Radius System 24 Mm": "named distal radius fracture-fixation plate system.",
    "Va Lcp Distal Radius Sterile Kit": "named distal radius fracture-fixation plate kit.",
    "24 Mm Variable Angle Lcp Volar Extra Articular Distal Radius System": "named distal radius fracture-fixation plate system.",
    "24Mm Variable Angle Lcp Volar Rim Distal Radius System": "named distal radius fracture-fixation plate system.",
    "Lcp Proximal Humerus Plate": "named proximal humerus fracture-fixation plate.",
    "Expert Hindfoot Arthrodesis Nail": "named hindfoot fusion nail.",
    "Volt Wrist Treatment System": "named distal radius (wrist) fracture-fixation plating system.",
    "Volt Proximal Humerus Plating System": "named proximal humerus fracture-fixation plating system.",
    "Antegra Plate System": "named proximal humerus fracture-fixation plate system.",
    "Cannulated Pediatric Osteotomy System Capos": "named paediatric osteotomy fixation system.",
    "Tomofix Osteotomy System": "named lower-limb osteotomy fixation plate system.",
    "Pediatric Lcp Plate System": "named paediatric fracture-fixation LCP system.",
    "Intrafix Advance Tibial Fastener System": "named tibial ACL-graft/fracture fixation system.",
    "Low Profile Pelvic System 35 Mm": "named pelvic fracture-fixation plate system.",
    "Variable Angle Forefoot Midfoot System": "named forefoot/midfoot fracture-fixation plating system.",
    "Modular Foot System": "named foot fracture-fixation/reconstruction plating system.",
    "Pelvic C Clamp Ii": "named pelvic-ring fracture stabilisation clamp.",
    "Midfoot Fusion Bolt": "named midfoot fusion fixation implant.",
    "Variable Angle Locking Calcaneal Plating System 27 Mm": "named calcaneus fracture-fixation plating system.",
    "Variable Angle Locking Calcaneal Plating System": "named calcaneus fracture-fixation plating system.",
    "Pro Spec Foot And Ankle Bio Implant System": "named foot and ankle fixation implant system.",
}

CEMENT = {
    "Confidence Spinal Cement System": "named vertebroplasty bone-cement system, matching the existing Medtronic Kyphon/It's Interventional Spine->ortho:cement precedent.",
    "Synflate Vertebral Balloon": "named vertebral-compression-fracture balloon (kyphoplasty) device.",
    "Synflate Vertebral Balloon System": "named vertebral-compression-fracture balloon system.",
    "Traumacem V Augmentation System": "named vertebral bone-cement augmentation system.",
    "Vertebral Body Balloon": "named vertebral-compression-fracture balloon device.",
}

EQUIP = {
    "Shoulder Extraction Instruments": "instrument set named for shoulder-implant extraction.",
    "General Shoulder Instruments": "instrument set named for shoulder arthroplasty.",
    "Hip Preservation Surgery Set": "instrument set named for hip-preservation surgery.",
    "Velys Hip Navigation": "J&J's named surgical navigation/robotics platform for hip arthroplasty.",
    "Orthopaedic Foot Instruments": "instrument set explicitly named orthopaedic.",
    "Trauma Saw Blades": "cutting instrument named for trauma (bone) surgery.",
}

GROUPS = (("ortho:implant", IMPLANT), ("ortho:trauma", TRAUMA),
          ("ortho:cement", CEMENT), ("ortho:equip", EQUIP))

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
added = 0
for hub, group in GROUPS:
    for name, why in group.items():
        key = (SUPPLIER, name)
        if key in known:
            print("already present, skipping:", name)
            continue
        doc["entries"].append({
            "supplier": SUPPLIER,
            "division": name,
            "products": 1,
            "categories": [],
            "examples": [name],
            "hub": hub,
            "notTaxonomy": False,
            "kind": "product-override",
            "evidence": EVIDENCE,
            "why": why,
        })
        known.add(key)
        added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False)
print("added %d product-override entries" % added)
