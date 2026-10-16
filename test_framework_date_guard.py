#!/usr/bin/env python3
"""Offline tests for scripts/framework_date_guard.py (page 2802, 16/10/2026)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import framework_date_guard as g  # noqa: E402

FW = [
    {"ref": "2023/S000-012286", "name": "Vascular Therapy and Associated Products", "end": (27, 2, 2028)},
    {"ref": "2021/S000-017565", "name": "Interventional Cardiology", "end": (26, 2, 2027)},
]

# The paragraph as it stood on page 2802 until 16/10/2026.
BAD = ('<p>But the <a>compression framework</a> in February 2028 is a device-buying-route '
       'expiry, not a Part IX date. The <a>successor framework\'s</a> own estimated start '
       '(27 Feb 2027) and first-term end (26 Feb 2030) are estimates, so only the confirmed '
       '26 Feb 2027 expiry is placed on the calendar.</p>')
GOOD = ('<p>But the compression framework, Vascular Therapy and Associated Products '
        '(2023/S 000-012286), expires on 27 February 2028. The 26 Feb 2027 expiry belongs to '
        'the IC/IR framework (2021/S 000-017565).</p>')


class Guard(unittest.TestCase):
    def test_original_2802_paragraph_fails(self):
        self.assertTrue(g.check_text(BAD, FW))

    def test_fixed_paragraph_passes(self):
        self.assertEqual(g.check_text(GOOD, FW), [])

    def test_wrong_date_for_named_framework_fails(self):
        p = "<p>Vascular Therapy and Associated Products (2023/S 000-012286) expires on 26 February 2027.</p>"
        self.assertTrue(any("012286" in x for x in g.check_text(p, FW)))

    def test_start_dates_are_not_expiries(self):
        p = "<p>Vascular Therapy and Associated Products (2023/S 000-012286) started 28 Feb 2024 and live to 27 Feb 2028.</p>"
        self.assertEqual(g.check_text(p, FW), [])

    def test_real_frameworks_load(self):
        self.assertTrue(any(f["ref"] == "2023/S000-012286" and f["end"] == (27, 2, 2028)
                            for f in g.load_frameworks()))


if __name__ == "__main__":
    unittest.main()
