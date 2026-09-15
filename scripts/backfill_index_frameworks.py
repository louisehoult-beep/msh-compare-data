#!/usr/bin/env python3
"""Push the sourced framework capture into supplier-index.json and supplier-seed.json,
so every Hub surface shows the same framework list.

WHY THIS EXISTS
---------------
data/frameworks.json is the sourced answer to "which frameworks is this supplier on",
read from NHS Supply Chain's own contract launch briefs. But on 06/08/2026 only two
consumers read it: the Company Report and the Top 10 panel. Everything else — the
Suppliers directory (app/supplier-search.js), Meeting Prep, the comparison tools —
reads the `frameworks[]` array inside supplier-index.json / supplier-seed.json, which
was hand-curated and badly incomplete. GBUK Group appeared with 22 frameworks on the
report and 2 everywhere else. One fact, two answers, is worse than one wrong answer:
it makes both untrustworthy.

Rewiring five apps would have been five chances to introduce a difference. Writing the
sourced list into the arrays those apps already read fixes all of them at once, and
keeps frameworks.json as the single source it is derived from.

WHAT IT DOES, AND WHAT IT REFUSES TO DO
---------------------------------------
- ADDS a framework entry to a supplier only where that framework's own brief names it,
  under the supplier's own name or a recorded alias. Never by resemblance.
- Each added entry carries `source: "nhssc-brief"`, the brief URL, the reference and the
  dates, so a reader (and the next script) can tell a sourced row from a curated one.
- NEVER deletes or overwrites a curated entry. Curated rows carry things the briefs do
  not — re-tender values, award criteria, award dates — and a curated row that looks
  like a duplicate of a sourced one is kept, because the two carry different facts.
- Deduplicates only against rows this script previously added (matched on the brief URL),
  so re-running is idempotent and does not stack copies.
- DROPS a generated `productCategories` row whose framework this run has just taken off
  the supplier. That field is derived from `frameworks[]` (backfill_product_categories.py)
  and nothing else in the company-intelligence workflow re-derives it, so a delisting used
  to leave the category behind, still citing a framework the supplier is no longer recorded
  as being on. That is a claim with its evidence removed, and verify.py's
  seed-product-categories check fails on it — which is how it was found: NHS Supply Chain
  took J & M Medical off the Textiles and Associated Products brief (2025/S 000-048142),
  and the run of 14/09/2026 and every run after it failed the publish gate on the orphaned
  "Facilities and Office Solutions" category. Curated rows (anything this repo did not
  generate) are never touched here, same discipline as the framework rows above.

Run AFTER build_supplier_index.py (which rebuilds the index from scratch and would drop
these rows) and AFTER refresh_frameworks.py. Then stamp_notice.py, then verify.py.
"""
import json
import re
import sys

INDEX = "data/supplier-index.json"
SEED = "data/supplier-seed.json"
FW = "data/frameworks.json"

CO_SUFFIX = re.compile(
    r"\b(ltd|limited|plc|llp|inc|corp|corporation|co|company|holdings|international|"
    r"uk|u k|gb)\b")
# Fixed 21/08/2026 (OUTSTANDING ^o66): the old pattern also stripped industry
# words — "medical", "medica", "health", "healthcare", "systems", "solutions",
# "technologies", "devices", "group", "products". In this sector those words
# ARE the distinguishing part of a name once "Ltd"/legal-form is removed, so
# stripping them collapsed unrelated companies onto one key: "Advanced Medical
# Solutions Ltd", "Advanced Medical Systems Ltd" and "Medica Advanced
# Technologies Ltd" — three separate companies — all reduced to "advanced",
# so every framework brief-matched to any one of them got attached to all
# three. Confirmed by key-collision count: the old pattern collapsed 23
# suppliers into 11 shared-key groups; this pattern collapses 8 suppliers
# into 4, and the survivors are genuine trading-name cases (e.g. "Cardiac
# Services" / "Cardiac Services UK Ltd") that need a human/Companies House
# call, not an algorithmic one — see Data-Verification/framework-key-collision-fix-2026-08-21.md.
# Only true legal-form suffixes are stripped now; matching is otherwise on
# the full name, same discipline as scripts/company_match.py.


