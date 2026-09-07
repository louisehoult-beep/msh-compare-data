#!/usr/bin/env python3
"""Apply two queued changes to the category data. Written 07/09/2026 while the
shared checkout was locked by another session; safe to run once it is free.

    ./session-lock.sh claim "apply-eclass-proposals"
    python3 scripts/apply_eclass_proposals.py            # dry run, prints only
    python3 scripts/apply_eclass_proposals.py --write
    python3 scripts/stamp_notice.py
    python3 verify.py
    ./land.sh "Mepilex division fix + inferred eClass mappings" data/...

CHANGE 1 — THE MÖLNLYCKE "WOUND CARE" DIVISION
------------------------------------------------
`differentiator-category-map.json` maps (Mölnlycke, "Wound Care") to
`marketing:content`. That decision was taken on 25/08/2026 and its recorded
reason was correct at the time: the named items were brochure-download links in
Dutch and French, not products.

The division has since filled with real products. Measured 07/09/2026 from
`supplier-products.json`: **70 products in that division, of which 2 are
brochure links** ("Download Ons Wondassortimentsboekje", "Telechargez Le Livret
D Assortiment Soins Des Plaies") and **68 are real advanced wound dressings** —
Exufiber, Melgisorb Plus, Mepilex Ag, Mepilex Border Ag, Mepitel Ag, Granudacyn
and the rest.

The effect on members: 17 Mepilex products are published as `marketing:content`
while 11 others reach `wound:adv` through the separate (supplier, NHSSC term)
entry "Mepilex range". Several of the mis-filed ones carry real NHS Supply Chain
NPCs — Mepilex Ag has 6, Mepilex Border Ag has 4 — so these are unambiguously
catalogue dressings, and because the category gate now decides which products
may be offered as alternatives to one another, a dressing filed under a
marketing category can never be offered as an alternative to a dressing.

This flips the division to `wound:adv` and records why, preserving the original
reasoning rather than erasing it. The two brochure links follow the division and
will be filed as `wound:adv` — wrong, but two rows wrong in a direction nobody
acts on, against 68 real dressings currently invisible to the comparison. Fixing
those two properly needs an item-level exclusion, which this file has no
mechanism for; it is recorded as a known residue rather than pretended away.

CHANGE 2 — INFERRED eClass MAPPINGS
-------------------------------------
`eclass-category-map.json` currently holds only mappings OBSERVED from real
(eClass, cat) pairs on the same NPC: 38 codes, ~36% of suspended lines. The
remaining 117 codes had too little observational evidence to auto-map.

Agents read the actual NHS Supply Chain descriptions of the suspended lines
filed under each unmapped code and proposed categories. Those proposals are
INFERRED FROM PRODUCT DESCRIPTIONS, not observed from paired data, and this
script keeps them in a separate `inferred` block with `source: "inferred"` so
the two kinds of evidence are never silently mixed. Root rule 14: the rule a
claim was derived under has to travel with it.

Every proposal is validated against the gated vocabulary before it is written.
Anything outside it is refused here rather than failing the publish gate later.
An eClass already carrying an OBSERVED mapping is never overwritten by an
inferred one — observation beats inference, always.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRATCH = ("/private/tmp/claude-501/-Users-louisehoult-Library-CloudStorage-OneDrive-"
           "Personal-Cowork-OS/41bcfc81-4628-4cf9-ba03-bdbf00129897/scratchpad")

CATMAP = os.path.join(REPO, "data", "differentiator-category-map.json")
ECLASS = os.path.join(REPO, "data", "eclass-category-map.json")
PROPOSALS = [os.path.join(SCRATCH, "eclass-proposals-AF.json"),
             os.path.join(SCRATCH, "eclass-proposals-GZ.json")]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def legal_vocabulary(catmap):
    legal = set()
    for spec, types in (catmap.get("vocabulary") or {}).items():
        for t in (types or {}):
            legal.add("%s:%s" % (spec, t))
    return legal


def fix_molnlycke(catmap, write):
    hits = [e for e in catmap["entries"]
            if "lnlycke" in str(e.get("supplier", ""))
            and str(e.get("division", "")) == "Wound Care"
            and e.get("kind") != "nhssc-term"]
    if not hits:
        print("Mölnlycke Wound Care: entry not found — nothing changed. Check by hand.")
        return False
    e = hits[0]
    if e.get("hub") == "wound:adv":
        print("Mölnlycke Wound Care: already wound:adv, nothing to do.")
        return False
    print("Mölnlycke Wound Care: %s -> wound:adv" % e.get("hub"))
    if write:
        e["hub"] = "wound:adv"
        e["why"] = ("Advanced wound dressings. Corrected 07/09/2026: this division was "
                    "mapped to marketing:content on 25/08/2026 when its visible items were "
                    "brochure-download links. Re-measured 07/09/2026 it holds 70 products, "
                    "68 of them real dressings (Exufiber, Melgisorb Plus, Mepilex Ag, "
                    "Mepitel Ag, Granudacyn) and only 2 brochure links. 17 Mepilex products "
                    "were reaching members as marketing:content, several carrying real NHSSC "
                    "NPCs, which under the category gate made them unavailable as alternatives "
                    "to any dressing. The 2 brochure links follow the division and are a known "
                    "residue: this file maps per (supplier, division) and has no item-level "
                    "exclusion.")
        e["evidence"] = ("the supplier's own site filing, read by scripts/crawl_supplier_site.py; "
                         "re-counted 07/09/2026 against data/supplier-products.json")
        e["decidedIn"] = "Mölnlycke.json; corrected 07/09/2026"
    return True


def merge_proposals(eclass_doc, legal, write):
    observed = set(eclass_doc.get("mappings") or {})
    inferred = dict(eclass_doc.get("inferred") or {})
    added, refused, skipped = 0, [], 0
    for path in PROPOSALS:
        if not os.path.exists(path):
            print("  (no proposal file at %s)" % os.path.basename(path))
            continue
        doc = load(path)
        for code, rec in (doc.get("proposed") or {}).items():
            code = str(code).strip().upper()
            cat = rec.get("cat")
            if code in observed:
                skipped += 1          # observation always beats inference
                continue
            if cat not in legal:
                refused.append((code, cat))
                continue
            inferred[code] = {
                "cat": cat,
                "confidence": rec.get("confidence", "medium"),
                "source": "inferred",
                "basis": "NHS Supply Chain descriptions of the suspended lines under this code",
                "suspendedLines": rec.get("suspendedLines"),
                "examples": (rec.get("examples") or [])[:5],
                "reasoning": rec.get("reasoning", ""),
                "addedOn": "07/09/2026",
            }
            added += 1
    print("  inferred mappings added: %d" % added)
    print("  skipped (already observed): %d" % skipped)
    if refused:
        print("  REFUSED, category not in the gated vocabulary: %s"
              % ", ".join("%s->%s" % r for r in refused[:8]))
    if write:
        eclass_doc["inferred"] = dict(sorted(inferred.items()))
        meta = eclass_doc.setdefault("_meta", {})
        meta["inferredCount"] = len(inferred)
        meta["inferredRule"] = (
            "Entries under `inferred` were proposed by reading the NHS Supply Chain "
            "descriptions of the suspended lines filed under each eClass code, not "
            "observed from paired (eClass, cat) data as `mappings` were. They are kept "
            "separate so the two kinds of evidence are never mixed, and an observed "
            "mapping always wins. Every category was validated against the gated "
            "vocabulary before being written.")
        meta["inferredAddedOn"] = datetime.date.today().strftime("%d/%m/%Y")
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply; otherwise dry run")
    args = ap.parse_args()

    catmap = load(CATMAP)
    eclass_doc = load(ECLASS)
    legal = legal_vocabulary(catmap)
    print("gated vocabulary: %d codes\n" % len(legal))

    print("CHANGE 1 — Mölnlycke Wound Care division")
    changed1 = fix_molnlycke(catmap, args.write)
    print("\nCHANGE 2 — inferred eClass mappings")
    added = merge_proposals(eclass_doc, legal, args.write)

    if not args.write:
        print("\nDRY RUN — nothing written. Re-run with --write.")
        return 0

    if changed1:
        with open(CATMAP, "w", encoding="utf-8") as f:
            json.dump(catmap, f, ensure_ascii=False, indent=1)
        print("\nwritten -> %s" % CATMAP)
    if added:
        with open(ECLASS, "w", encoding="utf-8") as f:
            json.dump(eclass_doc, f, ensure_ascii=False, indent=1)
        print("written -> %s" % ECLASS)
    print("\nNow run: python3 scripts/stamp_notice.py && python3 verify.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
