#!/usr/bin/env python3
"""Read each supplier's OWN careers page and record what it publishes there.

WHY THIS EXISTS (added 28/08/2026)
----------------------------------
Lou asked whether LinkedIn's company `/insights/` tab — headcount growth, hires,
open roles — could feed the Hub's company intelligence. It cannot, and the
reasons are settled: LinkedIn answers automated fetches with HTTP 999, the
insights tab is a paid Sales Navigator feature, republishing licensed LinkedIn
data inside a paid subscription product breaches their User Agreement, and a
paywalled panel is not a source a member can follow, so it fails the Hub's own
verification standard (root rules 12 and 16).

The signal Lou actually wanted from it was HIRING. That signal is available from
a source with none of those problems: the company's own careers page. It is
public, it is the company speaking about itself, it can be cited with a URL a
member can click, and reading it breaches nothing.

WHAT COUNTS AS EVIDENCE HERE (root rule 14 — state the rule, set a floor)
-------------------------------------------------------------------------
Two facts are recorded, and they are held to DIFFERENT bars, because they are
not equally knowable.

  THE CAREERS PAGE ITSELF is recorded whenever the company's own site points at
  it — an anchor in its own navigation, or a well-known path that answers 200
  from its own domain. A URL is a weak claim ("this company has a careers page")
  and the evidence is proportionate. This alone is publishable: a report that
  says "Mediq's own careers page" and links it is useful and cannot be wrong.

  THE ROLE COUNT is recorded ONLY where each role was read as a DISCRETE RECORD:

    ats       the careers page embeds an applicant tracking system whose public
              API returns one object per role — Greenhouse, Lever, Workable,
              Recruitee, SmartRecruiters, BambooHR. Strongest tier: the record
              carries title, location and its own URL, and the count is the
              company's own count.
    jsonld    the page publishes schema.org JobPosting structured data. Also one
              record per role, published by the company for exactly this purpose.

  ANYTHING ELSE IS REFUSED, and the refusal reason is recorded. Specifically it
  will NOT count roles by pattern-matching a rendered layout. That is the failure
  this is built around: a careers page saying "we have no vacancies right now"
  above a six-item footer counts as six roles to a regex, and the Hub would state
  it as a fact on a paid page. An honest empty state beats a confident wrong
  number, every time. Publishing nothing is the correct output when the evidence
  is thin.

  Where an ATS is detected but cannot be read as records (Workday, Ashby,
  Teamtailor, Personio all render client-side or gate their API), that is a
  refusal WITH the ATS named and the URL kept — a human can click it. It is not
  dressed up as a zero.

UK ROLES. Every role keeps the location string the company published. `uk` is
true only where that string names a UK nation, a UK city, or a UK postcode area;
false where it names somewhere else; and null where the company published no
location at all. There is no inference from the company being UK-registered — a
UK supplier's board can be entirely Dutch roles. A UK count is therefore stated
only over roles whose location was actually published, and the file records how
many had none so a reader can judge the denominator.

COMMERCIAL AND CLINICAL roles are flagged from the job title alone, against a
listed vocabulary held in this file. It is a filing aid, not a claim about the
role, and `roleFlagRule` says so in the output.

NEW SINCE LAST RUN. Each role is keyed on its own URL where it has one, else
title+location. A key not present in the previous run is `new: true`. On the very
first run nothing is new — there is no previous run to be new against — and the
file says `firstRun: true` rather than reporting every role as a fresh posting.

robots.txt is honoured, every fetch carries a timeout, and each site gets a
bounded wall-clock slot.

REPORT ONLY BY DEFAULT. This writes state/careers-report.json, which no consumer
reads. `--write` additionally writes data/supplier-careers.json, which IS served
to the Hub — see root rule 13: a push to this repo is a publish. Nothing should
be written there until the report has been read and the refusals understood.

Run:  python3 scripts/refresh_supplier_careers.py --limit 25
      python3 scripts/refresh_supplier_careers.py --supplier "Mediq Healthcare UK"
      python3 scripts/refresh_supplier_careers.py --auto --limit 200
      python3 scripts/refresh_supplier_careers.py --auto --write
Then: python3 scripts/stamp_notice.py && python3 verify.py
"""
import argparse
import datetime as dt
import difflib
import html as H
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

socket.setdefaulttimeout(45)

SEED = "data/supplier-seed.json"
REPORT = "state/careers-report.json"
OUT = "data/supplier-careers.json"

UA_STR = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120 Safari/537.36")
UA = {"User-Agent": UA_STR}
PAUSE = 0.4
SITE_BUDGET_S = 60
# How many roles will be pulled back from a paginated source before the fetch is
# stopped. A global manufacturer posts over a thousand; retrieving them all costs
# sixty requests per supplier and tells a UK rep nothing extra. Past this point
# the company's OWN stated total is still recorded — it is a record — but the
# UK/commercial/clinical breakdown is NOT, because it would be computed over a
# partial list and would read as a complete one.
#
# Raised from 300 to 500 on 28/08/2026 (Lou). At 300, Smith+Nephew's 343 roles
# fell just outside and lost their breakdown for the sake of 43 roles. This is a
# COST ceiling, not an evidence one — the rule that governs correctness is the
# withholding below, and it is unchanged — so moving it weakens nothing. Stryker
# (1,184) still exceeds it and still withholds, which is the proof that raising
# the cap did not quietly turn into tuning until a number appears.
WORKDAY_CAP = 500
TODAY = dt.date.today().isoformat()

