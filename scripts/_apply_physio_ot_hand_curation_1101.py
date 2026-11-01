#!/usr/bin/env python3
"""Apply the Physiotherapy and Occupational Therapy hand-curation (task o276, 01/11/2026).

Input: Hub/Supplier-Consultations/physio-ot-hand-curation-2026-11-01.json (Companies House and
each company's own site read live on 01/11/2026). 10 VERIFIED suppliers get a `handCurated`
block (legal name, number, status, domain, evidence URLs, caveats, provenance "hand-curated
01/11/2026"). Phoenix Medical Ltd also gets its address-tier website link (domain-proof-tier
policy), which is what lets the coverage ledger list it as crawlable. The 5 NOT VERIFIED get a
`handCurated` block with the held reason and what would settle it; no link, domain or
publication is added for them.

Run from the repo root: python3 scripts/_apply_physio_ot_hand_curation_1101.py <curation.json>
"""
import json, sys

SEED = "data/supplier-seed.json"
PROV = "hand-curated 01/11/2026"
FW = "Physiotherapy and Occupational Therapy"
REF = "2023/S 000-033230"

CAVEATS = {
    "Eureka Physiocare Ltd": "NHS Supply Chain words the award \"Eureka Physiocare (previously Splice Cast)\". The Splice Cast link is NOT supported: SPLICE CAST LIMITED (05102276) is a separate active company, and Eureka's Companies House previous names show only Eureka Physiocare (Newtown) Ltd. Do not repeat the Splice Cast wording.",
    "Medfac UK Ltd (previously Kinetec Medical Products UK Ltd)": "MEDFAC UK LTD (08608060) and KINETEC MEDICAL PRODUCTS UK LIMITED (09748313) are separate companies; never merged. The \"previously\" wording is not supported by Companies House. Which of the two holds this award is not settled by the register.",
    "Koolpak Ltd": "Entity matched to the award BY NAME ONLY (KOOLPAK LIMITED 02808528). The site says \"CMUK Visual Safety Ltd also trading as Koolpak Ltd\"; CMUK VISUAL SAFETY LIMITED (03951452) shares the registered address, so which entity holds the contract is not proven.",
    "Phoenix Medical Ltd": "PHOENIX MEDICAL LTD. 08921091 (Chelmsford) is NOT Phoenix Medical Supplies Limited (03603234, phoenixmedical.co.uk). Sister company PHOENIX MEDICAL GROUP LTD (08370979) shares the address. Domain proved by registered-office address match (site gives no number); phoenixmedical.com itself did not respond.",
    "DJO UK Ltd (Enovis)": "Entity attribution rests on the address match only: the site names Enovis Corporation, not the UK legal entity.",
    "Essity UK Limited": "Entity-to-award link is by the framework name only. BSN MEDICAL LIMITED (04085346) is a non-trading shell; Essity UK Limited is the trading entity. Catalogue read was the French-language edition.",
    "Kinetik Medical Devices": "Companies House 06778337 only; a different dissolved company 06388994 (also once called Kinetik Medical Devices) is not this one.",
}

SETTLE = {
    "Algeo": "Read Find a Tender award notice 024917-2024 and algeos.com in a normal browser session (the site is behind a Cloudflare bot challenge; do not bypass it).",
    "Medline Industries": "The UK Medline catalogue, or the NHS Supply Chain catalogue lines for this supplier on this framework (medline.com bot-challenged; medline.co.uk and medlineuk.com did not respond).",
    "Cuxson Gerrard & Company Limited": "NHS Supply Chain catalogue lines for this supplier on this framework (own site names no physiotherapy or occupational therapy product).",
    "Orca Medical Ltd": "NHS Supply Chain catalogue lines for Orca on this framework (own site sells diagnostic ultrasound, no treatment product).",
    "Reliance Medical": "A physiotherapy or occupational therapy product named on the supplier's trade portal or in NHS Supply Chain catalogue lines (product list is behind a trade portal).",
}


def main(path):
    cur = json.load(open(path))
    seed = json.load(open(SEED))
    by = {s["name"]: s for s in seed["suppliers"]}
    for s in cur["suppliers"]:
        rec = by[s["awardName"]]
        block = {
            "provenance": PROV, "framework": FW, "frameworkRef": REF,
            "verdict": s["verdict"], "legalName": s["legalName"],
            "companyNumber": s["companyNumber"], "companyStatus": s["status"],
            "domain": s["domain"], "evidenceUrls": s["evidenceUrls"],
            "readNote": s["note"],
        }
        if s["verdict"] == "VERIFIED":
            if s["awardName"] in CAVEATS:
                block["caveat"] = CAVEATS[s["awardName"]]
        else:
            block["heldReason"] = s["note"]
            block["toSettle"] = SETTLE[s["awardName"]]
            block["published"] = False
        rec["handCurated"] = block
        if s["awardName"] == "Phoenix Medical Ltd" and not rec.get("links"):
            rec["links"] = [{
                "label": "Company website", "url": "https://" + s["domain"] + "/",
                "route": "address-tier",
                "source": ("Proved group.phoenixmedical.com by registered-office address match on 2026-11-01 "
                           "(domain-proof-tier policy, data/identity-vocabulary-policy.json), hand-curated 01/11/2026: "
                           "the site footer names Phoenix Medical Ltd, 5 Lonebarn Link, Chelmsford CM2 5AR, matching "
                           "Companies House 08921091 (PHOENIX MEDICAL LTD.). The site prints no number. Not "
                           "phoenixmedical.co.uk, which belongs to Phoenix Medical Supplies Limited (03603234).")}]
    with open(SEED, "w") as f:
        json.dump(seed, f, ensure_ascii=False, separators=(",", ":"))
    print("ok", len(cur["suppliers"]))


if __name__ == "__main__":
    main(sys.argv[1])
