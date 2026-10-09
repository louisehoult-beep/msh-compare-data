#!/usr/bin/env python3
"""Snapshot the trust-level operational figures the Analysis pipeline already
holds into data/trust-pressures.json, so the Meeting Prep tool can put real,
sourced numbers in front of a rep for every trust it has them for.

WHY A SNAPSHOT AND NOT A LIVE FETCH. The figures live in analysis-data.json in
louisehoult-beep/medical-sales-hub-pipeline, which is a PRIVATE repo — an
anonymous raw.githubusercontent request returns 404 (checked 14/08/2026). The
Hub's tools run in the member's browser with no credentials, so they can only
read msh-compare-data. Copying is therefore the only route, and the copy is
stamped with the pipeline's own builtUTC and each source's own period so a
reader can see exactly how old every number is. If the pipeline repo is ever
made public, delete this script and fetch it directly instead.

READ FROM origin/main, NOT THE WORKING TREE. The local pipeline clone sits on
whatever branch someone last worked on — it was on fix/live-desk-flapping and a
week behind on 14/08/2026 — and the working tree's analysis-data.json is
whatever that branch has. main is what the hourly job publishes, so main is the
only honest source. `--tree` overrides for a manual run.

NOTHING HERE IS DERIVED. Every field is copied through unchanged from the
publisher's own figure. No ratios, rankings or "the only trust that..." claims
are computed, because a derived claim would need its rule stated and an
evidence floor under root rule 14, and none is needed to be useful: a rep
wants the trust's own median wait, not our opinion of it.

Usage:  python3 scripts/build_trust_pressures.py [--tree <git-ref>] [--repo <path>]
"""
import json, subprocess, sys, datetime, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stamp_notice

PIPELINE = os.path.expanduser(
    "~/Library/CloudStorage/OneDrive-Personal/Cowork-OS/02-Elevate-and-Thrive/"
    "Hub/Medical-Sales-Hub/cloud-pipeline")
OUT = "data/trust-pressures.json"
MAP = "data/trust-map.json"

# Per-field provenance. Each figure a member reads carries the publisher, the
# period it covers and a link to the publisher's own page. Root rule 12: no
# figure without a source, and no source without the period it applies to.
SOURCES = {
    "rtt": {
        "label": "NHS England — Referral to Treatment (RTT) waiting times, incomplete pathways",
        "url": "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/",
        "fields": ["wl", "pct18", "w52", "w65", "w78", "med", "spec"],
    },
    "cqc": {
        "label": "Care Quality Commission — latest overall provider ratings",
        "url": "https://www.cqc.org.uk/about-us/transparency/using-cqc-data",
        "fields": ["cqc"],
    },
    "seg": {
        "label": "NHS Oversight Framework — acute provider segmentation (1 best to 4)",
        "url": "https://data.england.nhs.uk/nhs-oversight-framework/acute/league-table",
        "fields": ["seg"],
    },
    "ne": {
        "label": "NHS England — provisional Never Events",
        "url": "https://www.england.nhs.uk/patient-safety/never-events-data/",
        "fields": ["ne"],
    },
    "cdi": {
        "label": "UKHSA — mandatory C. difficile surveillance (hospital-onset)",
        "url": "https://www.gov.uk/government/statistics/clostridioides-difficile-infection-annual-data",
        "fields": ["cdi"],
    },
    "eric": {
        "label": "NHS Digital — Estates Returns Information Collection (ERIC)",
        "url": "https://digital.nhs.uk/data-and-information/publications/statistical/"
               "estates-returns-information-collection",
        "fields": ["backlogHi", "backlogTot", "capEq"],
    },
}

KEEP = ("wl", "pct18", "w52", "w65", "w78", "med", "cqc", "seg", "ne",
        "cdi", "cdiTotal", "backlogHi", "backlogTot", "capEq", "spec", "region")


def load_analysis(repo, ref):
    if ref == "WORKTREE":
        return json.load(open(os.path.join(repo, "analysis-data.json")))
    subprocess.run(["git", "-C", repo, "fetch", "-q", "origin"], check=False)
    raw = subprocess.run(["git", "-C", repo, "show", "%s:analysis-data.json" % ref],
                         capture_output=True, check=True).stdout
    return json.loads(raw)


