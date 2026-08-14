#!/usr/bin/env python3
"""Add framework-awarded suppliers to data/supplier-seed.json.

Closes the gap reconcile_suppliers.py measures: companies named on an NHS Supply
Chain framework by that framework's OWN contract launch brief, held in no Hub
supplier section. Tier 1 (3+ frameworks) is state/backfill-tier1-adjudication.json.

    python3 scripts/backfill_seed_from_frameworks.py            # dry run
    python3 scripts/backfill_seed_from_frameworks.py --write

WHAT EACH RECORD ASSERTS, AND WHAT IT DOES NOT
----------------------------------------------
Exactly one fact: this company is named on these frameworks by those frameworks'
own briefs. That is sourced, dated and quoted in every record.

Everything else is explicitly NOT asserted. No product range, no ownership, no
turnover, no website. Company numbers found by NAME SEARCH are written to
`companyNumberCandidate`, never to `companyNumber` — per docs/COMPANY-REPORT-METHOD.md
a number is only confirmed via route 1 (anchored, curated) or route 2 (published on
the company's own site). Writing a name-search number into the confirmed field is
how 380 of 598 records ended up carrying numbers nobody had checked.

Specialities are assigned ONLY where the framework is named in
speciality-map.json's canonicalSpecialities[].nhssc, and every one carries
_specialitiesEvidence saying it came from the framework alone with no
product-level evidence. A supplier whose frameworks map to nothing gets an empty
list — an honest empty state, not a guess.

`unresolved` and `foreign` companies still get a record. The framework award is
real whether or not a company number was found; the record says plainly that no
number could be established and why. Suppressing them would put the gap back.
"""
import json, os, re, sys, datetime

from brief_names import clean as clean_brief_name
from stamp_notice import detect_style

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
ADJ = os.path.join(ROOT, "state", "backfill-tier1-adjudication.json")
TODAY = datetime.date.today().isoformat()
UK_TODAY = datetime.date.today().strftime("%d/%m/%Y")


def load(p):
    with open(p) as fh:
        return json.load(fh)


def speciality_index(smap):
    """framework name (lowercased) -> canonical speciality label.

    Built from canonicalSpecialities[].nhssc, which names the frameworks each
    speciality covers. Matching is on the framework name appearing in that
    field, so it is checkable against speciality-map.json by eye."""
    idx = {}
    for spec in smap["canonicalSpecialities"]:
        blob = (spec.get("nhssc") or "")
        for part in re.split(r"[;—]", blob):
            part = part.strip().strip(".")
            part = re.sub(r"\s*\([^)]*\)\s*$", "", part).strip()
            if len(part) > 12:
                idx.setdefault(part.lower(), spec["label"])
    return idx


def specialities_for(fw_names, idx):
    out, why = [], []
    for f in fw_names:
        lf = f.lower()
        for key, label in idx.items():
            if key in lf or lf in key:
                if label not in out:
                    out.append(label)
                    why.append(f)
                break
    return out, why


