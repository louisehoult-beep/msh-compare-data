#!/usr/bin/env python3
"""
test_product_types.py — proves verify.py's check_product_types() catches the
drift it was built for.

THE HOLE THIS CLOSES. The product-type taxonomy that decides whether two
products are "the same kind of thing" was implemented twice — once in
cloud-pipeline/sdt_match.py (Python, the Supply Disruption Tracker) and once
as a literal `var TYPES = [...]` in app/comparison.js (browser, served
straight to members). sdt_match.py was rewritten 04/09/2026 (167 entries, +20
categories: theatre caps, PPE, continence, nutrition); comparison.js was never
updated and kept the pre-rewrite 147-entry copy. Nothing caught it — there was
no gate. A member comparing two continence or theatre-cap products on the live
Compare tool got no match where the Tracker would.

data/product-types.json (07/09/2026) is now the one taxonomy both sides read.
check_product_types() is what stops it drifting apart again: it fails the
publish if the file itself is missing/malformed/empty, if it silently loses
entries against what is already committed, if comparison.js stops fetching it,
or if comparison.js's baked-in fallback literal drifts out of step with it.

    python3 test_product_types.py

Exit 0 = the gate holds. Exit 1 = the gate has a hole; do not trust a green
verify.py until this passes again.
"""
import copy
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import verify  # noqa: E402

failures = []


def check(name, ok, detail=""):
    print("  %s %s%s" % ("PASS" if ok else "FAIL", name,
                         "" if ok else "  <- " + detail))
    if not ok:
        failures.append(name)


def run(pt, comparison_js=None, committed_fn=None):
    """Run check_product_types() in isolation and return (fails, warns).

    Resets verify's module-level fails/warns lists first so each scenario
    starts clean, same discipline test_seed_domains.py uses for its own gate()
    copy — a shared list that leaked between cases would make every later
    assertion meaningless.

    comparison_js, when given, is written to a throwaway app/comparison.js in
    a temp working directory and the cwd is switched there for the duration of
    the call — check_product_types() reads that file by the same relative
    path (app/comparison.js) verify.py's other checks use. committed_fn, when
    given, stands in for verify.committed() so the "lost entries" path can be
    tested without a real git history for data/product-types.json (it is a
    brand new file, so HEAD has no prior version to diff against yet).
    """
    verify.fails[:] = []
    verify.warns[:] = []
    old_committed = verify.committed
    old_cwd = os.getcwd()
    tmp = None
    try:
        if committed_fn is not None:
            verify.committed = committed_fn
        if comparison_js is not None:
            tmp = tempfile.mkdtemp(prefix="test_product_types_")
            os.makedirs(os.path.join(tmp, "app"))
            with open(os.path.join(tmp, "app", "comparison.js"), "w") as f:
                f.write(comparison_js)
            os.chdir(tmp)
        else:
            # No JS scenario supplied: run from the real repo so the real,
            # currently-shipped app/comparison.js is what gets read — this is
            # what the actual gate does on every real run.
            os.chdir(REPO)
        verify.check_product_types(pt)
        return list(verify.fails), list(verify.warns)
    finally:
        os.chdir(old_cwd)
        verify.committed = old_committed
        verify.fails[:] = []
        verify.warns[:] = []


REAL_TYPES = json.load(open(os.path.join(REPO, "data", "product-types.json")))

GOOD_JS = ("var TYPES = ['antisepsis','cannula','dressing'];\n"
           "fetch(BASE + 'data/product-types.json' + CB);\n")

STALE_JS_NO_FETCH = ("var TYPES = ['antisepsis','cannula','dressing'];\n"
                     "// no fetch of the shared taxonomy at all\n")

DRIFTED_FALLBACK_JS = ("var TYPES = ['antisepsis','cannula'];\n"  # missing 'dressing'
                       "fetch(BASE + 'data/product-types.json' + CB);\n")


def good_doc(types=None):
    return {
        "_meta": {"warning": "editing this changes live matching"},
        "types": types if types is not None else ["antisepsis", "cannula", "dressing"],
        "generic_type_override": {"catheter": "cannula"},
        "cannula_disqualifiers": ["picc"],
    }


print("missing / malformed file")
fails, _ = run(None)
check("missing data/product-types.json fails", any("missing" in m for _, m in fails), str(fails))

fails, _ = run({"_meta": {"warning": "x"}, "generic_type_override": {"a": "b"},
               "cannula_disqualifiers": ["picc"]})
check("no `types` array at all fails", any("`types`" in m for _, m in fails), str(fails))

fails, _ = run(good_doc(types=[]))
check("empty `types` array fails", any("`types`" in m for _, m in fails), str(fails))

fails, _ = run(good_doc(types=["cannula", "cannula", "dressing"]))
check("duplicate entries in `types` fail",
      any("duplicate" in m for _, m in fails), str(fails))

