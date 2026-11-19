#!/usr/bin/env python3
"""One-off: add the Wound closure speciality (`closure`), 12/11/2026.

WHY. NHS Supply Chain's Wound Closure framework (2025/S 000-001071, 19/01/2026 to
18/01/2030, no extension) had no home in the Compare tab. Sutures, haemostats, tissue
adhesives and skin staplers were filed under theatres:theatre ("General theatre
consumables") with the stated reason "no dedicated suture category exists". So a rep
could not pick "sutures" and see Meril's Mitsu next to Ethicon's Vicryl without wading
through drapes and pens. Meril UK (a Hub member desk) was promised sutures in Compare
by Fri 27/11/2026.

SOURCES, ALL READ 12/11/2026:
  * Framework name, dates, "no option to extend", the 39-supplier award list and the
    five sub-categories: the contract launch brief,
    https://www.supplychain.nhs.uk/product-information/contract-launch-brief/wound-closure/
  * Which sub-lot each supplier holds: NHS Supply Chain's own "Product Matrix by Lot"
    (Product-Matrix-Wound-Closure-8-September-2026.xlsx, linked from that brief). Three
    suppliers on the brief (BSN Medical, R&D Surgical, Sela Medical UK) have no row in
    the matrix, so no sub-lot is shown for them rather than one guessed.
  * Brands: the NHS Supply Chain catalogue items already cached in data/nhssc-cache.json
    (the buyer's own list), and for Meril and Uniplex the supplier's own product pages
    (Meril's 21 closure pages re-fetched 12/11/2026, all live). Every other row says
    "Not verified".

WHAT MOVES. Add-only for the vocabulary; existing mappings that were filed under
theatres:theatre ONLY for want of a closure category are re-filed to closure:* (each
gets `movedFrom` so the change is traceable). Nothing else is renamed or merged.
Mixed NHSSC ranges are NOT mapped (Medtronic "V-Loc / Endo Stitch" holds a clip
applier; Gore "GORE-TEX Suture" holds grafts; AMS "LiquiBandFix8" is mesh fixation).

Both vocabulary copies move together (verify.py gates them against each other):
  data/compare-suppliers.json and data/differentiator-category-map.json.

Run once, then: python3 scripts/build_differentiator.py && python3 verify.py
"""
import json

TODAY = "2026-11-12"
BRIEF = "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/wound-closure/"
MATRIX = ("NHS Supply Chain Product Matrix by Lot, Wound Closure, updated 8 September 2026 "
          "(linked from the contract launch brief)")
NOTV = "Not verified — brand-level detail not yet captured; see the supplier's own site."

SPEC = "closure"
LABEL = "Wound closure (sutures, haemostats, adhesives, skin staplers)"
TYPES = {
    "sutures": "Sub-lot 1 · Surgical sutures (absorbable and non-absorbable, incl. tapes)",
    "haemo": "Sub-lot 2 · Haemostats (flowables, sealants, fabrics, sponges, powders, bone wax)",
    "adhes": "Sub-lot 3 · Tissue adhesives",
    "stapler": "Sub-lot 4 · Skin staplers and staple removers",
    "strips": "Sub-lot 5 · Wound closure strips",
}
T = {"Sutures": "sutures", "Haemostats": "haemo", "Tissue Adhesives": "adhes",
     "Skin Staplers": "stapler", "Wound Closure Strips": "strips"}

