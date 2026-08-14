#!/usr/bin/env python3
"""Find and PROVE the official website of a supplier, then seed it.

WHY THIS EXISTS (added 14/08/2026)
----------------------------------
`crawl_supplier_site.py --auto` finished its sweep on 13/08/2026 at 135 of 548
suppliers accounted for. It cannot advance, and the reason is not the crawler:
310 framework-named suppliers have NO WEBSITE recorded anywhere in the data, so
there is nothing for it to read. The next move is domains, not crawler changes.

THE DANGER THIS SCRIPT IS BUILT AROUND. Guessing a domain from a company name is
easy and almost right, and "almost right" here is worse than nothing: the
crawler would read the wrong company's catalogue and publish it, on a paid page,
as this supplier's own product range. A supplier with no range falls back to the
seed's curated list and the member sees something honest. A supplier with the
WRONG range sees a confident lie. So a guess is only ever a CANDIDATE here, and
nothing is written until the site itself proves who it belongs to.

THE RULE THIS WRITES UNDER (root rule 14 — state the rule, set an evidence floor)
---------------------------------------------------------------------------------
A domain is recorded only on one of two proofs, both taken from the live site:

  REGISTRATION  the site publishes a company registration number, next to
                registration wording, that matches the Companies House number
                already recorded for this supplier in company-financials.json.
                This is the strong proof: a number is unique to one company and
                cannot be coincidence.

  NAME          the site's own <title> or og:site_name contains the supplier's
                distinctive core name, AND that core name is distinctive enough
                to be evidence (see DISTINCTIVE_MIN and STOP_CORES). This is the
                weaker proof and is only accepted with --accept-name.

Anything else is REFUSED and written to the report, never to the seed. An
unproven supplier keeps its curated list. Publishing nothing is the correct
output when the evidence is thin.

Evidence is recorded beside every domain it writes — the proof kind, the string
that matched, the URL it was read from and the date — so a reader can judge it
later without re-running anything.

USAGE
  python3 scripts/seed_supplier_domains.py                 # report only, writes nothing
  python3 scripts/seed_supplier_domains.py --limit 25      # try 25 suppliers
  python3 scripts/seed_supplier_domains.py --write         # merge proven domains into the seed
  python3 scripts/seed_supplier_domains.py --accept-name --write

Writes data/supplier-seed.json (the curated, human-owned file — the index rebuild
copies seed records wholesale, so a domain put here survives; one put straight
into supplier-index.json is destroyed by the next nightly rebuild).
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import gzip
import io
import json
import re
import ssl
import sys
import urllib.error
import urllib.request

SEED = "data/supplier-seed.json"
INDEX = "data/supplier-index.json"
FW = "data/frameworks.json"
FIN = "data/company-financials.json"
REPORT = "state/domain-seeding-report.json"

UA = ("Mozilla/5.0 (compatible; MedSalesHubBot/1.0; +https://medsalesintelligencehub.co.uk) "
      "supplier range capture")
TIMEOUT = 15

# Hosts that can never be a supplier's own site. A redirect that lands on one of
# these is a dead candidate, not a find.
NEVER = ("linkedin.", "facebook.", "twitter.", "x.com", "instagram.", "youtube.",
         "wikipedia.", "amazon.", "ebay.", "companieshouse.", "gov.uk",
         "supplychain.nhs", "nhs.uk", "bloomberg.", "crunchbase.", "indeed.",
         "glassdoor.", "yell.com", "endole.", "opencorporates.", "trustpilot.")

# A parked or for-sale domain answers 200 and looks like a website. It is not one.
PARKED = ("domain is for sale", "buy this domain", "this domain may be for sale",
          "parked free", "godaddy.com/domainsearch", "sedoparking", "hugedomains",
          "under construction", "coming soon</", "namecheap.com/domains")

# A core name shorter than this proves nothing on its own — "MSL", "AGP", "ABC"
# match half the web. Registration proof is still accepted for these.
DISTINCTIVE_MIN = 6

# Core names that are real words and therefore not evidence of anything.
STOP_CORES = {"advance", "advanced", "alliance", "apex", "aspire", "assist", "care",
              "clinical", "complete", "direct", "elite", "essential", "first",
              "global", "innovate", "integra", "life", "lifeline", "matrix",
              "nova", "optimum", "premier", "prime", "pulse", "select", "summit",
              "support", "surgical", "unity", "vision", "vital", "wellbeing"}

SUFFIXES = re.compile(
    r"\b(ltd|limited|plc|llp|llc|inc|corp|corporation|co|company|group|holdings|"
    r"international|uk|u k|gb|great britain|england|europe|emea|healthcare|"
    r"health|medical|med|medic|products|product|solutions|systems|technologies|"
    r"technology|devices|device|services|service|supplies|scientific|"
    r"diagnostics|pharma|pharmaceuticals|laboratories|labs)\b")

REG_WORDS = re.compile(
    r"(registered\s+(?:in|number|no|office|company)|company\s+(?:number|no|reg)|"
    r"reg(?:istration)?\.?\s*(?:number|no)|companies\s+house|vat\s+(?:number|no))",
    re.I)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s).lower())).strip()


def core(name):
    """The distinctive part of a company name — suffixes and trade words stripped."""
    return re.sub(r"\s+", " ", SUFFIXES.sub(" ", norm(name))).strip()


def slugs(name):
    """Candidate domain labels, most likely first."""
    c = core(name)
    n = norm(name)
    out = []
    for base in (c, n):
        if not base:
            continue
        parts = base.split()
        for label in ("".join(parts), "-".join(parts), parts[0] if parts else ""):
            if label and 2 < len(label) <= 40 and label not in out:
                out.append(label)
    return out


def candidates(name, aliases, registered):
    """Domains worth trying, in order. Generation is cheap; proof is what counts."""
    seen, out = set(), []
    names = [name] + [a for a in (aliases or []) if a != name]
    if registered:
        names.append(registered)
    for nm in names:
        for label in slugs(nm):
            for tld in (".co.uk", ".com", ".uk", ".eu", ".net"):
                d = label + tld
                if d not in seen:
                    seen.add(d)
                    out.append(d)
    return out


def fetch(url):
    """GET a page. Returns (final_url, text) or (None, None). Never raises."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,*/*",
        "Accept-Encoding": "gzip", "Accept-Language": "en-GB,en;q=0.9"})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE          # a bad cert is not proof of identity either way
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            raw = r.read(600_000)
            if r.headers.get("Content-Encoding") == "gzip":
                try:
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                except OSError:
                    pass
            return r.geturl(), raw.decode("utf-8", "replace")
    except Exception:
        # DELIBERATELY BROAD. This is a probe of several hundred strangers'
        # servers, and every way one of them can be broken — a truncated
        # chunked body, a bad redirect, a malformed header, a certificate that
        # does not parse — means the same thing here: no page, try the next
        # candidate. An earlier version listed the exceptions it expected and
        # a single http.client.IncompleteRead killed a 40-minute sweep at
        # supplier 210 of 252, losing every result with it.
        return None, None


