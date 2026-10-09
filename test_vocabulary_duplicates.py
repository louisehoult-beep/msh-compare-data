#!/usr/bin/env python3
"""
test_vocabulary_duplicates.py — proves check_vocabulary_duplicates() catches
the synonym-duplicate fork it was built for.

THE HOLE THIS CLOSES (^o572). On 20/09/2026 two sessions working in parallel
each independently added the same three gated-vocabulary concepts —
radiotherapy positioning, dosimetry/QA, ECG accessories — under DIFFERENT
keys: one added oncology:posn / oncology:dosim / cardiology:ecgacc, the other
added oncology:pos / oncology:dosqa / cardiology:cons. `verify.py` did not
catch it — check_differentiator() only proves compare-suppliers.json and
differentiator-category-map.json agree with EACH OTHER, and a fork added
consistently to both files agrees with itself perfectly while still being
wrong. Only a cross-session chat message stopped it landing.

    python3 test_vocabulary_duplicates.py

Exit 0 = the gate holds. Exit 1 = the gate has a hole; do not trust a green
verify.py until this passes again.

WHAT "HOLDS" MEANS HERE
The gate is a WARN, never a FAIL (see check_vocabulary_duplicates()'s own
docstring for why — same house reasoning as check_source_links()). So this
suite does not prove verify.py exits non-zero on a duplicate; it proves the
duplicate is SURFACED as a warning a human will actually see, and — just as
important — that genuinely distinct types sitting close together in wording
are NOT flagged, because a gate that cries wolf on real, deliberate
near-neighbours gets its threshold loosened the first time it does, which is
how the next fork lands unnoticed.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import verify  # noqa: E402

failures = []


def check(name, ok, detail=""):
    print("  %s %s%s" % ("PASS" if ok else "FAIL", name,
                         "" if ok else "  <- " + detail))
    if not ok:
        failures.append(name)


def run(vocab):
    """Run check_vocabulary_duplicates() in isolation and return the warns.

    Resets verify's module-level fails/warns lists first, same discipline
    test_product_types.py uses for its own gate() copy — a shared list that
    leaked between cases would make every later assertion meaningless.
    """
    verify.fails[:] = []
    verify.warns[:] = []
    try:
        verify.check_vocabulary_duplicates(vocab)
        return list(verify.fails), list(verify.warns)
    finally:
        verify.fails[:] = []
        verify.warns[:] = []


def vocab(specialities):
    return {"specialities": specialities}


def spec(types):
    return {"types": types}


print("missing / empty vocabulary is a no-op, not a crash")
fails, warns = run(None)
check("None vocab produces no fails/warns", not fails and not warns, str((fails, warns)))
fails, warns = run({})
check("empty vocab produces no fails/warns", not fails and not warns, str((fails, warns)))
fails, warns = run(vocab({"oncology": spec({})}))
check("a speciality with no types produces no fails/warns", not fails and not warns,
      str((fails, warns)))

print()
print("the gate never FAILs — it is a policy judgement, not a mechanical fact")
exact_dupe = vocab({"oncology": spec({
    "posn": "Radiotherapy patient positioning and immobilisation devices",
    "pos": "Radiotherapy patient positioning and immobilisation devices",
})})
fails, warns = run(exact_dupe)
check("even a byte-identical duplicate label only warns, never fails",
      not fails and warns, str((fails, warns)))

print()
print("the three 20/09 near-misses, reconstructed")

# oncology:posn vs oncology:pos — same concept, "devices" dropped by the
# second session. This is the actual shape of the incident: one session's
# wording is a near-subset of the other's.
posn_pos = vocab({"oncology": spec({
    "posn": "Radiotherapy patient positioning and immobilisation devices",
    "pos": "Radiotherapy patient positioning and immobilisation",
})})
fails, warns = run(posn_pos)
check("oncology:posn / oncology:pos is flagged as a likely duplicate",
      any("posn" in m and "pos" in m for _, m in warns), str(warns))

# oncology:dosim vs oncology:dosqa — same concept, reordered and re-punctuated,
# exactly the kind of independent re-wording two sessions produce for one idea.
dosim_dosqa = vocab({"oncology": spec({
    "dosim": "Dosimetry and QA devices",
    "dosqa": "QA and dosimetry devices",
})})
fails, warns = run(dosim_dosqa)
check("oncology:dosim / oncology:dosqa is flagged as a likely duplicate",
      any("dosim" in m and "dosqa" in m for _, m in warns), str(warns))

# cardiology:ecgacc vs cardiology:cons — same concept, one session's longer
# phrasing against the other's shorter one.
ecgacc_cons = vocab({"cardiology": spec({
    "ecgacc": "ECG cables, accessories and recording consumables",
    "cons": "ECG cables, accessories and consumables",
})})
fails, warns = run(ecgacc_cons)
check("cardiology:ecgacc / cardiology:cons is flagged as a likely duplicate",
      any("ecgacc" in m and "cons" in m for _, m in warns), str(warns))

print()
print("genuinely distinct types must NOT be flagged (the other half of the boundary)")

# Real, live, deliberately opposite types in the same speciality — the
# closest real pair anywhere in the actual vocabulary (0.67 word overlap on
# the same similarity measure the gate uses), included here so the threshold
# can never be tightened enough to catch the real duplicates above without
# this case failing first.
opposite_meaning = vocab({"monitoring": spec({
    "gen": "Non-specialist monitoring",
    "spec": "Specialist monitoring",
})})
fails, warns = run(opposite_meaning)
check("monitoring:gen / monitoring:spec (opposite meanings) is NOT flagged",
      not any("gen" in m and "spec" in m for _, m in warns), str(warns))

# Same key, same word, different speciality, different equipment entirely —
# proves the gate is scoped to WITHIN a speciality and does not fire just
# because two unrelated types happen to share a code or a word.
cross_speciality = vocab({
    "oncology": spec({"dosim": "Dosimetry and QA devices"}),
    "nuclear": spec({"dosim": "Personnel & environmental radiation dosimetry"}),
})
fails, warns = run(cross_speciality)
check("oncology:dosim / nuclear:dosim (same code, cross-speciality) is NOT flagged",
      not warns, str(warns))

# Two unrelated devices that happen to share one clinical-sounding word.
unrelated = vocab({"imaging": spec({
    "ct": "CT scanners",
    "mri": "MRI scanners",
})})
fails, warns = run(unrelated)
check("imaging:ct / imaging:mri (unrelated modalities) is NOT flagged", not warns, str(warns))

print()
print("the real, currently-shipped vocabulary")
real = json.load(open(os.path.join(REPO, "data", "compare-suppliers.json")))
fails, warns = run(real)
check("the live gated vocabulary clears the gate with no near-duplicate warnings",
      not fails and not warns, str((fails, warns)))

print()
if failures:
    print("FAILED: %d check(s) — %s" % (len(failures), ", ".join(failures)))
    sys.exit(1)
print("gate holds — a synonym fork like 20/09's is surfaced, real near-neighbours are not")
