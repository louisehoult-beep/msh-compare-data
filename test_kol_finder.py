#!/usr/bin/env python3
"""KOL finder: the data gate's rules and the page's filters.

scripts/check_kol_finder.py must pass on the built file and must catch the faults
it exists for (contact detail, unknown source, opt-out name, non-search LinkedIn
link, a class with no people and no empty-state wording). app/kol-finder.js filters
by speciality, class, body and text, and picks a starting speciality; node is
skipped, loudly, where missing.

    python3 test_kol_finder.py
"""
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("chk", os.path.join(HERE, "scripts", "check_kol_finder.py"))
chk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chk)
DOC = json.load(open(os.path.join(HERE, "data", "kol-finder.json")))


class Gate(unittest.TestCase):
    def test_built_file_passes(self):
        self.assertEqual(chk.check(DOC), [])

    def test_catches_contact_detail(self):
        d = copy.deepcopy(DOC)
        d["people"][0]["appearances"][0]["role"] = "Secretary, a.b@example.org"
        self.assertTrue(any("contact detail" in b for b in chk.check(d)))

    def test_catches_unknown_source_and_optout(self):
        d = copy.deepcopy(DOC)
        d["people"][0]["appearances"][0]["source"] = "nowhere"
        self.assertTrue(any("unknown source" in b for b in chk.check(d, {d["people"][1]["name"].lower()})))
        self.assertTrue(any("opt-out" in b for b in chk.check(d, {d["people"][1]["name"].lower()})))

    def test_catches_profile_link(self):
        d = copy.deepcopy(DOC)
        d["people"][0]["linkedin_search"] = "https://www.linkedin.com/in/someone"
        self.assertTrue(any("search link" in b for b in chk.check(d)))

    def test_empty_class_needs_wording(self):
        d = copy.deepcopy(DOC)
        d["classes"].append({"id": "zzz", "label": "Zzz"})
        self.assertTrue(any("zzz" in b for b in chk.check(d)))

    def test_every_person_dermatology_and_cited(self):
        for p in DOC["people"]:
            self.assertIn("dermatology", p["specialities"])
            self.assertTrue(all(a["source_url"].startswith("https://") for a in p["appearances"]))


NODE = r"""
const k = require(process.argv[1])._pure;
const doc = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const out = {
  derm: k.filter(doc.people, {spec: 'dermatology'}).length,
  wound: k.filter(doc.people, {spec: 'wound'}).length,
  speakers: k.filter(doc.people, {spec: 'dermatology', cls: 'speaker'}).length,
  supply: k.filter(doc.people, {spec: 'dermatology', cls: 'supply'}).length,
  pcds: k.filter(doc.people, {body: 'PCDS'}).length,
  q: k.filter(doc.people, {q: 'scotland'}).map(p => p.name),
  pickDefault: k.pickSpeciality(doc, ['']),
  pickUnknown: k.pickSpeciality(doc, ['zzz']),
  pickWound: k.pickSpeciality(doc, ['wound']),
  esc: k.esc('<a href="x">&\'')
};
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "node not installed")
class Page(unittest.TestCase):
    def test_filters(self):
        r = subprocess.run(["node", "-e", NODE, os.path.join(HERE, "app", "kol-finder.js"),
                            os.path.join(HERE, "data", "kol-finder.json")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        n = len(DOC["people"])
        self.assertEqual(o["derm"], n)
        self.assertEqual(o["wound"], 0)
        self.assertEqual(o["speakers"], 23)
        self.assertEqual(o["supply"], 0)
        self.assertGreater(o["pcds"], 10)
        self.assertIn("Dr Paula Beattie", o["q"])
        self.assertEqual(o["pickDefault"], "dermatology")
        self.assertEqual(o["pickUnknown"], "dermatology")
        self.assertEqual(o["pickWound"], "wound")
        self.assertNotIn("<", o["esc"])


if __name__ == "__main__":
    unittest.main()
