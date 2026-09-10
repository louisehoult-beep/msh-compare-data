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

PUBLISHING ELSEWHERE IS NOT BEING UNREACHABLE (added 09/09/2026). A supplier
awarded on this framework that already publishes products, but none under a
category belonging to this framework's speciality, sits in
`publishedElsewhere`. Until this change that bucket counted towards nothing:
a framework whose whole unpublished remainder was publishing elsewhere came
out with `actionableTotal` 0 and was stamped BLOCKED — "every awarded supplier
not yet published has been read and refused" — which was simply untrue of
suppliers that had been crawled successfully and were only missing a
(supplier, division) -> category mapping into this speciality. Digital
Diagnostic Solutions (11 of 54), Blood Collection Devices (8 of 19) and CT
Scanners (4 of 8) were all wrongly BLOCKED on 09/09/2026 for that reason, and
BLOCKED is not a soft label: the sweep skips a blocked framework, so a wrong
one drops it for good. Those suppliers are now counted as
`actionable.publishedElsewhereNeedingCategory` — mapping work, not crawl work
— and BLOCKED additionally requires at least one recorded refusal, so the
message can never claim refusals that do not exist.

A REFUSAL IS A FACT ABOUT THE SITE, NOT ABOUT THE BUCKET (added 10/09/2026,
^o404). The bucket chain tests published/held BEFORE refusals, so any supplier
that publishes anything anywhere never reaches the `refused` branch and its
recorded refusal disappeared from the framework's report: 270 rows across 62
suppliers on 10/09/2026. `refusedSuppliers` now lists every awarded supplier
carrying a refusal whatever bucket it landed in, each stamped with that bucket.
Reporting only — the actionable counts are untouched, so nothing can become
BLOCKED because of it.

CAPTURED IS NOT THE SAME AS COUNTED (added 10/09/2026, ^o385). A supplier whose
site was read in full can contribute neither a published nor a held product:
mapping a category for a supplier whose captured rows carry no source drops it
out of `heldBySupplier` without adding it to `products`. It used to fall all the
way through to `notCrawled` and be re-offered as fresh crawl work. Read from
supplier-products.json's `suppliers` and counted as `capturedNothingCounted`.

A SECOND NAME ON A CAPTURED DOMAIN IS A MERGE, NOT A CRAWL (added 10/09/2026,
^o322). A seed record whose website is already captured under another canonical
name is counted as `duplicateOfCapturedSupplier` and kept out of crawlWorklist:
crawling it files the same range twice under two names, which is what happened
to "GB UK Ltd" beside "GBUK Group" on gbukgroup.com.

A framework is DONE only when every awarded supplier is published with a
category. Anything else is named, counted and left as work — never rounded up.

NAME RESOLUTION. Framework supplier names and crawl supplier names disagree
constantly ("BD" / "Becton Dickinson UK Ltd"). Every join goes through the
company alias registry; an UNRESOLVED or AMBIGUOUS name is reported as such and
never fuzzy-matched (see [[company-alias-registry]]).

Usage:  python3 scripts/build_coverage_ledger.py
Writes: data/coverage-ledger.json  and  docs/COVERAGE-LEDGER.md

