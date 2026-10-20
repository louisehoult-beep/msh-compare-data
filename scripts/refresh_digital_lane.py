#!/usr/bin/env python3
"""The digital health lane: NHS-buyer software and IT notices, in their own file.

WHAT THIS IS (20/10/2026, Hub health tech intelligence gap, build plan "Next 30
days"). The Hub's medical feeds are CPV 33 by design and stay that way:
company-awards.json (refresh_awards.py) and open-tenders.json
(refresh_open_tenders.py) are NOT touched by this script and must not be. This
writes ONE separate, tagged file, data/digital-lane.json, every row carrying
"lane": "digital", from three inputs:

  awards           data/framework-awards.json, already pulled daily from Find a
                   Tender by refresh_framework_awards.py (no network here). Every
                   award, contract, tender and planning release in that store
                   whose buyer is an NHS body and which carries a CPV 48 or 72.
  openNotices      A live pass over Find a Tender and Contracts Finder, tender and
                   planning stages, through refresh_open_tenders.py's own fetchers
                   with the lane rule passed in place of the medical rule. Closed
                   notices are dropped, as on the open-tenders page.
  marketEngagement data/atamis-opportunities-live.json, already pulled once a day
                   by refresh_atamis.py (no network here: Lou's one-request-a-day
                   decision of 28/08/2026 stands). Rows the shared rule calls
                   digital that are pre-market engagement or framework further
                   competition.

The rules are in scripts/digital_lane_rules.py and copied into the file.

USAGE
    python3 scripts/refresh_digital_lane.py              # last 8 days of notices
    python3 scripts/refresh_digital_lane.py --days 30    # catch up
    python3 scripts/refresh_digital_lane.py --offline    # no network: awards and
                                                         # Atamis only, open notices
                                                         # carried from the last run
Then: python3 scripts/stamp_notice.py && python3 verify.py
"""
import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digital_lane_rules as R  # noqa: E402

OUT_PATH = "data/digital-lane.json"
FA_PATH = "data/framework-awards.json"
ATAMIS_PATH = "data/atamis-opportunities-live.json"
DEFAULT_DAYS = 8
PANEL_SLUG = "digital-and-medical-it"

AWARD_TAGS = {"award", "awardUpdate", "contract", "contractUpdate"}
NOTICE_TAGS = {"planning", "planningUpdate", "tender", "tenderUpdate"}

LANE_RULE = (
    "A Find a Tender or Contracts Finder notice is in this lane when the buyer name "
    "is an NHS body (contains \"NHS\", \"Integrated Care Board\" or \"Health Board\"; "
    "bare \"Trust\" is not a match) AND a Common Procurement Vocabulary (CPV) code on the notice begins 48 (software "
    "package and information systems) or 72 (IT services). An Atamis opportunity "
    "carries no CPV code, so its own Category text stands in: a software, "
    "information systems or IT services category, or a title naming a clinical "
    "digital system. Every Atamis authority is an NHS body by construction.")
CLINICAL_RULE = (
    "CPV 48 and 72 are bought for payroll, finance, human resources and office systems as much as "
    "for clinical ones, so a lane row is not a claim of health technology. A row is "
    "flagged clinical only when its TITLE names a clinical system or a regulated "
    "digital product (electronic patient record, electronic prescribing, picture archiving "
    "and communication system (PACS), laboratory information management system (LIMS), "
    "artificial intelligence (AI), "
    "ambient voice, virtual ward, remote monitoring and the other terms in "
    "scripts/digital_lane_rules.py). Bare 'software', 'digital', 'IT' and 'licence' "
    "never flag a row. The speciality page shows clinical rows only.")
SCOPE_NOTE = (
    "A call-off under a framework is not a notice, and most digital money in the NHS "
    "moves as framework call-offs, capital business cases and G-Cloud awards without "
    "competition. This lane is therefore a floor, not a census: an absence here says "
    "nothing about the buyer or the market. Contract values, where shown, are the "
    "notice's own and are not summed across rows.")


def load(path, default=None):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return default


def award_rows(fa_doc):
    out = []
    for a in (fa_doc or {}).get("awards") or []:
        buyer = (a.get("buyer") or {}).get("name") or ""
        cpvs = a.get("cpv") or []
        if not R.in_lane(buyer, cpvs):
            continue
        tags = set(a.get("tag") or [])
        stage = ("award" if tags & AWARD_TAGS else
                 "tender" if tags & {"tender", "tenderUpdate"} else
                 "planning" if tags & {"planning", "planningUpdate"} else "other")
        values = [c.get("value") for c in a.get("contracts") or [] if c.get("value") is not None]
        out.append({
            "lane": "digital",
            "clinical": R.clinical(a.get("title")),
            "stage": stage,
            "title": a.get("title"),
            "buyer": buyer,
            "published": a.get("published"),
            "suppliers": [s.get("name") for s in a.get("suppliers") or [] if s.get("name")],
            "isFramework": bool(a.get("is_framework")),
            "contractEnd": next((c.get("end") for c in a.get("contracts") or [] if c.get("end")), None),
            "value": values[0] if len(values) == 1 else None,
            "digitalCpv": R.digital_cpvs(cpvs),
            "url": a.get("url"),
            "ocid": a.get("ocid"),
        })
    out.sort(key=lambda r: r.get("published") or "", reverse=True)
    return out


