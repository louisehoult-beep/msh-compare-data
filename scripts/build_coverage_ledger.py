#!/usr/bin/env python3
"""
build_coverage_ledger.py — the coverage ledger for the Differentiator.

WHY THIS EXISTS. The Differentiator publishes 7,984 products and holds 51,350.
"Held" is the honest answer for a product whose category is unknown (root rule
14), but held is not the same as *known about*. Without a ledger there is no way
to say which product areas are finished and which are not, so the attribute
sweep would be a guess dressed as progress.

The ledger walks the NHS Supply Chain FRAMEWORKS — one per row, all 121 of them
— because that is the unit a rep actually sells into, and because a framework
names its own award-winning suppliers. For each framework it answers:

  * which awarded suppliers are in the Hub's supplier index at all
  * which of those have any product published in the Differentiator
  * which have products HELD (crawled, uncategorised, invisible)
  * which have nothing crawled at all
  * which were ATTEMPTED AND REFUSED, with the recorded reason and date

REFUSALS ARE NOT WORK (added 06/09/2026). A supplier whose site was read and
found uncrawlable — robots.txt forbids it, the site publishes no product API, or
the only thing its catalogue exposes would misrepresent the company's range — is
recorded in data/supplier-products.json's `refusals` with a reason and a date.
Until this change the ledger counted those suppliers as "not crawled", so the
lowest-coverage framework it named was usually one that had already been worked
to exhaustion. Worse, the resulting crawl worklist drove re-crawls that
OVERWROTE those recorded refusals, because crawl_supplier_site.py only applies
its refusal TTL on the --auto path and not to an explicitly named --supplier.
That is how a batch run on 06/09/2026 destroyed three considered refusal
records (Clinisys, Hermes Medical Solutions, Magentus) and had to revert.
So: a refused supplier is reported in its own bucket, is excluded from
crawlWorklist and domainsMissing, and does not count towards `actionable`.
A framework with no actionable suppliers left carries a blockedReason.

A framework is DONE only when every awarded supplier is published with a
category. Anything else is named, counted and left as work — never rounded up.

NAME RESOLUTION. Framework supplier names and crawl supplier names disagree
constantly ("BD" / "Becton Dickinson UK Ltd"). Every join goes through the
company alias registry; an UNRESOLVED or AMBIGUOUS name is reported as such and
never fuzzy-matched (see [[company-alias-registry]]).

Usage:  python3 scripts/build_coverage_ledger.py
Writes: data/coverage-ledger.json  and  docs/COVERAGE-LEDGER.md

MIRRORED INTO msh-compare-data 03/09/2026 (canonical original stays at
Hub/Product-Build/market-intelligence-engine/scripts/, which writes its
ledger alongside itself) so a cloud session, with no OneDrive access, can
regenerate the ledger and pick a framework to work on. Re-copy this file
from the canonical original after any change there.
"""
import json, os, sys, collections, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
sys.path.insert(0, os.path.join(REPO, "company-aliases"))
import company_alias as CA


# SCOPE (Lou's decision, 26/08/2026: "clinical only"). Scope is read from NHS
# Supply Chain's OWN category on the framework record, never from the framework
# name, so a rename upstream cannot silently move something in or out. Food and
# Facilities/Office are out: no medical device rep compares a product against a
# beverage contract or an office chair. Out of scope does not mean deleted —
# anything already published in those areas stays live and untouched; it just
# stops driving the sweep.
IN_SCOPE = {"Medical and Surgical Consumables",
            "Diagnostic Equipment and Services",
            "Rehabilitation and Community",
            "Medical Technology"}
