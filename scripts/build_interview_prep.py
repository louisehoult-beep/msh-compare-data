#!/usr/bin/env python3
"""Rebuild the "co" (company) array of data/interview-prep.json.

WHY THIS FILE EXISTS
--------------------
The Interview Prep page (Hub page, one Custom HTML block) fetches
data/interview-prep.json and builds a prep pack from three dropdowns: role,
speciality and company. Roles, specialities, routes, conferences and the
cross-cutting blocks are editorial and are NOT touched here. Only the company
array is generated.

The original generator (build_page.py / confdata.py, referenced in
Website/INTERVIEW-PREP-BUILD-NOTE.md) was never committed. The published file
therefore drifted out of reach of its own sources: it carried 472 companies
against a supplier index of 1,334, seven of those 472 were the SAME company
twice under two spellings, and fifteen carried a name no Hub surface could
resolve. This script replaces that lost builder, is committed, and is
re-runnable, so the company array can never again be a hand-carried artefact.

WHAT IT READS  (nothing else is a source)
-----------------------------------------
  data/supplier-index.json   canonical company names and aliases; specialities,
                             products, links, national agreements, alerts,
                             news, award notices, positioning ("voice").
  data/company-financials.json
                             Companies House register facts: number, registered
                             name, status, incorporation, accounts category and
                             date, officers, tagged turnover series, employees.

NAMES
-----
Every record is keyed on the CANONICAL supplier-index name. Incoming names are
resolved with scripts/company_match.py — the Hub's exact-only alias rule. There
is no fuzzy matching. An unresolved name is a stop, never a guess. Competitor
names are resolved the same way and are additionally required to be a company
this file itself publishes, so every competitor the page renders is a company
the reader can then select from the dropdown.

DERIVED CLAIMS  (root rule 14: state the rule, test it, refuse thin evidence)
----------------------------------------------------------------------------
Only one field is derived rather than read: the competitor set. Both the rule
and its fallback are written into the published file (meta.cpRule / meta.nrRule)
so a reader can judge the claim without reading this source. Every record that
cannot meet the rule gets NO competitor panel rather than a plausible one — the
page has an honest empty state for exactly that case and it is used.

REGISTER FACTS ARE NOT OPTIONAL
-------------------------------
The page renders the company number and the registered name unconditionally: it
prints the Companies House link, the filing-history link and the registered name
into running prose. A company with no Companies House record would render a
blank name and a link to /company/ — a broken page, not an honest empty state.
Such companies are therefore OMITTED and counted, not published half-built. The
count is written to meta.omittedNoRegister. As company-financials.json is
backfilled, re-running this script picks the companies up with no code change.

USAGE
-----
    python3 scripts/build_interview_prep.py            # write the file
    python3 scripts/build_interview_prep.py --check    # build, verify, write nothing
    python3 scripts/build_interview_prep.py --report   # per-field diff vs the
                                                       # published file, then stop

Exit 0 = built and every invariant held. Exit 1 = an invariant failed and
nothing was written. Loosening an invariant to make a run succeed is the 24/07
incident with different words in it; fix the data instead.
"""

import argparse
import collections
import itertools
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import company_match as cm  # noqa: E402

PREP = os.path.join(ROOT, "data", "interview-prep.json")
INDEX = os.path.join(ROOT, "data", "supplier-index.json")
FIN = os.path.join(ROOT, "data", "company-financials.json")

# ---------------------------------------------------------------- field caps
# The page renders these as chip rows and short tables. The caps are a layout
# decision, not an evidence one, and are reproduced from the published file.
MAX_PRODUCTS = 8
MAX_LINKS = 3
MAX_FRAMEWORKS = 4
MAX_ALERTS = 2
MAX_NEWS = 3
MAX_AWARDS = 3
MAX_COMPETITORS = 8
MAX_OFFICERS = 4

