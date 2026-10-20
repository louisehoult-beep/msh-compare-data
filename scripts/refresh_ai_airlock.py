#!/usr/bin/env python3
"""Refresh data/ai-airlock-cohorts.json from the MHRA AI Airlock pages.

Source: the gov.uk content API for the MHRA AI Airlock collection and its
cohort pages. Python stdlib only.

Rules this file keeps:
  * Company and product names are MHRA's own spelling. They are NOT resolved
    to legal entities or Companies House (a separate, gated step), so every
    member carries "entityResolved": false.
  * The collection page states cohort counts in words. Our own counts are
    cross-checked against those statements. Agreement or disagreement is
    recorded; a disagreement is never corrected.
  * A cohort that is not announced yet (phase 3) is listed with members [] and
    a plain note. Nothing is invented to fill it.
  * Parsing is strict. A member heading the parser cannot place is kept with
    company/product null and "needsReview": true, never guessed.

Usage: python3 scripts/refresh_ai_airlock.py [--out PATH]
"""
import datetime
import html
import json
import re
import sys
import time
import urllib.request

API = "https://www.gov.uk/api/content"
SITE = "https://www.gov.uk"
COLLECTION_PATH = "/government/collections/ai-airlock-a-regulatory-sandbox-for-ai-enabled-medical-devices"
PILOT_PATH = "/government/publications/ai-airlock-pilot-cohort"
PILOT_HTML_PATH = "/government/publications/ai-airlock-pilot-cohort/ai-airlock-pilot-cohort"
PHASE2_PATH = "/government/publications/ai-airlock-phase-2-cohort"
PHASE2_REPORT_PATH = "/government/publications/ai-airlock-sandbox-phase-2-programme-report"
DEFAULT_OUT = "data/ai-airlock-cohorts.json"

RULE = ("Company and product names are MHRA's own spelling from the gov.uk AI Airlock pages. "
        "Not resolved to legal entities or Companies House (entityResolved false until the "
        "separate gated step). Counts are cross-checked against the collection page's own "
        "statements; disagreements are recorded, never corrected.")

# Phase 2 member headings are written inconsistently by MHRA (product - company,
# or company - product). Each heading below was read on the live page on
# 20/10/2026. Anything not listed is flagged needsReview rather than guessed.
PHASE2_HEADINGS = {
    "TORTUS": {"company": "TORTUS", "product": "TORTUS"},
    "Nu & Aegis AI Conversational & Monitoring System - Numan": {
        "company": "Numan", "product": "Nu & Aegis AI Conversational & Monitoring System"},
    "PANProfiler Colorectal (MSI/MMR) - Panakeia Technologies": {
        "company": "Panakeia Technologies", "product": "PANProfiler Colorectal (MSI/MMR)"},
    "Octopath": {"company": "Octopath", "product": "Octopath"},
    "NHS England Federated Data Platform - Safe Summarisation": {
        "company": "NHS England Federated Data Platform", "product": "Safe Summarisation"},
    "Eye2Gene - Eye2Gene Ltd (and Hardian Health)": {
        "company": "Eye2Gene Ltd (and Hardian Health)", "product": "Eye2Gene"},
    "DeepXAI - DeepX Health UK Ltd": {"company": "DeepX Health UK Ltd", "product": "DeepXAI"},
}

# Pilot headings read on 20/10/2026. product is only set where the page names it.
PILOT_HEADINGS = {
    "Gen-AI and LLMs to create impression of radiology reports: Developed by Philips Medical Systems": {
        "company": "Philips Medical Systems", "product": None,
        "productNote": "MHRA names no product; page describes a generative AI function added to the Philips PACS."},
    "Federated AI Monitoring Service (FAMOS): A virtual environment developed by Newtons Tree Ltd": {
        "company": "Newtons Tree Ltd", "product": "Federated AI Monitoring Service (FAMOS)"},
    "AI platform interoperating with existing clinical systems: OncoFlow": {
        "company": "OncoFlow", "product": "OncoFlow",
        "productNote": "MHRA gives the name OncoFlow only; no separate company name."},
    "Structured AI model to provide guidelines during a clinical encounter: Developed by Automedica Ltd": {
        "company": "Automedica Ltd", "product": "SmartGuideline"},
    "Artificial intelligence to predict risk in COPD patients: Developed by Lenus Health Ltd": {
        "company": "Lenus Health Ltd", "product": None},
}


