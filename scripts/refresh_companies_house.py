#!/usr/bin/env python3
"""Stage 3 of the Company Report: resolve every supplier to its Companies House
record and write data/company-financials.json.

Schema and derivation rules: docs/COMPANY-REPORT-METHOD.md. If this script and
that document disagree, this script is wrong. Stdlib only.

WHAT THIS CAN AND CANNOT GIVE YOU
---------------------------------
The Companies House public REST API returns the company PROFILE — number,
status, incorporation date, SIC codes, and the statutory accounts *category*.
It does not return turnover and it does not return employee numbers; neither
field exists anywhere in the company-profile resource (checked against the
published spec, 06/08/2026). Turnover appears only inside the filed accounts
document, and only when a company files full accounts — small and micro
companies may lawfully omit the profit-and-loss account, and most UK medtech
subsidiaries do.

So `turnoverGBP` and `employees` are written as null on every record here, and
null means "not disclosed". They may only ever be set by a later stage that has
actually parsed a filed document. ⚠️ NEVER write 0 and never infer a figure —
that is the whole reason the method doc exists.

THE MATCH RULE (root rule 14 — a derived claim carries the rule it was made
under, and refuses to fire on thin evidence)
------------------------------------------------------------------------------
`matchConfidence` is "confirmed" only when ALL FOUR hold:

  1. the company number came from a SOURCE, by one of the two routes below,
     never a bare 8-digit number found lying around in prose;
  2. Companies House returns a record for that number;
  3. the registered name corroborates the supplier — at least one significant
     token in common after corporate stopwords are dropped;
  4. the company is `active`.

The two accepted sources for test 1 (routes 1 and 2 of the method doc; route 3,
the NHSSC legal supplier name, is specified there and not yet implemented):

  ROUTE 1 — the anchored "Companies House NNNNNNNN" pattern in the supplier's
     own alerts[]/note, curated by hand.
  ROUTE 2 — `companyNumberProof`, the registration number the company publishes
     on its OWN site, written by scripts/confirm_company_numbers.py from the
     evidence in state/domain-seeding-report.json. It carries the source URL and
     the verbatim matched string, and `matchedOn` quotes the URL.

Where both routes fire and DISAGREE, the number is discarded and the supplier
falls through to name search — two sourced numbers disagreeing is a fact to
check by hand, not a tie to break in code. Same rule as two anchored numbers.

Everything else is "probable", and `matchedOn` says which test it failed.
Name-search matches are ALWAYS "probable", per the method doc.

**A "probable" record must never feed a derived claim.** It is written so the
page can show company facts with the caveat, and so a human can check it. Stage
4's field-position bands read confirmed records only.

Why the corroboration test exists: medtech is full of similarly-named and
renamed entities. The seed itself records that Abbott Diabetes Care was formerly
MediSense (U.K.) Holding Ltd, that SIRONA DENTAL SYSTEMS LIMITED was dissolved
in 2020, and that EXACTECH (UK) LIMITED now files as ADVITA ORTHO UK LIMITED.
Attaching the wrong company's finances to a named business is the same class of
error as the 145 false job changes on 24/07/2026.

⚠️ AMBIGUOUS SUPPLIERS ARE NOT GUESSED. Five suppliers in the current data name
two different company numbers in their free text (a UK subsidiary and its new
holding company, or an FC/BR overseas pair). Where the anchored pattern yields
more than one distinct number, the number is discarded and the supplier falls
through to name search, which can only ever produce "probable". Picking the
first of two would be inventing a fact.

THRESHOLDS ARE FETCHED, NEVER HARDCODED
---------------------------------------
The statutory micro/small/medium thresholds are a fact with a shelf life (root
rule 12) and they changed for financial years beginning on or after 6 April
2025. They are read at build time from Companies House's own published guidance
via GOV.UK's Content API — the JSON rendering of the same page a reader clicks —
and written into the file with the date they were read.

If the page wording moves and the parse fails, this script ABORTS. It does not
carry forward a previous value and it does not fall back to a constant: the page
prints the threshold the band was assigned under, so a stale threshold would be
a wrong fact in front of members.

SOURCES (all fetched directly, 06/08/2026)
------------------------------------------
  API base, auth      https://developer-specs.company-information.service.gov.uk/guides/authorisation
  Rate limit          https://developer-specs.company-information.service.gov.uk/guides/rateLimiting
  Company profile     https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/resources/companyprofile
  Size thresholds     https://www.gov.uk/government/publications/life-of-a-company-annual-requirements/life-of-a-company-part-1-accounts

AUTHENTICATION
--------------
Companies House uses HTTP Basic auth with the API KEY AS THE USERNAME and an
empty password. Register an "API Key" application at
https://developer.company-information.service.gov.uk/manage-applications — the
key is free and self-service.

Put the key in the environment, never in this file and never in the repo:

    export COMPANIES_HOUSE_KEY='...'

In GitHub Actions it belongs in repository secrets, exposed to the step as
`env: COMPANIES_HOUSE_KEY: ${{ secrets.COMPANIES_HOUSE_KEY }}`.

RATE LIMIT
----------
600 requests per five minutes; over that, every further request in the window
returns 429. Requests here are serialised and paced below that ceiling, and a
429 is honoured rather than hammered. Do not parallelise this — the docs say
applications attempting to bypass the limit can be banned without notice.

USAGE
-----
    python3 scripts/refresh_companies_house.py
    python3 scripts/refresh_companies_house.py --offline
    python3 scripts/refresh_companies_house.py --limit 10 --out /tmp/sample.json
    python3 scripts/refresh_companies_house.py --out data/company-financials.json

    --offline   no network at all. Reports what a live run would do and writes
                nothing — a file built offline would carry no verified fact.
    --limit N   first N suppliers only. A partial run may NOT be written to the
                default path; pass --out somewhere else.
    --out PATH  defaults to data/company-financials.json.

⚠️ BEFORE THE OUTPUT CAN BE PUBLISHED: company-financials.json needs a marker
ref minted from the private salt and added to REFS in scripts/stamp_notice.py,
then stamp_notice.py run over it. verify.py's notice check fails without one.
This script deliberately does not write a `_notice` block — it cannot mint a
ref, and a fabricated one would defeat the traceability scheme.
"""
import base64, datetime, html, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request