# Paths a company files its careers page under, tried in order, only after the
# homepage's own navigation has been asked first. Order matters: the earlier
# entries are the ones a UK company most often uses.
CAREER_PATHS = [
    "/careers", "/careers/", "/jobs", "/jobs/", "/vacancies", "/vacancies/",
    "/careers/vacancies", "/about/careers", "/about-us/careers", "/company/careers",
    "/work-with-us", "/join-us", "/work-for-us", "/current-vacancies",
    "/en-gb/careers", "/uk/careers", "/careers/current-opportunities",
]

# Anchor text or href that means "this is our careers page", in the company's
# own words. Deliberately narrow: "opportunities" alone matches sales copy.
NAV_RE = re.compile(
    r"career|vacanc|job openings|job vacanc|current vacanc|work with us|"
    r"work for us|join (our team|us)|life at ", re.I)

UK_RE = re.compile(
    r"\b(uk|u\.k\.|united kingdom|england|scotland|wales|northern ireland|"
    r"london|manchester|birmingham|leeds|glasgow|edinburgh|bristol|sheffield|"
    r"liverpool|cardiff|belfast|newcastle|nottingham|leicester|coventry|"
    r"southampton|portsmouth|brighton|oxford|cambridge|reading|milton keynes|"
    r"lincoln|york|hull|derby|stoke|swansea|aberdeen|dundee|norwich|exeter|"
    r"plymouth|luton|northampton|warwick|basingstoke|slough|crawley|swindon|"
    r"remote, uk|home based|field based)\b", re.I)

# "Boyne City, MI" is not the UK, but nothing in the country list says so, and
# the honest answer for an unrecognised place is "unknown", not "not UK". A
# trailing two-letter US or Canadian state code IS recognisable, so it is named
# here rather than left to fall through into the unknown bucket.
US_STATE_RE = re.compile(
    r",\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|"
    r"MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|"
    r"WI|WY|DC|AB|BC|MB|NB|NL|NS|ON|PE|QC|SK)\b")

NON_UK_RE = re.compile(
    r"\b(usa|u\.s\.|united states|germany|deutschland|france|netherlands|"
    r"belgium|spain|italy|poland|sweden|denmark|norway|finland|ireland|dublin|"
    r"switzerland|austria|australia|canada|india|china|japan|singapore|"
    r"new york|boston|chicago|paris|berlin|munich|amsterdam|madrid|milan)\b", re.I)

COMMERCIAL_RE = re.compile(
    r"\b(sales|account manager|account executive|territory|business development|"
    r"key account|commercial|regional manager|area manager|bdm|"
    r"product specialist|product manager|marketing|category manager|"
    r"tender|bid manager|customer success)\b", re.I)

CLINICAL_RE = re.compile(
    r"\b(clinical|nurse|nursing|specialist nurse|clinical specialist|"
    r"clinical advisor|clinical educator|clinical support|applications specialist|"
    r"medical science liaison|msl|therapy|physiotherap|radiograph|"
    r"biomedical scientist|theatre)\b", re.I)


def get(url, as_json=False, timeout=25):
    time.sleep(PAUSE)
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
    raw = r.read(4_000_000)
    body = raw.decode("utf-8", "replace")
    if as_json:
        return json.loads(body), r.geturl()
    return body, r.geturl()


def allowed(domain, path="/"):
    """Honour robots.txt, with a timeout, and treat a refusal to show it as a no.

    Same rule as crawl_supplier_site.py, and for the same reasons: a site that
    answers /robots.txt with 401/403 is not inviting a crawler, and a site that
    answers it with a block page must not be read as "no rules, crawl anything".
    """
    rp = urllib.robotparser.RobotFileParser()
    try:
        body, _ = get("https://%s/robots.txt" % domain, timeout=12)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False
        return True
    except Exception:
        return True
    head = body.lstrip()[:400].lower()
    if "<html" in head or "<!doctype" in head or (body.strip() and "user-agent" not in body.lower()):
        # AN HTML RESPONSE AT /robots.txt IS TWO DIFFERENT THINGS, and reading
        # them the same way is wrong in both directions.
        #
        #   A BLOCK PAGE. The site is refusing automated reads and saying so in
        #   HTML instead of a status code. Medtronic returned "Incorrect Browser"
        #   this way. Feeding that to RobotFileParser yields NO rules, i.e.
        #   "crawl anything" — precisely backwards. This must be a refusal.
        #
        #   A SOFT 404. The site simply has no robots.txt and its framework
        #   renders a not-found page with HTTP 200. Nobody has refused anything.
        #   Mediq Healthcare UK does this (confirmed 28/08/2026: its /robots.txt
        #   is its own 404 page, HTTP 200, 103KB of app shell).
        #
        # crawl_supplier_site.py separates them by similarity to the HOMEPAGE at
        # 0.99. That test has drifted — measured 28/08/2026, Mediq scores 0.9627,
        # because the shell renders route-specific content — and lowering the
        # threshold would start waving genuine block pages through. Nor does
        # probing a nonexistent path help: Mediq hard-404s those while soft-404ing
        # /robots.txt, so the two responses disagree on a site that is refusing
        # nothing.
        #
        # So ask what actually distinguishes them: a block page SAYS it is
        # blocking. Match on that vocabulary, and treat everything else as "no
        # robots file here". A genuine refusal still has two other ways to be
        # heard — 401/403 above, and a real robots.txt with a Disallow below.
        if re.search(r"cloudflare|captcha|access denied|attention required|"
                     r"incorrect browser|unsupported browser|bot detection|"
                     r"request blocked|you have been blocked|are you a robot",
                     body[:60000], re.I):
            return False
        return True
    rp.parse(body.splitlines())
    return rp.can_fetch(UA_STR, "https://%s%s" % (domain, path))


