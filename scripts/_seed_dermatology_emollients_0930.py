#!/usr/bin/env python3
"""One-off seeder, 30/09/2026: dermatology emollient competitors (Ego demo follow-up).

WHY
---
Lou demoed the Hub to Ego Pharmaceuticals UK (QV emollients) on 30/09/2026. The
customer named Aspire Pharma (Epimax) and "Fontys Healthcare" (Fontus Health Ltd,
AproDerm) as her main competitors. In the demo:

  * Aspire Pharma's Company Report said nothing about its accounts: the
    Companies House match was `probable` (name search), so no figure, officer or
    growth series was ever read, although full accounts to 31/12/2025 were filed
    on 29/08/2026.
  * Fontus Health had no Hub record at all, so "Fontus" and "Fontys" found
    nothing.
  * Compare Your Product had no emollient rows: the dermatology suppliers carried
    one combined product string each ("QV Cream / QV Gentle Wash / ...") that no
    product type could be read from.

Every fact written here was read on 30/09/2026 from the named primary source:

  Companies House (overview, officers, PSC, filing history, and the iXBRL
    accounts documents) for ASPIRE PHARMA LIMITED 06828501 and FONTUS HEALTH LTD
    08072503; FONTUS GROUP HOLDINGS LIMITED 13574786 (PSC); advanced search for
    "fontus", "fontys" and "alliance pharmaceuticals".
  Company websites: aspirepharma.com footer and portfolio page; fontushealth.com
    Terms and Conditions; aproderm.com range page and footer; qvskincare.co.uk
    and egopharm.com/gb "Our Brands"; hydromol.co.uk footer.
  NHSBSA Drug Tariff Part IX, September 2026 (the Hub's copy,
    data/drug-tariff-part-ix.json, dataAsOf 2026-09-30), BNF section 21.22.
  Find a Tender notice 2026/S 000-082784 (NHS National Generic Pharmaceuticals
    Wave 16a, published 01/09/2026).
  GOV.UK drug-device-alerts: Class 3 recall EL (21)A/26; FSN weekly lists for
    15-19/11/2021, 30/01-03/02/2023, 10-14/06/2024; MHRA Safety Roundup
    January 2026.

Re-runnable: every write SETS a field, so running it twice changes nothing.
A peer landing mid-work means: fresh ./begin.sh, copy this file in, run again
(msh-compare-data-peer-landed-redo-not-rebase).

Run: python3 scripts/_seed_dermatology_emollients_0930.py
"""
import json
import sys

sys.path.insert(0, "scripts")
from seed_format import write_like, describe

SEED = "data/supplier-seed.json"
TARIFF = "data/drug-tariff-part-ix.json"
TODAY = "2026-09-30"
CH = "https://find-and-update.company-information.service.gov.uk/company/"
DT_PAGE = "https://www.nhsbsa.nhs.uk/pharmacies-gp-practices-and-appliance-contractors/drug-tariff/drug-tariff-part-ix"
FTS = "https://www.find-tender.service.gov.uk/Notice/082784-2026"
DERM = "Dermatology / skin"

seed = json.load(open(SEED))
by_name = {s["name"]: s for s in seed["suppliers"]}

# ---------------------------------------------------------------------------
# Drug Tariff: every product name is the tariff's own AMP name, read from the
# file, never typed by hand, so the product and its dossier cannot drift apart.
# ---------------------------------------------------------------------------
tariff = json.load(open(TARIFF))
assert tariff["effectiveMonth"] == "2026-09", tariff["effectiveMonth"]
ix = {n: i for i, n in enumerate(tariff["schema"])}


def tariff_names(supplier, bnf_prefixes=("2122",), parts=("IXA",)):
    out = []
    for r in tariff["rows"]:
        if r[ix["supplier"]] != supplier or r[ix["part"]] not in parts:
            continue
        if bnf_prefixes and not str(r[ix["bnf"]]).startswith(bnf_prefixes):
            continue
        if r[ix["amp"]] not in out:
            out.append(r[ix["amp"]])
    assert out, "no tariff lines for %s" % supplier
    return out


def price(supplier, amp, qty):
    for r in tariff["rows"]:
        if r[ix["supplier"]] == supplier and r[ix["amp"]] == amp and r[ix["qty"]] == qty:
            return "£%.2f" % (int(r[ix["price"]]) / 100.0)
    raise SystemExit("no tariff price for %s / %s / %s" % (supplier, amp, qty))


