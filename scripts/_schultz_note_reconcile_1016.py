"""One-off: reconcile the Schultz Medical (UK) Limited seed note (16/10/2026).

The Company Intelligence report's Company information panel printed the seed
note written by the 07/09/2026 backfill ("Product range ... and website have NOT
been verified"), while the same report's Divisions panel said the range had been
read from the company's own site on 2026-09-16 (data/supplier-products.json:
schultzmedical.co.uk, 248 of the 249 products its own catalogue API declares,
12 divisions). Both cannot be true. The note is the stale one.

Website: schultzmedical.co.uk returned 200 on 16/10/2026 and names "Schultz
Medical UK", Unit 6 Commerce Park, Crowland Street, Southport PR9 7RL.
UK entity and ownership are still NOT verified: companyNumberCandidate 08853263
is a name-search candidate awaiting confirm_company_numbers.py, so the note keeps
saying so. Idempotent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like, describe  # noqa: E402

PATH = "data/supplier-seed.json"
NAME = "Schultz Medical (UK) Limited"
NOTE = ("Added 07/09/2026 from NHS Supply Chain's own contract launch brief for the Minimally "
        "Invasive Surgery framework (2026/S 000-061906); lots 4, 5 and 6 from the Find a Tender "
        "award notice 061906-2026. Website schultzmedical.co.uk confirmed as the company's own "
        "(Southport address, live 16/10/2026) and its product range read from that site's own "
        "catalogue on 16/09/2026 (248 of the 249 products it declares). UK entity and ownership "
        "have NOT been verified: Companies House 08853263 SCHULTZ MEDICAL (UK) LTD is a "
        "name-search candidate only, so check at source before quoting either to a customer.")
SPEC_EVIDENCE = ("Speciality assigned because the company is named on NHS Supply Chain's Minimally "
                 "Invasive Surgery, Related Equipment and Accessories framework, and borne out by "
                 "its own catalogue (hysteroscopy, gynaecology and laparoscopic instruments, read "
                 "16/09/2026).")


def main():
    with open(PATH, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    rec = [s for s in doc["suppliers"] if s.get("name") == NAME]
    if len(rec) != 1:
        raise SystemExit("expected one %s record" % NAME)
    rec = rec[0]
    if rec.get("note") == NOTE and rec.get("_specialitiesEvidence") == SPEC_EVIDENCE:
        print("already reconciled")
        return
    rec["note"] = NOTE
    rec["_specialitiesEvidence"] = SPEC_EVIDENCE
    fmt, round_trips = write_like(PATH, doc)
    print(describe(PATH, fmt, round_trips))


if __name__ == "__main__":
    main()
