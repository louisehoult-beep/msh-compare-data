#!/usr/bin/env python3
"""Build the per-speciality slice that feeds the two new tabs on a speciality page.

WHY THIS EXISTS. Until 07/09/2026 the "Suppliers, frameworks & related" tab on every
speciality page was three links out — Supplier Directory, Framework Hub, Compare tab —
and a list of neighbouring specialities. A rep on the wound care page got no wound care
frameworks, no wound care suppliers, no wound care tenders. Lou's instruction, 07/09/2026:
the sections have to be FILTERED to the speciality, and suppliers get their own tab.

WHAT IT PRODUCES. data/speciality-panels/<slug>.json — one small file per speciality,
holding only that speciality's slice of frameworks, suppliers, awards, tenders and the
Drug Tariff. Small on purpose: the page must not pull 13MB of Drug Tariff or 6MB of
supplier index to render a panel.

THE EVIDENCE FLOOR (root rule 14). A speciality with no rule in SPECIALITY_RULES gets
NO panel — it is written with `defined: false` and the renderer shows an honest empty
state. It never falls back to a loose keyword guess, because that is exactly what the
existing tender-history `spec` field does and it is wrong more often than it is right:
of the 16 rows it tags tissue-viability-and-wound-care, 10 are false positives matched
on "tissue", "viability", "pressure" or "compression" — Kew Gardens' seed viability
X-ray cabinet, donated corneal eye tissue, Paper Hygiene and Toilet Tissue, a chest
compression system, a high pressure test rig. None of those may reach a paying member.

Every rule this script applies is written into the file it produces, so a reader can
judge the filter for themselves (rule 14a). test_speciality_panels.py holds the
invariants that fail if the matching breaks (rule 14b).

USAGE
  python3 scripts/build_speciality_panels.py                     # every defined speciality
  python3 scripts/build_speciality_panels.py tissue-viability-and-wound-care
"""
import json
import os
import re
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "speciality-panels")

# ONE NAME PER COMPANY (company-aliases/README.md). NHS Supply Chain spells the same
# firm differently on two of its own framework pages: "Molnlycke Health Care Ltd" on
# Advanced Wound Care and "Molnlycke Healthcare" on Pressure Area Care; "ConvaTec
# Limited" and "ConvaTec Ltd"; "KCI Medical Ltd" and "KCI Medical Limited", which are
# both Solventum now. Published raw, that is one supplier looking like two and a count
# inflated by 15. Every name goes through the registry before it reaches a member.
sys.path.insert(0, os.path.join(ROOT, "company-aliases"))
import company_alias  # noqa: E402

# How many rows of each rolling feed a panel carries. The page shows the most recent
# and links out for the rest; an unbounded list would put a 2021 award at the top of
# a rep's screen on the strength of nothing.
AWARD_CAP = 40


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# THE RULES. One entry per speciality. Absent means no panel, never a guess.
#
# frameworks : matched against the NHSSC framework NAME. NHSSC names its own
#              frameworks after the clinical category, so the name is the honest
#              key; the CBU `category` field is far too broad (39 frameworks sit
#              under "Medical and Surgical Consumables" alone).
# include    : the award/tender title must match this.
# exclude    : ...and must not match this. Every pattern here was put in because a
#              real row in tender-history.json matched `include` and was wrong.
# cpv        : CPV code prefixes used for award feeds that carry classification.
# tariffParts: Drug Tariff Part IX parts that belong to this speciality.
# ---------------------------------------------------------------------------
SPECIALITY_RULES = {
    "tissue-viability-and-wound-care": {
        "label": "Tissue Viability and Wound Care",
        "frameworks": r"\b(wound|dressing|npwt|negative[- ]pressure|pressure area care)\b",
        "include": (
            r"\b(wound|woundcare|dressing|dressings|npwt|negative[- ]pressure wound|"
            r"tissue viability|pressure ulcer|pressure sore|pressure relieving|"
            r"pressure area care|debridement|larval therapy|"
            r"compression (?:bandag|hosiery|garment|therapy|stocking)|lymphoedema|"
            r"bandag(?:e|ing)|skin integrity|wound closure|suture|leg ulcer|"
            r"diabetic foot|venous ulcer|honey dressing|silver dressing|"
            r"foam dressing|hydrocolloid|alginate)\b"
        ),
        "exclude": (
            r"\b(seed viability|eye tissue|corneal|toilet tissue|paper hygiene|"
            r"facial tissue|chest compression|test rig|laminar flow|pressure infus|"
            r"blood pressure|pressure washer|tissue culture|breast tissue|"
            r"soft tissue (?:sarcoma|imaging))\b"
        ),
        # 33141110 dressings and the 3314111x family that hangs off it.
        "cpv": ("3314111",),
        # IXA is dressings and elastic hosiery — the compression and lymphoedema
        # range sits here, which is why Juzo and Sigvaris dominate the line count.
        "tariffParts": ("IXA",),
    },
}


