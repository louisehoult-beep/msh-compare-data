#!/usr/bin/env python3
"""Entry-level medical sales roles across the UK, built into an email for Lou.

Lou, 22/10/2026: "all entry levels roles nationally that might be a fit for people I
work with trying to get into medical sales ... emailing to me too". The people she
works with have a proven record in another industry and no medical sales experience.

Sources, all public and all UK-wide (no region filter):

  1. The employers' own careers sites: every UK role in data/supplier-careers.json
     whose TITLE reads as early career (config/careers-relevant-roles.json "entry").
  2. Job boards, where a free API key is in the macOS Keychain. Each is skipped
     quietly when its key is absent, so the digest works today on source 1 alone:
        Adzuna  service adzuna-app-id + adzuna-app-key   (developer.adzuna.com)
        Reed    service reed-api-key                      (reed.co.uk/developers)
     A board result is kept only if its title reads as early career AND the title,
     company or snippet carries a health word, so a generic graduate sales role at an
     agency never reaches Lou.

The tag is about the TITLE. The posting says what experience it asks for, and the
email says so. Nothing is invented: every row carries the company's or the board's
own link.

    python3 scripts/entry_level_digest.py                # build, print JSON, mark nothing seen
    python3 scripts/entry_level_digest.py --commit       # also record the roles as seen
"""
import argparse
import base64
import datetime
import html
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import careers_relevance as cr  # noqa: E402

DATA = os.path.join(ROOT, "data", "supplier-careers.json")
SEEN = os.path.join(ROOT, "state", "entry-digest-seen.json")
OUTDIR = os.path.join(ROOT, "state", "entry-digest")
HEALTH = ("medical", "healthcare", "health care", "pharma", "clinical", "device", "diagnostic",
          "surgical", "nhs", "life science", "biotech", "orthop", "cardio", "wound", "patient")
QUERIES = ["graduate medical sales", "trainee medical sales representative",
           "junior medical device sales", "sales development representative healthcare",
           "associate territory manager medical", "graduate pharmaceutical sales",
           "trainee clinical specialist", "medical sales graduate scheme"]


def keychain(service):
    try:
        return subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                              capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=dict({"User-Agent": "MSH-entry-digest/1.0"},
                                                    **(headers or {})))
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def health_word(*texts):
    t = " ".join(x or "" for x in texts).lower()
    return any(w in t for w in HEALTH)


def from_careers(compiled):
    doc = json.load(open(DATA, encoding="utf-8"))
    out = []
    for s in doc.get("suppliers", []):
        for r in s.get("roles") or []:
            if r.get("uk") is not True or not r.get("url"):
                continue
            if cr.classify(r.get("title"), compiled) and cr.is_entry(r.get("title"), compiled):
                out.append({"source": "Company careers site", "company": s["name"],
                            "title": r["title"], "location": r.get("location") or "",
                            "url": r["url"]})
    return out


def from_adzuna(compiled):
    app_id, app_key = keychain("adzuna-app-id"), keychain("adzuna-app-key")
    if not (app_id and app_key):
        return None
    out = []
    for q in QUERIES:
        url = ("https://api.adzuna.com/v1/api/jobs/gb/search/1?app_id=%s&app_key=%s"
               "&results_per_page=50&max_days_old=14&what=%s&content-type=application/json"
               % (app_id, app_key, urllib.parse.quote(q)))
        try:
            res = get_json(url).get("results", [])
        except Exception:
            continue
        for j in res:
            title = j.get("title") or ""
            co = (j.get("company") or {}).get("display_name") or ""
            if cr.is_entry(title, compiled) and health_word(title, co, j.get("description")):
                out.append({"source": "Adzuna", "company": co, "title": title,
                            "location": (j.get("location") or {}).get("display_name") or "",
                            "url": j.get("redirect_url")})
    return out


def from_reed(compiled):
    key = keychain("reed-api-key")
    if not key:
        return None
    auth = {"Authorization": "Basic " + base64.b64encode((key + ":").encode()).decode()}
    out = []
    for q in QUERIES:
        url = ("https://www.reed.co.uk/api/1.0/search?resultsToTake=50&postedByRecruitmentAgency=false"
               "&keywords=%s" % urllib.parse.quote(q))
        try:
            res = get_json(url, auth).get("results", [])
        except Exception:
            continue
        for j in res:
            title = j.get("jobTitle") or ""
            co = j.get("employerName") or ""
            if cr.is_entry(title, compiled) and health_word(title, co, j.get("jobDescription")):
                out.append({"source": "Reed", "company": co, "title": title,
                            "location": j.get("locationName") or "", "url": j.get("jobUrl")})
    return out


