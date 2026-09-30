#!/usr/bin/env python3
"""ICB watch — how many Integrated Care Boards exist, which are clustering or
merging, who leads them, and what has changed. Feeds the NHS structure page
(WP 884, via app/icb-watch.js) and the Live Desk (WP 675, via the pipeline's
`icb_watch` source, which reads the `events` list of data/icb-watch.json).

WHY IT EXISTS (30/09/2026)
--------------------------
Aneeka Hussain (National Market Access Manager, Ego Pharmaceuticals UK) asked
the Hub for ICB alerts: "Birmingham and Solihull have finished their
redundancies, and now this is the new chief [pharmacist]". The Hub had no such
feed. people-moves.json (private repo) only ever tracked trust PROCUREMENT
contacts on Find a Tender notices; nothing watched ICB executives, and the NHS
structure page carried a hand-typed "~26 ICBs expected by 2027" that no NHS
England source states.

FOUR SOURCES, EACH READ FOR THE ONE THING IT IS AUTHORITATIVE ON
----------------------------------------------------------------
1. NHS ODS (ORD API, RO261) — which ICBs legally exist. Liveness is a LEGAL
   END DATE, never Status (ODS keeps abolished ICBs at Status:Active for
   ever; a naive query returns 48). An ICB carrying a legal end date in the
   future is the earliest hard signal that a merger Order has been made, and
   is published as an event. An ICB code that is live in ODS but unknown to
   ICB (scripts/refresh_trusts.py) makes verify.py fail on purpose: that is
   the April 2027 round landing, and a person must update the region map.
2. NHS England "More about each integrated care system" — clusters, Chair,
   Chief Executive, and whether either is interim/acting. Structured text,
   parsed line by line.
3. NHS England "Integrated care in your area" — the national statement on
   future mergers. Stored verbatim; a change in the wording is an event (that
   is how a decision on the 2027 footprints will first show up).
4. Each ICB's own leadership/board page (config/icb-leadership-sources.json)
   — named executives by title, in particular the medicines lead (chief
   pharmacist / chief pharmacy officer / director of medicines optimisation),
   the chief medical officer and the chief executive. Only person–title pairs
   read off the page are stored; nothing is inferred.

PLUS curated, human-verified events (config/icb-watch-curated.json) for facts
that live only in board-paper PDFs or committee minutes — e.g. a redundancy
business case approval. Each carries its source URLs and the date it was
verified; verify.py refuses one without them.

CHANGE DETECTION — FROM STORED STATE, NEVER FROM ONE SCAN'S ORDER
------------------------------------------------------------------
The 24/07/2026 incident (145 false job changes about named NHS staff) came
from diffing one run against another. Here a leadership change is emitted only
when (a) a previous observation of that ICB and role is already stored, (b) the
new holder differs, and (c) the new holder has now been read on two runs on
different days (the first sighting is held in `pending`). A role that simply
stops being found (page redesign, fetch failure) is NEVER reported as a
departure — it is kept as last seen and flagged `stale` after 14 days. The
first ever run stores a baseline and emits no leadership events at all.

Nothing here carries an email address or phone number (verify.py's
personal-contact gate would refuse it). Names and job titles of ICB board
members and executives, as each ICB and NHS England publish them, are the
public-record facts the feature is built on.

USAGE
    python3 scripts/refresh_icb_watch.py              # full refresh
    python3 scripts/refresh_icb_watch.py --no-pages   # skip ICB own-site pages
Stdlib only.
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from refresh_trusts import ICB as ICB_REGION          # noqa: E402  code -> (name, region)

OUT = os.path.join(REPO, "data", "icb-watch.json")
PAGES_CFG = os.path.join(REPO, "config", "icb-leadership-sources.json")
CURATED_CFG = os.path.join(REPO, "config", "icb-watch-curated.json")

ODS_LIST = ("https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations"
            "?PrimaryRoleId=RO261&Limit=1000")
NHSE_LEADERS = ("https://www.england.nhs.uk/integratedcare/integrated-care-in-your-area/"
                "more-about-each-integrated-care-system/")
NHSE_AREA = "https://www.england.nhs.uk/integratedcare/integrated-care-in-your-area/"
# A full browser user-agent: eight ICB sites (Staffordshire, Central East, Essex,
# Norfolk and Suffolk, South West London, BSW, Devon, Somerset) answer 403 to a
# bare "Mozilla/5.0" but serve the same public page to a normal browser string.
UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"),
      "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-GB,en;q=0.9"}

EVENT_KEEP_DAYS = 180
STALE_DAYS = 14

# Role families a market-access or device rep cares about. Order matters: the
# first family whose pattern matches a title wins, so "Deputy Chief Medical
# Officer" must be excluded explicitly (deputies are not the role holder).
ROLE_FAMILIES = [
    ("medicines", re.compile(
        r"chief pharmac|pharmacy officer|director of (medicines|pharmacy)|"
        r"medicines optimisation|medicines management|director of medicines", re.I)),
    ("cmo", re.compile(r"chief medical officer|\bmedical director\b|\(medical\)", re.I)),
    ("ceo", re.compile(r"chief executive", re.I)),
    ("cfo", re.compile(r"chief financ\w*( and [\w ]+)? officer|director of finance", re.I)),
    ("nursing", re.compile(r"chief nurs|director of nursing|chief (clinical|quality)", re.I)),
    ("chair", re.compile(r"^(interim |acting )?chair(man|woman|person)?$", re.I)),
]
OWN_SITE_FAMILIES = {"medicines", "cmo", "cfo", "nursing"}
ROLE_LABEL = {"medicines": "Medicines lead", "cmo": "Medical leadership",
              "ceo": "Chief executive", "cfo": "Chief finance officer",
              "nursing": "Chief nurse / clinical and quality", "chair": "Chair"}
NOT_HOLDER = re.compile(r"\b(deputy|associate|assistant|interim deputy|support(s|ing)?|"
                        r"office of|pa to|to the)\b", re.I)
# A partner member's title names their OWN organisation ("Chief Executive of
# Birmingham Community Healthcare NHS Foundation Trust", "Group Chief Executive
# at University Hospitals Birmingham"). They sit on the ICB board but do not run
# the ICB, so they are not the ICB's executive and never raise an ICB event.
PARTNER = re.compile(r"\b(at|of)\s+(?!the ICB\b|Medicines\b|Pharmacy\b|Finance\b|Nursing\b|"
                     r"Strategy\b|Clinical\b|Primary Care\b|Medicines and\b)|Trust\b|Council\b|"
                     r"Foundation\b|Practice\b|Partnership\b|University\b|Hospital", re.I)
HONORIFIC = r"(?:(?:Dr|Prof(?:essor)?|Mr|Mrs|Ms|Miss|Sir|Dame|Cllr|Councillor)\.?\s+)?"
NAMEPART = r"[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿA-ZÀ-ÖØ-Þ'’\-]+"
POSTNOM = r"(?:,?\s+(?:OBE|MBE|CBE|DL|FRPharmS|FRCGP|FRCP|MRCGP|CB|KBE|DBE))*"
PERSON_RE = re.compile(r"^" + HONORIFIC + NAMEPART + r"(?:\s+" + NAMEPART + r"){1,3}" + POSTNOM + r"$")
NOT_A_NAME = re.compile(r"\b(Chief|Director|Officer|Board|Committee|Member|Members|Executive|"
                        r"Integrated|Care|NHS|Council|Trust|Partnership|Primary|Clinical|"
                        r"Medical|Nursing|Finance|Strategy|Team|Our|Meet|About|Read|More|"
                        r"Chair|Vice|Non|Partner|Governance|Leadership|Health|System)\b")


def today():
    return dt.date.today()


def iso(d):
    return d.isoformat()


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def page_lines(raw):
    """HTML -> list of visible text lines (block elements become breaks)."""
    t = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>", " ", raw)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|td|tr|dt|dd|span|a|strong|b)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    out = []
    for ln in t.split("\n"):
        ln = re.sub(r"\s+", " ", ln).strip(" |•·-–—")
        if ln:
            out.append(ln)
    return out


def norm_icb_name(s):
    s = s.upper().replace("&", "AND")
    s = re.sub(r"\bNHS\b|\bINTEGRATED CARE BOARD\b|\bICB\b|\bTHE\b", " ", s)
    return re.sub(r"[^A-Z]+", " ", s).strip()


# ---------------------------------------------------------------- 1. ODS
def ods_icbs():
    orgs = json.loads(fetch(ODS_LIST))["Organisations"]

    def detail(o):
        r = json.loads(fetch(o["OrgLink"], timeout=30))["Organisation"]
        legal = [d for d in r.get("Date", []) if d.get("Type") == "Legal"]
        return {"code": o["OrgId"], "odsName": o["Name"],
                "legalStart": legal[0].get("Start") if legal else None,
                "legalEnd": legal[0].get("End") if legal else None}

    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(detail, orgs))
    t = iso(today())
    icbs = [r for r in rows if "INTEGRATED CARE BOARD" in r["odsName"].upper()]
    live = [r for r in icbs if not r["legalEnd"] or r["legalEnd"] > t]
    ended = [r for r in icbs if r["legalEnd"] and r["legalEnd"] <= t]
    if len(live) < 20:
        raise SystemExit("ODS returned only %d live ICBs — refusing to publish a shrunken list."
                         % len(live))
    return live, ended


# ---------------------------------------------------------------- 2. NHSE leaders
LEADER_RE = re.compile(r"^(Interim |Acting )?(Chair|CEO|Chief Executive)\s*:\s*(.+)$", re.I)


def nhse_leaders():
    raw = fetch(NHSE_LEADERS)
    lines = page_lines(raw)
    updated = None
    for ln in lines:
        m = re.search(r"Information last updated:\s*(\d{1,2} \w+ \d{4})", ln)
        if m:
            updated = dt.datetime.strptime(m.group(1), "%d %B %Y").date().isoformat()
    # Leaders sit below "Find your local integrated care system leadership".
    try:
        start = next(i for i, ln in enumerate(lines) if "Find your local integrated care system" in ln)
    except StopIteration:
        raise SystemExit("NHS England leaders page changed shape — no 'Find your local integrated "
                         "care system leadership' heading. Refusing to guess.")
    blocks, cur = {}, None
    for ln in lines[start:]:
        m = re.match(r"^(?:NHS )?(.+?) (?:ICB|Integrated Care Board)$", ln)
        if m and len(ln) < 90 and ":" not in ln:
            cur = norm_icb_name(m.group(1))
            blocks[cur] = {"leaders": [], "clusterNote": None}
            continue
        if cur is None:
            continue
        lm = LEADER_RE.match(ln)
        if lm:
            qual = (lm.group(1) or "").strip().lower() or None
            role = "chair" if lm.group(2).lower() == "chair" else "ceo"
            name = lm.group(3).strip()
            if name.lower() in ("vacant", "to be confirmed", "tbc"):
                name = None
            blocks[cur]["leaders"].append({"role": role, "name": name, "qualifier": qual})
        elif ln.startswith("Clustering with"):
            blocks[cur]["clusterNote"] = ln.rstrip(".") + "."
    if len(blocks) < 30:
        raise SystemExit("NHS England leaders page parsed to only %d ICB blocks — refusing."
                         % len(blocks))
    return blocks, updated


# ---------------------------------------------------------------- 3. NHSE statement
def nhse_statement():
    lines = page_lines(fetch(NHSE_AREA))
    keep = [ln for ln in lines if not ln.lower().startswith("outlines") and re.search(
        r"new ICBs were established|clustering arrangements|future decisions on ICB footprints|"
        r"clustering ICBs remain separate", ln, re.I)]
    # The page breaks one sentence across a link; rejoin runs of short fragments.
    text = " ".join(keep)
    text = re.sub(r"\s+", " ", text).strip()
    if "Six new ICBs" not in text and "future decisions" not in text:
        raise SystemExit("NHS England 'integrated care in your area' wording not found — refusing "
                         "to publish a merger statement that was not read.")
    return {"url": NHSE_AREA, "text": text,
            "hash": hashlib.sha256(text.encode()).hexdigest()[:16]}


# ---------------------------------------------------------------- 4. ICB own pages
OWN_ORG_SUFFIX = re.compile(r"ICB|Integrated Care Board|Directorate|Director|Officer|Medicines|"
                            r"Clinical|Policy|Quality|Nursing|Medical|Finance|Interim|Acting|"
                            r"Accountable|Joint|Pharmacy|Primary Care|\(", re.I)


def role_family(title):
    if NOT_HOLDER.search(title) or PARTNER.search(title):
        return None
    # "Chief Executive, Sirona care & health" / "Chief Executive, G DOC": a
    # partner member whose own organisation follows the comma.
    if "," in title:
        suffix = title.split(",", 1)[1].strip()
        if suffix and not OWN_ORG_SUFFIX.search(suffix):
            return None
    fams = [fam for fam, rx in ROLE_FAMILIES if rx.search(title)]
    # "Chair and Chief Executive Officer" is a section heading, not a job title.
    if len(set(fams)) > 1 and re.search(r"\band\b", title, re.I) and not re.search(
            r"medicines|pharmac", title, re.I):
        return None
    return fams[0] if fams else None


def looks_like_person(s):
    s = s.strip()
    return (bool(PERSON_RE.match(s)) and not NOT_A_NAME.search(s) and len(s) <= 60
            and not s.startswith("The "))


def extract_people(lines):
    """Person–title pairs read directly off a page. Three layouts, all seen on
    ICB sites: 'Name, Title' on one line; 'Name' then 'Title' on the next
    line; 'Title' then 'Name'. Only a line that is plainly a job title (a role
    family matches, short) is paired, and only with a line that is plainly a
    person's name. Anything else is ignored rather than guessed."""
    found, pairs = [], []
    for i, ln in enumerate(lines):
        if len(ln) > 160:
            continue
        # "Nominated ICB Executive: Rosi Shepherd – Chief ..." — drop the label.
        one = re.sub(r"^[A-Z][\w ]{2,40}:\s+", "", ln)
        # One-line forms: "Hemant Patel, Chief Pharmacy Officer, Director of ..."
        # and "Chief executive - Aaron Cummins" / "... Joint Chief Medical Officer – Bernie Marden".
        m = re.match(r"^(" + HONORIFIC + NAMEPART + r"(?:\s+" + NAMEPART + r"){1,3}" + POSTNOM
                     + r")\s*(?:,|\s[–—\-])\s+(.+)$", one)
        if m and looks_like_person(m.group(1)) and role_family(m.group(2)):
            found.append((m.group(1).strip(), m.group(2).strip()))
            continue
        m = re.match(r"^(.+?)\s+[–—\-]\s+(" + HONORIFIC + NAMEPART + r"(?:\s+" + NAMEPART
                     + r"){1,3}" + POSTNOM + r")$", one)
        if m and looks_like_person(m.group(2)) and role_family(m.group(1)):
            found.append((m.group(2).strip(), m.group(1).strip()))
            continue
        fam = role_family(ln)
        if not fam or looks_like_person(ln):
            continue
        prev = lines[i - 1] if i else ""
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        pairs.append((i, ln, prev if looks_like_person(prev) else None,
                      nxt if looks_like_person(nxt) else None))
    # Each site uses ONE layout for its two-line cards. Decide it from the
    # UNAMBIGUOUS pairs only (a title with a name on exactly one side) and pair
    # the ambiguous ones (names both sides, i.e. inside a run of cards) the same
    # way; with no unambiguous pair, name-then-title, the commoner layout. So a
    # section heading sitting above a name is never taken for that person's title.
    before = sum(1 for _, _, p, n in pairs if p and not n)
    after = sum(1 for _, _, p, n in pairs if n and not p)
    for _, title, p, n in pairs:
        who = p if (p and not n) else n if (n and not p) else (p if before >= after else n)
        if who:
            found.append((who.strip(), title))
    seen, out = set(), []
    for name, title in found:
        bare = re.sub(r"^" + HONORIFIC, "", name).lower()
        bare = re.sub(r",?\s+(obe|mbe|cbe|dl|cb)\b", "", bare)
        key = (bare, role_family(title))
        if key not in seen:
            seen.add(key)
            out.append({"name": name, "title": title[:160], "family": role_family(title)})
    # Chair and chief executive come from NHS England's list, which is
    # authoritative for them; an ICB board page also carries partner members'
    # chief executives, which must never read as the ICB's own.
    return [p for p in out if p["family"] in OWN_SITE_FAMILIES]