def merge_products(rec, names, drop=()):
    kept = [p for p in (rec.get("products") or []) if p not in drop]
    for n in names:
        if n not in kept:
            kept.append(n)
    rec["products"] = kept


def add_speciality(rec, spec):
    specs = rec.get("specialities") or []
    if spec not in specs:
        specs.append(spec)
    rec["specialities"] = specs


# Line counts in BNF 21.22, used in the prose below, recomputed not typed.
def lines_in_2122(supplier):
    return sum(1 for r in tariff["rows"]
               if r[ix["supplier"]] == supplier and str(r[ix["bnf"]]).startswith("2122"))


def lines_part_ix(supplier):
    return sum(1 for r in tariff["rows"] if r[ix["supplier"]] == supplier)


N2122 = sum(1 for r in tariff["rows"] if str(r[ix["bnf"]]).startswith("2122"))
S2122 = len({r[ix["supplier"]] for r in tariff["rows"] if str(r[ix["bnf"]]).startswith("2122")})
ASP, FON = "Aspire Pharma Ltd", "Fontus Health Ltd"
assert (N2122, S2122) == (176, 35), (N2122, S2122)
assert lines_in_2122(ASP) == 15 and lines_part_ix(ASP) == 31
assert lines_in_2122(FON) == 10 and lines_part_ix(FON) == 13

# ---------------------------------------------------------------------------
# 1. ASPIRE PHARMA
# ---------------------------------------------------------------------------
asp = by_name["Aspire Pharma"]
ASP_ACCOUNTS = CH + "06828501/filing-history/MzU0MTU5ODI0NWFkaXF6a2N4/document?format=pdf&download=0"
asp_products = tariff_names(ASP) + [
    "Epimax eyelid ointment preservative free",
    "SilDerm Dual Action scar gel",
    "Carmize 0.5% eye drops",
    "Carmize 1% eye drops",
    "eyGuide eye drop dispenser",
]
merge_products(asp, asp_products)
asp["aliases"] = list(dict.fromkeys((asp.get("aliases") or []) + [
    "Aspire Pharma", "Aspire Pharma Limited", "Aspire Pharma Ltd", "ASPIRE PHARMA LIMITED",
    "epimax"]))
# Aspire's `note` and `companyNumberProof` are deliberately NOT written here: a
# parallel session ("Company info not pulling through Aspire", 30/09/2026) owns
# Aspire's Companies House identity (company-financials.json and the seed proof).
# This script adds products, aliases, the generics framework and the deep dive only.
asp["_specialitiesEvidence"] = (
    "aspirepharma.com home page, read 30/09/2026, lists its core promotional therapy areas: "
    "Anti-Infectives, Cardiology, Dermatology, Gynaecology, Oncology, Metabolism & "
    "Endocrinology, Ophthalmology, Urology, Central Nervous System, Respiratory. The five "
    "tagged here all appear in that list. Dermatology is also evidenced product by product: "
    "15 Epimax lines in Drug Tariff Part IX, BNF 21.22, September 2026.")
fw = [f for f in (asp.get("frameworks") or []) if not (isinstance(f, dict) and f.get("reference") == "2026/S 000-082784")]
fw.append({
    "name": "NHS England — NHS National Generic Pharmaceuticals, Wave 16a",
    "dates": "Lot 1: 1 February 2027 to 31 May 2030 (estimated); Lot 2: 1 February 2027 to 31 January 2029 (estimated)",
    "note": ("Named on the contract award notice as \"ASPIRE PHARMA LIMITED\" on Lot 1 (Oral plus "
             "non-parenteral products, 20 suppliers) and Lot 2 (Hospital only products, DLN & DNW "
             "regions, 101 suppliers); not on Lot 3. Award decision 27 August 2026. A medicines "
             "framework run by NHS England, not an NHS Supply Chain device framework."),
    "reference": "2026/S 000-082784",
    "url": FTS,
    "source": "Find a Tender contract award notice",
    "capturedOn": TODAY,
})
asp["frameworks"] = fw

