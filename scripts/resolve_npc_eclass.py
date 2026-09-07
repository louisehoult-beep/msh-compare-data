#!/usr/bin/env python3
"""Resolve NHS Supply Chain NPC codes to their eClass, and build the (eClass ->
category) evidence the Supply Disruption Tracker needs to obey the
Differentiator's own comparison rule.

WHY THIS EXISTS — 07/09/2026
-----------------------------
`differentiator.json` states its own rule verbatim:

    "Comparison is locked to a single category: two products may be put side by
     side only where their `cat` is identical."

The Supply Disruption Tracker (page 3641) cannot obey it. It starts from an NHS
Supply Chain suspended line, and an NHSSC catalogue line carries no `cat`. So
`sdt_match.py` falls back to word-overlap matching across a ~38,000-record
universe, and word overlap on a universe that size returns whatever supplier has
the biggest indexed catalogue. Measured on the live page 07/09/2026: a small
nitrile examination glove was offered 243 "alternatives" including sterile latex
surgeons' gloves in size 9.5, and one supplier appeared as an alternative on 424
of 973 suspended lines (44%).

THE BRIDGE, AND WHY IT HAS TO BE BUILT THIS WAY
------------------------------------------------
Every suspended line DOES carry an `eClass` code — `sdt_fetch.py` already
captures it for 973 of 973 rows (155 distinct codes). So if eClass can be
mapped to `cat`, the Tracker gains a category and can gate on it.

Learning that mapping needs observations of eClass and `cat` on the SAME
product. Neither file has both:

  - `differentiator.json` has `cat`, and 1,249 of its products carry real NPCs.
  - `sdt-suspensions.json` has eClass, but no `cat`.
  - `nhssc-cache.json` has neither eClass nor `cat` — its builder scrapes
    rendered search cards, which do not expose eClass at all (confirmed
    07/09/2026 against the live pilot site; the field exists only on the
    product detail route and on the backend API).

The join is therefore NPC -> eClass, fetched once for the NPCs that already
carry a `cat`. That is what this script does. It is a BUILD-TIME job whose
output is committed to the repo — nothing here is ever called per page view.

POLITENESS
----------
It calls the same backend API `sdt_fetch.py` already uses, importing that
module's constants and request helper rather than re-implementing a client, so
there is exactly one place where the endpoint, headers and User-Agent are
defined. `query=<NPC>` is an exact-match lookup (`total: 1`). Order of magnitude
is ~1,400 requests at a pool of 6, not one per catalogue item — resolving the
whole 13,581-item catalogue was considered and rejected on those grounds.

Results are cached to `data/npc-eclass.json` and reused, so a rebuild costs
nothing unless new categorised NPCs have appeared. `--refresh` forces a re-fetch
of codes already cached.

EVIDENCE QUALITY IS CARRIED, NOT ASSUMED
-----------------------------------------
The NPC->product joins inside `differentiator.json` are not uniformly sound.
Measured 07/09/2026: of 2,979 joined NPC lines, 1,622 (54%) rest on a single
shared significant word between the product name and the NHSSC description, and
24 share none at all — a male external catheter joined to foam dressings on the
word "silicone"; transit wheelchairs joined to a sphygmomanometer. Every
observation this script emits therefore carries the token overlap that backed
its join, so the map builder can weight or exclude weak ones rather than
treating all evidence as equal. Root rule 14: an honest partial map beats a
complete guessed one.

USAGE
-----
    python3 scripts/resolve_npc_eclass.py --report     # show what would be fetched
    python3 scripts/resolve_npc_eclass.py              # fetch missing, write cache
    python3 scripts/resolve_npc_eclass.py --limit 50   # testing
"""
import argparse
import concurrent.futures
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PIPELINE = ("/Users/louisehoult/Library/CloudStorage/OneDrive-Personal/Cowork-OS/"
            "02-Elevate-and-Thrive/Hub/Medical-Sales-Hub/cloud-pipeline")

DIFFERENTIATOR = os.path.join(REPO, "data", "differentiator.json")
OUT = os.path.join(REPO, "data", "npc-eclass.json")

# Words that say nothing about what a product IS. Kept deliberately in step with
# sdt_match.py's own stop list — these are fabric/packaging/colour/size words
# that match across unrelated products and were the measured cause of real
# false positives there.
STOP = {
    "the", "and", "for", "with", "size", "pack", "box", "case", "cases", "boxes",
    "sterile", "single", "use", "non", "each", "black", "white", "green", "brown",
    "beige", "clear", "amber", "purple", "yellow", "orange", "large", "small",
    "extra", "adult", "paediatric", "pediatric", "child", "infant", "neonatal",
    "woven", "nonwoven", "viscose", "returnable", "packaged", "individually",
    "ltd", "limited", "medical", "healthcare", "group", "products", "product",
}
_WORD4 = re.compile(r"[a-z]{4,}")


def toks(s):
    return {w for w in _WORD4.findall(str(s or "").lower()) if w not in STOP}


