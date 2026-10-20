#!/usr/bin/env python3
"""Fixture-based tests for scripts/refresh_ai_airlock.py. No network."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import refresh_ai_airlock as r  # noqa: E402

PILOT_BODY = """<div class="govspeak"><h2 id="overview">Overview</h2><p>intro</p>
<h2 id="the-selected-sandbox-candidates">The selected sandbox candidates</h2>
<h3>Federated AI Monitoring Service (FAMOS): A virtual environment developed by Newtons Tree Ltd</h3><p>drift text</p>
<h3>AI platform interoperating with existing clinical systems: OncoFlow</h3><p>text</p>
<h3>Artificial intelligence to predict risk in COPD patients: Developed by Lenus Health Ltd</h3>
<p>Unfortunately, Lenus Health have withdrawn from the AI Airlock pilot programme.</p>
<h3>Some new theme: Developed by Unknown Co</h3><p>text</p>
<h2 id="ai-airlock-partners">AI Airlock Partners</h2><h3>should be ignored</h3></div>"""

P2_BODY = """<div class="govspeak"><h2>Overview</h2>
<p><strong>Simulation environment:</strong> a roundtable workshop. Regulatory challenge words here.</p>
<h2>Regulatory challenge 1: Scope of intended use extension and validation</h2>
<h3>Multi-environment candidate:</h3>
<p><strong>TORTUS</strong></p><p>body</p>
<h3>Simulation candidate:</h3>
<h3>Nu &amp; Aegis AI Conversational &amp; Monitoring System - Numan</h3><p>body</p>
<h2>Regulatory challenge 2: AI-powered in-vitro diagnostic devices</h2>
<h3>Simulation candidate:</h3>
<h3>Octopath</h3><p>body</p>
<h3>Eye2Gene – Eye2Gene Ltd (and Hardian Health)</h3><p>en dash heading</p>
<h2>AI Airlock Partners</h2><ul><li>MHRA</li></ul></div>"""

GROUPS = [
    {"title": "AI Airlock programme reporting",
     "body": "<p>The second phase of the Airlock completed in May 2026 and focused on 3 innovators across 2 regulatory challenges. "
             "The pilot programme closed in April 2025 and focused on four products across a range.</p>"},
    {"title": "AI Airlock innovators",
     "body": "<p>Since its launch in 2024 the AI Airlock has now completed 2 testing phases with 11 innovators across 7 regulatory challenges. \xa0</p>"},
]


class Pilot(unittest.TestCase):
    def setUp(self):
        self.m = r.parse_pilot(PILOT_BODY)

    def test_members_and_names(self):
        self.assertEqual([x["company"] for x in self.m], ["Newtons Tree Ltd", "OncoFlow", "Lenus Health Ltd", None])
        self.assertEqual(self.m[0]["product"], "Federated AI Monitoring Service (FAMOS)")

    def test_withdrawn_and_unknown(self):
        self.assertEqual(self.m[2]["status"], "withdrawn")
        self.assertEqual(self.m[0]["status"], "participating")
        self.assertTrue(self.m[3]["needsReview"])
        self.assertIsNone(self.m[3]["product"])

    def test_not_resolved(self):
        self.assertTrue(all(x["entityResolved"] is False for x in self.m))

    def test_h3_after_partners_ignored(self):
        self.assertEqual(len(self.m), 4)


class Phase2(unittest.TestCase):
    def setUp(self):
        self.m = r.parse_phase2(P2_BODY)

    def test_bold_paragraph_candidate_and_roles(self):
        self.assertEqual([x["company"] for x in self.m],
                         ["TORTUS", "Numan", "Octopath", "Eye2Gene Ltd (and Hardian Health)"])
        self.assertEqual([x["testingRole"] for x in self.m],
                         ["multi-environment", "simulation", "simulation", "simulation"])

    def test_challenge_numbers_and_theme(self):
        self.assertEqual([x["challengeNumber"] for x in self.m], [1, 1, 2, 2])
        self.assertTrue(self.m[0]["theme"].startswith("Regulatory challenge 1: Scope of intended use"))

    def test_entities_unresolved_and_original_dash_kept(self):
        self.assertTrue(all(x["entityResolved"] is False for x in self.m))
        self.assertIn("–", self.m[3]["heading"])  # MHRA's own spelling preserved
        self.assertEqual(self.m[1]["product"], "Nu & Aegis AI Conversational & Monitoring System")


class CountCheck(unittest.TestCase):
    def phases(self, n_pilot, n_p2):
        def mem(i, **kw):
            d = {"status": "participating", "theme": "t%d" % i, "challengeNumber": 1 + i % 3}
            d.update(kw)
            return d
        return [{"phase": "Pilot", "members": [mem(i) for i in range(n_pilot)]},
                {"phase": "Phase 2", "members": [mem(i) for i in range(n_p2)]}]

    def test_statement_extraction(self):
        s = r.collection_statements(GROUPS)
        self.assertEqual((s["all"]["innovators"], s["all"]["challenges"]), (11, 7))
        self.assertEqual((s["phase2"]["innovators"], s["phase2"]["challenges"]), (3, 2))
        self.assertEqual(s["pilotProducts"]["products"], 4)
        self.assertTrue(s["all"]["text"].startswith("Since its launch"))

    def test_disagreement_recorded_not_corrected(self):
        s = r.collection_statements(GROUPS)
        c = r.count_check(self.phases(4, 5), s)
        self.assertFalse(c["allAgree"])
        self.assertEqual(c["ours"]["phase2Members"], 5)  # our count is untouched
        row = next(x for x in c["checks"] if x["check"].startswith("phase 2"))
        self.assertEqual((row["statedInnovators"], row["ourInnovators"], row["agrees"]), (3, 5, False))

    def test_missing_statement_is_unknown_not_agree(self):
        c = r.count_check(self.phases(4, 7), {})
        self.assertFalse(c["allAgree"])
        self.assertTrue(all(x["agrees"] is None for x in c["checks"]))


class Build(unittest.TestCase):
    def doc(self):
        coll = {"public_updated_at": "2026-10-06T00:01:56+01:00", "details": {"collection_groups": GROUPS}}
        page = lambda d: {"public_updated_at": d, "details": {"body": ""}}  # noqa: E731
        return r.build(coll, page("2025-02-28T09:18:01+00:00"),
                       {"public_updated_at": "2025-02-28T09:18:01+00:00", "details": {"body": PILOT_BODY}},
                       {"public_updated_at": "2025-10-16T00:00:00+01:00", "details": {"body": P2_BODY}},
                       {"public_updated_at": "2026-07-27T16:02:06+01:00", "details": {"body": "no products named"}},
                       "2026-10-20")

    def test_shape(self):
        d = self.doc()
        for k in ("rule", "source", "generated", "dataAsOf", "phases", "counts"):
            self.assertIn(k, d)
        self.assertEqual([p["phase"] for p in d["phases"]], ["Pilot", "Phase 2", "Phase 3"])
        self.assertEqual(d["dataAsOf"], "2026-10-06")
        self.assertEqual(d["phases"][0]["pageUpdated"], "2025-02-28")

    def test_phase3_empty_with_note(self):
        p3 = self.doc()["phases"][2]
        self.assertEqual(p3["members"], [])
        self.assertIn("not announced", p3["note"])

    def test_counts_and_review_flag(self):
        c = self.doc()["counts"]
        self.assertEqual(c["byPhase"], {"Pilot": 4, "Phase 2": 4, "Phase 3": 0})
        self.assertEqual(c["needsReview"], 1)
        self.assertEqual(c["totalParticipating"], 7)

    def test_report_names_no_products(self):
        self.assertFalse(self.doc()["phases"][1]["programmeReport"]["namesProductsOnPage"])


if __name__ == "__main__":
    unittest.main()
