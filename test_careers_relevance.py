#!/usr/bin/env python3
"""Relevant roles on the Career Centre — the filter, and that the page agrees with it.

Lou, 28/09/2026: "there is no max, they just need to be in the right categories or
job titles". config/careers-relevant-roles.json holds the one list. This proves:

  1. real titles from data/supplier-careers.json that a medical sales professional
     would want are IN, with the category they should carry;
  2. real titles from the same file that are not sales or commercial roles
     (manufacturing, finance, HR, IT, lab, service engineering) are OUT, including
     ones that mention a commercial word ("Talent Acquisition Specialist - Commercial");
  3. there is no cap: every matching role in a large synthetic file is returned;
  4. app/careers-roles.js, which the page runs, classifies every example the same
     way as scripts/careers_relevance.py (skipped only where node is not installed);
  5. a malformed config fails loudly rather than showing nothing.

Offline. python3 test_careers_relevance.py
"""
import importlib.util
import json
import shutil
import subprocess
import sys

spec = importlib.util.spec_from_file_location("cr", "scripts/careers_relevance.py")
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(label)
        print("FAIL  %s — got %r, wanted %r" % (label, got, want))
    else:
        print("ok    %s" % label)


# Real titles, as published in data/supplier-careers.json on 28/09/2026, plus the
# commonest UK medical sales titles for the categories that file does not yet hold.
IN = {
    "(Senior) Territory Manager Electrophysiology - South Coast": "territory-account",
    "Associate Territory Manager (ADC) Field based North": "territory-account",
    "Territory Manager, Structural Heart; Field Based Midlands": "territory-account",
    "Key Account Manager Rapid Diagnostics (Scotland)": "key-account",
    "Key Account Manager; Cardiometabolics; Field Based North Region": "key-account",
    "Business Development Manager Rapid Diagnostics - North West": "business-development",
    "Commercial Manager Cardiac Rhythm Management (Central & North UK)": "sales-management",
    "Clinical Specialist Cardiac Rhythm Management - South England": "clinical-product-specialist",
    "Trainee/Associate Clinical Specialists Cardiovascular - Graduate opportunities within "
    "Abbott Medical Devices (UK Locations)": "clinical-product-specialist",
    "Technical Application Specialist (Ideal role for a Biomedical Scientist)":
        "clinical-product-specialist",
    "Sales Operations Admin - Pricing & Contracts Lead": "tenders-bids",
    # Categories the file holds no example of yet.
    "Sales Representative - Wound Care": "sales-rep",
    "Medical Sales Executive, Orthopaedics": "sales-rep",
    "Area Sales Manager - Surgical": "territory-account",
    "Regional Sales Manager UK North": "sales-management",
    "Head of Sales UK & Ireland": "sales-management",
    "Sales Specialist, Endoscopy": "sales-specialist",
    "Product Specialist - Theatres": "clinical-product-specialist",
    "Clinical Application Specialist - Ultrasound": "clinical-product-specialist",
    "Market Access Manager": "market-access",
    "Tender Manager (NHS)": "tenders-bids",
    "Bid Writer": "tenders-bids",
    "Customer Success Manager - Digital Health": "customer-success-clinical-support",
    "Clinical Support Specialist - Critical Care": "customer-success-clinical-support",
    "Clinical Nurse Advisor - Continence": "customer-success-clinical-support",
    # Widened 14/10/2026 (Lou: product managers, trainers, nurse advisors too).
    # Real titles from the file on 14/10/2026 first, then common UK titles.
    "Clinical Development Specialist Electrophysiology London/South East UK":
        "clinical-product-specialist",
    "Sales Spine Specialist - East Anglia": "sales-specialist",
    "Country Manager Heart Failure UK & Ireland": "sales-management",
    "Regional Business Manager North UK & Ireland": "sales-management",
    "Specialist Technical Trainer": "training-education",
    "Marketing Manager (Reimbursed)": "product-marketing",
    "Trade Marketing Manager": "product-marketing",
    "Nurse Advisor - Stoma Care": "customer-success-clinical-support",
    "Homecare Nurse - Field Based": "customer-success-clinical-support",
    "Field Clinical Engineer - Cardiac": "clinical-product-specialist",
    "Medical Science Liaison - Oncology": "medical-affairs",
    "Clinical Educator - Wound Care": "training-education",
    "Sales Trainer": "training-education",
    "Product Manager - Surgical": "product-marketing",
    "Brand Manager, Respiratory": "product-marketing",
}

# Widened 22/10/2026 (Lou: more job-title names, plus early-career roles).
IN.update({
    "Professional Education and Development Manager, 12 month contract": "training-education",
    "Digital Health Solutions Executive (Diagnostics)": "sales-specialist",
    "Business Developer - Medical Devices": "business-development",
    "National Account Manager - NHS": "key-account",
    "Medical Director UK & Ireland": "medical-affairs",
    "Health Economics Manager": "market-access",
    "Sales Operations Manager": "commercial-operations",
    "Graduate Sales Programme": "entry-level",
    "Marketing Assistant": "entry-level",
    "Hospital Specialist - Immunology": "sales-rep",
    "Primary Care Sales Representative - North West": "sales-rep",
    "Customer Engagement Manager - Oncology": "sales-rep",
    "Regional Access Manager": "market-access",
})

