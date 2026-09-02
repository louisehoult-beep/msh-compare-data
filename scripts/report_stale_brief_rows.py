#!/usr/bin/env python3
"""Classify every `source: "nhssc-brief"` framework row the briefs no longer justify.

WHY THIS EXISTS
---------------
backfill_index_frameworks.py adds a framework row to a supplier when that
framework's own NHS Supply Chain contract launch brief names it, and re-adds the
whole sourced set on each run. It has one hole: `if not hits: continue`. A
supplier the current briefs match on NOTHING is skipped entirely, so the rows an
older capture wrote for it are never revisited. They survive the brief being
revised, indefinitely.

The obvious fix — purge the sourced rows of any supplier with no current hits —
is WRONG, and destructively so. Measured on the 01/09/2026 capture, 39 rows sit
in that state, and only 9 of them are actually unwarranted. The other 30 are
rows the briefs STILL justify; the matcher simply cannot reach them, because the
brief spells the supplier differently from the Hub record and no alias bridges
the two. Unisurge is the clearest case: the Hub holds it as "Unisurge", every
one of its 11 briefs names "Unisurge International Ltd", and co_key() reduces
those to different keys. Purging on "no current hits" would have deleted all 11
correct rows and left the record showing no frameworks at all.

So the two populations must be separated BEFORE anything is deleted:

  ALIAS-GAP    the current brief still names a company that looks like this
               supplier, under a spelling the record does not carry. The row is
               probably right and the ALIAS is what is missing. Never purge —
               resolving the identity is a human call (see OUTSTANDING ^o44,
               ^o143), because these records carry no company number to anchor
               against and "looks like" is not evidence.

  UNWARRANTED  the current brief is readable and names nothing resembling this
               supplier. The matcher that added the row no longer matches. This
               is the population the sweep was actually for.

  BRIEF-GONE   the brief URL has left frameworks.json altogether, so there is no
               longer any document to test the row against. NHS Supply Chain
               retires brief pages outright, so absence is not evidence the
               supplier was delisted — it is absence of evidence either way.
               Reported separately and never lumped in with UNWARRANTED.

This script only reports. It writes nothing. Deleting rows is a separate,
reviewed step, and must run on the UNWARRANTED list alone.

    python3 scripts/report_stale_brief_rows.py
    python3 scripts/report_stale_brief_rows.py --json
"""
import json
import re
import sys
import importlib.util

INDEX = "data/supplier-index.json"
SEED = "data/supplier-seed.json"
FW = "data/frameworks.json"

# Words that carry no distinguishing power when asking "does this brief name
# anything that looks like this supplier". Deliberately generous: a false
# ALIAS-GAP costs a human glance, a false UNWARRANTED costs a correct row.
STOP = {
    "ltd", "limited", "plc", "llp", "inc", "corp", "corporation", "co",
    "company", "holdings", "group", "uk", "gb", "international", "medical",
    "medica", "health", "healthcare", "care", "services", "service",
    "solutions", "systems", "technologies", "technology", "products", "the",
    "and", "of",
    # Category words. In this catalogue "surgical", "instrument" and the like
    # describe what a framework buys, not who the supplier is: leaving them in
    # made every surgical-instruments supplier a lookalike for every other.
    "surgical", "instrument", "instruments", "supply", "supplies", "equipment",
    "finance", "management", "manufacturing", "engineering", "devices",
    "device", "pharmaceutical", "pharmaceuticals", "laboratories", "labs",
    "sales", "trading", "distribution", "consumables", "hospital", "clinical",
}


def _load_matcher():
    """Reuse backfill_index_frameworks.py's OWN co_key/ambiguity logic.

    Re-implementing it here would mean two matchers drifting apart, and the
    whole point is to judge rows by the matcher that created them.
    """
    spec = importlib.util.spec_from_file_location(
        "bif", "scripts/backfill_index_frameworks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tokens(name):
    """Distinguishing words only. Single letters are dropped: "R B Medical"
    reduces to nothing useful, and matching on "b" made B. Braun a lookalike
    for it. Names that reduce to nothing are caught by squash() instead."""
    return {t for t in re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).split()
            if len(t) > 1 and t not in STOP}