# (brief wording, matrix wording or None, ref or None, own-site url or None, brands, note)
ROWS = [
    ("Advanced Medical Solutions Ltd", "AMS LTD", "Advanced Medical Solutions (AMS)",
     "https://www.admedsol.com/", "RESORBA · LiquiBand",
     "NHS Supply Chain catalogue: RESORBA absorbable and non-absorbable sutures, LiquiBand tissue adhesives."),
    ("Anser Medical Ltd", "ANSER MEDICAL LTD", "Anser Medical", "https://www.ansermedical.com", NOTV, ""),
    ("Aquilant Ltd", "AQUILANT LIMITED", "Aquilant Limited", None, NOTV,
     "The brief notes Pierson Surgical's Peters Surgical products moved to Aquilant under new codes."),
    ("Artivion UK Ltd", "ARTIVION UK LTD", "Artivion UK Ltd", "https://artivion.com/", NOTV, ""),
    ("Assut UK Ltd", "ASSUT UK LTD", "Assut UK LTD", None, NOTV, ""),
    ("B Braun Medical Ltd", "B BRAUN MEDICAL LTD", "B. Braun Medical", "https://www.bbraun.co.uk/en.html",
     "Monomax · Monoplus · Monosyn · Novosyn · Safil · Histoacryl",
     "NHS Supply Chain catalogue: Monomax, Monoplus, Monosyn, Novosyn and Safil sutures; Histoacryl tissue adhesive."),
    ("Baxter Healthcare Ltd", "BAXTER HEALTHCARE LTD", "Baxter Healthcare Ltd", "https://www.baxterhealthcare.co.uk",
     "Floseal · Coseal · Hemopatch · Tisseel · Artiss · Ostene",
     "NHS Supply Chain catalogue: Floseal flowable haemostat, Coseal sealant, Hemopatch, Tisseel and Artiss fibrin sealants, Ostene bone wax."),
    ("BSN Medical Ltd", None, "Essity UK Limited", "https://www.essity.com/company/essity-in-the-world/uk-roi/", NOTV,
     "BSN Medical is part of Essity."),
    ("Chemence Ltd", "CHEMENCE LTD", "Chemence Medical", "https://chemencemedical.com/", "Exofin · Exofin Fusion · Derma+Flex",
     "NHS Supply Chain catalogue: Exofin and Exofin Fusion 2-octyl cyanoacrylate skin adhesives, Derma+Flex topical skin adhesive."),
    ("Crest Medical Ltd", "CREST MEDICAL LTD", "Crest Medical Ltd", "https://www.crestmedical.co.uk", "Blue Dot",
     "Own site: Blue Dot sterile skin closure strips."),
    ("Critical Healthcare Ltd", "CRITICAL HEALTHCARE LTD", "Critical Healthcare", "https://www.criticalhealthcare.com/", NOTV, ""),
    ("Delta Surgical Ltd", "DELTA SURGICAL LIMITED", "Delta Surgical", "https://www.deltasurgical.co.uk/", NOTV, ""),
    ("Gentell UK Ltd", "GENTELL UK LIMITED", "Gentell UK Ltd", "https://www.gentell.co.uk", NOTV, ""),
    ("GBUK Ltd (novated from GS Medical Healthcare Ltd)", "GBUK LTD (novated from GS Medical LTD)", "GBUK Group",
     "https://gbukgroup.com/", "Pahacel · Surgiclean · Scrofalon",
     "The launch brief lists \"GS Medical Healthcare Ltd (novating to GBUK Ltd)\"; the 8 September 2026 product matrix shows the novation done. NHS Supply Chain catalogue: Pahacel oxidised regenerated cellulose, Surgiclean and Scrofalon polysaccharide haemostats."),
    ("Healthium Medtech UK Ltd", "HEALTHIUM MEDTECH UK LTD", "Healthium Medtech UK", "https://qclose.com/", "Clinicel",
     "NHS Supply Chain catalogue: Clinicel knitted and fibrillar oxidised cellulose haemostats. Suture brands not yet verified."),
    ("Ideal Medical Solutions Ltd", "IDEAL MEDICAL SOLUTIONS LTD", "Ideal Medical Solutions", None, NOTV, ""),
    ("Johnson & Johnson Medical Ltd", "JOHNSON & JOHNSON MEDICAL LTD", "Johnson & Johnson MedTech",
     "https://www.jnjmedtech.com/en-GB",
     "Ethicon: Vicryl · Prolene · Mersilk · Ethibond Excel · Ethilon · Surgicel · Spongostan · Surgiflo · Dermabond Prineo",
     "NHS Supply Chain catalogue: Ethicon Vicryl, Prolene, Mersilk, Ethibond Excel and Ethilon sutures; Surgicel, Spongostan and Surgiflo haemostats; Dermabond Prineo skin closure system."),
    ("KCI Medical Ltd", "KCI MEDICAL LIMITED (3M)", "Solventum (3M Health Care)", "https://www.solventum.com/en-gb/home/", NOTV,
     "The product matrix names it \"KCI Medical Limited (3M)\"."),
    ("Kebomed UK Ltd", "KEBOMED (UK) LTD", "Kebomed UK Ltd", "https://www.kebomed.co.uk/", NOTV, ""),
    ("Lenience UK Ltd", "LENIENCE UK LTD", "Lenience UK Ltd", None, NOTV, ""),
    ("Mediq Healthcare UK Ltd", "MEDIQ HEALTHCARE UK LIMITED", "Mediq Healthcare UK Ltd", "https://www.mediq.co.uk", NOTV, ""),
    ("Medline Industries Ltd", "MEDLINE INDUSTRIES LTD", "Medline Industries", "https://www.medline.eu/uk", NOTV, ""),
    ("Medtronic Ltd", "MEDTRONIC LIMITED", "Medtronic", "https://www.medtronic.com/en-gb", NOTV, ""),
    ("Meril UK Ltd", "MERIL UK LIMITED", "Meril UK Pvt Ltd", "https://www.merillife.com/our-products/endo-surgery",
     "Mitsu · Megasorb · Filapron · Filaxyn · Filaprop · Filamide · Filasilk · Mericron XL · Merisoft · Meristeel · Pinion · Filatwine · MeriGlu · MeriFix · Mirus",
     "Own product pages (merillife.com, re-read 12/11/2026): Mitsu, Mitsu AB, Mitsu C+ and Mitsu FST polyglactin sutures; Megasorb, Megasorb Plus and Megasorb Rapid PGA; Filapron poliglecaprone; Filaxyn polydioxanone; Pinion barbed; Merisoft chromic catgut; Filaprop polypropylene; Filamide nylon; Filasilk and Mericron XL; Meristeel steel; Filatwine endoloop ligature; MeriGlu and MeriFix topical skin adhesives; Mirus disposable skin stapler and staple remover. The only supplier on all four of sub-lots 1 to 4. Haemostat brand not yet verified."),
    ("OscarTech UK Ltd", "OSCARTECH UK", "OscarTech UK", "https://www.oscartech-uk.com/", NOTV, ""),
    ("P3 Medical Ltd", "P3 MEDICAL LIMITED", "P3 Medical Ltd", None, NOTV, ""),
    ("Pearsalls Ltd", "PEARSALLS LTD", "Pearsalls Ltd", None, NOTV, ""),
    ("R&D Surgical Ltd", None, "R&D Surgical Ltd", "https://www.rdsurgical.com/", NOTV, ""),
    ("Reflex Medical Ltd", "REFLEX MEDICAL LIMITED", "Reflex Medical Limited", "https://reflexmedical.co.uk/", NOTV, ""),
    ("Reliance Medical Ltd", "RELIANCE MEDICAL LTD", "Reliance Medical", "https://www.reliancemedical.co.uk/", NOTV, ""),
    ("Richardson Healthcare Ltd", "RICHARDSON HEALTHCARE LTD", "Richardson Healthcare", None, NOTV, ""),
    ("SAI Medical Solutions Ltd", "SAI MEDICAL SOLUTIONS LTD", "SAI Medical Solutions Ltd", None, NOTV, ""),
    ("Sela Medical UK Ltd", None, "Sela Medical UK Ltd", "https://selamedical.co.uk/", NOTV, ""),
    ("Stryker UK Ltd", "STRYKER UK LTD", "Stryker", "https://www.stryker.com/gb/en/index.html", NOTV, ""),
    ("TFX Group Ltd", "TELEFLEX MEDICAL UK", "TFX Group Ltd (Teleflex Medical)",
     "https://www.teleflex.com/emea/en/product-areas/surgery/index.html", NOTV,
     "The product matrix names it \"Teleflex Medical UK\"."),
    ("T.J Smith & Nephew Ltd", "SMITH & NEPHEW HEALTHCARE LTD", "Smith+Nephew", "https://www.smith-nephew.com/en-gb", NOTV,
     "The product matrix names it \"Smith & Nephew Healthcare Ltd\"."),
    ("Uniplex UK Ltd", "UNIPLEX UK LTD", "Uniplex", "https://uniplexuk.com/",
     "Silkus · Prolus · Nylus · Estralus · Okcel · Cutanplast",
     "Own site: Silkus silk, Prolus polypropylene, Nylus polyamide and Estralus polyester sutures; Okcel oxidised cellulose and Cutanplast gelatin haemostats."),
    ("Vascutek Ltd", "VASCUTEK LTD", "Terumo Aortic", None, NOTV, "Vascutek trades as Terumo Aortic."),
    ("Winners First Trading Ltd", "WINNERS FIRST TRADING LIMITED", "Winners First Trading Limited", None, NOTV, ""),
]

