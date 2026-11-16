#!/usr/bin/env python3
"""
test_wales_buyer_map.py — the Wales buyer map, and the Stakeholder Mapper's
Wales branch.

Every case here is either the bug that was found on 16/11/2026 or a way this
build could quietly go wrong later. The theme is that Wales fails SILENTLY: a
dropped crawl, a mislabelled nation or a lost ICB guard does not error, it just
leaves a member-facing picker resolving to nothing, or prints a commissioner
that does not exist.

    python3 test_wales_buyer_map.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
APP = os.path.join(HERE, "app")
sys.path.insert(0, os.path.join(HERE, "scripts"))

import build_wales_buyer_map as bw  # noqa: E402


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


class BuyerMatching(unittest.TestCase):
    """The regex that decides whether an award notice's buyer is Welsh."""

    def test_the_boilerplate_that_nearly_dragged_england_into_wales(self):
        # SCCL and CPP LLP notices carry "Registered in England and Wales" in the
        # buyer field. 55 English framework awards say it. A naive /wales/ match
        # puts every one of them on a Welsh page.
        for b in ("Collaborative Procurement Partnership LLP (CPP LLP) acting on "
                  "behalf of Supply Chain Coordination Ltd. Supply Chain "
                  "Coordination Limited (SCCL) is a company Registered in England "
                  "and Wales, with company number 10881715",
                  "Supply Chain Coordination Limited, registered in England and Wales"):
            self.assertTrue(bw.NOT_A_WELSH_BUYER.search(b),
                            "should be excluded as boilerplate: %s" % b[:60])

    def test_the_spellings_that_actually_appear(self):
        for b in ("NHS Wales Shared Services Partnership-Procurement Services "
                  "(hosted by Velindre University NHS Trust)",
                  "NHS Wales Shared Service Partnership (hosted by Velindre NHS Trust)",
                  "NWSSP",
                  "NWSSP Cardiff and Vale Local Health Board",
                  "NHS Wales Shares Services Procurement",      # NWSSP's own typo
                  "Velindre NHS Trust, NHS Wales Shared Services Parternship - "
                  "Procurement Services",                        # a notice's typo
                  "eTenderwales",
                  "Swansea Bay University Health Board (SBUHB)",
                  "Cwm Taf Morgannwg University Health Board",
                  "Public Health Wales NHS Trust"):
            self.assertTrue(bw.WELSH_BUYER.search(b), "should match: %s" % b[:60])
            self.assertFalse(bw.NOT_A_WELSH_BUYER.search(b),
                             "should not be excluded: %s" % b[:60])

    def test_english_buyers_do_not_match(self):
        for b in ("University Hospitals Birmingham NHS Foundation Trust",
                  "NHS Supply Chain",
                  "University Hospitals of Leicester NHS Trust",
                  "HealthTrust Europe LLP (HTE)",
                  "NHS London Procurement Partnership",
                  "UK Health Security Agency",
                  "The Common Services Agency (more commonly known as Public "
                  "Services Delivery Scotland )"):
            self.assertFalse(bw.WELSH_BUYER.search(b), "should NOT match: %s" % b[:60])

    def test_no_stem_reaches_another_organisations_notices(self):
        """A stem that reaches two organisations puts one's notices on the other's
        row. Checked against the real buyer strings rather than against the other
        stems' regex source, which proves nothing. Hand-written, so checked."""
        doc = load("wales-buyer-map.json")
        names = [e["name"] for e in doc["buyerNames"]]
        for code, pats in bw.ORG_NAME_STEMS.items():
            for pat in pats:
                for other, opats in bw.ORG_NAME_STEMS.items():
                    if other == code:
                        continue
                    both = [n for n in names
                            if re.search(pat, n, re.I)
                            and any(re.search(op, n, re.I) for op in opats)]
                    # Velindre legitimately co-occurs: NWSSP is hosted by it, so a
                    # notice can name Velindre AND the board it is buying for.
                    both = [n for n in both
                            if "RQF" not in (code, other)]
                    self.assertEqual(both, [],
                                     "stem %r (%s) also matches %s's notices: %s"
                                     % (pat, code, other, both[:2]))

    def test_each_stem_actually_matches_its_own_organisation(self):
        """A stem that matches nothing is dead weight that reads as coverage."""
        doc = load("wales-buyer-map.json")
        by_code = {o["code"]: o for o in doc["organisations"]}
        for code, pats in bw.ORG_NAME_STEMS.items():
            self.assertIn(code, by_code)
            hay = (by_code[code]["n"] + " " + by_code[code]["odsName"]).lower()
            self.assertTrue(
                any(re.search(p, hay, re.I) for p in pats),
                "no stem for %s matches its own name %r" % (code, by_code[code]["n"]))