# ---------------------------------------------------------------- fetching

def fetch_json(path, retries=1, timeout=30):
    url = API + path
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "msh-compare-data/ai-airlock-refresh"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - recorded, then retried once
            last = e
            time.sleep(2)
    raise RuntimeError("fetch failed for %s: %s" % (url, last))


# ----------------------------------------------------------------- parsing

def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    """Lookup key only: dashes folded so en/em dash headings match."""
    return s.replace("\u2013", "-").replace("\u2014", "-")


def date_of(iso):
    return iso[:10] if iso else None


def _blocks(body):
    """Yield (tag, text) for h2/h3 and bold-only paragraphs, with the text that
    follows each as its description."""
    pat = re.compile(r"<(h2|h3)[^>]*>(.*?)</\1>|<p>\s*<strong>([^<]*)</strong>\s*</p>", re.S)
    out, last_end, cur = [], 0, None
    for m in pat.finditer(body):
        if cur is not None:
            cur["text"] = body[last_end:m.start()]
        tag = m.group(1) or "strong"
        cur = {"tag": tag, "heading": clean(m.group(2) or m.group(3)), "text": ""}
        out.append(cur)
        last_end = m.end()
    if cur is not None:
        cur["text"] = body[last_end:]
    for b in out:
        b["text"] = clean(b["text"])
    return out


def parse_pilot(body):
    members = []
    started = False
    for b in _blocks(body):
        if b["tag"] == "h2":
            started = b["heading"].lower().startswith("the selected sandbox candidates")
            continue
        if not started or b["tag"] != "h3":
            continue
        heading = b["heading"]
        theme = heading.split(":")[0].strip()
        known = PILOT_HEADINGS.get(norm(heading))
        withdrawn = bool(re.search(r"\bwithdrawn from the AI Airlock\b", b["text"]))
        m = {
            "company": known["company"] if known else None,
            "product": known["product"] if known else None,
            "theme": theme,
            "heading": heading,
            "status": "withdrawn" if withdrawn else "participating",
            "entityResolved": False,
        }
        if known and known.get("productNote"):
            m["productNote"] = known["productNote"]
        if withdrawn:
            m["statusNote"] = b["text"]
        if not known:
            m["needsReview"] = True
        members.append(m)
    return members


def parse_phase2(body):
    members = []
    challenge = None
    role = None
    for b in _blocks(body):
        h = b["heading"]
        if b["tag"] == "h2":
            mm = re.match(r"Regulatory challenge (\d+):\s*(.+)$", h)
            challenge = {"number": int(mm.group(1)), "title": mm.group(2)} if mm else None
            role = None
            continue
        if challenge is None:
            continue
        low = h.lower().rstrip(":").strip()
        if low == "multi-environment candidate":
            role = "multi-environment"
            continue
        if low == "simulation candidate":
            role = "simulation"
            continue
        if b["tag"] == "strong" and role is None:
            continue
        key = h
        known = PHASE2_HEADINGS.get(norm(key))
        m = {
            "company": known["company"] if known else None,
            "product": known["product"] if known else None,
            "theme": "Regulatory challenge %d: %s" % (challenge["number"], challenge["title"]),
            "challengeNumber": challenge["number"],
            "testingRole": role,
            "heading": h,
            "status": "participating",
            "entityResolved": False,
        }
        if not known:
            m["needsReview"] = True
        members.append(m)
    return members


# --------------------------------------------------------------- count check