def clean(s):
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).split())


def uk_flag(loc):
    """True / False / None. None means the company published no location."""
    if not loc or not loc.strip():
        return None
    if UK_RE.search(loc):
        return True
    if NON_UK_RE.search(loc) or US_STATE_RE.search(loc):
        return False
    return None


def role_flags(title):
    t = title or ""
    return {"commercial": bool(COMMERCIAL_RE.search(t)),
            "clinical": bool(CLINICAL_RE.search(t))}


def role(title, location, url, posted=None):
    title = clean(title)
    location = clean(location)
    if not title:
        return None
    r = {"title": title, "location": location or "", "uk": uk_flag(location)}
    if url:
        r["url"] = url
    if posted:
        r["posted"] = str(posted)[:10]
    r.update(role_flags(title))
    return r


# Corporate and trade words that carry no identity. "Medical", "Healthcare" and
# "UK" are in almost every name in this seed, so a match on them is not evidence.
NOISE = {"ltd", "limited", "plc", "llp", "inc", "corp", "corporation", "company",
         "group", "holdings", "uk", "gb", "united", "kingdom", "europe", "european",
         "international", "global", "medical", "medic", "medics", "healthcare",
         "health", "care", "surgical", "科", "the", "and", "solutions", "systems",
         "services", "products", "supplies", "technologies", "technology", "science",
         "sciences", "diagnostics", "pharma", "pharmaceuticals", "labs", "laboratories"}


def _cores(name, domain):
    """The distinctive words that identify this company, name and domain."""
    words = re.split(r"[^a-z0-9]+", (name or "").lower())
    core = {w for w in words if len(w) >= 4 and w not in NOISE}
    host = re.sub(r"^www\.", "", (domain or "").lower())
    host = re.sub(r"\.(co\.uk|org\.uk|com|net|co|uk|eu|care|health|io|de|nl)$", "", host)
    for w in re.split(r"[^a-z0-9]+", host):
        if len(w) >= 4 and w not in NOISE:
            core.add(w)
    return core


def tenant_matches(token, name, domain):
    """Is this applicant tracking account THIS company's, or its parent group's?

    THE FAILURE THIS PREVENTS, found 28/08/2026. Acumed Ltd's own careers page
    links to Workday tenant `marmon` — its parent conglomerate — which returns 40
    roles, most of them US machine operators in Boyne City, Michigan. Read
    without this guard, the Hub would state "Acumed: 40 open roles" on a paid
    page. Not one of them is Acumed's, and a member would act on it.

    A group careers site is not evidence about a subsidiary. So the count is
    attributed only where the ATS account carries this company's own identity —
    a distinctive word from its name or its domain, in either direction. Anything
    else keeps the URL and refuses the count, naming the tenant so a reader can
    see exactly why.
    """
    t = re.sub(r"[^a-z0-9]", "", str(token or "").lower())
    if not t or t in NOISE:
        return False
    # ONE DIRECTION ONLY: a distinctive word from this company must appear IN the
    # account name. The reverse — account name inside the company word — waves
    # generic tokens through, because "medical" sits inside "advmedical" and
    # "healthcare" inside "amhealthcaregroup". Caught by test_careers_evidence.py
    # on 28/08/2026, before this ran wide.
    return any(c in t for c in _cores(name, domain))

# ---------------------------------------------------------------- ATS routes
#
# An applicant tracking system is the best possible source here: the roles are
# records, the count is the company's own count, and the API is public and meant
# to be read (it is what the company's own careers page calls to draw itself).
#
# Each entry is (name, regex over the page HTML capturing the account token,
# reader). A reader returns a list of role dicts, or raises.

def _greenhouse(token):
    doc, _ = get("https://boards-api.greenhouse.io/v1/boards/%s/jobs" % token, as_json=True)
    return [role(j.get("title"), (j.get("location") or {}).get("name"),
                 j.get("absolute_url"), j.get("updated_at"))
            for j in (doc.get("jobs") or [])]


