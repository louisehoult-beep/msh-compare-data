#!/usr/bin/env python3
"""
promote_index_to_compare.py — surface suppliers already held in the verified
supplier index (supplier-seed.json / supplier-index.json) into the Compare by
Speciality tab (data/compare-suppliers.json), for specialities where the tab
shows fewer companies than the index already holds against that speciality.

WHY: Lou noticed the Compare tab was showing far fewer suppliers per
speciality than the Hub actually has verified. This closes that gap using
data ALREADY held — no new research — per Lou's instruction 02/09/2026.

WHAT THIS DOES NOT DO: it does not fabricate brands, product types or NPC
codes for a promoted row. The existing hand-curated rows in this file carry
catalogue-level evidence (exact brands, pack codes) built by reading each
supplier's own NHS Supply Chain catalogue lines one at a time — that is real
research this script cannot replicate from the index alone. A promoted row
says plainly that this deeper evidence is not yet captured, carries no
product-type tag (an untagged claim about what it makes would be worse than
an honest gap), and links to the company's own site so a rep can check
themselves. This is Hub rule 8's "Not verified" pattern, not a shortcut round
it.

Safe by construction:
  * APPEND-ONLY — never edits or removes an existing supplier row, so no
    `iss` index (which points into the issues array BY POSITION) is disturbed.
  * `ref` is set from the exact resolution order verify.py's check_ref_present
    uses (supplier-seed.json first, then supplier-index.json), so a promoted
    row groups correctly in the company picker instead of becoming a second,
    orphaned entry the moment its name is spelled differently anywhere else.
  * Skips a candidate already present under any spelling verify.py's
    _norm_co() would consider the same company.
  * Every promoted row still satisfies verify.py's check_suppliers(): a
    non-empty `brands` string, an https `url`, `t` either empty or drawn from
    the speciality's own `types` map.

Usage:
    python3 scripts/promote_index_to_compare.py               # dry run, reports counts
    python3 scripts/promote_index_to_compare.py --write        # writes compare-suppliers.json
"""
import json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "scripts" else HERE
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import verify  # reuse the gate's own normalisation so this can never drift from it