def squash(name):
    """All punctuation and spacing removed, so "R B Medical" and "RB Medical
    Engineering Ltd" become comparable by containment. Catches the two shapes
    tokens() cannot: initialised names, and a brief that appends words to a
    name the Hub holds in short form ("Unisurge" / "Unisurge International")."""
    return re.sub(r"[^a-z0-9]+", "", str(name or "").lower())


def looks_like(brief_name, own_names):
    """Is this brief's supplier string plausibly the Hub's supplier?

    Deliberately generous. A false ALIAS-GAP costs a human one glance; a false
    UNWARRANTED costs a correct, sourced row. It is a lookalike test only and
    asserts no identity — that call is a human's."""
    bt, bs = tokens(brief_name), squash(brief_name)
    for n in own_names:
        if tokens(n) & bt:
            return True
        ns = squash(n)
        if len(ns) >= 5 and len(bs) >= 5 and (ns in bs or bs in ns):
            return True
    return False


def classify(path, m, fw):
    frameworks = fw.get("frameworks") or []
    by_url = {f["url"]: f for f in frameworks}

    by_key = {}
    for f in frameworks:
        for nm in (f.get("suppliers") or []):
            k = m.co_key(nm)
            if k:
                by_key.setdefault(k, []).append((f, nm))

    doc = m.load(path)
    ambiguous = m.ambiguous_keys_for(doc)
    out = []

    for s in (doc.get("suppliers") or []):
        sourced = [r for r in (s.get("frameworks") or [])
                   if isinstance(r, dict) and r.get("source") == "nhssc-brief"]
        if not sourced:
            continue

        names = [s.get("name")] + list(s.get("aliases") or [])
        keys = {m.co_key(n) for n in names}
        keys.discard("")
        own = {m.norm_name(n) for n in names if n}

        hit_urls = set()
        for k in keys:
            for f, matched in by_key.get(k, []):
                if k in ambiguous and m.norm_name(matched) not in own:
                    continue
                hit_urls.add(f["url"])

        for r in sourced:
            url = r.get("url")
            if url in hit_urls:
                continue                      # still warranted, nothing to say
            brief = by_url.get(url)
            if brief is None:
                out.append({"verdict": "BRIEF-GONE", "file": path,
                            "supplier": s.get("name"), "framework": r.get("name"),
                            "url": url, "candidates": []})
                continue
            # Does the brief still name anything that looks like this supplier?
            cands = [nm for nm in (brief.get("suppliers") or [])
                     if looks_like(nm, names)]
            out.append({
                "verdict": "ALIAS-GAP" if cands else "UNWARRANTED",
                "file": path, "supplier": s.get("name"),
                "framework": r.get("name"), "url": url,
                "candidates": sorted(cands),
            })
    return out


def main():
    m = _load_matcher()
    fw = m.load(FW)
    if not (fw.get("frameworks") or []):
        sys.exit("frameworks.json holds no frameworks — refusing to judge any row "
                 "against an empty capture.")

    rows = classify(INDEX, m, fw) + classify(SEED, m, fw)

    if "--json" in sys.argv:
        json.dump({"dataAsOf": fw.get("dataAsOf"), "rows": rows},
                  sys.stdout, indent=1, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    print("Sourced framework rows the %s capture no longer warrants\n"
          % fw.get("dataAsOf"))
    for verdict, blurb in (
            ("UNWARRANTED", "brief readable, names nothing like this supplier "
                            "— the sweep's actual target"),
            ("ALIAS-GAP", "brief still names a lookalike under another spelling "
                          "— DO NOT PURGE, needs an identity call"),
            ("BRIEF-GONE", "brief has left the capture — no document to test "
                           "against, so neither confirmed nor refuted")):
        group = [r for r in rows if r["verdict"] == verdict]
        print("%s  (%d row%s) — %s" % (verdict, len(group),
                                       "" if len(group) == 1 else "s", blurb))
        for r in sorted(group, key=lambda r: (r["supplier"], r["framework"])):
            where = "index" if r["file"] == INDEX else "seed "
            print("  %s  %-46s %s" % (where, r["supplier"], r["framework"][:44]))
            if r["candidates"]:
                print("        brief names: %s" % ", ".join(r["candidates"]))
        print()

    print("This script writes nothing. Purge the UNWARRANTED list only, and only "
          "after review.")


if __name__ == "__main__":
    main()