def from_medtechjobs(compiled):
    """Medical Technology Jobs' public JSON feed (CC BY 4.0, link back required).

    No key needed. It carries only the latest handful of vacancies, so it is a
    supplement, not the main source. Titles arrive as 'Role · Company · Location'."""
    try:
        items = get_json("https://medicaltechnologyjobs.co.uk/jobs.json").get("items", [])
    except Exception:
        return None
    out = []
    for j in items:
        parts = [x.strip() for x in (j.get("title") or "").split("·")]
        title = parts[0]
        if cr.is_entry(title, compiled) and cr.classify(title, compiled):
            out.append({"source": "Medical Technology Jobs", "title": title,
                        "company": parts[1] if len(parts) > 1 else "",
                        "location": parts[2] if len(parts) > 2 else "", "url": j.get("url")})
    return out


def load_seen():
    try:
        return set(json.load(open(SEEN)).get("urls", []))
    except Exception:
        return set()


def build_html(rows, skipped, today):
    e = html.escape
    items = "".join(
        '<tr><td style="padding:10px 14px;border-bottom:1px solid #D8DEE6;">'
        '<a href="%s" style="color:#0B1C33;font-weight:700;text-decoration:underline;">%s</a><br>'
        '<span style="color:#1D2733;font-size:14px;">%s%s &middot; <i>%s</i></span></td></tr>'
        % (e(r["url"], quote=True), e(r["title"]), e(r["company"]),
           (", " + e(r["location"])) if r["location"] else "", e(r["source"]))
        for r in sorted(rows, key=lambda r: (r["company"].lower(), r["title"])))
    note = ""
    if skipped:
        note = ('<p style="color:#1D2733;font-size:14px;">Not read today (no key yet): %s.</p>'
                % e(", ".join(skipped)))
    if any(r["source"] == "Medical Technology Jobs" for r in rows):
        note += ('<p style="color:#1D2733;font-size:13px;">Some roles from '
                 '<a href="https://medicaltechnologyjobs.co.uk" style="color:#0B1C33;">Medical Technology Jobs</a> (CC BY 4.0).</p>')
    return (
        '<div style="background:#EDE7DC;padding:24px 0;font-family:Arial,Helvetica,sans-serif;">'
        '<table role="presentation" width="100%%" style="max-width:720px;margin:0 auto;background:#FFFFFF;">'
        '<tr><td style="background:#0B1C33;padding:22px 24px;">'
        '<div style="color:#E0BE8E;font-size:13px;letter-spacing:2px;">ENTRY-LEVEL MEDICAL SALES ROLES</div>'
        '<div style="color:#FFFFFF;font-size:24px;font-weight:700;">%d new UK role%s, %s</div></td></tr>'
        '<tr><td style="padding:18px 24px;color:#1D2733;font-size:15px;">'
        'Roles whose job title reads as early career (graduate, trainee, junior, associate, sales '
        'development) in medical sales and clinical specialist work, anywhere in the UK. '
        'The title is a guide only: open each posting to see what experience it asks for. Many welcome a '
        'proven sales record from another industry.%s</td></tr>'
        '<tr><td><table role="presentation" width="100%%">%s</table></td></tr></table></div>'
        % (len(rows), "" if len(rows) == 1 else "s", today.strftime("%d/%m/%Y"), note, items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="record these roles as seen")
    a = ap.parse_args()
    compiled = cr.load_config()
    rows, skipped = from_careers(compiled), []
    for name, fn in (("Medical Technology Jobs", from_medtechjobs),
                     ("Adzuna", from_adzuna), ("Reed", from_reed)):
        got = fn(compiled)
        if got is None:
            skipped.append(name)
        else:
            rows += got
    seen = load_seen()
    uniq, urls = [], set()
    for r in rows:
        if r["url"] and r["url"] not in seen and r["url"] not in urls:
            urls.add(r["url"])
            uniq.append(r)
    today = datetime.date.today()
    result = {"new": len(uniq), "total_read": len(rows), "boardsWithoutKey": skipped,
              "html": None, "subject": None}
    if uniq:
        os.makedirs(OUTDIR, exist_ok=True)
        path = os.path.join(OUTDIR, today.isoformat() + ".html")
        open(path, "w", encoding="utf-8").write(build_html(uniq, skipped, today))
        result.update(html=path, subject="Entry-level medical sales roles: %d new, %s"
                      % (len(uniq), today.strftime("%d/%m/%Y")))
    if a.commit and uniq:
        os.makedirs(os.path.dirname(SEEN), exist_ok=True)
        json.dump({"urls": sorted(seen | urls)}, open(SEEN, "w"), indent=1)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