asp["deepDive"] = {
    "checked": TODAY,
    "origin": ("Built 30/09/2026 by reading Companies House directly for 06828501 (overview, "
               "officers, persons-with-significant-control and filing-history pages) and the "
               "full accounts of Aspire Pharma Limited for the years to 31 December 2025, 2024 "
               "and 2023 (iXBRL documents, filed 29/08/2026, 04/07/2025 and 25/07/2024), plus the "
               "company's own site (aspirepharma.com footer and portfolio page). Drug Tariff "
               "lines and prices are read from the Hub's own copy of NHSBSA Drug Tariff Part IX, "
               "September 2026. The framework line is read from Find a Tender notice "
               "2026/S 000-082784. MHRA items are read from GOV.UK drug-device-alerts."),
    "domain": "aspirepharma.com",
    "tagline": ("UK developer, licenser and distributor of branded and generic medicines and "
                "medical devices, including the Epimax emollient range · majority-owned by an "
                "affiliate of H.I.G. Capital since 2021 · NHS routes: Drug Tariff Part IX and "
                "NHS England's national generics framework"),
    "links": [
        {"label": "Website", "url": "https://aspirepharma.com/"},
        {"label": "Companies House (06828501)", "url": CH + "06828501"},
        {"label": "FY2025 accounts (filed 29/08/2026)", "url": ASP_ACCOUNTS},
        {"label": "NHSBSA Drug Tariff Part IX", "url": DT_PAGE},
        {"label": "Find a Tender: National Generics Wave 16a", "url": FTS},
    ],
    "lede": ("Aspire Pharma Limited's audited turnover rose 2.8% to £118.2m in the year to 31 "
             "December 2025 (2024: £115.0m), 98.6% of it in the UK. Profit before tax was £24.2m "
             "(2024: £24.9m) and the average headcount rose to 114 (2024: 100). The company has "
             "grown by acquisition under H.I.G. Capital's ownership: Morningside in 2022, Cenote "
             "Pharma and Canute Pharma's assets in 2024, Charlwood Pharma and Saint Germain Pharma "
             "in 2025, and Caragen (Ireland) in February 2026. In emollients it competes on "
             "price: its Epimax range holds 15 of the 176 BNF 21.22 lines on the September 2026 "
             "Drug Tariff, second only to Thornton & Ross, and Epimax original cream 500g "
             "reimburses at £2.74 against £6.75 for QV cream 500g. Taken together, the filings and "
             "range describe a private-equity-backed, acquisitive UK generics and devices house whose "
             "emollient range competes on price rather than brand."),
    "stats": [
        {"v": "£118.2m", "l": "Turnover, year to 31 December 2025",
         "n": "Statement of comprehensive income, Aspire Pharma Limited full accounts filed 29/08/2026: £118,167k (2024: £114,959k). UK £116,505k, rest of the world £1,662k (note 3)."},
        {"v": "£24.2m", "l": "Profit before tax, year to 31 December 2025",
         "n": "Same statement: £24,221k (2024: £24,928k). Operating profit £24,085k (2024: £24,691k); profit after tax £21,824k (2024: £23,092k). No dividend paid in 2025 (2024: £5,800k)."},
        {"v": "114", "l": "Average employees including directors, 2025 (2024: 100)",
         "n": "Employees note, same filing: administrative 38, regulatory 37, sales and distribution 39. The directors are paid through another group entity."},
        {"v": "15 lines", "l": "Epimax emollients on Drug Tariff Part IX, BNF 21.22, September 2026",
         "n": "Of 176 emollient lines from 35 suppliers. Epimax original cream 100g %s, 500g %s; Epimax ointment 500g %s; Epimax isomol gel 500g %s. 31 Part IX lines in all, including Carmize and AquaVista eye drops and SilDerm scar gel." % (
             price(ASP, "Epimax original cream", "100"), price(ASP, "Epimax original cream", "500"),
             price(ASP, "Epimax ointment", "500"), price(ASP, "Epimax isomol gel", "500"))},
    ],
    "ownership": [
        "Companies House PSC register: APHL 2 Limited (11534571) holds 75% or more of the shares and voting rights and the right to appoint or remove directors, notified 19 September 2019.",
        "FY2025 accounts note 24: the company is wholly owned by APHL 2 Limited, the smallest group that consolidates it; the ultimate controlling party is considered to be H.I.G Europe Middle Market LBO Fund L.P. (Cayman). The strategic report dates H.I.G.'s majority ownership of the Aspire group to 3 September 2021.",
    ],
    "people": [
        {"name": "Gary David Buckley", "role": "Director and company secretary",
         "note": "Companies House: both roles appointed 15 June 2020. Signed the FY2025 strategic report and balance sheet on 26/06/2026."},
        {"name": "Jonathan Charles May", "role": "Director",
         "note": "Companies House: appointed 15 June 2020."},
        {"name": "Richard Michael Condon", "role": "Director",
         "note": "Companies House: appointed 28 April 2023."},
    ],
    "marketPosition": [
        "Emollients reach the NHS through community prescribing: the Epimax range sits on Drug Tariff Part IXA, BNF 21.22 (emollient devices). No NHS Supply Chain framework covers emollients.",
        "Drug Tariff Part IX, September 2026, BNF 21.22: 176 lines from 35 suppliers. Most lines: Thornton & Ross 34 (Cetraben, Zerobase and the Zero range), Aspire Pharma 15 (Epimax), Ennogen Healthcare International 13, Alliance Pharmaceuticals 12 (Hydromol), Fontus Health 10 (AproDerm), TriOn Pharma 10, Molnlycke 9 (Epaderm), Ego Pharmaceuticals 5 (QV). Line counts measure range breadth on the tariff, not market share.",
        "NHS England's National Generic Pharmaceuticals framework, Wave 16a (Find a Tender 2026/S 000-082784, 01/09/2026): Aspire Pharma Limited is named on Lot 1 and Lot 2.",
        "MHRA: the January 2026 MHRA Safety Roundup repeats a Drug Safety Update warning not to prescribe or advise Epimax Ointment or Epimax Paraffin-Free Ointment for use on the face, after reports of ocular surface toxicity and chemical injury. Aspire field safety notices for Epimax are listed by MHRA in November 2021 (Epimax Original Cream 500g), January 2023 and June 2024 (Ointment and Paraffin-free Ointment). A Class 3 medicines recall of Bimatoprost Aspire eye drops was issued in October 2021 (EL (21)A/26).",
    ],
    "place": "Registered office (Companies House and FY2025 accounts): 102 High Street, Godalming, Surrey, GU7 1DS. Incorporated 24 February 2009, active, SIC 46460 (wholesale of pharmaceutical goods). Auditor: TC Group.",
    "interview": ("Worth raising: (1) Epimax reimburses at well under half QV's 500g price, so ask how "
                  "the team defends formulary places won on price when a cheaper line appears; (2) "
                  "turnover growth slowed to 2.8% in 2025 after 21% in 2023 and 16% in 2024, while "
                  "the group kept buying businesses, so ask where the next growth is meant to come "
                  "from; (3) the MHRA's repeated warning about Epimax ointments near the eyes, so "
                  "ask how the field team handles it with prescribers."),
    "sources": ("Primary sources read this session: " + CH + "06828501; " + CH + "06828501/officers; "
                + CH + "06828501/persons-with-significant-control; " + CH + "06828501/filing-history; "
                + ASP_ACCOUNTS + "; https://aspirepharma.com/; https://aspirepharma.com/product-innovation/portfolio/; "
                + DT_PAGE + " (September 2026); " + FTS + "; "
                "https://www.gov.uk/drug-device-alerts/mhra-safety-roundup-january-2026; "
                "https://www.gov.uk/drug-device-alerts/class-3-medicines-recall-bimatoprost-aspire-0-dot-3mg-slash-ml-eye-drops-solution-in-single-dose-container-aspire-pharma-limited-el-21-a-slash-26."),
    "growth": {
        "prose": [
            "Turnover rose from £81.7m (2022) to £99.1m (2023), £115.0m (2024) and £118.2m (2025): growth of 21.3%, 16.0% and 2.8% a year.",
            "Average headcount rose from 71 (2022) to 79, 100 and 114 over the same years, the largest rise in sales and distribution staff (23 to 39).",
        ],
        "series": {
            "label": "Turnover",
            "currency": "£",
            "unit": "m",
            "axis": {"from": 2022, "to": 2025},
            "axisNote": "Four years from three filed accounts (each carries the prior year as its comparative).",
            "points": [
                {"y": "FY2022", "v": 81.73, "src": "Comparative in the FY2023 accounts, filed 25/07/2024, Companies House 06828501"},
                {"y": "FY2023", "v": 99.11, "src": "Full accounts to 31 December 2023, filed 25/07/2024"},
                {"y": "FY2024", "v": 114.96, "src": "Full accounts to 31 December 2024, filed 04/07/2025"},
                {"y": "FY2025", "v": 118.17, "src": "Full accounts to 31 December 2025, filed 29/08/2026"},
            ],
            "source": "Aspire Pharma Limited, Companies House 06828501",
        },
    },
}