API = "https://api.company-information.service.gov.uk"
FIND = "https://find-and-update.company-information.service.gov.uk/company/"
KEY_ENV = "COMPANIES_HOUSE_KEY"

SEED = "data/supplier-seed.json"
INDEX = "data/supplier-index.json"
OUT = "data/company-financials.json"

# The human-readable guidance page (this is what goes in the file, because it is
# what a member or Lou would open) and its Content API rendering, which is the
# same document as machine-readable JSON.
THRESHOLDS_PAGE = ("https://www.gov.uk/government/publications/"
                   "life-of-a-company-annual-requirements/life-of-a-company-part-1-accounts")
THRESHOLDS_JSON = ("https://www.gov.uk/api/content/government/publications/"
                   "life-of-a-company-annual-requirements/life-of-a-company-part-1-accounts")

UA = {"User-Agent": "Mozilla/5.0 (msh-compare-data; company-report; contact via repo)"}

# 600 requests / 5 minutes = 2.0/sec. Pace at 1.8/sec so a slow response or a
# retry cannot push a burst over the ceiling. ~460 suppliers, up to two requests
# each, is roughly seven minutes.
MIN_GAP = 0.55
RETRIES = 3

# Dropped before comparing a supplier name with a registered name. Every one of
# these appears in so many medtech company names that it proves nothing.
STOP = {"ltd", "limited", "plc", "llp", "group", "holdings", "holding", "medical",
        "medtech", "healthcare", "health", "care", "uk", "gbr", "great", "britain",
        "international", "systems", "solutions", "products", "device", "devices",
        "technologies", "technology", "sciences", "science", "company", "trading",
        "services", "service", "europe", "european", "the", "and"}

log = lambda m: print("[companies-house]", m, flush=True)


def arg(flag, default=None):
    """--flag value. No argparse anywhere else in this repo; keep it that way."""
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 >= len(sys.argv):
            raise SystemExit("ABORT: %s needs a value." % flag)
        return sys.argv[i + 1]
    return default


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def tokens(*strings):
    """Significant words in a company name — 4+ characters, corporate noise out."""
    text = " ".join(s for s in strings if s)
    return {w for w in re.findall(r"[a-z0-9]{4,}", text.lower()) if w not in STOP}


# --------------------------------------------------------------------------
# HTTP: one request at a time, paced, and honest about failure
# --------------------------------------------------------------------------
_last_call = [0.0]


def pace():
    wait = MIN_GAP - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()


