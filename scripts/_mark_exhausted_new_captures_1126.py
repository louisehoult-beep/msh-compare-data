#!/usr/bin/env python3
"""26/11/2026: record the 24/11 captures that were checked and have no publishable
route, and refresh the Pressure Area Care entry after Harvest Healthcare published.
Internal picker bookkeeping only. Run once."""
import json

P = "docs/framework-coverage-exhausted.json"
L = {f["framework"]: f for f in json.load(open("data/coverage-ledger.json"))["frameworks"]}
UPDATES = {
 "Pressure Area Care and Patient Handling": (["Harvest Healthcare"],
  "Harvest Healthcare (07210261 proved on its own terms page) published from its own categories; mixed remainder (nurse call alarms, fall mats, some shear-relief and other items) held."),
 "Laboratory Diagnostics, Point of Care Testing and Pathology Managed Services": (["EUROIMMUN UK"],
  "EUROIMMUN UK: euroimmun.co.uk now redirects to the German parent's worldwide site (euroimmun.com); no NHS Supply Chain catalogue line for the UK entity, so no-parent-catalogue-credit-to-uk-subsidiary holds it. The 24/11 capture is also mostly disease and technique page names (nav-labels-are-not-products)."),
 "Total Orthopaedic Solutions 3": (["Adler Ortho UK Limited"],
  "Adler Ortho UK Limited: adlerortho.com is the parent's worldwide site (UK arm listed on its contact page only); no NHS Supply Chain catalogue line found, so no-parent-catalogue-credit-to-uk-subsidiary holds it."),
 "Urology and Bowel Management": (["Fairmont Medical Products Limited", "RB Medical Engineering Ltd"],
  "Fairmont (no readable catalogue, 13/09) and RB Medical (robots.txt disallows, 11/09): recorded crawl refusals stand."),
 "Advanced Wound Care": (["Integra LifeSciences (Integra Neurosciences)"],
  "Integra: recorded crawl refusal of 13/09 stands."),
 "Radiotherapy Treatment Systems and Associated Options and Related Services": (["Eckert & Ziegler BEBIG"],
  "Eckert & Ziegler BEBIG: UK entity recorded dissolved 05/03/2024 (read 18/08); the 24/11 capture is from www.ezag.com and is held under dissolved-awardee-successor-uncertain."),
}
doc = json.load(open(P))
by = {f["framework"]: f for f in doc["frameworks"]}
for name, (suppliers, why) in UPDATES.items():
    e, f = by[name], L[name]
    for s in suppliers:
        if isinstance(e["suppliersChecked"], list) and s not in e["suppliersChecked"]:
            e["suppliersChecked"].append(s)
    e["checkedOn"] = "2026-11-26"
    e["coverageAtCheck"] = "%s%% (%s/%s)" % (f["coverage"], f["suppliersPublished"], f["suppliersAwarded"])
    e["reason"] = "RE-CHECK 26/11/2026: %s PREVIOUS ENTRY FINDINGS STAND: %s" % (why, e.get("reason", ""))
json.dump(doc, open(P, "w"), ensure_ascii=False, indent=2)
open(P, "a").write("\n")
print("updated %d entries" % len(UPDATES))