# ---------------------------------------------------------------------------
# 2. FONTUS HEALTH (new record)
# ---------------------------------------------------------------------------
FON_NAME = "Fontus Health"
FON_ACCOUNTS = CH + "08072503/filing-history/MzQ5MTA5NDA3MmFkaXF6a2N4/document?format=pdf&download=0"
fon = by_name.get(FON_NAME)
if fon is None:
    fon = {"name": FON_NAME}
    seed["suppliers"].append(fon)
    by_name[FON_NAME] = fon
fon.update({
    "aliases": [FON_NAME, "Fontus Health Ltd", "Fontus Health Limited", "FONTUS HEALTH LTD",
                "aproderm", "Fontys Health", "Fontys Healthcare"],
    "_aliasesEvidence": (
        "Registered name FONTUS HEALTH LTD (Companies House 08072503, read 30/09/2026); the "
        "company's own Terms and Conditions call it both \"Fontus Health Limited\" and \"Fontus "
        "Health Ltd\"; NHSBSA Drug Tariff Part IX lists it as \"Fontus Health Ltd\". \"aproderm\" "
        "is its emollient brand (aproderm.com footer: \"No: 08072503 | © Fontus Health Ltd\"). "
        "\"Fontys Health\"/\"Fontys Healthcare\" are the spelling a customer used for this company "
        "in a Hub demo on 30/09/2026; a Companies House advanced search for \"fontys\" on "
        "30/09/2026 returned no company at all, so the misspelling names nobody else. Sister "
        "companies at the same address (FONTUS PHARMA LTD 16580619, FONTUS INVESTMENTS LTD "
        "16465797, FONTUS GROUP HOLDINGS LIMITED 13574786) are separate legal entities and are "
        "NOT aliased."),
    "specialities": [DERM],
    "frameworks": [{
        "name": "NHS England — NHS National Generic Pharmaceuticals, Wave 16a",
        "dates": "Lot 2: 1 February 2027 to 31 January 2029 (estimated)",
        "note": ("Named on the contract award notice as \"FONTUS HEALTH LTD\" (PPON PVQG-3746-DQLM, "
                 "SME) on Lot 2 (Hospital only products, DLN & DNW regions, 101 suppliers); not on "
                 "Lot 1 or Lot 3. Award decision 27 August 2026. A medicines framework run by NHS "
                 "England, not an NHS Supply Chain device framework."),
        "reference": "2026/S 000-082784",
        "url": FTS,
        "source": "Find a Tender contract award notice",
        "capturedOn": TODAY,
    }],
    "alerts": [],
    "news": [],
    "links": [
        {"label": "Website", "url": "https://fontushealth.com/"},
        {"label": "AproDerm", "url": "https://aproderm.com/aproderm-range/"},
    ],
    "awards": [],
    "curated": True,
    "note": (
        "UK pharmaceutical and medical device manufacturer, Walsall (FY2025 accounts). Its NHS "
        "emollient range is AproDerm. Added 30/09/2026: named by a customer as a key emollient "
        "competitor. Identity confirmed from the company's own Terms and Conditions against "
        "Companies House 08072503."),
    "verified": TODAY,
    "source": ("Companies House 08072503; fontushealth.com Terms and Conditions; aproderm.com; NHSBSA "
               "Drug Tariff Part IX September 2026; Find a Tender 2026/S 000-082784"),
    "companyNumberCandidate": {
        "number": "08072503",
        "registeredName": "FONTUS HEALTH LTD",
        "companyStatus": "active",
        "incorporated": "2012-05-17",
        "confidence": "confirmed",
        "matchedOn": ("Found by Companies House advanced search on 2026-09-30. CONFIRMED same day: "
                      "company number published on the company's own website, agreeing with the "
                      "Companies House record -- https://fontushealth.com/terms-and-conditions/, "
                      "read 2026-09-30."),
        "confirmedOn": TODAY,
        "confirmedRoute": "website-registration",
    },
    "companyNumberProof": {
        "number": "08072503",
        "route": "website-registration",
        "url": "https://fontushealth.com/terms-and-conditions/",
        "evidence": ("Fontus Health Ltd is registered under company No. 08072503 and our registered "
                     "office address is Fontus Health Ltd, 60 Lichfield Street, Walsall, WS4 2BX."),
        "checkedOn": TODAY,
    },
})
merge_products(fon, tariff_names(FON) + ["AproDerm barrier cream", "AproDerm protective barrier spray"])
fon["deepDive"] = {
    "checked": TODAY,
    "origin": ("Built 30/09/2026 by reading Companies House directly for 08072503 (overview, officers, "
               "persons-with-significant-control and filing-history pages) and 13574786 (the parent's "
               "PSC register), and the full accounts of Fontus Health Ltd for the year to 31 March 2025 "
               "(iXBRL, filed 26/11/2025), plus the company's own sites (fontushealth.com, aproderm.com). "
               "Drug Tariff lines and prices are read from the Hub's own copy of NHSBSA Drug Tariff Part "
               "IX, September 2026. The framework line is read from Find a Tender notice 2026/S 000-082784."),
    "domain": "fontushealth.com",
    "tagline": ("UK pharmaceutical and medical device manufacturer, Walsall, behind the AproDerm emollient "
                "range · owned by Fontus Group Holdings Limited · NHS routes: Drug Tariff Part IX and NHS "
                "England's national generics framework"),
    "links": [
        {"label": "Website", "url": "https://fontushealth.com/"},
        {"label": "AproDerm range", "url": "https://aproderm.com/aproderm-range/"},
        {"label": "Companies House (08072503)", "url": CH + "08072503"},
        {"label": "FY2025 accounts (filed 26/11/2025)", "url": FON_ACCOUNTS},
        {"label": "NHSBSA Drug Tariff Part IX", "url": DT_PAGE},
        {"label": "Find a Tender: National Generics Wave 16a", "url": FTS},
    ],
    "lede": ("Fontus Health Ltd's audited turnover rose 30.5%% to £13.4m in the year to 31 March 2025 "
             "(2024: £10.3m), all from pharmaceuticals, and profit before tax tripled to £2.62m (2024: "
             "£0.85m). It averaged 20 staff including directors and spent £1.02m on research and "
             "development. It is not a new company: it was incorporated in May 2012 and its accounts "
             "say it has traded since then, though its holding company was formed in 2021 and the "
             "FY2025 accounts are the first it filed as full rather than small-company accounts. In "
             "emollients it sells AproDerm: 10 lines in BNF 21.22 on the September 2026 Drug Tariff, "
             "AproDerm emollient cream 500g at %s against %s for QV cream 500g. Taken together, the filings and "
             "range describe a small, fast-growing, owner-managed manufacturer competing on price."
             % (price(FON, "AproDerm emollient cream", "500"), price("Ego Pharmaceuticals", "QV cream", "500"))),
    "stats": [
        {"v": "£13,445,494", "l": "Turnover, year to 31 March 2025",
         "n": "Profit and loss account, Fontus Health Ltd full accounts filed 26/11/2025 (2024: £10,302,190). All pharmaceuticals (note 3)."},
        {"v": "£2,619,784", "l": "Profit before tax, year to 31 March 2025",
         "n": "Same statement (2024: £852,000). Profit after tax £1,979,631 (2024: £626,938). No dividend paid."},
        {"v": "20", "l": "Average employees including directors, 2025 (2024: 17)",
         "n": "Employees note, same filing. Research and development costs £1,021,849 (2024: £1,008,710), note 4."},
        {"v": "13 lines", "l": "On Drug Tariff Part IX, September 2026",
         "n": "10 AproDerm emollient lines in BNF 21.22 (e.g. emollient cream 500g %s, ointment 500g %s, gel 500g %s, Colloidal Oat cream 500ml %s) and 3 AproDerm barrier lines in Part IXC (ostomy skin protectives)." % (
             price(FON, "AproDerm emollient cream", "500"), price(FON, "AproDerm ointment", "500"),
             price(FON, "AproDerm gel", "500"), price(FON, "AproDerm Colloidal Oat cream", "500"))},
    ],
    "ownership": [
        "Companies House PSC register: Fontus Group Holdings Limited (13574786) holds 75% or more of the shares and voting rights and the right to appoint or remove directors, notified 14 September 2021.",
        "The PSC register of Fontus Group Holdings Limited (incorporated 19 August 2021) names Navdeep Kaur Birdi as holding 75% or more of its shares, notified 19 August 2021. She is also a director of Fontus Health Ltd.",
    ],
    "people": [
        {"name": "Daljit Singh Birdi", "role": "Director",
         "note": "Companies House: appointed 15 July 2019. Signed the FY2025 strategic report and balance sheet on 26/11/2025."},
        {"name": "Navdeep Birdi", "role": "Director",
         "note": "Companies House: appointed 4 February 2015."},
    ],
    "marketPosition": [
        "Emollients reach the NHS through community prescribing: AproDerm sits on Drug Tariff Part IXA, BNF 21.22 (emollient devices), 10 of the section's 176 lines. No NHS Supply Chain framework covers emollients.",
        "The AproDerm site (aproderm.com, read 30/09/2026) lists Colloidal Oat Cream, Emollient Cream, Gel, Ointment and Barrier Cream, and sends consumers to an Amazon storefront; the tariff also lists AproDerm Plus cream and an emollient starter pack.",
        "NHS England's National Generic Pharmaceuticals framework, Wave 16a (Find a Tender 2026/S 000-082784, 01/09/2026): Fontus Health Ltd is named on Lot 2, as an SME.",
        "MHRA: a search of GOV.UK drug and device alerts on 30/09/2026 returned no alert naming Fontus Health or AproDerm.",
    ],
    "place": "Registered office (Companies House and FY2025 accounts): 60 Lichfield Street, Walsall, WS4 2BX. Incorporated 17 May 2012, active, SIC 21100 (manufacture of basic pharmaceutical products). Auditor: BK Plus Audit Limited.",
    "interview": ("Worth raising: (1) turnover grew 30% in a year on a team of about 20, so ask what drove it "
                  "and how the field team is structured; (2) AproDerm is priced against the large emollient "
                  "brands, so ask how it wins formulary places; (3) the business spends about £1m a year on "
                  "R&D, so ask what is in development."),
    "sources": ("Primary sources read this session: " + CH + "08072503; " + CH + "08072503/officers; "
                + CH + "08072503/persons-with-significant-control; " + CH + "08072503/filing-history; "
                + FON_ACCOUNTS + "; " + CH + "13574786/persons-with-significant-control; "
                "https://fontushealth.com/terms-and-conditions/; https://aproderm.com/aproderm-range/; "
                + DT_PAGE + " (September 2026); " + FTS + "."),
    "growth": {
        "prose": [
            "Turnover rose from £10.30m (year to 31 March 2024) to £13.45m (year to 31 March 2025), up 30.5%; profit before tax rose from £0.85m to £2.62m.",
        ],
        "series": {
            "label": "Turnover",
            "currency": "£",
            "unit": "m",
            "axis": {"from": 2024, "to": 2025},
            "axisNote": "Two years from the FY2025 filed accounts (FY2024 is the comparative). Earlier years were filed as small-company accounts and were not read in this pass.",
            "points": [
                {"y": "FY2024", "v": 10.30, "src": "Comparative in the FY2025 filed accounts, Companies House 08072503"},
                {"y": "FY2025", "v": 13.45, "src": "Full accounts to 31 March 2025, filed 26/11/2025"},
            ],
            "pending": "FY2023 and earlier were small-company accounts; not read in this pass.",
            "source": "Fontus Health Ltd, Companies House 08072503",
        },
    },
}

