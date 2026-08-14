#!/usr/bin/env python3
"""Promote website-proved registration numbers into supplier-seed.json.

WHY THIS EXISTS
---------------
598 suppliers carry a Companies House record; 380 of them are `matchConfidence:
"probable"`, and 356 of those are probable for one reason only — the number came
from a name search and nothing has ever corroborated it. A probable record feeds
no derived claim, carries no officers block and is excluded from the Stage 4
field-position bands, so those 380 companies get a visibly thinner report than
the 218 confirmed ones.

`docs/COMPANY-REPORT-METHOD.md` already names the route out, and has since
06/08/2026 — accepted confirmation route 2, "the company number published on the
company's **own** website (imprint/terms page), agreeing with the CH record".
It was specified and never implemented.

The evidence for it is already sitting in the repo, in two files, written by two
jobs that were both looking for something else:

  * `state/domain-seeding-report.json` — `scripts/seed_supplier_domains.py` reads
    candidate sites and refuses to record a domain unless the site publishes a
    registration number, beside registration wording, matching the number already
    held for that supplier in `company-financials.json`.
  * `state/name-proof-verification.json` — `scripts/verify_name_proofs.py`
    second-sources the 128 domains that had been accepted on a site TITLE alone.
    That route was circular (the title echoed the name the domain was guessed
    from), and only the few that turn out to publish a registration number are
    marked VERIFIED.

Every one of those registration proofs IS a route-2 confirmation — the company's
own site, naming its own number, agreeing with the CH record. Both jobs recorded
them as domain evidence and threw the confirmation away.

This script does the feeding-back. It reads nothing from the network.

WHAT IT WRITES
--------------
One field per supplier, on the seed record:

    "companyNumberProof": {
      "number":    "09033854",
      "route":     "website-registration",
      "url":       "https://www.abscientific.com/terms-of-use/",
      "evidence":  "site states registration number 09033854 (...verbatim...)",
      "checkedOn": "2026-08-14"
    }

`scripts/refresh_companies_house.py` reads that field as route 2 and, when
Companies House corroborates the registered name and the company is active,
records `matchConfidence: "confirmed"` with a `matchedOn` naming the URL. The
confidence rule itself stays in that script, in one place. Nothing here decides
a confidence.

Domains go in the seed, not the index — the nightly rebuild copies seed records
wholesale and destroys index-only edits (see the 14/08/2026 commit).

WHAT IT REFUSES TO DO (root rule 14 — refuse on thin evidence)
--------------------------------------------------------------
  * A proof of kind "name" — the site title merely resembling the company — is
    NOT a confirmation and is never written. Only "registration" proofs are, and
    from the name-proof file only those whose verdict is VERIFIED. A REFUSED
    record is evidence that the domain is wrong, not evidence of a number.
  * If the two evidence files publish different numbers for the same supplier,
    both are dropped. That is the same disagreement rule applied everywhere else
    here — a tie between two sourced numbers is checked by hand, not broken in
    code.
  * If the report's number disagrees with the number currently held in
    company-financials.json, the supplier is SKIPPED and logged. That
    disagreement means the report was built against different data, and the
    evidence string quotes a number we can no longer tie to the record.
  * If the seed already anchors a DIFFERENT company number in alerts[]/note, the
    supplier is SKIPPED and logged as ambiguous. Two sourced numbers disagreeing
    is a fact to check by hand, not a tie to break in code — the same rule
    refresh_companies_house.py applies to two anchored numbers.
  * A supplier with no record in company-financials.json is skipped: there is
    nothing to agree with.

Re-running changes nothing. An unchanged run writes no file.

USAGE
-----
    python3 scripts/confirm_company_numbers.py            # write the seed
    python3 scripts/confirm_company_numbers.py --dry-run  # report only
"""

import json
import re
import sys

SEED = "data/supplier-seed.json"
FIN = "data/company-financials.json"

# Both evidence files, because the same proof arrives by two paths.
#
#   domain-seeding-report.json      scripts/seed_supplier_domains.py — a candidate
#                                   domain generated from the company name, accepted
#                                   only where the site published the CH number.
#   name-proof-verification.json    scripts/verify_name_proofs.py — the second-sourcing
#                                   of the 128 domains that had been accepted on a site
#                                   TITLE alone, which was circular (the title echoed the
#                                   name we guessed the domain from). Only the handful
#                                   that turned out to publish a registration number are
#                                   VERIFIED, and only those are a route-2 proof.
#
# A REFUSED or name-only record is not evidence and is never read. Either file may be
# absent — they are written by separate jobs — and a missing one is skipped, not fatal.
SOURCES = (
    ("state/domain-seeding-report.json", None),
    ("state/name-proof-verification.json", "VERIFIED"),
)

ROUTE = "website-registration"