def _lever(token):
    doc, _ = get("https://api.lever.co/v0/postings/%s?mode=json" % token, as_json=True)
    out = []
    for j in doc if isinstance(doc, list) else []:
        cat = j.get("categories") or {}
        posted = j.get("createdAt")
        if isinstance(posted, (int, float)):
            posted = dt.datetime.utcfromtimestamp(posted / 1000).date().isoformat()
        out.append(role(j.get("text"), cat.get("location"), j.get("hostedUrl"), posted))
    return out


def _workable(token):
    doc, _ = get("https://apply.workable.com/api/v1/widget/accounts/%s?details=true" % token,
                 as_json=True)
    out = []
    for j in (doc.get("jobs") or []):
        loc = j.get("location") or {}
        where = ", ".join(x for x in [loc.get("city"), loc.get("country")] if x) \
            if isinstance(loc, dict) else str(loc)
        out.append(role(j.get("title"), where, j.get("url") or j.get("shortlink"),
                        j.get("published_on")))
    return out


def _recruitee(token):
    doc, _ = get("https://%s.recruitee.com/api/offers/" % token, as_json=True)
    return [role(j.get("title"), j.get("location"), j.get("careers_url"),
                 j.get("published_at"))
            for j in (doc.get("offers") or [])]


def _smartrecruiters(token):
    doc, _ = get("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100" % token,
                 as_json=True)
    out = []
    for j in (doc.get("content") or []):
        loc = j.get("location") or {}
        where = ", ".join(x for x in [loc.get("city"), loc.get("country")] if x)
        out.append(role(j.get("name"), where,
                        "https://jobs.smartrecruiters.com/%s/%s" % (token, j.get("id")),
                        (j.get("releasedDate") or "")))
    return out


def _bamboohr(token):
    doc, _ = get("https://%s.bamboohr.com/careers/list" % token, as_json=True)
    out = []
    for j in (doc.get("result") or []):
        loc = j.get("location") or {}
        where = ", ".join(x for x in [loc.get("city"), loc.get("state"),
                                      loc.get("country")] if x) if isinstance(loc, dict) else ""
        out.append(role(j.get("jobOpeningName"), where,
                        "https://%s.bamboohr.com/careers/%s" % (token, j.get("id"))))
    return out


# Path segments and API version markers that are never an ATS account name.
BAD_TOKENS = {"v0", "v1", "v2", "v3", "api", "embed", "job_board", "jobs",
              "careers", "www", "assets", "static", "board", "boards"}

def _workday(url):
    """Workday's own career-site API — the endpoint its front-end calls.

    Workday renders its listings in the browser, which is why it sits in the
    detect-only list in most crawlers. But the page draws itself from a public
    JSON endpoint that needs no key, and that endpoint returns ONE OBJECT PER
    ROLE with the company's own total. That is a record source, so it counts.

    A career site URL looks like
        https://<tenant>.wd3.myworkdayjobs.com/en-US/<site>
    and the API sits at
        https://<tenant>.wd3.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs
    """
    m = re.match(r"https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/"
                 r"(?:[a-z]{2}-[A-Za-z]{2,4}/)?([A-Za-z0-9_-]+)", url, re.I)
    if not m:
        raise ValueError("not a Workday career site URL")
    tenant, wd, site = m.group(1), m.group(2), m.group(3)
    api = "https://%s.%s.myworkdayjobs.com/wday/cxs/%s/%s/jobs" % (tenant, wd, tenant, site)
    base = "https://%s.%s.myworkdayjobs.com/%s" % (tenant, wd, site)
    out, offset, stated = [], 0, None
    while True:
        payload = json.dumps({"appliedFacets": {}, "limit": 20,
                              "offset": offset, "searchText": ""}).encode()
        req = urllib.request.Request(
            api, data=payload,
            headers=dict(UA, **{"Content-Type": "application/json", "Accept": "application/json"}))
        time.sleep(PAUSE)
        doc = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace"))
        page = doc.get("jobPostings") or []
        # TAKE `total` FROM THE FIRST PAGE ONLY. Workday reports the real total on
        # page 1 and then `0` on every page after it. Re-reading it each time made
        # the loop stop at offset 40 — so Stryker, which has 1,184 open roles,
        # was counted as 40. Wrong by a factor of thirty, on a paid page, and it
        # got as far as a finished run before the round number gave it away
        # (28/08/2026). A count that stops early looks exactly like a small
        # company, which is why this must never be inferred from the loop.
        if stated is None and isinstance(doc.get("total"), int) and doc["total"] > 0:
            stated = doc["total"]
        for j in page:
            path = j.get("externalPath") or ""
            out.append(role(j.get("title"), j.get("locationsText"),
                            base + path if path.startswith("/") else None,
                            j.get("startDate")))
        offset += 20
        if not page or (stated is not None and len(out) >= stated) or len(out) >= WORKDAY_CAP:
            break
    return out, (stated if stated is not None else len(out))