def text_of(html):
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html or "")
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def title_of(html):
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html or "")
    t = m.group(1) if m else ""
    m = re.search(r'(?is)<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)',
                  html or "")
    return re.sub(r"\s+", " ", (t + " " + (m.group(1) if m else ""))).strip()


def number_forms(ch_number):
    """The ways a real site writes its own registration number."""
    n = str(ch_number or "").strip().upper()
    if not n:
        return []
    forms = {n}
    if n.isdigit():
        forms.add(n.lstrip("0"))
        forms.add(n.zfill(8))
    return [f for f in forms if len(f) >= 6]


def prove(name, ch_number, pages, accept_name):
    """Return (proof_kind, evidence, url) or (None, why_refused, None)."""
    c = core(name)
    for url, html in pages:
        if not html:
            continue
        body = text_of(html)
        low = body.lower()
        if any(p in low for p in PARKED):
            return None, "candidate answered but is a parked or for-sale domain", None

        # REGISTRATION — the strong proof.
        for form in number_forms(ch_number):
            for m in re.finditer(re.escape(form), body, re.I):
                window = body[max(0, m.start() - 160):m.end() + 160]
                if REG_WORDS.search(window):
                    return ("registration",
                            "site states registration number %s (%s)" % (
                                form, re.sub(r"\s+", " ", window.strip())[:180]),
                            url)

    if accept_name and c and len(c) >= DISTINCTIVE_MIN and c not in STOP_CORES:
        for url, html in pages:
            if not html:
                continue
            t = title_of(html)
            if c.replace(" ", "") in norm(t).replace(" ", ""):
                return ("name", "site title names the company: %r" % t[:140], url)

    return None, "site read, but it never identifies itself as this company", None


