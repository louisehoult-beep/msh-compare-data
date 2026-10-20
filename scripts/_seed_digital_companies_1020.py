#!/usr/bin/env python3
"""One-off, 20/10/2026: health tech and digital company intel brought up to the
device-supplier standard (health tech company-intel audit).

WHAT IT DOES
------------
1. SEEDS 17 clinically relevant digital companies the Hub had no record for: the
   ones NHS buyers name on software award notices in data/digital-lane.json, and
   the health tech prospects in Lou's CRM. The 343 general IT firms on Technology
   Services 4 are deliberately NOT seeded.
2. CONFIRMS company numbers for 6 existing digital records that were "probable"
   (name search only), from the company's own site.
3. CORRECTS two identity decisions:
     * DrDoctor: the 03/09/2026 override excluded 08149394 ICNH LTD with "no
       relationship to DrDoctor established". DrDoctor's own privacy notice now
       establishes it: "DrDoctor (registered: ICNH Ltd) which is registered in
       England and Wales under company number 08149394". The exclusion is
       removed and the number recorded as a route 2 proof.
     * Aidoc Medical Ltd: name search had attached 17429893 TEE DEE AIDOC LTD, a
       company incorporated on 01/09/2026 at a Newcastle residential address,
       after the 2025 framework this supplier holds. Excluded.
4. RECORDS "no UK entity found" for three foreign suppliers whose own site names
   a non-UK legal entity and for which Companies House holds no registration.

EVERY NUMBER HAS A SOURCE, BY ONE OF TWO ROUTES ONLY
---------------------------------------------------
  Route 2 (`companyNumberProof`): the number published on the company's OWN
  site, quoted verbatim, read 20/10/2026, and agreeing with the Companies House
  register (name, active status) read the same day.
  Route 1 (anchored "Companies House NNNNNNNN" in the note): where the site
  names the legal entity but prints no number, the entity name on the company's
  own page AND the Companies House register entry for that exact name, two
  independent sources, both cited in the note. The registered name is also
  recorded as an alias so the name test in refresh_companies_house.py can see it.
No number here came from a name search alone. Companies where neither route
was available are seeded with NO number and stay "probable" or empty after the
Companies House refresh, which is the honest state.

Domains go in the seed (links[]), never the index alone. The same records are
mirrored into supplier-index.json so the index is right before the nightly
rebuild copies the seed. Idempotent: a record already present is left alone.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import company_match  # noqa: E402
from seed_format import write_like, describe  # noqa: E402

SEED = "data/supplier-seed.json"
INDEX = "data/supplier-index.json"
FIN = "data/company-financials.json"
OVERRIDES = "data/company-match-overrides.json"
DAY = "2026-10-20"
DIG_IT = "Digital and medical IT"
DIG_AI = "Digital health / AI"


def proof(number, url, evidence):
    return {"number": number, "route": "website-registration", "url": url,
            "evidence": evidence, "checkedOn": DAY}


def new(name, aliases, spec, site, why, *, proof_=None, route1=None):
    """A new seed record. `route1` = (number, registered name, entity URL, quote)."""
    note = ("Added %s (health tech company-intel audit). %s Products and frameworks not "
            "yet captured." % ("20/10/2026", why))
    if route1:
        num, reg, url, quote = route1
        note += (" Companies House %s %s, active, read 20/10/2026; the company's own page %s "
                 "names that entity: \"%s\". Two independent sources, so recorded by hand "
                 "(route 1); the site prints no registration number." % (num, reg, url, quote))
    rec = {
        "name": name,
        "aliases": aliases,
        "specialities": [spec],
        "products": [],
        "frameworks": [],
        "alerts": [],
        "news": [],
        "links": [{"label": "Company website", "url": site,
                   "source": "Company's own site, read %s." % DAY}],
        "awards": [],
        "curated": True,
        "note": note,
        "verified": DAY,
        "source": "Companies House register and the company's own site, read %s" % DAY,
    }
    if proof_:
        rec["companyNumberProof"] = proof_
    return rec


NEW = [
    new("EMIS (Enlivio Health)",
        ["EMIS (Enlivio Health)", "EMIS", "EMIS Health", "Enlivio Health",
         "Egton Medical Information Systems Limited"],
        DIG_IT, "https://www.enliviohealth.com/",
        "Named on NHS England award notice 'CPIT System Integration to NHSE RAVS' as "
        "EGTON MEDICAL INFORMATION SYSTEMS LIMITED. emishealth.com now redirects to "
        "enliviohealth.com, whose banner reads 'EMIS is now Enlivio Health'.",
        proof_=proof("02117205", "https://www.enliviohealth.com/privacy-policy",
                     "EMIS Group Limited includes: Egton Medical Information Systems Limited "
                     "(™ Enlivio Health). Egton Medical Information Systems Limited is a "
                     "company registered in England and Wales. Registered number: 02117205. "
                     "Registered office: Fulford Grange, Micklefield Lane, Rawdon, Leeds LS19 6BA")),
    new("Civica", ["Civica", "Civica UK Limited"], DIG_IT, "https://www.civica.com/en-gb/",
        "Named on four NHS software award notices (eOpas, Cito EDMS, OPAS-G2, CCM catering) "
        "as CIVICA UK LIMITED, and on Technology Services 4.",
        proof_=proof("01628868", "https://www.civica.com/en-gb/policies-and-statements/terms--conditions/",
                     "This is the Web Site of Civica UK Limited, a company registered in England "
                     "under company number 1628868, registered address is 8th Floor, Southbank "
                     "Central, 30 Stamford Street, London")),
    new("Netcall", ["Netcall", "Netcall Technology Limited"], DIG_IT, "https://www.netcall.com/",
        "Named on NHS award notices 'Contact Centre Platform' and 'Liberty Converse CX' as "
        "Netcall Technology Limited.",
        proof_=proof("02831215", "https://www.netcall.com/legal/",
                     "Netcall Technology Limited is a private limited company registered in "
                     "England with company number 02831215, whose registered office is at "
                     "Suite 203, Bedford Heights, Brickhill Drive, Bedford")),
    new("Patchwork Health",
        ["Patchwork Health", "LocumTap Limited trading as Patchwork Health", "LocumTap Limited",
         "Locum Tap"],
        DIG_IT, "https://patchwork.health/",
        "Named on NHS award notices as 'LocumTap Limited trading as Patchwork Health' and "
        "'Locum Tap'. LocumTap is the only Companies House registration of that name "
        "(search 20/10/2026).",
        proof_=proof("10359095", "https://patchwork.health/terms",
                     "LocumTap Limited, trading as Patchwork Health (\"Patchwork\") is a limited "
                     "company registered in England and Wales whose registered number is "
                     "10359095 and whose registered address is at 35 Luke St London EC2A 4LH")),
    new("Imosphere", ["Imosphere", "Imosphere Ltd"], DIG_IT, "https://www.imosphere.co.uk/",
        "Named on NHS award notice 'Carepartner Mental Health Clinical System' as Imosphere Ltd.",
        proof_=proof("02878495", "https://www.imosphere.co.uk/",
                     "Imosphere Ltd is a limited company registered in England and Wales. "
                     "Company registration no. 02878495. Registered office: 3 Princes Court, "
                     "Royal Way, Loughborough, Leicestershire")),
    new("Medilogik", ["Medilogik", "Medilogik Limited"], DIG_IT, "https://www.medilogik.co.uk/",
        "Named on NHS award notice 'WHHT - Endoscopy Management System (EMS)' as Medilogik Limited.",
        proof_=proof("06707492", "https://www.medilogik.co.uk/",
                     "© 2026 MEDILOGIK Ltd. All Rights Reserved. Policies, terms and "
                     "conditions . VAT number: GB941119640. Company number: 06707492.")),
    new("iPlato", ["iPlato", "iPlato Healthcare Ltd", "iPLATO"], DIG_IT, "https://www.iplato.com/",
        "Named on NHS Kent and Medway Integrated Care Board award notices as iPlato Healthcare Ltd.",
        proof_=proof("06131747", "https://www.iplato.com/privacy-policy/index.html",
                     "We are iPlato Healthcare Ltd (“we”, “us”, “our”, "
                     "” iPlato”), a company registered in England & Wales with company "
                     "number 6131747 and with registered offices at 13th floor, Millbank Tower, "
                     "21-24 Millbank, London SW1P 4QP")),
    new("CardMedic", ["CardMedic", "Card Medic Limited"], DIG_AI, "https://www.cardmedic.com/",
        "Named on NHS award notice 'Patient Communication and Translation Aid (CardMedic)' as "
        "CARD MEDIC LIMITED; a CRM health tech prospect.",
        proof_=proof("12544617", "https://www.cardmedic.com/",
                     "© 2026 Card Medic Limited. Registered in England and Wales, company "
                     "number 12544617.")),
    new("Cyted", ["Cyted", "Cyted Ltd"], DIG_AI, "https://www.cyted.ai/",
        "A CRM health tech prospect (listed there as Cyted Health). The site names Cyted Ltd as "
        "the parent; Cyted Health Ltd is a separate subsidiary registration and is NOT an alias "
        "of this record.",
        proof_=proof("11478299", "https://www.cyted.ai/",
                     "Cyted Health Inc. & Cyted Health Ltd are wholly owned subsidiaries of Cyted "
                     "Ltd. Cyted Ltd is registered in England & Wales, Company Number: 11478299.")),
    new("Limbic", ["Limbic", "Limbic Limited"], DIG_AI, "https://www.limbic.ai/",
        "A CRM health tech prospect (mental health AI).",
        proof_=proof("11093861", "https://www.limbic.ai/limbic-website-privacy-notice.html",
                     "Limbic is a company registered in England and Wales (company number: "
                     "11093861) with its registered office at Kemp House 160 City Road, London")),
    new("Medwise AI", ["Medwise AI", "Medwise AI Ltd", "Medwise.ai"], DIG_AI, "https://www.medwise.ai/",
        "A CRM health tech prospect (clinical knowledge search).",
        proof_=proof("12146414", "https://www.medwise.ai/terms.html",
                     "We are Medwise AI Ltd (trading as Medwise.ai), a company registered in "
                     "England and Wales with number 12146414 and its registered office address "
                     "at Nexus House, Discovery Way, Leeds")),
    new("Rapid Health", ["Rapid Health", "Rapid Health Ltd"], DIG_AI, "https://www.rapidhealth.co.uk/",
        "A CRM health tech prospect (primary care triage).",
        proof_=proof("12061137", "https://www.rapidhealth.co.uk/privacy-policy",
                     "Our legal name is RAPID HEALTH LTD with company number 12061137 and our "
                     "address is 86-90 Paul Street, London, England, EC2A 4NE.")),
    new("Ortus-iHealth", ["Ortus-iHealth", "Ortus Solutions Limited"], DIG_AI, "https://ortus-ihealth.com/",
        "A CRM health tech prospect (remote monitoring). Trading name of Ortus Solutions.",
        proof_=proof("10820096", "https://ortus-ihealth.com/",
                     "Ortus Solutions, registered as a company in England & Wales, registration "
                     "number 10820096")),
    new("Streets Heaver", ["Streets Heaver", "Streets Heaver Computer Systems Limited"], DIG_IT,
        "https://www.streets-heaver.com/",
        "A CRM health tech prospect (Compucare patient administration).",
        proof_=proof("01999298", "https://www.streets-heaver.com/",
                     "Copyright © 2026 Streets Heaver. The Point, Weaver Road, Lincoln, LN6 "
                     "3QN Registration No. 1999298 | VAT No. 613919143 Registered in England and Wales")),
    new("Dedalus", ["Dedalus", "Dedalus DH OPCO UK Ltd", "DH OpCo UK Ltd"], DIG_IT,
        "https://www.dedalus.com/uk/en/",
        "Named on NHS award notices (Telepath) as 'Dedalus DH OPCO UK Ltd' and 'Dedalus'. "
        "DEDALUS LIMITED (01732196, 1983) is a different registration and is NOT this company.",
        route1=("12888223", "DH OPCO UK LTD", "https://www.dedalus.com/global/en/privacy/",
                "DH OpCo UK Ltd ... UKI (the controller for the UK and Ireland region)")),
    new("Altera Digital Health", ["Altera Digital Health", "Altera Healthcare (IT) UK Ltd"], DIG_IT,
        "https://www.alterahealth.com/",
        "Named on NHS award notice 'Support services for the EPR - Sunrise 22.1' as ALTERA "
        "HEALTHCARE (IT) UK LTD.",
        route1=("07584643", "ALTERA HEALTHCARE (IT) UK LTD",
                "https://www.alterahealth.com/legal/privacy-policy/",
                "Altera Healthcare (IT) UK Ltd. https://uk.www.alterahealth.com/")),
    new("Oxford Heartbeat", ["Oxford Heartbeat", "Oxford Heartbeat Ltd"], DIG_AI,
        "https://www.oxfordheartbeat.com/",
        "A CRM health tech prospect (PreSize Neurovascular).",
        route1=("09685053", "OXFORD HEARTBEAT LTD", "https://www.oxfordheartbeat.com/privacy-policy",
                "Data protection is of a particularly high priority for the management of "
                "Oxford Heartbeat Ltd")),
    # No number on the site and no entity named there: seeded so the award attaches,
    # with no number. The Companies House refresh may find a probable name match.
    new("Allocate Software", ["Allocate Software", "Allocate Software Limited"], DIG_IT,
        "https://www.rldatix.com/en-uki/",
        "Named on NHS award notices (ER Tracker, Direct Instant Pay) as Allocate Software "
        "Limited. The Allocate products are sold under RLDatix (rldatix.com); RLDatix's UK "
        "pages name no legal entity or number, so no company number is recorded."),
]

# Existing records: own-site proofs (route 2), extra aliases, domains.
EXISTING = {
    "Accurx": dict(
        proof_=proof("10184077", "https://www.accurx.com/terms-and-conditions",
                     "“Accurx” means Accurx Limited a company registered in England with "
                     "company number 10184077 whose registered office is at 7 Curtain Road, "
                     "London, England EC2A 3LT."),
        aliases=["Accurx Limited"], site="https://www.accurx.com/"),
    "DrDoctor": dict(
        proof_=proof("08149394", "https://www.drdoctor.co.uk/privacy-notice",
                     "References to “us”/”we”/”our” in this Privacy "
                     "Notice means DrDoctor (registered: ICNH Ltd) which is registered in "
                     "England and Wales under company number 08149394."),
        aliases=["ICNH Ltd"], site="https://www.drdoctor.co.uk/"),
    "Brainomix": dict(
        proof_=proof("07426406", "https://www.brainomix.com/privacy-eu",
                     "Brainomix Limited is a company registered in England and Wales at OX2 0JJ. "
                     "Company Registration No. 07426406"),
        aliases=["Brainomix Limited"], site="https://www.brainomix.com/"),
    "Feedback Medical Limited": dict(
        proof_=proof("04025026", "https://feedbackmedical.com",
                     "Registered No: 04025026 | VAT No: GB760001191"),
        aliases=[], site=None),
    "Schiller UK Limited": dict(
        proof_=proof("09953850", "https://www.schiller-medical.com/en-gb/terms-and-conditions",
                     "Supplier: SCHILLER UK Ltd, a company registered in England and Wales with "
                     "company number 09953850 and having their registered office at 200 Brook "
                     "Drive Green Park, Reading"),
        aliases=[], site=None),
    "Nervecentre": dict(
        proof_=None, aliases=["Nervecentre Software Ltd"], site="https://www.nervecentresoftware.com/",
        note=(" Companies House 07166008 NERVECENTRE SOFTWARE LTD, active, registered office "
              "Denmark Court, 18 Market Place, Wokingham, read 20/10/2026; the company's own "
              "privacy policy (https://nervecentresoftware.com/nervecentre-privacy-policy) gives "
              "\"Privacy Officer, Nervecentre Software Ltd, Denmark Court, 18 Market Place, "
              "Wokingham RG40 1AL\" - same name, same address. Recorded by hand on those two "
              "sources (route 1), 20/10/2026.")),
}

# Foreign suppliers: own site names a non-UK entity; Companies House holds none.
NO_UK = {
    "inHeart S.A.S": ("inHEART is a French simplified joint stock company registered to the "
                      "Bordeaux Trade and Companies Register under number 830 755 393 "
                      "(https://www.inheartmedical.com/privacy-policy, read 20/10/2026). "
                      "Companies House search for 'inheart' (20/10/2026) returns no such company."),
    "SIM&CURE": ("Sim&Cure gives its address as 95 rue Pierre Flourens, 34090 Montpellier, France "
                 "(https://sim-and-cure.com/mentions-legales/, read 20/10/2026). Companies House "
                 "search for 'sim&cure' and 'sim and cure' (20/10/2026) returns no such company."),
    "Luscii": ("Luscii's own site is published by Luscii healthtech B.V., a Dutch company "
               "(https://luscii.com/, read 20/10/2026). Companies House search for 'luscii' "
               "(20/10/2026) returns no company."),
}

AIDOC_EXCLUDE = {
    "exclude": ["17429893"],
    "excludedName": "TEE DEE AIDOC LTD",
    "reason": ("TEE DEE AIDOC LTD was incorporated on 2026-09-01 at a residential address in "
               "Newcastle upon Tyne, after the 2025 Digital Diagnostic Solutions framework this "
               "supplier holds, so it cannot be the awarded company. Name search attached it "
               "because 'aidoc' is in its name."),
    "evidence": "https://find-and-update.company-information.service.gov.uk/company/17429893",
    "decidedOn": DAY,
    "clearedNote": ("No UK company is attached. Aidoc's own privacy policy names the company as "
                    "Aidoc Medical Ltd. (https://www.aidoc.com/privacy-policy/, read 20/10/2026), "
                    "and Companies House holds no registration of that name (search 20/10/2026). "
                    "The only name-search hit, TEE DEE AIDOC LTD (17429893), was incorporated on "
                    "01/09/2026 and is a different company."),
}


def load(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def edit_records(path, seed_index):
    doc = load(path)
    sups = doc["suppliers"]
    by = {s.get("name"): s for s in sups}
    changed = 0
    for rec in NEW:
        if rec["name"] in by:
            continue
        if seed_index is not None:
            for a in rec["aliases"]:
                hits = ((seed_index.get(company_match.key(a)) or set())
                        | (seed_index.exact.get(company_match.norm(a)) or set()))
                if hits - {rec["name"]}:
                    raise SystemExit("alias %r of %r already reaches %s"
                                     % (a, rec["name"], sorted(hits)))
        sups.append(json.loads(json.dumps(rec)))
        changed += 1
    for name, e in EXISTING.items():
        s = by.get(name)
        if s is None:
            raise SystemExit("%s: no record %r" % (path, name))
        before = json.dumps(s, sort_keys=True)
        if e.get("proof_"):
            s["companyNumberProof"] = e["proof_"]
            cand = s.get("companyNumberCandidate")
            if isinstance(cand, dict) and cand.get("number") == e["proof_"]["number"]:
                # Same number the 14/08/2026 name search found, now proved off the
                # company's own site: the candidate must stop calling it unverified.
                cand["confidence"] = "confirmed"
                cand["matchedOn"] = (
                    "Found by Companies House name search on 2026-08-14. CONFIRMED %s: "
                    "company number published on the company's own website, agreeing with "
                    "the Companies House record -- %s, read %s." % (DAY, e["proof_"]["url"], DAY))
                cand["confirmedOn"] = DAY
                cand["confirmedRoute"] = "website-registration"
            elif isinstance(cand, dict):
                raise SystemExit("%s: candidate %s disagrees with proof %s"
                                 % (name, cand.get("number"), e["proof_"]["number"]))
        al = s.setdefault("aliases", [])
        for a in e["aliases"]:
            if a not in al:
                if seed_index is not None:
                    hits = ((seed_index.get(company_match.key(a)) or set())
                            | (seed_index.exact.get(company_match.norm(a)) or set()))
                    if hits - {name}:
                        raise SystemExit("alias %r of %r already reaches %s" % (a, name, sorted(hits)))
                al.append(a)
        if e.get("site") and not any(l.get("url") == e["site"] for l in s.get("links") or []):
            s.setdefault("links", []).append({"label": "Company website", "url": e["site"],
                                              "source": "Company's own site, read %s." % DAY})
        if e.get("note") and e["note"].strip() not in (s.get("note") or ""):
            s["note"] = ((s.get("note") or "").rstrip() + e["note"]).strip()
        if json.dumps(s, sort_keys=True) != before:
            changed += 1
    for name, evidence in NO_UK.items():
        s = by.get(name)
        if s is None:
            raise SystemExit("%s: no record %r" % (path, name))
        want = {"state": "none", "evidence": evidence, "checkedOn": DAY}
        if s.get("ukEntity") != want:
            s["ukEntity"] = want
            changed += 1
    if changed:
        fmt, rt = write_like(path, doc)
        print(describe(path, fmt, rt))
    print("%s: %d record(s) added or changed" % (path, changed))


def edit_overrides():
    doc = load(OVERRIDES)
    ov = doc["overrides"]
    changed = False
    if "DrDoctor" in ov:
        del ov["DrDoctor"]
        changed = True
    if ov.get("Aidoc Medical Ltd") != AIDOC_EXCLUDE:
        ov["Aidoc Medical Ltd"] = AIDOC_EXCLUDE
        changed = True
    if changed:
        fmt, rt = write_like(OVERRIDES, doc)
        print(describe(OVERRIDES, fmt, rt))


def main():
    seed = load(SEED)
    edit_records(SEED, company_match.build_index(seed))
    edit_records(INDEX, None)
    edit_overrides()


if __name__ == "__main__":
    main()
