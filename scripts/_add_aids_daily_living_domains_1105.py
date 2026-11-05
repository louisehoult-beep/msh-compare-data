#!/usr/bin/env python3
"""One-off: record four proved domains for Aids for Daily Living suppliers
(framework-coverage batch, redo of 04/11/2026 work, run 05/11/2026).
Registration-number proof where the site publishes one; alias proof for Cefndy
(a Denbighshire County Council trading service: no Companies House number exists)."""
import json, sys
sys.path.insert(0, "scripts")
import seed_format
SEED = "data/supplier-seed.json"
CH = "https://find-and-update.company-information.service.gov.uk/company/"
D = "2026-11-05"
PROOFS = {
 "Essential Healthcare Solutions (UK) Ltd": dict(domain="www.essential-healthcare.com", url="https://www.essential-healthcare.com/",
   num="04991941", route="website-registration",
   evidence='footer states "Registered Company 04991941"; Companies House confirms ESSENTIAL HEALTHCARE SOLUTIONS (UK) LIMITED, active, registered office Essential Enterprise Village, Field Head Lane, Birstall, Batley, WF17 9BN (matches the site address)'),
 "Chiltern Invadex (UK) Limited": dict(domain="www.chilterninvadex.co.uk", url="https://www.chilterninvadex.co.uk/",
   num="04704248", route="website-registration",
   evidence='about page states "Chiltern Invadex (UK) Limited ... Registered at Companies House: 04704248", registered address Lancots Lane, Sutton Oak, St Helens WA9 3EX; Companies House confirms CHILTERN INVADEX (UK) LIMITED, active, same registered office'),
 "Langham Gordon Ellis": dict(domain="www.langham-ge.co.uk", url="https://www.langham-ge.co.uk/",
   num="00231734", route="website-registration",
   evidence='footer states "Registered in England Company Reg. No. 00231734"; Companies House confirms GORDON ELLIS & CO., active, registered office Trent Lane, Castle Donington, DE74 2PY (the seed already records Langham as a Gordon Ellis & Co product brand)'),
}
CEFNDY = ("Cefndy Healthcare", "www.cefndy.com", "https://www.cefndy.com/")
def main():
    seed = json.load(open(SEED))
    by = {s["name"]: s for s in seed["suppliers"]}
    for name, p in PROOFS.items():
        r = by[name]
        r["domain"] = p["domain"]
        r["links"].append({"label": "Company website", "url": p["url"], "route": p["route"],
            "source": f'Proved by registration number on {D}: {p["evidence"]}.'})
        r["companyNumberProof"] = {"number": p["num"], "route": p["route"], "url": p["url"],
            "evidence": p["evidence"], "checkedOn": D}
    r = by[CEFNDY[0]]
    r["domain"] = CEFNDY[1]
    r["links"].append({"label": "Company website", "url": CEFNDY[2], "route": "alias",
        "source": (f'Proved on {D} by the existing seed alias "cefndy.com" (assigned 29/08/2026 from the site itself): '
                   'the site footer names "Cefndy Healthcare & Manufacturing, Cefndy Road, Rhyl, Denbighshire LL18 2HG" and its About page says '
                   'Cefndy is part of Denbighshire County Council. A council trading service has no Companies House number, so no registration proof exists or is claimed.')})
    seed_format.write_like(SEED, seed)
    print("done")
main()
