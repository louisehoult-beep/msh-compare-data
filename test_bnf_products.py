#!/usr/bin/env python3
r"""A BNF catch-all code must not publish every brand under one brand's name.

Added 29/09/2026.

THE DEFECT
----------
The hospital prescribing tool labelled a product by BNF code characters 1-11.
BNF's catch-all "substances" hold many unrelated brands under one 11-character
code: 130201000BB ("Other emollient preparations") holds Dermol, Doublebase,
Aveeno, E45, Oilatum and more. The tool labelled the lot "Dermol". Across the
July 2025 to July 2026 window, 19 such codes put 5,987 items under another
brand's name.

THE RULE (scripts/bnf_products.py)
----------------------------------
Where the 13-character children of an 11-character code carry labels that do not
share a first word, each child is its own product (a 4-character key such as
'BBIC'). A generic ('AA') is never split. Hyphen or underscore suffixes
('Adizem-XL', 'Fybogel_Gran') and BNF's leading 'Half' stay with their brand.

Stdlib only, offline, no network.

  python3 test_bnf_products.py        exit 0 = holds
"""
import collections
import glob
import importlib.util
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import bnf_products as bp  # noqa: E402

HP_DIR = os.path.join(HERE, "data", "hospital-prescribing")


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "refresh_hospital_prescribing",
        os.path.join(HERE, "scripts", "refresh_hospital_prescribing.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def C(**kw):
    return collections.Counter(kw)


def names(d):
    return {k: collections.Counter({v: 10}) for k, v in d.items()}


class LabelOf(unittest.TestCase):
    """30/09/2026: a digit inside a brand word is part of the brand."""

    def test_strength_is_cut(self):
        self.assertEqual(bp.label_of("Zopiclone 3.75mg tablets"), "Zopiclone")
        self.assertEqual(bp.label_of("Zerobase 11% cream"), "Zerobase")
        self.assertEqual(bp.label_of("Dermol 500 lotion"), "Dermol")

    def test_digit_inside_brand_is_kept(self):
        self.assertEqual(bp.label_of("E45 cream"), "E45 cream")
        self.assertEqual(bp.label_of("Fifty:50 ointment"), "Fifty:50 ointment")
        self.assertEqual(bp.label_of("Adcal-D3 chewable tablets 1.5g"), "Adcal-D3 chewable tablets")

    def test_leading_digit_or_none_keeps_whole_name(self):
        self.assertEqual(bp.label_of("3M Cavilon barrier cream"), "3M Cavilon barrier cream")
        self.assertEqual(bp.label_of("QV cream"), "QV cream")


class FirstWord(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(bp.first_word("Doublebase gel"), "doublebase")
        self.assertEqual(bp.first_word("E45 cream"), "e45")

    def test_suffix_joined_by_punctuation_stays_with_brand(self):
        self.assertEqual(bp.first_word("Adizem-XL"), bp.first_word("Adizem-SR"))
        self.assertEqual(bp.first_word("Fybogel_Gran Sach"), bp.first_word("Fybogel"))
        self.assertEqual(bp.first_word("Augmentin-Duo"), "augmentin")

    def test_leading_half_is_skipped(self):
        self.assertEqual(bp.first_word("Half Sinemet CR"), "sinemet")
        self.assertEqual(bp.first_word("Half"), "half")

    def test_empty(self):
        self.assertEqual(bp.first_word(""), "")
        self.assertEqual(bp.first_word(None), "")


class ProductCodes(unittest.TestCase):
    def test_catch_all_is_split(self):
        m = bp.product_codes(names({
            "130201000BBIC": "Dermol 500 lotion",
            "130201000BBJG": "Doublebase gel",
            "130201000BBBA": "E45 cream",
        }))
        self.assertEqual(m["130201000BBIC"], "130201000BBIC")
        self.assertEqual(m["130201000BBJG"], "130201000BBJG")
        self.assertEqual(bp.split_codes(m), ["130201000BB"])

    def test_one_brand_in_several_strengths_is_not_split(self):
        m = bp.product_codes(names({
            "0401010Z0BBAA": "Zimovane 3.75mg tablets",
            "0401010Z0BBAB": "Zimovane 7.5mg tablets",
        }))
        self.assertEqual(set(m.values()), {"0401010Z0BB"})

    def test_same_brand_variants_are_not_split(self):
        for a, b in (("Adizem-XL 120mg capsules", "Adizem-SR 90mg capsules"),
                     ("Sinemet 62.5mg tablets", "Half Sinemet CR 125mg tablets"),
                     ("Augmentin 375mg tablets", "Augmentin-Duo 400mg/57mg")):
            m = bp.product_codes(names({"0206020C0BFAA": a, "0206020C0BFAB": b}))
            self.assertEqual(set(m.values()), {"0206020C0BF"}, (a, b))

    def test_generic_is_never_split(self):
        m = bp.product_codes(names({
            "0906040G0AAAA": "Colecalciferol 400unit capsules",
            "0906040G0AAAB": "Vitamin D3 400unit capsules",
        }))
        self.assertEqual(set(m.values()), {"0906040G0AA"})
        self.assertEqual(bp.split_codes(m), [])

    def test_appliance_code_maps_to_itself(self):
        m = bp.product_codes(names({"21300000172": "Clinitas Multi eye drops",
                                    "21300000116": "Lumecare Singles"}))
        self.assertEqual(m["21300000172"], "21300000172")
        self.assertEqual(m["21300000116"], "21300000116")

    def test_label_uses_most_common_name(self):
        m = bp.product_codes({
            "130201000BBIC": C(**{"Dermol 500 lotion": 90, "Doublebase gel": 1}),
            "130201000BBJG": C(**{"Doublebase gel": 50}),
        })
        # The first child is labelled by its larger name (Dermol), so the two differ.
        self.assertEqual(bp.split_codes(m), ["130201000BB"])


class HospitalCollapse(unittest.TestCase):
    """The builder folds 13-character series into products under the rule."""

    @classmethod
    def setUpClass(cls):
        cls.hp = load_builder()

    def test_split_keys_and_totals(self):
        s13 = {
            "130201000BBIC": {"T1": [5, 7]},
            "130201000BBJG": {"T1": [1, 2], "T2": [3, 0]},
            "130201000AAAA": {"T1": [10, 10]},
            "130201000AAAB": {"T1": [1, 1]},
        }
        n13 = {
            "130201000BBIC": C(**{"Dermol 500 lotion": 12}),
            "130201000BBJG": C(**{"Doublebase gel": 6}),
            "130201000AAAA": C(**{"White soft paraffin": 20}),
            "130201000AAAB": C(**{"Paraffin white soft": 2}),
        }
        series, nm, split = self.hp.collapse(s13, n13, 2)
        sub = series["130201000"]
        self.assertEqual(split, ["130201000BB"])
        self.assertEqual(sub["T1"]["BBIC"], [5, 7])
        self.assertEqual(sub["T1"]["BBJG"], [1, 2])
        self.assertEqual(sub["T2"]["BBJG"], [3, 0])
        self.assertEqual(sub["T1"]["AA"], [11, 11])       # generic folded, not split
        self.assertNotIn("BB", sub["T1"])
        self.assertEqual(nm[("130201000", "BBJG")].most_common(1)[0][0], "Doublebase gel")

    def test_unsplit_brand_keeps_two_character_key(self):
        s13 = {"0401010Z0BBAA": {"T1": [1]}, "0401010Z0BBAB": {"T1": [2]}}
        n13 = {"0401010Z0BBAA": C(**{"Zimovane 3.75mg tablets": 1}),
               "0401010Z0BBAB": C(**{"Zimovane 7.5mg tablets": 2})}
        series, _nm, split = self.hp.collapse(s13, n13, 1)
        self.assertEqual(split, [])
        self.assertEqual(series["0401010Z0"]["T1"]["BB"], [3])


class PublishedShards(unittest.TestCase):
    """Structural invariants on the committed data. Skipped if it is not built."""

    def setUp(self):
        idx = os.path.join(HP_DIR, "index.json")
        if not os.path.exists(idx):
            self.skipTest("data/hospital-prescribing not built")
        with open(idx) as f:
            self.index = json.load(f)

    def test_keys_match_split_list(self):
        split = set(self.index.get("splitProducts") or [])
        bad = []
        for path in glob.glob(os.path.join(HP_DIR, "ch-*.json")):
            with open(path) as f:
                shard = json.load(f)
            for sub, rec in shard["s"].items():
                for key in rec["p"]:
                    if len(key) == 4:
                        if key[:2] == "AA" or sub + key[:2] not in split:
                            bad.append(sub + key)
                    elif len(key) == 2 and sub[:2] not in bp.APPLIANCE_CHAPTERS:
                        if sub + key in split:
                            bad.append(sub + key)
                    elif len(key) not in (2, 4):
                        bad.append(sub + key)
        self.assertEqual(bad, [], "product keys disagree with splitProducts: %s" % bad[:5])

    def test_emollient_catch_all_is_not_labelled_dermol(self):
        path = os.path.join(HP_DIR, "ch-13.json")
        if not os.path.exists(path):
            self.skipTest("ch-13 not built")
        with open(path) as f:
            rec = json.load(f)["s"].get("130201000")
        if not rec:
            self.skipTest("130201000 not in window")
        self.assertNotIn("BB", rec["p"])
        for key, label in rec["p"].items():
            if "Doublebase" in label or "Aveeno" in label:
                self.assertNotEqual(bp.first_word(label), "dermol", key)


if __name__ == "__main__":
    unittest.main()