def own_site_people(cfg):
    results = {}

    def one(code, url):
        try:
            return code, url, extract_people(page_lines(fetch(url))), None
        except Exception as e:                                   # noqa: BLE001
            return code, url, None, "%s" % e.__class__.__name__

    jobs = [(code, p["url"]) for code, spec in cfg.get("icbs", {}).items()
            for p in spec.get("pages", [])]
    with concurrent.futures.ThreadPoolExecutor(6) as ex:
        for code, url, people, err in ex.map(lambda a: one(*a), jobs):
            r = results.setdefault(code, {"people": [], "errors": [], "urls": []})
            r["urls"].append(url)
            if err:
                r["errors"].append({"url": url, "error": err})
            else:
                for p in people:
                    p["url"] = url
                    r["people"].append(p)
    return results


# ---------------------------------------------------------------- state + events
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def event(date, code, kind, headline, detail, urls, role=None):
    ev = {"date": date, "icb": code, "kind": kind, "headline": headline,
          "detail": detail, "sources": urls}
    if role:
        ev["role"] = role
    ev["id"] = hashlib.sha256(("%s|%s|%s" % (code, kind, headline)).encode()).hexdigest()[:12]
    return ev


def display_name(code, ods_name):
    if code in ICB_REGION:
        return "NHS %s Integrated Care Board" % ICB_REGION[code][0]
    return ods_name.title().replace("Nhs ", "NHS ").replace(" And ", " and ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pages", action="store_true", help="skip each ICB's own site")
    args = ap.parse_args()

    prev = load_json(OUT, {})
    live, ended = ods_icbs()
    leaders, leaders_updated = nhse_leaders()
    statement = nhse_statement()
    page_cfg = load_json(PAGES_CFG, {"icbs": {}})
    own = None if args.no_pages else own_site_people(page_cfg)
    curated = load_json(CURATED_CFG, {"events": []}).get("events", [])
    doc, new_count = build(prev, live, ended, leaders, leaders_updated, statement, own,
                           curated, today())
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    icbs_out = doc["icbs"]
    n_exec = sum(len(i["execs"]) for i in icbs_out)
    n_med = sum(1 for i in icbs_out if any(e["family"] == "medicines" for e in i["execs"]))
    print("icb-watch: %d live ICBs, %d clusters, %d executives read, medicines lead named for "
          "%d ICBs, %d events (%d new this run), %d pending"
          % (len(icbs_out), len(doc["clusters"]), n_exec, n_med, len(doc["events"]),
             new_count, len(doc["pending"])))


