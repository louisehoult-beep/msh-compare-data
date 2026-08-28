#!/usr/bin/env python3
"""
NHS England Central Commercial Function (CCF): the openly published reference.

Most of CCF's substance sits on FutureNHS behind a login, including the actual
procurement value and savings methodology. Two things ARE open and are worth
holding, because reps routinely get both wrong:

  1. The accredited FRAMEWORK HOST list. There is no public national register of
     frameworks with their awarded suppliers, but there IS a published list of the
     organisations accredited to host NHS frameworks. That answers "who runs this
     framework", which is the question behind most framework confusion.

  2. The official supplier-engagement position on Supplying to the NHS, including
     NHS England's own instruction that suppliers register on Atamis.

Both are fetched live rather than typed in, so the Hub is never quoting a stale
copy of a page that has moved on (root CLAUDE.md rules 12 and 16).

INVARIANT (root CLAUDE.md rule 14)
----------------------------------
The host list stood at 18 organisations when this was built (28/08/2026), against
guidance last updated 26/08/2026. If a run finds a materially different number the
script writes nothing and says so, rather than quietly shrinking a list the Hub
presents as complete. A changed list is a real event worth a human look, not
something to absorb silently.

Note: Crown Commercial Service became the GOVERNMENT COMMERCIAL AGENCY (GCA) on
1 April 2026, and NHS England's own list now says GCA. Anything in the Hub still
naming Crown Commercial Service is out of date.

Usage:
    python3 scripts/refresh_ccf_reference.py
    python3 scripts/refresh_ccf_reference.py --allow-count-change
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HOSTS_URL = ("https://www.england.nhs.uk/long-read/"
             "system-guidance-for-the-implementation-of-framework-host-management/")
SUPPLYING_URL = "https://www.england.nhs.uk/nhs-commercial/supplying-to-the-nhs/"
CCF_URL = "https://www.england.nhs.uk/nhs-commercial/central-commercial-function-ccf/"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
OUT = os.path.join(DATA, "ccf-reference.json")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

EXPECTED_HOST_COUNT = 18

# The hosts are named in a list on the page. Anchor on the known names so a
# theme change does not silently empty the list: every one of these was verified
# present on 28/08/2026, and the matcher reports which were and were not found.
KNOWN_HOSTS = [
    "Countess of Chester",
    "Government Commercial Agency",
    "East of England Collaborative Procurement Hub",
    "Eastern Shires Purchasing Organisation",
    "Efficiency East Midlands",
    "HealthTrust Europe",
    "NHS London Procurement Partnership",
    "WSP UK Ltd",
    "NHS Shared Business Services",
    "NHS Commercial Solutions",
    "NHS Supply Chain",
    "NHS Workforce Alliance",
    "NHS England",
    "North of England Commercial Procurement Collaborative",
    "North Midlands and Black Country Procurement Group",
    "Northumbria NHS Foundation Trust",
    "Pagabo",
    "Salisbury Foundation Trust",
]

# Hosts whose own framework pages we know to be publicly readable, and how.
# Recorded here so the Hub can say where a framework's supplier list can be
# checked, rather than implying we hold every framework centrally.
HOST_ACCESS = {
    "NHS Supply Chain": {
        "public_supplier_lists": True,
        "where": "https://www.supplychain.nhs.uk/product-information/contract-launch-briefs/",
        "note": ("Contract launch briefs publish the named supplier list, framework "
                 "reference, start and expiry dates, and the suppliers delisted at "
                 "framework start. Richest public operator source."),
    },
    "NHS Shared Business Services": {
        "public_supplier_lists": True,
        "where": "https://www.sbs.nhs.uk/services/framework-agreements/",
        "note": "One page per framework, each naming its awarded suppliers.",
    },
    "Government Commercial Agency": {
        "public_supplier_lists": True,
        "where": "https://www.gca.gov.uk/agreements",
        "note": ("Formerly Crown Commercial Service, renamed 01/04/2026. Supplier "
                 "lists sit on individual agreement pages; no bulk export."),
    },
    "HealthTrust Europe": {
        "public_supplier_lists": False,
        "where": "https://www.find-tender.service.gov.uk/",
        "note": ("Their own site returns 403 to automated fetches, but their "
                 "framework award notices carry full supplier lists on Find a "
                 "Tender. Use data/framework-awards.json."),
    },
    "NHS London Procurement Partnership": {
        "public_supplier_lists": False,
        "where": "https://www.lpp.nhs.uk/frameworks/",
        "note": "Framework listings public; full detail needs an access agreement.",
    },
    "North of England Commercial Procurement Collaborative": {
        "public_supplier_lists": False,
        "where": "https://www.noecpc.nhs.uk/contracts",
        "note": ("Overviews public, documentation gated. No medical devices or "
                 "diagnostics category, so low relevance to device reps."),
    },
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch(url: str, tries: int = 3) -> str | None:
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == tries:
                log("  FETCH FAILED: %s (%s)" % (url[:90], exc))
                return None
            time.sleep(3 * attempt)
    return None


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def page_updated(page: str) -> str | None:
    m = re.search(r"(?:Page last reviewed|Last updated)[:\s]*</?[^>]*>?\s*"
                  r"(\d{1,2}\s+\w+\s+\d{4})", page, re.I)
    if m:
        return m.group(1)
    m = re.search(r'"dateModified"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2})', page)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-count-change", action="store_true",
                    help="write even if the host count has moved from the expected 18")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    log("CCF reference refresh  %s" % now.isoformat(timespec="seconds"))

    hosts_page = fetch(HOSTS_URL)
    if not hosts_page:
        log("FAILED: could not fetch the framework host guidance. Nothing written.")
        return 1

    text = strip_tags(hosts_page)

    found, missing = [], []
    for name in KNOWN_HOSTS:
        if re.search(re.escape(name), text, re.I):
            found.append(name)
        else:
            missing.append(name)

    log("  host list: %d of %d known names present on the page"
        % (len(found), len(KNOWN_HOSTS)))
    if missing:
        log("  NOT FOUND on the page: %s" % ", ".join(missing))

    if len(found) != EXPECTED_HOST_COUNT and not args.allow_count_change:
        log("")
        log("  STOPPING: expected %d accredited hosts, matched %d."
            % (EXPECTED_HOST_COUNT, len(found)))
        log("  The published list has probably changed, which is a real event and")
        log("  needs a human look, not a silent overwrite. Read the page, update")
        log("  KNOWN_HOSTS and EXPECTED_HOST_COUNT, then re-run. To write anyway:")
        log("      python3 scripts/refresh_ccf_reference.py --allow-count-change")
        return 1

    supplying_page = fetch(SUPPLYING_URL)
    supplying = {}
    if supplying_page:
        body = strip_tags(supplying_page)
        m = re.search(r"(We buy goods and services.{0,600})", body)
        supplying = {
            "url": SUPPLYING_URL,
            "updated": page_updated(supplying_page),
            "extract": m.group(1).strip() if m else None,
            "registers_on_atamis": bool(re.search(r"Atamis", body, re.I)),
            "contact": "england.supplier@nhs.net"
            if "england.supplier@nhs.net" in body else None,
        }
    else:
        log("  WARNING: could not fetch Supplying to the NHS; recording hosts only.")

    hosts = []
    for name in found:
        rec = {"name": name}
        rec.update(HOST_ACCESS.get(name, {}))
        hosts.append(rec)
    hosts.sort(key=lambda h: h["name"].lower())

    out = {
        "source": "NHS England, Central Commercial Function",
        "generated": now.isoformat(timespec="seconds"),
        "framework_hosts": {
            "source_url": HOSTS_URL,
            "page_updated": page_updated(hosts_page),
            "accreditation": (
                "Accreditation is granted through the Central Commercial Function "
                "(CCF) Steering Board, the formal governance route for the scheme. "
                "Framework host accreditation concluded in January 2024, with "
                "requirements taking effect from 1 April 2024."
            ),
            "count": len(hosts),
            "note": (
                "This is the list of organisations accredited to HOST NHS frameworks. "
                "It is not a register of frameworks, and it does not name any awarded "
                "supplier. No public national register of frameworks with their "
                "suppliers exists. Supplier lists come from the individual host, or "
                "from Find a Tender award notices: see data/framework-awards.json."
            ),
            "rename_note": (
                "Crown Commercial Service became the Government Commercial Agency "
                "(GCA) on 1 April 2026. Anything still naming Crown Commercial "
                "Service is out of date."
            ),
            "hosts": hosts,
        },
        "supplying_to_the_nhs": supplying,
        "ccf_overview_url": CCF_URL,
        "gated_note": (
            "The CCF Best Practice Hub on FutureNHS (future.nhs.uk/CCF_Hub) holds the "
            "procurement value and savings methodology, Spend Comparison Service "
            "training and data integration workflows. All of it needs a FutureNHS "
            "login and is not available to the Hub."
        ),
    }

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)

    log("")
    log("  wrote data/ccf-reference.json (%d accredited hosts)" % len(hosts))
    pub = sum(1 for h in hosts if h.get("public_supplier_lists"))
    log("  hosts with publicly readable supplier lists: %d" % pub)
    return 0


if __name__ == "__main__":
    sys.exit(main())