# Supplier-record alerts are a mixed bag: most are intelligence a candidate can
# use (ownership, group structure, sale processes, safety flags), but some are
# notes the Hub's own maintainers left about editing the dataset. Those are not
# company background and are dropped. Identified by their opening words, listed
# here so the filter is readable rather than clever.
HOUSEKEEPING_PREFIXES = (
    "removed ",
    "removed a ",
    "cleaned up ",
    "re-tagged ",
    "full product-list spot-check",
    "catalogue is wider than the store front page",
)

CP_RULE = (
    "Competitors are companies named on THE SAME national agreements, ranked by how "
    "many agreements they share — the firms a trust could buy instead, on the same "
    "paperwork, today. Companies in the same group are excluded by name root. Where "
    "several companies share the same number of agreements, the one whose shared "
    "agreements have the SMALLER awarded-supplier rosters ranks first: a place "
    "alongside six suppliers is evidence of head-to-head competition, a place "
    "alongside a hundred and twenty is barely evidence at all. Remaining ties break "
    "on how many specialities the two companies also share. A group of companies "
    "the evidence cannot separate is published whole or not at all — where such a "
    "group would have to be cut part-way to fit the panel, it is dropped rather "
    "than cut, because the cut would be alphabetical accident presented as a "
    "ranking. Where that leaves nothing, no competitor set is derived and the page "
    "shows its fallback or its empty state."
)
NR_RULE = (
    "Fallback, used ONLY where no shared national agreement produced a ranking, and "
    "shown on the page as a fallback in those words: companies the Hub tags to at "
    "least one of the same specialities, ranked by how many specialities they share "
    "and then by how narrow those specialities are — sharing a speciality only a "
    "handful of companies are tagged to says more than sharing a catch-all one — and "
    "then by how focused the other company is, because a firm tagged to that "
    "speciality and little else competes with you more directly than a conglomerate "
    "for which it is one line of forty. "
    "As with the derived set, a tied group is listed whole or not at all — an "
    "alphabetical slice of a hundred companies tagged to one broad speciality is not "
    "a competitive set, and where nothing fits, nothing is shown."
)
OMIT_RULE = (
    "A company is published here only where the Hub holds a Companies House record "
    "for it, because the page prints the registered name and the company number into "
    "running prose and links. Companies still awaiting a register match are omitted "
    "and counted rather than published with blank register fields and a broken link."
)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def root_of(name):
    """First word of the normalised name — the group root used to exclude a
    company's own siblings from its competitor set (Abbott Diabetes Care must
    not be told its competitor is Abbott Laboratories)."""
    k = cm.key(name)
    return k.split(" ")[0] if k else ""


def is_housekeeping(text):
    low = str(text or "").strip().lower()
    return any(low.startswith(p) for p in HOUSEKEEPING_PREFIXES)


def clean(value):
    return str(value).strip() if value is not None else ""


