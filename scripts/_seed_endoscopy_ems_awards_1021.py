#!/usr/bin/env python3
"""One-off, 21/10/2026: endoscopy management and reporting system awards since 2021.

WHY (Medilogik call prep, 23/10/2026)
-------------------------------------
data/digital-lane.json only holds the notices of its own recent walk, so the
software awards that show who runs each trust's endoscopy reporting system
(Medilogik EMS, HD Clinical's Solus, Endosoft) were missing from every supplier
record. This reads each notice below at source, in this run, and feeds it
through the normal digital-awards build (scripts/refresh_company_digital_awards.py
build()), so the exact-only match rule, the lane rule and verify.py's checks all
apply unchanged. Rows are then carried forward by that script like any other.

THE NOTICES
-----------
Found by a Contracts Finder search (awarded, published from 01/01/2021) for
"endoscopy", "endoscopy reporting", "endoscopy management", "endoscopy
software", "Medilogik", "Solus", "HD Clinical", "EndoSoft", and the Find a
Tender notice for NHS National Services Scotland's national Endoscopy Reporting
System. Each is re-read below from the notice's own OCDS release. Scopes,
consumables and equipment maintenance are not software awards and are not here.

A notice is added only if it passes the lane rule (NHS buyer name AND a CPV 48
or 72 code, scripts/digital_lane_rules.py). Those that fail it are printed and
left out, never forced in. Kettering's 09/01/2023 notice (addd5b51) is left out
because its 03/02/2023 notice (b6ff4f87) republishes the same award, same
contract period, with a revised value: each award appears once, under its most
recent notice.

USAGE
    python3 scripts/_seed_endoscopy_ems_awards_1021.py          # write
    python3 scripts/_seed_endoscopy_ems_awards_1021.py --check  # report only
    ... --from DIR   read releases saved in this session's fetch (DIR/<id>.json,
                     DIR/fts_<id>.json) when Contracts Finder is answering 429
Then: python3 scripts/stamp_notice.py && python3 verify.py
"""
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digital_lane_rules as R  # noqa: E402
import refresh_company_digital_awards as CDA  # noqa: E402

CF = "https://www.contractsfinder.service.gov.uk/Published/Notice/releases/%s.json"
CF_NOTICE = "https://www.contractsfinder.service.gov.uk/Notice/%s"
FTS = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages/%s"
FTS_NOTICE = "https://www.find-tender.service.gov.uk/Notice/%s"
UA = "Mozilla/5.0 (compatible; msh-compare-data endoscopy-ems-awards)"

CF_IDS = [
    # Medilogik
    "b6ff4f87-1eb7-4052-91c1-ef1bf5f59995",  # Kettering General, 03/02/2023
    "a8869a9a-7104-4588-8f89-def8428807a2",  # Derbyshire Support and Facilities Services
    "fc05fddc-b4d7-4d7b-b2c1-a9ba0bd4f9f9",  # Derbyshire Support and Facilities Services
    "ead912dc-1777-47fd-83c0-319e10223ca9",  # Derbyshire Support and Facilities Services
    "f7032089-a280-482c-8c71-f39892041e8b",  # West Herts, notice names "MEDILOGIC UK LTD"
    "8d70825b-ba9c-4f7b-9ed8-3a233eca3bbf",  # Norfolk and Norwich
    "e00602ca-5602-4e01-bf31-337843e4223b",  # Nottingham
    "32cf1700-236c-4a50-9246-0c27e1291213",  # Barnsley
    "e02cf0b2-d88d-49b9-ad98-c2788d1ce9d5",  # East Sussex
    "30ac7e50-1aad-4556-bca0-ff60d8a1adcc",  # West Suffolk
    # HD Clinical (Solus)
    "8b416209-d7a5-4f1e-b996-a0fccad1ba20",  # Frimley
    "99c55b14-4d3e-436d-a31f-e107b658175c",  # West Suffolk
    "1a70d2aa-d2ff-4982-b7d7-5ed3b2f67ba3",  # Northampton General
    "911ebf67-d108-4879-8d0c-22d3ea175f2d",  # West Suffolk
    "37ecc23f-0e55-49b9-808f-df414b15d066",  # University Hospitals Sussex (Solus upgrade)
    "1128d509-85ed-49f1-bd7b-d902d7a7e47e",  # Whittington Health
    "36fe4e59-073b-493b-a983-a71c8c323942",  # Leicester
    "a12229c9-feb9-4dc2-9cbb-92bfc3784f09",  # Princess Alexandra
    "24ea3a4d-19b0-4cb0-9929-6a811ae2a7e4",  # Princess Alexandra
    # Endosoft
    "72471ac0-40af-4686-8f3d-37efb51ee830",  # Hull
    "96d4683f-0894-45cf-9a1f-62f9aae61200",  # Hull
    "6a5183de-e4d4-4aff-b90b-cddd789631f6",  # Hull
    "ca02416a-9d44-4613-9243-d10b4f09bed0",  # Hull
    "6af82d87-7062-401f-b2eb-245a5e0da7a8",  # King's College Hospital
    "0bf9dad6-a49a-449e-b04e-d3bef97ee5cb",  # Walsall
    "3ac714ab-38a3-4726-97bc-de4ea3c7a53f",  # United Lincolnshire
    "05587760-96a3-418d-ac68-f714f74b8e9a",  # County Durham and Darlington
    # East and North Herts EMS, bought through Insight Direct (reseller)
    "758790a9-53f4-406b-ba49-baa760597079",
    "78c7eee5-78aa-44ee-a99c-fce6dd5ae844",
    "bb2c8ade-12f9-4fe6-b54a-d961c518fc1c",
    "8d32dce9-9fbb-4717-8ca8-9ce4bafe3aaf",
]
FTS_IDS = ["020909-2023"]  # NHS National Services Scotland, national ERS award