def compile_rule(rule):
    return {
        "fw": re.compile(rule["frameworks"], re.I),
        "inc": re.compile(rule["include"], re.I),
        "exc": re.compile(rule["exclude"], re.I),
    }


def match_title(rx, title):
    t = title or ""
    return bool(rx["inc"].search(t)) and not rx["exc"].search(t)


def build_frameworks(rx, fw_doc):
    """The speciality's NHSSC frameworks, with the supplier list each one carries."""
    out = []
    for f in fw_doc["frameworks"]:
        if not rx["fw"].search(f.get("name") or ""):
            continue
        out.append({
            "name": f.get("name"),
            "url": f.get("url"),
            "reference": f.get("reference"),
            "category": f.get("category"),
            "supplyRoute": f.get("supplyRoute"),
            "starts": f.get("starts"),
            "ends": f.get("ends"),
            "supplierCount": f.get("supplierCount"),
            "supplierSource": f.get("supplierSource"),
            "suppliers": [s for s in (f.get("suppliers") or []) if isinstance(s, str)],
            "delisted": f.get("delisted"),
        })
    out.sort(key=lambda x: (x.get("name") or ""))
    return out


def build_suppliers(frameworks, registry):
    """Every named supplier on the speciality's own frameworks, and which ones.

    This is the speciality's supplier list as the procurement record states it:
    not a redirect to the whole directory, and not a keyword guess against the
    free-text speciality strings, which were never one vocabulary.

    Names are resolved through company-aliases first. A name the registry cannot
    resolve is kept exactly as NHS Supply Chain wrote it and flagged, never dropped
    and never quietly merged into something that looks close.
    """
    by_key = {}
    for f in frameworks:
        for s in f["suppliers"]:
            status, canonical, _how = company_alias.resolve(s, registry)
            resolved = status == "RESOLVED"
            key = canonical if resolved else s
            rec = by_key.setdefault(key, {
                "name": key, "resolved": resolved, "variants": [], "frameworks": [],
            })
            if s not in rec["variants"]:
                rec["variants"].append(s)
            if f["name"] not in rec["frameworks"]:
                rec["frameworks"].append(f["name"])
    for rec in by_key.values():
        rec["variants"].sort()
        # Only worth showing when NHSSC really did write it two ways.
        if rec["variants"] == [rec["name"]]:
            rec["variants"] = []
    out = list(by_key.values())
    # Most frameworks first: a supplier on three of the speciality's frameworks is
    # a bigger name on this patch than one on a single lot, and that ordering is
    # the only claim being made — it is a count, not a ranking of importance.
    out.sort(key=lambda x: (-len(x["frameworks"]), x["name"].lower()))
    return out