class TheBuiltFile(unittest.TestCase):
    def setUp(self):
        self.doc = load("wales-buyer-map.json")
        self.tm = load("trust-map.json")

    def test_seven_health_boards_and_three_trusts(self):
        orgs = self.doc["organisations"]
        boards = [o for o in orgs if o["primaryRoleId"] == "RO142"]
        trusts = [o for o in orgs if o["primaryRoleId"] == "RO197"]
        self.assertEqual(len(boards), 7, "Wales has seven Local Health Boards")
        self.assertEqual(len(trusts), 3)

    def test_every_organisation_is_welsh_and_sourced(self):
        for o in self.doc["organisations"]:
            self.assertEqual(o["nation"], "Wales", o["code"])
            self.assertEqual(o["odsName"].strip().upper(), o["odsName"].strip(),
                             "odsName should be the register's own spelling")
            self.assertTrue(o["source"].startswith("https://"), o["code"])

    def test_it_joins_to_trust_map_by_code(self):
        """The Hub joins these two files by ODS code. A code in one and not the
        other is the silent half-migration this is here to stop."""
        codes = {t["code"] for t in self.tm["trusts"]}
        for o in self.doc["organisations"]:
            self.assertIn(o["code"], codes,
                          "%s is in the Wales map but not trust-map.json" % o["code"])

    def test_no_buyer_spelling_without_a_notice_behind_it(self):
        for e in self.doc["buyerNames"]:
            self.assertGreater(e["awards"], 0, e["name"])
            self.assertTrue(e["sources"], "%s cites no source" % e["name"])

    def test_the_route_keeps_its_sources(self):
        r = self.doc["procurementRoute"]
        self.assertEqual(r["shortName"], "NWSSP")
        self.assertTrue(r["checkedAt"])
        for f in ("whatItIs", "buysOnBehalfOf", "frameworkScope", "frameworkTerm",
                  "smes"):
            self.assertTrue(r.get(f + "Source", "").startswith("https://"),
                            "%s has no source URL" % f)
        # The fact a rep actually needs. Wales advertises on Sell2Wales; a
        # supplier watching only Find a Tender misses the Welsh pipeline.
        self.assertIn("sell2wales", r["advertisedOn"]["url"].lower())

    def test_nwssp_is_not_claimed_as_an_ods_organisation(self):
        """NWSSP has no ODS record. Inventing one would be the easy mistake, and
        it would then fail the join above in a confusing way."""
        for o in self.doc["organisations"]:
            self.assertNotIn("nwssp", o["odsName"].lower())
        self.assertEqual(self.doc["procurementRoute"]["hostedBy"]["odsCode"], "RQF")

    def test_velindre_says_the_notices_are_mostly_not_its_own_buying(self):
        v = [o for o in self.doc["organisations"] if o["code"] == "RQF"][0]
        self.assertIn("NWSSP", v.get("note", ""),
                      "Velindre's ~174 notices are NWSSP buying for all of Wales; "
                      "the row has to say so or a reader takes them as one cancer "
                      "centre's purchasing")


