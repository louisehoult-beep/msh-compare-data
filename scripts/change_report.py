#!/usr/bin/env python3
"""
change_report.py — what actually changed in the Hub data between two dates.

Every nightly run commits to this repo, so git already holds a dated copy of every
data file back to 17/07/2026. What it does not hold is an answer: `git log -p
data/supplier-seed.json` over a fortnight is a 3 MB JSON diff that nobody can read.
This turns the same history into English — which suppliers arrived, who gained or
lost a framework, whose turnover moved, which company numbers were corrected.

  python3 scripts/change_report.py --since 2026-08-01
  python3 scripts/change_report.py --since 7d
  python3 scripts/change_report.py --base HEAD~20 --head HEAD
  python3 scripts/change_report.py --since 30d --supplier Stryker
  python3 scripts/change_report.py --since 7d --markdown /tmp/week.md
  python3 scripts/change_report.py --selftest

--head defaults to the working tree, so this reads uncommitted data too.
Long sections are capped by --limit (default 25) and the cap is always PRINTED,
never silent: a truncated list that looks complete is how "nothing else changed"
becomes a false statement.

History starts at the repo's first commit. A supplier that was present then was
not necessarily new then, and the report says so rather than implying it.

Exit 0 = report produced (whether or not anything changed).
Exit 2 = a revision could not be resolved, or a file would not parse.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from check_no_loss import core, lead, read  # noqa: E402  (same repo, same rules)

SEED = "data/supplier-seed.json"
FINANCIALS = "data/company-financials.json"
AWARDS = "data/company-awards.json"
FRAMEWORKS = "data/frameworks.json"

# Free text that the pipeline rewords constantly. A wording change in these is not
# a change worth a line in a report; only arrivals and departures are.
NOISY = {"note", "_specialitiesEvidence", "voice", "curated"}


def git(*args, check=True):
    r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        die(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def die(msg):
    print(f"change_report: {msg}", file=sys.stderr)
    sys.exit(2)


def uk(d):
    """ISO date to the way Lou reads dates."""
    try:
        return datetime.date.fromisoformat(d).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return d or "unknown"


def resolve(spec):
    """A revision from a date, an age like '7d', or anything git already understands."""
    if spec is None:
        return None                      # the working tree
    m = re.fullmatch(r"(\d+)d", spec)
    if m:
        day = datetime.date.today() - datetime.timedelta(days=int(m.group(1)))
        spec = day.isoformat()
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", spec)
    if m:
        spec = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", spec):
        rev = git("rev-list", "-1", f"--before={spec} 23:59:59", "HEAD")
        if not rev:
            first = git("rev-list", "--max-parents=0", "HEAD").split()[0]
            when = git("log", "-1", "--format=%ad", "--date=short", first)
            die(f"no commit on or before {uk(spec)} — this history starts {uk(when)}")
        return rev
    out = git("rev-parse", "--verify", f"{spec}^{{commit}}", check=False)
    if not out:
        die(f"cannot resolve revision {spec!r}")
    return out


def stamp(rev):
    if rev is None:
        return "the working tree (uncommitted)"
    when = git("log", "-1", "--format=%ad", "--date=short", rev)
    return f"{uk(when)} ({rev[:8]})"


def load(rev, path):
    doc = read(rev, os.path.join(ROOT, path) if rev is None else path)
    return doc


def suppliers_by_name(doc):
    if not isinstance(doc, dict):
        return {}
    return {s["name"]: s for s in doc.get("suppliers") or [] if s.get("name")}


def item_id(item):
    """One framework, alert or news item named the way a person would name it."""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for k in ("name", "title", "headline", "text", "url"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return json.dumps(item, sort_keys=True)[:120]
    return str(item)


def ids(records):
    return {item_id(x) for x in records or []}


def find_by_id(records, wanted):
    for x in records or []:
        if item_id(x) == wanted:
            return x
    return None


def looks_renamed(name, present):
    """Is this name still findable among `present`, just written differently?"""
    forms = set(present)
    forms |= {core(p) for p in present}
    if core(name) in forms or name in forms:
        return True
    ln = lead(name)
    return bool(ln) and any(lead(p) == ln for p in present)


def money(v):
    if isinstance(v, (int, float)):
        if v >= 1_000_000:
            return f"£{v / 1_000_000:.1f}m"
        if v >= 1_000:
            return f"£{v / 1_000:.0f}k"
        return f"£{v:,.0f}"
    return "not recorded" if v in (None, "") else str(v)


def diff_seed(base, head, only=None):
    """Everything that moved inside supplier-seed.json."""
    b, h = suppliers_by_name(base), suppliers_by_name(head)
    if only:
        key = only.lower()
        b = {k: v for k, v in b.items() if key in k.lower()}
        h = {k: v for k, v in h.items() if key in k.lower()}

    out = {"added": [], "removed": [], "renamed": [],
           "frameworks_gained": [], "frameworks_lost": [],
           "alerts_added": [], "news_added": [],
           "specialities_changed": [], "products_changed": [],
           "fields_changed": []}

    # A rename shows up twice — as a departure and as an arrival — and reporting it
    # as both is how "1 supplier lost" gets read as a company dropping off the Hub.
    # Pair them up first, and let the pair stand for both halves.
    gone_names, new_names = sorted(set(b) - set(h)), sorted(set(h) - set(b))
    paired = {}
    for name in gone_names:
        for cand in new_names:
            if cand in paired.values():
                continue
            if looks_renamed(name, {cand}):
                paired[name] = cand
                break
    for name in new_names:
        if name in paired.values():
            continue
        out["added"].append({"name": name,
                             "specialities": h[name].get("specialities") or [],
                             "frameworks": len(h[name].get("frameworks") or [])})
    for name in gone_names:
        if name in paired:
            out["renamed"].append({"name": name, "to": paired[name],
                                   "frameworks": len(b[name].get("frameworks") or [])})
        else:
            out["removed"].append({"name": name,
                                   "frameworks": len(b[name].get("frameworks") or [])})

    for name in sorted(set(b) & set(h)):
        bs, hs = b[name], h[name]
        for field, bucket in (("frameworks", "frameworks_gained"),
                              ("alerts", "alerts_added"),
                              ("news", "news_added")):
            gained = ids(hs.get(field)) - ids(bs.get(field))
            for g in sorted(gained):
                rec = find_by_id(hs.get(field), g)
                out[bucket].append({"supplier": name, "item": g,
                                    "dates": (rec or {}).get("dates") if isinstance(rec, dict) else None,
                                    "date": (rec or {}).get("date") if isinstance(rec, dict) else None,
                                    "url": (rec or {}).get("url") if isinstance(rec, dict) else None})
        for lost in sorted(ids(bs.get("frameworks")) - ids(hs.get("frameworks"))):
            out["frameworks_lost"].append({"supplier": name, "item": lost})

        bspec, hspec = set(bs.get("specialities") or []), set(hs.get("specialities") or [])
        if bspec != hspec:
            out["specialities_changed"].append(
                {"supplier": name, "added": sorted(hspec - bspec), "removed": sorted(bspec - hspec)})
        bp, hp = ids(bs.get("products")), ids(hs.get("products"))
        if bp != hp:
            out["products_changed"].append(
                {"supplier": name, "added": len(hp - bp), "removed": len(bp - hp)})

        for k in ("companyNumberCandidate", "brand", "verified", "source", "links"):
            if k in NOISY:
                continue
            if json.dumps(bs.get(k), sort_keys=True) != json.dumps(hs.get(k), sort_keys=True):
                out["fields_changed"].append({"supplier": name, "field": k,
                                              "from": bs.get(k), "to": hs.get(k)})
    return out


def diff_financials(base, head, only=None):
    """Companies House layer: arrivals, corrections, and figures that moved."""
    def index(doc):
        if not isinstance(doc, dict):
            return {}
        c = doc.get("companies")
        if isinstance(c, dict):
            return c
        if isinstance(c, list):
            return {x.get("name") or x.get("registeredName") or item_id(x): x for x in c}
        return {}

    b, h = index(base), index(head)
    if only:
        key = only.lower()
        b = {k: v for k, v in b.items() if key in k.lower()}
        h = {k: v for k, v in h.items() if key in k.lower()}

    out = {"added": [], "removed": [], "number_changed": [], "confidence_changed": [],
           "turnover_changed": [], "status_changed": [], "accounts_updated": []}
    for name in sorted(set(h) - set(b)):
        out["added"].append({"name": name, "number": h[name].get("companyNumber"),
                             "confidence": h[name].get("matchConfidence")})
    for name in sorted(set(b) - set(h)):
        out["removed"].append({"name": name})
    for name in sorted(set(b) & set(h)):
        bc, hc = b[name], h[name]
        if bc.get("companyNumber") != hc.get("companyNumber"):
            out["number_changed"].append({"name": name, "from": bc.get("companyNumber"),
                                          "to": hc.get("companyNumber"),
                                          "registeredName": hc.get("registeredName")})
        if bc.get("matchConfidence") != hc.get("matchConfidence"):
            out["confidence_changed"].append({"name": name, "from": bc.get("matchConfidence"),
                                              "to": hc.get("matchConfidence")})
        if bc.get("turnoverGBP") != hc.get("turnoverGBP"):
            out["turnover_changed"].append({"name": name, "from": bc.get("turnoverGBP"),
                                            "to": hc.get("turnoverGBP"),
                                            "madeUpTo": hc.get("accountsMadeUpTo")})
        if bc.get("status") != hc.get("status"):
            out["status_changed"].append({"name": name, "from": bc.get("status"),
                                          "to": hc.get("status")})
        if bc.get("accountsMadeUpTo") != hc.get("accountsMadeUpTo"):
            out["accounts_updated"].append({"name": name, "from": bc.get("accountsMadeUpTo"),
                                            "to": hc.get("accountsMadeUpTo")})
    return out


def diff_counts(base, head, path):
    """A net record count for the files that do not need naming line by line."""
    def size(doc):
        if isinstance(doc, dict):
            for k, v in doc.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, list):
                    return len(v)
                if isinstance(v, dict) and len(v) > 3:
                    return len(v)
        if isinstance(doc, list):
            return len(doc)
        return None
    return {"file": path, "base": size(base), "head": size(head),
            "asOf": (head or {}).get("dataAsOf") if isinstance(head, dict) else None}


def section(lines, title, items, render, limit):
    if not items:
        return
    lines.append(f"### {title} ({len(items)})")
    lines.append("")
    for x in items[:limit]:
        lines.append(f"- {render(x)}")
    if len(items) > limit:
        lines.append(f"- _…and {len(items) - limit} more not listed "
                     f"(raise --limit to see them all)_")
    lines.append("")


def build_report(base_rev, head_rev, only, limit):
    seed_b, seed_h = load(base_rev, SEED), load(head_rev, SEED)
    if seed_h is None:
        die(f"{SEED} could not be read at {stamp(head_rev)}")
    if seed_b is None:
        die(f"{SEED} did not exist at {stamp(base_rev)}")
    fin_b, fin_h = load(base_rev, FINANCIALS), load(head_rev, FINANCIALS)

    s = diff_seed(seed_b, seed_h, only)
    f = diff_financials(fin_b, fin_h, only) if (fin_b and fin_h) else None
    counts = [diff_counts(load(base_rev, p), load(head_rev, p), p)
              for p in (AWARDS, FRAMEWORKS)]

    L = []
    L.append(f"# Hub data — what changed")
    L.append("")
    L.append(f"**From** {stamp(base_rev)}  ")
    L.append(f"**To** {stamp(head_rev)}")
    if only:
        L.append(f"  \n**Filtered to** names containing {only!r}")
    L.append("")

    head = []
    if s["added"]:
        head.append(f"{len(s['added'])} supplier(s) added")
    if s["removed"]:
        head.append(f"{len(s['removed'])} removed")
    if s["renamed"]:
        head.append(f"{len(s['renamed'])} renamed")
    if s["frameworks_gained"]:
        head.append(f"{len(s['frameworks_gained'])} framework place(s) gained")
    if s["frameworks_lost"]:
        head.append(f"{len(s['frameworks_lost'])} lost")
    if s["alerts_added"]:
        head.append(f"{len(s['alerts_added'])} new alert(s)")
    if f:
        if f["turnover_changed"]:
            head.append(f"{len(f['turnover_changed'])} turnover figure(s) changed")
        if f["number_changed"]:
            head.append(f"{len(f['number_changed'])} company number(s) corrected")
    L.append("**In one line:** " + (", ".join(head) + "." if head else
                                    "nothing changed in the supplier or company data."))
    L.append("")

    section(L, "Suppliers added", s["added"],
            lambda x: f"**{x['name']}** — {', '.join(x['specialities']) or 'no speciality recorded'}"
                      f" ({x['frameworks']} framework(s))", limit)
    section(L, "Suppliers removed", s["removed"],
            lambda x: f"**{x['name']}** — had {x['frameworks']} framework(s). "
                      f"A removal is only ever right if it was decided, not noticed later.", limit)
    section(L, "Suppliers renamed (same company, new name)", s["renamed"],
            lambda x: f"{x['name']} → **{x['to']}** ({x['frameworks']} framework(s) carried over) "
                      f"— matched on the name alone, so confirm it before quoting it", limit)
    section(L, "Framework places gained", s["frameworks_gained"],
            lambda x: f"**{x['supplier']}** — {x['item']}"
                      + (f" ({x['dates']})" if x.get("dates") else ""), limit)
    section(L, "Framework places lost", s["frameworks_lost"],
            lambda x: f"**{x['supplier']}** — {x['item']}", limit)
    section(L, "New alerts", s["alerts_added"],
            lambda x: f"**{x['supplier']}** — {x['item'][:160]}"
                      + (f" ({uk(x['date'])})" if x.get("date") else ""), limit)
    section(L, "New press items", s["news_added"],
            lambda x: f"**{x['supplier']}** — {x['item'][:160]}", limit)
    section(L, "Specialities changed", s["specialities_changed"],
            lambda x: f"**{x['supplier']}** — "
                      + (f"added {', '.join(x['added'])}" if x["added"] else "")
                      + ("; " if x["added"] and x["removed"] else "")
                      + (f"removed {', '.join(x['removed'])}" if x["removed"] else ""), limit)
    section(L, "Product lists changed", s["products_changed"],
            lambda x: f"**{x['supplier']}** — {x['added']} added, {x['removed']} removed", limit)
    section(L, "Other supplier fields changed", s["fields_changed"],
            lambda x: f"**{x['supplier']}** — {x['field']}: {str(x['from'])[:60]} → {str(x['to'])[:60]}", limit)

    if f:
        L.append("## Companies House layer")
        L.append("")
        section(L, "Companies added", f["added"],
                lambda x: f"**{x['name']}** — {x['number'] or 'no number'} "
                          f"({x['confidence'] or 'confidence not recorded'})", limit)
        section(L, "Companies removed", f["removed"], lambda x: f"**{x['name']}**", limit)
        section(L, "Company numbers corrected", f["number_changed"],
                lambda x: f"**{x['name']}** — {x['from']} → {x['to']} "
                          f"({x.get('registeredName') or 'registered name not recorded'})", limit)
        section(L, "Match confidence changed", f["confidence_changed"],
                lambda x: f"**{x['name']}** — {x['from']} → {x['to']}", limit)
        section(L, "Turnover changed", f["turnover_changed"],
                lambda x: f"**{x['name']}** — {money(x['from'])} → {money(x['to'])}"
                          + (f" (accounts to {x['madeUpTo']})" if x.get("madeUpTo") else ""), limit)
        section(L, "Company status changed", f["status_changed"],
                lambda x: f"**{x['name']}** — {x['from']} → {x['to']}", limit)
        section(L, "Accounts refiled", f["accounts_updated"],
                lambda x: f"**{x['name']}** — accounts date {x['from']} → {x['to']}", limit)
    else:
        L.append("_company-financials.json was not readable at both revisions, so no "
                 "Companies House comparison was made._")
        L.append("")

    L.append("## Record counts elsewhere")
    L.append("")
    for c in counts:
        if c["base"] is None and c["head"] is None:
            L.append(f"- `{c['file']}` — not comparable at these revisions")
            continue
        delta = (c["head"] or 0) - (c["base"] or 0)
        way = "no change" if delta == 0 else (f"+{delta}" if delta > 0 else str(delta))
        L.append(f"- `{c['file']}` — {c['base']} → {c['head']} ({way})"
                 + (f", dataAsOf {c['asOf']}" if c.get("asOf") else ""))
    L.append("")
    L.append("---")
    L.append("_Generated by `scripts/change_report.py` from this repo's own commit history. "
             "Every figure here is a difference between two committed states of the data, "
             "not a fresh claim about the world: check the underlying source before "
             "publishing anything from it._")
    return "\n".join(L), {"seed": s, "financials": f, "counts": counts}


BRIEF_TOP = 10


def brief_payload(base_rev, head_rev, raw, top=BRIEF_TOP):
    """A compact, briefing-shaped summary of the same diff.

    The full report is for us. This is what a rep can use: framework places won and
    lost, suppliers arriving, safety alerts, and companies whose Companies House
    status moved. Deliberately NOT included — brand colours, links, speciality
    re-tagging, product wording: housekeeping on our side is not news to a member.

    Every list is capped, and every cap records how many were left out, so the
    briefing can say "and 12 more on the Hub" instead of implying it is the lot.
    """
    s, f = raw["seed"], raw["financials"] or {}

    def cap(items, render):
        return {"items": [render(x) for x in items[:top]],
                "shown": min(len(items), top),
                "total": len(items),
                "notListed": max(0, len(items) - top)}

    def when(rev):
        if rev is None:
            return datetime.date.today().isoformat()
        return git("log", "-1", "--format=%ad", "--date=short", rev)

    counts = {
        "suppliersAdded": len(s["added"]),
        "suppliersRemoved": len(s["removed"]),
        "frameworksGained": len(s["frameworks_gained"]),
        "frameworksLost": len(s["frameworks_lost"]),
        "alerts": len(s["alerts_added"]),
        "companyNumbersCorrected": len(f.get("number_changed", [])),
        "statusChanged": len(f.get("status_changed", [])),
        "turnoverChanged": len(f.get("turnover_changed", [])),
    }
    bits = []
    if counts["frameworksGained"]:
        bits.append(f"{counts['frameworksGained']} framework place(s) gained")
    if counts["frameworksLost"]:
        bits.append(f"{counts['frameworksLost']} lost")
    if counts["suppliersAdded"]:
        bits.append(f"{counts['suppliersAdded']} supplier(s) added")
    if counts["alerts"]:
        bits.append(f"{counts['alerts']} new alert(s)")
    if counts["statusChanged"]:
        bits.append(f"{counts['statusChanged']} company status change(s)")

    return {
        "_notice": "GENERATED by scripts/change_report.py --brief. Differences between "
                   "two committed states of Hub data, not fresh claims about the world.",
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "from": when(base_rev),
        "to": when(head_rev),
        "headline": ", ".join(bits) + "." if bits else "",
        "counts": counts,
        "frameworksGained": cap(s["frameworks_gained"],
                                lambda x: {"supplier": x["supplier"], "framework": x["item"],
                                           "dates": x.get("dates")}),
        "frameworksLost": cap(s["frameworks_lost"],
                              lambda x: {"supplier": x["supplier"], "framework": x["item"]}),
        "suppliersAdded": cap(s["added"],
                              lambda x: {"name": x["name"],
                                         "specialities": x["specialities"]}),
        "suppliersRemoved": cap(s["removed"], lambda x: {"name": x["name"]}),
        "alerts": cap(s["alerts_added"],
                      lambda x: {"supplier": x["supplier"], "text": x["item"][:220],
                                 "date": x.get("date"), "url": x.get("url")}),
        "statusChanged": cap(f.get("status_changed", []),
                             lambda x: {"name": x["name"], "from": x["from"], "to": x["to"]}),
        "turnoverChanged": cap(f.get("turnover_changed", []),
                               lambda x: {"name": x["name"], "from": money(x["from"]),
                                          "to": money(x["to"]),
                                          "madeUpTo": x.get("madeUpTo")}),
    }


def selftest():
    """Prove the diff still catches what it was built for."""
    base = {"suppliers": [
        {"name": "Alpha Medical", "specialities": ["Wound"], "products": ["a"],
         "frameworks": [{"name": "FW1"}], "alerts": [], "news": []},
        {"name": "Gone Ltd", "specialities": [], "products": [],
         "frameworks": [], "alerts": [], "news": []},
        {"name": "Stryker UK Limited", "specialities": [], "products": [],
         "frameworks": [], "alerts": [], "news": []},
    ]}
    head = {"suppliers": [
        {"name": "Alpha Medical", "specialities": ["Wound", "Ortho"], "products": ["a", "b"],
         "frameworks": [{"name": "FW1"}, {"name": "FW2", "dates": "to 2028"}],
         "alerts": [{"text": "recall", "date": "2026-08-14"}], "news": []},
        {"name": "Stryker", "specialities": [], "products": [], "frameworks": [],
         "alerts": [], "news": []},
        {"name": "New Co", "specialities": ["CGM"], "products": [],
         "frameworks": [], "alerts": [], "news": []},
    ]}
    s = diff_seed(base, head)
    checks = [
        ("a new supplier is reported", [x["name"] for x in s["added"]] == ["New Co"]),
        ("a real deletion is reported", [x["name"] for x in s["removed"]] == ["Gone Ltd"]),
        ("a rename is NOT reported as a deletion",
         [x["name"] for x in s["renamed"]] == ["Stryker UK Limited"]),
        ("a gained framework is reported",
         [(x["supplier"], x["item"]) for x in s["frameworks_gained"]] == [("Alpha Medical", "FW2")]),
        ("no framework is invented", s["frameworks_lost"] == []),
        ("a new alert is reported", len(s["alerts_added"]) == 1),
        ("a speciality addition is reported",
         s["specialities_changed"][0]["added"] == ["Ortho"]),
        ("a product change is counted", s["products_changed"][0]["added"] == 1),
    ]
    fb = {"companies": {"Acme": {"companyNumber": "111", "turnoverGBP": 1000000,
                                 "matchConfidence": "probable", "status": "active"}}}
    fh = {"companies": {"Acme": {"companyNumber": "222", "turnoverGBP": 2000000,
                                 "matchConfidence": "verified", "status": "active"}}}
    f = diff_financials(fb, fh)
    checks += [
        ("a corrected company number is reported", len(f["number_changed"]) == 1),
        ("a turnover move is reported", len(f["turnover_changed"]) == 1),
        ("a confidence upgrade is reported", len(f["confidence_changed"]) == 1),
        ("an unchanged status is silent", f["status_changed"] == []),
    ]
    raw = {"seed": s, "financials": f}
    payload = brief_payload(None, None, raw, top=1)
    checks += [
        ("the briefing payload counts the gained framework",
         payload["counts"]["frameworksGained"] == 1),
        ("the briefing payload caps and SAYS it capped",
         payload["suppliersAdded"]["notListed"] == 0
         and payload["frameworksGained"]["shown"] == 1),
        ("the briefing payload has a headline", bool(payload["headline"])),
        ("housekeeping is kept out of the briefing payload",
         "specialities_changed" not in payload and "fields_changed" not in payload),
    ]

    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("  ok   " if ok else "  FAIL ") + name)
    if bad:
        print(f"\n{len(bad)} check(s) failed.")
        return 1
    print(f"\nAll {len(checks)} checks passed.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="date (2026-08-01 or 01/08/2026) or an age like 7d")
    ap.add_argument("--base", help="any git revision; overrides --since")
    ap.add_argument("--head", default=None, help="git revision (default: the working tree)")
    ap.add_argument("--supplier", help="only names containing this text")
    ap.add_argument("--limit", type=int, default=25, help="lines per section (default 25)")
    ap.add_argument("--markdown", help="write the report to this file as well")
    ap.add_argument("--json", action="store_true", help="print the raw diff as JSON instead")
    ap.add_argument("--brief", metavar="PATH",
                    help="also write the compact briefing payload here as JSON")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.base and not a.since:
        a.since = "7d"
    base_rev = resolve(a.base or a.since)
    head_rev = resolve(a.head) if a.head else None

    text, raw = build_report(base_rev, head_rev, a.supplier, a.limit)
    if a.json:
        print(json.dumps({"base": base_rev, "head": head_rev, "diff": raw},
                         indent=1, ensure_ascii=False))
    else:
        print(text)
    if a.brief:
        payload = brief_payload(base_rev, head_rev, raw)
        with open(a.brief, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print(f"\n[briefing payload written to {a.brief}: {payload['headline'] or 'nothing moved'}]",
              file=sys.stderr)
    if a.markdown:
        with open(a.markdown, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"\n[written to {a.markdown}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