STATEMENT_RE = re.compile(r"(\d+|[a-z]+) innovators? across (\d+|[a-z]+) regulatory challenges?", re.I)
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def _num(tok):
    tok = tok.lower()
    return int(tok) if tok.isdigit() else WORDS.get(tok)


def collection_statements(groups):
    """Return {'all': {innovators, challenges, text}, 'phase2': {...}, 'pilotProducts': n}
    taken from the collection page's own sentences."""
    found = {}
    for g in groups:
        text = clean(g.get("body", ""))
        for m in STATEMENT_RE.finditer(text):
            cut = text.rfind(". ", 0, m.start())
            sent_start = cut + 2 if cut >= 0 else 0
            end = text.find(".", m.end())
            sentence = text[sent_start:(end + 1 if end >= 0 else len(text))].strip()
            entry = {"innovators": _num(m.group(1)), "challenges": _num(m.group(2)), "text": sentence}
            if re.search(r"second phase|phase 2", sentence, re.I):
                found["phase2"] = entry
            elif re.search(r"testing phases|since its launch", sentence, re.I):
                found["all"] = entry
        pm = re.search(r"pilot programme closed[^.]*focused on (\w+) products", text, re.I)
        if pm:
            found["pilotProducts"] = {"products": _num(pm.group(1)), "text": clean(pm.group(0)) + "."}
    return found


def count_check(phases, statements):
    pilot = next(p for p in phases if p["phase"] == "Pilot")
    p2 = next(p for p in phases if p["phase"] == "Phase 2")
    active_pilot = [m for m in pilot["members"] if m["status"] == "participating"]
    p2_challenges = {m["challengeNumber"] for m in p2["members"]}
    pilot_themes = {m["theme"] for m in active_pilot}
    ours = {
        "pilotListed": len(pilot["members"]),
        "pilotParticipating": len(active_pilot),
        "phase2Members": len(p2["members"]),
        "phase2Challenges": len(p2_challenges),
        "pilotThemes": len(pilot_themes),
        "allInnovators": len(active_pilot) + len(p2["members"]),
        "allChallenges": len(pilot_themes) + len(p2_challenges),
    }
    checks = []

    def add(name, stmt, our_inn, our_ch=None):
        if stmt is None:
            checks.append({"check": name, "agrees": None,
                           "note": "statement not found on the collection page"})
            return
        row = {"check": name, "statement": stmt["text"],
               "statedInnovators": stmt.get("innovators", stmt.get("products")),
               "ourInnovators": our_inn}
        agrees = row["statedInnovators"] == our_inn
        if our_ch is not None:
            row["statedChallenges"] = stmt["challenges"]
            row["ourChallenges"] = our_ch
            agrees = agrees and stmt["challenges"] == our_ch
        row["agrees"] = agrees
        checks.append(row)

    add("pilot + phase 2 (innovators, regulatory challenges)", statements.get("all"),
        ours["allInnovators"], ours["allChallenges"])
    add("phase 2 (innovators, regulatory challenges)", statements.get("phase2"),
        ours["phase2Members"], ours["phase2Challenges"])
    add("pilot (products)", statements.get("pilotProducts"), ours["pilotParticipating"])
    checks[-1]["note"] = ("Pilot cohort page lists %d technologies; %d withdrew, leaving %d participating."
                          % (ours["pilotListed"], ours["pilotListed"] - ours["pilotParticipating"],
                             ours["pilotParticipating"]))
    known = [c["agrees"] for c in checks if c["agrees"] is not None]
    return {
        "ours": ours,
        "checks": checks,
        "allAgree": bool(known) and all(known) and len(known) == len(checks),
        "note": "Our challenge count for the pilot is the number of distinct challenge headings "
                "on the pilot cohort page; MHRA does not state it. Disagreements, if any, are "
                "recorded here and not corrected.",
    }


# ------------------------------------------------------------------ building

