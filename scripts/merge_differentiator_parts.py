#!/usr/bin/env python3
"""
merge_differentiator_parts.py — fold each agent's decisions into the category map.

WHY PARTS EXIST. The mapping work parallelises well: 1,783 decisions, each one
independent of the others. Writing them parallelises badly. Every agent editing
data/differentiator-category-map.json at once produces the same collision that
cost this repo a 28-minute run on 12/08 and a Frankenstein data file on 14/08.

So no agent touches the map. Each writes ONE FILE PER SUPPLIER:

    data/differentiator-map-parts/<supplier-slug>.json
    {"supplier": "Guldmann",
     "decisions": [
       {"division": "Slings", "hub": "handling:sling",
        "why": "the division holds sling products only; checked against the four
                example products on the record"}
     ]}

Disjoint by construction — two agents working different suppliers cannot write
the same file — so the merge is a fold, never a three-way diff.

This script refuses rather than guesses:
  * a `hub` outside the gated vocabulary
  * two parts disagreeing about the same (supplier, division)
  * a decision with no `why` — a mapping is a judgement and has to carry its reason
  * a supplier or division that is not in the worklist (a typo silently maps nothing)

Usage:  python3 scripts/merge_differentiator_parts.py [--apply]
Without --apply it reports and changes nothing.
"""
import json, os, sys, glob, collections

MAP = "data/differentiator-category-map.json"
PARTS = "data/differentiator-map-parts"


def main():
    apply_it = "--apply" in sys.argv
    doc = json.load(open(MAP))
    vocab = json.load(open("data/compare-suppliers.json"))["specialities"]
    legal = {"%s:%s" % (s, t) for s, v in vocab.items() for t in (v.get("types") or {})}
    known = {(e["supplier"], e["division"]) for e in doc["entries"]}

    seen, problems = {}, []
    for path in sorted(glob.glob(os.path.join(PARTS, "*.json"))):
        try:
            part = json.load(open(path))
        except Exception as exc:
            problems.append("%s is not readable JSON: %s" % (path, exc))
            continue
        co = part.get("supplier")
        for d in part.get("decisions") or []:
            div, hub, why = d.get("division"), d.get("hub"), (d.get("why") or "").strip()
            key = (co, div)
            if key not in known:
                problems.append("%s: (%s, %s) is not a pair in the worklist — check the "
                                "exact spelling, a typo maps nothing" % (path, co, div))
                continue
            if hub not in legal:
                problems.append("%s: (%s, %s) -> '%s' is not in the gated vocabulary"
                                % (path, co, div, hub))
                continue
            if len(why) < 15:
                problems.append("%s: (%s, %s) carries no reason. A mapping is a judgement "
                                "and publishes with its reason." % (path, co, div))
                continue
            if key in seen and seen[key][0] != hub:
                problems.append("%s: (%s, %s) -> '%s' contradicts '%s' decided in another "
                                "part. Two agents disagree — this needs a human."
                                % (path, co, div, hub, seen[key][0]))
                continue
            seen[key] = (hub, why, os.path.basename(path))

    for p in problems:
        print("REFUSED  " + p)

    applied = 0
    for e in doc["entries"]:
        got = seen.get((e["supplier"], e["division"]))
        if got and not e.get("hub"):
            e["hub"], e["why"], e["decidedIn"] = got[0], got[1], got[2]
            applied += 1

    products = sum(e["products"] for e in doc["entries"] if e.get("hub"))
    doc["counts"]["mapped"] = sum(1 for e in doc["entries"] if e.get("hub"))
    doc["counts"]["productsMapped"] = products

    print("\n%d decision(s) read, %d applied, %d refused."
          % (len(seen), applied, len(problems)))
    print("map now: %d of %d pairs mapped, covering %d products."
          % (doc["counts"]["mapped"], len(doc["entries"]), products))
    if apply_it and not problems:
        json.dump(doc, open(MAP, "w"), ensure_ascii=False, indent=1)
        print("written to %s — now run build_differentiator.py and verify.py" % MAP)
    elif apply_it:
        print("NOT written: fix the refusals above first. A partial merge is how two "
              "generations of a file end up in one file.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
