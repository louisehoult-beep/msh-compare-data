#!/usr/bin/env python3
"""Has the Hub attached the RIGHT company to this record?

`company_alias.py` answers "which company is this name". This answers the next
question, the one that actually reached members: "is the company we attached to
this record the right company at all".

Written 14/08/2026, after settling the alias review queue turned up faults that
no alias fixes. Every check below is one of those failures turned into an
invariant, per root rule 14 - a derived claim needs a test that fails if the
logic breaks.

  1 SHARED-NUMBER    two or more SEED SUPPLIER records carry the same company
                     number, so one company is two suppliers on the compare tab
  2 CONTRADICTED     the matched registered name resolves to a company already
                     settled as DIFFERENT from this record
  3 IMPLAUSIBLE      matched to a company that trades in something else entirely
  4 NAME-DISAGREES   the record's own matchedOn admits the registered name does
                     not correspond to the supplier
  5 IMPOSSIBLE-DATE  matched to a company incorporated AFTER a framework the Hub
                     says this supplier holds
  6 DEAD-COMPANY     matched to a company that was already DISSOLVED before a
                     framework the Hub says this supplier holds

WHY 6 IS NOT SIMPLY "IS IT DISSOLVED": a supplier really can be dissolved, and
saying so is correct and is real intelligence for a member — Emmat Medical
(03621176, dissolved 07/07/2026) and BK Medical UK are live examples. Failing
every dissolved match would cry wolf on the true ones and get the check ignored.
What is never possible is a company winning a framework it was already dead for.
That is the same shape as check 5 with the dates the other way round, and it is
what caught the three records that published a struck-off shell to members on
03/09/2026: HC21 (UK) Ltd shown as a takeaway dissolved in 2018, Gemini Surgical
shown as a company dissolved in 2017, Semperit shown as a shell struck off in
2025. Genuinely dissolved suppliers are printed separately, as a signal.

This is the Companies House version of the ODS trap in
[[ods-status-not-liveness]]: a status field that reads fine is not proof the
organisation behind it is still there. Here the reverse also holds — "dissolved"
is not proof the record is wrong.

Usage:
  python3 match_check.py            report and gate
  python3 match_check.py --json     machine-readable
  python3 match_check.py --quiet    exit code only

Exit 0 = clean. Exit 1 = at least one finding. Read-only; never writes.

WHY IT DOES NOT SIMPLY FAIL ON `probable`: 380 of 598 records carry
matchConfidence "probable", whose own matchedOn reads "name search on Companies
House - NOT verified against a recorded number". Failing all 380 would make a
gate nobody runs. The route-2 confirmation work in msh-compare-data
(confirm_company_numbers.py) is what reduces that number. This script fails on
evidence that a SPECIFIC match is wrong, which is the actionable subset - and
every finding below was a "probable" match, which is the argument for that work.
"""

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
# Moved into msh-compare-data itself 03/09/2026 (was a sibling Hub/company-aliases/);
# HERE is now <repo>/company-aliases, so data is just "../data".
FINANCIALS = os.path.join(DATA, "company-financials.json")
SEED = os.path.join(DATA, "supplier-seed.json")
NHSSC = os.path.join(DATA, "nhssc-cache.json")

sys.path.insert(0, HERE)
from company_alias import load_registry, resolve, norm, norm_stripped   # noqa: E402

# Two-digit SIC divisions plausible for a company that supplies the NHS.
# Deliberately broad: the point is to catch a match that is a different KIND of
# business, not to second-guess a supplier's own classification. Compression
# hosiery is knitted apparel (14), infant formula is dairy (10) and Gore makes
# technical textiles (13) - all legitimate, all previously false positives.
PLAUSIBLE_SIC = {
    "10", "11", "13", "14", "15", "16", "17", "18", "20", "21", "22", "23",
    "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "35", "36",
    "37", "38", "39", "43", "46", "47", "49", "52", "53", "58", "59", "61",
    "62", "63", "69", "70", "71", "72", "73", "74", "77", "78", "80", "81",
    "82", "84", "85", "86", "87", "88", "90", "93", "94", "96",
}
# Left out, and therefore failing: 64/65/66 financial services, 68 real estate,
# 41/42 construction, 45 motor trade, 55/56 hospitality, 01-09 agriculture and
# mining. A Hub supplier matched to one of those is the wrong company.

