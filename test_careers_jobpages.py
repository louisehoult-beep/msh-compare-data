#!/usr/bin/env python3
"""Prove the job-page record routes (Teamtailor, SuccessFactors CSB) in
scripts/refresh_supplier_careers.py keep the evidence bar.

Offline: every fetch is served from the fixtures below. What is asserted:

  * a role is counted ONLY from a JobPosting record on its own job page —
    a listing link with no record behind it yields nothing;
  * a listing that hands off to a parent group's site is refused, not counted;
  * a board read part-way (site budget) is refused as partial, not published;
  * a listing that names no job pages at all is not claimed as the platform,
    so nothing is ever published as "0 roles".

  python3 test_careers_jobpages.py
"""
import importlib.util
import json
import sys
import time

spec = importlib.util.spec_from_file_location("careers", "scripts/refresh_supplier_careers.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
M.PAUSE = 0

RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append((label, ok))
    print(("ok    " if ok else "FAIL  ") + label + ("" if ok else "   <- " + str(detail)))


def jobposting(title, locality, country, url):
    return ('<html><head><script type="application/ld+json">%s</script></head><body>x</body></html>'
            % json.dumps({"@context": "https://schema.org", "@type": "JobPosting", "title": title,
                          "datePosted": "2026-09-20", "url": url,
                          "jobLocation": {"@type": "Place", "address": {
                              "@type": "PostalAddress", "addressLocality": locality,
                              "addressCountry": country}}}))


def serve(pages):
    def get(url, as_json=False, timeout=25):
        if url not in pages:
            raise M.urllib.error.URLError("no such fixture: " + url)
        body = pages[url]
        return (json.loads(body) if as_json else body), url
    return get


IDENT = ("Acme Medical Ltd", "www.acmemedical.co.uk")
FAR = time.time() + 600

# ---------------------------------------------------------------- Teamtailor
TT = {
    "https://www.acmemedical.co.uk/careers": '<a href="https://acmemedical.teamtailor.com/jobs">Jobs</a>',
    "https://acmemedical.teamtailor.com/jobs": (
        '<li><a href="/jobs/101-territory-manager-north">Territory Manager North</a></li>'
        '<li><a href="https://acmemedical.teamtailor.com/jobs/102-clinical-specialist">Clinical</a></li>'
        '<li><a href="/jobs/103-warehouse">Warehouse</a></li>'
        '<a href="/jobs?page=2">Next</a>'),
    "https://acmemedical.teamtailor.com/jobs?page=2": "<p>no more</p>",
    "https://acmemedical.teamtailor.com/jobs/101-territory-manager-north":
        jobposting("Territory Manager North", "Leeds", "GB", "https://acmemedical.teamtailor.com/jobs/101-territory-manager-north"),
    "https://acmemedical.teamtailor.com/jobs/102-clinical-specialist":
        jobposting("Clinical Specialist", "Berlin", "Germany", "https://acmemedical.teamtailor.com/jobs/102-clinical-specialist"),
    "https://acmemedical.teamtailor.com/jobs/103-warehouse": "<html><body>no structured data</body></html>",
}
M.get = serve(TT)
res, method, ats, note, src = M.read_roles("https://www.acmemedical.co.uk/careers", FAR, IDENT)
check("teamtailor: roles come only from job pages with a JobPosting record",
      res is not None and len(res["roles"]) == 2 and res["totalAllLocations"] == 3, (res, note))
check("teamtailor: method is jsonld and the platform is named",
      method == "jsonld" and ats == "teamtailor" and res and res["atsAccount"] == "acmemedical", (method, ats))
check("teamtailor: UK flag read from the record's country",
      res and [r["uk"] for r in res["roles"]] == [True, False], res and res["roles"])

# The third link had no record, so the board is 3 and the records are 2: run_one
# must refuse the partial board rather than state a UK count.
M.allowed = lambda *a, **k: True
M.find_careers_url = lambda d, dl: ("https://www.acmemedical.co.uk/careers", "nav")
row = M.run_one(IDENT[0], IDENT[1], None)
check("teamtailor: a link with no record behind it makes the board partial, so no count is stated",
      "refused" in row and "2 of its 3" in row["refused"] and "ukRoleCount" not in row, row)

# All three carry a record: a count is stated, and it is the UK subset.
TT2 = dict(TT)
TT2["https://acmemedical.teamtailor.com/jobs/103-warehouse"] = jobposting(
    "Warehouse Operative", "Leeds", "GB", "https://acmemedical.teamtailor.com/jobs/103-warehouse")
M.get = serve(TT2)
row = M.run_one(IDENT[0], IDENT[1], None)
check("teamtailor: complete board gives a UK count from the records",
      row.get("ukRoleCount") == 2 and row.get("complete") is True and row.get("countMethod") == "jsonld"
      and row.get("commercialRoles") == 1, row)

# Parent group site: refused, named, not counted.
PARENT = {"https://www.acmemedical.co.uk/careers": '<a href="https://bigparentgroup.teamtailor.com/jobs">Jobs</a>'}
M.get = serve(PARENT)
res, method, ats, note, src = M.read_roles("https://www.acmemedical.co.uk/careers", FAR, IDENT)
check("teamtailor: a parent group's site is refused, not counted",
      res is None and ats == "teamtailor" and "bigparentgroup" in (note or "") and "parent or group" in (note or ""), note)

# No record on any page: refused in those words, never "0 roles".
NOREC = dict(TT)
for k in list(NOREC):
    if "/jobs/10" in k:
        NOREC[k] = "<html><body>rendered in the browser</body></html>"
M.get = serve(NOREC)
res, method, ats, note, src = M.read_roles("https://www.acmemedical.co.uk/careers", FAR, IDENT)
check("teamtailor: job pages without records are refused, not published as 0",
      res is None and "none carries a JobPosting" in (note or ""), (res, note))

# Site budget already spent: refused before any job page is read.
M.get = serve(TT2)
res, method, ats, note, src = M.read_roles("https://www.acmemedical.co.uk/careers", time.time() - 1, IDENT)
check("teamtailor: an exhausted site budget refuses rather than reads part of the board",
      res is None and "budget" in (note or ""), (res, note))

# ------------------------------------------------------------ SuccessFactors
SF = {
    "https://www.acmemedical.co.uk/careers":
        '<p>See our roles</p><a href="https://careers.acmemedical.com/search/">Search jobs</a>',
    "https://careers.acmemedical.com/search/": (
        '<a class="jobTitle-link" href="/job/Leeds-Territory-Manager/9000001/">Territory Manager</a>'
        '<a class="jobTitle-link" href="https://careers.acmemedical.com/job/Munich-Engineer/9000002/">Engineer</a>'
        '<a href="/search/?q=&startrow=25">Next</a>'),
    "https://careers.acmemedical.com/search/?q=&startrow=25": (
        '<a class="jobTitle-link" href="/job/Bristol-Clinical-Specialist/9000003/">Clinical Specialist</a>'),
    "https://careers.acmemedical.com/job/Leeds-Territory-Manager/9000001/":
        jobposting("Territory Manager", "Leeds", "GB", "https://careers.acmemedical.com/job/Leeds-Territory-Manager/9000001/"),
    "https://careers.acmemedical.com/job/Munich-Engineer/9000002/":
        jobposting("Engineer", "Munich", "Germany", "https://careers.acmemedical.com/job/Munich-Engineer/9000002/"),
    "https://careers.acmemedical.com/job/Bristol-Clinical-Specialist/9000003/":
        jobposting("Clinical Specialist", "Bristol", "GB", "https://careers.acmemedical.com/job/Bristol-Clinical-Specialist/9000003/"),
}
M.get = serve(SF)
row = M.run_one(IDENT[0], IDENT[1], None)
check("successfactors: paged search read fully, count from the records",
      row.get("ukRoleCount") == 2 and row.get("complete") is True and row.get("ats") == "successfactors"
      and row.get("totalRolesAllLocations") == 3 and row.get("clinicalRoles") == 1, row)

# A company site with an ordinary site search and no job links is NOT this platform.
PLAIN = {"https://www.acmemedical.co.uk/careers":
             '<a href="https://www.acmemedical.co.uk/search/">Site search</a><p>Email us your CV.</p>',
         "https://www.acmemedical.co.uk/search/": "<form>search</form>"}
M.get = serve(PLAIN)
res, method, ats, note, src = M.read_roles("https://www.acmemedical.co.uk/careers", FAR, IDENT)
check("a plain site search is not claimed as a listing, and nothing is published as 0 roles",
      res is None and ats is None and "no role records" in (note or ""), (res, ats, note))

bad = [l for l, ok in RESULTS if not ok]
print("\n%d checks, %d failed" % (len(RESULTS), len(bad)))
sys.exit(1 if bad else 0)
