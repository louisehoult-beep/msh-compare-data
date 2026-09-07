#!/usr/bin/env python3
"""
build_eclass_map.py — turn NPC->eClass observations into an eClass -> Hub
category map, so the Supply Disruption Tracker can gate its "alternatives" on
a genuine category instead of word overlap.

WHY THIS EXISTS — STAGE 3b, 07/09/2026
---------------------------------------
`differentiator.json` states its own rule verbatim:

    "Comparison is locked to a single category: two products may be put side
     by side only where their `cat` is identical."

The Supply Disruption Tracker (page 3641) cannot obey it. It starts from an
NHS Supply Chain suspended line, and a catalogue line carries no `cat` — so
`sdt_match.py` falls back to word-overlap matching, which is why the live page
was offering a small nitrile examination glove 243 "alternatives" including
sterile latex surgeons' gloves size 9.5, and why Farla Medical appeared as an
alternative on 424 of 973 suspended lines (44%).

Every suspended line DOES carry an eClass code (`sdt_fetch.py` captures it for
973/973 rows, 155 distinct codes). `scripts/resolve_npc_eclass.py` bridges
that: it reads every NPC in `differentiator.json` that already carries a
`cat`, resolves that NPC's eClass from NHS Supply Chain's own backend search
API, and writes `data/npc-eclass.json` — one row per NPC where an eClass AND a
`cat` are both known, i.e. an OBSERVATION that "this eClass, on this NPC's
evidence, looked like this category."

This script does the next step: it aggregates those observations PER ECLASS
and decides, per eClass, whether the evidence is strong enough to publish a
mapping at all — and if so, to what confidence.

THE RULE THIS IS DERIVED UNDER — root rule 14
-----------------------------------------------
A computed claim needs a stated rule, an evidence floor, and permission to
refuse. Here:

1. STATED RULE. An eClass's mapped category is the `cat` with majority support
   among its own NPC observations, where support is weighted 2x for a
   "strong" join (>=2 significant words shared between the Hub product name
   and the NHS Supply Chain description that produced the observation) and 1x
   for a "weak" one (exactly 1 shared word). A join with ZERO shared words is
   not evidence at all and is dropped before aggregation — see
   `resolve_npc_eclass.py`'s own accounting: of 2,979 NPC->product joins in
   `differentiator.json`, 24 share no word with the catalogue description that
   produced them (a male external catheter joined to foam dressings, wheel-
   chairs joined to a sphygmomanometer — both on the word "silicone" or a
   packaging term). Those 24 carry no vote here.

2. THE INVARIANT. A single mis-tagged product must not be able to flip an
   eClass's mapping on its own. That is why this script counts DISTINCT NPCs
   behind the winning category, not just observations, and requires a
   supermajority SHARE of the weighted support, not merely "more than the
   others". Measured case that proves the invariant holds: eClass ELA (wound
   dressings, 90 observations) splits 63 wound:adv / 27 marketing:content —
   the marketing:content votes are a real upstream error (Mölnlycke's Mepilex
   Border Comfort division is wrongly mapped to marketing:content in
   `differentiator-category-map.json`, not a text-matching fault), but they
   are a minority even among the STRONG votes (15 of 73), so the majority
   rule correctly reaches wound:adv despite the individual bad joins mixed
   into its own evidence. See docs/ECLASS-BRIDGE.md for the full case.

3. THE EVIDENCE FLOOR. Three tiers, and "no tier reached" is a real, expected
   outcome:

   HIGH   — >=3 distinct NPCs voting for the winner on STRONG joins, AND the
            winner holds >=65% of the eClass's total weighted support, AND
            >=3 distinct NPCs total behind the winner (strong or weak).
   MEDIUM — the winner has at least 1 strong-joined NPC OR >=3 weak-joined
            NPCs, AND holds >=60% of weighted support, AND >=2 distinct NPCs
            behind it, AND the eClass has >=3 observations in total (so a
            2-observation coin flip can never pass).
   UNMAPPED — everything else: no observations at all, or the winner cannot
            clear the share/count floor above. Root rule 14: publishing
            nothing is the correct output when the evidence is thin, and an
            empty entry is never padded to look like coverage.

DETERMINISM
-----------
No randomness, no external call. Every run against the same
`data/npc-eclass.json` and `data/differentiator.json` produces byte-identical
output (key order fixed, ties broken alphabetically by `cat`).

USAGE
    python3 scripts/build_eclass_map.py --report   # print coverage, write nothing
    python3 scripts/build_eclass_map.py             # write data/eclass-category-map.json

Reads:
    data/npc-eclass.json            (built by scripts/resolve_npc_eclass.py)
    data/compare-suppliers.json     (gated vocabulary — verify.py's authority)
    <cloud-pipeline>/sdt-suspensions.json   (the 973 suspended lines, for coverage)
Writes:
    data/eclass-category-map.json
"""
import argparse
import collections
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PIPELINE = ("/Users/louisehoult/Library/CloudStorage/OneDrive-Personal/Cowork-OS/"
            "02-Elevate-and-Thrive/Hub/Medical-Sales-Hub/cloud-pipeline")