def api_get(path, key):
    """GET one Companies House resource.

    Returns the decoded object, or None for a 404 (a number that no longer
    resolves is a finding, not a crash). A bad key aborts the whole run — every
    subsequent call would fail the same way and there is nothing to publish.
    """
    auth = base64.b64encode((key + ":").encode()).decode()
    headers = dict(UA)
    headers["Authorization"] = "Basic " + auth
    req = urllib.request.Request(API + path, headers=headers)

    for attempt in range(RETRIES):
        pace()
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 401:
                raise SystemExit(
                    "ABORT: Companies House rejected the key in $%s (401).\n"
                    "  The key must be an 'API Key' application key from\n"
                    "  https://developer.company-information.service.gov.uk/manage-applications\n"
                    "  and it must not be restricted to an IP range this machine is outside of."
                    % KEY_ENV)
            if e.code == 429:
                # Honour the ceiling rather than hammer it. The docs are explicit
                # that applications trying to bypass it can be banned.
                nap = int(e.headers.get("Retry-After") or 60)
                log("429 rate limited — sleeping %ds (attempt %d/%d)" % (nap, attempt + 1, RETRIES))
                time.sleep(nap)
                continue
            if 500 <= e.code < 600 and attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            log("HTTP %d on %s" % (e.code, path))
            return None
        except Exception as e:
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            log("failed %s (%s)" % (path, e))
            return None
    return None


# --------------------------------------------------------------------------
# Statutory thresholds — read from the source every run, never carried forward
# --------------------------------------------------------------------------
# Section numbers move, so nothing here depends on them. The anchors are the
# heading WORDING; if that changes, the parse fails loudly instead of quietly
# picking up the wrong block.
BAND_ANCHORS = {
    "micro":  r"(?i)^\s*[\d.]*\s*(?:conditions to )?qualify(?:ing)? as a micro-entity\s*$",
    "small":  r"(?i)^\s*[\d.]*\s*qualifying as a small company\s*$",
    "medium": r"(?i)^\s*[\d.]*\s*qualifying as a medium-sized company\s*$",
}
CURRENT = re.compile(r"(?i)^for accounting periods that begin on or after (.+?)\s*$")


def money(number, unit):
    value = float(number.replace(",", ""))
    unit = (unit or "").strip().lower()
    if unit == "million":
        value *= 1e6
    elif unit == "billion":
        value *= 1e9
    return int(round(value))


# The key lives OUTSIDE the synced workspace, the same rule as the marker salt:
# anything inside OneDrive is disclosed to every session that reads the file, and
# a key in the repo is a key on GitHub. Environment first (that is how Actions
# supplies it), then the local file.
KEY_FILE = "~/.companies-house-key"


