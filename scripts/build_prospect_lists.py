#!/usr/bin/env python3
"""Build prospect lists for Elevate and Thrive's products from the Hub's own data.

No LinkedIn, no Clay, no third-party enrichment. Every row is derived from a
primary source this repository already captures and verifies: NHS Supply Chain
contract launch briefs, Find a Tender awards, Companies House accounts, the
companies' own careers pages, MHRA alerts, the Hub's compare feed and the Hub
calendar. Each row carries the evidence that put it there, so a prospect is never
a guess and the line that opens the conversation is a fact the company can check.

Lists written (CSV, plus one summary.md):

  hub-team-prospects.csv           Companies whose reps need the Hub now, scored on
                                   live triggers (fresh award, competitor supply gap,
                                   open commercial roles, size band, growth, press).
  training-employers.csv           Companies advertising entry-level UK commercial
                                   roles today: the buyer for the Medical Sales
                                   Training Programme as an onboarding product.
  training-candidate-intents.csv   One row per live UK commercial role at a Hub
                                   supplier: the search-intent page targets that put
                                   the Training Programme and the Hub's Interview Prep
                                   in front of candidates while they are preparing.
  playbook-prospects.csv           Live clinical-commercial roles (clinical specialist,
                                   clinical application, nurse advisor, educator) and
                                   the companies hiring them: the Clinical Interview
                                   Playbook's audience and its employer-side channel.

Nothing here is published to the Hub. Output goes to tmp/prospects/ (gitignored)
unless --out says otherwise. Read-only against data/.

    python3 scripts/build_prospect_lists.py [--out DIR] [--asof YYYY-MM-DD] [--days 90]
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# Compare-tab speciality slug -> Hub calendar speciality slug(s). Two vocabularies
# exist (see data/speciality-map.json); this is the bridge used ONLY to say which
# upcoming conference a prospect's speciality is at. It never changes a tag.
CAL = {
    "wound": ["tissue-viability-and-wound-care"],
    "vascular": ["vascular-access-and-iv-therapy"],
    "continence": ["continence-bladder-and-bowel", "urology"],
    "ostomy": ["continence-bladder-and-bowel"],
    "endourology": ["urology"],
    "pathology": ["pathology-and-laboratory-medicine"],
    "bloodcoll": ["pathology-and-laboratory-medicine"],
    "bloodtx": ["haematology-and-patient-blood-management"],
    "respiratory": ["respiratory"],
    "ortho": ["orthopaedics-and-trauma"],
    "theatres": ["theatres-and-surgical"],
    "surgical": ["theatres-and-surgical"],
    "mis": ["theatres-and-surgical"],
    "handling": ["patient-handling"],
    "rehab": ["rehabilitation-prosthetics-and-orthotics"],
    "orthotics": ["rehabilitation-prosthetics-and-orthotics"],
    "infection": ["infection-prevention-and-control"],
    "skin-prep": ["infection-prevention-and-control"],
    "ssd": ["infection-prevention-and-control"],
    "digital": ["digital-and-medical-it"],
    "it": ["digital-and-medical-it"],
    "cardiology": ["cardiology-and-cardiac-surgery"],
    "diabetes": ["diabetes-and-endocrinology"],
    "endoscopy": ["colorectal-gi-and-endoscopy"],
    "gastro": ["colorectal-gi-and-endoscopy"],
    "anaesthesia": ["critical-care"],
    "monitoring": ["critical-care"],
    "neuro": ["neurology-and-neurosurgery"],
    "womens": ["gynaecology-and-womens-health", "maternity-and-neonatal"],
    "neonatal": ["maternity-and-neonatal"],
    "nutrition": ["nutrition-and-dietetics"],
    "oncology": ["oncology-and-sact"],
    "imaging": ["radiology-and-imaging"],
    "ultrasound": ["radiology-and-imaging"],
    "nuclear": ["radiology-and-imaging"],
    "renal": ["renal"],
    "ent": ["ent-and-head-and-neck"],
    "audiology": ["audiology-and-hearing"],
    "ophthalmology": ["ophthalmology"],
    "pharma": ["pharmacy-and-medicines"],
    "dermatology": ["dermatology"],
    "vascsurg": ["vascular-surgery-and-pad"],
    "facilities": ["capital-estates-watch"],
}

# Job-title vocabularies. A filing aid, never a claim about the role.
ENTRY = re.compile(r"\b(associate|graduate|trainee|junior|entry[- ]level|apprentice)\b", re.I)
CLINICAL = re.compile(r"\b(clinical (specialist|application|applications|educator|"
                      r"education|support|nurse|advisor|adviser|trainer|consultant|"
                      r"lead|manager)|nurse (advisor|adviser|specialist|educator)|"
                      r"application specialist|product specialist)\b", re.I)


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def parse_date(s):
    if not s:
        return None
    s = str(s)[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def build(asof, days, out):
    index = load("supplier-index.json")["suppliers"]
    fin = load("company-financials.json")["companies"]
    careers = load("supplier-careers.json")["suppliers"]
    awards = load("framework-awards.json")["awards"]
    issues = load("compare-issues.json")["specialities"]
    mhra = load("mhra-alerts.json").get("alerts", [])
    press = load("company-press.json").get("suppliers", {})
    cal = load("hub-calendar.json")
    labels = load("speciality-label-map.json")["entries"]

    window = asof - timedelta(days=days)
    label_to_slugs = {e["label"]: (e.get("slugs") or []) for e in labels}

    # alias -> canonical name (exact-only after normalisation, mirroring company_match)
    alias = {}
    for s in index:
        for a in [s["name"]] + list(s.get("aliases") or []):
            alias.setdefault(norm(a), s["name"])

    # Fresh Find a Tender awards per canonical supplier
    fresh_awards = defaultdict(list)
    for a in awards:
        pub = parse_date(a.get("published"))
        if not pub or pub < window:
            continue
        for sup in a.get("suppliers") or []:
            canon = alias.get(norm(sup.get("name")))
            if canon:
                fresh_awards[canon].append("%s: %s (%s)" % (pub.isoformat(), a.get("title", "")[:80],
                                                           (a.get("buyer") or {}).get("name", "")))

    # Live compare-tab issues by speciality slug (a competitor's gap is the opening)
    live_issues = defaultdict(list)
    for slug, block in issues.items():
        for it in block.get("issues") or []:
            closed = any(d.get("kind") == "resolved" for d in it.get("dates") or [])
            if closed or not (it.get("co") or "").strip():
                continue  # auto-detected items carry no company yet: not evidence of a rival's gap
            live_issues[slug].append((it.get("co", ""), it.get("p", "")[:60], it.get("url", "")))

    # MHRA alerts by company name and speciality slug
    mhra_by_slug = defaultdict(list)
    for al in mhra:
        for sl in al.get("specialities") or al.get("speciality") or []:
            mhra_by_slug[sl].append("%s %s" % (al.get("reference", ""), al.get("title", "")[:70]))

    # Recent press
    recent_press = {}
    for name, rec in press.items():
        n = 0
        for it in rec.get("items") or []:
            d = parse_date(it.get("date"))
            if d and d >= window:
                n += 1
        if n:
            recent_press[name] = n

    # Upcoming events by calendar slug (next 120 days)
    horizon = asof + timedelta(days=120)
    events = defaultdict(list)
    for e in cal.get("entries", []):
        if e.get("type") != "event":
            continue
        d = parse_date(e.get("date"))
        if not d or d < asof or d > horizon:
            continue
        for sl in e.get("specialities") or []:
            events[sl].append("%s (%s)" % (e.get("title"), d.strftime("%d/%m/%Y")))

    # Careers: dedupe group accounts (Abbott appears four times on one Workday board)
    seen_boards = set()
    roles_by_company = {}
    for c in careers:
        roles = c.get("roles") or []
        if not roles:
            continue
        board = (c.get("ats") or "", c.get("atsAccount") or c.get("careersUrl") or c["name"])
        if board in seen_boards:
            continue
        seen_boards.add(board)
        roles_by_company[c["name"]] = c

    def slugs_for(supplier):
        out = set()
        for lab in supplier.get("specialities") or []:
            for sl in label_to_slugs.get(lab) or []:
                out.add(sl)
        return sorted(out)

    def size_band(rec):
        e = (rec or {}).get("employees")
        if e is None:
            return "unknown", 0
        if e < 10:
            return "<10", 1
        if e < 250:
            return "10-249", 2
        return "250+", 0

    def growth(rec):
        s = (rec or {}).get("turnoverSeries") or []
        if len(s) >= 2 and s[-2].get("value") and s[-1].get("value"):
            return (s[-1]["value"] - s[-2]["value"]) / s[-2]["value"] * 100
        return None

    # ---- List 1: Hub team prospects ---------------------------------------------
    hub_rows = []
    for s in index:
        name = s["name"]
        rec = fin.get(name) or {}
        if rec.get("status") not in (None, "active"):
            continue
        slugs = slugs_for(s)
        score, triggers = 0, []
        if fresh_awards.get(name):
            score += 3
            triggers.append("Fresh award: " + "; ".join(fresh_awards[name][:2]))
        if s.get("frameworks"):
            score += 1
            triggers.append("On %d NHS Supply Chain framework(s)" % len(s["frameworks"]))
        comp = []
        for sl in slugs:
            for co, prod, url in live_issues.get(sl, []):
                if norm(co) != norm(name) and alias.get(norm(co)) != name:
                    comp.append("%s / %s" % (co, prod))
        if comp:
            score += 2
            triggers.append("Competitor gap on the Compare tab: " + "; ".join(sorted(set(comp))[:2]))
        for sl in slugs:
            if mhra_by_slug.get(sl):
                score += 1
                triggers.append("MHRA alert in speciality: " + mhra_by_slug[sl][0])
                break
        c = roles_by_company.get(name)
        if c and c.get("commercialRoles"):
            score += 2
            triggers.append("%d open UK commercial role(s) on its own careers page" % c["commercialRoles"])
        band, pts = size_band(rec)
        score += pts
        g = growth(rec)
        if g is not None and g >= 10:
            score += 1
            triggers.append("Turnover up %d%% on last filed accounts" % round(g))
        if recent_press.get(name):
            score += 1
            triggers.append("%d corroborated press item(s) in %d days" % (recent_press[name], days))
        live = bool(fresh_awards.get(name) or comp or (c and c.get("commercialRoles"))
                    or recent_press.get(name) or (g is not None and g >= 10))
        if score < 5 or not live:
            continue  # a framework place plus a size band is a profile, not a trigger
        meet = []
        for sl in slugs:
            for cs in CAL.get(sl, []):
                meet.extend(events.get(cs, []))
        hub_rows.append({
            "company": name,
            "specialities": " | ".join(s.get("specialities") or []),
            "employees": rec.get("employees") or "",
            "size_band": band,
            "score": score,
            "triggers": " || ".join(triggers),
            "meet_at": " | ".join(dict.fromkeys(meet))[:300],
            "lead_with": ("Compare tab (competitor gap)" if comp else
                          "Meeting Prep for the awarding trust" if fresh_awards.get(name) else
                          "Interview Prep + speciality panel"),
            "company_number": rec.get("companyNumber") or "",
        })
    hub_rows.sort(key=lambda r: (-r["score"], r["company"].lower()))

    # ---- Lists 2-4: from the companies' own careers pages -----------------------
    employers, intents, playbook = [], [], []
    for name, c in sorted(roles_by_company.items(), key=lambda kv: kv[0].lower()):
        rec = fin.get(name) or {}
        for r in c.get("roles") or []:
            if not r.get("uk"):
                continue
            row = {
                "company": name,
                "role_title": r.get("title", ""),
                "location": r.get("location", ""),
                "role_url": r.get("url", ""),
                "careers_page": c.get("careersUrl", ""),
                "ats": c.get("ats", ""),
                "employees": rec.get("employees") or "",
                "checked_on": c.get("checkedOn", ""),
            }
            if r.get("commercial"):
                intents.append(dict(row, interview_prep_target="%s - %s" % (name, r.get("title", ""))))
                if ENTRY.search(r.get("title", "")):
                    employers.append(row)
            if r.get("clinical") or CLINICAL.search(r.get("title", "")):
                playbook.append(row)

    os.makedirs(out, exist_ok=True)

    def write(fname, rows):
        path = os.path.join(out, fname)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            if not rows:
                fh.write("")
                return path
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        return path

    write("hub-team-prospects.csv", hub_rows)
    write("training-employers.csv", employers)
    write("training-candidate-intents.csv", intents)
    write("playbook-prospects.csv", playbook)

    # ---- Summary ------------------------------------------------------------------
    lines = ["# Prospect lists, built %s (window %d days)" % (asof.strftime("%d/%m/%Y"), days), ""]
    lines.append("Careers coverage: %d companies with readable role records out of %d checked. "
                 "The careers refresh rotates, so lists 2-4 grow as coverage grows." %
                 (len(roles_by_company), len(careers)))
    lines.append("")
    lines.append("| List | Rows |")
    lines.append("|---|---|")
    for lab, rows in (("Hub team prospects (live trigger, score >= 5)", hub_rows), ("Training employers", employers),
                      ("Candidate intents", intents), ("Playbook prospects", playbook)):
        lines.append("| %s | %d |" % (lab, len(rows)))
    lines.append("")
    lines.append("## Hub: top 20")
    lines.append("")
    lines.append("| Score | Company | Size | Triggers | Meet at |")
    lines.append("|---|---|---|---|---|")
    for r in hub_rows[:20]:
        lines.append("| %s | %s | %s | %s | %s |" % (r["score"], r["company"], r["size_band"],
                                                  r["triggers"][:160], r["meet_at"][:80]))
    lines.append("")
    lines.append("## Training employers (entry-level UK commercial roles live now)")
    lines.append("")
    for r in employers[:30]:
        lines.append("* %s: %s (%s)" % (r["company"], r["role_title"], r["location"]))
    lines.append("")
    lines.append("## Playbook prospects (clinical-commercial roles live now)")
    lines.append("")
    for r in playbook[:30]:
        lines.append("* %s: %s (%s)" % (r["company"], r["role_title"], r["location"]))
    with open(os.path.join(out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return hub_rows, employers, intents, playbook


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "tmp", "prospects"))
    ap.add_argument("--asof", default=date.today().isoformat(), help="YYYY-MM-DD, default today")
    ap.add_argument("--days", type=int, default=90, help="lookback for awards and press")
    a = ap.parse_args(argv)
    asof = parse_date(a.asof)
    if not asof:
        ap.error("--asof must be YYYY-MM-DD")
    hub, emp, intents, pb = build(asof, a.days, a.out)
    print("hub=%d employers=%d intents=%d playbook=%d -> %s" % (len(hub), len(emp), len(intents), len(pb), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
