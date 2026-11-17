#!/usr/bin/env python3
"""Hand Hygiene lot-source names: the clinical ones get a Hub record, 17/11/2026.

WHY THIS RUN EXISTS
-------------------
check_framework_lots()'s first warning counts lot-source supplier names that
resolve to NO Hub supplier record (86 names across 30 frameworks on 17/11/2026).
Eight of them sit on one framework, Hand Hygiene and Associated Products and
Services. Lou's ruling (Needs-Lou N886, answered 17/11/2026) was "hand hygiene
yes, the others no", refined to "depends on the product as hand hygiene could be
classed as clinical". So each of the eight was decided on what the company
actually sells, read on its own site, not on the framework it is named on.

WHAT WAS VERIFIED AT SOURCE, TODAY
----------------------------------
* Find a Tender award notice 000335-2023 (ocid ocds-h6vhtk-02ad97, award release
  dated 2023-01-06), read 17/11/2026 through the OCDS release-package API. It
  awards 33 supplier names across the framework's five lots. All eight names
  below are on it, with the lots recorded against each one here.
  Recorded by ~/.claude/hooks/framework_award_check.py as required by Lou's
  17/11/2026 framework-claims rule: ~/.claude/framework-claims/000335-2023-2026-11-17.json
* NHS Supply Chain's own contract launch brief for the framework, read
  17/11/2026. It states "There are 21 suppliers on the framework" and lists 21.
  It names NONE of the eight. The capture is not short -- the stated count and
  the printed list agree -- so the notice and the brief genuinely differ: the
  award named 33 in January 2023, the owner's current list names 21.

  That is why no `supplierLots` entry can be attached for these names, and why
  every framework entry written below is sourced to the AWARD NOTICE and says in
  its own text that NHS Supply Chain's current supplier list does not name the
  company. Nobody is presented as currently on the framework. This is the same
  harm check_no_delisted_as_a_route() exists to prevent, one state along: not
  delisted by the brief, simply absent from it.

THE DECISIONS
-------------
IN -- genuinely clinical:

* Esteve Pharmaceuticals Ltd (Lot 4, Emollient Conditioning Creams). A
  prescription pharmaceutical company. Its own UK site (esteve.com/uk, read
  17/11/2026) sells Aquamax skin cream 100g, Aquamax skin cream 500g and Aquamax
  body wash 250g, and describes Aquamax as "an innovative formula for eczema,
  psoriasis and other dry skin conditions"; the same site carries a Prescription
  products section. Aquamax cream is in the NHS dm+d under this company's name.
  A licensed leave-on emollient for eczema and psoriasis is clinical skin care,
  not a washroom consumable. NEW RECORD.

* GOJO / Purell (Lots 1, 3 and 4). Already a Hub record, so this run adds no
  second one -- it adds the award name as an alias so the lot source resolves,
  and the award itself as a framework entry. PURELL Advanced is certified to
  EN 12791, the surgical hand-rub standard, and the record's own product list is
  already the healthcare range. Clinical beyond argument. EXISTING RECORD
  EXTENDED -- and its alert kept honest: GOJO WAS awarded on Lots 1, 3 and 4 at
  the January 2023 award notice, and is NOT on NHS Supply Chain's current
  21-supplier list, which the alert already said and which today's reading of
  the brief confirms.

OUT -- with the reason, so nobody redoes this work:

* Aqualution System Ltd (Lot 2). Companies House 04100816, active; the number is
  published on its own site. Hypochlorous acid manufacturer. Its OWN brands are
  Salvesan (surface disinfectant), Solosan (animal first aid), Agripure
  (agriculture and food processing) and Within Skincare (cosmetic-grade). Its
  medical offer is a private-label category with no named clinical product, a
  bare "CE-marked" claim with no device class, and no stated NHS or hospital use
  beyond "Hospital & Clinic Sanitation -- surface disinfection". Genuinely
  borderline, so left out: a thin page asserting a clinical range it does not
  name would be worse than no page.
* INEOS ENTERPRISES GROUP LIMITED (Lots 1, 3). Companies House 04687714,
  previously INEOS CHLOR GROUP LIMITED, Bankes Lane, Runcorn -- a chlor-chemicals
  group entity. INEOS's own site describes INEOS Hygienics as "a successful
  household and personal care brand" in FMCG, established in response to the
  pandemic, and names no clinical product. Not a clinical supplier.
* Zoono Holdings Ltd (Lot 4). Companies House 11027188. Its own site sells
  alcohol-free sanitiser, body and surface wipes, a foot spray, a mould defence
  system and room deodorisers, with a surface-bonding antimicrobial as the
  pitch. No clinical product, no medical device registration. Surface and
  consumer antimicrobial, not clinical.
* QYK BRANDS LLC (Lot 4). A US LLC: no UK registration is expected and none was
  found, so the identity cannot be settled at the Companies House bar
  identity-vocabulary-policy.json sets. Its product is general-purpose
  sanitiser. Out on both counts.
* SpectrumX (Lot 2). A bare trading word. Companies House carries at least seven
  distinct companies using it -- SPECTRUMX HEALTHCARE LIMITED (12622911, in
  liquidation), SPECTRUMX HOLDINGS LIMITED (13039699, in liquidation),
  SPECTRUMX MEDICAL LIMITED (13042763), SPECTRUMX DIRECT LIMITED (13042692),
  SPECTRUMX HOLDINGS UK LTD (13745475), and two dissolved. The notice gives no
  number, so which one holds Lot 2 cannot be settled. A shared name is not
  evidence. Identity first, record after -- never the other way round.
* J A Marketing limited (Lot 4). Both Companies House candidates are DISSOLVED
  (04313818, Elland, dissolved 01/08/2025; 17156425, Lincoln, dissolved
  22/09/2026 and incorporated after the 2023 award, so it cannot be the
  awardee). No product evidence for the name anywhere -- no site, no catalogue
  entry, no dm+d listing. Nothing to write a record from.

Catering, facilities/electrical, furniture, office-supply and food names on the
other frameworks stay out entirely, per Lou's ruling. Not revisited here.

EFFECT ON THE GATE, STATED HONESTLY
-----------------------------------
This does NOT reduce the warning total. _warn_unresolved_lot_names() sorts an
unresolved name by whether it reaches a Hub record: giving Esteve one, and
giving the GOJO record the award spelling as an alias, moves those two names out
of the "resolve to NO Hub record" line (86 -> 84) and into the "DO resolve, but
the brief does not name them" line (48 -> 50). Both lines are warnings and the
baseline stays 42. The second line is the truthful home for them, because the
brief really does not name them -- and today's reading of the brief proves the
capture is complete, so the remedy that line offers ("re-read the brief") does
not apply to this framework either. That residual belongs to the 48-name job,
not to this one.

Run (idempotent -- safe to re-run, writes nothing when already applied):
    python3 scripts/_add_hand_hygiene_clinical_records_1117.py
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
ADJ = os.path.join(ROOT, "state", "hand-hygiene-lot-source-adjudication.json")

TODAY = "2026-11-17"
UK_TODAY = "17/11/2026"

NOTICE_URL = "https://www.find-tender.service.gov.uk/Notice/000335-2023"
BRIEF_URL = ("https://www.supplychain.nhs.uk/product-information/"
             "contract-launch-brief/hand-hygiene-and-associated-products-and-services/")
FW_LABEL = ("Hand Hygiene and Associated Products and Services "
            "(awarded January 2023; not on NHS Supply Chain's current supplier list)")

ABSENT = ("NHS Supply Chain's own contract launch brief for this framework, read "
          "%s, states \"There are 21 suppliers on the framework\" and lists 21. It "
          "does not name this company, and the stated count matches the printed "
          "list, so the capture is complete and the two sources genuinely differ: "
          "the award notice named 33 suppliers in January 2023, the owner's current "
          "list names 21. This company is therefore NOT presented as currently on "
          "the framework, and no lot can be attached to a brief row that does not "
          "exist. Brief read at %s." % (UK_TODAY, BRIEF_URL))


def framework_entry(named_as, lots):
    lotwords = ", ".join("Lot %s" % n for n in lots)
    return {
        "name": FW_LABEL,
        "dates": "12 June 2023 to 11 June 2027",
        "reference": "2023/S 000-000335",
        "category": "Medical and Surgical Consumables",
        "url": NOTICE_URL,
        "source": "fts-award",
        "capturedOn": TODAY,
        "lots": ["Lot %s" % n for n in lots],
        "note": ("Named as an awarded supplier on Find a Tender contract award notice "
                 "000335-2023 for this framework, as \"%s\", on %s. The notice (award "
                 "release dated 06/01/2023, ocid ocds-h6vhtk-02ad97) was read at source "
                 "on %s through the Find a Tender OCDS release-package API and recorded "
                 "by framework_award_check.py. %s"
                 % (named_as, lotwords, UK_TODAY, ABSENT)),
    }


ESTEVE = {
    "name": "Esteve Pharmaceuticals Ltd",
    "aliases": ["Esteve Pharmaceuticals Ltd", "Esteve Pharmaceuticals, Ltd.",
                "ESTEVE PHARMACEUTICALS LTD", "Esteve Pharmaceuticals Limited"],
    "specialities": ["Dermatology and skin health"],
    "products": ["Aquamax skin cream 100g", "Aquamax skin cream 500g",
                 "Aquamax body wash 250g"],
    "frameworks": [framework_entry("Esteve Pharmaceuticals Ltd", ["4"])],
    "alerts": [],
    "news": [],
    "links": [],
    "awards": [],
    "curated": False,
    "companyNumber": "03393686",
    "companyNumberSource": (
        "Published by the company itself: esteve.com's own legal notice lists "
        "\"Esteve Pharmaceuticals, Ltd. The Round House, The Courtyard Barns, Choke "
        "Lane, Cookham Dean, Maidenhead Berkshire, United Kingdom SL6 6PT ... Company "
        "No. 3393686\" (https://www.esteve.com/uk/legal-notice/, read %s). It matches "
        "the register: ESTEVE PHARMACEUTICALS LTD, 03393686, active, incorporated "
        "27/06/1997, registered office The Round House, The Courtyard Barns, Choke "
        "Lane, Cookham Dean, Maidenhead, Berkshire SL6 6PT "
        "(https://find-and-update.company-information.service.gov.uk/company/03393686, "
        "read %s). Confirmed on the company's own publication, not a name search."
        % (UK_TODAY, UK_TODAY)),
    "identityNote": (
        "Added %s, working the Hand Hygiene lot-source names under Lou's ruling that "
        "hand-hygiene framework suppliers come in where the product is genuinely "
        "clinical. WHAT THIS COMPANY SELLS, read on its own site "
        "(https://www.esteve.com/uk/patients/products/otc, %s): Aquamax skin cream "
        "100g, Aquamax skin cream 500g and Aquamax body wash 250g, with Aquamax "
        "described by Esteve as \"an innovative formula for eczema, psoriasis and "
        "other dry skin conditions\"; the same site carries a separate Prescription "
        "products section. Aquamax cream appears in the NHS dictionary of medicines "
        "and devices under Esteve Pharmaceuticals Ltd in 100g and 500g packs. WHY THAT "
        "IS CLINICAL: a licensed leave-on emollient indicated for eczema and psoriasis, "
        "from a prescription pharmaceutical company, is clinical skin care a clinician "
        "chooses for a patient -- not a washroom consumable, a dispenser or a "
        "general-purpose sanitiser, which is the line Lou's ruling draws. Esteve "
        "Pharmaceuticals is the former Intrapharm Laboratories; ESTEVE RD UK & IRELAND "
        "LTD. (06837207) shares the registered address and is a DIFFERENT company -- "
        "not an alias of this record." % (UK_TODAY, UK_TODAY)),
    "note": (
        "Added %s by the hand-hygiene lot-source run, resolving an unresolved-name gap "
        "on the Hand Hygiene and Associated Products and Services framework. The "
        "verified facts in this record are: the Find a Tender award (notice 000335-2023, "
        "Lot 4, read at source %s), the company number (published on the company's own "
        "legal notice and matching the register), and the product names and their stated "
        "indication (read on the company's own UK site). This company is NOT on NHS "
        "Supply Chain's current 21-supplier list for the framework -- see the framework "
        "entry. Ownership, turnover, UK headcount and NHS Supply Chain catalogue "
        "presence have NOT been verified and must be checked at source before being "
        "used with a customer." % (UK_TODAY, UK_TODAY)),
    "verified": TODAY,
    "source": ("Find a Tender contract award notice 000335-2023 (ocid "
               "ocds-h6vhtk-02ad97), read %s; NHS Supply Chain contract launch brief "
               "for the framework, read %s; esteve.com/uk OTC products and legal "
               "notice, read %s; Companies House company 03393686, read %s."
               % (UK_TODAY, UK_TODAY, UK_TODAY, UK_TODAY)),
    "_specialitiesEvidence": (
        "\"Dermatology and skin health\" assigned on PRODUCT-level evidence, not on the "
        "framework: Esteve's own UK site sells Aquamax as a leave-on emollient for "
        "eczema, psoriasis and other dry skin conditions (read %s)." % UK_TODAY),
}

GOJO_ALIAS = "GOJO Industries Europe Ltd"
GOJO_EXTRA_ALIASES = [GOJO_ALIAS, "GOJO Industries - Europe Ltd",
                      "GOJO INDUSTRIES - EUROPE LIMITED",
                      "GOJO Industries-Europe Limited"]

GOJO_ALERT_ADDITION = (
    " AWARD RECORD, read at source %s: Find a Tender contract award notice 000335-2023 "
    "for this framework (award release 06/01/2023, ocid ocds-h6vhtk-02ad97) DOES name "
    "\"GOJO Industries Europe Ltd\" as an awarded supplier on Lot 1 (Hand Hygiene 3-Step "
    "Process), Lot 3 (PPE Pandemic Products) and Lot 4 (Emollient Conditioning Creams). "
    "That award and the sentence above are both true and must be quoted together: GOJO "
    "was awarded on the framework in January 2023 and is absent from NHS Supply Chain's "
    "current supplier list for it, which on %s states 21 suppliers and names 21, none of "
    "them GOJO. Companies House on %s: GOJO INDUSTRIES - EUROPE LIMITED, 02473045, "
    "company status Liquidation, registered office C/O AlixPartners UK LLP, 6 New Street "
    "Square, London EC4A 3BF." % (UK_TODAY, UK_TODAY, UK_TODAY))

GOJO_NUMBER_CANDIDATE = {
    "number": "02473045",
    "registeredName": "GOJO INDUSTRIES - EUROPE LIMITED",
    "companyStatus": "Liquidation",
    "incorporated": "1990-02-22",
    "confidence": "probable",
    "matchedOn": (
        "Companies House name search on %s "
        "(https://find-and-update.company-information.service.gov.uk/company/02473045) "
        "-- NOT verified against a number published by the company; gojo.com refuses "
        "automated requests, so route 2 of docs/COMPANY-REPORT-METHOD.md could not be "
        "run. It stays a candidate. The registered name differs from the award notice's "
        "spelling only in hyphenation and legal form, and this record's own existing "
        "alert already names GOJO Industries-Europe Limited as the UK entity -- but a "
        "shared name is not evidence, so it is not written to companyNumber."
        % UK_TODAY),
}

EXCLUDED = [
    {
        "name": "Aqualution System Ltd",
        "lots": ["Lot 2"],
        "verdict": "excluded-borderline",
        "companyNumber": "04100816",
        "companyStatus": "Active",
        "why": ("Hypochlorous acid manufacturer. Its own brands, read on aqualution.co.uk "
                "on %s, are Salvesan (surface disinfectant), Solosan (animal first aid), "
                "Agripure (agriculture and food processing) and Within Skincare "
                "(cosmetic-grade). The medical offer is a private-label CATEGORY with no "
                "named clinical product, a bare \"CE-marked\" claim with no device class, "
                "and no stated NHS or hospital use beyond \"Hospital & Clinic Sanitation "
                "-- surface disinfection\". Genuinely borderline under Lou's \"depends on "
                "the product\" ruling, so left out: a record asserting a clinical range "
                "the company does not itself name would be worse than no record. Revisit "
                "only if Aqualution publishes a named clinical product with a device "
                "class. Company number 04100816 is published on its own site and matches "
                "the register, so identity is not the blocker here -- the product is."
                % UK_TODAY),
        "sources": ["https://www.aqualution.co.uk/about-us/",
                    "https://www.aqualution.co.uk/private-label/medical/"],
    },
    {
        "name": "INEOS ENTERPRISES GROUP LIMITED",
        "lots": ["Lot 1", "Lot 3"],
        "verdict": "excluded-not-clinical",
        "companyNumber": "04687714",
        "companyStatus": "Active",
        "why": ("Companies House 04687714, previously INEOS CHLOR GROUP LIMITED, Bankes "
                "Lane Office, Runcorn -- a chlor-chemicals group entity, not a medical "
                "supplier. INEOS's own site describes INEOS Hygienics as \"a successful "
                "household and personal care brand\" in FMCG, established in response to "
                "the pandemic, and names no clinical product (read %s). General-purpose "
                "and consumer sanitiser is the side of Lou's line that stays out."
                % UK_TODAY),
        "sources": ["https://www.ineos.com/businesses/ineos-hygienics/"],
    },
    {
        "name": "Zoono Holdings Ltd",
        "lots": ["Lot 4"],
        "verdict": "excluded-not-clinical",
        "companyNumber": "11027188",
        "companyStatus": "Active",
        "why": ("Companies House 11027188. Its own site (zoono.com, which redirects to "
                "zoono.co.nz, read %s) sells alcohol-free sanitiser, body and surface "
                "wipes, a foot spray, a mould defence system and room deodorisers, with "
                "a surface-bonding antimicrobial molecule as the pitch. No clinical "
                "product, no medical device registration. Surface and consumer "
                "antimicrobial, not clinical." % UK_TODAY),
        "sources": ["https://www.zoono.co.nz/"],
    },
    {
        "name": "QYK BRANDS LLC",
        "lots": ["Lot 4"],
        "verdict": "excluded-identity-unsettled",
        "companyNumber": None,
        "companyStatus": None,
        "why": ("A US LLC. No UK registration is expected and none was found on %s, so "
                "the identity cannot be settled at the bar "
                "data/identity-vocabulary-policy.json sets, and the notice gives no "
                "number. Its product is general-purpose hand sanitiser, so it would fail "
                "the clinical test even with the identity settled. Out on both counts."
                % UK_TODAY),
        "sources": ["https://find-and-update.company-information.service.gov.uk/"
                    "search/companies?q=QYK+BRANDS"],
    },
    {
        "name": "SpectrumX",
        "lots": ["Lot 2"],
        "verdict": "excluded-identity-unsettled",
        "companyNumber": None,
        "companyStatus": None,
        "why": ("A bare trading word with no legal form, and the notice gives no number. "
                "Companies House on %s carries at least seven distinct companies using "
                "it: SPECTRUMX HEALTHCARE LIMITED (12622911, Liquidation), SPECTRUMX "
                "HOLDINGS LIMITED (13039699, Liquidation), SPECTRUMX MEDICAL LIMITED "
                "(13042763), SPECTRUMX DIRECT LIMITED (13042692), SPECTRUMX HOLDINGS UK "
                "LTD (13745475), plus SPECTRUMX LIMITED (09589769) and SPECTRUMX UK "
                "LIMITED (10900106), both dissolved. Which of them holds Lot 2 cannot be "
                "settled from the notice. A shared name is not evidence: identity first, "
                "record after. Must not be confused with the Hub's existing BioSpectrum "
                "Ltd, Spectrum Medical Limited or Vision Pharmaceuticals Ltd T/A "
                "Spectrum records -- different companies." % UK_TODAY),
        "sources": ["https://find-and-update.company-information.service.gov.uk/"
                    "search/companies?q=SpectrumX"],
    },
    {
        "name": "J A Marketing limited",
        "lots": ["Lot 4"],
        "verdict": "excluded-identity-unsettled",
        "companyNumber": None,
        "companyStatus": None,
        "why": ("Both Companies House candidates on %s are DISSOLVED: J A MARKETING "
                "LIMITED 04313818 (Ground Floor Offices, Riverside Mills, Elland, West "
                "Yorkshire, dissolved 01/08/2025) and J A MARKETING LIMITED 17156425 "
                "(Lincoln, dissolved 22/09/2026 and incorporated in 2025, after the "
                "January 2023 award, so it cannot be the awardee). No product evidence "
                "exists for the name anywhere -- no company site, no NHS Supply Chain "
                "catalogue entry, no dm+d listing. There is nothing to write a record "
                "from, clinical or otherwise." % UK_TODAY),
        "sources": ["https://find-and-update.company-information.service.gov.uk/"
                    "search/companies?q=J+A+Marketing"],
    },
]


def load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def apply_to(doc, label):
    """Idempotently apply this run's changes to one supplier document.

    Returns a list of the changes made; an empty list means it was already done.
    """
    changed = []
    sups = doc.get("suppliers") or []
    by_name = {s.get("name"): s for s in sups if isinstance(s, dict)}

    # 1. Esteve: a new record of its own.
    rec = by_name.get(ESTEVE["name"])
    if rec is None:
        sups.append(json.loads(json.dumps(ESTEVE)))
        changed.append("added %s" % ESTEVE["name"])
    else:
        for key, want in ESTEVE.items():
            if rec.get(key) != want:
                rec[key] = json.loads(json.dumps(want))
                changed.append("%s: set %s" % (ESTEVE["name"], key))

    # 2. GOJO / Purell: alias, framework entry, number candidate, alert text.
    gojo = by_name.get("GOJO / Purell")
    if gojo is None:
        raise SystemExit("%s: no 'GOJO / Purell' record to extend -- stopping rather "
                         "than creating a second one." % label)

    aliases = list(gojo.get("aliases") or [])
    added_aliases = [a for a in GOJO_EXTRA_ALIASES if a not in aliases]
    if added_aliases:
        gojo["aliases"] = aliases + added_aliases
        changed.append("GOJO / Purell: +%d alias(es)" % len(added_aliases))

    fws = list(gojo.get("frameworks") or [])
    want_fw = framework_entry(GOJO_ALIAS, ["1", "3", "4"])
    existing = [i for i, f in enumerate(fws)
                if isinstance(f, dict) and f.get("name") == FW_LABEL]
    if not existing:
        fws.append(want_fw)
        gojo["frameworks"] = fws
        changed.append("GOJO / Purell: + hand hygiene award framework entry")
    elif fws[existing[0]] != want_fw:
        fws[existing[0]] = want_fw
        gojo["frameworks"] = fws
        changed.append("GOJO / Purell: refreshed hand hygiene award framework entry")

    if gojo.get("companyNumberCandidate") != GOJO_NUMBER_CANDIDATE:
        gojo["companyNumberCandidate"] = json.loads(json.dumps(GOJO_NUMBER_CANDIDATE))
        changed.append("GOJO / Purell: set companyNumberCandidate")

    # The page reads `alerts` from the index and the nightly rebuild regenerates
    # the index from the seed, so check_seed_index_alert_parity requires the same
    # text in both files. One addition, appended once.
    for al in gojo.get("alerts") or []:
        if not isinstance(al, dict):
            continue
        text = al.get("text") or ""
        if "IMPORTANT STATUS FLAG" in text and GOJO_ALERT_ADDITION.strip() not in text:
            al["text"] = text.rstrip() + GOJO_ALERT_ADDITION
            changed.append("GOJO / Purell: alert now carries the award record")

    return changed


def write_adjudication():
    doc = {
        "_what": ("Hand Hygiene and Associated Products and Services -- every lot-source "
                  "supplier name on the framework's Find a Tender award notice that "
                  "reaches no NHS Supply Chain brief row, and what was decided about it. "
                  "Written by scripts/_add_hand_hygiene_clinical_records_1117.py so the "
                  "'out' decisions are recorded once and not re-worked."),
        "framework": "Hand Hygiene and Associated Products and Services",
        "briefUrl": BRIEF_URL,
        "noticeUrl": NOTICE_URL,
        "noticeOcid": "ocds-h6vhtk-02ad97",
        "noticeAwardRelease": "2023-01-06",
        "noticeSupplierCount": 33,
        "briefSupplierCount": 21,
        "decidedOn": TODAY,
        "ruling": ("Lou, 17/11/2026 (Needs-Lou N886): \"Hand hygiene yes, the others "
                   "no\", refined to \"depends on the product as hand hygiene could be "
                   "classed as clinical\". Catering, facilities/electrical, furniture, "
                   "office-supply and food names stay out entirely."),
        "included": [
            {"name": "Esteve Pharmaceuticals Ltd", "lots": ["Lot 4"],
             "verdict": "included-clinical", "record": "Esteve Pharmaceuticals Ltd",
             "why": ("Licensed leave-on emollient (Aquamax) indicated for eczema and "
                     "psoriasis, in the NHS dm+d, from a prescription pharmaceutical "
                     "company. Clinical skin care, not a washroom consumable.")},
            {"name": "GOJO Industries Europe Ltd", "lots": ["Lot 1", "Lot 3", "Lot 4"],
             "verdict": "included-clinical-existing-record", "record": "GOJO / Purell",
             "why": ("PURELL Advanced is certified to EN 12791, the surgical hand-rub "
                     "standard, and the Hub already holds this company as GOJO / Purell. "
                     "The award spelling was added there as an alias; no second record "
                     "was created. The UK entity is in liquidation and is not on NHS "
                     "Supply Chain's current supplier list -- both stated on the "
                     "record's own alert.")},
        ],
        "excluded": EXCLUDED,
        "residual": ("With these two resolved, six of the framework's eight unresolved "
                     "lot-source names stay unresolved on purpose. Separately: NHS Supply "
                     "Chain's brief lists 21 suppliers where the award notice named 33, "
                     "and the brief's stated count matches its printed list, so the "
                     "difference is real and not a short capture. That is why these names "
                     "have no brief row to attach a lot to, and it belongs to the "
                     "'48 names not on this brief' job, not to this one."),
    }
    before = None
    if os.path.exists(ADJ):
        try:
            before = load(ADJ)
        except ValueError:
            before = None
    if before == doc:
        print("state/hand-hygiene-lot-source-adjudication.json already current")
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