def build_awards(rx, rule, th_doc, fa_doc):
    """Awarded contracts on this patch, from the two award feeds."""
    rows = []
    schema = th_doc["schema"]
    ix = {k: i for i, k in enumerate(schema)}
    for r in th_doc["rows"]:
        title = r[ix["t"]]
        if not match_title(rx, title):
            continue
        rows.append({
            "title": title,
            "buyer": r[ix["b"]],
            "supplier": r[ix["sup"]],
            "date": r[ix["d"]],
            "url": r[ix["u"]],
            "value": r[ix["v"]],
            "periodEnd": r[ix["pe"]],
            "source": "tender-history",
        })
    # CPV CORROBORATES, IT NEVER ADMITS. A CPV code on a notice carrying a basket of
    # them says what family the buyer filed it under, not what is being bought:
    # "Newborn Transport Harnesses for London Ambulance" carries 33141116, the dressing
    # packs code, alongside three others. Accepting on CPV alone put that on the wound
    # care page. The title has to match; the CPV is recorded so a reader can see the
    # classification agreed.
    cpv_prefixes = tuple(rule.get("cpv") or ())
    for a in fa_doc["awards"]:
        cpvs = [str(c) for c in (a.get("cpv") or [])]
        if not match_title(rx, a.get("title")):
            continue
        by_cpv = bool(cpv_prefixes) and any(c.startswith(cpv_prefixes) for c in cpvs)
        buyer = a.get("buyer")
        if isinstance(buyer, dict):
            buyer = buyer.get("name")
        rows.append({
            "title": a.get("title"),
            "buyer": buyer,
            "supplier": ", ".join(
                (s.get("name") if isinstance(s, dict) else str(s))
                for s in (a.get("suppliers") or [])
            ) or None,
            "date": a.get("published"),
            "url": a.get("url"),
            "value": None,
            "periodEnd": None,
            "cpv": cpvs,
            "isFramework": a.get("is_framework"),
            "source": "framework-awards",
            "cpvCorroborates": by_cpv,
        })
    # De-duplicate on the notice URL: the two feeds overlap at the recent end.
    seen, uniq = set(), []
    for r in sorted(rows, key=lambda x: (x.get("date") or ""), reverse=True):
        k = r.get("url") or (r.get("title"), r.get("date"))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq[:AWARD_CAP], len(uniq)


def build_open_tenders(rx, slug, ot_doc):
    """Notices still open for bidding. Usually empty for a given speciality, and an
    empty list is the correct answer — never padded out with near-misses."""
    out = []
    for n in ot_doc["notices"]:
        if n.get("speciality") == slug or match_title(rx, n.get("title")):
            out.append({
                "title": n.get("title"),
                "buyer": n.get("buyer"),
                "status": n.get("status"),
                "stage": n.get("stage"),
                "closingDate": n.get("closingDate"),
                "url": n.get("url"),
                "value": n.get("valueAmount"),
                "source": n.get("source"),
            })
    return out