def build(coll, pilot_page, pilot_html, p2_page, p2_report, generated):
    groups = coll["details"].get("collection_groups", [])
    pilot_members = parse_pilot(pilot_html["details"]["body"])
    p2_members = parse_phase2(p2_page["details"]["body"])
    pilot_updated = date_of(pilot_html.get("public_updated_at") or pilot_page.get("public_updated_at"))
    p2_updated = date_of(p2_page.get("public_updated_at"))
    coll_updated = date_of(coll.get("public_updated_at"))
    for m in pilot_members:
        m["phase"] = "Pilot"
        m["sourceUrl"] = SITE + PILOT_PATH
        m["pageUpdated"] = pilot_updated
    for m in p2_members:
        m["phase"] = "Phase 2"
        m["sourceUrl"] = SITE + PHASE2_PATH
        m["pageUpdated"] = p2_updated
    report_names = _report_names(p2_report)
    phases = [
        {"phase": "Pilot", "sourceUrl": SITE + PILOT_PATH, "pageUpdated": pilot_updated,
         "status": "complete (closed April 2025)", "members": pilot_members},
        {"phase": "Phase 2", "sourceUrl": SITE + PHASE2_PATH, "pageUpdated": p2_updated,
         "status": "complete (completed May 2026)", "members": p2_members,
         "programmeReport": {
             "sourceUrl": SITE + PHASE2_REPORT_PATH,
             "pageUpdated": date_of(p2_report.get("public_updated_at")),
             "namesProductsOnPage": report_names,
             "note": ("The report page text names no products; the case studies sit in attached PDFs, "
                      "which this script does not parse.")}},
        {"phase": "Phase 3", "sourceUrl": SITE + COLLECTION_PATH, "pageUpdated": coll_updated,
         "status": "open for applications", "members": [],
         "note": ("Cohort not announced. MHRA announced the third phase on 6 October 2026 and states "
                  "selected participants will be listed on the collection page when onboarded. "
                  "Phase 3 focus: post-market surveillance and broader oversight of AI-enabled "
                  "medical devices across the device lifecycle.")},
    ]
    check = count_check(phases, collection_statements(groups))
    dates = [d for d in (pilot_updated, p2_updated, coll_updated,
                         date_of(p2_report.get("public_updated_at"))) if d]
    flagged = [m for p in phases for m in p["members"] if m.get("needsReview")]
    return {
        "rule": RULE,
        "source": {
            "collection": SITE + COLLECTION_PATH,
            "collectionUpdated": coll_updated,
            "api": API,
            "pagesRead": [SITE + p for p in (COLLECTION_PATH, PILOT_PATH, PILOT_HTML_PATH,
                                             PHASE2_PATH, PHASE2_REPORT_PATH)],
        },
        "generated": generated,
        "dataAsOf": max(dates) if dates else None,
        "phases": phases,
        "counts": {
            "byPhase": {p["phase"]: len(p["members"]) for p in phases},
            "pilotParticipating": check["ours"]["pilotParticipating"],
            "total": sum(len(p["members"]) for p in phases),
            "totalParticipating": check["ours"]["allInnovators"],
            "needsReview": len(flagged),
            "collectionCrossCheck": check,
        },
    }


def _report_names(p2_report):
    body = clean(p2_report.get("details", {}).get("body", ""))
    return any(n["product"] and n["product"].lower() in body.lower() for n in PHASE2_HEADINGS.values())


def main(argv):
    out = DEFAULT_OUT
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    coll = fetch_json(COLLECTION_PATH)
    pilot_page = fetch_json(PILOT_PATH)
    pilot_html = fetch_json(PILOT_HTML_PATH)
    p2_page = fetch_json(PHASE2_PATH)
    p2_report = fetch_json(PHASE2_REPORT_PATH)
    doc = build(coll, pilot_page, pilot_html, p2_page, p2_report,
                datetime.date.today().isoformat())
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    c = doc["counts"]
    print("ai-airlock: %s | participating %d | crossCheck allAgree=%s | needsReview %d"
          % (c["byPhase"], c["totalParticipating"], c["collectionCrossCheck"]["allAgree"], c["needsReview"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
