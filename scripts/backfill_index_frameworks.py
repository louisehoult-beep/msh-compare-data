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
    r"\b(ltd|limited|plc|llp|inc|corp|corporation|co|company|group|holdings|international|"
    r"uk|u k|gb|healthcare|health care|health|medical|medica|med|products|solutions|systems|"
    r"technologies|technology|devices|device)\b")


def co_key(s):
    k = re.sub(r"[^a-z0-9]+", " ", str(s or "").lower())
    k = CO_SUFFIX.sub(" ", k)
    return re.sub(r"\s+", " ", k).strip()


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(path, doc, style):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, **style)
        f.write("\n")


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

    stats = {"files": 0, "suppliers_touched": 0, "rows_added": 0, "rows_refreshed": 0}

    for path, style in ((INDEX, {"indent": 1, "ensure_ascii": False}),
                        (SEED, {"separators": (",", ":"), "ensure_ascii": False})):
        doc = load(path)
        touched = added = refreshed = 0

        for s in (doc.get("suppliers") or []):
            keys = {co_key(n) for n in [s.get("name")] + list(s.get("aliases") or [])}
            keys.discard("")
            hits = []
            seen_urls = set()
            for k in keys:
                for f, matched in by_key.get(k, []):
                    if f["url"] in seen_urls:
                        continue
                    seen_urls.add(f["url"])
                    hits.append((f, matched))
            if not hits:
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
            touched += 1

        dump(path, doc, style)
        stats["files"] += 1
        stats["suppliers_touched"] += touched
        stats["rows_added"] += added
        stats["rows_refreshed"] += refreshed
        print("%-28s %d supplier(s) given sourced frameworks, %d row(s) written "
              "(%d replaced from a previous run)" % (path, touched, added, refreshed))

    print("Done. Curated rows were never removed; only rows previously written by this "
          "script were replaced.")


if __name__ == "__main__":
    main()
