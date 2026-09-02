#!/usr/bin/env python3
"""Verify one or more trust-profile JSON files against the batch gate.

Usage: python3 scripts/verify_trust_profile.py [--dir DIR] <CODE1> [CODE2 ...]

For each CODE, reads (from --dir, default ./tmp/trust-batch):
  <dir>/<CODE>-layer1.json   (layer-1 reference data, extracted from data/trust-pressures.json
                               and data/prep-config.json trustDirectory)
  <dir>/<CODE>-profile.json  (the draft profile to check)

Checks:
  - exact key order: name, code, region, context, news, structure, reportFacts, people, voices
  - name matches directory.n character for character
  - context mentions the waiting list, 18-week %, median wait and segment
  - no CQC rating asserted in context/news/structure if layer1 cqc is null/absent,
    UNLESS the profile explicitly explains it was sourced independently and dated
    (the accepted null-CQC carve-out, established batch ten/twelve)
  - HTTP-checks every source/linkedin URL (HEAD then GET, full browser headers)
  - no em dashes anywhere in string values

A URL that fails here is not necessarily dead — retry manually with curl using a full
browser header set, then a real browser, before dropping it. See docs/trust-profile-worklist.md
"Known fetching obstacles" for the recurring bot-block patterns.
"""
import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

EXPECTED_KEYS = ["name", "code", "region", "context", "news", "structure", "reportFacts", "people", "voices"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}


def check_url(url):
    if not url:
        return (url, "SKIP (empty)")
    last = "unknown"
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=25) as resp:
                if resp.getcode() == 200:
                    return (url, 200)
        except urllib.error.HTTPError as e:
            if e.code == 200:
                return (url, 200)
            last = e.code
        except Exception as e:
            last = str(e)
    return (url, f"FAIL ({last})")


def find_em_dashes(obj, path=""):
    hits = []
    if isinstance(obj, str):
        if "—" in obj:
            hits.append(path)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            hits.extend(find_em_dashes(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(find_em_dashes(v, f"{path}[{i}]"))
    return hits


def collect_urls(profile):
    urls = []
    for rf in profile.get("reportFacts", []):
        if rf.get("source"):
            urls.append(rf["source"])
    for p in profile.get("people", []):
        if p.get("source"):
            urls.append(p["source"])
        if p.get("linkedin"):
            urls.append(p["linkedin"])
    for v in profile.get("voices", []):
        if v.get("source"):
            urls.append(v["source"])
    return list(dict.fromkeys(urls))


def verify_one(directory, code):
    problems = []
    try:
        layer1 = json.load(open(f"{directory}/{code}-layer1.json"))
    except FileNotFoundError:
        return [f"[{code}] no layer1 file found"], []
    try:
        with open(f"{directory}/{code}-profile.json") as f:
            profile = json.load(f)
    except FileNotFoundError:
        return [f"[{code}] no profile file found"], []
    except json.JSONDecodeError as e:
        return [f"[{code}] invalid JSON: {e}"], []

    keys = list(profile.keys())
    if keys != EXPECTED_KEYS:
        problems.append(f"[{code}] key order/set wrong: got {keys}")

    dir_entry = layer1.get("directory") or {}
    expected_name = dir_entry.get("n")
    if expected_name and profile.get("name") != expected_name:
        problems.append(f"[{code}] name mismatch: profile={profile.get('name')!r} vs directory.n={expected_name!r}")

    if profile.get("code") != code:
        problems.append(f"[{code}] code field {profile.get('code')!r} != {code}")

    pr = layer1.get("pressures") or {}
    context = profile.get("context", "")

    def num_variants(n):
        if n is None:
            return []
        s = str(n)
        variants = {s}
        try:
            variants.add(f"{int(n):,}")
        except (ValueError, TypeError):
            pass
        return list(variants)

    wl = pr.get("wl")
    if wl is not None and not any(v in context for v in num_variants(wl)):
        problems.append(f"[{code}] context missing waiting list figure {wl}")

    pct18 = pr.get("pct18")
    if pct18 is not None and str(pct18) not in context and f"{pct18}%" not in context:
        problems.append(f"[{code}] context missing 18-week % figure {pct18}")

    med = pr.get("med")
    if med is not None and str(med) not in context:
        problems.append(f"[{code}] context missing median wait figure {med}")

    seg = pr.get("seg")
    all_text = context + " " + profile.get("news", "") + " " + profile.get("structure", "")
    if seg is not None and str(seg) not in all_text and f"segment {seg}" not in all_text.lower():
        problems.append(f"[{code}] context/news/structure missing oversight segment {seg}")

    cqc = pr.get("cqc")
    if cqc is None:
        cqc_letters = re.findall(r"\bCQC\b.{0,80}?(Outstanding|Good|Requires Improvement|Inadequate)\b", all_text, re.IGNORECASE)
        explains_null = bool(re.search(
            r"no (longer|overall) rating|not (currently )?rated|no single overall rating"
            r"|carries no (overall )?cqc rating|no cqc (rating|value)",
            all_text, re.IGNORECASE))
        if cqc_letters and not explains_null:
            problems.append(f"[{code}] asserts a CQC rating ({cqc_letters}) but layer1 cqc is null and no explanation given")

    ems = find_em_dashes(profile)
    if ems:
        problems.append(f"[{code}] em dash found at: {ems}")

    for p in profile.get("people", []):
        note = (p.get("note") or "").lower()
        role = p.get("role") or ""
        if "notice" in note and "enquiry" in note and role and "named as enquiry contact" not in role.lower():
            problems.append(f"[{code}] person {p.get('name')!r} sourced from a notice but carries role {role!r}")

    return problems, collect_urls(profile)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="tmp/trust-batch")
    ap.add_argument("codes", nargs="+")
    args = ap.parse_args()

    all_problems = []
    all_urls = {}
    for code in args.codes:
        problems, urls = verify_one(args.dir, code)
        all_problems.extend(problems)
        for u in urls:
            all_urls.setdefault(u, []).append(code)

    print(f"=== {len(args.codes)} profile(s), {len(all_urls)} unique URL(s) to check ===")

    url_failures = []
    if all_urls:
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(check_url, u): u for u in all_urls}
            for fut in as_completed(futs):
                url, status = fut.result()
                if status != 200:
                    url_failures.append((url, status, all_urls[url]))

    if all_problems:
        print("\n--- SCHEMA/CONTENT PROBLEMS ---")
        for p in all_problems:
            print(" -", p)
    else:
        print("\nNo schema/content problems.")

    if url_failures:
        print("\n--- URL FAILURES (not necessarily dead - retry with full browser headers or a real browser before dropping) ---")
        for url, status, codes_ in url_failures:
            print(f" - {status}: {url}  (used by {codes_})")
    else:
        print("\nAll URLs returned 200.")

    if all_problems or url_failures:
        sys.exit(1)
    print("\nGATE PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