# Lots read from the matrix 12/11/2026 (scratch copy parsed with openpyxl).
MATRIX_LOTS = {
    "AMS LTD": ["Sutures", "Haemostats", "Tissue Adhesives"],
    "ANSER MEDICAL LTD": ["Haemostats"],
    "AQUILANT LIMITED": ["Sutures", "Haemostats"],
    "ARTIVION UK LTD": ["Haemostats"],
    "ASSUT UK LTD": ["Sutures", "Haemostats"],
    "B BRAUN MEDICAL LTD": ["Sutures", "Haemostats", "Tissue Adhesives"],
    "BAXTER HEALTHCARE LTD": ["Haemostats"],
    "CHEMENCE LTD": ["Tissue Adhesives"],
    "CREST MEDICAL LTD": ["Wound Closure Strips"],
    "CRITICAL HEALTHCARE LTD": ["Sutures"],
    "DELTA SURGICAL LIMITED": ["Haemostats"],
    "GENTELL UK LIMITED": ["Sutures", "Haemostats", "Wound Closure Strips"],
    "GBUK LTD (novated from GS Medical LTD)": ["Haemostats", "Wound Closure Strips"],
    "HEALTHIUM MEDTECH UK LTD": ["Sutures", "Haemostats", "Skin Staplers"],
    "IDEAL MEDICAL SOLUTIONS LTD": ["Haemostats"],
    "JOHNSON & JOHNSON MEDICAL LTD": ["Sutures", "Haemostats", "Tissue Adhesives"],
    "KCI MEDICAL LIMITED (3M)": ["Wound Closure Strips"],
    "KEBOMED (UK) LTD": ["Tissue Adhesives"],
    "LENIENCE UK LTD": ["Haemostats"],
    "MEDIQ HEALTHCARE UK LIMITED": ["Wound Closure Strips"],
    "MEDLINE INDUSTRIES LTD": ["Skin Staplers"],
    "MEDTRONIC LIMITED": ["Sutures", "Haemostats", "Skin Staplers"],
    "MERIL UK LIMITED": ["Sutures", "Haemostats", "Tissue Adhesives", "Skin Staplers"],
    "OSCARTECH UK": ["Tissue Adhesives", "Skin Staplers", "Wound Closure Strips"],
    "P3 MEDICAL LIMITED": ["Haemostats"],
    "PEARSALLS LTD": ["Haemostats"],
    "REFLEX MEDICAL LIMITED": ["Sutures", "Skin Staplers", "Wound Closure Strips"],
    "RELIANCE MEDICAL LTD": ["Wound Closure Strips"],
    "RICHARDSON HEALTHCARE LTD": ["Wound Closure Strips"],
    "SAI MEDICAL SOLUTIONS LTD": ["Sutures"],
    "SMITH & NEPHEW HEALTHCARE LTD": ["Wound Closure Strips"],
    "STRYKER UK LTD": ["Wound Closure Strips"],
    "TELEFLEX MEDICAL UK": ["Haemostats", "Skin Staplers"],
    "UNIPLEX UK LTD": ["Sutures", "Haemostats"],
    "VASCUTEK LTD": ["Haemostats"],
    "WINNERS FIRST TRADING LIMITED": ["Sutures"],
}

