#!/usr/bin/env python3
"""One-off seeder, framework-coverage batch 15/10/2026.

Respiratory Solutions: picked as the lowest-coverage STARTED framework with
work left after confirming every lower-coverage framework in
docs/framework-coverage-exhausted.json is still genuinely unchanged (no new
award, no new unresolved name, no new held range on any of their recorded
supplier sets).

Two of the framework's `publishedElsewhereNeedingCategory` suppliers carry a
genuinely own-crawled "Respiratory"-named division that was never mapped
(hub: null in differentiator-category-map.json) because the division mixes
real respiratory-equipment products with generic/oral-care/securement items
that do not belong on this framework. Per the mixed-division-mapping policy
(data/identity-vocabulary-policy.json), mapped here at PRODUCT level only
where the product's own name unambiguously identifies a Respiratory Solutions
lot (oxygen therapy / aerosol therapy / respiratory therapy & circuits /
diagnostics & spirometry / sterile water for humidification, per
data/compare-suppliers.json's own respiratory.routeNote) — the remainder of
each division is left held.

Henleys Medical Supplies Limited — "Respiratory Care" division (19 products).
15 mapped; left held: "Humidification" (bare category label, not a named
product), "Bougies & Introducers" and "ATOREX Mucosal Atomization Devices"
(airway/ENT intubation aids, a different NHS Supply Chain framework's scope,
not this one), "Airway Clearance" (a bare duplicate of the named "Airway
Clearance – RC Cornet" product already mapped below).

"Incentive Spirometers" is mapped to resp, NOT diag, per this speciality's
own routeNote: "Incentive spirometers are ward-level respiratory therapy...
a different product doing a different job" from diagnostic spirometry
(Vitalograph's Lot 5 line already carries the diag mapping).

Salter Labs UK Ltd — "Respiratory" division (49 products). 19 mapped on the
same unambiguous-name basis; left held: the Ballard oral-suction/oral-care
line (suction swabs, toothbrush, mouthwash kits — infection-control/oral
care, not an oxygen/aerosol/circuit/diagnostic/humidification product),
Ballard neonatal/paediatric transport and intubation kits (airway management,
a different framework), and every generic securement/tubing/adapter/mask
item with no product-specific name tying it to one lot over another
(TubeCatch, Barbed Tubing Adapter, Adhesive Hydrocolloid Strips, Flex
Extenders, Strapette, Capette, Corrugated and Flex Hose, Round Soft Seal
Mask, Tube Tree, Mask Harness, Accessory Test Lungs).

Run once: python3 scripts/_seed_respiratory_solutions_overrides_1015.py
Then:     python3 scripts/build_differentiator.py
          python3 scripts/stamp_notice.py
          python3 scripts/build_coverage_ledger.py
"""
import json

MAP = "data/differentiator-category-map.json"