def load_key():
    key = os.environ.get(KEY_ENV, "").strip()
    if key:
        return key
    path = os.path.expanduser(KEY_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            return key
    raise SystemExit(
        "ABORT: no Companies House key, so there is nothing to authenticate with.\n"
        "  Looked in: $%s, then %s\n"
        "  1. Sign in at https://developer.company-information.service.gov.uk/\n"
        "  2. Manage applications -> your application -> add an API key (REST, live)\n"
        "  3. Save it:  pbpaste > %s && chmod 600 %s\n"
        "     (in Actions: a repository secret named %s)\n"
        "  The key is sent as the HTTP Basic USERNAME with a blank password.\n"
        "  Run with --offline to check the supplier side without a key."
        % (KEY_ENV, KEY_FILE, KEY_FILE, KEY_FILE, KEY_ENV))


def read_thresholds():
    """The current micro/small/medium thresholds, from Companies House guidance.

    Aborts rather than guesses. A wrong threshold on the page is a wrong fact in
    front of paying members, and there is no honest default to fall back on.
    """
    req = urllib.request.Request(THRESHOLDS_JSON, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        doc = json.loads(r.read().decode("utf-8", "replace"))
    body = (doc.get("details") or {}).get("body") or ""
    if not body:
        raise SystemExit("ABORT: GOV.UK Content API returned no body for the thresholds page.")

    lines = [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "\n", body)).split("\n") if l.strip()]

    bands, applies = {}, set()
    for band, anchor in BAND_ANCHORS.items():
        start = next((i for i, l in enumerate(lines) if re.match(anchor, l)), None)
        if start is None:
            raise SystemExit("ABORT: could not find the '%s' section on %s — the guidance has been "
                             "reworded. Read it and fix the anchor; do not hardcode a threshold."
                             % (band, THRESHOLDS_PAGE))
        # The page shows the current thresholds first, then the pre-6-April-2025
        # set. Take the block under the CURRENT heading only.
        head = next((i for i in range(start, min(start + 12, len(lines)))
                     if CURRENT.match(lines[i])), None)
        if head is None:
            raise SystemExit("ABORT: no 'For accounting periods that begin on or after ...' block "
                             "under the '%s' section of %s." % (band, THRESHOLDS_PAGE))
        block = []
        for line in lines[head + 1:head + 9]:
            if re.match(r"(?i)^for accounting periods", line):
                break
            block.append(line)
        stated = " ".join(block)

        # Belt and braces: the group-accounts sections use the same sentence shape
        # with different numbers. They always say "aggregate" and quote a gross
        # figure, so refuse anything carrying either word.
        if "aggregate" in stated.lower() or "gross" in stated.lower():
            raise SystemExit("ABORT: the '%s' anchor landed on a GROUP thresholds block. "
                             "Fix the anchor rather than the check." % band)

        turnover = re.search(r"(?i)turnover\s+(?:of\s+)?no more than\s+£([\d,.]+)(\s*(?:million|billion))?", stated)
        sheet = re.search(r"(?i)balance sheet total\s+(?:of\s+)?no more than\s+£([\d,.]+)(\s*(?:million|billion))?", stated)
        staff = re.search(r"(?i)no more than\s+([\d,]+)\s+employees", stated)
        if not (turnover and sheet and staff):
            raise SystemExit("ABORT: could not read all three '%s' thresholds from %s.\n  Read: %r"
                             % (band, THRESHOLDS_PAGE, stated[:300]))

        bands[band] = {
            "turnoverGBP": money(*turnover.groups()),
            "balanceSheetTotalGBP": money(*sheet.groups()),
            "employees": int(staff.group(1).replace(",", "")),
            # The verbatim sentence the three numbers were parsed out of, so the
            # parse can be checked without re-reading the page.
            "statedAs": stated,
        }
        applies.add(CURRENT.match(lines[head]).group(1))

    if len(applies) != 1:
        raise SystemExit("ABORT: the three bands quote different effective dates (%s). "
                         "Read the guidance before publishing anything." % sorted(applies))

    # Invariants. A parse that silently picked up the wrong figures would sail
    # through everything above; these are what would actually catch it.
    order = ("micro", "small", "medium")
    for key in ("turnoverGBP", "balanceSheetTotalGBP", "employees"):
        values = [bands[b][key] for b in order]
        if not (values[0] <= values[1] <= values[2]):
            raise SystemExit("ABORT: %s thresholds are not micro <= small <= medium (%s). "
                             "The parse is wrong." % (key, values))
    if not 100000 <= bands["micro"]["turnoverGBP"] < bands["medium"]["turnoverGBP"] <= 10_000_000_000:
        raise SystemExit("ABORT: turnover thresholds are outside any plausible range (%s). "
                         "The parse is wrong." % [bands[b]["turnoverGBP"] for b in order])

    return {
        "readFrom": THRESHOLDS_PAGE,
        "readOn": datetime.date.today().isoformat(),
        "appliesTo": "periods beginning on or after " + applies.pop(),
        "bands": bands,
    }


# --------------------------------------------------------------------------
# Suppliers
# --------------------------------------------------------------------------
# Anchored on the words "Companies House" so a bare 8-digit number in prose — an
# OJEU reference, a product code, a framework value — can never be mistaken for a
# company number.
CH_NUMBER = re.compile(
    r"(?i)compan(?:y|ies)\s+house"
    r"[^A-Za-z0-9]{0,4}"
    r"(?:number|no\.?|reg(?:istration)?\.?)?"
    r"[^A-Za-z0-9]{0,4}"
    r"((?:[A-Z]{2})?\d{6,8})")

# 8 characters: eight digits, or a two-letter prefix (SC, NI, OC, SO, FC, BR, NC)
# and six digits. Anything else is a typo in the seed, not a company number.
VALID_NUMBER = re.compile(r"^(?:[A-Z]{2}\d{6}|\d{8})$")


def suppliers():
    """Union of the two supplier files, by name, seed first.

    Same merge the rest of the repo does (build_supplier_index.py): the curated
    seed record wins, index-only records are added.
    """
    merged = {}
    for record in load(SEED, {"suppliers": []}).get("suppliers", []):
        merged.setdefault(record["name"], record)
    for record in load(INDEX, {"suppliers": []}).get("suppliers", []):
        merged.setdefault(record["name"], record)
    return [merged[name] for name in sorted(merged, key=str.lower)]


