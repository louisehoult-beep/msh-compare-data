#!/usr/bin/env python3
"""One-off: apply Lou's rulings of 09/10/2026 to the seed and the category map.

  ^o621  Future Health Works: domain myrecovery.com proved at the THIRD domain-proof
         tier (first-party link to its own compliance-register entry).
  ^o630  Jabbla UK Ltd: jabbla.co.uk proved at the FOURTH tier (first-party
         former-name statement matching the Companies House name history).
  ^o631  Tobii Dynavox Ltd: HOLD. The two divisions mapped to digital:aac are
         un-mapped (held, not deleted) because no framework award or NHSSC
         catalogue lists a Tobii Dynavox product for the UK entity.
  ^o632  Iansyst Ltd: DSA computing divisions stay under it:hw (IT & computer
         equipment); the ruling is recorded on the map entries.
Policy: data/identity-vocabulary-policy.json (domain-proof-tier, no-parent-catalogue-
credit-to-uk-subsidiary, general-purpose-computing-not-assistive-technology).
"""
import json

SEED = "data/supplier-seed.json"
MAP = "data/differentiator-category-map.json"
PART = "data/differentiator-map-parts/Tobii Dynavox Ltd.json"

seed = json.load(open(SEED))
by = {s["name"]: s for s in seed["suppliers"]}

fhw = by["Future Health Works Ltd. (t/a myrecovery & msk.ai)"]
assert not fhw.get("links")
fhw["links"] = [{
    "label": "Company website",
    "url": "https://www.myrecovery.com",
    "route": "compliance-register-link",
    "source": ("Proved myrecovery.com at the THIRD domain-proof tier (first-party link to the "
               "company's own compliance-register entry; domain-proof-tier, ruled 09/10/2026, "
               "^o621). The site's footer links to https://tiscreport.org/company/gb/09336986"
               "#compliance (read 2026-10-09). Companies House confirms 09336986 is "
               "incorporated 02/12/2014 and was named FUTURE HEALTH WORKS LTD until 11/2024; "
               "its current name is HOPPER HEALTHCARE LTD (renamed 09/2026), registered office "
               "3rd Floor 1 Ashley Road, Altrincham WA14 2DT. The TISCreport page itself "
               "returned HTTP 403 to automated fetch, so the link target is proved by the "
               "number in the URL, not by page text."),
    "checkedOn": "2026-10-09",
}]
fhw["companyNumberCandidate"] = {
    "number": "09336986", "registeredName": "HOPPER HEALTHCARE LTD",
    "companyStatus": "active", "incorporated": "2014-12-02", "confidence": "candidate",
    "matchedOn": ("Companies House overview for 09336986 read 2026-10-09: previous names FUTURE "
                  "HEALTH WORKS LTD (to 11/2024) and HEALTHCARE OUTCOMES PERFORMANCE COMPANY "
                  "LIMITED, now HOPPER HEALTHCARE LTD. Tied to the site by the TISCreport link "
                  "(domain-proof tier 3). NOT a number printed in text on the company's site, so "
                  "it must be proved by confirm_company_numbers.py before it is written to "
                  "companyNumber."),
}
fhw.pop("companyNumberNote", None)

jab = by["Jabbla UK Ltd"]
for l in jab["links"]:
    if "jabbla.co.uk" in l.get("url", ""):
        l["route"] = "former-name-statement"
        l["checkedOn"] = "2026-10-09"
        l["source"] = ("Proved jabbla.co.uk at the FOURTH domain-proof tier (first-party "
                       "former-name statement matching Companies House name history; "
                       "domain-proof-tier, ruled 09/10/2026, ^o630). https://www.jabbla.co.uk/"
                       "about-us/ states \"Previously named Techcess Communications, the brand name "
                       "changed to Jabbla UK in 2021\"; Companies House 06251446 JABBLA UK LIMITED "
                       "records the former name TECHCESS COMMUNICATIONS LIMITED to 09/09/2021. The "
                       "site's trading address (Kempton House, Grantham NG31 7LE) differs from the "
                       "registered office (3 Castlegate, Grantham NG31 6SF); the fourth tier does "
                       "not need them to match. Earlier discovery note: " + l.get("source", ""))
json.dump(seed, open(SEED, "w"), separators=(",", ":"), ensure_ascii=False)

cm = json.load(open(MAP))
for e in cm["entries"]:
    if e["supplier"] == "Tobii Dynavox Ltd" and e.get("hub") == "digital:aac":
        e["heldMapping"] = {"hub": e["hub"], "why": e["why"]}
        e["hub"] = None
        e["why"] = ("HELD 09/10/2026 on Lou's ruling (^o631, policy no-parent-catalogue-credit-to-"
                    "uk-subsidiary): no framework award or NHS Supply Chain catalogue line lists "
                    "this product for the UK entity, so it is not published. The earlier mapping "
                    "is kept in heldMapping for reinstatement if an award/NHSSC listing appears.")
    if e["supplier"] == "Iansyst Ltd" and e.get("hub") == "it:hw":
        e["why"] += (" CONFIRMED 09/10/2026 on Lou's ruling (^o632, policy general-purpose-"
                     "computing-not-assistive-technology): stays under IT & computer equipment, "
                     "never digital:tec.")
json.dump(cm, open(MAP, "w"), indent=1, ensure_ascii=False)
open(MAP, "a").write("\n")

part = json.load(open(PART))
part["heldOn"] = "2026-10-09"
part["heldBecause"] = ("Lou's ruling ^o631: no parent-catalogue credit to a UK subsidiary without "
                       "an award- or NHSSC-level product match. Decisions moved to heldDecisions.")
part["heldDecisions"], part["decisions"] = part["decisions"], []
json.dump(part, open(PART, "w"), indent=1, ensure_ascii=False)
print("done")