# Not a trade, just an absent or placeholder classification. Treated as unknown
# rather than implausible - a gap is not a contradiction.
UNKNOWN_SIC = {"99999", "74990", "98000", "82990"}


def load(path, what):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception as exc:
        print("FAIL: cannot read %s (%s): %s" % (what, path, exc), file=sys.stderr)
        sys.exit(1)


def add(findings, check, record, detail, rec=None):
    findings.append({
        "check": check, "record": record, "detail": detail,
        "confidence": (rec or {}).get("matchConfidence"),
        "companyNumber": (rec or {}).get("companyNumber"),
        "url": (rec or {}).get("sourceUrl"),
    })


def check_shared_number(companies, seed_names, findings):
    """One company number, two supplier records - a duplicate on the compare tab."""
    by_number = {}
    for name, rec in companies.items():
        num = rec.get("companyNumber")
        if num:
            by_number.setdefault(num, []).append(name)
    for num, names in sorted(by_number.items()):
        in_seed = sorted(n for n in names if n in seed_names)
        if len(in_seed) > 1:
            add(findings, "1 SHARED-NUMBER", " + ".join(in_seed),
                "%d supplier records share company number %s. One company is "
                "showing as %d suppliers." % (len(in_seed), num, len(in_seed)),
                companies[in_seed[0]])


def check_contradicted(companies, reg, findings):
    """The registered name points at a company settled as a different one."""
    distinct = reg.get("declaredDistinct", {})
    for name, rec in sorted(companies.items()):
        reg_name = rec.get("registeredName")
        if not reg_name:
            continue
        status, co, _ = resolve(reg_name, reg)
        if status != "RESOLVED":
            continue
        if norm(co) in set(distinct.get(norm(name), [])):
            add(findings, "2 CONTRADICTED", name,
                "matched to %s (%s), which resolves to '%s' - already settled "
                "as a DIFFERENT company from this record"
                % (reg_name, rec.get("companyNumber"), co), rec)


def check_implausible(companies, findings):
    """Matched to a company that trades in something else entirely."""
    for name, rec in sorted(companies.items()):
        sic = [str(s) for s in (rec.get("sic") or [])]
        sic = [s for s in sic if s not in UNKNOWN_SIC]
        if not sic:
            continue
        # The record's name and the registered name are the same. The match is
        # self-consistent, so an odd trade is a curiosity, not the wrong
        # company: Shawbrook Bank Limited really is a bank. The finding is for
        # records matched to a company with a DIFFERENT name AND a different
        # trade - a holding company, or a namesake in another industry.
        if norm_stripped(name) == norm_stripped(rec.get("registeredName") or ""):
            continue
        if any(s[:2] in PLAUSIBLE_SIC for s in sic):
            continue
        add(findings, "3 IMPLAUSIBLE", name,
            "matched to %s (%s), SIC %s - not a trade that supplies the NHS"
            % (rec.get("registeredName"), rec.get("companyNumber"), ", ".join(sic)),
            rec)


def check_name_disagrees(companies, findings):
    """The record itself says the registered name does not correspond."""
    for name, rec in sorted(companies.items()):
        matched_on = (rec.get("matchedOn") or "").lower()
        if "does not cor" in matched_on:
            add(findings, "4 NAME-DISAGREES", name,
                "matched to %s (%s), and the record's own matchedOn says the "
                "registered name does not correspond"
                % (rec.get("registeredName"), rec.get("companyNumber")), rec)


def _years(text):
    return [int(y) for y in re.findall(r"\b(19|20)\d{2}\b", str(text)) or []] or [
        int(m) for m in re.findall(r"\b((?:19|20)\d{2})\b", str(text))]