def fetch_json(url):
    last = None
    for attempt in range(4):
        time.sleep(1.5)  # Contracts Finder answers bursts with 429
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(15 * (attempt + 1))
    raise RuntimeError("fetch failed %s: %s" % (url, last))


def cpvs_of(tender):
    out = []
    for c in [tender.get("classification") or {}] + list(tender.get("additionalClassifications") or []):
        if c.get("scheme") == "CPV" and c.get("id"):
            out.append(str(c["id"]))
    return out


def award_release(pkg):
    for r in reversed(pkg.get("releases") or []):
        if r.get("awards"):
            return r
    return None


def rows_for(pkg, url):
    r = award_release(pkg)
    if r is None:
        return [], "no award in the release package"
    tender = r.get("tender") or {}
    buyer = (r.get("buyer") or {}).get("name") or ""
    cpvs = cpvs_of(tender)
    if not R.in_lane(buyer, cpvs):
        return [], "outside the lane rule (buyer %r, CPV %s)" % (buyer, ",".join(cpvs))
    out = []
    contracts = r.get("contracts") or []
    for a in r.get("awards") or []:
        names = [s.get("name") for s in a.get("suppliers") or [] if s.get("name")]
        if not names:
            names = [p.get("name") for p in r.get("parties") or []
                     if "supplier" in (p.get("roles") or []) and p.get("name")]
        value = (a.get("value") or {}).get("amount")
        if value is None and len(contracts) == 1:
            value = (contracts[0].get("value") or {}).get("amount")
        if not isinstance(value, (int, float)) or value <= 1:
            value = None
        end = ((a.get("contractPeriod") or {}).get("endDate")
               or next(((c.get("period") or {}).get("endDate") for c in contracts
                        if (c.get("period") or {}).get("endDate")), None))
        date = (a.get("datePublished") or r.get("date") or "")[:10]
        for n in names:
            out.append({
                "title": tender.get("title"),
                "buyer": buyer,
                "date": date,
                "url": url,
                "ocid": r.get("ocid"),
                "source": CDA.source_of(url),
                "valueAmount": float(value) if value is not None else None,
                "valueCurrency": "GBP" if value is not None else None,
                "periodEnd": end[:10] if end else None,
                "isFramework": False,
                "digitalCpv": R.digital_cpvs(cpvs),
                "clinical": R.clinical(tender.get("title")),
                "lane": "digital",
                "noticeSupplierName": n,
                "noticeSupplierCount": len(names),
            })
    return out, None


def main():
    check = "--check" in sys.argv
    saved = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else None

    def get(url, name):
        if saved:
            with open(os.path.join(saved, name + ".json"), encoding="utf-8") as f:
                return json.load(f)
        return fetch_json(url)

    rows, skipped = [], []
    for i in CF_IDS:
        got, why = rows_for(get(CF % i, i), CF_NOTICE % i)
        rows += got
        if why:
            skipped.append((CF_NOTICE % i, why))
    for n in FTS_IDS:
        got, why = rows_for(get(FTS % n, "fts_" + n), FTS_NOTICE % n)
        rows += got
        if why:
            skipped.append((FTS_NOTICE % n, why))
    for u, why in skipped:
        print("left out: %s: %s" % (u, why))
    print("%d notice row(s) read in lane" % len(rows))

    seed, lane = CDA.load(CDA.SEED), CDA.load(CDA.LANE)
    prev = CDA.load(CDA.OUT, {}) or {}
    pool = dict(prev)
    pool["unmatched"] = list(prev.get("unmatched") or []) + rows
    doc = CDA.build(seed, lane, CDA.load(CDA.MEDICAL, {}), pool)
    for r in rows:
        placed = [c for c, rs in doc["companies"].items()
                  if any(CDA.row_key(x) == CDA.row_key(r) for x in rs)]
        print("  %s | %s | %s -> %s" % (r["date"], r["buyer"][:45], r["noticeSupplierName"],
                                        placed[0] if placed else "UNMATCHED"))
    c = doc["counts"]
    print("company-digital-awards: %d rows on %d companies, %d unmatched, %d ambiguous"
          % (c["awardRows"], c["companies"], c["unmatched"], c["ambiguous"]))
    if check:
        return
    with open(CDA.OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote %s" % CDA.OUT)


if __name__ == "__main__":
    main()