def try_supplier(rec, ch_number, max_candidates):
    name = rec["name"]
    tried = []
    for d in candidates(name, rec.get("aliases"), (ch_number or {}).get("registeredName"))[:max_candidates]:
        for scheme in ("https://www.", "https://"):
            final, html = fetch(scheme + d)
            if not html:
                continue
            if any(b in (final or "").lower() for b in NEVER):
                tried.append((d, "redirected to a third-party host"))
                break
            pages = [(final, html)]
            # Registration numbers live on the legal pages far more often than
            # the homepage, so read those too before deciding.
            base = re.match(r"(https?://[^/]+)", final or "")
            if base:
                for path in ("/contact", "/contact-us", "/privacy-policy",
                             "/terms", "/legal", "/about-us"):
                    u, h = fetch(base.group(1) + path)
                    if h:
                        pages.append((u, h))
            kind, ev, url = prove(name, (ch_number or {}).get("companyNumber"),
                                  pages, try_supplier.accept_name)
            if kind:
                return {"name": name, "proof": kind, "domain": re.sub(r"^https?://", "", final).split("/")[0],
                        "url": url, "evidence": ev,
                        "companyNumber": (ch_number or {}).get("companyNumber"),
                        "checked": dt.date.today().isoformat()}
            tried.append((d, ev))
            break
    return {"name": name, "proof": None,
            "reason": (tried[0][1] if tried else "no candidate domain answered"),
            "candidatesTried": [d for d, _ in tried] or "none answered",
            "checked": dt.date.today().isoformat()}


try_supplier.accept_name = False