def build_tariff(rule, dt_doc):
    """Drug Tariff Part IX for this speciality — the reimbursement list a prescribing
    conversation actually turns on. Summarised, never shipped whole: Part IXA alone is
    56,833 lines and no panel can carry that."""
    parts = tuple(rule.get("tariffParts") or ())
    if not parts:
        return None
    ix = {k: i for i, k in enumerate(dt_doc["schema"])}
    rows = [r for r in dt_doc["rows"] if r[ix["part"]] in parts]
    if not rows:
        return None
    by_sup = {}
    prices = []
    for r in rows:
        by_sup[r[ix["supplier"]]] = by_sup.get(r[ix["supplier"]], 0) + 1
        try:
            prices.append(float(r[ix["price"]]))
        except (TypeError, ValueError):
            pass
    top = sorted(by_sup.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    return {
        "parts": list(parts),
        "effectiveMonth": dt_doc.get("effectiveMonth"),
        "dataAsOf": dt_doc.get("dataAsOf"),
        "sourcePage": dt_doc.get("sourcePage"),
        "lineCount": len(rows),
        "supplierCount": len(by_sup),
        "topSuppliers": [{"name": n, "lines": c} for n, c in top],
        "priceMin": round(min(prices), 2) if prices else None,
        "priceMax": round(max(prices), 2) if prices else None,
    }


def build(slug, sources):
    rule = SPECIALITY_RULES.get(slug)
    generated = datetime.date.today().isoformat()
    if not rule:
        return {
            "_notice": sources["notice"],
            "slug": slug,
            "defined": False,
            "generated": generated,
            "whyEmpty": (
                "No speciality rule has been written for this page yet. The panel shows "
                "nothing rather than guessing: a keyword match on the title alone is "
                "wrong more often than it is right on this data."
            ),
        }

    rx = compile_rule(rule)
    fw_doc, th_doc = sources["frameworks"], sources["tender_history"]
    fa_doc, ot_doc, dt_doc = sources["framework_awards"], sources["open_tenders"], sources["drug_tariff"]

    frameworks = build_frameworks(rx, fw_doc)
    suppliers = build_suppliers(frameworks, sources["registry"])
    awards, award_total = build_awards(rx, rule, th_doc, fa_doc)
    open_tenders = build_open_tenders(rx, slug, ot_doc)
    tariff = build_tariff(rule, dt_doc)

    return {
        "_notice": sources["notice"],
        "slug": slug,
        "label": rule["label"],
        "defined": True,
        "generated": generated,
        "dataAsOf": {
            "frameworks": fw_doc.get("dataAsOf"),
            "tenderHistory": th_doc.get("dataAsOf"),
            "frameworkAwards": fa_doc.get("generated"),
            "openTenders": ot_doc.get("dataAsOf"),
            "drugTariff": dt_doc.get("dataAsOf"),
        },
        "rules": {
            "frameworks": (
                "NHS Supply Chain framework names matching /%s/i. NHSSC names a framework "
                "after its clinical category, so the name is the key; the CBU category "
                "field is far too broad to filter on." % rule["frameworks"]
            ),
            "suppliers": (
                "Every supplier NHS Supply Chain names on the frameworks above, resolved to one "
                "name per company through the Hub's alias registry, and ordered by how many of "
                "this speciality's frameworks they appear on. That count is the only claim made. "
                "It is not a ranking of size or share. Where NHS Supply Chain spelled a company "
                "two ways across its own pages, both spellings are shown against the one entry."
            ),
            "awards": (
                "Award-stage notices whose TITLE matches /%s/i and does not match /%s/i. The "
                "exclusion list exists because every pattern in it matched a real notice that "
                "was not this speciality. A CPV code beginning %s is recorded as corroboration "
                "where the feed carries one, but never admits a notice on its own: a notice "
                "carrying a basket of CPV codes is filed under all of them and bought under "
                "one. Buyer names are never matched on." % (
                    rule["include"], rule["exclude"], " or ".join(rule.get("cpv") or ()) or "n/a")
            ),
            "openTenders": (
                "Notices still open for bidding, matched the same way. An empty list means no "
                "open notice on this patch today, not that none was looked for."
            ),
            "drugTariff": (
                "NHSBSA Drug Tariff Part %s for the stated effective month, summarised. Prices "
                "are the reimbursement price at publication, not necessarily today's."
                % "/".join(rule.get("tariffParts") or ())
            ),
        },
        "counts": {
            "frameworks": len(frameworks),
            "suppliers": len(suppliers),
            "suppliersUnresolved": sum(1 for s in suppliers if not s["resolved"]),
            "awardsShown": len(awards),
            "awardsMatched": award_total,
            "openTenders": len(open_tenders),
        },
        "frameworks": frameworks,
        "suppliers": suppliers,
        "awards": awards,
        "openTenders": open_tenders,
        "drugTariff": tariff,
    }


def main():
    sources = {
        "frameworks": load("frameworks.json"),
        "tender_history": load("tender-history.json"),
        "framework_awards": load("framework-awards.json"),
        "open_tenders": load("open-tenders.json"),
        "drug_tariff": load("drug-tariff-part-ix.json"),
    }
    # The licence and database-right wording is the house notice, carried verbatim.
    # The `ref` is NOT: a marker ref identifies one file, and reusing another file's
    # would defeat the traceability it exists for. stamp_notice.py only walks
    # data/*.json, so nothing mints one for a file in a subdirectory yet. Say so in
    # the file rather than shipping a borrowed marker.
    notice = dict(sources["open_tenders"]["_notice"])
    notice.pop("ref", None)
    notice["markerRef"] = ("Not yet minted. This file sits in data/speciality-panels/ and "
                           "scripts/stamp_notice.py walks only data/*.json.")
    sources["notice"] = notice
    sources["registry"] = company_alias.load_registry()

    slugs = sys.argv[1:] or sorted(SPECIALITY_RULES)
    os.makedirs(OUT, exist_ok=True)
    for slug in slugs:
        doc = build(slug, sources)
        path = os.path.join(OUT, slug + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
        c = doc.get("counts") or {}
        print("%-38s frameworks=%s suppliers=%s awards=%s/%s open=%s tariff=%s  (%d KB)" % (
            slug, c.get("frameworks"), c.get("suppliers"), c.get("awardsShown"),
            c.get("awardsMatched"), c.get("openTenders"),
            (doc.get("drugTariff") or {}).get("lineCount") if doc.get("drugTariff") else "-",
            os.path.getsize(path) // 1024))


if __name__ == "__main__":
    main()