ROUTE = [{
    "name": "NHS Supply Chain — Wound Closure (1 lot, 5 sub-categories, 39 suppliers, 12 of them new)",
    "dates": "19/01/2026 – 18/01/2030 (no option to extend)",
    "endsOn": "2030-01-18",
    "url": BRIEF,
}]
ROUTE_NOTE = (
    "One lot with five sub-categories: sutures (absorbable and non-absorbable), haemostats "
    "(flowables, sealants, fabrics, sponges, powders, bone wax), tissue adhesives, skin staplers "
    "and removers, and wound closure strips. Reference 2025/S 000-001071. All 39 suppliers on "
    "NHS Supply Chain's launch brief are listed (read 12/11/2026). Which sub-category each one "
    "holds is read from NHS Supply Chain's own Product Matrix by Lot (updated 8 September 2026), "
    "so picking a product type shows exactly the suppliers awarded it. BSN Medical, R&D Surgical "
    "and Sela Medical UK are on the brief's list but have no row in that matrix, so no "
    "sub-category is shown for them. Delisted at the start of the framework: Becton Dickinson "
    "UK (Arista, Avitene, Progel), Creed Medical, Q-Surgical, Prosys International (moved to the "
    "Mesh framework), Pierson Surgical (Peters Surgical now via Aquilant) and Unisurge "
    "International. Brands come from the NHS Supply Chain catalogue or the supplier's own product "
    "pages; rows marked \"Not verified\" have no product detail yet. Previous framework: "
    "2021/S 000-013272 (some trusts' call-offs still run under it, e.g. to 2028)."
)


