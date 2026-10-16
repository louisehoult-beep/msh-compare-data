"""One-off: the Minimally Invasive Surgery competitor set on Compare by speciality
reads its lots from the Find a Tender award notice, and lists every supplier on
the framework (16/10/2026).

Found while checking the Hub for a Schultz Medical demo. Compare by speciality >
Minimally invasive surgery listed 21 of the framework's 60 suppliers (Schultz
Medical (UK) Limited not among them, so it could not be picked as "your
company"), and its product-type column was built from each supplier's own
product pages because routeNote said per-supplier lot assignment existed only in
the login-gated Framework Matrices. That was no longer true: the Hub has held
the award notice's lots since 30/09/2026 (data/frameworks.json supplierLots,
source fts-award, https://www.find-tender.service.gov.uk/Notice/061906-2026,
re-read in Chrome 16/10/2026). Trocars showed 11 companies where Lot 5 has 22,
and four of the 11 (Healthium, Medline, Meril, Teleflex) are not on Lot 5.

What this does, for `mis` only:
  * each type is one lot of the award (clips = Lot 1 ... maint = Lot 8), and its
    label now says so;
  * every row's `t` is exactly the lots the award gives its supplier, nothing
    else; a supplier with no lot resolved gets [] and its note says why;
  * every one of the 60 brief suppliers has a row. Existing rows keep their
    co, ref, brands, url, note and iss (their product evidence is still true);
    new rows use the seed record's own name and say product detail is not
    verified;
  * routeNote no longer claims lots are only in the gated matrices.

Every brief name is matched to its seed record by company_match.resolve, which
must come back "confirmed" for all 60 and distinct, or this refuses.
Idempotent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import company_match  # noqa: E402
from seed_format import write_like, describe  # noqa: E402

PATH = "data/compare-suppliers.json"
FW_URL = "https://www.supplychain.nhs.uk/product-information/contract-launch-brief/minimally-invasive-surgery/"
AWARD = "https://www.find-tender.service.gov.uk/Notice/061906-2026"

LOT_TYPE = {"Lot 1": "clips", "Lot 2": "energy", "Lot 3": "staple", "Lot 4": "instruments",
            "Lot 5": "trocar", "Lot 6": "gynae", "Lot 7": "kits", "Lot 8": "maint"}
TYPE_LABEL = {
    "clips": "Lot 1 · Clips and clip appliers",
    "energy": "Lot 2 · Advanced energy based devices",
    "staple": "Lot 3 · Surgical stapling devices",
    "instruments": "Lot 4 · MIS instruments, devices and consumables",
    "trocar": "Lot 5 · Trocar systems and accessories",
    "gynae": "Lot 6 · Gynaecological endoscopy and uterine ablation",
    "kits": "Lot 7 · MIS procedure kits",
    "maint": "Lot 8 · Maintenance of MIS instruments and equipment",
}
ROUTE_NOTE = (
    "Eight lots: clips and clip appliers, advanced energy devices, surgical stapling, "
    "general laparoscopic instruments/devices/consumables, trocars, gynaecological endoscopy "
    "and uterine ablation, procedure kits, and maintenance of MIS instruments and equipment. "
    "Reference 2026/S 000-061906. All 60 suppliers on NHS Supply Chain's launch brief are "
    "listed. Which lot each one holds is read from the Find a Tender contract award notice for "
    "this procurement (061906-2026, re-read 16/10/2026), so picking a product type shows exactly "
    "the suppliers awarded that lot. Vanguard AG has no lot shown: the award names Vanguard "
    "Medical Devices Ltd on Lot 2, a separately registered UK company (Companies House "
    "12215708), so that lot is not attributed to it. Brands and product notes come from each "
    "supplier's own published pages; rows marked \"Not verified\" have no product detail yet.")
OLD_TAIL = " Lots held on this framework (Find a Tender award notice 061906-2026): "


def lot_text(lots):
    return ", ".join(lots) + "."


def main():
    seed = json.load(open("data/supplier-seed.json", encoding="utf-8"))
    idx = company_match.build_index(seed)
    fw = next(f for f in json.load(open("data/frameworks.json", encoding="utf-8"))["frameworks"]
              if f.get("url") == FW_URL)
    lots = fw.get("supplierLots") or {}

    b2c = {}
    for b in fw["suppliers"]:
        c, state, why = company_match.resolve(b, idx)
        if state != "confirmed":
            raise SystemExit("brief supplier %r does not resolve: %s" % (b, why))
        b2c[b] = c
    if len(set(b2c.values())) != len(b2c):
        raise SystemExit("two brief suppliers resolve to one Hub company; refusing")
    c2b = {c: b for b, c in b2c.items()}

    with open(PATH, "rb") as f:
        doc = json.loads(f.read().decode("utf-8"))
    blk = doc["specialities"]["mis"]
    # A company already in the file under another speciality keeps that row's
    # spelling: verify.py fails one company written two ways in this file.
    elsewhere = {}
    for sp, other in doc["specialities"].items():
        if sp == "mis":
            continue
        for s in other.get("suppliers") or []:
            c, state, _ = company_match.resolve(s.get("ref") or s["co"], idx)
            if state == "confirmed":
                elsewhere.setdefault(c, (s["co"], s.get("ref") or s["co"]))
    rows, covered = [], set()
    for s in blk["suppliers"]:
        c, state, _ = company_match.resolve(s.get("ref") or s["co"], idx)
        b = c2b.get(c) if state == "confirmed" else None
        if not b:
            raise SystemExit("existing row %r is not a supplier on this framework" % s["co"])
        covered.add(b)
        held = lots.get(b) or []
        s["t"] = [LOT_TYPE[l] for l in held if l in LOT_TYPE]
        note = s.get("note") or ""
        if OLD_TAIL in note:
            note = note[:note.index(OLD_TAIL)]
        s["note"] = note + OLD_TAIL + (lot_text(held) if held else "none attributed.")
        rows.append(s)

    for b in fw["suppliers"]:
        if b in covered:
            continue
        c = b2c[b]
        held = lots.get(b) or []
        if held:
            lot_line = ("Lots held on this framework (Find a Tender award notice 061906-2026): "
                        + lot_text(held))
        else:
            lot_line = ("No lot attributed: the award notice names no contractor that resolves to "
                        "this supplier under the Hub's alias rule.")
        co, ref = elsewhere.get(c, (c, c))
        row = {
            "co": co,
            "ref": ref,
            "brands": "Not verified — brand-level detail not yet captured; see the supplier's own site.",
            "t": [LOT_TYPE[l] for l in held if l in LOT_TYPE],
            "note": ("Named on NHS Supply Chain's own contract launch brief for the Minimally Invasive "
                     "Surgery, Related Equipment and Accessories framework as \"%s\". %s Product "
                     "range not yet verified for this speciality." % (b, lot_line)),
            "iss": [],
        }
        # The row's source is the document that puts it here, not a website the
        # seed may still mark unverified.
        row["url"] = AWARD if held else FW_URL
        rows.append(row)

    rows.sort(key=lambda r: r["co"].lower())
    blk["suppliers"] = rows
    blk["types"] = dict(TYPE_LABEL)
    blk["routeNote"] = ROUTE_NOTE
    fmt, round_trips = write_like(PATH, doc)
    print("mis rows: %d (framework suppliers %d)" % (len(rows), len(fw["suppliers"])))
    for k in TYPE_LABEL:
        print("  %-12s %d" % (k, sum(1 for r in rows if k in r["t"])))
    print(describe(PATH, fmt, round_trips))


if __name__ == "__main__":
    main()