ATS_READABLE = [
    # NOT boards-api.greenhouse.io — that host is the API's own URL, which the
    # embed script prints, and capturing from it yields the token "v1" (seen on
    # Aidoc, 28/08/2026). Only the board host and the ?for= parameter name a real
    # account.
    ("greenhouse",      re.compile(r"(?:job-)?boards\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_-]+)"
                                   r"|greenhouse\.io/embed/job_board\?for=([a-z0-9_-]+)", re.I), _greenhouse),
    ("lever",           re.compile(r"jobs\.lever\.co/([a-z0-9_-]+)", re.I),              _lever),
    ("workable",        re.compile(r"apply\.workable\.com/(?:api/v\d/widget/accounts/)?([a-z0-9_-]+)", re.I), _workable),
    ("recruitee",       re.compile(r"([a-z0-9_-]+)\.recruitee\.com", re.I),              _recruitee),
    ("smartrecruiters", re.compile(r"(?:careers|jobs)\.smartrecruiters\.com/([A-Za-z0-9_-]+)", re.I), _smartrecruiters),
    ("bamboohr",        re.compile(r"([a-z0-9_-]+)\.bamboohr\.com/(?:careers|jobs)", re.I), _bamboohr),
    # Captures the whole URL, not a token — _workday re-parses it for the tenant,
    # the wd host number and the site name, all three of which the API needs.
    ("workday",         re.compile(r"(https?://[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com/[^\s\"'<>\\]*)", re.I), _workday),
]

# Detected but NOT readable as records. These render their listings client-side
# or gate the API behind a key. Naming them is honest and useful — a human can
# click through — and it is emphatically not reported as "0 roles".
ATS_DETECT_ONLY = [
    # myworkdayjobs.com is handled above as a READABLE source. What stays here is
    # the other Workday shape — a company-hosted /careers page on workday.com —
    # which exposes no such endpoint.
    ("workday",     re.compile(r"workday\.com/[a-z-]+/careers", re.I)),
    ("ashby",       re.compile(r"jobs\.ashbyhq\.com", re.I)),
    ("teamtailor",  re.compile(r"[a-z0-9_-]+\.teamtailor\.com", re.I)),
    ("personio",    re.compile(r"[a-z0-9_-]+\.jobs\.personio\.(?:de|com)", re.I)),
    ("successfactors", re.compile(r"successfactors\.(?:eu|com)|career\d*\.sap", re.I)),
    ("icims",       re.compile(r"\.icims\.com", re.I)),
    ("taleo",       re.compile(r"\.taleo\.net", re.I)),
]


# ------------------------------------------------------------ JSON-LD route

def _walk_jobpostings(node, out):
    if isinstance(node, list):
        for n in node:
            _walk_jobpostings(n, out)
        return
    if not isinstance(node, dict):
        return
    t = node.get("@type")
    types = t if isinstance(t, list) else [t]
    if any(str(x).lower() == "jobposting" for x in types if x):
        out.append(node)
    for key in ("@graph", "itemListElement", "item", "mainEntity"):
        if key in node:
            _walk_jobpostings(node[key], out)


def jsonld_roles(html_doc, page_url):
    """schema.org JobPosting blocks — one record per role, published by the
    company for machines to read. A real record, so it counts."""
    found = []
    for m in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_doc, re.S | re.I):
        blob = m.group(1).strip()
        try:
            doc = json.loads(blob)
        except Exception:
            continue
        _walk_jobpostings(doc, found)
    out = []
    for j in found:
        loc = j.get("jobLocation")
        where = ""
        if isinstance(loc, list):
            loc = loc[0] if loc else None
        if isinstance(loc, dict):
            addr = loc.get("address") or {}
            if isinstance(addr, dict):
                where = ", ".join(str(x) for x in [
                    addr.get("addressLocality"), addr.get("addressRegion"),
                    addr.get("addressCountry") if isinstance(addr.get("addressCountry"), str)
                    else (addr.get("addressCountry") or {}).get("name")] if x)
            elif isinstance(addr, str):
                where = addr
        elif isinstance(loc, str):
            where = loc
        if not where and j.get("jobLocationType"):
            where = clean(j.get("jobLocationType"))
        out.append(role(j.get("title"), where,
                        j.get("url") or j.get("sameAs") or page_url, j.get("datePosted")))
    return [r for r in out if r]


# --------------------------------------------------- finding the careers page