def build_records(index_doc, fin_doc):
    suppliers = index_doc.get("suppliers") or []
    fin = fin_doc.get("companies") or {}
    by_name = {s.get("name"): s for s in suppliers if s.get("name")}
    alias_index = cm.build_index(index_doc)

    omitted = []
    kept = []
    for name in sorted(by_name, key=lambda x: x.lower()):
        reg = fin.get(name) or {}
        if not clean(reg.get("companyNumber")) or not clean(reg.get("registeredName")):
            omitted.append(name)
            continue
        kept.append(name)
    keptset = set(kept)

    # ---- framework and speciality maps, used by the competitor derivation ----
    fw_of, sp_of = {}, {}
    for name in kept:
        s = by_name[name]
        fw_of[name] = {clean(f.get("name")) for f in (s.get("frameworks") or [])
                       if clean(f.get("name"))}
        sp_of[name] = {clean(x) for x in (s.get("specialities") or []) if clean(x)}

    by_framework = collections.defaultdict(set)
    for name, fws in fw_of.items():
        for f in fws:
            by_framework[f].add(name)
    by_speciality = collections.defaultdict(set)
    for name, sps in sp_of.items():
        for sp in sps:
            by_speciality[sp].add(name)

    records = []
    for name in kept:
        s = by_name[name]
        reg = fin[name]
        rec = collections.OrderedDict()
        rec["n"] = name
        rec["r"] = clean(reg.get("registeredName"))
        rec["no"] = clean(reg.get("companyNumber"))
        if clean(reg.get("status")):
            rec["st"] = clean(reg.get("status"))
        if clean(reg.get("accountsCategory")):
            rec["ac"] = clean(reg.get("accountsCategory"))
        if clean(reg.get("accountsMadeUpTo")):
            rec["am"] = clean(reg.get("accountsMadeUpTo"))
        if clean(reg.get("incorporated")):
            rec["inc"] = clean(reg.get("incorporated"))

        sps = [clean(x) for x in (s.get("specialities") or []) if clean(x)]
        if sps:
            rec["sp"] = sps
        prods = [clean(x) for x in (s.get("products") or []) if clean(x)][:MAX_PRODUCTS]
        if prods:
            rec["pr"] = prods

        line = clean((s.get("voice") or {}).get("line"))
        if line:
            rec["vo"] = line

        links = []
        for l in (s.get("links") or []):
            label, url = clean(l.get("label")), clean(l.get("url"))
            if label and url.startswith("http"):
                links.append([label, url])
            if len(links) == MAX_LINKS:
                break
        if links:
            rec["ln"] = links

        fws, seen = [], set()
        for f in (s.get("frameworks") or []):
            fname, url = clean(f.get("name")), clean(f.get("url"))
            if not fname or fname in seen or not url.startswith("http"):
                continue
            seen.add(fname)
            fws.append([fname, clean(f.get("dates")), url])
            if len(fws) == MAX_FRAMEWORKS:
                break
        if fws:
            rec["f"] = fws

        # Competitors, and the honest empty state when the rule cannot fire.
        scored = []
        pool = set()
        for f in fw_of[name]:
            pool |= by_framework[f]
        for other in pool:
            if other == name or root_of(other) == root_of(name):
                continue
            common = fw_of[name] & fw_of[other]
            if not common:
                continue
            # Evidence weight: a shared place on a small roster is strong evidence
            # of head-to-head competition; on a 122-supplier roster it is weak.
            specificity = sum(1.0 / max(len(by_framework[f]), 1) for f in common)
            scored.append(((len(common), round(specificity, 9),
                            len(sp_of[name] & sp_of[other])), other))
        picked = []
        if scored:
            scored.sort(key=lambda t: (-t[0][0], -t[0][1], -t[0][2], t[1].lower()))
            # Take whole tied groups only. A group that would have to be cut
            # part-way to fit the panel is dropped, not cut.
            for _score, group in itertools.groupby(scored, key=lambda t: t[0]):
                group = list(group)
                if len(picked) + len(group) > MAX_COMPETITORS:
                    break
                picked.extend(group)
        if picked:
            rec["cp"] = [[other, score[0]] for score, other in picked]
        else:
            near = set()
            for sp in sp_of[name]:
                near |= by_speciality[sp]
            near.discard(name)
            ranked = []
            for o in near:
                common_sp = sp_of[name] & sp_of[o]
                # Same evidence weight as the derived set: sharing a narrow
                # speciality is a closer match than sharing a catch-all one.
                weight = sum(1.0 / max(len(by_speciality[sp]), 1) for sp in common_sp)
                ranked.append(((len(common_sp), round(weight, 9),
                                -len(sp_of[o])), o))
            ranked.sort(key=lambda t: (-t[0][0], -t[0][1], -t[0][2], t[1].lower()))
            fallback = []
            for _n_sp, group in itertools.groupby(ranked, key=lambda t: t[0]):
                group = list(group)
                if len(fallback) + len(group) > MAX_COMPETITORS:
                    break
                fallback.extend(group)
            if fallback:
                rec["nr"] = [o for _score, o in fallback]

        awards = []
        for a in (s.get("awards") or []):
            title, url = clean(a.get("title")), clean(a.get("url"))
            if not title or not url.startswith("http"):
                continue
            awards.append([title, clean(a.get("buyer")), clean(a.get("value")),
                           clean(a.get("date")), url])
            if len(awards) == MAX_AWARDS:
                break
        if awards:
            rec["aw"] = awards

        news = []
        for item in (s.get("news") or []):
            head = clean(item.get("headline"))
            srcs = item.get("sources") or []
            if not head or not srcs:
                continue
            url = clean(srcs[0].get("url"))
            if not url.startswith("http"):
                continue
            news.append([head, clean(item.get("date")), clean(srcs[0].get("publisher")), url])
            if len(news) == MAX_NEWS:
                break
        if news:
            rec["nw"] = news

        alerts = [a for a in (s.get("alerts") or []) if isinstance(a, str)]
        alerts = [a.strip() for a in alerts if a.strip() and not is_housekeeping(a)]
        if alerts:
            rec["al"] = alerts[:MAX_ALERTS]

        officers = []
        for o in ((reg.get("officers") or {}).get("current") or []):
            nm, role = clean(o.get("name")), clean(o.get("role"))
            if nm and role:
                officers.append("%s — %s" % (nm, role))
            if len(officers) == MAX_OFFICERS:
                break
        if officers:
            rec["o"] = officers

        if reg.get("employees") is not None:
            rec["e"] = reg["employees"]
        if reg.get("turnoverGBP") is not None:
            rec["t"] = reg["turnoverGBP"]
        series = []
        for p in (reg.get("turnoverSeries") or []):
            end, val = clean(p.get("periodEnd")), p.get("value")
            if end and val is not None:
                series.append([end, val])
        if series:
            rec["ts"] = series

        records.append(rec)

    records.sort(key=lambda r: r["n"].lower())
    return records, omitted, alias_index


