#!/usr/bin/env python3
"""Prove the careers collector's evidence floor still holds.

These are the three ways this thing could publish a confident wrong number on a
paid page. Each one has a test here because a rule that lives only in a docstring
is a rule that quietly stops being true.

  python3 test_careers_evidence.py
"""
import importlib.util
import os
import sys

spec = importlib.util.spec_from_file_location("rc", "scripts/refresh_supplier_careers.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, wanted %r" % (label, got, want))
        print("FAIL  %s — got %r, wanted %r" % (label, got, want))
    else:
        print("ok    %s" % label)


# 1. A PARENT GROUP'S APPLICANT TRACKING ACCOUNT IS NOT THIS COMPANY'S.
#    Acumed Ltd's own careers page links to Workday tenant `marmon` — its parent
#    conglomerate — which returns 40 roles, most of them US machine operators.
#    Without the guard the Hub states "Acumed: 40 open roles" and every one is
#    wrong. This is the case that made the guard exist (28/08/2026).
check("parent group tenant is refused",
      rc.tenant_matches("marmon", "Acumed Ltd", "www.acumed.net"), False)
check("the company's own tenant is accepted",
      rc.tenant_matches("acumed", "Acumed Ltd", "www.acumed.net"), True)
check("a recruitment agency tenant is refused",
      rc.tenant_matches("randstad", "Alpha Laboratories", "www.alphalabs.co.uk"), False)
check("identity may come from the domain alone",
      rc.tenant_matches("accora", "Accora", "accora.care"), True)

# 2. GENERIC TRADE WORDS ARE NOT IDENTITY. Almost every name in this seed
#    contains "Medical", "Healthcare", "UK" or "Group". If those counted, a
#    tenant called "healthcare" would match half the supplier list.
check("'medical' alone does not identify a company",
      rc.tenant_matches("medical", "Advanced Medical Systems Ltd", "advmedical.com"), False)
check("'healthcare' alone does not identify a company",
      rc.tenant_matches("healthcare", "AM Healthcare Group", "amhealthcaregroup.com"), False)
check("'group' alone does not identify a company",
      rc.tenant_matches("group", "GBUK Group", "www.gbuk.com"), False)

# 3. A LOCATION IS UK ONLY IF THE COMPANY SAID SO. There is no inference from
#    the company being UK-registered: a UK supplier's board can be entirely
#    Dutch roles. Unknown must stay unknown, not default to either answer.
check("a UK city is UK", rc.uk_flag("Leeds, England"), True)
check("field based is UK", rc.uk_flag("Home based, UK"), True)
check("a US city is not UK", rc.uk_flag("Boyne City, MI"), False)
check("an EU city is not UK", rc.uk_flag("Amsterdam, Netherlands"), False)
check("no location published stays unknown", rc.uk_flag(""), None)
check("an unrecognised location stays unknown", rc.uk_flag("2 Locations"), None)

# 4. A LAYOUT IS NEVER COUNTED. A careers page with no applicant tracking system
#    and no JobPosting data must yield NO roles — not a count scraped off list
#    markup. "No vacancies right now" above a six-item footer is six roles to a
#    regex, and the Hub would publish it as fact.
prose = ("<html><body><h1>Careers</h1><p>We have no vacancies right now.</p>"
         "<ul><li><a href='/a'>About</a></li><li><a href='/b'>Contact</a></li>"
         "<li><a href='/c'>News</a></li></ul></body></html>")
check("prose careers page yields no roles",
      rc.jsonld_roles(prose, "https://example.com/careers"), [])

# 5. STRUCTURED DATA IS COUNTED, because it is a record the company published.
jsonld = ('<html><script type="application/ld+json">'
          '{"@type":"JobPosting","title":"Territory Sales Manager",'
          '"jobLocation":{"address":{"addressLocality":"Manchester",'
          '"addressCountry":"GB"}},"url":"https://example.com/j/1"}'
          '</script></html>')
roles = rc.jsonld_roles(jsonld, "https://example.com/careers")
check("JobPosting data yields one role", len(roles), 1)
check("its title is read", roles[0]["title"], "Territory Sales Manager")
check("its UK location is read", roles[0]["uk"], True)
check("a sales title flags commercial", roles[0]["commercial"], True)
check("a sales title does not flag clinical", roles[0]["clinical"], False)

nurse = rc.role("Clinical Nurse Specialist", "Bristol", None)
check("a clinical title flags clinical", nurse["clinical"], True)

# 6. AN API VERSION SEGMENT IS NOT AN ACCOUNT NAME. boards-api.greenhouse.io/v1/
#    appears in the embed script; capturing from it yielded the token "v1" and a
#    dead API call reported as a refusal (Aidoc, 28/08/2026).
check("'v1' is rejected as a tenant token", "v1" in rc.BAD_TOKENS, True)
check("'api' is rejected as a tenant token", "api" in rc.BAD_TOKENS, True)

# 7. A PAGINATED SOURCE MUST NOT BE COUNTED BY WHERE THE LOOP STOPPED.
#    Workday reports the real total on page 1 and 0 on every page after it.
#    Re-reading it each page made the loop halt at 40, so Stryker — 1,184 open
#    roles — was counted as 40. Wrong by a factor of thirty, and it survived a
#    whole finished run, because 40 looks like a plausible number for a company.
#    Live, so it fails if Workday changes shape under us.
if os.environ.get("CAREERS_LIVE_TESTS"):
    wroles, stated = rc._workday("https://stryker.wd1.myworkdayjobs.com/StrykerCareers")
    check("a paginated source reports its OWN total, not where the loop stopped",
          stated > 500, True)
    check("the fetch stops at the cap", len(wroles) <= rc.WORKDAY_CAP, True)
    check("an incomplete fetch is visibly incomplete", len(wroles) < stated, True)
else:
    print("skip  live Workday pagination test (set CAREERS_LIVE_TESTS=1 to run)")

print()
if FAILURES:
    print("%d FAILURE(S)" % len(FAILURES))
    sys.exit(1)
print("All evidence-floor checks pass.")