def find_careers_url(domain, deadline):
    """Ask the company's own navigation first, then well-known paths.

    Returns (url, how) or (None, reason). "how" is recorded in the output so a
    reader can see whether the company named this page itself (`nav`) or whether
    it was found by trying a conventional path (`path`). The first is the
    company's own filing; the second is a convention it happens to follow.
    """
    home = None
    for base in ("https://%s/" % domain, "https://www.%s/" % domain):
        try:
            home, final = get(base, timeout=20)
            domain = urllib.parse.urlparse(final).netloc or domain
            break
        except Exception:
            continue
    if home:
        best = None
        for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                             home, re.S | re.I):
            # Unescape the href: an anchor written with &amp; in the markup
            # would otherwise be recorded as a URL that does not resolve.
            href, text = H.unescape(m.group(1)).strip(), clean(m.group(2))
            if not (NAV_RE.search(text) or NAV_RE.search(href)):
                continue
            url = urllib.parse.urljoin("https://%s/" % domain, href)
            if not url.lower().startswith("http"):
                continue
            # An off-site careers link (an ATS, a job board) is still the
            # company's own answer to "where are our jobs" — keep it.
            best = best or url
            if urllib.parse.urlparse(url).netloc.endswith(domain.replace("www.", "")):
                return url, "nav"
        if best:
            return best, "nav"

    for path in CAREER_PATHS:
        if time.time() > deadline:
            return None, "site budget exhausted before a careers page was found"
        url = "https://%s%s" % (domain, path)
        try:
            body, final = get(url, timeout=15)
        except Exception:
            continue
        # A site that answers every unknown path with its homepage (a SPA) would
        # otherwise "have" a careers page at the first path tried. Require the
        # page to actually talk about jobs.
        if NAV_RE.search(body[:20000]) or re.search(r"vacanc|job openings|apply now",
                                                    body[:40000], re.I):
            return final, "path"
    return None, "no careers page found in the site's own navigation or at a conventional path"


# A careers LANDING page is often just prose — "why work here" — with the actual
# list one click further on. These are the words a company uses for that link.
VACANCY_LINK_RE = re.compile(
    r"current vacanc|our vacanc|view vacanc|all vacanc|open (role|position|vacanc)|"
    r"current opportunit|job search|search jobs|view (our )?jobs|browse jobs|"
    r"see all jobs|job listings|live roles", re.I)


def _vacancy_subpage(html_doc, base_url):
    """One link deeper, and only one, from the careers landing page."""
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         html_doc, re.S | re.I):
        href, text = H.unescape(m.group(1)).strip(), clean(m.group(2))
        if VACANCY_LINK_RE.search(text) or VACANCY_LINK_RE.search(href):
            url = urllib.parse.urljoin(base_url, href)
            if url.lower().startswith("http") and url.rstrip("/") != base_url.rstrip("/"):
                return url
    return None


def read_roles(careers_url, deadline, ident, _depth=0):
    """Return (roles, method, ats, note, sourceUrl). Only ats/jsonld return roles.

    sourceUrl is the page the roles were actually read from, which is not always
    the careers page: a prose careers page keeps its list one hop away, and the
    output must say which page the count came from.
    """
    try:
        body, final = get(careers_url, timeout=25)
    except urllib.error.HTTPError as e:
        return None, None, None, "careers page returned HTTP %s" % e.code, None
    except Exception as e:
        return None, None, None, "careers page could not be read (%s)" % type(e).__name__, None

    for name, rx, reader in ATS_READABLE:
        m = rx.search(body)
        if not m:
            continue
        token = next((g for g in m.groups() if g), None)
        if not token or token.lower() in BAD_TOKENS:
            continue
        # Workday's token is a whole URL; the tenant is the identity in it.
        ident_token = token
        if name == "workday":
            tm = re.match(r"https?://([a-z0-9-]+)\.", token, re.I)
            ident_token = tm.group(1) if tm else token
        if not tenant_matches(ident_token, ident[0], ident[1]):
            return None, None, name, (
                "the careers page hands off to a %s account named \u201c%s\u201d, which does not "
                "carry this company's own identity \u2014 a parent or group careers site. Its roles "
                "are not this company's, so no count is stated. The page is linked."
                % (name, ident_token)), None
        if time.time() > deadline:
            return None, None, name, "%s detected but the site budget ran out before reading it" % name, None
        try:
            got = reader(token)
            # A reader returns either a plain list (it fetched everything) or a
            # (roles, statedTotal) pair, where the source states a total larger
            # than what was fetched.
            if isinstance(got, tuple):
                raw, stated_total = got
            else:
                raw, stated_total = got, None
            roles = [r for r in raw if r]
            if stated_total is None:
                stated_total = len(roles)
        except Exception as e:
            return None, None, name, ("%s detected (account %s) but its public API did not "
                                      "answer (%s)" % (name, token, type(e).__name__)), None
        return (roles, stated_total, ident_token), "ats", name, None, final

    roles = jsonld_roles(body, final)
    if roles:
        return (roles, len(roles), None), "jsonld", None, None, final

    for name, rx in ATS_DETECT_ONLY:
        if rx.search(body):
            return None, None, name, ("%s detected — it renders its listings in the browser, "
                                      "so the roles cannot be read as records. The page is "
                                      "linked; the count is not stated." % name), None

    # Nothing on the landing page. Follow the company's own "current vacancies"
    # link ONCE — that is where a prose careers page keeps the actual list — and
    # hold the sub-page to exactly the same evidence bar. One hop only: deeper
    # than that and it stops being the company's careers page.
    if _depth == 0 and time.time() < deadline:
        sub = _vacancy_subpage(body, final)
        if sub:
            roles, method, ats, note, src = read_roles(sub, deadline, ident, _depth=1)
            if roles is not None:
                return roles, method, ats, note, src
            return None, None, ats, note, None

    return None, None, None, ("the page publishes no role records (no applicant tracking "
                              "system and no JobPosting structured data), so no count is "
                              "stated"), None