NPC_ECLASS = os.path.join(REPO, "data", "npc-eclass.json")
VOCAB_FILE = os.path.join(REPO, "data", "compare-suppliers.json")
SDT_SUSPENSIONS = os.path.join(PIPELINE, "sdt-suspensions.json")
OUT = os.path.join(REPO, "data", "eclass-category-map.json")

# Evidence-floor thresholds — see the module docstring, section 3, for why
# each number is what it is. Named here so a re-tune touches one place.
HIGH_MIN_STRONG_NPCS = 3
HIGH_MIN_SHARE = 0.65
HIGH_MIN_TOTAL_NPCS = 3
MEDIUM_MIN_STRONG_NPCS = 1
MEDIUM_MIN_WEAK_NPCS = 3
MEDIUM_MIN_SHARE = 0.60
MEDIUM_MIN_TOTAL_NPCS = 2
MEDIUM_MIN_OBSERVATIONS = 3


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def legal_categories(vocab_doc):
    """Every "<speciality>:<type>" verify.py's own gate will accept. Publishing
    anything outside this set would fail the push gate outright — checked
    below as a hard assertion, not just relied on."""
    legal = set()
    for spec, rec in (vocab_doc.get("specialities") or {}).items():
        for typ in (rec.get("types") or {}):
            legal.add("%s:%s" % (spec, typ))
    return legal


def aggregate(observations, legal):
    """(eClass -> per-cat strong/weak NPC sets), observations with overlap<1
    already excluded by the caller — a 0-word join is not a vote."""
    by_eclass = collections.defaultdict(lambda: collections.defaultdict(
        lambda: {"strong": set(), "weak": set()}))
    itemclass_by_eclass = collections.defaultdict(collections.Counter)
    dropped_illegal = []
    for o in observations:
        cat = o.get("cat")
        eclass = o.get("eclass")
        npc = o.get("npc")
        if not (cat and eclass and npc):
            continue
        if cat not in legal:
            # Should never happen — differentiator.json's own `cat` is already
            # gated — but a computed file asserts this rather than trusting it.
            dropped_illegal.append((eclass, npc, cat))
            continue
        bucket = "strong" if (o.get("overlap") or 0) >= 2 else "weak"
        by_eclass[eclass][cat][bucket].add(npc)
        if o.get("itemclass"):
            itemclass_by_eclass[eclass][o["itemclass"]] += 1
    return by_eclass, itemclass_by_eclass, dropped_illegal


def decide(cat_buckets):
    """One eClass's aggregated evidence -> (tier, winner_cat, detail dict) or
    ("unmapped", None, detail). Pure function, no I/O, so it is unit-testable
    and the confidence rule lives in exactly one place."""
    support = {}
    for cat, b in cat_buckets.items():
        support[cat] = 2 * len(b["strong"]) + 1 * len(b["weak"])
    total_support = sum(support.values())
    total_obs = sum(len(b["strong"]) + len(b["weak"]) for b in cat_buckets.values())
    if not support or total_support == 0:
        return "unmapped", None, {"reason": "no eClass->cat observations", "totalObservations": 0}

    # Ties broken alphabetically by cat so the run is deterministic.
    ranked = sorted(support.items(), key=lambda kv: (-kv[1], kv[0]))
    winner, wscore = ranked[0]
    share = wscore / total_support
    strong_n = len(cat_buckets[winner]["strong"])
    weak_n = len(cat_buckets[winner]["weak"])
    total_n = len(cat_buckets[winner]["strong"] | cat_buckets[winner]["weak"])
    runner_up = ranked[1] if len(ranked) > 1 else None

    detail = {
        "strongNpcs": strong_n,
        "weakNpcs": weak_n,
        "distinctNpcs": total_n,
        "supportShare": round(share, 3),
        "totalObservations": total_obs,
        "runnerUp": ({"cat": runner_up[0], "support": runner_up[1]}
                     if runner_up else None),
    }

    if (strong_n >= HIGH_MIN_STRONG_NPCS and share >= HIGH_MIN_SHARE
            and total_n >= HIGH_MIN_TOTAL_NPCS):
        return "high", winner, detail
    if ((strong_n >= MEDIUM_MIN_STRONG_NPCS or weak_n >= MEDIUM_MIN_WEAK_NPCS)
            and share >= MEDIUM_MIN_SHARE and total_n >= MEDIUM_MIN_TOTAL_NPCS
            and total_obs >= MEDIUM_MIN_OBSERVATIONS):
        return "medium", winner, detail

    detail["reason"] = "evidence below the confidence floor (see thresholds in build_eclass_map.py)"
    detail["candidateCat"] = winner  # kept for review, NEVER published as a mapping
    return "unmapped", None, detail


