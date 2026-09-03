#!/usr/bin/env python3
"""Company name resolver for the Medical Sales Intelligence Hub.

The same company arrives under a different name from every source: NHS Supply
Chain writes "Stryker UK Limited", Find a Tender writes "STRYKER UK LTD", the
trade press writes "Stryker", the company's own site writes "Stryker UK". Left
alone that produces duplicate rows, a supplier that looks like two suppliers,
and a "no results" that reads to a member as "not on the framework".

This resolves any incoming name to ONE canonical Hub name, or refuses.

  python3 company_alias.py build                 rebuild the registry from source
  python3 company_alias.py resolve "NAME" [...]  resolve one or more names
  python3 company_alias.py check FILE|-          resolve a list, one name per line
  python3 company_alias.py selftest              prove the gate still catches things

Exit codes (this is the check, not a suggestion):
  0  every name resolved
  1  at least one name UNRESOLVED, or the overlay is malformed
  2  at least one name AMBIGUOUS (matched two different companies)

Sources, in precedence order:
  1. data/supplier-seed.json in the msh-compare-data working copy - the master
     supplier records and their aliases. Read only; never written by this script.
  2. alias-overlay.json beside this file - hand-maintained, for names the seed
     does not carry (renames, trading names, non-supplier companies).

WHY IT REFUSES RATHER THAN GUESSES: there is no fuzzy matching here on purpose.
Substring and edit-distance matching is exactly how homonyms get merged, and a
merged homonym publishes a false statement about a real company under the Hub's
name. Root rule 14: publishing nothing is the correct output when the evidence
is thin.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OVERLAY = os.path.join(HERE, "alias-overlay.json")
REGISTRY = os.path.join(HERE, "company-alias-registry.json")
SEED = os.path.abspath(os.path.join(
    HERE, "..", "data", "supplier-seed.json"))
# Moved into msh-compare-data itself 03/09/2026 (was Hub/company-aliases/,
# a sibling of this repo) so cloud sessions without OneDrive access can use
# it. HERE is now <repo>/company-aliases, so the seed is just "../data".

# Stripped when matching. Deliberately shallow: "healthcare", "medical" and
# "group" are NOT here, because removing them starts matching different
# companies to each other.
LEGAL_SUFFIX = (
    "limited|ltd|plc|p l c|llp|llc|inc|incorporated|corp|corporation|co|"
    "gmbh|a s|as|ab|bv b v|bv|nv n v|nv|sa s a|sa|ag|spa s p a|spa|oy|"
    "pty|pte|srl|sarl|kk"
)
TERRITORY = "uk|u k|gb|great britain|united kingdom|england|ireland|europe|emea"

REQUIRED_OVERLAY_FIELDS = ("canonical", "variants", "reason", "evidence", "addedOn")

# NHS Supply Chain appends routing tokens to the supplier name in its catalogue.
# Only two are stripped here, and deliberately only two:
#   (E-DIRECT) - an explicit channel marker, always bracketed, never part of a company name
#   NEWBURY01  - a depot code, always a word followed by digits
# Added 18/08/2026. A wider version of this rule was written first and REVERTED the same
# hour, because the gate caught it: stripping bare "STOCK"/"DIRECT" made the check exit 2
# (AMBIGUOUS, worse than unresolved). Two reasons it must not be widened:
#   1. Five legitimate canonical names end in those words - Bidfood Direct, Daylong Direct,
#      Hospital Direct, Insight Direct, Kimal PLC Stock. Stripping would corrupt them.
#   2. The supplier seed already holds channel variants as DISTINCT records ("Kimal PLC" and
#      "Kimal PLC Stock"; "Mediq Healthcare UK Ltd" and "Mediq Healthcare Uk Limited Ex Bunzl
#      Hea"). Collapsing the token therefore creates ambiguity by design of the seed.
# Whether those seed duplicates should be merged is a data decision for Lou, not a
# normalisation rule. Until then those names resolve by explicit alias or not at all.
NHSSC_CHANNEL_BRACKETED = "e direct|edirect"
NHSSC_DEPOT_CODE = r"[a-z]+\d{2,}"




def norm(s):
    """Lowercase, & -> and, strip punctuation and collapse whitespace."""
    s = str(s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_stripped(s):
    """norm() with trailing legal suffixes and territory words removed."""
    n = norm(s)
    prev = None
    while prev != n:
        prev = n
        n = re.sub(r"\s+(%s)$" % NHSSC_CHANNEL_BRACKETED, "", n)
        n = re.sub(r"\s+(%s)$" % NHSSC_DEPOT_CODE, "", n)
        n = re.sub(r"\s+(%s)$" % LEGAL_SUFFIX, "", n)
        n = re.sub(r"\s+(%s)$" % TERRITORY, "", n)
        n = n.strip()
    return n


def load_json(path, what):
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        die("%s not found at %s" % (what, path))
    except json.JSONDecodeError as exc:
        die("%s is not valid JSON: %s" % (what, exc))


def die(msg, code=1):
    print("FAIL: %s" % msg, file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- build

def read_overlay():
    """Load and validate the hand-maintained overlay. Exits 1 if malformed.

    Returns (entries, ambiguous, distinct).

    ambiguous maps a normalised name to the declaration explaining why two real
    companies legitimately share it. distinct records pairs somebody has already
    checked and found to be different companies, so the suggestion machinery
    stops offering them again every sweep.
    """
    data = load_json(OVERLAY, "alias-overlay.json")
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        die("alias-overlay.json: 'entries' must be a list")
    problems = []
    ambiguous = {}
    for i, a in enumerate(data.get("ambiguous", []) or []):
        label = a.get("name") or "ambiguous entry %d" % i
        for field in ("name", "between", "reason", "evidence", "addedOn"):
            if not a.get(field):
                problems.append("ambiguous %s: missing '%s'" % (label, field))
        if a.get("between") and len(a["between"]) < 2:
            problems.append("ambiguous %s: 'between' needs at least two companies" % label)
        if a.get("name"):
            ambiguous[norm(a["name"])] = a

    distinct = {}
    for i, p in enumerate(data.get("distinct", []) or []):
        label = p.get("a") or "distinct entry %d" % i
        for field in ("a", "b", "reason", "evidence", "addedOn"):
            if not p.get(field):
                problems.append("distinct %s: missing '%s'" % (label, field))
        if p.get("a") and p.get("b"):
            distinct.setdefault(norm(p["a"]), set()).add(norm(p["b"]))
            distinct.setdefault(norm(p["b"]), set()).add(norm(p["a"]))
    for i, e in enumerate(entries):
        label = e.get("canonical") or "entry %d" % i
        for field in REQUIRED_OVERLAY_FIELDS:
            if not e.get(field):
                problems.append("%s: missing '%s'" % (label, field))
        variants = e.get("variants")
        if variants is not None and not isinstance(variants, list):
            problems.append("%s: 'variants' must be a list" % label)
        ev = str(e.get("evidence") or "")
        if ev and not (ev.startswith("http") or ev.startswith("seed:")):
            problems.append(
                "%s: evidence must be a URL or 'seed:<supplier name>', got %r" % (label, ev))
    if problems:
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        die("alias-overlay.json failed validation (%d problem(s))" % len(problems))
    return entries, ambiguous, distinct


def build(quiet=False):
    seed = load_json(SEED, "supplier-seed.json")
    suppliers = seed.get("suppliers", [])
    if not suppliers:
        die("supplier-seed.json carries no suppliers - wrong file or a bad checkout")

    companies = {}   # canonical -> {"variants": set, "inSeed": bool, "notes": []}

    for s in suppliers:
        name = s.get("name")
        if not name:
            continue
        rec = companies.setdefault(
            name, {"variants": set(), "inSeed": True, "notes": []})
        rec["variants"].add(name)
        for a in s.get("aliases", []) or []:
            if a:
                rec["variants"].add(a)

    overlay_entries, declared_ambiguous, declared_distinct = read_overlay()
    for e in overlay_entries:
        canonical = e["canonical"]
        rec = companies.setdefault(
            canonical, {"variants": {canonical}, "inSeed": False, "notes": []})
        rec["variants"].add(canonical)
        for v in e["variants"]:
            rec["variants"].add(v)
        rec["notes"].append({
            "reason": e["reason"], "evidence": e["evidence"], "addedOn": e["addedOn"]})

    # Build the lookup layers, recording collisions rather than silently
    # letting one company win.
    exact, normal, stripped = {}, {}, {}
    for canonical, rec in companies.items():
        for v in rec["variants"]:
            exact.setdefault(v, set()).add(canonical)
            normal.setdefault(norm(v), set()).add(canonical)
            k = norm_stripped(v)
            if k:
                stripped.setdefault(k, set()).add(canonical)

    # Two different real companies CAN share a name - "GS Medical" is two
    # companies at Companies House. Those must stay ambiguous, never merged. But
    # a collision nobody has looked at is a bug, so the build fails until it is
    # declared in the overlay with its evidence.
    collisions = sorted(k for k, v in exact.items() if len(v) > 1)
    undeclared = [k for k in collisions if norm(k) not in declared_ambiguous]
    if undeclared:
        for k in undeclared:
            print("  - %r claimed by: %s" % (k, ", ".join(sorted(exact[k]))),
                  file=sys.stderr)
        die("%d name(s) claimed by more than one company and not declared in "
            "alias-overlay.json 'ambiguous'. Either they are the same company "
            "(merge them in the seed) or they are not (declare the ambiguity "
            "with evidence). Do not publish either name until this is settled."
            % len(undeclared))

    out = {
        "_notice": "GENERATED by company_alias.py - do not edit. "
                   "Edit alias-overlay.json, or the supplier's record in "
                   "msh-compare-data/data/supplier-seed.json, then rebuild.",
        "_sources": {"seed": SEED, "overlay": OVERLAY},
        "companyCount": len(companies),
        "variantCount": len(exact),
        "declaredAmbiguous": {k: v for k, v in sorted(declared_ambiguous.items())},
        "declaredDistinct": {k: sorted(v) for k, v in sorted(declared_distinct.items())},
        "companies": {
            c: {
                "variants": sorted(rec["variants"]),
                "inSeed": rec["inSeed"],
                "overlayNotes": rec["notes"],
            } for c, rec in sorted(companies.items())
        },
        "index": {
            "exact": {k: sorted(v) for k, v in exact.items()},
            "normalised": {k: sorted(v) for k, v in normal.items()},
            "stripped": {k: sorted(v) for k, v in stripped.items()},
        },
    }
    with open(REGISTRY, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
        fh.write("\n")
    if not quiet:
        print("Built %s" % REGISTRY)
        print("  %d companies, %d distinct name variants" % (len(companies), len(exact)))
        print("  %d from the supplier seed, %d overlay-only" % (
            sum(1 for r in companies.values() if r["inSeed"]),
            sum(1 for r in companies.values() if not r["inSeed"])))
    return out


def load_registry():
    if not os.path.exists(REGISTRY):
        return build(quiet=True)
    return load_json(REGISTRY, "company-alias-registry.json")


# ---------------------------------------------------------------- resolve

def resolve(name, reg):
    """Return (status, canonical_or_candidates, route).

    status is one of RESOLVED, AMBIGUOUS, UNRESOLVED.
    """
    idx = reg["index"]
    hits = idx["exact"].get(name)
    if hits:
        if len(hits) == 1:
            return "RESOLVED", hits[0], "exact name"
        return "AMBIGUOUS", hits, "exact name shared by two companies"
    hits = idx["normalised"].get(norm(name))
    if hits:
        if len(hits) == 1:
            return "RESOLVED", hits[0], "case/punctuation variant"
        return "AMBIGUOUS", hits, "case/punctuation variant"
    key = norm_stripped(name)
    hits = idx["stripped"].get(key) if key else None
    if hits:
        if len(hits) == 1:
            return "RESOLVED", hits[0], "legal-suffix/territory variant"
        return "AMBIGUOUS", hits, "legal-suffix/territory variant"
    return "UNRESOLVED", None, ""


# Ignored when scoring SUGGESTIONS only - never when matching. Half of medtech
# has "medical" in the name, so scoring on it suggests forty companies and helps
# with none of them.
GENERIC = set("""medical medicine medic healthcare health care clinical surgical
dental diagnostics diagnostic group holdings international global systems system
solutions technologies technology device devices products product equipment
services service supplies supply""".split())


def _tokens(s):
    return set(t for t in norm_stripped(s).split() if len(t) > 2 and t not in GENERIC)


def near_misses(name, reg, limit=5):
    """Human hints only. NEVER treat these as a match - that is the whole point."""
    want = _tokens(name)
    if not want:
        return []
    # Pairs somebody has already checked and found to be different companies.
    settled = set(reg.get("declaredDistinct", {}).get(norm(name), []))
    scored = []
    for canonical in reg["companies"]:
        if norm(canonical) in settled:
            continue      # already settled as a different company - don't re-ask
        have = _tokens(canonical)
        if not have:
            continue
        overlap = want & have
        if overlap:
            scored.append((len(overlap) / float(len(want | have)), canonical))
    scored.sort(reverse=True)
    return [c for score, c in scored[:limit] if score >= 0.34]


def report(names, as_json=False):
    reg = load_registry()
    results, worst = [], 0
    for name in names:
        status, value, route = resolve(name, reg)
        row = {"input": name, "status": status, "canonical": None,
               "route": route, "candidates": [], "suggestions": []}
        if status == "RESOLVED":
            row["canonical"] = value
        elif status == "AMBIGUOUS":
            row["candidates"] = value
            worst = max(worst, 2)
        else:
            row["suggestions"] = near_misses(name, reg)
            worst = max(worst, 1)
        results.append(row)

    if as_json:
        print(json.dumps(results, indent=1))
    else:
        for r in results:
            if r["status"] == "RESOLVED":
                print("OK          %-46s -> %s   (%s)" % (
                    r["input"], r["canonical"], r["route"]))
            elif r["status"] == "AMBIGUOUS":
                print("AMBIGUOUS   %-46s -> %s" % (
                    r["input"], " OR ".join(r["candidates"])))
                print("            Two companies claim this name. Do not publish it. "
                      "Decide which is meant and give it a distinct name.")
            else:
                print("UNRESOLVED  %s" % r["input"])
                if r["suggestions"]:
                    print("            Not a match - only names that look similar: %s"
                          % ", ".join(r["suggestions"]))
                print("            Confirm which company this is, then add the alias "
                      "to supplier-seed.json (preferred) or alias-overlay.json. "
                      "Until then it does not publish.")
    return worst


# ---------------------------------------------------------------- selftest

def selftest():
    """Prove the gate still catches what it was built for."""
    reg = load_registry()
    fails = []

    def expect(name, want_status, want_canonical=None):
        status, value, _ = resolve(name, reg)
        if status != want_status or (want_canonical and value != want_canonical):
            fails.append("%r -> %s/%s, expected %s/%s" % (
                name, status, value, want_status, want_canonical))

    # A name that is genuinely in the registry, in four source spellings.
    sample = None
    for c, rec in reg["companies"].items():
        if len(norm_stripped(c).split()) >= 1 and norm_stripped(c):
            sample = c
            break
    if sample:
        expect(sample, "RESOLVED", sample)
        expect(sample.upper(), "RESOLVED", sample)
        expect(sample + " Limited", "RESOLVED", sample)
        expect(sample + " UK Ltd.", "RESOLVED", sample)

    # Nonsense must NOT resolve. If this ever passes, fuzzy matching has crept in.
    expect("Zzqx Holdings of Nowhere", "UNRESOLVED")
    # A near-miss must not be silently merged.
    expect("Medical", "UNRESOLVED") if "Medical" not in reg["index"]["exact"] else None

    # Normalisation must not flatten two different companies into one key.
    if norm_stripped("Pentax Medical UK Limited") == norm_stripped("Pentax UK Limited"):
        fails.append("normalisation merges 'Pentax Medical UK' with 'Pentax UK'")

    if fails:
        for f in fails:
            print("  - %s" % f, file=sys.stderr)
        die("selftest failed (%d)" % len(fails))
    print("selftest passed - %d companies, %d variants, no fuzzy matching" % (
        reg["companyCount"], reg["variantCount"]))
    return 0


# ---------------------------------------------------------------- cli

def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, rest = argv[1], argv[2:]
    as_json = "--json" in rest
    rest = [a for a in rest if a != "--json"]

    if cmd == "build":
        build()
        return 0
    if cmd == "selftest":
        return selftest()
    if cmd == "resolve":
        if not rest:
            die("resolve needs at least one name")
        return report(rest, as_json)
    if cmd == "check":
        if not rest:
            die("check needs a file path, or - for stdin")
        src = sys.stdin if rest[0] == "-" else open(rest[0])
        names = [l.strip() for l in src if l.strip() and not l.startswith("#")]
        if rest[0] != "-":
            src.close()
        if not names:
            print("Nothing to check.")
            return 0
        code = report(names, as_json)
        if not as_json:   # --json must stay parseable - no trailing prose
            print("\n%d name(s) checked." % len(names))
        return code
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