class TrustMapWales(unittest.TestCase):
    def setUp(self):
        self.trusts = load("trust-map.json")["trusts"]

    def test_the_seven_boards_are_in_the_trust_map(self):
        boards = [t for t in self.trusts if t["kind"] == "Local Health Board"]
        self.assertEqual(len(boards), 7)
        for t in boards:
            self.assertEqual(t["nation"], "Wales", t["n"])
            self.assertIsNone(t["icb"], "Wales has no ICBs")
            self.assertIsNone(t["icbName"])

    def test_nation_is_backed_by_the_registers_own_country_field(self):
        """This replaced `welsh = icb is None`, which was a guess that would have
        mislabelled any organisation whose ICB link lapsed."""
        for t in self.trusts:
            self.assertIn(t.get("odsCountry"), ("ENGLAND", "WALES"),
                          "%s has ODS country %r" % (t["n"], t.get("odsCountry")))
            self.assertEqual(t["nation"],
                             "Wales" if t["odsCountry"] == "WALES" else "England",
                             t["n"])

    def test_no_welsh_row_carries_an_icb(self):
        for t in self.trusts:
            if t["nation"] == "Wales":
                self.assertFalse(t["icb"], t["n"])


NODE_HARNESS = r"""
// Evaluate only the Wales helpers out of app/mst-logic.js. The file is an IIFE
// that needs a whole DOM, so the pure parts are sliced out and run here.
%(src)s
var TRUSTS = %(trusts)s;
var GEO = '';
function $(id){ return id === 'm-geo' ? {value: GEO} : null; }
function esc(s){ return String(s == null ? '' : s); }
var out = {};
out.walesAll = (function(){ GEO = WALES_ALL; return trustsInICB().map(function(t){return t.code;}); })();
out.cardiff = (function(){ GEO = 'Cardiff and Vale University Health Board';
  return trustsInICB().map(function(t){return t.code;}); })();
out.powys = (function(){ GEO = 'Powys Teaching Health Board';
  return trustsInICB().map(function(t){return t.code;}); })();
out.england = (function(){ GEO = 'NHS Lincolnshire ICB';
  return trustsInICB().map(function(t){return t.code;}); })();
out.isWalesBoard = geoIsWales('Swansea Bay University Health Board');
out.isWalesEngland = geoIsWales('NHS Lincolnshire ICB');
out.isWalesTrap = geoIsWales('NHS Wales ICB');
out.commWelshBoard = commissionerOf({nation:'Wales', icbName:null});
out.commEnglish = commissionerOf({nation:'England', icbName:'Lincolnshire'});
out.commUnknown = commissionerOf({nation:'England', icbName:null});
console.log(JSON.stringify(out));
"""


