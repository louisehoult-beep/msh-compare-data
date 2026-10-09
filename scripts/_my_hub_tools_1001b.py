#!/usr/bin/env python3
"""One-off, idempotent: My Hub tools launcher (Task 12b, 01/10/2026).

    python3 scripts/_my_hub_tools_1001b.py

Lou's decisions on 01/10/2026, written into hub/my-hub-catalogue.json only:
  * every Hub tool is listed individually in the tools launcher (eight new
    items, group "tools"; ids are permanent, never reuse or rename one).
    Several are views inside the Med Sales Tools page, so their URL carries
    the page's `#view-...` hash. The third party's name is in no label.
  * four items are speciality-specific: `specialities` lists catalogue
    speciality ids. Every other item has no key, which means general.
  * retired pages leave the catalogue: icb-diabetes-tech-tracker (page 1754,
    titled RETIRED) and frameworks. They also leave profileStarters and role
    pins. Members' saved pins to them are hidden by the page code, not deleted.
New items get `profiles` by re-running scripts/build_my_hub_profiles.py
afterwards. Run this twice and the second run changes nothing.
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(HERE, "hub", "my-hub-catalogue.json")

T = "/medical-sales-hub/med-sales-tools/"
NEW = [
    ("tool-supplier-search", "Supplier Search", T + "#view-compare", "scan-search"),
    ("tool-compare-product", "Compare Your Product", T + "#view-compare", "arrow-left-right"),
    ("tool-help-me-prepare", "Help Me Prepare", T + "#view-prep", "clipboard-list"),
    ("tool-stakeholder-mapper", "Stakeholder Mapper", T + "#view-mapper", "hub-spoke"),
    ("tool-value-case-calculator", "Value Case Calculator", T + "#view-value", "circle-pound"),
    ("tool-wound-savings-calculator", "Wound Care Savings Calculator", T + "#view-value", "bandage"),
    ("tool-carbon-calculator", "Sustainability (Carbon) Calculator", T + "#view-value", "cloud"),
    ("tool-sustainability-comparison", "Sustainability Comparison Tool", "/critecocare-tool-example/", "sprout"),
]
SPECIALITIES = {
    "tool-wound-savings-calculator": ["tissue-viability-and-wound-care"],
    "intelligence-feed": ["theatres-and-surgical"],
    "fall-prevention-medical-sales-market-insights": ["frailty-and-older-people"],
    "pharmaceutical-sales": ["pharmacy-and-medicines"],
}
RETIRED = ["icb-diabetes-tech-tracker", "frameworks"]


def main():
    with open(CAT, encoding="utf-8") as f:
        cat = json.load(f)
    items = [i for i in cat["items"] if i["id"] not in RETIRED]
    have = {i["id"]: i for i in items}
    for id_, label, url, icon in NEW:
        it = have.get(id_)
        if it is None:
            it = {"id": id_}
            items.append(it)
            have[id_] = it
        it.update({"label": label, "group": "tools", "url": url, "icon": icon})
    spec_ids = {i["id"] for i in items if i["group"] == "specialities"}
    for id_, sp in SPECIALITIES.items():
        if id_ not in have:
            raise SystemExit("not in the catalogue: " + id_)
        bad = [s for s in sp if s not in spec_ids]
        if bad:
            raise SystemExit("not speciality ids: " + ", ".join(bad))
        have[id_]["specialities"] = sp
    cat["items"] = items
    for r, ids in cat["profileStarters"].items():
        cat["profileStarters"][r] = [i for i in ids if i not in RETIRED]
    for r in cat["roles"].values():
        r["pins"] = [i for i in r["pins"] if i not in RETIRED]
    with open(CAT, "w", encoding="utf-8") as f:
        f.write(json.dumps(cat, indent=1, ensure_ascii=False))
    print("tools added: %d, speciality-tagged: %d, retired removed: %d" % (len(NEW), len(SPECIALITIES), len(RETIRED)))


if __name__ == "__main__":
    main()
