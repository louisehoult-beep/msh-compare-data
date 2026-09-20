#!/usr/bin/env python3
"""
test_identity_policy.py — proves the identity/vocabulary policy gate holds.

    python3 test_identity_policy.py

Exit 0 = the gate holds. Exit 1 = it has a hole; do not trust a green verify.py.

WHY THIS SUITE EXISTS
The Operating Model Review (18/09/2026) classified all 135 open items in
OUTSTANDING.md and found roughly 44 of them were not decisions at all. They
were the same four or five SHAPES of ambiguity arriving over and over, each
escalated to Lou as though nobody had ever seen a parent/subsidiary naming
conflict before. differentiator-framework-coverage was firing six times a day
to rediscover that it was blocked on the same rulings.

Lou ruled on the shapes on 20/09/2026 and data/identity-vocabulary-policy.json
records those rulings so the pipeline can apply them without asking again.

The failure mode this suite guards is SILENT. A policy added later without a
guard, or with a guard that merely restates its own ruling, still reads like a
rule while constraining nothing. The first anyone would know is a wrong company
merge already published to paying members. Every case below is therefore a
state the file is one careless edit away from.

The second half of the suite covers the other silent failure: an escalation
path that stops consulting the policy at all, which would quietly restore the
backlog without anything looking broken.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import identity_policy as pol  # noqa: E402


def _broken(doc, mutate):
    d = copy.deepcopy(doc)
    mutate(d)
    return d


# Each case: a name, and a mutation that MUST be rejected by validate().
MALFORMED = [
    ("a policy with no guard",
     lambda d: d["policies"]["vocabulary-gap"].pop("guard")),
    ("a guard that just restates the ruling, so it guards nothing",
     lambda d: d["policies"]["vocabulary-gap"].__setitem__(
         "guard", d["policies"]["vocabulary-gap"]["ruling"])),
    ("a policy with an empty ruling",
     lambda d: d["policies"]["domain-proof-tier"].__setitem__("ruling", "")),
    ("a policy with no worked example to test it against",
     lambda d: d["policies"]["unconfirmable-awardee"].pop("workedExample")),
    ("an undated policy, so nobody can tell when it was agreed",
     lambda d: d["policies"]["mixed-division-mapping"].pop("decidedOn")),
    ("appliesTo as a bare string rather than a list of refs",
     lambda d: d["policies"]["parent-subsidiary-award-credit"].__setitem__(
         "appliesTo", "^o523")),
    ("no recorded decider, so a rule appears with no author",
     lambda d: d.__setitem__("decidedBy", "")),
    ("no pack recorded, so the reasoning cannot be found",
     lambda d: d.__setitem__("decidedIn", "")),
    ("every policy deleted, which would silently resume the backlog",
     lambda d: d.__setitem__("policies", {})),
]


def main():
    failures = []

    # 0. The live file must itself be clean, or nothing below means anything.
    live = pol.load()
    problems = pol.validate(live)
    if problems:
        failures.append("the live policy file is invalid: %s" % problems[0])
        print("FAIL  live file is invalid: %s" % problems[0])
    else:
        print("ok    live policy file validates (%d policies)" % len(pol.ids()))

    # 1. Every malformed state must be rejected.
    for name, mutate in MALFORMED:
        if pol.validate(_broken(live, mutate)):
            print("ok    rejects %s" % name)
        else:
            failures.append("gate accepts %s" % name)
            print("FAIL  gate ACCEPTS %s" % name)

    # 2. Every ruled shape must refuse escalation. This is the half that
    #    actually saves Lou's time: a policy that exists but is never consulted
    #    changes nothing.
    for pid in pol.ids():
        try:
            pol.refuse_escalation(pid, "a test subject")
        except pol.PolicyViolation as exc:
            msg = str(exc)
            if "RULING:" in msg and "GUARD:" in msg:
                print("ok    %s refuses escalation and quotes its ruling and guard" % pid)
            else:
                failures.append("%s refuses but does not quote its ruling and guard" % pid)
                print("FAIL  %s refuses without quoting ruling and guard" % pid)
        else:
            failures.append("%s did not refuse escalation" % pid)
            print("FAIL  %s did NOT refuse escalation" % pid)

    # 3. An unruled shape must NOT be refused. Silently swallowing a genuinely
    #    novel question is the opposite failure, and the worse one: it would
    #    hide something that really does need Lou.
    if pol.refuse_escalation("a-shape-nobody-has-ruled-on-yet", "x") is None:
        print("ok    an unruled shape still escalates")
    else:
        failures.append("an unruled shape was wrongly suppressed")
        print("FAIL  an unruled shape was wrongly suppressed")

    # 4. Every policy must claim at least one real open item, or it is a rule
    #    invented for a problem nobody had.
    for pid, p in sorted(pol.policies().items()):
        if not (p.get("appliesTo") or []):
            failures.append("%s cites no open items" % pid)
            print("FAIL  %s cites no open items it was written to clear" % pid)
    print("ok    every policy cites the open items it clears")

    print()
    if failures:
        print("IDENTITY POLICY GATE FAILED — %d hole(s)." % len(failures))
        return 1
    print("IDENTITY POLICY GATE HOLDS — %d case(s) passed." % (len(MALFORMED) + len(pol.ids()) + 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