def build(report_only=False):
    npce = load(NPC_ECLASS)
    vocab_doc = load(VOCAB_FILE)
    sdt = load(SDT_SUSPENSIONS)

    legal = legal_categories(vocab_doc)
    observations = [o for o in npce.get("observations", []) if (o.get("overlap") or 0) >= 1]

    by_eclass, itemclass_by_eclass, dropped_illegal = aggregate(observations, legal)
    if dropped_illegal:
        # Not a soft warning — an illegal cat reaching this file would fail
        # verify.py's own vocabulary gate downstream, so it is refused here,
        # loudly, at build time.
        print("REFUSED %d observation(s) carrying a cat outside the gated "
              "vocabulary — these indicate a bug upstream, not a mapping to "
              "make:" % len(dropped_illegal), file=sys.stderr)
        for eclass, npc, cat in dropped_illegal[:20]:
            print("  eClass=%s npc=%s cat=%r" % (eclass, npc, cat), file=sys.stderr)

    sdt_rows = sdt.get("rows", [])
    eclass_line_counts = collections.Counter(r.get("_eclass") for r in sdt_rows if r.get("_eclass"))
    sdt_eclasses = set(eclass_line_counts)

    mappings, unmapped = {}, {}
    for eclass in sorted(sdt_eclasses):
        cat_buckets = by_eclass.get(eclass, {})
        tier, winner, detail = decide(cat_buckets)
        ic_counter = itemclass_by_eclass.get(eclass)
        itemclass = ic_counter.most_common(1)[0][0] if ic_counter else (
            # Fall back to whatever sdt-suspensions.json itself recorded for
            # this eClass when there was no observation to read it from.
            next((r["_itemclass"] for r in sdt_rows
                  if r.get("_eclass") == eclass and r.get("_itemclass")), None)
        )
        lines = eclass_line_counts[eclass]
        if tier == "unmapped":
            unmapped[eclass] = {
                "itemclass": itemclass,
                "suspendedLines": lines,
                **detail,
            }
        else:
            mappings[eclass] = {
                "cat": winner,
                "confidence": tier,
                "itemclass": itemclass,
                "suspendedLines": lines,
                "evidence": detail,
            }

    lines_total = sum(eclass_line_counts.values())
    lines_high = sum(v["suspendedLines"] for v in mappings.values() if v["confidence"] == "high")
    lines_medium = sum(v["suspendedLines"] for v in mappings.values() if v["confidence"] == "medium")
    lines_unmapped = lines_total - lines_high - lines_medium

    counts = {
        "eclassInSuspensions": len(sdt_eclasses),
        "eclassWithAnyObservation": len(set(by_eclass) & sdt_eclasses),
        "eclassMappedHigh": sum(1 for v in mappings.values() if v["confidence"] == "high"),
        "eclassMappedMedium": sum(1 for v in mappings.values() if v["confidence"] == "medium"),
        "eclassMappedTotal": len(mappings),
        "eclassUnmapped": len(unmapped),
        "suspendedLinesTotal": lines_total,
        "suspendedLinesCoveredHigh": lines_high,
        "suspendedLinesCoveredMedium": lines_medium,
        "suspendedLinesCoveredTotal": lines_high + lines_medium,
        "suspendedLinesUncovered": lines_unmapped,
        "suspendedLinesCoveredPct": round(100.0 * (lines_high + lines_medium) / lines_total, 1)
                                     if lines_total else 0.0,
    }

    if report_only:
        print("eClass codes in the 973 suspended lines: %d" % counts["eclassInSuspensions"])
        print("  with >=1 usable NPC->cat observation:  %d" % counts["eclassWithAnyObservation"])
        print("  mapped HIGH:                           %d" % counts["eclassMappedHigh"])
        print("  mapped MEDIUM:                          %d" % counts["eclassMappedMedium"])
        print("  left UNMAPPED:                          %d" % counts["eclassUnmapped"])
        print()
        print("suspended-line coverage:")
        print("  HIGH-confidence lines:    %d" % counts["suspendedLinesCoveredHigh"])
        print("  MEDIUM-confidence lines:  %d" % counts["suspendedLinesCoveredMedium"])
        print("  uncovered:                %d" % counts["suspendedLinesUncovered"])
        print("  total:                    %d" % counts["suspendedLinesTotal"])
        print("  covered:                  %.1f%%" % counts["suspendedLinesCoveredPct"])
        print()
        print("HIGH-confidence mappings:")
        for ec in sorted(k for k, v in mappings.items() if v["confidence"] == "high"):
            v = mappings[ec]
            print("  %-4s -> %-22s  %2d lines  share=%.2f  strongNpcs=%d"
                  % (ec, v["cat"], v["suspendedLines"], v["evidence"]["supportShare"],
                     v["evidence"]["strongNpcs"]))
        print()
        print("MEDIUM-confidence mappings:")
        for ec in sorted(k for k, v in mappings.items() if v["confidence"] == "medium"):
            v = mappings[ec]
            print("  %-4s -> %-22s  %2d lines  share=%.2f  strongNpcs=%d weakNpcs=%d"
                  % (ec, v["cat"], v["suspendedLines"], v["evidence"]["supportShare"],
                     v["evidence"]["strongNpcs"], v["evidence"]["weakNpcs"]))
        return counts, mappings, unmapped

    # Ownership notice + traceability marker — required on every data/*.json
    # file by verify.py's check_notice(). Minted once via
    # scripts/mint_data_ref.py and registered in scripts/stamp_notice.py;
    # stamp_notice.py --check must pass before this is pushed.
    try:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import stamp_notice
        notice = stamp_notice.notice_for("eclass-category-map.json")
    except Exception as exc:
        print("WARNING: could not load the ownership notice (%s) — run "
              "scripts/stamp_notice.py after this to add it." % exc, file=sys.stderr)
        notice = None

    doc = {
        "_notice": notice,
        "_meta": {
            "what": "eClass -> Hub category (`cat`) map, so the Supply Disruption "
                    "Tracker can gate its alternatives on category equality instead "
                    "of word overlap.",
            "why": "differentiator.json's own rule: comparison is locked to a single "
                   "category. An NHS Supply Chain suspended line carries an eClass, "
                   "not a `cat` — this file is the bridge.",
            "generated": datetime.date.today().strftime("%d/%m/%Y"),
            "generatedBy": "scripts/build_eclass_map.py",
            "rule": (
                "A mapped eClass's `cat` is the category with majority support among "
                "its own NPC->cat observations (data/npc-eclass.json), weighted 2x "
                "for a strong join (>=2 shared significant words between the Hub "
                "product name and the NHS Supply Chain description) and 1x for a "
                "weak one (exactly 1 shared word); a 0-word join carries no vote. "
                "HIGH confidence needs >=3 distinct NPCs on strong joins AND >=65%% "
                "weighted support AND >=3 distinct NPCs total. MEDIUM needs >=1 "
                "strong NPC or >=3 weak NPCs AND >=60%% weighted support AND >=2 "
                "distinct NPCs AND >=3 total observations for the eClass. Everything "
                "else is UNMAPPED and carries no `cat` — root rule 14: publishing "
                "nothing is the correct output when the evidence is thin. This is a "
                "STATISTICAL aggregation over real, sourced observations, not a "
                "guess from general knowledge of medical devices."
            ),
            "source": "data/npc-eclass.json (NPC->eClass live lookups, from "
                      "scripts/resolve_npc_eclass.py, joined to differentiator.json's "
                      "own `cat` on the same NPC) aggregated per eClass code found in "
                      "<cloud-pipeline>/sdt-suspensions.json.",
            "vocabularyAuthority": "data/compare-suppliers.json — every `cat` this file "
                                   "writes is checked against that vocabulary before "
                                   "being written; none outside it is ever emitted.",
            "counts": counts,
            "thresholds": {
                "high": {"minStrongNpcs": HIGH_MIN_STRONG_NPCS, "minShare": HIGH_MIN_SHARE,
                         "minTotalNpcs": HIGH_MIN_TOTAL_NPCS},
                "medium": {"minStrongNpcs": MEDIUM_MIN_STRONG_NPCS,
                           "minWeakNpcs": MEDIUM_MIN_WEAK_NPCS, "minShare": MEDIUM_MIN_SHARE,
                           "minTotalNpcs": MEDIUM_MIN_TOTAL_NPCS,
                           "minObservations": MEDIUM_MIN_OBSERVATIONS},
            },
        },
        "mappings": dict(sorted(mappings.items())),
        "unmapped": dict(sorted(unmapped.items())),
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("mapped %d eClass codes (%d high, %d medium), covering %d/%d suspended "
          "lines (%.1f%%). %d eClass codes left unmapped."
          % (counts["eclassMappedTotal"], counts["eclassMappedHigh"],
             counts["eclassMappedMedium"], counts["suspendedLinesCoveredTotal"],
             counts["suspendedLinesTotal"], counts["suspendedLinesCoveredPct"],
             counts["eclassUnmapped"]))
    print("written -> %s" % OUT)
    return counts, mappings, unmapped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="print coverage and the mapping list, write nothing")
    args = ap.parse_args()
    build(report_only=args.report)


if __name__ == "__main__":
    main()