# ---------------------------------------------------------------------------
# 3. ALLIANCE PHARMACEUTICALS (Hydromol) - new record, identity NOT confirmed
# ---------------------------------------------------------------------------
ALL_NAME = "Alliance Pharmaceuticals"
alliance = by_name.get(ALL_NAME)
if alliance is None:
    alliance = {"name": ALL_NAME}
    seed["suppliers"].append(alliance)
    by_name[ALL_NAME] = alliance
alliance.update({
    "aliases": [ALL_NAME, "Alliance Pharmaceuticals Ltd", "Alliance Pharmaceuticals Limited", "hydromol"],
    "specialities": [DERM],
    "frameworks": [],
    "alerts": [],
    "news": [],
    "links": [{"label": "Hydromol", "url": "https://hydromol.co.uk/"},
              {"label": "Website", "url": "https://www.alliancepharmaceuticals.com/"}],
    "awards": [],
    "curated": True,
    "note": (
        "Owner of the Hydromol emollient range: NHSBSA Drug Tariff Part IX (September 2026) lists "
        "12 Hydromol lines in BNF 21.22 under \"Alliance Pharmaceuticals Ltd\", and hydromol.co.uk "
        "(read 30/09/2026) carries \"© Alliance Pharmaceuticals Limited 2026\". Added 30/09/2026 so "
        "Hydromol can be compared on the Hub. The company's site states that it sold its "
        "pharmaceutical division to two UK companies on 7 January 2026; Hydromol was still listed "
        "under Alliance on the September 2026 tariff. Company number NOT verified: its site does "
        "not publish one. Companies House holds exactly one company of this name, ALLIANCE "
        "PHARMACEUTICALS LIMITED (03250064, active, Avonbridge House, Bath Road, Chippenham, the "
        "address in the site footer), which is a candidate until the number is seen on a "
        "company-published page."),
    "verified": TODAY,
})
merge_products(alliance, tariff_names("Alliance Pharmaceuticals Ltd"))