def free_text(supplier):
    """Everything a curator might have typed a company number into.

    `background` is read as well as `alerts` and `note`. On 20/08/2026 commit
    121ed36 moved 281 background notes out of alerts[] across 252 companies, so
    that Alerts & recalls held alerts again. The curator-typed company numbers
    moved with them, and 204 companies confirmed by route 1 silently dropped to
    "probable" on the next refresh — 36 of them still carrying a figure carried
    forward from the previous run, which is what failed the gate. The evidence
    never went anywhere; only the field it sits in changed.
    """
    parts = []
    for alert in supplier.get("alerts", []) or []:
        parts.append(alert if isinstance(alert, str) else json.dumps(alert))
    for note in supplier.get("background", []) or []:
        parts.append(note if isinstance(note, str) else json.dumps(note))
    parts.append(supplier.get("note") or "")
    return " ".join(parts)


def website_proof(supplier):
    """Route 2 — the number published on the company's OWN site, or None.

    Written by scripts/confirm_company_numbers.py from the evidence in
    state/domain-seeding-report.json. A proof without a URL and a verbatim
    evidence string is not a proof: it is refused here rather than trusted,
    because `matchedOn` has to be able to quote a source a reader can open.
    """
    proof = supplier.get("companyNumberProof")
    if not isinstance(proof, dict):
        return None
    number = str(proof.get("number") or "").upper()
    if proof.get("route") != "website-registration" or not VALID_NUMBER.match(number):
        return None
    if not proof.get("url") or not proof.get("evidence"):
        log("  %s: ignoring a companyNumberProof with no url/evidence — unciteable"
            % supplier["name"])
        return None
    return {"number": number, "url": proof["url"], "checkedOn": proof.get("checkedOn")}


def recorded_number(supplier):
    """(number, note, source) — number is None when there isn't exactly one clean answer.

    `source` is None, "alerts" (route 1) or a route-2 proof dict. It decides the
    wording of `matchedOn`, never the confidence: the confidence rule lives in
    record_for() and stays in one place.
    """
    found, malformed = set(), set()
    for raw in CH_NUMBER.findall(free_text(supplier)):
        candidate = raw.upper()
        (found if VALID_NUMBER.match(candidate) else malformed).add(candidate)
    if malformed:
        log("  %s: ignoring malformed company number(s) %s" % (supplier["name"], sorted(malformed)))

    proof = website_proof(supplier)

    if len(found) > 1:
        # Two anchored numbers is ambiguous whatever the site says: the seed
        # itself disagrees, and route 2 cannot arbitrate between two claims it
        # was never shown. Falls through to name search, exactly as before.
        return None, "two or more company numbers recorded (%s) — ambiguous, not guessed" % \
                     ", ".join(sorted(found)), None

    if found and proof:
        anchored = next(iter(found))
        if anchored != proof["number"]:
            # A sourced number disagreeing with another sourced number is a fact
            # to check by hand, not a tie to break in code.
            return None, ("the seed anchors %s but the company's own site publishes %s — two "
                          "sourced numbers disagree, not guessed" % (anchored, proof["number"])), None
        return anchored, "", proof

    if proof:
        return proof["number"], "", proof
    if found:
        return found.pop(), "", "alerts"
    return None, "", None


def corroborates(supplier, registered_name):
    """Does the registered name look like this supplier at all?"""
    ours = tokens(supplier["name"], *(supplier.get("aliases") or []))
    theirs = tokens(registered_name or "")
    return bool(ours & theirs)


def search_for(supplier, key):
    """Name search. Everything this returns is 'probable' — the method doc is
    explicit that a name-search match never feeds a derived claim.

    The bar is deliberately high: EVERY significant token of the supplier name
    must appear in the registered name. 'Abbott Diabetes Care' will not silently
    become 'Abbott Laboratories'. If nothing clears it, nothing is written —
    publishing no record is the correct output for thin evidence.
    """
    query = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9&. ]", " ", supplier["name"])).strip()
    want = tokens(supplier["name"])
    if not (query and want):
        return None
    result = api_get("/search/companies?" + urllib.parse.urlencode(
        {"q": query, "items_per_page": 20}), key)
    items = (result or {}).get("items") or []

    # Prefer a live company: a dissolved shell that happens to share a name is
    # the wrong answer for a supplier currently selling into the NHS.
    for wanted_status in ("active", None):
        for item in items:
            if wanted_status and item.get("company_status") != wanted_status:
                continue
            if want <= tokens(item.get("title") or ""):
                return item.get("company_number")
    return None


