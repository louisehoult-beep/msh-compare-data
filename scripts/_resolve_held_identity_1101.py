#!/usr/bin/env python3
"""Held supplier-identity items o611, o619, o629, o640, o643, o474 (Lou, 01/11/2026).

Every fact below was read at a primary source on 01/11/2026: Companies House
(find-and-update.company-information.service.gov.uk), the Find a Tender OCDS API
(www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages/<ocid>), NHS Supply
Chain's contract launch briefs, and the companies' own sites. o639 (Syringa) is
a merge, done through company-aliases/merge_duplicates.py, not here.

Run from the repo root: python3 scripts/_resolve_held_identity_1101.py
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "data", "supplier-seed.json")
CH = "https://find-and-update.company-information.service.gov.uk/company/"
FTS = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages/"

doc = json.load(open(SEED))
by = {s["name"]: s for s in doc["suppliers"]}


def note(name, text, **extra):
    r = by[name]
    r["identityNote"] = text
    for k, v in extra.items():
        r[k] = v


note("AttoLife",
     "HELD, successor not credited (^o611, checked 01/11/2026). The award is to the entity the Find a Tender "
     "award notice for Laboratory Diagnostics (028831-2023, " + FTS + "ocds-h6vhtk-0397e8) names: \"iDna Genetics "
     "Limited trading as Anglia DNA Services\" (Norfolk) = ATTOLIFE LTD, Companies House 05061695 (registered name "
     "IDNA GENETICS LIMITED until 04/06/2024). 05061695 has been IN ADMINISTRATION since 13/08/2026 "
     "(administrators Rishi Karia and Grace Jones of Parker Andrews Limited, Norwich, and Deviesh R Raikundalia; " + CH +
     "05061695/insolvency). attolife.co.uk is now published by SENTINEL NEWCO 1 LIMITED (17385754), whose footer says "
     "\"formerly trading business of AttoLife Limited\"; Companies House shows it incorporated 06/08/2026, SIC 74990 "
     "non-trading, registered office Wantage, first filing a charge on 02/09/2026 (" + CH + "17385754). Nothing read says "
     "the framework award transferred to it: no filing, no notice from NHS Supply Chain (its brief still reads \"AttoLife "
     "Ltd (formerly Anglia DNA)\"), no statement on the site. Per policy dissolved-awardee-successor-uncertain the award "
     "stays with 05061695, flagged in administration; Sentinel Newco 1 is NOT credited and attolife.co.uk is NOT attached "
     "to this record. To settle: a Companies House filing or administrators' notice naming the transfer, or NHS Supply "
     "Chain listing Sentinel Newco 1 on the framework. Not verified.",
     companyNumberCandidate={
         "number": "05061695", "registeredName": "ATTOLIFE LTD", "companyStatus": "administration",
         "incorporated": "2004-03-03", "confidence": "candidate",
         "matchedOn": "Find a Tender award notice 028831-2023 names iDna Genetics Limited trading as Anglia DNA Services "
                      "(Norfolk); Companies House 05061695 was IDNA GENETICS LIMITED until 2024-06-04 (previousNames "
                      "above), read 2026-11-01. In administration since 2026-08-13, so NOT written to companyNumber."})

note("Aquilant Endoscopy Limited",
     "RESOLVED (^o619, checked 01/11/2026). The award stays with AQUILANT ENDOSCOPY LIMITED, Companies House 03402556, "
     "which Companies House shows ACTIVE (" + CH + "03402556). FUJIFILM Healthcare UK Limited bought only the Fujifilm "
     "endoscopy business from it (asset purchase agreed 30/09/2025, completed 01/12/2025: Fujifilm capital equipment, "
     "Fujifilm's endotherapeutic and accessory devices, the FUJIFILM medwork therapeutic portfolio and the sales, service "
     "and technical team; https://www.fujifilm.com/uk/en/news/FUJIFILM-Healthcare-UK-completes-acquisition-British-"
     "Aquilant-Endoscopy-Limited). Seller is part of the Healthcare21 group. Neither Fujifilm release mentions NHS Supply "
     "Chain, frameworks or customer-contract transfer, and NHS Supply Chain's briefs for the ENT Endoscopes and Endoscopy, "
     "Endourology and Oncology Ablation frameworks still name \"Aquilant Endoscopy\" and do not name Fujifilm or "
     "Healthcare21. So the award is NOT credited to FUJIFILM Healthcare UK; the Fujifilm product range moved to it, the "
     "framework position is not shown to have. The older \"ceased trading\" wording in the deep dive is superseded by "
     "this note: only the Fujifilm line was sold. To settle whether the framework supply moved: NHS Supply Chain's "
     "supplier change record. Not verified.")

note("Ecohydra Technologies Ltd",
     "HELD, no successor (^o629, checked 01/11/2026). The award is to EcoHydra Technologies Limited, Companies House "
     "05248154 (Find a Tender award notice 000335-2023, " + FTS + "ocds-h6vhtk-02ad97, names it, Middlesex). It is in "
     "CREDITORS' VOLUNTARY LIQUIDATION, wound up 16/04/2026, liquidator John Pearson, Station House, Midland Drive, "
     "Sutton Coldfield (" + CH + "05248154/insolvency). ecohydra.com still answers but only as a GoDaddy \"under "
     "maintenance\" page footed \"Copyright 2026 EcoHydra\" with no legal entity, company number or product, so a trading "
     "website is not evidence of a trading company or of a successor (policy dissolved-awardee-successor-uncertain, applied "
     "to a liquidation). The award stays with 05248154 flagged in liquidation; no other company is credited and no domain "
     "or catalogue is attached. To settle: a Companies House filing, liquidator's notice or EcoHydra statement naming who "
     "now owns the brand and the NHS Supply Chain supply. Not verified.")

note("Vyaire Medical Products Limited",
     "HELD, Jaeger link unproven (^o643a, checked 01/11/2026). The Find a Tender award notice for Patient Temperature "
     "Management (018561-2023, " + FTS + "ocds-h6vhtk-03a5ac) names \"Vyaire Medical Products Limited\", Basingstoke "
     "RG24 8NA = Companies House 10187476 (registered office then Chineham Gate, Basingstoke). It is in CREDITORS' VOLUNTARY "
     "LIQUIDATION (wind-up resolution 27/02/2025, liquidator Mark Reynolds, Valentine & Co, Barnet; " + CH +
     "10187476/insolvency and /filing-history). JAEGER MEDICAL UK LIMITED (01939558, Grove House, Chineham Court, "
     "RG24 8AG) is a different company number, formerly VYAIRE UK 236 LIMITED until 15/05/2025; nothing read links it to "
     "this award: the US parent's 2024 Chapter 11 sold its ventilation unit to ZOLL and respiratory diagnostics to Trudell "
     "Medical (no UK entity named), and NHS Supply Chain lists no Jaeger entity on Patient Temperature Management. The "
     "award stays with 10187476 flagged in liquidation; Jaeger Medical UK is NOT credited with it. To settle: a "
     "NHS Supply Chain supplier-change record or a Companies House/liquidator document naming the transfer. Not verified.")

note("Novus Medical Ltd",
     "HELD, identity unconfirmed (^o643b, checked 01/11/2026). NHS Supply Chain's Patient Temperature Management brief "
     "names \"Novus Medical Ltd\" (Lot 3, Patient temperature management equipment). The Find a Tender award notice for the "
     "same framework (018561-2023, " + FTS + "ocds-h6vhtk-03a5ac) instead names \"Novus Med Ltd\", Halifax HX3 8SX, a "
     "supplier ID (GB-FTS-86242) that is not the one the same company uses on its other NHS Supply Chain awards "
     "(Kenilworth/Honiley, Warwickshire). Companies House: NOVUS MED LTD 10242963 (Kenilworth, SIC 47749, the Hub's "
     "Novus Med record) and NOVUS MEDICAL LIMITED 09117117 (Southampton, SIC 32500; named CHINE CONSULTING LIMITED until "
     "17/11/2023) are different companies; neither is at Halifax, and no source read ties either to Lot 3. Name similarity "
     "is not evidence, so neither number is attached and the two records stay separate. The award is published under the "
     "name exactly as NHS Supply Chain writes it, marked unconfirmed. To settle: Novus's own site or its NHS Supply Chain "
     "catalogue entry stating the registered entity. Not verified.",
     identityUnconfirmed=True)

note("Medfac UK Ltd (previously Kinetec Medical Products UK Ltd)",
     "NOT A DUPLICATE, kept separate (^o640, checked 01/11/2026). Two different Companies House numbers. MEDFAC UK LTD "
     "08608060 (London, Gough Square; " + CH + "08608060) has NO previous names on the register, so it did not change its "
     "name from Kinetec. KINETEC MEDICAL PRODUCTS UK LIMITED 09748313 (Wellingborough, SIC 33190/47749; " + CH +
     "09748313) is a separate company that is still on the register (active, with a proposal to strike off). They are "
     "related, not identical: both list Robert John Donaldson and Maria Leonardina Spronken as officers. The Find a Tender "
     "award notices name them separately: Orthoses, Podiatry and Immobilisation (009725-2025, " + FTS + "ocds-h6vhtk-0471ef) "
     "names \"Medfac UK Ltd\" (London); Physiotherapy and Occupational Therapy (024917-2024, " + FTS + "ocds-h6vhtk-041734) "
     "names \"Kinetec Medical Products UK Ltd\" (London). NHS Supply Chain's brief words the Physiotherapy name as \"Medfac "
     "UK Ltd (previously Kinetec...)\"; the register does not support a rename, so per Lou's rule (same Companies House "
     "number merges, different numbers stay separate) the records are NOT merged and the award is kept as NHS Supply Chain "
     "words it. kinetecuk.com prints MEDFAC UK LTD 08608060 in its footer (proved 23/09/2026), so the domain stays with "
     "Medfac. Which of the two holds the Physiotherapy award is not settled by the register. To settle: NHS Supply Chain "
     "supplier record for the Physiotherapy framework.")

note("Medfac UK Ltd",
     "Not a duplicate of \"Medfac UK Ltd (previously Kinetec Medical Products UK Ltd)\" (^o640, 01/11/2026): that record "
     "is the Physiotherapy and Occupational Therapy award, which the Find a Tender notice (024917-2024) gives to KINETEC "
     "MEDICAL PRODUCTS UK LTD, a different company (09748313) from MEDFAC UK LTD (08608060). See that record.")

# Accoson: resolved by the register + the award notice.
r = by["AC Cossor & Son (Surgical) Ltd"]
r["companyNumberCandidate"] = {
    "number": "00601273", "registeredName": "A. C. COSSOR & SON(SURGICAL) LIMITED", "companyStatus": "active",
    "incorporated": "1958-03-26", "confidence": "candidate",
    "matchedOn": "Find a Tender award notice 019858-2024 for Patient Monitoring Equipment (" + FTS + "ocds-h6vhtk-0399b8) "
                 "names \"A. C. Cossor & Son (Surgical) Limited\", Egham; Companies House 00601273 is A. C. COSSOR & "
                 "SON(SURGICAL) LIMITED, Blays Cottage, Englefield Green, Egham, active, SIC 32500, formerly ACCOSON LTD "
                 "(13/02/2019 to 21/05/2019), the only company on the register of that name. Read 2026-11-01. Not written "
                 "to companyNumber: the website does not print this number (see companyNumberNote)."}
r["companyNumberNote"] = (
    "RESOLVED at entity level (^o474, checked 01/11/2026). The awarded entity is A. C. COSSOR & SON(SURGICAL) LIMITED, "
    "Companies House 00601273 (candidate above). accoson.com's \"Company registration no. 135969\" is not that company's "
    "number: it is the digits of SC135969, GM INSTRUMENTS LIMITED, Greig House, Annick Road, Irvine (" + CH + "SC135969), "
    "printed without the \"SC\" prefix, and the footer address is that company's registered office. The register ties the "
    "two: Companies House shows GM Instruments Limited as the person with significant control of 00601273 (75% or more of "
    "shares and votes, notified 18/12/2025, previously Raj Singh since 21/12/2023), and Raj Shekhar Singh is a director of "
    "both. So 135969 is the parent's number, not a second claim to the Cossor entity and not a collision with an unrelated "
    "company. The earlier statement that it is \"part of HCE Medical Group since 2018\" is not supported by the register "
    "filings read and should not be repeated. Per policy parent-subsidiary-award-credit the award credits to 00601273 as "
    "NHS Supply Chain names it; GM Instruments' financials are not published against it. companyNumber is left unset until "
    "confirm_company_numbers.py or a number on the company's own site proves it.")
r.pop("identityUnconfirmed", None)

with open(SEED, "w") as f:
    json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
print("ok")
