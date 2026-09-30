#!/usr/bin/env python3
"""Three Hub tool faults found live on a demo to HARTMANN UK, 30/09/2026.

1. "Help me prepare" (app/meeting-prep.js): typing "Hartmann" found nothing,
   because the picker is a plain <select> and a browser only jumps to an option
   that STARTS with what you type; the record is "Paul Hartmann (HARTMANN)".
   The finder box matches the start of any word of the name or of an alias,
   accents folded. These tests run that exact matcher (read out of the file,
   between its company-match markers) against the published supplier index.

2. Product Comparison (app/comparison.js): a seed product that is really a
   grouped NHS Supply Chain search term was treated as one product, so brand
   lines such as Cosmopor E never appeared, and "fabric" was labelled
   "knitted". Static checks hold the fix in place.

3. Company report (app/company-report.js): a "Download this report" button
   that saves the pack as a file, stamped with the date and the data notice.

Stdlib only. The matcher test needs `node` (present on ubuntu-latest); it is
skipped, loudly, where node is absent.
"""
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def read(rel):
    with open(os.path.join(HERE, rel), encoding="utf-8") as f:
        return f.read()


NODE_SCRIPT = r"""
const fs = require('fs');
const A = process.argv.slice(-3);
const src = fs.readFileSync(A[0], 'utf8');
const blk = src.split('/* company-match:start')[1].split('/* company-match:end */')[0];
const f = new Function('/*' + blk + '; return companyMatches;')();
const idx = JSON.parse(fs.readFileSync(A[1], 'utf8'));
const qs = JSON.parse(A[2]);
const out = {};
for (const q of qs) out[q] = idx.suppliers.filter(s => f(s, q)).map(s => s.name);
process.stdout.write(JSON.stringify(out));
"""


class CompanyFinder(unittest.TestCase):
    QUERIES = ["Hartmann", "HARTMANN", "Paul Hartmann", "Smith", "Molnlycke",
               "Mölnlycke", "Coloplast", "", "zzqxnotacompany"]

    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if not cls.node:
            return
        r = subprocess.run(
            [cls.node, "-e", NODE_SCRIPT,
             os.path.join(HERE, "app", "meeting-prep.js"),
             os.path.join(HERE, "data", "supplier-index.json"),
             json.dumps(cls.QUERIES)],
            capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError("node matcher run failed: " + r.stderr)
        cls.res = json.loads(r.stdout)
        with open(os.path.join(HERE, "data", "supplier-index.json"), encoding="utf-8") as f:
            cls.total = len(json.load(f)["suppliers"])

    def setUp(self):
        if not self.node:
            self.skipTest("node not installed; matcher not exercised")

    def test_hartmann_found_by_any_word(self):
        for q in ("Hartmann", "HARTMANN", "Paul Hartmann"):
            self.assertIn("Paul Hartmann (HARTMANN)", self.res[q], q)

    def test_hartmann_does_not_merge_other_companies(self):
        self.assertEqual(self.res["Hartmann"], ["Paul Hartmann (HARTMANN)"])

    def test_smith_finds_smith_nephew(self):
        self.assertIn("Smith+Nephew", self.res["Smith"])

    def test_accent_folding_both_ways(self):
        self.assertIn("Mölnlycke", self.res["Molnlycke"])
        self.assertEqual(self.res["Molnlycke"], self.res["Mölnlycke"])

    def test_empty_query_matches_all_and_nonsense_matches_none(self):
        self.assertEqual(len(self.res[""]), self.total)
        self.assertEqual(self.res["zzqxnotacompany"], [])


class ComparisonBrandLines(unittest.TestCase):
    def setUp(self):
        self.src = read("app/comparison.js")

    def test_detail_follows_the_brand_line(self):
        self.assertIn("function detailFor(prod){ return prod._detail || CACHE[nk(prod.name)] || null; }", self.src)

    def test_lines_only_from_this_supplier(self):
        self.assertIn("lineIsSuppliers(it, s)", self.src)

    def test_fabric_is_not_called_knitted(self):
        self.assertNotIn("/knit|fabric/", self.src)
        self.assertIn("a.form = 'non-woven fabric'", self.src)


class CompanyReportDownload(unittest.TestCase):
    def setUp(self):
        self.src = read("app/company-report.js")

    def test_download_button_and_stamp(self):
        self.assertIn('id="mcrDownload"', self.src)
        self.assertIn("Download this report", self.src)
        self.assertIn("Information correct at ", self.src)
        self.assertIn("notice: (index && index._notice) || null", self.src)

    def test_stamp_is_in_the_pack(self):
        self.assertIn("exportStamp(ctx, stamp) +", self.src)


class ComparisonHonoursTheirCompany(unittest.TestCase):
    """30/09/2026: Cosmopor E with "Their company" = Coloplast auto-picked
    Leukomed (Essity), because the auto-pick never read the chosen company.
    Reproduced in a harness against the published data with Coloplast listed
    as a real option (ten Coloplast dressings tracked)."""

    def setUp(self):
        self.src = read("app/comparison.js")

    def test_filter_applies_before_ranking_and_cut(self):
        self.assertIn("function competitorsOf(mine, supFilter){", self.src)
        self.assertIn("p.type === mine.type && (!supFilter || p.supplier === supFilter)", self.src)

    def test_auto_pick_uses_the_chosen_company(self):
        self.assertIn("var comps0 = competitorsOf(mine, selSup2.sel.value);", self.src)
        self.assertNotIn("var comps0 = competitorsOf(mine);", self.src)

    def test_honest_message_when_company_has_no_match(self):
        self.assertIn("if (chosenSupTheirs){", self.src)
        self.assertIn("so there is nothing honest to put beside it", self.src)


class CompanyReportMastheadNotAHeader(unittest.TestCase):
    """30/09/2026: the report mounts inside div.msh, and the Hub nav CSS paints
    `.msh header` with a gold gradient (!important). The masthead was a
    <header>, so it lost its navy ground and its text fell under 1.7:1."""

    def setUp(self):
        self.src = read("app/company-report.js")

    def test_masthead_is_a_div(self):
        self.assertIn("return '<div class=\"mcr-mast\">' +", self.src)
        self.assertNotIn('<header class="mcr-mast">', self.src)

    def test_navy_ground_is_important(self):
        self.assertIn("#1B3A5F 100%)!important;", self.src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
