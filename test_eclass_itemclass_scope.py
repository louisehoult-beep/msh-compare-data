#!/usr/bin/env python3
"""
test_eclass_itemclass_scope.py — one eClass code is not one kind of product.

Found 30/09/2026 in a live QA of the Supply Disruption Tracker (page 3641):
three Boston Scientific ureteral stents (FUQ763, FUQ4380, FUQ4461) sat in the
Continence filter. eClass FUQ holds bowel-irrigation kits under NHS Supply
Chain itemClass "23- Rehabilitation and Community" AND ureteral stents under
"22- Medical Technology". build_eclass_map.py pooled every observation per
code, so seven irrigation kits voted the stents into continence:bowel. The same
pooling filed 38 Boston Scientific guiding/drainage catheters (FVA) as
monitoring sensors on three arterial-line observations from another itemClass.

These tests pin the fix: only same-itemClass observations vote, each entry
records the itemClass it may categorise, a mapping needs at least one suspended
line that is the same kind of product as its evidence, and the three stents are
decided per line as ureteric stents.

  python3 test_eclass_itemclass_scope.py     exit 0 = the pooling cannot recur
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import build_eclass_map as b  # noqa: E402

IC22 = "22- Medical Technology"
IC23 = "23- Rehabilitation and Community"


def _obs(npc, ec, ic, cat, desc, overlap=3):
    return {"npc": npc, "eclass": ec, "itemclass": ic, "cat": cat,
            "overlap": overlap, "nhsscDesc": desc}


FUQ_OBS = [_obs("FUQ85047", "FUQ", IC23, "continence:bowel", "Bowel management system Pre-loaded")]
FUQ_OBS += [_obs("FUQ8505%d" % i, "FUQ", IC23, "continence:bowel",
                 "Anal Irrigation Washbag 1200ml Water-pack Pump 16 Cones") for i in range(6)]
FUQ_OBS += [_obs("FUQ742", "FUQ", IC22, "endourology:stent",
                 "Ureteral Stent - Steerable Perc Plus 7Fr X 26Cm", overlap=1)]
STENTS = [{"n": "FUQ763", "_eclass": "FUQ", "_itemclass": IC22,
           "d": "Ureteral Stent - Steerable Perc Plus 7Fr X 22Cm"},
          {"n": "FUQ4380", "_eclass": "FUQ", "_itemclass": IC22,
           "d": "Ureteral Stent - with Guidewire TRIA FIRM 6X20 SH W SEN .035"}]


class ItemclassScope(unittest.TestCase):
    def test_other_itemclass_observations_carry_no_vote(self):
        kept, excluded = b.same_itemclass_only(FUQ_OBS, STENTS)
        self.assertEqual(excluded, {"FUQ": 7})
        self.assertTrue(all(o["itemclass"] == IC22 for o in kept))
        legal = {"continence:bowel", "endourology:stent"}
        by_ec, _, _ = b.aggregate(kept, legal)
        tier, winner, _ = b.decide(by_ec["FUQ"])
        self.assertNotEqual(winner, "continence:bowel")

    def test_pooled_evidence_was_the_bug(self):
        # Without the scope, the pooled votes map FUQ to continence:bowel — the
        # published defect. Kept as a test so the reason for the scope is on record.
        by_ec, _, _ = b.aggregate(FUQ_OBS, {"continence:bowel", "endourology:stent"})
        tier, winner, _ = b.decide(by_ec["FUQ"])
        self.assertEqual(winner, "continence:bowel")

    def test_suspended_itemclass_is_the_majority_of_the_lines(self):
        rows = STENTS + [{"_eclass": "FUQ", "_itemclass": IC23, "d": "x"}]
        self.assertEqual(b.suspended_itemclass(rows)["FUQ"], IC22)


class HeadNoun(unittest.TestCase):
    def test_head_noun_reads_the_catalogue_heading(self):
        self.assertEqual(b.head_noun("Drills Burs Other (specify in description) Round"), "drills")
        self.assertEqual(b.head_noun("Haemostasis - Ligation Clips/Banding Ligator"), "haemostasis")
        self.assertEqual(b.head_noun("Belt product for moderate to heavy incontinence D15"), "belt")

    def test_fcc_evidence_about_ligators_cannot_file_saw_blades(self):
        self.assertFalse(b.shares_head_noun(
            ["Drills Burs Other (specify in description) Round Cutting",
             "Oscillilating Saw Osc/Sag Blade 0.40mmThick"],
            ["Haemostasis - Ligation Clips/Banding Ligator endoscopic multiple band"]))
        self.assertTrue(b.shares_head_noun(
            ["Sheath - Introducer 6F"], ["Sheath - Introducer 5F 11cm"]))


class InferredStamp(unittest.TestCase):
    def test_inferred_entry_gets_the_itemclass_of_its_examples(self):
        inferred = {"KBD": {"cat": "bloodcoll:tube", "examples": ["Venous Tube Serum 5ml"]}}
        rows = [{"_eclass": "KBD", "_itemclass": "21- Medical and Surgical Consumables",
                 "d": "Venous Tube Serum 5ml"},
                {"_eclass": "KBD", "_itemclass": "24- Diagnostics, Equipment and Services",
                 "d": "Transport Swab Liquid Virus"},
                {"_eclass": "KBD", "_itemclass": "24- Diagnostics, Equipment and Services",
                 "d": "Transport Swab Gel Media Amies"}]
        self.assertEqual(b.stamp_inferred_itemclass(inferred, rows), 1)
        self.assertEqual(inferred["KBD"]["itemclass"], "21- Medical and Surgical Consumables")

    def test_existing_itemclass_is_kept(self):
        inferred = {"X": {"cat": "a:b", "itemclass": IC23, "examples": []}}
        b.stamp_inferred_itemclass(inferred, [{"_eclass": "X", "_itemclass": IC22, "d": "y"}])
        self.assertEqual(inferred["X"]["itemclass"], IC23)


class CommittedData(unittest.TestCase):
    """The committed files the Tracker actually reads."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "data", "eclass-category-map.json"), encoding="utf-8") as f:
            cls.map = json.load(f)
        with open(os.path.join(HERE, "data", "npc-category-overrides.json"), encoding="utf-8") as f:
            cls.overrides = json.load(f)

    def test_every_observed_mapping_names_its_itemclass(self):
        for code, ent in self.map["mappings"].items():
            self.assertTrue(ent.get("itemclass"), code)

    def test_fuq_is_not_continence_for_medical_technology(self):
        ent = self.map["mappings"].get("FUQ")
        if ent:
            self.assertFalse(ent["itemclass"] == IC22 and ent["cat"].startswith("continence:"), ent)

    def test_fva_catheters_are_not_monitoring_sensors(self):
        ent = self.map["mappings"].get("FVA")
        if ent:
            self.assertFalse(ent["itemclass"] == IC22 and ent["cat"] == "monitoring:sens", ent)

    def test_the_three_stents_are_ureteric_stents(self):
        for npc in ("FUQ763", "FUQ4380", "FUQ4461"):
            self.assertEqual(self.overrides["lines"][npc]["cat"], "endourology:stent", npc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