# Early-career tag: title only.
ENTRY_YES = ["Graduate Sales Programme", "Associate Territory Manager (ADC) Field based North",
             "Junior Product Manager", "Sales Development Representative",
             "Business Development Representative - NHS", "Inside Sales Executive",
             "Trainee Clinical Specialist", "Sales Associate", "Marketing Assistant"]
ENTRY_NO = ["Senior Product Manager", "Key Account Manager", "Graduate Chemist",
            "Graduate Software Engineer", "Associate Director, Sales", "Territory Manager"]

OUT = [
    "Business Developer - Coffee Solutions",
    "Van Driver",
    # Real titles from the file, 28/09/2026.
    "Talent Acquisition Specialist - Commercial - temporary position based in Maidenhead",
    "Tax Accountant",
    "HR Business Partner",
    "Senior Software Developer",
    "Multi-Skilled Maintenance Engineer",
    "Planning Project Lead - Manufacturing",
    "Supply Chain Executive (Diagnostics) - Glasgow",
    "Laboratory Project and Change Manager",
    "VP, Research & Development",
    "Senior Regulatory Affairs Specialist",
    "Senior Buyer",
    "Customer Service Advisor",
    "Field Service Engineer",
    "Scientist",
    "Dispensing Operator I",
    "Audit Program Manager",
    "Admin Assistant",
    "Lean Specialist",
    "Chief Medical Officer",
    "Business Support Manager",
    # Typical unrelated titles with a commercial-sounding word in them.
    "Sales Finance Manager",
    "Warehouse Operative - Sales Orders",
    "IT Support Analyst - Sales Systems",
    "R&D Engineer, New Business Products",
]


def main():
    c = cr.load_config()
    for t, want in IN.items():
        check("IN  %s" % t[:60], cr.classify(t, c), want)
    for t in OUT:
        check("OUT %s" % t[:60], cr.classify(t, c), None)
    for t in ENTRY_YES:
        check("ENTRY yes %s" % t[:50], cr.is_entry(t, c), True)
    for t in ENTRY_NO:
        check("ENTRY no  %s" % t[:50], cr.is_entry(t, c), False)

    # No cap: 500 matching roles across 40 suppliers all come back.
    doc = {"suppliers": [
        {"name": "Supplier %02d" % s, "checkedOn": "2026-09-28",
         "roles": [{"title": "Territory Manager %d" % i, "uk": True, "location": "Leeds",
                    "url": "https://example.test/%d/%d" % (s, i)} for i in range(13)]
         + [{"title": "Tax Accountant", "uk": True, "location": "Leeds",
             "url": "https://example.test/%d/tax" % s},
            {"title": "Territory Manager", "uk": False, "location": "Boston",
             "url": "https://example.test/%d/us" % s}]}
        for s in range(40)]}
    roles, sups = cr.relevant_roles(doc, c)
    check("no cap: 520 matching roles returned", len(roles), 520)
    check("no minimum: 40 suppliers returned", len(sups), 40)
    one = {"suppliers": [{"name": "Solo Ltd", "roles": [
        {"title": "Key Account Manager", "uk": True, "url": "https://x.test/1"}]}]}
    check("no minimum supplier base: one supplier, one role shown",
          len(cr.relevant_roles(one, c)[0]), 1)

    # The live file classifies without error, and nothing outside the UK gets through.
    live = json.load(open("data/supplier-careers.json", encoding="utf-8"))
    roles, _ = cr.relevant_roles(live, c)
    check("live file: every listed role is uk=true", all(r["uk"] is True for r in roles), True)

    # A malformed config fails loudly.
    for label, bad in (("no categories", {"categories": []}),
                       ("missing patterns", {"categories": [{"key": "a", "label": "A"}]}),
                       ("python-only syntax", {"categories": [
                           {"key": "a", "label": "A", "patterns": ["(?P<x>sales)"]}]})):
        try:
            cr.compile_config(bad)
            check("bad config refused: " + label, "accepted", "ValueError")
        except ValueError:
            check("bad config refused: " + label, "ValueError", "ValueError")

    # The page's own JavaScript agrees, title for title.
    node = shutil.which("node")
    if not node:
        print("skip  JS parity — node not installed")
    else:
        titles = list(IN) + OUT + [r["title"] for s in live["suppliers"] for r in s.get("roles") or []]
        js = ("const api=require('./app/careers-roles.js');"
              "const cfg=require('./config/careers-relevant-roles.json');"
              "const c=api.compile(cfg);"
              "const t=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "process.stdout.write(JSON.stringify(t.map(x=>api.classify(x,c))));")
        out = subprocess.run([node, "-e", js], input=json.dumps(titles), capture_output=True,
                             text=True, check=True).stdout
        got = json.loads(out)
        ejs = ("const api=require('./app/careers-roles.js');"
               "const c=api.compile(require('./config/careers-relevant-roles.json'));"
               "const t=JSON.parse(require('fs').readFileSync(0,'utf8'));"
               "process.stdout.write(JSON.stringify(t.map(x=>api.isEntry(x,c))));")
        et = ENTRY_YES + ENTRY_NO + titles
        eout = json.loads(subprocess.run([node, "-e", ejs], input=json.dumps(et), capture_output=True,
                                         text=True, check=True).stdout)
        check("JS parity on early-career tag", eout, [cr.is_entry(t, c) for t in et])
        want = [cr.classify(t, c) for t in titles]
        diff = [(t, g, w) for t, g, w in zip(titles, got, want) if g != w]
        check("JS parity over %d titles" % len(titles), diff, [])

    if FAILURES:
        print("\n%d FAILED" % len(FAILURES))
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