def main():
    args = sys.argv[1:]
    ref, repo = "origin/main", PIPELINE
    if "--tree" in args:
        ref = args[args.index("--tree") + 1]
    if "--repo" in args:
        repo = args[args.index("--repo") + 1]

    a = load_analysis(repo, ref)
    trusts = a.get("trusts") or []

    # Shrink guard. The Analysis page has carried 140+ trusts since it was
    # built; a sudden collapse means the upstream fetch failed, and half a
    # directory published as if it were the whole one is the failure root
    # rule 14 exists to stop. Refuse rather than overwrite a good file.
    if len(trusts) < 120:
        raise SystemExit("ABORT: analysis-data has only %d trusts (expected ~148) — "
                         "refusing to publish a shrunken snapshot." % len(trusts))

    built = a.get("builtUTC", "")
    try:
        age = (datetime.datetime.now(datetime.timezone.utc)
               - datetime.datetime.fromisoformat(built.replace("Z", "+00:00"))).days
    except Exception:
        age = None
    if age is not None and age > 45:
        raise SystemExit("ABORT: analysis-data was built %d days ago (%s). The RTT feed is "
                         "monthly — publishing this would put stale waiting times in front "
                         "of members. Re-run the pipeline's refresh-analysis workflow first."
                         % (age, built))

    # DROP TRUSTS THAT NO LONGER LEGALLY EXIST. The RTT return is a monthly
    # snapshot, so it keeps reporting a trust for the months it was still
    # trading — North Bristol NHS Trust filed 42,031 waiters for June 2026 and
    # legally ended on 30/06/2026. Publishing that would put a rep in front of
    # a trust that cannot be sold to. trust-map.json is the liveness test (it
    # filters on legal end date, not ODS Status), so anything absent from it is
    # not a live account. Dropped ones are NAMED, never silently trimmed.
    live_codes = {t["code"] for t in json.load(open(MAP))["trusts"]}
    out, dropped = {}, []
    for t in trusts:
        code = t.get("ods")
        if not code:
            continue
        if code not in live_codes:
            dropped.append("%s (%s)" % (t.get("name") or code, code))
            continue
        rec = {k: t[k] for k in KEEP if t.get(k) not in (None, {}, "")}
        rec["name"] = t.get("name")
        out[code] = rec
    if dropped:
        print("dropped %d trust(s) carrying figures but no longer legally live: %s"
              % (len(dropped), "; ".join(sorted(dropped))), file=sys.stderr)

    doc = {
        # Its OWN marker ref, not a copied one. Lifting prep-config's notice
        # wholesale would stamp this file with prep-config's ref, so a leaked
        # copy would trace back to the wrong file — worse than no marker,
        # because it looks right until it matters. stamp_notice is the single
        # source for both the wording and the ref.
        "_notice": stamp_notice.notice_for(os.path.basename(OUT)),
        "note": ("Trust-level operational figures for the Meeting Prep tool, copied unchanged "
                 "from the publisher's own release via the Hub's Analysis pipeline. No figure "
                 "here is derived, ranked or interpreted. Rebuild with "
                 "scripts/build_trust_pressures.py."),
        "asOf": datetime.date.today().strftime("%d/%m/%Y"),
        "builtFrom": "medical-sales-hub-pipeline analysis-data.json, builtUTC %s (%s)" % (built, ref),
        "periods": {
            "rtt": a.get("rttPeriod"),
            "cqc": a.get("cqcAsOf"),
            "neverEvents": a.get("nePeriod"),
            "cdiff": a.get("cdiFY"),
            "eric": a.get("ericFY"),
        },
        "sources": SOURCES,
        "fieldMeanings": {
            "wl": "total incomplete RTT pathways (the waiting list)",
            "pct18": "% of the waiting list within 18 weeks (national standard 92%)",
            "w52": "patients waiting 52+ weeks",
            "w65": "patients waiting 65+ weeks",
            "w78": "patients waiting 78+ weeks",
            "med": "median wait, in weeks, across all specialities",
            "spec": "median wait in weeks, by RTT treatment function",
            "cqc": "CQC overall provider rating",
            "seg": "NHS Oversight Framework segment, 1 (most autonomy) to 4 (most support)",
            "ne": "Never Events recorded in the period",
            "cdi": "hospital-onset C. difficile cases; cdiTotal is all cases",
            "backlogHi": "high and significant-risk backlog maintenance, £",
            "backlogTot": "total backlog maintenance, £",
            "capEq": "capital investment in equipment, £",
        },
        "national": a.get("national", {}),
        "count": len(out),
        "trusts": out,
    }
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("trust-pressures: %d trusts · RTT %s · CQC %s · from %s (%s)"
          % (len(out), a.get("rttPeriod"), a.get("cqcAsOf"), ref, built))


if __name__ == "__main__":
    main()