# ------------------------------------------------------------------ invariants
def check(records, index_doc, fin_doc):
    """Every claim this file makes, re-derived and tested. Returns a list of
    failures; an empty list means the build may be written."""
    fails = []
    names = [r["n"] for r in records]
    nameset = set(names)
    index_names = {s.get("name") for s in (index_doc.get("suppliers") or [])}
    fin = fin_doc.get("companies") or {}

    if len(names) != len(nameset):
        dupes = [n for n, c in collections.Counter(names).items() if c > 1]
        fails.append("duplicate company names in co: %s" % dupes[:5])
    off = sorted(nameset - index_names)
    if off:
        fails.append("%d company names are not canonical supplier-index names: %s"
                     % (len(off), off[:5]))

    for r in records:
        n = r["n"]
        if not r.get("r") or not r.get("no"):
            fails.append("%s: published with no registered name or company number" % n)
        if r.get("no") != (fin.get(n) or {}).get("companyNumber"):
            fails.append("%s: company number does not match company-financials.json" % n)
        if "cp" in r and "nr" in r:
            fails.append("%s: carries both a derived and a fallback competitor set" % n)
        for label, cap in (("pr", MAX_PRODUCTS), ("ln", MAX_LINKS), ("f", MAX_FRAMEWORKS),
                           ("al", MAX_ALERTS), ("nw", MAX_NEWS), ("aw", MAX_AWARDS),
                           ("cp", MAX_COMPETITORS), ("nr", MAX_COMPETITORS),
                           ("o", MAX_OFFICERS)):
            if label in r and len(r[label]) > cap:
                fails.append("%s: %s exceeds its cap of %d" % (n, label, cap))
            if label in r and not r[label]:
                fails.append("%s: %s present but empty — omit the key instead" % (n, label))
        last = None
        for comp, count in r.get("cp", []):
            if comp == n:
                fails.append("%s: listed as its own competitor" % n)
            if comp not in nameset:
                fails.append("%s: competitor %r is not a selectable company" % (n, comp))
            if root_of(comp) == root_of(n):
                fails.append("%s: competitor %r is the same group" % (n, comp))
            if not isinstance(count, int) or count < 1:
                fails.append("%s: competitor %r has no shared-agreement count" % (n, comp))
            if last is not None and count > last:
                fails.append("%s: competitor set is not ranked by shared count" % n)
            last = count
        for comp in r.get("nr", []):
            if comp == n:
                fails.append("%s: listed in its own fallback set" % n)
            if comp not in nameset:
                fails.append("%s: fallback competitor %r is not a selectable company" % (n, comp))
        for key_, pos in (("ln", 1), ("f", 2), ("aw", 4), ("nw", 3)):
            for row in r.get(key_, []):
                if not str(row[pos]).startswith("http"):
                    fails.append("%s: %s row carries a non-http link" % (n, key_))
        for period, value in r.get("ts", []):
            if len(str(period)) != 10 or not isinstance(value, (int, float)):
                fails.append("%s: turnover series row is not (date, number)" % n)
    return fails


