#!/usr/bin/env python3
"""
test_seed_domains.py — proves a REFUSED title proof cannot reach the seed.

THE HOLE THIS CLOSES. scripts/seed_supplier_domains.py banks every result so a
40-minute sweep can resume. That bank is also how a bad proof travels: a domain
"proved" by a page title was banked once on 14/08/2026 and then replayed by
every later --write run, so the --accept-name flag stopped meaning anything the
moment the report existed. verify_name_proofs.py adjudicated all 128 title
proofs the same day — 4 stood up to registration proof, 124 could not be
second-sourced at all — and those 124 verdicts are now the authority the seeding
script checks before it writes.

Why it matters that this stays true: crawl_supplier_site.py reads whatever
domain the seed holds and publishes that site's catalogue as the supplier's own
product range, on a paid page. "1 Stop Medical Supplies" was banked against
www.1stop.com, an IT and networking reseller.

    python3 test_seed_domains.py

Exit 0 = the gate holds. Exit 1 = a refused proof can be written again.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import seed_supplier_domains as seeder  # noqa: E402

REPORT = "state/domain-seeding-report.json"
VERDICTS = "state/name-proof-verification.json"

failures = []


def check(name, ok, detail=""):
    print("  %s %s%s" % ("PASS" if ok else "FAIL", name,
                         "" if ok else "  <- " + detail))
    if not ok:
        failures.append(name)


def gate(proven, refused):
    """The filter as main() applies it. Kept in one place so the test cannot
    drift into testing a copy of the rule instead of the rule."""
    blocked = [r for r in proven
               if r["name"] in refused and r["proof"] != "registration"]
    return [r for r in proven if r not in blocked], blocked


print("verdict file")
verdicts = json.load(open(VERDICTS, encoding="utf-8"))["results"]
refused_names = seeder.refused_name_proofs()
check("124 suppliers stand REFUSED", len(refused_names) == 124,
      "found %d" % len(refused_names))
check("4 suppliers stand VERIFIED",
      sum(1 for v in verdicts if v.get("verdict") == "VERIFIED") == 4)
check("every one of the 128 has a verdict", len(verdicts) == 128,
      "found %d" % len(verdicts))

print("banked report")
report = json.load(open(REPORT, encoding="utf-8"))["results"]
titles = [r for r in report if r.get("proof") == "name"]
check("no title proof is left replayable", not titles,
      "%d still carry proof=name: %s" % (len(titles), [r["name"] for r in titles[:5]]))
refused_rows = [r for r in report if r.get("secondSourced") == "REFUSED"]
check("124 report rows carry the REFUSED verdict", len(refused_rows) == 124,
      "found %d" % len(refused_rows))
check("a refused row keeps no top-level domain",
      all("domain" not in r for r in refused_rows),
      "a domain at the top level is what the write loop reads")
check("a refused row keeps its evidence for the record",
      all(r.get("refusedNameProof", {}).get("domain") for r in refused_rows))

print("the gate")
# A --fresh re-probe lands on the same guessed domain and "proves" it by title
# again. That is the exact replay this must stop.
replay = [{"name": "1 Stop Medical Supplies", "proof": "name",
           "domain": "www.1stop.com", "evidence": "site title names the company"}]
kept, blocked = gate(replay, refused_names)
check("a re-probed title proof for a refused supplier is blocked",
      not kept and len(blocked) == 1)

# Refused on the title route, but proved properly later. The registration route
# is the way back in, and it must stay open or the refusal is a dead end.
reproved = [{"name": "1 Stop Medical Supplies", "proof": "registration",
             "domain": "www.example.co.uk", "evidence": "site states registration number"}]
kept, blocked = gate(reproved, refused_names)
check("a registration proof re-opens a refused supplier", len(kept) == 1 and not blocked)

# A supplier nobody has ruled on is unaffected by the gate.
untouched = [{"name": "Some Supplier Never Adjudicated", "proof": "name",
              "domain": "www.somewhere.co.uk", "evidence": "site title names the company"}]
kept, blocked = gate(untouched, refused_names)
check("the gate touches only adjudicated names", len(kept) == 1 and not blocked)

print("self-declared-foreign tier (added 28/08/2026)")
# A foreign supplier's own site, stating its own country's registration number.
# No UK company number exists for it (ch_number=None), so REGISTRATION can never
# fire — this is exactly the population ch-number-is-ideal-not-mandatory-for-
# supplier-data describes.
foreign_html = ("<title>Absorbest AB</title><body>Absorbest AB is registered "
                "in Sweden. Org.nr 556677-8899. Contact us.</body>")
kind, ev, url = seeder.prove("Absorbest AB", None, [("https://absorbest.com", foreign_html)],
                              accept_name=False, allow_foreign=True)
check("a foreign registration number is proven as self-declared-foreign",
      kind == "self-declared-foreign", "got %r" % (kind,))
check("the evidence records it as self-declared, not cross-checked",
      "self-declared" in (ev or "") and "not cross-checked" in (ev or ""))

# The same page, but allow_foreign is OFF (the flag's default). No proof at all —
# the route must not fire silently just because the page qualifies.
kind2, _, _ = seeder.prove("Absorbest AB", None, [("https://absorbest.com", foreign_html)],
                            accept_name=False, allow_foreign=False)
check("self-declared-foreign never fires without --allow-foreign", kind2 is None)

# THE LEAK THIS MUST NOT ALLOW: a supplier that DOES have a UK Companies House
# number must never be proved on the weaker self-declared route, even if its
# site happens to carry foreign-shaped registration wording (e.g. a UK company
# quoting an EU VAT number) and allow_foreign is on. ch_number truthy must gate
# self-declared-foreign off entirely, whatever the page says.
uk_with_foreign_wording = ("<title>Acme Medical Ltd</title><body>Acme Medical Ltd. "
                            "VAT number DE123456789. Registered in England, company "
                            "number 01234567.</body>")
kind3, ev3, _ = seeder.prove("Acme Medical Ltd", "01234567",
                              [("https://acmemedical.co.uk", uk_with_foreign_wording)],
                              accept_name=False, allow_foreign=True)
check("a UK-numbered supplier proves on registration, never self-declared-foreign",
      kind3 == "registration", "got %r" % (kind3,))

# A UK supplier whose site does NOT carry its own number is refused, not routed
# to the weaker tier as a fallback — allow_foreign only ever applies when there
# is no UK number to check against in the first place, not when the check fails.
uk_no_number = "<title>Acme Medical Ltd</title><body>Acme Medical Ltd. Contact us.</body>"
kind4, _, _ = seeder.prove("Acme Medical Ltd", "01234567",
                            [("https://acmemedical.co.uk", uk_no_number)],
                            accept_name=False, allow_foreign=True)
check("a UK-numbered supplier that never states its number is refused, not "
      "downgraded to self-declared-foreign", kind4 is None)

# THE OTHER LEAK: a UK company with NO matched CH record at all (a data gap in
# company-financials.json, not evidence of being foreign) states plain UK-style
# registration wording. FOREIGN_REG_WORDS deliberately overlaps with that
# wording, so without UK_MARKERS this would be wrongly recorded as "overseas
# company" — an invented fact, not an honestly weaker one.
uk_no_ch_match = ("<title>BVM Medical Ltd</title><body>BVM Medical Ltd is "
                   "Registered in England and Wales. Company number 07654321. "
                   "Registered office: 1 Trade Park, Leeds.</body>")
kind5, _, _ = seeder.prove("BVM Medical Ltd", None,
                            [("https://bvmmedical.co.uk", uk_no_ch_match)],
                            accept_name=False, allow_foreign=True)
check("a UK company with no matched CH record is never labelled overseas",
      kind5 is None, "got %r" % (kind5,))

# THE THIRD LEAK: self-declared-foreign has nothing to cross-check its number
# against (unlike "registration"), so a wrongly-guessed domain landing on some
# OTHER real company's site would otherwise "prove" on that unrelated site's own
# number. Found 28/08/2026 on a live run: "AMG Medtech Ltd" and "APR Medtech
# Limited" both guessed to aml.co.uk and both banked the same evidence, because
# nothing checked that either name actually appeared on that page.
unrelated_site = ("<title>Acme Laminates Ltd</title><body>Acme Laminates Ltd. "
                   "Registered in Ireland. CRO number 123456. Contact us.</body>")
kind6, _, _ = seeder.prove("AMG Medtech Ltd", None,
                            [("https://aml.co.uk", unrelated_site)],
                            accept_name=False, allow_foreign=True)
check("a real foreign proof on a site that never names the supplier is refused",
      kind6 is None, "got %r" % (kind6,))

# The positive case, same shape, but the site DOES name the supplier this time.
named_foreign_site = ("<title>AMG Medtech Ltd</title><body>AMG Medtech Ltd. "
                       "Registered in Ireland. CRO number 123456. Contact us.</body>")
kind7, ev7, _ = seeder.prove("AMG Medtech Ltd", None,
                              [("https://amgmedtech.ie", named_foreign_site)],
                              accept_name=False, allow_foreign=True)
check("the same evidence proves once the site actually names the supplier",
      kind7 == "self-declared-foreign", "got %r" % (kind7,))

# HTML-entity regression: "&amp;" must decode to "&" so UK_MARKERS can still
# catch "England &amp; Wales" as rendered by a real browser/site.
entity_encoded_uk = ("<title>Associated Optical Products</title><body>"
                      "Associated Optical Products. Registered No.84121 "
                      "England &amp; Wales.</body>")
kind8, _, _ = seeder.prove("Associated Optical Products", None,
                            [("https://www.associated.co.uk", entity_encoded_uk)],
                            accept_name=False, allow_foreign=True)
check("an HTML-entity-encoded UK marker (&amp;) still blocks the foreign route",
      kind8 is None, "got %r" % (kind8,))

# THE FOURTH LEAK: a UK footer that gives an address and a number but never
# says "England"/"Companies House" by name — found 28/08/2026 on "Bidfood
# Direct", a real UK company with no matched CH record, wrongly proved
# self-declared-foreign because nothing in its footer used the exact UK
# wording UK_MARKERS looked for.
uk_postcode_only = ("<title>Bidfood Direct</title><body>Bidfood Direct. "
                     "Company No. 239718, 814 Leigh Road, Slough, SL1 4AB.</body>")
kind9, _, _ = seeder.prove("Bidfood Direct", None,
                            [("https://www.bidfood.co.uk", uk_postcode_only)],
                            accept_name=False, allow_foreign=True)
check("a UK postcode next to the number blocks the foreign route even with no "
      "explicit jurisdiction wording", kind9 is None, "got %r" % (kind9,))

# THE FIFTH LEAK: the domain's own TLD is UK, independent of what the footer
# says at all — the strongest, simplest signal available and it should refuse
# on its own.
uk_tld_no_markers = ("<title>Msoft eSolutions</title><body>Msoft eSolutions. "
                      "Company Registration Number: 3472193.</body>")
kind10, _, _ = seeder.prove("Msoft eSolutions", None,
                             [("https://msoft.co.uk", uk_tld_no_markers)],
                             accept_name=False, allow_foreign=True)
check("a .co.uk domain is refused for the foreign route regardless of wording",
      kind10 is None, "got %r" % (kind10,))

# A genuinely foreign domain must still pass — the new guards must not have
# widened into refusing everything.
genuinely_foreign = ("<title>Cortrium ApS</title><body>Cortrium ApS is "
                      "registered in Denmark. Company registration number "
                      "36445335, Copenhagen.</body>")
kind11, _, _ = seeder.prove("Cortrium ApS", None,
                             [("https://cortrium.com", genuinely_foreign)],
                             accept_name=False, allow_foreign=True)
check("a genuinely foreign .com domain still proves", kind11 == "self-declared-foreign",
      "got %r" % (kind11,))

print("write-gate: self-declared-foreign is STRONG, not the weak/title tier")
STRONG = ("registration", "self-declared-foreign")
proven = [
    {"name": "Absorbest AB", "proof": "self-declared-foreign", "domain": "absorbest.com"},
    {"name": "1 Stop Medical Supplies", "proof": "name", "domain": "www.1stop.com"},
]
# Mirrors main()'s `if not a.accept_name: proven = [r for r in proven if
# r["proof"] in STRONG]` — kept as a literal copy of the rule, same discipline
# as gate() above, so this cannot drift into testing something else.
kept_strong = [r for r in proven if r["proof"] in STRONG]
check("self-declared-foreign survives the --accept-name gate (accept_name OFF)",
      any(r["proof"] == "self-declared-foreign" for r in kept_strong))
check("a title proof still does NOT survive the same gate",
      not any(r["proof"] == "name" for r in kept_strong))

# refused_name_proofs() blocking must exempt self-declared-foreign the same way
# it already exempts registration — a name that happens to appear in the
# REFUSED title-proof list must not block an unrelated, independently-earned
# self-declared-foreign proof for that same name.
refused_names_test = {"Absorbest AB"}
blocked_test = [r for r in [{"name": "Absorbest AB", "proof": "self-declared-foreign"}]
                if r["name"] in refused_names_test and r["proof"] not in STRONG]
check("self-declared-foreign is not blocked by the refused-title-proof gate",
      not blocked_test)

print()
if failures:
    print("FAILED: %d check(s) — %s" % (len(failures), ", ".join(failures)))
    sys.exit(1)
print("gate holds — no refused title proof can reach data/supplier-seed.json")
print("self-declared-foreign tier holds — cannot leak into the registration tier")