def lane_keep(tender, title, buyer):
    """keep() for refresh_open_tenders' fetchers: the lane rule on the HEADLINE
    CPV and the buyer name. Title words never admit a notice."""
    cl = tender.get("classification") or {}
    cpv = str(cl.get("id") or "") if cl.get("scheme") == "CPV" else ""
    extra = [str(c.get("id")) for c in tender.get("additionalClassifications") or []
             if c.get("scheme") == "CPV" and c.get("id")]
    return R.in_lane(buyer, [cpv] + extra)


def fetch_open_notices(days, today_iso):
    import refresh_open_tenders as OT
    rows, notes, ok = [], [], True
    for stage in ("tender", "planning"):
        for fn in (OT.fetch_fts, OT.fetch_cf):
            got, note, good = fn(days, today_iso, stage=stage, keep=lane_keep)
            rows += got
            notes.append(note.replace("open notice(s)", "digital lane notice(s)"))
            ok = ok and good
            print(" ", notes[-1], flush=True)
    seen, out = set(), []
    for r in rows:
        key = r.get("ocid") or r.get("url") or (r.get("title"), r.get("buyer"))
        if key in seen:
            continue
        seen.add(key)
        r = dict(r)
        r.pop("speciality", None)       # the medical tagger's slug; meaningless here
        r["lane"] = "digital"
        r["clinical"] = R.clinical(r.get("title"))
        out.append(r)
    return out, notes, ok


def merge_open(fresh, existing, today_iso):
    kept = {}
    for r in (existing or {}).get("openNotices") or []:
        cd = r.get("closingDate")
        if cd and cd[:10] < today_iso:
            continue
        kept[r.get("url") or r.get("ocid")] = r
    for r in fresh:
        kept[r.get("url") or r.get("ocid")] = r
    return sorted(kept.values(), key=lambda r: r.get("closingDate") or "9999-12-31")


def atamis_rows(at_doc, today_iso):
    import refresh_atamis as A
    out = []
    for o in (at_doc or {}).get("opportunities") or []:
        if (o.get("deadline") or "") < today_iso:
            continue
        labels = A.classify(o.get("name"), o.get("description"),
                            o.get("procurement_route"), o.get("category"))
        if "digital" not in labels:
            continue
        stage = [l for l in labels if l in ("pre_market_engagement", "framework_further_competition")]
        if not stage:
            continue
        out.append({
            "lane": "digital",
            "clinical": "digital_clinical" in labels,
            "labels": stage,
            "title": o.get("name"),
            "authority": o.get("authority"),
            "category": o.get("category"),
            "opens": o.get("opens"),
            "deadline": o.get("deadline"),
            "url": o.get("url"),
            "ref": o.get("ref"),
        })
    out.sort(key=lambda r: r.get("deadline") or "9999-12-31")
    return out


def assemble(awards, open_notices, engagement, existing, window, notes, complete, today):
    clin = lambda rows: sum(1 for r in rows if r.get("clinical"))
    doc = {
        "lane": "digital",
        "panel": PANEL_SLUG,
        "dataAsOf": today.strftime("%d/%m/%Y"),
        "generated": today.isoformat(),
        "source": ("Find a Tender and Contracts Finder OCDS notices (Open Government "
                   "Licence v3), via data/framework-awards.json and a live tender/planning "
                   "pass; Atamis Health Family public opportunity search via "
                   "data/atamis-opportunities-live.json."),
        "laneRule": LANE_RULE,
        "clinicalRule": CLINICAL_RULE,
        "scopeNote": SCOPE_NOTE,
        "untouched": ("data/company-awards.json and data/open-tenders.json keep their "
                      "CPV 33 medical rule. Nothing in this file is written to them."),
        "coverage": {
            "complete": bool(complete),
            "window": window,
            "notes": notes,
        },
        "counts": {
            "awards": len(awards),
            "awardsClinical": clin(awards),
            "openNotices": len(open_notices),
            "openNoticesClinical": clin(open_notices),
            "marketEngagement": len(engagement),
            "marketEngagementClinical": clin(engagement),
        },
        "awards": awards,
        "openNotices": open_notices,
        "marketEngagement": engagement,
    }
    windows = (existing or {}).get("windows") or []
    if window:
        windows = (windows + [window])[-60:]
    doc["windows"] = windows
    if existing and existing.get("_notice"):
        doc = {"_notice": existing["_notice"], **doc}
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--offline", action="store_true",
                    help="no network: carry open notices from the last run")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    os.chdir(os.path.dirname(HERE))

    today = dt.date.today()
    today_iso = today.isoformat()
    existing = load(OUT_PATH)
    awards = award_rows(load(FA_PATH, {}))
    engagement = atamis_rows(load(ATAMIS_PATH, {}), today_iso)

    if args.offline:
        fresh, notes, ok, window = [], ["--offline: no notice feed fetched this run; "
                                        "open notices carried from the previous run."], \
            bool((existing or {}).get("coverage", {}).get("complete", False)), None
    else:
        fresh, notes, ok = fetch_open_notices(args.days, today_iso)
        window = {"from": (today - dt.timedelta(days=args.days)).isoformat(),
                  "to": today_iso, "days": args.days, "run": today_iso}
    open_notices = merge_open(fresh, existing, today_iso)

    doc = assemble(awards, open_notices, engagement, existing, window, notes, ok, today)
    c = doc["counts"]
    print("digital lane: %d awards (%d clinical), %d open notices (%d clinical), "
          "%d market engagement (%d clinical)" % (
              c["awards"], c["awardsClinical"], c["openNotices"], c["openNoticesClinical"],
              c["marketEngagement"], c["marketEngagementClinical"]))
    if args.dry_run:
        print("--dry-run: nothing written.")
        return 0
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("wrote %s. Now: python3 scripts/stamp_notice.py && python3 verify.py" % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