def main(write=False):
    adj = load(ADJ)
    seed = load(os.path.join(DATA, "supplier-seed.json"))
    fw = load(os.path.join(DATA, "frameworks.json"))
    smap = load(os.path.join(DATA, "speciality-map.json"))
    idx = speciality_index(smap)

    held = {s["name"].lower() for s in seed["suppliers"]}
    held |= {a.lower() for s in seed["suppliers"] for a in (s.get("aliases") or [])}

    # framework name -> its own record, and the raw supplier strings on it
    fwrec = {f["name"]: f for f in fw["frameworks"]}

    aliases_for = {}
    for c in adj["companies"]:
        if c["verdict"] == "alias":
            aliases_for.setdefault(c["aliasOf"], []).append(c["name"])

    added, skipped = [], []
    for c in adj["companies"]:
        name = c["name"]
        if c["verdict"] == "alias":
            continue
        if name.lower() in held:
            skipped.append((name, "already in seed"))
            continue

        # every framework whose brief names this company, or one of its aliases
        names = {name} | set(aliases_for.get(name, []))
        mine = []
        for fname, f in fwrec.items():
            for raw in (f.get("suppliers") or []):
                if raw in names or clean_brief_name(raw) in names:
                    mine.append((fname, f, raw))
                    break
        if not mine:
            skipped.append((name, "no framework names it — check the worklist is current"))
            continue

        fw_names = [m[0] for m in mine]
        specs, spec_why = specialities_for(fw_names, idx)

        frameworks = []
        for fname, f, raw in sorted(mine):
            frameworks.append({
                "name": fname, "dates": f.get("dates"), "reference": f.get("reference"),
                "category": f.get("category"), "supplierCount": len(f.get("suppliers") or []),
                "url": f.get("url"),
                "note": (f'Named on NHS Supply Chain\'s own contract launch brief for this '
                         f'framework, as "{raw}". '
                         f'{len(f.get("suppliers") or [])} suppliers on the framework.'),
            })

        refs = ", ".join(sorted({f.get("reference") or "no reference"
                                 for _n, f, _r in mine}))
        note = (f"Added {UK_TODAY} from NHS Supply Chain's own contract launch briefs for "
                f"{len(mine)} framework{'s' if len(mine) != 1 else ''} ({refs}). "
                f"The framework award is the only verified fact in this record. Product "
                f"range, UK entity, ownership and website have NOT been verified and must "
                f"be checked at source before being used with a customer.")

        rec = {
            "name": name,
            "aliases": sorted({name, *aliases_for.get(name, []),
                               *(m[2] for m in mine)}),
            "specialities": specs,
            "products": [],
            "frameworks": frameworks,
            "alerts": [], "news": [], "links": [], "awards": [],
            "curated": True,
            "note": note,
            "verified": TODAY,
            "source": (f"NHS Supply Chain contract launch briefs ({refs}), "
                       f"fetched {UK_TODAY}"),
            "reconciledFrom": "reconcile_suppliers.py tier-1 backfill, 14/08/2026",
        }
        if specs:
            rec["_specialitiesEvidence"] = (
                "Speciality assigned solely because the company is named on NHS Supply "
                "Chain's " + "; ".join(spec_why) + " framework"
                + ("s" if len(spec_why) != 1 else "")
                + ". No product-level evidence yet.")

        if c["verdict"] in ("candidate", "probable"):
            rec["companyNumberCandidate"] = {
                "number": c["number"], "registeredName": c["registered"],
                "companyStatus": c["status"], "incorporated": c["incorporated"],
                "confidence": c["verdict"],
                "matchedOn": ("Companies House name search on " + TODAY
                              + " — NOT verified against a number published by the "
                                "company. Must be proved by confirm_company_numbers.py "
                                "before it may be written to companyNumber or feed any "
                                "derived claim."),
            }
            if c.get("why"):
                rec["companyNumberCandidate"]["caution"] = c["why"]
        else:
            rec["companyNumberNote"] = (
                ("No Companies House record is expected: " if c["verdict"] == "foreign"
                 else "No Companies House match could be established: ") + c["why"])

        added.append(rec)

    print(f"{len(added)} records to add, {len(skipped)} skipped")
    for n, why in skipped:
        print(f"   skip  {n}  ({why})")
    print()
    for r in added:
        cn = r.get("companyNumberCandidate")
        print(f"   {r['name'][:34]:36} {len(r['frameworks']):>2} fw  "
              f"{(cn['number'] + ' ' + cn['confidence']) if cn else 'no number'}"
              f"   specialities: {', '.join(r['specialities']) or '(none)'}")

    if write:
        path = os.path.join(DATA, "supplier-seed.json")
        original = open(path).read()
        seed["suppliers"].extend(added)
        seed["suppliers"].sort(key=lambda s: s["name"].lower())
        # supplier-seed.json is single-line with its own separators. Writing it
        # in this script's own style would reformat 1.8MB and bury the real
        # change, so the file's existing style is detected and reused — the same
        # reason scripts/stamp_notice.py does it.
        style = detect_style(original, json.loads(original)) or {"indent": 1,
                                                                 "ensure_ascii": False}
        with open(path, "w") as fh:
            json.dump(seed, fh, **style)
            if original.endswith("\n"):
                fh.write("\n")
        print(f"\nwrote supplier-seed.json — {len(seed['suppliers'])} suppliers")
        print("NOT PUSHED. Run verify.py, then the alias registry build, before any push.")


if __name__ == "__main__":
    main("--write" in sys.argv)
