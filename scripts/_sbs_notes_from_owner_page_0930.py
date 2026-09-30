#!/usr/bin/env python3
"""_sbs_notes_from_owner_page_0930.py - NHS SBS framework rows on the supplier seed,
restated from NHS SBS's own framework pages (read 30/09/2026).

WHY. 58 hand-tracked seed rows name an NHS SBS framework with a note carried from the
supplier directory retired 06/08/2026 ("unverified - check at source"). Nine of them
also state a lot ("Lot: Lot 5d"), and company-report.js prints the note verbatim, so
members saw a lot that no owner source confirms. Lou's standing rule (30/09/2026) is that
a lot comes only from the framework owner's own publication, never guessed.

WHAT NHS SBS PUBLISHES. Each framework page lists the lot titles and ONE flat "Supplier
Details" list. It names no supplier against a lot. So no lot can be shown for any SBS
row, and the note now says so plainly.

MATCHING. A seed supplier counts as named on the SBS list only when
company_match.key() of its name or one of its seed aliases equals key() of an SBS
spelling exactly. There is no fuzzy or substring matching. A supplier not matched keeps
the directory provenance, minus any lot, and says the owner's list does not name it
under that name.

Only frameworks[] entries for SBS10142 / SBS10015 / SBS10247 are touched: `note` and
`url`. Idempotent. Run from the repo root:  python3 scripts/_sbs_notes_from_owner_page_0930.py
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import company_match as cm
from seed_format import write_like

READ_ON = "30/09/2026"
EVIDENCE = {
 "SBS10142": {
  "title": "Advanced Wound Care and Lymphoedema Products and Services",
  "url": "https://www.sbs.nhs.uk/services/framework-agreements/advanced-wound-care-and-lymphoedema-products-and-services/",
  "lots": 12,
  "suppliers": [
   "Inotec AMD Ltd",
   "Accel Heal",
   "Advanced Medical Solutions Ltd",
   "Advancis Medical",
   "Alliance Healthcare",
   "Anser Medical",
   "Arjo UK Ltd",
   "Aspire Pharma Ltd",
   "B Braun Medical Ltd",
   "Baxter Healthcare Ltd",
   "Becton, Dickinson UK Limited",
   "Chemence Ltd",
   "Clarity Medtech",
   "Clinimed",
   "CliniSupplies Ltd",
   "Coloplast Ltd",
   "ConvaTec Ltd",
   "Credenhill Ltd",
   "Creed Medical Ltd",
   "Delta Surgical Ltd",
   "ekare Europe BV",
   "Ennogen Healthcare Ltd",
   "Essity UK Ltd",
   "Evolan Pharma AB",
   "Farla Medical Healthcare Limited",
   "Flen Health Ltd",
   "Frontier Therapeutics Ltd",
   "Gardamed Limited",
   "GS Medical Healthcare Ltd",
   "Haddenham Healthcare Ltd",
   "Healogics Wound Healing Centres CIC",
   "Healthy.io",
   "Huntleigh Healthcare",
   "Insight Direct UK Ltd",
   "Joint Operations",
   "KCI Medical",
   "L&R Medical UK Ltd",
   "Mediq Healthcare",
   "Medi UK Ltd",
   "Medical Data Solutions and Services Ltd",
   "Medicareplus International Limited",
   "Molnlycke Health Care Ltd",
   "Oswell Penda Pharmaceutical Ltd",
   "Paul Hartmann Ltd",
   "Phoenix Healthcare Distribution",
   "Pioneer Wound Healing & Lymphoedema Care Ltd",
   "Richardson Healthcare Ltd",
   "Schulke",
   "Sigvaris Britain Ltd",
   "Talley",
   "The Bullen Healthcare Group",
   "Thesis Technology Products Ltd",
   "TJ Smith and Nephew Ltd (T/A Smith & Nephew)",
   "Uniplex UK Ltd",
   "Urgo Limited",
   "Vernacare"
  ]
 },
 "SBS10015": {
  "title": "Acute and Community Health and Social Care Equipment Products and Services",
  "url": "https://www.sbs.nhs.uk/services/framework-agreements/acute-and-community-health-and-social-care-equipment-products-and-services/",
  "lots": 7,
  "suppliers": [
   "Abena UK Ltd",
   "Accora Limited",
   "Aidapt Bathrooms Limited",
   "AJM Healthcare",
   "Apollo Healthcare Technologies Ltd",
   "Arjo UK Ltd",
   "BES Healthcare Ltd",
   "CareFlex Limited",
   "Chas A Blatchford & Sons Ltd",
   "Direct Healthcare Group Limited",
   "Drive DeVilbiss Healthcare Limited",
   "Essity UK Ltd",
   "Etac Limited",
   "Five Mobility Ltd",
   "Frontier Therapeutics Ltd",
   "GBUK Group Ltd (formerly Care and Independence)",
   "Harvest Healthcare Ltd",
   "Healthcare Matters",
   "Helping Hand Company (Ledbury) Limited",
   "Hill-Rom Limited",
   "Invacare Limited",
   "IQ Medical Limited",
   "James Leckey Design Limited",
   "KATNIC Ltd T/A H&M Health & Mobility",
   "LINET UK",
   "Lisclare Limited",
   "Mangar International Limited T/A Winncare UK Limited",
   "Medequip Assistive Technology Ltd",
   "Medstrom Ltd",
   "Ontex Healthcare (UK ) Limited",
   "Opcare Limited",
   "Oska Care Limited",
   "Otto Bock Healthcare Plc",
   "Peacocks Medical Group",
   "Prism UK Medical Ltd",
   "Renray Healthcare Limited",
   "Ross Auto Engineering Limited T/A Ross Care",
   "Seating Matters",
   "Stryker UK Limited",
   "Sunrise Medical Limited",
   "Talley Group Limited",
   "Trulife Limited",
   "Vivid.Care",
   "Winncare PAC Limited"
  ]
 },
 "SBS10247": {
  "title": "Orthotics Products and Services including Prosthetic Services",
  "url": "https://www.sbs.nhs.uk/services/framework-agreements/orthotics-products-and-services/",
  "lots": 3,
  "suppliers": [
   "Ability Matters Group",
   "Blatchford Limited",
   "Buchanan Orthotics Limited",
   "Chaneco Limited",
   "Darco UK Ltd (formerly V-M Orthotics Ltd)",
   "Denovo Healthcare Ltd",
   "Hugh Steeper Limited",
   "MAG Orthotics Limited",
   "Medfac UK Ltd",
   "Otto Bock Healthcare PLC",
   "Peacocks Medical Group Limited",
   "Prestige Healthcare (London) Ltd",
   "Talarmade Limited",
   "Taycare Medical Ltd"
  ]
 }
}

# Source 5 (Lou, 30/09/2026): NHS SBS publishes no supplier-by-lot list, so a public
# body's own call-off notice that names the framework reference, the lot AND the supplier
# may carry a lot, labelled with the buyer and notice. Keyed by (ref, SBS list spelling).
# Each was read at source on 30/09/2026. A notice giving the framework's title but not its
# reference (Essity, Gloucestershire Health & Care, CF 2b1d60c8) does not qualify.
LOTS = {
 ("SBS10142", "Healthy.io"): {
  "lot": "Lot 7, Advanced Wound Care and Lymphoedema Digital Products",
  "buyer": "Hywel Dda University Health Board",
  "notice": "Sell2Wales contract award notice AUG533527, 07/08/2025",
  "url": "https://www.sell2wales.gov.wales/search/search_switch.aspx?ID=154502"},
 ("SBS10142", "Medi UK Ltd"): {
  "lot": "Lot 2, Advanced Wound Care and Lymphoedema Compression Bandages and Hosiery",
  "buyer": "County Durham and Darlington NHS Foundation Trust",
  "notice": "Contracts Finder award notice, 12/09/2025",
  "url": "https://www.contractsfinder.service.gov.uk/notice/8340efe5-e05d-470b-b3e0-df993b5feaae"},
 ("SBS10142", "Haddenham Healthcare Ltd"): {
  "lot": "Lot 2, Advanced Wound Care and Lymphoedema Compression Bandages and Hosiery",
  "buyer": "County Durham and Darlington NHS Foundation Trust",
  "notice": "Contracts Finder award notice, 12/09/2025",
  "url": "https://www.contractsfinder.service.gov.uk/notice/95a24c44-b361-450e-84f4-c7556664dca4"},
 ("SBS10142", "Alliance Healthcare"): {
  "lot": "Lot 8, Delivery",
  "buyer": "NHS Mid and South Essex (procured by Attain)",
  "notice": "Contracts Finder award notice (North West Ostomy Service call-off), 31/10/2023",
  "url": "https://www.contractsfinder.service.gov.uk/notice/e8c11519-e356-4cf5-b521-74b0ec9beb92"},
}

SEED = "data/supplier-seed.json"


def ref_of(name):
    for ref, e in EVIDENCE.items():
        if ref in name or e["title"].lower() in name.lower():
            return ref
    return None


def main():
    seed = json.load(open(SEED))
    matched, unmatched, lots_removed, lotted = [], [], [], []
    for s in seed["suppliers"]:
        keys = {cm.key(n) for n in [s.get("name", "")] + list(s.get("aliases") or []) if n}
        for f in s.get("frameworks") or []:
            ref = ref_of(f.get("name", ""))
            if not ref:
                continue
            e = EVIDENCE[ref]
            hit = next((x for x in e["suppliers"] if cm.key(x) in keys), None)
            old = f.get("note", "")
            if old.startswith("Lot:"):
                lots_removed.append((s["name"], old.split(".")[0]))
            if hit:
                f["note"] = ("Named on NHS SBS's own supplier list for %s (%s), read %s, as "
                             "\u201c%s\u201d. NHS SBS publishes the framework's %d lots but "
                             "not which lot each supplier holds, so no lot is shown."
                             % (e["title"], ref, READ_ON, hit, e["lots"]))
                lot = LOTS.get((ref, hit))
                if lot:
                    f["note"] = ("%s, per a call-off under this framework by %s (%s), which names "
                                 "the framework reference, the lot and this supplier. NHS SBS "
                                 "itself does not publish which lot each supplier holds; its own "
                                 "supplier list for %s (%s), read %s, names this supplier as "
                                 "\u201c%s\u201d." % (lot["lot"], lot["buyer"], lot["notice"],
                                 e["title"], ref, READ_ON, hit))
                    f["lotSourceUrl"] = lot["url"]
                    lotted.append(s["name"])
                else:
                    f.pop("lotSourceUrl", None)
                matched.append(s["name"])
            else:
                f["note"] = ("Reference carried from the Hub's former supplier directory, "
                             "retired 06/08/2026. NHS SBS's own supplier list for %s (%s), "
                             "read %s, does not name this supplier under this name, so its "
                             "place on the framework is not confirmed. NHS SBS does not publish "
                             "which lot each supplier holds." % (e["title"], ref, READ_ON))
                unmatched.append(s["name"])
            f["url"] = e["url"]
    fmt = write_like(SEED, seed)
    print("format", fmt)
    print("matched %d, not named %d" % (len(matched), len(unmatched)))
    print("not named:", sorted(unmatched))
    print("lot claims removed:", lots_removed)
    print("call-off lots (source 5):", sorted(lotted))


if __name__ == "__main__":
    main()