def check_impossible_date(companies, seed, findings):
    """A company cannot have won a framework before it existed."""
    for supplier in seed:
        name = supplier.get("name")
        rec = companies.get(name)
        if not rec or not rec.get("incorporated"):
            continue
        try:
            inc = datetime.date.fromisoformat(rec["incorporated"])
        except Exception:
            continue
        earliest = None
        for fw in supplier.get("frameworks", []) or []:
            yrs = [int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", str(fw.get("dates") or ""))]
            if yrs:
                earliest = min(yrs) if earliest is None else min(earliest, min(yrs))
        if earliest and inc.year > earliest:
            add(findings, "5 IMPOSSIBLE-DATE", name,
                "matched to %s (%s), incorporated %s - but the Hub says this "
                "supplier holds a framework starting %d, before that company "
                "existed" % (rec.get("registeredName"), rec.get("companyNumber"),
                             rec["incorporated"], earliest), rec)


DEAD_STATUSES = {"dissolved", "closed", "converted-closed", "removed",
                 "liquidation", "administration", "receivership", "insolvency-proceedings"}
# "open" is the normal live state for a BR/FC overseas UK establishment, and
# "registered" for an OE overseas entity. Neither means dead.


def _earliest_framework_year(supplier):
    years = []
    for fw in supplier.get("frameworks", []) or []:
        years += [int(y) for y in
                  re.findall(r"\b((?:19|20)\d{2})\b", str(fw.get("dates") or ""))]
    return min(years) if years else None


def check_dead_company(companies, seed, findings, genuinely_dead):
    """A company cannot hold a framework awarded after it ceased to exist.

    Splits the dissolved matches in two, which is the whole point:
      - ceased BEFORE the earliest framework  -> a finding, the match is wrong
      - ceased after, or no framework to test -> not a finding, but recorded so
        a human sees it, because a supplier going under IS the intelligence
    """
    for supplier in seed:
        name = supplier.get("name")
        rec = companies.get(name)
        if not rec or not rec.get("companyNumber"):
            continue
        status = (rec.get("status") or "").lower()
        if status not in DEAD_STATUSES:
            continue
        ceased = rec.get("dissolvedOn")
        earliest = _earliest_framework_year(supplier)
        ceased_year = None
        if ceased:
            try:
                ceased_year = int(str(ceased)[:4])
            except ValueError:
                ceased_year = None
        if earliest and ceased_year and ceased_year < earliest:
            add(findings, "6 DEAD-COMPANY", name,
                "matched to %s (%s), %s on %s - but the Hub says this supplier "
                "holds a framework starting %d, after that company ceased to "
                "exist. It cannot be the holder."
                % (rec.get("registeredName"), rec.get("companyNumber"),
                   status, ceased, earliest), rec)
        else:
            genuinely_dead.append(
                "%s -> %s (%s) is %s%s. Not a fault: report it to members."
                % (name, rec.get("registeredName"), rec.get("companyNumber"),
                   status, " on " + str(ceased) if ceased else ""))


def main(argv):
    as_json = "--json" in argv
    quiet = "--quiet" in argv

    companies = (load(FINANCIALS, "company-financials.json").get("companies") or {})
    seed = load(SEED, "supplier-seed.json").get("suppliers") or []
    seed_names = {s.get("name") for s in seed}
    reg = load_registry()

    findings, genuinely_dead = [], []
    check_shared_number(companies, seed_names, findings)
    check_contradicted(companies, reg, findings)
    check_implausible(companies, findings)
    check_name_disagrees(companies, findings)
    check_impossible_date(companies, seed, findings)
    check_dead_company(companies, seed, findings, genuinely_dead)

    if as_json:
        print(json.dumps(findings, indent=1))
    elif not quiet:
        if not findings:
            print("PASS  no contradicted company matches.")
        else:
            print("FAIL  %d finding(s). These are member-facing.\n" % len(findings))
            for f in sorted(findings, key=lambda x: x["check"]):
                print("  [%s] %s" % (f["check"], f["record"]))
                print("      %s" % f["detail"])
                if f.get("confidence"):
                    print("      matchConfidence: %s" % f["confidence"])
                if f.get("url"):
                    print("      %s" % f["url"])
                print()
        if genuinely_dead:
            print("%d supplier(s) match a company that really is dissolved or "
                  "insolvent. These are NOT faults - a supplier going under is "
                  "intelligence a member wants:" % len(genuinely_dead))
            for line in sorted(genuinely_dead):
                print("  %s" % line)
            print()
        probable = sum(1 for r in companies.values()
                       if r.get("matchConfidence") == "probable")
        print("Checked %d company records (%d still 'probable') against %d seed suppliers."
              % (len(companies), probable, len(seed)))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
