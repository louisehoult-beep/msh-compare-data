#!/usr/bin/env python3
"""One-off, 20/10/2026 (second batch): digital health company intel, round two.

Follows scripts/_seed_digital_companies_1020.py and reuses its record shape and
editing code. Every number below has the same two-part proof as that batch
(route 2, `companyNumberProof`):
  1. the number printed on the company's OWN site, quoted as read 20/10/2026;
  2. the Companies House record for that number read the same day (Companies House
     API): registered name matches, status active, registered office consistent with
     the site where the site prints one.
No number came from a name search alone.

WHAT IT DOES
  * SEEDS 10 clinically relevant digital health suppliers that NHS buyers name on
    software award notices in data/digital-lane.json and that had no Hub record.
    (The 343 general IT firms on Technology Services 4 and the generic IT, finance,
    estates and licence resellers on the lane are deliberately NOT seeded.)
  * PROVES Magentus Software Limited 08746973 (existing record, was probable).
  * NOTES on Lenus Health that the matched Companies House company is dissolved and
    which active company shares the site's address (operator link NOT verified).
Idempotent. Mirrors into supplier-index.json like the first batch.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _seed_digital_companies_1020 as base  # noqa: E402
from seed_format import write_like, describe  # noqa: E402

proof = base.proof
new = base.new
DIG_IT, DIG_AI = base.DIG_IT, base.DIG_AI

base.NEW = [
    new("C the Signs", ["C the Signs", "C The Signs Limited", "C The Signs Ltd"], DIG_AI,
        "https://cthesigns.co.uk/",
        "Named on NHS award notice 'C The Signs Earlier Cancer Detection Platform' (Somerset NHS Foundation Trust).",
        proof_=proof("10683539", "https://cthesigns.co.uk/terms-of-use",
                     "The Site is operated by C The Signs Limited ( We , Us or Our ). We are a limited "
                     "company registered in England and Wales under company number 10683539 and have "
                     "Our registered office at Gridiron Building, 1 Pancras Square, London")),
    new("Rx-Info", ["Rx-Info", "Rx-Info Limited", "RX-INFO LIMITED", "Rx-info Ltd"], DIG_IT,
        "https://www.rx-info.co.uk/",
        "Named on Cambridge University Hospitals award notices ('Annual license renewal') as RX-INFO LIMITED "
        "(medicines optimisation software).",
        proof_=proof("04981011", "https://www.rx-info.co.uk/cookie-policy/",
                     "Rx-info Ltd Registered in England and Wales, Company Number 04981011 Registered "
                     "office: 1 Colleton Crescent, Exeter, Devon, England, EX2 4DG")),
    new("SARD JV", ["SARD JV", "SARD JV Ltd", "SARD JV Ltd.", "SARD JV LTD."], DIG_IT,
        "https://www.sardjv.co.uk/",
        "Named on Epsom and St Helier award notice 'Medical Revalidation Software' as SARD JV Ltd; "
        "the company's own About page describes a joint venture with Oxleas NHS Foundation Trust.",
        proof_=proof("07916735", "https://www.sardjv.co.uk/About/",
                     "A joint venture with Oxleas NHS Foundation Trust. Registered in England and Wales "
                     "with company number 07916735. VAT No. 131901840")),
    new("HealthRota", ["HealthRota", "HealthRota Limited", "HEALTHROTA LIMITED"], DIG_IT,
        "https://www.healthrota.co.uk/",
        "Named on The Rotherham NHS Foundation Trust award notice 'Medical Erostering Software Solution'.",
        proof_=proof("10655443", "https://www.healthrota.co.uk/privacy_policy/",
                     "This website is owned and operated by HealthRota Limited . We are registered in "
                     "England and Wales under registration number 10655443 , and our registered office "
                     "is at 41 Dartmouth Park Road, London NW5 1SU")),
    new("Rotamap", ["Rotamap", "Rotamap Ltd", "Rotamap Limited"], DIG_IT,
        "https://www.rotamap.net/",
        "Named on University Hospitals Birmingham award notice 'Online Rostering System' as Rotamap Ltd.",
        proof_=proof("04551928", "https://www.rotamap.net/contact",
                     "© Rotamap Ltd. | 3 Tottenham Street, London W1T 2AF | Registered in England No. 04551928")),
    new("Henry Schein One UK", ["Henry Schein One UK", "Henry Schein One UK Limited",
                                "HENRY SCHEIN ONE UK Limited", "Henry Schein One"], DIG_IT,
        "https://www.henryscheinone.co.uk/",
        "Named on East of England Community Health award notice 'Provision of Dental Clinical Software' "
        "as HENRY SCHEIN ONE UK Limited. Henry Schein UK Limited (11735268) is a different registration "
        "and is NOT an alias of this record.",
        proof_=proof("02940919", "https://www.dentally.co/uk/about-us",
                     "© Henry Schein One UK LTD (Company registration number 02940919) Medcare South "
                     "Bailey Drive, Gillingham Business Park, Gillingham, Kent, ME8 0P")),
    new("Citrus Suite", ["Citrus Suite", "Citrus Suite Ltd", "Citrus Suite Limited", "CitrusSuite"], DIG_IT,
        "https://www.citrussuite.com/",
        "Named on The Walton Centre award notice 'Virtual Environment Rehabilitation Assistant (VERA) support'.",
        proof_=proof("06657283", "https://www.citrussuite.com/privacy-policy/",
                     "Registered in England and Wales. Company Reg: 06657283, VAT Reg: 938 4136 08")),
    new("OneAdvanced (Advanced Health and Care)",
        ["OneAdvanced (Advanced Health and Care)", "Advanced Health and Care",
         "Advanced Health and Care Limited", "OneAdvanced"], DIG_IT,
        "https://www.oneadvanced.com/",
        "Named on Lancashire Teaching Hospitals award notice 'ELFS - Finance & eProcurement System' as "
        "Advanced Health and Care. The company's own privacy policy gives the legal entity as "
        "Advanced Health and Care Limited (trading as OneAdvanced).",
        proof_=proof("02939302", "https://www.oneadvanced.com/privacy-policy/",
                     "Advanced Health and Care Limited (trading as OneAdvanced). Company number 02939302. "
                     "Registered office: The Mailbox, Level 3, 101 Wharfside Street, Birmingham, B1 1RF")),
    new("Blueteq", ["Blueteq", "Blueteq Limited", "BLUETEQ LIMITED", "BlueTeq"], DIG_IT,
        "https://blueteq.com/",
        "Named on Cwm Taf Morgannwg award notice 'BlueTeq Medicines Optimisation'.",
        proof_=proof("05334133", "https://blueteq.com/trust-extensions-new/",
                     "Unit A5, Endeavour Business Park Penner Road, Havant PO9 1QN Company Registration "
                     "Number: 5334133 Company VAT Number: 855 7246 95")),
    new("Floki Health", ["Floki Health", "Floki Health Ltd", "Floki Health Limited", "FLOKI HEALTH LTD"], DIG_IT,
        "https://www.flokihealth.co.uk/",
        "Named on The Rotherham NHS Foundation Trust award notice 'Location Asset management/ Smart hospital'.",
        proof_=proof("11082389", "https://www.flokihealth.co.uk/privacy-policy/",
                     "Our registered office is 3 Coningsby, Morpeth, Northumberland (Company Number 11082389)")),
]

base.EXISTING = {
    "Magentus Software Limited": dict(
        proof_=proof("08746973", "https://www.magentus.com/legal/magentus-group-emea-privacy-notice/",
                     "Magentus Group in EMEA is made up of the following companies: Magentus Software "
                     "Limited, a limited company incorporated in England and Wales with registered "
                     "number 08746973 and with its registered office at Second Floor, 75 Farringdon "
                     "Road, London"),
        aliases=[], site=None),
    "Harrison-AI Medical UK Ltd": dict(
        # Read from the rendered page (the notice is built by JavaScript). The notice
        # gives a contact address (280 Bishopsgate); the register's office is
        # Ludgate Hill. Name, number and active status agree, which is what route 2 tests.
        proof_=proof("12804340", "https://harrison.ai/privacy-notice/",
                     "United Kingdom: Harrison-AI Medical UK Ltd Company no: 12804340 Attention: "
                     "Privacy Officer 280 Bishopsgate, London, EC2M 4RB, England"),
        aliases=[], site=None),
    "Lenus Health": dict(
        proof_=None, aliases=[], site=None,
        note=(" Companies House 20/10/2026: SC652563 LENUS HEALTH LTD was dissolved on 28/02/2026, so it "
              "is not the operating company. The company's own site (https://www.lenushealth.com/) gives "
              "\"Lenus Health Ltd, 43 Constitution Street, Edinburgh, EH6 7BG\"; that is the registered "
              "office of SOLERSHA LTD SC828358 (active, incorporated 08/11/2024, formerly LENUS "
              "HEALTHCARE LIMITED until 21/02/2025). Not verified: whether SOLERSHA LTD is the operator "
              "or a successor; no source states it, so no company is attached.")),
}
base.NO_UK = {}


def main():
    seed = base.load(base.SEED)
    base.edit_records(base.SEED, base.company_match.build_index(seed))
    base.edit_records(base.INDEX, None)


if __name__ == "__main__":
    main()
