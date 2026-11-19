#!/usr/bin/env python3
"""Transcatheter Heart Valve lot-source names with no Hub record, 18/11/2026.

WHY THIS RUN EXISTS
-------------------
check_framework_lots()'s first warning counts lot-source supplier names that
resolve to NO Hub supplier record. Three of them sit on one framework,
Transcatheter Heart Valve Repair, Replacement and Associated Devices
(reference 2022/S 000-025267):

  * "Abbott Meditcal UK Limited"       -- already decided, do NOT touch here.
    Commit b983be2 put that NHS Supply Chain misspelling on Abbott Medical
    U.K. Ltd. Abbott's lots stay unattached on purpose: the brief's bare word
    "Abbott" resolves to Abbott Diabetes Care, and a global alias index cannot
    carry a per-framework truth.
  * "Biosensors International UK Limited" -- no Hub record. THIS RUN.
  * "Jenavalve Production Limited"        -- no Hub record. THIS RUN.

Both are clinical, so both are in scope under Lou's ruling that the Hub does
not carry non-clinical framework suppliers (catering, facilities and
electrical, furniture, office supplies, food). Neither is any of those: both
are Companies House SIC 32500, manufacture of medical and dental instruments
and supplies, and both are named by NHS Supply Chain itself on Lot 1,
Transcatheter Aortic Valve Implant (TAVI) System.

WHAT WAS VERIFIED AT SOURCE, TODAY (18/11/2026)
-----------------------------------------------
1. NHS Supply Chain's own contract launch brief for the framework, read
   18/11/2026. It states "There are 11 suppliers in total on this framework"
   and prints exactly 11: Abbott, Acrostak, Biosensors, BVM, Dot Medical,
   Edwards, Jenavalve, MCT, Medtronic, Meril, SMT. The stated count matches
   the printed list, so the capture is complete and BOTH companies ARE on the
   owner's current supplier list -- written there as bare brand words.
   Framework runs 18 September 2023 to 26 February 2027 (41 months including a
   17 month extension).

   This is the opposite of the Hand Hygiene case
   (state/hand-hygiene-lot-source-adjudication.json), where the brief named
   none of the eight unresolved names. Here the brief names them and the
   matrix spells them out, so a lot CAN be attached and nothing has to be
   hedged as "awarded but absent from the current list".

2. The brief's own attached product matrix,
   Product-Matrix-Transcatheter-Heart-Valve-09-September-2026-MT.xlsx, issued
   9 September 2026, downloaded and opened 18/11/2026. Its "Specification"
   grid carries one column per supplier, including column 4
   "Biosensors International UK Limited" and column 8
   "Jenavalve Production Limited", and marks BOTH "Y" on
   "Lot 1: Transcatheter Aortic Valve Implant (TAVI) System" and NOT on Lot 2
   (Transcatheter Non-Aortic Valve/Chord Repair and Replacement System,
   Components and Accessories). Lot 1 only, for both, read in the cells.

   Recorded by ~/.claude/hooks/framework_award_check.py as Lou's 17/11/2026
   framework-claims rule requires:
   ~/.claude/framework-claims/2022-S-000-025267-2026-11-18.json
   (manual record -- no Find a Tender OCDS id is known for this reference, so
   the facts were read from the owner's own brief and matrix, not from FTS.)

3. Companies House, read 18/11/2026 through find-and-update:
   * BIOSENSORS INTERNATIONAL UK LTD, 11783737, Active, private limited,
     incorporated 23/01/2019, registered office 12 New Fetter Lane, London
     EC4A 1JP. SIC 32500 (manufacture of medical and dental instruments and
     supplies) and 46460 (wholesale of pharmaceutical goods). Three officers,
     no resignations; the secretary is BIRD & BIRD COMPANY SECRETARIES LIMITED
     (03952862) at the same address; a director resident in Switzerland. No
     persons with significant control -- an active "no registrable person"
     statement since incorporation. It is the ONLY Companies House company
     whose name begins "Biosensors International UK".
   * JENAVALVE PRODUCTION LIMITED, 09520509, Active, private limited,
     incorporated 31/03/2015, registered office Unit 9a Astley Way, Astley
     Lane Industrial Estate, Swillington, Leeds LS26 8XT. SIC 32500. Eight
     officers, including a director at 4 Cromwell, Irvine, California -- the
     address of JenaValve Technology, Inc. No persons with significant
     control. It is the ONLY Companies House company using "JenaValve".

THE TWO DECISIONS, AND WHY THEY DIFFER
--------------------------------------
Both records go IN. What differs is how much each record is allowed to say,
and that is decided by data/identity-vocabulary-policy.json, not by taste.

JenaValve Production Limited -- domain ATTRIBUTED, products published.
  jenavalve.com is JenaValve Technology, Inc.'s site (its Terms of Use say
  so), i.e. a foreign-arm site, so policy cross-border-sibling-domain-
  attribution applies: it is attributed to the UK entity only if the site
  itself proves it under domain-proof-tier. It does, at the ADDRESS tier:
  * jenavalve.com/contact/ prints "Unit 9A Astley Way, Swillington, Leeds,
    LS26 8XT, United Kingdom" -- the registered office of 09520509 verbatim;
  * jenavalve.com/eu-uk-privacy-policy/ names the entity itself: "These
    include JenaValve Technology GmbH and JenaValve Production Ltd."
  Two independent sources agreeing on the entity's name AND its registered
  office is documentary proof, not an inference from branding. Domain accepted
  at tier 2 and recorded as address-proved, exactly as Artivion UK Ltd
  (03837138 / artivion.com) is already recorded in this seed.
  So the record may carry what jenavalve.com sells.

Biosensors International UK Ltd -- domain NOT attributed, no products.
  biosensors.com is the Biosensors International Group's site. It names
  Biosensors International Group Ltd (Singapore), Biosensors Interventional
  Technologies Pte Ltd (36 Jalan Tukang, Singapore) and Biosensors Europe SA
  (Rue de Lausanne 29, Morges, Switzerland). It names NO UK legal entity, it
  prints no UK company number, and it prints no UK address -- its United
  Kingdom entry is a customer-support helpdesk link, not an establishment.
  So domain-proof-tier is not satisfied at any tier, and the address tier is
  additionally barred here by its own guard: the registered office
  12 New Fetter Lane, London EC4A 1JP is the company secretary's own address
  (Bird & Bird), shared on 18/11/2026 by 344 companies on the Companies House
  advanced search -- "a shared serviced-office address used by many companies
  ... must be treated as no proof at all".
  Therefore, under cross-border-sibling-domain-attribution, biosensors.com is
  recorded as a related brand site, NOT attributed, and is not crawled into
  this record; and under no-parent-catalogue-credit-to-uk-subsidiary the UK
  record publishes NO product from the group's global catalogue. It publishes
  only what NHS Supply Chain itself lists for the UK entity, which is the Lot
  1 category and no named product. `products` is therefore empty on purpose,
  and the record says so, rather than borrowing BioFreedom, BioMatrix or
  ALLEGRA from the parent.

Company numbers. Neither company publishes its own UK number anywhere, so
under identity-vocabulary-policy.json neither number goes in `companyNumber`.
Both go in `companyNumberCandidate`, which is what 484 of the Hub's 1286
records already use, and each candidate records exactly what matched it.
JenaValve's candidate is the stronger of the two -- a unique registered name
PLUS a registered office its own site prints -- and says so; Biosensors' is a
unique Companies House name match and nothing more. A shared name is not
evidence; a shared registration number is, and no registration number is
shared here.

RELATED ENTITIES NOT ALIASED, DELIBERATELY
------------------------------------------
`aliases` DRIVES AWARD ROUTING through backfill_seed_from_frameworks.py and
refresh_awards.py, so only spellings of the awardee itself go in it.
  * "Biosensors SA" appears as a supplier name on other Hub award rows. It is
    the Swiss group entity (Biosensors Europe SA, Morges), a DIFFERENT company
    from 11783737, and is NOT an alias of this record.
  * Also NOT aliases, and not this company: Microbiosensor Limited,
    Dynamic Biosensors GmbH, SD BIOSENSOR, INC., BIOSENSORS LTD (13052619,
    Wirral), BIOSENSORS BEYOND BORDERS LIMITED (10581522, in liquidation),
    and the several dissolved "... Biosensors ..." companies.
  * "JenaValve Technology, Inc." (Irvine, California) and "JenaValve
    Technology GmbH" are the group's US and German entities and are NOT
    aliases of 09520509.
THE BARE BRIEF WORDS: ONE IS ALIASED, ONE IS NOT, AND THAT WAS TESTED
---------------------------------------------------------------------
NHS Supply Chain's brief writes both suppliers as bare brand words, and
refresh_framework_lots.attach_names() can only attach a lot by resolving the
brief's own string, so a bare-word alias is what would make Lot 1 attach. Each
was tested against company_match before being written, by resolving every
award supplier name in data/company-awards.json through the index the alias
would create. The results differ, so the decisions differ.

  "Jenavalve" IS aliased. company_match.key() reduces it to "jenavalve", and
  nothing else in the Hub's data reduces to that: the only award names in the
  region are "JenaValve Production Ltd." (key "jenavalve production", which
  routes to this record correctly on its full name), and no Hub record's name
  or aliases contain "jena" at all. The bare alias therefore routes no award
  by itself -- it only lets the brief's word reach the record, which is
  exactly what it is for. Lot 1 attaches.

  "Biosensors" IS NOT aliased, deliberately, and Biosensors' Lot 1 is left
  unattached as a result. company_match strips trailing legal-form words, so a
  bare "Biosensors" alias creates the key "biosensors" -- and "Biosensors SA",
  the SWISS group entity (Biosensors Europe SA, Rue de Lausanne 29, Morges),
  reduces to that same key. Two award rows currently sit in
  data/company-awards.json's `unmatched` list under the name "Biosensors SA",
  and the next refresh_awards.py --rematch would publish both of them against
  this UK record: an attribution the source does not make, about a different
  legal person. That is the 17/11/2026 framework-claims error with different
  words in it, and it is not worth a lot attachment.
  This is the Abbott precedent on this very framework, one step along: a
  global alias index cannot carry a per-framework truth. Biosensors' three
  FULL spellings are aliased (key "biosensors international"), so the matrix
  name resolves, the record is reachable, and six award rows route to it
  correctly -- only the brief's bare word does not, so the name will stay in
  the framework's `unresolved` list with its reason recorded here.
  It would become attachable, without this hazard, if a Hub record were ever
  created for Biosensors SA holding that name verbatim: company_match tries
  the unstripped name first, so the Swiss rows would match there instead. That
  is a separate piece of work and is NOT done here.
  Independently re-derived on main by the sibling session working this repo's
  remaining framework-lots residuals, 18/11/2026: with a bare "Biosensors"
  alias the stripped tier would have exactly ONE holder of the key, so both
  Swiss rows would resolve "confirmed" onto this UK record rather than being
  quarantined as ambiguous -- which is the worse of the two failure modes,
  because confirmed rows publish.
  ALSO IN THE UNMATCHED LIST, and harmless only because the rule is exact:
  "Microbiosensor Limited" (key "microbiosensor") and "SD BIOSENSOR, INC."
  (key "sd biosensor"). Neither collides today. But if an alias
  "Biosensors International" is ever added to this record, re-run the same
  collision test first -- that key is one strip away from several of these.

EFFECT ON THE GATE, STATED HONESTLY
-----------------------------------
This does NOT reduce the warning total; the baseline stays 42. Both names move
out of _warn_unresolved_lot_names()'s "resolve to NO Hub record" line, because
both companies now have a record. On the next FULL run of
refresh_framework_lots.py, JenaValve's Lot 1 should attach and that name should
leave `unresolved` altogether; Biosensors' name will stay in `unresolved`
on purpose, for the aliasing reason above, as Abbott's already does. The count
does not move on refresh_framework_lots.py --attach-only, which reuses the
stored `unresolved` lists.

Run after this:
    python3 scripts/refresh_awards.py --rematch
Adding a record makes quarantined award rows resolve. Since commit 36f8a2c
refresh_awards.py re-stamps the ownership notice itself, so the old
stamp_notice.py follow-up is not needed -- but check data/company-awards.json
keeps its `_notice` block.

Run (idempotent -- safe to re-run, writes nothing when already applied):
    python3 scripts/_add_transcatheter_clinical_records_1118.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from seed_format import write_like, describe  # noqa: E402

SEED = os.path.join(ROOT, "data", "supplier-seed.json")
INDEX = os.path.join(ROOT, "data", "supplier-index.json")
ADJ = os.path.join(ROOT, "state", "transcatheter-lot-source-adjudication.json")

TODAY = "2026-11-18"
UK_TODAY = "18/11/2026"

FW_NAME = "Transcatheter Heart Valve Repair, Replacement and Associated Devices"
FW_REF = "2022/S 000-025267"
FW_DATES = "18 September 2023 to 26 February 2027"
FW_CATEGORY = "Medical Technology"
BRIEF_URL = ("https://www.supplychain.nhs.uk/product-information/"
             "contract-launch-brief/"
             "transcatheter-heart-valve-repair-replacement-and-associated-devices/")
MATRIX_URL = ("https://azuksappnpdsa01.blob.core.windows.net/datashare/"
              "Product-Matrix-Transcatheter-Heart-Valve-09-September-2026-MT.xlsx")
LOT1_TITLE = "Transcatheter Aortic Valve Implant (TAVI) System"

CLAIM_RECORD = ("~/.claude/framework-claims/2022-S-000-025267-%s.json" % TODAY)


def framework_entry(named_as, brief_word, extra=""):
    return {
        "name": FW_NAME,
        "dates": FW_DATES,
        "reference": FW_REF,
        "category": FW_CATEGORY,
        "supplierCount": 11,
        "url": BRIEF_URL,
        "source": "nhssc-brief",
        "capturedOn": TODAY,
        "lots": ["Lot 1"],
        "lotSourceUrl": MATRIX_URL,
        "note": ("Named on NHS Supply Chain's own contract launch brief for this "
                 "framework, as \"%s\". 11 suppliers on the framework, stated and "
                 "printed. Lot 1 (%s) per the brief's own attached product matrix "
                 "(Product-Matrix-Transcatheter-Heart-Valve-09-September-2026-MT.xlsx, "
                 "issued 9 September 2026), whose Specification grid names this "
                 "company as \"%s\" and marks it Y on Lot 1 and not on Lot 2. Brief "
                 "and matrix both read at source on %s and recorded by "
                 "framework_award_check.py at %s.%s"
                 % (brief_word, LOT1_TITLE, named_as, UK_TODAY, CLAIM_RECORD,
                    extra)),
    }


BIOSENSORS_FW_EXTRA = (
    " NOTE ON THE LOT ATTACHMENT: this Lot 1 allocation is recorded here because "
    "it was read in the matrix's own cells, but data/framework-lots.json will keep "
    "listing \"Biosensors International UK Limited\" as an unresolved lot-source "
    "name. Attaching it needs the brief's bare word \"Biosensors\" as an alias on "
    "this record, and that alias cannot be added: company_match strips trailing "
    "legal-form words, so \"Biosensors\" and \"Biosensors SA\" -- the Swiss group "
    "entity, which has two award rows in data/company-awards.json's unmatched list "
    "-- reduce to the same key, and the alias would publish those rows against this "
    "UK company. The lot stays unattached rather than risk that, exactly as "
    "Abbott's lots do on this framework.")


def product_categories():
    return [{
        "category": FW_CATEGORY,
        "source": {
            "frameworkRef": FW_REF,
            "frameworkName": FW_NAME,
            "capturedOn": TODAY,
        },
        "generatedBy": "_add_transcatheter_clinical_records_1118.py",
    }]


BIOSENSORS = {
    "name": "Biosensors International UK Ltd",
    "aliases": [
        "Biosensors International UK Ltd",
        "Biosensors International UK Limited",
        "BIOSENSORS INTERNATIONAL UK LIMITED",
        "BIOSENSORS INTERNATIONAL UK LTD",
    ],
    "specialities": ["Cardiology"],
    "products": [],
    "productCategories": product_categories(),
    "frameworks": [framework_entry("Biosensors International UK Limited",
                                   "Biosensors", BIOSENSORS_FW_EXTRA)],
    "alerts": [],
    "news": [],
    "links": [{"label": "NHS Supply Chain contract launch brief for %s" % FW_NAME,
               "url": BRIEF_URL}],
    "awards": [],
    "curated": False,
    "companyNumberCandidate": {
        "number": "11783737",
        "registeredName": "BIOSENSORS INTERNATIONAL UK LTD",
        "companyStatus": "Active",
        "incorporated": "2019-01-23",
        "confidence": "probable",
        "matchedOn": (
            "Companies House name search on %s: BIOSENSORS INTERNATIONAL UK LTD, "
            "11783737, active, incorporated 23/01/2019, registered office 12 New "
            "Fetter Lane, London EC4A 1JP, SIC 32500 and 46460 "
            "(https://find-and-update.company-information.service.gov.uk/company/"
            "11783737). It is the only Companies House company whose name begins "
            "\"Biosensors International UK\", and the registered name differs from "
            "NHS Supply Chain's spelling only in legal form (LTD vs LIMITED). It "
            "stays a CANDIDATE, not companyNumber, because no number published by "
            "the company anchors it: biosensors.com prints no UK company number "
            "and names no UK legal entity, and the address tier of "
            "domain-proof-tier cannot be used either -- 12 New Fetter Lane EC4A 1JP "
            "is the company secretary's own address (BIRD & BIRD COMPANY "
            "SECRETARIES LIMITED, 03952862, same address) and was shared by 344 "
            "companies on the Companies House advanced search on %s, which that "
            "policy's guard says must be treated as no proof at all. A shared name "
            "is not evidence." % (UK_TODAY, UK_TODAY)),
    },
    "relatedBrandSites": [{
        "url": "https://www.biosensors.com/",
        "status": "related brand site, not attributed",
        "source": (
            "Recorded under policy cross-border-sibling-domain-attribution, %s. "
            "biosensors.com is the Biosensors International Group's own site and "
            "names only Biosensors International Group Ltd (Singapore), Biosensors "
            "Interventional Technologies Pte Ltd (36 Jalan Tukang, Singapore) and "
            "Biosensors Europe SA (Rue de Lausanne 29, Morges, Switzerland). It "
            "names no UK legal entity, prints no UK company number and prints no UK "
            "address -- its \"United Kingdom\" entry is a customer-support helpdesk "
            "link. Nothing on it proves it belongs to BIOSENSORS INTERNATIONAL UK "
            "LTD (11783737) at any tier of domain-proof-tier, so it is NOT "
            "attributed to this record and its catalogue (BioFreedom, BioMatrix, "
            "Rise, BioPath, and the ALLEGRA transcatheter aortic valve Biosensors "
            "commercialises with NVT GmbH) is NOT published here. Read %s."
            % (UK_TODAY, UK_TODAY)),
    }],
    "identityNote": (
        "Added %s, resolving a lot-source name on the Transcatheter Heart Valve "
        "Repair, Replacement and Associated Devices framework that reached no Hub "
        "record. WHO THIS IS: BIOSENSORS INTERNATIONAL UK LTD, Companies House "
        "11783737, active, incorporated 23/01/2019, SIC 32500 (manufacture of "
        "medical and dental instruments and supplies) and 46460 (wholesale of "
        "pharmaceutical goods), registered office 12 New Fetter Lane, London EC4A "
        "1JP, read %s. The UK arm of the Biosensors International Group, which is "
        "headquartered in Singapore with its European headquarters in Morges, "
        "Switzerland, and whose ultimate parent is Blue Sail Medical Co., Ltd. "
        "WHY THAT IS CLINICAL: NHS Supply Chain itself names this company, in full, "
        "on the product matrix attached to its own contract launch brief, marked on "
        "Lot 1, Transcatheter Aortic Valve Implant (TAVI) System -- an implanted "
        "cardiac device a clinician chooses for a patient. Its Companies House SIC "
        "codes are medical device manufacture and pharmaceutical wholesale. It is "
        "none of the non-clinical categories the Hub does not carry. WHAT THIS "
        "RECORD MAY NOT SAY: the group's global site biosensors.com names no UK "
        "entity and prints no UK number or UK address, so under "
        "cross-border-sibling-domain-attribution it is recorded as a related brand "
        "site, not attributed (see relatedBrandSites), and under "
        "no-parent-catalogue-credit-to-uk-subsidiary the parent's catalogue is NOT "
        "published under this UK record. `products` is empty for that reason, not "
        "because nothing is known: the Hub publishes a product here only once NHS "
        "Supply Chain's own catalogue or a framework award names that product for "
        "the UK entity. NOT ALIASES, and not this company: \"Biosensors SA\" (the "
        "Swiss group entity, which appears as a supplier name on other Hub award "
        "rows), Microbiosensor Limited, Dynamic Biosensors GmbH, SD BIOSENSOR INC., "
        "BIOSENSORS LTD (13052619, Wirral) and BIOSENSORS BEYOND BORDERS LIMITED "
        "(10581522, in liquidation). THE BARE WORD \"Biosensors\" IS ALSO NOT AN "
        "ALIAS, and that is a decision, not an omission: NHS Supply Chain's brief "
        "writes the supplier that way in its printed list of 11, and aliasing it "
        "would let the brief's word reach this record and attach Lot 1 -- but "
        "company_match strips trailing legal-form words, so \"Biosensors\" and "
        "\"Biosensors SA\" reduce to the same key \"biosensors\", and two award rows "
        "standing in data/company-awards.json's unmatched list under the name "
        "\"Biosensors SA\" would be published against this UK company by the next "
        "refresh_awards.py --rematch. Tested on %s before the alias was rejected. "
        "The lot allocation is recorded in this record's own framework entry "
        "instead, and the lot-source name stays unresolved in "
        "data/framework-lots.json -- the same choice already made for Abbott on "
        "this framework, for the same reason: a global alias index cannot carry a "
        "per-framework truth." % (UK_TODAY, UK_TODAY, UK_TODAY)),
    "note": (
        "Added %s by the transcatheter lot-source run. The verified facts in this "
        "record are: presence on the framework and the Lot 1 allocation (NHS Supply "
        "Chain's own contract launch brief and its attached product matrix, both "
        "read at source %s), and the Companies House registration, status, "
        "incorporation date, registered office and SIC codes (read %s). The company "
        "number is a CANDIDATE, not confirmed -- see companyNumberCandidate. NOT "
        "verified and to be checked at source before use with a customer: ownership "
        "beyond the group statement, turnover, UK headcount, named products, NHS "
        "Supply Chain catalogue lines and contacts. No product is published under "
        "this record on purpose; the group catalogue belongs to the group entities, "
        "not to the UK company." % (UK_TODAY, UK_TODAY, UK_TODAY)),
    "verified": TODAY,
    "source": ("NHS Supply Chain contract launch brief for %s, read %s (%s); the "
               "brief's attached product matrix "
               "Product-Matrix-Transcatheter-Heart-Valve-09-September-2026-MT.xlsx "
               "issued 9 September 2026, downloaded and opened %s (%s); Companies "
               "House company 11783737 overview, officers and persons with "
               "significant control, read %s; biosensors.com home and contact pages, "
               "read %s. Framework claim recorded at %s."
               % (FW_NAME, UK_TODAY, BRIEF_URL, UK_TODAY, MATRIX_URL, UK_TODAY,
                  UK_TODAY, CLAIM_RECORD)),
    "_specialitiesEvidence": (
        "\"Cardiology\" assigned on what NHS Supply Chain's own product matrix lists "
        "for THIS UK entity, not on the framework's title: the matrix names "
        "\"Biosensors International UK Limited\" as a column and marks it on Lot 1, "
        "Transcatheter Aortic Valve Implant (TAVI) System (read %s). Corroborated by "
        "Companies House SIC 32500, manufacture of medical and dental instruments "
        "and supplies. No second speciality is assigned, because no further product "
        "evidence attributable to the UK entity exists -- the group's interventional "
        "cardiology catalogue sits on an unattributed site (see relatedBrandSites)."
        % UK_TODAY),
    "_aliasesEvidence": (
        "\"Biosensors International UK Limited\" and the upper-case spelling are how "
        "NHS Supply Chain's product matrix and several Find a Tender award supplier "
        "lists write this company; \"Biosensors International UK Ltd\" is the "
        "Companies House registered name. All read %s. TWO THINGS ARE DELIBERATELY "
        "NOT HERE. \"Biosensors SA\" -- the Swiss group entity; aliasing it would "
        "re-route its awards onto a different legal person. And the bare word "
        "\"Biosensors\", which is how NHS Supply Chain's brief writes the supplier: "
        "it would make Lot 1 attach, but it reduces to the same company_match key "
        "as \"Biosensors SA\" and would publish that entity's two unmatched award "
        "rows against this record. The lot attachment is given up instead; see "
        "identityNote." % UK_TODAY),
}


JENAVALVE = {
    "name": "JenaValve Production Limited",
    "aliases": [
        "JenaValve Production Limited",
        "JenaValve Production Ltd.",
        "JenaValve Production Ltd",
        "Jenavalve Production Limited",
        "JENAVALVE PRODUCTION LIMITED",
        "Jenavalve",
    ],
    "specialities": ["Cardiology"],
    "products": [
        "Trilogy Transcatheter Heart Valve",
        "Trilogy Delivery System",
        "Trilogy Introducer Sheath",
    ],
    "productCategories": product_categories(),
    "frameworks": [framework_entry("Jenavalve Production Limited", "Jenavalve")],
    "alerts": [],
    "news": [],
    "links": [
        {"label": "JenaValve Trilogy Transcatheter Heart Valve System",
         "url": "https://jenavalve.com/"},
        {"label": "NHS Supply Chain contract launch brief for %s" % FW_NAME,
         "url": BRIEF_URL},
    ],
    "awards": [],
    "curated": False,
    "domain": "jenavalve.com",
    "domainEvidence": {
        "found": ("the company's own group site proves itself to this UK entity at "
                  "the ADDRESS tier of policy domain-proof-tier: "
                  "https://jenavalve.com/contact/ prints \"Unit 9A Astley Way, "
                  "Swillington, Leeds, LS26 8XT, United Kingdom\", which is the "
                  "registered office of Companies House 09520509 verbatim, and "
                  "https://jenavalve.com/eu-uk-privacy-policy/ names the entity "
                  "itself -- \"These include JenaValve Technology GmbH and JenaValve "
                  "Production Ltd.\" The site is operated by JenaValve Technology, "
                  "Inc. (Irvine, California) per its own Terms of Use, so "
                  "cross-border-sibling-domain-attribution applies and is satisfied: "
                  "the site itself, not its branding, proves the UK entity."),
        "on": TODAY,
        "run": "_add_transcatheter_clinical_records_1118.py",
        "tier": "address",
    },
    "companyNumberCandidate": {
        "number": "09520509",
        "registeredName": "JENAVALVE PRODUCTION LIMITED",
        "companyStatus": "Active",
        "incorporated": "2015-03-31",
        "confidence": "probable",
        "matchedOn": (
            "Companies House on %s: JENAVALVE PRODUCTION LIMITED, 09520509, active, "
            "incorporated 31/03/2015, registered office Unit 9a Astley Way, Astley "
            "Lane Industrial Estate, Swillington, Leeds LS26 8XT, SIC 32500 "
            "(https://find-and-update.company-information.service.gov.uk/company/"
            "09520509). It is the only Companies House company using \"JenaValve\", "
            "and NHS Supply Chain's matrix spells the supplier \"Jenavalve "
            "Production Limited\". STRONGER THAN A BARE NAME MATCH: the company's "
            "own group site names \"JenaValve Production Ltd.\" as its affiliate AND "
            "prints that same Leeds registered office, and a company director is "
            "resident at 4 Cromwell, Irvine, California, the address of JenaValve "
            "Technology, Inc. It is nevertheless recorded as a CANDIDATE rather than "
            "companyNumber because the number itself is published nowhere by the "
            "company: domain-proof-tier's address tier proves the SITE belongs to "
            "this entity, and its guard is explicit that it does not do more. Same "
            "treatment as Artivion UK Ltd (03837138) in this seed." % UK_TODAY),
    },
    "identityNote": (
        "Added %s, resolving a lot-source name on the Transcatheter Heart Valve "
        "Repair, Replacement and Associated Devices framework that reached no Hub "
        "record. WHO THIS IS: JENAVALVE PRODUCTION LIMITED, Companies House "
        "09520509, active, incorporated 31/03/2015, SIC 32500 (manufacture of "
        "medical and dental instruments and supplies), registered office Unit 9a "
        "Astley Way, Astley Lane Industrial Estate, Swillington, Leeds LS26 8XT, "
        "read %s. The UK manufacturing entity of the JenaValve group, whose parent "
        "JenaValve Technology, Inc. is in Irvine, California; the group's EU/UK "
        "privacy policy names \"JenaValve Production Ltd.\" and \"JenaValve "
        "Technology GmbH\" as its affiliates. WHAT IT SELLS, read on the group's own "
        "site (https://jenavalve.com/, %s), which is attributed to this entity at "
        "the address tier of domain-proof-tier (see domainEvidence): the Trilogy "
        "Transcatheter Heart Valve System for aortic regurgitation -- a "
        "self-expanding nitinol-framed porcine pericardial valve with locator "
        "technology, its delivery system, and its 85 cm introducer sheath. The site "
        "states Trilogy is the only TAVR system FDA-approved for aortic "
        "regurgitation. WHY THAT IS CLINICAL: an implanted transcatheter heart valve "
        "and its delivery hardware, which NHS Supply Chain itself marks on Lot 1, "
        "Transcatheter Aortic Valve Implant (TAVI) System. Not remotely one of the "
        "non-clinical categories the Hub does not carry. NOT ALIASES, and not this "
        "company: JenaValve Technology, Inc. (the US parent) and JenaValve "
        "Technology GmbH (the German entity) are different legal persons; aliasing "
        "either would re-route awards under parent-subsidiary-award-credit's guard. "
        "The bare word \"Jenavalve\" IS an alias because the owner's brief writes "
        "the supplier that way in its printed list of 11; it appears as a supplier "
        "string on this framework and no other, and no other Hub record's name or "
        "aliases contain \"jena\", so it cannot re-route another company's award."
        % (UK_TODAY, UK_TODAY, UK_TODAY)),
    "note": (
        "Added %s by the transcatheter lot-source run. The verified facts in this "
        "record are: presence on the framework and the Lot 1 allocation (NHS Supply "
        "Chain's own contract launch brief and its attached product matrix, both "
        "read at source %s), the Companies House registration, status, incorporation "
        "date, registered office and SIC code (read %s), and the product names and "
        "the device description (read on the group's own site, which is attributed "
        "to this entity at the address tier -- see domainEvidence). The company "
        "number is a CANDIDATE, not confirmed. NOT verified and to be checked at "
        "source before use with a customer: ownership structure, turnover, UK "
        "headcount, which products are actually stocked on NHS Supply Chain's "
        "catalogue, UK regulatory status (the FDA approval the site states is a US "
        "fact), and contacts." % (UK_TODAY, UK_TODAY, UK_TODAY)),
    "verified": TODAY,
    "source": ("NHS Supply Chain contract launch brief for %s, read %s (%s); the "
               "brief's attached product matrix "
               "Product-Matrix-Transcatheter-Heart-Valve-09-September-2026-MT.xlsx "
               "issued 9 September 2026, downloaded and opened %s (%s); Companies "
               "House company 09520509 overview, officers and persons with "
               "significant control, read %s; jenavalve.com home, contact, about, "
               "terms of use and EU/UK privacy policy pages, read %s. Framework "
               "claim recorded at %s."
               % (FW_NAME, UK_TODAY, BRIEF_URL, UK_TODAY, MATRIX_URL, UK_TODAY,
                  UK_TODAY, CLAIM_RECORD)),
    "_specialitiesEvidence": (
        "\"Cardiology\" assigned on PRODUCT-level evidence, not on the framework: "
        "the company's own group site (attributed to this entity at the address tier "
        "of domain-proof-tier) sells the Trilogy Transcatheter Heart Valve, its "
        "delivery system and its introducer sheath for transcatheter aortic valve "
        "replacement in aortic regurgitation (read %s). Corroborated by Companies "
        "House SIC 32500 and by NHS Supply Chain's own matrix marking this company "
        "on Lot 1, Transcatheter Aortic Valve Implant (TAVI) System." % UK_TODAY),
    "_aliasesEvidence": (
        "\"Jenavalve Production Limited\" is how NHS Supply Chain's product matrix "
        "writes it; \"JenaValve Production Ltd.\" is how Find a Tender award "
        "supplier lists and the company's own EU/UK privacy policy write it; "
        "\"JENAVALVE PRODUCTION LIMITED\" is the Companies House registered name; "
        "\"Jenavalve\" is how NHS Supply Chain's own contract launch brief writes "
        "the supplier in its printed list of 11, and a lot cannot attach without "
        "it. All read %s. JenaValve Technology, Inc. and JenaValve Technology GmbH "
        "are deliberately NOT here -- different legal persons." % UK_TODAY),
}

RECORDS = [BIOSENSORS, JENAVALVE]


def load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dedupe_product_categories(rec):
    """The gate FAILs on a duplicate category name in productCategories."""
    seen, out = set(), []
    for row in rec.get("productCategories") or []:
        cat = (row.get("category") or "").strip() if isinstance(row, dict) else ""
        if cat and cat in seen:
            continue
        if cat:
            seen.add(cat)
        out.append(row)
    if out != (rec.get("productCategories") or []):
        rec["productCategories"] = out
        return True
    return False


def apply_to(doc, label):
    """Idempotently apply this run's changes to one supplier document.

    Returns a list of the changes made; an empty list means it was already done.
    """
    changed = []
    sups = doc.get("suppliers") or []
    by_name = {s.get("name"): s for s in sups if isinstance(s, dict)}

    for want in RECORDS:
        rec = by_name.get(want["name"])
        if rec is None:
            # Guard against a near-duplicate arriving under another spelling.
            clash = [s.get("name") for s in sups
                     if isinstance(s, dict)
                     and ((s.get("name") or "") in want["aliases"]
                          or any(a in want["aliases"]
                                 for a in (s.get("aliases") or [])))]
            if clash:
                raise SystemExit(
                    "%s: %r would collide with existing record(s) %r -- stopping "
                    "rather than creating a second record for the same company."
                    % (label, want["name"], clash))
            sups.append(json.loads(json.dumps(want)))
            changed.append("added %s" % want["name"])
            continue
        for key, val in want.items():
            if rec.get(key) != val:
                rec[key] = json.loads(json.dumps(val))
                changed.append("%s: set %s" % (want["name"], key))
        if dedupe_product_categories(rec):
            changed.append("%s: deduped productCategories" % want["name"])

    return changed


def write_adjudication():
    doc = {
        "_what": ("Transcatheter Heart Valve Repair, Replacement and Associated "
                  "Devices -- every lot-source supplier name on the framework's NHS "
                  "Supply Chain product matrix that reached no Hub supplier record, "
                  "and what was decided about it. Written by "
                  "scripts/_add_transcatheter_clinical_records_1118.py so these "
                  "decisions are recorded once and not re-worked."),
        "framework": FW_NAME,
        "frameworkReference": FW_REF,
        "frameworkDates": FW_DATES,
        "briefUrl": BRIEF_URL,
        "matrixUrl": MATRIX_URL,
        "matrixIssued": "2026-09-09",
        "briefSupplierCount": 11,
        "briefSupplierCountSource": ("the brief states \"There are 11 suppliers in "
                                     "total on this framework\" and prints exactly "
                                     "11, so the capture is complete"),
        "briefSuppliers": ["Abbott", "Acrostak", "Biosensors", "BVM", "Dot Medical",
                           "Edwards", "Jenavalve", "MCT", "Medtronic", "Meril",
                           "SMT"],
        "lotTitles": {
            "Lot 1": LOT1_TITLE,
            "Lot 2": ("Transcatheter Non-Aortic Valve/Chord Repair and Replacement "
                      "System, Components and Accessories"),
        },
        "frameworkClaimRecord": CLAIM_RECORD,
        "decidedOn": TODAY,
        "ruling": ("Lou's standing ruling that the Hub does not carry non-clinical "
                   "framework suppliers -- catering, facilities and electrical, "
                   "furniture, office supplies, food. Both companies decided here "
                   "are clinical device suppliers, so both are in scope. The "
                   "speciality on each record comes from the product evidence, not "
                   "from the framework."),
        "included": [
            {"name": "Biosensors International UK Limited",
             "lots": ["Lot 1"],
             "verdict": "included-clinical",
             "record": "Biosensors International UK Ltd",
             "companyNumberCandidate": "11783737",
             "companyStatus": "Active",
             "why": ("NHS Supply Chain's own product matrix names this company in "
                     "full and marks it on Lot 1, Transcatheter Aortic Valve "
                     "Implant (TAVI) System; Companies House SIC 32500 and 46460. "
                     "The UK arm of the Biosensors International Group (Singapore; "
                     "European HQ Morges, Switzerland; ultimate parent Blue Sail "
                     "Medical Co., Ltd)."),
             "constraints": ("biosensors.com names no UK entity and prints no UK "
                             "number or UK address, so it is recorded as a related "
                             "brand site, NOT attributed "
                             "(cross-border-sibling-domain-attribution), and the "
                             "group catalogue is NOT published under the UK record "
                             "(no-parent-catalogue-credit-to-uk-subsidiary). "
                             "`products` is empty on purpose. The number is a "
                             "candidate only: the registered office 12 New Fetter "
                             "Lane EC4A 1JP is the company secretary's own address "
                             "and was shared by 344 companies on 18/11/2026, which "
                             "domain-proof-tier's guard says is no proof at all."),
             "lotAttached": False,
             "lotAttachedWhyNot": (
                 "Attaching Lot 1 needs the brief's bare word \"Biosensors\" as an "
                 "alias, and that alias is unsafe: company_match strips trailing "
                 "legal-form words, so \"Biosensors\" and \"Biosensors SA\" (the "
                 "Swiss group entity) reduce to the same key \"biosensors\", and the "
                 "two award rows sitting in data/company-awards.json's unmatched "
                 "list under \"Biosensors SA\" would be published against this UK "
                 "record by the next refresh_awards.py --rematch. Tested 18/11/2026. "
                 "The Lot 1 allocation is recorded on the record's own framework "
                 "entry instead; the lot-source name stays in the framework's "
                 "unresolved list. Same choice as Abbott on this framework. It would "
                 "become attachable if a Hub record for Biosensors SA ever held that "
                 "name verbatim, because company_match tries the unstripped name "
                 "first -- separate work, not done here. Independently re-derived "
                 "on main by the sibling session working this repo's remaining "
                 "framework-lots residuals, 18/11/2026: the alias would leave "
                 "exactly ONE holder of the key, so the Swiss rows would resolve "
                 "\"confirmed\" and PUBLISH, not quarantine as ambiguous."),
             "collisionRetestWarning": (
                 "data/company-awards.json's unmatched list also holds "
                 "\"Microbiosensor Limited\" (key \"microbiosensor\") and "
                 "\"SD BIOSENSOR, INC.\" (key \"sd biosensor\"). Neither collides "
                 "with this record today. If the alias \"Biosensors International\" "
                 "is ever added here, re-run the same collision test first."),
             "notAliased": ["Biosensors SA (and the bare word \"Biosensors\")",
                            "Microbiosensor Limited",
                            "Dynamic Biosensors GmbH", "SD BIOSENSOR, INC.",
                            "BIOSENSORS LTD (13052619)",
                            "BIOSENSORS BEYOND BORDERS LIMITED (10581522)"],
             "sources": [BRIEF_URL, MATRIX_URL,
                         "https://find-and-update.company-information.service.gov.uk/"
                         "company/11783737",
                         "https://www.biosensors.com/intl/contact-us"]},
            {"name": "Jenavalve Production Limited",
             "lots": ["Lot 1"],
             "verdict": "included-clinical",
             "record": "JenaValve Production Limited",
             "companyNumberCandidate": "09520509",
             "companyStatus": "Active",
             "why": ("Sells the Trilogy Transcatheter Heart Valve System for aortic "
                     "regurgitation -- valve, delivery system and introducer sheath "
                     "-- read on the group's own site, which is attributed to this "
                     "entity at the address tier of domain-proof-tier. NHS Supply "
                     "Chain's matrix marks it on Lot 1. Companies House SIC 32500. "
                     "The UK manufacturing entity of the JenaValve group."),
             "constraints": ("Domain jenavalve.com attributed at the ADDRESS tier: "
                             "the site prints the Leeds registered office of "
                             "09520509 verbatim and names \"JenaValve Production "
                             "Ltd.\" as an affiliate. The number is still a "
                             "candidate, because the address tier proves the site, "
                             "not the number, and the company publishes no number "
                             "-- same treatment as Artivion UK Ltd (03837138)."),
             "lotAttached": True,
             "lotAttachedWhyNot": None,
             "bareBriefWordAliased": (
                 "Yes -- \"Jenavalve\". Tested 18/11/2026 against every award "
                 "supplier name in data/company-awards.json: nothing else reduces to "
                 "the key \"jenavalve\" (the only award names in the region are "
                 "\"JenaValve Production Ltd.\", key \"jenavalve production\", which "
                 "routes here on its full name), and no other Hub record's name or "
                 "aliases contain \"jena\". The bare alias therefore routes no award "
                 "by itself; it only lets the brief's own word reach this record so "
                 "Lot 1 attaches."),
             "notAliased": ["JenaValve Technology, Inc.",
                            "JenaValve Technology GmbH"],
             "sources": [BRIEF_URL, MATRIX_URL,
                         "https://find-and-update.company-information.service.gov.uk/"
                         "company/09520509",
                         "https://jenavalve.com/contact/",
                         "https://jenavalve.com/eu-uk-privacy-policy/"]},
        ],
        "excluded": [],
        "alreadyDecidedElsewhere": [
            {"name": "Abbott Meditcal UK Limited",
             "lots": ["Lot 1", "Lot 2"],
             "verdict": "decided-in-b983be2",
             "why": ("NHS Supply Chain's own matrix misspelling, put on Abbott "
                     "Medical U.K. Ltd by commit b983be2. Abbott's lots stay "
                     "unattached on purpose: the brief's bare word \"Abbott\" "
                     "resolves to Abbott Diabetes Care, and a global alias index "
                     "cannot carry a per-framework truth. Not touched by this run.")},
        ],
        "residual": ("Both companies now have a Hub record, so neither name is a "
                     "\"no Hub record\" case any more. Unlike the Hand Hygiene "
                     "framework, the owner's brief DOES name both, so a lot CAN "
                     "attach -- and on the next FULL run of "
                     "refresh_framework_lots.py it should, for JenaValve. TWO NAMES "
                     "WILL REMAIN in this framework's `unresolved` list on purpose, "
                     "each with its reason recorded: \"Biosensors International UK "
                     "Limited\", because the bare-word alias its brief row needs "
                     "would re-route Biosensors SA's two unmatched award rows (see "
                     "its lotAttachedWhyNot above), and \"Abbott Meditcal UK "
                     "Limited\", decided in commit b983be2 for the same shape of "
                     "reason. Neither is an open question. The count does not move "
                     "on refresh_framework_lots.py --attach-only, which reuses the "
                     "stored unresolved lists."),
        "otherBareWordsOnThisFramework": (
            "Reported by the sibling session working this repo's remaining "
            "framework-lots residuals, 18/11/2026, and recorded here so this "
            "framework's bare-word picture is in one place: the brief's bare words "
            "now attach for Edwards (Lots 1 and 2, via the matrix's own misspelling "
            "\"Edwards Lidesciences Limited\"), BVM and MCT. \"Abbott\" stays "
            "unattached and must NOT be aliased -- it resolves to Abbott Diabetes "
            "Care. With the two records added here, suppliersWithoutLot on this "
            "framework should come down to Abbott and Biosensors."),
    }
    before = None
    if os.path.exists(ADJ):
        try:
            before = load(ADJ)
        except ValueError:
            before = None
    if before == doc:
        print("state/transcatheter-lot-source-adjudication.json already current")
        return
    fmt, rt = write_like(ADJ, doc)
    print(describe(ADJ, fmt, rt))


def main():
    any_change = False
    for path, label in ((SEED, "data/supplier-seed.json"),
                        (INDEX, "data/supplier-index.json")):
        doc = load(path)
        changes = apply_to(doc, label)
        if not changes:
            print("%s: already applied, nothing written" % label)
            continue
        any_change = True
        fmt, rt = write_like(path, doc)
        print(describe(path, fmt, rt))
        for c in changes:
            print("   %s" % c)
    write_adjudication()
    if not any_change:
        print("no supplier change needed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