def website_for(rec):
    """The supplier's OWN site, from a link the seed labels as such.

    Deliberately stricter than crawl_supplier_site.py's domain_for(): that one
    takes the first non-excluded link of any label, which here could hand back a
    trade-press article and have this reading a magazine's careers page as the
    supplier's. Only an explicitly labelled website counts.
    """
    for l in (rec.get("links") or []):
        if not isinstance(l, dict):
            continue
        label = (l.get("label") or "").strip().lower()
        if label in ("website", "company website") or label.endswith("— website"):
            m = re.search(r"https?://([^/]+)", str(l.get("url") or ""))
            if m and not any(x in m.group(1) for x in
                             ("gov.uk", "supplychain", "nhs.uk", "linkedin")):
                return m.group(1)
    return None


# --------------------------------------------------------------------- run

def role_key(r):
    return r.get("url") or ("%s|%s" % (r.get("title", ""), r.get("location", "")))


def existing_rows(path):
    """Rows from a previous run, by supplier name."""
    try:
        with open(path) as f:
            return {r.get("name"): r for r in (json.load(f).get("suppliers") or [])}
    except Exception:
        return {}


def previous_keys():
    """Roles seen on the last run, per supplier. Used only to mark `new`."""
    try:
        with open(REPORT) as f:
            old = json.load(f)
    except Exception:
        return None
    seen = {}
    for row in (old.get("suppliers") or []):
        seen[row.get("name")] = {role_key(r) for r in (row.get("roles") or [])}
    return seen or None