def load_categorised_npcs():
    """Every NPC in differentiator.json that already carries a `cat`, with the
    token overlap that backed its join so weak evidence stays identifiable."""
    with open(DIFFERENTIATOR, encoding="utf-8") as f:
        doc = json.load(f)
    out = {}
    for p in doc.get("products", []):
        cat = p.get("cat")
        if not cat:
            continue
        ptoks = toks(p.get("name", ""))
        for line in (p.get("nhssc") or []):
            npc = line.get("npc")
            if not npc:
                continue
            ltoks = toks(line.get("desc", "")) | toks(line.get("nhsscName", ""))
            overlap = len(ptoks & ltoks) if (ptoks and ltoks) else 0
            prev = out.get(npc)
            # One NPC can be reached from more than one product. Keep the
            # best-evidenced observation rather than whichever came last.
            if prev is None or overlap > prev["overlap"]:
                out[npc] = {
                    "npc": npc,
                    "cat": cat,
                    "supplier": p.get("supplier", ""),
                    "product": p.get("name", ""),
                    "nhsscDesc": line.get("desc", ""),
                    "overlap": overlap,
                    "matchedOn": line.get("matchedOn") or "",
                }
    return out


def _resolve(npc):
    """One exact-match lookup, returning the attributes we need or None.

    Never raises: a miss means "drop this NPC", not "the run failed" — the same
    contract sdt_fetch.py's own resolver uses.
    """
    try:
        import sdt_fetch
        data = sdt_fetch._post({"limit": 3, "query": npc})
    except Exception:
        return None
    for it in data.get("items", []):
        v = it["variants"][0]["attributes"]
        if v.get("nationalProductCode") == npc:
            return {
                "eclass": v.get("eClass") or "",
                "itemclass": v.get("itemClass") or "",
                "speciality": v.get("catalogueSpeciality") or "",
                "supplier": v.get("supplier", ""),
                "desc": it.get("description") or it.get("name") or "",
            }
    return None


def load_cache():
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"_meta": {}, "npcs": {}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="show what would be fetched and the current evidence, write nothing")
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch NPCs already cached")
    ap.add_argument("--limit", type=int, help="only resolve first N (testing)")
    ap.add_argument("--pool", type=int, default=6)
    args = ap.parse_args()

    sys.path.insert(0, PIPELINE)

    cand = load_categorised_npcs()
    cache = load_cache()
    known = cache.get("npcs", {})

    todo = sorted(cand) if args.refresh else sorted(set(cand) - set(known))
    if args.limit:
        todo = todo[:args.limit]

    print("categorised NPCs in differentiator.json: %d" % len(cand))
    print("already cached:                          %d" % len(known))
    print("to resolve this run:                     %d" % len(todo))

    if args.report:
        strong = sum(1 for v in cand.values() if v["overlap"] >= 2)
        weak = sum(1 for v in cand.values() if v["overlap"] == 1)
        none_ = sum(1 for v in cand.values() if v["overlap"] == 0)
        print("\njoin evidence behind those NPCs:")
        print("  >=2 shared significant words: %d" % strong)
        print("   1 shared significant word:   %d  (thin — weight down)" % weak)
        print("   0 shared words:              %d  (unusable — exclude)" % none_)
        return

    if todo:
        done = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.pool) as ex:
            futs = {ex.submit(_resolve, n): n for n in todo}
            for fut in concurrent.futures.as_completed(futs):
                npc = futs[fut]
                rec = fut.result()
                done += 1
                if done % 200 == 0:
                    print("  resolved %d/%d" % (done, len(todo)))
                if rec and rec.get("eclass"):
                    known[npc] = rec

    # Emit the observations: one row per NPC where we have BOTH an eClass and a
    # cat, carrying the join strength so the map builder can judge it.
    obs = []
    for npc, meta in cand.items():
        rec = known.get(npc)
        if not rec or not rec.get("eclass"):
            continue
        obs.append({
            "npc": npc,
            "eclass": rec["eclass"],
            "itemclass": rec.get("itemclass", ""),
            "cat": meta["cat"],
            "overlap": meta["overlap"],
            "matchedOn": meta["matchedOn"],
            "product": meta["product"],
            "supplier": meta["supplier"],
            "nhsscDesc": rec.get("desc") or meta["nhsscDesc"],
        })
    obs.sort(key=lambda o: (o["eclass"], -o["overlap"]))

    cache = {
        "_meta": {
            "what": "NPC -> eClass lookups, and the (eClass, cat) observations they yield.",
            "why": "The bridge that lets an NHS Supply Chain line carry a Hub product "
                   "category, so the Supply Disruption Tracker can obey differentiator.json's "
                   "own rule that comparison is locked to a single category.",
            "generated": datetime.date.today().strftime("%d/%m/%Y"),
            "source": "pilot.supplychain.nhs.uk's backend search API, via cloud-pipeline/sdt_fetch.py",
            "rule": "An observation pairs an eClass (read from NHS Supply Chain) with a cat "
                    "(read from differentiator.json) for the SAME NPC. `overlap` is the number "
                    "of significant words shared between the Hub product name and the NHSSC "
                    "description that backed the original join: 0 means the join is unusable, "
                    "1 means it is thin. Weight accordingly — do not treat all observations "
                    "as equal evidence.",
            "npcsResolved": len(known),
            "observations": len(obs),
            "distinctEclass": len({o["eclass"] for o in obs}),
        },
        "npcs": known,
        "observations": obs,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)

    print("\nresolved NPCs cached:   %d" % len(known))
    print("(eClass, cat) observations: %d across %d distinct eClass codes"
          % (len(obs), len({o["eclass"] for o in obs})))
    print("written -> %s" % OUT)


if __name__ == "__main__":
    main()