# Identical to refresh_companies_house.py, deliberately: this script has to see
# an anchored number exactly as that script would, or the ambiguity guard below
# would pass something that then loses to a seed number downstream.
CH_NUMBER = re.compile(
    r"(?i)compan(?:y|ies)\s+house"
    r"[^A-Za-z0-9]{0,4}"
    r"(?:number|no\.?|reg(?:istration)?\.?)?"
    r"[^A-Za-z0-9]{0,4}"
    r"((?:[A-Z]{2})?\d{6,8})")
VALID_NUMBER = re.compile(r"^(?:[A-Z]{2}\d{6}|\d{8})$")


def log(message):
    print(message, flush=True)


def free_text(supplier):
    parts = []
    for alert in supplier.get("alerts", []) or []:
        parts.append(alert if isinstance(alert, str) else json.dumps(alert))
    parts.append(supplier.get("note") or "")
    return " ".join(parts)


def anchored_numbers(supplier):
    return {n.upper() for n in CH_NUMBER.findall(free_text(supplier))
            if VALID_NUMBER.match(n.upper())}


def gather_proofs():
    """Every registration proof from every evidence file, keyed by supplier.

    A supplier proved in both files is only a problem if the two disagree — and
    then it is the same problem as any other pair of disagreeing sourced numbers,
    so it is dropped rather than arbitrated.
    """
    proofs, conflicts = {}, set()
    for path, require_verdict in SOURCES:
        try:
            results = json.load(open(path, encoding="utf-8"))["results"]
        except FileNotFoundError:
            log("%s not present — skipped" % path)
            continue
        except (ValueError, KeyError) as exc:
            log("%s could not be read (%s) — skipped rather than half-read" % (path, exc))
            continue

        usable = [r for r in results
                  if r.get("proof") == "registration"
                  and (require_verdict is None or r.get("verdict") == require_verdict)]
        log("%d registration proof(s) in %s" % (len(usable), path))

        for r in usable:
            name = r.get("name")
            if not name:
                continue
            r = dict(r, _from=path)
            seen = proofs.get(name)
            if seen and str(seen.get("companyNumber") or "").upper() != \
                    str(r.get("companyNumber") or "").upper():
                conflicts.add(name)
            proofs.setdefault(name, r)

    for name in sorted(conflicts):
        log("  SKIP %s: the two evidence files publish different company numbers — "
            "not arbitrated" % name)
        proofs.pop(name, None)
    return proofs


def main():
    dry_run = "--dry-run" in sys.argv

    seed = json.load(open(SEED, encoding="utf-8"))
    financials = json.load(open(FIN, encoding="utf-8"))["companies"]

    by_name = {}
    for record in seed["suppliers"]:
        by_name.setdefault(record["name"], record)

    proofs = list(gather_proofs().values())
    log("%d supplier(s) with a registration proof in total" % len(proofs))

    written = skipped = unchanged = 0
    for proof in proofs:
        name = proof["name"]
        number = str(proof.get("companyNumber") or "").upper()
        record = by_name.get(name)

        if record is None:
            log("  SKIP %s: proved a domain but has no seed record" % name)
            skipped += 1
            continue
        if not VALID_NUMBER.match(number):
            log("  SKIP %s: proof carries no usable company number (%r)" % (name, number))
            skipped += 1
            continue

        held = financials.get(name)
        if not held:
            log("  SKIP %s: no Companies House record to agree with" % name)
            skipped += 1
            continue
        if str(held.get("companyNumber") or "").upper() != number:
            log("  SKIP %s: proof says %s, company-financials.json holds %s — "
                "the evidence cannot be tied to the record" % (name, number, held.get("companyNumber")))
            skipped += 1
            continue

        anchored = anchored_numbers(record)
        if anchored and number not in anchored:
            log("  SKIP %s: seed already anchors %s, the site publishes %s — ambiguous, "
                "check by hand" % (name, ", ".join(sorted(anchored)), number))
            skipped += 1
            continue

        entry = {
            "number": number,
            "route": ROUTE,
            "url": proof.get("url"),
            "evidence": proof.get("evidence"),
            "checkedOn": proof.get("checked"),
        }
        if record.get("companyNumberProof") == entry:
            unchanged += 1
            continue

        if not dry_run:
            record["companyNumberProof"] = entry
        written += 1
        log("  %s %s  %s" % ("would write" if dry_run else "wrote", name, number))

    log("")
    log("%d written, %d already current, %d skipped"
        % (written, unchanged, skipped))

    if dry_run:
        log("--dry-run: %s not written" % SEED)
        return 0
    if not written:
        log("nothing changed; %s left alone" % SEED)
        return 0

    with open(SEED, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, separators=(",", ":"))
    log("wrote %s" % SEED)
    log("")
    log("These become `confirmed` on the next run of scripts/refresh_companies_house.py,")
    log("which needs COMPANIES_HOUSE_KEY and so runs in the company-intelligence workflow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
