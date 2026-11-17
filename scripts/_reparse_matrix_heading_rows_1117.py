"""One-off: re-read the product matrices already recorded in
data/framework-lots.json, now that parse_matrix_sections() no longer discards a
lot heading row's own data cells (17/11/2026).

WHY. On a section-shaped matrix NHS Supply Chain often writes the first product
of a lot on the SAME row as the lot heading:

    Lot 2 – Spinal and Neurological Robots | | | Mazor X System | | | ROSA Brain

parse_matrix_sections() used to `continue` on any heading row with three or
fewer non-empty cells, so those cells were dropped — not quarantined in
`unresolved`, just gone. On Robotic Medical Equipment and Associated Accessories
(matrix of 9 September 2026) that silently lost Zimmer Biomet UK Limited's only
mark (ROSA Brain, Lot 2) and MCT Lifesciences Ltd's only mark (ROBOFLEX
AVICENNA, Lot 3); Medtronic and Procept survived only because each had a second
product on the row below the heading. A heading row with four or more values was
already read, so the parser disagreed with itself about one shape of row.

The parser is fixed. This re-reads the 17 matrices the file already cites and
merges what the fix recovers, with the same per-sheet acceptance gate, the same
reconcile_lot() and the same merge the writer's own take() does. It re-reads
nothing else: briefs, award notices and every other source are left exactly as
captured, so the diff is this fix's effect and nothing else. Idempotent — a
second run finds nothing to add.

Measured before writing: across all 17 matrices the fix changes exactly two
things, both on Robotic Medical Equipment, both verified against the sheet.

USAGE
    python3 scripts/_reparse_matrix_heading_rows_1117.py --cache DIR [--dry-run]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refresh_framework_lots as R  # noqa: E402


def write(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")


def main(argv):
    cache = None
    if "--cache" in argv:
        cache = argv[argv.index("--cache") + 1]
    dry = "--dry-run" in argv
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    seed = json.load(open("data/supplier-seed.json", encoding="utf-8"))
    fwdoc = json.load(open(R.FW_PATH, encoding="utf-8"))
    lotsdoc = json.load(open(R.LOTS_PATH, encoding="utf-8"))
    to_company = R.resolver(seed)
    by_url = {f.get("url"): f
              for f in (fwdoc.get("frameworks") or []) + (fwdoc.get("expired") or [])}

    added, fw_touched, new_unres = 0, 0, 0
    for url, rec in (lotsdoc.get("frameworks") or {}).items():
        msrc = [s for s in rec.get("sources") or [] if s.get("kind") == "matrix"]
        if not msrc:
            continue
        suppliers = (by_url.get(url) or {}).get("suppliers") or []
        for s in msrc:
            try:
                sheets = R.parse_matrix(R.fetch(s["url"], cache, binary=True))
            except Exception as exc:
                print("  could not read %s (%s) — left as captured" % (s["url"], exc))
                continue
            src = {}
            for title, shape, m in sheets:
                if shape == "matrix-lot-rows":
                    m = {k: {x for x in (R.reconcile_lot(x, rec.get("lotTitles") or {}) for x in v)
                             if x} for k, v in m.items()}
                _, unres = R.attach_names(m, suppliers, to_company)
                resolved = len(m) - len(unres)
                if resolved >= 2 and resolved / float(len(m)) >= R.MIN_RESOLVED_SHARE:
                    for k, v in m.items():
                        src.setdefault(k, set()).update(v)
            if not src:
                continue

            held = {b: set(v) for b, v in (rec.get("lotsBySource") or {}).get("matrix", {}).items()}
            spelled = {}
            got, unres = R.attach_names(src, suppliers, to_company, spelled)
            gained = {b: sorted(v - held.get(b, set()), key=R.lot_sort_key)
                      for b, v in ((b, set(v)) for b, v in got.items())}
            gained = {b: v for b, v in gained.items() if v}

            # Names the matrix carries that no brief row can hold. They belong in
            # `unresolved` with their lots, not nowhere: the gate counts them and
            # the reason says which of the three real causes it is.
            keep = [u for u in rec.get("unresolved") or []
                    if not (u.get("source") == "matrix" and u.get("name"))]
            fresh = []
            for u in unres:
                u["source"] = "matrix"
                fresh.append(u)
            before = len([u for u in rec.get("unresolved") or []
                          if u.get("source") == "matrix" and u.get("name")])
            if not gained and len(fresh) == before:
                continue
            fw_touched += 1
            new_unres += max(0, len(fresh) - before)
            rec["unresolved"] = keep + fresh
            for b, names in spelled.items():
                other = sorted(n for n in names if n != b)
                if other:
                    rec.setdefault("namedAs", {})[b] = sorted(
                        set((rec.get("namedAs") or {}).get(b) or []) | set(other))
            lots = {b: set(v) for b, v in (rec.get("supplierLots") or {}).items()}
            for b, v in got.items():
                lots.setdefault(b, set()).update(v)
                cur = set((rec.setdefault("lotsBySource", {}).setdefault("matrix", {})).get(b) or [])
                rec["lotsBySource"]["matrix"][b] = sorted(cur | set(v), key=R.lot_sort_key)
                added += len(gained.get(b) or [])
            rec["supplierLots"] = {b: sorted(v, key=R.lot_sort_key) for b, v in sorted(lots.items())}
            s["suppliersWithLots"] = len(rec["lotsBySource"]["matrix"])
            s["coversLots"] = sorted({l for v in src.values() for l in v}, key=R.lot_sort_key)
            if rec["supplierLots"]:
                rec["status"] = "published"
            rec["suppliersWithoutLot"] = [x for x in suppliers if x not in rec["supplierLots"]] \
                if rec["status"] == "published" else []
            covered = sorted({l for q in rec.get("sources") or [] for l in q.get("coversLots") or []},
                             key=R.lot_sort_key)
            rec["coversLots"] = covered or None
            rec["lotsNotCovered"] = sorted(
                [k for k in (rec.get("lotTitles") or {})
                 if not any(l == k or re.match(re.escape(k) + r"[.a-z]", l) for l in covered)],
                key=R.lot_sort_key) if rec["status"] == "published" else []
            for b, v in gained.items():
                print("  + %-45s %-40s %s" % (rec["name"][:45], b[:40], v))

    lotsdoc["counts"] = {st: sum(1 for r in (lotsdoc.get("frameworks") or {}).values()
                                 if r.get("status") == st) for st in R.STATUSES}
    if dry:
        print("--dry-run: nothing written. %d lot(s) recovered across %d framework(s); "
              "%d matrix name(s) newly quarantined." % (added, fw_touched, new_unres))
        return 0
    write(R.LOTS_PATH, lotsdoc)
    R.attach(fwdoc, lotsdoc)
    write(R.FW_PATH, fwdoc)
    print("%d lot(s) recovered across %d framework(s); %d matrix name(s) newly quarantined. "
          "counts: %s" % (added, fw_touched, new_unres, lotsdoc["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
