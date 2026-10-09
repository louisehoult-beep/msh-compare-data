"""One-off: record Electrosurgical Consumables and Related Accessories as
exhausted after this run's work (coverage batch, 27/09/2026), so a future
run doesn't re-investigate it from scratch. Run once, then delete.
"""
import json

PATH = "docs/framework-coverage-exhausted.json"

ENTRY = {
    "framework": "Electrosurgical Consumables and Related Accessories",
    "checkedOn": "2026-09-27",
    "coverageAtCheck": "36.4% (12/33), up from 30.3% (10/33) this run",
    "suppliersChecked": [
        "Fannin (UK) Limited", "Olympus (KeyMed)", "Medline Industries",
        "NISSHA Medical Technologies", "Sela Medical UK Ltd",
        "Healthcare 25 Ltd", "Sterimed Medical Implants UK Ltd",
        "Surgica Limited", "J & M Medical",
    ],
    "reason": (
        "All 8 remaining actionable items checked, plus 2 resolved this "
        "run. Resolved: \"KCI Medical Limited (Solventum)\" (confirmed "
        "verbatim on NHS Supply Chain's own contract launch brief) is the "
        "existing Solventum (3M Health Care) record, already carrying a "
        "recorded site refusal -- no new products. \"Surgica Limited\" "
        "cannot be resolved to a confirmable company by any route (no "
        "company number on the award notice or on bidstats.uk/justskim.ai; "
        "its own site, surgica.co.uk, is copyrighted to \"Surgica Gmbh\" "
        "and gives only a shared Vantage London formation-agent address, "
        "not proof under the domain-proof-tier policy guard) -- published "
        "per the unconfirmable-awardee policy, no company number/domain "
        "attached, so it will always show as needDomain here and that is "
        "correct, not a gap. Published: Bolton Surgical Limited (131 "
        "reusable/single-use monopolar and bipolar forceps, disposable "
        "electrodes and diathermy generator cables -- all explicitly named "
        "\"Monopolar\"/\"Bipolar\"/\"Electrode\"/\"Diathermy\", confirmed "
        "against the supplier's own /product/electrosurgery/ URL "
        "structure; also corrected 50 of its OWN existing product-override "
        "entries that a prior bulk split, ^o550, had mis-filed as "
        "surgical:forceps/surgical:scissor purely on the word \"Forceps\"/"
        "\"Scissors\" in the name, missing the \"Bipolar\" that makes them "
        "a different, generator-powered product) and Ideal Medical "
        "Solutions (\"THOR Electrodes\" and \"Bipolar Forceps\", 2 of its "
        "41 flat range names, confirmed via ideal-ms.com's own product "
        "pages). J & M Medical: found and added its own site "
        "(jmmedical.co.uk, confirmed via its footer's \"J & M Medical NE "
        "Ltd\" reference, an existing alias on the record) but its "
        "robots.txt refuses automated reading -- freshly refused, not "
        "forced. Checked with no route: the 4 remaining publishedElsewhere "
        "suppliers (Fannin, Olympus (KeyMed), Medline, NISSHA) all already "
        "carry recorded crawl refusals, so re-crawling them is forbidden "
        "by the brief's own rule; Sela Medical UK Ltd's real crawled range "
        "(neuro-interventional coils/stents/guidewires, plus surgical "
        "adhesives/endoscopic devices) carries no electrosurgical item by "
        "name; Healthcare 25 Ltd's held capture is the same documented "
        "nav-labels-are-not-products failed-capture case already recorded "
        "elsewhere for this supplier (site nav headings, not products); "
        "Sterimed Medical Implants UK Ltd has no confirmable website (its "
        "only candidate is a LinkedIn page giving a shared virtual-office "
        "address and no site link) -- not an identity ambiguity, just no "
        "site found, so left and noted rather than escalated. No "
        "permitted route left on any of the 8."
    ),
    "wouldReopenIf": (
        "Any of the 4 refused publishedElsewhere suppliers' refusal is "
        "reopened and a fresh crawl succeeds; Sela Medical UK Ltd is "
        "re-crawled with a different/wider product set; Healthcare 25 "
        "Ltd's site is recrawled and reaches real product pages instead "
        "of navigation labels; a confirmable website surfaces for Sterimed "
        "Medical Implants UK Ltd or Surgica Limited; J & M Medical's "
        "robots.txt is lifted; or a new supplier is awarded on this "
        "framework."
    ),
}


def main():
    d = json.load(open(PATH))
    frameworks = d["frameworks"]
    for i, f in enumerate(frameworks):
        if f.get("framework") == ENTRY["framework"]:
            frameworks[i] = ENTRY
            print("replaced existing entry")
            break
    else:
        frameworks.append(ENTRY)
        print("added new entry")
    json.dump(d, open(PATH, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