def domain_for(rec):
    """Same test crawl_supplier_site.py applies — kept identical on purpose."""
    for l in (rec.get("links") or []):
        u = l.get("url") if isinstance(l, dict) else l
        m = re.search(r"https?://([^/]+)", str(u or ""))
        if m and not any(x in m.group(1) for x in ("gov.uk", "supplychain", "nhs.uk", "linkedin")):
            return m.group(1)
    m = re.search(r"logo\.clearbit\.com/([^/?]+)|domain=([^&]+)", rec.get("image") or "")
    return (m.group(1) or m.group(2)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="how many suppliers to attempt (0 = all)")
    ap.add_argument("--write", action="store_true", help="merge proven domains into the seed")
    ap.add_argument("--accept-name", action="store_true",
                    help="also accept the weaker title-match proof")
    ap.add_argument("--candidates", type=int, default=6,
                    help="candidate domains to try per supplier (default 6)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--supplier", help="attempt one named supplier only")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore the banked report and re-probe every supplier")
    a = ap.parse_args()
    try_supplier.accept_name = a.accept_name

    seed = json.load(open(SEED, encoding="utf-8"))
    fin = json.load(open(FIN, encoding="utf-8"))["companies"]
    fw = json.load(open(FW, encoding="utf-8"))

    onfw = set()
    for f in fw["frameworks"]:
        for x in f["suppliers"]:
            k = core(x)
            if k:
                onfw.add(k)

    todo = [s for s in seed["suppliers"]
            if not domain_for(s) and (core(s["name"]) in onfw)]
    if a.supplier:
        todo = [s for s in seed["suppliers"] if s["name"] == a.supplier]
    if a.limit:
        todo = todo[:a.limit]
    print("%d supplier(s) to attempt (framework-named, no website on record)" % len(todo),
          flush=True)
    if not todo:
        return

    # Resume. A sweep is ~40 minutes of other people's servers; losing it to one
    # broken host is unacceptable, so every result is banked as it lands and a
    # re-run skips what is already decided (--fresh starts over).
    done = {}
    if not a.fresh:
        try:
            done = {r["name"]: r for r in json.load(open(REPORT, encoding="utf-8"))["results"]}
        except (OSError, ValueError, KeyError):
            done = {}
    if done:
        before = len(todo)
        todo = [s for s in todo if s["name"] not in done]
        print("  resuming: %d already decided in %s, %d left"
              % (before - len(todo), REPORT, len(todo)), flush=True)

    results = list(done.values())

    def bank():
        json.dump({"_notice": "Evidence for every domain written to supplier-seed.json by "
                              "scripts/seed_supplier_domains.py. Report only — no consumer reads this.",
                   "generated": dt.date.today().isoformat(),
                   "acceptedNameProof": a.accept_name,
                   "results": sorted(results, key=lambda r: r["name"])},
                  open(REPORT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(try_supplier, s, fin.get(s["name"]), a.candidates): s["name"]
                for s in todo}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            try:
                r = fut.result()
            except Exception as e:                      # one bad host is not a failed sweep
                r = {"name": futs[fut], "proof": None,
                     "reason": "probe failed: %s: %s" % (type(e).__name__, e),
                     "checked": dt.date.today().isoformat()}
            results.append(r)
            if i % 10 == 0:
                bank()
            print("  %s %-38s %s" % ("OK " if r["proof"] else " --", r["name"][:38],
                                     r.get("domain") or r.get("reason", "")[:60]), flush=True)
            if i % 25 == 0:
                print("  ... %d of %d" % (i, len(todo)), flush=True)

    proven = [r for r in results if r["proof"]]
    byreg = [r for r in proven if r["proof"] == "registration"]
    print("\nproven      : %d of %d attempted" % (len(proven), len(results)))
    print("  by registration number : %d" % len(byreg))
    print("  by site title          : %d" % (len(proven) - len(byreg)))
    print("unproven    : %d (left alone — they keep their curated list)"
          % (len(results) - len(proven)))

    bank()
    print("evidence report: %s" % REPORT)

    if not a.write:
        print("\nreport only — nothing written to the seed. Re-run with --write to seed them.")
        return

    by_name = {s["name"]: s for s in seed["suppliers"]}
    added = 0
    for r in proven:
        rec = by_name.get(r["name"])
        if rec is None:
            continue
        rec.setdefault("links", []).append({
            "label": "Company website",
            "url": "https://" + r["domain"],
            "source": "Proved %s by %s on %s: %s" % (
                r["domain"], "registration number" if r["proof"] == "registration"
                else "site title", r["checked"], r["evidence"])})
        added += 1
    # MATCH THE FILE'S OWN FORMAT. supplier-seed.json is stored minified on a
    # single line with no trailing newline. Writing it back pretty-printed is a
    # 35,000-line diff for 25 added links, which buries the actual change and
    # makes every future diff of this file useless. Byte-format is not cosmetic
    # in a repo where a push is a live publish and the diff is the only review.
    with open(SEED, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, separators=(",", ":"))
    print("\nseeded %d website(s) into %s" % (added, SEED))
    print("next: python3 build_supplier_index.py, then python3 verify.py")


if __name__ == "__main__":
    main()