# THE 17 -> 7 PROBLEM, AND WHY MOST VALUES ARE DELIBERATELY LEFT UNPLACED.
# The API returns Companies House's own seventeen-value accounts enum. What the
# Hub publishes is a seven-value vocabulary describing the KIND of accounts filed
# (verify.py's ACCOUNTS_CATEGORIES). Six values mean the same thing in both and
# are mapped. The rest are audit-exemption and abridgement variants: they say
# something about the filing REGIME, not about which kind of accounts were filed,
# and mapping them would be our inference wearing a statutory label. Those stay
# UNPLACED — accountsCategory null — with the raw value recorded beside them, so
# nothing is lost and nothing is guessed.
#
# The visible consequence, stated because it is a real trade-off and not a bug:
# a field made up mostly of exemption filers will fall below the field filing
# profile's half-the-field floor and the panel will refuse. That is the honest
# outcome until somebody decides, with a stated rule, what those values mean for
# size. Do NOT widen verify.py's list to make them pass (root rule 13).
ACCOUNTS_MAP = {
    "full": "full",
    "small": "small",
    "medium": "medium",
    "group": "group",
    "dormant": "dormant",
    "micro-entity": "micro-entity",
}
ACCOUNTS_UNPLACED = {
    "interim", "initial", "total-exemption-full", "total-exemption-small",
    "partial-exemption", "audit-exemption-subsidiary", "filing-exemption-subsidiary",
    "no-accounts-type-available", "audited-abridged", "unaudited-abridged",
}


def map_accounts_type(raw):
    """(publication category or None, note). Never guesses."""
    if not raw:
        return None, "no accounts type on the record"
    if raw in ACCOUNTS_MAP:
        return ACCOUNTS_MAP[raw], None
    if raw in ACCOUNTS_UNPLACED:
        return None, ("Companies House reports %r, an audit-exemption or abridgement variant. "
                      "It is recorded but deliberately not mapped to a filing category, because "
                      "that would be an inference about size dressed as a statutory value." % raw)
    # A value nobody has seen before. Say so loudly rather than dropping it.
    return None, ("Companies House returned %r, which is not in the seventeen-value enum this "
                  "script knows. Add it to ACCOUNTS_MAP or ACCOUNTS_UNPLACED in "
                  "scripts/refresh_companies_house.py and to the table in "
                  "docs/COMPANY-REPORT-METHOD.md before trusting it." % raw)


def officers_for(number, key):
    """Current officers and dated appointment/resignation events.

    Register facts only. This never says one person replaced another: succession
    is not on the register, and asserting it is the 24/07/2026 stakeholder-mapper
    error with different names in it.
    """
    data = api_get("/company/" + urllib.parse.quote(number) + "/officers", key)
    if not data:
        return None
    current, changes = [], []
    for it in (data.get("items") or []):
        name = (it.get("name") or "").strip()
        if not name:
            continue
        role = (it.get("officer_role") or "").replace("-", " ").title()
        appointed, resigned = it.get("appointed_on"), it.get("resigned_on")
        if not resigned:
            current.append({"name": name, "role": role, "appointed": appointed})
        if appointed:
            changes.append({"name": name, "role": role, "event": "appointed", "date": appointed})
        if resigned:
            changes.append({"name": name, "role": role, "event": "resigned", "date": resigned})
    if not current and not changes:
        return None
    changes.sort(key=lambda c: c["date"] or "", reverse=True)
    current.sort(key=lambda c: c["appointed"] or "", reverse=True)
    return {
        "readOn": datetime.date.today().isoformat(),
        "sourceUrl": FIND + number + "/officers",
        "note": ("Statutory register facts only. Appointments and resignations are listed as "
                 "dated events; this file never asserts that one person replaced another, "
                 "because succession is not a register fact."),
        "current": current,
        "recentChanges": changes[:12],
    }