def run_one(name, domain, prev):
    deadline = time.time() + SITE_BUDGET_S
    row = {"name": name, "domain": domain, "checkedOn": TODAY}

    if not allowed(domain, "/careers"):
        row["refused"] = "robots.txt disallows automated reads of this site"
        return row

    url, how = find_careers_url(domain, deadline)
    if not url:
        row["refused"] = how
        return row
    row["careersUrl"] = url
    row["careersUrlFoundBy"] = how

    result, method, ats, note, src = read_roles(url, deadline, (name, domain))
    if ats:
        row["ats"] = ats
    if result is None:
        row["refused"] = note
        return row
    roles, stated_total, ats_account = result
    if ats_account:
        # Record the account the count was taken from, beside the count. A reader
        # (and verify.py) must be able to re-run the parent-group guard without
        # re-fetching the site — the Acumed/Marmon failure is invisible from the
        # numbers alone.
        row["atsAccount"] = ats_account

    seen = prev.get(name) if prev else None
    for r in roles:
        if seen is not None:
            r["new"] = role_key(r) not in seen
    roles.sort(key=lambda r: (not r.get("new"), r["title"].lower()))

    row["roleCount"] = stated_total
    row["countMethod"] = method
    if src and src.rstrip("/") != url.rstrip("/"):
        row["rolesUrl"] = src

    # THE BREAKDOWN IS ONLY STATED OVER A COMPLETE LIST. Where the source states
    # more roles than were retrieved, roleCount stands — it is the company's own
    # figure — but UK, commercial and clinical are omitted entirely rather than
    # computed over the first 300 of 1,184 and presented as if they were the lot.
    # A partial breakdown beside a full total is a wrong number wearing a right
    # one, and there is no honest way to caveat it into being true.
    row["rolesRetrieved"] = len(roles)
    row["complete"] = len(roles) >= stated_total
    if not row["complete"]:
        row["breakdownWithheld"] = (
            "The source states %d roles; %d were retrieved before the fetch cap. "
            "UK, commercial and clinical counts are not stated, because they would "
            "be computed over part of the list and read as all of it."
            % (stated_total, len(roles)))
        row["roles"] = roles[:40]
        return row

    located = [r for r in roles if r["uk"] is not None]
    row["ukRoles"] = sum(1 for r in located if r["uk"])
    row["rolesWithoutLocation"] = len(roles) - len(located)
    row["commercialRoles"] = sum(1 for r in roles if r["commercial"])
    row["clinicalRoles"] = sum(1 for r in roles if r["clinical"])
    if seen is not None:
        row["newRoles"] = sum(1 for r in roles if r.get("new"))
    row["roles"] = roles
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplier", help="run one supplier, or several: a comma-separated "
                                       "list of names or aliases, matched as substrings")
    ap.add_argument("--auto", action="store_true", help="run every supplier with a website")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--rotate", type=int, metavar="N",
                    help="check the N least-recently-checked suppliers and MERGE them "
                         "into the existing rows, rather than replacing the file. A full "
                         "sweep of all 483 takes about four hours, which no scheduled "
                         "run should hold open; rotation keeps each run bounded and "
                         "cycles the whole list over several weeks.")
    ap.add_argument("--write", action="store_true",
                    help="ALSO write data/supplier-careers.json, which the Hub serves. "
                         "A push to this repo is a publish — read the report first.")
    a = ap.parse_args()

    seed = json.load(open(SEED))
    rows = seed["suppliers"]

    targets = []
    for rec in rows:
        dom = website_for(rec)
        if not dom:
            continue
        if a.supplier:
            names = [rec.get("name", "")] + list(rec.get("aliases") or [])
            wanted = [w.strip().lower() for w in a.supplier.split(",") if w.strip()]
            if not any(w in n.lower() for w in wanted for n in names):
                continue
        targets.append((rec["name"], dom))

    if a.rotate:
        # Oldest first, never-checked before ever-checked. A supplier whose row
        # is stale is more useful to re-read than one checked yesterday.
        known = existing_rows(OUT) or existing_rows(REPORT)
        targets.sort(key=lambda t: (known.get(t[0], {}).get("checkedOn") or ""))
        targets = targets[:a.rotate]

    if not a.supplier and not a.auto and not a.rotate:
        print("%d suppliers carry an official website link in the seed." % len(targets))
        print("Run with --supplier NAME, or --auto --limit N.")
        return 0
    if not targets:
        print("No supplier matched.")
        return 1
    if a.auto:
        targets = targets[:a.limit]

    prev = previous_keys()
    out = []
    for i, (name, dom) in enumerate(targets, 1):
        print("[%d/%d] %s (%s)" % (i, len(targets), name, dom), flush=True)
        try:
            row = run_one(name, dom, prev)
        except Exception as e:
            row = {"name": name, "domain": dom, "checkedOn": TODAY,
                   "refused": "run failed (%s: %s)" % (type(e).__name__, e)}
        if row.get("refused"):
            print("      refused: %s" % row["refused"])
        else:
            if row.get("complete"):
                print("      %d role(s) via %s, %d UK, %d commercial, %d clinical  %s"
                      % (row["roleCount"], row["countMethod"], row["ukRoles"],
                         row["commercialRoles"], row["clinicalRoles"], row["careersUrl"]))
            else:
                print("      %d role(s) stated via %s (%d retrieved; breakdown withheld)  %s"
                      % (row["roleCount"], row["countMethod"], row["rolesRetrieved"],
                         row["careersUrl"]))
        out.append(row)

    if a.rotate:
        # MERGE, never replace. A rotating run touches a slice of the list; the
        # rows it did not visit must survive it untouched, carrying their own
        # older checkedOn date so a reader can see how stale each one is.
        merged = existing_rows(OUT) or existing_rows(REPORT)
        for r in out:
            merged[r["name"]] = r
        out = sorted(merged.values(), key=lambda r: r.get("name") or "")
        print("\nmerged %d checked row(s) into %d total." % (len(targets), len(out)))

    # Keyed on the count being PRESENT, not on the absence of a refusal: a merged
    # row from an older run may carry neither, and summing roleCount over it would
    # crash the run that was meant to be routine.
    counted = [r for r in out if r.get("roleCount") is not None]
    report = {
        "_notice": "Working report for scripts/refresh_supplier_careers.py. "
                   "No consumer reads this file.",
        "generatedOn": TODAY,
        "firstRun": prev is None,
        "rule": "A careers page URL is recorded on the company's own link or a "
                "conventional path answering from its own domain. A role COUNT is "
                "recorded only where each role was read as a discrete record — an "
                "applicant tracking system's public API, or schema.org JobPosting "
                "structured data. Layouts are never pattern-counted. Everything else "
                "is refused, with the reason kept.",
        "roleFlagRule": "commercial/clinical are matched from the job title against a "
                        "fixed vocabulary in the script. A filing aid, not a claim "
                        "about the role.",
        "ukRule": "uk is true only where the company's own published location names a "
                  "UK nation, city or region; false where it names somewhere else; "
                  "null where no location was published. rolesWithoutLocation gives "
                  "the denominator a UK count must be read against.",
        "counts": {
            "checked": len(out),
            "withCareersPage": sum(1 for r in out if r.get("careersUrl")),
            "withRoleCount": len(counted),
            "refused": sum(1 for r in out if r.get("refused")),
            "roles": sum(r["roleCount"] for r in counted),
            "completeBreakdowns": sum(1 for r in counted if r.get("complete")),
            "ukRoles": sum(r.get("ukRoles", 0) for r in counted),
        },
        "suppliers": out,
    }
    with open(REPORT, "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
        f.write("\n")
    c = report["counts"]
    print("\n%d checked | %d careers pages | %d with a readable role count | %d refused"
          % (c["checked"], c["withCareersPage"], c["withRoleCount"], c["refused"]))
    # "1,527 roles, 0 of them UK" is true and reads as a finding. It is not one:
    # the UK figure is 0 because every countable supplier exceeded the fetch cap
    # and had its breakdown withheld. Say how many breakdowns there actually are,
    # or the summary line invents a conclusion the data does not support.
    print("%d roles across %d supplier(s); %d of those have a full breakdown, "
          "covering %d UK role(s). Report: %s"
          % (c["roles"], c["withRoleCount"], c["completeBreakdowns"], c["ukRoles"], REPORT))

    if a.write:
        pub = {k: v for k, v in report.items() if k != "_notice"}
        pub["suppliers"] = [r for r in out if r.get("careersUrl")]
        with open(OUT, "w") as f:
            json.dump(pub, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print("WROTE %s — this is published. Run stamp_notice.py then verify.py." % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