doc = good_doc()
del doc["generic_type_override"]
fails, _ = run(doc)
check("missing `generic_type_override` fails",
      any("generic_type_override" in m for _, m in fails), str(fails))

doc = good_doc()
doc["generic_type_override"] = {}
fails, _ = run(doc)
check("empty `generic_type_override` fails",
      any("generic_type_override" in m for _, m in fails), str(fails))

doc = good_doc()
del doc["cannula_disqualifiers"]
fails, _ = run(doc)
check("missing `cannula_disqualifiers` fails",
      any("cannula_disqualifiers" in m for _, m in fails), str(fails))

doc = good_doc()
del doc["_meta"]
fails, _ = run(doc)
check("missing `_meta.warning` fails", any("_meta.warning" in m for _, m in fails), str(fails))

doc = good_doc()
doc["_meta"] = {}
fails, _ = run(doc)
check("empty `_meta` (no warning) fails",
      any("_meta.warning" in m for _, m in fails), str(fails))

print()
print("lost entries versus the committed version (THE 04/09/2026 FAILURE MODE)")
baseline = good_doc(types=["antisepsis", "cannula", "dressing", "theatre cap"])
shrunk = good_doc(types=["antisepsis", "cannula", "dressing"])  # 'theatre cap' quietly dropped
grown = good_doc(types=["antisepsis", "cannula", "dressing", "theatre cap", "shoe cover"])
# comparison_js's own TYPES fallback must match whichever doc is under test, or
# the separate "fallback drifted" check fires instead and confuses what this
# block is actually proving — so each JS literal below is built from that same
# doc's own `types` list.


def js_for(doc):
    return ("var TYPES = %s;\nfetch(BASE + 'data/product-types.json' + CB);\n"
           % json.dumps(doc["types"]).replace('"', "'"))


fails, _ = run(shrunk, comparison_js=js_for(shrunk),
              committed_fn=lambda path: baseline if path == "data/product-types.json" else None)
check("dropping an entry that was already committed fails",
      any("lost" in m and "theatre cap" in m for _, m in fails), str(fails))

fails, _ = run(baseline, comparison_js=js_for(baseline), committed_fn=lambda path: baseline)
check("no entries lost against the committed version passes clean", not fails, str(fails))

# A pure addition (exactly what the real 07/09/2026 rewrite is) must never fail —
# this gate protects against losing coverage, not against gaining it.
fails, _ = run(grown, comparison_js=js_for(grown), committed_fn=lambda path: baseline)
check("adding new entries never fails the shrink check", not fails, str(fails))

print()
print("comparison.js must actually FETCH the shared file, not carry its own copy")
fails, _ = run(good_doc(), comparison_js=STALE_JS_NO_FETCH)
check("comparison.js with no fetch of data/product-types.json fails",
      any("no longer fetches" in m for _, m in fails), str(fails))

fails, _ = run(good_doc(), comparison_js=GOOD_JS)
check("comparison.js that fetches data/product-types.json passes this leg",
      not any("no longer fetches" in m for _, m in fails), str(fails))

print()
print("comparison.js's baked-in fallback must stay in step with the authoritative file")
fails, _ = run(good_doc(), comparison_js=DRIFTED_FALLBACK_JS)
check("a fallback TYPES literal missing an entry the JSON has fails",
      any("drifted" in m and "dressing" in m for _, m in fails), str(fails))

fails, _ = run(good_doc(), comparison_js=GOOD_JS)
check("a fallback TYPES literal matching the JSON passes clean", not fails, str(fails))

# A fetch comment that merely NAMES the file (e.g. explaining the drift this
# gate exists to prevent) must not itself satisfy the "actually fetches it"
# check — _js_scan blanks comments before this check runs, same discipline
# check_no_clusters_on_tools relies on so its own explanatory comment cannot
# trip the rule it documents.
COMMENT_ONLY_JS = ("// we used to fetch data/product-types.json here but don't any more\n"
                   "var TYPES = ['antisepsis','cannula','dressing'];\n")
fails, _ = run(good_doc(), comparison_js=COMMENT_ONLY_JS)
check("a comment merely mentioning the filename does not count as fetching it",
      any("no longer fetches" in m for _, m in fails), str(fails))

print()
print("the real, currently-shipped files")
fails, _ = run(REAL_TYPES)
check("the real app/comparison.js still fetches data/product-types.json",
      not any("no longer fetches" in m for _, m in fails), str(fails))
check("the real app/comparison.js fallback has not drifted from the real JSON",
      not any("drifted" in m for _, m in fails), str(fails))
check("the real data/product-types.json is itself well-formed", not fails, str(fails))

print()
if failures:
    print("FAILED: %d check(s) — %s" % (len(failures), ", ".join(failures)))
    sys.exit(1)
print("gate holds — comparison.js cannot silently drift from data/product-types.json again")