def record_for(supplier, number, confirmed_source, key):
    """One entry in `companies`, or None if the number does not resolve."""
    profile = api_get("/company/" + urllib.parse.quote(number), key)
    if not profile:
        return None

    accounts = (profile.get("accounts") or {}).get("last_accounts") or {}
    registered = profile.get("company_name") or ""
    status = profile.get("company_status")
    _cat, _cat_note = map_accounts_type(accounts.get("type"))

    # The confidence rule, in one place. See the module docstring.
    if not confirmed_source:
        confidence, matched_on = "probable", "name search on Companies House — NOT verified against a recorded number"
    elif not corroborates(supplier, registered):
        confidence, matched_on = "probable", ("company number recorded in supplier data, but the "
                                              "registered name %r does not corroborate the supplier "
                                              "name — check by hand" % registered)
    elif status != "active":
        confidence, matched_on = "probable", ("company number recorded in supplier data, but the "
                                              "company is %s, not active — check the supplier now "
                                              "trades through a different entity" % status)
    elif isinstance(confirmed_source, dict):
        # Route 2 (docs/COMPANY-REPORT-METHOD.md): the number the company itself
        # publishes. The URL is quoted so a reader can open the page it came from.
        confidence, matched_on = "confirmed", (
            "company number published on the company's own website, agreeing with the "
            "Companies House record — %s, read %s"
            % (confirmed_source["url"], confirmed_source.get("checkedOn") or "on an unrecorded date"))
    else:
        confidence, matched_on = "confirmed", ("company number recorded by a curator in the supplier's own "
                                                "seed record (alerts, background or note)")

    return {
        "companyNumber": profile.get("company_number") or number,
        "registeredName": registered,
        "matchConfidence": confidence,
        "matchedOn": matched_on,
        "status": status,
        "incorporated": profile.get("date_of_creation"),
        "sic": profile.get("sic_codes") or [],
        # The API's own enum, mapped to the publication vocabulary ONLY where the
        # two mean the same thing; everything else stays unplaced with the raw
        # value recorded. See ACCOUNTS_MAP.
        "accountsCategory": _cat,
        "accountsCategoryRaw": accounts.get("type"),
        "accountsCategoryNote": _cat_note,
        # made_up_to is deprecated in the spec in favour of period_end_on; take
        # the current field first and fall back so older records still date.
        "accountsMadeUpTo": accounts.get("period_end_on") or accounts.get("made_up_to"),
        # ⚠️ The API returns neither. Null means "not disclosed" and the page must
        # print that phrase. Only a stage that has actually parsed a filed
        # document may ever set these.
        "turnoverGBP": None,
        "employees": None,
        "sourceUrl": FIND + (profile.get("company_number") or number),
        # Officers are fetched for CONFIRMED matches only. Attaching a board to a
        # company we are only probably looking at names the wrong people.
        "officers": (officers_for(profile.get("company_number") or number, key)
                     if confidence == "confirmed" else None),
    }


