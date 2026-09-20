#!/usr/bin/env python3
"""identity_policy.py — read data/identity-vocabulary-policy.json before escalating.

WHY THIS EXISTS
    The Operating Model Review (18/09/2026) classified all 135 open items in
    OUTSTANDING.md and found ~44 of them were not decisions at all: they were
    the same four or five SHAPES of ambiguity arriving over and over, each one
    escalated to Lou as though nobody had ever seen a parent/subsidiary naming
    conflict before. differentiator-framework-coverage's own spec had already
    said it plainly: "most runs end 'no coverage movement, the remaining
    blocker is a ruling for Lou' ... it is starved of decisions, not of run
    slots."

    Lou ruled on the five shapes on 20/09/2026. This module is the half that
    makes those rulings load-bearing. A policy file nothing reads is a
    document; a policy file every escalation path must consult is a gate.

HOW TO USE IT
    Before writing "needs a ruling" into OUTSTANDING.md, call:

        import identity_policy as pol
        hit = pol.match("parent-subsidiary-award-credit")
        if hit:
            ...apply hit["ruling"], observe hit["guard"], do NOT escalate...

    Or, to fail loudly when a script is about to escalate something already
    ruled on:

        pol.refuse_escalation("vocabulary-gap", "Henleys ECG accessories")

    Escalate ONLY when no policy matches, and then escalate the SHAPE, not the
    single company: one ruling should answer every future case of it.

ADDING A POLICY
    Only from a dated ruling by Lou, recorded in a decision pack, with a guard
    naming what the policy must never be used to do. Never widen an existing
    policy to make an awkward case fit — if it does not match, that is the
    signal to ask for a new ruling, not to stretch an old one.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PATH = os.path.join(ROOT, "data", "identity-vocabulary-policy.json")

# Every policy must carry these. verify.py checks the same list, so a policy
# added without a guard, or without the ruling that justifies it, fails the
# gate rather than silently becoming a rule nobody agreed.
REQUIRED_FIELDS = ("title", "shape", "ruling", "guard", "appliesTo",
                   "workedExample", "decidedOn")


class PolicyViolation(Exception):
    """Raised when a caller tries to escalate a question already ruled on."""


def load():
    """Return the whole policy document. Raises if it is missing: a pipeline
    that cannot read its own policy must stop, not quietly escalate again."""
    with open(PATH) as f:
        return json.load(f)


def policies():
    return load()["policies"]


def ids():
    return sorted(policies())


def match(policy_id):
    """Return the policy for this shape, or None if there is no ruling yet.

    None is a real answer: it means this genuinely needs Lou, and the caller
    should escalate the SHAPE.
    """
    return policies().get(policy_id)


def refuse_escalation(policy_id, subject):
    """Call this on the escalation path. If a policy covers the shape, refuse.

    `subject` is whatever was about to be written into OUTSTANDING.md, and is
    quoted back so the fix is obvious from the traceback alone.
    """
    hit = match(policy_id)
    if hit is None:
        return None
    raise PolicyViolation(
        "Refusing to escalate %r: shape %r was already ruled on by Lou on %s.\n"
        "  RULING: %s\n"
        "  GUARD:  %s\n"
        "Apply the ruling. Escalate only if the fact pattern genuinely does not "
        "match this shape, and then escalate the shape, not this one company."
        % (subject, policy_id, hit["decidedOn"], hit["ruling"], hit["guard"]))


def validate(doc=None):
    """Return a list of problems. Empty list means the file is well formed.

    Shared with verify.py so the gate and this module can never disagree about
    what a valid policy is.
    """
    problems = []
    doc = doc if doc is not None else load()

    for key in ("purpose", "rule", "decidedOn", "decidedBy", "decidedIn", "policies"):
        if not doc.get(key):
            problems.append("top-level %r is missing or empty" % key)

    pols = doc.get("policies") or {}
    if not pols:
        problems.append("no policies defined")

    for pid, p in sorted(pols.items()):
        if not isinstance(p, dict):
            problems.append("%s is not an object" % pid)
            continue
        for field in REQUIRED_FIELDS:
            if not p.get(field):
                problems.append("%s is missing %r" % (pid, field))
        # A guard that just restates the ruling protects nothing. This does not
        # prove a guard is meaningful, but it does catch the copy-paste case.
        if p.get("guard") and p.get("guard") == p.get("ruling"):
            problems.append("%s: guard is identical to ruling, so it guards nothing" % pid)
        if p.get("appliesTo") is not None and not isinstance(p["appliesTo"], list):
            problems.append("%s: appliesTo must be a list of item refs" % pid)
    return problems


def main(argv):
    if len(argv) > 1 and argv[1] == "--check":
        problems = validate()
        for m in problems:
            print("FAIL  %s" % m)
        print("%d problem(s)" % len(problems))
        return 1 if problems else 0

    doc = load()
    print("Identity & vocabulary policy — decided %s by %s" % (doc["decidedOn"], doc["decidedBy"]))
    print("Recorded in: %s\n" % doc["decidedIn"])
    for pid, p in sorted(doc["policies"].items()):
        print("== %s" % pid)
        print("   %s" % p["title"])
        print("   SHAPE:  %s" % p["shape"])
        print("   RULING: %s" % p["ruling"])
        print("   GUARD:  %s" % p["guard"])
        print("   covers %d open item(s): %s" % (len(p.get("appliesTo") or []),
                                                 ", ".join(p.get("appliesTo") or []) or "none"))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