def build(prev, live, ended, leaders, leaders_updated, statement, own, curated, t):
    """Pure: stored state + today's reads -> the new document. `own` is None
    when own-site pages were not read this run (their stored values are kept)."""
    prev_icbs = {i["code"]: i for i in prev.get("icbs", [])}
    prev_pending = prev.get("pending", {})
    events = [e for e in prev.get("events", []) if e.get("kind") != "curated"]
    tiso = iso(t)
    new_events = []
    own = own if own is not None else {}
    statement = dict(statement)

    icbs_out, pending = [], {}
    for r in sorted(live, key=lambda x: x["code"]):
        code = r["code"]
        name = display_name(code, r["odsName"])
        region = ICB_REGION.get(code, (None, None))[1]
        p = prev_icbs.get(code, {})
        blk = leaders.get(norm_icb_name(r["odsName"]), {"leaders": [], "clusterNote": None})
        rec = {"code": code, "name": name, "region": region,
               "legalStart": r["legalStart"], "legalEnd": r["legalEnd"],
               "cluster": blk["clusterNote"],
               "leaders": blk["leaders"],
               "leadersSource": NHSE_LEADERS,
               "execs": [], "execSources": [], "fetchErrors": []}

        # A legal end date appearing is the Order being made — the hard signal.
        if r["legalEnd"] and not p.get("legalEnd") and p:
            new_events.append(event(tiso, code, "legal-end",
                "%s: NHS records a legal end date of %s" % (name, dt.date.fromisoformat(
                    r["legalEnd"]).strftime("%d/%m/%Y")),
                "The NHS Organisation Data Service now records that this ICB legally ends on "
                "%s, which is how an establishment and abolition Order shows up in the "
                "register before the merger takes effect." % r["legalEnd"],
                ["https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations/%s" % code]))
        if not p and prev_icbs:
            new_events.append(event(tiso, code, "new-icb",
                "%s appears in the NHS register as a live ICB" % name,
                "A new ICB code is live in the NHS Organisation Data Service.",
                ["https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations/%s" % code]))

        # Chair / CEO from NHS England, compared with what was stored.
        prev_lead = {(x["role"]): x for x in p.get("leaders", [])}
        for x in blk["leaders"]:
            old = prev_lead.get(x["role"])
            if old is None or not x.get("name"):
                continue
            changed_name = (old.get("name") or "") != x["name"]
            changed_qual = (old.get("qualifier") or None) != (x.get("qualifier") or None)
            if changed_name or changed_qual:
                key = "%s|%s|%s|%s" % (code, x["role"], x["name"], x.get("qualifier"))
                first = prev_pending.get(key)
                if first and first < tiso:
                    label = ("%s %s" % (x["qualifier"].capitalize(), ROLE_LABEL[x["role"]].lower())
                             if x.get("qualifier") else ROLE_LABEL[x["role"]])
                    was = old.get("name") or "vacant"
                    new_events.append(event(tiso, code, "leadership",
                        "%s: %s is now %s (was %s)" % (name, label, x["name"], was),
                        "NHS England's list of ICB leaders now shows %s as %s, where it "
                        "previously showed %s%s." % (x["name"], label.lower(), was,
                            " (%s)" % old["qualifier"] if old.get("qualifier") else ""),
                        [NHSE_LEADERS], role=x["role"]))
                else:
                    pending[key] = first or tiso
                    x_keep = dict(old)            # hold the old value until confirmed
                    rec["leaders"] = [x_keep if y is x else y for y in rec["leaders"]]

        # Executives from the ICB's own site.
        o = own.get(code)
        rec["execSources"] = (o or {}).get("urls") or p.get("execSources", [])
        if o is None:
            rec["execs"] = p.get("execs", [])
        else:
            rec["fetchErrors"] = o["errors"]
            prev_exec = {(e["family"], e["name"].lower()): e for e in p.get("execs", [])}
            prev_by_family = {}
            for e in p.get("execs", []):
                prev_by_family.setdefault(e["family"], []).append(e)
            seen_now = {}
            for person in o["people"]:
                k = (person["family"], person["name"].lower())
                old = prev_exec.get(k)
                person["firstSeen"] = old["firstSeen"] if old else tiso
                person["lastSeen"] = tiso
                seen_now[k] = person
            # Keep what was not re-read (never report a disappearance).
            for k, e in prev_exec.items():
                if k not in seen_now:
                    e = dict(e)
                    if e.get("lastSeen") and (t - dt.date.fromisoformat(e["lastSeen"])).days > STALE_DAYS:
                        e["stale"] = True
                    seen_now[k] = e
            # New holder of a family that already had a DIFFERENT stored holder.
            for (fam, lname), person in list(seen_now.items()):
                if person.get("firstSeen") != tiso or fam not in prev_by_family:
                    continue
                if any(pe["name"].lower() == lname for pe in prev_by_family[fam]):
                    continue
                key = "%s|exec|%s|%s" % (code, fam, lname)
                first = prev_pending.get(key)
                if first and first < tiso:
                    was = ", ".join(sorted({pe["name"] for pe in prev_by_family[fam]}))
                    new_events.append(event(tiso, code, "leadership",
                        "%s: %s now listed as %s" % (name, person["name"], person["title"]),
                        "The ICB's own leadership page now lists %s as %s. Previously "
                        "listed in this role family: %s." % (person["name"], person["title"], was),
                        [person["url"]], role=fam))
                else:
                    pending[key] = first or tiso
                    # Not yet confirmed: hold it out of the published list.
                    del seen_now[(fam, lname)]
            # A first-seen person in a family with no previous holder is coverage,
            # not a change: it is published but raises no event.
            rec["execs"] = sorted(seen_now.values(),
                                  key=lambda e: ([f for f, _ in ROLE_FAMILIES].index(e["family"]),
                                                 e["name"]))
        icbs_out.append(rec)

    # National statement change.
    old_stmt = prev.get("nationalStatement") or {}
    if old_stmt.get("hash") and old_stmt["hash"] != statement["hash"]:
        new_events.append(event(tiso, None, "national",
            "NHS England has changed its published statement on ICB mergers",
            "New wording: “%s”" % statement["text"][:600], [NHSE_AREA]))
    statement["checkedOn"] = tiso
    statement["firstSeen"] = (old_stmt.get("firstSeen") if old_stmt.get("hash") == statement["hash"]
                              else tiso)

    # Curated, human-verified events from board papers and minutes.
    for c in curated:
        ev = event(c["date"], c.get("icb"), "curated", c["headline"], c["detail"], c["sources"],
                   role=c.get("role"))
        ev["verifiedOn"] = c["verifiedOn"]
        if c.get("alsoIcbs"):
            ev["alsoIcbs"] = list(c["alsoIcbs"])
        new_events.append(ev)

    # Merge, de-duplicate by id, age out.
    by_id = {e["id"]: e for e in events}
    for e in new_events:
        by_id.setdefault(e["id"], e)
    cutoff = iso(t - dt.timedelta(days=EVENT_KEEP_DAYS))
    events = sorted((e for e in by_id.values() if e["date"] >= cutoff),
                    key=lambda e: (e["date"], e["id"]), reverse=True)

    # Clusters, from each ICB's own "Clustering with X ICB; and with Y ICB." note.
    # Partner names are matched EXACTLY after normalising. A substring match put
    # Somerset in the Bristol cluster ("North SOMERSET"), which is why not.
    by_norm = {norm_icb_name(o["name"]): o["code"] for o in icbs_out}
    clusters = {}
    for rec in icbs_out:
        if not rec["cluster"]:
            continue
        body = re.sub(r"^Clustering with\s+", "", rec["cluster"]).rstrip(".")
        partners = [norm_icb_name(x) for x in re.split(r";?\s*and with\s+|;\s*", body) if x.strip()]
        codes = [by_norm.get(x) for x in partners]
        if None in codes:
            raise SystemExit("Could not resolve cluster partner(s) %r for %s — refusing to "
                             "publish a guessed cluster." % (partners, rec["code"]))
        members = sorted([rec["code"]] + codes)
        clusters[tuple(members)] = members
    doc = {
        "_notice": prev.get("_notice"),
        "asOf": t.strftime("%d/%m/%Y"),
        "generated": tiso,
        "note": ("ICB count from the NHS Organisation Data Service (legal end date, not status). "
                 "Clusters, Chairs and Chief Executives from NHS England's list of ICB leaders. "
                 "Executives from each ICB's own leadership page. Leadership events are "
                 "derived from stored observations: a new holder must be read on two runs on "
                 "different days, and a role that stops being found is never reported as a "
                 "departure. Curated events were verified by hand against the named board "
                 "papers or minutes on the date shown."),
        "count": len(icbs_out),
        "countSource": "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations?PrimaryRoleId=RO261",
        "abolished": [{"code": e["code"], "name": display_name(e["code"], e["odsName"]),
                       "legalEnd": e["legalEnd"]} for e in ended
                      if e["legalEnd"] >= "2026-01-01"],
        "clusters": sorted(clusters.values()),
        "leadersUpdated": leaders_updated,
        "nationalStatement": statement,
        "icbs": icbs_out,
        "events": events,
        "pending": pending,
    }
    if doc["_notice"] is None:
        del doc["_notice"]
    doc["abolished"] = sorted(doc["abolished"], key=lambda x: x["code"])
    return doc, len([e for e in new_events if e["kind"] != "curated"])


if __name__ == "__main__":
    main()