# ---------------------------------------------------------------------------
# 4. Existing dermatology suppliers: tariff product rows, and two corrections
# ---------------------------------------------------------------------------
ego = by_name["Ego Pharmaceuticals UK"]
# Correction: egopharm.com/gb "Our Brands", read 30/09/2026: "QV Skincare is currently
# the only brand available in the UK". Sunsense was listed here and is not sold in the UK.
# QV Bath Oil and QV Skin Lotion are still sold at retail (qvskincare.co.uk, read
# 30/09/2026) but are DISCONTINUED for NHS supply: dm+d AMP 40786 (bath oil, left
# Part IX June 2024) and AMP 40771 (5% skin lotion, last in Part IX August 2025),
# read 30/09/2026 (Call-Briefs/Ego-QV-Discontinued-Lines-Formulary-Check-2026-09-30.md).
# They are kept, labelled, never presented as current NHS products. The current
# NHS lines are the three tariff names above.
QV_OFF_NHS = " (retail only: discontinued for NHS supply, dm+d, read 30/09/2026)"
merge_products(ego, tariff_names("Ego Pharmaceuticals") + [
    "QV Bath Oil" + QV_OFF_NHS, "QV Skin Lotion" + QV_OFF_NHS,
    "QV Baby Moisturising Cream (retail only: not on Drug Tariff Part IX, September 2026)"],
    drop=("QV Cream / QV Gentle Wash / QV Intensive Ointment (emollients, dry skin & eczema)",
          "Sunsense sunscreens", "QV Bath Oil", "QV Skin Lotion", "QV Baby Moisturising Cream"))
