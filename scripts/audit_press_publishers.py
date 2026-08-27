#!/usr/bin/env python3
"""audit_press_publishers.py — which publishers is the corroboration rule turning away?

WHY THIS EXISTS
---------------
SUPPLIER PRESS on the Live Desk (page 675) was thin on 27/08/2026: six rows, of
which only two fell in the previous six weeks. The data was correct — the panel
was showing everything that cleared the bar. The question was whether the bar
was catching real trade coverage that simply is not named in
refresh_company_press.REPUTABLE.

That question cannot be answered by guessing at publisher names. This script
answers it from what Google News actually returned: it runs the SAME code path
as the sweep (press_match.assess, cluster, the rule-5 corroboration test), keeps
every publisher it saw, and tallies them by what the rule did with them.

IT IS READ-ONLY AND IT CHANGES NOTHING. It never writes data/company-press.json,
never writes the rotation state, and never resolves links (resolution is the
slow half of a sweep and an audit does not need publisher URLs). Nothing it
prints reaches the Hub. The output is evidence for a HUMAN decision about
REPUTABLE — widening that list is a judgement about which titles are real trade
press, and this script deliberately does not make it.

WHAT THE THREE BUCKETS MEAN
---------------------------
  counted     reputable() said yes — a named outlet or a name that signals a
              clinical/medical-device title. These already count towards the two.
  prwire      on the PRWIRE denylist — a wire, a stock-tip site or SEO
              syndication. These are excluded on purpose and are NOT candidates.
  uncounted   neither. A publisher here is either a real trade title the list
              does not name yet, or something that should stay out. Deciding
              which is the point of reading the report.

The "blocked stories" tally is the one that matters most: a story dropped on
rule 5 with exactly one counted publisher is a story that one more named outlet
would have published. Those are ranked by how often each uncounted publisher
appears in them.

Usage
    python3 scripts/audit_press_publishers.py --limit 80
    python3 scripts/audit_press_publishers.py --only "Bayer,Boston Scientific"
    python3 scripts/audit_press_publishers.py --limit 40 --json out.json
"""
import argparse
import collections
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import press_match                                     # noqa: E402
import refresh_company_press as rcp                    # noqa: E402

log = lambda m: print("[press-audit]", m)


def bucket(pub):
    p = (pub or "").lower()
    if not p:
        return "uncounted"
    if any(x in p for x in rcp.PRWIRE):
        return "prwire"
    return "counted" if rcp.reputable(pub) else "uncounted"


def audit(suppliers, universe, pause):
    seen = collections.Counter()          # publisher -> times seen at all
    buckets = {}                          # publisher -> bucket
    blocked = collections.Counter()       # uncounted publisher -> rule-5 stories it appeared in
    near_miss = []                        # stories one counted publisher short
    checked = throttled = 0

    for s in suppliers:
        name = s["name"]
        raw = rcp.query_google_news(name)
        time.sleep(pause)
        if raw is None:
            throttled += 1
            log("  %-42s fetch failed (throttled)" % name[:42])
            continue
        checked += 1

        identified = []
        for it in raw:
            pub = it.get("publisher", "")
            seen[pub] += 1
            buckets[pub] = bucket(pub)
            press_match.assess(s, it, publisher=pub, universe=universe)
            if press_match.identify(s, it, universe):
                identified.append(it)

        name_toks = set()
        for form in [s.get("name", "")] + list(s.get("aliases") or []):
            name_toks |= set(t for t in press_match.norm(form).split() if len(t) > 3)

        blocked_here = 0
        for c in rcp.cluster(identified, name_toks=name_toks):
            pubs = {i.get("publisher", "") for i in c["items"]}
            counted = {p for p in pubs if bucket(p) == "counted"}
            if len(counted) >= 2:
                continue                                   # this story already publishes
            others = sorted(p for p in pubs if bucket(p) == "uncounted")
            for p in others:
                blocked[p] += 1
            blocked_here += 1
            best = sorted(c["items"], key=lambda x: x.get("date", ""), reverse=True)[0]
            near_miss.append({
                "supplier": name,
                "date": best.get("date", ""),
                "headline": best["headline"],
                "counted": sorted(counted),
                "uncounted": others,
                "shortBy": 2 - len(counted),
            })
        log("  %-42s %3d raw, %d story(ies) short of rule 5" % (name[:42], len(raw), blocked_here))

    return {"seen": seen, "buckets": buckets, "blocked": blocked,
            "nearMiss": near_miss, "checked": checked, "throttled": throttled}