def co_key(s):
    k = re.sub(r"[^a-z0-9]+", " ", str(s or "").lower())
    k = CO_SUFFIX.sub(" ", k)
    return re.sub(r"\s+", " ", k).strip()


def norm_name(s):
    """Whitespace/case-normalised only — deliberately NOT co_key(). Used to test
    exact identity against a genuinely ambiguous key (see ambiguous_keys below),
    where stripping the legal-form suffix is exactly what created the ambiguity."""
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()


def ambiguous_keys_for(doc):
    """co_key values shared by two or more DIFFERENTLY-NAMED Hub suppliers in
    this doc.

    Added 21/08/2026 alongside the CO_SUFFIX fix (^o66): stripping only
    legal-form words still leaves a handful of genuine cases — "Cardiac
    Services" / "Cardiac Services UK Ltd" — where NHS Supply Chain's own
    briefs distinguish two real, differently-numbered companies (confirmed at
    Companies House) using nothing but the legal-form suffix the key strips.
    Grouping by key would hand each supplier's frameworks to the other. For
    any key on this list, a brief only counts as a hit if its verbatim
    supplier string is an EXACT name/alias match for that supplier — the same
    no-fuzzy-matching discipline scripts/company_match.py uses — instead of
    the looser key-sharing match every other supplier gets.
    See Data-Verification/framework-key-collision-fix-2026-08-21.md.
    """
    name_keys = {}
    for s in (doc.get("suppliers") or []):
        for n in [s.get("name")] + list(s.get("aliases") or []):
            k = co_key(n)
            if k:
                name_keys.setdefault(k, set()).add(s.get("name"))
    return {k for k, names in name_keys.items() if len(names) > 1}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(path, doc, style):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, **style)
        f.write("\n")


GENERATED_CATEGORIES_BY = "backfill_product_categories.py"


def prune_orphaned_categories(supplier):
    """Drop generated `productCategories` rows citing a framework the supplier no
    longer has, and return how many went.

    Call this immediately AFTER rewriting `supplier["frameworks"]`. A category in
    that field is not an observation — it is derived from a framework row, and
    carries the reference it was derived from. When the brief stops naming the
    supplier, the framework row goes and the derivation no longer holds, so the
    category must go with it rather than outlive its own evidence.

    Deliberately narrow:
      * only rows marked `generatedBy: backfill_product_categories.py` are ever
        considered. A curated category is somebody's own fact and is left alone,
        even if it cites a framework that has gone;
      * a row citing no `frameworkRef` is left alone — there is nothing to check
        it against, and silence is not evidence it is wrong;
      * nothing is dropped when the supplier ends up with no framework references
        at all, which is the shape of a capture that simply did not cover this
        supplier this cycle rather than of a delisting (same reasoning as the
        `if not hits` skip in main(), see STALE-BRIEF-ROWS-2026-09-02.md).
    """
    rows = supplier.get("productCategories")
    if not isinstance(rows, list) or not rows:
        return 0
    own_refs = {fw.get("reference") for fw in (supplier.get("frameworks") or [])
                if isinstance(fw, dict) and fw.get("reference")}
    if not own_refs:
        return 0

    kept = []
    for row in rows:
        if (isinstance(row, dict)
                and row.get("generatedBy") == GENERATED_CATEGORIES_BY
                and isinstance(row.get("source"), dict)):
            ref = row["source"].get("frameworkRef")
            if ref and ref not in own_refs:
                continue
        kept.append(row)

    dropped = len(rows) - len(kept)
    if dropped:
        if kept:
            supplier["productCategories"] = kept
        else:
            del supplier["productCategories"]
    return dropped


