#!/usr/bin/env python3
"""27/11/2026 (second batch): refresh the picker bookkeeping after Abena UK's
examination gloves published, and record that Rocialle's instrument range adds no
reusable Surgical Instruments line. Internal bookkeeping only. Run once."""
import json

P = "docs/framework-coverage-exhausted.json"
L = {f["framework"]: f for f in json.load(open("data/coverage-ledger.json"))["frameworks"]}
UPDATES = {
 "Examination Gloves": (["Abena UK Limited", "Medline Industries", "Reliance Medical"],
  "Abena UK Limited published (12 examination glove product pages read from abena.co.uk). Medline (cold therapy only) and Reliance Medical (no glove line in its capture) carry no glove range."),
 "Surgical Instruments": (["Rocialle Healthcare"],
  "Rocialle Healthcare (captured 16/11 from rocialleacutecare.com): its own About page describes its surgical instruments as single use, so under Lou's 31/08/2026 ruling they belong in theatres:sui, not surgical:* (reusable only). No route on this framework. Open for a theatres framework batch: map those instrument divisions to theatres:sui."),
}
doc = json.load(open(P))
by = {f["framework"]: f for f in doc["frameworks"]}
for name, (suppliers, why) in UPDATES.items():
    e, f = by[name], L[name]
    for s in suppliers:
        if s not in e["suppliersChecked"]:
            e["suppliersChecked"].append(s)
    e["checkedOn"] = "2026-11-27"
    e["coverageAtCheck"] = "%s%% (%s/%s)" % (f["coverage"], f["suppliersPublished"], f["suppliersAwarded"])
    e["reason"] = "RE-CHECK 27/11/2026: %s PREVIOUS ENTRY FINDINGS STAND: %s" % (why, e.get("reason", ""))
with open(P, "w") as fh:
    json.dump(doc, fh, ensure_ascii=False, indent=1)
    fh.write("\n")
print("updated %d entries" % len(UPDATES))