def main():
    offline = "--offline" in sys.argv
    out_path = arg("--out", OUT)
    limit = arg("--limit")
    limit = int(limit) if limit else None

    if limit and os.path.abspath(out_path) == os.path.abspath(OUT):
        raise SystemExit("ABORT: --limit builds a PARTIAL file. It may not be written to %s, which "
                         "is served straight to paying members. Pass --out somewhere else." % OUT)

    people = suppliers()
    if len(people) < 200:
        raise SystemExit("ABORT: only %d suppliers loaded from %s + %s (expected 400+) — refusing "
                         "to build a report over a collapsed supplier list." % (len(people), SEED, INDEX))
    if limit:
        people = people[:limit]

    with_number = [(s, recorded_number(s)) for s in people]
    have = sum(1 for _, (n, _, _) in with_number if n)
    by_site = sum(1 for _, (n, _, src) in with_number if n and isinstance(src, dict))
    log("%d suppliers | %d carry a recorded company number (%d of them proved on the "
        "company's own website) | %d need a name search"
        % (len(people), have, by_site, len(people) - have))

    if offline:
        # No network at all, so nothing can be verified, so nothing is written.
        # A file built offline would be a file of unverified claims.
        ambiguous = [s["name"] for s, (n, why, _) in with_number if not n and why]
        log("--offline: no requests made and no file written.")
        log("a live run would make about %d Companies House requests "
            "(%d profile + %d search-then-profile)"
            % (have + 2 * (len(people) - have), have, len(people) - have))
        if ambiguous:
            log("%d suppliers name more than one company number and would fall through to "
                "name search: %s" % (len(ambiguous), ", ".join(ambiguous)))
        return 0

    key = load_key()

    thresholds = read_thresholds()
    log("thresholds read from GOV.UK: micro £%s / small £%s / medium £%s turnover, %s"
        % ("{:,}".format(thresholds["bands"]["micro"]["turnoverGBP"]),
           "{:,}".format(thresholds["bands"]["small"]["turnoverGBP"]),
           "{:,}".format(thresholds["bands"]["medium"]["turnoverGBP"]),
           thresholds["appliesTo"]))

    companies, unresolved, downgraded = {}, [], []
    for i, (supplier, (number, why, source)) in enumerate(with_number, 1):
        if why:
            log("  %s: %s" % (supplier["name"], why))
        from_record = source if number else None
        if not number:
            number = search_for(supplier, key)
        if not number:
            unresolved.append(supplier["name"])
            continue
        entry = record_for(supplier, number, from_record, key)
        if not entry:
            unresolved.append(supplier["name"] + " (number %s does not resolve)" % number)
            continue
        companies[supplier["name"]] = entry
        if from_record and entry["matchConfidence"] == "probable":
            downgraded.append("%s -> %s (%s)" % (supplier["name"], entry["registeredName"],
                                                 entry["matchedOn"]))
        if i % 50 == 0:
            log("%d/%d | %d resolved" % (i, len(with_number), len(companies)))

    if not companies:
        raise SystemExit("ABORT: nothing resolved. Refusing to write an empty report.")

    # Shrink guard, same rule as the other refresh scripts: a run that loses a
    # fifth of the file is a broken run, not a smaller register.
    previous = load(out_path, None)
    if previous and not limit:
        was = len(previous.get("companies") or {})
        if was and len(companies) < 0.8 * was:
            raise SystemExit("ABORT: resolved %d companies vs %d previously — refusing to shrink "
                             "the report." % (len(companies), was))

    # CARRY FORWARD WHAT THIS SCRIPT DID NOT FETCH.
    # This builds every record from scratch, so writing straight out silently
    # DELETED the turnover series, headcounts and their notes that
    # extract_accounts_figures.py had read from the filed accounts — work that
    # costs hundreds of document fetches to redo. The two scripts have to
    # compose: this one owns the profile and the officers, that one owns the
    # figures, and neither may destroy the other's fields.
    # READ THE FIGURES FROM THE CANONICAL FILE, NOT FROM --out. This used to read
    # out_path, so a run to a scratch file — the safe way to inspect a diff before
    # publishing — carried nothing forward, silently dropping turnover for 18
    # companies, headcount for 72 and both figuresAsOf and figuresSource. The
    # output looked complete and was not, and copying it over the live file would
    # have published the loss. Found 12/08/2026. The figures live in OUT whatever
    # this run is writing to, so that is where they are read from.
    carried = 0
    KEEP = ("turnoverGBP", "turnoverSeries", "turnoverNote", "employees", "employeesNote")
    previous = {}
    prev_doc = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                prev_doc = json.load(f)
            previous = prev_doc.get("companies") or {}
        except (ValueError, OSError):
            previous, prev_doc = {}, {}
    for name, rec in companies.items():
        old_rec = previous.get(name)
        if not isinstance(old_rec, dict):
            continue
        for k in KEEP:
            if old_rec.get(k) not in (None, [], "") and rec.get(k) in (None, [], ""):
                rec[k] = old_rec[k]
                if k == "turnoverGBP":
                    carried += 1
    if carried:
        log("carried forward turnover for %d company(ies) already read from the filed "
            "accounts (this script does not fetch figures)" % carried)

    out = {
        "dataAsOf": datetime.date.today().isoformat(),
        "source": "Companies House public data API (%s)" % API,
        "thresholds": thresholds,
        "companies": {name: companies[name] for name in sorted(companies, key=str.lower)},
    }
    for k in ("figuresAsOf", "figuresSource"):
        if k in prev_doc:
            out[k] = prev_doc[k]
    # indent=1, ensure_ascii=False — the house style stamp_notice.py can detect
    # and re-stamp without reformatting the whole file.
    json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)

    confirmed = sum(1 for c in companies.values() if c["matchConfidence"] == "confirmed")
    with_category = sum(1 for c in companies.values() if c["accountsCategory"])
    log("wrote %s: %d companies (%d confirmed, %d probable), %d with an accounts category"
        % (out_path, len(companies), confirmed, len(companies) - confirmed, with_category))

    if downgraded:
        log("CHECK BY HAND — %d recorded numbers did not pass the confirmation rule and are "
            "flagged probable, so they will not feed any derived claim:" % len(downgraded))
        for line in downgraded:
            log("  - " + line)
    if unresolved:
        log("%d suppliers left with no Companies House record (nothing written for them, which is "
            "the correct output for thin evidence): %s%s"
            % (len(unresolved), ", ".join(unresolved[:15]),
               " ..." if len(unresolved) > 15 else ""))
    if os.path.abspath(out_path) == os.path.abspath(OUT):
        log("NOT PUBLISHABLE YET: mint a ref for company-financials.json from the private salt, add "
            "it to REFS in scripts/stamp_notice.py, run stamp_notice.py, then verify.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