def main():
    fw = load(FW)
    frameworks = fw.get("frameworks") or []
    if not frameworks:
        sys.exit("frameworks.json holds no frameworks — refusing to run. Fix the capture first.")

    # supplier key -> list of (framework, verbatim name it was matched under)
    by_key = {}
    for f in frameworks:
        for name in (f.get("suppliers") or []):
            k = co_key(name)
            if not k:
                continue
            by_key.setdefault(k, []).append((f, name))

    stats = {"files": 0, "suppliers_touched": 0, "rows_added": 0, "rows_refreshed": 0,
             "categories_dropped": 0}

    for path, style in ((INDEX, {"indent": 1, "ensure_ascii": False}),
                        (SEED, {"separators": (",", ":"), "ensure_ascii": False})):
        doc = load(path)
        touched = added = refreshed = dropped_categories = 0
        ambiguous_keys = ambiguous_keys_for(doc)

        for s in (doc.get("suppliers") or []):
            keys = {co_key(n) for n in [s.get("name")] + list(s.get("aliases") or [])}
            keys.discard("")
            own_names = {norm_name(n) for n in [s.get("name")] + list(s.get("aliases") or []) if n}
            hits = []
            excluded_urls = set()
            seen_urls = set()
            for k in keys:
                for f, matched in by_key.get(k, []):
                    if k in ambiguous_keys and norm_name(matched) not in own_names:
                        # Shared key, no exact name/alias match — this hit belongs
                        # to the other supplier sharing the key, not this one.
                        # That is a POSITIVE signal, not silence: a previous run
                        # (before this supplier's key was known to be ambiguous,
                        # or before its ambiguity guard existed) may have written
                        # exactly this row here in error. Recorded so it can be
                        # stripped below even when `hits` ends up empty — fixed
                        # 12/09/2026 (^o219) after "Baxter Healthcare Corporation"
                        # was found still carrying five NHS Supply Chain framework
                        # rows that every brief actually names "Baxter Healthcare
                        # Ltd/Limited" for — correctly excluded by this guard on
                        # every run since, but never removed, because the
                        # `if not hits: continue` below skipped the supplier
                        # entirely rather than reaching the code that drops stale
                        # nhssc-brief rows.
                        excluded_urls.add(f["url"])
                        continue
                    if f["url"] in seen_urls:
                        continue
                    seen_urls.add(f["url"])
                    hits.append((f, matched))
            if not hits and not excluded_urls:
                # Genuinely no signal at all under any of this supplier's keys —
                # the original, still-correct reason to leave existing sourced
                # rows untouched (see STALE-BRIEF-ROWS-2026-09-02.md): a capture
                # that simply doesn't cover this supplier this cycle is not
                # evidence the supplier's existing rows are wrong.
                continue

            existing = list(s.get("frameworks") or [])
            # Drop rows this script added on a previous run; curated rows are untouched.
            kept = [r for r in existing if not (isinstance(r, dict) and r.get("source") == "nhssc-brief")]
            refreshed += len(existing) - len(kept)

            rows = []
            for f, matched in sorted(hits, key=lambda h: h[0]["name"].lower()):
                lots = (f.get("supplierLots") or {}).get(matched)
                rows.append({
                    "name": f["name"],
                    "dates": " to ".join([d for d in (f.get("starts"), f.get("ends")) if d]) or None,
                    "note": ("Named on NHS Supply Chain's own contract launch brief for this "
                             "framework, as \"%s\"%s. %d suppliers on the framework."
                             % (matched,
                                (" (" + ", ".join(lots) + ")") if lots else "",
                                f.get("supplierCount") or 0)),
                    "reference": f.get("reference"),
                    "category": f.get("category"),
                    "supplierCount": f.get("supplierCount"),
                    "url": f["url"],
                    "source": "nhssc-brief",
                    "capturedOn": fw.get("dataAsOf"),
                })
            added += len(rows)
            s["frameworks"] = kept + rows
            dropped_categories += prune_orphaned_categories(s)
            touched += 1

        dump(path, doc, style)
        stats["files"] += 1
        stats["suppliers_touched"] += touched
        stats["rows_added"] += added
        stats["rows_refreshed"] += refreshed
        stats["categories_dropped"] += dropped_categories
        print("%-28s %d supplier(s) given sourced frameworks, %d row(s) written "
              "(%d replaced from a previous run)" % (path, touched, added, refreshed))
        if dropped_categories:
            print("%-28s %d generated productCategories row(s) dropped — the framework each "
                  "cited is no longer on that supplier" % ("", dropped_categories))

    print("Done. Curated rows were never removed; only rows previously written by this "
          "script were replaced.")


if __name__ == "__main__":
    main()