dd = ego.get("deepDive") or {}
if "Sunsense" in dd.get("tagline", ""):
    dd["tagline"] = dd["tagline"].replace("(QV emollients, Sunsense)", "(QV Skincare, its only UK brand)")

tr = by_name["Thornton & Ross Ltd"]
# Correction: Hydromol is Alliance Pharmaceuticals' brand (tariff supplier column and
# hydromol.co.uk footer), not Thornton & Ross's. "Zeroderma"/"Zeromed" are not tariff names;
# the tariff's own Zero-range names replace the combined string.
merge_products(tr, tariff_names("Thornton & Ross Ltd"),
               drop=("Hydromol", "Cetraben (emollient range)",
                     "Zeroderma / Zerobase / Zeromed (emollients)"))
tr["aliases"] = [a for a in tr.get("aliases", []) if a.lower() != "hydromol"]

dermal = by_name["Dermal Laboratories Ltd"]
merge_products(dermal, tariff_names("Dermal Laboratories Ltd"))

mol = by_name["Mölnlycke"]
merge_products(mol, tariff_names("Molnlycke Health Care Ltd"))
add_speciality(mol, DERM)

trion = by_name["Trion Pharma Limited"]
merge_products(trion, tariff_names("TriOn Pharma Ltd"))
add_speciality(trion, DERM)

fmt, round_trips = write_like(SEED, seed)
print(describe(SEED, fmt, round_trips))
for n in ("Aspire Pharma", FON_NAME, ALL_NAME, "Ego Pharmaceuticals UK", "Thornton & Ross Ltd",
          "Dermal Laboratories Ltd", "Mölnlycke", "Trion Pharma Limited"):
    print("%-26s %2d products  %s" % (n, len(by_name[n]["products"]), by_name[n]["specialities"]))