# (supplier, exact product name, hub, why)
ENTRIES = [
    ("Henleys Medical Supplies Limited", "Tender Grips Nasal Cannula & Tubing Securement",
     "respiratory:o2",
     "a nasal cannula securement product - oxygen therapy accessory"),
    ("Henleys Medical Supplies Limited", "Medium Concentration Oxygen Masks",
     "respiratory:o2", "an oxygen therapy mask by its own name"),
    ("Henleys Medical Supplies Limited", "Nasal Cannula",
     "respiratory:o2", "an oxygen therapy delivery device by its own name"),
    ("Henleys Medical Supplies Limited", "High Concentration Oxygen Masks",
     "respiratory:o2", "an oxygen therapy mask by its own name"),
    ("Henleys Medical Supplies Limited", "Oxygen Tubing",
     "respiratory:o2", "an oxygen therapy consumable by its own name"),
    ("Henleys Medical Supplies Limited", "FLOWONE CPAP Therapy system",
     "respiratory:resp",
     "a CPAP respiratory therapy system by its own name"),
    ("Henleys Medical Supplies Limited", "Incentive Spirometers",
     "respiratory:resp",
     "this speciality's own routeNote: incentive spirometers are ward-level "
     "respiratory therapy, a different product doing a different job from "
     "diagnostic spirometry (Vitalograph's diag-mapped Lot 5 line)"),
    ("Henleys Medical Supplies Limited", "Space Chambers",
     "respiratory:aero",
     "inhaler holding/spacer chambers - aerosol therapy by their own name"),
    ("Henleys Medical Supplies Limited", "Drug Nebulizers",
     "respiratory:aero", "nebulisers - aerosol therapy by their own name"),
    ("Henleys Medical Supplies Limited", "Aerosol Masks & Face Tents",
     "respiratory:aero", "aerosol therapy delivery devices by their own name"),
    ("Henleys Medical Supplies Limited", "FLAEM AirFeel PEP/OPEP Mucus Clearance Device",
     "respiratory:resp",
     "a PEP/OPEP airway-clearance respiratory therapy device by its own name"),
    ("Henleys Medical Supplies Limited", "FLAEM AirFeel IMT Inspiratory Muscle Trainer",
     "respiratory:resp",
     "an inspiratory muscle training respiratory therapy device by its own name"),
    ("Henleys Medical Supplies Limited", "Airway Clearance – RC Cornet",
     "respiratory:resp",
     "the RC Cornet PEP airway-clearance device - respiratory therapy"),
    ("Henleys Medical Supplies Limited", "FLAEM NebulAir+",
     "respiratory:aero", "a named nebuliser - aerosol therapy"),
    ("Henleys Medical Supplies Limited", "FLAEM HospiNeb",
     "respiratory:aero", "a named nebuliser - aerosol therapy"),

    ("Salter Labs UK Ltd", "DuoTherm ® Humidification System",
     "respiratory:resp",
     "an active humidification system for a respiratory circuit"),
    ("Salter Labs UK Ltd", "Tracheostomy HME",
     "respiratory:resp",
     "a heat and moisture exchanger for a respiratory/tracheostomy circuit"),
    ("Salter Labs UK Ltd", "Active Humidification Circuits & Chambers",
     "respiratory:resp", "respiratory circuit humidification hardware by its own name"),
    ("Salter Labs UK Ltd", "Edith Heat & Moisture Exchangers",
     "respiratory:resp", "a named heat and moisture exchanger for a respiratory circuit"),
    ("Salter Labs UK Ltd", "Ventlab™ High Flow Oxygen Nasal Cannulas with Humidifier",
     "respiratory:o2", "an oxygen therapy delivery device by its own name"),
    ("Salter Labs UK Ltd", "Single Limb Circuit with Exhalation Valve",
     "respiratory:resp", "a ventilator/respiratory breathing circuit by its own name"),
    ("Salter Labs UK Ltd", "Pulmonary Function Test Filters",
     "respiratory:diag", "pulmonary function test consumables - diagnostics & spirometry"),
    ("Salter Labs UK Ltd", "High Concentration, Non-Rebreathing Adult Oxygen Masks",
     "respiratory:o2", "an oxygen therapy mask by its own name"),
    ("Salter Labs UK Ltd", "Elongated CO2/O2 Masks",
     "respiratory:o2", "an oxygen therapy mask by its own name"),
    ("Salter Labs UK Ltd", "Pressure Safe™ Comfort Soft Plus® High Flow Nasal Cannulas",
     "respiratory:o2", "an oxygen therapy delivery device by its own name"),
    ("Salter Labs UK Ltd", "Comfort Soft Plus® High Flow Heated Humidification Nasal Cannulas",
     "respiratory:o2", "an oxygen therapy delivery device by its own name"),
    ("Salter Labs UK Ltd", "Bubble Humidifier, Dry",
     "respiratory:resp", "respiratory circuit humidification hardware by its own name"),
    ("Salter Labs UK Ltd", "Circulaire® Aerosol Masks",
     "respiratory:aero", "an aerosol therapy mask by its own name"),
    ("Salter Labs UK Ltd", "Aerosol Masks",
     "respiratory:aero", "an aerosol therapy mask by its own name"),
    ("Salter Labs UK Ltd", "Aerosol Therapy Face Tents",
     "respiratory:aero", "an aerosol therapy delivery device by its own name"),
    ("Salter Labs UK Ltd", "Lightweight Oxygen Nasal Cannulas",
     "respiratory:o2", "an oxygen therapy delivery device by its own name"),
    ("Salter Labs UK Ltd", "Ventlab™ Oxygen Nasal Cannulas with Fits-All Connector",
     "respiratory:o2", "an oxygen therapy delivery device by its own name"),
    ("Salter Labs UK Ltd", "BiFlo™ Nasal Masks",
     "respiratory:o2", "a nasal oxygen delivery mask by its own name"),
    ("Salter Labs UK Ltd", "Connector Tubing for Bubble Humidifiers",
     "respiratory:resp", "a named component of a respiratory humidification circuit"),
    ("Salter Labs UK Ltd", "Verso™ & Neo-Verso™ Airway Access Adapters & Suction Catheters",
     "respiratory:resp", "airway access/suction components of a respiratory circuit"),

    # Proact Medical Ltd's "Airway Management" division is otherwise correctly
    # out of scope for this framework (Guedel airways, ET tubes, laryngeal
    # airways, BVM resuscitators, bougies - the separate Airway Management
    # Products framework's territory). Three named products within it are
    # unambiguously Respiratory Solutions products and mapped at product level;
    # the rest of the division is left held.
    ("Proact Medical Ltd", "Pro Breathe Nebuliser Kits",
     "respiratory:aero", "a nebuliser kit - aerosol therapy by its own name"),
    ("Proact Medical Ltd", "Pro Breathe Oxygen Masks",
     "respiratory:o2", "an oxygen therapy mask by its own name"),
    ("Proact Medical Ltd", "Pro Breathe Nasal Cannulae",
     "respiratory:o2", "an oxygen therapy delivery device by its own name"),
]

doc = json.load(open(MAP))
known = {(e["supplier"], e["division"]) for e in doc["entries"]}
vocab = json.load(open("data/compare-suppliers.json"))["specialities"]
legal = {"%s:%s" % (s, t) for s, v in vocab.items() for t in (v.get("types") or {})}

added = 0
for supplier, name, hub, why in ENTRIES:
    assert hub in legal, "not in gated vocabulary: %r" % hub
    key = (supplier, name)
    if key in known:
        print("already present, skipping:", supplier, "/", name)
        continue
    doc["entries"].append({
        "supplier": supplier,
        "division": name,
        "products": 1,
        "categories": [],
        "examples": [name],
        "hub": hub,
        "notTaxonomy": False,
        "evidence": "the supplier's own site filing, read by scripts/crawl_supplier_site.py",
        "why": why,
        "decidedIn": "_seed_respiratory_solutions_overrides_1015.py",
        "kind": "product-override",
    })
    added += 1

doc["counts"]["pairs"] = len(doc["entries"])
json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
print("added %d product-override entries" % added)