OUT_REASON = {"Food": "NHS Supply Chain catering category — not a medical device market",
              "Facilities and Office Solutions":
                  "estates, catering and office supply — outside the Hub's medical sales audience"}


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def main():
    reg = CA.load_registry()
    fw = load("frameworks.json")
    diff = load("differentiator.json")
    seed = load("supplier-seed.json")
    vocab = load("compare-suppliers.json")["specialities"]
    # Recorded crawl refusals, keyed on the crawler's own supplier name. Resolved
    # through the alias registry like every other join here, never fuzzy-matched.
    refusals = {}
    for rawname, rec in (load("supplier-products.json").get("refusals") or {}).items():
        st, canon, _ = CA.resolve(rawname, reg)
        refusals[canon if st == "RESOLVED" else rawname] = rec

    # framework URL -> Hub speciality key. compare-suppliers.json already records
    # each speciality's buying route, so the framework a speciality is bought on
    # is read from the file, never inferred from the framework's own wording.
    fwSpec, specTypes = {}, {}
    for skey, sv in vocab.items():
        specTypes[skey] = sorted((sv.get("types") or {}).keys()) \
            if isinstance(sv.get("types"), dict) else list(sv.get("types") or [])
        for r in (sv.get("route") or []):
            u = (r.get("url") or "").rstrip("/")
            if u:
                fwSpec.setdefault(u, []).append(skey)

    # canonical name -> what we hold on that supplier
    published = collections.defaultdict(set)   # canon -> {cat}
    pubcount = collections.Counter()
    for p in diff.get("products", []):
        st, canon, _ = CA.resolve(p.get("supplier", ""), reg)
        key = canon if st == "RESOLVED" else p.get("supplier", "")
        published[key].add(p.get("cat"))
        pubcount[key] += 1

    # HELD: crawled, but no recorded category mapping, so nothing publishes.
    # Read from differentiator.json's `heldBySupplier`, which is complete.
    # Until 06/09/2026 this read `heldTopDivisions` — the 40 biggest (supplier,
    # division) pairs, written for a reader and never a complete list. Every
    # supplier whose whole held range was smaller than the 40th pair therefore
    # fell through to `notCrawled` and was queued as fresh crawl work it had
    # already had: Purple Surgical (76 products) and BioSpectrum Ltd (19) were
    # both re-crawled on 06/09/2026 for that reason alone, and both returned
    # exactly what was already on record. heldTopDivisions is still read as a
    # fallback so an older differentiator.json does not break this script.
    heldcount = collections.Counter()
    by_supplier = diff.get("heldBySupplier")
    if by_supplier:
        for rawname, n in by_supplier.items():
            st, canon, _ = CA.resolve(rawname, reg)
            heldcount[canon if st == "RESOLVED" else rawname] += n
    else:
        for h in diff.get("heldTopDivisions", []):
            st, canon, _ = CA.resolve(h.get("supplier", ""), reg)
            key = canon if st == "RESOLVED" else h.get("supplier", "")
            heldcount[key] += h.get("products", 0)

    # supplier -> its own website domain, read from supplier-seed.json links[].
    # A "Website"-labelled link wins; otherwise the first link that is not a
    # third-party record (NHSSC catalogue, LinkedIn, Companies House). A missing
    # domain is a real gap and is listed as one — never guessed from the name.
    THIRD_PARTY = ("supplychain.nhs.uk", "linkedin.com", "companieshouse",
                   "find-and-update", "gov.uk", "twitter.com", "facebook.com")

    def domain_of(rec):
        best = None
        for l in (rec.get("links") or []):
            host = urllib.parse.urlparse(l.get("url") or "").netloc.lower()
            host = host[4:] if host.startswith("www.") else host
            if not host or any(t in host for t in THIRD_PARTY):
                continue
            if (l.get("label") or "").strip().lower() == "website":
                return host
            best = best or host
        return best

    domains = {}
    known = set()
    for s in (seed.get("suppliers") or seed.get("entries") or []):
        n = s.get("name") if isinstance(s, dict) else s
        if not n:
            continue
        st, canon, _ = CA.resolve(n, reg)
        key = canon if st == "RESOLVED" else n
        known.add(key)
        d = domain_of(s) if isinstance(s, dict) else None
        if d:
            domains[key] = d

    rows, unresolved = [], collections.Counter()
    for f in fw.get("frameworks", []):
        sups = f.get("suppliers") or []
        nhsscCat = f.get("category")
        inScopeFw = nhsscCat in IN_SCOPE
        specKeys = fwSpec.get((f.get("url") or "").rstrip("/"), [])
        buckets = {"published": [], "publishedElsewhere": [], "heldOnly": [],
                   "notCrawled": [], "refused": [], "unknown": []}
        for name in sups:
            st, canon, _ = CA.resolve(name, reg)
            if st != "RESOLVED":
                unresolved[name] += 1
                buckets["unknown"].append(name)
                continue
            inScope = specKeys and any(
                c.split(":")[0] in specKeys for c in published.get(canon, ()) if c)
            if inScope:
                buckets["published"].append(canon)
            elif pubcount.get(canon):
                buckets["publishedElsewhere"].append(canon)
            elif heldcount.get(canon):
                buckets["heldOnly"].append(canon)
            elif canon in refusals:
                buckets["refused"].append(canon)
            else:
                buckets["notCrawled"].append(canon)
        total = len(sups)
        done = len(buckets["published"])
        rows.append({
            "framework": f.get("name"),
            "url": f.get("url"),
            "category": f.get("category"),
            "ends": f.get("ends"),
            "suppliersAwarded": total,
            "suppliersPublished": done,
            "coverage": round(100.0 * done / total, 1) if total else 0.0,
            "nhsscCategory": nhsscCat,
            "inScope": inScopeFw,
            "outOfScopeReason": None if inScopeFw else OUT_REASON.get(nhsscCat, "not a clinical category"),
            "state": ("OUT OF SCOPE" if not inScopeFw else
                      "UNMAPPED" if not specKeys else
                      "DONE" if total and done == total else
                      "STARTED" if done else "NOT STARTED"),
            "speciality": specKeys,
            # A supplier with a recorded crawl refusal NEVER appears here, even
            # when it also has held products from an earlier capture. Added
            # 06/09/2026 with the heldBySupplier fix above: that fix correctly
            # moved CD Medical Ltd and Healthcare 25 Ltd out of `refused` and
            # into `heldOnly` (they do have crawled products, held for want of a
            # category), and heldOnly is what this worklist is built from — which
            # would have queued two answered suppliers for exactly the re-crawl
            # that destroyed three considered refusals on 06/09/2026. Their held
            # products still need a mapping decision; that is a decision, not a
            # crawl, and it is counted in `actionable.heldNeedingCategory`.
            "crawlWorklist": [
                {"supplier": n, "domain": domains.get(n)}
                for n in buckets["heldOnly"] + buckets["notCrawled"]
                if n not in refusals],
            "domainsMissing": sorted(
                n for n in buckets["heldOnly"] + buckets["notCrawled"]
                if not domains.get(n)),
            # Attempted, read, and found uncrawlable — the reason and the date are
            # the crawler's own record. Reported so a reader can see the framework
            # was worked, not neglected; never re-queued as if it were fresh work.
            "refusedSuppliers": [
                {"supplier": n,
                 "domain": refusals[n].get("domain"),
                 "reason": refusals[n].get("reason"),
                 "checked": refusals[n].get("checked")}
                for n in buckets["refused"]],
            "route": "NHSSC framework" if specKeys else "no Hub speciality mapped to this framework",
            "catsInScope": sorted({c for s in buckets["published"]
                                   for c in published[s]
                                   if c and c.split(":")[0] in specKeys}),
            # What is genuinely left to do on this framework, split by the kind of
            # work it is. A refused supplier appears in none of these: it has been
            # read and answered, and re-queueing it is how recorded judgements get
            # overwritten. Zero across all four is the honest "nothing left by a
            # permitted route", which is not the same as DONE.
            "actionable": {
                "unresolvedNames": len(buckets["unknown"]),
                "heldNeedingCategory": len(buckets["heldOnly"]),
                "crawlable": sum(1 for n in buckets["notCrawled"] if domains.get(n)),
                "needDomain": sum(1 for n in buckets["notCrawled"] if not domains.get(n)),
            },
            **buckets,
        })
        a = rows[-1]["actionable"]
        left = sum(a.values())
        rows[-1]["actionableTotal"] = left
        rows[-1]["blockedReason"] = None if left or rows[-1]["state"] in (
            "DONE", "OUT OF SCOPE", "UNMAPPED") else (
            "every awarded supplier not yet published has been read and refused "
            "(%d recorded refusal(s)) — no permitted route left to the rest of "
            "this framework, so its coverage cannot rise without a new route"
            % len(buckets["refused"]))

    ORDER = {"STARTED": 0, "NOT STARTED": 1, "UNMAPPED": 2, "DONE": 3,
             "OUT OF SCOPE": 4}
    rows.sort(key=lambda r: (ORDER[r["state"]], -r["suppliersAwarded"]))
    out = {
        "rule": "A framework counts as DONE only when every supplier awarded on it "
                "has at least one product published with a gated category in the "
                "Differentiator. Suppliers whose name will not resolve against the "
                "company alias registry are listed as unknown and never guessed.",
        "generatedFrom": {
            "frameworks.json": fw.get("dataAsOf"),
            "differentiator.json published": diff.get("counts", {}).get("published"),
            "differentiator.json held": diff.get("counts", {}).get("held"),
        },
        "counts": {
            "frameworks": len(rows),
            "done": sum(1 for r in rows if r["state"] == "DONE"),
            "started": sum(1 for r in rows if r["state"] == "STARTED"),
            "notStarted": sum(1 for r in rows if r["state"] == "NOT STARTED"),
            "unmapped": sum(1 for r in rows if r["state"] == "UNMAPPED"),
            "outOfScope": sum(1 for r in rows if r["state"] == "OUT OF SCOPE"),
            "inScope": sum(1 for r in rows if r["inScope"]),
            "supplierNamesUnresolved": len(unresolved),
            "inScopeSuppliersNeedingCrawl": len({
                w["supplier"] for r in rows if r["inScope"]
                for w in r["crawlWorklist"]}),
            "inScopeSuppliersNeedingDomain": len({
                n for r in rows if r["inScope"] for n in r["domainsMissing"]}),
            "suppliersRefused": len({
                w["supplier"] for r in rows if r["inScope"]
                for w in r["refusedSuppliers"]}),
            "blockedFrameworks": sum(1 for r in rows if r["blockedReason"]),
        },
        "unresolvedSupplierNames": unresolved.most_common(),
        "frameworks": rows,
    }
    with open(os.path.join(REPO, "data", "coverage-ledger.json"), "w") as f:
        json.dump(out, f, indent=1)

    c = out["counts"]
    md = ["# Differentiator coverage ledger", "",
          "Generated by `scripts/build_coverage_ledger.py`. Do not edit by hand.", "",
          out["rule"], "",
          f"**{c['done']} frameworks done · {c['started']} started · "
          f"{c['notStarted']} not started**, of {c['frameworks']}.", "",
          "UNMAPPED means no Hub speciality records this framework as its buying",
          "route, so coverage cannot be measured against it yet. It is not a",
          "synonym for out of scope: decide each one deliberately.", "",
          "**Left** is the work genuinely still available on a framework: unresolved",
          "supplier names + suppliers held uncategorised + suppliers crawlable +",
          "suppliers needing a website. **Refused** suppliers were read and found",
          "uncrawlable (robots.txt, no product API, or a catalogue that would",
          "misrepresent the range), with the reason and date recorded in",
          "`data/supplier-products.json`; they are not counted as work and must not",
          "be re-crawled from this table, or the recorded judgement is overwritten.",
          f"**{c['blockedFrameworks']} framework(s) have nothing left by a permitted route** —",
          "low coverage there means exhausted, not neglected.", "",
          "| Framework | Speciality | Awarded | Published | Coverage | Left | Refused | State |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append("| %s | %s | %d | %d | %.1f%% | %d | %d | %s |" % (
            r["framework"], ", ".join(r["speciality"]) or "—",
            r["suppliersAwarded"], r["suppliersPublished"],
            r["coverage"], r["actionableTotal"], len(r["refusedSuppliers"]),
            r["state"] + (" · BLOCKED" if r["blockedReason"] else "")))
    with open(os.path.join(REPO, "docs", "COVERAGE-LEDGER.md"), "w") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps(c, indent=1))
    print("\nTop 12 by size:")
    for r in [x for x in rows if x["inScope"]][:14]:
        print("  %-52s %-14s %3d awarded %3d pub %3d left  %s" % (
            (r["framework"] or "")[:52], (",".join(r["speciality"]) or "-")[:14],
            r["suppliersAwarded"], r["suppliersPublished"],
            r["actionableTotal"], r["state"]))

    live = [x for x in rows if x["state"] == "STARTED" and x["actionableTotal"]]
    live.sort(key=lambda x: (x["coverage"], -x["suppliersAwarded"]))
    print("\nLowest-coverage STARTED frameworks that still have work left:")
    for r in live[:8]:
        a = r["actionable"]
        print("  %5.1f%%  %3d left (%d unresolved, %d held, %d crawlable, %d need domain)  %s"
              % (r["coverage"], r["actionableTotal"], a["unresolvedNames"],
                 a["heldNeedingCategory"], a["crawlable"], a["needDomain"],
                 (r["framework"] or "")[:52]))


if __name__ == "__main__":
    main()