THIS COPY IS THE ONE THAT RUNS. It was mirrored into msh-compare-data on
03/09/2026 from Hub/Product-Build/market-intelligence-engine/scripts/, which
was then the canonical original. It no longer is: the 06/09/2026 refusals and
heldBySupplier fixes and the 09/09/2026 publishedElsewhere fix were all made
here and never in that copy, and `differentiator-framework-coverage` — the
only thing that regenerates the ledger — works entirely inside this repo.
Corrected 09/09/2026, because the sentence that used to sit here said to
re-copy this file from the engine folder, which would have silently reverted
three fixes. The engine copy is marked superseded; edit this one.
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
    prod = load("supplier-products.json")
    refusals = {}
    for rawname, rec in (prod.get("refusals") or {}).items():
        st, canon, _ = CA.resolve(rawname, reg)
        refusals[canon if st == "RESOLVED" else rawname] = rec

    # CAPTURED: the crawler's own record of every site it has actually read, from
    # supplier-products.json's `suppliers`. Added 10/09/2026 for ^o385.
    #
    # WHY A THIRD SIGNAL. Until this change a supplier counted as crawled only if
    # it contributed a PUBLISHED or a HELD product to differentiator.json. Both
    # counts can be zero for a supplier whose site was read in full: mapping a
    # category for a supplier whose captured rows carry no source removes it from
    # `heldBySupplier` without adding it to `products`, so it falls through the
    # whole chain to `notCrawled` and is re-offered as fresh crawl work it has
    # already had. Swann Morton is the live case (137 products captured at
    # numeric URLs like /product/15.php, so the detail crawler's slug match never
    # fires and no row gets a source, ^o379) — one framework row today, but the
    # class re-offers a worked supplier every run and a re-crawl is how recorded
    # captures get overwritten.
    #
    # A captured-but-uncounted supplier is NOT a crawl target: the site has been
    # read and the answer is on record. It is counted as its own kind of work,
    # `capturedNothingCounted`, and never enters crawlWorklist.
    captured, captured_by_domain = {}, collections.defaultdict(set)
    for rawname, rec in (prod.get("suppliers") or {}).items():
        st, canon, _ = CA.resolve(rawname, reg)
        key = canon if st == "RESOLVED" else rawname
        d = (rec.get("domain") or "").strip().lower()
        d = d[4:] if d.startswith("www.") else d
        captured[key] = d or captured.get(key) or None
        if d:
            captured_by_domain[d].add(key)

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
                   "capturedNothingCounted": [], "notCrawled": [],
                   "refused": [], "unknown": []}
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
            elif canon in captured:
                # Read in full, nothing reaching either count. See the `captured`
                # note above (^o385). Not a crawl target.
                buckets["capturedNothingCounted"].append(canon)
            else:
                buckets["notCrawled"].append(canon)
        total = len(sups)
        done = len(buckets["published"])

        # DUPLICATE OF AN ALREADY-CAPTURED SUPPLIER (^o322, added 10/09/2026).
        # A seed record whose website is already captured under a DIFFERENT
        # canonical name is not crawl work: crawling it captures the same range a
        # second time under a second name, and the ledger then counts both. That
        # is how "GB UK Ltd" (344 products) came to sit beside "GBUK Group" (343)
        # on the same gbukgroup.com — crawled and reverted on 06/09/2026.
        # The work here is an identity/merge decision (^o298, ^o330), not a
        # re-crawl, so it is counted in its own right and kept out of
        # crawlWorklist and domainsMissing rather than dropped.
        def _dup_owner(n):
            d = domains.get(n)
            if not d:
                return None
            owners = captured_by_domain.get(d, set()) - {n}
            return sorted(owners)[0] if owners else None

        dupOf = {n: _dup_owner(n)
                 for n in buckets["heldOnly"] + buckets["notCrawled"]}
        dupOf = {n: o for n, o in dupOf.items() if o}
        # Counted in `actionable` only for the notCrawled ones. A duplicate that
        # ALSO has held products is already counted once under
        # heldNeedingCategory, and counting it again here would inflate `left`
        # by one per duplicate — measured on 10/09/2026 as all three live cases
        # (MIS Healthcare, Danone Nutricia Early Life Nutrition, Talley), so the
        # bug would have shipped in the same change that added the report.
        dupNotCrawled = {n: o for n, o in dupOf.items() if n in buckets["notCrawled"]}

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
                if n not in refusals and n not in dupOf],
            "domainsMissing": sorted(
                n for n in buckets["heldOnly"] + buckets["notCrawled"]
                if not domains.get(n) and n not in dupOf),
            # Seed records whose website is already captured under another name.
            # See the dupOf note above (^o322).
            "duplicateOfCapturedSupplier": [
                {"supplier": n, "domain": domains.get(n), "alreadyCapturedAs": o}
                for n, o in sorted(dupOf.items())],
            # Attempted, read, and found uncrawlable — the reason and the date are
            # the crawler's own record. Reported so a reader can see the framework
            # was worked, not neglected; never re-queued as if it were fresh work.
            #
            # EVERY awarded supplier carrying a recorded refusal is listed here,
            # whichever bucket it landed in — not only the `refused` bucket
            # (^o404, fixed 10/09/2026). The bucket chain tests `pubcount` and
            # `heldcount` BEFORE it tests refusals, so a supplier that publishes
            # anything anywhere never reaches the `refused` branch, and its
            # refusal became invisible: 270 framework rows across 62 suppliers on
            # 10/09/2026, including Philips (20 rows), Fannin (UK) Limited (21),
            # Medline Industries (15) and B. Braun Medical (12). A reader then saw
            # a framework as neglected when its remainder had in fact been read
            # and answered. `bucket` says which chain branch the supplier landed
            # in, so "refused AND publishing outside this speciality" reads as the
            # two separate facts it is. This is reporting only: the actionable
            # counts below are unchanged by it, so no framework can become BLOCKED
            # because of this fix.
            "refusedSuppliers": [
                {"supplier": n,
                 "domain": refusals[n].get("domain"),
                 "reason": refusals[n].get("reason"),
                 "checked": refusals[n].get("checked"),
                 "bucket": b}
                for b in ("refused", "publishedElsewhere", "heldOnly",
                          "capturedNothingCounted", "published", "notCrawled")
                for n in buckets[b] if n in refusals],
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
                # Crawled and publishing, just not into this speciality: the
                # work is a category mapping, never a re-crawl. See the
                # docstring's PUBLISHING ELSEWHERE note (09/09/2026).
                "publishedElsewhereNeedingCategory": len(buckets["publishedElsewhere"]),
                "heldNeedingCategory": len(buckets["heldOnly"]),
                # Site read in full, nothing reaching a published or a held
                # count (^o385). Real work — the capture needs a source or a
                # mapping — but never a re-crawl.
                "capturedNothingCounted": len(buckets["capturedNothingCounted"]),
                # Its website is already captured under another seed name, so the
                # work is an identity/merge decision, not a crawl (^o322).
                "duplicateOfCapturedSupplier": len(dupNotCrawled),
                "crawlable": sum(1 for n in buckets["notCrawled"]
                                 if domains.get(n) and n not in dupOf),
                "needDomain": sum(1 for n in buckets["notCrawled"]
                                  if not domains.get(n) and n not in dupOf),
            },
            **buckets,
        })
        a = rows[-1]["actionable"]
        left = sum(a.values())
        rows[-1]["actionableTotal"] = left
        # `left` now includes publishedElsewhere, so BLOCKED is already out of
        # reach for those frameworks; the refusal test is kept as well so the
        # sentence below can never report "(0 recorded refusal(s))".
        rows[-1]["blockedReason"] = None if left or not buckets["refused"] or \
            rows[-1]["state"] in ("DONE", "OUT OF SCOPE", "UNMAPPED") else (
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
            "suppliersRefusedButPublishingElsewhere": len({
                w["supplier"] for r in rows if r["inScope"]
                for w in r["refusedSuppliers"]
                if w["bucket"] != "refused"}),
            "suppliersCapturedNothingCounted": len({
                n for r in rows if r["inScope"]
                for n in r["capturedNothingCounted"]}),
            "suppliersDuplicateOfCaptured": len({
                w["supplier"] for r in rows if r["inScope"]
                for w in r["duplicateOfCapturedSupplier"]}),
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
          "supplier names + suppliers publishing only outside this speciality +",
          "suppliers held uncategorised + suppliers captured with nothing counted +",
          "suppliers duplicating a domain already captured under another name +",
          "suppliers crawlable + suppliers needing a website. Only the last two are",
          "crawl work. The second is mapping work: the supplier's range is already",
          "captured and published, just not under a category this framework's",
          "speciality contains. The fourth is an identity/merge decision — crawling",
          "it would file the same range twice under two names.",
          "**Refused** suppliers were read and found",
          "uncrawlable (robots.txt, no product API, or a catalogue that would",
          "misrepresent the range), with the reason and date recorded in",
          "`data/supplier-products.json`; they are not counted as work and must not",
          "be re-crawled from this table, or the recorded judgement is overwritten.",
          "A refusal is listed for every awarded supplier that carries one, including",
          "suppliers counted under Left because they publish outside this speciality:",
          "the two facts are separate, and the refusal used to be invisible for any",
          "supplier publishing anything anywhere.",
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
        print("  %5.1f%%  %3d left (%d unresolved, %d mapped elsewhere, %d held, "
              "%d captured-uncounted, %d duplicate, %d crawlable, %d need domain)  %s"
              % (r["coverage"], r["actionableTotal"], a["unresolvedNames"],
                 a["publishedElsewhereNeedingCategory"],
                 a["heldNeedingCategory"], a["capturedNothingCounted"],
                 a["duplicateOfCapturedSupplier"], a["crawlable"], a["needDomain"],
                 (r["framework"] or "")[:52]))


if __name__ == "__main__":
    main()