DATA = os.path.join(ROOT, "data")


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def save(name, doc):
    p = os.path.join(DATA, name)
    with open(p, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")


def build_ref_universe():
    """norm(name-or-alias) -> canonical display name, seed first (wins ties)."""
    universe = {}
    for fn in ("supplier-seed.json", "supplier-index.json"):
        doc = load(fn)
        if not isinstance(doc, dict):
            continue
        for s in doc.get("suppliers") or []:
            if not isinstance(s, dict):
                continue
            nm = s.get("name")
            if not nm:
                continue
            for key in [nm] + list(s.get("aliases") or []):
                k = verify._norm_co(key)
                if k and k not in universe:
                    universe[k] = nm
    return universe


def own_site_url(index_row):
    """Prefer a link that is not the NHS Supply Chain catalogue/gov.uk."""
    for l in (index_row.get("links") or []):
        u = (l.get("url") or "") if isinstance(l, dict) else ""
        if not u.startswith("https://"):
            continue
        if "supplychain.nhs.uk" in u or "gov.uk" in u:
            continue
        return u
    # Fall back to whatever https link exists, so the row still satisfies
    # verify.py's HTTPS requirement — better an NHSSC catalogue link than none.
    for l in (index_row.get("links") or []):
        u = (l.get("url") or "") if isinstance(l, dict) else ""
        if u.startswith("https://"):
            return u
    return None


def framework_note(index_row, slug_label):
    """A short, honest note: which framework, when captured, and the gap this
    row deliberately leaves open."""
    fw = None
    for f in (index_row.get("frameworks") or []):
        name = (f.get("name") or "")
        if slug_label.split(" and ")[0].split(",")[0].lower()[:6] in name.lower():
            fw = f
            break
    if fw is None and (index_row.get("frameworks") or []):
        fw = index_row["frameworks"][0]
    if fw:
        cap = fw.get("capturedOn", "")
        return ("Named on the %s framework by NHS Supply Chain's own award brief%s. "
                "Not yet catalogue-verified for this speciality — no brand or NPC-level "
                "product line matched here yet; check the company's own site or The "
                "Differential." % (fw.get("name", "a related"), (" (captured %s)" % cap) if cap else ""))
    return ("Held in the Hub's verified supplier index against this speciality. Not yet "
            "catalogue-verified — no brand or NPC-level product line matched here yet; "
            "check the company's own site or The Differential.")


def brands_text(index_row):
    prods = [p.get("name") for p in (index_row.get("products") or []) if isinstance(p, dict) and p.get("name")]
    if prods:
        return " · ".join(sorted(set(prods))[:6])
    return "Not verified — brand-level detail not yet captured; see the supplier's own site."


def main():
    write = "--write" in sys.argv

    cs = load("compare-suppliers.json")
    lab = load("speciality-label-map.json")
    index = load("supplier-index.json")
    ref_universe = build_ref_universe()

    index_by_name = {s["name"]: s for s in index.get("suppliers", []) if isinstance(s, dict) and s.get("name")}

    # GLOBAL co-spelling already in the file, across every speciality — not just
    # the one being extended. verify.py's compare_internal_dupes check treats
    # any two spellings of the same company ANYWHERE in this file as an error,
    # so a promoted row must reuse a spelling already on the page rather than
    # introduce the index's own wording as a second variant.
    global_co_spelling = {}
    for blk0 in cs["specialities"].values():
        for row0 in (blk0.get("suppliers") or []):
            co0 = (row0.get("co") or "").strip()
            if co0:
                global_co_spelling.setdefault(verify._norm_co(co0), co0)

    # label -> slugs, from the same source used for the earlier gap analysis
    label_to_slugs = {}
    for e in lab.get("entries", []):
        for slug in (e.get("slugs") or []):
            label_to_slugs.setdefault(e["label"], []).append(slug)

    # slug -> set of index supplier names tagged with any label resolving to it
    slug_candidates = {}
    for name, row in index_by_name.items():
        for spec_label in (row.get("specialities") or []):
            for slug in label_to_slugs.get(spec_label, []):
                slug_candidates.setdefault(slug, set()).add(name)

    added_total = 0
    report = []

    for slug, candidate_names in slug_candidates.items():
        blk = cs["specialities"].get(slug)
        if not blk:
            continue  # a slug with no researched framework/types yet - not this script's job
        if blk.get("noSuppliers"):
            continue  # explicit declared absence (e.g. medicines) - do not override

        existing_norms = {verify._norm_co(s.get("co", "")) for s in (blk.get("suppliers") or [])}
        existing_norms |= {verify._norm_co(s.get("ref", "")) for s in (blk.get("suppliers") or []) if s.get("ref")}

        label = blk.get("label", slug)
        new_rows = []
        for name in sorted(candidate_names):
            n = verify._norm_co(name)
            if n in existing_norms:
                continue
            row = index_by_name[name]
            url = own_site_url(row)
            if not url:
                continue  # verify.py requires an https url; skip rather than fabricate one
            ref = ref_universe.get(n, name)
            co_spelling = global_co_spelling.get(n, name)
            global_co_spelling.setdefault(n, co_spelling)
            new_rows.append({
                "co": co_spelling,
                "ref": ref,
                "brands": brands_text(row),
                "t": [],
                "url": url,
                "note": framework_note(row, label),
                "iss": [],
            })
            existing_norms.add(n)

        if new_rows:
            report.append((slug, label, len(blk.get("suppliers") or []), len(new_rows)))
            added_total += len(new_rows)
            if write:
                blk["suppliers"].extend(new_rows)
                if "More companies from the Hub's verified supplier index" not in (blk.get("routeNote") or ""):
                    blk["routeNote"] = (blk.get("routeNote", "") + (" " if blk.get("routeNote") else "") +
                        "More companies from the Hub's verified supplier index are listed below "
                        "without catalogue-level product detail yet (marked as such in their row) "
                        "— added 02/09/2026 from the index the Hub already held, not fresh research.")

    for slug, label, before, added in sorted(report, key=lambda r: -r[3]):
        print("%-15s %-45s %3d -> %3d  (+%d)" % (slug, label, before, before + added, added))
    print()
    print("TOTAL new rows: %d across %d specialities%s" % (added_total, len(report), "" if write else " (dry run — pass --write to apply)"))

    if write and added_total:
        save("compare-suppliers.json", cs)
        print("Wrote data/compare-suppliers.json")


if __name__ == "__main__":
    main()