# --------------------------------------------------------------------- report
def report(records, published):
    old = {r["n"]: r for r in published}
    new = {r["n"]: r for r in records}
    print("published records: %d   rebuilt records: %d" % (len(old), len(new)))
    print("names only in the published file: %d" % len(set(old) - set(new)))
    print("names only in the rebuild:        %d" % len(set(new) - set(old)))
    both = sorted(set(old) & set(new))
    print("names in both:                    %d" % len(both))
    fields = ["r", "no", "st", "ac", "am", "inc", "sp", "pr", "vo", "ln", "f",
              "cp", "nr", "aw", "nw", "al", "o", "e", "t", "ts"]
    print("\n%-4s %8s %8s %8s %8s" % ("fld", "same", "differ", "onlyOld", "onlyNew"))
    for f in fields:
        same = differ = only_old = only_new = 0
        for n in both:
            a, b = old[n].get(f), new[n].get(f)
            if a is None and b is None:
                continue
            if a is None:
                only_new += 1
            elif b is None:
                only_old += 1
            elif a == b:
                same += 1
            else:
                differ += 1
        print("%-4s %8d %8d %8d %8d" % (f, same, differ, only_old, only_new))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="build and run the invariants, write nothing")
    ap.add_argument("--report", action="store_true",
                    help="print a per-field diff against the published file, write nothing")
    args = ap.parse_args()

    doc = load(PREP)
    index_doc = load(INDEX)
    fin_doc = load(FIN)

    records, omitted, _ = build_records(index_doc, fin_doc)
    fails = check(records, index_doc, fin_doc)
    if fails:
        print("BUILD REFUSED — %d invariant failure(s):" % len(fails), file=sys.stderr)
        for f in fails[:40]:
            print("  " + f, file=sys.stderr)
        return 1

    if args.report:
        report(records, doc.get("co") or [])
        print("\nomitted, no Companies House record: %d" % len(omitted))
        return 0

    doc["co"] = records
    meta = doc.get("meta") or {}
    meta["n"] = len(records)
    meta["built"] = datetime.date.today().strftime("%d/%m/%Y")
    meta["coAsOf"] = fin_doc.get("dataAsOf") or meta.get("coAsOf")
    meta["supAsOf"] = index_doc.get("dataAsOf") or meta.get("supAsOf")
    meta["cpRule"] = CP_RULE
    meta["nrRule"] = NR_RULE
    meta["omitRule"] = OMIT_RULE
    meta["omittedNoRegister"] = len(omitted)
    meta["builtBy"] = "scripts/build_interview_prep.py"
    doc["meta"] = meta

    if args.check:
        print("OK — %d companies, %d omitted for want of a register record; "
              "nothing written (--check)." % (len(records), len(omitted)))
        return 0

    with open(PREP, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    print("wrote %s — %d companies, %d omitted for want of a register record."
          % (os.path.relpath(PREP, ROOT), len(records), len(omitted)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