def report(res, top):
    seen, buckets, blocked = res["seen"], res["buckets"], res["blocked"]
    tally = collections.Counter(buckets[p] for p in seen)
    print("\n" + "=" * 78)
    print("PUBLISHERS SEEN: %d distinct across %d supplier(s) checked (%d throttled)"
          % (len(seen), res["checked"], res["throttled"]))
    print("  counted %d   uncounted %d   prwire %d"
          % (tally["counted"], tally["uncounted"], tally["prwire"]))

    print("\nUNCOUNTED PUBLISHERS BLOCKING THE MOST STORIES")
    print("(each appeared in a story that fell short of two counted publishers)")
    if not blocked:
        print("  none — no story in this sample was short of corroboration")
    for pub, n in blocked.most_common(top):
        print("  %4d story(ies)  %4d seen   %s" % (n, seen[pub], pub))

    print("\nUNCOUNTED PUBLISHERS BY RAW FREQUENCY (context, not evidence on its own)")
    for pub, n in sorted(((p, c) for p, c in seen.items() if buckets[p] == "uncounted"),
                         key=lambda x: -x[1])[:top]:
        print("  %4d seen  %s" % (n, pub))

    one_short = [m for m in res["nearMiss"] if m["shortBy"] == 1 and m["uncounted"]]
    one_short.sort(key=lambda m: m["date"], reverse=True)
    print("\nSTORIES ONE COUNTED PUBLISHER SHORT (newest first, %d of %d)"
          % (min(len(one_short), top), len(one_short)))
    for m in one_short[:top]:
        print("  %s  %s" % (m["date"] or "no date", m["supplier"]))
        print("      %s" % m["headline"][:96])
        print("      counted: %s" % (", ".join(m["counted"]) or "none"))
        print("      uncounted: %s" % ", ".join(m["uncounted"][:6]))
    print("=" * 78)
    print("Nothing was written. Widening refresh_company_press.REPUTABLE is a human")
    print("decision — read the titles above and add only real trade or clinical press.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=60, help="suppliers to query (default 60)")
    ap.add_argument("--only", default="", help="comma-separated supplier names instead")
    ap.add_argument("--pause", type=float, default=rcp.QUERY_PAUSE,
                    help="seconds between Google News queries (default matches the sweep)")
    ap.add_argument("--top", type=int, default=25, help="rows per report section")
    ap.add_argument("--json", default="", help="also write the raw tallies here")
    args = ap.parse_args()

    seed = rcp.load_json(rcp.SEED, {"suppliers": []})
    suppliers = [s for s in (seed.get("suppliers") or []) if s.get("name")]
    if not suppliers:
        sys.exit("data/supplier-seed.json holds no suppliers")
    universe = press_match.alias_universe(seed)

    if args.only:
        by = {s["name"]: s for s in suppliers}
        wanted = [n.strip() for n in args.only.split(",") if n.strip()]
        missing = [n for n in wanted if n not in by]
        if missing:
            log("NOT IN THE SEED, skipped: %s" % ", ".join(missing))
        batch = [by[n] for n in wanted if n in by]
    else:
        # The noted tier is what SUPPLIER PRESS actually draws on, so audit that
        # first; oldest-checked first, the same order the sweep would take.
        noted, other = rcp.tiers(suppliers)
        state = rcp.load_json(rcp.STATE, {}) or {}
        stamps = state.get("lastPressCheck") or {}
        batch = rcp.due(noted, stamps, args.limit)

    log("auditing %d supplier(s) — read-only, nothing will be written" % len(batch))
    res = audit(batch, universe, args.pause)
    report(res, args.top)

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps({
            "checked": res["checked"], "throttled": res["throttled"],
            "seen": dict(res["seen"]), "buckets": res["buckets"],
            "blocked": dict(res["blocked"]), "nearMiss": res["nearMiss"],
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        log("wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
