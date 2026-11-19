"""One-off: re-match the supplier spellings left in data/framework-lots.json's
`unresolved` against TODAY's seed aliases, without re-reading any source
(17/11/2026).

WHY. The lots themselves were already read from the notices and matrices and are
stored per framework; only the NAME MATCH failed, which is why the gate's
[framework-lots] WARN asks for an alias rather than a re-read. Find a Tender
returns 403 to scripted requests and the matrices are large blobs, so a full
scripts/refresh_framework_lots.py run is not available on demand — but it is not
needed: every unresolved entry carries the source spelling and the lots verbatim.

This re-runs refresh_framework_lots.attach_names() over exactly those stored
names, with the same matching rule and the same merge the writer's take() does
(lotsBySource, namedAs, supplierLots, suppliersWithoutLot, suppliersWithLots),
then re-attaches to data/frameworks.json with the writer's own attach(). It adds
no lot that was not already in the file and invents no name. Idempotent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refresh_framework_lots as R  # noqa: E402

LOTS = R.LOTS_PATH
FW = R.FW_PATH
SEED = "data/supplier-seed.json"


def main():
    seed = json.load(open(SEED, encoding="utf-8"))
    fwdoc = json.load(open(FW, encoding="utf-8"))
    lotsdoc = json.load(open(LOTS, encoding="utf-8"))
    to_company = R.resolver(seed)
    by_url = {}
    for f in (fwdoc.get("frameworks") or []) + (fwdoc.get("expired") or []):
        by_url[f.get("url")] = f
    moved = 0
    fw_fixed = 0
    for url, rec in (lotsdoc.get("frameworks") or {}).items():
        pend = [u for u in rec.get("unresolved") or [] if u.get("name")]
        if not pend:
            continue
        fw = by_url.get(url) or {}
        suppliers = fw.get("suppliers") or []
        lots = {b: set(v) for b, v in (rec.get("supplierLots") or {}).items()}
        still, gained = [], 0
        for kind in sorted({u.get("source") for u in pend}):
            retry = {u["name"]: set(u.get("lots") or []) for u in pend if u.get("source") == kind}
            spelled = {}
            got, unres = R.attach_names(retry, suppliers, to_company, spelled)
            for b, v in got.items():
                lots.setdefault(b, set()).update(v)
                mine = rec.setdefault("lotsBySource", {}).setdefault(kind, {}).setdefault(b, [])
                rec["lotsBySource"][kind][b] = sorted(set(mine) | set(v), key=R.lot_sort_key)
            for b, names in spelled.items():
                other = sorted(n for n in names if n != b)
                if other:
                    rec.setdefault("namedAs", {})[b] = sorted(
                        set((rec.get("namedAs") or {}).get(b) or []) | set(other))
            for u in unres:
                u["source"] = kind
            still.extend(unres)
            gained += len(got)
            moved += len(got)
        rec["unresolved"] = still + [u for u in rec.get("unresolved") or [] if not u.get("name")]
        if not gained:
            continue
        fw_fixed += 1
        for s in rec.get("sources") or []:
            if "suppliersWithLots" in s:
                s["suppliersWithLots"] = len((rec.get("lotsBySource") or {}).get(s.get("kind")) or {})
        rec["supplierLots"] = {b: sorted(v, key=R.lot_sort_key) for b, v in sorted(lots.items())}
        if rec["supplierLots"]:
            rec["status"] = "published"
        rec["suppliersWithoutLot"] = [s for s in suppliers if s not in rec["supplierLots"]] \
            if rec["status"] == "published" else []
        covered = sorted({l for src in rec.get("sources") or [] for l in src.get("coversLots") or []},
                         key=R.lot_sort_key)
        rec["coversLots"] = covered or None
        import re
        rec["lotsNotCovered"] = sorted(
            [k for k in (rec.get("lotTitles") or {})
             if not any(l == k or re.match(re.escape(k) + r"[.a-z]", l) for l in covered)],
            key=R.lot_sort_key) if rec["status"] == "published" else []
    lotsdoc["counts"] = {s: sum(1 for r in (lotsdoc.get("frameworks") or {}).values()
                                if r.get("status") == s) for s in R.STATUSES}
    with open(LOTS, "w", encoding="utf-8") as f:
        json.dump(lotsdoc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    R.attach(fwdoc, lotsdoc)
    with open(FW, "w", encoding="utf-8") as f:
        json.dump(fwdoc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    left = sum(1 for r in (lotsdoc.get("frameworks") or {}).values()
               if any(u.get("name") for u in r.get("unresolved") or []))
    print("matched %d source spellings across %d frameworks; %d frameworks still carry unresolved names"
          % (moved, fw_fixed, left))
    print("counts: %s" % lotsdoc["counts"])


if __name__ == "__main__":
    main()