def supplier_rows():
    out = []
    for co, mx, ref, url, brands, note in ROWS:
        lots = MATRIX_LOTS.get(mx) if mx else None
        t = [T[x] for x in lots] if lots else []
        if lots:
            held = ("Sub-categories held (" + MATRIX + "): " +
                    ", ".join(lots).replace("Tissue Adhesives", "Tissue adhesives")
                    .replace("Skin Staplers", "Skin staplers").replace("Wound Closure Strips", "Wound closure strips") + ".")
        else:
            held = ("Named on the launch brief's supplier list, but has no row in NHS Supply Chain's "
                    "8 September 2026 product matrix, so no sub-category is shown.")
        base = ("Named on NHS Supply Chain's own contract launch brief for the Wound Closure framework "
                "as \"%s\". " % co)
        if brands == NOTV:
            text = base + held + " Product range not yet verified for this speciality."
        else:
            text = base + held + " " + note
        if brands == NOTV and note:
            text += " " + note
        row = {"co": co, "ref": ref, "t": t, "brands": brands, "note": text.strip(), "iss": []}
        row["url"] = url or BRIEF
        out.append(row)
    return out


def main():
    # 1. canonical speciality list
    p = json.load(open("data/products.json"))
    if not any(s["id"] == SPEC for s in p["SPECS"]):
        p["SPECS"].append({"id": SPEC, "label": LABEL})
        json.dump(p, open("data/products.json", "w"), ensure_ascii=False, indent=2)

    sm = json.load(open("data/speciality-map.json"))
    if not any(s["id"] == SPEC for s in sm["canonicalSpecialities"]):
        sm["canonicalSpecialities"].append({
            "id": SPEC, "label": LABEL,
            "nhssc": "Medical and Surgical Consumables — Wound Closure (2025/S 000-001071; 1 lot, 5 sub-categories, 39 suppliers)",
            "eClass": "UNVERIFIED — not read from the live eClass list this session",
            "addedBecause": "No Hub speciality held the Wound Closure framework; sutures, haemostats and "
                            "adhesives were filed under General theatre consumables. Added 12/11/2026.",
        })
        json.dump(sm, open("data/speciality-map.json", "w"), ensure_ascii=False, indent=2)

    # 2. gated vocabulary + supplier table
    cs = json.load(open("data/compare-suppliers.json"))
    # One spelling per company across the file (verify.py: "spelled more than one way").
    # The row shows the spelling the Compare tab already uses for that master record;
    # the brief's own wording stays in the note.
    spell = {}
    for sk, blk in cs["specialities"].items():
        if sk == SPEC:
            continue
        for r in blk.get("suppliers") or []:
            spell.setdefault(r.get("ref") or r["co"], []).append(r["co"])
    rows = supplier_rows()
    for r in rows:
        seen = spell.get(r["ref"]) or []
        if r["ref"] in seen:
            r["co"] = r["ref"]
        elif seen:
            r["co"] = max(set(seen), key=seen.count)
        else:
            r["co"] = r["ref"]
    cs["specialities"][SPEC] = {
        "label": LABEL, "route": ROUTE, "routeNote": ROUTE_NOTE,
        "types": TYPES, "suppliers": rows,
    }
    json.dump(cs, open("data/compare-suppliers.json", "w"), ensure_ascii=False, indent=1)

    # 3. working vocabulary copy + re-filed mappings
    cm = json.load(open("data/differentiator-category-map.json"))
    cm["vocabulary"][SPEC] = dict(TYPES)
    moved = 0

    def move(e, hub, why):
        nonlocal moved
        e["movedFrom"] = e.get("hub")
        e["hub"] = hub
        e["why"] = why
        e["movedIn"] = "Wound closure speciality added %s (scripts/_add_wound_closure_speciality_1112.py)" % TODAY
        moved += 1

    MERIL_SUT = {"Filamide Nylon Non-Absorbable Suture", "Filapron Poliglecaprone 25 Absorbable Suture",
                 "Filaprop Polypropylene Non-Absorbable Suture", "Filasilk Braided Silk Non-Absorbable Suture",
                 "Filaxyn Polydioxanone Absorbable Suture", "Megasorb Plus Antibacterial PGA Suture",
                 "Megasorb PGA Absorbable Suture", "Megasorb Rapid PGA Suture",
                 "Mericron XL Silk Non-Absorbable Suture", "Merisoft Chromic Catgut Absorbable Suture",
                 "Meristeel Stainless Steel Surgical Suture", "Mitsu Polyglactin 910 Absorbable Suture",
                 "Mitsu AB Antibacterial Absorbable Suture", "Mitsu C+ Coated Polyglactin Absorbable Suture",
                 "Mitsu FST Fast Absorbing Suture", "Pinion Barbed Absorbable Suture",
                 "Filatwine Chromic Catgut Endoloop Ligature"}
    MERIL_STAP = {"Mirus Disposable Skin Stapler", "Mirus Skin Staple Remover"}
    MERIL_ADH = {"Meri Glu Topical Skin Adhesive", "Merifix Topical Skin Adhesive"}
    JJ_SUT = {"Vicryl / Prolene / Monocryl (Ethicon sutures)", "Prolene (Ethicon non-absorbable sutures)",
              "Mersilk (Ethicon non-absorbable sutures)", "Ethibond Excel (Ethicon non-absorbable sutures)",
              "Ethilon (Ethicon non-absorbable sutures)"}
    JJ_HAEM = {"Surgicel oxidised cellulose (haemostat)", "Spongostan gelatin sponge (haemostat)",
               "Surgicel SNoW (haemostat)", "Surgiflo haemostatic matrix (haemostat)",
               "Surgicel Fibrillar (haemostat)"}
    GBUK_HAEM = {"Pahacel (haemostat)", "Surgiclean / Scrofalon (haemostats)"}

    for e in cm["entries"]:
        s, k, d, term, hub = e.get("supplier"), e.get("kind"), e.get("division"), e.get("term"), e.get("hub")
        if hub != "theatres:theatre" and not (s == "Crest Medical Ltd" and hub == "wound:fa"):
            continue
        if s == "Meril UK Pvt Ltd" and k == "product-override":
            if d in MERIL_SUT:
                move(e, "closure:sutures", "A surgical suture or ligature by its own Meril product page "
                     "(re-read 12/11/2026); Wound Closure framework sub-lot 1.")
            elif d in MERIL_STAP:
                move(e, "closure:stapler", "A skin stapler / staple remover by its own Meril product page "
                     "(re-read 12/11/2026); Wound Closure framework sub-lot 4.")
            elif d in MERIL_ADH:
                move(e, "closure:adhes", "A topical skin adhesive by its own Meril product page "
                     "(re-read 12/11/2026); Wound Closure framework sub-lot 3.")
        elif s == "Johnson & Johnson MedTech" and k == "nhssc-term":
            if term in JJ_SUT:
                move(e, "closure:sutures", "Every example is an Ethicon suture in the NHS Supply Chain "
                     "catalogue; Wound Closure framework sub-lot 1 now has its own category.")
            elif term in JJ_HAEM:
                move(e, "closure:haemo", "Every example is an absorbable haemostat in the NHS Supply Chain "
                     "catalogue; Wound Closure framework sub-lot 2 now has its own category.")
        elif s == "GBUK Group" and k == "nhssc-term" and term in GBUK_HAEM:
            move(e, "closure:haemo", "Every example is a haemostat in the NHS Supply Chain catalogue; "
                 "Wound Closure framework sub-lot 2.")
        elif s == "Uniplex" and k is None and d == "Sutures":
            move(e, "closure:sutures", "Silkus, Prolus, Nylus and Estralus sutures (own site); Wound Closure "
                 "framework sub-lot 1.")
        elif s == "Uniplex" and k is None and d == "Haemostats":
            move(e, "closure:haemo", "Okcel oxidised cellulose and Cutanplast gelatin haemostats (own site); "
                 "Wound Closure framework sub-lot 2.")
        elif s == "Crest Medical Ltd" and k == "product-override" and "Skin Closure Strips" in (d or ""):
            e["movedFrom"] = hub
            e["hub"] = ["wound:fa", "closure:strips"]
            e["movedIn"] = "Wound closure speciality added %s: closure strips also filed under sub-lot 5" % TODAY
            moved += 1

    # New NHSSC-term mappings for ranges that were unmapped only for want of a category.
    NEW = [
        ("Advanced Medical Solutions (AMS)", "RESORBA (haemostats/sutures)", "closure:sutures",
         "All 123 cached items are RESORBA absorbable or non-absorbable sutures."),
        ("Advanced Medical Solutions (AMS)", "LiquiBand (tissue adhesive)", "closure:adhes",
         "All cached items are LiquiBand tissue adhesives."),
        ("B. Braun Medical", "Safil / Novosyn / Monosyn / Monomax / MonoPlus (sutures)", "closure:sutures",
         "All 177 cached items are absorbable sutures (Monomax, Monoplus, Monosyn, Novosyn, Safil)."),
        ("Baxter Healthcare Ltd", "Floseal Haemostatic Matrix (flowable haemostatic matrix, >20 years cardiac surgery use)",
         "closure:haemo", "All cached items are Floseal haemostat products."),
        ("Baxter Healthcare Ltd", "Coseal (synthetic surgical sealant); Hemopatch (sealing patch for intraoperative bleeding/postoperative leakage)",
         "closure:haemo", "All cached items are haemostat sealants and patches (Coseal, Hemopatch)."),
        ("Baxter Healthcare Ltd", "Tisseel (fibrin sealant, ~40 years clinical use); Artiss (fibrin sealant for plastic/reconstructive/burns surgery)",
         "closure:haemo", "All cached items are Tisseel/Artiss fibrin sealant haemostat products."),
        ("Baxter Healthcare Ltd", "Ostene (haemostatic bone wax alternative); Peri-Strips / Tissue-Guard (tissue reinforcement, same Advanced Surgery division)",
         "closure:haemo", "The one cached item is Ostene bone wax; bone wax is in Wound Closure sub-lot 2."),
        ("Healthium Medtech UK", "AbGel / Clinicel / Sterispon / Truwax (haemostats)", "closure:haemo",
         "All cached items are Clinicel oxidised cellulose haemostats."),
    ]
    nhssc = json.load(open("data/nhssc-cache.json"))["products"]
    for k_, rec in nhssc.items():
        if not k_.startswith("NPC:"):
            continue
        it = (rec.get("items") or [{}])[0]
        if rec.get("supplier") in ("B BRAUN MEDICAL LTD", "CHEMENCE LTD", "JOHNSON & JOHNSON MEDICAL LTD") \
                and (it.get("desc") or "").startswith("Tissue Adhesives"):
            NEW.append((rec["supplier"], k_, "closure:adhes",
                        "The catalogue item is a tissue adhesive (%s)." % it.get("name")))
    have = {(e.get("supplier"), e.get("term")) for e in cm["entries"] if e.get("kind") == "nhssc-term"}
    added = 0
    for sup, term, hub, why in NEW:
        if (sup, term) in have or term not in nhssc:
            continue
        items = nhssc[term].get("items") or []
        cm["entries"].append({
            "kind": "nhssc-term", "supplier": sup, "term": term, "division": None,
            "products": len(items), "categories": [],
            "examples": [i.get("desc") for i in items[:8]],
            "hub": hub, "notTaxonomy": False,
            "evidence": "NHS Supply Chain public catalogue, cached by scripts/refresh_nhssc_cache.py; "
                        "decision made on the catalogue's own item descriptions above",
            "why": why, "decidedIn": "Wound closure speciality, %s" % TODAY,
        })
        added += 1
    json.dump(cm, open("data/differentiator-category-map.json", "w"), ensure_ascii=False, indent=1)

    # Keep the Uniplex part file in step so a re-merge cannot undo the move.
    pp = "data/differentiator-map-parts/Uniplex.json"
    part = json.load(open(pp))
    for dcs in part["decisions"]:
        if dcs.get("division") == "Sutures" and dcs.get("hub") == "theatres:theatre":
            dcs.update(hub="closure:sutures", movedFrom="theatres:theatre",
                       movedIn="Wound closure speciality added %s" % TODAY)
        if dcs.get("division") == "Haemostats" and dcs.get("hub") == "theatres:theatre":
            dcs.update(hub="closure:haemo", movedFrom="theatres:theatre",
                       movedIn="Wound closure speciality added %s" % TODAY)
    json.dump(part, open(pp, "w"), ensure_ascii=False, indent=1)
    print("speciality added; %d mapping(s) moved, %d NHSSC term(s) added" % (moved, added))


if __name__ == "__main__":
    main()
