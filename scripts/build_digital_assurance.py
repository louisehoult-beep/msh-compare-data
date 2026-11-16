#!/usr/bin/env python3
"""Digital supplier assurance — the page data for /medical-sales-hub/digital-assurance/.

WHAT THIS IS, AND WHY IT IS NOT A "SUSPENDED LINES" LIST
  The physical Hub has NHS Supply Chain suspended catalogue lines with a named
  alternative beside each one. There is no digital equivalent, because a digital
  product is bought through a framework lot under an assurance regime, not as a
  stock code, and nothing publishes "this software SKU is suspended".

  What CAN be said, from data this repo already holds, is the same SHAPE:
      a thing a trust's information governance team can block a purchase on
    + who in the same area is current
    + the question the member can ask without making a claim.

  So this file is built, not scraped. It joins three existing files and computes
  nothing that is not a direct reading of them:

    data/dspt-supplier-check.json  the Data Security and Protection Toolkit
                                   (DSPT) status per digital supplier, exact
                                   name match only (see refresh_dspt_suppliers.py)
    data/supplier-seed.json        each supplier's specialities, for the lane and
                                   the sub-area
    data/digital-frameworks.json   the routes to market and when each closes

THE TOOLKIT-YEAR RULE, STATED HERE AND PRINTED ON THE PAGE
  The DSPT year rolls in June. On a November reading the open year is 2026-27
  (version 9) and most organisations have not yet needed to publish against it,
  so their most recent published submission is 2025-26 (version 8). Both are
  therefore CURRENT. An organisation whose most recent publication is 2024-25
  (version 7) or older has let a whole cycle pass: that is BEHIND.

  The cut is held in CURRENT_FROM_YEAR, not hardcoded in a comparison, so the
  rule can be re-read and challenged. It is printed on the page verbatim.

WHAT THIS DELIBERATELY DOES NOT DO
  * It does not call a behind-the-year supplier unsafe, non-compliant or
    suspended. DSPT status is self-assessed and self-submitted. The page says
    only what DSPT published and on what date.
  * It does not resolve an AMBIGUOUS supplier. Where one supplier's names reach
    more than one DSPT organisation (Change Healthcare reaches two, one current
    and one from 2022-23), refresh_dspt_suppliers.py claims no status and so
    does this: it is reported as its own category, never counted as behind.
  * It does not treat UNMATCHED as a failing. 50 digital suppliers have no exact
    DSPT name match. That is a finding to ask about, not a status, and the page
    says so in those words.
  * It invents no alternative. Where a sub-area has no other tracked supplier
    with a current DSPT record, the row says so rather than reaching for a
    supplier from somewhere else.

    python3 scripts/build_digital_assurance.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DSPT = os.path.join(DATA, "dspt-supplier-check.json")
SEED = os.path.join(DATA, "supplier-seed.json")
FRAMEWORKS = os.path.join(DATA, "digital-frameworks.json")
OUT = os.path.join(DATA, "digital-assurance.json")

# A published submission for this toolkit year or later is current. See the
# module docstring: the year rolls in June, so on a November reading the
# previous year's version is still the most recent one most organisations have
# had to publish.
CURRENT_FROM_YEAR = 2025

YEAR_RULE = (
    "The Data Security and Protection Toolkit (DSPT) year rolls in June, so in the autumn "
    "most organisations' most recent published submission is still the previous year's. "
    "A supplier is read as CURRENT here when its published submission is %d-%s (version 8) "
    "or later, and BEHIND when it is %d-%s (version 7) or older, which means a whole "
    "cycle has passed without a publication. A supplier reading \"Not Published\" has a DSPT "
    "record with no published submission against it."
) % (CURRENT_FROM_YEAR, str(CURRENT_FROM_YEAR + 1)[2:],
     CURRENT_FROM_YEAR - 1, str(CURRENT_FROM_YEAR)[2:])

CLAIM_RULE = (
    "DSPT status is self-assessed and self-submitted by the organisation, and this page "
    "reports only what DSPT had published on the date it was read. Nothing here says a "
    "supplier is unsafe, non-compliant or barred, and nothing here is an endorsement of a "
    "supplier that is current. It is a published fact you can raise, not a claim you make."
)

MATCH_RULE = (
    "Matching is an exact match on the normalised company name, tried against the supplier's "
    "own name and the curated alternative names held for it. There is no fuzzy matching, "
    "because a wrong match would put another company's assurance status on a supplier. "
    "Where a supplier's names reach more than one DSPT organisation it claims no status and "
    "is listed as ambiguous; where no name matches it is listed as unmatched."
)

UNMATCHED_RULE = (
    "No exact DSPT name match was found for these suppliers. That is not a failing and not a "
    "status: a supplier can be assured under a parent company's registered name, under a name "
    "spelled differently from the one it trades as, or be outside the scope of the toolkit "
    "altogether. It is a reasonable thing to ask about, and an unreasonable thing to assert."
)

# ABBREVIATIONS IN THE AREA LABELS (rule 12: spelled out on first use, the
# abbreviation after it in brackets).
#
# The labels come from data/supplier-seed.json, which tags a supplier with the
# short form a rep uses. A member reading "Virtual wards / RPM" with nothing
# beside it is exactly what rule 12 exists to stop, and the seed cannot be
# rewritten from here without changing every other page that reads it. So the
# expansion is applied at the point the label is printed, and each one is read
# off a captured NHS source already held in this repo rather than from memory
# (rule 8): the wording below is the wording the NHS body itself used.
#
#   EPR  data/atamis-opportunities.json, Norfolk and Waveney University Hospital
#        Group pre-market engagement: "a single Electronic Patient Record (EPR)
#        across the three acute Trusts"
#   RPM  data/company-awards.json award title "Provision of Remote Patient
#        Monitoring", and data/atamis-opportunities.json "Remote patient
#        monitoring and alert solution"
#   AI   data/digital-lane.json notice title "Post-Deployment Monitoring of
#        Diagnostic Imaging Artificial Intelligence (AI) in the NHS"
#
# Anything not in this map is printed as the seed spells it. A guessed
# expansion is worse than none.
EXPANSIONS = {
    "AI": "artificial intelligence",
    "EPR": "electronic patient record",
    "RPM": "remote patient monitoring",
}

ABBR_RE = re.compile(r"\b(" + "|".join(sorted(EXPANSIONS, key=len, reverse=True)) + r")\b")


def spell_out(label):
    """"Virtual wards / RPM" -> "Virtual wards / remote patient monitoring (RPM)".

    A label that is nothing but the abbreviation ("EPR") becomes "Electronic
    patient record (EPR)", capitalised, because it starts the line.
    """
    def sub(m):
        a = m.group(1)
        return "%s (%s)" % (EXPANSIONS[a], a)
    out = ABBR_RE.sub(sub, label)
    if out and out[0].islower():
        out = out[0].upper() + out[1:]
    return out


YEAR_RE = re.compile(r"^(\d{4})-(\d{2}) \(version (\d+)\)\s*-\s*(.+)$")


def norm(name):
    t = name.lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_status(text):
    """('2025-26 (version 8) - Standards met') -> (2025, '2025-26', 8, 'Standards met')."""
    m = YEAR_RE.match(text or "")
    if not m:
        return None, None, None, None
    return int(m.group(1)), m.group(1) + "-" + m.group(2), int(m.group(3)), m.group(4)


def framework_index(frameworks):
    """Normalised supplier name -> [{framework name, ends, successor}] it appears on."""
    idx = {}
    for fw in frameworks:
        names = set(fw.get("suppliers") or [])
        for lot in (fw.get("lots") or []):
            names |= set(lot.get("suppliers") or [])
        entry = {
            "name": fw.get("name"),
            "reference": fw.get("reference"),
            "ends": fw.get("ends"),
            "url": fw.get("url"),
        }
        for n in names:
            idx.setdefault(norm(n), []).append(entry)
    return idx


def successors(frameworks):
    """A framework that ends, and the tracked agreement that starts to replace it.

    Named ONLY where one framework's own name carries the other's, which is how
    Technology Enabled Care Services 2 and 3 relate. Nothing is inferred from
    dates or subject matter: two agreements that happen to overlap are not a
    succession, and claiming one would send a member to the wrong route.

    The succession is DIRECTIONAL. An earlier edition is never the successor of
    a later one, so the candidate must both start after this framework starts
    and run past the date this one ends. Without that second test the pair is
    symmetrical and each names the other, which on 16/11/2026 printed
    "Technology Enabled Care Services 2" as the thing to move on to when
    Technology Enabled Care Services 3 closes - i.e. backwards, to an agreement
    that had already expired.
    """
    out = {}
    for fw in frameworks:
        if not fw.get("ends") or not fw.get("starts"):
            continue
        base = re.sub(r"\s*\d+\s*$", "", (fw.get("name") or "").split("(")[0]).strip()
        if not base:
            continue
        for other in frameworks:
            if other is fw or not other.get("starts") or not other.get("ends"):
                continue
            oname = other.get("name") or ""
            if (oname.startswith(base) and oname != fw.get("name")
                    and other["starts"] > fw["starts"]
                    and other["ends"] > fw["ends"]
                    and other["starts"] <= fw["ends"]):
                out[fw["name"]] = {"name": oname, "reference": other.get("reference"),
                                   "starts": other.get("starts"), "url": other.get("url")}
    return out


def question_for(kind, name, area):
    """The question the member asks. Phrased so the BUYER raises the issue.

    Never "tell them X is behind". The member asks what the trust's own process
    requires; the trust's information governance team finds the answer itself.
    """
    if kind == "behind":
        # The area is printed as the seed spells it, never lower-cased: doing so
        # turned "Breast screening AI" into "breast screening ai" on 16/11/2026.
        return ("Ask the information governance lead what the trust requires of a supplier's "
                "Data Security and Protection Toolkit (DSPT) publication before a purchase in "
                "%s goes through, and whether a submission older than the last toolkit year is "
                "accepted." % (area if area else "digital and medical IT"))
    if kind == "notPublished":
        return ("Ask whether the trust's process accepts a supplier that holds a Data Security "
                "and Protection Toolkit (DSPT) registration with no published submission "
                "against it, or whether a published submission is required.")
    if kind == "ambiguous":
        return ("Ask which registered legal entity would be named on the contract, because this "
                "supplier's names reach more than one Data Security and Protection Toolkit "
                "(DSPT) record and the records do not say the same thing.")
    return ("Ask how the trust satisfies itself on information governance for a supplier it "
            "cannot find in the Data Security and Protection Toolkit (DSPT).")


def build():
    dspt = load(DSPT)
    seed = load(SEED)
    fw_doc = load(FRAMEWORKS)
    frameworks = fw_doc.get("frameworks") or []

    by_name = {s["name"]: s for s in seed["suppliers"]}
    fidx = framework_index(frameworks)
    succ = successors(frameworks)

    def routes(supplier_name):
        s = by_name.get(supplier_name) or {}
        keys = {norm(supplier_name)} | {norm(a) for a in (s.get("aliases") or [])}
        seen, out = set(), []
        for k in keys:
            for e in fidx.get(k, []):
                if e["name"] in seen:
                    continue
                seen.add(e["name"])
                row = dict(e)
                row["successor"] = succ.get(e["name"])
                out.append(row)
        return sorted(out, key=lambda r: (r["ends"] or "9999", r["name"]))

    def areas(supplier_name):
        """The sub-area, i.e. the specialities that are not the digital lane label itself."""
        sp = (by_name.get(supplier_name) or {}).get("specialities") or []
        return [spell_out(l) for l in sp if "Digital" not in l]

    rows, current_by_speciality = [], {}
    for s in dspt["suppliers"]:
        year, label, version, outcome = parse_status(s.get("dsptStatus"))
        if s.get("ambiguous"):
            kind = "ambiguous"
        elif year is None:
            kind = "notPublished" if (s.get("dsptStatus") or "").strip() else "noStatus"
        elif year >= CURRENT_FROM_YEAR:
            kind = "current"
        else:
            kind = "behind"
        row = {
            "name": s["name"],
            "kind": kind,
            "dsptStatus": s.get("dsptStatus") or None,
            "yearLabel": label,
            "version": version,
            "outcome": outcome,
            "statusDate": s.get("statusDate") or None,
            "matchedOn": s.get("matchedOn"),
            "odsCode": s.get("odsCode"),
            "areas": areas(s["name"]),
            "routes": routes(s["name"]),
        }
        if kind == "ambiguous":
            row["conflicting"] = [
                {"dsptName": m.get("dsptName"), "dsptStatus": m.get("dsptStatus"),
                 "statusDate": m.get("statusDate"), "odsCode": m.get("odsCode")}
                for m in (s.get("matches") or [])
            ]
        rows.append(row)
        if kind == "current":
            for sp in (by_name.get(s["name"]) or {}).get("specialities") or []:
                current_by_speciality.setdefault(sp, []).append(s["name"])

    # The alternative side. For each flagged supplier, the tracked suppliers in
    # the SAME speciality whose DSPT publication is current. Narrow sub-areas
    # routinely have none, and that is reported as "no like-for-like", never
    # papered over with a supplier from a different area.
    for row in rows:
        if row["kind"] in ("current",):
            continue
        sp_all = (by_name.get(row["name"]) or {}).get("specialities") or []
        alts = []
        for sp in sp_all:
            peers = [p for p in current_by_speciality.get(sp, []) if p != row["name"]]
            # The lane label is spelled out too: "Digital health / AI" is read
            # by a member in the same sentence as the sub-area, and rule 12
            # does not stop at the sub-area column.
            alts.append({"speciality": spell_out(sp), "narrow": "Digital" not in sp,
                         "current": sorted(peers)})
        row["alternatives"] = alts
        row["question"] = question_for(row["kind"], row["name"],
                                       row["areas"][0] if row["areas"] else None)

    counts = {}
    for row in rows:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
    counts["unmatched"] = len(dspt.get("unmatched") or [])
    counts["tracked"] = len(rows) + counts["unmatched"]

    closing = []
    for fw in sorted(frameworks, key=lambda f: (f.get("ends") or "9999")):
        on_it = sorted({r["name"] for r in rows
                        for route in r["routes"] if route["name"] == fw.get("name")})
        closing.append({
            "name": fw.get("name"),
            "reference": fw.get("reference"),
            "owner": fw.get("owner"),
            "url": fw.get("url"),
            "starts": fw.get("starts"),
            "ends": fw.get("ends"),
            "notVerified": fw.get("notVerified"),
            "successor": succ.get(fw.get("name")),
            "trackedSuppliers": on_it,
        })

    return {
        "generated": dspt.get("checked"),
        "dsptCheckedOn": dspt.get("checked"),
        "frameworksAsOf": fw_doc.get("dataAsOf"),
        "source": dspt.get("source"),
        "sourceUrl": dspt.get("sourceUrl"),
        "frameworkSource": fw_doc.get("source"),
        "currentFromYear": CURRENT_FROM_YEAR,
        "yearRule": YEAR_RULE,
        "claimRule": CLAIM_RULE,
        "matchRule": MATCH_RULE,
        "unmatchedRule": UNMATCHED_RULE,
        "dsptNote": dspt.get("note"),
        "counts": counts,
        "suppliers": sorted(rows, key=lambda r: r["name"].lower()),
        "unmatched": sorted(dspt.get("unmatched") or [], key=str.lower),
        "frameworks": closing,
    }


def main():
    out = build()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    c = out["counts"]
    print("digital-assurance.json: %d tracked, %d current, %d behind, %d not published, "
          "%d ambiguous, %d unmatched, %d frameworks"
          % (c["tracked"], c.get("current", 0), c.get("behind", 0),
             c.get("notPublished", 0), c.get("ambiguous", 0), c["unmatched"],
             len(out["frameworks"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