class MapperWalesBranch(unittest.TestCase):
    """app/mst-logic.js. The bug was that icbName is null for every Welsh row and
    three places concatenated it into a sentence regardless."""

    @classmethod
    def setUpClass(cls):
        cls.src = open(os.path.join(APP, "mst-logic.js"), encoding="utf-8").read()

    def test_it_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        r = subprocess.run([node, "--check", os.path.join(APP, "mst-logic.js")],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_site_still_concatenates_an_icb_name_into_a_sentence(self):
        """THE ACTUAL BUG. Three places built 'NHS ' + icbName + ' ICB'. For a
        Welsh organisation two rendered 'NHS  ICB' and the printable account
        sheet rendered the literal string 'NHS null ICB'."""
        for pat in (r"'NHS\s*'\s*\+\s*esc\(\s*t\w*\.icbName\s*\)",
                    r"'NHS\s*'\s*\+\s*t\w*\.icbName"):
            self.assertIsNone(re.search(pat, self.src),
                              "an ICB name is still concatenated into a sentence "
                              "(%s) instead of going through commissionerOf()" % pat)

    def test_commissioner_line_has_one_definition(self):
        self.assertEqual(len(re.findall(r"function commissionerOf\(", self.src)), 1)

    def test_wales_is_in_the_geography_picker(self):
        self.assertIn("GEOS_WALES", self.src)
        for board in ("Betsi Cadwaladr", "Hywel Dda", "Swansea Bay",
                      "Cardiff and Vale", "Cwm Taf Morgannwg", "Aneurin Bevan",
                      "Powys"):
            self.assertIn(board, self.src, "%s is missing from the picker" % board)

    def test_local_health_board_is_a_group_the_picker_renders(self):
        """trust-map.json now carries kind 'Local Health Board'. fillTrust only
        renders the groups named in `order`, so a kind missing from that list is
        a board that silently never appears in the dropdown."""
        m = re.search(r"order\s*=\s*\[([^\]]+)\]", self.src)
        self.assertIsNotNone(m)
        self.assertIn("Local Health Board", m.group(1))

    def test_wales_detection_is_an_exact_match_not_a_substring(self):
        """'NHS Wales ICB' does not exist, but a substring test for 'wales' would
        send anything containing the word down the Welsh branch."""
        self.assertIsNone(re.search(r"indexOf\(\s*['\"]wales['\"]", self.src, re.I),
                          "Wales must not be detected by substring")

    def test_the_branch_behaves(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        # Slice out the declarations and functions under test.
        wanted = []
        for pat in (r"var GEOS_WALES=\{.*?\]\};",
                    r"var WALES_ALL=.*?;",
                    r"var WALES_STEMS=\{.*?\};",
                    r"var WALES_NATIONAL=\[.*?\];",
                    r"function geoIsWales\(v\)\{.*?\n    return false;\}",
                    r"function trustsInWales\(val\)\{.*?\n  \}",
                    r"function commissionerOf\(t\)\{.*?\n  \}",
                    r"function icbNameFromGeo\(\)\{.*?\n  \}",
                    r"function trustsInICB\(\)\{.*?\n  \}"):
            m = re.search(pat, self.src, re.S)
            self.assertIsNotNone(m, "could not slice %s out of mst-logic.js" % pat)
            wanted.append(m.group(0))

        trusts = [t for t in load("trust-map.json")["trusts"]
                  if t["nation"] == "Wales" or t.get("icbName") == "Lincolnshire"]
        script = NODE_HARNESS % {"src": "\n".join(wanted),
                                 "trusts": json.dumps(trusts)}
        r = subprocess.run([node, "-e", script], capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)

        self.assertEqual(sorted(out["walesAll"]),
                         ["7A1", "7A2", "7A3", "7A4", "7A5", "7A6", "7A7",
                          "RQF", "RT4", "RYT"],
                         "'All Wales' must reach every Welsh organisation")
        # A board entry returns that board plus the three national trusts, because
        # NWSSP buys for all of them.
        self.assertEqual(sorted(out["cardiff"]), ["7A4", "RQF", "RT4", "RYT"])
        self.assertEqual(sorted(out["powys"]), ["7A7", "RQF", "RT4", "RYT"])
        # England is untouched: no Welsh row may leak into an ICB.
        self.assertNotIn("7A4", out["england"])
        self.assertNotIn("RQF", out["england"])

        self.assertTrue(out["isWalesBoard"])
        self.assertFalse(out["isWalesEngland"])
        self.assertFalse(out["isWalesTrap"],
                         "an invented 'NHS Wales ICB' must not reach the Welsh branch")

        # It may SAY Wales has no ICBs; it must never name one.
        self.assertIsNone(re.search(r"commissioned by|NHS\s+\w+\s+ICB\b",
                                    out["commWelshBoard"]),
                          "a Welsh organisation must never be given an ICB: %r"
                          % out["commWelshBoard"])
        self.assertIn("NWSSP", out["commWelshBoard"])
        self.assertEqual(out["commEnglish"], "commissioned by NHS Lincolnshire ICB")
        self.assertNotIn("null", out["commUnknown"])
        self.assertNotIn("NHS  ICB", out["commUnknown"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
